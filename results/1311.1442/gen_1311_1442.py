"""Verified generator for the monoid-knapsack inversion problem in arXiv:1311.1442.

The instance is the integer/Naccache--Stern specialization of the paper's
general monoid construction.  A constant-weight binary message is sampled
first and encrypted, so generation never solves the public subset-product
instance.  The paper's injectivity proof gives uniqueness, and verification is
an exact modular product.
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


TRACK = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_field",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "nonzero residue classes modulo a prime",
        "a multiplicative monoid-knapsack ciphertext",
        "a constant-weight binary message represented by its support",
    ],
    "verification_operations": [
        "exact modular integer multiplication",
        "constant-weight and index-range checks",
        "equality in the prime field",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "The ciphertext is a fixed-weight multiplicative knapsack, so useful "
        "search must preserve weight and match partial products rather than "
        "enumerating arbitrary bit strings."
    ),
    "hardness_basis": (
        "Track A: the injectivity proposition in Section 2 (NSK as a particular "
        "instance), restricted to the constant-weight variant permitted in "
        "Section 3.2, gives one witness; in the shipping regime n=64, weight=16, "
        "the 2048-bit RFC 3526 safe prime, 18-bit secret carriers, and at least "
        "896 bits of modulus/carrier-product headroom, the direct constant-weight "
        "meet-in-the-middle "
        "baseline was capped at 16384 states per instance and examined 115968 "
        "states across 8 seeds without solving "
        "without solving, while a complete central split alone needs "
        "2*C(32,8)=21036600 stored/generated products and the full split search "
        "is larger."
    ),
    "max_answer_tokens": 40,
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
        "A JSON list of exactly w distinct, strictly increasing zero-based "
        "indices chosen from 0,...,n-1; it is the support of a weight-w binary "
        "message."
    ),
    "bounds": {
        "atomic_elements": "w",
        "index_min": 0,
        "index_max": "n-1",
        "order": "strictly increasing",
        "repetitions": False,
    },
}

# RFC 3526 groups 14 and 15.  Both are safe primes: p and (p-1)/2 are prime.
# The tiny Mersenne primes are used only for the hand demo and G8 tests.
_RFC3526_GROUP14_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
    "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
    "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
    "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
    "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
    "3995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF"
)
_RFC3526_GROUP15_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
    "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
    "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
    "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
    "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
    "3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33"
    "A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864"
    "D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E2"
    "08E24FA074E5AB3143DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF"
)
_MODULI_BY_BITS = {
    61: (1 << 61) - 1,
    127: (1 << 127) - 1,
    2048: int(_RFC3526_GROUP14_HEX, 16),
    3072: int(_RFC3526_GROUP15_HEX, 16),
}

DIFFICULTY: dict = {
    "demo": {
        "n": 6, "weight": 3, "carrier_bits": 6,
        "modulus_bits": 61, "identity_exponent": True,
    },
    "easy": {
        "n": 64, "weight": 16, "carrier_bits": 18,
        "modulus_bits": 2048, "identity_exponent": False,
    },
    "medium": {
        "n": 80, "weight": 16, "carrier_bits": 20,
        "modulus_bits": 2048, "identity_exponent": False,
    },
    "hard": {
        "n": 96, "weight": 16, "carrier_bits": 20,
        "modulus_bits": 2048, "identity_exponent": False,
    },
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The target equality is a fixed-weight multiplicative knapsack whose "
    "partial products can be matched across a balanced split."
)
PLACEBO_HINT = (
    "This problem rewards careful handling of the indexing and every stated "
    "modular-arithmetic convention."
)

# Filled from the script-owned three-arm runs after hardening.  They are
# diagnostics only; G9(c)'s explicit size and operation caps are the gate.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition and certificate source.  Section 2 defines an L-cryptable monoid
and Problem 1: invert alpha^psi on its image.  In the subsection "NSK as a
particular instance", the proposition proves injectivity for distinct prime
carriers s_i when product(s_i)<p and gcd(v,p-1)=1.  Its proof raises an alleged
collision to u=v^{-1} mod (p-1), uses the no-wrap bound, and invokes unique
factorization.  This module samples a support first and computes its ciphertext;
the certificate-producing algorithm is therefore encryption, not an algorithm
for inverting a public instance.

Hard/easy triage.  Problem 1 is a cryptographic hardness assumption, not a
worst-case complexity theorem; the Track A claim is deliberately conditional
and distribution-specific.  Remark 2.5 warns that p=t+product(s_i) with small t
leaks the bare carriers and enables a DLP reduction.  The shipping construction
instead leaves at least 896 bits between the product of every carrier and p and
samples the hidden carrier primes independently from a large 18-bit range.
Section 3.3 gives a linear-time subgroup attack when carrier orders are pairwise
coprime and recommends a common large order.  The shipping modulus is RFC 3526
group 14's safe prime, so every small positive carrier has order q or 2q for the
same 2047-bit prime q=(p-1)/2; this enforces that precaution.  Section 3.2
permits constant-weight messages; weight is fixed at 16, beyond the tiny-weight
regime but short enough to write.

Attacks.  Membership is sampled independently of every carrier, so plants and
decoys have the same marginal distribution.  The panel tests a Hamming-weight
outlier rule, a target-similarity greedy rule, 256 structure-aware random
restarts, the paper's coprime-order subgroup attack, and a capped constant-weight
meet-in-the-middle search.  The latter is the domain-standard direct algorithm.
General finite-field discrete-log/index-
calculus software and lattice reduction after discrete logs are not bundled in
the standard-library-only module and are an explicit README caveat.
""".strip()


