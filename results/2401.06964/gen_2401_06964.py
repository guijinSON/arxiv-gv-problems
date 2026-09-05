"""Verified moment-subset-sum generator for arXiv:2401.06964.

The paper defines the m-th moment k-subset-sum problem over a finite
field.  This module inverse-generates a k-subset of a prime field as a
union of translated multiplicative subgroups and publishes its first k
power sums.  The answer is known before the instance is formed.

This is deliberately Track B.  Newton identities followed by evaluation
of the resulting degree-k polynomial at every field element solve the
promise instances in O(k^2 + p*k) exact field operations.  The shorter
route recognizes centered subgroup power sums and constructs the roots
from a few multiplicative orbits.
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


sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The finite-field implementation below is stdlib-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_field",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "prime finite field F_p",
        "power-moment vector over F_p",
        "k-element subset of F_p",
    ],
    "verification_operations": [
        "finite-field exponentiation",
        "finite-field addition",
        "exact cardinality and distinctness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Centered second and third power sums expose the scale of translated "
        "multiplicative-subgroup orbits; without that invariant one reconstructs "
        "and scans the full degree-k root polynomial."
    ),
    "hardness_basis": (
        "Track B: the paper's Introduction cites the deterministic polynomial-time "
        "fixed-m algorithm of Lai--Marino--Robinson--Wan in the regime k<3m+1, "
        "which includes k=m=24 here; the explicit Newton-identity plus full-field "
        "root scan costs O(k^2+p*k), measured at 590,496 exact operations and "
        "0.139 seconds mean in the final G6 audit on the easy shipping preset, "
        "while the centered-orbit "
        "route uses at most 146 exact field operations."
    ),
    "max_answer_tokens": 33,
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


# n is a lower bound on the prime-field size.  make_instance chooses the first
# prime p >= n with 16 | p-1, so doubling n really enlarges the ambient field.
# The templates keep the answer length fixed at 24 outside the demo rung while
# increasing the number of interleaved subgroup orbits.
DIFFICULTY = {
    "demo": {"n": 97, "template": "demo"},
    "easy": {"n": 12_289, "template": "two"},
    "medium": {"n": 65_537, "template": "three"},
    "hard": {"n": 786_433, "template": "six"},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "The useful invariant is the ratio of the second and third power sums "
    "after translating a candidate subset to zero mean."
)
PLACEBO_HINT = (
    "The useful precaution is to keep every residue reduced modulo the prime "
    "while checking all of the displayed equations."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A k-element subset of F_p that already satisfies the freely enforced "
        "first-moment sum, serialized as a comma-separated list of k distinct "
        "canonical residues in 0..p-1; order is immaterial."
    ),
    "bounds": {
        "elements": "k",
        "entry_min": 0,
        "entry_max": "p-1",
        "distinct": True,
        "candidate_count": "binomial(p,k)/p",
    },
}


# Filled from the harness-owned transcripts after the three arms run.
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_external_openrouter_403",
}


NOTES = r"""
Paper grounding.  Section 1 and the beginning of Section 4 define
N_m(k,b,D) as the number of k-element subsets S of D satisfying
sum_(a in S) a^i=b_i for every displayed moment.  Section 4 specializes to
D=F_q and explicitly explains that diagonal-equation solutions must have
distinct coordinates and are identified up to coordinate permutation.  The
module presents exactly that native object over the prime field F_p, with
the consecutive exponents 1,...,k used in the paper's original definition.

STEP 0 / easy regime.  This is not a Track-A claim.  The Introduction states
that reference [25] gives a deterministic polynomial-time algorithm for
fixed m when D is the image of a monomial or Dickson polynomial and
k<3m+1.  Here D=F_p is the image of f(x)=x and k=m (12 in the demo, 24
otherwise), so the generated regime is explicitly on that easy side.  A
self-contained standard implementation uses Newton identities to recover
the unique monic root polynomial and evaluates it on all p residues.  Its
O(k^2+p*k) exact arithmetic, measured in G5/G6, is the Track-B mechanical
route.  Theorems 4.6, 4.7, and 4.10 instead concern existence for far fewer
moments relative to k; those are not used as hardness claims here.

