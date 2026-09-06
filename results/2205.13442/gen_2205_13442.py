"""Problem generator for arXiv:2205.13442 -- Lang & Rouse,
"Rational points on x^3 + x^2 y^2 + y^3 = k".

The paper studies the genus-3 plane quartic

    C_k : x^3 z + x^2 y^2 + y^3 z = k z^4

and, in Section 3, records the reason its Jacobian splits: the affine equation is
symmetric in x and y, so with

    s = x + y,      t = x y          =>      t^2 - 3 s t + s^3 = k,

which with (X, Y) = (-s, t) is the elliptic curve E_{1,k} : Y^2 + 3XY = X^3 + k.
That is the paper's degree-2 morphism phi_1(x : y : z) = (-xz - yz : xy : z^2).

An instance publishes a short list of integers k_0, ..., k_{m-1} and asserts that
at least one of them is of the form x^3 + x^2 y^2 + y^3 with |x|, |y| <= B.  The
answer is the index together with the pair.  Instances are built answer-first:
the pair is sampled, k is evaluated, decoys are manufactured to be points of
E_{1,k_j}(Q) whose fibre under the degree-2 map phi_1 is irrational.

The module is standard-library only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from fractions import Fraction
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the plane quartic C_k : x^3 + x^2 y^2 + y^3 = k",
        "integral points on C_k",
        "the elliptic curve E_{1,k} : Y^2 + 3XY = X^3 + k and the degree-2 map phi_1",
    ],
    "verification_operations": [
        "exact integer evaluation of x^3 + x^2 y^2 + y^3",
        "exact integer equality against the published k_j",
        "integer magnitude comparison against the published bound B",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The equation is symmetric in x and y, so s = x + y and t = xy satisfy "
        "t^2 - 3 s t + s^3 = k (the paper's phi_1 onto E_{1,k}); since k is close "
        "to a perfect square, |t| is pinned to within O(|s|) of sqrt(k) and the "
        "two-dimensional search over (x, y) collapses to a one-dimensional scan "
        "over the small quantity s.  A solver who does not see this must scan x "
        "over the whole interval [-B, B]."
    ),
    "hardness_basis": (
        "Track B.  An efficient algorithm exists and is the paper's own: apply "
        "phi_1, scan s = x + y upward, and for each s test whether "
        "9 s^2 - 4 s^3 + 4 k is a perfect square and then whether s^2 - 4t is.  "
        "Its cost is O(S) big-integer square roots per listed k, i.e. a few "
        "hundred operations at the shipping preset (measured: see README).  The "
        "mechanical route -- solve the cubic in y for every integer x in [-B, B], "
        "the standard way to hunt integral points on a plane quartic -- costs "
        "Theta(m * B) cubic solves, measured at 6.4e10 operations at the 'hard' "
        "preset (1.27e6 s extrapolated in CPython, ~15 CPU-days; 8.0e9 operations "
        "after a mod-30030 congruence sieve).  Neither route is executable "
        "in context by brute force; only the compact one is, and only if the "
        "substitution is found."
    ),
    "max_answer_tokens": 40,
}

NATIVE = {
    "domain": "number_theory",
    "core": "other",
    "objects": [
        "the plane quartic C_k : x^3 + x^2 y^2 + y^3 = k",
        "integral points on C_k",
        "the elliptic curve E_{1,k} : Y^2 + 3XY = X^3 + k and the degree-2 map phi_1",
    ],
    "intuition": (
        "change of variables: "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": None,
}


DIFFICULTY = {
    # Small enough to be finished with pencil and paper: the mechanical scan is
    # about a hundred cubic solves and the compact scan is five square tests.
    "demo": {
        "height": 12,
        "spread": (2, 6),
        "n_ks": 2,
        "near_miss_frac": 1.0,
        "slack": 4,
    },
    "easy": {
        "height": 3_000,
        "spread": (6, 40),
        "n_ks": 4,
        "near_miss_frac": 0.5,
        "slack": 4,
    },
    "medium": {
        "height": 200_000,
        "spread": (15, 90),
        "n_ks": 6,
        "near_miss_frac": 0.7,
        "slack": 4,
    },
    "hard": {
        "height": 1_000_000_000,
        "spread": (40, 220),
        "n_ks": 8,
        "near_miss_frac": 1.0,
        "slack": 4,
    },
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The equation is symmetric, so s = x + y and t = xy satisfy "
    "t^2 - 3 s t + s^3 = k, and in these instances |s| is far smaller than |x|."
)

PLACEBO_HINT = (
    "The equation mixes odd and even degrees, so keeping careful track of the "
    "sign of each term is worth the effort on these instances."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A triple [j, x, y] of integers: j is a 0-based index into the published "
        "list of m values, and x, y are integers with |x|, |y| <= B."
    ),
    "bounds": {"index_range": "m", "coordinate_bound": "B", "n_elements": 3},
}

NOTES = r"""
Source of the construction.  Lang--Rouse, Section 3, first paragraph: "the affine
equation for C_k is symmetric in x and y.  So letting s = x + y and t = xy, the
equation of C_k becomes s^3 - 3 s t + t^2 = k.  Setting X = -s and Y = t the
equation becomes Y^2 + 3 X Y = X^3 + k and the map (x, y) -> (s, t) is a degree 2
map."  The same map appears in the introduction as
phi_1(x : y : z) = (-xz - yz : xy : z^2) onto E_{1,k} : y^2 + 3xy = x^3 + k.

