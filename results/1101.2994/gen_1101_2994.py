"""Problem generator derived from Feng--Xiang, arXiv:1101.2994.

The generated task asks for the exact sign polynomial in the odd-character
root-of-unity sum used in the proof of Theorem 3.2.  Instances are planted by
choosing one lift of every residue modulo M; the answer follows by composition
of complete geometric-orbit identities, never by solving the generated task.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time


# harden.py is run from this directory, whereas gvlib lives at repository root.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family itself remains standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "For fixed a+i, the odd powers of a primitive 2M-th root form one complete "
    "M-term geometric orbit."
)
PLACEBO_HINT: str = (
    "For every index a, careful tracking of displayed terms prevents coefficient "
    "and ordering errors."
)


PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "cyclotomic class-index selector",
        "formal primitive-root sums in Q[x]/Phi_(2M)(x)",
        "dense sign polynomial",
    ],
    "verification_operations": [
        "exact integer modular reduction",
        "exact complete-geometric-orbit evaluation",
        "dense polynomial coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that the odd powers are a complete root-of-unity orbit, so all "
        "but the uniquely aligned selected class cancel; without that symmetry one "
        "expands the full cyclotomic sum."
    ),
    "hardness_basis": (
        "Track B: dense exact accumulation of the root-of-unity sum from the proof "
        "of Theorem 3.2 costs O(N*M^2); at the shipping regime M=127, N=254 it "
        "performs 4,096,766 exact term accumulations in a measured mean 0.497 "
        "seconds per instance (3.978104 seconds for eight), while the complete-"
        "orbit shortcut uses 254 exact arithmetic operations but has to be found "
        "and executed without tools."
    ),
    "max_answer_tokens": 223,
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
    "demo": {"n": 7},
    "easy": {"n": 23},
    "medium": {"n": 71},
    "hard": {"n": 127},
}
SHIPPING_DIFFICULTY: str = "hard"


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A dense polynomial E(x)=sum(e_a*x^a, 0<=a<2M), serialized as its "
        "ascending coefficient list.  Every coefficient is +1 or -1 and the "
        "freely visible antipodal rule e_(a+M)=-e_a is enforced, leaving exactly "
        "2^M candidates."
    ),
    "bounds": {
        "coefficient_choices": 2,
        "coefficient_abs_bound": 1,
        "max_coefficients": 256,
        "independent_coefficients_at_shipping": 127,
        "shipping_M": 127,
        "shipping_coefficients": 254,
    },
}


NOTES: str = (
    "Section 1 fixes cyclotomic classes C_i=gamma^i<gamma^N>.  Section 3.1 and "
    "Theorem 3.2 fix the usable regime N=2*p_1^m, p_1=7 mod 8, index two, and "
    "a selector I containing one lift of every residue modulo p_1^m.  The proof's "
    "display immediately before its final character-value formula is the exact "
    "identity generated here: summing all odd powers leaves one M-term orbit.  "
    "That displayed calculation is also what makes Track A false: a direct finite-"
    "field character sum is algorithmic, and even its formal root-of-unity version "
    "has a dense O(N*M^2) evaluation.  The compact route instead reflects each "
    "residue once and assigns an antipodal sign pair.  Plants and decoys are the "
    "same independent lower/upper lifts.  The measured attacks try lift-majority, "
    "sorted greedy alignment, random antipodal restarts, and the tempting same-"
    "residue ansatz; the exact dense evaluation is disclosed separately as the "
    "Track B reference algorithm.  The mandatory bare hardening run solved easy "
    "and medium and solved one of three hard instances; increasing M further "
    "would exceed the 256-coefficient cap, so harden.py returned cap_bound."
)


# Filled from the three independent harden.py runs at the configured hard preset.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 1, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value: int) -> bool:
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _multiplicative_order(a: int, modulus: int) -> int | None:
    if math.gcd(a, modulus) != 1:
        return None
    value = 1
    for order in range(1, modulus + 1):
        value = (value * a) % modulus
        if value == 1:
            return order
    return None


def _next_index_two_prime(minimum: int) -> int:
    """Least prime M>=minimum with M=7 (mod 8)."""
    candidate = max(7, int(minimum))
    candidate += (7 - candidate) % 8
    while not _is_prime(candidate):
        candidate += 8
    return candidate


def _find_characteristic(M: int) -> int:
    """Least p=3 (mod 4) satisfying the paper's index-two hypothesis."""
    target = (M - 1) // 2
    p = 3
    while True:
        if _is_prime(p) and p != M and _multiplicative_order(p, 2 * M) == target:
            return p
        p += 4


