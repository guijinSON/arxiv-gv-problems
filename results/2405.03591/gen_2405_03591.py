"""Verified generator for telescoping spherical equations over finite groups.

The native objects and group law come from Sections 1.3--1.5 and 4 of
arXiv:2405.03591.  The paper's Lemma 4.1 reduces a spherical equation over
G_{p,d} = Z_p^d semidirect Z_p^* to an exact weighted vector sum, and the
proposition in Section 4.1 gives a sparse solution whenever a coefficient has
nontrivial scalar part.

This module constructs the weighted coefficient vectors as consecutive terms
of a geometric telescoping identity.  The paper's mechanical sparse-solution
algorithm still works, but a solver who recognizes the invariant can replace a
long sum by one modular power.  Verification substitutes the proposed sparse
conjugator into Lemma 4.1's exact congruence and never reads inst["answer"].
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# Make the repository helpers available when this module is run from its result
# directory.  This family needs only standard-library modular arithmetic, but
# the graceful import keeps the module compatible with the repository contract.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the standard-library path is complete
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "telescoping",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "semidirect-product group G_{p,d} = Z_p^d ⋊ Z_p^*",
        "spherical equation with parametrically specified group coefficients",
        "one-support assignment of group conjugators",
    ],
    "verification_operations": [
        "exact modular exponentiation",
        "exact modular inversion",
        "exact semidirect-product conjugation identity",
        "exact weighted vector-sum comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the prefix-weighted coefficient vectors form one "
        "geometric telescoping sequence; without that invariant the paper's "
        "sparse-solution method expands and sums every coefficient."
    ),
    "hardness_basis": (
        "Track B: the Section 4.1 sparse-solution algorithm is polynomial and, "
        "on the shipping preset, its scalarized O(m) implementation expands "
        "262144 coefficients in about 1.20 seconds and 1310761 exact modular "
        "operations, while the telescoping route measured at most 70 operations "
        "over eight seeds (a conservative bound is 168)."
    ),
    "max_answer_tokens": 11,
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


# The first argument n is the number m of conjugates in the paper's notation.
# The group-vector dimension is named dimension here to prevent an ambiguity in
# rendered instances.  Difficulty grows mainly by lengthening the coefficient
# sequence while the two-atom compressed answer stays fixed.
DIFFICULTY = {
    "demo": {"n": 4, "dimension": 2, "prime": "toy"},
    "easy": {"n": 262_144, "dimension": 16, "prime": "large"},
    "medium": {"n": 524_288, "dimension": 24, "prime": "large"},
    "hard": {"n": 1_048_576, "dimension": 32, "prime": "large"},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "Inspect the coefficient vectors after multiplication by their scalar-prefix "
    "weights: they are consecutive differences of one geometric sequence."
)
PLACEBO_HINT = (
    "Keep all residues in their least nonnegative form and check the one-based "
    "index carefully before submitting the two requested fields."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"index\": j, \"scale\": lambda} with 1 <= j <= m "
        "and 0 <= lambda < p.  It denotes z_j=(lambda*v,1) and z_i=(0,1) "
        "for every i != j; multiplication of a vector by lambda is coordinatewise "
        "modulo p."
    ),
    "bounds": {
        "fields": ["index", "scale"],
        "index_min": 1,
        "index_max": "m",
        "scale_min": 0,
        "scale_max": "p-1",
        "candidate_count": "m*p",
    },
}


NOTES = (
    "Sections 1.2--1.5 fix the exact native problem and the group law; Lemma "
    "4.1 gives the executable weighted-sum condition for a solution.  The first "
    "proposition of Section 4.1 is the certificate-producing algorithm: if some "
    "coefficient scalar beta_i is not 1, it computes a one-support solution by "
    "forming all prefix products and their weighted coefficient sum.  The same "
    "section proves that unconstrained equations are strongly generically easy. "
    "Section 5's Theorem on average-case hardness applies instead to uniformly "
    "random constrained CISE_{1,2} instances with n log(p) < m < p/(2n^4); this "
    "structured generator does not claim that distribution or Track A.  Here the "
    "prefix-weighted vectors are (t-1)t^(i-1)v, so their sum is (t^m-1)v. "
    "Alternating beta values make their total scalar product 1 and make every "
    "position eligible for the paper's sparse construction.  Endpoint-magnitude, "
    "zero/greedy, small-scalar, and random-restart attacks are measured; the "
    "paper's full prefix-sum method is separately disclosed as the successful "
    "Track B reference algorithm."
)


_PRIMES = {
    "toy": 101,
    # The Mersenne prime 2^61-1.  Deterministic 64-bit Miller--Rabin is rerun in
    # selftest rather than trusting this comment.
    "large": 2_305_843_009_213_693_951,
}


# Updated only from script-owned transcripts after all three oracle arms run.
# Until then zero solves is an explicit placeholder, not an inferred result.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_by_openrouter_key_limit",
}


def _inverse(value, modulus):
    """Exact modular inverse, rejecting zero and nonunits."""
    value %= modulus
    if value == 0:
        raise ZeroDivisionError("zero has no inverse")
    old_r, r = value, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ZeroDivisionError("value is not invertible")
    return old_s % modulus


def _inverse_counted(value, modulus):
    value %= modulus
    if value == 0:
        raise ZeroDivisionError("zero has no inverse")
    old_r, r = value, modulus
    old_s, s = 1, 0
    divisions = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        divisions += 1
    if old_r != 1:
        raise ZeroDivisionError("value is not invertible")
    return old_s % modulus, divisions


def _pow_counted(base, exponent, modulus):
    """Binary modular exponentiation returning (value, modular multiplies)."""
    result = 1
    base %= modulus
    count = 0
    while exponent:
        if exponent & 1:
            result = result * base % modulus
            count += 1
        exponent >>= 1
        if exponent:
            base = base * base % modulus
            count += 1
    return result, count


def _is_prime_64(value):
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _beta_and_prefix(inst, index):
    """Return beta_i and B_i=beta_1...beta_(i-1), for one-based i."""
    if index % 2:
        return inst["rho"], 1
    return inst["rho_inv"], inst["rho"]


def _coefficient_scalar(inst, index):
    """a_i where c_i=(a_i*v,beta_i), evaluated exactly from the input."""
    p = inst["p"]
    _beta, prefix = _beta_and_prefix(inst, index)
    return (
        _inverse(prefix, p)
        * (inst["t"] - 1)
        * pow(inst["t"], index - 1, p)
    ) % p


def _required_scale(inst, index):
    """The unique scale for a valid one-support witness at index."""
    p = inst["p"]
    beta, prefix = _beta_and_prefix(inst, index)
    endpoint = (pow(inst["t"], inst["m"], p) - 1) % p
    denominator = prefix * (beta - 1) % p
    return (-endpoint * _inverse(denominator, p)) % p


def make_instance(n, seed=0, **params):
    """Construct a certified telescoping spherical equation.

    ``n`` is the number m of conjugates.  The witness position is sampled first;
    the group parameters then define its scale by the geometric identity.  No
    published instance is searched and no equation solver is called.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 2 or n % 2:
        raise ValueError("n must be an even integer at least 2")
    dimension = params.pop("dimension", 16)
    prime_name = params.pop("prime", "large")
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 2:
        raise ValueError("dimension must be an integer at least 2")
    if prime_name not in _PRIMES:
        raise ValueError("prime must be 'toy' or 'large'")

    p = _PRIMES[prime_name]
    rng = random.Random(seed)
    witness_index = rng.randrange(1, n + 1)

    # rho != +/-1 makes every alternating beta nontrivial.  t^m != 1 makes
    # the required scale nonzero, which strengthens corruption tests.
    while True:
        rho = rng.randrange(2, p - 1)
        if rho not in (1, p - 1):
            break
    while True:
        t = rng.randrange(2, p - 1)
        if t not in (1, p - 1) and pow(t, n, p) != 1:
            break

    # Distinct nonzero coordinates guarantee that a coordinate-swap corruption
    # changes the represented group element in the direct demo audit.
    vector = []
    used = set()
    while len(vector) < dimension:
        value = rng.randrange(1, p)
        if value not in used:
            used.add(value)
            vector.append(value)

    inst = {
        "family": "telescoping spherical equation over G_{p,d}",
        "m": n,
        "dimension": dimension,
        "prime_name": prime_name,
        "p": p,
        "rho": rho,
        "rho_inv": _inverse(rho, p),
        "t": t,
        "vector": vector,
    }
    inst["answer"] = {
        "index": witness_index,
        "scale": _required_scale(inst, witness_index),
    }
    return inst


