"""Leading minimal-polynomial coefficients and subtrace under affine changes.

This is a self-contained Track-B generator grounded in Section 1 and Lemma 1.1
of arXiv:2405.11463.  The paper identifies the subtrace of a finite-field
element with the degree-(n-2) coefficient of its monic minimal polynomial.

Generation composes invertible affine maps and applies the binomial identity to
an explicitly irreducible polynomial.  It never solves the generated instance.
Verification independently recomposes the maps and checks the requested
coefficients with exact modular arithmetic.  There is no file I/O, networking,
or printing at import time.
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
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import sparse_poly as _gv_sparse_poly  # noqa: F401
except ImportError:
    _gv_sparse_poly = None


TRACK = "B"

# q = 7*2^20+1 is prime.  The element 3 has order q-1, as witnessed by
# 3^((q-1)/2) != 1 and 3^((q-1)/7) != 1.  Consequently Y^n-3 is irreducible
# over F_q for every power of two n <= 2^20 (the standard binomial criterion).
_Q = 7_340_033
_RADICAND = 3
_MAX_DEGREE = 1 << 20


def _is_prime_32(value: int) -> bool:
    """Deterministic Miller--Rabin for the fixed 32-bit field modulus."""
    if value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 3, 5, 7, 11):
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


_Q_IS_PRIME = _is_prime_32(_Q)


PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "finite extension F_q[Y]/(Y^n-3)",
        "minimal polynomial over F_q",
        "affine changes of a finite-field generator",
        "trace and subtrace coefficients",
    ],
    "verification_operations": [
        "exact affine-map composition modulo q",
        "exact binomial-coefficient identities modulo q",
        "exact sparse-polynomial coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize that a long chain of affine substitutions is still one "
        "affine map, so its two aggregate coefficients determine the leading "
        "minimal-polynomial terms without expanding a degree-n polynomial."
    ),
    "hardness_basis": (
        "Track B: dense binomial expansion computes all n+1 coefficients in "
        "O(n+k) exact modular operations; at shipping n=4096,k=8 it "
        "materialized 4,097 coefficients in 20,508 counted operations and "
        "about 0.001 seconds, whereas composing the affine maps and evaluating "
        "only the two leading coefficients takes at most 60 exact operations "
        "and requires recognizing the unannounced change-of-variables invariant."
    ),
    "max_answer_tokens": 12,
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
    "demo": {"n": 8, "chain_length": 2, "coefficient_cap": 1},
    "easy": {"n": 4_096, "chain_length": 8},
    "medium": {"n": 65_536, "chain_length": 16},
    "hard": {"n": 262_144, "chain_length": 32},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The entire affine chain has only two aggregate coefficients, independent "
    "of the degree of the polynomial."
)
PLACEBO_HINT = (
    "The finite-field conventions make careful modular reduction important "
    "throughout the coefficient calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A descending three-term sparse-polynomial fragment over F_q: exactly "
        "[[1,[n]],[c1,[n-1]],[c2,[n-2]]], where c1 ranges over F_q and c2 "
        "is constrained by the freely deducible leading-binomial relation "
        "c2=((n-1)/(2n))*c1^2 in F_q."
    ),
    "bounds": {
        "terms": 3,
        "variables": 1,
        "free_coefficients": 1,
        "coefficient_modulus": _Q,
        "max_degree": _MAX_DEGREE,
    },
}

NOTES = r"""
STEP 0.  Section 1 defines STr_{q^n/q}(epsilon) as the sum of pairwise
products of distinct Frobenius conjugates.  Expanding the monic minimal
polynomial shows that this subtrace is exactly its x^(n-2) coefficient.
Lemma 1.1 gives the equivalent identity

  STr(epsilon) = (Tr(epsilon)^2 - Tr(epsilon^2))/2.

The paper then restricts its headline existence results to n>=5, odd q, and
rational functions with irreducible numerator and denominator.  Theorem 3.1
and the sieves in Section 4 are lower-bound existence results, not search
hardness results.  Section 5 explicitly says SageMath performed its significant
calculations.  Theorem 5.7 guarantees the primitive-normal-pair property for
q=7^k, n>=6 outside eleven possible cases, but neither it nor its proof outputs
an element.  A planted primitive-normal search family would also have many
valid witnesses and fails the structure-aware G4 test.  No Track-A claim is
therefore made.

