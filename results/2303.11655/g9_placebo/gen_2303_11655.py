"""Exact telescoping-polynomial generator for arXiv:2303.11655.

Lemma 4.1 of the paper supplies the factor chain used in its infinite family of
block-transitive designs.  This module applies independent monomial
substitutions to three copies of that identity, shuffles all factors, and asks
for their exact sparse product.  The product is planted by composition of
identities; generation never expands or solves the displayed instance.
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


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
try:
    from gvlib import sparse_poly
except ImportError:                 # pragma: no cover - exact fallback below
    sparse_poly = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "sparse multivariate polynomials over Q",
        "monomial substitutions of the factor chain in Lemma 4.1",
        "an exact sparse product polynomial",
    ],
    "verification_operations": [
        "exact rational coefficient multiplication and addition",
        "exact exponent-vector addition",
        "exact sparse-polynomial identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The shuffled factors split into exponent rays carrying telescoping "
        "power-of-two chains; without that decomposition one must perform "
        "large exact sparse convolutions."
    ),
    "hardness_basis": (
        "Track B: minimum-support pairwise sparse multiplication is an exact "
        "reference algorithm with O(d*m^3) arithmetic on this promised family; "
        "at the hard preset and reporting seed it is measured by selftest, while "
        "the Lemma 4.1 exponent-ray route needs at most 153 exact arithmetic "
        "operations and must be recognized without a CAS."
    ),
    "max_answer_tokens": 500,
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
        "One canonical sparse polynomial over Q in the displayed variables, "
        "encoded as {nvars, terms}; at the three-chain presets it has exactly "
        "27 distinct terms, coefficients in {-1,+1}, exponent vectors inside "
        "the displayed componentwise product-degree box, forced constant and "
        "top terms, and ascending graded-lexicographic term order."
    ),
    "bounds": {
        "nvars": "the displayed variable count (1 for demo, 3 otherwise)",
        "nonzero_terms": "3^chains (3 for demo, 27 otherwise)",
        "coefficient_numerators": [-1, 1],
        "coefficient_denominator": 1,
        "exponents": "0 through the displayed componentwise degree bounds",
        "term_order": "ascending (total degree, exponent vector)",
    },
}

DIFFICULTY: dict = {
    "hard": {"n": 30, "chains": 3, "variables": 3},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "The exponent supports lie on a few rays, and along each ray their scales "
    "are consecutive powers of two."
)
PLACEBO_HINT: str = (
    "The exponent vectors are nonnegative, and every displayed rational "
    "coefficient is already in lowest terms."
)

# Filled from harness-owned transcripts after the three arms are run.  Zero
# attempts make missing external evidence explicit rather than manufacturing a
# result from an unavailable service.
G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not yet run",
}

NOTES = r"""
Paper grounding.  Section 2.1 defines the point set as a product of coordinate
sets and the chain C_0 < ... < C_s by agreement in successively longer suffixes.
Section 2.2 identifies the s strong-inner-pair classes.  Definition 2.2 defines
the array of a point subset, and Theorem 1.3 gives the exact array equations
equivalent to the orbit being a 2-design.  The algebraic source used here is
Lemma 4.1 and its proof: e_1=p^2+p+1 and
e_i=p^(2^(i-1))-p^(2^(i-2))+1 have prefix product
p^(2^i)+p^(2^(i-1))+1.  Construction 4.3 uses precisely these factors to make
the chain parameters of the paper's infinite design family.

Step-0 discrimination and track.  The paper gives the telescoping identity
explicitly, so a Track-A claim would be false.  Exact sparse multiplication is
also an efficient certificate-producing algorithm on these finite inputs.  The
family is therefore Track B.  The mechanical reference repeatedly tries every
pair of current sparse factors and multiplies the pair with smallest resulting
support; on the promised distribution its support stays bounded and the run is
O(d*m^3).  Its measured shipping cost is reported by selftest.  Once the hidden
exponent-ray decomposition is noticed, Lemma 4.1 replaces each long chain by a
trinomial and the three trinomials need only 153 counted exact operations.

Generation route.  The generator samples independent primitive exponent
directions by nonnegative unimodular row operations.  For each direction a it
constructs the formal factors 1+X^a+X^(2a), 1-X^a+X^(2a), and
1-X^(2^j a)+X^(2^(j+1) a).  It also samples harmless factor signs and shuffles
both factors and their terms.  Lemma 4.1 gives the product on each ray before
the public factors are assembled; the three known trinomials are then composed
by exact polynomial multiplication.  No public instance is solved.

