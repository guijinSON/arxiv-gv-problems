"""Exact Track-B Hadamard factorization on a projective line.

This module turns Proposition 3.4 of arXiv:2510.05231 into a bounded witness
problem.  The instance is a projective line L=span(1,x) over Q and a target
point p.  A witness is a sorted rational vector (t_i) such that

    p = (1+t_0*x) star ... star (1+t_(n-1)*x)

projectively.  Instances are inverse-generated on a shared arithmetic lattice.
The product is a rising factorial, which is the intended no-tool shortcut.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time
from fractions import Fraction


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "rational",
    "native_objects": [
        "projective line over Q",
        "rational points on the line",
        "coordinatewise Hadamard product",
    ],
    "verification_operations": [
        "exact rational comparison",
        "exact affine-line parametrization",
        "exact coordinatewise multiplication",
        "projective cross multiplication",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Invert the line coordinates to expose a shared arithmetic lattice and "
        "a rising-factorial ratio; without it one must interpolate and factor "
        "a dense polynomial exactly."
    ),
    "hardness_basis": (
        "Track B: Proposition 3.4 identifies line-Hadamard decomposition with "
        "degree-n interpolation/factorization; modular Newton interpolation plus "
        "bounded rational-root scanning runs in O(n^2+nHD) and the shipping "
        "selftest measures 212,015 exact-field operations (median 0.0042 seconds) "
        "at the candidate easy preset, while "
        "the arithmetic-lattice route uses at most 2n+2ceil(log2 n)+12 exact "
        "arithmetic operations."
    ),
    "max_answer_tokens": 63,
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

DIFFICULTY = {
    "demo": {"n": 3, "max_num": 16, "max_den": 3},
    "easy": {"n": 31, "max_num": 512, "max_den": 5},
    "medium": {"n": 63, "max_num": 1536, "max_den": 7},
    "hard": {"n": 127, "max_num": 4096, "max_den": 8},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Hint: The inverse line coordinates and the factor parameters lie on one "
    "arithmetic lattice, making the cleared target coordinates a rising-factorial sequence."
)
PLACEBO_HINT = (
    "Hint: The rational coordinates and the factor parameters use exact reduced "
    "forms, making careful normalization important throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing list of exactly n positive reduced rationals; "
        "each is [numerator,denominator] with numerator <= the instance max_num "
        "and denominator <= the instance max_den."
    ),
    "bounds": {
        "max_length": 127,
        "shipping_max_numerator": 4096,
        "shipping_max_denominator": 8,
        "positive": 1,
        "strictly_increasing": 1,
    },
}

# Filled from the script-owned transcripts after the three hardening runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 2},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and native object. Section 2.2, Definition 2.2 defines the
X-Hadamard rank using coordinatewise products in a fixed projective basis.
Section 3, Lemma 3.3 and Proposition 3.4 specialize this to a projective line
L avoiding Delta_(N-2): L^star N is all of P^N and no closure is needed.  The
module hands the solver precisely such a line over Q, parametrized by
q(t)=1+t*x, and a target p; no graph, finite-field, or discrete surrogate is
used.  Pairwise-distinct nonzero coordinates of x ensure that any point of L
has at most one zero coordinate, which is the lemma's exact hypothesis.

Certificate-production test. The rational factor parameters are sampled first
on a common arithmetic lattice, their line points are formed, and only then is
the target made by exact coordinatewise multiplication.  This is inverse
generation/composition of identities, never solution of the emitted instance.
Verification reconstructs every q(t), multiplies with Fraction arithmetic, and
checks equality to p by projective cross multiplication.  It never reads the
planted answer.

Step-0 hardness decision. The paper proves existence and dimension statements,
not average-case computational hardness.  Track A is therefore not claimed.
For a general line instance, writing f(z)=product_i(1+t_i z) turns the n+1
target coordinates into evaluations of a degree-n polynomial.  The reference
algorithm interpolates f modulo a prime and scans the bounded rational language
for its roots -1/t_i.  It is polynomial in the declared bounds and succeeds on
every generated instance, so it is reported openly as the Track-B reference
algorithm.  Its measured cost is compared with the compact route in selftest.

Compact route. Write the inverse line coordinates as s_j=1/x_j.  Construction
uses s_j=s_0+j*h and t_i=t_0+i*h.  Consequently
p(s)=product_i(1+t_i/s), and for adjacent s,s+h the cleared ratio
R=(p(s+h)/p(s))*((s+h)/s)^n equals (s+t_0+n*h)/(s+t_0).  One exact rearrangement
recovers t_0, after which repeated addition emits the certificate.  This is a
change-of-variables/rising-factorial insight; the renderer never states the
ratio or the rearrangement.

Easy regimes. Section 2 notes that toric varieties themselves are
Hadamard-idempotent; asking for products of points on a toric X would be trivial
because the target remains on X (and the all-ones point pads a fixed factor
count).  We avoid that fatal version.  Example 3.1 gives a direct coordinate
formula with one rank-two tensor factor per slice; using it would make the
mechanical and compact routes comparable.  Our line family instead uses the
paper's Proposition 3.4 interpolation object and measures the efficient method.

Attacks. Low/high parameter outliers fail because the plant is sampled in the
interior.  A one-factor greedy approximation ignores degree n.  A same-origin
lattice ansatz notices the public lattice but guesses its origin, which is
independently sampled.  Uniform random restarts sample the full bounded,
strictly-increasing rational language.  None is the successful interpolation
algorithm; Track B requires that algorithm under reference_algorithm instead.

Canonicalization. Ambient coordinate reorderings preserve the projective line,
target and every witness. canonical_key sorts paired (x_j,p_j) coordinates and
hashes that exact multiset with the bounds. selftest checks permutations and
their compositions with carried witnesses over 20 seeds, plus 20-seed
distinctness. General PGL coordinate changes are not canonicalized because the
fixed basis is part of Hadamard multiplication in Definition 2.2.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_REFERENCE_PRIME = 1_000_003
_ENUMERATION_CAP = 50_000


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _fraction(pair: object) -> Fraction | None:
    if not isinstance(pair, list) or len(pair) != 2:
        return None
    a, b = pair
    if isinstance(a, bool) or isinstance(b, bool):
        return None
    if not isinstance(a, int) or not isinstance(b, int) or b <= 0:
        return None
    if math.gcd(a, b) != 1:
        return None
    return Fraction(a, b)


@functools.lru_cache(maxsize=32)
def _candidate_pool(max_num: int, max_den: int) -> tuple[tuple[int, int], ...]:
    values = {
        (num // math.gcd(num, den), den // math.gcd(num, den))
        for den in range(1, max_den + 1)
        for num in range(1, max_num + 1)
    }
    return tuple(sorted(values, key=lambda p: Fraction(p[0], p[1])))


def _choose_lattice(n: int, max_num: int, max_den: int,
                    rng: random.Random) -> tuple[Fraction, Fraction, Fraction]:
    """Return (t0, step, s0) with all t_i inside the certificate bounds."""
    den = rng.randint(2, max_den) if max_den >= 2 else 1
    max_step = max(1, max_num // max(4 * n, 1))
    steps = [g for g in range(1, max_step + 1) if math.gcd(g, den) == 1]
    step_num = rng.choice(steps or [1])
    room = max_num - (n - 1) * step_num
    if room < 3:
        raise ValueError("max_num is too small for n and max_den")
    low = min(max(2, max_num // 5), room - 1)
    start_num = rng.randint(low, room)

    node_room = max(max_num, room + n * step_num)
    node_num = rng.randint(1, max(1, node_room - n * step_num))
    if node_num == start_num:
        node_num = (node_num % max(2, node_room - n * step_num)) + 1
    return (Fraction(start_num, den), Fraction(step_num, den),
            Fraction(node_num, den))


def make_instance(n: int, seed: int = 0, max_num: int = 4096,
                  max_den: int = 8, **params) -> dict:
    """Inverse-generate an exact line-Hadamard decomposition."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("max_num", max_num), ("max_den", max_den)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 2:
        raise ValueError("n must be at least 2")
    if max_num < n + 2 or max_den < 1:
        raise ValueError("certificate bounds are too small")
    if max_num * max_den >= _REFERENCE_PRIME:
        raise ValueError("max_num*max_den must be below 1000003")

    rng = random.Random(seed)
    t0, step, s0 = _choose_lattice(n, max_num, max_den, rng)
    parameters = [t0 + i * step for i in range(n)]
    inverse_nodes = [s0 + j * step for j in range(n + 1)]
    if any(s <= 0 for s in inverse_nodes):
        raise AssertionError("internal nonpositive inverse node")
    direction = [1 / s for s in inverse_nodes]

    target = []
    for x in direction:
        value = Fraction(1)
        for t in parameters:
            value *= 1 + t * x
        target.append(value)

    return {
        "family": "Hadamard decomposition on a projective line over Q",
        "n": n,
        "max_num": max_num,
        "max_den": max_den,
        "line_direction": [_pair(x) for x in direction],
        "target": [_pair(p) for p in target],
        "answer": [_pair(t) for t in parameters],
    }


