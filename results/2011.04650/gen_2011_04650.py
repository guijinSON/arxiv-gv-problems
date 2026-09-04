"""Planted full rainbow matchings for arXiv:2011.04650.

The displayed object is a properly edge-coloured bipartite multigraph.  Treating
an edge (colour, left endpoint, right endpoint) as a triple makes a full rainbow
matching exactly a perfect matching in a 3-partite, 3-uniform hypergraph.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter
from itertools import permutations


DIFFICULTY = {
    "demo": {"n": 4, "choices": 2},
    "easy": {"n": 10, "choices": 3},
    "medium": {"n": 32, "choices": 5},
    "hard": {"n": 56, "choices": 5},
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper grounding.  Section 1 of Chakraborti--Loh, arXiv:2011.04650,
defines a rainbow matching as a matching whose edge colours are pairwise
distinct; it also specifies that multigraphs may have parallel edges but not
loops, and that a proper edge-colouring gives incident edges different colours.
The requested witness uses exactly that object.  An edge c-l-r is viewed as the
triple (colour c, left vertex l, right vertex r), so using every colour and every
endpoint once is the standard 3-dimensional matching formulation.

Hard and easy regimes.  General RAINBOW MATCHING is NP-complete already on
edge-coloured bipartite graphs (Le and Pfender, arXiv:1312.7253, Theorem 1), and
their Theorem 8 gives APX-completeness even for properly edge-coloured P4-free
bipartite graphs with each colour used at most twice.
Their Section 5 also observes fixed-parameter tractability in the requested
matching size, so this generator makes that size n grow.  The source paper's
easy-density warnings are Proposition 2.4 and Theorem 1.7/Section 4: many more
edges per colour than the maximum degree permit local-lemma/nibble construction.
Here each colour has exactly d edges and the maximum degree is exactly d, with
no slack at all.  Theorem 1.9's roughly 2n-colour guarantee is also avoided:
there are exactly n colours and the target size is n.

Inverse generation and attacks.  A random perfect rainbow layer is sampled
first.  The remaining d-1 layers are drawn by the same permutation mechanism;
each is itself a decoy solution, so every displayed edge participates in a
known valid solution and plants cannot be singled out by degree or frequency.
All colour, left, and right degrees are exactly d.  The outlier attack ranks
individual edges by endpoint-pair multiplicity, the deterministic greedy attack
uses minimum remaining values plus least conflict, and the restart attack makes
256 randomised least-conflict attempts.  The preliminary (n=36,d=4) rung was
rejected after restarts solved 1/8 gate seeds; increasing crowding to d=5 at
n=32 defeated all three attacks.  selftest records them across eight shipping
seeds.  The worst-case NP-completeness result does not prove average-
case hardness for this resolvable random distribution; the oracle loop and
adversary panel are the empirical checks for that caveat.
"""


def _avoiding_permutation(n, forbidden, rng):
    """Draw a permutation p with p[i] outside forbidden[i]."""
    values = list(range(n))
    # Rejection is quick for the shipped d <= 4: its limiting acceptance
    # probability is about exp(-len(forbidden[0])).
    for _ in range(20_000):
        rng.shuffle(values)
        if all(values[i] not in forbidden[i] for i in range(n)):
            return list(values)
    raise RuntimeError("could not draw a forbidden-position permutation")


def _edges_by_color(inst):
    rows = [[] for _ in range(inst["n"])]
    for edge in inst["edges"]:
        rows[edge[0]].append(tuple(edge))
    for row in rows:
        row.sort()
    return rows


def make_instance(n, seed=0, **params):
    """Sample a full rainbow matching first, then add matched decoy layers."""
    choices = params.pop("choices", 4)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if (isinstance(choices, bool) or not isinstance(choices, int)
            or choices < 2 or choices > n):
        raise ValueError("choices must be an integer in the inclusive range 2..n")

    rng = random.Random(seed)

    # G: this layer, and therefore the complete witness, exists before a decoy
    # is drawn.  Both endpoint maps are uniform random permutations.
    planted_left = list(range(n))
    planted_right = list(range(n))
    rng.shuffle(planted_left)
    rng.shuffle(planted_right)
    answer = [[c, planted_left[c], planted_right[c]] for c in range(n)]

    left_layers = [planted_left]
    right_layers = [planted_right]
    left_used = [{planted_left[c]} for c in range(n)]
    right_used = [{planted_right[c]} for c in range(n)]

    # Every decoy layer has precisely the same global shape as the plant: it is
    # a full rainbow perfect matching.  Avoiding repeated c-l and c-r pairs
    # makes every colour class a matching, hence the edge-colouring is proper.
    for _ in range(1, choices):
        left = _avoiding_permutation(n, left_used, rng)
        right = _avoiding_permutation(n, right_used, rng)
        left_layers.append(left)
        right_layers.append(right)
        for c in range(n):
            left_used[c].add(left[c])
            right_used[c].add(right[c])

    edges = []
    for layer in range(choices):
        edges.extend([[c, left_layers[layer][c], right_layers[layer][c]]
                      for c in range(n)])
    rng.shuffle(edges)

    return {
        "n": n,
        "choices": choices,
        "edges": edges,
        "answer": answer,
    }


