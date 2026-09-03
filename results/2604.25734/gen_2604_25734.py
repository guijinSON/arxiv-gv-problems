"""Verified radius-one Ulam k-center witnesses from arXiv:2604.25734.

The paper reduces triangle-free Vertex Cover to radius-one Ulam k-Center.  We
plant an exact 3-set cover, turn its conflict graph into a known vertex-cover
instance, 2-subdivide it, and expose a compact exact encoding of the resulting
permutations and center witness.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import time


NATIVE: dict = {
    "domain": "combinatorics",
    "core": "exact_cover",
    "objects": [
        "indexed 3-uniform set system",
        "compactly encoded radius-one Ulam k-center instance",
    ],
    "intuition": "exact-cover complement as a vertex cover",
    "reduction": (
        "Section 3.1 licenses triangle-free Vertex Cover to radius-one Ulam "
        "k-Center; before that paper construction, this generator uses the "
        "elementary Exact Cover to conflict-graph independent-set/complement "
        "vertex-cover surrogate"
    ),
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON array of exactly n distinct integer triple indices in strictly "
        "increasing order, with every index in [0, len(inst['triples'])); this "
        "is the set of all n-subsets of the public triples in their unique "
        "sorted wire encoding."
    ),
    "bounds": {
        "array_length": "inst['n']",
        "index_lower_inclusive": 0,
        "index_upper_exclusive": "len(inst['triples']) = inst['set_ratio'] * inst['n']",
        "distinct": True,
        "ordering": "strictly increasing",
    },
}

DIFFICULTY = {
    "example": {"n": 4, "set_ratio": 5},
    "standard": {"n": 80, "set_ratio": 6},
    "hard": {"n": 104, "set_ratio": 6},
    "extreme": {"n": 136, "set_ratio": 6},
}
SHIPPING_DIFFICULTY = "standard"

NOTES = r"""
Definition. Section 2 of Bai, Fomin, Golovach, More, and Wietheger,
"Clustering Permutations under the Ulam Metric: A Parameterized Complexity
Study" (arXiv:2604.25734), defines Ulam distance as permutation length minus
the length of a longest common subsequence. Section 1.1 defines continuous
Ulam k-Center: exactly k center permutations, not necessarily inputs, cover all
inputs within an inclusive radius. Section 3.1 supplies the construction used
here. It gives two consecutive symbols to every graph vertex; an edge input
reverses its endpoint pairs, and a vertex-center reverses one pair. A vertex
cover therefore supplies radius-one centers. The reverse proof uses a
triangle-free graph.

Hard and easy regimes. Theorem 1 proves Ulam k-Center NP-hard for every fixed
d>=1. We use d=1 and let k grow. Theorem 2 gives an FPT algorithm for combined
parameter k+d, so keeping k small would make a misleading generator. Section
3.1 also records the exact 2-subdivision used to remove triangles: replace uv
by u-a-b-v, increasing the minimum vertex-cover size by one per original edge.
Our base graph is the conflict graph of an Exact Cover by 3-Sets instance; an
independent set of n mutually disjoint triples is an exact cover, and its
complement is the needed base-graph vertex cover.

Inverse generation. A random partition of 3n ground elements into n planted
triples is sampled first. Decoy triples are then sampled uniformly from the
same set of all 3-subsets; an individual planted triple and an individual decoy
therefore have identical marginals. All triples are shuffled before their
public indices and the planted witness are formed. With 6n total triples, the
exact-cover constraints are crowded without giving plant triples a degree,
position, or value-range marker. render() states a lossless recipe rather than
printing the enormous pair-scheme permutations. verify() checks any exact
cover and the implied center counts without consulting the plant.

