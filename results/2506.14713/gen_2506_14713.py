"""Verified generator for arXiv:2506.14713.

The generated task is Linear Literal-Planar 3-SAT Reconfiguration.  Section 7.1
of the paper maps legal orientations of a planar cubic NCL graph to satisfying
assignments of a linear literal-planar 3-CNF.  We sample a legal NCL walk first
and only afterwards expose its endpoint assignments, so the witness is known by
construction and is never obtained by solving the emitted instance.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
import os
import random
import re
import time
from functools import lru_cache


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "linear literal-planar 3-CNF formula",
        "two satisfying Boolean assignments",
        "single-variable flip sequence",
    ],
    "verification_operations": [
        "exact Boolean clause evaluation",
        "single-bit flip simulation",
        "exact endpoint comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 7.1, Theorem 7.1 and its NCL encoding: legal constraint-graph "
        "orientations are exactly satisfying assignments, and edge reversals are "
        "exactly single-variable flips"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A satisfying assignment is an orientation with at least two units of "
        "inflow at every hidden constraint node; without that invariant the solver "
        "must search the exponentially large reconfiguration graph."
    ),
    "hardness_basis": (
        "Track A: Theorem 7.1 proves PSPACE-completeness for the Section 7.1 "
        "planar-cubic-NCL reduction image; at the shipping regime n=80 and a "
        "160-flip witness, memoized A* exhausts 100000 states (measured wall-clock "
        "cost is recorded by selftest) without finding a path."
    ),
    # Exact worst-case compact JSON bound at this preset: two brackets, 159
    # commas, and 160 three-digit variable identifiers = 641 chars = 161 tokens.
    "max_answer_tokens": 161,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A sequence of exactly B one-indexed variable numbers.  Repetitions are "
        "allowed; the parity of every variable's occurrence is forced by the two "
        "endpoint assignments."
    ),
    "bounds": {
        "max_sequence_length": 256,
        "variable_range": "1..q, where q is the displayed number of variables",
        "endpoint_parity_required": True,
    },
}

DIFFICULTY = {
    "demo": {
        "n": 8,
        "path_length": 6,
        "and_rate": 0.70,
        "min_hamming": 0,
        "scan_steps": 6,
        "screen_restarts": 0,
    },
    "easy": {
        "n": 80,
        "path_length": 160,
        "and_rate": 0.92,
        "min_hamming": 22,
        "scan_steps": 22000,
        "screen_restarts": 96,
    },
    "medium": {
        "n": 100,
        "path_length": 160,
        "and_rate": 0.94,
        "min_hamming": 24,
        "scan_steps": 26000,
        "screen_restarts": 112,
    },
    "hard": {
        "n": 120,
        "path_length": 160,
        "and_rate": 0.96,
        "min_hamming": 26,
        "scan_steps": 32000,
        "screen_restarts": 128,
    },
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The legal assignments are orientations of a planar cubic constraint graph, "
    "with every clause expressing one node's minimum inflow."
)
PLACEBO_HINT = (
    "The numbered variables and clauses should be tracked carefully throughout "
    "the requested sequence of exact local changes."
)

# Filled from the separately preserved harden.py transcripts after the three arms
# are run.  They are diagnostics; only the size and operation caps gate shipping.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
}

NOTES = (
    "Section 2 fixes 3-CNF to mean clauses of at most three literals and defines "
    "linearity literally: a clause shares a literal with at most one other clause, "
    "and shares at most one literal there. Section 3 defines literal-planarity. "
    "Theorem 7.1 and its proof supply the usable family: an OR NCL node becomes one "
    "3-clause, an AND node becomes two 2-clauses sharing only the heavy-edge "
    "literal, and a legal NCL edge reversal is one satisfying-assignment flip. "
    "The polynomial-time result in Section 5 only constructs the separating "
    "literal cycle for this reduction image; it does not produce a reconfiguration "
    "path. The generator plants no statistically special clause: it samples a "
    "legal walk before choosing the endpoints, permutes variables and clauses, and "
    "screens endpoint/outlier order, deterministic greedy, and target-biased random "
    "restart attacks. Memoized A* is retained as the domain-standard attack."
)


def _prism_edges(n: int) -> list[tuple[int, int]]:
    """A planar cubic prism, represented as a Hamiltonian cycle plus a matching."""

    if n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    r = n // 2
    cycle = [(i, i + 1) for i in range(r - 1)]
    cycle.append((r - 1, n - 1))
    cycle.extend((r + i, r + i - 1) for i in range(r - 1, 0, -1))
    cycle.append((r, 0))
    matching = [(0, r - 1), (r, n - 1)]
    matching.extend((i, r + i) for i in range(1, r - 1))
    return cycle + matching


def _build_ncl(n: int, rng: random.Random, and_rate: float) -> dict:
    """Build a planar cubic NCL graph and one legal orientation without search."""

    base_edges = _prism_edges(n)
    # The first n edges form a directed Hamiltonian cycle.  Every base vertex
    # therefore has one incoming heavy edge; a random matching supplies a second
    # incoming edge to exactly half of them.
    base_bits = [1] * n + [rng.randrange(2) for _ in range(n // 2)]
    base_inc = [[] for _ in range(n)]
    indegree = [0] * n
    for ei, (u, v) in enumerate(base_edges):
        base_inc[u].append(ei)
        base_inc[v].append(ei)
        indegree[v if base_bits[ei] else u] += 1

    expanded = {
        v for v in range(n) if indegree[v] == 2 and rng.random() < and_rate
    }
    # Keep both node types in every non-demo instance.  Changing an arbitrary
    # mark here remains constructive because only indegree-two vertices may be
    # expanded into the AND triangle below.
    candidates = [v for v in range(n) if indegree[v] == 2]
    if n >= 12 and not expanded:
        expanded.add(candidates[0])
    if len(expanded) == n:
        expanded.remove(max(expanded))

    port_node: dict[tuple[int, int], int] = {}
    node_types: list[str] = []
    node_base: list[int] = []
    for v in range(n):
        incident = sorted(base_inc[v])
        if v in expanded:
            for ei in incident:
                port_node[(v, ei)] = len(node_types)
                node_types.append("AND")
                node_base.append(v)
        else:
            q = len(node_types)
            node_types.append("OR")
            node_base.append(v)
            for ei in incident:
                port_node[(v, ei)] = q

    edges: list[tuple[int, int]] = []
    weights: list[int] = []
    bits: list[int] = []
    external_count = len(base_edges)
    for ei, (u, v) in enumerate(base_edges):
        edges.append((port_node[(u, ei)], port_node[(v, ei)]))
        weights.append(2)
        bits.append(base_bits[ei])

    for v in sorted(expanded):
        incident = sorted(base_inc[v])
        nodes = [port_node[(v, ei)] for ei in incident]
        outgoing_ports = []
        for k, ei in enumerate(incident):
            u, w = base_edges[ei]
            head = w if base_bits[ei] else u
            if head != v:
                outgoing_ports.append(k)
        if len(outgoing_ports) != 1:
            raise AssertionError("inverse construction expected one outgoing port")
        sink = outgoing_ports[0]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges.append((nodes[a], nodes[b]))
            weights.append(1)
            if a == sink:
                bits.append(0)  # nodes[b] -> nodes[a]
            elif b == sink:
                bits.append(1)  # nodes[a] -> nodes[b]
            else:
                bits.append(rng.randrange(2))

    incidence = [[] for _ in node_types]
    for ei, (u, v) in enumerate(edges):
        incidence[u].append(ei)
        incidence[v].append(ei)

    return {
        "edges": edges,
        "weights": weights,
        "bits": bits,
        "node_types": node_types,
        "node_base": node_base,
        "incidence": incidence,
        "external_count": external_count,
        "expanded_count": len(expanded),
    }


def _inward_literal(edge_index: int, node: int, edges: list[tuple[int, int]]) -> int:
    u, v = edges[edge_index]
    return edge_index + 1 if node == v else -(edge_index + 1)


def _formula_from_ncl(ncl: dict) -> list[list[int]]:
    """The clauses in the proof of Theorem 7.1, before random relabelling."""

    clauses: list[list[int]] = []
    edges = ncl["edges"]
    weights = ncl["weights"]
    for node, kind in enumerate(ncl["node_types"]):
        incident = ncl["incidence"][node]
        if kind == "OR":
            if len(incident) != 3 or any(weights[e] != 2 for e in incident):
                raise AssertionError("malformed OR node")
            clauses.append([_inward_literal(e, node, edges) for e in incident])
        else:
            heavy = [e for e in incident if weights[e] == 2]
            light = [e for e in incident if weights[e] == 1]
            if len(heavy) != 1 or len(light) != 2:
                raise AssertionError("malformed AND node")
            h = _inward_literal(heavy[0], node, edges)
            clauses.append([h, _inward_literal(light[0], node, edges)])
            clauses.append([h, _inward_literal(light[1], node, edges)])
    return clauses


def _bits_to_string(bits: int, q: int) -> str:
    return "".join("1" if (bits >> i) & 1 else "0" for i in range(q))


def _string_to_bits(s: str) -> int:
    out = 0
    for i, ch in enumerate(s):
        if ch == "1":
            out |= 1 << i
    return out


def _formula_index(clauses: list[list[int]], q: int) -> tuple[list[list[int]], list[tuple[int, int]]]:
    occurrence = [[] for _ in range(q)]
    masks: list[tuple[int, int]] = []
    for ci, clause in enumerate(clauses):
        pos = 0
        neg = 0
        for lit in clause:
            v = abs(lit) - 1
            occurrence[v].append(ci)
            if lit > 0:
                pos |= 1 << v
            else:
                neg |= 1 << v
        masks.append((pos, neg))
    return occurrence, masks


def _satisfies_masks(bits: int, masks: list[tuple[int, int]]) -> bool:
    return all((bits & pos) or ((~bits) & neg) for pos, neg in masks)


def _flip_legal(inst: dict, bits: int, variable: int) -> bool:
    """Whether flipping zero-indexed ``variable`` preserves all clauses."""

    new_bits = bits ^ (1 << variable)
    for ci in inst["_occurrence"][variable]:
        pos, neg = inst["_masks"][ci]
        if not ((new_bits & pos) or ((~new_bits) & neg)):
            return False
    return True


def _legal_flips(inst: dict, bits: int, variables=None) -> list[int]:
    pool = range(inst["num_variables"]) if variables is None else variables
    return [v for v in pool if _flip_legal(inst, bits, v)]


def _pad_path(inst: dict, path: list[int]) -> list[int] | None:
    """Pad a short zero-indexed path to the required length with reversible pairs."""

    B = inst["max_flips"]
    if len(path) > B or (B - len(path)) % 2:
        return None
    start = _string_to_bits(inst["start"])
    if path:
        pad_var = path[0]
    else:
        legal = _legal_flips(inst, start)
        if not legal:
            return None
        pad_var = legal[0]
    padded = [pad_var, pad_var] * ((B - len(path)) // 2) + path
    return [v + 1 for v in padded]


def _attack_outlier_order(inst: dict) -> list[int] | None:
    """Try endpoint differences in orders suggested by per-variable statistics."""

    start = _string_to_bits(inst["start"])
    goal = _string_to_bits(inst["goal"])
    differing = [v for v in range(inst["num_variables"]) if ((start ^ goal) >> v) & 1]
    stats = []
    for v in differing:
        occ = inst["_occurrence"][v]
        pos = sum(inst["clauses"][ci].count(v + 1) for ci in occ)
        stats.append((len(occ), pos, v))
    for reverse in (False, True):
        bits = start
        path: list[int] = []
        for _, _, v in sorted(stats, reverse=reverse):
            if not _flip_legal(inst, bits, v):
                break
            bits ^= 1 << v
            path.append(v)
        if bits == goal:
            return _pad_path(inst, path)
    return None


def _attack_greedy(inst: dict) -> list[int] | None:
    """Always make the legal target-directed flip with the tightest clauses."""

    bits = _string_to_bits(inst["start"])
    goal = _string_to_bits(inst["goal"])
    path: list[int] = []
    q = inst["num_variables"]
    for _ in range(q + 1):
        if bits == goal:
            return _pad_path(inst, path)
        differing = [v for v in range(q) if ((bits ^ goal) >> v) & 1]
        legal = [v for v in differing if _flip_legal(inst, bits, v)]
        if not legal:
            return None

        def score(v: int) -> tuple[int, int]:
            new_bits = bits ^ (1 << v)
            slack = 0
            for ci in inst["_occurrence"][v]:
                clause = inst["clauses"][ci]
                sat = 0
                for lit in clause:
                    val = (new_bits >> (abs(lit) - 1)) & 1
                    sat += bool(val) if lit > 0 else not bool(val)
                slack += sat
            return (slack, -v)

        v = max(legal, key=score)
        bits ^= 1 << v
        path.append(v)
    return None


def _attack_random_restart(inst: dict, restarts: int = 96) -> list[int] | None:
    """Target-biased random walks with mild detours, using only public data."""

    material = (inst["start"] + "|" + inst["goal"] + "|" + repr(inst["clauses"])).encode()
    seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    rng = random.Random(seed)
    start = _string_to_bits(inst["start"])
    goal = _string_to_bits(inst["goal"])
    q = inst["num_variables"]
    B = inst["max_flips"]
    for _ in range(restarts):
        bits = start
        path: list[int] = []
        previous = -1
        for _step in range(B):
            if bits == goal:
                return _pad_path(inst, path)
            legal = _legal_flips(inst, bits)
            if not legal:
                break
            direct = [v for v in legal if ((bits ^ goal) >> v) & 1]
            if direct and rng.random() < 0.84:
                choices = direct
            else:
                choices = [v for v in legal if v != previous] or legal
            v = rng.choice(choices)
            bits ^= 1 << v
            path.append(v)
            previous = v
        if bits == goal:
            return _pad_path(inst, path)
    return None


def _attack_astar(inst: dict, node_budget: int = 100_000) -> tuple[list[int] | None, int, float]:
    """Memoized A* in the satisfying-assignment reconfiguration graph."""

    start_time = time.perf_counter()
    start = _string_to_bits(inst["start"])
    goal = _string_to_bits(inst["goal"])
    B = inst["max_flips"]
    heap = [((start ^ goal).bit_count(), 0, start)]
    best = {start: 0}
    parent: dict[int, tuple[int, int]] = {}
    expanded = 0
    while heap and expanded < node_budget:
        _, depth, bits = heapq.heappop(heap)
        if best.get(bits) != depth:
            continue
        expanded += 1
        if bits == goal:
            path: list[int] = []
            cur = bits
            while cur != start:
                prev, var = parent[cur]
                path.append(var)
                cur = prev
            path.reverse()
            return _pad_path(inst, path), expanded, time.perf_counter() - start_time
        if depth >= B:
            continue
        # Target-directed variables first is substantially stronger than plain BFS
        # on these planted walks, while the Hamming distance remains admissible.
        variables = list(range(inst["num_variables"]))
        variables.sort(key=lambda v: (0 if ((bits ^ goal) >> v) & 1 else 1, v))
        for v in variables:
            if not _flip_legal(inst, bits, v):
                continue
            nxt = bits ^ (1 << v)
            nd = depth + 1
            if nd + (nxt ^ goal).bit_count() > B:
                continue
            if nd >= best.get(nxt, B + 1):
                continue
            best[nxt] = nd
            parent[nxt] = (bits, v)
            heapq.heappush(heap, (nd + (nxt ^ goal).bit_count(), nd, nxt))
    return None, expanded, time.perf_counter() - start_time


def _public_instance(
    n: int,
    seed: int,
    clauses: list[list[int]],
    start_bits: int,
    goal_bits: int,
    path: list[int],
    expanded_count: int,
) -> dict:
    q = max(abs(lit) for clause in clauses for lit in clause)
    occurrence, masks = _formula_index(clauses, q)
    return {
        "paper": "arXiv:2506.14713",
        "family": "Linear Literal-Planar 3-SAT Reconfiguration",
        "n": n,
        "seed": seed,
        "num_variables": q,
        "num_clauses": len(clauses),
        "clauses": clauses,
        "start": _bits_to_string(start_bits, q),
        "goal": _bits_to_string(goal_bits, q),
        "max_flips": len(path),
        "construction_summary": {
            "planar_cubic_base_vertices": n,
            "expanded_AND_base_vertices": expanded_count,
            "paper_reduction": "Section 7.1 NCL-to-linear-literal-planar-3-SAT",
        },
        "_occurrence": occurrence,
        "_masks": masks,
        "answer": [v + 1 for v in path],
    }


def make_instance(
    n: int,
    seed: int = 0,
    path_length: int = 160,
    and_rate: float = 0.92,
    min_hamming: int = 22,
    scan_steps: int = 22000,
    screen_restarts: int = 96,
    _construction_attempt: int = 0,
    **params,
) -> dict:
    """Construct a certified instance by sampling its legal path first.

    No search is used to obtain the answer.  Cheap attacks only screen which two
    already-visited legal states become the public endpoints.
    """

    del params
    if not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if not isinstance(path_length, int) or not 1 <= path_length <= 256:
        raise ValueError("path_length must lie in 1..256")
    if not 0.0 <= and_rate < 1.0:
        raise ValueError("and_rate must lie in [0,1)")
    if scan_steps < path_length:
        raise ValueError("scan_steps must be at least path_length")

    # Some legal-walk components yield endpoints that the cheap screens always
    # solve.  Move to another independently generated *certified* component; this
    # changes which planted walk is exposed, never how its witness is obtained.
    rng = random.Random(f"2506.14713|{seed}|{_construction_attempt}")
    ncl = _build_ncl(n, rng, and_rate)
    old_clauses = _formula_from_ncl(ncl)
    q = len(ncl["edges"])

    # Hide every construction-order statistic.  Reference orientation changes are
    # local Boolean variable complementations, which preserve the reconfiguration
    # graph; the random permutation removes external/internal edge numbering.
    perm = list(range(q))
    rng.shuffle(perm)
    complement = [rng.randrange(2) for _ in range(q)]

    def map_lit(lit: int) -> int:
        old = abs(lit) - 1
        positive = lit > 0
        if complement[old]:
            positive = not positive
        new = perm[old] + 1
        return new if positive else -new

    clauses = []
    for clause in old_clauses:
        c = [map_lit(lit) for lit in clause]
        rng.shuffle(c)
        clauses.append(c)
    rng.shuffle(clauses)
    occurrence, masks = _formula_index(clauses, q)

    old_start = sum(bit << i for i, bit in enumerate(ncl["bits"]))
    public_start = 0
    for old in range(q):
        bit = ((old_start >> old) & 1) ^ complement[old]
        public_start |= bit << perm[old]

    prototype = {
        "num_variables": q,
        "clauses": clauses,
        "_occurrence": occurrence,
        "_masks": masks,
        "max_flips": path_length,
    }
    if not _satisfies_masks(public_start, masks):
        raise AssertionError("constructed start assignment does not satisfy formula")

    bits = public_start
    states = [bits]
    flips: list[int] = []
    previous = -1
    external_public = {perm[e] for e in range(ncl["external_count"])}

    for step in range(scan_steps):
        legal = _legal_flips(prototype, bits)
        choices = [v for v in legal if v != previous] or legal
        heavy = [v for v in choices if v in external_public]
        if heavy and rng.random() < 0.85:
            choices = heavy
        if not choices:
            raise RuntimeError("legal-walk construction reached an isolated state")
        v = rng.choice(choices)
        bits ^= 1 << v
        flips.append(v)
        states.append(bits)
        previous = v

        if step + 1 < path_length:
            continue
        if screen_restarts and (step + 1 - path_length) % 10:
            continue
        begin = step + 1 - path_length
        start_bits = states[begin]
        goal_bits = bits
        if (start_bits ^ goal_bits).bit_count() < min_hamming:
            continue
        path = flips[begin : step + 1]
        inst = _public_instance(
            n, seed, clauses, start_bits, goal_bits, path, ncl["expanded_count"]
        )
        if not screen_restarts:
            return inst
        # These screens inspect public data only and never supply the certificate.
        if _attack_outlier_order(inst) is not None:
            continue
        if _attack_greedy(inst) is not None:
            continue
        if _attack_random_restart(inst, screen_restarts) is not None:
            continue
        return inst

    if screen_restarts and _construction_attempt < 15:
        return make_instance(
            n=n,
            seed=seed,
            path_length=path_length,
            and_rate=and_rate,
            min_hamming=min_hamming,
            scan_steps=scan_steps,
            screen_restarts=screen_restarts,
            _construction_attempt=_construction_attempt + 1,
        )
    raise RuntimeError(
        "could not find screened endpoints after 16 certified-walk constructions; "
        "raise scan_steps without changing the witness bound"
    )


def render(inst: dict) -> str:
    q = inst["num_variables"]
    B = inst["max_flips"]
    lines = [
        "Find a reconfiguration path between two satisfying assignments of a Boolean formula.",
        "",
        "Definitions and promise.",
        f"There are {q} Boolean variables x1 through x{q}.",
        "A positive integer k in a clause means xk; a negative integer -k means NOT xk.",
        "A clause is true when at least one of its listed literals is true, and the formula is the conjunction of all clauses.",
        "The formula is a 3-CNF: every clause has at most three literals.",
        "It is linear: each clause shares an identical signed literal with at most one other clause, and any such pair shares at most one literal.",
        "It is promised to be literal-planar: its bipartite literal-clause graph admits a planar embedding with a cycle through every signed literal, with opposite-literal edges on one side and all clause edges on the other.",
        "A move flips the truth value of exactly one variable. The assignment after every move must satisfy every clause.",
        "The leftmost bit of an assignment string is x1, the next is x2, and so on.",
        "",
        f"Start assignment: {inst['start']}",
        f"Goal assignment:  {inst['goal']}",
        "",
        "Clauses (one bracketed disjunction per line):",
    ]
    lines.extend("[" + ", ".join(map(str, clause)) + "]" for clause in inst["clauses"])
    lines.extend(
        [
            "",
            f"Give a sequence of exactly {B} moves. Each move is a variable number from 1 through {q}; repetitions are allowed and order matters.",
            "The final assignment after all moves must equal the displayed goal exactly.",
            "Give your final answer inside <answer></answer> tags, as a comma-separated list of variable numbers.",
            "Example: <answer>3, 17, 17, 42</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        match = re.search(r"<answer>(.*?)</answer>", text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        tokens = [token for token in re.split(r"[\s,]+", body) if token]
        if not tokens or any(not re.fullmatch(r"[+-]?\d+", token) for token in tokens):
            return None
        return [int(token) for token in tokens]
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list) or any(
        not isinstance(v, int) or isinstance(v, bool) for v in answer
    ):
        return False, "malformed: expected a list of integer variable numbers"
    B = inst["max_flips"]
    if not answer:
        return False, "empty: at least one move is required"
    if len(answer) < B:
        return False, f"too short: expected exactly {B} moves, got {len(answer)}"
    if len(answer) > B:
        return False, f"too long: expected exactly {B} moves, got {len(answer)}"
    q = inst["num_variables"]
    for step, v in enumerate(answer, 1):
        if v < 1 or v > q:
            return False, f"out of range at step {step}: variable {v} is not in 1..{q}"

    bits = _string_to_bits(inst["start"])
    if not _satisfies_masks(bits, inst["_masks"]):
        return False, "invalid instance: the displayed start assignment is unsatisfying"
    for step, one_based in enumerate(answer, 1):
        variable = one_based - 1
        new_bits = bits ^ (1 << variable)
        for ci in inst["_occurrence"][variable]:
            pos, neg = inst["_masks"][ci]
            if not ((new_bits & pos) or ((~new_bits) & neg)):
                return False, f"clause violation after step {step}: clause {ci + 1} is false"
        bits = new_bits
    if _bits_to_string(bits, q) != inst["goal"]:
        return False, "wrong endpoint: all moves are legal but the goal assignment is not reached"
    return True, "ok"


def _check_linear_3cnf(inst: dict) -> tuple[bool, str]:
    """Execute the paper's literal-based definition of linear 3-CNF exactly."""

    clauses = [set(clause) for clause in inst["clauses"]]
    for ci, clause in enumerate(inst["clauses"]):
        if not 1 <= len(clause) <= 3:
            return False, f"clause {ci + 1} has size {len(clause)}"
        if len(clauses[ci]) != len(clause):
            return False, f"clause {ci + 1} repeats a literal"
        if any(-lit in clauses[ci] for lit in clauses[ci]):
            return False, f"clause {ci + 1} is tautological"
    for i, left in enumerate(clauses):
        intersections = 0
        for j in range(i + 1, len(clauses)):
            common = left & clauses[j]
            if len(common) > 1:
                return False, f"clauses {i + 1} and {j + 1} share multiple literals"
            if common:
                intersections += 1
                if intersections > 1:
                    return False, f"clause {i + 1} intersects multiple clauses"
        # A previous clause may also intersect i, so count all earlier neighbors.
        intersections += sum(bool(left & clauses[j]) for j in range(i))
        if intersections > 1:
            return False, f"clause {i + 1} intersects multiple clauses"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample a length-B sequence satisfying all obvious endpoint parities.

    The induced distribution is a natural pair-insertion prior rather than the
    uniform distribution on the support: start with every forced odd occurrence,
    add random cancellation pairs, and uniformly shuffle.  It does not inspect the
    planted witness.
    """

    start = inst["start"]
    goal = inst["goal"]
    q = inst["num_variables"]
    B = inst["max_flips"]
    answer = [i + 1 for i, (a, b) in enumerate(zip(start, goal)) if a != b]
    extra = B - len(answer)
    if extra < 0 or extra % 2:
        raise ValueError("endpoint parity is incompatible with the certificate bound")
    for _ in range(extra // 2):
        v = rng.randrange(1, q + 1)
        answer.extend((v, v))
    rng.shuffle(answer)
    return answer


@lru_cache(maxsize=None)
def _parity_sequence_count(q: int, length: int, hamming: int) -> int:
    """Number of q-ary sequences with one fixed parity vector of given weight."""

    if hamming < 0 or hamming > q or hamming > length:
        return 0
    if (length - hamming) % 2:
        return 0
    if length == 0:
        return int(hamming == 0)
    return (
        hamming * _parity_sequence_count(q, length - 1, hamming - 1)
        + (q - hamming) * _parity_sequence_count(q, length - 1, hamming + 1)
    )


def search_space(inst: dict) -> int | None:
    hamming = sum(a != b for a, b in zip(inst["start"], inst["goal"]))
    return _parity_sequence_count(inst["num_variables"], inst["max_flips"], hamming)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 250_000:
        return None
    q = inst["num_variables"]
    B = inst["max_flips"]
    start = _string_to_bits(inst["start"])
    goal = _string_to_bits(inst["goal"])
    count = 0

    def visit(bits: int, depth: int) -> None:
        nonlocal count
        remaining = B - depth
        h = (bits ^ goal).bit_count()
        if h > remaining or (remaining - h) % 2:
            return
        if depth == B:
            if bits == goal:
                count += 1
            return
        for v in range(q):
            if _flip_legal(inst, bits, v):
                visit(bits ^ (1 << v), depth + 1)

    visit(start, 0)
    return count


def canonical_key(inst: dict) -> str:
    """A signed-incidence Weisfeiler-Lehman invariant.

    It is invariant under variable renaming, clause/literal ordering, and arbitrary
    local Boolean polarity changes.  Exact signed-CNF isomorphism is graph
    isomorphism; the README records that this inexpensive invariant can collide.
    """

    q = inst["num_variables"]
    start = inst["start"]
    goal = inst["goal"]
    adjacency: list[list[int]] = [[] for _ in range(q)]
    colors = [f"V:{int(start[v] != goal[v])}" for v in range(q)]

    for clause in inst["clauses"]:
        clause_node = len(colors)
        colors.append(f"C:{len(clause)}")
        adjacency.append([])
        for lit in clause:
            v = abs(lit) - 1
            positive = int(lit > 0) ^ int(start[v] == "1")
            occurrence_node = len(colors)
            colors.append(f"L:{positive}")
            adjacency.append([v, clause_node])
            adjacency[v].append(occurrence_node)
            adjacency[clause_node].append(occurrence_node)

    for _ in range(8):
        new_colors = []
        for node, color in enumerate(colors):
            signature = color + "|" + "|".join(sorted(colors[w] for w in adjacency[node]))
            new_colors.append(hashlib.sha256(signature.encode()).hexdigest())
        colors = new_colors
    summary = (
        f"q={q}|m={len(inst['clauses'])}|B={inst['max_flips']}|"
        + "|".join(sorted(colors))
    )
    return hashlib.sha256(summary.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the state-space haystack while keeping the witness length fixed."""

    out = dict(params)
    out.pop("_preset", None)
    out["n"] = int(out.get("n", 80)) + 20
    if out["n"] % 2:
        out["n"] += 1
    out["and_rate"] = min(0.97, float(out.get("and_rate", 0.92)) + 0.01)
    out["min_hamming"] = min(
        int(out.get("path_length", 160)), int(out.get("min_hamming", 22)) + 2
    )
    out["scan_steps"] = int(out.get("scan_steps", 22000) * 1.25)
    out["screen_restarts"] = min(256, int(out.get("screen_restarts", 96)) + 32)
    return out


