"""Verified Proposition 2.8 triple collisions from arXiv:2408.13867.

At q=2 and s>=3 the paper's twelve entries have one sign; negating them
gives four positive triples.  The module constructs those witnesses first,
then hides them among multiplicative partitions of the same factor multiset.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "four positive integer triples",
        "Proposition 2.8 multiplicative factor incidences",
        "common integer sum and product",
    ],
    "verification_operations": [
        "exact integer addition",
        "exact integer multiplication",
        "exact normalized triple membership",
        "exact equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "ansatz",
    "intuition_description": (
        "Recognize Proposition 2.8's four-by-three factor-incidence ansatz; "
        "without that pattern one must compute and bucket every displayed "
        "triple by its exact sum."
    ),
    "hardness_basis": (
        "Track B: expected-O(n) exact sum hashing solves every instance; at "
        "the shipping n=2400 preset the measured eight-instance reference "
        "panel used 76,300 counted operations (9,537 per instance) in 0.011 "
        "seconds, whereas the recognized Proposition 2.8 incidence pattern "
        "needs 48 exact operations."
    ),
    "max_answer_tokens": 71,
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

DIFFICULTY = {
    "demo": {"n": 10, "s_min": 3, "s_max": 3},
    "easy": {"n": 1000, "s_min": 11, "s_max": 31},
    "medium": {"n": 1600, "s_min": 19, "s_max": 47},
    "hard": {"n": 2400, "s_min": 28, "s_max": 61},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The target rows share a four-by-three incidence pattern separating the "
    "three distinguished factors c, e, and f."
)
PLACEBO_HINT = (
    "The target rows should be copied with care because each comparison uses "
    "every displayed integer in its exact form."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A lexicographically increasing JSON list of exactly four distinct "
        "displayed rows; every row is a nondecreasing list of three positive "
        "integers."
    ),
    "bounds": {
        "rows": 4,
        "entries_per_row": 3,
        "candidate_source": "the n displayed normalized pool rows",
        "candidate_count": "binomial(n,4)",
        "maximum_named_n": 2400,
    },
}

# Updated only from isolated harden.py runs. Provider errors count as no attempt.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Definition and source. Section 1, Problem 1.1 defines S_l(M,N) as l triples
of positive integers with equal sums and equal products. Proposition 2.8 is
the paper's new two-parameter solution for l=4,n=1. Its proof starts with four
explicit multiplicative regroupings and solves the three sum equalities. This
module uses precisely those integer triples, not a graph or other surrogate.

Step-0 decision. The paper proves parametric constructions and elliptic-curve
rank bounds, not computational hardness. Track A would be unsupported. Track B
is explicit: hashing all displayed rows by exact sum takes expected O(n) time
and always solves. Proposition 2.8 is the compact alternative. With auxiliary
values displayed, its twelve entries take 40 multiplications and checking the
four sums takes 8 additions, for 48 exact operations.

Positive theorem-backed regime. Set q=2 and s=u+3 with u>=0. Then t1, t2,
-t3, -t4 and t5 become
  4u^2+18u+19,
  7u^2+31u+32,
  7u^4+50u^3+130u^2+148u+63,
  4u^5+48u^4+217u^3+468u^2+488u+199,
  6u^7+110u^6+808u^5+3142u^4+7071u^3+9293u^2+6651u+2011.
All coefficients are positive. The twelve Proposition 2.8 entries are negative
in this regime; the structure-preserving map x -> -x makes them positive while
retaining their common sum and product. No search selects a valid parameter or
discovers the witness.

Generation. The four certified rows are formed first. Every plant and decoy is
a three-block multiplicative partition of {q,s,d,d,v,a,a,a,a,b,c,e,f}, where
d=s-1, v=s^2-q, a=t1, b=t2, c=-t3, e=-t4 and f=t5. Decoys with the target sum
are excluded and every other sum bucket is capped at three, making the planted
four-row bucket unique. This filtering protects uniqueness; it does not find
the stored witness.

Easy regimes and attacks. Proposition 2.8 itself is the successful compact
route, and exact sum hashing is the successful reference algorithm. The failing
panel probes position/magnitude, row balance, the conspicuous a^2 grouping,
separation of c,e,f, 256 uniform legal restarts, and a cyclic factor ansatz.
Every row comes from the same whole-factor partition universe. Difficulty grows
by crowding the pool and widening s while the twelve-integer answer stays fixed.

Canonicalization. Reordering candidate rows, permuting coordinates inside any
row, and compositions preserve the problem. The key normalizes both levels and
includes every labeled clue value, but never the seed or rendered text. Labels
are not interchangeable because they denote the roles in Proposition 2.8.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_WRONG_PATTERNS = (
    (0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 2),
    (0, 0, 1, 1, 2, 2, 0, 0, 1, 1, 2, 2, 2),
    (0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 2),
    (0, 1, 1, 2, 2, 0, 0, 1, 1, 2, 2, 0, 2),
)


def _validate_parameters(n: int, s_min: int, s_max: int) -> None:
    for name, value in (("n", n), ("s_min", s_min), ("s_max", s_max)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 4:
        raise ValueError("n must be at least 4")
    if s_min < 3 or s_max < s_min:
        raise ValueError("require 3 <= s_min <= s_max")
    if n > 30_000:
        raise ValueError("n exceeds the supported distinct-partition pool")


def _auxiliary(s: int) -> tuple[int, int, int, int, int]:
    """Return (t1,t2,-t3,-t4,t5) in the q=2, s>=3 regime."""
    u = s - 3
    a = 4 * u**2 + 18 * u + 19
    b = 7 * u**2 + 31 * u + 32
    c = 7 * u**4 + 50 * u**3 + 130 * u**2 + 148 * u + 63
    e = (4 * u**5 + 48 * u**4 + 217 * u**3 + 468 * u**2
         + 488 * u + 199)
    f = (6 * u**7 + 110 * u**6 + 808 * u**5 + 3142 * u**4
         + 7071 * u**3 + 9293 * u**2 + 6651 * u + 2011)
    return a, b, c, e, f


def _factor_slots(s: int) -> tuple[int, ...]:
    q, d, v = 2, s - 1, s * s - 2
    a, b, c, e, f = _auxiliary(s)
    return (q, s, d, d, v, a, a, a, a, b, c, e, f)


def _paper_rows(s: int) -> list[list[int]]:
    """Globally negated positive form of Proposition 2.8."""
    q, d, v = 2, s - 1, s * s - 2
    a, b, c, e, f = _auxiliary(s)
    rows = [
        [d * a * b * c, s * q * d * a * f, v * a * a * e],
        [d * q * a * b * c, a * a * f, d * s * v * a * e],
        [d * a * f, d * q * a * b * e, s * v * a * a * c],
        [d * q * a * f, d * s * a * b * e, v * a * a * c],
    ]
    return sorted(sorted(row) for row in rows)


def _signature(row: list[int] | tuple[int, int, int]) -> tuple[int, int]:
    return row[0] + row[1] + row[2], row[0] * row[1] * row[2]


def _partition_row(factors: tuple[int, ...], labels: list[int] | tuple[int, ...]) -> list[int]:
    products = [1, 1, 1]
    for value, label in zip(factors, labels):
        products[label] *= value
    return sorted(products)


def _wrong_incidence_rows(s: int) -> list[list[int]]:
    factors = _factor_slots(s)
    return sorted(_partition_row(factors, pattern) for pattern in _WRONG_PATTERNS)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct Proposition 2.8's witness, then add same-universe decoys."""
    s_min = params.pop("s_min", 19)
    s_max = params.pop("s_max", 47)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, s_min, s_max)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    s = rng.randint(s_min, s_max)
    factors = _factor_slots(s)
    answer = _paper_rows(s)
    target_signature = _signature(answer[0])
    if min(value for row in answer for value in row) <= 0:
        raise AssertionError("the q=2,s>=3 positivity construction failed")
    if len({tuple(row) for row in answer}) != 4:
        raise AssertionError("Proposition 2.8 produced repeated triples")
    if any(_signature(row) != target_signature for row in answer):
        raise AssertionError("Proposition 2.8 sum/product identity failed")

    pool_set = {tuple(row) for row in answer}
    sum_counts = {target_signature[0]: 4}

    def add_decoy(row: list[int]) -> bool:
        key, row_sum = tuple(row), sum(row)
        if key in pool_set or row_sum == target_signature[0]:
            return False
        if sum_counts.get(row_sum, 0) >= 3:
            return False
        pool_set.add(key)
        sum_counts[row_sum] = sum_counts.get(row_sum, 0) + 1
        return True

    if n > len(answer) + len(_WRONG_PATTERNS):
        for row in _wrong_incidence_rows(s):
            add_decoy(row)

    attempts = 0
    demo_bound = 20 * max(value for row in answer for value in row)
    while len(pool_set) < n:
        attempts += 1
        if attempts > 2000 * n + 100_000:
            raise RuntimeError("could not generate enough distinct decoys")
        labels = [rng.randrange(3) for _ in factors]
        if len(set(labels)) != 3:
            continue
        row = _partition_row(factors, labels)
        if n <= 10 and row[-1] > demo_bound:
            continue
        add_decoy(row)

    pool = [list(row) for row in sorted(pool_set)]
    common_product = math.prod(answer[0])
    if any(math.prod(row) != common_product for row in pool):
        raise AssertionError("same-product decoy construction failed")
    a, b, c, e, f = _auxiliary(s)
    return {
        "family": "four positive triples with equal sum and product",
        "n": n,
        "pool": pool,
        "_pool_normalized": True,
        "clue": {
            "q": 2, "s": s, "d": s - 1, "v": s * s - 2,
            "a": a, "b": b, "c": c, "e": e, "f": f,
            "factor_multiset": list(factors),
        },
        "answer": answer,
    }


