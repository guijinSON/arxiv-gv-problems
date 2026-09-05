"""Self-contained verified generator for arXiv:1601.03676.

The paper defines r-Set Packing with an arbitrary, well-conditioned overlap
predicate and proves a bounded-search-tree FPT algorithm.  This module uses the
paper's alpha-Weight predicate (Lemma 7) directly.  Candidate sets are arranged
as a finite covering of a connected constraint graph: the zero-conflict pairs
over every constraint edge are perfect matchings with one common sheet label.

Generation is inverse.  The sheet labels and one certified sheet are sampled
before the set intersections that encode them are created.  The reference
algorithm never runs inside make_instance().
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
from collections import Counter, deque


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family needs only the stdlib
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The weight residue modulo q of each group's common positive anchor is a "
    "coordinate offset conserved by the zero-conflict matchings."
)
PLACEBO_HINT: str = (
    "The integer labels in each candidate set should be compared carefully to "
    "avoid indexing and transcription mistakes."
)

# Replaced with the independently measured harden.py arms after those runs.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "pending: all harden arms hit OpenRouter HTTP 403 key total limit"


PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bounded set system",
        "nonnegative integer element weights",
        "alpha-Weight overlap constraint",
        "set packing",
    ],
    "verification_operations": [
        "exact set intersection",
        "exact integer overlap-weight sum",
        "pairwise integer comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The common anchor's weight residue modulo q changes local option numbers into a "
        "global sheet coordinate; without recognizing that invariant, a solver "
        "must materialize and search the compatibility relation."
    ),
    "hardness_basis": (
        "Track B: Section 3.1, Theorems 1 and 2 give the BST-alpha FPT algorithm with "
        "running time O(r^(rk) k^((r+1)k) N^(cr)); the shipping reference instead "
        "uses an exact positive-element incidence index and component propagation in "
        "O(L + |E| q^2), measuring 27,616 exact operations and 0.0070 seconds "
        "at the hard preset k=n=32, q=8, r=51, degree=7, while the anchor-weight-residue sheet "
        "route uses 64 exact modular operations after the invariant is recognized."
    ),
    "max_answer_tokens": 54,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "q": 3, "degree": 2},
    "easy": {"n": 16, "q": 5, "degree": 3},
    "medium": {"n": 24, "q": 7, "degree": 5},
    "hard": {"n": 32, "q": 8, "degree": 7},
}

SHIPPING_DIFFICULTY: str = "hard"

MAX_N = 128
MAX_Q = 12

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly n pairs [group, option], containing every group "
        "0..n-1 exactly once and one option 0..q-1 for that group; pair order is "
        "irrelevant, with even 6 <= n <= 128 and 3 <= q <= 12.  The bounded "
        "language for an instance therefore contains q^n witnesses."
    ),
    "bounds": {
        "max_pairs": MAX_N,
        "max_atomic_elements": 2 * MAX_N,
        "max_group_id": MAX_N - 1,
        "max_option_id": MAX_Q - 1,
        "max_option_count": MAX_Q,
        "shipping_space": "8^32 = 2^96",
    },
}

NOTES: str = """
Definition source: Section 2, Definition 1 gives the exact three requirements
for a well-conditioned overlap predicate.  Section 4.1, Lemma 7 proves that
alpha-Weight is well-conditioned for nonnegative weights and an upper threshold.
This module uses threshold zero, a zero-weight element shared by every set, and
positive-weight conflict elements; overlap is present but only positive shared
weight creates a conflict.

The easy-result warning is the paper's main result: Section 3.1, Theorems 1
and 2 give a complete bounded-search-tree algorithm in
O(r^(rk) k^((r+1)k) N^(cr)).  Small k is therefore fixed-parameter tractable.
That rules out Track A.  Here k=n grows, and the honest Track-B reference
algorithm builds a positive-element incidence index, computes local compatibility
tables, and propagates one component.  Its measured cost is reported by selftest.

Generation samples a connected regular constraint graph and a uniformly random
cyclic offset for the q hidden sheet labels in every group.  The offset is the
residue modulo q of that group's common positive anchor weight.  It then creates one
shared positive-weight element for each forbidden option pair on an edge, a
group anchor that forbids choosing twice from one group, and a universal
zero-weight element.  Any common sheet gives a packing.  The shipped answer is
sheet zero, known before any set is assembled; make_instance never searches.

