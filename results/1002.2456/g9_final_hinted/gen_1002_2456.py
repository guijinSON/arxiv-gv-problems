"""Verified cyclic-code multiplier-equivalence generator for arXiv:1002.2456.

The witness is sampled first.  A second cyclic code is obtained by carrying the
first code's defining q-cyclotomic orbits through that multiplier.  No generated
instance is solved in order to learn its answer.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The family only needs exact modular integer arithmetic.
    exact_matrices = rationals = None


TRACK = "B"

STRUCTURAL_HINT = (
    "In the quotient F_p^*/<q>, the product of a defining set's orbit "
    "representatives changes by the hidden multiplier raised to the number of orbits."
)
PLACEBO_HINT = (
    "In the quotient F_p^*/<q>, careful checking of every defining-set orbit "
    "representative helps avoid errors with the coordinate conventions."
)


PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "cyclic linear codes over F_q",
        "q-cyclotomic defining-set orbits modulo the prime code length p",
        "coordinate multiplier M_a and its inverse",
    ],
    "verification_operations": [
        "exact modular multiplication",
        "q-cyclotomic orbit expansion",
        "finite-set equality",
        "modular inverse check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Multiplication of all orbit representatives in F_p^*/<q> compresses "
        "equivalence of two defining sets to one group equation; without it, a "
        "solver scans possible orbit matches and expands their cyclotomic orbits."
    ),
    "hardness_basis": (
        "Track B: the Section III fixed-orbit multiplier scan is O(t^2 m) exact "
        "modular work; at shipping m=256 and t=89 it averaged 1,045,206 exact "
        "operations and 0.381 seconds per instance over eight measured seeds, "
        "while the quotient-product invariant used at most 254 operations; an "
        "efficient exact algorithm therefore exists and Track A is not claimed."
    ),
    "max_answer_tokens": 6,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "hard": {"n": 300_000_000, "orbit_order": 256, "orbit_count": 89},
}
SHIPPING_DIFFICULTY = "hard"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [a,a_inverse] encoding the multiplier M_a and M_a^{-1}; "
        "both entries are canonical integers in 1..p-1 and their product is 1 modulo p."
    ),
    "bounds": {
        "atomic_residues": 2,
        "minimum_residue": 1,
        "maximum_residue": "instance prime p minus 1",
        "structural_rule": "the residues are inverses and are not equal",
        "candidate_count": "p minus 3 (the self-inverse residues 1 and p-1 are excluded)",
    },
}


NOTES = """\
Section II defines permutation equivalence and the coordinate action sigma(C).
Section III fixes the native problem used here: for cyclic codes, a multiplier
M_a is the coordinate permutation i -> a*i modulo the length, and the section
studies the set H(P) containing the possible equivalence permutations.  The
paragraph before Lemma 10 and Theorem 15 identify the easy side that rules out
Track A: in several regimes equivalence is completely reduced to multipliers,
and the paper gives explicit structured sets of such permutations.

The construction uses the paper's own defining-set objects.  Choose primes p and
q for which q has exact order m modulo p.  Every listed residue r represents the
q-cyclotomic orbit {r*q^j mod p: 0<=j<m}.  Sample M_a first and obtain the second
code by multiplying every defining exponent by a^{-1}.  The certificate [a,a^-1]
is therefore carried through a structure-preserving map, never searched for.

This is Track B.  A fixed-orbit scan tries which first-code orbit matches one
fixed second-code orbit and checks each candidate by exact orbit expansion; its
O(t^2*m) measured cost is reported as reference_algorithm.  The compact route
works in F_p^*/<q>: the ratio of the two products of orbit representatives is
a^t, up to <q>.  Since gcd(t,(p-1)/m)=1 by construction, one modular exponent
recovers an element of the valid coset a<q>.  The cheap minimum, maximum, first,
ordinary-sum, raw-product, sorted-vote, and 256-uniform-restart attacks are all
tested.  Generation rejects the rare draw exposed by one of the deterministic
cheap signatures; this conditioning never discovers the already sampled answer.
"""


_ENUMERATION_CAP = 50_000
_PARAMETER_CACHE: dict[tuple[int, int, int], tuple[int, int, int]] = {}
_VERIFY_CACHE: dict[
    tuple[int, int, tuple[int, ...], tuple[int, ...]],
    tuple[frozenset[int], tuple[int, ...]],
] = {}
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the 64-bit range used by the presets."""
    if value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
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


