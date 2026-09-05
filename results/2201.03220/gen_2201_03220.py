"""Verified induced-matching generator for arXiv:2201.03220.

The module inverse-generates connected cubic graphs of girth at least five.
It samples a vertex set first, makes that set induce a perfect matching, and
then fills every remaining degree with a random configuration.  Thus the
requested induced matching is known without solving the generated graph.

Only the Python standard library is used.  Importing this file performs no
I/O, network access, or printing.
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


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "connected cubic graph of girth at least five",
        "vertex subset inducing a 1-regular graph",
    ],
    "verification_operations": [
        "exact vertex-range and cardinality checks",
        "exact adjacency lookup",
        "integer induced-degree counting",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Use the near-saturated target and the uniform radius-two neighborhoods "
        "to propagate compatible matched pairs globally; local edge scores leave "
        "every planted edge tied with its decoys."
    ),
    "hardness_basis": (
        "Track A: Section 1 cites NP-hardness already for planar 3-regular "
        "graphs, while Theorem 5 gives only an O(1.2630^n)-time polynomial-space "
        "exact algorithm for subcubic graphs; shipping uses connected random "
        "cubic girth-five graphs with n=120, a planted 68-vertex (34-edge) "
        "induced matching, and the Cameron line-graph-square branch-and-bound "
        "baseline exhausts 1,000,000 nodes on each of eight construction seeds."
    ),
    "max_answer_tokens": 58,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 10, "selected_vertices": 6},
    "easy": {"n": 120, "selected_vertices": 68},
    "medium": {"n": 160, "selected_vertices": 92},
    "hard": {"n": 200, "selected_vertices": 116},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "At girth five every edge has the same radius-two conflict count, so useful "
    "choices must be propagated through the near-saturated packing globally."
)
PLACEBO_HINT: str = (
    "Keep the zero-based vertex labels and the required output cardinality "
    "consistent while checking the displayed graph."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly selected_vertices distinct vertex labels in "
        "strictly increasing order, each in 0,...,n-1."
    ),
    "bounds": {
        "length": "selected_vertices",
        "label_min": 0,
        "label_max": "n-1",
        "order": "strictly increasing",
        "candidate_count": "binomial(n, selected_vertices)",
        "shipping_length": 68,
    },
}

NOTES: str = r"""
Definition and certificate. Section 1 defines Maximum Induced Matching as
finding a maximum vertex subset S for which every vertex of G[S] has degree
exactly one; the size-k search form used here is its witness-producing decision
version. The answer is S itself, not a surrogate. Verification directly counts
degrees in the induced graph and does not consult the planted answer.

Step 0. Section 1 identifies polynomial-time cases including trees, interval
graphs, chordal graphs, and circular-arc graphs, and cites NP-hardness for
planar 3-regular graphs. Theorem 4 gives the older O(1.3139^n) route through
Maximum Independent Set in the line graph of the graph square. Theorem 5 and
Section 4 give the paper's O(1.2630^n), polynomial-space bisection/branching
algorithm. Thus a polynomial certificate-producing algorithm does not make
the native general problem easy, and this module declares Track A rather than
hiding a known polynomial reference method. Worst-case hardness does not prove
this planted distribution hard; the measured adversary panel is the additional
distributional evidence and is reported with that limitation.

Inverse generation. First sample the selected class S. Pair all vertices of S,
giving each selected vertex its unique selected neighbor. Give every selected
vertex two random neighbors outside S, then pair the unused outside stubs. The
configuration is accepted only when it is simple, connected, cubic, and has no
3- or 4-cycle. Finally relabel every vertex uniformly and shuffle the edge list.
The stored S is consequently a valid induced-matching witness by construction;
no search over candidate witnesses occurs during generation.

Attack hardening. The earlier balanced construction put one internal neighbor
in both latent classes. A randomized minimum-conflict greedy found a target on
every seed and that version was discarded. The shipping construction raises
the selected fraction near the stub-capacity boundary. Girth at least five
makes every edge conflict with exactly twelve other edges, removing the planted
edge's simplest local signature. The panel tests radius-three outliers,
lexicographic greedy packing, 256 randomized minimum-conflict restarts, a
smallest-eigenvector-style spectral rounding, and the paper-licensed Cameron
line-graph-square exact formulation with a one-million-node branch cap.