Easy regimes and attacks.  With one short ray the identity is a hand example;
with ordered factors the recurrence is visible immediately.  Shipping uses
three mixed exponent directions and ninety shuffled factors.  The panel checks
largest-factor outliers, displayed-order greedy truncation, a coordinate-axis
ansatz, a univariate total-degree ansatz, and 256 structure-aware random
restarts.  They fail because plant and decoys are the same factors: only the
global exponent-ray relation distinguishes which cancellations compose.  The
successful exact sparse reference algorithm is disclosed separately, as Track
B requires.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _validate_parameters(n, chains, variables):
    for name, value in (("n", n), ("chains", chains), ("variables", variables)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 2:
        raise ValueError("n must be at least 2")
    if not 1 <= chains <= variables <= 6:
        raise ValueError("require 1 <= chains <= variables <= 6")
    if chains not in (1, 3):
        raise ValueError("this family supports one demo chain or three full chains")
    if chains == 1 and variables != 1:
        raise ValueError("the one-chain demo uses one variable")
    if chains == 3 and variables != 3:
        raise ValueError("the full family uses three variables")


def _graded_key(exponents):
    return (sum(exponents), tuple(exponents))


def _poly_to_json(poly, nvars):
    """Canonical gvlib-compatible JSON for dict[tuple] -> Fraction/int."""
    normalized = {}
    for exponents, coefficient in poly.items():
        q = coefficient if isinstance(coefficient, Fraction) else Fraction(coefficient)
        if q:
            normalized[tuple(exponents)] = normalized.get(tuple(exponents), Fraction(0)) + q
    normalized = {e: c for e, c in normalized.items() if c}
    if sparse_poly is not None:
        return sparse_poly.to_json(sparse_poly.normalize(normalized, nvars=nvars))
    return {
        "nvars": nvars,
        "terms": [
            [list(e), [c.numerator, c.denominator]]
            for e, c in sorted(normalized.items(), key=lambda item: _graded_key(item[0]))
        ],
    }


def _poly_from_json(obj, nvars):
    if sparse_poly is not None:
        return sparse_poly.from_json(obj, nvars=nvars)
    if not isinstance(obj, dict) or obj.get("nvars") != nvars:
        raise ValueError("polynomial needs the required nvars")
    terms = obj.get("terms")
    if not isinstance(terms, list):
        raise ValueError("polynomial terms must be a list")
    out = {}
    for item in terms:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("each term must be [exponents,[num,den]]")
        exponents, rational = item
        if not isinstance(exponents, list) or len(exponents) != nvars:
            raise ValueError("wrong exponent-vector width")
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in exponents):
            raise ValueError("exponents must be nonnegative integers")
        if not isinstance(rational, list) or len(rational) != 2:
            raise ValueError("coefficient must be [num,den]")
        num, den = rational
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (num, den)) or den <= 0:
            raise ValueError("invalid rational coefficient")
        q = Fraction(num, den)
        key = tuple(exponents)
        out[key] = out.get(key, Fraction(0)) + q
    return {e: c for e, c in out.items() if c}


def _mul_poly(left, right):
    if sparse_poly is not None:
        return sparse_poly.mul(left, right)
    out = {}
    for a, ca in left.items():
        for b, cb in right.items():
            exponent = tuple(x + y for x, y in zip(a, b))
            out[exponent] = out.get(exponent, Fraction(0)) + ca * cb
            if out[exponent] == 0:
                del out[exponent]
    return out


def _directions(chains, variables, rng):
    if chains == 1:
        return [[1]]
    matrix = [[1 if i == j else 0 for j in range(variables)]
              for i in range(chains)]
    # Nonnegative unimodular row shears preserve independence and primitivity.
    for _ in range(10):
        target, source = rng.sample(range(chains), 2)
        multiplier = rng.randrange(1, 4)
        matrix[target] = [
            x + multiplier * y for x, y in zip(matrix[target], matrix[source])
        ]
    rng.shuffle(matrix)
    return matrix


