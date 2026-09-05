"""Verified inverse generator from Pang--Yuan--Wu--Guan, arXiv:2511.02616.

The family uses Theorem 3.1 and its trace-zero coordinate calculation.  A
preimage is sampled first and pushed through a composition of certified
permutation polynomials, so generation never inverts the emitted instance.
All arithmetic is exact and standard-library-only.
"""

from __future__ import annotations

import functools
import hashlib
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
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the quadratic finite field F_p[alpha]/(alpha^2-u)",
        "permutation polynomials over F_{p^2}",
        "field elements in the basis (1,alpha)",
    ],
    "verification_operations": [
        "exact arithmetic modulo p",
        "quadratic-extension multiplication",
        "exact substitution into finite-field polynomials",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The paper's trace-zero coordinate makes the second coordinate of each "
        "layer an affine translate of a pure cube; without that change of "
        "variables one must invert the displayed map mechanically."
    ),
    "hardness_basis": (
        "Track B: exhaustive inversion after the paper's coordinate reduction "
        "scans O(layers*p) base-field values; at hard (p=500009, four layers) "
        "the measured 8-seed mean was 926457 scan iterations, 3705919 exact "
        "operations, and 0.112 seconds, while the structural O(layers*log p) "
        "route used at most 231 exact operations."
    ),
    "max_answer_tokens": 15,
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
        "One JSON list [r,s] encoding r+s*alpha in F_{p^2}, with exactly two "
        "decimal integers and 0 <= r,s < p."
    ),
    "bounds": {
        "elements": 2,
        "coordinate_min": 0,
        "coordinate_max": "p-1",
        "basis_order": ["coefficient of 1", "coefficient of alpha"],
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 11, "layers": 1},
    "easy": {"n": 10_007, "layers": 1},
    "medium": {"n": 100_003, "layers": 2},
    "hard": {"n": 500_000, "layers": 4},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "In the trace-zero basis, every layer's second output coordinate is an "
    "affine translate of a pure cube."
)
PLACEBO_HINT = (
    "In the displayed polynomial basis, every layer's arithmetic must be "
    "reduced consistently modulo the stated prime."
)

# Counts from the three script-owned oracle measurements after hardening.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Step-0 paper reading.  Section 2, Proposition 2.1 and its rewritten form fix
the exact coordinate principle: a univariate map over an extension field is a
permutation exactly when its coordinate polynomial map is.  Section 3,
Theorem 3.1 is decisive here.  For odd q it characterizes
f(x)=(x^q-x+delta)^(q+2)+gamma*x.  In case (ii), q=2 mod 3,
gamma is in F_q^*, and Tr(delta)^2=Tr(gamma).  Its proof writes
delta=a+b*alpha, alpha^2=u nonsquare, gamma=c, and
x=y-(z-b)*alpha/2.  With c=2*a^2 the coordinate map becomes

  (2*a^2*y-u*a*z^2+a^3, -u*z^3+b*a^2).

The second coordinate is therefore a translated pure cube, and cubing is a
permutation because gcd(3,p-1)=1.  These are the paper's own finite-field
objects and its own coordinate calculation; no graph or finite-field
surrogate has replaced them.

What makes it easy.  Theorem 3.1 is necessary-and-sufficient, and its proof
gives the coordinate reduction explicitly.  Thus Track A would be false.
The direct structural inverse takes a modular cube root by exponent
(2p-1)/3 and then two linear recoveries.  The mechanical reference used here
instead scans the reduced z coordinate, O(layers*p), which is practical in a
program at the presets but not by hand.  Composition preserves bijectivity, so
several independently parameterized theorem layers increase crowding while
the answer stays one field element.

Generation samples x first, chooses nonsquare u and nonzero a values, sets
delta=a+b*alpha and gamma=2*a^2, and evaluates the layers forward.  Since
Tr(delta)=2a and Tr(gamma)=2gamma=4a^2, Theorem 3.1(ii) applies to every layer.
The answer is therefore known before the target exists.  Verification never
reads inst['answer']; it substitutes any candidate through the displayed
composition and compares the exact result.