Attacks. The panel includes a per-set conflict-degree outlier rule,
deterministic Algorithm-X greedy, 256 randomized Algorithm-X restarts, capped
exact Algorithm X (the standard exact-cover attack), a smallest normalized
conflict-eigenvector method (mandatory for the planted independent set), and a
maximal-matching vertex-cover relaxation. Shipping requires zero successes on
eight seeds. random_candidate chooses a uniform sorted n-subset of the public
triples; distinctness and size are free, while exact coverage remains the hard
condition.

Canonicalization. Ground-element names and triple order are presentation only.
Exact hypergraph isomorphism canonicalization is not known to be polynomial,
so canonical_key() applies deterministic color refinement to the bipartite
incidence graph and records color histograms and colored incidence signatures.
It is invariant under all tested element/triple relabelings and compositions,
but can theoretically collide on nonisomorphic hypergraphs; README.md records
this limitation.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample an exact cover first, then construct its Ulam-center instance.

    ``n`` is the number of triples in a witness and the ground set has size
    ``3*n``. ``set_ratio*n`` triples are presented. Increasing n grows the
    exact-cover depth, answer space, conflict graph, and encoded Ulam instance.
    """
    set_ratio = params.pop("set_ratio", 6)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if isinstance(set_ratio, bool) or not isinstance(set_ratio, int) or set_ratio < 2:
        raise ValueError("set_ratio must be an integer at least 2")
    total_sets = n * set_ratio
    if total_sets > math.comb(3 * n, 3):
        raise ValueError("too many distinct triples requested")

    rng = random.Random(seed)
    ground = list(range(3 * n))
    rng.shuffle(ground)
    planted_triples = [tuple(sorted(ground[3 * i:3 * i + 3])) for i in range(n)]
    # G: the mathematical witness exists before a single decoy is drawn.
    triples = set(planted_triples)
    while len(triples) < total_sets:
        triples.add(tuple(sorted(rng.sample(range(3 * n), 3))))
    public = list(triples)
    rng.shuffle(public)
    index = {triple: i for i, triple in enumerate(public)}
    answer = sorted(index[triple] for triple in planted_triples)

    # The exact-cover conflict graph is implicit and cheap to count.
    by_element = [[] for _ in ground]
    for i, triple in enumerate(public):
        for element in triple:
            by_element[element].append(i)
    conflicts = set()
    for incident in by_element:
        for a, b in itertools.combinations(incident, 2):
            conflicts.add((min(a, b), max(a, b)))
    conflict_edges = len(conflicts)
    base_cover = total_sets - n
    return {
        "family": "radius-one Ulam k-center via planted exact 3-cover",
        "n": n,
        "set_ratio": set_ratio,
        "ground_size": 3 * n,
        "triples": [list(t) for t in public],
        "base_vertices": total_sets,
        "base_conflict_edges": conflict_edges,
        "subdivision_vertices": total_sets + 2 * conflict_edges,
        "input_permutations": 3 * conflict_edges,
        "centers": base_cover + conflict_edges,
        "radius": 1,
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    triples = "\n".join(
        f"{i}: {a} {b} {c}" for i, (a, b, c) in enumerate(inst["triples"])
    )
    example = list(range(min(3, n)))
    return f"""Radius-one Ulam k-Center (compact exact encoding)

The Ulam distance between two permutations of the same alphabet is their
length minus the length of a longest common subsequence. Equivalently, it is
the fewest operations that remove one symbol and reinsert it elsewhere.

First define a simple conflict graph H. Its {inst['base_vertices']} vertices
are the indexed triples below, over ground elements 0,...,{inst['ground_size'] - 1}.
Two vertices are adjacent exactly when their triples share at least one ground
element. Triple order and the order of elements inside a triple have no
mathematical significance.

{triples}

This losslessly specifies the Ulam instance:

1. Give the {inst['base_conflict_edges']} edges of H their lexicographic order
   by endpoint indices. Replace edge i={{u,v}} by u--a_i--b_i--v. The resulting
   graph G is triangle-free, with {inst['subdivision_vertices']} vertices and
   {inst['input_permutations']} edges.
