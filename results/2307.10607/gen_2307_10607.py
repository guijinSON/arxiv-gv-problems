"""Verified planted instances for arXiv:2307.10607.

The family is the Section 3.1 Red-Blue Dominating Set gadget, restricted to
3-uniform set systems with 3q elements and budget q.  Such a dominating set is
an exact cover.  A q-set exact cover expands to the spanning-tree contractions
used in Lemma 12 and contracts the gadget graph to a star K_{1,*}.
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
    "demo": {"n": 4, "set_factor": 3},
    "easy": {"n": 18, "set_factor": 6},
    "medium": {"n": 28, "set_factor": 6},
    "hard": {"n": 42, "set_factor": 6},
}

SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Paper reading and design notes
------------------------------
Section 2.1, Definition 7 and Lemma 8 fix the exact certificate semantics:
contracting to a biclique is equivalent to a partition whose induced spanning
forests use at most k edges and whose cross-side components are all adjacent.
Section 3.1, especially Lemma 12, gives the bipartite Red-Blue Dominating Set
gadget used here.  A dominating set S makes S union B union {x} one connected
witness set; its spanning tree has |B|+|S| edges and every other vertex is a
singleton leaf of the resulting star.

The source set systems here have 3q elements, q planted disjoint triples, and
only triples as candidate sets.  Therefore any q-set cover is automatically an
exact cover.  The submitted q identifiers are a compact contraction witness:
the checker expands them to x--S_j for selected j and B_i--S_j for the unique
selected triple containing i, then independently contracts and checks the
quotient star.

The easy regime that matters is Theorem 2 in Section 4 (both biclique variants
are FPT in k, in O*(25.904^k)) and, more sharply for this target, Lemma 20 and
Theorem 5 in Section 6.2 (K_{1,*}-Contraction is solvable in O*(2^k)).  Thus k
is never held constant: here k=4q grows linearly with the size parameter q.
The fixed-target K_{p,q} brute force noted after Lemma 10 is also avoided; the
number of leaves in the target star grows with q.

Leakage countermeasures and attacks: all planted and decoy objects are distinct
uniform 3-subsets (decoys are jointly conditioned only to give every element a
second occurrence, as assumed in Lemma 12), identifiers and element labels are
shuffled, and no answer data is rendered.  The outlier attack ranks triples by
the degrees of their elements; rarest-first exact-cover greedy is the obvious
left-to-right attack; random restart repeatedly shuffles and greedily packs
disjoint triples.  selftest requires all three to fail on at least eight seeds.

The canonical key uses invariant color refinement of the set-element incidence
graph.  Exact hypergraph isomorphism is not attempted; color refinement is a
strong cheap invariant and can collide on specially constructed non-isomorphic
systems.  selftest covers arbitrary element relabelling, set reordering, their
compositions, carried witnesses, and unrelated-seed distinctness.
"""


def _normalise_sets(inst: dict) -> list[tuple[int, int, int]]:
    """Return the set system in a representation independent of row internals."""

    return [tuple(sorted(int(x) for x in row)) for row in inst["sets"]]