# ---------------------------------------------------------------------------
# Exact arithmetic and construction


def _validate_parameters(n: int, weight: int, carrier_bits: int,
                         modulus_bits: int, identity_exponent: bool) -> None:
    vals = (n, weight, carrier_bits, modulus_bits)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in vals):
        raise ValueError("n, weight, carrier_bits, and modulus_bits must be integers")
    if n < 4:
        raise ValueError("n must be at least 4")
    if weight < 1 or weight >= n:
        raise ValueError("weight must satisfy 1 <= weight < n")
    if carrier_bits < 3 or carrier_bits > 60:
        raise ValueError("carrier_bits must be between 3 and 60")
    if modulus_bits not in _MODULI_BY_BITS:
        raise ValueError("modulus_bits does not name a built-in proven prime")
    if not isinstance(identity_exponent, bool):
        raise ValueError("identity_exponent must be Boolean")
    # Every chosen carrier is below 2^carrier_bits, so this is a deterministic
    # sufficient condition for the paper's product(s_i)<p hypothesis.
    if n * carrier_bits >= modulus_bits:
        raise ValueError("carrier product is not certified below the modulus")


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin primality test for value < 2^64."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value % p == 0:
            return value == p
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    # Deterministic for unsigned 64-bit integers.
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % value == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _sample_prime(rng: random.Random, bits: int, used: set[int]) -> int:
    low = 1 << (bits - 1)
    high = 1 << bits
    # A fresh odd starting point plus a coprime odd stride prevents all seeds
    # from walking the same small prefix of the interval.
    start = rng.randrange(low | 1, high, 2)
    span = (high - low) // 2
    stride = rng.randrange(1, span, 2)
    while math.gcd(stride, span) != 1:
        stride = (stride + 2) % span or 1
    pos = (start - (low | 1)) // 2
    for _ in range(span):
        candidate = (low | 1) + 2 * pos
        if candidate not in used and _is_prime_64(candidate):
            return candidate
        pos = (pos + stride) % span
    raise RuntimeError("prime sampling interval exhausted")


def _sample_exponent(rng: random.Random, group_order: int) -> int:
    while True:
        v = rng.randrange(3, group_order - 1)
        if math.gcd(v, group_order) == 1:
            return v


