"""Verified Track-B generator for primary decomposition of principal ideals.

The paper arXiv:1408.5515 defines primary decompositions for submodules of
Q[X]^s and gives a Singular implementation based on Groebner bases, Ext,
localization, saturation, and equidimensional hulls.  This module stays in
that native setting, in the special case s=1.

Generation first chooses an invertible triangular affine coordinate system
z_i and constants c,p.  It then constructs

    F = (z_0 z_1 ... z_{m-1} + c)^2 - p^2.

The planted certificate describes the coordinate system.  It certifies the
primary decomposition (F)=(g-p) intersect (g+p), where g=product(z_i)+c.
Both factors are prime: after the certified affine change of variables they
are product(z_i)+(c+-p), a primitive binomial with nonzero constant.  The
verifier checks the change-of-variables shape and the full polynomial identity
with exact integer arithmetic; it never reads inst["answer"].
"""

from __future__ import annotations

import copy
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


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import rationals, sparse_poly  # noqa: F401
except ImportError:  # The exact implementation below is standard-library-only.
    rationals = sparse_poly = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "principal ideal in a multivariate polynomial ring over Q",
        "sparse multivariate polynomial over Q",
        "prime primary components given by affine-coordinate expressions",
    ],
    "verification_operations": [
        "exact sparse-polynomial multiplication and coefficient comparison",
        "exact rational bound and shape checks",
        "permutation and triangular-determinant checks",
        "integer nonzero comparison for the primitive-binomial constants",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The top homogeneous layers reveal a triangular affine coordinate "
        "chain in which the generator becomes a difference of two squares; "
        "without recognizing that chain, one must carry out exact multivariate "
        "factorization or primary decomposition."
    ),
    "hardness_basis": (
        "Track B: the paper's Algorithm 2.15/Section 3 Singular pipeline uses "
        "Groebner bases, Ext, localization, saturation and equidimensional "
        "hulls; the executable reference here is exact multivariate square-root "
        "extraction followed by bounded affine trial division, with complexity "
        "O(T^2 + n^2*m^2*T^2) for T sparse terms and coefficient bound n.  At "
        "the medium preset it averages 1,519,764 exact operations and 1.9--2.9 s "
        "across the final local runs; "
        "the verified triangular coefficient-chain route needs 107 exact operations."
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

# n is the coefficient-height/search-width parameter.  Keeping variables fixed
# while growing n enlarges the haystack and the reference trial-division cost
# without lengthening the certificate.
DIFFICULTY = {
    "demo": {"n": 2, "variables": 2},
    "easy": {"n": 14, "variables": 5},
    "medium": {"n": 14, "variables": 6},
    "hard": {"n": 20, "variables": 6},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The highest homogeneous layers are the square of a product whose "
    "two-variable supports form a triangular coordinate chain."
)
PLACEBO_HINT = (
    "The polynomial terms are deliberately unordered, so track exponent "
    "vectors and rational signs with care."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON affine-coordinate certificate: a permutation order of all m "
        "variables; m-1 positive integer link coefficients in [1,n]; m "
        "nonzero integer offsets in [-n,n]; a center in [-n,n]; and a positive "
        "gap in [1,n] unequal to the center's absolute value.  Every scalar is "
        "encoded as [numerator,denominator] with denominator 1."
    ),
    "bounds": {
        "variables": "2 <= m <= 7",
        "link_numerators": "1..n",
        "offset_numerators": "[-n,n] excluding 0",
        "center_numerator": "[-n,n]",
        "gap_numerator": "1..n and gap != abs(center)",
        "denominator": 1,
    },
}

NOTES = (
    "Definition 1.3 fixes primary decomposition, distinct associated primes, "
    "and reducedness.  Algorithm 2.15 (PrimdecmEHV), together with Algorithms "
    "2.3--2.10, identifies the mechanical route: Ext computations, Groebner "
    "bases, localization, saturation, equidimensional hulls, and associated "
    "primes; Section 3 gives the Singular procedures.  Theorem 2.14 says that "
    "N+P^m R^s yields a P-primary component after taking the equidimensional "
    "part, but neither that theorem nor the paper proves a hard distribution, "
    "so Track A is not claimed.  The generator instead uses a theorem-backed "
    "affine transformation of the directly checkable binomials product(z_i)+d. "
    "Links, offsets, center and gap are sampled before F is multiplied out. "
    "Variable names and term order are scrambled.  The outlier, magnitude "
    "greedy, diagonal-coordinate and short random-restart attacks intentionally "
    "ignore different pieces of the triangular invariant; the exact reference "
    "algorithm reconstructs a polynomial square root and performs bounded "
    "linear-factor trial division without consulting the planted answer."
)

