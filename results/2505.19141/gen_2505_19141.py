"""Verified generator for bounded S-unit equations on unipotent modules.

The source is arXiv:2505.19141, especially Theorem 1.3 and the matrix-action
form of an S-unit equation in Section 3.3 (Equation (3.25) in the paper's v2
source).  Instances use a free finite-field module whose Laurent generators
act by commuting square-zero shears.

The exponent vector is sampled first.  The target module element is obtained
by applying the sampled monomial, so generation never solves the displayed
equation.  Generic recovery in this restricted family is modular Gaussian
elimination; a planted rank-one invariant provides the intended compact route.
"""

from __future__ import annotations

import hashlib
import itertools
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
    "certificate_form": "integer_tuple",
    "native_objects": [
        "free module over GF(p)",
        "commuting invertible module-generator actions",
        "Laurent monomial acting on a module element",
    ],
    "verification_operations": [
        "exact finite-field module action",
        "exact modular matrix-vector multiplication",
        "exact vector equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the generator columns form identity plus one rank-one "
        "operator and reduce all coupling to a single scalar pairing; without "
        "that invariant one must execute dense modular elimination."
    ),
    "hardness_basis": (
        "Track B: Theorem 1.3 supplies an effective automaton construction, and "
        "for this Section 3.3 unipotent-matrix regime exact Gaussian elimination "
        "is O(n^3); at shipping n=32 it averaged 23,376 field operations and "
        "0.0044 seconds in the recorded eight-seed run, while the rank-one route uses at "
        "most 7n+2=226 exact field operations and the full elimination is not "
        "executable by hand in context."
    ),
    "max_answer_tokens": 89,
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
    "demo": {"n": 2, "field": "toy"},
    "easy": {"n": 32, "field": "m31"},
    "medium": {"n": 36, "field": "m31"},
    "hard": {"n": 40, "field": "m31"},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The displayed coefficient matrix differs from identity by rank one, and "
    "all nonidentity contributions share a single scalar pairing."
)
PLACEBO_HINT = (
    "The displayed coefficient matrix uses least residues throughout, and all "
    "submitted coordinates require careful exact modular checking."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n least nonnegative residues: entry z_j is an "
        "integer with 0 <= z_j < p, in the displayed Laurent-generator order."
    ),
    "bounds": {
        "length": "n",
        "entry_min": 0,
        "entry_max": "p-1",
        "candidate_count": "p^n",
    },
}

NOTES = (
    "The exact definition is fixed by Introduction Equation (1.2): an S-unit "
    "equation asks for integer exponents of Laurent monomials acting on specified "
    "module elements. Section 3.3 rewrites the native problem with pairwise "
    "commuting invertible matrices acting on a free module (Equation (3.25)). "
    "Theorem 1.3 is the easy-regime warning: for prime-power torsion the whole "
    "solution set is effectively p-normal via the Section 3 automaton, so this is "
    "Track B, not Track A. The paper also states that one prime has classical "
    "decision algorithms and two primes are decidable, while three or more primes "
    "remain open; this generator deliberately stays in the exact one-prime module "
    "regime rather than borrowing an unsupported hardness claim. The answer z is "
    "sampled first. Generator X_j acts by (c,w)->(c,w+c*a_j), where the columns "
    "a_j form A=I+u*v^T, and the target is (1,A*z). The action shears commute and "
    "their nilpotent parts have pairwise-zero products, so substitution is exact. "
    "Uniform u, v, and z remove coordinate outliers; a dense nonsingular A defeats "
    "diagonal and left-to-right rules; eight obvious rank-one scalar guesses and "
    "256 uniform restarts are audited; exact Gaussian elimination is reported "
    "separately as the successful Track B reference algorithm."
)


# The large fields are Mersenne prime fields.  Lucas-Lehmer checks are rerun in
# selftest, rather than trusting this comment or an external table.
_FIELDS = {
    "toy": {"p": 11, "mersenne_exponent": None},
    "m31": {"p": (1 << 31) - 1, "mersenne_exponent": 31},
    "m61": {"p": (1 << 61) - 1, "mersenne_exponent": 61},
    "m89": {"p": (1 << 89) - 1, "mersenne_exponent": 89},
    "m127": {"p": (1 << 127) - 1, "mersenne_exponent": 127},
}

# Filled with evidence from the three harness runs.  Zero-attempt placeholders
# make an unrun external diagnostic explicit while keeping local gates honest.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "error_calls": 4},
    "hinted": {"solved": 0, "attempts": 0, "error_calls": 4},
    "placebo": {"solved": 0, "attempts": 0, "error_calls": 4},
    "hinted_verdict": "unavailable_api_errors",
}


