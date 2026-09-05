"""Verified problem generator for arXiv:2212.14814.

The paper's Theorem 8 locates a nested t-module from three pairs of vertices
whose neighborhood contrasts expose three nested cotree cuts.  This module
inverse-generates exactly that native object.  It first constructs a cograph,
then flips t pairs across all three cuts.  The six cut anchors are retained as
the witness; they are never recovered by solving the finished instance.

The verifier does not read ``inst["answer"]``.  It reconstructs the five parts,
checks the definition of a nested t-module exactly, derives Reduction Rule 4's
edits, applies them, and recognizes the resulting cograph.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "simple graph",
        "cotree neighborhood cuts",
        "nested t-module",
        "cograph edge-edit set",
    ],
    "verification_operations": [
        "exact neighborhood symmetric difference",
        "exact module edit-distance count",
        "set containment and adjacency checks",
        "exact cograph recognition by graph/complement decomposition",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Three pairs with complementary neighborhoods expose nested cotree cuts; "
        "without seeing those contrasts, one must mechanically search anchor sextuples."
    ),
    "hardness_basis": (
        "Track B, Theorem 8 and its proof: the paper detects a nested t-module "
        "by guessing six vertices in O(n^6) time; at shipping n=52, the memoized "
        "form solves 8/8 in 1,077,875.5 counted operations on average (0.014 "
        "seconds in the builder run), while the compact route uses three "
        "neighborhood contrasts and at most 168 exact adjacency/set operations."
    ),
    "max_answer_tokens": 8,
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
        "A JSON list of three ordered-by-depth anchor pairs [[x,x'],[y,y'],[z,z']]; "
        "each pair is written in increasing vertex order and all six 0-based vertex "
        "indices are distinct."
    ),
    "bounds": {
        "pairs": 3,
        "vertices": 6,
        "index_min": 0,
        "index_max": "n-1",
        "pair_order": "increasing",
        "depth_order": "inner, middle, outer",
        "maximum_supported_n": 200,
    },
}

DIFFICULTY = {
    "demo": {"n": 22, "t": 1, "scramble": False},
    "easy": {"n": 52, "t": 2, "scramble": True},
    "medium": {"n": 68, "t": 2, "scramble": True},
    "hard": {"n": 84, "t": 2, "scramble": True},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Look for three vertex pairs whose neighborhood contrasts are strictly nested cotree cuts."
)
PLACEBO_HINT = (
    "Keep the vertex indexing and the required order of the three pairs in view."
)

# Replaced with the script-owned measurements after the three oracle runs.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted": {"solved": 1, "attempts": 3, "error_calls": 0},
    "placebo": {"solved": 1, "attempts": 3, "error_calls": 0},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and native objects.  Section 2 defines a cograph as a graph with no
induced P4, equivalently a graph represented by a cotree, and defines edge
editing by symmetric difference.  Section 4 defines a t-module and a nested
t-module (the ordered partition A,B,C,K,I), and Reduction Rule 4 edits every
A--I edge and every A--K nonedge.  Lemma 3 proves that rule safe.

Step 0 and the easy boundary.  This is not a Track-A claim.  Theorem 8 in
Section 6 states that the nested t-module is polynomial-time detectable.  Its
proof guesses three cut pairs (six vertices), recovers each descendant set by
neighborhood contrast, and explicitly gives O(n^6) enumeration.  Corollary 10
then gives the O(k^2 log k)-vertex kernel.  The paper also says k<559 may be
handled by brute force, and fixed k is FPT after kernelization.  Those facts
make small-budget worst-case rhetoric inappropriate for this distribution.

Construction.  A binary cotree chain is assembled from the groups A0,A1,
B-plus,B-join,C-plus,C-join,K,I.  Two unedited vertices on each side of the
first three cotree cuts have complementary neighborhoods across exactly A,
A union B, and A union B union C.  The K and I subgraphs are independent random
cographs and supply decoys.  Finally t pairs from A to K or I are toggled.  The
same t toggles cross all three nested cuts and reversing them restores the
known cograph.  Thus the certificate is known before the noisy graph exists.

Verification.  For an anchor pair u,v, its cut is {u,v} union (N(u) symmetric
difference N(v)).  The three cuts determine A,B,C; the first anchor separates
the exterior into K and I.  The checker computes the exact minimum number of
cut edits needed to make each nested set a module, constructs all four buffer
sets from the paper's definition, derives Rule 4's edits, and recognizes the
edited graph recursively by disconnected graph/complement decomposition.

Attacks.  Degree extremes, largest contrast pairs, the most frequent contrast
patterns, a label-order/by-hand ansatz, and random restarts are tested.  The
Track-B reference separately memoizes all pair contrasts and enumerates nested
triples, which is the six-anchor search from Theorem 8 with repeated work
removed.  The planted cut pairs are drawn from the same two-vertex pools on
both sides of each cut; no single distinguished planted vertex is introduced.
""".strip()