def render(inst):
    """Return the complete standalone problem and exact output contract."""
    n = inst["n"]
    rows = "\n".join(f"{c} {left} {right}"
                     for c, left, right in inst["edges"])
    return f"""Find a full rainbow matching in a coloured bipartite multigraph

There are three separately labelled sets, each of size {n}:
- colours 0 through {n - 1};
- left vertices L0 through L{n - 1}; and
- right vertices R0 through R{n - 1}.

Each input line `c l r` is one edge from left vertex Ll to right vertex Rr,
with colour c.  All labels are 0-indexed and both bounds are inclusive.
Different colours may give parallel edges with the same endpoints.  No exact
triple is repeated.  The order of the input lines has no meaning.

Choose exactly {n} listed triples so that every colour occurs exactly once,
every left vertex occurs exactly once, and every right vertex occurs exactly
once.  Thus the chosen edges are pairwise vertex-disjoint and have pairwise
distinct colours.  The order of your chosen triples has no meaning, and you
may not repeat a triple.

The {len(inst['edges'])} input edges are:
{rows}

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly {n} triples `[c,l,r]` using decimal integers.
Example of the syntax: <answer>[[0,2,1],[1,0,3]]</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>",
                        re.IGNORECASE | re.DOTALL)


def parse_answer(text):
    """Extract a JSON list of triples from prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            body = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    for edge in value:
        if (not isinstance(edge, list) or len(edge) != 3
                or any(isinstance(x, bool) or not isinstance(x, int)
                       for x in edge)):
            return None
    return value


def verify(inst, answer):
    """Check any full rainbow matching; never inspect inst['answer']."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of edge triples"
    if len(answer) == 0:
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) != n:
        return False, f"wrong number of edges: expected {n}"
    for edge in answer:
        if not isinstance(edge, (list, tuple)) or len(edge) != 3:
            return False, "each selected edge must be a triple [c,l,r]"
        if any(isinstance(x, bool) or not isinstance(x, int) for x in edge):
            return False, "every entry in every triple must be an integer"
    if any(x < 0 or x >= n for edge in answer for x in edge):
        return False, f"a label is outside the inclusive range 0..{n - 1}"

    triples = [tuple(edge) for edge in answer]
    if len(set(triples)) != n:
        return False, "a selected edge triple is duplicated"
    available = {tuple(edge) for edge in inst["edges"]}
    if any(edge not in available for edge in triples):
        return False, "a selected triple is not an input edge"

    colours = [edge[0] for edge in triples]
    left = [edge[1] for edge in triples]
    right = [edge[2] for edge in triples]
    if len(set(colours)) != n:
        return False, "a colour is repeated"
    if len(set(left)) != n:
        return False, "a left endpoint is repeated"
    if len(set(right)) != n:
        return False, "a right endpoint is repeated"
    return True, "ok"


def random_candidate(inst, rng):
    """Choose one real edge of every colour, the strongest free structure."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    candidate = [list(rng.choice(row)) for row in _edges_by_color(inst)]
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    """Number of candidates after enforcing one listed edge per colour."""
    total = 1
    for row in _edges_by_color(inst):
        total *= len(row)
    return total


