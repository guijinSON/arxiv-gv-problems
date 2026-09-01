"""Verified generators for sub-square-root planted-clique search.

The family is based on Section 3.3 of Ames and Vavasis,
"Nuclear norm minimization for the planted clique and biclique problems"
(arXiv:0901.3348).  It uses only the Python standard library and performs no
I/O at import time.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re


DIFFICULTY = {
    # The demo is intentionally readable and is expected to be easy for search.
    "demo": {"n": 32, "k": 8, "edge_num": 1, "edge_den": 2},
    # k grows, but k/sqrt(n) decreases: this stays below the paper's easy scale.
    "hard": {"n": 512, "k": 16, "edge_num": 1, "edge_den": 2},
}

SHIPPING_DIFFICULTY = "hard"

NOTES = r"""
Definition: Section 3 (especially the first paragraph of Section 3 and the
rank-one formulation there) fixes a clique as a set of vertices with every
distinct pair adjacent.  Section 3.3, conditions Gamma_1 and Gamma_2, fixes the
planted distribution used here: all edges within V* are present and every
remaining possible edge is independently present with fixed probability p.

Easy regimes avoided: Theorem 3.3 in Section 3.3 proves that for a sufficiently
large constant alpha(p), n >= alpha*sqrt(N) is recovered in polynomial time by
the paper's nuclear-norm relaxation, with high-probability uniqueness.  The
presets instead keep k just above the logarithmic clique scale of G(N,1/2), so
k grows while k/sqrt(N) decreases.  Section 3.2 also gives a polynomially
recoverable adversarial regime with only O(k^2) diversionary edges and bounded
plant-to-outsider degree; constant-density backgrounds are far outside that
sparse regime.  The paper proves neither average-case hardness below sqrt(N)
nor a polynomial algorithm there.  The witness task is size-k CLIQUE, not
maximum clique, so the checker never claims optimality.

Planting and attacks: this implements Section 3.3's Gamma_1/Gamma_2 distribution
exactly.  Planted labels are a uniformly random k-subset and every non-forced
edge is an independent Bernoulli(1/2) draw.  Plant and decoy labels therefore
have the same prior, and k is below the degree-noise scale asymptotically,
avoiding a per-vertex degree marker.  The degree outlier attack is defeated by
uniform labels and this sub-noise signal; the greedy and randomized-restart
attacks required increasing the active level to N=512, k=16.  In particular,
the rejected N=128, k=10 candidate was solved on 6/12 seeds by deterministic
greedy and 11/12 by randomized restarts even though a preliminary oracle panel
missed it.  The self-test tries
(1) a degree/neighbor-degree outlier ranking, (2) deterministic degree-ordered
greedy clique growth from every start, and (3) randomized greedy restarts with
look-ahead scores.  The shipping preset is accepted only if none finds a valid
witness on any panel seed.  These attacks are diagnostics, not a proof of
average-case hardness.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INTEGER_LIST_RE = re.compile(r"\s*[+-]?\d+(?:\s*,\s*[+-]?\d+)*\s*")
_ENUMERATION_CAP = 2_000_000


def _default_k(n: int) -> int:
    """A growing, asymptotically sub-square-root planted size."""
    return max(4, int(math.ceil(2.0 * math.log2(n) - 2.0)))


def _validate_params(n: int, k: int, edge_num: int, edge_den: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    if isinstance(k, bool) or not isinstance(k, int) or not 2 <= k < n:
        raise ValueError("k must be an integer with 2 <= k < n")
    if any(isinstance(x, bool) or not isinstance(x, int)
           for x in (edge_num, edge_den)):
        raise ValueError("edge_num and edge_den must be integers")
    if edge_den <= 0 or not 0 < edge_num < edge_den:
        raise ValueError("edge probability must satisfy 0 < edge_num/edge_den < 1")


def make_instance(n, seed=0, **params) -> dict:
    """Sample a clique first, then plant it in independent Bernoulli noise.

    ``n`` is the total number of vertices.  If ``k`` is omitted it grows a
    little faster than the typical clique scale in G(n, 1/2), so increasing n
    does not leave a fixed-parameter problem.
    ``edge_num/edge_den`` is the exact probability for every non-forced edge.
    """
    k = params.pop("k", None)
    edge_num = params.pop("edge_num", 1)
    edge_den = params.pop("edge_den", 2)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if k is None:
        k = _default_k(n)
    _validate_params(n, k, edge_num, edge_den)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)

    # G: sample the answer first.  Labels are uniform and carry no positional
    # signature.  Sorting is only the answer's canonical output convention.
    answer = sorted(rng.sample(range(1, n + 1), k))
    planted = set(answer)

    # This is exactly Section 3.3's Gamma_1/Gamma_2 model: force the pairs
    # inside the sampled witness and draw every other possible edge
    # independently from the same Bernoulli distribution.
    edges = sorted(
        (u, v)
        for u in range(1, n + 1)
        for v in range(u + 1, n + 1)
        if ((u in planted and v in planted)
            or rng.randrange(edge_den) < edge_num)
    )

    return {
        "family": "planted_k_clique",
        "vertex_count": n,
        "clique_size": k,
        "edge_probability": [edge_num, edge_den],
        "planting": "paper_section_3_3_gamma_1_gamma_2",
        "edges": edges,
        # Internal O(1) checker index.  ``edges`` remains the portable problem
        # data; emitters serialize the rendered question rather than this set.
        "edge_lookup": frozenset(edges),
        "answer": answer,
    }


