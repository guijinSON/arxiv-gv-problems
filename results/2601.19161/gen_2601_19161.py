"""Verified inverse generator for a restricted 3-local Permutation Mastermind CSP.

This module is intentionally standard-library-only and has no import side effects.
The compact clause representation expands to the 3-local query gadget in Section 6
of arXiv:2601.19161.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import time
from collections import Counter, deque
from fractions import Fraction


DIFFICULTY = {
    "easy": {"n": 36, "clause_ratio": 0.82},
    "medium": {"n": 72, "clause_ratio": 0.82},
    "hard": {"n": 120, "clause_ratio": 0.82},
    "extreme": {"n": 180, "clause_ratio": 0.82},
}

SHIPPING_DIFFICULTY = "hard"

NOTES = r"""
The exact definition comes from Section 1 (black-peg score and ell_k locality)
and Section 6 (3-Local-PM-SAT) of Subercaseaux, arXiv:2601.19161v2.  The nine
move clause gadget and Claim 24 in that section fix the two allowed block cycles
alpha=(2,3,1), beta=(3,1,2), the forward feedback (0,0,0,0,0,0,1,2,3), and
the fact that it means exactly one alpha block.  Theorem 28 is the easy-regime
warning: support-2 locality is in RP in O(N^7 log^2 N), so this generator uses
support exactly 3 and never silently falls back to transpositions.

Generation samples the complete witness first, with one third alpha blocks,
then draws every clause with one alpha and two beta blocks.  Alpha and beta
variables have exactly the same degree-2/degree-3 mixture; block labels and
clause order are shuffled.  This removes position and occurrence-count plant
signatures.  Connected incidence graphs remove component-by-component solving.
The self-test attacks degree/two-hop outliers, greedy exact cover, and bounded
random-restart swap descent.  The candidate sampler knows the block restriction
and the degree-sum checksum obtained by adding all exact-one equations; it does
not sample arbitrary permutations or arbitrary bit strings.
""".strip()


_FORWARD_SCORES = (0, 0, 0, 0, 0, 0, 1, 2, 3)
_REVERSE_SCORES = (2, 1, 0, 0, 0, 0, 0, 0, 0)
_ENUMERATION_CAP = 500_000


def _rounded_clause_count(n: int, ratio: float) -> int:
    # A 2/3..1 density gives every variable degree 2 or 3 in the construction.
    m = int(math.floor(n * ratio + 0.5))
    return max(2 * (n // 3), min(n - 1, m))


def _connected(n: int, clauses: list[tuple[int, int, int]]) -> bool:
    """Whether the variable/clause incidence graph is connected."""
    total = n + len(clauses)
    adj = [[] for _ in range(total)]
    for j, clause in enumerate(clauses):
        cj = n + j
        for v in clause:
            adj[v].append(cj)
            adj[cj].append(v)
    seen = {0}
    todo = [0]
    while todo:
        u = todo.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                todo.append(v)
    return len(seen) == total


def _answer_from_bits(bits: list[int]) -> list[int]:
    answer: list[int] = []
    for i, bit in enumerate(bits):
        a, b, c = 3 * i + 1, 3 * i + 2, 3 * i + 3
        answer.extend((b, c, a) if bit else (c, a, b))
    return answer


def _bits_from_well_formed_answer(answer: list[int]) -> list[int] | None:
    bits = []
    for i in range(len(answer) // 3):
        a, b, c = 3 * i + 1, 3 * i + 2, 3 * i + 3
        block = tuple(answer[3 * i : 3 * i + 3])
        if block == (b, c, a):
            bits.append(1)
        elif block == (c, a, b):
            bits.append(0)
        else:
            return None
    return bits


def _apply_cycle(guess: list[int], positions: tuple[int, int, int], kind: str) -> None:
    """Apply the render() convention at zero-indexed positions."""
    p, q, r = positions
    old = guess[p], guess[q], guess[r]
    new = (old[1], old[2], old[0]) if kind == "A" else (old[2], old[0], old[1])
    guess[p], guess[q], guess[r] = new


def _expanded_clause_scores(bits: tuple[int, int, int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Expand one three-block gadget; used to test the compact equivalence."""
    secret = _answer_from_bits(list(bits))
    blocks = ((0, 1, 2), (3, 4, 5), (6, 7, 8))
    forward = [
        *(('A', tuple(block[j] for block in blocks)) for j in range(3)),
        *(('A', block) for block in blocks),
        *(('B', tuple(block[j] for block in blocks)) for j in range(3)),
    ]
    guess = list(range(1, 10))
    scores_out = []
    for kind, positions in forward:
        _apply_cycle(guess, positions, kind)
        scores_out.append(sum(a == b for a, b in zip(guess, secret)))
    scores_back = []
    for kind, positions in reversed(forward):
        _apply_cycle(guess, positions, "B" if kind == "A" else "A")
        scores_back.append(sum(a == b for a, b in zip(guess, secret)))
    assert guess == list(range(1, 10))
    return tuple(scores_out), tuple(scores_back)


