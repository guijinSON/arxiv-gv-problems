"""Verified generator for brace-derived Yang--Baxter evaluations.

The source is Section 3, especially Proposition 3.5 and Theorem 3.6, of
arXiv:1507.02602.  A nilpotent associative ring gives a two-sided brace via
``x circle y = x + y + x*y``; the theorem turns that brace into an involutive,
non-degenerate set-theoretic solution of the Yang--Baxter equation.

Instances use a circulant bilinear form over a finite field.  They ask for two
monic affine polynomials that describe one value of the canonical braiding.
The answer is carried through a planted polynomial decomposition, not found by
solving the emitted instance.  Verification independently evaluates the full
circulant symbol with exact modular arithmetic and never reads the planted
answer.
"""

from __future__ import annotations

import hashlib
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
        "finite-dimensional radical ring over GF(p)",
        "two-sided left brace",
        "circulant bilinear form and its character vectors",
        "monic affine coordinate polynomials for a Yang--Baxter map",
    ],
    "verification_operations": [
        "exact modular polynomial evaluation",
        "exact circulant bilinear contraction on character vectors",
        "exact substitution in the brace left and right actions",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize that the quotient of the circulant symbol by X-1 is a "
        "short polynomial plus a term vanishing at the two character roots; "
        "without that decomposition one must evaluate the entire dense symbol."
    ),
    "hardness_basis": (
        "Track B: Section 3, Theorem 3.6 gives the canonical brace braiding, "
        "and the standard character/Horner algorithm computes this instance in "
        "O(n) exact field operations; at shipping n=512 it uses 2,057 modular "
        "operations and about 0.0001 seconds, whereas the planted decomposition "
        "uses 109 operations but still entails twenty-term 64-bit modular "
        "evaluations that are not mechanically executable without tools."
    ),
    "max_answer_tokens": 17,
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
    "demo": {"n": 8, "window": 2, "field": "toy"},
    "easy": {"n": 512, "window": 20, "field": "goldilocks"},
    "medium": {"n": 1024, "window": 20, "field": "goldilocks"},
    "hard": {"n": 2048, "window": 20, "field": "goldilocks"},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The quotient of the circulant symbol by X-1 has a short low-degree part "
    "whose remainder is divisible by (X-omega)(X-omega^-1)."
)
PLACEBO_HINT = (
    "The coefficient order of the circulant symbol is significant and every "
    "field operation should be reduced to its canonical residue."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly the keys left and right; each value is the "
        "two-coefficient list [constant, 1] of a monic affine polynomial over "
        "GF(p), with both coefficients represented by canonical integers in "
        "0,...,p-1."
    ),
    "bounds": {
        "polynomials": 2,
        "degree": 1,
        "leading_coefficient": 1,
        "constant_min": 0,
        "constant_max": "p-1",
        "candidate_count": "p^2",
    },
}

NOTES = (
    "Section 2 fixes a solution as a bijective non-degenerate involutive map "
    "satisfying the braid identity.  Section 3, Definition 3.4 fixes the brace "
    "law; Proposition 3.5 identifies lambda_a(b)=a*b-a as an additive "
    "automorphism; and Theorem 3.6 constructs the unique associated symmetric "
    "group and Yang--Baxter map.  That direct construction rules out Track A. "
    "The ring here has x*y=(x^T C y)1 with a circulant C whose row and column "
    "sums vanish, so every triple product is zero and x circle y=x+y+x*y is a "
    "two-sided brace by construction.  The dense circulant symbol is composed "
    "as (X-1)(g(X)+X^L(X-omega)(X-omega^-1)h(X)); its values at the two "
    "characters therefore come from the short g without solving the emitted "
    "instance.  Random dense g and h remove coefficient outliers.  The audited "
    "attacks cover the flip ansatz, a constant-term shortcut, a magnitude "
    "outlier, an unjustified short-prefix evaluation, and random restarts."
)


# The Goldilocks prime is 2^64-2^32+1.  Its multiplicative group has a
# 2^32 factor, and 7 has full 2-adic order, so it supplies roots of unity for
# every shipping dimension.  The tiny field exists only for the worked demo.
_FIELDS = {
    "toy": {"p": 17, "generator": 3},
    "goldilocks": {"p": 18_446_744_069_414_584_321, "generator": 7},
}

