#!/usr/bin/env python3
"""Verified weighted (k,r)-Center witnesses from arXiv:1704.08868.

The generator first samples one vertex in each color class, builds a
degree-balanced planted Multicolored Independent Set instance around those
vertices, and then applies the weighted reduction of Section 4 (Lemmas 15--16,
Theorem 17).  The center set is therefore known before the public instance is
assembled; it is never recovered by solving that instance.
"""

from __future__ import annotations

import hashlib
import heapq
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
except ImportError:  # Helpers are optional; this family stays stdlib-only.
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "edge-weighted graph given by the paper's guard and conflict gadgets",
        "vertex center set",
        "k-partite conflict matrices",
    ],
    "verification_operations": [
        "integer decoding of center vertices",
        "exact hexadecimal bit lookup for every selected color pair",
        "exact integer comparison with the radius in the paper's conflict gadget",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Lemmas 15 and 16 and Theorem 17: a k-Multicolored "
        "Independent Set maps to the choice vertices of a weighted (k,4n)-Center instance"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize that the paired radius guards force one choice vertex per "
        "color and that each conflict gadget forbids exactly one pair; without "
        "this reduction the solver faces the much larger weighted graph."
    ),
    "hardness_basis": (
        "Track A: Theorem 17 rules out n^o(vc+k) exact algorithms under ETH "
        "for weighted instances with vc<=4k; the shipping distribution uses "
        "growing k and degree-balanced regular color-pair constraints at the "
        "planted-CSP first-moment threshold, and the measured capped CSP/DPLL "
        "baseline is reported by selftest at the shipping preset."
    ),
    "max_answer_tokens": 23,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "demo": {"n": 3, "part_size": 4, "safe_degree": 1},
    "easy": {"n": 22, "part_size": 48, "safe_degree": 33},
    "medium": {"n": 24, "part_size": 56, "safe_degree": 39},
    "hard": {"n": 24, "part_size": 64, "safe_degree": 44},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The two radius guards on every color block force a minimum center set to "
    "encode exactly one local choice from that block."
)
PLACEBO_HINT = (
    "The fixed-width hexadecimal rows should be read carefully with the stated "
    "least-significant-bit indexing convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of exactly k distinct integer IDs, in increasing color "
        "order, containing one choice vertex i*s+x from each color i; "
        "0<=x<s."
    ),
    "bounds": {
        "array_length": "inst['k']",
        "center_id_lower_inclusive": 0,
        "center_id_upper_exclusive": "inst['k'] * inst['part_size']",
        "one_center_per_color": True,
        "colors": "inst['k']",
        "choices_per_color": "inst['part_size']",
    },
}

NOTES = (
    "Section 1 and the opening of Section 2 fix the native definition: centers "
    "are graph vertices, edge weights are positive integers (and may be "
    "non-symmetric), distance is shortest-path distance, and every non-center "
    "must be within r. Section 4 defines k-Multicolored Independent Set with "
    "one choice from each clique and gives the weighted construction used here: "
    "radius 4n, two guards and two hubs per color, and one conflict vertex for "
    "each cross-color source edge. Lemmas 15 and 16 prove both directions and "
    "Theorem 17 gives vc<=4k and the ETH lower bound n^o(vc+k). The easy regimes "
    "that had to be avoided are explicit in the paper: unweighted instances "
    "with a supplied vertex cover have the O*(5^vc) algorithm of Theorem 19; "
    "unweighted bounded tree-depth has the 2^O(td^2) algorithm of Theorem 21; "
    "fixed-r clique-width instances have the O*((3r+1)^cw) counting algorithm "
    "of Theorem 14; and Sections 5--6 give FPT approximation schemes. This "
    "family therefore uses the weighted, unbounded-radius Theorem 17 regime and "
    "grows k. Generation samples the witness first. Every color-pair safe graph "
    "is regular on both sides, made from a random relabeling of random cyclic "
    "matchings conditioned to contain the planted pair, so plant and decoys "
    "have identical degree. The attacks test degree outliers, deterministic "
    "greedy selection, randomized greedy restarts, centered spectral recovery, "
    "a min-conflicts local search, and an exact MRV/forward-checking CSP solver."
)


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _pair_index(i: int, j: int, k: int) -> int:
    if not (0 <= i < j < k):
        raise ValueError("pair indices must satisfy 0 <= i < j < k")
    return i * (2 * k - i - 1) // 2 + (j - i - 1)