2. Give every vertex w of G private symbols (w,0),(w,1). The base permutation
   lists these pairs consecutively in vertex order, (w,0) before (w,1).
3. For each edge xy of G, one input permutation reverses exactly the two pairs
   for x and y. A vertex-center for w reverses exactly w's pair.

Provide a compact encoding of k={inst['centers']} distinct vertex-centers with
inclusive Ulam radius 1. Select exactly {n} displayed triples that are pairwise
disjoint and cover every ground element exactly once. Their complement is a
vertex cover X of H. The checker expands X by including its vertex-centers and,
for every oriented conflict edge u<v, including b_i if u is in X and a_i
otherwise. A valid selection therefore encodes exactly {inst['centers']} centers
and covers every edge-input of G at Ulam distance at most 1.

Output the selected triple indices as one JSON array of exactly {n} distinct
integers in strictly increasing order. Indices are 0-based and lie in
0,...,{inst['base_vertices'] - 1}. The set, not order, is mathematical; sorting
is the required unique wire encoding. Repeats are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format only: <answer>{json.dumps(example)}</answer>
The real answer must contain exactly {n} indices. Output nothing else inside
the tags."""


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any compact center witness; never inspect inst['answer']."""
    n, total = inst["n"], len(inst["triples"])
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong number of triples: expected {n}, got {len(answer)}"
    for position, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {position} is not an integer"
        if not 0 <= value < total:
            return False, f"triple index {value} is out of range 0..{total - 1}"
    if len(set(answer)) != n:
        return False, "a triple index is repeated"
    if any(answer[i] >= answer[i + 1] for i in range(n - 1)):
        return False, "triple indices are not in strictly increasing order"

    seen = 0
    for index in answer:
        triple = inst["triples"][index]
        if (not isinstance(triple, list) or len(triple) != 3 or
                any(isinstance(x, bool) or not isinstance(x, int) or
                    not 0 <= x < 3 * n for x in triple) or len(set(triple)) != 3):
            return False, f"instance triple {index} is malformed"
        mask = sum(1 << x for x in triple)
        overlap = seen & mask
        if overlap:
            element = (overlap & -overlap).bit_length() - 1
            return False, f"ground element {element} is covered more than once"
        seen |= mask
    full = (1 << (3 * n)) - 1
    if seen != full:
        missing = ((full ^ seen) & -(full ^ seen)).bit_length() - 1
        return False, f"ground element {missing} is not covered"

    selected = set(answer)
    base_cover = set(range(total)) - selected
    conflict_edges = []
    selected_sets = [set(inst["triples"][i]) for i in range(total)]
    for u in range(total):
        for v in range(u + 1, total):
            if selected_sets[u] & selected_sets[v]:
                conflict_edges.append((u, v))
    if len(conflict_edges) != inst["base_conflict_edges"]:
        return False, "instance conflict-edge count is inconsistent"

    # Materialize the claimed cover of the 2-subdivision and replay every path.
    expanded_cover = set(base_cover)
    for i, (u, _v) in enumerate(conflict_edges):
        a_i = total + 2 * i
        b_i = a_i + 1
        expanded_cover.add(b_i if u in base_cover else a_i)
    for i, (u, v) in enumerate(conflict_edges):
        a_i = total + 2 * i
        b_i = a_i + 1
        for left, right in ((u, a_i), (a_i, b_i), (b_i, v)):
            if left not in expanded_cover and right not in expanded_cover:
                return False, f"expanded subdivision edge {left}--{right} is uncovered"
    if len(expanded_cover) != inst["centers"]:
        return False, "expanded center count is inconsistent with k"
    if 3 * len(conflict_edges) != inst["input_permutations"]:
        return False, "expanded input-permutation count is inconsistent"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return sorted(rng.sample(range(len(inst["triples"])), inst["n"]))


def search_space(inst: dict) -> int | None:
    return math.comb(len(inst["triples"]), inst["n"])


