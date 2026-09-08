"""Track-B exact Gram-spectrum generator for arXiv:1809.05739.

Section 6, Construction 6.1 and Theorem 6.2 turn every two-intersection
block set satisfying Delta_1 >= 0 into equiangular Euclidean lines.  We use
subsets of the affine lines in F_q^2: parallel blocks are disjoint and
nonparallel blocks meet once.  The requested certificate is a compact exact
factorization of the characteristic polynomial of the resulting scaled Gram
matrix.

The generator samples the affine blocks first and obtains the characteristic
polynomial from their known parallel-class decomposition.  It never runs a
characteristic-polynomial algorithm to discover its planted certificate.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The implementation below remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"
STEP4_STATUS = "hardened"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "two-intersection block set in an affine plane",
        "exact scaled Gram matrix of equiangular Euclidean lines",
        "characteristic polynomial over Q",
    ],
    "verification_operations": [
        "exact finite-field proportionality and block-intersection checks",
        "exact integer polynomial multiplication and coefficient comparison",
        "exact rational normalization of polynomial terms",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize that the exact Gram matrix is constant on hidden parallel "
        "classes, splitting off their zero-sum subspaces; without that "
        "decomposition one computes a large characteristic polynomial."
    ),
    "hardness_basis": (
        "Track B: the classical Faddeev-LeVerrier characteristic-polynomial "
        "algorithm with schoolbook exact matrix products costs O(N^4) and used "
        "222,948,182 counted exact operations (19.33 seconds in the final selftest) on the measured "
        "shipping instance; the parallel-class decomposition used a conservative "
        "824-operation bound on the reference instance."
    ),
    "max_answer_tokens": 96,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is a lower bound for the prime field order.  The witness degree is governed
# by classes and stays small while the Gram matrix order grows with n.
DIFFICULTY = {
    "demo": {"n": 3, "classes": 3, "min_class": 2},
    "easy": {"n": 17, "classes": 7, "min_class": 8, "max_class": 17},
    "medium": {"n": 23, "classes": 7, "min_class": 11, "max_class": 23},
    "hard": {"n": 1_000_000, "classes": 7,
             "min_class": 11, "max_class": 23},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: The exact Gram matrix is constant on the parallel classes of the "
    "affine blocks."
)
PLACEBO_HINT = (
    "Hint: The exact Gram computation rewards careful handling of the modular "
    "line representatives."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON factorization of det(xI-G) into exactly one monic integer "
        "linear factor of the stated multiplicity N-r and one monic degree-r "
        "integer polynomial. Polynomial terms are [[num,den],[exponent]], "
        "with nonnegative exponent, positive denominator, and the coefficient "
        "height bound H shown in the instance. The leading and trace "
        "coefficients and alternating signs forced by positive semidefiniteness "
        "are built into the random-candidate prior. search_space counts the "
        "canonical normalized coefficient-vector representatives sampled by "
        "random_candidate; verify also accepts equivalent term/factor orderings."
    ),
    "bounds": {
        "number_of_factors": 2,
        "bulk_factor_degree": 1,
        "residual_degree": "r = classes (7 at the initial shipping preset)",
        "bulk_root_range": "0 <= z <= floor(trace(G)/(N-r))",
        "coefficient_height": "H = (2(N+2q))^r",
        "rational_denominators": 1,
        "shipping_atomic_elements_upper_bound": 64,
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Section 2.1 fixes a block set and quasi-symmetric design as families of
fixed-size subsets with prescribed intersection sizes.  Section 6 is the
load-bearing part: Construction 6.1 assigns a Euclidean vector v(B) to each
block, and Theorem 6.2 proves that a (d,k;s1,s2) block set with
Delta_1=k^2-d(s1+s2)/2 >= 0 gives equiangular lines of common angle
(s1-s2)/(2k-s1-s2).

Here the points are F_q^2 and each block is an affine line ax+by=c.  Each has
k=q points; distinct blocks intersect in s1=1 or s2=0 points; d=q^2; and
Delta_1=q^2/2.  Scaling the theorem's Gram matrix by 2/q^4 gives the exact
integer matrix G used in the question: diagonal 2q-1, +1 for intersecting
blocks, and -1 for disjoint blocks.  Independent orientation signs conjugate
G by a diagonal sign matrix and do not alter its characteristic polynomial.

Theorem 1.1 classifies only the absolute-bound examples in dimensions
2,3,7,23, while Examples 6.3--6.6 show both the power and the dimension limits
of special block families.  To obtain an unlimited family without pretending
that the finite classified configurations scale, this module uses the general
Theorem 6.2 rather than the maximal examples or the open classifications in
Problems 10.1 and 10.2.

Track A would be false.  A characteristic polynomial is produced by a
polynomial-time exact linear-algebra algorithm.  The reference implementation
is Faddeev-LeVerrier with exact schoolbook matrix powers.  Track B measures the
compression gap: if the parallel-class sizes are t_i, G has eigenvalue 2q on
every within-class zero-sum vector, and its remaining characteristic factor is
  product_i (x-2q+2t_i)
  - sum_i t_i product_{j != i} (x-2q+2t_j).
The generator uses this identity by construction; it never extracts a spectrum
from the completed Gram matrix.

The attack panel tries a line-coefficient outlier, a diagonal-only greedy
spectrum, a trace-only equal-residual-root ansatz, and 256 structure-aware
random restarts.  Random equation scalings, line order, directions, intercepts,
and vector orientations remove representation outliers.  canonical_key ignores
exactly those transformations and retains q plus the multiset of parallel-class
sizes, which completely determines G up to signed permutation similarity.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_ENUMERATION_CAP = 200_000


def _is_prime(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    # Deterministic Miller-Rabin for unsigned 64-bit integers.
    if value >= 2**64:
        return False
    odd_part, twos = value - 1, 0
    while odd_part % 2 == 0:
        odd_part //= 2
        twos += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        witness = pow(base, odd_part, value)
        if witness in (1, value - 1):
            continue
        for _ in range(twos - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value):
    if value >= 2**64 - 1000:
        raise ValueError("n is too large for deterministic 64-bit primality")
    candidate = max(2, value)
    if candidate > 2 and candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 1 if candidate == 2 else 2
    return candidate


def _validate_params(n, classes, min_class, max_class):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    q = _next_prime(n)
    if (isinstance(classes, bool) or not isinstance(classes, int)
            or classes < 3 or classes > q + 1):
        raise ValueError("classes must be an integer between 3 and q+1")
    if (isinstance(min_class, bool) or not isinstance(min_class, int)
            or min_class < 2 or min_class > q):
        raise ValueError("min_class must be an integer between 2 and q")
    if (isinstance(max_class, bool) or not isinstance(max_class, int)
            or max_class < min_class or max_class > q):
        raise ValueError("max_class must be an integer between min_class and q")
    return q


def _poly_mul(left, right, counter=None):
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if a == 0:
            continue
        for j, b in enumerate(right):
            if b == 0:
                continue
            out[i + j] += a * b
            if counter is not None:
                counter[0] += 2
    return out


def _trim(coefficients):
    out = list(coefficients)
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out or [0]


def _residual_polynomial(q, sizes, counter=None):
    """Low-degree-first residual factor from the determinant lemma."""
    factors = [[-2 * q + 2 * size, 1] for size in sizes]
    r = len(factors)
    prefix = [[1]]
    for factor in factors:
        prefix.append(_poly_mul(prefix[-1], factor, counter))
    suffix = [None] * (r + 1)
    suffix[r] = [1]
    for index in range(r - 1, -1, -1):
        suffix[index] = _poly_mul(factors[index], suffix[index + 1], counter)
    result = prefix[-1][:]
    for index, size in enumerate(sizes):
        omitted = _poly_mul(prefix[index], suffix[index + 1], counter)
        for degree, coefficient in enumerate(omitted):
            result[degree] -= size * coefficient
            if counter is not None and coefficient:
                counter[0] += 2
    return _trim(result)


def _poly_json(coefficients):
    return [[[int(coefficient), 1], [degree]]
            for degree, coefficient in enumerate(coefficients)]


def _certificate(q, sizes):
    sizes = sorted(sizes)
    count = sum(sizes)
    classes = len(sizes)
    return {
        "factors": [
            {
                "poly": [[[-2 * q, 1], [0]], [[1, 1], [1]]],
                "multiplicity": count - classes,
            },
            {
                "poly": _poly_json(_residual_polynomial(q, sizes)),
                "multiplicity": 1,
            },
        ]
    }


def _direction(normal_a, normal_b, q):
    if normal_a % q:
        inverse = pow(normal_a % q, -1, q)
        return (1, normal_b * inverse % q)
    if normal_b % q:
        return (0, 1)
    raise ValueError("zero normal")


def _normalized_line(record, q):
    a, b, c, sign = record
    if a % q:
        inverse = pow(a % q, -1, q)
    else:
        inverse = pow(b % q, -1, q)
    return (a * inverse % q, b * inverse % q, c * inverse % q, sign)


def _recover_sizes(inst):
    """Validate the affine block set and recover its parallel-class sizes."""
    if not isinstance(inst, dict):
        return None, "instance must be a dictionary"
    q = inst.get("q")
    lines = inst.get("lines")
    classes = inst.get("classes")
    if not _is_prime(q):
        return None, "q must be prime"
    if not isinstance(lines, list) or not lines:
        return None, "instance lines must be a nonempty list"
    if isinstance(classes, bool) or not isinstance(classes, int) or classes < 3:
        return None, "instance class count is invalid"
    groups = {}
    seen_lines = set()
    for index, record in enumerate(lines):
        if (not isinstance(record, list) or len(record) != 4
                or any(isinstance(value, bool) or not isinstance(value, int)
                       for value in record)):
            return None, f"line {index} must be [a,b,c,sign] with integers"
        a, b, c, sign = record
        if not (0 <= a < q and 0 <= b < q and 0 <= c < q):
            return None, f"line {index} has a coefficient outside 0..q-1"
        if sign not in (-1, 1):
            return None, f"line {index} orientation is not -1 or 1"
        if a == 0 and b == 0:
            return None, f"line {index} has zero normal"
        normalized = _normalized_line(record, q)
        identity = normalized[:3]
        if identity in seen_lines:
            return None, "the block set contains a repeated affine line"
        seen_lines.add(identity)
        groups.setdefault(identity[:2], []).append(normalized[2])
    if len(groups) != classes:
        return None, "declared class count disagrees with the affine lines"
    sizes = sorted(len(values) for values in groups.values())
    if any(size < 1 or size > q for size in sizes):
        return None, "a parallel class has an impossible size"
    if not any(size >= 2 for size in sizes):
        return None, "the block set has no disjoint block pair"
    if classes < 2:
        return None, "the block set has no intersecting block pair"
    if inst.get("N") != len(lines):
        return None, "declared Gram order N disagrees with the line list"
    return sizes, "ok"


def make_instance(n, seed=0, **params):
    """Construct a certified affine-block Gram instance without solving it."""
    q_guess = _next_prime(n)
    classes = params.pop("classes", min(7, q_guess + 1))
    min_class = params.pop("min_class", None)
    max_class = params.pop("max_class", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if min_class is None:
        min_class = max(2, q_guess // 2)
    if max_class is None:
        max_class = q_guess
    q = _validate_params(n, classes, min_class, max_class)
    rng = random.Random(seed)

    sizes = [rng.randint(min_class, max_class) for _ in range(classes)]
    directions = rng.sample(range(q + 1), classes)
    records = []
    for direction_code, size in zip(directions, sizes):
        normal = ((1, direction_code) if direction_code < q else (0, 1))
        intercepts = rng.sample(range(q), size)
        for intercept in intercepts:
            scalar = rng.randrange(1, q)
            records.append([
                scalar * normal[0] % q,
                scalar * normal[1] % q,
                scalar * intercept % q,
                rng.choice((-1, 1)),
            ])
    rng.shuffle(records)
    answer = _certificate(q, sizes)
    return {
        "n": n,
        "q": q,
        "dimension": q * q,
        "block_size": q,
        "intersection_sizes": [1, 0],
        "classes": classes,
        "min_class": min_class,
        "max_class": max_class,
        "N": len(records),
        "lines": records,
        "coefficient_height": (2 * (len(records) + 2 * q)) ** classes,
        "answer": answer,
    }


def render(inst):
    """Render a self-contained exact Gram characteristic-polynomial task."""
    rows = "\n".join(
        f"  {index}: [{a}, {b}, {c}, {sign}]"
        for index, (a, b, c, sign) in enumerate(inst["lines"])
    )
    example = (
        '{"factors":['
        '{"poly":[[[-6,1],[0]],[[1,1],[1]]],"multiplicity":4},'
        '{"poly":[[[-8,1],[0]],[[2,1],[1]],[[1,1],[2]]],'
        '"multiplicity":1}]}'
    )
    statement = f"""Exact spectrum of a Gram matrix from affine blocks