All candidates have exactly 2+degree*(q-1) elements.  Random anchor-weight
quotients and arbitrary element relabelling remove magnitude and position outliers.
Independent cyclic offsets defeat the equal-option ansatz.  The first two
displayed groups are nonadjacent but their option-zero candidates lie on
different sheets; connectedness makes the left-to-right no-backtracking prefix
impossible to complete.  Finally, q^n versus q valid sheets defeats random
restart.  The successful compatibility/component algorithm and the independently
executed anchor-weight-residue shortcut are reported separately because this is Track B.
""".strip()


def _validate_parameters(n: int, q: int, degree: int) -> None:
    if n < 6 or n > MAX_N or n % 2:
        raise ValueError(f"n must be an even integer in 6..{MAX_N}")
    if not 3 <= q <= MAX_Q:
        raise ValueError(f"q must lie in 3..{MAX_Q}")
    if not 2 <= degree <= n - 2:
        raise ValueError("degree must lie in 2..n-2 so the graph has a nonedge")
    if (n * degree) % 2:
        raise ValueError("n*degree must be even")


def _is_connected(n: int, edges: set[tuple[int, int]]) -> bool:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == n


def _regular_edges(n: int, degree: int, rng: random.Random) -> list[tuple[int, int]]:
    """Return a connected, seed-varying simple regular graph.

    A connected circulant is randomized by degree-preserving two-switches.  This
    samples distractor structure only; no packing certificate is searched for.
    """

    edges: set[tuple[int, int]] = set()

    def add(u: int, v: int) -> None:
        if u != v:
            edges.add(tuple(sorted((u, v))))

    for offset in range(1, degree // 2 + 1):
        for u in range(n):
            add(u, (u + offset) % n)
    if degree % 2:
        for u in range(n // 2):
            add(u, u + n // 2)
    if len(edges) != n * degree // 2 or not _is_connected(n, edges):
        raise RuntimeError("failed to initialize a connected regular graph")

    if degree == n - 1:
        return sorted(edges)

    target = 8 * n * max(1, degree - 1)
    successes = 0
    attempts = 0
    while successes < target and attempts < target * 80:
        attempts += 1
        e1, e2 = rng.sample(tuple(edges), 2)
        a, b = e1
        c, d = e2
        if len({a, b, c, d}) < 4:
            continue
        if rng.randrange(2):
            f1 = tuple(sorted((a, c)))
            f2 = tuple(sorted((b, d)))
        else:
            f1 = tuple(sorted((a, d)))
            f2 = tuple(sorted((b, c)))
        if f1 == f2 or f1 in edges or f2 in edges:
            continue
        edges.remove(e1)
        edges.remove(e2)
        edges.add(f1)
        edges.add(f2)
        if not _is_connected(n, edges):
            edges.remove(f1)
            edges.remove(f2)
            edges.add(e1)
            edges.add(e2)
            continue
        successes += 1
    if successes < target:
        raise RuntimeError("could not randomize the regular constraint graph")
    return sorted(edges)


def _display_nonedge_first(
    n: int, edges: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Relabel a nonedge as {0,1}, preserving the unlabelled base graph."""

    edge_set = set(edges)
    pair = next(
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if (i, j) not in edge_set
    )
    old_order = [pair[0], pair[1]] + [v for v in range(n) if v not in pair]
    new_of_old = {old: new for new, old in enumerate(old_order)}
    return sorted(
        tuple(sorted((new_of_old[i], new_of_old[j])))
        for i, j in edges
    )


def make_instance(n, seed=0, **params) -> dict:
    """Build a certified weighted-overlap set packing by inverse generation."""

    unknown = set(params).difference({"q", "degree"})
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    n = int(n)
    q = int(params.get("q", 8))
    degree = int(params.get("degree", 3))
    _validate_parameters(n, q, degree)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    edges = _display_nonedge_first(n, _regular_edges(n, degree, rng))

    # Observable option a in group i represents global sheet (a + shift_i) mod q.
    # The shifts are sampled before any set is assembled.  Groups 0 and 1 are a
    # displayed nonedge; give them distinct (but individually uniform) shifts so
    # the left-to-right option-zero greedy attack commits to inconsistent sheets.
    shifts = [rng.randrange(q) for _ in range(n)]
    while shifts[1] == shifts[0]:
        shifts[1] = rng.randrange(q)
    option_to_sheet = [
        [(a + shifts[i]) % q for a in range(q)]
        for i in range(n)
    ]

    universal = 0
    next_element = 1
    group_elements = list(range(next_element, next_element + n))
    next_element += n
    groups: list[list[list[int]]] = [
        [[universal, group_elements[i]] for _ in range(q)] for i in range(n)
    ]

    # An edge element is used by exactly the forbidden candidate pair that it
    # represents.  Allowed pairs share only the universal zero-weight element.
    for i, j in edges:
        for a in range(q):
            for b in range(q):
                if option_to_sheet[i][a] == option_to_sheet[j][b]:
                    continue
                token = next_element
                next_element += 1
                groups[i][a].append(token)
                groups[j][b].append(token)

    expected_size = 2 + degree * (q - 1)
    if any(len(s) != expected_size for group in groups for s in group):
        raise RuntimeError("candidate sets did not remain size-regular")

    # Element names remain arbitrary: apply a full random relabelling.  The
    # compact coordinate belongs instead to the paper's native weight data.
    # Each anchor weight has residue shift_i modulo q and a random positive
    # quotient, so it is positive without making one option in its group an
    # outlier (all q options share that same anchor).
    relabel = list(range(next_element))
    rng.shuffle(relabel)
    anchor_labels = [relabel[internal] for internal in group_elements]
    anchor_weights = [q * rng.randrange(2, 12 * n + 2) + shifts[i] for i in range(n)]
    groups = [
        [sorted(relabel[x] for x in candidate) for candidate in group]
        for group in groups
    ]
    zero_element = relabel[universal]

    answer = [
        [i, option_to_sheet[i].index(0)]
        for i in range(n)
    ]
    edge_matchings = []
    for i, j in edges:
        inverse_j = {sheet: b for b, sheet in enumerate(option_to_sheet[j])}
        edge_matchings.append(
            [i, j, [inverse_j[option_to_sheet[i][a]] for a in range(q)]]
        )
    return {
        "paper": "1601.03676",
        "problem": "r-Set Packing with alpha-Weight Overlap",
        "n": n,
        "q": q,
        "degree": degree,
        "r": expected_size,
        "overlap_threshold": 0,
        "zero_weight_element": zero_element,
        "universe_size": next_element,
        "group_anchors": anchor_labels,
        "group_anchor_weights": anchor_weights,
        "constraint_edges": [[i, j] for i, j in edges],
        # An exact, redundant consequence of the displayed set intersections.
        # It accelerates repeated rejection in density tests; acceptance is
        # still decided below by the native weighted intersections themselves.
        "edge_matchings": edge_matchings,
        "groups": groups,
        "answer": answer,
    }


