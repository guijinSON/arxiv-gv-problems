"""Verified affine arc-structure isomorphism generator for arXiv:2302.13657.

The paper's Section 6.2 defines the arc-structure Pultr functor.  This module
uses the fact, stated immediately before Definition 6.1 and instantiated in
Section 6.2, that a digraph homomorphism induces a homomorphism of the
corresponding arc structures.
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
from collections import Counter


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The finite-field sum of a step set is covariant under multiplicative relabelling."
)
PLACEBO_HINT: str = (
    "The displayed residue lists are sets, so their written order carries no significance."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "cyclic Cayley digraph over a prime field",
        "arc structure with the paper's D, I, and O incidence relations",
        "six-coefficient affine map on arc coordinates",
    ],
    "verification_operations": [
        "exact prime-field multiplication and addition",
        "finite-set equality of edge-step residues",
        "coefficient propagation from the D, I, and O incidence equalities",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Use the arc-incidence equalities to identify the common scale and recognize "
        "a field-valued step-set statistic that transforms by it; without this, "
        "compare candidate affine arc maps one multiplier at a time."
    ),
    "hardness_basis": (
        "Track B: the domain-standard anchor-image enumeration is an O(m^2) exact "
        "affine Cayley-isomorphism algorithm; at hard (m=120) its eight-seed median "
        "is 5,389 counted operations and about 0.0003 seconds, while the "
        "covariant-sum route uses exactly 242 counted operations and its relevance "
        "must be discovered without computational tools."
    ),
    "max_answer_tokens": 8,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY: dict = {
    "demo": {"n": 11, "step_count": 5},
    "easy": {"n": 2_000_000, "step_count": 60},
    "medium": {"n": 3_000_000, "step_count": 90},
    "hard": {"n": 5_000_000, "step_count": 120},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An ambient affine arc-coordinate map (x,s) -> (a*x+c*s+b,d*x+e*s+f), "
        "encoded as six canonical integers [a,c,b,d,e,f].  The structure-aware "
        "language incorporates the coefficient equalities forced directly by D, I, "
        "and O, so candidates have form [u,0,b,0,u,0] with 1 <= u < p and 0 <= b < p."
    ),
    "bounds": {
        "atomic_elements": 6,
        "named_preset_modulus_max": 5_000_161,
        "multiplier_choices_max_at_named_presets": 5_000_160,
        "translation_choices_max_at_named_presets": 5_000_161,
        "coefficient_bits_max_at_named_presets": 23,
    },
}

NOTES: str = (
    "Definition 2.2 fixes homomorphisms as relation-preserving maps. Definition 2.8 "
    "fixes central Pultr functors, and Section 6 (immediately before Definition 6.1) "
    "states that a homomorphism h induces h^S between the functor images. Section 6.2 "
    "defines the native arc structure: its vertices are arcs, and D, I, O record "
    "consecutivity, common head, and common tail. Theorem 6.3 supplies the surrounding "
    "right-adjoint construction, but it does not claim that finding arbitrary "
    "homomorphisms is hard; consequently a Track A claim would be unsupported. This "
    "generator instead transforms a known cyclic Cayley digraph isomorphism through "
    "the arc-structure functor. The answer is an ambient affine map on arc coordinates; "
    "arc-set membership and the D, I, and O relations force its six coefficients to "
    "the induced-map form. The "
    "exact reference algorithm then enumerates the image of one step and checks each "
    "resulting multiplier. Step sets are a checksum-normalised "
    "multiplicative subgroup with one deletion and one insertion, creating many "
    "near-symmetries without distinguishing the planted multiplier. The source sum is "
    "one, so covariance of the set sum breaks every residual multiplier symmetry and "
    "gives the short Track B route. "
    "Minimum-residue alignment, sorted greedy alignment, additive translation, small "
    "multipliers, and random restarts are tested separately."
)


# Official results from the bare shipping rung and the two isolated G9 runs.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
    "infrastructure_errors": {"bare": 0, "hinted": 0, "placebo": 0},
}


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin for all unsigned 64-bit integers."""
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