def enumerate_all(inst):
    """Count all full rainbow matchings when bounded search stays small."""
    rows = _edges_by_color(inst)
    if search_space(inst) > 300_000:
        return None
    nodes = 0
    aborted = False

    def visit(remaining, used_left, used_right):
        nonlocal nodes, aborted
        nodes += 1
        if nodes > 500_000:
            aborted = True
            return 0
        if not remaining:
            return 1
        feasible = {
            c: [edge for edge in rows[c]
                if edge[1] not in used_left and edge[2] not in used_right]
            for c in remaining
        }
        c = min(remaining, key=lambda color: (len(feasible[color]), color))
        if not feasible[c]:
            return 0
        rest = tuple(x for x in remaining if x != c)
        total = 0
        for edge in feasible[c]:
            total += visit(rest, used_left | {edge[1]},
                           used_right | {edge[2]})
            if aborted:
                return 0
        return total

    count = visit(tuple(range(inst["n"])), set(), set())
    return None if aborted else count


def _incidence_adjacency(inst):
    n = inst["n"]
    offset = 3 * n
    size = offset + len(inst["edges"])
    adj = [[] for _ in range(size)]
    for i, (c, left, right) in enumerate(inst["edges"]):
        e = offset + i
        for v in (c, n + left, 2 * n + right):
            adj[e].append(v)
            adj[v].append(e)
    return adj


def _rooted_certificate(inst, adj, root, role_map):
    """Rooted colour-refinement quotient of the tripartite incidence graph."""
    n = inst["n"]
    roles = []
    for v in range(len(adj)):
        if v < n:
            role = role_map[0]
        elif v < 2 * n:
            role = role_map[1]
        elif v < 3 * n:
            role = role_map[2]
        else:
            role = 3
        roles.append(role)
    initial = [(roles[v], int(v == root)) for v in range(len(adj))]
    kinds = {sig: i for i, sig in enumerate(sorted(set(initial)))}
    colours = [kinds[sig] for sig in initial]
    history = []
    for _ in range(min(len(adj) + 1, 12)):
        signatures = [
            (colours[v], tuple(sorted(colours[u] for u in adj[v])))
            for v in range(len(adj))
        ]
        kinds = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_colours = [kinds[sig] for sig in signatures]
        counts = tuple(Counter(new_colours)[i]
                       for i in range(max(new_colours) + 1))
        history.append(counts)
        if new_colours == colours:
            colours = new_colours
            break
        colours = new_colours

    classes = max(colours) + 1
    class_roles = [[] for _ in range(classes)]
    for v, colour in enumerate(colours):
        class_roles[colour].append(roles[v])
    role_profile = tuple(tuple(sorted(values)) for values in class_roles)
    quotient = [[0] * classes for _ in range(classes)]
    for v, row in enumerate(adj):
        for u in row:
            if v < u:
                a, b = sorted((colours[v], colours[u]))
                quotient[a][b] += 1
    flat_quotient = tuple(quotient[a][b]
                          for a in range(classes) for b in range(a, classes))
    return tuple(history), role_profile, flat_quotient


def canonical_key(inst):
    """Strong cheap invariant under all label, side, and input permutations.

    Exact tripartite-hypergraph canonical labelling is not attempted.  The key
    is the smallest sorted rooted colour-refinement deck over all six
    permutations of the colour/left/right roles.  Nonisomorphic graphs that
    colour refinement cannot distinguish may therefore collide.
    """
    adj = _incidence_adjacency(inst)
    decks = []
    n = inst["n"]
    for role_map in permutations(range(3)):
        rooted_group = role_map.index(0)
        roots = range(rooted_group * n, (rooted_group + 1) * n)
        deck = tuple(sorted(_rooted_certificate(inst, adj, root, role_map)
                            for root in roots))
        decks.append(deck)
    structural = (inst["n"], len(inst["edges"]), min(decks))
    return hashlib.sha256(repr(structural).encode("utf-8")).hexdigest()


