"""Verified generator for monochromatic Schur-like equation witnesses.

The native object is a finite colouring of an initial interval of the positive
integers, as in Theorem 4 of arXiv:2507.21656.  The interval is represented by
an exact formula rather than materialised: its endpoint has exponentially many
bits relative to the compact instance description.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite colouring of an integer interval",
        "2-adic valuations",
        "projective line over a prime field",
        "monochromatic additive-equation witnesses",
    ],
    "verification_operations": [
        "exact integer exponentiation",
        "exact 2-adic valuation",
        "modular inverse",
        "projective matrix action",
        "integer identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Conjugate reciprocal pairs on a projective line through the displayed "
        "Möbius map; without that change of variables one must scan all valuation "
        "levels and bucket their colours."
    ),
    "hardness_basis": (
        "Track B: bucket-scanning every valuation level solves the compressed "
        "instance in O(p log p) exact arithmetic; at the hard preset the measured "
        "reference cost is filled by selftest (about 50,000 levels and over one "
        "million modular arithmetic steps), whereas conjugating the reciprocal "
        "involution gives a sub-300-operation route that still requires discovering "
        "and executing projective modular arithmetic without tools."
    ),
    "max_answer_tokens": 40,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 17, "witness_count": 2},
    "easy": {"n": 5003, "witness_count": 8},
    "medium": {"n": 20011, "witness_count": 10},
    "hard": {"n": 50021, "witness_count": 12},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Conjugate reciprocal pairing through the displayed Möbius map instead of "
    "scanning the valuation levels."
)
PLACEBO_HINT = (
    "Keep the modular conventions and the required ordering in view while "
    "assembling the requested pairs."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A lexicographically increasing JSON list of exactly k pairs [u,v], "
        "where 0 <= u < v <= p, no valuation level occurs twice, and each pair "
        "symbolically denotes the five displayed integers."
    ),
    "bounds": {
        "pairs_parameter": "witness_count",
        "level_min": 0,
        "level_max_parameter": "p",
        "pair_order": "strictly increasing endpoints",
        "list_order": "lexicographic",
        "repeated_levels": 0,
        "max_pairs": 24,
    },
}

NOTES = r"""
Definition and exact conventions: Section 1 defines S_2(n) using n-colourings
of [N] with no monochromatic solution of x1+x2+x3=y1+y2.  Repetitions are
allowed: Section 3, Lemma 5 explicitly creates longer solutions by repeating
variables.  This module therefore uses the paper's native colouring and
equation, and its symbolic pair certificate expands to five positive integers
with the repetitions shown in render().

Easy regimes and Step-0 decision: Section 1 explicitly notes a geometric
interval colouring with ratio 1.5 that avoids the equation; generating such a
colouring would be an easy direct construction, not a hard witness problem.
Theorem 4 is an extremal upper bound N=O(sqrt(n!)), not a computational
hardness theorem, and its hidden constant cannot certify a concrete threshold.
For a fixed five-variable equation, a materialised colouring can also be
searched in polynomial time by pair/triple-sum bucketing.  Consequently this
module makes no Track-A claim.  Its exact compressed representation has p+1
valuation levels; the reference algorithm evaluates and buckets all of them in
O(p log p) exact arithmetic and is reported as successful, as Track B requires.

Construction: write P^1(F_p) as 0,...,p-1 plus p for infinity.  A random
invertible matrix M sends valuation levels to projective values T.  The colour
is an affine relabelling of T+T^{-1}, with {0,infinity} one special colour.
Thus T and T^{-1} always have equal colours.  Conjugating inversion by M gives
an explicit involution J=M^{-1}RM on valuation levels.  For every non-fixed
orbit u<v, the identity
  2^u + (2^v-2^u) + 2^v = 2^v + 2^v
is monochromatic because the five terms have valuations u,u,v,v,v.  The
generator samples distinct J-orbits and carries this identity certificate; it
does not solve the generated instance.  There are (p-1)/2 interchangeable
valid orbits, so there is no planted-element population.