# Replace only with script-owned measurements after the three hardening runs.
# The current environment exhausted its OpenRouter key before those runs could
# complete, so unavailable arms are recorded as zero attempts and do not pass G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


# ---------------------------------------------------------------------------
# Exact sparse polynomials.  Keys are exponent tuples; coefficients are ints or
# Fractions.  No floating-point arithmetic appears anywhere in the generator or
# checker.


def _padd(a, b):
    out = dict(a)
    for exponent, coefficient in b.items():
        value = out.get(exponent, 0) + coefficient
        if value:
            out[exponent] = value
        else:
            out.pop(exponent, None)
    return out


def _pscale(a, scalar):
    if not scalar:
        return {}
    return {e: c * scalar for e, c in a.items() if c * scalar}


def _psub(a, b):
    return _padd(a, _pscale(b, -1))


def _pmul(a, b, counter=None):
    out = {}
    for ea, ca in a.items():
        for eb, cb in b.items():
            exponent = tuple(x + y for x, y in zip(ea, eb))
            out[exponent] = out.get(exponent, 0) + ca * cb
            if counter is not None:
                counter[0] += 2  # one exact multiply and one exact add
    return {e: c for e, c in out.items() if c}


def _pconst(value, variables):
    return {} if not value else {(0,) * variables: value}


def _pvar(index, variables):
    exponent = [0] * variables
    exponent[index] = 1
    return {tuple(exponent): 1}


def _peval(poly, point):
    total = 0
    for exponent, coefficient in poly.items():
        term = coefficient
        for value, power in zip(point, exponent):
            if power:
                term *= value**power
        total += term
    return total


def _poly_to_terms(poly):
    terms = []
    for exponent, coefficient in sorted(poly.items()):
        q = Fraction(coefficient)
        terms.append([[q.numerator, q.denominator], list(exponent)])
    return terms


def _terms_to_poly(terms, variables):
    if not isinstance(terms, list):
        raise ValueError("terms must be a list")
    out = {}
    for term in terms:
        if not isinstance(term, list) or len(term) != 2:
            raise ValueError("malformed polynomial term")
        coefficient, exponent = term
        if (
            not isinstance(coefficient, list)
            or len(coefficient) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in coefficient)
            or coefficient[1] == 0
        ):
            raise ValueError("malformed rational coefficient")
        if (
            not isinstance(exponent, list)
            or len(exponent) != variables
            or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in exponent)
        ):
            raise ValueError("malformed exponent vector")
        q = Fraction(coefficient[0], coefficient[1])
        key = tuple(exponent)
        out[key] = out.get(key, 0) + q
    return {e: c for e, c in out.items() if c}


def _rat_json(value):
    q = Fraction(value)
    return [q.numerator, q.denominator]


def _draw_nonzero(rng, height):
    value = rng.randint(1, 2 * height)
    return value if value <= height else -(value - height)


def _draw_center_gap(rng, height):
    # Rejection sampling is uniform on the declared set of H(2H-1) pairs.
    while True:
        center = rng.randint(-height, height)
        gap = rng.randint(1, height)
        if gap != abs(center):
            return center, gap


def _answer_from_values(order, links, offsets, center, gap):
    return {
        "order": list(order),
        "links": [_rat_json(v) for v in links],
        "offsets": [_rat_json(v) for v in offsets],
        "center": _rat_json(center),
        "gap": _rat_json(gap),
    }


def _coordinate_product(variables, order, links, offsets):
    product = _pconst(1, variables)
    for i, variable in enumerate(order):
        linear = _padd(_pvar(variable, variables), _pconst(offsets[i], variables))
        if i + 1 < variables:
            linear = _padd(
                linear,
                _pscale(_pvar(order[i + 1], variables), links[i]),
            )
        product = _pmul(product, linear)
    return product


def _screen_points(variables):
    return [
        tuple(i + 2 for i in range(variables)),
        tuple(-(i + 3) for i in range(variables)),
    ]


def _instance_from_poly(poly, variables, height, answer, seed, rng=None):
    terms = _poly_to_terms(poly)
    if rng is not None:
        rng.shuffle(terms)
    checks = [[list(point), _rat_json(_peval(poly, point))] for point in _screen_points(variables)]
    return {
        "family": "affine-binomial principal-ideal primary decomposition",
        "ring": {"field": "Q", "variables": [f"x{i}" for i in range(variables)]},
        "variables": variables,
        "height": height,
        "generator_terms": terms,
        "screen_checks": checks,
        "seed_tag": int(seed),  # never used by canonical_key
        "answer": answer,
    }


