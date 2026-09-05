"""Certified private-key recovery instances from arXiv:2206.06261.

The paper's Algorithm 4 builds a nodal-curve public key from two same-size
primes.  Theorem 4.1 observes that the factors determine the two
Jacobian component orders and hence the private decryption exponent.  This
module samples and *proves* the primes first, constructs the public key, and
asks for the factorization together with that canonical exponent.

Prime generation uses recursively certified Pocklington witnesses.  Miller--
Rabin is only a rejection prefilter; it is never the reason an accepted number
is treated as prime.  The generated certificate is therefore known by
construction, not obtained by attacking the emitted modulus.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "a nodal curve y^2 = x(x^2-a)^2 over Z/NZ",
        "a balanced Blum semiprime public modulus and public exponent",
    ],
    "verification_operations": [
        "exact integer multiplication and division",
        "Euler-criterion checks modulo the submitted factors",
        "exact modular inverse and congruence comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Theorem 4.1: knowing the two factors gives the "
        "component orders and the private exponent"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The Chinese-remainder decomposition of the nodal Jacobian exposes "
        "two prime-field component orders; without the hidden factors, the "
        "private exponent cannot be recomputed from the public modulus."
    ),
    "hardness_basis": (
        "Track A: the factorization assumption in Section 4.1 and Theorem 4.1's "
        "factor-to-private-key construction motivate recovering the balanced factors; "
        "the shipping regime has two "
        "certified 512-bit primes (a 1024-bit Blum semiprime), degree r=2, "
        "and e=65537, while capped Pollard rho used 600000 modular iterations "
        "over eight instances with 0 recoveries; no polynomial-time general "
        "factoring method is known for this distribution."
    ),
    "max_answer_tokens": 240,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON object {p,q,d}.  The factors p<q are distinct n-bit integers "
        "congruent to 3 modulo 4 and not congruent to plus or minus 1 modulo "
        "the displayed prime e; d is forced to be the least positive inverse "
        "of e modulo (p^2-1)(q^2-1)."
    ),
    "bounds": {
        "fields": ["p", "q", "d"],
        "factor_bits": "exactly the displayed n",
        "factor_congruence": "p = q = 3 (mod 4)",
        "ordering": "p < q",
        "private_exponent": "1 <= d < (p^2-1)(q^2-1), uniquely determined",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 5, "public_exponent": 7},
    "easy": {"n": 512, "public_exponent": 65537},
    "medium": {"n": 640, "public_exponent": 65537},
    "hard": {"n": 768, "public_exponent": 65537},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The private exponent is governed by the Chinese-remainder decomposition "
    "of the nodal Jacobian into its two hidden prime-field components."
)
PLACEBO_HINT: str = (
    "The private exponent should be written as its least positive representative "
    "with all three requested fields in the stated order."
)

# Filled from the script-owned harden.py runs after the three arms complete.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
STEP 0.  Theorem 1.2 fixes the native single-polynomial representation:
deg(h)<deg(f) and gcd(f,x-h^2)=1.  Lemma 1.4 and Algorithm 1 give its exact
group law.  Algorithm 4 in Section 3 fixes key generation over Z/nZ.  For
degree r, it uses component orders p^r plus or minus 1 and q^r plus or minus
1, their product K, and d=e^(-1) mod K.  Theorem 4.1 is the
certificate-producing result: once p and q are known, K and d follow.

This family uses f(x)=x^2-a, certified primes p=q=3 (mod 4), and a quadratic
nonresidue modulo each factor.  A root alpha of f has norm -a.  Both -1 and a
are nonsquares in this congruence regime, so -a is a square; alpha is therefore
a square in each quadratic extension and both split torus/Jacobian component
orders are p^2-1 and q^2-1.  The certificate contains the paper's factorization
trapdoor and its canonical private exponent.  Generation proves each factor with a
recursive Pocklington certificate before multiplying them; Miller--Rabin is
only a speed prefilter.  It then chooses a and computes d.  It never factors a
completed instance.

This is a paper-licensed cryptanalytic reduction, not native curve-arithmetic
search: Theorem 4.1 explicitly makes factorization sufficient.
Track A is based on balanced-semiprime factoring, not on the paper's stronger
informal belief that root extraction in the nodal Jacobian is harder than RSA.
The paper itself supplies the decisive easy regime: known factors make key
recovery immediate.  Section 4.2 additionally says degrees two and three make
the group arithmetic integer-only; this does not reveal the factors, but it
prevents us from claiming hardness merely from expensive polynomial algebra.

The generator draws both factors from the same certified-prime procedure.  It
rejects close pairs and the two residues that make e divide a component order.
The curve coefficient is sampled uniformly subject to being a nonresidue in
both components.  The outlier probe takes gcds of visible coefficients, the
greedy probe is bounded Fermat factoring, random restart guesses certificates
from the exact declared language, Pollard p-1 probes smooth component factors,
and capped Pollard rho is the domain-standard implemented factoring attack.
General number field sieve was not available in the standard-library-only
harness and remains an explicit caveat.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
             31, 37, 41, 43, 47, 53, 59, 61, 67, 71)
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
_ENUMERATION_CAP = 200_000
_RHO_LOOPS = 25_000
_FERMAT_STEPS = 20_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, public_exponent):
    if not _is_int(n) or n < 5 or n > 1088:
        raise ValueError("n must be an integer from 5 through 1088")
    if not _is_int(public_exponent) or public_exponent < 3:
        raise ValueError("public_exponent must be an odd prime at least 3")
    if public_exponent % 2 == 0 or not _trial_prime(public_exponent):
        raise ValueError("public_exponent must be prime")


def _trial_prime(value):
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    return all(value % divisor for divisor in range(3, math.isqrt(value) + 1, 2))


def _probable_prime_prefilter(value):
    """Strong probable-prime prefilter; never used as a primality proof."""
    if value < 2:
        return False
    for prime in _SMALL_PRIMES:
        if value % prime == 0:
            return value == prime
    odd_part = value - 1
    twos = 0
    while odd_part % 2 == 0:
        twos += 1
        odd_part //= 2
    for base in _MR_BASES:
        if base >= value:
            continue
        x = pow(base, odd_part, value)
        if x in (1, value - 1):
            continue
        for _ in range(twos - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _pocklington_witness(value, prime_factor, rng):
    exponent = (value - 1) // prime_factor
    for _ in range(96):
        base = rng.randrange(2, value - 1)
        if (pow(base, value - 1, value) == 1
                and math.gcd(pow(base, exponent, value) - 1, value) == 1):
            return base
    return None


def _verify_prime_certificate(cert):
    value = cert.get("n") if isinstance(cert, dict) else None
    if not _is_int(value) or value < 2:
        return False
    if cert.get("kind") == "trial":
        return value <= (1 << 18) and _trial_prime(value)
    if cert.get("kind") != "pocklington":
        return False
    sub = cert.get("sub")
    if not _verify_prime_certificate(sub):
        return False
    q = sub["n"]
    k = cert.get("k")
    witnesses = cert.get("witnesses")
    if not _is_int(k) or k < 1 or value != 2 * q * k + 1:
        return False
    known_factor = 2 * q
    if known_factor * known_factor <= value:
        return False
    if not isinstance(witnesses, dict):
        return False
    for prime_factor, key in ((2, "2"), (q, "q")):
        base = witnesses.get(key)
        if not _is_int(base) or not (2 <= base < value - 1):
            return False
        if pow(base, value - 1, value) != 1:
            return False
        if math.gcd(pow(base, (value - 1) // prime_factor, value) - 1,
                    value) != 1:
            return False
    return True


def _certified_prime(bits, rng):
    """Return (prime, Pocklington certificate), always 3 modulo 4."""
    if bits <= 18:
        lower = 1 << (bits - 1)
        upper = 1 << bits
        while True:
            value = rng.randrange(lower | 1, upper, 2)
            if value % 4 != 3:
                value += 2
            if value < upper and _trial_prime(value):
                cert = {"kind": "trial", "n": value}
                assert _verify_prime_certificate(cert)
                return value, cert

    sub_bits = (bits + 2) // 2
    while True:
        q, subcert = _certified_prime(sub_bits, rng)
        lower_k = max(1, ((1 << (bits - 1)) - 1 + 2 * q - 1) // (2 * q))
        upper_k = min(2 * q - 1, ((1 << bits) - 2) // (2 * q))
        if lower_k % 2 == 0:
            lower_k += 1
        if upper_k % 2 == 0:
            upper_k -= 1
        if lower_k <= upper_k:
            break

    for _ in range(200_000):
        k = rng.randrange(lower_k, upper_k + 1, 2)
        value = 2 * q * k + 1
        if value.bit_length() != bits or not _probable_prime_prefilter(value):
            continue
        witness_2 = _pocklington_witness(value, 2, rng)
        witness_q = _pocklington_witness(value, q, rng)
        if witness_2 is None or witness_q is None:
            continue
        cert = {
            "kind": "pocklington",
            "n": value,
            "k": k,
            "witnesses": {"2": witness_2, "q": witness_q},
            "sub": subcert,
        }
        if _verify_prime_certificate(cert):
            return value, cert
    raise RuntimeError("certified-prime search exhausted its explicit cap")


def _factor_pair(bits, exponent, rng):
    minimum_gap = 1 << max(1, bits - 3)
    for _ in range(128):
        p, p_cert = _certified_prime(bits, rng)
        q, q_cert = _certified_prime(bits, rng)
        if p > q:
            p, q = q, p
            p_cert, q_cert = q_cert, p_cert
        if p == q or q - p <= minimum_gap:
            continue
        if p % exponent in (1, exponent - 1):
            continue
        if q % exponent in (1, exponent - 1):
            continue
        assert _verify_prime_certificate(p_cert)
        assert _verify_prime_certificate(q_cert)
        return p, q
    raise RuntimeError("could not construct a separated certified prime pair")


def _curve_nonresidue(modulus, p, q, rng):
    for _ in range(1024):
        value = rng.randrange(2, modulus - 1)
        if math.gcd(value * (value - 1) * (value + 1), modulus) != 1:
            continue
        if pow(value, (p - 1) // 2, p) != p - 1:
            continue
        if pow(value, (q - 1) // 2, q) != q - 1:
            continue
        return value
    raise RuntimeError("could not sample a simultaneous quadratic nonresidue")


def _component_product(p, q):
    return (p * p - 1) * (q * q - 1)


def _certificate(p, q, exponent):
    order_product = _component_product(p, q)
    return {"p": p, "q": q, "d": pow(exponent, -1, order_product)}


def make_instance(n, seed=0, **params) -> dict:
    """Construct a public key from a certified factor/private-key witness."""
    public_exponent = params.pop("public_exponent", 65537)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, public_exponent)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    p, q = _factor_pair(n, public_exponent, rng)
    modulus = p * q
    curve_a = _curve_nonresidue(modulus, p, q, rng)
    answer = _certificate(p, q, public_exponent)
    return {
        "factor_bits": n,
        "modulus": modulus,
        "public_exponent": public_exponent,
        "degree": 2,
        "curve_a": curve_a,
        "curve_polynomial": [(-curve_a) % modulus, 0, 1],
        "answer": answer,
    }


def _format_answer(answer):
    return json.dumps(answer, separators=(",", ":"))


def render(inst) -> str:
    statement = f"""Private-key recovery for a nodal-curve public key

