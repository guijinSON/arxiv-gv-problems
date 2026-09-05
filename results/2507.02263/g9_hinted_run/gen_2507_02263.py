"""Exact signless-Laplacian spectral radii of hidden multipartite graphs.

The source is arXiv:2507.02263.  Section 1.3 defines the signless Laplacian
Q(G)=D(G)+A(G) and its largest eigenvalue q(G); Sections 1.1 and 2 use complete
multipartite Turan graphs and clique blowups throughout.  This generator hides
an irregular complete multipartite graph behind a random vertex relabelling and
asks for q(G) as an exact algebraic number.

The certificate is obtained by composition, not by solving the emitted matrix.
If the part sizes are s_i and N=sum(s_i), the Perron eigenvector is constant on
parts and q(G) is the unique root above every pole of

  product_i (x-N+2*s_i) - sum_i s_i product_{j!=i}(x-N+2*s_j).

We retain only size vectors for which this monic polynomial is irreducible
modulo a small prime; Gauss's lemma then makes it the minimal polynomial over
Q.  The root interval from the largest pole to 2(N-1) is exact.  The checker
reconstructs all of this independently from the adjacency rows and never reads
``inst["answer"]``.
"""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
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
    from gvlib import roots
except ImportError:                 # standard-library fallback below
    roots = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "real_algebraic",
    "computational_core": "graph",
    "certificate_form": "algebraic_number",
    "native_objects": [
        "simple graph given by an adjacency matrix",
        "signless Laplacian matrix Q=D+A",
        "real algebraic signless Laplacian spectral radius",
    ],
    "verification_operations": [
        "exact adjacency-row comparison",
        "exact integer polynomial identity",
        "finite-field irreducibility test",
        "exact Sturm root count over Q",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Equal adjacency rows expose an equitable multipartite decomposition, "
        "reducing the full signless Laplacian to one scalar rational equation; "
        "without it one computes the characteristic polynomial of the full matrix."
    ),
    "hardness_basis": (
        "Track B: the exact Faddeev-LeVerrier characteristic-polynomial algorithm, "
        "followed by rational-root deflation and Sturm isolation, costs O(n^4) "
        "exact scalar operations; at the shipping preset its measured cost is "
        "filled from selftest_report.json, while the equitable-partition identity "
        "uses at most 268 exact arithmetic operations."
    ),
    "max_answer_tokens": 40,
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

DIFFICULTY = {"easy": {"n": 56, "k": 7}}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Identical adjacency rows are the cells of an equitable multipartite "
    "decomposition of the signless Laplacian."
)
PLACEBO_HINT = (
    "Careful attention to coefficient order and interval endpoints is important "
    "for this exact spectral calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON algebraic number {minpoly, interval}: minpoly is a monic dense "
        "integer polynomial of degree k in constant-to-leading order, with each "
        "nonleading coefficient in [-H,H], H=(k+1)(n+1)^k; interval is an open "
        "isolating interval whose two rational endpoints are encoded [integer,1], "
        "with 0 <= lower < upper <= 2(n-1)."
    ),
    "bounds": {
        "degree": "instance k (3 for demo, 7 for evaluated presets)",
        "coefficient_height": "H=(k+1)*(n+1)^k",
        "endpoint_denominator": 1,
        "endpoint_min": 0,
        "endpoint_max": "2*(n-1)",
    },
}

NOTES = (
    "Section 1.3 fixes the exact object q(G) as the largest eigenvalue of the "
    "signless Laplacian Q=D+A.  Section 1.1 defines the complete multipartite "
    "Turan graphs and the blowup notation used by Theorems 2.2--2.12.  Theorem "
    "2.4 is asymptotic and its proof (Section 4) supplies no usable finite "
    "constant; Example 4.1 also shows that the logarithmic blowup size is sharp. "
    "Consequently a small planted-blowup search would not honestly be certified "
    "by that theorem.  This module instead keeps the paper's native spectral "
    "object.  A general exact characteristic-polynomial computation is polynomial "
    "time, so Track A is unavailable and the family is explicitly Track B.  The "
    "certificate polynomial is composed directly from sampled part sizes and is "
    "retained only when a finite-field irreducibility witness exists.  Random "
    "vertex relabelling hides the cells.  The outlier, average-row-sum, row-sum "
    "factor, and random-candidate attacks all fail; the successful exact matrix "
    "algorithm is disclosed separately as the reference algorithm."
)


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

_IRREDUCIBILITY_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _poly_trim(poly):
    out = list(poly)
    while out and out[-1] == 0:
        out.pop()
    return out