Adversaries: endpoint outliers, adjacent greedy pairs, 256 random matchings,
and the tempting affine-reflection ansatz are tested over eight seeds and must
all fail.  The matrix sampler excludes affine J only to keep that explicitly
tested by-hand shortcut from becoming exact.  The successful full bucket scan
is disclosed separately as the Track-B reference algorithm.

Canonicalization: the monochromatic equivalence relation depends only on the
projective involution J, not on a scalar representative for M or on names of
the colours.  canonical_key stores a normalized projective matrix for J.
selftest checks scalar matrix changes, reciprocal row swaps, affine colour
renamings, and general post-composition by a matrix commuting with inversion;
each transformed instance retains the original witness and the same key.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_prime(x: int) -> bool:
    if x < 2:
        return False
    if x % 2 == 0:
        return x == 2
    f = 3
    while f * f <= x:
        if x % f == 0:
            return False
        f += 2
    return True


def _next_prime(x: int) -> int:
    q = max(3, x | 1)
    while not _is_prime(q):
        q += 2
    return q


def _inv_mod(a: int, p: int) -> tuple[int, int]:
    """Return a^-1 mod p and the number of Euclidean division steps."""
    a %= p
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    old_r, r = p, a
    old_t, t = 0, 1
    steps = 0
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_t, t = t, old_t - q * t
        steps += 1
    if old_r != 1:
        raise ZeroDivisionError("element is not invertible")
    return old_t % p, steps


def _mat_mul(a: list[int], b: list[int], p: int) -> list[int]:
    return [
        (a[0] * b[0] + a[1] * b[2]) % p,
        (a[0] * b[1] + a[1] * b[3]) % p,
        (a[2] * b[0] + a[3] * b[2]) % p,
        (a[2] * b[1] + a[3] * b[3]) % p,
    ]


def _involution_matrix(matrix: list[int], p: int) -> list[int]:
    a, b, c, d = matrix
    inverse_without_scalar = [d, -b % p, -c % p, a]
    reciprocal_after_m = [c, d, a, b]
    return _mat_mul(inverse_without_scalar, reciprocal_after_m, p)


def _projective_apply(
    matrix: list[int], point: int, p: int
) -> tuple[int, int]:
    """Apply PGL(2,p); encode infinity by p.  Return value and op count."""
    a, b, c, d = matrix
    if point == p:
        numerator, denominator = a % p, c % p
        base_ops = 0
    else:
        numerator = (a * point + b) % p
        denominator = (c * point + d) % p
        base_ops = 4
    if denominator == 0:
        return p, base_ops + 1
    inverse, steps = _inv_mod(denominator, p)
    return (numerator * inverse) % p, base_ops + steps + 2


def _colour_level(inst: dict, level: int) -> tuple[int, int]:
    p = inst["prime"]
    t, operations = _projective_apply(inst["matrix"], level, p)
    if t == 0 or t == p:
        return p, operations + 1
    inverse, steps = _inv_mod(t, p)
    value = (inst["colour_scale"] * ((t + inverse) % p)
             + inst["colour_shift"]) % p
    return value, operations + steps + 4


def _v2(x: int) -> int:
    if x <= 0:
        raise ValueError("2-adic valuation is defined here only for positives")
    return (x & -x).bit_length() - 1


def _normalise_projective_matrix(matrix: list[int], p: int) -> tuple[int, ...]:
    reduced = [x % p for x in matrix]
    pivot = next((x for x in reduced if x), None)
    if pivot is None:
        raise ValueError("zero matrix has no projective normalization")
    inverse, _ = _inv_mod(pivot, p)
    return tuple((x * inverse) % p for x in reduced)


