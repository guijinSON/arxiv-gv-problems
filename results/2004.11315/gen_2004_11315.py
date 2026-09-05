"""Verified twin-reduction witnesses from arXiv:2004.11315.

The paper defines twins as vertices with equal open neighborhoods and proves
that a twin pair can be consecutive in a minimum-fill ordering. This module
inverse-generates a 4-regular bipartite graph containing a known twin triple.
A distinguished left vertex begins a short, locally checkable codegree chain
that leads to the triple; the stored answer is chosen before the rest of the
regular incidence graph is completed.

The family is Track B. General twin detection by normalizing and comparing all
neighborhood rows is polynomial-time and is measured as the reference
algorithm. The intended no-tool route instead follows the local codegree-2
chain in fewer than 300 exact operations at every named non-demo preset.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "rooted labelled 4-regular bipartite graph",
        "open-neighborhood incidence rows",
        "three-vertex twin block",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact equality of finite open-neighborhood sets",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Follow the unique local codegree-2 continuation from the marked left "
        "vertex until three continuations share one neighborhood; without this "
        "structure one normalizes and compares every incidence row."
    ),
    "hardness_basis": (
        "Track B: Section 4's Twin Reduction implementation hashes, sorts, and "
        "compares neighborhoods in O(mn+n log n) worst-case time; on the shipping "
        "n=1600 preset the fixed-row reference sorter used at most 31,979 counted "
        "operations per instance (250,141 across eight, 0.028647 s measured), "
        "while the rooted codegree chain uses 236 exact incidence/count comparisons; "
        "the candidate preset was nevertheless solved by 3/3 live bare oracle calls, "
        "so Track-B hardness has not yet been established."
    ),
    "max_answer_tokens": 5,
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
    "demo": {"n": 16, "path_length": 2},
    "easy": {"n": 240, "path_length": 8},
    "medium": {"n": 700, "path_length": 8},
    "hard": {"n": 1600, "path_length": 8},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The marked left vertex lies on a chain whose consecutive left vertices "
    "have exactly two common right neighbors."
)
PLACEBO_HINT = (
    "The left and right labels occupy separate parts even when their printed "
    "integers happen to be equal."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly three distinct zero-based "
        "left-vertex labels in the range 0 through n-1."
    ),
    "bounds": {
        "length": 3,
        "strictly_increasing": True,
        "entry_range": "0 <= entry < n",
        "candidate_count": "binomial(n,3)",
    },
}

# Filled only from script-owned harden.py transcripts. API errors do not count
# as attempts and must leave this object unchanged.
G9_ORACLE_RESULTS = {
    # The current bare run reached the named shipping preset before the quota
    # failed on a later escalation; all three shipping-preset calls solved it.
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper definition and certificate. Section 2 defines the open neighborhood
Gamma(v). The Twin Reduction subsection of Section 4 defines twins by
Gamma(a)=Gamma(b); Theorem 4 proves that a twin pair can occur consecutively in
a minimum-fill ordering, and the following exact reduction contracts one twin
and later expands the ordering. The solver is handed the same undirected graph
object, as a bipartite incidence list. No surrogate reduction is used.

Step 0 and track. Track A would be false. Section 4 explicitly describes twin
detection by open-neighborhood hashing, sorting, and exact comparison and states
O(mn+n log n) worst-case time. This module therefore declares Track B and
measures a successful canonical-row sorter separately from the failing attacks.
Unlike an earlier global-row-scan draft, this construction has a real compact
route: from the marked left vertex, count co-occurrences only across its four
right neighbors. A unique unvisited label occurs twice at each chain step; at
the endpoint three labels occur twice and have equal full rows.

Inverse construction. The chain vertices and the final three twin vertices are
chosen first. Two right vertices are placed on every chain link. At the terminal
chain vertex, two right vertices also meet all three twins; two more right
vertices meet the same twins. Every partial right incidence is padded with
decoys, with pair reuse forbidden around special vertices. Remaining decoy
stubs are randomly partitioned into four-element right incidences. Thus all
left and right degrees are exactly four. Independent permutations relabel both
sides and row order, carrying the planted certificate and marked start.
Generation never invokes twin detection or the compact chain follower.

Easy regimes and attacks. Section 3 records a linear-time algorithm for perfect
elimination on chordal graphs, and Section 4 gives the polynomial twin detector
used as the reference algorithm. Equal degree on both sides defeats degree
outliers. Independent relabelling defeats position and label magnitude. The
panel also tests neighbor-sum greediness, a one-step use of the marked root
without chain propagation, a fixed affine-label ansatz, and random legal
triples. The domain reference algorithm is intentionally successful.

External hardening. A refreshed bare run solved every call through n=2400 and
two of three calls at n=3600, so each completed level was defeated. The API
quota failed on every redraw at n=5400 before the harness could produce a
verdict. These facts are recorded in README.md and BLOCKED.md; they are not
converted into a false model failure or a hardness claim.

Canonicalization. Independent left and right relabellings, input-row and
within-row reorderings, and their compositions preserve the rooted problem.
The key uses root-individualized bipartition-aware Weisfeiler-Lehman refinement
and an edge-color multiset. It is a strong polynomial invariant, not a complete
canonical form for bipartite graph isomorphism; README records that caveat.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_LEFT_DEGREE = 4
_RIGHT_DEGREE = 4
_LINK_CODEGREE = 2


def _validate_parameters(n: int, path_length: int) -> tuple[int, int]:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if isinstance(path_length, bool) or not isinstance(path_length, int):
        raise ValueError("path_length must be an integer")
    if path_length < 1:
        raise ValueError("path_length must be at least 1")
    if n < 2 * path_length + 6:
        raise ValueError("n must be at least 2*path_length+6")
    return n, path_length


def _add_padded_right(
    rights: list[list[int]],
    base: list[int],
    decoys: list[int],
    remaining: dict[int, int],
    forbidden_with_special: dict[int, set[int]],
    rng: random.Random,
) -> bool:
    """Append one four-vertex right incidence, padding with safe decoys."""

    chosen: list[int] = []
    for _ in range(_RIGHT_DEGREE - len(base)):
        candidates = []
        for decoy in decoys:
            if remaining[decoy] <= 0 or decoy in chosen or decoy in base:
                continue
            if any(decoy in forbidden_with_special.get(special, set())
                   for special in base):
                continue
            candidates.append(decoy)
        if not candidates:
            return False
        best_capacity = max(remaining[decoy] for decoy in candidates)
        best = [decoy for decoy in candidates
                if remaining[decoy] == best_capacity]
        decoy = rng.choice(best)
        chosen.append(decoy)
        remaining[decoy] -= 1
        for special in base:
            forbidden_with_special.setdefault(special, set()).add(decoy)
    rights.append(list(base) + chosen)
    return True


def _construct_incidence(
    n: int, path_length: int, rng: random.Random
) -> tuple[list[list[int]], list[list[int]], list[int]]:
    """Construct the planted regular incidence graph without finding twins."""

    chain = list(range(path_length + 1))
    twins = list(range(path_length + 1, path_length + 4))
    decoys = list(range(path_length + 4, n))
    for _attempt in range(400):
        rights: list[list[int]] = []
        remaining = {left: _LEFT_DEGREE for left in decoys}
        forbidden: dict[int, set[int]] = {}
        ok = True
        for _ in range(_LINK_CODEGREE):
            ok &= _add_padded_right(
                rights, [chain[0]], decoys, remaining, forbidden, rng
            )
        for index in range(path_length):
            for _ in range(_LINK_CODEGREE):
                ok &= _add_padded_right(
                    rights,
                    [chain[index], chain[index + 1]],
                    decoys,
                    remaining,
                    forbidden,
                    rng,
                )
        terminal = [chain[-1]] + twins
        for _ in range(_LINK_CODEGREE):
            rights.append(list(terminal))
        for _ in range(_LINK_CODEGREE):
            ok &= _add_padded_right(
                rights, list(twins), decoys, remaining, forbidden, rng
            )
        if not ok:
            continue

        stubs = [left for left in decoys for _ in range(remaining[left])]
        if len(stubs) % _RIGHT_DEGREE:
            raise AssertionError("remaining incidence stubs are not divisible by four")
        completion = None
        for _shuffle in range(8_000):
            rng.shuffle(stubs)
            groups = [stubs[i:i + _RIGHT_DEGREE]
                      for i in range(0, len(stubs), _RIGHT_DEGREE)]
            if all(len(set(group)) == _RIGHT_DEGREE for group in groups):
                completion = [list(group) for group in groups]
                break
        if completion is None:
            continue
        rights.extend(completion)

        if len(rights) != n or any(len(set(group)) != _RIGHT_DEGREE
                                   for group in rights):
            continue
        left_rows = [[] for _ in range(n)]
        for right, incident in enumerate(rights):
            for left in incident:
                left_rows[left].append(right)
        if any(len(row) != _LEFT_DEGREE for row in left_rows):
            continue
        counts = Counter(tuple(sorted(row)) for row in left_rows)
        twin_row = tuple(sorted(left_rows[twins[0]]))
        if counts[twin_row] != 3 or max(counts.values()) != 3:
            continue
        if any(left_rows[twin] != left_rows[twins[0]] for twin in twins[1:]):
            continue
        # Validate against the already chosen chain and twins. This never asks a
        # detector to discover which labels form the certificate.
        if _validate_planted_route(left_rows, rights, chain, twins):
            return left_rows, rights, twins
    raise RuntimeError("could not complete a regular incidence graph")


def make_instance(n: int, seed: int = 0, path_length: int = 8, **params) -> dict:
    """Inverse-generate a rooted regular bipartite graph with known twins."""

    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n, path_length = _validate_parameters(n, path_length)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    left_rows, rights, twins = _construct_incidence(n, path_length, rng)

    left_map = list(range(n))
    right_map = list(range(n))
    rng.shuffle(left_map)
    rng.shuffle(right_map)
    displayed_rows = []
    indexed_rows: list[list[int] | None] = [None] * n
    for old_left, old_row in enumerate(left_rows):
        neighbors = [right_map[right] for right in old_row]
        rng.shuffle(neighbors)
        new_left = left_map[old_left]
        displayed_rows.append({"left": new_left, "neighbors": neighbors})
        indexed_rows[new_left] = sorted(neighbors)
    rng.shuffle(displayed_rows)
    right_incidence: list[list[int] | None] = [None] * n
    for old_right, incident in enumerate(rights):
        labels = [left_map[left] for left in incident]
        rng.shuffle(labels)
        right_incidence[right_map[old_right]] = labels
    return {
        "paper": "arXiv:2004.11315",
        "family": "rooted codegree chain ending in a twin triple",
        "n": n,
        "left_degree": _LEFT_DEGREE,
        "right_degree": _RIGHT_DEGREE,
        "link_codegree": _LINK_CODEGREE,
        "path_length": path_length,
        "start": left_map[0],
        "rows": displayed_rows,
        "neighborhoods": indexed_rows,
        "right_incidence": right_incidence,
        "answer": sorted(left_map[left] for left in twins),
    }


def render(inst: dict) -> str:
    """Render a self-contained graph problem and exact output contract."""

    n = inst["n"]
    lines = [
        "Find a three-vertex twin block in this rooted undirected bipartite graph.",
        "",
        "Definitions and conventions:",
        f"The left vertices are L0,...,L{n - 1}; the right vertices are R0,...,R{n - 1}.",
        "Left and right labels are separate even when their integers are equal.",
        "Every edge has one left and one right endpoint, and no other edges exist.",
        "Every left vertex and every right vertex has degree exactly 4.",
        "The open neighborhood N(v) is the set of vertices joined to v; v itself is excluded.",
        "Distinct vertices are twins when their open neighborhoods are exactly equal as sets.",
        "Find exactly three distinct LEFT vertices that are pairwise twins.",
        "Output zero-based integer labels in strictly increasing order; repeats are forbidden.",
        "Row order and the order of labels within any row carry no meaning.",
        f"One distinguished left vertex is S = L{inst['start']}.",
        "",
        "Left adjacency rows (`Li: ...` lists the four right neighbors of Li):",
    ]
    for row in inst["rows"]:
        lines.append(
            "L{}: {}".format(row["left"], " ".join(map(str, row["neighbors"])))
        )
    lines.extend([
        "",
        "Right incidence index, in increasing right-label order (`Ri: ...` lists its four left neighbors):",
    ])
    for right, incident in enumerate(inst["right_incidence"]):
        lines.append("R{}: {}".format(right, " ".join(map(str, incident))))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as exactly three comma-separated left-vertex integer labels.",
        "Example of the required syntax: <answer>1, 5, 9</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract one tagged triple, tolerating prose, fences, and whitespace."""

    try:
        if not isinstance(text, str):
            return None
        matches = _ANSWER_RE.findall(text)
        if len(matches) != 1:
            return None
        body = matches[0].strip()
        body = re.sub(r"^```(?:text|json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not re.fullmatch(r"[+-]?\d+(?:\s*(?:,|\s)\s*[+-]?\d+){2}", body):
            return None
        pieces = [piece for piece in re.split(r"\s*,\s*|\s+", body) if piece]
        return [int(piece) for piece in pieces] if len(pieces) == 3 else None
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Accept any increasing left triple with equal displayed neighborhoods."""

    if not isinstance(answer, list):
        return False, "answer must be a list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 3:
        return False, "answer must contain exactly three labels"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every label must be an integer"
    if len(set(answer)) != 3:
        return False, "the three labels must be distinct"
    if answer != sorted(answer):
        return False, "labels must be in strictly increasing order"
    n = inst.get("n")
    if not isinstance(n, int) or any(value < 0 or value >= n for value in answer):
        return False, "a label is outside the left-vertex range"
    rows = inst.get("neighborhoods")
    if not isinstance(rows, list) or len(rows) != n:
        return False, "instance adjacency rows are malformed"
    selected = [rows[left] for left in answer]
    if any(not isinstance(row, list) or len(row) != _LEFT_DEGREE
           or any(isinstance(value, bool) or not isinstance(value, int)
                  or value < 0 or value >= n for value in row)
           or len(set(row)) != _LEFT_DEGREE for row in selected):
        return False, "instance adjacency rows are malformed"
    first = frozenset(selected[0])
    if any(frozenset(row) != first for row in selected[1:]):
        return False, "the three open neighborhoods are not equal"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from all legal increasing triples of left labels."""
    return sorted(rng.sample(range(inst["n"]), 3))


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], 3)


