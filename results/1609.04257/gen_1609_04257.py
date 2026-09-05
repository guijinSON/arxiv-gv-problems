"""Verified sparse standard-representation generator for arXiv:1609.04257.

The paper studies strong standard bases over Z and, in its preIntegerCheck
strategy, obtains integer-in-ideal certificates from polynomial syzygies.  This
module asks for the closely related native witness: polynomial multipliers
whose exact sum is a displayed target.  Instances are made by inverse
generation; the target is computed only after the multipliers are chosen.
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
from fractions import Fraction


# Make repository helpers visible when harden.py is invoked from this folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals, sparse_poly
except ImportError:                 # pragma: no cover - full stdlib fallback below
    exact_matrices = rationals = sparse_poly = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "univariate polynomials over Z in coefficient-formula representation",
        "a target polynomial over Z",
        "a sparse vector of polynomial ideal-membership multipliers",
    ],
    "verification_operations": [
        "exact rational polynomial parsing",
        "exact polynomial multiplication and addition over Z",
        "coefficient-by-coefficient identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "After removing the common multiplier 1+x, the target coefficients "
        "form a five-atom signed power-sum sequence whose degree-five "
        "annihilator reveals the participating generators."
    ),
    "hardness_basis": (
        "Track B: the standard signed-subset meet-in-the-middle algorithm is "
        "O(n^3) exact arithmetic and at shipping n=80 averaged 205,840 "
        "integer operations and about 0.01 seconds in the eight-seed gate run, "
        "whereas the annihilating-polynomial route uses at most 231 exact "
        "arithmetic operations once the invariant is recognized."
    ),
    "max_answer_tokens": 41,
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
        "A JSON list of exactly five [generator, polynomial] entries, sorted "
        "by distinct 1-based generator number.  Every polynomial is the "
        "coefficient-first sparse representation of +(1+x) or -(1+x), with "
        "a rational coefficient encoded [num,den] and its monomial encoded by "
        "the one-variable exponent list [e].  Exactly two signs are positive "
        "and three are negative."
    ),
    "bounds": {
        "nonzero_multipliers": 5,
        "positive_multipliers": 2,
        "negative_multipliers": 3,
        "variables": 1,
        "max_degree": 1,
        "terms_per_multiplier": 2,
        "coefficient_numerators": [-1, 1],
        "coefficient_denominator": 1,
        "generator_indices": "1..n inclusive, distinct and increasing",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "moment_count": 10, "prime_min": 2, "prime_span": 12},
    "easy": {"n": 40, "moment_count": 10, "prime_min": 100, "prime_span": 800},
    "medium": {"n": 80, "moment_count": 10, "prime_min": 1_000, "prime_span": 8_000},
    "hard": {"n": 128, "moment_count": 10, "prime_min": 10_000, "prime_span": 50_000},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT: str = (
    "The quotient by 1+x is a signed power-sum sequence with a degree-five annihilator."
)
PLACEBO_HINT: str = (
    "The coefficient ordering and the one-based labels both reward especially careful bookkeeping."
)

# Filled after the three script-owned runs.  Zero attempts are honest while the
# local mathematical gates are being developed; G9's oracle arms are diagnostic.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES: str = r"""
Paper triage.  Definition 4 in the Introduction fixes a standard basis through
the leading ideal in Z[x].  Algorithm 1 is Buchberger's strong-standard-basis
algorithm over a principal ideal ring.  Section 3, Algorithm 2
(preIntegerCheck), computes a standard basis over Q and syzygies of
<1,f_1,...,f_r> in order to expose a polynomial combination yielding an
integer; Example 1 displays such a combination.  Section 4, Algorithm 3 gives
the terminating weak-normal-form procedure for local and mixed orderings.

Step-0 hardness decision.  The paper proves no hardness result for a generated
distribution.  On the contrary it gives the algorithms producing normal forms,
standard bases, and syzygies.  It also measures why their mechanical execution
can be formidable: ALL versus JUST differs by factors up to 38,000, Example
B:1 takes almost 30 hours over Z, and the 70-generator Section 3 example first
produces the integer 6,133,248.  Therefore this module is Track B, never Track
A.  For this bounded family the strongest simple reference algorithm is the
exact meet-in-the-middle search over a positive pair and a negative triple.