def _candidate_set(inst: dict, group: int, option: int) -> frozenset[int]:
    return frozenset(inst["groups"][group][option])


def _alpha_conflict(inst: dict, left: frozenset[int], right: frozenset[int]) -> bool:
    zero = inst["zero_weight_element"]
    threshold = inst["overlap_threshold"]
    anchor_weights = dict(zip(inst["group_anchors"], inst["group_anchor_weights"]))
    shared_weight = sum(
        0 if x == zero else anchor_weights.get(x, 1)
        for x in left.intersection(right)
    )
    return shared_weight > threshold


def _derive_edge_matchings(inst: dict) -> list[list]:
    """Recompute the redundant rejection cache from the displayed native sets."""

    q = inst["q"]
    result = []
    for raw_i, raw_j in inst["constraint_edges"]:
        i, j = int(raw_i), int(raw_j)
        mapping = []
        for a in range(q):
            left = _candidate_set(inst, i, a)
            compatible = [
                b
                for b in range(q)
                if not _alpha_conflict(inst, left, _candidate_set(inst, j, b))
            ]
            if len(compatible) != 1:
                raise ValueError("constraint edge is not a perfect matching")
            mapping.append(compatible[0])
        result.append([i, j, mapping])
    return result


def _normalize_answer(inst: dict, answer) -> tuple[dict[int, int] | None, str]:
    n = inst["n"]
    q = inst["q"]
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    for pos, pair in enumerate(answer):
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or isinstance(pair[0], bool)
            or isinstance(pair[1], bool)
            or not isinstance(pair[0], int)
            or not isinstance(pair[1], int)
        ):
            return None, f"entry {pos} is not an integer [group, option] pair"
        if not 0 <= pair[0] < n or not 0 <= pair[1] < q:
            return None, f"entry {pos} has a group or option outside its stated range"
    groups = [pair[0] for pair in answer]
    duplicate = next((g for g, count in Counter(groups).items() if count > 1), None)
    if duplicate is not None:
        return None, f"group {duplicate} is selected more than once"
    if len(answer) != n:
        return None, f"expected exactly {n} group-option pairs, received {len(answer)}"
    chosen = {g: a for g, a in answer}
    if set(chosen) != set(range(n)):
        return None, "the answer does not select every group exactly once"
    return chosen, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Check any witness using only exact set intersections and instance weights."""

    chosen, reason = _normalize_answer(inst, answer)
    if chosen is None:
        return False, reason

    n = inst["n"]
    # The cache is used only for early rejection.  Anything surviving it is
    # accepted only after recomputing every displayed alpha-Weight intersection.
    for i, j, mapping in inst.get("edge_matchings", []):
        if mapping[chosen[i]] != chosen[j]:
            return False, (
                f"selected sets for groups {i} and {j} alpha-conflict: "
                "their shared positive weight exceeds 0"
            )

    selected = {i: _candidate_set(inst, i, chosen[i]) for i in range(n)}
    priority = {tuple(sorted(map(int, e))) for e in inst["constraint_edges"]}
    pairs = sorted(priority)
    pairs.extend(
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if (i, j) not in priority
    )
    for i, j in pairs:
        if _alpha_conflict(inst, selected[i], selected[j]):
            return False, (
                f"selected sets for groups {i} and {j} alpha-conflict: "
                "their shared positive weight exceeds 0"
            )
    return True, "ok"


def render(inst) -> str:
    n = inst["n"]
    q = inst["q"]
    lines = [
        "Weighted-overlap set packing",
        "",
        f"There are n={n} candidate groups, numbered 0 through {n-1}.",
        f"Every group has q={q} candidate sets, with options numbered 0 through {q-1}.",
        f"Every candidate is a set of exactly r={inst['r']} integer-labelled universe elements.",
        "The order of elements inside a displayed set has no meaning and elements do not repeat.",
        "",
        "Element weights are nonnegative integers.  The single element",
        f"  {inst['zero_weight_element']}",
        "has weight 0.  The common group anchors have the positive weights listed",
        "below; every other displayed universe element has weight 1.",
        "For two candidate sets A and B, their overlap weight is the sum of the",
        "weights of the elements in A intersection B.  They alpha-conflict exactly",
        "when this overlap weight is greater than the inclusive threshold 0.",
        "Thus sharing the weight-0 element is allowed, while sharing any positive-",
        "weight element is forbidden.  All comparisons and sums are exact integers.",
        "",
        f"Find exactly k={n} distinct candidate sets with no alpha-conflicting pair.",
        "You must choose exactly one option from every group.  (Candidates in the",
        "same group share a positive-weight group element, so no valid packing can",
        "take two of them.)  The listed constraint edges identify group pairs that",
        "may have an additional positive-weight overlap; all validity is still",
        "defined by the displayed sets and the alpha rule above.",
        "",
        "For reference, [anchor element, weight] is listed in group order 0..n-1",
        "(each anchor is also visible in every option of its group):",
        "  " + json.dumps(
            list(zip(inst["group_anchors"], inst["group_anchor_weights"])),
            separators=(",", ":"),
        ),
        "",
        "Constraint edges (undirected group pairs):",
        "  " + json.dumps(inst["constraint_edges"], separators=(",", ":")),
        "",
        "Candidate sets:",
    ]
    for i, group in enumerate(inst["groups"]):
        lines.append(f"Group {i}:")
        for a, candidate in enumerate(group):
            body = ",".join(map(str, candidate))
            lines.append(f"  option {a}: {{{body}}}")
    lines.extend([
        "",
        "Group IDs and option IDs are 0-indexed.  Return one [group,option] pair",
        "for every group.  Pair order is irrelevant; group IDs may not repeat.",
        "Give your final answer inside <answer></answer> tags as one JSON array.",
        "Example: <answer>[[0,2],[1,0],[2,1]]</answer>",
        "That three-pair example illustrates syntax only; it is not a complete answer.",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Parse the delimited JSON witness, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    bodies = matches[-1:] if matches else [text]
    decoder = json.JSONDecoder()
    for body in bodies:
        cleaned = re.sub(r"```(?:json)?", "", body, flags=re.I).replace("```", "")
        for start, ch in enumerate(cleaned):
            if ch != "[":
                continue
            try:
                value, _ = decoder.raw_decode(cleaned[start:])
            except (ValueError, TypeError):
                continue
            if isinstance(value, list):
                return value
    return None


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the q^n one-option-per-group language."""

    return [[i, rng.randrange(inst["q"])] for i in range(inst["n"])]


