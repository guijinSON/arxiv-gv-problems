"""Verified problem generator derived from arXiv:1610.03115.

The paragraph before Theorem 2.17 defines the necklace graph N_r from copies
of K_4-e, Remark 2.16 gives the twin obstruction used for a lower bound, and
Lemma 2.18 works directly with the four-vertex necklace blocks.  This module
composes several necklace components, randomly relabels their vertices, and
asks for a power dominating set containing exactly one vertex per hidden
block.

Generation is by composition, never by solving: one vertex is sampled in
each K_4-e block before the labels are scrambled.  Verification independently
checks the answer's shape and simulates the exact power-domination process.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family itself needs only the standard library.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "cubic graph given by adjacency lists",
        "power dominating vertex set",
        "K4-e necklace blocks",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact graph-neighborhood union",
        "exact power-domination forcing closure",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize the relabelled graph as disjoint necklaces of K4-e diamonds, "
        "so one representative can be chosen from every diamond instead of "
        "searching subsets."
    ),
    "hardness_basis": (
        "Track B: sorting closed-neighborhood signatures detects every true-twin "
        "pair in O((|V|+|E|) log Delta) time; at the 996-vertex shipping preset "
        "the reference implementation performs 15,936 counted signature operations "
        "and averaged about 0.001 seconds over eight seeds, whereas the compact "
        "necklace decomposition uses at most 261 exact adjacency decisions."
    ),
    "max_answer_tokens": 307,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list of exactly k distinct 0-based vertex identifiers, "
        "each in 0..|V|-1; candidates are uniformly sampled k-subsets."
    ),
    "bounds": {
        "atomic_elements": "instance k",
        "minimum_vertex": 0,
        "maximum_vertex": "instance vertex_count-1",
        "repetitions": False,
        "order_matters": False,
    },
}

STRUCTURAL_HINT = (
    "In every hidden K4-e block, the adjacent vertices with equal closed neighborhoods mark the diamond decomposition."
)
PLACEBO_HINT = (
    "In every displayed adjacency row, the three listed vertex labels deserve the same careful bookkeeping throughout."
)

DIFFICULTY = {
    "demo": {"n": 3, "component_max": 3},
    "easy": {"n": 24, "component_max": 8},
    "medium": {"n": 96, "component_max": 13},
    "hard": {"n": 249, "component_max": 17},
}

SHIPPING_DIFFICULTY = "hard"

# Populated after the three isolated harness runs.  These are diagnostics;
# only the answer/route caps are gated.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = """\
Section 1 gives the exact two-stage definition of power domination.  The
paragraph before Theorem 2.17 defines N_r as r copies of K4-e linked through
their degree-two vertices; Remark 2.16 supplies the twin obstruction; and
Lemma 2.18 names the same four-vertex blocks explicitly.  Theorem 3.13 confirms that disconnected cubic
graphs are handled componentwise and that necklaces attain the n/4 bound.

Step 0 rules out a Track-A claim.  On this generated distribution an efficient
algorithm sorts the four-element closed neighborhoods and reads off every
true-twin pair.  The module therefore declares Track B and measures that
algorithm rather than hiding it among failed attacks.  The paper's easy
regimes were also avoided as hardness claims: complements of necklaces have
power domination number two (Lemma 2.18), diameter at least three makes the
complement have a two-vertex dominating set (Theorem 2.5), and the extremal
foliated family T visibly exposes leaves (Theorem 2.12).

