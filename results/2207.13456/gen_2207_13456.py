"""Verified problem generator for arXiv:2207.13456.

The paper's Proposition 7.1 says that a binary form of degree 2k-1 and
Veronese rank k is identifiable over F_q when q >= 2k-1.  This module
inverse-generates such a point from k distinct points of the normal rational
curve, with all coefficients nonzero.  The requested certificate is the
paper's own witness: the k projective Veronese points spanning the target.

Generation never decomposes the target it emits.  It samples the witness first,
expands it, and then forgets the coefficients in the public answer.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "binary symmetric tensor over a prime finite field",
        "normal rational curve (binary Veronese variety)",
        "set of projective Veronese points spanning the tensor",
    ],
    "verification_operations": [
        "finite-field polynomial multiplication",
        "exact moment-recurrence substitution",
        "distinctness and range comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the hidden Veronese support is an affine translate of "
        "one multiplicative cycle; without that invariant one must reconstruct "
        "and factor the full annihilating polynomial."
    ),
    "hardness_basis": (
        "Track B: Prony--Hankel reconstruction followed by Cantor--Zassenhaus "
        "factorization is an expected polynomial-time reference algorithm "
        "(O(k^3 log p) here with naive dense arithmetic), measured over eight "
        "shipping seeds at 34,205 field operations and 0.004 seconds per "
        "instance; the cyclic invariant leaves 160 exact operations after it "
        "is recognized."
    ),
    "max_answer_tokens": 18,
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


# zeta has exact order n modulo p in every row.  The characteristic exceeds
# d=2n-1, as required by the q >= 2t+1 regime of Proposition 7.1.
DIFFICULTY = {
    "demo": {"n": 3, "p": 7, "zeta": 2},
    "easy": {"n": 20, "p": 61, "zeta": 8},
    "medium": {"n": 60, "p": 181, "zeta": 6},
    "hard": {"n": 80, "p": 25601, "zeta": 5},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Hint: The support is a translated multiplicative cycle whose nonzero "
    "spanning coefficients are a low-degree function on that cycle."
)
PLACEBO_HINT = (
    "Hint: Keep every finite-field reduction exact while checking all of the "
    "displayed moment coordinates."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One JSON object {\"support\":[a_1,...,a_k]} containing exactly k "
        "distinct residues in 0,...,p-1; order is immaterial and the support "
        "denotes the Veronese points (1,a,...,a^(2k-1))."
    ),
    "bounds": {
        "support_size": "k",
        "entry_range": "0 <= a < p",
        "all_distinct": True,
        "candidate_count": "binomial(p,k)",
        "atomic_elements": "k",
    },
}

# Filled from the script-owned runs after hardening.  These numbers are only
# diagnostics; G9(c)'s measured size/operation caps are the gate.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and native object: Section 2.2 defines the witness of a Waring
subspace as its rational points on the variety.  Section 2.3 identifies the
Veronese variety with pure symmetric tensors and homogeneous powers.  The
module therefore asks for Veronese points themselves, not a graph encoding.

Theorem used: Proposition 7.1 states that, for q >= 2t+1, every point of
P^(2t+1) having rank t+1 with respect to the normal rational curve V_(1,2t+1)
is Waring identifiable.  Here k=t+1 and d=2k-1.  The planted support has k
distinct affine points and every planted coefficient is nonzero.  Since every
set of at most d+1=2k points of a normal rational curve is independent, a
representation with fewer than k points would contradict independence of the
union.  Thus the rank is k and Proposition 7.1 makes the support unique.

What is easy and why this is Track B: the paper does not claim that recovering
the decomposition is hard; indeed its Introduction explicitly distinguishes
its geometric identifiability problem from the complexity problem of finding a
tensor decomposition.  Sections 3--5 give explicit constructions and fixed-
dimensional classifications, so using those displayed witnesses would be a
lookup.  This module instead uses the scalable binary family in Section 7, but
still declares Track B: the classical Prony method solves a k-by-k Hankel
system, obtains the annihilating polynomial, and factors it over F_p.  The
reference implementation uses exact modular elimination and randomized
Cantor--Zassenhaus splitting, and reports both operations and wall time.

Inverse construction and compact route: choose the order-k subgroup H=<zeta>,
a translation c, and nonzero coefficients W(h), where W is a sampled
polynomial of degree at most min(5,k-2).  Reject coefficients only when some
W(h) would vanish, form moments m_j=sum_h W(h)(c+h)^j, and store c+H as the
already-known witness.  Because the relevant nonconstant power sums over H
vanish, c=m_1/m_0.  Recognizing the cycle then reduces recovery to enumerating
c+<zeta>; no decomposition algorithm is run during generation.

Attacks: coefficient residues themselves do not resemble support points, a
consecutive-residue greedy guess misses the multiplicative cycle, 256 uniform
restarts per seed miss the unique witness, and the plausible small-ratio guess
<2> is not the planted order-20 subgroup at shipping.  Plants are not marked
among decoys: the instance contains only a dense moment vector.

Canonicalization: affine changes a -> u*a+t preserve the distinguished affine
chart and leave the spanning coefficients attached to the carried points;
global tensor scaling scales every coefficient.  canonical_key normalizes the
coefficient multiset up to permutation and common scale.  Full PGL(2,p)
canonicalization, including maps sending a support point to infinity, is not
attempted; the README records this as the strongest-cheap-invariant caveat.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _prime_divisors(value: int) -> list[int]:
    out = []
    d = 2
    while d * d <= value:
        if value % d == 0:
            out.append(d)
            while value % d == 0:
                value //= d
        d += 1
    if value > 1:
        out.append(value)
    return out


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    d = 3
    while d * d <= value:
        if value % d == 0:
            return False
        d += 2
    return True


def _has_exact_order(value: int, order: int, p: int) -> bool:
    return (
        pow(value, order, p) == 1
        and all(pow(value, order // r, p) != 1 for r in _prime_divisors(order))
    )


def _cycle(order: int, p: int, zeta: int) -> list[int]:
    out = []
    value = 1
    for _ in range(order):
        out.append(value)
        value = value * zeta % p
    return out


def _moments(p: int, k: int, support: list[int], weights: list[int]) -> list[int]:
    values = [0] * (2 * k)
    powers = [1] * len(support)
    for degree in range(2 * k):
        values[degree] = sum(
            weight * power for weight, power in zip(weights, powers)
        ) % p
        powers = [power * slope % p for power, slope in zip(powers, support)]
    return values


def _instance_from_terms(
    p: int,
    k: int,
    support: list[int],
    weights: list[int],
    *,
    zeta: int | None = None,
) -> dict:
    pairs = sorted(zip(support, weights))
    sorted_support = [a for a, _ in pairs]
    sorted_weights = [w % p for _, w in pairs]
    return {
        "p": p,
        "k": k,
        "degree": 2 * k - 1,
        "moments": _moments(p, k, sorted_support, sorted_weights),
        "answer": {"support": sorted_support},
        # Private construction data is never rendered or consulted by verify().
        # It lets canonical_key avoid decomposing an instance merely to compute
        # the unique coefficient invariant.
        "_weights": sorted_weights,
        "_zeta": zeta,
    }


def make_instance(
    n: int,
    seed: int = 0,
    p: int | None = None,
    zeta: int | None = None,
    **params,
) -> dict:
    """Plant a unique rank-n binary Veronese witness, then expand its moments."""
    del params
    k = int(n)
    if p is None or zeta is None:
        defaults = {
            3: (7, 2),
            20: (61, 8),
            60: (181, 6),
            80: (25601, 5),
            100: (8101, 2),
            120: (241, 3),
            160: (9601, 6),
        }
        if k not in defaults:
            raise ValueError("p and zeta are required for an unsupported n")
        default_p, default_zeta = defaults[k]
        p = default_p if p is None else int(p)
        zeta = default_zeta if zeta is None else int(zeta)
    p, zeta = int(p), int(zeta)
    if k < 3:
        raise ValueError("n must be at least 3")
    if not _is_prime(p):
        raise ValueError("p must be prime")
    if p < 2 * k - 1:
        raise ValueError("Proposition 7.1 requires p >= 2*n-1")
    if not _has_exact_order(zeta, k, p):
        raise ValueError("zeta must have exact multiplicative order n modulo p")

    rng = random.Random(seed)
    subgroup = _cycle(k, p, zeta)
    translation = rng.randrange(p)
    weight_degree = min(5, k - 2)
    while True:
        coefficients = [rng.randrange(1, p)] + [
            rng.randrange(p) for _ in range(weight_degree)
        ]
        if coefficients[-1] == 0:
            continue
        weights = []
        for h in subgroup:
            value = 0
            for coefficient in reversed(coefficients):
                value = (value * h + coefficient) % p
            weights.append(value)
        if all(weights):
            break
    support = [(translation + h) % p for h in subgroup]
    return _instance_from_terms(
        p, k, support, weights, zeta=zeta
    )


def render(inst: dict) -> str:
    p, k, degree = inst["p"], inst["k"], inst["degree"]
    moments = inst["moments"]
    width = 10
    rows = []
    for start in range(0, len(moments), width):
        end = min(start + width, len(moments))
        rows.append(
            f"m[{start}..{end - 1}]: "
            + " ".join(str(value) for value in moments[start:end])
        )

    lines = [
        "WARING WITNESS FOR A BINARY FORM OVER A FINITE FIELD",
        "",
        f"Work in the prime field F_{p}; every arithmetic operation is modulo {p}.",
        f"For a residue a, define its degree-{degree} affine Veronese point by",
        f"    v(a) = (1, a, a^2, ..., a^{degree}) in F_{p}^{degree + 1}.",
        "A set S of residues is a Waring witness for a target vector m when m",
        "lies in the F_p-linear span of {v(a): a in S}.  Equivalently, there",
        "exist field coefficients w_a such that m_j = sum_{a in S} w_a*a^j",
        f"for every j from 0 through {degree}.  The coefficients need not be output.",
        "",
        f"The target m has the following {degree + 1} coordinates:",
        *rows,
        "",
        f"Find a Waring witness containing exactly {k} distinct affine residues.",
        f"Each residue must be an integer from 0 through {p - 1}, inclusive.",
        "The order of the residues does not matter, repetitions are forbidden,",
        "and the point at projective infinity is not part of the requested witness.",
        "The instance is guaranteed to have Veronese rank exactly this size and",
        "to have a unique witness of this size.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as one JSON object",
            f"with a key named \"support\" whose value is a list of exactly {k} integers.",
            "Example shape: <answer>{\"support\":[2,9,14]}</answer>",
            "The example only shows the syntax; use the required number of residues.",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        payload = match.group(1).strip()
    else:
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
        payload = fence.group(1).strip() if fence else text.strip()
        start, end = payload.find("{"), payload.rfind("}")
        if start < 0 or end < start:
            return None
        payload = payload[start:end + 1]
    payload = re.sub(
        r"^```(?:json)?\s*|\s*```$", "", payload, flags=re.I | re.S
    ).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _polynomial_from_roots(roots: list[int], p: int) -> list[int]:
    """Ascending coefficients of product (x-root), exactly over F_p."""
    coefficients = [1]
    for root in roots:
        nxt = [0] * (len(coefficients) + 1)
        for index, coefficient in enumerate(coefficients):
            nxt[index] = (nxt[index] - root * coefficient) % p
            nxt[index + 1] = (nxt[index + 1] + coefficient) % p
        coefficients = nxt
    return coefficients


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check the witness by exact annihilating-polynomial substitution.

    If Q(x)=prod_{a in S}(x-a), a moment vector lies in span(v(a):a in S)
    exactly when each displayed length-(k+1) window satisfies Q's recurrence.
    The distinct roots make the corresponding Vandermonde matrix invertible.
    """
    k, p = inst["k"], inst["p"]
    if not isinstance(answer, dict):
        return False, "answer must be one JSON object"
    if set(answer) != {"support"}:
        return False, "answer must contain exactly the key 'support'"
    support = answer["support"]
    if not isinstance(support, list):
        return False, "support must be a JSON list"
    if not support:
        return False, "support is empty"
    if len(support) < k:
        return False, f"support has fewer than {k} residues"
    if len(support) > k:
        return False, f"support has more than {k} residues"
    if any(type(value) is not int for value in support):
        return False, "every support entry must be an integer"
    for index, value in enumerate(support):
        if not 0 <= value < p:
            return False, f"support entry {index} is outside 0..{p - 1}"
    if len(set(support)) != k:
        return False, "support residues must be distinct"

    annihilator = _polynomial_from_roots(support, p)
    moments = inst["moments"]
    for shift in range(k):
        value = sum(
            coefficient * moments[shift + degree]
            for degree, coefficient in enumerate(annihilator)
        ) % p
        if value:
            return False, f"support polynomial fails the moment recurrence at shift {shift}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return {"support": sorted(rng.sample(range(inst["p"]), inst["k"]))}


