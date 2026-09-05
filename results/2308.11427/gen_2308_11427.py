"""Verified generator for arXiv:2308.11427.

The family asks for the PBW normal form of a factored noncommutative
polynomial in the canonical permutation-idempotent Yang--Baxter algebra.
Generation composes coefficient-sum certificates; it never solves a generated
instance.  All arithmetic is exact in the displayed prime field.
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
except ImportError:  # This family only needs exact modular integer arithmetic.
    exact_matrices = rationals = None


TRACK = "B"

STRUCTURAL_HINT = (
    "Within each summand, the dense coefficient rows are balanced on the "
    "two-cycles of the displayed permutation f."
)
PLACEBO_HINT = (
    "Within each summand, careful attention to the displayed coefficient rows "
    "helps prevent ordinary modular arithmetic errors."
)


PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "permutation idempotent Yang-Baxter map r_f",
        "permutation-idempotent Yang-Baxter algebra over GF(p)",
        "factored noncommutative polynomial",
        "PBW normal-form polynomial",
    ],
    "verification_operations": [
        "exact finite-field coefficient addition",
        "exact finite-field coefficient multiplication",
        "PBW normal-form coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Theorem 3.4 makes every nonfinal factor act only through its coefficient "
        "sum, while the displayed permutation pairs independently sampled "
        "coefficients to a common total; without noticing the pairing, rows must be scanned."
    ),
    "hardness_basis": (
        "Track B: the Theorem 3.4/Corollary 3.6 PBW normal-form scan is "
        "O(branches*factors*n), with a measured shipping cost of 36,771 exact "
        "GF(1009) operations and roughly 0.002 seconds mean per instance, whereas balancing on "
        "the two-cycles of f reduces the intended route to 51 operations."
    ),
    "max_answer_tokens": 17,
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
    "demo": {"n": 8, "factors": 4, "modulus": 11},
    "easy": {"n": 24, "factors": 16, "modulus": 101},
    "medium": {"n": 64, "factors": 48, "modulus": 503},
    "hard": {"n": 128, "factors": 96, "modulus": 1009},
}
SHIPPING_DIFFICULTY = "hard"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A sparse PBW polynomial as a JSON list [[coefficient,generator],...], "
        "with six nonzero GF(p) coefficients in increasing 0-based generator "
        "order.  On each of the three printed two-generator terminal supports, "
        "the coefficient pair is one common nonzero (degree-1)-st-power scalar "
        "multiple of that terminal pair."
    ),
    "bounds": {
        "branches": 3,
        "terms": 6,
        "coefficient_min": 1,
        "coefficient_max_shipping": 1008,
        "generator_index_min": 0,
        "generator_index_max_shipping": 127,
    },
}


NOTES = """\
Section 2.2 defines the Yang--Baxter algebra from a finite quadratic set.
Proposition 3.1 fixes the exact permutation-idempotent definition
r_f(x,y)=(f(y),y) and also shows why the prior-triage task of recovering or
checking r_f is too easy: f is simply one row of r_f.  Theorem 3.4 gives the
reduced Groebner basis x_i x_j - x_1 x_j, and Corollary 3.6 says every word
y_1...y_(d-1)x_j has normal form x_1^(d-1)x_j.  The module uses 0-based
labels and randomly relabels the distinguished generator called x_1 in the
paper.  These two results license the native normal-form task here.

Certificate construction is a composition of identities.  For each summand,
the generator samples a field center c and a random fixed-point-free involution
f.  On every 2-cycle (i,f(i)), each dense row samples its first coefficient
uniformly and sets the other to 2c minus it.  Thus every independently sampled
row has certified sum n*c.  The planted normal-form scalar is the known sum to
the (factors-1)-st power, multiplied into a disjoint two-term terminal factor.
No generated instance is searched.

