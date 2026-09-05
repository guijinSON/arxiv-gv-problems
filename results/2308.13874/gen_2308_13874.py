"""Verified generators for 1-factors in structured bipartite graphs.

Section 1 of arXiv:2308.13874 defines a k-factor as a k-regular spanning
subgraph; a 1-factor is a perfect matching.  This module inverse-generates a
bipartite graph as a union of affine perfect matchings.  One affine component
is retained as the planted answer, but verification accepts every perfect
matching.  The module is deterministic in ``(n, seed, d)``, standard-library
only, silent on import, and performs no file or network I/O.
"""

from __future__ import annotations

import collections
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
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "explicit finite bipartite graph",
        "1-factor (perfect matching)",
    ],
    "verification_operations": [
        "integer range and permutation checks",
        "bipartite edge-membership checks",
        "degree-one spanning-subgraph check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The sum modulo n of each left neighborhood is affine in its vertex "
        "label; without noticing that invariant, one must run augmenting-path "
        "matching or search among permutations."
    ),
    "hardness_basis": (
        "Track B: a 1-factor is found by Hopcroft--Karp in O(E sqrt(V)); at "
        "the hard shipping preset it solved 8/8 in at most 0.0009 s and 10,765 "
        "counted edge/queue operations, while the neighborhood-sum route uses "
        "297 exact operations and the explicit permutation space is 251!."
    ),
    "max_answer_tokens": 224,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the number of vertices on EACH side; d is the common bipartite degree.
# The named rungs grow both the permutation haystack and the amount of adjacency
# clutter.  The demo is intentionally small enough to enumerate on paper.
DIFFICULTY = {
    "demo": {"n": 5, "d": 2},
    "easy": {"n": 181, "d": 11},
    "medium": {"n": 223, "d": 13},
    "hard": {"n": 251, "d": 17},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "The sum modulo n of each left neighborhood varies affinely with the "
    "left-vertex label."
)
PLACEBO_HINT = (
    "The neighbor lists use ordinary decimal vertex labels and may be read "
    "in their displayed order."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A perfect matching encoded as one permutation pi of 0,...,n-1: "
        "pi[x] is the right endpoint paired with left vertex x."
    ),
    "bounds": {
        "length": "n",
        "entry_min": 0,
        "entry_max_inclusive": "n-1",
        "all_entries_distinct": True,
        "named_hard_n": 251,
    },
}