def _draw_decoys(
    q: int,
    total_sets: int,
    planted: set[tuple[int, int, int]],
    rng: random.Random,
) -> list[tuple[int, int, int]]:
    """Draw uniform distinct non-planted triples, conditioned on full support."""

    element_count = 3 * q
    needed = total_sets - q
    if needed < 1:
        raise ValueError("set_factor must leave room for decoys")

    # Whole-sample rejection avoids special repair triples.  At the shipped
    # factor every element has about five decoy incidences, so this succeeds
    # quickly.  The small demo also has ample probability of full support.
    for _ in range(10_000):
        decoys: set[tuple[int, int, int]] = set()
        seen = [0] * element_count
        while len(decoys) < needed:
            triple = tuple(sorted(rng.sample(range(element_count), 3)))
            if triple in planted or triple in decoys:
                continue
            decoys.add(triple)
            for x in triple:
                seen[x] += 1
        if all(seen):
            rows = list(decoys)
            rng.shuffle(rows)
            return rows
    raise RuntimeError("could not draw a full-support decoy system")


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant an exact cover first, then construct its contraction gadget.

    ``n`` is q: the answer contains q triples and the universe has 3q elements.
    Larger q increases both the exact-cover search space and contraction budget.
    ``set_factor`` is the number of candidate triples divided by q.
    """

    try:
        q = int(n)
        set_factor = int(params.pop("set_factor", 6))
    except (TypeError, ValueError) as exc:
        raise ValueError("n and set_factor must be integers") from exc
    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    if q < 3:
        raise ValueError("n must be at least 3")
    if set_factor < 2:
        raise ValueError("set_factor must be at least 2")

    element_count = 3 * q
    total_sets = set_factor * q
    if total_sets > math.comb(element_count, 3):
        raise ValueError("too many distinct triples for this n")
    rng = random.Random(seed)

    # G: sample the answer before any decoy.  A random permutation split into
    # blocks of three is a uniformly random exact cover of the labelled universe.
    order = list(range(element_count))
    rng.shuffle(order)
    planted_rows = [tuple(sorted(order[3 * i:3 * i + 3])) for i in range(q)]
    planted = set(planted_rows)

    decoys = _draw_decoys(q, total_sets, planted, rng)
    tagged = [(row, True) for row in planted_rows]
    tagged.extend((row, False) for row in decoys)
    rng.shuffle(tagged)

    # A final uniform relabelling separates construction order from rendered
    # element labels.  It preserves both the planted partition and all decoys.
    labels = list(range(element_count))
    rng.shuffle(labels)
    rows: list[list[int]] = []
    answer: list[int] = []
    for sid, (row, is_planted) in enumerate(tagged):
        rows.append(sorted(labels[x] for x in row))
        if is_planted:
            answer.append(sid)

    answer.sort()
    return {
        "paper": "arXiv:2307.10607",
        "family": "bipartite K1,* contraction via 3-uniform exact cover",
        "n": q,
        "seed": int(seed),
        "set_factor": set_factor,
        "num_elements": element_count,
        "num_sets": total_sets,
        "k": 4 * q,
        "sets": rows,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete implicit graph and the contraction-certificate format."""

    q = int(inst["n"])
    v = int(inst["num_elements"])
    m = int(inst["num_sets"])
    k = int(inst["k"])
    rows = _normalise_sets(inst)
    lines = [
        "Find an edge-contraction witness that turns the graph below into a star.",
        "A star is a complete bipartite graph K_{1,t}: one centre adjacent to every",
        "other vertex, with no edges among the other vertices.",
        "",
        "The graph is specified compactly but completely.",
        f"There are {v} element vertices B0,...,B{v - 1}; matching pendant vertices",
        f"P0,...,P{v - 1}; {m} set vertices S0,...,S{m - 1}; one vertex x; and",
        f"{k + 1} guard leaves C0,...,C{k}.",
        "Its undirected edges are exactly these (there are no other edges):",
        f"  * x--Sj for every set ID j from 0 through {m - 1};",
        f"  * x--Ch for every guard index h from 0 through {k};",
        f"  * Bi--Pi for every element index i from 0 through {v - 1};",
        "  * Sj--Bi exactly when element i occurs in the triple listed for Sj.",
        f"The contraction budget is k={k}. Contracting an edge merges its endpoints;",
        "the merged vertex is adjacent to the union of their former neighbours, and",
        "self-loops and parallel copies are discarded.",
        "",
        "Return a compact witness consisting of exactly",
        f"q={q} distinct set IDs. The checker expands it into these contractions:",
        "  1. contract x--Sj for every returned set ID j;",
        "  2. for every element i, contract Bi--Sj where j is the unique returned",
        "     set whose listed triple contains i.",
        f"Thus the expanded witness has exactly q+{v}={k} edges. It is accepted only",
        "if every element has exactly one such selected set and replaying the",
        "contractions produces a star. The order of returned IDs does not matter.",
        "Set IDs and element IDs are 0-indexed; repeated IDs are forbidden.",
        "",
        "Candidate triples (format: set ID: three element IDs):",
    ]
    lines.extend(f"S{j}: {a} {b} {c}" for j, (a, b, c) in enumerate(rows))
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags, as exactly q",
            "comma-separated set IDs, with no S prefix.",
            "Example: <answer>3, 17, 42, 8</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse one tagged comma/whitespace-separated integer list without raising."""

    try:
        if not isinstance(text, str):
            return None
        matches = re.findall(
            r"<answer\b[^>]*>(.*?)</answer\s*>", text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not matches:
            return None
        body = matches[-1].strip()
        fence = re.fullmatch(r"```(?:text|json)?\s*(.*?)\s*```", body,
                             flags=re.IGNORECASE | re.DOTALL)
        if fence:
            body = fence.group(1).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        tokens = [tok for tok in re.split(r"[\s,]+", body) if tok]
        if not tokens or any(re.fullmatch(r"[+-]?\d+", tok) is None for tok in tokens):
            return None
        return [int(tok) for tok in tokens]
    except Exception:
        return None


def _layout(inst: dict) -> dict[str, int]:
    m = int(inst["num_sets"])
    v = int(inst["num_elements"])
    return {
        "x": 0,
        "sets": 1,
        "elements": 1 + m,
        "pendants": 1 + m + v,
        "guards": 1 + m + 2 * v,
        "vertices": 1 + m + 2 * v + int(inst["k"]) + 1,
    }


def _gadget_edges(inst: dict) -> list[tuple[int, int]]:
    """Expand the compact Section 3.1 graph into integer-labelled edges."""

    lay = _layout(inst)
    m = int(inst["num_sets"])
    v = int(inst["num_elements"])
    k = int(inst["k"])
    edges: list[tuple[int, int]] = []
    for j in range(m):
        edges.append((lay["x"], lay["sets"] + j))
    for h in range(k + 1):
        edges.append((lay["x"], lay["guards"] + h))
    for i in range(v):
        edges.append((lay["elements"] + i, lay["pendants"] + i))
    for j, row in enumerate(_normalise_sets(inst)):
        for i in row:
            edges.append((lay["sets"] + j, lay["elements"] + i))
    return edges


def _expanded_witness(inst: dict, selected: list[int]) -> list[tuple[int, int]] | None:
    lay = _layout(inst)
    v = int(inst["num_elements"])
    rows = _normalise_sets(inst)
    owner = [-1] * v
    for j in selected:
        for i in rows[j]:
            if owner[i] != -1:
                return None
            owner[i] = j
    if any(j < 0 for j in owner):
        return None
    contractions = [(lay["x"], lay["sets"] + j) for j in selected]
    contractions.extend(
        (lay["elements"] + i, lay["sets"] + owner[i]) for i in range(v)
    )
    return contractions


def _quotient_is_star(inst: dict, contractions: list[tuple[int, int]]) -> tuple[bool, str]:
    """Union the selected original edges, recompute the quotient, and test K1,t."""

    lay = _layout(inst)
    vertex_count = lay["vertices"]
    parent = list(range(vertex_count))
    size = [1] * vertex_count

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> bool:
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]
        return True

    graph_edges = _gadget_edges(inst)
    edge_set = {tuple(sorted(e)) for e in graph_edges}
    for u, v in contractions:
        if tuple(sorted((u, v))) not in edge_set:
            return False, "expanded certificate contains a non-edge"
        if not union(u, v):
            return False, "expanded contractions contain a cycle or repeated merge"

    roots = sorted({find(x) for x in range(vertex_count)})
    root_id = {root: i for i, root in enumerate(roots)}
    quotient = [set() for _ in roots]
    for u, v in graph_edges:
        a, b = root_id[find(u)], root_id[find(v)]
        if a != b:
            quotient[a].add(b)
            quotient[b].add(a)

    centre = root_id[find(lay["x"])]
    leaf_count = len(roots) - 1
    if len(quotient[centre]) != leaf_count:
        return False, "quotient centre is not adjacent to every other vertex"
    for node in range(len(roots)):
        if node != centre and quotient[node] != {centre}:
            return False, "quotient has a non-leaf vertex away from the centre"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept every valid compact contraction witness, never consulting the plant."""

    q = int(inst["n"])
    m = int(inst["num_sets"])
    if not isinstance(answer, list):
        return False, "malformed answer: expected a list of integer set IDs"
    if len(answer) == 0:
        return False, "empty answer: expected q selected set IDs"
    if len(answer) != q:
        return False, f"wrong length: expected {q} set IDs, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "malformed item: every set ID must be an integer"
    for x in answer:
        if x < 0 or x >= m:
            return False, f"out of range: set ID {x} is not in 0..{m - 1}"
    if len(set(answer)) != q:
        return False, "duplicate set ID: repeats are forbidden"

    rows = _normalise_sets(inst)
    counts = [0] * int(inst["num_elements"])
    for j in answer:
        for i in rows[j]:
            counts[i] += 1
    uncovered = next((i for i, count in enumerate(counts) if count == 0), None)
    if uncovered is not None:
        return False, f"not an exact cover: element {uncovered} is uncovered"
    repeated = next((i for i, count in enumerate(counts) if count != 1), None)
    if repeated is not None:
        return False, f"not an exact cover: element {repeated} is covered more than once"

    contractions = _expanded_witness(inst, answer)
    if contractions is None:
        return False, "could not expand the exact-cover certificate"
    if len(contractions) > int(inst["k"]):
        return False, "expanded certificate exceeds the contraction budget"
    return _quotient_is_star(inst, contractions)


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the shape-aware q-subset space.

    A candidate already has exactly q distinct in-range IDs.  Since every input
    row has arity three and there are 3q elements, no smaller or larger selector
    is relevant.  Finding q mutually disjoint rows is the exact-cover problem
    itself and is intentionally not conditioned on here.
    """

    return sorted(rng.sample(range(int(inst["num_sets"])), int(inst["n"])))