def _relabel_for_test(inst: dict, perm: list[int], rng: random.Random) -> dict:
    """Compose variable relabelling, local complementation, and input reordering."""

    q = inst["num_variables"]
    complement = [rng.randrange(2) for _ in range(q)]

    def map_lit(lit: int) -> int:
        old = abs(lit) - 1
        positive = lit > 0
        if complement[old]:
            positive = not positive
        new = perm[old] + 1
        return new if positive else -new

    clauses = []
    for clause in inst["clauses"]:
        c = [map_lit(lit) for lit in clause]
        rng.shuffle(c)
        clauses.append(c)
    rng.shuffle(clauses)
    start = ["0"] * q
    goal = ["0"] * q
    for old in range(q):
        start[perm[old]] = str(int(inst["start"][old]) ^ complement[old])
        goal[perm[old]] = str(int(inst["goal"][old]) ^ complement[old])
    occurrence, masks = _formula_index(clauses, q)
    out = dict(inst)
    out["clauses"] = clauses
    out["start"] = "".join(start)
    out["goal"] = "".join(goal)
    out["answer"] = [perm[v - 1] + 1 for v in inst["answer"]]
    out["_occurrence"] = occurrence
    out["_masks"] = masks
    return out


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    planted_failures = []
    planted_checks = 0
    built: dict[tuple[str, int], dict] = {}
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            try:
                inst = make_instance(seed=seed, **params)
                built[(preset, seed)] = inst
                ok, reason = verify(inst, inst["answer"])
                planted_checks += 1
                if not ok:
                    planted_failures.append(f"{preset}/{seed}: {reason}")
                family_ok, family_reason = _check_linear_3cnf(inst)
                if not family_ok:
                    planted_failures.append(
                        f"{preset}/{seed}: promised family violation: {family_reason}"
                    )
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    planted_failures.append(f"{preset}/{seed}: answer is not JSON-native")
            except Exception as exc:  # pragma: no cover - diagnostic path
                planted_failures.append(f"{preset}/{seed}: {type(exc).__name__}: {exc}")
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "checks": planted_checks,
        "failures": planted_failures,
    }

    ship = built.get((SHIPPING_DIFFICULTY, 0)) or make_instance(
        seed=0, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )
    answer = ship["answer"]
    corruptions = {}
    tests = {
        "drop": answer[:-1],
        "duplicate": answer + [answer[0]],
        "empty": [],
        "out_of_range": [0] + answer[1:],
    }
    swapped = None
    for i in range(len(answer) - 1):
        candidate = answer[:]
        candidate[i], candidate[i + 1] = candidate[i + 1], candidate[i]
        ok, _ = verify(ship, candidate)
        if not ok:
            swapped = candidate
            break
    tests["swap"] = swapped if swapped is not None else list(reversed(answer))
    reasons = []
    for name, candidate in tests.items():
        ok, reason = verify(ship, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reason_classes": len(set(reasons)),
    }

    body = ", ".join(map(str, answer))
    model_style = "I simulated every move.\n```text\n<answer>" + body + "</answer>\n```"
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("unrelated prose") is None,
        "model_style_recovered": parsed == answer,
        "garbage_returns_none": parse_answer("unrelated prose") is None,
    }

    samples = 200_000
    hits = 0
    guess_rng = random.Random(0x250614713)
    t0 = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(ship, guess_rng)
        if verify(ship, candidate)[0]:
            hits += 1
    guess_seconds = time.perf_counter() - t0
    guess_fraction = hits / samples
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_fraction": guess_fraction,
        "sampling_seconds": round(guess_seconds, 6),
        "structure_aware": "fixed length, exact variable range, and forced endpoint parity",
        "candidate_space": search_space(ship),
    }

    demo = built.get(("demo", 0)) or make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    _, baseline_nodes, baseline_seconds = _attack_astar(ship, 100_000)
    report["G5_density_and_baseline"] = {
        "pass": guess_fraction < 1e-6 and baseline_nodes >= 100_000,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": guess_fraction,
        "demo_exact_valid_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_attack": "memoized A* with Hamming lower bound",
        "baseline_nodes": baseline_nodes,
        "baseline_wall_seconds": round(baseline_seconds, 6),
    }

    attack_seeds = list(range(300, 308))
    attacks = {
        "outlier_occurrence_order": {"successes": 0, "attempts": len(attack_seeds)},
        "greedy_clause_slack": {"successes": 0, "attempts": len(attack_seeds)},
        "target_biased_random_restart_96": {"successes": 0, "attempts": len(attack_seeds)},
        "memoized_astar_100k": {
            "successes": 0,
            "attempts": len(attack_seeds),
            "nodes": 0,
            "wall_seconds": 0.0,
        },
    }
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, fn in (
            ("outlier_occurrence_order", _attack_outlier_order),
            ("greedy_clause_slack", _attack_greedy),
            ("target_biased_random_restart_96", lambda x: _attack_random_restart(x, 96)),
        ):
            candidate = fn(inst)
            if candidate is not None and verify(inst, candidate)[0]:
                attacks[name]["successes"] += 1
        candidate, nodes, seconds = _attack_astar(inst, 100_000)
        attacks["memoized_astar_100k"]["nodes"] += nodes
        attacks["memoized_astar_100k"]["wall_seconds"] += seconds
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["memoized_astar_100k"]["successes"] += 1
    attacks["memoized_astar_100k"]["wall_seconds"] = round(
        attacks["memoized_astar_100k"]["wall_seconds"], 6
    )
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attacks.values()),
        "attacks": attacks,
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["scan_steps"] = int(doubled_params["scan_steps"] * 1.5)
    try:
        doubled = make_instance(seed=991, **doubled_params)
        doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    except Exception as exc:  # pragma: no cover - diagnostic path
        doubled = None
        doubled_ok = False
        doubled_reason = f"{type(exc).__name__}: {exc}"
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled is not None
        and doubled["num_variables"] > ship["num_variables"]
        and len(doubled["answer"]) == len(ship["answer"]),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"] if doubled else None,
        "shipping_variables": ship["num_variables"],
        "doubled_variables": doubled["num_variables"] if doubled else None,
        "answer_elements_both": len(ship["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_ok = 0
    transform_ok = 0
    keys = []
    for seed in range(500, 520):
        inst = make_instance(seed=seed, **DIFFICULTY["demo"])
        key = canonical_key(inst)
        keys.append(key)
        rng = random.Random(seed ^ 0xC0FFEE)
        perm = list(range(inst["num_variables"]))
        rng.shuffle(perm)
        changed = _relabel_for_test(inst, perm, rng)
        if canonical_key(changed) == key:
            invariant_ok += 1
        if verify(changed, changed["answer"])[0]:
            transform_ok += 1
    report["G8_canonical_key"] = {
        "pass": invariant_ok == 20 and transform_ok == 20 and len(set(keys)) == 20,
        "invariance_passed": invariant_ok,
        "invariance_attempts": 20,
        "carried_witness_passed": transform_ok,
        "carried_witness_attempts": 20,
        "distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
        "transformations": [
            "variable permutation",
            "clause order",
            "literal order",
            "independent variable polarity changes",
            "their composition",
        ],
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(ship["answer"])
    arms = json.loads(json.dumps(G9_ARMS))
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
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and ship["max_flips"] <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_run"
            if not arms["hinted"]["attempts"]
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": ship["max_flips"],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