Generation chooses a uniformly random role in every diamond before an
arbitrary vertex relabelling, so planted vertices and non-planted vertices have
the same marginal role and label distributions.  All vertices have degree
three.  The degree outlier, marginal-coverage greedy, random-restart, and
periodic-label attacks are tested across eight shipping seeds.  The intended
route is the relational invariant: the two non-connector vertices in a diamond
have identical closed neighborhoods, while no connector does.
"""


def _partition_without_ones(total: int, maximum: int, rng: random.Random) -> list[int]:
    """Random composition into parts in [2, maximum], subsequently shuffled."""

    if total < 2:
        raise ValueError("n must be at least 2")
    maximum = max(2, min(maximum, total))
    parts: list[int] = []
    remaining = total
    while remaining:
        if remaining <= maximum and remaining != 1:
            parts.append(remaining)
            break
        upper = min(maximum, remaining - 2)
        choices = [x for x in range(2, upper + 1) if remaining - x != 1]
        if not choices:
            # This is reachable only at remaining=3 with maximum=2.
            if parts:
                parts[-1] += remaining
                remaining = 0
                break
            parts.append(remaining)
            break
        piece = rng.choice(choices)
        parts.append(piece)
        remaining -= piece
    rng.shuffle(parts)
    return parts


def _adjacency(inst: dict) -> list[set[int]]:
    count = inst["vertex_count"]
    adj = [set() for _ in range(count)]
    for edge in inst["edges"]:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("malformed edge")
        u, v = edge
        if not isinstance(u, int) or not isinstance(v, int):
            raise ValueError("non-integer edge endpoint")
        if u == v or not (0 <= u < count and 0 <= v < count):
            raise ValueError("invalid edge endpoint")
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _closed_signature(adj: list[set[int]], vertex: int) -> tuple[int, ...]:
    return tuple(sorted(adj[vertex] | {vertex}))


def _recover_diamonds(inst: dict) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Recover ((true twins), (connectors)) from the graph, without planted data."""

    adj = _adjacency(inst)
    by_closed: dict[tuple[int, ...], list[int]] = {}
    for vertex in range(len(adj)):
        by_closed.setdefault(_closed_signature(adj, vertex), []).append(vertex)

    blocks: list[tuple[tuple[int, int], tuple[int, int]]] = []
    used: set[int] = set()
    for signature, vertices in by_closed.items():
        if len(vertices) != 2 or len(signature) != 4:
            continue
        u, v = sorted(vertices)
        if v not in adj[u]:
            continue
        connectors = tuple(sorted(set(signature) - {u, v}))
        if len(connectors) != 2:
            continue
        a, b = connectors
        expected = {
            tuple(sorted((u, v))),
            tuple(sorted((u, a))),
            tuple(sorted((u, b))),
            tuple(sorted((v, a))),
            tuple(sorted((v, b))),
        }
        actual = {
            tuple(sorted((x, y)))
            for x, y in itertools.combinations(signature, 2)
            if y in adj[x]
        }
        if actual != expected:
            continue
        blocks.append(((u, v), (a, b)))
        used.update(signature)

    if len(blocks) * 4 != len(adj) or len(used) != len(adj):
        raise ValueError("graph is not completely decomposed into K4-e diamonds")
    blocks.sort(key=lambda block: min(block[0] + block[1]))
    return blocks


def make_instance(n: int, seed: int = 0, component_max: int = 17, **params) -> dict:
    """Construct a relabelled union of necklace graphs with a known witness."""

    if not isinstance(n, int) or n < 2:
        raise ValueError("n is the number of K4-e blocks and must be at least 2")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    parts = _partition_without_ones(n, int(component_max), rng)
    vertex_count = 4 * n
    canonical_edges: set[tuple[int, int]] = set()
    canonical_blocks: list[tuple[int, int, int, int]] = []

    cursor = 0
    for size in parts:
        component: list[tuple[int, int, int, int]] = []
        for block_index in range(cursor, cursor + size):
            z, w, left, right = (
                4 * block_index,
                4 * block_index + 1,
                4 * block_index + 2,
                4 * block_index + 3,
            )
            block = (z, w, left, right)
            component.append(block)
            canonical_blocks.append(block)
            for u, v in ((z, w), (z, left), (z, right), (w, left), (w, right)):
                canonical_edges.add((min(u, v), max(u, v)))
        for i, block in enumerate(component):
            right = block[3]
            next_left = component[(i + 1) % size][2]
            canonical_edges.add((min(right, next_left), max(right, next_left)))
        cursor += size

    # An arbitrary permutation erases block order and component order.  Sampling
    # the certificate role first makes planted and unplanted roles exchangeable.
    permutation = list(range(vertex_count))
    rng.shuffle(permutation)
    planted_canonical = [rng.choice(block) for block in canonical_blocks]
    answer = sorted(permutation[v] for v in planted_canonical)
    edges = sorted(
        (min(permutation[u], permutation[v]), max(permutation[u], permutation[v]))
        for u, v in canonical_edges
    )
    public_blocks = [sorted(permutation[v] for v in block) for block in canonical_blocks]
    public_blocks.sort()

    inst = {
        "vertex_count": vertex_count,
        "required_size": n,
        "edges": [[u, v] for u, v in edges],
        # Redundant, graph-checkable obstruction blocks make 200k density trials
        # cheap.  render() deliberately does not disclose this decomposition.
        "obstruction_blocks": public_blocks,
        "answer": answer,
    }
    return inst