def _validate_selector(M: int, selector) -> tuple[bool, str]:
    N = 2 * M
    if not isinstance(selector, list) or len(selector) != M:
        return False, "instance_selector_count"
    if any(not _is_int(i) or not (0 <= i < N) for i in selector):
        return False, "instance_selector_range"
    if len(set(selector)) != M:
        return False, "instance_selector_duplicate"
    if {i % M for i in selector} != set(range(M)):
        return False, "instance_selector_residues"
    return True, "ok"


def _coefficient_vector(M: int, selector: list[int]) -> list[int]:
    """Proof-produced certificate, using the unique aligned selected lift."""
    selected = [0] * M
    for i in selector:
        selected[i % M] = i
    answer = []
    for a in range(2 * M):
        i = selected[(-a) % M]
        quotient = (a + i) // M
        answer.append(-1 if quotient % 2 else 1)
    return answer


def make_instance(n, seed=0, **params) -> dict:
    """Construct a selector and its sign polynomial without solving an instance.

    ``n`` is a lower bound for M=p_1; it is rounded up to the next prime congruent
    to 7 modulo 8.  One of r and r+M is sampled independently for every residue r.
    Theorem 3.2 applies with m=s=1, and the proof's geometric-orbit identity
    composes to give the certificate.
    """
    if not _is_int(n) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    M = _next_index_two_prime(n)
    N = 2 * M
    p = _find_characteristic(M)
    f = (M - 1) // 2
    rng = random.Random(seed)
    selector = [r + M * rng.getrandbits(1) for r in range(M)]
    rng.shuffle(selector)
    answer = _coefficient_vector(M, selector)
    return {
        "paper": "1101.2994",
        "requested_n": n,
        "M": M,
        "N": N,
        "p": p,
        "f": f,
        "extension_degree": 1,
        "field_order": p**f,
        "selector": selector,
        "answer": answer,
    }


def render(inst) -> str:
    """Render the full exact cyclotomic sign-polynomial problem."""
    M = inst["M"]
    N = inst["N"]
    selector = ", ".join(str(i) for i in inst["selector"])
    statement = f"""Cyclotomic odd-character sign polynomial

All arithmetic in exponents below is modulo N={N}.  Let zeta be a formal
primitive {N}-th root of unity: zeta^{N}=1, and no smaller positive power is 1.
Equalities involving zeta are exact equalities in the cyclotomic number field;
do not use floating-point approximations.

Context from the construction: p={inst['p']}, f={inst['f']}, and q=p^f={inst['field_order']}.
If gamma is a primitive element of the finite field F_q, the order-{N}
cyclotomic classes are C_i = gamma^i <gamma^{N}>.  The selected index set below
contains exactly one of r and r+M for every residue 0 <= r < M={M}; consequently
D = union(C_i : i in I) is the cyclotomic union used in the p_1 == 7 (mod 8)
construction.

Selected class indices I (order is irrelevant):
[{selector}]

For every integer a with 0 <= a < {N}, define the exact root-of-unity sum

  S_a = sum over i in I, then over u=0,...,{M - 1},
        of zeta^((2u+1)(a+i)).

For this input, S_a/{M} is guaranteed to be either +1 or -1.  Determine the
dense polynomial

  E(x) = e_0 + e_1*x + ... + e_{N - 1}*x^{N - 1},

where e_a = S_a/{M}.  Your answer must contain exactly {N} coefficients, in
ascending exponent order e_0,e_1,...,e_{N - 1}.  Each coefficient must be the
JSON integer 1 or -1.  The order of I does not affect the answer; coefficient
order does matter, and indices are 0-based.

Give your final answer inside <answer></answer> tags, as one JSON array.
Example syntax: <answer>[1, -1, 1, -1]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _decode_json_list(text: str):
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json|python)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
        return value if isinstance(value, list) else None
    except (TypeError, ValueError):
        return None


def parse_answer(text) -> object | None:
    """Parse a JSON coefficient list from tags, fences, or surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    for body in reversed(tagged):
        value = _decode_json_list(body)
        if value is not None:
            return value
    fenced = re.findall(r"```(?:json|python)?\s*(.*?)```", text, flags=re.I | re.S)
    for body in reversed(fenced):
        value = _decode_json_list(body)
        if value is not None:
            return value
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except ValueError:
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check the dense polynomial via exact complete-orbit evaluation.

    The checker never reads ``inst['answer']``.  For k=a+i, the inner sum is a
    complete M-term geometric orbit: it is zero unless M divides k, and otherwise
    equals M*(-1)^(k/M).  These are integer divisibility and parity checks only.
    """
    try:
        M = inst["M"]
        N = inst["N"]
        selector = inst["selector"]
    except (KeyError, TypeError):
        return False, "malformed_instance"
    if not _is_int(M) or N != 2 * M or M < 2:
        return False, "instance_parameters"
    selector_ok, selector_reason = _validate_selector(M, selector)
    if not selector_ok:
        return False, selector_reason
    if not isinstance(answer, list):
        return False, "answer_not_coefficient_list"
    if not answer:
        return False, "empty_answer"
    if len(answer) != N:
        return False, f"coefficient_count:{len(answer)}_expected_{N}"
    for a, coefficient in enumerate(answer):
        if not _is_int(coefficient) or coefficient not in (-1, 1):
            return False, f"coefficient_not_sign_at_{a}"
    for a in range(M):
        if answer[a + M] != -answer[a]:
            return False, f"antipodal_rule_failed_at_{a}"

    selected = [0] * M
    for i in selector:
        selected[i % M] = i
    for a, claimed in enumerate(answer):
        i = selected[(-a) % M]
        # Exactly one selected i makes M divide a+i.  Its geometric orbit is
        # M*(-1)^((a+i)/M); every other orbit is zero.
        exact = -1 if ((a + i) // M) % 2 else 1
        if claimed != exact:
            return False, f"identity_mismatch_at_{a}:claimed_{claimed}_exact_{exact}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the structure-aware antipodal sign-polynomial language."""
    M = inst["M"]
    word = rng.getrandbits(M)
    first = [1 if (word >> a) & 1 else -1 for a in range(M)]
    return first + [-value for value in first]