Canonicalization. General cubic-graph isomorphism is not solved. The key starts
from each vertex's complete distance histogram, performs stable color
refinement, and hashes the resulting color/neighbor-color incidence multiset.
It is invariant under vertex relabeling, endpoint reversal, and edge ordering,
and distinguishes all audited seeds, but two non-isomorphic distance-regular
graphs could theoretically collide. README.md repeats this caveat.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000
_GUESS_TRIALS = 200_000
_ATTACK_SEEDS = tuple(range(7000, 7008))
_EXACT_NODE_CAP = 1_000_000

# Replaced after the script-owned bare/hinted/placebo runs. Oracle outcomes are
# diagnostic under the current G9 rules; only the answer/operation caps gate.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 2},
    "hinted_verdict": "hardened",
}
ORACLE_EVIDENCE_SCOPE = (
    "pre-fix generator: the same parameters but before the triangle rejection "
    "predicate was corrected; exact replay requires a new funded oracle run"
)


def _validate_parameters(n: int, selected_vertices: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 10 or n % 2:
        raise ValueError("n must be an even integer at least 10")
    if (
        isinstance(selected_vertices, bool)
        or not isinstance(selected_vertices, int)
        or selected_vertices < 2
        or selected_vertices % 2
    ):
        raise ValueError("selected_vertices must be a positive even integer")
    if selected_vertices >= n:
        raise ValueError("selected_vertices must be smaller than n")
    # Selected vertices need two outside stubs apiece. The outside class has
    # three stubs per vertex, and its unused number of stubs must be pairable.
    leftover = 3 * (n - selected_vertices) - 2 * selected_vertices
    if leftover < 0 or leftover % 2:
        raise ValueError("the requested class does not satisfy the cubic stub balance")


def _adjacency_from_edges(n: int, edges: list[list[int]] | list[tuple[int, int]]):
    adjacency = [[] for _ in range(n)]
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("each edge must have two endpoints")
        u, v = edge
        if not isinstance(u, int) or not isinstance(v, int) or u == v:
            raise ValueError("invalid edge endpoint")
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError("edge endpoint out of range")
        adjacency[u].append(v)
        adjacency[v].append(u)
    return [sorted(row) for row in adjacency]


def _connected(adjacency: list[list[int]]) -> bool:
    seen = {0}
    queue = [0]
    for vertex in queue:
        for neighbor in adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen) == len(adjacency)


