"""Inverse-generated affine isomorphisms of split binary forms over F_p.

The native problem is the Polynomial Isomorphism Search Problem from Section 8
of arXiv:2511.06843.  Each panel contains two degree-d homogeneous binary
forms.  The second is obtained from the first by an invertible affine linear
change of the two variables, so the witness is known before either expanded
coefficient vector is emitted.

The module is deterministic in ``(n, seed, params)``, uses only the standard
library, performs no file I/O, and prints nothing on import.
"""

from __future__ import annotations

import copy
import hashlib
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
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "homogeneous binary polynomials over a prime field",
        "invertible 2 by 2 change-of-variables matrices",
    ],
    "verification_operations": [
        "finite-field matrix normalization",
        "exact binomial substitution",
        "coefficient-vector equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The ratio of the third to second centered power sum of the projective "
        "roots scales exactly like the hidden affine coordinate; without this "
        "covariant, one factors the forms and aligns two large root sets."
    ),
    "hardness_basis": (
        "Track B: Cantor-Zassenhaus finite-field factorization followed by "
        "affine root-set alignment has expected polynomial complexity in d and "
        "log(p), with O(d^3) elementary alignment; at the intended hard preset the "
        "standard-library specialization averaged 1,427,306 field operations "
        "and 0.03--0.67 s across recorded runs, whereas the centered-moment route "
        "uses at most 280 "
        "exact operations across four panels, including inversions."
    ),
    "max_answer_tokens": 24,
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
    "demo": {"n": 5, "prime": 17, "panels": 1},
    "easy": {"n": 40, "prime": 1009, "panels": 2},
    "medium": {"n": 60, "prime": 1009, "panels": 3},
    "hard": {"n": 80, "prime": 1009, "panels": 4},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The ratio of the third to second centered root moments is covariant under "
    "the promised affine change."
)
PLACEBO_HINT = (
    "The ordering of the displayed coefficient vectors deserves careful attention "
    "throughout each panel of this finite-field problem."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object containing one normalized affine matrix "
        "[[1,-beta],[0,alpha]] over F_p per displayed panel, with "
        "alpha in {1,...,p-1} and beta in F_p."
    ),
    "bounds": {
        "matrix_rows": 2,
        "matrix_columns": 2,
        "top_left": 1,
        "bottom_left": 0,
        "alpha_min": 1,
        "alpha_max": "prime-1",
        "beta_range": "F_p",
        "max_panels": 32,
    },
}

# These are diagnostics, not local gates.  They are populated only after the
# three harness runs finish at the shipping preset.  OpenRouter quota currently
# prevents a complete arm, so the zero-attempt values are deliberately honest.
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_external",
}