def enumerate_all(inst: dict) -> int | None:
    """Count valid twin triples exactly by grouping finite incidence rows."""
    try:
        counts = Counter(tuple(sorted(row)) for row in inst["neighborhoods"])
        return sum(math.comb(count, 3) for count in counts.values() if count >= 3)
    except (KeyError, TypeError):
        return None


def _validate_planted_route(
    left_rows: list[list[int]],
    right_rows: list[list[int]],
    chain: list[int],
    twins: list[int],
) -> bool:
    """Check the chosen route locally without discovering a certificate."""

    visited: set[int] = set()
    for index, current in enumerate(chain):
        counts: Counter[int] = Counter()
        for right in left_rows[current]:
            for left in right_rows[right]:
                if left != current and left not in visited:
                    counts[left] += 1
        actual = {left for left, count in counts.items()
                  if count == _LINK_CODEGREE}
        expected = ({chain[index + 1]}
                    if index + 1 < len(chain) else set(twins))
        if actual != expected:
            return False
        visited.add(current)
    return all(left_rows[twin] == left_rows[twins[0]] for twin in twins[1:])


def _trace_from_root(
    left_rows: list[list[int]], right_rows: list[list[int]], start: int
) -> tuple[list[int] | None, int]:
    """Compact structural route; return its candidate and operation count."""

    current = start
    visited: set[int] = set()
    operations = 0
    for _ in range(len(left_rows)):
        counts: Counter[int] = Counter()
        for right in left_rows[current]:
            for left in right_rows[right]:
                operations += 1
                if left != current and left not in visited:
                    counts[left] += 1
        matches = []
        for left, count in counts.items():
            operations += 1
            if count == _LINK_CODEGREE:
                matches.append(left)
        if len(matches) == 3:
            operations += 3
            candidate = sorted(matches)
            first = set(left_rows[candidate[0]])
            for left in candidate[1:]:
                operations += _LEFT_DEGREE
                if set(left_rows[left]) != first:
                    return None, operations
            return candidate, operations
        if len(matches) != 1:
            return None, operations
        visited.add(current)
        current = matches[0]
    return None, operations


