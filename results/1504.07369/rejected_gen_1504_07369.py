"""Rejected prototype generator based on arXiv:1504.07369.

The paper constructs cyclic Hamiltonian cycle systems with partial differences.
This module uses one of its eight-entry base-cycle signatures and applies an
unknown automorphism of the ambient cyclic group.  The witness identifies the
unique transformed signature and gives the multiplier with its inverse.

This prototype is retained as required evidence.  It is not shippable: the
unit-anchor attack implemented below solves every instance in a handful of
operations.  See REJECTED.md.
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
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The modular sum of an oriented half-difference signature transforms linearly under every unit multiplier."
)
PLACEBO_HINT: str = (
    "Careful separation of source and target residue indices prevents avoidable transcription mistakes."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "partial-difference signatures in a cyclic group",
        "cyclic-group automorphisms",
        "base cycles of a cyclic Hamiltonian cycle system",
    ],
    "verification_operations": [
        "exact modular multiplication",
        "exact modular inverse check",
        "multiset equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Use the modular sum of a partial-difference signature to reduce an exhaustive unit search to eight lifts; "
        "without it, the reference method scans roughly a million multipliers."
    ),
    "hardness_basis": (
        "Track B: exhaustive unit-action search takes O(h*2^n*r) modular operations for h target signatures "
        "of length r=8 and, at shipping n=20 and h=3, measured a median 374,323 candidates, 374,334 modular "
        "products, and 0.05 seconds over eight seeds (with 1,557,317 products on the slowest seed); the sum "
        "invariant leaves only eight lifts per target and at most 247 "
        "exact-arithmetic operations, but a no-tool solver must discover that invariant and execute the modular arithmetic."
    ),
    "max_answer_tokens": 5,
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
    "demo": {"n": 8, "target_count": 2},
    "easy": {"n": 16, "target_count": 2},
    "medium": {"n": 18, "target_count": 3},
    "hard": {"n": 20, "target_count": 3},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A three-integer tuple [j,u,v]: j is a 0-based target index; u is an odd, non-involutory unit modulo 2^n; "
        "and v is the unique inverse of u in the range 0..2^n-1."
    ),
    "bounds": {
        "atomic_elements": 3,
        "target_index": "0..target_count-1",
        "multiplier": "1..2^n-1, odd, u^2 != 1 (mod 2^n)",
        "inverse": "determined by multiplier",
    },
}

NOTES: str = (
    "Section 2, especially Definition 2.1 and Theorem 2.2, fixes the native object: partial differences certify "
    "base cycles of a cyclic HCS by exact coverage in Z_mn. The source signature here is the b=3 cycle A_{i,3} "
    "from the power-of-two case in Theorem 4.4; its displayed half-signature is {16i+4} union {16i+9,...,16i+15}. "
    "Theorem 4.4 also identifies the easy route that rules out Track A for direct HCS construction: it gives every "
    "cycle by an explicit formula. This module therefore uses a transformation-of-a-known-instance route and makes "
    "the solver recover the automorphism, not reproduce the formula. Target decoys are independently transformed "
    "Theorem 4.4 signatures from the same distribution, and one further common random group automorphism hides the "
    "formula's consecutive coordinates without changing the hidden multiplier. The panel tests 2-adic outlier alignment, a smallest-gap "
    "greedy rule, uniform random restarts, a one-lift use of the sum congruence, and a small-unit scan. The plant is "
    "sampled away from the lowest sum lift and the small-unit range. For both plants and decoys, the generator also "
    "rejects transformed signatures recovered by the fixed 2-adic-rank and smallest-gap probes; this attack filtering "
    "is applied to the same source-index and multiplier distribution on both sides and never searches for a certificate. "
    "The reference algorithm is disclosed exhaustive unit enumeration."
)


# Filled from the three independent harden.py runs after the module is hardened.
# These arms are diagnostic; only the answer/operation caps gate G9.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
}


def _v2(x: int) -> int:
    """2-adic valuation for a nonzero residue represented as an integer."""
    if x == 0:
        return 10**9
    return (x & -x).bit_length() - 1


def _base_signature(group_order: int, cycle_index: int) -> list[int]:
    """The positive half of partial differences of paper cycle A_(i,3)."""
    offset = 16 * cycle_index
    signature = [offset + 4] + list(range(offset + 9, offset + 16))
    if not all(0 < x < group_order // 2 for x in signature):
        raise ValueError("cycle index is outside the Theorem 4.4 range")
    return signature


def _multiply_signature(signature: list[int], unit: int, modulus: int) -> list[int]:
    return [(unit * x) % modulus for x in signature]


def _is_language_unit(unit: int, modulus: int) -> bool:
    return (
        isinstance(unit, int)
        and not isinstance(unit, bool)
        and 0 < unit < modulus
        and unit % 2 == 1
        and (unit * unit) % modulus != 1
    )


def _sample_language_unit(rng: random.Random, modulus: int, hardened: bool = False) -> int:
    while True:
        unit = rng.randrange(1, modulus, 2)
        if not _is_language_unit(unit, modulus):
            continue
        if hardened and unit < modulus // 8:
            continue
        if hardened and unit <= 4095:
            continue
        return unit


def _orbit_key(signature: list[int], modulus: int) -> tuple[int, ...]:
    """Canonical unit orbit of one signature, using its odd entries as anchors."""
    forms = []
    for anchor in signature:
        if anchor % 2:
            inv = pow(anchor, -1, modulus)
            forms.append(tuple(sorted((inv * x) % modulus for x in signature)))
    if not forms:
        raise ValueError("a signature must contain an odd unit anchor")
    return min(forms)


def _rank_alignment_guess(source: list[int], target: list[int], modulus: int) -> int | None:
    """Unit guessed by aligning sorted entries within every 2-adic stratum."""
    source_groups = {}
    target_groups = {}
    for value in source:
        source_groups.setdefault(_v2(value), []).append(value)
    for value in target:
        target_groups.setdefault(_v2(value), []).append(value)
    for values in source_groups.values():
        values.sort()
    for values in target_groups.values():
        values.sort()
    if {key: len(val) for key, val in source_groups.items()} != {
        key: len(val) for key, val in target_groups.items()
    }:
        return None
    ratios = [
        (target_value * pow(source_value, -1, modulus)) % modulus
        for source_value, target_value in zip(
            source_groups.get(0, []), target_groups.get(0, [])
        )
    ]
    if ratios and len(set(ratios)) == 1:
        return ratios[0]
    return None


def _smallest_gap_guess(target: list[int], modulus: int) -> int | None:
    gaps = {
        (right - left) % modulus
        for left in target
        for right in target
        if left != right
    }
    return min(gaps) if gaps else None


def _sample_transformed_signature(
    source: list[int], rng: random.Random, modulus: int, hardened: bool
) -> tuple[list[int], int]:
    """Sample a transformed signature outside the two fixed cheap-probe events."""
    while True:
        unit = _sample_language_unit(rng, modulus, hardened=hardened)
        target = _multiply_signature(source, unit, modulus)
        rank_guess = _rank_alignment_guess(source, target, modulus)
        gap_guess = _smallest_gap_guess(target, modulus)
        if rank_guess == unit or gap_guess == unit:
            continue
        rng.shuffle(target)
        return target, unit


def make_instance(n, seed=0, **params) -> dict:
    """Plant a unit automorphism and transform a known Theorem 4.4 signature."""
    target_count = params.pop("target_count", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    if not isinstance(target_count, int) or not 2 <= target_count <= 3:
        raise ValueError("target_count must be 2 or 3")

    rng = random.Random(seed)
    modulus = 1 << n
    parts = 8
    part_size = modulus // parts
    cycle_count = modulus // 32

    source_index = rng.randrange(cycle_count)
    source = _base_signature(modulus, source_index)
    source_orbit = _orbit_key(source, modulus)

    decoy_sources = []
    used_orbits = {source_orbit}
    while len(decoy_sources) < target_count - 1:
        candidate = _base_signature(modulus, rng.randrange(cycle_count))
        key = _orbit_key(candidate, modulus)
        if key not in used_orbits:
            used_orbits.add(key)
            decoy_sources.append(candidate)

    hardened = n >= 14
    targets = []
    for decoy_source in decoy_sources:
        target, _decoy_unit = _sample_transformed_signature(
            decoy_source, rng, modulus, hardened
        )
        targets.append(target)

    # For non-demo instances the plant is deliberately outside two cheap scan
    # ranges.  This samples the certificate first; it never solves a generated
    # instance to recover one.
    target, unit = _sample_transformed_signature(source, rng, modulus, hardened)
    planted_slot = rng.randrange(target_count)
    targets.insert(planted_slot, target)

    # Change the common cyclic coordinate system as well.  This carries every
    # base cycle through a graph automorphism and prevents the consecutive block
    # in Theorem 4.4 from remaining a visible magnitude signature.  Resample the
    # common frame only when either fixed deterministic probe recovers the plant.
    while True:
        coordinate_unit = rng.randrange(1, modulus, 2)
        shown_source = _multiply_signature(source, coordinate_unit, modulus)
        shown_targets = [
            _multiply_signature(candidate, coordinate_unit, modulus)
            for candidate in targets
        ]
        rank_guess = _rank_alignment_guess(
            shown_source, shown_targets[planted_slot], modulus
        )
        gap_guess = _smallest_gap_guess(shown_targets[planted_slot], modulus)
        if rank_guess != unit and gap_guess != unit:
            source = shown_source
            targets = shown_targets
            break
    rng.shuffle(source)
    for shown_target in targets:
        rng.shuffle(shown_target)

    inverse = pow(unit, -1, modulus)
    return {
        "paper": "arXiv:1504.07369",
        "family": "partial-difference automorphism recovery",
        "n": n,
        "group_order": modulus,
        "parts": parts,
        "part_size": part_size,
        "cycle_step": 8,
        "source_signature": source,
        "target_signatures": targets,
        "answer": [planted_slot, unit, inverse],
    }


def render(inst) -> str:
    modulus = inst["group_order"]
    source = ", ".join(map(str, inst["source_signature"]))
    lines = [
        "Recover an automorphism between partial-difference signatures of cyclic Hamiltonian base cycles.",
        "",
        "Definitions.",
        f"Work in the additive cyclic group Z_{modulus}; all arithmetic below is modulo {modulus}.",
        f"This group labels the vertices of the complete multipartite graph K_{{8 x {inst['part_size']}}}: two vertices are in the same part exactly when they are congruent modulo 8.",
        "For a cyclic base cycle, every traversed edge has a nonzero difference x, and its undirected signed difference pair is {x,-x}.",
        "An oriented half-difference signature lists one chosen residue x from each of eight signed pairs. In this problem the chosen orientation is part of the data: do not replace x by -x.",
        "Each displayed signature is an unordered multiset of eight distinct residues; its printed order has no meaning.",
        "A unit is an odd residue u with 1 <= u < the group order. Multiplication by a unit is an automorphism of the cyclic group and maps a signature D to the multiset {u*d mod group_order : d in D}.",
        "A unit is non-involutory when u*u mod group_order is not 1.",
        "Exactly one target signature below is the image of the source under a non-involutory unit.",
        "",
        f"Source signature D: [{source}]",
        "Target signatures (0-based indices):",
    ]
    for index, target in enumerate(inst["target_signatures"]):
        lines.append(f"  {index}: [{', '.join(map(str, target))}]")
    lines.extend(
        [
            "",
            "Find the unique target index j, the non-involutory unit u mapping D to that target, and the inverse v satisfying u*v = 1 modulo the group order.",
            "All three output values are ordinary base-10 integers. Target indices are 0-based; order in each signature is ignored, but repeats would retain multiplicity.",
            "Give your final answer inside <answer></answer> tags, as exactly j, u, v separated by commas.",
            "Example: <answer>1, 37, 173</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    try:
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:[A-Za-z0-9_-]+)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1]
        tokens = [token.strip() for token in body.split(",")]
        if len(tokens) != 3 or not all(re.fullmatch(r"[+-]?\d+", token) for token in tokens):
            return None
        return [int(token) for token in tokens]
    except Exception:
        return None


def _maps(source: list[int], target: list[int], unit: int, modulus: int) -> bool:
    return sorted(_multiply_signature(source, unit, modulus)) == sorted(target)


def verify(inst, answer) -> tuple[bool, str]:
    if not isinstance(answer, list) or not all(
        isinstance(x, int) and not isinstance(x, bool) for x in answer
    ):
        return False, "malformed: expected a list of exactly three integers"
    if len(answer) == 0:
        return False, "empty answer: expected target index, multiplier, and inverse"
    if len(answer) != 3:
        return False, f"wrong length: expected 3 integers, got {len(answer)}"

    target_index, unit, inverse = answer
    targets = inst["target_signatures"]
    modulus = inst["group_order"]
    if not 0 <= target_index < len(targets):
        return False, f"target index out of range: expected 0..{len(targets) - 1}"
    if not 0 < unit < modulus or not 0 < inverse < modulus:
        return False, f"residue out of range: multiplier and inverse must lie in 1..{modulus - 1}"
    if unit == inverse:
        return False, "duplicate multiplier fields: the required unit is non-involutory"
    if unit % 2 == 0:
        return False, "not a unit: the multiplier must be odd modulo a power of two"
    if (unit * unit) % modulus == 1:
        return False, "involutory multiplier: u*u must not equal 1 modulo the group order"
    if (unit * inverse) % modulus != 1:
        return False, "inverse mismatch: u*v is not 1 modulo the group order"
    if not _maps(inst["source_signature"], targets[target_index], unit, modulus):
        return False, "signature mismatch: the multiplier does not map the source multiset to the selected target"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    modulus = inst["group_order"]
    unit = _sample_language_unit(rng, modulus)
    return [rng.randrange(len(inst["target_signatures"])), unit, pow(unit, -1, modulus)]


def search_space(inst) -> int | None:
    # For 2^n with n>=3 there are 2^(n-1) units and exactly four involutions.
    return len(inst["target_signatures"]) * (inst["group_order"] // 2 - 4)


def enumerate_all(inst) -> int | None:
    if search_space(inst) > 2_000_000:
        return None
    modulus = inst["group_order"]
    count = 0
    for target in inst["target_signatures"]:
        target_set = set(target)
        for unit in range(1, modulus, 2):
            if (unit * unit) % modulus == 1:
                continue
            if all((unit * x) % modulus in target_set for x in inst["source_signature"]):
                count += 1
    return count


def canonical_key(inst) -> str:
    """Canonical under list reorderings and a global cyclic-group automorphism."""
    modulus = inst["group_order"]
    source = inst["source_signature"]
    targets = inst["target_signatures"]
    forms = []
    for anchor in source:
        if anchor % 2:
            inv = pow(anchor, -1, modulus)
            norm_source = tuple(sorted((inv * x) % modulus for x in source))
            norm_targets = tuple(
                sorted(tuple(sorted((inv * x) % modulus for x in target)) for target in targets)
            )
            forms.append((norm_source, norm_targets))
    canonical = min(forms)
    payload = json.dumps([modulus, canonical], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    out = dict(params)
    current_n = int(out.get("n", 8))
    current_targets = int(out.get("target_count", 2))
    out["n"] = current_n + 2
    # Crowding is a second, fixed-answer-length axis; cap it at three because
    # the compact route's exact-operation budget is 300.
    out["target_count"] = min(3, current_targets + 1)
    if out["n"] > 120:
        return "cap_bound"
    return out


def _answer_text(answer: list[int]) -> str:
    return ", ".join(map(str, answer))


def _compact_sum_solver(inst) -> tuple[list[int] | None, dict]:
    """The intended invariant route, with a conservative arithmetic-op count."""
    modulus = inst["group_order"]
    source = inst["source_signature"]
    sum_source = sum(source) % modulus
    operations = len(source) - 1
    gcd_value = math.gcd(sum_source, modulus)
    operations += 1
    reduced_modulus = modulus // gcd_value
    reduced_source = (sum_source // gcd_value) % reduced_modulus
    source_inverse = pow(reduced_source, -1, reduced_modulus)
    operations += 1

    for target_index, target in enumerate(inst["target_signatures"]):
        sum_target = sum(target) % modulus
        operations += len(target) - 1
        if sum_target % gcd_value:
            operations += 1
            continue
        base = ((sum_target // gcd_value) * source_inverse) % reduced_modulus
        operations += 1
        for lift in range(gcd_value):
            unit = base + lift * reduced_modulus
            operations += 1
            if not _is_language_unit(unit, modulus):
                continue
            target_set = set(target)
            maps = True
            for value in source:
                operations += 1
                if (unit * value) % modulus not in target_set:
                    maps = False
                    break
            if maps:
                operations += 1
                return [target_index, unit, pow(unit, -1, modulus)], {
                    "operations": operations,
                    "gcd": gcd_value,
                    "lifts_per_target": gcd_value,
                }
    return None, {"operations": operations, "gcd": gcd_value, "lifts_per_target": gcd_value}


def _reference_exhaustive(inst) -> tuple[list[int] | None, dict]:
    modulus = inst["group_order"]
    source = inst["source_signature"]
    candidates = 0
    products = 0
    for target_index, target in enumerate(inst["target_signatures"]):
        target_set = set(target)
        for unit in range(1, modulus, 2):
            if (unit * unit) % modulus == 1:
                continue
            candidates += 1
            maps = True
            for value in source:
                products += 1
                if (unit * value) % modulus not in target_set:
                    maps = False
                    break
            if maps:
                return [target_index, unit, pow(unit, -1, modulus)], {
                    "candidates": candidates,
                    "modular_products": products,
                }
    return None, {"candidates": candidates, "modular_products": products}


def _attack_v2_rank_alignment(inst) -> list[int] | None:
    modulus = inst["group_order"]
    for target_index, target in enumerate(inst["target_signatures"]):
        unit = _rank_alignment_guess(inst["source_signature"], target, modulus)
        if unit is not None and _is_language_unit(unit, modulus):
            candidate = [target_index, unit, pow(unit, -1, modulus)]
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _attack_smallest_gap(inst) -> list[int] | None:
    modulus = inst["group_order"]
    for target_index, target in enumerate(inst["target_signatures"]):
        unit = _smallest_gap_guess(target, modulus)
        if unit is not None and _is_language_unit(unit, modulus):
            candidate = [target_index, unit, pow(unit, -1, modulus)]
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _attack_random_restart(inst, rng, restarts=256) -> list[int] | None:
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_one_sum_lift(inst) -> list[int] | None:
    modulus = inst["group_order"]
    source_sum = sum(inst["source_signature"]) % modulus
    gcd_value = math.gcd(source_sum, modulus)
    reduced_modulus = modulus // gcd_value
    inv = pow(source_sum // gcd_value, -1, reduced_modulus)
    for target_index, target in enumerate(inst["target_signatures"]):
        target_sum = sum(target) % modulus
        if target_sum % gcd_value:
            continue
        unit = ((target_sum // gcd_value) * inv) % reduced_modulus
        if _is_language_unit(unit, modulus):
            candidate = [target_index, unit, pow(unit, -1, modulus)]
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _attack_small_unit_scan(inst, limit=4095) -> list[int] | None:
    modulus = inst["group_order"]
    for target_index, target in enumerate(inst["target_signatures"]):
        for unit in range(3, min(modulus, limit + 1), 2):
            if not _is_language_unit(unit, modulus):
                continue
            if _maps(inst["source_signature"], target, unit, modulus):
                return [target_index, unit, pow(unit, -1, modulus)]
    return None


def _attack_unit_anchor(inst) -> list[int] | None:
    """The fatal standard attack: one odd source entry fixes each candidate unit."""
    modulus = inst["group_order"]
    source = inst["source_signature"]
    anchor = next(value for value in source if value % 2)
    anchor_inverse = pow(anchor, -1, modulus)
    for target_index, target in enumerate(inst["target_signatures"]):
        for image in target:
            if image % 2 == 0:
                continue
            unit = (image * anchor_inverse) % modulus
            if not _is_language_unit(unit, modulus):
                continue
            candidate = [target_index, unit, pow(unit, -1, modulus)]
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _transform_instance(inst, global_unit=1, target_permutation=None, reorder_seed=None):
    out = copy.deepcopy(inst)
    modulus = inst["group_order"]
    out["source_signature"] = _multiply_signature(
        inst["source_signature"], global_unit, modulus
    )
    out["target_signatures"] = [
        _multiply_signature(target, global_unit, modulus)
        for target in inst["target_signatures"]
    ]
    answer = list(inst["answer"])
    if target_permutation is not None:
        out["target_signatures"] = [out["target_signatures"][old] for old in target_permutation]
        answer[0] = target_permutation.index(answer[0])
    if reorder_seed is not None:
        rng = random.Random(reorder_seed)
        rng.shuffle(out["source_signature"])
        for target in out["target_signatures"]:
            rng.shuffle(target)
    out["answer"] = answer
    return out


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 101):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **shipping_params)
    target_index, unit, inverse = inst["answer"]
    corruptions = {
        "drop": [target_index, unit],
        "swap": [target_index, inverse, unit],
        "duplicate": [target_index, unit, unit],
        "empty": [],
        "out_of_range": [len(inst["target_signatures"]), unit, inverse],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(reasons) == len(set(reasons)),
        "cases": corruption_results,
    }

    realistic = (
        "The matching target and inverse check are exact.\n\n```text\n<answer>"
        + _answer_text(inst["answer"])
        + "</answer>\n```"
    )
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("No tagged answer is present.") is None
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage_none,
        "parsed": parsed,
        "garbage_returns_none": garbage_none,
    }

    samples = 200_000
    rng = random.Random(0x150407369)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, rng))[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform target index and uniform odd non-involutory unit; the inverse is filled in because the statement makes it free",
    }

    enumeration_start = time.perf_counter()
    exact_solution_count = enumerate_all(inst)
    enumeration_wall = time.perf_counter() - enumeration_start
    baseline_start = time.perf_counter()
    baseline_answer, baseline_stats = _reference_exhaustive(inst)
    baseline_wall = time.perf_counter() - baseline_start
    baseline_ok = baseline_answer is not None and verify(inst, baseline_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": exact_solution_count == 1 and baseline_ok,
        "shipping_exact_solution_count": exact_solution_count,
        "shipping_candidate_count": search_space(inst),
        "shipping_solution_fraction": exact_solution_count / search_space(inst),
        "enumeration_wall_seconds": round(enumeration_wall, 6),
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_candidates_tested": baseline_stats["candidates"],
        "baseline_modular_products": baseline_stats["modular_products"],
        "strongest_attack": "exhaustive unit-action search",
    }

    attack_results = {
        "outlier_2adic_rank_alignment": {"successes": 0, "attempts": 0},
        "greedy_smallest_modular_gap": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_single_sum_lift": {"successes": 0, "attempts": 0},
        "greedy_small_unit_scan_4095": {"successes": 0, "attempts": 0},
        "standard_unit_anchor_normalization": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_candidates = []
    reference_products = []
    compact_successes = 0
    compact_times = []
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_2adic_rank_alignment": _attack_v2_rank_alignment(attacked),
            "greedy_smallest_modular_gap": _attack_smallest_gap(attacked),
            "random_restart_256": _attack_random_restart(
                attacked, random.Random(seed ^ 0xA5A5), restarts=256
            ),
            "in_context_single_sum_lift": _attack_one_sum_lift(attacked),
            "greedy_small_unit_scan_4095": _attack_small_unit_scan(attacked),
            "standard_unit_anchor_normalization": _attack_unit_anchor(attacked),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if candidate is not None and verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        start = time.perf_counter()
        answer, stats = _reference_exhaustive(attacked)
        reference_times.append(time.perf_counter() - start)
        reference_candidates.append(stats["candidates"])
        reference_products.append(stats["modular_products"])
        if answer is not None and verify(attacked, answer)[0]:
            reference_successes += 1

        start = time.perf_counter()
        compact_answer, compact_stats = _compact_sum_solver(attacked)
        compact_times.append(time.perf_counter() - start)
        compact_operations.append(compact_stats["operations"])
        if compact_answer is not None and verify(attacked, compact_answer)[0]:
            compact_successes += 1

    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exhaustive unit-action search",
            "complexity": "O(h*2^n*r) exact modular products, h<=3 and r=8",
            "median_wall_clock_sec": round(statistics.median(reference_times), 6),
            "wall_clock_sec": round(statistics.median(reference_times), 6),
            "operations": int(statistics.median(reference_products)),
            "median_candidates": int(statistics.median(reference_candidates)),
            "median_modular_products": int(statistics.median(reference_products)),
            "operation_definition": "one product/reduction for every tested source entry, stopping a candidate at its first miss",
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "modular signature-sum invariant and eight lifts",
            "complexity": "O(h*r^2) with h<=3 and r=8",
            "median_wall_clock_sec": round(statistics.median(compact_times), 8),
            "operations": int(statistics.median(compact_operations)),
            "worst_case_operation_bound": 247,
            "operation_definition": "exact additions, gcd/inverse, lift formation, and modular products until a mismatch",
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * shipping_params["n"],
        target_count=shipping_params["target_count"],
        seed=77,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "fixed_answer_elements": len(doubled["answer"]),
    }

    invariance_checks = 0
    witness_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **shipping_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        permutation = list(range(len(original["target_signatures"])))
        random.Random(8000 + seed).shuffle(permutation)
        scale = random.Random(9000 + seed).randrange(1, original["group_order"], 2)
        variants = [
            _transform_instance(original, reorder_seed=10_000 + seed),
            _transform_instance(original, global_unit=scale),
            _transform_instance(original, target_permutation=permutation),
            _transform_instance(
                original,
                global_unit=scale,
                target_permutation=list(reversed(permutation)),
                reorder_seed=11_000 + seed,
            ),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                failures.append([seed, "key changed"])
            witness_checks += 1
            if not verify(variant, variant["answer"])[0]:
                failures.append([seed, "carried witness failed"])
    report["G8_canonical_key"] = {
        "pass": not failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": failures,
        "symmetries": "reordering either multiset, permuting target signatures, a global unit automorphism, and their compositions",
        "key_basis": "minimum unit-normalized source/target form; never the seed or rendered text",
    }

    # Worst-width legal fields at shipping size; brackets and commas are included.
    size = _answer_size(
        [shipping_params["target_count"] - 1, inst["group_order"] - 1, inst["group_order"] - 1]
    )
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    operation_bound = 247
    within_caps = size["chars"] <= 2000 and size["elements"] <= 256 and operation_bound <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "intended_route_operations": operation_bound,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
