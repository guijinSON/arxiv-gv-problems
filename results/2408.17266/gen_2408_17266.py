"""Verified problem generator for arXiv:2408.17266.

The paper studies nonnegative solutions of one linear Diophantine equation

    a_1 x_1 + ... + a_m x_m = b.

This module uses a hard special case.  Base-B digits encode a planted exact
cover by 3-sets.  A high digit forces exactly q coefficients to be used and
the lower digits force every one of 3q ground elements to be covered once.
Thus every nonnegative solution is automatically a binary exact cover.
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
    # The first rung is deliberately readable enough for README's worked example.
    "example": {"n": 4, "layers": 2},
    "hard": {"n": 54, "layers": 7},
}

SHIPPING_DIFFICULTY = "hard"


NOTES = """\
Definition: Section 2, equation (2.1), fixes the witness as nonnegative
integers x_i satisfying one exact linear equation.  The generated coefficients
encode Exact Cover by 3-Sets in base B=q+1; a leading digit and the absence of
base-B carries prove that all solutions have exactly q entries equal to one.

Easy regimes avoided: Theorem 2.1 and Proposition 2.2 make sufficiently large
right-hand sides automatically solvable; Proposition 2.5 gives a two-variable
solution when a coprime pair is small relative to b; Proposition 2.22 reduces
the special range b<2*min(a_i) to direct subset-sum membership.  Here b is only
about q times a coefficient, far below pairwise products and outside the
b<2*min(a_i) regime.  The recurrence in Theorem 2.21 still requires the
combinatorial subset-sum set T and does not yield a polynomial search method.

