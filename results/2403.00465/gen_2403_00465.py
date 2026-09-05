"""Verified generators for succinct unweighted Polyamorous Scheduling.

Section 5, Proposition 5.1 of arXiv:2403.00465 identifies the optimum heat
of an unweighted polycule with the chromatic index of its relationship graph.
Here that graph is bipartite and is described exactly by a polynomial over a
prime field.  Sampling an affine factor family first and multiplying its
factors gives both the instance and a compact periodic-matching certificate;
generation never factors the polynomial it creates.
"""

from __future__ import annotations

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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The construction below remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "unweighted OPS relationship graph given by an exact finite-field polynomial predicate",
        "periodic schedule of matchings encoded by an affine factor family",
    ],
    "verification_operations": [
        "finite-field polynomial multiplication and substitution",
        "exact coefficient comparison",
        "matching bijection check from nonzero affine slope",
        "maximum-degree lower bound on schedule heat",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, Proposition 5.1 (an unweighted OPS schedule of heat h "
        "exists exactly when the relationship graph is h-edge-colourable)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The top two coefficient layers are the first two moments of an "
        "arithmetic progression of parallel affine factors; without that "
        "observation one expands the graph or scans the field for every root."
    ),
    "hardness_basis": (
        "Track B: exhaustive finite-field root scanning recovers the schedule "
        "in O(p*n+n^3) and used 29,984,225 exact field operations (1.46 s "
        "maximum on the audit host) at shipping, whereas the coefficient-moment "
        "route used 112 exact operations and cannot be executed mechanically in context."
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
    "demo": {"n": 4, "p": 11},
    "easy": {"n": 32, "p": 16363},
    "medium": {"n": 48, "p": 65519},
    "hard": {"n": 56, "p": 262139},
}
SHIPPING_DIFFICULTY = "hard"

_ESCALATION_LEVELS = (
    (56, 262139),
    (64, 524287),
    (72, 1048571),
    (80, 2147483647),
    (88, 2305843009213693951),
    (96, 618970019642690137449562111),
    (104, 162259276829213363391578010288127),
    (112, 170141183460469231731687303715884105727),
)
_SUPPORTED_PRIMES = frozenset(
    [11, 4091, 16363, 65519, *(p for _, p in _ESCALATION_LEVELS)]
)

STRUCTURAL_HINT = (
    "The top two coefficient layers are the first two moments of an "
    "arithmetic progression of parallel affine factors."
)
PLACEBO_HINT = (
    "The coefficient rows use canonical residues and list every exponent in "
    "a consistent total-degree convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {slope,start,step} over F_p.  It denotes n affine "
        "factors y-slope*x-(start+j*step), for j=0,...,n-1, and hence an "
        "n-day periodic matching schedule.  slope and step are nonzero."
    ),
    "bounds": {
        "fields": 3,
        "slope_min": 1,
        "start_min": 0,
        "step_min": 1,
        "field_max_exclusive_at_shipping": 262139,
    },
}

