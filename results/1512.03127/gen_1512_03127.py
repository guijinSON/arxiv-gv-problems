"""Inverse generator for positive 1-in-3 SAT instances from arXiv:1512.03127.

The construction is the paper's Section 6 encoding applied to the line graph
of a planted 3-edge-colourable cubic graph.  A witness selects one Boolean
variable from every choice group so that every additional check clause also
contains exactly one selected variable.

The module is standard-library only, performs no I/O at import time, and is
deterministic from ``(n, seed, params)``.
"""

from __future__ import annotations

from collections import Counter, deque
import hashlib
import itertools
import json
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 8, "min_girth": 4},
    "easy": {"n": 12, "min_girth": 5},
    "medium": {"n": 200, "min_girth": 5},
    "hard": {"n": 280, "min_girth": 5},
    "extreme": {"n": 360, "min_girth": 5},
}
SHIPPING_DIFFICULTY = "medium"


NOTES = r"""
Definition source: Section 1 of Marcel Jackson, "Flexible constraint
satisfiability and a problem in semigroup theory" (arXiv:1512.03127), defines
positive 1-in-3SAT using the Boolean ternary relation
{(1,0,0),(0,1,0),(0,0,1)}.  Section 3 fixes "locally compatible" and
<=k-robust satisfaction.  Section 6, especially the A2/B2 construction and
Theorems 6.1--6.2, is the exact encoding used here: one A2 clause chooses one
colour for each graph vertex, and one B2 clause makes each colour occur once
on every triangle.  Theorem 6.2 proves NP-hardness for a class ranging from
the robust positive instances to all satisfiable positive 1-in-3 instances.

The source graph here is the line graph of a connected, simple cubic graph.
The cubic graph is sampled as the union of three independently and identically
distributed perfect matchings, so those matchings are a planted 3-edge-colour
witness.  Requiring girth at least five makes the line graph's triangles
exactly the stars of the cubic graph; hence every line-graph edge lies in
exactly one triangle, the regime highlighted in Sections 5 and 6.  The search
task is equivalently 3-edge-colouring a cubic graph, which is NP-complete
(Holyer, SIAM J. Comput. 10 (1981), 718--720).  Kaminski and Lozin,
"Coloring edges and vertices of graphs without short or long cycles"
(Contrib. Discrete Math. 2 (2007), Theorem 2.1), further prove NP-hardness for
cubic graphs of any fixed minimum girth, so the girth-five filter stays inside
a formally hard worst-case regime.  These results do not prove that every
planted random draw is hard.

Easy regimes deliberately avoided: Section 3, Proposition 3.2 explains that
fixed-level robustness over a template with tractable CSP is tractable (the
paper gives 2-colouring as an example), so hardness comes from the positive
1-in-3/K3 templates rather than robustness alone.  Disconnected formulas split
into smaller searches; cubic bipartite graphs have polynomial-time 3-edge
colouring; and short cycles give conspicuous alternating-cycle repairs.  The
shipping instances are connected, non-bipartite in practice, and have girth at
least five.  The generator never asks a solver to certify robustness; its
witness is an ordinary satisfying assignment, checked by direct substitution.

Plant and decoys have the same public statistics.  Each SAT variable occurs in
one choice group and two check clauses, every clause has size three, all numeric
variable names are globally shuffled, and the three planted matchings are
sampled symmetrically.  The outlier attack therefore has no degree/frequency
signal.  The adversary panel also tests left-to-right least-conflict greedy
colouring and min-conflicts random restarts.  The paper's A2 groups are exposed
to the solver, so random_candidate uses the honest structure-aware prior: one
uniform choice from each group, not a uniform subset of all variables.

Exact graph isomorphism is not known to have a simple polynomial canonical
form.  canonical_key reconstructs the underlying cubic graph and hashes a
strong relabelling-invariant combination of all-pairs distance profiles and
root-individualised colour refinement.  It is invariant under every public
reordering/renaming tested here and separates the sampled instances, but it is
not claimed to be a complete isomorphism invariant for adversarial graphs.
""".strip()


def _perfect_matching(n: int, rng: random.Random) -> list[tuple[int, int]]:
    vertices = list(range(n))
    rng.shuffle(vertices)
    return [tuple(sorted((vertices[i], vertices[i + 1])))
            for i in range(0, n, 2)]


