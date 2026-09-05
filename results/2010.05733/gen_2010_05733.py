"""Verified problem generator for arXiv:2010.05733.

The family uses the paper's Section 4 reduction from BICLIQUE COVER to
VC-k ROOT.  A cover is sampled first, its bipartite union is formed, and the
reduction graph is built around it.  The submitted certificate is an ordered
maximal-biclique cover; the verifier constructs the corresponding graph root,
squares it exactly with integer bitsets, and compares it with the instance.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family is stdlib-only anyway
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "finite simple graph specified by the paper's VC-k Root gadget",
        "bipartite adjacency matrix",
    ],
    "verification_operations": [
        "exact bitset biclique and maximality checks",
        "exact graph-root construction",
        "exact distance-at-most-two graph squaring",
        "bit-for-bit adjacency comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Lemma 6 (polynomial reduction from Biclique Cover to "
        "VC-k Root, with the forward proof constructing the square root)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The cross-edge matrix is a Boolean union of a small number of maximal "
        "rectangles, and those rectangles are precisely the neighborhoods of "
        "the Z vertices in the square root."
    ),
    "hardness_basis": (
        "Track A: Section 4, Theorem 5 rules out "
        "2^(2^o(k))*n^O(1) algorithms for VC-k Root under ETH when k grows; "
        "the shipping distribution uses 13 balanced planted rectangles on "
        "26+26 bipartite vertices (root vertex-cover bound 17), and a "
        "maximal-biclique DPLL attack exhausts "
        "2,000,000 nodes on 0/8 solved shipping instances (the theorem is "
        "worst-case, so the measured distributional evidence is stated separately)."
    ),
    "max_answer_tokens": 202,
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
    "demo": {"n": 2, "k": 2, "rectangle_size": 1},
    "easy": {"n": 16, "k": 8, "rectangle_size": 4},
    "medium": {"n": 26, "k": 13, "rectangle_size": 6},
    "hard": {"n": 36, "k": 16, "rectangle_size": 7},
}
SHIPPING_DIFFICULTY = "medium"

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered length-k list of inclusion-maximal nonempty bicliques of "
        "the displayed bipartite graph.  Each biclique is a pair of 0/1 strings "
        "of lengths |X| and |Y|; repeated bicliques are allowed."
    ),
    "bounds": {
        "n_bicliques": 13,
        "left_bits_per_biclique": 26,
        "right_bits_per_biclique": 26,
        "alphabet": "{0,1}",
        "max_atomic_strings": 26,
    },
}

STRUCTURAL_HINT = (
    "The useful objects are the inclusion-maximal all-one rectangles of the "
    "displayed bipartite adjacency matrix."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the displayed rows and columns helps avoid small "
    "indexing mistakes in the certificate."
)

G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}

NOTES = """\
Sections 1--3 fix the exact problem: H is a square root when H^2=G,
and deleting a k-vertex modulator must leave p isolated vertices plus q disjoint
edges.  Section 3, Theorem 2 and Corollary 2 identify the easy regime: the
problem is FPT in k, with running time 2^(2^O(k))*n^O(1), so the non-demo
difficulty ladder grows k with the instance.  Section 4, Lemma 6 is the
construction used here.  Its
forward proof turns a k-biclique cover into a square root whose vertex cover is
Z union {u,v,u',v'}, and its reverse proof recovers a cover from every root.
Theorem 5 supplies the ETH lower bound for growing k.

