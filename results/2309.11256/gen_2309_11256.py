"""Inverse generator for equal-degree tropical polynomial factorization.

The semiring operations are min (addition) and ordinary integer addition
(multiplication).  A coefficient vector ``a`` represents the formal polynomial
min_i(a[i] + i*x).  Formal coefficient vectors matter here: equality merely as
piecewise-linear functions is not enough.

This module is standard-library only and performs no I/O at import time.
"""

from __future__ import annotations

import ast
import hashlib
import itertools
import json
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 4, "coefficient_max": 7},
    "easy": {"n": 18, "coefficient_max": 127},
    "medium": {"n": 36, "coefficient_max": 127},
    "hard": {"n": 72, "coefficient_max": 127},
}

# The paper's own parameter setting.  Kept for reference: the ladder is exactly
# demo/easy/medium/hard, so this cannot live in DIFFICULTY.
PAPER_PARAMS = {"n": 150, "coefficient_max": 127}

# This is updated if harden.py selects a different named rung.
SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Definition: Sections 2.1 and 4.3 of Chen--Grigoriev--Shpilrain,
"Tropical cryptography III: digital signatures" (arXiv:2309.11256), define
formal one-variable tropical polynomials and coefficientwise min-plus
multiplication.  Section 5 says recovering equal-degree X,Y from M=X tensor Y
is the factorization problem.  Sections 4 and 4.1 supply the d=150, r=127
recommendation and the endpoint-zero safe-key rule.

Hard/easy boundary: the paper cites Kim--Roush, whose Theorem 7 proves
NP-completeness for growing degree in the equal-slope, equal-degree concave
case, even with public coefficients in {0,1,2,3}.  Kim--Roush Proposition 3
gives polynomial-time factorization when the coefficient diagram is convex;
their Algorithms section says fixed degree reduces to finitely many linear
programs and proposes exponential branch-and-bound.  Section 3.1 of the
signature paper warns that safe-key generation is not fully resolved.  Brown
and Monico's Section 3 gives exact division only when a divisor is already
known; their Section 5.2 motivates endpoint zeros to defeat small-degree
divisor enumeration.  Accordingly n grows here, both factor degrees are n,
and both endpoints are fixed to zero.

Generation and attacks: both hidden factors' non-endpoint coefficients are
i.i.d. uniform on the same inclusive interval [1,r], then the public product
is computed.  Conditioning the paper's [0,r] draw this way keeps the three
required product vertices at degrees 0,n,2n as the only zero-height vertices;
an interior zero would advertise extra convex-hull structure.  This also avoids
planted/decoy distribution differences.  The
outlier/lower-envelope attack, a deterministic left-to-right greedy repair,
and structure-aware random restarts are exercised by selftest.  The canonical
key sorts the input terms and quotients the genuine degree-reversal symmetry;
it never uses the seed or rendered text.

Caveat: Theorem 7 is a worst-case decision result for specially structured
coefficients.  It does not prove average-case hardness of these random planted
products.  The local attacks and required multi-vendor oracle loop are empirical
checks of that gap, not a reduction-based average-case proof.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _tropical_product(a: list[int] | tuple[int, ...],
                      b: list[int] | tuple[int, ...]) -> list[int]:
    """Formal min-plus convolution of two finite coefficient vectors."""
    out = []
    for k in range(len(a) + len(b) - 1):
        lo = max(0, k - len(b) + 1)
        hi = min(len(a) - 1, k)
        out.append(min(a[i] + b[k - i] for i in range(lo, hi + 1)))
    return out


def _public_coefficients(inst: dict) -> list[int]:
    n = inst["n"]
    terms = inst["terms"]
    by_degree = {int(degree): int(value) for degree, value in terms}
    if len(by_degree) != 2 * n + 1 or set(by_degree) != set(range(2 * n + 1)):
        raise ValueError("instance terms do not contain every degree exactly once")
    return [by_degree[i] for i in range(2 * n + 1)]