def _draw_matrix(rng: random.Random, p: int) -> list[int]:
    """Draw M with a genuinely non-affine conjugated involution."""
    while True:
        matrix = [rng.randrange(1, p) for _ in range(4)]
        a, b, c, d = matrix
        if (a * d - b * c) % p == 0:
            continue
        j = _involution_matrix(matrix, p)
        if j[2] % p == 0:  # affine J would validate the obvious reflection ansatz
            continue
        return matrix


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Construct reciprocal-orbit certificates without solving the instance."""
    if type(n) is not int or not (17 <= n <= 400_000):
        raise ValueError("n must be an integer in [17, 400000]")
    witness_count = params.pop("witness_count", max(2, min(12, n // 4000 + 2)))
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if type(witness_count) is not int or not (2 <= witness_count <= 24):
        raise ValueError("witness_count must be an integer in [2,24]")

    p = _next_prime(n)
    if 2 * witness_count + 2 > p + 1:
        raise ValueError("prime is too small for the requested disjoint witnesses")
    rng = random.Random(seed)
    matrix = _draw_matrix(rng, p)
    colour_scale = rng.randrange(1, p)
    colour_shift = rng.randrange(p)
    j = _involution_matrix(matrix, p)

    # Every non-fixed J-orbit is a certified solution support.  Sampling an orbit
    # is direct evaluation of the construction's involution, not instance search.
    pairs: set[tuple[int, int]] = set()
    while len(pairs) < witness_count:
        u = rng.randrange(p + 1)
        v, _ = _projective_apply(j, u, p)
        if u == v:
            continue
        pairs.add((min(u, v), max(u, v)))

    return {
        "prime": p,
        "interval_exponent": p + 1,
        "matrix": matrix,
        "colour_scale": colour_scale,
        "colour_shift": colour_shift,
        "witness_count": witness_count,
        "answer": [list(pair) for pair in sorted(pairs)],
    }


def render(inst: dict) -> str:
    """Render the complete native colouring problem and exact output grammar."""
    p = inst["prime"]
    a, b, c, d = inst["matrix"]
    k = inst["witness_count"]
    statement = f"""MONOCHROMATIC SOLUTIONS TO A SCHUR-LIKE EQUATION

Let p = {p}, which is prime.  The formal projective line P^1(F_p) consists of
the residues 0,1,...,{p - 1} together with INF.  In the output only, encode INF
by the integer {p}.

The positive integers z in the inclusive interval
    1 <= z <= 2^{p + 1}-1
are coloured by the following exact rule.  Let v2(z) be the largest e such that
2^e divides z; thus 0 <= v2(z) <= {p}.  Regard a finite level e as the column
(e,1), and regard level {p} as the projective point INF with column (1,0).
Multiply the column modulo p by

    M = [[{a}, {b}],
         [{c}, {d}]].

If the resulting column is (X,Y), put T=INF when Y=0, and otherwise put
T = X * Y^(-1) mod p.  Here every inverse is the unique multiplicative inverse
modulo p.  The colour of z is SPECIAL when T is 0 or INF.  Otherwise its colour
is the residue

    ({inst['colour_scale']} * (T + T^(-1)) + {inst['colour_shift']}) mod p.

Find exactly {k} pairwise support-disjoint monochromatic solutions of

    x1 + x2 + x3 = y1 + y2.

Use this bounded exact symbolic certificate.  A pair [u,v] denotes, in order,

    (x1,x2,x3,y1,y2) = (2^u, 2^v-2^u, 2^v, 2^v, 2^v).

