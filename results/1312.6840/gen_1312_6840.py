"""Verified false-twin certificates for arXiv:1312.6840.

The graph is a path with one internal vertex replaced by two false twins.  Its
vertex labels and duplicated path coordinate are hidden by bijective power maps
over a prime field.  The twin pair is sampled first, so generation never solves
the instance it emits.  Corollary 2.3 then certifies that the largest feasible
metric multiplicity is exactly two.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "simple connected graph given by an exact modular adjacency rule",
        "false-twin vertex pair",
    ],
    "verification_operations": [
        "exact modular change of variables",
        "integer base-coordinate comparison",
        "false-twin neighborhood identity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Invert the power permutations over the prime field to expose the one "
        "base-path coordinate represented by two graph vertices; a literal "
        "forward scan instead examines hundreds of thousands of coordinates."
    ),
    "hardness_basis": (
        "Track B: forward preimage enumeration, the domain-standard collision "
        "scan for the displayed succinct graph, costs O(n*rounds*log n) and at "
        "the shipping seed took about 0.52 s, 911574 coordinates, and 28306454 "
        "modular operations; reversing four prime-field power permutations, four "
        "affine permutations, and the relabelling takes 152 exact operations."
    ),
    "max_answer_tokens": 5,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON array [u,v] with 0 <= u < v < n: an unordered pair of "
        "distinct public graph vertices.  No member of the hidden twin pair is "
        "given for free by the statement."
    ),
    "bounds": {
        "array_length": 2,
        "index_lower_inclusive": 0,
        "index_upper_exclusive": "inst['n']",
        "distinct": True,
        "ordering": "strictly increasing",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 13, "rounds": 1},
    "easy": {"n": 1_000_003, "rounds": 4},
    "medium": {"n": 2_000_003, "rounds": 4},
    "hard": {"n": 3_000_017, "rounds": 4},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The power and affine update chains are bijective changes of variables "
    "hiding a single repeated base-path coordinate."
)
PLACEBO_HINT: str = (
    "The indexed quantities require consistent arithmetic bookkeeping, and each "
    "final vertex label must follow the stated exact output convention carefully."
)

# Populated only from completed, isolated harden.py runs. API failures never
# count as oracle failures.
G9_ORACLE_RESULTS: dict = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_api_quota",
}

NOTES: str = r"""
Definition and certificate. Section 1 defines a k-metric generator by requiring
every pair x,y to have at least k selected vertices at unequal distances from
x and y. Theorem 2.2 identifies the largest feasible k as
min_{x!=y}|D_G(x,y)|. Corollary 2.3 specializes this at k=2: a connected graph
is 2-metric dimensional exactly when it has twin vertices. This module asks for
the concrete twin pair that certifies that case, not for an unsupported proof.

What produces the certificate. A standard exact method evaluates the displayed
bijective prime-field update chain on successive base coordinates until its
target is hit, then checks the repeated neighborhood; this is
O(n*rounds*log n), and the planted coordinate is restricted to the middle third
so the scan performs tens of millions of modular multiplications at shipping
size. That polynomial algorithm makes Track A inappropriate. Track B uses the
    compression gap: use the validated inverse parameters to reverse the power
    and affine chains, and apply the visible vertex relabelling to the recovered
    exceptional index and duplicated path coordinate.

Inverse generation. The exceptional canonical index e and duplicated internal
path coordinate f are sampled first. Random exponents coprime to p-1 make every
map y -> y^e+b a permutation of the prime field; affine units similarly
permute the fold coordinates. Those rounds are applied forward to reveal only
two targets. A final affine permutation gives the twins their public labels.
Thus the answer exists before the instance is assembled and is never searched.

Exact graph. After undoing the public affine vertex labelling and recovering
the exceptional index e, every nonexceptional index is ranked in 0..n-2; those
ranks denote a path. The exceptional index denotes a second copy of rank f.
Two public vertices are adjacent exactly when their base-path coordinates
differ by one. The two copies of f are nonadjacent and have identical open
neighborhoods, so they are false twins. Every pair in any connected graph is
distinguished by its own two vertices, while this pair is distinguished by no
others; hence the maximum k is exactly two.

