"""Verified Track-B generator for arXiv:2409.17832.

The native object is an acyclic quiver whose underlying simple graph is one
cycle and whose parallel-arrow multiplicities form a shuffled arithmetic
progression.  The answer is its exact Markov invariant, represented as a
reduced rational.  It is known by a composition of the paper's cycle identity
with the closed identity for a sum of squared arithmetic-progression terms.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "acyclic quiver with integer arrow multiplicities",
        "unipotent companion over Z",
        "Markov invariant of an Alexander polynomial",
    ],
    "verification_operations": [
        "exact directed-cycle and degree checks",
        "exact integer squaring and addition",
        "reduced-rational comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Use the paper's edge-square/cycle decomposition and the shuffled "
        "arithmetic-progression multiset; otherwise compute the invariant by "
        "mechanically processing every multiplicity."
    ),
    "hardness_basis": (
        "Track B: Proposition 3.21 and Example 6.4 give an O(n) exact sum-of-"
        "squares algorithm (943 exact arithmetic operations at shipping n=472; "
        "measured wall-clock cost is recorded by selftest), while recognizing the complete "
        "arithmetic progression reduces the arithmetic to at most 18 exact operations."
    ),
    "max_answer_tokens": 16,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "weight_bits": 5},
    "easy": {"n": 472, "weight_bits": 40},
    "medium": {"n": 629, "weight_bits": 44},
    "hard": {"n": 838, "weight_bits": 48},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "Hint: The relevant structure is the edge-square/cycle decomposition and the "
    "arithmetic-progression multiset of arrow multiplicities."
)
PLACEBO_HINT: str = (
    "Hint: The relevant challenge is exact integer bookkeeping across the displayed "
    "vertex labels, arrow directions, and multiplicities."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One reduced nonnegative rational [p, 1], where p is an integer from 0 "
        "through n*(2^weight_bits-1)^2 inclusive."
    ),
    "bounds": {
        "numerator_min": 0,
        "numerator_max": "n*(2^weight_bits-1)^2",
        "denominator": 1,
        "json_shape": "[numerator, denominator]",
    },
}

G9_ORACLE_RESULTS: dict = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 2, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy",
    "one_step_up": {
        "params": {"n": 629, "weight_bits": 44},
        "solved": 1,
        "completed_attempts": 2,
        "verdict": "too_easy",
    },
}

NOTES: str = r"""
Definition 2.3 fixes quiver mutation and its involutivity; Definitions 2.5,
3.2, 3.3, and 3.20 fix acyclicity, cyclic order, the unipotent companion, the
Alexander polynomial, and the Markov invariant.  Theorem 1.1 makes every
mutation-acyclic quiver totally proper.  The family here needs no surrogate:
it uses the paper's native integer-multiplicity quivers.

Step-0 decision.  The suggested mutation-sequence search family was not used:
the paper gives no distributional lower bound for recovering an acyclic
representative, so that construction would not support Track A, while no
polynomial recovery algorithm is supplied to ground an honest Track-B claim.
Instead, Proposition 3.21 gives an executable exact certificate algorithm.  It
expresses M_Q as edge squares plus contributions from almost-directed cycles;
Example 6.4 specializes this to weighted cycle quivers.  With at least two
arrows in each direction around the cycle, the cycle contribution is zero.

Construction.  Sample the arithmetic progression first, shuffle its terms onto
the cycle, orient two source-to-sink arcs with both lengths at least two, and
randomly relabel and reorder the edges.  The answer is obtained before the
rendered quiver is assembled from
  sum_{i=0}^{n-1}(a+i*d)^2
    = n*a^2 + a*d*n*(n-1) + d^2*n*(n-1)*(2*n-1)/6.
This is composition of identities, not solution of the emitted instance.

Hardness and easy regime.  Proposition 3.21 is itself an O(n) algorithm on
this restricted family, so Track A would be false.  At shipping size it still
requires n nontrivial squares and n-1 additions if used mechanically.  The
compact route notices that the multiplicities are exactly a complete shuffled
arithmetic progression and uses the displayed closed identity in at most 18
exact operations.  The demo is intentionally hand-scale.  The source/sink
orientation excludes the easy extra product terms in Example 6.4 for l=0 or 1.