What makes it easy, and why this is Track B: Theorem 3.4 makes an ordinary
normal-form algorithm linear in all displayed coefficients.  The family is
not Track A.  At the hard preset that reference algorithm performs 36,771 exact
field operations and took roughly 0.002 seconds mean in local measurements.  The compact route notices that f pairs every row around one
branch center, obtains a row sum from a single 2-cycle, exponentiates three
scalars, and scales six terminal coefficients in at most 51 exact operations.
Every displayed coefficient is marginally uniform, and rows are independently
sampled, defeating positional, modal, leading-coordinate, adjacent-pair, copy,
and shared-scalar guesses; the billion-candidate scalar space defeats 256 random
restarts.  All attacks are tested on eight shipping seeds.  There is no special
planted row and hence no plant/decoy distribution split.
"""


_BRANCHES = 3
_TERMS_PER_BRANCH = 2
_ENUMERATION_CAP = 50_000
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 2, "attempts": 3},
}


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _normal_form(inst: dict[str, Any], count_operations: bool = False):
    """Reference PBW scan; it deliberately does not use planted metadata."""
    modulus = inst["modulus"]
    degree = inst["degree"]
    coefficients: dict[int, int] = {}
    operations = 0
    for branch in inst["branches"]:
        scalar = 1
        dense = branch["dense_factors"]
        if len(dense) != degree - 1:
            raise ValueError("instance has an inconsistent number of factors")
        for row in dense:
            if len(row) != inst["n"]:
                raise ValueError("instance has a malformed dense factor")
            row_sum = 0
            for coefficient in row:
                row_sum = (row_sum + coefficient) % modulus
                operations += 1
            scalar = (scalar * row_sum) % modulus
            operations += 1
        for generator, coefficient in branch["terminal"]:
            value = (scalar * coefficient) % modulus
            operations += 1
            coefficients[generator] = (coefficients.get(generator, 0) + value) % modulus
    answer = [
        [coefficient, generator]
        for generator, coefficient in sorted(coefficients.items())
        if coefficient % modulus
    ]
    if count_operations:
        return answer, operations
    return answer


def _direct_expand_small(inst: dict[str, Any]) -> list[list[int]]:
    """Independently expand a small instance before reducing every word."""
    modulus = inst["modulus"]
    coefficients: dict[int, int] = {}
    for branch in inst["branches"]:
        terms: dict[tuple[int, ...], int] = {(): 1}
        for row in branch["dense_factors"]:
            next_terms: dict[tuple[int, ...], int] = {}
            for word, coefficient in terms.items():
                for generator, value in enumerate(row):
                    new_word = word + (generator,)
                    next_terms[new_word] = (
                        next_terms.get(new_word, 0) + coefficient * value
                    ) % modulus
            terms = next_terms
        next_terms = {}
        for word, coefficient in terms.items():
            for generator, value in branch["terminal"]:
                new_word = word + (generator,)
                next_terms[new_word] = (
                    next_terms.get(new_word, 0) + coefficient * value
                ) % modulus
        for word, coefficient in next_terms.items():
            # Corollary 3.6 sends every word to the basis word determined by
            # its last generator; this expansion does not use _normal_form.
            generator = word[-1]
            coefficients[generator] = (
                coefficients.get(generator, 0) + coefficient
            ) % modulus
    return [
        [coefficient, generator]
        for generator, coefficient in sorted(coefficients.items())
        if coefficient
    ]


def _check_rf_identities(inst: dict[str, Any]) -> tuple[int, int]:
    """Directly count idempotence and YBE checks for the displayed r_f."""
    permutation = inst["permutation"]
    n = inst["n"]

    def r_pair(left: int, right: int) -> tuple[int, int]:
        return permutation[right], right

    idempotent = 0
    for left in range(n):
        for right in range(n):
            first = r_pair(left, right)
            idempotent += int(r_pair(*first) == first)

    ybe = 0
    for a in range(n):
        for b in range(n):
            for c in range(n):
                x, y = r_pair(a, b)
                y, z = r_pair(y, c)
                x, y = r_pair(x, y)
                lhs = (x, y, z)

                y, z = r_pair(b, c)
                x, y = r_pair(a, y)
                y, z = r_pair(y, z)
                rhs = (x, y, z)
                ybe += int(lhs == rhs)
    return idempotent, ybe


def _candidate_from_lambdas(inst: dict[str, Any], lambdas: list[int]) -> list[list[int]]:
    modulus = inst["modulus"]
    terms = []
    for branch, scalar in zip(inst["branches"], lambdas):
        for generator, coefficient in branch["terminal"]:
            terms.append([(scalar * coefficient) % modulus, generator])
    return sorted(terms, key=lambda term: term[1])


def _attack_candidates(inst: dict[str, Any]) -> dict[str, list[list[int]]]:
    modulus = inst["modulus"]
    exponent = inst["degree"] - 1
    first_entries = []
    adjacent_pair_guesses = []
    ignore_pairing_guesses = []
    modal_outlier_guesses = []
    for branch in inst["branches"]:
        rows = branch["dense_factors"]
        leading_product = 1
        for row in rows:
            leading_product = (leading_product * row[0]) % modulus
        first_entries.append(leading_product or 1)
        adjacent_sum = ((inst["n"] // 2) * (rows[0][0] + rows[0][1])) % modulus
        adjacent_pair_guesses.append(pow(adjacent_sum, exponent, modulus) or 1)
        guessed_sum = (inst["n"] * rows[0][0]) % modulus
        ignore_pairing_guesses.append(pow(guessed_sum, exponent, modulus) or 1)
        frequencies = [0] * modulus
        for row in rows:
            for coefficient in row:
                frequencies[coefficient] += 1
        # Guess that the most frequent individual coefficient is the hidden
        # centre.  Pair endpoints are marginally uniform, so this per-element
        # outlier statistic carries no planted signal.
        guessed_center = max(range(modulus), key=lambda value: frequencies[value])
        modal_sum = (inst["n"] * guessed_center) % modulus
        modal_outlier_guesses.append(pow(modal_sum, exponent, modulus) or 1)

    # This partial structural attack correctly compresses branch 0 but makes the
    # tempting (and false) assumption that all summands share its scalar.
    first_sum = sum(inst["branches"][0]["dense_factors"][0]) % modulus
    shared = pow(first_sum, exponent, modulus) or 1
    return {
        "outlier_modal_coefficient": _candidate_from_lambdas(
            inst, modal_outlier_guesses
        ),
        "ignore_f_pairing_center_guess": _candidate_from_lambdas(
            inst, ignore_pairing_guesses
        ),
        "adjacent_pairing_guess": _candidate_from_lambdas(
            inst, adjacent_pair_guesses
        ),
        "greedy_leading_product": _candidate_from_lambdas(inst, first_entries),
        "copy_terminal_factors": _candidate_from_lambdas(inst, [1] * _BRANCHES),
        "single_shared_scalar_ansatz": _candidate_from_lambdas(
            inst, [shared] * _BRANCHES
        ),
    }


def make_instance(n: int, seed: int = 0, **params: Any) -> dict[str, Any]:
    """Build a certified PBW-normal-form instance by composition of identities."""
    factors = params.pop("factors", None)
    modulus = params.pop("modulus", 1009)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(n) or n < 2 * _BRANCHES + 2 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    if factors is None:
        factors = max(3, n)
    if not _is_int(factors) or factors < 3:
        raise ValueError("factors must be an integer at least 3")
    if not _is_int(modulus) or modulus < 11 or not _is_prime(modulus):
        raise ValueError("modulus must be a prime at least 11")
    if n % modulus == 0:
        raise ValueError("n must be nonzero in GF(p)")
    power_image_size = (modulus - 1) // math.gcd(factors - 1, modulus - 1)
    if power_image_size < _BRANCHES + 1:
        raise ValueError(
            "the exponent map on GF(p)^* must have at least four image values"
        )

    rng = random.Random(seed)
    pivot = rng.randrange(n)
    for _ in range(100):
        shuffled = list(range(n))
        rng.shuffle(shuffled)
        permutation = [0] * n
        cycles = []
        for position in range(0, n, 2):
            left, right = shuffled[position : position + 2]
            permutation[left] = right
            permutation[right] = left
            cycles.append((left, right))
        if permutation[0] != 1:
            break
    else:
        raise RuntimeError("could not sample a non-adjacent first f-cycle")
    available = [index for index in range(n) if index != pivot]
    rng.shuffle(available)
    support_groups = [
        sorted(available[2 * b : 2 * b + 2]) for b in range(_BRANCHES)
    ]

    # Resampling merely avoids the named cheap signatures.  The certificate is
    # always known from target_sum; no instance is solved during this filter.
    for _attempt in range(200):
        branches = []
        true_lambdas = []
        used_lambdas: set[int] = set()
        for branch_index in range(_BRANCHES):
            for _target_attempt in range(10_000):
                center = rng.randrange(1, modulus)
                target_sum = (n * center) % modulus
                scalar = pow(target_sum, factors - 1, modulus)
                if scalar not in (0, 1) and scalar not in used_lambdas:
                    used_lambdas.add(scalar)
                    break
            else:
                raise RuntimeError("could not sample three distinct nonunit powers")

            dense_factors = []
            for _ in range(factors - 1):
                row = [0] * n
                for left, right in cycles:
                    value = rng.randrange(modulus)
                    row[left] = value
                    row[right] = (2 * center - value) % modulus
                dense_factors.append(row)
            terminal = [
                [generator, rng.randrange(1, modulus)]
                for generator in support_groups[branch_index]
            ]
            branches.append(
                {"dense_factors": dense_factors, "terminal": terminal}
            )
            true_lambdas.append(scalar)

        inst = {
            "paper": "arXiv:2308.11427",
            "field": f"GF({modulus})",
            "modulus": modulus,
            "n": n,
            "pivot": pivot,
            "permutation": permutation,
            "degree": factors,
            "branches": branches,
        }
        answer = _candidate_from_lambdas(inst, true_lambdas)
        inst["answer"] = answer
        if all(candidate != answer for candidate in _attack_candidates(inst).values()):
            return inst
    raise RuntimeError("could not avoid cheap planted signatures")


def _format_linear(row: list[int]) -> str:
    return "[" + ",".join(str(value) for value in row) + "]"


def render(inst: dict[str, Any]) -> str:
    """Render the complete problem, with no hint unless GV_HINT_MODE requests it."""
    n = inst["n"]
    modulus = inst["modulus"]
    pivot = inst["pivot"]
    degree = inst["degree"]
    lines = [
        "PBW normal form in a permutation-idempotent Yang--Baxter algebra",
        "",
        f"Work over the prime field GF({modulus}); reduce every coefficient modulo {modulus}.",
        "The displayed list f is a permutation: f[i]=j means f(x_i)=x_j.",
        "It defines the permutation-idempotent Yang--Baxter map",
        "r_f(x_i,x_j)=(x_k,x_j), where k=f[j].",
        "f: " + json.dumps(inst["permutation"], separators=(",", ":")),
        f"Let A be the associative noncommutative algebra on generators x_0,...,x_{n-1}",
        f"with relations x_i x_j = x_{pivot} x_j for every 0 <= i,j < {n}.",
        f"Use a generator order with the distinguished x_{pivot} first; thus the degree-{degree}",
        f"PBW basis is x_{pivot}^{degree-1} x_j (0 <= j < {n}).",
        "A coefficient row [c_0,...,c_(n-1)] denotes the linear form sum_i c_i x_i.",
        "Multiplication is in the printed left-to-right order; the three branch products are added.",
        "All indices are 0-based, all intervals are inclusive, and repeated generators in a linear form are combined modulo p.",
        "",
        "The polynomial F is the sum of these three products.  Each D-row is one dense linear factor; T is the final sparse factor.",
    ]
    for branch_index, branch in enumerate(inst["branches"]):
        lines.append(f"BRANCH {branch_index}")
        for row_index, row in enumerate(branch["dense_factors"]):
            lines.append(f"D{row_index}: {_format_linear(row)}")
        terminal_text = ",".join(
            f"({coefficient},x_{generator})"
            for generator, coefficient in branch["terminal"]
        )
        lines.append(f"T: [{terminal_text}]")
    supports = [
        [term[0] for term in branch["terminal"]] for branch in inst["branches"]
    ]
    lines.extend(
        [
            "",
            "Find the unique PBW normal form F = sum_j a_j "
            f"x_{pivot}^{degree-1} x_j.",
            f"The three terminal supports are {json.dumps(supports, separators=(',', ':'))}; they are disjoint.",
            "The answer is guaranteed to have exactly two nonzero terms on each terminal support.",
            "Within each support, its two coefficients must be one common nonzero GF(p) scalar multiple of the displayed T coefficients.",
            f"That common scalar has the form s^{degree-1} for some nonzero s in GF(p).",
            "",
            "Give your final answer inside <answer></answer> tags as compact JSON",
            "[[coefficient,generator],...] with exactly six terms, ordered by strictly increasing generator.",
            f"Use canonical coefficients 1,...,{modulus-1}; do not include zero terms.",
            "Example of the syntax: <answer>[[1,0],[2,1],[3,2],[4,3],[5,4],[6,5]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: Any) -> object | None:
    """Extract the last answer block and decode its JSON, returning None on error."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```") and payload.endswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        decoded = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return decoded if isinstance(decoded, list) else None


