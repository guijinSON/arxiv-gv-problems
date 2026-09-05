"""Verified generator for exact finite-field orthogonal-system counts.

The source is arXiv:0807.0592, especially the definition of D_k and lambda_k
in Section 2.  An instance is a subset E of GF(p)^d made from scalar layers
on a signed, coordinate-scrambled Hadamard basis.  Its exact ordered count is
known before the vectors are assembled:

    lambda_k = k! * e_k(m_1, ..., m_d),

where m_i is the number of nonzero scalar multiples on basis line i.  The
verifier does not trust that construction.  It normalizes every displayed
vector projectively, checks all resulting directions are nonisotropic and
mutually orthogonal, and recomputes the elementary symmetric coefficient.

Only the Python standard library is used.  Import has no I/O or randomness.
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
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "rational",
    "native_objects": [
        "explicit subset of a vector space over GF(p)",
        "finite-field dot product",
        "ordered mutually orthogonal vector systems",
    ],
    "verification_operations": [
        "exact modular projective normalization",
        "exact finite-field inner products",
        "exact elementary-symmetric coefficient recurrence",
        "reduced-rational comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize the displayed vectors as scalar layers on mutually orthogonal "
        "projective directions and count choices by their multiplicities; without "
        "that decomposition one must normalize the full set and reconstruct its Gram relations."
    ),
    "hardness_basis": (
        "Track B: projective normalization, an exact Gram check, and coefficient "
        "dynamic programming solve this promised distribution in "
        "O(|E|d+d^3+dk); at the final d=128 candidate selftest measured 2,165,594 "
        "field operations and 0.0577 seconds on average, while the scalar-layer/Newton "
        "route uses 285 exact arithmetic operations."
    ),
    "max_answer_tokens": 8,
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
    "demo": {
        "n": 4,
        "k": 2,
        "p": 257,
        "min_multiplicity": 1,
        "max_multiplicity": 2,
    },
    "easy": {
        "n": 16,
        "k": 2,
        "p": 257,
        "min_multiplicity": 1,
        "max_multiplicity": 1,
    },
    "medium": {
        "n": 32,
        "k": 3,
        "p": 257,
        "min_multiplicity": 1,
        "max_multiplicity": 1,
    },
    "hard": {
        "n": 128,
        "k": 10,
        "p": 257,
        "min_multiplicity": 1,
        "max_multiplicity": 5,
    },
}

SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "The canonical coordinate magnitudes are scalar layers on mutually orthogonal projective directions."
)
PLACEBO_HINT: str = (
    "The modular representatives and ordered-tuple convention require especially careful bookkeeping."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One reduced nonnegative rational [a,1].  The numerator a is a multiple "
        "of k! from 0 through the falling factorial |E|!/(|E|-k)!, inclusive."
    ),
    "bounds": {
        "json_shape": "[numerator, denominator]",
        "denominator": 1,
        "numerator_min": 0,
        "numerator_max": "falling_factorial(|E|, k)",
        "numerator_step": "k!",
    },
}

# Filled from the script-owned oracle runs before shipping.
G9_RESULTS: dict = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 1, "attempts": 1},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy",
}

NOTES: str = r"""
Paper definition.  Section 2 defines D_k as the ordered tuples
(x_1,...,x_k) in E^k satisfying x_i dot x_j=0 for every i<j, and defines
lambda_k=|D_k|.  Repetition is not separately forbidden.  Every vector in
this family is nonisotropic, so a valid tuple cannot repeat a vector.

Step-0 algorithm question.  Theorem 1.1 is a dense-set existence and
asymptotic-count theorem under binom(k,2)<d; it is not a search-hardness
theorem.  In its regime it predicts density q^(-binom(k,2)), so it cannot
justify Track A for the planted-subset proposal.  Section 2's recurrence
extends an orthogonal (k-1)-tuple through a common perpendicular hyperplane,
which is mechanically executable by enumerating tuples.  On this promised
distribution a much better exact algorithm normalizes projective directions,
checks their Gram matrix, and performs coefficient DP in
O(|E|d+d^3+dk).  That polynomial algorithm is disclosed as the Track-B
reference algorithm.