All scalar arithmetic below is exact. Let F_q be the field of integers modulo
the prime q={inst['q']}. The point set is F_q^2, of size d=q^2={inst['dimension']}.
A row [a,b,c,s] defines the q-point affine block
  B={{(x,y) in F_q^2 : a*x+b*y=c (mod q)}}
and an orientation sign s in {{-1,+1}}. Multiplying a,b,c by the same nonzero
field element does not change the block. Distinct blocks are parallel and
disjoint exactly when their normal pairs (a,b) are proportional modulo q;
otherwise they intersect in exactly one point.

The {inst['N']} oriented blocks are:
{rows}

These blocks have exactly r={inst['classes']} parallel classes. Define the
N-by-N integer matrix G, where N={inst['N']}, by
  G[i,i] = 2q-1;
  G[i,j] = s_i*s_j  if B_i and B_j intersect;
  G[i,j] = -s_i*s_j if B_i and B_j are disjoint (i != j).
This is a positive scalar multiple of the Gram matrix of the equiangular
Euclidean-line representatives supplied by Construction 6.1: here d=q^2,
k=q, the two block intersections are 1 and 0, and Delta_1=q^2/2 >= 0.

Find the exact characteristic polynomial chi_G(x)=det(xI-G). Output it in the
promised compressed factorization into exactly two monic factors: one monic
linear polynomial with multiplicity N-r={inst['N'] - inst['classes']}, and one
monic degree-r polynomial with multiplicity 1. Factor order and polynomial-term
order do not matter.

