"""Verified problem generator for arXiv:0902.4670.

The paper represents ideal classes of imaginary quadratic orders by primitive
positive-definite binary quadratic forms.  Its relation (3) ranges over signs
of oriented prime forms and its class-group implementation tests these signs
by exact form arithmetic.  This module asks for one such sign relation.

Instances are inverse-generated from the principal norm identity

    x^2 - D = 4 * product(ell_i).

The signs are known before the displayed forms are assembled.  The verifier
never reads the planted answer: it combines the signed roots by CRT and uses
an exact norm test for principality.  Importing the module performs no I/O.
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
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this module has a stdlib-only path
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "imaginary-quadratic discriminant",
        "oriented primitive positive-definite binary quadratic forms",
        "signed ideal-class relation",
    ],
    "verification_operations": [
        "Chinese remainder combination of oriented prime-form roots",
        "exact integer multiplication and congruence",
        "exact integer square root",
        "binary quadratic norm identity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The discriminant and the product of all prime-form norms conceal a "
        "principal norm identity; without recognizing it, the paper's relation "
        "evaluation ranges over every sign vector."
    ),
    "hardness_basis": (
        "Track B, in the arity-k relation regime of equation (3) and Section "
        "2.3: the paper's count enumerates 2^(k-1) signs, while the measured "
        "standard improvement is meet-in-the-middle on reduced form classes in "
        "O(2^(k/2) poly(log|D|)) time and memory; at shipping k=31 it averaged "
        "48,836.5 candidates and 1,237,669.75 counted exact operations (1.841 "
        "seconds mean and 3.422 seconds maximum in the final self-test), "
        "while the principal-norm "
        "invariant recovers the signs in 178 exact arithmetic operations if noticed."
    ),
    "max_answer_tokens": 24,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly k signs, each +1 or -1, with the first sign "
        "fixed to +1 to quotient the global inversion symmetry."
    ),
    "bounds": {
        "length": "instance arity k",
        "alphabet": [-1, 1],
        "first_sign": 1,
        "maximum_shipping_length": 31,
        "maximum_supported_length": 248,
    },
}

DIFFICULTY = {
    "demo": {"n": 5, "prime_bits": 7},
    "easy": {"n": 31, "prime_bits": 14},
    # Grow the arithmetic haystack at fixed witness length before increasing n.
    "medium": {"n": 31, "prime_bits": 22},
    "hard": {"n": 31, "prime_bits": 30},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Inspect the discriminant together with the product of the prime-form "
    "norms for a concealed principal norm identity."
)
PLACEBO_HINT = (
    "Keep the orientation convention and the fixed first sign in view while "
    "checking the displayed congruences."
)

# Filled from the script-owned transcripts after the three oracle arms run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted": {"solved": 0, "attempts": 3, "error_calls": 0},
    "placebo": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Paper definition.  Section 2.1 identifies End(E) with the order of conductor u
between Z[pi] and O_K.  Section 2.2 represents its ideal classes by primitive
positive-definite binary quadratic forms (a,b,c), with D=b^2-4ac, and says
that reduced forms uniquely represent classes.  Section 2.3 defines a relation
R by oriented split-prime classes alpha_i and signs tau_i in {+1,-1}; equation
(3) counts the sign vectors whose product is principal.  It explicitly fixes
one sign using global inversion and evaluates the remaining 2^(k-1) choices.

Step 0 and the easy boundary.  The full endomorphism-ring answer is not merely
read from a CM construction.  Algorithm Certify obtains relations by
FindRelation, and Algorithm Verify evaluates them by isogeny walks.  Proposition
6 bounds FindRelation heuristically by L[1/2,*], Proposition 9 bounds Verify by
L[1/2,*], and Corollary 8 bounds certificate size.  Small conductor primes are
easy by isogeny climbing (Algorithm 1, lines 3--4), so this module does not make
a Track-A endomorphism-ring claim; Section 3.3 also notes Algorithm 2 can be
much faster when u is small relative to v.  For the relation object itself,
Section 2.3 makes small arity easy by direct sign enumeration, so shipping uses
k=31 rather than the five-form demo.  The module isolates the central relation
object and declares Track B openly: generic relation search is mechanical,
while the inverse construction leaves a short norm-identity route.

Construction.  Sample k distinct odd primes ell_i and let A be their product.
Choose odd x coprime to A with A < x^2 < 3A, and set D=x^2-4A.  For each ell_i,
choose an independent orientation s_i and publish b_i congruent to s_i*x modulo
2ell_i.  Then (ell_i,b_i,(b_i^2-D)/(4ell_i)) is a primitive positive-definite
form of discriminant D.  Dirichlet composition for the pairwise-coprime norms
combines the planted signed roots to B congruent to x modulo 2A, producing the
form (A,B,(B^2-D)/(4A)); it represents 1 and is principal.  This is composition
of identities, not recovery of an answer from a completed instance.

Exact verifier shortcut.  Here A < |D| < 3A.  If the combined form Q represents
1, multiplying Q(r,s)=1 by 4A gives
(2Ar+Bs)^2-Ds^2=4A.  The size bound forces |s|=1, so 4A+D must be a square x^2
and B is congruent to +x or -x modulo 2A.  The converse supplies r directly.
Thus exact CRT, isqrt, squaring and congruence decide the witness without an
oracle, floating point, class-number table, or planted-answer access.

Hardness and attacks.  Every displayed prime participates and every orientation
is independently randomized; there is no special planted element.  The panel
tests all-positive/canonical orientations, a smallest-root outlier rule, a
prefix-CRT greedy rule, a small by-hand sign window, and random restarts.  The
paper's exhaustive 2^(k-1) sign scan is improved by the reported Track-B
reference algorithm to a generic meet-in-the-middle search on reduced form
classes.  The intended compact route computes A, recognizes 4A+D as a square,
and compares its root modulo each 2ell_i.
""".strip()


