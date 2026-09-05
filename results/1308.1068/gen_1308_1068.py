"""Verified generator for deletion list-homomorphisms to a skew sum P4.

The family is a native special case of DL-Hom(H) from Chitnis, Egri, and
Marx, arXiv:1308.1068.  Certificates are known by composition: the only
forbidden list-pair edges form vertex-disjoint odd paths, and the planted
deletion set takes the alternating internal side of every path.
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
from collections import deque


# Make the repository helpers importable when harden.py runs in this folder.
# This module needs no helper, so the standard-library fallback is complete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "loopless input graph G",
        "skew-decomposable target graph P4",
        "singleton vertex lists",
        "vertex deletion set",
    ],
    "verification_operations": [
        "exact singleton-list lookup",
        "exact target-edge membership",
        "exact vertex-cover check on the obstruction edges",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The skew-sum target makes three list-pair edge blocks automatically "
        "safe, so only the nonedge-colored block must be decomposed into odd "
        "paths; without that filter a solver faces the full regular graph."
    ),
    "hardness_basis": (
        "Track B: Theorem 1.1 and Lemma 3.22 give an FPT route; on the "
        "rendered block representation, list-pair filtering followed by the "
        "domain-standard Hopcroft-Karp/Konig algorithm is O(E*sqrt(V)) and "
        "used 1,645 recorded operations (about 0.0006 seconds) at the shipping "
        "measurement seed, versus at most 236 visits for the odd-path route; "
        "fully expanding the succinct reservoir instead costs about 12.6 "
        "million operations."
    ),
    "max_answer_tokens": 169,
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
        "A JSON array of exactly k distinct vertex IDs, strictly increasing, "
        "chosen from the endpoints of the explicitly displayed E12 obstruction "
        "block.  IDs are base-10 integers in [0,N-1]."
    ),
    "bounds": {
        "answer_vertices": "exactly k",
        "strictly_increasing": True,
        "repetition_allowed": False,
        "ground_set": "endpoints of E12",
        "max_atomic_elements": 256,
    },
}

DIFFICULTY: dict = {
    "demo": {
        "n": 64, "k": 6, "safe_degree": 4, "max_path_half": 3,
    },
    "easy": {
        "n": 20_000, "k": 36, "safe_degree": 8, "max_path_half": 6,
    },
    "medium": {
        "n": 100_000, "k": 72, "safe_degree": 10, "max_path_half": 8,
    },
    "hard": {
        "n": 350_000, "k": 96, "safe_degree": 12, "max_path_half": 9,
    },
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Edges whose endpoint lists name a nonedge of the skew-sum target form the "
    "only obstruction subgraph."
)
PLACEBO_HINT = (
    "The endpoint conventions and sorted output format reward especially careful "
    "bookkeeping."
)

# Filled from script-owned runs after hardening.  Zero-attempt entries are honest
# placeholders during local gate development, not oracle evidence.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Definition and easy regimes.  Section 2, Definition 2 and the boxed DL-Hom(H)
definition fix the native input: loopless graphs G,H, a list L(v) subset of
V(H), and a budget k; a witness deletes at most k vertices so the remainder has
a list-respecting homomorphism.  The Introduction notes that the singleton
target is Vertex Cover and that a single-edge target is Odd Cycle Transversal.
Theorem 1.1 says DL-Hom(H) is FPT in k and |H| for skew-decomposable H, so a
Track A claim based only on NP-hardness would be false for the small-k regime.

Construction.  Section 3.4 defines H=H1 oslash H2 and calls an input edge bad
when its endpoint lists lie in B1 and T2.  Take H1 and H2 to be single edges;
their special sum is the path with edges 0-1, 0-3, 3-2.  Every input list here
is a singleton.  Therefore 0-1, 0-3, and 2-3 input edges already map to H,
whereas each 1-2 edge must lose an endpoint.  The 1-2 block is composed from
vertex-disjoint paths on 2d+1 vertices.  Deleting positions 1,3,...,2d-1 is a
cover of size d and is the unique size-d cover of that path.  The generator
samples these paths and their labels first, records the alternating vertices,
then adds only safe edges.  It never solves the emitted instance.

Track choice and mechanical route.  A target-aware scan reduces the instance
to bipartite Vertex Cover; Hopcroft-Karp plus Konig's construction returns a
minimum cover in polynomial time.  The honest reference measurement first
classifies the four rendered edge blocks by their singleton-list pairs and then
runs matching only on the obstruction block; the report separately records the
larger cost of fully expanding the succinct reservoir.  The compact route uses
the paper's skew-sum decomposition and the fact that the obstruction components
are odd paths.  Thus this is Track B no-tool compression, not a distributional
or complexity-theoretic hardness claim.

Attack hardening.  Every vertex has exactly safe_degree total incident edges,
so total degree has no planted outlier.  Within the obstruction block both
planted and unplanted internal path vertices have degree two.  The measured
outlier ranking, dynamic maximum-degree greedy cover, 256 structure-aware
random restarts, and the in-context single-target-side ansatz all fail on eight
shipping seeds.  Safe attachment ports replace omitted reservoir edges, which
keeps plant and decoy total-degree distributions identical.
""".strip()


