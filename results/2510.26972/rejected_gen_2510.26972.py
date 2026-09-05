"""Problem generator based on arXiv:2510.26972.

The paper studies the F_q-order of an element through linearized polynomials.
This module works in normal-basis coordinates, where Frobenius is a cyclic
shift.  It constructs a k-normal element from complementary factors of
x^(2k)-1 and asks for its exact F_q-order polynomial.
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
    "certificate_form": "polynomial",
    "native_objects": [
        "finite-field element in normal-basis coordinates",
        "linearized polynomial over a prime field",
        "F_q-order polynomial",
    ],
    "verification_operations": [
        "modular coefficient normalization",
        "sparse cyclic polynomial convolution",
        "exact linearized-polynomial annihilation check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Normal-basis coordinate blocks repeat under a hidden cyclic shift, so the "
        "complementary factor of x^N-1 is short; ignoring that invariant requires "
        "a full polynomial gcd or minimal-polynomial computation."
    ),
    "hardness_basis": (
        "Track B: the standard formula Ord(beta)=(x^N-1)/gcd(x^N-1,B_beta) "
        "uses a polynomial Euclidean algorithm with quadratic schoolbook cost; "
        "on eight shipping instances it used 105,980,792 coefficient operations "
        "and 3.29 wall-clock seconds (at most 14,422,715 operations for one), "
        "whereas the repeated-block route uses 218 exact operations."
    ),
    "max_answer_tokens": 29,
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

# n is the power-of-two spacing A.  The actual extension degree is 2*t*A.
DIFFICULTY = {
    "demo": {"n": 1, "odd_factor": 3, "field_bits": 3, "disguise_degree": 0},
    "easy": {"n": 32, "odd_factor": 5, "field_bits": 17, "disguise_degree": 7},
    "medium": {"n": 128, "odd_factor": 7, "field_bits": 19, "disguise_degree": 11},
    "hard": {"n": 256, "odd_factor": 9, "field_bits": 23, "disguise_degree": 15},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: The nonzero normal-basis coordinates form scalar-multiple blocks with "
    "one common cyclic stride."
)
PLACEBO_HINT = (
    "Hint: The normal-basis coordinates should be copied with every index and "
    "coefficient checked carefully."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A canonical sparse monic polynomial over F_q of degree k with exactly "
        "R nonzero terms: a JSON list [[coefficient, exponent], ...] in strictly "
        "increasing exponent order, including nonzero constant and leading terms, "
        "with g(1)=0."
    ),
    "bounds": {
        "terms": "instance field answer_terms (at most 10 in the named presets)",
        "coefficient_range": "0 through q-1",
        "exponent_range": "0 through k",
        "monic": True,
        "constant_nonzero": True,
        "coefficient_sum_mod_q": 0,
    },
}

# Filled after script-owned runs.  These values are diagnostics; only G9(c) gates.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES = r"""
STEP 0 and definition.  The prior-triage proposal (choose q and retain a found
primitive k-normal element) is forbidden: Appendix Algorithm 2 explicitly loops
over translates beta+u and tests multiplicative order, so it obtains the answer
by solving the emitted search problem.  The module instead uses the paper's
native additive object.  Definition 2.3 defines the F_q-order as the least monic
g with L_g(beta)=0, and Theorem 2.4 equates degree n-k with k-normality.

Construction.  Section 3, especially Proposition 3.1 and Lemma 3.6(i), uses
beta=L_f(alpha) for a normal alpha and complementary factors f*g=x^(2k)-1.
For odd t and A=2^s, put y=x^A,
  f=(y+1)(1+y+...+y^(t-1)),
  g=(y-1)(y^(t-1)-y^(t-2)+...-y+1).
Then f*g=y^(2t)-1, deg(g)=k=tA, x-1 divides g, and g is not
x^k-1.  Multiplying f by a unit h modulo g and by a nonzero scalar/cyclic
shift preserves the annihilator.  The generator samples h first as a product of
linear factors x-c with c^N != 1, so every transformation has an executable unit
certificate and g is carried through; it never solves for g from beta.

