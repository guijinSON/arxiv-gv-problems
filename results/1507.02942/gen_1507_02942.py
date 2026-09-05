"""Verified problem generator for arXiv:1507.02942.

The generated task is native Nottingham-group power-series arithmetic.  It asks
for exact high iterates of normalized formal power series over a prime field.
Corollary 3.4 of the paper supplies a certified iterate for t+t^2+lambda*t^3;
the generator transports it through invertible scalings of the formal variable.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


# Keep the repository helpers importable when this file is run from its result
# directory.  This family uses only prime-field arithmetic and therefore remains
# standard-library-only if gvlib is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - documented dependency-free fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "truncated normalized formal power series over F_p",
        "composition iterates in a finite Nottingham-group quotient",
        "sparse output polynomials over F_p",
    ],
    "verification_operations": [
        "exact finite-field inversion and exponentiation",
        "exact scaling-conjugacy coefficient transport",
        "canonical sparse-polynomial comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Scaling the formal parameter normalizes the quadratic coefficient, so "
        "Corollary 3.4 replaces a huge composition iterate by two coefficient "
        "powers; without that conjugacy one must carry out truncated composition."
    ),
    "hardness_basis": (
        "Track B: direct coefficient-array iteration of r series costs "
        "O(r*p^m*z_m^2) exact field operations; at the hard preset the measured "
        "reference implementation executes about 26.43 million modular operations "
        "in about 2.10 seconds per instance on the final recorded run, whereas the "
        "scaling-conjugacy/Corollary 3.4 algorithm is logarithmic in the displayed "
        "exponents and uses 136 exact operations but must be recognized and "
        "executed without a CAS."
    ),
    "max_answer_tokens": 209,
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


# n is a lower bound for the prime p; p is the first prime at least n.  Thus
# doubling n grows both the iterate p^m and its truncation degree while the
# number of output polynomials stays fixed.
DIFFICULTY = {
    "demo": {"n": 5, "m": 1, "batch": 1},
    "easy": {"n": 7, "m": 1, "batch": 4},
    "medium": {"n": 7, "m": 2, "batch": 6},
    "hard": {"n": 11, "m": 2, "batch": 8},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered list of eight canonical sparse polynomials over F_11 at the "
        "shipping preset.  Each has exactly the fixed support {1,z_m,z_m+1}, "
        "linear coefficient 1, and two independently chosen nonzero field "
        "coefficients; other presets use their displayed p and batch size."
    ),
    "bounds": {
        "polynomials": 8,
        "terms_per_polynomial": 3,
        "variables": 1,
        "field_order": 11,
        "free_nonzero_coefficients_per_polynomial": 2,
    },
}

STRUCTURAL_HINT = (
    "Scaling the formal parameter conjugates every series with nonzero quadratic "
    "coefficient to one whose quadratic coefficient is 1."
)
PLACEBO_HINT = (
    "Careful organization of the modular coefficients keeps every requested "
    "truncation degree aligned with its corresponding input series."
)


# Filled after the separately preserved harden.py runs.  These arms are
# diagnostics only; G9.pass is determined solely by the answer/effort caps.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


NOTES = """\
The introduction fixes the exact Beauville definition through the conjugacy-power
sets Sigma(x,y).  Theorem 2.5 is the decisive easy-case result for the prior
triage idea: in the semi-p^(e-1)-abelian or potent regime, every lift of a
Beauville structure from G/Phi(G) works.  Theorem 3.7 is even more explicit for
the Nottingham quotients when p>=5, exhibiting {u,v} and {uv^2,uv^4}.  Thus a
generator asking merely for Beauville pairs would have abundant witnesses and a
short standard construction; it cannot support Track A and has too little
guess resistance for a useful Track B task.

The retained native problem is the power computation used to prove those
Beauville results.  Lemma 3.2 gives the mechanical coefficient-array method,
Lemma 3.3 analyzes the distinguished-diamond power map, and Corollary 3.4 gives
the p^m-th iterate of f_lambda=t+t^2+lambda*t^3.  Each generated series is an
exact scaling conjugate of an f_lambda, so its certificate is transported by a
structure-preserving change of variable rather than found by solving.