def verify(inst: dict[str, Any], answer: Any) -> tuple[bool, str]:
    """Check a canonical sparse PBW polynomial without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer cannot be empty"
    expected_terms = _BRANCHES * _TERMS_PER_BRANCH
    if len(answer) != expected_terms:
        return False, f"wrong number of terms: expected {expected_terms}"

    previous = -1
    seen: set[int] = set()
    parsed: list[list[int]] = []
    for position, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term {position} must be [coefficient,generator]"
        coefficient, generator = term
        if not _is_int(coefficient) or not _is_int(generator):
            return False, f"term {position} entries must be integers"
        if not 0 <= generator < inst["n"]:
            return False, f"generator index out of range at term {position}"
        if generator in seen:
            return False, f"generator indices must be distinct; duplicate {generator}"
        if generator <= previous:
            return False, "terms must be ordered by increasing generator index"
        if not 1 <= coefficient < inst["modulus"]:
            return False, f"coefficient at generator {generator} is not canonical nonzero GF(p)"
        previous = generator
        seen.add(generator)
        parsed.append([coefficient, generator])

    expected = _normal_form(inst)
    expected_support = [term[1] for term in expected]
    actual_support = [term[1] for term in parsed]
    if actual_support != expected_support:
        return False, "term support does not equal the three terminal supports"
    for actual_term, expected_term in zip(parsed, expected):
        if actual_term[0] != expected_term[0]:
            return False, f"coefficient mismatch at generator {actual_term[1]}"
    return True, "ok"


def random_candidate(inst: dict[str, Any], rng: random.Random) -> object:
    """Sample uniformly from the statement-aware three-power language."""
    exponent = inst["degree"] - 1
    lambdas = [
        pow(rng.randrange(1, inst["modulus"]), exponent, inst["modulus"])
        for _ in range(_BRANCHES)
    ]
    return _candidate_from_lambdas(inst, lambdas)


def search_space(inst: dict[str, Any]) -> int | None:
    """Count the three independent nonzero power-image scalars exactly."""
    image_size = (inst["modulus"] - 1) // math.gcd(
        inst["degree"] - 1, inst["modulus"] - 1
    )
    return image_size**_BRANCHES


def enumerate_all(inst: dict[str, Any]) -> int | None:
    """Brute-force the bounded scalar language when it is below a hard cap."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    expected = _normal_form(inst)
    hits = 0
    modulus = inst["modulus"]
    image = sorted(
        {pow(value, inst["degree"] - 1, modulus) for value in range(1, modulus)}
    )
    for a in image:
        for b in image:
            for c in image:
                if _candidate_from_lambdas(inst, [a, b, c]) == expected:
                    hits += 1
    return hits


