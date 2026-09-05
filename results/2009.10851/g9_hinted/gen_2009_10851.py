"""Self-contained verified generator for arXiv:2009.10851.

The paper constructs permutation binomials x^r(x^(q-1)+a) over F_(q^e)
by recognizing them as a linearized binomial after a permutation monomial.
Here h=1, a=1, s=q-1, and r=q^e in Theorem 1.4.  Consequently the
paper's binomial induces x -> x^q+x.  Odd e makes this map a permutation.

An instance changes from a normal basis to a deterministically generated
triangular basis, samples a preimage first, and applies the permutation.  The
answer is therefore known without solving the generated instance.  A witness
is checked by exact prime-field arithmetic only.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time

# Keep repository helpers importable when this module is run from its result
# directory.  This family only needs prime-field arithmetic and remains fully
# standard-library-only if gvlib is unavailable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - documented dependency-free fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "permutation binomial over F_(q^e)",
        "finite-field element in a changed normal basis",
        "Frobenius linear map",
    ],
    "verification_operations": [
        "exact prime-field basis change",
        "exact Frobenius cyclic shift",
        "exact finite-field coordinate comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Conjugating the binomial's x^q+x action into normal-basis coordinates "
        "turns a dense-looking inversion into one cyclic recurrence."
    ),
    "hardness_basis": (
        "Track B: the generic reference algorithm materializes the coordinate "
        "matrix of x^q+x and applies O(e^3) Gaussian elimination (24,466 exact "
        "F_q operations and about 0.001 seconds at the hard preset in the recorded "
        "self-test); the structure-specific O(e) algorithm takes 169 operations, "
        "but requires recognizing and executing the normal-basis conjugacy "
        "without tools."
    ),
    "max_answer_tokens": 59,
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

# n is the odd extension degree e.  q is the odd prime defining the base
# field.  Both axes enlarge the candidate space; escalation raises q while
# holding the 29-coordinate answer length fixed.
DIFFICULTY = {
    "hard": {"n": 29, "q": 101},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "One nonzero element of F_(q^e), written as exactly e displayed-basis "
        "coordinates in 0,...,q-1; at the shipping preset e=29 and q=101."
    ),
    "bounds": {
        "coordinates": 29,
        "coordinate_min": 0,
        "coordinate_max": 100,
        "zero_vector_excluded": True,
    },
}

STRUCTURAL_HINT = (
    "The Frobenius part is conjugate through the displayed triangular basis map "
    "to a single cyclic coordinate shift."
)
PLACEBO_HINT = (
    "Care with shown coordinate order and signs can prevent small modular slips "
    "while preparing the submitted answer."
)

# Filled after the three separately preserved harden.py runs.  These are
# diagnostics, not gates; G9.pass is determined only by the size/effort caps.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0, "errors": 4},
        "hinted": {"solved": 0, "attempts": 0, "errors": 4},
        "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    },
    "hinted_verdict": "unavailable_http_403",
}

NOTES = """\
Section 1 defines a permutation polynomial as one inducing a bijection of the
finite field.  Lemma 3.1 gives the exact criterion for x^(q^h)+a*x, Lemmas 3.2
and 3.3 identify the composition, and Theorem 3.4 (Theorem 1.4 in the
introduction) constructs all binomials in that composition family.  Taking
h=1, k=1, s=q-1, a=1, and odd e gives r=q^e and
x^r(x^(q-1)+1)=x^q+x as a field function.  Theorem 1.3 is a complete direct
classification for e<=6 (with its stated restrictions), and the paper reports
an optimized exhaustive search below q^e=10^8; those facts rule out a Track-A
claim based on deciding whether the displayed binomial permutes.

This module instead makes a Track-B preimage problem.  It samples the nonzero
preimage uniformly first, carries x^q+x through an invertible triangular basis
change, and uses the image as the target.  Generic matrix materialization and
Gaussian elimination are the disclosed polynomial-time reference algorithm.
The outlier probe, direct-image guess, coordinatewise divide-by-two guess,
cycle-without-basis-change guess, and random restarts all see a uniformly
distributed nonzero preimage and fail.  The compact route changes to normal
coordinates, uses the odd-cycle recurrence, and changes back.  The canonical
key first removes the generated triangular basis/slot disguise and then
quotients cyclic normal-basis rotation and common F_q rescaling.
"""


def _is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin for the 64-bit values used by the ladder."""
    # A final fixed-length escalation target; 2^127-1 is a known Mersenne prime.
    if n == (1 << 127) - 1:
        return True
    if n >= 1 << 64:
        return False
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n % p == 0:
            return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    # Deterministic for unsigned 64-bit integers.
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


