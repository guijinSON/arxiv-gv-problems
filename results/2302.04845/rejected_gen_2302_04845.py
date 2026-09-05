"""Rejected prototype Hamilton (4,3)-cycle instances for arXiv:2302.04845.

This file is retained as required forensic evidence.  Its Track B hardness
claim is invalid: the planted modulus is recovered directly by taking the
gcd of within-block tag differences, so its purported mechanical and compact
routes have essentially the same cost.  See REJECTED.md.

The paper defines a Hamilton (ell,k-ell)-cycle as an alternating cyclic
partition into ell-sets and (k-ell)-sets.  This module fixes (k,ell)=(7,4)
and supplies disjoint (L,R) block pairs.  Internal unions L_i union R_i
are hyperedges, and a displayed transition bit says exactly when
R_i union L_j is a hyperedge.  A permutation of all blocks is therefore a
literal Hamilton (4,3)-cycle witness in the paper's sense.

Generation is inverse: a hidden cyclic coordinate is sampled first, the
coordinate order is made a cycle, and regular decoy transitions are added.
The planted certificate is never obtained by solving the generated instance.
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
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - this family needs only stdlib
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "7-uniform hypergraph",
        "disjoint 4-set/3-set block pairs",
        "Hamilton (4,3)-cycle",
    ],
    "verification_operations": [
        "exact permutation and set-cardinality checks",
        "exact union of a 4-set and a 3-set",
        "exact hyperedge membership by transition-bit lookup",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 1 definition of an (ell,k-ell)-cycle and Section 2.2's "
        "auxiliary adjacency graph G(H), where (L,R) is adjacent exactly "
        "when L union R is a hyperedge"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The three tags on each block share a hidden modular coordinate whose "
        "cyclic order is a Hamilton cycle; without recognizing it, the solver "
        "must search the displayed block-transition graph."
    ),
    "hardness_basis": (
        "Track B: bounded-modulus recognition scans q<10000 in O(B*n+n log n) "
        "exact operations and, at the shipping preset n=72, performs 2,159,568 "
        "modular reductions (measured by selftest), whereas recognizing the "
        "common-residue invariant reduces the intended route to at most 154 "
        "exact arithmetic/edge-check operations; Section 1 only quotes general "
        "NP-completeness, so no Track A distributional claim is made."
    ),
    "max_answer_tokens": 146,
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
    "demo": {"n": 6, "degree": 2, "q": 11, "tag_bits": 4},
    "easy": {"n": 72, "degree": 8, "q": 7919, "tag_bits": 48},
    "medium": {"n": 84, "degree": 7, "q": 7919, "tag_bits": 80},
    "hard": {"n": 96, "degree": 6, "q": 7919, "tag_bits": 112},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The three tags on every block share one cyclic residue coordinate modulo 7919."
)
PLACEBO_HINT = (
    "The transition rows and block identifiers use the same zero-based indexing convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array containing every block identifier 0..n-1 exactly once; "
        "the array is a directed cyclic ordering, so the bounded language has n! "
        "members."
    ),
    "bounds": {
        "answer_length": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "structural_rule": "permutation of all block identifiers",
        "candidate_count": "n!",
    },
}

NOTES = r"""
STEP 0 and paper grounding.  Section 1 gives the exact definition used here:
a Hamilton (ell,k-ell)-cycle is a partition
(L_0,R_0,...,L_{t-1},R_{t-1}) with |L_i|=ell, |R_i|=k-ell, and
both L_i union R_i and R_i union L_{i+1} hyperedges.  The paper's main
Theorem 1.2 applies for k>=7, k/2<=ell<=k-1, sufficiently large total
vertex count divisible by k, and minimum ell-degree above delta(n,k,ell).
The generated family fixes k=7, ell=4, and has 7n vertices, so its witness
is exactly the paper's native object.  Section 2.2 defines the auxiliary
bipartite adjacency graph G(H) on ell-sets and (k-ell)-sets, with adjacency
meaning that their union is a hyperedge.  The displayed transition table is
the induced adjacency data on the supplied disjoint blocks; it does not
replace the hypergraph, because the L/R vertex sets and every permitted
7-set union are explicitly defined in the statement and checked by verify.

