"""Verified Track-B generator for arXiv:2402.17528.

The family uses Lemma 1.6 and the skew-conference construction in Section 2.2.
It is standard-library-only; gvlib is imported opportunistically as requested by
the corpus contract, but no helper is needed for these two polynomial terms.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import time

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "A simultaneous signed permutation preserves the spectrum, and the underlying "
    "skew conference matrix obeys a quadratic matrix identity."
)
PLACEBO_HINT: str = (
    "The indexing conventions and coefficient signs both deserve careful attention "
    "throughout this exact integer calculation."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "signed-permuted shifted Paley conference matrix over Z",
        "characteristic polynomial over Z[x]",
    ],
    "verification_operations": [
        "deterministic primality and congruence checks",
        "exact integer polynomial-coefficient expansion",
        "exact exponent and rational-coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Discard the displayed signed relabelling, use the conference-matrix "
        "quadratic identity to factor the characteristic polynomial, and extract "
        "only two coefficients; without this invariant one expands the matrix and "
        "runs a cubic exact trace/Newton calculation."
    ),
    "hardness_basis": (
        "Track B: the reference trace/Newton characteristic-coefficient algorithm "
        "is O(v^3) exact arithmetic; at the candidate shipping preset v=180 it is "
        "measured by selftest at 11,825,836 scalar operations and 8.82 seconds on the builder host, whereas "
        "the quadratic-identity factor expansion uses at most 30 exact arithmetic "
        "operations."
    ),
    "max_answer_tokens": 29,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "coeff_bits": 3},
    "easy": {"n": 127, "coeff_bits": 27},
    "medium": {"n": 179, "coeff_bits": 34},
    "hard": {"n": 251, "coeff_bits": 41},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A two-term univariate polynomial fragment in canonical JSON form: each "
        "term is [[numerator,1],[exponent]], the exponents are v-3 then v-4, "
        "the first coefficient is a negative integer of magnitude at most B3, "
        "and the second is a nonnegative integer at most B4; B3 and B4 are the "
        "explicit Hadamard bounds printed in the instance."
    ),
    "bounds": {
        "terms": 2,
        "variables": 1,
        "denominator": 1,
        "degree_offsets": [3, 4],
        "shipping_max_abs_first_numerator": 29080716060541567157841665858810182920,
        "shipping_max_second_numerator": 58953141924832405364852413985576442290080312614480,
        "shipping_coefficient_bits": 34,
        "shipping_atomic_elements": 6,
    },
}

NOTES: str = (
    "Section 1.4 fixes principal submatrices and D_A(k). Lemma 1.6 in Section "
    "1.5 identifies the coefficient of x^(v-k) in det(xI-A) with (-1)^k "
    "times the sum of all k-principal minors. Section 2.2 defines skew "
    "conference matrices and the Paley construction; Example 2.4 gives "
    "det(xI-S)=(x^2+q)^((q+1)/2) for order q+1. Remark 2.6 identifies the "
    "trivial two-eigenvalue regime with minimum multiplicity one, which is "
    "avoided here. Track A would be false: a generic characteristic polynomial "
    "is computable in polynomial time. The generator instead declares Track B, "
    "measures an exact trace/Newton reference algorithm, and inverse-transforms "
    "the paper's matrix by a random simultaneous permutation, diagonal sign "
    "congruence, scalar multiplication, and diagonal shift. Raw diagonal, "
    "one-row, random-restart, and unscaled-quadratic guesses are all tested."
)


# The three arms remain explicitly unclaimed until their script-owned runs complete.
# They are diagnostics under the 2026-09-05 contract; only the size/effort caps gate G9.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run_openrouter_key_limit",
}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin for the 64-bit size parameters supported."""
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


def _prime_at_least(n: int) -> int:
    """First prime q >= n with q == 3 (mod 4)."""
    if n < 3:
        n = 3
    candidate = n + ((3 - n) % 4)
    while not _is_prime_64(candidate):
        candidate += 4
    return candidate