Two consequences are used here.

(1) Generation is inverse and exact.  A pair (x, y) is sampled first and
    k = x^3 + x^2 y^2 + y^3 is evaluated.  Nothing is ever solved for.

(2) The map is degree 2, so a rational point of E_{1,k} lifts to C_k(Q) only when
    the fibre is rational, i.e. only when s^2 - 4t is a square.  The decoys are
    built to sit exactly in that gap: k_j is manufactured from an (s_j, t_j) with
    s_j^2 - 4 t_j a non-square, so a solver who runs only the elliptic half of the
    reduction gets a hit on every decoy and has to run the second square test to
    tell them apart.

Track B is declared, not Track A.  The compact route is an algorithm and it is a
fast one; the claim is only that its mechanical alternative is out of reach in
context and that the compact one has to be found.  Both numbers are measured in
the README.

Caveat recorded honestly: a solver who has the insight but cannot do the
arithmetic still faces roughly 2 * (spread_max - spread_min + 1) * m candidate
(s, j) pairs and must compute a 4th root of a 38-digit integer to place x; the
"insight-aware" guess probability at the hard preset is about 1 / 2900, which is
larger than the naive 1 / (m * (2B+1)^2).  Both numbers are reported.
"""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INT_RE = re.compile(r"[-+]?\d+")


# --------------------------------------------------------------------------
# exact integer helpers
# --------------------------------------------------------------------------


def _is_square(n: int) -> bool:
    if n < 0:
        return False
    r = math.isqrt(n)
    return r * r == n


def _exact_sqrt(n: int) -> int | None:
    if n < 0:
        return None
    r = math.isqrt(n)
    return r if r * r == n else None


def _icbrt(n: int) -> int:
    """Floor of the real cube root of n (exact, sign-aware)."""
    if n < 0:
        return -_icbrt_pos(-n) - (0 if _is_cube(-n) else 1)
    return _icbrt_pos(n)


def _is_cube(n: int) -> bool:
    r = _icbrt_pos(n)
    return r * r * r == n


def _icbrt_pos(n: int) -> int:
    if n < 2:
        return n
    r = 1 << ((n.bit_length() + 2) // 3)
    while True:
        nr = (2 * r + n // (r * r)) // 3
        if nr >= r:
            break
        r = nr
    while r * r * r > n:
        r -= 1
    while (r + 1) ** 3 <= n:
        r += 1
    return r


def curve_value(x: int, y: int) -> int:
    """x^3 + x^2 y^2 + y^3, exact integer arithmetic."""
    return x * x * x + x * x * y * y + y * y * y


def _cubic_int_roots(a2: int, a0: int, lo: int, hi: int) -> list[int]:
    """Integer roots of y^3 + a2*y^2 + a0 = 0 inside [lo, hi], exactly.

    The three monotone branches of y^3 + a2 y^2 + a0 are separated by the
    critical points 0 and -2*a2/3; a bisection on each branch is exact.
    """
    def g(y: int) -> int:
        return y * y * y + a2 * y * y + a0

    crit = sorted({0, -(2 * a2) // 3, -(2 * a2) // 3 - 1, -(2 * a2) // 3 + 1})
    marks = [lo] + [c for c in crit if lo < c < hi] + [hi]
    roots: set[int] = set()
    for i in range(len(marks) - 1):
        a, b = marks[i], marks[i + 1]
        ga, gb = g(a), g(b)
        if ga == 0:
            roots.add(a)
        if gb == 0:
            roots.add(b)
        if ga == 0 or gb == 0 or (ga > 0) == (gb > 0):
            continue
        # sign change on a monotone branch -> unique real root, bisect it
        while b - a > 1:
            mid = (a + b) // 2
            gm = g(mid)
            if gm == 0:
                roots.add(mid)
                break
            if (gm > 0) == (ga > 0):
                a, ga = mid, gm
            else:
                b, gb = mid, gm
    return sorted(r for r in roots if lo <= r <= hi and g(r) == 0)


# --------------------------------------------------------------------------
# the compact route (the paper's phi_1) -- used for decoy screening, for the
# reference algorithm, and by nothing that produces the planted answer
# --------------------------------------------------------------------------


def phi1_lift_scan(k: int, s_lo: int, s_hi: int) -> tuple[list[tuple[int, int]], int]:
    """Scan s = x + y over |s| in [s_lo, s_hi]; return integral points and op count.

    For each s the paper's substitution gives t^2 - 3 s t + s^3 = k, a quadratic
    in t with discriminant 9 s^2 - 4 s^3 + 4 k.  When that is a perfect square the
    point (X, Y) = (-s, t) lies on E_{1,k}; it lifts to C_k exactly when the fibre
    discriminant s^2 - 4 t is a perfect square as well.
    """
    found: list[tuple[int, int]] = []
    ops = 0
    for a in range(s_lo, s_hi + 1):
        for s in ({a, -a} if a else {0}):
            ops += 1
            disc = 9 * s * s - 4 * s * s * s + 4 * k
            w = _exact_sqrt(disc)
            if w is None:
                continue
            for num in (3 * s + w, 3 * s - w):
                if num % 2:
                    continue
                t = num // 2
                ops += 1
                d = _exact_sqrt(s * s - 4 * t)
                if d is None or (s + d) % 2:
                    continue
                x, y = (s + d) // 2, (s - d) // 2
                if curve_value(x, y) == k:
                    found.append((x, y))
                    found.append((y, x))
    return sorted(set(found)), ops


# --------------------------------------------------------------------------
# instance construction -- answer first, always
# --------------------------------------------------------------------------


def _params(**params) -> dict:
    p = dict(DIFFICULTY["medium"])
    p.update({k: v for k, v in params.items() if v is not None})
    if "n" in p and p["n"] is not None:
        # optional size knob: n is the decimal size of the coordinates
        p["height"] = 10 ** int(p["n"])
    p.pop("n", None)
    p["spread"] = tuple(p["spread"])
    return p


def make_instance(seed: int = 0, **params) -> dict:
    """Build an instance around a pair (x, y) that is sampled first.

    No search of any kind produces the answer: the coordinates are drawn, k is
    evaluated, and the decoys are evaluated from their own drawn (s, t).  The only
    search performed is a *rejection* test on the decoys.
    """
    p = _params(**params)
    height = int(p["height"])
    s_lo, s_hi = int(p["spread"][0]), int(p["spread"][1])
    m = int(p["n_ks"])
    near_frac = float(p["near_miss_frac"])
    slack = int(p["slack"])
    if s_hi > height:
        raise ValueError("spread must not exceed height")
    bound = slack * height

    rng = random.Random(hashlib.sha256(
        json.dumps([seed, sorted(p.items(), key=str)], default=str).encode()
    ).hexdigest())

    # ---- the answer, sampled before anything else exists -------------------
    x0 = rng.randrange(height, 3 * height + 1)
    s0 = rng.choice([1, -1]) * rng.randrange(s_lo, s_hi + 1)
    y0 = s0 - x0
    k_true = curve_value(x0, y0)
    assert abs(x0) <= bound and abs(y0) <= bound

    # ---- decoys, drawn from the SAME magnitude law as the plant ------------
    # A decoy starts life as a second, independent draw (u, s) of exactly the
    # distribution the plant came from, so k_j and k_true are identically
    # distributed in size.  It is then pushed off the curve in one of two ways:
    #   near-miss : t is nudged by a tiny delta, which leaves (X, Y) = (-s, t) a
    #               genuine integral point of E_{1,k_j} but makes the fibre
    #               discriminant s^2 - 4t a non-square, so phi_1 has no rational
    #               preimage.  The elliptic half of the reduction hits on it.
    #   plain     : k itself is nudged, which destroys the E_{1,k_j} point too.
    n_dec = m - 1
    n_near = int(round(near_frac * n_dec))
    screen_hi = max(4 * s_hi, 400)

    def draw_shadow():
        u = rng.randrange(height, 3 * height + 1)
        sj = rng.choice([1, -1]) * rng.randrange(s_lo, s_hi + 1)
        return u, sj, -u * (u - sj)          # t = x*y for the shadow pair

    ks = [k_true]
    seen = {k_true}
    guard = 0
    while len(ks) < m and guard < 20000:
        guard += 1
        u, sj, t = draw_shadow()
        if (len(ks) - 1) < n_near:
            delta = rng.choice([1, -1]) * rng.randrange(1, 51)
            t = t + delta
            if _is_square(sj * sj - 4 * t):          # cannot happen, but be exact
                continue
            kj = t * t - 3 * sj * t + sj ** 3
        else:
            eta = rng.choice([1, -1]) * rng.randrange(1, 1_000_001)
            kj = t * t - 3 * sj * t + sj ** 3 + eta
        if kj in seen or kj <= 0:
            continue
        # rejection screen -- this tests a decoy, it never produces the answer
        pts, _ = phi1_lift_scan(kj, 0, screen_hi)
        if any(abs(a) <= bound and abs(b) <= bound for a, b in pts):
            continue
        ks.append(kj)
        seen.add(kj)
    if len(ks) < m:
        raise RuntimeError("decoy generation failed to converge")

    order = list(range(m))
    rng.shuffle(order)
    shuffled = [ks[i] for i in order]
    j0 = order.index(0)

    return {
        "paper": "2205.13442",
        "ks": shuffled,
        "bound": bound,
        "params": p,
        "seed": seed,
        "answer": [j0, x0, y0],
    }


# --------------------------------------------------------------------------
# statement / parsing / verification
# --------------------------------------------------------------------------


def render(inst: dict) -> str:
    ks = inst["ks"]
    b = inst["bound"]
    lines = [
        "Consider the equation",
        "",
        "    x^3 + x^2*y^2 + y^3 = k",
        "",
        "in integers x, y (either sign is allowed; x and y need not be distinct).",
        "",
        f"Below are {len(ks)} integers k_0, ..., k_{len(ks) - 1}, indexed from 0.",
        "At least one of them can be written in the form above with integers x, y",
        f"satisfying |x| <= {b} and |y| <= {b}.",
        "",
    ]
    for i, k in enumerate(ks):
        lines.append(f"    k_{i} = {k}")
    lines += [
        "",
        "Find one index j for which such a representation exists, together with a",
        "pair (x, y) of integers that realises it:",
        "",
        f"    k_j = x^3 + x^2*y^2 + y^3,      |x| <= {b},   |y| <= {b}.",
        "",
        "Give your final answer inside <answer></answer> tags, as three integers",
        "separated by commas: the index j first, then x, then y.",
        "Example: <answer>1, -4, -2</answer>",
        "Output nothing else inside the tags.",
    ]
    text = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: Any) -> list[int] | None:
    """Recover [j, x, y] from raw solver output; None on anything malformed."""
    if isinstance(text, (list, tuple)):
        vals = list(text)
    elif isinstance(text, str):
        blocks = _ANSWER_RE.findall(text)
        chunk = blocks[-1] if blocks else text
        chunk = chunk.replace("−", "-").replace("$", " ").replace("\\", " ")
        chunk = chunk.replace("_", " ")
        vals = _INT_RE.findall(chunk)
        if len(vals) != 3 and blocks:
            return None
        if len(vals) < 3:
            return None
        vals = vals[:3]
    else:
        return None
    try:
        out = [int(v) for v in vals]
    except (TypeError, ValueError):
        return None
    if len(out) != 3:
        return None
    return out


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Exact check.  Accepts any valid witness; never consults inst['answer']."""
    if isinstance(answer, str):
        answer = parse_answer(answer)
    if answer is None:
        return False, "no answer parsed"
    if not isinstance(answer, (list, tuple)) or len(answer) != 3:
        return False, "answer must be exactly three integers [j, x, y]"
    try:
        j, x, y = (int(v) for v in answer)
    except (TypeError, ValueError):
        return False, "answer entries must be integers"
    for v, name in ((answer[0], "j"), (answer[1], "x"), (answer[2], "y")):
        if isinstance(v, float) and v != int(v):
            return False, f"{name} must be an integer"
    ks = inst["ks"]
    if not (0 <= j < len(ks)):
        return False, f"index j={j} outside 0..{len(ks) - 1}"
    b = inst["bound"]
    if abs(x) > b:
        return False, f"|x| = {abs(x)} exceeds the bound {b}"
    if abs(y) > b:
        return False, f"|y| = {abs(y)} exceeds the bound {b}"
    val = curve_value(x, y)
    if val != ks[j]:
        return False, f"x^3 + x^2 y^2 + y^3 = {val} != k_{j} = {ks[j]}"
    return True, "ok"