# Replaced with the script-owned measurements after the three oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value):
    return value > 0 and value & (value - 1) == 0


def _horner(coefficients, point, p):
    value = 0
    for coefficient in reversed(coefficients):
        value = (value * point + coefficient) % p
    return value


def _answer(left_constant, right_constant):
    return {
        "left": [left_constant, 1],
        "right": [right_constant, 1],
    }


def _validate_parameters(n, window, field):
    if field not in _FIELDS:
        raise ValueError("unknown field preset")
    p = _FIELDS[field]["p"]
    if not _is_int(n) or not _is_power_of_two(n):
        raise ValueError("n must be a positive power of two")
    if not _is_int(window) or window < 1 or n < window + 4:
        raise ValueError("window must be positive and at most n-4")
    if (p - 1) % n:
        raise ValueError("n must divide p-1")


def _build_symbol(n, window, omega, omega_inverse, rng, p):
    """Return (c,g) for c=(X-1)(g+X^L(X-w)(X-w^-1)h).

    The output degree is at most n-1.  The dense h coefficients and the short g
    coefficients are sampled from the same uniform field distribution.  This
    routine composes a polynomial identity; it performs no root finding or
    equation solving.
    """
    g = [rng.randrange(p) for _ in range(window)]
    if not any(g):
        g[0] = 1

    # deg(h) <= n-window-4, so the shifted quadratic has degree <= n-2.
    h = [rng.randrange(p) for _ in range(n - window - 3)]
    q = [0] * (n - 1)
    q[:window] = g
    middle = (-(omega + omega_inverse)) % p
    for index, coefficient in enumerate(h):
        base = window + index
        q[base] = (q[base] + coefficient) % p
        q[base + 1] = (q[base + 1] + middle * coefficient) % p
        q[base + 2] = (q[base + 2] + coefficient) % p

    # Multiply q by X-1 without a generic polynomial package.
    c = [0] * n
    c[0] = (-q[0]) % p
    for degree in range(1, n - 1):
        c[degree] = (q[degree - 1] - q[degree]) % p
    c[n - 1] = q[n - 2]
    return c, g