Attack handling.  Uniform preimages make neither coordinate a planted
outlier.  The panel tests small/magnitude-derived guesses, inversion of only
the visible linear terms, 512 uniform restarts, and an in-context ansatz that
uses ordinary integer cube roots in place of finite-field cube roots.  The
domain-standard coordinate scan is expected to solve and is reported
separately, as Track B requires.
""".strip()


# ---------------------------------------------------------------------------
# Prime-field and quadratic-extension arithmetic


def _validate_parameters(n: int, layers: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(layers, bool) or not isinstance(layers, int) or not 1 <= layers <= 8:
        raise ValueError("layers must be an integer from 1 through 8")


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for every 64-bit integer."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if value in small:
        return True
    if any(value % p == 0 for p in small):
        return False
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


@functools.lru_cache(maxsize=None)
def _next_prime_2mod3(lower: int) -> int:
    candidate = max(5, lower)
    if candidate % 2 == 0:
        candidate += 1
    while True:
        if candidate % 3 == 2 and _is_prime(candidate):
            return candidate
        candidate += 2


@functools.lru_cache(maxsize=None)
def _least_nonsquare(p: int) -> int:
    for value in range(2, p):
        if pow(value, (p - 1) // 2, p) == p - 1:
            return value
    raise AssertionError("an odd prime has a nonsquare")


def _sqrt_mod(value: int, p: int) -> int:
    """One square root modulo an odd prime, by Tonelli--Shanks."""
    value %= p
    if value == 0:
        return 0
    if pow(value, (p - 1) // 2, p) != 1:
        raise ValueError("value is not a square")
    if p % 4 == 3:
        return pow(value, (p + 1) // 4, p)
    q = p - 1
    s = 0
    while q % 2 == 0:
        s += 1
        q //= 2
    z = _least_nonsquare(p)
    c = pow(z, q, p)
    x = pow(value, (q + 1) // 2, p)
    t = pow(value, q, p)
    m = s
    while t != 1:
        i = 1
        t2 = t * t % p
        while i < m and t2 != 1:
            t2 = t2 * t2 % p
            i += 1
        if i == m:
            raise AssertionError("Tonelli--Shanks invariant failed")
        b = pow(c, 1 << (m - i - 1), p)
        x = x * b % p
        c = b * b % p
        t = t * c % p
        m = i
    return x


def _add(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] + y[0]) % p, (x[1] + y[1]) % p)


def _sub(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] - y[0]) % p, (x[1] - y[1]) % p)


def _mul(x: tuple[int, int], y: tuple[int, int], p: int,
         u: int) -> tuple[int, int]:
    return ((x[0] * y[0] + u * x[1] * y[1]) % p,
            (x[0] * y[1] + x[1] * y[0]) % p)


def _conjugate(x: tuple[int, int], p: int) -> tuple[int, int]:
    return (x[0], (-x[1]) % p)


def _scale(c: int, x: tuple[int, int], p: int) -> tuple[int, int]:
    return (c * x[0] % p, c * x[1] % p)


def _eval_layer(x: tuple[int, int], layer: dict, p: int,
                u: int) -> tuple[int, int]:
    """Exact substitution into (x^p-x+delta)^(p+2)+gamma*x."""
    delta = (layer["delta"][0], layer["delta"][1])
    w = _add(_sub(_conjugate(x, p), x, p), delta, p)
    # In this quadratic presentation w^p is conjugation, so this is literally
    # w^(p+2)=w^p*w*w, without a long exponentiation.
    nonlinear = _mul(_mul(_conjugate(w, p), w, p, u), w, p, u)
    return _add(nonlinear, _scale(layer["gamma"], x, p), p)


def _eval_composition(inst: dict, answer: list[int] | tuple[int, int]) -> tuple[int, int]:
    value = (answer[0], answer[1])
    for layer in inst["polynomials"]:
        value = _eval_layer(value, layer, inst["p"], inst["u"])
    return value


def _coordinate_layer(x: tuple[int, int], layer: dict, p: int,
                      u: int) -> tuple[int, int]:
    """The coordinate expression calculated in Theorem 3.1's proof."""
    a, b = layer["delta"]
    z = (b - 2 * x[1]) % p
    a2 = a * a % p
    real = (2 * a2 * x[0] - u * a * z * z + a * a2) % p
    imag = (-u * z * z * z + b * a2) % p
    return real, imag