Why Track B, not Track A.  The paper's Section 1 quotes Garey--Johnson
NP-completeness for perfect matching or Hamilton path in general k-uniform
hypergraphs, but that is worst-case hardness and says nothing about this
inverse-generated distribution.  Theorem 1.2 is an extremal existence
theorem, not a computational hardness theorem.  Its non-extremal proof uses
random reservoirs, absorbers, regularity, an almost-perfect matching and
path connection (Lemmas 2.1--2.4); its extremal proof identifies the parity
obstacle f(B) in Section 3.  None licenses a Track A claim for random planted
cycles.  The prior-triage proposal "plant a cycle, add random edges" would in
fact be easy at the roughly one-half density of Theorem 1.2.  This module is
therefore explicit about the polynomial family-specific method that exists.

Certificate production.  Coordinates c in Z_n and a regular set of shifts
S containing 1 are sampled first.  Block c has transitions to c+s for every
s in S, so c=0,1,...,n-1 is a Hamilton ordering by construction.  Blocks,
vertices and rows are independently relabelled, and every block receives
three large tags congruent to c modulo q.  The answer is carried through
those relabellings.  No Hamilton search is used to obtain it.  Plants and
decoys are translation layers of the same regular distribution: every block
has the same in-degree and out-degree.

What produces a certificate.  The measured reference algorithm tries every
candidate modulus below 10000, computes all three tag residues for all blocks,
and checks any common-residue ordering against the hyperedges.  This is
O(B*n+n log n), succeeds on every generated instance, and is cheap in a
sandbox but requires millions of exact reductions at the shipping preset.
The compact route is to notice the common modular coordinate, recover q from
within-block differences (or receive the structural hint), reduce one tag per
block, and check the cyclic order.  At shipping size that is at most 154 exact
arithmetic/edge operations after the insight.

Attack controls.  Regular translation layers eliminate degree outliers.
Public block and vertex orders are independent of coordinates.  Generation
resamples only decoys and presentation until the fixed public-index greedy,
local neighborhood-overlap rule, and two visual tag rankings all fail; the
known coordinate witness is unchanged and is never searched for.  The panel
also runs 512 structure-aware random permutations.  A capped generic directed
Hamilton DFS is recorded as an in-context/domain heuristic, while the
successful polynomial modulus recognizer is the Track B reference algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_MODULUS_SCAN_BOUND = 10_000
_ENUMERATION_CAP = 1_000_000

# Replaced after the three independent harness runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _validate_parameters(n: int, seed: int, degree: int, q: int, tag_bits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not (6 <= n <= 256):
        raise ValueError("n must be an integer in 6..256")
    if n % 2:
        raise ValueError("n must be even")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer")
    nonunits = sum(math.gcd(s, n) > 1 for s in range(2, n))
    if not (2 <= degree <= nonunits + 1):
        raise ValueError("degree must allow shift 1 and degree-1 non-unit decoys")
    if (isinstance(q, bool) or not isinstance(q, int)
            or not n < q < _MODULUS_SCAN_BOUND):
        raise ValueError("q must be an integer with n < q < 10000")
    if isinstance(tag_bits, bool) or not isinstance(tag_bits, int):
        raise ValueError("tag_bits must be an integer")
    if not (4 <= tag_bits <= 256):
        raise ValueError("tag_bits must lie in 4..256")


def _order_valid_rows(rows: list[str], order: list[int]) -> bool:
    n = len(rows)
    return (
        len(order) == n
        and len(set(order)) == n
        and all(0 <= x < n for x in order)
        and all(rows[order[i]][order[(i + 1) % n]] == "1" for i in range(n))
    )


def _greedy_public(rows: list[str]) -> list[int] | None:
    """Follow the smallest unused public-index successor from block 0."""
    n = len(rows)
    order = [0]
    used = {0}
    while len(order) < n:
        nxt = next((v for v, bit in enumerate(rows[order[-1]])
                    if bit == "1" and v not in used), None)
        if nxt is None:
            return None
        order.append(nxt)
        used.add(nxt)
    return order


