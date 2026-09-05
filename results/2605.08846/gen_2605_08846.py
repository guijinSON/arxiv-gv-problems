"""Verified rational-base descent-correction generator for arXiv:2605.08846.

The module uses the native integer objects in Blake's Theorem 1.  It samples
structured prime factors first, forms semiprimes, and records the bounded
integer correction produced by the theorem's proof.  No emitted instance is
factored to discover its answer.
"""

from __future__ import annotations

import copy
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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:                 # pragma: no cover - standard-library fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "structured semiprimes",
        "coprime rational base",
        "integer rational-base descent orbit",
        "bounded gcd correction vector",
    ],
    "verification_operations": [
        "exact integer multiplication and floor division",
        "exact Euclidean gcd",
        "integer range comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Unrolling the floor descent leaves a geometrically bounded sum of "
        "discarded fractions, forcing the target-depth correction to one of "
        "two integers; without that invariant one repeats a gcd window at "
        "every descent depth."
    ),
    "hardness_basis": (
        "Track B: Blake's Section 2 Rational Base Descent algorithm runs in "
        "O((a/(a-b)) log^3 N) bit operations by Section 5 and is expected to "
        "solve every row; at shipping n=18 it used 3,888 gcd calls, about "
        "75,600 counted exact operations, and 0.005 seconds, while collapsing "
        "the integer-base descent at the supplied depth uses 240 high-level "
        "exact operations and must be executed without a big-integer tool."
    ),
    "max_answer_tokens": 16,
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
        "A JSON list with exactly one correction per displayed row, in row "
        "order; every correction is -1 or 0, with exactly floor(rows/2) "
        "entries equal to -1."
    ),
    "bounds": {
        "entries": "instance rows (24 at every non-demo preset)",
        "alphabet": [-1, 0],
        "max_entries": 24,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "rows": 3},
    "easy": {"n": 18, "rows": 24},
    "medium": {"n": 24, "rows": 24},
    "hard": {"n": 32, "rows": 24},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "Unroll the floor recurrence as a rational power minus the bounded "
    "geometric sum of all discarded fractions."
)
PLACEBO_HINT: str = (
    "Keep every floor operation exact and preserve the displayed row order "
    "when preparing the correction list."
)

