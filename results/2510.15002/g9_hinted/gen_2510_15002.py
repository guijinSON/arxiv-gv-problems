"""Dense XOR-translation certificates for Binnendyk logic engines.

The generated object is the logic engine used in Sections 1.4 and 4 of
arXiv:2510.15002v2. A dense parity system expands deterministically to NAE-3
flag rows. The answer is a sparse algebraic-normal-form polynomial whose truth
table orients every primary armature.

Generation is inverse: sample that polynomial first, then compose it with an
odd translation convolution. The odd convolution is an involution, so the
certificate is unique, but mechanically applying it is deliberately dense.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import time
from functools import lru_cache
from typing import Any


TRACK = "B"

_REDUCTION = (
    "Sections 1.4 and 4: arbitrary NAE-3SAT clauses are represented by "
    "logic-engine flag rows, and a satisfying assignment is equivalent to a "
    "flat armature/flag configuration"
)

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "logic-engine armatures",
        "NAE-3 flag-incidence rows",
        "Boolean polynomial in algebraic normal form",
    ],
    "verification_operations": [
        "exact Boolean polynomial evaluation",
        "bitwise XOR translation",
        "logic-engine parity-row substitution",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A dense odd XOR-translation changes only the affine part of a "
        "quadratic Boolean function; without that invariant, one must apply "
        "the full dense involution and transform its entire truth table."
    ),
    "hardness_basis": (
        "Track B: a full Boolean Moebius transform followed by symbolic "
        "translation costs O(n*log n+k^2), measured at 11,479 Boolean "
        "operations and 0.001474 s at the hard preset (n=2048, k=11); the "
        "quadratic-moment route costs 215 Boolean operations."
    ),
    "max_answer_tokens": 54,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "hard": {"n": 2048, "weight": 1023},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "An odd XOR-translation preserves the quadratic part of algebraic normal form."
)
PLACEBO_HINT = (
    "A careful exact calculation keeps the indexing and Boolean notation consistent."
)

_MAX_TERMS = 96
_MAX_N = 8192

CERTIFICATE_LANGUAGE = {
    "description": (
        "A nonempty canonical list of at most 96 distinct squarefree ANF "
        "monomials in k=log2(n) Boolean variables; a monomial is the strictly "
        "increasing JSON list of its variable indices, [] is the constant 1, "
        "and the outer list is ordered by the monomial's binary mask."
    ),
    "bounds": {
        "max_terms": _MAX_TERMS,
        "max_degree": "k=log2(n)",
        "coefficient_field": "GF(2)",
        "monomial_count": "n",
        "absolute_supported_n": _MAX_N,
    },
}

NOTES = r"""
Step 0. Version 2, Section 1 defines a realization as an injective map to Z^2
whose listed edges have Euclidean length one; nonedges need not have nonunit
length. Section 1.4 gives the executable logic-engine criterion: every upper
and lower row must have an unflagged link. Sections 3--4 turn arbitrary NAE-3
rows into a square-lattice unit-distance graph and prove realizability iff the
source formula is satisfiable. Version 3 is only a withdrawal notice: a
stronger 1987 result was already known.

The theorem is worst-case NP-completeness and supplies no hardness claim for
randomly planted coordinate drawings, so the prior Track-A triage was not
used. This is Track B and paper-licensed rather than native geometry: the
solver sees the paper's logic engine, not every vertex of the much larger
frame/shaft/square-chain lattice graph.

Certificate production is inverse. Index armatures by F_2^k, sample a
non-affine quadratic ANF q, and sample an odd set S of translation masks. The
displayed table is r(i)=XOR_{s in S} q(i XOR s). In characteristic two the
convolution A=sum_{s in S} T_s satisfies A^2=|S|I=I: cross terms cancel and
every translation squares to I. Hence the certificate is unique and known
without solving the emitted instance.

Each dense parity row is converted to NAE-3 using accumulator armatures. Add a
fixed reference Z=0. For each wrong-parity triple t, the NAE-4 clause on
(A XOR t0,B XOR t1,C XOR t2,Z) forbids exactly that triple. Each
NAE-4(l0,l1,l2,l3) expands to NAE(l0,l1,y) and NAE(not y,l2,l3). The checker
evaluates the ANF, all accumulator parities, and final right sides exactly.