def _safe(inst: dict, i: int, x: int, j: int, y: int) -> bool:
    """Whether the two source choices are nonadjacent (compatible)."""
    if i > j:
        i, j, x, y = j, i, y, x
    rows = inst["blocks"][_pair_index(i, j, inst["k"])]["safe_rows"]
    return bool((rows[x] >> y) & 1)


def _threshold_degree(k: int, part_size: int) -> int:
    density = math.exp(-2.0 * math.log(part_size) / max(1, k - 1))
    # The lower integer is intentionally used: crossing one regular matching
    # can multiply the expected number of accidental witnesses dramatically.
    return max(1, min(part_size - 1, int(math.floor(part_size * density))))


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant an independent transversal, then apply the paper's reduction.

    ``n`` is the number k of color classes.  ``part_size`` is the paper's n
    (choices per class).  Increasing either grows the CSP search; escalation
    grows ``part_size`` first so that the answer length remains fixed.
    """
    part_size = params.pop("part_size", 32)
    safe_degree = params.pop("safe_degree", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if (isinstance(part_size, bool) or not isinstance(part_size, int)
            or part_size < 3):
        raise ValueError("part_size must be an integer at least 3")
    if safe_degree is None:
        safe_degree = _threshold_degree(n, part_size)
    if (isinstance(safe_degree, bool) or not isinstance(safe_degree, int)
            or not 1 <= safe_degree < part_size):
        raise ValueError("safe_degree must be an integer in 1..part_size-1")

    rng = random.Random(seed)
    planted_local = [rng.randrange(part_size) for _ in range(n)]
    blocks = []
    safe_edge_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            left = list(range(part_size))
            right = list(range(part_size))
            rng.shuffle(left)
            rng.shuffle(right)
            planted_shift = (
                right[planted_local[j]] - left[planted_local[i]]
            ) % part_size
            others = [z for z in range(part_size) if z != planted_shift]
            shifts = set(rng.sample(others, safe_degree - 1))
            shifts.add(planted_shift)
            rows = []
            for x in range(part_size):
                mask = 0
                lx = left[x]
                for y in range(part_size):
                    if (right[y] - lx) % part_size in shifts:
                        mask |= 1 << y
                rows.append(mask)
            # Both sides are exactly regular, including the planted endpoints.
            assert all(row.bit_count() == safe_degree for row in rows)
            for y in range(part_size):
                assert sum((row >> y) & 1 for row in rows) == safe_degree
            assert (rows[planted_local[i]] >> planted_local[j]) & 1
            safe_edge_count += part_size * safe_degree
            blocks.append({"parts": [i, j], "safe_rows": rows})

    pair_count = n * (n - 1) // 2
    conflict_count = pair_count * part_size * (part_size - safe_degree)
    radius = 4 * part_size
    answer = [i * part_size + planted_local[i] for i in range(n)]
    return {
        "family": "paper-reduced weighted (k,r)-Center",
        "k": n,
        "part_size": part_size,
        "safe_degree": safe_degree,
        "radius": radius,
        "blocks": blocks,
        "safe_edge_count": safe_edge_count,
        "conflict_vertex_count": conflict_count,
        "weighted_graph_vertex_count": n * part_size + 4 * n + conflict_count,
        "weighted_graph_edge_count": 4 * n * part_size + 4 * conflict_count,
        "answer": answer,
    }


def _render_blocks(inst: dict) -> str:
    width = (inst["part_size"] + 3) // 4
    lines = []
    for block in inst["blocks"]:
        i, j = block["parts"]
        rows = " ".join(
            format(row, f"0{width}x") for row in block["safe_rows"]
        )
        lines.append(f"{i},{j}: {rows}")
    return "\n".join(lines)


def render(inst: dict) -> str:
    k, s, radius = inst["k"], inst["part_size"], inst["radius"]
    statement = f"""Weighted (k,r)-Center with guard and conflict gadgets

