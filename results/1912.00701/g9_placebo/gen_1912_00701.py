"""Verified supersingular 2-isogeny-walk generator for arXiv:1912.00701.

The paper formulates the supersingular isogeny problem as path finding in an
ell-isogeny graph and, in Sections 2--3, explains the CGL encoding of a
non-backtracking 2-isogeny walk by a binary word.  This module inverse-generates
such a word over F_{p^2}, publishes only the oriented source curve and target
curve, and checks a proposed word by exact degree-2 quotient formulae.

Field elements are pairs (a,b) denoting a+b*i with i^2=-1.  Every supported
prime is a proved Mersenne prime p=2^e-1 with odd e, hence p=3 mod 4 and this is
indeed a representation of F_{p^2}.  Curves are monic split models

    y^2 = (x-r0)(x-r1)(x-r2).

Quotienting by the order-2 point (r,0), after translating r to zero, gives

    y^2 = x^3 - 2*a*x^2 + (a^2-4*b)*x,

where a=2*r-s-t and b=(r-s)(r-t).  Its branch points are
0 and a +/- 2*sqrt(b).  This makes generation and verification exact and
standard-library-only.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import multiprocessing
import os
import random
import re
import time


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "supersingular elliptic curves over F_(p^2) as split Weierstrass models",
        "a distinguished incoming 2-isogeny kernel",
        "a non-backtracking composition of degree-2 isogenies",
    ],
    "verification_operations": [
        "exact arithmetic in F_(p^2)",
        "exact square-root extraction in F_(p^2)",
        "exact degree-2 quotient (Velu) formula",
        "exact j-invariant comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "Use the marked dual kernel to remove backtracking and meet in the middle "
        "between the oriented source and target; without collision search the "
        "binary isogeny word must be explored exhaustively."
    ),
    "hardness_basis": (
        "Track A: Pizer's Ramanujan theorem, quoted in Section 2, places the "
        "generated Gamma_1(2;p) walks in the expanding supersingular regime where "
        "the paper's best cited classical path-finding cost is O~(sqrt(p)); at "
        "shipping p=2^127-1 this is about 2^63 graph operations, while fixed-length "
        "bidirectional search for the 64-step distribution needs about 2^32 "
        "midpoint states and the measured attack exhausts its 65536-state cap."
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


# n is a requested minimum field bit length.  It is rounded upward to a known
# Mersenne-prime exponent, so no probabilistic primality claim enters an instance.
_MERSENNE_EXPONENTS = (5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521, 607, 1279)

DIFFICULTY = {
    "easy": {"n": 127, "walk_length": 64, "prewalk_length": 16},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Hint: The marked order-two root is the dual-isogeny direction in the "
    "oriented supersingular walk."
)
PLACEBO_HINT = (
    "Hint: Keep the finite-field coordinates reduced modulo p throughout the "
    "calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One binary word of exactly walk_length symbols; at each curve the symbol "
        "selects one of the two lexicographically ordered order-2 kernels other "
        "than the marked dual kernel."
    ),
    "bounds": {
        "alphabet": ["0", "1"],
        "length": "walk_length",
        "max_named_preset_length": 96,
        "candidate_count": "2^walk_length",
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES = r"""
Definition. Section 2 defines Gamma_1(ell;p), its edges as ell-isogenies, and a
path/walk. Section 3's CGL paragraph fixes exactly the oriented binary encoding
used here: an incoming edge is distinguished and each message bit selects one
of the two 2-isogenies that is not its dual. The instance remains in the
paper's native objects: explicit elliptic curves over F_(p^2), an order-two
kernel, and a composition of 2-isogenies. No arbitrary graph is substituted.

Step-0 hardness decision. Theorem 1 is an attack on higher-dimensional general
path finding, not a polynomial-time certificate producer. For the elliptic
base case the paper explicitly gives O~(sqrt(p)) classical path finding in
Section 2. The fixed-length planted distribution also admits bidirectional
meet-in-the-middle in exponential time in half the word length. The shipping
parameters make those approximately 2^63 and 2^32 graph operations,
respectively. The generator never runs either: it samples the answer first and
composes exact quotient identities. This is Track A. The 2022 SIDH break does
not apply to this statement because it publishes no auxiliary torsion-point
images; it is a bare CGL-style endpoint problem.

Easy regimes avoided. The demo is deliberately tiny. Shipping uses the
127-bit Mersenne prime and 64 non-backtracking steps. The paper notes that an
explicit description of both endpoint endomorphism rings makes shortest-path
recovery efficient; neither ring is supplied. It also warns that higher-genus
product vertices enable recursive decomposition; the family stays in the
elliptic base problem, so there is no product factorization to read off.