def _structures(inst: dict):
    cached = inst.get("_structures")
    if cached is not None:
        return cached
    n, triples = inst["n"], inst["triples"]
    masks = [sum(1 << x for x in triple) for triple in triples]
    by_element = [0] * (3 * n)
    for i, triple in enumerate(triples):
        for x in triple:
            by_element[x] |= 1 << i
    conflicts = []
    for triple in triples:
        mask = 0
        for x in triple:
            mask |= by_element[x]
        conflicts.append(mask)
    return masks, by_element, conflicts


def enumerate_all(inst: dict) -> int | None:
    if len(inst["triples"]) > 26 or search_space(inst) > 2_000_000:
        return None
    count = 0
    full = (1 << (3 * inst["n"])) - 1
    masks, _, _ = _structures(inst)
    for chosen in itertools.combinations(range(len(masks)), inst["n"]):
        union = 0
        for i in chosen:
            if union & masks[i]:
                break
            union |= masks[i]
        else:
            count += union == full
    return count


def canonical_key(inst: dict) -> str:
    """Strong incidence-hypergraph invariant, not a seed or rendering hash."""
    triples = inst["triples"]
    element_count, set_count = inst["ground_size"], len(triples)
    neighbors = [[] for _ in range(element_count + set_count)]
    for j, triple in enumerate(triples):
        sv = element_count + j
        for x in triple:
            neighbors[x].append(sv)
            neighbors[sv].append(x)
    signatures = [(0, len(neighbors[v])) if v < element_count else (1, 3)
                  for v in range(len(neighbors))]
    palette = {s: i for i, s in enumerate(sorted(set(signatures)))}
    colors = [palette[s] for s in signatures]
    for _ in range(10):
        signatures = [(colors[v], tuple(sorted(colors[u] for u in neighbors[v])))
                      for v in range(len(neighbors))]
        palette = {s: i for i, s in enumerate(sorted(set(signatures)))}
        new = [palette[s] for s in signatures]
        if new == colors:
            break
        colors = new
    element_colors = sorted(colors[:element_count])
    set_colors = sorted(colors[element_count:])
    incidence = sorted((colors[x], colors[element_count + j])
                       for j, triple in enumerate(triples) for x in triple)
    intersections = sorted(len(set(a) & set(b))
                           for a, b in itertools.combinations(triples, 2))
    payload = [inst["n"], inst["set_ratio"], element_colors, set_colors,
               incidence, intersections]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params: dict) -> dict | None:
    if "n" not in params:
        return None
    out = dict(params)
    out["n"] = math.ceil(int(params["n"]) * 4 / 3)
    return out


def _answer_from_selected(inst: dict, selected: list[int]) -> list[int] | None:
    if len(selected) != inst["n"]:
        return None
    candidate = sorted(selected)
    return candidate if verify(inst, candidate)[0] else None


def _greedy_by_order(inst: dict, order: list[int]) -> object | None:
    masks, _, _ = _structures(inst)
    selected, used = [], 0
    for i in order:
        if not used & masks[i]:
            selected.append(i)
            used |= masks[i]
            if len(selected) == inst["n"]:
                return _answer_from_selected(inst, selected)
    return None


def _attack_outlier_degree(inst: dict) -> object | None:
    _, _, conflicts = _structures(inst)
    degrees = [(mask.bit_count() - 1, i) for i, mask in enumerate(conflicts)]
    for reverse in (False, True):
        candidate = _greedy_by_order(
            inst, [i for _, i in sorted(degrees, reverse=reverse)]
        )
        if candidate is not None:
            return candidate
    return None