def make_instance(n, seed=0, window=20, field="goldilocks") -> dict:
    """Construct a brace evaluation with a carried polynomial certificate.

    Generation samples the low polynomial g and a dense vanishing residual,
    composes their product identity, and evaluates only g at the two roots.
    It never solves the full emitted Horner problem.
    """
    _validate_parameters(n, window, field)
    rng = random.Random(seed)
    data = _FIELDS[field]
    p = data["p"]
    base_omega = pow(data["generator"], (p - 1) // n, p)
    odd_power = rng.randrange(1, n, 2)
    omega = pow(base_omega, odd_power, p)
    omega_inverse = pow(omega, n - 1, p)
    a_scale = rng.randrange(1, p)
    b_scale = rng.randrange(1, p)

    c, short_polynomial = _build_symbol(
        n, window, omega, omega_inverse, rng, p
    )

    phase = a_scale * b_scale % p
    short_at_omega = _horner(short_polynomial, omega, p)
    short_at_inverse = _horner(short_polynomial, omega_inverse, p)
    left_constant = (
        phase * (n % p) * ((omega - 1) % p) * short_at_omega
    ) % p
    right_constant = (
        -phase
        * (n % p)
        * ((omega_inverse - 1) % p)
        * short_at_inverse
    ) % p

    return {
        "n": n,
        "p": p,
        "field": field,
        "window": window,
        "omega": omega,
        "omega_inverse": omega_inverse,
        "a_scale": a_scale,
        "b_scale": b_scale,
        "symbol": c,
        "answer": _answer(left_constant, right_constant),
    }


def _format_coefficients(coefficients, width=6):
    lines = []
    for start in range(0, len(coefficients), width):
        stop = min(start + width, len(coefficients))
        body = " ".join(str(value) for value in coefficients[start:stop])
        lines.append(f"  c[{start}:{stop}] = {body}")
    return "\n".join(lines)


def render(inst) -> str:
    """Render a self-contained exact brace/Yang--Baxter problem."""
    n = inst["n"]
    p = inst["p"]
    statement = f"""Evaluate a brace-derived set-theoretic Yang--Baxter map.

All scalar arithmetic is in the finite field GF(p), represented by the least
nonnegative residues 0,...,p-1, where

  p = {p}.

Vectors have n={n} coordinates indexed 0,...,{n - 1}.  Vector addition and
negation are coordinatewise modulo p.  Let 1 denote the all-one vector.  The
circulant matrix C is defined, with indices reduced modulo n, by

  C[i,j] = c[(j-i) mod n].

Define a bilinear product and a second group operation on GF(p)^n by

  x * y       = (x^T C y) 1,
  x circle y  = x + y + x*y.

The displayed coefficients satisfy sum(c[k])=0 modulo p.  Consequently C1=0
and 1^T C=0, every triple product under * is zero, and circle makes this
radical ring into a two-sided left brace.

For a left brace define lambda_x(y)=x circle y-x.  Its canonical set-theoretic
Yang--Baxter map is

  r(x,y) = ( lambda_x(y), lambda_(lambda_x(y))^(-1)(x) ),

where the inverse superscript means the inverse of the additive automorphism
lambda_z, not a scalar reciprocal.  This r is bijective, non-degenerate,
involutive, and satisfies r12 r23 r12 = r23 r12 r23.

The two input vectors are given symbolically by

  a_i = {inst['a_scale']} * omega^(-i),
  b_i = {inst['b_scale']} * omega^i,

where

  omega          = {inst['omega']},
  omega^(-1)     = {inst['omega_inverse']},
  omega^n        = 1, and omega^(n/2) != 1.

The circulant symbol is f(X)=sum from k=0 to n-1 of c[k]X^k.  Its coefficients,
in increasing degree order, are:

{_format_coefficients(inst['symbol'])}

A public low-degree window parameter for this instance is L={inst['window']}.

There are unique monic affine polynomials P(T)=alpha+T and Q(T)=beta+T over
GF(p) such that, coordinate by coordinate,

  r(a,b) = ( (P(b_i))_i, (Q(a_i))_i ).

Find P and Q.  Encode each polynomial by its coefficient list [constant,linear]
in increasing degree order.  Thus both lists have exactly two integer entries,
their second entry must be 1, and alpha and beta must be their canonical
representatives in the inclusive range 0,...,p-1.  Order matters and no
coefficient may be omitted.

Give your final answer inside <answer></answer> tags, as exactly one JSON object
with keys "left" and "right" and no other keys.
Example: <answer>{{"left":[3,1],"right":[5,1]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nStructural hint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


_ANSWER_BLOCK = re.compile(r"<answer>(.*?)</answer>", re.IGNORECASE | re.DOTALL)


def parse_answer(text) -> object | None:
    """Extract the tagged JSON polynomial pair, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_BLOCK.search(text)
    payload = match.group(1).strip() if match else text.strip()
    if payload.startswith("```") and payload.endswith("```"):
        lines = payload.splitlines()
        if len(lines) >= 2:
            lines = lines[1:-1]
            payload = "\n".join(lines).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, dict):
        return None
    return answer