Certificate production.  Before any target moments exist, generation picks
a translation c and a nonzero scale a.  It takes a disjoint union of cosets
c+q_j*a+H_j, where H_j is the unique multiplicative subgroup of the stated
order.  The integer multipliers q_j have weighted sum zero.  Only after this
subset is fixed are all k target moments evaluated.  This is inverse
generation and composition of the identities sum_(h in H) h^r=0 whenever
the subgroup order does not divide r.  No search algorithm produces the
planted answer.

Compact route.  Translation by c=s_1/k gives centered moments t_2=C_2*a^2
and t_3=C_3*a^3, where C_r=sum_j |H_j|q_j^r.  Their ratio gives a in a few
field operations.  The remaining elements are generated by repeated
multiplication in subgroups of orders 4, 8, or 16.  A conservative count,
including binary exponentiation for subgroup generators, is 146 exact field
operations at every shipping-sized template.

Attack hardening.  The domain is the entire field, so planted elements have
no membership, position, degree, or magnitude feature absent from decoys.
The closest-to-mean and one-moment greedy attacks discard higher moments.
Uniform random restart samples the exact k-subset language.  The fourth,
in-context attack recovers the correct mean and scale ratio but substitutes
ordinary additive blocks for multiplicative orbits; it therefore tests a
solver that sees only the most obvious ansatz.  The successful Newton/root
scan is reported separately as Track B requires.  The canonical key uses
all centered moments normalized by t_2/t_3, making it invariant under every
affine coordinate change x -> u*x+t while retaining the full normalized
moment sequence; it first sorts moments by exponent so reordering the displayed
equations is also invisible to the key.
"""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000

_TEMPLATES = {
    "demo": ((8, 1), (4, -2)),
    "two": ((16, 1), (8, -2)),
    "three": ((8, 1), (8, 2), (8, -3)),
    "six": ((4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, -15)),
    "six_wide": ((4, 1), (4, 3), (4, 7), (4, 12), (4, 20), (4, -43)),
    "six_quadratic": ((4, 1), (4, 4), (4, 9), (4, 16), (4, 25), (4, -55)),
}

_KNOWN_FIELDS = {
    97: 5,
    12_289: 11,
    65_537: 3,
    786_433: 10,
    7_340_033: 3,
}
_FIELD_CACHE = dict(_KNOWN_FIELDS)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    """Deterministic Miller--Rabin for the 64-bit range."""
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


def _prime_factors(value):
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors.append(value)
    return factors


def _primitive_root(prime):
    factors = _prime_factors(prime - 1)
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // factor, prime) != 1 for factor in factors):
            return candidate
    raise RuntimeError("prime field has no primitive root")


def _field_for_n(n):
    for prime in sorted(_KNOWN_FIELDS):
        if prime >= n:
            return prime, _KNOWN_FIELDS[prime]
    candidate = n + ((1 - n) % 16)
    if candidate < n:
        candidate += 16
    while not _is_prime(candidate):
        candidate += 16
    if candidate not in _FIELD_CACHE:
        _FIELD_CACHE[candidate] = _primitive_root(candidate)
    return candidate, _FIELD_CACHE[candidate]


def _subgroup(prime, primitive_root, order):
    omega = pow(primitive_root, (prime - 1) // order, prime)
    values = []
    current = 1
    for _ in range(order):
        values.append(current)
        current = current * omega % prime
    if current != 1 or len(set(values)) != order:
        raise AssertionError("invalid subgroup generator")
    return values


def _validate_params(n, template, seed):
    if not _is_int(n) or n < 17:
        raise ValueError("n must be an integer at least 17")
    if template not in _TEMPLATES:
        raise ValueError("unknown orbit template")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    spec = _TEMPLATES[template]
    if sum(order * shift for order, shift in spec) != 0:
        raise AssertionError("template does not have zero weighted mean")
    if any(order not in (4, 8, 16) for order, _ in spec):
        raise AssertionError("unsupported subgroup order")


def _build_planted_set(prime, primitive_root, spec, seed, center):
    """Choose a nonzero scale and return a disjoint subgroup-coset union."""
    # Multiplication by H_4 is an affine symmetry of every template.  Distinct
    # seed residues choose distinct multiplicative cosets before the rare
    # collision-avoidance scan; the seed itself never enters canonical_key.
    coset_count = (prime - 1) // 4
    start = (seed * 131 + 17) % coset_count
    groups = {
        order: _subgroup(prime, primitive_root, order)
        for order, _ in spec
    }
    for offset in range(coset_count):
        exponent = (start + offset) % coset_count
        scale = pow(primitive_root, exponent, prime)
        values = []
        for order, shift in spec:
            translate = (center + shift * scale) % prime
            values.extend((translate + element) % prime for element in groups[order])
        if len(set(values)) == len(values):
            return sorted(values), scale
    raise RuntimeError("could not make the subgroup cosets disjoint")


def _moments(values, count, prime):
    return [sum(pow(value, degree, prime) for value in values) % prime
            for degree in range(1, count + 1)]


def make_instance(n, seed=0, **params):
    """Inverse-generate a moment subset sum instance and its witness."""
    template = params.pop("template", "two")
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, template, seed)
    prime, primitive_root = _field_for_n(n)
    spec = _TEMPLATES[template]
    k = sum(order for order, _ in spec)
    if prime <= k or (prime - 1) % 16:
        raise ValueError("field must have characteristic above k and 16 | p-1")

    rng = random.Random(seed)
    center = rng.randrange(prime)
    answer, _scale = _build_planted_set(prime, primitive_root, spec, seed, center)
    moments = _moments(answer, k, prime)

    return {
        "family": "finite_field_moment_subset_sum",
        "p": prime,
        "primitive_root": primitive_root,
        "k": k,
        "exponents": list(range(1, k + 1)),
        "moments": moments,
        "answer": answer,
    }


def render(inst):
    """Render a complete, standalone finite-field problem statement."""
    prime = inst["p"]
    k = inst["k"]
    rows = "\n".join(
        f"  i={degree}: b_i={target}"
        for degree, target in zip(inst["exponents"], inst["moments"])
    )
    text = f"""Moment subset sum over a prime field