def _edge_set(inst: dict) -> set[tuple[int, int]]:
    cached = inst.get("edge_lookup")
    if cached is not None:
        return cached
    return {tuple(sorted((int(u), int(v)))) for u, v in inst["edges"] if u != v}


def _adjacency(inst: dict) -> list[set[int]]:
    n = inst["vertex_count"]
    adj = [set() for _ in range(n)]
    for u, v in inst["edges"]:
        u0, v0 = int(u) - 1, int(v) - 1
        if 0 <= u0 < n and 0 <= v0 < n and u0 != v0:
            adj[u0].add(v0)
            adj[v0].add(u0)
    return adj


def render(inst) -> str:
    """Render a self-contained size-k clique search problem."""
    n = inst["vertex_count"]
    k = inst["clique_size"]
    edges = _edge_set(inst)
    rows = []
    for u in range(1, n + 1):
        bits = "".join("1" if tuple(sorted((u, v))) in edges and u != v else "0"
                       for v in range(1, n + 1))
        rows.append(f"{u}: {bits}")

    example = ", ".join(str(i) for i in range(1, k + 1))
    return (
        "Find a clique of the required size in the undirected simple graph below.\n\n"
        "Definitions and conventions:\n"
        f"- The vertices are the integer labels 1 through {n}, inclusive.\n"
        "- A clique is a set of distinct vertices for which every pair of distinct "
        "vertices is joined by an edge.\n"
        f"- Return exactly {k} distinct vertex labels. Order does not change the "
        "set, and the checker accepts any order. Repeats are forbidden.\n"
        "- The graph is given by its full adjacency matrix. In row i, character j "
        "is 1 exactly when vertices i and j are adjacent, and is 0 otherwise. "
        "Rows and character positions are both 1-indexed. The diagonal is 0 and "
        "the matrix is symmetric.\n\n"
        f"vertex_count: {n}\n"
        f"required_clique_size: {k}\n"
        "adjacency_matrix:\n" + "\n".join(rows) + "\n\n"
        "Give your final answer inside <answer></answer> tags, as exactly "
        f"{k} comma-separated integer labels.\n"
        f"Example format only: <answer>{example}</answer>\n"
        "Output nothing else inside the tags."
    )


def parse_answer(text) -> object | None:
    """Extract one comma-separated integer list from answer tags."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if len(matches) != 1:
        return None
    body = matches[0]
    if not _INTEGER_LIST_RE.fullmatch(body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any size-k clique; the planted ``inst['answer']`` is never read."""
    if not isinstance(answer, list) or any(isinstance(x, bool) or not isinstance(x, int)
                                           for x in answer):
        return False, "answer must be a list of integer vertex labels"
    if not answer:
        return False, "answer is empty"
    k = inst["clique_size"]
    if len(answer) != k:
        return False, f"wrong size: expected {k} labels, received {len(answer)}"
    if len(set(answer)) != len(answer):
        return False, "vertex labels must be distinct; a duplicate was found"
    n = inst["vertex_count"]
    bad = next((v for v in answer if not 1 <= v <= n), None)
    if bad is not None:
        return False, f"vertex label {bad} is outside the inclusive range 1..{n}"

    edges = _edge_set(inst)
    for u, v in itertools.combinations(answer, 2):
        if tuple(sorted((u, v))) not in edges:
            return False, f"missing edge between vertices {u} and {v}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the structure-aware space of k distinct labels."""
    if not hasattr(rng, "sample"):
        raise TypeError("rng must provide sample()")
    n, k = inst["vertex_count"], inst["clique_size"]
    return sorted(rng.sample(range(1, n + 1), k))