def render(inst: dict) -> str:
    """Return the complete, self-contained solver prompt."""
    rows = "\n".join(
        f"{j}: x={x[0]}/{x[1]}   p={p[0]}/{p[1]}"
        for j, (x, p) in enumerate(zip(inst["line_direction"], inst["target"]))
    )
    statement = f"""Exact Hadamard decomposition on a projective line

All arithmetic is over the rational numbers. A rational is always written in
reduced form num/den with den>0. Vectors represent projective points: two
nonzero vectors are the same point when one is a single nonzero rational
multiple of the other. The Hadamard product of vectors is coordinatewise
multiplication.

The ambient projective space has {inst['n'] + 1} coordinates numbered
0,...,{inst['n']}. Let 1 be the all-ones vector and let x be the rational vector
listed below. The projective line L is the span of 1 and x. For a rational t,
use the fixed representative

    q(t) = 1 + t*x,

so coordinate j of q(t) is 1+t*x_j. The x_j are nonzero and pairwise distinct;
therefore a point of L has at most one zero coordinate.

Find exactly {inst['n']} positive rational parameters

    t_0 < t_1 < ... < t_{inst['n'] - 1}

such that q(t_0) Hadamard ... Hadamard q(t_{inst['n'] - 1}) is projectively
equal to the target p. Each t_i must be reduced, with numerator in
1,...,{inst['max_num']} and denominator in 1,...,{inst['max_den']}. Repeats are
not allowed. The order requirement removes the irrelevant permutation of the
factors. All coordinate data are exact:

{rows}

Give your final answer inside <answer></answer> tags as one JSON list of
{inst['n']} rational pairs [[num,den],...], in strictly increasing order.
Example format: <answer>[[3,2],[2,1],[5,2]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: object) -> object | None:
    """Parse the delimited JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (ValueError, TypeError):
        return None
    if not isinstance(answer, list):
        return None
    return answer


