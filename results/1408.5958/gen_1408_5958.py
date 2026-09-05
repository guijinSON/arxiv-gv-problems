"""Self-contained generator for nonnegative integer linear equations.

The native problem is the ILP feasibility problem defined in Section 2 of
arXiv:1408.5958.  Instances are inverse-generated: choose the bounded
nonnegative integer assignment first, build a nonsingular matrix, and compute
the right-hand side.  No instance is solved during generation.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "integer coefficient matrix",
        "integer right-hand-side vector",
        "bounded nonnegative integer assignment",
    ],
    "verification_operations": [
        "exact integer matrix-vector multiplication",
        "integer bound comparison",
        "exact equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "After matching each equation to its exceptional coefficient, the "
        "coefficient matrix decomposes into a diagonal matrix plus a rank-one "
        "matrix; without that decomposition one must eliminate a dense system."
    ),
    "hardness_basis": (
        "Track B: the domain-standard exact Gaussian elimination algorithm is "
        "O(n^3) in general and, benefiting from this distribution's cancellations, "
        "averages 13,843 exact operations and about 0.008 seconds at shipping "
        "n=48 with 56-bit values; the diagonal-plus-rank-one route takes at most "
        "292 exact operations, but executing those large-integer operations without "
        "tools remains the measured bottleneck."
    ),
    "max_answer_tokens": 217,
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
    "demo": {"n": 4, "value_bits": 4, "coupling_bits": 1},
    "easy": {"n": 48, "value_bits": 20, "coupling_bits": 7},
    "medium": {"n": 48, "value_bits": 44, "coupling_bits": 7},
    "hard": {"n": 48, "value_bits": 56, "coupling_bits": 7},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The coefficient matrix is a row-and-column permutation of a scalar diagonal "
    "matrix plus a rank-one sign matrix."
)
PLACEBO_HINT = (
    "The coefficient matrix rewards careful attention to row-and-column order "
    "and exact signs throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n integers, in variable order, with every entry "
        "in the inclusive interval 0..2^value_bits-1; n is at most 128."
    ),
    "bounds": {
        "max_dimension": 128,
        "max_value_bits": 128,
        "nonnegative": True,
    },
}

NOTES = r"""
Paper grounding.  Section 2 defines an ILP instance in standard form as Ax=b
with integer A and b and asks for a nonnegative integer vector x.  Section 3,
Proposition 1 proves that these assignments are exactly the solutions encoded
by the paper's labelled graphs; this generator stays with the prior, native ILP
object and does not compile it to a graph.  Theorem 2 supplies the bounded
path-width representation, and Theorem 3 gives an automaton with the same
Parikh-image solution set.

Step-0 algorithm check.  Section 1 lists branch-and-bound, cutting planes, LLL,
the Omega test, and automata methods.  Section 6 states that general ILP
feasibility is NP-complete and that this paper's Boolean-program construction
only gives a PSPACE procedure.  Those worst-case facts do not make this planted
distribution hard: every generated coefficient matrix is nonsingular, so exact
Gaussian elimination finds its sole rational candidate in O(n^3), followed by
an integrality and nonnegativity check.  The family is therefore Track B, never
Track A.  The compact Sherman--Morrison-style calculation is shorter: align the
unique exceptional entry of every row, recover A=qI+r*u*v^T, compute
z=(v^T b)/(q+r*v^T u), and use x_i=(b_i-r*u_i*z)/q.  At n=48 this is bounded by
6n+4=292 exact arithmetic operations, versus the measured elimination count in
selftest_report.json.

Generation.  The assignment is sampled first.  Independent sign vectors u and
v and positive integers r,q with q=(n+1)r+1 define A=qI+r*u*v^T; hence
det(A)=q^(n-1)(q+r*v^T u)>0 because |v^T u|<=n.  The right side is computed as
b=Ax, after which equations and variables are independently shuffled.  Thus
the planted witness is known by inverse generation and is the unique rational,
hence unique bounded-integer, solution.