def _coefficient_values(q: int, diagonal: int, scale: int):
    """Two leading nontrivial coefficients of ((x-d)^2+q*u^2)^m."""
    v = q + 1
    m = v // 2
    a = -2 * diagonal
    b = diagonal * diagonal + q * scale * scale
    c3 = math.comb(m, 3) * a**3 + m * (m - 1) * a * b
    c4 = (
        math.comb(m, 4) * a**4
        + m * math.comb(m - 1, 2) * a * a * b
        + math.comb(m, 2) * b * b
    )
    return c3, c4


def _certificate(v: int, c3: int, c4: int):
    return [
        [[c3, 1], [v - 3]],
        [[c4, 1], [v - 4]],
    ]


def _compact_certificate(inst):
    c3, c4 = _coefficient_values(inst["q"], inst["diagonal"], inst["scale"])
    return _certificate(inst["v"], c3, c4), {
        "exact_operations": 30,
        "factor": "((x-diagonal)^2 + q*scale^2)^((q+1)/2)",
    }


def _coefficient_bounds_values(v: int, diagonal: int, scale: int):
    magnitude = max(abs(diagonal), abs(scale))
    b3 = 6 * math.comb(v, 3) * magnitude**3
    b4 = 16 * math.comb(v, 4) * magnitude**4
    return b3, b4


def make_instance(n, seed=0, **params) -> dict:
    """Transform a Paley skew-conference matrix with a known polynomial witness."""
    n = int(n)
    if n < 3 or n > 1_000_000_000:
        raise ValueError("n must lie in [3, 1000000000]")
    coeff_bits = int(params.get("coeff_bits", 27))
    if coeff_bits < 1 or coeff_bits > 400:
        raise ValueError("coeff_bits must lie in [1,400]")
    q = _prime_at_least(n)
    v = q + 1
    rng = random.Random(seed)
    low = 1 if coeff_bits == 1 else 1 << (coeff_bits - 1)
    high = 1 << coeff_bits
    diagonal = rng.randrange(low, high)
    scale = rng.randrange(low, high)

    permutation = list(range(v))
    rng.shuffle(permutation)
    switches = [1 if rng.randrange(2) else -1 for _ in range(v)]
    c3, c4 = _coefficient_values(q, diagonal, scale)
    bound3, bound4 = _coefficient_bounds_values(v, diagonal, scale)
    return {
        "n": n,
        "q": q,
        "v": v,
        "coeff_bits": coeff_bits,
        "diagonal": diagonal,
        "scale": scale,
        "permutation": permutation,
        "switches": switches,
        "bound3": bound3,
        "bound4": bound4,
        "answer": _certificate(v, c3, c4),
    }