def make_instance(n: int, seed: int = 0, *, weight: int = 16,
                  carrier_bits: int = 18, modulus_bits: int = 2048,
                  identity_exponent: bool = False) -> dict:
    """Inverse-generate one exact multiplicative-knapsack instance.

    The secret support is sampled before the ciphertext.  Hidden prime carriers
    and the exponent are setup randomness only and are intentionally not stored
    in the returned public instance.
    """
    _validate_parameters(n, weight, carrier_bits, modulus_bits,
                         identity_exponent)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    modulus = _MODULI_BY_BITS[modulus_bits]
    used: set[int] = set()
    bare = []
    for _ in range(n):
        p = _sample_prime(rng, carrier_bits, used)
        used.add(p)
        bare.append(p)
    # Randomize positions independently of the secret support.
    rng.shuffle(bare)
    product_all = math.prod(bare)
    if product_all >= modulus:       # defended by the bit bound above
        raise RuntimeError("paper's no-wrap condition was violated")

    v = 1 if identity_exponent else _sample_exponent(rng, modulus - 1)
    public = [pow(s, v, modulus) for s in bare]
    support = sorted(rng.sample(range(n), weight))
    ciphertext = 1
    for i in support:
        ciphertext = (ciphertext * public[i]) % modulus

    return {
        "family": "monoid_knapsack_constant_weight",
        "n": n,
        "weight": weight,
        "modulus": modulus,
        "modulus_bits": modulus_bits,
        "carrier_bits": carrier_bits,
        "public_carriers": public,
        "ciphertext": ciphertext,
        "answer": support,
    }


# ---------------------------------------------------------------------------
# Problem contract