def search_space(inst) -> int | None:
    return int(inst["q"]) ** int(inst["n"])


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    total = 0
    for options in itertools.product(range(inst["q"]), repeat=inst["n"]):
        candidate = [[i, options[i]] for i in range(inst["n"])]
        if verify(inst, candidate)[0]:
            total += 1
    return total


def _constraint_adjacency(inst: dict) -> list[list[int]]:
    n = inst["n"]
    adj = [[] for _ in range(n)]
    for raw in inst["constraint_edges"]:
        i, j = map(int, raw)
        if i == j or not (0 <= i < n and 0 <= j < n):
            raise ValueError("malformed constraint edge")
        adj[i].append(j)
        adj[j].append(i)
    for row in adj:
        row.sort()
    return adj


def _rooted_wl_signature(adj: list[list[int]], root: int) -> tuple:
    """A relabelling-invariant rooted 1-WL fingerprint."""

    n = len(adj)
    colors = [1 if v == root else 0 for v in range(n)]
    for _ in range(n):
        sigs = [(colors[v], tuple(sorted(colors[w] for w in adj[v]))) for v in range(n)]
        palette = {sig: i for i, sig in enumerate(sorted(set(sigs)))}
        new = [palette[sig] for sig in sigs]
        if new == colors:
            break
        colors = new
    class_sizes = tuple(sorted(Counter(colors).items()))
    edge_colors = Counter()
    for u, row in enumerate(adj):
        for v in row:
            if u < v:
                edge_colors[tuple(sorted((colors[u], colors[v])))] += 1
    distances = [-1] * n
    distances[root] = 0
    queue = deque([root])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if distances[v] < 0:
                distances[v] = distances[u] + 1
                queue.append(v)
    return (
        class_sizes,
        tuple(sorted(edge_colors.items())),
        tuple(sorted(Counter(distances).items())),
    )


def _closed_walk_traces(adj: list[list[int]], limit: int = 14) -> tuple[int, ...]:
    n = len(adj)
    base = [[0] * n for _ in range(n)]
    for i, row in enumerate(adj):
        for j in row:
            base[i][j] = 1
    power = [row[:] for row in base]
    traces = []
    for _length in range(1, min(limit, n) + 1):
        traces.append(sum(power[i][i] for i in range(n)))
        nxt = [[0] * n for _ in range(n)]
        for i in range(n):
            for k, value in enumerate(power[i]):
                if not value:
                    continue
                for j in adj[k]:
                    nxt[i][j] += value
        power = nxt
    return tuple(traces)


