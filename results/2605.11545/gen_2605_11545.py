"""Track-B generator for the pseudo-moment rank problem of arXiv:2605.11545.

The rendered object is the degree-two pseudo-moment subspace from Section 4.
A Boolean point succinctly encodes its honest rank-one moment matrix. Public
source equations are a dense circulant linear system over GF(257): ordinary
Gaussian elimination solves it, while a hidden two-term inverse gives the
intended no-tool route.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "degree-2 pseudo-moment matrix subspace over GF(257)",
        "localizing constraints for Boolean linear equations",
        "succinct Boolean factor of a rank-one moment matrix",
    ],
    "verification_operations": [
        "binary syntax and length checks",
        "exact matrix-vector multiplication modulo 257",
        "exact localizing-identity implication x^W f(x)=0",
        "rank-one outer-product implication with nonzero empty coordinate",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4.1 and Theorem 4.1: Boolean QuadEq is mapped to the "
        "equal-union pseudo-moment subspace L_2(f_1,...,f_m)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the dense coefficient matrix as a circulant operator whose "
        "inverse is identity plus one scaled cyclic shift; otherwise one must "
        "perform dense finite-field elimination."
    ),
    "hardness_basis": (
        "Track B: dense Gaussian elimination over GF(257) solves every instance "
        "in O(n^3); at the shipping preset its measured wall-clock and exact-field "
        "operation count are reported by selftest, whereas the circulant inverse "
        "uses at most 2n+1 exact field operations once recognized."
    ),
    "max_answer_tokens": 19,
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
    "demo": {"n": 7},
    "easy": {"n": 47},
    "medium": {"n": 71},
    "hard": {"n": 97},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "Hint: The dense coefficient matrix is circulant, and its inverse is "
    "identity plus 3 times one cyclic shift."
)
PLACEBO_HINT = (
    "Hint: Keep every modular reduction exact, and preserve the stated bit "
    "order while checking the equations."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One bit string of exactly n characters in {0,1}; it encodes the Boolean "
        "factor x of H_2(x)=v_2(x)v_2(x)^T over GF(257)."
    ),
    "bounds": {
        "length": "n",
        "alphabet": [0, 1],
        "max_shipping_length": 97,
        "candidate_count": "2^n",
        "matrix_factor_rule": "v_2(x)[S] = product of x_i for i in S",
    },
}

# Filled only from script-owned hardening transcripts after those runs finish.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES = r"""
Definition and certificate. Section 2 defines squarefree Boolean monomials and
the pseudo-moment matrix H_d(y)_{S,T}=y_{S union T}. Section 4.1 fixes the exact
subspace L_d: equal-union constraints plus every localizing equation
sum_U c_{ell,U} y_{U union W}=0 for |W|<=2d-2. This module uses d=2 and the
fixed field GF(257). The solver submits a Boolean point x, a succinct factor for
the honest matrix H_2(x)=v_2(x)v_2(x)^T. The empty coordinate of v_2 is 1, so
the matrix is nonzero and rank one. Checking f_ell(x)=0 executes every required
localizing check through the exact identity x^W f_ell(x)=0.

Step-0 hardness decision. Theorem 1.2 and Theorem 4.1 are worst-case results;
they do not make an inverse-generated random subspace hard on its generated
distribution. In this module the source polynomials are deliberately linear,
so Gaussian elimination over GF(257) produces the unique certificate in
polynomial time. That disqualifies Track A and is reported openly as the Track-B
reference algorithm. The mechanical elimination cost is measured at shipping
size. The compact route notices that the dense circulant coefficient matrix A
has inverse I+3P_s. From the first row, -3 times its diagonal coefficient occurs
at the unique column s; then x_i=b_i+3b_{i+s} mod 257. This uses 2n+1 field
operations, plus comparisons to locate s.

Construction. A Boolean answer x and a nonzero cyclic shift s are sampled first.
Let P_s z have coordinate i equal to z_{i+s mod n}, put G=I+3P_s, and construct
A=G^{-1} from the finite geometric-series identity. Finally b=Ax. Thus the
rank-one certificate is known before the public right-hand side exists; it is
not obtained by solving the emitted instance. Theorem 4.1's completeness proof
then carries x to the rank-one pseudo-moment matrix.

