"""Rejected Track-B stable HR-LQ prototype for arXiv:2009.14171.

Theorem 2 of Boehmer--Heeger reduces regular Multicolored Independent Set
to Hospital Residents with lower quotas (HR-LQ).  This module inverse-generates
a regular prime-field graph together with an independent transversal, then
carries that transversal through the theorem's explicit matching map.

The generated distribution has a polynomial affine decoder.  Re-audit showed
that this decoder is also the obvious in-context ansatz because the renderer
displays every excluded value and coefficient.  The prototype is retained for
audit, but its G6 panel now records that attack succeeding and REJECTED.md
explains why the family clears G and V but fails H on both tracks.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import time
from collections import Counter, deque


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "HR-LQ residents, hospitals, lower quotas, and strict preferences",
        "regular multicolored graph encoded by prime-field predicates",
        "stable matching represented by its open vertex hospital in each color",
    ],
    "verification_operations": [
        "exact arithmetic in GF(p)",
        "Euler-criterion quadratic-residue test",
        "exact blocking-coalition check",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.2, Theorem 2: parameterized reduction from regular "
        "Multicolored Independent Set to HR-LQ"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The uniquely excluded pair in every color-pair predicate is governed "
        "by one affine consistency component; without recognizing it, the "
        "solver faces a dense multicolored binary CSP."
    ),
    "hardness_basis": (
        "Rejected Track B candidate: on the succinct input, ordinary modular "
        "elimination is the same 241-operation affine route as the proposed "
        "shortcut, and the obvious in-context ansatz succeeds on 8/8 hard "
        "instances; Theorem 2 gives only generic worst-case W[1]-hardness."
    ),
    "max_answer_tokens": 118,
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
    "demo": {"n": 3, "prime": 7},
    "easy": {"n": 16, "prime": 29},
    "medium": {"n": 32, "prime": 59},
    "hard": {"n": 60, "prime": 101},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "The uniquely excluded pairs across all color relations belong to one "
    "shared affine-consistency component."
)
PLACEBO_HINT: str = (
    "The prime-field calculations across all color relations require careful "
    "attention to signs and residues."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A canonical JSON list [[0,x_0],...,[n-1,x_{n-1}]] containing exactly "
        "one vertex label x_c in {0,...,p-1} for every color c; it denotes the "
        "fully specified HR-LQ matching in the statement."
    ),
    "bounds": {
        "pairs": "exactly n",
        "color_range": "0 through n-1, once each, in order",
        "vertex_range": "0 through p-1",
        "candidate_count": "p^n",
    },
}

# Filled from script-owned oracle runs after hardening.  The three arms are a
# diagnostic, not a gate; G9 passes exactly when the answer and intended route
# fit the no-tool caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}
G9_ORACLE_STATUS = (
    "blocked before any scored attempt: bare, structural-hint, and placebo "
    "harden.py runs all received OpenRouter HTTP 403 key-limit errors"
)

NOTES = r"""
Definition. Section 2 defines an HR-LQ matching as feasible when every hospital
is closed or meets its lower quota. An open hospital and resident form a
blocking pair when the resident prefers it and it has room; a closed hospital
has a blocking coalition when l(h) residents all prefer it to their current
assignments. Observation 1 is essential here: if exactly l(h) residents accept
every hospital, a feasible matching cannot have a blocking pair.

Construction and certificate. Section 3.2, Theorem 2 reduces a regular
Multicolored Independent Set instance with k equal color classes to HR-LQ. It
creates five residents per color, quota-three vertex hospitals, quota-four edge
hospitals, and a three-hospital penalizing component. Its forward proof maps an
independent transversal x_c to the stable matching opening V(c,x_c) for the
three residents A_c,B_c,S_c and opening P(c,3) for T_c,U_c. This module samples
that transversal first. For every color pair it samples a regular prime-field
relation around the transversal, so no instance is solved during generation.