def _factor(direction, stage, unit, nvars, rng):
    zero = (0,) * nvars
    if stage == 0:
        middle_scale, middle_sign = 1, 1
    else:
        middle_scale, middle_sign = 1 << (stage - 1), -1
    high_scale = 2 * middle_scale
    middle = tuple(middle_scale * value for value in direction)
    high = tuple(high_scale * value for value in direction)
    raw = {
        zero: unit,
        middle: unit * middle_sign,
        high: unit,
    }
    encoded = _poly_to_json(raw, nvars)
    rng.shuffle(encoded["terms"])
    return encoded


def _planted_product(directions, n, chain_units, nvars):
    product = {(0,) * nvars: Fraction(1)}
    scale = 1 << (n - 1)
    for direction, unit in zip(directions, chain_units):
        middle = tuple(scale * value for value in direction)
        high = tuple(2 * value for value in middle)
        trinomial = {
            (0,) * nvars: Fraction(unit),
            middle: Fraction(unit),
            high: Fraction(unit),
        }
        product = _mul_poly(product, trinomial)
    return product


def make_instance(n, seed=0, **params) -> dict:
    """Construct a shuffled composition of Lemma 4.1 identities."""
    chains = params.pop("chains", 3)
    variables = params.pop("variables", chains)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, chains, variables)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    directions = _directions(chains, variables, rng)
    factors = []
    chain_units = []
    for direction in directions:
        units = [rng.choice((-1, 1)) for _ in range(n)]
        chain_units.append(math.prod(units))
        for stage, unit in enumerate(units):
            factors.append(_factor(direction, stage, unit, variables, rng))
    rng.shuffle(factors)

    answer_poly = _planted_product(directions, n, chain_units, variables)
    answer = _poly_to_json(answer_poly, variables)
    degree_bounds = [0] * variables
    constant_coefficient = 1
    leading_coefficient = 1
    for factor in factors:
        decoded = _poly_from_json(factor, variables)
        constant_coefficient *= int(decoded[(0,) * variables])
        top_exp, top_coeff = max(decoded.items(), key=lambda item: _graded_key(item[0]))
        degree_bounds = [x + y for x, y in zip(degree_bounds, top_exp)]
        leading_coefficient *= int(top_coeff)
    return {
        "paper": "arXiv:2303.11655",
        "family": "shuffled Lemma 4.1 factor chains",
        "n": n,
        "chains": chains,
        "variables": variables,
        "factor_count": len(factors),
        "promised_terms": 3 ** chains,
        "degree_bounds": degree_bounds,
        "constant_coefficient": constant_coefficient,
        "leading_coefficient": leading_coefficient,
        "factors": factors,
        "answer": answer,
    }


def _factor_line(index, factor):
    return f"F{index:03d} = " + json.dumps(factor["terms"], separators=(",", ":"))


