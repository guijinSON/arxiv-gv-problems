"""Verified inverse generator for two-flip paths on perfect matching polytopes.

The native combinatorial representation from Cardinal--Steiner, arXiv:2210.14608,
is used throughout: vertices of a bipartite perfect matching polytope are perfect
matchings, and skeleton edges are flips of one alternating cycle (Lemma 1).

The module is deterministic in ``(n, seed, decoys)``, standard-library-only, and
has no import-time side effects.
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
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "balanced bipartite graph",
        "vertices of a perfect matching polytope represented as perfect matchings",
        "two-flip skeleton path represented by its intermediate perfect matching",
    ],
    "verification_operations": [
        "perfect-matching incidence check",
        "exact inverse-permutation composition",
        "symmetric-difference cycle traversal",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 1.1 and Lemma 1: vertices of P_G are perfect matchings and two "
        "vertices are adjacent exactly when their symmetric difference is one cycle"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Normalize one endpoint matching to the identity and propagate two "
        "simultaneous no-subtour constraints; without that view one searches "
        "through exponentially many sparse perfect matchings."
    ),
    "hardness_basis": (
        "Track A: Theorem 1 for fixed k=2 proves NP-hardness under the promise "
        "distance at most two (even at maximum degree three); this generator uses "
        "growing 2n-vertex, degree-(3+decoys) instances in that fixed-k regime, "
        "with shipping cost measured by the cycle-aware DPLL baseline in selftest."
    ),
    "max_answer_tokens": 166,
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
    "demo": {"n": 6, "decoys": 1},
    # n=72 was rejected: cycle-aware DPLL solved 7/8 panel seeds even though
    # all three bare oracles failed. The release ladder starts at the first
    # locally defensible size and keeps the answer below G9's 256-element cap.
    "easy": {"n": 192, "decoys": 2},
    "medium": {"n": 224, "decoys": 2},
    "hard": {"n": 240, "decoys": 2},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Normalize the first matching to the identity and propagate both simultaneous no-subtour constraints before branching."
)
PLACEBO_HINT = (
    "Keep the matching arrays consistently indexed and check both required cycle conditions carefully before answering."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "Exactly n integers P[1],...,P[n] in 1..n, all distinct, representing "
        "a perfect matching; the sampled language additionally enforces the "
        "freely visible first-endpoint structure by making inv(M_start) o P a "
        "single n-cycle. Coefficient/label width is ceil(log2(n+1)) bits."
    ),
    "bounds": {
        "entries": "inst['n']",
        "label_min": 1,
        "label_max": "inst['n']",
        "all_distinct": True,
        "first_relative_permutation_cycles": 1,
        "candidate_count": "(n-1)!",
    },
}

NOTES = r"""
Definition. Section 1.1 defines P_G as the convex hull of incidence vectors of
perfect matchings in a balanced bipartite graph. Lemma 1 is the exact rule used
here: two such vertices are adjacent precisely when the symmetric difference of
their matchings is one alternating cycle. The render states this through an
equivalent inverse-permutation traversal, so no knowledge of the paper is needed.

Hard and easy regimes. Theorem 1 says that for every fixed k >= 2, producing a
path of length at most k remains NP-hard even when the two given matchings are
promised to be at distance at most two and the graph has maximum degree three.
Its ETH statement permits k to grow only as (1/4-o(1)) log N/log log N; this
family stays at k=2 while N grows. Section 1.3 records polynomial reachability
for a different matching-reconfiguration move and PSPACE-completeness when flips
are restricted to 4-cycles; neither is the skeleton adjacency used here. The
paper supplies no algorithm for producing the promised two-step witness.

Certificate source. The intermediate matching is sampled before either endpoint
or any decoy. Its permutation relative to the first endpoint is an n-cycle. A
second independent n-cycle is composed with it to make the other endpoint, so
both skeleton steps verify by Lemma 1. Extra matchings are sampled from the same
n-cycle distribution as the plant, all edge roles are merged, and the two colour
classes are relabelled independently. The certificate is never obtained by
solving the finished instance.