NOTES = r"""
Paper grounding and STEP 0.  Section 8 defines Polynomial Isomorphism over
F_q exactly as the search for A in GL_k(F_q) satisfying (A*f)(x)=f(Ax)=g(x).
This generator takes k=2 and stays in those native objects: it emits expanded
homogeneous binary forms and asks for the actual 2 by 2 matrix.  No graph,
finite-field surrogate, or decision-only reformulation is used.  Proposition
7.4 supplies equivariance of homogeneous linear changes, and Theorem 8.1 uses
the same action in the paper's PSE-to-PI reduction.

What makes the source problem easy.  The Introduction says that cubic IP1S has
been extensively cryptanalysed, and Section 10 says PI is believed efficiently
solvable in the vast majority of cases.  The paper also makes clear that LCE
has unresolved precise complexity, is not known NP-hard in the needed sense,
and has structural attacks in small-hull regimes.  Consequently this module
makes no Track-A or average-case hardness claim.  It is Track B and explicitly
runs a mechanical finite-field root recovery and affine alignment algorithm.

Certificate production.  Generation samples a set R of d distinct elements
of F_p and expands F(x,y)=product_{r in R}(x-r*y).  It then samples nonzero
alpha and beta and forms S={alpha*r+beta:r in R}.  Thus

  G(x,y) = product_s (x-s*y) = F(x-beta*y, alpha*y),

so [[1,-beta],[0,alpha]] is known by composition of identities, never by
solving an emitted instance.  Verification independently performs that exact
binomial substitution and compares every coefficient.

Mechanical and compact costs.  The reference route finds every root by exact
evaluation over F_p and aligns the two recovered sets by trying ordered root
pairs.  General finite-field factorization replaces exhaustive evaluation and
is polynomial in d and log(p); the elementary alignment is O(d^3).  The
shipping reference operation count and wall time are measured in selftest.
For the compact route, Newton identities recover the first three root power
sums from the first three coefficients.  If m, C2, C3 denote the mean and the
second and third centered sums, then under s=alpha*r+beta one has
C2'=alpha^2*C2 and C3'=alpha^3*C3.  Hence C3/C2 carries alpha and the means
carry beta.  This takes at most 28 field operations per panel, including the
small fixed number of inversions.  Counting modular inverses by binary
square-and-multiply gives at most 70 operations per panel, and four hard-preset
panels use at most 280 operations.

Attack hardening.  Root sets are uniform samples without any planted-versus-
decoy distinction.  The hidden scale and translation are uniform on their
nontrivial supports (scale 2..p-1 and translation 1..p-1), while random
restarts conservatively sample the full affine language stated to the solver.
Translation-only, scale-only, raw-coefficient, and uncentered-moment guesses
all fail because every panel has an independent nonzero translation and
nontrivial scale.  The successful factor-and-align reference algorithm is
reported separately, as Track B requires.
"""


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _inv(value: int, prime: int) -> int:
    value %= prime
    if value == 0:
        raise ValueError("zero has no inverse")
    return pow(value, prime - 2, prime)


def _poly_from_roots(roots: list[int], prime: int) -> list[int]:
    """Coefficients [c_0,...,c_d] of product (x-r*y), c_0=1."""
    coeffs = [1]
    for root in roots:
        old = coeffs
        coeffs = [0] * (len(old) + 1)
        coeffs[0] = old[0]
        for index in range(1, len(coeffs)):
            keep = old[index] if index < len(old) else 0
            coeffs[index] = (keep - root * old[index - 1]) % prime
    return coeffs


def _power_sums(coeffs: list[int], count: int, prime: int) -> list[int]:
    """Newton sums p_0,...,p_count of a monic split polynomial."""
    degree = len(coeffs) - 1
    sums = [degree % prime]
    for order in range(1, count + 1):
        total = order * coeffs[order]
        for index in range(1, order):
            total += coeffs[index] * sums[order - index]
        sums.append((-total) % prime)
    return sums


def _moments(coeffs: list[int], prime: int) -> tuple[int, int, int]:
    degree = len(coeffs) - 1
    if degree < 3 or degree >= prime:
        raise ValueError("moment route requires 3 <= degree < prime")
    pows = _power_sums(coeffs, 3, prime)
    degree_inv = _inv(degree, prime)
    mean = pows[1] * degree_inv % prime
    centered2 = (pows[2] - pows[1] * pows[1] * degree_inv) % prime
    centered3 = (
        pows[3]
        - 3 * pows[1] * pows[2] * degree_inv
        + 2 * pow(pows[1], 3, prime) * degree_inv * degree_inv
    ) % prime
    return mean, centered2, centered3


def _recover_affine(source: list[int], target: list[int], prime: int) -> tuple[int, int]:
    mean, centered2, centered3 = _moments(source, prime)
    mean2, centered2b, centered3b = _moments(target, prime)
    if centered2 == 0 or centered3 == 0 or centered2b == 0:
        raise ValueError("degenerate centered moments")
    alpha = (
        centered3b * centered2 * _inv(centered2b * centered3, prime)
    ) % prime
    beta = (mean2 - alpha * mean) % prime
    return alpha, beta


def _transform_coeffs(
    coeffs: list[int], alpha: int, beta: int, prime: int, limit: int | None = None
) -> list[int]:
    """Coefficients of F(x-beta*y, alpha*y), optionally through an index."""
    degree = len(coeffs) - 1
    last = degree if limit is None else min(degree, limit)
    output = [0] * (last + 1)
    neg_beta = (-beta) % prime
    alpha_power = 1
    for index in range(last + 1):
        coefficient = coeffs[index] * alpha_power % prime
        beta_power = 1
        max_shift = last - index
        for shift in range(max_shift + 1):
            output[index + shift] = (
                output[index + shift]
                + coefficient
                * (math.comb(degree - index, shift) % prime)
                * beta_power
            ) % prime
            beta_power = beta_power * neg_beta % prime
        alpha_power = alpha_power * alpha % prime
    return output