Planting defense: the instance is the shuffled union of independent uniformly
random exact-cover layers.  Every displayed 3-set, including the stored plant,
has the same marginal distribution; every ground element has exactly `layers`
incidences.  This removes degree, ordering, and coefficient-width signatures.
The self-test checks coefficient-magnitude/outlier selection, deterministic
most-constrained greedy search, left-to-right greedy packing, randomized greedy
restarts, and a 100,000-node Algorithm-X-style backtracker.  The canonical key
is a relabelling-invariant refinement hash of the incidence hypergraph, not a
hash of the seed or rendered statement.
"""


def _validate_parameters(n: int, layers: int) -> tuple[int, int]:
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if isinstance(layers, bool) or not isinstance(layers, int):
        raise TypeError("layers must be an integer")
    if n < 2:
        raise ValueError("n must be at least 2")
    if layers < 2:
        raise ValueError("layers must be at least 2")
    return n, layers


def _partition(universe_size: int, rng: random.Random) -> list[tuple[int, int, int]]:
    vertices = list(range(universe_size))
    rng.shuffle(vertices)
    return [tuple(sorted(vertices[i : i + 3])) for i in range(0, universe_size, 3)]


def _equation_data(
    q: int, supports: list[tuple[int, int, int]]
) -> tuple[int, int, list[int], int]:
    """Return base, common divisor, primitive coefficients, primitive target."""

    universe_size = 3 * q
    base = q + 1
    high = base**universe_size
    raw_coefficients = [
        high + base**u + base**v + base**w for u, v, w in supports
    ]
    raw_target = q * high + sum(base**u for u in range(universe_size))
    divisor = 0
    for value in raw_coefficients:
        divisor = math.gcd(divisor, value)
    # Every planted layer sums to raw_target, so the coefficient gcd divides it.
    if divisor <= 0 or raw_target % divisor:
        raise AssertionError("invalid coefficient normalization")
    coefficients = [value // divisor for value in raw_coefficients]
    target = raw_target // divisor
    return base, divisor, coefficients, target


def _assemble_instance(
    q: int,
    layers: int,
    supports: list[tuple[int, int, int]],
    answer: list[int],
    seed: int | None,
) -> dict:
    base, divisor, coefficients, target = _equation_data(q, supports)
    return {
        "paper": "arXiv:2408.17266",
        "family": "base-encoded exact cover linear Diophantine equation",
        "n": q,
        "q": q,
        "layers": layers,
        "universe_size": 3 * q,
        "base": base,
        "divisor": divisor,
        "supports": [list(edge) for edge in supports],
        "coefficients": coefficients,
        "target": target,
        "seed": seed,
        "answer": sorted(answer),
    }


def make_instance(n: int, seed: int = 0, layers: int = 6, **params) -> dict:
    """Sample a planted answer first, then surround it with symmetric covers.

    `n` is q, the number of selected variables; the universe has 3q elements.
    The final hypergraph is a shuffled union of `layers` independently sampled
    partitions.  Duplicate 3-sets are rejected so variable indices are distinct.
    Larger q increases the witness length and exact-cover search tree.
    """

    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    q, layers = _validate_parameters(n, layers)
    rng = random.Random(seed)
    universe_size = 3 * q

    # Each attempt begins by sampling layer zero: this is the answer sampled
    # before the remaining instance.  Conditioning on no duplicate triples is
    # symmetric in all i.i.d. layers, so plant and non-plant edges remain
    # identically distributed after the final shuffle.
    for _ in range(10_000):
        tagged: list[tuple[tuple[int, int, int], int]] = []
        seen: set[tuple[int, int, int]] = set()
        collision = False
        for layer in range(layers):
            for edge in _partition(universe_size, rng):
                if edge in seen:
                    collision = True
                    break
                seen.add(edge)
                tagged.append((edge, layer))
            if collision:
                break
        if not collision:
            break
    else:
        raise RuntimeError("could not sample distinct exact-cover layers")

    rng.shuffle(tagged)
    supports = [edge for edge, _layer in tagged]
    answer = [i + 1 for i, (_edge, layer) in enumerate(tagged) if layer == 0]
    return _assemble_instance(q, layers, supports, answer, seed)


def render(inst: dict) -> str:
    q = inst["q"]
    universe_size = inst["universe_size"]
    m = len(inst["coefficients"])
    base = inst["base"]
    divisor = inst["divisor"]
    lines = [
        "Find a nonnegative integer solution of one linear Diophantine equation.",
        "",
        "Definitions and exact encoding.",
        f"There are m={m} variables x_1,...,x_{m}, indexed from 1.",
        f"Let q={q}, B={base}, and U={universe_size}. Ground-element labels are the integers 0 through {universe_size - 1}.",
        "Each variable i has a listed support triple (u,v,w) of three distinct ground elements.",
        f"Its raw coefficient is A_i = B^U + B^u + B^v + B^w. Let d={divisor}.",
        "The equation coefficient is the exact integer a_i=A_i/d.",
        "The exact right-hand side is",
        "    b = (q*B^U + sum(B^j for j=0,...,U-1))/d.",
        f"For this instance, b={inst['target']}.",
        "You must find nonnegative integers satisfying sum(a_i*x_i for i=1,...,m)=b.",
        "",
        "The base encoding guarantees that every solution has exactly q entries equal to 1 and all other entries 0.",
        "Therefore output exactly q distinct variable indices; omitted indices mean x_i=0 and listed indices mean x_i=1.",
        "Order does not matter. Repeats are forbidden. Equivalently, the q listed support triples must cover every ground element exactly once.",
        "",
        "Support triples, one per line in the parseable format `index: u v w`:",
    ]
    for i, edge in enumerate(inst["supports"], 1):
        lines.append(f"{i}: {edge[0]} {edge[1]} {edge[2]}")
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags, as exactly q comma-separated 1-indexed variable indices.",
            "Example format: <answer>3, 17, 42, 58</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse a single tagged comma/whitespace-separated integer list."""

    try:
        if not isinstance(text, str):
            return None
        matches = re.findall(
            r"<answer\b[^>]*>(.*?)</answer\s*>", text, flags=re.IGNORECASE | re.DOTALL
        )
        if len(matches) != 1:
            return None
        body = matches[0].strip()
        body = re.sub(r"^```(?:[A-Za-z0-9_-]+)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        tokens = [token for token in re.split(r"[\s,]+", body) if token]
        if not tokens or any(re.fullmatch(r"[+-]?\d+", token) is None for token in tokens):
            return None
        return [int(token) for token in tokens]
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid witness by exact integer substitution; never use the plant."""

    q = inst["q"]
    m = len(inst["coefficients"])
    if not isinstance(answer, list) or any(
        isinstance(value, bool) or not isinstance(value, int) for value in answer
    ):
        return False, "malformed: expected a list of integer variable indices"
    if not answer:
        return False, f"empty answer: expected {q} selected variable indices"
    if len(answer) != q:
        return False, f"wrong length: expected {q} indices, got {len(answer)}"
    for index in answer:
        if index < 1 or index > m:
            return False, f"out of range: variable index {index} is not in 1..{m}"
    if len(set(answer)) != len(answer):
        duplicate = next(index for index in answer if answer.count(index) > 1)
        return False, f"duplicate index: variable {duplicate} is listed more than once"
    value = sum(inst["coefficients"][index - 1] for index in answer)
    if value != inst["target"]:
        return False, "equation mismatch: the selected coefficients do not sum to b"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact q-subset space revealed by the statement."""

    return sorted(rng.sample(range(1, len(inst["coefficients"]) + 1), inst["q"]))


def search_space(inst: dict) -> int | None:
    """Count q-subsets, after all statement-implied structure is enforced."""

    return math.comb(len(inst["coefficients"]), inst["q"])


def enumerate_all(inst: dict) -> int | None:
    """Exactly count covers for small instances; cap larger searches."""

    q = inst["q"]
    m = len(inst["supports"])
    if math.comb(m, q) > 2_000_000:
        return None

    universe_size = inst["universe_size"]
    supports = [tuple(edge) for edge in inst["supports"]]
    by_vertex: list[list[int]] = [[] for _ in range(universe_size)]
    masks: list[int] = []
    for i, edge in enumerate(supports):
        mask = sum(1 << v for v in edge)
        masks.append(mask)
        for v in edge:
            by_vertex[v].append(i)
    full = (1 << universe_size) - 1
    count = 0

    def visit(covered: int, used: int) -> None:
        nonlocal count
        if covered == full:
            if used == q:
                count += 1
            return
        if used >= q:
            return
        uncovered = full ^ covered
        best_options: list[int] | None = None
        bits = uncovered
        while bits:
            low = bits & -bits
            vertex = low.bit_length() - 1
            options = [i for i in by_vertex[vertex] if masks[i] & covered == 0]
            if not options:
                return
            if best_options is None or len(options) < len(best_options):
                best_options = options
                if len(options) == 1:
                    break
            bits ^= low
        assert best_options is not None
        for i in best_options:
            visit(covered | masks[i], used + 1)

    visit(0, 0)
    return count


def _wl_invariant(inst: dict) -> dict:
    """A cheap, strong incidence-hypergraph invariant under both relabellings."""

    supports = [tuple(edge) for edge in inst["supports"]]
    universe_size = inst["universe_size"]
    m = len(supports)
    total_nodes = universe_size + m
    adjacency: list[list[int]] = [[] for _ in range(total_nodes)]
    pair_counts: Counter[tuple[int, int]] = Counter()
    for edge_index, edge in enumerate(supports):
        node = universe_size + edge_index
        for vertex in edge:
            adjacency[vertex].append(node)
            adjacency[node].append(vertex)
        for pair in itertools.combinations(edge, 2):
            pair_counts[tuple(sorted(pair))] += 1

    vertex_profiles: list[tuple[int, ...]] = []
    for vertex in range(universe_size):
        profile = sorted(
            count
            for (u, v), count in pair_counts.items()
            if u == vertex or v == vertex
        )
        vertex_profiles.append(tuple(profile))

    labels: list[str] = []
    for profile in vertex_profiles:
        raw = "V|" + ",".join(map(str, profile))
        labels.append(hashlib.sha256(raw.encode()).hexdigest())
    for edge in supports:
        internal = sorted(pair_counts[tuple(sorted(pair))] for pair in itertools.combinations(edge, 2))
        raw = "E|" + ",".join(map(str, internal))
        labels.append(hashlib.sha256(raw.encode()).hexdigest())

    rounds: list[str] = []
    for _ in range(8):
        next_labels = []
        for node in range(total_nodes):
            kind = "V" if node < universe_size else "E"
            neighborhood = "|".join(sorted(labels[other] for other in adjacency[node]))
            raw = f"{kind}|{labels[node]}|{neighborhood}"
            next_labels.append(hashlib.sha256(raw.encode()).hexdigest())
        labels = next_labels
        rounds.append(hashlib.sha256("|".join(sorted(labels)).encode()).hexdigest())

    return {
        "vertices": universe_size,
        "edges": m,
        "degree_histogram": sorted(Counter(len(row) for row in adjacency[:universe_size]).items()),
        "pair_codegrees": sorted(Counter(pair_counts.values()).items()),
        "refinement_rounds": rounds,
    }


def canonical_key(inst: dict) -> str:
    """Return an order/ground-label invariant key of the encoded set system."""

    payload = json.dumps(_wl_invariant(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase exact-cover width while keeping constant-degree crowding."""

    if "n" not in params:
        return None
    q = int(params["n"])
    layers = int(params.get("layers", 6))
    if q >= 96:
        return None
    return {"n": q + max(8, q // 2), "layers": min(7, layers + 1)}


def _replace_one_corruption(inst: dict) -> list[int]:
    answer = list(inst["answer"])
    chosen = set(answer)
    for position in range(len(answer)):
        for replacement in range(1, len(inst["supports"]) + 1):
            if replacement in chosen:
                continue
            candidate = answer[:]
            candidate[position] = replacement
            if not verify(inst, candidate)[0]:
                return candidate
    raise AssertionError("could not construct a rejected replacement")


def _attack_smallest_coefficients(inst: dict, _rng: random.Random) -> object:
    order = sorted(
        range(1, len(inst["coefficients"]) + 1),
        key=lambda i: (inst["coefficients"][i - 1], i),
    )
    return sorted(order[: inst["q"]])


def _attack_left_to_right(inst: dict, _rng: random.Random) -> object:
    chosen: list[int] = []
    covered: set[int] = set()
    for i, edge_list in enumerate(inst["supports"], 1):
        edge = set(edge_list)
        if edge.isdisjoint(covered):
            chosen.append(i)
            covered.update(edge)
            if len(chosen) == inst["q"]:
                break
    return sorted(chosen)


def _greedy_once(inst: dict, rng: random.Random | None) -> object:
    supports = [set(edge) for edge in inst["supports"]]
    universe = set(range(inst["universe_size"]))
    selected: list[int] = []
    covered: set[int] = set()
    while len(selected) < inst["q"]:
        compatible = [i for i, edge in enumerate(supports) if edge.isdisjoint(covered)]
        if not compatible:
            return sorted(i + 1 for i in selected)
        options_by_vertex = {
            vertex: [i for i in compatible if vertex in supports[i]]
            for vertex in universe - covered
        }
        vertex = min(options_by_vertex, key=lambda v: (len(options_by_vertex[v]), v))
        options = options_by_vertex[vertex]
        if not options:
            return sorted(i + 1 for i in selected)
        if rng is None:
            # Prefer the edge that leaves the largest minimum future domain.
            def score(edge_index: int) -> tuple[int, int]:
                newly = covered | supports[edge_index]
                minima = []
                for other in universe - newly:
                    minima.append(
                        sum(1 for j in compatible if j != edge_index and supports[j].isdisjoint(newly) and other in supports[j])
                    )
                return (min(minima, default=0), -edge_index)

            pick = max(options, key=score)
        else:
            pick = rng.choice(options)
        selected.append(pick)
        covered.update(supports[pick])
    return sorted(i + 1 for i in selected)


def _attack_greedy(inst: dict, _rng: random.Random) -> object:
    return _greedy_once(inst, None)


def _attack_random_restarts(inst: dict, rng: random.Random, restarts: int = 1_000) -> object:
    last: object = []
    for _ in range(restarts):
        last = _greedy_once(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_bounded_exact_cover(
    inst: dict, _rng: random.Random, node_limit: int = 100_000
) -> object:
    """Try standard minimum-column exact-cover search under a cheap node cap."""

    universe_size = inst["universe_size"]
    supports = [tuple(edge) for edge in inst["supports"]]
    masks = [sum(1 << vertex for vertex in edge) for edge in supports]
    by_vertex: list[list[int]] = [[] for _ in range(universe_size)]
    for edge_index, edge in enumerate(supports):
        for vertex in edge:
            by_vertex[vertex].append(edge_index)
    full = (1 << universe_size) - 1
    selected: list[int] = []
    nodes = 0

    def visit(covered: int) -> list[int] | bool | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            return None
        if covered == full:
            return list(selected)
        bits = full ^ covered
        best: list[int] | None = None
        while bits:
            low = bits & -bits
            vertex = low.bit_length() - 1
            bits ^= low
            options = [i for i in by_vertex[vertex] if masks[i] & covered == 0]
            if not options:
                return False
            if best is None or len(options) < len(best):
                best = options
        assert best is not None
        for edge_index in best:
            selected.append(edge_index)
            result = visit(covered | masks[edge_index])
            selected.pop()
            if isinstance(result, list):
                return result
            if result is None:
                return None
        return False

    result = visit(0)
    if not isinstance(result, list):
        return []
    return sorted(edge_index + 1 for edge_index in result)


def _transform_instance(
    inst: dict,
    vertex_permutation: list[int] | None = None,
    edge_order: list[int] | None = None,
) -> dict:
    """Relabel ground elements/reorder variables and carry the witness along."""

    universe_size = inst["universe_size"]
    if vertex_permutation is None:
        vertex_permutation = list(range(universe_size))
    if edge_order is None:
        edge_order = list(range(len(inst["supports"])))
    mapped = [
        tuple(sorted(vertex_permutation[v] for v in edge)) for edge in inst["supports"]
    ]
    supports = [mapped[old] for old in edge_order]
    old_to_new = {old: new for new, old in enumerate(edge_order)}
    answer = [old_to_new[index - 1] + 1 for index in inst["answer"]]
    return _assemble_instance(inst["q"], inst["layers"], supports, answer, None)


def _attack_panel(params: dict, seeds: list[int]) -> dict:
    attacks = {
        "outlier_smallest_coefficient": _attack_smallest_coefficients,
        "greedy_left_to_right_packing": _attack_left_to_right,
        "greedy_most_constrained": _attack_greedy,
        "random_restart_1000": _attack_random_restarts,
        "bounded_exact_cover_100000_nodes": _attack_bounded_exact_cover,
    }
    result: dict[str, dict] = {}
    for name, attack in attacks.items():
        solved_seeds = []
        for seed in seeds:
            inst = make_instance(seed=seed, **params)
            candidate = attack(inst, random.Random(900_000 + seed))
            if verify(inst, candidate)[0]:
                solved_seeds.append(seed)
        result[name] = {
            "solved": len(solved_seeds),
            "total": len(seeds),
            "solved_seeds": solved_seeds,
        }
    return result


def selftest() -> dict:
    """Run gates G1--G8 and return their measurements as a JSON-safe dict."""

    report: dict[str, object] = {}

    g1_rows: dict[str, dict] = {}
    g1_pass = True
    for preset, params in DIFFICULTY.items():
        results = []
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            results.append({"seed": seed, "ok": ok, "reason": reason})
            g1_pass &= ok
        g1_rows[preset] = {"verified": sum(row["ok"] for row in results), "total": len(results), "rows": results}
    report["G1_planted_verifies"] = {"pass": g1_pass, "presets": g1_rows}

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12_345, **shipping)
    planted = list(inst["answer"])
    corruptions: dict[str, object] = {
        "drop_one": planted[:-1],
        "replace_one": _replace_one_corruption(inst),
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": [len(inst["supports"]) + 1] + planted[1:],
    }
    rejection_rows = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejection_rows[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in rejection_rows.values()]
    g2_pass = all(row["rejected"] for row in rejection_rows.values()) and len(set(reasons)) == len(reasons)
    report["G2_rejects_corruption"] = {"pass": g2_pass, "cases": rejection_rows, "distinct_reasons": len(set(reasons))}

    response = (
        "I used the base digits to identify a cover.\n\n```text\n<answer>\n"
        + ", ".join(map(str, planted))
        + "\n</answer>\n```\nThose are 1-indexed variables."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_count": None if parsed is None else len(parsed),
        "surrounding_prose_and_fence": True,
    }

    guess_rng = random.Random(88_231)
    total = 200_000
    hits = 0
    for _ in range(total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    p_hat = hits / total
    report["G4_guess_resistance"] = {
        "pass": p_hat < 1e-6,
        "hits": hits,
        "total": total,
        "p_hat": p_hat,
        "prior": "uniform over q distinct indices from m; all stated 0/1 and cardinality structure enforced",
        "candidate_space": search_space(inst),
    }

    small = make_instance(seed=77, n=6, layers=4)
    valid = enumerate_all(small)
    space = search_space(small)
    ratio = None if valid is None or space is None else valid / space
    report["G5_sparse"] = {
        "pass": ratio is not None and ratio < 1e-3,
        "params": {"n": 6, "layers": 4, "seed": 77},
        "valid_answers": valid,
        "candidate_space": space,
        "ratio": ratio,
    }

    panel = _attack_panel(shipping, list(range(8)))
    report["G6_adversary_panel"] = {
        "pass": all(row["solved"] == 0 for row in panel.values()),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "attacks": panel,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * shipping["n"]
    doubled = make_instance(seed=54_321, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "planted_ok": doubled_ok,
        "verify_reason": doubled_reason,
        "shipping_space": search_space(inst),
        "doubled_space": search_space(doubled),
    }

    invariant_checks = 0
    carried_verify_checks = 0
    keys = []
    g8_pass = True
    for seed in range(20):
        base_inst = make_instance(seed=1000 + seed, **shipping)
        base_key = canonical_key(base_inst)
        keys.append(base_key)
        transform_rng = random.Random(7000 + seed)
        vertex_permutation = list(range(base_inst["universe_size"]))
        transform_rng.shuffle(vertex_permutation)
        edge_order = list(range(len(base_inst["supports"])))
        transform_rng.shuffle(edge_order)
        variants = [
            _transform_instance(base_inst, edge_order=edge_order),
            _transform_instance(base_inst, vertex_permutation=vertex_permutation),
            _transform_instance(base_inst, vertex_permutation, edge_order),
        ]
        for variant in variants:
            invariant_checks += 1
            g8_pass &= canonical_key(variant) == base_key
            carried_ok, _ = verify(variant, variant["answer"])
            carried_verify_checks += 1
            g8_pass &= carried_ok
    distinct = len(set(keys))
    g8_pass &= distinct == len(keys)
    report["G8_canonical_key"] = {
        "pass": g8_pass,
        "seeds": 20,
        "invariance_checks": invariant_checks,
        "invariant_transformations": ["variable reorder", "ground-set permutation", "composition"],
        "carried_witness_verified": carried_verify_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": len(keys),
        "key_basis": "incidence hypergraph pair-codegrees plus 8 rounds of relabelling-invariant refinement",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
