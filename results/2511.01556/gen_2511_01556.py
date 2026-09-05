"""Verified affine-cover certificates for removable edge sets.

This family is grounded in Section 2 and the proof of Theorem 1.2 of
arXiv:2511.01556.  A locally bijective projection of a cubic graph onto K4
induces a Z-flow-continuous edge map.  Removing the inverse image of one K4
edge and pulling back a fixed nowhere-zero 3-flow on K4 minus that edge gives
an exactly checkable 3-removable set of one sixth of the edges.

Instances are inverse generated from a hidden rank-two affine map over GF(2).
The answer is the matrix and offset of any affine K4-cover projection; it is a
compact matrix certificate, not a list of planted edges.  The module is
deterministic in (n, seed, params), standard-library only, and silent on import.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from collections import deque
from typing import Any


TRACK = "B"

_PAPER_CITATION = (
    "Section 2 (definition of Z-flow-continuous maps and Lemma 2.1), "
    "Theorem 2.2, and Section 3 (proof of Theorem 1.2)"
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "cubic graph with binary-coordinate vertex labels",
        "affine K4-cover projection",
        "Z-flow-continuous edge map",
        "integer 3-flow",
    ],
    "verification_operations": [
        "exact GF(2) matrix-vector products",
        "local graph-cover incidence checks",
        "exact integer flow conservation",
        "edge-fibre cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The XOR of the three coordinate differences incident to each vertex "
        "is annihilated by both rows of the hidden affine projection; without "
        "that invariant one must process the whole graph-cover constraint system."
    ),
    "hardness_basis": (
        "Track B: the domain-standard exact (-1)-eigenspace method uses modular "
        "Gaussian elimination in O(n^3) field operations and at shipping n=768 "
        "took 121,489,118 field operations and 8.461 seconds over eight measured "
        "seeds (at most 16,283,642 operations on one), whereas the coordinate-XOR "
        "change of variables and rank "
        "saturation on d+2 vertices took at most 213 packed exact operations."
    ),
    "max_answer_tokens": 24,
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
    "demo": {"n": 8, "coordinate_bits": 4},
    "easy": {"n": 192, "coordinate_bits": 16},
    "medium": {"n": 384, "coordinate_bits": 16},
    "hard": {"n": 768, "coordinate_bits": 16},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "XOR the three endpoint-difference vectors incident to a vertex: the two "
    "projection rows span the nullspace of those local signatures."
)
PLACEBO_HINT = (
    "Track the vertex coordinates and edge indices carefully: the requested "
    "certificate uses exact binary data throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object containing an ordered 2 by d full-row-rank matrix over "
        "GF(2) and a two-bit affine offset; every entry is exactly 0 or 1."
    ),
    "bounds": {
        "matrix_rows": 2,
        "max_coordinate_bits": 32,
        "offset_bits": 2,
        "entry_alphabet": 2,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 defines integer k-flows and k-removable
edge sets.  Section 2 defines Z-flow-continuous edge maps; Lemma 2.1 says that
deleting an edge set in the target and its full inverse image in the source
preserves flow continuity.  Theorem 2.2 characterizes graphs with a 4-NZF by a
map to K4.  Section 3 proves Theorem 1.2 by deleting a smallest K4 edge fibre
and pulling back a 3-NZF of K4-e.  The checker below executes that pullback and
checks conservation; it does not merely appeal to the theorem.

What is easy, and why this is Track B.  Section 1 gives an especially direct
construction for cubic graphs once a proper 3-edge-colouring is known: orient
two bicoloured 2-factors and compare their orientations.  Section 3 is also
linear once a flow-continuous map is supplied: count six fibres and pull back a
fixed five-edge flow.  Calling either formulation Track A would therefore be
false.  This family instead asks for a compact affine formula for the native
cover projection.  The domain-standard reference algorithm computes the exact
-1 eigenspace of the adjacency matrix: for a K4 cover, its three-dimensional
space of fibre-constant vectors lies in that eigenspace.  Modular Gaussian
elimination is polynomial and succeeds on the generated distribution.  The
intended compression is the extra coordinate XOR invariant and early rank
saturation, not a complexity-theoretic hardness claim.

Generation.  Two dense independent GF(2) row masks and an affine offset are
sampled first.  Equal numbers of distinct coordinate labels are drawn from the
four affine fibres.  Independent random perfect matchings join every pair of
fibres, producing a connected random lift of K4.  The matchings are resampled
until the first d+2 local XOR signatures already have rank d-2.  This condition
changes no certificate and searches only for an informative presentation; the
certificate was fixed before the graph existed.  Vertices, labels, and edges
are shuffled, so planted and non-planted edges are the same population.

Attacks.  The panel tests single-coordinate outliers, a no-backtracking greedy
K4-cover colouring followed by affine fitting, 256 uniform matrix restarts,
and the hand ansatz that the two least significant coordinate bits are the
projection.  Dense random row masks, random fibre labels, and random lift
matchings defeat those probes.  The successful exact adjacency-eigenspace
computation is honestly separated as Track B's reference algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000

# Patched after the three harness runs.  They are data, not claims used by the
# verifier or generator.
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
}
_G9_HINTED_VERDICT = "hardened"


def _parity(x: int) -> int:
    return x.bit_count() & 1


def _mask_to_row(mask: int, d: int) -> list[int]:
    return [(mask >> j) & 1 for j in range(d)]


def _row_to_mask(row: object, d: int) -> tuple[int | None, str | None]:
    if not isinstance(row, list) or len(row) != d:
        return None, f"each matrix row must contain exactly {d} bits"
    if any(isinstance(x, bool) or not isinstance(x, int) or x not in (0, 1)
           for x in row):
        return None, "every matrix entry must be the integer 0 or 1"
    return sum(x << j for j, x in enumerate(row)), None


def _rank(masks: list[int], d: int) -> int:
    basis: dict[int, int] = {}
    for value in masks:
        x = value
        while x:
            p = x.bit_length() - 1
            if p not in basis:
                basis[p] = x
                break
            x ^= basis[p]
    return len(basis)


def _rref_nullspace(rows: list[int], d: int) -> tuple[list[int], int]:
    """Return a GF(2) nullspace basis and packed row-XOR operation count."""
    work = [x & ((1 << d) - 1) for x in rows if x]
    rank = 0
    pivots: list[int] = []
    xor_ops = 0
    for col in range(d):
        pivot = next((i for i in range(rank, len(work))
                      if (work[i] >> col) & 1), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for i in range(len(work)):
            if i != rank and ((work[i] >> col) & 1):
                work[i] ^= work[rank]
                xor_ops += 1
        pivots.append(col)
        rank += 1
        if rank == len(work):
            break
    reduced = work[:rank]
    pivot_set = set(pivots)
    free = [j for j in range(d) if j not in pivot_set]
    nullspace: list[int] = []
    for free_col in free:
        x = 1 << free_col
        for row, pivot_col in zip(reduced, pivots):
            if _parity(row & x):
                x |= 1 << pivot_col
        nullspace.append(x)
    return nullspace, xor_ops


def _validate_params(n: int, coordinate_bits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 8 or n % 4:
        raise ValueError("n must be a multiple of 4 and at least 8")
    if (isinstance(coordinate_bits, bool)
            or not isinstance(coordinate_bits, int)):
        raise ValueError("coordinate_bits must be an integer")
    if coordinate_bits < 4 or coordinate_bits > 32:
        raise ValueError("coordinate_bits must lie in 4..32")
    if n // 4 > (1 << (coordinate_bits - 2)):
        raise ValueError("not enough labels in each affine fibre")
    if n < coordinate_bits + 2 and n != 8:
        raise ValueError("non-demo instances need at least d+2 vertices")


def _dense_independent_rows(rng: random.Random, d: int) -> tuple[int, int]:
    lo = max(1, d // 3)
    hi = min(d - 1, (2 * d + 2) // 3)
    while True:
        a = rng.randrange(1, 1 << d)
        b = rng.randrange(1, 1 << d)
        if a == b:
            continue
        if all(lo <= x.bit_count() <= hi for x in (a, b, a ^ b)):
            return a, b


def _is_connected(n: int, edges: list[tuple[int, int]]) -> bool:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = {0}
    stack = [0]
    while stack:
        for w in adj[stack.pop()]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen) == n


def _adjacency(inst: dict) -> list[list[int]]:
    adj = [[] for _ in range(inst["n"])]
    for u, v in inst["edges"]:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def _signatures(inst: dict, limit: int | None = None) -> tuple[list[int], int]:
    labels = inst["labels"]
    adj = _adjacency(inst)
    stop = len(labels) if limit is None else min(limit, len(labels))
    rows: list[int] = []
    xor_ops = 0
    for v in range(stop):
        value = labels[v]
        for w in adj[v]:
            value ^= labels[w]
            xor_ops += 1
        rows.append(value)
    return rows, xor_ops


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a graph and its affine K4-cover certificate."""
    allowed = {"coordinate_bits"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    d = params.get("coordinate_bits", 16)
    _validate_params(n, d)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    row0, row1 = _dense_independent_rows(rng, d)
    offset = rng.randrange(4)
    quota = n // 4
    fibres: list[list[int]] = [[] for _ in range(4)]
    used: set[int] = set()
    while any(len(part) < quota for part in fibres):
        label = rng.randrange(1 << d)
        if label in used:
            continue
        cls = (_parity(row0 & label) ^ (offset & 1))
        cls |= (_parity(row1 & label) ^ ((offset >> 1) & 1)) << 1
        if len(fibres[cls]) >= quota:
            continue
        fibres[cls].append(label)
        used.add(label)

    records = [(label, cls) for cls, part in enumerate(fibres)
               for label in part]
    rng.shuffle(records)
    labels = [label for label, _ in records]
    classes = [cls for _, cls in records]
    vertices = [[i for i, cls in enumerate(classes) if cls == c]
                for c in range(4)]
    probe = min(n, d + 2)

    edges: list[tuple[int, int]] | None = None
    for _attempt in range(2000):
        candidate: list[tuple[int, int]] = []
        for a in range(4):
            for b in range(a + 1, 4):
                left = vertices[a][:]
                right = vertices[b][:]
                rng.shuffle(left)
                rng.shuffle(right)
                candidate.extend(zip(left, right))
        rng.shuffle(candidate)
        trial = {
            "n": n,
            "coordinate_bits": d,
            "labels": labels,
            "edges": candidate,
        }
        signature_rows, _ = _signatures(trial, probe)
        if _is_connected(n, candidate) and _rank(signature_rows, d) == d - 2:
            edges = candidate
            break
    if edges is None:
        raise RuntimeError("could not generate a connected rank-saturated lift")

    answer = {
        "matrix": [_mask_to_row(row0, d), _mask_to_row(row1, d)],
        "offset": [offset & 1, (offset >> 1) & 1],
    }
    return {
        "family": "affine_K4_cover_removable_set",
        "paper_basis": _PAPER_CITATION,
        "n": n,
        "coordinate_bits": d,
        "probe_vertices": probe,
        "labels": labels,
        "edges": [list(edge) for edge in edges],
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a self-contained graph-cover and removable-flow problem."""
    n = inst["n"]
    d = inst["coordinate_bits"]
    vertex_rows = "\n".join(
        f"{i}: {x:0{d}b}" for i, x in enumerate(inst["labels"])
    )
    edge_rows = "\n".join(
        f"{i}: {u} {v}" for i, (u, v) in enumerate(inst["edges"])
    )
    statement = f"""Affine K4-cover certificate for a removable edge set

The undirected graph below has {n} vertices, indexed 0 through {n - 1}, and
{len(inst['edges'])} edges, indexed 0 through {len(inst['edges']) - 1}.  It is
simple, connected, and cubic: every vertex has degree three.  Each vertex v
also carries a distinct vector x(v) in GF(2)^{d}.  In a displayed bit string,
the leftmost character is coordinate {d - 1} and the rightmost is coordinate 0.

Find a two-row binary matrix A and a two-bit offset b.  For a vertex v define

  c(v) = A x(v) + b  in GF(2)^2,

where all sums and products are modulo 2.  Interpret [q0,q1] as the K4 vertex
q0 + 2*q1 in {{0,1,2,3}}.  Your map must be a K4-cover projection: for every
vertex v, the four values consisting of c(v) and the values on its three
neighbours must be exactly {{0,1,2,3}}.

Why this certifies the paper's removable-set claim is checked explicitly.
Every graph edge maps to the K4 edge joining its endpoint classes.  The checker
deletes all edges mapping to {{0,1}} and pulls back this fixed integer 3-flow on
K4-{{0,1}}, with each base edge oriented from its smaller to its larger endpoint:

  f(0,2)=1, f(0,3)=-1, f(1,2)=1, f(1,3)=-1, f(2,3)=2.

It then checks that the deleted fibre has at most one sixth of all edges, every
retained value is nonzero with absolute value at most 2, and the exact incoming
and outgoing sums agree at every source vertex.  Thus the answer is a compact
formula for a concrete removable set and a concrete nowhere-zero 3-flow, not an
existence assertion.

Vertex coordinates x(v):
{vertex_rows}

Edges (edge_index: endpoint endpoint):
{edge_rows}

Return one JSON object with exactly these fields:
  "matrix": two rows, each a JSON array of exactly {d} integer bits in
            coordinate order [0,1,...,{d - 1}];
  "offset": exactly two integer bits [b0,b1].
Rows must be distinct and nonzero (equivalently, full row rank over GF(2)).
Every bit must be the integer 0 or 1; booleans are not accepted.

Give your final answer inside <answer></answer> tags, as that one JSON object.
Syntax-only example for d=4: <answer>{{"matrix":[[1,0,1,0],[0,1,1,0]],"offset":[0,1]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON certificate; never raise on garbage."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _validate_instance(inst: dict) -> tuple[bool, str, list[list[int]] | None]:
    n = inst.get("n")
    d = inst.get("coordinate_bits")
    labels = inst.get("labels")
    edges = inst.get("edges")
    if (isinstance(n, bool) or not isinstance(n, int) or n < 4
            or isinstance(d, bool) or not isinstance(d, int) or d < 1):
        return False, "malformed instance dimensions", None
    if (not isinstance(labels, list) or len(labels) != n
            or any(isinstance(x, bool) or not isinstance(x, int)
                   or x < 0 or x >= (1 << d) for x in labels)
            or len(set(labels)) != n):
        return False, "malformed or repeated vertex coordinates", None
    if not isinstance(edges, list) or len(edges) != 3 * n // 2:
        return False, "malformed cubic edge list", None
    adj = [[] for _ in range(n)]
    seen: set[tuple[int, int]] = set()
    for edge in edges:
        if (not isinstance(edge, list) or len(edge) != 2
                or any(isinstance(v, bool) or not isinstance(v, int)
                       or v < 0 or v >= n for v in edge)):
            return False, "malformed edge endpoint", None
        u, v = edge
        if u == v:
            return False, "self-loops are not allowed", None
        pair = (min(u, v), max(u, v))
        if pair in seen:
            return False, "parallel edges are not allowed", None
        seen.add(pair)
        adj[u].append(v)
        adj[v].append(u)
    if any(len(row) != 3 for row in adj):
        return False, "instance is not cubic", None
    return True, "ok", adj


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid affine cover and its explicit pulled-back 3-flow."""
    if not isinstance(answer, dict):
        return False, "answer must be one JSON object"
    if set(answer) != {"matrix", "offset"}:
        return False, "answer must contain exactly matrix and offset"
    matrix = answer.get("matrix")
    offset = answer.get("offset")
    if not isinstance(matrix, list) or len(matrix) != 2:
        return False, "matrix must contain exactly two rows"
    d = inst.get("coordinate_bits")
    if not isinstance(d, int):
        return False, "malformed instance dimensions"
    masks: list[int] = []
    for row in matrix:
        mask, reason = _row_to_mask(row, d)
        if reason is not None:
            return False, reason
        assert mask is not None
        masks.append(mask)
    if masks[0] == 0 or masks[1] == 0 or masks[0] == masks[1]:
        return False, "the two matrix rows must be nonzero and linearly independent"
    if (not isinstance(offset, list) or len(offset) != 2
            or any(isinstance(x, bool) or not isinstance(x, int)
                   or x not in (0, 1) for x in offset)):
        return False, "offset must contain exactly two integer bits"

    ok, reason, adj = _validate_instance(inst)
    if not ok:
        return False, reason
    assert adj is not None
    labels = inst["labels"]
    classes = [
        (_parity(masks[0] & x) ^ offset[0])
        | ((_parity(masks[1] & x) ^ offset[1]) << 1)
        for x in labels
    ]
    expected = inst["n"] // 4
    counts = [classes.count(c) for c in range(4)]
    if counts != [expected] * 4:
        return False, "affine classes are not four equal fibres"
    for v, neighbours in enumerate(adj):
        if {classes[v], *(classes[w] for w in neighbours)} != {0, 1, 2, 3}:
            return False, f"closed neighbourhood of vertex {v} does not map bijectively to K4"

    # Execute Section 3's pullback for the fixed removed target edge {0,1}.
    base_flow = {
        (0, 2): 1,
        (0, 3): -1,
        (1, 2): 1,
        (1, 3): -1,
        (2, 3): 2,
    }
    balances = [0] * inst["n"]
    removed = 0
    fibre_counts = {(a, b): 0 for a in range(4) for b in range(a + 1, 4)}
    for u, v in inst["edges"]:
        a, b = classes[u], classes[v]
        if a == b:
            return False, "an edge collapsed under the proposed K4 map"
        pair = (min(a, b), max(a, b))
        fibre_counts[pair] += 1
        if pair == (0, 1):
            removed += 1
            continue
        value = base_flow.get(pair)
        if value is None or value == 0 or abs(value) > 2:
            return False, "pulled-back value is not a nowhere-zero 3-flow value"
        low_vertex = u if a < b else v
        high_vertex = v if a < b else u
        balances[low_vertex] += value
        balances[high_vertex] -= value
    if any(count != expected for count in fibre_counts.values()):
        return False, "edge fibres do not all have the cover size n/4"
    if 6 * removed > len(inst["edges"]):
        return False, "removed fibre exceeds one sixth of the edges"
    if any(balance != 0 for balance in balances):
        return False, "pulled-back integer flow violates conservation"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample full-rank matrices and offsets from the stated language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    d = inst["coordinate_bits"]
    a = rng.randrange(1, 1 << d)
    b = rng.randrange(1, (1 << d) - 1)
    if b >= a:
        b += 1
    offset = rng.randrange(4)
    return {
        "matrix": [_mask_to_row(a, d), _mask_to_row(b, d)],
        "offset": [offset & 1, (offset >> 1) & 1],
    }


def search_space(inst: dict) -> int | None:
    """Exact size of the bounded, structure-aware certificate language."""
    d = inst["coordinate_bits"]
    return 4 * ((1 << d) - 1) * ((1 << d) - 2)


def enumerate_all(inst: dict) -> int | None:
    """Count all valid affine certificates when the language is small enough."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    d = inst["coordinate_bits"]
    hits = 0
    for a in range(1, 1 << d):
        for b in range(1, 1 << d):
            if a == b:
                continue
            for offset in range(4):
                candidate = {
                    "matrix": [_mask_to_row(a, d), _mask_to_row(b, d)],
                    "offset": [offset & 1, (offset >> 1) & 1],
                }
                if verify(inst, candidate)[0]:
                    hits += 1
    return hits


def canonical_key(inst: dict) -> str:
    """Strong cheap unlabeled-graph invariant, independent of coordinates.

    Sorted all-vertex distance histograms are invariant under vertex/edge
    reordering and every affine change of the auxiliary coordinate basis.  This
    is deliberately not a hash of the seed, rendered text, labels, or answer.
    It is not a complete cubic-graph isomorphism canonizer; that limitation is
    recorded in the README.
    """
    ok, reason, adj = _validate_instance(inst)
    if not ok or adj is None:
        raise ValueError(reason)
    profiles: list[tuple[int, ...]] = []
    n = inst["n"]
    for source in range(n):
        dist = [-1] * n
        dist[source] = 0
        queue = deque([source])
        while queue:
            v = queue.popleft()
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
        if any(x < 0 for x in dist):
            raise ValueError("canonical_key requires a connected graph")
        hist = [0] * (max(dist) + 1)
        for value in dist:
            hist[value] += 1
        profiles.append(tuple(hist))
    payload = json.dumps(sorted(profiles), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the graph at fixed answer length before increasing coordinate width."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    d = params.get("coordinate_bits", 16)
    if not isinstance(n, int) or not isinstance(d, int):
        return None
    out = dict(params)
    capacity = 1 << d
    if n < min(4096, capacity):
        out["n"] = min(4096, capacity, max(n + 4, 2 * n))
        out["n"] -= out["n"] % 4
        return out
    if d < 24:
        out["coordinate_bits"] = d + 2
        return out
    return "cap_bound"


def _decode_from_signatures(inst: dict, limit: int | None = None
                            ) -> tuple[dict | None, dict[str, int]]:
    rows, signature_xors = _signatures(inst, limit)
    basis, elimination_xors = _rref_nullspace(rows, inst["coordinate_bits"])
    stats = {
        "vertices_processed": len(rows),
        "signature_word_xors": signature_xors,
        "elimination_word_xors": elimination_xors,
        "packed_exact_operations": signature_xors + elimination_xors + 2 * inst["coordinate_bits"],
        "scalar_bit_operation_upper_bound": (
            (signature_xors + elimination_xors + 2 * inst["coordinate_bits"])
            * inst["coordinate_bits"]
        ),
    }
    if len(basis) != 2:
        return None, stats
    d = inst["coordinate_bits"]
    answer = {
        "matrix": [_mask_to_row(basis[0], d), _mask_to_row(basis[1], d)],
        "offset": [0, 0],
    }
    return answer, stats


def _modular_nullspace(matrix: list[list[int]], prime: int
                       ) -> tuple[list[list[int]], int]:
    """Exact forward elimination over GF(prime), with operation count."""
    if not matrix:
        return [], 0
    rows = [row[:] for row in matrix]
    height = len(rows)
    width = len(rows[0])
    rank = 0
    pivots: list[int] = []
    operations = 0
    for col in range(width):
        pivot = next((i for i in range(rank, height)
                      if rows[i][col] % prime), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        pivot_value = rows[rank][col] % prime
        if pivot_value != 1:
            inverse = pow(pivot_value, prime - 2, prime)
            for j in range(col, width):
                rows[rank][j] = (rows[rank][j] * inverse) % prime
                operations += 1
        for i in range(rank + 1, height):
            factor = rows[i][col] % prime
            if not factor:
                continue
            target = rows[i]
            source = rows[rank]
            for j in range(col, width):
                target[j] = (target[j] - factor * source[j]) % prime
                operations += 2
        pivots.append(col)
        rank += 1
        if rank == height:
            break

    pivot_set = set(pivots)
    free = [j for j in range(width) if j not in pivot_set]
    basis: list[list[int]] = []
    for free_col in free:
        vector = [0] * width
        vector[free_col] = 1
        for i in range(rank - 1, -1, -1):
            pivot_col = pivots[i]
            total = 0
            row = rows[i]
            for j in range(pivot_col + 1, width):
                if row[j] and vector[j]:
                    total = (total + row[j] * vector[j]) % prime
                    operations += 2
            vector[pivot_col] = (-total) % prime
        basis.append(vector)
    return basis, operations


def _spectral_cover_decode(inst: dict) -> tuple[dict | None, dict[str, int]]:
    """Domain-standard exact (-1)-eigenspace recovery of the K4 fibres.

    A random lift can occasionally have one accidental extra -1 eigenvector.
    Then same-fibre row signatures differ along one projective nuisance
    direction.  Quotienting by the most frequent such direction recovers the
    four fibre-constant signatures without consulting the planted answer.
    """
    n = inst["n"]
    adj = _adjacency(inst)
    matrix = [[0] * n for _ in range(n)]
    for v in range(n):
        matrix[v][v] = 1
        for w in adj[v]:
            matrix[v][w] = 1
    prime = 1_000_003
    basis, field_ops = _modular_nullspace(matrix, prime)
    clustering_ops = 0
    stats = {
        "matrix_dimension": n,
        "nullity": len(basis),
        "modular_field_operations": field_ops,
        "spectral_clustering_field_operations": clustering_ops,
    }
    if len(basis) not in (3, 4):
        return None, stats
    signatures = [tuple(vector[v] for vector in basis) for v in range(n)]
    if len(basis) == 4 and len(set(signatures)) != 4:
        direction_counts: dict[tuple[int, ...], int] = {}
        for i in range(n):
            for j in range(i + 1, n):
                difference = tuple(
                    (signatures[j][k] - signatures[i][k]) % prime
                    for k in range(4)
                )
                clustering_ops += 4
                pivot = next((k for k, value in enumerate(difference)
                              if value), None)
                if pivot is None:
                    continue
                inverse = pow(difference[pivot], prime - 2, prime)
                direction = tuple((value * inverse) % prime
                                  for value in difference)
                clustering_ops += 5  # one inversion and four multiplies
                direction_counts[direction] = direction_counts.get(direction, 0) + 1
        if not direction_counts:
            return None, stats
        candidate_directions = sorted(
            direction_counts,
            key=lambda direction: (-direction_counts[direction], direction),
        )[:128]
        quotient_signatures = None
        adj = _adjacency(inst)
        for nuisance in candidate_directions:
            pivot = next(k for k, value in enumerate(nuisance) if value)
            trial_signatures = []
            for signature in signatures:
                scale = signature[pivot]
                trial_signatures.append(tuple(
                    (signature[k] - scale * nuisance[k]) % prime
                    for k in range(4) if k != pivot
                ))
                clustering_ops += 6
            trial_distinct = sorted(set(trial_signatures))
            if (len(trial_distinct) != 4
                    or any(trial_signatures.count(value) != n // 4
                           for value in trial_distinct)):
                continue
            trial_class_of = {
                signature: c for c, signature in enumerate(trial_distinct)
            }
            trial_classes = [trial_class_of[signature]
                             for signature in trial_signatures]
            is_cover = all(
                {trial_classes[v], *(trial_classes[w] for w in adj[v])}
                == {0, 1, 2, 3}
                for v in range(n)
            )
            affine_fits = [
                _solve_affine_bit(
                    inst["labels"],
                    [(c >> bit) & 1 for c in trial_classes],
                    inst["coordinate_bits"],
                )
                for bit in range(2)
            ] if is_cover else []
            if is_cover and all(fit is not None for fit in affine_fits):
                quotient_signatures = trial_signatures
                break
        if quotient_signatures is None:
            return None, stats
        signatures = quotient_signatures
        stats["spectral_clustering_field_operations"] = clustering_ops
        stats["modular_field_operations"] += clustering_ops
    distinct = sorted(set(signatures))
    if len(distinct) != 4:
        return None, stats
    class_of = {signature: c for c, signature in enumerate(distinct)}
    classes = [class_of[signature] for signature in signatures]
    if any(classes.count(c) != n // 4 for c in range(4)):
        return None, stats
    fitted_masks = []
    fitted_offsets = []
    for bit in range(2):
        fitted = _solve_affine_bit(
            inst["labels"], [(c >> bit) & 1 for c in classes],
            inst["coordinate_bits"],
        )
        if fitted is None:
            return None, stats
        mask, offset = fitted
        fitted_masks.append(mask)
        fitted_offsets.append(offset)
    d = inst["coordinate_bits"]
    return {
        "matrix": [_mask_to_row(fitted_masks[0], d),
                   _mask_to_row(fitted_masks[1], d)],
        "offset": fitted_offsets,
    }, stats


def _unit_coordinate_attack(inst: dict) -> dict:
    """Outlier attack: choose the two coordinate columns closest to a cover."""
    d = inst["coordinate_bits"]
    adj = _adjacency(inst)
    labels = inst["labels"]
    best: tuple[int, int, int] | None = None
    for i, j in itertools.combinations(range(d), 2):
        classes = [((x >> i) & 1) | (((x >> j) & 1) << 1) for x in labels]
        violations = sum(
            {classes[v], *(classes[w] for w in adj[v])} != {0, 1, 2, 3}
            for v in range(inst["n"])
        )
        row = (violations, i, j)
        if best is None or row < best:
            best = row
    assert best is not None
    _, i, j = best
    return {
        "matrix": [_mask_to_row(1 << i, d), _mask_to_row(1 << j, d)],
        "offset": [0, 0],
    }


def _solve_affine_bit(labels: list[int], targets: list[int], d: int
                      ) -> tuple[int, int] | None:
    """Fit one affine GF(2) bit to fully assigned labelled vertices."""
    rows = [(x | (1 << d) | (targets[i] << (d + 1)))
            for i, x in enumerate(labels)]
    rank = 0
    pivots: list[int] = []
    for col in range(d + 1):
        pivot = next((i for i in range(rank, len(rows))
                      if (rows[i] >> col) & 1), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(len(rows)):
            if i != rank and ((rows[i] >> col) & 1):
                rows[i] ^= rows[rank]
        pivots.append(col)
        rank += 1
    variable_mask = (1 << (d + 1)) - 1
    if any((row & variable_mask) == 0 and ((row >> (d + 1)) & 1)
           for row in rows):
        return None
    solution = 0
    for row, pivot in zip(rows[:rank], pivots):
        if (row >> (d + 1)) & 1:
            solution |= 1 << pivot
    return solution & ((1 << d) - 1), (solution >> d) & 1


def _greedy_cover_attack(inst: dict) -> dict | None:
    """Greedy no-backtracking colouring of the closed-neighbourhood CSP."""
    n = inst["n"]
    adj = _adjacency(inst)
    constraints = [set() for _ in range(n)]
    for v in range(n):
        block = [v] + adj[v]
        for x in block:
            constraints[x].update(y for y in block if y != x)
    colors = [-1] * n
    while True:
        uncolored = [v for v in range(n) if colors[v] < 0]
        if not uncolored:
            break
        choices = []
        for v in uncolored:
            used = {colors[w] for w in constraints[v] if colors[w] >= 0}
            domain = [c for c in range(4) if c not in used]
            if not domain:
                return None
            choices.append((len(domain), -len(used), v, domain))
        _, _, v, domain = min(choices)
        colors[v] = domain[0]
    fitted = []
    offsets = []
    for bit in range(2):
        result = _solve_affine_bit(
            inst["labels"], [(c >> bit) & 1 for c in colors],
            inst["coordinate_bits"],
        )
        if result is None:
            return None
        mask, offset = result
        fitted.append(mask)
        offsets.append(offset)
    d = inst["coordinate_bits"]
    return {
        "matrix": [_mask_to_row(fitted[0], d), _mask_to_row(fitted[1], d)],
        "offset": offsets,
    }


def _low_bits_attack(inst: dict) -> dict:
    d = inst["coordinate_bits"]
    return {
        "matrix": [_mask_to_row(1, d), _mask_to_row(2, d)],
        "offset": [0, 0],
    }


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 256) -> tuple[dict, int]:
    last = random_candidate(inst, rng)
    for attempt in range(1, restarts + 1):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, attempt
    return last, restarts


def _transform_instance(inst: dict, vertex_permutation: list[int] | None = None,
                        coordinate_permutation: list[int] | None = None,
                        translation: int = 0) -> dict:
    """Carry instance and witness through genuine representation symmetries."""
    n = inst["n"]
    d = inst["coordinate_bits"]
    if vertex_permutation is None:
        vertex_permutation = list(range(n))
    if sorted(vertex_permutation) != list(range(n)):
        raise ValueError("bad vertex permutation")
    if coordinate_permutation is None:
        coordinate_permutation = list(range(d))
    if sorted(coordinate_permutation) != list(range(d)):
        raise ValueError("bad coordinate permutation")
    if translation < 0 or translation >= (1 << d):
        raise ValueError("bad coordinate translation")

    def transform_mask(x: int) -> int:
        y = 0
        for new_bit, old_bit in enumerate(coordinate_permutation):
            y |= ((x >> old_bit) & 1) << new_bit
        return y

    labels = [0] * n
    for old, new in enumerate(vertex_permutation):
        labels[new] = transform_mask(inst["labels"][old]) ^ translation
    edges = [[vertex_permutation[u], vertex_permutation[v]]
             for u, v in inst["edges"]]
    carried_masks = []
    carried_offsets = []
    for row, offset in zip(inst["answer"]["matrix"], inst["answer"]["offset"]):
        old_mask = sum(bit << j for j, bit in enumerate(row))
        new_mask = transform_mask(old_mask)
        carried_masks.append(_mask_to_row(new_mask, d))
        carried_offsets.append(offset ^ _parity(new_mask & translation))
    out = dict(inst)
    out["labels"] = labels
    out["edges"] = edges
    out["answer"] = {"matrix": carried_masks, "offset": carried_offsets}
    return out


def _shear_instance(inst: dict, source_bit: int, target_bit: int,
                    translation: int = 0) -> dict:
    """Apply the non-permutation basis change y_t=x_t+x_s over GF(2)."""
    d = inst["coordinate_bits"]
    if (source_bit == target_bit or source_bit < 0 or target_bit < 0
            or source_bit >= d or target_bit >= d):
        raise ValueError("bad shear coordinates")
    if translation < 0 or translation >= (1 << d):
        raise ValueError("bad coordinate translation")

    def shear_label(x: int) -> int:
        return (x ^ (((x >> source_bit) & 1) << target_bit)) ^ translation

    carried_masks = []
    carried_offsets = []
    for row, offset in zip(inst["answer"]["matrix"], inst["answer"]["offset"]):
        old_mask = sum(bit << j for j, bit in enumerate(row))
        # This elementary shear is its own inverse.  Substitution toggles the
        # source coefficient exactly when the target coefficient is present.
        new_mask = old_mask ^ (((old_mask >> target_bit) & 1) << source_bit)
        carried_masks.append(_mask_to_row(new_mask, d))
        carried_offsets.append(offset ^ _parity(new_mask & translation))
    out = dict(inst)
    out["labels"] = [shear_label(x) for x in inst["labels"]]
    out["answer"] = {"matrix": carried_masks, "offset": carried_offsets}
    return out


def _answer_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_elements(v) for v in value)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return machine-readable measured evidence."""
    report: dict[str, Any] = {}

    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            assert ok, (preset, seed, reason)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "generation_route": "inverse affine-cover generation and theorem-backed flow pullback",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260904, **ship_params)
    answer = json.loads(json.dumps(inst["answer"]))
    d = inst["coordinate_bits"]
    corruptions: dict[str, object] = {
        "empty": [],
        "drop_one_row": {
            "matrix": answer["matrix"][:1], "offset": answer["offset"]
        },
        "duplicate_row": {
            "matrix": [answer["matrix"][0], answer["matrix"][0]],
            "offset": answer["offset"],
        },
        "out_of_range_bit": {
            "matrix": [[2] + answer["matrix"][0][1:], answer["matrix"][1]],
            "offset": answer["offset"],
        },
        "swap_row_with_offset": {
            "matrix": [answer["offset"], answer["matrix"][1]],
            "offset": answer["matrix"][0],
        },
    }
    # Find one shape-correct single-bit corruption; it must reach a semantic
    # cover check, giving a distinct reason from the format corruptions above.
    for row in range(2):
        for col in range(d):
            bad = json.loads(json.dumps(answer))
            bad["matrix"][row][col] ^= 1
            if not verify(inst, bad)[0]:
                corruptions["single_bit_flip"] = bad
                break
        if "single_bit_flip" in corruptions:
            break
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        assert not ok, (name, reason)
        reasons[name] = reason
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "The local maps are bijections.\n```json\n<answer>"
        + json.dumps(inst["answer"], separators=(",", ":"))
        + "</answer>\n```\nAll coordinates use the stated little-endian row order."
    )
    assert parse_answer(response) == inst["answer"]
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>{not json}</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "answer_elements": _answer_elements(inst["answer"]),
        "json_native": True,
    }

    guess_inst = make_instance(seed=8675309, **ship_params)
    guess_rng = random.Random(13579)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            guess_hits += 1
    guess_density = guess_hits / guess_total
    assert guess_density < 1e-6, (guess_hits, guess_total)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_density,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform ordered full-rank 2xd matrices and uniform two-bit offsets",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1

    reference_seeds = list(range(4100, 4108))
    reference_operations = []
    reference_times = []
    compact_operations = []
    for seed in reference_seeds:
        sample = make_instance(seed=seed, **ship_params)
        start = time.perf_counter()
        decoded, stats = _spectral_cover_decode(sample)
        reference_times.append(time.perf_counter() - start)
        assert decoded is not None and verify(sample, decoded)[0]
        reference_operations.append(stats["modular_field_operations"])
        compact, compact_stats = _decode_from_signatures(
            sample, sample["probe_vertices"]
        )
        assert compact is not None and verify(sample, compact)[0]
        compact_operations.append(compact_stats["packed_exact_operations"])
    baseline_seconds = sum(reference_times)
    baseline_ops = sum(reference_operations)
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_density,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_seconds_8": baseline_seconds,
        "baseline_modular_field_operations_8": baseline_ops,
        "baseline_max_operations_one_instance": max(reference_operations),
        "baseline_algorithm": "exact (-1)-eigenspace via modular elimination and projective quotienting",
    }

    attack_results = {
        "outlier_best_coordinate_pair": {"successes": 0, "attempts": 8},
        "greedy_K4_cover_no_backtracking": {"successes": 0, "attempts": 8},
        "random_restart_256_full_rank_matrices": {"successes": 0, "attempts": 8},
        "by_hand_two_low_coordinate_bits": {"successes": 0, "attempts": 8},
    }
    for seed in range(5100, 5108):
        sample = make_instance(seed=seed, **ship_params)
        if verify(sample, _unit_coordinate_attack(sample))[0]:
            attack_results["outlier_best_coordinate_pair"]["successes"] += 1
        greedy = _greedy_cover_attack(sample)
        if greedy is not None and verify(sample, greedy)[0]:
            attack_results["greedy_K4_cover_no_backtracking"]["successes"] += 1
        restarted, _ = _random_restart_attack(
            sample, random.Random(900000 + seed), 256
        )
        if verify(sample, restarted)[0]:
            attack_results["random_restart_256_full_rank_matrices"]["successes"] += 1
        if verify(sample, _low_bits_attack(sample))[0]:
            attack_results["by_hand_two_low_coordinate_bits"]["successes"] += 1
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    assert all_failed, attack_results
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact (-1)-eigenspace via modular elimination and projective quotienting",
            "complexity": "O(n^3) modular field operations",
            "wall_clock_sec_8": baseline_seconds,
            "operations_8": baseline_ops,
            "max_operations_one_instance": max(reference_operations),
            "solves": "8/8, as expected for Track B",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    assert doubled_ok, doubled_reason
    assert len(doubled["edges"]) == 2 * len(inst["edges"])
    report["G7_scales"] = {
        "pass": True,
        "shipping_vertices": inst["n"],
        "doubled_vertices": doubled["n"],
        "shipping_edges": len(inst["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "answer_elements_unchanged": (
            _answer_elements(inst["answer"]) == _answer_elements(doubled["answer"])
        ),
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        sample = make_instance(seed=6000 + seed, **ship_params)
        key = canonical_key(sample)
        keys.append(key)
        rng = random.Random(7000 + seed)
        vp = list(range(sample["n"]))
        rng.shuffle(vp)
        cp = list(range(sample["coordinate_bits"]))
        rng.shuffle(cp)
        translation = rng.randrange(1 << sample["coordinate_bits"])
        edge_reordered = dict(sample)
        edge_reordered["edges"] = [[v, u] for u, v in sample["edges"]]
        rng.shuffle(edge_reordered["edges"])
        fully_transformed = _transform_instance(
            sample, vertex_permutation=vp,
            coordinate_permutation=cp, translation=translation,
        )
        fully_transformed["edges"] = [
            [v, u] for u, v in fully_transformed["edges"]
        ]
        rng.shuffle(fully_transformed["edges"])
        variants = [
            _transform_instance(sample, vertex_permutation=vp),
            _transform_instance(sample, coordinate_permutation=cp,
                                translation=translation),
            _transform_instance(sample, vertex_permutation=vp,
                                coordinate_permutation=cp,
                                translation=translation),
            _shear_instance(sample, 0, 1, translation=translation),
            _shear_instance(
                _transform_instance(sample, vertex_permutation=vp),
                0, 1, translation=translation,
            ),
            edge_reordered,
            fully_transformed,
        ]
        # A pure vertex renumbering preserves the original coordinate formula.
        assert verify(variants[0], sample["answer"])[0]
        carried_checks += 1
        for variant in variants:
            assert canonical_key(variant) == key
            invariant_checks += 1
            assert verify(variant, variant["answer"])[0]
            carried_checks += 1
    assert len(set(keys)) == len(keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariant_checks,
        "witness_transport_checks": carried_checks,
        "unrelated_instances": len(keys),
        "distinct_keys": len(set(keys)),
        "transformations": [
            "vertex renumbering",
            "edge reordering and endpoint reversal",
            "GF(2) coordinate permutation",
            "non-permutation GF(2) basis shear",
            "global GF(2) coordinate translation",
            "compositions of the above",
        ],
        "invariant": "sorted all-vertex graph-distance histograms",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_elements(inst["answer"])
    intended_ops = max(compact_operations)
    hinted_still_hardened = _G9_HINTED_VERDICT == "hardened"
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_ops <= 300)
    assert within_caps, (answer_chars, answer_elements, intended_ops)
    hinted_rate = (_G9_ARMS["hinted"]["solved"]
                   / max(1, _G9_ARMS["hinted"]["attempts"]))
    placebo_rate = (_G9_ARMS["placebo"]["solved"]
                    / max(1, _G9_ARMS["placebo"]["attempts"]))
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "intended_route_measure": "packed exact XOR/parity operations on d+2 signatures",
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = ship_params
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
