"""Verified generator for exact 3-uniform word representation.

The family is drawn from Definitions 1--3 and Proposition 11 of
arXiv:2509.03064.  It is deterministic for ``(n, seed, **params)`` and uses only
the Python standard library.
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
    # This deliberately easy complete graph makes the README example readable
    # and gives the hardening ladder an unambiguous first rung.
    "demo": {"n": 4, "k": 3, "mode": "demo"},
    "easy": {"n": 24, "k": 3, "mode": "random"},
    "medium": {"n": 64, "k": 3, "mode": "random"},
    "hard": {"n": 128, "k": 3, "mode": "random"},
}
SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Definitions 1--3 in Section 2 of Das and Hariharasubramanian,
arXiv:2509.03064v2, fix the exact alternation and k-uniformity requirements.
Proposition 11 records NP-completeness of deciding k-word-representability for
3 <= k <= ceil(|V|/2); the non-demo presets use k=3 in that regime.  The tempting
co-bipartite restriction was rejected: Section 4, Theorem 20 gives an explicit
algorithm constructing a 3-uniform representation for the paper's ordered
word-representable co-bipartite graphs.

For inverse generation, every attempted witness is sampled first as a uniformly
shuffled multiset containing three copies of every vertex.  Its graph is then
defined by exact pairwise alternation.  Final random instances are conditioned
only on connectedness, which avoids trivial component-wise solving while treating
all letters exchangeably.  Edge order is shuffled.

The outlier attack tries to reconstruct occurrence spacing from degree and
neighbour-degree statistics.  The greedy attack inserts one letter at a time in
positions that best match its already exposed adjacencies.  The random-restart
attack performs local swaps with simulated annealing against exact edge-symmetric
difference.  Plants and decoys are not separate populations here: all letters and
all three occurrences come from the same exchangeable shuffle.

Graph isomorphism is not known to have a general polynomial-time canonical form.
canonical_key therefore uses a deterministic 1-dimensional Weisfeiler--Leman
refinement trace and its final colour-quotient edge counts.  This is invariant
under vertex renaming, endpoint reversal, and edge-list reordering, and usually
individualises these random graphs, but it is an invariant rather than a complete
isomorphism test in the exceptional cases where colour refinement stalls.
""".strip()


def _positions(word, n):
    positions = [[] for _ in range(n)]
    for index, symbol in enumerate(word):
        positions[symbol].append(index)
    return positions


def _alternates_positions(left, right):
    """Whether two equal-sized sorted position lists strictly interleave."""
    i = 0
    j = 0
    previous = -1
    while i < len(left) or j < len(right):
        if j == len(right) or (i < len(left) and left[i] < right[j]):
            current = 0
            i += 1
        else:
            current = 1
            j += 1
        if current == previous:
            return False
        previous = current
    return True


def _edge_set_from_word(word, n):
    positions = _positions(word, n)
    edges = set()
    for left in range(n):
        for right in range(left + 1, n):
            if _alternates_positions(positions[left], positions[right]):
                edges.add((left, right))
    return edges


def _target_edges(inst):
    return {
        (left, right) if left < right else (right, left)
        for left, right in inst["edges"]
    }


def _is_connected(n, edges):
    if n <= 1:
        return True
    adjacency = [[] for _ in range(n)]
    for left, right in edges:
        adjacency[left].append(right)
        adjacency[right].append(left)
    reached = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbour in adjacency[vertex]:
            if neighbour not in reached:
                reached.add(neighbour)
                stack.append(neighbour)
    return len(reached) == n


def make_instance(n, seed=0, k=3, mode="random"):
    """Sample a k-uniform word first, then derive its alternation graph.

    ``n`` is the number of vertices.  At fixed ``k=3``, increasing ``n`` grows
    the balanced-word witness space super-exponentially and adds quadratically
    many exact pair constraints.  Random instances are conditioned on being
    connected so they do not split into independent component puzzles.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if not isinstance(k, int) or isinstance(k, bool) or k < 2:
        raise ValueError("k must be an integer at least 2")
    if mode not in ("demo", "random"):
        raise ValueError("mode must be 'demo' or 'random'")

    rng = random.Random(seed)
    if mode == "demo":
        permutation = list(range(n))
        rng.shuffle(permutation)
        # The witness exists before its (complete) alternation graph is derived.
        answer = permutation * k
        edges = _edge_set_from_word(answer, n)
    else:
        base = [vertex for vertex in range(n) for _ in range(k)]
        for _attempt in range(100_000):
            # G: sample the prospective answer before constructing any edges.
            answer = list(base)
            rng.shuffle(answer)
            edges = _edge_set_from_word(answer, n)
            if _is_connected(n, edges):
                break
        else:
            raise RuntimeError("could not sample a connected represented graph")

    edge_list = [list(edge) for edge in edges]
    rng.shuffle(edge_list)
    return {
        "family": "exact_k_uniform_word_representation",
        "n": n,
        "k": k,
        "edges": edge_list,
        "answer": list(answer),
    }


def render(inst):
    """Render a self-contained exact word-representation problem."""
    n = inst["n"]
    k = inst["k"]
    edges = "\n".join(f"{left} {right}" for left, right in inst["edges"])
    return f"""Exact {k}-uniform word representation

