"""Verified generator for diagonal-invariant Plucker ratios on Vandermonde codes.

The family is grounded in Section 4 of Alecci--D'Alconzo, arXiv:2603.09869.
For k-subsets I1,J1,I2,J2 with equal multiset union, Lemma 4.1 says that

    p_I1 p_J1 / (p_I2 p_J2)

is invariant under independent nonzero scalings of the code coordinates.  The
instances below use a Vandermonde generator matrix.  Their answers are sampled
first, then four exceptional nodes are chosen so that the displayed ratio has
that value; a random coordinate relabelling carries the certificate.

The module is standard-library-only.  It intentionally does not materialise the
large generator matrix in the problem statement: its exact entry formula is the
paper-native object and is sufficient to reconstruct every entry.
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
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "linear code over a prime finite field",
        "Vandermonde generator matrix",
        "Plucker coordinates",
        "diagonal-invariant rational function",
    ],
    "verification_operations": [
        "exact finite-field subtraction and multiplication",
        "Vandermonde determinant identity",
        "exact modular inversion",
        "exact residue comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Factor each Plucker minor as a Vandermonde product so all factors from "
        "the common columns cancel; without that change of variables one evaluates "
        "four dense determinants."
    ),
    "hardness_basis": (
        "Track B: Section 4, Lemma 4.1 makes the ratio polynomial-time computable; "
        "generic modular Gaussian elimination evaluates four k-by-k minors in "
        "O(k^3), and the measured hard-preset cost is filled from selftest's "
        "reference_algorithm record, while Vandermonde cancellation leaves at most "
        "67 exact field/Euclidean operations."
    ),
    "max_answer_tokens": 3,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "One canonical nonzero residue a with 1 <= a < p, representing the exact "
        "value in GF(p) of the displayed Plucker-coordinate ratio."
    ),
    "bounds": {
        "shape": "one integer",
        "minimum": 1,
        "maximum": "p-1 from the instance",
        "shipping_prime": 2147483647,
    },
}

DIFFICULTY = {"hard": {"n": 126, "prime": 2147483647}}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Vandermonde minors factor into pairwise node differences, and common-column "
    "factors occur equally in the numerator and denominator."
)
PLACEBO_HINT = (
    "Finite-field values use canonical residues, and careful attention to the "
    "displayed zero-based column indices prevents sign errors."
)

# Updated only from script-owned oracle transcripts after the shipping rung holds.
# The arms are diagnostic; G9(c)'s size and exact-operation limits are the gate.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not run",
    "placebo_verdict": "not run",
}

NOTES = r"""
Paper grounding and Step 0.  Section 2.3 defines a linear code as a point of
Gr_q(k,n), represented by a full-rank generator matrix, and defines monomial
equivalence.  Section 3 identifies diagonal invariants with integer vectors in
the left kernel of the subset-incidence matrix W_{k,n}.  Section 4, Lemma 4.1
is the exact identity used here: I1 multiset-union J1 = I2 multiset-union J2
makes p_I1 p_J1/(p_I2 p_J2) invariant under diagonal coordinate scaling.
Theorem 4.1 turns every such invariant into a polynomial vanishing at the
permutation part of a code equivalence, and Theorem 4.2 counts degree 2k and
2(k!)^2 monomials.

What makes it easy and why this is Track B.  The paper explicitly says the
complete incidence matrix has binomial(n,k) rows when k=O(n), and that the
resulting algebraic model is infeasible at cryptographic k >= 126.  It also
gives Lemma 4.1's four-minor invariant as a polynomial-time alternative.  For
this generated distribution there is an additional visible Vandermonde
structure: generic Gaussian elimination is an O(k^3) reference algorithm and
succeeds on every instance, while the determinant product formula cancels all
but four oriented differences.  Thus Track A would be false and Track B is the
honest claim.

