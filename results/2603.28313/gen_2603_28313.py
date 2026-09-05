"""Verified Track-B generator for arXiv:2603.28313.

Section V-B of the paper gives four modular equations for the same long-term
secret S when a recovered 2x2 matrix A and its transpose A^T are observed in
different sessions.  The paper's stated attack tests candidate reduced moduli
and solves the small system for each candidate.  This module inverse-generates
exact instances of that recovery problem.

The planted answer is sampled before any transcript is made.  A public,
answer-independent determinantal condition makes the answer unique: the gcd of
the 3x3 minors of the augmented coefficient/ciphertext matrix is exactly the
hidden modulus.  The generator checks that condition, but never recovers the
answer from the generated instance.
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
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "two-by-two integer encryption matrix and its transpose",
        "modular RFID ciphertext vectors from reused long-term secret data",
        "unknown reduced session modulus",
    ],
    "verification_operations": [
        "exact integer range comparison",
        "exact two-by-two matrix-vector multiplication",
        "exact modular reduction and equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The hidden modulus is the common determinantal divisor of the four "
        "augmented A/A^T equations; without recognizing it, the paper's method "
        "tests candidate moduli one at a time."
    ),
    "hardness_basis": (
        "Track B: Section V-B tests candidate reduced moduli by repeatedly "
        "solving a two-variable modular system, O(n log q) arithmetic for an "
        "n-value interval; at the hard shipping preset the measured eight-seed "
        "benchmark tested 4,268,172 candidate moduli in about 11.1 seconds "
        "(533,521.5 "
        "trials per instance), while the common-determinantal-divisor route used "
        "at most 161 counted exact operations."
    ),
    "max_answer_tokens": 10,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [q,s1,s2] of exactly three integers.  q ranges over the "
        "published half-open candidate interval [q_min,q_max), and each secret "
        "coordinate ranges independently over [0,secret_bound)."
    ),
    "bounds": {
        "length": 3,
        "modulus_min": "q_min",
        "modulus_max_exclusive": "q_max",
        "secret_coordinates": 2,
        "secret_min": 0,
        "secret_max_exclusive": "secret_bound",
        "candidate_count": "(q_max-q_min)*secret_bound^2",
    },
}

DIFFICULTY = {
    "demo": {"n": 7, "q_min": 9, "secret_bound": 5},
    "easy": {"n": 65_536, "q_min": 1_000_000, "secret_bound": 65_536},
    "medium": {
        "n": 262_144,
        "q_min": 2_147_483_648,
        "secret_bound": 1_048_576,
    },
    "hard": {
        "n": 1_048_576,
        "q_min": 140_737_488_355_328,
        "secret_bound": 2_147_483_648,
    },
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The augmented coefficient-and-ciphertext rows share a nontrivial common "
    "determinantal divisor."
)
PLACEBO_HINT = (
    "The bounds and least-nonnegative-residue convention should be checked "
    "carefully throughout the calculation."
)

# Filled after the three isolated oracle runs.  These values are diagnostic;
# verify() never reads them.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "error_draws": 4},
    "hinted": {"solved": 0, "attempts": 0, "error_draws": 4},
    "placebo": {"solved": 0, "attempts": 0, "error_draws": 4},
    "hinted_verdict": "unavailable: OpenRouter HTTP 403 key limit",
}

NOTES = (
    "Section II and Equation (1) fix the native encryption object E(t,A,p)=At "
    "mod p.  Section V-B, Equations (21)-(24), fixes this family's four "
    "A/A^T equations and the reuse of the same two-coordinate long-term secret. "
    "Section VI-C is the decisive easy-result audit: it explicitly gives a "
    "candidate reduced-modulus search, at most 2^32 candidates and about 2^39 "
    "small consistency checks, so this cannot be Track A.  The answer is sampled "
    "first and transcripts are encrypted from it.  Rejection sampling only "
    "ensures that the public augmented minors have gcd q, a uniqueness condition; "
    "it never solves for q or S.  The candidate interval hides q away from both "
    "edges; matrix entries and ciphertexts use the same ordinary residue range. "
    "The audit separately defeats max-value, lower-edge scan, random candidate-"
    "modulus restart, and no-wrap integer-solve attacks."
)


def _is_prime_64(value: int) -> bool:
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


def _choose_modulus(q_min: int, q_max: int, rng: random.Random) -> int:
    """Sample the answer modulus first, in the middle half of its interval."""
    width = q_max - q_min
    left = q_min + max(1, width // 4)
    right = q_min + max(2, (3 * width) // 4)
    if right <= left:
        right = q_max
    start = rng.randrange(left, right)
    candidate = start if start % 2 else start + 1
    while candidate < q_max:
        if _is_prime_64(candidate):
            return candidate
        candidate += 2
    candidate = start - 1 if start % 2 == 0 else start - 2
    while candidate >= q_min:
        if _is_prime_64(candidate):
            return candidate
        candidate -= 2
    raise ValueError("candidate interval contains no usable prime modulus")


def _mat_vec(matrix: list[list[int]], vector: list[int], modulus: int) -> list[int]:
    return [
        (matrix[0][0] * vector[0] + matrix[0][1] * vector[1]) % modulus,
        (matrix[1][0] * vector[0] + matrix[1][1] * vector[1]) % modulus,
    ]


def _transpose(matrix: list[list[int]]) -> list[list[int]]:
    return [[matrix[0][0], matrix[1][0]], [matrix[0][1], matrix[1][1]]]


def _det3(rows: list[list[int]]) -> int:
    a, b, c = rows[0]
    d, e, f = rows[1]
    g, h, i = rows[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _augmented_rows(inst: dict) -> list[list[int]]:
    rows: list[list[int]] = []
    for session in inst["sessions"]:
        matrix = session["matrix"]
        ciphertext = session["ciphertext"]
        rows.append([matrix[0][0], matrix[0][1], ciphertext[0]])
        rows.append([matrix[1][0], matrix[1][1], ciphertext[1]])
    return rows


def _minor_values(inst: dict) -> list[int]:
    rows = _augmented_rows(inst)
    return [
        abs(_det3([rows[i] for i in chosen]))
        for chosen in itertools.combinations(range(4), 3)
    ]


def _determinantal_divisor(inst: dict) -> int:
    return math.gcd(*_minor_values(inst))


def make_instance(
    n: int,
    seed: int = 0,
    q_min: int = 1_000_000,
    secret_bound: int = 65_536,
    **params: Any,
) -> dict:
    """Inverse-generate a Section V-B reduced-modulus recovery instance.

    ``n`` is the number of candidate modulus values in the public interval.
    Larger n therefore enlarges the paper's one-candidate-at-a-time search while
    the three-integer witness stays fixed in length.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("q_min", q_min), ("secret_bound", secret_bound)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 7:
        raise ValueError("n must be at least 7")
    if q_min < 3:
        raise ValueError("q_min must be at least 3")
    q_max = q_min + n
    if q_max >= 2**64:
        raise ValueError("the candidate interval must fit below 2^64")
    if secret_bound < 2 or secret_bound >= q_min:
        raise ValueError("secret_bound must satisfy 2 <= secret_bound < q_min")

    rng = random.Random(seed)
    modulus = _choose_modulus(q_min, q_max, rng)
    # Avoid degenerate coordinate symmetries in both the instance and G2.
    while True:
        secret = [rng.randrange(1, secret_bound), rng.randrange(1, secret_bound)]
        if secret[0] != secret[1]:
            break

    # The answer is already fixed.  We now draw public matrices until the
    # augmented minors certify uniqueness.  This is validation of a constructed
    # instance, not recovery of its answer.
    for _attempt in range(10_000):
        a, b, c, d = [rng.randrange(1, modulus) for _ in range(4)]
        if b == c:
            continue
        matrix = [[a, b], [c, d]]
        determinant = a * d - b * c
        if math.gcd(determinant, modulus) != 1:
            continue
        transpose = _transpose(matrix)
        sessions = [
            {"matrix": matrix, "ciphertext": _mat_vec(matrix, secret, modulus)},
            {
                "matrix": transpose,
                "ciphertext": _mat_vec(transpose, secret, modulus),
            },
        ]
        rng.shuffle(sessions)
        inst = {
            "family": "rfid_reduced_modulus_consistency",
            "n": n,
            "q_min": q_min,
            "q_max": q_max,
            "secret_bound": secret_bound,
            "sessions": sessions,
            "answer": [modulus, secret[0], secret[1]],
        }
        if _determinantal_divisor(inst) != modulus:
            continue
        public_max = max(
            value
            for session in sessions
            for value in (
                *session["matrix"][0],
                *session["matrix"][1],
                *session["ciphertext"],
            )
        )
        # Make the two simplest single-number guesses false by construction.
        if modulus in (q_min, q_min + n // 2, q_max - 1, public_max + 1):
            continue
        return inst
    raise RuntimeError("could not draw a nondegenerate certified transcript")


def render(inst: dict) -> str:
    lines = [
        "RECOVER A REDUCED RFID SESSION MODULUS",
        "",
        "All arithmetic below is over the ordinary integers followed by modular",
        "reduction.  For an integer q>1, x mod q means the unique remainder in",
        "{0,1,...,q-1}.",
        "",
        "There is an unknown modulus q and one reused secret column vector",
        "S=[s1,s2]^T.  They obey the half-open bounds",
        f"    {inst['q_min']} <= q < {inst['q_max']}",
        f"    0 <= s1,s2 < {inst['secret_bound']}.",
        "",
        "Each session below gives a 2 by 2 integer matrix M and a ciphertext",
        "column C.  It is promised that C = M*S mod q, coordinate by coordinate.",
        "The two displayed matrices are transposes of one another, as in the",
        "cross-session A/A^T equations of the protocol.  The same q and S are",
        "used in both sessions.  Exactly one triple [q,s1,s2] within the stated",
        "bounds satisfies every displayed equation.",
        "",
        "SESSIONS (entries are decimal integers; session order is irrelevant):",
    ]
    for index, session in enumerate(inst["sessions"]):
        matrix = session["matrix"]
        ciphertext = session["ciphertext"]
        lines.extend(
            [
                f"Session {index}:",
                f"  M = [[{matrix[0][0]}, {matrix[0][1]}],",
                f"       [{matrix[1][0]}, {matrix[1][1]}]]",
                f"  C = [{ciphertext[0]}, {ciphertext[1]}]",
            ]
        )
    lines.extend(
        [
            "",
            "Return the unique triple as a JSON list [q,s1,s2].  It must contain",
            "exactly three decimal integers in that order; intervals are half-open",
            "as stated above, and no alternative residue representatives are allowed.",
            "",
            "Give your final answer inside <answer></answer> tags in that exact JSON format.",
            "Example: <answer>[13,2,4]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(matches))
    if not candidates:
        candidates.extend(
            re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
        )
    for raw in candidates:
        body = raw.strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 3:
        return False, f"wrong length: expected 3 integers, got {len(answer)}"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "all three answer entries must be integers"
    modulus, s1, s2 = answer
    if modulus < inst["q_min"] or modulus >= inst["q_max"]:
        return False, "modulus is outside the stated half-open interval"
    bound = inst["secret_bound"]
    if s1 < 0 or s1 >= bound or s2 < 0 or s2 >= bound:
        return False, "a secret coordinate is outside the stated half-open interval"
    secret = [s1, s2]
    for session_index, session in enumerate(inst["sessions"]):
        observed = _mat_vec(session["matrix"], secret, modulus)
        expected = session["ciphertext"]
        for coordinate in range(2):
            if observed[coordinate] != expected[coordinate]:
                return (
                    False,
                    "ciphertext mismatch at session "
                    f"{session_index}, coordinate {coordinate}: got "
                    f"{observed[coordinate]}, expected {expected[coordinate]}",
                )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact bounded language stated to the solver."""
    return [
        rng.randrange(inst["q_min"], inst["q_max"]),
        rng.randrange(inst["secret_bound"]),
        rng.randrange(inst["secret_bound"]),
    ]


def search_space(inst: dict) -> int | None:
    return (inst["q_max"] - inst["q_min"]) * inst["secret_bound"] ** 2


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 200_000:
        return None
    valid = 0
    for modulus in range(inst["q_min"], inst["q_max"]):
        for s1 in range(inst["secret_bound"]):
            for s2 in range(inst["secret_bound"]):
                valid += int(verify(inst, [modulus, s1, s2])[0])
    return valid


def _canonical_public(inst: dict, swap_coordinates: bool) -> str:
    canonical_sessions = []
    for session in inst["sessions"]:
        matrix = session["matrix"]
        ciphertext = session["ciphertext"]
        if swap_coordinates:
            matrix = [
                [matrix[1][1], matrix[1][0]],
                [matrix[0][1], matrix[0][0]],
            ]
            ciphertext = [ciphertext[1], ciphertext[0]]
        canonical_sessions.append(
            (
                matrix[0][0],
                matrix[0][1],
                matrix[1][0],
                matrix[1][1],
                ciphertext[0],
                ciphertext[1],
            )
        )
    payload = [
        inst["q_min"],
        inst["q_max"],
        inst["secret_bound"],
        sorted(canonical_sessions),
    ]
    return json.dumps(payload, separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    # Session order and the names of the two vector coordinates are irrelevant.
    representative = min(_canonical_public(inst, False), _canonical_public(inst, True))
    return hashlib.sha256(representative.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    clean = {key: value for key, value in params.items() if key != "_preset"}
    n = int(clean.get("n", 65_536))
    q_min = int(clean.get("q_min", 1_000_000))
    secret_bound = int(clean.get("secret_bound", 65_536))
    # Grow the candidate-modulus haystack and arithmetic precision.  The answer
    # remains exactly three integers.  Stop before 64-bit primality support or
    # the compact Euclidean route's 300-operation allowance becomes doubtful.
    if q_min.bit_length() < 55 and n < 2**23:
        return {
            "n": n * 2,
            "q_min": q_min * 4 + 2,
            "secret_bound": secret_bound,
        }
    if n < 2**24:
        return {"n": n * 2, "q_min": q_min, "secret_bound": secret_bound}
    return None


def _solve_first_session(inst: dict, modulus: int) -> list[int] | None:
    session = inst["sessions"][0]
    matrix = session["matrix"]
    ciphertext = session["ciphertext"]
    a, b = matrix[0]
    c, d = matrix[1]
    determinant = (a * d - b * c) % modulus
    try:
        inverse = pow(determinant, -1, modulus)
    except (ValueError, ZeroDivisionError):
        return None
    s1 = ((d * ciphertext[0] - b * ciphertext[1]) * inverse) % modulus
    s2 = ((a * ciphertext[1] - c * ciphertext[0]) * inverse) % modulus
    if s1 >= inst["secret_bound"] or s2 >= inst["secret_bound"]:
        return None
    return [s1, s2]


def _reference_candidate_search(inst: dict) -> tuple[list[int] | None, int]:
    """Paper Section V-B's one-candidate-at-a-time consistency search."""
    trials = 0
    for modulus in range(inst["q_min"], inst["q_max"]):
        trials += 1
        secret = _solve_first_session(inst, modulus)
        if secret is None:
            continue
        answer = [modulus, secret[0], secret[1]]
        if verify(inst, answer)[0]:
            return answer, trials
    return None, trials


def _euclid_divisions(a: int, b: int) -> tuple[int, int]:
    a, b = abs(a), abs(b)
    divisions = 0
    while b:
        a, b = b, a % b
        divisions += 1
    return a, divisions


def _inverse_with_count(value: int, modulus: int) -> tuple[int, int]:
    old_r, r = value % modulus, modulus
    old_s, s = 1, 0
    divisions = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        divisions += 1
    if old_r != 1:
        raise ZeroDivisionError("noninvertible determinant")
    return old_s % modulus, divisions


def _compact_recover(inst: dict) -> tuple[list[int] | None, int]:
    """Recover with augmented minors; return answer and counted operations."""
    minors = _minor_values(inst)
    # Each displayed 3x3 determinant uses six multiplications and five additions
    # or subtractions in _det3.
    operations = 11 * len(minors)
    divisor = minors[0]
    for value in minors[1:]:
        divisor, divisions = _euclid_divisions(divisor, value)
        operations += divisions
    if divisor < inst["q_min"] or divisor >= inst["q_max"]:
        return None, operations

    session = inst["sessions"][0]
    matrix = session["matrix"]
    ciphertext = session["ciphertext"]
    a, b = matrix[0]
    c, d = matrix[1]
    determinant = (a * d - b * c) % divisor
    operations += 3  # two products, one subtraction/reduction unit
    try:
        inverse, divisions = _inverse_with_count(determinant, divisor)
    except ZeroDivisionError:
        return None, operations
    operations += divisions
    s1 = ((d * ciphertext[0] - b * ciphertext[1]) * inverse) % divisor
    s2 = ((a * ciphertext[1] - c * ciphertext[0]) * inverse) % divisor
    operations += 10
    answer = [divisor, s1, s2]
    return (answer if verify(inst, answer)[0] else None), operations


def _candidate_for_modulus(inst: dict, modulus: int) -> list[int] | None:
    if modulus < inst["q_min"] or modulus >= inst["q_max"]:
        return None
    secret = _solve_first_session(inst, modulus)
    if secret is None:
        return None
    return [modulus, secret[0], secret[1]]


def _attack_max_public_plus_one(inst: dict) -> list[int] | None:
    public_max = max(
        value
        for session in inst["sessions"]
        for value in (
            *session["matrix"][0],
            *session["matrix"][1],
            *session["ciphertext"],
        )
    )
    guess = public_max + 1
    if guess < inst["q_min"] or guess >= inst["q_max"]:
        guess = inst["q_min"]
    return _candidate_for_modulus(inst, guess)


def _attack_greedy_lower_edge(inst: dict, limit: int = 256) -> list[int] | None:
    stop = min(inst["q_max"], inst["q_min"] + limit)
    for modulus in range(inst["q_min"], stop):
        candidate = _candidate_for_modulus(inst, modulus)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_no_wrap(inst: dict) -> list[int] | None:
    """Obvious by-hand ansatz: treat the first congruence as integer equality."""
    session = inst["sessions"][0]
    matrix = session["matrix"]
    y = session["ciphertext"]
    a, b = matrix[0]
    c, d = matrix[1]
    determinant = a * d - b * c
    if determinant == 0:
        return None
    numerator1 = d * y[0] - b * y[1]
    numerator2 = a * y[1] - c * y[0]
    if numerator1 % determinant or numerator2 % determinant:
        return None
    return [inst["q_min"], numerator1 // determinant, numerator2 // determinant]


def _attack_random_moduli(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[list[int] | None, int]:
    for attempt in range(1, restarts + 1):
        modulus = rng.randrange(inst["q_min"], inst["q_max"])
        candidate = _candidate_for_modulus(inst, modulus)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def _swap_coordinate_instance(inst: dict) -> dict:
    transformed = {
        key: json.loads(json.dumps(value))
        for key, value in inst.items()
        if key != "answer"
    }
    sessions = []
    for session in inst["sessions"]:
        matrix = session["matrix"]
        ciphertext = session["ciphertext"]
        sessions.append(
            {
                "matrix": [
                    [matrix[1][1], matrix[1][0]],
                    [matrix[0][1], matrix[0][0]],
                ],
                "ciphertext": [ciphertext[1], ciphertext[0]],
            }
        )
    transformed["sessions"] = sessions
    transformed["answer"] = [
        inst["answer"][0],
        inst["answer"][2],
        inst["answer"][1],
    ]
    return transformed


def selftest() -> dict:
    report: dict[str, Any] = {
        "paper": "2603.28313",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: all presets and several seeds; also independently recover through the
    # public determinantal certificate and check JSON-native serialization.
    g1_failures = []
    checks = 0
    compact_operation_counts = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17, 991):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            compact, operations = _compact_recover(inst)
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if preset == SHIPPING_DIFFICULTY:
                compact_operation_counts.append(operations)
            if not ok or compact != inst["answer"] or not json_native:
                g1_failures.append(
                    {
                        "preset": preset,
                        "seed": seed,
                        "verify_reason": reason,
                        "compact_matches": compact == inst["answer"],
                        "json_native": json_native,
                    }
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": checks,
        "inverse_generation": "sample [q,s1,s2] first, then encrypt",
        "public_uniqueness_certificate": "gcd of all four augmented 3x3 minors equals q",
        "failures": g1_failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five distinct structural corruptions and five distinct explanations.
    answer = shipping["answer"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_secret_coordinates": [answer[0], answer[2], answer[1]],
        "duplicate_one": answer + [answer[-1]],
        "empty": [],
        "out_of_range_modulus": [shipping["q_max"], answer[1], answer[2]],
    }
    corruption_results = {}
    reasons = []
    for name, corrupted in corruptions.items():
        ok, reason = verify(shipping, corrupted)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(result["rejected"] for result in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: a realistic response with prose and a Markdown block around the tags.
    encoded = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = (
        "The shared modular invariant fixes the triple.\n```json\n"
        "<answer>\n" + encoded + "\n</answer>\n```\n"
        "The equations then check directly."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (
            parsed == shipping["answer"]
            and parse_answer("garbage only") is None
            and parse_answer("<answer>[1, nope]</answer>") is None
        ),
        "realistic_response": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage only") is None,
        "malformed_returns_none": parse_answer("<answer>[1, nope]</answer>") is None,
    }

    # G4/G5 density at the actual shipping preset.  This samples exactly the
    # statement-aware q interval and coordinate bounds, not a larger bit-string
    # universe.
    guess_rng = random.Random(260328313)
    samples = 200_000
    hits = 0
    density_start = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": space,
        "exact_unique_witness_probability": 1 / space,
        "sampler": "uniform q in the published interval and uniform bounded secret coordinates",
    }

    # G6: four failing no-tool attacks, plus the successful paper algorithm in
    # the separate Track-B reference slot.
    attack_counts = {
        "outlier_max_public_plus_one": {"successes": 0, "attempts": 0},
        "greedy_lower_edge_256": {"successes": 0, "attempts": 0},
        "random_modulus_restart_256": {"successes": 0, "attempts": 0},
        "by_hand_no_wrap_integer_solve": {"successes": 0, "attempts": 0},
    }
    random_restart_wall = 0.0
    random_restart_trials = 0
    reference_wall = 0.0
    reference_trials = 0
    reference_solves = 0
    route_operations = []
    for seed in range(8100, 8108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        fixed_attacks = {
            "outlier_max_public_plus_one": _attack_max_public_plus_one(inst),
            "greedy_lower_edge_256": _attack_greedy_lower_edge(inst),
            "by_hand_no_wrap_integer_solve": _attack_no_wrap(inst),
        }
        for name, candidate in fixed_attacks.items():
            solved = candidate is not None and verify(inst, candidate)[0]
            attack_counts[name]["successes"] += int(solved)
            attack_counts[name]["attempts"] += 1

        restart_start = time.perf_counter()
        candidate, trials = _attack_random_moduli(
            inst, random.Random(seed ^ 0xA51CE), 256
        )
        random_restart_wall += time.perf_counter() - restart_start
        random_restart_trials += trials
        solved = candidate is not None and verify(inst, candidate)[0]
        attack_counts["random_modulus_restart_256"]["successes"] += int(solved)
        attack_counts["random_modulus_restart_256"]["attempts"] += 1

        reference_start = time.perf_counter()
        recovered, trials = _reference_candidate_search(inst)
        reference_wall += time.perf_counter() - reference_start
        reference_trials += trials
        reference_solves += int(recovered is not None and verify(inst, recovered)[0])

        compact, operations = _compact_recover(inst)
        if compact != inst["answer"]:
            g1_failures.append({"seed": seed, "failure": "compact recovery mismatch"})
        route_operations.append(operations)

    all_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attack_counts.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_solves == 8,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "Section V-B candidate-q consistency search",
            "complexity": "O(n log q) exact arithmetic for fixed 2x2 systems",
            "wall_clock_sec_total_8": reference_wall,
            "wall_clock_sec_mean": reference_wall / 8,
            "candidate_moduli_tested_total": reference_trials,
            "candidate_moduli_tested_mean": reference_trials / 8,
            "operations": reference_trials,
            "operation_unit": "one small modular-system consistency trial",
            "solves": f"{reference_solves}/8, as expected",
        },
    }

    demo = make_instance(seed=20260905, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": hits / samples < 1e-6 and all_failed and reference_solves == 8,
        "density_hits": hits,
        "density_total": samples,
        "baseline_wall_clock_sec": random_restart_wall,
        "baseline_iterations": random_restart_trials,
        "shipping_density": {
            "hits": hits,
            "total": samples,
            "observed_fraction": hits / samples,
            "exact_fraction_from_uniqueness": f"1/{space}",
            "sampling_wall_clock_sec": density_wall,
        },
        "demo_exact_enumeration": {
            "candidate_space": search_space(demo),
            "valid_answers": enumerate_all(demo),
        },
        "strongest_failing_attack": {
            "name": "random candidate-modulus restart with exact first-system solve",
            "wall_clock_sec_total_8": random_restart_wall,
            "iterations": random_restart_trials,
            "successes": attack_counts["random_modulus_restart_256"]["successes"],
        },
        "successful_reference_cost": {
            "wall_clock_sec_total_8": reference_wall,
            "candidate_moduli_tested": reference_trials,
        },
    }

    # G7: double the candidate interval while keeping the witness length fixed.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    build_start = time.perf_counter()
    doubled = make_instance(seed=777, **doubled_params)
    doubled_build = time.perf_counter() - build_start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) == 2 * space,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_space": space,
        "doubled_space": search_space(doubled),
        "answer_length_shipping": len(shipping["answer"]),
        "answer_length_doubled": len(doubled["answer"]),
        "doubled_build_sec": doubled_build,
        "verify_reason": doubled_reason,
    }

    # G8: reorder sessions, rename the two coordinates, and compose both maps.
    invariance_checks = 0
    preservation_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        unrelated_keys.append(original_key)

        reordered = json.loads(json.dumps(inst))
        reordered["sessions"].reverse()
        swapped = _swap_coordinate_instance(inst)
        composed = _swap_coordinate_instance(reordered)
        for name, transformed in (
            ("session_reordering", reordered),
            ("coordinate_swap", swapped),
            ("coordinate_swap_plus_reordering", composed),
        ):
            invariance_checks += 1
            preservation_checks += 1
            if canonical_key(transformed) != original_key:
                g8_failures.append(
                    {"seed": seed, "map": name, "failure": "canonical key changed"}
                )
            if not verify(transformed, transformed["answer"])[0]:
                g8_failures.append(
                    {"seed": seed, "map": name, "failure": "map broke certificate"}
                )
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "problem_preservation_checks": preservation_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "canonicalization": (
            "sort sessions and minimize over the two possible coordinate-name permutations"
        ),
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _atom_count(shipping["answer"])
    answer_tokens = (answer_chars + 3) // 4
    intended_operations = max(route_operations + compact_operation_counts)
    arms = {
        key: dict(G9_ORACLE_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (
        arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": (
            answer_chars <= 2000
            and answer_atoms <= 256
            and intended_operations <= 300
        ),
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "token_measure": "ceil(minified JSON characters / 4)",
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_operations,
        "intended_route_operation_range": [
            min(route_operations + compact_operation_counts),
            max(route_operations + compact_operation_counts),
        ],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_passes = [
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate_passes)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