def _overlap_greedy(rows: list[str], largest: bool) -> list[int] | None:
    """A local graph-only rule based on successor-neighborhood overlap."""
    n = len(rows)
    out = [{j for j, bit in enumerate(row) if bit == "1"} for row in rows]
    order = [0]
    used = {0}
    while len(order) < n:
        u = order[-1]
        choices = [v for v in out[u] if v not in used]
        if not choices:
            return None
        scored = [(len(out[u] & out[v]), v) for v in choices]
        score, nxt = (max(scored) if largest else min(scored))
        del score
        order.append(nxt)
        used.add(nxt)
    return order


def _rank_order(blocks: list[dict], key) -> list[int]:
    return sorted(range(len(blocks)), key=lambda i: (key(blocks[i]), i))


def _presentation_attacks_fail(inst: dict) -> bool:
    rows = inst["transitions"]
    blocks = inst["blocks"]
    candidates = [
        list(range(len(rows))),
        _greedy_public(rows),
        _overlap_greedy(rows, True),
        _overlap_greedy(rows, False),
        _rank_order(blocks, lambda b: b["tags"][0]),
        _rank_order(blocks, lambda b: b["tags"][0] % 10_000),
    ]
    return all(c is None or not _order_valid_rows(rows, c) for c in candidates)


