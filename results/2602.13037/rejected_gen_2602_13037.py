"""Verified compact coloring witnesses for arXiv:2602.13037.

The family instantiates the paper's Theorem 15 at k=1.  A proper 3-coloring
of a planar maximum-degree-four base graph is carried through the theorem's
forcing gadget to a (1^3,2^1)-coloring of a planar maximum-degree-seven graph.
The base coloring is represented by three coefficients of an affine map over
a prime field.  Verification expands the complete target graph and checks all
distance-one and distance-two constraints exactly.

Generation is deterministic in (n, seed, params), uses a private Random, does
no file I/O, and prints nothing at import time.  Only the standard library is
needed; gvlib is not required for finite-field arithmetic this small.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK = "B"

_REDUCTION = (
    "Section 2.6, Theorem 15: attach H_1^k to every vertex of a planar "
    "maximum-degree-4 graph and carry a proper 3-coloring to a "
    "(1^3,2^k)-coloring; instantiated here at k=1"
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "coordinate-labelled planar graph",
        "paper-defined planar forcing-gadget graph",
        "affine finite-field coloring rule",
    ],
    "verification_operations": [
        "finite-field affine evaluation",
        "exact edge color comparison",
        "exact length-two conflict scan",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The base graph's forced three-color phase is encoded by three parallel "
        "affine fibers; without recognizing them, a solver must propagate a "
        "coloring and mechanically interpolate and test candidate rules."
    ),
    "hardness_basis": (
        "Rejected Track-B hypothesis: the O(n + log q) reference used "
        "110443--110587 counted operations at n=2400,q=1009, but the named "
        "anchor reduces certificate production to the same six interpolations "
        "used by the alleged shortcut; two of six candidates verify and trying "
        "all six costs at least 360 exact operations."
    ),
    "max_answer_tokens": 3,
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

DIFFICULTY = {
    "demo": {"n": 6, "q": 11},
    "easy": {"n": 90, "q": 101},
    "medium": {"n": 600, "q": 503},
    "hard": {"n": 2400, "q": 1009},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The shared triangles carry one three-color phase whose coordinate classes "
    "are three parallel affine fibers."
)
PLACEBO_HINT = (
    "The listed triangles require careful attention to the stated finite-field "
    "and indexing conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One of the six affine rules [a,b,d] obtained by assigning the named "
        "noncollinear anchor triangle a permutation of colors 0,1,2 and "
        "interpolating C(X,Y)=(aX+bY+d) mod q.  This incorporates the "
        "constraint a reader gets for free from the statement."
    ),
    "bounds": {
        "coefficients": 3,
        "anchor_color_permutations": 6,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 defines a (1^a,2^b)-coloring as a
partition into a independent sets and b sets whose distinct vertices have
graph distance at least three.  Section 2 observes that an explicit vertex
color map is a polynomial-size NP witness checked by scanning colors.  The
same section identifies the polynomial cases (1^2,2^0), (1^1,2^1),
(1^0,2^2), and (1^0,2^3); this family avoids all of them.  Theorem 15 proves
NP-completeness of (1^3,2^k)-coloring on planar graphs of maximum degree
3k+4.  At k=1 its local H_1^1 gadget has vertices u,v, one neighbor x of u,
and two K4 blocks sharing x.  If x used a distance-1 color, the two K4 blocks
would require two distance-2 colors at mutual distance two, so x must use the
single distance-2 color.  That exhausts this color within distance two of u
and v, forcing both to use distance-1 colors.  Identifying v with a base
vertex carries every proper base 3-coloring to the target graph.

Generation route.  The base graph is the square of a path: positions i and j
are adjacent exactly when 1<=|i-j|<=2.  It is maximal outerplanar, has maximum
degree four, and its consecutive triples force a repeating proper 3-coloring.
The generator samples the color phase first, samples one affine line for each
of its three values in F_q^2, and places every vertex of a phase uniformly on
the corresponding line.  It then relabels vertices and shuffles edges.  The
three affine coefficients are therefore known before the target graph exists;
no generated instance is solved.  The checker materializes every vertex and
edge of the Theorem 15 graph and executes the witness test rather than
appealing to the theorem.

Why Track B.  This distribution is not claimed average-case hard.  An exact
algorithm finds a triangle, tries its six proper color assignments, performs
finite-field interpolation, and tests the resulting rule in linear time.
Selftest reports its actual target-graph scan cost and time.  The intended
shortcut is to recognize the common affine-fiber invariant and do only the
six tiny interpolations around the displayed anchor.  Thus the paper's
worst-case NP-completeness is context, not the Track B hardness claim.

Adversaries.  Coordinate points within every phase are sampled from the same
uniform line distribution.  The generator rejects only presentations solved
by the declared lowest-label greedy rule, an extreme-coordinate triangle, or
small axis-aligned coefficient guesses.

Rejection audit.  The original implementation sampled random candidates from
all nonzero affine coefficient triples.  That was not structure-aware: the
statement explicitly names a noncollinear graph triangle, whose three colors
must be a permutation of 0,1,2.  The corrected language consists of its six
interpolants.  Exactly two verify, corrected sampling succeeds about one time
in three, and the 4096-restart attack succeeds on every tested seed.  The
retained module therefore records G4, G5, G6, and G9 as failures.

Canonicalization.  The square-of-a-path graph has two canonical orders,
reversals of one another.  For each, all coordinates are expressed in the
affine frame of its first three points; the lexicographically smaller frame
sequence is hashed.  Consequently the key ignores vertex names, edge and
record order, path reversal, translations, and every invertible affine change
of coordinates, while retaining the random affine geometry that distinguishes
unrelated seeds.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_PRIMES = [11, 101, 503, 1009, 10007, 100003, 1000003, 10000019,
           100000007, 1000000007, 2147483647]
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_RANDOM_RESTARTS = 4096
_ENUMERATION_CAP = 300_000
_ANCHOR_RULE_CACHE: dict[int, tuple[dict, tuple[tuple[int, int, int], ...]]] = {}

# Filled from script-owned runs after hardening.  Pending evidence deliberately
# makes G9 fail; it is replaced only after all three arms have run.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _check_int(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < low or value > high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    r = math.isqrt(n)
    p = 3
    while p <= r:
        if n % p == 0:
            return False
        p += 2
    return True


def _coords_dict(inst: dict) -> dict[int, tuple[int, int]]:
    return {int(v): (int(x), int(y)) for v, x, y in inst["base_vertices"]}


def _adjacency(n: int, edges: list[list[int]] | list[tuple[int, int]]) -> list[set[int]]:
    adj = [set() for _ in range(n)]
    for raw_u, raw_v in edges:
        u, v = int(raw_u), int(raw_v)
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _det3_points(points: list[tuple[int, int]], q: int) -> int:
    (x0, y0), (x1, y1), (x2, y2) = points
    return ((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) % q


def _mod_inverse(value: int, q: int, counter: list[int] | None = None) -> int:
    """Exact inverse with an operation counter for the reference measurement."""
    old_r, r = value % q, q
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        if counter is not None:
            counter[0] += 4
    if old_r != 1:
        raise ValueError("noninvertible field element")
    return old_s % q


def _interpolate(points: list[tuple[int, int]], values: list[int], q: int,
                 counter: list[int] | None = None) -> list[int] | None:
    """Solve aX+bY+d=value through three noncollinear points."""
    (x0, y0), (x1, y1), (x2, y2) = points
    v0, v1, v2 = values
    dx1, dy1 = (x1 - x0) % q, (y1 - y0) % q
    dx2, dy2 = (x2 - x0) % q, (y2 - y0) % q
    dv1, dv2 = (v1 - v0) % q, (v2 - v0) % q
    det = (dx1 * dy2 - dx2 * dy1) % q
    if counter is not None:
        counter[0] += 13
    if det == 0:
        return None
    inv = _mod_inverse(det, q, counter)
    a = ((dv1 * dy2 - dv2 * dy1) * inv) % q
    b = ((dx1 * dv2 - dx2 * dv1) * inv) % q
    d = (v0 - a * x0 - b * y0) % q
    if counter is not None:
        counter[0] += 11
    return [a, b, d]


def _evaluate(rule: list[int], point: tuple[int, int], q: int,
              counter: list[int] | None = None) -> int:
    if counter is not None:
        counter[0] += 5
    return (rule[0] * point[0] + rule[1] * point[1] + rule[2]) % q


def _fast_rule_check(inst: dict, rule: object,
                     counter: list[int] | None = None) -> bool:
    if not (isinstance(rule, list) and len(rule) == 3 and
            all(isinstance(x, int) and not isinstance(x, bool) for x in rule)):
        return False
    q = inst["q"]
    if any(x < 0 or x >= q for x in rule) or rule[:2] == [0, 0]:
        return False
    colors = [-1] * inst["n"]
    # Iterate the stored records directly.  A random rule almost always fails
    # on its first point, which keeps the required 200k exact trials linear in
    # the trials rather than linear in trials times the full graph size.
    for v, x, y in inst["base_vertices"]:
        c = _evaluate(rule, (x, y), q, counter)
        if c > 2:
            return False
        colors[v] = c
    for u, v in inst["base_edges"]:
        if counter is not None:
            counter[0] += 1
        if colors[u] == colors[v]:
            return False
    return True


def _greedy_attack(inst: dict) -> list[int] | None:
    n = inst["n"]
    adj = _adjacency(n, inst["base_edges"])
    colors: dict[int, int] = {}
    for v in range(n):
        used = {colors[w] for w in adj[v] if w in colors}
        c = next((x for x in range(3) if x not in used), None)
        if c is None:
            return None
        colors[v] = c
    ids = list(inst["anchor_triangle"])
    coords = _coords_dict(inst)
    return _interpolate([coords[v] for v in ids], [colors[v] for v in ids], inst["q"])


def _outlier_attack(inst: dict) -> list[int] | None:
    coords = _coords_dict(inst)
    ids = list(inst["anchor_triangle"])
    ordered = sorted(ids, key=lambda v: (coords[v][0] + coords[v][1], coords[v], v))
    assigned = {v: i for i, v in enumerate(ordered)}
    return _interpolate([coords[v] for v in ids], [assigned[v] for v in ids], inst["q"])


def _small_ansatz_attack(inst: dict) -> list[int] | None:
    q = inst["q"]
    coords = _coords_dict(inst)
    first = min(coords)
    x0, y0 = coords[first]
    small = [0, 1, q - 1]
    for a in small:
        for b in small:
            if a == b == 0:
                continue
            for target in range(3):
                d = (target - a * x0 - b * y0) % q
                candidate = [a, b, d]
                if _fast_rule_check(inst, candidate):
                    return candidate
    return None


def _random_restart_attack(inst: dict, seed: int,
                           attempts: int = _RANDOM_RESTARTS) -> tuple[list[int] | None, int]:
    rng = random.Random(seed)
    for i in range(attempts):
        candidate = random_candidate(inst, rng)
        if _fast_rule_check(inst, candidate):
            return candidate, i + 1
    return None, attempts


def _build_once(n: int, q: int, seed: int, nonce: int) -> dict:
    rng = random.Random((seed * 0x9E3779B185EBCA87 + nonce * 0xC2B2AE3D27D4EB4F
                         + n * 65537 + q) & ((1 << 128) - 1))

    position_to_id = list(range(n))
    rng.shuffle(position_to_id)
    phase_values = [0, 1, 2]
    rng.shuffle(phase_values)

    # Avoid the tiny coefficient family used by the explicit ansatz attack.
    forbidden = {0, 1, q - 1}
    a = rng.randrange(2, q - 1)
    b = rng.randrange(2, q - 1)
    while a in forbidden or b in forbidden or a == b:
        a = rng.randrange(2, q - 1)
        b = rng.randrange(2, q - 1)
    d = rng.randrange(q)
    inv_b = pow(b, -1, q)

    counts = [sum(1 for i in range(n) if phase_values[i % 3] == c)
              for c in range(3)]
    x_pool = {c: rng.sample(range(q), counts[c]) for c in range(3)}
    x_used = [0, 0, 0]
    records: list[list[int]] = []
    points_by_position: list[tuple[int, int]] = []
    for i in range(n):
        color = phase_values[i % 3]
        x = x_pool[color][x_used[color]]
        x_used[color] += 1
        y = ((color - d - a * x) * inv_b) % q
        points_by_position.append((x, y))
        records.append([position_to_id[i], x, y])

    # Every consecutive triple is a graph triangle and must support interpolation.
    if any(_det3_points(points_by_position[i:i + 3], q) == 0
           for i in range(n - 2)):
        raise ValueError("degenerate triangle coordinates")

    edges = []
    for gap in (1, 2):
        for i in range(n - gap):
            u, v = position_to_id[i], position_to_id[i + gap]
            edges.append([min(u, v), max(u, v)])
    rng.shuffle(edges)
    rng.shuffle(records)

    anchor_pos = rng.randrange(n - 2)
    anchor = position_to_id[anchor_pos:anchor_pos + 3]
    rng.shuffle(anchor)
    probes = rng.sample(position_to_id, min(3, n))
    inst = {
        "paper": "arXiv:2602.13037",
        "family": "compact (1^3,2^1)-coloring via Theorem 15",
        "n": n,
        "q": q,
        "base_vertices": records,
        "base_edges": edges,
        "anchor_triangle": anchor,
        "probe_vertices": probes,
        "target_vertex_count": 9 * n,
        "target_edge_count": (2 * n - 3) + 14 * n,
        "answer": [a, b, d],
    }
    return inst


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate an affine base coloring and carry it through Theorem 15."""
    n = _check_int("n", n, 6, 20000)
    seed = _check_int("seed", seed, -(1 << 63), (1 << 63) - 1)
    q = _check_int("q", params.pop("q", 1009), 7, 2147483647)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if not _is_prime(q):
        raise ValueError("q must be prime")
    if max(sum(1 for i in range(n) if i % 3 == c) for c in range(3)) > q:
        raise ValueError("q is too small for n: each affine fiber needs distinct points")

    for nonce in range(200):
        try:
            inst = _build_once(n, q, seed, nonce)
        except ValueError:
            continue
        answer = inst["answer"]
        swapped = [answer[1], answer[0], answer[2]]
        if _fast_rule_check(inst, swapped):
            continue
        if _fast_rule_check(inst, _greedy_attack(inst)):
            continue
        if _fast_rule_check(inst, _outlier_attack(inst)):
            continue
        if _small_ansatz_attack(inst) is not None:
            continue
        return inst
    raise RuntimeError("could not obscure the planted affine phase")


