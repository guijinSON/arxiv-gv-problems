"""Verified problem generator for arXiv:1701.06906.

The task is the finite-field coefficient identity used in the proof of Lemma
2.6.  Solvers recover selected coefficients of

    sum_{r=0}^{p-1} ((1+u)(1+v))^r

after exact blockwise changes of coefficient coordinates.  The generator uses
the paper's identity to know the coefficient matrix by construction; it never
expands or solves the generated instance.
"""

from __future__ import annotations

import itertools
import json
import os
import random
import re
import sys
import time

# Make the repository helpers available when this file is invoked from its own
# result directory.  The family itself uses only prime-field integer arithmetic
# and remains standard-library-only if gvlib is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - documented dependency-free path
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "bivariate polynomial over a prime field",
        "queried monomial coefficients",
        "blockwise coefficient-basis matrices over the prime field",
    ],
    "verification_operations": [
        "exact total-degree and parity comparison",
        "exact 2 by 2 finite-field matrix-vector multiplication",
        "exact coefficient-matrix comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Writing (1+u)(1+v)=1+(u+v+uv) turns the long power sum into a "
        "single characteristic-p power, whose low-total-degree support is rigid."
    ),
    "hardness_basis": (
        "Track B: direct factorial-recurrence coefficient accumulation is "
        "O(kp) and, at the hard shipping preset (p=100403, k=64), the reference "
        "run used 12,825,889 counted operations and 1.359 seconds; "
        "the Lemma 2.6 generating-function identity reduces this to at most 288 "
        "exact comparisons and field operations, but that identity must be found "
        "and executed without a CAS or sandbox."
    ),
    "max_answer_tokens": 106,
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
    "demo": {"n": 7, "k": 4},
    "easy": {"n": 1009, "k": 64},
    "medium": {"n": 10007, "k": 64},
    "hard": {"n": 100003, "k": 64},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A (k/2)-by-2 coefficient matrix over F_p in the displayed blockwise "
        "coefficient bases: exactly k field entries, each in 0,...,p-1."
    ),
    "bounds": {
        "rows_at_shipping": 32,
        "columns": 2,
        "atomic_entries_at_shipping": 64,
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "basis": "the ordered output coordinates of the displayed 2 by 2 blocks",
    },
}

STRUCTURAL_HINT = (
    "The product (1+u)(1+v) differs from 1 by the three-term polynomial "
    "u+v+uv, whose powers have a rigid low-total-degree support."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the query order and all modular signs helps avoid "
    "small coefficient and indexing mistakes."
)

# Filled after the separately isolated harden.py runs.  These oracle arms are
# diagnostics; G9's actual pass flag is determined only by the size/effort caps.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 2, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "blocked_api_key_limit",
}