def _adjacency(n: int, edges: list[tuple[int, int]]) -> list[set[int]]:
    adj = [set() for _ in range(n)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _connected_with_girth(
    n: int, edges: list[tuple[int, int]], min_girth: int
) -> bool:
    """Check connectedness and reject every cycle shorter than min_girth."""
    adj = _adjacency(n, edges)
    if any(len(row) != 3 for row in adj):
        return False

    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    if len(seen) != n:
        return False

    for start in range(n):
        distance = [-1] * n
        parent = [-1] * n
        distance[start] = 0
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if distance[v] < 0:
                    distance[v] = distance[u] + 1
                    parent[v] = u
                    queue.append(v)
                elif parent[u] != v:
                    if distance[u] + distance[v] + 1 < min_girth:
                        return False
    return True


def _is_bipartite(n: int, edges: list[tuple[int, int]]) -> bool:
    adj = _adjacency(n, edges)
    colours = [-1] * n
    for start in range(n):
        if colours[start] >= 0:
            continue
        colours[start] = 0
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if colours[v] < 0:
                    colours[v] = 1 - colours[u]
                    queue.append(v)
                elif colours[v] == colours[u]:
                    return False
    return True


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Plant a 3-edge-colouring first, then build the Section 6 formula.

    ``n`` is the even number of vertices in the hidden cubic graph.  It creates
    ``3*n/2`` choice groups and ``9*n/2`` Boolean variables.  Larger ``n``
    strictly increases both the witness length and the structure-aware search
    space.  ``min_girth`` defaults to 5; the value 4 is useful only for the
    small exact-enumeration control in selftest().
    """
    min_girth = params.pop("min_girth", 5)
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if (not isinstance(min_girth, int) or isinstance(min_girth, bool)
            or min_girth < 4 or min_girth > 6):
        raise ValueError("min_girth must be an integer from 4 through 6")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)

    # Each proposal samples the witness first: colour c is a uniform perfect
    # matching.  The acceptance conditions are symmetric in the three colours.
    coloured_edges: list[tuple[int, int, int]] | None = None
    attempts = 0
    for attempts in range(1, 200_001):
        matchings = [_perfect_matching(n, rng) for _ in range(3)]
        proposal = [(u, v, colour)
                    for colour, matching in enumerate(matchings)
                    for u, v in matching]
        plain_edges = [(u, v) for u, v, _ in proposal]
        if len(set(plain_edges)) != len(plain_edges):
            continue
        if not _connected_with_girth(n, plain_edges, min_girth):
            continue
        if _is_bipartite(n, plain_edges):
            continue
        coloured_edges = proposal
        break
    if coloured_edges is None:
        raise RuntimeError("could not sample a connected planted cubic graph")

    # Erase matching order and all construction labels before exposing clauses.
    rng.shuffle(coloured_edges)
    edge_count = len(coloured_edges)
    variable_count = 3 * edge_count
    variable_names = list(range(variable_count))
    rng.shuffle(variable_names)
    var_for = [[0, 0, 0] for _ in range(edge_count)]
    cursor = 0
    for edge_index in range(edge_count):
        for colour in range(3):
            var_for[edge_index][colour] = variable_names[cursor]
            cursor += 1

    incident: list[list[int]] = [[] for _ in range(n)]
    answer: list[int] = []
    for edge_index, (u, v, planted_colour) in enumerate(coloured_edges):
        incident[u].append(edge_index)
        incident[v].append(edge_index)
        answer.append(var_for[edge_index][planted_colour])

    groups = [row[:] for row in var_for]
    for group in groups:
        rng.shuffle(group)
    checks: list[list[int]] = []
    for vertex in range(n):
        if len(incident[vertex]) != 3:
            raise RuntimeError("internal cubic-degree invariant failed")
        for colour in range(3):
            clause = [var_for[e][colour] for e in incident[vertex]]
            rng.shuffle(clause)
            checks.append(clause)
    rng.shuffle(groups)
    rng.shuffle(checks)

    return {
        "family": "positive_1_in_3_line_graph",
        "n": n,
        "min_girth": min_girth,
        "num_variables": variable_count,
        "choice_groups": groups,
        "check_clauses": checks,
        "answer": sorted(answer),
        "construction_attempts": attempts,
    }


def render(inst: dict) -> str:
    """Render the complete positive 1-in-3 witness problem."""
    groups = inst["choice_groups"]
    checks = inst["check_clauses"]
    group_lines = "\n".join(
        f"G{i}: {a} {b} {c}" for i, (a, b, c) in enumerate(groups)
    )
    check_lines = "\n".join(
        f"C{i}: {a} {b} {c}" for i, (a, b, c) in enumerate(checks)
    )
    example_count = len(groups)
    return f"""Positive 1-in-3 Boolean witness problem

There are {inst['num_variables']} Boolean variables numbered 0 through
{inst['num_variables'] - 1} inclusive.  Your answer is the set of variables
assigned TRUE; every variable not listed is assigned FALSE.

A triple is satisfied when exactly one of its three distinct variable numbers
is TRUE.  "Exactly one" means one, not zero and not two or three.  The choice
groups below partition all variables.  Select exactly one variable from every
choice group, and also make every check clause contain exactly one selected
variable.

CHOICE GROUPS ({len(groups)} triples)
{group_lines}

CHECK CLAUSES ({len(checks)} triples)
{check_lines}

Return exactly {example_count} distinct integers.  Variable numbering is
0-based, order does not matter, and repeated numbers are forbidden.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {example_count} variable numbers.
Example syntax: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
"""


_ANSWER_BLOCK = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def parse_answer(text: str) -> object | None:
    """Extract the final tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_BLOCK.findall(text)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return None
    if re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body) is None:
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any satisfying witness by exact substitution; never read the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a list of integer variable IDs"
    if not answer:
        return False, "answer is empty"
    expected = len(inst["choice_groups"])
    if len(answer) != expected:
        return False, f"wrong number of selected variables: expected {expected}"
    if any(not isinstance(value, int) or isinstance(value, bool) for value in answer):
        return False, "selected variable IDs must all be integers"
    limit = inst["num_variables"]
    for value in answer:
        if value < 0 or value >= limit:
            return False, f"variable {value} is outside the inclusive range 0..{limit - 1}"
    if len(set(answer)) != len(answer):
        return False, "duplicate variable IDs are not allowed"

    selected = set(answer)
    for index, group in enumerate(inst["choice_groups"]):
        if sum(value in selected for value in group) != 1:
            return False, f"choice-group exact-one rule violated at group {index}"
    for index, clause in enumerate(inst["check_clauses"]):
        if sum(value in selected for value in clause) != 1:
            return False, f"check-clause exact-one rule violated at clause {index}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly choose one variable per public choice group.

    This satisfies the answer shape, distinctness, length, and every A2/choice
    constraint that a solver gets for free.  Only the cross-group check clauses
    remain, so this is the structure-aware space of size 3**group_count.
    """
    return sorted(rng.choice(group) for group in inst["choice_groups"])


def search_space(inst: dict) -> int | None:
    """Return the structure-aware one-choice-per-group candidate count."""
    if any(len(group) != 3 for group in inst["choice_groups"]):
        return None
    return 3 ** len(inst["choice_groups"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid witnesses when at most one million candidates are needed."""
    space = search_space(inst)
    if space is None or space > 1_000_000:
        return None
    count = 0
    groups = inst["choice_groups"]
    checks = inst["check_clauses"]
    for choices in itertools.product(*(range(len(group)) for group in groups)):
        selected = {groups[i][choice] for i, choice in enumerate(choices)}
        if all(sum(value in selected for value in clause) == 1 for clause in checks):
            count += 1
    return count