def render(inst: dict) -> str:
    """Render a complete standalone power-domination problem."""

    adj = _adjacency(inst)
    rows = [f"{v}: " + " ".join(map(str, sorted(adj[v]))) for v in range(len(adj))]
    statement = f"""Power domination in a cubic graph

The graph is finite, simple, and undirected.  Its vertices are the integers
0 through {inst['vertex_count'] - 1}.  For each vertex, the adjacency list below
gives all of its neighbors; every undirected edge therefore appears in two rows.

For a set S, first mark every vertex in S and every neighbor of a vertex in S.
Then repeatedly apply this forcing rule: if a marked vertex has exactly one
unmarked neighbor, mark that neighbor.  Continue until no such move exists.
S is a power dominating set exactly when every vertex is eventually marked.

Find a power dominating set S of exactly {inst['required_size']} DISTINCT vertices.
Order does not matter, repetitions are forbidden, and all identifiers are
0-based integers in the inclusive range 0..{inst['vertex_count'] - 1}.

Adjacency lists:
{chr(10).join(rows)}

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {inst['required_size']} distinct vertex identifiers.
Syntax example for a hypothetical three-vertex instance: <answer>0, 1, 2</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the last answer-tag block, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text|python)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    if not body:
        return []
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if isinstance(value, list) and all(type(v) is int for v in value):
            return value
        return None
    pieces = [piece.strip() for piece in body.split(",")]
    if not pieces or any(not re.fullmatch(r"[+-]?\d+", piece) for piece in pieces):
        return None
    try:
        return [int(piece) for piece in pieces]
    except ValueError:
        return None


def _power_closure(adj: list[set[int]], selected: set[int]) -> set[int]:
    observed = set(selected)
    for vertex in selected:
        observed.update(adj[vertex])
    changed = True
    while changed:
        changed = False
        newly_observed: set[int] = set()
        for vertex in observed:
            unobserved = adj[vertex] - observed
            if len(unobserved) == 1:
                newly_observed.update(unobserved)
        if newly_observed - observed:
            observed.update(newly_observed)
            changed = True
    return observed


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any size-k witness; never inspect inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a list of vertex identifiers"
    if not answer:
        return False, "answer is empty"
    if any(type(vertex) is not int for vertex in answer):
        return False, "every vertex identifier must be an integer"
    if len(set(answer)) != len(answer):
        return False, "vertex identifiers must be distinct"
    count = inst.get("vertex_count")
    if any(vertex < 0 or vertex >= count for vertex in answer):
        return False, f"vertex identifier outside the inclusive range 0..{count - 1}"
    required = inst.get("required_size")
    if len(answer) != required:
        return False, f"answer must contain exactly {required} vertices"

    selected = set(answer)
    # Remark 2.16: the two true twins in each block cannot be reached unless S
    # meets that four-vertex block.  This exact necessary test makes random
    # candidate measurement cheap and gives a useful rejection reason.
    blocks = inst.get("obstruction_blocks")
    if not isinstance(blocks, list) or len(blocks) != required:
        try:
            recovered = _recover_diamonds(inst)
        except (TypeError, ValueError) as exc:
            return False, f"malformed necklace instance: {exc}"
        blocks = [list(twins + connectors) for twins, connectors in recovered]
    missed = sum(1 for block in blocks if selected.isdisjoint(block))
    if missed:
        return False, f"selected set misses {missed} closed twin-obstruction block(s)"

    try:
        adj = _adjacency(inst)
    except (TypeError, ValueError) as exc:
        return False, f"malformed graph: {exc}"
    observed = _power_closure(adj, selected)
    if len(observed) != count:
        return False, f"power-domination process leaves {count - len(observed)} vertices unmarked"
    return True, "ok"


def random_candidate(inst: dict, rng) -> object:
    """Uniformly sample the statement-implied space of distinct size-k subsets."""

    values = rng.sample(range(inst["vertex_count"]), inst["required_size"])
    values.sort()
    return values


def search_space(inst: dict) -> int | None:
    return math.comb(inst["vertex_count"], inst["required_size"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 250_000:
        return None
    valid = 0
    for candidate in itertools.combinations(
        range(inst["vertex_count"]), inst["required_size"]
    ):
        valid += int(verify(inst, list(candidate))[0])
    return valid


def _component_sizes_from_graph(inst: dict) -> list[int]:
    adj = _adjacency(inst)
    blocks = _recover_diamonds(inst)
    vertex_to_block: dict[int, int] = {}
    for index, (twins, connectors) in enumerate(blocks):
        for vertex in twins + connectors:
            vertex_to_block[vertex] = index
    quotient = [[] for _ in blocks]
    for index, (_twins, connectors) in enumerate(blocks):
        for connector in connectors:
            outside = [v for v in adj[connector] if vertex_to_block[v] != index]
            if len(outside) != 1:
                raise ValueError("connector does not have exactly one external edge")
            quotient[index].append(vertex_to_block[outside[0]])
    seen: set[int] = set()
    sizes: list[int] = []
    for start in range(len(blocks)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            for neighbor in quotient[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    return sorted(sizes)


def canonical_key(inst: dict) -> str:
    """Exact necklace-union isomorphism key: the sorted component lengths."""

    sizes = _component_sizes_from_graph(inst)
    payload = json.dumps(sizes, separators=(",", ":"))
    return "necklace-components:" + hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase block count until the 256-atom certificate cap becomes binding."""

    current = int(params.get("n", 2))
    if current >= 249:
        return "cap_bound"
    harder = dict(params)
    harder["n"] = min(249, max(current + 16, math.ceil(current * 1.55)))
    harder["component_max"] = min(23, int(params.get("component_max", 8)) + 2)
    return harder