Step-0 algorithm re-audit. A Track-A claim is false for this distribution.
In each color-pair relation, the equation a*x+b*y+g=e identifies one excluded
perfect matching. Those marked pairs form a graph on n*p vertices. The planted
vertices are an isolated n-clique/component. More decisively, the statement
itself displays every excluded value and affine coefficient. Composing the
marked affine maps around colors 0,1,2 and propagating along the color-0 row is
therefore both the input-native mechanical algorithm and the obvious no-tool
ansatz. Both cost 241 field operations at hard; the earlier 715,000-visit
component scan first expanded the succinct input and was not an honest
baseline. This collapses Track B as well.

Easy regimes avoided. Theorem 4 gives an O(N^3*m) algorithm when every lower
quota is at most two, so the construction keeps the theorem's quota-three and
quota-four hospitals. Observation 3 solves HR-LQ in O(N*m) once the open set is
given, and Corollary 1 gives O(N*m*2^m_quota), confirming that selecting the open
vertex hospitals is the only hard part. The number of colors grows across the
ladder; it is not held as a small FPT parameter.

Attack handling. Every vertex has exactly (n-1)(p-3)/2 ordinary incident edges,
so degree and magnitude outliers carry no signal. Vertex labels and coefficients
are sampled symmetrically. Left-to-right greedy choices die after a few dense
constraints, uniform restarts sample the true p^n certificate language, and the
zero-anchor guess uses the wrong affine fixed point. However, the stronger and
obvious ansatz that solves the three displayed excluded equations succeeds on
every seed. G6 records that success, which is the local hardness failure.

Canonicalization. The key uses cycle types of all marked-map triangles and all
simple marked-map four-cycles. Cycle type is unchanged by arbitrary relabeling
inside a color, color permutation, input reordering, and compositions of those
maps. It is a strong polynomial invariant rather than a complete isomorphism
test; general colored-graph isomorphism is not attempted.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_prime(p: int) -> bool:
    if not isinstance(p, int) or isinstance(p, bool) or p < 2:
        return False
    if p % 2 == 0:
        return p == 2
    d = 3
    while d * d <= p:
        if p % d == 0:
            return False
        d += 2
    return True


def _next_prime(x: int) -> int:
    q = max(3, int(x) | 1)
    while not _is_prime(q):
        q += 2
    return q


