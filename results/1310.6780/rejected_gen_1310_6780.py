"""Exact uncertain-clique probability generator for arXiv:1310.6780.

The paper's Observation 1 says that, under independent edge existence, the
probability of a fixed clique is the product of its edge probabilities.  This
module composes two permutation identities with telescoping rational factors.
The ordinary evaluation still visits every factor; the planted certificate is
known from the endpoints before the uncertain graph is assembled.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time
from fractions import Fraction


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "rational_exact",
    "computational_core": "graph",
    "certificate_form": "rational",
    "native_objects": [
        "complete uncertain graph with an exact rational edge-probability function",
        "specified vertex set whose clique probability is requested",
    ],
    "verification_operations": [
        "exact integer polynomial summation",
        "exact gcd reduction",
        "exact rational cross multiplication",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Reindexing the edge factors and layer slopes by their affine "
        "permutations exposes two nested telescoping products; without this "
        "change of variables the direct method visits every edge-layer factor."
    ),
    "hardness_basis": (
        "Track B: exact endpoint cancellation implementing Observation 1 runs "
        "in O(L*n^2) expected time; at the hard preset it evaluates 2,585,720 "
        "edge-layer factors (5,171,460 cancellation/multiplication operations), "
        "averaging 1.88 seconds across eight shipping seeds in the retained "
        "self-test, while the compact "
        "permutation-and-power-sum route uses 19 exact arithmetic operations."
    ),
    "max_answer_tokens": 6,
}

NATIVE = {
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON-native pair [p,q], rendered as p/q, with integer 0 <= p <= q, "
        "1 <= q <= the instance's displayed max_denominator.  The pair need "
        "not be reduced; it denotes the exact rational p/q."
    ),
    "bounds": {
        "components": 2,
        "numerator_minimum": 0,
        "numerator_maximum": "denominator",
        "denominator_minimum": 1,
        "denominator_maximum": "instance.max_denominator",
    },
}

DIFFICULTY = {
    "demo": {"n": 5, "layers": 2, "coefficient_span": 5},
    "easy": {"n": 193, "layers": 8, "coefficient_span": 31},
    "medium": {"n": 353, "layers": 14, "coefficient_span": 127},
    "hard": {"n": 509, "layers": 20, "coefficient_span": 509},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Both affine index maps merely permute complete residue ranges whose neighboring potential factors share endpoints."
)
PLACEBO_HINT = (
    "Both nested definitions reward careful attention to zero-based ranges, inclusive bounds, and reduced-fraction formatting."
)

# Updated after script-owned hardening runs.  The arms are diagnostics, not gates.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
    "placebo_verdict": "not_run",
}

NOTES = r"""
Paper grounding. Section 2, Definition 3 defines the clique probability of a
vertex set in an uncertain graph. Observation 1 gives its exact value as the
product of the probabilities of all induced edges, using the paper's mutual
independence assumption. Section 4 maintains the same products incrementally;
Theorem 3 bounds the full MULE enumeration by O(n*2^n), and Section 4.4's
LARGE-MULE only changes which maximal cliques are emitted. The family here
stays in the paper's native object: a complete uncertain graph and its exact
rational probability function. It asks for the probability of its displayed
vertex set, not for a graph surrogate or a sampled possible world.

STEP 0 and track choice. A task asking for any alpha-maximal clique would not
support Track A: alpha-clique feasibility is hereditary (Observation 2), so
starting from one vertex and greedily adding every feasible extension produces
a maximal witness in polynomial time. Theorem 1's extremal construction is
even easier as a puzzle because every half-size subset is a valid answer. The
certificate here is also produced by an efficient algorithm: direct exact
evaluation of Observation 1 visits L*binom(n,2) rational factors. Therefore the
module declares Track B and reports that successful method separately from its
failing attacks.

