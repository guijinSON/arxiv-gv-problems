"""Self-contained verified generator for arXiv:1507.06286.

The paper's native witness is a graph derangement: a fixed-point-free
permutation f of the vertices for which every {v,f(v)} is an edge.  Instances
here are connected simple graphs assembled around a compact affine-XOR
derangement.  Many almost-complete affine matchings crowd the same graph, so
the planted matching is not a lone per-edge outlier.

This is honestly Track B.  A graph derangement is a perfect matching in the
bipartite double cover, so Hopcroft--Karp finds an explicit witness in
polynomial time.  The module measures that reference algorithm and separately
tests cheap no-tool attacks.  Only the Python standard library is required.
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
from collections import Counter, deque
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family needs no helper
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite simple connected undirected graph",
        "fixed-point-free vertex permutation",
    ],
    "verification_operations": [
        "integer range and shape checks",
        "exact bitwise XOR and parity",
        "permutation injectivity check",
        "graph edge-membership lookup",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Split each vertex label into two bit blocks and look for an affine-XOR "
        "neighbor rule; without that coordinate change one must construct a "
        "perfect matching in the graph's bipartite double cover."
    ),
    "hardness_basis": (
        "Track B: by the graph-derangement definition and the Q-factor/Hall "
        "criterion cited in the Introduction, bipartite-double-cover matching "
        "finds a witness with Hopcroft--Karp in O(E sqrt(V)) time; selftest "
        "at shipping n=128 averaged about 10,770 edge scans, 2.75 BFS phases, "
        "and 0.0007 seconds on the build host, while the affine-XOR route uses "
        "at most 136 exact operations "
        "after recognizing the coordinate invariant, a recognition that the "
        "no-tool solver must make from thousands of crowded edges."
    ),
    "max_answer_tokens": 13,
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
        "Either (i) an explicit JSON permutation table of all n vertices, "
        "already constrained to be bijective and fixed-point-free, or (ii) an "
        "affine-XOR rule with nonzero r-bit a, s rows of r-bit masks, and an "
        "s-bit d.  Both are finite exact encodings of a vertex function."
    ),
    "bounds": {
        "table_length": "n",
        "table_values": "a fixed-point-free permutation of 0..n-1",
        "affine_a": "1..2^r-1",
        "affine_rows": "exactly s integers in 0..2^r-1",
        "affine_d": "0..2^s-1",
        "shipping_n": 128,
    },
}

DIFFICULTY = {
    "hard": {"n": 128, "near_rules": 42, "u_bits": 3},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "One neighbor displacement persists under XOR within each first-coordinate "
    "block, and those persistent displacements vary affinely between blocks."
)
PLACEBO_HINT = (
    "The vertex identifiers and adjacency rows are exact integers, so careful "
    "bookkeeping of their stated ranges is useful throughout."
)

# Populated after the script-owned bare/hinted/placebo runs.  Zero attempts are
# permitted here because all three arms are diagnostics, not selftest gates.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "oracle_unreachable_http_403_key_limit",
}

NOTES = r"""
Paper reading.  Section 2 defines a graph derangement exactly as an injective
map f:V->V with f(v) different from and adjacent to v.  Because V is finite,
injective means bijective.  The Introduction states the equivalent Q-factor
criterion and the neighborhood condition |N(W)|>=|W|.  Proposition 3.1 proves
that every graph derangement is a strict Territorial Raider equilibrium for
h<1; Theorem 3.3 proves the converse.  Thus the certificate is the paper's own
vertex function, not a SAT encoding or an adjacency-only surrogate.

Step 0 / easy mechanism.  A graph derangement is precisely a perfect matching
between left and right copies of V with (v,w) allowed when {v,w} is an edge.
Hopcroft--Karp therefore produces one in O(E sqrt(V)); the paper also points to
the equivalent Hall/Tutte neighborhood condition and suggests equilibrium
learning algorithms in its Introduction.  No distributional hardness theorem
is given.  Track A would be false, so this module declares Track B, runs the
matching algorithm, and reports its actual work rather than hiding it.

Generation.  Vertices are pairs (u,v) of bit blocks.  The certificate is drawn
first as f(u,v)=(u XOR a, v XOR C*u XOR d), with a nonzero and C*a=0.  Hence f
is a fixed-point-free involution, and its unordered pairs are planted edges.
Other affine involutions are sampled from exactly the same rule distribution;
one private edge of each is withheld and reserved globally, turning it into a
near-rule.  Shuffled cross-block Hamilton-cycle edges guarantee connectedness,
and additional cross-block filler edges restore crowding.  None of this solves
the completed instance.