def _legendre(x: int, p: int) -> int:
    """Return -1, 0, or 1 for x modulo the odd prime p."""
    x %= p
    if x == 0:
        return 0
    value = pow(x, (p - 1) // 2, p)
    return -1 if value == p - 1 else 1


def _inv(x: int, p: int) -> int:
    return pow(x % p, p - 2, p)


def _pair_key(c: int, d: int) -> str:
    return f"{c},{d}"


def _relations(inst: dict) -> dict[tuple[int, int], tuple[int, int, int, int]]:
    return {
        (row[0], row[1]): (row[2], row[3], row[4], row[5])
        for row in inst.get("relations", [])
    }


def _relation_at(inst: dict, c: int, d: int) -> tuple[int, int, int, int]:
    """O(1) lookup in the lexicographically stored upper triangle."""
    n = inst["n"]
    index = c * (2 * n - c - 1) // 2 + (d - c - 1)
    row = inst["relations"][index]
    if row[0] != c or row[1] != d:
        # A table-row reordering is a presentation symmetry. Normal generated
        # instances take the O(1) path; relabeled audit instances may take this
        # bounded fallback without making table order semantically meaningful.
        row = next(r for r in inst["relations"] if r[0] == c and r[1] == d)
    return row[2], row[3], row[4], row[5]


def _edge(inst: dict, c: int, x: int, d: int, y: int) -> bool:
    """Whether the two vertices define an edge hospital."""
    if c == d:
        return False
    if c > d:
        c, d, x, y = d, c, y, x
    explicit = inst.get("explicit_rows")
    if explicit is not None:
        return bool((explicit[_pair_key(c, d)][x] >> y) & 1)
    a, b, g, excluded = _relation_at(inst, c, d)
    value = (a * x + b * y + g) % inst["prime"]
    return value != excluded and _legendre(value, inst["prime"]) == 1


def _marked_forward(inst: dict) -> dict[tuple[int, int], list[int]]:
    """The unique excluded-residue perfect matching for every c<d."""
    if "marked_maps" in inst:
        return {
            tuple(map(int, key.split(","))): list(values)
            for key, values in inst["marked_maps"].items()
        }
    p = inst["prime"]
    result = {}
    for (c, d), (a, b, g, excluded) in _relations(inst).items():
        ib = _inv(b, p)
        result[c, d] = [((excluded - g - a * x) * ib) % p for x in range(p)]
    return result


def _all_marked_maps(inst: dict) -> dict[tuple[int, int], list[int]]:
    p = inst["prime"]
    forward = _marked_forward(inst)
    result = dict(forward)
    for (c, d), mapping in forward.items():
        inverse = [0] * p
        for x, y in enumerate(mapping):
            inverse[y] = x
        result[d, c] = inverse
    return result


def _decoder_nondegenerate(rel: dict, p: int) -> bool:
    """Whether the 0-1-2 marked triangle has one affine fixed point."""
    a01, b01, g01, e01 = rel[0, 1]
    a02, b02, g02, e02 = rel[0, 2]
    a12, b12, _g12, _e12 = rel[1, 2]
    slope1 = (-a01 * _inv(b01, p)) % p
    slope2 = (-a02 * _inv(b02, p)) % p
    return (a12 * slope1 + b12 * slope2) % p != 0


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a regular Theorem-2 HR-LQ instance and certificate."""
    p = params.pop("prime", None)
    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if not _is_prime(p) or p < 7 or p % 2 == 0:
        raise ValueError("prime must be an odd prime at least 7")

    rng = random.Random(seed)
    secret = [rng.randrange(p) for _ in range(n)]
    residues = [z for z in range(1, p) if _legendre(z, p) == 1]
    rel: dict[tuple[int, int], tuple[int, int, int, int]] = {}

    # The marked equation a*x_c+b*x_d+g=e is built around the sampled secret.
    # Excluding the residue e removes one perfect matching from an otherwise
    # Paley-type regular bipartite graph, leaving degree (p-3)/2 on both sides.
    for c in range(n):
        for d in range(c + 1, n):
            while True:
                a = rng.randrange(1, p)
                b = rng.randrange(1, p)
                excluded = rng.choice(residues)
                g = (excluded - a * secret[c] - b * secret[d]) % p
                rel[c, d] = (a, b, g, excluded)
                if (c, d) != (1, 2) or _decoder_nondegenerate(rel, p):
                    break

    relations = [
        [c, d, *rel[c, d]]
        for c in range(n) for d in range(c + 1, n)
    ]
    answer = [[c, secret[c]] for c in range(n)]
    pair_count = n * (n - 1) // 2
    return {
        "family": "HR-LQ stable matching from Theorem 2",
        "n": n,
        "prime": p,
        "relations": relations,
        "resident_count": 5 * n,
        "vertex_hospital_count": n * p,
        "edge_hospital_count": pair_count * p * (p - 3) // 2,
        "penalizing_hospital_count": 3 * n,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete compact definition of the HR-LQ instance."""
    n = inst["n"]
    p = inst["prime"]
    rows = "\n".join(" ".join(map(str, row)) for row in inst["relations"])
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nStructural hint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""Find a stable matching in the following Hospital Residents instance
with lower quotas (HR-LQ). Everything needed to define the instance is below.

Arithmetic and graph. Work in the field GF({p}), represented by integers
0,...,{p - 1}; all displayed affine arithmetic is reduced modulo {p}. There are
{n} colors numbered 0,...,{n - 1}, and color c has vertices v(c,x) for
x=0,...,{p - 1}. For every pair c<d, its table row is

    c d a b g e

Vertices v(c,x) and v(d,y) are adjacent exactly when z=(a*x+b*y+g) mod {p}
is a nonzero quadratic residue modulo {p} AND z is not equal to e. A nonzero z
is a quadratic residue when z^(({p}-1)/2) mod {p} equals 1. The complete table is:

{rows}

This defines a regular multicolored graph: every vertex has exactly
({n}-1)*({p}-3)/2 incident edges, and there are no same-color edges.

HR-LQ instance. A hospital is either closed (assigned nobody) or open with at
least its stated lower quota. Every upper quota is {5 * n + 1}, larger than the
number of residents. An open hospital and acceptable resident block a matching
if the resident prefers it to their assignment. A closed hospital h has a
blocking coalition if at least l(h) acceptable residents all prefer h to their
assignments. A feasible matching is stable when it has neither kind of block.

For every color c and label x there is a vertex hospital V(c,x), lower quota 3.
For every graph edge {{v(c,x),v(d,y)}} there is an edge hospital E(c,x,d,y),
written with c<d, lower quota 4. For every color c there are P(c,1), P(c,2),
P(c,3), each with lower quota 2.

Each color c has residents A(c), B(c), S(c), T(c), U(c). Preferences are strict:

* A(c): process x=0,1,...,{p - 1}. For each x, first list every incident edge
  hospital E containing v(c,x), ordered lexicographically by its four indices,
  and then V(c,x).
* B(c): the same blocks and within-block order, but process
  x={p - 1},{p - 2},...,0.
* S(c): V(c,0) > V(c,1) > ... > V(c,{p - 1}) > P(c,1) > P(c,2).
* T(c): P(c,2) > P(c,3).
* U(c): P(c,3) > P(c,1).

Only the residents just listed accept each hospital. Thus V(c,x) is accepted by
A(c),B(c),S(c); an edge hospital is accepted by A and B at each endpoint; and
P(c,1),P(c,2),P(c,3) are accepted respectively by {{S(c),U(c)}},
{{S(c),T(c)}},{{T(c),U(c)}}. Hospital-side rankings are immaterial here because
exactly l(h) residents accept h.

Certificate format. Return exactly one pair [c,x_c] for every color, in color
order. It denotes the full matching that assigns A(c), B(c), and S(c) to
V(c,x_c), and assigns T(c), U(c) to P(c,3). All other hospitals are closed.
Different colors may use the same numeric label; labels are local to a color.
The checker accepts any such induced stable matching, not only a planted one.
{hint}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{n} pairs [[0,x_0],[1,x_1],..., [{n - 1},x_{n - 1}]], with every x_c an integer
from 0 through {p - 1}. For a hypothetical three-color instance, the syntax is
<answer>[[0,0],[1,1],[2,2]]</answer>.
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Parse the delimited JSON certificate, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check the induced matching by the exact Theorem-2 blocking criterion."""
    n = inst["n"]
    p = inst["prime"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must be a nonempty JSON list"
    if len(answer) != n:
        return False, f"expected exactly {n} color-vertex pairs"

    colors = []
    labels = []
    for pair in answer:
        if not isinstance(pair, list) or len(pair) != 2:
            return False, "each entry must be a two-element [color,vertex] list"
        c, x = pair
        if (not isinstance(c, int) or isinstance(c, bool)
                or not isinstance(x, int) or isinstance(x, bool)):
            return False, "color and vertex labels must be integers"
        if not 0 <= c < n:
            return False, "color index outside the allowed range"
        if not 0 <= x < p:
            return False, "vertex label outside the allowed field range"
        colors.append(c)
        labels.append(x)
    if len(set(colors)) != n:
        return False, "each color must occur exactly once"
    if colors != list(range(n)):
        return False, "pairs must be ordered by color 0 through n-1"

    # The displayed tuple induces exactly the matching in Theorem 2. Vertex and
    # penalty hospitals meet quota. Observation 1 rules out blocking pairs.
    # The proof shows that the only possible remaining block is the quota-four
    # edge hospital joining two selected vertices.
    for c in range(n):
        for d in range(c + 1, n):
            if _edge(inst, c, labels[c], d, labels[d]):
                return False, (
                    "blocking edge-hospital coalition at colors "
                    f"{c},{d} with labels {labels[c]},{labels[d]}"
                )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-aware space: one label per color."""
    return [[c, rng.randrange(inst["prime"])] for c in range(inst["n"])]


def search_space(inst: dict) -> int:
    return inst["prime"] ** inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Count valid certificates exactly when at most 200,000 need checking."""
    if search_space(inst) > 200_000:
        return None
    count = 0
    n, p = inst["n"], inst["prime"]
    for values in itertools.product(range(p), repeat=n):
        candidate = [[c, values[c]] for c in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def _permutation_cycle_type(perm: list[int]) -> tuple[int, ...]:
    seen = [False] * len(perm)
    lengths = []
    for start in range(len(perm)):
        if seen[start]:
            continue
        cur = start
        length = 0
        while not seen[cur]:
            seen[cur] = True
            length += 1
            cur = perm[cur]
        lengths.append(length)
    return tuple(sorted(lengths))


def _multiplicative_order(a: int, p: int) -> int:
    if a % p == 1:
        return 1
    value = a % p
    order = 1
    while value != 1:
        value = value * a % p
        order += 1
    return order


def _affine_cycle_type_from_slope(slope: int, p: int) -> tuple[int, ...]:
    order = _multiplicative_order(slope, p)
    if order == 1:
        return (1,) * p
    return (1,) + (order,) * ((p - 1) // order)


def _cycle_histograms(inst: dict) -> tuple[Counter, Counter]:
    """Relabel-invariant cycle types for all marked 3- and 4-color cycles."""
    n, p = inst["n"], inst["prime"]
    triangles: Counter = Counter()
    fours: Counter = Counter()
    if "relations" in inst and inst.get("relations"):
        slopes = {}
        cycle_types = {
            slope: _affine_cycle_type_from_slope(slope, p)
            for slope in range(1, p)
        }
        for (c, d), (a, b, _g, _e) in _relations(inst).items():
            s = (-a * _inv(b, p)) % p
            slopes[c, d] = s
            slopes[d, c] = _inv(s, p)

        def add_cycle(seq: tuple[int, ...], target: Counter) -> None:
            slope = 1
            for i, c in enumerate(seq):
                slope = slope * slopes[c, seq[(i + 1) % len(seq)]] % p
            target[cycle_types[slope]] += 1
    else:
        maps = _all_marked_maps(inst)

        def add_cycle(seq: tuple[int, ...], target: Counter) -> None:
            perm = list(range(p))
            for i, c in enumerate(seq):
                mapping = maps[c, seq[(i + 1) % len(seq)]]
                perm = [mapping[x] for x in perm]
            target[_permutation_cycle_type(perm)] += 1

    for c in range(n):
        for d in range(c + 1, n):
            for e in range(d + 1, n):
                add_cycle((c, d, e), triangles)
    for a in range(n):
        for b in range(a + 1, n):
            for c in range(b + 1, n):
                for d in range(c + 1, n):
                    add_cycle((a, b, c, d), fours)
                    add_cycle((a, b, d, c), fours)
                    add_cycle((a, c, b, d), fours)
    return triangles, fours


def canonical_key(inst: dict) -> str:
    """Strong cycle-type invariant of the marked prime-field presentation."""
    triangles, fours = _cycle_histograms(inst)

    def encode(counter: Counter) -> list:
        return sorted([[list(kind), count] for kind, count in counter.items()])

    payload = {
        "n": inst["n"],
        "prime": inst["prime"],
        "marked_triangle_cycle_types": encode(triangles),
        "marked_four_cycle_types": encode(fours),
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the field/haystack while keeping the n-pair answer length fixed."""
    harder = {k: v for k, v in params.items() if k != "_preset"}
    current = harder["prime"]
    harder["prime"] = _next_prime(current + max(10, current // 2))
    n = harder["n"]
    worst_answer = [[c, harder["prime"] - 1] for c in range(n)]
    if 2 * n > 256 or len(json.dumps(worst_answer, separators=(",", ":"))) > 2000:
        return "cap_bound"
    return harder


def _greedy_candidate(inst: dict) -> list | None:
    chosen = []
    for c in range(inst["n"]):
        options = [
            x for x in range(inst["prime"])
            if all(not _edge(inst, d, chosen[d], c, x) for d in range(c))
        ]
        if not options:
            return None
        chosen.append(options[0])
    return [[c, chosen[c]] for c in range(inst["n"])]


def _zero_anchor_candidate(inst: dict) -> list:
    maps = _all_marked_maps(inst)
    values = [0] + [maps[0, c][0] for c in range(1, inst["n"])]
    return [[c, values[c]] for c in range(inst["n"])]


def _attack_results(inst: dict, seed: int) -> dict[str, bool]:
    n = inst["n"]
    zero = [[c, 0] for c in range(n)]
    greedy = _greedy_candidate(inst)
    rng = random.Random(seed ^ 0x200914171)
    restart_success = False
    for _ in range(256):
        if verify(inst, random_candidate(inst, rng))[0]:
            restart_success = True
            break
    return {
        "outlier_equal_degree_min_label": verify(inst, zero)[0],
        "greedy_left_to_right": greedy is not None and verify(inst, greedy)[0],
        "random_restart_256": restart_success,
        "by_hand_solve_excluded_affine_equations": verify(
            inst, _compact_affine_candidate(inst)
        )[0],
    }


def _reference_components(inst: dict) -> tuple[list | None, dict]:
    """Mechanical Track-B algorithm on the graph of uniquely excluded pairs."""
    n, p = inst["n"], inst["prime"]
    maps = _marked_forward(inst)
    total = n * p
    adjacency = [[] for _ in range(total)]
    undirected_edges = 0
    for (c, d), mapping in maps.items():
        for x, y in enumerate(mapping):
            u, v = c * p + x, d * p + y
            adjacency[u].append(v)
            adjacency[v].append(u)
            undirected_edges += 1

    seen = [False] * total
    edge_scans = 0
    components = 0
    for start in range(total):
        if seen[start]:
            continue
        components += 1
        queue = deque([start])
        seen[start] = True
        comp = []
        while queue:
            u = queue.popleft()
            comp.append(u)
            for v in adjacency[u]:
                edge_scans += 1
                if not seen[v]:
                    seen[v] = True
                    queue.append(v)
        if len(comp) == n:
            by_color = {}
            for u in comp:
                c, x = divmod(u, p)
                if c in by_color:
                    break
                by_color[c] = x
            if len(by_color) == n:
                candidate = [[c, by_color[c]] for c in range(n)]
                if verify(inst, candidate)[0]:
                    return candidate, {
                        "undirected_edges": undirected_edges,
                        "edge_insertions": 2 * undirected_edges,
                        "edge_scans": edge_scans,
                        "vertices_examined": sum(seen),
                        "components_started": components,
                        "operations": 2 * undirected_edges + edge_scans + sum(seen),
                    }
    return None, {
        "undirected_edges": undirected_edges,
        "edge_insertions": 2 * undirected_edges,
        "edge_scans": edge_scans,
        "vertices_examined": sum(seen),
        "components_started": components,
        "operations": 2 * undirected_edges + edge_scans + sum(seen),
    }


def _compact_affine_candidate(inst: dict) -> list | None:
    """The intended three-cycle/anchor-row route; independent of the answer."""
    if not inst.get("relations"):
        return None
    p = inst["prime"]
    rel = _relations(inst)

    def affine_from_zero(c: int) -> tuple[int, int]:
        a, b, g, excluded = rel[0, c]
        # x_c = A*x_0+B on the marked equation.
        ib = _inv(b, p)
        return (-a * ib) % p, ((excluded - g) * ib) % p

    a1, b1 = affine_from_zero(1)
    a2, b2 = affine_from_zero(2)
    a12, b12, g12, e12 = rel[1, 2]
    denominator = (a12 * a1 + b12 * a2) % p
    if denominator == 0:
        return None
    numerator = (e12 - g12 - a12 * b1 - b12 * b2) % p
    x0 = numerator * _inv(denominator, p) % p
    values = [x0]
    for c in range(1, inst["n"]):
        slope, offset = affine_from_zero(c)
        values.append((slope * x0 + offset) % p)
    return [[c, values[c]] for c in range(inst["n"])]


def _relabel_instance(
    inst: dict,
    rng: random.Random,
    *,
    permute_colors: bool,
    permute_vertices: bool,
) -> dict:
    """Create an explicit, genuinely isomorphic presentation for G8."""
    n, p = inst["n"], inst["prime"]
    old_for_new = list(range(n))
    if permute_colors:
        rng.shuffle(old_for_new)
    permutations = []
    inverses = []
    for _old in range(n):
        perm = list(range(p))
        if permute_vertices:
            rng.shuffle(perm)
        inv = [0] * p
        for old_x, new_x in enumerate(perm):
            inv[new_x] = old_x
        permutations.append(perm)
        inverses.append(inv)

    rows = {}
    marked = {}
    old_maps = _all_marked_maps(inst)
    for nc in range(n):
        for nd in range(nc + 1, n):
            oc, od = old_for_new[nc], old_for_new[nd]
            relation_rows = []
            marked_map = []
            for nx in range(p):
                ox = inverses[oc][nx]
                bits = 0
                for ny in range(p):
                    oy = inverses[od][ny]
                    if _edge(inst, oc, ox, od, oy):
                        bits |= 1 << ny
                relation_rows.append(bits)
                old_y = old_maps[oc, od][ox]
                marked_map.append(permutations[od][old_y])
            rows[_pair_key(nc, nd)] = relation_rows
            marked[_pair_key(nc, nd)] = marked_map

    old_answer = {c: x for c, x in inst["answer"]}
    answer = []
    for nc, oc in enumerate(old_for_new):
        answer.append([nc, permutations[oc][old_answer[oc]]])
    pair_count = n * (n - 1) // 2
    return {
        "family": inst["family"],
        "n": n,
        "prime": p,
        "explicit_rows": rows,
        "marked_maps": marked,
        "resident_count": 5 * n,
        "vertex_hospital_count": n * p,
        "edge_hospital_count": pair_count * p * (p - 3) // 2,
        "penalizing_hospital_count": 3 * n,
        "answer": answer,
    }


def _reordered_instance(inst: dict, rng: random.Random) -> dict:
    transformed = dict(inst)
    transformed["relations"] = [list(row) for row in inst["relations"]]
    rng.shuffle(transformed["relations"])
    transformed["answer"] = [list(pair) for pair in inst["answer"]]
    return transformed


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run every mandatory gate and return measured evidence."""
    report: dict[str, object] = {}

    # G1: every named preset, multiple seeds, exact JSON round-trip.
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
            compact = _compact_affine_candidate(inst)
            if compact is None or not verify(inst, compact)[0]:
                failures.append([preset, seed, "compact route failed"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    answer = inst["answer"]

    # G2: five distinct malformed/corrupted forms and five distinct reasons.
    swapped = [list(pair) for pair in answer]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = [list(pair) for pair in answer]
    duplicate[1] = list(duplicate[0])
    out_of_range = [list(pair) for pair in answer]
    out_of_range[0][1] = inst["prime"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
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

    # G3: prose, Markdown fence, whitespace, and malformed text.
    compact_answer = json.dumps(answer, separators=(",", ":"))
    model_reply = (
        "The excluded affine maps give a consistent component.\n"
        "<answer>\n```json\n" + compact_answer + "\n```\n</answer>\n"
        "I checked every color pair."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4 and G5 shipping density share the required 200,000 samples.
    samples = 200_000
    hits = 0
    rng = random.Random(0x200914171)
    sample_start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, rng)
        hits += int(verify(inst, candidate)[0])
    sample_wall = time.perf_counter() - sample_start
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "empirical_probability": hits / samples,
        "candidate_space": search_space(inst),
        "prior": "uniform over one GF(p) label for each already-fixed color",
        "sampling_wall_seconds": sample_wall,
    }

    # G6: the obvious in-context affine ansatz succeeds, honestly rejecting H.
    attack_names = (
        "outlier_equal_degree_min_label",
        "greedy_left_to_right",
        "random_restart_256",
        "by_hand_solve_excluded_affine_equations",
    )
    attack_counts = {name: 0 for name in attack_names}
    attempts = 8
    reference_successes = 0
    reference_wall = 0.0
    reference_operations = 0
    reference_edges = 0
    reference_components = 0
    for seed in range(attempts):
        attack_inst = make_instance(seed=10_000 + seed, **shipping)
        for name, solved in _attack_results(attack_inst, 10_000 + seed).items():
            attack_counts[name] += int(solved)
        start = time.perf_counter()
        reference_answer = _compact_affine_candidate(attack_inst)
        reference_wall += time.perf_counter() - start
        operations = 13 + 4 * (shipping["n"] - 3)
        reference_operations += operations
        reference_successes += int(
            reference_answer is not None
            and verify(attack_inst, reference_answer)[0]
        )

    attacks = {
        name: {"successes": attack_counts[name], "attempts": attempts}
        for name in attack_names
    }
    all_attacks_failed = all(row["successes"] == 0 for row in attacks.values())
    reference = {
        "name": "modular elimination on the displayed excluded equations",
        "complexity": "O(n^2) row scan plus O(n) field operations",
        "wall_clock_sec": reference_wall,
        "wall_clock_sec_mean": reference_wall / attempts,
        "operations": reference_operations,
        "operations_mean": reference_operations // attempts,
        "solves": f"{reference_successes}/{attempts}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == attempts,
        "attacks": attacks,
        "reference_algorithm": reference,
    }
    report["G5_density_and_baseline"] = {
        "pass": hits / samples < 1e-6 and reference_successes == attempts,
        "shipping_density_sample_count": samples,
        "shipping_valid_hits": hits,
        "shipping_observed_valid_fraction": hits / samples,
        "shipping_candidate_space": search_space(inst),
        "enumerate_all_shipping": enumerate_all(inst),
        "demo_exact_valid_solution_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
        "density_sampling_wall_seconds": sample_wall,
        "baseline_wall_seconds": reference_wall,
        "baseline_wall_seconds_mean": reference_wall / attempts,
        "baseline_operations": reference_operations,
        "baseline_operations_mean": reference_operations // attempts,
        "baseline_rows_scanned_mean": shipping["n"] * (shipping["n"] - 1) // 2,
        "baseline_successes": reference_successes,
    }

    # G7: double n; the answer still remains inside the 256-atom cap.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_wall = time.perf_counter() - start
    named_sizes = [params["n"] * params["prime"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled_params["n"] > shipping["n"]
        and _answer_atoms(doubled["answer"]) <= 256
        and named_sizes == sorted(named_sizes),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_wall,
        "shipping_answer_atoms": _answer_atoms(answer),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
        "named_ambient_sizes": named_sizes,
    }

    # G8: arbitrary within-color relabeling, color permutation, and composition.
    invariant_checks = 0
    real_checks = 0
    unrelated_keys = []
    key_params = {"n": 10, "prime": 17}
    for seed in range(20):
        key_inst = make_instance(seed=20_000 + seed, **key_params)
        key = canonical_key(key_inst)
        unrelated_keys.append(key)
        transformations = (
            _relabel_instance(
                key_inst, random.Random(30_000 + seed),
                permute_colors=False, permute_vertices=True,
            ),
            _relabel_instance(
                key_inst, random.Random(40_000 + seed),
                permute_colors=True, permute_vertices=False,
            ),
            _relabel_instance(
                key_inst, random.Random(50_000 + seed),
                permute_colors=True, permute_vertices=True,
            ),
            _reordered_instance(key_inst, random.Random(60_000 + seed)),
        )
        for transformed in transformations:
            invariant_checks += int(canonical_key(transformed) == key)
            real_checks += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80
        and real_checks == 80
        and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "invariance_expected": 80,
        "real_transformation_verify_checks": real_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "symmetries": [
            "arbitrary vertex relabeling independently in every color",
            "arbitrary color permutation",
            "composition of both relabelings",
            "arbitrary reordering of the relation table",
        ],
    }

    # G9(c): measure worst answer size over 200 shipping seeds.
    sizes = []
    for seed in range(200):
        size_inst = make_instance(seed=30_000 + seed, **shipping)
        blob = json.dumps(size_inst["answer"], separators=(",", ":"))
        sizes.append((
            len(blob), (len(blob) + 3) // 4, _answer_atoms(size_inst["answer"])
        ))
    answer_chars = max(row[0] for row in sizes)
    answer_tokens = max(row[1] for row in sizes)
    answer_elements = max(row[2] for row in sizes)
    intended_operations = 13 + 4 * (shipping["n"] - 3)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    hint_effect = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "oracle_evidence_status": G9_ORACLE_STATUS,
        "arms": arms,
        "hinted_minus_placebo": hint_effect,
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
