"""Verified generator for a layered Kidney Exchange problem family.

The source problem is the Kidney Exchange Problem (KEP) from arXiv:2603.18471.
Instances are directed compatibility graphs with altruistic donors, an edge-count
path bound, a cycle bound, and a target number of transplants.  This family uses
only length-two altruist-starting chains.  Its certificate is a complete list of
vertex-disjoint chains, checked directly against the compatibility arcs.

Generation is answer-first.  Each compatibility layer is a union of uniformly
sampled multiplicative perfect matchings over the nonzero residues modulo a
prime.  The recorded answer composes one sampled matching from each layer; every
other sampled matching has exactly the same distribution and is also usable.

Only the Python standard library is used.  Importing this module performs no I/O
and has no side effects.
"""

from __future__ import annotations

from collections import deque
import hashlib
import json
import math
import os
import random
import re
import time
from typing import Any, Callable


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "directed compatibility graph",
        "altruistic-donor set",
        "bounded altruist-starting chains",
    ],
    "verification_operations": [
        "directed-edge membership",
        "vertex-disjointness",
        "path-length and exact transplant-count checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Residue tags expose each compatibility layer as multiplicative copies "
        "of one neighborhood; without recognizing that symmetry, a solver must "
        "carry out two large matching computations by hand."
    ),
    "hardness_basis": (
        "Track B: two Hopcroft-Karp perfect matchings solve the layered regime in "
        "O(E sqrt(V)); at shipping seed 2024 they took 3,361 edge scans and about "
        "0.0005 s, while the symmetry route uses at most 240 exact arithmetic operations."
    ),
    "max_answer_tokens": 228,
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

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A canonical JSON list of n length-two paths [a,u,v], sorted by a, "
        "using every altruist, middle recipient, and terminal recipient exactly "
        "once.  Entries are distinct vertex IDs in 0..3n-1."
    ),
    "bounds": {
        "n_paths": "n",
        "vertices_per_path": 3,
        "vertex_min": 0,
        "vertex_max": "3*n-1",
        "all_vertices_used": True,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "degree": 2, "screen_restarts": 0},
    "easy": {"n": 22, "degree": 4, "screen_restarts": 64},
    "medium": {"n": 42, "degree": 7, "screen_restarts": 128},
    "hard": {"n": 60, "degree": 10, "screen_restarts": 256},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Under the supplied residue tags, each layer's neighborhoods are "
    "multiplicative copies modulo the displayed prime."
)
PLACEBO_HINT = (
    "Under the supplied residue tags, each layer's neighborhoods should be "
    "checked carefully against the displayed arcs."
)

