"""Planted contained-Steiner-triple-system problem generator.

The module is deterministic for (n, seed, params), uses only the standard
library, performs no file I/O, and does not print when imported.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter, defaultdict


DIFFICULTY = {
    "medium": {"n": 21, "layers": 5},
    "hard": {"n": 27, "layers": 6},
    "extreme": {"n": 33, "layers": 7},
}
SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper basis. Section 1 defines an integral Steiner triple system as exactly
n(n-1)/6 triples in which every unordered vertex-pair occurs exactly once;
Section 1.2 gives the equivalent triangle-decomposition viewpoint.  Theorem
1.5 concerns the very dense, sufficiently-large regime (minimum codegree about
0.8579n), while Section 1.2 says the fractional relaxation used by the proof is
constructed by linear optimisation / maximum flow.  I therefore use the
integral contained-system witness, stay far below the dense threshold, and do
not use fractional weights.  The general completion/search problem is
NP-complete (C. J. Colbourn, JCTA 35 (1983), 100-105); no polynomial-time or
closed-form method is known for this bounded-codegree planted distribution.

Planting. The answer is sampled first by randomly relabelling a Bose Steiner
triple system.  The allowed hypergraph is then the union of that system and
independent systems sampled by exactly the same procedure.  Thus every allowed
triple is contributed by an exchangeable source layer: there is no separate
decoy distribution and every pair has at most `layers` choices.

Attacks. The outlier attack ranks triples only by the codegrees of their three
pairs; the generator removes that signal by using whole Steiner layers.  The
deterministic greedy attack uses the most-constrained uncovered pair first.
The random-restart attack uses the same constraint rule with randomized
low-damage choices.  selftest() requires every attack to fail on at least eight
shipping-level seeds.  A calibration preset n=15,layers=4 was rejected after
the first oracle run because random restart solved 7/8 local seeds (and each
deterministic greedy rule solved 2/8); it is intentionally absent from the
shipping ladder.  canonical_key uses an isomorphism-invariant refinement of the
vertex/triple incidence structure; it never includes the seed, answer, input
order, or rendered text.
""".strip()


def _validate_order(n: int) -> int:
    """Validate the supported Bose-admissible subsequence n == 3 (mod 6)."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 9:
        raise ValueError("n must be an integer at least 9")
    if n % 6 != 3:
        raise ValueError("n must be congruent to 3 modulo 6")
    return n


def _bose_system(order: int) -> tuple[tuple[int, int, int], ...]:
    """A Bose STS(3q), q odd, on vertices encoded as 3*x+i."""
    if order % 3 or (order // 3) % 2 != 1:
        raise ValueError("Bose construction requires order=3q with q odd")
    q = order // 3
    inv2 = (q + 1) // 2
    blocks: list[tuple[int, int, int]] = []
    for x in range(q):
        blocks.append((3 * x, 3 * x + 1, 3 * x + 2))
    for x in range(q):
        for y in range(x + 1, q):
            z = ((x + y) * inv2) % q
            for i in range(3):
                blocks.append(tuple(sorted((3 * x + i,
                                            3 * y + i,
                                            3 * z + (i + 1) % 3))))
    blocks.sort()
    expected = order * (order - 1) // 6
    if len(blocks) != expected or len(set(blocks)) != expected:
        raise AssertionError("internal Bose construction failure")
    return tuple(blocks)


def _random_relabelling(base: tuple[tuple[int, int, int], ...],
                        order: int, rng: random.Random) -> list[tuple[int, int, int]]:
    perm = list(range(order))
    rng.shuffle(perm)
    return [tuple(sorted((perm[a], perm[b], perm[c]))) for a, b, c in base]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a Steiner system first, then hide it among exchangeable layers."""
    if "layers" not in params:
        layers = 6
    else:
        layers = params.pop("layers")
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(layers, bool) or not isinstance(layers, int) or layers < 3:
        raise ValueError("layers must be an integer at least 3")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    order = _validate_order(n)
    rng = random.Random(seed)
    base = _bose_system(order)

    # G requires the witness to be sampled before the rest of the instance.
    answer = _random_relabelling(base, order, rng)
    allowed = set(answer)
    for _ in range(layers - 1):
        allowed.update(_random_relabelling(base, order, rng))

    answer_order = list(answer)
    edge_order = list(allowed)
    rng.shuffle(answer_order)
    rng.shuffle(edge_order)
    return {
        "n": order,
        "requested_n": n,
        "layers": layers,
        "edges": [list(e) for e in edge_order],
        "answer": [list(e) for e in answer_order],
    }