def _tag_triples_by_coordinate(
    n: int, q: int, tag_bits: int, rng: random.Random
) -> list[list[int]]:
    """Generate triples whose within-triple differences have gcd exactly q."""
    lo = 1 << (tag_bits - 1)
    hi = (1 << tag_bits) - 1
    for _ in range(256):
        multipliers = []
        for _block in range(n):
            triple = set()
            while len(triple) < 3:
                triple.add(rng.randint(lo, hi))
            multipliers.append(list(triple))
        g = 0
        for triple in multipliers:
            g = math.gcd(g, abs(triple[0] - triple[1]))
            g = math.gcd(g, abs(triple[0] - triple[2]))
        if g == 1:
            return [[q * h + c for h in triple]
                    for c, triple in enumerate(multipliers)]
    raise RuntimeError("could not generate tag differences with unit gcd")


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a block-transition hypergraph and a known cycle."""
    unknown = set(params) - {"degree", "q", "tag_bits"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    degree = params.get("degree", 6)
    q = params.get("q", 7919)
    tag_bits = params.get("tag_bits", 64)
    _validate_parameters(n, seed, degree, q, tag_bits)
    rng = random.Random(seed)

    # Resampling rejects incidental presentation shortcuts, never searches for
    # the certificate: coordinate step +1 remains known on every attempt.
    for _attempt in range(512):
        nonunit_shifts = [s for s in range(2, n) if math.gcd(s, n) > 1]
        shifts = {1, *rng.sample(nonunit_shifts, degree - 1)}

        public_to_coordinate = list(range(n))
        rng.shuffle(public_to_coordinate)
        coordinate_to_public = [0] * n
        for public, coordinate in enumerate(public_to_coordinate):
            coordinate_to_public[coordinate] = public

        rows = []
        for coordinate in public_to_coordinate:
            targets = {coordinate_to_public[(coordinate + s) % n] for s in shifts}
            rows.append("".join("1" if j in targets else "0" for j in range(n)))

        tags_by_coordinate = _tag_triples_by_coordinate(n, q, tag_bits, rng)
        vertex_labels = list(range(7 * n))
        rng.shuffle(vertex_labels)
        blocks = []
        for public, coordinate in enumerate(public_to_coordinate):
            vertices = vertex_labels[7 * public:7 * public + 7]
            blocks.append({
                "L": sorted(vertices[:4]),
                "R": sorted(vertices[4:]),
                "tags": tags_by_coordinate[coordinate],
            })

        base = {
            "paper": "arXiv:2302.04845",
            "family": "tagged_block_hamilton_4_3_cycle",
            "n": n,
            "total_vertices": 7 * n,
            "k": 7,
            "ell": 4,
            "degree": degree,
            "tag_bits": tag_bits,
            "blocks": blocks,
            "transitions": rows,
        }
        presentation_safe = _presentation_attacks_fail(base)
        dfs_safe = True
        if n != DIFFICULTY["demo"]["n"] and presentation_safe:
            dfs_safe = _attack_dfs(base, node_cap=5_000)[0] is None
        if n == DIFFICULTY["demo"]["n"] or (presentation_safe and dfs_safe):
            answer = [coordinate_to_public[c] for c in range(n)]
            assert _order_valid_rows(rows, answer)
            return {**base, "answer": answer}
    raise RuntimeError("could not remove fixed presentation shortcuts")


def render(inst: dict) -> str:
    """Render the complete native hypergraph problem and exact wire format."""
    n = inst["n"]
    lines = [
        "Hamilton (4,3)-cycle in a 7-uniform hypergraph",
        "",
        f"There are {inst['total_vertices']} vertices, numbered 0 through "
        f"{inst['total_vertices'] - 1}, and {n} disjoint block-pairs.",
        "Block b consists of a 4-vertex set L_b and a 3-vertex set R_b.",
        "All displayed L- and R-sets are pairwise disjoint and together cover",
        "every vertex exactly once.  Thus any ordering of all blocks gives an",
        "alternating partition (L_b0,R_b0,L_b1,R_b1,...).",
        "",
        "The 7-uniform hypergraph H has exactly these hyperedges:",
        "  (1) L_b union R_b for every block b; and",
        "  (2) R_b union L_c exactly when row b, column c of the transition",
        "      table is 1.  No other 7-set is a hyperedge.",
        "",
        "A Hamilton (4,3)-cycle is a cyclic ordering [b0,...,b_(n-1)] of every",
        "block exactly once such that L_bi union R_bi and R_bi union L_b(i+1)",
        "are hyperedges for every i, where the last block wraps to the first.",
        "Internal hyperedges of type (1) are automatic, so every consecutive",
        "transition in the submitted cyclic ordering must be a 1, including wraparound.",
        "",
        "Each block also has three integer tags.  Tags are metadata and impose",
        "no validity condition; only the vertex sets and hyperedges above determine",
        "whether an answer is correct.",
        "",
        "Blocks (all identifiers and vertex numbers are zero-based):",
    ]
    for b, block in enumerate(inst["blocks"]):
        lines.append(
            f"{b}: L={json.dumps(block['L'], separators=(',', ':'))} "
            f"R={json.dumps(block['R'], separators=(',', ':'))} "
            f"tags={json.dumps(block['tags'], separators=(',', ':'))}"
        )
    lines.extend([
        "",
        "Transition bit table (row b, columns c=0..n-1):",
    ])
    lines.extend(f"{b}: {row}" for b, row in enumerate(inst["transitions"]))
    lines.extend([
        "",
        f"Return one JSON array of length {n}, containing each integer 0 through "
        f"{n - 1} exactly once in cyclic order.  Order matters up to validity;",
        "repeats and omissions are forbidden, and wraparound is required.",
        "",
        "Give your final answer inside <answer></answer> tags, as that exact JSON array.",
        "Syntax-only example: <answer>[2,0,1]</answer>",
        "Output nothing else inside the tags.",
    ])
    statement = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON permutation, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            rows = body.splitlines()
            if len(rows) >= 3:
                body = "\n".join(rows[1:-1]).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if (isinstance(value, list)
                and all(isinstance(x, int) and not isinstance(x, bool) for x in value)):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid cyclic block ordering; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer must not be empty"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every answer entry must be an integer block identifier"
    n = inst.get("n")
    if not isinstance(n, int):
        return False, "malformed instance: n is not an integer"
    if len(answer) != n:
        return False, f"answer must contain exactly {n} block identifiers"
    if any(x < 0 or x >= n for x in answer):
        return False, f"every block identifier must lie in 0..{n - 1}"
    if len(set(answer)) != n:
        return False, "answer must be a permutation with no repeated or omitted block"
    rows = inst.get("transitions")
    if (not isinstance(rows, list) or len(rows) != n
            or any(not isinstance(row, str) or len(row) != n
                   or set(row) - {"0", "1"} for row in rows)):
        return False, "malformed instance: transition table is not an n-by-n bit matrix"
    for i, block in enumerate(answer):
        nxt = answer[(i + 1) % n]
        if rows[block][nxt] != "1":
            return False, (
                f"missing hyperedge at cycle step {i}: R_{block} union L_{nxt} "
                "is not present"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the structure-aware language of block permutations."""
    return rng.sample(range(inst["n"]), inst["n"])


