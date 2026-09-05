"""Verified generator for transported Waring decompositions of cubic surfaces.

The native objects and transformation are from Section 2 of Anna Seigal,
"Ranks and Symmetric Ranks of Cubic Surfaces" (arXiv:1801.05377).  A
quaternary cubic is represented as a symmetric order-three tensor, and a
simultaneous GL(4) change of coordinates carries every linear form in a
Waring decomposition to a new linear form.

Generation is by certificate-preserving transformation.  We sample a
five-cube decomposition first, then transport it through a succinct chain of
unimodular coordinate changes.  The verifier independently expands the five
claimed cubes and compares all 20 integer coefficients; it never reads the
planted answer.
"""

from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import itertools
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
    from gvlib import exact_matrices, rationals, sparse_poly
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = sparse_poly = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "homogeneous quaternary cubic over Q",
        "five linear forms in a Waring decomposition",
        "succinct chain of GL(4,Z) coordinate changes",
    ],
    "verification_operations": [
        "exact integer matrix multiplication",
        "exact multinomial expansion of cubes of linear forms",
        "coefficient-by-coefficient polynomial identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The two displayed coordinate-change generators span a square-zero "
        "matrix algebra, so the long product depends only on two telescoping "
        "endpoint differences; without this invariant one transports through "
        "every change in the chain."
    ),
    "hardness_basis": (
        "Track B: Section 2's displayed GL(4) tensor action gives a sequential "
        "O(n) exact transport algorithm; at shipping n=8192 it performs "
        "1,597,580 counted arithmetic operations and measured 0.12--0.20 "
        "seconds per instance, while the square-zero endpoint route takes 237 "
        "exact operations after the invariant is recognized."
    ),
    "max_answer_tokens": 192,
}

NATIVE: dict = {
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

DIFFICULTY: dict = {
    "demo": {
        "n": 3, "modulus": 17, "base_bound": 2, "h_bound": 1,
    },
    "easy": {
        "n": 8192, "modulus": 2305843009213693951,
        "base_bound": 5, "h_bound": 7,
    },
    "medium": {
        "n": 16384, "modulus": 618970019642690137449562111,
        "base_bound": 6, "h_bound": 8,
    },
    "hard": {
        "n": 32768, "modulus": 162259276829213363391578010288127,
        "base_bound": 7, "h_bound": 9,
    },
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The two displayed generator matrices span a square-zero matrix algebra."
)
PLACEBO_HINT: str = (
    "The displayed matrices and coefficient conventions should be read carefully."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of five objects, sorted by the displayed distinct integer "
        "weights.  Each object is {\"weight\": w, \"form\": [1,a,b,c]}, "
        "representing w*(x0+a*x1+b*x2+c*x3)^3.  The three free integer "
        "coefficients lie in [-H,H], with H displayed in the instance, and "
        "the five forms are distinct."
    ),
    "bounds": {
        "terms": 5,
        "variables": 4,
        "leading_coefficient": 1,
        "free_coefficients_per_form": 3,
        "free_coefficient_interval": "[-H,H] from the instance",
        "weights": "the five fixed distinct weights displayed in the instance",
        "forms_distinct": True,
    },
}

# Filled from script-owned evidence after the three oracle arms are run.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 2, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = (
    "Section 1 fixes the exact Waring convention f=sum lambda_i*l_i^3 and "
    "identifies a quaternary cubic with a symmetric 4x4x4 tensor.  Section 2 "
    "(Cones over cubic curves) gives the coordinate formula "
    "T'_{ijk}=sum T_{abc}M_{ai}M_{bj}M_{ck} and explicitly carries rank "
    "decompositions through GL(4).  Sylvester's Pentahedral Theorem in Section "
    "2 says a generic cubic surface has a unique five-cube decomposition, but "
    "the coordinate formula itself gives a polynomial-time sequential method "
    "for the data exposed here, ruling out Track A.  The generator samples a "
    "five-term decomposition and transports it; it never decomposes the target. "
    "The two conjugated elementary generators N0,N1 satisfy Ni*Nj=0 for every "
    "i,j.  Hence product_k(I+d0(k)N0+d1(k)N1) is I+(sum d0)N0+(sum d1)N1. "
    "Each d_j(k)=h_j(s_{k+1})-h_j(s_k), so the sums are endpoint differences. "
    "The adversary panel checks the unchanged decomposition, a first-step "
    "greedy transport, a largest-generator outlier, an endpoint-only ansatz, "
    "a diagonal projection, and random restarts."
)