def _coefficient_bounds(inst: dict) -> list[int]:
    """Obvious bounds implied by the two zero endpoints.

    For 1 <= i < n, the product contains both a_i+0 and b_i+0 at
    degrees i and n+i, so both hidden coefficients are at least the larger
    public coefficient at those degrees.
    """
    n = inst["n"]
    c = _public_coefficients(inst)
    return [0] + [max(c[i], c[n + i]) for i in range(1, n)] + [0]


def make_instance(n, seed=0, **params) -> dict:
    """Plant two factors first, then expose their formal tropical product.

    ``n`` is the degree of each hidden factor.  ``coefficient_max`` is the
    inclusive upper bound on every hidden coefficient.  Both endpoint
    coefficients are fixed to zero; all other coefficients are sampled i.i.d.
    from the same uniform distribution.
    """
    coefficient_max = params.pop("coefficient_max", 127)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if (isinstance(coefficient_max, bool) or
            not isinstance(coefficient_max, int) or coefficient_max < 1):
        raise ValueError("coefficient_max must be a positive integer")

    rng = random.Random(seed)
    factor_a = [0]
    factor_a.extend(rng.randint(1, coefficient_max) for _ in range(n - 1))
    factor_a.append(0)
    factor_b = [0]
    factor_b.extend(rng.randint(1, coefficient_max) for _ in range(n - 1))
    factor_b.append(0)
    product = _tropical_product(factor_a, factor_b)

    # Terms are deliberately not presented in degree order.  Their order is
    # only input formatting, not mathematical structure; canonical_key sorts.
    terms = [[degree, value] for degree, value in enumerate(product)]
    rng.shuffle(terms)
    return {
        "family": "equal_degree_formal_tropical_factorization_v1",
        "n": n,
        "coefficient_max": coefficient_max,
        "terms": terms,
        "answer": {"factor_a": factor_a, "factor_b": factor_b},
    }


def render(inst) -> str:
    """Render a complete standalone problem statement."""
    n = inst["n"]
    coefficient_max = inst["coefficient_max"]
    terms = sorted(inst["terms"], key=lambda item: item[0])
    term_lines = "\n".join(f"{degree}: {value}" for degree, value in terms)
    example_a = [0] * (n + 1)
    example_b = [0] * (n + 1)
    return f"""FORMAL TROPICAL POLYNOMIAL FACTORIZATION

A coefficient list A=[a_0,...,a_n] denotes a formal one-variable
polynomial.  Tropical multiplication of A and B=[b_0,...,b_n] is the
coefficient list C=[c_0,...,c_{{2n}}] defined exactly by

    c_k = min(a_i + b_j over all integers i,j with 0<=i,j<=n and i+j=k).

The plus sign inside that formula is ordinary integer addition.  Equality is
equality of every formal coefficient, not merely equality of the functions
obtained by evaluating the polynomials.

Here n={n}.  Find two lists A and B, each containing exactly {n + 1} ordinary
    integers.  Both lists must have endpoint coefficients zero,
a_0=a_{n}=b_0=b_{n}=0.  Every non-endpoint entry must lie in the inclusive
range [1,{coefficient_max}].  A and B may be equal; no entries may be omitted;
repeated coefficient values are allowed.  The order of the two factors does
not matter, but the position within each list is its degree and is 0-indexed.
Their tropical product must equal the public C below at every degree.

Public coefficients, one line as "degree: coefficient":
{term_lines}

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys "factor_a" and "factor_b", whose values are the two integer
lists in increasing degree order.
Example of the required shape (the values shown are only a format example):
<answer>{{"factor_a":{json.dumps(example_a)},"factor_b":{json.dumps(example_b)}}}</answer>
Output nothing else inside the tags."""


def _strip_fence(text: str) -> str:
    body = text.strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            body = "\n".join(lines).strip()
    return body