def _compact_route(inst: dict) -> tuple[list[int] | None, int]:
    return _trace_from_root(
        [list(row) for row in inst["neighborhoods"]],
        [list(row) for row in inst["right_incidence"]],
        inst["start"],
    )


def _wl_payload(inst: dict) -> tuple | None:
    try:
        n = inst["n"]
        left_adj = [set(row) for row in inst["neighborhoods"]]
        if len(left_adj) != n or any(len(row) != _LEFT_DEGREE for row in left_adj):
            return None
        right_adj = [set() for _ in range(n)]
        for left, neighbors in enumerate(left_adj):
            for right in neighbors:
                if not 0 <= right < n:
                    return None
                right_adj[right].add(left)
        if any(len(row) != _RIGHT_DEGREE for row in right_adj):
            return None
        start = inst["start"]
        if not 0 <= start < n:
            return None
    except (KeyError, TypeError):
        return None

    left_colors = ["LR" if left == start else "L" for left in range(n)]
    right_colors = ["R"] * n
    for _ in range(12):
        new_left = [
            hashlib.sha256(repr(("L", left_colors[left],
                                 tuple(sorted(right_colors[right]
                                              for right in left_adj[left])))).encode()
                           ).hexdigest()
            for left in range(n)
        ]
        new_right = [
            hashlib.sha256(repr(("R", right_colors[right],
                                 tuple(sorted(left_colors[left]
                                              for left in right_adj[right])))).encode()
                           ).hexdigest()
            for right in range(n)
        ]
        left_colors, right_colors = new_left, new_right
    edge_colors = sorted(
        (left_colors[left], right_colors[right])
        for left in range(n) for right in left_adj[left]
    )
    return (
        n,
        tuple(sorted(left_colors)),
        tuple(sorted(right_colors)),
        tuple(edge_colors),
    )