# Filled after the three harness arms are run.  They are diagnostics, not gates.
G9_ARMS: dict = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = r"""
Paper reading (arXiv:2603.18471v2).  Section 1 gives the exact KEP definition:
G is a loopless directed compatibility graph; B is the altruist set; path and
cycle length mean number of edges; a feasible path starts in B and has length at
most l_p; a feasible cycle avoids B and has length at most l_c; and t counts the
total transplant edges.  This generator uses l_p=2, l_c=0, t=2n, and a layered
DAG, so every target-reaching packing is exactly n disjoint two-edge chains.

The certificate-producing question was asked before construction.  Theorem 1
gives a deterministic O*(6.855^t) algorithm for general KEP, Theorem 2 gives an
O*(2^|V|) dynamic program, and Theorem 3 gives a randomized O*(4^t) color-coding
algorithm.  Moreover, this generator's special layered regime decomposes into
two bipartite perfect matchings and is polynomial-time solvable by Hopcroft-Karp.
It therefore cannot honestly be Track A.  Track B measures whether a solver can
recognize and use the shorter multiplicative symmetry without a sandbox.

The paper's easy parameter regime is also respected rather than hidden: KEP is
FPT in t, so t grows with n on every named rung.  Section 3 first handles the
large-bound cases l_p>=t or l_c>=t by k-Path/Long Directed Cycle algorithms; our
bounds instead obey l_p,l_c<t, the regime of Lemma 3 and the representative-set
dynamic program.  Section 5 explicitly calls faster algorithms for small fixed
l_p,l_c an open practical direction; our polynomial layered subcase is disclosed
as such in TRACK and hardness_basis.

Construction samples every usable multiplier in a layer from the same uniform
distribution.  The answer merely chooses one of them in each layer and composes
the two identities, so it is known before any attack runs.  There is no special
planted multiplier.  The hardness screen only rejects draws solved by the four
declared no-tool heuristics; it never supplies the certificate.

The degree/magnitude outlier attack is defeated by regular layers and randomized
vertex IDs.  Lexicographic greedy and randomized greedy restarts are screened at
generation time.  The obvious equal-tag and additive-offset ansatzes fail because
multiplier 1 is excluded and the matching symmetry is multiplicative, not
additive.  The successful domain reference is reported separately, as Track B
requires: two Hopcroft-Karp matchings, composed through the middle layer.
"""


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _validate_parameters(n: int, degree: int, screen_restarts: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if not _is_prime(n + 1):
        raise ValueError("n + 1 must be prime")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer")
    # Multiplier 1 is reserved so that the equal-tag heuristic is not a witness.
    if not (1 <= degree <= n - 1):
        raise ValueError("degree must lie between 1 and n-1")
    if (
        isinstance(screen_restarts, bool)
        or not isinstance(screen_restarts, int)
        or screen_restarts < 0
    ):
        raise ValueError("screen_restarts must be a nonnegative integer")


def _vertex_maps(vertices: list[list[Any]]) -> tuple[dict[int, str], dict[int, int]]:
    role: dict[int, str] = {}
    tag: dict[int, int] = {}
    for row in vertices:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("malformed vertex record")
        vertex, vertex_role, residue = row
        role[int(vertex)] = str(vertex_role)
        tag[int(vertex)] = int(residue)
    return role, tag


def _instance_from_parts(
    n: int,
    degree: int,
    screen_restarts: int,
    vertices: list[list[Any]],
    edges: list[list[int]],
    answer: list[list[int]],
    build_round: int,
) -> dict:
    total = 3 * n
    adjacency = [[] for _ in range(total)]
    masks = [0] * total
    for edge in edges:
        u, v = edge
        adjacency[u].append(v)
        masks[u] |= 1 << v
    for row in adjacency:
        row.sort()
    role, _ = _vertex_maps(vertices)
    altruists = sorted(v for v, r in role.items() if r == "A")
    middle = sorted(v for v, r in role.items() if r == "U")
    terminal = sorted(v for v, r in role.items() if r == "V")
    return {
        "family": "layered_multiplicative_kidney_exchange",
        "n": n,
        "vertex_count": total,
        "modulus": n + 1,
        "degree": degree,
        "vertices": vertices,
        "edges": edges,
        "adjacency": adjacency,
        "adjacency_masks": masks,
        "altruists": altruists,
        "middle_vertices": middle,
        "terminal_vertices": terminal,
        "path_limit": 2,
        "cycle_limit": 0,
        "target": 2 * n,
        "screen_restarts": screen_restarts,
        "build_round": build_round,
        "answer": sorted(answer, key=lambda path: path[0]),
    }


def _raw_instance(
    n: int,
    degree: int,
    screen_restarts: int,
    rng: random.Random,
    build_round: int,
) -> dict:
    """Sample all matchings symmetrically, then compose two sampled identities."""
    modulus = n + 1
    multipliers_1 = rng.sample(range(2, modulus), degree)
    multipliers_2 = rng.sample(range(2, modulus), degree)

    abstract = [(role, tag) for role in ("A", "U", "V") for tag in range(1, modulus)]
    ids = list(range(3 * n))
    rng.shuffle(ids)
    by_abstract = {item: vertex for item, vertex in zip(abstract, ids)}
    vertices = [[vertex, role, tag] for (role, tag), vertex in by_abstract.items()]
    rng.shuffle(vertices)

    edges: list[list[int]] = []
    for tag in range(1, modulus):
        source = by_abstract[("A", tag)]
        for multiplier in multipliers_1:
            target_tag = multiplier * tag % modulus
            edges.append([source, by_abstract[("U", target_tag)]])
    for tag in range(1, modulus):
        source = by_abstract[("U", tag)]
        for multiplier in multipliers_2:
            target_tag = multiplier * tag % modulus
            edges.append([source, by_abstract[("V", target_tag)]])
    rng.shuffle(edges)

    # Every sampled multiplier is a valid perfect matching.  Choosing the
    # recorded pair uniformly means the certificate has the same distribution
    # as every apparent decoy matching.
    chosen_1 = rng.choice(multipliers_1)
    chosen_2 = rng.choice(multipliers_2)
    answer: list[list[int]] = []
    for tag in range(1, modulus):
        middle_tag = chosen_1 * tag % modulus
        terminal_tag = chosen_2 * middle_tag % modulus
        answer.append(
            [
                by_abstract[("A", tag)],
                by_abstract[("U", middle_tag)],
                by_abstract[("V", terminal_tag)],
            ]
        )
    return _instance_from_parts(
        n,
        degree,
        screen_restarts,
        vertices,
        edges,
        answer,
        build_round,
    )


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Build a KEP yes-instance and its chain packing by composition of identities.

    ``n`` is the number of altruists and also the number of middle and terminal
    recipients; consequently the graph has ``3*n`` vertices and the target is
    ``2*n`` transplants.  ``n+1`` must be prime.  Larger ``n`` enlarges both the
    matching computation and the paper's target parameter ``t``.
    """
    degree = params.pop("degree", 10)
    screen_restarts = params.pop("screen_restarts", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, degree, screen_restarts)

    rng = random.Random(seed)
    for build_round in range(64):
        inst = _raw_instance(n, degree, screen_restarts, rng, build_round)
        if not screen_restarts:
            return inst
        attacks = _run_no_tool_attacks(inst, screen_restarts)
        if not any(candidate is not None and verify(inst, candidate)[0] for candidate in attacks.values()):
            return inst
    raise RuntimeError("could not draw an instance that passed the heuristic screen")


def render(inst: dict) -> str:
    """Return the complete, self-contained question shown to a solver."""
    n = inst["n"]
    vertex_rows = "\n".join(
        f"{vertex}: {role} {tag}"
        for vertex, role, tag in sorted(inst["vertices"], key=lambda row: row[0])
    )
    adjacency_rows = []
    for source, targets in enumerate(inst["adjacency"]):
        if targets:
            adjacency_rows.append(f"{source}: " + " ".join(map(str, targets)))
    adjacency = "\n".join(adjacency_rows)

    statement = f"""Kidney exchange: find a full packing of length-two chains

There are {3 * n} vertices, numbered 0 through {3 * n - 1}.  Each vertex has a
role and a residue tag in the table below.  Role A means an altruistic donor;
roles U and V mean patient-donor pairs.  Tags are unique within each role and
range from 1 through {n}.  The displayed modulus is the prime {inst['modulus']}.
Tags and the modulus are auxiliary labels; whether a transplant is compatible is
determined solely by the directed arcs listed below.

A directed arc x -> y means x's donor is compatible with y's patient.  No arc
other than a listed arc exists.  A chain is a sequence [a,u,v] of three distinct
vertices with roles A,U,V in that order and with both arcs a->u and u->v.  Such a
chain has length 2 because length counts arcs.  Chains must be vertex-disjoint.
Cycles are forbidden (cycle limit 0), and the path/chain length limit is 2.

Find exactly {n} vertex-disjoint chains, for a total of {2 * n} transplant arcs.
Equivalently, use every A, every U, and every V vertex exactly once.  Vertex IDs
are 0-based; residue tags are 1-based.  Sort the output paths by their first
(altruist) vertex ID.  Repeats are not allowed, and the order of the paths has no
mathematical significance beyond this canonical output convention.

Vertex table, as "ID: role tag":
{vertex_rows}

Complete outgoing adjacency list, as "source: targets":
{adjacency}

Give your final answer inside <answer></answer> tags, as one JSON array containing
exactly {n} arrays [a,u,v] in the canonical order specified above.
Example format: <answer>[[0, 7, 13], [2, 9, 17]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON list, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for raw in reversed(blocks):
        body = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
        if fenced:
            body = fenced.group(1).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(value, list):
            continue
        if not all(isinstance(path, list) for path in value):
            continue
        if not all(
            isinstance(vertex, int) and not isinstance(vertex, bool)
            for path in value
            for vertex in path
        ):
            continue
        return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid target-reaching KEP packing; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    expected = inst["n"]
    if len(answer) != expected:
        return False, f"expected {expected} chains, got {len(answer)}"

    total_vertices = inst["vertex_count"]
    altruists = set(inst["altruists"])
    middle = set(inst["middle_vertices"])
    terminal = set(inst["terminal_vertices"])
    seen: set[int] = set()

    # Shape, type, range, role, and global disjointness are checked before arcs
    # so corruptions receive stable, discriminating reasons.
    for index, path in enumerate(answer):
        if not isinstance(path, list) or len(path) != 3:
            got = len(path) if isinstance(path, list) else "non-list"
            return False, f"chain {index} has shape {got}; expected three vertices"
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in path):
            return False, f"chain {index} contains a non-integer vertex"
        if any(v < 0 or v >= total_vertices for v in path):
            return False, f"chain {index} contains an out-of-range vertex"
        a, u, v = path
        if a not in altruists or u not in middle or v not in terminal:
            return False, f"chain {index} is not in A,U,V role order"
        for vertex in path:
            if vertex in seen:
                return False, f"vertex {vertex} appears in more than one chain"
            seen.add(vertex)

    for index, (a, u, v) in enumerate(answer):
        if not ((inst["adjacency_masks"][a] >> u) & 1):
            return False, f"chain {index} uses missing arc {a}->{u}"
        if not ((inst["adjacency_masks"][u] >> v) & 1):
            return False, f"chain {index} uses missing arc {u}->{v}"

    if seen != altruists | middle | terminal:
        return False, "the chains do not cover every vertex exactly once"
    if 2 * len(answer) != inst["target"]:
        return False, "the packing does not reach the transplant target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-aware space of two full matchings."""
    altruists = sorted(inst["altruists"])
    middle = sorted(inst["middle_vertices"])
    terminal = sorted(inst["terminal_vertices"])
    rng.shuffle(middle)
    rng.shuffle(terminal)
    terminal_for_middle = {u: v for u, v in zip(sorted(middle), terminal)}
    answer = [[a, u, terminal_for_middle[u]] for a, u in zip(altruists, middle)]
    return sorted(answer, key=lambda path: path[0])


def search_space(inst: dict) -> int | None:
    """Count the exact bounded language sampled by random_candidate."""
    return math.factorial(inst["n"]) ** 2


def _permanent_count(rows: list[list[int]], right_vertices: list[int]) -> int:
    index = {vertex: i for i, vertex in enumerate(right_vertices)}
    masks = []
    for row in rows:
        mask = 0
        for vertex in row:
            mask |= 1 << index[vertex]
        masks.append(mask)
    size = len(rows)
    dp = {0: 1}
    for left in range(size):
        nxt: dict[int, int] = {}
        for used, count in dp.items():
            available = masks[left] & ~used
            while available:
                bit = available & -available
                available -= bit
                nxt[used | bit] = nxt.get(used | bit, 0) + count
        dp = nxt
    return dp.get((1 << size) - 1, 0)


def enumerate_all(inst: dict) -> int | None:
    """Exactly count witnesses for small n via two permanent computations."""
    n = inst["n"]
    if n > 12:
        return None
    altruists = sorted(inst["altruists"])
    middle = sorted(inst["middle_vertices"])
    terminal = sorted(inst["terminal_vertices"])
    first_rows = [inst["adjacency"][vertex] for vertex in altruists]
    second_rows = [inst["adjacency"][vertex] for vertex in middle]
    return _permanent_count(first_rows, middle) * _permanent_count(second_rows, terminal)


def _hopcroft_karp(
    left: list[int], right: list[int], adjacency: list[list[int]]
) -> tuple[dict[int, int] | None, int]:
    """Maximum bipartite matching with an exact edge-inspection counter."""
    right_set = set(right)
    filtered = {u: [v for v in adjacency[u] if v in right_set] for u in left}
    pair_left: dict[int, int | None] = {u: None for u in left}
    pair_right: dict[int, int | None] = {v: None for v in right}
    distance: dict[int, int] = {}
    edge_scans = 0
    infinity = len(left) + 1

    def bfs() -> bool:
        nonlocal edge_scans
        queue: deque[int] = deque()
        found = False
        for u in left:
            if pair_left[u] is None:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = infinity
        while queue:
            u = queue.popleft()
            for v in filtered[u]:
                edge_scans += 1
                mate = pair_right[v]
                if mate is None:
                    found = True
                elif distance[mate] == infinity:
                    distance[mate] = distance[u] + 1
                    queue.append(mate)
        return found

    def dfs(u: int) -> bool:
        nonlocal edge_scans
        for v in filtered[u]:
            edge_scans += 1
            mate = pair_right[v]
            if mate is None or (distance[mate] == distance[u] + 1 and dfs(mate)):
                pair_left[u] = v
                pair_right[v] = u
                return True
        distance[u] = infinity
        return False

    cardinality = 0
    while bfs():
        for u in left:
            if pair_left[u] is None and dfs(u):
                cardinality += 1
    if cardinality != len(left):
        return None, edge_scans
    return {u: int(v) for u, v in pair_left.items() if v is not None}, edge_scans


def _candidate_from_matchings(
    first: dict[int, int] | None, second: dict[int, int] | None
) -> list[list[int]] | None:
    if first is None or second is None:
        return None
    if any(u not in second for u in first.values()):
        return None
    return sorted([[a, u, second[u]] for a, u in first.items()], key=lambda path: path[0])


def _reference_solution(inst: dict) -> tuple[list[list[int]] | None, int]:
    first, scans_1 = _hopcroft_karp(
        sorted(inst["altruists"]),
        sorted(inst["middle_vertices"]),
        inst["adjacency"],
    )
    second, scans_2 = _hopcroft_karp(
        sorted(inst["middle_vertices"]),
        sorted(inst["terminal_vertices"]),
        inst["adjacency"],
    )
    return _candidate_from_matchings(first, second), scans_1 + scans_2


def _greedy_matching(
    sources: list[int],
    allowed_targets: set[int],
    adjacency: list[list[int]],
    score: Callable[[int, int], tuple[Any, ...]],
) -> dict[int, int] | None:
    used: set[int] = set()
    result: dict[int, int] = {}
    for source in sources:
        options = [v for v in adjacency[source] if v in allowed_targets and v not in used]
        if not options:
            return None
        target = min(options, key=lambda v: score(source, v))
        used.add(target)
        result[source] = target
    return result


def _attack_greedy(inst: dict, kind: str) -> list[list[int]] | None:
    adjacency = inst["adjacency"]
    indegree = [0] * inst["vertex_count"]
    for targets in adjacency:
        for target in targets:
            indegree[target] += 1
    altruists = sorted(inst["altruists"])
    middle = set(inst["middle_vertices"])
    terminal = set(inst["terminal_vertices"])
    if kind == "smallest":
        score = lambda _u, v: (v,)
    else:
        # A construction-aware per-vertex outlier probe.  All legal destinations
        # tie in degree; random IDs make the magnitude tie-break uninformative.
        score = lambda u, v: (indegree[v] + len(adjacency[v]), -abs(v - u), v)
    first = _greedy_matching(altruists, middle, adjacency, score)
    second = _greedy_matching(sorted(middle), terminal, adjacency, score)
    return _candidate_from_matchings(first, second)


def _random_greedy_matching(
    sources: list[int], targets: set[int], adjacency: list[list[int]], rng: random.Random
) -> dict[int, int] | None:
    order = list(sources)
    rng.shuffle(order)
    used: set[int] = set()
    result: dict[int, int] = {}
    for source in order:
        options = [v for v in adjacency[source] if v in targets and v not in used]
        if not options:
            return None
        target = rng.choice(options)
        result[source] = target
        used.add(target)
    return result


def _attack_random_restart(inst: dict, restarts: int) -> list[list[int]] | None:
    digest = hashlib.sha256(
        json.dumps(inst["edges"], separators=(",", ":")).encode()
    ).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    altruists = sorted(inst["altruists"])
    middle = set(inst["middle_vertices"])
    terminal = set(inst["terminal_vertices"])
    for _ in range(restarts):
        first = _random_greedy_matching(altruists, middle, inst["adjacency"], rng)
        second = _random_greedy_matching(sorted(middle), terminal, inst["adjacency"], rng)
        candidate = _candidate_from_matchings(first, second)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _tag_maps(inst: dict) -> tuple[dict[int, int], dict[tuple[str, int], int]]:
    role, tag = _vertex_maps(inst["vertices"])
    by_role_tag = {(role[v], tag[v]): v for v in role}
    return tag, by_role_tag


def _attack_additive_tags(inst: dict) -> list[list[int]] | None:
    """Try the obvious equal/constant-additive-tag pattern, not multiplication."""
    modulus = inst["modulus"]
    tag, by_role_tag = _tag_maps(inst)
    masks = inst["adjacency_masks"]

    def shifts(source_role: str, target_role: str) -> list[int]:
        good = []
        for shift in range(modulus):
            valid = True
            for source_tag in range(1, modulus):
                target_tag = (source_tag - 1 + shift) % inst["n"] + 1
                source = by_role_tag[(source_role, source_tag)]
                target = by_role_tag[(target_role, target_tag)]
                if not ((masks[source] >> target) & 1):
                    valid = False
                    break
            if valid:
                good.append(shift)
        return good

    first_shifts = shifts("A", "U")
    second_shifts = shifts("U", "V")
    if not first_shifts or not second_shifts:
        return None
    shift_1, shift_2 = first_shifts[0], second_shifts[0]
    answer = []
    for a in inst["altruists"]:
        source_tag = tag[a]
        middle_tag = (source_tag - 1 + shift_1) % inst["n"] + 1
        terminal_tag = (middle_tag - 1 + shift_2) % inst["n"] + 1
        answer.append(
            [a, by_role_tag[("U", middle_tag)], by_role_tag[("V", terminal_tag)]]
        )
    return sorted(answer, key=lambda path: path[0])


def _run_no_tool_attacks(inst: dict, restarts: int) -> dict[str, list[list[int]] | None]:
    return {
        "outlier_degree_magnitude": _attack_greedy(inst, "outlier"),
        "greedy_smallest_id": _attack_greedy(inst, "smallest"),
        f"random_greedy_restart_{restarts}": _attack_random_restart(inst, restarts),
        "equal_or_additive_tag_ansatz": _attack_additive_tags(inst),
    }


def canonical_key(inst: dict) -> str:
    """Canonicalize vertex IDs and input order through the supplied role/tag labels."""
    role, tag = _vertex_maps(inst["vertices"])
    arcs = sorted(
        (role[u], tag[u], role[v], tag[v])
        for u, v in inst["edges"]
    )
    payload = {
        "n": inst["n"],
        "path_limit": inst["path_limit"],
        "cycle_limit": inst["cycle_limit"],
        "target": inst["target"],
        "arcs": arcs,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Hide the same-size witness more deeply before lengthening it."""
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 60))
    degree = int(current.get("degree", 10))
    restarts = int(current.get("screen_restarts", 256))
    if n <= 60 and degree < 12:
        return {"n": n, "degree": 12, "screen_restarts": max(512, restarts)}
    for harder_n in (66, 70, 72):
        if n < harder_n:
            # At n=72 the intended route is 4n=288 exact arithmetic operations.
            return {
                "n": harder_n,
                "degree": max(12, degree),
                "screen_restarts": max(512, restarts),
            }
    # The next supported n is 78 (modulus 79), where the intended route needs
    # 312 operations.  The answer still fits, but the no-tool effort cap does not.
    return "cap_bound"


def _count_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_atoms(v) for v in value)
    return 1


def _corruptions(inst: dict) -> dict[str, object]:
    answer = json.loads(json.dumps(inst["answer"]))
    dropped = answer[:-1]
    swapped = json.loads(json.dumps(answer))
    swapped[0][1], swapped[0][2] = swapped[0][2], swapped[0][1]
    duplicated = json.loads(json.dumps(answer))
    duplicated[1][1] = duplicated[0][1]
    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0] = inst["vertex_count"]
    return {
        "empty": [],
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "out_of_range": out_of_range,
    }


def _relabel(inst: dict, rng: random.Random, permute_vertices: bool, reorder: bool) -> dict:
    total = inst["vertex_count"]
    permutation = list(range(total))
    if permute_vertices:
        rng.shuffle(permutation)
    vertices = [[permutation[v], role, tag] for v, role, tag in inst["vertices"]]
    edges = [[permutation[u], permutation[v]] for u, v in inst["edges"]]
    answer = [[permutation[v] for v in path] for path in inst["answer"]]
    if reorder:
        rng.shuffle(vertices)
        rng.shuffle(edges)
        rng.shuffle(answer)
    return _instance_from_parts(
        inst["n"],
        inst["degree"],
        inst["screen_restarts"],
        vertices,
        edges,
        answer,
        inst["build_round"],
    )


def selftest() -> dict:
    """Run gates G1--G9 and return their machine-readable measurements."""
    report: dict[str, Any] = {
        "paper": "2603.18471",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every named rung over several independent seeds.
    g1_attempts = 0
    g1_successes = 0
    g1_json_native = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            if verify(inst, inst["answer"])[0]:
                g1_successes += 1
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                g1_json_native += 1
    report["G1_planted_verifies"] = {
        "pass": g1_successes == g1_attempts and g1_json_native == g1_attempts,
        "verified": g1_successes,
        "attempts": g1_attempts,
        "json_native": g1_json_native,
    }

    shipping = make_instance(seed=2024, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five corruption modes and five stable, distinct reasons.
    rejection_reasons = {}
    for name, candidate in _corruptions(shipping).items():
        ok, reason = verify(shipping, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejection_reasons.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose/fence round-trip and malformed-input behavior.
    wire = json.dumps(shipping["answer"])
    response = f"I matched both layers.\n<answer>```json\n{wire}\n```</answer>\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("no tagged answer") is None,
        "prose_and_fence": parsed == shipping["answer"],
        "garbage_is_none": parse_answer("<answer>{not json}</answer>") is None,
    }

    # G4/G5: structure-aware density at the shipping preset.
    guess_rng = random.Random(0x260318471)
    sample_total = 200_000
    sample_hits = 0
    for _ in range(sample_total):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            sample_hits += 1
    observed = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed,
        "candidate_space": search_space(shipping),
        "prior": "uniform over two full bijections, with all shape/coverage rules enforced",
    }

    started = time.perf_counter()
    reference_answer, reference_scans = _reference_solution(shipping)
    reference_seconds = time.perf_counter() - started
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_exact = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and demo_exact is not None and observed < 1e-6,
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_observed_solution_fraction": observed,
        "shipping_exact_solution_count": None,
        "demo_exact_solution_count": demo_exact,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_seconds": reference_seconds,
        "baseline_edge_scans": reference_scans,
        "baseline_solved": reference_ok,
    }

    # G6: attacks fail; the polynomial reference is intentionally separate.
    attack_names = [
        "outlier_degree_magnitude",
        "greedy_smallest_id",
        "random_greedy_restart_256",
        "equal_or_additive_tag_ansatz",
    ]
    attack_successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_total_scans = 0
    reference_total_seconds = 0.0
    panel_seeds = list(range(100, 108))
    for seed in panel_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks = _run_no_tool_attacks(inst, 256)
        for name in attack_names:
            candidate = attacks[name]
            if candidate is not None and verify(inst, candidate)[0]:
                attack_successes[name] += 1
        started = time.perf_counter()
        candidate, scans = _reference_solution(inst)
        reference_total_seconds += time.perf_counter() - started
        reference_total_scans += scans
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1
    attack_report = {
        name: {"successes": attack_successes[name], "attempts": len(panel_seeds)}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attack_successes.values())
        and reference_successes == len(panel_seeds),
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "two Hopcroft-Karp bipartite perfect matchings",
            "complexity": "O(E sqrt(V))",
            "wall_clock_sec": reference_total_seconds,
            "edge_scans": reference_total_scans,
            "attempts": len(panel_seeds),
            "successes": reference_successes,
            "solves": f"{reference_successes}/{len(panel_seeds)}, as expected",
        },
    }

    # G7: more than double the shipping n while preserving exact construction.
    doubled_n = next(
        candidate - 1
        for candidate in range(2 * shipping["n"] + 1, 4 * shipping["n"] + 3)
        if _is_prime(candidate)
    )
    doubled = make_instance(
        n=doubled_n,
        seed=991,
        degree=DIFFICULTY[SHIPPING_DIFFICULTY]["degree"],
        screen_restarts=0,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n >= 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "scale_factor": doubled_n / shipping["n"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_verified": doubled_ok,
    }

    # G8: ID relabeling, input reordering, their composition, and distinctness.
    invariance_checks = 0
    carried_witness_checks = 0
    invariance_failures = 0
    carried_failures = 0
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY["medium"])
        original = canonical_key(inst)
        variants = [
            _relabel(inst, random.Random(seed + 1), False, True),
            _relabel(inst, random.Random(seed + 2), True, False),
            _relabel(inst, random.Random(seed + 3), True, True),
            _relabel(inst, random.Random(seed + 4), True, True),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != original:
                invariance_failures += 1
            carried_witness_checks += 1
            if not verify(variant, variant["answer"])[0]:
                carried_failures += 1
    unrelated_keys = {
        canonical_key(make_instance(seed=20_000 + seed, **DIFFICULTY["medium"]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariance_failures == 0
        and carried_failures == 0
        and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": invariance_failures,
        "carried_witness_checks": carried_witness_checks,
        "carried_witness_failures": carried_failures,
        "unrelated_distinct": len(unrelated_keys),
        "unrelated_attempts": 20,
        "transformations": [
            "input row/edge reorder",
            "arbitrary vertex-ID permutation",
            "vertex permutation composed with input reorder",
        ],
    }

    answer_blob = json.dumps(shipping["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _count_atoms(shipping["answer"])
    intended_operations = 4 * shipping["n"]
    hinted_rate = (
        G9_ARMS["hinted"]["solved"] / G9_ARMS["hinted"]["attempts"]
        if G9_ARMS["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        G9_ARMS["placebo"]["solved"] / G9_ARMS["placebo"]["attempts"]
        if G9_ARMS["placebo"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300,
        "arms": G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "hardened"
            if G9_ARMS["hinted"]["attempts"]
            and G9_ARMS["hinted"]["solved"] == 0
            else "too_easy"
            if G9_ARMS["hinted"]["attempts"]
            else "not_yet_run"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_model": (
            "two modular multiplications and two modular reductions per chain; "
            "global vertex IDs are table lookups"
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