_H_EDGES = [[0, 1], [0, 3], [2, 3]]


def _reachable_parts(total: int, maximum: int) -> list[bool]:
    reachable = [False] * (total + 1)
    reachable[0] = True
    for value in range(1, total + 1):
        reachable[value] = any(
            value >= d and reachable[value - d]
            for d in range(3, maximum + 1)
        )
    return reachable


def _sample_partition(total: int, maximum: int,
                      rng: random.Random) -> list[int]:
    """A random ordered composition of total using parts 3..maximum."""
    reachable = _reachable_parts(total, maximum)
    if not reachable[total]:
        raise ValueError("k/2 is not composable from the permitted path sizes")
    parts = []
    remaining = total
    while remaining:
        choices = [d for d in range(3, min(maximum, remaining) + 1)
                   if reachable[remaining - d]]
        d = rng.choice(choices)
        parts.append(d)
        remaining -= d
    rng.shuffle(parts)
    return parts


def _validate_params(n: int, k: int, safe_degree: int,
                     max_path_half: int) -> None:
    vals = (n, k, safe_degree, max_path_half)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in vals):
        raise ValueError("all parameters must be integers")
    if n < 16:
        raise ValueError("n must be at least 16")
    if k < 6 or k % 2:
        raise ValueError("k must be an even integer at least 6")
    if max_path_half < 3 or max_path_half > k // 2:
        raise ValueError("max_path_half must lie between 3 and k/2")
    if safe_degree <= max_path_half or safe_degree >= n:
        raise ValueError("need max_path_half < safe_degree < n")
    if not _reachable_parts(k // 2, max_path_half)[k // 2]:
        raise ValueError("k/2 has no permitted path-size composition")


def _vertex_color(inst: dict, vertex: int) -> int | None:
    n = inst["padding_per_side"]
    active = inst["active_per_color"]
    if 0 <= vertex < n:
        return 0
    if n <= vertex < 2 * n:
        return 3
    if 2 * n <= vertex < 2 * n + active:
        return 1
    if 2 * n + active <= vertex < 2 * n + 2 * active:
        return 2
    return None


def _active_vertices(inst: dict) -> list[int]:
    start = 2 * inst["padding_per_side"]
    return list(range(start, inst["n_vertices"]))


def _bad_degrees(inst: dict) -> dict[int, int]:
    degree = {v: 0 for v in _active_vertices(inst)}
    for u, v in inst["constraint_edges_E12"]:
        degree[u] += 1
        degree[v] += 1
    return degree


def make_instance(n: int, seed: int = 0, *, k: int,
                  safe_degree: int, max_path_half: int) -> dict:
    """Inverse-generate a certified DL-Hom(P4) instance.

    ``n`` is the number of safe reservoir vertices on each of colors 0 and 3.
    The answer length k stays fixed when n grows; the mechanical edge scan grows.
    """
    _validate_params(n, k, safe_degree, max_path_half)
    rng = random.Random(seed)
    pair_sizes = _sample_partition(k // 2, max_path_half, rng)

    # Logical path vertices are assigned random numeric IDs independently inside
    # each singleton-list color class.  Each size d occurs in both orientations,
    # so the two active color classes have exactly the same cardinality and stub
    # count.
    logical_by_color: dict[int, list[tuple[int, int]]] = {1: [], 2: []}
    path_logical: list[list[tuple[int, int]]] = []
    path_half_sizes: list[int] = []
    path_id = 0
    for d in pair_sizes:
        for orientation in (0, 1):
            path = []
            for pos in range(2 * d + 1):
                color = (1 if pos % 2 == 0 else 2)
                if orientation:
                    color = 3 - color
                key = (path_id, pos)
                logical_by_color[color].append(key)
                path.append(key)
            path_logical.append(path)
            path_half_sizes.append(d)
            path_id += 1

    if len(logical_by_color[1]) != len(logical_by_color[2]):
        raise AssertionError("paired orientations must balance active colors")
    active_per_color = len(logical_by_color[1])
    mapping: dict[tuple[int, int], int] = {}
    starts = {1: 2 * n, 2: 2 * n + active_per_color}
    for color in (1, 2):
        keys = list(logical_by_color[color])
        rng.shuffle(keys)
        for offset, key in enumerate(keys):
            mapping[key] = starts[color] + offset

    bad_edges = []
    answer = []
    bad_degree: dict[int, int] = {}
    for path in path_logical:
        ids = [mapping[key] for key in path]
        for a, b in zip(ids, ids[1:]):
            bad_edges.append([min(a, b), max(a, b)])
            bad_degree[a] = bad_degree.get(a, 0) + 1
            bad_degree[b] = bad_degree.get(b, 0) + 1
        answer.extend(ids[1::2])
    rng.shuffle(bad_edges)
    answer.sort()

    # Give every active vertex enough safe attachments to reach safe_degree.
    stubs: dict[int, list[int]] = {1: [], 2: []}
    for color in (1, 2):
        for key in logical_by_color[color]:
            vertex = mapping[key]
            stubs[color].extend([vertex] * (safe_degree - bad_degree[vertex]))
        rng.shuffle(stubs[color])
    if len(stubs[1]) != len(stubs[2]):
        raise AssertionError("paired paths must balance safe attachment stubs")
    used_count = len(stubs[1])
    if used_count >= n:
        raise ValueError(
            "n is too small for distinct safe attachment ports; increase n"
        )

    shifts = rng.sample(range(n), safe_degree)
    reserved_shift = shifts[0]
    shifts.sort()
    omitted_starts = rng.sample(range(n), used_count)
    ports0 = list(omitted_starts)
    ports3 = [(i + reserved_shift) % n for i in omitted_starts]
    rng.shuffle(ports0)
    rng.shuffle(ports3)
    attachments01 = [[port, vertex]
                     for port, vertex in zip(ports0, stubs[1])]
    attachments23 = [[vertex, n + port]
                     for port, vertex in zip(ports3, stubs[2])]
    rng.shuffle(attachments01)
    rng.shuffle(attachments23)

    n_vertices = 2 * n + 2 * active_per_color
    inst = {
        "paper": "arXiv:1308.1068",
        "target_vertices": [0, 1, 2, 3],
        "target_edges": [list(e) for e in _H_EDGES],
        "padding_per_side": n,
        "active_per_color": active_per_color,
        "n_vertices": n_vertices,
        "k": k,
        "safe_degree": safe_degree,
        "max_path_half": max_path_half,
        "path_half_sizes": list(path_half_sizes),
        "pair_sizes": list(pair_sizes),
        "constraint_edges_E12": bad_edges,
        "safe_attachments_E01": attachments01,
        "safe_attachments_E23": attachments23,
        "reservoir_shifts": shifts,
        "reserved_shift": reserved_shift,
        "answer": answer,
    }
    return inst


def _adjacency_rows(inst: dict) -> list[tuple[int, list[int]]]:
    rows = {v: [] for v in _active_vertices(inst)}
    for u, v in inst["constraint_edges_E12"]:
        rows[u].append(v)
        rows[v].append(u)
    return [(v, sorted(rows[v])) for v in sorted(rows)]


def _pairs_text(pairs: list[list[int]], per_line: int = 4) -> str:
    chunks = []
    for i in range(0, len(pairs), per_line):
        chunks.append("  " + " ".join(
            f"({a},{b})" for a, b in pairs[i:i + per_line]
        ))
    return "\n".join(chunks) if chunks else "  (none)"


def render(inst: dict) -> str:
    n = inst["padding_per_side"]
    active = inst["active_per_color"]
    total = inst["n_vertices"]
    rows = _adjacency_rows(inst)
    row_text = "\n".join(
        f"  {v}: " + (" ".join(map(str, nbrs)) if nbrs else "-")
        for v, nbrs in rows
    )
    a01 = _pairs_text(inst["safe_attachments_E01"])
    a23 = _pairs_text(inst["safe_attachments_E23"])
    shifts = ", ".join(map(str, inst["reservoir_shifts"]))
    start1 = 2 * n
    stop1 = start1 + active - 1
    start2 = stop1 + 1
    stop2 = total - 1
    text = f"""DELETION LIST-HOMOMORPHISM TO A FOUR-VERTEX TARGET

All graphs below are finite, undirected, loopless, and have no parallel edges.
The target graph H has vertices 0,1,2,3 and exactly the edges
  {{0,1}}, {{0,3}}, {{2,3}}.

The input graph G has vertex IDs 0 through {total - 1}.  Every vertex has a
singleton list, so its image in H is forced.  The forced image c(v) is
  c(v)=0 for 0 <= v < {n};
  c(v)=3 for {n} <= v < {2 * n};
  c(v)=1 for {start1} <= v <= {stop1};
  c(v)=2 for {start2} <= v <= {stop2}.

The edge set of G is the union of the four blocks below.  Modular arithmetic in
the reservoir block uses residues 0,...,{n - 1}.  These formulas are the exact
graph definition; do not add edges not specified here.

E12 (listed as symmetric adjacency rows; '-' means no neighbor):
{row_text}

E01 (explicit edges):
{a01}

E23 (explicit edges):
{a23}

E03 reservoir block:
  shifts S = [{shifts}]
  reserved shift q = {inst['reserved_shift']}
  For every 0 <= i < {n} and every s in S, include
    {{i, {n} + ((i+s) mod {n})}},
  except omit the q-edge starting at i whenever i is the color-0 endpoint of
  an edge in E01.  No other edges exist.

A map phi from a graph to H is a homomorphism when every input edge {{u,v}}
maps to an edge {{phi(u),phi(v)}} of H.  It respects the lists when
phi(v)=c(v).  Delete exactly k={inst['k']} vertices so that the forced map
phi(v)=c(v) is a list-respecting homomorphism from the remaining induced graph
G-W to H.  Deleting exactly k loses no witness: any solution using fewer than k
vertices can be padded with arbitrary additional deletions.  Vertex IDs in W
must be distinct and written in strictly increasing order.

Give your final answer inside <answer></answer> tags as one JSON array of exactly
{inst['k']} base-10 vertex IDs.
Example format: <answer>[1,2,3]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body,
                  flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer contains no deleted vertices"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every vertex ID must be an integer"
    total = inst["n_vertices"]
    if any(x < 0 or x >= total for x in answer):
        return False, "vertex ID outside the inclusive range 0 through N-1"
    if len(set(answer)) != len(answer):
        return False, "deleted vertex IDs must be distinct"
    if len(answer) != inst["k"]:
        return False, f"answer must contain exactly {inst['k']} vertex IDs"
    if answer != sorted(answer):
        return False, "vertex IDs must be in strictly increasing order"

    h_edges = {tuple(sorted(e)) for e in inst["target_edges"]}
    for pair in ((0, 1), (0, 3), (2, 3)):
        if pair not in h_edges:
            return False, "a symbolic safe edge block does not map to H"

    deleted = set(answer)
    for u, v in inst["constraint_edges_E12"]:
        cu, cv = _vertex_color(inst, u), _vertex_color(inst, v)
        if cu is None or cv is None:
            return False, "instance contains an invalid E12 endpoint"
        if tuple(sorted((cu, cv))) in h_edges:
            continue
        if u not in deleted and v not in deleted:
            return False, f"uncovered obstruction edge ({u},{v})"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    # A statement-aware solver immediately discards reservoir vertices: they are
    # incident only with list-pair blocks that already map to H.  Sample uniformly
    # from the remaining exact-k subset language.
    return sorted(rng.sample(_active_vertices(inst), inst["k"]))


def search_space(inst: dict) -> int | None:
    return math.comb(len(_active_vertices(inst)), inst["k"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 50_000:
        return None
    count = 0
    for candidate in itertools.combinations(_active_vertices(inst), inst["k"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _normalised_shift_signature(inst: dict) -> tuple[int, ...]:
    n = inst["padding_per_side"]
    q = inst["reserved_shift"]
    rel = tuple(sorted((s - q) % n for s in inst["reservoir_shifts"]))
    reflected = tuple(sorted((-x) % n for x in rel))
    return min(rel, reflected)


def canonical_key(inst: dict) -> str:
    # The compact representation fixes the four list colors.  Within it, active
    # vertex renumbering, edge-record order, reservoir rotations, and reflection
    # do not change this signature.  It is intentionally a strong invariant, not
    # a claim to solve arbitrary colored cubic-graph isomorphism.
    payload = {
        "target": sorted(tuple(sorted(e)) for e in inst["target_edges"]),
        "n": inst["padding_per_side"],
        "k": inst["k"],
        "degree": inst["safe_degree"],
        "path_halves": sorted(inst["path_half_sizes"]),
        "shift_signature": _normalised_shift_signature(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    out = dict(params)
    out.pop("_preset", None)
    # Both changes enlarge only safe, symbolically ignorable graph structure;
    # answer length and the compact odd-path route remain fixed.
    out["n"] = int(out["n"]) * 2
    out["safe_degree"] = int(out["safe_degree"]) + 2
    return out


def _hopcroft_karp(left: list[int], adjacency: dict[int, list[int]],
                    op_counter: list[int]) -> tuple[dict[int, int | None],
                                                    dict[int, int | None]]:
    right = sorted({v for nbrs in adjacency.values() for v in nbrs})
    pair_u: dict[int, int | None] = {u: None for u in left}
    pair_v: dict[int, int | None] = {v: None for v in right}
    dist: dict[int, int] = {}
    inf = 10**18

    def bfs() -> bool:
        queue = deque()
        found = False
        for u in left:
            op_counter[0] += 1
            if pair_u[u] is None:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = inf
        while queue:
            u = queue.popleft()
            for v in adjacency.get(u, []):
                op_counter[0] += 1
                mate = pair_v[v]
                if mate is None:
                    found = True
                elif dist[mate] == inf:
                    dist[mate] = dist[u] + 1
                    queue.append(mate)
        return found

    def dfs(u: int) -> bool:
        for v in adjacency.get(u, []):
            op_counter[0] += 1
            mate = pair_v[v]
            if mate is None or (dist.get(mate, inf) == dist[u] + 1
                                and dfs(mate)):
                pair_u[u] = v
                pair_v[v] = u
                return True
        dist[u] = inf
        return False

    while bfs():
        for u in left:
            if pair_u[u] is None:
                dfs(u)
    return pair_u, pair_v


def _reference_algorithm(inst: dict, expand_symbolic: bool = False) -> dict:
    """List-pair filtering, then Hopcroft-Karp and Konig's cover.

    ``expand_symbolic`` is a separately reported diagnostic: it materializes
    the safe reservoir as a generic explicit-graph implementation would.  The
    Track B reference cost leaves it false because the solver is actually shown
    a block representation and can classify a whole block from its list pair.
    """
    start = time.perf_counter()
    operations = [0]
    h_edges = {tuple(sorted(e)) for e in inst["target_edges"]}
    left_start = 2 * inst["padding_per_side"]
    left = list(range(left_start, left_start + inst["active_per_color"]))
    adjacency = {u: [] for u in left}

    # The renderer exposes four edge blocks whose endpoint lists are fixed.
    # Classifying their four list pairs is the honest cost on that encoding.
    for pair in ((1, 2), (0, 1), (2, 3), (0, 3)):
        operations[0] += 1
        _ = tuple(sorted(pair)) in h_edges

    for u, v in inst["constraint_edges_E12"]:
        operations[0] += 3
        cu, cv = _vertex_color(inst, u), _vertex_color(inst, v)
        if tuple(sorted((cu, cv))) not in h_edges:
            if cu == 1:
                adjacency[u].append(v)
            else:
                adjacency[v].append(u)
    n = inst["padding_per_side"]
    omitted = {u for u, _ in inst["safe_attachments_E01"]}
    q = inst["reserved_shift"]
    checksum = 0
    if expand_symbolic:
        # Diagnostic only: replay all known-safe records as if G had first been
        # converted from the rendered block form to an explicit edge list.
        for u, v in inst["safe_attachments_E01"]:
            operations[0] += 3
            checksum ^= (u + v) & 1
        for u, v in inst["safe_attachments_E23"]:
            operations[0] += 3
            checksum ^= (u + v) & 1
        for i in range(n):
            for shift in inst["reservoir_shifts"]:
                operations[0] += 3
                if shift == q and i in omitted:
                    continue
                checksum ^= (i + shift) % n

    for nbrs in adjacency.values():
        nbrs.sort()
    pair_u, pair_v = _hopcroft_karp(left, adjacency, operations)

    # Konig: alternating reachability from unmatched left vertices.
    seen_left = {u for u in left if pair_u[u] is None}
    seen_right: set[int] = set()
    queue = deque(seen_left)
    while queue:
        u = queue.popleft()
        for v in adjacency[u]:
            operations[0] += 1
            if pair_u[u] == v or v in seen_right:
                continue
            seen_right.add(v)
            mate = pair_v[v]
            if mate is not None and mate not in seen_left:
                seen_left.add(mate)
                queue.append(mate)
    cover = sorted((set(left) - seen_left) | seen_right)
    elapsed = time.perf_counter() - start
    ok, why = verify(inst, cover)
    return {
        "ok": ok,
        "reason": why,
        "answer": cover,
        "wall_clock_sec": elapsed,
        "operations": operations[0],
        "obstruction_edges_scanned": len(inst["constraint_edges_E12"]),
        "expanded_edges_scanned": (
            n * len(inst["reservoir_shifts"]) - len(omitted)
            + len(inst["safe_attachments_E01"])
            + len(inst["safe_attachments_E23"])
            + len(inst["constraint_edges_E12"])
            if expand_symbolic else 0
        ),
        "matching_size": sum(v is not None for v in pair_u.values()),
        "checksum": checksum,
    }


def _attack_outlier_degree(inst: dict) -> list[int]:
    degree = _bad_degrees(inst)
    # Total degrees are all identical.  Break that tie using the most obvious
    # remaining per-vertex statistic: degree in the displayed obstruction block.
    ranked = sorted(_active_vertices(inst),
                    key=lambda v: (-inst["safe_degree"], -degree[v], v))
    return sorted(ranked[:inst["k"]])


def _attack_greedy(inst: dict) -> tuple[list[int], int]:
    edges = [tuple(e) for e in inst["constraint_edges_E12"]]
    uncovered = set(range(len(edges)))
    chosen: set[int] = set()
    operations = 0
    for _ in range(inst["k"]):
        counts: dict[int, int] = {}
        for idx in uncovered:
            u, v = edges[idx]
            counts[u] = counts.get(u, 0) + 1
            counts[v] = counts.get(v, 0) + 1
            operations += 2
        if not counts:
            break
        pick = min(counts, key=lambda v: (-counts[v], v))
        chosen.add(pick)
        uncovered = {idx for idx in uncovered if pick not in edges[idx]}
    if len(chosen) < inst["k"]:
        chosen.update(v for v in _active_vertices(inst) if v not in chosen
                      and len(chosen) < inst["k"])
    return sorted(chosen), operations


def _attack_single_target_side(inst: dict) -> list[int]:
    degree = _bad_degrees(inst)
    n = inst["padding_per_side"]
    a = inst["active_per_color"]
    side1 = list(range(2 * n, 2 * n + a))
    ranked = sorted(side1, key=lambda v: (-degree[v], v))
    return sorted(ranked[:inst["k"]])


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x13081068)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _intended_route_operations(inst: dict) -> int:
    # After the list-pair invariant is recognized, visit each obstruction vertex
    # once and start one alternating traversal per odd path.
    return len(_active_vertices(inst)) + len(inst["path_half_sizes"])


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    wire = json.dumps(answer, separators=(",", ":"))
    return len(wire), math.ceil(len(wire) / 4), len(answer)


def _permuted_active(inst: dict, rng: random.Random) -> tuple[dict, list[int]]:
    out = dict(inst)
    n = inst["padding_per_side"]
    a = inst["active_per_color"]
    mapping = {}
    for start in (2 * n, 2 * n + a):
        old = list(range(start, start + a))
        new = list(old)
        rng.shuffle(new)
        mapping.update(zip(old, new))

    def mv(v: int) -> int:
        return mapping.get(v, v)

    out["constraint_edges_E12"] = [
        [min(mv(u), mv(v)), max(mv(u), mv(v))]
        for u, v in reversed(inst["constraint_edges_E12"])
    ]
    out["safe_attachments_E01"] = [
        [u, mv(v)] for u, v in reversed(inst["safe_attachments_E01"])
    ]
    out["safe_attachments_E23"] = [
        [mv(u), v] for u, v in reversed(inst["safe_attachments_E23"])
    ]
    carried = sorted(mv(v) for v in inst["answer"])
    out["answer"] = carried
    return out, carried


def _rotated_reservoir(inst: dict, r0: int,
                       r3: int) -> tuple[dict, list[int]]:
    out = dict(inst)
    n = inst["padding_per_side"]

    def m0(v: int) -> int:
        return (v + r0) % n

    def m3(v: int) -> int:
        return n + ((v - n + r3) % n)

    out["safe_attachments_E01"] = [
        [m0(u), v] for u, v in reversed(inst["safe_attachments_E01"])
    ]
    out["safe_attachments_E23"] = [
        [u, m3(v)] for u, v in reversed(inst["safe_attachments_E23"])
    ]
    delta = r3 - r0
    out["reservoir_shifts"] = sorted(
        (s + delta) % n for s in inst["reservoir_shifts"]
    )
    out["reserved_shift"] = (inst["reserved_shift"] + delta) % n
    out["constraint_edges_E12"] = list(
        reversed(inst["constraint_edges_E12"])
    )
    out["answer"] = list(inst["answer"])
    return out, list(out["answer"])


def _reflected_reservoir(inst: dict, r0: int,
                         r3: int) -> tuple[dict, list[int]]:
    out = dict(inst)
    n = inst["padding_per_side"]

    def m0(v: int) -> int:
        return (-v + r0) % n

    def m3(v: int) -> int:
        return n + ((-(v - n) + r3) % n)

    out["safe_attachments_E01"] = [
        [m0(u), v] for u, v in reversed(inst["safe_attachments_E01"])
    ]
    out["safe_attachments_E23"] = [
        [u, m3(v)] for u, v in reversed(inst["safe_attachments_E23"])
    ]
    delta = r3 - r0
    out["reservoir_shifts"] = sorted(
        (delta - s) % n for s in inst["reservoir_shifts"]
    )
    out["reserved_shift"] = (delta - inst["reserved_shift"]) % n
    out["constraint_edges_E12"] = list(
        reversed(inst["constraint_edges_E12"])
    )
    out["answer"] = list(inst["answer"])
    return out, list(out["answer"])


def selftest() -> dict:
    report: dict = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    original = list(inst["answer"])
    duplicate = list(original)
    duplicate[-1] = duplicate[-2]
    out_range = list(original)
    out_range[-1] = inst["n_vertices"]
    swapped = list(original)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions = {
        "drop_one": verify(inst, original[:-1]),
        "swap_two": verify(inst, swapped),
        "duplicate_one": verify(inst, duplicate),
        "empty": verify(inst, []),
        "out_of_range": verify(inst, out_range),
    }
    reasons = [why for _, why in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"rejected": not result[0], "reason": result[1]}
                  for name, result in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(original, separators=(",", ":"))
    parsed = parse_answer(
        "The skew-sum leaves one obstruction block.\n```text\n<answer>\n"
        + wire + "\n</answer>\n```\nThe IDs are sorted."
    )
    report["G3_round_trip"] = {
        "pass": parsed == original,
        "surrounding_prose_and_markdown_fence": True,
        "json_round_trip": parsed == original,
    }

    guess_rng = random.Random(0x13081068)
    guess_total = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - t0
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / guess_total < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": hits / guess_total,
        "candidate_space": space,
        "prior": (
            "uniform over exact-k subsets of E12 endpoints; safe-only reservoir "
            "vertices are excluded as a statement-aware solver would exclude them"
        ),
        "sampling_wall_seconds": guess_seconds,
    }

    baseline = _reference_algorithm(inst)
    expanded_baseline = _reference_algorithm(inst, expand_symbolic=True)
    attack_t0 = time.perf_counter()
    greedy_answer, greedy_ops = _attack_greedy(inst)
    greedy_ok = verify(inst, greedy_answer)[0]
    attack_seconds = time.perf_counter() - attack_t0
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": baseline["ok"] and hits / guess_total < 1e-6
                and demo_count == 1 and not greedy_ok,
        "shipping_observed_valid_fraction": hits / guess_total,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_construction_solution_count": 1,
        "strongest_failing_attack_wall_seconds": attack_seconds,
        "strongest_failing_attack_operations": greedy_ops,
        "strongest_failing_attack_name": "dynamic maximum-uncovered-degree greedy",
        "strongest_failing_attack_success_count": int(greedy_ok),
        "reference_wall_seconds": baseline["wall_clock_sec"],
        "reference_operation_count": baseline["operations"],
        "reference_obstruction_edges_scanned": (
            baseline["obstruction_edges_scanned"]
        ),
        "full_expansion_wall_seconds": expanded_baseline["wall_clock_sec"],
        "full_expansion_operation_count": expanded_baseline["operations"],
        "full_expansion_edges_scanned": (
            expanded_baseline["expanded_edges_scanned"]
        ),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo_inst),
        "shipping_candidate_space": space,
        "enumerate_all_shipping": None,
    }

    attack_successes = {
        "outlier_total_and_obstruction_degree": 0,
        "greedy_max_uncovered_degree": 0,
        "random_restart_256_structure_aware": 0,
        "in_context_single_target_side": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        if verify(trial, _attack_outlier_degree(trial))[0]:
            attack_successes["outlier_total_and_obstruction_degree"] += 1
        greedy, _ = _attack_greedy(trial)
        if verify(trial, greedy)[0]:
            attack_successes["greedy_max_uncovered_degree"] += 1
        if _attack_random_restart(trial, seed):
            attack_successes["random_restart_256_structure_aware"] += 1
        if verify(trial, _attack_single_target_side(trial))[0]:
            attack_successes["in_context_single_target_side"] += 1
        reference_runs.append(_reference_algorithm(trial))
    ref_ok = sum(int(run["ok"]) for run in reference_runs)
    all_failed = all(count == 0 for count in attack_successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_ok == 8,
        "attacks": {
            name: {"successes": count, "attempts": 8}
            for name, count in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "block list-pair filter, Hopcroft-Karp, and Konig cover",
            "complexity": "O(E*sqrt(V)) time and O(E+V) space",
            "wall_clock_sec": baseline["wall_clock_sec"],
            "mean_wall_clock_sec": (
                sum(r["wall_clock_sec"] for r in reference_runs) / 8
            ),
            "measured_runs": 8,
            "operations": (
                sum(r["operations"] for r in reference_runs) // 8
            ),
            "total_operations": sum(r["operations"] for r in reference_runs),
            "mean_operations": sum(r["operations"] for r in reference_runs) // 8,
            "mean_obstruction_edges_scanned": (
                sum(r["obstruction_edges_scanned"] for r in reference_runs) // 8
            ),
            "solves": f"{ref_ok}/8, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["safe_degree"] += 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_params["n"] > ship_params["n"]
                and doubled_params["safe_degree"] > ship_params["safe_degree"]
                and len(doubled["answer"]) == len(inst["answer"]),
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "base_safe_degree": ship_params["safe_degree"],
        "doubled_safe_degree": doubled_params["safe_degree"],
        "answer_elements_unchanged": len(doubled["answer"]),
        "doubled_verify": doubled_why,
        "mechanical_edge_haystack_ratio": round(
            (doubled_params["n"] * doubled_params["safe_degree"])
            / (ship_params["n"] * ship_params["safe_degree"]), 3
        ),
    }

    invariance_checks = 0
    witness_checks = 0
    key_params = {
        "n": 512, "k": 24, "safe_degree": 7, "max_path_half": 6,
    }
    for seed in range(20):
        base = make_instance(seed=seed, **key_params)
        permuted, carried1 = _permuted_active(base, random.Random(seed + 9000))
        invariance_checks += int(canonical_key(permuted) == canonical_key(base))
        witness_checks += int(verify(permuted, carried1)[0])
        rotated, carried2 = _rotated_reservoir(
            base, (17 * seed + 3) % key_params["n"],
            (29 * seed + 5) % key_params["n"]
        )
        invariance_checks += int(canonical_key(rotated) == canonical_key(base))
        witness_checks += int(verify(rotated, carried2)[0])
        reflected, carried3 = _reflected_reservoir(
            base, (37 * seed + 13) % key_params["n"],
            (41 * seed + 17) % key_params["n"]
        )
        invariance_checks += int(canonical_key(reflected) == canonical_key(base))
        witness_checks += int(verify(reflected, carried3)[0])
        composed, carried4 = _rotated_reservoir(
            permuted, (31 * seed + 7) % key_params["n"],
            (43 * seed + 11) % key_params["n"]
        )
        invariance_checks += int(canonical_key(composed) == canonical_key(base))
        witness_checks += int(verify(composed, carried4)[0])
    keys = {canonical_key(make_instance(seed=seed, **key_params))
            for seed in range(1000, 1020)}
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 80 and witness_checks == 80
                and len(keys) == 20,
        "invariance_checks": invariance_checks,
        "transformed_witness_checks": witness_checks,
        "unrelated_distinct": len(keys),
        "unrelated_attempts": 20,
        "transformations": (
            "active-vertex renumbering and explicit-edge reordering; independent "
            "rotations and reflections of both reservoir coordinates; and a "
            "composition of active renumbering with reservoir rotation"
        ),
    }

    size_and_ops = []
    for seed in range(256):
        measured = make_instance(seed=1000 + seed, **ship_params)
        size_and_ops.append((*_answer_metrics(measured["answer"]),
                             _intended_route_operations(measured)))
    chars = max(x[0] for x in size_and_ops)
    tokens = max(x[1] for x in size_and_ops)
    elements = max(x[2] for x in size_and_ops)
    intended_ops = max(x[3] for x in size_and_ops)
    ev = G9_EVIDENCE
    hinted_attempts = ev["hinted"]["attempts"]
    placebo_attempts = ev["placebo"]["attempts"]
    hinted_rate = (ev["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (ev["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = chars <= 2000 and elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(ev["bare"]),
            "hinted": dict(ev["hinted"]),
            "placebo": dict(ev["placebo"]),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": ev["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "answer_size_sample_count": len(size_and_ops),
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
