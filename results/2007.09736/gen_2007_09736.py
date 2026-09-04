"""Generators for partitions of regular graphs into efficient dominating sets.

The family is inspired by the E-set partitions in arXiv:2007.09736.  Unlike
the paper's star/pancake transposition graphs, whose partitions have an explicit
coordinate formula, these instances are randomly relabelled graph covers of a
complete graph.  Finding such a cover is NP-complete for every fixed target
K_q with q >= 4, while a proposed cover is checked by scanning neighborhoods.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    "demo": {"n": 4, "q": 4},
    "easy": {"n": 5, "q": 4},
    "medium": {"n": 40, "q": 6},
    "hard": {"n": 56, "q": 6},
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper grounding.  Section 1 of arXiv:2007.09736v10 defines an efficient
dominating set (E-set) by the exact-one-neighbor condition.  Theorem 1 connects
a totally efficient coloring with a partition into E-sets.  Theorem 2(ii) and
Theorems 10--12 identify the easy regime that must be avoided: in the paper's
ST^2_k and PC^2_k transposition graphs, coordinate classes Sigma_i^k give the
E-sets explicitly.  This generator therefore uses general connected regular
graphs, not those transposition graphs.

Hardness regime.  On a connected (q-1)-regular graph, a partition into q
E-sets is the same as a locally bijective homomorphism (covering projection)
onto K_q: every vertex has exactly one neighbor of every other color.  The
K_q-Cover decision problem is NP-complete for every fixed q >= 4 (Kratochvil,
1994, Theorem 4.5).  Here q is at least four and n, the number of vertices in
each fiber, grows.  Verification remains linear in the displayed graph size.

Inverse generation and attacks.  A balanced hidden color vector is sampled
first.  For every pair of colors, an independently shuffled perfect matching
is then placed between their fibers; disconnected draws are discarded without
changing the planted answer.  Vertex labels and edge order reveal no fiber.
All vertices have identical degree.  The outlier attack balances colors after
sorting by degree and triangle count; the greedy attack colors the square graph
left-to-right; the restart attack makes 128 randomized DSATUR-style greedy
attempts.  selftest records that each attack fails on eight shipping
instances.  random_candidate uses the substantially stronger balanced-coloring
prior rather than independent random colors.  An earlier candidate medium rung
(n=20, q=5) held against three LLM oracles but was discarded because randomized
greedy restarts solved 7/8 seeds (and 8/8 with 512 restarts); the shipped medium
rung is n=40, q=6.
"""