def _add_edge(rows: list[int], u: int, v: int) -> None:
    if u == v:
        return
    rows[u] |= 1 << v
    rows[v] |= 1 << u


def _toggle_edge(rows: list[int], u: int, v: int) -> None:
    rows[u] ^= 1 << v
    rows[v] ^= 1 << u


def _join(rows: list[int], left: list[int], right: list[int]) -> None:
    for u in left:
        for v in right:
            _add_edge(rows, u, v)


def _random_cograph(rows: list[int], vertices: list[int], rng: random.Random) -> None:
    """Add edges of a random binary-cotree cograph on ``vertices``."""
    if len(vertices) <= 1:
        return
    work = list(vertices)
    rng.shuffle(work)
    split = rng.randrange(1, len(work))
    left, right = work[:split], work[split:]
    _random_cograph(rows, left, rng)
    _random_cograph(rows, right, rng)
    if rng.randrange(2):
        _join(rows, left, right)


def _anchored_piece(rows: list[int], vertices: list[int]) -> list[int]:
    """A cograph with two isolated anchors and a clique of decoys."""
    anchors = vertices[:2]
    body = vertices[2:]
    for i, u in enumerate(body):
        for v in body[i + 1:]:
            _add_edge(rows, u, v)
    return anchors


def _relabel_rows(rows: list[int], old_to_new: list[int]) -> list[int]:
    n = len(rows)
    result = [0] * n
    for u in range(n):
        nu = old_to_new[u]
        mask = rows[u]
        while mask:
            bit = mask & -mask
            v = bit.bit_length() - 1
            if u < v:
                _add_edge(result, nu, old_to_new[v])
            mask ^= bit
    return result


def _complement_rows(rows: list[int]) -> list[int]:
    all_vertices = (1 << len(rows)) - 1
    return [all_vertices ^ rows[v] ^ (1 << v) for v in range(len(rows))]


