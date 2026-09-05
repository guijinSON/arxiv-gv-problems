"""Verified generator for arXiv:2309.12607.

The paper studies Hamilton cycle transversals in families of (random
subgraphs of) Dirac graphs.  This module fixes a displayed Hamilton cycle and
asks for the bijection from its edges to a family of sparse subgraphs.  The
incidence table is inverse-generated around a hidden affine perfect matching.

Only the Python standard library is used.  Generation is deterministic in
``(n, seed, **params)`` and never solves the instance it creates.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "family of sparse subgraphs of a complete Dirac graph",
        "fixed Hamilton cycle",
        "rainbow edge-to-graph bijection",
    ],
    "verification_operations": [
        "permutation comparison",
        "exact graph-edge membership",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, Lemma 5.1: perfect matchings of the auxiliary "
        "color--fixed-edge bipartite graph are exactly rainbow colorings"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Cycle-edge indices and graph colors hide an affine perfect matching "
        "over a prime field; without recognizing it, one must execute a "
        "general bipartite matching algorithm on the displayed incidence table."
    ),
    "hardness_basis": (
        "Track B: Sections 4--5 use auxiliary bipartite matchings for rainbow "
        "edge selection and fixed-path coloring; Hopcroft--Karp is O(E sqrt(V)) "
        "and averaged 2,443 exact edge scans (0.0061 s in the final gate run) "
        "at shipping, whereas "
        "the measured affine change of variables needs 266 modular operations."
    ),
    "max_answer_tokens": 80,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 7, "width": 2},
    "easy": {"n": 79, "width": 4},
    "medium": {"n": 97, "width": 6},
    "hard": {"n": 107, "width": 8},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Modulo the prime cycle length, the color-to-edge incidence contains an "
    "affine permutation shared across all rows."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the cycle indices and graph labels helps prevent "
    "small transcription errors in the answer."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array containing every graph color 0,...,p-1 exactly once; "
        "entry t colors the displayed Hamilton-cycle edge e_t."
    ),
    "bounds": {
        "shipping_answer_length": 107,
        "shipping_entry_min": 0,
        "shipping_entry_max": 106,
        "maximum_output_atoms": 256,
    },
}

# Filled from the script-owned oracle runs after hardening.  These diagnostics
# do not determine the G9 pass flag; only the size and effort caps do.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable: OpenRouter HTTP 403 key-total-limit",
}

NOTES = r"""
Definition and paper regime. Section 1.2 defines a G-transversal as an edge
set E together with a bijection phi:E->[m] for which e belongs to G_phi(e),
and defines a Hamilton G-transversal when E is a Hamilton cycle. Theorems 1.4
and 1.5 (v3 numbering) study Hamilton transversals in random subgraphs of
Dirac graphs. Every base graph here is K_p, which is Dirac, and every displayed
F_c is a sparse subgraph of that base. The cycle is fixed, and Section 5,
Lemma 5.1 licenses the resulting auxiliary bipartite matching representation:
perfect matchings are exactly rainbow colorings of the fixed edges. Therefore
this is declared a paper-licensed reduction rather than full native coverage.
The sampling is conditioned by inverse generation rather than claimed to be
the paper's unconditioned binomial distribution. The paragraph after Theorem
1.5 identifies the basic threshold obstructions: the common sparsifier needs
minimum degree at least two, while independent color graphs must be nonempty;
the counterexample after Question 1.6 adds a parity obstruction in the fully
combined setting. This module does not claim to sample any of those threshold
regimes.

Step-0 hardness decision. This is not Track A. Section 4's cover-down step
constructs rainbow edge sets through maximum matching in an auxiliary
bipartite graph; Section 5 explicitly identifies perfect matchings with rainbow
colorings of fixed path edges. A standard Hopcroft--Karp computation therefore
produces this module's certificate in polynomial time. The self-test runs that
reference algorithm and reports its exact edge scans. Track B is appropriate
because the displayed table has hundreds of incidences, while a hidden affine
perfect matching can be recovered from modular differences and emitted by a
recurrence within the 300-operation no-tool cap.