You must give exactly {k} pairs.  In each pair 0 <= u < v <= {p}; no level may
occur in two pairs.  Sort the list of pairs lexicographically.  Repeated integer
values inside one decoded five-tuple are allowed (as in the paper's definition),
but repeated valuation levels across different pairs are not.

Give your final answer inside <answer></answer> tags, as one JSON list of pairs.
Example: <answer>[[0, 3], [1, 5]]</answer>
The example shows syntax only and has two pairs; supply exactly {k} pairs for
this instance.  Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON list of integer pairs without raising."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
        if fence:
            body = fence.group(1).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if (isinstance(value, list)
                and all(isinstance(pair, list) and len(pair) == 2
                        and all(type(x) is int for x in pair) for pair in value)):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Inspect only the public instance and candidate; never consult answer."""
    if not isinstance(answer, list):
        return False, "answer is not a JSON list"
    if not answer:
        return False, "answer is empty"
    k = inst["witness_count"]
    if len(answer) != k:
        return False, f"expected exactly {k} pairs, got {len(answer)}"
    if any(not isinstance(pair, list) or len(pair) != 2 for pair in answer):
        return False, "an entry is not a two-element JSON list"
    if any(any(type(x) is not int for x in pair) for pair in answer):
        return False, "a level is not an integer"
    if any(pair[0] >= pair[1] for pair in answer):
        return False, "pair endpoints must be strictly increasing"
    p = inst["prime"]
    if any(x < 0 or x > p for pair in answer for x in pair):
        return False, f"a level is outside the inclusive range 0..{p}"
    if answer != sorted(answer) or len({tuple(pair) for pair in answer}) != len(answer):
        return False, "pairs must be distinct and lexicographically increasing"
    flat = [x for pair in answer for x in pair]
    if len(set(flat)) != len(flat):
        return False, "a valuation level is reused across pairs"

    for pair_index, (u, v) in enumerate(answer):
        # Expand the certificate and check the equation and claimed valuations
        # with exact integers.  These integers have only O(p) bits.
        two_u = 1 << u
        two_v = 1 << v
        values = [two_u, two_v - two_u, two_v, two_v, two_v]
        if values[0] + values[1] + values[2] != values[3] + values[4]:
            return False, f"pair {pair_index} does not satisfy the additive identity"
        levels = [_v2(x) for x in values]
        if levels != [u, u, v, v, v]:
            return False, f"pair {pair_index} has incorrect decoded valuations"
        colour_u, _ = _colour_level(inst, u)
        colour_v, _ = _colour_level(inst, v)
        if colour_u != colour_v:
            return False, f"pair {pair_index} has two different colours"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-aware space of k disjoint matchings."""
    k = inst["witness_count"]
    levels = rng.sample(range(inst["prime"] + 1), 2 * k)
    pairs = [sorted(levels[2 * i:2 * i + 2]) for i in range(k)]
    return sorted(pairs)


def search_space(inst: dict) -> int | None:
    """Number of k-edge matchings on the p+1 labelled valuation levels."""
    level_count = inst["prime"] + 1
    k = inst["witness_count"]
    return math.factorial(level_count) // (
        math.factorial(level_count - 2 * k) * (2 ** k) * math.factorial(k)
    )


def enumerate_all(inst: dict) -> int | None:
    """Exact valid-certificate count from the reciprocal-orbit decomposition."""
    orbit_count = (inst["prime"] - 1) // 2
    return math.comb(orbit_count, inst["witness_count"])