Generation and attacks.  The target nonzero field residue is sampled before
the code nodes.  A fractional-linear equation chooses the fourth exceptional
node so that the cleanly ordered ratio equals the target.  A uniformly random
coordinate permutation is then applied, and its determinant-orientation sign
carries the certificate.  Filler and exceptional nodes are all distinct draws
from the same field distribution.  The panel tests a largest-node outlier,
the diagonal-product approximation to each determinant, 256 random residues,
the tempting value-one ansatz, and ordinary integer rather than finite-field
division.  The successful four-determinant elimination is reported separately.
""".strip()


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the 64-bit primes used by this module."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value % p == 0:
            return value == p
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % value == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _permutation_sign(values: list[int]) -> int:
    inversions = 0
    for i, left in enumerate(values):
        inversions += sum(left > right for right in values[i + 1 :])
    return -1 if inversions % 2 else 1


def _minor_orientation_sign(old_subset: list[int], old_to_new: list[int]) -> int:
    return _permutation_sign([old_to_new[index] for index in old_subset])


def make_instance(n: int, seed: int = 0, prime: int = 2147483647, **params: Any) -> dict:
    """Inverse-generate a Vandermonde-code invariant with a known exact value.

    ``n`` is the code dimension and order of each minor; the code length is
    n+2.  The answer is sampled first.  It is never recovered by evaluating the
    four determinants of the completed instance.
    """
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(prime, bool) or not isinstance(prime, int) or not _is_prime(prime):
        raise ValueError("prime must be a prime integer")
    if prime <= n + 5:
        raise ValueError("prime is too small for the required distinct nonzero nodes")

    rng = random.Random(seed)
    k = n
    length = k + 2

    # The old order is R,a,b,x,y, so the uncancelled Vandermonde factors have
    # exactly the ordinary cross-ratio orientation used in the equation below.
    while True:
        target = rng.randrange(2, prime - 1)  # excludes 0, 1, and -1
        a, b, x = rng.sample(range(1, prime), 3)
        xb = (x - b) % prime
        xa = (x - a) % prime
        denominator = (target * xb - xa) % prime
        if denominator == 0:
            continue
        y = (target * xb * a - xa * b) * pow(denominator, -1, prime) % prime
        if y != 0 and len({a, b, x, y}) == 4:
            break

    used = {a, b, x, y}
    common_nodes: list[int] = []
    while len(common_nodes) < k - 2:
        value = rng.randrange(1, prime)
        if value not in used:
            used.add(value)
            common_nodes.append(value)

    old_nodes = common_nodes + [a, b, x, y]
    r_old = list(range(k - 2))
    a_old, b_old, x_old, y_old = range(k - 2, k + 2)
    old_sets = {
        "I1": sorted(r_old + [a_old, x_old]),
        "J1": sorted(r_old + [b_old, y_old]),
        "I2": sorted(r_old + [a_old, y_old]),
        "J2": sorted(r_old + [b_old, x_old]),
    }

    new_to_old = list(range(length))
    rng.shuffle(new_to_old)
    old_to_new = [0] * length
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new
    nodes = [old_nodes[old] for old in new_to_old]
    subsets = {
        name: sorted(old_to_new[index] for index in subset)
        for name, subset in old_sets.items()
    }

    orientation = math.prod(
        _minor_orientation_sign(old_sets[name], old_to_new)
        for name in ("I1", "J1", "I2", "J2")
    )
    answer = target if orientation == 1 else (-target) % prime

    return {
        "field_prime": prime,
        "dimension": k,
        "length": length,
        "nodes": nodes,
        "I1": subsets["I1"],
        "J1": subsets["J1"],
        "I2": subsets["I2"],
        "J2": subsets["J2"],
        "answer": answer,
    }


def render(inst: dict) -> str:
    lines = [
        "PROBLEM: Evaluate a diagonal-invariant ratio of Plucker coordinates exactly.",
        "",
        f"Work in the prime field GF({inst['field_prime']}); all arithmetic, including division, is modulo {inst['field_prime']}.",
        f"The code has dimension k={inst['dimension']} and length m={inst['length']}.",
        "Its k by m generator matrix G is given exactly (without expanding it) by",
        "    G[r,j] = t_j^r in GF(p),",
        f"for row indices r=0,...,{inst['dimension'] - 1} and column indices j=0,...,{inst['length'] - 1}.",
        "Thus row 0 consists of ones.  The nodes t_j, in increasing zero-based column-index order, are:",
        "    " + ", ".join(map(str, inst["nodes"])),
        "",
        "For a k-element set I of column indices, p_I is the determinant in GF(p) of the k by k submatrix formed by those columns in increasing index order.  These are Plucker coordinates of the code.",
        "The four displayed sets have size k and satisfy I1 multiset-union J1 = I2 multiset-union J2.  The nodes are pairwise distinct, so every displayed minor is nonzero.",
        "",
        "I1 = [" + ", ".join(map(str, inst["I1"])) + "]",
        "J1 = [" + ", ".join(map(str, inst["J1"])) + "]",
        "I2 = [" + ", ".join(map(str, inst["I2"])) + "]",
        "J2 = [" + ", ".join(map(str, inst["J2"])) + "]",
        "",
        "Compute the unique canonical nonzero residue a with 1 <= a < p such that",
        "    a = p_I1 * p_J1 / (p_I2 * p_J2) in GF(p).",
        "Independent nonzero rescaling of any coordinate column would not change this ratio.",
        "",
        "Give your final answer inside <answer></answer> tags, as one base-10 integer in the range 1 through p-1.",
        "Example: <answer>37</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> int | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
    if len(matches) != 1:
        return None
    payload = matches[0].strip()
    if not re.fullmatch(r"[+-]?\d+", payload):
        return None
    try:
        return int(payload)
    except ValueError:
        return None


def _vandermonde_minor(inst: dict, name: str) -> int:
    p = inst["field_prime"]
    indices = inst[name]
    nodes = inst["nodes"]
    value = 1
    for left_pos, left_index in enumerate(indices):
        left = nodes[left_index]
        for right_index in indices[left_pos + 1 :]:
            value = value * (nodes[right_index] - left) % p
    return value


def _full_value(inst: dict) -> int:
    p = inst["field_prime"]
    numerator = _vandermonde_minor(inst, "I1") * _vandermonde_minor(inst, "J1") % p
    denominator = _vandermonde_minor(inst, "I2") * _vandermonde_minor(inst, "J2") % p
    if denominator == 0:
        raise ValueError("displayed denominator is zero")
    return numerator * pow(denominator, -1, p) % p


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any proposed exact residue without consulting ``inst['answer']``."""
    if answer is None:
        return False, "answer is missing"
    if isinstance(answer, list):
        if not answer:
            return False, "answer container is empty"
        if len(answer) > 1:
            return False, "answer contains multiple residues"
        return False, "answer must be a scalar, not a one-item container"
    if isinstance(answer, bool) or not isinstance(answer, int):
        return False, "answer must be one integer residue"
    p = inst.get("field_prime")
    if not isinstance(p, int) or answer < 1 or answer >= p:
        return False, "answer is outside the canonical range 1 through p-1"
    try:
        expected = _full_value(inst)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False, "instance data do not define a nonzero Plucker ratio"
    if answer != expected:
        return False, "residue does not equal the displayed Plucker ratio"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> int:
    """Uniformly sample the nonzero residues the statement permits."""
    return rng.randrange(1, inst["field_prime"])