def make_instance(n, seed=0, **params):
    """Inverse-generate a primary decomposition certificate before expanding F."""
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 10_000:
        raise ValueError("n must be an integer coefficient height in [2,10000]")
    variables = params.pop("variables", 5)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if (
        isinstance(variables, bool)
        or not isinstance(variables, int)
        or not 2 <= variables <= 7
    ):
        raise ValueError("variables must be an integer in [2,7]")

    rng = random.Random(seed)
    order = list(range(variables))
    rng.shuffle(order)
    links = [rng.randint(1, n) for _ in range(variables - 1)]
    offsets = [_draw_nonzero(rng, n) for _ in range(variables)]
    center, gap = _draw_center_gap(rng, n)

    product = _coordinate_product(variables, order, links, offsets)
    g = _padd(product, _pconst(center, variables))
    f = _padd(_pmul(g, g), _pconst(-(gap * gap), variables))
    answer = _answer_from_values(order, links, offsets, center, gap)
    return _instance_from_poly(f, variables, n, answer, seed, rng)


def _format_polynomial(terms):
    lines = []
    for coefficient, exponent in terms:
        lines.append(f"  {coefficient[0]}/{coefficient[1]} | {json.dumps(exponent)}")
    return "\n".join(lines)


def render(inst):
    variables = inst["variables"]
    height = inst["height"]
    names = ", ".join(inst["ring"]["variables"])
    statement = f"""Work in the polynomial ring R = Q[{names}].  A monomial
x0^e0*...*x{variables - 1}^e{variables - 1} is encoded by its {variables}-entry exponent
vector [e0,...,e{variables - 1}].  The following unordered lines define a sparse
polynomial F exactly; each line is `numerator/denominator | exponent-vector`, and
terms not listed have coefficient zero:

{_format_polynomial(inst['generator_terms'])}

The input module is the principal ideal I=(F), viewed as a submodule of R.

Find a reduced two-component primary decomposition certificate in this bounded
language.  Give:

* `order`: a permutation [v0,...,v{variables - 1}] of the 0-based variable indices;
* `links`: exactly {variables - 1} rationals a_i, each a positive integer in [1,{height}];
* `offsets`: exactly {variables} nonzero integer rationals b_i with |b_i| <= {height};
* `center`: an integer rational c with |c| <= {height}; and
* `gap`: a positive integer rational p <= {height}, with p != |c|.

Every rational must be JSON `[numerator,denominator]` in lowest terms with a
positive denominator (all bounded entries here necessarily have denominator 1).
These data define

  z_i = x_(v_i) + a_i*x_(v_(i+1)) + b_i   for 0 <= i < {variables - 1},
  z_{variables - 1} = x_(v_{variables - 1}) + b_{variables - 1},
  g = z_0*z_1*...*z_{variables - 1} + c.

Your certificate is valid exactly when F = g^2-p^2.  It then denotes the two
components (g-p) and (g+p).  The triangular affine map has determinant 1.  In
the z-coordinates each generator is z_0*...*z_{variables - 1}+(c-p) or
z_0*...*z_{variables - 1}+(c+p); the required nonzero constants make both
generators irreducible (hence prime), and their difference 2p is a unit in Q,
so their intersection is their product (F).  Component order is irrelevant.

Give your final answer inside <answer></answer> tags as one JSON object with
keys `order`, `links`, `offsets`, `center`, `gap` in exactly that form.
Example: <answer>{{"order":[0,1],"links":[[2,1]],"offsets":[[1,1],[-1,1]],"center":[0,1],"gap":[1,1]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON certificate, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    payload = tagged.group(1).strip() if tagged else text.strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        # A common model response fences only the JSON inside the tags.
        match = re.search(r"\{.*\}", payload, re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except (TypeError, ValueError):
            return None
    return value if isinstance(value, dict) else None


def _decode_int_rational(value, label):
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in value)
        or value[1] <= 0
    ):
        raise ValueError(f"{label} must be a [numerator,positive-denominator] rational")
    q = Fraction(value[0], value[1])
    if q.denominator != 1:
        raise ValueError(f"{label} must be an integer rational")
    if [q.numerator, q.denominator] != value:
        raise ValueError(f"{label} must be in lowest terms")
    return q.numerator


def _decode_answer(inst, answer):
    variables = inst["variables"]
    height = inst["height"]
    if not isinstance(answer, dict):
        raise ValueError("answer must be a JSON object")
    if set(answer) != {"order", "links", "offsets", "center", "gap"}:
        raise ValueError("answer must have exactly the five required keys")

    order = answer["order"]
    if not isinstance(order, list) or len(order) != variables:
        raise ValueError(f"order must contain exactly {variables} indices")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in order):
        raise ValueError("order entries must be integer indices")
    if sorted(order) != list(range(variables)):
        raise ValueError("order must be a permutation of all variable indices")

    raw_links = answer["links"]
    if not isinstance(raw_links, list) or len(raw_links) != variables - 1:
        raise ValueError(f"links must contain exactly {variables - 1} rationals")
    links = [_decode_int_rational(v, f"links[{i}]") for i, v in enumerate(raw_links)]
    if any(not 1 <= v <= height for v in links):
        raise ValueError("link coefficient out of declared bounds")

    raw_offsets = answer["offsets"]
    if not isinstance(raw_offsets, list) or len(raw_offsets) != variables:
        raise ValueError(f"offsets must contain exactly {variables} rationals")
    offsets = [
        _decode_int_rational(v, f"offsets[{i}]") for i, v in enumerate(raw_offsets)
    ]
    if any(v == 0 or abs(v) > height for v in offsets):
        raise ValueError("offset must be nonzero and within declared bounds")

    center = _decode_int_rational(answer["center"], "center")
    if abs(center) > height:
        raise ValueError("center is outside the declared bounds")
    gap = _decode_int_rational(answer["gap"], "gap")
    if not 1 <= gap <= height or gap == abs(center):
        raise ValueError("gap must be positive, bounded, and different from |center|")
    return order, links, offsets, center, gap


def _candidate_value(point, order, links, offsets, center, gap):
    product = 1
    for i, variable in enumerate(order):
        value = point[variable] + offsets[i]
        if i + 1 < len(order):
            value += links[i] * point[order[i + 1]]
        product *= value
    g = product + center
    return g * g - gap * gap


def verify(inst, answer):
    """Check any bounded affine certificate; never consult inst['answer']."""
    try:
        order, links, offsets, center, gap = _decode_answer(inst, answer)
    except (TypeError, ValueError) as exc:
        return False, str(exc)

    # Cheap exact screens make the 200k density experiment practical.  Equality
    # at these points is only a rejection filter; survivors still face complete
    # coefficient comparison below.
    for raw_point, raw_value in inst.get("screen_checks", []):
        target = Fraction(raw_value[0], raw_value[1])
        if _candidate_value(raw_point, order, links, offsets, center, gap) != target:
            return False, "polynomial identity fails an exact evaluation screen"

    try:
        target_poly = _terms_to_poly(inst["generator_terms"], inst["variables"])
    except (TypeError, ValueError) as exc:
        return False, "malformed instance polynomial: " + str(exc)
    product = _coordinate_product(inst["variables"], order, links, offsets)
    g = _padd(product, _pconst(center, inst["variables"]))
    candidate_poly = _padd(_pmul(g, g), _pconst(-(gap * gap), inst["variables"]))
    if candidate_poly != target_poly:
        return False, "expanded polynomial identity F = g^2-p^2 does not hold"
    # The decoded shape executes the primaryness certificate: in the displayed
    # triangular coordinates, determinant=1 and c+-p are both nonzero.
    if center - gap == 0 or center + gap == 0:
        return False, "a component has zero binomial constant and is not prime"
    return True, "ok"


def random_candidate(inst, rng):
    variables = inst["variables"]
    height = inst["height"]
    order = list(range(variables))
    rng.shuffle(order)
    links = [rng.randint(1, height) for _ in range(variables - 1)]
    offsets = [_draw_nonzero(rng, height) for _ in range(variables)]
    center, gap = _draw_center_gap(rng, height)
    return _answer_from_values(order, links, offsets, center, gap)


def search_space(inst):
    variables = inst["variables"]
    height = inst["height"]
    return (
        math.factorial(variables)
        * (height ** (variables - 1))
        * ((2 * height) ** variables)
        * height
        * (2 * height - 1)
    )


def enumerate_all(inst):
    total = search_space(inst)
    if total > 200_000:
        return None
    variables = inst["variables"]
    height = inst["height"]
    nonzero = list(range(-height, 0)) + list(range(1, height + 1))
    count = 0
    for order in itertools.permutations(range(variables)):
        for links in itertools.product(range(1, height + 1), repeat=variables - 1):
            for offsets in itertools.product(nonzero, repeat=variables):
                for center in range(-height, height + 1):
                    for gap in range(1, height + 1):
                        if gap == abs(center):
                            continue
                        answer = _answer_from_values(order, links, offsets, center, gap)
                        if verify(inst, answer)[0]:
                            count += 1
    return count


def _canonical_payload(poly, variables):
    # A polynomial canonical form up to arbitrary variable permutation is as
    # hard as a colored-hypergraph isomorphism problem.  The strongest cheap
    # invariant used here keeps both the global exponent-partition profile and
    # the sorted collection of one-variable incidence profiles.  It is exactly
    # invariant, much stronger than a coefficient multiset, and avoids m! work.
    global_profile = []
    variable_profiles = [[] for _ in range(variables)]
    for exponent, coefficient in poly.items():
        q = Fraction(coefficient)
        coefficient_key = (q.numerator, q.denominator)
        global_profile.append((tuple(sorted(exponent)), coefficient_key))
        for i in range(variables):
            others = tuple(sorted(exponent[:i] + exponent[i + 1 :]))
            variable_profiles[i].append((exponent[i], others, coefficient_key))
    global_profile.sort()
    normalized_variables = []
    for profile in variable_profiles:
        profile.sort()
        normalized_variables.append(tuple(profile))
    normalized_variables.sort()
    return repr((global_profile, normalized_variables)).encode("ascii")


def canonical_key(inst):
    poly = _terms_to_poly(inst["generator_terms"], inst["variables"])
    payload = _canonical_payload(poly, inst["variables"])
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    harder = dict(params)
    current = harder.get("n")
    if isinstance(current, bool) or not isinstance(current, int):
        return None
    if current >= 10_000:
        return "cap_bound"
    harder["n"] = min(10_000, current * 2)
    return harder


# ---------------------------------------------------------------------------
# Exact Track-B reference algorithm.  It does not read the planted answer.


def _monomial_order(exponent):
    return (sum(exponent), exponent)


def _sqrt_fraction(value):
    q = Fraction(value)
    if q < 0:
        return None
    a = math.isqrt(q.numerator)
    b = math.isqrt(q.denominator)
    return Fraction(a, b) if a * a == q.numerator and b * b == q.denominator else None


def _square_root_mod_constant(poly, counter):
    """Recover A and constant r from poly=A^2+r by long square-root extraction."""
    if not poly:
        return None
    lead_exp = max(poly, key=_monomial_order)
    lead_coeff = Fraction(poly[lead_exp])
    if any(v % 2 for v in lead_exp):
        return None
    root_coeff = _sqrt_fraction(lead_coeff)
    if root_coeff is None:
        return None
    root_exp = tuple(v // 2 for v in lead_exp)
    root = {root_exp: root_coeff}
    residual = _psub(poly, _pmul(root, root, counter))
    variables = len(lead_exp)
    zero = (0,) * variables
    limit = len(poly) + 2
    for _ in range(limit):
        nonconstant = [e for e in residual if e != zero]
        if not nonconstant:
            constant = Fraction(residual.get(zero, 0))
            return root, constant
        exponent = max(nonconstant, key=_monomial_order)
        delta = tuple(exponent[i] - root_exp[i] for i in range(variables))
        if any(v < 0 for v in delta) or delta in root:
            return None
        coefficient = Fraction(residual[exponent], 2 * root_coeff)
        term = {delta: coefficient}
        # (root+term)^2-root^2 = 2*root*term+term^2.
        update = _padd(_pscale(_pmul(root, term, counter), 2), _pmul(term, term, counter))
        residual = _psub(residual, update)
        counter[0] += len(update)
        root[delta] = coefficient
    return None


def _slice(poly, variable, degree):
    out = {}
    for exponent, coefficient in poly.items():
        if exponent[variable] == degree:
            reduced = list(exponent)
            reduced[variable] = 0
            out[tuple(reduced)] = coefficient
    return out


def _divide_by_monic_linear(poly, variable, tail, counter):
    """Exact division by x_variable+tail, or None when the remainder is nonzero."""
    degree = max((e[variable] for e in poly), default=-1)
    if degree < 1:
        return None
    pieces = [_slice(poly, variable, k) for k in range(degree + 1)]
    quotient_pieces = [None] * degree
    quotient_pieces[degree - 1] = pieces[degree]
    for k in range(degree - 1, 0, -1):
        product = _pmul(tail, quotient_pieces[k], counter)
        quotient_pieces[k - 1] = _psub(pieces[k], product)
        counter[0] += len(pieces[k]) + len(product)
    remainder = _psub(pieces[0], _pmul(tail, quotient_pieces[0], counter))
    counter[0] += len(pieces[0])
    if remainder:
        return None
    quotient = {}
    for degree_index, piece in enumerate(quotient_pieces):
        for exponent, coefficient in piece.items():
            lifted = list(exponent)
            lifted[variable] = degree_index
            quotient[tuple(lifted)] = coefficient
    return quotient


def _factor_chain(product, variables, height, counter):
    """Bounded exact trial division for the declared triangular language."""
    nonzero = list(range(-height, 0)) + list(range(1, height + 1))

    def recurse(poly, current, remaining, reversed_nodes):
        if not remaining:
            zero = (0,) * variables
            if poly == {zero: 1}:
                nodes = list(reversed(reversed_nodes))
                order = [node[0] for node in nodes]
                offsets = [node[2] for node in nodes]
                links = [node[1] for node in nodes[:-1]]
                return order, links, offsets
            return None
        for variable in sorted(remaining):
            for link in range(1, height + 1):
                for offset in nonzero:
                    tail = _padd(
                        _pscale(_pvar(current, variables), link),
                        _pconst(offset, variables),
                    )
                    quotient = _divide_by_monic_linear(poly, variable, tail, counter)
                    if quotient is None:
                        continue
                    result = recurse(
                        quotient,
                        variable,
                        remaining - {variable},
                        reversed_nodes + [(variable, link, offset)],
                    )
                    if result is not None:
                        return result
        return None

    for terminal in range(variables):
        for offset in nonzero:
            tail = _pconst(offset, variables)
            quotient = _divide_by_monic_linear(product, terminal, tail, counter)
            if quotient is None:
                continue
            result = recurse(
                quotient,
                terminal,
                set(range(variables)) - {terminal},
                [(terminal, None, offset)],
            )
            if result is not None:
                return result
    return None


def _reference_algorithm(inst):
    """Mechanical square-root plus bounded trial division; returns answer, ops."""
    counter = [0]
    poly = _terms_to_poly(inst["generator_terms"], inst["variables"])
    recovered = _square_root_mod_constant(poly, counter)
    if recovered is None:
        return None, counter[0]
    g, residual_constant = recovered
    if residual_constant >= 0:
        return None, counter[0]
    gap = _sqrt_fraction(-residual_constant)
    if gap is None or gap.denominator != 1:
        return None, counter[0]
    height = inst["height"]
    variables = inst["variables"]
    for center in range(-height, height + 1):
        product = _psub(g, _pconst(center, variables))
        factored = _factor_chain(product, variables, height, counter)
        if factored is None:
            continue
        order, links, offsets = factored
        answer = _answer_from_values(order, links, offsets, center, gap.numerator)
        if verify(inst, answer)[0]:
            return answer, counter[0]
    return None, counter[0]


def _compact_route(inst):
    """Recover the witness by the intended coefficient-chain insight.

    The returned count includes every exact rational arithmetic operation after
    locating the relevant coefficients.  Dictionary lookups and comparisons
    are not arithmetic operations.  This makes G9(c) an executable measurement
    independent of the planted answer rather than a formula-based estimate.
    """
    poly = _terms_to_poly(inst["generator_terms"], inst["variables"])
    variables = inst["variables"]
    operations = 0
    baseline = [2] * variables

    # In the top layer H^2, lowering x_u and raising x_v from the baseline
    # occurs exactly when u precedes v in the hidden path.  A cover relation has
    # coefficient 2*a_u.
    successors = {u: [] for u in range(variables)}
    relation_coefficients = {}
    for u in range(variables):
        for v in range(variables):
            if u == v:
                continue
            exponent = list(baseline)
            exponent[u] = 1
            exponent[v] = 3
            coefficient = Fraction(poly.get(tuple(exponent), 0))
            if coefficient:
                successors[u].append(v)
                relation_coefficients[(u, v)] = coefficient
    order = sorted(range(variables), key=lambda u: len(successors[u]), reverse=True)
    expected_degrees = list(range(variables - 1, -1, -1))
    if [len(successors[u]) for u in order] != expected_degrees:
        return None, operations

    links = []
    for i in range(variables - 1):
        coefficient = relation_coefficients.get((order[i], order[i + 1]))
        if coefficient is None:
            return None, operations
        links.append(coefficient / 2)
        operations += 1

    # Half the degree-(2m-1) coefficient lowered at v_i is
    # S_i=b_i+2*a_i*S_(i+1), with S_last=b_last.
    tails = []
    for variable in order:
        exponent = list(baseline)
        exponent[variable] = 1
        tails.append(Fraction(poly.get(tuple(exponent), 0)) / 2)
        operations += 1
    offsets = [Fraction(0)] * variables
    offsets[-1] = tails[-1]
    for i in range(variables - 2, -1, -1):
        offsets[i] = tails[i] - 2 * links[i] * tails[i + 1]
        operations += 3

    # Coefficient of x_0*...*x_(m-1) in q^2, q=product(z_i), via a
    # two-state path recurrence.  State 1 says the next variable was already
    # selected by the preceding squared linear factor.
    state = [Fraction(1), Fraction(0)]
    for i in range(variables - 1):
        a = links[i]
        b = offsets[i]
        weights = [b * b, 2 * b, 2 * a * b, 2 * a]
        operations += 5
        following = [Fraction(0), Fraction(0)]
        following[0] += state[0] * weights[1]
        following[1] += state[0] * weights[3]
        following[0] += state[1] * weights[0]
        following[1] += state[1] * weights[2]
        operations += 8
        state = following
    last = offsets[-1]
    terminal_linear = 2 * last
    terminal_constant = last * last
    operations += 2
    squarefree_coefficient = (
        state[0] * terminal_linear + state[1] * terminal_constant
    )
    operations += 3

    # F=(q+c)^2-p^2.  The squarefree degree-m coefficient is the q^2
    # coefficient above plus 2c; the constant coefficient then determines p.
    center = (Fraction(poly.get((1,) * variables, 0)) - squarefree_coefficient) / 2
    operations += 2
    q_constant = Fraction(1)
    for offset in offsets:
        q_constant *= offset
        operations += 1
    gap_squared = (
        (q_constant + center) ** 2
        - Fraction(poly.get((0,) * variables, 0))
    )
    operations += 3
    gap = _sqrt_fraction(gap_squared)
    if gap is None:
        return None, operations
    recovered = links + offsets + [center, gap]
    if any(value.denominator != 1 for value in recovered):
        return None, operations
    answer = _answer_from_values(
        order,
        [value.numerator for value in links],
        [value.numerator for value in offsets],
        center.numerator,
        gap.numerator,
    )
    return answer, operations


# ---------------------------------------------------------------------------
# Adversarial probes and self-test.


def _candidate_from_stat(inst, mode):
    variables = inst["variables"]
    height = inst["height"]
    poly = _terms_to_poly(inst["generator_terms"], variables)
    stats = []
    for variable in range(variables):
        if mode == "frequency":
            score = sum(1 + e[variable] for e in poly)
        else:
            score = sum(abs(int(Fraction(c))) * (1 + e[variable]) for e, c in poly.items())
        stats.append((score, variable))
    order = [variable for _, variable in sorted(stats, reverse=(mode != "frequency"))]
    links = [1 + (abs(stats[i][0]) % height) for i in range(variables - 1)]
    offsets = [(-1 if i % 2 else 1) * (1 + (abs(stats[i][0]) % height)) for i in range(variables)]
    center = 0
    gap = 1
    return _answer_from_values(order, links, offsets, center, gap)


def _attack_outlier(inst):
    answer = _candidate_from_stat(inst, "frequency")
    return verify(inst, answer)[0]


def _attack_greedy(inst):
    answer = _candidate_from_stat(inst, "magnitude")
    return verify(inst, answer)[0]


def _attack_diagonal_ansatz(inst):
    variables = inst["variables"]
    answer = _answer_from_values(
        list(range(variables)),
        [1] * (variables - 1),
        [1 if i % 2 == 0 else -1 for i in range(variables)],
        0,
        1,
    )
    return verify(inst, answer)[0]


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed ^ 0x6A09E667)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _atom_count(value):
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def _permute_instance(inst, old_to_new, reorder_terms=True):
    variables = inst["variables"]
    poly = _terms_to_poly(inst["generator_terms"], variables)
    moved = {}
    for exponent, coefficient in poly.items():
        new_exp = [0] * variables
        for old, power in enumerate(exponent):
            new_exp[old_to_new[old]] = power
        moved[tuple(new_exp)] = coefficient
    answer = copy.deepcopy(inst["answer"])
    answer["order"] = [old_to_new[v] for v in answer["order"]]
    transformed = _instance_from_poly(
        moved,
        variables,
        inst["height"],
        answer,
        inst.get("seed_tag", 0),
        None,
    )
    if reorder_terms:
        transformed["generator_terms"].reverse()
    return transformed


def selftest():
    report = {}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    base = inst["answer"]
    corruptions = {}

    changed = copy.deepcopy(base)
    changed["offsets"] = changed["offsets"][:-1]
    corruptions["drop_one"] = verify(inst, changed)

    changed = copy.deepcopy(base)
    changed["order"][0], changed["order"][-1] = changed["order"][-1], changed["order"][0]
    corruptions["swap_two"] = verify(inst, changed)

    changed = copy.deepcopy(base)
    changed["order"][1] = changed["order"][0]
    corruptions["duplicate_index"] = verify(inst, changed)

    corruptions["empty"] = verify(inst, [])

    changed = copy.deepcopy(base)
    changed["links"][0] = [inst["height"] + 1, 1]
    corruptions["out_of_range"] = verify(inst, changed)

    reasons = [value[1] for value in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not value[0] for value in corruptions.values()) and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": value[0], "reason": value[1]} for name, value in corruptions.items()},
    }

    response = (
        "I used the triangular homogeneous chain and checked the product exactly.\n"
        "```json\n<answer>"
        + json.dumps(base, separators=(",", ":"))
        + "</answer>\n```\nThe two generators differ by a rational unit."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == base and verify(inst, parsed)[0],
        "parsed": parsed == base,
    }

    samples = 200_000
    hits = 0
    rng = random.Random(271828)
    started = time.perf_counter()
    for _ in range(samples):
        if verify(inst, random_candidate(inst, rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "certificate_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    attack_seeds = list(range(800, 808))
    attacks = {
        "outlier_term_frequency": {"successes": 0, "attempts": len(attack_seeds)},
        "greedy_coefficient_magnitude": {"successes": 0, "attempts": len(attack_seeds)},
        "random_restart_256": {"successes": 0, "attempts": len(attack_seeds)},
        "diagonal_coordinate_ansatz": {"successes": 0, "attempts": len(attack_seeds)},
    }
    reference_successes = 0
    reference_operations = []
    reference_seconds = []
    compact_successes = 0
    compact_operations = []
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping_params)
        attacks["outlier_term_frequency"]["successes"] += int(_attack_outlier(trial))
        attacks["greedy_coefficient_magnitude"]["successes"] += int(_attack_greedy(trial))
        attacks["random_restart_256"]["successes"] += int(_attack_random_restart(trial, seed))
        attacks["diagonal_coordinate_ansatz"]["successes"] += int(_attack_diagonal_ansatz(trial))
        t0 = time.perf_counter()
        recovered, operations = _reference_algorithm(trial)
        elapsed = time.perf_counter() - t0
        solved = recovered is not None and verify(trial, recovered)[0]
        reference_successes += int(solved)
        reference_operations.append(operations)
        reference_seconds.append(elapsed)
        compact, compact_ops = _compact_route(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
        compact_operations.append(compact_ops)

    all_failed = all(value["successes"] == 0 for value in attacks.values())
    reference = {
        "name": "exact multivariate square-root extraction plus bounded affine trial division",
        "complexity": "O(T^2 + n^2*m^2*T^2) exact coefficient operations",
        "wall_clock_sec": round(sum(reference_seconds) / len(reference_seconds), 6),
        "operations": round(sum(reference_operations) / len(reference_operations)),
        "max_operations": max(reference_operations),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count is not None
            and reference_successes == len(attack_seeds)
            and compact_successes == len(attack_seeds)
        ),
        "shipping_sampled_valid_fraction": hits / samples,
        "shipping_density_samples": samples,
        "shipping_density_hits": hits,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "baseline_wall_clock_sec": reference["wall_clock_sec"],
        "baseline_operations": reference["operations"],
        "compact_route_operations": max(compact_operations),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=123456, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "space_ratio_floor": search_space(doubled) // search_space(inst),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_witness_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **shipping_params)
        key = canonical_key(original)
        keys.append(key)
        rng_perm = random.Random(90_000 + seed)
        first = list(range(original["variables"]))
        second = list(range(original["variables"]))
        rng_perm.shuffle(first)
        rng_perm.shuffle(second)
        composed = [second[first[i]] for i in range(original["variables"])]
        for permutation in (first, composed):
            transformed = _permute_instance(original, permutation, True)
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append([seed, "key changed under variable permutation"])
            ok, reason = verify(transformed, transformed["answer"])
            carried_witness_checks += 1
            if not ok:
                g8_failures.append([seed, "carried witness failed: " + reason])
        reordered = copy.deepcopy(original)
        reordered["generator_terms"].reverse()
        invariant_checks += 1
        if canonical_key(reordered) != key:
            g8_failures.append([seed, "key changed under term reordering"])
        ok, reason = verify(reordered, original["answer"])
        carried_witness_checks += 1
        if not ok:
            g8_failures.append([seed, "original witness failed after term reorder: " + reason])
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(keys)) == len(keys),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_unrelated": len(set(keys)),
        "unrelated_attempts": len(keys),
        "failures": g8_failures,
    }

    height = inst["height"]
    worst_case_answer = _answer_from_values(
        list(range(inst["variables"])),
        [height] * (inst["variables"] - 1),
        [-height] * inst["variables"],
        -height,
        height - 1,
    )
    answer_blob = json.dumps(worst_case_answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atom_count(worst_case_answer)
    compact_answer, intended_operations = _compact_route(inst)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    compact_ok = compact_answer is not None and verify(inst, compact_answer)[0]
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and compact_ok
    )
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and hinted_hardened,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verified": compact_ok,
    }
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