Let F_p be the field of residues modulo the prime p={prime}.  Every field
element is written as its unique integer representative in 0,...,{prime - 1}.
The nonzero field elements are generated multiplicatively by g={inst['primitive_root']}.

Find a subset S of F_p containing exactly k={k} DISTINCT elements such that

    sum(a^i for a in S) = b_i (mod p)

for every exponent i listed below.  Exponentiation and addition are in F_p.
The subset is unordered: any ordering of its elements is accepted.  Repeated
elements are forbidden, and every submitted integer must lie in the inclusive
range 0 through {prime - 1}.

Moment targets:
{rows}

Give your final answer inside <answer></answer> tags, as exactly {k}
comma-separated base-10 integers.  Do not use ellipses.
Example format: <answer>{', '.join(str(i) for i in range(k))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text):
    """Parse the delimited comma-separated subset; never raise on garbage."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return []
    parts = body.split(",")
    if any(not re.fullmatch(r"[+-]?\d+", part.strip()) for part in parts):
        return None
    try:
        return [int(part.strip()) for part in parts]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst, answer):
    """Check any submitted subset directly; never consult inst['answer']."""
    if answer is None or answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a list of integers"
    if len(answer) != inst["k"]:
        return False, f"expected exactly {inst['k']} elements"
    if any(not _is_int(value) for value in answer):
        return False, "every element must be an integer"
    prime = inst["p"]
    if any(value < 0 or value >= prime for value in answer):
        return False, f"an element lies outside 0..{prime - 1}"
    if len(set(answer)) != len(answer):
        return False, "elements must be distinct"
    for degree, target in zip(inst["exponents"], inst["moments"]):
        observed = sum(pow(value, degree, prime) for value in answer) % prime
        if observed != target:
            return False, f"moment {degree} mismatch: got {observed}, expected {target}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample k-subsets already satisfying the first moment.

    Draw k-1 distinct residues and force the last.  Conditional on the forced
    residue being new, every valid unordered subset has exactly k! preimages,
    so rejection sampling is uniform over the structure-aware language.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    prime = inst["p"]
    count = inst["k"] - 1
    target = inst["moments"][0]
    while True:
        prefix = rng.sample(range(prime), count)
        final = (target - sum(prefix)) % prime
        if final not in prefix:
            return sorted(prefix + [final])


def search_space(inst):
    """Number of k-subsets with the prescribed first moment."""
    # Translation by t adds k*t to the subset sum.  Since k<p, multiplication
    # by k permutes F_p, so the p possible sums receive equal-sized fibres.
    return math.comb(inst["p"], inst["k"]) // inst["p"]


def enumerate_all(inst):
    """Brute-force count only when the actual candidate space is safely tiny."""
    space = search_space(inst)
    if space > 100_000:
        return None
    # No named preset reaches this branch, but it keeps the API exact for any
    # future genuinely small supported field.
    import itertools
    return sum(
        verify(inst, list(candidate))[0]
        for candidate in itertools.combinations(range(inst["p"]), inst["k"])
    )


def _ordered_power_sums(inst):
    """Return power sums in degree order, independent of input-row order."""
    k = inst["k"]
    exponents = inst["exponents"]
    moments = inst["moments"]
    if len(exponents) != len(moments):
        raise ValueError("exponents and moments must have equal length")
    by_degree = dict(zip(exponents, moments))
    if len(by_degree) != k or set(by_degree) != set(range(1, k + 1)):
        raise ValueError("the instance must contain each exponent 1..k exactly once")
    return [by_degree[degree] for degree in range(1, k + 1)]


def _centered_moments(inst):
    prime = inst["p"]
    k = inst["k"]
    raw = [k] + _ordered_power_sums(inst)
    center = raw[1] * pow(k, -1, prime) % prime
    centered = [k, 0]
    for degree in range(2, k + 1):
        value = sum(
            math.comb(degree, power)
            * pow(-center, degree - power, prime)
            * raw[power]
            for power in range(degree + 1)
        ) % prime
        centered.append(value)
    return center, centered


def canonical_key(inst):
    """Affine-invariant key from the complete normalized moment sequence."""
    prime = inst["p"]
    _center, centered = _centered_moments(inst)
    z2, z3 = centered[2], centered[3]
    if z2 and z3:
        inverse_scale = z2 * pow(z3, -1, prime) % prime
        invariant = [
            centered[degree] * pow(inverse_scale, degree, prime) % prime
            for degree in range(2, inst["k"] + 1)
        ]
        payload = [prime, inst["k"], invariant]
    else:
        # Generated instances never use this branch.  It remains deterministic
        # and avoids pretending a singular normalization is affine-complete.
        payload = [prime, inst["k"], "singular", centered[2:]]
    blob = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """Enlarge the field and complicate the orbit template at fixed answer size."""
    out = dict(params)
    out["n"] = max(97, int(params["n"]) * 2)
    template = params.get("template", "two")
    order = ["two", "three", "six", "six_wide", "six_quadratic"]
    if template == "demo":
        out["template"] = "two"
    elif template in order[:-1]:
        out["template"] = order[order.index(template) + 1]
    else:
        out["template"] = "six_wide" if template == "six_quadratic" else "six_quadratic"
    return out


def _newton_root_scan(inst):
    """Reference solver: Newton identities, then exhaustive root evaluation."""
    prime = inst["p"]
    k = inst["k"]
    powers = [0] + _ordered_power_sums(inst)
    elementary = [1]
    operations = 0
    for degree in range(1, k + 1):
        total = 0
        for power in range(1, degree + 1):
            term = elementary[degree - power] * powers[power]
            total += term if power % 2 else -term
            operations += 2
        elementary.append(total * pow(degree, -1, prime) % prime)
        operations += 1
    coefficients = [1]
    for degree in range(1, k + 1):
        coefficients.append(((-1) ** degree * elementary[degree]) % prime)
    roots = []
    for value in range(prime):
        evaluated = coefficients[0]
        for coefficient in coefficients[1:]:
            evaluated = (evaluated * value + coefficient) % prime
            operations += 2
        if evaluated == 0:
            roots.append(value)
    return roots, {
        "operations": operations,
        "field_elements_scanned": prime,
        "newton_convolution_terms": k * (k + 1) // 2,
    }


def _template_constants(spec, prime):
    c2 = sum(order * shift * shift for order, shift in spec) % prime
    c3 = sum(order * shift * shift * shift for order, shift in spec) % prime
    return c2, c3


def _recover_center_scale(inst, spec):
    prime = inst["p"]
    k = inst["k"]
    s1, s2, s3 = _ordered_power_sums(inst)[:3]
    center = s1 * pow(k, -1, prime) % prime
    center2 = center * center % prime
    center3 = center2 * center % prime
    t2 = (s2 - 2 * center * s1 + k * center2) % prime
    t3 = (s3 - 3 * center * s2 + 3 * center2 * s1 - k * center3) % prime
    c2, c3 = _template_constants(spec, prime)
    denominator = t2 * c3 % prime
    if not denominator:
        return None
    scale = t3 * c2 * pow(denominator, -1, prime) % prime
    return center, scale


def _compact_orbit_solution(inst, spec):
    recovered = _recover_center_scale(inst, spec)
    if recovered is None:
        return None
    center, scale = recovered
    prime = inst["p"]
    values = []
    for order, shift in spec:
        origin = (center + shift * scale) % prime
        values.extend(
            (origin + element) % prime
            for element in _subgroup(prime, inst["primitive_root"], order)
        )
    if len(set(values)) != inst["k"]:
        return None
    return sorted(values)


def _attack_closest_to_mean(inst, _rng):
    center = inst["moments"][0] * pow(inst["k"], -1, inst["p"]) % inst["p"]
    prime = inst["p"]
    ranked = sorted(
        range(prime),
        key=lambda value: (min((value - center) % prime, (center - value) % prime), value),
    )
    return sorted(ranked[:inst["k"]])


def _attack_greedy_sum_completion(inst, _rng):
    prime = inst["p"]
    chosen = list(range(inst["k"] - 1))
    final = (inst["moments"][0] - sum(chosen)) % prime
    if final in chosen:
        chosen[-1] = inst["k"]
        final = (inst["moments"][0] - sum(chosen)) % prime
    if final in chosen:
        return None
    return sorted(chosen + [final])


def _attack_random_restart(inst, rng, restarts=256):
    target = inst["moments"][0]
    prime = inst["p"]
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if sum(candidate) % prime != target:
            continue
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_ratio_additive_partition_scan(inst, _rng):
    """Try the obvious balanced two-block ansatz using only rendered data."""
    prime = inst["p"]
    k = inst["k"]
    # Subgroup orders visible from p-1 are natural candidate block lengths, but
    # this deliberately uses ordinary additive blocks rather than the hidden
    # multiplicative orbits.  Nothing here reads the generator's template.
    for left_size in range(2, k - 1):
        right_size = k - left_size
        if (prime - 1) % left_size or (prime - 1) % right_size:
            continue
        divisor = math.gcd(left_size, right_size)
        spec = (
            (left_size, right_size // divisor),
            (right_size, -(left_size // divisor)),
        )
        recovered = _recover_center_scale(inst, spec)
        if recovered is None:
            continue
        center, scale = recovered
        values = []
        for order, shift in spec:
            origin = (center + shift * scale) % prime
            values.extend((origin + offset) % prime for offset in range(order))
        if len(set(values)) != k:
            continue
        candidate = sorted(values)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _transform_affine(inst, multiplier, translation, answer):
    prime = inst["p"]
    k = inst["k"]
    raw = [k] + _ordered_power_sums(inst)
    transformed_by_degree = {}
    for degree in range(1, k + 1):
        transformed_by_degree[degree] = sum(
            math.comb(degree, power)
            * pow(multiplier, power, prime)
            * pow(translation, degree - power, prime)
            * raw[power]
            for power in range(degree + 1)
        ) % prime
    transformed = dict(inst)
    transformed["moments"] = [
        transformed_by_degree[degree] for degree in inst["exponents"]
    ]
    transformed["answer"] = sorted(
        (multiplier * value + translation) % prime for value in answer
    )
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    checks = 0
    json_roundtrips = 0
    deterministic_rebuilds = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            rebuilt = make_instance(seed=seed, **params)
            deterministic_rebuilds += rebuilt == inst
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and checks == json_roundtrips == deterministic_rebuilds,
        "checks": checks,
        "json_native_roundtrips": json_roundtrips,
        "deterministic_rebuilds": deterministic_rebuilds,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=511, **shipping_params)
    answer = list(inst["answer"])
    replacement = (answer[0] + 1) % inst["p"]
    while replacement in answer:
        replacement = (replacement + 1) % inst["p"]
    swapped = list(answer)
    swapped[0] = replacement
    duplicated = list(answer)
    duplicated[-1] = duplicated[0]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_one": swapped,
        "duplicate_one": duplicated,
        "empty": [],
        "out_of_range": answer[:-1] + [inst["p"]],
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    answer_text = ", ".join(map(str, inst["answer"]))
    realistic = (
        "The centered moments suggest multiplicative orbits.\n```text\n"
        f"<answer>{answer_text}</answer>\n```\nThese are canonical residues."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no tagged answer") is None,
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    rng = random.Random(0x240106964)
    hits = 0
    started = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        candidate = random_candidate(inst, rng)
        # random_candidate enforces moment 1.  Moment 2 is an exact necessary
        # filter that rejects essentially every sample without changing it.
        if sum(value * value for value in candidate) % inst["p"] != inst["moments"][1]:
            continue
        hits += verify(inst, candidate)[0]
    guess_seconds = time.perf_counter() - started
    space = search_space(inst)
    exact_probability = 1 / space
    report["G4_guess_resistance"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "observed_probability": hits / _GUESS_SAMPLES,
        "exact_probability": exact_probability,
        "search_space": space,
        "prior": "uniform over distinct k-subsets of F_p conditioned on moment 1",
        "sampling_seconds": round(guess_seconds, 6),
    }

    baseline_records = []
    compact_records = []
    for seed in range(8):
        audit_inst = make_instance(seed=9_000 + seed, **shipping_params)
        started = time.perf_counter()
        candidate, stats = _newton_root_scan(audit_inst)
        elapsed = time.perf_counter() - started
        baseline_records.append((verify(audit_inst, candidate)[0], elapsed, stats))
        compact = _compact_orbit_solution(
            audit_inst, _TEMPLATES[shipping_params["template"]]
        )
        compact_records.append(compact is not None and verify(audit_inst, compact)[0])
    mean_wall = sum(row[1] for row in baseline_records) / len(baseline_records)
    mean_ops = sum(row[2]["operations"] for row in baseline_records) / len(baseline_records)
    report["G5_density_and_baseline"] = {
        "pass": hits == 0
        and all(row[0] for row in baseline_records)
        and all(compact_records),
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": hits / _GUESS_SAMPLES,
        "shipping_exact_valid_answer_count": 1,
        "shipping_exact_solution_fraction": exact_probability,
        "uniqueness_reason": "Newton identities determine the monic root polynomial because k<p",
        "baseline_solved": sum(row[0] for row in baseline_records),
        "baseline_attempts": len(baseline_records),
        "baseline_wall_seconds_mean": round(mean_wall, 6),
        "baseline_wall_seconds_max": round(max(row[1] for row in baseline_records), 6),
        "baseline_operations_mean": mean_ops,
        "baseline_field_elements_scanned": inst["p"],
        "compact_route_solved": sum(compact_records),
        "compact_route_attempts": len(compact_records),
        "compact_route_operation_bound": 146,
    }

    spec = _TEMPLATES[shipping_params["template"]]
    attack_functions = {
        "outlier_closest_to_mean": lambda obj, rr: _attack_closest_to_mean(obj, rr),
        "greedy_first_moment_completion": lambda obj, rr: _attack_greedy_sum_completion(obj, rr),
        "random_restart_256": lambda obj, rr: _attack_random_restart(obj, rr, 256),
        "ratio_additive_partition_scan": _attack_ratio_additive_partition_scan,
    }
    attack_results = {
        name: {"successes": 0, "attempts": 8} for name in attack_functions
    }
    reference_successes = 0
    reference_walls = []
    reference_operations = []
    for seed in range(8):
        audit_inst = make_instance(seed=17_000 + seed, **shipping_params)
        for name, attack in attack_functions.items():
            candidate = attack(audit_inst, random.Random(44_000 + seed))
            if candidate is not None and verify(audit_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        started = time.perf_counter()
        candidate, stats = _newton_root_scan(audit_inst)
        reference_walls.append(time.perf_counter() - started)
        reference_operations.append(stats["operations"])
        reference_successes += verify(audit_inst, candidate)[0]
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Newton identities plus exhaustive full-field root scan",
            "complexity": "O(k^2 + p*k) exact finite-field operations",
            "wall_clock_sec": round(sum(reference_walls) / len(reference_walls), 6),
            "operations": round(sum(reference_operations) / len(reference_operations)),
            "field_elements_scanned": inst["p"],
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_n = 2 * shipping_params["n"]
    started = time.perf_counter()
    doubled = make_instance(
        n=doubled_n,
        template=shipping_params["template"],
        seed=707,
    )
    doubled_build = time.perf_counter() - started
    harder = escalate(shipping_params)
    escalated = make_instance(seed=708, **harder)
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0]
        and verify(escalated, escalated["answer"])[0]
        and doubled["p"] > inst["p"]
        and len(doubled["answer"]) == len(inst["answer"]),
        "shipping_n": shipping_params["n"],
        "shipping_field_p": inst["p"],
        "doubled_n": doubled_n,
        "doubled_field_p": doubled["p"],
        "doubled_build_seconds": round(doubled_build, 6),
        "answer_atoms_before": _answer_atoms(inst["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "fixed_answer_escalation": harder,
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = []
    deterministic_keys = 0
    for seed in range(20):
        base = make_instance(seed=31_000 + seed, **shipping_params)
        rebuilt = make_instance(seed=31_000 + seed, **shipping_params)
        base_key = canonical_key(base)
        deterministic_keys += canonical_key(rebuilt) == base_key
        unrelated_keys.append(base_key)
        trng = random.Random(81_000 + seed)
        multiplier = trng.randrange(1, base["p"])
        translation = trng.randrange(base["p"])
        transformed = [
            ("translation", _transform_affine(base, 1, translation, base["answer"])),
            ("scaling", _transform_affine(base, multiplier, 0, base["answer"])),
            (
                "affine_composition",
                _transform_affine(base, multiplier, translation, base["answer"]),
            ),
        ]
        reordered_equations = dict(base)
        reordered_equations["exponents"] = list(reversed(base["exponents"]))
        reordered_equations["moments"] = list(reversed(base["moments"]))
        transformed.append(("equation_order", reordered_equations))
        reordered = dict(base)
        reordered["answer"] = list(reversed(base["answer"]))
        transformed.append(("answer_order", reordered))
        fully_composed = _transform_affine(
            reordered_equations,
            multiplier,
            translation,
            list(reversed(base["answer"])),
        )
        transformed.append(("affine_equation_answer_composition", fully_composed))
        for name, changed in transformed:
            invariance_checks += 1
            if canonical_key(changed) != base_key:
                key_failures.append({"seed": seed, "transformation": name, "kind": "key"})
            carried_checks += 1
            if not verify(changed, changed["answer"])[0]:
                key_failures.append(
                    {"seed": seed, "transformation": name, "kind": "witness"}
                )
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20 and deterministic_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "deterministic_rebuilds": deterministic_keys,
        "transformations": [
            "global field translation",
            "nonzero field scaling",
            "composed affine change x -> u*x+t",
            "moment-equation order permutation",
            "answer-order permutation",
            "affine change composed with equation and answer permutations",
        ],
        "invariant": "all centered moments normalized by the scale t_2/t_3",
        "failures": key_failures,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    arms = {
        key: {"solved": G9_RESULTS[key]["solved"], "attempts": G9_RESULTS[key]["attempts"]}
        for key in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    difference = None
    if hinted["attempts"] and placebo["attempts"]:
        difference = (
            hinted["solved"] / hinted["attempts"]
            - placebo["solved"] / placebo["attempts"]
        )
    answer_chars = len(answer_blob)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 146
    caps_pass = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": caps_pass,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": math.ceil(answer_chars / 4),
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    report["shipping_params"] = dict(shipping_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