Attacks.  Random relabeling, edge-order shuffling, and weight shuffling remove
positional signals.  The panel checks a largest-weight outlier guess, a linear
greedy sum, 4096 structure-aware random restarts, and a by-hand prefix
mean-square extrapolation.  The successful paper-standard sum-of-squares
algorithm is reported separately, as Track B requires.  The structural hint
names the two decompositions but gives neither the vanished-cycle conclusion
nor the closed-form calculation.

G9 result.  The bare pool hardened at n=472, but the structural hint yielded
verified solutions on 2/3 attempts there.  The single permitted move to n=629
also yielded a verified hinted solution (1/2 completed attempts); later calls
hit the external API key limit, which is irrelevant because any verified solve
already fails the polarity-flipped gate.  The family is therefore rejected
under G9(b), not shipped.

Canonicalization.  canonical_key reconstructs the unique undirected cycle and
minimizes its (weight,direction) word over every rotation and reflection.  It
therefore ignores vertex names and input edge order without collapsing the
directed weighted object.  Selftest exercises relabelings, reorderings, and
their compositions, and verifies that the carried rational witness remains
valid.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _ap_square_sum(n: int, first: int, step: int) -> int:
    """Closed identity used by construction, not a scan of the instance."""
    return (
        n * first * first
        + first * step * n * (n - 1)
        + step * step * n * (n - 1) * (2 * n - 1) // 6
    )


def make_instance(n: int, seed: int = 0, weight_bits: int = 16, **params) -> dict:
    """Compose a weighted-cycle Markov certificate from sampled identities."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    if isinstance(weight_bits, bool) or not isinstance(weight_bits, int):
        raise ValueError("weight_bits must be an integer")
    if weight_bits < 4 or weight_bits > 256:
        raise ValueError("weight_bits must lie from 4 through 256")

    limit = (1 << weight_bits) - 1
    max_step = (limit - 1) // (n - 1)
    if max_step < 1:
        raise ValueError("weight_bits is too small for n distinct multiplicities")

    rng = random.Random(seed)
    step = rng.randint(max(1, max_step // 3), max_step)
    first = rng.randint(1, limit - step * (n - 1))
    weights = [first + i * step for i in range(n)]
    rng.shuffle(weights)

    # Two directed source-to-sink arcs.  Both have at least two edges, so the
    # single cycle is not almost directed and contributes zero in Prop. 3.21.
    forward_count = rng.randint(2, n - 2)
    labels = list(range(1, n + 1))
    rng.shuffle(labels)
    edges = []
    for i, weight in enumerate(weights):
        left = labels[i]
        right = labels[(i + 1) % n]
        if i < forward_count:
            edges.append([left, right, weight])
        else:
            edges.append([right, left, weight])
    rng.shuffle(edges)

    markov = _ap_square_sum(n, first, step)
    return {
        "family": "Markov invariant of an acyclic weighted cycle quiver",
        "n": n,
        "weight_bits": weight_bits,
        "multiplicity_limit": limit,
        "edges": edges,
        "answer": [markov, 1],
    }


def render(inst: dict) -> str:
    lines = "\n".join(
        f"  {tail} -> {head} : {weight}"
        for tail, head, weight in inst["edges"]
    )
    statement = f"""EXACT MARKOV INVARIANT OF A WEIGHTED QUIVER

A quiver is a finite directed graph with parallel arrows allowed and no loops or
directed 2-cycles.  The vertices here are the integers 1 through {inst['n']}.
Each line `u -> v : w` means exactly w parallel arrows from u to v.  The
underlying simple undirected graph of this instance is one cycle, and the
displayed orientation is guaranteed acyclic.  At least two cycle edges point in
each traversal direction.  The multiset of the {inst['n']} positive
multiplicities is guaranteed to be one complete arithmetic progression of
distinct integers, in shuffled order; each is at most {inst['multiplicity_limit']}.

