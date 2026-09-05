"""Verified sparse decoding problems from arXiv:1710.02265.

Li--Ling--Xing--Yeo construct a modular lattice/code from evaluations of
linear polynomials over F_q.  Their public map has a systematic generator
H=[I|-G], and its output is mH+e modulo q-1 for a binary error e of fixed
weight d-1.  Multiplying by the corresponding parity-check matrix removes m,
so inversion contains the exact witness problem used here: find the support of
e from its modular syndrome.

The generator samples e first, constructs a genuine polynomial-lattice public
key as in Proposition 1, and derives the syndrome.  It never decodes the
instance it emits.  Everything is deterministic in (n, seed, params), uses
only the Python standard library, and is silent on import.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time
from typing import Any


TRACK = "A"

_REDUCTION = (
    "Sections 4--5 (Evaluate and Error search): eliminate the systematic "
    "message from c=mH+e with the parity-check matrix of H=[I|-G]"
)

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "polynomial-lattice code over Z/(q-1)",
        "modular parity-check columns",
        "fixed-weight binary error syndrome",
    ],
    "verification_operations": [
        "exact modular vector addition",
        "fixed-weight support validation",
        "exact syndrome comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "View the systematic public map through its parity-check dual, where "
        "the hidden binary error is a fixed-size subset of columns summing to "
        "the syndrome; without that view one searches messages and errors together."
    ),
    "hardness_basis": (
        "Track A: Section 5's Error search and Proposition 2 analyze decoding "
        "through exhaustive information-set search and BKZ rather than an "
        "efficient inversion; the shipping n=400,d=15 regime has 14 errors, "
        "a systematic-search layer of about C(385,13), and the measured "
        "50,000-node systematic decoder cost and wall-clock are reported in G5."
    ),
    "max_answer_tokens": 15,
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

DIFFICULTY = {
    "demo": {"n": 10, "d": 3, "field_slack": 0},
    "easy": {"n": 400, "d": 15, "field_slack": 0},
    "medium": {"n": 520, "d": 15, "field_slack": 180},
    "hard": {"n": 700, "d": 15, "field_slack": 420},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The systematic map has a parity-check dual in which the hidden error "
    "support is a fixed-size subset of columns with the displayed modular sum."
)
PLACEBO_HINT = (
    "The displayed modular columns use zero-based labels, so careful indexing "
    "and consistent residue representatives matter throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly d-1 distinct zero-based "
        "column indices from 0 through n-1; it is the support of a binary error."
    ),
    "bounds": {
        "max_support_size": 14,
        "max_index_exclusive_named_ladder": 700,
        "binary_entries": 1,
        "strictly_increasing": 1,
    },
}

# Filled from the script-owned transcripts after the three oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition and Step 0.  Section 3 defines L_{a,c(x)} as the kernel of the
homomorphism u -> product_i (x-alpha_i)^u_i modulo c(x).  Proposition 1 gives
the basis [I,-G;0,(q^{d0}-1)I].  Section 4 takes d=t and d0=1, publishes
H=[I,-G] over Z/(q-1), samples a binary error of exact weight d-1, and evaluates
c=mH+e.  The final remark of Section 4 explicitly permits a coordinate
permutation.  Section 5's Error search eliminates the systematic message and
checks the remaining coordinates.  The module makes exactly the equivalent
parity-check syndrome P e, where P=[G^T|I_d], then uniformly permutes columns.
This is the paper's decoding object, not a graph or an unrelated finite-field
analogue.

What produces the certificate.  The support is sampled uniformly before the
syndrome is formed.  Independently, key generation chooses distinct roots and
evaluation points in F_q, computes the discrete-log matrix M, rejects until
its exact inverse modulo q-1 exists, and forms every row g_alpha=y M^{-1} as
in Proposition 1.  The public columns are rows of G followed by the d identity
columns.  Summing the planted support gives the public syndrome.  No decoder,
lattice reduction, or subset-sum search is part of generation.

Hardness and easy regimes.  Section 5 observes that d>n/2 is equivalent to a
smaller negative error, so every preset keeps d<n/2.  It gives systematic
error-search cost O(C(n-d,l)(n-d)d), l=(n-d)(d-1)/n (the source has a /t typo
in one occurrence; the Introduction and Section 6 parameter table use /n).
It also reports that Babai becomes less effective when n grows and more
effective when d grows.  The named non-demo ladder therefore keeps d=15 and
the 14-symbol answer fixed while increasing n and q.  Proposition 2 supplies
the super-polynomial/exponential BKZ cost model; there is no polynomial-time
certificate-recovery algorithm to disclose, so this is Track A, not Track B.
A 2025 cryptanalysis by Athukorala--Galbraith corrects security claims and
identifies May--Ozerov information-set decoding as the strongest decoding
attack, but does not give polynomial-time decoding.  This benchmark makes no
claim that the original encryption scheme is CCA secure.

Attacks.  Plants and decoys are coordinates of the same public code and the
support is uniform after permutation.  The per-column outlier attack selects
unusually small centered columns; greedy residual descent repeatedly takes the
column nearest the remaining syndrome; random restart samples 256 legal
supports; and the domain attack is the paper's systematic error search, capped
at 50,000 combinations around the expected non-pivot error count.  The last
attack exposes the recognizable identity columns and exactly completes each
guess from them.  Its complete layer has about C(n-d,round((n-d)(d-1)/n))
nodes at shipping size, so the cap is reported rather than confused with a
complete proof of failure.  Stronger May--Ozerov ISD and production BKZ/fplll
were not available under the standard-library-only constraint and are explicit
README caveats.

Canonicalization.  The problem is invariant under arbitrary coordinate
renumbering: permute columns and carry every support index through the inverse
permutation.  canonical_key sorts the exact column multiset and retains the
syndrome, modulus, dimension and weight.  selftest checks arbitrary
permutations, compositions, carried witnesses, and unrelated seeds.  It does
not canonicalize invertible changes of basis in syndrome space; that stronger
code-equivalence problem is deliberately listed as a caveat.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 100_000
_SYSTEMATIC_NODE_CAP = 50_000


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(after: int) -> int:
    candidate = max(2, after + 1)
    if candidate > 2 and candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 1 if candidate == 2 else 2
    return candidate


def _prime_divisors(value: int) -> list[int]:
    result = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            result.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1 if divisor == 2 else 2
    if value > 1:
        result.append(value)
    return result


def _primitive_root(prime: int) -> int:
    factors = _prime_divisors(prime - 1)
    for candidate in range(2, prime):
        if all(pow(candidate, (prime - 1) // p, prime) != 1 for p in factors):
            return candidate
    raise AssertionError("prime field has no primitive root")


def _discrete_log_table(prime: int, generator: int) -> list[int]:
    table = [-1] * prime
    value = 1
    for exponent in range(prime - 1):
        table[value] = exponent
        value = value * generator % prime
    if any(table[value] < 0 for value in range(1, prime)):
        raise AssertionError("primitive-root table is incomplete")
    return table


def _invert_matrix_mod(matrix: list[list[int]], modulus: int) -> list[list[int]] | None:
    """Gauss-Jordan inverse when unit pivots are exposed by row swaps.

    Rejection here is harmless: accepted matrices have a checked two-sided
    inverse, exactly the condition needed by Proposition 1.  This deliberately
    avoids claiming that every invertible matrix over a composite ring is found
    by this particular elimination order.
    """
    size = len(matrix)
    aug = [
        [entry % modulus for entry in row]
        + [1 if i == j else 0 for j in range(size)]
        for i, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = next(
            (r for r in range(column, size)
             if math.gcd(aug[r][column], modulus) == 1),
            None,
        )
        if pivot is None:
            return None
        aug[column], aug[pivot] = aug[pivot], aug[column]
        inverse = pow(aug[column][column], -1, modulus)
        aug[column] = [(value * inverse) % modulus for value in aug[column]]
        for row in range(size):
            if row == column:
                continue
            factor = aug[row][column]
            if factor:
                aug[row] = [
                    (left - factor * right) % modulus
                    for left, right in zip(aug[row], aug[column])
                ]
    result = [row[size:] for row in aug]
    # Check both sides.  This is key-generation validation, not witness search.
    for left, right in ((matrix, result), (result, matrix)):
        for i in range(size):
            for j in range(size):
                value = sum(left[i][k] * right[k][j] for k in range(size)) % modulus
                if value != (1 if i == j else 0):
                    return None
    return result


def _row_times_matrix(row: list[int], matrix: list[list[int]], modulus: int) -> list[int]:
    return [
        sum(row[k] * matrix[k][j] for k in range(len(row))) % modulus
        for j in range(len(matrix))
    ]


def _construct_polynomial_columns(
    n: int, d: int, field_slack: int, rng: random.Random
) -> tuple[int, list[list[int]], int]:
    """Construct P=[G^T|I] from Proposition 1 with d=t,d0=1."""
    q = _next_prime(n + d + field_slack)
    modulus = q - 1
    generator = _primitive_root(q)
    logs = _discrete_log_table(q, generator)

    for attempt in range(1, 2_001):
        field_values = list(range(q))
        rng.shuffle(field_values)
        roots = field_values[:d]
        alphas = field_values[d:d + n]
        anchors = alphas[n - d:]
        discrete_log_matrix = [
            [logs[(root - alpha) % q] for root in roots]
            for alpha in anchors
        ]
        matrix_inverse = _invert_matrix_mod(discrete_log_matrix, modulus)
        if matrix_inverse is None:
            continue

        columns = []
        for alpha in alphas[:n - d]:
            y = [logs[(root - alpha) % q] for root in roots]
            # This is g_alpha=y M^{-1}.  Since H=[I|-G], the parity
            # check P=[G^T|I] has g_alpha itself as a column.
            columns.append(_row_times_matrix(y, matrix_inverse, modulus))
        for j in range(d):
            columns.append([1 if i == j else 0 for i in range(d)])
        if len(columns) != n:
            raise AssertionError("wrong public column count")
        return q, columns, attempt
    raise RuntimeError("could not construct an invertible polynomial-lattice key")


def make_instance(
    n: int,
    seed: int = 0,
    d: int = 15,
    field_slack: int = 0,
    **params: Any,
) -> dict:
    """Inverse-generate a fixed-weight polynomial-lattice decoding instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("d", d), ("field_slack", field_slack), ("seed", seed)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if d < 2:
        raise ValueError("d must be at least 2")
    if n <= 2 * d:
        raise ValueError("the paper's hard-side regime requires n>2d")
    if field_slack < 0:
        raise ValueError("field_slack must be nonnegative")

    rng = random.Random(seed)
    q, columns, attempts = _construct_polynomial_columns(n, d, field_slack, rng)

    # The coordinate permutation is explicitly allowed in Section 4.  Plant
    # after permutation so support and non-support coordinates have precisely
    # the same marginal distribution.
    rng.shuffle(columns)
    weight = d - 1
    support = sorted(rng.sample(range(n), weight))
    modulus = q - 1
    syndrome = [0] * d
    for index in support:
        column = columns[index]
        for j in range(d):
            syndrome[j] = (syndrome[j] + column[j]) % modulus

    return {
        "family": "fixed-weight decoding in a polynomial-lattice code",
        "paper": "arXiv:1710.02265",
        "n": n,
        "d": d,
        "weight": weight,
        "q": q,
        "modulus": modulus,
        "field_slack": field_slack,
        "columns": columns,
        "syndrome": syndrome,
        "key_generation_attempts": attempts,
        "answer": support,
    }