# --------------------------------------------------------------------------
# repo bookkeeping helpers
# --------------------------------------------------------------------------


def canonical_key(inst: dict) -> str:
    """Invariant under reordering of the published list (the family's relabelling)."""
    payload = json.dumps(
        {"ks": sorted(inst["ks"]), "bound": inst["bound"]}, sort_keys=True
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def search_space(inst: dict) -> int:
    return len(inst["ks"]) * (2 * inst["bound"] + 1) ** 2


def random_candidate(inst: dict, rng: random.Random) -> list[int]:
    """A candidate that already satisfies everything the statement gives for free:
    shape, index range, coordinate bound, and the mod-2 / mod-3 congruence that
    x^3 + x^2 y^2 + y^3 = k_j forces (both are free to a reader of the statement)."""
    ks = inst["ks"]
    b = inst["bound"]
    j = rng.randrange(len(ks))
    k = ks[j]
    ok2 = [(a, c) for a in range(2) for c in range(2)
           if (a * a * a + a * a * c * c + c * c * c - k) % 2 == 0]
    ok3 = [(a, c) for a in range(3) for c in range(3)
           if (a ** 3 + a * a * c * c + c ** 3 - k) % 3 == 0]
    r2 = rng.choice(ok2) if ok2 else (rng.randrange(2), rng.randrange(2))
    r3 = rng.choice(ok3) if ok3 else (rng.randrange(3), rng.randrange(3))
    def pick(t2: int, t3: int) -> int:
        # CRT to modulus 6, then a uniform representative inside [-b, b]
        r = next(v for v in range(6) if v % 2 == t2 and v % 3 == t3)
        lo = -b + ((r - (-b)) % 6)
        return lo + 6 * rng.randrange((b - lo) // 6 + 1)
    return [j, pick(r2[0], r3[0]), pick(r2[1], r3[1])]


def enumerate_all(inst: dict, budget: int = 400_000) -> int | None:
    """Exact count of valid [j, x, y] by brute force; None when out of budget."""
    ks = inst["ks"]
    b = inst["bound"]
    if len(ks) * (2 * b + 1) > budget:
        return None
    total = 0
    for j, k in enumerate(ks):
        for x in range(-b, b + 1):
            for y in _cubic_int_roots(x * x, x * x * x - k, -b, b):
                total += 1
    return total


# --------------------------------------------------------------------------
# ATTACKS
# --------------------------------------------------------------------------


def attack_bruteforce_scan(inst: dict, budget_ops: int = 400_000,
                           time_budget: float = 6.0) -> dict:
    """The mechanical route: for every integer x in [-B, B] solve the cubic in y.

    This is what a solver without the substitution has to do; it is also how one
    hunts integral points on a plane quartic when nothing else is known.  Run here
    with a budget so that its failure at the shipping preset is a measurement.
    """
    ks = inst["ks"]
    b = inst["bound"]
    t0 = time.perf_counter()
    ops = 0
    for x in range(-b, b + 1):
        x2, x3 = x * x, x * x * x
        for j, k in enumerate(ks):
            ops += 1
            for y in _cubic_int_roots(x2, x3 - k, -b, b):
                return {"solved": True, "ops": ops,
                        "seconds": time.perf_counter() - t0,
                        "answer": [j, x, y]}
        if ops >= budget_ops or time.perf_counter() - t0 > time_budget:
            return {"solved": False, "ops": ops,
                    "seconds": time.perf_counter() - t0,
                    "exhausted": False,
                    "total_ops_needed": len(ks) * (2 * b + 1)}
    return {"solved": False, "ops": ops, "seconds": time.perf_counter() - t0,
            "exhausted": True}


def mechanical_cost(inst: dict, sample: int = 4000) -> dict:
    """Measure the per-x cost of the mechanical scan and extrapolate to the whole
    interval.  Returns operation count and extrapolated wall-clock seconds."""
    ks = inst["ks"]
    b = inst["bound"]
    rng = random.Random(12345)
    xs = [rng.randrange(-b, b + 1) for _ in range(sample)]
    t0 = time.perf_counter()
    for x in xs:
        x2, x3 = x * x, x * x * x
        for k in ks:
            _cubic_int_roots(x2, x3 - k, -b, b)
    dt = time.perf_counter() - t0
    per_x = dt / sample
    total_ops = len(ks) * (2 * b + 1)
    return {
        "ops": total_ops,
        "seconds_per_x": per_x,
        "seconds_total": per_x * (2 * b + 1),
        "sample": sample,
    }


def attack_congruence_sieve(inst: dict, primes: tuple[int, ...] = (2, 3, 5, 7, 11, 13),
                            budget_ops: int = 400_000,
                            time_budget: float = 6.0) -> dict:
    """The number-theorist's speed-up of the mechanical scan.

    For each small prime p only those x mod p for which the cubic in y has a root
    mod p can occur.  Sieve x by the CRT of those classes and scan only survivors.
    Reports the achieved density (hence the speed-up) as well as success/failure.
    """
    ks = inst["ks"]
    b = inst["bound"]
    t0 = time.perf_counter()
    modulus = 1
    for p in primes:
        modulus *= p
    survivors_per_k: list[set[int]] = []
    for k in ks:
        allowed_by_p = {}
        for p in primes:
            ok = set()
            for a in range(p):
                for c in range(p):
                    if (a ** 3 + a * a * c * c + c ** 3 - k) % p == 0:
                        ok.add(a)
                        break
            allowed_by_p[p] = ok
        cur = {r for r in range(modulus)
               if all(r % p in allowed_by_p[p] for p in primes)}
        survivors_per_k.append(cur)
    density = sum(len(s) for s in survivors_per_k) / (len(ks) * modulus)
    ops = 0
    x = -b
    while x <= b:
        block = x % modulus
        for j, k in enumerate(ks):
            if block not in survivors_per_k[j]:
                continue
            ops += 1
            for y in _cubic_int_roots(x * x, x * x * x - k, -b, b):
                return {"solved": True, "ops": ops, "density": density,
                        "seconds": time.perf_counter() - t0}
        if ops >= budget_ops or time.perf_counter() - t0 > time_budget:
            break
        x += 1
    return {"solved": False, "ops": ops, "density": density,
            "speedup": (1.0 / density) if density else float("inf"),
            "seconds": time.perf_counter() - t0,
            "sieved_ops_needed": density * len(ks) * (2 * b + 1)}


# ---- exact LLL, used by the lattice attack --------------------------------


def _lll(basis: list[list[int]], delta: Fraction = Fraction(99, 100)) -> list[list[int]]:
    """Exact (Fraction) LLL.  Small dimensions only; used by the lattice attack."""
    b = [row[:] for row in basis]
    n = len(b)

    def gram_schmidt():
        bs: list[list[Fraction]] = []
        mu = [[Fraction(0)] * n for _ in range(n)]
        B: list[Fraction] = []
        for i in range(n):
            v = [Fraction(c) for c in b[i]]
            for j in range(i):
                if B[j] == 0:
                    continue
                mu[i][j] = sum(Fraction(b[i][t]) * bs[j][t]
                               for t in range(n)) / B[j]
                v = [v[t] - mu[i][j] * bs[j][t] for t in range(n)]
            bs.append(v)
            B.append(sum(x * x for x in v))
        return mu, B

    mu, B = gram_schmidt()
    k = 1
    guard = 0
    while k < n and guard < 3000:
        guard += 1
        for j in range(k - 1, -1, -1):
            if abs(mu[k][j]) > Fraction(1, 2):
                q = -((-mu[k][j] + Fraction(1, 2)).__floor__()) \
                    if mu[k][j] < 0 else (mu[k][j] + Fraction(1, 2)).__floor__()
                b[k] = [b[k][t] - q * b[j][t] for t in range(n)]
                mu, B = gram_schmidt()
        if B[k] >= (delta - mu[k][k - 1] ** 2) * B[k - 1]:
            k += 1
        else:
            b[k], b[k - 1] = b[k - 1], b[k]
            mu, B = gram_schmidt()
            k = max(1, k - 1)
    return b


def attack_lattice_coppersmith(inst: dict, which: int | None = None) -> dict:
    """Bivariate Coppersmith / Howgrave-Graham on f(x,y) = x^3+x^2y^2+y^3-k.

    Builds the standard shift lattice for f, x f, y f modulo N = k with the
    coordinates scaled by the bounds X = Y = B, LLL-reduces it exactly, and tests
    the Howgrave-Graham condition ||v||_1 < N.
    """
    ks = inst["ks"]
    b = inst["bound"]
    idx = 0 if which is None else which
    N = ks[idx]
    X = Y = b

    # f = x^3 + x^2 y^2 + y^3 - k, and the shifts x*f and y*f
    base = {(3, 0): 1, (2, 2): 1, (0, 3): 1, (0, 0): -N}
    polys = [{(a + i, c + j): v for (a, c), v in base.items()}
             for (i, j) in [(0, 0), (1, 0), (0, 1)]]
    monos = sorted({m for p in polys for m in p})
    leads = [max(p, key=lambda m: (m[0] + m[1], m[0])) for p in polys]
    rows = []
    for p in polys:
        rows.append([p.get(m, 0) * (X ** m[0]) * (Y ** m[1]) for m in monos])
    for m in monos:
        if m in leads:
            continue
        rows.append([(N if mm == m else 0) * (X ** mm[0]) * (Y ** mm[1])
                     for mm in monos])
    t0 = time.perf_counter()
    red = _lll(rows)
    dt = time.perf_counter() - t0
    l1 = min(sum(abs(c) for c in r) for r in red if any(r))
    ok = l1 < N
    return {
        "solved": False,
        "dimension": len(rows),
        "shortest_l1_norm": l1,
        "modulus": N,
        "howgrave_graham_satisfied": bool(ok),
        "single_monomial_XY_squared": X * X * Y * Y,
        "XY2_over_N": (X * X * Y * Y) / N,
        "seconds": dt,
        "note": ("Howgrave-Graham needs a reduced vector with ||v||_1 < N.  The "
                 "cross-term monomial of f alone contributes X^2 Y^2 = B^4, and the "
                 "planted root sits at |x| ~ k^(1/4), i.e. exactly at B^4 ~ N.  The "
                 "small-root condition is therefore violated before reduction "
                 "starts, and LLL returns nothing shorter than the trivial row N."),
    }


def attack_in_context_heuristics(inst: dict) -> dict:
    """What a model with no sandbox can actually try: tiny exhaustive search, the
    obvious degenerate families, and the two obvious magnitude guesses (x ~ k^(1/3),
    x ~ k^(1/4) with y = -x) with a small window around each."""
    ks = inst["ks"]
    b = inst["bound"]
    ops = 0
    t0 = time.perf_counter()
    for j, k in enumerate(ks):
        for x in range(-200, 201):
            for y in range(-200, 201):
                ops += 1
                if abs(x) <= b and abs(y) <= b and curve_value(x, y) == k:
                    return {"solved": True, "ops": ops, "answer": [j, x, y],
                            "seconds": time.perf_counter() - t0}
        c = _icbrt(k)
        q = math.isqrt(math.isqrt(k)) if k > 0 else 0
        cands = []
        for d in range(-3, 4):
            cands += [(c + d, 0), (c + d, 1), (c + d, -1), (c + d, 2), (c + d, -2)]
            for e in range(-3, 4):
                cands.append((q + d, -(q + d) + e))
        for x, y in cands:
            ops += 1
            if abs(x) <= b and abs(y) <= b and curve_value(x, y) == k:
                return {"solved": True, "ops": ops, "answer": [j, x, y],
                        "seconds": time.perf_counter() - t0}
    return {"solved": False, "ops": ops, "seconds": time.perf_counter() - t0}


def attack_outlier_statistics(inst: dict) -> dict:
    """Can the planted index be picked out by a per-k statistic, without solving?

    Five statistics are ranked: magnitude, distance to the nearest perfect square,
    distance to the nearest perfect 4th power, k mod 2520, and bit length.  Reports
    for each whether it ranks the planted list entry first.  This never produces a
    point, so it is reported as a diagnostic, not as a solving attack.
    """
    ks = inst["ks"]
    def near_sq(k):
        r = math.isqrt(k)
        return min(k - r * r, (r + 1) ** 2 - k)
    def near_4th(k):
        r = math.isqrt(math.isqrt(k))
        return min(k - r ** 4, (r + 1) ** 4 - k)
    stats = {
        "magnitude": [k for k in ks],
        "dist_to_square": [near_sq(k) for k in ks],
        "dist_to_4th_power": [near_4th(k) for k in ks],
        "k_mod_2520": [k % 2520 for k in ks],
        "bit_length": [k.bit_length() for k in ks],
    }
    out = {}
    for nm, vals in stats.items():
        order = sorted(range(len(ks)), key=lambda i: vals[i])
        out[nm] = {"argmin": order[0], "argmax": order[-1]}
    return out


def compact_route_cost(inst: dict) -> dict:
    """Cost of the compact route done well: scan |s| outward across every listed
    k at once and stop at the first lift.  This is the number a solver who has
    found phi_1 actually pays."""
    ks = inst["ks"]
    b = inst["bound"]
    ops = 0
    t0 = time.perf_counter()
    a = 0
    while a <= 4 * int(inst["params"]["spread"][1]) + 4:
        for j, k in enumerate(ks):
            pts, o = phi1_lift_scan(k, a, a)
            ops += o
            for x, y in pts:
                if abs(x) <= b and abs(y) <= b:
                    return {"solved": True, "ops": ops, "answer": [j, x, y],
                            "seconds": time.perf_counter() - t0,
                            "s_reached": a}
        a += 1
    return {"solved": False, "ops": ops, "seconds": time.perf_counter() - t0}


def reference_algorithm(inst: dict, s_cap: int | None = None) -> dict:
    """The compact route: the paper's phi_1, scanned over s = x + y."""
    ks = inst["ks"]
    b = inst["bound"]
    cap = s_cap if s_cap is not None else max(4 * int(inst["params"]["spread"][1]), 50)
    t0 = time.perf_counter()
    ops = 0
    for j, k in enumerate(ks):
        pts, o = phi1_lift_scan(k, 0, cap)
        ops += o
        for x, y in pts:
            if abs(x) <= b and abs(y) <= b:
                return {"solved": True, "ops": ops, "answer": [j, x, y],
                        "seconds": time.perf_counter() - t0, "s_cap": cap}
    return {"solved": False, "ops": ops, "seconds": time.perf_counter() - t0,
            "s_cap": cap}


# --------------------------------------------------------------------------
# escalation
# --------------------------------------------------------------------------


def escalate(params: dict) -> dict | str | None:
    """Harder parameters at FIXED answer length.

    The answer is always [j, x, y] with |x|, |y| <= 4 * height, so keeping
    `height` fixed keeps the serialised answer exactly as long as it was.  Three
    other knobs move:
      * spread      -- the range of |x + y| the plant is drawn from.  This is the
                       length of the compact route: a solver who has found phi_1
                       still has to scan s over the whole range.  The minimum also
                       moves up, which deletes the "guess a tiny s" shortcut.
      * n_ks        -- more published values, each of which must be screened.
      * near_miss_frac -- crowding: the fraction of decoys that are genuine points
                       of E_{1,k_j}(Q) whose phi_1-fibre is irrational, so the
                       elliptic half of the reduction hits on them and only the
                       second square test separates them from the real one.
    """
    p = dict(params)
    s_lo, s_hi = int(p["spread"][0]), int(p["spread"][1])
    height = int(p["height"])
    n_ks = int(p["n_ks"])

    new_lo, new_hi = s_lo * 2, s_hi * 2
    new_n = n_ks * 2
    new_frac = 1.0

    if new_hi > height:
        return "cap_bound"
    if new_n > 64:
        if s_hi * 2 <= height:
            new_n = n_ks
        else:
            return "cap_bound"
    if (new_lo, new_hi) == (s_lo, s_hi) and new_n == n_ks and \
            new_frac == float(p.get("near_miss_frac", 0.0)):
        return "cap_bound"

    p["spread"] = (new_lo, new_hi)
    p["n_ks"] = new_n
    p["near_miss_frac"] = new_frac
    return p


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------


def _perturbations(inst: dict, ans: list[int], rng: random.Random) -> list[Any]:
    """Corruptions that must all be rejected.

    Note that (y, x) is NOT here: x^3 + x^2 y^2 + y^3 is symmetric, so the swapped
    pair is a genuine second witness and verify() is required to accept it.
    """
    j, x, y = ans
    m = len(inst["ks"])
    b = inst["bound"]
    return [
        [j, x + 1, y],
        [j, x, y + 1],
        [j, x + 1, y + 1],
        [(j + 1) % m, x, y],
        [j, x],
        [],
        [j, b + 1, y],
        [j, x, -b - 1],
        [m, x, y],
        [j, "banana", y],
        None,
    ]


def selftest(seeds: int = 8, verbose: bool = False) -> dict:
    report: dict[str, Any] = {"track": TRACK}

    # G1 -----------------------------------------------------------------
    g1_ok = 0
    g1_tot = 0
    atoms_max = 0
    chars_max = 0
    for name in DIFFICULTY:
        for s in range(seeds):
            inst = make_instance(seed=s, **DIFFICULTY[name])
            ok, why = verify(inst, inst["answer"])
            g1_tot += 1
            g1_ok += 1 if ok else 0
            ser = json.dumps(inst["answer"])
            assert json.loads(ser) == inst["answer"]
            atoms_max = max(atoms_max, len(inst["answer"]))
            chars_max = max(chars_max, len(ser))
            if not ok and verbose:
                print(name, s, why)
    report["G1_planted_verifies"] = {"pass": g1_ok == g1_tot,
                                     "ok": g1_ok, "total": g1_tot}
    report["G9c_answer_size"] = {"max_atoms": atoms_max, "max_chars": chars_max,
                                 "pass": atoms_max <= 256 and chars_max <= 2000}

    # G2 -----------------------------------------------------------------
    rng = random.Random(7)
    inst = make_instance(seed=1, **DIFFICULTY["medium"])
    reasons = set()
    all_rejected = True
    for cand in _perturbations(inst, inst["answer"], rng):
        ok, why = verify(inst, cand)
        if ok:
            all_rejected = False
        reasons.add(why)
    report["G2_rejects_corruption"] = {"pass": all_rejected,
                                       "distinct_reasons": len(reasons)}

    # G3 -----------------------------------------------------------------
    j, x, y = inst["answer"]
    prose = (f"Let me substitute s = x+y.\nAfter some work I find x = {x}.\n"
             f"So the final result is\n\n<answer>{j}, {x}, {y}</answer>\n\nDone.")
    report["G3_round_trip"] = {
        "pass": parse_answer(prose) == inst["answer"]
                and parse_answer("nothing here") is None
                and parse_answer("<answer>oops</answer>") is None,
    }

    # G4 -----------------------------------------------------------------
    ship = make_instance(seed=2, **DIFFICULTY[SHIPPING_DIFFICULTY])
    rng = random.Random(11)
    hits = 0
    trials = 200_000
    for _ in range(trials):
        if verify(ship, random_candidate(ship, rng))[0]:
            hits += 1
    space = search_space(ship)
    report["G4_guess_resistance"] = {
        "hits": hits, "trials": trials,
        "analytic_p": 1.0 / space,
        "pass": hits == 0 and 1.0 / space < 1e-6,
    }

    # G5 -----------------------------------------------------------------
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    ref = reference_algorithm(ship)
    comp = compact_route_cost(ship)
    mech = mechanical_cost(ship, sample=600)
    sieve = attack_congruence_sieve(ship, time_budget=3.0)
    report["G5_density_and_cost"] = {
        "exact_count_demo": enumerate_all(demo),
        "shipping_analytic_density": 1.0 / space,
        "mechanical_ops_shipping": mech["ops"],
        "mechanical_seconds_shipping_extrapolated": mech["seconds_total"],
        "sieved_mechanical_ops_shipping": sieve["sieved_ops_needed"],
        "sieve_speedup": sieve["speedup"],
        "compact_ops_shipping": comp["ops"],
        "compact_seconds_shipping": comp["seconds"],
        "compact_s_reached": comp["s_reached"],
        "naive_order_compact_ops": ref["ops"],
        "gap_mechanical_over_compact": mech["ops"] / max(1, comp["ops"]),
    }

    # G6 -----------------------------------------------------------------
    panel: dict[str, dict] = {}
    n_att = 8
    for nm in ("bruteforce_scan", "congruence_sieve", "lattice_coppersmith",
               "in_context_heuristics"):
        panel[nm] = {"successes": 0, "attempts": 0}
    for s in range(n_att):
        i = make_instance(seed=100 + s, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for nm, fn in (("bruteforce_scan", attack_bruteforce_scan),
                       ("congruence_sieve", attack_congruence_sieve),
                       ("lattice_coppersmith", attack_lattice_coppersmith),
                       ("in_context_heuristics", attack_in_context_heuristics)):
            r = fn(i)
            panel[nm]["attempts"] += 1
            panel[nm]["successes"] += 1 if r.get("solved") else 0
    # outlier statistics -- a diagnostic (it cannot produce a point), reported
    # against the 1/m chance baseline
    outl: dict[str, int] = {}
    n_out = 24
    for s_ in range(n_out):
        i = make_instance(seed=300 + s_, **DIFFICULTY[SHIPPING_DIFFICULTY])
        j = i["answer"][0]
        for nm, v in attack_outlier_statistics(i).items():
            outl[nm + "_argmin"] = outl.get(nm + "_argmin", 0) + (v["argmin"] == j)
            outl[nm + "_argmax"] = outl.get(nm + "_argmax", 0) + (v["argmax"] == j)
    m_ship = DIFFICULTY[SHIPPING_DIFFICULTY]["n_ks"]
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in panel.values()),
        "attacks": panel,
        "outlier_diagnostics": {
            "trials": n_out,
            "chance_baseline": n_out / m_ship,
            "hits": outl,
        },
        "reference_algorithm": {
            "name": "phi_1 reduction to E_{1,k} + outward scan over s = x+y",
            "complexity": "O(m * S) big-integer square roots",
            "ops": comp["ops"], "seconds": comp["seconds"],
            "solved": comp["solved"],
        },
    }

    # G7 -----------------------------------------------------------------
    esc = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    g7 = {"escalate": esc if isinstance(esc, str) else dict(esc)}
    if isinstance(esc, dict):
        i2 = make_instance(seed=3, **esc)
        ok2, _ = verify(i2, i2["answer"])
        g7["escalated_builds_and_verifies"] = ok2
        g7["escalated_answer_chars"] = len(json.dumps(i2["answer"]))
        g7["moved_params"] = sorted(
            k for k in esc if esc[k] != DIFFICULTY[SHIPPING_DIFFICULTY].get(k))
        g7["pass"] = ok2 and len(g7["moved_params"]) >= 2
    else:
        g7["pass"] = False
    report["G7_scales"] = g7

    # G8 -----------------------------------------------------------------
    a = make_instance(seed=5, **DIFFICULTY["easy"])
    b_ = dict(a)
    perm = list(range(len(a["ks"])))
    random.Random(3).shuffle(perm)
    b_["ks"] = [a["ks"][t] for t in perm]
    c = make_instance(seed=6, **DIFFICULTY["easy"])
    report["G8_canonical_key"] = {
        "pass": canonical_key(a) == canonical_key(b_) != canonical_key(c),
    }

    report["pass"] = all(
        v.get("pass", True) for v in report.values() if isinstance(v, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, default=str))