Construction and compact route. Give the binom(n,2) edges lexicographic ranks
r and map them to s=(a*r+b) mod m, where gcd(a,m)=1. Give the L layers ranks l
and map them to t=(u*l+v) mod L, where gcd(u,L)=1. A positive quadratic c(t)
is the layer slope. Starting at x_0=B, put x_(l+1)=x_l+m*c(t_l), and give edge
rank s the factor (x_l+c_l*s)/(x_l+c_l*(s+1)) in layer l. The edge map covers
every s exactly once, so one layer collapses to x_l/x_(l+1); the layers then
collapse to B/x_L. Since t covers 0..L-1, x_L is obtained from the standard
sums of t and t^2. This is composition of identities, and the two endpoints
are known before the vertex and rank presentations are shuffled.

Attack response. The edge-rank multiplier and offset, layer multiplier and
offset, vertex presentation, base, and positive quadratic coefficients all
vary by seed. The panel checks a near-one edge outlier guess, a greedy
one-layer cancellation, bounded random rational restarts, and the tempting
linear ansatz that drops the quadratic term. Exact endpoint cancellation is
the successful O(L*n^2) reference algorithm, not a failing attack. The
canonical key ignores vertex names and edge assignment and keys on the exact
probability multiset parameters; this is a strong cheap invariant, not a
complete weighted-graph isomorphism canonical form.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _validate_params(n: int, layers: int, coefficient_span: int) -> None:
    values = (n, layers, coefficient_span)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
        raise ValueError("n, layers, and coefficient_span must be integers")
    if n < 3:
        raise ValueError("n must be at least 3")
    if layers < 2:
        raise ValueError("layers must be at least 2")
    if coefficient_span < 2:
        raise ValueError("coefficient_span must be at least 2")


def _random_unit(modulus: int, rng: random.Random) -> int:
    while True:
        value = rng.randrange(1, modulus)
        if math.gcd(value, modulus) == 1:
            return value


def _layer_data(inst: dict) -> tuple[list[int], list[int]]:
    count = inst["layer_map"]["modulus"]
    multiplier = inst["layer_map"]["multiplier"]
    offset = inst["layer_map"]["offset"]
    c0, c1, c2 = inst["slope_coefficients"]
    m = inst["edge_rank_map"]["modulus"]
    x = inst["base_potential"]
    potentials = [x]
    slopes = []
    for layer in range(count):
        t = (multiplier * layer + offset) % count
        c = c0 + c1 * t + c2 * t * t
        slopes.append(c)
        x += m * c
        potentials.append(x)
    return slopes, potentials


