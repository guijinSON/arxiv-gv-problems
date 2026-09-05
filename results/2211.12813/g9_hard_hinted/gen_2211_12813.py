"""Verified Track-B generator for arXiv:2211.12813.

The instances are shuffled Cartesian products of a complete hypergraph and an
r-uniform star-hypergraph.  The planted L(2,1)-labeling is the diagonal
construction behind Theorem 4.2, written as two Chinese-remainder schedules.
It is generated before vertex relabeling and carried through the relabeling;
``make_instance`` never solves the emitted instance.
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
try:  # The family is integer-combinatorial; gvlib is optional here.
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - standard-library fallback is complete
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite hypergraph",
        "Cartesian product of hypergraphs",
        "L(2,1)-vertex labeling",
    ],
    "verification_operations": [
        "exact hyperedge co-membership",
        "exact graph-distance-two test in the 2-section",
        "integer color-difference comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The two hyperedge sizes expose hidden Cartesian coordinates, and the "
        "noncentral product blocks split into diagonal distance-three color "
        "classes; without that decomposition one faces a large exact labeling CSP."
    ),
    "hardness_basis": (
        "Track B: incidence-matrix Cartesian-factor recovery followed by the "
        "Theorem 4.2 diagonal construction is polynomial, O(V^3+V^2E); its "
        "measured shipping wall time and exact comparison count are reported in "
        "G6, while the compact CRT route uses at most 2nr exact modular operations "
        "once the factors are seen and must be executed without code or a CSP solver."
    ),
    "max_answer_tokens": 250,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "min_star_size": 6, "max_star_size": 6},
    "easy": {
        "n": 11, "min_star_size": 20, "max_star_size": 23,
        "max_rank": 13, "min_petals": 7, "decoy_edges": 8,
    },
    "medium": {
        "n": 13, "min_star_size": 18, "max_star_size": 19,
        "max_rank": 11, "min_petals": 7, "decoy_edges": 10,
    },
    "hard": {
        "n": 15, "min_star_size": 14, "max_star_size": 17,
        "max_rank": 10, "min_petals": 6, "decoy_edges": 12,
    },
}
SHIPPING_DIFFICULTY = "hard"
DIFFICULTY = {"hard": DIFFICULTY["hard"]}

STRUCTURAL_HINT: str = (
    "The two hyperedge sizes expose Cartesian coordinates whose noncentral "
    "blocks contain diagonal classes at mutual distance three."
)
PLACEBO_HINT: str = (
    "The vertex names and edge order are arbitrary, so keep the indexing "
    "consistent while checking every required color difference."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A normalized integer L(2,1)-labeling: exactly V entries in displayed "
        "vertex order, every entry in the inclusive interval [0,B], with at "
        "least one zero."
    ),
    "bounds": {
        "entries": "V (instance dependent, at most 256 at every shipping/escalated level)",
        "minimum_color": 0,
        "maximum_color": "B=n*r-1 (instance dependent)",
    },
}

# Filled after the script-owned oracle runs.  Pending evidence deliberately
# keeps G9 from passing until real transcripts exist.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES = r"""
Definition. Section 1 defines an L(h,k)-coloring of a hypergraph; Lemma 2.4
identifies it exactly with the same labeling problem on the 2-section. Section
4, Definition 4.1 fixes the Cartesian product used here. A complete
hypergraph H_n is represented by its one n-vertex edge, and K^r_{c,m} has c
central vertices and m r-edges sharing that center.

Step-0 algorithm check. The prior planted-random-hyperedge idea cannot support
Track A: the paper contains no distributional hardness theorem. Track A would
also be dishonest for the family built here because Theorem 4.2 explicitly
constructs an L(2,1)-labeling of K^r_{c,m} square H_n when m<n. This module is
therefore Track B. Its reference algorithm constructs the full 2-section and
distance-two constraint matrix, recognizes the two incidence factors, and
implements the theorem's diagonal classes in O(V^3+V^2E). The self-test records
the measured operation count and wall time. In the restricted coprime regime,
the compact route is two CRT schedules: central singleton classes are indexed
by residues modulo c and n, while noncentral diagonal classes are indexed by
residues modulo r-c and n.