def _recover_cubic_graph(inst: dict) -> list[set[int]]:
    """Reconstruct the hidden cubic graph using only the public clauses."""
    variable_count = inst["num_variables"]
    group_of = [-1] * variable_count
    for group_index, group in enumerate(inst["choice_groups"]):
        for value in group:
            if value < 0 or value >= variable_count or group_of[value] != -1:
                raise ValueError("choice groups do not partition the variables")
            group_of[value] = group_index
    if any(value < 0 for value in group_of):
        raise ValueError("choice groups do not cover every variable")

    support_counts: Counter[tuple[int, int, int]] = Counter()
    for clause in inst["check_clauses"]:
        support = tuple(sorted(group_of[value] for value in clause))
        if len(set(support)) != 3:
            raise ValueError("a check clause repeats a choice group")
        support_counts[support] += 1
    if any(count != 3 for count in support_counts.values()):
        raise ValueError("check supports do not occur in triples")

    supports = sorted(support_counts)
    containing: list[list[int]] = [[] for _ in inst["choice_groups"]]
    for vertex, support in enumerate(supports):
        for group_index in support:
            containing[group_index].append(vertex)
    adj = [set() for _ in supports]
    for endpoints in containing:
        if len(endpoints) != 2 or endpoints[0] == endpoints[1]:
            raise ValueError("a choice group does not connect two reconstructed vertices")
        u, v = endpoints
        if v in adj[u]:
            raise ValueError("reconstructed cubic graph has parallel edges")
        adj[u].add(v)
        adj[v].add(u)
    if any(len(row) != 3 for row in adj):
        raise ValueError("reconstructed graph is not cubic")
    return adj