@functools.lru_cache(maxsize=65_536)
def _mod_inverse(denominator: int, prime: int = _REFERENCE_PRIME) -> int:
    return pow(denominator % prime, prime - 2, prime)


def _mod_fraction(value: Fraction, prime: int = _REFERENCE_PRIME) -> int:
    return value.numerator % prime * _mod_inverse(value.denominator, prime) % prime


def _decode_candidate(inst: dict, answer: object) -> tuple[list[Fraction] | None, str]:
    if answer == []:
        return None, "answer list is empty"
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if len(answer) != inst["n"]:
        return None, f"expected exactly {inst['n']} parameters"
    values = []
    for i, raw in enumerate(answer):
        value = _fraction(raw)
        if value is None:
            return None, f"parameter {i} is not a reduced [num,den] rational"
        if not (1 <= value.numerator <= inst["max_num"] and
                1 <= value.denominator <= inst["max_den"]):
            return None, f"parameter {i} is outside the declared bounds"
        values.append(value)
    if len(set(values)) != len(values):
        return None, "parameters must be distinct"
    if any(values[i] >= values[i + 1] for i in range(len(values) - 1)):
        return None, "parameters must be in strictly increasing order"
    return values, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any bounded rational decomposition, never the planted answer."""
    values, reason = _decode_candidate(inst, answer)
    if values is None:
        return False, reason

    direction = [Fraction(a, b) for a, b in inst["line_direction"]]
    target = [Fraction(a, b) for a, b in inst["target"]]

    # A modular mismatch is an exact rejection and makes the 200k-sample gate
    # inexpensive. A modular match is never accepted without the rational check.
    x0 = _mod_fraction(direction[0])
    t_mods = [_mod_fraction(t) for t in values]
    product0 = 1
    for t_mod in t_mods:
        product0 = product0 * (1 + t_mod * x0) % _REFERENCE_PRIME
    target0_mod = _mod_fraction(target[0])
    # Compare projectively against coordinate 1 modulo the reference prime.
    x1 = _mod_fraction(direction[1])
    product1 = 1
    for t_mod in t_mods:
        product1 = product1 * (1 + t_mod * x1) % _REFERENCE_PRIME
    target1_mod = _mod_fraction(target[1])
    if product0 * target1_mod % _REFERENCE_PRIME != product1 * target0_mod % _REFERENCE_PRIME:
        return False, "Hadamard product does not equal the target projectively"

    products = []
    for x in direction:
        value = Fraction(1)
        for t in values:
            value *= 1 + t * x
        products.append(value)
    if all(value == 0 for value in products):
        return False, "Hadamard product is the zero vector, not a projective point"
    pivot = next(i for i, value in enumerate(products) if value != 0)
    if target[pivot] == 0:
        return False, "Hadamard product has a different zero-coordinate pattern"
    for j in range(len(products)):
        if products[j] * target[pivot] != products[pivot] * target[j]:
            return False, "Hadamard product does not equal the target projectively"
    return True, "ok"


def _modular_candidate_survives(inst: dict, answer: list[list[int]]) -> bool:
    """Necessary projective check for already-grammatical sampled candidates."""
    prime = _REFERENCE_PRIME
    x0 = _mod_fraction(Fraction(*inst["line_direction"][0]))
    x1 = _mod_fraction(Fraction(*inst["line_direction"][1]))
    p0 = _mod_fraction(Fraction(*inst["target"][0]))
    p1 = _mod_fraction(Fraction(*inst["target"][1]))
    product0 = product1 = 1
    for num, den in answer:
        t_mod = num % prime * _mod_inverse(den, prime) % prime
        product0 = product0 * (1 + t_mod * x0) % prime
        product1 = product1 * (1 + t_mod * x1) % prime
    return product0 * p1 % prime == product1 * p0 % prime


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement's sorted distinct rational language."""
    pool = _candidate_pool(inst["max_num"], inst["max_den"])
    if inst["n"] > len(pool):
        raise ValueError("certificate language is smaller than n")
    indices = sorted(rng.sample(range(len(pool)), inst["n"]))
    return [[pool[i][0], pool[i][1]] for i in indices]