_MR_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def _is_prime(value: int) -> bool:
    """Deterministic primality test for all values used by this module."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    for prime in _SMALL_PRIMES:
        if value % prime == 0:
            return value == prime
    if value >= 1 << 64:
        # Escalation is capped below 31 bits, so this exact fallback is defensive.
        divisor = 41
        limit = math.isqrt(value)
        while divisor <= limit:
            if value % divisor == 0:
                return False
            divisor += 2
        return True
    odd = value - 1
    twos = 0
    while odd % 2 == 0:
        odd //= 2
        twos += 1
    for base in _MR_BASES_64:
        if base % value == 0:
            continue
        x = pow(base, odd, value)
        if x in (1, value - 1):
            continue
        for _ in range(twos - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _sample_primes(count: int, bits: int, rng: random.Random) -> list[int]:
    lower = 1 << (bits - 1)
    upper = 1 << bits
    primes: set[int] = set()
    budget = max(20_000, count * bits * 100)
    for _ in range(budget):
        candidate = rng.randrange(lower, upper) | 1
        if _is_prime(candidate):
            primes.add(candidate)
            if len(primes) == count:
                result = list(primes)
                rng.shuffle(result)
                return result
    # This is deterministic and still samples every selected prime from the same
    # interval; it only handles an exceptionally unlucky random stream.
    for candidate in range(lower | 1, upper, 2):
        if _is_prime(candidate):
            primes.add(candidate)
            if len(primes) == count:
                result = list(primes)
                rng.shuffle(result)
                return result
    raise ValueError("prime_bits interval contains too few distinct primes")


def make_instance(n: int, seed: int = 0, prime_bits: int = 14,
                  **params: Any) -> dict:
    """Inverse-generate an oriented prime-form relation and its sign witness."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or not 5 <= n <= 248:
        raise ValueError("n must be an integer in [5,248]")
    if (isinstance(prime_bits, bool) or not isinstance(prime_bits, int)
            or not 6 <= prime_bits <= 31):
        raise ValueError("prime_bits must be an integer in [6,31]")

    master = random.Random(seed)
    prime_rng = random.Random(master.getrandbits(128))
    norm_rng = random.Random(master.getrandbits(128))
    orientation_rng = random.Random(master.getrandbits(128))
    order_rng = random.Random(master.getrandbits(128))

    primes = _sample_primes(n, prime_bits, prime_rng)
    total_norm = math.prod(primes)
    low = math.isqrt(total_norm) + 1  # total_norm is squarefree, hence nonsquare
    high = math.isqrt(3 * total_norm - 1)
    while True:
        hidden_root = norm_rng.randrange(low, high + 1) | 1
        if hidden_root <= high and math.gcd(hidden_root, total_norm) == 1:
            break
    discriminant = hidden_root * hidden_root - 4 * total_norm

    records: list[tuple[dict[str, int], int]] = []
    while True:
        records.clear()
        for ell in primes:
            orientation = orientation_rng.choice((-1, 1))
            b = (orientation * hidden_root) % (2 * ell)
            c = (b * b - discriminant) // (4 * ell)
            records.append(({"ell": ell, "b": b, "c": c}, orientation))
        order_rng.shuffle(records)
        answer = [orientation for _, orientation in records]
        if answer[0] == -1:
            answer = [-sign for sign in answer]
        # G2 needs a genuine internal swap, and avoiding a constant answer also
        # removes an obvious statistical accident.  This resamples orientations,
        # not a relation: both global sign choices are known by construction.
        if 1 in answer[1:] and -1 in answer[1:]:
            break

    forms = [record for record, _ in records]
    return {
        "n": n,
        "prime_bits": prime_bits,
        "discriminant": discriminant,
        "forms": forms,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a self-contained signed binary-quadratic-form relation problem."""
    rows = "\n".join(
        f"  {index}: ell={form['ell']}, b={form['b']}, c={form['c']}"
        for index, form in enumerate(inst["forms"])
    )
    format_example = json.dumps(
        [1] + [(-1 if i % 2 else 1) for i in range(1, inst["n"])],
        separators=(",", ":"),
    )
    statement = f"""Find a principal signed relation among oriented binary quadratic forms.

A binary quadratic form is Q(X,Y)=a X^2+b XY+c Y^2.  Its discriminant is
D=b^2-4ac.  All forms below are primitive positive-definite forms with the same
negative discriminant

  D = {inst['discriminant']}.

Row i gives the oriented prime form Q_i=(ell_i,b_i,c_i).  Choose one sign
epsilon_i in {{+1,-1}} for every row.  Let

  A = product_i ell_i.

There is a unique odd B in the half-open interval 0 <= B < 2A satisfying

  B = epsilon_i*b_i (mod 2*ell_i)  for every i.

(The ell_i are distinct odd primes, so these congruences are compatible and
determine B.)  Put C=(B^2-D)/(4A).  Your signs are valid exactly when the
combined form Q=(A,B,C) is principal.  Here "principal" means that there exist
integers r,s with A*r^2+B*r*s+C*s^2=1.

Because negating every sign gives the inverse of the same relation, fix
epsilon_0=+1.  Row indices are 0-based, list entry i is epsilon_i, every row
gets exactly one sign, and signs may repeat.  All congruence intervals above
use the stated inclusive/exclusive endpoints.

The {inst['n']} rows are:
{rows}

Give your final answer inside <answer></answer> tags as a JSON list of exactly
{inst['n']} integers, each 1 or -1, with the first entry 1.
Format example: <answer>{format_example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the delimited JSON sign vector, tolerating surrounding prose."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:json|text)?\s*", "", payload,
                     flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def _instance_data(inst: dict) -> tuple[int, int, list[dict[str, int]]]:
    forms = inst.get("forms")
    discriminant = inst.get("discriminant")
    if not isinstance(forms, list) or not forms:
        raise ValueError("instance has no forms")
    if isinstance(discriminant, bool) or not isinstance(discriminant, int):
        raise ValueError("invalid discriminant")
    total_norm = 1
    seen: set[int] = set()
    for form in forms:
        if not isinstance(form, dict):
            raise ValueError("invalid form row")
        ell, b, c = form.get("ell"), form.get("b"), form.get("c")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (ell, b, c)):
            raise ValueError("noninteger form coefficient")
        if ell in seen or not _is_prime(ell) or ell % 2 == 0:
            raise ValueError("norms are not distinct odd primes")
        if not 0 <= b < 2 * ell or b * b - 4 * ell * c != discriminant:
            raise ValueError("form row has the wrong discriminant")
        if math.gcd(math.gcd(ell, b), c) != 1 or ell <= 0 or c <= 0:
            raise ValueError("form row is not primitive positive-definite")
        seen.add(ell)
        total_norm *= ell
    return discriminant, total_norm, forms


def _crt_plan(forms: list[dict[str, int]], total_norm: int
              ) -> list[tuple[int, int]]:
    """Return the CRT contribution for each sign (-1,+1), in that order."""
    plan: list[tuple[int, int]] = []
    for form in forms:
        ell = form["ell"]
        b = form["b"]
        cofactor = total_norm // ell
        weight = cofactor * pow(cofactor, -1, ell)
        minus_residue = (-b - 1) // 2 % ell
        plus_residue = (b - 1) // 2 % ell
        plan.append(((minus_residue * weight) % total_norm,
                     (plus_residue * weight) % total_norm))
    return plan


def _combined_b(signs: list[int], total_norm: int,
                plan: list[tuple[int, int]]) -> int:
    z = sum(plan[i][1 if sign == 1 else 0]
            for i, sign in enumerate(signs)) % total_norm
    return 2 * z + 1


def _principal_target(discriminant: int, total_norm: int) -> int | None:
    """The positive root forced by the exact norm equation, if it exists."""
    value = 4 * total_norm + discriminant
    if value < 0:
        return None
    root = math.isqrt(value)
    return root if root * root == value else None


def _is_valid_with_plan(signs: list[int], discriminant: int, total_norm: int,
                        plan: list[tuple[int, int]]) -> bool:
    b = _combined_b(signs, total_norm, plan)
    root = _principal_target(discriminant, total_norm)
    if root is None:
        return False
    modulus = 2 * total_norm
    return (b - root) % modulus == 0 or (b + root) % modulus == 0


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid normalized sign relation without consulting the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected = len(inst.get("forms", []))
    if len(answer) < expected:
        return False, f"too few signs: expected {expected}"
    if len(answer) > expected:
        return False, f"too many signs: expected {expected}"
    if any(isinstance(sign, bool) or not isinstance(sign, int)
           or sign not in (-1, 1) for sign in answer):
        return False, "every entry must be the integer 1 or -1"
    if answer[0] != 1:
        return False, "the first sign must be 1"
    try:
        discriminant, total_norm, forms = _instance_data(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"invalid instance: {exc}"
    if discriminant >= 0 or discriminant % 4 != 1:
        return False, "invalid instance: D must be negative and 1 modulo 4"
    # This exact bound is what makes the executable principality criterion
    # complete: Q(r,s)=1 forces |s|=1, as proved in NOTES.
    if not total_norm < -discriminant < 4 * total_norm:
        return False, "invalid instance: norm bound needed for exact verifier"
    plan = _crt_plan(forms, total_norm)
    if not _is_valid_with_plan(answer, discriminant, total_norm, plan):
        return False, "the signed combined form is not principal"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the structure-aware, global-sign-normalized language."""
    count = len(inst["forms"])
    return [1] + [rng.choice((-1, 1)) for _ in range(count - 1)]


def search_space(inst: dict) -> int | None:
    """The exact number of normalized sign vectors."""
    count = len(inst["forms"])
    return 1 << (count - 1)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact valid-answer count when at most 2^16 vectors exist."""
    space = search_space(inst)
    if space is None or space > 65_536:
        return None
    discriminant, total_norm, forms = _instance_data(inst)
    plan = _crt_plan(forms, total_norm)
    count = 0
    for tail in itertools.product((-1, 1), repeat=len(forms) - 1):
        count += int(_is_valid_with_plan([1, *tail], discriminant,
                                         total_norm, plan))
    return count


def canonical_key(inst: dict) -> str:
    """Invariant under row permutation and independent prime-form inversions."""
    discriminant, _, forms = _instance_data(inst)
    normalized = {
        "D": discriminant,
        # At a split prime the two orientations are inverse classes.  Independent
        # inversion merely renames the corresponding sign coordinate.
        "norms": sorted(form["ell"] for form in forms),
    }
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """First enlarge arithmetic at fixed witness length, then enlarge arity."""
    result = {key: value for key, value in params.items() if key != "_preset"}
    bits = int(result.get("prime_bits", 14))
    n = int(result.get("n", 31))
    if bits < 30:
        result["prime_bits"] = min(30, bits + 4)
        return result
    if n + 8 <= 248:
        result["n"] = n + 8
        return result
    return "cap_bound"


def _normalize_signs(signs: list[int]) -> list[int]:
    return signs if signs[0] == 1 else [-sign for sign in signs]


def _compact_route(inst: dict) -> tuple[list[int] | None, int]:
    """Execute and count the intended invariant route; never inspect the answer."""
    discriminant, total_norm, forms = _instance_data(inst)
    # Count n-1 multiplications for A, then multiply by 4 and add D.
    operations = max(0, len(forms) - 1) + 2
    value = 4 * total_norm + discriminant
    root = math.isqrt(value)
    # A conservative bit-level Newton/isqrt allowance, even though math.isqrt is
    # one library call in the executable route.
    operations += 3 * (value.bit_length().bit_length() + 1)
    if root * root != value:
        return None, operations + 1
    operations += 1
    signs: list[int] = []
    for form in forms:
        modulus = 2 * form["ell"]
        residue = root % modulus
        operations += 1
        if form["b"] == residue:
            signs.append(1)
        elif (-form["b"]) % modulus == residue:
            signs.append(-1)
            operations += 1
        else:
            return None, operations + 1
        operations += 1
    if signs[0] == -1:
        signs = [-sign for sign in signs]
        operations += len(signs)
    return signs, operations


def _reduce_form(a: int, b: int, c: int) -> tuple[tuple[int, int, int], int]:
    """Gauss-reduce a positive-definite form; return its canonical form and steps."""
    steps = 0
    while True:
        shift = (a - b) // (2 * a)
        if shift:
            c = c + b * shift + a * shift * shift
            b = b + 2 * a * shift
            steps += 1
        if a > c:
            a, b, c = c, -b, a
            steps += 1
            continue
        if abs(b) <= a <= c:
            if (abs(b) == a or a == c) and b < 0:
                b = -b
                steps += 1
            return (a, b, c), steps
        raise ArithmeticError("quadratic-form reduction invariant failed")


def _partial_class(forms: list[dict[str, int]], signs: list[int],
                   discriminant: int,
                   total_norm: int, plan: list[tuple[int, int]]) -> tuple[
                       tuple[int, int, int], int]:
    b = _combined_b(signs, total_norm, plan)
    numerator = b * b - discriminant
    denominator = 4 * total_norm
    if numerator % denominator:
        raise ArithmeticError("CRT combination did not produce an integral form")
    c = numerator // denominator
    reduced, reduction_steps = _reduce_form(total_norm, b, c)
    # Per candidate: choose/sum CRT contributions, reduce modulo A, form B,
    # square/subtract/divide for C, then the measured Gauss steps.
    operations = len(forms) + 6 + reduction_steps
    return reduced, operations


def _reference_mitm(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Generic meet-in-the-middle search on exact reduced form-class keys."""
    discriminant, _, forms = _instance_data(inst)
    split = (len(forms) + 1) // 2
    left_forms = forms[:split]
    right_forms = forms[split:]
    left_norm = math.prod(form["ell"] for form in left_forms)
    right_norm = math.prod(form["ell"] for form in right_forms)
    left_plan = _crt_plan(left_forms, left_norm)
    right_plan = _crt_plan(right_forms, right_norm)
    table: dict[tuple[int, int, int], list[int]] = {}
    operations = 2 * len(forms)
    reductions = 0
    left_candidates = 0
    right_candidates = 0
    reduction_steps = 0

    for tail in itertools.product((-1, 1), repeat=len(left_forms) - 1):
        signs = [1, *tail]
        key, cost = _partial_class(left_forms, signs, discriminant,
                                   left_norm, left_plan)
        table.setdefault(key, signs)
        left_candidates += 1
        reductions += 1
        operations += cost
        reduction_steps += cost - len(left_forms) - 6

    for tail in itertools.product((-1, 1), repeat=len(right_forms)):
        signs = list(tail)
        key, cost = _partial_class(right_forms, signs, discriminant,
                                   right_norm, right_plan)
        inverse_key, inverse_steps = _reduce_form(key[0], -key[1], key[2])
        right_candidates += 1
        reductions += 2
        operations += cost + inverse_steps + 1
        reduction_steps += cost - len(right_forms) - 6 + inverse_steps
        left = table.get(inverse_key)
        if left is not None:
            candidate = left + signs
            if verify(inst, candidate)[0]:
                return candidate, {
                    "candidates": left_candidates + right_candidates,
                    "left_candidates": left_candidates,
                    "right_candidates": right_candidates,
                    "form_reductions": reductions,
                    "reduction_steps": reduction_steps,
                    "operations": operations,
                    "table_entries": len(table),
                }
    return None, {
        "candidates": left_candidates + right_candidates,
        "left_candidates": left_candidates,
        "right_candidates": right_candidates,
        "form_reductions": reductions,
        "reduction_steps": reduction_steps,
        "operations": operations,
        "table_entries": len(table),
    }


def _greedy_prefix(inst: dict) -> list[int]:
    forms = inst["forms"]
    signs = [1]
    first = forms[0]
    current_modulus = first["ell"]
    current_z = (first["b"] - 1) // 2 % current_modulus
    for form in forms[1:]:
        ell, b = form["ell"], form["b"]
        choices = []
        for sign in (-1, 1):
            residue = (sign * b - 1) // 2 % ell
            step = ((residue - current_z) *
                    pow(current_modulus, -1, ell)) % ell
            candidate = current_z + current_modulus * step
            new_modulus = current_modulus * ell
            combined_b = 2 * candidate + 1
            centered = min(combined_b, 2 * new_modulus - combined_b)
            choices.append((centered, sign, candidate))
        _, chosen, current_z = min(choices)
        signs.append(chosen)
        current_modulus *= ell
    return signs


def _attack_candidates(inst: dict, seed: int) -> dict[str, list[int] | None]:
    forms = inst["forms"]
    count = len(forms)
    discriminant, total_norm, _ = _instance_data(inst)
    plan = _crt_plan(forms, total_norm)
    all_positive = [1] * count
    smallest_root = _normalize_signs([
        1 if form["b"] <= form["ell"] else -1 for form in forms
    ])
    greedy = _greedy_prefix(inst)

    by_hand_result = None
    fixed = smallest_root[:]
    free = min(8, count - 1)
    for mask in range(1 << free):
        candidate = fixed[:]
        for bit in range(free):
            candidate[bit + 1] = 1 if mask >> bit & 1 else -1
        if _is_valid_with_plan(candidate, discriminant, total_norm, plan):
            by_hand_result = candidate
            break

    restart_result = None
    rng = random.Random(seed)
    for _ in range(2048):
        candidate = random_candidate(inst, rng)
        if _is_valid_with_plan(candidate, discriminant, total_norm, plan):
            restart_result = candidate
            break
    return {
        "outlier_all_positive": all_positive,
        "outlier_smallest_oriented_root": smallest_root,
        "greedy_minimum_prefix_crt": greedy,
        "by_hand_first_8_signs": by_hand_result,
        "random_restart_2048": restart_result,
    }


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def _permuted_and_inverted(inst: dict, seed: int
                          ) -> tuple[dict, list[int]]:
    rng = random.Random(seed)
    order = list(range(len(inst["forms"])))
    rng.shuffle(order)
    inversion = [rng.choice((False, True)) for _ in order]
    forms = []
    signs = []
    source_answer = inst["answer"]
    for new_position, old_position in enumerate(order):
        form = dict(inst["forms"][old_position])
        sign = source_answer[old_position]
        if inversion[new_position]:
            form["b"] = (-form["b"]) % (2 * form["ell"])
            form["c"] = (form["b"] * form["b"] - inst["discriminant"]) // (
                4 * form["ell"])
            sign = -sign
        forms.append(form)
        signs.append(sign)
    signs = _normalize_signs(signs)
    transformed = dict(inst)
    transformed["forms"] = forms
    # Deliberately do not install the carried answer into transformed.  The
    # checker test receives it explicitly and canonical_key cannot consult it.
    transformed["answer"] = list(inst["answer"])
    return transformed, signs


def selftest() -> dict:
    """Run G1--G9 and return all measured evidence as a JSON-native dict."""
    report: dict[str, Any] = {
        "paper": "0902.4670",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    failures: list[str] = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    planted = list(ship["answer"])
    plus_positions = [i for i in range(1, len(planted)) if planted[i] == 1]
    minus_positions = [i for i in range(1, len(planted)) if planted[i] == -1]
    swapped = planted[:]
    swapped[plus_positions[0]], swapped[minus_positions[0]] = (
        swapped[minus_positions[0]], swapped[plus_positions[0]])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_opposite_signs": swapped,
        "duplicate_one": planted + [planted[-1]],
        "empty": [],
        "out_of_range": planted[:1] + [0] + planted[2:],
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    answer_json = json.dumps(planted, separators=(",", ":"))
    realistic = (
        "The CRT checks lead to the following relation.\n```json\n"
        f"<answer>{answer_json}</answer>\n```\n"
        "The first orientation is normalized as requested."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    sample_total = 250_000
    sample_rng = random.Random(8675309)
    discriminant, total_norm, forms = _instance_data(ship)
    plan = _crt_plan(forms, total_norm)
    sample_hits = 0
    for _ in range(sample_total):
        candidate = random_candidate(ship, sample_rng)
        sample_hits += int(_is_valid_with_plan(candidate, discriminant,
                                               total_norm, plan))
    density = sample_hits / sample_total
    exact_probability = 1 / search_space(ship)
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": density,
        "construction_proved_probability": exact_probability,
        "construction_proved_valid_answers": 1,
        "candidate_space": search_space(ship),
        "sampler": "uniform sign vectors conditioned on epsilon_0=+1",
    }

    attack_names = [
        "outlier_all_positive",
        "outlier_smallest_oriented_root",
        "greedy_minimum_prefix_crt",
        "by_hand_first_8_signs",
        "random_restart_2048",
    ]
    attacks = {name: {"successes": 0, "attempts": 8}
               for name in attack_names}
    reference_successes = 0
    reference_times: list[float] = []
    reference_candidates: list[int] = []
    reference_operations: list[int] = []
    reference_reductions: list[int] = []
    reference_reduction_steps: list[int] = []
    reference_table_entries: list[int] = []
    for seed in range(8):
        trial = make_instance(seed=12_000 + seed, **ship_params)
        for name, candidate in _attack_candidates(trial, 700_000 + seed).items():
            if candidate is not None and verify(trial, candidate)[0]:
                attacks[name]["successes"] += 1
        started = time.perf_counter()
        found, metrics = _reference_mitm(trial)
        reference_times.append(time.perf_counter() - started)
        reference_candidates.append(metrics["candidates"])
        reference_operations.append(metrics["operations"])
        reference_reductions.append(metrics["form_reductions"])
        reference_reduction_steps.append(metrics["reduction_steps"])
        reference_table_entries.append(metrics["table_entries"])
        reference_successes += int(
            found is not None and verify(trial, found)[0])

    reference = {
        "name": "meet-in-the-middle signed relation search on reduced form classes",
        "complexity": "O(2^(k/2) poly(log|D|)) time and memory",
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "candidates_mean": sum(reference_candidates) / len(reference_candidates),
        "candidates_max": max(reference_candidates),
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "form_reductions_mean": sum(reference_reductions) / len(reference_reductions),
        "form_reductions_max": max(reference_reductions),
        "reduction_steps_mean": (
            sum(reference_reduction_steps) / len(reference_reduction_steps)),
        "reduction_steps_max": max(reference_reduction_steps),
        "table_entries_mean": sum(reference_table_entries) / len(reference_table_entries),
        "table_entries_max": max(reference_table_entries),
        "solves": f"{reference_successes}/8, as expected",
    }
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    shipping_count = enumerate_all(ship)
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and sample_total >= 200_000
        and reference_successes == 8,
        "shipping_density_hits": sample_hits,
        "shipping_density_total": sample_total,
        "shipping_observed_fraction": density,
        "shipping_construction_proved_fraction": exact_probability,
        "shipping_construction_proved_valid_solution_count": 1,
        "shipping_valid_solution_count": shipping_count,
        "shipping_structure_aware_space": search_space(ship),
        "demo_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_sec_max": reference["wall_clock_sec_max"],
        "baseline_candidates_mean": reference["candidates_mean"],
        "baseline_candidates_max": reference["candidates_max"],
        "baseline_operations_mean": reference["operations_mean"],
        "baseline_operations_max": reference["operations_max"],
        "baseline_form_reductions_mean": reference["form_reductions_mean"],
        "baseline_reduction_steps_mean": reference["reduction_steps_mean"],
    }
    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(ship),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_space": search_space(ship),
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "answer_elements_shipping": _atom_count(ship["answer"]),
        "answer_elements_doubled": _atom_count(doubled["answer"]),
    }

    invariance = 0
    real_transforms = 0
    composed = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(original)
        unrelated_keys.append(key)
        transformed, carried = _permuted_and_inverted(original, 30_000 + seed)
        if canonical_key(transformed) == key:
            invariance += 1
        else:
            g8_failures.append(f"permutation/inversion changed key at seed {seed}")
        if verify(transformed, carried)[0]:
            real_transforms += 1
        else:
            g8_failures.append(f"carried witness failed at seed {seed}")
        # _permuted_and_inverted carries transformed['answer'], not `carried`;
        # install the already-carried witness only in this local test instance.
        transformed_for_second = dict(transformed)
        transformed_for_second["answer"] = carried
        transformed_twice, carried_twice = _permuted_and_inverted(
            transformed_for_second, 40_000 + seed)
        if (canonical_key(transformed_twice) == key
                and verify(transformed_twice, carried_twice)[0]):
            composed += 1
        else:
            g8_failures.append(f"composed transform failed at seed {seed}")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance,
        "real_transformation_checks": real_transforms,
        "composed_transformation_checks": composed,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary row permutation with carried sign permutation",
            "independent inversion b_i -> -b_i with carried sign flip",
            "composition of both transformations",
        ],
        "failures": g8_failures,
    }

    compact_answer, route_operations = _compact_route(ship)
    compact_ok = compact_answer is not None and verify(ship, compact_answer)[0]
    blob = json.dumps(ship["answer"], separators=(",", ":"))
    # The planted mix varies by seed, so gate on the longest legal sign vector.
    worst_blob = json.dumps([1] + [-1] * (len(ship["answer"]) - 1),
                            separators=(",", ":"))
    answer_chars = max(len(blob), len(worst_blob))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _atom_count(ship["answer"])
    # Seed-independent upper bound for the same route: every residue may take
    # the negative branch and global sign normalization may touch every sign.
    principal_value = 4 * total_norm + discriminant
    route_operations_bound = (
        max(0, len(forms) - 1) + 2
        + 3 * (principal_value.bit_length().bit_length() + 1) + 1
        + 4 * len(forms)
    )
    arms = {
        name: dict(G9_MEASUREMENTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and route_operations_bound <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations_bound,
        "measured_instance_route_operations": route_operations,
        "compact_route_verifies": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