def canonical_key(inst) -> str:
    """Hash a structural invariant of the constraint graph, never the seed/render.

    Independent option names and universe labels are pure relabellings.  Every
    generated consistent q-cover over the same base graph is isomorphic under
    those relabellings, so the key intentionally reduces to strong invariants of
    the unlabelled base graph plus n, q, degree and the alpha threshold.
    """

    adj = _constraint_adjacency(inst)
    invariant = {
        "n": inst["n"],
        "q": inst["q"],
        "degree": inst["degree"],
        "threshold": inst["overlap_threshold"],
        "rooted_wl": sorted(_rooted_wl_signature(adj, v) for v in range(len(adj))),
        "walk_traces": _closed_walk_traces(adj),
    }
    blob = json.dumps(invariant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase crowding at fixed witness length before touching other axes."""

    p = {k: int(v) for k, v in params.items() if not k.startswith("_")}
    n = p["n"]
    degree = p.get("degree", 3)
    if degree + 2 <= n - 5:
        p["degree"] = degree + 2
        return p
    q = p.get("q", 8)
    if q < MAX_Q:
        p["q"] = q + 1
        p["degree"] = min(degree, n - 5)
        return p
    if n < MAX_N:
        p["n"] = min(MAX_N, n + 16)
        p["degree"] = min(degree, p["n"] - 5)
        return p
    return "cap_bound"


def _reference_algorithm(inst: dict) -> tuple[object | None, dict]:
    """Index positive-element incidences, then propagate one component.

    This is the strongest simple exact baseline for the displayed distribution:
    scan every set once, use shared positive elements to mark forbidden option
    pairs, inspect each local table, and propagate.  It does not read
    ``inst['answer']`` or the redundant ``inst['edge_matchings']`` cache.
    """

    started = time.perf_counter()
    n, q = inst["n"], inst["q"]
    zero = inst["zero_weight_element"]
    edge_keys = {
        tuple(sorted((int(raw_i), int(raw_j))))
        for raw_i, raw_j in inst["constraint_edges"]
    }
    allowed = {
        edge: [[True] * q for _ in range(q)]
        for edge in edge_keys
    }
    postings: dict[int, list[tuple[int, int]]] = {}
    operations = 0
    incidence_reads = 0
    conflict_marks = 0
    compatibility_cells = 0

    for i, group in enumerate(inst["groups"]):
        for a, candidate in enumerate(group):
            for element in candidate:
                incidence_reads += 1
                operations += 1
                if element != zero:
                    postings.setdefault(element, []).append((i, a))

    for occurrences in postings.values():
        for left_pos in range(len(occurrences)):
            left_group, left_option = occurrences[left_pos]
            for right_group, right_option in occurrences[left_pos + 1:]:
                operations += 1
                if left_group == right_group:
                    continue
                i, a = left_group, left_option
                j, b = right_group, right_option
                if i > j:
                    i, j, a, b = j, i, b, a
                edge = (i, j)
                if edge not in allowed:
                    return None, {
                        "operations": operations,
                        "incidence_reads": incidence_reads,
                        "conflict_marks": conflict_marks,
                        "compatibility_cells": compatibility_cells,
                        "nodes": 0,
                        "wall_clock_sec": time.perf_counter() - started,
                        "reason": "positive overlap appeared on an unlisted group pair",
                    }
                if allowed[edge][a][b]:
                    allowed[edge][a][b] = False
                    conflict_marks += 1

    tables: dict[tuple[int, int], list[int]] = {}
    for edge in sorted(edge_keys):
        mapping = [-1] * q
        used = set()
        for a in range(q):
            compatible = [b for b in range(q) if allowed[edge][a][b]]
            compatibility_cells += q
            operations += q
            if len(compatible) != 1:
                return None, {
                    "operations": operations,
                    "incidence_reads": incidence_reads,
                    "conflict_marks": conflict_marks,
                    "compatibility_cells": compatibility_cells,
                    "nodes": 0,
                    "wall_clock_sec": time.perf_counter() - started,
                    "reason": "a local compatibility row was not a singleton",
                }
            mapping[a] = compatible[0]
            used.add(compatible[0])
        if len(used) != q:
            return None, {
                "operations": operations,
                "incidence_reads": incidence_reads,
                "conflict_marks": conflict_marks,
                "compatibility_cells": compatibility_cells,
                "nodes": 0,
                "wall_clock_sec": time.perf_counter() - started,
                "reason": "a local compatibility relation was not a perfect matching",
            }
        tables[edge] = mapping

    adjacency = [[] for _ in range(n)]
    for (i, j), mapping in tables.items():
        inverse = [-1] * q
        for a, b in enumerate(mapping):
            inverse[b] = a
        adjacency[i].append((j, mapping))
        adjacency[j].append((i, inverse))

    assigned: dict[int, int] = {0: 0}
    queue = deque([0])
    nodes = 0
    while queue:
        i = queue.popleft()
        nodes += 1
        for j, mapping in adjacency[i]:
            operations += 1
            b = mapping[assigned[i]]
            if j in assigned:
                if assigned[j] != b:
                    return None, {
                        "operations": operations,
                        "incidence_reads": incidence_reads,
                        "conflict_marks": conflict_marks,
                        "compatibility_cells": compatibility_cells,
                        "nodes": nodes,
                        "wall_clock_sec": time.perf_counter() - started,
                        "reason": "cycle inconsistency",
                    }
            else:
                assigned[j] = b
                queue.append(j)
    if len(assigned) != n:
        return None, {
            "operations": operations,
            "incidence_reads": incidence_reads,
            "conflict_marks": conflict_marks,
            "compatibility_cells": compatibility_cells,
            "nodes": nodes,
            "wall_clock_sec": time.perf_counter() - started,
            "reason": "constraint graph disconnected",
        }
    answer = [[i, assigned[i]] for i in range(n)]
    elapsed = time.perf_counter() - started
    return answer, {
        "operations": operations,
        "incidence_reads": incidence_reads,
        "conflict_marks": conflict_marks,
        "compatibility_cells": compatibility_cells,
        "nodes": nodes,
        "wall_clock_sec": elapsed,
        "reason": "ok",
    }


def _compact_anchor_algorithm(inst: dict) -> tuple[list[list[int]], int]:
    """Recover global sheet zero from the anchor-weight-residue invariant.

    This reads only rendered instance fields, never ``inst['answer']``.  One
    remainder and one modular negation per group give the local option whose
    coordinate is zero.
    """

    q = inst["q"]
    answer = []
    operations = 0
    for group, weight in enumerate(inst["group_anchor_weights"]):
        shift = weight % q
        option = (-shift) % q
        operations += 2
        answer.append([group, option])
    return answer, operations


def _attack_equal_option(inst: dict) -> list[list[int]]:
    return [[i, 0] for i in range(inst["n"])]


def _attack_outlier_min_sum(inst: dict) -> list[list[int]]:
    zero = inst["zero_weight_element"]
    answer = []
    for i, group in enumerate(inst["groups"]):
        total_weight = inst["group_anchor_weights"][i] + inst["r"] - 2
        scores = [
            (total_weight, sum(x for x in candidate if x != zero), a)
            for a, candidate in enumerate(group)
        ]
        answer.append([i, min(range(inst["q"]), key=lambda a: scores[a])])
    return answer


def _attack_greedy_left_to_right(inst: dict) -> list[list[int]]:
    selected: dict[int, int] = {}
    selected_sets: dict[int, frozenset[int]] = {}
    for i in range(inst["n"]):
        choice = None
        for a in range(inst["q"]):
            candidate = _candidate_set(inst, i, a)
            if all(
                not _alpha_conflict(inst, candidate, selected_sets[j])
                for j in selected_sets
            ):
                choice = a
                break
        if choice is None:
            choice = 0
        selected[i] = choice
        selected_sets[i] = _candidate_set(inst, i, choice)
    return [[i, selected[i]] for i in range(inst["n"])]


def _attack_local_plurality(inst: dict) -> list[list[int]]:
    """Choose the option compatible with most option-zero neighboring sets."""

    adj = _constraint_adjacency(inst)
    answer = []
    for i in range(inst["n"]):
        scores = []
        for a in range(inst["q"]):
            candidate = _candidate_set(inst, i, a)
            score = sum(
                not _alpha_conflict(inst, candidate, _candidate_set(inst, j, 0))
                for j in adj[i]
            )
            scores.append(score)
        best = max(range(inst["q"]), key=lambda a: (scores[a], -a))
        answer.append([i, best])
    return answer


def _transform_instance(inst: dict, seed: int) -> dict:
    """Compose universe, option, group and presentation relabellings."""

    rng = random.Random(seed)
    out = {
        k: v
        for k, v in inst.items()
        if k not in {
            "groups", "group_anchors", "group_anchor_weights",
            "constraint_edges", "edge_matchings", "answer"
        }
    }
    groups = [[list(s) for s in group] for group in inst["groups"]]
    answer_map = {int(g): int(a) for g, a in inst["answer"]}

    # Universe relabelling, including transport of the distinguished weight-zero
    # element.  Also reorder each set's presentation.
    elements = sorted({x for group in groups for s in group for x in s})
    shuffled = elements[:]
    rng.shuffle(shuffled)
    element_map = dict(zip(elements, shuffled))
    groups = [
        [[element_map[x] for x in s] for s in group]
        for group in groups
    ]
    for group in groups:
        for s in group:
            rng.shuffle(s)
    out["zero_weight_element"] = element_map[inst["zero_weight_element"]]
    anchors = [element_map[value] for value in inst["group_anchors"]]
    anchor_weights = list(inst["group_anchor_weights"])

    # Independent option permutations.
    for i in range(inst["n"]):
        order = list(range(inst["q"]))
        rng.shuffle(order)
        inverse = {old: new for new, old in enumerate(order)}
        groups[i] = [groups[i][old] for old in order]
        answer_map[i] = inverse[answer_map[i]]

    # Group permutation.  order[new] = old.
    order = list(range(inst["n"]))
    rng.shuffle(order)
    inverse_group = {old: new for new, old in enumerate(order)}
    groups = [groups[old] for old in order]
    anchors = [anchors[old] for old in order]
    anchor_weights = [anchor_weights[old] for old in order]
    edges = [
        [inverse_group[int(i)], inverse_group[int(j)]]
        for i, j in inst["constraint_edges"]
    ]
    rng.shuffle(edges)
    for edge in edges:
        if rng.randrange(2):
            edge.reverse()
    answer = [
        [inverse_group[old], answer_map[old]]
        for old in range(inst["n"])
    ]
    rng.shuffle(answer)

    out["groups"] = groups
    out["group_anchors"] = anchors
    out["group_anchor_weights"] = anchor_weights
    out["constraint_edges"] = edges
    out["answer"] = answer
    out["edge_matchings"] = _derive_edge_matchings(out)
    return out


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run mandatory gates and return their machine-readable measurements."""

    report: dict = {"paper": "1601.03676", "track": TRACK}

    # G1: all presets, several seeds, and JSON-native answers.
    g1_checks = 0
    g1_errors = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            compact, _ = _compact_anchor_algorithm(inst)
            compact_ok = verify(inst, compact)[0]
            g1_checks += 1
            if not ok or not json_ok or not compact_ok:
                g1_errors.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_errors,
        "checks": g1_checks,
        "errors": g1_errors,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=73, **shipping)

    # G2: five qualitatively different corruptions and five distinct reasons.
    planted = [pair[:] for pair in inst["answer"]]
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate_group": planted[:-1] + [planted[0][:]],
        "out_of_range": planted[:-1] + [[planted[-1][0], inst["q"]]],
    }
    swapped = None
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            trial = [pair[:] for pair in planted]
            trial[i][1], trial[j][1] = trial[j][1], trial[i][1]
            if trial != planted and not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = [pair[:] for pair in planted]
        swapped[0][1] = (swapped[0][1] + 1) % inst["q"]
    corruptions["swap_options"] = swapped
    rejection_reasons = {}
    g2_ok = True
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejection_reasons[name] = reason
        g2_ok = g2_ok and not ok
    g2_ok = g2_ok and len(set(rejection_reasons.values())) == len(corruptions)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "reasons": rejection_reasons,
        "distinct_reasons": len(set(rejection_reasons.values())),
    }

    # G3: actual model-style prose and a fenced tagged JSON answer.
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    model_reply = (
        "I checked every positive-weight intersection.\n\n```json\n"
        f"<answer>{encoded}</answer>\n```\nThe tags contain only the requested object."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_equals_answer": parsed == inst["answer"],
    }

    # G4 and shipping-density half of G5.  Random candidates already enforce the
    # one-option-per-group structure that the statement gives away for free.
    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform over q^n one-option-per-group assignments",
    }

    # Exact enumeration where it is genuinely small.
    demo_inst = make_instance(seed=73, **DIFFICULTY["demo"])
    demo_solution_count = enumerate_all(demo_inst)

    # Reference algorithm across eight shipping seeds, also used by G6.
    ref_successes = 0
    ref_operations = []
    ref_incidence_reads = []
    ref_conflict_marks = []
    ref_compatibility_cells = []
    ref_nodes = []
    ref_seconds = []
    compact_successes = 0
    compact_operations = []
    reference_seeds = list(range(800, 808))
    reference_instances = []
    for seed in reference_seeds:
        test_inst = make_instance(seed=seed, **shipping)
        reference_instances.append(test_inst)
        candidate, stats = _reference_algorithm(test_inst)
        solved = candidate is not None and verify(test_inst, candidate)[0]
        ref_successes += int(solved)
        ref_operations.append(stats["operations"])
        ref_incidence_reads.append(stats["incidence_reads"])
        ref_conflict_marks.append(stats["conflict_marks"])
        ref_compatibility_cells.append(stats["compatibility_cells"])
        ref_nodes.append(stats["nodes"])
        ref_seconds.append(stats["wall_clock_sec"])
        compact_candidate, compact_ops = _compact_anchor_algorithm(test_inst)
        compact_successes += int(verify(test_inst, compact_candidate)[0])
        compact_operations.append(compact_ops)

    report["G5_density_and_baseline"] = {
        "pass": (
            guess_probability < 1e-6
            and demo_solution_count == demo_inst["q"]
            and ref_successes == 8
            and compact_successes == 8
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_probability,
        "shipping_solution_count_known_by_construction": inst["q"],
        "demo_exact_solution_count": demo_solution_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_wall_clock_sec_mean": sum(ref_seconds) / len(ref_seconds),
        "baseline_operations_mean": sum(ref_operations) / len(ref_operations),
        "baseline_operations_max": max(ref_operations),
        "baseline_incidence_reads_mean": (
            sum(ref_incidence_reads) / len(ref_incidence_reads)
        ),
        "baseline_conflict_marks_mean": (
            sum(ref_conflict_marks) / len(ref_conflict_marks)
        ),
        "baseline_compatibility_cells_mean": (
            sum(ref_compatibility_cells) / len(ref_compatibility_cells)
        ),
        "baseline_component_nodes_mean": sum(ref_nodes) / len(ref_nodes),
    }

    attack_results = {
        "outlier_weight_and_label_sum": {"successes": 0, "attempts": 8},
        "greedy_left_to_right": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "equal_local_option_ansatz": {"successes": 0, "attempts": 8},
        "local_option_zero_plurality": {"successes": 0, "attempts": 8},
    }
    for offset, test_inst in enumerate(reference_instances):
        attacks = {
            "outlier_weight_and_label_sum": _attack_outlier_min_sum(test_inst),
            "greedy_left_to_right": _attack_greedy_left_to_right(test_inst),
            "equal_local_option_ansatz": _attack_equal_option(test_inst),
            "local_option_zero_plurality": _attack_local_plurality(test_inst),
        }
        for name, candidate in attacks.items():
            attack_results[name]["successes"] += int(verify(test_inst, candidate)[0])

        restart_rng = random.Random(90_000 + offset)
        restart_hit = False
        for _ in range(256):
            if verify(test_inst, random_candidate(test_inst, restart_rng))[0]:
                restart_hit = True
                break
        attack_results["random_restart_256"]["successes"] += int(restart_hit)

    all_attacks_failed = all(v["successes"] == 0 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "positive-element incidence index plus component propagation",
            "complexity": "O(L + |E| q^2) exact operations on this distribution",
            "wall_clock_sec_mean": sum(ref_seconds) / len(ref_seconds),
            "operations_mean": sum(ref_operations) / len(ref_operations),
            "operations_max": max(ref_operations),
            "incidence_reads_mean": (
                sum(ref_incidence_reads) / len(ref_incidence_reads)
            ),
            "conflict_marks_mean": (
                sum(ref_conflict_marks) / len(ref_conflict_marks)
            ),
            "compatibility_cells_mean": (
                sum(ref_compatibility_cells) / len(ref_compatibility_cells)
            ),
            "component_nodes_mean": sum(ref_nodes) / len(ref_nodes),
            "solves": f"{ref_successes}/8, as expected for Track B",
        },
        "compact_route_audit": {
            "name": "anchor weight residue modulo q to global sheet zero",
            "complexity": "O(n) exact modular operations after recognizing the invariant",
            "operations_mean": sum(compact_operations) / len(compact_operations),
            "operations_max": max(compact_operations),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    # G7: double the principal size axis without using a solver during build.
    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * shipping["n"]
    doubled = make_instance(seed=991, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    first_escalation = escalate(dict(shipping))
    escalation_probe = dict(shipping)
    escalation_steps = 0
    while escalation_steps < 1000:
        next_probe = escalate(escalation_probe)
        if next_probe == "cap_bound":
            break
        if not isinstance(next_probe, dict) or next_probe == escalation_probe:
            break
        escalation_probe = next_probe
        escalation_steps += 1
    cap_is_honest = (
        next_probe == "cap_bound"
        and escalation_probe["n"] == MAX_N
        and 2 * escalation_probe["n"] == 256
    )
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and search_space(doubled) > search_space(inst)
            and isinstance(first_escalation, dict)
            and first_escalation["n"] == shipping["n"]
            and cap_is_honest
        ),
        "base_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "base_space_bits": int(math.log2(search_space(inst))),
        "doubled_space_bits": int(math.log2(search_space(doubled))),
        "doubled_verify_reason": doubled_reason,
        "first_escalation": first_escalation,
        "first_escalation_keeps_answer_atoms": (
            isinstance(first_escalation, dict)
            and first_escalation["n"] == shipping["n"]
        ),
        "steps_until_cap_bound": escalation_steps,
        "cap_bound_parameters": escalation_probe,
        "cap_bound_answer_atoms": 2 * escalation_probe["n"],
    }

    # G8: composed real relabellings and unrelated-seed distinctness.
    invariant_checks = 0
    carried_verifications = 0
    keys = []
    g8_errors = []
    for offset, seed in enumerate(range(1200, 1220)):
        original = make_instance(seed=seed, **shipping)
        transformed = _transform_instance(original, seed=50_000 + offset)
        key_original = canonical_key(original)
        key_transformed = canonical_key(transformed)
        invariant_checks += 1
        if key_original != key_transformed:
            g8_errors.append(f"seed {seed}: composed relabelling changed key")
        ok, reason = verify(transformed, transformed["answer"])
        carried_verifications += int(ok)
        if not ok:
            g8_errors.append(f"seed {seed}: carried answer failed: {reason}")

        # With threshold zero every positive weight has exactly the same effect.
        # Normalizing those magnitudes prevents random decorative weights from
        # acting as a nonce in the diversity key.
        normalized_weights = dict(transformed)
        normalized_weights["group_anchor_weights"] = [1] * original["n"]
        invariant_checks += 1
        if canonical_key(normalized_weights) != key_original:
            g8_errors.append(f"seed {seed}: positive-weight normalization changed key")
        normalized_ok, normalized_reason = verify(
            normalized_weights, normalized_weights["answer"]
        )
        carried_verifications += int(normalized_ok)
        if not normalized_ok:
            g8_errors.append(
                f"seed {seed}: normalized-weight answer failed: {normalized_reason}"
            )
        keys.append(key_original)
    distinct_count = len(set(keys))
    if distinct_count != len(keys):
        g8_errors.append("unrelated shipping seeds collided under the structural invariant")
    report["G8_canonical_key"] = {
        "pass": not g8_errors,
        "invariance_checks": invariant_checks,
        "carried_answer_verifications": carried_verifications,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": len(keys),
        "transformations": [
            "universe-element relabelling",
            "element order within sets",
            "independent option relabelling",
            "group relabelling",
            "constraint-edge order and orientation",
            "answer-pair order",
            "positive-weight magnitude normalization at threshold zero",
        ],
        "errors": g8_errors,
    }

    compact_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact_answer)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_ops = 2 * inst["n"]
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300,
        "arms": G9_ARM_RESULTS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