def make_instance(n: int, seed: int = 0, t: int = 2,
                  scramble: bool = True, **params: Any) -> dict:
    """Inverse-generate a noisy cograph with a known six-anchor certificate."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or not 22 <= n <= 200:
        raise ValueError("n must be an integer in [22,200]")
    if isinstance(t, bool) or not isinstance(t, int) or not 1 <= t <= 4:
        raise ValueError("t must be an integer in [1,4]")
    q = 3 * t + 1
    a_size = 4 if t == 1 else q + 3
    minimum = a_size + 4 * q + 2
    if n < minimum:
        raise ValueError(f"n must be at least {minimum} when t={t}")

    rng = random.Random(seed)
    rows = [0] * n
    cursor = 0

    def take(count: int) -> list[int]:
        nonlocal cursor
        out = list(range(cursor, cursor + count))
        cursor += count
        return out

    a0_size = a_size // 2
    A0 = take(a0_size)
    A1 = take(a_size - a0_size)
    Bjoin = take(q)
    Bplus = take(q)
    Cjoin = take(q)
    Cplus = take(q)
    outside = n - cursor
    K = take(outside // 2)
    I = take(outside - len(K))

    anchors0 = _anchored_piece(rows, A0)
    anchors1 = _anchored_piece(rows, A1)
    anchors_bj = _anchored_piece(rows, Bjoin)
    anchors_bp = _anchored_piece(rows, Bplus)
    anchors_cj = _anchored_piece(rows, Cjoin)
    anchors_cp = _anchored_piece(rows, Cplus)
    _random_cograph(rows, K, rng)
    _random_cograph(rows, I, rng)

    A = A0 + A1
    B = Bjoin + Bplus
    C = Cjoin + Cplus
    AB = A + B
    ABC = AB + C

    _join(rows, A0, A1)
    _join(rows, Bjoin, A + Bplus)
    _join(rows, Cjoin, AB + Cplus)
    _join(rows, ABC, K)

    chosen = [
        [rng.choice(anchors0), rng.choice(anchors1)],
        [rng.choice(anchors_bj), rng.choice(anchors_bp)],
        [rng.choice(anchors_cj), rng.choice(anchors_cp)],
    ]
    # Preserve both planted choices on each side of the innermost cut.  This
    # is what makes the memoized reference search complete for the declared
    # distribution; the actual returned answer still chooses only one pair.
    protected = set(anchors0 + anchors1)
    noise_a = [v for v in A if v not in protected]
    if not noise_a:  # the minimal t=1 demo has only its four anchor-pool vertices
        noise_a = [v for v in A if v not in set(chosen[0])]
    rng.shuffle(noise_a)
    used: set[tuple[int, int]] = set()
    for edit_index in range(t):
        u = noise_a[edit_index % len(noise_a)]
        target_group = K if (edit_index + rng.randrange(2)) % 2 == 0 else I
        choices = list(target_group)
        rng.shuffle(choices)
        for v in choices:
            pair = (min(u, v), max(u, v))
            if pair not in used:
                used.add(pair)
                _toggle_edge(rows, u, v)
                break

    if scramble:
        permutation = list(range(n))
        rng.shuffle(permutation)
        rows = _relabel_rows(rows, permutation)
        chosen = [[permutation[u], permutation[v]] for u, v in chosen]
        if rng.randrange(2):
            rows = _complement_rows(rows)

    answer = [sorted(pair) for pair in chosen]
    return {
        "n": n,
        "k": t,
        "t": t,
        "rows": rows,
        "answer": answer,
    }


def _row_string(row: int, n: int) -> str:
    return "".join("1" if (row >> j) & 1 else "0" for j in range(n))


def render(inst: dict) -> str:
    """Render a self-contained nested-module/cograph-editing problem."""
    n = inst["n"]
    matrix = "\n".join(f"{i:>3}: {_row_string(row, n)}"
                       for i, row in enumerate(inst["rows"]))
    statement = f"""Find a six-vertex certificate for a nested t-module cograph edit.

The input is a simple undirected graph G on the 0-based vertices 0,...,{n - 1}.
Its adjacency matrix is displayed below: character j of row i is 1 exactly when
vertices i and j are adjacent.  The diagonal is 0 and the matrix is symmetric.

For a vertex v, N(v) is its set of neighbors.  For two distinct vertices u,v,
define their contrast cut

  D(u,v) = {{u,v}} union (N(u) symmetric-difference N(v)).