Generation. The parameters c,m,r and n are sampled first with m<n,
gcd(c,n)=gcd(r-c,n)=1, and c,r-c>=2. Canonical product coordinates and the CRT
labeling are then constructed. A small set of random 3-edges is accepted only
when this already-held certificate remains valid; this inverse-generated
augmentation supplies non-isomorphic instances and tighter constraints without
searching for a witness. Only afterward are vertex names, edge order and
within-edge order independently shuffled, with the certificate carried through
the permutation. No factor recovery is used by make_instance.

Attack handling. Vertex incidence degree reveals the central rows but not the
diagonal schedule, so the degree/outlier coloring fails. Numeric-order greedy,
random-order greedy restarts, and the obvious vertex-name cyclic ansatz are
tested across eight independently shuffled shipping instances. The reference
factor-recovery algorithm is reported separately, as Track B requires.

Canonicalization. Vertex relabeling and both edge orderings are the presentation
symmetries applied by the generator. The key combines the incidence-recovered
tuple (n,c,m,r) with multisets of vertex incidence signatures and pairwise edge
intersection signatures. It never uses the seed or rendered text. This is a
strong cheap invariant, not a complete hypergraph-isomorphism algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _parameter_catalog(n: int, minimum: int, maximum: int,
                       max_rank: int | None = None,
                       min_petals: int = 2) -> list[tuple[int, int, int, int]]:
    """Return (c,m,d,S), where d=r-c and S is the star's order."""
    out = []
    for c in range(2, maximum + 1):
        if math.gcd(c, n) != 1:
            continue
        for d in range(2, maximum + 1):
            if (math.gcd(d, n) != 1 or c + d == n
                    or (max_rank is not None and c + d > max_rank)):
                continue
            for m in range(max(2, min_petals), n):
                star_size = c + m * d
                if minimum <= star_size <= maximum:
                    out.append((c, m, d, star_size))
    return out


def _crt_pair(a: int, mod_a: int, b: int, mod_b: int) -> int:
    """The unique x in [0,mod_a*mod_b) with the two requested residues."""
    if math.gcd(mod_a, mod_b) != 1:
        raise ValueError("CRT moduli must be coprime")
    # The moduli in shipped instances are small.  This direct form is exact,
    # transparent, and counts as one compact-route modular lookup.
    for value in range(a % mod_a, mod_a * mod_b, mod_a):
        if value % mod_b == b % mod_b:
            return value
    raise AssertionError("coprime CRT system had no solution")