def render(inst: dict) -> str:
    """Render the complete graph problem and exact coefficient wire format."""
    vertices = "\n".join(f"{v}: {x} {y}" for v, x, y in sorted(inst["base_vertices"]))
    edges = " ".join(f"{u}-{v}" for u, v in inst["base_edges"])
    anchor = " ".join(map(str, inst["anchor_triangle"]))
    probes = " ".join(map(str, inst["probe_vertices"]))
    text = f"""Compact (1^3,2^1)-coloring certificate

All vertex numbers are 0-based.  All arithmetic explicitly marked modulo q
uses the least residue in 0,...,q-1.  An independent set contains no adjacent
pair.  A 2-independent set contains no two distinct vertices whose graph
distance is 1 or 2.  A (1^3,2^1)-coloring assigns one of three distance-1
colors D0,D1,D2 or the one distance-2 color S to every vertex, with each D
class independent and the S class 2-independent.

The target graph H is given compactly from the coordinate-labelled base graph
B below.  It is still a completely specified finite graph.  For every base
vertex v, H contains v and eight new vertices u(v), x(v), and t(v,j,r) for
j in {{0,1}} and r in {{0,1,2}}.  H has every base edge and, for every v:

  v--u(v), u(v)--x(v);
  x(v)--t(v,j,r) for every j,r;
  all three edges among t(v,j,0),t(v,j,1),t(v,j,2), for each j.

There are no other vertices or edges.  Thus each j-block together with x(v)
is a K4, the two K4s share only x(v), and the gadget meets B only at v.
This instance has {inst['target_vertex_count']} target vertices and
{inst['target_edge_count']} target edges.

Let q={inst['q']}.  A witness is exactly three integers a,b,d.  It defines

  C(v) = (a*X(v) + b*Y(v) + d) mod q.

You must have 0<=a,b,d<q, (a,b)!=(0,0), C(v) in {{0,1,2}} for every base
vertex, and C(u)!=C(v) on every base edge.  The rule then colors H as follows:

  base v gets D[C(v)];  u(v) gets D[(C(v)+1) mod 3];
  x(v) gets S;           t(v,j,r) gets D[r].

Your coefficients are accepted only if this fully expanded coloring satisfies
all edge and length-two constraints.  Order of a,b,d matters and repetitions
are allowed.  The named anchor is merely one base triangle; the probes are
ordinary vertices and impose no extra condition.

Base vertices, one line "id: X Y" ({inst['n']} total):
{vertices}

Base edges, as unordered u-v pairs ({len(inst['base_edges'])} total):
{edges}

Anchor triangle: {anchor}
Probe vertices: {probes}

Give your final answer inside <answer></answer> tags as exactly a JSON array
[a,b,d] of three base-10 integers, in that order.
Example: <answer>[2,7,4]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON array, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        if re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+){2}", body):
            try:
                value = [int(x.strip()) for x in body.split(",")]
            except ValueError:
                return None
        else:
            return None
    return value


def _expanded_target(inst: dict, colors: dict[int, int]) -> tuple[list[tuple[int, int]],
                                                                   list[tuple[int, int]]]:
    """Return (kind,color) per vertex and every edge of the actual target H."""
    n = inst["n"]
    assignments: list[tuple[int, int]] = [(-1, -1)] * (9 * n)
    for v in range(n):
        assignments[v] = (1, colors[v])
        assignments[n + v] = (1, (colors[v] + 1) % 3)       # u(v)
        assignments[2 * n + v] = (2, 0)                     # x(v)
        for j in range(2):
            for r in range(3):
                assignments[3 * n + 6 * v + 3 * j + r] = (1, r)

    edges: list[tuple[int, int]] = [(int(u), int(v)) for u, v in inst["base_edges"]]
    for v in range(n):
        u_node, x_node = n + v, 2 * n + v
        edges.append((v, u_node))
        edges.append((u_node, x_node))
        for j in range(2):
            triple = [3 * n + 6 * v + 3 * j + r for r in range(3)]
            edges.extend((x_node, t) for t in triple)
            edges.extend((triple[r], triple[s]) for r in range(3) for s in range(r + 1, 3))
    return assignments, edges


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Expand and exactly scan any coefficient witness; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) != 3:
        return False, f"expected 3 coefficients, got {len(answer)}"
    for i, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"coefficient {i} is not an integer"
    q = inst["q"]
    if any(value < 0 or value >= q for value in answer):
        return False, f"coefficients must lie in 0..{q - 1}"
    if answer[0] == answer[1] == 0:
        return False, "the affine linear part (a,b) may not be zero"

    base_colors: dict[int, int] = {}
    for v, x, y in inst["base_vertices"]:
        c = _evaluate(answer, (x, y), q)
        if c > 2:
            return False, f"base vertex {v} maps to {c}, outside color set 0..2"
        base_colors[v] = c
    for u, v in inst["base_edges"]:
        if base_colors[u] == base_colors[v]:
            return False, f"base edge {u}-{v} is monochromatic"

    assignments, edges = _expanded_target(inst, base_colors)
    adj = [set() for _ in assignments]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
        if assignments[u] == assignments[v]:
            kind = "distance-1" if assignments[u][0] == 1 else "distance-2"
            return False, f"target edge {u}-{v} repeats a {kind} color"
    square_vertices = [i for i, item in enumerate(assignments) if item[0] == 2]
    for x in square_vertices:
        for middle in adj[x]:
            for y in adj[middle]:
                if y != x and assignments[y] == assignments[x]:
                    return False, f"target vertices {x} and {y} repeat S within distance 2"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the six rules a reader would actually try."""
    cached = _ANCHOR_RULE_CACHE.get(id(inst))
    if cached is None or cached[0] is not inst:
        coords = _coords_dict(inst)
        ids = list(inst["anchor_triangle"])
        points = [coords[v] for v in ids]
        rules = tuple(
            tuple(_interpolate(points, list(values), inst["q"]) or ())
            for values in itertools.permutations(range(3))
        )
        if any(len(rule) != 3 for rule in rules):
            raise AssertionError("the declared anchor must be noncollinear")
        cached = (inst, rules)  # type: ignore[assignment]
        _ANCHOR_RULE_CACHE[id(inst)] = cached
    return list(cached[1][rng.randrange(6)])