def search_space(inst: dict) -> int | None:
    return math.comb(int(inst["num_sets"]), int(inst["n"]))


def enumerate_all(inst: dict) -> int | None:
    """Count exact covers when at most two million q-subsets need inspection."""

    q = int(inst["n"])
    m = int(inst["num_sets"])
    space = math.comb(m, q)
    if space > 2_000_000:
        return None
    full = (1 << int(inst["num_elements"])) - 1
    masks = []
    for row in _normalise_sets(inst):
        mask = 0
        for x in row:
            mask |= 1 << x
        masks.append(mask)
    count = 0
    for choice in itertools.combinations(range(m), q):
        union = 0
        disjoint = True
        for j in choice:
            if union & masks[j]:
                disjoint = False
                break
            union |= masks[j]
        if disjoint and union == full:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """A label/order-invariant color-refinement key for the incidence graph."""

    rows = _normalise_sets(inst)
    v = int(inst["num_elements"])
    m = len(rows)
    adjacency = [[] for _ in range(v + m)]
    for j, row in enumerate(rows):
        snode = v + j
        for x in row:
            adjacency[snode].append(x)
            adjacency[x].append(snode)

    # Types are distinct initially.  Canonical integer colors are reassigned by
    # sorting signatures, so neither vertex labels nor set-row order can matter.
    colors = [0] * v + [1] * m
    profiles = []
    for _ in range(12):
        signatures = [
            (colors[node], tuple(sorted(colors[nei] for nei in adjacency[node])))
            for node in range(v + m)
        ]
        unique = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        colors = [unique[sig] for sig in signatures]
        profiles.append(sorted(Counter(signatures).items()))

    final_neighbourhoods = sorted(
        (colors[node], tuple(sorted(colors[nei] for nei in adjacency[node])))
        for node in range(v + m)
    )
    # Encode tuples via repr: all atoms are non-negative integers and tuple/list
    # boundaries are unambiguous.  The hash is only a compact form of this
    # structural invariant; neither seed nor rendered text is included.
    payload = repr((v, m, profiles, final_neighbourhoods)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase q, the exact-cover dimension and the linearly related k."""

    q = int(params.get("n", 0))
    factor = int(params.get("set_factor", 6))
    if q >= 128:
        return None
    harder = max(q + 1, (3 * q + 1) // 2)
    return {"n": min(harder, 128), "set_factor": factor}


def _outlier_attack(inst: dict) -> list[int]:
    """Choose triples with the rarest-looking element-degree profile."""

    rows = _normalise_sets(inst)
    degree = [0] * int(inst["num_elements"])
    for row in rows:
        for x in row:
            degree[x] += 1
    ranked = sorted(
        range(len(rows)),
        key=lambda j: (-sum(1.0 / degree[x] for x in rows[j]), j),
    )
    return sorted(ranked[:int(inst["n"])])


def _greedy_attack(inst: dict) -> list[int]:
    """Rarest-uncovered-element, least-conflicting exact-cover greedy."""

    rows = _normalise_sets(inst)
    v = int(inst["num_elements"])
    q = int(inst["n"])
    incidence = [[] for _ in range(v)]
    for j, row in enumerate(rows):
        for x in row:
            incidence[x].append(j)
    used_elements: set[int] = set()
    chosen: list[int] = []
    while len(chosen) < q:
        available = [
            j for j, row in enumerate(rows)
            if j not in chosen and not (used_elements & set(row))
        ]
        if not available:
            break
        available_set = set(available)
        uncovered = [x for x in range(v) if x not in used_elements]
        pivot = min(
            uncovered,
            key=lambda x: (sum(j in available_set for j in incidence[x]), x),
        )
        options = [j for j in incidence[pivot] if j in available_set]
        if not options:
            break
        choice = min(
            options,
            key=lambda j: (
                sum(len(incidence[x]) for x in rows[j]),
                sum(len(set(rows[j]) & set(rows[t])) for t in available),
                j,
            ),
        )
        chosen.append(choice)
        used_elements.update(rows[choice])
    # Preserve the required output shape even when greedy gets stuck.
    for j in range(len(rows)):
        if len(chosen) == q:
            break
        if j not in chosen:
            chosen.append(j)
    return sorted(chosen)


def _random_restart_attack(inst: dict, rng: random.Random, restarts: int = 256) -> list[int]:
    """Repeated random-order disjoint packing; return immediately on a solution."""

    rows = _normalise_sets(inst)
    q = int(inst["n"])
    best: list[int] = []
    for _ in range(restarts):
        order = list(range(len(rows)))
        rng.shuffle(order)
        used: set[int] = set()
        chosen: list[int] = []
        for j in order:
            if not (used & set(rows[j])):
                chosen.append(j)
                used.update(rows[j])
                if len(chosen) == q:
                    candidate = sorted(chosen)
                    if verify(inst, candidate)[0]:
                        return candidate
                    break
        if len(chosen) > len(best):
            best = chosen
    for j in range(len(rows)):
        if len(best) == q:
            break
        if j not in best:
            best.append(j)
    return sorted(best[:q])


def _relabel_instance(
    inst: dict,
    element_old_to_new: list[int],
    set_new_order: list[int],
) -> tuple[dict, list[int]]:
    """Apply both incidence-graph relabellings and carry the witness through."""

    old_rows = _normalise_sets(inst)
    old_to_new_set = {old: new for new, old in enumerate(set_new_order)}
    new_rows = [
        sorted(element_old_to_new[x] for x in old_rows[old])
        for old in set_new_order
    ]
    transformed = dict(inst)
    transformed["sets"] = new_rows
    transformed["answer"] = sorted(old_to_new_set[j] for j in inst["answer"])
    return transformed, transformed["answer"][:]


def selftest() -> dict:
    """Run gates G1--G8 and return a JSON-serialisable evidence dictionary."""

    report: dict[str, object] = {}

    # G1: every named preset and several seeds.
    g1_total = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "verified": g1_total, "failures": g1_failures,
    }

    shipping = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    probe = make_instance(seed=1234567, **shipping)
    plant = probe["answer"][:]
    nonplant = next(j for j in range(probe["num_sets"]) if j not in set(plant))
    corruptions = {
        "drop_one": plant[:-1],
        "replace_one": plant[:-1] + [nonplant],
        "duplicate": plant[:-1] + [plant[0]],
        "empty": [],
        "out_of_range": plant[:-1] + [probe["num_sets"]],
    }
    g2 = {}
    for name, candidate in corruptions.items():
        ok, why = verify(probe, candidate)
        g2[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in g2.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in g2.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": g2,
    }

    realistic = (
        "I used the pendant guards to identify the centre and found this exact cover.\n\n"
        "```text\nFinal response follows.\n```\n"
        f"<answer>\n```json\n{json.dumps(plant)}\n```\n</answer>\n"
        "Those IDs are unordered."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == plant and parse_answer("unstructured garbage") is None,
        "parsed_items": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("unstructured garbage") is None,
    }

    # G4: candidate has exact size, uniqueness, and range already enforced.
    guess_rng = random.Random(0x230710607)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(probe, guess_rng)
        if verify(probe, candidate)[0]:
            guess_hits += 1
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "rate": guess_hits / guess_total,
        "prior": "uniform q-subsets: exact length, distinctness, and range enforced",
        "naive_space": search_space(probe),
    }

    # G5: the demo is deliberately the only exhaustively countable preset.
    sparse_rows = []
    sparse_ok = True
    for seed in (3, 5, 8):
        small = make_instance(seed=seed, **DIFFICULTY["demo"])
        solutions = enumerate_all(small)
        space = search_space(small)
        fraction = None if solutions is None else solutions / space
        sparse_rows.append({
            "seed": seed, "solutions": solutions, "search_space": space,
            "fraction": fraction,
        })
        sparse_ok = sparse_ok and solutions is not None and fraction is not None and fraction < 0.01
    report["G5_sparse"] = {"pass": sparse_ok, "enumerated": sparse_rows}

    attack_trials = 8
    attack_success = {"degree_outlier": 0, "rarest_first_greedy": 0,
                      "random_restart_256": 0}
    attack_details = []
    for seed in range(80, 80 + attack_trials):
        inst = make_instance(seed=seed, **shipping)
        candidates = {
            "degree_outlier": _outlier_attack(inst),
            "rarest_first_greedy": _greedy_attack(inst),
            "random_restart_256": _random_restart_attack(
                inst, random.Random(0xBAD5EED + seed), 256
            ),
        }
        seed_result = {}
        for name, candidate in candidates.items():
            ok, why = verify(inst, candidate)
            attack_success[name] += int(ok)
            seed_result[name] = {"solved": ok, "reason": why}
        attack_details.append({"seed": seed, "attacks": seed_result})
    report["G6_adversary_panel"] = {
        "pass": all(hits == 0 for hits in attack_success.values()),
        "trials_per_attack": attack_trials,
        "successes": attack_success,
        "details": attack_details,
    }

    base = make_instance(seed=2468, **shipping)
    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * int(shipping["n"])
    doubled = make_instance(seed=2468, **doubled_params)
    base_ok = verify(base, base["answer"])[0]
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": base_ok and doubled_ok
        and doubled["k"] > base["k"]
        and search_space(doubled) > search_space(base),
        "base_n": base["n"], "doubled_n": doubled["n"],
        "base_k": base["k"], "doubled_k": doubled["k"],
        "base_space": search_space(base),
        "doubled_space": search_space(doubled),
    }

    # G8: 20 seeds, three non-identity relabellings each, plus a carried witness.
    invariant_checks = 0
    real_transform_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **shipping)
        key = canonical_key(inst)
        keys.append(key)
        rr = random.Random(0xC4A0 + seed)
        element_perm = list(range(inst["num_elements"]))
        rr.shuffle(element_perm)
        set_order = list(range(inst["num_sets"]))
        rr.shuffle(set_order)
        identity_elements = list(range(inst["num_elements"]))
        identity_sets = list(range(inst["num_sets"]))
        transforms = [
            (element_perm, identity_sets),
            (identity_elements, set_order),
            (element_perm, set_order),
        ]
        for ep, so in transforms:
            moved, moved_answer = _relabel_instance(inst, ep, so)
            invariant_checks += 1
            if canonical_key(moved) != key:
                g8_failures.append({"seed": seed, "failure": "key changed"})
            ok, why = verify(moved, moved_answer)
            real_transform_checks += 1
            if not ok:
                g8_failures.append({"seed": seed, "failure": why})
        # Element relabelling leaves set IDs unchanged, so the literal original
        # answer must also remain valid for this non-identity transformation.
        elem_only, _ = _relabel_instance(inst, element_perm, identity_sets)
        ok, why = verify(elem_only, inst["answer"])
        real_transform_checks += 1
        if not ok:
            g8_failures.append({"seed": seed, "failure": f"original witness: {why}"})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transform_verifications": real_transform_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
        "method": "12-round color refinement of the set-element incidence graph",
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(
        isinstance(value, dict) and bool(value.get("pass")) for value in gate_values
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