Attacks and distribution warning. Worst-case NP-hardness does not prove this
planted distribution hard. The panel therefore tries a local/outlier-ranked
perfect matching, a no-backtracking greedy route, randomized matching restarts,
and cycle-aware DPLL with early subtour rejection (the standard exact CSP route).
The last attack is the deciding empirical check. The cheap canonical key is an
isomorphism invariant obtained by colour refinement relative to the distinguished
endpoint permutation; it is deliberately documented as a strong invariant, not
a complete graph-isomorphism canonical form.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INT_LIST_RE = re.compile(r"[+-]?\d+(?:\s*(?:,|\s)\s*[+-]?\d+)*")
_ENUMERATION_CAP = 250_000


def _validate_params(n: int, decoys: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    if isinstance(decoys, bool) or not isinstance(decoys, int) or decoys < 1:
        raise ValueError("decoys must be a positive integer")
    if decoys + 3 > n:
        raise ValueError("n is too small for the requested number of edge-disjoint matchings")


def _random_n_cycle(n: int, rng: random.Random) -> list[int]:
    order = list(range(n))
    rng.shuffle(order)
    permutation = [0] * n
    for a, b in zip(order, order[1:] + order[:1]):
        permutation[a] = b
    return permutation


def _inverse(permutation: list[int]) -> list[int]:
    inv = [0] * len(permutation)
    for i, value in enumerate(permutation):
        inv[value] = i
    return inv


def _relative_permutation(first: list[int], second: list[int]) -> list[int]:
    inv = _inverse(first)
    return [inv[value] for value in second]


def _cycle_lengths(permutation: list[int]) -> list[int]:
    n = len(permutation)
    seen = [False] * n
    lengths = []
    for start in range(n):
        if seen[start]:
            continue
        length = 0
        vertex = start
        while not seen[vertex]:
            seen[vertex] = True
            vertex = permutation[vertex]
            length += 1
        lengths.append(length)
    return sorted(lengths)


def _is_n_cycle_relative(first: list[int], second: list[int]) -> bool:
    n = len(first)
    # Public matchings use the stated 1..n labels; construction-time
    # permutations use Python's 0..n-1 labels.
    if set(first) == set(range(1, n + 1)):
        first = [value - 1 for value in first]
        second = [value - 1 for value in second]
    return _cycle_lengths(_relative_permutation(first, second)) == [n]


def _sample_avoiding_cycle(
    n: int, rng: random.Random, forbidden: list[list[int]], max_tries: int = 200_000
) -> list[int]:
    for _ in range(max_tries):
        candidate = _random_n_cycle(n, rng)
        if all(all(candidate[i] != old[i] for old in forbidden) for i in range(n)):
            return candidate
    raise RuntimeError("could not sample an edge-disjoint n-cycle")


def make_instance(n: int, seed: int = 0, decoys: int = 2, **params: Any) -> dict:
    """Inverse-generate a certified two-edge skeleton path.

    ``n`` is the size of each bipartition class, hence the polytope's graph has
    ``2*n`` vertices. Larger ``n`` increases both the certificate language and
    the sparse simultaneous-cycle CSP.
    """
    if params:
        raise TypeError("unknown make_instance parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n, decoys)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # G: the full abstract witness is sampled before either endpoint or a decoy.
    start = list(range(n))
    planted = _random_n_cycle(n, rng)

    # Compose an independently sampled n-cycle on the LEFT labels with the
    # planted matching. Then inv(planted) o finish is exactly that n-cycle.
    # Reject the rare case in which the endpoints themselves are adjacent: the
    # intended shortest path must have length exactly two, not merely at most two.
    for _ in range(200_000):
        second_step = _random_n_cycle(n, rng)
        finish = [planted[second_step[i]] for i in range(n)]
        if all(finish[i] != start[i] for i in range(n)) and not _is_n_cycle_relative(start, finish):
            break
    else:
        raise RuntimeError("could not sample a nonadjacent finish matching")

    candidate_layers = [planted]
    for _ in range(decoys):
        candidate_layers.append(
            _sample_avoiding_cycle(n, rng, [start, finish] + candidate_layers)
        )

    # Independent relabellings of both colour classes erase construction order.
    left_labels = list(range(n))
    right_labels = list(range(n))
    rng.shuffle(left_labels)
    rng.shuffle(right_labels)

    def relabel_matching(old: list[int]) -> list[int]:
        new = [0] * n
        for old_left, old_right in enumerate(old):
            new[left_labels[old_left]] = right_labels[old_right] + 1
        return new

    start_r = relabel_matching(start)
    finish_r = relabel_matching(finish)
    planted_r = relabel_matching(planted)
    layers_r = [relabel_matching(layer) for layer in candidate_layers]

    neighbours = []
    for left in range(n):
        row = {start_r[left], finish_r[left]}
        row.update(layer[left] for layer in layers_r)
        if len(row) != decoys + 3:
            raise AssertionError("internal edge-disjointness failure")
        row = list(row)
        rng.shuffle(row)
        neighbours.append(row)

    return {
        "family": "two-flip paths on a bipartite perfect matching polytope",
        "n": n,
        "decoys": decoys,
        "left_vertices": list(range(1, n + 1)),
        "right_vertices": list(range(1, n + 1)),
        "neighbours": neighbours,
        "start_matching": start_r,
        "finish_matching": finish_r,
        "answer": planted_r,
    }


def render(inst: dict) -> str:
    """Render the complete problem and its exact permutation wire format."""
    n = inst["n"]
    rows = "\n".join(
        f"L{i}: " + " ".join(map(str, sorted(inst["neighbours"][i - 1])))
        for i in range(1, n + 1)
    )
    start = " ".join(map(str, inst["start_matching"]))
    finish = " ".join(map(str, inst["finish_matching"]))
    example = ", ".join(map(str, range(1, n + 1)))
    statement = f"""TWO-FLIP PATH ON A PERFECT MATCHING POLYTOPE

The bipartite graph below has left vertices L1,...,L{n} and right vertices
R1,...,R{n}. Row Li lists exactly the right-vertex labels adjacent to Li.
Labels are 1-indexed and all bounds below are inclusive.

A perfect matching is represented by an array P[1],...,P[{n}]: edge
(Li,R(P[i])) is selected for every i. Thus every P[i] must occur in Li's row,
and the array must contain every integer 1,...,{n} exactly once.

For two perfect matchings X and Y, define f_XY(i) to be the unique index j
with X[j]=Y[i]. Their symmetric difference is one alternating cycle through
all 2*{n} graph vertices exactly when repeated application of f_XY, starting
at index 1, visits all {n} left indices once and then returns to 1.
By the bipartite perfect-matching-polytope adjacency rule, this condition means
that X and Y are adjacent vertices of the polytope's skeleton.

Find an intermediate perfect matching P such that START and P have this
single-cycle property and P and FINISH have this single-cycle property. Your
answer therefore certifies the two-edge skeleton path START -> P -> FINISH.
START and FINISH themselves do not have the single-cycle property.

START (entry i is matched to Li):
{start}

FINISH (entry i is matched to Li):
{finish}

GRAPH NEIGHBOUR ROWS:
{rows}

Return exactly {n} comma-separated integers in array order P[1] through P[{n}].
Order is fixed by the left labels; repeats and omissions are forbidden.

Give your final answer inside <answer></answer> tags, as the comma-separated array.
Example format only: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the last delimited integer array, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    for body in reversed(blocks):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
            body = re.sub(r"\s*```$", "", body)
        try:
            decoded = json.loads(body)
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, list) and all(
            isinstance(value, int) and not isinstance(value, bool) for value in decoded
        ):
            return decoded
        if not body or _INT_LIST_RE.fullmatch(body) is None:
            continue
        try:
            return [int(token) for token in re.split(r"(?:\s*,\s*|\s+)", body) if token]
        except ValueError:
            continue
    return None


def _validate_matching(inst: dict, answer: Any) -> tuple[list[int] | None, str]:
    n = inst["n"]
    if not isinstance(answer, list):
        return None, "answer must be a list"
    if not answer:
        return None, "answer is empty"
    if len(answer) != n:
        return None, f"wrong length: expected {n}, got {len(answer)}"
    for i, value in enumerate(answer, 1):
        if isinstance(value, bool) or not isinstance(value, int):
            return None, f"entry {i} is not an integer"
        if not 1 <= value <= n:
            return None, f"entry {i} is out of range 1..{n}"
    if len(set(answer)) != n:
        return None, "right-vertex labels are repeated"
    for i, value in enumerate(answer):
        if value not in inst["neighbours"][i]:
            return None, f"edge (L{i + 1},R{value}) is not in the graph"
    return answer, "ok"


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Check any valid intermediate matching without consulting the plant."""
    candidate, reason = _validate_matching(inst, answer)
    if candidate is None:
        return False, reason
    if not _is_n_cycle_relative(inst["start_matching"], candidate):
        return False, "START symmetric difference is not one spanning alternating cycle"
    if not _is_n_cycle_relative(candidate, inst["finish_matching"]):
        return False, "FINISH symmetric difference is not one spanning alternating cycle"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the (n-1)! matchings n-cycle-adjacent to START.

    This enforces array shape, range, distinctness, and the first no-subtour
    condition. Graph incidence and simultaneous adjacency to FINISH are the
    nontrivial search constraints and are not conditioned upon.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n = inst["n"]
    relative = _random_n_cycle(n, rng)
    start = inst["start_matching"]
    return [start[relative[i]] for i in range(n)]


def search_space(inst: dict) -> int | None:
    return math.factorial(inst["n"] - 1)


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if math.factorial(n - 1) > _ENUMERATION_CAP:
        return None
    start = inst["start_matching"]
    count = 0
    for tail in itertools.permutations(range(1, n)):
        order = (0,) + tail
        relative = [0] * n
        for a, b in zip(order, order[1:] + order[:1]):
            relative[a] = b
        candidate = [start[relative[i]] for i in range(n)]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _normalised_structure(inst: dict) -> tuple[list[int], list[list[int]]]:
    """Use START to identify right labels with left labels."""
    n = inst["n"]
    start0 = [value - 1 for value in inst["start_matching"]]
    inv_start = _inverse(start0)
    finish = [inv_start[value - 1] for value in inst["finish_matching"]]
    candidates = []
    for i, row in enumerate(inst["neighbours"]):
        endpoints = {start0[i], inst["finish_matching"][i] - 1}
        candidates.append(sorted(inv_start[value - 1] for value in row if value - 1 not in endpoints))
    return finish, candidates


def canonical_key(inst: dict) -> str:
    """A relabelling-invariant colour-refinement key, not a seed/render hash."""
    finish, candidates = _normalised_structure(inst)
    n = len(finish)
    inv_finish = _inverse(finish)
    incoming = [[] for _ in range(n)]
    for source, row in enumerate(candidates):
        for target in row:
            incoming[target].append(source)

    cycle_len = [0] * n
    seen = [False] * n
    for start in range(n):
        if seen[start]:
            continue
        vertices = []
        vertex = start
        while not seen[vertex]:
            seen[vertex] = True
            vertices.append(vertex)
            vertex = finish[vertex]
        for vertex in vertices:
            cycle_len[vertex] = len(vertices)

    palette = {value: i for i, value in enumerate(sorted(set(cycle_len)))}
    colours = [palette[value] for value in cycle_len]
    history = []
    for _ in range(min(n, 24)):
        signatures = [
            (
                colours[v],
                colours[finish[v]],
                colours[inv_finish[v]],
                tuple(sorted(colours[w] for w in candidates[v])),
                tuple(sorted(colours[w] for w in incoming[v])),
            )
            for v in range(n)
        ]
        unique = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_colours = [unique[signature] for signature in signatures]
        history.append(sorted(new_colours.count(c) for c in set(new_colours)))
        if new_colours == colours:
            break
        colours = new_colours

    classes = sorted(set(colours))
    quotient = []
    for c in classes:
        members = [v for v in range(n) if colours[v] == c]
        records = []
        for v in members:
            records.append((
                colours[finish[v]],
                colours[inv_finish[v]],
                tuple(sorted(colours[w] for w in candidates[v])),
                tuple(sorted(colours[w] for w in incoming[v])),
            ))
        quotient.append((len(members), tuple(sorted(records))))

    payload: dict[str, Any] = {
        "n": n,
        "degree": tuple(sorted(len(row) for row in candidates)),
        "finish_cycle_type": tuple(sorted(_cycle_lengths(finish))),
        "history": history,
        "quotient": quotient,
    }
    if len(classes) == n:
        by_colour = [0] * n
        for vertex, colour in enumerate(colours):
            by_colour[colour] = vertex
        payload["individualised"] = [
            (
                colours[finish[v]],
                tuple(sorted(colours[w] for w in candidates[v])),
            )
            for v in by_colour
        ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "wl-endpoint-v1:" + hashlib.sha256(encoded.encode()).hexdigest()


def escalate(params: dict) -> dict | None:
    n = int(params["n"])
    decoys = int(params.get("decoys", 2))
    if n < 224:
        return {"n": 224, "decoys": decoys}
    if n < 240:
        return {"n": 240, "decoys": decoys}
    return None


# ---- adversarial probes -------------------------------------------------

def _denormalise(inst: dict, relative: list[int]) -> list[int]:
    start = inst["start_matching"]
    return [start[relative[i]] for i in range(inst["n"])]


def _kuhn_matching(options: list[list[int]], orders: list[list[int]] | None = None) -> list[int] | None:
    n = len(options)
    match_target = [-1] * n

    def augment(source: int, seen: list[bool]) -> bool:
        row = orders[source] if orders is not None else options[source]
        for target in row:
            if seen[target]:
                continue
            seen[target] = True
            if match_target[target] < 0 or augment(match_target[target], seen):
                match_target[target] = source
                return True
        return False

    for source in range(n):
        if not augment(source, [False] * n):
            return None
    result = [-1] * n
    for target, source in enumerate(match_target):
        result[source] = target
    return result


def _attack_outlier(inst: dict) -> list[int] | None:
    finish, options = _normalised_structure(inst)
    n = len(options)
    incoming = [0] * n
    for row in options:
        for target in row:
            incoming[target] += 1
    ranked = [
        sorted(row, key=lambda target: (incoming[target], abs(target - finish[source]), target))
        for source, row in enumerate(options)
    ]
    relative = _kuhn_matching(options, ranked)
    return None if relative is None else _denormalise(inst, relative)


def _creates_small_cycle(successor: list[int], source: int, target: int, assigned: int, n: int) -> bool:
    vertex = target
    steps = 1
    while successor[vertex] >= 0:
        vertex = successor[vertex]
        steps += 1
        if vertex == source:
            return assigned < n
        if steps > n:
            return True
    return False


def _attack_greedy(inst: dict) -> list[int] | None:
    finish, options = _normalised_structure(inst)
    n = len(options)
    inv_finish = _inverse(finish)
    assignment = [-1] * n
    used = [False] * n
    succ1 = [-1] * n
    succ2 = [-1] * n
    for assigned in range(1, n + 1):
        best = None
        for source in range(n):
            if assignment[source] >= 0:
                continue
            legal = []
            for target in options[source]:
                if used[target]:
                    continue
                if _creates_small_cycle(succ1, source, target, assigned, n):
                    continue
                if _creates_small_cycle(succ2, inv_finish[target], source, assigned, n):
                    continue
                legal.append(target)
            if not legal:
                return None
            candidate = (len(legal), source, min(legal))
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        _, source, target = best
        assignment[source] = target
        used[target] = True
        succ1[source] = target
        succ2[inv_finish[target]] = source
    return _denormalise(inst, assignment)


def _attack_random_restarts(inst: dict, seed: int, restarts: int = 128) -> list[int] | None:
    _, options = _normalised_structure(inst)
    rng = random.Random(seed ^ 0x9E3779B97F4A7C15)
    for _ in range(restarts):
        orders = []
        for row in options:
            shuffled = row[:]
            rng.shuffle(shuffled)
            orders.append(shuffled)
        relative = _kuhn_matching(options, orders)
        if relative is not None:
            answer = _denormalise(inst, relative)
            if verify(inst, answer)[0]:
                return answer
    return None


def _attack_dpll(inst: dict, node_cap: int = 50_000) -> tuple[list[int] | None, int]:
    """Cycle-aware exact-cover DPLL with early subtour rejection."""
    finish, options = _normalised_structure(inst)
    n = len(options)
    inv_finish = _inverse(finish)
    assignment = [-1] * n
    used = [False] * n
    succ1 = [-1] * n
    succ2 = [-1] * n
    nodes = 0

    # Static edge scores are label-free local statistics, not construction order.
    incoming = [0] * n
    for row in options:
        for target in row:
            incoming[target] += 1

    def recurse(left: int) -> bool:
        nonlocal nodes
        if nodes >= node_cap:
            return False
        nodes += 1
        if left == 0:
            return True
        assigned = n - left + 1
        best_source = -1
        best_targets: list[int] | None = None
        for source in range(n):
            if assignment[source] >= 0:
                continue
            legal = []
            for target in options[source]:
                if used[target]:
                    continue
                if _creates_small_cycle(succ1, source, target, assigned, n):
                    continue
                if _creates_small_cycle(succ2, inv_finish[target], source, assigned, n):
                    continue
                legal.append(target)
            if not legal:
                return False
            legal.sort(key=lambda target: (incoming[target], target))
            if best_targets is None or (len(legal), source) < (len(best_targets), best_source):
                best_source = source
                best_targets = legal
        assert best_targets is not None
        for target in best_targets:
            assignment[best_source] = target
            used[target] = True
            succ1[best_source] = target
            succ2[inv_finish[target]] = best_source
            if recurse(left - 1):
                return True
            succ2[inv_finish[target]] = -1
            succ1[best_source] = -1
            used[target] = False
            assignment[best_source] = -1
        return False

    solved = recurse(n)
    return (_denormalise(inst, assignment) if solved else None), nodes


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, list[int]]:
    """Independently relabel both shores and reorder every adjacency row."""
    n = inst["n"]
    left = list(range(n))
    right = list(range(n))
    rng.shuffle(left)
    rng.shuffle(right)

    def matching(old: list[int]) -> list[int]:
        new = [0] * n
        for old_left, old_right1 in enumerate(old):
            new[left[old_left]] = right[old_right1 - 1] + 1
        return new

    neighbours = [[] for _ in range(n)]
    for old_left, row in enumerate(inst["neighbours"]):
        neighbours[left[old_left]] = [right[value - 1] + 1 for value in row]
        rng.shuffle(neighbours[left[old_left]])
    transformed = {
        **inst,
        "left_vertices": list(range(1, n + 1)),
        "right_vertices": list(range(1, n + 1)),
        "neighbours": neighbours,
        "start_matching": matching(inst["start_matching"]),
        "finish_matching": matching(inst["finish_matching"]),
    }
    carried = matching(inst["answer"])
    transformed["answer"] = carried
    return transformed, carried


def _find_swap_corruption(inst: dict) -> list[int]:
    answer = inst["answer"][:]
    n = len(answer)
    for i in range(n):
        for j in range(i + 1, n):
            if answer[j] not in inst["neighbours"][i] or answer[i] not in inst["neighbours"][j]:
                answer[i], answer[j] = answer[j], answer[i]
                return answer
    answer[0], answer[1] = answer[1], answer[0]
    return answer


def selftest() -> dict:
    """Run G1--G9 measurements and return a JSON-native gate report."""
    report: dict[str, Any] = {
        "paper": "2210.14608",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named rung, several unrelated seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=37, **ship_params)

    corruptions = {
        "drop": ship["answer"][:-1],
        "swap": _find_swap_corruption(ship),
        "duplicate": ship["answer"][:-1] + [ship["answer"][0]],
        "empty": [],
        "out_of_range": [ship["n"] + 1] + ship["answer"][1:],
    }
    corruption_reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(ship, bad)
        corruption_reasons[name] = {"rejected": not ok, "reason": why}
    distinct_reasons = len({item["reason"] for item in corruption_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_reasons.values()) and distinct_reasons == 5,
        "distinct_reasons": distinct_reasons,
        "cases": corruption_reasons,
    }

    wire = ", ".join(map(str, ship["answer"]))
    realistic = "I used the two relative permutations.\n```text\n<answer>\n" + wire + "\n</answer>\n```"
    parsed = parse_answer(realistic)
    json_roundtrip = json.loads(json.dumps(ship["answer"])) == ship["answer"]
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"] and json_roundtrip,
        "model_style_parsed": parsed == ship["answer"],
        "json_native": json_roundtrip,
    }

    # G4/G5 share a shipping-level, structure-aware Monte Carlo run.
    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(0x221014608)
    t_guess = time.perf_counter()
    for _ in range(guess_total):
        if verify(ship, random_candidate(ship, guess_rng))[0]:
            guess_hits += 1
    guess_sec = time.perf_counter() - t_guess
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "sampler": "uniform n-cycle relative to START; shape, permutation, and first-cycle constraints enforced",
        "search_space": search_space(ship),
        "wall_clock_sec": round(guess_sec, 6),
    }

    t_base = time.perf_counter()
    base_answer, base_nodes = _attack_dpll(ship, node_cap=50_000)
    base_sec = time.perf_counter() - t_base
    base_success = base_answer is not None and verify(ship, base_answer)[0]
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": not base_success,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_probability,
        "shipping_density_upper_95_if_zero": (3.0 / guess_total if guess_hits == 0 else None),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec": round(base_sec, 6),
        "baseline_nodes": base_nodes,
        "baseline_node_budget": 50_000,
        "baseline_solved": base_success,
    }

    attacks = {
        "outlier_local_edge_score": {"successes": 0, "attempts": 8},
        "greedy_dual_no_subtour": {"successes": 0, "attempts": 8},
        "random_restart_matching_128": {"successes": 0, "attempts": 8},
        "cycle_aware_dpll_50000": {"successes": 0, "attempts": 8},
    }
    dpll_nodes = []
    panel_t0 = time.perf_counter()
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **ship_params)
        candidate = _attack_outlier(inst)
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["outlier_local_edge_score"]["successes"] += 1
        candidate = _attack_greedy(inst)
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["greedy_dual_no_subtour"]["successes"] += 1
        candidate = _attack_random_restarts(inst, seed, restarts=128)
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["random_restart_matching_128"]["successes"] += 1
        candidate, nodes = _attack_dpll(inst, node_cap=50_000)
        dpll_nodes.append(nodes)
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["cycle_aware_dpll_50000"]["successes"] += 1
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "standard_algorithm": "cycle-aware exact-cover DPLL with two subtour propagators",
        "dpll_nodes_by_seed": dpll_nodes,
        "panel_wall_clock_sec": round(time.perf_counter() - panel_t0, 6),
    }

    doubled_params = {**ship_params, "n": ship_params["n"] * 2}
    t_scale = time.perf_counter()
    doubled = make_instance(seed=911, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > ship["n"],
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "doubled_vertices": 2 * doubled["n"],
        "doubled_verify_reason": doubled_why,
        "build_and_verify_sec": round(time.perf_counter() - t_scale, 6),
    }

    invariant_checks = 0
    carried_checks = 0
    original_changed = 0
    for seed in range(20):
        inst = make_instance(n=24, decoys=2, seed=1000 + seed)
        transformed, carried = _relabel_instance(inst, random.Random(9000 + seed))
        if canonical_key(inst) == canonical_key(transformed):
            invariant_checks += 1
        if verify(transformed, carried)[0]:
            carried_checks += 1
        if transformed["neighbours"] != inst["neighbours"]:
            original_changed += 1
    unrelated_keys = {
        canonical_key(make_instance(n=24, decoys=2, seed=20_000 + seed))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 20 and carried_checks == 20 and original_changed == 20 and len(unrelated_keys) == 20,
        "invariant_relabellings": invariant_checks,
        "relabelled_instances_changed": original_changed,
        "carried_witnesses_verified": carried_checks,
        "unrelated_distinct_keys": len(unrelated_keys),
        "unrelated_attempts": 20,
        "method": "endpoint-normalised directed colour-refinement invariant",
    }

    answer_json = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_json)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(ship["answer"])
    intended_ops = ship["n"]
    # These are filled from the mandated independent harden.py runs after the
    # oracle evidence exists. Until then, selftest is deliberately not a claim
    # that G9(b) was measured.
    report["G9_no_tool_suitability"] = {
        "pass": False,
        "arms": {
            "bare": {"solved": None, "attempts": 0},
            "hinted": {"solved": None, "attempts": 0},
            "placebo": {"solved": None, "attempts": 0},
        },
        "hinted_minus_placebo": None,
        "hinted_verdict": "not_run",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "within_caps": answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300,
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass", False) for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