def _canonical_product(n: int, c: int, m: int, d: int) -> tuple[list[list[int]], list[int]]:
    """Construct product edges and the known diagonal certificate, without search."""
    vertices: list[tuple] = []
    for a in range(c):
        for column in range(n):
            vertices.append(("C", a, column))
    for h in range(d):
        for petal in range(m):
            for column in range(n):
                vertices.append(("P", h, petal, column))
    index = {vertex: i for i, vertex in enumerate(vertices)}

    edges: list[list[int]] = []
    # Copies of H_n: one complete-factor edge through every star vertex.
    for a in range(c):
        edges.append([index[("C", a, column)] for column in range(n)])
    for h in range(d):
        for petal in range(m):
            edges.append([
                index[("P", h, petal, column)] for column in range(n)
            ])
    # Copies of K^r_{c,m}: m star edges in every complete-factor column.
    for column in range(n):
        for petal in range(m):
            edge = [index[("C", a, column)] for a in range(c)]
            edge.extend(index[("P", h, petal, column)] for h in range(d))
            edges.append(edge)

    colors = [0] * len(vertices)
    for a in range(c):
        for column in range(n):
            colors[index[("C", a, column)]] = _crt_pair(a, c, column, n)
    offset = c * n
    for h in range(d):
        for petal in range(m):
            for column in range(n):
                diagonal = (column - petal) % n
                colors[index[("P", h, petal, column)]] = (
                    offset + _crt_pair(h, d, diagonal, n)
                )
    return edges, colors


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Build a shuffled native product and carry its certificate by relabeling."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    minimum = int(params.get("min_star_size", 6))
    maximum = int(params.get("max_star_size", minimum))
    max_rank = params.get("max_rank")
    max_rank = None if max_rank is None else int(max_rank)
    min_petals = int(params.get("min_petals", 2))
    if minimum < 6 or maximum < minimum:
        raise ValueError("invalid star-size interval")
    rng = random.Random(seed)
    catalog = _parameter_catalog(n, minimum, maximum, max_rank, min_petals)
    if not catalog:
        raise ValueError("no admissible coprime product parameters in this interval")
    c, m, d, star_size = rng.choice(catalog)
    r = c + d
    edges, canonical_answer = _canonical_product(n, c, m, d)
    vertex_count = n * star_size
    max_color = n * r - 1

    # Inverse-generated crowding: add random 3-edges only when the certificate
    # already in hand remains valid.  These are genuine non-isomorphic instance
    # variations, while sizes 3, n, and r keep the theorem's product core
    # mechanically recognizable.  This is certificate filtering, not witness
    # search: the answer was fixed before the first candidate edge was drawn.
    requested_decoys = int(params.get("decoy_edges", 0))
    if requested_decoys < 0 or requested_decoys >= n:
        raise ValueError("decoy_edges must lie in [0,n)")
    edge_sets = {frozenset(edge) for edge in edges}
    attempts = 0
    while len(edges) < star_size + n * m + requested_decoys:
        attempts += 1
        if attempts > 50_000:
            raise ValueError("could not sample enough certificate-compatible decoy edges")
        candidate = frozenset(rng.sample(range(vertex_count), 3))
        if candidate in edge_sets:
            continue
        # Preserve simplicity: no hyperedge may contain another.
        if any(candidate <= existing or existing <= candidate for existing in edge_sets):
            continue
        trial_edges = edges + [sorted(candidate)]
        trial = {
            "n_vertices": vertex_count,
            "edges": trial_edges,
            "max_color": max_color,
        }
        if not verify(trial, canonical_answer)[0]:
            continue
        edges.append(sorted(candidate))
        edge_sets.add(candidate)

    # perm[old] is the displayed name of canonical vertex old.
    perm = list(range(vertex_count))
    rng.shuffle(perm)
    shuffled_edges = []
    for edge in edges:
        shown = [perm[v] for v in edge]
        rng.shuffle(shown)
        shuffled_edges.append(shown)
    rng.shuffle(shuffled_edges)
    answer = [0] * vertex_count
    for old, color in enumerate(canonical_answer):
        answer[perm[old]] = color

    return {
        "n_vertices": vertex_count,
        "edges": shuffled_edges,
        "max_color": max_color,
        "answer": answer,
        # Construction metadata is not needed by render or verify.  It is kept
        # for auditability only; reference attacks recover it from incidence.
        "construction": {
            "n": n, "c": c, "m": m, "r": r,
            "decoy_edges": requested_decoys,
        },
    }