def _answer_text(answer: list[int]) -> str:
    return "<answer>" + ", ".join(map(str, answer)) + "</answer>"


def _reference_closed_signature(inst: dict) -> tuple[list[int], int]:
    """Efficient Track-B algorithm: hash equal closed neighborhoods."""

    adj = _adjacency(inst)
    groups: dict[tuple[int, ...], list[int]] = {}
    operations = 0
    for vertex in range(len(adj)):
        signature = tuple(sorted(adj[vertex] | {vertex}))
        # Four inserts/reads, <=8 small-sort comparisons, four hash atoms.
        operations += 16
        groups.setdefault(signature, []).append(vertex)
    answer = sorted(min(vertices) for vertices in groups.values() if len(vertices) == 2)
    return answer, operations


def _attack_outlier(inst: dict) -> list[int]:
    adj = _adjacency(inst)
    # All degrees tie at three, so a degree outlier heuristic falls back to IDs.
    ranked = sorted(range(len(adj)), key=lambda v: (-len(adj[v]), v))
    return sorted(ranked[: inst["required_size"]])


def _attack_greedy_coverage(inst: dict) -> list[int]:
    adj = _adjacency(inst)
    selected: set[int] = set()
    covered: set[int] = set()
    for _ in range(inst["required_size"]):
        best = max(
            (
                len((adj[v] | {v}) - covered),
                -sum(adj[v]),
                -v,
                v,
            )
            for v in range(len(adj))
            if v not in selected
        )[-1]
        selected.add(best)
        covered.update(adj[best] | {best})
    return sorted(selected)