Construction.  For each distinct positive prime a_i, define
f_i(x)=sum_{r=0}^{9} a_i^r x^r.  Uniformly choose five generator labels and,
independently of all per-generator data, choose two positive and three negative
signs.  Let q_i be the corresponding +(1+x) or -(1+x), and only then form
T=sum q_i f_i.  Thus the certificate is known by inverse generation, not by
solving T.  The nodes are all drawn before the planted support, so plants and
decoys have exactly the same marginal distribution.

Why the shortcut works.  Dividing T by 1+x gives moments
s_r=sum epsilon_i a_i^r.  A five-term exponential sequence obeys the order-five
linear recurrence whose characteristic polynomial is prod(z-a_i).  Ten moments
determine that recurrence exactly.  Its constant coefficient is the product of
five primes from the printed node list, so trial division identifies the roots;
s_1 then identifies the positive pair.  This costs at most 231 exact arithmetic
operations at shipping n=80.  In contrast, the reference
positive-pair/negative-triple meet-in-the-middle search performs hundreds of
thousands of exact additions.

Attacks.  The outlier probe chooses the five largest nodes, the greedy probe
locally reduces the first-moment residual, the by-hand probe tries all ten sign
patterns on the first five printed nodes, and the restart probe draws 256 times
from the exact bounded language.  None is allowed to solve any of eight shipping
seeds.  The reference meet-in-the-middle algorithm is reported separately and
is expected to solve every seed because this is Track B.
""".strip()


_SUPPORT = 5
_POSITIVE = 2
_MILLER_RABIN_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)


def _plain_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value: int) -> bool:
    """Deterministic primality test for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value % p == 0:
            return value == p
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in _MILLER_RABIN_BASES:
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


def _next_primes(start: int, count: int) -> list[int]:
    value = max(2, start)
    out = []
    if value <= 2:
        out.append(2)
        value = 3
    if value % 2 == 0:
        value += 1
    while len(out) < count:
        if _is_prime(value):
            out.append(value)
        value += 2
    return out


def _poly_json(sign: int) -> list:
    """Coefficient-first JSON for sign*(1+x)."""
    return [
        [[sign, 1], [0]],
        [[sign, 1], [1]],
    ]


def _certificate(positive, negative) -> list:
    signs = {int(i): 1 for i in positive}
    signs.update({int(i): -1 for i in negative})
    return [[i + 1, _poly_json(signs[i])] for i in sorted(signs)]


def _moments(nodes, signed_indices, count: int) -> list[int]:
    values = [0] * count
    for idx, sign in signed_indices:
        power = 1
        a = nodes[idx]
        for r in range(count):
            values[r] += sign * power
            power *= a
    return values


def _multiply_one_plus_x(coeffs: list[int]) -> list[int]:
    out = [0] * (len(coeffs) + 1)
    for i, value in enumerate(coeffs):
        out[i] += value
        out[i + 1] += value
    return out