For an undirected graph with positive integer edge weights, the distance from
v to u is the minimum total edge weight of any path from v to u. A center set
of budget k and radius r is a set of at most k graph vertices such that every
vertex not in the set is at distance at most r from at least one center.

This instance has k={k}, r={radius}, and s={s} choices per color. All color and
local-choice indices are 0-based. The graph below is specified exactly; edges
not created by these rules do not exist.

Choice vertices are P(i,x), for 0<=i<{k} and 0<=x<{s}. P(i,x) has integer ID
i*s+x. For each color i there are hubs A(i), B(i) and guards G(i,0), G(i,1).
For every x, add these undirected weighted edges:

  P(i,x)--G(i,0) weight {radius}; P(i,x)--G(i,1) weight {radius}
  P(i,x)--A(i) weight s+x+1; P(i,x)--B(i) weight 2*s-x

For each color pair i<j, one line below contains {s} fixed-width hexadecimal
bitmasks, in increasing x for color i. Bit y (least-significant bit is y=0) is
1 when choices P(i,x),P(j,y) are SAFE (nonadjacent in the source graph), and 0
when they conflict. Padding zeroes beyond bit {s - 1} are ignored.

{_render_blocks(inst)}

For every 0 bit at pair (i,j), row x, bit y, create a conflict vertex U(i,x,j,y)
and exactly four incident edges:

  U--A(i) weight 3*s-x;     U--B(i) weight 2*s+x+1
  U--A(j) weight 3*s-y;     U--B(j) weight 2*s+y+1

There are {inst['weighted_graph_vertex_count']} graph vertices, including
{inst['conflict_vertex_count']} conflict vertices. The two guards for each
color force every radius-{radius} center set of size at most {k} to use exactly
one P(i,x) from every color. A conflict vertex U(i,x,j,y) is at distance
{radius + 1} from both P(i,x) and P(j,y), while a different choice in either
of those colors reaches it within radius. Thus the selected pair for every
color pair must be a displayed 1 bit.

Output the {k} selected choice-vertex IDs as a JSON array, one ID from each
color, in increasing color order. IDs must be distinct integers in
0,...,{k * s - 1}; the entry for color i must lie in i*s,...,(i+1)*s-1.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format only: <answer>{json.dumps([i * s for i in range(k)])}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Read the last tagged JSON answer, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any represented center witness without reading ``inst['answer']``."""
    k, s = inst["k"], inst["part_size"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k:
        return False, f"wrong number of centers: expected {k}, got {len(answer)}"
    for pos, center in enumerate(answer):
        if isinstance(center, bool) or not isinstance(center, int):
            return False, f"center at array position {pos} is not an integer"
        if not 0 <= center < k * s:
            return False, f"center ID {center} is out of range 0..{k * s - 1}"
    if len(set(answer)) != k:
        return False, "center IDs must be distinct"

    by_color = {}
    for center in answer:
        color, local = divmod(center, s)
        if color in by_color:
            return False, f"more than one center was selected from color {color}"
        by_color[color] = local
    missing = [i for i in range(k) if i not in by_color]
    if missing:
        return False, f"no center was selected from color {missing[0]}"

    # This bit test is also the exact radius calculation for the native graph.
    # At conflict U(i,x,j,y), P(i,z) is at distance <=4s iff z!=x:
    # min((s+z+1)+(3s-x), (2s-z)+(2s+x+1))
    # = 4s+1-|z-x|.  Both selected endpoints miss U only when z=x,w=y.
    for i in range(k):
        for j in range(i + 1, k):
            x, y = by_color[i], by_color[j]
            if not _safe(inst, i, x, j, y):
                return (
                    False,
                    f"conflict vertex U({i},{x},{j},{y}) is at radius+1 "
                    "from both selected choices",
                )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the strongest free prior: one choice in every color."""
    s = inst["part_size"]
    return [i * s + rng.randrange(s) for i in range(inst["k"])]