Easy regimes and attacks. Corollary 2.3 itself gives an efficient twin scan, so
the family is explicitly Track B. Degree endpoints, label order, random pairs,
treating the target as the preimage, undoing only the final translation, and
undoing only the last full update all fail on the audited seeds. The reference
forward scan succeeds, as Track B requires.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _random_unit(rng: random.Random, modulus: int) -> int:
    while True:
        value = rng.randrange(1, modulus)
        if math.gcd(value, modulus) == 1:
            return value


def _forward_chain(modulus: int, updates: list[list[int]], value: int) -> int:
    for exponent, shift in updates:
        value = (pow(value, exponent, modulus) + shift) % modulus
    return value


def _reverse_chain(modulus: int, updates: list[list[int]], target: int) -> int:
    """Invert y <- y**e+b over the prime field, exactly."""
    value = target
    for exponent, shift in reversed(updates):
        inverse_exponent = pow(exponent, -1, modulus - 1)
        value = pow((value - shift) % modulus, inverse_exponent, modulus)
    return value


def _forward_affine_chain(
    modulus: int, updates: list[list[int]], value: int
) -> int:
    for multiplier, shift in updates:
        value = (multiplier * value + shift) % modulus
    return value


def _reverse_affine_chain(
    modulus: int, updates: list[list[int]], target: int
) -> int:
    value = target
    for multiplier, shift in reversed(updates):
        value = pow(multiplier, -1, modulus) * (value - shift) % modulus
    return value


def _euclid_divisions(a: int, b: int) -> int:
    divisions = 0
    while a:
        a, b = b % a, a
        divisions += 1
    return divisions


def _compact_route_operations(inst: dict) -> int:
    # Inverses are part of the exact update data. Count every square/multiply in
    # binary modular powering, subtraction/reduction, affine reversal, ranking,
    # public relabelling, and final ordering.
    total = 9
    for inverse_exponent in reversed(inst["special_inverse_exponents"]):
        power_ops = inverse_exponent.bit_length() + inverse_exponent.bit_count()
        total += power_ops + 2
    total += 3 * len(inst["fold_updates"])
    return total


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for the 64-bit sizes supported here."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    power = 0
    while d % 2 == 0:
        d //= 2
        power += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        witness = pow(base, d, value)
        if witness in (1, value - 1):
            continue
        for _ in range(power - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def _next_prime(lower: int) -> int:
    prime = max(13, lower)
    if prime % 2 == 0:
        prime += 1
    while not _is_prime(prime):
        prime += 2
    return prime


def _random_exponent(rng: random.Random, modulus: int) -> int:
    # Small forward exponents keep the measured reference scan practical.  Their
    # inverses modulo the large number modulus-1 remain large, so reversing the
    # permutation still requires full modular exponentiation.
    choices = [
        exponent
        for exponent in range(3, min(256, modulus - 1), 2)
        if math.gcd(exponent, modulus - 1) == 1
    ]
    if not choices:
        raise ValueError("prime field is too small for a power permutation")
    return rng.choice(choices)


def _public_label(inst: dict, canonical: int) -> int:
    return (
        inst["label_multiplier"] * canonical + inst["label_shift"]
    ) % inst["n"]


def _validate_instance(inst: dict) -> tuple[tuple[int, int] | None, str]:
    if not isinstance(inst, dict):
        return None, "instance is not a dictionary"
    n = inst.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 13:
        return None, "instance n must be an integer at least 13"
    if not _is_prime(n):
        return None, "instance n must be prime"
    if inst.get("k") != 2:
        return None, "instance k must equal 2"
    multiplier = inst.get("label_multiplier")
    shift = inst.get("label_shift")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or not 1 <= multiplier < n
        or math.gcd(multiplier, n) != 1
    ):
        return None, "instance label multiplier is not a unit modulo n"
    if isinstance(shift, bool) or not isinstance(shift, int) or not 0 <= shift < n:
        return None, "instance label shift is out of range"
    special_updates = inst.get("special_updates")
    if not isinstance(special_updates, list) or not special_updates:
        return None, "instance special update chain is empty or malformed"
    for index, update in enumerate(special_updates):
        if (
            not isinstance(update, list)
            or len(update) != 2
            or isinstance(update[0], bool)
            or not isinstance(update[0], int)
            or not 1 < update[0] < n - 1
            or math.gcd(update[0], n - 1) != 1
            or isinstance(update[1], bool)
            or not isinstance(update[1], int)
            or not 0 <= update[1] < n
        ):
            return None, f"instance special update {index} is malformed"
    special_target = inst.get("special_target")
    if (
        isinstance(special_target, bool)
        or not isinstance(special_target, int)
        or not 0 <= special_target < n
    ):
        return None, "instance special target is out of range"
    inverse_exponents = inst.get("special_inverse_exponents")
    if (
        not isinstance(inverse_exponents, list)
        or len(inverse_exponents) != len(special_updates)
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value < n - 1
            or exponent * value % (n - 1) != 1
            for (exponent, _), value in zip(special_updates, inverse_exponents)
        )
    ):
        return None, "instance inverse exponent list is malformed"
    special = special_target
    for (_, shift), inverse_exponent in zip(
        reversed(special_updates), reversed(inverse_exponents)
    ):
        special = pow((special - shift) % n, inverse_exponent, n)
    if not 1 <= special <= n - 2:
        return None, "instance exceptional canonical index is out of range"
    if _forward_chain(n, special_updates, special) != special_target:
        return None, "instance special update chain does not invert exactly"

    modulus = n - 1
    fold_updates = inst.get("fold_updates")
    if not isinstance(fold_updates, list) or not fold_updates:
        return None, "instance fold update chain is empty or malformed"
    for index, update in enumerate(fold_updates):
        if (
            not isinstance(update, list)
            or len(update) != 2
            or isinstance(update[0], bool)
            or not isinstance(update[0], int)
            or not 1 <= update[0] < modulus
            or math.gcd(update[0], modulus) != 1
            or isinstance(update[1], bool)
            or not isinstance(update[1], int)
            or not 0 <= update[1] < modulus
        ):
            return None, f"instance fold update {index} is malformed"
    fold_target = inst.get("fold_target")
    if (
        isinstance(fold_target, bool)
        or not isinstance(fold_target, int)
        or not 0 <= fold_target < modulus
    ):
        return None, "instance fold target is out of range"
    inverse_multipliers = inst.get("fold_inverse_multipliers")
    if (
        not isinstance(inverse_multipliers, list)
        or len(inverse_multipliers) != len(fold_updates)
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value < modulus
            or multiplier * value % modulus != 1
            for (multiplier, _), value in zip(fold_updates, inverse_multipliers)
        )
    ):
        return None, "instance inverse multiplier list is malformed"
    fold = fold_target
    for (_, shift), inverse_multiplier in zip(
        reversed(fold_updates), reversed(inverse_multipliers)
    ):
        fold = inverse_multiplier * (fold - shift) % modulus
    if not 2 <= fold <= modulus - 3:
        return None, "instance repeated coordinate is not internal to the base path"
    if _forward_affine_chain(modulus, fold_updates, fold) != fold_target:
        return None, "instance fold update chain does not invert exactly"
    return (special, fold), "ok"