The certificate is not found by the generator: k balanced rectangles are drawn
first, their Boolean union B is formed, each rectangle is enlarged to a maximal
biclique, and Lemma 6 carries that cover into H.  The profile-size outlier,
degree-star, largest-rectangle, deterministic greedy, and randomized greedy
attacks all fail because planted rectangles and the many emergent rectangles
come from the same union.  The domain attack enumerates all maximal bicliques
and runs a capped exact DPLL set-cover search; at shipping size it fails on all
eight seeds after two million nodes each.  The bare oracle solved easy once in
three attempts, while medium failed in all three and is the shipping preset.
"""


_CONCEPT_CACHE: dict[tuple, tuple[tuple[int, int], ...]] = {}


def _bits(mask: int, length: int) -> str:
    """Bit i is character i; this intentionally uses little-endian display."""
    return "".join("1" if (mask >> i) & 1 else "0" for i in range(length))


def _mask(text: str) -> int:
    out = 0
    for i, ch in enumerate(text):
        if ch == "1":
            out |= 1 << i
    return out


def _iter_set(mask: int):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask -= bit


def _add_edge(adj: list[int], u: int, v: int) -> None:
    if u == v:
        raise ValueError("loops are not allowed")
    adj[u] |= 1 << v
    adj[v] |= 1 << u


def _add_clique(adj: list[int], vertices) -> None:
    vs = list(vertices)
    for i, u in enumerate(vs):
        for v in vs[i + 1:]:
            _add_edge(adj, u, v)


def _common_y(rows: tuple[int, ...] | list[int], p: int, q: int,
              xmask: int) -> int:
    common = (1 << q) - 1
    for i in _iter_set(xmask):
        if i >= p:
            return 0
        common &= rows[i]
    return common


def _common_x(rows: tuple[int, ...] | list[int], p: int, q: int,
              ymask: int) -> int:
    return sum(1 << i for i, row in enumerate(rows)
               if row & ymask == ymask)


def _maximalize(rows: tuple[int, ...] | list[int], p: int, q: int,
                xmask: int, ymask: int) -> tuple[int, int]:
    """Enlarge a known biclique to a formal-concept/maximal biclique."""
    if not xmask or not ymask or ymask & ~_common_y(rows, p, q, xmask):
        raise ValueError("the seed pair is not a nonempty biclique")
    yclosed = _common_y(rows, p, q, xmask)
    xclosed = _common_x(rows, p, q, yclosed)
    yclosed = _common_y(rows, p, q, xclosed)
    return xclosed, yclosed


def _maximal_bicliques_from_rows(rows: tuple[int, ...], p: int,
                                 q: int) -> tuple[tuple[int, int], ...]:
    """Enumerate formal concepts by Ganter's Next-Closure algorithm."""
    cache_key = (rows, p, q)
    cached = _CONCEPT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    full_x = (1 << p) - 1

    def close(xmask: int) -> tuple[int, int]:
        ymask = _common_y(rows, p, q, xmask)
        if not ymask:
            return full_x, 0
        return _common_x(rows, p, q, ymask), ymask

    current = close(0)[0]
    found = []
    while True:
        closed, ymask = close(current)
        if current and ymask:
            # current is closed by construction.  Keep the assertion cheap and
            # local because this routine defines the candidate language.
            if closed != current:
                raise AssertionError("Next-Closure emitted a non-closed set")
            found.append((current, ymask))
        for i in range(p - 1, -1, -1):
            if not ((current >> i) & 1):
                prefix = current & ((1 << i) - 1)
                nxt, _ = close(prefix | (1 << i))
                if nxt & ((1 << i) - 1) == prefix:
                    current = nxt
                    break
        else:
            answer = tuple(sorted(set(found)))
            _CONCEPT_CACHE[cache_key] = answer
            return answer


def _build_reduction_graph(p: int, q: int, k: int,
                           rows: list[int]) -> tuple[list[int], dict]:
    """Build G exactly as in Section 4, Lemma 6, before relabelling."""
    x = list(range(p))
    y = list(range(p, p + q))
    z = list(range(p + q, p + q + k))
    base = p + q + k
    special = {"u": base, "v": base + 1, "w": base + 2,
               "up": base + 3, "vp": base + 4, "wp": base + 5}
    adj = [0] * (base + 6)
    _add_clique(adj, x + z + [special["u"]])
    _add_clique(adj, x + [special["v"]])
    _add_clique(adj, [special["u"], special["v"], special["w"]])
    _add_clique(adj, y + z + [special["up"]])
    _add_clique(adj, y + [special["vp"]])
    _add_clique(adj, [special["up"], special["vp"], special["wp"]])
    for i, row in enumerate(rows):
        for j in _iter_set(row):
            _add_edge(adj, x[i], y[j])
    return adj, {"X": x, "Y": y, "Z": z, "special": special}


def _relabel_adj(adj: list[int], perm: list[int]) -> list[int]:
    out = [0] * len(adj)
    for old_u, row in enumerate(adj):
        for old_v in _iter_set(row):
            if old_u < old_v:
                _add_edge(out, perm[old_u], perm[old_v])
    return out


def _square(adj: list[int]) -> list[int]:
    out = []
    for u, row in enumerate(adj):
        reach = row
        for v in _iter_set(row):
            reach |= adj[v]
        reach &= ~(1 << u)
        out.append(reach)
    return out