def search_space(inst) -> int | None:
    """Count all k-subsets, the exact statement-aware candidate space."""
    try:
        return math.comb(inst["vertex_count"], inst["clique_size"])
    except (KeyError, TypeError, ValueError):
        return None


def enumerate_all(inst) -> int | None:
    """Count all valid k-cliques exactly when at most two million are tested."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n, k = inst["vertex_count"], inst["clique_size"]
    edges = _edge_set(inst)
    count = 0
    for candidate in itertools.combinations(range(1, n + 1), k):
        if all((u, v) in edges for u, v in itertools.combinations(candidate, 2)):
            count += 1
    return count


def _compress(values) -> list[int]:
    unique = {value: index for index, value in enumerate(sorted(set(values)))}
    return [unique[value] for value in values]


def _canonical_payload(inst: dict) -> tuple[str, bool]:
    """Return a permutation-invariant graph payload and whether it is exact.

    Color refinement is canonical.  It almost surely makes these dense random
    graphs discrete; in that case ordering by the canonical singleton colors
    gives an exact canonical adjacency string.  A strong invariant fallback is
    used for the exceptionally rare non-discrete case.
    """
    n = inst["vertex_count"]
    k = inst["clique_size"]
    adj = _adjacency(inst)
    colors = _compress([len(a) for a in adj])
    history = []
    for _ in range(n):
        signatures = [
            (colors[v], tuple(sorted(colors[u] for u in adj[v])))
            for v in range(n)
        ]
        new_colors = _compress(signatures)
        history.append(tuple(sorted(new_colors.count(c) for c in set(new_colors))))
        if new_colors == colors:
            colors = new_colors
            break
        colors = new_colors

    if len(set(colors)) == n:
        order = sorted(range(n), key=lambda v: colors[v])
        upper = "".join(
            "1" if order[j] in adj[order[i]] else "0"
            for i in range(n) for j in range(i + 1, n)
        )
        return json.dumps(["exact", n, k, upper], separators=(",", ":")), True

    # Strong cheap fallback.  It is invariant but can collide for nonisomorphic
    # graphs; exact graph canonicalization is not claimed in this branch.
    vertex_stats = []
    for v in range(n):
        triangles_twice = sum(len(adj[v] & adj[u]) for u in adj[v])
        vertex_stats.append((colors[v], len(adj[v]), triangles_twice))
    pair_stats = []
    for u in range(n):
        for v in range(u + 1, n):
            pair_stats.append((
                1 if v in adj[u] else 0,
                min(colors[u], colors[v]), max(colors[u], colors[v]),
                len(adj[u] & adj[v]),
            ))
    payload = ["invariant", n, k, history, sorted(vertex_stats), sorted(pair_stats)]
    return json.dumps(payload, separators=(",", ":")), False


def canonical_key(inst) -> str:
    """Canonical graph key, invariant under vertex and edge-list relabelling."""
    payload, exact = _canonical_payload(inst)
    tag = "exact" if exact else "fallback"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"planted-k-clique-v1:{tag}:{digest}"


def escalate(params) -> dict | None:
    """Increase graph and witness size while moving farther below sqrt(n)."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    old_n = int(params["n"])
    old_k = int(params.get("k", _default_k(old_n)))
    new_n = max(old_n + 1, int(math.ceil(old_n * 1.5)))
    new_k = max(old_k + 1, _default_k(new_n))
    if new_k >= math.sqrt(new_n):
        # Increase N until the finite preset also lies strictly below sqrt(N).
        new_n = max(new_n, new_k * new_k + 1)
    return {
        "n": new_n,
        "k": new_k,
        "edge_num": int(params.get("edge_num", 1)),
        "edge_den": int(params.get("edge_den", 2)),
    }


# ---------------------------------------------------------------------------
# Adversary panel used by selftest().  Each attack sees only statement data.

def _outlier_attack(inst: dict) -> list[int]:
    adj = _adjacency(inst)
    k = inst["clique_size"]
    scores = [
        (len(adj[v]), sum(len(adj[u]) for u in adj[v]), -v, v + 1)
        for v in range(len(adj))
    ]
    return sorted(item[-1] for item in sorted(scores, reverse=True)[:k])