def _distance_shells(adj: list[set[int]], start: int) -> tuple[int, ...]:
    distance = [-1] * len(adj)
    distance[start] = 0
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if distance[v] < 0:
                distance[v] = distance[u] + 1
                queue.append(v)
    counts = Counter(distance)
    return tuple(counts[d] for d in range(max(distance) + 1))


def _rooted_refinement(adj: list[set[int]], root: int) -> tuple:
    """A canonical root-individualised 1-WL quotient signature."""
    colours = [1 if vertex == root else 0 for vertex in range(len(adj))]
    for _ in range(len(adj)):
        signatures = [
            (colours[v], tuple(sorted(colours[w] for w in adj[v])))
            for v in range(len(adj))
        ]
        palette = {signature: colour
                   for colour, signature in enumerate(sorted(set(signatures)))}
        new_colours = [palette[signature] for signature in signatures]
        if len(set(new_colours)) == len(set(colours)):
            colours = new_colours
            break
        colours = new_colours

    classes: dict[int, list[int]] = {}
    for vertex, colour in enumerate(colours):
        classes.setdefault(colour, []).append(vertex)
    quotient = []
    for colour in sorted(classes):
        representative = classes[colour][0]
        quotient.append((len(classes[colour]),
                         tuple(sorted(colours[w] for w in adj[representative]))))
    return tuple(quotient)


def canonical_key(inst: dict) -> str:
    """Return a strong cheap invariant of the underlying unlabeled cubic graph.

    Variable renaming, ordering within triples, and ordering of either clause
    list are discarded.  This is intentionally an invariant rather than a
    claimed complete graph-isomorphism canonical form; see NOTES/README.
    """
    adj = _recover_cubic_graph(inst)
    payload = {
        "vertices": len(adj),
        "distance_shells": sorted(_distance_shells(adj, v) for v in range(len(adj))),
        "rooted_refinement": sorted(_rooted_refinement(adj, v) for v in range(len(adj))),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return "cubic-invariant-v1:" + hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Add 80 cubic vertices, preserving the structural girth filter."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = params["n"]
    if not isinstance(n, int) or n >= 1024:
        return None
    out = dict(params)
    out["n"] = n + 80
    if out["n"] % 2:
        out["n"] += 1
    return out


def _variable_checks(inst: dict) -> list[list[int]]:
    memberships = [[] for _ in range(inst["num_variables"])]
    for clause_index, clause in enumerate(inst["check_clauses"]):
        for value in clause:
            memberships[value].append(clause_index)
    return memberships


def _attack_outlier(inst: dict) -> list[int]:
    """Pick the smallest numeric label in each statistically identical group."""
    return sorted(min(group) for group in inst["choice_groups"])


def _attack_left_to_right_greedy(inst: dict) -> list[int]:
    """Satisfy groups in displayed order, minimizing immediate check conflicts."""
    memberships = _variable_checks(inst)
    counts = [0] * len(inst["check_clauses"])
    selected = []
    for group in inst["choice_groups"]:
        def score(value: int) -> tuple[int, int, int]:
            conflicts = sum(counts[index] > 0 for index in memberships[value])
            occupied = sum(counts[index] for index in memberships[value])
            return conflicts, occupied, value

        choice = min(group, key=score)
        selected.append(choice)
        for index in memberships[choice]:
            counts[index] += 1
    return sorted(selected)


def _check_violation_count(inst: dict, selected: set[int]) -> int:
    return sum(sum(value in selected for value in clause) != 1
               for clause in inst["check_clauses"])


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 32, moves_per_group: int = 30
) -> list[int] | None:
    """Mild min-conflicts search constrained to one choice per group."""
    groups = inst["choice_groups"]
    group_of = {}
    for group_index, group in enumerate(groups):
        for value in group:
            group_of[value] = group_index
    checks = inst["check_clauses"]
    memberships = _variable_checks(inst)

    for _ in range(restarts):
        chosen = [rng.choice(group) for group in groups]
        selected = set(chosen)
        counts = [sum(value in selected for value in clause) for clause in checks]
        bad = {index for index, count in enumerate(counts) if count != 1}
        for _ in range(moves_per_group * len(groups)):
            if not bad:
                return sorted(selected)
            clause_index = rng.choice(tuple(bad))
            clause = checks[clause_index]
            candidate_groups = sorted({group_of[value] for value in clause})
            group_index = rng.choice(candidate_groups)
            old = chosen[group_index]
            trials = []
            for new in groups[group_index]:
                if new == old:
                    continue
                affected = set(memberships[old]) | set(memberships[new])
                before = sum(counts[index] != 1 for index in affected)
                after = 0
                for index in affected:
                    count = counts[index]
                    if index in memberships[old]:
                        count -= 1
                    if index in memberships[new]:
                        count += 1
                    after += count != 1
                trials.append((len(bad) - before + after, rng.random(), new))
            best_score, _, new = min(trials)
            # A small sideways/noisy component prevents a deterministic local
            # minimum from making every restart identical.
            if best_score <= len(bad) or rng.random() < 0.03:
                affected = set(memberships[old]) | set(memberships[new])
                selected.remove(old)
                selected.add(new)
                chosen[group_index] = new
                for index in affected:
                    if index in memberships[old]:
                        counts[index] -= 1
                    if index in memberships[new]:
                        counts[index] += 1
                    if counts[index] == 1:
                        bad.discard(index)
                    else:
                        bad.add(index)
        if not bad:
            return sorted(selected)
    return None