def render(inst):
    p = inst["p"]
    m = inst["m"]
    d = inst["dimension"]
    vector = " ".join(str(value) for value in inst["vector"])
    statement = f"""Find a sparse solution of a spherical equation in a finite semidirect-product group.

All residues below are least nonnegative integers modulo the prime
p={p}.  Let G be the set of pairs (x,a), where x is a length-{d} vector over
Z_p and a is a nonzero residue modulo p.  Define the group operation by

    (x,a)*(y,b) = (x + a*y mod p, a*b mod p).

Its identity is (0,1), where 0 is the all-zero vector.  Vector addition and
scalar multiplication are coordinatewise modulo p.  Inverses and powers of
nonzero residues are also taken modulo p.

This instance has m={m} ordered coefficients c_1,...,c_m.  Put

    rho = {inst['rho']},    rho_inverse = {inst['rho_inv']},
    t = {inst['t']},
    v = [{vector}].

For each one-based index i=1,...,m, define beta_i and the vector part of c_i by

    beta_i = rho                  if i is odd,
             rho_inverse          if i is even;

    a_i = (t-1)*t^(i-1)           if i is odd,
          rho_inverse*(t-1)*t^(i-1) if i is even;

    c_i = (a_i*v mod p, beta_i).

The order of the m factors is significant.  Find a one-support assignment to
the variables z_1,...,z_m such that

    z_1^(-1)*c_1*z_1 * z_2^(-1)*c_2*z_2 * ... * z_m^(-1)*c_m*z_m = (0,1).

Your assignment must have the following compressed form: choose one index j
with 1 <= j <= m and one scale lambda with 0 <= lambda < p, set
z_j=(lambda*v mod p,1), and set every z_i=(0,1) for i != j.  Any valid j is
accepted.  Indices are one-based, repetitions are not relevant because exactly
one index is returned, and both interval bounds above are inclusive.

Return a JSON object with exactly the integer fields \"index\" and \"scale\".
Give your final answer inside <answer></answer> tags, as that JSON object.
Example: <answer>{{\"index\":1,\"scale\":0}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract a tagged JSON object while tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value.values()):
        return None
    return value


def verify(inst, answer):
    """Check any compressed one-support witness without reading inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object must not be empty"
    expected = {"index", "scale"}
    missing = sorted(expected - set(answer))
    if missing:
        return False, "missing field: " + missing[0]
    extra = sorted(set(answer) - expected)
    if extra:
        return False, "unexpected field: " + extra[0]
    index = answer["index"]
    scale = answer["scale"]
    if isinstance(index, bool) or not isinstance(index, int):
        return False, "index is not an integer"
    if isinstance(scale, bool) or not isinstance(scale, int):
        return False, "scale is not an integer"
    if not 1 <= index <= inst["m"]:
        return False, f"index is outside 1 <= index <= {inst['m']}"
    if not 0 <= scale < inst["p"]:
        return False, "scale is outside 0 <= scale < p"

    # Lemma 4.1 says the vector residual is
    #   sum_i B_i*cvec_i + B_j*(beta_j-1)*zvec_j.
    # The instance definition gives B_i*cvec_i=(t-1)t^(i-1)v, so exact
    # geometric telescoping reduces the residual to the scalar below times v.
    p = inst["p"]
    beta, prefix = _beta_and_prefix(inst, index)
    endpoint = (pow(inst["t"], inst["m"], p) - 1) % p
    residual_scalar = (endpoint + prefix * (beta - 1) * scale) % p
    if residual_scalar:
        return False, "spherical group equation is not satisfied"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the exact structure-aware language m times Z_p."""
    return {
        "index": rng.randrange(1, inst["m"] + 1),
        "scale": rng.randrange(inst["p"]),
    }


def search_space(inst):
    return inst["m"] * inst["p"]


def enumerate_all(inst):
    total = search_space(inst)
    if total > 100_000:
        return None
    count = 0
    for index in range(1, inst["m"] + 1):
        for scale in range(inst["p"]):
            count += int(verify(inst, {"index": index, "scale": scale})[0])
    return count


def canonical_key(inst):
    """Canonical under every linear change of coordinates in Z_p^d.

    All nonzero vectors v lie in one GL(d,p) orbit, so v is deliberately absent.
    The remaining scalars determine the ordered coefficient formula.  Reordering
    factors is not a relabelling: G_{p,d} is noncommutative and the statement
    explicitly fixes their order.
    """
    payload = {
        "family": inst["family"],
        "p": inst["p"],
        "m": inst["m"],
        "dimension": inst["dimension"],
        "rho": inst["rho"],
        "t": inst["t"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Grow the coefficient haystack while keeping the two-field answer fixed."""
    n = params.get("n")
    dimension = params.get("dimension", 16)
    prime = params.get("prime", "large")
    if prime == "large" and isinstance(n, int) and n < 16_777_216:
        return {
            "n": n * 2,
            "dimension": min(64, dimension + 8),
            "prime": "large",
        }
    return None