The undirected simple graph has vertices labelled 0 through {n - 1} inclusive.
Its {len(inst['edges'])} edges are listed below, one unordered pair per line.
Pairs not listed are non-edges; the order of edges and of endpoints is irrelevant.

{edges}

Find a word of exactly {k * n} integer symbols in which every vertex label from
0 through {n - 1} occurs exactly {k} times.  Repetitions are required, and the
order of symbols matters.

For two distinct labels x and y, form their induced subword by deleting every
symbol other than x and y.  The labels alternate exactly when every two
consecutive symbols of this length-{2 * k} subword are different (so it is
x,y,x,y,... or y,x,y,x,...).  Your word must make x and y alternate if and only
if {{x,y}} is a listed edge, for every unordered pair of distinct vertices.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {k * n} base-10 integer labels.  Do not use brackets.  Output nothing
else inside the tags.
Example syntax: <answer>0, 1, 0, 1</answer>
"""


_ANSWER_RE = re.compile(r"<answer\s*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL)


def parse_answer(text):
    """Extract the first tagged comma/whitespace-separated integer word."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match is None:
        return None
    body = match.group(1).strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines.pop()
            body = "\n".join(lines).strip()
    if len(body) >= 2 and body[0] in "[(" and body[-1] in ")]":
        body = body[1:-1].strip()
    if not body or re.fullmatch(r"[+-]?\d+(?:[\s,]+[+-]?\d+)*", body) is None:
        return None
    try:
        return [int(piece) for piece in re.split(r"[\s,]+", body) if piece]
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Check any valid k-uniform representing word; never consult the plant."""
    n = inst["n"]
    k = inst["k"]
    expected_length = n * k
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a sequence of integer labels"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != expected_length:
        return False, f"wrong length: expected {expected_length}, got {len(answer)}"
    for index, symbol in enumerate(answer):
        if not isinstance(symbol, int) or isinstance(symbol, bool):
            return False, f"non-integer symbol at position {index}"
        if not 0 <= symbol < n:
            return False, f"symbol out of range at position {index}: {symbol}"
    counts = Counter(answer)
    wrong = [(vertex, counts[vertex]) for vertex in range(n) if counts[vertex] != k]
    if wrong:
        vertex, count = wrong[0]
        return False, f"wrong multiplicity: label {vertex} occurs {count} times, expected {k}"

    positions = _positions(answer, n)
    target = _target_edges(inst)
    for left in range(n):
        for right in range(left + 1, n):
            actual = _alternates_positions(positions[left], positions[right])
            expected = (left, right) in target
            if actual != expected:
                expected_text = "edge/alternation" if expected else "non-edge/non-alternation"
                actual_text = "alternate" if actual else "do not alternate"
                return False, (
                    f"pair mismatch at ({left},{right}): expected {expected_text}, "
                    f"but the symbols {actual_text}"
                )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the balanced multiset space a solver would search."""
    candidate = [
        vertex
        for vertex in range(inst["n"])
        for _ in range(inst["k"])
    ]
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    """Number of balanced labelled words before alternation constraints."""
    n = inst["n"]
    k = inst["k"]
    return math.factorial(n * k) // (math.factorial(k) ** n)


def enumerate_all(inst):
    """Count exact witnesses by multiset permutation, with a hard work cap."""
    space = search_space(inst)
    if space > 500_000:
        return None
    n = inst["n"]
    k = inst["k"]
    target = _target_edges(inst)
    counts = [k] * n
    word = [0] * (n * k)
    solutions = 0

    def visit(position):
        nonlocal solutions
        if position == len(word):
            if _edge_set_from_word(word, n) == target:
                solutions += 1
            return
        for symbol in range(n):
            if counts[symbol]:
                counts[symbol] -= 1
                word[position] = symbol
                visit(position + 1)
                counts[symbol] += 1

    visit(0)
    return solutions