Attacks.  The per-edge XOR outlier attack, lexicographic greedy permutation,
modal affine ansatz, and 512 structure-aware random derangements are tested on
eight shipping seeds.  Near-rules prevent one affine signature from being a
lone frequency spike; if their union accidentally completes one of the five
deterministic cheap ansatzes, one non-planted and non-Hamiltonian edge of that
ansatz is withheld.  The successful Hopcroft--Karp run is kept
under reference_algorithm, as Track B requires.  The compact route reads the
affine block invariant and emits its few parameters; verification expands it
and checks the graph exactly.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 500_000


def _validate_params(n: int, near_rules: int, u_bits: int | None) -> tuple[int, int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n & (n - 1):
        raise ValueError("n must be a power of two and at least 8")
    total_bits = n.bit_length() - 1
    if u_bits is None:
        u_bits = total_bits // 2
    if isinstance(u_bits, bool) or not isinstance(u_bits, int):
        raise ValueError("u_bits must be an integer")
    if not 1 <= u_bits < total_bits:
        raise ValueError("u_bits must lie strictly between 0 and log2(n)")
    if isinstance(near_rules, bool) or not isinstance(near_rules, int):
        raise ValueError("near_rules must be an integer")
    if not 1 <= near_rules <= min(192, (1 << 20)):
        raise ValueError("near_rules must lie in [1,192]")
    v_bits = total_bits - u_bits
    # a has 2^r-1 choices; every row lies in the (r-1)-dimensional
    # orthogonal space to a; d is arbitrary.
    involution_count = ((1 << u_bits) - 1) * (1 << (
        v_bits * (u_bits - 1) + v_bits
    ))
    if near_rules > involution_count:
        raise ValueError(
            f"near_rules exceeds the {involution_count} distinct rules at this size"
        )
    return u_bits, v_bits


def _parity(value: int) -> int:
    return value.bit_count() & 1


def _linear(rows: list[int], u: int) -> int:
    value = 0
    for bit, row in enumerate(rows):
        value |= _parity(row & u) << bit
    return value


def _affine_image(x: int, r: int, s: int, a: int,
                  rows: list[int], d: int) -> int:
    mask = (1 << s) - 1
    u, v = x >> s, x & mask
    return ((u ^ a) << s) | (v ^ _linear(rows, u) ^ d)


def _rule_key(rule: tuple[int, tuple[int, ...], int]) -> tuple[Any, ...]:
    return rule


def _sample_involution(rng: random.Random, r: int, s: int
                       ) -> tuple[int, tuple[int, ...], int]:
    a = rng.randrange(1, 1 << r)
    rows: list[int] = []
    for _ in range(s):
        while True:
            row = rng.randrange(1 << r)
            if _parity(row & a) == 0:
                rows.append(row)
                break
    d = rng.randrange(1 << s)
    return a, tuple(rows), d


def _rule_edges(n: int, r: int, s: int,
                rule: tuple[int, tuple[int, ...], int]) -> set[tuple[int, int]]:
    a, row_tuple, d = rule
    rows = list(row_tuple)
    edges: set[tuple[int, int]] = set()
    for x in range(n):
        y = _affine_image(x, r, s, a, rows, d)
        edges.add((x, y) if x < y else (y, x))
    return edges


def _cross_edge(rng: random.Random, n: int, s: int) -> tuple[int, int]:
    u_count = n >> s
    x = rng.randrange(n)
    xu, xv = x >> s, x & ((1 << s) - 1)
    yu = xu ^ rng.randrange(1, u_count)
    yv = rng.randrange(1 << s)
    y = (yu << s) | yv
    return (x, y) if x < y else (y, x)


def _hamilton_cycle(rng: random.Random, n: int, s: int,
                    forbidden: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Make a cross-u Hamilton cycle, retrying only the random presentation."""
    u_count = n >> s
    v_count = 1 << s
    for _ in range(400):
        order_u = list(range(u_count))
        rng.shuffle(order_u)
        buckets: dict[int, list[int]] = {}
        for u in range(u_count):
            vals = list(range(v_count))
            rng.shuffle(vals)
            buckets[u] = vals
        order = [
            (u << s) | buckets[u][round_no]
            for round_no in range(v_count)
            for u in order_u
        ]
        cycle: set[tuple[int, int]] = set()
        good = True
        for i, x in enumerate(order):
            y = order[(i + 1) % n]
            edge = (x, y) if x < y else (y, x)
            if edge in forbidden:
                good = False
                break
            cycle.add(edge)
        if good and len(cycle) == n:
            return cycle
    raise RuntimeError("could not construct a reserved-edge-free Hamilton cycle")


def make_instance(n: int, seed: int = 0, *, near_rules: int = 2,
                  u_bits: int | None = None) -> dict:
    """Inverse-generate a connected graph and a known graph derangement."""
    r, s = _validate_params(n, near_rules, u_bits)
    rng = random.Random(seed)

    rules: list[tuple[int, tuple[int, ...], int]] = []
    seen: set[tuple[Any, ...]] = set()
    while len(rules) < near_rules:
        rule = _sample_involution(rng, r, s)
        if not rules and rule == (1, tuple([0] * s), 0):
            # The renderer uses this harmless value only to demonstrate syntax.
            # It must never itself be the planted answer.
            continue
        if _rule_key(rule) not in seen:
            seen.add(_rule_key(rule))
            rules.append(rule)

    # G: the first rule and its certificate exist before any graph is assembled.
    planted = rules[0]
    planted_edges = _rule_edges(n, r, s, planted)
    rule_edge_sets = [_rule_edges(n, r, s, rule) for rule in rules]

    # Withhold one non-planted edge from every decoy and reserve it globally.
    # Thus another near-rule cannot accidentally repair the advertised defect.
    reserved: set[tuple[int, int]] = set()
    for edge_set in rule_edge_sets[1:]:
        choices = sorted(edge_set - planted_edges - reserved)
        if not choices:
            choices = sorted(edge_set - planted_edges)
        if not choices:
            raise RuntimeError("duplicate affine matching escaped validation")
        reserved.add(choices[rng.randrange(len(choices))])

    edges = set(planted_edges)
    for edge_set in rule_edge_sets[1:]:
        edges.update(edge_set - reserved)

    # Connectivity is a construction invariant, not a post-hoc search result.
    cycle_edges = _hamilton_cycle(rng, n, s, reserved)
    edges.update(cycle_edges)

    # One same-marginal cross-block filler per damaged near-rule masks raw edge
    # counts without ever restoring a reserved edge.
    filler_goal = max(0, near_rules - 1)
    fillers = 0
    while fillers < filler_goal:
        edge = _cross_edge(rng, n, s)
        if edge not in edges and edge not in reserved:
            edges.add(edge)
            fillers += 1

    # A union of incomplete matchings can accidentally complete a cheap
    # aggregate ansatz.  Treat such an accident exactly like a near-rule: remove
    # one edge of that candidate, never a planted edge and never a connectivity
    # edge.  This is attack-aware decoy rejection, not certificate search; the
    # planted certificate above is unchanged and remains known by construction.
    for _ in range(64):
        probe = {
            "n": n,
            "u_bits": r,
            "v_bits": s,
            "edges": [[x, y] for x, y in sorted(edges)],
        }
        probes = [
            _example_copy_attack(probe),
            _xor_outlier_attack(probe),
            _greedy_table_attack(probe),
            _basis_first_attack(probe),
            _modal_affine_attack(probe),
        ]
        passing = next((candidate for candidate in probes
                        if _fast_valid(probe, candidate)), None)
        if passing is None:
            break
        image, reason = _expand_answer(probe, passing)
        if image is None:
            raise AssertionError(reason)
        candidate_edges = {
            ((x, y) if x < y else (y, x))
            for x, y in enumerate(image)
        }
        removable = sorted(candidate_edges - planted_edges - cycle_edges)
        if not removable:
            # The hand-scale demo intentionally may expose the plant outright.
            # At larger presets the crowded panel is checked independently by G6.
            break
        edges.remove(removable[rng.randrange(len(removable))])
    else:
        raise RuntimeError("attack-aware decoy rejection did not stabilize")

    edge_list = [[x, y] for x, y in sorted(edges)]
    a, row_tuple, d = planted
    answer = {
        "kind": "affine_xor",
        "a": a,
        "rows": list(row_tuple),
        "d": d,
    }
    return {
        "paper": "arXiv:1507.06286",
        "n": n,
        "u_bits": r,
        "v_bits": s,
        "edges": edge_list,
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = int(inst["n"])
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    upper: list[list[int]] = [[] for _ in range(n)]
    for x, y in inst["edges"]:
        upper[x].append(y)
    edge_rows = "\n".join(
        f"{x}: " + " ".join(str(y) for y in upper[x])
        for x in range(n)
    )
    text = f"""Find a graph derangement of the following finite graph.

A graph derangement is a bijection f from the vertex set to itself such that
f(x) != x and {{x,f(x)}} is an edge for every vertex x.  The graph is simple,
undirected, and connected.  Its vertices are the integers 0 through {n - 1}.

There are {r} high (u) bits and {s} low (v) bits.  Thus vertex x represents
(u,v) with u=x >> {s} and v=x mod {1 << s}.  XOR means bitwise exclusive-or.

The complete edge list is below in upper-triangular adjacency form.  A row
"x: y ..." lists exactly those neighbors y>x; an empty row has no such
neighbors.  Every undirected edge appears once and there are no other edges.

{edge_rows}

You may give either of two exact witness encodings.

1. Compact affine-XOR form:
   {{"kind":"affine_xor","a":A,"rows":[R0,...,R{s - 1}],"d":D}}
   Here 1 <= A < {1 << r}, there are exactly {s} row masks, every Ri is in
   [0,{(1 << r) - 1}], and D is in [0,{(1 << s) - 1}].  It denotes
   f(u,v)=(u XOR A, v XOR L(u) XOR D), where bit j of L(u) is the parity
   (0 for even, 1 for odd) of the 1-bits in (Rj AND u); j=0 is the least
   significant bit.

2. Explicit table form:
   {{"kind":"table","image":[f(0),f(1),...,f({n - 1})]}}
   The image list must have exactly {n} integers.  It must be a permutation of
   0..{n - 1}; order is by source vertex, and repeats are forbidden.

All numbers are decimal JSON integers.  Either encoding is expanded and
checked exactly against the displayed graph.

Give your final answer inside <answer></answer> tags as one JSON object in
exactly one of the two formats above.
Example shape: <answer>{{"kind":"affine_xor","a":1,"rows":[{','.join('0' for _ in range(s))}],"d":0}}</answer>
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
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def _edge_set(inst: dict) -> set[tuple[int, int]]:
    return {(int(x), int(y)) for x, y in inst["edges"]}


def _expand_answer(inst: dict, answer: object) -> tuple[list[int] | None, str]:
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    kind = answer.get("kind")
    n = int(inst["n"])
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    if kind == "table":
        image = answer.get("image")
        if not isinstance(image, list):
            return None, "table image must be a JSON list"
        if len(image) != n:
            return None, f"table length must be exactly {n}"
        if any(isinstance(v, bool) or not isinstance(v, int) for v in image):
            return None, "table entries must be integers"
        if any(v < 0 or v >= n for v in image):
            return None, f"table entry outside 0..{n - 1}"
        if len(set(image)) != n:
            return None, "table is not injective (a value is repeated)"
        return list(image), "ok"
    if kind != "affine_xor":
        return None, "kind must be 'affine_xor' or 'table'"
    a, rows, d = answer.get("a"), answer.get("rows"), answer.get("d")
    if isinstance(a, bool) or not isinstance(a, int):
        return None, "affine a must be an integer"
    if a <= 0 or a >= (1 << r):
        return None, f"affine a must be nonzero and below {1 << r}"
    if not isinstance(rows, list) or len(rows) != s:
        return None, f"affine rows must contain exactly {s} masks"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in rows):
        return None, "affine row masks must be integers"
    if any(v < 0 or v >= (1 << r) for v in rows):
        return None, f"affine row mask outside 0..{(1 << r) - 1}"
    if isinstance(d, bool) or not isinstance(d, int):
        return None, "affine d must be an integer"
    if d < 0 or d >= (1 << s):
        return None, f"affine d outside 0..{(1 << s) - 1}"
    return [_affine_image(x, r, s, a, rows, d) for x in range(n)], "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any explicit or affine graph derangement; never read the plant."""
    try:
        image, reason = _expand_answer(inst, answer)
        if image is None:
            return False, reason
        n = int(inst["n"])
        if len(set(image)) != n:
            return False, "expanded function is not injective"
        fixed = next((x for x, y in enumerate(image) if x == y), None)
        if fixed is not None:
            return False, f"fixed point at vertex {fixed}"
        edges = _edge_set(inst)
        for x, y in enumerate(image):
            edge = (x, y) if x < y else (y, x)
            if edge not in edges:
                return False, f"nonedge used by vertex {x}: {y}"
        return True, "ok"
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance or answer: {exc}"


def _derangement_count(n: int) -> int:
    d0, d1 = 1, 0
    if n == 0:
        return d0
    if n == 1:
        return d1
    for k in range(2, n + 1):
        d0, d1 = d1, (k - 1) * (d1 + d0)
    return d1


def _affine_language_size(inst: dict) -> int:
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    return ((1 << r) - 1) * (1 << (s * r + s))


def search_space(inst: dict) -> int:
    return _derangement_count(int(inst["n"])) + _affine_language_size(inst)


def _uniform_derangement(n: int, rng: random.Random) -> list[int]:
    # Rejection from uniform permutations is exactly uniform on derangements;
    # acceptance tends to 1/e, so this has constant expected repetitions.
    while True:
        image = list(range(n))
        rng.shuffle(image)
        if all(x != y for x, y in enumerate(image)):
            return image


def random_candidate(inst: dict, rng: random.Random) -> object:
    n = int(inst["n"])
    affine_size = _affine_language_size(inst)
    table_size = _derangement_count(n)
    choice = rng.randrange(affine_size + table_size)
    if choice < affine_size:
        r, s = int(inst["u_bits"]), int(inst["v_bits"])
        return {
            "kind": "affine_xor",
            "a": rng.randrange(1, 1 << r),
            "rows": [rng.randrange(1 << r) for _ in range(s)],
            "d": rng.randrange(1 << s),
        }
    return {"kind": "table", "image": _uniform_derangement(n, rng)}


def enumerate_all(inst: dict) -> int | None:
    n = int(inst["n"])
    if math.factorial(n) + _affine_language_size(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    for perm in itertools.permutations(range(n)):
        if all(i != perm[i] for i in range(n)):
            count += int(verify(inst, {"kind": "table", "image": list(perm)})[0])
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    for a in range(1, 1 << r):
        for rows in itertools.product(range(1 << r), repeat=s):
            for d in range(1 << s):
                candidate = {"kind": "affine_xor", "a": a,
                             "rows": list(rows), "d": d}
                count += int(verify(inst, candidate)[0])
    return count


def _adjacency(inst: dict) -> list[list[int]]:
    adj = [[] for _ in range(int(inst["n"]))]
    for x, y in inst["edges"]:
        adj[x].append(y)
        adj[y].append(x)
    for row in adj:
        row.sort()
    return adj


def canonical_key(inst: dict) -> str:
    """A relabelling-invariant 1-WL canonical fingerprint of the abstract graph."""
    adj = _adjacency(inst)
    n = len(adj)
    colors = [len(row) for row in adj]
    for _ in range(8):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adj[v])))
            for v in range(n)
        ]
        unique = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_colors = [unique[sig] for sig in signatures]
        old_partition = sorted(Counter(colors).values())
        new_partition = sorted(Counter(new_colors).values())
        colors = new_colors
        if old_partition == new_partition and len(set(colors)) == n:
            break
    classes = sorted(Counter(colors).values())
    edge_colors = sorted(
        (min(colors[x], colors[y]), max(colors[x], colors[y]))
        for x, y in inst["edges"]
    )
    payload = json.dumps([n, classes, edge_colors], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    harder = {k: v for k, v in params.items() if k != "_preset"}
    current = int(harder.get("near_rules", 1))
    if current < 74:
        harder["near_rules"] = min(74, current + 8)
        return harder
    if current < 106:
        harder["near_rules"] = min(106, current + 16)
        return harder
    if int(harder.get("n", 0)) < 256:
        harder["n"] = 2 * int(harder["n"])
        bits = int(harder["n"]).bit_length() - 1
        harder["u_bits"] = bits // 2
        return harder
    return "cap_bound"


def _hopcroft_karp(inst: dict) -> tuple[dict | None, dict[str, int]]:
    adj = _adjacency(inst)
    n = len(adj)
    pair_u = [-1] * n
    pair_v = [-1] * n
    dist = [0] * n
    counts = {"edge_scans": 0, "bfs_phases": 0, "dfs_calls": 0,
              "queue_pops": 0, "augmentations": 0}

    def bfs() -> bool:
        queue: deque[int] = deque()
        found = False
        counts["bfs_phases"] += 1
        for u in range(n):
            if pair_u[u] < 0:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = -1
        while queue:
            u = queue.popleft()
            counts["queue_pops"] += 1
            for v in adj[u]:
                counts["edge_scans"] += 1
                mate = pair_v[v]
                if mate < 0:
                    found = True
                elif dist[mate] < 0:
                    dist[mate] = dist[u] + 1
                    queue.append(mate)
        return found

    def dfs(u: int) -> bool:
        counts["dfs_calls"] += 1
        for v in adj[u]:
            counts["edge_scans"] += 1
            mate = pair_v[v]
            if mate < 0 or (dist[mate] == dist[u] + 1 and dfs(mate)):
                pair_u[u] = v
                pair_v[v] = u
                return True
        dist[u] = -1
        return False

    while bfs():
        progressed = 0
        for u in range(n):
            if pair_u[u] < 0 and dfs(u):
                counts["augmentations"] += 1
                progressed += 1
        if not progressed:
            break
    if any(v < 0 for v in pair_u):
        return None, counts
    return {"kind": "table", "image": pair_u}, counts


def _fast_valid(inst: dict, candidate: object,
                edges: set[tuple[int, int]] | None = None) -> bool:
    image, _ = _expand_answer(inst, candidate)
    if image is None or len(set(image)) != int(inst["n"]):
        return False
    if any(x == y for x, y in enumerate(image)):
        return False
    if edges is None:
        edges = _edge_set(inst)
    return all(((x, y) if x < y else (y, x)) in edges
               for x, y in enumerate(image))


def _modal_affine_attack(inst: dict) -> dict:
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    mask = (1 << s) - 1
    by_a: Counter[int] = Counter()
    for x, y in inst["edges"]:
        a = (x >> s) ^ (y >> s)
        if a:
            by_a[a] += 1
    a = min(((-count, value) for value, count in by_a.items()))[1]

    def modal_delta(u: int) -> int:
        counts: Counter[int] = Counter()
        for x, y in inst["edges"]:
            xu, yu = x >> s, y >> s
            if xu == u and yu == (u ^ a):
                counts[(x & mask) ^ (y & mask)] += 1
            elif yu == u and xu == (u ^ a):
                counts[(x & mask) ^ (y & mask)] += 1
        if not counts:
            return 0
        return min(((-count, value) for value, count in counts.items()))[1]

    d = modal_delta(0)
    columns = [modal_delta(1 << bit) ^ d for bit in range(r)]
    rows = [
        sum(((columns[bit] >> out_bit) & 1) << bit for bit in range(r))
        for out_bit in range(s)
    ]
    return {"kind": "affine_xor", "a": a, "rows": rows, "d": d}


def _xor_outlier_attack(inst: dict) -> dict:
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    counts: Counter[tuple[int, int]] = Counter()
    mask = (1 << s) - 1
    for x, y in inst["edges"]:
        counts[((x >> s) ^ (y >> s), (x & mask) ^ (y & mask))] += 1
    (_, (a, d)) = min((-count, key) for key, count in counts.items())
    return {"kind": "affine_xor", "a": a,
            "rows": [0] * s, "d": d}


def _example_copy_attack(inst: dict) -> dict:
    return {"kind": "affine_xor", "a": 1,
            "rows": [0] * int(inst["v_bits"]), "d": 0}


def _greedy_table_attack(inst: dict) -> dict:
    adj = _adjacency(inst)
    used: set[int] = set()
    image: list[int] = []
    for x, row in enumerate(adj):
        available = [y for y in row if y not in used and y != x]
        if available:
            y = min(available, key=lambda z: (len(adj[z]), z))
        else:
            y = 0
        image.append(y)
        used.add(y)
    return {"kind": "table", "image": image}


def _basis_first_attack(inst: dict) -> dict:
    adj = _adjacency(inst)
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    mask = (1 << s) - 1
    origin_neighbor = adj[0][0]
    a, d = origin_neighbor >> s, origin_neighbor & mask
    if a == 0:
        a = 1
    columns: list[int] = []
    for bit in range(r):
        x = (1 << bit) << s
        candidates = [y for y in adj[x] if (y >> s) == ((1 << bit) ^ a)]
        y = candidates[0] if candidates else adj[x][0]
        columns.append((y & mask) ^ d)
    rows = [
        sum(((columns[bit] >> out_bit) & 1) << bit for bit in range(r))
        for out_bit in range(s)
    ]
    return {"kind": "affine_xor", "a": a, "rows": rows, "d": d}


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 512) -> object:
    edges = _edge_set(inst)
    last: object = {"kind": "table", "image": list(range(int(inst["n"])))}
    for _ in range(restarts):
        # Uniform explicit derangements are the overwhelmingly dominant branch
        # of the declared certificate language at shipping size.
        last = {"kind": "table",
                "image": _uniform_derangement(int(inst["n"]), rng)}
        if _fast_valid(inst, last, edges):
            return last
    return last


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def _intended_operation_bound(inst: dict) -> int:
    r, s = int(inst["u_bits"]), int(inst["v_bits"])
    # Once the persistent XOR displacement has been recognized: read the
    # origin and r basis displacements, unpack s*r parity bits, and validate on
    # two independent block representatives.  Bitwise operations count as one.
    return 12 * (r + 1) + 6 * r * s + 4 * s


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, dict]:
    n = int(inst["n"])
    old_to_new = list(range(n))
    rng.shuffle(old_to_new)
    edges = []
    for x, y in inst["edges"]:
        a, b = old_to_new[x], old_to_new[y]
        edges.append([a, b] if a < b else [b, a])
    changed = dict(inst)
    changed["edges"] = sorted(edges)
    original_image, reason = _expand_answer(inst, inst["answer"])
    if original_image is None:
        raise AssertionError(reason)
    carried = [0] * n
    for old_x, old_y in enumerate(original_image):
        carried[old_to_new[old_x]] = old_to_new[old_y]
    return changed, {"kind": "table", "image": carried}