def escalate(params):
    """Increase the growing witness/search dimension, keeping density fixed."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    choices = int(params.get("choices", 4))
    if n >= 128:
        return None
    return {"n": min(128, max(n + 1, math.ceil(1.6 * n))),
            "choices": choices}


def _complete_with_first(rows, partial, remaining):
    result = list(partial)
    for c in sorted(remaining):
        result.append(rows[c][0])
    return [list(edge) for edge in result]


def _attack_outlier(inst):
    """Pick the locally rarest-looking edge of each colour independently."""
    rows = _edges_by_color(inst)
    pair_count = Counter((left, right)
                         for _, left, right in map(tuple, inst["edges"]))
    result = []
    for row in rows:
        edge = min(row, key=lambda e: (pair_count[(e[1], e[2])],
                                      e[1] + e[2], e))
        result.append(edge)
    return [list(edge) for edge in result]


def _feasible_by_colour(rows, remaining, used_left, used_right):
    return {
        c: [edge for edge in rows[c]
            if edge[1] not in used_left and edge[2] not in used_right]
        for c in remaining
    }


def _blocking_score(edge, feasible, chosen_colour):
    return sum(1 for c, row in feasible.items() if c != chosen_colour
               for other in row
               if other[1] == edge[1] or other[2] == edge[2])


def _attack_greedy(inst):
    """Minimum remaining values, then a deterministic least-conflict edge."""
    rows = _edges_by_color(inst)
    remaining = set(range(inst["n"]))
    used_left, used_right = set(), set()
    selected = []
    while remaining:
        feasible = _feasible_by_colour(rows, remaining,
                                       used_left, used_right)
        c = min(remaining, key=lambda x: (len(feasible[x]), x))
        if not feasible[c]:
            return _complete_with_first(rows, selected, remaining)
        edge = min(feasible[c], key=lambda e: (_blocking_score(e, feasible, c),
                                               e[1], e[2]))
        selected.append(edge)
        used_left.add(edge[1])
        used_right.add(edge[2])
        remaining.remove(c)
    return [list(edge) for edge in selected]


def _attack_random_restart(inst, rng, attempts=256):
    """Randomised MRV/least-conflict greedy without backtracking."""
    rows = _edges_by_color(inst)
    last = None
    for _ in range(attempts):
        remaining = set(range(inst["n"]))
        used_left, used_right = set(), set()
        selected = []
        while remaining:
            feasible = _feasible_by_colour(rows, remaining,
                                           used_left, used_right)
            smallest = min(len(row) for row in feasible.values())
            colour_choices = [c for c in remaining
                              if len(feasible[c]) == smallest]
            if smallest == 0:
                break
            c = rng.choice(colour_choices)
            scored = sorted((_blocking_score(edge, feasible, c), edge)
                            for edge in feasible[c])
            cutoff = scored[min(1, len(scored) - 1)][0]
            edge = rng.choice([edge for score, edge in scored
                               if score <= cutoff])
            selected.append(edge)
            used_left.add(edge[1])
            used_right.add(edge[2])
            remaining.remove(c)
        candidate = _complete_with_first(rows, selected, remaining)
        last = candidate
        if verify(inst, candidate)[0]:
            return candidate
    return last


def _transform(inst, pc, pl, pr, coordinate_order=(0, 1, 2),
               reorder=False):
    n = inst["n"]
    if any(sorted(p) != list(range(n)) for p in (pc, pl, pr)):
        raise ValueError("each relabelling must be a permutation")

    def carry(edge):
        raw = [edge[i] for i in coordinate_order]
        return [pc[raw[0]], pl[raw[1]], pr[raw[2]]]

    edges = [carry(edge) for edge in inst["edges"]]
    if reorder:
        edges.reverse()
        # This deterministic permutation is deliberately not tied to labels.
        edges = edges[::2] + edges[1::2]
    return {
        "n": n,
        "choices": inst["choices"],
        "edges": edges,
        "answer": [carry(edge) for edge in inst["answer"]],
    }


def selftest():
    """Run all mandatory G1--G8 gates and return measured evidence."""
    report = {}

    # G1: every named preset, with several independent seeds.
    g1_checked = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checked += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checked": g1_checked,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    planted = [list(edge) for edge in inst["answer"]]

    # G2: five corruptions, deliberately routed to five diagnostics.
    corruptions = {
        "drop_one": planted[:-1],
        "empty": [],
    }
    out_of_range = [list(edge) for edge in planted]
    out_of_range[0][0] = inst["n"]
    corruptions["out_of_range"] = out_of_range
    duplicate = [list(edge) for edge in planted]
    duplicate[-1] = list(duplicate[0])
    corruptions["duplicate_one"] = duplicate
    rows = _edges_by_color(inst)
    swapped = [list(edge) for edge in planted]
    old = tuple(swapped[0])
    alternative = next(edge for edge in rows[old[0]] if edge != old)
    swapped[0] = list(alternative)
    corruptions["swap_one_edge"] = swapped
    g2_results = {name: verify(inst, value)
                  for name, value in corruptions.items()}
    reasons = [reason for ok, reason in g2_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (all(not ok for ok, _ in g2_results.values())
                 and len(set(reasons)) == len(g2_results)),
        "results": {name: {"accepted": ok, "reason": reason}
                    for name, (ok, reason) in g2_results.items()},
        "distinct_reasons": len(set(reasons)),
    }

    # G3: prose outside tags and a Markdown fence inside them.
    encoded = json.dumps(planted, separators=(",", ":"))
    realistic = ("I checked all three coordinate sets.\n"
                 "<answer>\n```json\n" + encoded
                 + "\n```\n</answer>\nThis is the matching.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_edges": len(parsed) if parsed is not None else None,
    }

    # G4: one genuine edge per colour is enforced before guessing endpoints.
    guess_rng = random.Random(271828)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_probability": hits / trials,
        "candidate_prior": "uniform independent listed edge for every colour",
        "structure_aware_space": search_space(inst),
    }

    # G5: exhaustive count on a small, separately generated member.
    small = make_instance(n=14, choices=2, seed=7)
    solutions = enumerate_all(small)
    space = search_space(small)
    fraction = solutions / space if solutions is not None else None
    report["G5_sparse"] = {
        "pass": solutions is not None and fraction < 0.01,
        "instance": {"n": 14, "choices": 2, "seed": 7},
        "solutions": solutions,
        "search_space": space,
        "solution_fraction": fraction,
    }

    # G6: construction-aware outlier, greedy, and restart attacks.
    attack_solved = {"outlier": 0, "greedy": 0, "random_restart": 0}
    attack_reasons = {name: Counter() for name in attack_solved}
    degree_ranges = []
    for seed in range(8):
        attacked = make_instance(seed=10_000 + seed, **shipping)
        candidates = {
            "outlier": _attack_outlier(attacked),
            "greedy": _attack_greedy(attacked),
            "random_restart": _attack_random_restart(
                attacked, random.Random(20_000 + seed)),
        }
        left_degree = Counter(edge[1] for edge in attacked["edges"])
        right_degree = Counter(edge[2] for edge in attacked["edges"])
        colour_degree = Counter(edge[0] for edge in attacked["edges"])
        all_degrees = list(left_degree.values()) + list(right_degree.values()) \
            + list(colour_degree.values())
        degree_ranges.append([min(all_degrees), max(all_degrees)])
        for name, candidate in candidates.items():
            ok, reason = verify(attacked, candidate)
            attack_solved[name] += int(ok)
            if not ok:
                attack_reasons[name][reason] += 1
    report["G6_adversary_panel"] = {
        "pass": all(count == 0 for count in attack_solved.values()),
        "seeds_per_attack": 8,
        "tested_seeds": list(range(10_000, 10_008)),
        "solved_counts": attack_solved,
        "rejection_reasons": {name: dict(counts)
                              for name, counts in attack_reasons.items()},
        "colour_left_right_degree_ranges": degree_ranges,
        "random_restart_attempts_per_seed": 256,
    }

    # G7: n doubles every part, the witness, and the edge count.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=123456, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] == 2 * inst["n"]
                 and len(doubled["edges"]) == 2 * len(inst["edges"])),
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_edges": len(inst["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "planted_verify_reason": doubled_reason,
    }

    # G8: input order, label permutations, all six coordinate-role symmetries,
    # and their compositions.
    invariant_checks = 0
    real_transform_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=30_000 + seed, **shipping)
        base_key = canonical_key(original)
        unrelated_keys.append(base_key)
        rng = random.Random(40_000 + seed)
        pc, pl, pr = [list(range(original["n"])) for _ in range(3)]
        for permutation in (pc, pl, pr):
            rng.shuffle(permutation)
        identity = list(range(original["n"]))
        transforms = [_transform(original, identity, identity, identity,
                                 reorder=True)]
        transforms.extend(
            _transform(original, pc, pl, pr,
                       coordinate_order=coordinate_order, reorder=True)
            for coordinate_order in permutations(range(3))
        )
        for changed in transforms:
            invariant_checks += 1
            if canonical_key(changed) != base_key:
                failures.append({"seed": seed, "failure": "key changed"})
        for changed in transforms[1:]:
            carried_ok, carried_reason = verify(changed, changed["answer"])
            real_transform_checks += 1
            if not carried_ok:
                failures.append({"seed": seed, "failure": carried_reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (not failures and invariant_checks == 140
                 and real_transform_checks == 120 and distinct == 20),
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": failures,
        "caveat": "rooted colour refinement is invariant, not a complete canon",
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