Easy regimes and attacks. Section 1 notes that rank one is trivial in the
diagonal-code embedding, and our linear source regime is also easy with tools.
The adversary panel therefore keeps Gaussian elimination outside the failing
attacks as Track B requires. It measures a column-correlation outlier guess,
greedy exact-equation improvement, uniform random restart, and simple
right-hand-side ansatzes; the plant is uniform and the circulant columns have
identical marginal statistics, so these leave no per-coordinate plant signal.

Canonicalization. Arbitrary equation reorderings and variable renamings act as
row and column permutations of the weighted coefficient matrix. canonical_key
uses a fixed-round weighted bipartite color-refinement invariant and hashes its
canonical multisets. It is tested on row permutations, column permutations, and
their compositions with carried witnesses. General finite-field row operations
are equivalences too, but canonical equivalence of the resulting linear code is
not attempted; this strongest cheap invariant may therefore miss such duplicate
presentations, as documented in README.md.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)
_P = 257
_C = 3


def _choose_shift(n: int, rng: random.Random) -> int:
    choices = [s for s in range(1, n) if math.gcd(s, n) == 1]
    if not choices:
        raise ValueError("n has no nonzero coprime cyclic shift")
    return rng.choice(choices)


def _inverse_circulant(n: int, shift: int) -> list[list[int]]:
    """Return (I + 3 P_shift)^-1 over GF(257) by a geometric identity."""
    minus_c = (-_C) % _P
    denominator = (1 - pow(minus_c, n, _P)) % _P
    if denominator == 0:
        raise ValueError("n is a multiple of the order of -3 modulo 257")
    scale = pow(denominator, _P - 2, _P)
    first = [0] * n
    coeff = scale
    position = 0
    for _ in range(n):
        first[position] = coeff
        coeff = coeff * minus_c % _P
        position = (position + shift) % n
    return [first[-i:] + first[:-i] if i else list(first) for i in range(n)]


def _matvec(matrix: list[list[int]], vector: list[int]) -> list[int]:
    return [sum(a * x for a, x in zip(row, vector)) % _P for row in matrix]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a Boolean factor, then its paper-defined subspace.

    ``n`` is the number of Boolean variables and public linear equations. The
    pseudo-moment matrices themselves have dimension 1+n+binomial(n,2).
    Larger n enlarges the answer space, dense elimination, and rendered input.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if pow((-_C) % _P, n, _P) == 1:
        raise ValueError("n must not be a multiple of 256")

    rng = random.Random(seed)
    shift = _choose_shift(n, rng)
    planted = [rng.randrange(2) for _ in range(n)]
    matrix = _inverse_circulant(n, shift)
    rhs = _matvec(matrix, planted)
    answer = "".join(str(bit) for bit in planted)
    return {
        "family": "degree-2 pseudo-moment rank-one search over GF(257)",
        "field_prime": _P,
        "moment_degree": 2,
        "n": n,
        "moment_matrix_dimension": 1 + n + n * (n - 1) // 2,
        "coefficient_matrix": matrix,
        "rhs": rhs,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete pseudo-moment problem and its compact answer format."""
    n = inst["n"]
    rows = "\n".join(
        f"{i}: " + " ".join(str(value) for value in row)
        for i, row in enumerate(inst["coefficient_matrix"])
    )
    rhs = " ".join(str(value) for value in inst["rhs"])
    statement = f"""Rank-one pseudo-moment matrix in a linear subspace over GF(257)

All arithmetic below is modulo the prime 257. There are {n} Boolean variables
x_0,...,x_{n - 1}, so each x_j must be exactly 0 or 1. The public linear
polynomials are

    f_i(x) = sum_(j=0 to {n - 1}) A[i,j] x_j - b_i  (mod 257),

for i=0,...,{n - 1}. The coefficient matrix A is given row by row below. Row
labels and variable indices are 0-based; each row has exactly {n} entries in
the order x_0,...,x_{n - 1}.

{rows}

The right-hand side b, in row order 0,...,{n - 1}, is:
{rhs}

These data define the following degree-2 pseudo-moment matrix subspace. Let V
be all subsets S of {{0,...,{n - 1}}} with |S|<=2, including the empty set.
For one field value y_R for every subset R with |R|<=4, form the
{inst['moment_matrix_dimension']} by {inst['moment_matrix_dimension']} matrix

    H(y)[S,T] = y_(S union T),  for S,T in V.

The subspace L consists of those H(y) satisfying, for every row i and every
subset W with |W|<=2,

    sum_(j=0 to {n - 1}) A[i,j] y_(W union {{j}}) - b_i y_W = 0 (mod 257).

Find a Boolean vector x whose honest moment matrix lies in L. Your submitted
bits encode that matrix succinctly: set y_R=product_(j in R) x_j (the empty
product is 1), equivalently H(y)=v_2(x)v_2(x)^T. Thus the encoded matrix is
automatically nonzero and rank one. Membership in L is equivalent here to all
displayed equations f_i(x)=0, because each localizing left side equals
(product_(j in W) x_j) f_i(x). You need not print H(y).

Output exactly {n} bits with no spaces, in x_0,...,x_{n - 1} order. Repetitions
of bit values are allowed; characters other than 0 and 1 are forbidden.

Give your final answer inside <answer></answer> tags, as the bit string.
Example: <answer>0100110</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged bit string, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:text)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
    body = re.sub(r"\s+", "", body)
    return body if re.fullmatch(r"[01]+", body) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any succinct rank-one factor without consulting ``inst['answer']``."""
    n = inst["n"]
    if not isinstance(answer, str):
        return False, "answer must be a bit string"
    if answer == "":
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    for j, char in enumerate(answer):
        if char not in "01":
            return False, f"non-binary character at position {j}"
    vector = [ord(char) - 48 for char in answer]
    for i, (row, target) in enumerate(
        zip(inst["coefficient_matrix"], inst["rhs"])
    ):
        if sum(a * x for a, x in zip(row, vector)) % _P != target:
            return False, f"linear/localizing constraint {i} is violated"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Draw uniformly from all n-bit factors, the full stated answer language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n = inst["n"]
    return format(rng.getrandbits(n), f"0{n}b")


def search_space(inst: dict) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when at most 2^20 candidates exist."""
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for value in range(1 << n):
        candidate = format(value, f"0{n}b")
        count += int(verify(inst, candidate)[0])
    return count


