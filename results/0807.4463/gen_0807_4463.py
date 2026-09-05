"""Exact generator for multipartite clique-factor witnesses from arXiv:0807.4463.

The paper studies K_q-factors in dense balanced q-partite graphs.  This module
uses q=3 and inverse-generates a triangle factor.  All graph data are explicit
bit matrices, and a proposed factor is checked using only exact bit lookups.
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
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "balanced tripartite graph",
        "triangle factor",
    ],
    "verification_operations": [
        "permutation check",
        "exact adjacency-bit lookup",
        "vertex-cover check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A common residue coordinate aligns one vertex from each part; without "
        "that invariant the solver must construct a perfect 3-dimensional matching."
    ),
    "hardness_basis": (
        "Track B: Section 3.1's Factor Finder is an algorithmic recursive matching "
        "construction (polynomial for fixed q when combined with the algorithmic "
        "regularity and Blow-up lemmas); on the shipping n=83 distribution, the "
        "measured graph-only references include O(R*n^3) randomized valid-triangle "
        "greedy and triangle-enumeration/Algorithm X, the latter performing about "
        "1.72 million exact edge probes plus backtracking per instance, while the "
        "compact residue route uses 249 exact reductions modulo 997."
    ),
    "max_answer_tokens": 341,
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
    "demo": {"n": 5, "tag_bits": 3, "degree_extra": 0},
    "easy": {"n": 83, "tag_bits": 48, "degree_extra": 4},
    "medium": {"n": 89, "tag_bits": 72, "degree_extra": 2},
    "hard": {"n": 97, "tag_bits": 96, "degree_extra": 0},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The vertex tags in all three parts share a complete residue pattern modulo 997."
)
PLACEBO_HINT = (
    "The three adjacency tables use a consistent row-and-column order throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with keys B and C, each an arbitrary permutation of "
        "0..n-1; the two permutations encode one B- and one C-vertex for every "
        "A-vertex."
    ),
    "bounds": {
        "arrays": 2,
        "max_length_each": 996,
        "entry_min": 0,
        "entry_max": 995,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Page 1 defines a J-factor as vertex-disjoint
copies covering the graph and defines a balanced q-partite graph and its
proportional minimum degree.  Theorem 3 states that, for fixed q and all
sufficiently large class sizes, proportional minimum degree k_q/(k_q+1),
k_q=q-3/2+h_q/2, guarantees a K_q-factor.  At q=3 this is exactly 29/41.
Section 3 says explicitly that the proof exhibits a randomized embedding
algorithm.  Section 3.1 then gives the recursive Factor Finder: q=2 is perfect
matching (Lemma 5), q=3 obtains regular spanning bipartite subgraphs via
Theorem 6 and reduces neighborhood instances to perfect matchings, and Lemma
16 licenses the recursion for larger q.  The final embedding uses the Blow-up
Lemma; reference [5] is its algorithmic version.  Thus an efficient
construction exists in the paper's fixed-q asymptotic regime and Track A would
be false.

What is easy and what is not claimed.  Theorem 3 has an unspecified n_0 and is
not used as the finite generator's existence oracle: every certificate here is
known by inverse generation.  The paper calls q=2 straightforward via Hall's
theorem and reports the conjecturally sharper threshold already proved for
q=3 and q=4, so this family neither uses q=2 nor claims worst-case hardness at
the displayed degree.  Track B is the honest claim.  A graph-only reference
enumerates all possible cross-part triangles and applies exact-cover
backtracking.  Its cubic enumeration is easy for a computer and too large to
execute in-context.  The compact construction coordinate is the residue of a
public vertex tag modulo 997; matching equal coordinates uses 3n reductions.

Generation.  Three independent cyclic difference sets, each containing zero,
produce regular bipartite graphs between A-B, A-C, and B-C.  Their degree is
ceil(29n/41)+degree_extra, so every generated graph meets the paper's exact
q=3 proportional-degree bound.  Independently shuffled tags hide the cyclic
coordinate.  Equal-coordinate triples are cliques because zero belongs to all
three difference sets and they cover every vertex, giving the planted factor
without solving.  Every vertex belongs to that factor and tags in every part
come from the same distribution; there is no separate planted population.
The generator rejects only public orderings solved by the deterministic
lexicographic greedy probe, preventing that incidental row order from being a
shortcut.

Attacks.  Regularity makes degree outliers absent.  Independent public orders
defeat index alignment, tag-magnitude rank alignment, and last-three-decimal
alignment.  A 64-restart local two-swap hill climber enforces both permutation
constraints and optimizes the number of clique rows but does not complete a
factor in the measured panel.  The successful graph-only exact-cover routine
and a stronger randomized greedy that scans currently valid triangles are
reported separately as Track B reference algorithms, never as failed attacks.
""".strip()