The strongest mechanical route runs the full Boolean Moebius transform on r
and then translates the recovered polynomial symbolically: 11,264 transform
XORs plus 215 symbolic Boolean operations at shipping. Directly applying the
dense involution is a slower 2,104,320-XOR alternative. The compact route
notices that odd translation keeps the quadratic ANF part. Values of r at 0,
basis vectors, and pairwise basis sums recover that part; displayed first- and
second-moment checksums recover the affine correction in 215 operations.

The original draft incorrectly used I+T_a+T_b and reported Gaussian
elimination as the baseline. That operator is itself an involution, giving a
direct 2n-XOR attack. This version reports its dense analogue as the successful
reference algorithm instead of hiding it.

Every armature occurs in exactly |S| positions. Generation rejects rare cases
in which copying the right-side ANF, using an affine-only fit, or ignoring the
moment correction happens to be right. Those attacks and 256 uniform restarts
are tested on eight seeds.

Canonicalization uses the absolute Walsh-spectrum multiset of S. It is
invariant under invertible basis changes, translations of S, row-index
translations, shift ordering, and quadratic Boolean gauge changes. It is a
strong cheap invariant, not a complete affine-equivalence canonizer.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP_N = 12

# Filled only from script-owned runs. Provider failures are not model failures.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_openrouter_key_limit",
}


