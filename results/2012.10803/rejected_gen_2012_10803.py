"""Verified bounded class-action exponent generator for arXiv:2012.10803.

Colo and Kohel represent the class group of the nonmaximal order
O_d = Z + 3^d Z[i] by Gaussian residue classes.  Section 6 then chooses a
bounded exponent vector for public class generators.  This module samples that
vector first and multiplies the corresponding classes, so generation never
solves the vectorization instance it emits.

All arithmetic is exact and uses only the Python standard library.  Importing
the module performs no I/O and prints nothing.
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
import time
from fractions import Fraction
from typing import Any


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Gaussian residue classes representing Cl(Z + 3^d Z[i])",
        "bounded products of invertible ideal classes",
        "private class-action exponent vector",
    ],
    "verification_operations": [
        "exact Gaussian-integer multiplication modulo 3^d",
        "exact modular inversion",
        "exact quotient-class equivalence modulo Gaussian units and real units",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize the paper's Gaussian residue quotient as a cyclic smooth-order "
        "class group and turn vectorization into a bounded modular subset-sum; "
        "without that recognition one searches the full class-action box."
    ),
    "hardness_basis": (
        "Track A uses Theorem 7's faithful class-group action in the Section 6 "
        "effectively-injective bounded-exponent regime: at the shipping preset "
        "40 independent classes have exponents in [-5,5], a 138.4-bit box in a "
        "145-bit-order group; smooth-order Pohlig-Hellman preprocessing is "
        "explicitly acknowledged, while the remaining bounded modular subset-sum "
        "defeated exact LLL embedding and capped meet-in-the-middle attacks on all "
        "eight audit seeds (measured costs are in selftest_report.json)."
    ),
    "max_answer_tokens": 31,
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
    "demo": {"n": 3, "exponent_bound": 1, "slack_trits": 4},
    "easy": {"n": 40, "exponent_bound": 5, "slack_trits": 4},
    "medium": {"n": 40, "exponent_bound": 6, "slack_trits": 4},
    "hard": {"n": 40, "exponent_bound": 7, "slack_trits": 4},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The Gaussian quotient is cyclic of order 2*3^(d-1), and every displayed "
    "class is a power of one full-order class."
)
PLACEBO_HINT: str = (
    "The Gaussian quotient uses exact modular conventions, and every displayed "
    "pair should be read with the stated indexing rules."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly n ordinary integers, one for each displayed class "
        "in its displayed 0-based order, with every entry in the inclusive interval "
        "[-r,r].  The structure-aware candidate prior is uniform on this entire box."
    ),
    "bounds": {
        "length": "n",
        "entry_minimum": "-exponent_bound",
        "entry_maximum": "exponent_bound",
        "candidate_count": "(2*exponent_bound+1)**n",
    },
}

# Updated from script-owned oracle transcripts after STEP 4 and the two G9 runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES: str = r"""
Definition and native object.  Theorem 7 identifies primitive O-oriented curves
as a faithful transitive Cl(O)-torsor.  Section 5.1 displays

  Cl(O_d) = (Z[i]/3^d Z[i])^* / (Z[i]^* (Z/3^d Z)^*)

for O_d=Z+3^d Z[i], and explains the successive order-3 kernels.  Section 6,
"Private walk exponents", fixes the actual witness: an exponent vector in a
box [-r,r]^t whose product of chosen ideal classes acts on the public oriented
curve.  It also requires the box-to-class-group map to be effectively
injective.  This module stays in those quotient-class objects; it does not
replace curves by an unrelated graph or finite-field analogue.

Step-0 certificate algorithm.  Generation samples the exponent vector first,
samples independent full-order class generators, and multiplies them.  That is
inverse generation.  Checking a candidate repeats the exact class product and
tests quotient equivalence.  The successful preprocessing algorithm is also
made explicit: because |Cl(O_d)|=2*3^(d-1), Pohlig-Hellman recovers one discrete
logarithm digit at a time in polynomial time.  It does not by itself recover
the bounded vector; what remains is a random modular bounded subset-sum at
density just below one.  Thus the family is not falsely claiming that the
smooth class-group discrete logarithm is hard.

Hard and easy regimes.  Section 5.1 makes the full-chain case easy by lifting
through the cyclic order-3 kernels.  Section 6 warns that too small a private
degree is distinguished and that cycles in the exponent box must not be easy
to find.  The presets keep the class group about 3^4 larger than the entire
box, so a target normally has one bounded preimage, while n and r grow.  The
demo is enumerable.  At shipping size the exact LLL embedding, greedy modular
residual descent, one-sparse outlier test, random restart, and capped
meet-in-the-middle attacks are all measured rather than inferred from the
138-bit cardinality.

Plants and decoys.  Every public discrete-log weight is independently uniform
among units modulo the class-group order, conditioned only on avoiding a
duplicate up to sign.  Every secret coordinate is uniform on exactly the box
sampled by random_candidate.  Representatives are independently multiplied by
random Gaussian units and real residue units, and the input order is shuffled,
so the stored witness has no coordinate, magnitude, or representative-format
signature.