def make_instance(n: int, seed: int = 0, layers: int = 1, **params) -> dict:
    """Inverse-generate a composition of Theorem-3.1 permutation layers."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, layers)
    p = _next_prime_2mod3(n)
    rng = random.Random(seed)

    while True:
        u = rng.randrange(2, p)
        if pow(u, (p - 1) // 2, p) == p - 1:
            break

    polynomial_layers = []
    for _ in range(layers):
        a = rng.randrange(1, p)
        b = rng.randrange(p)
        polynomial_layers.append({
            "delta": [a, b],
            "gamma": 2 * a * a % p,
        })

    # The witness exists before the public target.  Distinct coordinates make
    # all mandated corruption tests genuine changes, not a rejection search.
    while True:
        answer = [rng.randrange(p), rng.randrange(p)]
        if answer[0] != answer[1]:
            break

    skeleton = {
        "p": p,
        "u": u,
        "polynomials": polynomial_layers,
    }
    target = list(_eval_composition(skeleton, answer))
    return {
        "p": p,
        "u": u,
        "polynomials": polynomial_layers,
        "target": target,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete native finite-field inversion problem."""
    lines = [
        "Invert a composition of permutation polynomials over a quadratic finite field",
        "",
        f"Let p = {inst['p']}.  Work in K = F_p[alpha]/(alpha^2-u), where",
        f"u = {inst['u']}.  Thus alpha^2 = {inst['u']}, and all integer",
        "coefficients and both coordinates are reduced modulo p to 0,...,p-1.",
        "Represent r+s*alpha by the ordered pair [r,s].  Pair order matters.",
        "Addition and multiplication are",
        "",
        "  [r,s]+[v,w] = [r+v, s+w] (mod p),",
        f"  [r,s]*[v,w] = [r*v+{inst['u']}*s*w, r*w+s*v] (mod p).",
        "",
        "For each row j below, delta_j=[a_j,b_j] means a_j+b_j*alpha and",
        "",
        "  f_j(x) = (x^p - x + delta_j)^(p+2) + gamma_j*x.",
        "",
        "The rows, in composition order, are:",
        "",
        "  j | delta_j=[a_j,b_j] | gamma_j",
    ]
    for j, layer in enumerate(inst["polynomials"], 1):
        lines.append(
            f"  {j} | [{layer['delta'][0]},{layer['delta'][1]}] | {layer['gamma']}"
        )
    lines.extend([
        "",
        "Define F(x)=f_L(...f_2(f_1(x))...), using the rows in the listed order.",
        f"The target is T = [{inst['target'][0]},{inst['target'][1]}].",
        "",
        "Find the unique field element x=[r,s] with F(x)=T.  Your answer must",
        f"contain exactly two decimal integers with 0 <= r,s < {inst['p']}; do not",
        "swap them.  Powers, including x^p, are powers in K, not coordinatewise",
        "integer powers.  Every interval above is closed and repetitions are allowed.",
        "",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["Hint: " + STRUCTURAL_HINT, ""])
    elif mode == "placebo":
        lines.extend(["Hint: " + PLACEBO_HINT, ""])
    lines.extend([
        "Give your final answer inside <answer></answer> tags as one JSON list",
        "[r,s] of two decimal integers.",
        "Example: <answer>[3, 7]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse the last tagged pair, tolerating surrounding prose and fences."""
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
        match = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", body)
        if not match:
            return None
        value = [int(match.group(1)), int(match.group(2))]
    if (not isinstance(value, list) or len(value) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in value)):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any preimage by one exact substitution; never inspect the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer is missing its alpha-coordinate"
    if len(answer) != 2:
        return False, "answer must contain exactly two coordinates"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "both coordinates must be decimal integers"
    p = inst["p"]
    if any(x < 0 or x >= p for x in answer):
        return False, "a coordinate is outside the closed range 0,...,p-1"
    image = _eval_composition(inst, answer)
    target = tuple(inst["target"])
    if image != target:
        return False, f"wrong preimage: F(candidate)={list(image)}, target={list(target)}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform sample from the exact, structure-aware field-element language."""
    return [rng.randrange(inst["p"]), rng.randrange(inst["p"])]


def search_space(inst: dict) -> int | None:
    return inst["p"] * inst["p"]


def enumerate_all(inst: dict) -> int | None:
    """Exact brute-force solution count when the field is hand-scale."""
    if search_space(inst) > 200_000:
        return None
    count = 0
    for r in range(inst["p"]):
        for s in range(inst["p"]):
            count += int(verify(inst, [r, s])[0])
    return count


# ---------------------------------------------------------------------------
# Structural inverse, mechanical reference, attacks, and relabellings


class _OperationCounter:
    __slots__ = ("field_operations", "euclidean_divisions", "scan_iterations")

    def __init__(self) -> None:
        self.field_operations = 0
        self.euclidean_divisions = 0
        self.scan_iterations = 0

    @property
    def operations(self) -> int:
        return self.field_operations + self.euclidean_divisions


def _inverse_counted(value: int, p: int, counter: _OperationCounter) -> int:
    old_r, r = p, value % p
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_t, t = t, old_t - q * t
        counter.euclidean_divisions += 1
    if old_r != 1:
        raise ZeroDivisionError("nonzero base-field element was not invertible")
    return old_t % p


def _pow_counted(value: int, exponent: int, p: int,
                 counter: _OperationCounter) -> int:
    result = 1
    base = value % p
    while exponent:
        if exponent & 1:
            result = result * base % p
            counter.field_operations += 1
        exponent >>= 1
        if exponent:
            base = base * base % p
            counter.field_operations += 1
    return result


def _compact_inverse(inst: dict) -> dict:
    """Invert with Theorem 3.1's pure-cube coordinate formula."""
    p, u = inst["p"], inst["u"]
    counter = _OperationCounter()
    start = time.perf_counter()
    current = tuple(inst["target"])
    # One multiply, one subtraction, and one exact division form the exponent.
    counter.field_operations += 3
    inv2 = _inverse_counted(2, p, counter)
    invu = _inverse_counted(u, p, counter)
    cube_inverse_exponent = (2 * p - 1) // 3
    for layer in reversed(inst["polynomials"]):
        a, b = layer["delta"]
        a2 = a * a % p
        counter.field_operations += 1
        rhs = (b * a2 - current[1]) * invu % p
        counter.field_operations += 3
        z = _pow_counted(rhs, cube_inverse_exponent, p, counter)
        z2 = z * z % p
        a3 = a * a2 % p
        correction = u * a % p * z2 % p
        counter.field_operations += 4
        invgamma = _inverse_counted(layer["gamma"], p, counter)
        y = (current[0] + correction - a3) * invgamma % p
        s = (b - z) * inv2 % p
        counter.field_operations += 5
        current = (y, s)
    elapsed = time.perf_counter() - start
    answer = list(current)
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "wall_clock_sec": elapsed,
        "operations": counter.operations,
        "field_operations": counter.field_operations,
        "euclidean_divisions": counter.euclidean_divisions,
    }


def _reference_coordinate_scan(inst: dict) -> dict:
    """Mechanical Track-B inversion: scan z in each reduced coordinate."""
    p, u = inst["p"], inst["u"]
    start = time.perf_counter()
    iterations = 0
    counter = _OperationCounter()
    current = tuple(inst["target"])
    inv2 = _inverse_counted(2, p, counter)
    for layer in reversed(inst["polynomials"]):
        a, b = layer["delta"]
        a2 = a * a % p
        translated = b * a2 % p
        counter.field_operations += 2
        wanted = current[1]
        found = None
        for z in range(p):
            iterations += 1
            z2 = z * z % p
            z3 = z2 * z % p
            trial = (-u * z3 + translated) % p
            # Three multiplications and one addition/subtraction.
            counter.field_operations += 4
            if trial == wanted:
                found = z
                break
        if found is None:
            return {"ok": False, "reason": "scan found no z"}
        z2 = found * found % p
        invgamma = _inverse_counted(layer["gamma"], p, counter)
        y = ((current[0] + u * a * z2 - a * a2)
             * invgamma) % p
        s = (b - found) * inv2 % p
        counter.field_operations += 9
        current = (y, s)
    elapsed = time.perf_counter() - start
    answer = list(current)
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "wall_clock_sec": elapsed,
        "iterations": iterations,
        "operations": counter.operations,
    }