def _generate_formula(
    n: int, m: int, planted: list[int], rng: random.Random
) -> tuple[list[tuple[int, int, int]], list[int]]:
    """Configuration-model formula with equal degree law on both plant sides."""
    true_vars = [i for i, x in enumerate(planted) if x]
    false_vars = [i for i, x in enumerate(planted) if not x]
    q = n // 3
    high_true = m - 2 * q
    if not (0 <= high_true <= q):
        raise ValueError("clause_ratio must yield between 2n/3 and n clauses")

    degree = [2] * n
    for v in rng.sample(true_vars, high_true):
        degree[v] = 3
    # Twice as many false variables get degree 3, preserving the degree law.
    for v in rng.sample(false_vars, 2 * high_true):
        degree[v] = 3

    t_stubs = [v for v in true_vars for _ in range(degree[v])]
    f_stubs = [v for v in false_vars for _ in range(degree[v])]
    assert len(t_stubs) == m and len(f_stubs) == 2 * m

    # Reject loops, repeated clauses, and disconnected factor graphs.  The
    # degree sequence stays fixed, so retrying does not introduce a degree leak.
    for _ in range(20_000):
        ts = t_stubs[:]
        fs = f_stubs[:]
        rng.shuffle(ts)
        rng.shuffle(fs)
        clauses = []
        seen = set()
        okay = True
        for j in range(m):
            f1, f2 = fs[2 * j], fs[2 * j + 1]
            if f1 == f2:
                okay = False
                break
            clause = (ts[j], f1, f2)
            signature = tuple(sorted(clause))
            if signature in seen:
                okay = False
                break
            seen.add(signature)
            row = list(clause)
            rng.shuffle(row)
            clauses.append(tuple(row))
        if okay and _connected(n, clauses):
            rng.shuffle(clauses)
            return clauses, degree
    raise RuntimeError("could not draw a simple connected planted formula")


def make_instance(n, seed=0, **params) -> dict:
    """Sample a secret first, then build a compatible 3-local transcript.

    ``n`` is the number of three-position blocks; the actual permutation has
    length ``3*n``.  Larger n increases both the Boolean core and permutation.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 9 or n % 3:
        raise ValueError("n must be an integer multiple of 3 and at least 9")
    ratio = params.pop("clause_ratio", 0.82)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
        raise TypeError("clause_ratio must be a number")
    ratio = float(ratio)
    if not (2 / 3 <= ratio < 1):
        raise ValueError("clause_ratio must be in [2/3, 1)")

    rng = random.Random(seed)
    q = n // 3
    true_set = set(rng.sample(range(n), q))
    planted = [int(i in true_set) for i in range(n)]
    m = _rounded_clause_count(n, ratio)
    clauses, degree = _generate_formula(n, m, planted, rng)
    answer = _answer_from_bits(planted)
    return {
        "family": "restricted-3-local-permutation-mastermind",
        "n": n,
        "permutation_size": 3 * n,
        "clause_ratio": ratio,
        "clauses": [list(c) for c in clauses],
        "degrees": degree,
        "answer": answer,
    }


def _fmt_clause(c: list[int]) -> str:
    return " ".join(str(x + 1) for x in c)


def render(inst) -> str:
    """Render a complete, standalone statement and an exact output contract."""
    n = inst["n"]
    N = 3 * n
    m = len(inst["clauses"])
    degree = _degrees(inst)
    checksum = len(inst["clauses"])
    clauses = "\n".join(
        f"{j + 1}: {_fmt_clause(c)}" for j, c in enumerate(inst["clauses"])
    )
    return f"""Restricted 3-local permutation Mastermind witness problem

