"""Verified problem generator for arXiv:1605.03871.

The paper defines maximal Delta-cliques in temporal graphs and gives a
Bron--Kerbosch enumeration algorithm.  This module inverse-generates a regular
temporal graph containing a maximal Delta-clique.  Every qualifying vertex pair
interacts twice, exactly Delta time steps apart, so validity is checked directly
against all sliding Delta-windows.  The interaction times also carry an additive
residue invariant that gives a short structural route without being part of the
answer or the checker.
"""

from __future__ import annotations

import collections
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
except ImportError:  # This family remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "temporal graph with integer-stamped undirected interactions",
        "maximal Delta-clique as a vertex set and closed time interval",
    ],
    "verification_operations": [
        "exact integer sliding-window coverage checks",
        "pairwise temporal-neighborhood intersection",
        "exact vertex-maximality scan",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "First interaction times are endpoint-sums of hidden residues, whose one "
        "missing value makes the target one of two boundary blocks; without this "
        "invariant a solver faces temporal Bron--Kerbosch search."
    ),
    "hardness_basis": (
        "Track B: the paper's pivoted BronKerboschDelta algorithm (Algorithm 5; "
        "Theorem 2 gives O(x|E|+|E||T|), with Corollary 1 exponential in |V|) "
        "solves the shipping instance in 39,720 counted operations and 0.006 "
        "seconds on this host; a 128-restart randomized greedy used 31,621 "
        "operations, versus at most 296 exact operations after the "
        "additive timestamp invariant is recognized."
    ),
    "max_answer_tokens": 21,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly k distinct vertex indices in strictly "
        "increasing order and the fixed closed full-lifetime interval [0,2q-1]; "
        "vertices lie in [0,q-2], k <= 12, and no repetitions are allowed."
    ),
    "bounds": {
        "max_vertices": 12,
        "max_atomic_elements": 14,
        "vertex_min": 0,
        "vertex_max": "q-2 from the instance",
        "interval": "fixed by the instance",
    },
}

STRUCTURAL_HINT = (
    "The first interaction times are pairwise sums of latent vertex residues modulo q."
)
PLACEBO_HINT = (
    "The interaction rows reward careful attention to endpoint order and interval conventions."
)


DIFFICULTY = {
    "hard": {"n": 138, "d": 68, "k": 12, "mixing": 8},
}
SHIPPING_DIFFICULTY = "hard"

# Populated only from script-owned oracle runs.  Zero attempts means unmeasured.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "not_run"

NOTES = (
    "Section 2.1.2, Definition 2 fixes a Delta-clique: for every integer "
    "tau in [a,b-Delta], every vertex pair must interact in the inclusive "
    "window [tau,tau+Delta]. The same section distinguishes vertex-, time-, "
    "and joint maximality. Theorem 1 proves Algorithm 4 enumerates exactly all "
    "maximal Delta-cliques; Algorithm 5 adds temporal pivoting. Theorem 2 makes "
    "the algorithm output-sensitive, Corollary 1 gives an exponential general "
    "bound, and Theorem 3 says small Delta-slice degeneracy is FPT. Thus this is "
    "Track B, not a claim that an algorithm is unknown. Construction starts "
    "from a heavily switched regular graph, inserts the known clique by "
    "degree-preserving 2-switches, and carries that witness into two-event "
    "temporal schedules. Equal degrees defeat degree outliers; a random vertex "
    "relabeling and random missing residue defeat raw-label guesses; nearly all "
    "field residues and a random cyclic offset flatten timestamp means; random "
    "regular mixing defeats one-path greedy search; and the planted dimension "
    "is kept below the nontrivial spectral bulk observed by the deflated power "
    "attack. The exact timestamp invariant remains a deliberately short route."
)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    d = value - 1
    shift = 0
    while d % 2 == 0:
        shift += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(shift - 1):
            x = (x * x) % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value: int) -> int:
    candidate = max(2, int(value))
    if candidate == 2:
        return 2
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _edge_masks(neighbors: list[set[int]]) -> list[int]:
    return [sum(1 << vertex for vertex in row) for row in neighbors]


def _connected(masks: list[int]) -> bool:
    if not masks:
        return True
    seen = 1
    frontier = 1
    while frontier:
        bit = frontier & -frontier
        frontier -= bit
        vertex = bit.bit_length() - 1
        new = masks[vertex] & ~seen
        seen |= new
        frontier |= new
    return seen.bit_count() == len(masks)


def _is_clique_masks(masks: list[int], vertices: list[int]) -> bool:
    for index, vertex in enumerate(vertices):
        required = vertices[index + 1:]
        if any(not (masks[vertex] >> other) & 1 for other in required):
            return False
    return True


