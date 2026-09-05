"""Verified 3-dipath 4-colouring generator for arXiv:1605.08905.

The module inverse-generates a hard-looking regular four-colouring instance and
then applies exactly the oriented-graph construction in Section 4, Lemma 22.
The answer is a compact colour word for the two ports of every gadget.  The
checker expands that word to all oriented-graph vertices and checks bounded
directed reachability exactly; it never reads the planted answer.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - no helper is required for this family
    exact_matrices = rationals = None


TRACK: str = "A"

_REDUCTION_CITATION = (
    "Section 4, Lemma 22 and Theorem 23: replace each vertex by the "
    "H_{k,t} port/tournament/path gadget and each acyclically oriented source "
    "edge by an out-port to in-port arc"
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "acyclic oriented graph given by five-vertex port gadgets",
        "3-dipath 4-colouring encoded by its port-colour word",
    ],
    "verification_operations": [
        "exact expansion of the port word to all oriented vertices",
        "directed breadth-first search to depth three",
        "integer colour comparison on every reached vertex pair",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION_CITATION,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "The overlapping 3-dipath cliques force each gadget's two ports to "
        "share a colour, leaving a hidden balanced four-partition on the port "
        "constraint graph; without that propagation one faces the full "
        "oriented graph."
    ),
    "hardness_basis": (
        "Track A: Theorem 23 proves NP-completeness at the used fixed regime "
        "t=4>k=3 even for directed girth at least 4; shipping uses 252 ports "
        "in a degree-9 balanced planted regular regime with randomized "
        "degree-preserving switches, for which no efficient exact method is "
        "known and G5 measures a bounded exact DSATUR baseline."
    ),
    "max_answer_tokens": 254,
}

NATIVE: dict = {
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

DIFFICULTY: dict = {
    "demo": {"n": 8, "regular_degree": 3, "switch_rounds": 0},
    "easy": {"n": 252, "regular_degree": 9, "switch_rounds": 50},
    "medium": {"n": 252, "regular_degree": 9, "switch_rounds": 75},
    "hard": {"n": 252, "regular_degree": 9, "switch_rounds": 100},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "Each five-vertex gadget contains two overlapping four-vertex "
    "3-dipath cliques with the same three internal vertices."
)
PLACEBO_HINT: str = (
    "Each five-vertex gadget should be tracked carefully together with all "
    "of its displayed incident arcs."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A word of exactly n symbols from {1,2,3,4}, in port-index order, "
        "with symbol 0 fixed to 1 and the stated anchor-neighbour symbol "
        "fixed to 2."
    ),
    "bounds": {
        "alphabet_size": 4,
        "min_word_length": 8,
        "max_word_length": 504,
        "fixed_symmetry_symbols": 2,
        "shipping_word_length": 252,
    },
}

NOTES: str = r"""
Section 2 fixes the exact definition: weak distance is the smaller of the two
directed distances, and vertices at weak distance at most k must have different
colours.  Observation 1 identifies this with proper colouring of G^k when the
directed girth is at least k+1.  Section 4, Lemma 22 supplies the construction
used here.  For k=3,t=4 each source vertex becomes the directed path
v_out -> s_v -> t_v -> v'_1 -> v_in.  Consecutive four-vertex subpaths are
3-dipath cliques, forcing v_out and v_in to have the same colour.  A source
edge becomes an arc from one out-port to the other endpoint's in-port.  Theorem
23 proves NP-completeness in the directed-girth-restricted regime t>k>=3.

The same theorem also identifies the easy boundary that the generator avoids:
for directed girth at least k+1 and t<=k, colourability is polynomial via a
homomorphism to the transitive tournament.  Theorem 19 records the separate
k=2 dichotomy, and Theorem 24 gives the unrestricted dichotomy.  This module
uses k=3,t=4 throughout and constructs an acyclic oriented graph, hence one of
infinite directed girth.