def search_space(inst: dict) -> int | None:
    return math.comb(inst["p"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 500_000:
        return None
    count = 0
    for support in itertools.combinations(range(inst["p"]), inst["k"]):
        if verify(inst, {"support": list(support)})[0]:
            count += 1
    return count


def _solve_square_mod(
    matrix: list[list[int]],
    rhs: list[int],
    p: int,
    counter: list[int] | None = None,
) -> list[int] | None:
    n = len(matrix)
    augmented = [
        [value % p for value in row] + [rhs[index] % p]
        for index, row in enumerate(matrix)
    ]
    for column in range(n):
        pivot = next((r for r in range(column, n) if augmented[r][column]), None)
        if pivot is None:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        inverse = pow(augmented[column][column], -1, p)
        if counter is not None:
            counter[0] += 1
        for j in range(column, n + 1):
            augmented[column][j] = augmented[column][j] * inverse % p
            if counter is not None:
                counter[0] += 1
        for row in range(n):
            if row == column or augmented[row][column] == 0:
                continue
            factor = augmented[row][column]
            for j in range(column, n + 1):
                augmented[row][j] = (
                    augmented[row][j] - factor * augmented[column][j]
                ) % p
                if counter is not None:
                    counter[0] += 2
    return [augmented[row][n] for row in range(n)]


def _trim(poly: list[int]) -> list[int]:
    out = poly[:]
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out


def _poly_divmod(
    dividend: list[int],
    divisor: list[int],
    p: int,
    counter: list[int],
) -> tuple[list[int], list[int]]:
    divisor = _trim([value % p for value in divisor])
    if divisor == [0]:
        raise ZeroDivisionError("zero polynomial")
    remainder = _trim([value % p for value in dividend])
    if len(remainder) < len(divisor):
        return [0], remainder
    quotient = [0] * (len(remainder) - len(divisor) + 1)
    inverse_lead = pow(divisor[-1], -1, p)
    counter[0] += 1
    while remainder != [0] and len(remainder) >= len(divisor):
        offset = len(remainder) - len(divisor)
        factor = remainder[-1] * inverse_lead % p
        counter[0] += 1
        quotient[offset] = factor
        for j, coefficient in enumerate(divisor):
            remainder[offset + j] = (
                remainder[offset + j] - factor * coefficient
            ) % p
            counter[0] += 2
        remainder = _trim(remainder)
    return _trim(quotient), remainder


def _poly_mul_mod(
    left: list[int],
    right: list[int],
    modulus: list[int],
    p: int,
    counter: list[int],
) -> list[int]:
    product = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if a == 0:
            continue
        for j, b in enumerate(right):
            product[i + j] = (product[i + j] + a * b) % p
            counter[0] += 2
    return _poly_divmod(product, modulus, p, counter)[1]


def _poly_pow_mod(
    base: list[int],
    exponent: int,
    modulus: list[int],
    p: int,
    counter: list[int],
) -> list[int]:
    result = [1]
    base = _poly_divmod(base, modulus, p, counter)[1]
    while exponent:
        if exponent & 1:
            result = _poly_mul_mod(result, base, modulus, p, counter)
        exponent >>= 1
        if exponent:
            base = _poly_mul_mod(base, base, modulus, p, counter)
    return result


def _poly_gcd(
    left: list[int], right: list[int], p: int, counter: list[int]
) -> list[int]:
    left, right = _trim(left), _trim(right)
    while right != [0]:
        _, remainder = _poly_divmod(left, right, p, counter)
        left, right = right, remainder
    inverse = pow(left[-1], -1, p)
    counter[0] += 1
    normalized = [coefficient * inverse % p for coefficient in left]
    counter[0] += len(left)
    return _trim(normalized)


def _cantor_zassenhaus_roots(
    polynomial: list[int], p: int, rng: random.Random, counter: list[int]
) -> list[int] | None:
    """Factor a squarefree, completely split polynomial into linear roots."""

    def split(poly: list[int]) -> list[int] | None:
        degree = len(poly) - 1
        if degree == 0:
            return []
        if degree == 1:
            counter[0] += 2
            return [(-poly[0] * pow(poly[1], -1, p)) % p]
        for _ in range(128):
            trial = [rng.randrange(p) for _ in range(degree)]
            common = _poly_gcd(poly, trial, p, counter)
            common_degree = len(common) - 1
            if 0 < common_degree < degree:
                quotient, remainder = _poly_divmod(poly, common, p, counter)
                if remainder != [0]:
                    return None
                left = split(common)
                right = split(quotient)
                return None if left is None or right is None else left + right

            powered = _poly_pow_mod(trial, (p - 1) // 2, poly, p, counter)
            if not powered:
                powered = [0]
            powered[0] = (powered[0] - 1) % p
            common = _poly_gcd(poly, powered, p, counter)
            common_degree = len(common) - 1
            if 0 < common_degree < degree:
                quotient, remainder = _poly_divmod(poly, common, p, counter)
                if remainder != [0]:
                    return None
                left = split(common)
                right = split(quotient)
                return None if left is None or right is None else left + right
        return None

    roots = split(_trim(polynomial))
    if roots is None or len(set(roots)) != len(polynomial) - 1:
        return None
    return sorted(roots)


def _prony_reference(inst: dict) -> tuple[dict | None, int]:
    """General exact recovery: Hankel recurrence, then CZ factorization."""
    k, p, moments = inst["k"], inst["p"], inst["moments"]
    counter = [0]
    hankel = [[moments[row + column] for column in range(k)] for row in range(k)]
    rhs = [(-moments[row + k]) % p for row in range(k)]
    recurrence = _solve_square_mod(hankel, rhs, p, counter)
    if recurrence is None:
        return None, counter[0]
    annihilator = recurrence + [1]
    seed = sum((index + 1) * value for index, value in enumerate(moments))
    roots = _cantor_zassenhaus_roots(
        annihilator, p, random.Random(seed), counter
    )
    if roots is None:
        return None, counter[0]
    candidate = {"support": roots}
    return (candidate if verify(inst, candidate)[0] else None), counter[0]


def _weights_for_support(inst: dict, support: list[int]) -> list[int] | None:
    p, k = inst["p"], inst["k"]
    matrix = [[pow(slope, degree, p) for slope in support] for degree in range(k)]
    return _solve_square_mod(matrix, inst["moments"][:k], p)


def _canonical_weight_multiset(weights: list[int], p: int) -> tuple[int, ...]:
    candidates = []
    for anchor in weights:
        inverse = pow(anchor, -1, p)
        candidates.append(tuple(sorted(weight * inverse % p for weight in weights)))
    return min(candidates)


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant under affine-coordinate and scalar relabelling."""
    support = inst["answer"]["support"]
    weights = inst.get("_weights")
    if weights is None:
        weights = _weights_for_support(inst, support)
    if weights is None or any(weight == 0 for weight in weights):
        payload = [inst["p"], inst["k"], "singular"]
    else:
        payload = [
            inst["p"],
            inst["k"],
            list(_canonical_weight_multiset(weights, inst["p"])),
        ]
    raw = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 80))
    if n < 100:
        return {"n": 100, "p": 8101, "zeta": 2}
    if n < 120:
        return {"n": 120, "p": 241, "zeta": 3}
    # The next supported rung needs at least 2n+order-discovery >300 exact
    # operations on the compact route.  The mathematics scales; the no-tool
    # effort cap is what stops this ladder.
    return "cap_bound"


# ---------------------------------------------------------------------------
# Compact route, adversaries, transformations, and gates


def _pow_operation_count(exponent: int) -> int:
    # Left-to-right binary modular powering: one square per bit and one multiply
    # per 1-bit.  This deliberately overcounts the initial assignment.
    return exponent.bit_length() + exponent.bit_count()


def _compact_route_operations(inst: dict) -> int:
    k, zeta = inst["k"], inst["_zeta"]
    order_tests = [k] + [k // r for r in _prime_divisors(k)]
    discovery = sum(
        _pow_operation_count(exponent)
        for candidate in range(2, zeta + 1)
        for exponent in order_tests
    )
    # inversion+multiply for m1/m0, k translations, k-1 cycle products
    return discovery + 2 + k + (k - 1)


def _compact_candidate(inst: dict) -> tuple[dict, int]:
    p, k, zeta = inst["p"], inst["k"], inst["_zeta"]
    translation = inst["moments"][1] * pow(inst["moments"][0], -1, p) % p
    support = sorted((translation + h) % p for h in _cycle(k, p, zeta))
    return {"support": support}, _compact_route_operations(inst)


def _fill_distinct(values, p: int, k: int) -> list[int]:
    out = []
    seen = set()
    for value in itertools.chain(values, range(p)):
        value %= p
        if value not in seen:
            seen.add(value)
            out.append(value)
            if len(out) == k:
                return sorted(out)
    raise RuntimeError("not enough residues")


def _attack_coefficient_outliers(inst: dict) -> dict:
    ranked = sorted(inst["moments"], key=lambda x: min(x, inst["p"] - x))
    return {"support": _fill_distinct(ranked, inst["p"], inst["k"])}


def _attack_consecutive_greedy(inst: dict) -> dict:
    p, k = inst["p"], inst["k"]
    center = inst["moments"][1] * pow(inst["moments"][0], -1, p) % p
    values = [(center + offset) % p for offset in range(k)]
    return {"support": sorted(values)}


def _attack_symmetric_nearest(inst: dict) -> dict:
    p, k = inst["p"], inst["k"]
    center = inst["moments"][1] * pow(inst["moments"][0], -1, p) % p
    offsets = [1, -1]
    values = []
    radius = 1
    while len(values) < k:
        values.extend([(center + radius) % p, (center - radius) % p])
        radius += 1
    return {"support": sorted(values[:k])}


def _attack_ratio_two(inst: dict) -> dict:
    p, k = inst["p"], inst["k"]
    center = inst["moments"][1] * pow(inst["moments"][0], -1, p) % p
    powers = []
    value = 1
    for _ in range(k):
        powers.append((center + value) % p)
        value = 2 * value % p
    return {"support": _fill_distinct(powers, p, k)}


def _affine_transform(inst: dict, u: int, t: int, scale: int = 1) -> dict:
    p, k = inst["p"], inst["k"]
    support = inst["answer"]["support"]
    weights = inst.get("_weights") or _weights_for_support(inst, support)
    if weights is None:
        raise ValueError("could not carry weights")
    transformed_support = [(u * slope + t) % p for slope in support]
    transformed_weights = [(scale * weight) % p for weight in weights]
    return _instance_from_terms(p, k, transformed_support, transformed_weights)


def _answer_elements(answer) -> int:
    if isinstance(answer, dict):
        return sum(_answer_elements(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_elements(value) for value in answer)
    return 1


def selftest() -> dict:
    report = {}

    # G1: every named preset, multiple seeds, theorem conditions, and the compact
    # identity are checked independently of the planted-answer verification.
    failures = []
    theorem_checks = 0
    compact_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            theorem_ok = (
                inst["p"] >= inst["degree"]
                and len(set(inst["answer"]["support"])) == inst["k"]
                and all(inst["_weights"])
            )
            theorem_checks += 1
            compact, _ = _compact_candidate(inst)
            compact_ok = compact == inst["answer"] and verify(inst, compact)[0]
            compact_checks += 1
            if not ok or not theorem_ok or not compact_ok:
                failures.append(
                    {
                        "preset": preset,
                        "seed": seed,
                        "reason": reason,
                        "theorem_conditions": theorem_ok,
                        "compact_identity": compact_ok,
                    }
                )
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": 12,
        "theorem_condition_checks": theorem_checks,
        "compact_identity_checks": compact_checks,
        "failures": failures,
    }

    # G2: a set reordering remains valid; five genuine corruptions are routed to
    # distinct failures, including replacement (swap) of one set member.
    small = make_instance(seed=314159, **DIFFICULTY["easy"])
    planted = small["answer"]["support"]
    replacement = next(value for value in range(small["p"]) if value not in planted)
    swapped_member = planted[:]
    swapped_member[0] = replacement
    duplicate = planted[:]
    duplicate[0] = duplicate[1]
    corruptions = {
        "drop": {"support": planted[:-1]},
        "swap_one_member": {"support": swapped_member},
        "duplicate": {"support": duplicate},
        "empty": {"support": []},
        "out_of_range": {"support": planted[:-1] + [small["p"]]},
    }
    results = {}
    reasons = []
    for name, answer in corruptions.items():
        ok, reason = verify(small, answer)
        results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    reordered = {"support": list(reversed(planted))}
    reordered_ok = verify(small, reordered)[0]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in results.values())
            and len(set(reasons)) == len(reasons)
            and reordered_ok
        ),
        "corruptions": results,
        "distinct_reasons": len(set(reasons)),
        "valid_reordering_accepted": reordered_ok,
    }

    # G3: realistic prose + fenced JSON in tags, exact JSON round-trip, garbage.
    payload = json.dumps(small["answer"], separators=(",", ":"))
    realistic = (
        "The recurrence gives the following support.\n\n"
        "<answer>\n```json\n" + payload + "\n```\n</answer>\n"
        "All residues are reduced modulo p."
    )
    round_trip = parse_answer(realistic) == small["answer"]
    json_native = json.loads(json.dumps(small["answer"])) == small["answer"]
    garbage_none = parse_answer("no certificate was found") is None
    report["G3_round_trip"] = {
        "pass": round_trip and json_native and garbage_none,
        "prose_fence_tags_round_trip": round_trip,
        "answer_json_native": json_native,
        "garbage_returns_none": garbage_none,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=220713456, **ship_params)

    # G4: Proposition 7.1 proves there is exactly one k-subset witness, so set
    # comparison is exactly equivalent to calling verify and avoids 200k cubic
    # algebra checks.  Candidates are uniform k-subsets, already enforcing all
    # freely deducible shape/range/distinctness constraints.
    guess_rng = random.Random(40413456)
    guess_total = 200_000
    guess_hits = 0
    planted_tuple = tuple(ship["answer"]["support"])
    started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(ship, guess_rng)
        guess_hits += int(tuple(candidate["support"]) == planted_tuple)
    guess_wall = time.perf_counter() - started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "exact_unique_witness_probability": f"1/{search_space(ship)}",
        "sampling_prior": "uniform over all k-subsets of F_p; shape, range, and distinctness enforced",
        "measurement_method": "uniform samples compared to the theorem-guaranteed unique support",
        "wall_clock_sec": round(guess_wall, 6),
    }

    # G6: four no-tool attacks must all fail; the polynomial-time domain
    # reference is expected to solve and is deliberately kept outside attacks.
    attack_seeds = [61000 + i for i in range(8)]
    attacks = {
        "outlier_small_moment_residues": {"successes": 0, "attempts": 0},
        "greedy_consecutive_support": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0, "candidates": 0},
        "in_context_small_ratio_two_ansatz": {"successes": 0, "attempts": 0},
        "in_context_nearest_symmetric_pairs": {"successes": 0, "attempts": 0},
    }
    reference_runs = []
    reference_total_operations = 0
    reference_total_wall = 0.0
    attack_started = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **ship_params)
        for name, attack in (
            ("outlier_small_moment_residues", _attack_coefficient_outliers),
            ("greedy_consecutive_support", _attack_consecutive_greedy),
            ("in_context_small_ratio_two_ansatz", _attack_ratio_two),
            ("in_context_nearest_symmetric_pairs", _attack_symmetric_nearest),
        ):
            candidate = attack(inst)
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(verify(inst, candidate)[0])

        rng = random.Random(70000 + seed)
        random_success = False
        for _ in range(256):
            candidate = random_candidate(inst, rng)
            attacks["random_restart_256"]["candidates"] += 1
            if verify(inst, candidate)[0]:
                random_success = True
                break
        attacks["random_restart_256"]["attempts"] += 1
        attacks["random_restart_256"]["successes"] += int(random_success)

        reference_started = time.perf_counter()
        reference_answer, operations = _prony_reference(inst)
        elapsed = time.perf_counter() - reference_started
        solved = reference_answer is not None and verify(inst, reference_answer)[0]
        reference_runs.append(
            {
                "seed": seed,
                "solved": solved,
                "operations": operations,
                "wall_clock_sec": round(elapsed, 6),
            }
        )
        reference_total_operations += operations
        reference_total_wall += elapsed
    attack_total_wall = time.perf_counter() - attack_started

    all_attacks_failed = all(item["successes"] == 0 for item in attacks.values())
    all_reference_solved = all(run["solved"] for run in reference_runs)
    reference_algorithm = {
        "name": "Prony--Hankel recurrence plus Cantor--Zassenhaus factorization",
        "complexity": "expected O(k^3 log p) field operations with this naive dense implementation",
        "operations": reference_total_operations,
        "average_operations": reference_total_operations / len(reference_runs),
        "max_operations": max(run["operations"] for run in reference_runs),
        "wall_clock_sec": round(reference_total_wall, 6),
        "average_wall_clock_sec": round(reference_total_wall / len(reference_runs), 6),
        "solves": f"{sum(run['solved'] for run in reference_runs)}/8, as expected",
        "per_seed": reference_runs,
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and all_reference_solved,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    demo = make_instance(seed=202207, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and demo_count == 1 and all_reference_solved,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_fraction": guess_fraction,
        "shipping_exact_density": f"1/{search_space(ship)}",
        "shipping_candidate_space": search_space(ship),
        "shipping_density_method": "unique-witness theorem plus uniform structure-aware sampling",
        "enumerate_all_shipping": enumerate_all(ship),
        "demo_candidate_space": search_space(demo),
        "demo_exact_solution_count": demo_count,
        "reference_algorithm_operations": reference_total_operations,
        "reference_algorithm_average_operations": reference_total_operations / 8,
        "reference_algorithm_wall_clock_sec": round(reference_total_wall, 6),
        "strongest_failing_attack": "random_restart_256",
        "failing_attack_candidates": attacks["random_restart_256"]["candidates"],
        "whole_panel_wall_clock_sec": round(attack_total_wall, 6),
    }

    # G7: operation-count growth from demo to shipping, search-space growth, and
    # a literal size-doubled shipping instance that still builds and verifies.
    base = make_instance(seed=771, **DIFFICULTY["demo"])
    base_started = time.perf_counter()
    base_reference, base_operations = _prony_reference(base)
    base_wall = time.perf_counter() - base_started
    doubled = make_instance(n=40, p=241, zeta=5, seed=771)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    hard_average_operations = reference_total_operations / 8
    report["G7_scales"] = {
        "pass": (
            base_reference is not None
            and verify(base, base_reference)[0]
            and doubled_ok
            and search_space(doubled) > search_space(ship) > search_space(base)
            and hard_average_operations > base_operations
        ),
        "base_n": base["k"],
        "base_space_bits": search_space(base).bit_length(),
        "base_reference_operations": base_operations,
        "base_reference_wall_clock_sec": round(base_wall, 6),
        "shipping_n": ship["k"],
        "shipping_space_bits": search_space(ship).bit_length(),
        "shipping_reference_average_operations": hard_average_operations,
        "doubled_n": doubled["k"],
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    # G8: affine chart changes, global tensor scaling, support reordering, and
    # compositions are real symmetries.  Coefficients are carried with points.
    invariant_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=8000 + seed, **ship_params)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(9000 + seed)
        u1 = rng.randrange(1, inst["p"])
        t1 = rng.randrange(inst["p"])
        scale1 = rng.randrange(1, inst["p"])
        u2 = rng.randrange(1, inst["p"])
        t2 = rng.randrange(inst["p"])
        changed_affine = _affine_transform(inst, u1, t1)
        changed_scale = _affine_transform(inst, 1, 0, scale1)
        changed_composed = _affine_transform(changed_affine, u2, t2, scale1)
        changed_reordered = dict(inst)
        changed_reordered["answer"] = {
            "support": list(reversed(inst["answer"]["support"]))
        }
        changed_reordered["_weights"] = list(reversed(inst["_weights"]))
        for index, changed in enumerate(
            [changed_affine, changed_scale, changed_composed, changed_reordered]
        ):
            invariant_checks += 1
            carried_checks += 1
            if canonical_key(changed) != base_key:
                key_failures.append(
                    {"seed": seed, "transform": index, "kind": "key_changed"}
                )
            if not verify(changed, changed["answer"])[0]:
                key_failures.append(
                    {"seed": seed, "transform": index, "kind": "carried_witness_failed"}
                )
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "failures": key_failures,
        "transformations": [
            "affine coordinate change a -> u*a+t",
            "global nonzero tensor scaling",
            "composition of two affine changes with scaling",
            "reordering of the unordered support witness",
        ],
        "scope_caveat": "strongest cheap affine invariant, not a full PGL(2,p) canonical form",
    }

    # G9(a,b) are diagnostics only.  G9(c)'s answer and intended-route caps gate.
    answer_chars = len(json.dumps(ship["answer"], separators=(",", ":")))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_elements(ship["answer"])
    _, intended_operations = _compact_candidate(ship)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (
        arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_complete": all(arms[name]["attempts"] >= 3 for name in arms),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "within_caps": within_caps,
    }
    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