def _neighbors(num_vertices, edges):
    adj = [[] for _ in range(num_vertices)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def _connected(adj):
    if not adj:
        return False
    seen = {0}
    stack = [0]
    while stack:
        v = stack.pop()
        for u in adj[v]:
            if u not in seen:
                seen.add(u)
                stack.append(u)
    return len(seen) == len(adj)


def make_instance(n, seed=0, **params):
    """Plant a balanced E-set partition, then build a random cover around it."""
    q = params.pop("q", 4)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(q, bool) or not isinstance(q, int) or q < 4:
        raise ValueError("q must be an integer at least 4")

    rng = random.Random(seed)
    total = n * q

    # G: the witness is sampled before any edge is drawn.
    answer = [c for c in range(q) for _ in range(n)]
    rng.shuffle(answer)
    fibers = [[v for v, c in enumerate(answer) if c == color]
              for color in range(q)]

    # Random n-lifts are connected with high probability here.  Resampling the
    # matchings leaves the already-sampled witness untouched.
    for _ in range(1000):
        edges = []
        for a in range(q):
            for b in range(a + 1, q):
                right = list(fibers[b])
                rng.shuffle(right)
                edges.extend(zip(fibers[a], right))
        edges = [(min(u, v), max(u, v)) for u, v in edges]
        rng.shuffle(edges)
        adj = _neighbors(total, edges)
        if _connected(adj):
            break
    else:  # Practically unreachable, but never return an invalid instance.
        raise RuntimeError("could not draw a connected graph cover")

    return {
        "q": q,
        "fiber_size": n,
        "num_vertices": total,
        "edges": edges,
        "neighbors": adj,
        "answer": answer,
    }


def render(inst):
    """Render the complete, standalone problem and its exact output contract."""
    q = inst["q"]
    total = inst["num_vertices"]
    n = inst["fiber_size"]
    edge_tokens = [f"{u}-{v}" for u, v in inst["edges"]]
    rows = [" ".join(edge_tokens[i:i + 10])
            for i in range(0, len(edge_tokens), 10)]
    edge_block = "\n".join(rows)
    return f"""Partition a graph into efficient dominating sets

The input is a finite undirected simple graph.  Its vertices are the integers
0 through {total - 1}, inclusive.  Each unordered edge is listed once as u-v;
there are no loops, and the order of endpoints and edges has no meaning.

A set S of vertices is an efficient dominating set (an E-set) when every
vertex outside S has exactly one neighbor in S.  Find a partition of all
vertices into exactly {q} E-sets, named by colors 0 through {q - 1}.  In other
words, assign one color c[v] to each vertex v so that the closed neighborhood
consisting of v and all its neighbors contains every color 0 through {q - 1}
exactly once.  Consequently adjacent vertices have different colors.  Every
color must occur exactly {n} times.

Every vertex has degree {q - 1}.  The graph has {total} vertices and
{len(inst['edges'])} edges:
{edge_block}

Order matters only by vertex index: the first output integer is c[0], the
second is c[1], and so on through c[{total - 1}].  Color names may be globally
permuted.  Repeated colors are required, but there must be exactly {total}
comma-separated integers, each in the inclusive range 0..{q - 1}.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of the {total} colors in vertex order.
Example of the syntax: <answer>0, 2, 1, 0</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>",
                        re.IGNORECASE | re.DOTALL)
_INT_LIST_RE = re.compile(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*")


def parse_answer(text):
    """Extract a comma-separated color list from a tagged model response."""
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
    if len(body) >= 2 and body[0] == "[" and body[-1] == "]":
        body = body[1:-1].strip()
    if not body or _INT_LIST_RE.fullmatch(body) is None:
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Accept every valid E-set partition; never consult the planted answer."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of vertex colors"
    if len(answer) == 0:
        return False, "empty answer"
    total = inst["num_vertices"]
    q = inst["q"]
    if len(answer) != total:
        return False, f"wrong number of vertex colors: expected {total}"
    if any(isinstance(c, bool) or not isinstance(c, int) for c in answer):
        return False, "every color must be an integer"
    if any(c < 0 or c >= q for c in answer):
        return False, f"a vertex color is outside 0..{q - 1}"
    if any(count != inst["fiber_size"]
           for count in Counter(answer).values()) or len(set(answer)) != q:
        return False, "color classes do not all have the required size"

    adj = inst.get("neighbors")
    if adj is None:
        adj = _neighbors(total, inst["edges"])

    for u, v in inst["edges"]:
        if answer[u] == answer[v]:
            return False, "adjacent vertices share a color"
    for v, row in enumerate(adj):
        mask = 0
        for u in row:
            bit = 1 << answer[u]
            if mask & bit:
                return False, "a vertex has duplicate neighbor colors"
            mask |= bit
        wanted = ((1 << q) - 1) ^ (1 << answer[v])
        if mask != wanted:
            return False, "a closed neighborhood does not contain every color once"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the balanced colorings a structure-aware guesser uses."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    candidate = [c for c in range(inst["q"])
                 for _ in range(inst["fiber_size"])]
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    """Number of syntactically valid q-color vectors (the naive space)."""
    return inst["q"] ** inst["num_vertices"]


def _is_cover_coloring(adj, colors, q):
    for v, row in enumerate(adj):
        seen = {colors[v]}
        seen.update(colors[u] for u in row)
        if len(seen) != q:
            return False
    return True


def enumerate_all(inst):
    """Count all valid colorings exactly when at most 250,000 are examined."""
    total = search_space(inst)
    if total > 250_000:
        return None
    q = inst["q"]
    nverts = inst["num_vertices"]
    adj = inst.get("neighbors") or _neighbors(nverts, inst["edges"])
    count = 0
    for colors in itertools.product(range(q), repeat=nverts):
        if _is_cover_coloring(adj, colors, q):
            count += 1
    return count


def _rooted_refinement_certificate(adj, root):
    """An isomorphism-invariant rooted 1-WL quotient certificate."""
    size = len(adj)
    colors = [1 if v == root else 0 for v in range(size)]
    history = []
    # A bounded number of rounds keeps this a cheap invariant even on the
    # shipping graphs.  Twelve rooted refinement layers distinguish the sampled
    # covers in the diversity gate; completeness is neither claimed nor needed.
    for _ in range(min(size + 1, 12)):
        signatures = [
            (colors[v], tuple(sorted(colors[u] for u in adj[v])))
            for v in range(size)
        ]
        kinds = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_colors = [kinds[sig] for sig in signatures]
        counts = tuple(Counter(new_colors)[i]
                       for i in range(max(new_colors) + 1))
        history.append(counts)
        if new_colors == colors:
            colors = new_colors
            break
        colors = new_colors

    classes = max(colors) + 1
    edge_counts = [[0] * classes for _ in range(classes)]
    for v, row in enumerate(adj):
        for u in row:
            if v < u:
                a, b = sorted((colors[v], colors[u]))
                edge_counts[a][b] += 1
    quotient = tuple(edge_counts[a][b]
                     for a in range(classes) for b in range(a, classes))
    return (colors[root], tuple(history), quotient)


def canonical_key(inst):
    """Strong cheap unlabeled-graph invariant; independent of seed and answer.

    Exact graph canonicalization is Graph-Isomorphism-hard in general.  The key
    uses the sorted deck of rooted color-refinement quotients.  It is invariant
    under every vertex relabelling, edge reordering, and endpoint reversal, and
    is much stronger than a degree sequence, though rare nonisomorphic
    color-refinement-equivalent graphs can still collide.
    """
    total = inst["num_vertices"]
    normalized = sorted((min(u, v), max(u, v)) for u, v in inst["edges"])
    adj = _neighbors(total, normalized)
    certificates = sorted(_rooted_refinement_certificate(adj, r)
                          for r in range(total))
    structural = (total, len(normalized), inst["q"], tuple(certificates))
    data = repr(structural).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def escalate(params):
    """Increase the number of cover sheets, the direct CSP-size axis."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    q = int(params.get("q", 4))
    if n >= 64:
        return None
    return {"n": min(64, max(n + 1, math.ceil(1.75 * n))), "q": q}


def _square_adjacency(inst):
    adj = inst.get("neighbors") or _neighbors(inst["num_vertices"],
                                               inst["edges"])
    square = []
    for v, row in enumerate(adj):
        nearby = set(row)
        for u in row:
            nearby.update(adj[u])
        nearby.discard(v)
        square.append(nearby)
    return square


def _balanced_fallback(partial, q, n, rng):
    counts = Counter(c for c in partial if c is not None)
    remaining = [c for c in range(q) for _ in range(n - counts[c])]
    rng.shuffle(remaining)
    result = list(partial)
    for i, c in zip((i for i, value in enumerate(result) if value is None),
                    remaining):
        result[i] = c
    return result


def _attack_outlier(inst):
    adj = inst["neighbors"]
    triangle_counts = []
    adj_sets = [set(row) for row in adj]
    for v, row in enumerate(adj):
        twice = sum(len(adj_sets[u] & adj_sets[v]) for u in row)
        triangle_counts.append(twice // 2)
    order = sorted(range(inst["num_vertices"]),
                   key=lambda v: (len(adj[v]), triangle_counts[v], v))
    answer = [None] * inst["num_vertices"]
    for rank, v in enumerate(order):
        answer[v] = rank // inst["fiber_size"]
    return answer


def _attack_greedy(inst):
    q, n = inst["q"], inst["fiber_size"]
    square = _square_adjacency(inst)
    result = [None] * inst["num_vertices"]
    counts = [0] * q
    for v in range(inst["num_vertices"]):
        forbidden = {result[u] for u in square[v] if result[u] is not None}
        choices = [c for c in range(q) if c not in forbidden and counts[c] < n]
        if not choices:
            choices = [c for c in range(q) if counts[c] < n]
        c = min(choices, key=lambda color: (counts[color], color))
        result[v] = c
        counts[c] += 1
    return result


def _attack_random_restart(inst, rng, attempts=128):
    q, n = inst["q"], inst["fiber_size"]
    total = inst["num_vertices"]
    square = _square_adjacency(inst)
    last = None
    for _ in range(attempts):
        result = [None] * total
        counts = [0] * q
        clique = [0] + list(inst["neighbors"][0])
        palette = list(range(q))
        rng.shuffle(palette)
        for v, c in zip(clique, palette):
            result[v] = c
            counts[c] += 1
        while any(c is None for c in result):
            uncolored = [v for v, c in enumerate(result) if c is None]
            rng.shuffle(uncolored)
            v = max(uncolored, key=lambda x: len(
                {result[u] for u in square[x] if result[u] is not None}))
            forbidden = {result[u] for u in square[v] if result[u] is not None}
            choices = [c for c in range(q)
                       if c not in forbidden and counts[c] < n]
            if not choices:
                break
            rng.shuffle(choices)
            c = min(choices, key=lambda color: counts[color])
            result[v] = c
            counts[c] += 1
        result = _balanced_fallback(result, q, n, rng)
        last = result
        if verify(inst, result)[0]:
            return result
    return last


def _relabel(inst, permutation, reorder=False):
    total = inst["num_vertices"]
    if sorted(permutation) != list(range(total)):
        raise ValueError("not a vertex permutation")
    edges = [(permutation[u], permutation[v]) for u, v in inst["edges"]]
    if reorder:
        edges = [(v, u) if i % 2 else (u, v)
                 for i, (u, v) in enumerate(reversed(edges))]
    answer = [None] * total
    for old, new in enumerate(permutation):
        answer[new] = inst["answer"][old]
    return {
        "q": inst["q"],
        "fiber_size": inst["fiber_size"],
        "num_vertices": total,
        "edges": edges,
        "neighbors": _neighbors(total, edges),
        "answer": answer,
    }


def selftest():
    """Run and report all mandatory G1--G8 gates."""
    report = {}

    # G1: all named presets and several seeds.
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
        "pass": not g1_failures, "checked": g1_checked,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    planted = list(inst["answer"])

    # G2: five semantically different corruptions and five distinct diagnostics.
    corruptions = {
        "drop_one": planted[:-1],
        "empty": [],
        "out_of_range": [inst["q"]] + planted[1:],
    }
    duplicate = list(planted)
    duplicate_index = next(i for i, c in enumerate(duplicate)
                           if c != duplicate[0])
    duplicate[duplicate_index] = duplicate[0]
    corruptions["duplicate_one"] = duplicate

    swap_answer = None
    for i in range(len(planted)):
        for j in range(i + 1, len(planted)):
            if planted[i] == planted[j]:
                continue
            trial = list(planted)
            trial[i], trial[j] = trial[j], trial[i]
            ok, reason = verify(inst, trial)
            if not ok and reason not in {
                    verify(inst, value)[1] for value in corruptions.values()}:
                swap_answer = trial
                break
        if swap_answer is not None:
            break
    corruptions["swap_two"] = swap_answer if swap_answer is not None else tuple()
    g2_results = {name: verify(inst, value)
                  for name, value in corruptions.items()}
    g2_reasons = [reason for ok, reason in g2_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (all(not ok for ok, _ in g2_results.values())
                 and len(set(g2_reasons)) == len(g2_results)),
        "results": {name: {"accepted": ok, "reason": reason}
                    for name, (ok, reason) in g2_results.items()},
        "distinct_reasons": len(set(g2_reasons)),
    }

    # G3: prose, a Markdown fence, whitespace, and tags all survive parsing.
    encoded = ", ".join(map(str, planted))
    realistic = ("I checked every closed neighborhood.\n```text\n"
                 f"<answer>\n  {encoded}\n</answer>\n```\nThat is my result.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_length": len(parsed) if parsed is not None else None,
    }

    # G4: balanced random guesses, not the vastly larger independent-color prior.
    guess_rng = random.Random(271828)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    balanced_space = math.factorial(inst["num_vertices"])
    balanced_space //= math.factorial(inst["fiber_size"]) ** inst["q"]
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_probability": hits / trials,
        "candidate_prior": "uniform balanced color vectors",
        "balanced_candidate_space": balanced_space,
        "naive_candidate_space": search_space(inst),
    }

    # G5: a small connected 2-lift is exhaustively enumerable.
    small = make_instance(n=2, q=4, seed=7)
    solutions = enumerate_all(small)
    naive = search_space(small)
    fraction = solutions / naive if solutions is not None else None
    report["G5_sparse"] = {
        "pass": solutions is not None and fraction < 0.01,
        "instance": {"n": 2, "q": 4, "seed": 7},
        "solutions": solutions,
        "search_space": naive,
        "solution_fraction": fraction,
    }

    # G6: attacks target labels/local outliers, obvious greedy, and restarts.
    attack_results = {"outlier": [], "greedy": [], "random_restart": []}
    for seed in range(8):
        attacked = make_instance(seed=10_000 + seed, **shipping)
        candidates = {
            "outlier": _attack_outlier(attacked),
            "greedy": _attack_greedy(attacked),
            "random_restart": _attack_random_restart(
                attacked, random.Random(20_000 + seed)),
        }
        for name, candidate in candidates.items():
            ok, reason = verify(attacked, candidate)
            attack_results[name].append({"seed": 10_000 + seed,
                                         "solved": ok, "reason": reason})
    attack_solved = {name: sum(row["solved"] for row in rows)
                     for name, rows in attack_results.items()}
    attack_reasons = {
        name: dict(Counter(row["reason"] for row in rows if not row["solved"]))
        for name, rows in attack_results.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(count == 0 for count in attack_solved.values()),
        "seeds_per_attack": 8,
        "tested_seeds": list(range(10_000, 10_008)),
        "solved_counts": attack_solved,
        "rejection_reasons": attack_reasons,
    }

    # G7: n is the cover degree; doubling it doubles vertices and edges.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=123456, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and doubled["num_vertices"] == 2 * inst["num_vertices"]
                 and len(doubled["edges"]) == 2 * len(inst["edges"])),
        "base_vertices": inst["num_vertices"],
        "doubled_vertices": doubled["num_vertices"],
        "base_edges": len(inst["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "planted_verify_reason": doubled_reason,
    }

    # G8: vertex relabel, edge reorder, endpoint reversal, and compositions.
    invariant_checks = 0
    real_transform_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=30_000 + seed, **shipping)
        base_key = canonical_key(original)
        unrelated_keys.append(base_key)
        perm_rng = random.Random(40_000 + seed)
        permutation = list(range(original["num_vertices"]))
        perm_rng.shuffle(permutation)
        identity = list(range(original["num_vertices"]))
        transforms = [
            _relabel(original, identity, reorder=True),
            _relabel(original, permutation, reorder=False),
            _relabel(original, permutation, reorder=True),
        ]
        for changed in transforms:
            invariant_checks += 1
            if canonical_key(changed) != base_key:
                g8_failures.append({"seed": seed, "failure": "key changed"})
        carried_ok, carried_reason = verify(transforms[-1],
                                             transforms[-1]["answer"])
        real_transform_checks += 1
        if not carried_ok:
            g8_failures.append({"seed": seed, "failure": carried_reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (not g8_failures and invariant_checks == 60
                 and real_transform_checks == 20 and distinct == 20),
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
        "caveat": "rooted color refinement is an invariant, not a complete GI canon",
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