def _instance_error(inst):
    required = {
        "n",
        "p",
        "field",
        "window",
        "omega",
        "omega_inverse",
        "a_scale",
        "b_scale",
        "symbol",
    }
    if not isinstance(inst, dict) or not required.issubset(inst):
        return "malformed instance"
    n, p = inst["n"], inst["p"]
    if not _is_int(n) or not _is_int(p) or n < 2 or p < 3:
        return "malformed instance dimensions"
    c = inst["symbol"]
    if not isinstance(c, list) or len(c) != n:
        return "circulant symbol has the wrong length"
    scalar_fields = ("omega", "omega_inverse", "a_scale", "b_scale")
    if any(not _is_int(inst[name]) or not 0 < inst[name] < p for name in scalar_fields):
        return "instance scalar is outside GF(p)"
    if any(not _is_int(value) or not 0 <= value < p for value in c):
        return "circulant coefficient is outside GF(p)"
    if sum(c) % p:
        return "circulant row sum is not zero"
    if inst["omega"] * inst["omega_inverse"] % p != 1:
        return "displayed character roots are not inverses"
    if pow(inst["omega"], n, p) != 1 or pow(inst["omega"], n // 2, p) == 1:
        return "omega does not have exact order n"
    return None


def _reference_constants(inst):
    """Standard O(n) exact route: evaluate the entire circulant symbol."""
    p = inst["p"]
    n = inst["n"]
    phase = inst["a_scale"] * inst["b_scale"] % p
    at_omega = _horner(inst["symbol"], inst["omega"], p)
    at_inverse = _horner(inst["symbol"], inst["omega_inverse"], p)
    left = phase * (n % p) * at_omega % p
    right = (-phase * (n % p) * at_inverse) % p
    return left, right


def verify(inst, answer) -> tuple[bool, str]:
    """Check any correctly encoded polynomial pair by exact brace evaluation."""
    problem = _instance_error(inst)
    if problem:
        return False, problem
    if not isinstance(answer, dict) or set(answer) != {"left", "right"}:
        return False, "answer must be an object with exactly left and right keys"
    left = answer["left"]
    right = answer["right"]
    if not isinstance(left, list) or len(left) != 2:
        return False, "left polynomial must have exactly two coefficients"
    if not isinstance(right, list) or len(right) != 2:
        return False, "right polynomial must have exactly two coefficients"
    if any(not _is_int(value) for value in left + right):
        return False, "all polynomial coefficients must be integers"
    p = inst["p"]
    if any(value < 0 or value >= p for value in left + right):
        return False, "polynomial coefficient is outside the canonical field range"
    if left[1] != 1:
        return False, "left polynomial is not monic affine"
    if right[1] != 1:
        return False, "right polynomial is not monic affine"

    expected_left, expected_right = _reference_constants(inst)
    if left[0] != expected_left:
        return False, "left constant does not match the brace left action"
    if right[0] != expected_right:
        return False, "right constant does not match the brace right action"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the exact two-monic-affine-polynomial language."""
    p = inst["p"]
    return _answer(rng.randrange(p), rng.randrange(p))


def search_space(inst) -> int | None:
    """There is one free field constant in each of two monic polynomials."""
    return inst["p"] ** 2


def enumerate_all(inst) -> int | None:
    """Brute-force the bounded language only in the tiny demo field."""
    p = inst["p"]
    if p * p > 10_000:
        return None
    count = 0
    for left in range(p):
        for right in range(p):
            if verify(inst, _answer(left, right))[0]:
                count += 1
    return count


def _phase_orbit_min(a_scale, b_scale, omega, n, p):
    best = None
    a_value = a_scale
    b_value = b_scale
    inverse = pow(omega, n - 1, p)
    for _ in range(n):
        pair = (a_value, b_value)
        if best is None or pair < best:
            best = pair
        a_value = a_value * inverse % p
        b_value = b_value * omega % p
    return best


def canonical_key(inst) -> str:
    """Canonicalise every affine relabelling of the cyclic coordinate set.

    A relabelling i -> u*i+s preserves the presentation exactly when u is a
    unit modulo n.  The primitive roots omega^u are all distinct, so choosing
    the numerically least one also chooses u uniquely; translation s is removed
    by the phase orbit.
    """
    p, n = inst["p"], inst["n"]
    choices = (
        (pow(inst["omega"], multiplier, p), multiplier)
        for multiplier in range(1, n)
        if math.gcd(multiplier, n) == 1
    )
    omega, multiplier = min(choices)
    symbol = [inst["symbol"][(multiplier * index) % n] for index in range(n)]
    phase_pair = _phase_orbit_min(
        inst["a_scale"], inst["b_scale"], omega, n, p
    )
    record = [p, n, inst["window"], omega, phase_pair, symbol]
    payload = json.dumps(record, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _dihedral_relabel(inst, shift=0, reverse=False):
    """Relabel coordinate i by i+shift or -i+shift and carry the witness."""
    return _affine_relabel(inst, -1 if reverse else 1, shift)


def _affine_relabel(inst, multiplier=1, shift=0):
    """Relabel coordinate i by multiplier*i+shift and carry the witness."""
    n, p = inst["n"], inst["p"]
    multiplier %= n
    if math.gcd(multiplier, n) != 1:
        raise ValueError("coordinate multiplier must be a unit modulo n")
    shift %= n
    omega_shift = pow(inst["omega"], shift, p)
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {"omega", "omega_inverse", "a_scale", "b_scale", "symbol"}
    }
    transformed["a_scale"] = (
        inst["a_scale"] * pow(omega_shift, p - 2, p)
    ) % p
    transformed["b_scale"] = inst["b_scale"] * omega_shift % p
    transformed["omega"] = pow(inst["omega"], multiplier, p)
    transformed["omega_inverse"] = pow(inst["omega_inverse"], multiplier, p)
    transformed["symbol"] = [
        inst["symbol"][(multiplier * index) % n] for index in range(n)
    ]
    return transformed


def escalate(params) -> dict | str | None:
    """Double the dense symbol while keeping the two-polynomial answer fixed.

    This axis never reaches ``"cap_bound"``: unlike a usual increase of n, it
    does not add a single atom or character to the certificate.
    """
    harder = dict(params)
    current = int(harder.get("n", 0))
    if current <= 0:
        return None
    next_n = current * 2
    field = harder.get("field", "goldilocks")
    p = _FIELDS.get(field, {}).get("p", 0)
    if not p or (p - 1) % next_n:
        return None
    harder["n"] = next_n
    return harder


def _is_prime_64(value):
    """Deterministic Miller--Rabin primality test for unsigned 64-bit values."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 325, 9_375, 28_178, 450_775, 9_780_504, 1_795_265_022):
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


def _compact_constants(inst):
    """Recover and use the planted low-degree quotient, without hidden data."""
    p = inst["p"]
    window = inst["window"]
    c = inst["symbol"]
    short = [(-c[0]) % p]
    for degree in range(1, window):
        short.append((short[-1] - c[degree]) % p)
    phase = inst["a_scale"] * inst["b_scale"] % p
    left = (
        phase
        * (inst["n"] % p)
        * ((inst["omega"] - 1) % p)
        * _horner(short, inst["omega"], p)
    ) % p
    right = (
        -phase
        * (inst["n"] % p)
        * ((inst["omega_inverse"] - 1) % p)
        * _horner(short, inst["omega_inverse"], p)
    ) % p
    return left, right


def _outlier_attack(inst):
    p = inst["p"]
    centered = lambda x: min(x, p - x)
    guess = max(inst["symbol"], key=centered)
    scale = inst["a_scale"] * inst["b_scale"] * inst["n"] % p
    return _answer(scale * guess % p, (-scale * guess) % p)


def _constant_term_attack(inst):
    p = inst["p"]
    scale = inst["a_scale"] * inst["b_scale"] * inst["n"] % p
    value = scale * inst["symbol"][0] % p
    return _answer(value, (-value) % p)


def _short_prefix_attack(inst):
    p = inst["p"]
    prefix = inst["symbol"][: min(8, inst["window"])]
    phase = inst["a_scale"] * inst["b_scale"] % p
    left = phase * inst["n"] * _horner(prefix, inst["omega"], p) % p
    right = (
        -phase
        * inst["n"]
        * _horner(prefix, inst["omega_inverse"], p)
    ) % p
    return _answer(left, right)


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(item) for item in value)
    return 1