Choose any topological order q_1,...,q_n, meaning every arrow points from an
earlier q_i to a later q_j.  In that order define B by
  B[i,j] = (# arrows q_i -> q_j) - (# arrows q_j -> q_i).
Define the integer upper-triangular matrix U by U[i,i]=1, U[i,j]=-B[i,j] for
i<j, and U[i,j]=0 for i>j.  Thus B=U^T-U.  Define
  Delta(t) = det(t*U - U^T),
and define the Markov invariant M to be n plus the coefficient of t^(n-1) in
Delta(t).  The value is independent of the chosen topological order.

Edges (their line order has no meaning):
{lines}

Compute M exactly.  The certificate language is the reduced nonnegative rational
[p,1] with 0 <= p <= {inst['n'] * inst['multiplicity_limit'] ** 2}; although M
is an integer, the two-entry rational encoding is mandatory.

Give your final answer inside <answer></answer> tags, as the JSON array
[numerator, denominator] using base-10 integers.
Example: <answer>[12345, 1]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: object) -> object | None:
    """Extract exactly one JSON rational from a tagged model response."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if len(matches) != 1:
        return None
    body = matches[0].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _cycle_word(inst: dict) -> tuple[tuple[int, int], ...]:
    """Canonical weighted/oriented cycle word, or raise ValueError."""
    n = inst.get("n")
    edges = inst.get("edges")
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("invalid vertex count")
    if not isinstance(edges, list) or len(edges) != n:
        raise ValueError("the quiver must have exactly n weighted edges")

    adjacency = {v: [] for v in range(1, n + 1)}
    edge_data = {}
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 3:
            raise ValueError("each edge must be [tail, head, multiplicity]")
        tail, head, weight = edge
        if any(isinstance(x, bool) or not isinstance(x, int) for x in edge):
            raise ValueError("edge entries must be integers")
        if not (1 <= tail <= n and 1 <= head <= n) or tail == head:
            raise ValueError("edge endpoint is out of range")
        if weight <= 0 or weight > inst.get("multiplicity_limit", -1):
            raise ValueError("multiplicity is out of range")
        pair = (min(tail, head), max(tail, head))
        if pair in edge_data:
            raise ValueError("the underlying simple edges must be distinct")
        edge_data[pair] = (tail, head, weight)
        adjacency[tail].append(head)
        adjacency[head].append(tail)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("the underlying simple graph is not one cycle")

    def traverse(start: int, nxt: int) -> tuple[tuple[int, int], ...]:
        word = []
        previous, current = start, nxt
        for _ in range(n):
            pair = (min(previous, current), max(previous, current))
            tail, head, weight = edge_data[pair]
            direction = 1 if (tail, head) == (previous, current) else -1
            word.append((weight, direction))
            following = adjacency[current][0]
            if following == previous:
                following = adjacency[current][1]
            previous, current = current, following
        if previous != start or current != nxt:
            raise ValueError("the underlying graph is disconnected")
        return tuple(word)

    words = []
    for start in range(1, n + 1):
        for nxt in adjacency[start]:
            words.append(traverse(start, nxt))
    return min(words)


def _validated_weights(inst: dict) -> list[int]:
    """Inspect the native instance and return its valid multiplicities."""
    word = _cycle_word(inst)
    directions = [direction for _, direction in word]
    agreeing = directions.count(1)
    if min(agreeing, len(word) - agreeing) < 2:
        raise ValueError("the cycle orientation must have two arrows each way")

    weights = sorted(weight for weight, _ in word)
    if len(set(weights)) != len(weights):
        raise ValueError("multiplicities must be distinct")
    step = weights[1] - weights[0]
    if step <= 0 or any(weights[i] - weights[i - 1] != step for i in range(2, len(weights))):
        raise ValueError("multiplicities are not a complete arithmetic progression")
    return weights


def _expected_markov(inst: dict) -> int:
    """Executable specialization of Proposition 3.21 / Example 6.4."""
    weights = _validated_weights(inst)
    return sum(weight * weight for weight in weights)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any correctly encoded exact Markov invariant; never read answer key."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 1:
        return False, "answer is missing its denominator"
    if len(answer) > 2:
        return False, "answer has extra elements"
    if len(answer) != 2:
        return False, "answer must contain exactly two entries"
    numerator, denominator = answer
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "numerator and denominator must be integers"
    if denominator <= 0:
        return False, "denominator must be positive"
    if numerator < 0:
        return False, "numerator must be nonnegative"
    if math.gcd(abs(numerator), denominator) != 1:
        return False, "rational must be in reduced form"
    try:
        expected = _expected_markov(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, "invalid instance: " + str(exc)
    if numerator != expected * denominator:
        return False, "wrong exact Markov invariant"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement's already-reduced rational language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    upper = inst["n"] * inst["multiplicity_limit"] ** 2
    return [rng.randrange(upper + 1), 1]


def search_space(inst: dict) -> int | None:
    """Exact size of the bounded reduced-rational certificate language."""
    return inst["n"] * inst["multiplicity_limit"] ** 2 + 1


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when at most 100,000 values."""
    size = search_space(inst)
    if size is None or size > 100_000:
        return None
    expected = _expected_markov(inst)
    count = 0
    for numerator in range(size):
        if numerator == expected:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Hash the cycle word modulo all rotations/reflections, never the seed."""
    word = _cycle_word(inst)
    payload = json.dumps(word, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the cycle and coefficient entropy while the rational stays two atoms."""
    if not isinstance(params, dict):
        raise TypeError("params must be a dict")
    n = params.get("n")
    bits = params.get("weight_bits", 16)
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("params must contain integer n")
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise ValueError("weight_bits must be an integer")
    return {"n": n + max(24, n // 3), "weight_bits": min(256, bits + 4)}


def _relabel_and_reorder(inst: dict, rng: random.Random, relabel: bool, reorder: bool) -> dict:
    transformed = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in inst.items()
    }
    edges = [list(edge) for edge in inst["edges"]]
    if relabel:
        labels = list(range(1, inst["n"] + 1))
        shuffled = list(labels)
        rng.shuffle(shuffled)
        mapping = dict(zip(labels, shuffled))
        edges = [[mapping[u], mapping[v], w] for u, v, w in edges]
    if reorder:
        rng.shuffle(edges)
    transformed["edges"] = edges
    transformed["answer"] = list(inst["answer"])
    return transformed


def _attack_results(params: dict, attempts: int = 8) -> tuple[dict, dict]:
    names = (
        "outlier_largest_multiplicity_square",
        "greedy_linear_weight_sum",
        "random_restart_4096",
        "by_hand_prefix_mean_square",
    )
    results = {name: {"successes": 0, "attempts": attempts} for name in names}
    random_iterations = 0
    random_wall = 0.0
    reference_successes = 0
    reference_wall = 0.0
    n = params["n"]

    for seed in range(8100, 8100 + attempts):
        inst = make_instance(seed=seed, **params)
        weights = [edge[2] for edge in inst["edges"]]
        candidates = {
            names[0]: [max(weights) ** 2, 1],
            names[1]: [sum(weights), 1],
            names[3]: [n * sum(w * w for w in weights[:12]) // 12, 1],
        }
        for name, candidate in candidates.items():
            if verify(inst, candidate)[0]:
                results[name]["successes"] += 1

        rng = random.Random(seed ^ 0x240917832)
        expected = _expected_markov(inst)
        started = time.perf_counter()
        found = False
        for _ in range(4096):
            random_iterations += 1
            if random_candidate(inst, rng)[0] == expected:
                found = True
                break
        random_wall += time.perf_counter() - started
        if found:
            results[names[2]]["successes"] += 1

        started = time.perf_counter()
        candidate = [sum(w * w for w in weights), 1]
        reference_wall += time.perf_counter() - started
        if verify(inst, candidate)[0]:
            reference_successes += 1

    reference = {
        "name": "Proposition 3.21 weighted-cycle sum of squares",
        "complexity": "O(n) exact integer arithmetic",
        "wall_clock_sec_total": round(reference_wall, 9),
        "wall_clock_sec_per_instance": round(reference_wall / attempts, 9),
        "operations_per_instance": 2 * n - 1,
        "operations_total": attempts * (2 * n - 1),
        "solves": f"{reference_successes}/{attempts}, as expected",
    }
    baseline = {
        "iterations": random_iterations,
        "wall_clock_sec": round(random_wall, 6),
    }
    return results, {"reference_algorithm": reference, "baseline": baseline}


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(v) for v in value)
    return 1


def selftest() -> dict:
    """Run correctness, resistance, scaling, canonical, and suitability gates."""
    report = {
        "paper": "2409.17832",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    planted_attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 91):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            if not verify(inst, inst["answer"])[0]:
                raise AssertionError(f"G1 failed for {preset=} {seed=}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "attempts": planted_attempts,
        "json_roundtrips": json_roundtrips,
    }

    ship = make_instance(seed=20240917, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = ship["answer"]
    corruptions = {
        "drop_one": planted[:1],
        "swap": list(reversed(planted)),
        "duplicate": planted + planted[:1],
        "empty": [],
        "out_of_range": [planted[0], 0],
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = reason
    g2_pass = len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "rejected": len(reasons),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    realistic = (
        "I used the coefficient definition and checked the sign.\n\n"
        "```text\nFinal result follows.\n```\n"
        f"<answer>\n{json.dumps(planted)}\n</answer>\n"
        "The denominator is positive."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(ship, parsed)[0],
        "parsed": parsed,
    }

    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(0x240917832)
    expected = _expected_markov(ship)
    for _ in range(guess_total):
        if random_candidate(ship, guess_rng)[0] == expected:
            guess_hits += 1
    space = search_space(ship)
    theoretical_density = 1.0 / space
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6 and theoretical_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "search_space": space,
        "exact_unique_answer_density": theoretical_density,
        "sampling_prior": "uniform over every reduced [p,1] allowed by the statement",
    }

    attacks, costs = _attack_results(DIFFICULTY[SHIPPING_DIFFICULTY], attempts=8)
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and theoretical_density < 1e-6,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_density": guess_hits / guess_total,
        "shipping_exact_unique_answer_density": theoretical_density,
        "demo_exact_valid_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_iterations": costs["baseline"]["iterations"],
        "baseline_wall_seconds": costs["baseline"]["wall_clock_sec"],
    }

    all_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4,
        "attacks": attacks,
        "reference_algorithm": costs["reference_algorithm"],
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["weight_bits"] += 1
    doubled = make_instance(seed=17, **doubled_params)
    scaled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": scaled_ok and search_space(doubled) > space,
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_space_bits": space.bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
    }

    invariant_checks = 0
    witness_checks = 0
    distinct_keys = set()
    for seed in range(20):
        inst = make_instance(seed=20000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        distinct_keys.add(key)
        transform_rng = random.Random(30000 + seed)
        for relabel, reorder in ((True, False), (False, True), (True, True)):
            changed = _relabel_and_reorder(inst, transform_rng, relabel, reorder)
            if canonical_key(changed) != key:
                raise AssertionError("G8 key changed under an isomorphism")
            invariant_checks += 1
            if not verify(changed, inst["answer"])[0]:
                raise AssertionError("G8 transformation did not preserve the problem")
            witness_checks += 1
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 60 and witness_checks == 60 and len(distinct_keys) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "unrelated_distinct": len(distinct_keys),
        "unrelated_attempts": 20,
        "symmetries": ["vertex relabeling", "edge reordering", "their composition"],
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _atomic_elements(ship["answer"])
    intended_operations = 18
    arms = G9_ORACLE_RESULTS["arms"]
    hinted_verdict = G9_ORACLE_RESULTS["hinted_verdict"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    diagnostic_difference = (
        hinted_rate - placebo_rate
        if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]
        else None
    )
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": hinted_verdict == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": diagnostic_difference,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
