"""Verified preimage generator from a trace permutation polynomial.

The native object is the permutation from Corollary 15 / Example 16 of
Ruikai Chen, arXiv:2506.24012.  A preimage is sampled first and the target is
obtained by exact finite-field evaluation.  The generator never solves its own
instance.  Everything is standard-library-only; gvlib currently has no binary
finite-field helper.
"""

from __future__ import annotations

import functools
import json
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
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "the finite field GF(4^n) as GF(2^n)[W]/(W^2+W+1)",
        "a trace permutation polynomial from Corollary 15",
        "a finite-field preimage written in the displayed polynomial basis",
    ],
    "verification_operations": [
        "carryless polynomial reduction over GF(2)",
        "exact squaring and multiplication in GF(4^n)",
        "relative trace evaluation and exact field-element comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The relative trace of the target determines the relative trace of "
        "the preimage, reducing the nonlinear-looking inversion to two "
        "Artin--Schreier half-traces; without this invariant one performs "
        "several full binary linear solves."
    ),
    "hardness_basis": (
        "Track B: four trace-branch Gaussian eliminations solve the instance "
        "in O(n^3) bit operations; across eight n=31 shipping instances they "
        "measured 89,884 bit operations and 0.0265 seconds per instance, "
        "whereas the compact relative-trace/half-trace route used at most 110 "
        "field operations and must be recognized before it can be executed "
        "without tools."
    ),
    "max_answer_tokens": 23,
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
        "One GF(4^n) element as the JSON list [u,v], where u and v are "
        "distinct nonzero decimal encodings below 2^n of elements of GF(2^n)."
    ),
    "bounds": {
        "outer_elements": 2,
        "component_encoding": "decimal integers in [1,2^n-1]",
        "components_distinct": True,
    },
}

DIFFICULTY: dict = {
    "easy": {"n": 31, "decoy_terms": 6},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The relative trace of the target depends only on the relative trace of "
    "its preimage."
)
PLACEBO_HINT = (
    "The field representation rewards careful handling of every displayed "
    "component."
)

# Replaced with script-owned measurements after the three oracle runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_http_403_key_limit",
}

NOTES = r"""
STEP 0.  Section 1 fixes the convention that finite-field polynomials are maps,
so x^(q^n)=x.  Section 2, especially Proposition 3, supplies the quadratic-form
character-sum framework.  Corollary 15 gives the exact permutation criterion
for a*x^(2^l q^k)+x*Tr(x).  Its l=1,k=0 specialization, called out in Example
16, says that f(x)=a*x^2+x*Tr(x) permutes GF(q^n) when n is odd and
a in GF(q)^* is not 1.  This module uses q=4 and represents GF(4^n) natively as
GF(2^n)[W]/(W^2+W+1).

The discriminating certificate question rules out Track A.  Given a target,
one can try each of the four possible trace values and solve the resulting
binary linear equations by Gaussian elimination in O(n^3) bit operations.
The compact Track B route is materially shorter: tracing y=f(x) gives
Tr(y)=(a+1)Tr(x)^2; after that substitution, a normalized preimage satisfies
z^2+z=c and two half-traces in the odd-degree GF(2^n) component recover it.

Generation is inverse.  The module uniformly samples a legal preimage x first,
chooses a in GF(4)\{0,1}, and evaluates the paper's permutation to obtain y.
No search is used to obtain the answer.  Displayed decoy terms have the form
c*(Z^(4^n+r)+Z^(r+1)); they vanish identically by the paper's x^(q^n)=x
convention and increase presentation crowding without changing the witness.

The adversary panel attacks construction leakage with low-Hamming-weight
components, lexicographically small components, uniform restarts, and the
obvious but wrong approximation that drops the trace term.  The domain-standard
binary Gaussian solver is reported separately, as Track B requires.
""".strip()


# ---------------------------------------------------------------------------
# Exact binary-polynomial arithmetic and GF(4^n)