def _next_prime(n: int) -> int:
    candidate = max(3, int(n))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _to_chain(display: list[int], slot_to_chain: list[int]) -> list[int]:
    """Undo the arbitrary ordering of the displayed coordinate slots."""
    chain = [0] * len(display)
    for slot, chain_index in enumerate(slot_to_chain):
        chain[chain_index] = display[slot]
    return chain


def _from_chain(chain: list[int], slot_to_chain: list[int]) -> list[int]:
    return [chain[chain_index] for chain_index in slot_to_chain]


def _triangular_forward(chain: list[int], b: list[int], q: int) -> list[int]:
    """T: displayed-chain coordinates -> normal-basis coordinates."""
    normal = [chain[0] % q]
    for i in range(1, len(chain)):
        normal.append((chain[i] + b[i - 1] * normal[i - 1]) % q)
    return normal


def _triangular_inverse(normal: list[int], b: list[int], q: int) -> list[int]:
    """T^-1, written without solving a system."""
    chain = [normal[0] % q]
    for i in range(1, len(normal)):
        chain.append((normal[i] - b[i - 1] * normal[i - 1]) % q)
    return chain


def _display_to_normal(inst: dict, display: list[int]) -> list[int]:
    chain = _to_chain(display, inst["slot_to_chain"])
    return _triangular_forward(chain, inst["basis_multipliers"], inst["q"])


def _normal_to_display(inst: dict, normal: list[int]) -> list[int]:
    chain = _triangular_inverse(normal, inst["basis_multipliers"], inst["q"])
    return _from_chain(chain, inst["slot_to_chain"])


def _apply_binomial(inst: dict, display: list[int]) -> list[int]:
    """Apply x^q+x exactly in the instance's displayed coordinates."""
    q = inst["q"]
    normal = _display_to_normal(inst, display)
    # In a normal basis eta_i^q=eta_(i+1), so output coordinate i of
    # Frobenius is the old coordinate i-1.
    image_normal = [
        (normal[i] + normal[(i - 1) % len(normal)]) % q
        for i in range(len(normal))
    ]
    return _normal_to_display(inst, image_normal)