def canonical_key(inst: dict[str, Any]) -> str:
    """Invariant under relabellings and normal-form-preserving reorderings."""
    permutation = inst["permutation"]
    cycles = [(i, permutation[i]) for i in range(inst["n"]) if i < permutation[i]]
    canonical_branches = []
    for branch in inst["branches"]:
        row_pair_multisets = []
        for row in branch["dense_factors"]:
            paired = sorted(
                (min(row[left], row[right]), max(row[left], row[right]))
                for left, right in cycles
            )
            row_pair_multisets.append(paired)
        row_pair_multisets.sort()
        terminal_coefficients = sorted(term[1] for term in branch["terminal"])
        terminal_generators = [term[0] for term in branch["terminal"]]
        terminal_is_cycle = (
            permutation[terminal_generators[0]] == terminal_generators[1]
        )
        terminal_touches_pivot_pair = sum(
            generator in (inst["pivot"], permutation[inst["pivot"]])
            for generator in terminal_generators
        )
        canonical_branches.append(
            [
                row_pair_multisets,
                terminal_coefficients,
                terminal_is_cycle,
                terminal_touches_pivot_pair,
            ]
        )
    canonical_branches.sort(key=lambda item: json.dumps(item, separators=(",", ":")))
    payload = {
        "n": inst["n"],
        "modulus": inst["modulus"],
        "degree": inst["degree"],
        "branches": canonical_branches,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict[str, Any]) -> dict[str, Any] | str | None:
    """Grow the ambient coefficient table at fixed six-term certificate length."""
    result = dict(params)
    factors = int(result.get("factors", 3))
    n = int(result.get("n", 8))
    if n < 256:
        result["n"] = min(256, n * 2)
        return result
    if factors < 384:
        result["factors"] = min(384, factors * 2)
        return result
    return None


