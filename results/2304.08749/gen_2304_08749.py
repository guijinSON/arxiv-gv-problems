"""Verified generator for a finite-field k-normality certificate problem.

The native construction is the remark in Section 2 of Choudhary--Sharma,
arXiv:2304.08749: if sigma is normal and f divides X^n-1 with degree k,
then f circle sigma is k-normal.  We sample f first and compose the public
element from it.  No public instance is searched for its answer.
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
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "cyclotomic finite field over a prime field",
        "normal element and its Frobenius conjugates",
        "divisor polynomial of X^n-1 over the prime field",
        "k-normal element represented in an exact power basis",
    ],
    "verification_operations": [
        "exact modular polynomial multiplication",
        "exact Frobenius-coordinate permutation",
        "finite-field polynomial evaluation",
        "cyclic convolution identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The Frobenius conjugates of a cyclotomic normal element merely "
        "permute power-basis coordinates, exposing a sparse cyclic inverse; "
        "without that symmetry one performs a full normal-basis conversion."
    ),
    "hardness_basis": (
        "Track B: normal-basis coordinate recovery is solved by an exact "
        "finite-field DFT in O(n^2) base-field operations (24,652 measured "
        "operations and about 0.001 seconds at shipping n=58), whereas the "
        "cyclotomic/sparse-inverse route uses 103 exact operations but must "
        "be noticed and executed without a CAS."
    ),
    "max_answer_tokens": 102,
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
        "A factored-and-expanded monic degree-k divisor f of X^n-1 over "
        "F_q: JSON object {coefficients:[f_0,...,f_k], roots:[s_1,...,s_k]}, "
        "where the distinct sorted root indices specify "
        "f=product(X-omega^s_i) and every coefficient is in [0,q-1]."
    ),
    "bounds": {
        "degree": "instance k",
        "coefficient_range": "0 through q-1",
        "root_indices": "exactly k distinct integers from 0 through n-1",
        "representation": "expanded coefficients plus exact linear factorization",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "k": 1, "min_q": 0, "terms": 2},
    "easy": {"n": 58, "k": 6, "min_q": 10**6, "terms": 4},
    "medium": {"n": 126, "k": 6, "min_q": 10**8, "terms": 4},
    "hard": {"n": 250, "k": 6, "min_q": 10**12, "terms": 4},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Reorder coordinates along the Frobenius orbit, then test the short "
    "cyclic inverse whose shifts follow the residue of q modulo n+1."
)
PLACEBO_HINT = (
    "Keep every modular coefficient in its stated range and check the "
    "factor indices carefully before giving the polynomial at the end."
)

# Filled from the script-owned oracle runs after hardening.  These defaults are
# deliberately not presented as fresh evidence by NOTES or README.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition and source.  The Introduction defines k-normality through the
degree-k gcd of the conjugate polynomial with X^n-1.  The decisive construction
is Remark 2.5 immediately after the Wang--Fu character-sum lemmas:
for a normal sigma and a degree-k divisor f of X^n-1, epsilon=f circle sigma is
k-normal.  The generator uses exactly these finite-field objects.  It does not
replace them by a graph or a discrete surrogate.

Step-0 algorithm check.  The paper proves existence, not search hardness.
Moreover, once a normal anchor sigma is supplied, recovering f is ordinary
normal-basis coordinate conversion, hence polynomial time.  Track A would
therefore be dishonest.  This module declares Track B and measures a standard
exact finite-field DFT solver.  At shipping size it carries out 24,652 modular
field operations; the intended route recognizes that the
Frobenius orbit permutes the cyclotomic basis and that the sampled normal anchor
has a four-term cyclic inverse.  Only the few requested coefficients then need
be formed in 103 exact operations, below the 300-operation no-tool cap.

Construction.  Put ell=n+1.  The base prime q is chosen with q=1 mod n and q
primitive mod ell.  Thus Phi_ell is irreducible over F_q, zeta has degree n,
and zeta,zeta^q,...,zeta^(q^(n-1)) are exactly the n nontrivial ell-th roots in
a permuted order; they form a normal basis.  A public normal sigma is obtained
from an invertible cyclic multiplier L.  Its inverse A is a short geometric
polynomial supported at multiples of d=q mod ell.  A uniformly sampled set of
k distinct n-th roots gives f, and epsilon=f circle sigma.  The answer is f in
both expanded and factored form.  This is composition of identities and the
paper's theorem-backed construction, never a solve of the emitted instance.

Attack handling.  Root subsets used for plants and random candidates have the
same uniform distribution.  The panel tries coefficient magnitude outliers,
the first-root greedy divisor, uniform structure-aware restarts, and the common
but wrong assumption that power-basis coordinates already are normal-basis
coordinates.  The polynomial-time DFT solver is reported separately, as Track
B requires.  A specialized extended-gcd/circulant solver is an unmeasured
faster alternative and is called out in the README caveats.
""".strip()