def canonical_key(inst: dict) -> str:
    """Canonicalize the exact monochromatic orbit relation, not the seed."""
    p = inst["prime"]
    j = _normalise_projective_matrix(_involution_matrix(inst["matrix"], p), p)
    payload = json.dumps(
        {"prime": p, "witness_count": inst["witness_count"], "involution": j},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Double the scan range while keeping the compact answer within G9 caps."""
    n = params.get("n")
    k = params.get("witness_count")
    if type(n) is not int or type(k) is not int or n >= 200_000:
        return None
    return {"n": n * 2 + 1, "witness_count": k}


def _reference_algorithm(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Evaluate every level and bucket equal colours: O(p log p)."""
    buckets: dict[int, list[int]] = {}
    operations = 0
    for level in range(inst["prime"] + 1):
        colour, cost = _colour_level(inst, level)
        operations += cost
        buckets.setdefault(colour, []).append(level)
    pairs = [values for values in buckets.values() if len(values) == 2]
    pairs = sorted(sorted(pair) for pair in pairs)
    if len(pairs) < inst["witness_count"]:
        return None, operations
    return pairs[:inst["witness_count"]], operations


def _attack_outlier_endpoints(inst: dict) -> list[list[int]]:
    p = inst["prime"]
    k = inst["witness_count"]
    return [[i, p - i] for i in range(k)]


def _attack_greedy_adjacent(inst: dict) -> list[list[int]]:
    return [[2 * i, 2 * i + 1] for i in range(inst["witness_count"])]


def _attack_affine_reflection(inst: dict) -> list[list[int]]:
    """Pretend the Möbius denominator is constant and pair about a center."""
    p = inst["prime"]
    a, b, _c, _d = inst["matrix"]
    inverse_a, _ = _inv_mod(a, p)
    center_twice = (-2 * b * inverse_a) % p
    used: set[int] = set()
    pairs: list[list[int]] = []
    for u in range(p):
        v = (center_twice - u) % p
        if u == v or u in used or v in used:
            continue
        pair = [min(u, v), max(u, v)]
        used.update(pair)
        pairs.append(pair)
        if len(pairs) == inst["witness_count"]:
            return sorted(pairs)
    return sorted(pairs)


def _compact_route_answer_and_cost(inst: dict) -> tuple[list[list[int]], int]:
    """Conjugate inversion once, then take the first non-fixed J-orbits."""
    p = inst["prime"]
    j = _involution_matrix(inst["matrix"], p)
    operations = 24  # two exact 2x2 modular matrix products/conjugation
    used: set[int] = set()
    pairs: list[list[int]] = []
    for u in range(p + 1):
        if u in used:
            continue
        v, cost = _projective_apply(j, u, p)
        operations += cost
        if u == v:
            continue
        pair = [min(u, v), max(u, v)]
        used.update(pair)
        pairs.append(pair)
        if len(pairs) == inst["witness_count"]:
            break
    return sorted(pairs), operations


def _scaled_instance(inst: dict, scalar: int) -> dict:
    p = inst["prime"]
    transformed = dict(inst)
    transformed["matrix"] = [(scalar * x) % p for x in inst["matrix"]]
    transformed.pop("answer", None)
    return transformed


def _commuting_transform_instance(inst: dict, u: int, v: int) -> dict:
    p = inst["prime"]
    # [[u,v],[v,u]] commutes with reciprocal R; determinant u^2-v^2 != 0.
    transform = [u % p, v % p, v % p, u % p]
    transformed = dict(inst)
    transformed["matrix"] = _mat_mul(transform, inst["matrix"], p)
    transformed["colour_scale"] = (inst["colour_scale"] * 3) % p or 1
    transformed["colour_shift"] = (inst["colour_shift"] + 7) % p
    transformed.pop("answer", None)
    return transformed


# The bare hardening run was terminally too easy, so the G9 arms were correctly
# not run.  Keep the attempted module executable, but make selftest fail G9
# rather than recording fictional post-rejection measurements.
G9_AUDIT = {
    "arms": {
        "bare": {"solved": 6, "attempts": 12},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run_bare_was_too_easy",
}


def selftest() -> dict:
    """Run all G1--G9 gates and return a fully measured JSON-native report."""
    report: dict[str, Any] = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: all named presets, several independent seeds.
    g1_attempts = 0
    g1_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=101, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions: dict[str, object] = {
        "drop_one": planted[:-1],
        "swap_endpoint_order": [[planted[0][1], planted[0][0]]] + planted[1:],
        "duplicate_pair": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": planted[:-1] + [[planted[-1][0], shipping["prime"] + 1]],
    }
    g2_reasons: dict[str, str] = {}
    g2_all_rejected = True
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        g2_all_rejected &= not ok
        g2_reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": g2_all_rejected and len(set(g2_reasons.values())) == len(g2_reasons),
        "rejected": sum(1 for reason in g2_reasons.values() if reason != "ok"),
        "distinct_reasons": len(set(g2_reasons.values())),
        "reasons": g2_reasons,
    }

    response = (
        "I used the projective involution.\n```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThese pairs are disjoint."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    t_guess = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(shipping, rng)
        if verify(shipping, candidate)[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - t_guess
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_hits / guess_total,
        "candidate_prior": "uniform k-edge matching on all p+1 valuation levels",
        "elapsed_sec": round(guess_elapsed, 6),
    }

    t_reference = time.perf_counter()
    reference_answer, reference_operations = _reference_algorithm(shipping)
    reference_wall = time.perf_counter() - t_reference
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    valid_count = enumerate_all(shipping)
    candidate_count = search_space(shipping)
    assert valid_count is not None and candidate_count is not None
    exact_fraction = valid_count / candidate_count
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and 0.0 < exact_fraction < 1e-6,
        "shipping_valid_answer_count": valid_count,
        "shipping_candidate_count": candidate_count,
        "shipping_exact_solution_fraction": exact_fraction,
        "baseline_wall_clock_sec": round(reference_wall, 6),
        "baseline_operation_count": reference_operations,
        "baseline_levels_scanned": shipping["prime"] + 1,
    }

    attack_names = [
        "outlier_endpoint_pairing",
        "greedy_adjacent_levels",
        "random_restart_256_matchings",
        "in_context_affine_reflection_ansatz",
    ]
    attack_successes = {name: 0 for name in attack_names}
    attack_attempts = 8
    reference_successes = 0
    reference_ops_total = 0
    reference_wall_total = 0.0
    for seed in range(200, 200 + attack_attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates: dict[str, object | None] = {
            "outlier_endpoint_pairing": _attack_outlier_endpoints(inst),
            "greedy_adjacent_levels": _attack_greedy_adjacent(inst),
            "in_context_affine_reflection_ansatz": _attack_affine_reflection(inst),
        }
        rr_rng = random.Random(seed ^ 0xA5A5A5A5)
        random_found: object | None = None
        for _ in range(256):
            trial = random_candidate(inst, rr_rng)
            if verify(inst, trial)[0]:
                random_found = trial
                break
        candidates["random_restart_256_matchings"] = random_found
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_successes[name] += 1

        start = time.perf_counter()
        candidate, operations = _reference_algorithm(inst)
        reference_wall_total += time.perf_counter() - start
        reference_ops_total += operations
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1

    attacks = {
        name: {"successes": attack_successes[name], "attempts": attack_attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values())
        and reference_successes == attack_attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "evaluate and bucket every projective valuation level",
            "complexity": "O(p log p) exact arithmetic",
            "wall_clock_sec": round(reference_wall_total / attack_attempts, 6),
            "operations": round(reference_ops_total / attack_attempts),
            "levels": shipping["prime"] + 1,
            "solves": f"{reference_successes}/{attack_attempts}, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=303, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["prime"] > shipping["prime"],
        "shipping_prime": shipping["prime"],
        "doubled_prime": doubled["prime"],
        "doubled_verification": doubled_reason,
    }

    invariance_checks = 0
    preserving_checks = 0
    g8_failures: list[str] = []
    distinct_keys: list[str] = []
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY["easy"])
        key = canonical_key(inst)
        distinct_keys.append(key)
        p = inst["prime"]
        scalar = 2 + seed % (p - 2)
        variants = [_scaled_instance(inst, scalar)]
        # Row swap is post-composition by reciprocal and preserves colours.
        swapped = dict(inst)
        a, b, c, d = inst["matrix"]
        swapped["matrix"] = [c, d, a, b]
        swapped["colour_scale"] = (inst["colour_scale"] * 5) % p or 1
        swapped["colour_shift"] = (inst["colour_shift"] + 11) % p
        swapped.pop("answer", None)
        variants.append(swapped)
        u, v = 3, 1
        if (u * u - v * v) % p == 0:
            u = 4
        variants.append(_commuting_transform_instance(inst, u, v))
        composed = _scaled_instance(variants[-1], scalar)
        variants.append(composed)
        for index, variant in enumerate(variants):
            invariance_checks += 1
            if canonical_key(variant) != key:
                g8_failures.append(f"seed {seed} variant {index}: key changed")
            preserving_checks += 1
            ok, reason = verify(variant, inst["answer"])
            if not ok:
                g8_failures.append(f"seed {seed} variant {index}: {reason}")
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "preserving_witness_checks": preserving_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": 20,
        "failures": g8_failures,
    }

    compact_answer, compact_operations = _compact_route_answer_and_cost(shipping)
    compact_ok = verify(shipping, compact_answer)[0]
    answer_text = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_text)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = 2 * len(shipping["answer"])
    arms = G9_AUDIT["arms"]
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256
        and compact_operations <= 300 and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_AUDIT["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_AUDIT["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "compact_route_verifies": compact_ok,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