def _poly_mul(left, right, counter=None):
    if not left or not right:
        return []
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] += a * b
            if counter is not None:
                counter[0] += 2
    return _poly_trim(out)


def _multiply_monic_linear(poly, constant, counter=None):
    """Multiply by x+constant without charging copies as arithmetic."""
    if not poly:
        return []
    out = [0] * (len(poly) + 1)
    out[0] = constant * poly[0]
    if counter is not None:
        counter[0] += 1
    for index in range(1, len(poly)):
        out[index] = poly[index - 1] + constant * poly[index]
        if counter is not None:
            counter[0] += 2
    out[-1] = poly[-1]
    return _poly_trim(out)


def _poly_eval(poly, value):
    total = 0
    for coefficient in reversed(poly):
        total = total * value + coefficient
    return total


def _divide_monic_linear(poly, constant, counter=None):
    """Return q with poly=(x+constant)q; caller guarantees exact division."""
    degree = len(poly) - 1
    quotient = [0] * degree
    quotient[-1] = poly[-1]
    for index in range(degree - 1, 0, -1):
        quotient[index - 1] = poly[index] - constant * quotient[index]
        if counter is not None:
            counter[0] += 2
    if poly[0] != constant * quotient[0]:
        raise ValueError("non-exact monic linear division")
    if counter is not None:
        counter[0] += 1
    return _poly_trim(quotient)


def _spectral_polynomial(sizes, counter=None):
    """Minimal-polynomial candidate from the multipartite Perron equation."""
    order = sum(sizes)
    constants = [2 * size - order for size in sizes]
    product = [1]
    for constant in constants:
        product = _multiply_monic_linear(product, constant, counter)
    result = list(product)
    for size, constant in zip(sizes, constants):
        quotient = _divide_monic_linear(product, constant, counter)
        for index, value in enumerate(quotient):
            result[index] -= size * value
            if counter is not None:
                counter[0] += 2
    return _poly_trim(result)


# --- finite-field polynomial arithmetic for an executable irreducibility proof

def _fp_trim(poly, prime):
    out = [value % prime for value in poly]
    while out and out[-1] == 0:
        out.pop()
    return out


def _fp_divmod(dividend, divisor, prime):
    remainder = _fp_trim(dividend, prime)
    divisor = _fp_trim(divisor, prime)
    if not divisor:
        raise ZeroDivisionError("zero polynomial")
    quotient = [0] * max(0, len(remainder) - len(divisor) + 1)
    inverse = pow(divisor[-1], prime - 2, prime)
    while len(remainder) >= len(divisor):
        shift = len(remainder) - len(divisor)
        scale = remainder[-1] * inverse % prime
        quotient[shift] = scale
        for index, value in enumerate(divisor):
            remainder[shift + index] = (
                remainder[shift + index] - scale * value
            ) % prime
        remainder = _fp_trim(remainder, prime)
    return _fp_trim(quotient, prime), remainder


def _fp_gcd(left, right, prime):
    left = _fp_trim(left, prime)
    right = _fp_trim(right, prime)
    while right:
        _, remainder = _fp_divmod(left, right, prime)
        left, right = right, remainder
    if not left:
        return []
    inverse = pow(left[-1], prime - 2, prime)
    return [(value * inverse) % prime for value in left]


def _fp_mulmod(left, right, modulus, prime):
    product = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            product[i + j] = (product[i + j] + a * b) % prime
    return _fp_divmod(product, modulus, prime)[1]


def _fp_powmod(base, exponent, modulus, prime):
    result = [1]
    value = _fp_divmod(base, modulus, prime)[1]
    while exponent:
        if exponent & 1:
            result = _fp_mulmod(result, value, modulus, prime)
        value = _fp_mulmod(value, value, modulus, prime)
        exponent //= 2
    return result


def _prime_divisors(value):
    result = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            result.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1
    if value > 1:
        result.append(value)
    return result