def search_space(inst: dict) -> int | None:
    """Exact size of the declared permutation language."""
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid orderings when n! stays below a hard work cap."""
    n = inst["n"]
    if math.factorial(n) > _ENUMERATION_CAP:
        return None
    return sum(
        _order_valid_rows(inst["transitions"], list(order))
        for order in itertools.permutations(range(n))
    )


def _recover_tag_modulus(blocks: list[dict]) -> int:
    g = 0
    for block in blocks:
        tags = block["tags"]
        g = math.gcd(g, abs(tags[0] - tags[1]))
        g = math.gcd(g, abs(tags[0] - tags[2]))
    return g


def canonical_key(inst: dict) -> str:
    """Canonicalize block/input/vertex relabellings through attached tags."""
    q = _recover_tag_modulus(inst["blocks"])
    if q <= inst["n"]:
        raise ValueError("malformed instance: tags do not determine distinct coordinates")
    order = sorted(range(inst["n"]),
                   key=lambda b: (inst["blocks"][b]["tags"][0] % q, b))
    rows = inst["transitions"]
    canonical_rows = ["".join(rows[i][j] for j in order) for i in order]
    payload = {
        "n": inst["n"],
        "k": 7,
        "ell": 4,
        "rows": canonical_rows,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """First harden arithmetic/decoys at fixed answer length, then approach caps."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    p.setdefault("tag_bits", 64)
    p.setdefault("degree", 6)
    p.setdefault("q", 7919)
    if p["tag_bits"] < 224:
        p["tag_bits"] = min(224, p["tag_bits"] + 32)
        p["degree"] = max(2, p["degree"] - 1)
        return p
    if p["degree"] > 2:
        p["degree"] -= 1
        return p
    if p.get("n", 0) < 144:
        p["n"] = min(144, p.get("n", 0) + 12)
        if p["n"] % 2:
            p["n"] += 1
        return p
    return "cap_bound"


def _attack_visual_tags(inst: dict) -> list[list[int] | None]:
    blocks = inst["blocks"]
    return [
        _rank_order(blocks, lambda b: b["tags"][0]),
        _rank_order(blocks, lambda b: b["tags"][0] % 10_000),
    ]


def _attack_random_permutations(
    inst: dict, rng: random.Random, attempts: int = 512
) -> list[int] | None:
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if _order_valid_rows(inst["transitions"], candidate):
            return candidate
    return None


def _attack_dfs(
    inst: dict, node_cap: int = 5_000
) -> tuple[list[int] | None, dict]:
    """Generic directed-Hamilton DFS with a least-onward-choice ordering."""
    rows = inst["transitions"]
    n = inst["n"]
    out = [[j for j, bit in enumerate(row) if bit == "1"] for row in rows]
    path = [0]
    used = {0}
    nodes = 0
    trials = 0

    def dfs(u: int) -> bool:
        nonlocal nodes, trials
        nodes += 1
        if nodes > node_cap:
            return False
        if len(path) == n:
            return rows[u][path[0]] == "1"
        choices = [v for v in out[u] if v not in used]
        choices.sort(key=lambda v: (sum(w not in used for w in out[v]), v))
        for v in choices:
            trials += 1
            used.add(v)
            path.append(v)
            if dfs(v):
                return True
            path.pop()
            used.remove(v)
        return False

    solved = dfs(0)
    return (path[:] if solved else None), {
        "nodes": nodes,
        "branch_trials": trials,
        "node_cap": node_cap,
    }


def _reference_algorithm(inst: dict) -> tuple[list[int] | None, dict]:
    """Polynomial exhaustive bounded-modulus recognition and exact validation."""
    t0 = time.perf_counter()
    n = inst["n"]
    blocks = inst["blocks"]
    valid_orders = []
    reductions = 0
    comparisons = 0
    edge_checks = 0
    for modulus in range(2, _MODULUS_SCAN_BOUND):
        residues = []
        for block in blocks:
            row = [tag % modulus for tag in block["tags"]]
            reductions += 3
            residues.append(row)
        if not all(row[0] == row[1] == row[2] for row in residues):
            continue
        coordinate = [row[0] for row in residues]
        if len(set(coordinate)) != n:
            continue
        order = sorted(range(n), key=lambda b: (coordinate[b], b))
        comparisons += max(1, math.ceil(n * math.log2(max(2, n))))
        edge_checks += n
        if _order_valid_rows(inst["transitions"], order):
            valid_orders.append((modulus, order))
    answer = valid_orders[0][1] if valid_orders else None
    elapsed = time.perf_counter() - t0
    return answer, {
        "moduli_tested": _MODULUS_SCAN_BOUND - 2,
        "modular_reductions": reductions,
        "sort_comparisons_upper_bound": comparisons,
        "edge_checks": edge_checks,
        "operations": reductions + comparisons + edge_checks,
        "wall_clock_sec": elapsed,
        "valid_moduli": [m for m, _ in valid_orders],
    }