The certificate is produced before the instance is solved.  Four equal hidden
classes are sampled first.  Edge-disjoint perfect matchings between different
classes make a regular source graph; degree-preserving switches erase the
matching layers without changing the held colouring.  Public vertex labels,
edge order, and an independent acyclic orientation are randomized.  Lemma 22
then transports the held source colouring to the oriented graph.  The verifier
does not appeal to that lemma: it deterministically expands a submitted port
word, builds every arc, and scans directed reachability to depth three.

All public ports have equal undirected degree, defeating a degree outlier.
Random relabelling defeats input order.  Switches destroy the exact matching
layers and equitable per-class neighbour counts that otherwise create an
obvious spectral eigenvector.  Selftest also runs greedy saturation, randomized
min-conflicts, a non-backtracking spectral clustering probe, and bounded exact
DSATUR/DPLL.  Plants and decoys are the same population: every source edge is
sampled subject to the same hidden-partition constraint.

The attack budgets are evidence, not a proof of average-case hardness.  During
the builder audit, combining spectral initialization with twenty 200,000-step
min-conflicts restarts solved 2 of 8 panel seeds after roughly 2.5--3.2 million
updates on the successful runs.  That larger hybrid is deliberately disclosed
as a caveat; it is outside the declared G6 attack budget and prevents any claim
stronger than the measured Track-A baseline.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_DSATUR_PANEL_BUDGET = 200_000
_DSATUR_BASELINE_BUDGET = 1_000_000

# Filled only from harness-owned transcripts after the three oracle arms run.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _validate_params(n: int, regular_degree: int, switch_rounds: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 4:
        raise ValueError("n must be an integer multiple of 4 and at least 8")
    if n > 504:
        raise ValueError("n may not exceed the certificate-language bound 504")
    class_size = n // 4
    if (
        isinstance(regular_degree, bool)
        or not isinstance(regular_degree, int)
        or regular_degree < 3
        or regular_degree % 3
        or regular_degree > 3 * class_size
    ):
        raise ValueError(
            "regular_degree must be a positive multiple of 3 no larger than 3n/4"
        )
    if (
        isinstance(switch_rounds, bool)
        or not isinstance(switch_rounds, int)
        or switch_rounds < 0
        or switch_rounds > 200
    ):
        raise ValueError("switch_rounds must be an integer in 0..200")


def _canon_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _sample_matching(
    left: list[int],
    right: list[int],
    edges: set[tuple[int, int]],
    rng: random.Random,
) -> list[tuple[int, int]]:
    for _attempt in range(10_000):
        targets = right[:]
        rng.shuffle(targets)
        layer = [_canon_edge(left[i], targets[i]) for i in range(len(left))]
        if not any(edge in edges for edge in layer):
            return layer
    raise RuntimeError("could not sample an edge-disjoint perfect matching")


def _regular_four_partite_edges(
    class_size: int, regular_degree: int, rng: random.Random
) -> set[tuple[int, int]]:
    classes = [
        list(range(colour * class_size, (colour + 1) * class_size))
        for colour in range(4)
    ]
    edges: set[tuple[int, int]] = set()
    pair_degree = regular_degree // 3
    for left in range(4):
        for right in range(left + 1, 4):
            for _ in range(pair_degree):
                edges.update(
                    _sample_matching(classes[left], classes[right], edges, rng)
                )
    return edges


def _switch_edges(
    edges: set[tuple[int, int]],
    class_size: int,
    switch_rounds: int,
    rng: random.Random,
) -> None:
    """Randomize layers while preserving degree and the held four-colouring."""
    rows = list(edges)
    for _ in range(switch_rounds * class_size):
        for _attempt in range(10_000):
            pos1, pos2 = rng.sample(range(len(rows)), 2)
            edge1, edge2 = rows[pos1], rows[pos2]
            u, v = edge1
            x, y = edge2
            orientations = [(u, v, x, y), (u, v, y, x), (v, u, x, y), (v, u, y, x)]
            rng.shuffle(orientations)
            replacement = None
            for a, b, c, d in orientations:
                if a == c or a // class_size != c // class_size:
                    continue
                if b // class_size == d // class_size:
                    continue
                new1 = _canon_edge(a, d)
                new2 = _canon_edge(c, b)
                if new1 in edges or new2 in edges:
                    continue
                replacement = new1, new2
                break
            if replacement is None:
                continue
            new1, new2 = replacement
            edges.remove(edge1)
            edges.remove(edge2)
            edges.add(new1)
            edges.add(new2)
            rows[pos1], rows[pos2] = new1, new2
            break
        else:
            raise RuntimeError("could not perform a degree-preserving switch")