NOTES = """\
The definition comes from Section 2, Lemma 2.5 and the proof of Lemma 2.6:
C(i,j) is the coefficient of u^i v^j in the displayed sum of
(1+u)^r(1+v)^r.  The proof's characteristic-p identity turns that sum into
(u+v+uv)^(p-1), and for queried total degree at most p-1 only the (u+v)^(p-1)
part can contribute.  Thus the planted coefficient is 0 below the boundary and
(-1)^i on it.  This is also the paper's efficient route, so the family is Track
B, not Track A.

The prior group-enumeration triage is not used: Corollary 2.10, Remark 2.11, and
Theorems 2.12--2.16 make the natural Beauville-pair witness abundant and directly
constructible, so that candidate fails Track-A hardness and structure-aware guess
resistance.  The coefficient identity still has a genuine Track-B compression gap.

The generator mixes pairs of true coefficients through independently sampled
invertible 2 by 2 matrices.  This preserves the native coefficient object and
keeps the 32-by-2 answer fixed while p grows.  The mixing defeats the all-zero,
all-one, unsigned-boundary, and parity-everywhere shortcuts; uniform restarts
sample the full statement-visible coefficient language.  The disclosed
reference algorithm evaluates every requested binomial sum by factorial and
recurrence, while the intended route recognizes the paper's polynomial
identity and performs only the small block multiplications.
"""


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for the 64-bit range used by the ladder."""
    n = int(value)
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for q in small:
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _next_prime(start: int) -> int:
    q = max(7, int(start))
    if q % 2 == 0:
        q += 1
    while not _is_prime(q):
        q += 2
    return q


def _mat_vec(matrix, vector, p: int) -> list[int]:
    return [
        (matrix[0][0] * vector[0] + matrix[0][1] * vector[1]) % p,
        (matrix[1][0] * vector[0] + matrix[1][1] * vector[1]) % p,
    ]


def _det2(matrix, p: int) -> int:
    return (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) % p


def _random_gl2(rng: random.Random, p: int) -> list[list[int]]:
    while True:
        matrix = [[rng.randrange(p), rng.randrange(p)],
                  [rng.randrange(p), rng.randrange(p)]]
        if _det2(matrix, p):
            return matrix


def _native_coefficient(pair, p: int) -> int:
    """Lemma 2.6 proof identity for positive i,j and i+j <= p-1."""
    i, j = pair
    if i + j < p - 1:
        return 0
    return 1 if i % 2 == 0 else p - 1


def _sample_queries(p: int, k: int, rng: random.Random) -> list[tuple[int, int]]:
    """Mix boundary coefficients of both signs with strict-interior zeros."""
    boundary_needed = k // 2
    interior_needed = k - boundary_needed
    boundary: set[tuple[int, int]] = set()
    interior: set[tuple[int, int]] = set()

    # Force both nonzero signs, plus zeros, before filling from the same
    # distribution used for the remaining members of each stated stratum.
    for i in (1, 2):
        if 1 <= i <= p - 2:
            boundary.add(tuple(sorted((i, p - 1 - i))))

    while len(boundary) < boundary_needed:
        i = rng.randrange(1, p - 1)
        boundary.add(tuple(sorted((i, p - 1 - i))))

    interior.add((1, 1))
    while len(interior) < interior_needed:
        i = rng.randrange(1, p - 2)
        j = rng.randrange(1, p - 1 - i)
        interior.add(tuple(sorted((i, j))))

    queries = list(boundary)[:boundary_needed] + list(interior)[:interior_needed]
    rng.shuffle(queries)
    return queries


def make_instance(n, seed=0, **params) -> dict:
    """Build queried coefficients using the theorem-backed identity.

    ``n`` is a lower scale for the prime p; increasing it lengthens the literal
    coefficient accumulation while ``k`` and hence the witness length stay fixed.
    """
    n = int(n)
    k = int(params.get("k", 64))
    if n < 7:
        raise ValueError("n must be at least 7")
    if k < 4 or k % 2:
        raise ValueError("k must be an even integer at least 4")
    rng = random.Random(seed)
    jitter = max(2, n // 50)
    p = _next_prime(n + rng.randrange(jitter))
    if k // 2 > (p - 2) // 2:
        raise ValueError("p is too small for k distinct symmetric boundary queries")

    queries = _sample_queries(p, k, rng)
    blocks = []
    answer = []
    for b in range(k // 2):
        pair_queries = [list(queries[2 * b]), list(queries[2 * b + 1])]
        matrix = _random_gl2(rng, p)
        source = [_native_coefficient(q, p) for q in pair_queries]
        transformed = _mat_vec(matrix, source, p)
        blocks.append({"queries": pair_queries, "matrix": matrix})
        answer.append(transformed)

    return {
        "paper": "1701.06906",
        "p": p,
        "k": k,
        "blocks": blocks,
        "answer": answer,
    }


def render(inst) -> str:
    p, k = inst["p"], inst["k"]
    lines = [
        "Recover selected coefficients of a bivariate polynomial over a prime field.",
        "",
        f"Let p={p}. All arithmetic is in F_p, represented by the integers "
        f"0,...,{p-1} modulo p.",
        "For nonnegative integers r and s, binom(r,s)=0 when s>r and otherwise",
        "binom(r,s)=r!/(s!(r-s)!) as an ordinary integer, reduced modulo p.",
        "Define the polynomial",
        "  P(u,v) = sum_{r=0}^{p-1} (1+u)^r (1+v)^r  in F_p[u,v].",
        "For each query (i,j), let c(i,j) be the coefficient of u^i v^j in P.",
        "Equivalently, and this is a direct mechanical definition,",
        "  c(i,j) = sum_{r=0}^{p-1} binom(r,i) binom(r,j) mod p.",
        "Every displayed query has i>=1, j>=1, and i+j<=p-1.",
        "",
        f"There are {k // 2} independent blocks.  In block b, form the two-entry column",
        "from its two queried coefficients in the displayed order, multiply it on the left",
        "by the displayed 2 by 2 matrix, and reduce both outputs modulo p.",
        "Use the two outputs from block b as row b of the answer matrix.",
        "Rows and columns of every matrix are 0-indexed; order within each block matters.",
        "",
        "Block data (b: query1 ; query2 ; matrix [[a,b],[c,d]]):",
    ]
    for b, block in enumerate(inst["blocks"]):
        q1, q2 = block["queries"]
        lines.append(
            f"  {b}: ({q1[0]},{q1[1]}) ; ({q2[0]},{q2[1]}) ; "
            f"{json.dumps(block['matrix'], separators=(',', ':'))}"
        )
    lines += [
        "",
        f"Return exactly {k // 2} rows of two integers in 0,...,{p-1}, as a JSON matrix.",
        "Row b must contain the two coordinates of block b in their displayed order.",
        "Repetitions and zero entries are allowed.",
        "Give your final answer inside <answer></answer> tags, as that JSON array.",
        f"Example format only: <answer>{json.dumps([[0, 0] for _ in range(k // 2)])}</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    """Parse the last tagged JSON payload, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    if any(not isinstance(row, list) for row in answer):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int)
           for row in answer for x in row):
        return None
    return answer