def _direct_group_check(inst, answer):
    """Literal native-group multiplication, reserved for small audit instances."""
    p = inst["p"]
    d = inst["dimension"]
    accumulator_vector = [0] * d
    accumulator_scalar = 1
    for index in range(1, inst["m"] + 1):
        beta, _prefix = _beta_and_prefix(inst, index)
        cscale = _coefficient_scalar(inst, index)
        conjugator_scale = answer["scale"] if index == answer["index"] else 0
        factor_vector = [
            (cscale * value + (beta - 1) * conjugator_scale * value) % p
            for value in inst["vector"]
        ]
        accumulator_vector = [
            (x + accumulator_scalar * y) % p
            for x, y in zip(accumulator_vector, factor_vector)
        ]
        accumulator_scalar = accumulator_scalar * beta % p
    return accumulator_scalar == 1 and all(value == 0 for value in accumulator_vector)


def _reference_solve(inst):
    """Section 4.1 prefix-sum algorithm, scalarized but not telescoped."""
    p = inst["p"]
    power = 1
    total = 0
    operations = 0
    for index in range(1, inst["m"] + 1):
        _beta, prefix = _beta_and_prefix(inst, index)
        prefix_inv = 1 if index % 2 else inst["rho_inv"]
        cscale = prefix_inv * (inst["t"] - 1) % p
        operations += 1
        cscale = cscale * power % p
        operations += 1
        weighted = prefix * cscale % p
        operations += 1
        total = (total + weighted) % p
        operations += 1
        power = power * inst["t"] % p
        operations += 1
    inverse, divisions = _inverse_counted(inst["rho"] - 1, p)
    scale = (-total * inverse) % p
    operations += divisions + 2
    return {"index": 1, "scale": scale}, {
        "modular_operations": operations,
        "euclidean_divisions": divisions,
        "expanded_coefficients": inst["m"],
    }