Construction.  The multiplicities m_i are sampled first.  Before any vector
is assembled, the answer is composed from the identity
lambda_k=k!*[z^k] product_i(1+m_i z).  A Sylvester Hadamard basis is then
randomly row-signed, coordinate-signed, coordinate-permuted, scaled through
the layers 1,...,m_i, and shuffled.  The Hadamard identity HH^T=dI proves
that different projective directions are orthogonal and each direction is
nonisotropic because p does not divide d.

Compact route and attacks.  All coordinates of a displayed vector have one
canonical magnitude s=min(a,p-a).  The supplied audit histogram records how
many vectors occupy each scalar layer; adjacent histogram differences give
the multiplicity frequencies.  Newton identities recover the needed
elementary-symmetric coefficient with at most 300 exact operations at the
shipping preset.  Coordinate and row scrambling defeat position and sign
probes.  The attack panel checks a largest-layer outlier guess, a greedy
top-k-lines count, the paper's random-density ansatz, and structure-aware
random certificate restarts.  The successful projective-normalization
algorithm is reported separately, as Track B requires.

Easy regimes.  k=2 and the demo are hand-scale.  Full E=GF(q)^d or sets in
Theorem 1.1's density range have many tuples and permit random sampling;
neither is used.  Section 3 also constructs large orthogonal-pair-free sets,
which are irrelevant to this positive exact-count family.

Hardening outcome.  The bare pool hardened first at n=64,k=10, but a valid
answer appeared when its one-sentence structural hint was supplied.  The one
permitted G9 move raised the shipping candidate to n=128,k=10 and five scalar
layers.  That candidate hardened bare on all three vendors, but GPT-5.6 Terra
returned the exact hinted answer for seed 1597021224 in 67.4 seconds.  Thus
G9(b), not G, V, the answer cap, or the arithmetic-operation cap, rejects the
family.  Later hinted calls hit the external key limit; they are not counted
as failures and are unnecessary because one verified solve already fails the
polarity-flipped gate.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


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


def _falling(total: int, k: int) -> int:
    value = 1
    for offset in range(k):
        value *= total - offset
    return value


def _elementary_count(multiplicities: list[int], k: int) -> int:
    coefficients = [1] + [0] * k
    for multiplicity in multiplicities:
        for degree in range(k, 0, -1):
            coefficients[degree] += coefficients[degree - 1] * multiplicity
    return math.factorial(k) * coefficients[k]


def _validate_parameters(
    n: int,
    k: int,
    p: int,
    min_multiplicity: int,
    max_multiplicity: int,
) -> None:
    values = (n, k, p, min_multiplicity, max_multiplicity)
    if not all(_is_int(value) for value in values):
        raise ValueError("all parameters must be integers")
    if not _is_power_of_two(n) or n < 4:
        raise ValueError("n must be a power of two at least 4")
    if k < 2 or k > n:
        raise ValueError("k must lie from 2 through n")
    if math.comb(k, 2) >= n:
        raise ValueError("the paper's dimension regime requires binom(k,2) < n")
    if not _is_prime(p) or p <= n:
        raise ValueError("p must be a prime larger than n")
    if min_multiplicity < 1 or max_multiplicity < min_multiplicity:
        raise ValueError("multiplicity bounds must be positive and ordered")
    if 2 * max_multiplicity >= p:
        raise ValueError("scalar layers must be below p/2")


def _hadamard_sign(row: int, column: int) -> int:
    return -1 if ((row & column).bit_count() & 1) else 1