def _validate_params(n: int, decoy_terms: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 3 or n % 2 == 0:
        raise ValueError("n must be an odd integer at least 3")
    if (isinstance(decoy_terms, bool) or not isinstance(decoy_terms, int)
            or decoy_terms < 0 or decoy_terms > 64):
        raise ValueError("decoy_terms must be an integer from 0 through 64")


def _poly_remainder(value: int, modulus: int) -> int:
    md = modulus.bit_length() - 1
    while value and value.bit_length() - 1 >= md:
        value ^= modulus << ((value.bit_length() - 1) - md)
    return value


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_remainder(a, b)
    return a


def _k_mul(a: int, b: int, modulus: int, n: int) -> int:
    """Carryless product in K=GF(2)[X]/(modulus)."""
    # The loop consumes bits of b, so put the shorter operand there.  This is a
    # large win for multiplication by one of the four GF(4) scalars.
    if a.bit_length() < b.bit_length():
        a, b = b, a
    result = 0
    top = 1 << n
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & top:
            a ^= modulus
    return result & (top - 1)


def _k_square(a: int, modulus: int, n: int) -> int:
    return _k_mul(a, a, modulus, n)


def _prime_divisors(n: int) -> list[int]:
    out = []
    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            out.append(divisor)
            while n % divisor == 0:
                n //= divisor
        divisor += 1
    if n > 1:
        out.append(n)
    return out


def _is_irreducible(modulus: int, n: int) -> bool:
    """Rabin's exact test for a monic binary polynomial."""
    if modulus >> n != 1 or modulus & 1 == 0:
        return False
    x = 0b10
    value = x
    for _ in range(n):
        value = _k_square(value, modulus, n)
    if value != x:
        return False
    for prime in _prime_divisors(n):
        value = x
        for _ in range(n // prime):
            value = _k_square(value, modulus, n)
        if _poly_gcd(value ^ x, modulus) != 1:
            return False
    return True


@functools.lru_cache(maxsize=None)
def _first_irreducible(n: int) -> int:
    """The first monic odd irreducible in integer (bit-polynomial) order."""
    _validate_params(n, 0)
    high = 1 << n
    for low in range(1, high, 2):
        candidate = high | low
        if _is_irreducible(candidate, n):
            return candidate
    raise RuntimeError("no irreducible polynomial found")


def _k_trace(a: int, modulus: int, n: int) -> int:
    total = 0
    value = a
    for _ in range(n):
        total ^= value
        value = _k_square(value, modulus, n)
    if total not in (0, 1):
        raise AssertionError("GF(2^n)/GF(2) trace escaped GF(2)")
    return total


@functools.lru_cache(maxsize=None)
def _trace_mask(n: int, modulus: int) -> int:
    mask = 0
    for bit in range(n):
        if _k_trace(1 << bit, modulus, n):
            mask |= 1 << bit
    return mask


def _k_trace_fast(a: int, mask: int) -> int:
    return (a & mask).bit_count() & 1


def _k_half_trace(a: int, modulus: int, n: int,
                  counter: dict | None = None) -> int:
    """H(a)=sum a^(2^(2j)); H(a)^2+H(a)=a+Tr(a) for odd n."""
    result = a
    value = a
    for _ in range((n - 1) // 2):
        value = _k_square(value, modulus, n)
        value = _k_square(value, modulus, n)
        result ^= value
        if counter is not None:
            counter["field_operations"] += 3
    return result


def _e_add(x: tuple[int, int], y: tuple[int, int]) -> tuple[int, int]:
    return x[0] ^ y[0], x[1] ^ y[1]


def _e_mul(x: tuple[int, int], y: tuple[int, int], modulus: int,
           n: int) -> tuple[int, int]:
    """Multiply u+vW using W^2=W+1."""
    u, v = x
    r, s = y
    ur = _k_mul(u, r, modulus, n)
    vs = _k_mul(v, s, modulus, n)
    return (ur ^ vs,
            _k_mul(u, s, modulus, n) ^ _k_mul(v, r, modulus, n) ^ vs)


def _e_square(x: tuple[int, int], modulus: int, n: int) -> tuple[int, int]:
    u2 = _k_square(x[0], modulus, n)
    v2 = _k_square(x[1], modulus, n)
    return u2 ^ v2, v2


def _e_pow(x: tuple[int, int], exponent: int, modulus: int,
           n: int) -> tuple[int, int]:
    result = (1, 0)
    value = x
    while exponent:
        if exponent & 1:
            result = _e_mul(result, value, modulus, n)
        exponent >>= 1
        if exponent:
            value = _e_square(value, modulus, n)
    return result


def _e_frobenius(x: tuple[int, int], power: int, modulus: int,
                 n: int) -> tuple[int, int]:
    value = x
    for _ in range(power % (2 * n)):
        value = _e_square(value, modulus, n)
    return value


def _e_trace(x: tuple[int, int], mask: int) -> tuple[int, int]:
    """Relative trace GF(4^n)->GF(4) in the fixed compositum basis."""
    return _k_trace_fast(x[0], mask), _k_trace_fast(x[1], mask)


def _field_element(value: object) -> tuple[int, int] | None:
    if (not isinstance(value, list) or len(value) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in value)):
        return None
    return value[0], value[1]


def _paper_map(inst: dict, x: tuple[int, int]) -> tuple[int, int]:
    """Evaluate the displayed map; every listed decoy is identically zero."""
    modulus, n = inst["modulus"], inst["n"]
    a = tuple(inst["a"])
    trace_x = _e_trace(x, inst["trace_mask"])
    return _e_add(_e_mul(a, _e_square(x, modulus, n), modulus, n),
                  _e_mul(x, trace_x, modulus, n))


# ---------------------------------------------------------------------------
# Public generator interface


def make_instance(n: int, seed: int = 0, decoy_terms: int = 0,
                  **params) -> dict:
    """Inverse-generate a certified Corollary-15 preimage instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, decoy_terms)
    rng = random.Random(seed)
    modulus = _first_irreducible(n)
    mask = _trace_mask(n, modulus)
    bound = 1 << n

    # The witness is sampled before the target exists.  The conditions are part
    # of the advertised bounded language and make all G2 corruptions distinct.
    while True:
        u = rng.randrange(1, bound)
        v = rng.randrange(1, bound)
        if u != v and _e_trace((u, v), mask) != (0, 0):
            break
    a = (0, 1) if rng.getrandbits(1) == 0 else (1, 1)

    core = {
        "n": n,
        "modulus": modulus,
        "trace_mask": mask,
        "a": list(a),
    }
    target = _paper_map(core, (u, v))

    # c*(Z^(4^n+r)+Z^(r+1)) is the zero function on GF(4^n).
    decoys = []
    for _ in range(decoy_terms):
        coefficient = [rng.randrange(bound), rng.randrange(bound)]
        if coefficient == [0, 0]:
            coefficient[0] = 1
        exponent_shift = rng.randrange(1, 2 * n + 2)
        decoys.append([coefficient, exponent_shift])

    inst = {
        **core,
        "decoy_terms": decoys,
        "target": list(target),
        "answer": [u, v],
    }
    ok, why = verify(inst, inst["answer"])
    if not ok:
        raise AssertionError("inverse construction failed: " + why)
    return inst


def render(inst: dict) -> str:
    """Render the complete native finite-field inversion problem."""
    n = inst["n"]
    bound = 1 << n
    field_size = 1 << (2 * n)
    decoys = "\n".join(
        f"    c={coefficient}, r={shift}"
        for coefficient, shift in inst["decoy_terms"]
    ) or "    (none)"
    statement = f"""Invert a trace permutation polynomial over a finite field

Let K=GF(2^{n}) be represented as GF(2)[X]/(P).  A K element is a decimal
integer from 0 through {bound - 1}; bit j is the coefficient of X^j.  The
monic irreducible bit-polynomial is P={inst['modulus']} (bit {n} is its leading
term).  Addition is bitwise XOR.  Multiplication is carryless binary-polynomial
multiplication followed by remainder modulo P.

Let E=K[W]/(W^2+W+1), which is GF(4^{n}).  Write u+vW as [u,v].  Thus

    [u,v]+[r,s] = [u XOR r, v XOR s]
    [u,v]*[r,s] = [u*r+v*s, u*s+v*r+v*s]

where operations on the right are in K.  The subfield GF(4) consists of the
four pairs whose coordinates are 0 or 1.  The relative trace T:E->GF(4) is

    T([u,v]) = [parity(u & M), parity(v & M)],
    M = {inst['trace_mask']},

where '&' is bitwise AND and parity is 0 for an even number of set bits and 1
for an odd number.

The coefficient a={inst['a']} is in GF(4)^* and is not [1,0].  Define the
following polynomial function on E, with Q=4^{n}={field_size}:

    F(Z) = a*Z^2 + Z*T(Z)
           + sum over the rows below of c*(Z^(Q+r) + Z^(r+1)).

The rows [c,r] are:
{decoys}

Because every Z in E satisfies Z^Q=Z, each row contributes the zero function.
Corollary 15 (specialized to l=1,k=0) therefore makes F a permutation because
{n} is odd and a is a nonidentity nonzero element of GF(4).

The target is y={inst['target']}.  Find the unique x=[u,v] with F(x)=y.  The
instance promises that 1 <= u,v <= {bound - 1} and u != v.  Coordinates are
ordered [constant K component, W component]; swapping them changes the field
element.  All displayed bounds are inclusive and decimal.

"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "Hint: " + STRUCTURAL_HINT + "\n\n"
    elif mode == "placebo":
        statement += "Hint: " + PLACEBO_HINT + "\n\n"
    statement += (
        "Give your final answer inside <answer></answer> tags as one JSON list "
        "of two decimal integers.\n"
        "Example: <answer>[5, 7]</answer>\n"
        "Output nothing else inside the tags."
    )
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON pair, tolerating surrounding prose/fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        match = re.fullmatch(r"\[?\s*(\d+)\s*,\s*(\d+)\s*\]?", body)
        if not match:
            return None
        value = [int(match.group(1)), int(match.group(2))]
    if _field_element(value) is None:
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid preimage by one exact evaluation; never read answer."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 2:
        return False, "answer must contain exactly two field components"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "both field components must be decimal integers"
    u, v = answer
    bound = 1 << inst["n"]
    if not (0 <= u < bound and 0 <= v < bound):
        return False, "a component is outside the K encoding range"
    if u == 0 or v == 0:
        return False, "the promised preimage has two nonzero components"
    if u == v:
        return False, "the promised preimage has distinct components"
    if _paper_map(inst, (u, v)) != tuple(inst["target"]):
        return False, "the candidate does not map to the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact nonzero/distinct promised answer language."""
    bound = 1 << inst["n"]
    u = rng.randrange(1, bound)
    v = rng.randrange(1, bound - 1)
    if v >= u:
        v += 1
    return [u, v]


def search_space(inst: dict) -> int | None:
    bound = 1 << inst["n"]
    return (bound - 1) * (bound - 2)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force exact count only at genuinely small declared languages."""
    size = search_space(inst)
    if size is None or size > 200_000:
        return None
    bound = 1 << inst["n"]
    count = 0
    for u in range(1, bound):
        for v in range(1, bound):
            if u != v and verify(inst, [u, v])[0]:
                count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize (a,target) under every GF(2)-Frobenius automorphism."""
    modulus, n = inst["modulus"], inst["n"]
    a = tuple(inst["a"])
    target = tuple(inst["target"])
    orbit = []
    for _ in range(2 * n):
        orbit.append((a[0], a[1], target[0], target[1]))
        a = _e_square(a, modulus, n)
        target = _e_square(target, modulus, n)
    # Decoy rows are polynomial identities, so their order and coefficients do
    # not change the underlying equation whose duplicate status is measured.
    return json.dumps([n, modulus, min(orbit)], separators=(",", ":"))


def escalate(params: dict) -> dict | str | None:
    """Grow both field entropy and zero-identity presentation crowding."""
    n = params.get("n")
    decoy_terms = params.get("decoy_terms", 0)
    if (isinstance(n, bool) or not isinstance(n, int)
            or isinstance(decoy_terms, bool) or not isinstance(decoy_terms, int)):
        return None
    if n >= 91:
        return None
    return {"n": n + 10, "decoy_terms": min(64, decoy_terms + 4)}


# ---------------------------------------------------------------------------
# Compact Track-B route, mechanical reference, and adversaries


def _compact_inverse(inst: dict) -> dict:
    """Trace invariant plus two odd-degree half-traces."""
    n, modulus, mask = inst["n"], inst["modulus"], inst["trace_mask"]
    a = tuple(inst["a"])
    y = tuple(inst["target"])
    counter = {"field_operations": 0}
    start = time.perf_counter()

    # Trace(y)=(a+1)t^2 in GF(4).  Every nonzero GF(4) inverse is its square.
    trace_y = _e_trace(y, mask)
    counter["field_operations"] += 2  # two parity evaluations
    a_plus_one = _e_add(a, (1, 0))
    quotient = _e_mul(trace_y, _e_square(a_plus_one, modulus, n),
                      modulus, n)
    t = _e_square(quotient, modulus, n)
    counter["field_operations"] += 4
    if t == (0, 0):
        return {"answer": None, "ok": False,
                "reason": "unexpected zero trace in promised language",
                "field_operations": counter["field_operations"],
                "wall_clock_sec": time.perf_counter() - start}

    # z=a*x/t obeys z^2+z=c=a*y/t^2.
    t2 = _e_square(t, modulus, n)
    inv_t2 = _e_square(t2, modulus, n)
    c = _e_mul(_e_mul(a, y, modulus, n), inv_t2, modulus, n)
    counter["field_operations"] += 4
    c0, c1 = c

    v = _k_half_trace(c1, modulus, n, counter)
    if _k_trace_fast(c1, mask) != 0:
        raise AssertionError("planted Artin--Schreier equation is insoluble")
    s = c0 ^ _k_square(v, modulus, n)
    counter["field_operations"] += 2
    if _k_trace_fast(s, mask):
        v ^= 1
        s ^= 1
        counter["field_operations"] += 2
    u = _k_half_trace(s, modulus, n, counter)
    z = (u, v)
    if _e_trace(z, mask) != a:
        z = (u ^ 1, v)
        counter["field_operations"] += 3
    # x=(t/a)z and a^-1=a^2 in GF(4).
    scale = _e_mul(t, _e_square(a, modulus, n), modulus, n)
    x = _e_mul(scale, z, modulus, n)
    counter["field_operations"] += 3
    answer = list(x)
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "field_operations": counter["field_operations"],
        "wall_clock_sec": time.perf_counter() - start,
    }


def _solve_binary(rows: list[int], nvars: int) -> tuple[int | None, int]:
    """Gauss-Jordan elimination on augmented bit rows; return one solution."""
    work = rows[:]
    pivot_rows: list[tuple[int, int]] = []
    row = 0
    operations = 0
    width = nvars + 1
    for col in range(nvars):
        pivot = None
        for candidate in range(row, len(work)):
            operations += 1
            if (work[candidate] >> col) & 1:
                pivot = candidate
                break
        if pivot is None:
            continue
        work[row], work[pivot] = work[pivot], work[row]
        for other in range(len(work)):
            operations += 1
            if other != row and ((work[other] >> col) & 1):
                work[other] ^= work[row]
                operations += width
        pivot_rows.append((row, col))
        row += 1
        if row == len(work):
            break
    coefficient_mask = (1 << nvars) - 1
    for equation in work:
        if equation & coefficient_mask == 0 and (equation >> nvars) & 1:
            return None, operations
    solution = 0
    for pivot_row, col in pivot_rows:
        if (work[pivot_row] >> nvars) & 1:
            solution |= 1 << col
    return solution, operations


def _reference_algorithm(inst: dict) -> dict:
    """Try four traces and solve the induced F2-linear systems."""
    n, modulus = inst["n"], inst["modulus"]
    dimension = 2 * n
    y = tuple(inst["target"])
    y_bits = y[0] | (y[1] << n)
    a = tuple(inst["a"])
    start = time.perf_counter()
    operations = 0
    answer = None
    for t in ((0, 0), (1, 0), (0, 1), (1, 1)):
        rows = [0] * dimension
        for col in range(dimension):
            basis = ((1 << col), 0) if col < n else (0, 1 << (col - n))
            image = _e_add(_e_mul(a, _e_square(basis, modulus, n),
                                  modulus, n),
                           _e_mul(t, basis, modulus, n))
            encoded = image[0] | (image[1] << n)
            for output_bit in range(dimension):
                operations += 1
                if (encoded >> output_bit) & 1:
                    rows[output_bit] |= 1 << col
        for output_bit in range(dimension):
            if (y_bits >> output_bit) & 1:
                rows[output_bit] |= 1 << dimension
        trace_u = inst["trace_mask"]
        trace_v = inst["trace_mask"] << n
        rows.extend([
            trace_u | (t[0] << dimension),
            trace_v | (t[1] << dimension),
        ])
        encoded_answer, used = _solve_binary(rows, dimension)
        operations += used
        if encoded_answer is None:
            continue
        candidate = [encoded_answer & ((1 << n) - 1),
                     encoded_answer >> n]
        if verify(inst, candidate)[0]:
            answer = candidate
            break
    ok = answer is not None and verify(inst, answer)[0]
    return {
        "answer": answer,
        "ok": ok,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _attack_outlier(inst: dict) -> list[int]:
    n = inst["n"]
    target = inst["target"]
    choices = [1, 2, 1 << (n - 1), (1 << n) - 1,
               target[0] or 1, target[1] or 2]
    for u in choices:
        for v in choices:
            candidate = [u, v]
            if u != v and verify(inst, candidate)[0]:
                return candidate
    return [1, 2]


def _attack_greedy(inst: dict) -> list[int]:
    return [1, 2]


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 512) -> list[int]:
    rng = random.Random(seed ^ 0x250624012)
    last = [1, 2]
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_drop_trace(inst: dict) -> list[int]:
    """Wrong by-hand ansatz: solve only a*x^2=y by repeated square roots."""
    n, modulus = inst["n"], inst["modulus"]
    a_inv = _e_square(tuple(inst["a"]), modulus, n)
    value = _e_mul(a_inv, tuple(inst["target"]), modulus, n)
    # E has absolute degree 2n, so sqrt(z)=z^(2^(2n-1)).
    for _ in range(2 * n - 1):
        value = _e_square(value, modulus, n)
    return list(value)


def _frobenius_relabel(inst: dict, power: int) -> tuple[dict, list[int]]:
    moved = {key: value for key, value in inst.items() if key != "answer"}
    moved["a"] = list(_e_frobenius(tuple(inst["a"]), power,
                                     inst["modulus"], inst["n"]))
    moved["target"] = list(_e_frobenius(tuple(inst["target"]), power,
                                          inst["modulus"], inst["n"]))
    moved_decoys = []
    for coefficient, shift in inst["decoy_terms"]:
        moved_coefficient = _e_frobenius(tuple(coefficient), power,
                                         inst["modulus"], inst["n"])
        moved_decoys.append([list(moved_coefficient), shift])
    moved["decoy_terms"] = moved_decoys
    carried = list(_e_frobenius(tuple(inst["answer"]), power,
                                inst["modulus"], inst["n"]))
    moved["answer"] = carried
    return moved, carried


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    # A conservative tokenizer-independent upper bound.
    return len(encoded), len(encoded), 2


def selftest() -> dict:
    """Run every mandatory gate and return measured JSON-native evidence."""
    report: dict = {}

    checks = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not (ok and json_ok):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": why, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "generation_route": "inverse generation followed by exact evaluation",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    u, v = inst["answer"]
    corruptions = {
        "drop_one": [u],
        "swap_order": [v, u],
        "duplicate": [u, u],
        "empty": [],
        "out_of_range": [1 << inst["n"], v],
    }
    reasons = {}
    rejected = True
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        rejected &= not ok
        reasons[name] = why
    distinct = len(set(reasons.values())) == len(corruptions)
    report["G2_rejects_corruption"] = {
        "pass": rejected and distinct,
        "rejections": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    realistic = (
        "I used the trace relation and reduced in the stated basis.\n\n"
        "```json\n"
        f"<answer>{json.dumps(inst['answer'])}</answer>\n"
        "```\nThe components are in constant,W order."
    )
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("no tagged answer here") is None
    report["G3_round_trip"] = {
        "pass": (parsed == inst["answer"] and verify(inst, parsed)[0]
                 and garbage_none),
        "parsed_matches": parsed == inst["answer"],
        "garbage_returns_none": garbage_none,
        "json_native": True,
    }

    guess_rng = random.Random(0x250624012)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_seconds = time.perf_counter() - guess_start
    density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": density,
        "structure_aware_space": search_space(inst),
        "prior": "uniform over the promised nonzero, distinct component pairs",
        "sampling_wall_seconds": guess_seconds,
    }

    baseline_start = time.perf_counter()
    baseline_candidate = _attack_random_restart(inst, 2026, restarts=4096)
    baseline_seconds = time.perf_counter() - baseline_start
    baseline_success = verify(inst, baseline_candidate)[0]
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (density < 1e-6 and not baseline_success
                 and demo_count is not None),
        "shipping_observed_valid_fraction": density,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": guess_hits,
        "shipping_candidate_space": search_space(inst),
        "theorem_guaranteed_total_preimages": 1,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_seconds": baseline_seconds,
        "baseline_iterations": 4096,
        "baseline_successes": int(baseline_success),
    }

    attack_names = {
        "outlier_low_or_extreme_hamming_weight": 0,
        "greedy_lexicographically_smallest": 0,
        "random_restart_512_structure_aware": 0,
        "by_hand_drop_the_trace_term": 0,
    }
    reference_runs = []
    compact_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_names["outlier_low_or_extreme_hamming_weight"] += int(
            verify(trial, _attack_outlier(trial))[0])
        attack_names["greedy_lexicographically_smallest"] += int(
            verify(trial, _attack_greedy(trial))[0])
        attack_names["random_restart_512_structure_aware"] += int(
            verify(trial, _attack_random_restart(trial, seed))[0])
        attack_names["by_hand_drop_the_trace_term"] += int(
            verify(trial, _attack_drop_trace(trial))[0])
        reference_runs.append(_reference_algorithm(trial))
        compact_runs.append(_compact_inverse(trial))
    ref_ok = sum(int(run["ok"]) for run in reference_runs)
    compact_ok = sum(int(run["ok"]) for run in compact_runs)
    all_attacks_failed = all(value == 0 for value in attack_names.values())
    ref_wall = sum(run["wall_clock_sec"] for run in reference_runs)
    ref_operations = sum(run["operations"] for run in reference_runs)
    compact_wall = sum(run["wall_clock_sec"] for run in compact_runs)
    compact_max_ops = max(run["field_operations"] for run in compact_runs)
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_ok == 8 and compact_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_names.items()
        },
        "reference_algorithm": {
            "name": "four trace branches plus Gaussian elimination over GF(2)",
            "complexity": "O(n^3) bit operations",
            "wall_clock_sec": ref_wall,
            "mean_wall_clock_sec": ref_wall / 8,
            "operations": ref_operations,
            "mean_operations": ref_operations // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
        "compact_route": {
            "name": "relative-trace invariant plus two half-traces",
            "wall_clock_sec": compact_wall,
            "max_field_operations": compact_max_ops,
            "solves": f"{compact_ok}/8",
        },
    }

    doubled_n = 2 * ship_params["n"] + 1
    doubled_decoys = 2 * ship_params["decoy_terms"] + 1
    doubled = make_instance(n=doubled_n, decoy_terms=doubled_decoys, seed=77)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n > 2 * ship_params["n"],
        "base_n": ship_params["n"],
        "doubled_valid_n": doubled_n,
        "base_decoy_terms": ship_params["decoy_terms"],
        "doubled_decoy_terms": doubled_decoys,
        "doubled_verify": doubled_why,
        "candidate_space_bits": 2 * doubled_n,
    }

    invariant_ok = 0
    witness_ok = 0
    reorder_ok = 0
    attempts = 0
    for seed in range(20):
        trial = make_instance(seed=seed + 700, **ship_params)
        # Powers 1 and 2, their composition 3, and inverse Frobenius -1.
        for power in (1, 2, 3, 2 * trial["n"] - 1):
            moved, carried = _frobenius_relabel(trial, power)
            attempts += 1
            invariant_ok += int(canonical_key(moved) == canonical_key(trial))
            witness_ok += int(verify(moved, carried)[0])
        reordered = {key: value for key, value in trial.items()}
        reordered["decoy_terms"] = list(reversed(trial["decoy_terms"]))
        reorder_ok += int(canonical_key(reordered) == canonical_key(trial)
                          and verify(reordered, trial["answer"])[0])
    unrelated = {
        canonical_key(make_instance(seed=9000 + seed, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariant_ok == attempts and witness_ok == attempts
                 and reorder_ok == 20 and len(unrelated) == 20),
        "invariance_checks": invariant_ok,
        "invariance_attempts": attempts,
        "transformed_witness_checks": witness_ok,
        "decoy_reorder_checks": reorder_ok,
        "unrelated_distinct": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": (
            "all tested GF(2)-Frobenius automorphisms, including generators, "
            "composition, inverse, and reordering of zero polynomial identities"
        ),
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    evidence = G9_EVIDENCE
    h_attempts = evidence["hinted"]["attempts"]
    p_attempts = evidence["placebo"]["attempts"]
    h_rate = evidence["hinted"]["solved"] / h_attempts if h_attempts else 0.0
    p_rate = evidence["placebo"]["solved"] / p_attempts if p_attempts else 0.0
    within_caps = (chars <= 2000 and tokens <= 500 and elements <= 256
                   and compact_max_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": h_rate - p_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": compact_max_ops,
        "caps": {"chars": 2000, "tokens": 500,
                 "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
