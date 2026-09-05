"""Exact free-Lie equation witnesses inspired by arXiv:1708.07419.

Instances live in a rank-three free Lie algebra over a prime field. A witness
is sampled first as a polynomial in a displayed Lie basis. Jacobi's identity
and a finite-field character transform then manufacture the right-hand side,
so generation never solves the equation that it emits.
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
from collections import Counter


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The displayed change-of-basis matrix is the character table of a cyclic "
    "subgroup of the coefficient field."
)
PLACEBO_HINT: str = (
    "The displayed coefficient data rewards careful attention to the indexing "
    "and the arithmetic in the coefficient field."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "rank-three free Lie algebra over a prime field",
        "Hall-basis Lie monomials",
        "polynomial in a displayed Lie basis",
    ],
    "verification_operations": [
        "exact prime-field arithmetic",
        "Jacobi derivation in Hall-basis coordinates",
        "exact polynomial coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize the Jacobi coefficient chain and the finite-field character "
        "table; without that decomposition one performs dense exact elimination."
    ),
    "hardness_basis": (
        "Track B: Hall coefficient matching plus Gaussian elimination over F_p "
        "is O(n^3); at the shipping preset n=32 over F_786433 it takes 36,527 "
        "counted field operations and 0.0014 seconds, while Jacobi recovery plus "
        "an inverse radix-2 number-"
        "theoretic transform takes 273 exact arithmetic operations."
    ),
    "max_answer_tokens": 85,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is the number of displayed Lie-basis terms and must be a power of two.
# The final axis grows the coefficient field and Hall degree at fixed n.
DIFFICULTY: dict = {
    "demo": {"n": 4, "modulus": 17, "degree_pad": 1},
    "easy": {"n": 8, "modulus": 257, "degree_pad": 8},
    "medium": {"n": 16, "modulus": 257, "degree_pad": 32},
    "hard": {"n": 32, "modulus": 786433, "degree_pad": 257},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A dense coordinate polynomial X(z)=sum_{j=0}^{n-1} x_j z^j over "
        "the displayed prime field: exactly n ordered coefficient/exponent "
        "terms [[x_j,[j]],...], with 0 <= x_j < p."
    ),
    "bounds": {
        "max_terms_supported": 128,
        "max_degree_supported": 127,
        "shipping_terms": 32,
        "shipping_coefficient_range": [0, 786432],
    },
}

NOTES: str = (
    "Section 4 fixes the free-Lie objects, the left-normed adjoint notation, "
    "and the Hall basis. Lemma 6 proves the Jacobi recurrence that constructs "
    "an s with a prescribed bracket [s,a]; Lemma 4 gives Hall-basis "
    "faithfulness. Theorem 5 proves only worst-case undecidability through the "
    "K[t] interpretation of Theorem 3, so it cannot support Track A for an "
    "inverse-generated distribution. The chosen bounded coefficient problem "
    "is deliberately disclosed as Track B: dense finite-field elimination "
    "solves it, while the compact route recognizes the character table and "
    "uses its radix-2 inverse transform. Coefficients are sampled i.i.d. before "
    "the equation is built, defeating position or magnitude leakage. The "
    "outlier, diagonal-greedy, random-restart, and unmixed-coordinate attacks "
    "all fail; Gaussian elimination succeeds as the reference algorithm."
)

# Filled from the script-owned hardening transcripts after the three runs.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}

_SUPPORTED_MODULI = (
    17, 257, 65537, 786433, 7340033, 167772161, 469762049, 754974721,
    998244353, 1004535809, 1224736769, 2013265921,
)


def _root_of_two_power_order(modulus, n):
    """Return the least-found element of exact order n in F_modulus."""
    exponent = (modulus - 1) // n
    for base in range(2, 10000):
        root = pow(base, exponent, modulus)
        if pow(root, n, modulus) == 1 and (n == 1 or pow(root, n // 2, modulus) != 1):
            return root
    raise ValueError("could not find a root of the requested order")


def _poly_from_coefficients(coefficients):
    return [[int(value), [j]] for j, value in enumerate(coefficients)]


def _coefficients_from_poly(answer):
    return [term[0] for term in answer]


def _format_answer(answer):
    return ", ".join(f"{term[1][0]}:{term[0]}" for term in answer)


def _matrix_vector(matrix, vector, modulus):
    return [sum(entry * value for entry, value in zip(row, vector)) % modulus
            for row in matrix]


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a free-Lie equation from a sampled polynomial witness.

    ``n`` controls the transform dimension and must be a power of two.
    ``modulus`` and ``degree_pad`` are fixed-answer-length hardness axes. The
    right-hand side is computed from the sampled answer, never inverted.
    """
    modulus = params.pop("modulus", 65537)
    degree_pad = params.pop("degree_pad", 128)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value, lower in (("n", n, 2), ("modulus", modulus, 3),
                               ("degree_pad", degree_pad, 0)):
        if isinstance(value, bool) or not isinstance(value, int) or value < lower:
            raise ValueError(f"{name} must be an integer at least {lower}")
    if n > 128 or n & (n - 1):
        raise ValueError("n must be a power of two no larger than 128")
    if modulus not in _SUPPORTED_MODULI:
        raise ValueError("modulus is not one of the module's certified NTT primes")
    if (modulus - 1) % n:
        raise ValueError("n must divide modulus-1")

    rng = random.Random(seed)
    while True:
        coefficients = [rng.randrange(modulus) for _ in range(n)]
        if len(set(coefficients)) > 1:
            break

    primitive = _root_of_two_power_order(modulus, n)
    # Every odd power of a primitive 2-power root is primitive.
    omega = pow(primitive, 2 * rng.randrange(n // 2) + 1, modulus)
    matrix = [[pow(omega, i * j, modulus) for j in range(n)]
              for i in range(n)]

    # T_i=H(m+i,n-1-i). A large m keeps every T_i and every derivative
    # coordinate in the distinct Hall-basis regime p>q.
    m = 2 * n + degree_pad + 3
    terms = [[m + i, n - 1 - i] for i in range(n)]

    # P_j=sum_i M[i,j]T_i and S=sum_j x_j P_j. First compute its T
    # coefficients, then apply [H(p,q),a]=H(p+1,q)+H(p,q+1).
    t_coefficients = _matrix_vector(matrix, coefficients, modulus)
    rhs = [0] * (n + 1)
    rhs[0] = t_coefficients[0]
    for i in range(1, n):
        rhs[i] = (t_coefficients[i - 1] + t_coefficients[i]) % modulus
    rhs[n] = t_coefficients[-1]

    return {
        "family": "character-mixed Jacobi equation",
        "field_modulus": modulus,
        "n": n,
        "degree_pad": degree_pad,
        "m": m,
        "generators": ["a", "b", "c"],
        "terms": terms,
        "matrix": matrix,
        "rhs_coefficients": rhs,
        "answer": _poly_from_coefficients(coefficients),
    }


def render(inst) -> str:
    a, b, c = inst["generators"]
    modulus = inst["field_modulus"]
    n = inst["n"]
    term_lines = "\n".join(
        f"  T_{i} = H({p},{q})" for i, (p, q) in enumerate(inst["terms"])
    )
    matrix_lines = "\n".join(
        f"  row {i}: " + " ".join(str(value) for value in row)
        for i, row in enumerate(inst["matrix"])
    )
    rhs_line = " ".join(str(value) for value in inst["rhs_coefficients"])
    statement = f"""FREE-LIE POLYNOMIAL WITNESS OVER A PRIME FIELD

Work in the free Lie algebra over the prime field F_{modulus} on the three
free generators {a}, {b}, {c}. Field elements are represented by their unique
integer residues 0,...,{modulus - 1}; every addition and multiplication of
coefficients is modulo {modulus}. The Lie bracket is bilinear,
[u,u]=0, [u,v]=-[v,u], and it satisfies the Jacobi identity. All repeated
brackets are left-normed. Define

  ad_{a}^0(u)=u,    ad_{a}^(r+1)(u)=[ad_{a}^r(u),{a}],
  H(p,q)=[ad_{a}^p({c}), ad_{a}^q({b})].

The Hall order is degree-first with {a}<{b}<{c}. Every H(p,q) used below has
p>q, so the displayed H terms are distinct Hall-basis elements. There are
n={n} displayed terms:
{term_lines}

Define Lie polynomials P_0,...,P_{n - 1} by

  P_j = sum from i=0 to {n - 1} of M[i,j]*T_i.

The matrix M is listed by rows; each row has exactly {n} field residues:
{matrix_lines}

Also put U_r=H({inst['m']}+r,{n}-r) for 0<=r<={n}. The right-hand side R is

  R = sum from r=0 to {n} of q_r*U_r,

where q_0,...,q_{n} in that order are:
  {rhs_line}

Find the unique coordinate polynomial

  X(z)=x_0+x_1*z+...+x_{n - 1}*z^{n - 1}

whose coefficients define S=sum from j=0 to {n - 1} of x_j*P_j and make the
free-Lie identity [S,{a}]=R true. Your answer must contain exactly {n} terms,
one for every exponent 0,...,{n - 1}, in increasing exponent order. Write a
term as exponent:coefficient. Coefficients must be canonical integer residues
in the inclusive range 0..{modulus - 1}; exponents and coefficients are
ordinary decimal integers, and repeated exponents are not allowed.

Give your final answer inside <answer></answer> tags, as exactly {n}
comma-separated exponent:coefficient terms.
Example format for n=3 only: <answer>0:2, 1:0, 2:7</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the last tagged polynomial, tolerating prose and fences."""
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text),
                             re.IGNORECASE | re.DOTALL)
        if not matches:
            return None
        body = matches[-1].strip()
        body = re.sub(r"^```(?:text|json)?\s*", "", body,
                      flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return []
        answer = []
        for token in body.split(","):
            match = re.fullmatch(r"\s*(\d+)\s*:\s*([+-]?\d+)\s*", token)
            if not match:
                return None
            exponent = int(match.group(1))
            coefficient = int(match.group(2))
            answer.append([coefficient, [exponent]])
        return answer
    except (TypeError, ValueError, OverflowError):
        return None


def _validate_polynomial(inst, answer):
    n = inst["n"]
    modulus = inst["field_modulus"]
    if not isinstance(answer, list):
        return None, "answer must be a polynomial term list"
    if len(answer) != n:
        return None, f"expected exactly {n} polynomial terms, got {len(answer)}"
    coefficients = []
    for i, term in enumerate(answer):
        if (not isinstance(term, list) or len(term) != 2
                or isinstance(term[0], bool) or not isinstance(term[0], int)
                or not isinstance(term[1], list) or len(term[1]) != 1
                or isinstance(term[1][0], bool) or not isinstance(term[1][0], int)):
            return None, f"term {i} must be [coefficient,[exponent]]"
        coefficient, exponent_list = term
        exponent = exponent_list[0]
        if exponent != i:
            return None, f"term {i} has exponent {exponent}, expected {i}"
        if not 0 <= coefficient < modulus:
            return None, (f"coefficient of z^{i} is outside the inclusive "
                          f"range 0..{modulus - 1}")
        coefficients.append(coefficient)
    return coefficients, None


def _expanded_derivative(inst, t_coefficients):
    modulus = inst["field_modulus"]
    coordinates = {}
    for coefficient, (p, q) in zip(t_coefficients, inst["terms"]):
        for key in ((p + 1, q), (p, q + 1)):
            coordinates[key] = (coordinates.get(key, 0) + coefficient) % modulus
            if coordinates[key] == 0:
                del coordinates[key]
    return coordinates


def _target_coordinates(inst):
    modulus = inst["field_modulus"]
    n = inst["n"]
    target = {}
    for i, coefficient in enumerate(inst["rhs_coefficients"]):
        coefficient %= modulus
        if coefficient:
            target[(inst["m"] + i, n - i)] = coefficient
    return target


def verify(inst, answer) -> tuple[bool, str]:
    """Substitute and compare exact Hall coordinates; never read inst['answer']."""
    coefficients, error = _validate_polynomial(inst, answer)
    if error:
        return False, error
    modulus = inst["field_modulus"]
    t_coefficients = []
    for row in inst["matrix"]:
        t_coefficients.append(
            sum(entry * value for entry, value in zip(row, coefficients)) % modulus
        )
    got = _expanded_derivative(inst, t_coefficients)
    expected = _target_coordinates(inst)
    if got != expected:
        for p, q in sorted(set(got) | set(expected)):
            actual = got.get((p, q), 0)
            wanted = expected.get((p, q), 0)
            if actual != wanted:
                return False, (f"Lie identity mismatch at Hall coordinate "
                               f"H({p},{q}): got {actual}, expected {wanted}")
        return False, "Lie identity mismatch"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    modulus = inst["field_modulus"]
    return _poly_from_coefficients(
        [rng.randrange(modulus) for _ in range(inst["n"])]
    )


def search_space(inst) -> int | None:
    return inst["field_modulus"] ** inst["n"]


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for coefficients in itertools.product(range(inst["field_modulus"]),
                                          repeat=inst["n"]):
        ok, _ = verify(inst, _poly_from_coefficients(coefficients))
        count += int(ok)
    return count


def canonical_key(inst) -> str:
    """Canonicalize row order, displayed-basis order, and generator names."""
    n = inst["n"]
    columns = []
    for j in range(n):
        polynomial = sorted(
            (inst["terms"][i][0], inst["terms"][i][1], inst["matrix"][i][j])
            for i in range(n)
        )
        columns.append(polynomial)
    target = sorted(
        (inst["m"] + i, n - i, value)
        for i, value in enumerate(inst["rhs_coefficients"])
    )
    payload = {
        "field_modulus": inst["field_modulus"],
        "columns": sorted(columns),
        "target": target,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase field size and Hall degree while keeping answer length fixed."""
    harder = dict(params)
    current = int(harder.get("modulus", 65537))
    choices = [value for value in _SUPPORTED_MODULI
               if value > current and (value - 1) % int(harder.get("n", 32)) == 0]
    harder["modulus"] = choices[0] if choices else current
    harder["degree_pad"] = int(harder.get("degree_pad", 128)) * 2 + 1
    harder["n"] = int(harder.get("n", 32))
    return harder


def _recover_t_from_rhs(inst):
    modulus = inst["field_modulus"]
    rhs = inst["rhs_coefficients"]
    t = [rhs[0]]
    for i in range(1, inst["n"]):
        t.append((rhs[i] - t[-1]) % modulus)
    return t


def _inverse_counted(value, modulus):
    exponent = modulus - 2
    result = 1
    base = value % modulus
    operations = 0
    while exponent:
        if exponent & 1:
            result = result * base % modulus
            operations += 1
        exponent >>= 1
        if exponent:
            base = base * base % modulus
            operations += 1
    return result, operations


def _gaussian_reference(inst):
    """Generic exact Hall matching and Gauss-Jordan elimination over F_p."""
    modulus = inst["field_modulus"]
    n = inst["n"]
    t = _recover_t_from_rhs(inst)
    operations = n - 1
    augmented = [[value % modulus for value in row] + [t[i]]
                 for i, row in enumerate(inst["matrix"])]
    for column in range(n):
        pivot = next((row for row in range(column, n)
                      if augmented[row][column] % modulus), None)
        if pivot is None:
            return None, operations
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        inverse, inverse_ops = _inverse_counted(augmented[column][column], modulus)
        operations += inverse_ops
        for j in range(column, n + 1):
            augmented[column][j] = augmented[column][j] * inverse % modulus
            operations += 1
        for row in range(n):
            if row == column or not augmented[row][column]:
                continue
            factor = augmented[row][column]
            for j in range(column, n + 1):
                augmented[row][j] = (
                    augmented[row][j] - factor * augmented[column][j]
                ) % modulus
                operations += 2
    return _poly_from_coefficients([row[-1] for row in augmented]), operations


def _compact_reference(inst):
    """The intended radix-2 route, with every field operation counted."""
    modulus = inst["field_modulus"]
    n = inst["n"]
    t = _recover_t_from_rhs(inst)
    operations = n - 1
    # Checking the second boundary coefficient costs one subtraction.
    operations += 1
    if (t[-1] - inst["rhs_coefficients"][n]) % modulus:
        return None, operations

    # M[i,j]=omega^(i*j).  The inverse transform has root omega^-1.
    # Its twiddles are already entries of column 1, so looking them up does not
    # smuggle uncounted modular exponentiation into the compact route.
    def inverse_transform(values):
        nonlocal operations
        size = len(values)
        if size == 1:
            return values
        even = inverse_transform(values[0::2])
        odd = inverse_transform(values[1::2])
        half = size // 2
        step = n // size
        out = [0] * size
        for j in range(half):
            twiddle = inst["matrix"][(-j * step) % n][1]
            value = odd[j]
            if twiddle != 1:
                value = value * twiddle % modulus
                operations += 1
            out[j] = (even[j] + value) % modulus
            out[j + half] = (even[j] - value) % modulus
            operations += 2
        return out

    coefficients = inverse_transform(t)
    # Since n divides p-1, n^{-1}=p-(p-1)/n in F_p.
    inverse_n = modulus - (modulus - 1) // n
    coefficients = [value * inverse_n % modulus for value in coefficients]
    operations += n
    return _poly_from_coefficients(coefficients), operations


def _attack_outlier_singleton(inst):
    """Guess each coefficient from the modal one-variable row explanation."""
    modulus = inst["field_modulus"]
    t = _recover_t_from_rhs(inst)
    guess = []
    for j in range(inst["n"]):
        implied = [t[i] * pow(inst["matrix"][i][j], modulus - 2, modulus) % modulus
                   for i in range(inst["n"])]
        counts = Counter(implied)
        guess.append(min(counts, key=lambda value: (-counts[value], value)))
    return _poly_from_coefficients(guess)


def _attack_greedy_diagonal(inst):
    modulus = inst["field_modulus"]
    t = _recover_t_from_rhs(inst)
    guess = [0] * inst["n"]
    for j in range(inst["n"]):
        residual = (t[j] - sum(inst["matrix"][j][ell] * guess[ell]
                               for ell in range(j))) % modulus
        guess[j] = residual * pow(inst["matrix"][j][j], modulus - 2, modulus) % modulus
    return _poly_from_coefficients(guess)


def _attack_unmixed(inst):
    return _poly_from_coefficients(_recover_t_from_rhs(inst))


def _permuted_columns(inst, permutation):
    out = dict(inst)
    out["matrix"] = [[row[j] for j in permutation] for row in inst["matrix"]]
    old = _coefficients_from_poly(inst["answer"])
    out["answer"] = _poly_from_coefficients([old[j] for j in permutation])
    return out


def _permuted_rows(inst, permutation):
    out = dict(inst)
    out["matrix"] = [list(inst["matrix"][i]) for i in permutation]
    out["terms"] = [list(inst["terms"][i]) for i in permutation]
    out["answer"] = json.loads(json.dumps(inst["answer"]))
    return out


def _renamed_instance(inst):
    out = dict(inst)
    out["generators"] = ["alpha", "beta", "gamma"]
    out["answer"] = json.loads(json.dumps(inst["answer"]))
    return out


def _answer_metrics(params):
    max_chars = max_tokens = max_elements = 0
    for seed in range(20):
        answer = make_instance(seed=seed, **params)["answer"]
        body = _format_answer(answer)
        max_chars = max(max_chars, len(body))
        max_tokens = max(max_tokens, (len(body) + 3) // 4)
        max_elements = max(max_elements, 2 * len(answer))
    return max_chars, max_tokens, max_elements


def selftest() -> dict:
    report = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=9137, **shipping)
    planted = json.loads(json.dumps(inst["answer"]))
    unequal = next(i for i in range(inst["n"] - 1)
                   if planted[i][0] != planted[i + 1][0])
    swapped = json.loads(json.dumps(planted))
    swapped[unequal][0], swapped[unequal + 1][0] = (
        swapped[unequal + 1][0], swapped[unequal][0]
    )
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": planted + [planted[0]],
        "empty": [],
        "out_of_range": [[inst["field_modulus"], [0]]] + planted[1:],
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        reasons[name] = "unexpectedly accepted" if ok else reason
    report["G2_rejects_corruption"] = {
        "pass": all(value != "unexpectedly accepted" for value in reasons.values())
        and len(set(reasons.values())) == len(reasons),
        "rejected": sum(value != "unexpectedly accepted" for value in reasons.values()),
        "distinct_reasons": len(set(reasons.values())), "reasons": reasons,
    }

    response = ("The polynomial coefficients follow.\n```text\n<answer>" +
                _format_answer(inst["answer"]) +
                "</answer>\n```\nAll arithmetic is modulo p.")
    parsed = parse_answer(response)
    garbage = ["", "no tagged answer", "<answer>0=x</answer>",
               "<answer>0:1,</answer>"]
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"]
        and all(parse_answer(text) is None for text in garbage),
        "realistic_response_parsed": parsed == inst["answer"],
        "garbage_rejected": sum(parse_answer(text) is None for text in garbage),
    }

    samples = 200_000
    rng = random.Random(0x170807419)
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        ok, _ = verify(inst, random_candidate(inst, rng))
        hits += int(ok)
    guess_seconds = time.perf_counter() - start
    fraction = hits / samples
    report["G4_guess_resistance"] = {
        "pass": fraction < 1e-6, "hits": hits, "total": samples,
        "observed_fraction": fraction,
        "candidate_space": str(search_space(inst)), "structure_aware": True,
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=5, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_counts = {
        "outlier_modal_singleton": 0,
        "greedy_diagonal_one_pass": 0,
        "random_restart_256": 0,
        "obvious_unmixed_coordinates": 0,
    }
    attack_seeds = list(range(8))
    restart_checks = reference_successes = 0
    reference_times = []
    reference_operations = []
    compact_successes = 0
    compact_operations = []
    attack_start = time.perf_counter()
    for seed in attack_seeds:
        test_inst = make_instance(seed=seed + 2000, **shipping)
        for name, function in (
            ("outlier_modal_singleton", _attack_outlier_singleton),
            ("greedy_diagonal_one_pass", _attack_greedy_diagonal),
            ("obvious_unmixed_coordinates", _attack_unmixed),
        ):
            ok, _ = verify(test_inst, function(test_inst))
            attack_counts[name] += int(ok)
        local_rng = random.Random(seed + 9000)
        solved = False
        for _ in range(256):
            restart_checks += 1
            ok, _ = verify(test_inst, random_candidate(test_inst, local_rng))
            solved |= ok
        attack_counts["random_restart_256"] += int(solved)

        reference_start = time.perf_counter()
        answer, operations = _gaussian_reference(test_inst)
        reference_times.append(time.perf_counter() - reference_start)
        reference_operations.append(operations)
        ok, _ = verify(test_inst, answer)
        reference_successes += int(ok)
        compact_answer, compact_ops = _compact_reference(test_inst)
        compact_operations.append(compact_ops)
        compact_ok, _ = verify(test_inst, compact_answer)
        compact_successes += int(compact_ok)
    attack_seconds = time.perf_counter() - attack_start
    reference_wall = statistics.median(reference_times)
    reference_ops = int(statistics.median(reference_operations))
    report["G5_density_and_baseline"] = {
        "pass": fraction < 1e-6 and demo_count == 1
        and reference_successes == len(attack_seeds),
        "shipping_density_hits": hits, "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": fraction,
        "exact_demo_valid_answers": demo_count,
        "exact_demo_candidate_space": search_space(demo),
        "strongest_failing_attack_wall_sec": round(attack_seconds, 6),
        "strongest_failing_attack_candidate_checks": restart_checks,
        "reference_wall_clock_sec": round(reference_wall, 6),
        "reference_field_operations": reference_ops,
        "compact_route_field_operations": max(compact_operations),
        "compact_route_solves": f"{compact_successes}/{len(attack_seeds)}",
    }
    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Hall coefficient matching plus exact Gauss-Jordan elimination",
            "complexity": "O(n^3) prime-field operations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_ops,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated_params = escalate(shipping)
    escalated = make_instance(seed=78, **escalated_params)
    escalated_ok, escalated_reason = verify(escalated, escalated["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok
        and doubled["n"] == 2 * inst["n"]
        and escalated["field_modulus"] > inst["field_modulus"],
        "base_terms": inst["n"], "doubled_terms": doubled["n"],
        "base_modulus": inst["field_modulus"],
        "escalated_modulus": escalated["field_modulus"],
        "doubled_verify_reason": doubled_reason,
        "fixed_length_escalation_verify_reason": escalated_reason,
    }

    invariant_checks = preserving_checks = 0
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=seed + 4000, **shipping)
        permutation = list(range(original["n"]))
        random.Random(seed + 5000).shuffle(permutation)
        row_permutation = list(range(original["n"]))
        random.Random(seed + 6000).shuffle(row_permutation)
        column_changed = _permuted_columns(original, permutation)
        row_changed = _permuted_rows(original, row_permutation)
        renamed = _renamed_instance(original)
        composed = _renamed_instance(_permuted_rows(column_changed, row_permutation))
        original_key = canonical_key(original)
        for transformed in (column_changed, row_changed, renamed, composed):
            invariant_checks += 1
            if (canonical_key(transformed) == original_key
                    and verify(transformed, transformed["answer"])[0]):
                preserving_checks += 1
        unrelated_keys.append(original_key)
    report["G8_canonical_key"] = {
        "pass": preserving_checks == invariant_checks
        and len(set(unrelated_keys)) == len(unrelated_keys),
        "invariance_checks": invariant_checks,
        "preserving_transformations_verified": preserving_checks,
        "unrelated_instances": len(unrelated_keys),
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "transformations": ["displayed-basis permutation",
                            "Hall-term row reordering",
                            "free-generator renaming", "their composition"],
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(shipping)
    compact_answer, intended_operations = _compact_reference(inst)
    compact_ok, _ = verify(inst, compact_answer)
    arms = G9_RESULTS["arms"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps and compact_ok, "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars, "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verifies": compact_ok,
    }

    report["all_passed"] = all(
        result.get("pass", False) for key, result in report.items()
        if key.startswith("G") and isinstance(result, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