# Replaced with script-owned measurements after the three oracle arms run.
G9_EVIDENCE: dict = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES: str = r"""
Definition and exact regime.  Section 2 defines Q <- floor(bQ/a), followed at
every depth by gcd tests in the integer window [-J,J], where
J=ceil(2+a/(a-b)).  Theorem 1 proves success for N=pq when
p=floor(c(a/b)^s)+Delta, (a/b)^s>q, and
|Delta|<(a/b)^s/q.  The generator uses a/b=6/1 and takes
p=k*6^s+1 or p=k*6^s-1 with c=k, hence Delta is respectively +1 or -1 and
the central power is exactly integral.  Since q<6^s, direct floor division
gives Q_s=kq in the plus case and Q_s=kq-1 in the minus case.  Thus the
correction is exactly 0 or -1.  That is the finite certificate requested from
the solver.

Step 0.  Section 5 explicitly makes certificate recovery polynomial time,
O((a/(a-b))*log^3 N), once (a,b) is known.  Track A would therefore be false.
This is Track B: the reference implementation performs the paper's gcd window
at all depths and reports its exact Euclidean-remainder count.  A solver who
uses the supplied target depth and notices that base 6 makes the nested floors
one division by 6^s needs one binary power, one division, and two candidate
gcds per row, but still has to carry out exact big-integer arithmetic unaided.

Construction and primality.  Factors are sampled before multiplication.
For a plus row p=2^u*3^v+1 is accepted only with an executable Pocklington
certificate using the complete factorisation of p-1.  For a minus row
p=2^u*3^v-1 is accepted only with an executable Lucas N+1 certificate using
the complete factorisation of p+1.  The smaller q is independently generated
as a Proth prime and proved by Pocklington.  Thus every row really is a
semiprime; probable primes are never silently used.

Attack handling.  Rows are exchangeable and their presentation is shuffled.
The panel tries magnitude-ranked corrections, all-zero greedy corrections,
structure-aware random restarts, and a last-digit rounding ansatz.  The full
Rational Base Descent algorithm is reported separately because Track B expects
it to succeed.  The canonical key sorts the semiprime rows and quotients exactly
the row-reordering symmetry; it never hashes a seed or rendered statement.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000


def _small_primes(limit: int) -> tuple[int, ...]:
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[:2] = b"\x00\x00"
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p: limit + 1: p] = b"\x00" * (
                (limit - p * p) // p + 1)
    return tuple(i for i, flag in enumerate(sieve) if flag)


_SIEVE_PRIMES = _small_primes(997)


def _is_prime64(value: int) -> bool:
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if value < 2 or value >= 1 << 64:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
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


def _strong_probable_prime(value: int, bases: tuple[int, ...]) -> bool:
    if value < 2:
        return False
    for prime in _SIEVE_PRIMES:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in bases:
        if base >= value:
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


def _pocklington_certificate(value: int, known_part: int,
                             prime_divisors: tuple[int, ...]) -> dict | None:
    """Return an exact Pocklington certificate, or None.

    ``known_part`` is fully factored through ``prime_divisors`` and divides
    value-1.  The executable checks here are the proof; Miller--Rabin is only a
    filter before this function is called.
    """
    if (value - 1) % known_part or known_part <= math.isqrt(value):
        return None
    witnesses: dict[int, int] = {}
    for divisor in prime_divisors:
        found = None
        for base in range(2, 80):
            if pow(base, value - 1, value) != 1:
                continue
            if math.gcd(pow(base, (value - 1) // divisor, value) - 1,
                        value) == 1:
                found = base
                break
        if found is None:
            return None
        witnesses[divisor] = found
    return {"known_part": known_part, "witnesses": witnesses}


def _structured_prime(a: int, steps: int, k_bits: int,
                      rng: random.Random, forbidden: set[int],
                      prime_divisors: tuple[int, ...] = (2, 3)) -> tuple[int, int]:
    known_part = pow(a, steps)
    low = 1 << (k_bits - 1)
    mask = (1 << k_bits) - 1
    for _ in range(200_000):
        k = (rng.getrandbits(k_bits) | low) & mask
        value = k * known_part + 1
        if value in forbidden:
            continue
        if not _strong_probable_prime(value, (2, 3, 5, 7, 11)):
            continue
        cert = _pocklington_certificate(value, known_part, prime_divisors)
        if cert is not None:
            # Recheck the compact certificate before returning it.
            assert cert["known_part"] > math.isqrt(value)
            assert all(
                pow(base, value - 1, value) == 1
                and math.gcd(pow(base, (value - 1) // divisor, value) - 1,
                             value) == 1
                for divisor, base in cert["witnesses"].items()
            )
            return value, k
    raise RuntimeError("structured Pocklington-prime search exhausted")


def _jacobi(a: int, n: int) -> int:
    """Jacobi symbol (a/n) for positive odd n."""
    if n <= 0 or n % 2 == 0:
        raise ValueError("Jacobi denominator must be positive and odd")
    a %= n
    result = 1
    while a:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def _matrix_mul_2x2(left: tuple[int, int, int, int],
                    right: tuple[int, int, int, int], modulus: int
                    ) -> tuple[int, int, int, int]:
    a, b, c, d = left
    e, f, g, h = right
    return ((a * e + b * g) % modulus,
            (a * f + b * h) % modulus,
            (c * e + d * g) % modulus,
            (c * f + d * h) % modulus)


def _lucas_u(index: int, p_parameter: int, q_parameter: int,
             modulus: int) -> int:
    """U_index(P,Q) modulo modulus via the companion matrix."""
    result = (1, 0, 0, 1)
    power = (p_parameter % modulus, -q_parameter % modulus, 1, 0)
    exponent = index
    while exponent:
        if exponent & 1:
            result = _matrix_mul_2x2(result, power, modulus)
        power = _matrix_mul_2x2(power, power, modulus)
        exponent >>= 1
    return result[2]


def _lucas_n_plus_one_certificate(value: int,
                                  prime_divisors: tuple[int, ...]
                                  ) -> dict | None:
    """Executable Lucas certificate using the complete factorisation of n+1."""
    for q_parameter in range(1, 80):
        if math.gcd(q_parameter, value) != 1:
            continue
        for p_parameter in range(1, 120):
            discriminant = p_parameter * p_parameter - 4 * q_parameter
            if _jacobi(discriminant, value) != -1:
                continue
            if _lucas_u(value + 1, p_parameter, q_parameter, value) != 0:
                continue
            if all(math.gcd(
                    _lucas_u((value + 1) // divisor, p_parameter,
                             q_parameter, value), value
                    ) == 1 for divisor in prime_divisors):
                return {"P": p_parameter, "Q": q_parameter,
                        "prime_divisors": prime_divisors}
    return None


def _smooth_signed_prime(sign: int, steps: int, rng: random.Random,
                         forbidden: set[int]) -> tuple[int, int]:
    """Prove p=2^u*3^v+sign, with u,v>=steps, and return (p,k)."""
    if sign not in (-1, 1):
        raise ValueError("sign must be -1 or +1")
    span = max(12, 4 * steps)
    for _ in range(200_000):
        u = steps + rng.randrange(span)
        v = steps + rng.randrange(span)
        central = (1 << u) * pow(3, v)
        value = central + sign
        if value in forbidden:
            continue
        if not _strong_probable_prime(value, (2, 3, 5, 7, 11)):
            continue
        if sign == 1:
            cert = _pocklington_certificate(value, central, (2, 3))
        else:
            cert = _lucas_n_plus_one_certificate(value, (2, 3))
        if cert is not None:
            base_power = pow(6, steps)
            assert central % base_power == 0
            return value, central // base_power
    raise RuntimeError("smooth signed-prime search exhausted")


@functools.lru_cache(maxsize=64)
def _signed_prime_pool(sign: int, steps: int) -> tuple[tuple[int, int], ...]:
    """Reusable proved-prime pool; seed-dependent q values still vary instances."""
    count = 8 if steps <= 4 else 36
    rng = random.Random((steps << 12) ^ (0x51A7 if sign > 0 else 0xA17E))
    used: set[int] = set()
    pool = []
    while len(pool) < count:
        item = _smooth_signed_prime(sign, steps, rng, used)
        used.add(item[0])
        pool.append(item)
    return tuple(pool)


def _random_prime64(bits: int, rng: random.Random,
                    forbidden: set[int]) -> int:
    if not 3 <= bits <= 62:
        raise ValueError("q_bits must lie from 3 through 62")
    high = 1 << (bits - 1)
    for _ in range(100_000):
        value = rng.getrandbits(bits) | high | 1
        if value not in forbidden and _is_prime64(value):
            return value
    raise RuntimeError("64-bit prime search exhausted")


def _random_prime_interval(lower: int, upper: int, rng: random.Random,
                           forbidden: set[int]) -> int:
    """Choose a proved prime uniformly by rejection from an odd interval."""
    lower = max(3, lower)
    if upper <= lower or upper >= 1 << 64:
        raise ValueError("prime interval must be nonempty and below 2^64")
    for _ in range(100_000):
        value = rng.randrange(lower, upper) | 1
        if value < upper and value not in forbidden and _is_prime64(value):
            return value
    raise RuntimeError("interval prime search exhausted")


def _validate_parameters(n: int, rows: int) -> None:
    values = (n, rows)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("n and rows must be integers")
    if n < 3:
        raise ValueError("n must be at least 3")
    if not 1 <= rows <= 24:
        raise ValueError("rows must lie from 1 through 24")


def _descent(value: int, a: int, b: int, steps: int) -> int:
    q_value = value
    for _ in range(steps):
        q_value = (b * q_value) // a
    return q_value


@functools.lru_cache(maxsize=192)
def _make_cached(n: int, seed: int, rows: int) -> dict:
    _validate_parameters(n, rows)
    rng = random.Random(seed)
    a, b, steps = 6, 1, n
    base_power = pow(a, steps)

    # Exactly half of the rows use each sign.  This is a transformation of two
    # theorem-backed constructions, not a post-hoc answer balancing step.
    signs = [-1] * (rows // 2) + [1] * (rows - rows // 2)
    rng.shuffle(signs)
    needed_minus = signs.count(-1)
    needed_plus = signs.count(1)
    minus_pool = rng.sample(list(_signed_prime_pool(-1, steps)), needed_minus)
    plus_pool = rng.sample(list(_signed_prime_pool(1, steps)), needed_plus)
    selected = {-1: iter(minus_pool), 1: iter(plus_pool)}
    built_rows = []
    used_primes: set[int] = set()
    for sign in signs:
        p, k = next(selected[sign])
        used_primes.add(p)
        # q is a separately generated Proth prime.  Its bit length is kept at
        # least four below 6^steps, so Theorem 1's strict size bound is exact.
        target_bits = max(5, base_power.bit_length() - 4)
        if base_power < 1 << 16:
            q = _random_prime_interval(3, base_power, rng, used_primes)
        else:
            q_exponent = max(3, (target_bits + 1) // 2)
            q_k_bits = max(2, target_bits - q_exponent)
            q, _ = _structured_prime(2, q_exponent, q_k_bits, rng,
                                     used_primes, prime_divisors=(2,))
        used_primes.add(q)
        if not base_power > q:
            raise AssertionError("Theorem 1 size inequality failed")
        composite = p * q
        endpoint = _descent(composite, a, b, steps)
        c = k
        correction = endpoint - c * q
        expected = -1 if sign == -1 else 0
        if correction != expected:
            raise AssertionError("signed descent correction identity failed")
        if math.gcd(endpoint - correction, composite) not in (p, q):
            raise AssertionError("constructed correction does not expose a factor")
        built_rows.append({"N": composite, "correction": correction})

    rng.shuffle(built_rows)
    answer = [row["correction"] for row in built_rows]
    public_rows = [{"N": row["N"]} for row in built_rows]
    return {
        "family": "rational_base_descent_corrections_v1",
        "n": n,
        "a": a,
        "b": b,
        "steps": steps,
        "rows": public_rows,
        "correction_alphabet": [-1, 0],
        "answer": answer,
    }


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate structured semiprimes and theorem corrections."""
    rows = params.pop("rows", 24)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    return copy.deepcopy(_make_cached(n, seed, rows))