def render(inst) -> str:
    variables = inst["variables"]
    variable_list = ",".join(f"x{index}" for index in range(variables))
    exponent_list = ",".join(f"a{index}" for index in range(variables))
    monomial = "*".join(f"x{index}^a{index}" for index in range(variables))
    lines = [
        "Compute an exact sparse polynomial product.",
        "",
        "Definitions.",
        f"Work in Q[{variable_list}].  An exponent vector [{exponent_list}] denotes the monomial {monomial}.",
        "A rational is [numerator,denominator] in lowest terms with positive denominator.",
        "A term is [exponent_vector,rational_coefficient].  Each line below is one polynomial given as a list of terms; term order on input lines is irrelevant.",
        "Polynomial multiplication is ordinary distributive multiplication over Q: add exponent vectors and collect equal monomials exactly.",
        "",
        f"There are {inst['factor_count']} displayed factors in {variables} variables.",
        f"Their product is promised to have exactly {inst['promised_terms']} nonzero monomials, each with coefficient +1 or -1.",
        f"Every output exponent must lie componentwise between zero and {inst['degree_bounds']} inclusive.",
        f"The constant coefficient is {inst['constant_coefficient']} and the coefficient of the componentwise top exponent {inst['degree_bounds']} is {inst['leading_coefficient']}.",
        "The promise and these forced endpoint terms are part of the answer language; no other factorization or construction is disclosed.",
        "",
        "Factors:",
    ]
    lines.extend(_factor_line(index, factor)
                 for index, factor in enumerate(inst["factors"], 1))
    lines.extend([
        "",
        "Return the product in canonical gvlib JSON form:",
        '{"nvars":d,"terms":[[exponent_vector,[numerator,denominator]],...]}.',
        f"Use nvars={variables}, exactly {inst['promised_terms']} distinct terms, and sort terms in ascending order by (sum of exponents, then exponent vector lexicographically).",
        "Do not omit zero coordinates, do not repeat monomials, and do not use decimal coefficients.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object in the exact format above.",
        '<answer>{"nvars":1,"terms":[[[0],[1,1]],[[2],[-1,1]],[[5],[1,1]]]}</answer>',
        "The example shows syntax only and is not the answer to this instance. Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the JSON polynomial from tags or a surrounding model response."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    body = match.group(1).strip() if match else text.strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    candidates = [body]
    first, last = body.find("{"), body.rfind("}")
    if 0 <= first < last:
        candidates.append(body[first:last + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _primitive_and_scale(vector):
    scale = 0
    for value in vector:
        scale = math.gcd(scale, value)
    if scale <= 0:
        raise ValueError("zero exponent direction")
    return tuple(value // scale for value in vector), scale


def _structured_product(inst):
    """Derive the exact product from factor data, never from inst['answer']."""
    nvars = inst["variables"]
    zero = (0,) * nvars
    groups = {}
    all_units = 1
    for factor in inst["factors"]:
        poly = _poly_from_json(factor, nvars)
        if len(poly) != 3 or zero not in poly:
            raise ValueError("a displayed factor is not a trinomial with a constant")
        constant = poly[zero]
        if constant not in (Fraction(-1), Fraction(1)):
            raise ValueError("a factor unit is not +1 or -1")
        nonzero = sorted((e for e in poly if e != zero), key=_graded_key)
        small, large = nonzero
        if tuple(2 * value for value in small) != large:
            raise ValueError("a factor support is not {0,a,2a}")
        if poly[large] != constant or poly[small] not in (constant, -constant):
            raise ValueError("a factor coefficient pattern is invalid")
        direction, scale = _primitive_and_scale(small)
        middle_sign = int(poly[small] / constant)
        groups.setdefault(direction, []).append((scale, middle_sign))
        all_units *= int(constant)

    if len(groups) != inst["chains"]:
        raise ValueError("wrong number of exponent rays")
    expected_scales = [(1, 1), (1, -1)] + [
        (1 << (stage - 1), -1) for stage in range(2, inst["n"])
    ]
    for entries in groups.values():
        if sorted(entries) != sorted(expected_scales):
            raise ValueError("an exponent ray is not a complete Lemma 4.1 chain")

    product = {zero: Fraction(all_units)}
    top_scale = 1 << (inst["n"] - 1)
    # The scalar unit has already been accumulated globally, so use monic
    # trinomials here.
    for direction in sorted(groups):
        middle = tuple(top_scale * value for value in direction)
        high = tuple(2 * value for value in middle)
        product = _mul_poly(product, {
            zero: Fraction(1), middle: Fraction(1), high: Fraction(1)
        })
    return product


def _validate_answer_shape(inst, answer):
    if not isinstance(answer, dict):
        return None, "answer must be a JSON polynomial object"
    if answer.get("nvars") != inst["variables"]:
        return None, f"nvars must equal {inst['variables']}"
    terms = answer.get("terms")
    if not isinstance(terms, list):
        return None, "terms must be a JSON list"
    if not terms:
        return None, "answer terms must be nonempty"
    if len(terms) != inst["promised_terms"]:
        return None, f"expected exactly {inst['promised_terms']} terms"
    seen = set()
    parsed_order = []
    poly = {}
    for index, item in enumerate(terms):
        if not isinstance(item, list) or len(item) != 2:
            return None, f"term {index} must be [exponents,[num,den]]"
        exponents, rational = item
        if not isinstance(exponents, list) or len(exponents) != inst["variables"]:
            return None, f"term {index} has the wrong exponent-vector width"
        if any(isinstance(x, bool) or not isinstance(x, int) for x in exponents):
            return None, f"term {index} exponents must be integers"
        key = tuple(exponents)
        if key in seen:
            return None, f"duplicate monomial at term {index}"
        seen.add(key)
        for coordinate, (value, bound) in enumerate(zip(exponents, inst["degree_bounds"])):
            if value < 0 or value > bound:
                return None, f"term {index} exponent {coordinate} is out of range"
        if not isinstance(rational, list) or len(rational) != 2:
            return None, f"term {index} coefficient must be [num,den]"
        num, den = rational
        if isinstance(num, bool) or isinstance(den, bool) \
                or not isinstance(num, int) or not isinstance(den, int):
            return None, f"term {index} coefficient entries must be integers"
        if den != 1 or num not in (-1, 1):
            return None, f"term {index} coefficient must be +1 or -1 over denominator 1"
        poly[key] = Fraction(num, den)
        parsed_order.append(key)
    canonical = sorted(parsed_order, key=_graded_key)
    if parsed_order != canonical:
        return None, "terms are not in canonical graded-lexicographic order"
    zero = (0,) * inst["variables"]
    top = tuple(inst["degree_bounds"])
    if poly.get(zero) != inst["constant_coefficient"]:
        return None, "constant term is missing or has the wrong forced coefficient"
    if poly.get(top) != inst["leading_coefficient"]:
        return None, "top term is missing or has the wrong forced coefficient"
    return poly, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Check shape and the exact polynomial identity without reading answer."""
    try:
        claimed, reason = _validate_answer_shape(inst, answer)
        if claimed is None:
            return False, reason
        expected = _structured_product(inst)
        if sparse_poly is not None:
            if not sparse_poly.is_zero(sparse_poly.sub(claimed, expected)):
                return False, "claimed polynomial is not the exact product"
        elif claimed != expected:
            return False, "claimed polynomial is not the exact product"
        return True, "ok"
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return False, f"malformed instance or answer: {exc}"


def _grid_size(inst):
    return math.prod(bound + 1 for bound in inst["degree_bounds"])


def _rank_to_exponents(rank, bounds):
    coordinates = []
    for bound in reversed(bounds):
        rank, value = divmod(rank, bound + 1)
        coordinates.append(value)
    return tuple(reversed(coordinates))


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the promised sparse language, endpoints forced."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    term_count = inst["promised_terms"]
    grid = _grid_size(inst)
    if grid < term_count:
        raise ValueError("degree box is smaller than promised support")
    chosen = {0, grid - 1}
    while len(chosen) < term_count:
        chosen.add(rng.randrange(1, grid - 1))
    zero = (0,) * inst["variables"]
    top = tuple(inst["degree_bounds"])
    poly = {}
    for rank in chosen:
        exponent = _rank_to_exponents(rank, inst["degree_bounds"])
        if exponent == zero:
            coefficient = inst["constant_coefficient"]
        elif exponent == top:
            coefficient = inst["leading_coefficient"]
        else:
            coefficient = rng.choice((-1, 1))
        poly[exponent] = Fraction(coefficient)
    return _poly_to_json(poly, inst["variables"])


def search_space(inst) -> int | None:
    grid = _grid_size(inst)
    free_terms = inst["promised_terms"] - 2
    if grid < inst["promised_terms"]:
        return 0
    return math.comb(grid - 2, free_terms) * (1 << free_terms)


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    grid = _grid_size(inst)
    count = 0
    zero = (0,) * inst["variables"]
    top = tuple(inst["degree_bounds"])
    free_terms = inst["promised_terms"] - 2
    for ranks in itertools.combinations(range(1, grid - 1), free_terms):
        for signs in itertools.product((-1, 1), repeat=free_terms):
            poly = {
                zero: Fraction(inst["constant_coefficient"]),
                top: Fraction(inst["leading_coefficient"]),
            }
            for rank, sign in zip(ranks, signs):
                poly[_rank_to_exponents(rank, inst["degree_bounds"])] = Fraction(sign)
            candidate = _poly_to_json(poly, inst["variables"])
            if verify(inst, candidate)[0]:
                count += 1
    return count


def _canonical_factor(factor, variable_permutation):
    terms = []
    for exponents, coefficient in factor["terms"]:
        moved = tuple(exponents[index] for index in variable_permutation)
        terms.append((moved, tuple(coefficient)))
    terms.sort(key=lambda item: (_graded_key(item[0]), item[1]))
    return tuple(terms)


def canonical_key(inst) -> str:
    """Invariant under factor order, term order, and variable relabelling."""
    variables = inst["variables"]
    representatives = []
    for permutation in itertools.permutations(range(variables)):
        factors = sorted(_canonical_factor(factor, permutation)
                         for factor in inst["factors"])
        representatives.append(repr(tuple(factors)))
    canonical = min(representatives)
    payload = (inst["n"], inst["chains"], inst["variables"], canonical)
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def escalate(params) -> dict | str | None:
    harder = dict(params)
    harder["n"] = int(harder["n"]) + 6
    try:
        probe = make_instance(seed=98765, **harder)
    except (TypeError, ValueError):
        return None
    blob = json.dumps(probe["answer"], separators=(",", ":"))
    if len(blob) > 1900 or _answer_atoms(probe["answer"]) > 250:
        return "cap_bound"
    return harder


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _mul_int_counted(left, right, nvars):
    out = {}
    operations = 0
    for a, ca in left.items():
        for b, cb in right.items():
            exponent = tuple(x + y for x, y in zip(a, b))
            operations += nvars
            value = ca * cb
            operations += 1
            if exponent in out:
                value += out[exponent]
                operations += 1
            if value:
                out[exponent] = value
            else:
                out.pop(exponent, None)
    return out, operations


def _reference_product(inst):
    """Mechanical exact pair-lookahead sparse multiplication with cost."""
    nvars = inst["variables"]
    current = []
    for factor in inst["factors"]:
        decoded = _poly_from_json(factor, nvars)
        current.append({e: int(c) for e, c in decoded.items()})
    operations = 0
    pair_trials = 0
    while len(current) > 1:
        best = None
        best_product = None
        best_pair = None
        for left_index in range(len(current) - 1):
            for right_index in range(left_index + 1, len(current)):
                product, cost = _mul_int_counted(
                    current[left_index], current[right_index], nvars
                )
                operations += cost
                pair_trials += 1
                signature = (
                    len(product),
                    sum(sum(e) for e in product),
                    tuple(sorted(product.items(), key=lambda item: _graded_key(item[0]))),
                )
                if best is None or signature < best:
                    best = signature
                    best_product = product
                    best_pair = (left_index, right_index)
        left_index, right_index = best_pair
        current.pop(right_index)
        current.pop(left_index)
        current.append(best_product)
    return current[0], operations, pair_trials


def _candidate_from_exponents(inst, exponents, seed):
    """Turn a heuristic support into a valid-language candidate."""
    grid = _grid_size(inst)
    zero = (0,) * inst["variables"]
    top = tuple(inst["degree_bounds"])
    support = {zero, top}
    for exponent in exponents:
        exponent = tuple(exponent)
        if len(exponent) == inst["variables"] and all(
            0 <= x <= bound for x, bound in zip(exponent, inst["degree_bounds"])
        ):
            support.add(exponent)
        if len(support) >= inst["promised_terms"]:
            break
    rng = random.Random(seed)
    while len(support) < inst["promised_terms"]:
        support.add(_rank_to_exponents(rng.randrange(1, grid - 1),
                                       inst["degree_bounds"]))
    chosen = sorted(support, key=_graded_key)[:inst["promised_terms"]]
    if top not in chosen:
        chosen[-1] = top
    poly = {}
    for exponent in chosen:
        if exponent == zero:
            coefficient = inst["constant_coefficient"]
        elif exponent == top:
            coefficient = inst["leading_coefficient"]
        else:
            coefficient = inst["constant_coefficient"]
        poly[exponent] = Fraction(coefficient)
    # A duplicate introduced by restoring top is repaired deterministically.
    while len(poly) < inst["promised_terms"]:
        exponent = _rank_to_exponents(rng.randrange(1, grid - 1),
                                      inst["degree_bounds"])
        if exponent not in poly:
            poly[exponent] = Fraction(rng.choice((-1, 1)))
    return _poly_to_json(poly, inst["variables"])


def _attack_largest_factors(inst):
    scored = []
    for factor in inst["factors"]:
        poly = _poly_from_json(factor, inst["variables"])
        scored.append((max(sum(e) for e in poly), poly))
    selected = [poly for _, poly in sorted(scored, key=lambda item: item[0], reverse=True)
                [:inst["chains"]]]
    product = {(0,) * inst["variables"]: Fraction(1)}
    for poly in selected:
        product = _mul_poly(product, poly)
    return _candidate_from_exponents(inst, product.keys(), 101)


def _attack_display_greedy(inst):
    product = {(0,) * inst["variables"]: Fraction(1)}
    for factor in inst["factors"]:
        product = _mul_poly(product, _poly_from_json(factor, inst["variables"]))
        if len(product) >= inst["promised_terms"]:
            break
    return _candidate_from_exponents(inst, product.keys(), 202)


def _attack_coordinate_axes(inst):
    half = [bound // 2 for bound in inst["degree_bounds"]]
    axes = []
    for index in range(inst["chains"]):
        vector = [0] * inst["variables"]
        vector[index] = half[index]
        axes.append(tuple(vector))
    support = []
    for choices in itertools.product((0, 1, 2), repeat=inst["chains"]):
        support.append(tuple(sum(choice * axes[row][column]
                                 for row, choice in enumerate(choices))
                             for column in range(inst["variables"])))
    return _candidate_from_exponents(inst, support, 303)


def _attack_univariate_degree(inst):
    maximum = sum(inst["degree_bounds"])
    support = []
    for index in range(inst["promised_terms"]):
        exponent = [0] * inst["variables"]
        exponent[0] = min(inst["degree_bounds"][0],
                          index * maximum // max(1, inst["promised_terms"] - 1))
        support.append(tuple(exponent))
    return _candidate_from_exponents(inst, support, 404)


def _permute_variables(obj, permutation):
    moved = copy.deepcopy(obj)
    for factor in moved["factors"]:
        for term in factor["terms"]:
            term[0] = [term[0][index] for index in permutation]
    moved["degree_bounds"] = [moved["degree_bounds"][index] for index in permutation]
    for term in moved["answer"]["terms"]:
        term[0] = [term[0][index] for index in permutation]
    moved["answer"] = _poly_to_json(
        _poly_from_json(moved["answer"], moved["variables"]), moved["variables"]
    )
    return moved


def _transformed_instances(inst, seed):
    rng = random.Random(seed)
    reordered = copy.deepcopy(inst)
    rng.shuffle(reordered["factors"])

    term_reordered = copy.deepcopy(inst)
    for factor in term_reordered["factors"]:
        factor["terms"].reverse()

    permutation = list(range(inst["variables"]))
    rng.shuffle(permutation)
    variable_relabelled = _permute_variables(inst, permutation)

    composed = _permute_variables(reordered, permutation)
    for factor in composed["factors"]:
        factor["terms"].reverse()
    return [reordered, term_reordered, variable_relabelled, composed]


def selftest() -> dict:
    report = {}
    g1_checks = 0
    g1_ok = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            instance = make_instance(seed=seed, **params)
            ok, _ = verify(instance, instance["answer"])
            json_ok = json.loads(json.dumps(instance["answer"])) == instance["answer"]
            g1_ok &= ok and json_ok
            g1_checks += 1
    report["G1_planted_verifies"] = {
        "pass": bool(g1_ok), "checks": g1_checks,
        "presets": len(DIFFICULTY), "seeds_per_preset": 3,
    }

    shipping = make_instance(seed=4242, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]
    corruptions = {}
    dropped = copy.deepcopy(base)
    dropped["terms"].pop(1)
    corruptions["drop_term"] = dropped
    swapped = copy.deepcopy(base)
    swapped["terms"][0], swapped["terms"][1] = swapped["terms"][1], swapped["terms"][0]
    corruptions["swap_terms"] = swapped
    duplicated = copy.deepcopy(base)
    duplicated["terms"][-1][0] = list(duplicated["terms"][0][0])
    corruptions["duplicate_term"] = duplicated
    empty = {"nvars": shipping["variables"], "terms": []}
    corruptions["empty"] = empty
    out_of_range = copy.deepcopy(base)
    out_of_range["terms"][1][0][0] = shipping["degree_bounds"][0] + 1
    corruptions["out_of_range"] = out_of_range
    bad_coefficient = copy.deepcopy(base)
    bad_coefficient["terms"][1][1] = [2, 1]
    corruptions["bad_coefficient"] = bad_coefficient
    reasons = {}
    all_rejected = True
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        all_rejected &= not ok
        reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": bool(all_rejected and len(set(reasons.values())) == len(reasons)),
        "rejected": sum(not verify(shipping, value)[0]
                        for value in corruptions.values()),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    realistic = (
        "I used the cancellation pattern.\n```json\n<answer>\n"
        + json.dumps(base, separators=(",", ":"))
        + "\n</answer>\n```\nThe tags contain only the polynomial."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == base and verify(shipping, parsed)[0],
        "parsed": parsed is not None,
        "verified": verify(shipping, parsed)[0] if parsed is not None else False,
    }

    samples = 200_000
    hits = 0
    rng = random.Random(90210)
    expected_json = _poly_to_json(_structured_product(shipping), shipping["variables"])
    for _ in range(samples):
        candidate = random_candidate(shipping, rng)
        if candidate == expected_json:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": search_space(shipping),
        "sampling_prior": "uniform supports and signs after forced endpoint constraints",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_results = []
    reference_start = time.perf_counter()
    for seed in range(8):
        instance = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        started = time.perf_counter()
        product, operations, pair_trials = _reference_product(instance)
        elapsed = time.perf_counter() - started
        expected = _structured_product(instance)
        reference_results.append({
            "ok": {e: Fraction(c) for e, c in product.items()} == expected,
            "operations": operations,
            "pair_trials": pair_trials,
            "wall_clock_sec": elapsed,
        })
    reference_total_wall = time.perf_counter() - reference_start
    report["G5_density_and_baseline"] = {
        "pass": hits / samples < 1e-6 and demo_count == 1
                and all(item["ok"] for item in reference_results),
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_sampled_valid_fraction": hits / samples,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_operations": reference_results[0]["operations"],
        "reference_pair_trials": reference_results[0]["pair_trials"],
        "reference_wall_clock_sec": reference_results[0]["wall_clock_sec"],
        "reference_eight_seed_wall_clock_sec": reference_total_wall,
    }

    attacks = {
        "largest_factor_outlier": {"successes": 0, "attempts": 8},
        "display_order_greedy": {"successes": 0, "attempts": 8},
        "coordinate_axis_ansatz": {"successes": 0, "attempts": 8},
        "univariate_degree_ansatz": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
    }
    attack_functions = {
        "largest_factor_outlier": _attack_largest_factors,
        "display_order_greedy": _attack_display_greedy,
        "coordinate_axis_ansatz": _attack_coordinate_axes,
        "univariate_degree_ansatz": _attack_univariate_degree,
    }
    for seed in range(8):
        instance = make_instance(seed=1000 + seed,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, attack in attack_functions.items():
            if verify(instance, attack(instance))[0]:
                attacks[name]["successes"] += 1
        restart_rng = random.Random(7000 + seed)
        solved = any(verify(instance, random_candidate(instance, restart_rng))[0]
                     for _ in range(256))
        attacks["random_restart_256"]["successes"] += int(solved)
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and all(item["ok"] for item in reference_results),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "minimum-support pairwise exact sparse multiplication",
            "complexity": "O(d*m^3) exact arithmetic on this promised family",
            "wall_clock_sec": reference_results[0]["wall_clock_sec"],
            "operations": reference_results[0]["operations"],
            "pair_trials": reference_results[0]["pair_trials"],
            "solves": f"{sum(item['ok'] for item in reference_results)}/8, as expected",
        },
    }

    scaled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    scaled_params["n"] *= 2
    scaled = make_instance(seed=31337, **scaled_params)
    scaled_ok, scaled_reason = verify(scaled, scaled["answer"])
    report["G7_scales"] = {
        "pass": scaled_ok and scaled["factor_count"] == 2 * shipping["factor_count"],
        "shipping_n": shipping["n"],
        "doubled_n": scaled["n"],
        "shipping_factors": shipping["factor_count"],
        "doubled_factors": scaled["factor_count"],
        "doubled_verify_reason": scaled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    invariant_ok = True
    carried_ok = True
    for seed in range(20):
        instance = make_instance(seed=20_000 + seed,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(instance)
        for transformed in _transformed_instances(instance, 30_000 + seed):
            invariant_ok &= canonical_key(transformed) == key
            invariance_checks += 1
            ok, _ = verify(transformed, transformed["answer"])
            carried_ok &= ok
            carried_checks += 1
    unrelated = [canonical_key(make_instance(
        seed=40_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )) for seed in range(20)]
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": bool(invariant_ok and carried_ok and distinct == 20),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "factor permutation", "term permutation", "variable permutation",
            "composition of all three",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 153
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    arms = copy.deepcopy(G9_EVIDENCE["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") for value in gates)
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    report["gvlib_sparse_poly_available"] = sparse_poly is not None
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