def _validate_params(n: int, moment_count: int, prime_min: int,
                     prime_span: int) -> None:
    vals = (n, moment_count, prime_min, prime_span)
    if not all(_plain_int(v) for v in vals):
        raise TypeError("all parameters must be genuine integers")
    if n < _SUPPORT:
        raise ValueError("n must be at least 5")
    if moment_count < 2 * _SUPPORT:
        raise ValueError("moment_count must be at least 10")
    if prime_min < 2 or prime_span < 1:
        raise ValueError("prime_min >= 2 and prime_span >= 1 are required")
    if prime_min + prime_span >= 2**63:
        raise ValueError("the deterministic primality range must stay below 2^63")


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a sparse polynomial standard representation."""
    moment_count = params.pop("moment_count", 10)
    prime_min = params.pop("prime_min", 10_000)
    prime_span = params.pop("prime_span", 50_000)
    if params:
        raise TypeError("unknown make_instance parameters: " + ", ".join(sorted(params)))
    if not _plain_int(seed):
        raise TypeError("seed must be an integer")
    _validate_params(n, moment_count, prime_min, prime_span)

    rng = random.Random(seed)
    start = prime_min + rng.randrange(prime_span)
    nodes = _next_primes(start, n)
    rng.shuffle(nodes)

    support = sorted(rng.sample(range(n), _SUPPORT))
    positive = set(rng.sample(support, _POSITIVE))
    negative = [i for i in support if i not in positive]
    signed = [(i, 1 if i in positive else -1) for i in support]
    base = _moments(nodes, signed, moment_count)
    target = _multiply_one_plus_x(base)

    return {
        "n": n,
        "moment_count": moment_count,
        "nodes": nodes,
        "target_coefficients": target,
        "multiplier": _poly_json(1),
        "support_size": _SUPPORT,
        "positive_count": _POSITIVE,
        "answer": _certificate(sorted(positive), negative),
    }


def _human_poly(coeffs: list[int]) -> str:
    pieces = []
    for degree in range(len(coeffs) - 1, -1, -1):
        value = coeffs[degree]
        if value == 0:
            continue
        magnitude = abs(value)
        if degree == 0:
            body = str(magnitude)
        elif degree == 1:
            body = "x" if magnitude == 1 else f"{magnitude}*x"
        else:
            body = f"x^{degree}" if magnitude == 1 else f"{magnitude}*x^{degree}"
        if not pieces:
            pieces.append(("-" if value < 0 else "") + body)
        else:
            pieces.append((" - " if value < 0 else " + ") + body)
    return "".join(pieces) if pieces else "0"


def render(inst) -> str:
    """Render the complete self-contained solver prompt."""
    n = inst["n"]
    m = inst["moment_count"]
    nodes = ", ".join(f"{i + 1}:{a}" for i, a in enumerate(inst["nodes"]))
    target = ", ".join(str(c) for c in inst["target_coefficients"])
    example = (
        '[[1,[[[1,1],[0]],[[1,1],[1]]]],'
        '[2,[[[-1,1],[0]],[[-1,1],[1]]]],'
        '[3,[[[1,1],[0]],[[1,1],[1]]]],'
        '[4,[[[-1,1],[0]],[[-1,1],[1]]]],'
        '[5,[[[-1,1],[0]],[[-1,1],[1]]]]]'
    )
    statement = f"""Work in the integer polynomial ring Z[x].

There are {n} generators.  Generator i has the printed positive integer node a_i and is

    f_i(x) = sum from r=0 through r={m - 1} of a_i^r x^r.

Generator labels are 1-based.  Here are all label:node pairs; their printed order is part of the instance:
{nodes}

The target is T(x)=sum from r=0 through r={m} of t_r x^r.  Its coefficients are listed in ascending degree order [t_0,t_1,...,t_{m}]:
[{target}]

Find a sparse standard representation T(x)=sum_i q_i(x)f_i(x) with exactly five nonzero multipliers.  Each q_i must be +(1+x) or -(1+x), exactly two must be positive and three negative, and the five distinct entries must be sorted by increasing generator label.  No other generators are implicitly present.

Encode the answer as JSON.  Each entry is [generator_label, polynomial].  A polynomial is a list of [coefficient, exponent-list] terms in ascending exponent order; an exact rational coefficient is [numerator,denominator], and this problem has the single-variable exponent lists [0] and [1].