def _matrix(alpha: int, beta: int, prime: int) -> list[list[int]]:
    return [[1, (-beta) % prime], [0, alpha % prime]]


def _decode_matrix(value: Any, prime: int, index: int) -> tuple[int, int] | tuple[None, str]:
    if not (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(row, list) and len(row) == 2 for row in value)
    ):
        return None, f"matrix {index} must have shape 2 by 2"
    entries = [value[0][0], value[0][1], value[1][0], value[1][1]]
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in entries):
        return None, f"matrix {index} entries must be integers"
    if not all(0 <= item < prime for item in entries):
        return None, f"matrix {index} has an entry outside 0..{prime - 1}"
    if value[0][0] != 1 or value[1][0] != 0:
        return None, f"matrix {index} is not in normalized affine form"
    if value[1][1] == 0:
        return None, f"matrix {index} is singular"
    return value[1][1], (-value[0][1]) % prime


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Construct split binary forms and their known affine PI witnesses."""
    prime = int(params.get("prime", 1009))
    panels = int(params.get("panels", 8))
    n = int(n)
    if not _is_prime(prime):
        raise ValueError("prime must be prime")
    if not (5 <= n < prime):
        raise ValueError("n must satisfy 5 <= n < prime")
    if not (1 <= panels <= CERTIFICATE_LANGUAGE["bounds"]["max_panels"]):
        raise ValueError("panels out of bounds")

    rng = random.Random(seed)
    panel_data = []
    matrices = []
    for _panel_index in range(panels):
        for _attempt in range(10_000):
            roots = sorted(rng.sample(range(prime), n))
            source = _poly_from_roots(roots, prime)
            _mean, centered2, centered3 = _moments(source, prime)
            if centered2 != 0 and centered3 != 0:
                break
        else:
            raise RuntimeError("could not sample nondegenerate root moments")

        alpha = rng.randrange(2, prime)
        beta = rng.randrange(1, prime)
        target_roots = sorted((alpha * root + beta) % prime for root in roots)
        target = _poly_from_roots(target_roots, prime)
        panel_data.append({"source": source, "target": target})
        matrices.append(_matrix(alpha, beta, prime))

    return {
        "family": "affine_isomorphism_of_split_binary_forms",
        "prime": prime,
        "degree": n,
        "panel_count": panels,
        "panels": panel_data,
        "answer": {"matrices": matrices},
    }


def render(inst: dict) -> str:
    prime = inst["prime"]
    degree = inst["degree"]
    lines = [
        "Polynomial Isomorphism Search over a prime field (batched).",
        "",
        f"All arithmetic is in F_{prime}: reduce every integer modulo {prime}.",
        f"Each panel gives two homogeneous binary forms F(x,y), G(x,y) of degree {degree}.",
        "A displayed vector [c0,c1,...,cd] means exactly",
        "  c0*x^d + c1*x^(d-1)*y + ... + cd*y^d.",
        "Every displayed coefficient is the canonical integer in 0..p-1.",
        "",
        "For each panel, find a normalized affine change-of-variables matrix",
        "  A = [[1, u], [0, a]] with 0 <= u < p and 1 <= a < p",
        "such that F(A*[x,y]^T) = F(x+u*y, a*y) equals G(x,y)",
        "coefficient by coefficient in F_p.  A solution is guaranteed for every",
        "panel.  The panels are ordered, and your matrices must follow Panel 1,",
        "Panel 2, and so on in that order.  The same field element may appear more",
        "than once inside a matrix; no floating point or integer equality is intended.",
        "",
    ]
    for index, panel in enumerate(inst["panels"], 1):
        lines.append(f"Panel {index}")
        lines.append("F: " + json.dumps(panel["source"], separators=(",", ":")))
        lines.append("G: " + json.dumps(panel["target"], separators=(",", ":")))
        lines.append("")
    lines.extend(
        [
            "Output one JSON object with exactly one 2x2 matrix per panel:",
            '{"matrices":[[[1,u1],[0,a1]],[[1,u2],[0,a2]],...]}.',
            "Use ordinary base-10 integers in 0..p-1 and no ellipses.",
            "Give your final answer inside <answer></answer> tags, as that exact JSON object.",
            'Example: <answer>{"matrices":[[[1,3],[0,5]]]}</answer>',
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
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, flags=re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"matrices"} or not isinstance(answer["matrices"], list):
        return False, "answer must contain only a matrices list"
    matrices = answer["matrices"]
    if len(matrices) != inst["panel_count"]:
        return False, f"wrong matrix count: expected {inst['panel_count']}"
    prime = inst["prime"]
    for index, (panel, matrix_value) in enumerate(zip(inst["panels"], matrices)):
        decoded = _decode_matrix(matrix_value, prime, index)
        if decoded[0] is None:
            return False, decoded[1]
        alpha, beta = decoded
        prefix_limit = min(3, inst["degree"])
        prefix = _transform_coeffs(
            panel["source"], alpha, beta, prime, prefix_limit
        )
        target_prefix = panel["target"][: prefix_limit + 1]
        if prefix != target_prefix:
            mismatch = next(
                i for i, (left, right) in enumerate(zip(prefix, target_prefix))
                if left != right
            )
            return False, f"panel {index} coefficient mismatch at index {mismatch}"
        transformed = _transform_coeffs(panel["source"], alpha, beta, prime)
        if transformed != panel["target"]:
            mismatch = next(
                i
                for i, (left, right) in enumerate(zip(transformed, panel["target"]))
                if left != right
            )
            return False, f"panel {index} full coefficient mismatch at index {mismatch}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    prime = inst["prime"]
    matrices = []
    for _ in range(inst["panel_count"]):
        alpha = rng.randrange(1, prime)
        beta = rng.randrange(prime)
        matrices.append(_matrix(alpha, beta, prime))
    return {"matrices": matrices}


def search_space(inst: dict) -> int:
    return (inst["prime"] * (inst["prime"] - 1)) ** inst["panel_count"]


def enumerate_all(inst: dict) -> int | None:
    if inst["panel_count"] != 1 or search_space(inst) > 300_000:
        return None
    prime = inst["prime"]
    count = 0
    for alpha in range(1, prime):
        for beta in range(prime):
            candidate = {"matrices": [_matrix(alpha, beta, prime)]}
            if verify(inst, candidate)[0]:
                count += 1
    return count


def _canonical_affine_map(coeffs: list[int], prime: int) -> tuple[int, int]:
    """The unique generic affine map sending the first three moments to normal form."""
    mean, centered2, centered3 = _moments(coeffs, prime)
    scale = centered2 * _inv(centered3, prime) % prime
    shift = (-scale * mean) % prime
    return scale, shift


def _canonical_oriented_pair(
    source: list[int], target: list[int], prime: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Normalize an ordered pair with one shared change of coordinates.

    Normalizing each form independently would erase the relative isomorphism
    and over-collapse pairs having the same affine orbit but different maps.
    """
    scale, shift = _canonical_affine_map(source, prime)
    return (
        tuple(_transform_coeffs(source, scale, shift, prime)),
        tuple(_transform_coeffs(target, scale, shift, prime)),
    )