def selftest() -> dict:
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    failures: list[str] = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    table, reason = _expand_answer(ship, ship["answer"])
    if table is None:
        raise AssertionError(reason)
    drop = {"kind": "table", "image": table[:-1]}
    swapped = list(table)
    partner = table[0]
    swapped[0], swapped[partner] = swapped[partner], swapped[0]
    duplicate = list(table)
    duplicate[0] = duplicate[1]
    out_of_range = list(table)
    out_of_range[0] = int(ship["n"])
    corruptions = {
        "drop_one": drop,
        "swap_one": {"kind": "table", "image": swapped},
        "duplicate_one": {"kind": "table", "image": duplicate},
        "empty": {},
        "out_of_range": {"kind": "table", "image": out_of_range},
    }
    cases: dict[str, Any] = {}
    reasons: list[str] = []
    for name, candidate in corruptions.items():
        ok, rejection = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": rejection}
        reasons.append(rejection)
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    blob = json.dumps(ship["answer"], separators=(",", ":"))
    model_reply = (
        "The XOR rule expands to a fixed-point-free permutation.\n"
        "```json\n<answer>" + blob + "</answer>\n```\n"
        "I checked every required edge."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"]
        and parse_answer("there is no tagged witness") is None,
        "parsed": parsed,
    }

    samples = 200_000
    sample_rng = random.Random(8_675_309)
    ship_edges = _edge_set(ship)
    hits = 0
    for _ in range(samples):
        hits += int(_fast_valid(ship, random_candidate(ship, sample_rng), ship_edges))
    observed = hits / samples
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": observed,
        "candidate_space": search_space(ship),
        "sampler": (
            "uniform over the disjoint table/affine encoding language; table "
            "candidates are uniform fixed-point-free permutations"
        ),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_names = [
        "copy_format_example",
        "outlier_constant_xor",
        "greedy_low_degree_neighbor",
        "by_hand_first_basis_ansatz",
        "modal_affine_displacement",
        "random_restart_512",
    ]
    attack_stats = {name: {"successes": 0, "attempts": 8}
                    for name in attack_names}
    reference_successes = 0
    reference_times: list[float] = []
    reference_counts: list[dict[str, int]] = []
    for seed in range(8):
        inst = make_instance(seed=12_000 + seed, **ship_params)
        candidates = {
            "copy_format_example": _example_copy_attack(inst),
            "outlier_constant_xor": _xor_outlier_attack(inst),
            "greedy_low_degree_neighbor": _greedy_table_attack(inst),
            "by_hand_first_basis_ansatz": _basis_first_attack(inst),
            "modal_affine_displacement": _modal_affine_attack(inst),
            "random_restart_512": _random_restart_attack(
                inst, random.Random(700_000 + seed)),
        }
        for name, candidate in candidates.items():
            attack_stats[name]["successes"] += int(verify(inst, candidate)[0])
        started = time.perf_counter()
        reference_answer, counts = _hopcroft_karp(inst)
        reference_times.append(time.perf_counter() - started)
        reference_counts.append(counts)
        reference_successes += int(
            reference_answer is not None and verify(inst, reference_answer)[0]
        )

    def mean_count(key: str) -> float:
        return sum(row[key] for row in reference_counts) / len(reference_counts)

    reference = {
        "name": "Hopcroft-Karp on the bipartite double cover",
        "paper_basis": (
            "Introduction: graph derangements are equivalent to Q-factors and "
            "the Hall-type neighborhood condition"
        ),
        "complexity": "O(E sqrt(V))",
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "edge_scans_mean": mean_count("edge_scans"),
        "edge_scans_max": max(row["edge_scans"] for row in reference_counts),
        "bfs_phases_mean": mean_count("bfs_phases"),
        "dfs_calls_mean": mean_count("dfs_calls"),
        "queue_pops_mean": mean_count("queue_pops"),
        "augmentations_mean": mean_count("augmentations"),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attack_stats.values())
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6 and demo_count is not None
        and demo_count >= 1 and reference_successes == 8,
        "shipping_density_hits": hits,
        "shipping_density_total": samples,
        "shipping_observed_fraction": observed,
        "shipping_candidate_space": search_space(ship),
        "demo_valid_certificate_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_sec_max": reference["wall_clock_sec_max"],
        "baseline_edge_scans_mean": reference["edge_scans_mean"],
        "baseline_edge_scans_max": reference["edge_scans_max"],
        "baseline_bfs_phases_mean": reference["bfs_phases_mean"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_stats,
        "reference_algorithm": reference,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    total_bits = int(doubled_params["n"]).bit_length() - 1
    doubled_params["u_bits"] = total_bits // 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(ship)
        and _atom_count(doubled["answer"]) <= 256,
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_space": search_space(ship),
        "doubled_space": search_space(doubled),
        "shipping_answer_elements": _atom_count(ship["answer"]),
        "doubled_answer_elements": _atom_count(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariant = 0
    real = 0
    reordered_count = 0
    keys: list[str] = []
    g8_failures: list[str] = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(inst)
        keys.append(key)
        changed, carried = _relabel_instance(inst, random.Random(30_000 + seed))
        if canonical_key(changed) == key:
            invariant += 1
        else:
            g8_failures.append(f"vertex relabelling changed key at seed {seed}")
        if verify(changed, carried)[0]:
            real += 1
        else:
            g8_failures.append(f"carried witness failed at seed {seed}")
        reordered = dict(changed)
        reordered["edges"] = list(reversed(changed["edges"]))
        if canonical_key(reordered) == key and verify(reordered, carried)[0]:
            reordered_count += 1
        else:
            g8_failures.append(f"edge reordering failed at seed {seed}")
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariant == 20 and real == 20
        and reordered_count == 20 and distinct == 20,
        "invariance_checks": invariant,
        "real_transformation_checks": real,
        "composed_reordering_checks": reordered_count,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary vertex renumbering with carried explicit permutation",
            "edge-list reordering composed with vertex renumbering",
        ],
        "failures": g8_failures,
    }

    answer_blobs = [
        json.dumps(make_instance(seed=seed, **ship_params)["answer"],
                   separators=(",", ":"))
        for seed in range(32)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = max(
        _atom_count(make_instance(seed=seed, **ship_params)["answer"])
        for seed in range(32)
    )
    intended_ops = _intended_operation_bound(ship)
    arms = {
        name: {"solved": int(G9_MEASUREMENTS[name]["solved"]),
               "attempts": int(G9_MEASUREMENTS[name]["attempts"])}
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_names = [name for name in report if name.startswith("G")]
    report["all_passed"] = all(bool(report[name].get("pass"))
                                  for name in gate_names)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