def _build_from_fold(
    n: int,
    special: int,
    fold: int,
    label_multiplier: int,
    label_shift: int,
    special_updates: list[list[int]],
    fold_updates: list[list[int]],
) -> dict:
    modulus = n - 1
    inst = {
        "family": "modularly labelled one-vertex blow-up of a path",
        "n": n,
        "k": 2,
        "label_multiplier": label_multiplier,
        "label_shift": label_shift,
        "special_updates": special_updates,
        "special_inverse_exponents": [
            pow(exponent, -1, n - 1) for exponent, _ in special_updates
        ],
        "special_target": _forward_chain(n, special_updates, special),
        "fold_updates": fold_updates,
        "fold_inverse_multipliers": [
            pow(multiplier, -1, modulus) for multiplier, _ in fold_updates
        ],
        "fold_target": _forward_affine_chain(modulus, fold_updates, fold),
    }
    ordinary_copy = fold if fold < special else fold + 1
    inst["answer"] = sorted(
        [_public_label(inst, ordinary_copy), _public_label(inst, special)]
    )
    return inst


def make_instance(n: int, seed: int = 0, rounds: int = 4, **params) -> dict:
    """Inverse-generate a succinct connected graph and its false-twin pair."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("rounds", rounds), ("seed", seed)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if n < 13 or not _is_prime(n):
        raise ValueError("n must be a prime integer at least 13")
    if not 1 <= rounds <= 60:
        raise ValueError("rounds must lie in 1..60")
    rng = random.Random(seed)
    modulus = n - 1

    # G: sample both certificate coordinates before producing their obfuscations.
    special = rng.randrange(max(1, n // 3), min(n - 1, 2 * n // 3))
    lower = max(2, modulus // 3)
    upper = min(modulus - 2, 2 * modulus // 3)
    fold = rng.randrange(lower, upper)
    special_updates = [
        [_random_exponent(rng, n), rng.randrange(n)]
        for _ in range(rounds)
    ]
    fold_updates = [
        [_random_unit(rng, modulus), rng.randrange(modulus)]
        for _ in range(rounds)
    ]
    inst = _build_from_fold(
        n,
        special,
        fold,
        _random_unit(rng, n),
        rng.randrange(n),
        special_updates,
        fold_updates,
    )
    ok, reason = verify(inst, inst["answer"])
    if not ok:
        raise AssertionError("construction proof failed: " + reason)
    return inst


def render(inst: dict) -> str:
    special_updates = "\n".join(
        f"  {index + 1}: exponent={exponent}, inverse_exponent={inverse}, "
        f"shift={shift}"
        for index, ((exponent, shift), inverse) in enumerate(zip(
            inst["special_updates"], inst["special_inverse_exponents"]
        ))
    )
    fold_updates = "\n".join(
        f"  {index + 1}: multiplier={multiplier}, inverse_multiplier={inverse}, "
        f"shift={shift}"
        for index, ((multiplier, shift), inverse) in enumerate(zip(
            inst["fold_updates"], inst["fold_inverse_multipliers"]
        ))
    )
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT
    return f"""False-twin certificate for the maximum metric multiplicity