def search_space(inst: dict) -> int:
    pool_size = len(_candidate_pool(inst["max_num"], inst["max_den"]))
    return math.comb(pool_size, inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force only genuinely small certificate spaces."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    pool = _candidate_pool(inst["max_num"], inst["max_den"])
    count = 0
    for combo in itertools.combinations(pool, inst["n"]):
        candidate = [[a, b] for a, b in combo]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize every ambient-coordinate reordering."""
    coordinates = sorted(
        (tuple(x), tuple(p))
        for x, p in zip(inst["line_direction"], inst["target"])
    )
    payload = {
        "n": inst["n"],
        "max_num": inst["max_num"],
        "max_den": inst["max_den"],
        "coordinates": coordinates,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the bounded rational haystack while keeping n and answer atoms fixed."""
    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = int(clean["n"])
    max_num = int(clean.get("max_num", 4096))
    max_den = int(clean.get("max_den", 8))
    nxt = max_num * 2
    if nxt * max_den >= _REFERENCE_PRIME:
        return "cap_bound"
    # At 127 entries, ten-digit numerators approach the 2000-character cap.
    if n >= 100 and nxt > 100_000_000:
        return "cap_bound"
    return {"n": n, "max_num": nxt, "max_den": max_den}


def _interpolate_mod(xs: list[int], ys: list[int], prime: int,
                     counter: list[int]) -> list[int]:
    """Newton interpolation, returned in ascending monomial order."""
    size = len(xs)
    dd = list(ys)
    inv_cost = 2 * math.ceil(math.log2(prime))
    for order in range(1, size):
        for i in range(size - 1, order - 1, -1):
            numerator = (dd[i] - dd[i - 1]) % prime
            denominator = (xs[i] - xs[i - order]) % prime
            dd[i] = numerator * pow(denominator, prime - 2, prime) % prime
            counter[0] += 3 + inv_cost

    coeff = [dd[-1]]
    for k in range(size - 2, -1, -1):
        new = [0] * (len(coeff) + 1)
        for i, value in enumerate(coeff):
            new[i] = (new[i] - xs[k] * value) % prime
            new[i + 1] = (new[i + 1] + value) % prime
            counter[0] += 3
        new[0] = (new[0] + dd[k]) % prime
        counter[0] += 1
        coeff = new
    return coeff


def _reference_algorithm(inst: dict) -> tuple[object | None, int, float]:
    """Generic modular interpolation plus bounded rational-root scan."""
    started = time.perf_counter()
    prime = _REFERENCE_PRIME
    counter = [0]
    xs = []
    ys = []
    inv_cost = 2 * math.ceil(math.log2(prime))
    for x_raw, y_raw in zip(inst["line_direction"], inst["target"]):
        x = Fraction(x_raw[0], x_raw[1])
        y = Fraction(y_raw[0], y_raw[1])
        xs.append(_mod_fraction(x, prime))
        ys.append(_mod_fraction(y, prime))
        counter[0] += 2 * (2 + inv_cost)
    coeff = _interpolate_mod(xs, ys, prime, counter)

    roots = []
    for num, den in _candidate_pool(inst["max_num"], inst["max_den"]):
        z = (-den * pow(num, prime - 2, prime)) % prime
        counter[0] += 1 + inv_cost
        value = 0
        for c in reversed(coeff):
            value = (value * z + c) % prime
            counter[0] += 2
        if value == 0:
            roots.append([num, den])
    roots.sort(key=lambda p: Fraction(p[0], p[1]))
    candidate = roots if len(roots) == inst["n"] else None
    elapsed = time.perf_counter() - started
    return candidate, counter[0], elapsed


def _compact_route(inst: dict) -> tuple[object | None, int]:
    """Recover the lattice origin from two adjacent coordinates."""
    n = inst["n"]
    nodes = [1 / Fraction(a, b) for a, b in inst["line_direction"]]
    target = [Fraction(a, b) for a, b in inst["target"]]
    order = sorted(range(len(nodes)), key=lambda i: nodes[i])
    i0, i1 = order[0], order[1]
    s0, s1 = nodes[i0], nodes[i1]
    step = s1 - s0
    ratio = target[i1] / target[i0] * (s1 / s0) ** n
    if ratio == 1:
        return None, 0
    t0 = n * step / (ratio - 1) - s0
    values = [t0 + i * step for i in range(n)]
    # Conservative arithmetic count: coordinate reciprocals and output additions
    # are included; sorting comparisons are not exact arithmetic operations.
    operations = 2 * n + 2 * math.ceil(math.log2(max(2, n))) + 12
    return [_pair(v) for v in values], operations


def _low_end_attack(inst: dict) -> object:
    pool = _candidate_pool(inst["max_num"], inst["max_den"])
    return [[a, b] for a, b in pool[:inst["n"]]]


def _single_factor_greedy(inst: dict) -> object:
    x = Fraction(*inst["line_direction"][0])
    p = Fraction(*inst["target"][0])
    estimate = (p - 1) / x
    pool = _candidate_pool(inst["max_num"], inst["max_den"])
    # Use the nearest n legal single-factor estimates; this is intentionally the
    # natural wrong model p=1+t*x, not knowledge of the planted progression.
    nearest = sorted(pool, key=lambda q: abs(Fraction(q[0], q[1]) - estimate))[:inst["n"]]
    nearest.sort(key=lambda q: Fraction(q[0], q[1]))
    return [[a, b] for a, b in nearest]


def _same_origin_lattice_attack(inst: dict) -> object:
    nodes = sorted(1 / Fraction(a, b) for a, b in inst["line_direction"])
    step = nodes[1] - nodes[0]
    guesses = [nodes[0] + i * step for i in range(inst["n"])]
    raw = [_pair(v) for v in guesses]
    # Return an ordinary invalid candidate if public node numerators exceed the
    # bounded answer language; verify records the attack as a failure either way.
    return raw


def _random_restart_attack(inst: dict, seed: int, restarts: int = 256) -> object | None:
    rng = random.Random(seed ^ 0xA5A5_2510)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _permute_coordinates(inst: dict, permutation: list[int]) -> dict:
    out = dict(inst)
    out["line_direction"] = [inst["line_direction"][i] for i in permutation]
    out["target"] = [inst["target"][i] for i in permutation]
    out["answer"] = json.loads(json.dumps(inst["answer"]))
    return out


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(v) for v in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(v) for v in answer)
    return 1