_Q = 997
_THRESHOLD_NUM = 29
_THRESHOLD_DEN = 41
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000

# Measured by the harness-owned transcripts shipped beside this module.
_G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _validate_params(n: int, tag_bits: int, degree_extra: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not (5 <= n < _Q):
        raise ValueError("n must be an integer in 5..996")
    if isinstance(tag_bits, bool) or not isinstance(tag_bits, int):
        raise ValueError("tag_bits must be an integer")
    if not (3 <= tag_bits <= 512):
        raise ValueError("tag_bits must lie in 3..512")
    if isinstance(degree_extra, bool) or not isinstance(degree_extra, int):
        raise ValueError("degree_extra must be an integer")
    base = (_THRESHOLD_NUM * n + _THRESHOLD_DEN - 1) // _THRESHOLD_DEN
    if degree_extra < 0 or base + degree_extra > n:
        raise ValueError("degree_extra makes the regular degree invalid")


def _matrix_from_coordinates(
    left: list[int], right: list[int], shifts: set[int], n: int
) -> list[str]:
    return [
        "".join("1" if (v - u) % n in shifts else "0" for v in right)
        for u in left
    ]


def _edge(matrices: dict[str, list[str]], pair: str, i: int, j: int) -> bool:
    return matrices[pair][i][j] == "1"


def _lexicographic_greedy(matrices: dict[str, list[str]], n: int) -> dict | None:
    unused_b = set(range(n))
    unused_c = set(range(n))
    out_b = [-1] * n
    out_c = [-1] * n
    for a in range(n):
        chosen = None
        for b in sorted(unused_b):
            if not _edge(matrices, "AB", a, b):
                continue
            for c in sorted(unused_c):
                if (_edge(matrices, "AC", a, c)
                        and _edge(matrices, "BC", b, c)):
                    chosen = (b, c)
                    break
            if chosen is not None:
                break
        if chosen is None:
            return None
        b, c = chosen
        out_b[a] = b
        out_c[a] = c
        unused_b.remove(b)
        unused_c.remove(c)
    return {"B": out_b, "C": out_c}


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a dense balanced tripartite graph and triangle factor."""
    unknown = set(params) - {"tag_bits", "degree_extra"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    tag_bits = params.get("tag_bits", 48)
    degree_extra = params.get("degree_extra", 0)
    _validate_params(n, tag_bits, degree_extra)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    degree = min(
        n,
        (_THRESHOLD_NUM * n + _THRESHOLD_DEN - 1) // _THRESHOLD_DEN
        + degree_extra,
    )
    rng = random.Random(seed)

    # Conditioning on failure of one fixed public-order greedy rule removes an
    # accidental shortcut; it never searches for the certificate, which is the
    # equal-coordinate factor already known below.
    for _attempt in range(256):
        shifts = []
        for _ in range(3):
            row = {0}
            row.update(rng.sample(range(1, n), degree - 1))
            shifts.append(row)

        coordinates: list[list[int]] = []
        tags: list[list[int]] = []
        lo = 1 << (tag_bits - 1)
        hi = (1 << tag_bits) - 1
        for _part in range(3):
            records = [(_Q * rng.randint(lo, hi) + t, t) for t in range(n)]
            rng.shuffle(records)
            tags.append([tag for tag, _ in records])
            coordinates.append([coord for _, coord in records])

        matrices = {
            "AB": _matrix_from_coordinates(coordinates[0], coordinates[1], shifts[0], n),
            "AC": _matrix_from_coordinates(coordinates[0], coordinates[2], shifts[1], n),
            "BC": _matrix_from_coordinates(coordinates[1], coordinates[2], shifts[2], n),
        }
        if n <= 8 or _lexicographic_greedy(matrices, n) is None:
            break
    else:
        raise RuntimeError("could not remove the lexicographic-order shortcut")

    pos_b = {coord: i for i, coord in enumerate(coordinates[1])}
    pos_c = {coord: i for i, coord in enumerate(coordinates[2])}
    answer = {
        "B": [pos_b[t] for t in coordinates[0]],
        "C": [pos_c[t] for t in coordinates[0]],
    }
    return {
        "paper": "arXiv:0807.4463",
        "family": "dense_tripartite_triangle_factor",
        "n": n,
        "degree": degree,
        "threshold": [_THRESHOLD_NUM, _THRESHOLD_DEN],
        "tag_bits": tag_bits,
        "degree_extra": degree_extra,
        "tags": tags,
        "adjacency": matrices,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a self-contained exact triangle-factor problem."""
    n = inst["n"]
    tags = inst["tags"]
    matrices = inst["adjacency"]
    lines = [
        "Triangle factor in a dense balanced tripartite graph",
        "",
        f"The graph has three disjoint parts A, B, and C, each with {n} vertices.",
        f"Within each part the vertices are indexed 0 through {n - 1}.",
        "Edges occur only between different parts.  Every vertex also has the",
        "displayed integer tag; tags are metadata and impose no validity condition.",
        "",
        "A triangle is a triple (A[a], B[b], C[c]) for which all three edges",
        "A[a]-B[b], A[a]-C[c], and B[b]-C[c] exist.  A triangle factor is",
        f"exactly {n} vertex-disjoint triangles covering every vertex once.",
        "",
        "Tags, in public vertex-index order:",
        "A: " + " ".join(map(str, tags[0])),
        "B: " + " ".join(map(str, tags[1])),
        "C: " + " ".join(map(str, tags[2])),
        "",
        "Adjacency tables are bit matrices.  In AB, row a and column b is 1",
        "exactly when A[a]-B[b] is an edge; AC and BC follow the analogous",
        "source/target order.  Each row is a length-n bit string, and rows appear",
        "in increasing source index.",
    ]
    for pair in ("AB", "AC", "BC"):
        lines.append("")
        lines.append(pair + ":")
        lines.extend(f"{i}: {row}" for i, row in enumerate(matrices[pair]))
    lines.extend([
        "",
        "Return one JSON object {\"B\":[...],\"C\":[...]}.  Both arrays must",
        f"have length {n} and each must be a permutation of 0..{n - 1}.",
        "For every A-index a, the arrays encode the triangle",
        "(A[a], B[B[a]], C[C[a]]).  Arrays are 0-indexed; order is fixed by a;",
        "repeats and omitted vertices are forbidden.",
        "",
        "Give your final answer inside <answer></answer> tags, as that exact JSON object.",
        "Syntax-only example: <answer>{\"B\":[2,0,1],\"C\":[1,2,0]}</answer>",
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
    """Extract the last tagged JSON factor; tolerate prose and fences."""
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
        if not isinstance(value, dict) or set(value) != {"B", "C"}:
            continue
        if all(
            isinstance(value[k], list)
            and all(isinstance(x, int) and not isinstance(x, bool) for x in value[k])
            for k in ("B", "C")
        ):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any triangle factor using the graph only, never the planted answer."""
    if not isinstance(answer, dict) or set(answer) != {"B", "C"}:
        return False, "answer must be a JSON object with exactly the keys B and C"
    b_perm = answer["B"]
    c_perm = answer["C"]
    if not isinstance(b_perm, list) or not isinstance(c_perm, list):
        return False, "B and C must both be JSON arrays"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in b_perm + c_perm):
        return False, "every B and C entry must be an integer vertex index"
    n = inst.get("n")
    if not isinstance(n, int):
        return False, "malformed instance: n is not an integer"
    if len(b_perm) != n or len(c_perm) != n:
        return False, f"B and C must each have length {n}"
    if any(x < 0 or x >= n for x in b_perm + c_perm):
        return False, f"every B and C entry must lie in 0..{n - 1}"
    if len(set(b_perm)) != n:
        return False, "B must be a permutation with no repeated or omitted vertex"
    if len(set(c_perm)) != n:
        return False, "C must be a permutation with no repeated or omitted vertex"
    matrices = inst.get("adjacency")
    if not isinstance(matrices, dict):
        return False, "malformed instance: adjacency tables are absent"
    for a, (b, c) in enumerate(zip(b_perm, c_perm)):
        if not _edge(matrices, "AB", a, b):
            return False, f"row {a} is not a triangle: edge A[{a}]-B[{b}] is absent"
        if not _edge(matrices, "AC", a, c):
            return False, f"row {a} is not a triangle: edge A[{a}]-C[{c}] is absent"
        if not _edge(matrices, "BC", b, c):
            return False, f"row {a} is not a triangle: edge B[{b}]-C[{c}] is absent"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the two-permutation certificate language."""
    n = inst["n"]
    return {"B": rng.sample(range(n), n), "C": rng.sample(range(n), n)}


def search_space(inst: dict) -> int | None:
    """The exact size of the two-permutation certificate language."""
    return math.factorial(inst["n"]) ** 2


def enumerate_all(inst: dict) -> int | None:
    """Count all ordered factor certificates for hand-scale n; cap the work."""
    n = inst["n"]
    if math.factorial(n) ** 2 > _ENUMERATION_CAP:
        return None
    matrices = inst["adjacency"]
    count = 0
    perms = list(itertools.permutations(range(n)))
    for b_perm in perms:
        if any(not _edge(matrices, "AB", a, b) for a, b in enumerate(b_perm)):
            continue
        for c_perm in perms:
            if all(
                _edge(matrices, "AC", a, c_perm[a])
                and _edge(matrices, "BC", b_perm[a], c_perm[a])
                for a in range(n)
            ):
                count += 1
    return count


def _canonical_rows(inst: dict) -> tuple[list[list[int]], dict[str, list[str]]]:
    """Put storage-order relabellings back into tag-residue order."""
    n = inst["n"]
    tags = inst["tags"]
    orders = [sorted(range(n), key=lambda i: (tags[p][i] % _Q, tags[p][i]))
              for p in range(3)]
    matrices = inst["adjacency"]

    def reordered(pair: str, left: int, right: int) -> list[str]:
        return [
            "".join(matrices[pair][i][j] for j in orders[right])
            for i in orders[left]
        ]

    return orders, {
        "AB": reordered("AB", 0, 1),
        "AC": reordered("AC", 0, 2),
        "BC": reordered("BC", 1, 2),
    }


def canonical_key(inst: dict) -> str:
    """Canonicalize every within-part storage relabelling using public tags."""
    _, matrices = _canonical_rows(inst)
    payload = {
        "n": inst["n"],
        "AB": matrices["AB"],
        "AC": matrices["AC"],
        "BC": matrices["BC"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase tag arithmetic and tighten density before lengthening the answer."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    p.setdefault("tag_bits", 48)
    p.setdefault("degree_extra", 0)
    if p["tag_bits"] < 256:
        p["tag_bits"] = min(256, p["tag_bits"] + 32)
        p["degree_extra"] = max(0, p["degree_extra"] - 1)
        return p
    if p.get("n", 0) < 97:
        p["n"] = 97
        p["degree_extra"] = 0
        return p
    return None


def _valid_rows(inst: dict, candidate: dict) -> int:
    matrices = inst["adjacency"]
    return sum(
        _edge(matrices, "AB", a, b)
        and _edge(matrices, "AC", a, c)
        and _edge(matrices, "BC", b, c)
        for a, (b, c) in enumerate(zip(candidate["B"], candidate["C"]))
    )


def _attack_index_alignment(inst: dict) -> dict:
    n = inst["n"]
    return {"B": list(range(n)), "C": list(range(n))}


def _attack_tag_magnitude_rank(inst: dict) -> dict:
    n = inst["n"]
    tags = inst["tags"]
    order = [sorted(range(n), key=lambda i: tags[p][i]) for p in range(3)]
    b_perm = [-1] * n
    c_perm = [-1] * n
    for rank, a in enumerate(order[0]):
        b_perm[a] = order[1][rank]
        c_perm[a] = order[2][rank]
    return {"B": b_perm, "C": c_perm}


def _attack_last_three_digits(inst: dict) -> dict:
    n = inst["n"]
    tags = inst["tags"]
    order = [sorted(range(n), key=lambda i: (tags[p][i] % 1000, i)) for p in range(3)]
    b_perm = [-1] * n
    c_perm = [-1] * n
    for rank, a in enumerate(order[0]):
        b_perm[a] = order[1][rank]
        c_perm[a] = order[2][rank]
    return {"B": b_perm, "C": c_perm}


def _attack_local_swap(inst: dict, rng: random.Random) -> dict:
    """64 random restarts, each with 4n non-decreasing two-row swaps."""
    n = inst["n"]
    best: dict | None = None
    best_score = -1
    for _ in range(64):
        cand = random_candidate(inst, rng)
        score = _valid_rows(inst, cand)
        if score > best_score:
            best = {"B": cand["B"][:], "C": cand["C"][:]}
            best_score = score
        for _step in range(4 * n):
            kind = rng.randrange(3)
            i, j = rng.sample(range(n), 2)
            matrices = inst["adjacency"]

            def row_good(a: int) -> bool:
                b = cand["B"][a]
                c = cand["C"][a]
                return (
                    _edge(matrices, "AB", a, b)
                    and _edge(matrices, "AC", a, c)
                    and _edge(matrices, "BC", b, c)
                )

            old = int(row_good(i)) + int(row_good(j))
            if kind in (0, 2):
                cand["B"][i], cand["B"][j] = cand["B"][j], cand["B"][i]
            if kind in (1, 2):
                cand["C"][i], cand["C"][j] = cand["C"][j], cand["C"][i]
            new = int(row_good(i)) + int(row_good(j))
            if new < old:
                if kind in (0, 2):
                    cand["B"][i], cand["B"][j] = cand["B"][j], cand["B"][i]
                if kind in (1, 2):
                    cand["C"][i], cand["C"][j] = cand["C"][j], cand["C"][i]
            else:
                score += new - old
                if score > best_score:
                    best = {"B": cand["B"][:], "C": cand["C"][:]}
                    best_score = score
            if score == n:
                return cand
    assert best is not None
    return best


def _reference_algorithm(inst: dict, node_cap: int = 1_000_000) -> tuple[dict | None, dict]:
    """Graph-only triangle enumeration followed by exact-cover backtracking."""
    n = inst["n"]
    matrices = inst["adjacency"]
    t0 = time.perf_counter()
    edge_probes = 0
    candidates: list[list[tuple[int, int]]] = []
    for a in range(n):
        rows = []
        for b in range(n):
            for c in range(n):
                edge_probes += 3
                if (_edge(matrices, "AB", a, b)
                        and _edge(matrices, "AC", a, c)
                        and _edge(matrices, "BC", b, c)):
                    rows.append((b, c))
        random.Random(1_000_003 + a).shuffle(rows)
        candidates.append(rows)

    order = sorted(range(n), key=lambda a: len(candidates[a]))
    used_b = [False] * n
    used_c = [False] * n
    b_perm = [-1] * n
    c_perm = [-1] * n
    nodes = 0
    pair_trials = 0

    def dfs(k: int) -> bool:
        nonlocal nodes, pair_trials
        nodes += 1
        if nodes > node_cap:
            return False
        if k == n:
            return True
        a = order[k]
        for b, c in candidates[a]:
            pair_trials += 1
            if used_b[b] or used_c[c]:
                continue
            used_b[b] = True
            used_c[c] = True
            b_perm[a] = b
            c_perm[a] = c
            if dfs(k + 1):
                return True
            used_b[b] = False
            used_c[c] = False
        return False

    solved = dfs(0)
    elapsed = time.perf_counter() - t0
    answer = {"B": b_perm, "C": c_perm} if solved else None
    return answer, {
        "edge_probes": edge_probes,
        "nodes": nodes,
        "pair_trials": pair_trials,
        "operations": edge_probes + pair_trials,
        "wall_clock_sec": elapsed,
    }


def _reference_random_valid_greedy(
    inst: dict, rng: random.Random, restarts: int = 64
) -> tuple[dict | None, dict]:
    """Graph-aware random greedy; successful behavior belongs to Track B's baseline."""
    n = inst["n"]
    matrices = inst["adjacency"]
    edge_probes = 0
    t0 = time.perf_counter()
    for restart in range(1, restarts + 1):
        order = list(range(n))
        rng.shuffle(order)
        unused_b = set(range(n))
        unused_c = set(range(n))
        b_perm = [-1] * n
        c_perm = [-1] * n
        complete = True
        for a in order:
            choices = []
            for b in unused_b:
                for c in unused_c:
                    edge_probes += 3
                    if (_edge(matrices, "AB", a, b)
                            and _edge(matrices, "AC", a, c)
                            and _edge(matrices, "BC", b, c)):
                        choices.append((b, c))
            if not choices:
                complete = False
                break
            b, c = rng.choice(choices)
            b_perm[a] = b
            c_perm[a] = c
            unused_b.remove(b)
            unused_c.remove(c)
        if complete:
            return {"B": b_perm, "C": c_perm}, {
                "edge_probes": edge_probes,
                "restarts": restart,
                "wall_clock_sec": time.perf_counter() - t0,
            }
    return None, {
        "edge_probes": edge_probes,
        "restarts": restarts,
        "wall_clock_sec": time.perf_counter() - t0,
    }


def _permute_storage(inst: dict, rng: random.Random) -> dict:
    """Relabel all three public index sets and carry the witness."""
    n = inst["n"]
    new_to_old = []
    old_to_new = []
    for _ in range(3):
        p = list(range(n))
        rng.shuffle(p)
        inv = [0] * n
        for new, old in enumerate(p):
            inv[old] = new
        new_to_old.append(p)
        old_to_new.append(inv)
    old_m = inst["adjacency"]

    def matrix(pair: str, left: int, right: int) -> list[str]:
        return [
            "".join(old_m[pair][new_to_old[left][i]][new_to_old[right][j]]
                    for j in range(n))
            for i in range(n)
        ]

    old_answer = inst["answer"]
    b_perm = [-1] * n
    c_perm = [-1] * n
    for new_a, old_a in enumerate(new_to_old[0]):
        b_perm[new_a] = old_to_new[1][old_answer["B"][old_a]]
        c_perm[new_a] = old_to_new[2][old_answer["C"][old_a]]
    out = dict(inst)
    out["tags"] = [
        [inst["tags"][part][old] for old in new_to_old[part]]
        for part in range(3)
    ]
    out["adjacency"] = {
        "AB": matrix("AB", 0, 1),
        "AC": matrix("AC", 0, 2),
        "BC": matrix("BC", 1, 2),
    }
    out["answer"] = {"B": b_perm, "C": c_perm}
    return out


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(v) for v in value)
    return 1


def _find_invalid_swap(inst: dict) -> dict:
    answer = {"B": inst["answer"]["B"][:], "C": inst["answer"]["C"][:]}
    n = inst["n"]
    for i in range(n):
        for j in range(i + 1, n):
            trial = {"B": answer["B"][:], "C": answer["C"][:]}
            trial["B"][i], trial["B"][j] = trial["B"][j], trial["B"][i]
            ok, why = verify(inst, trial)
            if not ok and "not a triangle" in why:
                return trial
    raise AssertionError("no edge-breaking planted-coordinate swap exists")


def selftest() -> dict:
    """Run gates G1--G9 and return their machine-readable measurements."""
    report: dict[str, Any] = {"track": TRACK, "shipping": SHIPPING_DIFFICULTY}

    # G1: every preset, four unrelated seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260807, **shipping_params)

    # G2: five syntactically different corruptions and distinct diagnostics.
    planted = inst["answer"]
    corruptions = {
        "empty": [],
        "drop_one": {"B": planted["B"][:-1], "C": planted["C"][:]},
        "duplicate": {"B": [planted["B"][0]] + planted["B"][:-1],
                      "C": planted["C"][:]},
        "out_of_range": {"B": [inst["n"]] + planted["B"][1:],
                         "C": planted["C"][:]},
        "swap": _find_invalid_swap(inst),
    }
    rejection_reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        rejection_reasons[name] = {"rejected": not ok, "reason": why}
    distinct_reasons = len({row["reason"] for row in rejection_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejection_reasons.values())
        and distinct_reasons == len(rejection_reasons),
        "distinct_reasons": distinct_reasons,
        "cases": rejection_reasons,
    }

    # G3: realistic prose and a fenced answer round-trip.
    answer_json = json.dumps(planted, separators=(",", ":"))
    model_style = (
        "I matched the three parts and checked all pairwise edges.\n"
        "<answer>\n```json\n" + answer_json + "\n```\n</answer>\n"
        "The arrays use zero-based indices."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_equals_answer": parsed == planted,
    }

    # G4 and the shipping density component of G5.
    guess_rng = random.Random(445566)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
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
        "pass": reference_ok and isinstance(guess_fraction, float)
        and demo_count is not None,
        "shipping_valid_hits": guess_hits,
        "shipping_samples": guess_total,
        "shipping_density_estimate": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": reference_cost["wall_clock_sec"],
        "baseline_operations": reference_cost["operations"],
        "baseline_nodes": reference_cost["nodes"],
    }

    # G6: four failed construction-aware/in-context attacks over eight seeds.
    attack_names = (
        "outlier_regular_degree_index_alignment",
        "greedy_lexicographic",
        "random_restart_64_local_swap",
        "by_hand_tag_magnitude_or_decimal_rank",
    )
    attacks = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    ref_successes = 0
    ref_operations = 0
    ref_nodes = 0
    ref_wall = 0.0
    greedy_ref_successes = 0
    greedy_ref_probes = 0
    greedy_ref_restarts = 0
    greedy_ref_wall = 0.0
    for seed in range(31001, 31009):
        attack_inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            attack_names[0]: _attack_index_alignment(attack_inst),
            attack_names[1]: _lexicographic_greedy(
                attack_inst["adjacency"], attack_inst["n"]
            ),
            attack_names[2]: _attack_local_swap(
                attack_inst, random.Random(seed ^ 0xA5A5A5A5)
            ),
            attack_names[3]: _attack_tag_magnitude_rank(attack_inst),
        }
        # The fourth attack tries two obvious visual readings; either solving counts.
        decimal = _attack_last_three_digits(attack_inst)
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            success = candidate is not None and verify(attack_inst, candidate)[0]
            if name == attack_names[3]:
                success = success or verify(attack_inst, decimal)[0]
            attacks[name]["successes"] += int(success)
        found, cost = _reference_algorithm(attack_inst)
        ref_successes += int(found is not None and verify(attack_inst, found)[0])
        ref_operations += cost["operations"]
        ref_nodes += cost["nodes"]
        ref_wall += cost["wall_clock_sec"]
        greedy_found, greedy_cost = _reference_random_valid_greedy(
            attack_inst, random.Random(seed ^ 0x5A5A5A5A)
        )
        greedy_ref_successes += int(
            greedy_found is not None and verify(attack_inst, greedy_found)[0]
        )
        greedy_ref_probes += greedy_cost["edge_probes"]
        greedy_ref_restarts += greedy_cost["restarts"]
        greedy_ref_wall += greedy_cost["wall_clock_sec"]
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8 and greedy_ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "triangle enumeration plus exact-cover backtracking (Algorithm X)",
            "complexity": "O(n^3) preprocessing plus exponential worst-case search",
            "wall_clock_sec": ref_wall,
            "operations": ref_operations,
            "nodes": ref_nodes,
            "solves": f"{ref_successes}/8, as expected on Track B",
            "randomized_valid_triangle_greedy": {
                "complexity": "O(R*n^3) with at most 64 restarts",
                "wall_clock_sec": greedy_ref_wall,
                "edge_probes": greedy_ref_probes,
                "restarts": greedy_ref_restarts,
                "solves": f"{greedy_ref_successes}/8, as expected on Track B",
            },
        },
    }

    # G7: literal size doubling from the shipping class size.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = shipping_params["n"] * 2
    doubled = make_instance(seed=8675309, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verification": doubled_why,
        "shipping_search_space_bits": search_space(inst).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    # G8: within-part relabelling, compositions, carried witnesses, diversity.
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

    # G9(a) is externally measured; (b) and the exact size/effort caps are gated.
    compact_answer = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(compact_answer)
    answer_atoms = _atomic_elements(planted)
    # Conservative JSON-token estimate: each number and each punctuation/name token.
    answer_tokens = len(re.findall(r"\d+|[\[\]{},:]|[A-Za-z]+", compact_answer))
    intended_ops = 3 * inst["n"]
    arms = {k: dict(_G9_EVIDENCE[k]) for k in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    hinted_still_hardened = _G9_EVIDENCE["hinted_verdict"] == "hardened"
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