Inverse generation. For a prime p, first sample nonzero a and b modulo p. The
answer assigns color a^{-1}(t-b) to cycle edge e_t. For each color c, place the
edge e_(ac+b) in F_c and add uniformly sampled distinct cycle-edge decoys;
then shuffle each row, the rows, and the vertex names. Thus the selected edges
are all p cycle edges exactly once. The certificate is known before any decoy
is drawn. For every fixed row, the planted location and every decoy location
have the same uniform marginal distribution.

Attacks. The panel tests edge-frequency outliers, deterministic first-fit,
256 random fixed-order greedy restarts, and the obvious shift/reversal ansatz.
The slope sampler excludes those four elementary ansatz slopes for non-demo
instances; at the optional p=127 escalation it also avoids long Euclidean
chains so the compact route stays under the arithmetic cap. The uniform offset
still prevents either restriction from distinguishing the planted entry inside
any individual row. The successful Hopcroft--Karp reference is reported
separately, as Track B requires.

Canonicalization. Vertex names and row/edge input order are discarded. Color
names are quotiented by sorting the row sets, and the incidence system is
minimized over every rotation and reflection of the displayed cycle. This
exactly covers arbitrary vertex renaming, arbitrary color renaming, input
reordering, and the dihedral symmetries of the fixed Hamilton cycle.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    value = max(5, int(value))
    if value % 2 == 0:
        value += 1
    while not _is_prime(value):
        value += 2
    return value


def _inverse_mod(value: int, modulus: int) -> int:
    """Return the inverse of value modulo the prime modulus."""
    old_r, r = value % modulus, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ValueError("value is not invertible")
    return old_s % modulus


def _choose_slope(p: int, rng: random.Random) -> int:
    forbidden = {1, p - 1, 2 % p, (-2) % p} if p >= 11 else set()

    def euclid_rounds(value: int) -> int:
        old_r, remainder = value, p
        rounds = 0
        while remainder:
            quotient = old_r // remainder
            old_r, remainder = remainder, old_r - quotient * remainder
            rounds += 1
        return rounds

    # At the optional p=127 escalation, long Euclidean chains alone can use
    # enough of the arithmetic budget that no choice of decoys can fit.  This
    # restriction does not create a per-row outlier: the uniform offset still
    # makes every planted edge uniform in every graph row.
    choices = [
        a
        for a in range(1, p)
        if a not in forbidden and (p < 120 or euclid_rounds(a) <= 6)
    ]
    return rng.choice(choices)


def _edge_positions(inst: dict) -> list[set[int]]:
    """Return rows indexed by color, independent of their display order."""
    p = int(inst["p"])
    rows: list[set[int] | None] = [None] * p
    graphs = inst.get("graphs")
    if not isinstance(graphs, list) or len(graphs) != p:
        raise ValueError("malformed graph family")
    for color, edges in enumerate(graphs):
        if not isinstance(edges, list):
            raise ValueError("malformed graph edge list")
        row: set[int] = set()
        for edge in edges:
            if not isinstance(edge, int) or not 0 <= edge < p:
                raise ValueError("cycle-edge index outside range")
            row.add(edge)
        if len(row) != len(edges):
            raise ValueError("duplicate edge within a graph")
        rows[color] = row
    return [row for row in rows if row is not None]


def _answer_from_affine(p: int, slope: int, offset: int) -> list[int]:
    inverse = _inverse_mod(slope, p)
    first = (-offset * inverse) % p
    answer = []
    color = first
    for _ in range(p):
        answer.append(color)
        color = (color + inverse) % p
    return answer