A permutation of 1,...,{N} is an ordered list in which every integer occurs
exactly once.  Positions and values are both 1-indexed.  Split them into {n}
ordered blocks: block i consists of 3i-2, 3i-1, 3i.  A permitted secret must use
one of exactly two orientations independently in every block:

  A_i = (3i-1, 3i, 3i-2)
  B_i = (3i, 3i-2, 3i-1).

The full secret is the concatenation of those {n} block triples, in block order.
Thus order matters, values may not repeat, and no other block orientation is
allowed.

Here is the lossless compact representation of a black-peg transcript.  A
black-peg score is the number of positions where a query permutation equals the
secret.  For three positions p,q,r, move A(p,q,r) replaces the current entries
(g[p],g[q],g[r]) by (g[q],g[r],g[p]); move B(p,q,r) is its inverse.  Each move
changes exactly three positions, so consecutive queries are 3-local.

For every listed clause (i,j,k), start at the identity query and perform:

  A(3i-2,3j-2,3k-2), A(3i-1,3j-1,3k-1), A(3i,3j,3k),
  A(3i-2,3i-1,3i), A(3j-2,3j-1,3j), A(3k-2,3k-1,3k),
  B(3i-2,3j-2,3k-2), B(3i-1,3j-1,3k-1), B(3i,3j,3k).

The nine resulting black-peg scores must be
  0 0 0 0 0 0 1 2 3.
Then undo those nine moves in reverse order; the resulting scores must be
  2 1 0 0 0 0 0 0 0,
returning to the identity (whose score is 0) before the next clause.  This is a
complete procedural specification of every query permutation and score; there
are no omitted queries.  For the two permitted block orientations, matching the
gadget is equivalent to requiring exactly one of blocks i,j,k to have type A.

As a redundant check obtainable by adding all clause equations, if d_i is the
number of listed clauses containing block i and x_i is 1 for type A (0 for B),
then sum(d_i*x_i) must equal {checksum}.  Here the degree list d_1,...,d_{n} is:
  {' '.join(map(str, degree))}

Instance: {m} clauses.  Each row is "row_number: i j k" and contains three
distinct 1-indexed block numbers.  Clause order and the order within a row have
no semantic effect.
{clauses}