Easy regime and track.  Theorem 2.4 makes a generic order computation a
polynomial gcd/minimal-polynomial problem, so Track A would be false.  This is
Track B: selftest actually runs the schoolbook Euclidean algorithm on eight
shipping instances and records its coefficient-operation count and wall time.
The compact route notices the shifted scalar-multiple coordinate blocks, reduces
to y=x^A, and multiplies two displayed geometric identities.  Its measured
operation budget is below 300.  The paper's complete n=6,k=3 existence
classification (Theorem 4.2) is not used as a lookup table.

Attacks.  The outlier probe guesses exponents from the largest centered
coefficients; the greedy probe follows the most common coordinate gap (the
consecutive disguise coefficients make that gap 1); random restart samples the
fully constrained certificate language; the in-context ansatz assumes the
visible short spacing is the annihilator spacing.  The actual invariant is the
long cyclic block stride, and plants and disguise coordinates are coefficients
of the same product rather than differently distributed marked entries.

Canonicalization.  Reordering the sparse coordinate pairs, multiplying beta by
a nonzero base-field scalar, and applying a Frobenius/cyclic shift all preserve
the order.  Every generated beta for fixed (q,N,R) is a unit multiple of the same
f in F_q[x]/(x^N-1), hence lies in the same module-automorphism orbit.
canonical_key records exactly (q,N,R).  The selftest checks each symmetry and a
composition, carries the unchanged witness, and uses independently generated q
values to check diversity.