All integer arithmetic below is exact.  Let N be a composite integer known to
be the product of two distinct {inst['factor_bits']}-bit primes p<q.  Both
primes are congruent to 3 modulo 4.  Over Z/NZ consider

    f(x) = x^2 - a,  where a = {inst['curve_a']},
    C: y^2 = x f(x)^2.

The value a is a quadratic nonresidue modulo p and modulo q, so f is
irreducible over both prime fields.  In this stated degree-two regime, the two
generalized-Jacobian component orders are p^2-1 and q^2-1.  Define

    K = (p^2 - 1)(q^2 - 1).

The public data are

    N = {inst['modulus']}
    e = {inst['public_exponent']}
    f coefficients, constant first = {inst['curve_polynomial']}

Recover the private-key certificate.  Submit exactly one JSON object with
integer fields p, q, and d.  It must satisfy p<q, p*q=N, and d must be the
unique least positive integer below K satisfying e*d congruent to 1 modulo K.
Each factor is also neither +1 nor -1 modulo e.  No signs, repeats, omitted
fields, or alternative representatives are allowed.

Give your final answer inside <answer></answer> tags, as compact JSON.
Example: <answer>{{"p":19,"q":31,"d":12345}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        payload = match.group(1).strip()
    else:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text,
                           re.I | re.S)
        payload = fenced.group(1).strip() if fenced else text.strip()
    try:
        value = json.loads(payload)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def verify(inst, answer):
    """Verify a submitted trapdoor without consulting ``inst['answer']``."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "empty certificate"
    if set(answer) != {"p", "q", "d"}:
        return False, "certificate must contain exactly p, q, and d"
    p, q, d = answer["p"], answer["q"], answer["d"]
    if not all(_is_int(value) for value in (p, q, d)):
        return False, "all certificate fields must be integers"
    if p == q:
        return False, "the two factors must be distinct"
    if p > q:
        return False, "factors must be in increasing order"
    bits = inst["factor_bits"]
    if p.bit_length() != bits or q.bit_length() != bits:
        return False, "both factors must have the declared bit length"
    exponent = inst["public_exponent"]
    if p % 4 != 3 or q % 4 != 3:
        return False, "both factors must be 3 modulo 4"
    if p % exponent in (1, exponent - 1) or q % exponent in (1, exponent - 1):
        return False, "a factor lies in a forbidden public-exponent residue"
    if p * q != inst["modulus"]:
        return False, "submitted factors do not multiply to N"
    a = inst["curve_a"]
    if math.gcd(a, p * q) != 1:
        return False, "curve coefficient is not a unit modulo the factors"
    if (pow(a, (p - 1) // 2, p) != p - 1
            or pow(a, (q - 1) // 2, q) != q - 1):
        return False, "f(x) is not irreducible over both submitted prime fields"
    order_product = _component_product(p, q)
    if not (1 <= d < order_product):
        return False, "private exponent is outside its canonical range"
    if exponent * d % order_product != 1:
        return False, "private exponent is not the inverse of e modulo K"
    return True, "ok"


def _count_residue(lower, upper, modulus, residue):
    """Count integers x in [lower,upper) with x == residue (mod modulus)."""
    first = lower + ((residue - lower) % modulus)
    if first >= upper:
        return 0
    return 1 + (upper - 1 - first) // modulus


def _candidate_factor_count(bits, exponent):
    lower, upper = 1 << (bits - 1), 1 << bits
    total = _count_residue(lower, upper, 4, 3)
    modulus = 4 * exponent
    excluded = 0
    inverse_four = pow(4, -1, exponent)
    for target in (1, exponent - 1):
        k = (target - 3) * inverse_four % exponent
        residue = 3 + 4 * k
        excluded += _count_residue(lower, upper, modulus, residue)
    return total - excluded


def _sample_factor_shaped(bits, exponent, rng):
    lower, upper = 1 << (bits - 1), 1 << bits
    first = lower + ((3 - lower) % 4)
    count = 1 + (upper - 1 - first) // 4
    while True:
        value = first + 4 * rng.randrange(count)
        if value % exponent not in (1, exponent - 1):
            return value


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    bits = inst["factor_bits"]
    exponent = inst["public_exponent"]
    p = _sample_factor_shaped(bits, exponent, rng)
    q = _sample_factor_shaped(bits, exponent, rng)
    while q == p:
        q = _sample_factor_shaped(bits, exponent, rng)
    if p > q:
        p, q = q, p
    # A solver who guessed the factors gets d for free, so the structure-aware
    # prior computes it instead of independently guessing another huge integer.
    return _certificate(p, q, exponent)


def search_space(inst):
    candidates = _candidate_factor_count(
        inst["factor_bits"], inst["public_exponent"])
    return candidates * (candidates - 1) // 2


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    bits = inst["factor_bits"]
    exponent = inst["public_exponent"]
    lower, upper = 1 << (bits - 1), 1 << bits
    values = [value for value in range(lower, upper)
              if value % 4 == 3
              and value % exponent not in (1, exponent - 1)]
    count = 0
    for p, q in itertools.combinations(values, 2):
        candidate = _certificate(p, q, exponent)
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    # For p,q=3 mod 4, all simultaneous nonsquare a values differ by a fourth
    # power in both prime fields.  They therefore give isomorphic scaled curves.
    normal = {
        "modulus": inst["modulus"],
        "public_exponent": inst["public_exponent"],
        "degree": 2,
        "curve_square_class": "simultaneous_nonsquare",
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    if not isinstance(params, dict):
        raise TypeError("params must be a dict")
    current = params.get("n")
    exponent = params.get("public_exponent", 65537)
    _validate_parameters(current, exponent)
    if current >= 1088:
        return "cap_bound"
    harder = min(1088, current + 64)
    return {"n": harder, "public_exponent": exponent}


def _answer_from_factor(inst, factor):
    if not _is_int(factor) or not (1 < factor < inst["modulus"]):
        return None
    if inst["modulus"] % factor:
        return None
    other = inst["modulus"] // factor
    p, q = sorted((factor, other))
    try:
        return _certificate(p, q, inst["public_exponent"])
    except ValueError:
        return None


def _attack_curve_gcd(inst):
    modulus = inst["modulus"]
    probes = (
        inst["curve_a"], inst["curve_a"] - 1, inst["curve_a"] + 1,
        inst["public_exponent"], inst["curve_polynomial"][0],
    )
    for probe in probes:
        factor = math.gcd(probe, modulus)
        if 1 < factor < modulus:
            return _answer_from_factor(inst, factor), len(probes)
    return None, len(probes)


def _attack_fermat(inst, steps=_FERMAT_STEPS):
    modulus = inst["modulus"]
    x = math.isqrt(modulus)
    if x * x < modulus:
        x += 1
    for iteration in range(1, steps + 1):
        square = x * x - modulus
        y = math.isqrt(square)
        if y * y == square:
            factor = x - y
            return _answer_from_factor(inst, factor), iteration
        x += 1
    return None, steps


def _primes_through(bound):
    sieve = bytearray(b"\x01") * (bound + 1)
    sieve[:2] = b"\x00\x00"
    for value in range(2, math.isqrt(bound) + 1):
        if sieve[value]:
            sieve[value * value:bound + 1:value] = b"\x00" * (
                (bound - value * value) // value + 1)
    return [value for value in range(2, bound + 1) if sieve[value]]


def _attack_pollard_p1(inst, bound=1000):
    modulus = inst["modulus"]
    value = 2
    operations = 0
    for prime in _primes_through(bound):
        power = prime
        while power * prime <= bound:
            power *= prime
        value = pow(value, power, modulus)
        operations += power.bit_length()
    factor = math.gcd(value - 1, modulus)
    return (_answer_from_factor(inst, factor)
            if 1 < factor < modulus else None), operations


def _attack_pollard_rho(inst, seed, loops=_RHO_LOOPS):
    modulus = inst["modulus"]
    rng = random.Random(seed)
    modular_iterations = 0
    restarts = 4
    per_restart = max(1, loops // restarts)
    for _ in range(restarts):
        x = rng.randrange(2, modulus - 1)
        y = x
        constant = rng.randrange(1, modulus - 1)
        for _ in range(per_restart):
            x = (x * x + constant) % modulus
            y = (y * y + constant) % modulus
            y = (y * y + constant) % modulus
            modular_iterations += 3
            factor = math.gcd(abs(x - y), modulus)
            if 1 < factor < modulus:
                return _answer_from_factor(inst, factor), modular_iterations
            if factor == modulus:
                break
    return None, modular_iterations


def _attack_random_restart(inst, seed, attempts=256):
    rng = random.Random(seed)
    for number in range(1, attempts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, number
    return None, attempts


def _euclid_steps(a, b):
    steps = 0
    while b:
        a, b = b, a % b
        steps += 1
    return steps


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}

    g1_failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=1000 + seed, **params)
            checks += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": checks,
        "failures": g1_failures,
    }

    shipping = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=220606261, **shipping)
    answer = dict(inst["answer"])
    p, q = answer["p"], answer["q"]
    order_product = _component_product(p, q)
    corruptions = {
        "drop": {"p": p, "d": answer["d"]},
        "swap": {"p": q, "q": p, "d": answer["d"]},
        "duplicate": {"p": p, "q": p, "d": answer["d"]},
        "empty": {},
        "out_of_range": {"p": p, "q": q, "d": order_product},
    }
    reasons = {name: verify(inst, value)[1]
               for name, value in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": (all(not verify(inst, value)[0]
                     for value in corruptions.values())
                 and len(set(reasons.values())) == len(reasons)),
        "reasons": reasons,
    }

    model_reply = (
        "I used the component-order product and checked the inverse.\n"
        "```json\n<answer>" + _format_answer(answer)
        + "</answer>\n```\nThe multiplication also checks."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
        and parse_answer("not an answer") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(4404)
    guess_hits = 0
    for _ in range(samples):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and guess_hits / samples < 1e-6,
        "hits": guess_hits,
        "total": samples,
        "observed_probability": guess_hits / samples,
        "structure_aware": (
            "uniform unordered pair of correctly sized 3-mod-4 candidates, "
            "with d deterministically recomputed from that pair"
        ),
        "candidate_space": search_space(inst),
    }

    attack_names = (
        "outlier_curve_coefficient_gcd",
        "greedy_fermat_20000",
        "random_restart_256",
        "pollard_p_minus_1_B1000",
        "pollard_rho_factoring_75000",
    )
    attack_records = {
        name: {"successes": 0, "attempts": 8, "operations": 0,
               "wall_clock_sec": 0.0}
        for name in attack_names
    }
    for seed in range(8):
        attack_inst = make_instance(seed=7000 + seed, **shipping)
        runners = {
            attack_names[0]: lambda: _attack_curve_gcd(attack_inst),
            attack_names[1]: lambda: _attack_fermat(attack_inst),
            attack_names[2]: lambda: _attack_random_restart(
                attack_inst, 900_000 + seed),
            attack_names[3]: lambda: _attack_pollard_p1(attack_inst),
            attack_names[4]: lambda: _attack_pollard_rho(
                attack_inst, 800_000 + seed),
        }
        for name in attack_names:
            started = time.perf_counter()
            candidate, operations = runners[name]()
            elapsed = time.perf_counter() - started
            success = candidate is not None and verify(attack_inst, candidate)[0]
            attack_records[name]["successes"] += int(success)
            attack_records[name]["operations"] += operations
            attack_records[name]["wall_clock_sec"] += elapsed
    for value in attack_records.values():
        value["wall_clock_sec"] = round(value["wall_clock_sec"], 6)

    demo = make_instance(seed=17, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo)
    rho = attack_records[attack_names[4]]
    report["G5_density_and_baseline"] = {
        "pass": (exact_demo == 1 and guess_hits == 0
                 and rho["operations"] > 0),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": samples,
        "shipping_observed_valid_fraction": guess_hits / samples,
        "shipping_candidate_space": search_space(inst),
        "demo_exact_valid_answers": exact_demo,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec": rho["wall_clock_sec"],
        "baseline_modular_iterations": rho["operations"],
        "baseline_attempts": rho["attempts"],
    }
    report["G6_adversary_panel"] = {
        "pass": all(value["successes"] == 0
                    for value in attack_records.values()),
        "attacks": attack_records,
        "standard_algorithm": (
            "the standard-library panel implements capped Pollard rho as its "
            "general-purpose factoring algorithm; GNFS is named in the caveats "
            "but was unavailable under the dependency constraint"
        ),
    }

    spaces = [search_space(make_instance(seed=3100, **params))
              for name, params in DIFFICULTY.items() if name != "demo"]
    doubled_params = dict(shipping)
    doubled_params["n"] = min(1024, 2 * doubled_params["n"])
    started = time.perf_counter()
    doubled = make_instance(seed=8808, **doubled_params)
    doubled_seconds = time.perf_counter() - started
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": all(left < right for left, right in zip(spaces, spaces[1:]))
        and doubled_ok,
        "non_demo_search_space_bits": [value.bit_length() for value in spaces],
        "doubled_n": doubled_params["n"],
        "doubled_build_sec": round(doubled_seconds, 6),
        "doubled_verifies": doubled_ok,
    }

    invariance_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=12000 + seed, **shipping)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        relabel_rng = random.Random(99000 + seed)
        units = []
        while len(units) < 2:
            unit = relabel_rng.randrange(2, base["modulus"] - 1)
            if math.gcd(unit, base["modulus"]) == 1:
                units.append(unit)
        variants = []
        current_a = base["curve_a"]
        for unit in (units[0], units[1], units[0] * units[1] % base["modulus"]):
            moved = dict(base)
            inverse_fourth = pow(pow(unit, 4, base["modulus"]),
                                 -1, base["modulus"])
            moved_a = current_a * inverse_fourth % base["modulus"]
            moved["curve_a"] = moved_a
            moved["curve_polynomial"] = [
                (-moved_a) % base["modulus"], 0, 1]
            variants.append(moved)
        for moved in variants:
            invariance_checks += int(canonical_key(moved) == base_key)
            carried_checks += int(verify(moved, base["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == 60 and carried_checks == 60
                 and len(set(unrelated_keys)) == 20),
        "invariance_successes": invariance_checks,
        "invariance_attempts": 60,
        "carried_witness_successes": carried_checks,
        "carried_witness_attempts": 60,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "transformations": (
            "x=u^2 X and y=u^5 Y, including two scalings and their composition"
        ),
    }

    measured = [make_instance(seed=15000 + seed, **shipping)
                for seed in range(20)]
    blobs = [json.dumps(value["answer"]) for value in measured]
    answer_chars = max(map(len, blobs))
    answer_tokens = max((len(blob) + 3) // 4 for blob in blobs)
    answer_elements = max(_answer_atoms(value["answer"]) for value in measured)
    intended_operations = 0
    for value in measured:
        cert = value["answer"]
        component = _component_product(cert["p"], cert["q"])
        # Two squares, two subtractions, one product, plus exact Euclid steps.
        intended_operations = max(
            intended_operations,
            5 + _euclid_steps(value["public_exponent"], component),
        )
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and answer_tokens <= 500 and intended_operations <= 300
                   and answer_tokens <= PROBLEM_PROFILE["max_answer_tokens"])
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "tokens": 500,
                 "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True for key, value in report.items()
        if key.startswith("G")
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