def search_space(inst: dict) -> int:
    return 6


def enumerate_all(inst: dict) -> int | None:
    coords = _coords_dict(inst)
    ids = list(inst["anchor_triangle"])
    points = [coords[v] for v in ids]
    return sum(
        int(_fast_rule_check(inst, _interpolate(points, list(values), inst["q"])))
        for values in itertools.permutations(range(3))
    )


def _chain_orders(inst: dict) -> list[list[int]]:
    n = inst["n"]
    adj = _adjacency(n, inst["base_edges"])
    endpoints = [v for v in range(n) if len(adj[v]) == 2]
    if len(endpoints) != 2:
        raise ValueError("base graph is not a path square")
    orders = []
    for start in endpoints:
        choices = sorted(adj[start], key=lambda v: (len(adj[v]), v))
        second = choices[0]
        order = [start, second]
        seen = set(order)
        while len(order) < n:
            common = (adj[order[-2]] & adj[order[-1]]) - seen
            if len(common) != 1:
                raise ValueError("cannot reconstruct the path-square order")
            nxt = next(iter(common))
            order.append(nxt)
            seen.add(nxt)
        orders.append(order)
    return orders


def _affine_frame_signature(inst: dict, order: list[int]) -> tuple[tuple[int, int], ...]:
    q = inst["q"]
    coords = _coords_dict(inst)
    p0, p1, p2 = (coords[v] for v in order[:3])
    dx1, dy1 = (p1[0] - p0[0]) % q, (p1[1] - p0[1]) % q
    dx2, dy2 = (p2[0] - p0[0]) % q, (p2[1] - p0[1]) % q
    det = (dx1 * dy2 - dx2 * dy1) % q
    inv = pow(det, -1, q)
    out = []
    for v in order:
        dx, dy = (coords[v][0] - p0[0]) % q, (coords[v][1] - p0[1]) % q
        alpha = ((dx * dy2 - dx2 * dy) * inv) % q
        beta = ((dx1 * dy - dx * dy1) * inv) % q
        out.append((alpha, beta))
    return tuple(out)