Return three anchor pairs [[x,x'],[y,y'],[z,z']].  They define

  A = D(x,x'),
  A union B = D(y,y'),
  A union B union C = D(z,z').

These three sets must be strictly nested.  The remaining vertices are split as
K = neighbors of x outside A union B union C, and I = the other outside
vertices.  Thus A,B,C,K,I must be five nonempty, pairwise-disjoint sets covering
all vertices.

A set X is a t-module when at most t adjacencies across the cut (X,V(G)-X)
must be toggled to make every vertex of X have the same neighbors outside X.
Equivalently, for each outside vertex w let d_w be its number of neighbors in X;
X is a t-module exactly when sum_w min(d_w, |X|-d_w) <= t.

Here t={inst['t']} and k={inst['k']}.  Your anchors are valid only if all of the
following hold:

1. A, A union B, and A union B union C are t-modules, and |A| > k+t.
2. At least 3t+1 vertices b in B are adjacent to every vertex of A and K and
   to no vertex of I.
3. At least 3t+1 other vertices b in B are adjacent to every vertex of K and
   to no vertex of A or I.
4. At least 3t+1 vertices c in C are adjacent to every vertex of A union B and
   K and to no vertex of I.
5. At least 3t+1 other vertices c in C are adjacent to every vertex of K and
   to no vertex of A union B or I.

The nested t-module rule toggles every existing A--I edge and every missing
A--K edge.  For this task those derived toggles must be nonempty, use at most k
pairs, and the resulting graph must be a cograph.  A cograph means a graph with
no induced path on four vertices (no four vertices whose induced subgraph is
exactly a three-edge path).

All six anchor indices must be distinct.  Within each pair write the smaller
index first.  The three pairs are ordered inner, middle, outer as above; pair
order is not interchangeable.  No repeated indices are allowed.

Adjacency matrix:
{matrix}

Give your final answer inside <answer></answer> tags as JSON in the exact form
[[x,x'],[y,y'],[z,z']], with three pairs and six 0-based integer indices.
Example: <answer>[[2,9],[4,17],[6,21]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON certificate, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:json|text)?\s*", "", payload,
                     flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value


def _contrast(rows: list[int], u: int, v: int) -> int:
    return (rows[u] ^ rows[v]) | (1 << u) | (1 << v)


def _module_distance(rows: list[int], subset: int, limit: int | None = None) -> int:
    n = len(rows)
    outside = ((1 << n) - 1) ^ subset
    size = subset.bit_count()
    total = 0
    mask = outside
    while mask:
        bit = mask & -mask
        v = bit.bit_length() - 1
        degree = (rows[v] & subset).bit_count()
        total += min(degree, size - degree)
        if limit is not None and total > limit:
            return total
        mask ^= bit
    return total


def _components(rows: list[int], subset: int, complement: bool) -> list[int]:
    components: list[int] = []
    remaining = subset
    while remaining:
        seed = remaining & -remaining
        component = seed
        frontier = seed
        remaining ^= seed
        while frontier:
            bit = frontier & -frontier
            frontier ^= bit
            v = bit.bit_length() - 1
            if complement:
                neighbors = subset & ~rows[v] & ~(1 << v)
            else:
                neighbors = subset & rows[v]
            new = neighbors & remaining
            remaining ^= new
            component |= new
            frontier |= new
        components.append(component)
    return components


def _is_cograph(rows: list[int]) -> bool:
    """Exact cotree recognition via graph/complement disconnection."""
    stack = [(1 << len(rows)) - 1]
    while stack:
        subset = stack.pop()
        if subset.bit_count() <= 1:
            continue
        parts = _components(rows, subset, False)
        if len(parts) > 1:
            stack.extend(parts)
            continue
        parts = _components(rows, subset, True)
        if len(parts) > 1:
            stack.extend(parts)
            continue
        return False
    return True


def _derived(inst: dict, pairs: list[list[int]]) -> tuple[dict[str, int] | None, str]:
    rows = inst["rows"]
    first, second, third = pairs
    A = _contrast(rows, first[0], first[1])
    AB = _contrast(rows, second[0], second[1])
    ABC = _contrast(rows, third[0], third[1])
    if A == AB or (A & ~AB):
        return None, "the first two anchor contrast sets are not strictly nested"
    if AB == ABC or (AB & ~ABC):
        return None, "the last two anchor contrast sets are not strictly nested"
    all_mask = (1 << inst["n"]) - 1
    outside = all_mask ^ ABC
    B = AB ^ A
    C = ABC ^ AB
    K = outside & rows[first[0]]
    I = outside ^ K
    if not all((A, B, C, K, I)):
        return None, "the derived A,B,C,K,I partition has an empty part"
    return {"A": A, "B": B, "C": C, "K": K, "I": I,
            "AB": AB, "ABC": ABC}, "ok"


def _iter_vertices(mask: int):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def _buffer_count(rows: list[int], pool: int, joined: int, antijoined: int) -> int:
    count = 0
    for v in _iter_vertices(pool):
        if (rows[v] & joined) == joined and not (rows[v] & antijoined):
            count += 1
    return count


def _forced_edits(rows: list[int], A: int, K: int, I: int) -> list[tuple[int, int]]:
    edits: list[tuple[int, int]] = []
    for a in _iter_vertices(A):
        for v in _iter_vertices(I):
            if (rows[a] >> v) & 1:
                edits.append((min(a, v), max(a, v)))
        for v in _iter_vertices(K):
            if not ((rows[a] >> v) & 1):
                edits.append((min(a, v), max(a, v)))
    return sorted(set(edits))


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid six-anchor witness without consulting the planted one."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 3:
        return False, "expected exactly three anchor pairs"
    pairs: list[list[int]] = []
    flat: list[int] = []
    for pair in answer:
        if not isinstance(pair, list) or len(pair) != 2:
            return False, "each anchor pair must contain exactly two indices"
        if any(isinstance(v, bool) or not isinstance(v, int) for v in pair):
            return False, "anchor indices must be integers"
        if any(v < 0 or v >= inst["n"] for v in pair):
            return False, "anchor index out of range"
        if pair[0] >= pair[1]:
            return False, "each anchor pair must be in strictly increasing order"
        pairs.append(pair)
        flat.extend(pair)
    if len(set(flat)) != 6:
        return False, "the six anchor vertices must be distinct"

    parts, reason = _derived(inst, pairs)
    if parts is None:
        return False, reason
    A, B, C = parts["A"], parts["B"], parts["C"]
    K, I, AB, ABC = parts["K"], parts["I"], parts["AB"], parts["ABC"]
    k, t = inst["k"], inst["t"]
    if A.bit_count() <= k + t:
        return False, "the derived set A does not satisfy |A| > k+t"
    for name, subset in (("A", A), ("A union B", AB),
                         ("A union B union C", ABC)):
        distance = _module_distance(inst["rows"], subset, t)
        if distance > t:
            return False, f"{name} is not a t-module"

    rows = inst["rows"]
    q = 3 * t + 1
    counts = (
        ("B-join buffer", _buffer_count(rows, B, A | K, I)),
        ("B-union buffer", _buffer_count(rows, B, K, A | I)),
        ("C-join buffer", _buffer_count(rows, C, AB | K, I)),
        ("C-union buffer", _buffer_count(rows, C, K, AB | I)),
    )
    for name, count in counts:
        if count < q:
            return False, f"{name} has fewer than 3t+1 vertices"

    edits = _forced_edits(rows, A, K, I)
    if not edits:
        return False, "the nested t-module rule derives no edit"
    if len(edits) > k:
        return False, "the nested t-module rule derives more than k edits"
    edited_rows = list(rows)
    for u, v in edits:
        _toggle_edge(edited_rows, u, v)
    if not _is_cograph(edited_rows):
        return False, "the derived rule edits do not produce a cograph"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the bounded language of canonical six-anchor tuples."""
    vertices = rng.sample(range(inst["n"]), 6)
    return [sorted(vertices[i:i + 2]) for i in (0, 2, 4)]


def search_space(inst: dict) -> int:
    """Number of ordered triples of disjoint unordered vertex pairs."""
    n = inst["n"]
    product = 1
    for value in range(n - 5, n + 1):
        product *= value
    return product // 8


def enumerate_all(inst: dict) -> int | None:
    """Exact enumeration only below a conservative two-million-candidate cap."""
    space = search_space(inst)
    if space > 2_000_000:
        return None
    hits = 0
    n = inst["n"]
    for a in range(n):
        for b in range(a + 1, n):
            remaining1 = [v for v in range(n) if v not in (a, b)]
            for c_index, c in enumerate(remaining1):
                for d in remaining1[c_index + 1:]:
                    remaining2 = [v for v in remaining1 if v not in (c, d)]
                    for e_index, e in enumerate(remaining2):
                        for f in remaining2[e_index + 1:]:
                            if verify(inst, [[a, b], sorted([c, d]),
                                             sorted([e, f])])[0]:
                                hits += 1
    return hits


def _wl_payload(rows: list[int]) -> str:
    n = len(rows)
    colors = [row.bit_count() for row in rows]
    while True:
        signatures = []
        for v in range(n):
            neighbor_colors = sorted(colors[w] for w in _iter_vertices(rows[v]))
            signatures.append((colors[v], tuple(neighbor_colors)))
        palette = {signature: index for index, signature
                   in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        if new_colors == colors:
            break
        colors = new_colors
    classes: dict[int, list[int]] = {}
    for v, color in enumerate(colors):
        classes.setdefault(color, []).append(v)
    ordered = [classes[color] for color in sorted(classes)]
    sizes = [len(group) for group in ordered]
    edge_counts: list[int] = []
    for i, left in enumerate(ordered):
        for j in range(i, len(ordered)):
            right = ordered[j]
            count = sum((rows[u] >> v) & 1 for u in left for v in right)
            if i == j:
                count //= 2
            edge_counts.append(count)
    return json.dumps([sizes, edge_counts], separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    """A complement-invariant 1-WL quotient signature (strong cheap invariant)."""
    rows = inst["rows"]
    payload = min(_wl_payload(rows), _wl_payload(_complement_rows(rows)))
    framed = json.dumps([inst["k"], inst["t"], payload], separators=(",", ":"))
    return hashlib.sha256(framed.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the decoy region at fixed six-index answer length."""
    current = dict(params)
    n = int(current.get("n", 52))
    next_n = n + 8
    if 3 * next_n + 12 > 300:
        return "cap_bound"
    current["n"] = next_n
    current["scramble"] = True
    return current


def _answer_from_pair_sequence(inst: dict, sequence: list[tuple[int, int]]) -> list[list[int]]:
    pairs = [tuple(sorted(pair)) for pair in sequence]
    pairs.sort(key=lambda pair: _contrast(inst["rows"], pair[0], pair[1]).bit_count())
    return [[u, v] for u, v in pairs]


def _attack_degree_extremes(inst: dict) -> object:
    order = sorted(range(inst["n"]), key=lambda v: (inst["rows"][v].bit_count(), v))
    pairs = [(order[i], order[-1 - i]) for i in range(3)]
    return _answer_from_pair_sequence(inst, pairs)


def _all_pairs_by_contrast(inst: dict) -> list[tuple[int, int, int, int]]:
    out = []
    rows = inst["rows"]
    for u in range(inst["n"]):
        for v in range(u + 1, inst["n"]):
            cut = _contrast(rows, u, v)
            out.append((cut.bit_count(), u, v, cut))
    return out


def _attack_largest_contrasts(inst: dict) -> object:
    pairs = sorted(_all_pairs_by_contrast(inst), reverse=True)
    chosen: list[tuple[int, int]] = []
    used: set[int] = set()
    for _, u, v, _ in pairs:
        if u not in used and v not in used:
            chosen.append((u, v))
            used.update((u, v))
            if len(chosen) == 3:
                break
    return _answer_from_pair_sequence(inst, chosen)


def _attack_frequent_contrasts(inst: dict) -> object:
    groups: dict[int, list[tuple[int, int]]] = {}
    for _, u, v, cut in _all_pairs_by_contrast(inst):
        groups.setdefault(cut, []).append((u, v))
    masks = sorted(groups, key=lambda cut: (-len(groups[cut]), cut.bit_count(), cut))
    chosen: list[tuple[int, int]] = []
    used: set[int] = set()
    for cut in masks:
        for u, v in groups[cut]:
            if u not in used and v not in used:
                chosen.append((u, v))
                used.update((u, v))
                break
        if len(chosen) == 3:
            break
    return _answer_from_pair_sequence(inst, chosen)


def _attack_first_rows(inst: dict) -> object:
    return _answer_from_pair_sequence(inst, [(0, 1), (2, 3), (4, 5)])


def _pick_disjoint_representatives(groups: list[list[tuple[int, int]]]) -> list[tuple[int, int]] | None:
    for p0 in groups[0]:
        used0 = set(p0)
        for p1 in groups[1]:
            if used0.intersection(p1):
                continue
            used1 = used0 | set(p1)
            for p2 in groups[2]:
                if not used1.intersection(p2):
                    return [p0, p1, p2]
    return None


def _reference_solve(inst: dict) -> tuple[object | None, dict[str, int | float]]:
    """Memoized implementation of the proof's six-anchor enumeration."""
    start = time.perf_counter()
    n, t, k = inst["n"], inst["t"], inst["k"]
    q = 3 * t + 1
    groups: dict[int, list[tuple[int, int]]] = {}
    operations = 0
    for u in range(n):
        for v in range(u + 1, n):
            cut = 0
            for w in range(n):
                operations += 1
                if w in (u, v) or (((inst["rows"][u] >> w) & 1)
                                    != ((inst["rows"][v] >> w) & 1)):
                    cut |= 1 << w
            if k + t < cut.bit_count() <= n - 2:
                groups.setdefault(cut, []).append((u, v))

    # The declared distribution plants two clean anchors on each side of every
    # cut, so its three target signatures each occur at least four times.
    candidates = [cut for cut, pairs in groups.items() if len(pairs) >= 4]
    candidates.sort(key=lambda cut: (cut.bit_count(), cut))
    chains_tested = 0
    validations = 0
    for A in candidates:
        if A.bit_count() <= k + t:
            continue
        for AB in candidates:
            operations += n
            if A == AB or (A & ~AB) or (AB ^ A).bit_count() < 2 * q:
                continue
            for ABC in candidates:
                operations += n
                if AB == ABC or (AB & ~ABC) or (ABC ^ AB).bit_count() < 2 * q:
                    continue
                if n - ABC.bit_count() < 2:
                    continue
                chains_tested += 1
                reps = _pick_disjoint_representatives(
                    [groups[A], groups[AB], groups[ABC]])
                if reps is None:
                    continue
                answer = [[u, v] for u, v in reps]
                validations += 1
                if verify(inst, answer)[0]:
                    elapsed = time.perf_counter() - start
                    return answer, {
                        "operations": operations,
                        "pair_signatures": n * (n - 1) // 2,
                        "repeated_signatures": len(candidates),
                        "chains_tested": chains_tested,
                        "validations": validations,
                        "wall_clock_sec": elapsed,
                    }
    elapsed = time.perf_counter() - start
    return None, {
        "operations": operations,
        "pair_signatures": n * (n - 1) // 2,
        "repeated_signatures": len(candidates),
        "chains_tested": chains_tested,
        "validations": validations,
        "wall_clock_sec": elapsed,
    }


def _relabel_instance(inst: dict, old_to_new: list[int]) -> tuple[dict, list[list[int]]]:
    transformed = {
        "n": inst["n"],
        "k": inst["k"],
        "t": inst["t"],
        "rows": _relabel_rows(inst["rows"], old_to_new),
    }
    carried = [sorted([old_to_new[u], old_to_new[v]])
               for u, v in inst["answer"]]
    transformed["answer"] = carried
    return transformed, carried


def _complement_instance(inst: dict) -> dict:
    return {
        "n": inst["n"],
        "k": inst["k"],
        "t": inst["t"],
        "rows": _complement_rows(inst["rows"]),
        "answer": [list(pair) for pair in inst["answer"]],
    }


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run the nine mandatory gates and return their measured report."""
    report: dict[str, Any] = {
        "paper": "2212.14814",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=1701, **params)
    answer = [list(pair) for pair in inst["answer"]]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_one": [answer[1], answer[0], answer[2]],
        "duplicate_one": [[answer[0][0], answer[0][1]],
                          sorted([answer[0][0], answer[1][1]]), answer[2]],
        "empty": [],
        "out_of_range": [[answer[0][0], inst["n"]], answer[1], answer[2]],
    }
    g2_cases = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        g2_cases[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in g2_cases.values())
                and len(set(reasons)) == len(g2_cases),
        "distinct_reasons": len(set(reasons)),
        "cases": g2_cases,
    }

    model_style = ("I compared the three cuts.\n```json\n<answer>\n"
                   + json.dumps(answer) + "\n</answer>\n```\nThese are 0-based.")
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed": parsed,
    }

    guess_rng = random.Random(991827)
    guess_total = 250_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "candidate_space": search_space(inst),
        "sampler": "uniform ordered triples of disjoint canonical unordered pairs",
    }

    reference_runs = []
    attack_names = {
        "outlier_degree_extremes": _attack_degree_extremes,
        "greedy_largest_contrasts": _attack_largest_contrasts,
        "frequency_top_contrasts": _attack_frequent_contrasts,
        "by_hand_first_six_rows": _attack_first_rows,
    }
    attack_results = {name: {"successes": 0, "attempts": 8}
                      for name in attack_names}
    attack_results["random_restart_256"] = {"successes": 0, "attempts": 8}
    for seed in range(800, 808):
        trial = make_instance(seed=seed, **params)
        found, metrics = _reference_solve(trial)
        metrics = dict(metrics)
        metrics["solved"] = bool(found is not None and verify(trial, found)[0])
        reference_runs.append(metrics)
        for name, attack in attack_names.items():
            candidate = attack(trial)
            if verify(trial, candidate)[0]:
                attack_results[name]["successes"] += 1
        restart_rng = random.Random(seed ^ 0xC0A4)
        solved = any(verify(trial, random_candidate(trial, restart_rng))[0]
                     for _ in range(256))
        if solved:
            attack_results["random_restart_256"]["successes"] += 1

    ref_solved = sum(bool(run["solved"]) for run in reference_runs)
    mean_wall = sum(float(run["wall_clock_sec"]) for run in reference_runs) / 8
    max_wall = max(float(run["wall_clock_sec"]) for run in reference_runs)
    mean_ops = sum(int(run["operations"]) for run in reference_runs) / 8
    max_ops = max(int(run["operations"]) for run in reference_runs)
    mean_signatures = sum(int(run["pair_signatures"]) for run in reference_runs) / 8
    report["G5_density_and_baseline"] = {
        "pass": ref_solved == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_observed_fraction": guess_hits / guess_total,
        "shipping_structure_aware_space": search_space(inst),
        "shipping_valid_solution_count": None,
        "baseline_wall_clock_sec_mean": mean_wall,
        "baseline_wall_clock_sec_max": max_wall,
        "baseline_operations_mean": mean_ops,
        "baseline_operations_max": max_ops,
        "baseline_pair_signatures_mean": mean_signatures,
    }
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_solved == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "memoized six-anchor neighborhood-contrast enumeration",
            "paper_route": "Theorem 8 proof, O(n^6) over six guessed vertices",
            "complexity": "O(n^3 + r^3 n) on memoized pair signatures; O(n^6) worst case",
            "wall_clock_sec_mean": mean_wall,
            "wall_clock_sec_max": max_wall,
            "operations_mean": mean_ops,
            "operations_max": max_ops,
            "pair_signatures_mean": mean_signatures,
            "solves": f"{ref_solved}/8, as expected",
        },
    }

    doubled_params = dict(params)
    doubled_params["n"] = 2 * params["n"]
    doubled = make_instance(seed=4321, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_space": search_space(inst),
        "doubled_space": search_space(doubled),
        "answer_elements_shipping": _answer_atoms(inst["answer"]),
        "answer_elements_doubled": _answer_atoms(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    g8_failures = []
    unrelated_keys = set()
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **params)
        key = canonical_key(original)
        unrelated_keys.add(key)
        prng = random.Random(50_000 + seed)
        permutation = list(range(original["n"]))
        prng.shuffle(permutation)
        relabelled, carried = _relabel_instance(original, permutation)
        complemented = _complement_instance(original)
        composed, composed_answer = _relabel_instance(complemented, permutation)
        for name, transformed, witness in (
            ("permutation", relabelled, carried),
            ("complement", complemented, original["answer"]),
            ("composed", composed, composed_answer),
        ):
            if canonical_key(transformed) != key:
                g8_failures.append({"seed": seed, "transform": name,
                                    "reason": "key changed"})
            ok, reason = verify(transformed, witness)
            if not ok:
                g8_failures.append({"seed": seed, "transform": name,
                                    "reason": reason})
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(unrelated_keys) == 20,
        "permutation_invariance_checks": 20,
        "complement_invariance_checks": 20,
        "composed_transformation_checks": 20,
        "real_transformation_checks": 60,
        "unrelated_attempts": 20,
        "unrelated_distinct": len(unrelated_keys),
        "failures": g8_failures,
        "caveat": "key is the strongest cheap 1-WL quotient invariant, not graph canonization",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _answer_atoms(inst["answer"])
    route_ops = 3 * inst["n"] + 12
    arms = {name: dict(G9_MEASUREMENTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_atoms <= 256 and route_ops <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": (answer_chars + 3) // 4,
        "answer_elements": answer_atoms,
        "intended_route_operations": route_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