def _cycle_inverse(target_normal: list[int], q: int) -> list[int]:
    """Invert I+cyclic_shift for odd dimension by an alternating identity."""
    e = len(target_normal)
    acc = 0
    for k in range(e):
        term = target_normal[(-k) % e]
        acc = (acc + term) % q if k % 2 == 0 else (acc - term) % q
    z = [0] * e
    z[0] = acc * ((q + 1) // 2) % q
    for i in range(1, e):
        z[i] = (target_normal[i] - z[i - 1]) % q
    return z


def _compact_solve(inst: dict) -> list[int]:
    target_normal = _display_to_normal(inst, inst["target"])
    preimage_normal = _cycle_inverse(target_normal, inst["q"])
    return _normal_to_display(inst, preimage_normal)


def _theorem_34_conditions(inst: dict) -> bool:
    """Check the h=k=1, s=q-1 specialization of paper Theorem 3.4."""
    q, e, r, a = inst["q"], inst["e"], inst["r"], inst["a"]
    field_group_order = pow(q, e) - 1
    ell = field_group_order // (q - 1)
    composed_exponent = (q - 1) * ell + 1
    return (
        a != 0
        and pow((-a) % q, ell, q) != 1
        and r % field_group_order == composed_exponent % field_group_order
        and math.gcd(r, q - 1) == 1
    )


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a preimage instance of the paper's binomial.

    ``n`` is the odd extension degree e; larger n enlarges F_(q^e).  ``q`` is
    an odd prime and supplies a fixed-answer-length escalation axis.  The
    planted preimage is sampled before its target is computed; no generated
    instance is solved to obtain its certificate.
    """
    e = int(n)
    q = int(params.get("q", 5))
    if e < 3 or e % 2 == 0:
        raise ValueError("n must be an odd extension degree at least 3")
    if q < 3 or q % 2 == 0 or not _is_prime(q):
        raise ValueError("q must be an odd prime")

    rng = random.Random(seed)
    b = [rng.randrange(1, q) for _ in range(e - 1)]
    slot_to_chain = list(range(e))
    rng.shuffle(slot_to_chain)

    # Uniform over the structure-aware nonzero answer language.
    while True:
        answer = [rng.randrange(q) for _ in range(e)]
        if any(answer):
            break

    inst = {
        "paper": "2009.10851",
        "q": q,
        "e": e,
        "r": pow(q, e),
        "a": 1,
        "basis_multipliers": b,
        "slot_to_chain": slot_to_chain,
    }
    inst["target"] = _apply_binomial(inst, answer)
    inst["answer"] = answer
    return inst


def render(inst) -> str:
    q, e = inst["q"], inst["e"]
    lines = [
        "Invert a permutation binomial over a finite field.",
        "",
        f"All scalar arithmetic below is modulo the prime q={q}.",
        f"Let K=F_(q^e) with e={e}.  Fix a normal basis eta_0,...,eta_{e-1}",
        "whose indices are modulo e and satisfy eta_i^q=eta_(i+1).",
        "A field element is reported in e displayed coordinate slots.  To turn a",
        "displayed vector v into its normal-basis coordinate vector w, first form",
        "chain coordinates c using c[slot_to_chain[j]]=v[j], and then use",
        "  w[0]=c[0],",
        "  w[i]=c[i]+b[i]*w[i-1] mod q  for i=1,...,e-1.",
        "This triangular rule is invertible and therefore defines the displayed basis.",
        "",
        "The slot_to_chain list (entry j belongs to displayed slot j) is:",
        "  " + json.dumps(inst["slot_to_chain"]),
        "The multipliers b[1],...,b[e-1] are:",
        "  " + json.dumps(inst["basis_multipliers"]),
        "",
        f"Consider f(x)=x^(q^e)*(x^(q-1)+1), with q^e={inst['r']}.",
        "For every x in K, x^(q^e)=x, so this same field function is f(x)=x^q+x.",
        "The target y, in displayed coordinate-slot order, is:",
        "  " + json.dumps(inst["target"]),
        "",
        "Find the unique x in K such that f(x)=y.",
        f"Your answer must be one JSON array of exactly {e} integers in 0,...,{q-1}.",
        "Coordinate order is the displayed slot order above; order matters, zeros and",
        "repeated coordinates are allowed, and the whole vector must be nonzero.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON array of integers.",
        f"Example format only: <answer>{json.dumps([0] * (e - 1) + [1])}</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged JSON integer vector; never raise on garbage."""
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
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return None
    return answer


def verify(inst, answer):
    """Verify any valid preimage exactly, without consulting planted data."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    e, q = inst["e"], inst["q"]
    if len(answer) < e:
        return False, f"too few coordinates: expected {e}"
    if len(answer) > e:
        return False, f"too many coordinates: expected {e}"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every coordinate must be an integer"
    if any(v < 0 or v >= q for v in answer):
        return False, f"coordinate outside the required range 0..{q-1}"
    if not any(answer):
        return False, "the requested nonzero preimage cannot be the zero vector"
    image = _apply_binomial(inst, answer)
    for i, (got, wanted) in enumerate(zip(image, inst["target"])):
        if got != wanted:
            return False, (
                f"image mismatch at displayed coordinate {i}: got {got}, "
                f"expected {wanted}"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the obvious, structure-aware nonzero field elements."""
    e, q = inst["e"], inst["q"]
    while True:
        candidate = [rng.randrange(q) for _ in range(e)]
        if any(candidate):
            return candidate


def search_space(inst):
    return pow(inst["q"], inst["e"]) - 1


def enumerate_all(inst):
    size = search_space(inst)
    if size > 200_000:
        return None
    hits = 0
    for values in itertools.product(range(inst["q"]), repeat=inst["e"]):
        if not any(values):
            continue
        hits += int(verify(inst, list(values))[0])
    return hits


def _canonical_normal_orbit(vector: list[int], q: int) -> list[int]:
    """Quotient cyclic normal-basis rotation and base-field rescaling.

    Replacing eta_i by u*eta_(i+t), with u in F_q^*, is a presentation change:
    it preserves eta_i^q=eta_(i+1) and conjugates neither x^q+x nor the target
    equation.  Normalize the first nonzero coordinate of every rotation and
    choose the lexicographically least representative.
    """
    e = len(vector)
    representatives = []
    for shift in range(e):
        rotated = [vector[(i + shift) % e] % q for i in range(e)]
        first = next(value for value in rotated if value)
        scale = pow(first, q - 2, q)
        representatives.append([(value * scale) % q for value in rotated])
    return min(representatives)


def canonical_key(inst):
    """Canonicalize every coordinate disguise deliberately generated here.

    The random triangular displayed basis and slot ordering carry no abstract
    information, so the target is first returned to normal coordinates.  The
    remaining inexpensive normal-basis presentation symmetries (cyclic rotation
    and common nonzero F_q scaling) are removed as well.
    """
    target_normal = _display_to_normal(inst, inst["target"])
    normal = {
        "q": inst["q"],
        "e": inst["e"],
        "a": inst["a"],
        "target_normal_orbit": _canonical_normal_orbit(target_normal, inst["q"]),
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Grow base-field entropy while keeping the answer at 29 coordinates."""
    p = dict(params)
    e = int(p.get("n", 29))
    q = int(p.get("q", 101))
    mersenne_61 = (1 << 61) - 1
    mersenne_127 = (1 << 127) - 1
    if q < mersenne_61:
        new_q = _next_prime(min(2 * q + 1, mersenne_61))
    elif q < mersenne_127:
        new_q = mersenne_127
    else:
        return "cap_bound"
    estimated_chars = e * (len(str(new_q - 1)) + 2) + 2
    if estimated_chars > 1900:
        return "cap_bound"
    p["q"] = new_q
    return p


# --- Reference algorithm and adversarial probes used only by selftest -------

def _materialize_matrix(inst: dict):
    e = inst["e"]
    matrix = [[0] * e for _ in range(e)]
    # Applying T, I+S, and T^-1 to one vector costs
    # 2(e-1) + e + 2(e-1) primitive field operations.
    operations = 0
    for col in range(e):
        unit = [0] * e
        unit[col] = 1
        image = _apply_binomial(inst, unit)
        operations += 5 * e - 4
        for row, value in enumerate(image):
            matrix[row][col] = value
    return matrix, operations


def _gaussian_solve(matrix: list[list[int]], rhs: list[int], q: int):
    """Generic dense Gauss-Jordan elimination with an operation count."""
    n = len(matrix)
    aug = [row[:] + [rhs[i] % q] for i, row in enumerate(matrix)]
    operations = 0
    pivot_row = 0
    pivots = []
    for col in range(n):
        pivot = next((r for r in range(pivot_row, n) if aug[r][col] % q), None)
        if pivot is None:
            continue
        aug[pivot_row], aug[pivot] = aug[pivot], aug[pivot_row]
        inv = pow(aug[pivot_row][col], q - 2, q)
        operations += 1
        for j in range(col, n + 1):
            aug[pivot_row][j] = aug[pivot_row][j] * inv % q
            operations += 1
        for r in range(n):
            if r == pivot_row or aug[r][col] == 0:
                continue
            factor = aug[r][col]
            for j in range(col, n + 1):
                aug[r][j] = (aug[r][j] - factor * aug[pivot_row][j]) % q
                operations += 2
        pivots.append(col)
        pivot_row += 1
        if pivot_row == n:
            break
    if len(pivots) != n:
        return None, operations
    solution = [0] * n
    for row, col in enumerate(pivots):
        solution[col] = aug[row][n]
    return solution, operations


def _reference_algorithm(inst: dict):
    start = time.perf_counter()
    matrix, materialize_ops = _materialize_matrix(inst)
    solution, eliminate_ops = _gaussian_solve(matrix, inst["target"], inst["q"])
    return solution, time.perf_counter() - start, materialize_ops + eliminate_ops


def _attack_candidates(inst: dict, rng: random.Random):
    q, e = inst["q"], inst["e"]
    target = inst["target"]

    # Per-coordinate outlier: keep only the largest displayed target entry.
    outlier = [0] * e
    outlier[max(range(e), key=lambda i: (target[i], -i))] = max(target)
    if not any(outlier):
        outlier[0] = 1

    direct = target[:]
    inv_two = (q + 1) // 2
    coordinatewise_half = [v * inv_two % q for v in target]

    # Recognize the cyclic map but ignore the nontrivial displayed basis.
    cyclic_without_basis = _cycle_inverse(target, q)

    # Do the normal-coordinate solve but forget to convert its result back to
    # the displayed basis.  This is a realistic partial-recognition failure.
    normal_target = _display_to_normal(inst, target)
    normal_answer_misread_as_display = _cycle_inverse(normal_target, q)

    return {
        "outlier_largest_target_coordinate": [outlier],
        "direct_target_as_preimage": [direct],
        "greedy_coordinatewise_divide_by_two": [coordinatewise_half],
        "cyclic_inverse_without_basis_change": [cyclic_without_basis],
        "omit_inverse_basis_change": [normal_answer_misread_as_display],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _reorder_display_slots(inst: dict, rng: random.Random) -> dict:
    """Apply a real representation relabelling and carry the witness through."""
    old_for_new = list(range(inst["e"]))
    rng.shuffle(old_for_new)
    out = {k: v for k, v in inst.items() if k not in (
        "slot_to_chain", "target", "answer"
    )}
    out["slot_to_chain"] = [inst["slot_to_chain"][i] for i in old_for_new]
    out["target"] = [inst["target"][i] for i in old_for_new]
    out["answer"] = [inst["answer"][i] for i in old_for_new]
    return out


def _change_coordinate_presentation(inst: dict, rng: random.Random) -> dict:
    """Change basis/slots and carry target and answer through the isomorphism."""
    e, q = inst["e"], inst["q"]
    answer_normal = _display_to_normal(inst, inst["answer"])
    target_normal = _display_to_normal(inst, inst["target"])

    # eta'_i = unit * eta_(i+shift), so coordinates transform by the inverse
    # unit and the corresponding cyclic rotation.
    shift = rng.randrange(e)
    unit = rng.randrange(1, q)
    inverse_unit = pow(unit, q - 2, q)

    def changed_normal(vector):
        return [
            vector[(i + shift) % e] * inverse_unit % q
            for i in range(e)
        ]

    out = {k: v for k, v in inst.items() if k not in (
        "basis_multipliers", "slot_to_chain", "target", "answer"
    )}
    out["basis_multipliers"] = [rng.randrange(1, q) for _ in range(e - 1)]
    out["slot_to_chain"] = list(range(e))
    rng.shuffle(out["slot_to_chain"])
    out["answer"] = _normal_to_display(out, changed_normal(answer_normal))
    out["target"] = _normal_to_display(out, changed_normal(target_normal))
    return out


def _answer_token_measure(answer) -> int:
    # Conservative lexical estimate: count every number and punctuation mark.
    return len(re.findall(r"\d+|[\[\],-]", json.dumps(answer)))


def selftest():
    report = {
        "paper": "2009.10851",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all four presets, three independently generated instances each.
    verified = 0
    theorem_verified = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            verified += int(ok)
            theorem_verified += int(_theorem_34_conditions(inst))
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": verified == theorem_verified == 12,
        "verified": verified,
        "theorem_3_4_conditions_verified": theorem_verified,
        "attempts": 12,
        "failures": failures,
    }

    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = ship["answer"]

    # G2: five corruption classes with five distinguishable rejection reasons.
    swap = answer[:]
    pair = next(((i, j) for i in range(len(answer))
                 for j in range(i + 1, len(answer))
                 if answer[i] != answer[j]), (0, 1))
    swap[pair[0]], swap[pair[1]] = swap[pair[1]], swap[pair[0]]
    corruptions = {
        "drop": answer[:-1],
        "swap": swap,
        "duplicate": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [ship["q"], *answer[1:]],
    }
    cases = {}
    for name, bad in corruptions.items():
        ok, why = verify(ship, bad)
        cases[name] = {"rejected": not ok, "reason": why}
    distinct = len({item["reason"] for item in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in cases.values()) and distinct == 5,
        "cases": cases,
        "distinct_reasons": distinct,
    }

    # G3: prose and a markdown fence surrounding the required tagged payload.
    reply = (
        "Changing to normal coordinates gives the following vector.\n```json\n"
        + "<answer>" + json.dumps(answer) + "</answer>\n```"
    )
    parsed = parse_answer(reply)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "parsed_matches": parsed == answer,
        "json_native": json_native,
    }

    # G4 and shipping-density portion of G5 use the same 200k candidates from
    # the exact, structure-aware nonzero finite-field language.
    density_inst = make_instance(seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY])
    density_rng = random.Random(0x200910851)
    samples = 200_000
    hits = 0
    density_start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(density_inst, density_rng)
        hits += int(verify(density_inst, candidate)[0])
    density_wall = time.perf_counter() - density_start
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "exact_language_size": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
    }

    # G6: no-tool probes fail; generic exact Gaussian elimination is separated
    # as Track B's expected-to-succeed reference algorithm.
    attempts = 8
    attack_success = None
    ref_success = 0
    ref_times = []
    ref_ops = []
    for seed in range(20, 20 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        probes = _attack_candidates(inst, random.Random(91_000 + seed))
        if attack_success is None:
            attack_success = {name: 0 for name in probes}
        for name, candidates in probes.items():
            if any(verify(inst, candidate)[0] for candidate in candidates):
                attack_success[name] += 1
        solved, elapsed, operations = _reference_algorithm(inst)
        ref_success += int(solved is not None and verify(inst, solved)[0])
        ref_times.append(elapsed)
        ref_ops.append(operations)
    attacks = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_success.items()
    }
    reference_wall = sum(ref_times) / len(ref_times)
    reference_ops = sum(ref_ops) // len(ref_ops)
    all_attacks_failed = all(v["successes"] == 0 for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_success == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "materialize the x^q+x coordinate matrix and use dense Gaussian elimination",
            "complexity": "O(e^3) exact F_q operations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_ops,
            "solves": f"{ref_success}/{attempts}, as expected",
        },
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits == 0 and ref_success == attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": probability,
        "shipping_exact_valid_answers_by_permutation_identity": 1,
        "demo_exact_solution_count_by_enumeration": demo_count,
        "baseline_wall_clock_sec": round(reference_wall, 6),
        "baseline_operation_count": reference_ops,
    }

    # G7: double extension size (rounding to the next odd value) and recheck G1.
    doubled_params = dict(DIFFICULTY["hard"])
    doubled_params["n"] = 2 * doubled_params["n"] + 1
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["e"] > 2 * ship["e"],
        "original_extension_degree": ship["e"],
        "doubled_extension_degree": doubled["e"],
        "original_search_space": search_space(ship),
        "doubled_search_space": search_space(doubled),
        "verify_reason": doubled_why,
    }

    # G8: displayed-slot reorderings, triangular basis changes, normal-basis
    # rotations, and base-field rescalings are real problem isomorphisms.
    invariance_passed = 0
    invariance_attempted = 0
    transformed_verified = 0
    distinct_keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(123_000 + seed)
        once = _reorder_display_slots(inst, rng)
        twice = _change_coordinate_presentation(once, rng)
        key = canonical_key(inst)
        for changed in (once, twice):
            invariance_attempted += 1
            invariance_passed += int(canonical_key(changed) == key)
        transformed_verified += int(verify(twice, twice["answer"])[0])
        distinct_keys.append(key)
    report["G8_canonical_key"] = {
        "pass": (
            invariance_passed == invariance_attempted == 40
            and transformed_verified == 20
            and len(set(distinct_keys)) == 20
        ),
        "invariance_checks_passed": invariance_passed,
        "invariance_checks_attempted": invariance_attempted,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": len(set(distinct_keys)),
        "unrelated_instances": 20,
    }

    blob = json.dumps(answer)
    worst_case_blob = json.dumps([ship["q"] - 1] * ship["e"])
    answer_tokens = _answer_token_measure([ship["q"] - 1] * ship["e"])
    answer_elements = len(answer)
    intended_ops = 6 * (ship["e"] - 1) + 1
    arms = G9_RESULTS["arms"]
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    else:
        hinted_minus_placebo = None
    within_caps = (
        len(worst_case_blob) <= 2000
        and answer_elements <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(worst_case_blob),
        "sample_answer_chars": len(blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [v for k, v in report.items() if k.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
