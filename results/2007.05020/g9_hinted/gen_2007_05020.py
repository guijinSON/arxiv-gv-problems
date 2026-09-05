"""Verified Dota Underlords pair-alliance team instances (arXiv:2007.05020).

The paper's Theorem 1 identifies the equal-power, size-two-alliance special
case with fixed-size densest subgraph.  This module inverse-generates a hidden
complete transversal in regular pool-to-pool alliance graphs.  The returned
certificate is the corresponding team of heroes; generation never solves the
instance it creates.

The module is deterministic in ``(n, seed, params)``, uses only the Python
standard library, performs no file I/O, and prints nothing when imported.
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


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "equal-power heroes partitioned into display pools",
        "size-two alliances with threshold-two bonuses",
        "team-size and exact power threshold",
    ],
    "verification_operations": [
        "integer team-size and hero-range checks",
        "pair-alliance membership lookups",
        "exact integer team-power comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Use intersections of compatibility neighborhoods across hero pools; "
        "without that structure a solver faces one choice from each of many "
        "regular, statistically indistinguishable pools."
    ),
    "hardness_basis": (
        "Track A: Theorem 1 proves hardness for equal-power heroes with "
        "size-two, threshold-two, equal-bonus alliances; shipping uses the "
        "planted regular multipartite regime stated by the selected preset, "
        "where no efficient exact recovery method is known and the measured "
        "centered-spectral and 300,000-node CSP baselines are reported by G5/G6."
    ),
    "max_answer_tokens": 96,
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
    "easy": {"n": 24, "pool_size": 40, "degree": 29, "mix_rounds": 3},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The useful signal is in intersections of compatibility neighborhoods "
    "across several pools, not in any single hero's degree."
)
PLACEBO_HINT = (
    "The useful information is encoded in hexadecimal rows across several "
    "pools, so careful attention to indexing matters."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON array of exactly n distinct global hero IDs, with "
        "position c naming one hero from pool c; n <= 64 and each pool has "
        "at most 128 heroes."
    ),
    "bounds": {
        "max_team_size": 64,
        "max_pool_size": 128,
        "global_id_max_exclusive": 8192,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 3.2 defines a hero's base power, alliance
membership a_ij, threshold-indexed bonus e_ijk, and a team of at most m heroes.
Theorem 1 in Section 4.1 gives the exact special case used here: all hero powers
are equal, every alliance contains exactly two heroes, its only nonzero bonus
is unlocked when both are selected, bonuses affect only alliance members, and
all bonuses are equal.  The active alliances are therefore graph edges and a
size-k team's power is an affine function of its induced edge count.  Theorem 2
in Section 4.2 says the witness is the team itself and checks it by recomputing
active alliances in polynomial time.  Theorem 3 concludes NP-completeness.

What makes it easy.  Section 3.1 explicitly says the no-alliance model is solved
by sorting hero powers.  We avoid it by giving every hero many pair alliances
and making all base powers identical.  Section 4.4 supplies a polynomial
reduction to maximum edge-weighted clique, not a polynomial solver; it points
to branch-and-bound and quadratic formulations for individual instances.
Generation does not invoke any such method.  It samples the answer first, then
constructs every pair-alliance matrix around it.

Inverse generation and distribution.  There are n display pools of q heroes.
For each pair of pools an independent d-regular bipartite graph is made from a
randomly relabelled circulant graph and degree-preserving 2-switches.  A
uniformly random ordinary edge is chosen and its endpoint labels are exchanged
with the two planted labels.  Consequently every hero has exactly d alliances
into every other pool and a planted pair is an ordinary edge under relabelling,
not an inserted edge.  The planted labels form a complete transversal team.
With r <= n selected heroes and a active pair alliances, power is r + 2a <=
r^2 <= n^2; equality forces r=n and every pair active.  Because no alliances
exist within a pool, equality also forces one hero from every pool.

Hardness claim and attacks.  Theorem 1 is a worst-case result, not a proof that
this planted regular distribution is average-case hard.  Track A therefore
states the distribution and relies on measured evidence: a triangle-profile
outlier probe, greedy propagation, randomized restarts, centered spectral power
iteration, and bounded exact CSP backtracking.  Regularity makes all one-hero
degrees identical; random relabellings remove index leakage; 2-switches erase
the initial circulant layers.  The exact solver is deliberately bounded and
its exhausted node count is reported, not misrepresented as a proof.

Canonicalization.  canonical_key excludes the seed, answer, raw input order,
and raw labels.  It hashes transpose-invariant common-neighbor profiles for
each regular bipartite pair matrix and associates them through sorted incident
profiles for each pool.  This is a strong cheap isomorphism invariant, not a
complete multipartite-graph canonizer; that limitation is recorded in README.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_DPLL_NODE_BUDGET = 300_000

# Filled after the script-owned bare, structural, and placebo hardening runs.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _require_int(name: str, value: object, low: int, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise ValueError(f"{name} must be an integer at least {low}")
    if high is not None and value > high:
        raise ValueError(f"{name} must be at most {high}")
    return value


def _random_bit(mask: int, rng: random.Random) -> int:
    """Return a uniformly random set-bit index from nonzero ``mask``."""
    rank = rng.randrange(mask.bit_count())
    while rank:
        mask &= mask - 1
        rank -= 1
    return (mask & -mask).bit_length() - 1


def _swap_bit_labels(mask: int, a: int, b: int) -> int:
    if a == b:
        return mask
    abit = (mask >> a) & 1
    bbit = (mask >> b) & 1
    if abit != bbit:
        mask ^= (1 << a) | (1 << b)
    return mask


def _regular_matrix(q: int, degree: int, planted_left: int,
                    planted_right: int, mix_rounds: int,
                    rng: random.Random) -> list[int]:
    """Make a d-regular bipartite graph and relabel an ordinary edge to plant.

    The starting random circulant is simple and d-regular.  Valid 2-switches
    preserve both side degrees.  Since the selected source edge is uniform over
    the regular graph, the edge carried onto the planted labels has no special
    per-matrix source distribution.
    """
    left_order = list(range(q))
    right_order = list(range(q))
    rng.shuffle(left_order)
    rng.shuffle(right_order)
    rows = [0] * q
    for pos, left in enumerate(left_order):
        for shift in range(degree):
            rows[left] |= 1 << right_order[(pos + shift) % q]

    for _ in range(mix_rounds * q * degree):
        x1 = rng.randrange(q)
        x2 = rng.randrange(q - 1)
        if x2 >= x1:
            x2 += 1
        y1 = _random_bit(rows[x1], rng)
        y2 = _random_bit(rows[x2], rng)
        if y1 == y2:
            continue
        if ((rows[x1] >> y2) & 1) or ((rows[x2] >> y1) & 1):
            continue
        rows[x1] ^= (1 << y1) | (1 << y2)
        rows[x2] ^= (1 << y2) | (1 << y1)

    old_left = rng.randrange(q)
    old_right = _random_bit(rows[old_left], rng)
    rows[old_left], rows[planted_left] = rows[planted_left], rows[old_left]
    rows = [_swap_bit_labels(mask, old_right, planted_right) for mask in rows]

    if not ((rows[planted_left] >> planted_right) & 1):
        raise AssertionError("planting failed")
    if any(mask.bit_count() != degree for mask in rows):
        raise AssertionError("row regularity failed")
    for y in range(q):
        if sum((mask >> y) & 1 for mask in rows) != degree:
            raise AssertionError("column regularity failed")
    return rows


def _pair_indices(n: int):
    return itertools.combinations(range(n), 2)


def _columns(rows: list[int], q: int) -> list[int]:
    cols = [0] * q
    for x, mask in enumerate(rows):
        scan = mask
        while scan:
            bit = scan & -scan
            y = bit.bit_length() - 1
            cols[y] |= 1 << x
            scan -= bit
    return cols


def _ordered_pairs(inst: dict) -> list[dict]:
    pairs = inst["pair_alliances"]
    if [(p["i"], p["j"]) for p in pairs] == sorted(
            (p["i"], p["j"]) for p in pairs):
        return pairs
    return sorted(pairs, key=lambda p: (p["i"], p["j"]))


def _adjacency(inst: dict) -> list[list[list[int] | None]]:
    n = inst["n"]
    q = inst["pool_size"]
    adj: list[list[list[int] | None]] = [[None] * n for _ in range(n)]
    for record in inst["pair_alliances"]:
        i, j = record["i"], record["j"]
        rows = list(record["rows"])
        adj[i][j] = rows
        adj[j][i] = _columns(rows, q)
    return adj


def _labels_from_answer(inst: dict, answer: list[int]) -> list[int]:
    q = inst["pool_size"]
    return [hero - c * q for c, hero in enumerate(answer)]


def _answer_from_labels(inst: dict, labels: list[int]) -> list[int]:
    q = inst["pool_size"]
    return [c * q + labels[c] for c in range(inst["n"])]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a team first, then build regular pair alliances around it."""
    n = _require_int("n", n, 4, 64)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    q = _require_int("pool_size", params.pop("pool_size", 24), 4, 128)
    degree = _require_int(
        "degree", params.pop("degree", max(2, round(0.72 * q))), 2
    )
    mix_rounds = _require_int(
        "mix_rounds", params.pop("mix_rounds", 8), 0, 40
    )
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if degree >= q:
        raise ValueError("degree must be smaller than pool_size")

    rng = random.Random(seed)
    planted_labels = [rng.randrange(q) for _ in range(n)]
    pairs = []
    for i, j in _pair_indices(n):
        rows = _regular_matrix(
            q, degree, planted_labels[i], planted_labels[j], mix_rounds, rng
        )
        pairs.append({"i": i, "j": j, "rows": rows})

    inst = {
        "n": n,
        "pool_size": q,
        "degree": degree,
        "mix_rounds": mix_rounds,
        "hero_count": n * q,
        "team_limit": n,
        "base_power": 1,
        "pair_bonus_per_hero": 1,
        "target_power": n * n,
        "pair_alliances": pairs,
    }
    inst["answer"] = _answer_from_labels(inst, planted_labels)
    return inst