NOTES = r"""
STEP 0. Section 1 (the paragraph before Theorem 1.1) fixes the native object:
a k-factor is a k-regular spanning subgraph, so a 1-factor is exactly a perfect
matching. The same section says K_n has a k-factor when nk is even. Theorem 1.2
and Corollary 1.1 give clique-count and edge-count sufficient regimes; Lemma 2.4
gives the especially easy minimum-degree-at-least-n/2 regime. Those results
guarantee existence, not distributional search hardness. Moreover, 1-factors
are found in polynomial time by matching algorithms. Track A would therefore
be false; this module declares Track B.

GENERATION. Choose a unit a modulo n and d distinct offsets B. The bipartite
edge set is the union of the d affine bijections x -> a*x+b (b in B). Choose b
uniformly from B and retain that bijection as the planted 1-factor. Generation
never searches for a matching. Every offset is sampled identically, so planted
and decoy affine factors have the same distribution. No attack or matching
algorithm is run during generation.

COMPACT ROUTE AND REFERENCE ALGORITHM. If N(x)=a*x+B modulo n, then
sum(N(1))-sum(N(0)) = d*a modulo n. Since gcd(d,n)=1, two neighborhood sums
recover a. Any b in N(0), followed by the recurrence y <- y+a mod n, yields a
perfect matching. The counted route stays below 300 operations at every named
preset. Hopcroft--Karp is the successful O(E*sqrt(V)) mechanical reference and
is reported separately from the failing Track B attacks.

ATTACKS. All right degrees are equal, defeating per-vertex outliers. Displayed
neighbor order is independently shuffled, defeating first-choice and
left-to-right greedy rules. At the shipping parameters, 256 randomized greedy
restarts failed on every tested seed without generator-side conditioning. The
obvious unit-slope affine ansatz is false because a is sampled as a nontrivial
unit. Verification nevertheless accepts every genuine matching.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000
_ATTACK_RESTARTS = 256

# Filled from the three harden.py runs after the shipping rung is known.  These
# are diagnostics, not an oracle simulation performed by selftest().
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
}
_G9_HINTED_VERDICT = (
    "solved at the shipping preset (3/3); script verdict cap_bound after the "
    "fixed-length d=19 escalation was also solved"
)


def _validate_params(n: int, d: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not 5 <= n <= 600:
        raise ValueError("n must be an integer in 5..600")
    if isinstance(d, bool) or not isinstance(d, int) or not 2 <= d < n:
        raise ValueError("d must be an integer in 2..n-1")
    if math.gcd(d, n) != 1:
        raise ValueError("d must be invertible modulo n")


def _is_permutation(values: list[int], n: int) -> bool:
    return len(values) == n and len(set(values)) == n and all(
        isinstance(v, int) and not isinstance(v, bool) and 0 <= v < n
        for v in values
    )


def _candidate_outlier(rows: list[list[int]]) -> list[int]:
    """Pick the least-degree neighbor, breaking the regular tie numerically."""
    n = len(rows)
    right_degree = [0] * n
    for row in rows:
        for y in row:
            right_degree[y] += 1
    return [min(row, key=lambda y: (right_degree[y], y)) for row in rows]


def _candidate_display_greedy(rows: list[list[int]]) -> list[int] | None:
    used: set[int] = set()
    answer: list[int] = []
    for row in rows:
        choice = next((y for y in row if y not in used), None)
        if choice is None:
            return None
        used.add(choice)
        answer.append(choice)
    return answer


def _candidate_unit_slope(rows: list[list[int]]) -> list[int]:
    n = len(rows)
    b = rows[0][0]
    return [(x + b) % n for x in range(n)]


def _attack_seed(rows: list[list[int]]) -> int:
    h = hashlib.sha256()
    for row in rows:
        h.update(",".join(map(str, row)).encode("ascii"))
        h.update(b";")
    return int.from_bytes(h.digest()[:8], "big")


def _candidate_random_greedy(
    rows: list[list[int]], restarts: int = _ATTACK_RESTARTS
) -> tuple[list[int] | None, int]:
    """Random row order and random neighbor order; return work in row visits."""
    n = len(rows)
    rng = random.Random(_attack_seed(rows))
    visits = 0
    for _ in range(restarts):
        order = list(range(n))
        rng.shuffle(order)
        used: set[int] = set()
        answer = [-1] * n
        for x in order:
            visits += 1
            choices = rows[x][:]
            rng.shuffle(choices)
            y = next((z for z in choices if z not in used), None)
            if y is None:
                break
            used.add(y)
            answer[x] = y
        else:
            return answer, visits
    return None, visits


def _raw_valid(rows: list[list[int]], answer: list[int] | None) -> bool:
    if answer is None or not _is_permutation(answer, len(rows)):
        return False
    return all(y in rows[x] for x, y in enumerate(answer))


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a d-regular bipartite graph with a known 1-factor."""
    unknown = set(params) - {"d"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    d = params.get("d", 11)
    _validate_params(n, d)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    units = [a for a in range(2, n) if math.gcd(a, n) == 1]
    if not units:
        raise ValueError("n has no supported nontrivial affine multiplier")

    a = rng.choice(units)
    offsets = rng.sample(range(n), d)
    planted_offset = rng.choice(offsets)
    rows = [
        [((a * x + b) % n) for b in offsets]
        for x in range(n)
    ]
    for row in rows:
        rng.shuffle(row)
    answer = [(a * x + planted_offset) % n for x in range(n)]
    return {
        "family": "affine_union_bipartite_one_factor",
        "n": n,
        "d": d,
        "neighbors": rows,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete, self-contained perfect-matching problem."""
    n, d = inst["n"], inst["d"]
    lines = [
        "ONE-FACTOR OF AN EXPLICIT BIPARTITE GRAPH",
        "",
        f"The graph is simple and bipartite. Its left vertices are L_0,...,L_{n-1}",
        f"and its right vertices are R_0,...,R_{n-1}. There are no edges within",
        "one side. For each left vertex x, the line below lists exactly all",
        f"{d} right-vertex labels y for which {{L_x,R_y}} is an edge.",
        "The order of neighbors on a line carries no meaning.",
        "",
        "A 1-factor (perfect matching) is a set of edges in which every vertex",
        "of the graph occurs exactly once. Find any 1-factor.",
        "",
        "Adjacency lists (all labels and row indices are 0-based):",
    ]
    lines.extend(
        f"{x}: " + " ".join(map(str, row))
        for x, row in enumerate(inst["neighbors"])
    )
    lines.extend(
        [
            "",
            f"Encode the matching as a JSON list pi of exactly {n} integers:",
            "pi[x]=y means that L_x is paired with R_y. List order therefore",
            f"matters. Every entry must lie in 0,...,{n-1}; every right label",
            "must occur exactly once; repetitions are forbidden.",
            "Give your final answer inside <answer></answer> tags.",
            "Example syntax for a four-vertex side: <answer>[2,0,3,1]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON integer list; never raise on bad output."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    try:
        value = json.loads(matches[-1].strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any perfect matching exactly; never inspect ``inst['answer']``."""
    n = inst.get("n")
    rows = inst.get("neighbors")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != n:
        return False, f"answer must have exactly {n} entries"
    for x, y in enumerate(answer):
        if isinstance(y, bool) or not isinstance(y, int):
            return False, f"entry {x} is not an integer"
        if not 0 <= y < n:
            return False, f"entry {x} is outside 0..{n-1}"
    if len(set(answer)) != n:
        return False, "right endpoints must form a permutation without repeats"
    if not isinstance(rows, list) or len(rows) != n:
        return False, "instance has the wrong number of adjacency rows"
    for x, y in enumerate(answer):
        row = rows[x]
        if not isinstance(row, list):
            return False, f"instance adjacency row {x} is malformed"
        if y not in row:
            return False, f"pair (L_{x},R_{y}) is not an edge"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-aware space of permutations."""
    candidate = list(range(inst["n"]))
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int:
    """The certificate language contains all n! permutations."""
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count valid matchings exactly only when n! stays below the work cap."""
    n = inst["n"]
    if math.factorial(n) > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.permutations(range(n)):
        if all(candidate[x] in inst["neighbors"][x] for x in range(n)):
            count += 1
    return count


def _transpose(rows: list[list[int]]) -> list[list[int]]:
    cols = [[] for _ in rows]
    for x, row in enumerate(rows):
        for y in row:
            cols[y].append(x)
    return cols


def _orientation_profile(rows: list[list[int]]) -> list[list[Any]]:
    """A relabelling-invariant multiset of edge-local codegree signatures."""
    cols = _transpose(rows)
    codegree: collections.Counter[tuple[int, int]] = collections.Counter()
    for col in cols:
        for i, x in enumerate(col):
            for x2 in col[i + 1 :]:
                codegree[(min(x, x2), max(x, x2))] += 1
    signatures: collections.Counter[tuple[int, ...]] = collections.Counter()
    for y, col in enumerate(cols):
        del y  # the label is deliberately absent from the invariant
        for x in col:
            sig = tuple(
                sorted(
                    codegree[(min(x, x2), max(x, x2))]
                    for x2 in col
                    if x2 != x
                )
            )
            signatures[sig] += 1
    return [[list(sig), multiplicity] for sig, multiplicity in sorted(signatures.items())]


def canonical_key(inst: dict) -> str:
    """Key on an exact graph invariant, never on seed, labels, or rendering."""
    rows = inst["neighbors"]
    left = _orientation_profile(rows)
    right = _orientation_profile(_transpose(rows))
    two_sided = sorted([left, right], key=lambda value: json.dumps(value, separators=(",", ":")))
    invariant = {
        "n": inst["n"],
        "d": inst["d"],
        "edge_local_codegrees": two_sided,
    }
    payload = json.dumps(invariant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase clutter at fixed witness length before reporting the cap."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n, d = p["n"], p["d"]
    named = [(181, 11), (223, 13), (251, 17)]
    for nn, dd in named:
        if n < nn:
            p["n"], p["d"] = nn, dd
            return p
    if n == 251 and d < 19:
        p["d"] = 19
        return p
    # More vertices cross the 256-atom answer cap; more degree crosses the
    # conservative 300-operation compact-route cap before adding useful signal.
    return "cap_bound"


def _hopcroft_karp(rows: list[list[int]]) -> tuple[list[int] | None, dict[str, int]]:
    """Standard bipartite maximum matching with explicit operation counters."""
    n = len(rows)
    pair_u = [-1] * n
    pair_v = [-1] * n
    dist = [0] * n
    inf = n + 1
    counters = {"edge_inspections": 0, "queue_pops": 0, "phases": 0}

    def bfs() -> bool:
        queue: collections.deque[int] = collections.deque()
        found = False
        for u in range(n):
            if pair_u[u] == -1:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = inf
        while queue:
            u = queue.popleft()
            counters["queue_pops"] += 1
            for v in rows[u]:
                counters["edge_inspections"] += 1
                mate = pair_v[v]
                if mate == -1:
                    found = True
                elif dist[mate] == inf:
                    dist[mate] = dist[u] + 1
                    queue.append(mate)
        return found

    def dfs(u: int) -> bool:
        for v in rows[u]:
            counters["edge_inspections"] += 1
            mate = pair_v[v]
            if mate == -1 or (dist[mate] == dist[u] + 1 and dfs(mate)):
                pair_u[u] = v
                pair_v[v] = u
                return True
        dist[u] = inf
        return False

    matched = 0
    while bfs():
        counters["phases"] += 1
        progress = 0
        for u in range(n):
            if pair_u[u] == -1 and dfs(u):
                progress += 1
        matched += progress
        if progress == 0:
            break
    return (pair_u if matched == n else None), counters


def _inverse_with_division_count(a: int, modulus: int) -> tuple[int, int]:
    """Extended Euclid inverse and a conservative division-step count."""
    old_r, r = a, modulus
    old_s, s = 1, 0
    steps = 0
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        steps += 1
    if old_r != 1:
        raise ValueError("noninvertible degree")
    return old_s % modulus, steps


def _compact_translation(inst: dict) -> tuple[list[int], int]:
    """Recover an affine matching using the intended neighborhood-sum route."""
    n, d, rows = inst["n"], inst["d"], inst["neighbors"]
    s0 = sum(rows[0]) % n
    s1 = sum(rows[1]) % n
    inv_d, euclid_steps = _inverse_with_division_count(d, n)
    slope = ((s1 - s0) * inv_d) % n
    value = rows[0][0]
    answer = [value]
    for _ in range(1, n):
        value = (value + slope) % n
        answer.append(value)
    # 2(d-1) additions for the sums, two reductions, subtraction,
    # multiplication, reduction, n-1 recurrence additions/reductions, and a
    # conservative two exact operations per Euclidean division.
    operations = 2 * (d - 1) + 5 + 2 * euclid_steps + (n - 1)
    return answer, operations


def _shuffle_rows(inst: dict, rng: random.Random) -> dict:
    out = {k: v for k, v in inst.items() if k not in {"neighbors", "answer"}}
    out["neighbors"] = [row[:] for row in inst["neighbors"]]
    for row in out["neighbors"]:
        rng.shuffle(row)
    out["answer"] = inst["answer"][:]
    return out


def _relabel(inst: dict, left: list[int], right: list[int]) -> dict:
    """left/right map old labels to new labels; carry the witness."""
    n = inst["n"]
    rows = [[] for _ in range(n)]
    answer = [-1] * n
    for old_x, row in enumerate(inst["neighbors"]):
        rows[left[old_x]] = [right[y] for y in row]
        answer[left[old_x]] = right[inst["answer"][old_x]]
    return {
        "family": inst["family"],
        "n": n,
        "d": inst["d"],
        "neighbors": rows,
        "answer": answer,
    }


def _swap_sides(inst: dict) -> dict:
    rows = _transpose(inst["neighbors"])
    answer = [-1] * inst["n"]
    for x, y in enumerate(inst["answer"]):
        answer[y] = x
    return {
        "family": inst["family"],
        "n": inst["n"],
        "d": inst["d"],
        "neighbors": rows,
        "answer": answer,
    }


def _find_bad_swap(inst: dict) -> list[int]:
    original = inst["answer"]
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            candidate = original[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if not verify(inst, candidate)[0]:
                return candidate
    raise AssertionError("every transposition unexpectedly remained a matching")


def selftest() -> dict:
    """Run and report all mandatory G1--G9 gates with measured quantities."""
    report: dict[str, Any] = {}
    preset_names = list(DIFFICULTY)

    # G1: every named rung, four seeds, plus JSON-native answers.
    g1_ok = True
    g1_instances = 0
    for preset in preset_names:
        for seed in range(4):
            inst = make_instance(seed=seed, **DIFFICULTY[preset])
            ok, _ = verify(inst, inst["answer"])
            g1_ok &= ok and json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_instances += 1
    report["G1_planted_verifies"] = {
        "pass": g1_ok,
        "instances": g1_instances,
        "generation_route": (
            "inverse generation: sample affine bijections first and retain one"
        ),
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=0, **shipping_params)

    # G2: five semantically different corruptions and five distinct reasons.
    corruptions: dict[str, list[int]] = {}
    corruptions["empty"] = []
    corruptions["drop_one"] = shipping["answer"][:-1]
    out_of_range = shipping["answer"][:]
    out_of_range[-1] = shipping["n"]
    corruptions["out_of_range"] = out_of_range
    duplicate = shipping["answer"][:]
    duplicate[-1] = duplicate[0]
    corruptions["duplicate"] = duplicate
    corruptions["swap_two"] = _find_bad_swap(shipping)
    reasons: dict[str, str] = {}
    g2_ok = True
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        g2_ok &= not ok
        reasons[name] = reason
    g2_ok &= len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "reasons": reasons,
    }

    # G3: realistic prose/fence wrapper, exact round trip, and malformed input.
    blob = json.dumps(shipping["answer"], separators=(",", ":"))
    model_style = "I used alternating paths.\n```json\n<answer>" + blob + "</answer>\n```"
    parsed = parse_answer(model_style)
    g3_ok = parsed == shipping["answer"] and parse_answer("no tagged answer") is None
    report["G3_round_trip"] = {
        "pass": g3_ok,
        "json_native": json.loads(json.dumps(shipping["answer"])) == shipping["answer"],
        "answer_elements": len(shipping["answer"]),
    }

    # G4 and shipping part of G5 share the same required 200k uniform sample.
    guess_rng = random.Random(0x230813874)
    hits = 0
    sample_t0 = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(shipping, guess_rng)
        if _raw_valid(shipping["neighbors"], candidate):
            hits += 1
    sample_seconds = time.perf_counter() - sample_t0
    probability = hits / _G4_SAMPLES
    space = search_space(shipping)
    # Every left vertex has only d choices, so there are at most d**n valid
    # permutations.  This elementary exact upper bound is far stronger than
    # the empirical zero-hit result and avoids treating zero observations as a
    # proof that the true density is below 1e-6.
    density_upper_numerator = shipping["d"] ** shipping["n"]
    density_upper = density_upper_numerator / space
    density_upper_log10 = (
        shipping["n"] * math.log10(shipping["d"])
        - math.lgamma(shipping["n"] + 1) / math.log(10)
    )
    report["G4_guess_resistance"] = {
        "pass": density_upper < 1e-6 and probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "empirical_probability": probability,
        "structure_aware_space": space,
        "exact_density_upper_numerator": density_upper_numerator,
        "exact_density_upper_denominator": space,
        "exact_density_upper": density_upper,
        "exact_density_upper_log10": density_upper_log10,
        "prior": "uniform permutations; length, range, and all-different enforced",
        "sample_wall_seconds": sample_seconds,
    }

    # G5/G6 measurements: eight independent shipping instances.
    attack_results = {
        "equal_degree_outlier_then_smallest": {"successes": 0, "attempts": 8},
        "left_to_right_display_greedy": {"successes": 0, "attempts": 8},
        "random_greedy_restart_256": {"successes": 0, "attempts": 8},
        "by_hand_unit_slope_affine_ansatz": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    compact_successes = 0
    reference_walls: list[float] = []
    reference_ops: list[int] = []
    reference_edges: list[int] = []
    reference_phases: list[int] = []
    compact_ops: list[int] = []
    restart_visits = 0
    restart_t0 = time.perf_counter()
    for seed in range(8):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        candidates = {
            "equal_degree_outlier_then_smallest": _candidate_outlier(inst["neighbors"]),
            "left_to_right_display_greedy": _candidate_display_greedy(inst["neighbors"]),
            "by_hand_unit_slope_affine_ansatz": _candidate_unit_slope(inst["neighbors"]),
        }
        random_answer, visits = _candidate_random_greedy(inst["neighbors"])
        restart_visits += visits
        candidates["random_greedy_restart_256"] = random_answer
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1

        t0 = time.perf_counter()
        reference, counters = _hopcroft_karp(inst["neighbors"])
        reference_walls.append(time.perf_counter() - t0)
        ref_ok = reference is not None and verify(inst, reference)[0]
        reference_successes += int(ref_ok)
        op_count = counters["edge_inspections"] + counters["queue_pops"]
        reference_ops.append(op_count)
        reference_edges.append(counters["edge_inspections"])
        reference_phases.append(counters["phases"])

        compact, operations = _compact_translation(inst)
        compact_successes += int(verify(inst, compact)[0])
        compact_ops.append(operations)
    restart_seconds = time.perf_counter() - restart_t0

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            density_upper < 1e-6
            and probability < 1e-6
            and isinstance(demo_count, int)
            and reference_successes == 8
        ),
        "shipping_sample_hits": hits,
        "shipping_sample_total": _G4_SAMPLES,
        "shipping_sample_fraction": probability,
        "shipping_exact_density_upper": density_upper,
        "shipping_exact_density_upper_log10": density_upper_log10,
        "shipping_known_valid_affine_matchings_lower_bound": shipping["d"],
        "shipping_sample_wall_seconds": sample_seconds,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "reference_max_wall_seconds": max(reference_walls),
        "reference_mean_wall_seconds": sum(reference_walls) / len(reference_walls),
        "reference_max_operations": max(reference_ops),
        "reference_max_edge_inspections": max(reference_edges),
        "reference_max_phases": max(reference_phases),
        "reference_attempts": 8,
        "failing_restart_wall_seconds": restart_seconds,
        "failing_restart_row_visits": restart_visits,
    }

    all_attacks_failed = all(v["successes"] == 0 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Hopcroft--Karp bipartite maximum matching",
            "complexity": "O(E sqrt(V))",
            "wall_clock_sec_max": max(reference_walls),
            "wall_clock_sec_mean": sum(reference_walls) / len(reference_walls),
            "operations": max(reference_ops),
            "edge_inspections": max(reference_edges),
            "phases": max(reference_phases),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "modular neighborhood-sum invariant and affine recurrence",
            "operations": max(compact_ops),
            "solves": f"{compact_successes}/8",
        },
    }

    # G7: literally double n, keeping d and certificate construction valid.
    doubled_params = {"n": 2 * shipping_params["n"], "d": shipping_params["d"]}
    doubled = make_instance(seed=4242, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > space,
        "base_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "base_edges": shipping_params["n"] * shipping_params["d"],
        "doubled_edges": doubled_params["n"] * doubled_params["d"],
        "planted_verifies": doubled_ok,
        "fixed_answer_length_escalation_axis": "raise d from 17 to 19 at n=251",
    }

    # G8: arbitrary left/right relabelling, input reorder, side swap, compositions.
    invariant_checks = 0
    real_transform_checks = 0
    distinct_keys: list[str] = []
    g8_ok = True
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping_params)
        base_key = canonical_key(inst)
        distinct_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        left = list(range(inst["n"]))
        right = list(range(inst["n"]))
        rng.shuffle(left)
        rng.shuffle(right)
        relabelled = _relabel(inst, left, right)
        swapped = _swap_sides(inst)
        reordered = _shuffle_rows(inst, rng)
        composed = _shuffle_rows(_swap_sides(relabelled), rng)
        for transformed in (relabelled, swapped, reordered, composed):
            invariant_checks += 1
            g8_ok &= canonical_key(transformed) == base_key
            ok, _ = verify(transformed, transformed["answer"])
            real_transform_checks += 1
            g8_ok &= ok
    unrelated_distinct = len(set(distinct_keys))
    g8_ok &= unrelated_distinct == len(distinct_keys)
    report["G8_canonical_key"] = {
        "pass": g8_ok,
        "invariance_checks": invariant_checks,
        "real_transform_checks": real_transform_checks,
        "distinct_unrelated": unrelated_distinct,
        "unrelated_total": len(distinct_keys),
        "symmetries": (
            "neighbor-list reorder, arbitrary independent left/right relabelling, "
            "side swap, and their composition"
        ),
        "key_invariant": "two-sided multiset of edge-local integer codegrees",
    }

    compact_answer, intended_ops = _compact_translation(shipping)
    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens
    arms = {name: dict(values) for name, values in _G9_ARMS.items()}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and len(compact_answer) <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(compact_answer),
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