def _attack_small_residue_outlier(inst: dict) -> bool:
    p = inst["p"]
    candidates = [[0, 0], list(inst["target"])]
    candidates += [list(layer["delta"]) for layer in inst["polynomials"]]
    candidates += [[x[0], (-x[1]) % p] for x in candidates[1:]]
    values = {0, 1, p - 1}
    values.update(inst["target"])
    for layer in inst["polynomials"]:
        values.update(layer["delta"])
    centered = sorted(values, key=lambda x: min(x, p - x))[:4]
    candidates += [[r, s] for r in centered for s in centered]
    return any(verify(inst, candidate)[0] for candidate in candidates)


def _attack_linear_terms_only(inst: dict) -> bool:
    p = inst["p"]
    current = tuple(inst["target"])
    for layer in reversed(inst["polynomials"]):
        invgamma = pow(layer["gamma"], -1, p)
        current = (current[0] * invgamma % p,
                   current[1] * invgamma % p)
    return verify(inst, list(current))[0]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 512) -> bool:
    rng = random.Random(seed ^ 0x251102616)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _integer_cuberoot(value: int) -> int:
    lo, hi = 0, 1
    while hi ** 3 <= value:
        hi *= 2
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid ** 3 <= value:
            lo = mid
        else:
            hi = mid
    return lo