Native Track-B family.  Set q=7,340,033=7*2^20+1 and let 3 be a primitive
element of F_q.  For each power of two 8<=n<=2^20, the executable binomial
irreducibility criterion proves Y^n-3 irreducible: every prime divisor of n
divides ord_q(3)=q-1, gcd(n,(q-1)/ord_q(3))=1, and q=1 mod 4.  Thus a root eta
defines the native extension F_{q^n}.  The instance gives invertible affine
maps T_i(z)=a_i*z+b_i and defines eta=T_{k-1}(...T_0(epsilon)...).

Generation is composition of identities.  If the chain is U*x+V, then the
monic minimal polynomial of epsilon is

  U^(-n) * ((U*x+V)^n - 3).

Its leading coefficients are c1=n*V/U and
c2=binom(n,2)*(V/U)^2 in F_q.  The planted answer is the corresponding sparse
three-term fragment.  Generation samples the affine pieces first and computes
these two formulas; it never invokes the dense reference expansion.

What makes the native question easy if stated carelessly.  Section 1 itself
says the requested subtrace is a displayed minimal-polynomial coefficient, so
handing the polynomial of epsilon directly would reduce the problem to a
lookup.  Here only the binomial polynomial of eta and a noncommutative chain of
coordinate changes are supplied.  A mechanical exact expansion produces all
n+1 coefficients; the intended route composes the chain before touching the
polynomial.  The standard dense algorithm is reported openly as the Track-B
reference algorithm.

Attacks.  Every generated chain is screened against (not solved by) the cheap
wrong routes measured in G6: treating translations as commutative, reversing
the composition order, using only the last map, selecting the largest
translation, and random polynomial fragments.  The affine pieces all come
from the same distribution.  Difficulty grows through polynomial degree and
chain length while the three-term answer stays fixed.

Canonicalization.  Inserting identity maps, refactoring a map into two maps,
and multiplying the final affine map by an n-th root of unity all preserve the
field element and its monic minimal polynomial.  The canonical key uses n and
the invariant ratio V/U, not the seed or the rendered text.  It is complete for
the chain-refactorings generated here; no claim is made for arbitrary finite-
field presentation isomorphism.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8

# Updated after the script-owned hardening and diagnostic runs.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n: object, chain_length: object,
                     coefficient_cap: object) -> tuple[int, int, int]:
    if not _is_int(n):
        raise ValueError("n must be an integer")
    n = int(n)
    if n < 8 or n > _MAX_DEGREE or n & (n - 1):
        raise ValueError("n must be a power of two in 8..1048576")
    if not _is_int(chain_length):
        raise ValueError("chain_length must be an integer")
    chain_length = int(chain_length)
    if not 1 <= chain_length <= 88:
        raise ValueError("chain_length must lie in 1..88")
    if coefficient_cap is None:
        coefficient_cap = _Q - 1
    if not _is_int(coefficient_cap):
        raise ValueError("coefficient_cap must be an integer")
    coefficient_cap = int(coefficient_cap)
    if not 1 <= coefficient_cap < _Q:
        raise ValueError("coefficient_cap must lie in 1..q-1")
    return n, chain_length, coefficient_cap


def _compose(chain: list[list[int]], q: int = _Q) -> tuple[int, int]:
    """Return U,V for maps applied in listed order: z <- a*z+b."""
    u, v = 1, 0
    for a, b in chain:
        u = (a * u) % q
        v = (a * v + b) % q
    return u, v