def render(inst: dict) -> str:
    """Render a complete exact decoding problem and its output contract."""
    rows = "\n".join(
        f"{index}: " + " ".join(str(value) for value in column)
        for index, column in enumerate(inst["columns"])
    )
    statement = f"""Polynomial-lattice fixed-weight decoding

All arithmetic below is in the finite ring Z/{inst['modulus']}Z.  Every listed
integer denotes its residue modulo {inst['modulus']}.  There are {inst['n']}
columns p_0,...,p_{inst['n'] - 1}, each a vector of length {inst['d']}.

These columns are the parity-check dual of a systematic polynomial-lattice
public map H=[I|-G]: if a public output has the form c=mH+e, multiplication by
the parity check removes the unknown message m and gives the displayed
syndrome.  The binary error e has exactly {inst['weight']} entries equal to 1
and every other entry 0.

Find the support S of e.  Equivalently, find exactly {inst['weight']} distinct
indices S such that

    sum(p_i for i in S) = syndrome  (coordinatewise modulo {inst['modulus']}).

Indices are zero-based, from 0 through {inst['n'] - 1}, inclusive.  Repeats are
not allowed.  Output the indices in strictly increasing order.  Column order is
part of this instance.  All data are exact.

modulus: {inst['modulus']}
syndrome: {' '.join(str(value) for value in inst['syndrome'])}
columns (index: {inst['d']} coordinates):
{rows}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{inst['weight']} increasing integers.
Example format: <answer>[0, 3, 9]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: object) -> object | None:
    """Extract the last tagged JSON integer list, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any legal support by an exact modular column sum."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["weight"]:
        return False, f"support must contain exactly {inst['weight']} indices"
    if any(isinstance(index, bool) or not isinstance(index, int) for index in answer):
        return False, "every support entry must be an integer"
    if len(set(answer)) != len(answer):
        return False, "repeated indices are not allowed"
    if any(index < 0 or index >= inst["n"] for index in answer):
        return False, f"support index must lie in 0..{inst['n'] - 1}"
    if answer != sorted(answer):
        return False, "indices must be in strictly increasing order"

    total = [0] * inst["d"]
    modulus = inst["modulus"]
    for index in answer:
        column = inst["columns"][index]
        for j in range(inst["d"]):
            total[j] = (total[j] + column[j]) % modulus
    if total != inst["syndrome"]:
        return False, "selected columns do not sum to the syndrome"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the full legal fixed-weight support language."""
    return sorted(rng.sample(range(inst["n"]), inst["weight"]))


def search_space(inst: dict) -> int:
    """Count all fixed-weight binary supports exactly."""
    return math.comb(inst["n"], inst["weight"])


def enumerate_all(inst: dict) -> int | None:
    """Count valid witnesses exactly when the legal language is genuinely small."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    return sum(
        1
        for combo in itertools.combinations(range(inst["n"]), inst["weight"])
        if verify(inst, list(combo))[0]
    )