def _permute_storage(inst: dict, rng: random.Random) -> dict:
    """Relabel block order and all vertices, carrying the supplied witness."""
    n = inst["n"]
    new_to_old = list(range(n))
    rng.shuffle(new_to_old)
    old_to_new = [0] * n
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new

    vertex_new_to_old = list(range(7 * n))
    rng.shuffle(vertex_new_to_old)
    vertex_old_to_new = [0] * (7 * n)
    for new, old in enumerate(vertex_new_to_old):
        vertex_old_to_new[old] = new

    blocks = []
    for old in new_to_old:
        block = inst["blocks"][old]
        blocks.append({
            "L": sorted(vertex_old_to_new[v] for v in block["L"]),
            "R": sorted(vertex_old_to_new[v] for v in block["R"]),
            "tags": list(block["tags"]),
        })
    rows = [
        "".join(inst["transitions"][old_i][old_j] for old_j in new_to_old)
        for old_i in new_to_old
    ]
    answer = [old_to_new[old] for old in inst["answer"]]
    return {**inst, "blocks": blocks, "transitions": rows, "answer": answer}


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(v) for v in value)
    return 1


def _find_invalid_swap(inst: dict) -> list[int]:
    answer = inst["answer"][:]
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            trial = answer[:]
            trial[i], trial[j] = trial[j], trial[i]
            ok, why = verify(inst, trial)
            if not ok and why.startswith("missing hyperedge"):
                return trial
    raise AssertionError("could not find an edge-breaking swap")