The graph below is simple, undirected, and connected. Its vertices are the
integers 0 through {inst['n'] - 1}. For vertices x,z, graph distance d(x,z) is
the number of edges in a shortest path. A vertex z distinguishes distinct
vertices x,y when d(x,z) != d(y,z). The graph's maximum metric multiplicity is
the largest integer k such that every pair can be distinguished by at least k
vertices.

Find two vertices u<v that are false twins: they are not adjacent and have
identical open neighborhoods (the same neighbors). Such a pair is distinguished
only by u and v themselves and therefore certifies that this graph's maximum
metric multiplicity is k=2. Your answer must contain exactly that vertex pair.

The graph is specified exactly by the following rules; no edge list is omitted.
All remainders are the unique integers in the range starting at 0.

Let n={inst['n']} (a prime) and m=n-1={inst['n'] - 1}.
Let A={inst['label_multiplier']} and B={inst['label_shift']}.
For a public vertex label v, let
  x(v) = A^(-1) * (v-B) mod n,
where A^(-1) is the multiplicative inverse of A modulo n.

For any input q in 0..n-1, start y=q and apply the following special-index
updates in order; each replaces y by (y^exponent mod n + shift) mod n.
Every exponent is coprime to n-1, so every update is bijective; its displayed
inverse_exponent satisfies exponent*inverse_exponent = 1 mod (n-1):
{special_updates}
There is a unique e in 0..n-1 whose final y equals
special_target={inst['special_target']}.

For any input q in 0..m-1, start z=q and apply the following fold-coordinate
updates in order; each replaces z by (multiplier*z + shift) mod m.
Every multiplier is coprime to m, so every update is bijective; its displayed
inverse_multiplier satisfies multiplier*inverse_multiplier = 1 mod m:
{fold_updates}
There is a unique f in 0..m-1 whose final z equals
fold_target={inst['fold_target']}.

Define the base-path coordinate of v by
  base(v) = f          if x(v)=e,
  base(v) = x(v)       if x(v)<e,
  base(v) = x(v)-1     if x(v)>e.
Distinct vertices u,v are adjacent exactly when |base(u)-base(v)|=1.{hint}

Give your final answer inside <answer></answer> tags as one JSON array [u,v]
of exactly two distinct 0-based integers with 0 <= u < v < {inst['n']}.
Example format only: <answer>[0, 1]</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept every false-twin pair in the specified graph; never read answer."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != 2:
        return False, f"wrong number of vertices: expected 2, got {len(answer)}"
    n = inst.get("n") if isinstance(inst, dict) else None
    for position, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {position} is not an integer"
        if not isinstance(n, int) or not 0 <= value < n:
            high = n - 1 if isinstance(n, int) else "?"
            return False, f"vertex {value} is out of range 0..{high}"
    if answer[0] == answer[1]:
        return False, "the same vertex was supplied twice"
    if answer[0] > answer[1]:
        return False, "vertices are not in strictly increasing order"
    coordinates, reason = _validate_instance(inst)
    if coordinates is None:
        return False, reason
    special, fold = coordinates
    inverse = pow(inst["label_multiplier"], -1, n)
    canonical = [
        (inverse * (value - inst["label_shift"])) % n for value in answer
    ]
    base = [
        fold if value == special else value if value < special else value - 1
        for value in canonical
    ]
    if base[0] != base[1]:
        return False, "the two vertices do not have identical base-path coordinates"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return sorted(rng.sample(range(inst["n"]), 2))


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], 2)


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 2_000_000:
        return None
    return sum(
        verify(inst, [left, right])[0]
        for left in range(inst["n"])
        for right in range(left + 1, inst["n"])
    )