def _dot(a, b, p):
    return sum(x * y for x, y in zip(a, b)) % p


def _inverse(a, p):
    """Exact inverse in GF(p), with a clear failure on malformed data."""
    a %= p
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    old_r, r = a, p
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ZeroDivisionError("element is not invertible")
    return old_s % p


def _inverse_counted(a, p):
    a %= p
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    old_r, r = a, p
    old_s, s = 1, 0
    divisions = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        divisions += 1
    if old_r != 1:
        raise ZeroDivisionError("element is not invertible")
    return old_s % p, divisions


def _is_prime_64(value):
    """Deterministic Miller-Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
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


def _is_mersenne_prime(exponent):
    """Lucas-Lehmer test, exact for a Mersenne number 2^exponent-1."""
    if exponent == 2:
        return True
    if not _is_prime_64(exponent):
        return False
    modulus = (1 << exponent) - 1
    state = 4
    for _ in range(exponent - 2):
        state = (state * state - 2) % modulus
    return state == 0


def make_instance(n, seed=0, **params):
    """Inverse-generate a native one-term S-unit equation.

    The exponent witness is sampled before A or the target.  The target is then
    obtained by composing the commuting module actions; no equation is solved.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    field = params.pop("field", "m31")
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if field not in _FIELDS:
        raise ValueError("unknown field preset")
    p = _FIELDS[field]["p"]
    rng = random.Random(seed)

    # G: sample the certificate first.
    answer = [rng.randrange(p) for _ in range(n)]

    # A = I + u v^T.  det(A)=1+v^T u, so reject only construction
    # randomness that would make the displayed equation non-unique.  This is not
    # searching for the answer; the answer was already sampled above.
    while True:
        u = [rng.randrange(1, p) for _ in range(n)]
        v = [rng.randrange(1, p) for _ in range(n)]
        if any((1 + u[i] * v[i]) % p == 0 for i in range(n)):
            continue
        if (1 + _dot(v, u, p)) % p != 0:
            break

    scalar = _dot(v, answer, p)
    action_columns = [
        [((1 if i == j else 0) + u[i] * v[j]) % p for j in range(n)]
        for i in range(n)
    ]
    target_tail = [(answer[i] + u[i] * scalar) % p for i in range(n)]

    return {
        "family": "bounded S-unit equation on commuting unipotent module actions",
        "n": n,
        "field": field,
        "p": p,
        "action_columns": action_columns,
        "source": [1] + [0] * n,
        "target": [1] + target_tail,
        "answer": answer,
    }