def _short_affine_candidates(rows, checked_rows: int = 6) -> set[tuple[int, int]]:
    """Affine lines consistent with the first few rows of an incidence table."""
    p = len(rows)
    stop = min(p, checked_rows)
    candidates: set[tuple[int, int]] = set()
    for offset in rows[0]:
        for second in rows[1]:
            slope = (second - offset) % p
            if slope == 0:
                continue
            predicted = second
            good = True
            for color in range(2, stop):
                predicted = (predicted + slope) % p
                if predicted not in rows[color]:
                    good = False
                    break
            if good:
                candidates.add((slope, offset))
    return candidates


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a fixed-cycle Hamilton transversal instance.

    ``n`` is rounded up to an odd prime ``p``.  The certificate is chosen
    before any decoys, row order, edge order, or vertex labels are sampled.
    """
    rng = random.Random(seed)
    p = _next_prime(int(n))
    width = int(params.get("width", 4))
    if not 1 <= width <= min(8, p - 1):
        raise ValueError("width must lie between 1 and min(8, p-1)")

    slope = _choose_slope(p, rng)
    offset = rng.randrange(p)
    answer = _answer_from_affine(p, slope, offset)

    # The first six rows determine the hidden affine line uniquely.  This is a
    # construction-side rejection condition around an answer already known,
    # not a search for a certificate.  It makes the claimed compact route
    # executable and measurable rather than merely heuristic.
    for _construction_attempt in range(10_000):
        graphs = []
        for color in range(p):
            planted = (slope * color + offset) % p
            row = {planted}
            while len(row) < width:
                row.add(rng.randrange(p))
            displayed = list(row)
            rng.shuffle(displayed)
            graphs.append(displayed)
        if p < 6 or _short_affine_candidates(graphs) == {(slope, offset)}:
            # p=127 is the only post-hard rung offered by escalate().  Keep the
            # complete compact route inside G9's arithmetic cap for every seed,
            # rather than relying on the single seed used by selftest().
            if p <= 127 and p >= 6:
                _, compact_operations = _compact_affine_route(
                    {"p": p, "graphs": graphs}
                )
                if compact_operations > 300:
                    continue
            break
    else:
        raise RuntimeError("could not obtain a uniquely exposed affine plant")

    cycle = list(range(p))
    rng.shuffle(cycle)
    display_order = list(range(p))
    rng.shuffle(display_order)

    return {
        "paper": "arXiv:2309.12607",
        "requested_n": int(n),
        "p": p,
        "width": width,
        "vertices": list(range(p)),
        "cycle": cycle,
        "graphs": graphs,
        "display_order": display_order,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete, self-contained graph-transversal problem."""
    p = int(inst["p"])
    width = int(inst["width"])
    cycle = inst["cycle"]
    lines = [
        "Fixed-cycle Hamilton transversal problem",
        "",
        f"There are p={p} vertices and p={p} graph colors, numbered 0 through {p-1}.",
        "All graph edges are undirected; repeated vertices and repeated colors are forbidden.",
        "The base graph for every color is the complete graph K_p (so every base graph is Dirac).",
        "Each displayed F_c is a sparse subgraph of that base graph and contains only edges of H.",
        "",
        "The fixed Hamilton cycle H has this cyclic vertex order:",
        "  " + " ".join(str(v) for v in cycle),
        "The last listed vertex is adjacent back to the first.",
        f"For 0 <= t < {p}, edge e_t joins cycle entries t and (t+1) mod {p}; indices are 0-based.",
        "",
        "For each graph color c, the following row gives exactly the indices t for which e_t belongs to F_c.",
        f"Every row has {width} distinct indices. F_c contains no other edges.",
    ]
    for color in inst["display_order"]:
        items = " ".join(str(t) for t in inst["graphs"][color])
        lines.append(f"  F_{color}: {items}")
    lines.extend(
        [
            "",
            "Find a Hamilton F-transversal of the displayed fixed cycle H: assign every edge e_t",
            "one graph color, use every color exactly once, and require e_t to belong to its assigned F_c.",
            "",
            f"Give your final answer inside <answer></answer> tags as one JSON array of exactly {p} integers.",
            "Array entry t is the color assigned to e_t; the array must be a permutation of 0,...,p-1.",
            "Example format: <answer>[2,0,1]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Extract the JSON answer array from tagged model output."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        for fenced in _FENCE_RE.findall(text):
            matches.extend(_ANSWER_RE.findall(fenced))
    if not matches:
        return None
    body = matches[-1].strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        return None
    return value


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any valid edge-to-color bijection; never consult the plant."""
    p = int(inst["p"])
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) != p:
        return False, f"expected exactly {p} colors, got {len(answer)}"
    for position, color in enumerate(answer):
        if not isinstance(color, int) or isinstance(color, bool):
            return False, f"color at position {position} is not an integer"
        if not 0 <= color < p:
            return False, f"color at position {position} is outside 0..{p-1}"
    if len(set(answer)) != p:
        return False, "colors do not form a bijection: a color is repeated or missing"
    graphs = inst.get("graphs")
    if not isinstance(graphs, list) or len(graphs) != p:
        return False, "malformed instance: malformed graph family"
    for edge_index, color in enumerate(answer):
        row = graphs[color]
        if not isinstance(row, list):
            return False, "malformed instance: malformed graph edge list"
        if edge_index not in row:
            return False, f"edge e_{edge_index} is not present in F_{color}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-implied permutation language."""
    candidate = list(range(int(inst["p"])))
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """The exact number p! of structurally admissible color permutations."""
    return math.factorial(int(inst["p"]))


def enumerate_all(inst: dict) -> int | None:
    """Count valid witnesses exactly when p! is safely small."""
    p = int(inst["p"])
    if math.factorial(p) > 100_000:
        return None
    count = 0
    for candidate in itertools.permutations(range(p)):
        count += int(verify(inst, list(candidate))[0])
    return count


def _canonical_rows(inst: dict) -> tuple[tuple[int, ...], ...]:
    rows = _edge_positions(inst)
    return tuple(sorted(tuple(sorted(row)) for row in rows))


def canonical_key(inst: dict) -> str:
    """Canonicalize colors, input order, vertex names, and cycle dihedral action."""
    p = int(inst["p"])
    rows = _edge_positions(inst)
    candidates = []
    for shift in range(p):
        rotated = tuple(
            sorted(tuple(sorted((edge + shift) % p for edge in row)) for row in rows)
        )
        reflected = tuple(
            sorted(tuple(sorted((shift - edge - 1) % p for edge in row)) for row in rows)
        )
        candidates.append(rotated)
        candidates.append(reflected)
    canonical = min(candidates)
    blob = json.dumps([p, canonical], separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase crowding first, then the prime ground set, without a longer route."""
    n = int(params.get("n", 79))
    width = int(params.get("width", 4))
    harder = dict(params)
    if width < 8:
        harder["width"] = min(8, width + 2)
        harder["n"] = n
        return harder
    p = _next_prime(n)
    if p < 127:
        harder["n"] = _next_prime(p + 10)
        harder["width"] = width
        return harder
    # Further crowding makes the affine scan exceed 300 operations, and a
    # larger cycle length makes both that route and the witness longer.  The
    # no-tool effort cap, rather than the answer-character cap, is binding.
    return None


def _eligible_by_edge(rows: list[set[int]]) -> list[list[int]]:
    p = len(rows)
    eligible = [[] for _ in range(p)]
    for color, row in enumerate(rows):
        for edge in row:
            eligible[edge].append(color)
    for choices in eligible:
        choices.sort()
    return eligible


def _greedy_fixed(
    rows: list[set[int]],
    *,
    rng: random.Random | None = None,
    outlier_scores: list[int] | None = None,
) -> list[int] | None:
    eligible = _eligible_by_edge(rows)
    used: set[int] = set()
    answer = [-1] * len(rows)
    for edge in range(len(rows)):
        choices = [color for color in eligible[edge] if color not in used]
        if not choices:
            return None
        if rng is not None:
            color = rng.choice(choices)
        elif outlier_scores is not None:
            color = min(choices, key=lambda c: (outlier_scores[c], c))
        else:
            color = min(choices)
        answer[edge] = color
        used.add(color)
    return answer


def _outlier_candidate(rows: list[set[int]]) -> list[int] | None:
    degrees = [0] * len(rows)
    for row in rows:
        for edge in row:
            degrees[edge] += 1
    scores = [sum(degrees[edge] for edge in row) for row in rows]
    return _greedy_fixed(rows, outlier_scores=scores)


def _shift_reversal_attack(inst: dict) -> list[int] | None:
    p = int(inst["p"])
    rows = _edge_positions(inst)
    for step in (1, p - 1):
        for first in range(p):
            candidate = [(first + step * edge) % p for edge in range(p)]
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _hopcroft_karp(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Domain-standard exact bipartite matching with operation counters."""
    rows = _edge_positions(inst)
    adjacency = _eligible_by_edge(rows)
    p = len(rows)
    pair_left = [-1] * p
    pair_right = [-1] * p
    distance = [0] * p
    counters = {"edge_scans": 0, "bfs_rounds": 0, "augmentations": 0}

    def bfs() -> bool:
        counters["bfs_rounds"] += 1
        queue = []
        for left in range(p):
            if pair_left[left] < 0:
                distance[left] = 0
                queue.append(left)
            else:
                distance[left] = -1
        found = False
        head = 0
        while head < len(queue):
            left = queue[head]
            head += 1
            for right in adjacency[left]:
                counters["edge_scans"] += 1
                other = pair_right[right]
                if other < 0:
                    found = True
                elif distance[other] < 0:
                    distance[other] = distance[left] + 1
                    queue.append(other)
        return found

    def dfs(left: int) -> bool:
        for right in adjacency[left]:
            counters["edge_scans"] += 1
            other = pair_right[right]
            if other < 0 or (
                distance[other] == distance[left] + 1 and dfs(other)
            ):
                pair_left[left] = right
                pair_right[right] = left
                return True
        distance[left] = -1
        return False

    matching = 0
    while bfs():
        for left in range(p):
            if pair_left[left] < 0 and dfs(left):
                matching += 1
                counters["augmentations"] += 1
    if matching != p:
        return None, counters
    return pair_left, counters


def _compact_affine_route(inst: dict) -> tuple[list[int] | None, int]:
    """Execute and count the intended short change-of-variables route.

    Arithmetic accounting includes every modular subtraction/addition used to
    identify a line from the first six rows, Euclid divisions, and the additive
    recurrence that emits the full permutation.  Hash/set membership and the
    final checker are not arithmetic operations.
    """
    rows = _edge_positions(inst)
    p = len(rows)
    survivors: set[tuple[int, int]] = set()
    operations = 0
    for offset in rows[0]:
        for second in rows[1]:
            slope = (second - offset) % p
            operations += 1
            if slope == 0:
                continue
            predicted = second
            good = True
            for color in range(2, min(p, 6)):
                predicted = (predicted + slope) % p
                operations += 1
                if predicted not in rows[color]:
                    good = False
                    break
            if good:
                survivors.add((slope, offset))
    if len(survivors) != 1:
        return None, operations
    slope, offset = next(iter(survivors))

    # Instrument extended Euclid instead of hiding its cost in pow(..., -1, p).
    old_r, r = slope, p
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        operations += 1
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        operations += 4
    inverse = old_s % p
    operations += 1
    color = (-offset * inverse) % p
    operations += 2
    answer = []
    for _ in range(p):
        answer.append(color)
        color = (color + inverse) % p
        operations += 1
    return answer, operations


def _relabeled_instance(
    inst: dict,
    vertex_map: list[int] | None = None,
    color_map: list[int] | None = None,
    edge_map=None,
) -> dict:
    """Carry the public instance and witness through genuine relabellings."""
    p = int(inst["p"])
    if vertex_map is None:
        vertex_map = list(range(p))
    if color_map is None:
        color_map = list(range(p))
    if edge_map is None:
        edge_map = lambda edge: edge
    transformed_graphs: list[list[int] | None] = [None] * p
    for old_color, row in enumerate(inst["graphs"]):
        transformed_graphs[color_map[old_color]] = [edge_map(edge) for edge in row]
    new_display_order = [color_map[c] for c in reversed(inst["display_order"])]
    answer = [-1] * p
    for old_edge, old_color in enumerate(inst["answer"]):
        answer[edge_map(old_edge)] = color_map[old_color]
    return {
        "paper": inst["paper"],
        "requested_n": inst["requested_n"],
        "p": p,
        "width": inst["width"],
        "vertices": sorted(vertex_map),
        "cycle": [vertex_map[v] for v in inst["cycle"]],
        "graphs": [row for row in transformed_graphs if row is not None],
        "display_order": new_display_order,
        "answer": answer,
    }


def _answer_size(answer) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))

    def atoms(value) -> int:
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(item) for item in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "arXiv:2309.12607",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    planted_ok = 0
    json_ok = 0
    failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            planted_ok += int(ok)
            json_ok += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
    report["G1_planted_verifies"] = {
        "pass": planted_ok == 12 and json_ok == 12,
        "verified": planted_ok,
        "attempts": 12,
        "json_native": json_ok,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    answer = list(inst["answer"])
    swapped = None
    for first in range(len(answer)):
        for second in range(first + 1, len(answer)):
            trial = list(answer)
            trial[first], trial[second] = trial[second], trial[first]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("could not create a rejected swap")
    duplicate = list(answer)
    duplicate[1] = duplicate[0]
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate_color": duplicate,
        "out_of_range": [inst["p"]] + answer[1:],
        "swap_two": swapped,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The bijection is below.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nEach entry uses the stated zero-based edge index."
    )
    parsed = parse_answer(response)
    malformed_returns_none = all(
        parse_answer(sample) is None
        for sample in ("", "no tagged answer", "<answer>not JSON</answer>", "<answer>{}</answer>")
    )
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0] and malformed_returns_none,
        "parsed_equals_answer": parsed == answer,
        "malformed_returns_none": malformed_returns_none,
    }

    guess_rng = random.Random(0x230912607)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_prior": "uniform over all p! color permutations",
        "candidate_space": search_space(inst),
        "candidate_space_bits": int(search_space(inst)).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_edge_frequency_greedy",
        "greedy_first_fit",
        "random_restart_256_fixed_order",
        "shift_or_reversal_ansatz",
    ]
    successes = {name: 0 for name in attack_names}
    seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_scans = 0
    reference_rounds = 0
    reference_augmentations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping_params)
        rows = _edge_positions(trial)

        start = time.perf_counter()
        candidate = _outlier_candidate(rows)
        successes[attack_names[0]] += int(
            candidate is not None and verify(trial, candidate)[0]
        )
        seconds[attack_names[0]] += time.perf_counter() - start

        start = time.perf_counter()
        candidate = _greedy_fixed(rows)
        successes[attack_names[1]] += int(
            candidate is not None and verify(trial, candidate)[0]
        )
        seconds[attack_names[1]] += time.perf_counter() - start

        start = time.perf_counter()
        random_won = False
        for restart in range(256):
            candidate = _greedy_fixed(
                rows, rng=random.Random((seed + 1) * 1_000_003 + restart)
            )
            if candidate is not None and verify(trial, candidate)[0]:
                random_won = True
                break
        successes[attack_names[2]] += int(random_won)
        seconds[attack_names[2]] += time.perf_counter() - start

        start = time.perf_counter()
        candidate = _shift_reversal_attack(trial)
        successes[attack_names[3]] += int(
            candidate is not None and verify(trial, candidate)[0]
        )
        seconds[attack_names[3]] += time.perf_counter() - start

        start = time.perf_counter()
        reference, counts = _hopcroft_karp(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(
            reference is not None and verify(trial, reference)[0]
        )
        reference_scans += counts["edge_scans"]
        reference_rounds += counts["bfs_rounds"]
        reference_augmentations += counts["augmentations"]

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(seconds[name], 6),
        }
        for name in attack_names
    }
    reference_algorithm = {
        "name": "Hopcroft--Karp maximum bipartite matching",
        "complexity": "O(E sqrt(V))",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_scans // 8,
        "bfs_rounds": reference_rounds // 8,
        "augmentations": reference_augmentations // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    count_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    count_seconds = time.perf_counter() - count_start
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and isinstance(demo_count, int)
        and demo_count > 0
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_count_wall_clock_sec": round(count_seconds, 6),
        "baseline_name": reference_algorithm["name"],
        "baseline_wall_clock_sec": reference_algorithm["wall_clock_sec"],
        "baseline_edge_scans": reference_algorithm["operations"],
        "baseline_bfs_rounds": reference_algorithm["bfs_rounds"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled_start = time.perf_counter()
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_seconds = time.perf_counter() - doubled_start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_sizes = [_next_prime(item["n"]) for item in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["p"] >= 2 * inst["p"]
        and search_space(doubled) > search_space(inst)
        and ladder_sizes == sorted(ladder_sizes)
        and len(set(ladder_sizes)) == 4,
        "shipping_p": inst["p"],
        "doubled_requested_n": doubled_params["n"],
        "doubled_p": doubled["p"],
        "doubled_build_wall_clock_sec": round(doubled_seconds, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    real_transform_checks = 0
    invariant_failures = []
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        rng = random.Random(70_000 + seed)
        vertex_map = list(range(original["p"]))
        color_map = list(range(original["p"]))
        rng.shuffle(vertex_map)
        rng.shuffle(color_map)
        rotation = rng.randrange(original["p"])
        reordered = dict(original)
        reordered["graphs"] = [list(reversed(row)) for row in original["graphs"]]
        reordered["display_order"] = list(reversed(original["display_order"]))
        reordered["answer"] = list(original["answer"])
        transforms = [
            reordered,
            _relabeled_instance(original, vertex_map=vertex_map),
            _relabeled_instance(original, color_map=color_map),
            _relabeled_instance(
                original,
                edge_map=lambda edge, r=rotation, p=original["p"]: (edge + r) % p,
            ),
            _relabeled_instance(
                original,
                vertex_map=vertex_map,
                color_map=color_map,
                edge_map=lambda edge, r=rotation, p=original["p"]: (r - edge - 1) % p,
            ),
        ]
        for transformed in transforms:
            same = canonical_key(transformed) == key
            valid = verify(transformed, transformed["answer"])[0]
            invariant_checks += int(same)
            real_transform_checks += int(valid)
            if not same or not valid:
                invariant_failures.append(
                    {"seed": seed, "same_key": same, "carried_answer_valid": valid}
                )
    unrelated_keys = {
        canonical_key(make_instance(seed=90_000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 100
        and real_transform_checks == 100
        and len(unrelated_keys) == 20,
        "invariance_passed": invariant_checks,
        "invariance_attempts": 100,
        "real_transform_passed": real_transform_checks,
        "real_transform_attempts": 100,
        "distinct_unrelated": len(unrelated_keys),
        "distinct_attempts": 20,
        "transformations": [
            "row-edge and displayed-row input reordering",
            "arbitrary vertex relabeling",
            "arbitrary color relabeling and row reordering",
            "cycle rotation",
            "composed vertex/color relabeling with cycle reflection",
        ],
        "failures": invariant_failures,
    }

    answer_chars, answer_tokens, answer_elements = _answer_size(inst["answer"])
    compact_answer, intended_operations = _compact_affine_route(inst)
    compact_ok = compact_answer is not None and verify(inst, compact_answer)[0]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verified": compact_ok,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_passed"] = all(bool(value["pass"]) for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