Inputs exclude zero normalized lambda, lambda=1, and scale u=1.  This keeps the
two requested coefficients nonzero and prevents the unscaled and m=1 ansatzes
from being silently correct.  Random u,v pairs otherwise come from one common
distribution.  The adversary panel tests constant residues, copied input
coefficients, the normalized deficit alone, the paper formula with scaling
ignored, the m=1 formula, and 256 random restarts.  Exact direct composition is
reported separately because it is the expected-success Track-B reference.
"""


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(lower: int) -> int:
    candidate = max(5, int(lower))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _z_value(p: int, m: int) -> int:
    return 2 + sum(p ** power for power in range(1, m + 1))


def _inverse(value: int, p: int) -> int:
    value %= p
    if value == 0:
        raise ValueError("zero has no inverse in F_p")
    return pow(value, p - 2, p)


def _expected_coefficients(p: int, m: int, z: int,
                           u: int, v: int) -> tuple[int, int]:
    """Transport Corollary 3.4 through t -> u*t scaling conjugacy."""
    normalized_lambda = v * _inverse(u * u, p) % p
    deficit = (1 - normalized_lambda) % p
    a = pow(u, z - 1, p) * pow(deficit, m, p) % p
    b = -pow(u, z, p) * pow(deficit, m + 1, p) % p
    return a, b


def _polynomial(z: int, a: int, b: int) -> list[list[object]]:
    """Canonical JSON polynomial [[coefficient,[exponent]], ...]."""
    return [[1, [1]], [a, [z]], [b, [z + 1]]]


def make_instance(n, seed=0, **params) -> dict:
    """Construct certified high iterates by a structure-preserving scaling.

    The first prime p>=n determines the field and the p^m-fold composition
    count.  The certificate is obtained directly from Corollary 3.4 and carried
    through a randomly sampled nonzero scale; no iterate is solved during
    generation.
    """
    n = int(n)
    m = int(params.get("m", 2))
    batch = int(params.get("batch", 8))
    if n < 5:
        raise ValueError("n must be at least 5")
    if m < 1 or m > 8:
        raise ValueError("m must lie between 1 and 8")
    p = _next_prime(n)
    available = (p - 2) * (p - 2)
    if batch < 1 or batch > min(64, available):
        raise ValueError("batch must be positive, at most 64, and fit the field")

    rng = random.Random(seed)
    # u=1 is excluded so ignoring the coordinate scaling is not a useful probe.
    # v is nonzero and v!=u^2, hence normalized lambda is neither 0 nor 1 and
    # both certified high coefficients are nonzero.
    # Sample without materialising the O(p^2) admissible pair space.  This
    # keeps generation linear in the fixed batch size even after escalation.
    chosen = []
    seen = set()
    while len(chosen) < batch:
        pair = (rng.randrange(2, p), rng.randrange(1, p))
        u, v = pair
        if v == u * u % p or pair in seen:
            continue
        seen.add(pair)
        chosen.append(pair)
    z = _z_value(p, m)
    series = [{"u": u, "v": v} for u, v in chosen]
    answer = [
        _polynomial(z, *_expected_coefficients(p, m, z, u, v))
        for u, v in chosen
    ]
    return {
        "n": n,
        "p": p,
        "m": m,
        "batch": batch,
        "iterate": p ** m,
        "z": z,
        "modulus_exponent": z + 2,
        "series": series,
        "answer": answer,
    }


def render(inst) -> str:
    p = inst["p"]
    batch = inst["batch"]
    z = inst["z"]
    lines = [
        "Compute exact high composition iterates of truncated formal power series.",
        "",
        f"All coefficients lie in the prime field F_{p}, represented by integers "
        f"0,...,{p - 1} with every operation reduced modulo {p}.",
        "For series h(t) and g(t), h composed with g means substitute g(t) for "
        "every t in h(t), expand, and reduce coefficients modulo p.",
        f"After every composition discard every monomial of degree at least "
        f"{inst['modulus_exponent']}; equivalently, work modulo "
        f"t^{inst['modulus_exponent']}.",
        "The E-fold iterate f^[E] is f composed with itself E times; f^[0](t)=t.",
        "",
        f"Here m={inst['m']}, E=p^m={inst['iterate']}, and",
        f"  z_m = 2 + sum_(j=1)^m p^j = {z}.",
        (
            "There is 1 input, indexed 0:"
            if batch == 1
            else f"There are {batch} inputs, indexed 0 through {batch - 1}, in this order:"
        ),
    ]
    for index, item in enumerate(inst["series"]):
        lines.append(
            f"  {index}: f_{index}(t) = t + {item['u']}*t^2 + "
            f"{item['v']}*t^3"
        )
    lines += [
        "",
        "It is guaranteed that each requested iterate has exactly the form",
        f"  f_i^[E](t) = t + A_i*t^{z} + B_i*t^{z + 1} "
        f"(mod t^{inst['modulus_exponent']}),",
        f"where A_i and B_i are both in 1,...,{p - 1}.",
        "Find all of these output polynomials.  The outer-list order must match "
        "the input order; no input may be omitted or repeated.",
        "",
        "Represent each polynomial canonically as",
        f"  [[1,[1]],[A_i,[{z}]],[B_i,[{z + 1}]]].",
        "Thus a coefficient is an integer residue and a monomial is a "
        "one-entry exponent list.  Terms must appear in increasing exponent order.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON array "
        + ("containing exactly 1 polynomial." if batch == 1
           else f"containing exactly {batch} polynomials."),
        "Example format only: <answer>" + json.dumps(
            [_polynomial(z, 1, 1) for _ in range(batch)],
            separators=(",", ":"),
        ) + "</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>\s*(.*?)\s*</answer>", text,
                        flags=re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    return answer


def verify(inst, answer):
    """Check canonical shape and exact iterate coefficients without the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of polynomials"
    if not answer:
        return False, "answer is empty"
    batch = inst["batch"]
    if len(answer) < batch:
        return False, f"too few polynomials: expected {batch}"
    if len(answer) > batch:
        return False, f"too many polynomials: expected {batch}"

    p, m, z = inst["p"], inst["m"], inst["z"]
    expected_exponents = ([1], [z], [z + 1])
    for index, (poly, item) in enumerate(zip(answer, inst["series"])):
        if not isinstance(poly, list) or len(poly) != 3:
            return False, f"polynomial {index} must contain exactly three terms"
        coefficients = []
        for term_index, term in enumerate(poly):
            if not isinstance(term, list) or len(term) != 2:
                return False, f"term {term_index} of polynomial {index} is malformed"
            coefficient, exponent = term
            if isinstance(coefficient, bool) or not isinstance(coefficient, int):
                return False, f"coefficient in polynomial {index} must be an integer"
            if not 0 <= coefficient < p:
                return False, f"coefficient in polynomial {index} is outside 0..{p - 1}"
            if exponent != list(expected_exponents[term_index]):
                return False, f"polynomial {index} has a wrong or noncanonical exponent"
            coefficients.append(coefficient)
        if coefficients[0] != 1:
            return False, f"polynomial {index} must have linear coefficient 1"
        if coefficients[1] == 0 or coefficients[2] == 0:
            return False, f"polynomial {index} must have two nonzero high coefficients"

        expected_a, expected_b = _expected_coefficients(
            p, m, z, item["u"], item["v"]
        )
        if coefficients[1] != expected_a or coefficients[2] != expected_b:
            return False, f"polynomial {index} does not equal the exact E-fold iterate"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform sample from the promised fixed-support, nonzero language."""
    p, z = inst["p"], inst["z"]
    return [
        _polynomial(z, rng.randrange(1, p), rng.randrange(1, p))
        for _ in range(inst["batch"])
    ]


def search_space(inst):
    return (inst["p"] - 1) ** (2 * inst["batch"])


def enumerate_all(inst):
    """Brute-force the declared language when it has at most 200k members."""
    if search_space(inst) > 200_000:
        return None
    p, z, batch = inst["p"], inst["z"], inst["batch"]
    hits = 0
    for values in itertools.product(range(1, p), repeat=2 * batch):
        candidate = [
            _polynomial(z, values[2 * i], values[2 * i + 1])
            for i in range(batch)
        ]
        hits += int(verify(inst, candidate)[0])
    return hits


def canonical_key(inst):
    """Normalize input order and every formal-parameter scaling.

    For S_c(t)=c*t, S_c^-1 f S_c changes (u,v) to (c*u,c^2*v),
    while lambda=v/u^2 is invariant.  The sorted lambda multiset is the exact
    normal form for the relabellings implemented and tested by this family.
    General Nottingham conjugacy is not classified here (see README caveats).
    """
    p = inst["p"]
    normalized = sorted(
        item["v"] * _inverse(item["u"] * item["u"], p) % p
        for item in inst["series"]
    )
    normal = {
        "p": p,
        "m": inst["m"],
        "normalized_lambda_multiset": normalized,
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Grow two mechanical-cost dials while keeping the witness shape fixed."""
    harder = dict(params)
    harder["n"] = max(5, int(harder.get("n", 11)) * 2)
    harder["m"] = min(8, int(harder.get("m", 2)) + 1)
    # Keep batch fixed: increasing p and m grows the composition count and
    # truncation degree while the answer remains 24 terms at the hard preset.
    return harder