def selftest() -> dict:
    """Run correctness, density, attacks, scaling, canonicalization and G9 gates."""
    report: dict[str, object] = {}

    # G1: every named preset across several seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 2025):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)

    # G2: five distinct corruption modes and five distinct rejection reasons.
    base = json.loads(json.dumps(inst["answer"]))
    corruptions = {}
    corruptions["drop_one"] = base[:-1]
    swapped = json.loads(json.dumps(base))
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap_adjacent"] = swapped
    duplicated = json.loads(json.dumps(base))
    duplicated[1] = duplicated[0]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    outside = json.loads(json.dumps(base))
    outside[-1] = [inst["max_num"] + 1, 1]
    corruptions["out_of_range"] = outside
    g2_results = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        g2_results[name] = {"rejected": not ok, "reason": why}
    reasons = [value["reason"] for value in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in g2_results.values()) and len(set(reasons)) == 5,
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose/fence response and raw tagged response.
    blob = json.dumps(inst["answer"], separators=(",", ":"))
    realistic = f"I used exact projective normalization.\n<answer>```json\n{blob}\n```</answer>\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed": parsed == inst["answer"],
    }

    # G4/G5 shipping density: structure-aware candidates already obey every
    # stated rational bound, length, distinctness and ordering constraint.
    samples = 200_000
    sample_rng = random.Random(0x251005231)
    hits = 0
    sample_prime = _REFERENCE_PRIME
    sample_x0 = _mod_fraction(Fraction(*inst["line_direction"][0]))
    sample_x1 = _mod_fraction(Fraction(*inst["line_direction"][1]))
    sample_p0 = _mod_fraction(Fraction(*inst["target"][0]))
    sample_p1 = _mod_fraction(Fraction(*inst["target"][1]))
    sample_started = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, sample_rng)
        # Every sampled candidate already satisfies the grammar. A modular
        # mismatch proves exact invalidity; survivors go through full verify.
        product0 = product1 = 1
        for num, den in candidate:
            t_mod = num % sample_prime * _mod_inverse(den, sample_prime) % sample_prime
            product0 = product0 * (1 + t_mod * sample_x0) % sample_prime
            product1 = product1 * (1 + t_mod * sample_x1) % sample_prime
        survives = product0 * sample_p1 % sample_prime == product1 * sample_p0 % sample_prime
        if survives and verify(inst, candidate)[0]:
            hits += 1
    sample_elapsed = time.perf_counter() - sample_started
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": str(search_space(inst)),
        "structure_aware": True,
        "wall_clock_sec": round(sample_elapsed, 6),
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)

    # Measure the successful generic method on eight independent shipping seeds.
    ref_successes = 0
    ref_ops = []
    ref_times = []
    reference_records = []
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **shipping_params)
        candidate, operations, elapsed = _reference_algorithm(attack_inst)
        ok = candidate is not None and verify(attack_inst, candidate)[0]
        ref_successes += int(ok)
        ref_ops.append(operations)
        ref_times.append(elapsed)
        reference_records.append({
            "seed": 10_000 + seed,
            "solved": ok,
            "operations": operations,
            "wall_clock_sec": round(elapsed, 6),
        })

    report["G5_density_and_baseline_cost"] = {
        "pass": hits / samples < 1e-6 and ref_successes == 8 and demo_count is not None,
        "shipping_density": {
            "hits": hits,
            "samples": samples,
            "observed_fraction": hits / samples,
        },
        "exact_demo_solution_count": demo_count,
        "exact_demo_candidate_space": search_space(demo_inst),
        "baseline_attack": "modular Newton interpolation plus bounded rational-root scan",
        "baseline_successes": ref_successes,
        "baseline_attempts": 8,
        "median_wall_clock_sec": round(statistics.median(ref_times), 6),
        "max_wall_clock_sec": round(max(ref_times), 6),
        "median_exact_field_operations": int(statistics.median(ref_ops)),
        "records": reference_records,
    }

    # G6: four failing in-context attacks; successful polynomial interpolation
    # is deliberately a sibling reference_algorithm, as Track B requires.
    attack_results = {
        "outlier_lowest_parameters": {"successes": 0, "attempts": 8},
        "greedy_single_factor_fit": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "same_lattice_origin_ansatz": {"successes": 0, "attempts": 8},
    }
    compact_successes = 0
    compact_ops = []
    for seed in range(8):
        attack_inst = make_instance(seed=20_000 + seed, **shipping_params)
        candidates = {
            "outlier_lowest_parameters": _low_end_attack(attack_inst),
            "greedy_single_factor_fit": _single_factor_greedy(attack_inst),
            "random_restart_256": _random_restart_attack(attack_inst, seed),
            "same_lattice_origin_ansatz": _same_origin_lattice_attack(attack_inst),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        compact, operations = _compact_route(attack_inst)
        compact_successes += int(compact is not None and verify(attack_inst, compact)[0])
        compact_ops.append(operations)
    all_failed = all(v["successes"] == 0 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "modular Newton interpolation plus bounded rational-root scan",
            "complexity": "O(n^2+n*H*D) exact finite-field operations",
            "wall_clock_sec_median": round(statistics.median(ref_times), 6),
            "operations_median": int(statistics.median(ref_ops)),
            "solves": f"{ref_successes}/8, as expected",
        },
        "compact_route": {
            "name": "inverse-coordinate arithmetic-lattice rising-factorial ratio",
            "successes": compact_successes,
            "attempts": 8,
            "max_exact_arithmetic_operations": max(compact_ops),
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["max_num"] *= 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verification": doubled_why,
        "escalation_axis": "max_num at fixed n after the named ladder",
    }

    invariant = 0
    carried = 0
    for seed in range(20):
        original = make_instance(seed=30_000 + seed, **shipping_params)
        permutation = list(range(original["n"] + 1))
        random.Random(seed ^ 0xC0FFEE).shuffle(permutation)
        transformed = _permute_coordinates(original, permutation)
        if canonical_key(original) == canonical_key(transformed):
            invariant += 1
        if verify(transformed, original["answer"])[0]:
            carried += 1
        # Compose with a second independently sampled coordinate permutation.
        second = list(range(original["n"] + 1))
        random.Random(seed ^ 0xBAD5EED).shuffle(second)
        composed = _permute_coordinates(transformed, second)
        if canonical_key(original) != canonical_key(composed):
            invariant -= 1000
        if not verify(composed, original["answer"])[0]:
            carried -= 1000
    unrelated = {
        canonical_key(make_instance(seed=40_000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(unrelated) == 20,
        "invariant_coordinate_permutations_and_compositions": invariant,
        "carried_witnesses_verified": carried,
        "distinct_unrelated_keys": len(unrelated),
        "unrelated_attempts": 20,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    _, intended_operations = _compact_route(inst)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    hinted_rate = arms["hinted"].get("solved", 0) / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"].get("solved", 0) / placebo_attempts if placebo_attempts else 0.0
    hinted_hardened = G9_ORACLE_RESULTS.get("hinted_verdict") == "hardened"
    within_caps = (answer_chars <= 2000 and answer_elements <= 256 and
                   intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "pending"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