Give your final answer inside <answer></answer> tags, in exactly this JSON format:
<answer>{example}</answer>
The displayed JSON is only a syntax example, not the solution.  Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Extract the JSON certificate from tags, a fence, or surrounding prose."""
    if not isinstance(text, str):
        return None
    candidates = []
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    candidates.extend(reversed(tagged))
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text,
                        flags=re.IGNORECASE | re.DOTALL)
    candidates.extend(reversed(fenced))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        sample = candidate.strip()
        try:
            obj = json.loads(sample)
            if isinstance(obj, list):
                return obj
        except (TypeError, ValueError):
            pass
        for match in re.finditer(r"\[", sample):
            try:
                obj, _ = decoder.raw_decode(sample[match.start():])
            except ValueError:
                continue
            if isinstance(obj, list):
                return obj
    return None


def _decode_multiplier(obj):
    """Return +1/-1 for exactly +/- (1+x), else None."""
    if not isinstance(obj, list) or len(obj) != 2:
        return None
    decoded = []
    for degree, term in enumerate(obj):
        if not isinstance(term, list) or len(term) != 2:
            return None
        coeff, exponents = term
        if not isinstance(coeff, list) or len(coeff) != 2:
            return None
        num, den = coeff
        if not _plain_int(num) or not _plain_int(den):
            return None
        if den != 1 or num not in (-1, 1):
            return None
        q = Fraction(num, den)
        if exponents != [degree]:
            return None
        decoded.append(q)
    if decoded == [Fraction(1), Fraction(1)]:
        return 1
    if decoded == [Fraction(-1), Fraction(-1)]:
        return -1
    return None


def _gv_poly_from_coeffs(coeffs):
    return {(i,): Fraction(c) for i, c in enumerate(coeffs) if c}


def _exact_identity_with_gvlib(inst, signed) -> bool:
    """Final exact expansion, using gvlib when present and an integer fallback."""
    if sparse_poly is None:
        base = _moments(inst["nodes"], signed, inst["moment_count"])
        return _multiply_one_plus_x(base) == inst["target_coefficients"]
    total = {}
    for idx, sign in signed:
        a = inst["nodes"][idx]
        generator = _gv_poly_from_coeffs([a**r for r in range(inst["moment_count"])])
        multiplier = {(0,): Fraction(sign), (1,): Fraction(sign)}
        total = sparse_poly.add(total, sparse_poly.mul(multiplier, generator))
    target = _gv_poly_from_coeffs(inst["target_coefficients"])
    return sparse_poly.equal(total, target)


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any bounded sparse standard representation; never read the plant."""
    if not isinstance(answer, list) or not answer:
        return False, "answer must be a nonempty JSON list"
    if len(answer) != inst.get("support_size", _SUPPORT):
        return False, "expected exactly five certificate entries"

    indices = []
    signed = []
    for entry in answer:
        if not isinstance(entry, list) or len(entry) != 2:
            return False, "each certificate entry must be [generator, polynomial]"
        idx, poly = entry
        if not _plain_int(idx) or not 1 <= idx <= inst["n"]:
            return False, "generator label is outside the inclusive range 1..n"
        sign = _decode_multiplier(poly)
        if sign is None:
            return False, "each multiplier must be exactly +(1+x) or -(1+x)"
        indices.append(idx)
        signed.append((idx - 1, sign))

    if len(set(indices)) != len(indices):
        return False, "generator labels must be distinct"
    if indices != sorted(indices):
        return False, "certificate entries must be sorted by generator label"
    if sum(sign > 0 for _, sign in signed) != inst.get("positive_count", _POSITIVE):
        return False, "exactly two multipliers must be positive"

    # A cheap exact prefix rejection keeps the 200k structure-aware density
    # samples fast; a survivor is still checked by full exact polynomial algebra.
    for r in range(inst["moment_count"]):
        got = sum(sign * inst["nodes"][idx] ** r for idx, sign in signed)
        target = inst["target_coefficients"]
        expected = target[0] if r == 0 else target[r] - (
            sum(sign * inst["nodes"][idx] ** (r - 1) for idx, sign in signed)
        )
        if got != expected:
            return False, f"polynomial identity fails at quotient coefficient x^{r}"

    if not _exact_identity_with_gvlib(inst, signed):
        return False, "expanded polynomial identity does not equal the target"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniform candidate after all stated shape and sign constraints."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    support = sorted(rng.sample(range(inst["n"]), inst["support_size"]))
    positive = set(rng.sample(support, inst["positive_count"]))
    negative = [i for i in support if i not in positive]
    return _certificate(sorted(positive), negative)


def search_space(inst) -> int | None:
    """Size of the exact structure-aware bounded certificate language."""
    n = inst["n"]
    k = inst["support_size"]
    p = inst["positive_count"]
    return math.comb(n, k) * math.comb(k, p)