def _expected(inst) -> list[list[int]]:
    p = inst["p"]
    output = []
    for block in inst["blocks"]:
        source = [_native_coefficient(pair, p) for pair in block["queries"]]
        output.append(_mat_vec(block["matrix"], source, p))
    return output


def verify(inst, answer) -> tuple[bool, str]:
    """Check a coefficient witness exactly without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer must not be empty"
    k, p = inst["k"], inst["p"]
    if len(answer) != k // 2:
        return False, f"expected exactly {k // 2} output rows"
    for block_index, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 2:
            return False, f"row {block_index} must contain exactly two coordinates"
        for coordinate, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int):
                return False, f"block {block_index} coordinate {coordinate} is not an integer"
            if not 0 <= value < p:
                return False, (
                    f"block {block_index} coordinate {coordinate} is outside 0,...,{p-1}"
                )
    expected = _expected(inst)
    for block_index, (got_row, want_row) in enumerate(zip(answer, expected)):
        for coordinate, (got, want) in enumerate(zip(got_row, want_row)):
            if got != want:
                return False, (
                    f"block {block_index} coordinate {coordinate} does not match "
                    "the exact coefficient identity"
                )
    return True, "ok"


def random_candidate(inst, rng) -> list[list[int]]:
    """Uniformly sample the statement-visible fixed-shape coefficient space."""
    return [
        [rng.randrange(inst["p"]), rng.randrange(inst["p"])]
        for _ in range(inst["k"] // 2)
    ]


def search_space(inst) -> int:
    return inst["p"] ** inst["k"]


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for candidate in itertools.product(range(inst["p"]), repeat=inst["k"]):
        matrix = [list(candidate[i:i + 2]) for i in range(0, inst["k"], 2)]
        if verify(inst, matrix)[0]:
            count += 1
    return count


def canonical_key(inst) -> str:
    """Canonicalize query order, u/v exchange, and output-coordinate bases.

    Each block matrix is invertible, so left changes of its output basis carry
    witnesses but add no new coefficient problem.  A block is consequently
    determined by its unordered pair of unordered monomial exponents.
    """
    canonical_blocks = []
    for block in inst["blocks"]:
        queries = [tuple(sorted((int(q[0]), int(q[1])))) for q in block["queries"]]
        canonical_blocks.append(tuple(sorted(queries)))
    canonical_blocks.sort()
    return json.dumps([int(inst["p"]), canonical_blocks], separators=(",", ":"))


def escalate(params) -> dict | str:
    """Raise p tenfold at fixed shape, or report the eventual answer cap."""
    next_n = int(params["n"]) * 10
    k = int(params.get("k", 64))
    # The sampled start is below 1.02*next_n, and Bertrand's postulate puts the
    # next prime below twice that.  Three times next_n is therefore a safe digit
    # bound.  A compact (k/2)-by-2 JSON matrix needs at most k*d+2*k+1 chars
    # when every residue has d digits.
    residue_digits = len(str(3 * next_n))
    worst_answer_chars = k * residue_digits + 2 * k + 1
    if worst_answer_chars > 2_000:
        return "cap_bound"
    return {"n": next_n, "k": k}


def _attack_vector(inst, source_rule) -> list[list[int]]:
    p = inst["p"]
    out = []
    for block in inst["blocks"]:
        source = [source_rule(q, p) % p for q in block["queries"]]
        out.append(_mat_vec(block["matrix"], source, p))
    return out


def _attacks(inst, seed: int) -> dict[str, list[list[int]]]:
    p, k = inst["p"], inst["k"]
    rng = random.Random(seed ^ 0x6A09E667)
    return {
        "all_source_coefficients_zero": _attack_vector(inst, lambda q, mod: 0),
        "all_source_coefficients_one": _attack_vector(inst, lambda q, mod: 1),
        "unsigned_boundary_only": _attack_vector(
            inst, lambda q, mod: 1 if q[0] + q[1] == mod - 1 else 0
        ),
        "parity_on_every_query": _attack_vector(
            inst, lambda q, mod: 1 if q[0] % 2 == 0 else mod - 1
        ),
        "uniform_random_coefficient_matrix": [
            [rng.randrange(p), rng.randrange(p)] for _ in range(k // 2)
        ],
    }


def _factorial_tables(p: int):
    fac = [1] * p
    for i in range(1, p):
        fac[i] = fac[i - 1] * i % p
    invfac = [1] * p
    invfac[p - 1] = pow(fac[p - 1], p - 2, p)
    for i in range(p - 1, 0, -1):
        invfac[i - 1] = invfac[i] * i % p
    inv = [0] * p
    inv[1] = 1
    for i in range(2, p):
        inv[i] = (p - (p // i) * inv[p % i] % p) % p
    return fac, invfac, inv


def _comb_from_tables(n: int, r: int, p: int, fac, invfac) -> int:
    if r < 0 or r > n:
        return 0
    return fac[n] * invfac[r] % p * invfac[n - r] % p


def _reference_direct(inst) -> tuple[list[list[int]], int, int]:
    """Literal O(kp) binomial-sum evaluation; return answer, terms, field ops."""
    p = inst["p"]
    fac, invfac, inv = _factorial_tables(p)
    native = []
    terms = 0
    # Count factorial, inverse-factorial, and inverse-table preparation
    # conservatively as five exact modular/integer operations per field element.
    operations = 5 * p
    for block in inst["blocks"]:
        for i, j in block["queries"]:
            r0 = max(i, j)
            bi = _comb_from_tables(r0, i, p, fac, invfac)
            bj = _comb_from_tables(r0, j, p, fac, invfac)
            total = 0
            operations += 4
            for r in range(r0, p):
                total = (total + bi * bj) % p
                terms += 1
                operations += 2
                if r + 1 < p:
                    bi = bi * (r + 1) % p * inv[r + 1 - i] % p
                    bj = bj * (r + 1) % p * inv[r + 1 - j] % p
                    operations += 4
            native.append(total)
    output = []
    for block_index, block in enumerate(inst["blocks"]):
        output.append(
            _mat_vec(block["matrix"], native[2 * block_index:2 * block_index + 2], p)
        )
        operations += 6
    return output, terms, operations


def _transform_instance(inst, rng: random.Random):
    """Apply all declared relabellings and carry the witness through them."""
    p = inst["p"]
    new_blocks = []
    new_answer_blocks = []
    old_answer = inst["answer"]
    for b, block in enumerate(inst["blocks"]):
        queries = [list(q) for q in block["queries"]]
        matrix = [list(row) for row in block["matrix"]]

        # Global u/v exchange preserves every coefficient of this symmetric P.
        queries = [[q[1], q[0]] for q in queries]

        # Swap the two source-coordinate names and the corresponding columns.
        if rng.randrange(2):
            queries.reverse()
            matrix = [[row[1], row[0]] for row in matrix]

        # Relabel the two output coordinates by an arbitrary GL(2,p) basis.
        left = _random_gl2(rng, p)
        changed = [
            [sum(left[r][s] * matrix[s][c] for s in range(2)) % p for c in range(2)]
            for r in range(2)
        ]
        carried = _mat_vec(left, old_answer[b], p)
        new_blocks.append({"queries": queries, "matrix": changed})
        new_answer_blocks.append(carried)

    order = list(range(len(new_blocks)))
    rng.shuffle(order)
    shuffled_blocks = [new_blocks[i] for i in order]
    shuffled_answer = [new_answer_blocks[i] for i in order]
    transformed = {
        "paper": inst["paper"],
        "p": p,
        "k": inst["k"],
        "blocks": shuffled_blocks,
        "answer": shuffled_answer,
    }
    return transformed


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report = {}

    # G1: every rung and several independently generated instances.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 1729):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "attempts": g1_attempts, "failures": g1_failures
    }

    # G2: distinct, targeted failure paths.
    inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = [list(row) for row in inst["answer"]]
    positions = [(b, c) for b in range(len(answer)) for c in range(2)]
    source = positions[0]
    swap_pos = next(pos for pos in positions[1:]
                    if answer[pos[0]][pos[1]] != answer[source[0]][source[1]])
    duplicate_pos = next(pos for pos in positions[1:] if pos != swap_pos
                         and answer[pos[0]][pos[1]] != answer[source[0]][source[1]])
    corruptions = {}
    dropped = answer[:-1]
    corruptions["drop_one"] = verify(inst, dropped)
    swapped = [list(row) for row in answer]
    swapped[source[0]][source[1]], swapped[swap_pos[0]][swap_pos[1]] = (
        swapped[swap_pos[0]][swap_pos[1]], swapped[source[0]][source[1]]
    )
    corruptions["swap_two"] = verify(inst, swapped)
    duplicated = [list(row) for row in answer]
    duplicated[duplicate_pos[0]][duplicate_pos[1]] = answer[source[0]][source[1]]
    corruptions["duplicate_one"] = verify(inst, duplicated)
    corruptions["empty"] = verify(inst, [])
    out_of_range = [list(row) for row in answer]
    out_of_range[-1][1] = inst["p"]
    corruptions["out_of_range"] = verify(inst, out_of_range)
    reasons = [result[1] for result in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not result[0] for result in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": result[0], "reason": result[1]}
                  for name, result in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    # G3: exact model-style round trip with prose and a JSON fence.
    response = (
        "I used the characteristic-p coefficient identity.\n"
        "<answer>\n```json\n" + json.dumps(answer) + "\n```\n</answer>\n"
        "The entries are canonical residues."
    )
    parsed = parse_answer(response)
    parse_ok, parse_why = verify(inst, parsed) if parsed is not None else (False, "None")
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_ok,
        "parsed_matches": parsed == answer,
        "verify_reason": parse_why,
    }

    # G4/G5 density: structure-aware candidates already obey the exact length
    # and residue bounds stated in the prompt.
    samples = 200_000
    sample_rng = random.Random(0xC0FFEE)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, sample_rng))[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": str(search_space(inst)),
        "prior": "uniform over (k/2)-by-2 matrices in F_p^k",
    }

    start = time.perf_counter()
    reference_answer, reference_terms, reference_ops = _reference_direct(inst)
    reference_wall = time.perf_counter() - start
    reference_ok, reference_why = verify(inst, reference_answer)
    report["G5_density_and_baseline_cost"] = {
        "pass": hits / samples < 1e-6 and reference_ok,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": hits / samples,
        "exact_valid_answer_count": 1,
        "reference_wall_clock_sec": round(reference_wall, 6),
        "reference_binomial_terms": reference_terms,
        "reference_field_operations": reference_ops,
        "reference_verify_reason": reference_why,
    }

    # G6: five no-tool attacks fail; the O(kp) direct algorithm is separately
    # disclosed and expected to solve every Track-B instance.
    attack_counts = {name: 0 for name in _attacks(inst, 0)}
    attempts = 8
    reference_successes = 0
    reference_seconds = []
    reference_operations = []
    reference_terms_all = []
    for seed in range(attempts):
        trial = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attacks(trial, seed).items():
            if verify(trial, candidate)[0]:
                attack_counts[name] += 1
        t0 = time.perf_counter()
        ref, term_count, op_count = _reference_direct(trial)
        reference_seconds.append(time.perf_counter() - t0)
        reference_operations.append(op_count)
        reference_terms_all.append(term_count)
        if verify(trial, ref)[0]:
            reference_successes += 1
    attacks_report = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks_report.values()),
        "attacks": attacks_report,
        "reference_algorithm": {
            "name": "direct factorial-recurrence binomial coefficient accumulation",
            "complexity": "O(k*p) exact field operations and O(p) memory",
            "wall_clock_sec_mean": round(sum(reference_seconds) / attempts, 6),
            "wall_clock_sec_max": round(max(reference_seconds), 6),
            "operations_mean": round(sum(reference_operations) / attempts),
            "binomial_terms_mean": round(sum(reference_terms_all) / attempts),
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    # G7: the modulus/haystack grows while answer length remains fixed.
    base_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled = {"n": base_params["n"] * 2, "k": base_params["k"]}
    bigger = make_instance(seed=271828, **doubled)
    bigger_ok, bigger_why = verify(bigger, bigger["answer"])
    report["G7_scales"] = {
        "pass": bigger_ok and bigger["p"] > inst["p"]
                and _answer_atoms(bigger["answer"]) == _answer_atoms(answer),
        "shipping_p": inst["p"],
        "doubled_p": bigger["p"],
        "shipping_answer_elements": _answer_atoms(answer),
        "doubled_answer_elements": _answer_atoms(bigger["answer"]),
        "verify_reason": bigger_why,
    }

    # G8: block permutations, query swaps, u/v exchange, and GL2 output-basis
    # changes are composed in _transform_instance.
    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        original = make_instance(seed=12000 + seed, **DIFFICULTY["medium"])
        transformed = _transform_instance(original, random.Random(22000 + seed))
        if canonical_key(original) == canonical_key(transformed):
            invariant_checks += 1
        if verify(transformed, transformed["answer"])[0]:
            carried_checks += 1
        keys.append(canonical_key(original))
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 20 and carried_checks == 20 and distinct == 20,
        "invariance_checks_passed": invariant_checks,
        "carried_witness_checks_passed": carried_checks,
        "unrelated_distinct_keys": distinct,
        "unrelated_instances": 20,
        "symmetries": [
            "block permutation",
            "swap of the two queries with matrix-column swap",
            "global exchange of u and v",
            "independent GL(2,p) output-coordinate changes",
        ],
    }

    # Report the largest serialized witness observed over a broad deterministic
    # shipping-preset seed sweep, not merely the convenient G2 instance.
    answer_size_samples = 10_000
    answer_chars = 0
    answer_size_worst_seed = None
    for size_seed in range(answer_size_samples):
        size_inst = make_instance(
            seed=size_seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        chars = len(json.dumps(size_inst["answer"], separators=(",", ":")))
        if chars > answer_chars:
            answer_chars = chars
            answer_size_worst_seed = size_seed
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(answer)
    # Per query: one addition and one boundary comparison; for the 32 boundary
    # queries, one parity test.  Once the source values are known to be 0,+1,-1,
    # each of the 64 output coordinates needs at most one signed addition and one modular
    # reduction (ordinary scalar multiplications are unnecessary).  This is a
    # conservative executable count, not the earlier one-operation-per-query
    # shorthand.
    intended_ops = 2 * inst["k"] + inst["k"] // 2 + 4 * (inst["k"] // 2)
    arms = G9_RESULTS["arms"]
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "answer_size_samples": answer_size_samples,
        "answer_size_worst_seed": answer_size_worst_seed,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
