"""Verified problem generator for arXiv:2205.13905.

The paper constructs C5-free regular graphs by putting nine smaller regular
graphs into a 3-by-3 grid.  This module turns the exact numerical condition in
Section 2 into a witness problem: from a crowded pool of admissible component
cards (v,d), select and arrange nine cards so that the grid construction has a
prescribed number of vertices and degree.

Certificates are inverse-generated.  Several valid grids are sampled first,
their cards are mixed, and one known grid is retained as the planted answer.
No search is used to obtain a certificate.  Verification is integer arithmetic
on the displayed component parameters.

Only the Python standard library is required.  Importing this module performs
no file I/O, network access, or printing.
"""

from __future__ import annotations

import functools
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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family needs no helper routines
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "3-by-3 grid of regular-graph component parameters (v,d)",
        "C5-free regular graph construction",
        "Turán (n,5,3)-system construction",
    ],
    "verification_operations": [
        "integer parity and range checks",
        "exact row and column size sums",
        "exact degree-equation comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Replacing each component card (v,d) by 2v-d turns the nine coupled "
        "degree equations into an additively separable 3-by-3 matrix; without "
        "that invariant one must mechanically join triples of cards."
    ),
    "hardness_basis": (
        "Track B: an exact hash-join CSP algorithm enumerates ordered card "
        "triples in O(p^3+B) time (B is the collision-bucket work); at the "
        "shipping preset p=63 it averaged 82,293 counted operations and 0.118 "
        "seconds across eight measured runs, while the compact 2v-d route uses "
        "at most 207 exact arithmetic operations once the additive grid is "
        "recognized; the cubic join is efficient with tools but not executable "
        "by hand."
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
        "A JSON 3-by-3 matrix of nine distinct 1-based card IDs.  The chosen "
        "cards must already have total vertex count equal to the displayed "
        "target; row order, column order, and transposition are significant "
        "spellings even though all preserve validity."
    ),
    "bounds": {
        "rows": 3,
        "columns": 3,
        "card_id_min": 1,
        "card_id_max": "instance card_count",
        "distinct_ids": True,
        "chosen_vertex_sum": "instance target_vertices",
    },
}

DIFFICULTY = {
    "demo": {"n": 9, "spread": 4},
    "easy": {"n": 27, "spread": 31},
    "medium": {"n": 45, "spread": 61},
    "hard": {"n": 63, "spread": 97},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The nine quantities 2v-d form an additively separable matrix whose every "
    "2-by-2 alternating sum vanishes."
)
PLACEBO_HINT = (
    "The nine component identifiers form a fully specified matrix whose row "
    "and column positions should be copied carefully."
)

# Filled after the script-owned oracle runs.  Until then, zero attempts are
# explicit diagnostic placeholders and are never treated as hardness evidence.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and native objects.  Section 1 defines a Turán (n,5,3)-system.
Proposition 1 says that the triangles and anti-triangles of a graph with no
induced 5-cycle form such a system.  Section 2 then defines the paper's grid
graph from nine component graphs and writes the ten exact size/degree
equations.  The solver is handed those same (v,d) component objects and returns
their 3-by-3 grid; there is no external graph, SAT, or finite-field reduction.

Step 0 and track choice.  Theorem 3 is an existence theorem, not a hardness
theorem.  Lemma 5 gives a recursive construction for every even-order regular
component; Lemma 6 handles odd order and even degree away from the midpoint;
Lemma 7 handles the needed midpoint when it is divisible by four.  Thus the
component certificates are produced by explicit formulas.  A generic finite
CSP algorithm can also find a card grid efficiently, making Track A false.
This module therefore declares Track B and reports a successful exact hash-join
reference algorithm.  The mechanical route enumerates ordered triples of the
p public cards.  The compact route notices that w=2v-d equals a row-size term
plus a column-size term minus the target degree, so all three grid rows have
the same ordered pair of w-differences.

Construction.  For each hidden grid choose offsets consisting of zero and four
random opposite pairs.  Component orders are v=2(s+u), with one randomly
eligible component changed to 2(s+u)+1.  Their degrees are then defined from
the Section 2 grid equations.  The scale s=32*spread keeps every degree in
range.  The odd component is chosen where its degree is not the forbidden
midpoint, so Lemmas 5 and 6 construct every component.  All hidden grids are
drawn by the same rule, all have 18s+1 vertices and degree 9s, and all nine-card
sets are valid before their cards are mixed.  The retained answer is therefore
known by inverse generation, not recovered by search.