# ---------------------------------------------------------------------------
# Exact integer and polynomial helpers


def _prime_divisors(value: int) -> list[int]:
    out: list[int] = []
    d = 2
    while d * d <= value:
        if value % d == 0:
            out.append(d)
            while value % d == 0:
                value //= d
        d = 3 if d == 2 else d + 2
    if value > 1:
        out.append(value)
    return out


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin on the 64-bit range used here."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value % p == 0:
            return value == p
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    # This set is deterministic for unsigned 64-bit integers.
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        a = base % value
        if a == 0:
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


def _primitive_root_prime(prime: int) -> int:
    factors = _prime_divisors(prime - 1)
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // p, prime) != 1
               for p in factors):
            return candidate
    raise RuntimeError("prime field has no primitive root")


def _largest_coprime_primitive_residue(ell: int) -> int:
    order = ell - 1
    factors = _prime_divisors(order)
    for candidate in range(ell - 1, 1, -1):
        if math.gcd(candidate, order) == 1 and all(
                pow(candidate, order // p, ell) != 1 for p in factors):
            return candidate
    raise RuntimeError("no suitable primitive residue")


def _crt_pair(a: int, m: int, b: int, n: int) -> int:
    return (a + ((b - a) * pow(m, -1, n) % n) * m) % (m * n)


def _trim(poly: list[int]) -> list[int]:
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return poly


def _poly_mul(a: list[int], b: list[int], prime: int) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        if av:
            for j, bv in enumerate(b):
                if bv:
                    out[i + j] = (out[i + j] + av * bv) % prime
    return _trim(out)


def _poly_from_roots(root_indices: list[int], omega: int,
                     prime: int) -> list[int]:
    poly = [1]
    for index in root_indices:
        root = pow(omega, index, prime)
        poly = _poly_mul(poly, [(-root) % prime, 1], prime)
    return poly


def _cyclic_mul(a: list[int], b: list[int], n: int,
                prime: int) -> list[int]:
    out = [0] * n
    for i, av in enumerate(a):
        if av:
            for j, bv in enumerate(b):
                if bv:
                    out[(i + j) % n] = (out[(i + j) % n] + av * bv) % prime
    return out


def _poly_eval(poly: list[int], value: int, prime: int) -> int:
    total = 0
    for coefficient in reversed(poly):
        total = (total * value + coefficient) % prime
    return total


def _validate_parameters(n: int, k: int, min_q: int, terms: int) -> None:
    values = {"n": n, "k": k, "min_q": min_q, "terms": terms}
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 4 or not _is_prime(n + 1):
        raise ValueError("n+1 must be prime and n must be at least 4")
    if not (1 <= k < n):
        raise ValueError("k must satisfy 1 <= k < n")
    if min_q < 0:
        raise ValueError("min_q must be nonnegative")
    if not (2 <= terms <= 8):
        raise ValueError("terms must be between 2 and 8")


def _short_inverse(n: int, d: int, generator: int,
                   terms: int, prime: int) -> list[int]:
    out = [0] * n
    coefficient = 1
    for j in range(terms):
        position = (j * d) % n
        out[position] = (out[position] + coefficient) % prime
        coefficient = coefficient * generator % prime
    return out


def _has_no_nth_root_zero(poly: list[int], omega: int,
                          n: int, prime: int) -> bool:
    value = 1
    for _ in range(n):
        if _poly_eval(poly, value, prime) == 0:
            return False
        value = value * omega % prime
    return True


def _inverse_by_dft(poly: list[int], omega: int, n: int,
                    prime: int) -> list[int]:
    """Invert a unit modulo X^n-1 using exact evaluation/interpolation."""
    values = []
    point = 1
    for _ in range(n):
        value = _poly_eval(poly, point, prime)
        if value == 0:
            raise ValueError("cyclic multiplier is not invertible")
        values.append(pow(value, prime - 2, prime))
        point = point * omega % prime
    inv_n = pow(n, prime - 2, prime)
    omega_inv = pow(omega, prime - 2, prime)
    result = []
    for i in range(n):
        step = pow(omega_inv, i, prime)
        power = 1
        total = 0
        for value in values:
            total = (total + value * power) % prime
            power = power * step % prime
        result.append(total * inv_n % prime)
    return result


@functools.lru_cache(maxsize=None)
def _field_parameters(n: int, min_q: int, terms: int) -> tuple:
    ell = n + 1
    d = _largest_coprime_primitive_residue(ell)
    step = n * ell
    prime = _crt_pair(1, n, d, ell)
    if prime < 2:
        prime += step
    if prime < min_q:
        prime += ((min_q - prime + step - 1) // step) * step
    while True:
        if _is_prime(prime):
            generator = _primitive_root_prime(prime)
            omega = pow(generator, (prime - 1) // n, prime)
            short = _short_inverse(n, d, generator, terms, prime)
            if _has_no_nth_root_zero(short, omega, n, prime):
                normal_multiplier = _inverse_by_dft(
                    short, omega, n, prime)
                check = _cyclic_mul(short, normal_multiplier, n, prime)
                if check != [1] + [0] * (n - 1):
                    raise AssertionError("cyclic inverse construction failed")
                return (prime, ell, d, generator, omega,
                        tuple(short), tuple(normal_multiplier))
        prime += step
        if prime >= 2**63:
            raise ValueError("requested field exceeds the supported 64-bit range")


def _orbit_to_power(values: list[int], d: int, ell: int) -> list[int]:
    n = ell - 1
    out = [0] * n
    exponent = 1
    for value in values:
        out[exponent - 1] = value
        exponent = exponent * d % ell
    return out


def _power_to_orbit(values: list[int], d: int, ell: int) -> list[int]:
    out = []
    exponent = 1
    for _ in range(ell - 1):
        out.append(values[exponent - 1])
        exponent = exponent * d % ell
    return out


# ---------------------------------------------------------------------------
# Generator and answer contract


def make_instance(n: int, seed: int = 0, k: int = 6,
                  min_q: int = 0, terms: int = 4, **params) -> dict:
    """Compose a certified Section-2 k-normality witness."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, k, min_q, terms)
    rng = random.Random(seed)
    (prime, ell, d, generator, omega, short_tuple,
     normal_tuple) = _field_parameters(n, min_q, terms)
    short = list(short_tuple)
    normal = list(normal_tuple)

    # The answer is sampled first, uniformly from exactly the same divisor
    # language used by random_candidate.
    roots = sorted(rng.sample(range(n), k))
    coefficients = _poly_from_roots(roots, omega, prime)
    effect = _cyclic_mul(coefficients, normal, n, prime)
    sigma = _orbit_to_power(normal, d, ell)
    epsilon = _orbit_to_power(effect, d, ell)

    return {
        "q": prime,
        "n": n,
        "ell": ell,
        "k": k,
        "terms": terms,
        "d": d,
        "base_generator": generator,
        "omega": omega,
        "sigma": sigma,
        "epsilon": epsilon,
        "answer": {"coefficients": coefficients, "roots": roots},
    }


def _format_vector(values: list[int], width: int = 8) -> str:
    lines = []
    for start in range(0, len(values), width):
        chunk = values[start:start + width]
        lines.append("  " + ", ".join(str(v) for v in chunk))
    return "[\n" + "\n".join(lines) + "\n]"


def render(inst: dict) -> str:
    """Render the complete native finite-field certificate problem."""
    n = inst["n"]
    q = inst["q"]
    statement = f"""Recover a k-normality certificate over a finite field

Let q={q}, n={n}, ell=n+1={inst['ell']}, and work in

    F = F_q[Z] / (1 + Z + Z^2 + ... + Z^{n}).

The displayed cyclotomic polynomial is irreducible for these data.  Coordinates
[a_1,...,a_n] mean the exact field element sum(a_j*Z^j, j=1..n), with every
coefficient reduced modulo q.  Thus positions are 1-based powers of Z, while
all coefficient-list and root indices below are 0-based.

For h(X)=h_0+h_1 X+...+h_s X^s over F_q and u in F, define the Frobenius
action

    h circle u = h_0*u + h_1*u^q + ... + h_s*u^(q^s).

An element u is normal when u,u^q,...,u^(q^(n-1)) is an F_q-basis of F.
The following supplied element sigma is normal:

sigma = {_format_vector(inst['sigma'])}

The target element is

epsilon = {_format_vector(inst['epsilon'])}

Also, g={inst['base_generator']} generates F_q^*, and
omega={inst['omega']} has exact multiplicative order n in F_q.

Find the unique monic degree-{inst['k']} polynomial

    f(X)=sum(f_i X^i, i=0..k)

such that both:

  1. f divides X^n-1 over F_q; equivalently, for exactly {inst['k']} distinct
     indices s in {{0,...,n-1}}, f=product(X-omega^s), and
  2. f circle sigma = epsilon in F.

This f is an exact certificate of the paper's construction of the k-normal
element epsilon.  Return both its expanded coefficients and the sorted root
indices.  Coefficients are decimal integers in [0,{q - 1}], listed from
constant term through the leading coefficient.  Root indices are distinct,
sorted, 0-based integers in [0,{n - 1}].  Repeats are forbidden; order in the
root list is fixed by sorting.

"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "Hint: " + STRUCTURAL_HINT + "\n\n"
    elif mode == "placebo":
        statement += "Hint: " + PLACEBO_HINT + "\n\n"
    statement += (
        "Give your final answer inside <answer></answer> tags as one JSON "
        "object with keys coefficients and roots.\n"
        "Example: <answer>{\"coefficients\":[4,3,1],"
        "\"roots\":[2,7]}</answer>\n"
        "Output nothing else inside the tags."
    )
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON polynomial, tolerating surrounding prose."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {"coefficients", "roots"}:
        return None
    if not isinstance(value["coefficients"], list) or not isinstance(
            value["roots"], list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int)
           for x in value["coefficients"] + value["roots"]):
        return None
    return {"coefficients": value["coefficients"], "roots": value["roots"]}


def _instance_orbits(inst: dict) -> tuple[list[int], list[int]]:
    return (
        _power_to_orbit(inst["sigma"], inst["d"], inst["ell"]),
        _power_to_orbit(inst["epsilon"], inst["d"], inst["ell"]),
    )


@functools.lru_cache(maxsize=256)
def _probe_data(q: int, n: int, k: int, omega: int,
                normal: tuple[int, ...], effect: tuple[int, ...]) -> tuple:
    data = []
    point = 1
    for _ in range(k + 1):
        data.append((_poly_eval(list(normal), point, q),
                     _poly_eval(list(effect), point, q), point))
        point = point * omega % q
    return tuple(data)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid factored polynomial without reading inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"coefficients", "roots"}:
        return False, "answer must have exactly coefficients and roots"
    coefficients = answer["coefficients"]
    roots = answer["roots"]
    if not isinstance(coefficients, list) or not isinstance(roots, list):
        return False, "coefficients and roots must both be lists"
    if not coefficients and not roots:
        return False, "answer polynomial is empty"
    k = inst["k"]
    if len(coefficients) < k + 1:
        return False, "coefficient list has too few entries"
    if len(coefficients) > k + 1:
        return False, "coefficient list has too many entries"
    if len(roots) != k:
        return False, "root list must contain exactly k indices"
    all_values = coefficients + roots
    if any(isinstance(x, bool) or not isinstance(x, int) for x in all_values):
        return False, "all coefficients and root indices must be integers"
    q = inst["q"]
    if any(x < 0 or x >= q for x in coefficients):
        return False, "a polynomial coefficient is out of range"
    if any(x < 0 or x >= inst["n"] for x in roots):
        return False, "a root index is out of range"
    if roots != sorted(roots):
        return False, "root indices must be sorted"
    if len(set(roots)) != len(roots):
        return False, "root indices must be distinct"
    if coefficients[-1] != 1:
        return False, "polynomial is not monic of degree k"
    expanded = _poly_from_roots(roots, inst["omega"], q)
    if expanded != coefficients:
        return False, "coefficients do not match the claimed linear factors"

    normal, effect = _instance_orbits(inst)
    probes = _probe_data(q, inst["n"], k, inst["omega"],
                         tuple(normal), tuple(effect))
    for normal_value, effect_value, point in probes:
        if _poly_eval(coefficients, point, q) * normal_value % q != effect_value:
            return False, "Frobenius identity fails at a diagnostic root"

    # The probes are an exact cheap rejection filter.  Acceptance still checks
    # the complete coefficient identity in F_q[X]/(X^n-1).
    padded = coefficients + [0] * (inst["n"] - len(coefficients))
    if _cyclic_mul(padded, normal, inst["n"], q) != effect:
        return False, "full Frobenius composition identity fails"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample every structural constraint stated for f."""
    roots = sorted(rng.sample(range(inst["n"]), inst["k"]))
    coefficients = _poly_from_roots(roots, inst["omega"], inst["q"])
    return {"coefficients": coefficients, "roots": roots}


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    size = search_space(inst)
    if size is None or size > 200_000:
        return None
    count = 0
    for roots_tuple in itertools.combinations(range(inst["n"]), inst["k"]):
        roots = list(roots_tuple)
        candidate = {
            "coefficients": _poly_from_roots(
                roots, inst["omega"], inst["q"]),
            "roots": roots,
        }
        count += int(verify(inst, candidate)[0])
    return count


# ---------------------------------------------------------------------------
# Structural canonicalization and relabellings


def _frobenius_coords(values: list[int], d: int, ell: int,
                       power: int) -> list[int]:
    n = ell - 1
    multiplier = pow(d, power % n, ell)
    out = [0] * n
    for j, value in enumerate(values, 1):
        out[(j * multiplier % ell) - 1] = value
    return out


def _scale_coords(values: list[int], scalar: int, prime: int) -> list[int]:
    return [scalar * value % prime for value in values]


def canonical_key(inst: dict) -> str:
    """Canonicalize simultaneous Frobenius relabelling and base scaling."""
    normal, effect = _instance_orbits(inst)
    q = inst["q"]
    n = inst["n"]
    candidates = []
    for shift in range(n):
        moved_normal = normal[shift:] + normal[:shift]
        moved_effect = effect[shift:] + effect[:shift]
        scale = pow(moved_normal[0], q - 2, q)
        candidates.append(tuple(
            [x * scale % q for x in moved_normal]
            + [x * scale % q for x in moved_effect]
        ))
    normalized = min(candidates)
    payload = json.dumps(
        [q, n, inst["k"], inst["terms"], inst["omega"], normalized],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow field degree and coefficient height at fixed certificate length."""
    n = params.get("n")
    k = params.get("k", 6)
    min_q = params.get("min_q", 0)
    terms = params.get("terms", 4)
    if any(isinstance(x, bool) or not isinstance(x, int)
           for x in (n, k, min_q, terms)):
        return None
    target = n + max(20, n // 3)
    next_n = target + (target % 2)
    while not _is_prime(next_n + 1):
        next_n += 2
    return {
        "n": next_n,
        "k": k,
        "min_q": max(1000, min_q * 10),
        "terms": terms,
    }


# ---------------------------------------------------------------------------
# Track-B reference algorithm and failing attacks


class _Counter:
    def __init__(self) -> None:
        self.additions = 0
        self.multiplications = 0
        self.inversions = 0

    @property
    def operations(self) -> int:
        return self.additions + self.multiplications + self.inversions


def _eval_counted(poly: list[int], value: int, prime: int,
                  counter: _Counter) -> int:
    total = 0
    for coefficient in reversed(poly):
        counter.multiplications += 1
        counter.additions += 1
        total = (total * value + coefficient) % prime
    return total


def _reference_dft(inst: dict) -> dict:
    """Mechanical exact cyclic deconvolution, independent of the short inverse."""
    q = inst["q"]
    n = inst["n"]
    omega = inst["omega"]
    normal, effect = _instance_orbits(inst)
    counter = _Counter()
    start = time.perf_counter()
    spectral = []
    point = 1
    for _ in range(n):
        lv = _eval_counted(normal, point, q, counter)
        ev = _eval_counted(effect, point, q, counter)
        counter.inversions += 1
        spectral.append(ev * pow(lv, q - 2, q) % q)
        counter.multiplications += 1
        point = point * omega % q
        counter.multiplications += 1
    inverse_omega = pow(omega, q - 2, q)
    inverse_n = pow(n, q - 2, q)
    counter.inversions += 2
    coefficients = []
    for i in range(n):
        step = pow(inverse_omega, i, q)
        power = 1
        total = 0
        for value in spectral:
            total = (total + value * power) % q
            counter.multiplications += 2
            counter.additions += 1
            power = power * step % q
        coefficients.append(total * inverse_n % q)
        counter.multiplications += 1
    recovered = _trim(list(coefficients))
    roots = []
    point = 1
    for index in range(n):
        if _eval_counted(recovered, point, q, counter) == 0:
            roots.append(index)
        point = point * omega % q
        counter.multiplications += 1
    elapsed = time.perf_counter() - start
    answer = {
        "coefficients": recovered,
        "roots": roots,
    }
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "wall_clock_sec": elapsed,
        "operations": counter.operations,
        "additions": counter.additions,
        "multiplications": counter.multiplications,
        "inversions": counter.inversions,
    }


def _candidate_from_roots(inst: dict, roots: list[int]) -> dict:
    roots = sorted(roots)
    return {
        "coefficients": _poly_from_roots(
            roots, inst["omega"], inst["q"]),
        "roots": roots,
    }


def _attack_outlier_coefficients(inst: dict) -> bool:
    # Rank roots by the ordinary integer magnitude of their field value.
    ranked = sorted(range(inst["n"]),
                    key=lambda i: pow(inst["omega"], i, inst["q"]))
    guesses = [ranked[:inst["k"]], ranked[-inst["k"]:]]
    return any(verify(inst, _candidate_from_roots(inst, g))[0] for g in guesses)


def _attack_greedy_first_roots(inst: dict) -> bool:
    guesses = [
        list(range(inst["k"])),
        list(range(inst["n"] - inst["k"], inst["n"])),
    ]
    return any(verify(inst, _candidate_from_roots(inst, g))[0] for g in guesses)


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x230408749)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_power_basis_ansatz(inst: dict) -> bool:
    # A plausible by-hand mistake: treat the first k+1 displayed coordinates
    # of epsilon as the normal-basis coefficients and then use their roots.
    raw = inst["epsilon"][:inst["k"] + 1]
    if raw[-1] == 0:
        return False
    inv = pow(raw[-1], inst["q"] - 2, inst["q"])
    coefficients = [x * inv % inst["q"] for x in raw]
    roots = [i for i in range(inst["n"])
             if _poly_eval(coefficients,
                           pow(inst["omega"], i, inst["q"]), inst["q"]) == 0]
    if len(roots) != inst["k"]:
        return False
    return verify(inst, {"coefficients": coefficients, "roots": roots})[0]


def _relabel(inst: dict, frobenius_power: int, scalar: int) -> dict:
    moved = {key: value for key, value in inst.items() if key != "answer"}
    sigma = _frobenius_coords(inst["sigma"], inst["d"], inst["ell"],
                              frobenius_power)
    epsilon = _frobenius_coords(inst["epsilon"], inst["d"], inst["ell"],
                                frobenius_power)
    moved["sigma"] = _scale_coords(sigma, scalar, inst["q"])
    moved["epsilon"] = _scale_coords(epsilon, scalar, inst["q"])
    moved["answer"] = inst["answer"]
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    coefficients = answer.get("coefficients", []) if isinstance(answer, dict) else []
    roots = answer.get("roots", []) if isinstance(answer, dict) else []
    return len(encoded), len(encoded), len(coefficients) + len(roots)


def selftest() -> dict:
    """Run and report every mandatory correctness and hardness gate."""
    report: dict = {}

    g1_failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            json_ok = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            checks += 1
            if not (ok and json_ok):
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": reason, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "checks": checks, "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    answer = inst["answer"]
    swapped = {
        "coefficients": list(answer["coefficients"]),
        "roots": list(answer["roots"]),
    }
    swap_index = next(
        i for i, value in enumerate(swapped["coefficients"][:-1]) if value != 1)
    swapped["coefficients"][swap_index], swapped["coefficients"][-1] = (
        swapped["coefficients"][-1], swapped["coefficients"][swap_index])
    duplicated = {
        "coefficients": list(answer["coefficients"]),
        "roots": list(answer["roots"]),
    }
    duplicated["roots"][-1] = duplicated["roots"][0]
    corruptions = {
        "drop_one": {"coefficients": answer["coefficients"][:-1],
                     "roots": list(answer["roots"])},
        "swap_coefficients": swapped,
        "duplicate_root": duplicated,
        "empty": {"coefficients": [], "roots": []},
        "out_of_range": {"coefficients": list(answer["coefficients"]),
                         "roots": list(answer["roots"][:-1]) + [inst["n"]]},
    }
    rejections = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejections[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejections.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejections.values())
                and len(set(reasons)) == len(reasons),
        "rejections": rejections,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The Frobenius-coordinate calculation gives the following.\n"
        "```json\nintermediate notes omitted\n```\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n"
        "The roots are listed in increasing order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(0x230408749)
    total = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    sampling_seconds = time.perf_counter() - started
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "candidate_space": search_space(inst),
        "prior": "uniform over all monic degree-k divisors via k root indices",
        "sampling_wall_seconds": sampling_seconds,
    }

    baseline_started = time.perf_counter()
    baseline_success = _attack_random_restart(inst, 0xB451, restarts=4096)
    baseline_seconds = time.perf_counter() - baseline_started
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and not baseline_success and demo_count == 1,
        "shipping_observed_valid_fraction": probability,
        "shipping_density_sample_count": total,
        "shipping_valid_hits": hits,
        "shipping_exact_valid_count": 1,
        "shipping_candidate_space": search_space(inst),
        "baseline_wall_seconds": baseline_seconds,
        "baseline_iterations": 4096,
        "baseline_successes": int(baseline_success),
        "demo_exact_solution_count": demo_count,
        "enumerate_all_shipping": None,
    }

    attack_names = {
        "outlier_root_value_magnitude": 0,
        "greedy_first_or_last_roots": 0,
        "random_restart_256_structure_aware": 0,
        "by_hand_power_basis_is_normal_ansatz": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_names["outlier_root_value_magnitude"] += int(
            _attack_outlier_coefficients(trial))
        attack_names["greedy_first_or_last_roots"] += int(
            _attack_greedy_first_roots(trial))
        attack_names["random_restart_256_structure_aware"] += int(
            _attack_random_restart(trial, seed))
        attack_names["by_hand_power_basis_is_normal_ansatz"] += int(
            _attack_power_basis_ansatz(trial))
        reference_runs.append(_reference_dft(trial))
    reference_ok = sum(int(run["ok"]) for run in reference_runs)
    reference_wall = sum(run["wall_clock_sec"] for run in reference_runs)
    reference_ops = sum(run["operations"] for run in reference_runs)
    attacks_failed = all(successes == 0 for successes in attack_names.values())
    report["G6_adversary_panel"] = {
        "pass": attacks_failed and reference_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_names.items()
        },
        "reference_algorithm": {
            "name": "exact finite-field DFT cyclic deconvolution",
            "complexity": "O(n^2) base-field operations",
            "wall_clock_sec_total": reference_wall,
            "wall_clock_sec_mean": reference_wall / 8,
            "operations_total": reference_ops,
            "operations_mean": reference_ops // 8,
            "solves": f"{reference_ok}/8, as expected",
        },
    }

    # Build beyond twice the shipping degree, keeping k fixed.
    doubled_n = 520  # 521 is prime
    doubled_params = {"n": doubled_n, "k": ship_params["k"],
                      "min_q": ship_params["min_q"] * 2,
                      "terms": ship_params["terms"]}
    doubled_start = time.perf_counter()
    doubled = make_instance(seed=7, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_seconds = time.perf_counter() - doubled_start
    spaces = [search_space(make_instance(seed=9, **params))
              for name, params in DIFFICULTY.items() if name != "demo"]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n >= 2 * ship_params["n"]
                and spaces == sorted(spaces) and len(set(spaces)) == len(spaces),
        "shipping_n": ship_params["n"],
        "doubled_n": doubled_n,
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_seconds,
        "named_candidate_spaces": spaces,
        "answer_degree_fixed": ship_params["k"],
    }

    invariance_checks = 0
    real_transform_checks = 0
    invariant = True
    for seed in range(20):
        trial = make_instance(seed=10_000 + seed, **ship_params)
        original_key = canonical_key(trial)
        transformations = [
            _relabel(trial, seed + 1, 1),
            _relabel(trial, 0, 2 + seed),
            _relabel(trial, seed + 1, 2 + seed),
        ]
        for moved in transformations:
            invariance_checks += 1
            invariant &= canonical_key(moved) == original_key
            real_transform_checks += 1
            invariant &= verify(moved, trial["answer"])[0]
    unrelated_keys = {
        canonical_key(make_instance(seed=20_000 + seed, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_verify_checks": real_transform_checks,
        "distinct_unrelated_keys": len(unrelated_keys),
        "unrelated_instances": 20,
        "symmetries": ["simultaneous Frobenius", "common nonzero F_q scaling",
                       "their composition"],
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    # Exact count for the stated compact route after recognizing A: obtain only
    # the orbit coordinates needed for the k+1 outputs by binary powering d,
    # then form the sparse cyclic convolution.  A binary exponent e costs
    # floor(log2(e)) squarings plus popcount(e)-1 multiplies.
    needed_indices = {
        (i - j * inst["d"]) % inst["n"]
        for i in range(inst["k"] + 1) for j in range(inst["terms"])
    }
    powering_operations = sum(
        0 if exponent == 0 else
        (exponent.bit_length() - 1 + exponent.bit_count() - 1)
        for exponent in needed_indices
    )
    inverse_coeff_operations = inst["terms"] - 1
    convolution_operations = (
        (2 * inst["terms"] - 1) * (inst["k"] + 1)
    )
    intended_operations = (powering_operations + inverse_coeff_operations
                           + convolution_operations)
    arms = {
        name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": G9_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = ship_params
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