def _algorithm_x_greedy(inst: dict, rng: random.Random | None = None) -> object | None:
    masks, by_element, conflicts = _structures(inst)
    uncovered = (1 << (3 * inst["n"])) - 1
    available = (1 << len(masks)) - 1
    selected = []
    while uncovered:
        elements = [x for x in range(3 * inst["n"]) if (uncovered >> x) & 1]
        counts = [(by_element[x] & available).bit_count() for x in elements]
        minimum = min(counts)
        if minimum == 0:
            return None
        choices = [x for x, count in zip(elements, counts) if count == minimum]
        x = rng.choice(choices) if rng is not None else min(choices)
        option_mask = by_element[x] & available
        options = []
        while option_mask:
            bit = option_mask & -option_mask
            options.append(bit.bit_length() - 1)
            option_mask ^= bit
        if rng is not None:
            chosen = rng.choice(options)
        else:
            chosen = min(options, key=lambda i: (conflicts[i] & available).bit_count())
        selected.append(chosen)
        uncovered &= ~masks[chosen]
        available &= ~conflicts[chosen]
    return _answer_from_selected(inst, selected)


def _attack_random_restarts(inst: dict, rng: random.Random,
                            restarts: int = 256) -> object | None:
    for _ in range(restarts):
        candidate = _algorithm_x_greedy(inst, rng)
        if candidate is not None:
            return candidate
    return None


def _attack_algorithm_x(inst: dict, node_limit: int = 100_000):
    masks, by_element, conflicts = _structures(inst)
    nodes = 0

    def search(uncovered: int, available: int, selected: list[int]):
        nonlocal nodes
        if nodes >= node_limit:
            return None
        nodes += 1
        if not uncovered:
            return selected
        best_options, best_count = 0, len(masks) + 1
        scan = uncovered
        while scan:
            bit = scan & -scan
            x = bit.bit_length() - 1
            options = by_element[x] & available
            count = options.bit_count()
            if count == 0:
                return None
            if count < best_count:
                best_options, best_count = options, count
            scan ^= bit
        options = []
        while best_options:
            bit = best_options & -best_options
            options.append(bit.bit_length() - 1)
            best_options ^= bit
        options.sort(key=lambda i: (conflicts[i] & available).bit_count())
        for chosen in options:
            found = search(uncovered & ~masks[chosen], available & ~conflicts[chosen],
                           selected + [chosen])
            if found is not None:
                return found
            if nodes >= node_limit:
                break
        return None

    found = search((1 << (3 * inst["n"])) - 1,
                   (1 << len(masks)) - 1, [])
    return (_answer_from_selected(inst, found) if found is not None else None), nodes


def _attack_spectral(inst: dict, seed: int = 0) -> object | None:
    _, _, conflicts = _structures(inst)
    size = len(conflicts)
    degrees = [mask.bit_count() - 1 for mask in conflicts]
    rng = random.Random(seed)
    vector = [rng.random() - 0.5 for _ in range(size)]
    for _ in range(100):
        nxt = []
        for v, mask in enumerate(conflicts):
            total = 0.0
            scan = mask & ~(1 << v)
            while scan:
                bit = scan & -scan
                u = bit.bit_length() - 1
                total += vector[u] / math.sqrt(max(1, degrees[v] * degrees[u]))
                scan ^= bit
            nxt.append(vector[v] - total)
        mean = sum(nxt) / size
        nxt = [x - mean for x in nxt]
        norm = math.sqrt(sum(x * x for x in nxt)) or 1.0
        vector = [x / norm for x in nxt]
    for reverse in (False, True):
        order = sorted(range(size), key=lambda i: vector[i], reverse=reverse)
        candidate = _greedy_by_order(inst, order)
        if candidate is not None:
            return candidate
    return None