def _answer_from_pairs(pairs, p: int, q: int) -> list[list[str]]:
    return [[_bits(a, p), _bits(b, q)] for a, b in pairs]


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a certified instance of the paper's VC-k Root gadget."""
    p = q = int(n)
    k = int(params.get("k", max(2, n // 2)))
    rectangle_size = int(params.get("rectangle_size", max(1, n // 4)))
    if p < 1:
        raise ValueError("n must be positive")
    if k < 1:
        raise ValueError("k must be positive")
    if not 1 <= rectangle_size <= n:
        raise ValueError("rectangle_size must lie in 1..n")

    rng = random.Random(seed)
    full = (1 << n) - 1
    planted = None
    # Rejection sampling treats every rectangle identically.  Full vertex
    # participation is required by the forward construction in Lemma 6.
    for _ in range(100_000):
        trial = []
        used_x = used_y = 0
        for _j in range(k):
            a = sum(1 << i for i in rng.sample(range(n), rectangle_size))
            b = sum(1 << i for i in rng.sample(range(n), rectangle_size))
            trial.append((a, b))
            used_x |= a
            used_y |= b
        if used_x == full and used_y == full:
            planted = trial
            break
    if planted is None:
        raise ValueError("parameters make full vertex participation too unlikely")

    rows = [0] * n
    for a, b in planted:
        for i in _iter_set(a):
            rows[i] |= b
    maximal_cover = [_maximalize(rows, n, n, a, b) for a, b in planted]

    graph, roles = _build_reduction_graph(n, n, k, rows)
    vertex_count = len(graph)
    perm = list(range(vertex_count))
    rng.shuffle(perm)
    graph = _relabel_adj(graph, perm)
    x = [perm[v] for v in roles["X"]]
    y = [perm[v] for v in roles["Y"]]
    z = [perm[v] for v in roles["Z"]]
    special = {name: perm[v] for name, v in roles["special"].items()}

    inst = {
        "n": n,
        "left_size": n,
        "right_size": n,
        "k": k,
        "rectangle_size": rectangle_size,
        "vertex_count": vertex_count,
        "b_rows": rows,
        "g_adj": graph,
        "X": x,
        "Y": y,
        "Z": z,
        "special": special,
        "designated_cover": z + [special["u"], special["v"],
                                  special["up"], special["vp"]],
        "answer": _answer_from_pairs(maximal_cover, n, n),
    }
    # This assertion only checks the carried certificate; it never searches.
    ok, reason = verify(inst, inst["answer"])
    if not ok:
        raise AssertionError(f"construction bug: {reason}")
    return inst


def render(inst) -> str:
    p, q, k = inst["left_size"], inst["right_size"], inst["k"]
    rows = "\n".join(f"  X{i:02d}: {_bits(row, q)}"
                     for i, row in enumerate(inst["b_rows"]))
    example = [["1" + "0" * (p - 1), "1" + "0" * (q - 1)]
               for _ in range(k)]
    text = f"""VC-(k+4) graph square root via maximal bicliques

All graphs here are finite, simple, undirected graphs.  The square H^2 of a
graph H has the same vertices as H, and two distinct vertices are adjacent in
H^2 exactly when their distance in H is at most two.

The input graph G has the ordered vertex groups
  X = {inst['X']}
  Y = {inst['Y']}
  Z = {inst['Z']}
and six further vertices
  u={inst['special']['u']}, v={inst['special']['v']}, w={inst['special']['w']},
  u'={inst['special']['up']}, v'={inst['special']['vp']}, w'={inst['special']['wp']}.

Within this statement, Xi means the i-th vertex in the displayed X list, and
Yj means the j-th vertex in the displayed Y list (indices start at 0).
The X-Y edges are the 1 entries of this {p}-by-{q} matrix; character j of row i
is 1 exactly when XiYj is an edge:
{rows}

All remaining edges of G are defined as follows, with no other edges present:
X union Z union {{u}} is a clique; X union {{v}} is a clique; {{u,v,w}} is a
clique; Y union Z union {{u'}} is a clique; Y union {{v'}} is a clique; and
{{u',v',w'}} is a clique.  (A clique contains every edge between distinct
vertices in the named set.)

A biclique is a pair (A,D) of nonempty subsets A of X and D of Y for which
every possible A-D edge is present.  It is inclusion-maximal when no vertex of
X can be added to A and no vertex of Y can be added to D while preserving that
property.

Find an ordered list C0,...,C{k-1} of exactly {k} inclusion-maximal bicliques
whose union covers every X-Y edge.  Repeated bicliques are allowed.  By the
construction, Ci specifies the neighbors in X union Y of Zi in a square root H;
the fixed root edges are uv, vw, u'v', v'w', all u-X edges, all u'-Y edges,
and every edge inside Z.  Thus your list is a compact matrix certificate for a
square root whose designated vertex cover is Z union {{u,v,u',v'}}.

Give your final answer inside <answer></answer> tags as a JSON array of exactly
{k} pairs [x_bits,y_bits].  Each x_bits is a {p}-character 0/1 string whose
character i selects Xi; each y_bits is a {q}-character 0/1 string whose
character j selects Yj.  Order inside each bitstring is exactly the displayed
order, both strings must select at least one vertex, and the outer order is the
Z order.  Example of the required shape (not asserted to solve this instance):
<answer>{json.dumps(example, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text):
    """Parse the last delimited JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    payload = blocks[-1].strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload,
                         flags=re.IGNORECASE)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _decode_and_validate(inst, answer):
    k, p, q = inst["k"], inst["left_size"], inst["right_size"]
    if not isinstance(answer, list):
        return None, "answer must be a JSON array"
    if not answer:
        return None, "answer is empty"
    if len(answer) < k:
        return None, f"answer has too few bicliques: {len(answer)} < {k}"
    if len(answer) > k:
        return None, f"answer has too many bicliques: {len(answer)} > {k}"
    rows = inst["b_rows"]
    pairs = []
    for t, pair in enumerate(answer):
        if not isinstance(pair, list) or len(pair) != 2:
            return None, f"biclique {t} must be a two-element JSON array"
        xs, ys = pair
        if not isinstance(xs, str) or not isinstance(ys, str):
            return None, f"biclique {t} entries must be bitstrings"
        if len(xs) != p:
            return None, f"left bitstring in biclique {t} has length {len(xs)}, not {p}"
        if len(ys) != q:
            return None, f"right bitstring in biclique {t} has length {len(ys)}, not {q}"
        if re.fullmatch(r"[01]+", xs) is None or re.fullmatch(r"[01]+", ys) is None:
            return None, f"biclique {t} contains a character other than 0 or 1"
        a, b = _mask(xs), _mask(ys)
        if not a or not b:
            return None, f"biclique {t} has an empty side"
        common_y = _common_y(rows, p, q, a)
        if b & ~common_y:
            return None, f"biclique {t} contains a missing X-Y edge"
        common_x = _common_x(rows, p, q, b)
        if common_y != b or common_x != a:
            return None, f"biclique {t} is not inclusion-maximal"
        pairs.append((a, b))
    return pairs, "ok"


def _construct_root(inst, pairs) -> list[int]:
    adj = [0] * inst["vertex_count"]
    x, y, z = inst["X"], inst["Y"], inst["Z"]
    s = inst["special"]
    for u, v in ((s["u"], s["v"]), (s["v"], s["w"]),
                 (s["up"], s["vp"]), (s["vp"], s["wp"])):
        _add_edge(adj, u, v)
    for v in x:
        _add_edge(adj, s["u"], v)
    for v in y:
        _add_edge(adj, s["up"], v)
    _add_clique(adj, z)
    for zi, (a, b) in zip(z, pairs):
        for i in _iter_set(a):
            _add_edge(adj, zi, x[i])
        for j in _iter_set(b):
            _add_edge(adj, zi, y[j])
    return adj


def verify(inst, answer):
    """Accept every valid maximal-biclique certificate; never read the plant."""
    pairs, reason = _decode_and_validate(inst, answer)
    if pairs is None:
        return False, reason
    covered = [0] * inst["left_size"]
    for a, b in pairs:
        for i in _iter_set(a):
            covered[i] |= b
    if covered != inst["b_rows"]:
        missing = sum((want & ~got).bit_count()
                      for want, got in zip(inst["b_rows"], covered))
        return False, f"the bicliques leave {missing} X-Y edges uncovered"
    root = _construct_root(inst, pairs)
    cover_mask = sum(1 << v for v in inst["designated_cover"])
    for u, row in enumerate(root):
        if not ((cover_mask >> u) & 1) and row & ~cover_mask:
            return False, f"designated set fails to cover a root edge at vertex {u}"
    squared = _square(root)
    if squared != inst["g_adj"]:
        bad = next(i for i, (a, b) in enumerate(zip(squared, inst["g_adj"]))
                   if a != b)
        return False, f"constructed H^2 differs from G at vertex {bad}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform sample from ordered k-tuples of maximal bicliques."""
    concepts = _maximal_bicliques_from_rows(
        tuple(inst["b_rows"]), inst["left_size"], inst["right_size"])
    pairs = [concepts[rng.randrange(len(concepts))] for _ in range(inst["k"])]
    return _answer_from_pairs(pairs, inst["left_size"], inst["right_size"])


def search_space(inst):
    concepts = _maximal_bicliques_from_rows(
        tuple(inst["b_rows"]), inst["left_size"], inst["right_size"])
    return len(concepts) ** inst["k"]


def enumerate_all(inst):
    concepts = _maximal_bicliques_from_rows(
        tuple(inst["b_rows"]), inst["left_size"], inst["right_size"])
    total = len(concepts) ** inst["k"]
    if total > 200_000:
        return None
    hits = 0
    for choice in itertools.product(range(len(concepts)), repeat=inst["k"]):
        answer = _answer_from_pairs([concepts[i] for i in choice],
                                    inst["left_size"], inst["right_size"])
        hits += int(verify(inst, answer)[0])
    return hits


def _transpose_rows(rows: list[int], p: int, q: int) -> list[int]:
    return [sum(1 << i for i, row in enumerate(rows) if (row >> j) & 1)
            for j in range(q)]


def _wl_signature(rows: list[int], p: int, q: int) -> str:
    """A strong, relabelling-invariant 1-WL signature of a bipartite graph."""
    columns = _transpose_rows(rows, p, q)
    colors = [0] * p + [1] * q
    for _ in range(p + q + 1):
        signatures = []
        for i, row in enumerate(rows):
            signatures.append((colors[i], tuple(sorted(
                colors[p + j] for j in _iter_set(row)))))
        for j, col in enumerate(columns):
            signatures.append((colors[p + j], tuple(sorted(
                colors[i] for i in _iter_set(col)))))
        palette = {sig: c for c, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        if new_colors == colors:
            break
        colors = new_colors
    features = []
    for i, row in enumerate(rows):
        features.append((0, colors[i], row.bit_count(), tuple(sorted(
            colors[p + j] for j in _iter_set(row)))))
    for j, col in enumerate(columns):
        features.append((1, colors[p + j], col.bit_count(), tuple(sorted(
            colors[i] for i in _iter_set(col)))))
    edge_color_counts = {}
    for i, row in enumerate(rows):
        for j in _iter_set(row):
            key = (colors[i], colors[p + j])
            edge_color_counts[key] = edge_color_counts.get(key, 0) + 1
    return repr((p, q, sorted(features), sorted(edge_color_counts.items())))


def canonical_key(inst):
    """Ignore X/Y/Z order, graph labels, and the symmetry exchanging sides."""
    p, q = inst["left_size"], inst["right_size"]
    direct = _wl_signature(inst["b_rows"], p, q)
    transposed_rows = _transpose_rows(inst["b_rows"], p, q)
    swapped = _wl_signature(transposed_rows, q, p)
    normal = repr((inst["k"], min(direct, swapped)))
    return hashlib.sha256(normal.encode()).hexdigest()


def escalate(params):
    """Grow the bipartite haystack at fixed certificate atom count."""
    old = dict(params)
    n = int(old.get("n", 36))
    k = int(old.get("k", 16))
    r = int(old.get("rectangle_size", 7))
    new_n = math.ceil(n * 1.10)
    # Keeping k fixed keeps the answer at 2k atomic strings.  Scale rectangle
    # width to hold edge density and full-participation probability steady.
    new_r = max(r + 1, round(r * new_n / n))
    predicted_chars = 2 * k * new_n + 12 * k + 2
    predicted_route_ops = 2 * k * new_r + k
    if predicted_chars > 1_950 or predicted_route_ops > 300:
        return "cap_bound"
    return {"n": new_n, "k": k, "rectangle_size": new_r}


# --- Adversarial and invariance helpers used only by selftest ---------------

def _edge_bitset(a: int, b: int, q: int) -> int:
    out = 0
    for i in _iter_set(a):
        out |= b << (i * q)
    return out


def _target_edges(inst) -> int:
    out = 0
    q = inst["right_size"]
    for i, row in enumerate(inst["b_rows"]):
        out |= row << (i * q)
    return out


def _selection_covers(inst, concepts, indices) -> bool:
    covered = 0
    q = inst["right_size"]
    for idx in indices:
        covered |= _edge_bitset(*concepts[idx], q)
    return covered == _target_edges(inst)


def _cheap_attack_results(inst, rng):
    concepts = _maximal_bicliques_from_rows(
        tuple(inst["b_rows"]), inst["left_size"], inst["right_size"])
    q, k, r = inst["right_size"], inst["k"], inst["rectangle_size"]
    covers = [_edge_bitset(a, b, q) for a, b in concepts]
    target = _target_edges(inst)

    profile = sorted(range(len(concepts)), key=lambda i: (
        abs(concepts[i][0].bit_count() - r)
        + abs(concepts[i][1].bit_count() - r),
        -covers[i].bit_count(), i))[:k]
    largest = sorted(range(len(concepts)),
                     key=lambda i: (-covers[i].bit_count(), i))[:k]

    # Degree stars are what a solver gets by anchoring on conspicuous rows or
    # columns and immediately closing to a maximal biclique.
    star_pairs = set()
    rows = inst["b_rows"]
    p = inst["left_size"]
    for i in sorted(range(p), key=lambda x: -rows[x].bit_count())[:k]:
        star_pairs.add(_maximalize(rows, p, q, 1 << i, rows[i]))
    columns = _transpose_rows(rows, p, q)
    for j in sorted(range(q), key=lambda y: -columns[y].bit_count())[:k]:
        star_pairs.add(_maximalize(rows, p, q, columns[j], 1 << j))
    concept_index = {pair: i for i, pair in enumerate(concepts)}
    stars = sorted((concept_index[pair] for pair in star_pairs),
                   key=lambda i: (-covers[i].bit_count(), i))[:k]
    if stars:
        stars += [stars[-1]] * (k - len(stars))

    def greedy(randomized=False):
        done = 0
        choice = []
        for _ in range(k):
            gains = [(cover & ~done).bit_count() for cover in covers]
            order = sorted(range(len(concepts)),
                           key=lambda i: (-gains[i], i))
            idx = rng.choice(order[:min(12, len(order))]) if randomized else order[0]
            choice.append(idx)
            done |= covers[idx]
            if done == target:
                break
        return done == target, choice

    greedy_ok, greedy_choice = greedy(False)
    restart_ok = False
    restart_choice = []
    for _ in range(64):
        ok, choice = greedy(True)
        if ok:
            restart_ok, restart_choice = True, choice
            break

    return {
        "outlier_planted_size_profile": _selection_covers(inst, concepts, profile),
        "degree_star_closures": bool(stars) and _selection_covers(inst, concepts, stars),
        "largest_area_concepts": _selection_covers(inst, concepts, largest),
        "greedy_max_uncovered": greedy_ok and _selection_covers(
            inst, concepts, greedy_choice),
        "randomized_greedy_64": restart_ok and _selection_covers(
            inst, concepts, restart_choice),
    }


def _dpll_attack(inst, node_cap=2_000_000):
    """Exact maximal-biclique set cover, capped after node_cap search nodes."""
    start = time.perf_counter()
    concepts = _maximal_bicliques_from_rows(
        tuple(inst["b_rows"]), inst["left_size"], inst["right_size"])
    q = inst["right_size"]
    covers = [_edge_bitset(a, b, q) for a, b in concepts]
    target = _target_edges(inst)
    by_edge = [[] for _ in range(inst["left_size"] * q)]
    for ci, cover in enumerate(covers):
        for e in _iter_set(cover):
            by_edge[e].append(ci)
    nodes = 0
    path = []
    memo = set()

    def dfs(done: int, depth: int):
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            return None
        if done == target:
            return path[:]
        if depth == inst["k"]:
            return False
        state = (done, depth)
        if state in memo:
            return False
        remaining = target & ~done
        options = None
        scan = remaining
        while scan:
            bit = scan & -scan
            scan -= bit
            here = by_edge[bit.bit_length() - 1]
            if options is None or len(here) < len(options):
                options = here
        options = sorted(options or (),
                         key=lambda i: (covers[i] & remaining).bit_count(),
                         reverse=True)
        if not options:
            return False
        for ci in options:
            path.append(ci)
            result = dfs(done | covers[ci], depth + 1)
            if isinstance(result, list):
                return result
            path.pop()
            if nodes > node_cap:
                return None
        memo.add(state)
        return False

    solution = dfs(0, 0)
    elapsed = time.perf_counter() - start
    verified = False
    if isinstance(solution, list):
        answer = _answer_from_pairs([concepts[i] for i in solution]
                                    + [concepts[solution[-1]]]
                                    * (inst["k"] - len(solution)),
                                    inst["left_size"], inst["right_size"])
        verified = verify(inst, answer)[0]
    return {
        "success": verified,
        "nodes": nodes,
        "node_cap": node_cap,
        "wall_clock_sec": elapsed,
        "maximal_bicliques": len(concepts),
        "exhausted_cap": solution is None,
    }


def _ordered_transform(inst, x_order, y_order, z_order, swap=False):
    """Reorder role lists (and optionally exchange gadget halves)."""
    out = {key: value for key, value in inst.items()
           if key not in ("X", "Y", "Z", "special", "designated_cover",
                          "b_rows", "answer")}
    old_rows = inst["b_rows"]
    new_rows = []
    for old_i in x_order:
        new_rows.append(sum(1 << new_j for new_j, old_j in enumerate(y_order)
                            if (old_rows[old_i] >> old_j) & 1))
    transformed_answer = []
    for pair in inst["answer"]:
        transformed_answer.append([
            "".join(pair[0][i] for i in x_order),
            "".join(pair[1][j] for j in y_order),
        ])
    transformed_answer = [transformed_answer[i] for i in z_order]
    out["X"] = [inst["X"][i] for i in x_order]
    out["Y"] = [inst["Y"][j] for j in y_order]
    out["Z"] = [inst["Z"][i] for i in z_order]
    out["special"] = dict(inst["special"])
    out["b_rows"] = new_rows
    out["answer"] = transformed_answer
    if swap:
        out["X"], out["Y"] = out["Y"], out["X"]
        out["left_size"], out["right_size"] = (
            out["right_size"], out["left_size"])
        out["b_rows"] = _transpose_rows(
            out["b_rows"], len(x_order), len(y_order))
        out["answer"] = [[pair[1], pair[0]] for pair in out["answer"]]
        s = out["special"]
        out["special"] = {"u": s["up"], "v": s["vp"], "w": s["wp"],
                          "up": s["u"], "vp": s["v"], "wp": s["w"]}
    s = out["special"]
    out["designated_cover"] = out["Z"] + [s["u"], s["v"], s["up"], s["vp"]]
    return out


def _vertex_relabelled(inst, rng):
    out = {key: value for key, value in inst.items()
           if key not in ("g_adj", "X", "Y", "Z", "special",
                          "designated_cover", "answer")}
    perm = list(range(inst["vertex_count"]))
    rng.shuffle(perm)
    out["g_adj"] = _relabel_adj(inst["g_adj"], perm)
    out["X"] = [perm[v] for v in inst["X"]]
    out["Y"] = [perm[v] for v in inst["Y"]]
    out["Z"] = [perm[v] for v in inst["Z"]]
    out["special"] = {name: perm[v] for name, v in inst["special"].items()}
    s = out["special"]
    out["designated_cover"] = out["Z"] + [s["u"], s["v"], s["up"], s["vp"]]
    out["answer"] = [pair[:] for pair in inst["answer"]]
    return out


def _answer_token_measure(answer) -> int:
    # The corpus cap equates 2000 characters with about 500 tokens.  Binary
    # strings tokenize favorably; char/4 is a stable conservative proxy here.
    return math.ceil(len(json.dumps(answer)) / 4)


def selftest():
    report = {"paper": "2010.05733", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY}

    planted = 0
    failures = []
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted += int(ok)
            if not ok:
                failures.append(f"{name}/{seed}: {reason}")
    report["G1_planted_verifies"] = {
        "pass": planted == 12, "verified": planted, "attempts": 12,
        "failures": failures,
    }

    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = ship["answer"]
    swapped = [[a, b] for a, b in answer]
    swap_done = False
    for t, pair in enumerate(swapped):
        ones = [i for i, ch in enumerate(pair[0]) if ch == "1"]
        zeros = [i for i, ch in enumerate(pair[0]) if ch == "0"]
        if ones and zeros:
            chars = list(pair[0])
            chars[ones[0]], chars[zeros[0]] = chars[zeros[0]], chars[ones[0]]
            swapped[t] = ["".join(chars), pair[1]]
            swap_done = True
            break
    if not swap_done:
        raise AssertionError("shipping answer has no swappable membership bits")
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [[answer[0][0] + "1", answer[0][1]]]
                        + [[a, b] for a, b in answer[1:]],
    }
    rejected = {}
    for name, bad in corruptions.items():
        ok, reason = verify(ship, bad)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = {result["reason"] for result in rejected.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in rejected.values())
                and len(reasons) == len(corruptions),
        "cases": rejected,
        "distinct_reasons": len(reasons),
    }

    realistic = ("I used the maximal rectangles of the matrix.\n```json\n"
                 + "<answer>" + json.dumps(answer) + "</answer>\n```")
    parsed = parse_answer(realistic)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "parsed_matches": parsed == answer,
        "json_native": json_native,
    }

    density_inst = make_instance(seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY])
    density_rng = random.Random(0x201005733)
    samples = 200_000
    hits = 0
    density_concepts = _maximal_bicliques_from_rows(
        tuple(density_inst["b_rows"]), density_inst["left_size"],
        density_inst["right_size"])
    density_covers = [_edge_bitset(a, b, density_inst["right_size"])
                      for a, b in density_concepts]
    density_target = _target_edges(density_inst)
    density_start = time.perf_counter()
    for _ in range(samples):
        covered = 0
        for _j in range(density_inst["k"]):
            covered |= density_covers[density_rng.randrange(len(density_covers))]
        hits += int(covered == density_target)
    density_wall = time.perf_counter() - density_start
    # Cross-check that the indexed sampler and the public string-valued sampler
    # really inhabit the same verified language.
    cross_rng = random.Random(0xC0FFEE)
    density_cross_checks = sum(
        _decode_and_validate(density_inst,
                             random_candidate(density_inst, cross_rng))[0] is not None
        for _ in range(32)
    )
    probability = hits / samples
    concepts_at_shipping = len(density_concepts)
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "structure_aware_language": (
            f"ordered {density_inst['k']}-tuples sampled uniformly from "
            f"{concepts_at_shipping} maximal bicliques"
        ),
        "exact_language_size": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
        "public_sampler_language_cross_checks": f"{density_cross_checks}/32",
    }

    attack_names = [
        "outlier_planted_size_profile", "degree_star_closures",
        "largest_area_concepts", "greedy_max_uncovered",
        "randomized_greedy_64", "dpll_maximal_biclique_2000000",
    ]
    attack_successes = {name: 0 for name in attack_names}
    dpll_nodes = []
    dpll_times = []
    dpll_concepts = []
    attempts = 8
    for seed in range(20, 20 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        cheap = _cheap_attack_results(inst, random.Random(90_000 + seed))
        for name, success in cheap.items():
            attack_successes[name] += int(success)
        dpll = _dpll_attack(inst)
        attack_successes["dpll_maximal_biclique_2000000"] += int(
            dpll["success"])
        dpll_nodes.append(dpll["nodes"])
        dpll_times.append(dpll["wall_clock_sec"])
        dpll_concepts.append(dpll["maximal_bicliques"])
    attacks = {
        name: {"successes": attack_successes[name], "attempts": attempts}
        for name in attack_names
    }
    attacks["dpll_maximal_biclique_2000000"].update({
        "mean_nodes": round(sum(dpll_nodes) / attempts),
        "node_cap": 2_000_000,
        "mean_wall_clock_sec": round(sum(dpll_times) / attempts, 6),
        "max_wall_clock_sec": round(max(dpll_times), 6),
        "maximal_bicliques_range": [min(dpll_concepts), max(dpll_concepts)],
    })
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": (
            "exact set-cover DPLL over all inclusion-maximal bicliques"
        ),
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and demo_count > 0
                and hits == 0
                and attack_successes["dpll_maximal_biclique_2000000"] == 0,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": probability,
        "demo_exact_valid_answer_count": demo_count,
        "baseline_name": "maximal-biclique DPLL",
        "baseline_mean_nodes": round(sum(dpll_nodes) / attempts),
        "baseline_node_cap": 2_000_000,
        "baseline_mean_wall_clock_sec": round(sum(dpll_times) / attempts, 6),
        "baseline_max_wall_clock_sec": round(max(dpll_times), 6),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["rectangle_size"] *= 2
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * ship["n"]
                and len(doubled["answer"]) == len(answer),
        "original_n": ship["n"],
        "doubled_n": doubled["n"],
        "answer_atomic_strings_before": 2 * len(answer),
        "answer_atomic_strings_after": 2 * len(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    invariant_passed = 0
    invariant_attempted = 0
    transformed_verified = 0
    unrelated_keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(123_000 + seed)
        xo = list(range(inst["left_size"]))
        yo = list(range(inst["right_size"]))
        zo = list(range(inst["k"]))
        rng.shuffle(xo)
        rng.shuffle(yo)
        rng.shuffle(zo)
        x_only = _ordered_transform(inst, xo, list(range(inst["right_size"])),
                                    list(range(inst["k"])))
        y_only = _ordered_transform(inst, list(range(inst["left_size"])), yo,
                                    list(range(inst["k"])))
        z_only = _ordered_transform(inst, list(range(inst["left_size"])),
                                    list(range(inst["right_size"])), zo)
        swapped_inst = _ordered_transform(
            inst, list(range(inst["left_size"])),
            list(range(inst["right_size"])), list(range(inst["k"])), True)
        relabelled = _vertex_relabelled(inst, rng)
        composed = _vertex_relabelled(
            _ordered_transform(inst, xo, yo, zo, True), rng)
        base_key = canonical_key(inst)
        for changed in (x_only, y_only, z_only, swapped_inst,
                        relabelled, composed):
            invariant_attempted += 1
            invariant_passed += int(canonical_key(changed) == base_key)
        transformed_verified += int(verify(composed, composed["answer"])[0])
        unrelated_keys.append(base_key)
    report["G8_canonical_key"] = {
        "pass": invariant_passed == invariant_attempted
                and transformed_verified == 20
                and len(set(unrelated_keys)) == 20,
        "invariance_checks_passed": invariant_passed,
        "invariance_checks_attempted": invariant_attempted,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "canonicalization_caveat": (
            "1-WL is a strong invariant, not a complete bipartite-isomorphism test"
        ),
    }

    blob = json.dumps(answer)
    answer_elements = sum(len(pair) for pair in answer)
    selected_incidences = sum(pair[0].count("1") + pair[1].count("1")
                              for pair in answer)
    intended_ops = selected_incidences + ship["k"]
    arms = G9_RESULTS["arms"]
    complete = all(arms[name]["attempts"] >= 3
                   for name in ("bare", "hinted", "placebo"))
    difference = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        difference = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    within_caps = (len(blob) <= 2_000 and answer_elements <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "arms_complete": complete,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": _answer_token_measure(answer),
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "operation_definition": (
            "one membership placement per selected X/Y incidence plus one "
            "rectangle-union operation per biclique after the decomposition insight"
        ),
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