def render(inst) -> str:
    """Render the exact implicit matrix and polynomial-certificate task."""
    q = inst["q"]
    v = inst["v"]
    statement = f"""Recover two exact coefficients of a transformed Paley conference matrix.

All indexing is 0-based. Let q={q}, an odd prime congruent to 3 modulo 4, and
let v=q+1={v}. The projective point set is {{0,1,...,q-1,infinity}}; in the
integer data below, the value q represents infinity.

For a nonzero finite residue z modulo q, its Legendre symbol chi(z) is +1 when
z is a square modulo q and -1 otherwise. Define the v by v skew matrix C,
whose rows and columns are indexed by the projective points, by

  C[r,r] = 0;
  C[infinity,s] = -1 and C[s,infinity] = +1 for finite s;
  C[r,s] = -chi(r-s) for distinct finite r,s (reduce r-s modulo q).

The displayed matrix B is specified without printing all v^2 entries. Put
d={inst['diagonal']} and u={inst['scale']}. For displayed indices i,j, let
pi and eps be the following permutation and sign list:

pi  = {json.dumps(inst['permutation'], separators=(',', ':'))}
eps = {json.dumps(inst['switches'], separators=(',', ':'))}

Then B[i,i]=d and, for i != j,

  B[i,j] = u * eps[i] * eps[j] * C[pi[i],pi[j]].

Let f(x)=det(x I_v-B), a monic polynomial over the integers. Return exactly
the terms of f at exponents v-3={v - 3} and v-4={v - 4}, in that descending
order. A term is encoded as [[numerator,denominator],[exponent]]. Here both
denominators must be exactly 1. Do not include zero terms or any other terms.

For the bounded certificate language, the first numerator must lie in the
inclusive range -B3 <= value <= -1 with B3={inst['bound3']}; the second must
lie in 0 <= value <= B4 with B4={inst['bound4']}.

Give your final answer inside <answer></answer> tags, as a JSON list containing
exactly the two terms just defined.
Syntax-only example: <answer>[[[-1,1],[{v - 3}]],[[1,1],[{v - 4}]]]</answer>
(The illustrative numerators -1 and 1 are not the answer.)
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the last tagged JSON value, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _validate_instance(inst):
    q = inst.get("q")
    v = inst.get("v")
    if not _is_int(q) or not _is_int(v) or v != q + 1:
        return False, "instance order parameters are malformed"
    if q % 4 != 3 or not _is_prime_64(q):
        return False, "q must be prime and congruent to 3 modulo 4"
    if not _is_int(inst.get("diagonal")) or inst["diagonal"] <= 0:
        return False, "diagonal shift must be a positive integer"
    if not _is_int(inst.get("scale")) or inst["scale"] <= 0:
        return False, "matrix scale must be a positive integer"
    permutation = inst.get("permutation")
    if not isinstance(permutation, list) or len(permutation) != v:
        return False, "pi must contain exactly v entries"
    if any(not _is_int(x) for x in permutation) or set(permutation) != set(range(v)):
        return False, "pi must be a permutation of 0 through q"
    switches = inst.get("switches")
    if not isinstance(switches, list) or len(switches) != v:
        return False, "eps must contain exactly v entries"
    if any(x not in (-1, 1) for x in switches):
        return False, "every eps entry must be +1 or -1"
    return True, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Verify the canonical polynomial fragment by exact integer expansion."""
    valid, reason = _validate_instance(inst)
    if not valid:
        return False, reason
    if not isinstance(answer, list):
        return False, "answer must be a JSON polynomial list"
    if not answer:
        return False, "answer polynomial must be nonempty"
    if len(answer) < 2:
        return False, "certificate is missing one of the two required terms"
    if len(answer) > 2:
        return False, "extra polynomial terms are not permitted"
    expected_exponents = (inst["v"] - 3, inst["v"] - 4)
    numerators = []
    for index, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term {index} must be [coefficient, exponent-list]"
        coefficient, exponent = term
        if not isinstance(coefficient, list) or len(coefficient) != 2:
            return False, f"term {index} coefficient must be [numerator,denominator]"
        numerator, denominator = coefficient
        if not _is_int(numerator):
            return False, f"term {index} numerator must be an integer"
        if denominator != 1 or isinstance(denominator, bool):
            return False, f"term {index} denominator must be exactly 1"
        if exponent != [expected_exponents[index]]:
            return False, (
                f"term {index} exponent must be [{expected_exponents[index]}] "
                "in descending order"
            )
        numerators.append(numerator)
    if not -inst["bound3"] <= numerators[0] <= -1:
        return False, "the x^(v-3) numerator is outside the stated bound"
    if not 0 <= numerators[1] <= inst["bound4"]:
        return False, "the x^(v-4) numerator is outside the stated bound"

    c3, c4 = _coefficient_values(inst["q"], inst["diagonal"], inst["scale"])
    if numerators[0] != c3:
        return False, "the x^(v-3) coefficient is incorrect"
    if numerators[1] != c4:
        return False, "the x^(v-4) coefficient is incorrect"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample the exact signed, bounded, fixed-support certificate language."""
    c3 = -rng.randint(1, inst["bound3"])
    c4 = rng.randint(0, inst["bound4"])
    return _certificate(inst["v"], c3, c4)


def search_space(inst) -> int | None:
    return inst["bound3"] * (inst["bound4"] + 1)


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 500_000:
        return None
    count = 0
    for magnitude in range(1, inst["bound3"] + 1):
        for c4 in range(inst["bound4"] + 1):
            if verify(inst, _certificate(inst["v"], -magnitude, c4))[0]:
                count += 1
    return count


def canonical_key(inst) -> str:
    """Quotient simultaneous index permutations and diagonal sign congruence."""
    valid, reason = _validate_instance(inst)
    if not valid:
        raise ValueError(reason)
    payload = {
        "family": "paley-conference-leading-coefficients-v1",
        "q": inst["q"],
        "diagonal": inst["diagonal"],
        "scale": inst["scale"],
        "degrees": [inst["v"] - 3, inst["v"] - 4],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow matrix order and coefficient entropy without adding answer terms."""
    out = dict(params)
    current_n = int(out["n"])
    current_bits = int(out.get("coeff_bits", 27))
    next_n = min(1_000_000_000, current_n * 2 + 1)
    next_bits = min(400, current_bits + 8)
    trial = {"n": next_n, "coeff_bits": next_bits}
    trial_inst = make_instance(seed=98765, **trial)
    answer_chars = len(json.dumps(trial_inst["answer"], separators=(",", ":")))
    if answer_chars > 2000:
        return "cap_bound"
    if next_n == current_n and next_bits == current_bits:
        return "cap_bound"
    return trial