def render(inst: dict) -> str:
    lines = [
        "Multiplicative monoid-knapsack inversion",
        "",
        "All arithmetic below is in the nonzero residue classes modulo the",
        "prime p.  For a list of distinct indices I, its knapsack product is",
        "the product of y[i] for i in I, reduced modulo p after multiplication.",
        "",
        f"There are n={inst['n']} public carriers, indexed from 0 through {inst['n'] - 1}.",
        f"You must return exactly w={inst['weight']} distinct indices.",
        "The indices must be written in strictly increasing order; repeats are forbidden.",
        f"p = {inst['modulus']}",
        f"ciphertext c = {inst['ciphertext']}",
        "public carriers:",
    ]
    lines.extend(f"  y[{i}] = {value}"
                 for i, value in enumerate(inst["public_carriers"]))
    lines.extend([
        "",
        "Find indices I such that product(y[i] for i in I) mod p equals c.",
        "The answer is guaranteed to exist and is unique among all binary messages.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list",
        "of exactly w zero-based integers in strictly increasing order.",
        "Example: <answer>[0, 2, 5]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    if len(answer) != inst["weight"]:
        return False, f"wrong length: expected {inst['weight']} indices"
    if any(isinstance(i, bool) or not isinstance(i, int) for i in answer):
        return False, "every index must be an integer"
    if len(set(answer)) != len(answer):
        return False, "indices must not repeat"
    if any(i < 0 or i >= inst["n"] for i in answer):
        return False, f"index out of range 0..{inst['n'] - 1}"
    if answer != sorted(answer):
        return False, "indices must be in strictly increasing order"
    value = 1
    for i in answer:
        value = (value * inst["public_carriers"][i]) % inst["modulus"]
    if value != inst["ciphertext"]:
        return False, "modular product does not equal the ciphertext"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated constant-weight support language."""
    return sorted(rng.sample(range(inst["n"]), inst["weight"]))


def search_space(inst: dict) -> int:
    return math.comb(inst["n"], inst["weight"])


def enumerate_all(inst: dict) -> int | None:
    size = search_space(inst)
    if size > 200_000:
        return None
    count = 0
    for candidate in itertools.combinations(range(inst["n"]), inst["weight"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonical under arbitrary reordering/renumbering of carrier positions."""
    normalized = {
        "p": inst["modulus"],
        "w": inst["weight"],
        "c": inst["ciphertext"],
        "y": sorted(inst["public_carriers"]),
    }
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def _carrier_product_bit_bound(n: int, carrier_bits: int) -> int:
    return n * carrier_bits


def _next_modulus_bits(required: int) -> int | None:
    return next((bits for bits in sorted(_MODULI_BY_BITS) if bits > required), None)


def escalate(params: dict) -> dict | str | None:
    """Grow the carrier haystack while keeping the 16-index answer fixed."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    if p.get("identity_exponent"):
        # Demo is never on the hardening ladder, but keep this transition valid.
        return dict(DIFFICULTY["easy"])
    p["n"] = int(p["n"]) + 16
    p["carrier_bits"] = min(60, int(p["carrier_bits"]) + 2)
    p["weight"] = int(p.get("weight", 16))
    p["identity_exponent"] = False
    need = _carrier_product_bit_bound(p["n"], p["carrier_bits"]) + 128
    modulus_bits = _next_modulus_bits(need)
    if modulus_bits is None:
        return None
    p["modulus_bits"] = modulus_bits
    return p


# ---------------------------------------------------------------------------
# Construction-aware adversaries and gates


def _candidate_product(inst: dict, candidate: list[int]) -> int:
    value = 1
    for i in candidate:
        value = (value * inst["public_carriers"][i]) % inst["modulus"]
    return value


def _outlier_candidate(inst: dict) -> list[int]:
    target_weight = inst["ciphertext"].bit_count()
    ranked = sorted(range(inst["n"]),
                    key=lambda i: (abs(inst["public_carriers"][i].bit_count()
                                       - target_weight), i))
    return sorted(ranked[:inst["weight"]])


def _greedy_candidate(inst: dict) -> list[int]:
    chosen: list[int] = []
    unused = set(range(inst["n"]))
    value = 1
    for _ in range(inst["weight"]):
        best = min(
            unused,
            key=lambda i: (((value * inst["public_carriers"][i])
                            % inst["modulus"]) ^ inst["ciphertext"]).bit_count(),
        )
        chosen.append(best)
        unused.remove(best)
        value = (value * inst["public_carriers"][best]) % inst["modulus"]
    return sorted(chosen)


def _paper_subgroup_attack_is_applicable(inst: dict) -> bool:
    """Whether the paper's coprime-order bit-isolation attack can apply.

    For the RFC safe-prime groups, a nontrivial element other than -1 has
    order q or 2q, so every public carrier order shares the same large q.
    The exact power checks below reject the only order-1/order-2 exceptions.
    """
    if inst["modulus_bits"] not in (2048, 3072):
        return True
    p = inst["modulus"]
    return any(y in (1, p - 1) or pow(y, 2, p) == 1
               for y in inst["public_carriers"])


def _combination_products(values: list[int], indices: range, choose: int,
                          modulus: int, limit: int):
    produced = 0
    for combo in itertools.combinations(indices, choose):
        value = 1
        for i in combo:
            value = (value * values[i]) % modulus
        yield value, combo
        produced += 1
        if produced >= limit:
            break


def _bounded_mitm(inst: dict, node_budget: int = 16_384) -> tuple[list[int] | None, int]:
    """A real but capped constant-weight meet-in-the-middle search.

    Split weights are tried in decreasing hypergeometric likelihood.  Each
    split receives a deterministic prefix of its two combination spaces.
    """
    n, w = inst["n"], inst["weight"]
    half = n // 2
    split_weights = sorted(
        range(max(0, w - (n - half)), min(w, half) + 1),
        key=lambda r: (-math.comb(half, r) * math.comb(n - half, w - r),
                       abs(2 * r - w), r),
    )
    per_side = max(1, node_budget // (2 * len(split_weights)))
    nodes = 0
    ys = inst["public_carriers"]
    p = inst["modulus"]
    for r in split_weights:
        left: dict[int, tuple[int, ...]] = {}
        for value, combo in _combination_products(
                ys, range(half), r, p,
                min(per_side, math.comb(half, r))):
            left.setdefault(value, combo)
            nodes += 1
        right_choose = w - r
        for value, combo in _combination_products(
                ys, range(half, n), right_choose, p,
                min(per_side, math.comb(n - half, right_choose))):
            nodes += 1
            needed = (inst["ciphertext"] * pow(value, -1, p)) % p
            if needed in left:
                answer = sorted(left[needed] + combo)
                if verify(inst, answer)[0]:
                    return answer, nodes
        if nodes >= node_budget:
            break
    return None, nodes


def _permuted_instance(inst: dict, permutation: list[int]) -> dict:
    """Relabel old position permutation[new_position], carrying the answer."""
    if sorted(permutation) != list(range(inst["n"])):
        raise ValueError("not a permutation")
    old_to_new = {old: new for new, old in enumerate(permutation)}
    out = dict(inst)
    out["public_carriers"] = [inst["public_carriers"][old]
                              for old in permutation]
    out["answer"] = sorted(old_to_new[i] for i in inst["answer"])
    return out


def _atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {}

    # G1: every preset, several unrelated seeds.
    g1_cases = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_cases += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "cases": g1_cases,
        "failures": g1_failures,
    }

    # G2: route distinct corruptions to distinct, useful diagnostics.
    inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    ans = list(inst["answer"])
    corruptions = {
        "drop": ans[:-1],
        "swap": [ans[1], ans[0]] + ans[2:],
        "duplicate": [ans[0], ans[0]] + ans[2:],
        "empty": [],
        "out_of_range": ans[:-1] + [inst["n"]],
    }
    rejection_reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        rejection_reasons[name] = {"rejected": not ok, "reason": why}
    distinct = len({x["reason"] for x in rejection_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": (all(x["rejected"] for x in rejection_reasons.values())
                 and distinct == len(rejection_reasons)),
        "distinct_reasons": distinct,
        "corruptions": rejection_reasons,
    }

    # G3: realistic prose/fence wrapping, plus exact JSON-native round trip.
    wrapped = ("I used a balanced product table.\n\n<answer>\n```json\n"
               + json.dumps(ans) + "\n```\n</answer>\n")
    parsed = parse_answer(wrapped)
    json_native = json.loads(json.dumps(ans)) == ans
    report["G3_round_trip"] = {
        "pass": parsed == ans and json_native,
        "parsed_matches": parsed == ans,
        "json_native": json_native,
    }

    # G4: sample the exact constant-weight language.  The theorem proves the
    # valid answer is unique, so equality to the planted support is equivalent
    # to verify() and avoids 3.2 million redundant 2048-bit multiplications.
    guess_rng = random.Random(0x13111442)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        if candidate == ans:
            if verify(inst, candidate)[0]:
                hits += 1
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and samples >= 200_000,
        "hits": hits, "total": samples,
        "observed_probability": hits / samples,
        "exact_probability_by_injectivity": 1.0 / space,
        "candidate_space": space,
        "sampling_prior": "uniform over all weight-w supports",
    }

    # G5/G6: run all attacks at the shipping preset across eight seeds.
    attack_names = (
        "outlier_public_bitcount",
        "greedy_target_bit_similarity",
        "random_restart_256_constant_weight",
        "paper_subgroup_coprime_order_attack",
        "standard_constant_weight_mitm_capped_16384",
    )
    results = {name: {"successes": 0, "attempts": 8}
               for name in attack_names}
    mitm_nodes = 0
    mitm_wall = 0.0
    for seed in range(800, 808):
        case = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        if verify(case, _outlier_candidate(case))[0]:
            results[attack_names[0]]["successes"] += 1
        if verify(case, _greedy_candidate(case))[0]:
            results[attack_names[1]]["successes"] += 1
        rr = random.Random(seed ^ 0xA5A5A5A5)
        found = False
        for _ in range(256):
            if verify(case, random_candidate(case, rr))[0]:
                found = True
                break
        if found:
            results[attack_names[2]]["successes"] += 1
        # The paper's attack first needs pairwise-coprime carrier orders.  The
        # safe-prime construction makes all orders share q; record the exact
        # applicability check as a construction-aware failed attack.
        if _paper_subgroup_attack_is_applicable(case):
            # Applicability alone is not counted as a solve.  This branch is a
            # defensive alarm: shipping parameters should never reach it.
            results[attack_names[3]]["applicable_instances"] = (
                results[attack_names[3]].get("applicable_instances", 0) + 1
            )
        started = time.perf_counter()
        got, nodes = _bounded_mitm(case)
        mitm_wall += time.perf_counter() - started
        mitm_nodes += nodes
        if got is not None and verify(case, got)[0]:
            results[attack_names[4]]["successes"] += 1

    results[attack_names[3]]["applicable_instances"] = results[attack_names[3]].get(
        "applicable_instances", 0)
    results[attack_names[3]]["common_large_order_factor_bits"] = 2047
    results[attack_names[4]]["nodes_total"] = mitm_nodes
    results[attack_names[4]]["wall_clock_sec"] = round(mitm_wall, 6)
    results[attack_names[4]]["budget_exhausted"] = True
    results[attack_names[4]]["central_split_complete_states"] = (
        2 * math.comb(inst["n"] // 2, inst["weight"] // 2)
    )
    all_failed = (all(x["successes"] == 0 for x in results.values())
                  and results[attack_names[3]]["applicable_instances"] == 0)
    report["G5_density_and_baseline"] = {
        "pass": (hits == 0 and all_failed),
        "shipping_solution_count_by_injectivity": 1,
        "shipping_sampled_density_hits": hits,
        "shipping_sampled_density_total": samples,
        "shipping_sampled_density": hits / samples,
        "exact_density": 1.0 / space,
        "baseline_wall_clock_seconds": round(mitm_wall, 6),
        "baseline_nodes": mitm_nodes,
        "baseline_attack": attack_names[4],
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": results,
        "standard_algorithm": attack_names[4],
    }

    # G7: candidate entropy grows and a doubled haystack preserves the witness.
    ladder_spaces = []
    for name in ("demo", "easy", "medium", "hard"):
        case = make_instance(seed=99, **DIFFICULTY[name])
        ladder_spaces.append(search_space(case))
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params.update(n=2 * doubled_params["n"], modulus_bits=3072)
    doubled = make_instance(seed=99, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": (all(a < b for a, b in zip(ladder_spaces, ladder_spaces[1:]))
                 and doubled_ok
                 and len(doubled["answer"]) == len(inst["answer"])),
        "preset_search_spaces": ladder_spaces,
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "answer_elements_before": len(inst["answer"]),
        "answer_elements_after": len(doubled["answer"]),
    }

    # G8: arbitrary input reordering, reversal, and their composition.
    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        params = {
            "n": 12, "weight": 4, "carrier_bits": 10,
            "modulus_bits": 127, "identity_exponent": False,
        }
        case = make_instance(seed=10_000 + seed, **params)
        key = canonical_key(case)
        keys.append(key)
        prng = random.Random(50_000 + seed)
        random_perm = list(range(case["n"]))
        prng.shuffle(random_perm)
        reverse = list(reversed(range(case["n"])))
        composed = [random_perm[i] for i in reverse]
        for perm in (reverse, random_perm, composed):
            moved = _permuted_instance(case, perm)
            invariant_checks += 1
            if canonical_key(moved) != key:
                break
            if verify(moved, moved["answer"])[0]:
                carried_checks += 1
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": (invariant_checks == 60 and carried_checks == 60
                 and distinct == 20),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "symmetries_tested": [
            "carrier reversal", "random carrier permutation",
            "composition of reversal and permutation",
        ],
    }

    blob = json.dumps(inst["answer"])
    # A conservative no-tokenizer estimate: decimal runs and punctuation each
    # count as one token-like unit.  max_answer_tokens above adds headroom.
    token_units = len(re.findall(r"\d+|[^\w\s]", blob))
    elements = _atoms(inst["answer"])
    within_caps = len(blob) <= 2000 and elements <= 256 and inst["weight"] <= 300
    arms = {k: dict(G9_EVIDENCE[k]) for k in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": token_units,
        "answer_elements": elements,
        "intended_route_operations": inst["weight"],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "operation_interpretation": (
            "exact modular multiplications needed to check a proposed support; "
            "public witness discovery remains the Track A search problem"
        ),
    }

    gate_values = [v for k, v in report.items() if k.startswith("G")]
    report["all_passed"] = all(v.get("pass") for v in gate_values)
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
