"""Verified valued-Gröbner problem generator for arXiv:1303.0729.

The paper's Example 2.2 shows that naive valued reduction can run forever on
a cyclic list of linear forms.  Algorithm 2.1 repairs this with a strong
normal form.  This module inverse-generates longer, shuffled versions of that
cycle and asks for the rational constant multipliers in a zero-remainder
certificate.

The certificate is composed by telescoping before the rows are shuffled.  The
checker independently expands the two-term linear forms over Q and checks the
paper's exact p-adic leading-cost inequalities; it never reads the planted
answer.  Importing this module performs no I/O.
"""

from __future__ import annotations

import functools
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
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - every operation also has a stdlib path
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "rational",
    "native_objects": [
        "homogeneous linear polynomials over Q with the 2-adic valuation",
        "rational weight vector",
        "strong zero-remainder ideal-membership certificate",
    ],
    "verification_operations": [
        "exact rational linear combination",
        "exact 2-adic valuation of rational coefficients",
        "weighted leading-term comparison",
        "coefficient-by-coefficient polynomial identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "telescoping",
    "intuition_description": (
        "The valuation-leading variables orient the shuffled binomials into "
        "one multiplicative cycle, whose rationally scaled terms telescope; "
        "without seeing that cycle one solves the full exact linear system."
    ),
    "hardness_basis": (
        "Track B: Algorithm 2.1 supplies a terminating valued normal-form "
        "method and Algorithm 4.1 explicitly reduces homogeneous lifting to "
        "rational matrix inversion; dense exact Gaussian elimination is "
        "O(n^3).  At the shipping preset its measured cost is filled from "
        "selftest_report.json (eight solved references), while the cycle "
        "telescoping route uses at most 5n+5 exact operations."
    ),
    "max_answer_tokens": 128,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "An index-sorted JSON list with one entry [i,\"num/den\"] for every "
        "displayed generator i.  If q_i is the positive odd part common to "
        "that row's two coefficients, num/den must be one of "
        "-2^e/q_i for 0 <= e <= max_height, written in lowest terms with a "
        "positive denominator."
    ),
    "bounds": {
        "length": "number n of displayed generators",
        "indices": "exactly 0,...,n-1 in increasing order",
        "choices_per_coefficient": "max_height+1",
        "maximum_shipping_length": 73,
        "maximum_height": 8,
        "coefficient_denominator": "the row's odd scale q_i <= 127",
    },
}

DIFFICULTY = {
    "hard": {"n": 73, "max_height": 8, "scale_bound": 127},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The 2-adic leading variables orient the shuffled linear forms into one "
    "multiplicative cycle with a telescoping coefficient invariant."
)
PLACEBO_HINT = (
    "Keep the rational signs, row indices, and stated output ordering in view "
    "while checking the linear identity."
)

# These are replaced with script-owned measurements after the three oracle
# arms run.  Zero attempts is honest before those external calls exist.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper grounding.  Section 2 defines in_w(f), then Definition 2.1 orders
homogeneous polynomials by val(c_u)+w.u and a monomial tie-breaker.  Algorithm
2.1 returns f=sum h_i g_i+r with h_i g_i >= f, r >= f, and no remainder term
divisible by any leading monomial.  Lemma 2.4 proves termination for the
support ecart.  Example 2.2 is the decisive template: x-2y, y-2z, z-2x makes
naive division cycle x -> 2y -> 4z -> 8x forever.  Section 4, especially
Algorithm 4.1, also states the mechanical homogeneous route explicitly as
matrix formation and inversion over Q.  Thus an efficient certificate
algorithm exists and Track A would be false.

Construction.  Before emitting an instance, sample an odd-length walk of
exponents a_i in {-1,+1} whose prefix heights stay between zero and
max_height and whose sum is one.  Sample odd row scales q_i.  Around a random
cycle of the variables form q_i(x_i-2^a_i x_{i+1}).  Give x_0 weight zero and
recursively choose weights so the second term of every row has leading cost
exactly 1/n above the first.  Since product 2^a_i=2, multiplying row i by
-2^(prefix height)/q_i telescopes to x_0.  The path and all multipliers are
sampled before the shuffled polynomial list is assembled; no emitted system
is solved during generation.

