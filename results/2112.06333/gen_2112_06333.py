"""Verified generator for single-conflict coloring instances.

This module uses the proper-coloring special case in Section 1.1 of
Bradshaw--Masarik, "Single-conflict colorings of degenerate graphs"
(arXiv:2112.06333).  It is deliberately standard-library only.
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
    "tiny": {"n": 4, "matchings": 2, "triangle_free": False},
    "medium": {"n": 72, "matchings": 4, "triangle_free": True},
    "hard": {"n": 108, "matchings": 4, "triangle_free": True},
}

SHIPPING_DIFFICULTY = "medium"

NOTES = """\
Definition: Section 1 and especially Section 1.1 define a single-conflict
coloring and state the exact proper-coloring encoding used here: replace every
edge by k parallel edges carrying the k monochromatic conflicts.  With k=3,
the witness is exactly a proper 3-coloring.

Easy regimes avoided: Theorem 1.1 gives enough colors at roughly the square
root of maximum degree.  Theorem 2.3 gives a stronger bounded-degeneracy bound
for uniquely restrictive conflicts (which includes proper coloring), and its
proof also notes the elementary 2d+1-color greedy regime.  Our instances offer
only three colors, far below these sufficient bounds for the generated
multigraphs.  Theorem 3.1 treats general bounded restrictiveness and likewise
does not give a three-color algorithm here.  Section 1.1 identifies graph
3-coloring as an exact subproblem; classical graph 3-colorability is NP-complete.
The paper itself proves extremal existence bounds, not computational hardness.