def canonical_key(inst: dict) -> str:
    canonical_panels = []
    for panel in inst["panels"]:
        forward = _canonical_oriented_pair(
            panel["source"], panel["target"], inst["prime"]
        )
        backward = _canonical_oriented_pair(
            panel["target"], panel["source"], inst["prime"]
        )
        canonical_panels.append(min(forward, backward))
    canonical_panels.sort()
    payload = json.dumps(
        [inst["prime"], inst["degree"], canonical_panels],
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _next_prime(value: int) -> int:
    candidate = max(3, value | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def escalate(params: dict) -> dict | str | None:
    out = dict(params)
    degree = int(out["n"])
    prime = int(out.get("prime", 1009))
    panels = int(out.get("panels", 8))
    if degree * 2 < prime:
        out["n"] = degree * 2
        return out
    digits = len(str(prime))
    projected_chars = panels * (4 * (digits + 2) + 10) + 20
    if projected_chars > 1900:
        return "cap_bound"
    new_prime = _next_prime(2 * prime + 1)
    out["prime"] = new_prime
    out["n"] = min(2 * degree, new_prime - 2)
    return out


def _eval_univariate(coeffs: list[int], value: int, prime: int) -> tuple[int, int]:
    result = 0
    operations = 0
    for coefficient in coeffs:
        result = (result * value + coefficient) % prime
        operations += 2
    return result, operations


def _all_roots(coeffs: list[int], prime: int) -> tuple[list[int], int]:
    roots = []
    operations = 0
    for value in range(prime):
        evaluation, cost = _eval_univariate(coeffs, value, prime)
        operations += cost
        if evaluation == 0:
            roots.append(value)
    return roots, operations


def _reference_algorithm(inst: dict) -> tuple[object | None, dict[str, int]]:
    """Factor by exhaustive F_p evaluation, then align ordered root pairs."""
    prime = inst["prime"]
    degree = inst["degree"]
    matrices = []
    root_evaluations = 0
    alignment_operations = 0
    candidates_tested = 0
    for panel in inst["panels"]:
        roots1, cost1 = _all_roots(panel["source"], prime)
        roots2, cost2 = _all_roots(panel["target"], prime)
        root_evaluations += cost1 + cost2
        if len(roots1) != degree or len(roots2) != degree:
            return None, {
                "root_evaluation_operations": root_evaluations,
                "alignment_operations": alignment_operations,
                "candidates_tested": candidates_tested,
            }
        source0, source1 = roots1[0], roots1[1]
        source_gap_inv = _inv(source1 - source0, prime)
        target_set = set(roots2)
        found = None
        for target0 in roots2:
            for target1 in roots2:
                if target0 == target1:
                    continue
                candidates_tested += 1
                alpha = (target1 - target0) * source_gap_inv % prime
                beta = (target0 - alpha * source0) % prime
                alignment_operations += 5
                image = set()
                ok = True
                for root in roots1:
                    mapped = (alpha * root + beta) % prime
                    alignment_operations += 2
                    if mapped not in target_set:
                        ok = False
                        break
                    image.add(mapped)
                if ok and len(image) == degree:
                    found = (alpha, beta)
                    break
            if found is not None:
                break
        if found is None:
            return None, {
                "root_evaluation_operations": root_evaluations,
                "alignment_operations": alignment_operations,
                "candidates_tested": candidates_tested,
            }
        matrices.append(_matrix(found[0], found[1], prime))
    return {"matrices": matrices}, {
        "root_evaluation_operations": root_evaluations,
        "alignment_operations": alignment_operations,
        "candidates_tested": candidates_tested,
    }


def _translation_only_attack(inst: dict) -> object:
    matrices = []
    for panel in inst["panels"]:
        mean1, _c2, _c3 = _moments(panel["source"], inst["prime"])
        mean2, _d2, _d3 = _moments(panel["target"], inst["prime"])
        matrices.append(_matrix(1, mean2 - mean1, inst["prime"]))
    return {"matrices": matrices}


def _scale_only_attack(inst: dict) -> object:
    prime = inst["prime"]
    matrices = []
    for panel in inst["panels"]:
        p1 = _power_sums(panel["source"], 1, prime)[1]
        p2 = _power_sums(panel["target"], 1, prime)[1]
        alpha = p2 * _inv(p1, prime) % prime if p1 else 1
        matrices.append(_matrix(alpha or 1, 0, prime))
    return {"matrices": matrices}


def _raw_coefficient_attack(inst: dict) -> object:
    prime = inst["prime"]
    matrices = []
    for panel in inst["panels"]:
        left = panel["source"][2]
        right = panel["target"][2]
        alpha = right * _inv(left, prime) % prime if left else 1
        matrices.append(_matrix(alpha or 1, 0, prime))
    return {"matrices": matrices}


def _uncentered_moment_attack(inst: dict) -> object:
    prime = inst["prime"]
    matrices = []
    for panel in inst["panels"]:
        p = _power_sums(panel["source"], 3, prime)
        q = _power_sums(panel["target"], 3, prime)
        denom = q[2] * p[3] % prime
        alpha = q[3] * p[2] * _inv(denom, prime) % prime if denom else 1
        degree_inv = _inv(inst["degree"], prime)
        beta = (q[1] - alpha * p[1]) * degree_inv % prime
        matrices.append(_matrix(alpha or 1, beta, prime))
    return {"matrices": matrices}


def _random_restart_attack(inst: dict, seed: int, restarts: int = 256) -> object:
    rng = random.Random(seed)
    last = random_candidate(inst, rng)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
        last = candidate
    return last


def _inverse_answer(answer: dict, prime: int) -> dict:
    matrices = []
    for value in answer["matrices"]:
        alpha, beta = _decode_matrix(value, prime, 0)
        alpha_inv = _inv(alpha, prime)
        matrices.append(_matrix(alpha_inv, -beta * alpha_inv, prime))
    return {"matrices": matrices}


def _simultaneous_affine(inst: dict, seed: int) -> tuple[dict, dict]:
    rng = random.Random(seed)
    transformed = copy.deepcopy(inst)
    carried = []
    prime = inst["prime"]
    for index, panel in enumerate(inst["panels"]):
        gamma = rng.randrange(1, prime)
        delta = rng.randrange(prime)
        transformed["panels"][index]["source"] = _transform_coeffs(
            panel["source"], gamma, delta, prime
        )
        transformed["panels"][index]["target"] = _transform_coeffs(
            panel["target"], gamma, delta, prime
        )
        alpha, beta = _decode_matrix(inst["answer"]["matrices"][index], prime, index)
        new_beta = (gamma * beta + delta * (1 - alpha)) % prime
        carried.append(_matrix(alpha, new_beta, prime))
    transformed["answer"] = {"matrices": carried}
    return transformed, transformed["answer"]


def _answer_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    report: dict[str, Any] = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every named rung, several independent seeds.
    planted_checks = 0
    planted_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_roundtrips == planted_checks,
        "checks": planted_checks,
        "json_native_roundtrips": json_roundtrips,
        "failures": planted_failures,
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    ship = make_instance(seed=424242, **shipping_params)

    # G2: deliberately reach distinct validation failures.
    corruptions: dict[str, object] = {}
    corruptions["empty"] = []
    corruptions["drop_one"] = {"matrices": ship["answer"]["matrices"][:-1]}
    malformed = copy.deepcopy(ship["answer"])
    malformed["matrices"][0] = [[1, 0, 0], [0, 1, 0]]
    corruptions["wrong_shape"] = malformed
    noncanonical = copy.deepcopy(ship["answer"])
    noncanonical["matrices"][0][0][0] = 2
    corruptions["noncanonical"] = noncanonical
    singular = copy.deepcopy(ship["answer"])
    singular["matrices"][0][1][1] = 0
    corruptions["singular"] = singular
    out_of_range = copy.deepcopy(ship["answer"])
    out_of_range["matrices"][0][0][1] = ship["prime"]
    corruptions["out_of_range"] = out_of_range
    mismatch = copy.deepcopy(ship["answer"])
    mismatch["matrices"][2][0][1] = (mismatch["matrices"][2][0][1] + 1) % ship["prime"]
    corruptions["changed_entry"] = mismatch
    swapped = copy.deepcopy(ship["answer"])
    swapped["matrices"][0], swapped["matrices"][1] = (
        swapped["matrices"][1], swapped["matrices"][0]
    )
    corruptions["swap_panels"] = swapped
    duplicated = copy.deepcopy(ship["answer"])
    duplicated["matrices"][-1] = copy.deepcopy(duplicated["matrices"][0])
    corruptions["duplicate_matrix"] = duplicated
    corruption_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        corruption_reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({v["reason"] for v in corruption_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruption_reasons.values())
        and distinct_reasons == len(corruption_reasons),
        "cases": corruption_reasons,
        "distinct_reasons": distinct_reasons,
    }

    # G3: tagged JSON survives realistic prose and a markdown fence.
    serialized = json.dumps(ship["answer"], separators=(",", ":"))
    response = "I used the affine covariant.\n<answer>```json\n" + serialized + "\n```</answer>\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"] and verify(ship, parsed)[0]
        and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == ship["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: uniform sampling from the exact promised affine matrix language.
    samples = 200_000
    hits = 0
    rng = random.Random(991827)
    start = time.perf_counter()
    for _ in range(samples):
        if verify(ship, random_candidate(ship, rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - start
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "search_space": search_space(ship),
        "sampling_seconds": round(guess_seconds, 6),
        "prior": "independent uniform normalized affine matrices for every panel",
    }

    # G5: shipping density plus the successful Track-B mechanical baseline.
    start = time.perf_counter()
    reference_answer, reference_stats = _reference_algorithm(ship)
    reference_seconds = time.perf_counter() - start
    reference_ok = reference_answer is not None and verify(ship, reference_answer)[0]
    demo = make_instance(seed=17, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and samples >= 200_000 and demo_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": hits / samples,
        "shipping_exact_count": enumerate_all(ship),
        "demo_exact_valid_count": demo_count,
        "baseline_wall_seconds": round(reference_seconds, 6),
        "baseline_field_operations": (
            reference_stats["root_evaluation_operations"]
            + reference_stats["alignment_operations"]
        ),
        "baseline_candidates_tested": reference_stats["candidates_tested"],
        "baseline_solved": reference_ok,
    }

    # G6: four failed in-context probes; the successful standard algorithm is separate.
    attack_fns = {
        "coefficient_outlier_raw_ratio": lambda inst, seed: _raw_coefficient_attack(inst),
        "greedy_translation_only": lambda inst, seed: _translation_only_attack(inst),
        "random_restart_256": lambda inst, seed: _random_restart_attack(inst, seed, 256),
        "obvious_scale_only_ansatz": lambda inst, seed: _scale_only_attack(inst),
        "uncentered_moment_ratio": lambda inst, seed: _uncentered_moment_attack(inst),
    }
    attack_seeds = 8
    attack_results = {
        name: {"successes": 0, "attempts": attack_seeds} for name in attack_fns
    }
    ref_successes = 0
    ref_seconds_total = 0.0
    ref_ops_total = 0
    ref_candidates_total = 0
    for offset in range(attack_seeds):
        inst = make_instance(seed=900_000 + offset, **shipping_params)
        for name, attack in attack_fns.items():
            candidate = attack(inst, 700_000 + offset)
            if verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        started = time.perf_counter()
        candidate, stats = _reference_algorithm(inst)
        ref_seconds_total += time.perf_counter() - started
        ref_ops_total += stats["root_evaluation_operations"] + stats["alignment_operations"]
        ref_candidates_total += stats["candidates_tested"]
        if candidate is not None and verify(inst, candidate)[0]:
            ref_successes += 1
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == attack_seeds,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "finite-field root recovery and ordered-pair affine alignment",
            "complexity": (
                "implemented O(P*p*d + P*d^3); standard randomized finite-field "
                "factorization is polynomial in P,d,log(p)"
            ),
            "wall_clock_sec": round(ref_seconds_total / attack_seeds, 6),
            "operations": ref_ops_total // attack_seeds,
            "candidates_tested": ref_candidates_total // attack_seeds,
            "solves": f"{ref_successes}/{attack_seeds}, as expected",
        },
    }

    # G7: double polynomial degree without lengthening the matrix witness.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    escalated_params = escalate(shipping_params)
    escalated_ok = False
    if isinstance(escalated_params, dict):
        escalated = make_instance(seed=271828, **escalated_params)
        escalated_ok = verify(escalated, escalated["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "shipping_degree": shipping_params["n"],
        "doubled_degree": doubled_params["n"],
        "answer_atoms_before": _answer_atoms(ship["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "doubled_verified": doubled_ok,
        "fixed_answer_escalation": escalated_params,
        "escalated_verified": escalated_ok,
    }

    # G8: panel reorder, source/target swap, and simultaneous affine coordinates.
    invariance_checks = 0
    witness_checks = 0
    relative_map_distinct = 0
    invariance_failures = []
    for offset in range(20):
        inst = make_instance(seed=1_200_000 + offset, **shipping_params)
        key = canonical_key(inst)

        reordered = copy.deepcopy(inst)
        reordered["panels"].reverse()
        reordered["answer"]["matrices"].reverse()
        invariance_checks += 1
        if canonical_key(reordered) != key:
            invariance_failures.append([offset, "panel_reorder_key"])
        if verify(reordered, reordered["answer"])[0]:
            witness_checks += 1
        else:
            invariance_failures.append([offset, "panel_reorder_witness"])

        swapped = copy.deepcopy(inst)
        for panel in swapped["panels"]:
            panel["source"], panel["target"] = panel["target"], panel["source"]
        swapped["answer"] = _inverse_answer(inst["answer"], inst["prime"])
        invariance_checks += 1
        if canonical_key(swapped) != key:
            invariance_failures.append([offset, "swap_key"])
        if verify(swapped, swapped["answer"])[0]:
            witness_checks += 1
        else:
            invariance_failures.append([offset, "swap_witness"])

        changed, carried = _simultaneous_affine(inst, 1_300_000 + offset)
        invariance_checks += 1
        if canonical_key(changed) != key:
            invariance_failures.append([offset, "coordinate_key"])
        if verify(changed, carried)[0]:
            witness_checks += 1
        else:
            invariance_failures.append([offset, "coordinate_witness"])

        # Hold every source fixed while changing one relative isomorphism.  This
        # catches the opposite canonicalization bug: independently normalizing
        # source and target would erase the map and give the same key here.
        altered = copy.deepcopy(inst)
        old_alpha, old_beta = _decode_matrix(
            inst["answer"]["matrices"][0], inst["prime"], 0
        )
        inverse_alpha = _inv(old_alpha, inst["prime"])
        new_alpha = next(
            candidate
            for candidate in range(1, inst["prime"])
            if candidate not in {old_alpha, inverse_alpha}
        )
        altered["panels"][0]["target"] = _transform_coeffs(
            altered["panels"][0]["source"], new_alpha, old_beta, inst["prime"]
        )
        altered["answer"]["matrices"][0] = _matrix(
            new_alpha, old_beta, inst["prime"]
        )
        if not verify(altered, altered["answer"])[0]:
            invariance_failures.append([offset, "relative_map_witness"])
        elif canonical_key(altered) != key:
            relative_map_distinct += 1
        else:
            invariance_failures.append([offset, "relative_map_overcollapse"])

    unrelated_keys = {
        canonical_key(make_instance(seed=1_400_000 + offset, **shipping_params))
        for offset in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariance_failures
        and witness_checks == invariance_checks
        and relative_map_distinct == 20
        and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "relative_map_distinct": relative_map_distinct,
        "relative_map_attempts": 20,
        "unrelated_distinct": len(unrelated_keys),
        "unrelated_attempts": 20,
        "failures": invariance_failures,
        "transformations": [
            "panel permutation",
            "source/target swap with inverse witness",
            "independent simultaneous affine coordinate changes",
        ],
    }

    # G9: the three oracle arms are recorded diagnostics under the current
    # contract (the old hinted-arm gate was retired on 2026-09-05).  Only the
    # answer-size and intended-route caps are gated locally.
    compact = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(compact)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(ship["answer"])
    intended_ops = 70 * ship["panel_count"]
    arms = copy.deepcopy(G9_RESULTS)
    hinted = arms.pop("hinted_verdict")
    hinted_attempts = G9_RESULTS["hinted"]["attempts"]
    placebo_attempts = G9_RESULTS["placebo"]["attempts"]
    hinted_minus_placebo = None
    if hinted_attempts and placebo_attempts:
        hinted_minus_placebo = (
            G9_RESULTS["hinted"]["solved"] / hinted_attempts
            - G9_RESULTS["placebo"]["solved"] / placebo_attempts
        )
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    diagnostic_complete = all(
        G9_RESULTS[name]["attempts"] >= 3
        for name in ("bare", "hinted", "placebo")
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "caps_pass": within_caps,
        "diagnostic_complete": diagnostic_complete,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": hinted,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    gate_values = [
        value for key, value in report.items() if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