def _fragment(n: int, ratio: int, q: int = _Q) -> list[list[object]]:
    c1 = (n * ratio) % q
    c2 = ((n * (n - 1) // 2) % q) * ratio * ratio % q
    return [[1, [n]], [c1, [n - 1]], [c2, [n - 2]]]


def _answer_for_chain(n: int, chain: list[list[int]],
                      q: int = _Q) -> list[list[object]]:
    u, v = _compose(chain, q)
    ratio = v * pow(u, q - 2, q) % q
    return _fragment(n, ratio, q)


def _attack_ratios(chain: list[list[int]], q: int = _Q) -> dict[str, int]:
    product_a = 1
    sum_b = 0
    for a, b in chain:
        product_a = product_a * a % q
        sum_b = (sum_b + b) % q
    last_a, last_b = chain[-1]
    largest_a, largest_b = max(chain, key=lambda ab: min(ab[1], q - ab[1]))
    reverse_u, reverse_v = _compose(list(reversed(chain)), q)
    return {
        "commutative_product_sum": sum_b * pow(product_a, q - 2, q) % q,
        "ignore_scalings_sum_translations": sum_b,
        "last_map_only": last_b * pow(last_a, q - 2, q) % q,
        "largest_translation_outlier": (
            largest_b * pow(largest_a, q - 2, q) % q
        ),
        "reverse_composition_order": reverse_v * pow(reverse_u, q - 2, q) % q,
    }


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Compose affine maps and obtain the coefficient witness by identity."""
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    chain_length = params.pop("chain_length", 12)
    coefficient_cap = params.pop("coefficient_cap", None)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    n, chain_length, coefficient_cap = _validate_params(
        n, chain_length, coefficient_cap
    )
    rng = random.Random(seed)

    # Reject only degenerate presentations and accidental successes of the
    # declared cheap attacks.  This is construction-time screening, not search
    # for the answer: every surviving answer is still the same closed identity.
    for _ in range(10_000):
        chain: list[list[int]] = []
        for _j in range(chain_length):
            a = rng.randint(1, coefficient_cap)
            b = rng.randint(1, coefficient_cap)
            chain.append([a, b])
        u, v = _compose(chain)
        if not u or not v:
            continue
        ratio = v * pow(u, _Q - 2, _Q) % _Q
        answer = _fragment(n, ratio)
        c1 = int(answer[1][0])
        c2 = int(answer[2][0])
        if c1 == 0 or c2 == 0 or c1 == c2:
            continue
        if (coefficient_cap > 1
                and any(candidate == ratio
                        for candidate in _attack_ratios(chain).values())):
            continue
        break
    else:  # pragma: no cover - probability is negligible
        raise RuntimeError("could not construct a nondegenerate affine chain")

    return {
        "schema": "affine_subtrace_v1",
        "q": _Q,
        "degree": n,
        "radicand": _RADICAND,
        "chain": chain,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete standalone finite-field coefficient problem."""
    q = inst["q"]
    n = inst["degree"]
    lines = [
        "Leading minimal-polynomial terms after finite-field coordinate changes",
        "",
        f"All scalar arithmetic is in the prime field F_q with q={q}; write",
        f"field elements as their unique integer residues from 0 through {q - 1}.",
        f"Let n={n}.  The polynomial Y^{n}-{inst['radicand']} is irreducible over F_q,",
        f"and eta denotes its residue class in the extension F_q[Y]/(Y^{n}-{inst['radicand']}).",
        "",
        "Starting with z=epsilon, apply the following affine maps in the exact",
        "listed order.  A row `a b` means replace z by a*z+b in the extension.",
        "After the last row, the resulting z equals eta.",
        "",
        "AFFINE_MAPS (a b):",
    ]
    lines.extend(f"{a} {b}" for a, b in inst["chain"])
    lines.extend([
        "END_AFFINE_MAPS",
        "",
        "Let M(X) be the monic minimal polynomial of epsilon over F_q:",
        "",
        "  M(X) = X^n + c1*X^(n-1) + c2*X^(n-2) + lower-degree terms.",
        "",
        "Find its three displayed leading terms.  In the paper's notation,",
        "Tr(epsilon)=-c1 and STr(epsilon)=c2, where the subtrace is the sum",
        "of the products of every two distinct Frobenius conjugates.",
        "",
        "Return exactly three terms in descending degree as JSON.  Each term is",
        "[coefficient,[exponent]]; coefficients must be canonical residues in",
        "0..q-1, exponents are ordinary integers, order matters, and no term may",
        "be repeated.  Thus the required shape is",
        "[[1,[n]],[c1,[n-1]],[c2,[n-2]]].",
        "",
        "Give your final answer inside <answer></answer> tags in that exact JSON format.",
        f"Format-only example: <answer>[[1,[{n}]],[0,[{n-1}]],[0,[{n-2}]]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse a tagged JSON sparse-polynomial fragment; never raise."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def _check_answer_shape(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "certificate must be a JSON list"
    if not answer:
        return False, "empty certificate"
    if len(answer) < 3:
        return False, f"too few terms: expected 3, got {len(answer)}"
    if len(answer) > 3:
        return False, f"too many terms: expected 3, got {len(answer)}"
    expected_exponents = [inst["degree"], inst["degree"] - 1,
                          inst["degree"] - 2]
    for j, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term {j} must be [coefficient,[exponent]]"
        coefficient, monomial = term
        if not _is_int(coefficient):
            return False, f"coefficient at term {j} must be an integer"
        if not 0 <= coefficient < inst["q"]:
            return False, f"coefficient at term {j} lies outside F_q"
        if not isinstance(monomial, list) or len(monomial) != 1:
            return False, f"monomial at term {j} must contain one exponent"
        if not _is_int(monomial[0]):
            return False, f"exponent at term {j} must be an integer"
        if monomial[0] != expected_exponents[j]:
            return False, f"term {j} has the wrong exponent or order"
    if answer[0][0] != 1:
        return False, "leading coefficient must be one"
    return True, "ok"


def _valid_instance(inst: object) -> tuple[bool, str]:
    if not isinstance(inst, dict):
        return False, "instance must be a dictionary"
    if inst.get("schema") != "affine_subtrace_v1":
        return False, "unknown instance schema"
    if inst.get("q") != _Q or inst.get("radicand") != _RADICAND:
        return False, "unsupported field constants"
    n = inst.get("degree")
    if not _is_int(n) or n < 8 or n > _MAX_DEGREE or n & (n - 1):
        return False, "degree does not satisfy the binomial field criterion"
    chain = inst.get("chain")
    if not isinstance(chain, list) or not chain:
        return False, "affine chain is absent"
    for row in chain:
        if (not isinstance(row, list) or len(row) != 2
                or any(not _is_int(x) for x in row)):
            return False, "malformed affine map"
        if not 1 <= row[0] < _Q or not 0 <= row[1] < _Q:
            return False, "affine map coefficient outside F_q"
    # Executable witnesses for q prime, ord_q(3)=q-1, and the special binomial
    # irreducibility criterion used by the construction.
    if not _Q_IS_PRIME:
        return False, "field modulus is not prime"
    if pow(3, _Q - 1, _Q) != 1:
        return False, "field primality witness failed"
    if pow(3, (_Q - 1) // 2, _Q) == 1 or pow(3, (_Q - 1) // 7, _Q) == 1:
        return False, "radicand is not primitive in F_q"
    if _Q % 4 != 1 or (_Q - 1) % n:
        return False, "binomial irreducibility condition failed"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept any correct leading fragment; never inspect inst['answer']."""
    valid, reason = _valid_instance(inst)
    if not valid:
        return False, reason
    shaped, reason = _check_answer_shape(inst, answer)
    if not shaped:
        return False, reason
    expected = _answer_for_chain(inst["degree"], inst["chain"], inst["q"])
    if answer[1][0] != expected[1][0]:
        return False, "degree-(n-1) coefficient mismatch"
    if answer[2][0] != expected[2][0]:
        return False, "degree-(n-2) subtrace coefficient mismatch"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the exact shape and freely deducible binomial relation."""
    n, q = inst["degree"], inst["q"]
    c1 = rng.randrange(q)
    ratio = c1 * pow(n, q - 2, q) % q
    return _fragment(n, ratio, q)


def search_space(inst: dict) -> int | None:
    """One free F_q coefficient after enforcing the binomial relation."""
    return int(inst["q"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force only when the bounded language is small enough."""
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    n, q = inst["degree"], inst["q"]
    count = 0
    for c1 in range(q):
        ratio = c1 * pow(n, q - 2, q) % q
        count += int(verify(inst, _fragment(n, ratio, q))[0])
    return count


def canonical_key(inst: dict) -> str:
    """Key by degree and V/U, invariant under generated presentation changes."""
    valid, reason = _valid_instance(inst)
    if not valid:
        raise ValueError(reason)
    u, v = _compose(inst["chain"], inst["q"])
    ratio = v * pow(u, inst["q"] - 2, inst["q"]) % inst["q"]
    payload = json.dumps([inst["q"], inst["degree"], ratio], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow dense expansion work and then chain crowding, never the answer."""
    harder = dict(params)
    n = int(harder["n"])
    chain_length = int(harder.get("chain_length", 12))
    if n < _MAX_DEGREE:
        harder["n"] = min(_MAX_DEGREE, n * 2)
        harder["chain_length"] = min(72, chain_length + 8)
        harder.pop("coefficient_cap", None)
        return harder
    if chain_length < 80:
        harder["chain_length"] = min(80, chain_length + 8)
        harder.pop("coefficient_cap", None)
        return harder
    return "cap_bound"


def _dense_reference(inst: dict, materialize: bool = True
                     ) -> tuple[list[list[object]], int, int]:
    """Expand every coefficient of U^-n((UX+V)^n-3) in O(n)."""
    q, n = inst["q"], inst["degree"]
    u, v = _compose(inst["chain"], q)
    ratio = v * pow(u, q - 2, q) % q
    # Coefficient of X^(n-k) is C(n,k)*ratio^k.  Since n<q, modular
    # inverses 1..n exist and are generated together in linear time.
    inv = [0] * (n + 1) if materialize else None
    coeffs = [0] * (n + 1) if materialize else None
    if materialize:
        inv[1] = 1
        coeffs[0] = 1
    coefficient = 1
    first = second = 0
    operations = 3 * len(inst["chain"]) + 1
    for k in range(1, n + 1):
        if k == 1:
            inverse = 1
        else:
            inverse = (q - (q // k) * (
                inv[q % k] if materialize else pow(q % k, q - 2, q)
            ) % q) % q
        # The non-materialized branch is used only for operation estimates.
        coefficient = coefficient * ((n - k + 1) % q) % q
        coefficient = coefficient * inverse % q
        coefficient = coefficient * ratio % q
        if materialize:
            inv[k] = inverse
            coeffs[k] = coefficient
        if k == 1:
            first = coefficient
        elif k == 2:
            second = coefficient
        operations += 5
    # The constant term additionally contains -3/U^n, irrelevant to the
    # returned leading fragment but computed to ensure a genuine full expansion.
    if materialize:
        coeffs[n] = (coeffs[n] - _RADICAND * pow(u, q - 1 - (n % (q - 1)), q)) % q
        operations += 3
    answer = [[1, [n]], [first, [n - 1]], [second, [n - 2]]]
    return answer, operations, n + 1


def _estimated_dense_operations(inst: dict) -> int:
    return 3 * len(inst["chain"]) + 1 + 5 * inst["degree"] + 3


def _attack_answers(inst: dict, seed: int) -> dict[str, list[object]]:
    n = inst["degree"]
    guesses = {
        name: [_fragment(n, ratio, inst["q"])]
        for name, ratio in _attack_ratios(inst["chain"], inst["q"]).items()
    }
    rng = random.Random(0x240511463 ^ seed)
    guesses["random_restart_256"] = [random_candidate(inst, rng) for _ in range(256)]
    return guesses


def _refactor_and_relabel(inst: dict, rng: random.Random) -> dict:
    """Apply composed chain refactoring and an n-th-root field relabelling."""
    transformed = copy.deepcopy(inst)
    chain = transformed["chain"]
    index = rng.randrange(len(chain))
    a, b = chain[index]
    s = rng.randrange(1, _Q)
    t = rng.randrange(_Q)
    c = a * pow(s, _Q - 2, _Q) % _Q
    d = (b - c * t) % _Q
    chain[index:index + 1] = [[s, t], [c, d]]
    chain.insert(rng.randrange(len(chain) + 1), [1, 0])

    # Multiply the final aggregate affine map by zeta with zeta^n=1.  Scaling
    # the final row scales U,V together and leaves (U X+V)^n-3 unchanged.
    root_index = rng.randrange(inst["degree"])
    zeta = pow(3, ((_Q - 1) // inst["degree"]) * root_index, _Q)
    chain[-1][0] = chain[-1][0] * zeta % _Q
    chain[-1][1] = chain[-1][1] * zeta % _Q
    return transformed


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _intended_route_operations(inst: dict) -> int:
    # Per affine map: two multiplications and one addition.  The modular inverse
    # of U costs at most 24 Euclidean divisions at this 23-bit prime; the two
    # coefficient formulas use at most twelve further exact operations.
    return 3 * len(inst["chain"]) + 24 + 12


def selftest() -> dict:
    """Run G1--G9 and return a JSON-native evidence report."""
    report: dict[str, Any] = {
        "paper": "arXiv:2405.11463",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every named rung, several seeds, exact JSON round trips.
    verified = json_roundtrips = total = 0
    for _preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            verified += int(verify(inst, inst["answer"])[0])
            json_roundtrips += int(
                json.loads(json.dumps(inst["answer"])) == inst["answer"]
            )
            total += 1
    report["G1_planted_verifies"] = {
        "pass": verified == total and json_roundtrips == total,
        "verified": verified,
        "attempts": total,
        "json_roundtrips": json_roundtrips,
    }

    ship = make_instance(seed=20260517, **DIFFICULTY[SHIPPING_DIFFICULTY])
    good = copy.deepcopy(ship["answer"])

    # G2: required corruption shapes with distinct rejection paths.
    dropped = copy.deepcopy(good)
    dropped.pop()
    swapped = copy.deepcopy(good)
    swapped[1], swapped[2] = swapped[2], swapped[1]
    duplicated = copy.deepcopy(good)
    duplicated.append(copy.deepcopy(duplicated[-1]))
    empty: object = []
    out_of_range = copy.deepcopy(good)
    out_of_range[1][0] = ship["q"]
    corruptions = [dropped, swapped, duplicated, empty, out_of_range]
    outcomes = [verify(ship, value) for value in corruptions]
    reasons = [reason for ok, reason in outcomes if not ok]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in outcomes) and len(set(reasons)) == 5,
        "rejected": sum(not ok for ok, _ in outcomes),
        "attempts": len(corruptions),
        "distinct_reasons": len(set(reasons)),
        "reasons": reasons,
    }

    # G3: prose, fences, case, and whitespace.
    blob = json.dumps(good, separators=(",", ":"))
    samples = [
        f"I composed the changes first.\n<answer>{blob}</answer>\nDone.",
        f"Result:\n<answer>```json\n{blob}\n```</answer>",
        f"prose <ANSWER>  {blob}  </ANSWER> trailing prose",
    ]
    parsed_ok = sum(parse_answer(sample) == good for sample in samples)
    report["G3_round_trip"] = {
        "pass": parsed_ok == len(samples) and parse_answer("garbage") is None,
        "model_style_roundtrips": parsed_ok,
        "attempts": len(samples),
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: the exact shape, monicity, exponents, and coefficient ranges are all
    # pre-enforced, including the relation between c1 and c2.  Only one field
    # coefficient remains genuinely unknown without composing the chain.
    rng = random.Random(0x240511463)
    hits = 0
    for _ in range(_G4_SAMPLES):
        hits += int(verify(ship, random_candidate(ship, rng))[0])
    exact_probability = 1.0 / int(search_space(ship))
    report["G4_guess_resistance"] = {
        "pass": hits / _G4_SAMPLES < 1e-6 and exact_probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": hits / _G4_SAMPLES,
        "exact_uniform_probability": exact_probability,
        "structure_aware_space": search_space(ship),
        "prior": "monic, correct exponents, binomial relation, one uniform c1 in F_q",
    }

    # G5: shipping density plus an actual full dense expansion.
    start = time.perf_counter()
    reference, reference_ops, reference_coefficients = _dense_reference(ship)
    reference_wall = time.perf_counter() - start
    reference_ok = verify(ship, reference)[0]
    report["G5_density_and_baseline"] = {
        "pass": (hits / _G4_SAMPLES < 1e-6 and reference_ok
                 and reference_ops > _intended_route_operations(ship)),
        "shipping_valid_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_observed_fraction": hits / _G4_SAMPLES,
        "shipping_exact_solution_count": 1,
        "shipping_exact_fraction": exact_probability,
        "reference_wall_clock_sec": round(reference_wall, 6),
        "reference_modular_operations": reference_ops,
        "reference_coefficients_materialized": reference_coefficients,
        "reference_iterations": ship["degree"],
    }

    # G6 Track B: cheap/no-tool attacks fail; the successful dense algorithm is
    # reported separately and is expected to solve every instance.
    attack_counts: dict[str, dict[str, int]] = {}
    ref_successes = 0
    ref_ops: list[int] = []
    ref_times: list[float] = []
    for offset in range(_ATTACK_SEEDS):
        inst = make_instance(seed=3100 + offset,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidates in _attack_answers(inst, 3100 + offset).items():
            entry = attack_counts.setdefault(name, {"successes": 0, "attempts": 0})
            solved = any(verify(inst, candidate)[0] for candidate in candidates)
            entry["successes"] += int(solved)
            entry["attempts"] += 1
        t0 = time.perf_counter()
        candidate, operations, _count = _dense_reference(inst)
        elapsed = time.perf_counter() - t0
        ref_successes += int(verify(inst, candidate)[0])
        ref_ops.append(operations)
        ref_times.append(elapsed)
    all_failed = len(attack_counts) >= 4 and all(
        data["successes"] == 0 and data["attempts"] >= _ATTACK_SEEDS
        for data in attack_counts.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == _ATTACK_SEEDS,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "dense binomial coefficient expansion over F_q",
            "complexity": "O(n+k) exact modular operations and O(n) storage",
            "wall_clock_sec": round(sum(ref_times) / len(ref_times), 6),
            "operations": round(sum(ref_ops) / len(ref_ops)),
            "coefficients": ship["degree"] + 1,
            "solves": f"{ref_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    # G7 doubles degree only; certificate size is fixed.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=8888, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    shipping_estimate = _estimated_dense_operations(ship)
    doubled_estimate = _estimated_dense_operations(doubled)
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled_estimate > shipping_estimate
                 and _answer_atoms(doubled["answer"]) == _answer_atoms(good)),
        "shipping_degree": ship["degree"],
        "doubled_degree": doubled["degree"],
        "shipping_reference_operations": shipping_estimate,
        "doubled_reference_operations": doubled_estimate,
        "shipping_answer_elements": _answer_atoms(good),
        "doubled_answer_elements": _answer_atoms(doubled["answer"]),
    }

    # G8 uses composed real presentation symmetries and carried witnesses.
    invariant = carried_ok = 0
    keys: list[str] = []
    for seed in range(20):
        inst = make_instance(n=256, chain_length=8, seed=7000 + seed)
        key = canonical_key(inst)
        transformed = _refactor_and_relabel(inst, random.Random(9000 + seed))
        invariant += int(canonical_key(transformed) == key)
        carried_ok += int(verify(transformed, inst["answer"])[0])
        keys.append(key)
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried_ok == 20 and len(set(keys)) == 20,
        "composed_refactoring_and_root_scaling_invariance": invariant,
        "invariance_attempts": 20,
        "carried_witnesses_verified": carried_ok,
        "carried_attempts": 20,
        "unrelated_distinct_keys": len(set(keys)),
        "unrelated_attempts": 20,
    }

    # G9(a,b) are recorded diagnostics; only answer/effort caps gate.
    answer_blob = json.dumps(good, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(good)
    intended_ops = _intended_route_operations(ship)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and intended_ops <= 300)
    bare = _ORACLE_EVIDENCE["bare"]
    hinted = _ORACLE_EVIDENCE["hinted"]
    placebo = _ORACLE_EVIDENCE["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {"bare": bare, "hinted": hinted, "placebo": placebo},
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