def render(inst: dict) -> str:
    """Render a complete, self-contained exact team-selection problem."""
    n = inst["n"]
    q = inst["pool_size"]
    degree = inst["degree"]
    width = max(1, (q + 3) // 4)
    lines = [
        "DOTA UNDERLORDS PAIR-ALLIANCE TEAM",
        "",
        "There are N*Q distinct heroes, displayed in N pools only to make",
        "their IDs and alliance data readable. Pool c contains local heroes",
        "x=0,...,Q-1; that hero's global ID is c*Q+x. IDs and pools are",
        "0-indexed. Every hero has base power 1.",
        "",
        "Every listed compatibility is a size-two alliance. If both heroes",
        "of such an alliance are selected, each of them receives bonus power",
        "1, so that active alliance contributes 2 total. No unlisted pair is",
        "an alliance, and there are no alliances within a pool.",
        "",
        f"N = {n}",
        f"Q = {q}",
        f"Each pool pair is D-regular with D = {degree}",
        f"Team size limit = {n}",
        f"Required total power = at least {inst['target_power']}",
        "",
        "For a team with r heroes and a active listed alliances, total power",
        "is r+2a. Since r<=N, reaching N^2 is possible exactly when r=N and",
        "all N choose 2 hero pairs are alliances. Such a team necessarily has",
        "one hero from every pool. You may therefore return that canonical",
        "one-per-pool representation directly.",
        "",
        "PAIR DATA: for each 0<=i<j<N, ROWS has Q hexadecimal integers.",
        "The x-th integer is a Q-bit mask: bit y (least-significant bit y=0)",
        "is 1 exactly when local hero x in pool i has a size-two alliance",
        "with local hero y in pool j. Leading zeroes do not change a mask.",
        "",
        "PAIR_DATA_BEGIN",
    ]
    for record in _ordered_pairs(inst):
        row_text = ",".join(f"{mask:0{width}x}" for mask in record["rows"])
        lines.append(
            f"PAIR {record['i']} {record['j']} ROWS {row_text}"
        )
    lines.extend([
        "PAIR_DATA_END",
        "",
        "Return an ordered JSON array of exactly N distinct global hero IDs.",
        "Position c must contain the chosen hero from pool c, hence it must lie",
        "in the inclusive range c*Q through (c+1)*Q-1. Repeats are forbidden.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON",
        "array of integer global hero IDs in pool order.",
        "Example syntax (not a solution): <answer>[2, 27, 51]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Extract the JSON answer array from tolerant tagged model output."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any correctly formatted qualifying team without reading the plant."""
    n = inst["n"]
    q = inst["pool_size"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong team length: expected {n}, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every hero ID must be an integer"
    if len(set(answer)) != len(answer):
        return False, "hero IDs must be distinct"
    if any(x < 0 or x >= inst["hero_count"] for x in answer):
        return False, f"hero ID outside 0..{inst['hero_count'] - 1}"
    for c, hero in enumerate(answer):
        if not (c * q <= hero < (c + 1) * q):
            return False, f"position {c} does not name a hero from pool {c}"

    labels = _labels_from_answer(inst, answer)
    active = 0
    for record in inst["pair_alliances"]:
        i, j = record["i"], record["j"]
        if not ((record["rows"][labels[i]] >> labels[j]) & 1):
            return False, f"missing size-two alliance between pools {i} and {j}"
        active += 1
    power = n * inst["base_power"] + 2 * active * inst["pair_bonus_per_hero"]
    if power < inst["target_power"]:
        return False, f"team power {power} is below {inst['target_power']}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the one-hero-per-pool certificate language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    q = inst["pool_size"]
    return [c * q + rng.randrange(q) for c in range(inst["n"])]


def search_space(inst: dict) -> int | None:
    """Return the exact size q^n of the structure-aware candidate language."""
    return pow(inst["pool_size"], inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count qualifying teams exactly when q^n is below a strict work cap."""
    n = inst["n"]
    q = inst["pool_size"]
    if pow(q, n) > _ENUMERATION_CAP:
        return None
    adj = _adjacency(inst)
    total = 0
    for labels in itertools.product(range(q), repeat=n):
        valid = True
        for i, j in _pair_indices(n):
            rows = adj[i][j]
            if rows is None or not ((rows[labels[i]] >> labels[j]) & 1):
                valid = False
                break
        if valid:
            total += 1
    return total


def _bipartite_signature(rows: list[int], q: int) -> tuple:
    """Common-neighbor invariant under either-side relabeling and transpose."""
    cols = _columns(rows, q)

    def side_signature(side: list[int]) -> tuple:
        profiles = []
        for i, mask in enumerate(side):
            common = sorted(
                (mask & side[j]).bit_count() for j in range(q) if j != i
            )
            profiles.append(tuple(common))
        return tuple(sorted(profiles))

    return tuple(sorted((side_signature(rows), side_signature(cols))))


def canonical_key(inst: dict) -> str:
    """Return a strong cheap invariant for pool and hero relabelings."""
    n = inst["n"]
    q = inst["pool_size"]
    pair_tokens: dict[tuple[int, int], str] = {}
    for record in inst["pair_alliances"]:
        signature = _bipartite_signature(record["rows"], q)
        token = hashlib.sha256(repr(signature).encode("ascii")).hexdigest()
        pair_tokens[(record["i"], record["j"])] = token
    class_profiles = []
    for c in range(n):
        incident = [
            pair_tokens[(min(c, d), max(c, d))]
            for d in range(n) if d != c
        ]
        class_profiles.append(tuple(sorted(incident)))
    payload = {
        "family": "underlords-regular-pair-alliance-v1",
        "n": n,
        "q": q,
        "degree": inst["degree"],
        "pair_tokens": sorted(pair_tokens.values()),
        "class_profiles": sorted(class_profiles),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow each pool while keeping the 24-hero answer and route fixed."""
    current = dict(params)
    n = min(24, int(current["n"]) + 2)
    q = int(current.get("pool_size", 24)) + 8
    if q > CERTIFICATE_LANGUAGE["bounds"]["max_pool_size"]:
        return None
    degree = max(2, min(q - 1, round(0.72 * q)))
    return {
        "n": n,
        "pool_size": q,
        "degree": degree,
        "mix_rounds": min(40, int(current.get("mix_rounds", 8)) + 1),
    }


# ---------------------------------------------------------------------------
# Attacks and explicit symmetry transformations used by selftest().


def _fallback_answer(inst: dict, labels: list[int]) -> list[int]:
    q = inst["pool_size"]
    clean = [(labels[c] if 0 <= labels[c] < q else 0) for c in range(inst["n"])]
    return _answer_from_labels(inst, clean)


def _triangle_scores(inst: dict) -> list[list[int]]:
    """Count compatible cross-pool triangles through every individual hero."""
    n = inst["n"]
    q = inst["pool_size"]
    adj = _adjacency(inst)
    scores = [[0] * q for _ in range(n)]
    for c in range(n):
        others = [x for x in range(n) if x != c]
        for value in range(q):
            score = 0
            for at, i in enumerate(others):
                left_mask = adj[c][i][value]  # type: ignore[index]
                for j in others[at + 1:]:
                    right_mask = adj[c][j][value]  # type: ignore[index]
                    scan = left_mask
                    between = adj[i][j]
                    while scan:
                        bit = scan & -scan
                        u = bit.bit_length() - 1
                        score += (between[u] & right_mask).bit_count()  # type: ignore[index]
                        scan -= bit
            scores[c][value] = score
    return scores


def _attack_outlier(inst: dict) -> list[int]:
    scores = _triangle_scores(inst)
    labels = [
        max(range(inst["pool_size"]), key=lambda x: (scores[c][x], -x))
        for c in range(inst["n"])
    ]
    return _fallback_answer(inst, labels)


def _attack_greedy(inst: dict) -> list[int]:
    n = inst["n"]
    q = inst["pool_size"]
    adj = _adjacency(inst)
    labels: list[int] = []
    for c in range(n):
        def merit(value: int) -> tuple[int, int, int]:
            prior = sum(
                (adj[d][c][labels[d]] >> value) & 1  # type: ignore[index]
                for d in range(c)
            )
            future_support = sum(
                adj[c][d][value].bit_count()  # type: ignore[index]
                for d in range(c + 1, n)
            )
            return prior, future_support, -value
        labels.append(max(range(q), key=merit))
    return _fallback_answer(inst, labels)


def _attack_random_restart(inst: dict, rng: random.Random,
                           restarts: int = 256) -> tuple[list[int], int]:
    """Randomized MRV propagation without backtracking."""
    n = inst["n"]
    q = inst["pool_size"]
    adj = _adjacency(inst)
    full = (1 << q) - 1
    operations = 0
    last_labels = [0] * n
    for _ in range(restarts):
        domains = [full] * n
        assigned: dict[int, int] = {}
        while len(assigned) < n:
            choices = [c for c in range(n) if c not in assigned]
            c = min(choices, key=lambda x: (domains[x].bit_count(), x))
            mask = domains[c]
            if not mask:
                break
            candidates = []
            scan = mask
            while scan:
                bit = scan & -scan
                value = bit.bit_length() - 1
                scan -= bit
                support = 0
                for d in choices:
                    if d == c:
                        continue
                    support += (adj[c][d][value] & domains[d]).bit_count()  # type: ignore[index]
                    operations += 1
                candidates.append((support, rng.random(), value))
            candidates.sort(reverse=True)
            _, _, value = candidates[0]
            assigned[c] = value
            for d in choices:
                if d != c:
                    domains[d] &= adj[c][d][value]  # type: ignore[index]
                    operations += 1
        for c in range(n):
            last_labels[c] = assigned.get(c, rng.randrange(q))
        if len(assigned) == n:
            candidate = _answer_from_labels(inst, [assigned[c] for c in range(n)])
            if verify(inst, candidate)[0]:
                return candidate, operations
    return _fallback_answer(inst, last_labels), operations


def _centered_multiply(inst: dict, vector: list[float],
                       adj: list[list[list[int] | None]]) -> list[float]:
    """Multiply by cross-pool adjacency minus its regular density."""
    n = inst["n"]
    q = inst["pool_size"]
    density = inst["degree"] / q
    pool_sums = [sum(vector[c * q:(c + 1) * q]) for c in range(n)]
    out = [0.0] * (n * q)
    for c in range(n):
        for x in range(q):
            value = 0.0
            for d in range(n):
                if d == c:
                    continue
                scan = adj[c][d][x]  # type: ignore[index]
                neighbor_sum = 0.0
                while scan:
                    bit = scan & -scan
                    y = bit.bit_length() - 1
                    neighbor_sum += vector[d * q + y]
                    scan -= bit
                value += neighbor_sum - density * pool_sums[d]
            out[c * q + x] = value
    return out


def _attack_spectral(inst: dict, rng: random.Random,
                     starts: int = 3, iterations: int = 24) -> tuple[list[int], int]:
    """Centered adjacency power iteration, the standard planted-graph probe."""
    n = inst["n"]
    q = inst["pool_size"]
    adj = _adjacency(inst)
    best: list[int] | None = None
    best_edges = -1
    operations = 0
    for _ in range(starts):
        vector = [rng.uniform(-1.0, 1.0) for _ in range(n * q)]
        mean = sum(vector) / len(vector)
        vector = [x - mean for x in vector]
        for _ in range(iterations):
            vector = _centered_multiply(inst, vector, adj)
            operations += n * q * (n - 1) * inst["degree"]
            norm = math.sqrt(sum(x * x for x in vector))
            if norm == 0.0:
                break
            vector = [x / norm for x in vector]
        for sign in (1.0, -1.0):
            labels = [
                max(range(q), key=lambda x: (sign * vector[c * q + x], -x))
                for c in range(n)
            ]
            edges = sum(
                (adj[i][j][labels[i]] >> labels[j]) & 1  # type: ignore[index]
                for i, j in _pair_indices(n)
            )
            if edges > best_edges:
                best_edges = edges
                best = labels
    assert best is not None
    return _answer_from_labels(inst, best), operations


class _NodeLimit(Exception):
    pass


def _dpll_attack(inst: dict, node_budget: int = _DPLL_NODE_BUDGET
                 ) -> tuple[list[int] | None, int]:
    """Exact CSP backtracking with MRV, forward checking, and a node cap."""
    n = inst["n"]
    q = inst["pool_size"]
    adj = _adjacency(inst)
    full = (1 << q) - 1
    nodes = 0

    def search(domains: list[int], assigned: list[int]) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            raise _NodeLimit
        if all(value >= 0 for value in assigned):
            return list(assigned)
        unassigned = [c for c, value in enumerate(assigned) if value < 0]
        c = min(unassigned, key=lambda x: (domains[x].bit_count(), x))
        if not domains[c]:
            return None

        # Least-constraining values first is stronger than numeric ordering.
        ranked = []
        scan = domains[c]
        while scan:
            bit = scan & -scan
            value = bit.bit_length() - 1
            scan -= bit
            support = sum(
                (adj[c][d][value] & domains[d]).bit_count()  # type: ignore[index]
                for d in unassigned if d != c
            )
            ranked.append((-support, value))
        ranked.sort()
        for _, value in ranked:
            new_domains = list(domains)
            new_assigned = list(assigned)
            new_assigned[c] = value
            new_domains[c] = 1 << value
            feasible = True
            for d in unassigned:
                if d == c:
                    continue
                new_domains[d] &= adj[c][d][value]  # type: ignore[index]
                if not new_domains[d]:
                    feasible = False
                    break
            if feasible:
                found = search(new_domains, new_assigned)
                if found is not None:
                    return found
        return None

    try:
        labels = search([full] * n, [-1] * n)
    except _NodeLimit:
        return None, nodes
    if labels is None:
        return None, nodes
    return _answer_from_labels(inst, labels), nodes


def _relabel_instance(inst: dict, class_map: list[int],
                      local_maps: list[list[int]], reorder: bool = False) -> dict:
    """Carry an instance and certificate through pool/hero relabellings."""
    n = inst["n"]
    q = inst["pool_size"]
    if sorted(class_map) != list(range(n)):
        raise ValueError("class_map must be a permutation")
    if len(local_maps) != n or any(
            sorted(mapping) != list(range(q)) for mapping in local_maps):
        raise ValueError("each local map must be a permutation")

    matrices: dict[tuple[int, int], list[int]] = {}
    for record in inst["pair_alliances"]:
        old_i, old_j = record["i"], record["j"]
        new_i, new_j = class_map[old_i], class_map[old_j]
        rows = [0] * q
        for x, mask in enumerate(record["rows"]):
            scan = mask
            while scan:
                bit = scan & -scan
                y = bit.bit_length() - 1
                scan -= bit
                nx = local_maps[old_i][x]
                ny = local_maps[old_j][y]
                if new_i < new_j:
                    rows[nx] |= 1 << ny
                else:
                    rows[ny] |= 1 << nx
        matrices[(min(new_i, new_j), max(new_i, new_j))] = rows

    pairs = [
        {"i": i, "j": j, "rows": matrices[(i, j)]}
        for i, j in _pair_indices(n)
    ]
    if reorder:
        pairs.reverse()
    transformed = {
        key: value for key, value in inst.items()
        if key not in {"pair_alliances", "answer"}
    }
    transformed["pair_alliances"] = pairs
    old_labels = _labels_from_answer(inst, inst["answer"])
    new_labels = [0] * n
    for old_c in range(n):
        new_labels[class_map[old_c]] = local_maps[old_c][old_labels[old_c]]
    transformed["answer"] = _answer_from_labels(transformed, new_labels)
    return transformed


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return JSON-native measured evidence."""
    report: dict[str, Any] = {}

    g1_failures = []
    g1_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": reason}
                )
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total - len(g1_failures),
        "total": g1_total,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)

    corruptions: dict[str, dict[str, object]] = {}
    dropped = list(inst["answer"][:-1])
    swapped = list(inst["answer"])
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(inst["answer"])
    duplicated[1] = duplicated[0]
    out_of_range = list(inst["answer"])
    out_of_range[-1] = inst["hero_count"]
    for name, candidate in {
        "drop_one": dropped,
        "swap_two": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [str(row["reason"]) for row in corruptions.values()]
    g2_pass = (
        all(bool(row["rejected"]) for row in corruptions.values())
        and len(set(reasons)) == len(reasons)
    )
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "rejected": sum(bool(row["rejected"]) for row in corruptions.values()),
        "total": len(corruptions),
        "distinct_reasons": len(set(reasons)),
        "cases": corruptions,
    }

    encoded = json.dumps(inst["answer"])
    parse_cases = [
        f"I checked every alliance. <answer>{encoded}</answer>",
        f"Final:\n<answer>\n```json\n{encoded}\n```\n</answer>",
        f"Some prose before. <answer> {encoded} </answer> Some prose after.",
    ]
    parsed_ok = sum(parse_answer(case) == inst["answer"] for case in parse_cases)
    garbage_ok = all(parse_answer(x) is None for x in ["", "[1,2]", "<answer>x</answer>"])
    report["G3_round_trip"] = {
        "pass": parsed_ok == len(parse_cases) and garbage_ok,
        "round_trips": parsed_ok,
        "total": len(parse_cases),
        "garbage_rejected": garbage_ok,
    }

    density_inst = make_instance(seed=112358, **shipping)
    density_rng = random.Random(24680)
    density_total = 200_000
    density_hits = 0
    for _ in range(density_total):
        if verify(density_inst, random_candidate(density_inst, density_rng))[0]:
            density_hits += 1
    report["G4_guess_resistance"] = {
        "pass": density_hits / density_total < 1e-6,
        "hits": density_hits,
        "total": density_total,
        "observed_probability": density_hits / density_total,
        "structure_aware_space": search_space(density_inst),
        "prior": "uniform one hero from each pool, already in required pool order",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1
    baseline_inst = make_instance(seed=424242, **shipping)
    start = time.perf_counter()
    baseline_answer, baseline_nodes = _dpll_attack(baseline_inst)
    baseline_seconds = time.perf_counter() - start
    baseline_solved = (
        baseline_answer is not None and verify(baseline_inst, baseline_answer)[0]
    )
    report["G5_density_and_baseline"] = {
        "pass": not baseline_solved,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": density_total,
        "shipping_density_estimate": density_hits / density_total,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_name": "exact CSP backtracking with MRV and forward checking",
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_nodes": baseline_nodes,
        "baseline_node_budget": _DPLL_NODE_BUDGET,
        "baseline_solved": baseline_solved,
    }

    attack_names = [
        "per_hero_triangle_outlier",
        "greedy_left_to_right",
        "random_restart_mrv_256",
        "centered_spectral_power_iteration",
        "exact_csp_dpll_300k_nodes",
    ]
    attack_seeds = list(range(3100, 3108))
    attacks = {
        name: {"successes": 0, "attempts": len(attack_seeds), "operations_or_nodes": 0}
        for name in attack_names
    }
    for seed in attack_seeds:
        current = make_instance(seed=seed, **shipping)
        candidates: dict[str, object | None] = {}
        candidates[attack_names[0]] = _attack_outlier(current)
        candidates[attack_names[1]] = _attack_greedy(current)
        candidate, operations = _attack_random_restart(
            current, random.Random(seed ^ 0xA5A5A5A5)
        )
        candidates[attack_names[2]] = candidate
        attacks[attack_names[2]]["operations_or_nodes"] += operations
        candidate, operations = _attack_spectral(
            current, random.Random(seed ^ 0x5A5A5A5A)
        )
        candidates[attack_names[3]] = candidate
        attacks[attack_names[3]]["operations_or_nodes"] += operations
        candidate, nodes = _dpll_attack(current)
        candidates[attack_names[4]] = candidate
        attacks[attack_names[4]]["operations_or_nodes"] += nodes
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": "exact_csp_dpll_300k_nodes",
        "planted_graph_attack": "centered_spectral_power_iteration",
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated = escalate(shipping)
    report["G7_scales"] = {
        "pass": doubled_ok and isinstance(escalated, dict),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_hero_count": doubled["hero_count"],
        "doubled_verify_reason": doubled_reason,
        "escalated_params": escalated,
    }

    invariant_trials = 0
    carried_trials = 0
    unrelated_keys = []
    for seed in range(20):
        small = make_instance(
            n=8, pool_size=8, degree=5, mix_rounds=4, seed=5000 + seed
        )
        original_key = canonical_key(small)
        unrelated_keys.append(original_key)
        rng = random.Random(9000 + seed)
        class_map = list(range(small["n"]))
        rng.shuffle(class_map)
        local_maps = []
        for _ in range(small["n"]):
            mapping = list(range(small["pool_size"]))
            rng.shuffle(mapping)
            local_maps.append(mapping)
        transformed = _relabel_instance(small, class_map, local_maps, reorder=True)
        if canonical_key(transformed) == original_key:
            invariant_trials += 1
        if verify(transformed, transformed["answer"])[0]:
            carried_trials += 1

        second_classes = list(range(small["n"]))
        rng.shuffle(second_classes)
        second_locals = []
        for _ in range(small["n"]):
            mapping = list(range(small["pool_size"]))
            rng.shuffle(mapping)
            second_locals.append(mapping)
        composed = _relabel_instance(
            transformed, second_classes, second_locals, reorder=(seed % 2 == 0)
        )
        if canonical_key(composed) == original_key:
            invariant_trials += 1
        if verify(composed, composed["answer"])[0]:
            carried_trials += 1
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_trials == 40
            and carried_trials == 40
            and distinct_keys == len(unrelated_keys)
        ),
        "invariant_relabelings": invariant_trials,
        "relabeling_attempts": 40,
        "valid_carried_witnesses": carried_trials,
        "carried_attempts": 40,
        "distinct_unrelated": distinct_keys,
        "unrelated_attempts": len(unrelated_keys),
        "key_kind": "common-neighbor/class-profile invariant, never seed/render/answer",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _answer_atoms(inst["answer"])
    # Conservative: each integer and punctuation run can tokenize separately.
    answer_tokens = 2 * answer_atoms + 2
    intended_operations = math.comb(inst["n"], 2)
    within_caps = (
        answer_chars <= 2000
        and answer_atoms <= 256
        and intended_operations <= 300
    )
    arms = {key: dict(_ORACLE_EVIDENCE[key]) for key in ("bare", "hinted", "placebo")}
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    hinted_hardened = _ORACLE_EVIDENCE["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and bool(value.get("pass"))
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