def selftest() -> dict:
    """Run gates G1--G9 and return measured, JSON-native evidence."""
    report: dict[str, Any] = {"track": TRACK, "shipping": SHIPPING_DIFFICULTY}

    # G1: all presets, several independent seeds, and JSON-native answers.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            instance = make_instance(seed=seed, **params)
            ok, why = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260204845, **shipping_params)
    planted = inst["answer"]

    # G2: all required corruptions, intentionally distinct diagnostics.
    corruptions: dict[str, object] = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate": [planted[0], planted[0], *planted[2:]],
        "out_of_range": [inst["n"], *planted[1:]],
        "swap": _find_invalid_swap(inst),
    }
    rejection_reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        rejection_reasons[name] = {"rejected": not ok, "reason": why}
    distinct = len({row["reason"] for row in rejection_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejection_reasons.values())
        and distinct == len(rejection_reasons),
        "distinct_reasons": distinct,
        "cases": rejection_reasons,
    }

    # G3: realistic surrounding prose and a Markdown-fenced exact answer.
    answer_json = json.dumps(planted, separators=(",", ":"))
    model_style = (
        "The cyclic transitions and wraparound all check out.\n"
        "<answer>\n```json\n" + answer_json + "\n```\n</answer>\n"
        "All identifiers are zero-based."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_equals_answer": parsed == planted,
    }

    # G4 and the shipping-density half of G5.
    guess_rng = random.Random(445566)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(_order_valid_rows(inst["transitions"], candidate))
    guess_elapsed = time.perf_counter() - t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "structure_aware_space": str(search_space(inst)),
        "wall_clock_sec": guess_elapsed,
    }

    reference_answer, reference_cost = _reference_algorithm(inst)
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and demo_count is not None,
        "shipping_valid_hits": guess_hits,
        "shipping_samples": guess_total,
        "shipping_density_estimate": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": reference_cost["wall_clock_sec"],
        "baseline_operations": reference_cost["operations"],
        "baseline_modular_reductions": reference_cost["modular_reductions"],
        "baseline_moduli_tested": reference_cost["moduli_tested"],
    }

    # G6: four failing attacks over eight seeds; successful algorithm separate.
    attack_names = (
        "outlier_regular_degree_public_index",
        "greedy_smallest_successor",
        "random_restart_512_permutations",
        "by_hand_tag_magnitude_or_decimal_rank",
        "local_neighborhood_overlap_extremes",
        "directed_hamilton_dfs_5000_nodes",
    )
    attacks = {name: {"successes": 0, "attempts": 0}
               for name in attack_names}
    ref_successes = 0
    ref_operations = 0
    ref_reductions = 0
    ref_wall = 0.0
    ref_valid_moduli: set[int] = set()
    dfs_nodes = 0
    for seed in range(31001, 31009):
        attack_inst = make_instance(seed=seed, **shipping_params)
        rows = attack_inst["transitions"]
        candidates: dict[str, list[int] | None] = {
            attack_names[0]: list(range(attack_inst["n"])),
            attack_names[1]: _greedy_public(rows),
            attack_names[2]: _attack_random_permutations(
                attack_inst, random.Random(seed ^ 0xA5A5A5A5)
            ),
            attack_names[3]: _attack_visual_tags(attack_inst)[0],
            attack_names[4]: _overlap_greedy(rows, True),
        }
        visual_second = _attack_visual_tags(attack_inst)[1]
        overlap_second = _overlap_greedy(rows, False)
        dfs_candidate, dfs_cost = _attack_dfs(attack_inst, node_cap=5_000)
        dfs_nodes += dfs_cost["nodes"]
        candidates[attack_names[5]] = dfs_candidate
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            success = candidate is not None and verify(attack_inst, candidate)[0]
            if name == attack_names[3]:
                success = success or verify(attack_inst, visual_second)[0]
            if name == attack_names[4]:
                success = success or (
                    overlap_second is not None and verify(attack_inst, overlap_second)[0]
                )
            attacks[name]["successes"] += int(success)

        found, cost = _reference_algorithm(attack_inst)
        ref_successes += int(found is not None and verify(attack_inst, found)[0])
        ref_operations += cost["operations"]
        ref_reductions += cost["modular_reductions"]
        ref_wall += cost["wall_clock_sec"]
        ref_valid_moduli.update(cost["valid_moduli"])

    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attacks.values())
    attacks[attack_names[5]]["nodes_total"] = dfs_nodes
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "bounded-modulus recognition plus exact cycle validation",
            "complexity": "O(B*n + n log n) exact for fixed bound B=10000",
            "wall_clock_sec": ref_wall,
            "operations": ref_operations,
            "modular_reductions": ref_reductions,
            "valid_moduli_seen": sorted(ref_valid_moduli),
            "solves": f"{ref_successes}/8, as expected on Track B",
        },
    }

    # G7: double n while preserving answer construction and exact verification.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled = make_instance(seed=8675309, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "shipping_n": inst["n"],
        "shipping_total_vertices": inst["total_vertices"],
        "doubled_n": doubled["n"],
        "doubled_total_vertices": doubled["total_vertices"],
        "doubled_verification": doubled_why,
        "shipping_search_space_bits": search_space(inst).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    # G8: block/input ordering and global vertex relabelling, including composition.
    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    g8_failures = []
    for seed in range(20):
        base = make_instance(seed=50000 + seed, **shipping_params)
        key = canonical_key(base)
        distinct_keys.append(key)
        once = _permute_storage(base, random.Random(60000 + seed))
        twice = _permute_storage(once, random.Random(70000 + seed))
        for transformed in (once, twice):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed under relabelling")
            carried_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append(f"seed {seed}: carried witness failed: {why}")
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariant_checks >= 20
        and carried_checks >= 20 and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": distinct_count,
        "unrelated_attempts": 20,
        "failures": g8_failures,
    }

    # G9(a,b) are external diagnostics; only exact size/effort caps gate.
    compact_answer = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(compact_answer)
    answer_atoms = _atomic_elements(planted)
    answer_tokens = len(re.findall(r"\d+|[\[\],]", compact_answer))
    intended_ops = 2 * inst["n"] + 10
    arms = {k: dict(G9_EVIDENCE[k]) for k in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