def render(inst: dict) -> str:
    """Render the complete standalone witness problem and exact output format."""
    edge_lines = "\n".join(
        f"  e{number}: " + " ".join(str(v) for v in edge)
        for number, edge in enumerate(inst["edges"])
    )
    statement = f"""Distance-constrained labeling of a hypergraph

A finite hypergraph has vertices 0,1,...,{inst['n_vertices'] - 1}.  Each line
below is one hyperedge; order within an edge and the order of the edge lines
have no meaning.

{edge_lines}

Two distinct vertices are adjacent when some displayed hyperedge contains both.
Two distinct nonadjacent vertices are at distance two when they have a common
adjacent vertex.  An L(2,1)-labeling assigns an integer color to every vertex so
that adjacent vertices' colors differ by at least 2, while vertices at distance
two receive different colors.

Find an L(2,1)-labeling using only colors in the inclusive interval
0,...,{inst['max_color']}.  Normalize it so that at least one vertex has color 0.
Give exactly {inst['n_vertices']} integers in vertex order: entry i is the color
of vertex i.  Repeats are allowed only when the distance conditions permit them.

Give your final answer inside <answer></answer> tags, as one comma-separated
list of exactly {inst['n_vertices']} base-10 integers with no brackets.
Example format: <answer>0, 2, 4</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the tagged comma-separated labeling, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text|python)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return []
    pieces = body.split(",")
    values = []
    for piece in pieces:
        token = piece.strip()
        if not re.fullmatch(r"[+-]?\d+", token):
            return None
        try:
            values.append(int(token))
        except (TypeError, ValueError, OverflowError):
            return None
    return values


def _adjacency(inst: dict) -> list[set[int]]:
    count = inst["n_vertices"]
    adjacency = [set() for _ in range(count)]
    for edge in inst["edges"]:
        for i, u in enumerate(edge):
            for v in edge[i + 1:]:
                adjacency[u].add(v)
                adjacency[v].add(u)
    return adjacency


def _near_two(adjacency: list[set[int]]) -> list[set[int]]:
    out = []
    for vertex, neighbors in enumerate(adjacency):
        near = set(neighbors)
        for middle in neighbors:
            near.update(adjacency[middle])
        near.discard(vertex)
        out.append(near)
    return out


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized valid labeling; never consult inst['answer']."""
    expected = inst.get("n_vertices")
    if not isinstance(answer, list):
        return False, "answer must be a list of integers"
    if len(answer) != expected:
        return False, f"expected {expected} entries, got {len(answer)}"
    if any(not isinstance(value, int) or isinstance(value, bool) for value in answer):
        return False, "every color must be an integer"
    bound = inst.get("max_color")
    for vertex, value in enumerate(answer):
        if value < 0 or value > bound:
            return False, f"vertex {vertex} color {value} is outside [0,{bound}]"
    if min(answer, default=1) != 0:
        return False, "the labeling is not normalized: no vertex has color 0"

    adjacency = _adjacency(inst)
    # Check the more selective adjacency constraints first; random candidates
    # usually fail early, keeping the 200k-sample gate inexpensive.
    for u, neighbors in enumerate(adjacency):
        for v in neighbors:
            if v > u and abs(answer[u] - answer[v]) < 2:
                return False, (
                    f"adjacent vertices {u} and {v} have colors differing by less than 2"
                )
    for u, neighbors in enumerate(adjacency):
        for middle in neighbors:
            for v in adjacency[middle]:
                if v > u and v not in neighbors and answer[u] == answer[v]:
                    return False, (
                        f"distance-two vertices {u} and {v} have the same color"
                    )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the bounded language, conditioned on its stated zero."""
    count = inst["n_vertices"]
    bound = inst["max_color"]
    while True:
        candidate = [rng.randint(0, bound) for _ in range(count)]
        if 0 in candidate:
            return candidate


def search_space(inst: dict) -> int:
    """Exact size of all bounded vectors containing at least one zero."""
    count = inst["n_vertices"]
    bound = inst["max_color"]
    return (bound + 1) ** count - bound ** count


def enumerate_all(inst: dict) -> int | None:
    """Enumerate only genuinely tiny languages; supported instances exceed cap."""
    if search_space(inst) > 1_000_000:
        return None
    # No supported instance reaches this branch.
    total = 0
    count = inst["n_vertices"]
    bound = inst["max_color"]
    candidate = [0] * count

    def visit(position: int) -> None:
        nonlocal total
        if position == count:
            if verify(inst, candidate)[0]:
                total += 1
            return
        for value in range(bound + 1):
            candidate[position] = value
            visit(position + 1)

    visit(0)
    return total


def _base_edge_families(inst: dict, counter: dict[str, int] | None = None
                        ) -> tuple[int, list[set[int]], int, list[set[int]]]:
    """Recover the row and star edge families while ignoring size-3 decoys."""
    if counter is None:
        counter = {"operations": 0}
    vertex_count = inst["n_vertices"]
    edges = [set(edge) for edge in inst["edges"]]
    sizes = sorted(set(len(edge) for edge in edges))
    counter["operations"] += sum(len(edge) for edge in edges)
    candidates = []
    for size in sizes:
        group = [edge for edge in edges if len(edge) == size]
        counts = [0] * vertex_count
        for edge in group:
            for vertex in edge:
                counts[vertex] += 1
                counter["operations"] += 1
        if all(value == 1 for value in counts):
            candidates.append((size, group))
        counter["operations"] += vertex_count
    if len(candidates) != 1:
        raise ValueError("incidence does not expose a unique partition edge family")
    n, rows = candidates[0]
    star_candidates = []
    for size in sizes:
        if size == n or size < 4:
            continue
        group = [edge for edge in edges if len(edge) == size]
        if not group or len(group) % n:
            continue
        m = len(group) // n
        if m < 2:
            continue
        incidence = [0] * vertex_count
        for edge in group:
            for vertex in edge:
                incidence[vertex] += 1
                counter["operations"] += 1
        center_vertices = sum(value == m for value in incidence)
        if center_vertices % n:
            continue
        c = center_vertices // n
        if (c >= 2 and size > c
                and all(value in (1, m) for value in incidence)
                and len(rows) == c + m * (size - c)):
            star_candidates.append((size, group))
    if len(star_candidates) != 1:
        raise ValueError("incidence does not expose a unique star edge family")
    r, star_edges = star_candidates[0]
    return n, rows, r, star_edges


def _recover_parameters(inst: dict, counter: dict[str, int] | None = None) -> tuple[int, int, int, int]:
    """Recover (n,c,m,r) solely from incidence, invariant under relabeling."""
    if counter is None:
        counter = {"operations": 0}
    n, rows, r, star_edges = _base_edge_families(inst, counter)
    m = len(star_edges) // n
    incidence = [0] * inst["n_vertices"]
    for edge in star_edges:
        for vertex in edge:
            incidence[vertex] += 1
            counter["operations"] += 1
    c = sum(value == m for value in incidence) // n
    return n, c, m, r


def canonical_key(inst: dict) -> str:
    """Hash strong incidence invariants, never the seed or rendered text."""
    params = _recover_parameters(inst)
    sizes = sorted(set(len(edge) for edge in inst["edges"]))
    vertex_signatures = []
    for vertex in range(inst["n_vertices"]):
        vertex_signatures.append(tuple(
            sum(vertex in edge for edge in inst["edges"] if len(edge) == size)
            for size in sizes
        ))
    intersection_signatures = []
    edge_sets = [set(edge) for edge in inst["edges"]]
    for i, left in enumerate(edge_sets):
        for right in edge_sets[i + 1:]:
            intersection_signatures.append((
                min(len(left), len(right)), max(len(left), len(right)),
                len(left & right),
            ))
    payload = json.dumps([
        params,
        sizes,
        sorted(vertex_signatures),
        sorted(intersection_signatures),
    ], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


_ESCALATION_LEVELS = [
    (11, 20, 23, 13),
    (13, 18, 19, 11),
    (17, 14, 15, 8),
    (19, 12, 13, 7),
    (23, 10, 11, 6),
    (29, 8, 8, 5),
    (31, 8, 8, 4),
    (37, 6, 6, 4),
]


def escalate(params: dict) -> dict | str | None:
    """Increase the complete factor while holding the answer near 256 entries."""
    current = int(params.get("n", 3))
    for n, minimum, maximum, max_rank in _ESCALATION_LEVELS:
        if n > current:
            return {
                "n": n, "min_star_size": minimum,
                "max_star_size": maximum, "max_rank": max_rank,
            }
    return "cap_bound"


def _recover_coordinates(inst: dict, counter: dict[str, int] | None = None) -> tuple[dict[int, tuple], tuple[int, int, int, int]]:
    """Incidence-based factor recovery used only by the reference algorithm."""
    if counter is None:
        counter = {"operations": 0}
    n, rows, r, star_edges = _base_edge_families(inst, counter)
    m = len(star_edges) // n
    incidence = [0] * inst["n_vertices"]
    for edge in star_edges:
        for vertex in edge:
            incidence[vertex] += 1
            counter["operations"] += 1
    c = sum(value == m for value in incidence) // n
    d = r - c
    rows.sort(key=lambda edge: tuple(sorted(edge)))
    row_of = {}
    for row_index, row in enumerate(rows):
        for vertex in row:
            row_of[vertex] = row_index
            counter["operations"] += 1
    incident_star: list[list[int]] = [[] for _ in range(inst["n_vertices"])]
    for edge_index, edge in enumerate(star_edges):
        for vertex in edge:
            incident_star[vertex].append(edge_index)
            counter["operations"] += 1
    center_rows = [
        i for i, row in enumerate(rows)
        if all(len(incident_star[vertex]) == m for vertex in row)
    ]
    noncenter_rows = [i for i in range(len(rows)) if i not in set(center_rows)]
    center_rows.sort(key=lambda i: tuple(sorted(rows[i])))
    if len(center_rows) != c:
        raise ValueError("factor recovery found the wrong number of center rows")

    first_center = center_rows[0]
    column_vertices = sorted(rows[first_center])
    column_of_anchor = {vertex: i for i, vertex in enumerate(column_vertices)}
    edge_column = {}
    for edge_index, edge in enumerate(star_edges):
        anchors = edge & rows[first_center]
        counter["operations"] += len(rows[first_center])
        if len(anchors) != 1:
            raise ValueError("star edge has malformed center intersection")
        edge_column[edge_index] = column_of_anchor[next(iter(anchors))]

    # Rows co-occurring in a star edge form exactly one petal component of d rows.
    row_neighbors = {row: set() for row in noncenter_rows}
    noncenter_set = set(noncenter_rows)
    for edge in star_edges:
        members = sorted({row_of[v] for v in edge if row_of[v] in noncenter_set})
        for i, left in enumerate(members):
            row_neighbors[left].update(members[:i] + members[i + 1:])
            counter["operations"] += len(members) - 1
    components = []
    unseen = set(noncenter_rows)
    while unseen:
        start = min(unseen)
        stack = [start]
        component = set()
        while stack:
            row = stack.pop()
            if row in component:
                continue
            component.add(row)
            unseen.discard(row)
            stack.extend(row_neighbors[row] - component)
            counter["operations"] += len(row_neighbors[row])
        components.append(sorted(component, key=lambda i: tuple(sorted(rows[i]))))
    components.sort(key=lambda comp: tuple(tuple(sorted(rows[i])) for i in comp))
    if len(components) != m or any(len(component) != d for component in components):
        raise ValueError("noncentral rows do not split into star petals")

    coordinates: dict[int, tuple] = {}
    for a, row_index in enumerate(center_rows):
        for vertex in rows[row_index]:
            edge_index = incident_star[vertex][0]
            coordinates[vertex] = ("C", a, edge_column[edge_index])
            counter["operations"] += 1
    for petal, component in enumerate(components):
        for h, row_index in enumerate(component):
            for vertex in rows[row_index]:
                edge_index = incident_star[vertex][0]
                coordinates[vertex] = ("P", h, petal, edge_column[edge_index])
                counter["operations"] += 1
    if len(coordinates) != inst["n_vertices"]:
        raise ValueError("factor recovery omitted vertices")
    return coordinates, (n, c, m, r)


def _label_coordinates(coordinates: dict[int, tuple], params: tuple[int, int, int, int]) -> list[int]:
    n, c, _m, r = params
    d = r - c
    answer = [0] * len(coordinates)
    for vertex, coordinate in coordinates.items():
        if coordinate[0] == "C":
            _, a, column = coordinate
            answer[vertex] = _crt_pair(a, c, column, n)
        else:
            _, h, petal, column = coordinate
            answer[vertex] = c * n + _crt_pair(
                h, d, (column - petal) % n, n
            )
    return answer


def _reference_algorithm(inst: dict) -> tuple[list[int], dict[str, int]]:
    """Mechanical Track-B route: full constraints, then factor and diagonalize."""
    counter = {"operations": 0, "pair_edge_tests": 0, "two_step_tests": 0}
    count = inst["n_vertices"]
    edge_sets = [set(edge) for edge in inst["edges"]]
    adjacency = [[False] * count for _ in range(count)]
    for u in range(count):
        for v in range(u + 1, count):
            linked = False
            for edge in edge_sets:
                counter["pair_edge_tests"] += 1
                counter["operations"] += 1
                if u in edge and v in edge:
                    linked = True
                    break
            adjacency[u][v] = adjacency[v][u] = linked
    # A standard CSP front end materializes all distance-two disequalities.
    for u in range(count):
        for v in range(u + 1, count):
            if adjacency[u][v]:
                continue
            for middle in range(count):
                counter["two_step_tests"] += 1
                counter["operations"] += 1
                if adjacency[u][middle] and adjacency[middle][v]:
                    break
    coordinates, params = _recover_coordinates(inst, counter)
    answer = _label_coordinates(coordinates, params)
    return answer, counter


def _constraints(inst: dict) -> tuple[list[set[int]], list[set[int]]]:
    adjacency = _adjacency(inst)
    return adjacency, _near_two(adjacency)


def _greedy_candidate(inst: dict, order: list[int]) -> list[int] | None:
    adjacency, near_two = _constraints(inst)
    colors = [-1] * inst["n_vertices"]
    for vertex in order:
        chosen = None
        for color in range(inst["max_color"] + 1):
            if any(colors[u] == color for u in near_two[vertex] if colors[u] >= 0):
                continue
            if any(
                abs(colors[u] - color) < 2
                for u in adjacency[vertex] if colors[u] >= 0
            ):
                continue
            chosen = color
            break
        if chosen is None:
            return None
        colors[vertex] = chosen
    minimum = min(colors)
    return [color - minimum for color in colors]


def _attack_results(inst: dict, seed: int) -> dict[str, bool]:
    count = inst["n_vertices"]
    bound = inst["max_color"]
    incidences = [0] * count
    size_sums = [0] * count
    for edge in inst["edges"]:
        for vertex in edge:
            incidences[vertex] += 1
            size_sums[vertex] += len(edge)
    ordered = sorted(range(count), key=lambda v: (-incidences[v], -size_sums[v], v))
    outlier = [0] * count
    for rank, vertex in enumerate(ordered):
        outlier[vertex] = rank % (bound + 1)
    outlier_ok = verify(inst, outlier)[0]

    greedy = _greedy_candidate(inst, list(range(count)))
    greedy_ok = greedy is not None and verify(inst, greedy)[0]

    restart_ok = False
    rng = random.Random(seed ^ 0x221112813)
    for _ in range(64):
        order = list(range(count))
        rng.shuffle(order)
        candidate = _greedy_candidate(inst, order)
        if candidate is not None and verify(inst, candidate)[0]:
            restart_ok = True
            break

    cyclic = [vertex % (bound + 1) for vertex in range(count)]
    cyclic_ok = verify(inst, cyclic)[0]
    return {
        "outlier_incidence_degree_order": outlier_ok,
        "greedy_numeric_vertex_order": greedy_ok,
        "random_restart_64_greedy_orders": restart_ok,
        "by_hand_vertex_name_cyclic_ansatz": cyclic_ok,
    }


def _relabel_instance(inst: dict, perm: list[int], reverse_edges: bool = False) -> dict:
    out = {key: value for key, value in inst.items() if key not in ("edges", "answer")}
    edges = [[perm[v] for v in edge] for edge in inst["edges"]]
    if reverse_edges:
        edges = [list(reversed(edge)) for edge in reversed(edges)]
    out["edges"] = edges
    carried = [0] * len(perm)
    for old, new in enumerate(perm):
        carried[new] = inst["answer"][old]
    out["answer"] = carried
    return out


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run all mandatory gates and return measured, machine-readable evidence."""
    report: dict[str, object] = {}

    failures = []
    checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    answer = inst["answer"]
    # Find an actual invalid transposition instead of assuming arbitrary colors
    # differ in a way that violates this non-unique witness problem.
    swapped = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            candidate = list(answer)
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if not verify(inst, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    corruptions: dict[str, object] = {
        "drop_one": answer[:-1],
        "swap_two": swapped if swapped is not None else list(reversed(answer)),
        "duplicate": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [inst["max_color"] + 1] + answer[1:],
    }
    rejection_rows = {}
    reasons = set()
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejection_rows[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejection_rows.values())
        and len(reasons) == len(corruptions),
        "distinct_reasons": len(reasons),
        "rejections": rejection_rows,
    }

    answer_text = ", ".join(str(value) for value in answer)
    model_reply = (
        "I recovered the product coordinates and used diagonal classes.\n"
        "<answer>\n```text\n" + answer_text + "\n```\n</answer>\n"
        "The resulting labeling uses only the allowed colors."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    samples = 200_000
    hits = 0
    rng = random.Random(0x221112813)
    sample_start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            hits += 1
    sampling_wall = time.perf_counter() - sample_start
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "empirical_probability": hits / samples,
        "candidate_space": search_space(inst),
        "prior": "uniform bounded color vectors conditioned on containing color 0",
        "sampling_wall_seconds": sampling_wall,
    }

    attack_names = (
        "outlier_incidence_degree_order",
        "greedy_numeric_vertex_order",
        "random_restart_64_greedy_orders",
        "by_hand_vertex_name_cyclic_ansatz",
    )
    attack_counts = {name: 0 for name in attack_names}
    reference_attempts = 8
    reference_successes = 0
    reference_wall = 0.0
    reference_operations = 0
    reference_pair_tests = 0
    reference_two_step_tests = 0
    for seed in range(reference_attempts):
        attack_inst = make_instance(seed=10_000 + seed, **shipping)
        for name, solved in _attack_results(attack_inst, 10_000 + seed).items():
            attack_counts[name] += int(solved)
        start = time.perf_counter()
        reference_answer, counters = _reference_algorithm(attack_inst)
        reference_wall += time.perf_counter() - start
        reference_operations += counters["operations"]
        reference_pair_tests += counters["pair_edge_tests"]
        reference_two_step_tests += counters["two_step_tests"]
        reference_successes += int(verify(attack_inst, reference_answer)[0])
    attacks = {
        name: {"successes": attack_counts[name], "attempts": reference_attempts}
        for name in attack_names
    }
    reference = {
        "name": "incidence-matrix Cartesian-factor recovery plus Theorem 4.2 CRT diagonals",
        "complexity": "O(V^3+V^2E) exact incidence comparisons",
        "wall_clock_sec": reference_wall,
        "wall_clock_sec_mean": reference_wall / reference_attempts,
        "operations": reference_operations,
        "operations_mean": reference_operations // reference_attempts,
        "pair_edge_tests": reference_pair_tests,
        "two_step_tests": reference_two_step_tests,
        "solves": f"{reference_successes}/{reference_attempts}, as expected",
    }
    all_attacks_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == reference_attempts,
        "attacks": attacks,
        "reference_algorithm": reference,
    }
    report["G5_density_and_baseline"] = {
        "pass": hits / samples < 1e-6 and reference_successes == reference_attempts,
        "shipping_density_sample_count": samples,
        "shipping_valid_hits": hits,
        "shipping_observed_valid_fraction": hits / samples,
        "shipping_candidate_space": search_space(inst),
        "enumerate_all_shipping": enumerate_all(inst),
        "baseline_wall_seconds": reference_wall,
        "baseline_operations": reference_operations,
        "baseline_iterations": reference_pair_tests + reference_two_step_tests,
        "baseline_successes": reference_successes,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    # The doubled-size gate checks constructibility, not the shipping crowding
    # subregime; at n=22, m<n still holds but m>=7 is needlessly restrictive.
    doubled_params.pop("min_petals", None)
    start = time.perf_counter()
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_wall = time.perf_counter() - start
    named_sizes = [
        make_instance(seed=7, **params)["n_vertices"]
        for name, params in DIFFICULTY.items() if name != "demo"
    ]
    named_n = [params["n"] for name, params in DIFFICULTY.items() if name != "demo"]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n_vertices"] >= 2 * inst["n_vertices"] * 0.75
        and named_n == sorted(named_n)
        and len(set(named_n)) == len(named_n),
        "shipping_n": shipping["n"],
        "shipping_vertices": inst["n_vertices"],
        "doubled_n": doubled_params["n"],
        "doubled_vertices": doubled["n_vertices"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_wall,
        "named_n_values": named_n,
        "named_vertex_sizes": named_sizes,
    }

    # Select twenty genuinely different structural seeds, then apply vertex,
    # edge, within-edge, and composed presentation symmetries to every one.
    selected = []
    distinct = {}
    for preset_index, preset_params in enumerate(DIFFICULTY.values()):
        for seed in range(5_000):
            actual_seed = 20_000 + 5_000 * preset_index + seed
            key_inst = make_instance(seed=actual_seed, **preset_params)
            key = canonical_key(key_inst)
            if key not in distinct:
                distinct[key] = actual_seed
                selected.append(key_inst)
            if len(selected) == 20:
                break
        if len(selected) == 20:
            break
    invariance = 0
    real_checks = 0
    transformations = 0
    for index, key_inst in enumerate(selected):
        key = canonical_key(key_inst)
        count = key_inst["n_vertices"]
        relabel_rng = random.Random(90_000 + index)
        perm = list(range(count))
        relabel_rng.shuffle(perm)
        identity = list(range(count))
        variants = [
            _relabel_instance(key_inst, identity, reverse_edges=True),
            _relabel_instance(key_inst, perm, reverse_edges=False),
            _relabel_instance(key_inst, perm, reverse_edges=True),
        ]
        for transformed in variants:
            transformations += 1
            invariance += int(canonical_key(transformed) == key)
            real_checks += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": len(selected) == 20
        and invariance == transformations
        and real_checks == transformations,
        "invariance_checks": invariance,
        "transformations_tested": transformations,
        "real_transformation_verify_checks": real_checks,
        "distinct_unrelated_keys": len(selected),
        "unrelated_instances": len(selected),
        "symmetries": [
            "edge and within-edge reordering",
            "arbitrary vertex relabeling",
            "their composition",
        ],
    }

    sizes = []
    route_operations = []
    for seed in range(20):
        size_inst = make_instance(seed=30_000 + seed, **shipping)
        blob = json.dumps(size_inst["answer"], separators=(",", ":"))
        n0, c0, _m0, r0 = _recover_parameters(size_inst)
        sizes.append((len(blob), (len(blob) + 3) // 4, _answer_atoms(size_inst["answer"])))
        route_operations.append(2 * n0 * r0)
    answer_chars = max(row[0] for row in sizes)
    answer_tokens = max(row[1] for row in sizes)
    answer_elements = max(row[2] for row in sizes)
    intended_operations = max(route_operations)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    )
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    profile = dict(PROBLEM_PROFILE)
    profile["max_answer_tokens"] = answer_tokens
    report["problem_profile"] = profile
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