def canonical_key(inst: dict) -> str:
    """Exact isomorphism key for a path with one internal vertex doubled."""
    coordinates, reason = _validate_instance(inst)
    if coordinates is None:
        raise ValueError(reason)
    _, fold = coordinates
    reflected = inst["n"] - 2 - fold
    payload = [inst["n"], inst["k"], min(fold, reflected)]
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    out = {key: value for key, value in params.items() if key != "_preset"}
    if "n" not in out or "rounds" not in out:
        return None
    # Grow only the virtual graph; the answer and compact route stay fixed.
    proposed = _next_prime(2 * int(out["n"]))
    # Two maximal labels serialize as "[digits,digits]".
    if 2 * len(str(proposed - 1)) + 3 > 2_000:
        return "cap_bound"
    out["n"] = proposed
    return out


def _reference_forward_scan(inst: dict) -> tuple[list[int], int, int]:
    """Mechanical preimage enumeration, expected to solve on Track B."""
    tested = 0
    special = None
    for candidate in range(inst["n"]):
        tested += 1
        if (
            _forward_chain(inst["n"], inst["special_updates"], candidate)
            == inst["special_target"]
        ):
            special = candidate
            break
    if special is None:
        raise AssertionError("bijective special chain had no preimage")
    special_tested = tested

    modulus = inst["n"] - 1
    fold = None
    for candidate in range(modulus):
        tested += 1
        if (
            _forward_affine_chain(modulus, inst["fold_updates"], candidate)
            == inst["fold_target"]
        ):
            fold = candidate
            break
    if fold is None:
        raise AssertionError("bijective fold chain had no preimage")
    ordinary_copy = fold if fold < special else fold + 1
    answer = sorted(
        [_public_label(inst, ordinary_copy), _public_label(inst, special)]
    )
    special_cost = sum(
        exponent.bit_length() + exponent.bit_count() + 2
        for exponent, _ in inst["special_updates"]
    )
    fold_cost = 3 * len(inst["fold_updates"])
    operations = special_tested * special_cost
    operations += (tested - special_tested) * fold_cost + 6
    return answer, tested, operations


def _candidate_from_guesses(inst: dict, special: int, fold: int) -> list[int]:
    special %= inst["n"]
    fold %= inst["n"] - 1
    ordinary_copy = fold if fold < special else fold + 1
    return sorted(
        [_public_label(inst, ordinary_copy), _public_label(inst, special)]
    )


def _attack_degree_endpoints(inst: dict) -> list[int]:
    return sorted([_public_label(inst, 0), _public_label(inst, inst["n"] - 1)])


def _attack_smallest_labels(inst: dict) -> list[int]:
    return [0, 1]


def _attack_random_pairs(inst: dict, seed: int, restarts: int = 256) -> list[int] | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_target_as_preimage(inst: dict) -> list[int]:
    return _candidate_from_guesses(
        inst, inst["special_target"], inst["fold_target"]
    )


def _attack_undo_last_translation(inst: dict) -> list[int]:
    _, special_shift = inst["special_updates"][-1]
    _, fold_shift = inst["fold_updates"][-1]
    return _candidate_from_guesses(
        inst,
        (inst["special_target"] - special_shift) % inst["n"],
        (inst["fold_target"] - fold_shift) % (inst["n"] - 1),
    )


def _attack_undo_last_update(inst: dict) -> list[int]:
    exponent, shift = inst["special_updates"][-1]
    residue = (inst["special_target"] - shift) % inst["n"]
    special = pow(residue, inst["special_inverse_exponents"][-1], inst["n"])
    multiplier, shift = inst["fold_updates"][-1]
    fold = (
        inst["fold_inverse_multipliers"][-1]
        * (inst["fold_target"] - shift)
        % (inst["n"] - 1)
    )
    return _candidate_from_guesses(inst, special, fold)