# --- Exact reference computation and adversarial probes for selftest --------

def _poly_mul(left, right, degree: int, p: int, counter: list[int]):
    out = [0] * (degree + 1)
    for i, a in enumerate(left):
        if not a:
            continue
        upper = min(degree - i, len(right) - 1)
        for j in range(1, upper + 1):
            b = right[j]
            if b:
                out[i + j] = (out[i + j] + a * b) % p
                counter[0] += 2  # one multiplication and one addition
    return out


def _direct_one(p: int, iterate: int, degree: int, u: int, v: int,
                counter: list[int]):
    """Mechanically apply f(g)=g+u*g^2+v*g^3, truncating every step."""
    current = [0] * (degree + 1)
    current[1] = 1
    for _ in range(iterate):
        square = _poly_mul(current, current, degree, p, counter)
        cube = _poly_mul(square, current, degree, p, counter)
        current = [
            (current[i] + u * square[i] + v * cube[i]) % p
            for i in range(degree + 1)
        ]
        counter[0] += 4 * (degree + 1)
    return current


def _reference_algorithm(inst):
    start = time.perf_counter()
    counter = [0]
    answer = []
    degree = inst["z"] + 1
    for item in inst["series"]:
        dense = _direct_one(
            inst["p"], inst["iterate"], degree,
            item["u"], item["v"], counter,
        )
        answer.append(_polynomial(inst["z"], dense[inst["z"]],
                                  dense[inst["z"] + 1]))
    return answer, time.perf_counter() - start, counter[0]