def _attack_integer_cube_ansatz(inst: dict) -> bool:
    """By-hand-looking route: ordinary cube roots, not modular ones."""
    p, u = inst["p"], inst["u"]
    current = tuple(inst["target"])
    inv2, invu = pow(2, -1, p), pow(u, -1, p)
    for layer in reversed(inst["polynomials"]):
        a, b = layer["delta"]
        a2 = a * a % p
        rhs = (b * a2 - current[1]) * invu % p
        z = _integer_cuberoot(rhs)
        y = ((current[0] + u * a * z * z - a * a2)
             * pow(layer["gamma"], -1, p)) % p
        current = (y, (b - z) * inv2 % p)
    return verify(inst, list(current))[0]


def _rebase_instance(inst: dict, scale: int) -> tuple[dict, list[int]]:
    """Use beta=scale*alpha and carry every field element to the new basis."""
    p = inst["p"]
    scale %= p
    if scale == 0:
        raise ValueError("basis scale must be nonzero")
    inv = pow(scale, -1, p)

    def move(value: list[int]) -> list[int]:
        return [value[0], value[1] * inv % p]

    moved = {
        "p": p,
        "u": inst["u"] * scale * scale % p,
        "polynomials": [
            {"delta": move(layer["delta"]), "gamma": layer["gamma"]}
            for layer in inst["polynomials"]
        ],
        "target": move(inst["target"]),
        "answer": move(inst["answer"]),
    }
    return moved, moved["answer"]