Exact verification.  The checker expands sum h_i g_i and compares every
rational coefficient with the target.  It also computes exact 2-adic
valuations and checks val(h_i)+leadcost(g_i) >= leadcost(f), precisely the
strong-normal-form inequalities relevant here.  The relation matrix has
determinant (product q_i)(1-product 2^a_i), up to sign, hence is nonsingular;
the certificate is unique.  No float, planted-answer lookup, Gröbner oracle,
or root isolation appears in verify().

Easy boundary and attacks.  Dense exact Gaussian elimination, the degree-one
specialization of the paper's matrix route, solves every instance in cubic
time and is reported as the Track-B reference algorithm.  The compact route
instead reads the valuation orientation, follows one cycle, and accumulates
its powers of two.  Random variable names, row order, odd row scalings, and a
random bounded Dyck-like exponent walk remove positional, magnitude, fixed
alternation, and ordinary-term-order shortcuts.  The adversary panel tests
those routes plus random restarts; the disclosed reference solve is kept out
of attacks because Track B expects it to succeed.
""".strip()


_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.IGNORECASE | re.DOTALL)
_RATIONAL_RE = re.compile(r"^([+-]?\d+)\s*/\s*([+-]?\d+)$")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _rat_json(value: Fraction | int) -> list[int]:
    value = Fraction(value)
    return [value.numerator, value.denominator]


def _as_fraction(value: Any) -> Fraction:
    if (not isinstance(value, list) or len(value) != 2
            or not all(_is_int(x) for x in value)):
        raise ValueError("a rational must be a [numerator,denominator] pair")
    numerator, denominator = value
    if denominator <= 0:
        raise ValueError("rational denominators must be positive")
    if math.gcd(abs(numerator), denominator) != 1:
        raise ValueError("rationals must be in lowest terms")
    return Fraction(numerator, denominator)


def _format_fraction(value: Fraction | list[int]) -> str:
    q = _as_fraction(value) if isinstance(value, list) else Fraction(value)
    return f"{q.numerator}/{q.denominator}"


def _v2_integer(value: int) -> int:
    value = abs(value)
    if value == 0:
        raise ValueError("the 2-adic valuation of zero is infinite")
    return (value & -value).bit_length() - 1


def _v2(value: Fraction) -> int:
    if value == 0:
        raise ValueError("the 2-adic valuation of zero is infinite")
    return _v2_integer(value.numerator) - _v2_integer(value.denominator)


def _odd_part_abs(value: Fraction) -> Fraction:
    value = abs(value)
    valuation = _v2(value)
    if valuation >= 0:
        return value / (1 << valuation)
    return value * (1 << (-valuation))


def _sample_height_walk(n: int, maximum: int, rng: random.Random) -> list[int]:
    """Sample +/-1 steps, staying in [0,maximum] and ending at height one."""

    @functools.lru_cache(maxsize=None)
    def completions(position: int, height: int) -> int:
        if position == n:
            return int(height == 1)
        total = 0
        for step in (-1, 1):
            new_height = height + step
            if 0 <= new_height <= maximum:
                total += completions(position + 1, new_height)
        return total

    if completions(0, 0) == 0:
        raise ValueError("no bounded height walk exists for these parameters")
    steps: list[int] = []
    height = 0
    for position in range(n):
        choices: list[tuple[int, int]] = []
        for step in (-1, 1):
            new_height = height + step
            if 0 <= new_height <= maximum:
                count = completions(position + 1, new_height)
                if count:
                    choices.append((step, count))
        draw = rng.randrange(sum(count for _, count in choices))
        for step, count in choices:
            if draw < count:
                steps.append(step)
                height += step
                break
            draw -= count
    assert height == 1 and sum(steps) == 1
    return steps


def _validate_parameters(n: int, max_height: int, scale_bound: int) -> None:
    if not _is_int(n) or not 5 <= n <= 255 or n % 2 == 0:
        raise ValueError("n must be an odd integer in [5,255]")
    if not _is_int(max_height) or not 2 <= max_height <= 12:
        raise ValueError("max_height must be an integer in [2,12]")
    if (not _is_int(scale_bound) or not 3 <= scale_bound <= 1_000_001
            or scale_bound % 2 == 0):
        raise ValueError("scale_bound must be an odd integer in [3,1000001]")


def make_instance(n: int, seed: int = 0, max_height: int = 3,
                  scale_bound: int = 31, **params: Any) -> dict:
    """Compose and shuffle a valued cyclic ideal-membership certificate."""
    del params
    _validate_parameters(n, max_height, scale_bound)
    rng = random.Random(seed)

    steps = _sample_height_walk(n, max_height, rng)
    variables = list(range(n))
    rng.shuffle(variables)
    target_variable = variables[0]
    scales = [rng.randrange(1, scale_bound + 1, 2) for _ in range(n)]

    weights: list[Fraction | None] = [None] * n
    weights[target_variable] = Fraction(0)
    for position in range(n - 1):
        source = variables[position]
        destination = variables[position + 1]
        assert weights[source] is not None
        weights[destination] = (
            weights[source] - steps[position] + Fraction(1, n)
        )
    closing = weights[variables[-1]] - steps[-1] + Fraction(1, n)
    assert closing == weights[target_variable]

    rows_with_coefficients: list[tuple[dict, Fraction]] = []
    prefix_height = 0
    for position, step in enumerate(steps):
        source = variables[position]
        destination = variables[(position + 1) % n]
        scale = scales[position]
        second = (Fraction(-2 * scale) if step == 1
                  else Fraction(-scale, 2))
        terms = [
            [_rat_json(Fraction(scale)), source],
            [_rat_json(second), destination],
        ]
        terms.sort(key=lambda term: term[1])
        row = {"terms": terms, "q": scale}
        multiplier = Fraction(-(1 << prefix_height), scale)
        rows_with_coefficients.append((row, multiplier))
        prefix_height += step
    assert prefix_height == 1

    rng.shuffle(rows_with_coefficients)
    generators = [row for row, _ in rows_with_coefficients]
    answer = [
        [index, _rat_json(coefficient)]
        for index, (_, coefficient) in enumerate(rows_with_coefficients)
    ]

    return {
        "arxiv_id": "1303.0729",
        "field": "Q with the 2-adic valuation",
        "p": 2,
        "degree": 1,
        "term_order": "lex with x0 > x1 > ... > x(n-1)",
        "n": n,
        "max_height": max_height,
        "scale_bound": scale_bound,
        "weights": [_rat_json(weight) for weight in weights],
        "generators": generators,
        "target": {"terms": [[_rat_json(Fraction(1)), target_variable]]},
        "answer": answer,
    }


def _linear_form_string(poly: dict) -> str:
    pieces: list[str] = []
    for raw_coefficient, variable in poly["terms"]:
        coefficient = _as_fraction(raw_coefficient)
        magnitude = abs(coefficient)
        monomial = f"x{variable}"
        body = monomial if magnitude == 1 else f"{_format_fraction(magnitude)}*{monomial}"
        if not pieces:
            pieces.append(("-" if coefficient < 0 else "") + body)
        else:
            pieces.append((" - " if coefficient < 0 else " + ") + body)
    return "".join(pieces) if pieces else "0"


def _row_scale(poly: dict) -> int:
    cached = poly.get("q")
    if _is_int(cached) and cached > 0 and cached % 2 == 1:
        return cached
    units = {
        _odd_part_abs(_as_fraction(raw_coefficient))
        for raw_coefficient, _ in poly["terms"]
    }
    if len(units) != 1:
        raise ValueError("row coefficients do not have a common odd part")
    unit = next(iter(units))
    if unit.denominator != 1 or unit.numerator <= 0:
        raise ValueError("row odd part is not a positive integer")
    return unit.numerator


def render(inst: dict) -> str:
    n = inst["n"]
    target_variable = inst["target"]["terms"][0][1]
    lines = [
        "Find a strong zero-remainder certificate over a valued field.",
        "",
        "Work in Q[x0,...,x%d].  For a nonzero rational c, v2(c) is the " % (n - 1),
        "exponent of 2 in its numerator minus the exponent of 2 in its denominator.",
        "The weight of xj is wj.  The leading cost of a nonzero linear form",
        "sum c_j*xj is min_j(v2(c_j)+w_j); a term attaining that minimum is",
        "a leading term (lexicographic order x0>x1>... breaks a tie).",
        "For a nonzero constant h, the leading cost of h*g is v2(h) plus",
        "the leading cost of g.",
        "",
        "The exact rational weights, in variable order x0,x1,..., are:",
        "  " + ", ".join(_format_fraction(weight) for weight in inst["weights"]),
        "",
        "The target is f = x%d.  The following n=%d homogeneous generators are" % (
            target_variable, n),
        "indexed from 0.  Beside each row, q_i is the positive odd part common",
        "to its two rational coefficients after powers of 2 are removed.",
    ]
    for index, generator in enumerate(inst["generators"]):
        lines.append(
            f"  {index}: g_{index} = {_linear_form_string(generator)}    "
            f"(q_{index}={_row_scale(generator)})"
        )
    lines.extend([
        "",
        "Return rational constants h_0,...,h_%d satisfying both conditions:" % (n - 1),
        "  (1) f = sum_i h_i*g_i as an exact polynomial identity over Q;",
        "  (2) every h_i*g_i has leading cost at least the leading cost of f.",
        "The zero coefficient is not allowed.  For row i, h_i must be one of",
        "  -1/q_i, -2/q_i, ..., -2^%d/q_i," % inst["max_height"],
        "reduced to lowest terms.  There is exactly one valid vector in this",
        "bounded language.",
        "",
        "Give your final answer inside <answer></answer> tags as JSON with exactly",
        "%d entries [i,\"num/den\"], one for every i=0,...,%d in increasing order." % (
            n, n - 1),
        "Rational strings use a positive denominator, including /1 for integers.",
        "Example shape: <answer>[[0,\"-1/3\"],[1,\"-2/5\"],...,[%d,\"-1/7\"]]</answer>" % (
            n - 1),
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def _answer_text(answer: list) -> str:
    external = []
    for index, rational in answer:
        external.append([index, _format_fraction(rational)])
    return json.dumps(external, separators=(",", ":"))


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = _TAG_RE.search(text)
    if match is None:
        return None
    payload = match.group(1).strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        raw = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(raw, list):
        return None
    result = []
    try:
        for entry in raw:
            if not isinstance(entry, list) or len(entry) != 2 or not _is_int(entry[0]):
                return None
            value = entry[1]
            if isinstance(value, str):
                rational_match = _RATIONAL_RE.fullmatch(value.strip())
                if rational_match is None:
                    return None
                numerator = int(rational_match.group(1))
                denominator = int(rational_match.group(2))
                if denominator == 0:
                    return None
                fraction = Fraction(numerator, denominator)
                result.append([entry[0], _rat_json(fraction)])
            elif isinstance(value, list):
                fraction = _as_fraction(value)
                result.append([entry[0], _rat_json(fraction)])
            else:
                return None
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return result


def _leading_cost(poly: dict, weights: list[Fraction]) -> Fraction:
    costs = []
    for raw_coefficient, variable in poly["terms"]:
        coefficient = _as_fraction(raw_coefficient)
        if coefficient:
            costs.append(Fraction(_v2(coefficient)) + weights[variable])
    if not costs:
        raise ValueError("zero polynomial has no leading cost")
    return min(costs)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any bounded rational strong-normal-form witness exactly."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"answer must contain exactly {n} indexed coefficients"

    parsed: list[tuple[int, Fraction]] = []
    seen: set[int] = set()
    previous = -1
    for position, entry in enumerate(answer):
        if not isinstance(entry, list) or len(entry) != 2 or not _is_int(entry[0]):
            return False, f"entry {position} must be [integer_index,[num,den]]"
        index = entry[0]
        if not 0 <= index < n:
            return False, "generator index out of range"
        if index in seen:
            return False, "generator indices must be unique"
        if index <= previous:
            return False, "entries must be sorted by generator index"
        seen.add(index)
        previous = index
        try:
            coefficient = _as_fraction(entry[1])
        except ValueError as exc:
            return False, str(exc)
        row_scale = _row_scale(inst["generators"][index])
        allowed = {
            Fraction(-(1 << exponent), row_scale)
            for exponent in range(inst["max_height"] + 1)
        }
        if coefficient not in allowed:
            return False, f"coefficient for generator {index} is outside its bounded language"
        parsed.append((index, coefficient))

    target_variable = inst["target"]["terms"][0][1]
    # An exact two-incidence equation rejects almost every random language
    # candidate before the remaining coefficient equations are expanded.  This
    # is a checker optimization, not a search or a planted-answer comparison.
    target_total = Fraction(0)
    for index, multiplier in parsed:
        for raw_coefficient, variable in inst["generators"][index]["terms"]:
            if variable == target_variable:
                target_total += multiplier * _as_fraction(raw_coefficient)
    if target_total != 1:
        return False, "the rational polynomial identity does not equal the target"

    weights = [_as_fraction(weight) for weight in inst["weights"]]
    target_cost = weights[target_variable]
    totals = [Fraction(0) for _ in range(n)]
    for index, multiplier in parsed:
        generator = inst["generators"][index]
        product_cost = Fraction(_v2(multiplier)) + _leading_cost(generator, weights)
        if product_cost < target_cost:
            return False, f"row {index} violates the leading-cost inequality"
        for raw_coefficient, variable in generator["terms"]:
            totals[variable] += multiplier * _as_fraction(raw_coefficient)
    expected = [Fraction(0) for _ in range(n)]
    expected[target_variable] = Fraction(1)
    if totals != expected:
        return False, "the rational polynomial identity does not equal the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    answer = []
    for index, generator in enumerate(inst["generators"]):
        row_scale = _row_scale(generator)
        exponent = rng.randrange(inst["max_height"] + 1)
        answer.append([index, _rat_json(Fraction(-(1 << exponent), row_scale))])
    return answer


def search_space(inst: dict) -> int | None:
    return (inst["max_height"] + 1) ** inst["n"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 20_000:
        return None
    count = 0
    for exponents in itertools.product(
            range(inst["max_height"] + 1), repeat=inst["n"]):
        candidate = []
        for index, exponent in enumerate(exponents):
            scale = _row_scale(inst["generators"][index])
            candidate.append([
                index, _rat_json(Fraction(-(1 << exponent), scale))
            ])
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _oriented_row(inst: dict, generator: dict) -> tuple[int, int, int, int]:
    weights = [_as_fraction(weight) for weight in inst["weights"]]
    decorated = []
    for raw_coefficient, variable in generator["terms"]:
        coefficient = _as_fraction(raw_coefficient)
        decorated.append((Fraction(_v2(coefficient)) + weights[variable],
                          variable, coefficient))
    decorated.sort(key=lambda item: (item[0], item[1]))
    if decorated[0][0] == decorated[1][0]:
        raise ValueError("canonical orientation requires a unique leading cost")
    _, source, source_coefficient = decorated[0]
    _, destination, destination_coefficient = decorated[1]
    ratio = -destination_coefficient / source_coefficient
    if ratio <= 0 or _odd_part_abs(ratio) != 1:
        raise ValueError("row ratio is not a signed power of two")
    step = _v2(ratio)
    scale = _odd_part_abs(source_coefficient)
    if scale.denominator != 1:
        raise ValueError("row scale is not integral")
    return source, destination, step, scale.numerator


def canonical_key(inst: dict) -> str:
    """Canonicalize generator order and variable names via the oriented cycle."""
    outgoing = {}
    for generator in inst["generators"]:
        source, destination, step, scale = _oriented_row(inst, generator)
        if source in outgoing:
            raise ValueError("oriented rows do not define one outgoing edge per variable")
        outgoing[source] = (destination, step, scale)
    current = inst["target"]["terms"][0][1]
    signature = []
    seen = set()
    for _ in range(inst["n"]):
        if current in seen or current not in outgoing:
            raise ValueError("oriented rows do not form one target-anchored cycle")
        seen.add(current)
        destination, step, scale = outgoing[current]
        signature.append([step, scale])
        current = destination
    if current != inst["target"]["terms"][0][1] or len(seen) != inst["n"]:
        raise ValueError("oriented rows do not close after every variable")
    payload = {
        "p": inst["p"],
        "n": inst["n"],
        "max_height": inst["max_height"],
        "cycle": signature,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params: dict) -> dict | str | None:
    clean = {key: value for key, value in params.items() if not key.startswith("_")}
    n = int(clean.get("n", 5))
    maximum = int(clean.get("max_height", 2))
    bound = int(clean.get("scale_bound", 9))
    if maximum < 8:
        clean["max_height"] = maximum + 1
        return clean
    if n < 73:
        clean["n"] = n + 2
        return clean
    return "cap_bound"


def _candidate_from_heights(inst: dict, heights: list[int]) -> list:
    result = []
    for index, exponent in enumerate(heights):
        scale = _row_scale(inst["generators"][index])
        exponent = max(0, min(inst["max_height"], int(exponent)))
        result.append([index, _rat_json(Fraction(-(1 << exponent), scale))])
    return result


def _attack_all_minimum(inst: dict) -> list:
    return _candidate_from_heights(inst, [0] * inst["n"])


def _attack_scale_outlier(inst: dict) -> list:
    scales = [_row_scale(row) for row in inst["generators"]]
    median = sorted(scales)[len(scales) // 2]
    return _candidate_from_heights(
        inst, [int(scale > median) for scale in scales]
    )


def _attack_position_alternation(inst: dict) -> list:
    return _candidate_from_heights(
        inst, [index % (inst["max_height"] + 1) for index in range(inst["n"])]
    )


def _attack_ordinary_lex(inst: dict) -> list:
    """A plausible by-hand route that ignores the valuation orientation."""
    outgoing: dict[int, tuple[int, int]] = {}
    for index, generator in enumerate(inst["generators"]):
        terms = sorted(generator["terms"], key=lambda term: term[1])
        source = terms[0][1]  # ordinary lex picks the smaller variable index
        destination = terms[1][1]
        outgoing.setdefault(source, (destination, index))
    heights = [0] * inst["n"]
    current = inst["target"]["terms"][0][1]
    height = 0
    visited = set()
    while current in outgoing and current not in visited:
        visited.add(current)
        destination, row_index = outgoing[current]
        heights[row_index] = height
        coefficient_by_variable = {
            variable: _as_fraction(raw) for raw, variable
            in inst["generators"][row_index]["terms"]
        }
        ratio = -coefficient_by_variable[destination] / coefficient_by_variable[current]
        height = max(0, min(inst["max_height"], height + _v2(ratio)))
        current = destination
    return _candidate_from_heights(inst, heights)


def _reference_gaussian(inst: dict) -> tuple[list, int, float]:
    """Dense exact solve of A^T h=f, intentionally making no cycle shortcut."""
    n = inst["n"]
    matrix = [[Fraction(0) for _ in range(n + 1)] for _ in range(n)]
    operations = n * n  # constructing/zeroing the dense coefficient array
    for column, generator in enumerate(inst["generators"]):
        for raw_coefficient, variable in generator["terms"]:
            matrix[variable][column] += _as_fraction(raw_coefficient)
            operations += 1
    target_variable = inst["target"]["terms"][0][1]
    matrix[target_variable][n] = Fraction(1)

    started = time.perf_counter()
    pivot_row = 0
    pivot_for_column: dict[int, int] = {}
    for column in range(n):
        pivot = None
        for row in range(pivot_row, n):
            operations += 1
            if matrix[row][column] != 0:
                pivot = row
                break
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        pivot_value = matrix[pivot_row][column]
        for cell in range(n + 1):
            matrix[pivot_row][cell] /= pivot_value
            operations += 1
        for row in range(n):
            if row == pivot_row:
                continue
            factor = matrix[row][column]
            operations += 1
            # This is the conventional dense loop: even a zero factor incurs
            # the exact multiply/subtract cells a dense implementation visits.
            for cell in range(n + 1):
                matrix[row][cell] -= factor * matrix[pivot_row][cell]
                operations += 2
        pivot_for_column[column] = pivot_row
        pivot_row += 1
    elapsed = time.perf_counter() - started
    if pivot_row != n:
        raise AssertionError("reference coefficient matrix was singular")
    solution = [Fraction(0) for _ in range(n)]
    for column, row in pivot_for_column.items():
        solution[column] = matrix[row][n]
    answer = [[index, _rat_json(value)] for index, value in enumerate(solution)]
    return answer, operations, elapsed


def _atom_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, list]:
    n = inst["n"]
    old_to_new = list(range(n))
    rng.shuffle(old_to_new)
    generator_order = list(range(n))
    rng.shuffle(generator_order)
    answer_map = {index: rational for index, rational in inst["answer"]}

    weights = [None] * n
    for old, new in enumerate(old_to_new):
        weights[new] = list(inst["weights"][old])
    generators = []
    carried = []
    for new_index, old_index in enumerate(generator_order):
        terms = [
            [list(raw), old_to_new[variable]]
            for raw, variable in inst["generators"][old_index]["terms"]
        ]
        rng.shuffle(terms)  # term-list order is also representational only
        generators.append({"terms": terms, "q": inst["generators"][old_index]["q"]})
        carried.append([new_index, list(answer_map[old_index])])
    target_old = inst["target"]["terms"][0][1]
    transformed = dict(inst)
    transformed["weights"] = weights
    transformed["generators"] = generators
    transformed["target"] = {
        "terms": [[_rat_json(Fraction(1)), old_to_new[target_old]]]
    }
    transformed["answer"] = carried
    return transformed, carried


def selftest() -> dict:
    report: dict[str, Any] = {"track": TRACK, "shipping": SHIPPING_DIFFICULTY}

    # G1: every preset and four unrelated seeds, including JSON-native answers.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    corruption_inst = make_instance(seed=314159, **shipping_params)
    planted = corruption_inst["answer"]
    corruptions = {}
    corruptions["drop_one"] = planted[:-1]
    swapped = [[index, list(rat)] for index, rat in planted]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap_entries"] = swapped
    duplicated = [[index, list(rat)] for index, rat in planted]
    duplicated[1][0] = duplicated[0][0]
    corruptions["duplicate_index"] = duplicated
    corruptions["empty"] = []
    out_of_range = [[index, list(rat)] for index, rat in planted]
    out_of_range[-1][0] = corruption_inst["n"]
    corruptions["out_of_range"] = out_of_range
    corruption_results = {
        name: {"accepted": verify(corruption_inst, value)[0],
               "reason": verify(corruption_inst, value)[1]}
        for name, value in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (not any(entry["accepted"] for entry in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    answer_payload = _answer_text(planted)
    model_style = (
        "I followed the valuation order and obtained the cycle multipliers.\n"
        "```json\n<answer>" + answer_payload + "</answer>\n```\n"
        "The displayed identity then telescopes."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(corruption_inst, parsed)[0],
        "parsed_matches": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_inst = make_instance(seed=271828, **shipping_params)
    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_started
    space = search_space(guess_inst)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "structure_aware_space": space,
        "proved_probability": 1 / space,
        "sampler": "one allowed row-specific rational per index, uniformly",
        "wall_clock_sec": guess_elapsed,
    }

    attack_names = (
        "all_minimum_height",
        "odd_scale_outlier",
        "generator_position_alternation",
        "ordinary_lex_cycle",
        "random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    attempts = {name: 0 for name in attack_names}
    reference_times = []
    reference_operations = []
    reference_successes = 0
    for seed in range(8):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        fixed_attacks = {
            "all_minimum_height": _attack_all_minimum(inst),
            "odd_scale_outlier": _attack_scale_outlier(inst),
            "generator_position_alternation": _attack_position_alternation(inst),
            "ordinary_lex_cycle": _attack_ordinary_lex(inst),
        }
        for name, candidate in fixed_attacks.items():
            attempts[name] += 1
            successes[name] += int(verify(inst, candidate)[0])
        restart_rng = random.Random(90_000 + seed)
        restart_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_solved = True
                break
        attempts["random_restart_256"] += 1
        successes["random_restart_256"] += int(restart_solved)

        reference_answer, operation_count, elapsed = _reference_gaussian(inst)
        reference_successes += int(verify(inst, reference_answer)[0])
        reference_operations.append(operation_count)
        reference_times.append(elapsed)

    attack_report = {
        name: {"successes": successes[name], "attempts": attempts[name]}
        for name in attack_names
    }
    all_failed = all(entry["successes"] == 0 for entry in attack_report.values())
    reference_report = {
        "name": "dense exact Gaussian elimination on the degree-one coefficient matrix",
        "complexity": "O(n^3) exact rational operations",
        "successes": reference_successes,
        "attempts": 8,
        "solves": f"{reference_successes}/8, as expected",
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_report,
        "reference_algorithm": reference_report,
    }

    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": (demo_count == 1 and guess_hits / guess_total < 1e-6
                 and reference_successes == 8),
        "shipping_density": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": guess_hits / guess_total,
            "proved_exact_valid_answers": 1,
            "candidate_space": space,
            "proved_fraction": 1 / space,
        },
        "demo_exact_enumeration": {
            "n": demo_inst["n"],
            "valid_answers": demo_count,
            "candidate_space": search_space(demo_inst),
        },
        "baseline_cost": reference_report,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"] + 1
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] > 2 * guess_inst["n"]
                 and search_space(doubled) > space),
        "base_n": guess_inst["n"],
        "doubled_n": doubled["n"],
        "base_space": space,
        "doubled_space": search_space(doubled),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_count = 0
    carried_count = 0
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=70_000 + seed, **shipping_params)
        key = canonical_key(inst)
        transformed, carried = _relabel_instance(inst, random.Random(80_000 + seed))
        invariant_count += int(canonical_key(transformed) == key)
        carried_count += int(verify(transformed, carried)[0])
        distinct_keys.append(key)
    report["G8_canonical_key"] = {
        "pass": (invariant_count == 20 and carried_count == 20
                 and len(set(distinct_keys)) == 20),
        "invariant_relabellings": invariant_count,
        "invariance_attempts": 20,
        "carried_witnesses_verified": carried_count,
        "carried_attempts": 20,
        "distinct_unrelated_keys": len(set(distinct_keys)),
        "distinctness_attempts": 20,
        "transformations": [
            "arbitrary variable permutation with weights carried",
            "arbitrary generator permutation with certificate indices carried",
            "independent term-list reordering",
        ],
    }

    sizes = []
    for seed in range(20):
        inst = make_instance(seed=90_000 + seed, **shipping_params)
        serialized = _answer_text(inst["answer"])
        sizes.append((len(serialized), (len(serialized) + 3) // 4,
                      _atom_count(inst["answer"])))
    answer_chars = max(item[0] for item in sizes)
    answer_tokens = max(item[1] for item in sizes)
    answer_elements = max(item[2] for item in sizes)
    # After recognizing the invariant: at most two valuation/arithmetic steps
    # to orient a row, one prefix update, and one rational normalization per
    # row, plus the final closure check.  Index lookups and comparisons are not
    # exact arithmetic operations.
    intended_operations = 4 * shipping_params["n"] + 1
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and intended_operations <= 300)
    arms = {
        name: dict(G9_MEASUREMENTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    hinted_rate = (arms["hinted"].get("solved", 0) / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"].get("solved", 0) / placebo_attempts
                    if placebo_attempts else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps_only_are_gated": True,
    }

    gate_values = [
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_pass"] = all(gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