def render(inst: dict) -> str:
    """Return the complete standalone problem statement."""
    row_lines = "\n".join(
        f"{index}: {row['N']}" for index, row in enumerate(inst["rows"])
    )
    statement = f"""RATIONAL-BASE DESCENT CORRECTIONS

For integers a>b>=1 and an integer X, one descent update replaces X by
floor(b*X/a), where floor is ordinary downward rounding.  Starting from an
integer N, let Q_0=N and

    Q_t = floor(b*Q_(t-1)/a)  for t=1,...,s.

For this instance a={inst['a']}, b={inst['b']}, and s={inst['steps']}.
The pair (a,b) is coprime.  Each numbered N below is the product of two
distinct primes and was constructed in the following promised regime: for an
unrevealed positive integer k, its larger prime factor is either k*a^s-1 or
k*a^s+1, while its smaller prime factor q satisfies (a/b)^s>q.  These promises
imply that exactly one j in the two-element set {{-1,0}} makes gcd(Q_s-j,N) a
nontrivial factor (strictly between 1 and N).

For every row, find that correction j.  Return exactly {len(inst['rows'])}
integers in the displayed 0-based row order.  Repetitions are allowed; no row
may be omitted; -1 and 0 are the only permitted values.  Exactly
{len(inst['rows']) // 2} entries are -1 and the rest are 0.

Rows, written as "row_index: N":
{row_lines}

Give your final answer inside <answer></answer> tags as one JSON array of
exactly {len(inst['rows'])} integers, with no prose inside the tags.
Example of the required syntax for three rows: <answer>[-1,0,0]</answer>
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\nHint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        statement += "\nHint: " + PLACEBO_HINT + "\n"
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON correction list, tolerating surrounding prose."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return None
    return answer


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid correction vector without reading ``inst['answer']``."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list must not be empty"
    expected = len(inst["rows"])
    if len(answer) == expected - 1:
        return False, "correction list is one entry short"
    if len(answer) < expected:
        return False, f"expected {expected} corrections, received too few"
    if len(answer) == expected + 1:
        return False, "correction list is one entry too long"
    if len(answer) > expected:
        return False, f"expected {expected} corrections, received too many"
    for index, correction in enumerate(answer):
        if isinstance(correction, bool) or not isinstance(correction, int):
            return False, f"correction at row {index} is not an integer"
        if correction not in (-1, 0):
            return False, f"correction at row {index} is outside {{-1,0}}"
    if answer.count(-1) != expected // 2:
        return False, f"answer must contain exactly {expected // 2} entries equal to -1"
    for index, correction in enumerate(answer):
        composite = inst["rows"][index]["N"]
        endpoint = _descent(composite, inst["a"], inst["b"], inst["steps"])
        factor = math.gcd(endpoint - correction, composite)
        if not 1 < factor < composite:
            return False, f"row {index} correction does not expose a factor"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated balanced correction language."""
    answer = [0] * len(inst["rows"])
    for index in rng.sample(range(len(answer)), len(answer) // 2):
        answer[index] = -1
    return answer


def search_space(inst: dict) -> int:
    rows = len(inst["rows"])
    return math.comb(rows, rows // 2)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    rows = len(inst["rows"])
    for minus_indices in itertools.combinations(range(rows), rows // 2):
        candidate = [0] * rows
        for index in minus_indices:
            candidate[index] = -1
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize the genuine row-permutation symmetry."""
    payload = {
        "a": inst["a"],
        "b": inst["b"],
        "steps": inst["steps"],
        "rows": sorted(row["N"] for row in inst["rows"]),
        "alphabet": [-1, 0],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase operand width while keeping the 24-entry witness fixed."""
    harder = dict(params)
    current = int(harder.get("n", 40))
    if current >= 256:
        return "cap_bound"
    harder["n"] = min(256, max(current + 16, (3 * current) // 2))
    harder["rows"] = int(harder.get("rows", 24))
    return harder


class _OperationCounter:
    def __init__(self) -> None:
        self.descent_multiply_divides = 0
        self.gcd_calls = 0
        self.euclidean_remainders = 0
        self.offset_subtractions = 0

    @property
    def operations(self) -> int:
        return (2 * self.descent_multiply_divides + self.offset_subtractions
                + self.euclidean_remainders)


def _counted_gcd(x: int, y: int, counter: _OperationCounter) -> int:
    counter.gcd_calls += 1
    x, y = abs(x), abs(y)
    while y:
        x, y = y, x % y
        counter.euclidean_remainders += 1
    return x


def _reference_algorithm(inst: dict) -> dict:
    """Run the paper's full gcd window at every supplied descent depth."""
    counter = _OperationCounter()
    start = time.perf_counter()
    corrections = []
    radius = math.ceil(2 + inst["a"] / (inst["a"] - inst["b"]))
    for row in inst["rows"]:
        composite = row["N"]
        endpoint = composite
        target_valid: list[int] = []
        for depth in range(1, inst["steps"] + 1):
            endpoint = (inst["b"] * endpoint) // inst["a"]
            counter.descent_multiply_divides += 1
            for offset in range(-radius, radius + 1):
                counter.offset_subtractions += 1
                factor = _counted_gcd(endpoint - offset, composite, counter)
                if depth == inst["steps"] and offset in (-1, 0) \
                        and 1 < factor < composite:
                    target_valid.append(offset)
        if len(target_valid) != 1:
            return {
                "ok": False,
                "reason": f"reference found {len(target_valid)} target corrections",
                "answer": corrections,
                "wall_clock_sec": time.perf_counter() - start,
                "counter": counter,
            }
        corrections.append(target_valid[0])
    ok, reason = verify(inst, corrections)
    return {
        "ok": ok,
        "reason": reason,
        "answer": corrections,
        "wall_clock_sec": time.perf_counter() - start,
        "counter": counter,
    }


def _attack_outlier_magnitude(inst: dict) -> bool:
    ranked = sorted(range(len(inst["rows"])),
                    key=lambda i: inst["rows"][i]["N"])
    answer = [0] * len(ranked)
    for index in ranked[:len(ranked) // 2]:
        answer[index] = -1
    return verify(inst, answer)[0]


def _attack_greedy_all_zero(inst: dict) -> bool:
    answer = [0] * len(inst["rows"])
    for index in range(len(answer) // 2):
        answer[index] = -1
    return verify(inst, answer)[0]


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x260508846)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_last_digit_rounding(inst: dict) -> bool:
    # A genuinely in-context pencil-and-paper guess: rank the final decimal
    # digits as a surrogate for the accumulated floor error.
    answer = [0] * len(inst["rows"])
    ranked = sorted(range(len(answer)),
                    key=lambda i: (inst["rows"][i]["N"] % 10, i), reverse=True)
    for index in ranked[:len(answer) // 2]:
        answer[index] = -1
    return verify(inst, answer)[0]


def _permute_rows(inst: dict, permutation: list[int]) -> dict:
    moved = {key: copy.deepcopy(value) for key, value in inst.items()
             if key != "answer"}
    moved["rows"] = [copy.deepcopy(inst["rows"][i]) for i in permutation]
    moved["answer"] = [inst["answer"][i] for i in permutation]
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    atoms = len(answer) if isinstance(answer, list) else 1
    return len(encoded), (len(encoded) + 3) // 4, atoms


def selftest() -> dict:
    """Run every mandatory correctness, resistance, and reporting gate."""
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            native = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            checks += 1
            if not (ok and native):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason, "json_native": native})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    answer = inst["answer"]
    differing = next(i for i in range(1, len(answer)) if answer[i] != answer[0])
    swapped = list(answer)
    swapped[0], swapped[differing] = swapped[differing], swapped[0]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_one": swapped,
        "duplicate_one": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [1] + answer[1:],
    }
    rejections = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejections[name] = {"rejected": not ok, "reason": reason}
    reasons = [value["reason"] for value in rejections.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in rejections.values())
                and len(set(reasons)) == len(reasons),
        "rejections": rejections,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the bounded truncation error.\n```text\nwork omitted\n```\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n"
        "The entries follow the displayed row order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(0x260508846)
    total = 2_000_000
    hits = 0
    sampling_start = time.perf_counter()
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    sampling_seconds = time.perf_counter() - sampling_start
    probability = hits / total
    exact_density = 1 / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "exact_density_from_unique_row_witnesses": exact_density,
        "candidate_space": search_space(inst),
        "prior": "uniform over balanced vectors with exactly 12 entries equal to -1",
        "sampling_wall_seconds": sampling_seconds,
    }

    baseline = _reference_algorithm(inst)
    baseline_counter = baseline["counter"]
    per_row_solution_counts = []
    for row in inst["rows"]:
        composite = row["N"]
        endpoint = _descent(composite, inst["a"], inst["b"], inst["steps"])
        per_row_solution_counts.append(sum(
            int(1 < math.gcd(endpoint - j, composite) < composite)
            for j in (-1, 0)
        ))
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": (probability < 1e-6 and baseline["ok"]
                 and all(count == 1 for count in per_row_solution_counts)
                 and enumerate_all(demo) == 1),
        "shipping_observed_valid_fraction": probability,
        "shipping_density_sample_count": total,
        "shipping_valid_hits": hits,
        "shipping_exact_valid_count": 1,
        "shipping_candidate_space": search_space(inst),
        "shipping_exact_density": exact_density,
        "baseline_name": "full Rational Base Descent gcd window",
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_operations": baseline_counter.operations,
        "baseline_gcd_calls": baseline_counter.gcd_calls,
        "baseline_euclidean_remainders": baseline_counter.euclidean_remainders,
        "baseline_successes": int(baseline["ok"]),
        "demo_exact_solution_count": enumerate_all(demo),
        "enumerate_all_shipping": None,
    }

    attack_successes = {
        "outlier_semiprime_magnitude_rank": 0,
        "greedy_first_half_minus_one": 0,
        "random_restart_256_binary_vectors": 0,
        "by_hand_last_digit_rounding_ansatz": 0,
    }
    references = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes["outlier_semiprime_magnitude_rank"] += int(
            _attack_outlier_magnitude(trial))
        attack_successes["greedy_first_half_minus_one"] += int(
            _attack_greedy_all_zero(trial))
        attack_successes["random_restart_256_binary_vectors"] += int(
            _attack_random_restart(trial, seed))
        attack_successes["by_hand_last_digit_rounding_ansatz"] += int(
            _attack_last_digit_rounding(trial))
        references.append(_reference_algorithm(trial))
    reference_ok = sum(int(value["ok"]) for value in references)
    reference_seconds = sum(value["wall_clock_sec"] for value in references)
    reference_operations = sum(value["counter"].operations for value in references)
    reference_gcds = sum(value["counter"].gcd_calls for value in references)
    report["G6_adversary_panel"] = {
        "pass": (all(value == 0 for value in attack_successes.values())
                 and reference_ok == 8),
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "Section 2 Rational Base Descent with every gcd window",
            "complexity": "O((a/(a-b)) log^3 N) bit operations",
            "wall_clock_sec_total": reference_seconds,
            "wall_clock_sec_mean": reference_seconds / 8,
            "operations_total": reference_operations,
            "operations_mean": reference_operations // 8,
            "gcd_calls_total": reference_gcds,
            "gcd_calls_mean": reference_gcds // 8,
            "solves": f"{reference_ok}/8, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled_start = time.perf_counter()
    doubled = make_instance(seed=7, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_seconds = time.perf_counter() - doubled_start
    operand_bits = []
    for preset in ("easy", "medium", "hard"):
        trial = make_instance(seed=9, **DIFFICULTY[preset])
        operand_bits.append(max(row["N"].bit_length() for row in trial["rows"]))
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled_params["n"] == 2 * ship_params["n"]
                 and operand_bits == sorted(operand_bits)
                 and len(set(operand_bits)) == len(operand_bits)
                 and len(doubled["answer"]) == len(answer)),
        "shipping_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_seconds,
        "named_max_operand_bits": operand_bits,
        "answer_entries_fixed": len(answer),
    }

    invariant = True
    invariance_checks = 0
    real_checks = 0
    for seed in range(20):
        trial = make_instance(seed=10_000 + seed, **ship_params)
        count = len(trial["rows"])
        reverse = list(reversed(range(count)))
        rotate = list(range(1, count)) + [0]
        composed = [reverse[i] for i in rotate]
        original_key = canonical_key(trial)
        for permutation in (reverse, rotate, composed):
            moved = _permute_rows(trial, permutation)
            invariance_checks += 1
            invariant &= canonical_key(moved) == original_key
            real_checks += 1
            invariant &= verify(moved, moved["answer"])[0]
    unrelated_keys = {
        canonical_key(make_instance(seed=20_000 + seed, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_verify_checks": real_checks,
        "distinct_unrelated_keys": len(unrelated_keys),
        "unrelated_instances": 20,
        "symmetries": ["row reversal", "cyclic row rotation", "composition"],
    }

    chars, tokens, elements = _answer_metrics(answer)
    # Because b=1, all nested floors equal floor(N/a^steps).  Binary powering
    # a^steps costs floor(log2 steps) squarings plus popcount(steps)-1 products;
    # add one division, two subtractions and two gcd calls per row.
    exponent = inst["steps"]
    power_operations = exponent.bit_length() - 1 + exponent.bit_count() - 1
    intended_operations = len(answer) * (power_operations + 5)
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
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
        "within_size_and_operation_caps": within_caps,
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