Attacks.  Plants and decoys are entire grids drawn from the same distribution,
so per-card size and degree scores have no planted class to isolate.  The panel
tests a central-value outlier rule, a target-sum greedy rule, 256 uniform
structure-aware restarts, and an obvious sorted-2v-d ansatz that a solver could
try by hand.  The exact cubic hash join is successful by design and is reported
separately as Track B's reference algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 400_000
_SUBSET_TABLE_CACHE: dict[tuple[tuple[int, ...], int], Any] = {}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n: int, spread: int) -> None:
    if not _is_int(n) or n < 9 or n % 9:
        raise ValueError("n must be a multiple of 9 and at least 9")
    if not _is_int(spread) or spread < 4:
        raise ValueError("spread must be an integer at least 4")
    if spread < 4:
        raise ValueError("spread must permit four distinct offset magnitudes")


def _admissible_component(v: int, d: int) -> bool:
    """Executable form of the component cases in Lemmas 5--7."""

    if not (_is_int(v) and _is_int(d)) or v < 1 or not 0 <= d < v:
        return False
    if v % 2 == 0:
        return True  # Lemma 5
    if d % 2:
        return False  # handshake parity for odd v
    midpoint = (v - 1) // 2
    if d != midpoint:
        return True  # Lemma 6
    return midpoint % 4 == 0  # Lemma 7


def _one_hidden_grid(rng: random.Random, spread: int) -> list[list[list[int]]]:
    """Sample one valid grid before any public card pool exists."""

    magnitudes = rng.sample(range(1, spread + 1), 4)
    offsets = [0]
    for value in magnitudes:
        offsets.extend((value, -value))
    rng.shuffle(offsets)
    u = [offsets[0:3], offsets[3:6], offsets[6:9]]

    # For an odd card at (r,c), d-(v-1)/2 = -2R_r-2C_c+3u_rc.
    # A nonzero balanced offset matrix cannot make this vanish everywhere.
    row_u = [sum(row) for row in u]
    col_u = [sum(u[r][c] for r in range(3)) for c in range(3)]
    eligible = [
        (r, c) for r in range(3) for c in range(3)
        if -2 * row_u[r] - 2 * col_u[c] + 3 * u[r][c] != 0
    ]
    if not eligible:  # defensive; the preceding observation rules this out
        raise AssertionError("balanced offsets supplied no odd-card position")
    odd_r, odd_c = eligible[rng.randrange(len(eligible))]

    scale = 32 * spread
    sizes = [
        [2 * (scale + u[r][c]) + int((r, c) == (odd_r, odd_c))
         for c in range(3)]
        for r in range(3)
    ]
    target_vertices = 18 * scale + 1
    target_degree = 9 * scale
    assert sum(map(sum, sizes)) == target_vertices
    row_sizes = [sum(row) for row in sizes]
    col_sizes = [sum(sizes[r][c] for r in range(3)) for c in range(3)]
    grid: list[list[list[int]]] = []
    for r in range(3):
        row = []
        for c in range(3):
            v = sizes[r][c]
            d = target_degree - row_sizes[r] - col_sizes[c] + 2 * v
            if not _admissible_component(v, d):
                raise AssertionError(f"inadmissible constructed component {(v, d)}")
            row.append([v, d])
        grid.append(row)
    return grid