Hardening outcome.  The script-owned bare run tried easy, medium, hard, and the
one further level that still fit the 300-operation route cap.  Both oracle
vendors returned an exactly verifying polynomial on every call: 12 solves in 12
attempts.  The public degree k and term count R exposed the same complementary
factor pattern on every seed.  Thus G and V pass, but H fails on Track B; this
module is retained only as rejection evidence.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for the <2^64 values used by the ladder."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value == p:
            return True
        if value % p == 0:
            return False
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % value == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _sample_prime(bits: int, rng: random.Random) -> int:
    if bits == 3:
        return rng.choice((5, 7))
    low = 1 << (bits - 1)
    high = 1 << bits
    candidate = rng.randrange(low, high) | 1
    for _ in range((high - low) // 2):
        if candidate != 3 and _is_prime(candidate):
            return candidate
        candidate += 2
        if candidate >= high:
            candidate = low | 1
    raise RuntimeError("failed to find a prime in the requested bit interval")


def _poly_mul_dense(a: list[int], b: list[int], q: int) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                if bj:
                    out[i + j] = (out[i + j] + ai * bj) % q
    return out


def _make_unit_disguise(
    degree: int, extension_degree: int, q: int, rng: random.Random
) -> list[int]:
    """Construct h as product(x-c), with every factor a unit modulo x^N-1."""
    if degree == 0:
        return [rng.randrange(1, q)]
    for _ in range(128):
        h = [1]
        used: set[int] = set()
        while len(used) < degree:
            c = rng.randrange(1, q)
            if c in used or pow(c, extension_degree, q) == 1:
                continue
            used.add(c)
            h = _poly_mul_dense(h, [(-c) % q, 1], q)
        if all(h):
            return h
    raise RuntimeError("could not construct a nonzero-coefficient unit disguise")


def _f_coefficients(t: int, q: int) -> list[int]:
    # (y+1)(1+y+...+y^(t-1))
    return [1] + [2 % q] * (t - 1) + [1]


def _g_coefficients(t: int, q: int) -> list[int]:
    # (y-1)(y^(t-1)-y^(t-2)+...-y+1), ascending powers.
    return [q - 1] + [(2 if j % 2 else q - 2) for j in range(1, t)] + [1]


def _answer_from_stride(stride: int, t: int, k: int, q: int) -> list[list[int]]:
    exponents = [j * stride for j in range(t)] + [k]
    if len(set(exponents)) != t + 1 or exponents != sorted(exponents):
        exponents = list(range(t)) + [k]
    return [[c, e] for c, e in zip(_g_coefficients(t, q), exponents)]


def make_instance(
    n: int,
    seed: int = 0,
    odd_factor: int = 3,
    field_bits: int = 17,
    disguise_degree: int = 7,
    **params,
) -> dict:
    """Build a promised k-normal element and carry its order through a unit map.

    ``n`` is A=2^s, the spacing in the complementary-factor identity.  The
    extension degree is N=2*odd_factor*n, so increasing n increases the ambient
    minimal-polynomial problem while the sparse answer length stays fixed.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 1 or n & (n - 1):
        raise ValueError("n must be a positive power of two")
    if (
        isinstance(odd_factor, bool)
        or not isinstance(odd_factor, int)
        or odd_factor < 3
        or odd_factor % 2 == 0
    ):
        raise ValueError("odd_factor must be an odd integer at least 3")
    if isinstance(field_bits, bool) or not 3 <= field_bits <= 63:
        raise ValueError("field_bits must be an integer from 3 through 63")
    if (
        isinstance(disguise_degree, bool)
        or not isinstance(disguise_degree, int)
        or not 0 <= disguise_degree < n
    ):
        raise ValueError("disguise_degree must be an integer from 0 through n-1")

    rng = random.Random(seed)
    q = _sample_prime(field_bits, rng)
    t = odd_factor
    stride = n
    k = t * stride
    extension_degree = 2 * k

    h = _make_unit_disguise(disguise_degree, extension_degree, q, rng)
    f_coeffs = _f_coefficients(t, q)
    scale = rng.randrange(1, q)
    block_shift = rng.randrange(2 * t)

    beta_terms: list[list[int]] = []
    for j, fj in enumerate(f_coeffs):
        for r, hr in enumerate(h):
            exponent = ((j + block_shift) * stride + r) % extension_degree
            coefficient = scale * fj * hr % q
            beta_terms.append([exponent, coefficient])
    rng.shuffle(beta_terms)

    checks = [
        "monic least linearized annihilator",
        "degree equals k=N/2",
        "canonical sparse coefficient representation",
    ]
    rng.shuffle(checks)
    answer = [
        [coefficient, j * stride]
        for j, coefficient in enumerate(_g_coefficients(t, q))
    ]
    return {
        "family": "F_q-order in normal-basis coordinates",
        "q": q,
        "extension_degree": extension_degree,
        "target_degree": k,
        "answer_terms": t + 1,
        "beta_coordinates": beta_terms,
        "checks": checks,
        "answer": answer,
    }


def render(inst: dict) -> str:
    coords = "\n".join(f"  {i}: {c}" for i, c in inst["beta_coordinates"])
    checks = "\n".join(f"- {item}" for item in inst["checks"])
    statement = f"""Exact F_q-order from normal-basis coordinates

Let q={inst['q']} (a prime) and N={inst['extension_degree']}.  Work in the finite
field F_(q^N), regarded as an N-dimensional vector space over F_q.  A normal
basis is an ordered basis
  alpha, alpha^q, alpha^(q^2), ..., alpha^(q^(N-1)).
Indices below are 0-based and cyclic modulo N.

The element beta is given by its nonzero coordinates in that basis: a line
"i: c" means c*alpha^(q^i), with c represented by the integer 0<=c<q.  Lines
may appear in any order; omitted coordinates are zero.  The complete list is:
{coords}

For a polynomial a(x)=sum_j a_j*x^j in F_q[x], define its q-linearized action by
  L_a(beta)=sum_j a_j*beta^(q^j).
The F_q-order Ord(beta) is the unique monic polynomial of least degree satisfying
L_a(beta)=0.  This instance promises that beta is k-normal with
k={inst['target_degree']}=N/2, so Ord(beta) has degree N-k=k.

Return Ord(beta) in canonical sparse form.  It has exactly
R={inst['answer_terms']} nonzero terms.  Write a JSON list
[[coefficient, exponent], ...] in strictly increasing exponent order.  Include
the nonzero constant term and the monic leading term [1,k].  Every coefficient
must be its canonical integer representative from 1 through q-1; exponents are
integers from 0 through k.  No exponent may repeat.  The coefficients sum to 0
modulo q (equivalently x-1 divides the answer polynomial).

The checker enforces:
{checks}

Give your final answer inside <answer></answer> tags, as the JSON list above.
Example: <answer>[[4,0],[2,1],[3,2],[1,3]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract one tagged JSON polynomial; surrounding prose/fences are allowed."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    try:
        value = json.loads(match.group(1).strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _validate_answer_shape(inst: dict, answer: object) -> tuple[bool, str]:
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != inst["answer_terms"]:
        return False, f"expected exactly {inst['answer_terms']} polynomial terms"
    parsed: list[tuple[int, int]] = []
    for term in answer:
        if (
            not isinstance(term, list)
            or len(term) != 2
            or isinstance(term[0], bool)
            or isinstance(term[1], bool)
            or not isinstance(term[0], int)
            or not isinstance(term[1], int)
        ):
            return False, "each term must be [integer coefficient, integer exponent]"
        coefficient, exponent = term
        if not 1 <= coefficient < inst["q"]:
            return False, "a coefficient is outside the canonical range 1..q-1"
        if not 0 <= exponent <= inst["target_degree"]:
            return False, "an exponent is outside the required range 0..k"
        parsed.append((coefficient, exponent))
    exponents = [e for _, e in parsed]
    if len(set(exponents)) != len(exponents):
        return False, "duplicate exponents are not allowed"
    if exponents != sorted(exponents):
        return False, "terms must be in strictly increasing exponent order"
    if exponents[0] != 0:
        return False, "the nonzero constant term is missing"
    if exponents[-1] != inst["target_degree"] or parsed[-1][0] != 1:
        return False, "the polynomial must be monic of degree k"
    if sum(c for c, _ in parsed) % inst["q"]:
        return False, "the coefficients do not sum to zero modulo q"
    return True, "ok"


def _cyclic_coefficient(
    beta: dict[int, int], terms: list[tuple[int, int]], position: int, q: int, n: int
) -> int:
    total = 0
    for coefficient, exponent in terms:
        total += coefficient * beta.get((position - exponent) % n, 0)
    return total % q


def _annihilates(inst: dict, answer: list[list[int]]) -> bool:
    q = inst["q"]
    n = inst["extension_degree"]
    beta = {i: c for i, c in inst["beta_coordinates"]}
    terms = [(c, e) for c, e in answer]

    # Sound early exits make the 200k-candidate density measurement inexpensive.
    anchor = inst["beta_coordinates"][0][0]
    for _, exponent in terms:
        position = (anchor + exponent) % n
        if _cyclic_coefficient(beta, terms, position, q, n):
            return False

    product: dict[int, int] = {}
    for coefficient, exponent in terms:
        for beta_exponent, beta_coefficient in beta.items():
            position = (exponent + beta_exponent) % n
            product[position] = (
                product.get(position, 0) + coefficient * beta_coefficient
            ) % q
    return all(value == 0 for value in product.values())


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check the promised-degree order by exact sparse linearized substitution."""
    shape_ok, reason = _validate_answer_shape(inst, answer)
    if not shape_ok:
        return False, reason
    assert isinstance(answer, list)
    if not _annihilates(inst, answer):
        return False, "the polynomial does not annihilate beta under L_a"
    # On the stated k-normal promise, any monic degree-k annihilator is the unique
    # least annihilator: Ord(beta) divides it and has the same degree.
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the fully constrained sparse certificate language."""
    q = inst["q"]
    k = inst["target_degree"]
    term_count = inst["answer_terms"]
    internal = sorted(rng.sample(range(1, k), term_count - 2))
    while True:
        coefficients = [rng.randrange(1, q) for _ in range(term_count - 2)]
        last_unknown = (-1 - sum(coefficients)) % q
        if last_unknown:
            break
    all_nonleading = coefficients + [last_unknown]
    rng.shuffle(all_nonleading)
    exponents = [0] + internal
    return [[c, e] for c, e in zip(all_nonleading, exponents)] + [[1, k]]


def search_space(inst: dict) -> int:
    """Exact cardinality of random_candidate's monic/sum-zero language."""
    q = inst["q"]
    k = inst["target_degree"]
    t = inst["answer_terms"] - 1
    supports = math.comb(k - 1, t - 1)
    coefficient_choices = ((q - 1) ** t - (-1) ** t) // q
    return supports * coefficient_choices


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when it has at most 100k members."""
    if search_space(inst) > 100_000:
        return None
    q = inst["q"]
    k = inst["target_degree"]
    term_count = inst["answer_terms"]
    valid = 0
    for internal in itertools.combinations(range(1, k), term_count - 2):
        for prefix in itertools.product(range(1, q), repeat=term_count - 2):
            final = (-1 - sum(prefix)) % q
            if not final:
                continue
            coefficients = list(prefix) + [final]
            exponents = [0] + list(internal)
            candidate = [[c, e] for c, e in zip(coefficients, exponents)] + [[1, k]]
            valid += int(verify(inst, candidate)[0])
    return valid


def canonical_key(inst: dict) -> str:
    """Canonical module-orbit invariant, independent of coordinate presentation."""
    raw = f"q={inst['q']}|N={inst['extension_degree']}|R={inst['answer_terms']}"
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow ambient degree, coefficient entropy, and disguise at fixed short answer."""
    harder = {k: v for k, v in params.items() if k != "_preset"}
    # The named hard rung already costs 218 intended-route operations.  The first
    # exploratory escalation raises that to 298 and later ones exceed G9(c), while
    # the script-owned oracle run showed that larger N/q do not change the exposed
    # complementary-factor formula.  There is therefore no honest remaining axis:
    # more coordinate decoys become an inspection-length test, not more insight.
    if int(harder.get("n", 1)) >= 512 and int(harder.get("disguise_degree", 0)) >= 23:
        return None
    harder["n"] = int(harder.get("n", 1)) * 2
    harder["field_bits"] = min(63, int(harder.get("field_bits", 17)) + 2)
    old_disguise = int(harder.get("disguise_degree", 7))
    harder["disguise_degree"] = min(harder["n"] - 1, old_disguise + 8)
    return harder


def _trim(poly: list[int]) -> list[int]:
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return poly


def _poly_divmod_counted(
    numerator: list[int], denominator: list[int], q: int, counter: list[int]
) -> tuple[list[int], list[int]]:
    numerator = _trim(numerator[:])
    denominator = _trim(denominator[:])
    if denominator == [0]:
        raise ZeroDivisionError("polynomial division by zero")
    if len(numerator) < len(denominator):
        return [0], numerator
    quotient = [0] * (len(numerator) - len(denominator) + 1)
    inverse_lead = pow(denominator[-1], q - 2, q)
    counter[0] += 2 * q.bit_length()
    while len(numerator) >= len(denominator) and numerator != [0]:
        shift = len(numerator) - len(denominator)
        factor = numerator[-1] * inverse_lead % q
        quotient[shift] = factor
        counter[0] += 1
        if factor:
            for j, value in enumerate(denominator):
                numerator[shift + j] = (numerator[shift + j] - factor * value) % q
                counter[0] += 2
        _trim(numerator)
    return _trim(quotient), _trim(numerator)


def _reference_order(inst: dict) -> tuple[list[list[int]], int]:
    """Generic Euclidean formula, deliberately unaware of the planted blocks."""
    q = inst["q"]
    n = inst["extension_degree"]
    beta = [0] * n
    for exponent, coefficient in inst["beta_coordinates"]:
        beta[exponent] = coefficient
    x_n_minus_one = [q - 1] + [0] * (n - 1) + [1]
    a, b = x_n_minus_one, _trim(beta)
    counter = [0]
    while b != [0]:
        _, remainder = _poly_divmod_counted(a, b, q, counter)
        a, b = b, remainder
    inverse = pow(a[-1], q - 2, q)
    counter[0] += 2 * q.bit_length()
    gcd_poly = [(value * inverse) % q for value in a]
    counter[0] += len(a)
    quotient, remainder = _poly_divmod_counted(
        x_n_minus_one, gcd_poly, q, counter
    )
    if remainder != [0]:
        raise AssertionError("reference gcd did not divide x^N-1")
    answer = [[c, e] for e, c in enumerate(quotient) if c]
    return answer, counter[0]


def _candidate_with_exponents(inst: dict, internal: list[int]) -> list[list[int]]:
    t = inst["answer_terms"] - 1
    k = inst["target_degree"]
    q = inst["q"]
    usable = sorted({e for e in internal if 0 < e < k})
    for e in range(1, k):
        if len(usable) >= t - 1:
            break
        if e not in usable:
            usable.append(e)
    usable = sorted(usable[: t - 1])
    return [
        [coefficient, exponent]
        for coefficient, exponent in zip(
            _g_coefficients(t, q), [0] + usable + [k]
        )
    ]


def _outlier_attack(inst: dict) -> list[list[int]]:
    q = inst["q"]
    t = inst["answer_terms"] - 1
    ranked = sorted(
        inst["beta_coordinates"],
        key=lambda pair: abs(pair[1] - q // 2),
        reverse=True,
    )
    return _candidate_with_exponents(inst, [i for i, _ in ranked[: t - 1]])


def _greedy_gap_attack(inst: dict) -> list[list[int]]:
    exponents = sorted(i for i, _ in inst["beta_coordinates"])
    counts: dict[int, int] = {}
    for left, right in zip(exponents, exponents[1:]):
        gap = right - left
        counts[gap] = counts.get(gap, 0) + 1
    stride = max(counts, key=lambda gap: (counts[gap], -gap)) if counts else 1
    t = inst["answer_terms"] - 1
    return _candidate_with_exponents(inst, [j * stride for j in range(1, t)])


def _in_context_ansatz(inst: dict) -> list[list[int]]:
    t = inst["answer_terms"] - 1
    stride = max(1, inst["target_degree"] // (t + 1))
    return _candidate_with_exponents(inst, [j * stride for j in range(1, t)])


def _random_restart_attack(inst: dict, seed: int, restarts: int = 256) -> tuple[object, int]:
    rng = random.Random(seed)
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _scale_shift_reorder(inst: dict, scale: int, shift: int, seed: int) -> dict:
    transformed = dict(inst)
    q = inst["q"]
    n = inst["extension_degree"]
    coords = [
        [(index + shift) % n, coefficient * scale % q]
        for index, coefficient in inst["beta_coordinates"]
    ]
    random.Random(seed).shuffle(coords)
    transformed["beta_coordinates"] = coords
    transformed["checks"] = list(reversed(inst["checks"]))
    transformed["answer"] = json.loads(json.dumps(inst["answer"]))
    return transformed


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run all mandatory gates and return JSON-native measured evidence."""
    report: dict[str, object] = {
        "paper": "2510.26972",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_count = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_count += 1
            if not ok or not json_native:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "instances": g1_count,
        "failures": g1_failures,
    }

    ship = make_instance(seed=251026972, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = ship["answer"]
    dropped = planted[:-1]
    swapped = json.loads(json.dumps(planted))
    swapped[1], swapped[2] = swapped[2], swapped[1]
    duplicated = json.loads(json.dumps(planted))
    duplicated[2][1] = duplicated[1][1]
    out_of_range = json.loads(json.dumps(planted))
    out_of_range[0][0] = ship["q"]
    corruptions = {
        "drop_one": dropped,
        "swap_two": swapped,
        "duplicate_one": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    flags = {name: not verify(ship, candidate)[0] for name, candidate in corruptions.items()}
    reasons = {name: verify(ship, candidate)[1] for name, candidate in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(flags.values()) and len(set(reasons.values())) == 5,
        "rejected": flags,
        "reasons": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    response = (
        "The repeated normal-coordinate blocks give the following order.\n"
        "```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(9042510)
    density_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    observed = guess_hits / guess_total
    exact_fraction = 1.0 / search_space(ship)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6 and exact_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "exact_probability_unique_order": exact_fraction,
        "structure_aware_search_space": search_space(ship),
        "sampling_wall_clock_seconds": round(density_wall, 6),
        "candidate_prior": (
            "uniform over canonical monic R-term degree-k polynomials with nonzero "
            "constant, distinct ordered exponents, and coefficient sum zero"
        ),
    }

    attack_seeds = [3101, 3109, 3119, 3121, 3137, 3163, 3167, 3181]
    attacks = {
        "outlier_largest_centered_coefficients": {"successes": 0, "attempts": 0},
        "greedy_most_common_coordinate_gap": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_even_spacing_ansatz": {"successes": 0, "attempts": 0},
    }
    attack_trials = 0
    attack_start = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_largest_centered_coefficients": _outlier_attack(inst),
            "greedy_most_common_coordinate_gap": _greedy_gap_attack(inst),
            "in_context_even_spacing_ansatz": _in_context_ansatz(inst),
        }
        restart, used = _random_restart_attack(inst, seed ^ 0xA11CE, 256)
        candidates["random_restart_256"] = restart
        attack_trials += used
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if candidate is not None:
                attacks[name]["successes"] += int(verify(inst, candidate)[0])
    attack_wall = time.perf_counter() - attack_start

    reference_successes = 0
    reference_operations = 0
    reference_max_operations = 0
    reference_start = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate, operations = _reference_order(inst)
        reference_operations += operations
        reference_max_operations = max(reference_max_operations, operations)
        reference_successes += int(verify(inst, candidate)[0])
    reference_wall = time.perf_counter() - reference_start
    all_attacks_failed = all(item["successes"] == 0 for item in attacks.values())
    reference_algorithm = {
        "name": "Euclidean polynomial gcd: (x^N-1)/gcd(x^N-1,B_beta)",
        "complexity": "O(N^2) schoolbook field operations",
        "wall_clock_sec": round(reference_wall, 6),
        "operations": reference_operations,
        "max_operations_one_instance": reference_max_operations,
        "solves": f"{reference_successes}/{len(attack_seeds)}",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": observed < 1e-6 and all_attacks_failed and reference_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_valid_fraction_observed": observed,
        "shipping_valid_fraction_exact": exact_fraction,
        "analytic_valid_solution_count": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_seconds": round(reference_wall, 6),
        "baseline_coefficient_operations": reference_operations,
        "baseline_attack": reference_algorithm["name"],
        "failing_panel_wall_clock_seconds": round(attack_wall, 6),
        "failing_panel_random_trials": attack_trials,
    }

    before_params = dict(DIFFICULTY["medium"])
    after_params = dict(before_params)
    after_params["n"] *= 2
    before = make_instance(seed=771, **before_params)
    after = make_instance(seed=771, **after_params)
    g7_ok = (
        verify(before, before["answer"])[0]
        and verify(after, after["answer"])[0]
        and after["extension_degree"] == 2 * before["extension_degree"]
        and search_space(after) > search_space(before)
        and _answer_atoms(after["answer"]) == _answer_atoms(before["answer"])
    )
    report["G7_scales"] = {
        "pass": g7_ok,
        "n_before": before_params["n"],
        "n_after_doubling": after_params["n"],
        "extension_degree_before": before["extension_degree"],
        "extension_degree_after": after["extension_degree"],
        "space_before": search_space(before),
        "space_after": search_space(after),
        "answer_elements_before": _answer_atoms(before["answer"]),
        "answer_elements_after": _answer_atoms(after["answer"]),
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_ok = True
    carried_ok = True
    unrelated_keys = []
    for offset in range(20):
        inst = make_instance(
            seed=8000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        unrelated_keys.append(canonical_key(inst))
        q = inst["q"]
        n_ext = inst["extension_degree"]
        transformed1 = _scale_shift_reorder(
            inst, 1, 0, 10000 + offset
        )
        transformed2 = _scale_shift_reorder(
            inst, 2 % q, 1, 11000 + offset
        )
        transformed3 = _scale_shift_reorder(
            transformed2, 3 % q, n_ext // 3 + 1, 12000 + offset
        )
        base_key = canonical_key(inst)
        for transformed in (transformed1, transformed2, transformed3):
            invariant_checks += 1
            invariant_ok = invariant_ok and canonical_key(transformed) == base_key
            carried_checks += 1
            carried_ok = carried_ok and verify(transformed, inst["answer"])[0]
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok and carried_ok and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_checks if invariant_ok else 0,
        "carried_witness_checks": carried_checks,
        "carried_witness_passed": carried_checks if carried_ok else 0,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries": [
            "coordinate-pair reordering",
            "nonzero base-field scalar multiplication",
            "Frobenius/cyclic coordinate shift",
            "composition of scalar, shift, and reordering",
        ],
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(ship["answer"])
    intended_ops = len(ship["beta_coordinates"]) + 5 * len(ship["answer"]) + 8
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