def _copy_public(inst: dict) -> dict:
    return {
        key: ([row[:] for row in value]
              if key in ("choice_groups", "check_clauses") else value)
        for key, value in inst.items()
        if key != "answer"
    }


def _transformed_instance(inst: dict, mode: str, salt: int) -> dict:
    rng = random.Random(0x151203127 + salt)
    out = _copy_public(inst)
    answer = list(inst["answer"])

    if mode in ("variable_relabel", "combined"):
        permutation = list(range(inst["num_variables"]))
        rng.shuffle(permutation)
        out["choice_groups"] = [
            [permutation[value] for value in group]
            for group in out["choice_groups"]
        ]
        out["check_clauses"] = [
            [permutation[value] for value in clause]
            for clause in out["check_clauses"]
        ]
        answer = [permutation[value] for value in answer]

    if mode in ("member_reorder", "combined"):
        for row in out["choice_groups"]:
            rng.shuffle(row)
        for row in out["check_clauses"]:
            rng.shuffle(row)

    if mode in ("input_reorder", "combined"):
        rng.shuffle(out["choice_groups"])
        rng.shuffle(out["check_clauses"])

    out["answer"] = sorted(answer)
    return out


def selftest() -> dict:
    """Run mandatory gates G1--G8 and return their measured report."""
    report: dict[str, Any] = {}

    # G1: every preset and several seeds.
    g1_failures = []
    g1_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)

    # G2: five corruptions with five distinct diagnostics.
    answer = list(inst["answer"])
    dropped = answer[:-1]
    duplicate = answer[:]
    duplicate[0] = duplicate[1]
    out_of_range = answer[:]
    out_of_range[0] = inst["num_variables"]
    swapped = answer[:]
    selected = set(answer)
    first_group = inst["choice_groups"][0]
    second_group = inst["choice_groups"][1]
    old = next(value for value in first_group if value in selected)
    replacement = next(value for value in second_group if value not in selected)
    swapped[swapped.index(old)] = replacement
    corruptions = {
        "drop_one": dropped,
        "swap_one_selection": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    g2_results = {name: verify(inst, candidate)
                  for name, candidate in corruptions.items()}
    reasons = [reason for ok, reason in g2_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (all(not ok for ok, _ in g2_results.values())
                 and len(set(reasons)) == len(g2_results)),
        "cases": {name: {"rejected": not ok, "reason": reason}
                  for name, (ok, reason) in g2_results.items()},
        "distinct_reasons": len(set(reasons)),
    }

    # G3: prose, a Markdown fence, whitespace, and the exact tagged format.
    body = ", ".join(map(str, inst["answer"]))
    model_reply = ("I checked every exact-one clause.\n\n```text\n<answer>\n"
                   + body + "\n</answer>\n```\nThat is my final witness.")
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_equal": parsed == inst["answer"],
    }

    # G4: one uniform choice per public A2 group, never the naive bit-vector prior.
    guess_rng = random.Random(0x151203127)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": hits / total,
        "prior": "uniform one-of-three choice independently in every public choice group",
        "structure_aware_search_space": search_space(inst),
        "unconstrained_bit_vector_space": 2 ** inst["num_variables"],
    }

    # G5: n=8 permits complete enumeration of the same construction (girth 4).
    tiny = make_instance(n=8, seed=7, min_girth=4)
    tiny_count = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    fraction = None if tiny_count is None else tiny_count / tiny_space
    report["G5_sparse"] = {
        "pass": (tiny_count is not None and fraction is not None and fraction < 0.001),
        "control_n": 8,
        "enumerated_solutions": tiny_count,
        "structure_aware_search_space": tiny_space,
        "solution_fraction": fraction,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: planting-aware per-variable, greedy, and random-restart attacks.
    attack_rows: dict[str, list[dict[str, Any]]] = {
        "degree_frequency_outlier": [],
        "left_to_right_greedy": [],
        "min_conflicts_random_restart": [],
    }
    for seed in range(8):
        attacked = make_instance(seed=10_000 + seed, **ship_params)
        memberships = _variable_checks(attacked)
        public_signatures = {
            (1, len(memberships[value]))
            for value in range(attacked["num_variables"])
        }
        outlier_ok, _ = verify(attacked, _attack_outlier(attacked))
        greedy_ok, _ = verify(attacked, _attack_left_to_right_greedy(attacked))
        restart_answer = _attack_random_restarts(
            attacked, random.Random(90_000 + seed), restarts=16,
            moves_per_group=10,
        )
        restart_ok = (restart_answer is not None
                      and verify(attacked, restart_answer)[0])
        attack_rows["degree_frequency_outlier"].append({
            "seed": seed,
            "solved": outlier_ok,
            "distinct_public_degree_signatures": len(public_signatures),
            "signature": sorted(public_signatures),
        })
        attack_rows["left_to_right_greedy"].append({
            "seed": seed, "solved": greedy_ok,
        })
        attack_rows["min_conflicts_random_restart"].append({
            "seed": seed, "solved": restart_ok,
            "restarts": 16, "moves_per_group": 10,
        })
    attack_summary = {}
    for name, rows in attack_rows.items():
        attack_summary[name] = {
            "successes": sum(bool(row["solved"]) for row in rows),
            "seeds": len(rows),
            "runs": rows,
        }
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attack_summary.values()),
        "attacks": attack_summary,
    }

    # G7: doubling n doubles the witness length/exponent of the candidate space.
    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and len(doubled["choice_groups"]) == 2 * len(inst["choice_groups"])
                 and search_space(doubled) == search_space(inst) ** 2),
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "base_witness_length": len(inst["choice_groups"]),
        "doubled_witness_length": len(doubled["choice_groups"]),
        "base_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "planted_verify": doubled_ok,
        "verify_reason": doubled_reason,
    }

    # G8: all public relabellings/reorderings, their composition, and real witnesses.
    modes = ("variable_relabel", "member_reorder", "input_reorder", "combined")
    invariance_checks = 0
    real_transform_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **ship_params)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        for mode in modes:
            moved = _transformed_instance(base, mode, seed)
            invariance_checks += 1
            if canonical_key(moved) != base_key:
                failures.append({"seed": seed, "mode": mode, "kind": "key_changed"})
            ok, reason = verify(moved, moved["answer"])
            real_transform_checks += 1
            if not ok:
                failures.append({
                    "seed": seed, "mode": mode,
                    "kind": "carried_witness_failed", "reason": reason,
                })
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "transformations": list(modes),
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": failures,
        "caveat": "strong invariant, not a complete graph-isomorphism canonical form",
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
