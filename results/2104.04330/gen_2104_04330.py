"""Verified generator for an equiangular-vector subset problem.

The construction follows the search pattern in Section 2 of arXiv:2104.04330:
make a compatibility graph on equal-norm integer vectors, then find a clique.
Here the vectors are encoded implicitly by the graph, which keeps the rendered
instance small and makes the equivalence with CLIQUE exact.

This module uses only the Python standard library, performs no file I/O, and is
deterministic for a fixed (n, seed, params) tuple.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 20, "margin_tenths": 50},
    "easy": {"n": 720, "margin_tenths": 50},
    "medium": {"n": 950, "margin_tenths": 50},
    "hard": {"n": 1340, "margin_tenths": 50},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Definition source: the Introduction of Greaves--Syatriadi--Yatsyna defines an
equiangular line system using equal absolute inner products of unit spanning
vectors.  Section 2 is decisive for the search formulation: it builds the
integer norm-10 set L_0, joins two vectors when their inner product is +/-2,
and explicitly obtains more lines by finding a clique in that compatibility
graph.  The fixed 18-dimensional matrices F_1,...,F_4 printed in Section 2 are
not used as instances: asking for one of those would be a finite lookup and
would fail H.

Hard/easy boundary: the paper is not a complexity paper and gives no average-
case hardness theorem.  The scalable construction below instead makes the
compatibility graph exactly an arbitrary input graph, so the worst-case search
problem is CLIQUE.  The generated instances use the planted-clique regime with
k growing logarithmically with n; fixed k would admit the elementary O(n^k)
enumeration warned about in the task.  Section 8 of the paper independently
notes that deciding whether candidate Seidel data are realizable can be very
challenging, but that is not used as a hardness proof here.

Planting defenses: planted vertices are a uniformly random k-subset; labels
carry no signal.  At every named preset the remaining vertices are randomly
partitioned into further k-cliques, and every edge between different blocks is
an independent fair bit.  Thus every vertex, including those in the stored
witness, has exactly the same distribution.  k stays below sqrt(n).  The
adversary panel tests per-vertex degree/triangle outliers, a deterministic
common-neighbor greedy rule, and randomized greedy restarts.  All graph
vertices also use the same implicit vector construction.

Canonicalization: vertex relabelling is graph isomorphism, for which no cheap
general canonical form is known.  canonical_key uses canonical 1-WL refinement.
When refinement individualizes every vertex (the normal case for these random
graphs), it serializes the graph in that canonical order and is exact.  If
colour classes remain, it uses a stronger invariant summary; that fallback can
over-collapse non-isomorphic graphs, but never splits relabellings of one graph.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _clique_size(n: int, margin_tenths: int) -> int:
    """A growing k just above the random-graph clique threshold."""
    logn = math.log2(n)
    margin = margin_tenths / 10.0
    k = math.ceil(2.0 * logn - 2.0 * math.log2(logn) + margin)
    return max(7, min(n - 2, k))


def _rows_to_masks(rows: list[str]) -> list[int]:
    masks = []
    for row in rows:
        mask = 0
        for j, bit in enumerate(row):
            if bit == "1":
                mask |= 1 << j
        masks.append(mask)
    return masks


def _graph_ok(rows: Any, n: int) -> bool:
    if not isinstance(rows, list) or len(rows) != n:
        return False
    if any(not isinstance(row, str) or len(row) != n for row in rows):
        return False
    for i, row in enumerate(rows):
        if any(bit not in "01" for bit in row) or row[i] != "0":
            return False
        for j in range(i):
            if row[j] != rows[j][i]:
                return False
    return True


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Plant a clique first, then sample a symmetric noisy clique cover.

    ``n`` is the number of graph vertices / implicit integer vectors.  The
    requested clique size grows with n.  ``margin_tenths`` moves k above the
    usual random-graph clique threshold without putting it above sqrt(n).
    """
    if type(n) is not int or n < 18:
        raise ValueError("n must be an integer at least 18")
    if n > 2000:
        raise ValueError("n above 2000 would make the inline instance excessive")
    margin_tenths = params.pop("margin_tenths", 25)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if type(margin_tenths) is not int or not (0 <= margin_tenths <= 60):
        raise ValueError("margin_tenths must be an integer in [0, 60]")

    k = _clique_size(n, margin_tenths)
    if k >= math.isqrt(n) and n >= 196:
        raise ValueError("parameters leave the intended sub-sqrt(n) planted-clique regime")

    rng = random.Random(seed)
    planted = sorted(rng.sample(range(n), k))
    in_plant = [False] * n
    for v in planted:
        in_plant[v] = True

    # Named presets have n divisible by k.  The stored answer is sampled first;
    # then every remaining vertex is put into another random size-k block.  All
    # vertices consequently have the same conditional distribution.  For an
    # arbitrary n with a short final block, the stored witness remains valid;
    # named/shipped settings avoid that asymmetry.
    remaining = [v for v in range(n) if not in_plant[v]]
    rng.shuffle(remaining)
    blocks = [planted] + [remaining[i : i + k] for i in range(0, len(remaining), k)]
    block_of = [-1] * n
    for block_id, block in enumerate(blocks):
        for v in block:
            block_of[v] = block_id

    matrix = [bytearray(b"0" * n) for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            edge = block_of[i] == block_of[j] or bool(rng.getrandbits(1))
            if edge:
                matrix[i][j] = 49  # ord("1")
                matrix[j][i] = 49
    rows = [row.decode("ascii") for row in matrix]

    inst = {
        "n": n,
        "k": k,
        "margin_tenths": margin_tenths,
        "rows": rows,
        "answer": planted,
    }
    return inst


def render(inst: dict) -> str:
    """Render a complete, self-contained problem statement."""
    n = inst["n"]
    k = inst["k"]
    rows = inst["rows"]
    pair_count = n * (n - 1) // 2
    edge_bits = "".join(rows[i][j] for i in range(n) for j in range(i + 1, n))
    hex_width = (pair_count + 3) // 4
    packed = format(int(edge_bits, 2), f"0{hex_width}x") if edge_bits else ""
    data = "\n".join(packed[i : i + 128] for i in range(0, len(packed), 128))
    return f"""EQUIANGULAR INTEGER-VECTOR SUBSET

There are {n} labelled vertices, numbered 0 through {n - 1}.  Their undirected
simple graph is encoded below by one hexadecimal integer.  Ignore whitespace
between its lines.  Expand it to exactly {4 * hex_width} binary bits, preserving
leading zeroes, then discard the first {4 * hex_width - pair_count} padding bit(s).
The remaining {pair_count} bits give edges in this exact order:
    (0,1),(0,2),...,(0,{n - 1}),(1,2),(1,3),...,(1,{n - 1}),...,
    ({n - 2},{n - 1}).
A bit is 1 exactly when that unordered pair is an edge.  There are no loops.

This graph also defines {n} integer vectors x_0,...,x_{n - 1} without listing
their many zero coordinates.  There is one coordinate p_(a,b) for every pair
0 <= a < b < {n}.  At p_(a,b), vector x_a has value 1, vector x_b has value 1
if a and b are adjacent (otherwise 0), and every other vector has value 0.
For each i, add private coordinates used only by x_i, each with value 1, until
the squared length of x_i is exactly {n - 1}.  This is always possible because
the pair coordinates contribute at most {n - 1} to that squared length.

Consequently, every x_i has squared length {n - 1}, and for distinct i,j:
    x_i dot x_j = 1  if i and j are adjacent,
    x_i dot x_j = 0  otherwise.
Thus a set of indices gives equiangular lines with common absolute normalized
inner product 1/{n - 1} exactly when every two of its vertices are adjacent.

Find exactly {k} DISTINCT indices whose vectors are pairwise equiangular; in
graph terms, find a clique of size {k}.  The order of the submitted indices
does not matter.  Repeated indices are forbidden.  Bounds are inclusive:
every index must lie from 0 through {n - 1}.

HEX-ENCODED UPPER TRIANGLE ({hex_width} hex digits)
{data}

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly {k} integer indices separated by commas.
Example of the required format: <answer>[3, 17, 42]</answer>
The example illustrates syntax only and is not an answer to this instance.
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged JSON integer array, or return None."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    for body in reversed(matches):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(body)
        except (ValueError, TypeError):
            continue
        if isinstance(value, list) and all(type(v) is int for v in value):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any size-k clique; never consult the planted answer."""
    n = inst.get("n")
    k = inst.get("k")
    rows = inst.get("rows")
    # Instances are trusted checker inputs.  Keep only constant-time/container
    # sanity checks here: rescanning the whole n^2-bit graph for every candidate
    # would make the mandated 200,000-guess experiment needlessly quadratic.
    if type(n) is not int or type(k) is not int or not isinstance(rows, list) or len(rows) != n:
        return False, "invalid instance graph"
    if not isinstance(answer, list):
        return False, "answer is not a JSON array"
    if not answer:
        return False, "answer array is empty"
    if len(answer) != k:
        return False, f"wrong number of indices: expected {k}, got {len(answer)}"
    if any(type(v) is not int for v in answer):
        return False, "every index must be an integer"
    if any(v < 0 or v >= n for v in answer):
        return False, f"index out of range 0..{n - 1}"
    if len(set(answer)) != k:
        return False, "indices must be distinct"
    for pos, u in enumerate(answer):
        for v in answer[pos + 1 :]:
            if rows[u][v] != "1":
                return False, f"vertices {u} and {v} are not adjacent"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the structure-aware space of k-subsets."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return sorted(rng.sample(range(inst["n"]), inst["k"]))


def search_space(inst: dict) -> int | None:
    """Number of distinct size-k subsets, with order and repeats removed."""
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    """Count all k-cliques exactly when at most 100,000 subsets are needed."""
    total = search_space(inst)
    if total is None or total > 100_000:
        return None
    rows = inst["rows"]
    count = 0
    for candidate in itertools.combinations(range(inst["n"]), inst["k"]):
        if all(rows[u][v] == "1" for u, v in itertools.combinations(candidate, 2)):
            count += 1
    return count


def _canonical_colors(rows: list[str]) -> list[int]:
    """Canonical 1-dimensional Weisfeiler--Leman colour refinement."""
    n = len(rows)
    degrees = [row.count("1") for row in rows]
    values = sorted(set(degrees))
    rank = {value: i for i, value in enumerate(values)}
    colors = [rank[d] for d in degrees]
    for _ in range(n):
        signatures = []
        for i in range(n):
            neighbour_colors = sorted(colors[j] for j, bit in enumerate(rows[i]) if bit == "1")
            signatures.append((colors[i], tuple(neighbour_colors)))
        unique = sorted(set(signatures))
        sig_rank = {sig: i for i, sig in enumerate(unique)}
        refined = [sig_rank[sig] for sig in signatures]
        if refined == colors:
            break
        colors = refined
    return colors


def canonical_key(inst: dict) -> str:
    """An isomorphism-invariant key, exact when 1-WL individualizes vertices."""
    n = inst["n"]
    k = inst["k"]
    rows = inst["rows"]
    colors = _canonical_colors(rows)
    if len(set(colors)) == n:
        order = sorted(range(n), key=lambda v: colors[v])
        bits = "".join(rows[order[a]][order[b]] for a in range(n) for b in range(a + 1, n))
        digest = hashlib.sha256(bits.encode("ascii")).hexdigest()
        return f"wl-exact:n={n}:k={k}:{digest}"

    # Strong, cheap invariant fallback for graphs with unresolved colour cells.
    masks = _rows_to_masks(rows)
    per_vertex = []
    for i in range(n):
        neighbours = [j for j in range(n) if rows[i][j] == "1"]
        triangles = sum((masks[i] & masks[j]).bit_count() for j in neighbours) // 2
        colour_neighbours: dict[int, int] = {}
        for j in neighbours:
            colour_neighbours[colors[j]] = colour_neighbours.get(colors[j], 0) + 1
        per_vertex.append((colors[i], len(neighbours), triangles, tuple(sorted(colour_neighbours.items()))))
    edge_colour_pairs: dict[tuple[int, int], int] = {}
    for i in range(n):
        for j in range(i + 1, n):
            if rows[i][j] == "1":
                pair = tuple(sorted((colors[i], colors[j])))
                edge_colour_pairs[pair] = edge_colour_pairs.get(pair, 0) + 1
    invariant = (n, k, tuple(sorted(per_vertex)), tuple(sorted(edge_colour_pairs.items())))
    digest = hashlib.sha256(repr(invariant).encode("utf-8")).hexdigest()
    return f"wl-invariant:n={n}:k={k}:{digest}"


def escalate(params: dict) -> dict | None:
    """Add decoys while allowing the logarithmic clique size to grow."""
    if "n" not in params:
        return None
    n = int(params["n"])
    if n >= 2000:
        return None
    margin = int(params.get("margin_tenths", 25))
    candidate = int(math.ceil(math.sqrt(2.0) * n))
    while candidate <= 2000:
        if candidate % _clique_size(candidate, margin) == 0:
            return {"n": candidate, "margin_tenths": margin}
        candidate += 1
    return None


def _triangle_scores(rows: list[str]) -> list[int]:
    masks = _rows_to_masks(rows)
    scores = []
    for i, row in enumerate(rows):
        score_twice = 0
        bits = masks[i]
        while bits:
            low = bits & -bits
            j = low.bit_length() - 1
            score_twice += (masks[i] & masks[j]).bit_count()
            bits ^= low
        scores.append(score_twice // 2)
    return scores


def _attack_outlier(inst: dict) -> list[int]:
    """Pick vertices with the largest degree-plus-triangle outlier score."""
    rows = inst["rows"]
    triangles = _triangle_scores(rows)
    scored = [(triangles[i], rows[i].count("1"), -i, i) for i in range(inst["n"])]
    scored.sort(reverse=True)
    return sorted(item[3] for item in scored[: inst["k"]])


def _greedy_from_start(inst: dict, start: int) -> list[int]:
    rows = inst["rows"]
    n = inst["n"]
    k = inst["k"]
    clique = [start]
    candidates = {v for v in range(n) if v != start and rows[start][v] == "1"}
    while candidates and len(clique) < k:
        # Most neighbours remaining, then global degree, then lowest label.
        v = max(candidates, key=lambda x: (sum(rows[x][y] == "1" for y in candidates), rows[x].count("1"), -x))
        clique.append(v)
        candidates = {u for u in candidates if u != v and rows[v][u] == "1"}
    if len(clique) < k:
        clique.extend(v for v in range(n) if v not in clique)
    return sorted(clique[:k])


def _attack_greedy(inst: dict) -> list[int]:
    """Try deterministic common-neighbour greedy searches from obvious starts."""
    rows = inst["rows"]
    starts = sorted(range(inst["n"]), key=lambda v: (-rows[v].count("1"), v))[:16]
    best: list[int] | None = None
    for start in starts:
        candidate = _greedy_from_start(inst, start)
        ok, _ = verify(inst, candidate)
        if ok:
            return candidate
        if best is None:
            best = candidate
    return best if best is not None else list(range(inst["k"]))


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 96) -> list[int]:
    """Randomized greedy with a mild induced-degree heuristic."""
    rows = inst["rows"]
    n = inst["n"]
    k = inst["k"]
    best: list[int] = []
    for _ in range(restarts):
        clique: list[int] = []
        candidates = set(range(n))
        while candidates and len(clique) < k:
            pool = list(candidates)
            rng.shuffle(pool)
            pool.sort(key=lambda x: sum(rows[x][y] == "1" for y in candidates), reverse=True)
            v = rng.choice(pool[: min(6, len(pool))])
            clique.append(v)
            candidates = {u for u in candidates if u != v and rows[v][u] == "1"}
        if len(clique) > len(best):
            best = clique
        if len(clique) == k:
            return sorted(clique)
    padded = list(dict.fromkeys(best))
    padded.extend(v for v in range(n) if v not in padded)
    return sorted(padded[:k])


def _permute_instance(inst: dict, old_to_new: list[int]) -> dict:
    """Relabel vertices, carrying the witness through the same permutation."""
    n = inst["n"]
    if sorted(old_to_new) != list(range(n)):
        raise ValueError("not a permutation")
    matrix = [bytearray(b"0" * n) for _ in range(n)]
    rows = inst["rows"]
    for old_i in range(n):
        new_i = old_to_new[old_i]
        for old_j in range(n):
            if rows[old_i][old_j] == "1":
                matrix[new_i][old_to_new[old_j]] = 49
    return {
        "n": n,
        "k": inst["k"],
        "margin_tenths": inst.get("margin_tenths", 25),
        "rows": [row.decode("ascii") for row in matrix],
        "answer": sorted(old_to_new[v] for v in inst["answer"]),
    }


def selftest() -> dict:
    """Run gates G1--G8 and return their measured, JSON-serializable report."""
    report: dict[str, Any] = {
        "paper": "arXiv:2104.04330",
        "family": "implicit equal-norm integer vectors / planted k-clique",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every preset, several unrelated seeds.
    g1_trials = 0
    g1_failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 8675309):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            g1_trials += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_trials - len(g1_failures),
        "trials": g1_trials,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260430, **ship_params)
    planted = list(inst["answer"])

    # G2: five distinct corruptions must reach five distinct rejection paths.
    decoy = next(v for v in range(inst["n"]) if v not in planted)
    swap_bad = None
    for drop_pos in range(len(planted)):
        trial = planted[:drop_pos] + planted[drop_pos + 1 :] + [decoy]
        ok, _ = verify(inst, trial)
        if not ok and len(set(trial)) == inst["k"]:
            swap_bad = trial
            break
    if swap_bad is None:
        swap_bad = planted[:-1] + [decoy]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": swap_bad,
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [inst["n"]],
    }
    corruption_reasons = {}
    corruption_failures = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_reasons[name] = reason
        if ok:
            corruption_failures.append(name)
    report["G2_rejects_corruption"] = {
        "pass": not corruption_failures and len(set(corruption_reasons.values())) == len(corruptions),
        "rejected": len(corruptions) - len(corruption_failures),
        "trials": len(corruptions),
        "distinct_reasons": len(set(corruption_reasons.values())),
        "reasons": corruption_reasons,
    }

    # G3: realistic prose/fence wrapping and malformed text.
    payload = json.dumps(planted)
    response = f"I checked every pair.\n```text\n<answer>{payload}</answer>\n```\n"
    parsed = parse_answer(response)
    garbage_cases = ["", "no tags here", "<answer>[1, nope]</answer>", "<answer>{}</answer>"]
    garbage_rejected = sum(parse_answer(text) is None for text in garbage_cases)
    report["G3_round_trip"] = {
        "pass": parsed == planted and garbage_rejected == len(garbage_cases),
        "realistic_response_parsed": parsed == planted,
        "garbage_rejected": garbage_rejected,
        "garbage_trials": len(garbage_cases),
    }

    # G4: uniform over k-subsets, i.e. all stated shape/distinctness constraints.
    guess_rng = random.Random(0x210404330)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        ok, _ = verify(inst, candidate)
        guess_hits += int(ok)
    measured = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": measured < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "measured_probability": measured,
        "prior": "uniform over unordered size-k subsets (distinct and in range)",
        "search_space": search_space(inst),
    }

    # G5: a deliberately small instance fits the exact enumeration cap.
    enum_inst = make_instance(n=18, seed=314159, margin_tenths=25)
    enum_count = enumerate_all(enum_inst)
    enum_space = search_space(enum_inst)
    enum_fraction = None if enum_count is None else enum_count / enum_space
    report["G5_sparse"] = {
        "pass": enum_count is not None and enum_count >= 1 and enum_fraction < 1e-3,
        "n": enum_inst["n"],
        "k": enum_inst["k"],
        "valid_answers": enum_count,
        "search_space": enum_space,
        "solution_fraction": enum_fraction,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: three generator-aware cheap attacks over eight fresh instances.
    attack_seeds = list(range(8100, 8108))
    attack_results = {
        "degree_triangle_outlier": {"solved": 0, "trials": len(attack_seeds)},
        "common_neighbor_greedy": {"solved": 0, "trials": len(attack_seeds)},
        "randomized_greedy_96_restarts": {"solved": 0, "trials": len(attack_seeds)},
    }
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **ship_params)
        candidates = {
            "degree_triangle_outlier": _attack_outlier(attack_inst),
            "common_neighbor_greedy": _attack_greedy(attack_inst),
            "randomized_greedy_96_restarts": _attack_random_restart(
                attack_inst, random.Random(seed ^ 0xA5A5A5A5)
            ),
        }
        for name, candidate in candidates.items():
            ok, _ = verify(attack_inst, candidate)
            attack_results[name]["solved"] += int(ok)
    attacks_all_failed = all(row["solved"] == 0 for row in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": attacks_all_failed,
        "seeds": attack_seeds,
        "results": attack_results,
    }

    # G7: same non-size parameters, doubled n, and growing k.
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["k"] > inst["k"] and search_space(doubled) > search_space(inst),
        "base_n": inst["n"],
        "base_k": inst["k"],
        "doubled_n": doubled["n"],
        "doubled_k": doubled["k"],
        "doubled_planted_verify": doubled_ok,
        "verify_reason": doubled_reason,
        "base_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
    }

    # G8: four relabellings (including compositions) x 20 seeds.
    g8_seeds = list(range(9200, 9220))
    invariance_trials = 0
    real_transform_trials = 0
    keys = []
    g8_failures = []
    g8_params = dict(ship_params)
    for seed in g8_seeds:
        base = make_instance(seed=seed, **g8_params)
        base_key = canonical_key(base)
        keys.append(base_key)
        n8 = base["n"]
        prng = random.Random(seed ^ 0xC0DEC0DE)
        random_perm = list(range(n8))
        prng.shuffle(random_perm)
        reverse = list(reversed(range(n8)))
        cyclic = [(v + 7) % n8 for v in range(n8)]
        composed = [reverse[random_perm[v]] for v in range(n8)]
        for label, permutation in (
            ("random", random_perm),
            ("reverse", reverse),
            ("cyclic", cyclic),
            ("random_then_reverse", composed),
        ):
            transformed = _permute_instance(base, permutation)
            transformed_key = canonical_key(transformed)
            invariance_trials += 1
            ok, reason = verify(transformed, transformed["answer"])
            real_transform_trials += 1
            if transformed_key != base_key or not ok:
                g8_failures.append({"seed": seed, "transform": label, "verify": reason})
    distinct_keys = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == len(g8_seeds),
        "invariance_passed": invariance_trials - len(g8_failures),
        "invariance_trials": invariance_trials,
        "real_transform_passed": real_transform_trials - len(g8_failures),
        "real_transform_trials": real_transform_trials,
        "distinct_unrelated_keys": distinct_keys,
        "distinctness_trials": len(g8_seeds),
        "transformations": ["random permutation", "reversal", "cyclic shift", "random composed with reversal"],
        "failures": g8_failures,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