NOTES = r"""
Step 0. Definitions 1.1 and 1.2 fix the native object: each day is a matching,
and heat is the largest growth-rate times recurrence time. Section 4 gives the
general configuration-graph algorithm; its graph has up to product_e f(e)
states and does not supply an efficient certificate search. Section 5,
Proposition 5.1 is the decisive result here: for unit growth rates, optimum heat
is exactly chromatic index. The same section cites NP-completeness of deciding
3-edge-colourability of cubic graphs, but that worst-case theorem does not make
an inverse-planted distribution hard. Indeed, random planted cubic graphs were
rejected during construction because randomized DPLL found their colourings.

Track and certificate algorithm. This family is Track B, not Track A. Its graph
is bipartite, and an explicit graph can be edge-coloured in polynomial time;
more directly, the shipped succinct instance can be solved by evaluating its
degree-n polynomial at every field element and collecting all roots. The
reference implementation costs O(p*n+n^3), about 2*p*n Horner field operations
plus progression reconstruction. At shipping, this is 29,984,225 exact
operations in the slowest audit seed. The compact route reads the degree-n and degree-(n-1) layers,
recovers the common slope, and uses the first two root moments to obtain the
progression step up to sign and its start. Modular exponentiation for the two
inverses and square root keeps the route below 100 counted operations.

Generation. Sample nonzero slope and step and a start first. Multiply
Q(z)=product_j(z-start-j*step), then substitute z=y-slope*x. The answer therefore
exists by composition of polynomial identities. Each factor is a perfect
matching between two copies of F_p, and distinct progression terms partition
all relationships into n matchings. Three seed-dependent disjoint cycles alter
the graph isomorphism type without marking any core edge; they have a fixed
canonical schedule within the same n days.

Easy results avoided. Misra-Gries gives Delta+1 colours in polynomial time, and
Theorems 1.5 and 1.6 give polynomial-time approximation schedules. Those are
not hidden: they are insufficient for the requested optimal n-day symbolic
schedule, while the exact root scan is reported as the successful Track B
reference algorithm. Cheap coefficient guesses, a low-degree greedy guess,
uniform restarts, and the by-hand unit-step ansatz are measured and fail.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 200_000


def _validate_params(n: int, p: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not 4 <= n <= 160:
        raise ValueError("n must be an integer in 4..160")
    if isinstance(p, bool) or not isinstance(p, int) or p not in _SUPPORTED_PRIMES:
        raise ValueError("p must be one of the module's supported exact primes")
    if n >= p or p % 4 != 3:
        raise ValueError("parameters require n < p and p congruent to 3 modulo 4")


def _mul_linear(poly: list[int], root: int, p: int) -> list[int]:
    """Return poly(z)*(z-root), coefficients in increasing degree."""
    out = [0] * (len(poly) + 1)
    for i, value in enumerate(poly):
        out[i] = (out[i] - root * value) % p
        out[i + 1] = (out[i + 1] + value) % p
    return out


def _univariate_from_params(n: int, p: int, start: int, step: int) -> list[int]:
    q = [1]
    root = start
    for _ in range(n):
        q = _mul_linear(q, root, p)
        root = (root + step) % p
    return q


def _coefficient_rows(
    n: int, p: int, slope: int, start: int, step: int
) -> list[list[int]]:
    """Coefficients of product_j(y-slope*x-start-j*step).

    Row k contains coefficients of total degree k. Entry i is the coefficient
    of x^i*y^(k-i).  Rows are JSON-native and coefficient comparison is exact.
    """
    q = _univariate_from_params(n, p, start, step)
    rows: list[list[int]] = []
    for k, qk in enumerate(q):
        row = []
        for i in range(k + 1):
            value = qk * math.comb(k, i) * pow(-slope, i, p)
            row.append(value % p)
        rows.append(row)
    return rows


def _cycle_signature(n: int, seed: int) -> list[int]:
    """Inject seeds 0..19 into structural decorations, without keying on seed."""
    choices = list(range(3, n + 9))
    triples = []
    for i in range(len(choices) - 2):
        for j in range(i + 1, len(choices) - 1):
            for k in range(j + 1, len(choices)):
                triples.append((choices[i], choices[j], choices[k]))
    return list(triples[seed % len(triples)])


def _candidate_from_values(slope: int, start: int, step: int) -> dict[str, int]:
    return {"slope": slope, "start": start, "step": step}


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Compose affine factors into a succinct optimal periodic schedule."""
    unknown = set(params) - {"p"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    p = params.get("p", 4091)
    _validate_params(n, p)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    while True:
        slope = rng.randrange(1, p)
        start = rng.randrange(p)
        step = rng.randrange(2, p - 1)
        if step in (1, p - 1):
            continue
        roots = {(start + j * step) % p for j in range(n)}
        if len(roots) != n or 0 in roots or 1 in roots:
            continue
        answer = _candidate_from_values(slope, start, step)
        rows = _coefficient_rows(n, p, slope, start, step)
        # Keep the highest-information rows away from a fixed display position.
        row_order = list(range(n + 1))
        rng.shuffle(row_order)
        return {
            "family": "succinct_unweighted_polyamorous_schedule",
            "n": n,
            "p": p,
            "coefficient_rows": rows,
            "row_order": row_order,
            "cycle_lengths": _cycle_signature(n, seed),
            "answer": answer,
        }


def render(inst: dict) -> str:
    n, p = inst["n"], inst["p"]
    lines = [
        "SUCCINCT UNWEIGHTED POLYAMOROUS SCHEDULING",
        "",
        f"All arithmetic below is in the prime field F_{p}; residues are integers 0,...,{p-1}.",
        f"There are two sets of people L_x and R_y, one person for each x,y in F_{p}.",
        "They form an undirected bipartite relationship graph: L_x is related to R_y",
        "exactly when F(x,y)=0. There are no other relationships in this core.",
        "Every relationship has unit desire growth per day.",
        "",
        "The polynomial F is given by total-degree rows.  In a row labelled k,",
        "entry i (0-indexed) is the coefficient of x^i*y^(k-i); omitted",
        "monomials have coefficient 0.  Row and entry order do not otherwise matter:",
    ]
    for k in inst["row_order"]:
        lines.append(f"  degree {k}: " + ",".join(map(str, inst["coefficient_rows"][k])))
    cycles = ", ".join(map(str, inst["cycle_lengths"]))
    lines.extend([
        "",
        f"The full graph also has three disjoint cycle components of lengths {cycles}.",
        "For the compact certificate below, those cycles use their canonical schedule:",
        "an even cycle alternates days 0 and 1; an odd cycle alternates days 0 and 1",
        "on all but its closing edge, which uses day 2. Cycle vertices and edges are",
        "indexed consecutively from 0 solely for this convention.",
        "",
        f"Find slope a != 0, start b, and step s != 0 in F_{p} such that",
        f"  F(x,y) = product over j=0,...,{n-1} of (y - a*x - (b+j*s)).",
        f"The {n} values b+j*s must be distinct.  Your object denotes this complete",
        f"period-{n} schedule: on day j, schedule every core relationship satisfying",
        "y=a*x+b+j*s, together with the canonical cycle edges assigned to day j.",
        "Days and coefficient exponents are 0-indexed; the period is cyclic; order",
        "within a day's matching is irrelevant.  A valid factorization proves the",
        f"schedule has heat {n}, which is optimal because every core vertex has degree {n}.",
        "",
        "Output one JSON object with exactly the integer keys slope, start, and step.",
        f"Each value must be its canonical residue in 0,...,{p-1}; slope and step cannot be 0.",
        "Give your final answer inside <answer></answer> tags.",
        "Example: <answer>{\"slope\":2,\"start\":3,\"step\":4}</answer>",
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
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    if set(value) != {"slope", "start", "step"}:
        return None
    if any(isinstance(value[k], bool) or not isinstance(value[k], int) for k in value):
        return None
    return {"slope": value["slope"], "start": value["start"], "step": value["step"]}


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object must not be empty"
    if set(answer) != {"slope", "start", "step"}:
        return False, "answer must contain exactly slope, start, and step"
    for name in ("slope", "start", "step"):
        if isinstance(answer[name], bool) or not isinstance(answer[name], int):
            return False, f"{name} must be an integer"
    p, n = inst["p"], inst["n"]
    a, b, s = answer["slope"], answer["start"], answer["step"]
    if not 1 <= a < p:
        return False, f"slope must lie in 1..{p-1}"
    if not 0 <= b < p:
        return False, f"start must lie in 0..{p-1}"
    if not 1 <= s < p:
        return False, f"step must lie in 1..{p-1}"
    if n >= p:
        return False, "instance degree must be smaller than the field size"

    rows = inst.get("coefficient_rows")
    if not isinstance(rows, list) or len(rows) != n + 1:
        return False, "instance polynomial has malformed degree rows"
    if any(not isinstance(row, list) or len(row) != k + 1
           for k, row in enumerate(rows)):
        return False, "instance polynomial has malformed coefficient rows"

    actual_slope_layer = rows[n][1] % p
    expected_slope_layer = (-n * a) % p
    if actual_slope_layer != expected_slope_layer:
        return False, "slope is inconsistent with the top coefficient layer"

    actual_root_sum = (-rows[n - 1][0]) % p
    candidate_root_sum = (n * b + s * n * (n - 1) // 2) % p
    if actual_root_sum != candidate_root_sum:
        return False, "start and step have the wrong first root moment"

    q = _univariate_from_params(n, p, b, s)
    if q[n - 2] % p != rows[n - 2][0] % p:
        return False, "step has the wrong second root moment"

    expected = _coefficient_rows(n, p, a, b, s)
    if expected != rows:
        for k, (left, right) in enumerate(zip(expected, rows)):
            if left != right:
                for i, (x, y) in enumerate(zip(left, right)):
                    if x != y:
                        return False, (
                            "polynomial identity mismatch at coefficient "
                            f"x^{i}*y^{k-i}"
                        )
        return False, "polynomial identity mismatch"

    # Nonzero s and n<p make the n intercepts distinct; nonzero a makes each
    # affine factor a bijective perfect matching.  The supplied cycle rule is a
    # proper 2/3-edge-colouring and n>=4, so it fits in the same period.
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    p = inst["p"]
    return {
        "slope": rng.randrange(1, p),
        "start": rng.randrange(p),
        "step": rng.randrange(1, p),
    }


def search_space(inst: dict) -> int | None:
    p = inst["p"]
    return p * (p - 1) * (p - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    count = 0
    p = inst["p"]
    for a in range(1, p):
        for b in range(p):
            for s in range(1, p):
                if verify(inst, _candidate_from_values(a, b, s))[0]:
                    count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Complete within-family invariant under coordinate affine relabellings.

    Every core is isomorphic to shifts {0,...,n-1} on F_p; slope, start and
    nonzero step are coordinate choices.  The disjoint cycle lengths are the
    remaining component invariants and are sorted to forget input order.
    """
    structural = [inst["p"], inst["n"], sorted(inst["cycle_lengths"])]
    blob = json.dumps(structural, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params["n"])
    p = int(params["p"]) if "p" in params else 4091
    for next_n, next_p in _ESCALATION_LEVELS:
        if next_n > n or next_p > p:
            return {"n": max(n, next_n), "p": max(p, next_p)}
    return None


def _poly_eval(q: list[int], value: int, p: int) -> int:
    total = 0
    for coefficient in reversed(q):
        total = (total * value + coefficient) % p
    return total


def _reference_root_scan(inst: dict) -> dict:
    """Successful mechanical Track-B algorithm with an operation counter."""
    n, p = inst["n"], inst["p"]
    rows = inst["coefficient_rows"]
    operations = 0
    inv_n = pow(n, -1, p)
    slope = (-rows[n][1] * inv_n) % p
    operations += 2
    q = [rows[k][0] % p for k in range(n + 1)]
    roots = []
    for value in range(p):
        total = 0
        for coefficient in reversed(q):
            total = (total * value + coefficient) % p
            operations += 2
        if total == 0:
            roots.append(value)
    root_set = set(roots)
    candidate = None
    if len(roots) == n:
        for start in roots:
            if candidate is not None:
                break
            for second in roots:
                if second == start:
                    continue
                step = (second - start) % p
                operations += 1
                values = set()
                current = start
                for _ in range(n):
                    values.add(current)
                    current = (current + step) % p
                    operations += 1
                if values == root_set:
                    candidate = _candidate_from_values(slope, start, step)
                    break
    return {"candidate": candidate, "operations": operations, "roots": len(roots)}


def _pow_with_count(base: int, exponent: int, modulus: int) -> tuple[int, int]:
    result = 1
    base %= modulus
    operations = 0
    while exponent:
        if exponent & 1:
            result = result * base % modulus
            operations += 1
        exponent >>= 1
        if exponent:
            base = base * base % modulus
            operations += 1
    return result, operations


def _compact_moment_route(inst: dict) -> dict:
    n, p = inst["n"], inst["p"]
    rows = inst["coefficient_rows"]
    operations = 0

    inv_n, used = _pow_with_count(n, p - 2, p)
    operations += used
    slope = (-rows[n][1] * inv_n) % p
    operations += 2

    e1 = (-rows[n - 1][0]) % p
    e2 = rows[n - 2][0] % p
    sum_squares = (e1 * e1 - 2 * e2) % p
    operations += 3
    central = (sum_squares - e1 * e1 * inv_n) % p
    operations += 3
    denominator = n * (n * n - 1) % p
    operations += 2
    inv_den, used = _pow_with_count(denominator, p - 2, p)
    operations += used
    step_square = central * 12 * inv_den % p
    operations += 2
    step, used = _pow_with_count(step_square, (p + 1) // 4, p)
    operations += used
    triangular = n * (n - 1) // 2
    start = (e1 - step * triangular) * inv_n % p
    operations += 3
    candidate = _candidate_from_values(slope, start, step)
    return {"candidate": candidate, "operations": operations}


def _unit_step_candidate(inst: dict) -> dict:
    n, p = inst["n"], inst["p"]
    rows = inst["coefficient_rows"]
    inv_n = pow(n, -1, p)
    slope = (-rows[n][1] * inv_n) % p
    root_sum = (-rows[n - 1][0]) % p
    start = (root_sum - n * (n - 1) // 2) * inv_n % p
    return _candidate_from_values(slope, start, 1)


def _largest_coeff_candidate(inst: dict) -> dict:
    p = inst["p"]
    values = sorted((v for row in inst["coefficient_rows"] for v in row), reverse=True)
    slope = values[0] or 1
    start = values[1] % p
    step = values[2] or 1
    return _candidate_from_values(slope, start, step)


def _low_degree_candidate(inst: dict) -> dict:
    p = inst["p"]
    rows = inst["coefficient_rows"]
    slope = rows[1][1] % p or 1
    start = rows[0][0] % p
    step = rows[1][0] % p or 1
    return _candidate_from_values(slope, start, step)


def _affine_relabel(inst: dict, u: int, v: int, t: int, w: int) -> tuple[dict, dict]:
    """Carry the graph and certificate through x'=u*x+t, y'=v*y+w."""
    p, n = inst["p"], inst["n"]
    # This helper is test-only; using the planted object here carries a known
    # certificate through a relabelling and is never part of verify().
    old = inst["answer"]
    a2 = v * old["slope"] * pow(u, -1, p) % p
    b2 = (v * old["start"] + w - a2 * t) % p
    s2 = v * old["step"] % p
    answer = _candidate_from_values(a2, b2, s2)
    transformed = {
        "family": inst["family"],
        "n": n,
        "p": p,
        "coefficient_rows": _coefficient_rows(n, p, a2, b2, s2),
        "row_order": list(reversed(inst["row_order"])),
        "cycle_lengths": list(reversed(inst["cycle_lengths"])),
        "answer": answer,
    }
    return transformed, answer


# Filled from the three isolated harden.py runs.  These diagnostics do not gate;
# G9(c)'s measured size and operation caps do.
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3, "error_attempts": 0},
    "hinted": {"solved": 1, "attempts": 3, "error_attempts": 0},
    "placebo": {"solved": 1, "attempts": 2, "error_attempts": 4},
}
_G9_HINTED_VERDICT = "too_easy"


def selftest() -> dict:
    report: dict[str, Any] = {}

    g1_instances = 0
    json_ok = True
    for preset in DIFFICULTY.values():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **preset)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 failed for {preset}, seed {seed}: {why}")
            json_ok &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_instances += 1
    report["G1_planted_verifies"] = {
        "pass": g1_instances == 16 and json_ok,
        "instances": g1_instances,
        "json_native": json_ok,
        "generation_route": "composition of affine polynomial factors with known matchings",
    }

    shipping = make_instance(seed=123, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = dict(shipping["answer"])
    corruptions = {
        "empty": {},
        "drop_one": {"slope": planted["slope"], "start": planted["start"]},
        "out_of_range": {**planted, "slope": shipping["p"]},
        "swap_two": {
            "slope": planted["start"] or 1,
            "start": planted["slope"],
            "step": planted["step"],
        },
        "duplicate": {**planted, "step": planted["start"] or planted["slope"]},
    }
    reasons = {name: verify(shipping, bad)[1] for name, bad in corruptions.items()}
    rejected = all(not verify(shipping, bad)[0] for bad in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": rejected and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
    }

    encoded = json.dumps(shipping["answer"], separators=(",", ":"))
    prose = f"I used the two leading moments.\n<answer>```json\n{encoded}\n```</answer>\nDone."
    parsed = parse_answer(prose)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "realistic_prose": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(0x240300465)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        hits += int(verify(shipping, candidate)[0])
    space = search_space(shipping)
    exact_valid = 2  # progression reversal: (b,s) and (b+(n-1)s,-s)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and exact_valid / space < 1e-6,
        "hits": hits,
        "total": samples,
        "empirical_probability": hits / samples,
        "structure_aware_space": space,
        "exact_valid_answers": exact_valid,
        "exact_probability": {"numerator": exact_valid, "denominator": space},
        "prior": "uniform bounded slope/start/step triples with nonzero slope and step",
    }

    ref_walls = []
    ref_ops = []
    reference_successes = 0
    compact_successes = 0
    compact_ops = []
    attack_results = {
        "outlier_largest_coefficients": 0,
        "greedy_low_degree_coefficients": 0,
        "random_uniform_restart_256": 0,
        "by_hand_unit_step_ansatz": 0,
    }
    for seed in range(8):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        t0 = time.perf_counter()
        ref = _reference_root_scan(inst)
        ref_walls.append(time.perf_counter() - t0)
        ref_ops.append(ref["operations"])
        reference_successes += int(
            ref["candidate"] is not None and verify(inst, ref["candidate"])[0]
        )
        compact = _compact_moment_route(inst)
        compact_ops.append(compact["operations"])
        compact_successes += int(verify(inst, compact["candidate"])[0])
        attack_results["outlier_largest_coefficients"] += int(
            verify(inst, _largest_coeff_candidate(inst))[0]
        )
        attack_results["greedy_low_degree_coefficients"] += int(
            verify(inst, _low_degree_candidate(inst))[0]
        )
        attack_results["by_hand_unit_step_ansatz"] += int(
            verify(inst, _unit_step_candidate(inst))[0]
        )
        rr = random.Random(9000 + seed)
        found = any(verify(inst, random_candidate(inst, rr))[0] for _ in range(256))
        attack_results["random_uniform_restart_256"] += int(found)

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": hits == 0 and reference_successes == 8 and demo_count == 2,
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "shipping_sample_fraction": hits / samples,
        "shipping_exact_valid_answers_by_symmetry": exact_valid,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "reference_wall_seconds_max": max(ref_walls),
        "reference_wall_seconds_mean": sum(ref_walls) / len(ref_walls),
        "reference_operations_max": max(ref_ops),
        "reference_attempts": 8,
    }

    panel = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_results.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(x == 0 for x in attack_results.values()),
        "attacks": panel,
        "reference_algorithm": {
            "name": "exhaustive finite-field root scan plus AP reconstruction",
            "complexity": "O(p*n+n^3) exact field operations",
            "wall_clock_sec_max": max(ref_walls),
            "wall_clock_sec_mean": sum(ref_walls) / len(ref_walls),
            "operations": max(ref_ops),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "top-layer slope plus two root moments",
            "operations": max(compact_ops),
            "solves": f"{compact_successes}/8",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        p=DIFFICULTY[SHIPPING_DIFFICULTY]["p"],
        seed=77,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["coefficient_rows"]) > len(shipping["coefficient_rows"]),
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "base_coefficients": sum(map(len, shipping["coefficient_rows"])),
        "doubled_coefficients": sum(map(len, doubled["coefficient_rows"])),
        "planted_verifies": doubled_ok,
        "fixed_answer_length_axis": "n, p, and polynomial coefficient haystack grow; answer remains three fields",
    }

    invariance_checks = 0
    real_checks = 0
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        distinct_keys.append(key)

        reordered = dict(inst)
        reordered["row_order"] = list(reversed(inst["row_order"]))
        reordered["cycle_lengths"] = list(reversed(inst["cycle_lengths"]))
        if canonical_key(reordered) != key:
            raise AssertionError("canonical key changed under input/component reordering")
        invariance_checks += 1
        real_checks += int(verify(reordered, inst["answer"])[0])

        p = inst["p"]
        u = 2 + seed % (p - 2)
        v = 3 + (2 * seed) % (p - 3)
        transformed, carried = _affine_relabel(inst, u, v, seed + 1, 3 * seed + 2)
        if canonical_key(transformed) != key:
            raise AssertionError("canonical key changed under affine vertex relabelling")
        invariance_checks += 1
        real_checks += int(verify(transformed, carried)[0])

        transformed2, carried2 = _affine_relabel(
            transformed, (u + 5) % p or 1, (v + 7) % p or 1, seed + 11, seed + 17
        )
        if canonical_key(transformed2) != key:
            raise AssertionError("canonical key changed under composed relabelling")
        invariance_checks += 1
        real_checks += int(verify(transformed2, carried2)[0])

    report["G8_canonical_key"] = {
        "pass": invariance_checks >= 60 and real_checks == 60 and len(set(distinct_keys)) == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_checks,
        "distinct_unrelated": len(set(distinct_keys)),
        "unrelated_total": 20,
        "symmetries": "row/component reorderings and one or two composed affine relabellings of both field-coordinate vertex classes",
        "key_invariant": "field size, core degree, and multiset of disjoint cycle-component lengths",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    intended_ops = max(compact_ops)
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    arm_complete = hinted["attempts"] == 3 and placebo["attempts"] == 3
    within_caps = len(answer_blob) <= 2000 and 3 <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate if arm_complete else None,
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": 3,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