Planting and attacks: a balanced coloring is drawn first and vertex labels are
scrambled.  Between every pair of planted classes we generate the same number
of random edge-disjoint perfect matchings, making every vertex have the same
degree and preventing degree/frequency outliers.  At medium and hard sizes the
last constraints are conditioned to remove every triangle, defeating the
obvious triangle-seed propagation attack; the order of the three class pairs is
randomized so the conditioned pair is not tied to a color label.  Input edges
are shuffled.  selftest measures a degree/order outlier rule, left-to-right
greedy coloring, and a multi-start min-conflicts heuristic on eight fresh seeds.
The generator's distribution has empirical, not reduction-based, average-case
hardness; worst-case hardness comes from the exact proper-coloring subfamily.
An earlier n=36 pilot was retired even though the LLM panel failed on it,
because the stronger local min-conflicts attack solved 5 of 8 fixed audit seeds.
"""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _random_perfect_matching(left, right, forbidden, rng):
    """Find a randomized perfect matching avoiding a set of ordered pairs."""
    left_order = list(left)
    rng.shuffle(left_order)
    choices = {}
    for u in left_order:
        allowed = [v for v in right if (u, v) not in forbidden]
        rng.shuffle(allowed)
        choices[u] = allowed

    owner = {}

    def augment(u, seen):
        for v in choices[u]:
            if v in seen:
                continue
            seen.add(v)
            if v not in owner or augment(owner[v], seen):
                owner[v] = u
                return True
        return False

    for u in left_order:
        if not augment(u, set()):
            return None
    return [(u, v) for v, u in owner.items()]


def _pair_matchings(left, right, layers, extra_forbidden, rng):
    """Generate edge-disjoint randomized perfect matchings."""
    used = set(extra_forbidden)
    result = []
    for _ in range(layers):
        matching = _random_perfect_matching(left, right, used, rng)
        if matching is None:
            return None
        result.extend(matching)
        used.update(matching)
    return result


def _build_constraints(classes, layers, triangle_free, rng):
    """Build regular cross-class constraints, retrying symmetric pair orders."""
    class_pairs = [(0, 1), (0, 2), (1, 2)]
    for _attempt in range(200):
        order = list(class_pairs)
        rng.shuffle(order)
        by_pair = {}
        all_edges = []
        failed = False
        for step, (a, b) in enumerate(order):
            forbidden = set()
            if triangle_free and step == 2:
                c = 3 - a - b
                ca = set()
                cb = set()
                for x, y in by_pair.get(tuple(sorted((a, c))), []):
                    if a < c:
                        ca.add((x, y))
                    else:
                        ca.add((y, x))
                for x, y in by_pair.get(tuple(sorted((b, c))), []):
                    if b < c:
                        cb.add((x, y))
                    else:
                        cb.add((y, x))
                a_to_c = {}
                b_to_c = {}
                for av, cv in ca:
                    a_to_c.setdefault(av, set()).add(cv)
                for bv, cv in cb:
                    b_to_c.setdefault(bv, set()).add(cv)
                c_to_b = {}
                for bv, cvs in b_to_c.items():
                    for cv in cvs:
                        c_to_b.setdefault(cv, set()).add(bv)
                for av, cvs in a_to_c.items():
                    for cv in cvs:
                        for bv in c_to_b.get(cv, ()):
                            forbidden.add((av, bv))

            edges = _pair_matchings(classes[a], classes[b], layers, forbidden, rng)
            if edges is None:
                failed = True
                break
            key = tuple(sorted((a, b)))
            if a < b:
                by_pair[key] = list(edges)
            else:
                by_pair[key] = [(v, u) for u, v in edges]
            all_edges.extend((min(u, v), max(u, v)) for u, v in edges)
        if failed:
            continue
        edge_set = set(all_edges)
        if len(edge_set) != 3 * len(classes[0]) * layers:
            continue
        if triangle_free and _triangle_count(3 * len(classes[0]), edge_set):
            continue
        return list(edge_set)
    raise ValueError("could not construct the requested regular constraint graph")


def _triangle_count(num_vertices, edges):
    adj = [set() for _ in range(num_vertices)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    total = 0
    for u in range(num_vertices):
        for v in adj[u]:
            if u < v:
                total += len(adj[u].intersection(adj[v]))
    return total // 3


def make_instance(n, seed=0, matchings=4, triangle_free=True, **params):
    """Draw a balanced answer first, then build constraints that it satisfies.

    ``n`` is the number of vertices in each of the three hidden color classes;
    the rendered graph therefore has ``3*n`` vertices.  Increasing ``n`` grows
    the fixed-density constraint system while preserving satisfiability.
    """
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if isinstance(matchings, bool) or not isinstance(matchings, int):
        raise ValueError("matchings must be an integer")
    if not 1 <= matchings < n:
        raise ValueError("matchings must satisfy 1 <= matchings < n")
    if not isinstance(triangle_free, bool):
        raise ValueError("triangle_free must be boolean")

    rng = random.Random(seed)
    num_colors = 3
    num_vertices = num_colors * n

    # G requires answer-first construction.  This shuffle is deliberately the
    # first random object drawn; all constraints are sampled afterward.
    answer = [c for c in range(num_colors) for _ in range(n)]
    rng.shuffle(answer)
    classes = [[v for v, c in enumerate(answer) if c == color]
               for color in range(num_colors)]

    edges = _build_constraints(classes, matchings, triangle_free, rng)
    rng.shuffle(edges)
    return {
        "paper": "arXiv:2112.06333",
        "family": "proper-3-coloring-as-single-conflict-coloring",
        "class_size": n,
        "num_vertices": num_vertices,
        "num_colors": num_colors,
        "matchings": matchings,
        "triangle_free": triangle_free,
        "edges": [[u, v] for u, v in edges],
        "answer": answer,
    }


def render(inst):
    """Render a complete, unambiguous solver-facing problem statement."""
    n = inst["num_vertices"]
    q = inst["num_colors"]
    lines = [
        "Single-conflict coloring witness problem",
        "",
        f"There are {n} vertices, numbered 0 through {n - 1}, and {q} colors,",
        f"numbered 0 through {q - 1}. A coloring assigns exactly one color to",
        "every vertex. Colors may be reused, and the coloring need not use every color.",
        "",
        "A conflict edge has two endpoints and one forbidden ordered color pair.",
        "For each unordered constraint pair `u v` listed below (always u < v),",
        f"there are exactly {q} parallel conflict edges. For color c in",
        f"{{0, ..., {q - 1}}}, the c-th parallel edge forbids (c,c) from u to v;",
        "the reverse orientation forbids the reversed pair, which is also (c,c).",
        "Thus a coloring is valid exactly when every listed pair has differently",
        "colored endpoints. The order of the listed pairs has no meaning.",
        "",
        f"CONSTRAINT_PAIRS {len(inst['edges'])}",
    ]
    lines.extend(f"{u} {v}" for u, v in inst["edges"])
    lines.extend([
        "END_CONSTRAINT_PAIRS",
        "",
        f"Output exactly {n} base-10 integers. Integer number v is the color of",
        "vertex v, so order matters and vertices are 0-indexed. Separate integers",
        "with commas. Do not include vertex numbers, brackets, or repeated entries.",
        "",
        "Give your final answer inside <answer></answer> tags, as a comma-separated",
        "list of colors in vertex order.",
        "Example of the format only: <answer>0, 2, 1, 0</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last well-formed tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body or not re.fullmatch(r"\d+(?:\s*,\s*\d+)*", body):
        return None
    try:
        return [int(part.strip()) for part in body.split(",")]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst, answer):
    """Verify any valid coloring without consulting the planted answer."""
    if not isinstance(answer, list):
        return False, "answer_not_a_list"
    if not answer:
        return False, "empty_answer"
    n = inst["num_vertices"]
    if len(answer) < n:
        return False, f"too_few_colors:{len(answer)}<{n}"
    if len(answer) > n:
        return False, f"too_many_colors:{len(answer)}>{n}"
    q = inst["num_colors"]
    for v, color in enumerate(answer):
        if isinstance(color, bool) or not isinstance(color, int):
            return False, f"color_not_integer_at_vertex:{v}"
        if not 0 <= color < q:
            return False, f"color_out_of_range_at_vertex:{v}"
    for u, v in inst["edges"]:
        if answer[u] == answer[v]:
            return False, f"forbidden_conflict_on_pair:{u},{v}"
    return True, "ok"


def _canonicalize_color_names(colors, q):
    mapping = {}
    next_name = 0
    out = []
    for color in colors:
        if color not in mapping:
            mapping[color] = next_name
            next_name += 1
        out.append(mapping[color])
    return out


def random_candidate(inst, rng):
    """Sample a shape-valid coloring after removing global color-name symmetry."""
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange")
    q = inst["num_colors"]
    raw = [rng.randrange(q) for _ in range(inst["num_vertices"])]
    return _canonicalize_color_names(raw, q)


def search_space(inst):
    """Return the naive labeled-coloring space size."""
    return inst["num_colors"] ** inst["num_vertices"]


def enumerate_all(inst):
    """Count all labeled valid colorings exactly when at most 2M trials suffice."""
    n = inst["num_vertices"]
    q = inst["num_colors"]
    reduced = q ** (n - 1)
    if reduced > 2_000_000:
        return None
    count_first_zero = 0
    for tail in itertools.product(range(q), repeat=n - 1):
        colors = (0,) + tail
        if all(colors[u] != colors[v] for u, v in inst["edges"]):
            count_first_zero += 1
    # Color names are symmetric, so each possible color at vertex 0 has the
    # same number of extensions.
    return q * count_first_zero


def canonical_key(inst):
    """A relabelling-invariant structural fingerprint of the conflict graph.

    Exact graph isomorphism is not known to be cheaply canonicalizable.  This
    key seeds Weisfeiler--Lehman refinement with invariant common-neighbor and
    distance profiles.  It can theoretically collide on non-isomorphic graphs;
    unlike a seed/render hash, it is invariant under every vertex relabelling.
    """
    n = inst["num_vertices"]
    adj = [set() for _ in range(n)]
    for edge in inst["edges"]:
        u, v = edge
        adj[u].add(v)
        adj[v].add(u)
    bits = []
    for neighbors in adj:
        value = 0
        for v in neighbors:
            value |= 1 << v
        bits.append(value)

    labels = []
    for u in range(n):
        common_hist = Counter((bits[u] & bits[v]).bit_count()
                              for v in range(n) if v != u)
        # Breadth-first layer sizes are another cheap rooted invariant.
        seen = {u}
        frontier = {u}
        layers = []
        while frontier:
            nxt = set()
            for v in frontier:
                nxt.update(adj[v])
            nxt.difference_update(seen)
            if not nxt:
                break
            layers.append(len(nxt))
            seen.update(nxt)
            frontier = nxt
        base = (len(adj[u]), tuple(sorted(common_hist.items())), tuple(layers))
        labels.append(hashlib.sha256(repr(base).encode()).hexdigest())

    history = []
    for _ in range(n):
        hist = tuple(sorted(Counter(labels).items()))
        history.append(hist)
        refined = []
        for u in range(n):
            signature = (labels[u], tuple(sorted(labels[v] for v in adj[u])))
            refined.append(hashlib.sha256(repr(signature).encode()).hexdigest())
        if refined == labels:
            break
        labels = refined

    payload = {
        "vertices": n,
        "colors": inst["num_colors"],
        "edges": sum(len(a) for a in adj) // 2,
        "degrees": sorted(len(a) for a in adj),
        "wl": history,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def escalate(params):
    """Increase the number of variables at the same satisfiable hard density."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    if n >= 180:
        return None
    harder = dict(params)
    harder["n"] = max(n + 1, (3 * n) // 2)
    return harder


def _adjacency(inst):
    adj = [set() for _ in range(inst["num_vertices"])]
    for u, v in inst["edges"]:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _attack_outlier(inst):
    """Balanced coloring from degree and first-appearance ranks."""
    n = inst["num_vertices"]
    q = inst["num_colors"]
    degree = [0] * n
    first = [len(inst["edges"])] * n
    for pos, (u, v) in enumerate(inst["edges"]):
        degree[u] += 1
        degree[v] += 1
        first[u] = min(first[u], pos)
        first[v] = min(first[v], pos)
    order = sorted(range(n), key=lambda v: (degree[v], first[v], v))
    answer = [0] * n
    for rank, v in enumerate(order):
        answer[v] = min(q - 1, rank * q // n)
    return answer


def _attack_greedy(inst):
    """Obvious left-to-right first-fit, with a least-conflict fallback."""
    n = inst["num_vertices"]
    q = inst["num_colors"]
    adj = _adjacency(inst)
    colors = [-1] * n
    for v in range(n):
        counts = [0] * q
        for u in adj[v]:
            if colors[u] >= 0:
                counts[colors[u]] += 1
        colors[v] = min(range(q), key=lambda c: (counts[c], c))
    return colors


def _attack_random_restart(inst, rng, restarts=16, steps_per_vertex=20):
    """A bounded min-conflicts local search with random restarts and mild noise."""
    n = inst["num_vertices"]
    q = inst["num_colors"]
    adj = _adjacency(inst)
    best = None
    best_bad = math.inf
    for _ in range(restarts):
        colors = [rng.randrange(q) for _ in range(n)]
        for _step in range(steps_per_vertex * n):
            bad_vertices = [v for v in range(n)
                            if any(colors[v] == colors[u] for u in adj[v])]
            if not bad_vertices:
                return colors
            v = rng.choice(bad_vertices)
            conflict_counts = [sum(colors[u] == c for u in adj[v])
                               for c in range(q)]
            minimum = min(conflict_counts)
            choices = [c for c, count in enumerate(conflict_counts)
                       if count == minimum]
            if rng.random() < 0.08:
                colors[v] = rng.randrange(q)
            else:
                colors[v] = rng.choice(choices)
        bad = sum(colors[u] == colors[v] for u, v in inst["edges"])
        if bad < best_bad:
            best_bad = bad
            best = list(colors)
    return best


def _find_bad_swap(inst):
    planted = inst["answer"]
    n = inst["num_vertices"]
    for u in range(n):
        for v in range(u + 1, n):
            if planted[u] == planted[v]:
                continue
            trial = list(planted)
            trial[u], trial[v] = trial[v], trial[u]
            ok, reason = verify(inst, trial)
            if not ok and reason.startswith("forbidden_conflict"):
                return trial
    raise AssertionError("could not find a conflict-producing swap")


def _relabel_instance(inst, permutation, edge_rng):
    """Carry an instance and its witness through old->new vertex labels."""
    n = inst["num_vertices"]
    moved = {k: (list(v) if isinstance(v, list) else v)
             for k, v in inst.items() if k not in ("edges", "answer")}
    edges = [(min(permutation[u], permutation[v]),
              max(permutation[u], permutation[v])) for u, v in inst["edges"]]
    edge_rng.shuffle(edges)
    answer = [0] * n
    for old, new in enumerate(permutation):
        answer[new] = inst["answer"][old]
    moved["edges"] = [[u, v] for u, v in edges]
    moved["answer"] = answer
    return moved


def selftest():
    """Run mandatory G1--G8 gates and return their measured results."""
    report = {}

    # G1: every preset, several unrelated seeds.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "checks": g1_checks, "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=202603, **shipping)

    # G2: five corruption modes with five distinct rejection reasons.
    planted = list(inst["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": _find_bad_swap(inst),
        "duplicate_one": planted + [planted[0]],
        "empty": [],
        "out_of_range": [inst["num_colors"]] + planted[1:],
    }
    g2 = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    g2_pass = all(row["rejected"] for row in g2.values()) and len(set(reasons)) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_pass, "distinct_reasons": len(set(reasons)), "cases": g2,
    }

    # G3: realistic prose and markdown around the wire-format answer.
    body = ", ".join(map(str, planted))
    response = "Here is the coloring I found.\n```text\n<answer>" + body + "</answer>\n```\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted, "parsed_length": len(parsed) if parsed else None,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    # G4: the sampler removes the freely available global color-name symmetry.
    guess_rng = random.Random(904_2112)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "measured_probability": probability,
        "sampler": "independent colors modulo global color-label symmetry",
        "naive_search_space": search_space(inst),
    }

    # G5: exact enumeration on the only feasible preset.
    tiny = make_instance(seed=73, **DIFFICULTY["tiny"])
    exact = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    fraction = exact / tiny_space if exact is not None else None
    report["G5_sparse"] = {
        "pass": exact is not None and fraction < 0.01,
        "preset": "tiny", "valid_answers": exact,
        "naive_search_space": tiny_space, "solution_fraction": fraction,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: construction-aware attacks on eight independent shipping instances.
    attack_rows = {
        "degree_and_input_order_outlier": [],
        "left_to_right_greedy": [],
        "random_restart_min_conflicts": [],
        "triangle_seed_available": [],
    }
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **shipping)
        attack_rows["degree_and_input_order_outlier"].append(
            verify(attacked, _attack_outlier(attacked))[0])
        attack_rows["left_to_right_greedy"].append(
            verify(attacked, _attack_greedy(attacked))[0])
        rr = _attack_random_restart(attacked, random.Random(seed ^ 0x5A17))
        attack_rows["random_restart_min_conflicts"].append(verify(attacked, rr)[0])
        triangle_attack_solved = _triangle_count(
            attacked["num_vertices"], {tuple(e) for e in attacked["edges"]}) > 0
        attack_rows["triangle_seed_available"].append(triangle_attack_solved)
    attacks = {}
    for name, solved_flags in attack_rows.items():
        attacks[name] = {
            "solved": sum(solved_flags), "trials": len(solved_flags),
            "all_failed": not any(solved_flags),
        }
    report["G6_adversary_panel"] = {
        "pass": all(row["all_failed"] for row in attacks.values()),
        "attacks": attacks,
        "random_restart_budget": "16 restarts x 20*N recolor steps, 8% noise",
        "degree_uniform": len({sum(v in e for e in inst["edges"])
                               for v in range(inst["num_vertices"])}) == 1,
    }

    # G7: double n at fixed density and verify construction and witness.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=707, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["num_vertices"] == 2 * inst["num_vertices"]
                and len(doubled["edges"]) == 2 * len(inst["edges"]),
        "base_vertices": inst["num_vertices"],
        "doubled_vertices": doubled["num_vertices"],
        "base_constraints": len(inst["edges"]),
        "doubled_constraints": len(doubled["edges"]),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: vertex relabelling, edge reordering, color symmetry, compositions.
    invariant_checks = 0
    real_transform_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(9200, 9220):
        base = make_instance(seed=seed, **shipping)
        key = canonical_key(base)
        unrelated_keys.append(key)
        trng = random.Random(seed ^ 0xC4110)
        perm = list(range(base["num_vertices"]))
        trng.shuffle(perm)
        moved = _relabel_instance(base, perm, trng)
        reordered = dict(base)
        reordered["edges"] = list(reversed(base["edges"]))
        color_perm = [2, 0, 1]
        recolored = dict(base)
        recolored["answer"] = [color_perm[c] for c in base["answer"]]
        composed = _relabel_instance(recolored, perm, trng)
        for label, transformed in (("vertex", moved), ("edge_order", reordered),
                                   ("color", recolored), ("composed", composed)):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append([seed, label, "key_changed"])
            real_transform_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append([seed, label, reason])
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transform_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
        "caveat": "rooted-profile + WL invariant; not a complete GI canonical form",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