def search_space(inst: dict) -> int | None:
    return inst["part_size"] ** inst["k"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 2_000_000:
        return None
    k, s = inst["k"], inst["part_size"]
    count = 0
    for local in itertools.product(range(s), repeat=k):
        answer = [i * s + local[i] for i in range(k)]
        count += int(verify(inst, answer)[0])
    return count


def _safe_adjacency(inst: dict) -> list[list[list[int]]]:
    """adj[i][x][j] is the safe-neighbor mask in color j."""
    k, s = inst["k"], inst["part_size"]
    adj = [[[0 for _ in range(k)] for _ in range(s)] for _ in range(k)]
    for block in inst["blocks"]:
        i, j = block["parts"]
        for x, row in enumerate(block["safe_rows"]):
            adj[i][x][j] = row
            bits = row
            while bits:
                bit = bits & -bits
                y = bit.bit_length() - 1
                bits -= bit
                adj[j][y][i] |= 1 << x
    return adj


def _block_invariant(rows: list[int], s: int) -> tuple:
    row_common = sorted(
        (rows[a] & rows[b]).bit_count()
        for a in range(s) for b in range(a + 1, s)
    )
    columns = [0] * s
    for a, row in enumerate(rows):
        bits = row
        while bits:
            bit = bits & -bits
            y = bit.bit_length() - 1
            bits -= bit
            columns[y] |= 1 << a
    col_common = sorted(
        (columns[a] & columns[b]).bit_count()
        for a in range(s) for b in range(a + 1, s)
    )
    sides = sorted((tuple(row_common), tuple(col_common)))
    return tuple(sides)


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant under color and within-color relabellings.

    Exact graph isomorphism is not claimed.  Each bipartite constraint is
    represented by its two multisets of pairwise common-neighbor counts, then
    the color-incidence pattern of those block invariants is canonicalized.
    """
    k, s = inst["k"], inst["part_size"]
    block_hashes = {}
    for block in inst["blocks"]:
        i, j = block["parts"]
        inv = _block_invariant(block["safe_rows"], s)
        digest = hashlib.sha256(
            json.dumps(inv, separators=(",", ":")).encode("ascii")
        ).hexdigest()
        block_hashes[i, j] = digest
    color_profiles = []
    for i in range(k):
        incident = []
        for j in range(k):
            if i == j:
                continue
            incident.append(block_hashes[min(i, j), max(i, j)])
        color_profiles.append(tuple(sorted(incident)))
    payload = [
        k,
        s,
        inst["safe_degree"],
        sorted(block_hashes.values()),
        sorted(color_profiles),
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow each color's haystack while holding the center-set length fixed."""
    if not isinstance(params, dict):
        return None
    k = int(params.get("n", 0))
    s = int(params.get("part_size", 0))
    if k < 3 or s < 3:
        return None
    new_s = max(s + 8, (3 * s + 1) // 2)
    return {
        "n": k,
        "part_size": new_s,
        "safe_degree": _threshold_degree(k, new_s),
    }


def _local_candidate(inst: dict, candidate: object | None) -> list[int] | None:
    if candidate is None or not verify(inst, candidate)[0]:
        return None
    s = inst["part_size"]
    local = [-1] * inst["k"]
    for center in candidate:
        i, x = divmod(center, s)
        local[i] = x
    return local


def _global_answer(local: list[int], s: int) -> list[int]:
    return [i * s + local[i] for i in range(len(local))]


def _attack_outlier_degree(inst: dict) -> list[int]:
    """Choose the maximum safe-degree vertex; exact regularity forces a tie."""
    adj = _safe_adjacency(inst)
    k, s = inst["k"], inst["part_size"]
    local = []
    for i in range(k):
        local.append(max(
            range(s),
            key=lambda x: (
                sum(adj[i][x][j].bit_count() for j in range(k) if j != i),
                -x,
            ),
        ))
    return _global_answer(local, s)


def _attack_greedy(inst: dict) -> list[int] | None:
    """MRV-color greedy with maximum remaining compatibility, no backtracking."""
    k, s = inst["k"], inst["part_size"]
    adj = _safe_adjacency(inst)
    full = (1 << s) - 1
    domains = [full] * k
    selected = [-1] * k
    remaining = set(range(k))
    while remaining:
        color = min(remaining, key=lambda c: (domains[c].bit_count(), c))
        bits = domains[color]
        if not bits:
            return None
        options = []
        while bits:
            bit = bits & -bits
            value = bit.bit_length() - 1
            bits -= bit
            score = sum(
                (domains[c] & adj[color][value][c]).bit_count()
                for c in remaining if c != color
            )
            options.append((-score, value))
        value = min(options)[1]
        selected[color] = value
        remaining.remove(color)
        for c in remaining:
            domains[c] &= adj[color][value][c]
    return _global_answer(selected, s)


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 256
) -> list[int] | None:
    k, s = inst["k"], inst["part_size"]
    adj = _safe_adjacency(inst)
    full = (1 << s) - 1
    for _ in range(restarts):
        domains = [full] * k
        selected = [-1] * k
        remaining = set(range(k))
        while remaining:
            minimum = min(domains[c].bit_count() for c in remaining)
            tied = [c for c in remaining if domains[c].bit_count() == minimum]
            color = rng.choice(tied)
            bits = domains[color]
            if not bits:
                break
            values = []
            while bits:
                bit = bits & -bits
                values.append(bit.bit_length() - 1)
                bits -= bit
            value = rng.choice(values)
            selected[color] = value
            remaining.remove(color)
            for c in remaining:
                domains[c] &= adj[color][value][c]
        else:
            return _global_answer(selected, s)
    return None


def _attack_min_conflicts(
    inst: dict,
    rng: random.Random,
    restarts: int = 4,
    steps: int = 500,
) -> list[int] | None:
    """Repair a random assignment by minimizing its incident conflicts."""
    k, s = inst["k"], inst["part_size"]
    adj = _safe_adjacency(inst)
    for _ in range(restarts):
        selected = [rng.randrange(s) for _ in range(k)]
        for _ in range(steps):
            bad_colors = [
                i for i in range(k)
                if any(
                    not ((adj[i][selected[i]][j] >> selected[j]) & 1)
                    for j in range(k) if j != i
                )
            ]
            if not bad_colors:
                return _global_answer(selected, s)
            color = rng.choice(bad_colors)
            best_score = k + 1
            best_values = []
            for value in range(s):
                score = sum(
                    not ((adj[color][value][j] >> selected[j]) & 1)
                    for j in range(k) if j != color
                )
                if score < best_score:
                    best_score = score
                    best_values = [value]
                elif score == best_score:
                    best_values.append(value)
            selected[color] = rng.choice(best_values)
    return None


def _attack_exact_dpll(inst: dict, node_limit: int = 1_000_000) -> dict:
    """Exact CSP backtracking with MRV, forward checking, and value ordering."""
    k, s = inst["k"], inst["part_size"]
    adj = _safe_adjacency(inst)
    full = (1 << s) - 1
    selected = [-1] * k
    nodes = 0
    hit_limit = False

    def visit(domains: list[int], remaining: tuple[int, ...]):
        nonlocal nodes, hit_limit
        if not remaining:
            return list(selected)
        if nodes >= node_limit:
            hit_limit = True
            return None
        color = min(remaining, key=lambda c: domains[c].bit_count())
        rest = tuple(c for c in remaining if c != color)
        bits = domains[color]
        ordering = []
        while bits:
            bit = bits & -bits
            value = bit.bit_length() - 1
            bits -= bit
            score = sum(
                (domains[c] & adj[color][value][c]).bit_count() for c in rest
            )
            ordering.append((-score, value))
        for _, value in sorted(ordering):
            nodes += 1
            if nodes > node_limit:
                hit_limit = True
                return None
            narrowed = list(domains)
            feasible = True
            for c in rest:
                narrowed[c] &= adj[color][value][c]
                if not narrowed[c]:
                    feasible = False
                    break
            if feasible:
                selected[color] = value
                found = visit(narrowed, rest)
                if found is not None:
                    return found
        selected[color] = -1
        return None

    started = time.perf_counter()
    local = visit([full] * k, tuple(range(k)))
    elapsed = time.perf_counter() - started
    return {
        "candidate": None if local is None else _global_answer(local, s),
        "nodes": nodes,
        "hit_limit": hit_limit,
        "wall_clock_sec": elapsed,
    }


def _attack_spectral(inst: dict, seed: int, iterations: int = 16) -> list[int]:
    """Centered compatibility-adjacency power iteration and per-color rounding."""
    k, s = inst["k"], inst["part_size"]
    rng = random.Random(seed)
    vector = [rng.random() - 0.5 for _ in range(k * s)]
    density = inst["safe_degree"] / s
    for _ in range(iterations):
        group_sums = [sum(vector[i * s:(i + 1) * s]) for i in range(k)]
        nxt = [0.0] * (k * s)
        for block in inst["blocks"]:
            i, j = block["parts"]
            base_i = density * group_sums[j]
            base_j = density * group_sums[i]
            for x, row in enumerate(block["safe_rows"]):
                bits = row
                total = 0.0
                source = vector[i * s + x]
                while bits:
                    bit = bits & -bits
                    y = bit.bit_length() - 1
                    bits -= bit
                    total += vector[j * s + y]
                    nxt[j * s + y] += source
                nxt[i * s + x] += total - base_i
            for y in range(s):
                nxt[j * s + y] -= base_j
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    high = [max(range(s), key=lambda x: vector[i * s + x]) for i in range(k)]
    low = [min(range(s), key=lambda x: vector[i * s + x]) for i in range(k)]
    high_answer = _global_answer(high, s)
    if verify(inst, high_answer)[0]:
        return high_answer
    return _global_answer(low, s)


def _relabel_instance(
    inst: dict,
    color_map: list[int],
    vertex_maps: list[list[int]],
) -> dict:
    """Carry the weighted construction and its certificate through relabelling."""
    k, s = inst["k"], inst["part_size"]
    if sorted(color_map) != list(range(k)):
        raise ValueError("color_map is not a permutation")
    if len(vertex_maps) != k or any(sorted(p) != list(range(s)) for p in vertex_maps):
        raise ValueError("a vertex map is not a permutation")
    new_rows = {(i, j): [0] * s for i in range(k) for j in range(i + 1, k)}
    for block in inst["blocks"]:
        old_i, old_j = block["parts"]
        for old_x, row in enumerate(block["safe_rows"]):
            bits = row
            while bits:
                bit = bits & -bits
                old_y = bit.bit_length() - 1
                bits -= bit
                ni, nj = color_map[old_i], color_map[old_j]
                nx = vertex_maps[old_i][old_x]
                ny = vertex_maps[old_j][old_y]
                if ni < nj:
                    new_rows[ni, nj][nx] |= 1 << ny
                else:
                    new_rows[nj, ni][ny] |= 1 << nx
    blocks = [
        {"parts": [i, j], "safe_rows": rows}
        for (i, j), rows in sorted(new_rows.items())
    ]
    old_local = [None] * k
    for center in inst["answer"]:
        i, x = divmod(center, s)
        old_local[i] = x
    new_local = [0] * k
    for old_i, old_x in enumerate(old_local):
        new_local[color_map[old_i]] = vertex_maps[old_i][old_x]
    pair_count = k * (k - 1) // 2
    conflicts = pair_count * s * (s - inst["safe_degree"])
    return {
        "family": inst["family"],
        "k": k,
        "part_size": s,
        "safe_degree": inst["safe_degree"],
        "radius": 4 * s,
        "blocks": blocks,
        "safe_edge_count": pair_count * s * inst["safe_degree"],
        "conflict_vertex_count": conflicts,
        "weighted_graph_vertex_count": k * s + 4 * k + conflicts,
        "weighted_graph_edge_count": 4 * k * s + 4 * conflicts,
        "answer": _global_answer(new_local, s),
    }


def _explicit_weighted_graph_check(inst: dict, answer: list[int]) -> bool:
    """Expand a demo instance and independently run multi-source Dijkstra."""
    k, s = inst["k"], inst["part_size"]
    choice_count = k * s
    next_vertex = choice_count + 4 * k
    graph = [[] for _ in range(next_vertex + inst["conflict_vertex_count"])]

    def hubs(i: int) -> tuple[int, int, int, int]:
        base = choice_count + 4 * i
        return base, base + 1, base + 2, base + 3

    def add(u: int, v: int, weight: int) -> None:
        graph[u].append((v, weight))
        graph[v].append((u, weight))

    for i in range(k):
        a, b, g0, g1 = hubs(i)
        for x in range(s):
            p = i * s + x
            add(p, g0, 4 * s)
            add(p, g1, 4 * s)
            add(p, a, s + x + 1)
            add(p, b, 2 * s - x)
    u = next_vertex
    full = (1 << s) - 1
    for block in inst["blocks"]:
        i, j = block["parts"]
        ai, bi, _, _ = hubs(i)
        aj, bj, _, _ = hubs(j)
        for x, safe_row in enumerate(block["safe_rows"]):
            bits = full ^ safe_row
            while bits:
                bit = bits & -bits
                y = bit.bit_length() - 1
                bits -= bit
                add(u, ai, 3 * s - x)
                add(u, bi, 2 * s + x + 1)
                add(u, aj, 3 * s - y)
                add(u, bj, 2 * s + y + 1)
                u += 1
    if u != len(graph):
        return False
    infinity = 10 ** 30
    distance = [infinity] * len(graph)
    queue = []
    for center in answer:
        distance[center] = 0
        heapq.heappush(queue, (0, center))
    while queue:
        dist, vertex = heapq.heappop(queue)
        if dist != distance[vertex]:
            continue
        for neighbor, weight in graph[vertex]:
            nd = dist + weight
            if nd < distance[neighbor]:
                distance[neighbor] = nd
                heapq.heappush(queue, (nd, neighbor))
    return max(distance) <= inst["radius"]


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _find_conflicting_replacement(inst: dict) -> list[int] | None:
    s = inst["part_size"]
    local = [center % s for center in inst["answer"]]
    for i in range(inst["k"]):
        for x in range(s):
            if x == local[i]:
                continue
            for j in range(inst["k"]):
                if i != j and not _safe(inst, i, x, j, local[j]):
                    bad = list(inst["answer"])
                    bad[i] = i * s + x
                    return bad
    return None


def selftest() -> dict:
    report: dict = {}

    failures = []
    attempts = 0
    explicit_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
            if preset == "demo":
                explicit_checks += 1
                if not _explicit_weighted_graph_check(inst, inst["answer"]):
                    failures.append(f"{preset}/{seed}: expanded Dijkstra check failed")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "explicit_weighted_graph_checks": explicit_checks,
        "failures": failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])

    replacement = _find_conflicting_replacement(shipping)
    fixed = {
        "empty": [],
        "drop_one": shipping["answer"][:-1],
        "out_of_range": shipping["answer"][:-1]
        + [shipping["k"] * shipping["part_size"]],
        "duplicate": shipping["answer"][:-1] + [shipping["answer"][0]],
        "swap_one": replacement,
    }
    cases = {}
    for name, bad in fixed.items():
        if bad is None:
            cases[name] = {"rejected": False, "reason": "no corruption found"}
        else:
            ok, why = verify(shipping, bad)
            cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The guard gadgets leave the following center set.\n\n"
        "<answer>```json\n" + json.dumps(shipping["answer"]) + "\n```</answer>\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"]
        and parse_answer("no tagged answer") is None
        and parse_answer("<answer>{bad json}</answer>") is None,
        "parsed": parsed,
    }

    guess_rng = random.Random(934857)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6
        and search_space(shipping) > 1_000_000,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_probability": guess_hits / guess_total,
        "candidate_space": search_space(shipping),
        "prior": "uniform over one in-range choice vertex in every color",
    }

    baseline_inst = make_instance(seed=100, **DIFFICULTY[SHIPPING_DIFFICULTY])
    baseline = _attack_exact_dpll(baseline_inst)
    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline_solved = baseline["candidate"] is not None and verify(
        baseline_inst, baseline["candidate"]
    )[0]
    report["G5_density_and_baseline"] = {
        "pass": not baseline_solved and baseline["nodes"] >= 1_000_000
        and demo_count is not None,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_solution_density_estimate": guess_hits / guess_total,
        "shipping_candidate_space": search_space(shipping),
        "baseline_name": "exact CSP DPLL with MRV and forward checking",
        "baseline_wall_clock_seconds": baseline["wall_clock_sec"],
        "baseline_search_nodes": baseline["nodes"],
        "baseline_node_budget": 1_000_000,
        "baseline_solved": int(baseline_solved),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
    }

    names = [
        "outlier_safe_degree",
        "greedy_mrv_no_backtracking",
        "random_greedy_256_restarts",
        "min_conflicts_4x500_repairs",
        "centered_spectral_power_iteration",
        "exact_csp_dpll_1000000_nodes",
    ]
    attack_results = {name: {"successes": 0, "attempts": 0} for name in names}
    exact_nodes = 0
    exact_seconds = 0.0
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_safe_degree": _attack_outlier_degree(inst),
            "greedy_mrv_no_backtracking": _attack_greedy(inst),
            "random_greedy_256_restarts": _attack_random_restarts(
                inst, random.Random(seed ^ 0xA51C), 256
            ),
            "min_conflicts_4x500_repairs": _attack_min_conflicts(
                inst, random.Random(seed ^ 0x51C0), 4, 500
            ),
            "centered_spectral_power_iteration": _attack_spectral(
                inst, seed ^ 0xC0FFEE, 16
            ),
        }
        exact = _attack_exact_dpll(inst)
        candidates["exact_csp_dpll_1000000_nodes"] = exact["candidate"]
        exact_nodes += exact["nodes"]
        exact_seconds += exact["wall_clock_sec"]
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(
                candidate is not None and verify(inst, candidate)[0]
            )
    report["G6_adversary_panel"] = {
        "pass": all(
            item["successes"] == 0 and item["attempts"] >= 8
            for item in attack_results.values()
        ),
        "attacks": attack_results,
        "standard_algorithm": {
            "name": "exact CSP DPLL with MRV and forward checking",
            "completeness": "complete when run without the reported node cap",
            "complexity": "O(part_size^k) worst case, matching the paper's XP bound",
            "aggregate_nodes": exact_nodes,
            "aggregate_wall_clock_seconds": exact_seconds,
        },
    }

    work_sizes = []
    for params in DIFFICULTY.values():
        inst = make_instance(seed=7, **params)
        work_sizes.append(inst["weighted_graph_vertex_count"])
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["safe_degree"] = _threshold_degree(
        doubled_params["n"], doubled_params["part_size"]
    )
    doubled = make_instance(seed=7, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(work_sizes, work_sizes[1:]))
        and doubled_ok,
        "named_work_sizes": work_sizes,
        "named_n_values": [p["n"] for p in DIFFICULTY.values()],
        "doubled_n": doubled_params["n"],
        "doubled_work_size": doubled["weighted_graph_vertex_count"],
        "doubled_verification": doubled_why,
    }

    invariant_checks = 0
    transformed_verify_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        rng = random.Random(seed ^ 0x8CA1)
        color_perm = list(range(inst["k"]))
        rng.shuffle(color_perm)
        identity_colors = list(range(inst["k"]))
        identity_vertices = [list(range(inst["part_size"])) for _ in range(inst["k"])]
        vertex_perms = []
        for _ in range(inst["k"]):
            permutation = list(range(inst["part_size"]))
            rng.shuffle(permutation)
            vertex_perms.append(permutation)
        transforms = [
            _relabel_instance(inst, color_perm, identity_vertices),
            _relabel_instance(inst, identity_colors, vertex_perms),
            _relabel_instance(inst, color_perm, vertex_perms),
        ]
        for changed in transforms:
            invariant_checks += 1
            if canonical_key(changed) != key:
                g8_failures.append(f"seed {seed}: canonical key changed")
            transformed_verify_checks += 1
            ok, why = verify(changed, changed["answer"])
            if not ok:
                g8_failures.append(f"seed {seed}: real relabelling failed: {why}")
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "transformed_instances_verified": transformed_verify_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": g8_failures,
        "invariant_kind": (
            "bipartite common-neighbor spectra plus color-incidence refinement; not full GI"
        ),
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    # Decode one local index per color, then check one exact matrix bit per pair.
    route_operations = (
        shipping["k"] + shipping["k"] * (shipping["k"] - 1) // 2
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and route_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