def _legendre_table(q: int):
    table = bytearray(q)
    for value in range(1, (q + 1) // 2):
        table[value * value % q] = 1
    return table


def _base_conference_entry(left: int, right: int, q: int, residues) -> int:
    if left == right:
        return 0
    if left == q:
        return -1
    if right == q:
        return 1
    return -1 if residues[(left - right) % q] else 1


def _expand_matrix(inst):
    """Expand B exactly, deliberately without using its spectral shortcut."""
    q, v = inst["q"], inst["v"]
    residues = _legendre_table(q)
    pi = inst["permutation"]
    eps = inst["switches"]
    diagonal = inst["diagonal"]
    scale = inst["scale"]
    matrix = [[0] * v for _ in range(v)]
    for i in range(v):
        matrix[i][i] = diagonal
        for j in range(i + 1, v):
            value = (
                scale
                * eps[i]
                * eps[j]
                * _base_conference_entry(pi[i], pi[j], q, residues)
            )
            matrix[i][j] = value
            matrix[j][i] = -value
    return matrix


def _reference_trace_newton(inst):
    """Generic O(v^3) trace/Newton coefficient algorithm for the expanded B."""
    started = time.perf_counter()
    matrix = _expand_matrix(inst)
    q = inst["q"]
    v = inst["v"]
    square = [[0] * v for _ in range(v)]
    for i in range(v):
        row_i = matrix[i]
        out_i = square[i]
        for k in range(v):
            left = row_i[k]
            row_k = matrix[k]
            for j in range(v):
                out_i[j] += left * row_k[j]

    trace1 = sum(matrix[i][i] for i in range(v))
    trace2 = sum(square[i][i] for i in range(v))
    trace3 = sum(
        square[i][j] * matrix[j][i] for i in range(v) for j in range(v)
    )
    trace4 = sum(
        square[i][j] * square[j][i] for i in range(v) for j in range(v)
    )
    e1 = trace1
    e2 = (e1 * trace1 - trace2) // 2
    e3 = (e2 * trace1 - e1 * trace2 + trace3) // 3
    e4 = (e3 * trace1 - e2 * trace2 + e1 * trace3 - trace4) // 4
    candidate = _certificate(v, -e3, e4)

    residue_operations = q - 1
    entry_operations = 2 * v * (v - 1)
    square_operations = 2 * v**3 - v**2
    trace_operations = 4 * v**2
    newton_operations = 18
    return candidate, {
        "wall_clock_sec": time.perf_counter() - started,
        "exact_operations": (
            residue_operations
            + entry_operations
            + square_operations
            + trace_operations
            + newton_operations
        ),
        "matrix_order": v,
    }


def _attack_diagonal_only(inst):
    v, d = inst["v"], inst["diagonal"]
    return _certificate(v, -math.comb(v, 3) * d**3, math.comb(v, 4) * d**4)


def _attack_greedy_first_row(inst):
    matrix = _expand_matrix(inst)
    v = inst["v"]
    effective = sum(matrix[0])
    return _certificate(
        v,
        -math.comb(v, 3) * effective**3,
        math.comb(v, 4) * effective**4,
    )


def _attack_random_restart(inst, rng, restarts=256):
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_unscaled_quadratic(inst):
    """Obvious by-hand ansatz: use eigenvalues d +/- i*u, omitting q."""
    c3, c4 = _coefficient_values(1, inst["diagonal"], inst["scale"])
    return _certificate(inst["v"], c3, c4)


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value):
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, list):
            return sum(atoms(item) for item in value)
        return 1

    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": atoms(answer),
    }