def _relabel_instance(inst: dict[str, Any], permutation: list[int]) -> dict[str, Any]:
    """Carry the algebra and certificate through old_index -> new_index."""
    n = inst["n"]
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in ("branches", "answer", "pivot", "permutation")
    }
    transformed["pivot"] = permutation[inst["pivot"]]
    transformed_permutation = [0] * n
    for old_index in range(n):
        transformed_permutation[permutation[old_index]] = permutation[
            inst["permutation"][old_index]
        ]
    transformed["permutation"] = transformed_permutation
    branches = []
    for branch in inst["branches"]:
        rows = []
        for row in branch["dense_factors"]:
            new_row = [0] * n
            for old_index, coefficient in enumerate(row):
                new_row[permutation[old_index]] = coefficient
            rows.append(new_row)
        terminal = sorted(
            [[permutation[generator], coefficient] for generator, coefficient in branch["terminal"]],
            key=lambda term: term[0],
        )
        branches.append({"dense_factors": rows, "terminal": terminal})
    transformed["branches"] = branches
    transformed["answer"] = sorted(
        [[coefficient, permutation[generator]] for coefficient, generator in inst["answer"]],
        key=lambda term: term[1],
    )
    return transformed


def _reorder_instance(inst: dict[str, Any], branch_order: list[int], reverse_factors: bool):
    transformed = {
        key: value for key, value in inst.items() if key not in ("branches", "answer")
    }
    branches = []
    for index in branch_order:
        branch = inst["branches"][index]
        rows = [list(row) for row in branch["dense_factors"]]
        if reverse_factors:
            rows.reverse()
        branches.append(
            {
                "dense_factors": rows,
                "terminal": [list(term) for term in branch["terminal"]],
            }
        )
    transformed["branches"] = branches
    transformed["answer"] = [list(term) for term in inst["answer"]]
    return transformed