def _is_maximal_clique_masks(masks: list[int], vertices: list[int]) -> bool:
    if not _is_clique_masks(masks, vertices):
        return False
    chosen = set(vertices)
    for vertex in range(len(masks)):
        if vertex in chosen:
            continue
        if all((masks[vertex] >> other) & 1 for other in vertices):
            return False
    return True


def _mixed_regular_graph(
    n: int,
    d: int,
    plant: set[int],
    rng: random.Random,
    mixing: int,
) -> list[int]:
    """Make a d-regular graph and insert plant by degree-preserving switches."""
    neighbors = [set() for _ in range(n)]
    half = d // 2
    for vertex in range(n):
        for offset in range(1, half + 1):
            other = (vertex + offset) % n
            neighbors[vertex].add(other)
            neighbors[other].add(vertex)

    edges = [
        (left, right)
        for left in range(n)
        for right in neighbors[left]
        if left < right
    ]
    position = {edge: index for index, edge in enumerate(edges)}

    def remove_edge(left: int, right: int) -> None:
        edge = tuple(sorted((left, right)))
        index = position.pop(edge)
        last = edges.pop()
        if index < len(edges):
            edges[index] = last
            position[last] = index
        neighbors[left].remove(right)
        neighbors[right].remove(left)

    def add_edge(left: int, right: int) -> None:
        edge = tuple(sorted((left, right)))
        position[edge] = len(edges)
        edges.append(edge)
        neighbors[left].add(right)
        neighbors[right].add(left)

    for _ in range(mixing * len(edges)):
        first_index, second_index = rng.sample(range(len(edges)), 2)
        left, right = edges[first_index]
        other_left, other_right = edges[second_index]
        if rng.randrange(2):
            left, right = right, left
        if rng.randrange(2):
            other_left, other_right = other_right, other_left
        if len({left, right, other_left, other_right}) < 4:
            continue
        if other_left in neighbors[left] or other_right in neighbors[right]:
            continue
        remove_edge(left, right)
        remove_edge(other_left, other_right)
        add_edge(left, other_left)
        add_edge(right, other_right)

    for left in sorted(plant):
        for right in sorted(plant):
            if left >= right or right in neighbors[left]:
                continue
            left_neighbors = [v for v in neighbors[left] if v not in plant]
            right_neighbors = [v for v in neighbors[right] if v not in plant]
            switch = None
            for _ in range(512):
                a = rng.choice(left_neighbors)
                b = rng.choice(right_neighbors)
                if a != b and b not in neighbors[a]:
                    switch = (a, b)
                    break
            if switch is None:
                for a in left_neighbors:
                    for b in right_neighbors:
                        if a != b and b not in neighbors[a]:
                            switch = (a, b)
                            break
                    if switch is not None:
                        break
            if switch is None:
                raise RuntimeError("could not complete a degree-preserving plant switch")
            a, b = switch
            remove_edge(left, a)
            remove_edge(right, b)
            add_edge(left, right)
            add_edge(a, b)

    masks = _edge_masks(neighbors)
    if any(mask.bit_count() != d for mask in masks):
        raise AssertionError("degree-preserving construction changed a degree")
    return masks