def search_space(inst) -> int | None:
    """There are two independent choices for each of the M antipodal pairs."""
    return 1 << inst["M"]


def enumerate_all(inst) -> int | None:
    """Brute-force the exact answer count at hand-scale M, with a strict cap."""
    M = inst["M"]
    if M > 18:
        return None
    valid = 0
    for word in range(1 << M):
        first = [1 if (word >> a) & 1 else -1 for a in range(M)]
        if verify(inst, first + [-value for value in first])[0]:
            valid += 1
    return valid


def _least_rotation(data: bytes) -> bytes:
    """Booth's O(n) lexicographically least cyclic rotation."""
    if not data:
        return data
    doubled = data + data
    n = len(data)
    i, j, k = 0, 1, 0
    while i < n and j < n and k < n:
        left = doubled[i + k]
        right = doubled[j + k]
        if left == right:
            k += 1
            continue
        if left > right:
            i = i + k + 1
            if i <= j:
                i = j + 1
        else:
            j = j + k + 1
            if j <= i:
                j = i + 1
        k = 0
    start = min(i, j)
    return doubled[start : start + n]


def canonical_key(inst) -> str:
    """Canonicalize class labels under i -> u*i+t, u a unit modulo N."""
    M = inst["M"]
    N = 2 * M
    ok, reason = _validate_selector(M, inst["selector"])
    if not ok:
        return "invalid:" + reason
    best = None
    for unit in range(1, N):
        if math.gcd(unit, N) != 1:
            continue
        bits = bytearray(N)
        for i in inst["selector"]:
            bits[(unit * i) % N] = 1
        rotated = _least_rotation(bytes(bits))
        if best is None or rotated < best:
            best = rotated
    payload = str(N).encode("ascii") + b":" + (best or b"")
    return hashlib.sha256(payload).hexdigest()


def escalate(params) -> dict | str | None:
    """The 254-coefficient hard rung exhausts the only honest hardness axis."""
    current = _next_index_two_prime(int(params.get("n", 7)))
    if current >= 127:
        return "cap_bound"
    # This branch supports callers that start outside the declared four-rung ladder.
    params = dict(params)
    params["n"] = max(current + 1, 2 * current)
    return params