Represent a polynomial as a JSON list of terms [[num,den],[e]], meaning the
rational coefficient num/den times x^e. Exponents are nonnegative integers,
denominators are positive, repeated exponents are combined, and zero terms may
be omitted. Represent the factorization as
  {{"factors":[{{"poly": POLY, "multiplicity": INTEGER}}, ...]}}.
All coefficients here are integers (denominator 1). The certificate language
bounds every freely chosen coefficient magnitude by
H={inst['coefficient_height']}.

Give your final answer inside <answer></answer> tags as one JSON object.
Example format: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the JSON certificate despite prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    candidates = [match.group(1)] if match else []
    candidates.extend(item.group(1) for item in _FENCE_RE.finditer(text))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except (TypeError, ValueError):
            pass
        for position, character in enumerate(candidate):
            if character != "{":
                continue
            try:
                value, _end = decoder.raw_decode(candidate[position:])
                if isinstance(value, dict):
                    return value
            except ValueError:
                continue
    return None


def _parse_polynomial(raw, factor_index):
    if not isinstance(raw, list) or not raw:
        return None, f"factor {factor_index} polynomial must be a nonempty list"
    coefficients = {}
    for term_index, term in enumerate(raw):
        if not isinstance(term, list) or len(term) != 2:
            return None, (f"factor {factor_index} term {term_index} must be "
                          "[[num,den],[exponent]]")
        rational, exponent = term
        if (not isinstance(rational, list) or len(rational) != 2
                or any(isinstance(value, bool) or not isinstance(value, int)
                       for value in rational)):
            return None, f"factor {factor_index} term {term_index} has a malformed rational"
        numerator, denominator = rational
        if denominator <= 0:
            return None, f"factor {factor_index} term {term_index} denominator must be positive"
        if (not isinstance(exponent, list) or len(exponent) != 1
                or isinstance(exponent[0], bool)
                or not isinstance(exponent[0], int) or exponent[0] < 0):
            return None, f"factor {factor_index} term {term_index} has an invalid exponent"
        power = exponent[0]
        coefficients[power] = coefficients.get(power, Fraction(0)) + Fraction(
            numerator, denominator)
    coefficients = {power: value for power, value in coefficients.items() if value}
    if not coefficients:
        return None, f"factor {factor_index} polynomial is zero"
    degree = max(coefficients)
    if coefficients[degree] != 1:
        return None, f"factor {factor_index} polynomial is not monic"
    return coefficients, "ok"