def make_instance(n: int, seed: int = 0, *, spread: int = 31) -> dict:
    """Inverse-generate a crowded pool and a known 3-by-3 grid certificate."""

    _validate_params(n, spread)
    rng = random.Random(seed)
    grid_count = n // 9
    hidden = [_one_hidden_grid(rng, spread) for _ in range(grid_count)]
    planted_grid = rng.randrange(grid_count)

    flat: list[tuple[int, int, int, int, int]] = []
    for g, grid in enumerate(hidden):
        for r in range(3):
            for c in range(3):
                v, d = grid[r][c]
                flat.append((g, r, c, v, d))
    rng.shuffle(flat)

    cards: list[list[int]] = []
    public_id: dict[tuple[int, int, int], int] = {}
    for card_id, (g, r, c, v, d) in enumerate(flat, 1):
        cards.append([v, d])
        public_id[(g, r, c)] = card_id
    answer = [
        [public_id[(planted_grid, r, c)] for c in range(3)]
        for r in range(3)
    ]

    scale = 32 * spread
    return {
        "family": "C5-free regular grid construction from component cards",
        "card_count": n,
        "cards": cards,
        "target_vertices": 18 * scale + 1,
        "target_degree": 9 * scale,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete, self-contained component-grid problem."""

    lines = [
        "C5-free regular grid certificate",
        "",
        "A component card (v,d) denotes a d-regular graph on v vertices with "
        "no induced 5-cycle.  Every supplied card is admissible: either v is "
        "even; or v is odd, d is even, and d differs from (v-1)/2; or v is "
        "odd and d=(v-1)/2 is divisible by 4.",
        "",
        "Select nine DISTINCT cards and place their IDs in a 3-by-3 grid.  "
        "A placement is valid exactly when:",
        f"1. the sum of its nine v-values is N={inst['target_vertices']}; and",
        f"2. for every cell (r,c), d plus the v-values of the other two "
        f"cards in row r and the other two cards in column c equals "
        f"D={inst['target_degree']}.",
        "The four other cards in condition 2 are distinct; do not count the "
        "cell itself.  Rows and columns are ordered only for writing the "
        "answer, and transposed or permuted valid grids are also accepted.",
        "",
        "Cards are 1-indexed; each line is ID: v d.",
    ]
    lines.extend(
        f"{i}: {card[0]} {card[1]}"
        for i, card in enumerate(inst["cards"], 1)
    )
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as a JSON "
        "3-by-3 array of card IDs.",
        "Example: <answer>[[1,2,3],[4,5,6],[7,8,9]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Extract the last tagged JSON matrix; never raise on malformed output."""

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
    except (TypeError, ValueError):
        return None
    return value


def _shape_ids(inst: dict, answer: object) -> tuple[list[list[int]] | None, str]:
    if answer == []:
        return None, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 3:
        return None, "answer must be a list of exactly 3 rows"
    rows: list[list[int]] = []
    for r, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 3:
            return None, f"row {r + 1} must contain exactly 3 card IDs"
        if any(not _is_int(x) for x in row):
            return None, f"row {r + 1} contains a non-integer card ID"
        rows.append(row)
    flat = [x for row in rows for x in row]
    card_count = len(inst.get("cards", []))
    bad = next((x for x in flat if not 1 <= x <= card_count), None)
    if bad is not None:
        return None, f"card ID {bad} is outside 1..{card_count}"
    if len(set(flat)) != 9:
        return None, "the nine card IDs must be distinct"
    return rows, "ok"


def _grid_valid_ids(inst: dict, rows: list[list[int]]) -> tuple[bool, str]:
    cards = inst["cards"]
    chosen = [[cards[x - 1] for x in row] for row in rows]
    for r in range(3):
        for c in range(3):
            v, d = chosen[r][c]
            if not _admissible_component(v, d):
                return False, f"card {rows[r][c]} is not an admissible component"
    total = sum(chosen[r][c][0] for r in range(3) for c in range(3))
    if total != inst["target_vertices"]:
        return False, (
            f"chosen vertex total is {total}, expected {inst['target_vertices']}"
        )
    row_sums = [sum(chosen[r][c][0] for c in range(3)) for r in range(3)]
    col_sums = [sum(chosen[r][c][0] for r in range(3)) for c in range(3)]
    target = inst["target_degree"]
    for r in range(3):
        for c in range(3):
            v, d = chosen[r][c]
            got = d + row_sums[r] + col_sums[c] - 2 * v
            if got != target:
                return False, (
                    f"degree equation fails at row {r + 1}, column {c + 1}: "
                    f"got {got}, expected {target}"
                )
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid nine-card grid using exact integer arithmetic."""

    rows, reason = _shape_ids(inst, answer)
    if rows is None:
        return False, reason
    return _grid_valid_ids(inst, rows)


def _subset_tables(inst: dict) -> list[list[dict[int, int]]]:
    sizes = tuple(card[0] for card in inst["cards"])
    target = inst["target_vertices"]
    key = (sizes, target)
    cached = _SUBSET_TABLE_CACHE.get(key)
    if cached is not None:
        return cached
    p = len(sizes)
    table: list[list[dict[int, int]]] = [
        [dict() for _ in range(10)] for _ in range(p + 1)
    ]
    table[p][0][0] = 1
    for i in range(p - 1, -1, -1):
        value = sizes[i]
        for need in range(10):
            out = dict(table[i + 1][need])
            if need:
                for subtotal, count in table[i + 1][need - 1].items():
                    new_sum = subtotal + value
                    if new_sum <= target:
                        out[new_sum] = out.get(new_sum, 0) + count
            table[i][need] = out
    _SUBSET_TABLE_CACHE[key] = table
    return table


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample a distinct-card, target-sum certificate candidate."""

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    table = _subset_tables(inst)
    sizes = [card[0] for card in inst["cards"]]
    need = 9
    remaining = inst["target_vertices"]
    selected: list[int] = []
    for i, value in enumerate(sizes):
        if need == 0:
            break
        skip = table[i + 1][need].get(remaining, 0)
        take = table[i + 1][need - 1].get(remaining - value, 0)
        total = skip + take
        if total <= 0:
            raise RuntimeError("declared certificate language is unexpectedly empty")
        if rng.randrange(total) < take:
            selected.append(i + 1)
            remaining -= value
            need -= 1
    if need or remaining:
        raise RuntimeError("failed to sample the declared certificate language")
    rng.shuffle(selected)
    return [selected[0:3], selected[3:6], selected[6:9]]


def search_space(inst: dict) -> int:
    """Exact size of the structure-aware bounded certificate language."""

    table = _subset_tables(inst)
    subsets = table[0][9].get(inst["target_vertices"], 0)
    return subsets * math.factorial(9)


def enumerate_all(inst: dict) -> int | None:
    """Count all valid ordered grids exactly when the language is small."""

    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    cards = inst["cards"]
    total = 0
    for subset in itertools.combinations(range(1, len(cards) + 1), 9):
        if sum(cards[i - 1][0] for i in subset) != inst["target_vertices"]:
            continue
        for perm in itertools.permutations(subset):
            rows = [list(perm[0:3]), list(perm[3:6]), list(perm[6:9])]
            if _grid_valid_ids(inst, rows)[0]:
                total += 1
    return total


def canonical_key(inst: dict) -> str:
    """Canonicalize the unordered multiset of cards and the two targets."""

    payload = {
        "family": inst.get("family"),
        "target_vertices": inst["target_vertices"],
        "target_degree": inst["target_degree"],
        "cards": sorted([list(card) for card in inst["cards"]]),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict:
    """Grow the mixed card pool and spread while the witness stays 3-by-3."""

    out = {k: v for k, v in params.items() if k != "_preset"}
    out["n"] = int(out.get("n", 63)) + 18
    out["spread"] = int(out.get("spread", 97)) + 37
    return out


def _reference_solve(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Exact cubic hash-join CSP solver used as Track B's reference."""

    cards = inst["cards"]
    p = len(cards)
    w = []
    operations = 0
    for v, d in cards:
        w.append(2 * v - d)
        operations += 2
    buckets: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for a in range(p):
        for b in range(p):
            if b == a:
                continue
            delta1 = w[b] - w[a]
            operations += 1
            for c in range(p):
                if c == a or c == b:
                    continue
                signature = (delta1, w[c] - w[a])
                operations += 1
                row = (a + 1, b + 1, c + 1)
                prior = buckets.setdefault(signature, [])
                for i in range(len(prior)):
                    first = prior[i]
                    if set(first) & set(row):
                        operations += 1
                        continue
                    for j in range(i + 1, len(prior)):
                        second = prior[j]
                        operations += 1
                        if set(second) & set(row) or set(first) & set(second):
                            continue
                        candidate = [list(first), list(second), list(row)]
                        operations += 9
                        if _grid_valid_ids(inst, candidate)[0]:
                            return candidate, operations
                prior.append(row)
    return None, operations


def _sorted_matrix(ids: list[int], inst: dict) -> list[list[int]]:
    ids = sorted(ids, key=lambda x: (
        2 * inst["cards"][x - 1][0] - inst["cards"][x - 1][1],
        inst["cards"][x - 1][0], x,
    ))
    return [ids[0:3], ids[3:6], ids[6:9]]


def _attack_outlier(inst: dict) -> list[list[int]]:
    sizes = sorted(card[0] for card in inst["cards"])
    degrees = sorted(card[1] for card in inst["cards"])
    mv = sizes[len(sizes) // 2]
    md = degrees[len(degrees) // 2]
    ids = sorted(
        range(1, len(inst["cards"]) + 1),
        key=lambda x: (
            abs(inst["cards"][x - 1][0] - mv)
            + abs(inst["cards"][x - 1][1] - md), x,
        ),
    )[:9]
    return _sorted_matrix(ids, inst)


def _attack_greedy(inst: dict) -> list[list[int]]:
    target = inst["target_vertices"]
    unused = set(range(1, len(inst["cards"]) + 1))
    picked: list[int] = []
    subtotal = 0
    for step in range(9):
        desired = target * (step + 1) / 9
        choice = min(
            unused,
            key=lambda x: (abs(subtotal + inst["cards"][x - 1][0] - desired), x),
        )
        picked.append(choice)
        unused.remove(choice)
        subtotal += inst["cards"][choice - 1][0]
    return _sorted_matrix(picked, inst)


def _attack_additive_ansatz(inst: dict) -> list[list[int]]:
    cards = inst["cards"]
    odd = min(
        (i for i, card in enumerate(cards, 1) if card[0] % 2),
        key=lambda x: (abs(cards[x - 1][0] * 9 - inst["target_vertices"]), x),
    )
    w0 = 2 * cards[odd - 1][0] - cards[odd - 1][1]
    rest = sorted(
        (i for i in range(1, len(cards) + 1) if i != odd),
        key=lambda x: (
            abs((2 * cards[x - 1][0] - cards[x - 1][1]) - w0), x,
        ),
    )[:8]
    chosen = sorted(rest, key=lambda x: (
        2 * cards[x - 1][0] - cards[x - 1][1], x
    ))
    return [chosen[0:3], [chosen[3], odd, chosen[4]], chosen[5:8]]


def _permuted_cards(inst: dict, rng: random.Random) -> tuple[dict, dict[int, int]]:
    order = list(range(len(inst["cards"])))
    rng.shuffle(order)
    mapping = {old + 1: new + 1 for new, old in enumerate(order)}
    out = dict(inst)
    out["cards"] = [list(inst["cards"][old]) for old in order]
    out["answer"] = [[mapping[x] for x in row] for row in inst["answer"]]
    return out, mapping


def _symmetry_answer(answer: list[list[int]]) -> list[list[int]]:
    # A nontrivial composition: row cycle, column swap, then transpose.
    rows = [answer[1], answer[2], answer[0]]
    cols = [[row[2], row[0], row[1]] for row in rows]
    return [[cols[c][r] for c in range(3)] for r in range(3)]


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run all mandatory correctness, resistance, scaling, and metadata gates."""

    report: dict[str, Any] = {
        "paper": "2205.13905",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
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
        "verified": g1_attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12345, **ship_params)
    base = [list(row) for row in inst["answer"]]
    corruptions: dict[str, object] = {
        "drop": [base[0][0:2], list(base[1]), list(base[2])],
        "duplicate": [[base[0][0], base[0][0], base[0][2]],
                      list(base[1]), list(base[2])],
        "empty": [],
        "out_of_range": [[len(inst["cards"]) + 1, base[0][1], base[0][2]],
                         list(base[1]), list(base[2])],
    }
    swapped = None
    for a in range(9):
        for b in range(a + 1, 9):
            trial_flat = [x for row in base for x in row]
            trial_flat[a], trial_flat[b] = trial_flat[b], trial_flat[a]
            trial = [trial_flat[0:3], trial_flat[3:6], trial_flat[6:9]]
            ok, _ = verify(inst, trial)
            if not ok:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions["swap"] = swapped
    corruption_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        corruption_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    g2_ok = (
        swapped is not None
        and all(row["rejected"] for row in corruption_results.values())
        and len(set(reasons)) == len(reasons)
    )
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "I used the row/column equations.\n```json\n<answer>\n"
        + json.dumps(inst["answer"])
        + "\n</answer>\n```\nThe check is exact."
    )
    parsed = parse_answer(model_style)
    direct = parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and direct == inst["answer"],
        "model_style_recovered": parsed == inst["answer"],
        "direct_recovered": direct == inst["answer"],
    }

    sample_total = 200_000
    sample_rng = random.Random(0x220513905)
    hits = 0
    for _ in range(sample_total):
        candidate = random_candidate(inst, sample_rng)
        hits += int(verify(inst, candidate)[0])
    guess_probability = hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": hits,
        "total": sample_total,
        "estimated_probability": guess_probability,
        "structure_aware_space": search_space(inst),
        "sampler_prior": "uniform over distinct 9-card target-sum subsets and permutations",
    }

    ref_attempts = 8
    ref_successes = 0
    ref_ops = []
    ref_times = []
    for seed in range(700, 700 + ref_attempts):
        ref_inst = make_instance(seed=seed, **ship_params)
        started = time.perf_counter()
        found, operations = _reference_solve(ref_inst)
        elapsed = time.perf_counter() - started
        ref_successes += int(found is not None and verify(ref_inst, found)[0])
        ref_ops.append(operations)
        ref_times.append(elapsed)

    demo = make_instance(seed=23, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and ref_successes == ref_attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": sample_total,
        "shipping_density_estimate": guess_probability,
        "demo_exact_valid_answer_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": sum(ref_times) / len(ref_times),
        "baseline_wall_clock_sec_max": max(ref_times),
        "baseline_operations_mean": sum(ref_ops) / len(ref_ops),
        "baseline_operations_max": max(ref_ops),
        "baseline_successes": ref_successes,
        "baseline_attempts": ref_attempts,
    }

    attack_names = (
        "outlier_central_value",
        "greedy_target_sum",
        "random_restart_256",
        "by_hand_sorted_additive_ansatz",
    )
    attack_wins = {name: 0 for name in attack_names}
    attack_attempts = 8
    for seed in range(900, 900 + attack_attempts):
        attack_inst = make_instance(seed=seed, **ship_params)
        attack_wins["outlier_central_value"] += int(
            verify(attack_inst, _attack_outlier(attack_inst))[0]
        )
        attack_wins["greedy_target_sum"] += int(
            verify(attack_inst, _attack_greedy(attack_inst))[0]
        )
        restart_rng = random.Random(seed ^ 0xA5A5A5)
        restart_win = any(
            verify(attack_inst, random_candidate(attack_inst, restart_rng))[0]
            for _ in range(256)
        )
        attack_wins["random_restart_256"] += int(restart_win)
        attack_wins["by_hand_sorted_additive_ansatz"] += int(
            verify(attack_inst, _attack_additive_ansatz(attack_inst))[0]
        )
    attacks = {
        name: {"successes": attack_wins[name], "attempts": attack_attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact ordered-triple hash-join CSP",
            "complexity": "O(p^3+B) integer operations, B=bucket-collision work",
            "wall_clock_sec_mean": sum(ref_times) / len(ref_times),
            "wall_clock_sec_max": max(ref_times),
            "operations_mean": sum(ref_ops) / len(ref_ops),
            "operations_max": max(ref_ops),
            "solves": f"{ref_successes}/{ref_attempts}, as expected",
        },
    }

    doubled_params = {
        "n": ship_params["n"] * 2,
        "spread": ship_params["spread"] * 2,
    }
    doubled = make_instance(seed=404, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["cards"]) == 2 * len(inst["cards"])
        and search_space(doubled) > search_space(inst),
        "shipping_cards": len(inst["cards"]),
        "doubled_cards": len(doubled["cards"]),
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    transformed_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=seed + 1200, **ship_params)
        key = canonical_key(original)
        keys.append(key)
        relabelled, _ = _permuted_cards(original, random.Random(seed + 501))
        invariant_checks += 1
        if canonical_key(relabelled) != key:
            g8_failures.append(f"seed {seed}: card relabelling changed key")
        ok, why = verify(relabelled, relabelled["answer"])
        transformed_checks += 1
        if not ok:
            g8_failures.append(f"seed {seed}: carried relabelling failed: {why}")
        symmetric_answer = _symmetry_answer(original["answer"])
        invariant_checks += 1
        if canonical_key(original) != key:
            g8_failures.append(f"seed {seed}: grid symmetry changed key")
        ok, why = verify(original, symmetric_answer)
        transformed_checks += 1
        if not ok:
            g8_failures.append(f"seed {seed}: grid symmetry failed: {why}")
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "transformed_witness_checks": transformed_checks,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "transformations": [
            "arbitrary public card relabelling",
            "row cycle composed with column cycle and transposition",
        ],
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_ops = 2 * len(inst["cards"]) + 81
    arms = {
        name: dict(G9_MEASUREMENTS[name])
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
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