Attacks.  Large-coordinate ranking, exceptional-diagonal rounding, 256 local
random restarts, and the by-hand centered-residue lift all fail.  The rank term
is deliberately large enough to spoil diagonal rounding, plants and decoys do
not exist as separate populations, and generation enforces |v^T x| well beyond
the centered modular representative.  Exact Gaussian elimination is successful
and is reported separately as Track B requires.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 2},
    "hinted": {"solved": 0, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 2, "errors": 4},
    "hinted_verdict": "hardened",
    "placebo_note": (
        "The third placebo slot was not completed: all four script-mandated "
        "redraws returned HTTP 403 after the OpenRouter key reached its total limit."
    ),
}


def _validate_params(n: int, value_bits: int, coupling_bits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or n > 128:
        raise ValueError("n must be an integer in 4..128")
    if isinstance(value_bits, bool) or not isinstance(value_bits, int):
        raise ValueError("value_bits must be an integer")
    if not 4 <= value_bits <= 128:
        raise ValueError("value_bits must lie in 4..128")
    if n > 1 << (value_bits - 1):
        raise ValueError(
            "n must not exceed the number of distinct planted values available "
            "at this value_bits setting"
        )
    if isinstance(coupling_bits, bool) or not isinstance(coupling_bits, int):
        raise ValueError("coupling_bits must be an integer")
    if not 1 <= coupling_bits <= 20:
        raise ValueError("coupling_bits must lie in 1..20")


def _balanced_signs(n: int, rng: random.Random) -> list[int]:
    signs = [1] * (n // 2) + [-1] * (n - n // 2)
    rng.shuffle(signs)
    return signs


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a uniquely solvable bounded nonnegative ILP instance."""
    allowed = {"value_bits", "coupling_bits"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    value_bits = params.get("value_bits", 20)
    coupling_bits = params.get("coupling_bits", 7)
    _validate_params(n, value_bits, coupling_bits)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    maximum = (1 << value_bits) - 1
    lower = 1 << (value_bits - 1)

    # The demo keeps arithmetic genuinely hand-scale.  Other presets make the
    # rank-one displacement much larger than a centered residue modulo q.
    if coupling_bits == 1:
        r = 1
    else:
        r = rng.randrange(1 << (coupling_bits - 1), 1 << coupling_bits)
    q = (n + 1) * r + 1

    fallback = None
    for _ in range(10_000):
        x = rng.sample(range(lower, maximum + 1), n)
        u = _balanced_signs(n, rng)
        v = _balanced_signs(n, rng)
        products = {u[i] * v[i] for i in range(n)}
        z = sum(v[i] * x[i] for i in range(n))
        if products == {-1, 1}:
            fallback = (x, u, v)
            if n == 4 or abs(z) > 10 * q:
                break
    else:
        # Extreme caller-supplied bit combinations can make |v^T x| > 10q
        # impossible.  That condition only hardens one heuristic; it is not
        # needed for correctness, so retain total deterministic generation.
        if fallback is None:  # mathematically unreachable for n >= 4
            raise RuntimeError("could not draw nondegenerate sign vectors")
        x, u, v = fallback

    matrix = []
    rhs = []
    for i in range(n):
        row = [r * u[i] * v[j] + (q if i == j else 0) for j in range(n)]
        matrix.append(row)
        rhs.append(sum(row[j] * x[j] for j in range(n)))

    # Equations and variable names carry no semantic order.
    row_order = list(range(n))
    col_order = list(range(n))
    rng.shuffle(row_order)
    rng.shuffle(col_order)
    public_matrix = [[matrix[i][j] for j in col_order] for i in row_order]
    public_rhs = [rhs[i] for i in row_order]
    public_answer = [x[j] for j in col_order]

    return {
        "family": "bounded_nonnegative_integer_equations",
        "n": n,
        "value_bits": value_bits,
        "coupling_bits": coupling_bits,
        "max_value": maximum,
        "A": public_matrix,
        "b": public_rhs,
        "answer": public_answer,
    }


def render(inst: dict) -> str:
    """Render a complete, unambiguous problem with an exact JSON output contract."""
    n = inst["n"]
    rows = [f"{i}: " + " ".join(str(a) for a in row) + f" | {inst['b'][i]}"
            for i, row in enumerate(inst["A"])]
    statement = f"""Bounded nonnegative integer equations

An integer assignment is a vector x=(x_0,...,x_{n-1}) of exactly {n} integers.
Find any assignment satisfying every equation A x = b, where multiplication and
addition are over the ordinary integers.  Every coordinate must lie in the
inclusive interval 0 <= x_j <= {inst['max_value']}.  Variable and column indices
are 0-based, the output order is x_0 through x_{n-1}, and repeats are allowed.

Each line below is one equation.  Before the vertical bar are its {n}
coefficients in x_0,...,x_{n-1} order; after the bar is its right-hand side.

""" + "\n".join(rows) + f"""

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{n} decimal integers in variable order.
Example format: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the tagged JSON integer vector; never raise on model output."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check a candidate directly and exactly without consulting the plant."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    for j, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {j} is not an integer"
        if not 0 <= value <= inst["max_value"]:
            return False, (
                f"entry {j}={value} is outside inclusive range "
                f"0..{inst['max_value']}"
            )
    for i, (row, target) in enumerate(zip(inst["A"], inst["b"])):
        lhs = sum(row[j] * answer[j] for j in range(n))
        if lhs != target:
            return False, f"equation {i} fails: left side {lhs}, right side {target}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated bounded vector language."""
    return [rng.randint(0, inst["max_value"]) for _ in range(inst["n"])]


def search_space(inst: dict) -> int:
    return (inst["max_value"] + 1) ** inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force only when the complete declared language is safely small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.product(range(inst["max_value"] + 1), repeat=inst["n"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def _structure(inst: dict) -> tuple[int, int, list[int], list[int], list[int]]:
    """Recover q,r,u,v and b after matching equations to variables."""
    a = inst["A"]
    n = inst["n"]
    abs_values = [abs(value) for row in a for value in row if value]
    r = min(abs_values)
    large = []
    for i, row in enumerate(a):
        columns = [j for j, value in enumerate(row) if abs(value) > r]
        if len(columns) != 1:
            raise ValueError("matrix is outside the generated family")
        large.append((columns[0], i, abs(row[columns[0]])))
    if len({col for col, _, _ in large}) != n:
        raise ValueError("exceptional coefficients do not form a matching")
    diagonal_magnitudes = {mag for _, _, mag in large}
    if len(diagonal_magnitudes) != 2:
        raise ValueError("cannot infer the common diagonal shift")
    lo, hi = sorted(diagonal_magnitudes)
    if hi - lo != 2 * r:
        raise ValueError("invalid diagonal magnitudes")
    q = (lo + hi) // 2
    row_for_col = [0] * n
    for col, row, _ in large:
        row_for_col[col] = row
    paired_b = [inst["b"][row_for_col[i]] for i in range(n)]
    b00 = a[row_for_col[0]][0] - q
    if abs(b00) != r:
        raise ValueError("rank-one pivot is invalid")
    u = []
    for i in range(n):
        value = a[row_for_col[i]][0] - (q if i == 0 else 0)
        u.append(value // r)
    v = []
    for j in range(n):
        value = a[row_for_col[0]][j] - (q if j == 0 else 0)
        v.append(value // (r * u[0]))
    return q, r, u, v, paired_b


def canonical_key(inst: dict) -> str:
    """Canonicalize equation order, variable relabelling, and sign ambiguity."""
    q, r, u, v, paired_b = _structure(inst)
    orientation_a = sorted((u[i], v[i], paired_b[i]) for i in range(inst["n"]))
    orientation_b = sorted((-u[i], -v[i], paired_b[i]) for i in range(inst["n"]))
    payload = [inst["n"], inst["max_value"], q, r,
               min(orientation_a, orientation_b)]
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise numeric entropy at fixed witness dimension and operation count."""
    clean = {k: v for k, v in params.items() if not k.startswith("_")}
    n = int(clean.get("n", 48))
    value_bits = int(clean.get("value_bits", 20))
    coupling_bits = int(clean.get("coupling_bits", 7))
    if value_bits + 12 <= 128:
        return {"n": n, "value_bits": value_bits + 12,
                "coupling_bits": coupling_bits}
    return "cap_bound"


def _relabel(inst: dict, row_order: list[int], col_order: list[int]) -> dict:
    moved = {k: v for k, v in inst.items() if k not in {"A", "b", "answer"}}
    moved["A"] = [[inst["A"][i][j] for j in col_order] for i in row_order]
    moved["b"] = [inst["b"][i] for i in row_order]
    moved["answer"] = [inst["answer"][j] for j in col_order]
    return moved


def _round_fraction(numerator: int, denominator: int) -> int:
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    if numerator >= 0:
        return (2 * numerator + denominator) // (2 * denominator)
    return -((-2 * numerator + denominator) // (2 * denominator))


def _exceptional_rows(inst: dict) -> list[int]:
    a = inst["A"]
    r = min(abs(value) for row in a for value in row if value)
    rows = [0] * inst["n"]
    for i, row in enumerate(a):
        col = max(range(inst["n"]), key=lambda j: abs(row[j]))
        rows[col] = i
    return rows


def _diagonal_round(inst: dict) -> list[int]:
    rows = _exceptional_rows(inst)
    maximum = inst["max_value"]
    return [max(0, min(maximum,
                       _round_fraction(inst["b"][rows[j]], inst["A"][rows[j]][j])))
            for j in range(inst["n"])]


def _outlier_rank(inst: dict) -> list[int]:
    rows = _exceptional_rows(inst)
    order = sorted(range(inst["n"]), key=lambda j: abs(inst["b"][rows[j]]))
    candidate = [0] * inst["n"]
    maximum = inst["max_value"]
    for rank, j in enumerate(order):
        candidate[j] = (rank + 1) * maximum // (inst["n"] + 1)
    return candidate


def _centered_residue(inst: dict) -> list[int] | None:
    try:
        q, r, u, _v, paired_b = _structure(inst)
        inv_r = pow(r, -1, q)
        residue = (u[0] * paired_b[0] * inv_r) % q
        z0 = residue if residue <= q // 2 else residue - q
        candidate = [(paired_b[i] - r * u[i] * z0) // q for i in range(inst["n"])]
        return candidate
    except (ValueError, ZeroDivisionError):
        return None


def _random_restart(inst: dict, rng: random.Random, restarts: int = 256) -> tuple[bool, int]:
    base = _diagonal_round(inst)
    maximum = inst["max_value"]
    for _ in range(restarts):
        candidate = [max(0, min(maximum, x + rng.randint(-1024, 1024))) for x in base]
        if verify(inst, candidate)[0]:
            return True, restarts
    return False, restarts


def _gaussian_solve(inst: dict) -> tuple[list[int] | None, int]:
    """Generic exact Fraction Gaussian elimination, instrumented by operations."""
    n = inst["n"]
    aug = [[Fraction(value) for value in row] + [Fraction(inst["b"][i])]
           for i, row in enumerate(inst["A"])]
    operations = 0
    for col in range(n):
        pivot = next((i for i in range(col, n) if aug[i][col]), None)
        if pivot is None:
            return None, operations
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pivot_value
            operations += 1
        for i in range(col + 1, n):
            factor = aug[i][col]
            if not factor:
                continue
            for j in range(col, n + 1):
                aug[i][j] -= factor * aug[col][j]
                operations += 2
    solution = [Fraction(0) for _ in range(n)]
    for i in range(n - 1, -1, -1):
        value = aug[i][n]
        for j in range(i + 1, n):
            value -= aug[i][j] * solution[j]
            operations += 2
        solution[i] = value
    if any(value.denominator != 1 for value in solution):
        return None, operations
    return [int(value) for value in solution], operations


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))
    elements = len(answer) if isinstance(answer, list) else 1
    # A conservative reproducible approximation used throughout this repository.
    tokens = math.ceil(len(blob) / 4)
    return len(blob), tokens, elements


def selftest() -> dict:
    """Run every locally measurable gate and include script-owned G9 evidence."""
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]
    swap = list(answer)
    swap[0], swap[1] = swap[1], swap[0]
    duplicate = list(answer)
    duplicate[1] = duplicate[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": swap,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": [ship["max_value"] + 1] + answer[1:],
    }
    cases = {name: {"accepted": verify(ship, candidate)[0],
                    "reason": verify(ship, candidate)[1]}
             for name, candidate in corruptions.items()}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not case["accepted"] for case in cases.values())
                and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    wrapped = (
        "I obtained the bounded integer assignment.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\n"
        "The tagged list is in variable order."
    )
    parsed = parse_answer(wrapped)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(ship, parsed)[0],
        "parsed_matches": parsed == answer,
    }

    guess_rng = random.Random(0x14085958)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_t0
    guess_density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_density,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform over every bounded n-coordinate integer vector",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_rhs_rank",
        "greedy_exceptional_diagonal_rounding",
        "random_restart_local_256",
        "by_hand_centered_residue_lift",
    )
    stats = {name: {"successes": 0, "attempts": 0, "steps": 0,
                    "wall_clock_sec": 0.0} for name in attack_names}
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping)
        probes = [
            ("outlier_rhs_rank", lambda: (_outlier_rank(inst), inst["n"])),
            ("greedy_exceptional_diagonal_rounding",
             lambda: (_diagonal_round(inst), inst["n"])),
            ("by_hand_centered_residue_lift",
             lambda: (_centered_residue(inst), 4 * inst["n"])),
        ]
        for name, probe in probes:
            t0 = time.perf_counter()
            candidate, steps = probe()
            elapsed = time.perf_counter() - t0
            stats[name]["attempts"] += 1
            stats[name]["successes"] += int(verify(inst, candidate)[0])
            stats[name]["steps"] += steps
            stats[name]["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        solved, steps = _random_restart(inst, random.Random(seed ^ 0xA55A), 256)
        elapsed = time.perf_counter() - t0
        name = "random_restart_local_256"
        stats[name]["attempts"] += 1
        stats[name]["successes"] += int(solved)
        stats[name]["steps"] += steps
        stats[name]["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        solved_vector, operations = _gaussian_solve(inst)
        reference_wall += time.perf_counter() - t0
        reference_operations += operations
        reference_successes += int(
            solved_vector is not None and verify(inst, solved_vector)[0]
        )

    for stat in stats.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in stats.values())
    average_ops = reference_operations // 8
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": stats,
        "reference_algorithm": {
            "name": "dense exact Gaussian elimination over Q",
            "complexity": "O(n^3) exact rational operations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations_per_instance": average_ops,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest = max(stats.items(), key=lambda item: item[1]["wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == 8,
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": f"1/{search_space(ship)}",
        "shipping_log10_solution_fraction": -math.log10(search_space(ship)),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_density,
        "demo_bruteforce_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": average_ops,
        "strongest_failing_attack": strongest[0],
        "strongest_failing_attack_wall_clock_sec": strongest[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest[1]["steps"],
    }

    preset_n = [params["n"] for params in DIFFICULTY.values()]
    preset_spaces = [search_space(make_instance(seed=9, **params))
                     for params in DIFFICULTY.values()]
    doubled = make_instance(n=2 * ship["n"], seed=909,
                            value_bits=shipping["value_bits"],
                            coupling_bits=shipping["coupling_bits"])
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": preset_n == sorted(preset_n)
                and preset_spaces == sorted(set(preset_spaces)) and doubled_ok,
        "preset_n": dict(zip(DIFFICULTY, preset_n)),
        "preset_candidate_spaces": dict(zip(DIFFICULTY, preset_spaces)),
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated = []
    for seed in range(20):
        inst = make_instance(n=17, seed=20_000 + seed,
                             value_bits=12, coupling_bits=5)
        base_key = canonical_key(inst)
        unrelated.append(base_key)
        rng = random.Random(30_000 + seed)
        rows = list(range(inst["n"]))
        cols = list(range(inst["n"]))
        identity = list(range(inst["n"]))
        rng.shuffle(rows)
        rng.shuffle(cols)
        variants = (
            _relabel(inst, rows, identity),
            _relabel(inst, identity, cols),
            _relabel(inst, rows, cols),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                invariant_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant_failures.append(f"witness/{seed}/{number}")
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "transformations": [
            "arbitrary equation-row permutation",
            "arbitrary variable-column permutation with carried assignment",
            "composition of equation and variable permutations",
        ],
    }

    # All planted 56-bit values have 17 decimal digits, so every shipping answer
    # attains the 865-character worst case (217 tokens under this measurement).
    metrics_inst = make_instance(seed=931, **shipping)
    chars, tokens, elements = _answer_metrics(metrics_inst["answer"])
    intended_operations = 6 * ship["n"] + 4
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (chars <= 2000 and elements <= 256
                   and intended_operations <= 300
                   and PROBLEM_PROFILE["max_answer_tokens"] == tokens)
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
        "diagnostic_complete": arms["placebo"]["attempts"] == 3,
        "diagnostic_note": G9_ORACLE_RESULTS["placebo_note"],
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