def _int_param(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def _parity(value: int) -> int:
    return value.bit_count() & 1


def _pairs(k: int) -> list[tuple[int, int]]:
    return [(i, j) for i in range(k) for j in range(i + 1, k)]


def _moments(shifts: list[int], k: int) -> tuple[int, int]:
    first = 0
    for shift in shifts:
        first ^= shift
    second = 0
    for pair_index, (left, right) in enumerate(_pairs(k)):
        bit = 0
        for shift in shifts:
            bit ^= ((shift >> left) & 1) & ((shift >> right) & 1)
        second |= bit << pair_index
    return first, second


def _quadratic_value(index: int, constant: int, linear: int,
                     quadratic: int, k: int) -> int:
    value = constant ^ _parity(index & linear)
    for pair_index, (left, right) in enumerate(_pairs(k)):
        if (quadratic >> pair_index) & 1:
            value ^= ((index >> left) & 1) & ((index >> right) & 1)
    return value


def _quadratic_table(n: int, constant: int, linear: int,
                     quadratic: int) -> list[int]:
    k = n.bit_length() - 1
    return [
        _quadratic_value(index, constant, linear, quadratic, k)
        for index in range(n)
    ]


def _translated_quadratic(constant: int, linear: int, quadratic: int,
                          first: int, second: int, k: int
                          ) -> tuple[int, int, int]:
    neighbors = [0] * k
    for pair_index, (left, right) in enumerate(_pairs(k)):
        if (quadratic >> pair_index) & 1:
            neighbors[left] |= 1 << right
            neighbors[right] |= 1 << left
    translated_linear = linear
    for bit in range(k):
        translated_linear ^= _parity(neighbors[bit] & first) << bit
    translated_constant = (
        constant ^ _parity(linear & first) ^ _parity(quadratic & second)
    )
    return translated_constant, translated_linear, quadratic


def _coefficients_to_masks(constant: int, linear: int,
                           quadratic: int, k: int) -> list[int]:
    masks = []
    if constant:
        masks.append(0)
    masks.extend(1 << bit for bit in range(k) if (linear >> bit) & 1)
    for pair_index, (left, right) in enumerate(_pairs(k)):
        if (quadratic >> pair_index) & 1:
            masks.append((1 << left) | (1 << right))
    return sorted(masks)


def _masks_to_answer(masks: list[int], k: int) -> list[list[int]]:
    return [
        [bit for bit in range(k) if (mask >> bit) & 1]
        for mask in sorted(masks)
    ]


def _answer_to_masks(inst: dict, answer: object
                     ) -> tuple[list[int] | None, str | None]:
    if not isinstance(answer, list):
        return None, "certificate must be a JSON list of monomials"
    if not answer:
        return None, "empty polynomial certificate"
    max_terms = int(inst["max_terms"])
    if len(answer) > max_terms:
        return None, f"too many monomials: maximum is {max_terms}"
    k = int(inst["dimension"])
    masks = []
    for term_index, term in enumerate(answer):
        if not isinstance(term, list):
            return None, f"monomial {term_index} is not a JSON list"
        previous = -1
        mask = 0
        for exponent in term:
            if type(exponent) is not int:
                return None, f"monomial {term_index} has a noninteger variable"
            if not 0 <= exponent < k:
                return None, f"variable {exponent} is outside 0..{k - 1}"
            if exponent <= previous:
                return None, f"monomial {term_index} is not strictly increasing"
            previous = exponent
            mask |= 1 << exponent
        if mask in masks:
            return None, f"duplicate monomial at position {term_index}"
        masks.append(mask)
    if masks != sorted(masks):
        return None, "monomials are not in canonical binary-mask order"
    return masks, None


def _truth_from_masks(masks: list[int], n: int) -> list[int]:
    values = [0] * n
    for mask in masks:
        values[mask] = 1
    k = n.bit_length() - 1
    for bit in range(k):
        flag = 1 << bit
        for mask in range(n):
            if mask & flag:
                values[mask] ^= values[mask ^ flag]
    return values


def _masks_from_truth(values: list[int]) -> list[int]:
    coefficients = list(values)
    n = len(coefficients)
    k = n.bit_length() - 1
    for bit in range(k):
        flag = 1 << bit
        for mask in range(n):
            if mask & flag:
                coefficients[mask] ^= coefficients[mask ^ flag]
    return [mask for mask, value in enumerate(coefficients) if value]


def _quadratic_coefficients_from_masks(masks: list[int], k: int
                                       ) -> tuple[int, int, int]:
    constant = int(0 in masks)
    linear = 0
    quadratic = 0
    pair_to_index = {pair: index for index, pair in enumerate(_pairs(k))}
    for mask in masks:
        degree = mask.bit_count()
        if degree == 1:
            linear |= mask
        elif degree == 2:
            bits = tuple(bit for bit in range(k) if (mask >> bit) & 1)
            quadratic |= 1 << pair_to_index[bits]
        elif degree > 2:
            raise ValueError("polynomial is not quadratic")
    return constant, linear, quadratic


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a quadratic armature function and dense parity rows."""
    n = _int_param("n", n, 8, _MAX_N)
    if not _is_power_of_two(n):
        raise ValueError("n must be a power of two")
    weight = _int_param(
        "weight", params.pop("weight", n // 2 - 1), 3, n - 1
    )
    if weight % 2 != 1:
        raise ValueError("weight must be odd")
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))

    rng = random.Random(seed)
    k = n.bit_length() - 1
    pair_count = max(1, len(_pairs(k)) // 2)
    max_terms = min(_MAX_TERMS, n)
    for _ in range(200):
        chosen_pairs = rng.sample(range(len(_pairs(k))), pair_count)
        quadratic = sum(1 << index for index in chosen_pairs)
        linear = rng.randrange(1 << k)
        constant = rng.getrandbits(1)
        answer_masks = _coefficients_to_masks(constant, linear, quadratic, k)
        if not answer_masks or len(answer_masks) > max_terms:
            continue
        shifts = rng.sample(range(n), weight)
        first, second = _moments(shifts, k)
        r_constant, r_linear, r_quadratic = _translated_quadratic(
            constant, linear, quadratic, first, second, k
        )
        rhs_masks = _coefficients_to_masks(
            r_constant, r_linear, r_quadratic, k
        )
        affine_masks = _coefficients_to_masks(r_constant, r_linear, 0, k)
        moment_blind_masks = _coefficients_to_masks(
            r_constant, linear, quadratic, k
        )
        if answer_masks in (rhs_masks, affine_masks, moment_blind_masks):
            continue
        rhs = "".join(
            str(bit) for bit in _quadratic_table(
                n, r_constant, r_linear, r_quadratic
            )
        )
        rng.shuffle(shifts)
        return {
            "family": "dense_translation_logic_engine_v2",
            "n": n,
            "dimension": k,
            "weight": weight,
            "shifts": shifts,
            "rhs": rhs,
            "first_moment": first,
            "second_moment": format(second, f"0{len(_pairs(k))}b")[::-1],
            "max_terms": max_terms,
            "parity_equations": n,
            "accumulator_steps": n * (weight - 1),
            "nae3_row_count": 8 * n * (weight - 1) + n,
            "answer": _masks_to_answer(answer_masks, k),
        }
    raise RuntimeError("could not draw a nondegenerate generated instance")


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Expand any admitted ANF and recompute every dense parity row exactly."""
    masks, error = _answer_to_masks(inst, answer)
    if error is not None or masks is None:
        return False, str(error)
    n = int(inst["n"])
    values = _truth_from_masks(masks, n)
    for row in range(n):
        accumulator = 0
        for shift in inst["shifts"]:
            accumulator ^= values[row ^ shift]
        if accumulator != int(inst["rhs"][row]):
            return False, f"dense parity row {row} is violated"
    return True, "ok"


def _format_answer(answer: list[list[int]]) -> str:
    return json.dumps(answer, separators=(",", ":"))


def _wrapped_values(values: list[int], width: int = 16) -> list[str]:
    return [
        "  " + " ".join(str(value) for value in values[start:start + width])
        for start in range(0, len(values), width)
    ]


def render(inst: dict) -> str:
    """Render a self-contained compressed flat-logic-engine problem."""
    n = inst["n"]
    k = inst["dimension"]
    pair_names = ", ".join(f"({a},{b})" for a, b in _pairs(k))
    lines = [
        "DENSE FLAT LOGIC-ENGINE ORIENTATION (exact Boolean instance)",
        "",
        f"There are n={n}=2^{k} primary armatures X_0,...,X_{n - 1}.",
        "Write each index as a k-bit vector; XOR below is bitwise exclusive-or.",
        "Orientation 1 means the unprimed chain points up; 0 means it points down.",
        "",
        f"The shift list S has w={inst['weight']} distinct entries. For every",
        "row index i=0,...,n-1 the required relation is",
        "",
        "  XOR over s in S of X_(i XOR s) = R[i].",
        "",
        "This is a finite logic engine, not a probabilistic condition. Process S",
        "in displayed order, introducing an accumulator after each later X value.",
        "Enforce each update A XOR B XOR C=0 (C is the new accumulator) as follows.",
        "Add a reference armature Z fixed to 0. For each of the four bit triples",
        "t=(t0,t1,t2) with t0 XOR t1 XOR t2=1, include the NAE-4 clause",
        "NAE(A XOR t0,B XOR t1,C XOR t2,Z); it forbids exactly that wrong triple.",
        "NAE means its literals are not all equal. Expand each NAE-4(l0,l1,l2,l3)",
        "as NAE(l0,l1,y) and NAE(not y,l2,l3), with a fresh auxiliary y. The final",
        "accumulator equals R[i]. All auxiliaries are fixed by the primary X values,",
        "so the requested polynomial is a compact complete orientation. The checker",
        "evaluates it and recomputes every accumulator parity exactly.",
        "",
        "Represent orientations by a Boolean polynomial q in algebraic normal form",
        "(ANF): XOR of distinct squarefree monomials in Boolean variables",
        f"u_0,...,u_{k - 1}, evaluated on i's k bits (least-significant is u_0).",
        f"At most {inst['max_terms']} nonzero monomials are allowed. Write a monomial",
        "as its strictly increasing JSON list of variable indices; [] is constant 1.",
        "Sort the outer list by each monomial's binary mask sum(2^j). Coefficients",
        "are 1 in GF(2), so terms may not repeat. Example [[],[0],[1,3]] means",
        "q=1 XOR u_0 XOR (u_1*u_3).",
        "",
        "SHIFT LIST S (order matters only for named accumulators):",
    ]
    lines.extend(_wrapped_values(inst["shifts"]))
    lines.extend(["END SHIFT LIST", "", "RIGHT-SIDE TABLE R (half-open offsets):"])
    rhs = inst["rhs"]
    for start in range(0, n, 128):
        lines.append(f"  R[{start}:{min(n, start + 128)}] = {rhs[start:start + 128]}")
    lines.extend([
        "END RIGHT-SIDE TABLE",
        "",
        "Exact checksums of S, included as instance data:",
        f"  T = XOR of all masks in S = {inst['first_moment']}",
        "  Pair order = " + pair_names,
        "  U = " + inst["second_moment"],
        "U has one bit in that pair order; its (a,b) bit is the parity of the",
        "number of s in S whose bits a and b are both 1.",
        "",
        "Return one nonempty canonical JSON list of monomials. The stated order is",
        "mandatory, and repeated terms are forbidden.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as that JSON list.",
        "Example: <answer>[[],[0],[1,3]]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse a tagged ANF list, tolerating surrounding prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json|text|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        parsed = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, list):
        return None
    if not all(
        isinstance(term, list) and all(type(index) is int for index in term)
        for term in parsed
    ):
        return None
    return parsed


@lru_cache(maxsize=None)
def _language_counts(monomials: int, limit: int) -> tuple[int, ...]:
    return tuple(math.comb(monomials, size) for size in range(1, limit + 1))


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the bounded, canonical nonempty sparse-ANF language."""
    monomials = int(inst["n"])
    limit = min(int(inst["max_terms"]), monomials)
    counts = _language_counts(monomials, limit)
    ticket = rng.randrange(sum(counts))
    size = 1
    for count in counts:
        if ticket < count:
            break
        ticket -= count
        size += 1
    masks = sorted(rng.sample(range(monomials), size))
    return _masks_to_answer(masks, int(inst["dimension"]))


def search_space(inst: dict) -> int | None:
    monomials = int(inst["n"])
    limit = min(int(inst["max_terms"]), monomials)
    return sum(_language_counts(monomials, limit))


def enumerate_all(inst: dict) -> int | None:
    """Count valid bounded certificates exactly only at hand scale."""
    n = int(inst["n"])
    if n > _ENUMERATION_CAP_N or int(inst["max_terms"]) < n:
        return None
    count = 0
    for support in range(1, 1 << n):
        masks = [mask for mask in range(n) if (support >> mask) & 1]
        if verify(inst, _masks_to_answer(masks, inst["dimension"]))[0]:
            count += 1
    return count


def _walsh_absolute_spectrum(n: int, shifts: list[int]) -> list[int]:
    spectrum = [0] * n
    for shift in shifts:
        spectrum[shift] = 1
    step = 1
    while step < n:
        for start in range(0, n, 2 * step):
            for offset in range(step):
                left = spectrum[start + offset]
                right = spectrum[start + offset + step]
                spectrum[start + offset] = left + right
                spectrum[start + offset + step] = left - right
        step *= 2
    return sorted(abs(value) for value in spectrum)


def canonical_key(inst: dict) -> str:
    """A strong affine-invariant signature of the translation operator."""
    payload = {
        "n": int(inst["n"]),
        "weight": len(inst["shifts"]),
        "absolute_walsh_spectrum": _walsh_absolute_spectrum(
            int(inst["n"]), list(inst["shifts"])
        ),
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("ascii")
    ).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the dense truth-table haystack while the ANF witness stays short."""
    out = {key: value for key, value in params.items() if key != "_preset"}
    n = int(out["n"])
    if n >= _MAX_N:
        return "cap_bound"
    harder_n = 2 * n
    out["n"] = harder_n
    out["weight"] = harder_n // 2 - 1
    return out


def _reference_algorithm(inst: dict) -> tuple[object | None, dict[str, int]]:
    """Run the full Boolean Moebius transform, then translate symbolically."""
    n = int(inst["n"])
    rhs = [int(bit) for bit in inst["rhs"]]
    rhs_masks = _masks_from_truth(rhs)
    try:
        rhs_coeffs = _quadratic_coefficients_from_masks(
            rhs_masks, int(inst["dimension"])
        )
    except ValueError:
        return None, {
            "moebius_xors": n * int(inst["dimension"]) // 2,
            "symbolic_boolean_operations": 0,
            "scalar_operations": n * int(inst["dimension"]) // 2,
            "dense_involution_alternative_xors": n * (len(inst["shifts"]) - 1),
        }
    first = int(inst["first_moment"])
    second = int(inst["second_moment"][::-1], 2)
    answer_coeffs = _translated_quadratic(
        *rhs_coeffs, first, second, int(inst["dimension"])
    )
    masks = _coefficients_to_masks(*answer_coeffs, int(inst["dimension"]))
    symbolic_operations = 3 * len(_pairs(int(inst["dimension"]))) + 4 * int(inst["dimension"]) + 6
    operations = {
        "moebius_xors": n * int(inst["dimension"]) // 2,
        "symbolic_boolean_operations": symbolic_operations,
        "dense_involution_alternative_xors": n * (len(inst["shifts"]) - 1),
    }
    operations["scalar_operations"] = (
        operations["moebius_xors"] + operations["symbolic_boolean_operations"]
    )
    if not masks or len(masks) > int(inst["max_terms"]):
        return None, operations
    return _masks_to_answer(masks, inst["dimension"]), operations


def _compact_algorithm(inst: dict) -> tuple[list[list[int]], int]:
    """Recover a quadratic ANF through its translation-invariant top part."""
    k = int(inst["dimension"])
    rhs = inst["rhs"]
    r_constant = int(rhs[0])
    r_linear = 0
    for bit in range(k):
        r_linear |= (int(rhs[1 << bit]) ^ r_constant) << bit
    quadratic = 0
    for pair_index, (left, right) in enumerate(_pairs(k)):
        coefficient = (
            int(rhs[(1 << left) | (1 << right)])
            ^ int(rhs[1 << left])
            ^ int(rhs[1 << right])
            ^ r_constant
        )
        quadratic |= coefficient << pair_index
    first = int(inst["first_moment"])
    second = int(inst["second_moment"][::-1], 2)
    neighbors = [0] * k
    for pair_index, (left, right) in enumerate(_pairs(k)):
        if (quadratic >> pair_index) & 1:
            neighbors[left] |= 1 << right
            neighbors[right] |= 1 << left
    linear = r_linear
    for bit in range(k):
        linear ^= _parity(neighbors[bit] & first) << bit
    constant = (
        r_constant ^ _parity(linear & first) ^ _parity(quadratic & second)
    )
    masks = _coefficients_to_masks(constant, linear, quadratic, k)
    operations = 3 * len(_pairs(k)) + 4 * k + 6
    return _masks_to_answer(masks, k), operations


def _rhs_anf_attack(inst: dict) -> list[list[int]]:
    return _masks_to_answer(
        _masks_from_truth([int(bit) for bit in inst["rhs"]]), inst["dimension"]
    )


def _affine_only_attack(inst: dict) -> list[list[int]]:
    masks = [
        mask for mask in _masks_from_truth([int(bit) for bit in inst["rhs"]])
        if mask.bit_count() <= 1
    ]
    return _masks_to_answer(masks or [0], inst["dimension"])


def _moment_blind_attack(inst: dict) -> list[list[int]]:
    compact, _ = _compact_algorithm(inst)
    masks, _ = _answer_to_masks(inst, compact)
    assert masks is not None
    masks = [mask for mask in masks if mask != 0]
    if int(inst["rhs"][0]):
        masks.append(0)
    return _masks_to_answer(sorted(masks) or [0], inst["dimension"])


def _outlier_occurrence_attack(inst: dict) -> list[list[int]]:
    # Translation makes every primary armature occur exactly |S| times.
    return [[]]


def _random_restart_succeeds(inst: dict, planted: list[list[int]], seed: int,
                             restarts: int = 256) -> bool:
    rng = random.Random(seed)
    # Uniqueness from A^2=I makes equality an exact fast validity test.
    return any(random_candidate(inst, rng) == planted for _ in range(restarts))


def _linear_map_table(k: int, rng: random.Random) -> list[int]:
    operations = []
    for _ in range(5 * k):
        left, right = rng.sample(range(k), 2)
        operations.append((rng.getrandbits(1), left, right))
    table = []
    for value in range(1 << k):
        mapped = value
        for kind, left, right in operations:
            left_bit = (mapped >> left) & 1
            right_bit = (mapped >> right) & 1
            if kind == 0:
                if left_bit != right_bit:
                    mapped ^= (1 << left) | (1 << right)
            elif right_bit:
                mapped ^= 1 << left
        table.append(mapped)
    return table


def _transform_for_g8(inst: dict, answer: list[list[int]], seed: int
                      ) -> tuple[dict, list[list[int]]]:
    """Compose affine relabeling, support translation, gauge, and reordering."""
    rng = random.Random(seed)
    n = int(inst["n"])
    k = int(inst["dimension"])
    linear_map = _linear_map_table(k, rng)
    index_translation = rng.randrange(n)
    support_translation = rng.randrange(n)
    answer_masks, error = _answer_to_masks(inst, answer)
    assert error is None and answer_masks is not None
    old_values = _truth_from_masks(answer_masks, n)
    gauge_quadratic = 0
    for pair_index in rng.sample(range(len(_pairs(k))), min(3, len(_pairs(k)))):
        gauge_quadratic |= 1 << pair_index
    gauge_values = _quadratic_table(
        n, rng.getrandbits(1), rng.randrange(1 << k), gauge_quadratic
    )
    new_values = [0] * n
    for old_index in range(n):
        new_index = linear_map[old_index] ^ index_translation
        new_values[new_index] = old_values[old_index] ^ gauge_values[old_index]
    new_masks = _masks_from_truth(new_values)
    assert 0 < len(new_masks) <= int(inst["max_terms"])
    new_coeffs = _quadratic_coefficients_from_masks(new_masks, k)
    new_shifts = [
        linear_map[shift] ^ support_translation for shift in inst["shifts"]
    ]
    first, second = _moments(new_shifts, k)
    r_coeffs = _translated_quadratic(*new_coeffs, first, second, k)
    rhs = "".join(str(bit) for bit in _quadratic_table(n, *r_coeffs))
    rng.shuffle(new_shifts)
    transformed = {
        "family": inst["family"],
        "n": n,
        "dimension": k,
        "weight": len(new_shifts),
        "shifts": new_shifts,
        "rhs": rhs,
        "first_moment": first,
        "second_moment": format(second, f"0{len(_pairs(k))}b")[::-1],
        "max_terms": inst["max_terms"],
        "parity_equations": n,
        "accumulator_steps": n * (len(new_shifts) - 1),
        "nae3_row_count": 8 * n * (len(new_shifts) - 1) + n,
        "answer": _masks_to_answer(new_masks, k),
    }
    return transformed, transformed["answer"]


def _answer_atoms(answer: list[list[int]]) -> int:
    return len(answer) + sum(len(term) for term in answer)


def selftest() -> dict:
    """Run gates G1--G9 and return a JSON-native measured report."""
    report: dict[str, Any] = {
        "paper": "2510.15002",
        "paper_version_read": "v2 (v3 is withdrawn)",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }
    verified = json_roundtrips = attempts = 0
    for params in DIFFICULTY.values():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            verified += int(verify(inst, inst["answer"])[0])
            json_roundtrips += int(
                json.loads(json.dumps(inst["answer"])) == inst["answer"]
            )
    report["G1_planted_verifies"] = {
        "pass": verified == attempts and json_roundtrips == attempts,
        "verified": verified,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=20260905, **shipping_params)
    planted = ship["answer"]
    corruptions: list[tuple[str, object]] = [("empty", [])]
    corruptions.append(("drop", planted[:-1]))
    swapped = copy.deepcopy(planted)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions.append(("swap", swapped))
    duplicate = copy.deepcopy(planted)
    duplicate.insert(1, copy.deepcopy(duplicate[0]))
    corruptions.append(("duplicate", duplicate))
    out_of_range = copy.deepcopy(planted)
    out_of_range[-1] = [ship["dimension"]]
    corruptions.append(("out_of_range", out_of_range))
    cases = {}
    for name, candidate in corruptions:
        ok, reason = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({entry["reason"] for entry in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values())
        and distinct_reasons == len(cases),
        "rejected": sum(entry["rejected"] for entry in cases.values()),
        "attempts": len(cases),
        "distinct_reasons": distinct_reasons,
        "cases": cases,
    }

    body = _format_answer(planted)
    replies = [
        f"I used the invariant.\n<answer>{body}</answer>\nDone.",
        f"Result:\n<answer>```json\n{body}\n```</answer>",
        f"prose before <answer> {body} </answer> prose after",
    ]
    parsed = sum(parse_answer(reply) == planted for reply in replies)
    garbage_rejected = parse_answer("there is no tagged polynomial") is None
    report["G3_round_trip"] = {
        "pass": parsed == len(replies) and garbage_rejected,
        "parsed": parsed,
        "attempts": len(replies),
        "garbage_rejected": garbage_rejected,
    }

    guess_rng = random.Random(0x251015002)
    hits = 0
    started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        hits += int(random_candidate(ship, guess_rng) == planted)
    sampling_seconds = time.perf_counter() - started
    observed = hits / _G4_SAMPLES
    space = search_space(ship)
    assert space is not None
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6 and _G4_SAMPLES >= 200_000,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": observed,
        "exact_probability": 1 / space,
        "search_space": space,
        "sampling_seconds": round(sampling_seconds, 6),
        "prior": "uniform over canonical nonempty ANFs with at most 96 terms",
        "validity_test": "equality to the unique involution-backed certificate",
    }

    ref_started = time.perf_counter()
    reference_answer, reference_metrics = _reference_algorithm(ship)
    reference_seconds = time.perf_counter() - ref_started
    reference_ok = reference_answer is not None and verify(ship, reference_answer)[0]
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and demo_count == 1,
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_density_estimate": observed,
        "shipping_exact_solution_count": None,
        "theorem_backed_shipping_solution_count": 1,
        "demo_exact_solution_count": demo_count,
        "demo_n": demo["n"],
        "baseline_wall_seconds": round(reference_seconds, 6),
        "baseline_moebius_xors": reference_metrics["moebius_xors"],
        "baseline_symbolic_boolean_operations": reference_metrics["symbolic_boolean_operations"],
        "baseline_scalar_operations": reference_metrics["scalar_operations"],
        "dense_involution_alternative_xors": reference_metrics["dense_involution_alternative_xors"],
        "baseline_solved": reference_ok,
    }

    attack_names = [
        "outlier_occurrence_frequency",
        "greedy_copy_rhs_anf",
        "random_restart_256",
        "affine_only_ansatz",
        "ignore_moment_correction",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": _ATTACK_SEEDS}
        for name in attack_names
    }
    ref_successes = compact_successes = 0
    ref_total_wall = 0.0
    ref_total_operations = 0
    compact_operations = []
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=90_000 + seed, **shipping_params)
        candidates = {
            "outlier_occurrence_frequency": _outlier_occurrence_attack(inst),
            "greedy_copy_rhs_anf": _rhs_anf_attack(inst),
            "affine_only_ansatz": _affine_only_attack(inst),
            "ignore_moment_correction": _moment_blind_attack(inst),
        }
        for name, candidate in candidates.items():
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
        attack_results["random_restart_256"]["successes"] += int(
            _random_restart_succeeds(inst, inst["answer"], 700_000 + seed)
        )
        t0 = time.perf_counter()
        candidate, metrics = _reference_algorithm(inst)
        ref_total_wall += time.perf_counter() - t0
        ref_total_operations += metrics["scalar_operations"]
        ref_successes += int(candidate is not None and verify(inst, candidate)[0])
        compact, operations = _compact_algorithm(inst)
        compact_successes += int(verify(inst, compact)[0])
        compact_operations.append(operations)
    all_attacks_failed = all(
        result["successes"] == 0 for result in attack_results.values()
    )
    reference = {
        "name": "full Boolean Moebius transform plus symbolic translation",
        "complexity": "O(n*log n+k^2) Boolean operations",
        "wall_clock_sec": round(ref_total_wall / _ATTACK_SEEDS, 6),
        "operations": ref_total_operations // _ATTACK_SEEDS,
        "solves": f"{ref_successes}/{_ATTACK_SEEDS}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed
        and ref_successes == _ATTACK_SEEDS
        and compact_successes == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "quadratic ANF plus first/second translation moments",
            "successes": compact_successes,
            "attempts": _ATTACK_SEEDS,
            "max_operations": max(compact_operations),
        },
    }

    doubled_params = {
        "n": 2 * int(shipping_params["n"]),
        "weight": int(shipping_params["n"]) - 1,
    }
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    escalated_params = escalate(shipping_params)
    escalated_ok = False
    if isinstance(escalated_params, dict):
        escalated = make_instance(seed=271828, **escalated_params)
        escalated_ok = verify(escalated, escalated["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "shipping_n": ship["n"],
        "shipping_reference_operations": reference_metrics["scalar_operations"],
        "doubled_n": doubled["n"],
        "doubled_reference_operations": (
            doubled["n"] * doubled["dimension"] // 2
            + 3 * len(_pairs(doubled["dimension"]))
            + 4 * doubled["dimension"] + 6
        ),
        "doubled_verified": doubled_ok,
        "escalated_params": escalated_params,
        "escalated_verified": escalated_ok,
    }

    invariant = carried = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=400_000 + seed, **shipping_params)
        key = canonical_key(inst)
        transformed, transformed_answer = _transform_for_g8(
            inst, inst["answer"], 500_000 + seed
        )
        invariant += int(canonical_key(transformed) == key)
        carried += int(verify(transformed, transformed_answer)[0])
        keys.append(key)
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and distinct == 20,
        "invariance_passed": invariant,
        "invariance_attempts": 20,
        "carried_witnesses_verified": carried,
        "carried_witness_attempts": 20,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "invertible change of F_2 basis",
            "global armature-index translation",
            "translation of shift set with corresponding row translation",
            "quadratic Boolean gauge change",
            "shift reordering",
            "all transformations composed",
        ],
    }

    answer_blob = _format_answer(ship["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(ship["answer"])
    compact_answer, intended_operations = _compact_algorithm(ship)
    compact_ok = verify(ship, compact_answer)[0]
    arms = {
        name: dict(_ORACLE_EVIDENCE[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verified": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "diagnostic_gated": False,
    }
    gate_values = [
        value for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