def _reference_dense(inst) -> tuple[list[int], int]:
    """Expand every term, then reduce exactly modulo Phi_(2M).

    For odd prime M, Phi_(2M)(x)=1-x+x^2-...+x^(M-1).  Folding x^(r+M)=-x^r
    leaves a length-M coefficient vector.  If it is rational, its nonconstant
    part is an integer multiple of the alternating cyclotomic relation.
    """
    M = inst["M"]
    N = 2 * M
    selector = inst["selector"]
    result = []
    operations = 0
    for a in range(N):
        counts = [0] * N
        for i in selector:
            k = (a + i) % N
            for u in range(M):
                counts[((2 * u + 1) * k) % N] += 1
                operations += 1
        folded = [counts[r] - counts[r + M] for r in range(M)]
        relation_scale = -folded[1]
        value = folded[0] - relation_scale
        if any(
            folded[r]
            != (value if r == 0 else 0) + relation_scale * (1 if r % 2 == 0 else -1)
            for r in range(M)
        ):
            raise AssertionError("dense cyclotomic reduction did not become rational")
        if value % M:
            raise AssertionError("root sum was not divisible by M")
        result.append(value // M)
    return result, operations


def _candidate_ok(inst, candidate) -> bool:
    return candidate is not None and verify(inst, candidate)[0]


def _attack_lift_majority(inst):
    M = inst["M"]
    upper = sum(i >= M for i in inst["selector"])
    sign = -1 if upper > M // 2 else 1
    first = [sign] * M
    return first + [-value for value in first]


def _attack_sorted_greedy(inst):
    M = inst["M"]
    ordered = sorted(inst["selector"])
    first = [1 if ordered[a] < M else -1 for a in range(M)]
    return first + [-value for value in first]


def _attack_same_residue(inst):
    M = inst["M"]
    selected = [0] * M
    for i in inst["selector"]:
        selected[i % M] = i
    first = [1 if selected[a] < M else -1 for a in range(M)]
    return first + [-value for value in first]


def _attack_alternating(inst):
    M = inst["M"]
    first = [1 if a % 2 == 0 else -1 for a in range(M)]
    return first + [-value for value in first]


def _attack_random_restart(inst, rng, restarts=256):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if _candidate_ok(inst, candidate):
            return candidate, restarts
    return None, restarts


def _affine_transform_instance(inst, unit: int, shift: int, shuffle_seed: int):
    """Relabel i -> unit*i+shift and transport the Fourier coefficients."""
    transformed = copy.deepcopy(inst)
    N = inst["N"]
    unit %= N
    shift %= N
    if math.gcd(unit, N) != 1:
        raise ValueError("unit must be invertible modulo N")
    transformed["selector"] = [
        (unit * i + shift) % N for i in inst["selector"]
    ]
    random.Random(shuffle_seed).shuffle(transformed["selector"])
    inverse = pow(unit, -1, N)
    transformed["answer"] = [
        inst["answer"][(inverse * (a + shift)) % N] for a in range(N)
    ]
    return transformed


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "1101.2994",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: all presets, independent selectors, and JSON-native answers.
    g1_failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 19):
            candidate_inst = make_instance(seed=seed, **params)
            ok, reason = verify(candidate_inst, candidate_inst["answer"])
            attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(candidate_inst["answer"])) != candidate_inst["answer"]:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "not_json_native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=731, **ship_params)
    planted = inst["answer"]
    M = inst["M"]

    # G2: five natural corruptions, deliberately routed to five distinct reasons.
    opposite = next(
        (j for j in range(1, M) if planted[j] != planted[0]),
        1,
    )
    swapped = planted[:]
    swapped[0], swapped[opposite] = swapped[opposite], swapped[0]
    swapped[M], swapped[M + opposite] = swapped[M + opposite], swapped[M]
    duplicate = planted[:]
    duplicate[opposite] = duplicate[0]
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": [3] + planted[1:],
    }
    corruption_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The odd character orbit cancels except at one aligned lift.\n\n"
        "<answer>\n```json\n"
        + json.dumps(planted)
        + "\n```\n</answer>\nI kept coefficients in ascending degree order."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_reason = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_reason,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4 and shipping-density portion of G5: candidates already obey antipodality.
    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    expected = _coefficient_vector(M, inst["selector"])
    for _ in range(guess_total):
        if random_candidate(inst, guess_rng) == expected:
            guess_hits += 1
    density_wall = time.perf_counter() - density_start
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": search_space(inst) > 1_000_000 and observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "exact_probability": f"1/{search_space(inst)}",
        "candidate_prior": "uniform over antipodal sign polynomials",
        "search_space": str(search_space(inst)),
    }

    # G6 attacks, plus the successful Track B reference algorithm separately.
    attack_seeds = list(range(9100, 9108))
    successes = {
        "outlier_lift_majority": 0,
        "greedy_sorted_alignment": 0,
        "random_restart_256": 0,
        "same_residue_ansatz": 0,
        "alternating_by_hand": 0,
    }
    restart_operations = 0
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    reference_per_seed_wall = []
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **ship_params)
        if _candidate_ok(attack_inst, _attack_lift_majority(attack_inst)):
            successes["outlier_lift_majority"] += 1
        if _candidate_ok(attack_inst, _attack_sorted_greedy(attack_inst)):
            successes["greedy_sorted_alignment"] += 1
        candidate, operations = _attack_random_restart(
            attack_inst, random.Random(seed ^ 0x5A17), 256
        )
        restart_operations += operations
        if _candidate_ok(attack_inst, candidate):
            successes["random_restart_256"] += 1
        if _candidate_ok(attack_inst, _attack_same_residue(attack_inst)):
            successes["same_residue_ansatz"] += 1
        if _candidate_ok(attack_inst, _attack_alternating(attack_inst)):
            successes["alternating_by_hand"] += 1

        start = time.perf_counter()
        reference_answer, operations = _reference_dense(attack_inst)
        elapsed = time.perf_counter() - start
        reference_wall += elapsed
        reference_per_seed_wall.append(round(elapsed, 6))
        reference_operations += operations
        reference_successes += int(_candidate_ok(attack_inst, reference_answer))

    attacks = {
        name: {"successes": count, "attempts": len(attack_seeds)}
        for name, count in successes.items()
    }
    attacks["random_restart_256"]["candidates"] = restart_operations
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    per_instance_ops = inst["N"] * inst["M"] * inst["M"]
    reference = {
        "name": "dense exact root-of-unity coefficient accumulation",
        "complexity": "O(N*M^2) exact integer term accumulations",
        "wall_clock_sec": round(reference_wall, 6),
        "wall_clock_sec_per_seed": reference_per_seed_wall,
        "operations": reference_operations,
        "operations_per_instance": per_instance_ops,
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4 and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    demo = make_instance(seed=731, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6
        and all_failed
        and reference_successes == len(attack_seeds),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_baseline_wall_clock_sec": round(reference_wall, 6),
        "shipping_density": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": observed,
            "wall_clock_sec": round(density_wall, 6),
            "exact_fraction_from_uniqueness": f"1/{search_space(inst)}",
        },
        "demo_exact_valid_answers": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_baseline": reference,
    }

    doubled_start = time.perf_counter()
    doubled = make_instance(n=2 * inst["M"], seed=4471)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["M"] >= 2 * inst["M"],
        "base_requested_n": inst["requested_n"],
        "base_M": inst["M"],
        "doubled_requested_n": 2 * inst["M"],
        "doubled_M": doubled["M"],
        "build_and_verify_sec": round(time.perf_counter() - doubled_start, 6),
        "verify_reason": doubled_reason,
    }

    # G8: reorderings, translations, and unit-times-translation compositions.
    invariance_checks = 0
    transport_checks = 0
    nontrivial = 0
    keys = []
    for seed in range(20):
        original = make_instance(seed=12000 + seed, **ship_params)
        key = canonical_key(original)
        keys.append(key)
        N = original["N"]
        rng = random.Random(33000 + seed)
        units = [u for u in range(1, N) if math.gcd(u, N) == 1]
        unit = units[rng.randrange(len(units))]
        shift = rng.randrange(N)

        reordered = copy.deepcopy(original)
        rng.shuffle(reordered["selector"])
        translated = _affine_transform_instance(original, 1, shift, 44000 + seed)
        composed = _affine_transform_instance(original, unit, shift, 55000 + seed)
        for variant in (reordered, translated, composed):
            invariance_checks += 1
            if canonical_key(variant) != key:
                continue
            ok, _ = verify(variant, variant["answer"])
            transport_checks += int(ok)
            nontrivial += int(variant["selector"] != original["selector"])
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and transport_checks == 60
        and nontrivial >= 40
        and len(set(keys)) == 20,
        "invariance_checks": invariance_checks,
        "witness_transport_checks": transport_checks,
        "nontrivial_transformations": nontrivial,
        "unrelated_distinct": len(set(keys)),
        "unrelated_attempts": len(keys),
        "invariant": "least affine-unit rotation of the cyclotomic selector bitset",
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(inst["answer"])
    intended_operations = 2 * inst["M"]
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    diagnostic_difference = (
        hinted_rate - placebo_rate
        if hinted["attempts"] and placebo["attempts"]
        else None
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 all three oracle arms are diagnostic.  Only the
        # answer-size and compact-route caps are gated.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": diagnostic_difference,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps_pass": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