def _decode_answer(answer):
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    factors = answer.get("factors")
    if not isinstance(factors, list):
        return None, "answer must contain a factors list"
    if not factors:
        return None, "factor list is empty"
    if len(factors) != 2:
        return None, "factorization must contain exactly two factors"
    parsed = []
    for index, factor in enumerate(factors):
        if not isinstance(factor, dict):
            return None, f"factor {index} must be a JSON object"
        multiplicity = factor.get("multiplicity")
        if (isinstance(multiplicity, bool) or not isinstance(multiplicity, int)
                or multiplicity < 1):
            return None, f"factor {index} multiplicity must be a positive integer"
        polynomial, reason = _parse_polynomial(factor.get("poly"), index)
        if polynomial is None:
            return None, reason
        parsed.append((polynomial, multiplicity))
    return parsed, "ok"


def _dense_fraction(polynomial):
    degree = max(polynomial)
    return [polynomial.get(power, Fraction(0)) for power in range(degree + 1)]


def verify(inst, answer):
    """Verify any exact certificate in the declared format; never read answer."""
    parsed, reason = _decode_answer(answer)
    if parsed is None:
        return False, reason
    q = inst.get("q") if isinstance(inst, dict) else None
    count = len(inst.get("lines", [])) if isinstance(inst, dict) else 0
    classes = inst.get("classes") if isinstance(inst, dict) else None
    if not _is_prime(q) or not isinstance(classes, int):
        return False, "instance parameters are invalid"
    expected_multiplicity = count - classes
    bulk_candidates = [item for item in parsed
                       if max(item[0]) == 1
                       and item[1] == expected_multiplicity]
    if len(bulk_candidates) != 1:
        return False, "wrong degree or multiplicity for the repeated linear factor"
    bulk = bulk_candidates[0][0]
    other = parsed[1] if parsed[0] == bulk_candidates[0] else parsed[0]
    residual, residual_multiplicity = other
    if residual_multiplicity != 1 or max(residual) != classes:
        return False, "wrong degree or multiplicity for the residual factor"
    root = -bulk.get(0, Fraction(0))
    if bulk.get(1) != 1 or root.denominator != 1:
        return False, "the repeated linear factor must have an integer root"
    if root != 2 * q:
        return False, "wrong repeated eigenvalue"

    sizes, instance_reason = _recover_sizes(inst)
    if sizes is None:
        return False, instance_reason
    expected = [Fraction(value) for value in _residual_polynomial(q, sizes)]
    proposed = _dense_fraction(residual)
    if len(proposed) != len(expected):
        return False, "residual polynomial degree is wrong"
    for degree, (left, right) in enumerate(zip(proposed, expected)):
        if left != right:
            return False, f"residual coefficient of x^{degree} is wrong"
    return True, "ok"