Canonicalization quotients the genuine symmetries: input permutation,
independent generator inversion (the exponent box is symmetric), replacement
of a residue by an equivalent axis multiple, and every automorphism of the
cyclic class group.  It uses discrete logs only to compute this invariant; it
never hashes the seed or rendered statement.

Final audit disposition.  The initially reported 242-operation figure was the
cost of checking an exponent vector that had already been supplied.  It was
not the intended route for finding that vector.  Recognizing the cyclic
quotient still leaves Pohlig--Hellman preprocessing (at least 459,092 measured
exact group operations at the shipping preset) followed by an unsolved
bounded modular subset-sum.  There is no sub-300-operation compact route, so
this retained module is evidence for the rejection documented in REJECTED.md,
not a shippable generator.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000
_VERIFY_TABLE_CACHE: dict[tuple, list[list[tuple[int, int]]]] = {}


def _validate_params(n: int, exponent_bound: int, slack_trits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if (
        isinstance(exponent_bound, bool)
        or not isinstance(exponent_bound, int)
        or exponent_bound < 1
    ):
        raise ValueError("exponent_bound must be a positive integer")
    if (
        isinstance(slack_trits, bool)
        or not isinstance(slack_trits, int)
        or not 2 <= slack_trits <= 12
    ):
        raise ValueError("slack_trits must be an integer from 2 through 12")


def _parameters(n: int, exponent_bound: int, slack_trits: int) -> tuple[int, int, int]:
    """Return (depth, modulus, class_order), using integer comparisons only."""
    box = pow(2 * exponent_bound + 1, n)
    required = box * pow(3, slack_trits)
    depth = 1
    order = 2
    while order <= required:
        depth += 1
        order *= 3
    modulus = pow(3, depth)
    return depth, modulus, order


def _gmul(x: tuple[int, int], y: tuple[int, int], modulus: int) -> tuple[int, int]:
    return (
        (x[0] * y[0] - x[1] * y[1]) % modulus,
        (x[0] * y[1] + x[1] * y[0]) % modulus,
    )


def _ginv(x: tuple[int, int], modulus: int) -> tuple[int, int]:
    norm = (x[0] * x[0] + x[1] * x[1]) % modulus
    if math.gcd(norm, modulus) != 1:
        raise ValueError("Gaussian residue is not a unit")
    inverse_norm = pow(norm, -1, modulus)
    return (x[0] * inverse_norm % modulus, -x[1] * inverse_norm % modulus)


def _gpow(
    base: tuple[int, int], exponent: int, modulus: int
) -> tuple[int, int]:
    if exponent < 0:
        base = _ginv(base, modulus)
        exponent = -exponent
    result = (1, 0)
    while exponent:
        if exponent & 1:
            result = _gmul(result, base, modulus)
        exponent >>= 1
        if exponent:
            base = _gmul(base, base, modulus)
    return result


def _gpow_counted(
    base: tuple[int, int], exponent: int, modulus: int
) -> tuple[tuple[int, int], int]:
    operations = 0
    if exponent < 0:
        base = _ginv(base, modulus)
        exponent = -exponent
        operations += 1
    result = (1, 0)
    while exponent:
        if exponent & 1:
            result = _gmul(result, base, modulus)
            operations += 1
        exponent >>= 1
        if exponent:
            base = _gmul(base, base, modulus)
            operations += 1
    return result, operations


def _class_equal(
    x: tuple[int, int], y: tuple[int, int], modulus: int
) -> bool:
    """Equality modulo Gaussian units and invertible real scalars."""
    ratio = _gmul(x, _ginv(y, modulus), modulus)
    return ratio[0] == 0 or ratio[1] == 0


def _axis_multiple(
    z: tuple[int, int], scalar: int, unit: int, modulus: int
) -> tuple[int, int]:
    scalar %= modulus
    if unit == 0:
        axis = (scalar, 0)
    elif unit == 1:
        axis = (0, scalar)
    elif unit == 2:
        axis = (-scalar % modulus, 0)
    else:
        axis = (0, -scalar % modulus)
    return _gmul(axis, z, modulus)


def _random_representative(
    z: tuple[int, int], rng: random.Random, modulus: int
) -> tuple[int, int]:
    while True:
        scalar = rng.randrange(1, modulus)
        if scalar % 3:
            return _axis_multiple(z, scalar, rng.randrange(4), modulus)


def make_instance(
    n: int,
    seed: int = 0,
    **params: Any,
) -> dict:
    """Inverse-generate a bounded class-action vectorization instance."""
    exponent_bound = params.pop("exponent_bound", 5)
    slack_trits = params.pop("slack_trits", 4)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n, exponent_bound, slack_trits)
    depth, modulus, class_order = _parameters(n, exponent_bound, slack_trits)
    rng = random.Random(seed)

    # The class of (-2+4i) has exact order 2*3^(d-1) in this quotient.
    full_generator = (-2 % modulus, 4 % modulus)
    if not _class_equal(_gpow(full_generator, class_order, modulus), (1, 0), modulus):
        raise AssertionError("internal full-order identity failed")
    if _class_equal(_gpow(full_generator, class_order // 2, modulus), (1, 0), modulus):
        raise AssertionError("internal order unexpectedly lost its 2-part")
    if _class_equal(_gpow(full_generator, class_order // 3, modulus), (1, 0), modulus):
        raise AssertionError("internal order unexpectedly lost its 3-part")

    weights: list[int] = []
    signed_seen: set[int] = set()
    while len(weights) < n:
        weight = rng.randrange(1, class_order)
        if math.gcd(weight, class_order) != 1:
            continue
        normalized = min(weight, class_order - weight)
        if normalized in signed_seen:
            continue
        signed_seen.add(normalized)
        weights.append(weight)

    secret = [rng.randint(-exponent_bound, exponent_bound) for _ in range(n)]
    classes = [_gpow(full_generator, weight, modulus) for weight in weights]
    target = (1, 0)
    for ideal_class, exponent in zip(classes, secret):
        target = _gmul(target, _gpow(ideal_class, exponent, modulus), modulus)

    pairs = list(zip(classes, secret))
    rng.shuffle(pairs)
    classes = [pair[0] for pair in pairs]
    secret = [pair[1] for pair in pairs]

    classes = [_random_representative(z, rng, modulus) for z in classes]
    target = _random_representative(target, rng, modulus)

    return {
        "family": "bounded_gaussian_class_action_vectorization_v1",
        "n": n,
        "exponent_bound": exponent_bound,
        "slack_trits": slack_trits,
        "order": {"quadratic_generator": "i", "relation": "i^2=-1", "conductor": pow(3, depth)},
        "depth": depth,
        "modulus": modulus,
        "class_group_order": class_order,
        "class_generators": [[a, b] for a, b in classes],
        "target_class": [target[0], target[1]],
        "answer": secret,
    }


def render(inst: dict) -> str:
    n = int(inst["n"])
    r = int(inst["exponent_bound"])
    depth = int(inst["depth"])
    modulus = int(inst["modulus"])
    group_order = int(inst["class_group_order"])
    rows = "\n".join(
        f"  {index}: [{pair[0]}, {pair[1]}]"
        for index, pair in enumerate(inst["class_generators"])
    )
    statement = f"""BOUNDED IDEAL-CLASS ACTION VECTORIZATION

Work in the finite Gaussian residue ring R=(Z/{modulus}Z)[i], where i^2=-1.
A displayed pair [a,b] denotes the residue a+b*i; both coordinates are reduced
to the inclusive range 0 through {modulus - 1}.  Multiplication is

  [a,b]*[c,d] = [a*c-b*d, a*d+b*c] modulo {modulus}.

Every displayed pair is a unit.  Two units z and w represent the same ideal
class when z*w^(-1) is an invertible real scalar times one of 1,-1,i,-i.
Equivalently, after computing z*w^(-1), at least one of its two coordinates is
zero modulo {modulus}.  Negative powers use the multiplicative inverse in R.

These are the residue-class coordinates for the ideal class group of the
quadratic order O_d=Z+3^d Z[i], with d={depth}.  Its order is exactly
2*3^(d-1)={group_order}.  The group operation is multiplication of the above
classes; it is commutative after quotienting by the stated equivalence.

There are n={n} public ideal classes Q_0,...,Q_{n - 1}.  Find exactly {n}
ordinary integers e_0,...,e_{n - 1}, each in the inclusive interval
[-{r},{r}], such that

  Q_0^e_0 * Q_1^e_1 * ... * Q_{n - 1}^e_{n - 1}

represents the target class.  The exponent list is in the displayed 0-based
order.  Repeated exponent values are allowed; no position may be omitted.
Any bounded exponent list producing the target is accepted.

Public ideal classes, one line as "index: [real, imaginary]":
{rows}

Target class: {json.dumps(inst["target_class"], separators=(",", ":"))}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{n} integers in displayed index order.
Example of the required shape only: <answer>{json.dumps([0] * n, separators=(",", ":"))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: Any) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def _instance_units(inst: dict) -> tuple[int, int, int, list[tuple[int, int]], tuple[int, int]]:
    n = int(inst["n"])
    r = int(inst["exponent_bound"])
    modulus = int(inst["modulus"])
    classes_raw = inst["class_generators"]
    target_raw = inst["target_class"]
    if not isinstance(classes_raw, list) or len(classes_raw) != n:
        raise ValueError("wrong number of public classes")
    classes: list[tuple[int, int]] = []
    for pair in classes_raw:
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in pair)
        ):
            raise ValueError("malformed public class")
        z = (pair[0] % modulus, pair[1] % modulus)
        _ginv(z, modulus)
        classes.append(z)
    if (
        not isinstance(target_raw, list)
        or len(target_raw) != 2
        or any(isinstance(x, bool) or not isinstance(x, int) for x in target_raw)
    ):
        raise ValueError("malformed target class")
    target = (target_raw[0] % modulus, target_raw[1] % modulus)
    _ginv(target, modulus)
    return n, r, modulus, classes, target


def _power_tables(
    classes: list[tuple[int, int]], r: int, modulus: int
) -> list[list[tuple[int, int]]]:
    key = (modulus, r, tuple(classes))
    cached = _VERIFY_TABLE_CACHE.get(key)
    if cached is not None:
        return cached
    tables: list[list[tuple[int, int]]] = []
    for z in classes:
        positive = [(1, 0)]
        for _ in range(r):
            positive.append(_gmul(positive[-1], z, modulus))
        z_inverse = _ginv(z, modulus)
        negative = [(1, 0)]
        for _ in range(r):
            negative.append(_gmul(negative[-1], z_inverse, modulus))
        tables.append([negative[-e] if e < 0 else positive[e] for e in range(-r, r + 1)])
    if len(_VERIFY_TABLE_CACHE) >= 16:
        _VERIFY_TABLE_CACHE.pop(next(iter(_VERIFY_TABLE_CACHE)))
    _VERIFY_TABLE_CACHE[key] = tables
    return tables


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list"
    if len(answer) == 0:
        return False, "answer is empty"
    try:
        n, r, modulus, classes, target = _instance_units(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"invalid instance: {exc}"
    if len(answer) < n:
        return False, f"too few exponents: expected {n}"
    if len(answer) > n:
        return False, f"too many exponents: expected {n}"
    for index, exponent in enumerate(answer):
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            return False, f"exponent {index} is not an integer"
        if not -r <= exponent <= r:
            return False, f"exponent {index} is outside [-{r},{r}]"

    product = (1, 0)
    tables = _power_tables(classes, r, modulus)
    for table, exponent in zip(tables, answer):
        product = _gmul(product, table[exponent + r], modulus)
    if not _class_equal(product, target, modulus):
        return False, "class product does not equal the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    n = int(inst["n"])
    r = int(inst["exponent_bound"])
    return [rng.randint(-r, r) for _ in range(n)]


def search_space(inst: dict) -> int | None:
    return pow(2 * int(inst["exponent_bound"]) + 1, int(inst["n"]))


def enumerate_all(inst: dict) -> int | None:
    size = search_space(inst)
    if size is None or size > _ENUMERATION_CAP:
        return None
    n = int(inst["n"])
    r = int(inst["exponent_bound"])
    valid = 0
    for candidate in itertools.product(range(-r, r + 1), repeat=n):
        valid += int(verify(inst, candidate)[0])
    return valid


def _discrete_log(inst: dict, value: tuple[int, int]) -> tuple[int, int]:
    """Pohlig-Hellman in the cyclic class group; return (log, group ops)."""
    modulus = int(inst["modulus"])
    depth = int(inst["depth"])
    order = int(inst["class_group_order"])
    generator = (-2 % modulus, 4 % modulus)
    k = depth - 1
    order3 = pow(3, k)
    a, ops = _gpow_counted(generator, 2, modulus)
    h, count = _gpow_counted(value, 2, modulus)
    ops += count
    gamma, count = _gpow_counted(a, pow(3, k - 1), modulus)
    ops += count
    gamma_powers = [(1, 0), gamma, _gmul(gamma, gamma, modulus)]
    ops += 1
    a_powers = [a]
    for _ in range(1, k):
        cube = _gmul(_gmul(a_powers[-1], a_powers[-1], modulus), a_powers[-1], modulus)
        a_powers.append(cube)
        ops += 2

    x = 0
    ax = (1, 0)
    place = 1
    for index in range(k):
        c = _gmul(h, _ginv(ax, modulus), modulus)
        ops += 2
        d, count = _gpow_counted(c, pow(3, k - 1 - index), modulus)
        ops += count
        digit = None
        for possible in range(3):
            if _class_equal(d, gamma_powers[possible], modulus):
                digit = possible
                ops += 2
                break
            ops += 2
        if digit is None:
            raise ValueError("class is outside the generated 3-primary subgroup")
        if digit:
            ax = _gmul(ax, _gpow(a_powers[index], digit, modulus), modulus)
            ops += digit + 1
        x += digit * place
        place *= 3

    gx, count = _gpow_counted(generator, x, modulus)
    ops += count
    if _class_equal(gx, value, modulus):
        return x, ops + 2
    gx2 = _gmul(gx, _gpow(generator, order3, modulus), modulus)
    ops += order3.bit_length() + 1
    if _class_equal(gx2, value, modulus):
        return x + order3, ops + 2
    raise ValueError("discrete logarithm reconstruction failed")


def _recover_logs(inst: dict) -> tuple[list[int], int, int]:
    _, _, _, classes, target = _instance_units(inst)
    weights: list[int] = []
    operations = 0
    for z in classes:
        value, cost = _discrete_log(inst, z)
        weights.append(value)
        operations += cost
    target_log, cost = _discrete_log(inst, target)
    operations += cost
    return weights, target_log, operations


def _canonical_payload(inst: dict) -> tuple:
    weights, target, _ = _recover_logs(inst)
    order = int(inst["class_group_order"])
    candidates = []
    for pivot in weights:
        inverse = pow(pivot, -1, order)
        for sign in (1, -1):
            multiplier = sign * inverse % order
            normalized_weights = sorted(
                min(multiplier * weight % order, (-multiplier * weight) % order)
                for weight in weights
            )
            normalized_target = multiplier * target % order
            candidates.append((tuple(normalized_weights), normalized_target))
    best = min(candidates)
    return (
        int(inst["n"]),
        int(inst["exponent_bound"]),
        int(inst["depth"]),
        best,
    )


def canonical_key(inst: dict) -> str:
    payload = _canonical_payload(inst)
    blob = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    harder = {k: v for k, v in params.items() if k != "_preset"}
    n = int(harder.get("n", 40))
    r = int(harder.get("exponent_bound", 5))
    slack = int(harder.get("slack_trits", 4))
    if n != 40:
        # Normalize ad-hoc inputs to the shipping answer length before widening.
        harder.update({"n": max(40, n), "exponent_bound": max(5, r), "slack_trits": slack})
        return harder
    if r < 7:
        harder["exponent_bound"] = 7
        harder["slack_trits"] = slack
        return harder
    # r=8 raises worst-case exact group operations beyond the G9(c) limit.
    return "cap_bound"


def _nearest_integer(value: Fraction) -> int:
    return math.floor(value + Fraction(1, 2))


def _lll_reduce(
    basis: list[list[int]], delta: Fraction = Fraction(3, 4), limit: int = 60_000
) -> tuple[list[list[int]], dict]:
    """Exact row-basis LLL, adapted to keep the attack dependency-free."""
    rows = [row[:] for row in basis]
    m = len(rows)
    dimension = len(rows[0])
    star = [[Fraction(0) for _ in range(dimension)] for _ in range(m)]
    mu = [[Fraction(0) for _ in range(m)] for _ in range(m)]
    norms = [Fraction(0) for _ in range(m)]

    def dot(x: list, y: list) -> Fraction:
        return sum(a * b for a, b in zip(x, y))

    for i in range(m):
        star[i] = [Fraction(value) for value in rows[i]]
        for j in range(i):
            if norms[j] == 0:
                raise ValueError("linearly dependent LLL basis")
            mu[i][j] = dot(rows[i], star[j]) / norms[j]
            star[i] = [
                star[i][column] - mu[i][j] * star[j][column]
                for column in range(dimension)
            ]
        norms[i] = dot(star[i], star[i])

    reductions = 0
    swaps = 0
    iterations = 0
    k = 1

    def reduce_row(i: int, j: int) -> None:
        nonlocal reductions
        q = _nearest_integer(mu[i][j])
        rows[i] = [rows[i][z] - q * rows[j][z] for z in range(dimension)]
        for z in range(j):
            mu[i][z] -= q * mu[j][z]
        mu[i][j] -= q
        reductions += 1

    while k < m and iterations < limit:
        iterations += 1
        if abs(mu[k][k - 1]) > Fraction(1, 2):
            reduce_row(k, k - 1)
        if norms[k] >= (delta - mu[k][k - 1] ** 2) * norms[k - 1]:
            for j in range(k - 2, -1, -1):
                if abs(mu[k][j]) > Fraction(1, 2):
                    reduce_row(k, j)
            k += 1
            continue

        nu = mu[k][k - 1]
        alpha = norms[k] + nu * nu * norms[k - 1]
        if alpha == 0:
            raise ValueError("linearly dependent LLL basis")
        beta = norms[k - 1] / alpha
        mu[k][k - 1] = nu * beta
        norms[k] *= beta
        norms[k - 1] = alpha
        rows[k], rows[k - 1] = rows[k - 1], rows[k]
        mu[k][: k - 1], mu[k - 1][: k - 1] = mu[k - 1][: k - 1], mu[k][: k - 1]
        for i in range(k + 1, m):
            xi = mu[i][k]
            mu[i][k] = mu[i][k - 1] - nu * xi
            mu[i][k - 1] = mu[k][k - 1] * mu[i][k] + xi
        swaps += 1
        k = max(k - 1, 1)

    return rows, {
        "iterations": iterations,
        "size_reductions": reductions,
        "swaps": swaps,
        "limit_reached": k < m,
    }


def _lll_attack(
    weights: list[int], target: int, order: int, r: int
) -> tuple[list[int] | None, dict]:
    n = len(weights)
    scale = 2 * r * math.isqrt(n) + 10
    basis: list[list[int]] = []
    for index, weight in enumerate(weights):
        row = [0] * (n + 2)
        row[index] = 1
        row[n] = scale * weight
        basis.append(row)
    modulus_row = [0] * (n + 2)
    modulus_row[n] = scale * order
    basis.append(modulus_row)
    target_row = [0] * (n + 2)
    target_row[n] = scale * target
    target_row[n + 1] = 1
    basis.append(target_row)

    reduced, stats = _lll_reduce(basis)
    for row in reduced:
        if abs(row[-1]) != 1 or row[n] != 0:
            continue
        orientation = -row[-1]
        candidate = [orientation * value for value in row[:n]]
        if (
            all(-r <= value <= r for value in candidate)
            and sum(weight * value for weight, value in zip(weights, candidate)) % order == target
        ):
            return candidate, stats
    return None, stats


def _one_sparse_attack(
    weights: list[int], target: int, order: int, r: int
) -> list[int] | None:
    for index, weight in enumerate(weights):
        for exponent in range(-r, r + 1):
            if exponent and exponent * weight % order == target:
                candidate = [0] * len(weights)
                candidate[index] = exponent
                return candidate
    return None


def _representative_statistic_attack(
    inst: dict, weights: list[int], target: int, order: int, r: int
) -> list[int] | None:
    """Try simple per-coordinate statistics that could reveal planted exponents."""
    pairs = [tuple(pair) for pair in inst["class_generators"]]
    n = len(pairs)
    by_magnitude = sorted(
        range(n),
        key=lambda index: (
            min(pairs[index][0], int(inst["modulus"]) - pairs[index][0])
            + min(pairs[index][1], int(inst["modulus"]) - pairs[index][1]),
            index,
        ),
    )
    ranked = [0] * n
    for rank, index in enumerate(by_magnitude):
        ranked[index] = -r + ((2 * r + 1) * rank) // n
    guesses = [
        ranked,
        [-value for value in ranked],
        [r if a < b else -r for a, b in pairs],
        [((a + b) % (2 * r + 1)) - r for a, b in pairs],
    ]
    for candidate in guesses:
        if sum(weight * value for weight, value in zip(weights, candidate)) % order == target:
            return candidate
    return None


def _greedy_attack(
    weights: list[int], target: int, order: int, r: int
) -> list[int] | None:
    def distance(value: int) -> int:
        residue = (target - value) % order
        return min(residue, order - residue)

    for ordering in (
        list(range(len(weights))),
        sorted(range(len(weights)), key=lambda j: min(weights[j], order - weights[j]), reverse=True),
    ):
        candidate = [0] * len(weights)
        total = 0
        for _ in range(3):
            changed = False
            for index in ordering:
                without = total - candidate[index] * weights[index]
                best = min(range(-r, r + 1), key=lambda e: distance(without + e * weights[index]))
                if best != candidate[index]:
                    total = without + best * weights[index]
                    candidate[index] = best
                    changed = True
            if total % order == target:
                return candidate
            if not changed:
                break
    return None


def _random_restart_attack(
    weights: list[int], target: int, order: int, r: int, rng: random.Random
) -> tuple[list[int] | None, int]:
    attempts = 256
    for _ in range(attempts):
        candidate = [rng.randint(-r, r) for _ in weights]
        if sum(w * e for w, e in zip(weights, candidate)) % order == target:
            return candidate, attempts
    return None, attempts


def _capped_mitm_attack(
    weights: list[int], target: int, order: int, r: int, rng: random.Random
) -> tuple[list[int] | None, int]:
    midpoint = len(weights) // 2
    left_weights = weights[:midpoint]
    right_weights = weights[midpoint:]
    per_side = 20_000
    left: dict[int, list[int]] = {}
    for _ in range(per_side):
        vector = [rng.randint(-r, r) for _ in left_weights]
        value = sum(w * e for w, e in zip(left_weights, vector)) % order
        left.setdefault(value, vector)
    for _ in range(per_side):
        vector = [rng.randint(-r, r) for _ in right_weights]
        value = sum(w * e for w, e in zip(right_weights, vector)) % order
        complement = (target - value) % order
        if complement in left:
            return left[complement] + vector, 2 * per_side
    return None, 2 * per_side


def _audit_instance(inst: dict, seed: int) -> dict:
    audit_start = time.perf_counter()
    start = audit_start
    weights, target, dlog_ops = _recover_logs(inst)
    dlog_seconds = time.perf_counter() - start
    order = int(inst["class_group_order"])
    r = int(inst["exponent_bound"])

    candidates: dict[str, list[int] | None] = {}
    candidates["representative_coordinate_statistics"] = _representative_statistic_attack(
        inst, weights, target, order, r
    )
    candidates["one_sparse_target"] = _one_sparse_attack(weights, target, order, r)
    candidates["greedy_circular_residual"] = _greedy_attack(weights, target, order, r)
    random_candidate_value, random_attempts = _random_restart_attack(
        weights, target, order, r, random.Random(seed ^ 0xA5A5A5A5)
    )
    candidates["random_restart_256"] = random_candidate_value
    mitm_candidate, mitm_nodes = _capped_mitm_attack(
        weights, target, order, r, random.Random(seed ^ 0x5A5A5A5A)
    )
    candidates["capped_meet_in_middle_40000"] = mitm_candidate

    lll_start = time.perf_counter()
    lll_candidate, lll_stats = _lll_attack(weights, target, order, r)
    lll_seconds = time.perf_counter() - lll_start
    candidates["exact_lll_embedding"] = lll_candidate

    successes = {}
    for name, candidate in candidates.items():
        successes[name] = bool(candidate is not None and verify(inst, candidate)[0])
    return {
        "successes": successes,
        "dlog_operations": dlog_ops,
        "dlog_wall_clock_sec": dlog_seconds,
        "lll_wall_clock_sec": lll_seconds,
        "lll": lll_stats,
        "random_restarts": random_attempts,
        "mitm_nodes": mitm_nodes,
        "strongest_wall_clock_sec": dlog_seconds + lll_seconds,
        "audit_wall_clock_sec": time.perf_counter() - audit_start,
    }


def _copy_without_answer(inst: dict) -> dict:
    return copy.deepcopy(inst)


def _reorder_instance(inst: dict, order_indices: list[int]) -> tuple[dict, list[int]]:
    moved = _copy_without_answer(inst)
    moved["class_generators"] = [inst["class_generators"][i] for i in order_indices]
    answer = [inst["answer"][i] for i in order_indices]
    moved["answer"] = answer
    return moved, answer


def _invert_instance(inst: dict, indices: set[int]) -> tuple[dict, list[int]]:
    moved = _copy_without_answer(inst)
    modulus = int(inst["modulus"])
    answer = list(inst["answer"])
    for index in indices:
        z = tuple(inst["class_generators"][index])
        inverse = _ginv(z, modulus)
        moved["class_generators"][index] = [inverse[0], inverse[1]]
        answer[index] = -answer[index]
    moved["answer"] = answer
    return moved, answer


def _automorphism_instance(inst: dict, multiplier: int) -> tuple[dict, list[int]]:
    moved = _copy_without_answer(inst)
    modulus = int(inst["modulus"])
    moved["class_generators"] = [
        list(_gpow(tuple(pair), multiplier, modulus)) for pair in inst["class_generators"]
    ]
    moved["target_class"] = list(_gpow(tuple(inst["target_class"]), multiplier, modulus))
    return moved, list(inst["answer"])


def _representative_instance(inst: dict, rng: random.Random) -> tuple[dict, list[int]]:
    moved = _copy_without_answer(inst)
    modulus = int(inst["modulus"])
    replaced = []
    for pair in inst["class_generators"]:
        replaced.append(list(_random_representative(tuple(pair), rng, modulus)))
    moved["class_generators"] = replaced
    moved["target_class"] = list(_random_representative(tuple(inst["target_class"]), rng, modulus))
    return moved, list(inst["answer"])


def _answer_metrics(answer: Any) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))

    def atoms(value: Any) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(v) for v in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def _intended_operations(n: int, r: int) -> int:
    # Worst-case square-and-multiply class operations, one optional inversion,
    # one accumulator multiply, and the final quotient comparison.
    bits = r.bit_length()
    worst_popcount = max(i.bit_count() for i in range(1, r + 1))
    per_coordinate = (bits - 1) + worst_popcount + 1 + 1
    return n * per_coordinate + 2


def selftest() -> dict:
    report: dict[str, Any] = {}

    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            g1_checks += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=1729, **ship_params)
    answer = list(ship["answer"])
    corruptions: dict[str, Any] = {
        "drop_one": answer[:-1],
        "duplicate_one": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [ship["exponent_bound"] + 1] + answer[1:],
    }
    swapped = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            if answer[i] == answer[j]:
                continue
            candidate = answer[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if not verify(ship, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    corruptions["swap_two_positions"] = swapped if swapped is not None else answer[::-1]
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({entry["reason"] for entry in reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in reasons.values()) and distinct_reasons == len(reasons),
        "cases": reasons,
        "distinct_reasons": distinct_reasons,
    }

    realistic = (
        "I multiplied the Gaussian classes modulo the conductor.\n\n"
        "```text\nFinal witness follows.\n```\n"
        f"<answer>\n```json\n{json.dumps(ship['answer'])}\n```\n</answer>\n"
        "The entries are in the displayed order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"] and parse_answer("no tagged answer") is None,
        "realistic_prose": True,
        "parsed_matches": parsed == ship["answer"],
        "garbage_returns_none": parse_answer("<answer>not json</answer>") is None,
    }

    # Pohlig--Hellman gives an exact isomorphism from the Gaussian quotient to
    # Z/(2*3^(d-1)).  Use it here so 200,000 density samples do one modular dot
    # product apiece instead of repeating equivalent Gaussian multiplications.
    guess_weights, guess_target, _ = _recover_logs(ship)
    guess_order = int(ship["class_group_order"])
    guess_rng = random.Random(0x201210803)
    guess_total = 200_000
    guess_hits = 0
    density_crosschecks = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(ship, guess_rng)
        congruent = (
            sum(weight * value for weight, value in zip(guess_weights, candidate))
            % guess_order
            == guess_target
        )
        guess_hits += int(congruent)
        if density_crosschecks < 128:
            assert verify(ship, candidate)[0] == congruent
            density_crosschecks += 1
    guess_seconds = time.perf_counter() - guess_start
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "structure_aware_space": search_space(ship),
        "sampler": "uniform over every integer vector in the stated bounded box",
        "exact_coordinate_crosschecks": density_crosschecks,
        "wall_clock_sec": guess_seconds,
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    audits = []
    for offset in range(8):
        audit_seed = 91_000 + offset
        audit_inst = make_instance(seed=audit_seed, **ship_params)
        audits.append(_audit_instance(audit_inst, audit_seed))

    strongest = max(audits, key=lambda item: item["strongest_wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and guess_total >= 200_000 and guess_rate < 1e-6,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_rate,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec": strongest["strongest_wall_clock_sec"],
        "baseline_dlog_operations": strongest["dlog_operations"],
        "baseline_lll_iterations": strongest["lll"]["iterations"],
        "baseline_lll_swaps": strongest["lll"]["swaps"],
        "baseline_attack": "Pohlig-Hellman preprocessing plus exact LLL embedding",
    }

    attack_names = [
        "representative_coordinate_statistics",
        "one_sparse_target",
        "greedy_circular_residual",
        "random_restart_256",
        "capped_meet_in_middle_40000",
        "exact_lll_embedding",
    ]
    attacks = {}
    for name in attack_names:
        attacks[name] = {
            "successes": sum(int(audit["successes"][name]) for audit in audits),
            "attempts": len(audits),
        }
    panel_pass = all(entry["successes"] == 0 and entry["attempts"] >= 8 for entry in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": panel_pass,
        "attacks": attacks,
        "audit_seeds": list(range(91_000, 91_008)),
        "per_seed_costs": [
            {
                "dlog_operations": audit["dlog_operations"],
                "dlog_wall_clock_sec": audit["dlog_wall_clock_sec"],
                "lll_wall_clock_sec": audit["lll_wall_clock_sec"],
                "lll_iterations": audit["lll"]["iterations"],
                "lll_swaps": audit["lll"]["swaps"],
                "mitm_nodes": audit["mitm_nodes"],
                "audit_wall_clock_sec": audit["audit_wall_clock_sec"],
            }
            for audit in audits
        ],
        "domain_standard_attack": "Pohlig-Hellman discrete logs plus exact LLL subset-sum embedding",
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(ship_params["n"])
    doubled = make_instance(seed=8080, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(ship),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_space_bits": search_space(ship).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verification": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_failures = []
    unrelated_keys = []
    key_params = {"n": 12, "exponent_bound": 2, "slack_trits": 4}
    for seed in range(20):
        base = make_instance(seed=30_000 + seed, **key_params)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        rng = random.Random(40_000 + seed)

        order_indices = list(range(base["n"]))
        rng.shuffle(order_indices)
        reordered, reordered_answer = _reorder_instance(base, order_indices)

        inversion_indices = {i for i in range(base["n"]) if rng.randrange(2)}
        inverted, inverted_answer = _invert_instance(base, inversion_indices)

        group_order = int(base["class_group_order"])
        while True:
            multiplier = rng.randrange(1, group_order)
            if math.gcd(multiplier, group_order) == 1:
                break
        automated, automated_answer = _automorphism_instance(base, multiplier)
        represented, represented_answer = _representative_instance(base, rng)

        composed, composed_answer = _reorder_instance(inverted, order_indices)
        composed, composed_answer = _automorphism_instance(composed, multiplier)
        composed["answer"] = composed_answer
        composed, composed_answer = _representative_instance(composed, rng)

        for label, transformed, witness in (
            ("reorder", reordered, reordered_answer),
            ("invert", inverted, inverted_answer),
            ("automorphism", automated, automated_answer),
            ("representative", represented, represented_answer),
            ("composition", composed, composed_answer),
        ):
            invariant_checks += 1
            if canonical_key(transformed) != base_key:
                invariant_failures.append(f"{seed}/{label}/key")
            ok, reason = verify(transformed, witness)
            carried_checks += int(ok)
            if not ok:
                invariant_failures.append(f"{seed}/{label}/witness:{reason}")

    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and carried_checks == invariant_checks and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary public-generator permutation",
            "independent generator inversion with exponent negation",
            "cyclic class-group automorphism z -> z^u for gcd(u,|Cl|)=1",
            "independent equivalent Gaussian unit/real-unit representatives",
            "composition of all preceding transformations",
        ],
        "key_definition": "normalized discrete-log multiset and target, SHA-256 encoded",
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    verification_operations = _intended_operations(ship["n"], ship["exponent_bound"])
    # This is a lower bound on *finding* the witness after recognizing the
    # cyclic quotient.  The subsequent bounded subset-sum is still unsolved;
    # counting only `verification_operations` here would confuse checking a
    # supplied certificate with the intended solution route prohibited by G9.
    operations = min(audit["dlog_operations"] for audit in audits)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    caps_pass = chars <= 2_000 and elements <= 256 and operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": caps_pass,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_recorded_not_gated": True,
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": operations,
        "intended_route_operations_are_lower_bound": True,
        "intended_route_known": False,
        "verification_operations_for_supplied_witness": verification_operations,
        "operation_basis": (
            "minimum measured Pohlig-Hellman preprocessing cost over eight shipping "
            "seeds; bounded modular subset-sum work remains afterward"
        ),
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
        "within_caps": caps_pass,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