_EXPONENTS = tuple(
    (a, b, c, 3 - a - b - c)
    for a in range(3, -1, -1)
    for b in range(3 - a, -1, -1)
    for c in range(3 - a - b, -1, -1)
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _identity(size=4):
    return [[int(i == j) for j in range(size)] for i in range(size)]


def _mat_add_scaled(identity, generators, scalars):
    size = len(identity)
    return [
        [identity[i][j] + sum(c * g[i][j]
                              for c, g in zip(scalars, generators))
         for j in range(size)]
        for i in range(size)
    ]


def _mat_mul(left, right):
    rows, middle, cols = len(left), len(right), len(right[0])
    return [
        [sum(left[i][k] * right[k][j] for k in range(middle))
         for j in range(cols)]
        for i in range(rows)
    ]


def _row_mul(row, matrix):
    return [sum(row[k] * matrix[k][j] for k in range(len(row)))
            for j in range(len(matrix[0]))]


def _det3(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _inverse3_unimodular(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    det = _det3(matrix)
    if det not in (-1, 1):
        raise ValueError("matrix is not unimodular")
    adj = [
        [e * i - f * h, c * h - b * i, b * f - c * e],
        [f * g - d * i, a * i - c * g, c * d - a * f],
        [d * h - e * g, b * g - a * h, a * e - b * d],
    ]
    return [[entry // det for entry in row] for row in adj]


def _sample_unimodular3(rng):
    matrix = _identity(3)
    for _ in range(8):
        i, j = rng.sample(range(3), 2)
        multiple = rng.choice((-2, -1, 1, 2))
        matrix[i] = [x + multiple * y
                     for x, y in zip(matrix[i], matrix[j])]
    if rng.randrange(2):
        matrix[0], matrix[1] = matrix[1], matrix[0]
    return matrix


def _conjugated_generators(rng):
    change = _sample_unimodular3(rng)
    inverse = _inverse3_unimodular(change)
    elementary = []
    for source in (0, 1):
        item = [[0] * 3 for _ in range(3)]
        item[source][2] = 1
        elementary.append(item)
    generators = []
    for item in elementary:
        small = _mat_mul(_mat_mul(inverse, item), change)
        full = [[0] * 4 for _ in range(4)]
        for i in range(3):
            for j in range(3):
                full[i + 1][j + 1] = small[i][j]
        generators.append(full)
    zero = [[0] * 4 for _ in range(4)]
    if any(_mat_mul(a, b) != zero for a in generators for b in generators):
        raise AssertionError("generator construction lost square-zero property")
    return generators


def _eval_quadratic(coefficients, value):
    c0, c1, c2 = coefficients
    return (c2 * value + c1) * value + c0


def _pow_mod_counted(base, exponent, modulus):
    result = 1
    operations = 0
    while exponent:
        if exponent & 1:
            result = (result * base) % modulus
            operations += 1
        exponent >>= 1
        if exponent:
            base = (base * base) % modulus
            operations += 1
    return result, operations


def _endpoint_data(inst):
    power, power_operations = _pow_mod_counted(
        inst["multiplier"], inst["n"], inst["modulus"]
    )
    state_n = (power * inst["state0"]) % inst["modulus"]
    deltas = [
        _eval_quadratic(h, state_n) - _eval_quadratic(h, inst["state0"])
        for h in inst["h_polynomials"]
    ]
    # power operations, one state multiplication, 16 Horner arithmetic
    # operations for two quadratics at two points, and two subtractions.
    operations = power_operations + 1 + 16 + 2
    return state_n, deltas, operations


def _product_from_deltas(generators, deltas):
    return _mat_add_scaled(_identity(4), generators, deltas)


def _normalise_terms(base_terms, product):
    transformed = []
    for term in sorted(base_terms, key=lambda t: t["weight"]):
        form = _row_mul(term["form"], product)
        if form[0] != 1:
            raise AssertionError("the affine coordinate chart was not preserved")
        transformed.append({"weight": term["weight"], "form": form})
    return transformed


def _expand_terms(terms):
    coefficients = {exponent: 0 for exponent in _EXPONENTS}
    factorial3 = math.factorial(3)
    for term in terms:
        weight = term["weight"]
        form = term["form"]
        for exponent in _EXPONENTS:
            multinomial = factorial3
            value = weight
            for coordinate, degree in zip(form, exponent):
                multinomial //= math.factorial(degree)
                if degree:
                    value *= coordinate ** degree
            coefficients[exponent] += multinomial * value
    return coefficients


def _coefficients_json(coefficients):
    return [[list(exponent), coefficients[exponent]] for exponent in _EXPONENTS]


def _terms_match_target(terms, target):
    """Compare coefficients exactly, stopping at the first mismatch.

    This is algebraically the same expansion as ``_expand_terms``.  Early exit
    matters for G4: a random normalized candidate always matches the x0^3
    coefficient (the weights and leading coefficients are fixed), but almost
    always fails on the next mixed coefficient.
    """
    factorial3 = math.factorial(3)
    for exponent in _EXPONENTS:
        total = 0
        for term in terms:
            multinomial = factorial3
            value = term["weight"]
            for coordinate, degree in zip(term["form"], exponent):
                multinomial //= math.factorial(degree)
                if degree:
                    value *= coordinate ** degree
            total += multinomial * value
        if total != target[exponent]:
            return False
    return True


def _sample_base_terms(rng, bound):
    for _ in range(1000):
        weights = rng.sample(range(2, 48), 5)
        points = []
        while len(points) < 5:
            point = tuple(rng.randint(-bound, bound) for _ in range(3))
            if point not in points:
                points.append(point)
        terms = sorted(
            ({"weight": w, "form": [1, *point]}
             for w, point in zip(weights, points)),
            key=lambda term: term["weight"],
        )
        anchored = [term["form"][1:] for term in terms]
        basis = [[anchored[i][j] - anchored[0][j] for j in range(3)]
                 for i in range(1, 4)]
        if _det3(basis) != 0:
            return terms
    raise RuntimeError("could not sample an affine projective frame")


def _validate_params(n, modulus, base_bound, h_bound):
    for name, value in (("n", n), ("modulus", modulus),
                        ("base_bound", base_bound), ("h_bound", h_bound)):
        if not _is_int(value) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if modulus <= 5:
        raise ValueError("modulus must exceed five")


def make_instance(n, seed=0, modulus=65537, base_bound=5, h_bound=7,
                  **params) -> dict:
    """Build a transported five-cube decomposition without solving the target."""
    if params:
        unknown = ", ".join(sorted(params))
        raise ValueError(f"unknown make_instance parameters: {unknown}")
    _validate_params(n, modulus, base_bound, h_bound)
    rng = random.Random(seed)
    base_terms = _sample_base_terms(rng, base_bound)
    generators = _conjugated_generators(rng)

    # Reject only degenerate chain parameters, not hard decomposition cases.
    # This keeps every advertised coordinate chain nontrivial and every canned
    # attack meaningfully different from the planted transport.
    for _ in range(1000):
        multiplier = rng.randrange(2, modulus - 1)
        state0 = rng.randrange(1, modulus)
        h_polynomials = []
        for _j in range(2):
            h = [rng.randint(-h_bound, h_bound) for _d in range(3)]
            if h[1] == 0 and h[2] == 0:
                h[1] = rng.choice((-1, 1))
            h_polynomials.append(h)
        provisional = {
            "n": n,
            "modulus": modulus,
            "multiplier": multiplier,
            "state0": state0,
            "h_polynomials": h_polynomials,
        }
        state_n, deltas, _ = _endpoint_data(provisional)
        state1 = (multiplier * state0) % modulus
        first_deltas = [
            _eval_quadratic(h, state1) - _eval_quadratic(h, state0)
            for h in h_polynomials
        ]
        if (state_n not in (state0, state1)
                and any(deltas)
                and deltas != first_deltas
                and all(_eval_quadratic(h, state0) != 0
                        for h in h_polynomials)):
            break
    else:
        raise RuntimeError("could not sample a nondegenerate coordinate chain")

    product = _product_from_deltas(generators, deltas)
    answer = _normalise_terms(base_terms, product)
    coefficient_map = _expand_terms(answer)
    answer_bound = max(abs(value) for term in answer
                       for value in term["form"][1:]) + 2

    return {
        "family": "transported_waring_decomposition",
        "n": n,
        "modulus": modulus,
        "multiplier": multiplier,
        "state0": state0,
        "h_polynomials": h_polynomials,
        "generators": generators,
        "base_terms": base_terms,
        "target_coefficients": _coefficients_json(coefficient_map),
        "answer_bound": answer_bound,
        "answer": answer,
    }


def _format_form(form):
    pieces = []
    for coefficient, variable in zip(form, ("x0", "x1", "x2", "x3")):
        if coefficient == 0:
            continue
        magnitude = abs(coefficient)
        atom = variable if magnitude == 1 else f"{magnitude}*{variable}"
        if not pieces:
            pieces.append(atom if coefficient > 0 else "-" + atom)
        else:
            pieces.append((" + " if coefficient > 0 else " - ") + atom)
    return "".join(pieces) or "0"


def render(inst) -> str:
    """Render a complete, exact problem statement with a strict JSON contract."""
    base_lines = []
    for term in inst["base_terms"]:
        base_lines.append(
            f"  weight {term['weight']}: ({_format_form(term['form'])})^3"
        )
    coefficient_lines = [
        f"  {','.join(map(str, exponent))}: {coefficient}"
        for exponent, coefficient in inst["target_coefficients"]
    ]
    generator_lines = []
    for index, matrix in enumerate(inst["generators"]):
        generator_lines.append(f"N{index} =")
        generator_lines.extend("  " + json.dumps(row) for row in matrix)

    statement = f"""Transported Waring decomposition of a cubic surface

A linear form is a0*x0+a1*x1+a2*x2+a3*x3.  A five-term Waring
decomposition of a homogeneous cubic F is an identity

    F(x) = sum_(i=1)^5 w_i * L_i(x)^3.

All arithmetic in this problem is exact integer arithmetic.  Row vectors
represent linear forms.  Replacing x by a 4x4 matrix M times x sends the row
of L to row(L)*M, and it sends every cube in the displayed decomposition in
the same way.

The base cubic is already decomposed as follows (the five weights are
distinct):
{chr(10).join(base_lines)}

It undergoes n={inst['n']} successive coordinate changes M_0,...,M_(n-1).
Define states as the least nonnegative residues

    s_0 = {inst['state0']}
    s_(k+1) = {inst['multiplier']}*s_k mod {inst['modulus']},

for integer k with 0 <= k < n.  For h=[c0,c1,c2], h(s) means the ordinary
integer c0+c1*s+c2*s^2 after s has been replaced by its least nonnegative
residue.  Here

    h0 = {inst['h_polynomials'][0]}
    h1 = {inst['h_polynomials'][1]}.

The two generator matrices are

{chr(10).join(generator_lines)}

For 0 <= k < n, let

    d_j(k) = h_j(s_(k+1)) - h_j(s_k)       for j=0,1,
    M_k = I_4 + d_0(k)*N0 + d_1(k)*N1.

The changes act in increasing-k order, so a base row L becomes
L*M_0*M_1*...*M_(n-1).  The resulting target cubic has the following 20
coefficients.  A line e0,e1,e2,e3: c means coefficient c on
x0^e0*x1^e1*x2^e2*x3^e3.

{chr(10).join(coefficient_lines)}

Find five transformed linear forms whose weighted cubes equal that target.
Output one object for each of the five displayed weights, in strictly
increasing weight order.  Each form must be [1,a,b,c], all entries must be
integers, |a|,|b|,|c| <= H={inst['answer_bound']}, and the five forms must be
distinct.  Order within a form is x0,x1,x2,x3; indexing starts at zero and
there are no omitted coordinates.

Give your final answer inside <answer></answer> tags as a JSON list of objects
with exactly the keys \"weight\" and \"form\".
Example: <answer>[{{\"weight\":2,\"form\":[1,0,1,-1]}},{{\"weight\":3,\"form\":[1,1,0,0]}},{{\"weight\":5,\"form\":[1,-1,1,0]}},{{\"weight\":7,\"form\":[1,0,-1,1]}},{{\"weight\":11,\"form\":[1,1,1,1]}}]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Extract the tagged JSON answer, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    candidates = matches if matches else [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = re.sub(r"```(?:json)?", "", candidate,
                         flags=re.IGNORECASE).replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            pass
        for start, character in enumerate(cleaned):
            if character != "[":
                continue
            try:
                value, _end = decoder.raw_decode(cleaned[start:])
                return value
            except ValueError:
                continue
    return None


def _expected_weights(inst):
    return sorted(term["weight"] for term in inst["base_terms"])


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any bounded five-form identity by exact expansion."""
    if not isinstance(answer, list) or not answer:
        return False, "answer must be a nonempty JSON list"
    if len(answer) != 5:
        return False, "expected exactly five weighted linear forms"
    weights = []
    forms = []
    for index, term in enumerate(answer):
        if not isinstance(term, dict) or set(term) != {"weight", "form"}:
            return False, f"term {index} must have exactly weight and form keys"
        weight, form = term["weight"], term["form"]
        if not _is_int(weight):
            return False, f"term {index} weight must be an integer"
        if not isinstance(form, list) or len(form) != 4:
            return False, f"term {index} form must have exactly four entries"
        if any(not _is_int(value) for value in form):
            return False, f"term {index} form entries must all be integers"
        if form[0] != 1:
            return False, f"term {index} form must have leading coefficient 1"
        if any(abs(value) > inst["answer_bound"] for value in form[1:]):
            return False, f"term {index} coefficient exceeds the displayed bound H"
        weights.append(weight)
        forms.append(tuple(form))
    if weights != _expected_weights(inst):
        return False, "weights must be the displayed weights in increasing order"
    if len(set(forms)) != 5:
        return False, "the five linear forms must be distinct"
    target = {tuple(exponent): coefficient
              for exponent, coefficient in inst["target_coefficients"]}
    if not _terms_match_target(answer, target):
        return False, "weighted cube expansion does not equal the target cubic"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample ordered distinct normalized forms in the stated box."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    bound = inst["answer_bound"]
    forms = []
    seen = set()
    while len(forms) < 5:
        triple = tuple(rng.randint(-bound, bound) for _ in range(3))
        if triple in seen:
            continue
        seen.add(triple)
        forms.append([1, *triple])
    return [
        {"weight": weight, "form": form}
        for weight, form in zip(_expected_weights(inst), forms)
    ]


def search_space(inst) -> int | None:
    """Exact size of the structure-aware bounded certificate language."""
    form_count = (2 * inst["answer_bound"] + 1) ** 3
    result = 1
    for offset in range(5):
        result *= form_count - offset
    return result


def enumerate_all(inst) -> int | None:
    """Enumerate only genuinely tiny languages; otherwise return promptly."""
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    bound = inst["answer_bound"]
    forms = [[1, *triple] for triple in itertools.product(
        range(-bound, bound + 1), repeat=3
    )]
    count = 0
    for chosen in itertools.permutations(forms, 5):
        candidate = [
            {"weight": weight, "form": list(form)}
            for weight, form in zip(_expected_weights(inst), chosen)
        ]
        count += int(verify(inst, candidate)[0])
    return count


def _solve_fraction(matrix, rhs):
    work = [[Fraction(value) for value in row] + [Fraction(value)]
            for row, value in zip(matrix, rhs)]
    size = len(work)
    for col in range(size):
        pivot = next((row for row in range(col, size)
                      if work[row][col]), None)
        if pivot is None:
            raise ValueError("singular affine frame")
        work[col], work[pivot] = work[pivot], work[col]
        scale = work[col][col]
        work[col] = [value / scale for value in work[col]]
        for row in range(size):
            if row == col:
                continue
            factor = work[row][col]
            if factor:
                work[row] = [a - factor * b
                             for a, b in zip(work[row], work[col])]
    return [work[i][-1] for i in range(size)]


def canonical_key(inst) -> str:
    """Affine-coordinate invariant of the weighted base pentahedron."""
    terms = sorted(inst["base_terms"], key=lambda term: term["weight"])
    points = [term["form"][1:] for term in terms]
    basis_rows = [[points[i][j] - points[0][j] for j in range(3)]
                  for i in range(1, 4)]
    difference = [points[4][j] - points[0][j] for j in range(3)]
    # Solve transpose(basis_rows)*coordinates = difference.  These are the
    # barycentric coordinates of the fifth weighted point in the affine frame
    # fixed by the first four distinct weights, hence invariant under every
    # affine change of the three free coordinates.
    transpose = [[basis_rows[col][row] for col in range(3)]
                 for row in range(3)]
    coordinates = _solve_fraction(transpose, difference)
    payload = {
        "weights": [term["weight"] for term in terms],
        "fifth_point_affine_coordinates": [
            [value.numerator, value.denominator] for value in coordinates
        ],
    }
    normal = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normal.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow chain and modulus at fixed five-form witness length."""
    required = {"n", "modulus", "base_bound", "h_bound"}
    clean = {key: value for key, value in params.items() if key != "_preset"}
    if set(clean) != required:
        return None
    harder = dict(clean)
    harder["n"] = 2 * clean["n"]
    # The next known Mersenne-prime modulus adds entropy while the resulting
    # five forms still fit the published character/atom caps.  The following
    # jump to exponent 521 would push typical serialized answers beyond 2,000
    # characters, so that is honestly cap-bound.
    p107 = 162259276829213363391578010288127
    p127 = 170141183460469231731687303715884105727
    if clean["modulus"] <= p107:
        harder["modulus"] = p127
    elif clean["modulus"] == p127:
        return "cap_bound"
    else:
        return "cap_bound"
    return harder


def _compact_transport(inst):
    _state_n, deltas, operations = _endpoint_data(inst)
    product = _product_from_deltas(inst["generators"], deltas)
    # Constructing I+d0*N0+d1*N1: two multiplies and two additions in
    # each of 16 entries.  Five generic row-by-4x4 products cost
    # 5*(16 multiplications + 12 additions).
    operations += 64 + 140
    answer = _normalise_terms(inst["base_terms"], product)
    return {"answer": answer, "operations": operations}


def _reference_transport(inst):
    """Straight sequential application of all n displayed GL(4) changes."""
    start = time.perf_counter()
    product = _identity(4)
    state = inst["state0"]
    operations = 0
    for _ in range(inst["n"]):
        next_state = (inst["multiplier"] * state) % inst["modulus"]
        operations += 1
        deltas = []
        for h in inst["h_polynomials"]:
            before = _eval_quadratic(h, state)
            after = _eval_quadratic(h, next_state)
            operations += 8
            deltas.append(after - before)
            operations += 1
        change = _product_from_deltas(inst["generators"], deltas)
        operations += 64
        product = _mat_mul(product, change)
        operations += 112
        state = next_state
    answer = _normalise_terms(inst["base_terms"], product)
    operations += 140
    return {
        "answer": answer,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _candidate_from_product(inst, product):
    return _normalise_terms(inst["base_terms"], product)


def _attack_candidates(inst):
    identity = _identity(4)
    state1 = (inst["multiplier"] * inst["state0"]) % inst["modulus"]
    first_deltas = [
        _eval_quadratic(h, state1) - _eval_quadratic(h, inst["state0"])
        for h in inst["h_polynomials"]
    ]
    _state_n, true_deltas, _ = _endpoint_data(inst)
    endpoint_only = [
        _eval_quadratic(h, _state_n) for h in inst["h_polynomials"]
    ]
    norms = [sum(abs(value) for row in generator for value in row)
             for generator in inst["generators"]]
    outlier_index = max(range(2), key=lambda i: norms[i])
    outlier_deltas = [0, 0]
    outlier_deltas[outlier_index] = 1
    actual_product = _product_from_deltas(inst["generators"], true_deltas)
    diagonal_product = [[actual_product[i][j] if i == j else int(i == j)
                         for j in range(4)] for i in range(4)]
    return {
        "unchanged_base_forms": _candidate_from_product(inst, identity),
        "greedy_first_change_only": _candidate_from_product(
            inst, _product_from_deltas(inst["generators"], first_deltas)
        ),
        "largest_generator_outlier": _candidate_from_product(
            inst, _product_from_deltas(inst["generators"], outlier_deltas)
        ),
        "endpoint_without_initial_value": _candidate_from_product(
            inst, _product_from_deltas(inst["generators"], endpoint_only)
        ),
        "diagonal_projection_ansatz": _candidate_from_product(
            inst, diagonal_product
        ),
    }


def _affine_relabelling(seed):
    rng = random.Random(seed)
    permutation = list(range(3))
    rng.shuffle(permutation)
    signs = [rng.choice((-1, 1)) for _ in range(3)]
    q = [[0] * 3 for _ in range(3)]
    for i in range(3):
        q[i][permutation[i]] = signs[i]
    q_inverse = [[q[j][i] for j in range(3)] for i in range(3)]
    translation = [rng.randint(-2, 2) for _ in range(3)]
    inverse_translation = [
        -sum(translation[k] * q_inverse[k][j] for k in range(3))
        for j in range(3)
    ]
    matrix = [[1, *translation]] + [[0, *row] for row in q]
    inverse = [[1, *inverse_translation]] + [[0, *row]
                                              for row in q_inverse]
    if _mat_mul(matrix, inverse) != _identity(4):
        raise AssertionError("bad affine relabelling inverse")
    return matrix, inverse


def _relabel_instance(inst, matrix, inverse, reorder=False):
    transformed = copy.deepcopy(inst)
    transformed["base_terms"] = [
        {"weight": term["weight"], "form": _row_mul(term["form"], matrix)}
        for term in inst["base_terms"]
    ]
    if reorder:
        transformed["base_terms"].reverse()
    transformed["generators"] = [
        _mat_mul(_mat_mul(inverse, generator), matrix)
        for generator in inst["generators"]
    ]
    carried_answer = [
        {"weight": term["weight"], "form": _row_mul(term["form"], matrix)}
        for term in inst["answer"]
    ]
    carried_answer.sort(key=lambda term: term["weight"])
    transformed["target_coefficients"] = _coefficients_json(
        _expand_terms(carried_answer)
    )
    transformed["answer_bound"] = max(
        abs(value) for term in carried_answer for value in term["form"][1:]
    ) + 2
    transformed["answer"] = carried_answer
    return transformed


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest() -> dict:
    """Run gates G1--G9 and return their measured, JSON-native report."""
    report = {"paper": "1801.05377", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every named preset, several seeds, plus JSON-native answers.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            json_native = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            g1_checks += 1
            if not ok or not json_native:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": reason,
                                    "json_native": json_native})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)

    # G2: five common corruptions, deliberately reaching distinct checks.
    drop = copy.deepcopy(inst["answer"][:-1])
    swap = copy.deepcopy(inst["answer"])
    swap[0], swap[1] = swap[1], swap[0]
    duplicate = copy.deepcopy(inst["answer"])
    duplicate[1]["form"] = list(duplicate[0]["form"])
    empty = []
    out_of_range = copy.deepcopy(inst["answer"])
    out_of_range[0]["form"][1] = inst["answer_bound"] + 1
    mismatch = copy.deepcopy(inst["answer"])
    value = mismatch[0]["form"][1]
    mismatch[0]["form"][1] = value + 1 if value < inst["answer_bound"] else value - 1
    corruptions = {
        "drop_one": drop,
        "swap_two": swap,
        "duplicate_form": duplicate,
        "empty": empty,
        "out_of_range": out_of_range,
        "coefficient_change": mismatch,
    }
    rejection_reasons = {name: verify(inst, candidate)[1]
                         for name, candidate in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": (all(not verify(inst, candidate)[0]
                     for candidate in corruptions.values())
                 and len(set(rejection_reasons.values())) == len(corruptions)),
        "reasons": rejection_reasons,
    }

    # G3: model-style prose and fences round-trip the exact JSON-native answer.
    realistic = (
        "I used the coordinate action and checked the expansion.\n"
        "```json\n<answer>" + json.dumps(inst["answer"], separators=(",", ":"))
        + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    malformed = parse_answer("<answer>this is not JSON</answer>")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and malformed is None,
        "realistic_response_recovered": parsed == inst["answer"],
        "garbage_returns_none": malformed is None,
    }

    # G4: sample the actual bounded language after all stated structure.
    guess_rng = random.Random(0x180105377)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "candidate_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length(),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
        "sampling_prior": (
            "uniform ordered distinct normalized forms [1,a,b,c] in the "
            "displayed coefficient box, with the fixed weights already applied"
        ),
    }

    # G6 plus Track-B reference algorithm over eight shipping instances.
    attack_names = tuple(_attack_candidates(inst)) + ("random_restart_256",)
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = []
    compact_successes = 0
    compact_operations = []
    compact_seconds = 0.0
    for seed in range(80, 88):
        trial = make_instance(seed=seed, **shipping_params)
        for name, candidate in _attack_candidates(trial).items():
            start = time.perf_counter()
            solved = verify(trial, candidate)[0]
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(solved)
        restart_rng = random.Random(seed ^ 0xBAD5EED)
        start = time.perf_counter()
        restart_solved = False
        for _ in range(256):
            if verify(trial, random_candidate(trial, restart_rng))[0]:
                restart_solved = True
                break
        attack_seconds["random_restart_256"] += time.perf_counter() - start
        successes["random_restart_256"] += int(restart_solved)

        reference = _reference_transport(trial)
        reference_seconds += reference["wall_clock_sec"]
        reference_operations.append(reference["operations"])
        reference_successes += int(verify(trial, reference["answer"])[0])

        start = time.perf_counter()
        compact = _compact_transport(trial)
        compact_seconds += time.perf_counter() - start
        compact_operations.append(compact["operations"])
        compact_successes += int(verify(trial, compact["answer"])[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference_algorithm = {
        "name": "sequential GL(4) transport through all M_k",
        "complexity": "O(n) exact integer arithmetic for fixed 4x4 format",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": max(reference_operations),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
        "intended_compact_route": {
            "name": "square-zero product and endpoint differences",
            "complexity": "O(log n) modular multiplications plus fixed 4x4 work",
            "wall_clock_sec": round(compact_seconds / 8, 6),
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/8",
        },
    }

    # G5: shipping density and actual strongest/reference costs.
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_fraction < 1e-6 and all_failed
                 and reference_successes == 8 and compact_successes == 8),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_estimate": guess_fraction,
        "shipping_candidate_space": search_space(inst),
        "exact_solution_count": "not enumerated; shipping density is sampled",
        "strongest_failing_attack": "random_restart_256",
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference_algorithm["wall_clock_sec"],
        "reference_operation_count": reference_algorithm["operations"],
        "compact_operation_count": max(compact_operations),
    }

    # G7: double the chain length without changing the five-term answer shape.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_n = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and doubled["n"] == 2 * inst["n"]
                 and ladder_n == sorted(ladder_n)
                 and len(set(ladder_n)) == len(ladder_n)
                 and _atomic_elements(doubled["answer"])
                     == _atomic_elements(inst["answer"])),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "reference_operations_shipping": 195 * inst["n"] + 140,
        "reference_operations_doubled": 195 * doubled["n"] + 140,
        "answer_elements_shipping": _atomic_elements(inst["answer"]),
        "answer_elements_doubled": _atomic_elements(doubled["answer"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: input reordering, affine relabelling, and their composition.
    invariant_checks = 0
    carried_verification_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        small_params = dict(DIFFICULTY["demo"])
        original = make_instance(seed=1000 + seed, **small_params)
        key = canonical_key(original)
        reordered = copy.deepcopy(original)
        reordered["base_terms"].reverse()
        invariant_checks += 1
        if canonical_key(reordered) != key:
            g8_failures.append({"seed": seed, "map": "input_reordering"})
        ok, _reason = verify(reordered, original["answer"])
        carried_verification_checks += 1
        if not ok:
            g8_failures.append({"seed": seed, "map": "reordering_is_not_real"})

        matrix, inverse = _affine_relabelling(7000 + seed)
        relabelled = _relabel_instance(original, matrix, inverse, reorder=False)
        composed = _relabel_instance(original, matrix, inverse, reorder=True)
        for name, changed in (("affine", relabelled),
                              ("affine_plus_reordering", composed)):
            invariant_checks += 1
            if canonical_key(changed) != key:
                g8_failures.append({"seed": seed, "map": name})
            ok, _reason = verify(changed, changed["answer"])
            carried_verification_checks += 1
            if not ok:
                g8_failures.append({"seed": seed,
                                    "map": name + "_carried_answer"})
        unrelated_keys.append(key)
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_answer_verification_checks": carried_verification_checks,
        "unrelated_instances": 20,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "failures": g8_failures,
        "transformations": [
            "reorder the five displayed base terms",
            "signed-permutation-plus-translation affine coordinate relabelling",
            "composition of the two",
        ],
    }

    # G9(a,b) are recorded diagnostics; only the size/operation caps gate.
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _atomic_elements(inst["answer"])
    intended_operations = max(compact_operations)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