def canonical_key(inst):
    """A vertex-renaming-invariant 1-WL trace and colour quotient fingerprint."""
    n = inst["n"]
    adjacency = [set() for _ in range(n)]
    for left, right in inst["edges"]:
        if left == right:
            continue
        adjacency[left].add(right)
        adjacency[right].add(left)

    def compress(signatures):
        ordered = sorted(set(signatures))
        indices = {signature: index for index, signature in enumerate(ordered)}
        return [indices[signature] for signature in signatures]

    colors = compress([len(adjacency[vertex]) for vertex in range(n)])
    trace = []
    for _round in range(n + 1):
        class_sizes = sorted(Counter(colors).values())
        trace.append(class_sizes)
        signatures = [
            (colors[vertex], tuple(sorted(colors[other] for other in adjacency[vertex])))
            for vertex in range(n)
        ]
        refined = compress(signatures)
        if len(set(refined)) == len(set(colors)):
            colors = refined
            break
        colors = refined

    class_count = max(colors, default=-1) + 1
    sizes = [0] * class_count
    for color in colors:
        sizes[color] += 1
    cells = Counter()
    for left in range(n):
        for right in adjacency[left]:
            if left < right:
                a, b = sorted((colors[left], colors[right]))
                cells[(a, b)] += 1
    invariant = {
        "n": n,
        "k": inst["k"],
        "trace": trace,
        "sizes": sizes,
        "cells": [[a, b, cells[(a, b)]] for a in range(class_count)
                  for b in range(a, class_count) if cells[(a, b)]],
    }
    payload = json.dumps(invariant, sort_keys=True, separators=(",", ":")).encode()
    return "wl1:" + hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Double the random connected instance size, up to a practical ceiling."""
    current = int(params.get("n", 0))
    if current <= 0 or current >= 512:
        return None
    harder = dict(params)
    harder["n"] = current * 2
    harder["mode"] = "random"
    return harder


# --- construction-aware attacks used by G6 ---------------------------------


def _mismatch_count(word, inst):
    n = inst["n"]
    target = _target_edges(inst)
    positions = _positions(word, n)
    mismatches = 0
    for left in range(n):
        for right in range(left + 1, n):
            actual = _alternates_positions(positions[left], positions[right])
            mismatches += actual != ((left, right) in target)
    return mismatches


def _outlier_attack(inst):
    """Infer occurrence spread from per-letter degree statistics."""
    n = inst["n"]
    k = inst["k"]
    target = _target_edges(inst)
    adjacency = [set() for _ in range(n)]
    for left, right in target:
        adjacency[left].add(right)
        adjacency[right].add(left)
    degree = [len(row) for row in adjacency]
    max_degree = max(degree) or 1
    best = None
    best_score = math.inf
    for phase in range(8):
        tokens = []
        for vertex in range(n):
            neighbour_stat = sum(degree[x] for x in adjacency[vertex]) / max(1, n * max_degree)
            center = (
                vertex * 0.6180339887498949
                + phase * 0.13750352375
                + neighbour_stat * 0.31
            ) % 1.0
            spread = 0.08 + 0.40 * degree[vertex] / max_degree
            for occurrence in range(k):
                offset = occurrence - (k - 1) / 2
                key = (center + offset * spread) % 1.0
                tokens.append((key, occurrence, vertex))
        candidate = [vertex for _, _, vertex in sorted(tokens)]
        score = _mismatch_count(candidate, inst)
        if score < best_score:
            best = candidate
            best_score = score
    return best


def _alternates_in_word(word, left, right):
    projected = [symbol for symbol in word if symbol == left or symbol == right]
    return all(projected[index] != projected[index - 1]
               for index in range(1, len(projected)))


def _greedy_attack(inst):
    """Insert each new letter at the locally best sampled positions."""
    n = inst["n"]
    k = inst["k"]
    target = _target_edges(inst)
    adjacency = [set() for _ in range(n)]
    for left, right in target:
        adjacency[left].add(right)
        adjacency[right].add(left)
    degree = [len(row) for row in adjacency]
    order = sorted(range(n), key=lambda v: (-degree[v], -sum(degree[u] for u in adjacency[v]), v))
    rng_seed = sum((left + 1) * 1_000_003 + (right + 1) * 97_409 for left, right in target)
    rng = random.Random(rng_seed)
    word = []
    processed = []
    for vertex in order:
        final_length = len(word) + k
        choices = set()
        choices.add(tuple(range(k)))
        choices.add(tuple(range(final_length - k, final_length)))
        even = tuple(sorted({round(i * (final_length - 1) / max(1, k - 1)) for i in range(k)}))
        if len(even) == k:
            choices.add(even)
        choice_target = min(64, math.comb(final_length, k))
        while len(choices) < choice_target:
            choices.add(tuple(sorted(rng.sample(range(final_length), k))))
        best_word = None
        best_score = math.inf
        for slots in choices:
            slot_set = set(slots)
            old = iter(word)
            candidate = [vertex if index in slot_set else next(old)
                         for index in range(final_length)]
            candidate_positions = _positions(candidate, n)
            score = 0
            for other in processed:
                pair = (other, vertex) if other < vertex else (vertex, other)
                score += (
                    _alternates_positions(
                        candidate_positions[vertex], candidate_positions[other]
                    )
                    != (pair in target)
                )
            if score < best_score:
                best_score = score
                best_word = candidate
        word = best_word
        processed.append(vertex)
    return word


def _random_restart_attack(inst, rng):
    """Balanced local-swap simulated annealing with several restarts."""
    n = inst["n"]
    target = _target_edges(inst)
    best_word = None
    best_score = math.inf
    steps = max(200, 18 * n)
    for _restart in range(3):
        word = random_candidate(inst, rng)
        positions = _positions(word, n)
        score = _mismatch_count(word, inst)
        if score < best_score:
            best_score = score
            best_word = list(word)
        for step in range(steps):
            left_index = rng.randrange(len(word))
            right_index = rng.randrange(len(word))
            if left_index == right_index or word[left_index] == word[right_index]:
                continue
            left_symbol = word[left_index]
            right_symbol = word[right_index]
            affected = {
                tuple(sorted((symbol, other)))
                for symbol in (left_symbol, right_symbol)
                for other in range(n)
                if symbol != other
            }
            old_local = sum(
                _alternates_positions(positions[a], positions[b]) != ((a, b) in target)
                for a, b in affected
            )
            word[left_index], word[right_index] = word[right_index], word[left_index]
            positions[left_symbol].remove(left_index)
            positions[left_symbol].append(right_index)
            positions[left_symbol].sort()
            positions[right_symbol].remove(right_index)
            positions[right_symbol].append(left_index)
            positions[right_symbol].sort()
            new_local = sum(
                _alternates_positions(positions[a], positions[b]) != ((a, b) in target)
                for a, b in affected
            )
            delta = new_local - old_local
            temperature = max(0.08, 1.5 * (1.0 - step / steps))
            accept = delta <= 0 or rng.random() < math.exp(-delta / temperature)
            if accept:
                score += delta
                if score < best_score:
                    best_score = score
                    best_word = list(word)
                    if score == 0:
                        return best_word
            else:
                word[left_index], word[right_index] = word[right_index], word[left_index]
                positions[left_symbol].remove(right_index)
                positions[left_symbol].append(left_index)
                positions[left_symbol].sort()
                positions[right_symbol].remove(left_index)
                positions[right_symbol].append(right_index)
                positions[right_symbol].sort()
    return best_word


def _relabel_instance(inst, permutation, reorder_seed=None, reverse_endpoints=False):
    edges = [[permutation[left], permutation[right]] for left, right in inst["edges"]]
    if reverse_endpoints:
        edges = [[right, left] for left, right in edges]
    if reorder_seed is not None:
        random.Random(reorder_seed).shuffle(edges)
    return {
        "family": inst["family"],
        "n": inst["n"],
        "k": inst["k"],
        "edges": edges,
        "answer": [permutation[symbol] for symbol in inst["answer"]],
    }


def selftest():
    """Run mandatory G1--G8 gates and return a machine-readable report."""
    report = {
        "family": "Exact 3-uniform word representation",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all presets, several seeds.
    failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checked += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checked": checked,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=123456, **shipping)
    planted = list(inst["answer"])

    # G2: force five independent validation paths, including a graph mismatch.
    duplicate = list(planted)
    first_different = next(index for index, value in enumerate(duplicate) if value != duplicate[0])
    duplicate[first_different] = duplicate[0]
    out_of_range = list(planted)
    out_of_range[-1] = inst["n"]
    swapped = None
    for left in range(len(planted)):
        for right in range(left + 1, min(len(planted), left + 50)):
            if planted[left] == planted[right]:
                continue
            trial = list(planted)
            trial[left], trial[right] = trial[right], trial[left]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    reasons = {}
    rejected = 0
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejected += not ok
        reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": swapped is not None and rejected == 5 and len(set(reasons.values())) == 5,
        "rejected": rejected,
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # G3: prose and a Markdown fence around the tagged exact answer.
    response = (
        "I checked all unordered pairs.\n```text\n<answer>"
        + ", ".join(map(str, planted))
        + "</answer>\n```\nThe tagged sequence is my final witness."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_length": len(parsed) if parsed is not None else None,
    }

    # G4: every sample already has exact length, range, and multiplicities.
    guess_rng = random.Random(20260902)
    total = 200_000
    hits = 0
    for _ in range(total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    rate = hits / total
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": total,
        "rate": rate,
        "sampler": "uniform over all length k*n words with exactly k copies of every label",
        "naive_balanced_search_space": search_space(inst),
    }

    # G5: K4 has exactly the rare all-pairs-alternating balanced words.
    tiny = make_instance(n=4, k=3, mode="demo", seed=314159)
    solutions = enumerate_all(tiny)
    space = search_space(tiny)
    fraction = solutions / space if solutions is not None else None
    report["G5_sparse"] = {
        "pass": solutions is not None and fraction < 0.001,
        "n": tiny["n"],
        "solutions": solutions,
        "search_space": space,
        "fraction": fraction,
    }

    # G6: all attacks inspect only public graph data.
    attack_rows = {
        "degree_spacing_outlier": [],
        "incremental_insertion_greedy": [],
        "local_swap_random_restarts": [],
    }
    for seed in range(800, 808):
        attacked = make_instance(seed=seed, **shipping)
        candidates = {
            "degree_spacing_outlier": _outlier_attack(attacked),
            "incremental_insertion_greedy": _greedy_attack(attacked),
            "local_swap_random_restarts": _random_restart_attack(
                attacked, random.Random(seed ^ 0x5A17)
            ),
        }
        for name, candidate in candidates.items():
            ok, reason = verify(attacked, candidate)
            attack_rows[name].append({
                "seed": seed,
                "solved": ok,
                "pair_mismatches": _mismatch_count(candidate, attacked),
                "reason": reason,
            })
    attacks = {
        name: {
            "successes": sum(row["solved"] for row in rows),
            "trials": len(rows),
            "minimum_pair_mismatches": min(row["pair_mismatches"] for row in rows),
            "maximum_pair_mismatches": max(row["pair_mismatches"] for row in rows),
            "rows": rows,
        }
        for name, rows in attack_rows.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 and item["trials"] >= 8
                    for item in attacks.values()),
        "attacks": attacks,
    }

    # G7: double vertices at the same k and connected random distribution.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["n"] == 2 * inst["n"]
            and search_space(doubled) > search_space(inst)
            and _is_connected(doubled["n"], _target_edges(doubled))
        ),
        "base_n": inst["n"],
        "base_edges": len(inst["edges"]),
        "doubled_n": doubled["n"],
        "doubled_edges": len(doubled["edges"]),
        "verify_reason": doubled_reason,
    }

    # G8: edge ordering, endpoint order, vertex labels, and their composition.
    invariance_checks = 0
    carried_witness_checks = 0
    g8_failures = []
    unrelated_keys = []
    key_params = {"n": 48, "k": 3, "mode": "random"}
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **key_params)
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        permutation = list(range(original["n"]))
        random.Random(seed + 7700).shuffle(permutation)
        identity = list(range(original["n"]))
        variants = [
            _relabel_instance(original, identity, reorder_seed=seed + 1),
            _relabel_instance(original, identity, reverse_endpoints=True),
            _relabel_instance(original, permutation),
            _relabel_instance(
                original, permutation, reorder_seed=seed + 2, reverse_endpoints=True
            ),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                g8_failures.append({"seed": seed, "kind": "key_changed"})
            ok, reason = verify(variant, variant["answer"])
            carried_witness_checks += 1
            if not ok:
                g8_failures.append({"seed": seed, "kind": "map_not_real", "reason": reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
        "invariant_under": [
            "edge-list reordering",
            "undirected endpoint reversal",
            "arbitrary vertex permutation",
            "their composition",
        ],
        "limitation": "1-WL is a strong cheap invariant, not a complete graph-isomorphism test",
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