def _girth_at_least_five(adjacency: list[list[int]]) -> bool:
    """Detect triangles and four-cycles through radius-two collisions."""
    for vertex, neighbors in enumerate(adjacency):
        neighbor_set = set(neighbors)
        radius_two = set()
        for neighbor in neighbors:
            for other in adjacency[neighbor]:
                if other == vertex:
                    continue
                # A second neighbor of ``vertex`` closes a triangle.
                if other in neighbor_set:
                    return False
                # Two distinct length-two paths close a four-cycle.
                if other in radius_two:
                    return False
                radius_two.add(other)
    return True


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a cubic graph and a large induced matching."""
    if set(params) != {"selected_vertices"}:
        missing = "selected_vertices" not in params
        unknown = sorted(set(params) - {"selected_vertices"})
        if missing:
            raise TypeError("missing selected_vertices")
        raise TypeError("unknown parameters: " + ", ".join(unknown))
    selected_vertices = params["selected_vertices"]
    _validate_parameters(n, selected_vertices)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    selected = list(range(selected_vertices))
    outside = list(range(selected_vertices, n))

    accepted_edges = None
    for _attempt in range(100_000):
        selected_order = list(selected)
        rng.shuffle(selected_order)
        planted_edges = [
            tuple(sorted((selected_order[i], selected_order[i + 1])))
            for i in range(0, selected_vertices, 2)
        ]

        selected_stubs = [vertex for vertex in selected for _ in range(2)]
        outside_stubs = [vertex for vertex in outside for _ in range(3)]
        rng.shuffle(selected_stubs)
        rng.shuffle(outside_stubs)

        cross_count = len(selected_stubs)
        cross_edges = [
            tuple(sorted(pair))
            for pair in zip(selected_stubs, outside_stubs[:cross_count])
        ]
        remainder = outside_stubs[cross_count:]
        rng.shuffle(remainder)
        outside_edges = [
            tuple(sorted((remainder[i], remainder[i + 1])))
            for i in range(0, len(remainder), 2)
        ]
        edges = planted_edges + cross_edges + outside_edges

        if any(u == v for u, v in edges) or len(set(edges)) != len(edges):
            continue
        adjacency = _adjacency_from_edges(n, edges)
        if any(len(row) != 3 for row in adjacency):
            continue
        if not _girth_at_least_five(adjacency) or not _connected(adjacency):
            continue
        accepted_edges = edges
        break
    if accepted_edges is None:
        raise RuntimeError("could not draw a simple connected girth-five configuration")

    permutation = list(range(n))
    rng.shuffle(permutation)
    relabeled_edges = [
        tuple(sorted((permutation[u], permutation[v])))
        for u, v in accepted_edges
    ]
    rng.shuffle(relabeled_edges)
    answer = sorted(permutation[vertex] for vertex in selected)
    adjacency = _adjacency_from_edges(n, relabeled_edges)

    return {
        "family": "large induced matching in a subcubic graph",
        "n": n,
        "selected_vertices": selected_vertices,
        "matching_edges": selected_vertices // 2,
        "maximum_degree": 3,
        "girth_lower_bound": 5,
        "edges": [[u, v] for u, v in relabeled_edges],
        "adjacency": adjacency,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete native induced-matching search problem."""
    edge_rows = "\n".join(f"  {u} {v}" for u, v in inst["edges"])
    mode = os.environ.get("GV_HINT_MODE")
    hint = ""
    if mode == "structural":
        hint = "\n\nStructural hint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""LARGE INDUCED MATCHING IN A SUBCUBIC GRAPH

The graph is finite, simple, and undirected. Its vertices are the integers
0 through {inst['n'] - 1}. An edge row "u v" means that u and v are adjacent;
there are no other edges. The graph is cubic (every vertex has degree 3) and
has no cycle of length 3 or 4.

Choose exactly {inst['selected_vertices']} distinct vertices. In the subgraph
induced by the chosen vertices, every chosen vertex must have degree exactly
1. Equivalently, the chosen vertices must be the endpoints of exactly
{inst['matching_edges']} pairwise induced edges: selected edges share no
endpoint, and no graph edge joins endpoints of two different selected edges.

Edges ({len(inst['edges'])} rows, in arbitrary order):
{edge_rows}{hint}

Give your final answer inside <answer></answer> tags as one JSON array of
exactly {inst['selected_vertices']} zero-based vertex labels in strictly
increasing order. Repeats are forbidden and order is otherwise semantically
irrelevant; increasing order is the required canonical serialization.
Example format: <answer>[0, 3, 8]</answer>
Output nothing else inside the tags."""


def parse_answer(text: object) -> object | None:
    """Extract the last tagged JSON list, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            lines = lines[1:-1]
            body = "\n".join(lines).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any submitted induced vertex set; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected = inst["selected_vertices"]
    if len(answer) != expected:
        return False, f"wrong number of vertices: expected {expected}, got {len(answer)}"
    if any(isinstance(vertex, bool) or not isinstance(vertex, int) for vertex in answer):
        return False, "every vertex label must be an integer"
    if len(set(answer)) != len(answer):
        return False, "vertex labels must be distinct"
    n = inst["n"]
    if any(vertex < 0 or vertex >= n for vertex in answer):
        return False, f"vertex label outside the inclusive range 0..{n - 1}"
    if any(answer[i] >= answer[i + 1] for i in range(len(answer) - 1)):
        return False, "vertex labels must be in strictly increasing order"

    chosen = set(answer)
    adjacency = inst.get("adjacency")
    if not isinstance(adjacency, list) or len(adjacency) != n:
        try:
            adjacency = _adjacency_from_edges(n, inst["edges"])
        except (KeyError, TypeError, ValueError) as exc:
            return False, f"malformed instance graph: {exc}"
    for vertex in answer:
        degree = sum(neighbor in chosen for neighbor in adjacency[vertex])
        if degree != 1:
            return False, f"selected vertex {vertex} has induced degree {degree}, not 1"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated fixed-cardinality subset language."""
    return sorted(rng.sample(range(inst["n"]), inst["selected_vertices"]))


def search_space(inst: dict) -> int | None:
    """Count all canonical fixed-cardinality vertex subsets exactly."""
    return math.comb(inst["n"], inst["selected_vertices"])


def enumerate_all(inst: dict) -> int | None:
    """Count valid answers exactly when the declared language is small."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.combinations(
        range(inst["n"]), inst["selected_vertices"]
    ):
        ok, _ = verify(inst, list(candidate))
        count += int(ok)
    return count