def _compact_solve(inst, index=1):
    """Intended geometric-telescoping route with an exact operation count."""
    p = inst["p"]
    power, multiplications = _pow_counted(inst["t"], inst["m"], p)
    beta, prefix = _beta_and_prefix(inst, index)
    denominator = prefix * (beta - 1) % p
    inverse, divisions = _inverse_counted(denominator, p)
    scale = (-(power - 1) * inverse) % p
    operations = multiplications + divisions + 4
    return {"index": index, "scale": scale}, {
        "modular_operations": operations,
        "power_multiplications": multiplications,
        "euclidean_divisions": divisions,
    }


def _attack_candidates(inst, seed):
    p = inst["p"]
    m = inst["m"]

    # Per-position endpoint magnitude: inspect a few conspicuous coefficient
    # scalars and use the smallest ordinary residue as both clue and scale.
    positions = sorted(set((1, 2, 3, m - 2, m - 1, m)))
    endpoint_data = [(_coefficient_scalar(inst, j), j) for j in positions]
    smallest_value, smallest_index = min(endpoint_data)
    outlier = [{"index": smallest_index, "scale": smallest_value}]

    # Greedy/linearized sum: replace every t^(i-1) by 1 and cancel that sum at
    # the first factor.  This is executable by hand but discards the invariant.
    linear_total = m * (inst["t"] - 1) % p
    greedy_scale = (-linear_total * _inverse(inst["rho"] - 1, p)) % p
    greedy = [{"index": 1, "scale": greedy_scale}]

    # Small symbolic ansatzes a solver might try without doing long arithmetic.
    obvious = [
        0,
        1,
        p - 1,
        inst["t"],
        inst["rho"],
        (inst["t"] - 1) % p,
        (inst["rho"] - 1) % p,
        sum(inst["vector"]) % p,
    ]
    small_ansatz = [
        {"index": index, "scale": scale}
        for index in (1, 2)
        for scale in obvious
    ]

    rrng = random.Random(seed ^ 0x240503591)
    restarts = [random_candidate(inst, rrng) for _ in range(256)]
    return {
        "outlier_endpoint_coefficient": outlier,
        "greedy_linearized_geometric_sum": greedy,
        "by_hand_small_scalar_ansatz": small_ansatz,
        "random_restart_256": restarts,
    }