def _worst_answer_size(params):
    q = _prime_at_least(int(params["n"]))
    bits = int(params.get("coeff_bits", 27))
    maximum = (1 << bits) - 1
    c3, c4 = _coefficient_values(q, maximum, maximum)
    return _answer_size(_certificate(q + 1, c3, c4))


def _transform_reorder(inst, order):
    out = copy.deepcopy(inst)
    out["permutation"] = [inst["permutation"][i] for i in order]
    out["switches"] = [inst["switches"][i] for i in order]
    return out


def _transform_switch(inst, signs):
    out = copy.deepcopy(inst)
    out["switches"] = [a * b for a, b in zip(inst["switches"], signs)]
    return out


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    attempts = 0
    json_roundtrips = 0
    compact_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, "plant", reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
            compact, _ = _compact_certificate(inst)
            compact_ok, compact_reason = verify(inst, compact)
            compact_checks += 1
            if not compact_ok:
                failures.append([preset, seed, "compact", compact_reason])
    report["G1_planted_verifies"] = {
        "pass": not failures
        and json_roundtrips == attempts
        and compact_checks == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "independent_compact_route_checks": compact_checks,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    drop = copy.deepcopy(answer)
    drop.pop()
    swapped = [copy.deepcopy(answer[1]), copy.deepcopy(answer[0])]
    duplicate = copy.deepcopy(answer) + [copy.deepcopy(answer[0])]
    out_of_range = copy.deepcopy(answer)
    out_of_range[0][0][1] = 0
    corruptions = {
        "drop_one_term": drop,
        "swap_terms": swapped,
        "duplicate_term": duplicate,
        "empty": [],
        "out_of_range_denominator": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
    }

    realistic = (
        "Using exact arithmetic, I obtain the requested fragment.\n\n```json\n"
        "<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage without tags") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("garbage without tags") is None,
    }

    samples = 200_000
    sample_rng = random.Random(0x240217528)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, sample_rng))[0]:
            hits += 1
    space = search_space(inst)
    exact_probability = 1.0 / space
    report["G4_guess_resistance"] = {
        "pass": exact_probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": exact_probability,
        "structure_aware_space": space,
        "sampler": (
            "uniform over the two fixed exponents, unit denominators, forced signs, "
            "and the exact printed Hadamard coefficient bounds"
        ),
    }

    # This gate needs a preset small enough for enumerate_all() to run
    # exhaustively.  It used to read DIFFICULTY["demo"], which silently coupled it
    # to the illustration rung: prompts/codex_task.md defines demo as the rung a
    # person can solve on paper, and a demo that is also DIVERSE across seeds
    # necessarily exceeds enumerate_all()'s internal cap, at which point it returns
    # None and this gate breaks on a module that is perfectly healthy.  The
    # measurement size is therefore pinned here, independent of the ladder -- these
    # are exactly the params the gate measured before, so its behaviour is
    # unchanged.
    G5_ENUMERATION_PARAMS = {"n": 3, "coeff_bits": 1}
    demo_inst = make_instance(seed=3, **G5_ENUMERATION_PARAMS)
    demo_count = enumerate_all(demo_inst)
    attack_results = {
        "outlier_diagonal_only": {"successes": 0, "attempts": 0},
        "greedy_first_row_effective_root": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_unscaled_quadratic_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    compact_successes = 0
    compact_times = []
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_diagonal_only": _attack_diagonal_only(attacked),
            "greedy_first_row_effective_root": _attack_greedy_first_row(attacked),
            "random_restart_256": _attack_random_restart(
                attacked, random.Random(seed ^ 0xA5A5), 256
            ),
            "in_context_unscaled_quadratic_ansatz": _attack_unscaled_quadratic(
                attacked
            ),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        reference, stats = _reference_trace_newton(attacked)
        reference_times.append(stats["wall_clock_sec"])
        reference_operations.append(stats["exact_operations"])
        if verify(attacked, reference)[0]:
            reference_successes += 1

        started = time.perf_counter()
        compact, compact_stats = _compact_certificate(attacked)
        compact_times.append(time.perf_counter() - started)
        compact_operations.append(compact_stats["exact_operations"])
        if verify(attacked, compact)[0]:
            compact_successes += 1

    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    reference_median_time = statistics.median(reference_times)
    reference_median_ops = int(statistics.median(reference_operations))
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "expanded-matrix trace/Newton characteristic coefficients",
            "complexity": "O(v^3) exact integer arithmetic",
            "median_wall_clock_sec": round(reference_median_time, 6),
            "median_operations": reference_median_ops,
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "conference quadratic identity and two-term factor expansion",
            "complexity": "O(1) exact big-integer arithmetic for fixed offsets 3,4",
            "median_wall_clock_sec": round(statistics.median(compact_times), 8),
            "median_operations": int(statistics.median(compact_operations)),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == 8,
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_exact_solution_count": 1,
        "shipping_exact_solution_fraction": exact_probability,
        "demo_exact_solution_count": demo_count,
        "strongest_attack": "expanded-matrix trace/Newton",
        "reference_median_wall_seconds": round(reference_median_time, 6),
        "reference_median_operations": reference_median_ops,
    }

    doubled = make_instance(
        n=2 * ship_params["n"],
        coeff_bits=ship_params["coeff_bits"] + 1,
        seed=77,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    shipping_v = inst["v"]
    doubled_v = doubled["v"]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_v >= 2 * shipping_v,
        "shipping_n": ship_params["n"],
        "shipping_matrix_order": shipping_v,
        "doubled_n": 2 * ship_params["n"],
        "doubled_matrix_order": doubled_v,
        "reference_operation_growth_factor": (doubled_v / shipping_v) ** 3,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **ship_params)
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        rng = random.Random(8000 + seed)
        order1 = list(range(original["v"]))
        order2 = list(range(original["v"]))
        rng.shuffle(order1)
        rng.shuffle(order2)
        signs1 = [1 if rng.randrange(2) else -1 for _ in range(original["v"])]
        signs2 = [1 if rng.randrange(2) else -1 for _ in range(original["v"])]
        reordered = _transform_reorder(original, order1)
        switched = _transform_switch(original, signs1)
        composed = _transform_switch(
            _transform_reorder(_transform_switch(original, signs2), order2),
            signs1,
        )
        for variant in (reordered, switched, composed):
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append([seed, "key changed under relabelling"])
            witness_checks += 1
            if not verify(variant, original["answer"])[0]:
                invariant_failures.append([seed, "original witness did not carry"])
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "symmetries": (
            "two simultaneous input reorderings, two diagonal sign congruences, "
            "and their compositions"
        ),
        "key_basis": (
            "SHA-256 of q, diagonal, scale, and requested degrees after quotienting "
            "the displayed permutation and signs; never the seed or render text"
        ),
    }

    size = _answer_size(answer)
    worst_size = _worst_answer_size(ship_params)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0
    )
    intended_operations = max(compact_operations)
    within_caps = (
        size["chars"] <= 2000
        and size["elements"] <= 256
        and worst_size["chars"] <= 2000
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "worst_case_answer_chars": worst_size["chars"],
        "worst_case_answer_tokens": worst_size["tokens"],
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