Planting and attacks. Source randomization consists of a hidden prewalk followed
by a random affine change of the split model; target coordinates receive an
independent affine change. Thus the planted bits are not encoded by coordinate
size, sign, order, or a fixed zero root. The panel tests low-bit/outlier words,
greedy numerical closeness, random restarts, and a capped bidirectional
meet-in-the-middle implementation. Canonicalization uses the mathematical
oriented edge (previous j, source j) and target j, modulo Frobenius conjugation;
it is independent of the seed, root ordering, and affine curve coordinates.
"""


# ---------------------------------------------------------------------------
# Exact F_(p^2) arithmetic.  A field element is a tuple (a,b) for a+b*i.


def _resolve_exponent(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 5:
        raise ValueError("n must be at least 5")
    for exponent in _MERSENNE_EXPONENTS:
        if exponent >= n:
            return exponent
    raise ValueError(f"n exceeds the largest supported proved prime exponent {_MERSENNE_EXPONENTS[-1]}")


def _elt(value: object, p: int) -> tuple[int, int]:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(isinstance(x, bool) or not isinstance(x, int) for x in value)
    ):
        raise ValueError("field element must be a pair of integers")
    return int(value[0]) % p, int(value[1]) % p


def _add(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return (x[0] + y[0]) % p, (x[1] + y[1]) % p


def _sub(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return (x[0] - y[0]) % p, (x[1] - y[1]) % p


def _neg(x: tuple[int, int], p: int) -> tuple[int, int]:
    return (-x[0]) % p, (-x[1]) % p


def _mul(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return (
        (x[0] * y[0] - x[1] * y[1]) % p,
        (x[0] * y[1] + x[1] * y[0]) % p,
    )


def _square(x: tuple[int, int], p: int) -> tuple[int, int]:
    return (x[0] * x[0] - x[1] * x[1]) % p, (2 * x[0] * x[1]) % p


def _inv(x: tuple[int, int], p: int) -> tuple[int, int]:
    denominator = (x[0] * x[0] + x[1] * x[1]) % p
    if denominator == 0:
        raise ZeroDivisionError("zero has no inverse")
    inverse = pow(denominator, -1, p)
    return x[0] * inverse % p, -x[1] * inverse % p


def _div(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return _mul(x, _inv(y, p), p)


def _scale(k: int, x: tuple[int, int], p: int) -> tuple[int, int]:
    return k * x[0] % p, k * x[1] % p


def _conj(x: tuple[int, int], p: int) -> tuple[int, int]:
    return x[0], -x[1] % p


def _sqrt_fp(a: int, p: int) -> int | None:
    """A canonical square root in F_p for p=3 mod 4, or None."""

    a %= p
    if a == 0:
        return 0
    root = pow(a, (p + 1) // 4, p)
    if root * root % p != a:
        return None
    return min(root, p - root)


def _sqrt_fq(value: tuple[int, int], p: int) -> tuple[int, int]:
    """A canonical square root of a known square in F_(p^2)."""

    a, b = value
    if a == 0 and b == 0:
        return 0, 0
    if b == 0:
        root = _sqrt_fp(a, p)
        if root is not None:
            return root, 0
        root = _sqrt_fp(-a, p)
        if root is not None:
            return 0, root
        raise ValueError("element is not a square in F_(p^2)")

    norm_root = _sqrt_fp((a * a + b * b) % p, p)
    if norm_root is None:
        raise ValueError("element is not a square in F_(p^2)")
    inv_two = (p + 1) // 2
    for signed_norm in (norm_root, -norm_root % p):
        x_squared = (a + signed_norm) * inv_two % p
        x = _sqrt_fp(x_squared, p)
        if x not in (None, 0):
            y = b * pow(2 * x, -1, p) % p
            root = (x, y)
            if _square(root, p) == value:
                return min(root, _neg(root, p))
    raise ValueError("element is not a square in F_(p^2)")


def _json_elt(x: tuple[int, int]) -> list[int]:
    return [x[0], x[1]]


def _json_roots(roots: tuple[tuple[int, int], ...]) -> list[list[int]]:
    return [_json_elt(x) for x in roots]


def _read_roots(values: object, p: int) -> tuple[tuple[int, int], ...]:
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError("curve roots must be a list of three field elements")
    roots = tuple(_elt(value, p) for value in values)
    if len(set(roots)) != 3:
        raise ValueError("curve is singular because its roots are not distinct")
    return roots


# ---------------------------------------------------------------------------
# Curves, 2-isogenies, and inverse generation.


def _quotient(
    roots: tuple[tuple[int, int], ...], kernel_root: tuple[int, int], p: int
) -> tuple[tuple[int, int], ...]:
    if kernel_root not in roots:
        raise ValueError("kernel root is not a branch point")
    others = list(roots)
    others.remove(kernel_root)
    s, t = others
    a = _sub(_scale(2, kernel_root, p), _add(s, t, p), p)
    b = _mul(_sub(kernel_root, s, p), _sub(kernel_root, t, p), p)
    root_b = _sqrt_fq(b, p)
    twice_root_b = _scale(2, root_b, p)
    result = ((0, 0), _add(a, twice_root_b, p), _sub(a, twice_root_b, p))
    if len(set(result)) != 3:
        raise ValueError("degenerate degree-2 quotient")
    return result


def _transition(
    roots: tuple[tuple[int, int], ...],
    forbidden_root: tuple[int, int],
    bit: int,
    p: int,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, int]]:
    if forbidden_root not in roots:
        raise ValueError("marked dual kernel is not a branch point")
    choices = sorted(root for root in roots if root != forbidden_root)
    if bit not in (0, 1):
        raise ValueError("isogeny symbol must be 0 or 1")
    return _quotient(roots, choices[bit], p), (0, 0)


def _curve_j(roots: tuple[tuple[int, int], ...], p: int) -> tuple[int, int]:
    """Exact j-invariant of y^2=product(x-r), valid in char > 3."""

    r0, r1, r2 = roots
    # Translate r0 to zero.  The resulting equation is x^3+a*x^2+b*x.
    a = _sub(_scale(2, r0, p), _add(r1, r2, p), p)
    b = _mul(_sub(r0, r1, p), _sub(r0, r2, p), p)
    a2 = _square(a, p)
    numerator_base = _sub(a2, _scale(3, b, p), p)
    numerator = _scale(256, _mul(_square(numerator_base, p), numerator_base, p), p)
    denominator = _mul(_square(b, p), _sub(a2, _scale(4, b, p), p), p)
    return _div(numerator, denominator, p)


def _walk(
    roots: tuple[tuple[int, int], ...],
    forbidden_root: tuple[int, int],
    word: str,
    p: int,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, int]]:
    for symbol in word:
        roots, forbidden_root = _transition(roots, forbidden_root, ord(symbol) - 48, p)
    return roots, forbidden_root


def _random_nonzero(rng: random.Random, p: int) -> tuple[int, int]:
    while True:
        value = rng.randrange(p), rng.randrange(p)
        if value != (0, 0):
            return value


def _affine_roots(
    roots: tuple[tuple[int, int], ...],
    multiplier: tuple[int, int],
    translation: tuple[int, int],
    p: int,
    conjugate: bool = False,
) -> tuple[tuple[int, int], ...]:
    def move(x: tuple[int, int]) -> tuple[int, int]:
        base = _conj(x, p) if conjugate else x
        return _add(_mul(multiplier, base, p), translation, p)

    return tuple(move(root) for root in roots)


def _good_oriented_state(
    roots: tuple[tuple[int, int], ...], forbidden: tuple[int, int], p: int
) -> bool:
    try:
        j0 = _curve_j(roots, p)
        child_js = {
            _curve_j(_transition(roots, forbidden, bit, p)[0], p) for bit in (0, 1)
        }
        return len(child_js) == 2 and j0 not in child_js
    except (ValueError, ZeroDivisionError):
        return False


def make_instance(
    n: int,
    seed: int = 0,
    walk_length: int = 64,
    prewalk_length: int = 16,
    **params: object,
) -> dict:
    """Inverse-generate a CGL-style non-backtracking 2-isogeny preimage.

    The binary answer is sampled before the target.  Starting from the known
    supersingular curve y^2=x^3-x for p=3 mod 4, a hidden prewalk removes its
    extra-automorphism local symmetry.  Exact quotient identities then compose
    the planted walk.  No endpoint path-finding algorithm is run.
    """

    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    if isinstance(walk_length, bool) or not isinstance(walk_length, int):
        raise TypeError("walk_length must be an integer")
    if isinstance(prewalk_length, bool) or not isinstance(prewalk_length, int):
        raise TypeError("prewalk_length must be an integer")
    if not 1 <= walk_length <= 256:
        raise ValueError("walk_length must lie in 1..256")
    if prewalk_length < 1:
        raise ValueError("prewalk_length must be positive")

    exponent = _resolve_exponent(n)
    p = (1 << exponent) - 1
    rng = random.Random(seed)

    # j=1728 is supersingular for p=3 mod 4.  The marked zero root represents
    # the incoming edge; the hidden prewalk is allowed to pass through the
    # small automorphism orbit, but the published source is not.
    roots: tuple[tuple[int, int], ...] = ((0, 0), (1, 0), (p - 1, 0))
    forbidden = (0, 0)
    for _ in range(prewalk_length):
        roots, forbidden = _transition(roots, forbidden, rng.randrange(2), p)
    for _ in range(64):
        if _good_oriented_state(roots, forbidden, p):
            break
        roots, forbidden = _transition(roots, forbidden, rng.randrange(2), p)
    else:
        raise RuntimeError("could not leave the extra-automorphism neighbourhood")

    # A square x-multiplier is an honest Weierstrass change of coordinates.
    scale_source = _square(_random_nonzero(rng, p), p)
    translate_source = (rng.randrange(p), rng.randrange(p))
    roots = _affine_roots(roots, scale_source, translate_source, p)
    forbidden = _add(_mul(scale_source, forbidden, p), translate_source, p)

    answer = "".join(str(rng.randrange(2)) for _ in range(walk_length))
    target_roots, _target_forbidden = _walk(roots, forbidden, answer, p)

    # Give the target as an ordinary un-oriented curve model.  An independent
    # affine change removes the otherwise visible zero root of the final dual.
    scale_target = _square(_random_nonzero(rng, p), p)
    translate_target = (rng.randrange(p), rng.randrange(p))
    target_roots = _affine_roots(target_roots, scale_target, translate_target, p)

    source_j = _curve_j(roots, p)
    target_j = _curve_j(target_roots, p)
    if source_j == target_j:
        # This event is negligible at named presets.  Deterministically extend
        # the already sampled construction rather than solve the endpoint.
        replacement = "1" if answer[-1] == "0" else "0"
        answer = answer[:-1] + replacement
        target_roots, _target_forbidden = _walk(roots, forbidden, answer, p)
        target_roots = _affine_roots(target_roots, scale_target, translate_target, p)
        target_j = _curve_j(target_roots, p)
        if source_j == target_j:
            raise RuntimeError("degenerate planted endpoint; choose another seed")

    return {
        "paper": "arXiv:1912.00701",
        "family": "CGL-style supersingular 2-isogeny word preimage",
        "n": n,
        "prime_exponent": exponent,
        "p": p,
        "field_nonresidue": -1,
        "walk_length": walk_length,
        "prewalk_length": prewalk_length,
        "source_roots": _json_roots(roots),
        "source_forbidden_root": _json_elt(forbidden),
        "source_j": _json_elt(source_j),
        "target_roots": _json_roots(target_roots),
        "target_j": _json_elt(target_j),
        "seed": seed,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# User-facing contract.


def _format_elt(value: list[int] | tuple[int, int]) -> str:
    return f"({value[0]},{value[1]})"


def render(inst: dict) -> str:
    p = inst["p"]
    length = inst["walk_length"]
    roots = ", ".join(_format_elt(root) for root in inst["source_roots"])
    target_roots = ", ".join(_format_elt(root) for root in inst["target_roots"])
    lines = [
        "Recover a non-backtracking supersingular 2-isogeny walk.",
        "",
        "All arithmetic below is exact. Let F be the field F_p[i] with i^2=-1;",
        f"p={p}. A pair (a,b) denotes a+b*i, with both coordinates reduced modulo p.",
        "For this p, -1 is not a square in F_p, so these pairs form F_(p^2).",
        "",
        "A curve is represented by three distinct branch points r0,r1,r2 in F:",
        "    E: y^2=(x-r0)(x-r1)(x-r2).",
        "Each branch point r gives the nonzero order-2 point (r,0). One branch",
        "point is marked as forbidden: it is the kernel of the dual of the",
        "previous 2-isogeny. Thus each step has exactly two allowed kernels.",
        "",
        "The binary step rule is the following deterministic exact rule.",
        "1. Sort the two roots other than the forbidden root lexicographically",
        "   by (a,b). Bit 0 chooses the first and bit 1 chooses the second.",
        "2. If the chosen root is r and the other roots are s,t, set",
        "       A=2*r-s-t and B=(r-s)*(r-t) in F.",
        "3. Let q be the lexicographically smaller of the two square roots of B.",
        "   Replace the curve roots by (0,0), A+2*q, A-2*q. Mark (0,0)",
        "   forbidden for the next step. This is the exact degree-2 quotient.",
        "",
        f"Source roots: {roots}",
        f"Source forbidden root: {_format_elt(inst['source_forbidden_root'])}",
        f"Source j-invariant (for checking only): {_format_elt(inst['source_j'])}",
        "",
        f"Target roots (un-ordered and with no forbidden root): {target_roots}",
        f"Target j-invariant: {_format_elt(inst['target_j'])}",
        "",
        "Two curves count as the same endpoint exactly when their j-invariants",
        "are equal in F. Intermediate coordinate models need not equal the target",
        "model. Repeated vertices are allowed; only immediate dual backtracking is",
        "forbidden by the marked-root rule.",
        "",
        f"Find one binary word of exactly {length} bits whose successive quotient",
        "steps start at the source and finish at a curve with the target j-invariant.",
        "No spaces, separators, or prefix are allowed inside the answer tags.",
        "",
        "Give your final answer inside <answer></answer> tags, as one binary word.",
        "Example: <answer>01001101</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract one tagged binary word, tolerating prose and Markdown fences."""

    try:
        if not isinstance(text, str):
            return None
        matches = re.findall(
            r"<answer\b[^>]*>(.*?)</answer\s*>", text, flags=re.IGNORECASE | re.DOTALL
        )
        if len(matches) != 1:
            return None
        body = matches[0].strip()
        body = re.sub(r"^```(?:[A-Za-z0-9_-]+)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
        if re.fullmatch(r"[01]+", body) is None:
            return None
        return body
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay any candidate word exactly; never inspect inst['answer']."""

    if not isinstance(answer, str):
        return False, "malformed answer: expected one binary string"
    if answer == "":
        return False, "empty answer: expected a nonempty binary word"
    if re.fullmatch(r"[01]+", answer) is None:
        return False, "invalid symbol: the word may contain only 0 and 1"
    expected = inst.get("walk_length")
    if len(answer) < expected:
        return False, f"word too short: expected {expected} bits, got {len(answer)}"
    if len(answer) > expected:
        return False, f"word too long: expected {expected} bits, got {len(answer)}"
    try:
        p = int(inst["p"])
        roots = _read_roots(inst["source_roots"], p)
        forbidden = _elt(inst["source_forbidden_root"], p)
        if forbidden not in roots:
            return False, "invalid instance: source forbidden root is not on the curve"
        source_j = _elt(inst["source_j"], p)
        if _curve_j(roots, p) != source_j:
            return False, "invalid instance: displayed source j-invariant is inconsistent"
        target_roots = _read_roots(inst["target_roots"], p)
        target_j = _elt(inst["target_j"], p)
        if _curve_j(target_roots, p) != target_j:
            return False, "invalid instance: displayed target j-invariant is inconsistent"
        roots, _forbidden = _walk(roots, forbidden, answer, p)
        if _curve_j(roots, p) != target_j:
            return False, "endpoint mismatch: the word does not reach the target j-invariant"
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return False, f"exact isogeny replay failed: {exc}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact fixed-length binary walk language."""

    return "".join(str(rng.randrange(2)) for _ in range(inst["walk_length"]))


def search_space(inst: dict) -> int:
    return 1 << inst["walk_length"]


def enumerate_all(inst: dict) -> int | None:
    length = inst["walk_length"]
    if length > 18:
        return None
    count = 0
    for bits in itertools.product("01", repeat=length):
        count += int(verify(inst, "".join(bits))[0])
    return count


# ---------------------------------------------------------------------------
# Canonicalization and relabelling tests.


def _orientation_signature(inst: dict, conjugate: bool = False) -> tuple[object, ...]:
    p = inst["p"]
    source = _read_roots(inst["source_roots"], p)
    forbidden = _elt(inst["source_forbidden_root"], p)
    previous = _curve_j(_quotient(source, forbidden, p), p)
    current = _curve_j(source, p)
    target = _curve_j(_read_roots(inst["target_roots"], p), p)
    if conjugate:
        previous, current, target = (
            _conj(previous, p),
            _conj(current, p),
            _conj(target, p),
        )
    return (
        p,
        inst["walk_length"],
        previous,
        current,
        target,
    )


def canonical_key(inst: dict) -> str:
    """Hash canonical oriented endpoint data, not the seed or rendered text."""

    signatures = (_orientation_signature(inst), _orientation_signature(inst, True))
    canonical = min(
        json.dumps(signature, separators=(",", ":"), sort_keys=True)
        for signature in signatures
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _carry_word_under_affine(
    roots: tuple[tuple[int, int], ...],
    forbidden: tuple[int, int],
    word: str,
    multiplier: tuple[int, int],
    translation: tuple[int, int],
    p: int,
    conjugate: bool,
) -> tuple[str, tuple[tuple[int, int], ...]]:
    moved_roots = _affine_roots(roots, multiplier, translation, p, conjugate)
    moved_forbidden = _add(
        _mul(multiplier, _conj(forbidden, p) if conjugate else forbidden, p),
        translation,
        p,
    )
    carried: list[str] = []
    current_translation = translation
    for symbol in word:
        old_choices = sorted(root for root in roots if root != forbidden)
        selected = old_choices[ord(symbol) - 48]
        moved_selected = _add(
            _mul(multiplier, _conj(selected, p) if conjugate else selected, p),
            current_translation,
            p,
        )
        new_choices = sorted(root for root in moved_roots if root != moved_forbidden)
        if moved_selected not in new_choices:
            raise AssertionError("affine map did not carry the selected kernel")
        moved_bit = new_choices.index(moved_selected)
        carried.append(str(moved_bit))
        roots, forbidden = _transition(roots, forbidden, ord(symbol) - 48, p)
        moved_roots, moved_forbidden = _transition(
            moved_roots, moved_forbidden, moved_bit, p
        )
        expected = set(_affine_roots(roots, multiplier, (0, 0), p, conjugate))
        if set(moved_roots) != expected:
            raise AssertionError("quotient did not commute with the affine relabelling")
        current_translation = (0, 0)
    return "".join(carried), moved_roots


def _relabel_instance(
    inst: dict,
    multiplier: tuple[int, int],
    translation: tuple[int, int],
    conjugate: bool,
    reorder: bool,
) -> dict:
    p = inst["p"]
    source = _read_roots(inst["source_roots"], p)
    forbidden = _elt(inst["source_forbidden_root"], p)
    carried, _end = _carry_word_under_affine(
        source,
        forbidden,
        inst["answer"],
        multiplier,
        translation,
        p,
        conjugate,
    )
    moved_source = _affine_roots(source, multiplier, translation, p, conjugate)
    moved_forbidden = _add(
        _mul(multiplier, _conj(forbidden, p) if conjugate else forbidden, p),
        translation,
        p,
    )
    target = _read_roots(inst["target_roots"], p)
    target_translation = _scale(7, translation, p)
    moved_target = _affine_roots(
        target, multiplier, target_translation, p, conjugate
    )
    if reorder:
        moved_source = tuple(reversed(moved_source))
        moved_target = (moved_target[1], moved_target[2], moved_target[0])
    moved = dict(inst)
    moved["source_roots"] = _json_roots(moved_source)
    moved["source_forbidden_root"] = _json_elt(moved_forbidden)
    moved["source_j"] = _json_elt(_curve_j(moved_source, p))
    moved["target_roots"] = _json_roots(moved_target)
    moved["target_j"] = _json_elt(_curve_j(moved_target, p))
    moved["answer"] = carried
    return moved


# ---------------------------------------------------------------------------
# Adversarial attacks.


def _endpoint_low_bits(inst: dict) -> tuple[str, int]:
    values = [
        *inst["source_j"],
        *inst["target_j"],
        *inst["source_forbidden_root"],
    ]
    word = "".join(str(values[i % len(values)] & 1) for i in range(inst["walk_length"]))
    return word, len(word)


def _cyclic_distance(x: int, y: int, p: int) -> int:
    delta = (x - y) % p
    return min(delta, p - delta)


def _greedy_numeric(inst: dict) -> tuple[str, int]:
    p = inst["p"]
    roots = _read_roots(inst["source_roots"], p)
    forbidden = _elt(inst["source_forbidden_root"], p)
    target = _elt(inst["target_j"], p)
    word: list[str] = []
    operations = 0
    for _ in range(inst["walk_length"]):
        options = []
        for bit in (0, 1):
            child_roots, child_forbidden = _transition(roots, forbidden, bit, p)
            j = _curve_j(child_roots, p)
            distance = _cyclic_distance(j[0], target[0], p) + _cyclic_distance(
                j[1], target[1], p
            )
            options.append((distance, bit, child_roots, child_forbidden))
            operations += 1
        _distance, bit, roots, forbidden = min(options, key=lambda row: (row[0], row[1]))
        word.append(str(bit))
    return "".join(word), operations


def _random_restarts(inst: dict, rng: random.Random, restarts: int) -> tuple[bool, int]:
    for attempt in range(1, restarts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, attempt
    return False, restarts


def _frontier_from_oriented(
    roots: tuple[tuple[int, int], ...],
    forbidden: tuple[int, int],
    depth: int,
    p: int,
    budget: int,
) -> tuple[dict[tuple[int, int], tuple[tuple[tuple[int, int], ...], list[tuple[int, int]]]], int, bool]:
    start_j = _curve_j(roots, p)
    frontier = [(roots, forbidden, [start_j])]
    nodes = 1
    for _ in range(depth):
        nxt = []
        for state_roots, state_forbidden, path in frontier:
            for bit in (0, 1):
                child, child_forbidden = _transition(
                    state_roots, state_forbidden, bit, p
                )
                child_j = _curve_j(child, p)
                nxt.append((child, child_forbidden, path + [child_j]))
                nodes += 1
                if nodes >= budget:
                    return {}, nodes, False
        frontier = nxt
    table = {
        _curve_j(state_roots, p): (state_roots, path)
        for state_roots, _state_forbidden, path in frontier
    }
    return table, nodes, True


def _frontier_from_target(
    roots: tuple[tuple[int, int], ...], depth: int, p: int, budget: int
) -> tuple[dict[tuple[int, int], list[list[tuple[int, int]]]], int, bool]:
    start_j = _curve_j(roots, p)
    # The target is un-oriented: its first reverse step may use any of 3 roots.
    frontier: list[tuple[tuple[tuple[int, int], ...], tuple[int, int] | None, list[tuple[int, int]]]] = [
        (roots, None, [start_j])
    ]
    nodes = 1
    for _ in range(depth):
        nxt = []
        for state_roots, state_forbidden, path in frontier:
            choices = (
                sorted(state_roots)
                if state_forbidden is None
                else sorted(root for root in state_roots if root != state_forbidden)
            )
            for kernel in choices:
                child = _quotient(state_roots, kernel, p)
                child_j = _curve_j(child, p)
                nxt.append((child, (0, 0), path + [child_j]))
                nodes += 1
                if nodes >= budget:
                    return {}, nodes, False
        frontier = nxt
    table: dict[tuple[int, int], list[list[tuple[int, int]]]] = {}
    for state_roots, _state_forbidden, path in frontier:
        table.setdefault(_curve_j(state_roots, p), []).append(path)
    return table, nodes, True


def _word_for_j_path(inst: dict, path: list[tuple[int, int]]) -> str | None:
    p = inst["p"]
    roots = _read_roots(inst["source_roots"], p)
    forbidden = _elt(inst["source_forbidden_root"], p)
    result: list[str] = []
    for wanted in path[1:]:
        matched = False
        for bit in (0, 1):
            child, child_forbidden = _transition(roots, forbidden, bit, p)
            if _curve_j(child, p) == wanted:
                result.append(str(bit))
                roots, forbidden = child, child_forbidden
                matched = True
                break
        if not matched:
            return None
    return "".join(result)


def _meet_in_middle(inst: dict, node_cap: int) -> tuple[bool, int, str]:
    """Exact bidirectional attack when frontiers fit; otherwise a measured cap."""

    p = inst["p"]
    length = inst["walk_length"]
    left_depth = length // 2
    right_depth = length - left_depth
    left_budget = max(2, node_cap // 2)
    right_budget = max(2, node_cap - left_budget)
    source = _read_roots(inst["source_roots"], p)
    forbidden = _elt(inst["source_forbidden_root"], p)
    left, left_nodes, left_complete = _frontier_from_oriented(
        source, forbidden, left_depth, p, left_budget
    )
    if not left_complete:
        return False, left_nodes, "left frontier exceeded cap before midpoint"
    target = _read_roots(inst["target_roots"], p)
    right, right_nodes, right_complete = _frontier_from_target(
        target, right_depth, p, right_budget
    )
    nodes = left_nodes + right_nodes
    if not right_complete:
        return False, nodes, "right frontier exceeded cap before midpoint"
    for meeting in left.keys() & right.keys():
        left_path = left[meeting][1]
        for reverse_path in right[meeting]:
            full_path = left_path + list(reversed(reverse_path))[1:]
            word = _word_for_j_path(inst, full_path)
            if word is not None and verify(inst, word)[0]:
                return True, nodes, "frontiers met at a verified path"
    return False, nodes, "complete capped frontiers had no compatible collision"


def escalate(params: dict) -> dict | str | None:
    """Raise the field first and the walk entropy second, within output caps."""

    current_n = int(params.get("n", 127))
    current_length = int(params.get("walk_length", 64))
    current_prewalk = int(params.get("prewalk_length", 16))
    exponent = _resolve_exponent(current_n)
    try:
        next_exponent = _MERSENNE_EXPONENTS[_MERSENNE_EXPONENTS.index(exponent) + 1]
    except IndexError:
        if current_length >= 256:
            return "cap_bound"
        harder = dict(params)
        harder["n"] = current_n
        harder["walk_length"] = min(256, current_length + 16)
        harder["prewalk_length"] = min(64, current_prewalk + 4)
        return harder
    harder = dict(params)
    harder["n"] = next_exponent
    harder["walk_length"] = min(256, current_length + 16)
    harder["prewalk_length"] = min(64, current_prewalk + 4)
    return harder


# ---------------------------------------------------------------------------
# Mandatory gates.


def _answer_metrics(answer: str) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def _guess_worker(payload: tuple[dict, int, int]) -> tuple[int, int]:
    inst, samples, worker_seed = payload
    rng = random.Random(worker_seed)
    hits = 0
    for _ in range(samples):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    return hits, samples


def _sample_guesses(inst: dict, total: int) -> tuple[int, float, int]:
    """Parallel exact replay of structure-aware random walks on POSIX."""

    workers = min(12, os.cpu_count() or 1)
    if total < workers or "fork" not in multiprocessing.get_all_start_methods():
        workers = 1
    sizes = [total // workers + (index < total % workers) for index in range(workers)]
    payloads = [
        (inst, size, 0x191200701 + 1_000_003 * index)
        for index, size in enumerate(sizes)
        if size
    ]
    started = time.perf_counter()
    if workers == 1:
        results = [_guess_worker(payloads[0])]
    else:
        context = multiprocessing.get_context("fork")
        with context.Pool(workers) as pool:
            results = pool.map(_guess_worker, payloads)
    elapsed = time.perf_counter() - started
    return sum(row[0] for row in results), elapsed, workers


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, multiple seeds, exact checking and JSON-native answers.
    g1_attempts = 0
    g1_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                restored = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if restored != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]

    # G2: five corruption classes with five distinct rejection diagnostics.
    differing = next(
        (index for index in range(len(answer) - 1) if answer[index] != answer[index + 1]),
        None,
    )
    if differing is None:
        swapped = ("1" if answer[0] == "0" else "0") + answer[1:]
    else:
        data = list(answer)
        data[differing], data[differing + 1] = data[differing + 1], data[differing]
        swapped = "".join(data)
    corruptions: dict[str, object] = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + answer[-1],
        "empty": "",
        "out_of_range": "2" + answer[1:],
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and an outer Markdown fence.
    realistic = (
        "I used the marked dual kernel to orient the walk.\n```text\n"
        f"<answer>\n{answer}\n</answer>\n```\n"
        "The tag contains the requested binary word."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(ship, parsed)[0],
        "parsed_matches": parsed == answer,
        "realistic_wrapper": True,
    }

    # G4: exact endpoint checks for 200k uniformly sampled valid walk words.
    guess_total = 200_000
    guess_hits, guess_elapsed, guess_workers = _sample_guesses(ship, guess_total)
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": (
            "uniform over exact-length binary non-backtracking kernel-choice words; "
            "all stated shape and orientation constraints are already enforced"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
        "workers": guess_workers,
    }

    # G6: three construction-aware probes and the domain-standard collision attack.
    attack_names = (
        "endpoint_coordinate_low_bits",
        "greedy_j_coordinate_distance",
        "random_restart_64",
        "bidirectional_meet_in_middle_65536_cap",
    )
    attack_stats = {
        name: {"successes": 0, "attempts": 0, "operations": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    mitm_reasons: list[str] = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping)

        started = time.perf_counter()
        candidate, operations = _endpoint_low_bits(inst)
        elapsed = time.perf_counter() - started
        stat = attack_stats["endpoint_coordinate_low_bits"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["operations"] += operations
        stat["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, operations = _greedy_numeric(inst)
        elapsed = time.perf_counter() - started
        stat = attack_stats["greedy_j_coordinate_distance"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["operations"] += operations
        stat["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        success, operations = _random_restarts(
            inst, random.Random(seed ^ 0xC61A), 64
        )
        elapsed = time.perf_counter() - started
        stat = attack_stats["random_restart_64"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["operations"] += operations
        stat["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        success, operations, reason = _meet_in_middle(inst, 65_536)
        elapsed = time.perf_counter() - started
        stat = attack_stats["bidirectional_meet_in_middle_65536_cap"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["operations"] += operations
        stat["wall_clock_sec"] += elapsed
        mitm_reasons.append(reason)

    for stat in attack_stats.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attack_stats.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_stats,
        "domain_attack_notes": sorted(set(mitm_reasons)),
        "standard_algorithm": (
            "fixed-length bidirectional collision/meet-in-the-middle; Section 2 "
            "also gives O~(sqrt(p)) general supersingular path finding"
        ),
        "projected_shipping_midpoint_states": 1 << (ship["walk_length"] // 2),
    }

    # G5: shipping density plus the actual strongest measured baseline cost.
    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest = max(
        attack_stats.items(), key=lambda item: item[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline"] = {
        "pass": guess_fraction < 1e-6 and strongest[1]["successes"] == 0,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_attack": strongest[0],
        "strongest_attack_wall_clock_sec": strongest[1]["wall_clock_sec"],
        "strongest_attack_operations": strongest[1]["operations"],
        "strongest_attack_attempts": strongest[1]["attempts"],
    }

    # G7: ordered ladder, a doubled n, and a two-axis escalation all verify.
    ladder_instances = [
        make_instance(seed=777, **params) for params in DIFFICULTY.values()
    ]
    ladder_field_bits = [inst["prime_exponent"] for inst in ladder_instances]
    ladder_spaces = [search_space(inst) for inst in ladder_instances]
    doubled = make_instance(
        n=2 * ship["n"],
        walk_length=ship["walk_length"],
        prewalk_length=ship["prewalk_length"],
        seed=909,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated_params = escalate(dict(shipping))
    escalated = (
        make_instance(seed=910, **escalated_params)
        if isinstance(escalated_params, dict)
        else None
    )
    escalated_ok, escalated_reason = (
        verify(escalated, escalated["answer"])
        if escalated is not None
        else (False, "escalate did not return parameters")
    )
    report["G7_scales"] = {
        "pass": (
            ladder_field_bits == sorted(set(ladder_field_bits))
            and ladder_spaces == sorted(set(ladder_spaces))
            and doubled_ok
            and doubled["prime_exponent"] > ship["prime_exponent"]
            and escalated_ok
            and isinstance(escalated_params, dict)
            and escalated_params["n"] > shipping["n"]
            and escalated_params["walk_length"] > shipping["walk_length"]
        ),
        "preset_field_bits": dict(zip(DIFFICULTY, ladder_field_bits)),
        "preset_candidate_spaces": dict(zip(DIFFICULTY, ladder_spaces)),
        "doubled_requested_n": doubled["n"],
        "doubled_field_bits": doubled["prime_exponent"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "escalated_params": escalated_params,
        "escalated_verifies": escalated_ok,
        "escalated_reason": escalated_reason,
    }

    # G8: root permutations, affine model changes, Frobenius, and compositions.
    invariant_checks = 0
    witness_checks = 0
    invariant_failures: list[str] = []
    unrelated_keys: list[str] = []
    for seed in range(20):
        inst = make_instance(n=31, walk_length=12, prewalk_length=8, seed=20_000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        p = inst["p"]
        rng = random.Random(30_000 + seed)
        multiplier = _square(_random_nonzero(rng, p), p)
        translation = (rng.randrange(p), rng.randrange(p))
        variants = (
            _relabel_instance(inst, (1, 0), (0, 0), False, True),
            _relabel_instance(inst, multiplier, translation, False, False),
            _relabel_instance(inst, (1, 0), (0, 0), True, False),
            _relabel_instance(inst, multiplier, translation, True, True),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                invariant_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant_failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary branch-root reordering",
            "square affine change of Weierstrass x-coordinate",
            "Frobenius conjugation in F_(p^2)",
            "composition of affine change, conjugation, and root reordering",
        ],
    }

    # G9(a,b) is patched from harden.py evidence; only the local caps gate here.
    chars, tokens, elements = _answer_metrics(answer)
    intended_operations = len(answer)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