Find any permitted secret permutation matching every score in the transcript.
Give your final answer inside <answer></answer> tags, as all {N} integers of the
permutation in position order, separated by commas.
Format example for a two-block permutation: <answer>2, 3, 1, 6, 4, 5</answer>
Output nothing else inside the tags.
"""


def parse_answer(text) -> object | None:
    """Extract the last well-formed tagged comma/whitespace integer list."""
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for raw in reversed(bodies):
        body = raw.strip()
        if not body or not re.fullmatch(r"[+-]?\d+(?:\s*(?:,|\s)\s*[+-]?\d+)*", body):
            continue
        try:
            pieces = re.findall(r"[+-]?\d+", body)
            return [int(x) for x in pieces]
        except (TypeError, ValueError):
            continue
    return None


def _degrees(inst) -> list[int]:
    n = inst["n"]
    degrees = [0] * n
    for clause in inst["clauses"]:
        for v in clause:
            degrees[v] += 1
    return degrees


def verify(inst, answer) -> tuple[bool, str]:
    """Check any witness without consulting the planted ``inst['answer']``."""
    n = inst.get("n")
    N = 3 * n
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of integers"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != N:
        return False, f"wrong length: expected {N} integers, got {len(answer)}"
    for i, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry at position {i + 1} is not an integer"
        if not 1 <= value <= N:
            return False, f"value at position {i + 1} is out of range 1..{N}"
    counts = Counter(answer)
    duplicate = next((x for x, count in counts.items() if count > 1), None)
    if duplicate is not None:
        return False, f"values must be a permutation; duplicate value {duplicate}"

    values = list(answer)
    bits = _bits_from_well_formed_answer(values)
    if bits is None:
        for i in range(n):
            a, b, c = 3 * i + 1, 3 * i + 2, 3 * i + 3
            if tuple(values[3 * i : 3 * i + 3]) not in ((b, c, a), (c, a, b)):
                return False, f"block {i + 1} is neither allowed orientation A nor B"
        return False, "invalid block orientation"

    # Substitution into the exact-one equation is the compressed exact check of
    # all 18 gadget scores (the eight-case table in the paper's Claim 24).
    for j, clause in enumerate(inst["clauses"]):
        total = sum(bits[v] for v in clause)
        if total != 1:
            return (
                False,
                f"clause {j + 1} transcript mismatch: expected exactly one A block, got {total}",
            )
    return True, "ok"


def _checksum_compositions(inst) -> list[tuple[int, int, int]]:
    """(ways, chosen degree-2 count, chosen degree-3 count)."""
    degree = _degrees(inst)
    n2 = degree.count(2)
    n3 = degree.count(3)
    target = len(inst["clauses"])
    result = []
    for b in range(n3 + 1):
        rem = target - 3 * b
        if rem >= 0 and rem % 2 == 0:
            a = rem // 2
            if a <= n2:
                result.append((math.comb(n2, a) * math.comb(n3, b), a, b))
    return result


def random_candidate(inst, rng) -> object:
    """Uniform candidate after block-shape and summed-equation deductions."""
    if not hasattr(rng, "randrange") or not hasattr(rng, "sample"):
        raise TypeError("rng must provide random.Random-style methods")
    degree = _degrees(inst)
    deg2 = [i for i, d in enumerate(degree) if d == 2]
    deg3 = [i for i, d in enumerate(degree) if d == 3]
    choices = _checksum_compositions(inst)
    total = sum(row[0] for row in choices)
    pick = rng.randrange(total)
    a = b = 0
    for ways, ca, cb in choices:
        if pick < ways:
            a, b = ca, cb
            break
        pick -= ways
    bits = [0] * inst["n"]
    for i in rng.sample(deg2, a):
        bits[i] = 1
    for i in rng.sample(deg3, b):
        bits[i] = 1
    return _answer_from_bits(bits)


def search_space(inst) -> int | None:
    """Number of structurally legal candidates obeying the obvious checksum."""
    return sum(row[0] for row in _checksum_compositions(inst))


def enumerate_all(inst) -> int | None:
    """Count all valid witnesses exactly when at most 500k candidates exist."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    degree = _degrees(inst)
    deg2 = [i for i, d in enumerate(degree) if d == 2]
    deg3 = [i for i, d in enumerate(degree) if d == 3]
    found = 0
    for _, a, b in _checksum_compositions(inst):
        for left in itertools.combinations(deg2, a):
            for right in itertools.combinations(deg3, b):
                chosen = set(left)
                chosen.update(right)
                if all(sum(v in chosen for v in c) == 1 for c in inst["clauses"]):
                    found += 1
    return found


def _wl_payload(inst) -> dict:
    """Strong isomorphism invariant of the variable/clause incidence graph."""
    n = inst["n"]
    clauses = [tuple(c) for c in inst["clauses"]]
    m = len(clauses)
    adj = [[] for _ in range(n + m)]
    for j, clause in enumerate(clauses):
        node = n + j
        for v in clause:
            adj[v].append(node)
            adj[node].append(v)

    colors = [0] * n + [1] * m
    for _ in range(n + m):
        signatures = [(colors[u], tuple(sorted(colors[v] for v in adj[u]))) for u in range(n + m)]
        palette = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new = [palette[sig] for sig in signatures]
        if new == colors:
            break
        colors = new

    variable_rows = sorted(
        (colors[v], len(adj[v]), tuple(sorted(colors[c] for c in adj[v]))) for v in range(n)
    )
    clause_rows = sorted(
        (colors[n + j], tuple(sorted(colors[v] for v in clause)))
        for j, clause in enumerate(clauses)
    )
    # Pairwise co-occurrence profile strengthens 1-WL but remains label-free.
    pair_counts = Counter()
    for clause in clauses:
        for a, b in itertools.combinations(clause, 2):
            ca, cb = sorted((colors[a], colors[b]))
            pair_counts[(ca, cb)] += 1
    return {
        "n": n,
        "m": m,
        "variables": variable_rows,
        "clauses": clause_rows,
        "colored_pairs": sorted((a, b, k) for (a, b), k in pair_counts.items()),
    }