def canonical_key(inst: dict) -> str:
    """Affine- and relabelling-invariant key for generated path-square instances."""
    signatures = [_affine_frame_signature(inst, order) for order in _chain_orders(inst)]
    payload = json.dumps([inst["q"], min(signatures)], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow graph size and the coefficient haystack while the answer stays length 3."""
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 90))
    q = int(current.get("q", 101))
    next_q = next((p for p in _PRIMES if p > q), None)
    if next_q is None or n >= 20000:
        return None
    new_n = min(20000, max(n + 1, n * 2))
    while math.ceil(new_n / 3) > next_q:
        next_q = next((p for p in _PRIMES if p > next_q), None)
        if next_q is None:
            return None
    current["n"] = new_n
    current["q"] = next_q
    return current


def _reference_algorithm(inst: dict) -> tuple[list[int] | None, int]:
    """Try the six anchor colorings, interpolate, and exactly scan the target."""
    counter = [0]
    coords = _coords_dict(inst)
    ids = list(inst["anchor_triangle"])
    points = [coords[v] for v in ids]
    for values_tuple in itertools.permutations(range(3)):
        counter[0] += 1
        rule = _interpolate(points, list(values_tuple), inst["q"], counter)
        if rule is None or not _fast_rule_check(inst, rule, counter):
            continue
        ok, _ = verify(inst, rule)
        # Count the explicit target construction and edge/distance-two scan.
        counter[0] += inst["target_vertex_count"] + inst["target_edge_count"] + 14 * inst["n"]
        if ok:
            return rule, counter[0]
    return None, counter[0]


def _relabel_instance(inst: dict, rng: random.Random) -> dict:
    out = copy.deepcopy(inst)
    labels = list(range(inst["n"]))
    rng.shuffle(labels)
    mapping = {old: labels[old] for old in range(inst["n"])}
    out["base_vertices"] = [[mapping[v], x, y] for v, x, y in inst["base_vertices"]]
    out["base_edges"] = [[min(mapping[u], mapping[v]), max(mapping[u], mapping[v])]
                         for u, v in inst["base_edges"]]
    out["anchor_triangle"] = [mapping[v] for v in inst["anchor_triangle"]]
    out["probe_vertices"] = [mapping[v] for v in inst["probe_vertices"]]
    rng.shuffle(out["base_vertices"])
    rng.shuffle(out["base_edges"])
    rng.shuffle(out["anchor_triangle"])
    return out


def _affine_transform_instance(inst: dict, rng: random.Random) -> dict:
    out = copy.deepcopy(inst)
    q = inst["q"]
    while True:
        m00, m01, m10, m11 = [rng.randrange(q) for _ in range(4)]
        det = (m00 * m11 - m01 * m10) % q
        if det:
            break
    tx, ty = rng.randrange(q), rng.randrange(q)
    transformed = []
    for v, x, y in inst["base_vertices"]:
        xp = (m00 * x + m01 * y + tx) % q
        yp = (m10 * x + m11 * y + ty) % q
        transformed.append([v, xp, yp])
    out["base_vertices"] = transformed

    a, b, d = inst["answer"]
    inv_det = pow(det, -1, q)
    ap = ((a * m11 - b * m10) * inv_det) % q
    bp = ((-a * m01 + b * m00) * inv_det) % q
    dp = (d - ap * tx - bp * ty) % q
    out["answer"] = [ap, bp, dp]
    return out


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))
    atoms = len(answer) if isinstance(answer, list) else 1
    return len(blob), math.ceil(len(blob) / 4), atoms


def selftest() -> dict:
    """Run and return all mandatory correctness, resistance, and invariance gates."""
    report: dict[str, Any] = {}

    # G1: every rung and four seeds, plus JSON-native answers.
    g1_ok = True
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 314159):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_checks += 1
            if not (ok and json_ok):
                g1_ok = False
                g1_failures.append(f"{preset}/{seed}: {why}, json={json_ok}")
    report["G1_planted_verifies"] = {
        "pass": g1_ok, "checks": g1_checks, "failures": g1_failures,
    }

    # G2: mandated corruption styles with distinct diagnostics.
    inst = make_instance(seed=2026, **DIFFICULTY["easy"])
    ans = list(inst["answer"])
    corruptions = {
        "drop_one": ans[:-1],
        "swap_two": [ans[1], ans[0], ans[2]],
        "duplicate_one": ans + [ans[0]],
        "empty": [],
        "out_of_range": [inst["q"], ans[1], ans[2]],
    }
    reasons = {}
    all_rejected = True
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        all_rejected &= not ok
        reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": bool(all_rejected and len(set(reasons.values())) == len(reasons)),
        "rejections": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    # G3: exact round trip through realistic prose and a fenced answer.
    wrapped = "I used the shared phase.\n<answer>```json\n" + json.dumps(ans) + "\n```</answer>\nDone."
    parsed = parse_answer(wrapped)
    report["G3_round_trip"] = {
        "pass": parsed == ans,
        "parsed": parsed,
    }

    # G4 and shipping-density half of G5 share the required 200k samples.
    # There are only six structure-aware candidates: the named anchor is a
    # triangle, so its colors must be a permutation of 0,1,2.  Enumerate those
    # six once, verify them exactly, then sample uniformly from that same set.
    ship = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])
    rng = random.Random(0x260213037)
    hits = 0
    t0 = time.perf_counter()
    ship_coords = _coords_dict(ship)
    ship_ids = list(ship["anchor_triangle"])
    ship_points = [ship_coords[v] for v in ship_ids]
    anchor_rules = [
        _interpolate(ship_points, list(values), ship["q"])
        for values in itertools.permutations(range(3))
    ]
    valid_rules = {
        tuple(rule) for rule in anchor_rules
        if rule is not None and verify(ship, rule)[0]
    }
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(ship, rng)
        if tuple(candidate) in valid_rules:
            hits += 1
    density_wall = time.perf_counter() - t0
    probability = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "probability": probability,
        "structure_aware_space": search_space(ship),
        "exact_valid_rules_in_space": len(valid_rules),
    }

    # Exact small count, reference algorithm, and strongest failing-attack cost.
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    exact_demo_count = enumerate_all(demo)
    t0 = time.perf_counter()
    reference_answer, reference_ops = _reference_algorithm(ship)
    reference_wall = time.perf_counter() - t0
    attack_t0 = time.perf_counter()
    attack_answer, attack_trials = _random_restart_attack(ship, 99173)
    attack_wall = time.perf_counter() - attack_t0
    report["G5_density_and_baseline"] = {
        "pass": bool(hits == 0 and exact_demo_count is not None and
                     reference_answer is not None and attack_answer is None),
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_density_fraction": probability,
        "shipping_density_wall_sec": round(density_wall, 6),
        "demo_exact_solution_count": exact_demo_count,
        "demo_search_space": search_space(demo),
        "baseline_attack_wall_sec": round(attack_wall, 6),
        "baseline_attack_candidates": attack_trials,
        "reference_wall_sec": round(reference_wall, 6),
        "reference_operations": reference_ops,
    }

    # G6: four failing attacks, plus the successful Track B reference algorithm.
    attack_results = {
        "outlier_extreme_triangle": {"successes": 0, "attempts": _ATTACK_SEEDS},
        "greedy_lowest_label": {"successes": 0, "attempts": _ATTACK_SEEDS},
        "random_restart_4096": {"successes": 0, "attempts": _ATTACK_SEEDS},
        "obvious_axis_ansatz": {"successes": 0, "attempts": _ATTACK_SEEDS},
    }
    reference_successes = 0
    ref_ops_all = []
    ref_t0 = time.perf_counter()
    for seed in range(_ATTACK_SEEDS):
        current = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_extreme_triangle": _outlier_attack(current),
            "greedy_lowest_label": _greedy_attack(current),
            "obvious_axis_ansatz": _small_ansatz_attack(current),
        }
        random_hit, _ = _random_restart_attack(current, 70000 + seed)
        candidates["random_restart_4096"] = random_hit
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attack_results[name]["successes"] += 1
        ref_answer, ref_ops = _reference_algorithm(current)
        ref_ops_all.append(ref_ops)
        if ref_answer is not None and verify(current, ref_answer)[0]:
            reference_successes += 1
    ref_panel_wall = time.perf_counter() - ref_t0
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "triangle propagation, six affine interpolations, exact target scan",
            "complexity": "O(n + log q) exact",
            "wall_clock_sec": round(ref_panel_wall, 6),
            "operations_min": min(ref_ops_all),
            "operations_max": max(ref_ops_all),
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    # G7: n doubles while the certificate remains three atoms; q grows only as needed.
    doubled_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_ok = isinstance(doubled_params, dict) and doubled_params["n"] >= 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
    doubled_reason = "escalate failed"
    if doubled_ok:
        doubled = make_instance(seed=8888, **doubled_params)
        doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": bool(doubled_ok),
        "shipping_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_params": doubled_params,
        "doubled_verify": doubled_reason,
        "answer_atoms_before": 3,
        "answer_atoms_after": 3,
    }

    # G8: relabel + reorder + arbitrary invertible affine coordinate maps.
    invariant = 0
    carried = 0
    keys = []
    g8_rng = random.Random(8080)
    for seed in range(20):
        original = make_instance(
            seed=5000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        key = canonical_key(original)
        keys.append(key)
        changed = _affine_transform_instance(_relabel_instance(original, g8_rng), g8_rng)
        if canonical_key(changed) == key:
            invariant += 1
        if verify(changed, changed["answer"])[0]:
            carried += 1
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(set(keys)) == 20,
        "invariance_passed": invariant,
        "invariance_attempts": 20,
        "carried_witness_passed": carried,
        "carried_witness_attempts": 20,
        "unrelated_distinct": len(set(keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "vertex relabelling", "record order", "edge order", "path reversal",
            "invertible affine coordinate change", "global translation",
        ],
    }

    chars, tokens, atoms = _answer_metrics(ship["answer"])
    arms = {
        name: dict(_ORACLE_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    # Each interpolation costs 60 counted exact operations for this modulus;
    # trying all six already costs 360 before testing a non-anchor vertex.
    intended_operations = 360
    within_caps = chars <= 2000 and atoms <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": _ORACLE_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": atoms,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