def _decode_answer_body(body: str) -> object | None:
    body = _strip_fence(body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        try:
            value = ast.literal_eval(body)
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            return None
    if not isinstance(value, dict):
        return None
    if "factor_a" not in value or "factor_b" not in value:
        return None
    return value


def parse_answer(text) -> object | None:
    """Extract a tagged JSON (or harmless Python-literal) answer; never raise."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    for body in reversed(matches):
        value = _decode_answer_body(body)
        if value is not None:
            return value

    # Be liberal when a solver supplies the requested object in a Markdown
    # fence but accidentally omits the tags.  JSONDecoder can start amid prose.
    decoder = json.JSONDecoder()
    for match in reversed(list(re.finditer(r"\{", text))):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and "factor_a" in value and "factor_b" in value:
            return value
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check a candidate factorization without consulting ``inst['answer']``."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if "factor_a" not in answer or "factor_b" not in answer:
        return False, "answer is missing factor_a or factor_b"
    a = answer["factor_a"]
    b = answer["factor_b"]
    if not isinstance(a, list) or not isinstance(b, list):
        return False, "factor_a and factor_b must both be lists"
    if not a or not b:
        return False, "factor lists must not be empty"

    n = inst["n"]
    if len(a) != n + 1:
        return False, f"factor_a must contain exactly {n + 1} coefficients"
    if len(b) != n + 1:
        return False, f"factor_b must contain exactly {n + 1} coefficients"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in a + b):
        return False, "all factor coefficients must be ordinary integers"
    if a[0] != 0 or a[-1] != 0 or b[0] != 0 or b[-1] != 0:
        return False, "both endpoint coefficients of both factors must be zero"
    coefficient_max = inst["coefficient_max"]
    if any(x < 1 or x > coefficient_max for x in a[1:-1] + b[1:-1]):
        return False, ("a non-endpoint factor coefficient is outside the "
                       f"inclusive range [1,{coefficient_max}]")

    try:
        expected = _public_coefficients(inst)
    except (KeyError, TypeError, ValueError):
        return False, "instance has malformed public coefficients"
    # Compare degree-by-degree and stop early.  Besides giving a useful reason,
    # this makes the 200k structure-aware guess experiment inexpensive.
    for k, want in enumerate(expected):
        lo = max(0, k - n)
        hi = min(n, k)
        got = min(a[i] + b[k - i] for i in range(lo, hi + 1))
        if got != want:
            return False, f"product mismatch at degree {k}: expected {want}, got {got}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample from a solver-aware prior, not the raw coefficient cube.

    Endpoint zeros, coefficient bounds forced by the public product, and the
    exact two-term equations at degrees 1 and 2n-1 are all imposed before the
    candidate is returned.  The remaining choices are independent and do not
    use or favor the planted witness.
    """
    n = inst["n"]
    coefficient_max = inst["coefficient_max"]
    c = _public_coefficients(inst)
    lower = _coefficient_bounds(inst)
    lower[1:-1] = [max(1, value) for value in lower[1:-1]]
    a = [0] + [rng.randint(lower[i], coefficient_max) for i in range(1, n)] + [0]
    b = [0] + [rng.randint(lower[i], coefficient_max) for i in range(1, n)] + [0]

    # c_1=min(a_1,b_1) and c_{2n-1}=min(a_{n-1},b_{n-1}) follow immediately
    # from the two endpoint-zero rules, so an informed guesser gets them free.
    for i, target in ((1, c[1]), (n - 1, c[2 * n - 1])):
        if rng.randrange(2):
            a[i] = target
            b[i] = rng.randint(max(lower[i], target), coefficient_max)
        else:
            b[i] = target
            a[i] = rng.randint(max(lower[i], target), coefficient_max)
    return {"factor_a": a, "factor_b": b}


def search_space(inst) -> int | None:
    """Ordered endpoint-zero coefficient pairs in the naive bounded cube."""
    n = inst["n"]
    coefficient_max = inst["coefficient_max"]
    return coefficient_max ** (2 * (n - 1))


def enumerate_all(inst) -> int | None:
    """Count ordered valid witnesses exactly when the raw cube is small."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    coefficient_max = inst["coefficient_max"]
    expected = _public_coefficients(inst)
    vectors = [
        (0,) + middle + (0,)
        for middle in itertools.product(range(1, coefficient_max + 1), repeat=n - 1)
    ]
    count = 0
    for a in vectors:
        for b in vectors:
            if _tropical_product(a, b) == expected:
                count += 1
    return count


def canonical_key(inst) -> str:
    """Canonicalize term order and the degree-reversal symmetry."""
    n = inst["n"]
    coefficient_max = inst["coefficient_max"]
    coeffs = tuple(_public_coefficients(inst))
    normalized = min(coeffs, tuple(reversed(coeffs)))
    payload = json.dumps(
        ["equal_degree_formal_tropical_factorization_v1", n,
         coefficient_max, normalized], separators=(",", ":")
    ).encode("ascii")
    return "tropfact-v1:" + hashlib.sha256(payload).hexdigest()


def escalate(params) -> dict | None:
    """Increase growing degree while keeping the paper's coefficient range."""
    if "n" not in params:
        return None
    n = params["n"]
    coefficient_max = params.get("coefficient_max", 127)
    if n >= 600:
        return None
    return {"n": max(n + 1, (3 * n) // 2),
            "coefficient_max": coefficient_max}


def _copy_answer(answer: dict) -> dict:
    return {"factor_a": list(answer["factor_a"]),
            "factor_b": list(answer["factor_b"])}


def _outlier_attack_candidates(inst: dict) -> list[dict]:
    """Candidates based only on per-degree lower-envelope statistics."""
    n = inst["n"]
    r = inst["coefficient_max"]
    lower = _coefficient_bounds(inst)
    lower[1:-1] = [max(1, value) for value in lower[1:-1]]
    envelope = list(lower)
    high = [0] + [r] * (n - 1) + [0]
    return [
        {"factor_a": list(envelope), "factor_b": list(envelope)},
        {"factor_a": list(envelope), "factor_b": list(high)},
        {"factor_a": list(high), "factor_b": list(envelope)},
    ]


def _greedy_attack(inst: dict) -> dict | None:
    """A cheap first-mismatch repair heuristic, with no backtracking."""
    n = inst["n"]
    r = inst["coefficient_max"]
    target = _public_coefficients(inst)
    lower = _coefficient_bounds(inst)
    lower[1:-1] = [max(1, value) for value in lower[1:-1]]
    a = [0] + [r] * (n - 1) + [0]
    b = [0] + [r] * (n - 1) + [0]

    for k in range(1, 2 * n):
        product = _tropical_product(a, b)
        if product[k] == target[k]:
            continue
        if product[k] < target[k]:
            return None
        repaired = False
        lo = max(0, k - n)
        hi = min(n, k)
        for i in range(lo, hi + 1):
            j = k - i
            low_x = lower[i]
            high_x = min(a[i], r, target[k] - lower[j])
            if low_x > high_x:
                continue
            choices = [high_x, low_x, target[k] // 2]
            seen = set()
            for x in choices:
                x = max(low_x, min(high_x, x))
                y = target[k] - x
                if (x, y) in seen:
                    continue
                seen.add((x, y))
                if not (lower[j] <= y <= b[j] and y <= r):
                    continue
                old_a, old_b = a[i], b[j]
                a[i], b[j] = x, y
                trial = _tropical_product(a, b)
                if trial[k] == target[k] and all(
                        trial[d] >= target[d] for d in range(2 * n + 1)):
                    repaired = True
                    break
                a[i], b[j] = old_a, old_b
            if repaired:
                break
        if not repaired:
            return None
    return {"factor_a": a, "factor_b": b}


def _transformed_instance(inst: dict, *, reverse_degrees=False,
                          reorder_seed=None) -> dict:
    clone = {
        "family": inst["family"],
        "n": inst["n"],
        "coefficient_max": inst["coefficient_max"],
        "terms": [list(term) for term in inst["terms"]],
        "answer": _copy_answer(inst["answer"]),
    }
    if reverse_degrees:
        top = 2 * inst["n"]
        clone["terms"] = [[top - degree, value] for degree, value in clone["terms"]]
        clone["answer"] = {
            "factor_a": list(reversed(clone["answer"]["factor_a"])),
            "factor_b": list(reversed(clone["answer"]["factor_b"])),
        }
    if reorder_seed is not None:
        random.Random(reorder_seed).shuffle(clone["terms"])
    return clone


def selftest() -> dict:
    """Run mandatory G1--G8 gates and return their measured evidence."""
    report: dict[str, Any] = {}

    # G1: every preset, several seeds.
    g1_failures = []
    g1_cases = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 23, 99991):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_cases += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "cases": g1_cases, "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=13579, **shipping_params)
    planted = base["answer"]

    # G2: five concrete corruption classes, with distinct diagnostics.
    corruptions = {}
    drop = _copy_answer(planted)
    drop["factor_a"].pop(n := max(1, base["n"] // 2))
    corruptions["drop_one"] = drop

    duplicate = _copy_answer(planted)
    duplicate["factor_b"].insert(max(1, base["n"] // 3),
                                 duplicate["factor_b"][max(1, base["n"] // 3)])
    corruptions["duplicate_one"] = duplicate

    empty = _copy_answer(planted)
    empty["factor_a"] = []
    corruptions["empty"] = empty

    outside = _copy_answer(planted)
    outside["factor_a"][1] = base["coefficient_max"] + 1
    corruptions["out_of_range"] = outside

    swapped = None
    for factor_name in ("factor_a", "factor_b"):
        for i in range(1, base["n"] - 1):
            for j in range(i + 1, base["n"]):
                if planted[factor_name][i] == planted[factor_name][j]:
                    continue
                trial = _copy_answer(planted)
                trial[factor_name][i], trial[factor_name][j] = (
                    trial[factor_name][j], trial[factor_name][i])
                if not verify(base, trial)[0]:
                    swapped = trial
                    break
            if swapped is not None:
                break
        if swapped is not None:
            break
    corruptions["swap_two_positions"] = swapped

    g2_results = {}
    for name, candidate in corruptions.items():
        if candidate is None:
            g2_results[name] = "could not construct rejected swap corruption"
        else:
            ok, why = verify(base, candidate)
            g2_results[name] = "UNEXPECTEDLY ACCEPTED" if ok else why
    reasons = list(g2_results.values())
    g2_pass = (all(reason != "UNEXPECTEDLY ACCEPTED" for reason in reasons) and
               "could not construct rejected swap corruption" not in reasons and
               len(set(reasons)) == len(reasons))
    report["G2_rejects_corruption"] = {
        "pass": g2_pass, "rejections": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: exact format, Markdown fence inside tags, and surrounding prose.
    encoded = json.dumps(planted, separators=(",", ":"))
    realistic = ("I used the endpoint constraints and checked every antidiagonal.\n\n"
                 "<answer>\n```json\n" + encoded + "\n```\n</answer>\n"
                 "The lists are in degree order.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted, "tagged_fenced_prose": parsed == planted,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }
    report["G3_round_trip"]["pass"] = bool(
        report["G3_round_trip"]["pass"] and
        report["G3_round_trip"]["garbage_returns_none"])

    # G4: at least 200k samples from the structure-aware candidate prior.
    guess_inst = make_instance(seed=24681357, **shipping_params)
    guess_rng = random.Random(97531)
    total = 200_000
    hits = 0
    for _ in range(total):
        hits += int(verify(guess_inst, random_candidate(guess_inst, guess_rng))[0])
    rate = hits / total
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": total,
        "rate": rate,
        "naive_search_space": str(search_space(guess_inst)),
        "prior": ("uniform independent coefficients conditional on endpoint zeros, "
                  "all public endpoint-derived lower bounds, and the exact degree-1 "
                  "and degree-(2n-1) minimum constraints"),
    }

    # G5: a deliberately enumerable member, not a misleading extrapolation.
    small = make_instance(n=4, coefficient_max=7, seed=6)
    valid_count = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if valid_count is None else valid_count / small_space
    report["G5_sparse"] = {
        "pass": valid_count is not None and fraction is not None and fraction < 1e-3,
        "instance": {"n": 4, "coefficient_max": 7, "seed": 6},
        "valid_ordered_answers": valid_count,
        "naive_search_space": small_space,
        "fraction": fraction,
        "shipping_enumeration": enumerate_all(guess_inst),
    }

    # G6: attacks designed around this planting scheme, over eight fixed seeds.
    attack_seeds = list(range(800, 808))
    outlier_successes = 0
    greedy_successes = 0
    restart_successes = 0
    outlier_attempts = 0
    greedy_attempts = 0
    restart_attempts = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        outliers = _outlier_attack_candidates(inst)
        outlier_attempts += len(outliers)
        if any(verify(inst, candidate)[0] for candidate in outliers):
            outlier_successes += 1
        greedy_attempts += 1
        greedy = _greedy_attack(inst)
        if greedy is not None and verify(inst, greedy)[0]:
            greedy_successes += 1
        restart_rng = random.Random(10_000_000 + seed)
        seed_hit = False
        for _ in range(64):
            restart_attempts += 1
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                seed_hit = True
        restart_successes += int(seed_hit)
    attack_report = {
        "outlier_lower_envelope": {
            "seed_successes": outlier_successes, "seeds": len(attack_seeds),
            "candidate_attempts": outlier_attempts,
        },
        "greedy_first_mismatch_repair": {
            "seed_successes": greedy_successes, "seeds": len(attack_seeds),
            "candidate_attempts": greedy_attempts,
        },
        "structure_aware_random_restart_64": {
            "seed_successes": restart_successes, "seeds": len(attack_seeds),
            "candidate_attempts": restart_attempts,
        },
    }
    report["G6_adversary_panel"] = {
        "pass": all(row["seed_successes"] == 0 for row in attack_report.values()),
        "difficulty": SHIPPING_DIFFICULTY,
        "attacks": attack_report,
    }

    # G7: double the actual shipping degree, rebuild, and verify.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and search_space(doubled) > search_space(guess_inst)),
        "base_n": shipping_params["n"], "doubled_n": doubled_params["n"],
        "doubled_planted_verifies": doubled_ok,
        "verify_reason": doubled_why,
        "search_space_increased": search_space(doubled) > search_space(guess_inst),
    }

    # G8: input reorder, degree reversal, and their composition over 20 seeds.
    g8_seeds = list(range(20_000, 20_020))
    invariance_checks = 0
    witness_checks = 0
    keys = []
    g8_failures = []
    for seed in g8_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        key = canonical_key(inst)
        keys.append(key)
        variants = [
            _transformed_instance(inst, reorder_seed=seed + 1),
            _transformed_instance(inst, reverse_degrees=True),
            _transformed_instance(inst, reverse_degrees=True,
                                  reorder_seed=seed + 2),
        ]
        for number, variant in enumerate(variants):
            invariance_checks += 1
            if canonical_key(variant) != key:
                g8_failures.append({"seed": seed, "variant": number,
                                    "kind": "key changed"})
            witness_checks += 1
            ok, why = verify(variant, variant["answer"])
            if not ok:
                g8_failures.append({"seed": seed, "variant": number,
                                    "kind": "mapped witness failed", "reason": why})
        # Commutativity is a witness symmetry, though it does not alter C.
        swapped_factors = {"factor_a": list(inst["answer"]["factor_b"]),
                           "factor_b": list(inst["answer"]["factor_a"])}
        witness_checks += 1
        ok, why = verify(inst, swapped_factors)
        if not ok:
            g8_failures.append({"seed": seed, "kind": "factor swap failed",
                                "reason": why})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == len(g8_seeds),
        "seeds": len(g8_seeds),
        "invariance_checks": invariance_checks,
        "mapped_witness_checks": witness_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": len(g8_seeds),
        "transformations": ["input-term permutation", "degree reversal",
                            "degree reversal composed with input-term permutation",
                            "factor-order witness swap"],
        "failures": g8_failures,
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
