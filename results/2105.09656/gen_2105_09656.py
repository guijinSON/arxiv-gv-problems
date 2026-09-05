"""Verified generator from Proposition 4.7 of arXiv:2105.09656.

The paper needs the value of a cyclotomic expression in F_{p^2} while
choosing the two orbits that form its hemisystem.  Proposition 4.7 and
Appendix A prove that the expression is +1 or -1 according only to p modulo
16.  This module composes several independently affine-encoded copies.

Generation is theorem-backed: it samples primes in the two theorem regimes,
uses the proved sign to plant each answer, and never evaluates the public
power expression to discover that answer.  Verification independently does
the exact finite-field exponentiation.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "quadratic finite fields F_p[H]/(H^2-2)",
        "cyclotomic power expressions used to select hemisystem orbits",
        "affine encodings of finite-field elements",
    ],
    "verification_operations": [
        "exact arithmetic in a quadratic finite field",
        "binary exponentiation",
        "exact affine decoding and equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The cyclotomic expression is invariant under the choice of square "
        "root of 2 and is controlled only by p modulo 16; without noticing "
        "this, each displayed value requires a long finite-field power."
    ),
    "hardness_basis": (
        "Track B: binary exponentiation evaluates the batch in O(kb) "
        "quadratic-field multiplications for b-bit public exponents; "
        "at n=63,k=48 selftest measures 71,868 exact coefficient operations, "
        "8,972 field multiplications and 0.004--0.008 seconds per instance "
        "across repeated measured runs, "
        "whereas Proposition 4.7 and Appendix A reduce the compact route to "
        "144 residue and affine operations, which fits in context only if the "
        "modulo-16 invariant is found."
    ),
    "max_answer_tokens": 481,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON matrix with exactly k rows [a,0]; after the immediate identity "
        "L_i^2=1, row i is one of the two distinct affine encodings "
        "offset_i-scale_i or offset_i+scale_i modulo p_i."
    ),
    "bounds": {
        "rows": "k",
        "columns": 2,
        "choices_per_row": 2,
        "entry_i": "one of the two encoded sign branches, with second coordinate 0",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "k": 2},
    "easy": {"n": 63, "k": 32},
    "medium": {"n": 63, "k": 40},
    "hard": {"n": 63, "k": 48},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The value of each cyclotomic expression is controlled by its prime's "
    "residue class modulo 16 and not by the displayed choice of root."
)
PLACEBO_HINT = (
    "The value of each finite-field expression rewards careful handling of "
    "the displayed powers and of the chosen coefficient conventions."
)

# Filled from the three script-owned hardening runs before final delivery.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and source.  Section 2 fixes the Hermitian surface and Section 3
defines a half-hemisystem and the orbit conditions (C)--(E).  In Section 4,
the case p == 5 (mod 8) requires a square root h of 2 in F_{p^2}.  Equation
(4.12) introduces lambda=(1+h)^((p+1)/2) h^((p-1)/2), and Proposition 4.7,
proved in Appendix A, states lambda=+1 for p == 13 (mod 16) and lambda=-1
for p == 5 (mod 16).  The proof also shows that lambda does not depend on
which of h and -h is used.  This sign is used in the explicit base generator
and hence in choosing the two group orbits that form the half-hemisystem.

Step-0 hardness decision.  Fast exponentiation is an efficient algorithm, so
Track A would be false.  This is Track B: the mechanical route performs the
two large powers in every quadratic field, while Appendix A compresses each
one to a residue test and an affine add/subtract.  The full hemisystem itself
was not chosen as the answer: already at p=5 it contains 378 lines, exceeding
the 256-atom output cap.  The present family keeps the paper's exact native
finite-field object rather than replacing the geometry by an incidence graph.

Generation.  Half of the primes are sampled in each of the two residue
classes, all pass deterministic Miller--Rabin for 64-bit inputs, and the list
is shuffled.  For each coordinate the theorem-backed sign is hidden by a
uniform nonzero affine scale and offset.  The public choice h or -h is sampled
independently.  Plants and apparent alternatives therefore use the same
prime/encoding distribution; only the theorem's invariant distinguishes them.
Beyond 63, n grows the displayed exponents at fixed answer length by adding
multiples of p^2-1, the order of the quadratic field's multiplicative group.

Candidate language.  Squaring Equation (4.12) immediately gives lambda^2=1,
so a structure-aware guesser gets the two affine sign branches for free.  G4
therefore samples exactly those 2^k matrices, not the much larger and misleading
product of all quadratic fields.

Attack handling.  A balanced mix defeats constant-sign greedy rules.  Random
root choices defeat the tempting assumption that the answer follows the
displayed square root.  The panel also chooses the smaller encoded branch as a
per-row magnitude outlier and tries 256 independent plus/minus restarts.  Exact
binary exponentiation is expected to succeed and is reported separately as the
Track-B reference algorithm.
""".strip()