def search_space(inst: dict) -> int:
    return inst["field_prime"] - 1


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 1000:
        return None
    return sum(verify(inst, candidate)[0] for candidate in range(1, inst["field_prime"]))


def _membership_signatures(inst: dict) -> list[tuple[int, int, int, int]]:
    memberships = [set(inst[name]) for name in ("I1", "J1", "I2", "J2")]
    return [tuple(int(index in subset) for subset in memberships) for index in range(inst["length"])]


def canonical_key(inst: dict) -> str:
    """Coordinate-relabeling and affine-node invariant key for this family."""
    p = inst["field_prime"]
    signatures = _membership_signatures(inst)
    try:
        a_index = signatures.index((1, 0, 1, 0))
        b_index = signatures.index((0, 1, 0, 1))
    except ValueError:
        # Strongest cheap fallback for malformed/out-of-family inputs.
        fallback = {
            "p": p,
            "k": inst.get("dimension"),
            "columns": sorted(zip(inst.get("nodes", []), signatures)),
        }
        wire = json.dumps(fallback, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(wire.encode()).hexdigest()
    origin = inst["nodes"][a_index]
    scale = (inst["nodes"][b_index] - origin) % p
    inverse = pow(scale, -1, p)
    columns = sorted(
        [((node - origin) * inverse % p, list(signature))
         for node, signature in zip(inst["nodes"], signatures)]
    )
    canonical = {"p": p, "k": inst["dimension"], "columns": columns}
    wire = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(wire.encode()).hexdigest()


def escalate(params: dict) -> dict:
    """Grow determinant order while the one-residue witness stays fixed-size."""
    harder = dict(params)
    current = int(harder.get("n", 2))
    harder["n"] = max(current + 1, (3 * current + 1) // 2)
    harder.setdefault("prime", 2147483647)
    return harder


def _extended_inverse(value: int, p: int) -> tuple[int, int]:
    old_r, r = p, value % p
    old_t, t = 0, 1
    divisions = 0
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_t, t = t, old_t - q * t
        divisions += 1
    if old_r != 1:
        raise ZeroDivisionError("noninvertible field element")
    return old_t % p, divisions


def _reference_minor(inst: dict, name: str) -> tuple[int, int]:
    """Materialise a dense minor and eliminate; deliberately no Vandermonde trick."""
    p = inst["field_prime"]
    indices = inst[name]
    k = inst["dimension"]
    matrix = [[0] * k for _ in range(k)]
    operations = 0
    for column, index in enumerate(indices):
        node = inst["nodes"][index]
        power = 1
        for row in range(k):
            matrix[row][column] = power
            if row + 1 < k:
                power = power * node % p
                operations += 1

    determinant = 1
    sign = 1
    for column in range(k):
        pivot = next((row for row in range(column, k) if matrix[row][column]), None)
        if pivot is None:
            return 0, operations
        if pivot != column:
            matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
            sign = -sign
        pivot_value = matrix[column][column]
        determinant = determinant * pivot_value % p
        operations += 1
        inverse, divisions = _extended_inverse(pivot_value, p)
        operations += divisions
        for row in range(column + 1, k):
            factor = matrix[row][column] * inverse % p
            operations += 1
            matrix[row][column] = 0
            if factor:
                for j in range(column + 1, k):
                    matrix[row][j] = (matrix[row][j] - factor * matrix[column][j]) % p
                    operations += 2
    return determinant * sign % p, operations


def _reference_gaussian(inst: dict) -> tuple[int, int]:
    values = []
    operations = 0
    for name in ("I1", "J1", "I2", "J2"):
        value, cost = _reference_minor(inst, name)
        values.append(value)
        operations += cost
    p = inst["field_prime"]
    numerator = values[0] * values[1] % p
    denominator = values[2] * values[3] % p
    inverse, divisions = _extended_inverse(denominator, p)
    operations += 2 + divisions
    return numerator * inverse % p, operations + 1


def _exceptional_indices(inst: dict) -> dict[tuple[int, int, int, int], int]:
    signatures = _membership_signatures(inst)
    return {signature: index for index, signature in enumerate(signatures) if signature != (1, 1, 1, 1)}


def _oriented_difference(inst: dict, left: int, right: int) -> int:
    low, high = sorted((left, right))
    return (inst["nodes"][high] - inst["nodes"][low]) % inst["field_prime"]


def _compact_components(inst: dict) -> tuple[int, int]:
    special = _exceptional_indices(inst)
    a = special[(1, 0, 1, 0)]
    b = special[(0, 1, 0, 1)]
    x = special[(1, 0, 0, 1)]
    y = special[(0, 1, 1, 0)]
    p = inst["field_prime"]
    numerator = _oriented_difference(inst, a, x) * _oriented_difference(inst, b, y) % p
    denominator = _oriented_difference(inst, a, y) * _oriented_difference(inst, b, x) % p
    return numerator, denominator


def _compact_value(inst: dict) -> int:
    numerator, denominator = _compact_components(inst)
    return numerator * pow(denominator, -1, inst["field_prime"]) % inst["field_prime"]


def _greedy_diagonal_candidate(inst: dict) -> int:
    p = inst["field_prime"]
    products = []
    for name in ("I1", "J1", "I2", "J2"):
        value = 1
        for exponent, index in enumerate(inst[name]):
            value = value * pow(inst["nodes"][index], exponent, p) % p
        products.append(value)
    denominator = products[2] * products[3] % p
    if denominator == 0:
        return 1
    return products[0] * products[1] * pow(denominator, -1, p) % p or 1


def _ordinary_integer_candidate(inst: dict) -> int:
    special = _exceptional_indices(inst)
    a = special[(1, 0, 1, 0)]
    b = special[(0, 1, 0, 1)]
    x = special[(1, 0, 0, 1)]
    y = special[(0, 1, 1, 0)]
    nodes = inst["nodes"]

    def raw(left: int, right: int) -> int:
        low, high = sorted((left, right))
        return nodes[high] - nodes[low]

    numerator = raw(a, x) * raw(b, y)
    denominator = raw(a, y) * raw(b, x)
    if denominator == 0:
        return 1
    rounded = round(numerator / denominator)
    return rounded % inst["field_prime"] or 1


def _random_restart_candidate(inst: dict, seed: int, restarts: int = 256) -> int:
    rng = random.Random(seed)
    expected = _full_value(inst)
    last = 1
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if last == expected:
            return last
    return last


def _attack_candidates(inst: dict, seed: int) -> dict[str, int]:
    return {
        "outlier_largest_node": max(inst["nodes"]),
        "greedy_determinant_diagonal": _greedy_diagonal_candidate(inst),
        "random_restart_256": _random_restart_candidate(inst, 700000 + seed),
        "unit_invariant_ansatz": 1,
        "ordinary_integer_cross_ratio": _ordinary_integer_candidate(inst),
    }


def _relabel_coordinates(inst: dict, rng: random.Random) -> tuple[dict, int]:
    transformed = copy.deepcopy(inst)
    length = inst["length"]
    old_to_new = list(range(length))
    rng.shuffle(old_to_new)
    new_to_old = [0] * length
    for old, new in enumerate(old_to_new):
        new_to_old[new] = old
    transformed["nodes"] = [inst["nodes"][old] for old in new_to_old]
    orientation = 1
    for name in ("I1", "J1", "I2", "J2"):
        old_subset = inst[name]
        orientation *= _minor_orientation_sign(old_subset, old_to_new)
        transformed[name] = sorted(old_to_new[index] for index in old_subset)
    carried = inst["answer"] if orientation == 1 else (-inst["answer"]) % inst["field_prime"]
    transformed["answer"] = carried
    return transformed, carried


def _affine_nodes(inst: dict, rng: random.Random) -> tuple[dict, int]:
    transformed = copy.deepcopy(inst)
    p = inst["field_prime"]
    scale = rng.randrange(1, p)
    shift = rng.randrange(p)
    transformed["nodes"] = [(scale * value + shift) % p for value in inst["nodes"]]
    transformed["answer"] = inst["answer"]
    return transformed, inst["answer"]


def _count_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_atoms(item) for item in value)
    return 1


def _intended_operation_bound(inst: dict) -> int:
    _, denominator = _compact_components(inst)
    _, divisions = _extended_inverse(denominator, inst["field_prime"])
    # Four oriented subtractions, two pair products, one final product, and the
    # measured Euclidean divisions for inversion.
    return 7 + divisions


def selftest() -> dict:
    report: dict[str, Any] = {
        "paper": "2603.09869",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, why = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            relation_ok = (
                sorted(inst["I1"] + inst["J1"])
                == sorted(inst["I2"] + inst["J2"])
            )
            compact_ok = _compact_value(inst) == inst["answer"]
            if not (ok and json_ok and relation_ok and compact_ok):
                failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "json_native_checks": attempts,
        "multiset_identity_checks": attempts,
        "independent_compact_formula_checks": attempts,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=24681357, **shipping_params)
    answer = inst["answer"]

    corruptions = {
        "drop_one": None,
        "swap_one": [answer],
        "duplicate": [answer, answer],
        "empty": [],
        "out_of_range": inst["field_prime"],
    }
    cases = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    wrong = answer + 1 if answer + 1 < inst["field_prime"] else answer - 1
    wrong_ok, wrong_reason = verify(inst, wrong)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(row["rejected"] for row in cases.values())
            and len(set(reasons)) == len(reasons)
            and not wrong_ok
        ),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
        "wrong_valid_residue": {"rejected": not wrong_ok, "reason": wrong_reason},
    }

    response = (
        "Using the Vandermonde product and cancelling common factors gives:\n"
        "```text\n<answer>" + str(answer) + "</answer>\n```\n"
        "This is already the canonical residue."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    trials = 200_000
    rng = random.Random(0x260309869)
    expected = _full_value(inst)
    hits = sum(random_candidate(inst, rng) == expected for _ in range(trials))
    observed = hits / trials
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": observed,
        "exact_probability": 1 / search_space(inst),
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform over all nonzero canonical residues, the exact bounded answer language",
    }

    reference_attempts = 8
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(800, 800 + reference_attempts):
        test = make_instance(seed=seed, **shipping_params)
        started = time.perf_counter()
        got, operations = _reference_gaussian(test)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        reference_successes += int(verify(test, got)[0])

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6 and reference_successes == reference_attempts and demo_count == 1,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_sampled_solution_fraction": observed,
        "shipping_exact_solution_probability": 1 / search_space(inst),
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_seconds_total": round(sum(reference_times), 6),
        "baseline_wall_clock_seconds_max": round(max(reference_times), 6),
        "baseline_operations_max": max(reference_operations),
        "baseline_attempts": reference_attempts,
    }

    attack_counts = {
        name: {"successes": 0, "attempts": 0}
        for name in (
            "outlier_largest_node",
            "greedy_determinant_diagonal",
            "random_restart_256",
            "unit_invariant_ansatz",
            "ordinary_integer_cross_ratio",
        )
    }
    for seed in range(8):
        test = make_instance(seed=9000 + seed, **shipping_params)
        for name, candidate in _attack_candidates(test, seed).items():
            ok, _ = verify(test, candidate)
            attack_counts[name]["successes"] += int(ok)
            attack_counts[name]["attempts"] += 1
    all_failed = all(
        row["successes"] == 0 and row["attempts"] >= 8
        for row in attack_counts.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "dense modular Gaussian elimination on four materialised Vandermonde minors",
            "complexity": "O(k^3) finite-field operations after O(k^2) materialisation",
            "wall_clock_sec_total": round(sum(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations": max(reference_operations),
            "successes": reference_successes,
            "attempts": reference_attempts,
            "solves": f"{reference_successes}/{reference_attempts}, as expected on Track B",
        },
    }

    harder = escalate(shipping_params)
    hard_inst = make_instance(seed=111, **harder)
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=222, **doubled_params)
    k0 = inst["dimension"]
    k1 = hard_inst["dimension"]
    report["G7_scales"] = {
        "pass": (
            k1 > k0
            and verify(hard_inst, hard_inst["answer"])[0]
            and verify(doubled, doubled["answer"])[0]
            and k1 ** 3 > k0 ** 3
        ),
        "shipping_minor_order": k0,
        "escalated_minor_order": k1,
        "reference_cubic_work_ratio": (k1 / k0) ** 3,
        "doubled_n": doubled_params["n"],
        "doubled_verifies": verify(doubled, doubled["answer"])[0],
        "answer_elements_unchanged": _count_atoms(hard_inst["answer"]) == 1,
    }

    selected = [make_instance(seed=20000 + seed, **shipping_params) for seed in range(20)]
    seen = {canonical_key(test) for test in selected}
    g8_failures = []
    invariance_checks = 0
    carried_checks = 0
    for offset, base in enumerate(selected):
        local_rng = random.Random(26030000 + offset)
        relabelled, relabelled_answer = _relabel_coordinates(base, local_rng)
        affine, affine_answer = _affine_nodes(base, local_rng)
        composed, composed_answer = _relabel_coordinates(affine, local_rng)
        for transformed, carried, label in (
            (relabelled, relabelled_answer, "coordinate relabelling"),
            (affine, affine_answer, "affine node change"),
            (composed, composed_answer, "composed relabelling and affine change"),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != canonical_key(base):
                g8_failures.append(f"seed {20000 + offset}: key changed under {label}")
            ok, why = verify(transformed, carried)
            carried_checks += 1
            if not ok:
                g8_failures.append(f"seed {20000 + offset}: carried answer failed under {label}: {why}")
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(seen) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(seen),
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "symmetries": [
            "arbitrary coordinate relabelling with determinant-orientation transport",
            "global affine node changes t -> u*t+v with u nonzero",
            "compositions of those maps",
        ],
    }

    blob = json.dumps(answer, separators=(",", ":"))
    chars = len(blob)
    atoms = _count_atoms(answer)
    tokens = (chars + 3) // 4
    intended_operations = _intended_operation_bound(inst)
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else 0.0
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else 0.0
    within_caps = chars <= 2000 and atoms <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "placebo_verdict": G9_EVIDENCE["placebo_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": atoms,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if re.match(r"G\d", key)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