def _masks_to_schedules(
    masks: list[int], tags: list[int], q: int
) -> list[dict[str, list[int]]]:
    schedules: list[dict[str, list[int]]] = [dict() for _ in masks]
    for left, mask in enumerate(masks):
        remaining = mask & ~((1 << (left + 1)) - 1)
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            right = bit.bit_length() - 1
            phase = (tags[left] + tags[right]) % q
            schedules[left][str(right)] = [phase, phase + q]
    return schedules


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a temporal graph and a maximal Delta-clique witness."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 10:
        raise ValueError("n must be an integer at least 10")
    d = params.pop("d", max(4, 2 * (n // 6)))
    k = params.pop("k", 10)
    mixing = params.pop("mixing", 6)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if any(not isinstance(x, int) or isinstance(x, bool) for x in (d, k, mixing)):
        raise ValueError("d, k, and mixing must be integers")
    q = _next_prime(n + 1)
    vertex_count = q - 1
    if d < 2 or d >= vertex_count or d % 2:
        raise ValueError("d must be even and satisfy 2 <= d < q-1")
    if not 3 <= k <= min(64, d + 1, vertex_count - 2):
        raise ValueError("k must satisfy 3 <= k <= min(64,d+1,q-3)")
    if mixing < 1 or mixing > 64:
        raise ValueError("mixing must lie in [1,64]")

    rng = random.Random(seed)
    missing = rng.randrange(q)
    side = rng.choice((-1, 1))
    plant_tags = {(missing + side * offset) % q for offset in range(1, k + 1)}
    tags = [value for value in range(q) if value != missing]
    rng.shuffle(tags)
    plant = {vertex for vertex, tag in enumerate(tags) if tag in plant_tags}
    other_boundary_tags = {
        (missing - side * offset) % q for offset in range(1, k + 1)
    }
    other_boundary = [
        vertex for vertex, tag in enumerate(tags) if tag in other_boundary_tags
    ]

    masks = None
    for _ in range(16):
        candidate = _mixed_regular_graph(
            vertex_count, d, plant, rng, mixing
        )
        if not _connected(candidate):
            continue
        if not _is_maximal_clique_masks(candidate, sorted(plant)):
            continue
        if _is_clique_masks(candidate, sorted(other_boundary)):
            continue
        masks = candidate
        break
    if masks is None:
        raise RuntimeError("could not construct a certified regular temporal instance")

    delta = q
    lifetime = 2 * q - 1
    schedules = _masks_to_schedules(masks, tags, q)
    answer = {"vertices": sorted(plant), "interval": [0, lifetime]}
    return {
        "family": "regular_additive_temporal_clique_v1",
        "n": vertex_count,
        "q": q,
        "d": d,
        "k": k,
        "delta": delta,
        "time_interval": [0, lifetime],
        "schedules": schedules,
        "answer": answer,
    }


def _render_rows(inst: dict) -> str:
    rows = []
    for left, row in enumerate(inst["schedules"]):
        for right_text, times in row.items():
            rows.append(f"{left} {right_text} {times[0]} {times[1]}")
    return "\n".join(rows)


def render(inst: dict) -> str:
    """Render a complete, self-contained maximal Delta-clique problem."""
    prompt = f"""Find a maximal Delta-clique in the temporal graph below.

The vertices are the integers 0 through {inst['n'] - 1}.  Time is discrete and
the graph lifetime is the closed integer interval [0,{inst['time_interval'][1]}].
Delta = {inst['delta']}.

A pair (X,[a,b]) is a Delta-clique when X is a set of vertices, b-a >= Delta,
and, for every integer tau from a through b-Delta inclusive, every two distinct
vertices of X have at least one interaction at a time t in the closed window
[tau,tau+Delta].  It is vertex-maximal when no vertex outside X can be added
while keeping [a,b], and time-maximal when [a,b] cannot be enlarged inside the
graph lifetime while keeping X.  "Maximal" means both properties.

Find a maximal Delta-clique with exactly {inst['k']} vertices and interval
[0,{inst['time_interval'][1]}].  Vertex order does not matter mathematically,
but output the vertices in strictly increasing order, with no repetitions.

Each interaction row has the form "u v t1 t2" and means that the undirected
pair {{u,v}} interacts exactly at the two listed integer times.  A pair absent
from the rows never interacts.  Rows are data, not extra assumptions.

INTERACTIONS ({sum(len(row) for row in inst['schedules'])} pair schedules)
u v t1 t2
{_render_rows(inst)}
END INTERACTIONS

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys "vertices" and "interval".  The interval must be the stated
closed interval and all numbers are decimal integers.
Example: <answer>{{"vertices":[0,3,7],"interval":[0,{inst['time_interval'][1]}]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        prompt += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        prompt += "\n\nHint: " + PLACEBO_HINT
    return prompt


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def _times_for(inst: dict, left: int, right: int) -> list[int]:
    if left > right:
        left, right = right, left
    return inst["schedules"][left].get(str(right), [])


def _covers_interval(times: list[int], a: int, b: int, delta: int) -> bool:
    """Exact equivalent of inspecting every inclusive sliding Delta-window."""
    if not times:
        return False
    if times[0] > a + delta or times[-1] < b - delta:
        return False
    return all(right - left <= delta for left, right in zip(times, times[1:]))


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check a candidate directly against temporal schedules; never read answer."""
    if answer is None or answer == {} or answer == []:
        return False, "answer is empty"
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"vertices", "interval"}:
        return False, "answer must have exactly vertices and interval keys"
    vertices = answer["vertices"]
    interval = answer["interval"]
    if not isinstance(vertices, list):
        return False, "vertices must be a JSON list"
    if len(vertices) != inst["k"]:
        return False, f"need exactly {inst['k']} vertices"
    if any(not isinstance(vertex, int) or isinstance(vertex, bool) for vertex in vertices):
        return False, "all vertices must be integers"
    if any(vertex < 0 or vertex >= inst["n"] for vertex in vertices):
        return False, f"vertex out of range [0,{inst['n'] - 1}]"
    if len(set(vertices)) != len(vertices):
        return False, "vertices must be distinct"
    if any(vertices[i] >= vertices[i + 1] for i in range(len(vertices) - 1)):
        return False, "vertices must be strictly increasing"
    if interval != inst["time_interval"]:
        return False, "interval must equal the full closed graph lifetime"

    a, b = interval
    delta = inst["delta"]
    for index, left in enumerate(vertices):
        for right in vertices[index + 1:]:
            if not _covers_interval(_times_for(inst, left, right), a, b, delta):
                return False, f"pair {left},{right} misses a Delta-window"
    chosen = set(vertices)
    for outside in range(inst["n"]):
        if outside in chosen:
            continue
        if all(_covers_interval(
            _times_for(inst, outside, inside), a, b, delta
        ) for inside in vertices):
            return False, f"vertex {outside} extends the clique"
    # The requested interval already equals the graph lifetime, so it is
    # time-maximal by inspection.
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the shape-aware space of k-sets and the fixed interval."""
    return {
        "vertices": sorted(rng.sample(range(inst["n"]), inst["k"])),
        "interval": list(inst["time_interval"]),
    }


def search_space(inst: dict) -> int:
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    """Count valid witnesses exactly when the declared language is small."""
    if search_space(inst) > 100_000:
        return None
    count = 0
    for vertices in itertools.combinations(range(inst["n"]), inst["k"]):
        candidate = {
            "vertices": list(vertices),
            "interval": list(inst["time_interval"]),
        }
        count += int(verify(inst, candidate)[0])
    return count


def _temporal_masks(inst: dict) -> tuple[list[int], int]:
    """Build full-lifetime Delta-neighborhoods and count exact comparisons."""
    masks = [0] * inst["n"]
    operations = 0
    a, b = inst["time_interval"]
    for left, row in enumerate(inst["schedules"]):
        for right_text, times in row.items():
            right = int(right_text)
            operations += len(times) + 2
            if _covers_interval(times, a, b, inst["delta"]):
                masks[left] |= 1 << right
                masks[right] |= 1 << left
    return masks, operations


def _reference_bron_kerbosch(inst: dict) -> tuple[object | None, dict]:
    """Algorithm 5 specialized to the common full-lifetime interval."""
    masks, schedule_checks = _temporal_masks(inst)
    target = inst["k"]
    recursive_calls = 0
    pivot_tests = 0

    def recurse(clique: list[int], candidates: int, excluded: int) -> list[int] | None:
        nonlocal recursive_calls, pivot_tests
        recursive_calls += 1
        if not candidates and not excluded:
            return clique if len(clique) == target else None
        if len(clique) >= target or len(clique) + candidates.bit_count() < target:
            return None

        union = candidates | excluded
        pivot = 0
        best = -1
        while union:
            bit = union & -union
            union -= bit
            vertex = bit.bit_length() - 1
            score = (candidates & masks[vertex]).bit_count()
            pivot_tests += 1
            if score > best:
                best = score
                pivot = vertex

        branch = candidates & ~masks[pivot]
        while branch:
            bit = branch & -branch
            branch -= bit
            vertex = bit.bit_length() - 1
            found = recurse(
                clique + [vertex],
                candidates & masks[vertex],
                excluded & masks[vertex],
            )
            if found is not None:
                return found
            candidates &= ~bit
            excluded |= bit
        return None

    vertices = recurse([], (1 << inst["n"]) - 1, 0)
    answer = None if vertices is None else {
        "vertices": sorted(vertices),
        "interval": list(inst["time_interval"]),
    }
    metrics = {
        "recursive_calls": recursive_calls,
        "pivot_candidate_tests": pivot_tests,
        "schedule_comparisons": schedule_checks,
        "counted_operations": recursive_calls + pivot_tests + schedule_checks,
    }
    return answer, metrics


def _recover_tags(inst: dict) -> tuple[list[int], int]:
    """Recover the unique additive vertex labels from edge phases."""
    masks, _ = _temporal_masks(inst)
    triangle = None
    for first in range(inst["n"]):
        neighbors = []
        remaining = masks[first]
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            neighbors.append(bit.bit_length() - 1)
        for index, second in enumerate(neighbors):
            for third in neighbors[index + 1:]:
                if (masks[second] >> third) & 1:
                    triangle = (first, second, third)
                    break
            if triangle is not None:
                break
        if triangle is not None:
            break
    if triangle is None:
        raise ValueError("timestamp graph has no triangle")

    q = inst["q"]
    first, second, third = triangle
    t12 = _times_for(inst, first, second)[0]
    t13 = _times_for(inst, first, third)[0]
    t23 = _times_for(inst, second, third)[0]
    tags: list[int | None] = [None] * inst["n"]
    tags[first] = ((t12 + t13 - t23) * pow(2, -1, q)) % q
    tags[second] = (t12 - tags[first]) % q
    tags[third] = (t13 - tags[first]) % q
    operations = 5
    queue = collections.deque((first, second, third))
    while queue:
        vertex = queue.popleft()
        remaining = masks[vertex]
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            other = bit.bit_length() - 1
            phase = _times_for(inst, vertex, other)[0]
            if tags[other] is None:
                tags[other] = (phase - tags[vertex]) % q
                operations += 1
                queue.append(other)
            elif (tags[vertex] + tags[other]) % q != phase:
                raise ValueError("interaction times violate the additive invariant")
    if any(tag is None for tag in tags):
        raise ValueError("timestamp graph is disconnected")
    recovered = [int(tag) for tag in tags]
    if len(set(recovered)) != inst["n"]:
        raise ValueError("recovered vertex residues are not distinct")
    return recovered, operations


def _compact_answer(inst: dict) -> tuple[dict, int]:
    tags, operations = _recover_tags(inst)
    present = [False] * inst["q"]
    by_tag = {}
    for vertex, tag in enumerate(tags):
        present[tag] = True
        by_tag[tag] = vertex
    missing_values = [value for value, seen in enumerate(present) if not seen]
    if len(missing_values) != 1:
        raise ValueError("expected exactly one missing residue")
    missing = missing_values[0]
    k = inst["k"]
    tag_blocks = [
        [(missing + offset) % inst["q"] for offset in range(1, k + 1)],
        [(missing - offset) % inst["q"] for offset in range(1, k + 1)],
    ]
    operations += 2 * k
    masks, _ = _temporal_masks(inst)
    for block in tag_blocks:
        vertices = sorted(by_tag[tag] for tag in block)
        is_clique = True
        for index, left in enumerate(vertices):
            for right in vertices[index + 1:]:
                operations += 1
                if not (masks[left] >> right) & 1:
                    is_clique = False
                    break
            if not is_clique:
                break
        if is_clique:
            answer = {
                "vertices": vertices,
                "interval": list(inst["time_interval"]),
            }
            return answer, operations
    raise ValueError("neither residue boundary block is a clique")


def _relabel_vertices(inst: dict, permutation: list[int], reverse_rows: bool = False) -> dict:
    """Carry the temporal graph and witness through an arbitrary renumbering."""
    if sorted(permutation) != list(range(inst["n"])):
        raise ValueError("permutation must biject the vertex set")
    triples = []
    for left, row in enumerate(inst["schedules"]):
        for right_text, times in row.items():
            right = int(right_text)
            new_left, new_right = sorted((permutation[left], permutation[right]))
            triples.append((new_left, new_right, list(times)))
    triples.sort(reverse=reverse_rows)
    schedules: list[dict[str, list[int]]] = [dict() for _ in range(inst["n"])]
    for left, right, times in triples:
        schedules[left][str(right)] = times
    out = dict(inst)
    out["schedules"] = schedules
    out["answer"] = {
        "vertices": sorted(permutation[v] for v in inst["answer"]["vertices"]),
        "interval": list(inst["answer"]["interval"]),
    }
    return out


def canonical_key(inst: dict) -> str:
    """Canonicalize vertex renumbering and interaction-row reordering via residues."""
    tags, _ = _recover_tags(inst)
    edges = []
    for left, row in enumerate(inst["schedules"]):
        for right_text in row:
            right = int(right_text)
            edges.append(tuple(sorted((tags[left], tags[right]))))
    edges.sort()
    raw = json.dumps(
        [
            inst["family"], inst["q"], inst["d"], inst["k"], inst["delta"],
            inst["time_interval"], edges,
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Tighten the target and add regular decoys before the route hits 300 ops."""
    current = {key: value for key, value in params.items() if key != "_preset"}
    n = int(current.get("n", DIFFICULTY[SHIPPING_DIFFICULTY]["n"]))
    k = int(current.get("k", 10))
    d = int(current.get("d", 58))
    proposed_k = k + 1
    proposed_d = min(_next_prime(n + 1) - 3, d + 4)
    if proposed_d % 2:
        proposed_d -= 1
    proposed_operations = (_next_prime(n + 1) - 1) + 2 + 2 * proposed_k \
        + proposed_k * (proposed_k - 1)
    if proposed_operations > 300:
        return "cap_bound"
    current["k"] = proposed_k
    current["d"] = proposed_d
    current["mixing"] = min(64, int(current.get("mixing", 6)) + 2)
    return current


def _candidate(inst: dict, vertices: list[int]) -> dict:
    return {
        "vertices": sorted(vertices),
        "interval": list(inst["time_interval"]),
    }


def _timestamp_mean_candidate(inst: dict, high: bool = False) -> dict:
    totals = [0] * inst["n"]
    counts = [0] * inst["n"]
    for left, row in enumerate(inst["schedules"]):
        for right_text, times in row.items():
            right = int(right_text)
            totals[left] += times[0]
            totals[right] += times[0]
            counts[left] += 1
            counts[right] += 1
    order = sorted(
        range(inst["n"]),
        key=lambda vertex: (totals[vertex] / counts[vertex], vertex),
        reverse=high,
    )
    return _candidate(inst, order[:inst["k"]])


def _greedy_one_path(inst: dict) -> dict:
    masks, _ = _temporal_masks(inst)
    totals = [0] * inst["n"]
    counts = [0] * inst["n"]
    for left, row in enumerate(inst["schedules"]):
        for right_text, times in row.items():
            right = int(right_text)
            totals[left] += times[0]
            totals[right] += times[0]
            counts[left] += 1
            counts[right] += 1
    # Start at the most tempting timestamp outlier, then always choose the
    # extension leaving the largest common neighborhood.  This is executable as
    # one by-hand route, unlike the full reference backtracking tree.
    start = min(
        range(inst["n"]),
        key=lambda vertex: (totals[vertex] / counts[vertex], vertex),
    )
    clique = [start]
    candidates = masks[start]
    while candidates and len(clique) < inst["k"]:
        best_vertex = None
        best_score = -1
        remaining = candidates
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            vertex = bit.bit_length() - 1
            score = (candidates & masks[vertex]).bit_count()
            if score > best_score:
                best_score = score
                best_vertex = vertex
        clique.append(best_vertex)
        candidates &= masks[best_vertex]
    return _candidate(inst, clique)


def _random_greedy_restart(
    inst: dict, rng: random.Random, restarts: int = 64
) -> dict | None:
    masks, _ = _temporal_masks(inst)
    for _ in range(restarts):
        clique = [rng.randrange(inst["n"])]
        candidates = masks[clique[0]]
        while candidates and len(clique) < inst["k"]:
            pool = []
            remaining = candidates
            while remaining:
                bit = remaining & -remaining
                remaining -= bit
                pool.append(bit.bit_length() - 1)
            chosen = rng.choice(pool)
            clique.append(chosen)
            candidates &= masks[chosen]
        if len(clique) == inst["k"]:
            answer = _candidate(inst, clique)
            if verify(inst, answer)[0]:
                return answer
    return None


def _strong_random_greedy(
    inst: dict, rng: random.Random, restarts: int = 64
) -> tuple[dict | None, dict]:
    """Tool-scale randomized greedy: prefer maximum common-neighborhood degree."""
    masks, schedule_operations = _temporal_masks(inst)
    operations = schedule_operations
    attempts_used = 0
    for attempts_used in range(1, restarts + 1):
        clique = [rng.randrange(inst["n"])]
        candidates = masks[clique[0]]
        while candidates and len(clique) < inst["k"]:
            scored = []
            remaining = candidates
            while remaining:
                bit = remaining & -remaining
                remaining -= bit
                vertex = bit.bit_length() - 1
                scored.append(((candidates & masks[vertex]).bit_count(), vertex))
                operations += 1
            best = max(score for score, _ in scored)
            pool = [vertex for score, vertex in scored if score >= best - 1]
            chosen = rng.choice(pool)
            clique.append(chosen)
            candidates &= masks[chosen]
            operations += 1
        if len(clique) == inst["k"]:
            answer = _candidate(inst, clique)
            if verify(inst, answer)[0]:
                return answer, {
                    "restarts_used": attempts_used,
                    "counted_operations": operations,
                }
    return None, {
        "restarts_used": attempts_used,
        "counted_operations": operations,
    }


def _spectral_attack(inst: dict) -> dict | None:
    """Deflated power iteration; try positive, negative, and magnitude tails."""
    masks, _ = _temporal_masks(inst)
    rng = random.Random(0x5EEC7A1)
    vector = [rng.random() - 0.5 for _ in range(inst["n"])]
    mean = sum(vector) / len(vector)
    vector = [value - mean for value in vector]
    for _ in range(96):
        product = []
        for mask in masks:
            total = 0.0
            remaining = mask
            while remaining:
                bit = remaining & -remaining
                remaining -= bit
                total += vector[bit.bit_length() - 1]
            product.append(total)
        mean = sum(product) / len(product)
        product = [value - mean for value in product]
        norm = math.sqrt(sum(value * value for value in product))
        if not norm:
            return None
        vector = [value / norm for value in product]
    orders = [
        sorted(range(inst["n"]), key=lambda v: vector[v], reverse=True),
        sorted(range(inst["n"]), key=lambda v: vector[v]),
        sorted(range(inst["n"]), key=lambda v: abs(vector[v]), reverse=True),
    ]
    for order in orders:
        answer = _candidate(inst, order[:inst["k"]])
        if verify(inst, answer)[0]:
            return answer
    return None


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return measured, JSON-native evidence."""
    report: dict = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 8675309):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]
    corruptions = {}
    dropped = json.loads(json.dumps(base))
    dropped["vertices"].pop()
    swapped = json.loads(json.dumps(base))
    swapped["vertices"][0], swapped["vertices"][1] = (
        swapped["vertices"][1], swapped["vertices"][0]
    )
    duplicated = json.loads(json.dumps(base))
    duplicated["vertices"][1] = duplicated["vertices"][0]
    outside = json.loads(json.dumps(base))
    outside["vertices"][-1] = shipping["n"]
    bad_interval = json.loads(json.dumps(base))
    bad_interval["interval"][1] -= 1
    for name, candidate in (
        ("drop_one_vertex", dropped),
        ("swap_two_vertices", swapped),
        ("duplicate_vertex", duplicated),
        ("empty", {}),
        ("out_of_range", outside),
        ("wrong_interval", bad_interval),
    ):
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(base, separators=(",", ":"))
    realistic = (
        "The full-lifetime maximal clique is:\n```json\n<answer>"
        + encoded + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == base and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed == base,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(0x160503871)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "sampler": "uniform k-subsets; sorted, distinct, and with the forced interval",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    reference_started = time.perf_counter()
    reference_answer, reference_metrics = _reference_bron_kerbosch(shipping)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    greedy_started = time.perf_counter()
    greedy_answer, greedy_metrics = _strong_random_greedy(
        shipping, random.Random(424242), 128
    )
    greedy_seconds = time.perf_counter() - greedy_started
    greedy_ok = greedy_answer is not None and verify(shipping, greedy_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and greedy_ok and guess_hits / guess_total < 1e-6,
        "shipping_vertices": shipping["n"],
        "shipping_pair_schedules": sum(len(row) for row in shipping["schedules"]),
        "sampled_valid_fraction": guess_hits / guess_total,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_count_exact_decimal": str(search_space(shipping)),
        "reference_algorithm_recursive_nodes": reference_metrics["recursive_calls"],
        "reference_algorithm_counted_operations": reference_metrics["counted_operations"],
        "reference_algorithm_wall_clock_sec": round(reference_seconds, 6),
        "reference_solution_verified": reference_ok,
        "alternative_greedy_counted_operations": greedy_metrics["counted_operations"],
        "alternative_greedy_restarts": greedy_metrics["restarts_used"],
        "alternative_greedy_wall_clock_sec": round(greedy_seconds, 6),
        "alternative_greedy_solution_verified": greedy_ok,
    }

    attack_names = (
        "outlier_equal_degree_then_low_id",
        "outlier_low_mean_first_time",
        "greedy_single_common_neighborhood_path",
        "random_clique_growth_restart_64",
        "spectral_deflated_power_iteration",
    )
    successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_operations = 0
    reference_nodes = 0
    reference_seconds_panel = 0.0
    strong_greedy_successes = 0
    strong_greedy_operations = 0
    strong_greedy_restarts = 0
    strong_greedy_seconds = 0.0
    for trial_seed in range(8100, 8108):
        trial = make_instance(seed=trial_seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        degree_order = sorted(
            range(trial["n"]),
            key=lambda vertex: (-sum(
                1 for row in trial["schedules"] for key in row
                if int(key) == vertex
            ) - len(trial["schedules"][vertex]), vertex),
        )
        candidates = {
            "outlier_equal_degree_then_low_id": _candidate(
                trial, degree_order[:trial["k"]]
            ),
            "outlier_low_mean_first_time": _timestamp_mean_candidate(trial),
            "greedy_single_common_neighborhood_path": _greedy_one_path(trial),
            "random_clique_growth_restart_64": _random_greedy_restart(
                trial, random.Random(90_000 + trial_seed), 64
            ),
            "spectral_deflated_power_iteration": _spectral_attack(trial),
        }
        for name, candidate in candidates.items():
            successes[name] += int(candidate is not None and verify(trial, candidate)[0])

        started = time.perf_counter()
        answer, metrics = _reference_bron_kerbosch(trial)
        reference_seconds_panel += time.perf_counter() - started
        reference_operations += metrics["counted_operations"]
        reference_nodes += metrics["recursive_calls"]
        reference_successes += int(answer is not None and verify(trial, answer)[0])
        started = time.perf_counter()
        strong_answer, strong_metrics = _strong_random_greedy(
            trial, random.Random(110_000 + trial_seed), 128
        )
        strong_greedy_seconds += time.perf_counter() - started
        strong_greedy_operations += strong_metrics["counted_operations"]
        strong_greedy_restarts += strong_metrics["restarts_used"]
        strong_greedy_successes += int(
            strong_answer is not None and verify(trial, strong_answer)[0]
        )

    attacks = {
        name: {"successes": successes[name], "attempts": 8}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values())
        and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "pivoted temporal Bron--Kerbosch (paper Algorithm 5)",
            "complexity": (
                "O(x|E|+|E||T|) to enumerate by Theorem 2; "
                "O(2^|V||T||E|) general bound by Corollary 1"
            ),
            "wall_clock_sec_for_8": round(reference_seconds_panel, 6),
            "counted_operations_for_8": reference_operations,
            "recursive_nodes_for_8": reference_nodes,
            "successes": reference_successes,
            "attempts": 8,
            "solves": f"{reference_successes}/8, as expected on Track B",
        },
        "reference_algorithm_alternative": {
            "name": "128-restart maximum-common-neighborhood randomized greedy",
            "complexity": "O(128*k*n*d) bitset-score operations",
            "wall_clock_sec_for_8": round(strong_greedy_seconds, 6),
            "counted_operations_for_8": strong_greedy_operations,
            "restarts_used_for_8": strong_greedy_restarts,
            "successes": strong_greedy_successes,
            "attempts": 8,
            "solves": f"{strong_greedy_successes}/8, a tool-scale Track B route",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["d"] *= 2
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_planted_ok = verify(doubled, doubled["answer"])[0]
    compact_doubled, compact_doubled_ops = _compact_answer(doubled)
    doubled_compact_ok = verify(doubled, compact_doubled)[0]
    report["G7_scales"] = {
        "pass": doubled_planted_ok and doubled_compact_ok
        and doubled["n"] >= 2 * shipping["n"],
        "shipping_vertices": shipping["n"],
        "doubled_vertices": doubled["n"],
        "planted_verifies_at_doubled_size": doubled_planted_ok,
        "compact_route_verifies_at_doubled_size": doubled_compact_ok,
        "compact_route_operations_at_doubled_size": compact_doubled_ops,
        "answer_elements_unchanged": (
            _answer_atoms(doubled["answer"]) == _answer_atoms(shipping["answer"])
        ),
    }

    invariance_checks = 0
    carried_witness_checks = 0
    failures_g8 = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        rr = random.Random(60_000 + seed)
        first_permutation = list(range(original["n"]))
        second_permutation = list(range(original["n"]))
        rr.shuffle(first_permutation)
        rr.shuffle(second_permutation)
        first = _relabel_vertices(original, first_permutation, reverse_rows=True)
        second = _relabel_vertices(original, second_permutation)
        composed = _relabel_vertices(first, second_permutation, reverse_rows=True)
        for transformed in (first, second, composed):
            invariance_checks += 1
            carried_witness_checks += 1
            if canonical_key(transformed) != original_key:
                failures_g8.append("key changed under vertex/input relabeling")
            if not verify(transformed, transformed["answer"])[0]:
                failures_g8.append("carried witness failed")
    report["G8_canonical_key"] = {
        "pass": not failures_g8 and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": failures_g8,
        "normalized_away": "all vertex permutations and all interaction-row reorderings",
    }

    compact_failures = []
    route_operations = []
    actual_answer_chars = []
    for seed in range(64):
        inst = make_instance(seed=70_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        compact, operations = _compact_answer(inst)
        route_operations.append(operations)
        actual_answer_chars.append(len(json.dumps(inst["answer"], separators=(",", ":"))))
        if not verify(inst, compact)[0]:
            compact_failures.append(seed)
    worst_shape = {
        "vertices": list(range(shipping["n"] - shipping["k"], shipping["n"])),
        "interval": list(shipping["time_interval"]),
    }
    answer_chars = max(
        max(actual_answer_chars),
        len(json.dumps(worst_shape, separators=(",", ":"))),
    )
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    # The wrong boundary block can in principle survive until its last pair;
    # include that exact worst-case bound rather than only the sampled maximum.
    route_operation_bound = (
        shipping["n"] + 2 + 2 * shipping["k"]
        + shipping["k"] * (shipping["k"] - 1)
    )
    max_route_operations = max(max(route_operations), route_operation_bound)
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and max_route_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and not compact_failures,
        "arms": G9_ARM_RESULTS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": max_route_operations,
        "compact_route_failures": compact_failures,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    compact_demo, compact_demo_operations = _compact_answer(demo)
    report["demo"] = {
        "instance": {key: value for key, value in demo.items() if key != "answer"},
        "rendered": render(demo),
        "answer": demo["answer"],
        "verify": list(verify(demo, demo["answer"])),
        "compact_answer": compact_demo,
        "compact_route_operations": compact_demo_operations,
        "enumerated_valid_answers": enumerate_all(demo),
        "candidate_space": search_space(demo),
    }
    report["all_passed"] = all(
        value.get("pass", True)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