def canonical_key(inst: dict) -> str:
    """Canonicalize arbitrary coordinate/column relabellings."""
    payload = {
        "modulus": inst["modulus"],
        "d": inst["d"],
        "weight": inst["weight"],
        "syndrome": inst["syndrome"],
        "columns": sorted(tuple(column) for column in inst["columns"]),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow coordinates and residue range while keeping the 14-index witness fixed."""
    clean = {key: value for key, value in params.items() if key != "_preset"}
    n = int(clean["n"])
    d = int(clean.get("d", 15))
    field_slack = int(clean.get("field_slack", 0))
    # Both axes increase the haystack or suppress accidental collisions; d and
    # therefore answer length remain fixed.  There is no certificate-size cap.
    return {"n": n + 200, "d": d, "field_slack": field_slack + 240}


def _centered(value: int, modulus: int) -> int:
    value %= modulus
    return min(value, modulus - value)


def _outlier_attack(inst: dict) -> list[int]:
    """Pick columns with smallest centered L1 norm."""
    ranked = sorted(
        range(inst["n"]),
        key=lambda i: (
            sum(_centered(value, inst["modulus"]) for value in inst["columns"][i]),
            i,
        ),
    )
    return sorted(ranked[:inst["weight"]])


def _greedy_residual_attack(inst: dict) -> list[int]:
    """Greedily minimize centered distance to the remaining syndrome."""
    modulus = inst["modulus"]
    total = [0] * inst["d"]
    available = set(range(inst["n"]))
    chosen = []
    for _ in range(inst["weight"]):
        def score(index: int) -> tuple[int, int]:
            column = inst["columns"][index]
            distance = sum(
                _centered(total[j] + column[j] - inst["syndrome"][j], modulus)
                for j in range(inst["d"])
            )
            return distance, index

        best = min(available, key=score)
        available.remove(best)
        chosen.append(best)
        for j in range(inst["d"]):
            total[j] = (total[j] + inst["columns"][best][j]) % modulus
    return sorted(chosen)


def _random_restart_attack(inst: dict, seed: int, restarts: int = 256) -> list[int] | None:
    rng = random.Random(seed ^ 0x171002265)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _identity_basis(inst: dict) -> list[int] | None:
    """Find one visibly systematic identity column for every syndrome row."""
    basis = []
    used = set()
    for row in range(inst["d"]):
        unit = tuple(1 if j == row else 0 for j in range(inst["d"]))
        index = next(
            (i for i, column in enumerate(inst["columns"])
             if i not in used and tuple(column) == unit),
            None,
        )
        if index is None:
            return None
        basis.append(index)
        used.add(index)
    return basis


def _systematic_error_search(
    inst: dict, node_cap: int = _SYSTEMATIC_NODE_CAP
) -> tuple[list[int] | None, int, int, float]:
    """The Section-5 systematic decoder, stopped after a measured node cap."""
    started = time.perf_counter()
    basis = _identity_basis(inst)
    if basis is None:
        return None, 0, 0, time.perf_counter() - started
    basis_set = set(basis)
    ordinary = [i for i in range(inst["n"]) if i not in basis_set]
    expected = round(len(ordinary) * inst["weight"] / inst["n"])
    layer_order = sorted(range(inst["weight"] + 1), key=lambda r: (abs(r - expected), -r))
    modulus = inst["modulus"]
    nodes = 0
    operations = 0
    for size in layer_order:
        for combo in itertools.combinations(ordinary, size):
            nodes += 1
            partial = [0] * inst["d"]
            for index in combo:
                column = inst["columns"][index]
                for j in range(inst["d"]):
                    partial[j] = (partial[j] + column[j]) % modulus
                    operations += 1
            residual = [
                (inst["syndrome"][j] - partial[j]) % modulus
                for j in range(inst["d"])
            ]
            operations += inst["d"]
            if all(value in (0, 1) for value in residual):
                candidate = sorted(
                    list(combo) + [basis[j] for j, value in enumerate(residual) if value]
                )
                if len(candidate) == inst["weight"] and verify(inst, candidate)[0]:
                    return candidate, nodes, operations, time.perf_counter() - started
            if nodes >= node_cap:
                return None, nodes, operations, time.perf_counter() - started
    return None, nodes, operations, time.perf_counter() - started


def _permute_instance(inst: dict, permutation: list[int]) -> dict:
    """Apply new-position -> old-position coordinate permutation and carry support."""
    if sorted(permutation) != list(range(inst["n"])):
        raise ValueError("not a permutation")
    inverse = [0] * inst["n"]
    for new, old in enumerate(permutation):
        inverse[old] = new
    out = dict(inst)
    out["columns"] = [list(inst["columns"][old]) for old in permutation]
    out["syndrome"] = list(inst["syndrome"])
    out["answer"] = sorted(inverse[index] for index in inst["answer"])
    return out


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run all nine correctness, hardness, diversity and suitability gates."""
    report: dict[str, object] = {}

    # G1: construction and JSON safety across every named rung.
    g1_failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 2025):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)

    # G2: five syntactically different corruptions must reach distinct reasons.
    base = list(inst["answer"])
    swapped = list(base)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = list(base)
    duplicate[1] = duplicate[0]
    outside = list(base)
    outside[-1] = inst["n"]
    corruptions = {
        "drop_one": base[:-1],
        "swap_adjacent": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": outside,
    }
    g2_cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in g2_cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in g2_cases.values()) and len(set(reasons)) == 5,
        "cases": g2_cases,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and a markdown fence inside the required tags.
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    response = (
        "I reduced the public map to its exact modular syndrome.\n"
        f"<answer>```json\n{answer_blob}\n```</answer>\n"
        "The indices above are zero-based."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_exactly": parsed == inst["answer"],
    }

    # G4/G5 density at the actual shipping preset.  random_candidate already
    # enforces length, distinctness, range, sorting and binary fixed weight.
    samples = 200_000
    sample_rng = random.Random(0x171002265)
    hits = 0
    sample_started = time.perf_counter()
    for _ in range(samples):
        if verify(inst, random_candidate(inst, sample_rng))[0]:
            hits += 1
    density_elapsed = time.perf_counter() - sample_started
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware": True,
        "candidate_space": str(search_space(inst)),
        "wall_clock_sec": round(density_elapsed, 6),
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_solution_count = enumerate_all(demo_inst)

    baseline_records = []
    baseline_successes = 0
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **shipping_params)
        candidate, nodes, operations, elapsed = _systematic_error_search(attack_inst)
        solved = candidate is not None and verify(attack_inst, candidate)[0]
        baseline_successes += int(solved)
        baseline_records.append({
            "seed": 10_000 + seed,
            "solved": solved,
            "nodes": nodes,
            "operations": operations,
            "wall_clock_sec": round(elapsed, 6),
        })
    node_values = [record["nodes"] for record in baseline_records]
    operation_values = [record["operations"] for record in baseline_records]
    time_values = [record["wall_clock_sec"] for record in baseline_records]
    report["G5_density_and_baseline_cost"] = {
        "pass": hits / samples < 1e-6 and baseline_successes == 0 and demo_solution_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_fraction": hits / samples,
        "exact_demo_solution_count": demo_solution_count,
        "exact_demo_candidate_space": search_space(demo_inst),
        "baseline_attack": "Section-5 systematic error search",
        "baseline_successes": baseline_successes,
        "baseline_attempts": 8,
        "baseline_nodes_median": int(statistics.median(node_values)),
        "baseline_operations_median": int(statistics.median(operation_values)),
        "baseline_wall_clock_sec_median": round(statistics.median(time_values), 6),
        "baseline_wall_clock_sec_max": round(max(time_values), 6),
        "records": baseline_records,
    }

    # G6: three construction probes plus the paper's domain-standard decoder.
    attack_results = {
        "outlier_centered_column_norm": {"successes": 0, "attempts": 8},
        "greedy_centered_residual": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "systematic_error_search_50000": {"successes": baseline_successes, "attempts": 8},
    }
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **shipping_params)
        candidates = {
            "outlier_centered_column_norm": _outlier_attack(attack_inst),
            "greedy_centered_residual": _greedy_residual_attack(attack_inst),
            "random_restart_256": _random_restart_attack(attack_inst, seed),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "domain_attack_full_layer": (
            f"C({inst['n'] - inst['d']},"
            f"{round((inst['n'] - inst['d']) * inst['weight'] / inst['n'])})"
        ),
        "domain_attack_node_cap": _SYSTEMATIC_NODE_CAP,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["field_slack"] += 200
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"] and doubled["weight"] == inst["weight"],
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_answer_elements": len(inst["answer"]),
        "doubled_answer_elements": len(doubled["answer"]),
        "doubled_verification": doubled_reason,
        "escalation_axes": ["n", "field_slack"],
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=30_000 + seed, **shipping_params)
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        first = list(range(original["n"]))
        random.Random(seed ^ 0xC0FFEE).shuffle(first)
        transformed = _permute_instance(original, first)
        if canonical_key(transformed) == original_key:
            invariant_checks += 1
        if verify(transformed, transformed["answer"])[0]:
            carried_checks += 1

        second = list(range(original["n"]))
        random.Random(seed ^ 0xBAD5EED).shuffle(second)
        composed = _permute_instance(transformed, second)
        if canonical_key(composed) != original_key:
            invariant_checks -= 1000
        if not verify(composed, composed["answer"])[0]:
            carried_checks -= 1000
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 20 and carried_checks == 20 and distinct_keys == 20,
        "invariant_relabelings_and_compositions": invariant_checks,
        "valid_carried_witnesses": carried_checks,
        "distinct_unrelated_keys": distinct_keys,
        "unrelated_attempts": 20,
        "key_kind": "sorted exact column multiset plus syndrome and ring parameters",
    }

    answer_chars = len(json.dumps(inst["answer"], separators=(",", ":")))
    answer_elements = _answer_atoms(inst["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    # Once the support is identified, exact confirmation is one d-vector add
    # per selected coordinate plus d final comparisons.
    intended_operations = inst["weight"] * inst["d"] + inst["d"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    hinted_rate = arms["hinted"].get("solved", 0) / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"].get("solved", 0) / placebo_attempts if placebo_attempts else 0.0
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and answer_tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    hinted_hardened = G9_ORACLE_RESULTS.get("hinted_verdict") == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "pending"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "measured_worst_case_answer_tokens": PROBLEM_PROFILE["max_answer_tokens"],
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