def _closed_form(inst: dict) -> list[int]:
    """Compute the endpoint ratio from instance fields, never from answer."""
    layers = inst["layer_map"]["modulus"]
    c0, c1, c2 = inst["slope_coefficients"]
    sum_t = layers * (layers - 1) // 2
    sum_t2 = layers * (layers - 1) * (2 * layers - 1) // 6
    slope_sum = layers * c0 + c1 * sum_t + c2 * sum_t2
    numerator = inst["base_potential"]
    denominator = numerator + inst["edge_rank_map"]["modulus"] * slope_sum
    common = math.gcd(numerator, denominator)
    return [numerator // common, denominator // common]


def make_instance(
    n: int,
    seed: int = 0,
    layers: int = 8,
    coefficient_span: int = 31,
    **params,
) -> dict:
    """Compose a known rational product certificate; never solve the result."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, layers, coefficient_span)
    rng = random.Random(seed)
    m = n * (n - 1) // 2

    edge_multiplier = _random_unit(m, rng)
    edge_offset = rng.randrange(m)
    layer_multiplier = _random_unit(layers, rng)
    layer_offset = rng.randrange(layers)

    c0 = rng.randrange(1, coefficient_span + 1)
    c1 = rng.randrange(1, coefficient_span + 1)
    c2 = rng.randrange(1, coefficient_span + 1)
    base = rng.randrange(coefficient_span + 1, coefficient_span * 97 + 98)

    vertices = list(range(n))
    rank_order = list(vertices)
    rng.shuffle(vertices)
    rng.shuffle(rank_order)

    inst = {
        "n": n,
        "vertices": vertices,
        "rank_order": rank_order,
        "edge_rank_map": {
            "multiplier": edge_multiplier,
            "offset": edge_offset,
            "modulus": m,
        },
        "layer_map": {
            "multiplier": layer_multiplier,
            "offset": layer_offset,
            "modulus": layers,
        },
        "slope_coefficients": [c0, c1, c2],
        "base_potential": base,
    }
    answer = _closed_form(inst)
    # All syntactically valid rational candidates up to this height form the
    # declared, exactly countable certificate language.
    inst["max_denominator"] = max(1000, 11 * answer[1])
    inst["answer"] = answer
    return inst


def render(inst: dict) -> str:
    n = inst["n"]
    m = inst["edge_rank_map"]["modulus"]
    a = inst["edge_rank_map"]["multiplier"]
    b = inst["edge_rank_map"]["offset"]
    layers = inst["layer_map"]["modulus"]
    u = inst["layer_map"]["multiplier"]
    v = inst["layer_map"]["offset"]
    c0, c1, c2 = inst["slope_coefficients"]
    rank_order = " ".join(str(x) for x in inst["rank_order"])
    shown_vertices = " ".join(str(x) for x in inst["vertices"])
    statement = f"""Exact clique probability in an uncertain graph

An uncertain graph is a simple undirected graph in which every possible edge
exists independently with its stated probability.  If C is a set of vertices,
its clique probability clq(C) is the probability that every unordered pair in
C is present; independence means clq(C) is the product of those edge
probabilities.

This instance is a complete uncertain graph on n={n} vertices.  The vertex IDs,
shown in arbitrary input order, are:
{shown_vertices}

All of those vertices belong to C.  Edge probabilities are specified exactly
by the following finite formula.  No floating-point approximation is intended.

The rank order is this zero-based list of all vertex IDs:
{rank_order}

For an unordered edge {{v,w}}, let i<j be the two zero-based positions of v and
w in the rank order.  Its lexicographic unordered-pair rank is

    r = i*(2*n-i-1)/2 + (j-i-1),

where the division is exact.  Thus 0 <= r < m, with m={m}.  Put

    s = ({a}*r + {b}) mod {m}.

There are L={layers} layers, numbered ell=0,...,{layers - 1}.  In layer ell put

    t_ell = ({u}*ell + {v}) mod {layers},
    c_ell = {c0} + {c1}*t_ell + {c2}*t_ell^2.

Define integer potentials by x_0={inst['base_potential']} and

    x_(ell+1) = x_ell + {m}*c_ell.

The exact existence probability of edge {{v,w}} is

    p({{v,w}}) = PRODUCT over ell=0,...,{layers - 1} of
                 (x_ell + c_ell*s) / (x_ell + c_ell*(s+1)).

Every displayed numerator and denominator is positive, and every factor is at
most 1, so this defines a valid uncertain graph.  Compute clq(C) exactly.

Your certificate language is a pair of integers [P,Q] denoting P/Q, with
0 <= P <= Q and 1 <= Q <= {inst['max_denominator']}.  The fraction need not be
reduced; equivalent exact fractions are accepted.  In the rendered answer,
write the same pair as P/Q.

Give your final answer inside <answer></answer> tags, as one exact fraction P/Q.
Example: <answer>3/7</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if matches:
        body = matches[-1].strip()
    else:
        # A cautious fallback for otherwise well-formed model prose.
        fractions = re.findall(r"(?<![\d/+-])([+-]?\d+)\s*/\s*([+-]?\d+)(?![\d/])", text)
        if len(fractions) != 1:
            return None
        return [int(fractions[0][0]), int(fractions[0][1])]
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S).strip()
    match = re.fullmatch(r"([+-]?\d+)\s*/\s*([+-]?\d+)", body)
    if match:
        return [int(match.group(1)), int(match.group(2))]
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if isinstance(value, list) and len(value) == 2:
        return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    if answer is None:
        return False, "no answer was parsed"
    if not isinstance(answer, list):
        return False, "answer must be a two-element list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer is missing the denominator"
    if len(answer) > 2:
        return False, "answer has extra components"
    numerator, denominator = answer
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "numerator and denominator must be integers"
    if denominator <= 0:
        return False, "denominator must be positive"
    if numerator < 0 or numerator > denominator:
        return False, "fraction must lie in the closed interval [0,1]"
    if denominator > inst["max_denominator"]:
        return False, "denominator exceeds the certificate-language bound"
    true_numerator, true_denominator = _closed_form(inst)
    if numerator * true_denominator != denominator * true_numerator:
        return False, "fraction is not the exact clique probability"
    return True, "ok"