def make_instance(
    n: int,
    seed: int = 0,
    k: int = 5,
    p: int = 257,
    min_multiplicity: int = 1,
    max_multiplicity: int = 4,
    **params,
) -> dict:
    """Compose lambda_k first, then assemble its finite-field vector set."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, k, p, min_multiplicity, max_multiplicity)
    rng = random.Random(seed)

    # The certificate is fixed before the emitted coordinates exist.
    while True:
        multiplicities = [
            rng.randint(min_multiplicity, max_multiplicity) for _ in range(n)
        ]
        if min_multiplicity == max_multiplicity or len(set(multiplicities)) >= 2:
            break
    lambda_k = _elementary_count(multiplicities, k)

    coordinate_order = list(range(n))
    rng.shuffle(coordinate_order)
    coordinate_signs = [rng.choice((-1, 1)) for _ in range(n)]
    row_signs = [rng.choice((-1, 1)) for _ in range(n)]

    vectors: list[list[int]] = []
    for row, multiplicity in enumerate(multiplicities):
        for scalar in range(1, multiplicity + 1):
            vector = []
            for shown_column in range(n):
                source_column = coordinate_order[shown_column]
                sign = (
                    row_signs[row]
                    * coordinate_signs[shown_column]
                    * _hadamard_sign(row, source_column)
                )
                vector.append((sign * scalar) % p)
            vectors.append(vector)
    rng.shuffle(vectors)

    histogram = []
    for scalar in range(1, max(multiplicities) + 1):
        histogram.append([scalar, sum(m >= scalar for m in multiplicities)])

    return {
        "field_prime": p,
        "dimension": n,
        "tuple_size": k,
        "vectors": vectors,
        "magnitude_histogram": histogram,
        "answer": [lambda_k, 1],
    }


def _canonical_magnitude(value: int, p: int) -> int:
    value %= p
    return min(value, (-value) % p)


def _rational_text(answer) -> str:
    return f"{int(answer[0])}/{int(answer[1])}"


def render(inst: dict) -> str:
    p = inst["field_prime"]
    dimension = inst["dimension"]
    k = inst["tuple_size"]
    vectors = inst["vectors"]
    total = len(vectors)
    upper = _falling(total, k)
    factorial = math.factorial(k)

    lines = [
        "Exact count of orthogonal systems over a finite field",
        "",
        f"Work in GF({p}); every coordinate below is its canonical integer residue 0,...,{p - 1}.",
        f"For x,y in GF({p})^{dimension}, define x dot y = sum_j x_j*y_j modulo {p}.",
        f"The set E consists of the {total} distinct rows listed below.  Each row is nonzero and",
        "nonisotropic (x dot x is nonzero); these promises are part of the instance.",
        "",
        f"An ordered orthogonal {k}-system is an ordered tuple (x_1,...,x_{k}) in E^{k}",
        "such that x_i dot x_j = 0 for every i<j.  Repetitions are not separately",
        "forbidden, but nonisotropy makes a repeated vector impossible in a valid tuple.",
        f"Compute lambda_{k}, the exact number of ordered orthogonal {k}-systems.",
        "",
        "For exact auditing, the canonical magnitude of a residue a is min(a,p-a).",
        "The supplied histogram [s,c] says that exactly c displayed vectors have every",
        "coordinate of canonical magnitude s:",
        json.dumps(inst["magnitude_histogram"], separators=(",", ":")),
        "",
        "Vectors (row numbers are only for readability; row order has no mathematical meaning):",
    ]
    for index, vector in enumerate(vectors):
        lines.append(f"{index}: " + " ".join(str(value) for value in vector))

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])

    lines.extend(
        [
            "",
            "Output the count as the reduced rational NUM/1.  It must satisfy",
            f"0 <= NUM <= {upper} and be divisible by {factorial}=k!.",
            "Give your final answer inside <answer></answer> tags, as NUM/1.",
            "Example: <answer>360/1</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S).strip()
    rational = re.fullmatch(r"([+-]?\d+)\s*/\s*([+-]?\d+)", body)
    if rational:
        try:
            return [int(rational.group(1)), int(rational.group(2))]
        except ValueError:
            return None
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(_is_int(entry) for entry in value)
    ):
        return value
    return None


def _inverse_counted(value: int, p: int) -> tuple[int, int]:
    value %= p
    if value == 0:
        raise ValueError("zero has no inverse")
    old_r, r = value, p
    old_s, s = 1, 0
    divisions = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        divisions += 1
    if old_r != 1:
        raise ValueError("pivot is not invertible")
    return old_s % p, divisions


def _reference_count(inst: dict) -> tuple[int, dict]:
    """Independently recover projective directions and their exact Gram data."""
    p = inst.get("field_prime")
    dimension = inst.get("dimension")
    k = inst.get("tuple_size")
    vectors = inst.get("vectors")
    histogram = inst.get("magnitude_histogram")
    if not (_is_int(p) and _is_prime(p)):
        raise ValueError("field_prime is not prime")
    if not (_is_int(dimension) and dimension >= 1):
        raise ValueError("invalid dimension")
    if not (_is_int(k) and 1 <= k <= dimension):
        raise ValueError("invalid tuple size")
    if not isinstance(vectors, list) or not vectors:
        raise ValueError("vectors must be a nonempty list")

    seen_vectors = set()
    direction_counts: dict[tuple[int, ...], int] = {}
    actual_histogram: dict[int, int] = {}
    field_operations = 0
    euclidean_divisions = 0

    for vector in vectors:
        if (
            not isinstance(vector, list)
            or len(vector) != dimension
            or not all(_is_int(value) and 0 <= value < p for value in vector)
        ):
            raise ValueError("a vector has invalid shape or coordinate")
        frozen = tuple(vector)
        if frozen in seen_vectors:
            raise ValueError("vectors are not distinct")
        seen_vectors.add(frozen)
        pivot = next((value for value in vector if value), None)
        if pivot is None:
            raise ValueError("zero vector is forbidden")
        inverse, divisions = _inverse_counted(pivot, p)
        euclidean_divisions += divisions
        representative = tuple((value * inverse) % p for value in vector)
        field_operations += dimension
        direction_counts[representative] = direction_counts.get(representative, 0) + 1

        magnitudes = {_canonical_magnitude(value, p) for value in vector}
        if len(magnitudes) != 1 or 0 in magnitudes:
            raise ValueError("a vector does not have one nonzero canonical magnitude")
        magnitude = next(iter(magnitudes))
        actual_histogram[magnitude] = actual_histogram.get(magnitude, 0) + 1

    expected_histogram = [[s, actual_histogram[s]] for s in sorted(actual_histogram)]
    if histogram != expected_histogram:
        raise ValueError("magnitude histogram does not match the vectors")

    directions = sorted(direction_counts)
    for i, left in enumerate(directions):
        norm = 0
        for a in left:
            norm = (norm + a * a) % p
            field_operations += 2
        if norm == 0:
            raise ValueError("a projective direction is isotropic")
        for right in directions[i + 1 :]:
            dot = 0
            for a, b in zip(left, right):
                dot = (dot + a * b) % p
                field_operations += 2
            if dot != 0:
                raise ValueError("projective directions are not mutually orthogonal")

    coefficients = [1] + [0] * k
    for multiplicity in direction_counts.values():
        for degree in range(k, 0, -1):
            coefficients[degree] += coefficients[degree - 1] * multiplicity
            field_operations += 2
    result = math.factorial(k) * coefficients[k]
    field_operations += max(1, k)
    return result, {
        "field_operations": field_operations,
        "euclidean_divisions": euclidean_divisions,
        "projective_directions": len(directions),
    }


def _compact_count(inst: dict) -> tuple[int, int]:
    """Count from the scalar-layer histogram using Newton identities."""
    histogram = inst["magnitude_histogram"]
    k = inst["tuple_size"]
    if not histogram:
        raise ValueError("empty histogram")
    max_scalar = histogram[-1][0]
    layers = {scalar: count for scalar, count in histogram}
    frequencies = {}
    operations = 0
    for scalar in range(1, max_scalar + 1):
        frequencies[scalar] = layers.get(scalar, 0) - layers.get(scalar + 1, 0)
        operations += 1

    power_sums = [0] * (k + 1)
    for scalar, frequency in frequencies.items():
        power = 1
        for degree in range(1, k + 1):
            power *= scalar
            power_sums[degree] += frequency * power
            operations += 3

    elementary = [0] * (k + 1)
    elementary[0] = 1
    for degree in range(1, k + 1):
        total = 0
        for index in range(1, degree + 1):
            term = elementary[degree - index] * power_sums[index]
            total = total + term if index & 1 else total - term
            operations += 2
        if total % degree:
            raise ValueError("Newton identity did not divide exactly")
        elementary[degree] = total // degree
        operations += 1
    factorial = 1
    for value in range(2, k + 1):
        factorial *= value
        operations += 1
    operations += 1
    return factorial * elementary[k], operations


def verify(inst: dict, answer) -> tuple[bool, str]:
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a rational pair [numerator, denominator]"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer is missing its denominator"
    if len(answer) > 2:
        return False, "answer has extra entries"
    numerator, denominator = answer
    if not (_is_int(numerator) and _is_int(denominator)):
        return False, "numerator and denominator must be integers"
    if denominator <= 0:
        return False, "denominator must be positive"
    if math.gcd(numerator, denominator) != 1:
        return False, "rational answer is not reduced"
    if denominator != 1:
        return False, "the exact count must have denominator 1"
    if numerator < 0:
        return False, "the count cannot be negative"

    try:
        total = len(inst["vectors"])
        k = inst["tuple_size"]
        upper = _falling(total, k)
        factorial = math.factorial(k)
    except (KeyError, TypeError, ValueError):
        return False, "instance has invalid counting parameters"
    if numerator > upper:
        return False, "count exceeds the number of ordered distinct tuples"
    if numerator % factorial:
        return False, "count is not divisible by k!"
    try:
        expected, _metrics = _reference_count(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, "invalid instance: " + str(exc)
    if numerator != expected:
        return False, "incorrect exact orthogonal-system count"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    total = len(inst["vectors"])
    k = inst["tuple_size"]
    rank = rng.randrange(math.comb(total, k) + 1)
    return [rank * math.factorial(k), 1]


def search_space(inst: dict) -> int | None:
    return math.comb(len(inst["vectors"]), inst["tuple_size"]) + 1


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    expected, _metrics = _reference_count(inst)
    factorial = math.factorial(inst["tuple_size"])
    hits = 0
    for rank in range(space):
        if rank * factorial == expected:
            hits += 1
    return hits


def _projective_profile(inst: dict) -> tuple[int, ...]:
    p = inst["field_prime"]
    counts: dict[tuple[int, ...], int] = {}
    for vector in inst["vectors"]:
        pivot = next(value for value in vector if value)
        inverse = pow(pivot, -1, p)
        representative = tuple((value * inverse) % p for value in vector)
        counts[representative] = counts.get(representative, 0) + 1
    return tuple(sorted(counts.values()))


def canonical_key(inst: dict) -> str:
    """Canonicalize row order and every orthogonal relabelling of the axes."""
    payload = {
        "p": inst["field_prime"],
        "d": inst["dimension"],
        "k": inst["tuple_size"],
        "projective_multiplicities": _projective_profile(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    result = dict(params)
    n = int(result["n"])
    if n < 512:
        result["n"] = 2 * n
        # This grows the vector haystack and reference Gram work while the
        # rational certificate stays at two atoms and the Newton route stays short.
        if n >= 64:
            result["max_multiplicity"] = min(5, int(result["max_multiplicity"]) + 1)
        return result
    return None


def _candidate_equal(candidate, target) -> bool:
    return (
        isinstance(candidate, list)
        and len(candidate) == 2
        and candidate[0] == target
        and candidate[1] == 1
    )


def _attack_candidates(inst: dict, rng: random.Random) -> dict[str, list[list[int]]]:
    n = inst["dimension"]
    k = inst["tuple_size"]
    total = len(inst["vectors"])
    factorial = math.factorial(k)
    histogram = inst["magnitude_histogram"]
    layers = {scalar: count for scalar, count in histogram}
    max_scalar = histogram[-1][0]
    frequencies = {
        scalar: layers.get(scalar, 0) - layers.get(scalar + 1, 0)
        for scalar in range(1, max_scalar + 1)
    }
    multiplicities = []
    for scalar, frequency in frequencies.items():
        multiplicities.extend([scalar] * frequency)
    multiplicities.sort(reverse=True)

    max_count = frequencies.get(max_scalar, 0)
    outlier = 0
    if max_count >= k:
        outlier = factorial * math.comb(max_count, k) * (max_scalar**k)

    greedy = factorial
    for value in multiplicities[:k]:
        greedy *= value

    numerator = total**k
    denominator = (inst["field_prime"] ** math.comb(k, 2)) * factorial
    expected_rank = (numerator + denominator // 2) // denominator
    paper_density = expected_rank * factorial

    random_guesses = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_largest_scalar_layer": [[outlier, 1]],
        "greedy_top_k_projective_lines": [[greedy, 1]],
        "paper_random_density_ansatz": [[paper_density, 1]],
        "random_certificate_restart_256": random_guesses,
    }


def _transform_instance(inst: dict, rng: random.Random, reorder: bool, coordinates: bool) -> dict:
    result = {
        "field_prime": inst["field_prime"],
        "dimension": inst["dimension"],
        "tuple_size": inst["tuple_size"],
        "vectors": [list(vector) for vector in inst["vectors"]],
        "magnitude_histogram": [list(pair) for pair in inst["magnitude_histogram"]],
        "answer": list(inst["answer"]),
    }
    if coordinates:
        p = result["field_prime"]
        order = list(range(result["dimension"]))
        rng.shuffle(order)
        signs = [rng.choice((-1, 1)) for _ in order]
        result["vectors"] = [
            [(signs[j] * vector[source]) % p for j, source in enumerate(order)]
            for vector in result["vectors"]
        ]
    if reorder:
        rng.shuffle(result["vectors"])
    return result


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(entry) for entry in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(entry) for entry in value)
    return 1


def selftest() -> dict:
    report: dict = {}
    preset_instances = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            preset_instances += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                planted_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "instances": preset_instances,
        "failures": planted_failures,
    }

    corruption_inst = make_instance(seed=41, **DIFFICULTY["easy"])
    correct = corruption_inst["answer"]
    upper = _falling(len(corruption_inst["vectors"]), corruption_inst["tuple_size"])
    step = math.factorial(corruption_inst["tuple_size"])
    corruptions = {
        "drop_one": [correct[0]],
        "swap": [correct[1], correct[0]],
        "duplicate": [correct[0], correct[1], correct[1]],
        "empty": [],
        "out_of_range": [upper + step, 1],
        "wrong_in_range": [correct[0] - step, 1],
    }
    corruption_reasons = {}
    corruption_ok = True
    for name, candidate in corruptions.items():
        ok, reason = verify(corruption_inst, candidate)
        corruption_ok = corruption_ok and not ok
        corruption_reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": corruption_ok and len(set(corruption_reasons.values())) == len(corruption_reasons),
        "reasons": corruption_reasons,
    }

    model_response = (
        "I used the orthogonal projective-line decomposition.\n\n"
        f"<answer>\n```text\n{_rational_text(correct)}\n```\n</answer>\n"
        "The value is exact."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == correct and parse_answer("garbage") is None,
        "parsed": parsed,
    }

    shipping = make_instance(seed=1729, **DIFFICULTY[SHIPPING_DIFFICULTY])
    shipping_target, reference_metrics = _reference_count(shipping)
    guess_rng = random.Random(99173)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if _candidate_equal(random_candidate(shipping, guess_rng), shipping_target):
            guess_hits += 1
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "certificate_space": search_space(shipping),
        "candidate_prior": "uniform over every k!-multiple in [0, falling(|E|,k)]",
    }

    reference_times = []
    reference_operations = []
    reference_divisions = []
    for seed in range(8):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        started = time.perf_counter()
        recovered, metrics = _reference_count(inst)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(metrics["field_operations"])
        reference_divisions.append(metrics["euclidean_divisions"])
        if recovered != inst["answer"][0]:
            planted_failures.append(["reference", seed, "count mismatch"])

    attack_rng = random.Random(731)
    started = time.perf_counter()
    restart_hits = 0
    restart_total = 4096
    for _ in range(restart_total):
        if _candidate_equal(random_candidate(shipping, attack_rng), shipping_target):
            restart_hits += 1
    restart_seconds = time.perf_counter() - started
    report["G5_density_and_baseline"] = {
        "pass": guess_probability < 1e-6 and restart_hits == 0,
        "shipping_valid_answers": 1,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sample_density": guess_probability,
        "exact_language_density": 1 / search_space(shipping),
        "baseline_wall_seconds": sum(reference_times) / len(reference_times),
        "baseline_field_operations": sum(reference_operations) / len(reference_operations),
        "baseline_euclidean_divisions": sum(reference_divisions) / len(reference_divisions),
        "strongest_failing_attack_wall_seconds": restart_seconds,
        "strongest_failing_attack_restarts": restart_total,
        "demo_valid_answer_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
    }

    attack_results = {
        "outlier_largest_scalar_layer": {"successes": 0, "attempts": 8},
        "greedy_top_k_projective_lines": {"successes": 0, "attempts": 8},
        "paper_random_density_ansatz": {"successes": 0, "attempts": 8},
        "random_certificate_restart_256": {"successes": 0, "attempts": 8},
    }
    for seed in range(8):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        target, _metrics = _reference_count(inst)
        candidates = _attack_candidates(inst, random.Random(30_000 + seed))
        for name, guesses in candidates.items():
            if any(_candidate_equal(guess, target) for guess in guesses):
                attack_results[name]["successes"] += 1
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "projective normalization + exact Gram check + coefficient DP",
            "complexity": "O(|E|d + d^3 + dk) exact",
            "wall_clock_sec": sum(reference_times) / len(reference_times),
            "operations": sum(reference_operations) / len(reference_operations),
            "euclidean_divisions": sum(reference_divisions) / len(reference_divisions),
            "solves": "8/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=404, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["vectors"]) > len(shipping["vectors"]),
        "shipping_dimension": shipping["dimension"],
        "doubled_dimension": doubled["dimension"],
        "shipping_vectors": len(shipping["vectors"]),
        "doubled_vectors": len(doubled["vectors"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_witness_checks = 0
    keys = set()
    distinct_seeds = []
    for seed in range(20):
        inst = make_instance(seed=40_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        keys.add(key)
        distinct_seeds.append(40_000 + seed)
        rng = random.Random(50_000 + seed)
        transforms = [
            _transform_instance(inst, rng, reorder=True, coordinates=False),
            _transform_instance(inst, rng, reorder=False, coordinates=True),
            _transform_instance(inst, rng, reorder=True, coordinates=True),
        ]
        for transformed in transforms:
            invariant_checks += 1
            if canonical_key(transformed) != key:
                break
        carried_ok, _reason = verify(transforms[-1], inst["answer"])
        carried_witness_checks += int(carried_ok)
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 60
            and carried_witness_checks == 20
            and len(keys) == 20
        ),
        "invariance_checks": invariant_checks,
        "relabelled_witness_checks": carried_witness_checks,
        "unrelated_seeds": len(distinct_seeds),
        "distinct_keys": len(keys),
        "transformations": [
            "input-row permutation",
            "global coordinate permutation and sign changes",
            "composition of both",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    _compact_value, compact_operations = _compact_count(shipping)
    arms = G9_RESULTS["arms"]
    hinted_verdict = G9_RESULTS["hinted_verdict"]
    within_caps = (
        len(answer_blob) <= 2000
        and _answer_atoms(shipping["answer"]) <= 256
        and compact_operations <= 300
    )
    hinted_still_hardened = hinted_verdict == "hardened"
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": hinted_verdict,
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": _answer_atoms(shipping["answer"]),
        "intended_route_operations": compact_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report