def render(inst: dict) -> str:
    """Render a complete, standalone exact-witness problem."""
    n = inst["n"]
    needed = n * (n - 1) // 6
    lines = [
        "STEINER TRIPLE SYSTEM INSIDE AN ALLOWED 3-UNIFORM HYPERGRAPH",
        "",
        f"The vertices are the integers 0 through {n - 1}, inclusive.",
        "An unordered pair means two distinct vertices; (a,b) and (b,a) are",
        "the same pair.  A triple is an unordered set of three distinct vertices.",
        "",
        f"Choose exactly {needed} distinct triples from the allowed list below so",
        "that every unordered pair of distinct vertices occurs in exactly one",
        "chosen triple.  Order within a triple and order among triples do not",
        "matter.  Repeated vertices and repeated triples are forbidden.",
        "",
        f"ALLOWED_TRIPLES {len(inst['edges'])}",
    ]
    lines.extend("{} {} {}".format(*edge) for edge in inst["edges"])
    lines.extend([
        "END_ALLOWED_TRIPLES",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON array",
        f"containing exactly {needed} three-integer arrays.  JSON whitespace and",
        "the order conventions above are ignored.",
        "Example: <answer>[[0,1,2],[0,3,4]]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def parse_answer(text: str) -> object | None:
    """Parse JSON inside answer tags, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None

    def valid(value):
        if not isinstance(value, list):
            return False
        for triple in value:
            if not isinstance(triple, list) or len(triple) != 3:
                return False
            if any(isinstance(v, bool) or not isinstance(v, int) for v in triple):
                return False
        return True

    # Honour the advertised tagged format first, then recover the common model
    # deviation of returning only a fenced JSON array.
    bodies = list(reversed(_ANSWER_RE.findall(text)))
    bodies.extend(reversed(re.findall(r"```(?:json)?\s*(.*?)\s*```",
                                      text, re.I | re.S)))
    for body in bodies:
        try:
            value = json.loads(body.strip())
        except (TypeError, ValueError):
            continue
        if valid(value):
            return value

    # Last resort for prose wrapped directly around JSON without tags/fences.
    decoder = json.JSONDecoder()
    for start in (i for i, char in enumerate(text) if char == "["):
        try:
            value, _ = decoder.raw_decode(text[start:])
        except (TypeError, ValueError):
            continue
        if valid(value):
            return value
    return None


def _normalise_triple(raw) -> tuple[int, int, int] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in raw):
        return None
    return tuple(sorted(raw))


def _pairs(edge: tuple[int, int, int]):
    a, b, c = edge
    return ((a, b), (a, c), (b, c))


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any valid contained STS; the planted answer is never consulted."""
    n = inst["n"]
    needed = n * (n - 1) // 6
    if not isinstance(answer, list):
        return False, "answer must be a list of triples"
    if not answer:
        return False, "answer must be a non-empty list of triples"

    triples: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for i, raw in enumerate(answer):
        triple = _normalise_triple(raw)
        if triple is None:
            return False, f"triple {i} must contain exactly three integer vertices"
        for v in triple:
            if v < 0 or v >= n:
                return False, f"vertex {v} is outside the inclusive range 0..{n - 1}"
        if len(set(triple)) != 3:
            return False, f"triple {i} repeats a vertex"
        if triple in seen:
            return False, f"duplicate triple: {list(triple)}"
        seen.add(triple)
        triples.append(triple)

    if len(triples) != needed:
        return False, f"wrong number of triples: expected {needed}, got {len(triples)}"

    allowed = {tuple(sorted(e)) for e in inst["edges"]}
    for triple in triples:
        if triple not in allowed:
            return False, f"triple {list(triple)} is not in the allowed hypergraph"

    counts: Counter[tuple[int, int]] = Counter()
    for triple in triples:
        counts.update(_pairs(triple))
    for a in range(n):
        for b in range(a + 1, n):
            count = counts[(a, b)]
            if count != 1:
                return False, f"pair [{a}, {b}] occurs {count} times instead of exactly once"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """A structurally valid STS sampled independently of the planted answer.

    This prior already enforces the exact answer size, vertex range, distinctness,
    and every-pair-exactly-once rule.  It does not condition on containment in the
    allowed hypergraph, because doing so is precisely the search problem.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    n = inst["n"]
    candidate = _random_relabelling(_bose_system(n), n, rng)
    rng.shuffle(candidate)
    return [list(e) for e in candidate]


def search_space(inst: dict) -> int | None:
    """Naive unordered choice space of correctly-sized allowed-edge subsets."""
    n = inst["n"]
    needed = n * (n - 1) // 6
    edge_count = len({tuple(sorted(e)) for e in inst["edges"]})
    if edge_count < needed:
        return 0
    return math.comb(edge_count, needed)


class _EnumerationCap(Exception):
    pass


def enumerate_all(inst: dict) -> int | None:
    """Count exact covers by bounded DFS, returning None beyond a work cap."""
    n = inst["n"]
    edges = sorted({tuple(sorted(e)) for e in inst["edges"]})
    if n > 11 or len(edges) > 64:
        return None

    pair_index = {}
    k = 0
    for a in range(n):
        for b in range(a + 1, n):
            pair_index[(a, b)] = k
            k += 1
    masks = []
    incidence: list[list[int]] = [[] for _ in range(k)]
    for edge in edges:
        mask = 0
        for pair in _pairs(edge):
            mask |= 1 << pair_index[pair]
        idx = len(masks)
        masks.append(mask)
        for pair in _pairs(edge):
            incidence[pair_index[pair]].append(idx)

    full = (1 << k) - 1
    nodes = 0
    cap = 2_000_000

    def visit(covered: int) -> int:
        nonlocal nodes
        nodes += 1
        if nodes > cap:
            raise _EnumerationCap
        if covered == full:
            return 1
        best = None
        remaining = full ^ covered
        while remaining:
            bit = remaining & -remaining
            p = bit.bit_length() - 1
            viable = [idx for idx in incidence[p] if masks[idx] & covered == 0]
            if not viable:
                return 0
            if best is None or len(viable) < len(best):
                best = viable
                if len(best) == 1:
                    break
            remaining ^= bit
        return sum(visit(covered | masks[idx]) for idx in best or ())

    try:
        return visit(0)
    except _EnumerationCap:
        return None


def _rank_signatures(signatures) -> list[int]:
    ordered = sorted(set(signatures))
    rank = {signature: i for i, signature in enumerate(ordered)}
    return [rank[signature] for signature in signatures]


def canonical_key(inst: dict) -> str:
    """WL-style invariant of the unlabelled allowed 3-uniform hypergraph."""
    n = inst["n"]
    edges = sorted({tuple(sorted(e)) for e in inst["edges"]})
    pair_degree = [[0] * n for _ in range(n)]
    incident: list[list[int]] = [[] for _ in range(n)]
    for ei, edge in enumerate(edges):
        for v in edge:
            incident[v].append(ei)
        for a, b in _pairs(edge):
            pair_degree[a][b] += 1
            pair_degree[b][a] += 1

    vertex_signatures = [
        (len(incident[v]), tuple(sorted(pair_degree[v][u]
                                       for u in range(n) if u != v)))
        for v in range(n)
    ]
    edge_signatures = [
        tuple(sorted(pair_degree[a][b] for a, b in _pairs(edge)))
        for edge in edges
    ]
    vcolour = _rank_signatures(vertex_signatures)
    ecolour = _rank_signatures(edge_signatures)

    for _ in range(n + len(edges)):
        new_v = _rank_signatures([
            (vcolour[v], tuple(sorted(ecolour[ei] for ei in incident[v])))
            for v in range(n)
        ])
        new_e = _rank_signatures([
            (ecolour[ei], tuple(sorted(vcolour[v] for v in edge)))
            for ei, edge in enumerate(edges)
        ])
        if new_v == vcolour and new_e == ecolour:
            break
        vcolour, ecolour = new_v, new_e

    representation = {
        "n": n,
        "vertex_colour_counts": sorted(Counter(vcolour).items()),
        "pairs": sorted((min(vcolour[a], vcolour[b]),
                         max(vcolour[a], vcolour[b]), pair_degree[a][b])
                        for a in range(n) for b in range(a + 1, n)),
        "triples": sorted((tuple(sorted(vcolour[v] for v in edge)),
                           tuple(sorted(pair_degree[a][b]
                                        for a, b in _pairs(edge))))
                          for edge in edges),
    }
    payload = json.dumps(representation, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase both system order and exact-cover branching degree."""
    n = params.get("n")
    layers = params.get("layers", 6)
    if not isinstance(n, int) or not isinstance(layers, int) or n >= 51:
        return None
    return {"n": n + 6, "layers": layers + 2}


def _greedy_candidate(inst: dict, mode: str, rng: random.Random | None = None):
    """Cheap non-backtracking attack used only by selftest."""
    n = inst["n"]
    edges = sorted({tuple(sorted(e)) for e in inst["edges"]})
    edge_pairs = [_pairs(edge) for edge in edges]
    incidence = defaultdict(list)
    for ei, pairs in enumerate(edge_pairs):
        for pair in pairs:
            incidence[pair].append(ei)
    pair_degree = {pair: len(ids) for pair, ids in incidence.items()}
    all_pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    used: set[tuple[int, int]] = set()
    chosen: list[tuple[int, int, int]] = []

    while len(used) < len(all_pairs):
        best_pair = None
        best_viable = None
        for pair in all_pairs:
            if pair in used:
                continue
            viable = [ei for ei in incidence[pair]
                      if all(p not in used for p in edge_pairs[ei])]
            if not viable:
                return [list(e) for e in chosen]
            if best_viable is None or (len(viable), pair) < (len(best_viable), best_pair):
                best_pair, best_viable = pair, viable
        viable = best_viable or []
        if mode == "lexicographic":
            pick = min(viable, key=lambda ei: edges[ei])
        elif mode == "outlier":
            pick = min(viable, key=lambda ei: (
                sum(pair_degree[p] for p in edge_pairs[ei]), edges[ei]))
        elif mode == "random_restart":
            assert rng is not None
            scored = []
            for ei in viable:
                newly_used = used.union(edge_pairs[ei])
                damage = 0
                for p in edge_pairs[ei]:
                    for ej in incidence[p]:
                        if any(q in newly_used for q in edge_pairs[ej]):
                            damage += 1
                scored.append((damage, rng.random(), ei))
            scored.sort()
            window = scored[:min(3, len(scored))]
            pick = rng.choice(window)[2]
        else:
            raise ValueError("unknown greedy mode")
        chosen.append(edges[pick])
        used.update(edge_pairs[pick])
    return [list(e) for e in chosen]


def _relabeled_instance(inst: dict, perm: list[int], reverse: bool) -> dict:
    def mapped(triple):
        values = [perm[v] for v in triple]
        if reverse:
            values.reverse()
        return values

    edges = [mapped(e) for e in inst["edges"]]
    answer = [mapped(e) for e in inst["answer"]]
    if reverse:
        edges.reverse()
        answer.reverse()
    return {
        "n": inst["n"],
        "requested_n": inst.get("requested_n", inst["n"]),
        "layers": inst.get("layers"),
        "edges": edges,
        "answer": answer,
    }


def selftest() -> dict:
    """Run gates G1--G8 and return their measured, JSON-serialisable report."""
    report: dict[str, object] = {}

    # G1: every named preset, several independent seeds.
    g1_total = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "verified": g1_total, "failures": g1_failures,
    }

    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=9173, **ship)
    planted = [list(t) for t in inst["answer"]]

    # G2: five corruptions, deliberately routed to distinct checker failures.
    allowed = {tuple(sorted(e)) for e in inst["edges"]}
    nonedge = next(tuple(c) for c in itertools.combinations(range(inst["n"]), 3)
                   if tuple(c) not in allowed)
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": [list(nonedge)] + planted[1:],
        "duplicate": planted[:-1] + [list(planted[0])],
        "empty": [],
        "out_of_range": [[inst["n"], planted[0][1], planted[0][2]]] + planted[1:],
    }
    g2_results = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        g2_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [value["reason"] for value in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in g2_results.values())
                and len(set(reasons)) == len(reasons),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and fences surrounding the exact wire format.
    response = ("I checked every pair.\n```json\n<answer>\n" +
                json.dumps(planted) +
                "\n</answer>\n```\nThe tagged JSON is my final witness.")
    bare_fence = "Here is the result:\n```json\n" + json.dumps(planted) + "\n```"
    parsed = parse_answer(response)
    parsed_bare = parse_answer(bare_fence)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_bare == planted,
        "parsed_triples": len(parsed) if isinstance(parsed, list) else None,
        "model_style_variants_parsed": int(parsed == planted) + int(parsed_bare == planted),
    }

    # G4: candidates are complete Steiner systems, not arbitrary triple noise.
    guess_rng = random.Random(0x241107981)
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
        "prior": "independent randomly relabelled Bose STS; all pair constraints pre-satisfied",
        "naive_search_space": str(search_space(inst)),
    }

    # G5: use small orders where exact enumeration is capped and feasible.
    sparse_cases = []
    sparse_pass = True
    for seed in range(3):
        small = make_instance(n=9, layers=3, seed=seed)
        count = enumerate_all(small)
        space = search_space(small)
        fraction = None if count is None or not space else count / space
        passed = count is not None and fraction is not None and fraction < 1e-3
        sparse_pass = sparse_pass and passed
        sparse_cases.append({"seed": seed, "answers": count,
                             "search_space": space, "fraction": fraction,
                             "pass": passed})
    report["G5_sparse"] = {"pass": sparse_pass, "cases": sparse_cases}

    # G6: construction-aware cheap attacks, eight independent instances each.
    attacks = {"outlier_codegree": [], "mrv_lexicographic_greedy": [],
               "random_restart_mild_heuristic": []}
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **ship)
        outlier = _greedy_candidate(attack_inst, "outlier")
        lex = _greedy_candidate(attack_inst, "lexicographic")
        attacks["outlier_codegree"].append(verify(attack_inst, outlier)[0])
        attacks["mrv_lexicographic_greedy"].append(verify(attack_inst, lex)[0])
        restart_hit = False
        attack_rng = random.Random(50_000 + seed)
        for _ in range(24):
            candidate = _greedy_candidate(attack_inst, "random_restart", attack_rng)
            if verify(attack_inst, candidate)[0]:
                restart_hit = True
                break
        attacks["random_restart_mild_heuristic"].append(restart_hit)
    attack_summary = {
        name: {"seeds_tested": len(values), "solved": sum(values),
               "failed": len(values) - sum(values), "pass": not any(values)}
        for name, values in attacks.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["pass"] for item in attack_summary.values()),
        "attacks": attack_summary,
    }

    # G7: double the requested size and retain the same construction/check.
    doubled_params = dict(ship)
    # If n == 3 (mod 6), then 2n+3 is also 3 (mod 6) and exceeds 2n.
    doubled_params["n"] = 2 * doubled_params["n"] + 3
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > inst["n"],
        "base_order": inst["n"], "doubled_order": doubled["n"],
        "base_required_triples": inst["n"] * (inst["n"] - 1) // 6,
        "doubled_required_triples": doubled["n"] * (doubled["n"] - 1) // 6,
        "doubled_allowed_triples": len(doubled["edges"]),
        "verify_reason": doubled_reason,
    }

    # G8: vertex relabelling, input reorder, within-triple reorder, compositions.
    invariance_checks = 0
    witness_checks = 0
    g8_failures = []
    distinct_keys = []
    for seed in range(20):
        original = make_instance(seed=80_000 + seed, **ship)
        key = canonical_key(original)
        distinct_keys.append(key)

        reordered = dict(original)
        reordered["edges"] = list(reversed(original["edges"]))
        if canonical_key(reordered) != key:
            g8_failures.append({"seed": seed, "transform": "input reorder"})
        invariance_checks += 1
        if not verify(reordered, original["answer"])[0]:
            g8_failures.append({"seed": seed, "transform": "reorder witness"})
        witness_checks += 1

        relabel_rng = random.Random(90_000 + seed)
        perm = list(range(original["n"]))
        relabel_rng.shuffle(perm)
        relabeled = _relabeled_instance(original, perm, False)
        if canonical_key(relabeled) != key:
            g8_failures.append({"seed": seed, "transform": "vertex relabel"})
        invariance_checks += 1
        if not verify(relabeled, relabeled["answer"])[0]:
            g8_failures.append({"seed": seed, "transform": "relabel witness"})
        witness_checks += 1

        composed = _relabeled_instance(original, perm, True)
        if canonical_key(composed) != key:
            g8_failures.append({"seed": seed, "transform": "composed"})
        invariance_checks += 1
        if not verify(composed, composed["answer"])[0]:
            g8_failures.append({"seed": seed, "transform": "composed witness"})
        witness_checks += 1

    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "witness_preservation_checks": witness_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_total": 20,
        "failures": g8_failures,
        "method": "incidence/pair-codegree colour refinement invariant",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship)
    return report