def _irreducible_mod_prime(poly, prime):
    """Rabin's exact irreducibility criterion over GF(prime)."""
    modulus = _fp_trim(poly, prime)
    degree = len(modulus) - 1
    if degree < 1 or modulus[-1] == 0:
        return False
    x_poly = [0, 1]
    for divisor in _prime_divisors(degree):
        test = _fp_powmod(x_poly, prime ** (degree // divisor), modulus, prime)
        if len(test) < 2:
            test.extend([0] * (2 - len(test)))
        test[1] = (test[1] - 1) % prime
        if len(_fp_gcd(modulus, test, prime)) > 1:
            return False
    test = _fp_powmod(x_poly, prime ** degree, modulus, prime)
    if len(test) < 2:
        test.extend([0] * (2 - len(test)))
    test[1] = (test[1] - 1) % prime
    return not _fp_trim(test, prime)


def _irreducibility_prime(poly):
    for prime in _IRREDUCIBILITY_PRIMES:
        if _irreducible_mod_prime(poly, prime):
            return prime
    return None


# --- exact rational Sturm fallback

def _q_trim(poly):
    out = [Fraction(value) for value in poly]
    while out and out[-1] == 0:
        out.pop()
    return out


def _q_divmod(dividend, divisor):
    remainder = _q_trim(dividend)
    divisor = _q_trim(divisor)
    if not divisor:
        raise ZeroDivisionError("zero polynomial")
    quotient = [Fraction(0)] * max(0, len(remainder) - len(divisor) + 1)
    while len(remainder) >= len(divisor):
        shift = len(remainder) - len(divisor)
        scale = remainder[-1] / divisor[-1]
        quotient[shift] = scale
        for index, value in enumerate(divisor):
            remainder[shift + index] -= scale * value
        remainder = _q_trim(remainder)
    return _q_trim(quotient), remainder


def _sturm_chain(poly):
    first = _q_trim(poly)
    second = [Fraction(index) * first[index] for index in range(1, len(first))]
    second = _q_trim(second)
    chain = [first, second]
    while len(chain[-1]) > 1:
        _, remainder = _q_divmod(chain[-2], chain[-1])
        if not remainder:
            break
        chain.append([-value for value in remainder])
    return chain


def _q_eval(poly, value):
    total = Fraction(0)
    point = Fraction(value)
    for coefficient in reversed(poly):
        total = total * point + coefficient
    return total


def _sign_changes(chain, value):
    signs = []
    for poly in chain:
        evaluated = _q_eval(poly, value)
        if evaluated:
            signs.append(1 if evaluated > 0 else -1)
    return sum(left != right for left, right in zip(signs, signs[1:]))


def _count_roots(poly, lower, upper):
    lower = Fraction(lower)
    upper = Fraction(upper)
    if roots is not None:
        return roots.count_roots(poly, lower, upper)
    if _q_eval(poly, lower) == 0 or _q_eval(poly, upper) == 0:
        raise ValueError("root at interval endpoint")
    chain = _sturm_chain(poly)
    return _sign_changes(chain, lower) - _sign_changes(chain, upper)


@lru_cache(maxsize=256)
def _cached_graph_data(order, k, encoded_rows):
    """Validated invariants of an immutable adjacency encoding."""
    shadow = {"n": order, "k": k, "rows": list(encoded_rows)}
    sizes = _part_sizes_from_rows(shadow)
    polynomial = _spectral_polynomial(sizes)
    prime = _irreducibility_prime(polynomial)
    pole = max(order - 2 * size for size in sizes)
    return tuple(sizes), tuple(polynomial), prime, pole


def _coefficient_bound(order, k):
    return (k + 1) * (order + 1) ** k


def _sample_sizes(order, k, rng):
    minimum = sum(range(2, k + 2))
    if order < minimum:
        raise ValueError(
            "n must be at least %d for k distinct parts of size at least 2" % minimum
        )
    for _ in range(100000):
        cuts = sorted(rng.sample(range(2, order - 1), k - 1))
        sizes = [cuts[0]]
        sizes.extend(cuts[index] - cuts[index - 1] for index in range(1, k - 1))
        sizes.append(order - cuts[-1])
        if min(sizes) < 2 or len(set(sizes)) != k:
            continue
        poly = _spectral_polynomial(sizes)
        if max(abs(value) for value in poly) > _coefficient_bound(order, k):
            continue
        prime = _irreducibility_prime(poly)
        if prime is not None:
            return sizes, poly, prime
    raise RuntimeError("could not construct an irreducible multipartite instance")


def _rows_from_classes(classes):
    order = len(classes)
    rows = []
    for left in range(order):
        bits = 0
        for right in range(order):
            if classes[left] != classes[right]:
                bits |= 1 << right
        rows.append(bits)
    width = (order + 3) // 4
    return [format(bits, "0%dx" % width) for bits in rows]


def _decode_rows(inst):
    order = inst.get("n")
    encoded = inst.get("rows")
    if not _is_int(order) or order < 1:
        raise ValueError("instance order is malformed")
    if not isinstance(encoded, list) or len(encoded) != order:
        raise ValueError("instance adjacency rows are malformed")
    width = (order + 3) // 4
    rows = []
    for text in encoded:
        if not isinstance(text, str) or len(text) != width or not re.fullmatch(
            r"[0-9a-f]+", text
        ):
            raise ValueError("instance adjacency row is malformed")
        bits = int(text, 16)
        if bits >> order:
            raise ValueError("instance adjacency row has excess bits")
        rows.append(bits)
    for vertex, bits in enumerate(rows):
        if (bits >> vertex) & 1:
            raise ValueError("instance graph has a loop")
        for other in range(vertex):
            if ((bits >> other) & 1) != ((rows[other] >> vertex) & 1):
                raise ValueError("instance adjacency matrix is not symmetric")
    return rows


def _part_sizes_from_rows(inst):
    rows = _decode_rows(inst)
    groups = {}
    for vertex, row in enumerate(rows):
        groups.setdefault(row, []).append(vertex)
    sizes = []
    order = len(rows)
    for row, vertices in groups.items():
        vertex_set = set(vertices)
        for vertex in vertices:
            expected = ((1 << order) - 1) ^ sum(1 << item for item in vertex_set)
            if rows[vertex] != expected:
                raise ValueError("instance is not complete multipartite by row classes")
        sizes.append(len(vertices))
    sizes.sort()
    if len(sizes) != inst.get("k") or len(set(sizes)) != len(sizes) or min(sizes) < 2:
        raise ValueError("instance has the wrong multipartite cell structure")
    return sizes


def make_instance(n, seed=0, **params):
    """Composition-generate a relabelled complete multipartite spectral instance."""
    if not _is_int(n) or not _is_int(seed):
        raise TypeError("n and seed must be integers")
    k = params.pop("k", 7)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(k) or not 3 <= k <= 7:
        raise ValueError("k must be an integer in 3,...,7")
    rng = random.Random(seed)
    sizes, polynomial, witness_prime = _sample_sizes(n, k, rng)

    classes = []
    for cell, size in enumerate(sizes):
        classes.extend([cell] * size)
    rng.shuffle(classes)
    rows = _rows_from_classes(classes)

    lower = max(n - 2 * size for size in sizes)
    upper = 2 * (n - 1)
    answer = {
        "minpoly": polynomial,
        "interval": [[lower, 1], [upper, 1]],
    }
    return {
        "n": n,
        "k": k,
        "rows": rows,
        "coefficient_bound": _coefficient_bound(n, k),
        "construction_irreducibility_prime": witness_prime,
        "answer": answer,
    }


def render(inst):
    order = inst["n"]
    k = inst["k"]
    width = (order + 3) // 4
    lines = [
        "Find the signless Laplacian spectral radius of a graph exactly.",
        "",
        "The graph is finite, simple, and undirected, with vertices 0,...,%d." % (order - 1),
        "Its adjacency matrix is A.  The degree d_i is the number of 1s in row i,",
        "D is the diagonal matrix diag(d_0,...,d_%d), and the signless Laplacian" % (order - 1),
        "is Q=D+A.  Its spectral radius q(G) is the largest real eigenvalue of Q.",
        "",
        "The adjacency rows are hexadecimal bit masks of exactly %d digits." % width,
        "In row i, bit j is 1 exactly when vertices i and j are adjacent; bit 0",
        "is the least-significant (rightmost) bit.  Leading zero hex digits are kept.",
        "Rows:",
    ]
    lines.extend("  %d: %s" % (index, row) for index, row in enumerate(inst["rows"]))
    lines.extend([
        "",
        "It is guaranteed that exactly k=%d distinct adjacency-row patterns occur," % k,
        "and that the requested number has a monic irreducible minimal polynomial",
        "of degree k over the rationals.",
        "",
        "Return q(G) as an exact real algebraic number.  The key minpoly must be",
        "the dense coefficient list [c0,c1,...,c%d] for" % k,
        "  c0 + c1*x + ... + c%d*x^%d," % (k, k),
        "in constant-to-leading order.  All coefficients are integers, c%d=1," % k,
        "and every nonleading coefficient must lie in the inclusive range [-H,H],",
        "where H=%d." % inst["coefficient_bound"],
        "",
        "The key interval must be [[L,1],[U,1]], representing the OPEN rational",
        "interval L < q(G) < U.  Here L and U are integers satisfying",
        "0 <= L < U <= %d, neither endpoint is a root, and the interval contains" % (2 * (order - 1)),
        "exactly one root of minpoly.  Coefficient order matters; interval endpoint",
        "order matters; no coefficient or endpoint may be omitted.",
        "",
        "Give your final answer inside <answer></answer> tags, as exactly one JSON",
        "object with keys minpoly and interval.",
        "Example format for k=%d: <answer>{\"minpoly\":[0,%s1],\"interval\":[[0,1],[1,1]]}</answer>" % (k, "0," * (k - 1)),
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    candidates = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        starts = [index for index, char in enumerate(candidate) if char == "{"]
        for start in starts:
            try:
                value, _ = decoder.raw_decode(candidate[start:])
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict):
                return value
    return None


def _answer_interval(answer):
    interval = answer.get("interval")
    if not isinstance(interval, list) or len(interval) != 2:
        return None, "interval must contain exactly two rational endpoints"
    values = []
    for endpoint in interval:
        if not isinstance(endpoint, list) or len(endpoint) != 2:
            return None, "each interval endpoint must be [integer,1]"
        numerator, denominator = endpoint
        if not _is_int(numerator) or denominator != 1 or not _is_int(denominator):
            return None, "interval endpoints must be integer rationals [integer,1]"
        values.append(numerator)
    return values, None


def verify(inst, answer):
    """Verify any valid minimal-polynomial/interval witness; never use inst['answer']."""
    if not isinstance(answer, dict) or set(answer) != {"minpoly", "interval"}:
        return False, "answer must be an object with exactly minpoly and interval"
    try:
        order = inst["n"]
        k = inst["k"]
        height = _coefficient_bound(order, k)
    except (KeyError, TypeError, ValueError):
        return False, "instance parameters are malformed"

    polynomial = answer.get("minpoly")
    if not isinstance(polynomial, list) or len(polynomial) != k + 1:
        return False, "minpoly must contain exactly k+1 coefficients"
    if not all(_is_int(value) for value in polynomial):
        return False, "minpoly coefficients must be integers"
    if any(abs(value) > height for value in polynomial[:-1]):
        return False, "a minpoly coefficient is outside the declared height bound"
    if polynomial[-1] != 1:
        return False, "minpoly must be monic with leading coefficient 1"

    endpoints, problem = _answer_interval(answer)
    if problem:
        return False, problem
    lower, upper = endpoints
    if not (0 <= lower < upper <= 2 * (order - 1)):
        return False, "interval endpoints violate 0 <= L < U <= 2(n-1)"

    try:
        sizes, expected, irreducibility_prime, pole = _cached_graph_data(
            order, k, tuple(inst["rows"])
        )
    except (ValueError, TypeError) as exc:
        return False, str(exc)
    if tuple(polynomial) != expected:
        return False, "minpoly does not match the graph-derived Perron polynomial"
    if irreducibility_prime is None:
        return False, "minpoly has no accepted finite-field irreducibility witness"

    if lower < pole:
        return False, "interval lower endpoint is below the Perron pole bound"
    if _poly_eval(polynomial, lower) == 0 or _poly_eval(polynomial, upper) == 0:
        return False, "an interval endpoint is a root"
    try:
        root_count = _count_roots(polynomial, lower, upper)
    except (ValueError, ZeroDivisionError, TypeError):
        return False, "Sturm root count could not certify the interval"
    if root_count != 1:
        return False, "interval does not isolate exactly one root"
    return True, "ok"


def random_candidate(inst, rng):
    order = inst["n"]
    k = inst["k"]
    height = _coefficient_bound(order, k)
    polynomial = [rng.randrange(-height, height + 1) for _ in range(k)] + [1]
    endpoints = rng.sample(range(0, 2 * (order - 1) + 1), 2)
    endpoints.sort()
    return {
        "minpoly": polynomial,
        "interval": [[endpoints[0], 1], [endpoints[1], 1]],
    }


def search_space(inst):
    order = inst["n"]
    k = inst["k"]
    height = _coefficient_bound(order, k)
    endpoint_values = 2 * (order - 1) + 1
    return (2 * height + 1) ** k * math.comb(endpoint_values, 2)


def _valid_interval_count(inst):
    sizes, polynomial, _, pole = _cached_graph_data(
        inst["n"], inst["k"], tuple(inst["rows"])
    )
    polynomial = list(polynomial)
    order = inst["n"]
    endpoint_max = 2 * (order - 1)
    if roots is not None:
        chain = roots.sturm_sequence(polynomial)
        variations = {
            endpoint: roots.sign_changes(chain, endpoint)
            for endpoint in range(pole, endpoint_max + 1)
        }
        root_counts = lambda lower, upper: variations[lower] - variations[upper]
    else:
        chain = _sturm_chain(polynomial)
        variations = {
            endpoint: _sign_changes(chain, endpoint)
            for endpoint in range(pole, endpoint_max + 1)
        }
        root_counts = lambda lower, upper: variations[lower] - variations[upper]
    count = 0
    for lower in range(pole, endpoint_max):
        for upper in range(lower + 1, endpoint_max + 1):
            if root_counts(lower, upper) == 1:
                count += 1
    return count


def enumerate_all(inst):
    # Only one coefficient vector can be valid; enumerate all bounded endpoint
    # pairs for it exactly.  This is a complete count of encoded certificates.
    return _valid_interval_count(inst)


def canonical_key(inst):
    sizes = _part_sizes_from_rows(inst)
    return "complete-multipartite:" + ",".join(map(str, sizes))


def escalate(params):
    harder = dict(params)
    order = int(harder["n"])
    k = int(harder.get("k", 7))
    next_order = max(order + 8, (5 * order + 3) // 4)
    # k stays fixed, so the answer keeps k+5 atoms while the full matrix and the
    # bounded coefficient search space grow.  At astronomically large n the
    # coefficient spelling, rather than the mathematics, eventually hits the cap.
    if k * (next_order.bit_length() + 3) > 1800:
        return "cap_bound"
    harder["n"] = next_order
    harder["k"] = k
    return harder


# --- exact Track-B reference algorithm and adversaries

def _signless_matrix(inst):
    rows = _decode_rows(inst)
    order = len(rows)
    matrix = [[0] * order for _ in range(order)]
    for i, bits in enumerate(rows):
        matrix[i][i] = bits.bit_count()
        for j in range(order):
            if (bits >> j) & 1:
                matrix[i][j] = 1
    return matrix


def _faddeev_charpoly(matrix):
    """Dense exact Faddeev-LeVerrier; return ascending charpoly and op count."""
    order = len(matrix)
    current = [[int(i == j) for j in range(order)] for i in range(order)]
    descending = [1]
    operations = 0
    for step in range(1, order + 1):
        product = [[0] * order for _ in range(order)]
        for i, row in enumerate(matrix):
            destination = product[i]
            for middle, scalar in enumerate(row):
                if scalar == 0:
                    continue
                source = current[middle]
                for j, value in enumerate(source):
                    destination[j] += scalar * value
                    operations += 2
        coefficient = -sum(product[i][i] for i in range(order)) // step
        operations += order + 1
        descending.append(coefficient)
        for i in range(order):
            product[i][i] += coefficient
            operations += 1
        current = product
    return list(reversed(descending)), operations


def _primitive_integer(poly):
    fractions = [Fraction(value) for value in poly]
    lcm = 1
    for value in fractions:
        lcm = math.lcm(lcm, value.denominator)
    integers = [int(value * lcm) for value in fractions]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    integers = [value // divisor for value in integers]
    if integers[-1] < 0:
        integers = [-value for value in integers]
    return _poly_trim(integers)


def _reference_algorithm(inst):
    """General matrix route: charpoly, squarefree part, root deflation, Sturm."""
    started = time.perf_counter()
    characteristic, operations = _faddeev_charpoly(_signless_matrix(inst))
    if roots is not None:
        squarefree = roots.squarefree_part(characteristic)
    else:
        # The generated spectrum is known to have only repeated integer factors;
        # divide repeated integer roots below directly from the full polynomial.
        squarefree = [Fraction(value) for value in characteristic]
        for candidate in range(0, 2 * inst["n"]):
            while _q_eval(squarefree, candidate) == 0:
                quotient, remainder = _q_divmod(squarefree, [-candidate, 1])
                if remainder:
                    break
                squarefree = quotient
    remaining = _primitive_integer(squarefree)
    # Generic rational-root deflation.  For this family the non-Perron factors
    # are the integer eigenvalues contributed by within-cell zero-sum vectors.
    for candidate in range(0, 2 * inst["n"]):
        while len(remaining) - 1 > inst["k"] and _poly_eval(remaining, candidate) == 0:
            remaining = _divide_monic_linear(remaining, -candidate)
            operations += 2 * len(remaining)
    remaining = _primitive_integer(remaining)
    upper = 2 * (inst["n"] - 1)
    interval = None
    for lower in range(0, upper):
        if _poly_eval(remaining, lower) == 0:
            continue
        if _count_roots(remaining, lower, upper) == 1:
            interval = [[lower, 1], [upper, 1]]
            break
    if interval is None:
        raise RuntimeError("reference root isolation failed")
    answer = {"minpoly": remaining, "interval": interval}
    elapsed = time.perf_counter() - started
    return answer, operations, elapsed


def _power_polynomial(root_value, degree):
    result = [1]
    for _ in range(degree):
        result = _poly_mul(result, [-root_value, 1])
    return result


def _guess_answer(inst, polynomial):
    order = inst["n"]
    return {
        "minpoly": polynomial,
        "interval": [[0, 1], [2 * (order - 1), 1]],
    }


def _attack_candidates(inst, rng):
    rows = _decode_rows(inst)
    degrees = [row.bit_count() for row in rows]
    degree_values = sorted(set(degrees))
    k = inst["k"]
    maximum_guess = 2 * max(degrees)
    average_guess = round(2 * sum(degrees) / len(degrees))
    row_sum_factors = [1]
    for degree in degree_values:
        row_sum_factors = _poly_mul(row_sum_factors, [-2 * degree, 1])
    midpoint_guess = (2 * min(degrees) + 2 * max(degrees)) // 2
    return {
        "outlier_max_row_sum": _guess_answer(inst, _power_polynomial(maximum_guess, k)),
        "greedy_average_row_sum": _guess_answer(inst, _power_polynomial(average_guess, k)),
        "obvious_row_sum_factor_ansatz": _guess_answer(inst, row_sum_factors),
        "perron_bound_midpoint_ansatz": _guess_answer(inst, _power_polynomial(midpoint_guess, k)),
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _relabel_instance(inst, permutation):
    order = inst["n"]
    if sorted(permutation) != list(range(order)):
        raise ValueError("not a permutation")
    old_rows = _decode_rows(inst)
    new_rows = [0] * order
    for old_vertex, bits in enumerate(old_rows):
        new_vertex = permutation[old_vertex]
        new_bits = 0
        for old_other in range(order):
            if (bits >> old_other) & 1:
                new_bits |= 1 << permutation[old_other]
        new_rows[new_vertex] = new_bits
    transformed = {key: value for key, value in inst.items() if key not in {"rows", "answer"}}
    width = (order + 3) // 4
    transformed["rows"] = [format(bits, "0%dx" % width) for bits in new_rows]
    transformed["answer"] = json.loads(json.dumps(inst["answer"]))
    return transformed


def selftest():
    report = {}

    # G1
    planted_attempts = 0
    planted_verified = 0
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            ok, _ = verify(inst, inst["answer"])
            planted_verified += int(ok)
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": planted_verified == planted_attempts and json_native,
        "attempts": planted_attempts,
        "verified": planted_verified,
        "answer_json_native": json_native,
    }

    # G2
    shipping = make_instance(seed=1234, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = json.loads(json.dumps(shipping["answer"]))
    height = _coefficient_bound(shipping["n"], shipping["k"])
    corruptions = {}
    variants = {}
    drop = json.loads(json.dumps(base))
    drop["minpoly"].pop(0)
    variants["drop"] = drop
    swap = json.loads(json.dumps(base))
    swap["minpoly"][0], swap["minpoly"][1] = swap["minpoly"][1], swap["minpoly"][0]
    variants["swap"] = swap
    duplicate = json.loads(json.dumps(base))
    duplicate["interval"][1] = list(duplicate["interval"][0])
    variants["duplicate"] = duplicate
    variants["empty"] = []
    outside = json.loads(json.dumps(base))
    outside["minpoly"][0] = height + 1
    variants["out_of_range"] = outside
    reasons = []
    for name, candidate in variants.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "corruptions": corruptions,
    }

    # G3
    realistic = "Here is the exact result.\n```json\n<answer>%s</answer>\n```\n" % json.dumps(
        shipping["answer"], separators=(",", ":")
    )
    recovered = parse_answer(realistic)
    garbage = parse_answer("No JSON answer is present here.")
    report["G3_round_trip"] = {
        "pass": recovered == shipping["answer"] and garbage is None,
        "realistic_response_recovered": recovered == shipping["answer"],
        "garbage_returns_none": garbage is None,
    }

    # G4
    guess_rng = random.Random(20260905)
    samples = 200000
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        hits += int(verify(shipping, candidate)[0])
    guess_elapsed = time.perf_counter() - start
    exact_valid = enumerate_all(shipping)
    space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": space,
        "exact_valid_certificate_count": exact_valid,
        "exact_probability": exact_valid / space,
        "sampling_wall_clock_sec": round(guess_elapsed, 6),
        "sampling_prior": (
            "uniform monic degree-k bounded coefficient vectors and uniformly "
            "chosen ordered integer endpoint pairs; all syntax, degree, monicity, "
            "height, and interval-order constraints are enforced"
        ),
    }

    # G6 reference algorithm: run the exact full-matrix method over eight seeds.
    reference_operations = []
    reference_times = []
    reference_successes = 0
    attack_names = [
        "outlier_max_row_sum",
        "greedy_average_row_sum",
        "random_restart_256",
        "obvious_row_sum_factor_ansatz",
        "perron_bound_midpoint_ansatz",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    for seed in range(8):
        inst = make_instance(seed=7000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        ref_answer, operations, elapsed = _reference_algorithm(inst)
        reference_operations.append(operations)
        reference_times.append(elapsed)
        reference_successes += int(verify(inst, ref_answer)[0])

        generated = _attack_candidates(inst, random.Random(seed))
        for name, candidate in generated.items():
            attack_started = time.perf_counter()
            ok, _ = verify(inst, candidate)
            attack_results[name]["wall_clock_sec"] += time.perf_counter() - attack_started
            attack_results[name]["successes"] += int(ok)
            attack_results[name]["attempts"] += 1
        restart_started = time.perf_counter()
        restart_rng = random.Random(9000 + seed)
        restart_hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_hit = True
                break
        attack_results["random_restart_256"]["wall_clock_sec"] += (
            time.perf_counter() - restart_started
        )
        attack_results["random_restart_256"]["successes"] += int(restart_hit)
        attack_results["random_restart_256"]["attempts"] += 1
    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)

    intended_counter = [0]
    sizes = _part_sizes_from_rows(shipping)
    compact_poly = _spectral_polynomial(sizes, intended_counter)
    intended_operations = intended_counter[0] + 2 * len(sizes) + 2
    compact_ok = compact_poly == shipping["answer"]["minpoly"]
    report["G5_density_and_baseline_cost"] = {
        "pass": reference_successes == 8,
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "shipping_sampled_density": hits / samples,
        "shipping_exact_valid_certificate_count": exact_valid,
        "shipping_exact_density": exact_valid / space,
        "baseline_wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
        "baseline_wall_clock_sec_max": round(max(reference_times), 6),
        "baseline_operation_count_mean": round(sum(reference_operations) / 8),
        "baseline_operation_count_max": max(reference_operations),
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attack_results.values())
        and reference_successes == 8 and compact_ok,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": (
                "exact Faddeev-LeVerrier characteristic polynomial, rational-root "
                "deflation, and Sturm isolation"
            ),
            "complexity": "O(n^4) exact scalar operations",
            "wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_operations) / 8),
            "operations_max": max(reference_operations),
            "solves": "%d/8, as expected" % reference_successes,
        },
        "intended_compact_route": {
            "name": "equal-row equitable decomposition and Perron rational equation",
            "operations": intended_operations,
            "solves": "1/1 audited symbolically",
        },
    }

    # G7
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(seed=321, **doubled_params)
    doubled_build = time.perf_counter() - doubled_started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and search_space(doubled) > search_space(shipping)
        and _answer_atoms(doubled["answer"]) == _answer_atoms(shipping["answer"]),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(doubled),
        "shipping_answer_elements": _answer_atoms(shipping["answer"]),
        "doubled_answer_elements": _answer_atoms(doubled["answer"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: arbitrary relabellings, reversals, and compositions.
    invariant = 0
    real = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=12000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        rng = random.Random(13000 + seed)
        random_permutation = list(range(inst["n"]))
        rng.shuffle(random_permutation)
        reversal = list(reversed(range(inst["n"])))
        composed = [reversal[random_permutation[index]] for index in range(inst["n"])]
        for permutation in (random_permutation, reversal, composed):
            transformed = _relabel_instance(inst, permutation)
            invariant += int(canonical_key(transformed) == original_key)
            real += int(verify(transformed, inst["answer"])[0])
        unrelated_keys.append(original_key)
    report["G8_canonical_key"] = {
        "pass": invariant == 60 and real == 60 and len(set(unrelated_keys)) == 20,
        "invariant_relabellings": invariant,
        "invariant_attempts": 60,
        "real_transformations_verified": real,
        "real_transformation_attempts": 60,
        "unrelated_distinct_keys": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "uniform random vertex permutation",
            "vertex-order reversal",
            "random permutation composed with reversal",
        ],
    }

    # G9(c) gates; arms are populated after the script-owned oracle runs.
    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_minus = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