def _greedy_attack(inst: dict) -> list[int] | None:
    adj = _adjacency(inst)
    n, k = len(adj), inst["clique_size"]
    degree_order = sorted(range(n), key=lambda v: (-len(adj[v]), v))
    for start in degree_order:
        clique = [start]
        candidates = set(adj[start])
        while candidates and len(clique) < k:
            # Degree first, then common-candidate lookahead, then label.
            v = max(candidates,
                    key=lambda x: (len(adj[x]), len(adj[x] & candidates), -x))
            clique.append(v)
            candidates &= adj[v]
        if len(clique) == k:
            answer = sorted(v + 1 for v in clique)
            if verify(inst, answer)[0]:
                return answer
    return None


def _restart_attack(inst: dict, rng: random.Random, restarts: int = 256) -> list[int] | None:
    adj = _adjacency(inst)
    n, k = len(adj), inst["clique_size"]
    weights = [len(adj[v]) + 1 for v in range(n)]
    population = list(range(n))
    for _ in range(restarts):
        start = rng.choices(population, weights=weights, k=1)[0]
        clique = [start]
        candidates = set(adj[start])
        while candidates and len(clique) < k:
            pool = list(candidates)
            # A mild heuristic: sample among the best quarter by how many
            # options would remain after choosing the vertex.
            pool.sort(key=lambda v: (len(adj[v] & candidates), len(adj[v])),
                      reverse=True)
            pool = pool[:max(1, len(pool) // 4)]
            v = rng.choice(pool)
            clique.append(v)
            candidates &= adj[v]
        if len(clique) == k:
            answer = sorted(v + 1 for v in clique)
            if verify(inst, answer)[0]:
                return answer
    return None


def _replace_with_bad_outsider(inst: dict, answer: list[int]) -> list[int]:
    n = inst["vertex_count"]
    inside = set(answer)
    edges = _edge_set(inst)
    for outsider in range(1, n + 1):
        if outsider in inside:
            continue
        for removed in answer:
            candidate = sorted((inside - {removed}) | {outsider})
            if len(candidate) == len(answer) and not all(
                    tuple(sorted(pair)) in edges
                    for pair in itertools.combinations(candidate, 2)):
                return candidate
    raise AssertionError("could not construct a non-clique one-element replacement")


def _relabel_instance(inst: dict, permutation: list[int]) -> dict:
    """Relabel old vertex i+1 as permutation[i], carrying the witness."""
    n = inst["vertex_count"]
    if sorted(permutation) != list(range(1, n + 1)):
        raise ValueError("permutation is not a relabelling of 1..n")
    mapping = {old + 1: permutation[old] for old in range(n)}
    out = dict(inst)
    out["edges"] = [(min(mapping[u], mapping[v]), max(mapping[u], mapping[v]))
                    for u, v in inst["edges"]]
    out["edge_lookup"] = frozenset(out["edges"])
    out["answer"] = sorted(mapping[v] for v in inst["answer"])
    return out


def selftest() -> dict:
    """Run mandatory gates and return a JSON-serializable measurement report."""
    report = {}

    # G1: every named preset, six deterministic seeds.
    g1_checked = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(6):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checked += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "checked": g1_checked, "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=1729, **shipping)
    planted = list(inst["answer"])

    # G2: five different corruptions must hit five distinct diagnostics.
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one_for_outsider": _replace_with_bad_outsider(inst, planted),
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [inst["vertex_count"] + 1],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(row["rejected"] for row in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose + markdown fences around the delimited answer.
    answer_text = ", ".join(map(str, planted))
    response = ("I checked all pairwise adjacencies.\n\n```text\n"
                f"<answer>  {answer_text}  </answer>\n```\n")
    parsed = parse_answer(response)
    rt_ok, rt_reason = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and rt_ok,
        "parsed": parsed,
        "verify_reason": rt_reason,
    }

    # G4: uniform over all k-subsets is already structure-aware: distinctness,
    # exact arity, range, and order normalisation are built into the sampler.
    guess_rng = random.Random(0x09013348)
    total = 250_000
    hits = 0
    for _ in range(total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "measured_probability": probability,
        "sampler": "uniform k-subset (all statement-obvious constraints enforced)",
        "candidate_space": search_space(inst),
    }

    # G5: a deliberately small, enumerable instance.  This is separate from
    # presets because a million-scale space is too guessable for G4 sampling.
    small = make_instance(n=20, k=7, seed=314159)
    small_space = search_space(small)
    small_solutions = enumerate_all(small)
    sparse_fraction = (small_solutions / small_space
                       if small_solutions is not None else None)
    report["G5_sparse"] = {
        "pass": (small_solutions is not None and small_solutions >= 1
                 and sparse_fraction < 1e-4),
        "n": 20,
        "k": 7,
        "valid_answers": small_solutions,
        "candidate_space": small_space,
        "solution_fraction": sparse_fraction,
        "enumeration_cap": _ENUMERATION_CAP,
    }

    # G6: every attack must fail on every one of twelve unrelated seeds.
    attacks = {
        "outlier_degree_neighbor_degree": 0,
        "degree_ordered_greedy": 0,
        "random_restart_lookahead_256": 0,
    }
    panel_seeds = list(range(800, 812))
    per_seed = []
    for seed in panel_seeds:
        panel_inst = make_instance(seed=seed, **shipping)
        candidates = {
            "outlier_degree_neighbor_degree": _outlier_attack(panel_inst),
            "degree_ordered_greedy": _greedy_attack(panel_inst),
            "random_restart_lookahead_256": _restart_attack(
                panel_inst, random.Random(seed ^ 0xA5A5A5A5), 256),
        }
        solved = {}
        for name, candidate in candidates.items():
            ok = candidate is not None and verify(panel_inst, candidate)[0]
            solved[name] = bool(ok)
            attacks[name] += int(ok)
        per_seed.append({"seed": seed, "solved": solved})
    report["G6_adversary_panel"] = {
        "pass": all(count == 0 for count in attacks.values()),
        "seeds": len(panel_seeds),
        "solves_by_attack": attacks,
        "failures_by_attack": {name: len(panel_seeds) - count
                               for name, count in attacks.items()},
        "per_seed": per_seed,
    }

    # G7: double the shipping N and let the asymptotic rule grow k.
    doubled_n = shipping["n"] * 2
    doubled_k = _default_k(doubled_n)
    if doubled_k <= shipping["k"]:
        doubled_k = shipping["k"] + 1
    doubled = make_instance(
        n=doubled_n, k=doubled_k,
        edge_num=shipping["edge_num"], edge_den=shipping["edge_den"], seed=271828)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled_k > shipping["k"]
                 and search_space(doubled) > search_space(inst)),
        "base_n": shipping["n"], "base_k": shipping["k"],
        "doubled_n": doubled_n, "doubled_k": doubled_k,
        "base_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "verify_reason": doubled_reason,
    }

    # G8: edge-list order, two vertex relabellings, and their compositions.
    invariant_checks = 0
    carried_witness_checks = 0
    exact_keys = 0
    base_keys = []
    g8_failures = []
    # Use a substantial but non-shipping graph to keep this 20-seed proof fast.
    key_params = {"n": 128, "k": 10, "edge_num": 1, "edge_den": 2}
    for seed in range(20, 40):
        key_inst = make_instance(seed=seed, **key_params)
        base = canonical_key(key_inst)
        base_keys.append(base)
        exact_keys += int(":exact:" in base)
        rng = random.Random(seed ^ 0xC0DEC0DE)
        perm_random = list(range(1, key_inst["vertex_count"] + 1))
        rng.shuffle(perm_random)
        perm_reverse = list(range(key_inst["vertex_count"], 0, -1))

        reordered = dict(key_inst)
        reordered["edges"] = list(reversed(key_inst["edges"]))
        rel_random = _relabel_instance(key_inst, perm_random)
        rel_reverse = _relabel_instance(key_inst, perm_reverse)
        composed = dict(rel_random)
        composed["edges"] = list(reversed(rel_random["edges"]))
        transforms = {
            "edge_order_reversal": reordered,
            "random_vertex_permutation": rel_random,
            "reverse_vertex_permutation": rel_reverse,
            "random_permutation_plus_edge_reorder": composed,
        }
        for name, transformed in transforms.items():
            invariant_checks += 1
            if canonical_key(transformed) != base:
                g8_failures.append({"seed": seed, "transform": name,
                                    "failure": "key changed"})
            # Edge reordering preserves the literal answer; relabelling carries it.
            witness = (key_inst["answer"] if name == "edge_order_reversal"
                       else transformed["answer"])
            carried_witness_checks += 1
            ok, why = verify(transformed, witness)
            if not ok:
                g8_failures.append({"seed": seed, "transform": name,
                                    "failure": "transformed witness failed: " + why})

    distinct_count = len(set(base_keys))
    report["G8_canonical_key"] = {
        "pass": (not g8_failures and invariant_checks == 80
                 and carried_witness_checks == 80 and distinct_count == 20),
        "invariance_checks": invariant_checks,
        "real_transformation_witness_checks": carried_witness_checks,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_instances": 20,
        "exact_canonical_branches": exact_keys,
        "fallback_branches": 20 - exact_keys,
        "failures": g8_failures,
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