def _attack_periodic_labels(inst: dict) -> list[int]:
    # The obvious response to four vertices per block after labels are scrambled.
    return list(range(0, inst["vertex_count"], 4))[: inst["required_size"]]


def _relabel(inst: dict, permutation: list[int]) -> tuple[dict, list[int]]:
    changed = copy.deepcopy(inst)
    changed["edges"] = [
        sorted((permutation[u], permutation[v])) for u, v in inst["edges"]
    ]
    changed["obstruction_blocks"] = [
        sorted(permutation[v] for v in block) for block in inst["obstruction_blocks"]
    ]
    changed["answer"] = sorted(permutation[v] for v in inst["answer"])
    return changed, changed["answer"]


def _answer_metrics(params: dict) -> tuple[int, int, int]:
    blobs = [
        json.dumps(make_instance(seed=seed, **params)["answer"])
        for seed in range(20)
    ]
    chars = max(map(len, blobs))
    return chars, math.ceil(chars / 4), int(params["n"])


def selftest() -> dict:
    report: dict = {}

    # G1: every named preset over several unrelated seeds.
    g1_cases = []
    g1_pass = True
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_cases.append({"preset": preset, "seed": seed, "ok": ok, "reason": reason})
            g1_pass &= ok
            try:
                json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
            except (TypeError, ValueError):
                json_native = False
    report["G1_planted_verifies"] = {
        "pass": g1_pass and json_native,
        "cases": g1_cases,
        "json_native_answers": json_native,
    }

    ship_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=1234567, **ship_params)

    # G2: five corruptions with five distinct reasons.
    answer = list(inst["answer"])
    blocks = inst["obstruction_blocks"]
    chosen = set(answer)
    chosen_block = next(block for block in blocks if answer[0] in block)
    replacement = next(v for v in chosen_block if v not in chosen)
    replaced = list(answer)
    # Replace an element from another block by a second vertex of chosen_block.
    replace_index = next(
        index
        for index, vertex in enumerate(answer)
        if vertex not in chosen_block
    )
    replaced[replace_index] = replacement
    corruptions = {
        "drop_one": answer[:-1],
        "swap_one_to_wrong_block": replaced,
        "duplicate_one": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": answer[:-1] + [inst["vertex_count"]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I followed the propagation carefully.\n```text\n"
        + _answer_text(inst["answer"])
        + "\n```\nThat is my final set."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"]
        and parse_answer("no tagged answer here") is None
        and parse_answer("<answer>one, two</answer>") is None,
        "realistic_response_parsed": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: full 200k structure-aware trials at the shipping preset.
    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(8675309)
    for _ in range(guess_total):
        ok, _ = verify(inst, random_candidate(inst, guess_rng))
        guess_hits += int(ok)
    guess_rate = guess_hits / guess_total
    exact_solutions = 4 ** inst["required_size"]
    candidate_count = search_space(inst)
    exact_density = exact_solutions / candidate_count
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_rate,
        "exact_probability": exact_density,
        "candidate_space": candidate_count,
        "prior": "uniform distinct k-subsets, exactly as required by the statement",
    }

    # G6 attacks and honest Track-B reference algorithm.
    attack_names = (
        "outlier_degree_then_low_label",
        "greedy_new_closed_coverage",
        "random_restart_256",
        "by_hand_periodic_label_stride",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_attempts = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_seconds = []
    reference_operations = []
    for seed in range(8):
        probe = make_instance(seed=70_000 + seed, **ship_params)
        guesses = {
            "outlier_degree_then_low_label": _attack_outlier(probe),
            "greedy_new_closed_coverage": _attack_greedy_coverage(probe),
            "by_hand_periodic_label_stride": _attack_periodic_labels(probe),
        }
        restart_rng = random.Random(80_000 + seed)
        restart_answer = None
        for _ in range(256):
            candidate = random_candidate(probe, restart_rng)
            if verify(probe, candidate)[0]:
                restart_answer = candidate
                break
        guesses["random_restart_256"] = restart_answer
        for name, candidate in guesses.items():
            attack_attempts[name] += 1
            if candidate is not None and verify(probe, candidate)[0]:
                attack_successes[name] += 1

        started = time.perf_counter()
        reference_answer, operations = _reference_closed_signature(probe)
        elapsed = time.perf_counter() - started
        reference_seconds.append(elapsed)
        reference_operations.append(operations)
        reference_successes += int(verify(probe, reference_answer)[0])

    attacks = {
        name: {
            "successes": attack_successes[name],
            "attempts": attack_attempts[name],
        }
        for name in attack_names
    }
    reference = {
        "name": "sorted closed-neighborhood signature hashing",
        "complexity": "O((|V|+|E|) log Delta) exact",
        "wall_clock_sec_mean": sum(reference_seconds) / len(reference_seconds),
        "wall_clock_sec_max": max(reference_seconds),
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "successes": reference_successes,
        "attempts": 8,
        "solves": f"{reference_successes}/8, as expected",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": guess_rate < 1e-6 and reference_successes == 8,
        "shipping_exact_solution_count": exact_solutions,
        "shipping_candidate_count": candidate_count,
        "shipping_exact_density": exact_density,
        "shipping_sample_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_seconds_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_seconds_max": reference["wall_clock_sec_max"],
        "baseline_operations_mean": reference["operations_mean"],
    }
    report["G6_adversary_panel"] = {
        "pass": all(
            result["successes"] == 0 and result["attempts"] >= 8
            for result in attacks.values()
        ),
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    bigger = make_instance(seed=271828, **doubled_params)
    bigger_ok, bigger_reason = verify(bigger, bigger["answer"])
    report["G7_scales"] = {
        "pass": bigger_ok
        and bigger["vertex_count"] == 2 * inst["vertex_count"]
        and search_space(bigger) > search_space(inst),
        "shipping_vertices": inst["vertex_count"],
        "doubled_vertices": bigger["vertex_count"],
        "shipping_answer_elements": inst["required_size"],
        "doubled_answer_elements": bigger["required_size"],
        "doubled_verify_reason": bigger_reason,
    }

    invariant_checks = 0
    transform_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **ship_params)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        count = base["vertex_count"]
        reverse = list(reversed(range(count)))
        random_perm = list(range(count))
        random.Random(90_000 + seed).shuffle(random_perm)
        reverse_inst, reverse_answer = _relabel(base, reverse)
        random_inst, random_answer = _relabel(base, random_perm)
        edge_reordered = copy.deepcopy(base)
        edge_reordered["edges"] = list(reversed(edge_reordered["edges"]))
        composed, composed_answer = _relabel(edge_reordered, random_perm)
        transforms = (
            ("reverse_vertex_labels", reverse_inst, reverse_answer),
            ("random_vertex_relabelling", random_inst, random_answer),
            ("reverse_edge_order", edge_reordered, edge_reordered["answer"]),
            ("edge_order_then_relabelling", composed, composed_answer),
        )
        for name, changed, carried in transforms:
            invariant_checks += 1
            if canonical_key(changed) != base_key:
                failures.append([seed, name, "canonical key changed"])
            ok, reason = verify(changed, carried)
            transform_checks += 1
            if not ok:
                failures.append([seed, name, reason])
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "valid_transformation_checks": transform_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "failures": failures,
        "symmetries": [
            "arbitrary vertex relabelling",
            "edge-list reordering",
            "compositions of relabelling and reordering",
            "necklace component reordering and reversal (captured by component lengths)",
        ],
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(ship_params)
    route_operations = int(ship_params["n"]) + 12
    arms = copy.deepcopy(G9_ARM_RESULTS)
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_tokens <= 500
        and answer_elements <= 256
        and route_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_yet_measured"
            if arms["hinted"]["attempts"] == 0
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
        "caps": {"chars": 2000, "tokens": 500, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if re.match(r"G[1-9]_", key)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