def _distance_histogram(adjacency: list[list[int]], start: int) -> tuple[int, ...]:
    distances = [-1] * len(adjacency)
    distances[start] = 0
    queue = [start]
    for vertex in queue:
        for neighbor in adjacency[vertex]:
            if distances[neighbor] < 0:
                distances[neighbor] = distances[vertex] + 1
                queue.append(neighbor)
    if any(distance < 0 for distance in distances):
        # Components are still represented canonically if an externally built
        # instance reaches here, though generated instances are connected.
        distances = [len(adjacency) + 1 if d < 0 else d for d in distances]
    histogram = [0] * (max(distances) + 1)
    for distance in distances:
        histogram[distance] += 1
    return tuple(histogram)


def canonical_key(inst: dict) -> str:
    """A strong relabeling-invariant fingerprint for the cubic graph."""
    n = inst["n"]
    adjacency = _adjacency_from_edges(n, inst["edges"])
    initial = [_distance_histogram(adjacency, vertex) for vertex in range(n)]
    palette = {signature: i for i, signature in enumerate(sorted(set(initial)))}
    colors = [palette[signature] for signature in initial]

    for _ in range(n):
        signatures = [
            (colors[vertex], tuple(sorted(colors[w] for w in adjacency[vertex])))
            for vertex in range(n)
        ]
        palette = {
            signature: i for i, signature in enumerate(sorted(set(signatures)))
        }
        refined = [palette[signature] for signature in signatures]
        if refined == colors:
            break
        colors = refined

    vertex_records = sorted(
        (
            colors[vertex],
            initial[vertex],
            tuple(sorted(colors[w] for w in adjacency[vertex])),
        )
        for vertex in range(n)
    )
    edge_records = sorted(
        tuple(sorted((colors[u], colors[v]))) for u, v in inst["edges"]
    )
    payload = {
        "n": n,
        "m": len(inst["edges"]),
        "vertices": vertex_records,
        "edges": edge_records,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise ambient size and boundary crowding until the answer cap binds."""
    n = params.get("n")
    selected_vertices = params.get("selected_vertices")
    if not isinstance(n, int) or not isinstance(selected_vertices, int):
        return None
    if n >= 220 or selected_vertices >= 124:
        return "cap_bound"
    harder_n = n + 40
    # Move closer to the cubic stub-capacity boundary s <= 3n/5 while keeping
    # the value even. This is a second difficulty axis, not merely more output.
    harder_selected = min(3 * harder_n // 5, selected_vertices + 24)
    harder_selected -= harder_selected % 2
    if harder_selected > 124:
        return "cap_bound"
    return {"n": harder_n, "selected_vertices": harder_selected}


def _conflict_masks(inst: dict) -> list[int]:
    """Closed neighborhoods in Cameron's line-graph-square formulation."""
    edges = [tuple(edge) for edge in inst["edges"]]
    incidence = [[] for _ in range(inst["n"])]
    for index, (u, v) in enumerate(edges):
        incidence[u].append(index)
        incidence[v].append(index)
    masks = []
    for index, (u, v) in enumerate(edges):
        conflict = 1 << index
        for endpoint in (u, v):
            for adjacent_edge in incidence[endpoint]:
                for neighbor in edges[adjacent_edge]:
                    for other_edge in incidence[neighbor]:
                        conflict |= 1 << other_edge
        masks.append(conflict)
    return masks


def _indices_to_answer(inst: dict, indices: list[int]) -> list[int] | None:
    if len(indices) < inst["matching_edges"]:
        return None
    vertices = set()
    for index in indices[: inst["matching_edges"]]:
        vertices.update(inst["edges"][index])
    if len(vertices) != inst["selected_vertices"]:
        return None
    return sorted(vertices)


def _greedy_edge_pack(
    inst: dict,
    rng: random.Random | None = None,
    randomized: bool = False,
) -> list[int]:
    masks = _conflict_masks(inst)
    available = (1 << len(masks)) - 1
    solution = []
    while available:
        choices = []
        minimum = None
        scan = available
        while scan:
            bit = scan & -scan
            index = bit.bit_length() - 1
            degree = (masks[index] & available).bit_count()
            if minimum is None or degree < minimum:
                minimum = degree
                choices = [index]
            elif degree <= minimum + (2 if randomized else 0):
                choices.append(index)
            scan -= bit
        if randomized and rng is not None:
            index = rng.choice(choices)
        else:
            index = min(choices)
        solution.append(index)
        available &= ~masks[index]
    return solution


def _radius_three_outlier_candidates(inst: dict) -> list[list[int]]:
    adjacency = inst["adjacency"]
    records = []
    for start in range(inst["n"]):
        seen = {start}
        frontier = {start}
        layers = []
        for _ in range(3):
            nxt = {
                neighbor
                for vertex in frontier
                for neighbor in adjacency[vertex]
                if neighbor not in seen
            }
            layers.append(len(nxt))
            seen.update(nxt)
            frontier = nxt
        records.append((tuple(layers), start))
    records.sort()
    size = inst["selected_vertices"]
    return [
        sorted(vertex for _, vertex in records[:size]),
        sorted(vertex for _, vertex in records[-size:]),
    ]


def _spectral_candidates(inst: dict, seed: int) -> list[list[int]]:
    """Float-only adversary: round the most-negative adjacency direction."""
    rng = random.Random(seed ^ 0x5EEC7A1)
    n = inst["n"]
    adjacency = inst["adjacency"]
    vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    mean = sum(vector) / n
    vector = [value - mean for value in vector]
    for _ in range(100):
        nxt = [-sum(vector[w] for w in adjacency[v]) for v in range(n)]
        mean = sum(nxt) / n
        nxt = [value - mean for value in nxt]
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    order = sorted(range(n), key=lambda vertex: (vector[vertex], vertex))
    size = inst["selected_vertices"]
    return [sorted(order[:size]), sorted(order[-size:])]


def _exact_line_square_attack(inst: dict, node_cap: int) -> dict:
    """Target-size MIS branch-and-bound on the edge-conflict graph."""
    masks = _conflict_masks(inst)
    target = inst["matching_edges"]
    nodes = 0
    capped = False

    def visit(available: int, remaining: int):
        nonlocal nodes, capped
        nodes += 1
        if nodes > node_cap:
            capped = True
            return None
        if remaining == 0:
            return []
        if available.bit_count() < remaining:
            return None

        scan = available
        vertex = -1
        best_degree = -1
        while scan:
            bit = scan & -scan
            index = bit.bit_length() - 1
            degree = (masks[index] & available).bit_count()
            if degree > best_degree:
                best_degree = degree
                vertex = index
            scan -= bit

        included = visit(available & ~masks[vertex], remaining - 1)
        if included is not None:
            return [vertex] + included
        if capped:
            return None
        return visit(available & ~(1 << vertex), remaining)

    started = time.perf_counter()
    indices = visit((1 << len(masks)) - 1, target)
    elapsed = time.perf_counter() - started
    candidate = None if indices is None else _indices_to_answer(inst, indices)
    solved = bool(candidate is not None and verify(inst, candidate)[0])
    return {
        "solved": solved,
        "nodes": nodes,
        "wall_clock_sec": elapsed,
        "capped": capped,
    }


def _relabel_instance(inst: dict, permutation: list[int]) -> dict:
    edges = [
        sorted((permutation[u], permutation[v])) for u, v in inst["edges"]
    ]
    answer = sorted(permutation[vertex] for vertex in inst["answer"])
    transformed = dict(inst)
    transformed["edges"] = edges
    transformed["adjacency"] = _adjacency_from_edges(inst["n"], edges)
    transformed["answer"] = answer
    return transformed


def _reorder_instance(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    edges = [list(reversed(edge)) if rng.randrange(2) else list(edge)
             for edge in inst["edges"]]
    rng.shuffle(edges)
    transformed = dict(inst)
    transformed["edges"] = edges
    transformed["adjacency"] = _adjacency_from_edges(inst["n"], edges)
    transformed["answer"] = list(inst["answer"])
    return transformed


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run all mandatory correctness, resistance, and audit gates."""
    report: dict = {
        "paper": "2201.03220",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every preset and several independent construction seeds.
    planted_checks = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 93):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "checks": planted_checks,
        "failures": planted_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12345, **shipping_params)
    answer = inst["answer"]

    # G2: shape corruptions reach distinct diagnostics.
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    out_of_range = list(answer)
    out_of_range[-1] = inst["n"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(row["rejected"] for row in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and a fenced tagged answer round-trip exactly.
    model_reply = (
        "I checked each chosen induced degree.\n\n"
        "```json\n<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\n"
        "The tags contain only the requested array."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer
        and json.loads(json.dumps(answer)) == answer,
        "parsed_equals_answer": parsed == answer,
        "json_native": json.loads(json.dumps(answer)) == answer,
    }

    # G4 and shipping-preset half of G5: uniform structure-aware subsets.
    guess_rng = random.Random(0x220103220)
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(_GUESS_TRIALS):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(verify(inst, candidate)[0])
    guess_elapsed = time.perf_counter() - guess_started
    guess_probability = guess_hits / _GUESS_TRIALS
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_TRIALS,
        "observed_probability": guess_probability,
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform fixed-cardinality vertex subsets",
        "wall_clock_sec": guess_elapsed,
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_valid_count = enumerate_all(demo)

    # G6: all attacks are run on the same eight held construction seeds.
    attack_names = (
        "radius_three_outlier",
        "greedy_left_to_right",
        "random_restart_min_conflict_256",
        "spectral_smallest_adjacency",
        "cameron_line_square_branch_and_bound",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_costs = {name: {"wall_clock_sec": 0.0} for name in attack_names}
    exact_nodes = []
    exact_times = []

    for seed in _ATTACK_SEEDS:
        attacked = make_instance(seed=seed, **shipping_params)

        started = time.perf_counter()
        outlier_solved = any(
            verify(attacked, candidate)[0]
            for candidate in _radius_three_outlier_candidates(attacked)
        )
        attack_costs["radius_three_outlier"]["wall_clock_sec"] += (
            time.perf_counter() - started
        )
        attack_successes["radius_three_outlier"] += int(outlier_solved)

        started = time.perf_counter()
        greedy_indices = _greedy_edge_pack(attacked)
        greedy_candidate = _indices_to_answer(attacked, greedy_indices)
        greedy_solved = bool(
            greedy_candidate is not None and verify(attacked, greedy_candidate)[0]
        )
        attack_costs["greedy_left_to_right"]["wall_clock_sec"] += (
            time.perf_counter() - started
        )
        attack_successes["greedy_left_to_right"] += int(greedy_solved)

        started = time.perf_counter()
        restart_solved = False
        restart_best = 0
        restart_rng = random.Random(seed ^ 0xA771AC)
        for _ in range(256):
            indices = _greedy_edge_pack(attacked, restart_rng, randomized=True)
            restart_best = max(restart_best, len(indices))
            candidate = _indices_to_answer(attacked, indices)
            if candidate is not None and verify(attacked, candidate)[0]:
                restart_solved = True
                break
        attack_costs["random_restart_min_conflict_256"]["wall_clock_sec"] += (
            time.perf_counter() - started
        )
        attack_costs["random_restart_min_conflict_256"].setdefault(
            "best_edges", []
        ).append(restart_best)
        attack_successes["random_restart_min_conflict_256"] += int(restart_solved)

        started = time.perf_counter()
        spectral_solved = any(
            verify(attacked, candidate)[0]
            for candidate in _spectral_candidates(attacked, seed)
        )
        attack_costs["spectral_smallest_adjacency"]["wall_clock_sec"] += (
            time.perf_counter() - started
        )
        attack_successes["spectral_smallest_adjacency"] += int(spectral_solved)

        exact = _exact_line_square_attack(attacked, _EXACT_NODE_CAP)
        exact_nodes.append(exact["nodes"])
        exact_times.append(exact["wall_clock_sec"])
        attack_successes["cameron_line_square_branch_and_bound"] += int(
            exact["solved"]
        )

    attacks = {}
    for name in attack_names:
        entry = {
            "successes": attack_successes[name],
            "attempts": len(_ATTACK_SEEDS),
        }
        if name == "cameron_line_square_branch_and_bound":
            entry.update(
                {
                    "node_cap_each": _EXACT_NODE_CAP,
                    "nodes_each": exact_nodes,
                    "wall_clock_sec_each": exact_times,
                    "complexity": (
                        "exponential MIS branch-and-bound on L(G)^2; Theorem 4 "
                        "bounds the best cited MIS route by O(1.3139^n)"
                    ),
                }
            )
        else:
            entry.update(attack_costs[name])
        attacks[name] = entry
    all_attacks_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attacks,
        "construction_seeds": list(_ATTACK_SEEDS),
    }

    report["G5_density_and_baseline"] = {
        "pass": (
            guess_probability < 1e-6
            and demo_valid_count is not None
            and len(exact_nodes) == len(_ATTACK_SEEDS)
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_TRIALS,
        "shipping_sampled_solution_fraction": guess_probability,
        "demo_exact_valid_answer_count": demo_valid_count,
        "demo_candidate_count": search_space(demo),
        "baseline_nodes_total": sum(exact_nodes),
        "baseline_nodes_average": sum(exact_nodes) / len(exact_nodes),
        "baseline_wall_clock_sec_total": sum(exact_times),
        "baseline_wall_clock_sec_average": sum(exact_times) / len(exact_times),
        "baseline_node_cap_each": _EXACT_NODE_CAP,
    }

    # G7: double both the graph and boundary-sized planted set.
    doubled_params = {
        "n": 2 * shipping_params["n"],
        "selected_vertices": 2 * shipping_params["selected_vertices"],
    }
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > inst["n"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_candidate_space_bits": search_space(inst).bit_length(),
        "doubled_candidate_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: presentation symmetries, semantic preservation, and diversity.
    invariant_checks = 0
    preserving_checks = 0
    distinct_keys = []
    g8_failures = []
    for offset in range(20):
        base = make_instance(seed=9000 + offset, **shipping_params)
        key = canonical_key(base)
        distinct_keys.append(key)

        rng = random.Random(12000 + offset)
        permutation = list(range(base["n"]))
        rng.shuffle(permutation)
        relabeled = _relabel_instance(base, permutation)
        reordered = _reorder_instance(base, 13000 + offset)
        composed = _reorder_instance(relabeled, 14000 + offset)
        for name, transformed in (
            ("vertex_relabel", relabeled),
            ("edge_reorder_and_reverse", reordered),
            ("composed", composed),
        ):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append([offset, name, "key changed"])
            ok, reason = verify(transformed, transformed["answer"])
            preserving_checks += 1
            if not ok:
                g8_failures.append([offset, name, reason])
        # Edge order and endpoint orientation preserve the literal vertex set.
        original_ok, original_reason = verify(reordered, base["answer"])
        preserving_checks += 1
        if not original_ok:
            g8_failures.append([offset, "original_answer_after_reorder", original_reason])

    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "semantics_preserving_checks": preserving_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": 20,
        "failures": g8_failures,
        "known_limit": "strong invariant, not a complete cubic-graph isomorphism test",
    }

    # G9(c) is gated; the three arms are diagnostics populated by harden.py.
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 3 * inst["selected_vertices"]
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
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
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "oracle_evidence_scope": ORACLE_EVIDENCE_SCOPE,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "operation_accounting": (
            "after choosing the globally compatible set, inspect the three "
            "adjacency entries of each submitted vertex"
        ),
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