def _coordinate_variants(inst, seed):
    """Seven nonempty compositions of coordinate permutation/scale/shear."""
    rng = random.Random(seed)
    d = inst["dimension"]
    p = inst["p"]
    permutation = list(range(d))
    rng.shuffle(permutation)
    diagonal = [rng.randrange(1, p) for _ in range(d)]
    shear = rng.randrange(1, p)
    variants = []
    for mask in range(1, 8):
        vector = list(inst["vector"])
        if mask & 1:
            vector = [vector[i] for i in permutation]
        if mask & 2:
            vector = [value * diagonal[i] % p for i, value in enumerate(vector)]
        if mask & 4:
            vector[0] = (vector[0] + shear * vector[1]) % p
        transformed = {
            key: (dict(value) if isinstance(value, dict) else value)
            for key, value in inst.items()
            if key != "vector"
        }
        transformed["vector"] = vector
        variants.append(transformed)
    return variants


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    prime_checks = {name: _is_prime_64(value) for name, value in _PRIMES.items()}
    g1_failures = []
    g1_attempts = 0
    direct_demo_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
            if preset == "demo":
                direct = _direct_group_check(inst, inst["answer"])
                direct_demo_checks += int(direct)
                if not direct:
                    g1_failures.append([preset, seed, "literal group product failed"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and all(prime_checks.values()) and direct_demo_checks == 3,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "prime_checks": prime_checks,
        "literal_demo_group_products": direct_demo_checks,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = {"index": answer["scale"], "scale": answer["index"]}
    corruptions = {
        "drop": {"index": answer["index"]},
        "swap": swapped,
        "duplicate": {**answer, "scale_copy": answer["scale"]},
        "empty": {},
        "out_of_range": {"index": answer["index"], "scale": inst["p"]},
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The sparse conjugator I obtain is below.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe index is one-based."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    guess_rng = random.Random(0x240503591)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_density": f"1/{inst['p']}",
        "candidate_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_endpoint_coefficient",
        "greedy_linearized_geometric_sum",
        "by_hand_small_scalar_ansatz",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    compact_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_divisions = 0
    compact_max_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _reference_solve(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(verify(trial, recovered)[0])
        reference_operations += counts["modular_operations"]
        reference_divisions += counts["euclidean_divisions"]
        compact, compact_counts = _compact_solve(trial)
        compact_successes += int(verify(trial, compact)[0])
        compact_max_operations = max(
            compact_max_operations, compact_counts["modular_operations"]
        )
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "Section 4.1 prefix-product and weighted-coefficient summation",
        "complexity": (
            "O(m) modular operations for the displayed rank-one formula; "
            "O(m*d) on explicitly expanded group vectors"
        ),
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "euclidean_divisions": reference_divisions // 8,
        "expanded_coefficients": inst["m"],
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "geometric telescoping plus one modular inverse",
            "solves": f"{compact_successes}/8",
            "measured_max_operations": compact_max_operations,
            "operations_upper_bound": 2 * inst["m"].bit_length()
            + 2 * inst["p"].bit_length()
            + 8,
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == demo["m"]
        and all_failed
        and reference_successes == 8
        and compact_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "shipping_exact_valid_answers": inst["m"],
        "shipping_exact_candidate_count": search_space(inst),
        "shipping_exact_density": f"1/{inst['p']}",
        "demo_exact_solution_count": demo_count,
        "baseline_attack_name": "random_restart_256",
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_m = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["m"] == 2 * inst["m"]
        and search_space(doubled) > search_space(inst)
        and ladder_m == sorted(ladder_m)
        and len(set(ladder_m)) == len(ladder_m),
        "shipping_m": inst["m"],
        "doubled_m": doubled["m"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
        "answer_atoms_shipping": 2,
        "answer_atoms_doubled": 2,
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _coordinate_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "coordinate permutation",
            "invertible diagonal coordinate scaling",
            "invertible coordinate shear",
            "all nonempty compositions of those three",
        ],
        "scope": (
            "complete for the GL(d,p) orbit of the nonzero direction v; ordered "
            "noncommuting factors are intentionally not freely permuted"
        ),
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = 2
    worst_case_answer = {"index": inst["m"], "scale": inst["p"] - 1}
    worst_case_chars = len(json.dumps(worst_case_answer, separators=(",", ":")))
    worst_case_tokens = math.ceil(worst_case_chars / 4)
    intended_bound = (
        2 * inst["m"].bit_length() + 2 * inst["p"].bit_length() + 8
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_bound <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_case_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_case_chars,
        "worst_case_answer_tokens": worst_case_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_bound,
        "measured_compact_operations_max": compact_max_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