def canonical_key(inst: dict) -> str:
    """Strong rooted bipartite-graph invariant under label permutations."""
    payload = _wl_payload(inst)
    if payload is None:
        return "malformed"
    return hashlib.sha256(repr(payload).encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the graph haystack and, while the route cap allows, its decoy chain."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    harder = dict(params)
    harder["n"] = max(params["n"] + 100, (params["n"] * 3) // 2)
    harder["path_length"] = min(10, int(params.get("path_length", 8)) + 1)
    return harder


def _reference_row_sort(inst: dict) -> tuple[list[int] | None, int]:
    """Successful domain-standard twin detection by canonical row sorting."""
    operations = 0
    normalized = []
    sort_factor = math.ceil(math.log2(_LEFT_DEGREE))
    for row in inst["rows"]:
        normalized.append((tuple(sorted(row["neighbors"])), row["left"]))
        operations += _LEFT_DEGREE * sort_factor
    normalized.sort()
    operations += len(normalized) * math.ceil(math.log2(max(2, len(normalized))))
    run: list[int] = []
    previous = None
    for neighbors, left in normalized:
        operations += 1
        if neighbors == previous:
            run.append(left)
            if len(run) == 3:
                return sorted(run), operations
        else:
            previous = neighbors
            run = [left]
    return None, operations


def _attack_first_rows(inst: dict) -> list[int]:
    return sorted(row["left"] for row in inst["rows"][:3])


def _attack_smallest_neighbor_sums(inst: dict) -> list[int]:
    rows = sorted(inst["rows"], key=lambda row: (sum(row["neighbors"]), row["left"]))
    return sorted(row["left"] for row in rows[:3])


def _attack_degree_outlier(inst: dict) -> list[int]:
    return sorted(range(inst["n"]),
                  key=lambda left: (len(inst["neighborhoods"][left]), left))[:3]


def _attack_one_step_from_root(inst: dict) -> list[int]:
    current = inst["start"]
    counts: Counter[int] = Counter()
    for right in inst["neighborhoods"][current]:
        for left in inst["right_incidence"][right]:
            if left != current:
                counts[left] += 1
    ordered = sorted(counts, key=lambda left: (-counts[left], left))
    return sorted(ordered[:3])


def _attack_affine_labels(inst: dict) -> list[int]:
    n = inst["n"]
    return [0, n // 2, n - 1]


def _attack_random_restarts(
    inst: dict, seed: int, trials: int = 2_048
) -> tuple[list[int], int]:
    rng = random.Random(seed)
    candidate = [0, 1, 2]
    for attempt in range(1, trials + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return candidate, trials


def _relabel_instance(
    inst: dict,
    left_permutation: list[int],
    right_permutation: list[int],
    shuffle_seed: int,
) -> dict:
    rng = random.Random(shuffle_seed)
    transformed = dict(inst)
    rows = []
    indexed: list[list[int] | None] = [None] * inst["n"]
    for row in inst["rows"]:
        neighbors = [right_permutation[right] for right in row["neighbors"]]
        rng.shuffle(neighbors)
        left = left_permutation[row["left"]]
        rows.append({"left": left, "neighbors": neighbors})
        indexed[left] = sorted(neighbors)
    rng.shuffle(rows)
    right_incidence: list[list[int] | None] = [None] * inst["n"]
    for right, incident in enumerate(inst["right_incidence"]):
        labels = [left_permutation[left] for left in incident]
        rng.shuffle(labels)
        right_incidence[right_permutation[right]] = labels
    transformed["rows"] = rows
    transformed["neighborhoods"] = indexed
    transformed["right_incidence"] = right_incidence
    transformed["start"] = left_permutation[inst["start"]]
    transformed["answer"] = sorted(left_permutation[left] for left in inst["answer"])
    return transformed


def _answer_elements(answer) -> int:
    if isinstance(answer, dict):
        return sum(_answer_elements(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_elements(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run all local correctness, density, attack, scale, and key gates."""
    report = {
        "paper": "2004.11315",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            compact, _ = _compact_route(inst)
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checked += 1
            if not ok or compact != inst["answer"] or not json_native:
                failures.append({
                    "preset": preset,
                    "seed": seed,
                    "reason": reason,
                    "compact_matches": compact == inst["answer"],
                })
    report["G1_planted_verifies"] = {
        "pass": not failures, "instances": checked, "failures": failures,
    }

    ship = make_instance(seed=200411315, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = ship["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[2], planted[1], planted[0]],
        "duplicate_one": [planted[0], planted[0], planted[2]],
        "empty": [],
        "out_of_range": [planted[0], planted[1], ship["n"]],
    }
    outcomes = {name: verify(ship, value) for name, value in corruptions.items()}
    reasons = {name: outcome[1] for name, outcome in outcomes.items()}
    report["G2_rejects_corruption"] = {
        "pass": (all(not outcome[0] for outcome in outcomes.values())
                 and len(set(reasons.values())) == len(corruptions)),
        "rejected": {name: not outcome[0] for name, outcome in outcomes.items()},
        "reasons": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    body = ", ".join(map(str, planted))
    response = (
        "The terminal rows agree.\n```text\n"
        f"<answer>\n{body}\n</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(40052026)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    exact_answers = enumerate_all(ship)
    exact_space = search_space(ship)
    exact_density = exact_answers / exact_space
    observed_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed_probability < 1e-6 and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed_probability,
        "exact_probability": exact_density,
        "structure_aware_search_space": exact_space,
        "candidate_prior": "uniform over all increasing triples of distinct left labels",
        "wall_clock_seconds": round(density_wall, 6),
    }

    attack_seeds = [6101, 6113, 6121, 6131, 6143, 6151, 6163, 6173]
    attack_instances = [
        make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for seed in attack_seeds
    ]
    attacks = {
        "outlier_equal_degree": {"successes": 0, "attempts": 0},
        "outlier_first_input_rows": {"successes": 0, "attempts": 0},
        "greedy_smallest_neighbor_sums": {"successes": 0, "attempts": 0},
        "in_context_one_step_from_root": {"successes": 0, "attempts": 0},
        "in_context_affine_label_ansatz": {"successes": 0, "attempts": 0},
        "random_restart_2048": {"successes": 0, "attempts": 0},
    }
    random_trials = 0
    attack_start = time.perf_counter()
    for seed, inst in zip(attack_seeds, attack_instances):
        random_answer, trials = _attack_random_restarts(inst, seed ^ 0x5A17)
        random_trials += trials
        candidates = {
            "outlier_equal_degree": _attack_degree_outlier(inst),
            "outlier_first_input_rows": _attack_first_rows(inst),
            "greedy_smallest_neighbor_sums": _attack_smallest_neighbor_sums(inst),
            "in_context_one_step_from_root": _attack_one_step_from_root(inst),
            "in_context_affine_label_ansatz": _attack_affine_labels(inst),
            "random_restart_2048": random_answer,
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
    attack_wall = time.perf_counter() - attack_start

    reference_successes = 0
    reference_operations = 0
    reference_max_operations = 0
    reference_start = time.perf_counter()
    for inst in attack_instances:
        candidate, operations = _reference_row_sort(inst)
        reference_operations += operations
        reference_max_operations = max(reference_max_operations, operations)
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
    reference_wall = time.perf_counter() - reference_start
    compact_successes = 0
    compact_max_operations = 0
    for inst in attack_instances:
        candidate, operations = _compact_route(inst)
        compact_max_operations = max(compact_max_operations, operations)
        compact_successes += int(candidate is not None and verify(inst, candidate)[0])
    all_attacks_failed = all(value["successes"] == 0 for value in attacks.values())
    reference_algorithm = {
        "name": "canonical sorting of all open-neighborhood incidence rows",
        "complexity": "O(nd log d+n log n) comparisons for fixed-length rows",
        "paper_algorithm": "Section 4 hash/sort/compare twin detection, O(mn+n log n) worst case",
        "wall_clock_sec": round(reference_wall, 6),
        "operations": reference_operations,
        "max_operations_one_instance": reference_max_operations,
        "solves": f"{reference_successes}/{len(attack_instances)}",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == len(attack_instances),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
        "compact_route": {
            "name": "rooted codegree-2 constraint propagation",
            "solves": f"{compact_successes}/{len(attack_instances)}",
            "max_operations_one_instance": compact_max_operations,
        },
    }
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_answers == 1 and exact_density < 1e-6 and all_attacks_failed,
        "shipping_exact_solution_count": exact_answers,
        "shipping_candidate_count": exact_space,
        "shipping_exact_valid_fraction": exact_density,
        "shipping_sample_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "density_wall_clock_seconds": round(density_wall, 6),
        "strongest_failing_attack": "random restart plus one-step root and magnitude probes",
        "baseline_wall_clock_seconds": round(attack_wall, 6),
        "baseline_candidate_trials": random_trials + 5 * len(attack_instances),
        "successful_reference_wall_clock_seconds": round(reference_wall, 6),
        "successful_reference_operations": reference_operations,
    }

    before = make_instance(seed=771, **DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    after = make_instance(seed=771, **doubled_params)
    report["G7_scales"] = {
        "pass": (
            verify(before, before["answer"])[0]
            and verify(after, after["answer"])[0]
            and after["n"] == 2 * before["n"]
            and search_space(after) > search_space(before)
            and len(after["answer"]) == len(before["answer"])
        ),
        "n_before": before["n"],
        "n_after_size_doubling": after["n"],
        "space_before": search_space(before),
        "space_after": search_space(after),
        "answer_elements_before": len(before["answer"]),
        "answer_elements_after": len(after["answer"]),
    }

    invariant_checks = 0
    invariant_passed = 0
    carried_checks = 0
    carried_passed = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=8000 + seed, **DIFFICULTY["easy"])
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(9000 + seed)
        left_one = list(range(inst["n"]))
        right_one = list(range(inst["n"]))
        left_two = list(range(inst["n"]))
        right_two = list(range(inst["n"]))
        rng.shuffle(left_one)
        rng.shuffle(right_one)
        rng.shuffle(left_two)
        rng.shuffle(right_two)
        once = _relabel_instance(inst, left_one, right_one, seed)
        twice = _relabel_instance(once, left_two, right_two, 100 + seed)
        for transformed in (once, twice):
            invariant_checks += 1
            invariant_passed += int(canonical_key(transformed) == base_key)
            carried_checks += 1
            carried_passed += int(verify(transformed, transformed["answer"])[0])
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (invariant_passed == invariant_checks
                 and carried_passed == carried_checks
                 and distinct_keys == 20),
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_passed,
        "carried_witness_checks": carried_checks,
        "carried_witness_passed": carried_passed,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries": [
            "arbitrary left-label permutation carrying the marked root",
            "arbitrary right-label permutation",
            "row and within-row reordering",
            "composition of all preceding transformations",
        ],
    }

    answer_chars = len(json.dumps(ship["answer"]))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_elements(ship["answer"])
    compact_answer, intended_operations = _compact_route(ship)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in arms)
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and compact_answer == ship["answer"]
    )
    report["G9_no_tool_suitability"] = {
        # The oracle arms are diagnostic as of 2026-09-05.  Only the answer-size
        # and intended-route caps in G9(c) gate this family.
        "pass": within_caps,
        "arms": arms,
        "diagnostic_evidence_complete": evidence_complete,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate if evidence_complete else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_recovers_answer": compact_answer == ship["answer"],
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