def render(inst: dict) -> str:
    clue = inst["clue"]
    rows = "\n".join(
        f"{index}: {row[0]}, {row[1]}, {row[2]}"
        for index, row in enumerate(inst["pool"])
    )
    common_product = math.prod(inst["pool"][0])
    statement = f"""Equal-sum/equal-product triples

Below are {len(inst['pool'])} candidate triples of positive integers. A triple
is unordered, so every row is printed in nondecreasing order. Every candidate
row already has the same product

P = {common_product}.

Find four distinct printed rows whose three integers have exactly the same
sum. Since every candidate has product P, your rows then have both equal sum
and equal product.

The order of the four chosen rows does not matter mathematically, but your
answer must use the normalization specified below. No row may be repeated or
invented: each complete triple must occur in the candidate list.

Construction labels (all labels are distinct roles, even when values repeat):
q={clue['q']}, s={clue['s']}, d={clue['d']}, v={clue['v']},
a={clue['a']}, b={clue['b']}, c={clue['c']}, e={clue['e']}, f={clue['f']}.
Every displayed row is obtained by splitting the following complete multiset
into three nonempty blocks and multiplying within each block:
q, s, d, d, v, a, a, a, a, b, c, e, f.
The labels come from one integer identity; recognizing its factor-incidence
pattern is optional but can avoid scanning all rows.

Candidate rows (indices are only labels; do not output them):
{rows}

Give your final answer inside <answer></answer> tags as JSON: a list of exactly
four rows, each row a list of exactly three positive integers. Sort each row
in nondecreasing order, then sort the four rows lexicographically. Repeats are
not allowed.
Shape-only syntax example (not a valid solution):
<answer>[[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        payload = match.group(1).strip()
    else:
        fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.I | re.S)
        if not fenced:
            return None
        payload = fenced.group(1).strip()
    if payload.startswith("```") and payload.endswith("```"):
        payload = re.sub(r"^```(?:json)?\s*|\s*```$", "", payload,
                         flags=re.I | re.S)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _normalized_pool(inst: dict) -> list[tuple[int, int, int]]:
    return sorted(tuple(sorted(row)) for row in inst.get("pool", []))


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list) or len(answer) != 4:
        return False, "answer must be a list of exactly four triples"
    if any(not isinstance(row, list) or len(row) != 3 for row in answer):
        return False, "each triple must be a list of exactly three integers"
    if any(isinstance(value, bool) or not isinstance(value, int)
           for row in answer for value in row):
        return False, "every entry must be an integer"
    if any(value <= 0 for row in answer for value in row):
        return False, "every entry must be a positive integer"
    if any(row != sorted(row) for row in answer):
        return False, "each triple must be in nondecreasing order"
    row_keys = [tuple(row) for row in answer]
    if len(set(row_keys)) != 4:
        return False, "the four triples must be distinct"
    if row_keys != sorted(row_keys):
        return False, "the four triples must be lexicographically increasing"

    if inst.get("_pool_normalized") is True:
        pool = inst.get("pool", [])
        for row in answer:
            at = bisect.bisect_left(pool, row)
            if at == len(pool) or pool[at] != row:
                return False, "every submitted triple must occur in the candidate pool"
    else:
        pool_keys = set(_normalized_pool(inst))
        if any(row not in pool_keys for row in row_keys):
            return False, "every submitted triple must occur in the candidate pool"
    if len({sum(row) for row in answer}) != 1:
        return False, "the four triples do not have one common sum"
    if len({math.prod(row) for row in answer}) != 1:
        return False, "the four triples do not have one common product"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    indices = rng.sample(range(len(inst["pool"])), 4)
    return sorted([list(inst["pool"][index]) for index in indices])


def search_space(inst: dict) -> int:
    return math.comb(len(inst["pool"]), 4)


def enumerate_all(inst: dict) -> int:
    buckets: dict[tuple[int, int], int] = {}
    for row in _normalized_pool(inst):
        sig = _signature(row)
        buckets[sig] = buckets.get(sig, 0) + 1
    return sum(math.comb(count, 4) for count in buckets.values() if count >= 4)


def canonical_key(inst: dict) -> str:
    clue = inst.get("clue", {})
    payload = {
        "pool": [list(row) for row in _normalized_pool(inst)],
        "clue": {name: clue.get(name) for name in
                 ("q", "s", "d", "v", "a", "b", "c", "e", "f")},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    current_n = int(params.get("n", 1000))
    next_n = max(current_n + 400, (current_n * 3) // 2)
    if next_n > 30_000:
        return None
    width = max(1, int(params.get("s_max", 47)) - int(params.get("s_min", 19)))
    return {
        "n": next_n,
        "s_min": int(params.get("s_min", 19)) + max(2, width // 3),
        "s_max": int(params.get("s_max", 47)) + max(4, width // 2),
    }


def _reference_sum_hash(inst: dict) -> tuple[list[list[int]] | None, int]:
    buckets: dict[int, list[list[int]]] = {}
    operations = 0
    for raw in inst["pool"]:
        row = sorted(raw)
        row_sum = row[0] + row[1] + row[2]
        operations += 3  # two additions and one expected-O(1) table update
        buckets.setdefault(row_sum, []).append(row)
    for bucket in buckets.values():
        operations += 1
        if len(bucket) >= 4:
            return sorted(bucket[:4]), operations
    return None, operations


def _compact_incidence(inst: dict) -> tuple[list[list[int]], int]:
    return _paper_rows(inst["clue"]["s"]), 48


def _attack_outlier_magnitude(inst: dict) -> tuple[list[list[int]], int]:
    rows = inst["pool"]
    maxima = sorted(row[-1] for row in rows)
    median = maxima[len(maxima) // 2]
    chosen = sorted(rows, key=lambda row: (abs(row[-1] - median), row))[:4]
    return sorted([list(row) for row in chosen]), len(rows)


def _attack_greedy_balanced(inst: dict) -> tuple[list[list[int]], int]:
    chosen = sorted(inst["pool"], key=lambda row: (row[-1] - row[0], row))[:4]
    return sorted([list(row) for row in chosen]), len(inst["pool"])


def _capped_valuation(value: int, factor: int, cap: int = 4) -> int:
    count = 0
    while count < cap and value % factor == 0:
        value //= factor
        count += 1
    return count


def _attack_a_square_balance(inst: dict) -> tuple[list[list[int]], int]:
    """Exploit the visible fact that every target row has one a^2 entry."""
    a = inst["clue"]["a"]

    def score(row: list[int]) -> tuple[int, int, list[int]]:
        valuations = sorted(_capped_valuation(value, a) for value in row)
        penalty = sum(abs(x - y) for x, y in zip(valuations, (1, 1, 2)))
        return penalty, row[-1] - row[0], row

    chosen = sorted(inst["pool"], key=score)[:4]
    return sorted([list(row) for row in chosen]), 3 * len(inst["pool"])


def _attack_distinguished_separation(inst: dict) -> tuple[list[list[int]], int]:
    """Prefer rows placing c,e,f separately, another planted incidence trait."""
    special = [inst["clue"][name] for name in ("c", "e", "f")]

    def score(row: list[int]) -> tuple[int, int, list[int]]:
        collisions = 0
        for value in row:
            hits = sum(value % factor == 0 for factor in special)
            collisions += max(0, hits - 1)
        return collisions, row[-1] - row[0], row

    chosen = sorted(inst["pool"], key=score)[:4]
    return sorted([list(row) for row in chosen]), 3 * len(inst["pool"])


def _attack_wrong_ansatz(inst: dict) -> tuple[list[list[int]], int]:
    return _wrong_incidence_rows(inst["clue"]["s"]), 52


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer)

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, list):
            return sum(atoms(item) for item in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def _worst_supported_answer_metrics(s_min: int, s_max: int) -> tuple[int, int, int, int]:
    worst = (0, 0, 0)
    cases = 0
    for s in range(s_min, s_max + 1):
        cases += 1
        worst = max(worst, _answer_metrics(_paper_rows(s)))
    return worst[0], worst[1], worst[2], cases


def _moved_instance(inst: dict, rng: random.Random,
                    permute_coordinates: bool, reorder_rows: bool) -> dict:
    moved = {key: value for key, value in inst.items() if key not in ("pool", "answer")}
    pool = [list(row) for row in inst["pool"]]
    if permute_coordinates:
        for row in pool:
            rng.shuffle(row)
    if reorder_rows:
        rng.shuffle(pool)
    moved["pool"] = pool
    moved["_pool_normalized"] = False
    moved["answer"] = json.loads(json.dumps(inst["answer"]))
    return moved


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "arXiv:2408.13867",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=240813867, **shipping)

    checks, json_round_trips = [], 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            serial_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks.append({"preset": preset, "seed": seed, "ok": ok,
                           "reason": reason, "json_native": serial_ok})
            json_round_trips += int(serial_ok)
    report["G1_planted_verifies"] = {
        "pass": all(item["ok"] and item["json_native"] for item in checks),
        "checks": checks,
        "verified": sum(int(item["ok"]) for item in checks),
        "json_round_trips": json_round_trips,
    }

    answer = json.loads(json.dumps(ship["answer"]))
    dropped = json.loads(json.dumps(answer)); dropped[0] = dropped[0][:-1]
    swapped = json.loads(json.dumps(answer)); swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = json.loads(json.dumps(answer)); duplicated[1] = list(duplicated[0])
    outside = json.loads(json.dumps(answer)); outside[0][0] = 0
    malformed_type = json.loads(json.dumps(answer)); malformed_type[0][0] = str(malformed_type[0][0])
    corruptions = {
        "drop": dropped, "swap": swapped, "duplicate": duplicated,
        "empty": [], "out_of_range": outside, "non_integer": malformed_type,
    }
    corruption_results = {
        name: {"accepted": verify(ship, value)[0], "reason": verify(ship, value)[1]}
        for name, value in corruptions.items()
    }
    required = ("drop", "swap", "duplicate", "empty", "out_of_range")
    reasons = [corruption_results[name]["reason"] for name in required]
    report["G2_rejects_corruption"] = {
        "pass": (all(not value["accepted"] for value in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_required_reasons": len(set(reasons)),
    }

    realistic = ("The product follows from the factor multiset.\n```json\n"
                 f"<answer>\n{json.dumps(answer)}\n</answer>\n```\nChecked.")
    fenced = "Here is the result:\n```json\n" + json.dumps(answer) + "\n```"
    parsed, parsed_fenced = parse_answer(realistic), parse_answer(fenced)
    report["G3_round_trip"] = {
        "pass": (parsed == answer and parsed_fenced == answer
                 and verify(ship, parsed)[0] and verify(ship, parsed_fenced)[0]
                 and parse_answer("no answer present") is None),
        "tagged_matches": parsed == answer,
        "untagged_fence_matches": parsed_fenced == answer,
        "garbage_returns_none": parse_answer("no answer present") is None,
    }

    guess_rng, guess_total, guess_hits = random.Random(0x240813867), 200_000, 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits, "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform over all 4-subsets of normalized pool rows",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_median_magnitude", "greedy_most_balanced_rows",
        "a_square_then_balance", "distinguished_factors_separate_then_balance",
        "random_restart_256", "in_context_cyclic_factor_ansatz",
    )
    attacks = {name: {"successes": 0, "attempts": 0, "steps": 0,
                      "wall_clock_sec": 0.0} for name in attack_names}
    ref_successes = ref_operations = compact_successes = compact_operations = 0
    ref_wall = 0.0
    attack_seeds = list(range(800, 808))
    deterministic_attacks = (
        ("outlier_median_magnitude", _attack_outlier_magnitude),
        ("greedy_most_balanced_rows", _attack_greedy_balanced),
        ("a_square_then_balance", _attack_a_square_balance),
        ("distinguished_factors_separate_then_balance", _attack_distinguished_separation),
        ("in_context_cyclic_factor_ansatz", _attack_wrong_ansatz),
    )
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping)
        for name, attack in deterministic_attacks:
            t0 = time.perf_counter()
            candidate, steps = attack(inst)
            elapsed = time.perf_counter() - t0
            stat = attacks[name]
            stat["attempts"] += 1
            stat["successes"] += int(verify(inst, candidate)[0])
            stat["steps"] += steps
            stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = False, 0
        restart_rng = random.Random(seed ^ 0xA11CE)
        for _ in range(256):
            candidate = random_candidate(inst, restart_rng)
            steps += 1
            if verify(inst, candidate)[0]:
                success = True
                break
        stat = attacks["random_restart_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += time.perf_counter() - t0

        t0 = time.perf_counter()
        reference, operations = _reference_sum_hash(inst)
        ref_wall += time.perf_counter() - t0
        ref_operations += operations
        ref_successes += int(reference is not None and verify(inst, reference)[0])
        compact, operations = _compact_incidence(inst)
        compact_operations += operations
        compact_successes += int(verify(inst, compact)[0])

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (all_failed and ref_successes == len(attack_seeds)
                 and compact_successes == len(attack_seeds)),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact integer-sum signature hashing",
            "complexity": "expected O(n) dictionary operations and O(n) exact arithmetic",
            "wall_clock_sec": round(ref_wall, 6),
            "operations": ref_operations,
            "average_operations_per_instance": ref_operations // len(attack_seeds),
            "solves": f"{ref_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route_audit": {
            "name": "Proposition 2.8 four-by-three factor incidence",
            "operations": compact_operations,
            "operations_per_instance": compact_operations // len(attack_seeds),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    exact_solutions = enumerate_all(ship)
    strongest = max(attacks.items(), key=lambda item: item[1]["wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": (exact_solutions >= 1
                 and exact_solutions / search_space(ship) < 1e-6
                 and ref_successes == len(attack_seeds)),
        "shipping_exact_valid_answers": exact_solutions,
        "shipping_candidate_space": search_space(ship),
        "shipping_exact_density": exact_solutions / search_space(ship),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "reference_algorithm_wall_clock_sec": round(ref_wall, 6),
        "reference_algorithm_operations": ref_operations,
        "reference_average_operations": ref_operations // len(attack_seeds),
        "strongest_failing_attack": strongest[0],
        "strongest_failing_attack_wall_clock_sec": strongest[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest[1]["steps"],
    }

    ns = [params["n"] for params in DIFFICULTY.values()]
    doubled_params = dict(shipping); doubled_params["n"] *= 2
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (ns == sorted(set(ns)) and doubled_ok
                 and len(doubled["pool"]) == 2 * len(ship["pool"])
                 and len(doubled["answer"]) == len(ship["answer"])),
        "preset_pool_sizes": dict(zip(DIFFICULTY, ns)),
        "doubled_n": len(doubled["pool"]),
        "answer_elements_unchanged": True,
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = witness_checks = 0
    failures, unrelated_keys = [], []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        rng = random.Random(30_000 + seed)
        variants = (
            _moved_instance(inst, rng, False, True),
            _moved_instance(inst, rng, True, False),
            _moved_instance(inst, rng, True, True),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != key:
                failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, inst["answer"])[0]:
                failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "candidate-row reordering",
            "independent coordinate permutations within every triple",
            "composition of row and coordinate reordering",
        ],
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    worst_chars, worst_tokens, worst_elements, support_cases = (
        _worst_supported_answer_metrics(shipping["s_min"], shipping["s_max"])
    )
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    intended_operations = 48
    within_caps = (worst_chars <= 2000 and worst_elements <= 256
                   and intended_operations <= 300
                   and worst_tokens <= PROBLEM_PROFILE["max_answer_tokens"])
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": tokens,
        "answer_elements": elements,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "worst_case_answer_elements": worst_elements,
        "exhaustively_checked_s_values": support_cases,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "diagnostic_is_not_gated": True,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