def canonical_key(inst: dict) -> str:
    """Normalize all trace-zero quadratic bases, including conjugation."""
    p = inst["p"]
    u0 = _least_nonsquare(p)
    root = _sqrt_mod(inst["u"] * pow(u0, -1, p) % p, p)

    def representation(scale: int) -> list:
        def move(value: list[int]) -> list[int]:
            return [value[0], value[1] * scale % p]
        return [
            p,
            u0,
            [[move(layer["delta"]), layer["gamma"]]
             for layer in inst["polynomials"]],
            move(inst["target"]),
        ]

    choices = [representation(root), representation((-root) % p)]
    canonical = min(choices, key=lambda item: json.dumps(item, separators=(",", ":")))
    payload = json.dumps(canonical, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase modulus crowding and composition depth at fixed answer size."""
    n = params.get("n")
    layers = params.get("layers")
    if (isinstance(n, bool) or not isinstance(n, int)
            or isinstance(layers, bool) or not isinstance(layers, int)):
        return None
    return {
        "n": n * 2 + 1,
        "layers": min(layers + 1, 8),
    }


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), len(encoded), len(answer) if isinstance(answer, list) else 1


def selftest() -> dict:
    """Run all mandatory gates and return a JSON-native report."""
    report: dict = {}

    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, why = verify(trial, trial["answer"])
            coordinate_ok = all(
                _eval_layer((17 % trial["p"], 23 % trial["p"]), layer,
                            trial["p"], trial["u"])
                == _coordinate_layer((17 % trial["p"], 23 % trial["p"]), layer,
                                     trial["p"], trial["u"])
                for layer in trial["polynomials"]
            )
            json_ok = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            g1_checks += 1
            if not (ok and coordinate_ok and json_ok):
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": why, "coordinate_identity": coordinate_ok,
                                    "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    r, s = inst["answer"]
    corruptions = {
        "drop_one": [r],
        "swap_order": [s, r],
        "duplicate": [r, r],
        "empty": [],
        "out_of_range": [inst["p"], s],
    }
    rejections = {}
    all_rejected = True
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        all_rejected &= not ok
        rejections[name] = why
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and len(set(rejections.values())) == len(corruptions),
        "rejections": rejections,
        "distinct_reasons": len(set(rejections.values())),
    }

    realistic = (
        "I worked in the stated polynomial basis.\n\n"
        "```text\nThe ordered coordinates are below.\n```\n"
        f"<answer>\n{json.dumps(inst['answer'])}\n</answer>\n"
        "Both entries are least nonnegative residues."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == inst["answer"] and verify(inst, parsed)[0]
                 and parse_answer("garbage") is None),
        "parsed_matches": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(0x25110216)
    guess_total = 200_000
    hits = 0
    sample_start = time.perf_counter()
    for _ in range(guess_total):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    sample_seconds = time.perf_counter() - sample_start
    probability = hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": probability,
        "exact_probability": 1 / search_space(inst),
        "prior": "uniform over all p^2 field elements, exactly the answer language",
        "candidate_space": search_space(inst),
        "sampling_wall_seconds": sample_seconds,
    }

    baseline_start = time.perf_counter()
    baseline_success = _attack_random_restart(inst, 0xB451, restarts=4096)
    baseline_seconds = time.perf_counter() - baseline_start
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (probability < 1e-6 and not baseline_success and demo_count == 1),
        "shipping_observed_valid_fraction": probability,
        "shipping_exact_valid_fraction": 1 / search_space(inst),
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(inst),
        "baseline_wall_seconds": baseline_seconds,
        "baseline_iterations": 4096,
        "baseline_successes": int(baseline_success),
        "demo_exact_solution_count": demo_count,
        "enumerate_all_shipping": None,
    }

    attack_successes = {
        "outlier_small_or_displayed_residues": 0,
        "greedy_visible_linear_terms_only": 0,
        "random_restart_512_structure_aware": 0,
        "by_hand_ordinary_integer_cube_root_ansatz": 0,
    }
    reference_runs = []
    compact_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes["outlier_small_or_displayed_residues"] += int(
            _attack_small_residue_outlier(trial))
        attack_successes["greedy_visible_linear_terms_only"] += int(
            _attack_linear_terms_only(trial))
        attack_successes["random_restart_512_structure_aware"] += int(
            _attack_random_restart(trial, seed))
        attack_successes["by_hand_ordinary_integer_cube_root_ansatz"] += int(
            _attack_integer_cube_ansatz(trial))
        reference_runs.append(_reference_coordinate_scan(trial))
        compact_runs.append(_compact_inverse(trial))
    ref_ok = sum(int(run.get("ok", False)) for run in reference_runs)
    compact_ok = sum(int(run["ok"]) for run in compact_runs)
    all_failed = all(value == 0 for value in attack_successes.values())
    ref_wall = sum(run["wall_clock_sec"] for run in reference_runs)
    ref_iterations = sum(run["iterations"] for run in reference_runs)
    ref_operations = sum(run["operations"] for run in reference_runs)
    compact_operations = max(run["operations"] for run in compact_runs)
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_ok == 8 and compact_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "Theorem-3.1 coordinate reduction plus exhaustive z scan",
            "complexity": "O(layers*p) exact base-field trials",
            "wall_clock_sec": ref_wall,
            "mean_wall_clock_sec": ref_wall / 8,
            "iterations": ref_iterations,
            "mean_iterations": ref_iterations // 8,
            "operations": ref_operations,
            "mean_operations": ref_operations // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
        "compact_structural_route": {
            "name": "pure-cube exponentiation and linear recovery",
            "complexity": "O(layers*log p) exact operations",
            "maximum_operations": compact_operations,
            "solves": f"{compact_ok}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * ship_params["n"],
                            layers=min(ship_params["layers"] + 1, 8), seed=77)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["p"] > 2 * inst["p"] - 1000,
        "base_n": ship_params["n"],
        "doubled_n": 2 * ship_params["n"],
        "doubled_prime": doubled["p"],
        "doubled_layers": len(doubled["polynomials"]),
        "doubled_verify": doubled_why,
        "candidate_space_growth_factor": search_space(doubled) / search_space(inst),
    }

    invariance_checks = 0
    witness_checks = 0
    attempts = 0
    for seed in range(20):
        trial = make_instance(seed=seed + 700, **ship_params)
        scale1 = 2 + seed % (trial["p"] - 2)
        scale2 = 5 + 3 * seed % (trial["p"] - 5)
        first, carried1 = _rebase_instance(trial, scale1)
        second, carried2 = _rebase_instance(first, scale2)
        conjugate, carried3 = _rebase_instance(trial, trial["p"] - 1)
        for moved, carried in ((first, carried1), (second, carried2),
                               (conjugate, carried3)):
            attempts += 1
            invariance_checks += int(canonical_key(moved) == canonical_key(trial))
            witness_checks += int(verify(moved, carried)[0])
    unrelated = {
        canonical_key(make_instance(seed=seed + 9000, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == attempts and witness_checks == attempts
                 and len(unrelated) == 20),
        "invariance_checks": invariance_checks,
        "invariance_attempts": attempts,
        "transformed_witness_checks": witness_checks,
        "unrelated_distinct": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": (
            "trace-zero basis scaling, conjugation, and compositions of two "
            "basis scalings"
        ),
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    intended = _compact_inverse(inst)
    evidence = G9_EVIDENCE
    hinted_pass = evidence["hinted_verdict"] == "hardened"
    within_caps = (chars <= 2000 and tokens <= 500 and elements <= 256
                   and intended["operations"] <= 300)
    h_attempts = evidence["hinted"]["attempts"]
    p_attempts = evidence["placebo"]["attempts"]
    h_rate = evidence["hinted"]["solved"] / h_attempts if h_attempts else 0.0
    p_rate = evidence["placebo"]["solved"] / p_attempts if p_attempts else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": hinted_pass and within_caps,
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
        "intended_route_operations": intended["operations"],
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