def _candidate_from_pairs(inst, pairs):
    return [
        _polynomial(inst["z"], a % inst["p"], b % inst["p"])
        for a, b in pairs
    ]


def _attack_candidates(inst, rng):
    p, m, z = inst["p"], inst["m"], inst["z"]
    uv = [(item["u"], item["v"]) for item in inst["series"]]
    deficit = []
    for u, v in uv:
        lam = v * _inverse(u * u, p) % p
        deficit.append((1 - lam) % p)

    constant = _candidate_from_pairs(inst, [(1, 1) for _ in uv])
    copied = _candidate_from_pairs(inst, uv)
    deficit_only = _candidate_from_pairs(inst, [(d, d) for d in deficit])
    unscaled = _candidate_from_pairs(inst, [
        (pow(d, m, p), -pow(d, m + 1, p)) for d in deficit
    ])
    m_one = _candidate_from_pairs(inst, [
        (pow(u, z - 1, p) * d,
         -pow(u, z, p) * pow(d, 2, p))
        for (u, _), d in zip(uv, deficit)
    ])
    return {
        "per_series_smallest_nonzero": [constant],
        "copy_input_coefficients": [copied],
        "normalized_deficit_ansatz": [deficit_only],
        "ignore_coordinate_scaling": [unscaled],
        "assume_single_p_power": [m_one],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _reordered(inst, rng):
    order = list(range(inst["batch"]))
    rng.shuffle(order)
    out = {key: value for key, value in inst.items()
           if key not in ("series", "answer")}
    out["series"] = [dict(inst["series"][i]) for i in order]
    out["answer"] = [inst["answer"][i] for i in order]
    return out


def _scaled(inst, rng):
    """Apply independent S_c^-1 f S_c changes and carry each polynomial."""
    p, z = inst["p"], inst["z"]
    out = {key: value for key, value in inst.items()
           if key not in ("series", "answer")}
    new_series = []
    new_answer = []
    for item, polynomial in zip(inst["series"], inst["answer"]):
        c = rng.randrange(1, p)
        new_series.append({
            "u": c * item["u"] % p,
            "v": c * c * item["v"] % p,
        })
        a, b = polynomial[1][0], polynomial[2][0]
        new_answer.append(_polynomial(
            z, pow(c, z - 1, p) * a % p, pow(c, z, p) * b % p
        ))
    out["series"] = new_series
    out["answer"] = new_answer
    return out


def _pow_multiplication_count(exponent: int) -> int:
    """Multiplications in ordinary left-to-right binary modular powering."""
    if exponent <= 0:
        return 0
    return exponent.bit_count() + exponent.bit_length() - 1


def _intended_operations(inst) -> int:
    # Per series: u^2; inverse by u^(2(p-2)); lambda multiply; subtraction;
    # deficit^m; one multiply for deficit^(m+1); u^(z-1); one multiply for
    # u^z; and the two final products.  Fermat reduction is used for u powers.
    p, m, z = inst["p"], inst["m"], inst["z"]
    inverse_power = p - 2
    u_power = (z - 1) % (p - 1)
    per_series = (
        1 + _pow_multiplication_count(inverse_power) + 1 + 1
        + _pow_multiplication_count(m) + 1
        + _pow_multiplication_count(u_power) + 1 + 2
    )
    return inst["batch"] * per_series


def _answer_token_measure(answer) -> int:
    # Conservative lexical count: integers and punctuation are all counted.
    blob = json.dumps(answer, separators=(",", ":"))
    return len(re.findall(r"\d+|[\[\],-]", blob))


def _answer_elements(answer) -> int:
    # The mathematical atoms are the three monomial/coefficient terms in every
    # output polynomial, rather than JSON punctuation or exponent-list wrappers.
    return sum(len(polynomial) for polynomial in answer)


def selftest():
    report = {
        "paper": "1507.02942",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all four presets, three independently generated instances each.
    verified = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            verified += int(ok)
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
    report["G1_planted_verifies"] = {
        "pass": verified == 12,
        "verified": verified,
        "attempts": 12,
        "failures": failures,
    }

    # G2: five corruption classes with five distinguishable rejection reasons.
    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = ship["answer"]
    swapped = json.loads(json.dumps(planted))
    swap_index = next(
        (i for i, poly in enumerate(swapped) if poly[1][0] != poly[2][0]),
        None,
    )
    if swap_index is not None:
        swapped[swap_index][1][0], swapped[swap_index][2][0] = (
            swapped[swap_index][2][0], swapped[swap_index][1][0]
        )
    else:
        swapped[0], swapped[1] = swapped[1], swapped[0]
    outside = json.loads(json.dumps(planted))
    outside[0][1][0] = ship["p"]
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": planted + [planted[-1]],
        "empty": [],
        "out_of_range": outside,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({case["reason"] for case in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and distinct_reasons == 5,
        "cases": cases,
        "distinct_reasons": distinct_reasons,
    }

    # G3: model-style prose/fence wrapper plus a JSON-native round trip.
    reply = (
        "Using formal-series conjugacy gives the following.\n```json\n"
        "<answer>" + json.dumps(planted) + "</answer>\n```\n"
    )
    parsed = parse_answer(reply)
    json_native = json.loads(json.dumps(planted)) == planted
    report["G3_round_trip"] = {
        "pass": parsed == planted and json_native,
        "parsed_matches": parsed == planted,
        "json_native": json_native,
    }

    # G4 and shipping-density part of G5 use the same 200k uniform samples from
    # the fully promised fixed-support/nonzero certificate language.
    density_inst = make_instance(seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY])
    density_rng = random.Random(0x150702942)
    samples = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(density_inst,
                           random_candidate(density_inst, density_rng))[0])
    sampling_wall = time.perf_counter() - started
    observed_probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and observed_probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": observed_probability,
        "exact_language_size": search_space(density_inst),
        "exact_valid_fraction": 1 / search_space(density_inst),
        "sampling_wall_sec": round(sampling_wall, 6),
    }

    # G6: Track B keeps the successful domain-standard algorithm separate.
    attempts = 8
    successes = None
    reference_success = 0
    reference_times = []
    reference_operations = []
    for seed in range(20, 20 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        probes = _attack_candidates(inst, random.Random(90_000 + seed))
        if successes is None:
            successes = {name: 0 for name in probes}
        for name, candidates in probes.items():
            if any(verify(inst, candidate)[0] for candidate in candidates):
                successes[name] += 1
        reference, elapsed, operations = _reference_algorithm(inst)
        reference_success += int(verify(inst, reference)[0])
        reference_times.append(elapsed)
        reference_operations.append(operations)
    attacks = {
        name: {"successes": count, "attempts": attempts}
        for name, count in successes.items()
    }
    all_failed = all(value["successes"] == 0 for value in attacks.values())
    mean_reference_time = sum(reference_times) / attempts
    mean_reference_operations = sum(reference_operations) // attempts
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_success == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "direct truncated coefficient-array composition",
            "complexity": "O(batch*p^m*z_m^2) exact field operations",
            "wall_clock_sec": round(mean_reference_time, 6),
            "operations": mean_reference_operations,
            "solves": f"{reference_success}/{attempts}, as expected",
        },
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits == 0
        and reference_success == attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": observed_probability,
        "shipping_exact_valid_fraction": 1 / search_space(density_inst),
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(mean_reference_time, 6),
        "baseline_operation_count": mean_reference_operations,
    }

    # G7: double the size dial, hence the field/truncation/iterate, while keeping
    # the eight-polynomial witness length fixed.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and _answer_elements(doubled["answer"]) == _answer_elements(planted)
        and doubled["iterate"] > ship["iterate"],
        "original_n": ship["n"],
        "doubled_n": doubled["n"],
        "original_prime": ship["p"],
        "doubled_prime": doubled["p"],
        "original_iterate": ship["iterate"],
        "doubled_iterate": doubled["iterate"],
        "answer_elements_before": _answer_elements(planted),
        "answer_elements_after": _answer_elements(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: input reordering, independent variable scalings, and their composition.
    invariance_passed = 0
    invariance_attempted = 0
    transformed_verified = 0
    keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(123_000 + seed)
        reordered = _reordered(inst, rng)
        scaled = _scaled(inst, rng)
        composed = _scaled(_reordered(inst, rng), rng)
        key = canonical_key(inst)
        for changed in (reordered, scaled, composed):
            invariance_attempted += 1
            invariance_passed += int(canonical_key(changed) == key)
        transformed_verified += int(verify(composed, composed["answer"])[0])
        keys.append(key)
    report["G8_canonical_key"] = {
        "pass": invariance_passed == invariance_attempted
        and transformed_verified == 20 and len(set(keys)) == 20,
        "invariance_checks_passed": invariance_passed,
        "invariance_checks_attempted": invariance_attempted,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
    }

    compact_blob = json.dumps(planted, separators=(",", ":"))
    worst_answer = [
        _polynomial(ship["z"], ship["p"] - 1, ship["p"] - 1)
        for _ in range(ship["batch"])
    ]
    worst_blob = json.dumps(worst_answer, separators=(",", ":"))
    answer_tokens = _answer_token_measure(worst_answer)
    answer_elements = _answer_elements(planted)
    intended_operations = _intended_operations(ship)
    arms = G9_RESULTS["arms"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        len(worst_blob) <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(worst_blob),
        "sample_answer_chars": len(compact_blob),
        "size_measurement": "worst case at the shipping preset",
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