def _swap_within_f_cycles(inst: dict[str, Any], seed: int) -> dict[str, Any]:
    """Independently swap coefficients across f-cycles in every dense row."""
    rng = random.Random(seed)
    transformed = {
        key: value for key, value in inst.items() if key not in ("branches", "answer")
    }
    branches = []
    for branch in inst["branches"]:
        rows = []
        for source in branch["dense_factors"]:
            row = list(source)
            for left in range(inst["n"]):
                right = inst["permutation"][left]
                if left < right and rng.randrange(2):
                    row[left], row[right] = row[right], row[left]
            rows.append(row)
        branches.append(
            {
                "dense_factors": rows,
                "terminal": [list(term) for term in branch["terminal"]],
            }
        )
    transformed["branches"] = branches
    transformed["answer"] = [list(term) for term in inst["answer"]]
    return transformed


def _atomic_elements(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def _pow_operation_count(exponent: int) -> int:
    # The straightforward left-to-right binary method: one square per bit and
    # one multiply for every set bit.
    return exponent.bit_length() + exponent.bit_count()


def selftest() -> dict[str, Any]:
    """Run mandatory G1--G9 checks and return only JSON-native measurements."""
    report: dict[str, Any] = {
        "paper": "2308.11427",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every preset, several seeds, JSON-native certificate, no exceptions.
    g1_attempts = 0
    g1_successes = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok = verify(inst, inst["answer"])[0]
            g1_attempts += 1
            g1_successes += int(ok)
            json_roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    demo_identity = make_instance(seed=0, **DIFFICULTY["demo"])
    direct_expansion_ok = _direct_expand_small(demo_identity) == demo_identity["answer"]
    idempotent_checks, ybe_checks = _check_rf_identities(demo_identity)
    identity_checks_ok = (
        idempotent_checks == demo_identity["n"] ** 2
        and ybe_checks == demo_identity["n"] ** 3
    )
    report["G1_planted_verifies"] = {
        "pass": g1_successes == g1_attempts
        and json_roundtrips == g1_attempts
        and direct_expansion_ok
        and identity_checks_ok,
        "successes": g1_successes,
        "attempts": g1_attempts,
        "json_native_roundtrips": json_roundtrips,
        "demo_direct_expansion_matches": direct_expansion_ok,
        "demo_idempotence_checks": idempotent_checks,
        "demo_ybe_checks": ybe_checks,
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: order checks are intentionally sequenced to produce diagnostic reasons.
    answer = [list(term) for term in shipping["answer"]]
    corruptions: dict[str, Any] = {
        "drop": answer[:-1],
        "swap": [answer[1], answer[0]] + answer[2:],
        "duplicate": [answer[0], [answer[1][0], answer[0][1]]] + answer[2:],
        "empty": [],
        "out_of_range": [[answer[0][0], shipping["n"]]] + answer[1:],
    }
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejection_reasons.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    model_response = (
        "I reduced each branch in GF(p).\n```json\n<answer>\n"
        + json.dumps(shipping["answer"], separators=(",", ":"))
        + "\n</answer>\n```\nThe entries are in increasing generator order."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"]
        and parse_answer("no tagged answer here") is None
        and parse_answer("<answer>{bad json}</answer>") is None,
        "realistic_response_recovered": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4 and shipping-density part of G5 share one structure-aware sample.
    expected = _normal_form(shipping)
    guess_rng = random.Random(0x230811427)
    sample_total = 200_000
    sample_hits = 0
    for _ in range(sample_total):
        sample_hits += int(random_candidate(shipping, guess_rng) == expected)
    empirical = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "empirical_probability": empirical,
        "candidate_space": search_space(shipping),
        "exact_probability": 1.0 / search_space(shipping),
        "prior": "uniform over three independent nonzero power-image branch scalars; all stated shape, proportionality, and exponent constraints enforced",
    }

    attack_stats = {
        name: {"successes": 0, "attempts": 0}
        for name in list(_attack_candidates(shipping)) + ["random_restart_256"]
    }
    reference_successes = 0
    reference_operations = 0
    reference_elapsed = 0.0
    reference_instances = []
    for seed in range(8100, 8108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_candidates(inst).items():
            ok = verify(inst, candidate)[0]
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(ok)
        restart_rng = random.Random(seed ^ 0xA55A5AA5)
        restart_solved = False
        target = _normal_form(inst)
        for _ in range(256):
            if random_candidate(inst, restart_rng) == target:
                restart_solved = True
                break
        attack_stats["random_restart_256"]["attempts"] += 1
        attack_stats["random_restart_256"]["successes"] += int(restart_solved)

        start = time.perf_counter()
        reference_answer, operations = _normal_form(inst, count_operations=True)
        elapsed = time.perf_counter() - start
        reference_ok = verify(inst, reference_answer)[0]
        reference_successes += int(reference_ok)
        reference_operations += operations
        reference_elapsed += elapsed
        reference_instances.append(
            {
                "seed": seed,
                "operations": operations,
                "wall_clock_sec": round(elapsed, 6),
                "solved": reference_ok,
            }
        )

    reference = {
        "name": "PBW coefficient-sum normal-form scan",
        "complexity": "O(branches*factors*n) exact finite-field operations; O(n) working memory",
        "wall_clock_sec": round(reference_elapsed, 6),
        "mean_wall_clock_sec": round(reference_elapsed / 8, 6),
        "operations": reference_operations,
        "mean_operations": reference_operations // 8,
        "solves": f"{reference_successes}/8, as expected",
        "instances": reference_instances,
    }
    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": sample_total >= 200_000
        and reference_successes == 8
        and demo_count == 1,
        "shipping_sampled_solution_hits": sample_hits,
        "shipping_sampled_solution_total": sample_total,
        "shipping_sampled_solution_fraction": empirical,
        "shipping_exact_solution_fraction": 1.0 / search_space(shipping),
        "strongest_attack_wall_sec": round(reference_elapsed, 6),
        "strongest_attack_operations": reference_operations,
        "strongest_attack_mean_operations": reference_operations // 8,
        "strongest_attack_solved_instances": reference_successes,
        "demo_exact_valid_certificate_count": demo_count,
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attack_stats.values()),
        "attacks": attack_stats,
        "reference_algorithm": reference,
    }

    hard = DIFFICULTY["hard"]
    doubled_params = dict(hard)
    doubled_params["n"] = hard["n"] * 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok
        and len(doubled["answer"]) == len(shipping["answer"])
        and doubled["n"] == 2 * shipping["n"],
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "base_dense_coefficients": _BRANCHES * (shipping["degree"] - 1) * shipping["n"],
        "doubled_dense_coefficients": _BRANCHES * (doubled["degree"] - 1) * doubled["n"],
        "base_answer_terms": len(shipping["answer"]),
        "doubled_answer_terms": len(doubled["answer"]),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys: set[str] = set()
    g8_ok = True
    for offset in range(20):
        seed = 90000 + offset
        inst = make_instance(seed=seed, **DIFFICULTY["hard"])
        key = canonical_key(inst)
        unrelated_keys.add(key)
        relabel_rng = random.Random(seed ^ 0xC0FFEE)
        permutation = list(range(inst["n"]))
        relabel_rng.shuffle(permutation)
        relabelled = _relabel_instance(inst, permutation)
        reordered = _reorder_instance(inst, [2, 0, 1], True)
        cycle_swapped = _swap_within_f_cycles(inst, seed ^ 0x51A7)
        composed = _swap_within_f_cycles(
            _reorder_instance(relabelled, [1, 2, 0], True), seed ^ 0xBEEF
        )
        for variant in (
            relabelled,
            reordered,
            cycle_swapped,
            composed,
        ):
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
            "global generator relabelling carrying the pivot",
            "summand reorder",
            "nonfinal factor reorder",
            "independent endpoint swaps within f-cycles in every dense row",
            "composition of all four",
        ],
    }

    # Exact worst-sized member of the bounded six-term language at shipping.
    # This is stronger than hoping a sample happens to contain maximum-width
    # coefficients and generator indices.
    max_width_answer = [
        [shipping["modulus"] - 1, generator]
        for generator in range(shipping["n"] - 6, shipping["n"])
    ]
    answer_chars = len(json.dumps(max_width_answer, separators=(",", ":")))
    answer_elements = _atomic_elements(max_width_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    intended_ops = _BRANCHES * (
        2  # add one f-paired coefficient pair, then multiply by n/2
        + _pow_operation_count(shipping["degree"] - 1)
        + _TERMS_PER_BRANCH
    )
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "hardened"
            if hinted["attempts"] and hinted["solved"] == 0
            else "too_easy"
            if hinted["attempts"]
            else "diagnostic_pending"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_passed"] = all(value["pass"] for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