def _compatible_prime(lower_bound: int, step_count: int) -> int:
    """Smallest prime p >= lower_bound with step_count dividing p-1."""
    start = max(int(lower_bound), step_count + 1, 3)
    candidate = ((start - 1 + step_count - 1) // step_count) * step_count + 1
    while not _is_prime_64(candidate):
        candidate += step_count
    return candidate


def _prime_factors(value: int) -> tuple[int, ...]:
    factors = []
    divisor = 2
    remaining = value
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            factors.append(divisor)
            while remaining % divisor == 0:
                remaining //= divisor
        divisor += 1
    if remaining > 1:
        factors.append(remaining)
    return tuple(factors)


def _element_of_exact_order(p: int, order: int, rng: random.Random) -> int:
    exponent = (p - 1) // order
    factors = _prime_factors(order)
    while True:
        candidate = pow(rng.randrange(2, p), exponent, p)
        if candidate != 1 and all(
            pow(candidate, order // prime, p) != 1 for prime in factors
        ):
            return candidate


def make_instance(n, seed=0, **params) -> dict:
    """Transform a known affine digraph isomorphism through the arc functor.

    The certificate is sampled first.  No homomorphism search is performed.
    """
    step_count = int(params.get("step_count", 60))
    if not 3 <= step_count <= 150:
        raise ValueError("step_count must lie between 3 and 150")
    p = _compatible_prime(int(n), step_count)
    rng = random.Random(seed)

    generator = _element_of_exact_order(p, step_count, rng)
    subgroup = []
    value = 1
    for _ in range(step_count):
        subgroup.append(value)
        value = value * generator % p
    subgroup_set = set(subgroup)
    if len(subgroup_set) != step_count:
        raise AssertionError("subgroup construction did not have the requested order")

    removed = rng.choice(subgroup)
    inserted = rng.randrange(1, p)
    while inserted in subgroup_set:
        inserted = rng.randrange(1, p)
    base_steps = (subgroup_set - {removed}) | {inserted}
    # The subgroup sum is zero, so the one-point perturbation has sum
    # inserted-removed != 0.  Scale it to make the public source checksum one.
    # This keeps the intended no-tool route below the G9 arithmetic cap without
    # revealing the planted multiplier or solving the instance.
    base_sum = (inserted - removed) % p
    source_scale = pow(base_sum, -1, p)
    source_steps = sorted(source_scale * step % p for step in base_steps)

    # These coefficients determine the certificate and are sampled before the
    # target is built.  The induced map has matrix diag(multiplier, multiplier).
    multiplier = rng.randrange(1, p)
    translation = rng.randrange(p)
    target_steps = sorted(multiplier * step % p for step in source_steps)

    if sum(source_steps) % p != 1:
        raise AssertionError("normalised one-point perturbation should have sum one")
    return {
        "n": int(n),
        "p": p,
        "step_count": step_count,
        "source_steps": source_steps,
        "target_steps": target_steps,
        "answer": [multiplier, 0, translation, 0, multiplier, 0],
    }


def render(inst) -> str:
    """Render a self-contained affine homomorphism problem."""
    p = inst["p"]
    source = ", ".join(str(x) for x in inst["source_steps"])
    target = ", ".join(str(x) for x in inst["target_steps"])
    statement = f"""Affine isomorphism of arc structures over a prime field

All arithmetic below is modulo the prime p = {p}, using canonical residues
0,1,...,p-1.  The displayed lists are unordered sets: they contain distinct,
nonzero residues, and their written order has no meaning.

For a step set S, define the cyclic Cayley digraph G(S).  Its vertices are the
residues x in F_p.  For every x and every s in S it has the directed arc
x -> x+s.  Write that arc as the pair (x,s).

The arc structure A(S) is a relational structure whose vertices are all arcs
(x,s) of G(S), with three binary relations:

  D((x,s),(y,t)) holds exactly when x+s = y       (consecutive arcs);
  I((x,s),(y,t)) holds exactly when x+s = y+t     (the same head);
  O((x,s),(y,t)) holds exactly when x = y         (the same tail).

Source step set S = [{source}]
Target step set T = [{target}]

Find six canonical residues a,c,b,d,e,f in {{0,...,p-1}} such that the affine rule

  Phi(x,s) = (a*x+c*s+b mod p, d*x+e*s+f mod p)

is a bijective homomorphism from A(S) to A(T): it must send every source arc to
a target arc and preserve all three relations D, I, and O.  Its 2-by-2 linear
part must be invertible modulo p.  The six coefficients are the complete finite
description of Phi; do not list its p*|S| values.  Coefficients are ordered
exactly as a,c,b,d,e,f; order matters and no coefficient may be omitted.

Give your final answer inside <answer></answer> tags, as six base-10 integers
a, c, b, d, e, f separated by commas.  Example: <answer>3, 0, 7, 0, 3, 0</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _answer_text(answer) -> str:
    return ", ".join(str(value) for value in answer)


def parse_answer(text) -> object | None:
    """Parse the tagged pair, tolerating prose and Markdown around it."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    bodies = tagged[-1:] if tagged else []
    if not bodies:
        fenced = re.findall(r"```(?:text|json|python)?\s*(.*?)```", text, re.I | re.S)
        bodies = fenced[-1:] if fenced else [text]
    body = bodies[0].strip()
    body = re.sub(r"^\s*[\[\(]\s*|\s*[\]\)]\s*$", "", body)
    number = r"([+-]?\d+)"
    match = re.fullmatch(r"\s*" + r"\s*,\s*".join([number] * 6) + r"\s*", body)
    if not match:
        # Untagged model replies often put the final tuple on one plain line.
        matches = re.findall(
            r"(?m)^\s*(?:final(?:\s+answer)?\s*:\s*)?[\[\(]?\s*"
            + r"\s*,\s*".join([number] * 6)
            + r"\s*[\]\)]?\s*$",
            body,
            re.I,
        )
        if not matches:
            return None
        match_values = matches[-1]
        return [int(value) for value in match_values]
    return [int(value) for value in match.groups()]


def verify(inst, answer) -> tuple[bool, str]:
    """Check any affine arc-structure isomorphism; never inspect inst['answer']."""
    if answer is None:
        return False, "answer is absent or malformed"
    if not isinstance(answer, list):
        return False, "answer must be a six-integer list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) < 6:
        return False, "answer is missing one or more affine coefficients"
    if len(answer) > 6:
        return False, "answer has extra fields"
    if any(type(value) is not int for value in answer):
        return False, "all six affine coefficients must be exact integers"
    a, c, b, d, e, f = answer
    p = inst["p"]
    if any(not 0 <= value < p for value in answer):
        return False, "an affine coefficient is outside the canonical field range"
    if (a * e - c * d) % p == 0:
        return False, "the 2-by-2 linear part is singular"

    # Since |T| < p, the second output coordinate cannot depend on x: if d
    # were nonzero, varying x would make it attain every field element rather
    # than stay in T.  With d=0, exact step-set membership is e*S+f=T.
    if d != 0:
        return False, "the step coordinate depends on the tail and leaves T"
    image_steps = {((e * step) + f) % p for step in inst["source_steps"]}
    target_steps = set(inst["target_steps"])
    if image_steps != target_steps:
        missing = len(target_steps - image_steps)
        extra = len(image_steps - target_steps)
        return False, f"the affine map sends steps to the wrong set ({missing} missing, {extra} extra)"

    # O relates every pair of arcs with the same tail.  Because S has at least
    # two distinct steps, preservation of O is equivalent to c=0.
    if c != 0:
        return False, "the map does not preserve the common-tail relation O"

    # With c=d=0, preservation of D for every consecutive pair is equivalent
    # to (e-a)*s+f=0 for every s in S.  Distinct steps force e=a and f=0.
    if e != a:
        return False, "the map does not use one common scale for D, I, and O"
    if f != 0:
        return False, "the map does not preserve the consecutive-arc relation D"

    # Now Phi(x,s)=(a*x+b,a*s), with a nonzero.  Exactly and universally:
    # D: x+s=y => ax+b+as=ay+b; I: x+s=y+t => transformed heads
    # agree; O: x=y => transformed tails agree.  The inverse has the same
    # form, so Phi is bijective on arcs.  No p*m enumeration or floats occur.
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample after the directly forced D/I/O coefficient rules."""
    u = rng.randrange(1, inst["p"])
    b = rng.randrange(inst["p"])
    return [u, 0, b, 0, u, 0]


def search_space(inst) -> int | None:
    return (inst["p"] - 1) * inst["p"]


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 20_000:
        return None
    total = 0
    for u in range(1, inst["p"]):
        for b in range(inst["p"]):
            if verify(inst, [u, 0, b, 0, u, 0])[0]:
                total += 1
    return total


def _normalised_steps(steps, p: int) -> tuple[int, ...]:
    """Canonical representative under multiplication by F_p^*."""
    values = tuple(sorted(set(steps)))
    candidates = []
    for anchor in values:
        inverse = pow(anchor, -1, p)
        candidates.append(tuple(sorted(inverse * value % p for value in values)))
    return min(candidates)


def canonical_key(inst) -> str:
    """Key modulo input order and independent affine relabellings."""
    payload = [
        "cyclic-arc-structure-affine-isomorphism",
        inst["p"],
        inst["step_count"],
        _normalised_steps(inst["source_steps"], inst["p"]),
        _normalised_steps(inst["target_steps"], inst["p"]),
    ]
    raw = json.dumps(payload, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow field size and near-symmetry crowding at fixed certificate length."""
    out = dict(params)
    out["n"] = int(params["n"]) * 2
    out["step_count"] = min(149, int(params.get("step_count", 60)) + 3)
    return out


def _compact_sum_solver(inst):
    """The intended Track B invariant route, independent of the planted answer."""
    p = inst["p"]
    source_sum = sum(inst["source_steps"]) % p
    target_sum = sum(inst["target_steps"]) % p
    if source_sum != 1:
        return None, {"operations": 2 * (inst["step_count"] - 1) + 4}
    u = target_sum
    return [u, 0, 0, 0, u, 0], {
        "operations": 2 * (inst["step_count"] - 1) + 4,
        "field_additions": 2 * (inst["step_count"] - 1),
        "field_inversions": 0,
        "field_multiplications": 0,
        "relation_coefficient_implications": 4,
    }


def _reference_anchor_enumeration(inst):
    """Natural exact affine-isomorphism solver: enumerate one anchor's image."""
    p = inst["p"]
    source = inst["source_steps"]
    target = inst["target_steps"]
    target_set = set(target)
    anchor_inverse = pow(source[0], -1, p)
    # Four coefficient implications (d=0,c=0,e=a,f=0), then one anchor inverse.
    operations = 5
    candidates = 0
    for image in target:
        candidates += 1
        u = image * anchor_inverse % p
        operations += 1
        transformed = {u * step % p for step in source}
        operations += len(source)
        if transformed == target_set:
            return [u, 0, 0, 0, u, 0], {
                "operations": operations,
                "candidate_multipliers": candidates,
                "step_transforms": candidates * len(source),
            }
    return None, {
        "operations": operations,
        "candidate_multipliers": candidates,
        "step_transforms": candidates * len(source),
    }


def _attack_outlier_minimum(inst):
    p = inst["p"]
    u = inst["target_steps"][0] * pow(inst["source_steps"][0], -1, p) % p
    return [u, 0, 0, 0, u, 0]


def _attack_greedy_sorted_alignment(inst):
    p = inst["p"]
    ratios = [
        target * pow(source, -1, p) % p
        for source, target in zip(inst["source_steps"], inst["target_steps"])
    ]
    u = Counter(ratios).most_common(1)[0][0]
    return [u, 0, 0, 0, u, 0]


def _attack_additive_translation(inst):
    # Translation changes vertex labels but cannot change Cayley step differences.
    b = (inst["target_steps"][0] - inst["source_steps"][0]) % inst["p"]
    return [1, 0, b, 0, 1, 0]


def _attack_small_multipliers(inst, radius=16):
    candidates = list(range(1, radius + 1))
    candidates += [inst["p"] - value for value in range(1, radius + 1)]
    last = [1, 0, 0, 0, 1, 0]
    for u in candidates:
        last = [u, 0, 0, 0, u, 0]
        if verify(inst, last)[0]:
            return last
    return last


def _attack_random_restarts(inst, rng, restarts=4096):
    last = [1, 0, 0, 0, 1, 0]
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _affine_relabel_instance(
    inst, source_scale=1, target_scale=1, source_translation=0,
    target_translation=0, reorder=False, rng=None
):
    """Apply independent affine relabellings and carry the certificate."""
    out = copy.deepcopy(inst)
    p = inst["p"]
    source_scale %= p
    target_scale %= p
    if source_scale == 0 or target_scale == 0:
        raise ValueError("relabeling scales must be nonzero")
    out["source_steps"] = [source_scale * x % p for x in inst["source_steps"]]
    out["target_steps"] = [target_scale * x % p for x in inst["target_steps"]]
    u, _, b, _, _, _ = inst["answer"]
    carried_u = target_scale * u * pow(source_scale, -1, p) % p
    carried_b = (
        target_scale * b + target_translation - carried_u * source_translation
    ) % p
    out["answer"] = [carried_u, 0, carried_b, 0, carried_u, 0]
    if reorder:
        if rng is None:
            rng = random.Random(0)
        rng.shuffle(out["source_steps"])
        rng.shuffle(out["target_steps"])
    return out


def _swap_source_target(inst):
    """Reverse the isomorphism problem and carry the inverse affine map."""
    out = copy.deepcopy(inst)
    out["source_steps"], out["target_steps"] = (
        list(inst["target_steps"]),
        list(inst["source_steps"]),
    )
    p = inst["p"]
    u, _, b, _, _, _ = inst["answer"]
    inverse_u = pow(u, -1, p)
    inverse_b = (-inverse_u * b) % p
    out["answer"] = [inverse_u, 0, inverse_b, 0, inverse_u, 0]
    return out


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def _worst_answer_size(inst):
    """Exact worst case in the bounded, structure-aware language at fixed p."""
    top = inst["p"] - 1
    return _answer_size([top, 0, top, 0, top, 0])


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    corruptions = {
        "drop": answer[:-1],
        "swap": [answer[1], answer[0], *answer[2:]],
        "duplicate": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [answer[0], answer[1], inst["p"], *answer[3:]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [result["reason"] for result in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(result["rejected"] for result in corruption_results.values())
        and len(reasons) == len(set(reasons)),
        "cases": corruption_results,
    }

    realistic = (
        "The induced map preserves common heads and tails.\n\n"
        "```text\n<answer>" + _answer_text(answer) + "</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no numerical answer here") is None,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("no numerical answer here") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x230213657)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    exact_probability = 1.0 / (inst["p"] - 1)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and exact_probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": exact_probability,
        "structure_aware_space": search_space(inst),
        "sampler": (
            "uniform over all nonzero multipliers and all translations; coefficient "
            "ranges and the relation-forced affine shape are enforced before sampling"
        ),
    }

    attack_results = {
        "outlier_minimum_residue_alignment": {"successes": 0, "attempts": 0},
        "greedy_sorted_alignment_mode": {"successes": 0, "attempts": 0},
        "random_restart_4096_affine_maps": {"successes": 0, "attempts": 0},
        "in_context_additive_translation_ansatz": {"successes": 0, "attempts": 0},
        "in_context_small_multiplier_pm16": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_walls = []
    reference_operations = []
    reference_candidates = []
    reference_step_transforms = []
    compact_successes = 0
    compact_walls = []
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_minimum_residue_alignment": _attack_outlier_minimum(attacked),
            "greedy_sorted_alignment_mode": _attack_greedy_sorted_alignment(attacked),
            "random_restart_4096_affine_maps": _attack_random_restarts(
                attacked, random.Random(seed ^ 0xA5A5), restarts=4096
            ),
            "in_context_additive_translation_ansatz": _attack_additive_translation(attacked),
            "in_context_small_multiplier_pm16": _attack_small_multipliers(attacked, radius=16),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        started = time.perf_counter()
        reference_answer, stats = _reference_anchor_enumeration(attacked)
        reference_walls.append(time.perf_counter() - started)
        reference_operations.append(stats["operations"])
        reference_candidates.append(stats["candidate_multipliers"])
        reference_step_transforms.append(stats["step_transforms"])
        if reference_answer is not None and verify(attacked, reference_answer)[0]:
            reference_successes += 1

        started = time.perf_counter()
        compact_answer, compact_stats = _compact_sum_solver(attacked)
        compact_walls.append(time.perf_counter() - started)
        compact_operations.append(compact_stats["operations"])
        if compact_answer is not None and verify(attacked, compact_answer)[0]:
            compact_successes += 1

    all_attacks_failed = all(
        result["successes"] == 0 for result in attack_results.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "anchor-image enumeration for affine Cayley digraph isomorphism",
            "complexity": "O(m^2) exact field operations with hashed set equality",
            "median_wall_clock_sec": round(statistics.median(reference_walls), 8),
            "operations": int(statistics.median(reference_operations)),
            "median_candidate_multipliers": int(statistics.median(reference_candidates)),
            "median_step_transforms": int(statistics.median(reference_step_transforms)),
            "operation_definition": (
                "four relation-coefficient implications and one field inversion, "
                "then field multiplications used to form each candidate image"
            ),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "covariant nonzero step-set sum",
            "complexity": "O(m) exact field operations",
            "median_wall_clock_sec": round(statistics.median(compact_walls), 8),
            "operations": int(statistics.median(compact_operations)),
            "operation_definition": (
                "four relation-coefficient implications plus 2(m-1) modular "
                "additions; sum(S)=1 by construction"
            ),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference = report["G6_adversary_panel"]["reference_algorithm"]
    report["G5_density_and_baseline"] = {
        "pass": exact_probability < 1e-6 and reference_successes == 8
        and demo_count == demo["p"],
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_exact_valid_answer_count": inst["p"],
        "shipping_exact_solution_fraction": exact_probability,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": reference["median_wall_clock_sec"],
        "baseline_exact_operations": reference["operations"],
        "baseline_candidate_multipliers": reference["median_candidate_multipliers"],
    }

    doubled_params = {
        "n": 2 * int(ship_params["n"]),
        "step_count": int(ship_params["step_count"]),
    }
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["p"] > inst["p"]
        and search_space(doubled) > search_space(inst),
        "shipping_requested_n": ship_params["n"],
        "shipping_prime": inst["p"],
        "doubled_requested_n": doubled_params["n"],
        "doubled_prime": doubled["p"],
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "answer_elements_unchanged": len(doubled["answer"]) == len(inst["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    witness_checks = 0
    key_failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **ship_params)
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        rng = random.Random(8000 + seed)
        p = original["p"]
        a = rng.randrange(1, p)
        c = rng.randrange(1, p)
        r = rng.randrange(p)
        q = rng.randrange(p)
        reordered = _affine_relabel_instance(original, reorder=True, rng=rng)
        scaled = _affine_relabel_instance(
            original, source_scale=a, target_scale=c,
            source_translation=r, target_translation=q
        )
        translated = _affine_relabel_instance(
            original, source_translation=r, target_translation=q
        )
        composed = _affine_relabel_instance(
            original, source_scale=a, target_scale=c,
            source_translation=r, target_translation=q, reorder=True, rng=rng
        )
        swapped = _swap_source_target(original)
        for variant in (reordered, scaled, translated, composed, swapped):
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                key_failures.append([seed, "key changed under an affine relabelling"])
            witness_checks += 1
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                key_failures.append([seed, "carried witness failed: " + reason])
    report["G8_canonical_key"] = {
        "pass": not key_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": key_failures,
        "symmetries": (
            "independent affine relabellings of source and target vertices, input-list "
            "reordering, translations, reversal with the inverse map, and compositions"
        ),
        "key_basis": (
            "SHA-256 of p, m, and the lexicographically minimal multiplier-normal "
            "forms of both step sets; neither seed nor rendering is included"
        ),
    }

    size = _worst_answer_size(inst)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    )
    hinted_rate = (
        arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    )
    arms_complete = all(entry["attempts"] >= 3 for entry in arms.values())
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    intended_operations = 2 * (inst["step_count"] - 1) + 4
    within_caps = (
        size["chars"] <= 2000
        and size["elements"] <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the oracle arms are diagnostic only.  G9(c), the
        # answer/effort caps, is the sole gated part of G9.
        "pass": within_caps,
        "arms": arms,
        "infrastructure_errors": copy.deepcopy(
            G9_RESULTS.get("infrastructure_errors", {})
        ),
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "diagnostic_complete": arms_complete,
        "hinted_still_hardened": hinted_hardened,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