# ---------------------------------------------------------------------------
# Deterministic prime generation below 2^64


_MR_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)


@functools.lru_cache(maxsize=16384)
def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin primality test for value < 2^64."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in _MR_BASES_64:
        a = base % value
        if a == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _validate_params(n: int, k: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if isinstance(k, bool) or not isinstance(k, int):
        raise ValueError("k must be an integer")
    if n < 4 or n > 4096:
        raise ValueError("n must lie from 4 through 4096 inclusive")
    if k < 2 or k > 96 or k % 2:
        raise ValueError("k must be an even integer from 2 through 96")


def _next_prime_with_residue(n: int, residue: int, rng: random.Random,
                             used: set[int]) -> int:
    lower = 1 << (n - 1)
    upper = 1 << n
    start = rng.randrange(lower, upper)
    candidate = start + ((residue - start) % 16)
    if candidate >= upper:
        candidate = lower + ((residue - lower) % 16)
    first = candidate
    while True:
        if candidate not in used and _is_prime_64(candidate):
            return candidate
        candidate += 16
        if candidate >= upper:
            candidate = lower + ((residue - lower) % 16)
        if candidate == first:
            raise RuntimeError("prime search exhausted the requested interval")


def _theorem_sign(p: int) -> int:
    """Proposition 4.7: return the integer representative +1 or -1."""
    residue = p % 16
    if residue == 13:
        return 1
    if residue == 5:
        return -1
    raise ValueError("Proposition 4.7 applies only for p == 5 or 13 (mod 16)")


def make_instance(n: int, seed: int = 0, k: int = 32, **params) -> dict:
    """Make a theorem-backed batch; no public power is evaluated here."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameters: {unknown}")
    _validate_params(n, k)
    rng = random.Random(seed)

    prime_bits = min(n, 63)
    if n == 4 and k == 2:
        primes = [5, 13]
        rng.shuffle(primes)
    else:
        residues = [5] * (k // 2) + [13] * (k // 2)
        rng.shuffle(residues)
        used: set[int] = set()
        primes = []
        for residue in residues:
            p = _next_prime_with_residue(prime_bits, residue, rng, used)
            used.add(p)
            primes.append(p)

    entries = []
    answer = []
    for p in primes:
        root_sign = rng.choice((-1, 1))
        offset = rng.randrange(p)
        scale = rng.randrange(1, p)
        sign = _theorem_sign(p)
        encoded = (offset + sign * scale) % p
        left_exponent = (p + 1) // 2
        right_exponent = (p - 1) // 2
        if n > 63:
            # Both bases are nonzero.  Adding a multiple of |F_(p^2)^*| is a
            # structure-preserving transformation that increases the public
            # exponent length while carrying Proposition 4.7's value through.
            period = p * p - 1
            # n=64 starts with one period; every subsequent increment doubles
            # its multiplier, so larger n strictly grows the mechanical work.
            shift = n - 64
            multiple = 1 << shift
            left_exponent += multiple * period
            right_exponent += multiple * period
        entries.append({
            "p": p,
            "root_sign": root_sign,
            "offset": offset,
            "scale": scale,
            "left_exponent": left_exponent,
            "right_exponent": right_exponent,
        })
        answer.append([encoded, 0])

    return {
        "family": "Appendix-A cyclotomic sign batch",
        "n": n,
        "k": k,
        "entries": entries,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Exact arithmetic in F_p[H]/(H^2-2)


class _Counter:
    __slots__ = ("field_multiplications", "field_additions",
                 "coefficient_multiplications", "coefficient_additions")

    def __init__(self) -> None:
        self.field_multiplications = 0
        self.field_additions = 0
        self.coefficient_multiplications = 0
        self.coefficient_additions = 0

    @property
    def exact_operations(self) -> int:
        return (self.coefficient_multiplications
                + self.coefficient_additions)


def _fadd(x: tuple[int, int], y: tuple[int, int], p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    if counter is not None:
        counter.field_additions += 1
        counter.coefficient_additions += 2
    return ((x[0] + y[0]) % p, (x[1] + y[1]) % p)


def _fmul(x: tuple[int, int], y: tuple[int, int], p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    # (a+bH)(c+dH)=(ac+2bd)+(ad+bc)H, H^2=2.
    if counter is not None:
        counter.field_multiplications += 1
        counter.coefficient_multiplications += 5
        counter.coefficient_additions += 3
    a, b = x
    c, d = y
    return ((a * c + 2 * b * d) % p, (a * d + b * c) % p)


def _fpow(base: tuple[int, int], exponent: int, p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    result = (1, 0)
    while exponent:
        if exponent & 1:
            result = _fmul(result, base, p, counter)
        exponent >>= 1
        if exponent:
            base = _fmul(base, base, p, counter)
    return result


def _lambda_uncached(p: int, root_sign: int,
                     counter: _Counter | None = None,
                     left_exponent: int | None = None,
                     right_exponent: int | None = None) -> tuple[int, int]:
    root = (0, root_sign % p)
    one_plus_root = _fadd((1, 0), root, p, counter)
    if left_exponent is None:
        left_exponent = (p + 1) // 2
    if right_exponent is None:
        right_exponent = (p - 1) // 2
    left = _fpow(one_plus_root, left_exponent, p, counter)
    right = _fpow(root, right_exponent, p, counter)
    return _fmul(left, right, p, counter)


@functools.lru_cache(maxsize=8192)
def _lambda_value(p: int, root_sign: int, left_exponent: int,
                  right_exponent: int) -> tuple[int, int]:
    return _lambda_uncached(
        p, root_sign, None, left_exponent, right_exponent
    )


def _expected_entry(entry: dict) -> list[int]:
    p = entry["p"]
    lam = _lambda_value(
        p, entry["root_sign"], entry["left_exponent"],
        entry["right_exponent"]
    )
    # The affine map has prime-field coefficients, so apply it to both coords.
    return [
        (entry["offset"] + entry["scale"] * lam[0]) % p,
        (entry["scale"] * lam[1]) % p,
    ]


def _validate_instance(inst: dict) -> tuple[bool, str]:
    try:
        k = inst["k"]
        entries = inst["entries"]
    except (KeyError, TypeError):
        return False, "instance is missing its batch data"
    if not isinstance(k, int) or not isinstance(entries, list) or len(entries) != k:
        return False, "instance batch length is inconsistent"
    for entry in entries:
        if not isinstance(entry, dict):
            return False, "an instance entry is malformed"
        try:
            p = entry["p"]
            root_sign = entry["root_sign"]
            offset = entry["offset"]
            scale = entry["scale"]
            left_exponent = entry["left_exponent"]
            right_exponent = entry["right_exponent"]
        except KeyError:
            return False, "an instance entry is incomplete"
        if (not isinstance(p, int) or p >= 2**64 or not _is_prime_64(p)
                or p % 16 not in (5, 13)):
            return False, "an entry modulus is not an allowed prime"
        if root_sign not in (-1, 1):
            return False, "a root sign is not +1 or -1"
        if (not isinstance(offset, int) or isinstance(offset, bool)
                or not 0 <= offset < p):
            return False, "an affine offset is out of range"
        if (not isinstance(scale, int) or isinstance(scale, bool)
                or not 1 <= scale < p):
            return False, "an affine scale is out of range"
        period = p * p - 1
        if (not isinstance(left_exponent, int) or isinstance(left_exponent, bool)
                or left_exponent <= 0
                or (left_exponent - (p + 1) // 2) % period):
            return False, "a left exponent is outside the licensed period class"
        if (not isinstance(right_exponent, int) or isinstance(right_exponent, bool)
                or right_exponent <= 0
                or (right_exponent - (p - 1) // 2) % period):
            return False, "a right exponent is outside the licensed period class"
    return True, "ok"


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any exact answer by recomputing every public power expression."""
    ok, reason = _validate_instance(inst)
    if not ok:
        return False, reason
    k = inst["k"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k:
        return False, f"answer must contain exactly {k} field elements"
    for i, (row, entry) in enumerate(zip(answer, inst["entries"])):
        if not isinstance(row, list) or len(row) != 2:
            return False, f"row {i} must be a two-integer list [a,b]"
        if any(isinstance(x, bool) or not isinstance(x, int) for x in row):
            return False, f"row {i} contains a non-integer coordinate"
        p = entry["p"]
        if not (0 <= row[0] < p and 0 <= row[1] < p):
            return False, f"row {i} has a coordinate outside [0,p-1]"

    # Full-field random guesses almost surely fail at the first row.  Compact
    # +/- branch guesses are scanned completely so corruption diagnostics can
    # distinguish a transposition from a duplication.
    compact_like = all(row[1] == 0 for row in answer)
    if not compact_like:
        for i, (row, entry) in enumerate(zip(answer, inst["entries"])):
            if row != _expected_entry(entry):
                return False, f"row {i} fails the exact power identity"
        return True, "ok"

    expected = [_expected_entry(entry) for entry in inst["entries"]]
    bad = [i for i, (got, want) in enumerate(zip(answer, expected)) if got != want]
    if not bad:
        return True, "ok"
    if (len(bad) == 2 and answer[bad[0]] == expected[bad[1]]
            and answer[bad[1]] == expected[bad[0]]):
        return False, "two field elements are transposed"
    if sorted(map(tuple, answer)) != sorted(map(tuple, expected)):
        return False, "the encoded values have wrong multiplicities"
    return False, f"row {bad[0]} fails the exact power identity"


# ---------------------------------------------------------------------------
# Rendering and answer parsing


def render(inst: dict) -> str:
    extended = any(
        entry["left_exponent"] != (entry["p"] + 1) // 2
        for entry in inst["entries"]
    )
    expression_lines = ([
        "Define, using the two exponents shown in each row,",
        "",
        "    L_i = (1+r_i)^(E_i) * r_i^(D_i),",
    ] if extended else [
        "Define",
        "",
        "    L_i = (1+r_i)^((p_i+1)/2) * r_i^((p_i-1)/2),",
    ])
    lines = [
        "Evaluate cyclotomic signs in quadratic finite fields",
        "",
        "For each independently listed row i, work in the field",
        "",
        "    F_i = F_{p_i}[H]/(H^2-2).",
        "",
        "Represent a+bH by the JSON pair [a,b], using the unique integers",
        "0 <= a,b < p_i. All additions, multiplications, and powers below are",
        "in F_i. The listed root r_i is either H or -H; in both cases r_i^2=2.",
    ] + expression_lines + [
        "    Z_i = offset_i + scale_i * L_i.",
        "",
        "Compute every Z_i exactly and return them in the listed order. Each",
        "p_i is prime and is 5 or 13 modulo 16, so 2 is a nonsquare modulo",
        "p_i and the displayed quotient really is a field. Every scale is",
        "nonzero. Indices are 0-based; no rows may be omitted or repeated.",
        "",
        f"There are k={inst['k']} rows:",
    ]
    for i, entry in enumerate(inst["entries"]):
        root = "H" if entry["root_sign"] == 1 else "-H"
        suffix = ""
        if extended:
            suffix = (f", E={entry['left_exponent']}, "
                      f"D={entry['right_exponent']}")
        lines.append(f"  {i}: p={entry['p']}, r={root}, "
                     f"offset={entry['offset']}, scale={entry['scale']}{suffix}")
    lines.extend([
        "",
        f"Your answer must be a JSON list of exactly {inst['k']} pairs [a,b].",
        "Pair i is reduced modulo its own p_i with both endpoints allowed; the",
        "coordinate bounds 0 <= a,b < p_i are inclusive on the left and",
        "exclusive on the right.",
        "",
        "Give your final answer inside <answer></answer> tags as that JSON list.",
        "Example: <answer>[[3,0],[7,2]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.I | re.S)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


# ---------------------------------------------------------------------------
# Candidate language, enumeration, canonicalisation, escalation


def random_candidate(inst: dict, rng: random.Random) -> object:
    return [
        _encoded_branch(entry, rng.choice((-1, 1)))
        for entry in inst["entries"]
    ]


def search_space(inst: dict) -> int | None:
    return 1 << inst["k"]


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 100_000:
        return None
    alphabets = [
        [_encoded_branch(entry, -1), _encoded_branch(entry, 1)]
        for entry in inst["entries"]
    ]
    count = 0
    for rows in itertools.product(*alphabets):
        candidate = [list(row) for row in rows]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Normalise row order, root conjugation, and affine output coordinates."""
    primes = sorted(entry["p"] for entry in inst["entries"])
    blob = json.dumps({"family": "A-sign", "primes": primes}, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params["n"])
    k = int(params.get("k", 32))
    # Exhaust the fixed-answer-length exponent axis before adding rows.
    if n < 4096:
        return {"n": min(4096, max(n + 3, n * 2)), "k": k}
    if k < 64:
        return {"n": n, "k": min(64, k + 8)}
    return "cap_bound"


# ---------------------------------------------------------------------------
# Attacks and mandatory self-test


def _encoded_branch(entry: dict, sign: int) -> list[int]:
    return [(entry["offset"] + sign * entry["scale"]) % entry["p"], 0]


def _attack_offset_only(inst: dict) -> list[list[int]]:
    return [[entry["offset"], 0] for entry in inst["entries"]]


def _attack_smaller_branch(inst: dict) -> list[list[int]]:
    """Per-row magnitude probe: retain the smaller encoded sign branch."""
    return [
        min(_encoded_branch(entry, -1), _encoded_branch(entry, 1))
        for entry in inst["entries"]
    ]


def _attack_all_plus(inst: dict) -> list[list[int]]:
    return [_encoded_branch(entry, 1) for entry in inst["entries"]]


def _attack_root_sign(inst: dict) -> list[list[int]]:
    return [_encoded_branch(entry, entry["root_sign"]) for entry in inst["entries"]]


def _attack_random_branches(inst: dict, rng: random.Random,
                            restarts: int) -> tuple[bool, int]:
    for attempt in range(1, restarts + 1):
        candidate = [
            _encoded_branch(entry, rng.choice((-1, 1)))
            for entry in inst["entries"]
        ]
        if verify(inst, candidate)[0]:
            return True, attempt
    return False, restarts


def _reference_answer(inst: dict,
                      counter: _Counter | None = None) -> list[list[int]]:
    out = []
    for entry in inst["entries"]:
        p = entry["p"]
        lam = _lambda_uncached(
            p, entry["root_sign"], counter, entry["left_exponent"],
            entry["right_exponent"]
        )
        out.append([
            (entry["offset"] + entry["scale"] * lam[0]) % p,
            entry["scale"] * lam[1] % p,
        ])
    return out


def _atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atoms(v) for v in value)
    return 1


def _affine_reencode(inst: dict) -> tuple[dict, list[list[int]]]:
    """A deterministic problem isomorphism used by the G8 test."""
    transformed = {k: v for k, v in inst.items() if k not in ("entries", "answer")}
    entries = []
    carried = []
    for entry, row in zip(inst["entries"], inst["answer"]):
        p = entry["p"]
        old_scale = entry["scale"]
        lam = (row[0] - entry["offset"]) * pow(old_scale, -1, p) % p
        new_offset = (entry["offset"] + 3) % p
        new_scale = (entry["scale"] * 2) % p or 1
        new_entry = dict(entry, offset=new_offset, scale=new_scale)
        entries.append(new_entry)
        carried.append([(new_offset + new_scale * lam) % p, 0])
    transformed["entries"] = entries
    transformed["answer"] = carried
    return transformed, carried


def _period_lift(inst: dict) -> tuple[dict, list[list[int]]]:
    """Add one multiplicative-group period to both public exponents."""
    transformed = {k: v for k, v in inst.items() if k not in ("entries", "answer")}
    transformed["entries"] = []
    for entry in inst["entries"]:
        period = entry["p"] * entry["p"] - 1
        transformed["entries"].append(dict(
            entry,
            left_exponent=entry["left_exponent"] + period,
            right_exponent=entry["right_exponent"] + period,
        ))
    transformed["answer"] = json.loads(json.dumps(inst["answer"]))
    return transformed, transformed["answer"]


def selftest() -> dict:
    report: dict = {}

    # G1: all named rungs, several seeds, JSON-native answers.
    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            checks += 1
            ok, why = verify(inst, inst["answer"])
            if not ok:
                failures.append(f"{preset}/seed={seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/seed={seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    planted = json.loads(json.dumps(inst["answer"]))
    # Pick opposite-sign rows whose encoded representatives fit in each other's
    # moduli, so the swap and duplicate tests reach semantic (not range) checks.
    plus_i = minus_i = -1
    for i, left in enumerate(inst["entries"]):
        for j, right in enumerate(inst["entries"]):
            if (_theorem_sign(left["p"]) == 1
                    and _theorem_sign(right["p"]) == -1
                    and planted[i][0] < right["p"]
                    and planted[j][0] < left["p"]):
                plus_i, minus_i = i, j
                break
        if plus_i >= 0:
            break
    if plus_i < 0:  # astronomically unlikely for the balanced 32-row preset
        raise AssertionError("could not find cross-compatible corruption rows")

    # G2: five meaningful corruptions and five distinct rejection reasons.
    corruptions = {}
    corruptions["drop_one"] = planted[:-1]
    swapped = json.loads(json.dumps(planted))
    swapped[plus_i], swapped[minus_i] = swapped[minus_i], swapped[plus_i]
    corruptions["swap_two"] = swapped
    duplicated = json.loads(json.dumps(planted))
    duplicated[plus_i] = list(duplicated[minus_i])
    corruptions["duplicate_one"] = duplicated
    corruptions["empty"] = []
    outside = json.loads(json.dumps(planted))
    outside[0] = [inst["entries"][0]["p"], 0]
    corruptions["out_of_range"] = outside
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = "ACCEPTED" if ok else why
    report["G2_rejects_corruption"] = {
        "pass": (all(v != "ACCEPTED" for v in rejected.values())
                 and len(set(rejected.values())) == len(rejected)),
        "rejections": rejected,
        "distinct_reasons": len(set(rejected.values())),
    }

    # G3: tagged JSON amid prose and fences; malformed output returns None.
    realistic = (
        "I reduced each row exactly.\n\n<answer>\n```json\n"
        + json.dumps(planted) + "\n```\n</answer>\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer here") is None,
        "parsed_matches": parsed == planted,
        "garbage_returns_none": parse_answer("<answer>not json</answer>") is None,
    }

    # G4 and shipping density: exact structure-aware candidate sampler.
    total = 200_000
    rng = random.Random(0x210509656)
    hits = 0
    t0 = time.perf_counter()
    for _ in range(total):
        if verify(inst, random_candidate(inst, rng))[0]:
            hits += 1
    sample_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": hits / total,
        "prior": (
            "uniform independently over the two affine sign branches implied "
            "by the freely deducible identity L_i^2=1"
        ),
        "candidate_space": search_space(inst),
        "sampling_wall_seconds": sample_seconds,
    }

    # G5: sampled shipping density plus a measured stronger branch restart.
    baseline_rng = random.Random(913)
    t0 = time.perf_counter()
    baseline_success, baseline_iterations = _attack_random_branches(
        inst, baseline_rng, 4096
    )
    baseline_seconds = time.perf_counter() - t0
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": hits / total < 1e-6 and not baseline_success and demo_count == 1,
        "shipping_observed_valid_fraction": hits / total,
        "shipping_density_sample_count": total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(inst),
        "baseline_wall_seconds": baseline_seconds,
        "baseline_iterations": baseline_iterations,
        "baseline_successes": int(baseline_success),
        "demo_exact_solution_count": demo_count,
        "enumerate_all_shipping": enumerate_all(inst),
    }

    # G6: four failing no-tool attacks; standard exponentiation is separate.
    attack_counts = {
        "outlier_smaller_encoded_branch": 0,
        "greedy_all_plus_branch": 0,
        "random_restart_256_pm_branches": 0,
        "by_hand_root_sign_ansatz": 0,
    }
    attempts = 8
    reference_successes = 0
    reference_counter = _Counter()
    reference_seconds = 0.0
    for seed in range(100, 100 + attempts):
        attack_inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_smaller_encoded_branch": _attack_smaller_branch(attack_inst),
            "greedy_all_plus_branch": _attack_all_plus(attack_inst),
            "by_hand_root_sign_ansatz": _attack_root_sign(attack_inst),
        }
        for name, candidate in candidates.items():
            attack_counts[name] += int(verify(attack_inst, candidate)[0])
        won, _ = _attack_random_branches(
            attack_inst, random.Random(seed ^ 0xA51CE), 256
        )
        attack_counts["random_restart_256_pm_branches"] += int(won)
        t0 = time.perf_counter()
        ref = _reference_answer(attack_inst, reference_counter)
        reference_seconds += time.perf_counter() - t0
        reference_successes += int(verify(attack_inst, ref)[0])
    attacks = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "binary square-and-multiply in each quadratic field",
            "complexity": "O(k b) exact F_(p^2) multiplications for b-bit exponents",
            "wall_clock_sec": reference_seconds,
            "mean_wall_clock_sec": reference_seconds / attempts,
            "operations": reference_counter.exact_operations,
            "field_multiplications": reference_counter.field_multiplications,
            "mean_exact_operations": reference_counter.exact_operations // attempts,
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    # G7: double the public exponent length while keeping the witness length
    # fixed.  make_instance carries the value through by adding multiples of
    # |F_(p^2)^*| to the exponents.
    doubled_n = shipping_params["n"] * 2
    doubled = make_instance(n=doubled_n, k=shipping_params["k"], seed=77)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    base_bits = max(max(entry["left_exponent"].bit_length(),
                        entry["right_exponent"].bit_length())
                    for entry in inst["entries"])
    doubled_bits = max(max(entry["left_exponent"].bit_length(),
                           entry["right_exponent"].bit_length())
                       for entry in doubled["entries"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled_n > shipping_params["n"]
                 and doubled["k"] == inst["k"]
                 and doubled_bits > base_bits),
        "base_n": shipping_params["n"],
        "doubled_n": doubled_n,
        "answer_rows_unchanged": doubled["k"] == inst["k"],
        "doubled_verify": doubled_why,
        "base_max_exponent_bits": base_bits,
        "doubled_max_exponent_bits": doubled_bits,
        "reference_exponent_bit_growth": doubled_bits / base_bits,
    }

    # G8: row permutations, root conjugations, affine/output and exponent-period
    # re-encodings, plus a composition of the symmetries.
    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        base = make_instance(seed=1000 + seed, **shipping_params)
        base_key = canonical_key(base)
        keys.append(base_key)

        reversed_inst = dict(base)
        reversed_inst["entries"] = list(reversed(base["entries"]))
        reversed_inst["answer"] = list(reversed(base["answer"]))

        conjugated = dict(base)
        conjugated["entries"] = [
            dict(entry, root_sign=-entry["root_sign"])
            for entry in base["entries"]
        ]
        conjugated["answer"] = json.loads(json.dumps(base["answer"]))

        affine, affine_answer = _affine_reencode(base)
        lifted, lifted_answer = _period_lift(base)

        composed, composed_answer = _affine_reencode(conjugated)
        composed, composed_answer = _period_lift(composed)
        composed["entries"] = list(reversed(composed["entries"]))
        composed["answer"] = list(reversed(composed_answer))

        for transformed, carried in (
            (reversed_inst, reversed_inst["answer"]),
            (conjugated, conjugated["answer"]),
            (affine, affine_answer),
            (lifted, lifted_answer),
            (composed, composed["answer"]),
        ):
            invariant_checks += int(canonical_key(transformed) == base_key)
            carried_checks += int(verify(transformed, carried)[0])
    report["G8_canonical_key"] = {
        "pass": (invariant_checks == 100 and carried_checks == 100
                 and len(set(keys)) == 20),
        "invariance_checks": invariant_checks,
        "invariance_attempts": 100,
        "transformed_witness_checks": carried_checks,
        "transformed_witness_attempts": 100,
        "unrelated_distinct": len(set(keys)),
        "unrelated_attempts": 20,
        "transformations": (
            "row permutation, independent H->-H conjugation, invertible affine "
            "output re-encoding, multiplicative-period exponent lift, and their "
            "composition"
        ),
    }

    # G9(c) is the gate; the oracle arms are recorded diagnostics.
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    # Decimal integers are split into at most three-digit tokens by the corpus
    # tokenizer.  For compact JSON [[a,0],...], this count matches both cl100k
    # and o200k on the measured shipping answers; 481 is the theoretical worst
    # case for 48 rows of 63-bit values.
    answer_tokens = (sum(math.ceil(len(str(row[0])) / 3) + 1
                         for row in inst["answer"])
                     + 2 * inst["k"] + 1)
    answer_elements = _atoms(inst["answer"])
    intended_operations = 3 * inst["k"]
    arms = {
        arm: dict(G9_EVIDENCE.get(arm, {"solved": 0, "attempts": 0}))
        for arm in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