def _color_hash(tag: bytes, old: bytes, entries: list[tuple[int, bytes]]) -> bytes:
    h = hashlib.sha256()
    h.update(tag)
    h.update(old)
    for value, color in sorted(entries, key=lambda item: (item[0], item[1])):
        h.update(value.to_bytes(2, "big"))
        h.update(color)
    return h.digest()


def canonical_key(inst: dict) -> str:
    """Weighted bipartite color-refinement invariant for row/column relabelling."""
    matrix = inst["coefficient_matrix"]
    rhs = inst["rhs"]
    n = inst["n"]
    row_colors = [
        hashlib.sha256(b"row" + value.to_bytes(2, "big")).digest()
        for value in rhs
    ]
    col_seed = hashlib.sha256(b"variable-column").digest()
    col_colors = [col_seed] * n
    # Fixed-round refinement is exactly permutation equivariant. Six rounds are
    # ample to individualize these dense weighted circulants with random RHS.
    for _ in range(6):
        next_rows = [
            _color_hash(
                b"R",
                row_colors[i],
                [(matrix[i][j], col_colors[j]) for j in range(n)],
            )
            for i in range(n)
        ]
        next_cols = [
            _color_hash(
                b"C",
                col_colors[j],
                [(matrix[i][j], row_colors[i]) for i in range(n)],
            )
            for j in range(n)
        ]
        row_colors, col_colors = next_rows, next_cols

    # This multiset is invariant even if refinement leaves tied color classes.
    outer = hashlib.sha256()
    outer.update(f"p={inst['field_prime']};n={n};d={inst['moment_degree']}".encode())
    for color in sorted(row_colors):
        outer.update(b"R" + color)
    for color in sorted(col_colors):
        outer.update(b"C" + color)
    edge_types = sorted(
        row_colors[i] + col_colors[j] + matrix[i][j].to_bytes(2, "big")
        for i in range(n)
        for j in range(n)
    )
    for edge in edge_types:
        outer.update(b"E" + edge)
    return outer.hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase n while the compact route remains under the 300-operation cap."""
    if not isinstance(params, dict) or set(params) != {"n"}:
        return None
    n = params["n"]
    if not isinstance(n, int) or n >= 145:
        return None
    nxt = min(145, n + 16)
    if nxt % 256 == 0:
        nxt += 1
    return {"n": nxt}


def _gaussian_solve(inst: dict) -> tuple[str | None, int]:
    """Dense GF(257) elimination; return a bit answer and field-op count."""
    n = inst["n"]
    aug = [
        [value % _P for value in row] + [target % _P]
        for row, target in zip(inst["coefficient_matrix"], inst["rhs"])
    ]
    operations = 0
    pivot_row = 0
    pivot_columns: list[int] = []
    for column in range(n):
        pivot = next(
            (r for r in range(pivot_row, n) if aug[r][column] % _P), None
        )
        if pivot is None:
            continue
        aug[pivot_row], aug[pivot] = aug[pivot], aug[pivot_row]
        inverse = pow(aug[pivot_row][column], _P - 2, _P)
        operations += 1
        for j in range(column, n + 1):
            aug[pivot_row][j] = aug[pivot_row][j] * inverse % _P
            operations += 1
        for r in range(n):
            if r == pivot_row:
                continue
            factor = aug[r][column]
            if not factor:
                continue
            for j in range(column, n + 1):
                aug[r][j] = (aug[r][j] - factor * aug[pivot_row][j]) % _P
                operations += 2
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == n:
            break
    if pivot_row != n:
        return None, operations
    solution = [0] * n
    for r, column in enumerate(pivot_columns):
        solution[column] = aug[r][n]
    if any(value not in (0, 1) for value in solution):
        return None, operations
    return "".join(str(value) for value in solution), operations


def _outlier_correlation(inst: dict) -> str:
    """A matched-filter-style per-column guess using only marginal statistics."""
    n = inst["n"]

    def signed(value: int) -> int:
        return value if value <= _P // 2 else value - _P

    bits = []
    for j in range(n):
        score = sum(
            signed(inst["coefficient_matrix"][i][j]) * signed(inst["rhs"][i])
            for i in range(n)
        )
        bits.append("1" if score > 0 else "0")
    return "".join(bits)


def _greedy_exact_fit(inst: dict, passes: int = 4) -> tuple[str, int]:
    """Toggle a bit only when it strictly increases exactly satisfied rows."""
    n = inst["n"]
    matrix = inst["coefficient_matrix"]
    vector = [0] * n
    residual = [(-value) % _P for value in inst["rhs"]]
    steps = 0
    for _ in range(passes):
        changed = False
        for j in range(n):
            old_score = sum(value == 0 for value in residual)
            sign = 1 if vector[j] == 0 else -1
            proposed = [
                (residual[i] + sign * matrix[i][j]) % _P for i in range(n)
            ]
            new_score = sum(value == 0 for value in proposed)
            steps += 1
            if new_score > old_score:
                vector[j] ^= 1
                residual = proposed
                changed = True
        if not changed:
            break
    return "".join(str(bit) for bit in vector), steps


def _random_restart(inst: dict, rng: random.Random, restarts: int = 256) -> tuple[bool, int]:
    for attempt in range(1, restarts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, attempt
    return False, restarts


def _rhs_ansatz(inst: dict) -> tuple[bool, int]:
    """Try bit projections of b that are plausible without doing elimination."""
    n = inst["n"]
    rhs = inst["rhs"]
    candidates = [
        "0" * n,
        "1" * n,
        "".join("1" if value == 1 else "0" for value in rhs),
        "".join(str(value & 1) for value in rhs),
        "".join("1" if value <= _P // 2 else "0" for value in rhs),
    ]
    parity = candidates[3]
    candidates.extend(parity[offset:] + parity[:offset] for offset in range(1, 9))
    for candidate in candidates:
        if verify(inst, candidate)[0]:
            return True, len(candidates)
    return False, len(candidates)


def _relabel(
    inst: dict, row_order: list[int], column_order: list[int]
) -> dict:
    """Apply arbitrary equation and variable permutations, carrying the witness."""
    n = inst["n"]
    moved = dict(inst)
    moved["coefficient_matrix"] = [
        [inst["coefficient_matrix"][row_order[i]][column_order[j]] for j in range(n)]
        for i in range(n)
    ]
    moved["rhs"] = [inst["rhs"][row_order[i]] for i in range(n)]
    moved["answer"] = "".join(inst["answer"][column_order[j]] for j in range(n))
    return moved


def _answer_metrics(answer: str) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def selftest() -> dict:
    """Run correctness, corruption, density, attack, scale, and symmetry gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every named preset, several independent seeds, including JSON safety.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                roundtrip = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if roundtrip != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)

    # G2: five materially different malformed/corrupted answers and reasons.
    answer = ship["answer"]
    differing = next(i for i in range(1, len(answer)) if answer[i] != answer[0])
    swapped_list = list(answer)
    swapped_list[0], swapped_list[differing] = (
        swapped_list[differing],
        swapped_list[0],
    )
    corruptions = {
        "drop": answer[:-1],
        "swap": "".join(swapped_list),
        "duplicate": answer + answer[0],
        "empty": "",
        "out_of_range": "2" + answer[1:],
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: the answer survives prose, whitespace, and an outer Markdown fence.
    realistic = (
        "I reduced the equations modulo 257.\n```text\n"
        f"<answer>\n{answer}\n</answer>\n```\n"
        "The tag contains only the requested bits."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(ship, parsed)[0],
        "parsed_matches": parsed == answer,
        "realistic_wrapper": True,
    }

    # G4: uniform n-bit factors already satisfy every syntactic constraint.
    guess_rng = random.Random(0x260511545)
    guess_samples = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_samples):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / guess_samples
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_samples,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform over all exactly-n-bit Boolean factors",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    # G6: four failing in-context attacks; Gaussian elimination is separate on B.
    attack_names = (
        "outlier_column_correlation",
        "greedy_exact_equation_fit",
        "random_restart_256",
        "rhs_projection_ansatz",
    )
    attack_stats = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping)

        t0 = time.perf_counter()
        candidate = _outlier_correlation(inst)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["outlier_column_correlation"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += inst["n"]
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _greedy_exact_fit(inst)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["greedy_exact_equation_fit"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _random_restart(inst, random.Random(seed ^ 0xA551), 256)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["random_restart_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _rhs_ansatz(inst)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["rhs_projection_ansatz"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        solved, operations = _gaussian_solve(inst)
        elapsed = time.perf_counter() - t0
        reference_wall += elapsed
        reference_operations += operations
        reference_successes += int(solved is not None and verify(inst, solved)[0])

    for stat in attack_stats.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attack_stats.values())
    reference_average_operations = reference_operations // len(attack_seeds)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "dense Gaussian elimination over GF(257)",
            "complexity": "O(n^3) exact field operations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations_per_instance": reference_average_operations,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    # G5: exact uniqueness is certified by invertibility; sampling is also at ship.
    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(
        attack_stats.items(), key=lambda item: item[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == len(attack_seeds),
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": 2.0 ** (-ship["n"]),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_samples,
        "shipping_sampled_density": guess_fraction,
        "demo_bruteforce_solution_count": demo_count,
        "demo_n": demo["n"],
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": reference_average_operations,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    # G7: the ladder and a size-doubled instance both grow and remain certified.
    ladder_sizes = [params["n"] for params in DIFFICULTY.values()]
    ladder_spaces = [1 << size for size in ladder_sizes]
    doubled = make_instance(n=2 * ship["n"], seed=909)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            ladder_sizes == sorted(set(ladder_sizes))
            and ladder_spaces == sorted(set(ladder_spaces))
            and doubled_ok
            and doubled["moment_matrix_dimension"] > ship["moment_matrix_dimension"]
        ),
        "preset_n": dict(zip(DIFFICULTY, ladder_sizes)),
        "preset_candidate_spaces": dict(zip(DIFFICULTY, ladder_spaces)),
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    # G8: arbitrary row/column relabellings and their composition over 20 seeds.
    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(n=31, seed=20_000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        rows = list(range(inst["n"]))
        columns = list(range(inst["n"]))
        rng.shuffle(rows)
        rng.shuffle(columns)
        identity = list(range(inst["n"]))
        variants = (
            _relabel(inst, rows, identity),
            _relabel(inst, identity, columns),
            _relabel(inst, rows, columns),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                invariant_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant_failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary equation-row permutation",
            "arbitrary variable-column permutation",
            "composition of row and column permutations",
        ],
    }

    # G9(a,b) is patched only from harden.py evidence; size/effort are local.
    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = 2 * ship["n"] + 1
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