def _undirected_adjacency(n: int, arcs: list[list[int]]) -> list[set[int]]:
    adjacency = [set() for _ in range(n)]
    for u, v in arcs:
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def _canonicalize_colours(colours: list[int], anchor: int) -> str:
    first = colours[0]
    second = colours[anchor]
    if first == second:
        order = [first] + [colour for colour in range(4) if colour != first]
    else:
        order = [first, second] + [
            colour for colour in range(4) if colour not in (first, second)
        ]
    rename = {old: str(new + 1) for new, old in enumerate(order)}
    return "".join(rename[colour] for colour in colours)


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate and carry a colouring through Lemma 22's reduction."""
    unknown = set(params) - {"regular_degree", "switch_rounds"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    regular_degree = params.get("regular_degree", 9)
    switch_rounds = params.get("switch_rounds", 50)
    _validate_params(n, regular_degree, switch_rounds)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    class_size = n // 4
    edges = _regular_four_partite_edges(class_size, regular_degree, rng)
    _switch_edges(edges, class_size, switch_rounds, rng)

    # Hide the balanced classes before adding an unrelated acyclic orientation.
    permutation = list(range(n))
    rng.shuffle(permutation)
    public_edges = [
        _canon_edge(permutation[u], permutation[v]) for u, v in edges
    ]
    hidden_colours = [0] * n
    for old, public in enumerate(permutation):
        hidden_colours[public] = old // class_size

    topological_order = list(range(n))
    rng.shuffle(topological_order)
    rank = {vertex: i for i, vertex in enumerate(topological_order)}
    arcs = [
        [u, v] if rank[u] < rank[v] else [v, u] for u, v in public_edges
    ]
    rng.shuffle(arcs)

    adjacency = _undirected_adjacency(n, arcs)
    anchor = min(adjacency[0])
    answer = _canonicalize_colours(hidden_colours, anchor)
    return {
        "family": "lemma22_3_dipath_4_colouring",
        "k": 3,
        "t": 4,
        "n": n,
        "oriented_vertices": 5 * n,
        "regular_degree": regular_degree,
        "switch_rounds": switch_rounds,
        "base_arcs": arcs,
        "anchor_neighbor": anchor,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete oriented graph and exact output contract."""
    n = inst["n"]
    tokens = [f"O{u}->I{v}" for u, v in inst["base_arcs"]]
    rows = ["  " + "  ".join(tokens[i : i + 10]) for i in range(0, len(tokens), 10)]
    statement = f"""3-dipath 4-colouring of an oriented graph

An oriented graph is a directed graph with no loops and with at most one of
u->v and v->u for each pair of distinct vertices.  A directed path of length L
is a sequence of L arcs followed in their displayed directions.  Two vertices
have weak distance at most 3 when there is a directed path of length 1, 2, or 3
from either one to the other.  A 3-dipath 4-colouring assigns one of the colours
1,2,3,4 to every vertex so that all pairs at weak distance at most 3 receive
different colours.

This oriented graph has {5 * n} vertices arranged in {n} indexed gadgets.  For
every index i from 0 through {n - 1}, inclusive, gadget i has the five distinct
vertices Oi, Si, Ti, Pi, Ii and exactly these four internal arcs:

    Oi -> Si -> Ti -> Pi -> Ii

The following are all additional arcs; an item Ou->Iv means the single arc
from vertex Ou to vertex Iv.  Order in this list has no meaning:
{chr(10).join(rows)}

There are no other vertices or arcs.  The graph is promised to be acyclic.

Return a port-colour word w of exactly {n} symbols.  Symbol w[i] is assigned to
both Oi and Ii.  Expand it to the three internal vertices by taking the other
three colours in increasing order: Si gets the smallest colour unequal to
w[i], Ti the middle such colour, and Pi the largest.  Your word is valid exactly
when this expanded assignment is a 3-dipath 4-colouring of the entire displayed
oriented graph.

Symbols are written without commas or spaces and must lie in 1..4.  To remove
global colour-name symmetry, w[0] must be 1 and w[{inst['anchor_neighbor']}] must
be 2.  Repeated colours are allowed and required; indices are zero-based.

Give your final answer inside <answer></answer> tags, as the exact {n}-symbol
word in increasing gadget-index order.
Syntax-only example (not instance data): <answer>12341432</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged colour word, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        if len(body) >= 2 and body[0] == body[-1] == '"':
            try:
                body = json.loads(body)
            except (TypeError, ValueError):
                continue
        if isinstance(body, str) and body and all(char in "1234" for char in body):
            return body
    return None


def _expanded_colours(answer: str) -> list[int]:
    colours: list[int] = []
    for symbol in answer:
        port = int(symbol)
        other = [colour for colour in range(1, 5) if colour != port]
        colours.extend([port, other[0], other[1], other[2], port])
    return colours


def _oriented_adjacency(inst: dict) -> list[list[int]]:
    n = inst["n"]
    adjacency = [[] for _ in range(5 * n)]
    for gadget in range(n):
        start = 5 * gadget
        for offset in range(4):
            adjacency[start + offset].append(start + offset + 1)
    for u, v in inst["base_arcs"]:
        adjacency[5 * u].append(5 * v + 4)
    return adjacency


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized canonical-extension witness; never read the plant."""
    if not isinstance(answer, str):
        return False, "answer must be one port-colour word"
    if not answer:
        return False, "port-colour word must not be empty"
    n = inst.get("n")
    if not isinstance(n, int) or n < 1:
        return False, "malformed instance size"
    if len(answer) != n:
        return False, f"port-colour word must contain exactly {n} symbols"
    if any(char not in "1234" for char in answer):
        return False, "every symbol must be one of 1, 2, 3, or 4"
    if answer[0] != "1":
        return False, "symbol 0 must be 1 to normalize colour names"
    anchor = inst.get("anchor_neighbor")
    if not isinstance(anchor, int) or not (0 <= anchor < n):
        return False, "malformed anchor neighbour"
    if answer[anchor] != "2":
        return False, f"symbol {anchor} must be 2 to normalize colour names"

    arcs = inst.get("base_arcs")
    if not isinstance(arcs, list):
        return False, "malformed additional-arc list"
    seen_pairs: set[tuple[int, int]] = set()
    for number, row in enumerate(arcs):
        if (
            not isinstance(row, list)
            or len(row) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in row)
        ):
            return False, f"malformed additional arc {number}"
        u, v = row
        pair = _canon_edge(u, v)
        if not (0 <= u < n and 0 <= v < n and u != v) or pair in seen_pairs:
            return False, f"invalid or repeated endpoints at additional arc {number}"
        seen_pairs.add(pair)
        if answer[u] == answer[v]:
            return False, (
                f"additional arc O{u}->I{v} has equal port colour {answer[u]}"
            )

    # Execute the native definition: expand all 5n colours, then inspect every
    # directed path endpoint reachable within three arcs.
    colours = _expanded_colours(answer)
    adjacency = _oriented_adjacency(inst)
    for source in range(len(adjacency)):
        reached = {source}
        frontier = {source}
        for distance in range(1, 4):
            frontier = {
                target
                for vertex in frontier
                for target in adjacency[vertex]
                if target not in reached
            }
            for target in frontier:
                if colours[source] == colours[target]:
                    return False, (
                        "expanded colouring repeats a colour at directed "
                        f"distance {distance}"
                    )
            reached.update(frontier)
            if not frontier:
                break
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample after enforcing both stated symmetry constraints."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    word = [str(rng.randrange(1, 5)) for _ in range(inst["n"])]
    word[0] = "1"
    word[inst["anchor_neighbor"]] = "2"
    return "".join(word)


def search_space(inst: dict) -> int | None:
    """Exact size of the normalized port-colour-word language."""
    return 4 ** (inst["n"] - 2)


def enumerate_all(inst: dict) -> int | None:
    """Count valid normalized witnesses when at most two million are tested."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    anchor = inst["anchor_neighbor"]
    free = [index for index in range(n) if index not in (0, anchor)]
    word = ["1"] * n
    word[anchor] = "2"
    count = 0
    for values in itertools.product("1234", repeat=len(free)):
        for index, value in zip(free, values):
            word[index] = value
        if verify(inst, "".join(word))[0]:
            count += 1
    return count


def _structural_signature(inst: dict) -> list[Any]:
    """A strong cheap problem invariant (not a complete canonical form).

    Arc direction is intentionally absent.  In this Lemma 22 construction each
    additional arc only joins a source port to a sink port, so reversing it does
    not change any port-colour constraint: weak distance is symmetric in which
    endpoint can reach the other.  The underlying source graph is therefore the
    exact constraint object represented by the compact answer language.
    """
    n = inst["n"]
    arcs = inst["base_arcs"]
    adjacency = _undirected_adjacency(n, arcs)

    triangles = []
    local = []
    for vertex in range(n):
        neighbours = sorted(adjacency[vertex])
        triangle_count = sum(
            right in adjacency[left]
            for i, left in enumerate(neighbours)
            for right in neighbours[i + 1 :]
        )
        triangles.append(triangle_count)
        local.append(
            (
                len(neighbours),
                triangle_count,
                sum(len(adjacency[v]) for v in neighbours),
                sum(
                    len(adjacency[vertex] & adjacency[v]) for v in neighbours
                ),
            )
        )

    common_hist: Counter[int] = Counter()
    for u in range(n):
        for v in range(u + 1, n):
            common_hist[len(adjacency[u] & adjacency[v])] += 1

    return [
        n,
        len(arcs),
        sorted(local),
        sorted(triangles),
        sorted(common_hist.items()),
    ]


def canonical_key(inst: dict) -> str:
    """Hash only a relabelling-invariant structural signature."""
    payload = json.dumps(_structural_signature(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Erase more matching-layer structure at fixed answer length."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    degree = params.get("regular_degree", 9)
    switches = params.get("switch_rounds", 0)
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (n, degree, switches)
    ):
        return None
    if switches < 200:
        out = dict(params)
        out["switch_rounds"] = min(200, switches + 10)
        return out
    return "cap_bound"


def _transform_instance(
    inst: dict, permutation: list[int], arc_order: list[int] | None = None
) -> dict:
    """Carry the compact oriented graph and witness through relabellings."""
    n = inst["n"]
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation is not a relabelling of 0..n-1")
    arcs = [[permutation[u], permutation[v]] for u, v in inst["base_arcs"]]
    if arc_order is not None:
        if sorted(arc_order) != list(range(len(arcs))):
            raise ValueError("arc_order is not a permutation of the arc list")
        arcs = [arcs[index] for index in arc_order]

    old_word = inst["answer"]
    colours = [0] * n
    for old, new in enumerate(permutation):
        colours[new] = int(old_word[old]) - 1
    adjacency = _undirected_adjacency(n, arcs)
    anchor = min(adjacency[0])
    answer = _canonicalize_colours(colours, anchor)
    return {
        "family": inst["family"],
        "k": 3,
        "t": 4,
        "n": n,
        "oriented_vertices": 5 * n,
        "regular_degree": inst["regular_degree"],
        "switch_rounds": inst["switch_rounds"],
        "base_arcs": arcs,
        "anchor_neighbor": anchor,
        "answer": answer,
    }


def _degree_order_attack(inst: dict) -> str:
    adjacency = _undirected_adjacency(inst["n"], inst["base_arcs"])
    order = sorted(range(inst["n"]), key=lambda u: (-len(adjacency[u]), u))
    colours = [0] * inst["n"]
    for rank, vertex in enumerate(order):
        colours[vertex] = rank % 4
    return _canonicalize_colours(colours, inst["anchor_neighbor"])


def _greedy_saturation_attack(inst: dict) -> str:
    adjacency = _undirected_adjacency(inst["n"], inst["base_arcs"])
    n = inst["n"]
    colours = [-1] * n
    masks = [0] * n
    anchor = inst["anchor_neighbor"]
    colours[0] = 0
    colours[anchor] = 1
    for vertex in adjacency[0]:
        if colours[vertex] < 0:
            masks[vertex] |= 1
    for vertex in adjacency[anchor]:
        if colours[vertex] < 0:
            masks[vertex] |= 2
    for _ in range(n - 2):
        vertex = max(
            (u for u in range(n) if colours[u] < 0),
            key=lambda u: (masks[u].bit_count(), len(adjacency[u]), -u),
        )
        choices = [colour for colour in range(4) if not masks[vertex] & (1 << colour)]
        if not choices:
            for u in range(n):
                if colours[u] < 0:
                    colours[u] = 0
            return _canonicalize_colours(colours, anchor)
        colour = choices[0]
        colours[vertex] = colour
        for neighbour in adjacency[vertex]:
            if colours[neighbour] < 0:
                masks[neighbour] |= 1 << colour
    return _canonicalize_colours(colours, anchor)


def _min_conflicts_attack(
    inst: dict, rng: random.Random, restarts: int = 8, steps: int = 5_000
) -> tuple[str, int]:
    adjacency = _undirected_adjacency(inst["n"], inst["base_arcs"])
    n = inst["n"]
    operations = 0
    last = [0] * n
    for _ in range(restarts):
        colours = [rng.randrange(4) for _ in range(n)]
        counts = [
            sum(colours[v] == colours[w] for w in adjacency[v]) for v in range(n)
        ]
        operations += sum(len(row) for row in adjacency)
        bad = {vertex for vertex, count in enumerate(counts) if count}
        for _step in range(steps):
            if not bad:
                return _canonicalize_colours(colours, inst["anchor_neighbor"]), operations
            vertex = rng.choice(tuple(bad))
            scores = [
                sum(colours[neighbour] == colour for neighbour in adjacency[vertex])
                for colour in range(4)
            ]
            operations += 4 * len(adjacency[vertex])
            best = min(scores)
            choices = [colour for colour, score in enumerate(scores) if score == best]
            new_colour = rng.choice(choices)
            old_colour = colours[vertex]
            if new_colour == old_colour and rng.randrange(20) == 0:
                new_colour = rng.randrange(4)
            if new_colour == old_colour:
                continue
            colours[vertex] = new_colour
            counts[vertex] = scores[new_colour]
            for neighbour in adjacency[vertex]:
                if colours[neighbour] == old_colour:
                    counts[neighbour] -= 1
                if colours[neighbour] == new_colour:
                    counts[neighbour] += 1
                if counts[neighbour]:
                    bad.add(neighbour)
                else:
                    bad.discard(neighbour)
            if counts[vertex]:
                bad.add(vertex)
            else:
                bad.discard(vertex)
        last = colours
    return _canonicalize_colours(last, inst["anchor_neighbor"]), operations


def _orthonormalize(rows: list[list[float]]) -> list[list[float]]:
    result: list[list[float]] = []
    for row in rows:
        mean = sum(row) / len(row)
        row = [value - mean for value in row]
        for previous in result:
            dot = sum(x * y for x, y in zip(row, previous))
            row = [x - dot * y for x, y in zip(row, previous)]
        norm = math.sqrt(sum(value * value for value in row)) or 1.0
        result.append([value / norm for value in row])
    return result


def _nonbacktracking_spectral_attack(
    inst: dict, rng: random.Random, iterations: int = 80
) -> tuple[str, int]:
    """Three-vector non-backtracking clustering; the construction-aware probe."""
    adjacency = _undirected_adjacency(inst["n"], inst["base_arcs"])
    directed: list[tuple[int, int]] = []
    position: dict[tuple[int, int], int] = {}
    for u in range(inst["n"]):
        for v in sorted(adjacency[u]):
            position[(u, v)] = len(directed)
            directed.append((u, v))
    reverse = [position[(v, u)] for u, v in directed]
    outgoing = [
        [position[(v, w)] for w in sorted(adjacency[v])] for _, v in directed
    ]
    size = len(directed)
    vectors = [
        [rng.uniform(-1.0, 1.0) for _ in range(size)] for _ in range(3)
    ]
    vectors = _orthonormalize(vectors)
    operations = 0
    for _ in range(iterations):
        rows = []
        for vector in vectors:
            sums = [sum(vector[index] for index in row) for row in outgoing]
            rows.append(
                [-(sums[i] - vector[reverse[i]]) for i in range(size)]
            )
            operations += sum(len(row) for row in outgoing)
        vectors = _orthonormalize(rows)

    points = []
    for vertex in range(inst["n"]):
        incoming = [position[(u, vertex)] for u in adjacency[vertex]]
        points.append(
            tuple(sum(vector[index] for index in incoming) for vector in vectors)
        )
    first = min(range(len(points)), key=lambda i: (points[i], i))
    centres = [points[first]]
    while len(centres) < 4:
        index = max(
            range(len(points)),
            key=lambda i: min(
                sum((points[i][axis] - centre[axis]) ** 2 for axis in range(3))
                for centre in centres
            ),
        )
        centres.append(points[index])
    labels = [0] * len(points)
    for _ in range(20):
        labels = [
            min(
                range(4),
                key=lambda colour: (
                    sum(
                        (point[axis] - centres[colour][axis]) ** 2
                        for axis in range(3)
                    ),
                    colour,
                ),
            )
            for point in points
        ]
        updated = []
        for colour in range(4):
            cluster = [points[i] for i, label in enumerate(labels) if label == colour]
            if not cluster:
                updated.append(centres[colour])
            else:
                updated.append(
                    tuple(
                        sum(point[axis] for point in cluster) / len(cluster)
                        for axis in range(3)
                    )
                )
        if updated == centres:
            break
        centres = updated
    return _canonicalize_colours(labels, inst["anchor_neighbor"]), operations


def _dsatur_attack(inst: dict, node_budget: int) -> tuple[str | None, int]:
    """Exact four-colour DSATUR/DPLL with a declared node budget."""
    adjacency = _undirected_adjacency(inst["n"], inst["base_arcs"])
    n = inst["n"]
    anchor = inst["anchor_neighbor"]
    colours = [-1] * n
    masks = [0] * n
    colours[0] = 0
    colours[anchor] = 1
    for vertex in adjacency[0]:
        if colours[vertex] < 0:
            masks[vertex] |= 1
    for vertex in adjacency[anchor]:
        if colours[vertex] < 0:
            masks[vertex] |= 2
    nodes = 0

    def search(left: int) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return None
        if left == 0:
            return colours[:]
        vertex = max(
            (u for u in range(n) if colours[u] < 0),
            key=lambda u: (masks[u].bit_count(), len(adjacency[u]), -u),
        )
        available = (~masks[vertex]) & 15
        for colour in range(4):
            bit = 1 << colour
            if not available & bit:
                continue
            colours[vertex] = colour
            changed: list[tuple[int, int]] = []
            impossible = False
            for neighbour in adjacency[vertex]:
                if colours[neighbour] < 0:
                    old = masks[neighbour]
                    new = old | bit
                    if new != old:
                        masks[neighbour] = new
                        changed.append((neighbour, old))
                        if new == 15:
                            impossible = True
            if not impossible:
                result = search(left - 1)
                if result is not None:
                    return result
            for neighbour, old in changed:
                masks[neighbour] = old
            colours[vertex] = -1
            if nodes > node_budget:
                return None
        return None

    result = search(n - 2)
    if result is None:
        return None, nodes
    return _canonicalize_colours(result, anchor), nodes


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
        "generation_route": "inverse generation plus paper-licensed transformation",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping)
    answer = inst["answer"]
    anchor = inst["anchor_neighbor"]
    edge_u, edge_v = next(
        (u, v)
        for u, v in inst["base_arcs"]
        if u not in (0, anchor) and v not in (0, anchor)
    )
    duplicate = list(answer)
    duplicate[edge_v] = duplicate[edge_u]
    swapped = list(answer)
    swapped[0], swapped[anchor] = swapped[anchor], swapped[0]
    corruptions = {
        "empty": "",
        "drop_one": answer[:-1],
        "swap_normalizers": "".join(swapped),
        "duplicate_across_arc": "".join(duplicate),
        "out_of_range": answer[:-1] + "5",
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = reason
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "I propagated the port constraints and checked all short paths.\n"
        "```text\n<answer>" + answer + "</answer>\n```\n"
        "The word is in increasing gadget order."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>12x4</answer>") is None
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
        "prior": "uniform four-colour words with both stated symmetries fixed",
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
    baseline_solved = bool(
        baseline_answer is not None and verify(baseline_inst, baseline_answer)[0]
    )
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
        "random_restart_min_conflicts_256x5000",
        "nonbacktracking_spectral_clustering",
        "exact_dsatur_dpll_200k_nodes",
    ]
    attacks = {
        name: {"successes": 0, "attempts": len(attack_seeds)}
        for name in attack_names
    }
    attack_costs = {name: 0 for name in attack_names}
    for seed in attack_seeds:
        current = make_instance(seed=seed, **shipping)
        candidates: dict[str, str | None] = {}
        candidates[attack_names[0]] = _degree_order_attack(current)
        candidates[attack_names[1]] = _greedy_saturation_attack(current)
        candidate, operations = _min_conflicts_attack(
            current,
            random.Random(seed ^ 0xA5A5A5A5),
            restarts=256,
            steps=5_000,
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
        "domain_standard_attack": "exact_dsatur_dpll_200k_nodes",
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
        "doubled_oriented_vertices": doubled["oriented_vertices"],
        "doubled_additional_arcs": len(doubled["base_arcs"]),
        "escalated_params": escalated,
    }

    invariant_trials = 0
    carried_trials = 0
    original_keys = []
    for seed in range(20):
        small = make_instance(
            n=32, regular_degree=6, switch_rounds=8, seed=5000 + seed
        )
        original_key = canonical_key(small)
        original_keys.append(original_key)
        rng = random.Random(9000 + seed)
        permutation = list(range(small["n"]))
        rng.shuffle(permutation)
        arc_order = list(range(len(small["base_arcs"])))
        rng.shuffle(arc_order)
        transformed = _transform_instance(small, permutation, arc_order)
        assert canonical_key(transformed) == original_key
        invariant_trials += 1
        ok, reason = verify(transformed, transformed["answer"])
        assert ok, reason
        carried_trials += 1
        # Each extra arc joins a source port to a sink port.  Reversing any
        # subset swaps which endpoint is the source gadget but preserves the
        # sole port inequality, so exercise independent (not merely global)
        # orientation changes as well as vertex and list permutations.
        reversed_arcs = dict(transformed)
        reversed_arcs["base_arcs"] = [
            ([v, u] if rng.randrange(2) else [u, v])
            for u, v in transformed["base_arcs"]
        ]
        assert canonical_key(reversed_arcs) == original_key
        invariant_trials += 1
        ok, reason = verify(reversed_arcs, transformed["answer"])
        assert ok, reason
        carried_trials += 1
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
        "key_kind": "underlying local/common-neighbour constraint invariant, not seed or render hash",
    }

    answer_chars = len(json.dumps(inst["answer"]))
    answer_atoms = _answer_atoms(inst["answer"])
    answer_tokens = answer_atoms + 2
    intended_operations = inst["n"]
    within_caps = (
        answer_chars <= 2_000
        and answer_atoms <= 256
        and intended_operations <= 300
    )
    hinted_still_hardened = _ORACLE_EVIDENCE["hinted_verdict"] == "hardened"
    arms = {
        key: dict(_ORACLE_EVIDENCE[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
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
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