def _root_max(inst):
    multiplicity = inst["N"] - inst["classes"]
    trace = inst["N"] * (2 * inst["q"] - 1)
    return trace // multiplicity


def random_candidate(inst, rng):
    """Sample the PSD/degree/trace-aware bounded certificate language."""
    q = inst["q"]
    count = inst["N"]
    classes = inst["classes"]
    multiplicity = count - classes
    root = rng.randrange(_root_max(inst) + 1)
    height = inst["coefficient_height"]
    coefficients = []
    for degree in range(classes - 1):
        magnitude = rng.randint(0, height)
        sign = -1 if (classes - degree) % 2 else 1
        coefficients.append(sign * magnitude)
    coefficients.append(multiplicity * root - count * (2 * q - 1))
    coefficients.append(1)
    return {
        "factors": [
            {
                "poly": [[[-root, 1], [0]], [[1, 1], [1]]],
                "multiplicity": multiplicity,
            },
            {"poly": _poly_json(coefficients), "multiplicity": 1},
        ]
    }


def search_space(inst):
    height = inst["coefficient_height"]
    classes = inst["classes"]
    return (_root_max(inst) + 1) * (height + 1) ** (classes - 1)


def enumerate_all(inst):
    """Brute-force the declared prior only when its exact size is safely small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    height = inst["coefficient_height"]
    classes = inst["classes"]
    valid = 0
    for root in range(_root_max(inst) + 1):
        ranges = [range(height + 1)] * (classes - 1)
        for magnitudes in itertools.product(*ranges):
            coefficients = []
            for degree, magnitude in enumerate(magnitudes):
                sign = -1 if (classes - degree) % 2 else 1
                coefficients.append(sign * magnitude)
            coefficients.append((inst["N"] - classes) * root
                                - inst["N"] * (2 * inst["q"] - 1))
            coefficients.append(1)
            candidate = {
                "factors": [
                    {"poly": [[[-root, 1], [0]], [[1, 1], [1]]],
                     "multiplicity": inst["N"] - classes},
                    {"poly": _poly_json(coefficients), "multiplicity": 1},
                ]
            }
            valid += int(verify(inst, candidate)[0])
    return valid


def canonical_key(inst):
    """Canonical signed-permutation invariant: q and class-size multiset."""
    sizes, reason = _recover_sizes(inst)
    if sizes is None:
        payload = {"invalid": reason}
    else:
        payload = {"q": inst["q"], "parallel_class_sizes": sizes}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _estimated_compact_operations(n, classes, min_class, max_class=None):
    q = _next_prime(n)
    if max_class is None:
        max_class = q
    typical_count = classes * (min_class + max_class) // 2
    # Normalize each line (one inversion and two products), count classes, and
    # form prefix/suffix products plus the rank-one determinant correction.
    return 4 * typical_count + 8 * classes * classes + 20


def escalate(params):
    """Grow Gram order first at fixed certificate degree, then raise degree."""
    n = params.get("n")
    classes = params.get("classes")
    min_class = params.get("min_class")
    max_class = params.get("max_class")
    if not all(isinstance(value, int) and not isinstance(value, bool)
               for value in (n, classes, min_class)):
        return None
    current_q = _next_prime(n)
    effective_max = current_q if max_class is None else max_class
    if n < 43:
        # Climb through intermediate primes.  Jumping straight to 2*n can cross
        # the route cap even when several useful fixed-degree levels remain.
        next_n = _next_prime(n + 4)
        next_min = max(min_class, next_n // 2)
        if _estimated_compact_operations(
                next_n, classes, next_min, next_n) <= 1000:
            return {"n": next_n, "classes": classes,
                    "min_class": next_min, "max_class": next_n}
    # Once increasing class sizes would cross the route cap, freeze them and
    # enlarge only F_q.  This raises coefficient entropy while preserving the
    # witness degree, matrix order distribution, and compact operation count.
    if n < 1_000_000:
        return {"n": 1_000_000, "classes": classes,
                "min_class": min_class, "max_class": effective_max}
    if n < 10**15:
        return {"n": 10**15, "classes": classes,
                "min_class": min_class, "max_class": effective_max}
    if n < 10**18:
        return {"n": 10**18, "classes": classes,
                "min_class": min_class, "max_class": effective_max}
    if classes < 11 and classes + 2 <= _next_prime(n) + 1:
        next_classes = classes + 2
        if _estimated_compact_operations(
                n, next_classes, min_class, effective_max) <= 1000:
            return {"n": n, "classes": next_classes,
                    "min_class": min_class, "max_class": effective_max}
    return "cap_bound"


def _full_gram(inst):
    q = inst["q"]
    normalized = [_normalized_line(record, q) for record in inst["lines"]]
    directions = [record[:2] for record in normalized]
    signs = [record[3] for record in normalized]
    count = len(normalized)
    return [[
        2 * q - 1 if i == j else
        signs[i] * signs[j] * (-1 if directions[i] == directions[j] else 1)
        for j in range(count)] for i in range(count)]


def _matrix_multiply(left, right, counter):
    columns = list(zip(*right))
    size = len(left)
    out = []
    for row in left:
        out_row = []
        for column in columns:
            total = 0
            for a, b in zip(row, column):
                total += a * b
            out_row.append(total)
        out.append(out_row)
    counter[0] += 2 * size * size * size
    return out


def _faddeev_leverrier(matrix):
    """Generic exact characteristic polynomial, low-degree first."""
    size = len(matrix)
    traces = []
    high_coefficients = []
    power = None
    counter = [0]
    for k in range(1, size + 1):
        power = matrix if k == 1 else _matrix_multiply(power, matrix, counter)
        trace = sum(power[index][index] for index in range(size))
        counter[0] += size
        traces.append(trace)
        numerator = trace
        for j in range(1, k):
            numerator += high_coefficients[j - 1] * traces[k - j - 1]
            counter[0] += 2
        if numerator % k:
            raise ArithmeticError("Faddeev-LeVerrier division was not exact")
        high_coefficients.append(-numerator // k)
        counter[0] += 1
    return list(reversed(high_coefficients)) + [1], counter[0]


def _divide_by_linear(coefficients, root, counter=None):
    """Divide a low-first polynomial by x-root; return quotient, remainder."""
    degree = len(coefficients) - 1
    quotient = [0] * degree
    carry = coefficients[-1]
    quotient[-1] = carry
    for index in range(degree - 1, 0, -1):
        carry = coefficients[index] + root * carry
        quotient[index - 1] = carry
        if counter is not None:
            counter[0] += 2
    remainder = coefficients[0] + root * carry
    if counter is not None:
        counter[0] += 2
    return _trim(quotient), remainder


def _reference_certificate(inst):
    """Mechanical general linear-algebra route, with no class decomposition."""
    full, operations = _faddeev_leverrier(_full_gram(inst))
    count, classes = inst["N"], inst["classes"]
    multiplicity = count - classes
    division_counter = [0]
    # The output contract promises a high-multiplicity integer linear factor.
    # A generic factorer can recover it from the full polynomial; after paying
    # the dominant O(N^4) cost above, verify the natural integer candidate 2q
    # by exact synthetic division, without using any parallel-class data.
    chosen_root = 2 * inst["q"]
    chosen_residual = full
    for _ in range(multiplicity):
        chosen_residual, remainder = _divide_by_linear(
            chosen_residual, chosen_root, division_counter)
        if remainder:
            raise ArithmeticError("reference promised-factor extraction failed")
    answer = {
        "factors": [
            {"poly": [[[-chosen_root, 1], [0]], [[1, 1], [1]]],
             "multiplicity": multiplicity},
            {"poly": _poly_json(chosen_residual), "multiplicity": 1},
        ]
    }
    return answer, operations + division_counter[0]


def _power_polynomial(root, degree):
    result = [1]
    for _ in range(degree):
        result = _poly_mul(result, [-root, 1])
    return result


def _candidate_from_roots(inst, bulk_root, residual_root):
    """Build a syntactically valid two-root spectrum and repair its trace."""
    count, classes = inst["N"], inst["classes"]
    multiplicity = count - classes
    residual = _power_polynomial(residual_root, classes)
    required = multiplicity * bulk_root - count * (2 * inst["q"] - 1)
    residual[-2] = required
    return {
        "factors": [
            {"poly": [[[-bulk_root, 1], [0]], [[1, 1], [1]]],
             "multiplicity": multiplicity},
            {"poly": _poly_json(residual), "multiplicity": 1},
        ]
    }


def _attack_answers(inst):
    q = inst["q"]
    coefficients = [abs(value) for record in inst["lines"]
                    for value in record[:3] if value]
    frequency = {}
    for value in coefficients:
        frequency[value] = frequency.get(value, 0) + 1
    outlier = min(frequency, key=lambda value: (frequency[value], value))
    diagonal = 2 * q - 1
    trace_average = inst["N"] * diagonal // max(1, inst["classes"])
    signed_row_sums = [sum(row) for row in _full_gram(inst)]
    median_row = sorted(signed_row_sums)[len(signed_row_sums) // 2]
    row_guess = max(0, min(_root_max(inst), abs(median_row)))
    return {
        "outlier_line_coefficient": _candidate_from_roots(
            inst, min(outlier, _root_max(inst)), diagonal),
        "greedy_diagonal_single_root": _candidate_from_roots(
            inst, min(diagonal, _root_max(inst)), diagonal),
        "trace_only_equal_residual_roots": _candidate_from_roots(
            inst, min(2 * q, _root_max(inst)), trace_average),
        "signed_row_sum_ansatz": _candidate_from_roots(
            inst, row_guess, diagonal),
    }


def _random_invertible_matrix(rng, q):
    while True:
        matrix = [[rng.randrange(q), rng.randrange(q)],
                  [rng.randrange(q), rng.randrange(q)]]
        determinant = (matrix[0][0] * matrix[1][1]
                       - matrix[0][1] * matrix[1][0]) % q
        if determinant:
            inverse_det = pow(determinant, -1, q)
            inverse = [
                [matrix[1][1] * inverse_det % q,
                 -matrix[0][1] * inverse_det % q],
                [-matrix[1][0] * inverse_det % q,
                 matrix[0][0] * inverse_det % q],
            ]
            return matrix, inverse


def _transformed_instance(inst, rng):
    """Compose affine point relabelling, equation scaling, signs, and order."""
    q = inst["q"]
    _matrix, inverse = _random_invertible_matrix(rng, q)
    translation = [rng.randrange(q), rng.randrange(q)]
    transformed_lines = []
    for a, b, c, sign in inst["lines"]:
        new_a = (a * inverse[0][0] + b * inverse[1][0]) % q
        new_b = (a * inverse[0][1] + b * inverse[1][1]) % q
        new_c = (c + new_a * translation[0]
                 + new_b * translation[1]) % q
        scalar = rng.randrange(1, q)
        transformed_lines.append([
            new_a * scalar % q,
            new_b * scalar % q,
            new_c * scalar % q,
            sign * rng.choice((-1, 1)),
        ])
    rng.shuffle(transformed_lines)
    transformed = dict(inst)
    transformed["lines"] = transformed_lines
    transformed["answer"] = json.loads(json.dumps(inst["answer"]))
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _compact_operation_bound(inst):
    # Conservative count for normalizing each line, tallying class sizes, and
    # evaluating the prefix/suffix determinant-lemma formula.
    return 4 * inst["N"] + 8 * inst["classes"] ** 2 + 20


def selftest():
    """Run G1--G9 and return fully JSON-native measured evidence."""
    report = {
        "paper": "arXiv:1809.05739",
        "track": TRACK,
        "step4_status": STEP4_STATUS,
        "family": "affine-block equiangular Gram characteristic polynomial",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    checks = 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "construction": "Theorem 6.2 plus the parallel-class determinant identity",
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = json.loads(json.dumps(shipping["answer"]))
    dropped = json.loads(json.dumps(answer))
    dropped["factors"][1]["poly"].pop(0)
    swapped = json.loads(json.dumps(answer))
    swapped["factors"][1]["poly"][0][0], swapped["factors"][1]["poly"][-1][0] = (
        swapped["factors"][1]["poly"][-1][0],
        swapped["factors"][1]["poly"][0][0],
    )
    duplicated = json.loads(json.dumps(answer))
    duplicated["factors"].append(json.loads(json.dumps(duplicated["factors"][0])))
    outside = json.loads(json.dumps(answer))
    outside["factors"][1]["poly"][0][0][1] = 0
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "empty": {"factors": []},
        "out_of_range": outside,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
    distinct_reasons = len({item["reason"] for item in corruption_results.values()})
    report["G2_rejects_corruption"] = {
        "pass": (all(not item["accepted"] for item in corruption_results.values())
                 and distinct_reasons == len(corruption_results)),
        "distinct_reasons": distinct_reasons,
        "cases": corruption_results,
    }

    answer_json = json.dumps(answer, separators=(",", ":"))
    wrapped = (
        "The parallel classes give the following exact factorization.\n```json\n"
        f"<answer>\n{answer_json}\n</answer>\n```\nI also checked the trace."
    )
    report["G3_round_trip"] = {
        "pass": parse_answer(wrapped) == answer and parse_answer("garbage") is None,
        "prose_fence_tags_round_trip": parse_answer(wrapped) == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    sample_total = 200_000
    sample_rng = random.Random(0x180905739)
    hits = 0
    started = time.perf_counter()
    for _ in range(sample_total):
        hits += int(verify(shipping, random_candidate(shipping, sample_rng))[0])
    sample_wall = time.perf_counter() - started
    space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": hits / sample_total < 1e-6 and space > 1_000_000,
        "hits": hits,
        "total": sample_total,
        "observed_fraction": hits / sample_total,
        "exact_fraction": {"numerator": 1, "denominator": space},
        "exact_log10_fraction": -math.log10(space),
        "candidate_space": space,
        "sampling_prior": (
            "monic promised shape, PSD coefficient signs, exact degree, exact "
            "trace coefficient, and the displayed height bound"
        ),
        "wall_clock_sec": round(sample_wall, 6),
    }

    attack_stats = {
        "outlier_line_coefficient": {"successes": 0, "attempts": 0},
        "greedy_diagonal_single_root": {"successes": 0, "attempts": 0},
        "trace_only_equal_residual_roots": {"successes": 0, "attempts": 0},
        "signed_row_sum_ansatz": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0, "candidates": 0},
    }
    strongest_wall = 0.0
    for seed in range(8):
        trial = make_instance(seed=10_000 + seed,
                              **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_answers(trial).items():
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(verify(trial, candidate)[0])
        restart_rng = random.Random(90_000 + seed)
        restart_started = time.perf_counter()
        restart_success = False
        for _ in range(256):
            attack_stats["random_restart_256"]["candidates"] += 1
            if verify(trial, random_candidate(trial, restart_rng))[0]:
                restart_success = True
                break
        strongest_wall += time.perf_counter() - restart_started
        attack_stats["random_restart_256"]["attempts"] += 1
        attack_stats["random_restart_256"]["successes"] += int(restart_success)

    reference_instance = make_instance(
        seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    reference_started = time.perf_counter()
    reference_answer, reference_operations = _reference_certificate(reference_instance)
    reference_wall = time.perf_counter() - reference_started
    reference_ok, reference_reason = verify(reference_instance, reference_answer)
    all_attacks_failed = all(
        values["successes"] == 0 for values in attack_stats.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_ok,
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "exact Faddeev-LeVerrier characteristic polynomial and promised-factor extraction",
            "complexity": "O(N^4) exact operations with schoolbook matrix products",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "operation_unit": "integer multiply/add/divide steps on one shipping instance",
            "matrix_order": reference_instance["N"],
            "solves": "1/1, as expected" if reference_ok else "0/1",
            "verify_reason": reference_reason,
        },
        "compact_route": {
            "name": "parallel-class zero-sum decomposition and determinant lemma",
            "operations_upper_bound": _compact_operation_bound(reference_instance),
            "solves": f"{checks}/{checks} in G1",
        },
    }

    exact_count = enumerate_all(shipping)
    report["G5_density_and_baseline"] = {
        "pass": (hits / sample_total < 1e-6 and reference_ok
                 and reference_operations >= 1_000_000),
        "shipping_exact_valid_count": 1,
        "shipping_exact_solution_fraction": {"numerator": 1, "denominator": space},
        "shipping_sampled_valid_hits": hits,
        "shipping_sampled_valid_total": sample_total,
        "shipping_observed_fraction": hits / sample_total,
        "shipping_density_method": (
            "structure-aware Monte Carlo plus uniqueness of the characteristic polynomial"
        ),
        "bruteforce_count": exact_count,
        "bruteforce_feasible": exact_count is not None,
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "strongest_failing_attack": "random_restart_256",
        "strongest_failing_attack_candidates": attack_stats["random_restart_256"]["candidates"],
        "strongest_failing_attack_wall_clock_sec": round(strongest_wall, 6),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=12345, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    preset_spaces = {}
    preset_orders = {}
    for name, preset_params in DIFFICULTY.items():
        trial = make_instance(seed=424242, **preset_params)
        preset_spaces[name] = search_space(trial)
        preset_orders[name] = trial["N"]
    ascending_spaces = all(
        left < right for left, right in zip(
            list(preset_spaces.values()), list(preset_spaces.values())[1:]))
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["q"] > shipping["q"]
                 and search_space(doubled) > space and ascending_spaces),
        "preset_gram_orders": preset_orders,
        "preset_candidate_spaces": preset_spaces,
        "doubled_n": doubled_params["n"],
        "doubled_q": doubled["q"],
        "doubled_gram_order": doubled["N"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "shipping_answer_atoms": _answer_atoms(shipping["answer"]),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
    }

    invariance_checks = 0
    carried_checks = 0
    invariant_failures = []
    for seed in range(20):
        original = make_instance(seed=20_000 + seed,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])
        transformed = _transformed_instance(original, random.Random(30_000 + seed))
        invariance_checks += 1
        if canonical_key(original) != canonical_key(transformed):
            invariant_failures.append(f"seed {seed}: key changed")
        carried_ok, carried_reason = verify(transformed, original["answer"])
        carried_checks += 1
        if not carried_ok:
            invariant_failures.append(f"seed {seed}: carried witness {carried_reason}")
    unrelated_keys = {
        canonical_key(make_instance(seed=40_000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (not invariant_failures and invariance_checks >= 20
                 and carried_checks >= 20 and len(unrelated_keys) == 20),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": len(unrelated_keys),
        "transformations": [
            "invertible affine relabelling of F_q^2",
            "independent nonzero scaling of every line equation",
            "independent vector sign flips composed with input reordering",
        ],
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_elements = _answer_atoms(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_operations = _compact_operation_bound(shipping)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    difference = (hinted_rate - placebo_rate
                  if hinted_rate is not None and placebo_rate is not None else None)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 1000)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "within_caps": within_caps,
        "arms": arms,
        "diagnostic_complete": all(item["attempts"] > 0 for item in arms.values()),
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 1000},
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