def search_space(inst: dict) -> int:
    height = inst["max_denominator"]
    return height * (height + 3) // 2


def _cumulative_candidates(denominator: int) -> int:
    return denominator * (denominator + 3) // 2


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over all bounded rational pairs already satisfying 0<=P<=Q."""
    height = inst["max_denominator"]
    index = rng.randrange(search_space(inst))
    # Invert q(q+3)/2 using an integer-square-root estimate and exact repairs.
    denominator = max(1, (math.isqrt(8 * index + 9) - 3) // 2)
    while _cumulative_candidates(denominator) <= index:
        denominator += 1
    while denominator > 1 and _cumulative_candidates(denominator - 1) > index:
        denominator -= 1
    before = _cumulative_candidates(denominator - 1) if denominator > 1 else 0
    numerator = index - before
    return [numerator, denominator]


def enumerate_all(inst: dict) -> int | None:
    total = search_space(inst)
    if total > 200_000:
        return None
    count = 0
    for denominator in range(1, inst["max_denominator"] + 1):
        for numerator in range(denominator + 1):
            if verify(inst, [numerator, denominator])[0]:
                count += 1
    return count


def canonical_key(inst: dict) -> str:
    slopes, _ = _layer_data(inst)
    # Vertex IDs, their presentation, and the assignment of the same probability
    # multiset to edge ranks are deliberately absent.
    invariant = {
        "n": inst["n"],
        "base": inst["base_potential"],
        "ordered_slopes": slopes,
    }
    blob = json.dumps(invariant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    out = {k: v for k, v in params.items() if k != "_preset"}
    n = int(out["n"])
    layers = int(out["layers"])
    span = int(out["coefficient_span"])
    if n >= 200_000 or layers >= 512:
        return "cap_bound"
    # Three fixed-witness axes move: more edges, more layers, and more numeric
    # entropy.  The answer remains two integers.
    out["n"] = 2 * n + 1
    out["layers"] = layers + 8
    out["coefficient_span"] = 2 * span + 1
    return out


def _reference_direct_product(inst: dict) -> tuple[list[int], int]:
    """Exact O(L*m) factor generation with blind whole-factor cancellation."""
    m = inst["edge_rank_map"]["modulus"]
    a = inst["edge_rank_map"]["multiplier"]
    b = inst["edge_rank_map"]["offset"]
    slopes, potentials = _layer_data(inst)
    residual_numerators = []
    residual_denominators = []
    operations = 0
    for layer, slope in enumerate(slopes):
        unmatched_num = set()
        unmatched_den = set()
        x = potentials[layer]
        for rank in range(m):
            s = (a * rank + b) % m
            numerator = x + slope * s
            denominator = numerator + slope
            if numerator in unmatched_den:
                unmatched_den.remove(numerator)
            else:
                unmatched_num.add(numerator)
            if denominator in unmatched_num:
                unmatched_num.remove(denominator)
            else:
                unmatched_den.add(denominator)
            operations += 2
        if unmatched_num != {x} or unmatched_den != {x + slope * m}:
            raise AssertionError("exact factor cancellation did not reach endpoints")
        residual_numerators.append(x)
        residual_denominators.append(x + slope * m)
    value = Fraction(1, 1)
    for numerator, denominator in zip(residual_numerators, residual_denominators):
        value *= Fraction(numerator, denominator)
        operations += 1
    return [value.numerator, value.denominator], operations


def _one_layer_guess(inst: dict) -> list[int]:
    slopes, potentials = _layer_data(inst)
    value = Fraction(inst["base_potential"], potentials[0] + slopes[0] * inst["edge_rank_map"]["modulus"])
    return [value.numerator, value.denominator]


def _linear_ansatz_guess(inst: dict) -> list[int]:
    layers = inst["layer_map"]["modulus"]
    c0, c1, _ = inst["slope_coefficients"]
    slope_sum = layers * c0 + c1 * layers * (layers - 1) // 2
    value = Fraction(
        inst["base_potential"],
        inst["base_potential"] + inst["edge_rank_map"]["modulus"] * slope_sum,
    )
    return [value.numerator, value.denominator]


def _constant_slope_guess(inst: dict) -> list[int]:
    slopes, _ = _layer_data(inst)
    layers = len(slopes)
    denominator = (
        inst["base_potential"]
        + inst["edge_rank_map"]["modulus"] * layers * slopes[0]
    )
    value = Fraction(inst["base_potential"], denominator)
    return [value.numerator, value.denominator]


def _random_restarts(inst: dict, seed: int, attempts: int) -> tuple[bool, int]:
    rng = random.Random(seed)
    for trial in range(1, attempts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, trial
    return False, attempts


def _relabel_instance(inst: dict, mapping: dict[int, int], reverse_input: bool) -> dict:
    out = {
        "n": inst["n"],
        "vertices": [mapping[x] for x in inst["vertices"]],
        "rank_order": [mapping[x] for x in inst["rank_order"]],
        "edge_rank_map": dict(inst["edge_rank_map"]),
        "layer_map": dict(inst["layer_map"]),
        "slope_coefficients": list(inst["slope_coefficients"]),
        "base_potential": inst["base_potential"],
        "max_denominator": inst["max_denominator"],
        "answer": list(inst["answer"]),
    }
    if reverse_input:
        out["vertices"].reverse()
    return out


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(x) for x in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(x) for x in value)
    return 1


def selftest() -> dict:
    report = {}

    g1_total = 0
    g1_good = 0
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            g1_total += 1
            g1_good += int(verify(inst, inst["answer"])[0])
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": g1_good == g1_total and json_native,
        "verified": g1_good,
        "attempts": g1_total,
        "answers_json_native": json_native,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    p, q = shipping["answer"]
    corruptions = {
        "drop_one": [p],
        "swap": [q, p],
        "duplicate": [p, q, q],
        "empty": [],
        "out_of_range": [p, shipping["max_denominator"] + 1],
    }
    reasons = {name: verify(shipping, value)[1] for name, value in corruptions.items()}
    rejected = sum(not verify(shipping, value)[0] for value in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": rejected == len(corruptions) and len(set(reasons.values())) == len(corruptions),
        "rejected": rejected,
        "attempts": len(corruptions),
        "reasons": reasons,
    }

    realistic = (
        "I used exact products rather than decimals.\n```text\n"
        f"<answer>{p}/{q}</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    malformed = (parse_answer("no exact fraction here") is None and parse_answer("<answer>oops</answer>") is None)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and malformed,
        "parsed": parsed,
        "malformed_returns_none": malformed,
    }

    guess_rng = random.Random(13106780)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_probability": guess_hits / guess_total,
        "structure_aware": True,
    }

    reduced_denominator = shipping["answer"][1]
    exact_valid = shipping["max_denominator"] // reduced_denominator
    exact_density = exact_valid / search_space(shipping)
    t0 = time.perf_counter()
    restart_hit, restart_iterations = _random_restarts(shipping, 7001, 4096)
    baseline_wall = time.perf_counter() - t0
    report["G5_density_and_baseline"] = {
        "pass": exact_density < 1e-6 and not restart_hit,
        "shipping_candidate_count": search_space(shipping),
        "shipping_exact_valid_answer_count": exact_valid,
        "shipping_exact_solution_density": exact_density,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "baseline_random_restart_iterations": restart_iterations,
        "baseline_random_restart_wall_sec": round(baseline_wall, 6),
    }

    attack_names = (
        "outlier_near_one_probability",
        "greedy_first_layer_only",
        "random_restart_256",
        "by_hand_linear_ansatz",
        "by_hand_constant_slope_ansatz",
    )
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    for seed in range(8):
        inst = make_instance(seed=80_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_near_one_probability": [
                inst["max_denominator"] - 1,
                inst["max_denominator"],
            ],
            "greedy_first_layer_only": _one_layer_guess(inst),
            "by_hand_linear_ansatz": _linear_ansatz_guess(inst),
            "by_hand_constant_slope_ansatz": _constant_slope_guess(inst),
        }
        for name, candidate in candidates.items():
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
        random_hit, _ = _random_restarts(inst, 90_000 + seed, 256)
        attack_results["random_restart_256"]["successes"] += int(random_hit)

        start = time.perf_counter()
        reference_answer, operations = _reference_direct_product(inst)
        reference_wall += time.perf_counter() - start
        reference_operations += operations
        reference_successes += int(verify(inst, reference_answer)[0])
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Observation 1 exact endpoint cancellation",
            "complexity": "O(L*n^2) expected-time exact integer hash cancellation",
            "wall_clock_sec_total": round(reference_wall, 6),
            "wall_clock_sec_mean": round(reference_wall / 8, 6),
            "operations_total": reference_operations,
            "operations_mean": reference_operations // 8,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] = 2 * doubled_params["n"] + 1
    doubled = make_instance(seed=111, **doubled_params)
    escalated = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    shipping_cost = shipping["edge_rank_map"]["modulus"] * shipping["layer_map"]["modulus"]
    doubled_cost = doubled["edge_rank_map"]["modulus"] * doubled["layer_map"]["modulus"]
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0]
        and doubled_cost > shipping_cost
        and isinstance(escalated, dict)
        and escalated["layers"] > DIFFICULTY[SHIPPING_DIFFICULTY]["layers"],
        "shipping_factor_count": shipping_cost,
        "size_doubled_factor_count": doubled_cost,
        "size_doubled_verifies": verify(doubled, doubled["answer"])[0],
        "escalate_moves": ["n", "layers", "coefficient_span"],
    }

    invariant_checks = 0
    invariant_good = 0
    carried_checks = 0
    carried_good = 0
    unrelated_keys = []
    key_params = DIFFICULTY["easy"]
    for seed in range(20):
        inst = make_instance(seed=120_000 + seed, **key_params)
        original_key = canonical_key(inst)
        unrelated_keys.append(original_key)
        rng = random.Random(130_000 + seed)
        permuted_labels = list(range(inst["n"]))
        rng.shuffle(permuted_labels)
        mapping = {old: new for old, new in enumerate(permuted_labels)}
        variants = (
            _relabel_instance(inst, mapping, False),
            _relabel_instance(inst, {i: i for i in range(inst["n"])}, True),
            _relabel_instance(inst, mapping, True),
        )
        for variant in variants:
            invariant_checks += 1
            invariant_good += int(canonical_key(variant) == original_key)
            carried_checks += 1
            carried_good += int(verify(variant, inst["answer"])[0])
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_good == invariant_checks
        and carried_good == carried_checks
        and distinct == 20,
        "invariance_passed": invariant_good,
        "invariance_attempts": invariant_checks,
        "carried_witness_passed": carried_good,
        "carried_witness_attempts": carried_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": ["vertex relabelling", "input reordering", "composition"],
    }

    worst_chars = 0
    worst_tokens = 0
    worst_elements = 0
    for seed in range(20):
        inst = make_instance(seed=140_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        serial = json.dumps(inst["answer"], separators=(",", ":"))
        worst_chars = max(worst_chars, len(serial))
        worst_tokens = max(worst_tokens, (len(serial) + 3) // 4)
        worst_elements = max(worst_elements, _answer_atoms(inst["answer"]))
    report["G9_no_tool_suitability"] = {
        "pass": worst_chars <= 2000 and worst_elements <= 256 and 19 <= 300,
        "arms": {
            "bare": dict(G9_MEASUREMENTS["bare"]),
            "hinted": dict(G9_MEASUREMENTS["hinted"]),
            "placebo": dict(G9_MEASUREMENTS["placebo"]),
        },
        "hinted_minus_placebo": (
            G9_MEASUREMENTS["hinted"]["solved"]
            / max(1, G9_MEASUREMENTS["hinted"]["attempts"])
            - G9_MEASUREMENTS["placebo"]["solved"]
            / max(1, G9_MEASUREMENTS["placebo"]["attempts"])
        ),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "placebo_verdict": G9_MEASUREMENTS["placebo_verdict"],
        "answer_chars": worst_chars,
        "answer_tokens": worst_tokens,
        "answer_elements": worst_elements,
        "intended_route_operations": 19,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