def _parameters(n: int, orbit_order: int, orbit_count: int) -> tuple[int, int, int]:
    key = (n, orbit_order, orbit_count)
    if key in _PARAMETER_CACHE:
        return _PARAMETER_CACHE[key]
    if not (_is_int(n) and n >= 5):
        raise ValueError("n must be an integer at least 5")
    if not (_is_int(orbit_order) and orbit_order >= 2 and orbit_order & (orbit_order - 1) == 0):
        raise ValueError("orbit_order must be a power of two at least 2")
    if not (_is_int(orbit_count) and orbit_count >= 3 and orbit_count % 2 == 1):
        raise ValueError("orbit_count must be an odd integer at least 3")

    p = n + ((1 - n) % orbit_order)
    while True:
        quotient_order = (p - 1) // orbit_order
        if quotient_order >= orbit_count and math.gcd(orbit_count, quotient_order) == 1 and _is_prime(p):
            break
        p += orbit_order

    q_mod_p = None
    for base in range(2, 10_000):
        candidate = pow(base, (p - 1) // orbit_order, p)
        if pow(candidate, orbit_order, p) != 1:
            continue
        if orbit_order == 2 or pow(candidate, orbit_order // 2, p) != 1:
            q_mod_p = candidate
            break
    if q_mod_p is None:
        raise RuntimeError("could not construct the cyclotomic subgroup")

    # Dirichlet's theorem guarantees primes in this coprime residue class.  For
    # the supported sizes the deterministic search terminates within a few steps.
    multiplier = 1
    while True:
        q = q_mod_p + multiplier * p
        if _is_prime(q):
            break
        multiplier += 1

    result = (p, q, q_mod_p)
    _PARAMETER_CACHE[key] = result
    return result


def _orbit(residue: int, p: int, q_mod_p: int, order: int) -> tuple[int, ...]:
    values = []
    value = residue % p
    for _ in range(order):
        values.append(value)
        value = value * q_mod_p % p
    return tuple(values)


def _coset_key(residue: int, p: int, q_mod_p: int, order: int) -> int:
    return min(_orbit(residue, p, q_mod_p, order))


def _coset_set(representatives: list[int], p: int, q_mod_p: int, order: int) -> frozenset[int]:
    return frozenset(_coset_key(r, p, q_mod_p, order) for r in representatives)


def _quotient_label(residue: int, p: int, order: int) -> int:
    """An exact label for a coset of the order-``order`` subgroup of F_p^*."""
    return pow(residue % p, order, p)


def _valid_multiplier_data(
    p: int,
    q_mod_p: int,
    order: int,
    reps1: list[int],
    reps2: list[int],
    multiplier: int,
) -> bool:
    if not (1 <= multiplier < p):
        return False
    # F_p^* is cyclic.  Raising to ``order`` has kernel equal to the unique
    # subgroup <q> of that order, so it labels the displayed cyclotomic cosets
    # exactly.  The cache contains only data derived from the instance.
    cache_key = (p, order, tuple(reps1), tuple(reps2))
    cached = _VERIFY_CACHE.get(cache_key)
    if cached is None:
        target = frozenset(_quotient_label(r, p, order) for r in reps1)
        source_labels = tuple(_quotient_label(r, p, order) for r in reps2)
        cached = (target, source_labels)
        _VERIFY_CACHE[cache_key] = cached
    target, source_labels = cached
    factor = _quotient_label(multiplier, p, order)
    image = frozenset(factor * label % p for label in source_labels)
    return image == target


def _ratio(numerator: int, denominator: int, p: int) -> int | None:
    denominator %= p
    if denominator == 0:
        return None
    return numerator % p * pow(denominator, -1, p) % p


def _cheap_attack_values(
    p: int, reps1: list[int], reps2: list[int]
) -> dict[str, int | None]:
    sorted1 = sorted(reps1)
    sorted2 = sorted(reps2)
    ratios = [_ratio(x, y, p) for x, y in zip(sorted1, sorted2)]
    counts: dict[int, int] = {}
    for value in ratios:
        if value is not None:
            counts[value] = counts.get(value, 0) + 1
    vote = min(counts, key=lambda x: (-counts[x], x)) if counts else None

    product1 = 1
    product2 = 1
    for value in reps1:
        product1 = product1 * value % p
    for value in reps2:
        product2 = product2 * value % p
    return {
        "first_representative_ratio": _ratio(reps1[0], reps2[0], p),
        "minimum_representative_ratio": _ratio(min(reps1), min(reps2), p),
        "maximum_representative_ratio": _ratio(max(reps1), max(reps2), p),
        "ordinary_sum_ratio": _ratio(sum(reps1), sum(reps2), p),
        "raw_product_ratio": _ratio(product1, product2, p),
        "sorted_position_vote": vote,
    }


def make_instance(n: int, seed: int = 0, **params: Any) -> dict[str, Any]:
    """Construct two equivalent cyclic codes after sampling the multiplier first."""
    orbit_order = params.get("orbit_order", 8)
    orbit_count = params.get("orbit_count", 13)
    p, q, q_mod_p = _parameters(n, orbit_order, orbit_count)
    rng = random.Random(seed)

    for _attempt in range(20_000):
        keys: set[int] = set()
        reps1: list[int] = []
        while len(reps1) < orbit_count:
            residue = rng.randrange(1, p)
            key = _coset_key(residue, p, q_mod_p, orbit_order)
            if key not in keys:
                keys.add(key)
                reps1.append(residue)

        a = rng.randrange(2, p - 1)
        a_inverse = pow(a, -1, p)
        reps2 = []
        for residue in reps1:
            orbit_shift = pow(q_mod_p, rng.randrange(orbit_order), p)
            reps2.append(a_inverse * residue % p * orbit_shift % p)
        rng.shuffle(reps1)
        rng.shuffle(reps2)

        if _valid_multiplier_data(p, q_mod_p, orbit_order, reps1, reps2, a_inverse):
            # Swapping answer fields would accidentally be valid when a^2 lies
            # in <q>; exclude that case so the corruption test is meaningful.
            continue
        attacks = _cheap_attack_values(p, reps1, reps2)
        if any(
            candidate is not None
            and _valid_multiplier_data(
                p, q_mod_p, orbit_order, reps1, reps2, candidate
            )
            for candidate in attacks.values()
        ):
            continue

        return {
            "paper": "arXiv:1002.2456",
            "requested_n": n,
            "p": p,
            "q": q,
            "q_mod_p": q_mod_p,
            "orbit_order": orbit_order,
            "orbit_count": orbit_count,
            "code1_orbit_representatives": reps1,
            "code2_orbit_representatives": reps2,
            "answer": [a, a_inverse],
        }
    raise RuntimeError("could not hide the multiplier from the cheap probes")


def render(inst: dict[str, Any]) -> str:
    p = inst["p"]
    q = inst["q"]
    m = inst["orbit_order"]
    t = inst["orbit_count"]
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\nStructural hint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        hint = "\nHint: " + PLACEBO_HINT + "\n"

    return f"""Cyclic-code equivalence by a coordinate multiplier

All arithmetic in exponents is modulo the prime code length p={p}.
The code alphabet is the prime field F_q with q={q}.  The residue of q modulo
p is {inst['q_mod_p']} and has exact multiplicative order m={m}.

For a nonzero residue r modulo p, define its q-cyclotomic orbit
    O(r) = {{r*q^j mod p : j=0,1,...,{m - 1}}}.
Every orbit here has exactly {m} distinct elements.  A list R of representatives
defines the exponent set D(R)=the union of O(r) over r in R.  Relative to a
primitive p-th root alpha in F_(q^{m}), D(R) defines the length-p cyclic code
C(R) over F_q whose code polynomials vanish at alpha^d for every d in D(R).
The listed representatives have pairwise disjoint orbits; their printed order
has no meaning, and replacing a representative by another element of its orbit
does not change the code.

CODE 1 has these {t} q-orbit representatives:
{json.dumps(inst['code1_orbit_representatives'])}

CODE 2 has these {t} q-orbit representatives:
{json.dumps(inst['code2_orbit_representatives'])}

For 1 <= a < p, the coordinate multiplier M_a sends coordinate i to a*i mod p
(coordinates are 0-based, including coordinate 0).  With the convention above,
M_a maps CODE 1 to CODE 2 exactly when multiplying every defining exponent of
CODE 2 by a gives the defining exponent set of CODE 1.

Find any such a and also give b=a^(-1) mod p.  Output exactly two canonical
integers [a,b], each in the inclusive range 1,...,p-1.  The first entry is the
forward multiplier from CODE 1 to CODE 2 under the stated convention, and the
second is its inverse.
{hint}
Give your final answer inside <answer></answer> tags as compact JSON [a,b].
Example of the required syntax: <answer>[2,{(p + 1) // 2}]</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict[str, Any], answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer is missing the inverse residue"
    if len(answer) > 2:
        if len(set(map(repr, answer))) < len(answer):
            return False, "answer contains a duplicated residue field"
        return False, "answer must contain exactly two residues"
    if not all(_is_int(value) for value in answer):
        return False, "both residues must be integers"
    a, a_inverse = answer
    p = inst["p"]
    if not (1 <= a < p and 1 <= a_inverse < p):
        return False, "residue out of the inclusive range 1..p-1"
    if a * a_inverse % p != 1:
        return False, "second residue is not the modular inverse of the first"
    if not _valid_multiplier_data(
        p,
        inst["q_mod_p"],
        inst["orbit_order"],
        inst["code1_orbit_representatives"],
        inst["code2_orbit_representatives"],
        a,
    ):
        return False, "forward multiplier does not map CODE 2's defining set to CODE 1's"
    return True, "ok"


def random_candidate(inst: dict[str, Any], rng: random.Random) -> list[int]:
    # The statement gives the no-repetition rule for free, so exclude the two
    # self-inverse residues rather than sampling from a naively larger space.
    a = rng.randrange(2, inst["p"] - 1)
    return [a, pow(a, -1, inst["p"])]


def search_space(inst: dict[str, Any]) -> int:
    return inst["p"] - 3


def enumerate_all(inst: dict[str, Any]) -> int | None:
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    p = inst["p"]
    for a in range(1, p):
        if verify(inst, [a, pow(a, -1, p)])[0]:
            count += 1
    return count


def canonical_key(inst: dict[str, Any]) -> str:
    p = inst["p"]
    order = inst["orbit_order"]
    first = sorted(
        _quotient_label(value, p, order)
        for value in inst["code1_orbit_representatives"]
    )
    second = sorted(
        _quotient_label(value, p, order)
        for value in inst["code2_orbit_representatives"]
    )
    candidates = []
    for pivot in first + second:
        scale = pow(pivot, -1, p)
        a = tuple(sorted(scale * x % p for x in first))
        b = tuple(sorted(scale * x % p for x in second))
        candidates.append(min((a, b), (b, a)))
    normal = min(candidates)
    payload = json.dumps(
        {
            "p": p,
            "q": inst["q"],
            "orbit_order": order,
            "pair": normal,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict[str, Any]) -> dict[str, Any] | str | None:
    try:
        n = int(params["n"])
        order = int(params["orbit_order"])
        count = int(params["orbit_count"])
    except (KeyError, TypeError, ValueError):
        return None
    # Double the orbit-expansion work and the ambient multiplier space together.
    # Their ratio, and hence exact guess density, stays essentially fixed; the
    # two-residue answer and the number of displayed representatives do not grow.
    return {"n": n * 2, "orbit_order": order * 2, "orbit_count": count}


def _modinv_count(value: int, modulus: int) -> tuple[int, int]:
    old_r, r = value % modulus, modulus
    old_s, s = 1, 0
    divisions = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        divisions += 1
    if old_r != 1:
        raise ValueError("inverse does not exist")
    return old_s % modulus, divisions


def _pow_count(base: int, exponent: int, modulus: int) -> tuple[int, int]:
    result = 1
    value = base % modulus
    operations = 0
    e = exponent
    while e:
        if e & 1:
            result = result * value % modulus
            operations += 1
        e >>= 1
        if e:
            value = value * value % modulus
            operations += 1
    return result, operations


def _compact_route(inst: dict[str, Any]) -> tuple[list[int], int]:
    p = inst["p"]
    product1 = 1
    product2 = 1
    operations = 0
    for value in inst["code1_orbit_representatives"]:
        product1 = product1 * value % p
        operations += 1
    for value in inst["code2_orbit_representatives"]:
        product2 = product2 * value % p
        operations += 1
    inverse_product2, cost = _modinv_count(product2, p)
    operations += cost
    ratio = product1 * inverse_product2 % p
    operations += 1
    quotient_order = (p - 1) // inst["orbit_order"]
    exponent, cost = _modinv_count(inst["orbit_count"], quotient_order)
    operations += cost
    a, cost = _pow_count(ratio, exponent, p)
    operations += cost
    a_inverse, cost = _modinv_count(a, p)
    operations += cost
    return [a, a_inverse], operations


def _reference_algorithm(inst: dict[str, Any]) -> tuple[list[int] | None, int]:
    """Fixed-orbit scan, the ordinary exact algorithm for this representation."""
    p = inst["p"]
    q_mod_p = inst["q_mod_p"]
    order = inst["orbit_order"]
    reps1 = inst["code1_orbit_representatives"]
    reps2 = inst["code2_orbit_representatives"]
    operations = len(reps1) * (order - 1)
    target = _coset_set(reps1, p, q_mod_p, order)
    inverse, divisions = _modinv_count(reps2[0], p)
    operations += divisions
    for representative in reps1:
        candidate = representative * inverse % p
        operations += 1
        image = set()
        for source in reps2:
            scaled = candidate * source % p
            operations += 1
            image.add(_coset_key(scaled, p, q_mod_p, order))
            operations += order - 1
        if image == target:
            candidate_inverse, divisions = _modinv_count(candidate, p)
            operations += divisions
            return [candidate, candidate_inverse], operations
    return None, operations


def _attack_candidates(inst: dict[str, Any]) -> dict[str, object]:
    values = _cheap_attack_values(
        inst["p"],
        inst["code1_orbit_representatives"],
        inst["code2_orbit_representatives"],
    )
    result: dict[str, object] = {}
    for name, value in values.items():
        result[name] = None if value is None else [value, pow(value, -1, inst["p"])]
    return result


def _transformed_instance(
    inst: dict[str, Any], rng: random.Random, *, scale: int = 1, swap: bool = False
) -> dict[str, Any]:
    result = {key: value for key, value in inst.items() if key != "answer"}
    q_mod_p = inst["q_mod_p"]
    p = inst["p"]

    def changed(values: list[int]) -> list[int]:
        output = []
        for value in values:
            orbit_representative_change = pow(
                q_mod_p, rng.randrange(inst["orbit_order"]), p
            )
            output.append(value * scale % p * orbit_representative_change % p)
        rng.shuffle(output)
        return output

    first = changed(inst["code1_orbit_representatives"])
    second = changed(inst["code2_orbit_representatives"])
    if swap:
        first, second = second, first
        answer = [inst["answer"][1], inst["answer"][0]]
    else:
        answer = list(inst["answer"])
    result["code1_orbit_representatives"] = first
    result["code2_orbit_representatives"] = second
    result["answer"] = answer
    return result


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(v) for v in value)
    return 1


def selftest() -> dict[str, Any]:
    report: dict[str, Any] = {}

    planted = 0
    roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            planted += int(verify(inst, inst["answer"])[0])
            roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": planted == 16 and roundtrips == 16,
        "verified": planted,
        "attempts": 16,
        "json_roundtrips": roundtrips,
    }

    corruption_inst = make_instance(seed=7001, **DIFFICULTY[SHIPPING_DIFFICULTY])
    a, a_inverse = corruption_inst["answer"]
    corruptions = {
        "drop_one": [a],
        "swap_fields": [a_inverse, a],
        "duplicate_field": [a, a, a_inverse],
        "empty": [],
        "out_of_range": [corruption_inst["p"], a_inverse],
    }
    corruption_results = {
        name: {"accepted": verify(corruption_inst, value)[0], "reason": verify(corruption_inst, value)[1]}
        for name, value in corruptions.items()
    }
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": not any(item["accepted"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the cyclotomic quotient.\n```text\n<answer>\n```json\n"
        + json.dumps(corruption_inst["answer"])
        + "\n```\n</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    garbage = parse_answer("The calculation did not finish.")
    report["G3_round_trip"] = {
        "pass": parsed == corruption_inst["answer"] and garbage is None,
        "realistic_response_parsed": parsed == corruption_inst["answer"],
        "garbage_returns_none": garbage is None,
    }

    shipping = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])
    guess_rng = random.Random(0x10022456)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    empirical = guess_hits / guess_total
    exact_valid = shipping["orbit_order"]
    exact_density = exact_valid / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and empirical < 1e-6 and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_probability": empirical,
        "exact_probability": exact_density,
        "candidate_space": search_space(shipping),
        "valid_multipliers": exact_valid,
        "prior": "uniform over nonzero, non-self-inverse multipliers, with the required inverse field filled in exactly",
    }

    attack_names = list(_attack_candidates(shipping)) + ["uniform_random_restart_256"]
    attack_stats = {
        name: {"successes": 0, "attempts": 0} for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_elapsed = 0.0
    reference_instances = []
    for seed in range(8100, 8108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_candidates(inst).items():
            ok = verify(inst, candidate)[0]
            attack_stats[name]["successes"] += int(ok)
            attack_stats[name]["attempts"] += 1
        restart_rng = random.Random(seed ^ 0xA55A5AA5)
        restart_ok = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_ok = True
                break
        attack_stats["uniform_random_restart_256"]["successes"] += int(restart_ok)
        attack_stats["uniform_random_restart_256"]["attempts"] += 1

        start = time.perf_counter()
        found, operations = _reference_algorithm(inst)
        elapsed = time.perf_counter() - start
        solved = found is not None and verify(inst, found)[0]
        reference_successes += int(solved)
        reference_operations += operations
        reference_elapsed += elapsed
        reference_instances.append(
            {
                "seed": seed,
                "solved": solved,
                "operations": operations,
                "wall_clock_sec": round(elapsed, 6),
            }
        )
    reference = {
        "name": "fixed-orbit multiplier scan with exact q-cyclotomic expansion",
        "complexity": "O(t^2*m) modular multiplications and O(t) memory",
        "solves": f"{reference_successes}/8, as expected",
        "operations": reference_operations,
        "mean_operations": reference_operations / 8,
        "wall_clock_sec": round(reference_elapsed, 6),
        "mean_wall_clock_sec": round(reference_elapsed / 8, 6),
        "instances": reference_instances,
    }
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_successes == 8
        and demo_count == demo["orbit_order"]
        and exact_density < 1e-6,
        "shipping_sampled_solution_hits": guess_hits,
        "shipping_sampled_solution_total": guess_total,
        "shipping_sampled_solution_fraction": empirical,
        "shipping_exact_valid_solution_count": exact_valid,
        "shipping_exact_solution_fraction": exact_density,
        "strongest_attack_wall_sec": round(reference_elapsed, 6),
        "strongest_attack_operations": reference_operations,
        "strongest_attack_mean_operations": reference_operations / 8,
        "strongest_attack_solved_instances": reference_successes,
        "demo_bruteforce_valid_solution_count": demo_count,
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attack_stats.values()),
        "attacks": attack_stats,
        "reference_algorithm": reference,
    }

    doubled_params = dict(DIFFICULTY["hard"])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["p"] > shipping["p"]
        and len(doubled["answer"]) == len(shipping["answer"]),
        "base_requested_n": shipping["requested_n"],
        "base_code_length_p": shipping["p"],
        "doubled_requested_n": doubled["requested_n"],
        "doubled_code_length_p": doubled["p"],
        "base_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(doubled),
        "answer_residues_both": len(shipping["answer"]),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys: set[str] = set()
    g8_ok = True
    for offset in range(20):
        seed = 90_000 + offset
        inst = make_instance(seed=seed, **DIFFICULTY["hard"])
        key = canonical_key(inst)
        unrelated_keys.add(key)
        rng = random.Random(seed ^ 0xC0FFEE)
        scale = rng.randrange(1, inst["p"])
        reordered = _transformed_instance(inst, rng)
        scaled = _transformed_instance(inst, rng, scale=scale)
        swapped = _transformed_instance(inst, rng, swap=True)
        composed = _transformed_instance(inst, rng, scale=scale, swap=True)
        for variant in (reordered, scaled, swapped, composed):
            invariant_checks += 1
            g8_ok = g8_ok and canonical_key(variant) == key
            carried_checks += 1
            g8_ok = g8_ok and verify(variant, variant["answer"])[0]
    report["G8_canonical_key"] = {
        "pass": g8_ok and len(unrelated_keys) == 20,
        "invariance_checks": invariant_checks,
        "carried_certificate_checks": carried_checks,
        "unrelated_distinct_keys": len(unrelated_keys),
        "unrelated_instances": 20,
        "symmetries_tested": [
            "orbit-representative replacement and list reorder",
            "simultaneous coordinate multiplier",
            "swap the two codes while inverting the certificate",
            "composition of all transformations",
        ],
    }

    max_chars = 0
    max_elements = 0
    max_operations = 0
    compact_verified = 0
    for seed in range(8):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        encoded = json.dumps(inst["answer"], separators=(",", ":"))
        max_chars = max(max_chars, len(encoded))
        max_elements = max(max_elements, _atomic_elements(inst["answer"]))
        compact, operations = _compact_route(inst)
        max_operations = max(max_operations, operations)
        compact_verified += int(verify(inst, compact)[0])
    bare = _G9_ARMS["bare"]
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": max_chars <= 2_000 and max_elements <= 256 and max_operations <= 300,
        "arms": {"bare": bare, "hinted": hinted, "placebo": placebo},
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": "unmeasured" if not hinted["attempts"] else ("too_easy" if hinted["solved"] else "hardened"),
        "answer_chars": max_chars,
        "answer_tokens": (max_chars + 3) // 4,
        "answer_elements": max_elements,
        "intended_route_operations": max_operations,
        "compact_route_verified": f"{compact_verified}/8",
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