def _reencode(inst: dict, rng: random.Random, reflect: bool) -> dict:
    coordinates, reason = _validate_instance(inst)
    if coordinates is None:
        raise ValueError(reason)
    _, fold = coordinates
    n = inst["n"]
    if reflect:
        fold = n - 2 - fold
    special = rng.randrange(max(1, n // 3), min(n - 1, 2 * n // 3))
    special_updates = [
        [_random_exponent(rng, n), rng.randrange(n)]
        for _ in range(len(inst["special_updates"]))
    ]
    fold_updates = [
        [_random_unit(rng, n - 1), rng.randrange(n - 1)]
        for _ in range(len(inst["fold_updates"]))
    ]
    return _build_from_fold(
        n,
        special,
        fold,
        _random_unit(rng, n),
        rng.randrange(n),
        special_updates,
        fold_updates,
    )


def _answer_size(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(child) for child in value.values())
        if isinstance(value, list):
            return sum(atoms(child) for child in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def selftest() -> dict:
    report: dict = {
        "paper": "1312.6840",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    verified = attempted = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            attempted += 1
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            verified += 1
    report["G1_planted_verifies"] = {
        "pass": verified == attempted,
        "verified": verified,
        "attempted": attempted,
    }

    base = make_instance(seed=12_345, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = base["answer"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": [answer[1], answer[0]],
        "duplicate": [answer[0], answer[0]],
        "empty": [],
        "out_of_range": [answer[0], base["n"]],
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(base, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = reason
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError("G2 reasons are not distinct: " + repr(reasons))
    report["G2_rejects_corruption"] = {
        "pass": True,
        "rejected": len(reasons),
        "attempted": len(reasons),
        "reasons": reasons,
    }

    response = (
        "The repeated coordinate gives the pair below.\n```json\n<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\nBoth open neighborhoods coincide."
    )
    parsed = parse_answer(response)
    if parsed != answer:
        raise AssertionError("G3 realistic response did not round-trip")
    report["G3_round_trip"] = {
        "pass": True,
        "entries_recovered": len(answer),
        "prose": True,
        "markdown_fence": True,
    }

    shipping = make_instance(
        seed=314_159, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )
    samples = 200_000
    guess_rng = random.Random(271_828)
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            hits += 1
    probability = hits / samples
    if probability >= 1e-6:
        raise AssertionError(f"G4 guess probability {hits}/{samples}")
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": hits,
        "samples": samples,
        "measured_probability": probability,
        "candidate_space": str(search_space(shipping)),
        "exact_valid_answers": 1,
        "exact_probability": 1 / search_space(shipping),
        "prior": (
            "a uniformly sampled unordered pair of distinct public vertices, "
            "with both hidden preimages unknown"
        ),
    }

    demo_counts = []
    for seed in (5, 6, 7):
        demo = make_instance(seed=seed, **DIFFICULTY["demo"])
        count = enumerate_all(demo)
        if count != 1:
            raise AssertionError(f"demo seed {seed} has {count} valid pairs")
        demo_counts.append(
            {
                "n": demo["n"],
                "seed": seed,
                "valid_answers": count,
                "candidate_space": search_space(demo),
                "solution_fraction": count / search_space(demo),
            }
        )
    start = time.perf_counter()
    reference, scanned, operations = _reference_forward_scan(shipping)
    reference_seconds = time.perf_counter() - start
    reference_ok = verify(shipping, reference)[0]
    if not reference_ok:
        raise AssertionError("G5 reference scan did not return a witness")
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_n": shipping["n"],
        "shipping_seed": 314_159,
        "density_method": "sampled exact predicate on random_candidate",
        "density_hits": hits,
        "density_samples": samples,
        "observed_solution_fraction": probability,
        "exact_solution_fraction": 1 / search_space(shipping),
        "enumerate_all_shipping": enumerate_all(shipping),
        "baseline_attack": "forward_power_map_preimage_enumeration",
        "baseline_solved": reference_ok,
        "baseline_wall_seconds": round(reference_seconds, 6),
        "baseline_coordinates_scanned": scanned,
        "baseline_modular_operations": operations,
        "additional_demo_exact_counts": demo_counts,
    }

    attack_names = (
        "degree_one_endpoints",
        "smallest_public_labels",
        "random_pair_256_restarts",
        "target_equals_preimage_ansatz",
        "undo_only_final_translation_ansatz",
        "undo_only_last_update_ansatz",
    )
    successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_measurements = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            attack_names[0]: _attack_degree_endpoints(inst),
            attack_names[1]: _attack_smallest_labels(inst),
            attack_names[2]: _attack_random_pairs(inst, 90_000 + seed, 256),
            attack_names[3]: _attack_target_as_preimage(inst),
            attack_names[4]: _attack_undo_last_translation(inst),
            attack_names[5]: _attack_undo_last_update(inst),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                successes[name] += 1
        start = time.perf_counter()
        found, tested, op_count = _reference_forward_scan(inst)
        elapsed = time.perf_counter() - start
        if verify(inst, found)[0]:
            reference_successes += 1
        reference_measurements.append(
            {
                "seed": seed,
                "wall_seconds": round(elapsed, 6),
                "coordinates_scanned": tested,
                "modular_operations": op_count,
            }
        )
    if any(successes.values()):
        raise AssertionError("G6 attack succeeded: " + repr(successes))
    if reference_successes != 8:
        raise AssertionError(f"G6 reference solved {reference_successes}/8")
    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": {
            name: {"successes": successes[name], "attempts": 8}
            for name in attack_names
        },
        "reference_algorithm": {
            "name": "forward power-map preimage enumeration",
            "complexity": "O(n*rounds*log n) exact modular arithmetic",
            "shipping_seed": 314_159,
            "wall_clock_sec": round(reference_seconds, 6),
            "coordinates_scanned": scanned,
            "operations": operations,
            "solves": "8/8, as expected for Track B",
            "measurements": reference_measurements,
        },
    }

    base_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled_params = dict(base_params)
    doubled_params["n"] = _next_prime(2 * doubled_params["n"])
    doubled = make_instance(seed=77, **doubled_params)
    ok, reason = verify(doubled, doubled["answer"])
    if not ok:
        raise AssertionError("G7 doubled instance: " + reason)
    report["G7_scales"] = {
        "pass": True,
        "base_n": base_params["n"],
        "doubled_n": doubled_params["n"],
        "base_answer_length": 2,
        "doubled_answer_length": 2,
        "base_space": str(search_space(shipping)),
        "doubled_space": str(search_space(doubled)),
        "doubled_planted_verifies": True,
    }

    invariant = carried = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(
            seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        for reflect in (False, True):
            transformed = _reencode(
                inst, random.Random(20_000 + 2 * seed + int(reflect)), reflect
            )
            if canonical_key(inst) != canonical_key(transformed):
                raise AssertionError(
                    f"G8 relabelling/reflection changed key at seed {seed}"
                )
            invariant += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                raise AssertionError(f"G8 carried witness at seed {seed}: {reason}")
            carried += 1
        unrelated_keys.append(canonical_key(inst))
    distinct = len(set(unrelated_keys))
    if distinct != 20:
        raise AssertionError(f"G8 unrelated distinctness {distinct}/20")
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_transformations": invariant,
        "carried_witnesses_verified": carried,
        "unrelated_keys_distinct": distinct,
        "unrelated_keys_tested": 20,
        "symmetries": [
            "affine vertex relabelling",
            "base-path reflection",
            "their compositions",
        ],
        "method": (
            "exact isomorphism class n plus duplicated path coordinate modulo "
            "path reflection"
        ),
    }

    chars, tokens, elements = _answer_size(shipping["answer"])
    arms = G9_ORACLE_RESULTS
    hinted_verdict = arms.get("hinted_verdict")
    intended_operations = _compact_route_operations(shipping)
    within_caps = chars <= 2_000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05, both the three-arm comparison and the hinted arm
        # are diagnostics.  Only the answer-size and intended-effort caps gate.
        "pass": within_caps,
        "arms": {
            name: dict(arms[name]) for name in ("bare", "hinted", "placebo")
        },
        "hinted_minus_placebo": (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
            if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]
            else None
        ),
        "hinted_verdict": hinted_verdict,
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "operation_model": (
            "binary modular square/multiplies using displayed inverse "
            "exponents, two subtraction/reduction operations per power "
            "reverse, three per affine reverse, and nine final "
            "ranking/relabel/order operations"
        ),
    }
    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