def render(inst):
    n, p = inst["n"], inst["p"]
    matrix_lines = "\n".join(
        f"  {i + 1}: " + " ".join(str(value) for value in row)
        for i, row in enumerate(inst["action_columns"])
    )
    target_line = " ".join(str(value) for value in inst["target"])
    example = json.dumps(list(range(n)), separators=(",", ":"))
    statement = f"""Find a Laurent monomial sending one element of a finite-field module to another.

Let F be the field of residues modulo the prime p={p}.  The module is
V=F^({n + 1}); write its vectors as (c,w_1,...,w_{n}).  There are {n}
commuting Laurent generators X_1,...,X_{n}.  Column j of the matrix A below is
the vector a_j in F^{n}, and the action of X_j is

    X_j * (c,w) = (c, w + c*a_j)  (all coordinates modulo p).

This action is invertible: X_j^(-1)*(c,w)=(c,w-c*a_j), so every integer
exponent is defined.  The actions commute.  For an exponent vector
z=(z_1,...,z_{n}), the Laurent monomial X_1^z_1 ... X_{n}^z_{n} means compose
those actions.  We require the unique least-residue representative with every
0 <= z_j < p.  Rows and columns are 1-indexed, their order is significant, and
no entry may be omitted.

Matrix A ({n} rows, {n} entries per row; entries are least residues modulo p):
{matrix_lines}

Source module element:
  {' '.join(str(value) for value in inst['source'])}

Target module element:
  {target_line}

Find z such that the ordered product over j=1,...,{n} of X_j^(z_j), acting
on source, equals target.

The displayed A is nonsingular over F, so the required least-residue exponent
vector is unique.  The answer must be a JSON list of exactly {n} decimal
integers in X_1,...,X_{n} order, with every entry in the inclusive range
0,...,p-1.  Repetitions are allowed.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the final tagged JSON vector; never raise on model garbage."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(entry, bool) or not isinstance(entry, int) for entry in value):
        return None
    return value


def verify(inst, answer):
    """Check any valid exponent witness exactly; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    n, p = inst["n"], inst["p"]
    if len(answer) != n:
        return False, f"expected {n} entries, got {len(answer)}"
    for j, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {j + 1} is not an integer"
        if not 0 <= value < p:
            return False, f"entry {j + 1} is outside 0 <= z < p"

    matrix = inst["action_columns"]
    target = inst["target"]
    if target[0] % p != inst["source"][0] % p:
        return False, "the invariant leading module coordinate does not match"
    # Composing X_j^z_j on source=(1,0) gives tail A*z.  Check rows in
    # sequence so a random wrong answer normally costs only one exact dot product.
    for i, row in enumerate(matrix):
        got = sum(coefficient * exponent for coefficient, exponent in zip(row, answer)) % p
        expected = target[i + 1] % p
        if got != expected:
            return False, (
                f"module coordinate {i + 1} has residue {got}, expected {expected}"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the fully constrained least-residue exponent language."""
    return [rng.randrange(inst["p"]) for _ in range(inst["n"])]


def search_space(inst):
    return inst["p"] ** inst["n"]


def enumerate_all(inst):
    total = search_space(inst)
    if total > 100_000:
        return None
    count = 0
    for candidate in itertools.product(range(inst["p"]), repeat=inst["n"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def _gaussian_reference(inst):
    """Exact modular elimination, with arithmetic counters for Track B."""
    p, n = inst["p"], inst["n"]
    rhs = inst["target"][1:]
    aug = [list(row) + [value] for row, value in zip(inst["action_columns"], rhs)]
    field_operations = 0
    euclidean_divisions = 0
    row_swaps = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] % p), None)
        if pivot is None:
            return None, {
                "field_operations": field_operations,
                "euclidean_divisions": euclidean_divisions,
                "row_swaps": row_swaps,
            }
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
            row_swaps += 1
        inv, divisions = _inverse_counted(aug[col][col], p)
        euclidean_divisions += divisions
        for j in range(col, n + 1):
            aug[col][j] = aug[col][j] * inv % p
            field_operations += 1
        for r in range(col + 1, n):
            factor = aug[r][col]
            if factor == 0:
                continue
            aug[r][col] = 0
            for j in range(col + 1, n + 1):
                aug[r][j] = (aug[r][j] - factor * aug[col][j]) % p
                field_operations += 2
    solution = [0] * n
    for i in range(n - 1, -1, -1):
        value = aug[i][n]
        for j in range(i + 1, n):
            value = (value - aug[i][j] * solution[j]) % p
            field_operations += 2
        solution[i] = value
    return solution, {
        "field_operations": field_operations,
        "euclidean_divisions": euclidean_divisions,
        "row_swaps": row_swaps,
    }


def _rank_one_factors(inst):
    """Recover factors of A-I from the public matrix, not generator secrets."""
    p, matrix, n = inst["p"], inst["action_columns"], inst["n"]
    b00 = (matrix[0][0] - 1) % p
    inv_b00 = _inverse(b00, p)
    left = [
        (matrix[i][0] - (1 if i == 0 else 0)) % p for i in range(n)
    ]
    right = [
        ((matrix[0][j] - (1 if j == 0 else 0)) * inv_b00) % p
        for j in range(n)
    ]
    return left, right


def _rank_one_compact_solve(inst):
    """Sherman-Morrison solve for public A=I+u*v^T."""
    p = inst["p"]
    left, right = _rank_one_factors(inst)
    rhs = inst["target"][1:]
    alpha = _dot(right, rhs, p)
    beta = _dot(right, left, p)
    correction = alpha * _inverse(1 + beta, p) % p
    return [(value - u_i * correction) % p for value, u_i in zip(rhs, left)]


def _det_mod(matrix, p):
    work = [list(row) for row in matrix]
    determinant = 1
    for col in range(len(work)):
        pivot = next(
            (r for r in range(col, len(work)) if work[r][col] % p), None
        )
        if pivot is None:
            return 0
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
            determinant = -determinant
        pivot_value = work[col][col] % p
        determinant = determinant * pivot_value % p
        inv = _inverse(pivot_value, p)
        for r in range(col + 1, len(work)):
            factor = work[r][col] * inv % p
            if factor:
                for j in range(col + 1, len(work)):
                    work[r][j] = (work[r][j] - factor * work[col][j]) % p
    return determinant % p


def canonical_key(inst):
    """Canonicalize module-basis changes and Laurent-generator relabellings.

    Left multiplication by any invertible module-basis matrix leaves the unique
    exponent vector unchanged; generator relabelling permutes coordinates, and
    replacing X_j by X_j^-1 negates one residue.  Reducing the augmented action
    matrix, normalizing each residue up to sign, and sorting is therefore an
    exact normal form for the transformations audited in G8.  This function
    solves from public data and never reads inst['answer'].
    """
    solution, _counts = _gaussian_reference(inst)
    if solution is None:
        # Generated instances never enter this branch.  It keeps malformed input
        # deterministic without pretending singular systems share a normal form.
        payload = {
            "p": inst.get("p"),
            "n": inst.get("n"),
            "singular_rows": sorted(
                sorted(int(x) for x in row) for row in inst["action_columns"]
            ),
        }
    else:
        payload = {
            "p": inst["p"],
            "n": inst["n"],
            "signed_exponent_multiset": sorted(
                min(value, (-value) % inst["p"]) for value in solution
            ),
        }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Increase ambient dimension first, then field entropy at fixed answer length."""
    n = params.get("n")
    field = params.get("field", "m31")
    if not isinstance(n, int):
        return None
    if field == "m31" and n < 42:
        return {"n": min(42, n + 4), "field": "m31"}
    next_field = {"m31": "m61", "m61": "m89", "m89": "m127"}.get(field)
    if next_field is not None:
        return {"n": n, "field": next_field}
    if field == "m127":
        return "cap_bound"
    return None


def _attack_candidates(inst, seed):
    p, n = inst["p"], inst["n"]
    matrix = inst["action_columns"]
    rhs = inst["target"][1:]

    # Since z is sampled independently of A, column magnitude/order carries no
    # information.  This nevertheless tests the most obvious planting leak.
    column_scores = [
        sum(matrix[i][j] for i in range(n)) % p for j in range(n)
    ]
    ranks = {value: rank for rank, value in enumerate(sorted(set(column_scores)))}
    outlier = [[ranks[value] % p for value in column_scores]]

    diagonal = [
        [rhs[i] * _inverse(matrix[i][i], p) % p for i in range(n)]
    ]

    greedy = [0] * n
    for i in range(n):
        residual = rhs[i] - sum(matrix[i][j] * greedy[j] for j in range(i))
        greedy[i] = residual * _inverse(matrix[i][i], p) % p

    left, _right = _rank_one_factors(inst)
    trial_scalars = [
        0,
        1,
        p - 1,
        rhs[0],
        sum(rhs) % p,
        min(rhs),
        max(rhs),
        sum(matrix[i][i] for i in range(n)) % p,
    ]
    small_scalar = [
        [(rhs[i] - left[i] * scalar) % p for i in range(n)]
        for scalar in trial_scalars
    ]

    rrng = random.Random(seed ^ 0x250519141)
    restarts = [random_candidate(inst, rrng) for _ in range(256)]
    return {
        "outlier_column_sum_rank": outlier,
        "greedy_left_to_right_zero_fill": [greedy],
        "diagonal_only_relaxation": diagonal,
        "by_hand_eight_obvious_coupling_scalars": small_scalar,
        "random_restart_256": restarts,
    }


def _relabel_variants(inst, seed):
    """Compositions of row/column, basis-shear, and X_j inversion maps."""
    rng = random.Random(seed)
    n, p = inst["n"], inst["p"]
    row_perm = list(range(n))
    col_perm = list(range(n))
    rng.shuffle(row_perm)
    rng.shuffle(col_perm)
    shear_to, shear_from = rng.sample(range(n), 2)
    shear_scalar = rng.randrange(1, p)
    inverted_columns = {j for j in range(n) if rng.randrange(2)}
    if not inverted_columns:
        inverted_columns.add(rng.randrange(n))
    variants = []
    for mask in range(1, 16):
        out = {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in inst.items()
            if key != "action_columns"
        }
        out["action_columns"] = [list(row) for row in inst["action_columns"]]
        out["source"] = list(inst["source"])
        out["target"] = list(inst["target"])
        carried = list(inst["answer"])
        if mask & 1:
            out["action_columns"] = [out["action_columns"][i] for i in row_perm]
            tail = [out["target"][i + 1] for i in row_perm]
            out["target"] = [out["target"][0]] + tail
        if mask & 2:
            out["action_columns"] = [
                [row[j] for j in col_perm] for row in out["action_columns"]
            ]
            carried = [carried[j] for j in col_perm]
        if mask & 4:
            row_to = out["action_columns"][shear_to]
            row_from = out["action_columns"][shear_from]
            out["action_columns"][shear_to] = [
                (a + shear_scalar * b) % p for a, b in zip(row_to, row_from)
            ]
            out["target"][shear_to + 1] = (
                out["target"][shear_to + 1]
                + shear_scalar * out["target"][shear_from + 1]
            ) % p
        if mask & 8:
            for j in inverted_columns:
                for i in range(n):
                    out["action_columns"][i][j] = (
                        -out["action_columns"][i][j]
                    ) % p
                carried[j] = (-carried[j]) % p
        out["answer"] = carried
        variants.append(out)
    return variants


def _check_module_laws(inst, seed):
    """Spot-check invertibility and commutation of the displayed actions."""
    rng = random.Random(seed)
    n, p = inst["n"], inst["p"]
    vector = [rng.randrange(p) for _ in range(n + 1)]
    j, k = rng.sample(range(n), 2)

    def act(vec, column, exponent):
        c = vec[0] % p
        tail = [
            (vec[i + 1] + exponent * c * inst["action_columns"][i][column]) % p
            for i in range(n)
        ]
        return [c] + tail

    forward_back = act(act(vector, j, 1), j, -1)
    jk = act(act(vector, j, 1), k, 1)
    kj = act(act(vector, k, 1), j, 1)
    return forward_back == [x % p for x in vector] and jk == kj


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    field_checks = {}
    for name, field in _FIELDS.items():
        exponent = field["mersenne_exponent"]
        field_checks[name] = {
            "prime": (
                _is_prime_64(field["p"])
                if exponent is None
                else _is_mersenne_prime(exponent)
            )
        }

    g1_failures = []
    g1_attempts = 0
    module_law_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
            if _check_module_laws(inst, seed ^ 0x5151):
                module_law_checks += 1
            else:
                g1_failures.append([preset, seed, "module action law failed"])
    all_field_checks = all(all(checks.values()) for checks in field_checks.values())
    report["G1_planted_verifies"] = {
        "pass": not g1_failures
        and all_field_checks
        and module_law_checks == g1_attempts,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "field_primality_checks": field_checks,
        "module_law_checks": module_law_checks,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swap_j = next(i for i in range(1, len(answer)) if answer[i] != answer[0])
    duplicate_j = next(
        i for i in range(len(answer) - 1, 0, -1) if answer[i] != answer[0]
    )
    swapped = list(answer)
    swapped[0], swapped[swap_j] = swapped[swap_j], swapped[0]
    duplicated = list(answer)
    duplicated[duplicate_j] = answer[0]
    out_of_range = list(answer)
    out_of_range[min(4, len(answer) - 1)] = inst["p"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [value["reason"] for value in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The invariant calculation gives this least-residue vector.\n"
        "```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nI used the displayed generator order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x250519141)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_prior": "uniform over all p^n in-range exponent vectors",
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_column_sum_rank",
        "greedy_left_to_right_zero_fill",
        "diagonal_only_relaxation",
        "by_hand_eight_obvious_coupling_scalars",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    compact_successes = 0
    reference_seconds = 0.0
    reference_field_operations = 0
    reference_euclidean_divisions = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        reference_field_operations += counts["field_operations"]
        reference_euclidean_divisions += counts["euclidean_divisions"]
        compact_successes += int(verify(trial, _rank_one_compact_solve(trial))[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact modular Gaussian elimination with back substitution",
        "complexity": "O(n^3) exact field operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_field_operations // 8,
        "euclidean_divisions": reference_euclidean_divisions // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "rank-one Sherman-Morrison scalar solve",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": 7 * inst["n"] + 2,
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8
        and compact_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "exact_density": f"1/{inst['p']}^{inst['n']} (unique nonsingular module equation)",
        "demo_exact_solution_count": demo_count,
        "baseline_attack_name": "random_restart_256",
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and len(render(doubled)) > len(render(inst))
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(
                verify(transformed, transformed["answer"])[0]
            )
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 300
        and real_transform_count == 300
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariance_attempts": 300,
        "real_transformations_verified": real_transform_count,
        "real_transformation_attempts": 300,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "module-coordinate row reordering",
            "Laurent-generator/answer-coordinate reordering",
            "elementary shear change of module basis",
            "replacement of a nonempty subset of X_j by X_j^-1",
            "all nonempty compositions of those four",
        ],
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(inst["answer"])
    worst_case_answer = json.dumps(
        [inst["p"] - 1] * inst["n"], separators=(",", ":")
    )
    worst_case_answer_chars = len(worst_case_answer)
    worst_case_answer_tokens = math.ceil(worst_case_answer_chars / 4)
    intended_operations = 7 * inst["n"] + 2
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else None
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_case_answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "evidence_complete": all(arms[name]["attempts"] > 0 for name in arms),
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_case_answer_chars,
        "worst_case_answer_tokens": worst_case_answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