def _attack_matching_relaxation(inst: dict) -> object | None:
    _, _, conflicts = _structures(inst)
    matched, cover = set(), set()
    for u in range(len(conflicts)):
        scan = conflicts[u] & ~((1 << (u + 1)) - 1)
        while scan:
            bit = scan & -scan
            v = bit.bit_length() - 1
            scan ^= bit
            if u not in matched and v not in matched:
                matched.update((u, v))
                cover.update((u, v))
                break
    full = (1 << len(conflicts)) - 1
    for v in sorted(cover, reverse=True):
        outside = full
        for u in cover:
            outside &= ~(1 << u)
        if not (conflicts[v] & outside):
            cover.remove(v)
    target = len(conflicts) - inst["n"]
    if len(cover) > target:
        return None
    for i in range(len(conflicts)):
        if len(cover) == target:
            break
        cover.add(i)
    selected = sorted(set(range(len(conflicts))) - cover)
    return _answer_from_selected(inst, selected)


def _transform_instance(inst: dict, rng: random.Random) -> dict:
    ground_perm = list(range(inst["ground_size"]))
    rng.shuffle(ground_perm)
    order = list(range(len(inst["triples"])))
    rng.shuffle(order)
    inverse_order = {old: new for new, old in enumerate(order)}
    triples = []
    for old in order:
        triple = [ground_perm[x] for x in inst["triples"][old]]
        rng.shuffle(triple)
        triples.append(triple)
    out = {**inst, "triples": triples,
           "answer": sorted(inverse_order[i] for i in inst["answer"])}
    out.pop("_structures", None)
    return out