def _explicit_bilinear(inst, x, y):
    """Direct O(n^2) contraction, used only as an independent demo audit."""
    n, p, c = inst["n"], inst["p"], inst["symbol"]
    total = 0
    for i, x_value in enumerate(x):
        for j, y_value in enumerate(y):
            total += x_value * c[(j - i) % n] * y_value
    return total % p


def _explicit_braiding(inst, x, y):
    """Evaluate the two brace actions directly, without character identities."""
    p = inst["p"]
    left_shift = _explicit_bilinear(inst, x, y)
    left = [(value + left_shift) % p for value in y]
    # lambda_left(z)=z+(left^T C z)1 and C1=0, so its inverse subtracts.
    right_shift = _explicit_bilinear(inst, left, x)
    right = [(value - right_shift) % p for value in x]
    return left, right


def _explicit_braid_side(inst, triple, left_side):
    values = [list(vector) for vector in triple]
    positions = (0, 1, 0) if left_side else (1, 0, 1)
    for position in positions:
        first, second = _explicit_braiding(
            inst, values[position], values[position + 1]
        )
        values[position], values[position + 1] = first, second
    return values


def selftest() -> dict:
    """Run the mandatory correctness, density, adversary, scale, and G9 gates."""
    report = {}

    # G1: every preset, several independent seeds, plus exact field checks.
    g1_attempts = 0
    g1_successes = 0
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            instance = make_instance(seed=seed, **params)
            ok, _ = verify(instance, instance["answer"])
            g1_attempts += 1
            g1_successes += int(ok)
            json_native &= json.loads(json.dumps(instance["answer"])) == instance["answer"]
    prime_checks = {
        name: _is_prime_64(data["p"]) for name, data in _FIELDS.items()
    }
    demo_audit = make_instance(seed=0, **DIFFICULTY["demo"])
    p_demo, n_demo = demo_audit["p"], demo_audit["n"]
    a_vector = [
        demo_audit["a_scale"] * pow(demo_audit["omega_inverse"], i, p_demo)
        % p_demo
        for i in range(n_demo)
    ]
    b_vector = [
        demo_audit["b_scale"] * pow(demo_audit["omega"], i, p_demo) % p_demo
        for i in range(n_demo)
    ]
    direct_left, direct_right = _explicit_braiding(demo_audit, a_vector, b_vector)
    direct_action_match = (
        direct_left
        == [
            (value + demo_audit["answer"]["left"][0]) % p_demo
            for value in b_vector
        ]
        and direct_right
        == [
            (value + demo_audit["answer"]["right"][0]) % p_demo
            for value in a_vector
        ]
    )
    identity_rng = random.Random(0xBACE)
    involution_checks = 0
    braid_checks = 0
    for _ in range(24):
        x = [identity_rng.randrange(p_demo) for _ in range(n_demo)]
        y = [identity_rng.randrange(p_demo) for _ in range(n_demo)]
        z = [identity_rng.randrange(p_demo) for _ in range(n_demo)]
        first, second = _explicit_braiding(demo_audit, x, y)
        back = _explicit_braiding(demo_audit, first, second)
        involution_checks += int(back == (x, y))
        triple = (x, y, z)
        braid_checks += int(
            _explicit_braid_side(demo_audit, triple, True)
            == _explicit_braid_side(demo_audit, triple, False)
        )
    report["G1_planted_verifies"] = {
        "pass": g1_successes == g1_attempts
        and json_native
        and all(prime_checks.values())
        and direct_action_match
        and involution_checks == 24
        and braid_checks == 24,
        "verified": g1_successes,
        "attempts": g1_attempts,
        "answer_json_native": json_native,
        "field_prime_checks": prime_checks,
        "direct_demo_action_match": direct_action_match,
        "explicit_involution_checks": involution_checks,
        "explicit_braid_identity_checks": braid_checks,
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=12_345, **shipping_params)
    planted = json.loads(json.dumps(inst["answer"]))

    # G2: five corruption categories, deliberately exercising distinct checks.
    corruptions = {}
    variants = {
        "drop": {"left": planted["left"][:1], "right": planted["right"]},
        "swap": {"left": list(reversed(planted["left"])), "right": planted["right"]},
        "duplicate": {"left": planted["left"], "right": planted["right"] + [1]},
        "empty": {},
        "out_of_range": {"left": [inst["p"], 1], "right": planted["right"]},
    }
    for name, candidate in variants.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(reasons) == len(corruptions),
        "corruptions": corruptions,
        "distinct_reasons": len(reasons),
    }

    # G3: realistic prose, a markdown fence, whitespace, and exact round-trip.
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I used the brace actions exactly.\n<answer>\n```json\n{encoded}\n```\n</answer>\n"
    parsed = parse_answer(response)
    malformed = parse_answer("Here is no tagged or JSON answer: perhaps zero?")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and malformed is None,
        "realistic_response_recovered": parsed == inst["answer"],
        "garbage_returns_none": malformed is None,
    }

    # G4: sample the exact structure-aware language (two monic affine polys).
    guess_rng = random.Random(0x150702602)
    expected_constants = _reference_constants(inst)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(
            candidate["left"][0] == expected_constants[0]
            and candidate["right"][0] == expected_constants[1]
        )
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6 and guess_total >= 200_000,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "exact_probability": 1 / search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length(),
        "sampling_prior": "uniform constants in the two stated monic affine polynomials",
    }

    # G6 and the Track-B reference algorithm, over eight shipping instances.
    attack_names = (
        "coefficient_magnitude_outlier",
        "flip_map_ansatz",
        "constant_term_only_greedy",
        "short_prefix_horner",
        "random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    compact_successes = 0
    compact_seconds = 0.0

    for seed in range(80, 88):
        test_inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "coefficient_magnitude_outlier": _outlier_attack(test_inst),
            "flip_map_ansatz": _answer(0, 0),
            "constant_term_only_greedy": _constant_term_attack(test_inst),
            "short_prefix_horner": _short_prefix_attack(test_inst),
        }
        for name, candidate in candidates.items():
            start = time.perf_counter()
            solved = verify(test_inst, candidate)[0]
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(solved)

        restart_rng = random.Random(seed ^ 0xBAD5EED)
        start = time.perf_counter()
        restart_solved = False
        for _ in range(256):
            if verify(test_inst, random_candidate(test_inst, restart_rng))[0]:
                restart_solved = True
                break
        attack_seconds["random_restart_256"] += time.perf_counter() - start
        successes["random_restart_256"] += int(restart_solved)

        start = time.perf_counter()
        reference = _reference_constants(test_inst)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(verify(test_inst, _answer(*reference))[0])

        start = time.perf_counter()
        compact = _compact_constants(test_inst)
        compact_seconds += time.perf_counter() - start
        compact_successes += int(verify(test_inst, _answer(*compact))[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference_operations = 4 * inst["n"] + 9
    compact_operations = 5 * inst["window"] + 9
    reference_algorithm = {
        "name": "two full Horner evaluations of the circulant symbol",
        "complexity": "O(n) exact field operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
        "intended_compact_route": {
            "name": "low-degree quotient plus vanishing-factor decomposition",
            "operations": compact_operations,
            "wall_clock_sec": round(compact_seconds / 8, 6),
            "solves": f"{compact_successes}/8",
        },
    }

    # G5: shipping density plus measured costs at shipping, not a reduced proxy.
    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": 1 / search_space(inst),
        "shipping_exact_solution_count": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference_algorithm["wall_clock_sec"],
        "reference_operation_count": reference_operations,
    }

    # G7: grow the dense haystack at fixed certificate size.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and len(render(doubled)) > len(render(inst))
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "answer_atoms_shipping": _atomic_elements(inst["answer"]),
        "answer_atoms_doubled": _atomic_elements(doubled["answer"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
        "reference_operations_shipping": 4 * inst["n"] + 9,
        "reference_operations_doubled": 4 * doubled["n"] + 9,
    }

    # G8: affine relabellings and compositions in the cyclic coordinate group.
    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    transformations_per_seed = 7
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping_params)
        key = canonical_key(original)
        variants = (
            _affine_relabel(original, multiplier=1, shift=1),
            _affine_relabel(original, multiplier=3, shift=0),
            _affine_relabel(original, multiplier=5, shift=0),
            _affine_relabel(original, multiplier=-1, shift=0),
            _affine_relabel(original, multiplier=3, shift=37),
            _affine_relabel(original, multiplier=-1, shift=91),
            _affine_relabel(original, multiplier=15, shift=112),
        )
        for transformed in variants:
            invariant_count += int(canonical_key(transformed) == key)
            real_transform_count += int(
                verify(transformed, original["answer"])[0]
            )
        unrelated_keys.append(key)
    expected_invariants = 20 * transformations_per_seed
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == expected_invariants
        and real_transform_count == expected_invariants
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariant_attempts": expected_invariants,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "cyclic coordinate translation",
            "two nontrivial cyclic-group automorphisms",
            "coordinate reflection",
            "automorphisms composed with translations",
            "a three-way composition of the tested generators",
        ],
    }

    # G9: external arm counts are script-owned; the size/effort measurements are local.
    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atomic_elements(inst["answer"])
    worst_answer = _answer(inst["p"] - 1, inst["p"] - 1)
    worst_chars = len(json.dumps(worst_answer, separators=(",", ":")))
    worst_tokens = math.ceil(worst_chars / 4)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and compact_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