def enumerate_all(inst) -> int | None:
    """Brute-force the language only when it has at most 200,000 elements."""
    if search_space(inst) > 200_000:
        return None
    valid = 0
    for support in itertools.combinations(range(inst["n"]), inst["support_size"]):
        for positive in itertools.combinations(support, inst["positive_count"]):
            pos = set(positive)
            answer = _certificate(positive, [i for i in support if i not in pos])
            if verify(inst, answer)[0]:
                valid += 1
    return valid


def canonical_key(inst) -> str:
    """Invariant under arbitrary reordering/renumbering of the generators."""
    canonical = {
        "nodes": sorted(inst["nodes"]),
        "target": inst["target_coefficients"],
        "moment_count": inst["moment_count"],
        "support_size": inst["support_size"],
        "positive_count": inst["positive_count"],
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow the node haystack, then coefficient sizes, at fixed answer length."""
    out = dict(params)
    out.pop("_preset", None)
    n = int(out.get("n", 128))
    if n < 144:
        out["n"] = min(144, n + 16)
        out["prime_min"] = int(out.get("prime_min", 10_000)) * 2
        out["prime_span"] = int(out.get("prime_span", 50_000)) * 2
        return out
    prime_min = int(out.get("prime_min", 10_000))
    prime_span = int(out.get("prime_span", 50_000))
    if prime_min < 2**59 and prime_min * 4 + prime_span * 2 < 2**63:
        out["prime_min"] = prime_min * 4
        out["prime_span"] = prime_span * 2
        return out
    return None


def _quotient_moments(inst) -> list[int] | None:
    """Exact synthetic division of T by 1+x."""
    target = inst["target_coefficients"]
    if len(target) != inst["moment_count"] + 1:
        return None
    out = [target[0]]
    for r in range(1, inst["moment_count"]):
        out.append(target[r] - out[-1])
    if target[-1] != out[-1]:
        return None
    return out


def _reference_meet_in_middle(inst, with_count=False):
    """Domain-standard exact positive-pair/negative-triple attack."""
    moments = _quotient_moments(inst)
    if moments is None:
        return None, 0, 0
    nodes = inst["nodes"]
    n = len(nodes)
    squares = [a * a for a in nodes]
    operations = n
    pair_by_moments = {}
    for i in range(n - 1):
        ai, ai2 = nodes[i], squares[i]
        for j in range(i + 1, n):
            key = (ai + nodes[j], ai2 + squares[j])
            operations += 2
            pair_by_moments[key] = (i, j)
    triples = 0
    for i in range(n - 2):
        for j in range(i + 1, n - 1):
            for k in range(j + 1, n):
                triples += 1
                neg1 = nodes[i] + nodes[j] + nodes[k]
                neg2 = squares[i] + squares[j] + squares[k]
                key = (moments[1] + neg1, moments[2] + neg2)
                operations += 6
                pair = pair_by_moments.get(key)
                if pair is None or pair[0] in (i, j, k) or pair[1] in (i, j, k):
                    continue
                answer = _certificate(pair, (i, j, k))
                if verify(inst, answer)[0]:
                    return answer, operations, triples
    return None, operations, triples


def _fraction_solve_count(A, b):
    """Exact square solve plus a conservative arithmetic-operation count."""
    n = len(A)
    M = [[Fraction(value) for value in row] + [Fraction(b[i])]
         for i, row in enumerate(A)]
    operations = n                 # the n right-hand-side negations upstream
    for col in range(n):
        pivot = next((r for r in range(col, n) if M[r][col]), None)
        if pivot is None:
            return None, operations
        if pivot != col:
            M[col], M[pivot] = M[pivot], M[col]
        for row in range(col + 1, n):
            factor = M[row][col] / M[col][col]
            operations += 1
            for j in range(col + 1, n + 1):
                M[row][j] -= factor * M[col][j]
                operations += 2
            M[row][col] = Fraction(0)
    x = [Fraction(0)] * n
    for row in range(n - 1, -1, -1):
        value = M[row][n]
        for j in range(row + 1, n):
            value -= M[row][j] * x[j]
            operations += 2
        x[row] = value / M[row][row]
        operations += 1
    return x, operations


def _compact_annihilator_solver(inst):
    """The intended Prony/Newton-style route, with exact operation accounting."""
    moments = _quotient_moments(inst)
    if moments is None or len(moments) < 2 * _SUPPORT:
        return None, 0
    # Recovering the quotient uses nine subtractions for ten moments.  The
    # final equality test is a comparison, not arithmetic.
    operations = inst["moment_count"] - 1
    A = [[moments[r + j] for j in range(_SUPPORT)]
         for r in range(_SUPPORT)]
    b = [-moments[r + _SUPPORT] for r in range(_SUPPORT)]
    coeffs, solve_ops = _fraction_solve_count(A, b)
    operations += solve_ops
    if coeffs is None or any(c.denominator != 1 for c in coeffs):
        return None, operations

    # P(z)=z^5+c4*z^4+...+c0.  Its constant coefficient is minus the
    # product of the five positive-prime roots.  Trial division by the printed
    # prime nodes avoids evaluating P at all n nodes.
    remaining = abs(coeffs[0].numerator)
    root_indices = []
    for idx, node in enumerate(inst["nodes"]):
        operations += 1             # remaining % node
        if remaining % node == 0:
            remaining //= node
            operations += 1
            root_indices.append(idx)
    if remaining != 1 or len(root_indices) != _SUPPORT:
        return None, operations

    root_sum = 0
    for idx in root_indices:
        root_sum += inst["nodes"][idx]
        operations += 1
    # s1 = sum(positive roots)-sum(negative roots), so the positive-pair
    # sum is (s1 + sum(all roots))/2.
    wanted = moments[1] + root_sum
    operations += 1
    if wanted % 2:
        return None, operations
    wanted //= 2
    operations += 1
    positive = None
    for pair in itertools.combinations(root_indices, _POSITIVE):
        operations += 1             # one pair sum
        if inst["nodes"][pair[0]] + inst["nodes"][pair[1]] == wanted:
            positive = set(pair)
            break
    if positive is None:
        return None, operations
    negative = [i for i in root_indices if i not in positive]
    answer = _certificate(sorted(positive), negative)
    if not verify(inst, answer)[0]:
        return None, operations
    return answer, operations


def _best_signs_for_support(inst, support):
    moments = _quotient_moments(inst)
    target1 = moments[1]
    best = None
    for pos in itertools.combinations(support, _POSITIVE):
        pset = set(pos)
        value = sum(inst["nodes"][i] if i in pset else -inst["nodes"][i]
                    for i in support)
        score = abs(value - target1)
        if best is None or score < best[0]:
            best = (score, pos)
    positive = set(best[1])
    return _certificate(sorted(positive), [i for i in support if i not in positive])


def _attack_outlier(inst):
    support = sorted(range(inst["n"]), key=lambda i: inst["nodes"][i], reverse=True)[:5]
    return _best_signs_for_support(inst, sorted(support))


def _attack_first_five(inst):
    return _best_signs_for_support(inst, list(range(5)))


def _attack_greedy(inst):
    moments = _quotient_moments(inst)
    residual = moments[1]
    unused = set(range(inst["n"]))
    chosen = []
    positives_left, negatives_left = _POSITIVE, _SUPPORT - _POSITIVE
    for _ in range(_SUPPORT):
        options = []
        for idx in unused:
            if positives_left:
                options.append((abs(residual - inst["nodes"][idx]), idx, 1))
            if negatives_left:
                options.append((abs(residual + inst["nodes"][idx]), idx, -1))
        _, idx, sign = min(options)
        chosen.append((idx, sign))
        unused.remove(idx)
        residual -= sign * inst["nodes"][idx]
        positives_left -= sign == 1
        negatives_left -= sign == -1
    pos = [i for i, sign in chosen if sign == 1]
    neg = [i for i, sign in chosen if sign == -1]
    return _certificate(pos, neg)


def _permute_instance(inst, new_to_old):
    """Reorder generators and carry a certificate through the relabelling."""
    old_to_new = {old: new for new, old in enumerate(new_to_old)}
    answer = []
    for old_label, poly in inst["answer"]:
        answer.append([old_to_new[old_label - 1] + 1, json.loads(json.dumps(poly))])
    answer.sort(key=lambda entry: entry[0])
    transformed = dict(inst)
    transformed["nodes"] = [inst["nodes"][old] for old in new_to_old]
    transformed["answer"] = answer
    return transformed


def _answer_atoms(obj) -> int:
    if isinstance(obj, dict):
        return sum(_answer_atoms(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_answer_atoms(v) for v in obj)
    return 1


def selftest() -> dict:
    """Run and report all mandatory correctness and hardness gates."""
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, several independent seeds.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "checks": g1_checks, "failures": g1_failures,
    }

    # G2: malformed/corrupted answers reach distinct rejection paths.
    inst = make_instance(seed=73, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = json.loads(json.dumps(inst["answer"]))
    corruptions = {}
    corruptions["empty"] = []
    corruptions["drop_one"] = planted[:-1]
    swapped = json.loads(json.dumps(planted))
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap_order"] = swapped
    duplicate = json.loads(json.dumps(planted))
    duplicate[1][0] = duplicate[0][0]
    corruptions["duplicate_label"] = duplicate
    outside = json.loads(json.dumps(planted))
    outside[-1][0] = inst["n"] + 1
    corruptions["out_of_range"] = outside
    bad_poly = json.loads(json.dumps(planted))
    bad_poly[0][1][0][0] = [0, 1]
    corruptions["bad_multiplier"] = bad_poly
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
                and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose/fence/tags and direct answer round trips.
    blob = json.dumps(inst["answer"], separators=(",", ":"))
    realistic = "I used the recurrence.\n```json\n<answer>\n" + blob + "\n</answer>\n```\n"
    parsed = parse_answer(realistic)
    direct = parse_answer("<answer>" + blob + "</answer>")
    garbage = parse_answer("No certificate was found.")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and direct == inst["answer"] and garbage is None,
        "prose_round_trip": parsed == inst["answer"],
        "direct_round_trip": direct == inst["answer"],
        "garbage_returns_none": garbage is None,
    }

    # G4/G5 share the mandated 200k shipping-preset structure-aware sample.
    density_inst = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    samples = 200_000
    hits = 0
    guess_rng = random.Random(0x160904257)
    t0 = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(density_inst, guess_rng)
        hits += bool(verify(density_inst, candidate)[0])
    density_seconds = time.perf_counter() - t0
    space = search_space(density_inst)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": space,
        "theoretical_probability_unique_answer": 1 / space,
        "sampling_wall_clock_sec": round(density_seconds, 6),
    }

    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline_inst = make_instance(seed=8101, **DIFFICULTY[SHIPPING_DIFFICULTY])
    t0 = time.perf_counter()
    baseline_answer, baseline_ops, baseline_triples = _reference_meet_in_middle(
        baseline_inst, with_count=True)
    baseline_seconds = time.perf_counter() - t0
    baseline_ok = baseline_answer is not None and verify(baseline_inst, baseline_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits / samples < 1e-6 and baseline_ok,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": hits / samples,
        "shipping_theoretical_valid_answers": 1,
        "shipping_theoretical_solution_fraction": 1 / space,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "baseline_exact_operations": baseline_ops,
        "baseline_triples_examined": baseline_triples,
        "baseline_verified": baseline_ok,
    }

    compact_successes = 0
    compact_ops = []
    for seed in range(8):
        compact_inst = make_instance(seed=18_000 + seed,
                                     **DIFFICULTY[SHIPPING_DIFFICULTY])
        compact_answer, used = _compact_annihilator_solver(compact_inst)
        compact_successes += bool(
            compact_answer is not None and verify(compact_inst, compact_answer)[0]
        )
        compact_ops.append(used)
    report["G5_density_and_baseline"]["compact_route_solves"] = (
        f"{compact_successes}/8"
    )
    report["G5_density_and_baseline"]["compact_route_operations_max"] = max(compact_ops)
    report["G5_density_and_baseline"]["pass"] = (
        report["G5_density_and_baseline"]["pass"]
        and compact_successes == 8 and max(compact_ops) <= 284
    )

    # G6: four deliberately cheap failing attacks and the successful Track-B reference.
    attack_names = (
        "outlier_five_largest_nodes",
        "greedy_first_moment_residual",
        "random_restart_256",
        "by_hand_first_five_signs",
    )
    successes = {name: 0 for name in attack_names}
    attempts = 8
    reference_successes = 0
    reference_ops = []
    reference_times = []
    reference_triples = []
    for trial in range(attempts):
        probe = make_instance(seed=31_000 + trial,
                              **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in (
            (attack_names[0], _attack_outlier(probe)),
            (attack_names[1], _attack_greedy(probe)),
            (attack_names[3], _attack_first_five(probe)),
        ):
            successes[name] += bool(verify(probe, candidate)[0])
        rrng = random.Random(91_000 + trial)
        restart_hit = False
        for _ in range(256):
            if verify(probe, random_candidate(probe, rrng))[0]:
                restart_hit = True
                break
        successes[attack_names[2]] += restart_hit

        t0 = time.perf_counter()
        ref, ops, triples = _reference_meet_in_middle(probe, with_count=True)
        reference_times.append(time.perf_counter() - t0)
        reference_ops.append(ops)
        reference_triples.append(triples)
        reference_successes += bool(ref is not None and verify(probe, ref)[0])

    attacks = {
        name: {"successes": successes[name], "attempts": attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact positive-pair/negative-triple meet-in-the-middle",
            "complexity": "O(n^3) integer additions and O(n^2) stored pairs",
            "wall_clock_sec_mean": round(sum(reference_times) / attempts, 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": sum(reference_ops) // attempts,
            "triples_examined_mean": sum(reference_triples) // attempts,
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    # G7: n doubles while the five-polynomial witness stays fixed.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    t0 = time.perf_counter()
    doubled = make_instance(seed=404, **doubled_params)
    doubled_seconds = time.perf_counter() - t0
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["answer"]) == _SUPPORT,
        "shipping_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_n": doubled_params["n"],
        "doubled_build_wall_clock_sec": round(doubled_seconds, 6),
        "doubled_verification_reason": doubled_why,
        "answer_entries_unchanged": len(doubled["answer"]),
    }

    # G8: reverse, rotate, random permutation, and a composition over 20 seeds.
    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        original = make_instance(seed=70_000 + seed,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])
        keys.append(canonical_key(original))
        n = original["n"]
        reverse = list(reversed(range(n)))
        shift = (seed * 7 + 3) % n
        rotate = list(range(shift, n)) + list(range(shift))
        random_perm = list(range(n))
        random.Random(80_000 + seed).shuffle(random_perm)
        composition = [reverse[rotate[i]] for i in range(n)]
        for perm in (reverse, rotate, random_perm, composition):
            moved = _permute_instance(original, perm)
            invariant_checks += canonical_key(moved) == canonical_key(original)
            carried_checks += verify(moved, moved["answer"])[0]
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80 and carried_checks == 80 and distinct == 20,
        "invariance_passed": invariant_checks,
        "invariance_attempts": 80,
        "carried_witness_passed": carried_checks,
        "carried_witness_attempts": 80,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "symmetries_tested": [
            "generator reversal", "cyclic reordering", "random reordering",
            "composition of reversal and cyclic reordering",
        ],
    }

    # G9: oracle arms are diagnostic; only exact size/effort caps gate.
    max_chars = max_atoms = max_tokens = 0
    for seed in range(64):
        sample = make_instance(seed=90_000 + seed,
                               **DIFFICULTY[SHIPPING_DIFFICULTY])
        encoded = json.dumps(sample["answer"], separators=(",", ":"))
        max_chars = max(max_chars, len(encoded))
        max_atoms = max(max_atoms, _answer_atoms(sample["answer"]))
        max_tokens = max(max_tokens, (len(encoded) + 3) // 4)
    intended_ops = max(compact_ops)
    within_caps = max_chars <= 2_000 and max_atoms <= 256 and intended_ops <= 300
    hinted = G9_EVIDENCE["hinted"]
    placebo = G9_EVIDENCE["placebo"]
    h_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    p_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(G9_EVIDENCE["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": h_rate - p_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": max_chars,
        "answer_tokens": max_tokens,
        "answer_elements": max_atoms,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