def selftest() -> dict:
    report: dict[str, object] = {"paper": "2604.25734",
                                 "shipping_difficulty": SHIPPING_DIFFICULTY}
    verified = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {why}")
            verified += 1
    report["G1_planted_verifies"] = {"pass": True, "verified": verified,
                                      "attempted": verified}

    base = make_instance(seed=19, **DIFFICULTY[SHIPPING_DIFFICULTY])
    duplicate = base["answer"][:]
    duplicate[1] = duplicate[0]
    swapped = base["answer"][:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    out_of_range = base["answer"][:]
    out_of_range[-1] = len(base["triples"])
    corruptions = {"drop_one": base["answer"][:-1], "swap_two": swapped,
                   "duplicate": duplicate, "empty": [],
                   "out_of_range": out_of_range}
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(base, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = why
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError(f"G2 reasons not distinct: {reasons}")
    report["G2_rejects_corruption"] = {"pass": True, "rejected": len(reasons),
                                        "attempted": len(reasons), "reasons": reasons}

    response = ("The exact cover is below.\n```json\n<answer>\n"
                + json.dumps(base["answer"])
                + "\n</answer>\n```\nI checked every ground element.")
    parsed = parse_answer(response)
    if parsed != base["answer"]:
        raise AssertionError("G3 realistic response failed")
    report["G3_round_trip"] = {"pass": True, "indices_recovered": len(parsed),
                                "prose": True, "markdown_fence": True}

    guess_inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    guess_rng, samples, hits = random.Random(271828), 200_000, 0
    for _ in range(samples):
        hits += bool(verify(guess_inst, random_candidate(guess_inst, guess_rng))[0])
    probability = hits / samples
    if probability >= 1e-6:
        raise AssertionError(f"G4 guess rate {hits}/{samples} too high")
    report["G4_guess_resistance"] = {
        "pass": True, "hits": hits, "samples": samples,
        "measured_probability": probability,
        "prior": "uniform sorted n-subset of the public triples",
        "candidate_space": str(search_space(guess_inst))}

    sparse = []
    for seed in (5, 6, 7):
        small = make_instance(n=4, set_ratio=5, seed=seed)
        count, space = enumerate_all(small), search_space(small)
        if count is None or count / space >= 1e-3:
            raise AssertionError(f"G5 not sparse: {count}/{space}")
        sparse.append({"n": small["n"], "seed": seed, "solutions": count,
                       "space": space, "fraction": count / space})

    shipping_exact = enumerate_all(guess_inst)
    if shipping_exact is None:
        shipping_density = probability
        density_method = "sampled random_candidate"
    else:
        shipping_density = shipping_exact / search_space(guess_inst)
        density_method = "exact enumeration"
    baseline_start = time.perf_counter()
    baseline_candidate, baseline_nodes = _attack_algorithm_x(guess_inst, 100_000)
    baseline_seconds = time.perf_counter() - baseline_start
    baseline_solved = (baseline_candidate is not None and
                       verify(guess_inst, baseline_candidate)[0])
    g5_pass = (shipping_density < 1e-6 and not baseline_solved and
               baseline_nodes == 100_000)
    if not g5_pass:
        raise AssertionError(
            "G5 shipping measurement failed: "
            f"density={shipping_density}, solved={baseline_solved}, "
            f"nodes={baseline_nodes}"
        )
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_n": guess_inst["n"],
        "shipping_instance_seed": 314159,
        "density_method": density_method,
        "enumerate_all": shipping_exact,
        "density_hits": hits,
        "density_samples": samples,
        "density_rng_seed": 271828,
        "observed_fraction": shipping_density,
        "baseline_attack": "exact_algorithm_x_100000_nodes",
        "baseline_solved": baseline_solved,
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_nodes": baseline_nodes,
        "baseline_node_limit": 100_000,
        "additional_small_exact_counts": sparse,
    }

    names = ("outlier_conflict_degree", "greedy_algorithm_x",
             "random_restart_256", "spectral_conflict_eigenvector",
             "matching_vertex_cover_relaxation", "exact_algorithm_x_100000_nodes")
    successes = {name: 0 for name in names}
    exact_nodes = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        exact, nodes = _attack_algorithm_x(inst, 100_000)
        exact_nodes.append(nodes)
        candidates = {
            names[0]: _attack_outlier_degree(inst),
            names[1]: _algorithm_x_greedy(inst),
            names[2]: _attack_random_restarts(inst, random.Random(90_000 + seed), 256),
            names[3]: _attack_spectral(inst, 100_000 + seed),
            names[4]: _attack_matching_relaxation(inst), names[5]: exact}
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                successes[name] += 1
    if any(successes.values()):
        raise AssertionError(f"G6 attack succeeded: {successes}")
    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": {name: {"successes": successes[name], "attempts": 8}
                    for name in names},
        "domain_attack": names[5], "planted_subgraph_attack": names[3],
        "exact_nodes": exact_nodes}

    doubled = make_instance(n=160, set_ratio=6, seed=77)
    ok, why = verify(doubled, doubled["answer"])
    if not ok:
        raise AssertionError(f"G7 doubled failed: {why}")
    report["G7_scales"] = {"pass": True, "base_n": 80, "doubled_n": 160,
                            "base_space": str(search_space(base)),
                            "doubled_space": str(search_space(doubled)),
                            "doubled_planted_verifies": True}

    invariance = carried = 0
    keys = []
    for seed in range(20):
        small = make_instance(n=12, set_ratio=5, seed=10_000 + seed)
        transformed = _transform_instance(small, random.Random(20_000 + seed))
        if canonical_key(small) != canonical_key(transformed):
            raise AssertionError(f"G8 key changed at {seed}")
        invariance += 1
        ok, why = verify(transformed, transformed["answer"])
        if not ok:
            raise AssertionError(f"G8 carried witness failed: {why}")
        carried += 1
        keys.append(canonical_key(small))
    distinct = len(set(keys))
    if distinct != len(keys):
        raise AssertionError(f"G8 only {distinct}/{len(keys)} distinct")
    report["G8_canonical_key"] = {
        "pass": True, "invariance_transformations": invariance,
        "carried_witnesses_verified": carried, "unrelated_keys_distinct": distinct,
        "unrelated_keys_tested": len(keys),
        "symmetries": ["ground-set relabelling", "triple reordering",
                       "within-triple reordering", "all composed"],
        "limitation": "strong incidence-WL invariant, not complete hypergraph canon"}

    report["all_passed"] = all(value.get("pass") for key, value in report.items()
                                  if key.startswith("G") and isinstance(value, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