def canonical_key(inst) -> str:
    """Invariant under block relabelling and all clause/input reorderings."""
    raw = json.dumps(_wl_payload(inst), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | None:
    """Grow the connected planted core while keeping its hard sparse density."""
    n = int(params.get("n", 36))
    if n >= 405:
        return None
    new_n = 3 * math.ceil((1.5 * n) / 3)
    return {"n": new_n, "clause_ratio": float(params.get("clause_ratio", 0.82))}


# ---------------------------------------------------------------------------
# Self-test attacks.  None of these helpers ever reads inst["answer"].


def _violations(inst, bits: list[int]) -> int:
    return sum(sum(bits[v] for v in clause) != 1 for clause in inst["clauses"])


def _outlier_attack(inst) -> list[int]:
    degree = _degrees(inst)
    incident = [[] for _ in range(inst["n"])]
    for clause in inst["clauses"]:
        for v in clause:
            incident[v].extend(u for u in clause if u != v)
    # A per-variable occurrence/two-hop score, with input position only a tie-break.
    stat = [degree[v] * 1000 + sum(degree[u] for u in incident[v]) for v in range(inst["n"])]
    d2 = [i for i, d in enumerate(degree) if d == 2]
    d3 = [i for i, d in enumerate(degree) if d == 3]
    best_bits = None
    best_score = None
    for _, a, b in _checksum_compositions(inst):
        bits = [0] * inst["n"]
        chosen2 = sorted(d2, key=lambda v: (-stat[v], v))[:a]
        chosen3 = sorted(d3, key=lambda v: (-stat[v], v))[:b]
        for v in chosen2 + chosen3:
            bits[v] = 1
        score = sum(stat[v] for v in chosen2 + chosen3)
        if best_score is None or score > best_score:
            best_score, best_bits = score, bits
    return _answer_from_bits(best_bits or [0] * inst["n"])


def _greedy_attack(inst) -> list[int]:
    degree = _degrees(inst)
    by_degree = {2: [i for i, d in enumerate(degree) if d == 2], 3: [i for i, d in enumerate(degree) if d == 3]}
    incidence = [[] for _ in range(inst["n"])]
    for j, clause in enumerate(inst["clauses"]):
        for v in clause:
            incidence[v].append(j)
    best = None
    best_bad = len(inst["clauses"]) + 1
    for _, need2, need3 in _checksum_compositions(inst):
        quota = {2: need2, 3: need3}
        bits = [0] * inst["n"]
        covered = [0] * len(inst["clauses"])
        for _step in range(need2 + need3):
            candidates = [
                v for d in (2, 3) if quota[d] > 0 for v in by_degree[d] if not bits[v]
            ]
            if not candidates:
                break
            def merit(v):
                overlap = sum(covered[j] > 0 for j in incidence[v])
                fresh = len(incidence[v]) - overlap
                return (fresh - 5 * overlap, fresh, -v)
            v = max(candidates, key=merit)
            bits[v] = 1
            quota[degree[v]] -= 1
            for j in incidence[v]:
                covered[j] += 1
        bad = _violations(inst, bits)
        if bad < best_bad:
            best_bad, best = bad, bits
    return _answer_from_bits(best or [0] * inst["n"])


def _random_restart_attack(inst, rng: random.Random) -> list[int]:
    degree = _degrees(inst)
    best_answer = random_candidate(inst, rng)
    best_bits = _bits_from_well_formed_answer(best_answer)
    best_bad = _violations(inst, best_bits)
    for _restart in range(4):
        answer = random_candidate(inst, rng)
        bits = _bits_from_well_formed_answer(answer)
        bad = _violations(inst, bits)
        for _step in range(8 * inst["n"]):
            selected = {d: [] for d in (2, 3)}
            unselected = {d: [] for d in (2, 3)}
            for v, bit in enumerate(bits):
                (selected if bit else unselected)[degree[v]].append(v)
            moves = []
            for _ in range(14):
                d = 2 if rng.randrange(2) == 0 else 3
                if selected[d] and unselected[d]:
                    moves.append((rng.choice(selected[d]), rng.choice(unselected[d])))
            if not moves:
                break
            scored = []
            for old, new in moves:
                bits[old], bits[new] = 0, 1
                score = _violations(inst, bits)
                bits[old], bits[new] = 1, 0
                scored.append((score, old, new))
            score, old, new = min(scored)
            if score < bad or (score == bad and rng.random() < 0.04):
                bits[old], bits[new] = 0, 1
                bad = score
            if bad < best_bad:
                best_bad = bad
                best_bits = bits[:]
            if bad == 0:
                return _answer_from_bits(bits)
    return _answer_from_bits(best_bits)


def _linear_zero_free_attack(inst) -> list[int] | None:
    """Gaussian elimination over Q, assigning every free variable zero."""
    n = inst["n"]
    matrix = []
    for clause in inst["clauses"]:
        row = [Fraction(0) for _ in range(n + 1)]
        for v in clause:
            row[v] = Fraction(1)
        row[-1] = Fraction(1)
        matrix.append(row)
    rank = 0
    pivots = []
    for col in range(n):
        pivot = next((r for r in range(rank, len(matrix)) if matrix[r][col]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        scale = matrix[rank][col]
        matrix[rank] = [x / scale for x in matrix[rank]]
        for r in range(len(matrix)):
            if r != rank and matrix[r][col]:
                scale = matrix[r][col]
                matrix[r] = [a - scale * b for a, b in zip(matrix[r], matrix[rank])]
        pivots.append(col)
        rank += 1
        if rank == len(matrix):
            break
    bits = [Fraction(0)] * n
    for row, col in reversed(list(zip(matrix[:rank], pivots))):
        bits[col] = row[-1] - sum(row[j] * bits[j] for j in range(col + 1, n))
    if any(x.denominator != 1 or x not in (0, 1) for x in bits):
        return None
    return _answer_from_bits([int(x) for x in bits])


def _transformed_copy(
    inst,
    rng: random.Random,
    *,
    relabel_blocks: bool,
    reorder_clauses: bool,
    reorder_members: bool,
) -> tuple[dict, list[int]]:
    """Apply any composition of the family's three relabelling symmetries."""
    n = inst["n"]
    old_to_new = list(range(n))
    if relabel_blocks:
        rng.shuffle(old_to_new)
    clauses = []
    source = list(inst["clauses"])
    if reorder_clauses:
        rng.shuffle(source)
    for clause in source:
        row = [old_to_new[v] for v in clause]
        if reorder_members:
            rng.shuffle(row)
        clauses.append(row)

    original_bits = _bits_from_well_formed_answer(list(inst["answer"]))
    carried_bits = [0] * n
    for old, new in enumerate(old_to_new):
        carried_bits[new] = original_bits[old]
    transformed = {
        "family": inst["family"],
        "n": n,
        "permutation_size": 3 * n,
        "clause_ratio": inst["clause_ratio"],
        "clauses": clauses,
        "degrees": [],  # deliberately stale/ignored; canonical_key recomputes
        "answer": _answer_from_bits(carried_bits),
    }
    return transformed, transformed["answer"]


def selftest() -> dict:
    """Run G1--G8 and return a JSON-serialisable evidence dictionary."""
    report: dict[str, object] = {}

    # G1: every named preset, four unrelated seeds.
    g1_failures = []
    g1_count = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_count += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "instances": g1_count,
        "failures": g1_failures,
    }
    truth_table_ok = True
    for bits in itertools.product((0, 1), repeat=3):
        forward, reverse = _expanded_clause_scores(bits)
        matches = forward == _FORWARD_SCORES and reverse == _REVERSE_SCORES
        truth_table_ok &= matches == (sum(bits) == 1)
    report["G1_planted_verifies"]["gadget_truth_table_cases"] = 8
    report["G1_planted_verifies"]["gadget_truth_table_pass"] = truth_table_ok
    report["G1_planted_verifies"]["pass"] &= truth_table_ok

    # G2: corruption classes exercise distinct validation paths.
    inst = make_instance(seed=2048, **DIFFICULTY["easy"])
    planted = list(inst["answer"])
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate": [planted[0], planted[0], *planted[2:]],
        "out_of_range": [0, *planted[1:]],
        "swap_within_block": [planted[1], planted[0], *planted[2:]],
    }
    g2 = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        g2[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    g2_pass = all(row["rejected"] for row in g2.values()) and len(set(reasons)) == len(reasons)
    report["G2_rejects_corruption"] = {"pass": g2_pass, "cases": g2}

    # G3: prose and a markdown fence around the exact wire format.
    body = ", ".join(map(str, inst["answer"]))
    realistic = f"I checked each clause.\n```text\n<answer>\n {body}\n</answer>\n```\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("garbage") is None,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_is_none": parse_answer("garbage") is None,
    }

    # G4: structure-aware sampling at the declared shipping level.
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    guess_inst = make_instance(seed=47001, **shipping)
    guess_rng = random.Random(8675309)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(guess_inst, guess_rng)
        if verify(guess_inst, candidate)[0]:
            hits += 1
    rate = hits / total
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "difficulty": SHIPPING_DIFFICULTY,
        "hits": hits,
        "total": total,
        "empirical_probability": rate,
        "candidate_prior": "uniform over A/B block choices satisfying sum(degree*x)=clauses",
        "structure_aware_space": search_space(guess_inst),
    }

    # G5: exact enumeration on a bounded small member of the same distribution.
    enum_inst = make_instance(n=18, seed=314159, clause_ratio=0.82)
    valid_count = enumerate_all(enum_inst)
    enum_space = search_space(enum_inst)
    fraction = valid_count / enum_space if valid_count is not None else None
    report["G5_sparse"] = {
        "pass": valid_count is not None and fraction is not None and fraction < 1e-3,
        "n": 18,
        "valid_answers": valid_count,
        "candidate_space": enum_space,
        "fraction": fraction,
        "work_cap": _ENUMERATION_CAP,
    }

    # G6: four plant-aware cheap attacks, across eight seeds.
    attack_rows = {
        "degree_two_hop_outlier": {"trials": 0, "candidates_produced": 0, "solved": 0, "best_remaining_violations": None},
        "greedy_exact_cover": {"trials": 0, "candidates_produced": 0, "solved": 0, "best_remaining_violations": None},
        "bounded_random_restart": {"trials": 0, "candidates_produced": 0, "solved": 0, "best_remaining_violations": None},
        "linear_free_variables_zero": {"trials": 0, "candidates_produced": 0, "solved": 0, "best_remaining_violations": None},
    }
    attack_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    for seed in range(80, 88):
        attack_inst = make_instance(seed=seed, **attack_params)
        candidates = {
            "degree_two_hop_outlier": _outlier_attack(attack_inst),
            "greedy_exact_cover": _greedy_attack(attack_inst),
            "bounded_random_restart": _random_restart_attack(attack_inst, random.Random(seed ^ 0xBAD5EED)),
            "linear_free_variables_zero": _linear_zero_free_attack(attack_inst),
        }
        for name, candidate in candidates.items():
            row = attack_rows[name]
            row["trials"] += 1
            if candidate is None:
                remaining = None
                ok = False
            else:
                row["candidates_produced"] += 1
                bits = _bits_from_well_formed_answer(candidate)
                remaining = _violations(attack_inst, bits) if bits is not None else len(attack_inst["clauses"])
                ok = verify(attack_inst, candidate)[0]
            if ok:
                row["solved"] += 1
            if remaining is not None:
                old = row["best_remaining_violations"]
                row["best_remaining_violations"] = remaining if old is None else min(old, remaining)
    panel_pass = all(row["trials"] >= 8 and row["solved"] == 0 for row in attack_rows.values())
    report["G6_adversary_panel"] = {"pass": panel_pass, "attacks": attack_rows}

    # G7: the same density remains satisfiable after doubling the shipped n.
    t0 = time.monotonic()
    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * shipping["n"]
    doubled = make_instance(seed=8888, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    elapsed = time.monotonic() - t0
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"],
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_permutation_size": doubled["permutation_size"],
        "doubled_clauses": len(doubled["clauses"]),
        "build_and_verify_seconds": round(elapsed, 6),
        "verify_reason": doubled_why,
    }

    # G8: structural transformations, carried witnesses, and unrelated seeds.
    invariant_checks = 0
    transformed_verify = 0
    invariant_failures = []
    distinct_keys = []
    key_params = DIFFICULTY["medium"]
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **key_params)
        base_key = canonical_key(base)
        distinct_keys.append(base_key)

        # Individually apply each symmetry and all four nonempty compositions.
        # This is the complete 2^3-1 panel for block labels, row order, and the
        # irrelevant ordering of the three members within every row.
        for mask in range(1, 8):
            transformed, carried = _transformed_copy(
                base,
                random.Random(20_000 + 8 * seed + mask),
                relabel_blocks=bool(mask & 1),
                reorder_clauses=bool(mask & 2),
                reorder_members=bool(mask & 4),
            )
            invariant_checks += 1
            if canonical_key(transformed) != base_key:
                invariant_failures.append({"seed": seed, "transform_mask": mask})
            if verify(transformed, carried)[0]:
                transformed_verify += 1

    distinct = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and transformed_verify == invariant_checks and distinct == 20,
        "invariance_checks": invariant_checks,
        "invariance_failures": invariant_failures,
        "transformed_witnesses_verified": transformed_verify,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "method": "stable color refinement plus colored incidence/co-occurrence profiles",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
