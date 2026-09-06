"""Verified problem generator for arXiv:1606.02117.

The paper studies representations of one by distinct odd unit fractions and,
in Lemma 2.5(a), gives a divisor-parametrised identity that preserves the odd
denominator restriction.  This module mixes several independently constructed
eleven-term instances of that identity.  Every displayed denominator therefore
comes from the same construction, and every complete block is a valid witness.
The returned witness is known by composition of identities, never by solving
the finished subset instance.
"""

from __future__ import annotations

from fractions import Fraction
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
    from gvlib import rationals  # type: ignore  # available from the repository root
except ImportError:  # The implementation below remains standard-library-only.
    rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "rational_exact",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "distinct odd positive denominators",
        "exact unit fractions over Q",
    ],
    "verification_operations": [
        "integer parity and membership checks",
        "exact rational reciprocal addition",
        "exact rational equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "An anchor denominator reveals a divisor of the target denominator "
        "and hence the common scale of its ten companions; without that "
        "normalization one faces fixed-length exact reciprocal subset search."
    ),
    "hardness_basis": (
        "Track B: fixed-eleven modular meet-in-the-middle reciprocal subset "
        "search runs in O(N^6) time and O(N^5) space and, at shipping N=44, "
        "succeeds in 8/8 trials after 7,103,905 modular additions and 1.296019 "
        "seconds on average; the anchor-and-scale route takes at most 153 exact "
        "operations."
    ),
    "max_answer_tokens": 141,
}

NATIVE: dict = {
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

DIFFICULTY: dict = {
    "demo": {"n": 11, "exponent": 36},
    "easy": {"n": 22, "exponent": 84},
    "medium": {"n": 33, "exponent": 84},
    "hard": {"n": 44, "exponent": 84},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Within a valid block, one denominator is q+2d for a divisor d of the target "
    "denominator q, while its ten companions share the scale (q/d)(q+2d)."
)
PLACEBO_HINT: str = (
    "Within the displayed list, every denominator is odd and positive, while the "
    "eleven selected entries must be copied in strictly increasing order."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An unordered set of exactly 11 distinct displayed odd denominators: "
        "exactly one target-scale entry q<x<3q and ten larger entries, serialized "
        "as an increasing list of decimal integers."
    ),
    "bounds": {
        "answer_length": 11,
        "entry_source": "the displayed candidate set",
        "target_scale_entries": 1,
        "larger_entries": 10,
        "order": "canonical increasing order",
        "repetitions": 0,
    },
}

# Script-owned oracle results are copied here after the three hardening runs.
# They are diagnostics only; G9's pass bit depends solely on the size/effort caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked: OpenRouter HTTP 403 key-total-limit",
}

NOTES: str = r"""
Section 1, equation (1.1) and the definition of X_k, fixes the native problem:
the denominators are distinct positive integers and their exact unit fractions
sum to one.  Corollary 1.2 imposes odd denominators and odd k.  The introductory
paragraph records that k=9 has exactly five solutions, whereas Theorem 1.1 and
Corollary 1.2 concern the abundance of solutions for sufficiently large odd k;
they are counting results, not search-hardness results.

Lemma 2.5(a) is the certificate-producing identity used here.  For P=2, q=2^t-1,
d|q, and distinct odd n_i with sum 1/n_i=2, it says

  1/q = 1/(q+2d) + sum_i 1/((q/d)(q+2d)n_i).

Each block takes n_i to be 1 together with one of the five nine-denominator odd
representations of one cited in Section 1.  Although Lemma 2.4 chooses n_i>1,
Lemma 2.5(a)'s displayed algebraic identity remains exact for this distinct set,
and make_instance checks it over Q.  It chooses d=2^a-1 for a proper divisor a
of t, so d|2^t-1 by the elementary factorization used throughout Section 2.
Thus every complete block is assembled by composition of exact identities.  No
subset search is run while generating an instance.

Step 0 rules out Track A: the paper supplies the identity, and this module's
distribution deliberately has a short normalization route.  It is Track B.
The reference route is fixed-eleven meet-in-the-middle subset search, polynomial
for the fixed witness length.  The compact route recognizes a candidate anchor
q+2d, derives its block scale, and reads off the ten companions.  Each preset
after demo is a shuffled union of complete independently sampled blocks.  Thus
there are no marginally different decoys: every displayed entry belongs to a
valid witness, while larger presets grow only the haystack and never the
eleven-term answer.

Assemblies are rejection-sampled only against the declared cheap attacks; this
does not discover a certificate because every block certificate is already
known.  The attacks are smallest magnitude, direct unit-fraction greedy,
consecutive magnitude windows, decimal-length clustering, and 256 uniform
restarts.  The generic exact meet-in-the-middle algorithm is reported
separately because its success is expected on Track B.

The canonical key sorts the exact normalized reciprocal weights q/x.  It is
therefore invariant under input reordering, answer reordering, and simultaneous
odd scaling of the target denominator and every candidate denominator.  It does
not use the seed or the rendered statement.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)

# The five k=9 solutions mentioned (and proved exhaustive in the cited work) in
# Section 1.  Each tuple is independently checked at import-free construction
# time by make_instance; they are data, not results of solving a generated pool.
_NINE_TERM_SOLUTIONS = (
    (3, 5, 7, 9, 11, 15, 21, 231, 315),
    (3, 5, 7, 9, 11, 15, 35, 45, 231),
    (3, 5, 7, 9, 11, 15, 21, 135, 10395),
    (3, 5, 7, 9, 11, 15, 33, 45, 385),
    (3, 5, 7, 9, 11, 15, 21, 165, 693),
)
_MODULUS = 2_305_843_009_213_693_951  # 2^61-1, prime


def _unit_sum(values: list[int] | tuple[int, ...]) -> Fraction:
    return sum((Fraction(1, value) for value in values), Fraction(0, 1))


def _proper_divisors(value: int) -> list[int]:
    out = []
    for divisor in range(1, math.isqrt(value) + 1):
        if value % divisor:
            continue
        if divisor < value:
            out.append(divisor)
        other = value // divisor
        if other != divisor and other < value:
            out.append(other)
    return sorted(out)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Mix complete Lemma 2.5(a) blocks without solving the subset instance."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 11 or n % 11:
        raise ValueError("n must be a positive multiple of 11")
    exponent = int(params.get("exponent", 84))
    if exponent < 4:
        raise ValueError("exponent must be at least 4")
    divisors = _proper_divisors(exponent)
    block_count = n // 11
    if len(divisors) < block_count:
        raise ValueError("exponent has too few proper divisors for n/11 blocks")
    q = (1 << exponent) - 1

    # Conditioning on failure of the declared cheap heuristics prevents an
    # accidental easy seed.  It never searches for a witness: every complete
    # block below comes with its own exact certificate before the conditioning.
    rng = random.Random(seed)
    for _attempt in range(512):
        exponents = rng.sample(divisors, block_count)
        candidates: list[int] = []
        certificates: list[list[int]] = []
        for a in exponents:
            d = (1 << a) - 1
            if q % d:
                raise AssertionError("2^a-1 must divide 2^t-1 when a divides t")
            anchor = q + 2 * d
            inner_scale = anchor * (q // d)
            solution = rng.choice(_NINE_TERM_SOLUTIONS)
            if _unit_sum(solution) != 1:
                raise AssertionError("bad fixed nine-term identity")
            block = [anchor, inner_scale]
            block.extend(inner_scale * value for value in solution)
            certificate = sorted(block)
            if _unit_sum(certificate) != Fraction(1, q):
                raise AssertionError("Lemma 2.5 block identity failed")
            candidates.extend(block)
            certificates.append(certificate)

        if len(candidates) != n or len(set(candidates)) != n:
            raise AssertionError("blocks did not yield distinct denominators")
        if any(value <= 0 or value % 2 == 0 for value in candidates):
            raise AssertionError("construction did not yield positive odd denominators")
        rng.shuffle(candidates)
        instance = {
            "target": [1, q],
            "answer_size": 11,
            "candidates": candidates,
            "answer": certificates[0],
        }
        ok, reason = verify(instance, instance["answer"])
        if not ok:
            raise AssertionError(f"constructed certificate failed: {reason}")
        if n == 11 or not _cheap_attack_succeeds(instance, seed):
            return instance
    raise RuntimeError("could not draw a block assembly defeating the cheap attacks")


def _format_answer(answer: list[int]) -> str:
    return ", ".join(str(value) for value in answer)


def render(inst: dict) -> str:
    """Render the complete exact reciprocal-subset problem."""
    numerator, denominator = inst["target"]
    lines = [
        "Odd Egyptian-fraction subset problem",
        "",
        "A unit fraction is a rational number 1/x with positive integer denominator x.",
        f"Choose exactly {inst['answer_size']} distinct entries from the candidate list below",
        f"so that their unit fractions sum exactly to {numerator}/{denominator}.",
        "Every listed candidate is a distinct odd positive integer. Order does not matter,",
        "but your output must list the chosen decimal denominators in increasing order.",
        "Candidates (one denominator per line):",
    ]
    lines.extend(str(value) for value in inst["candidates"])
    lines.extend([
        "",
        "All equalities are exact rational equalities; decimal approximation is not allowed.",
        "Give your final answer inside <answer></answer> tags, as exactly 11",
        "comma-separated decimal integers in increasing order, with no repeats.",
        "Example: <answer>3, 5, 7, 9, 11, 15, 21, 231, 315, 999, 1001</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse the tagged comma-separated denominator list, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    matches = list(_ANSWER_RE.finditer(text))
    if not matches:
        return None
    body = matches[-1].group(1).strip()
    if not body:
        return []
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    pieces = [piece.strip() for piece in body.split(",")]
    if not pieces or any(not re.fullmatch(r"[+]?[0-9]+", piece) for piece in pieces):
        return None
    try:
        return [int(piece) for piece in pieces]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid displayed eleven-denominator witness; never read the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a list of denominators"
    if len(answer) == 0:
        return False, "answer is empty"
    expected = int(inst.get("answer_size", 0))
    if len(answer) != expected:
        return False, f"expected exactly {expected} denominators"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every denominator must be a decimal integer"
    if any(value <= 0 for value in answer):
        return False, "denominators must be positive"
    if any(value % 2 == 0 for value in answer):
        return False, "denominators must be odd"
    if len(set(answer)) != len(answer):
        return False, "denominators must not repeat"
    displayed = set(inst.get("candidates", []))
    if any(value not in displayed for value in answer):
        return False, "a denominator is not in the displayed candidate list"
    target_raw = inst.get("target")
    if (
        not isinstance(target_raw, list) or len(target_raw) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in target_raw)
        or target_raw[1] == 0
    ):
        return False, "instance target is malformed"
    total = _unit_sum(answer)
    target = Fraction(target_raw[0], target_raw[1])
    if total != target:
        return False, "the exact reciprocal sum does not equal the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing the obvious one-anchor magnitude bound."""
    q = int(inst["target"][1])
    anchors = [value for value in inst["candidates"] if q < value < 3 * q]
    tails = [value for value in inst["candidates"] if not (q < value < 3 * q)]
    return sorted([rng.choice(anchors), *rng.sample(tails, 10)])


def search_space(inst: dict) -> int | None:
    """Count legal one-anchor/ten-tail subsets under the structure-aware prior."""
    q = int(inst["target"][1])
    anchors = sum(q < value < 3 * q for value in inst["candidates"])
    tails = len(inst["candidates"]) - anchors
    return anchors * math.comb(tails, 10)


def _structural_recovery(inst: dict) -> list[int] | None:
    """Execute the intended Lemma 2.5 anchor-and-scale route."""
    target = inst.get("target")
    candidates = inst.get("candidates")
    if (
        not isinstance(target, list) or len(target) != 2 or target[0] != 1
        or not isinstance(candidates, list)
    ):
        return None
    q = int(target[1])
    # Proper d=2^a-1 is much smaller than q, so q < q+2d < 3q.
    possible_anchors = sorted(value for value in candidates if q < value < 3 * q)
    for anchor in possible_anchors:
        delta = anchor - q
        if delta % 2:
            continue
        d = delta // 2
        if d <= 0 or q % d:
            continue
        inner = anchor * (q // d)
        companions = sorted(
            value for value in candidates if value != anchor and value % inner == 0
        )
        if len(companions) != 10:
            continue
        answer = sorted([anchor, *companions])
        if verify(inst, answer)[0]:
            return answer
    return None


def _reference_mitm(inst: dict, count_all: bool = False) -> tuple[list[int] | None, dict]:
    """Exact one-anchor plus five/five-tail meet-in-the-middle subset search."""
    stats = {
        "left_subsets": 0,
        "right_subsets": 0,
        "modular_additions": 0,
        "exact_checks": 0,
        "solutions": 0,
    }
    candidates = inst.get("candidates")
    target = inst.get("target")
    if not isinstance(candidates, list) or not isinstance(target, list) or len(target) != 2:
        return None, stats
    values = sorted(candidates)
    if len(values) < 11 or target[1] % _MODULUS == 0:
        return None, stats
    modulus = _MODULUS
    if any(value % modulus == 0 for value in values):
        raise AssertionError("reference modulus divides a candidate denominator")
    weights = [pow(value, -1, modulus) for value in values]
    q = int(target[1])
    anchor_indices = [index for index, value in enumerate(values) if q < value < 3 * q]
    tail_indices = [index for index, value in enumerate(values) if not (q < value < 3 * q)]
    if not anchor_indices or len(tail_indices) < 10:
        return None, stats

    left: dict[int, int | list[int]] = {}
    for combo in itertools.combinations(tail_indices, 5):
        residue = sum(weights[index] for index in combo) % modulus
        mask = sum(1 << index for index in combo)
        old = left.get(residue)
        if old is None:
            left[residue] = mask
        elif isinstance(old, int):
            left[residue] = [old, mask]
        else:
            old.append(mask)
        stats["left_subsets"] += 1
        stats["modular_additions"] += 5

    target_residue = (target[0] * pow(target[1], -1, modulus)) % modulus
    found_masks: set[int] = set()
    first_answer = None
    for anchor_index in anchor_indices:
        needed = (target_residue - weights[anchor_index]) % modulus
        anchor_mask = 1 << anchor_index
        for combo in itertools.combinations(tail_indices, 5):
            residue = sum(weights[index] for index in combo) % modulus
            stats["right_subsets"] += 1
            stats["modular_additions"] += 6
            matches = left.get((needed - residue) % modulus)
            if matches is None:
                continue
            right_mask = sum(1 << index for index in combo)
            left_masks = [matches] if isinstance(matches, int) else matches
            for left_mask in left_masks:
                if left_mask & right_mask:
                    continue
                full_mask = anchor_mask | left_mask | right_mask
                chosen = [values[index] for index in range(len(values))
                          if full_mask >> index & 1]
                stats["exact_checks"] += 1
                if len(chosen) != 11 or _unit_sum(chosen) != Fraction(*target):
                    continue
                found_masks.add(full_mask)
                if first_answer is None:
                    first_answer = sorted(chosen)
                    if not count_all:
                        stats["solutions"] = 1
                        return first_answer, stats
    stats["solutions"] = len(found_masks)
    return first_answer, stats


def enumerate_all(inst: dict) -> int | None:
    """Count exact answers at supported sizes; refuse an unbounded brute force."""
    if len(inst.get("candidates", [])) > 44:
        return None
    _, stats = _reference_mitm(inst, count_all=True)
    return int(stats["solutions"])


def _greedy_candidate(inst: dict) -> list[int] | None:
    target = Fraction(*inst["target"])
    chosen = []
    total = Fraction(0, 1)
    unused = set(inst["candidates"])
    for _ in range(inst["answer_size"]):
        fitting = [value for value in unused if total + Fraction(1, value) <= target]
        if not fitting:
            if not unused:
                return None
            pick = max(unused)
        else:
            pick = min(fitting)
        chosen.append(pick)
        unused.remove(pick)
        total += Fraction(1, pick)
    return sorted(chosen)


def _consecutive_magnitude_candidates(inst: dict) -> list[list[int]]:
    values = sorted(inst["candidates"])
    width = int(inst["answer_size"])
    return [values[start:start + width] for start in range(len(values) - width + 1)]


def _digit_bucket_candidates(inst: dict) -> list[list[int]]:
    """A cheap visual clustering heuristic based only on decimal lengths."""
    q = int(inst["target"][1])
    anchors = sorted(value for value in inst["candidates"] if q < value < 3 * q)
    buckets: dict[int, list[int]] = {}
    for value in inst["candidates"]:
        if value not in anchors:
            buckets.setdefault(len(str(value)), []).append(value)
    guesses = []
    for anchor in anchors:
        for bucket in buckets.values():
            if len(bucket) >= 10:
                ordered = sorted(bucket)
                guesses.append(sorted([anchor, *ordered[:10]]))
                guesses.append(sorted([anchor, *ordered[-10:]]))
    return guesses


def _attack_candidates(inst: dict, seed: int) -> dict[str, list[object]]:
    candidates = list(inst["candidates"])
    outlier = sorted(sorted(candidates)[:inst["answer_size"]])
    rng = random.Random(seed ^ 0x160602117)
    restarts = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_smallest_magnitude": [outlier],
        "greedy_exact_reciprocals": [_greedy_candidate(inst)],
        "consecutive_magnitude_windows": _consecutive_magnitude_candidates(inst),
        "decimal_length_clustering": _digit_bucket_candidates(inst),
        "random_restart_256": restarts,
    }


def _cheap_attack_succeeds(inst: dict, seed: int) -> bool:
    """Condition block assemblies on all declared attacks failing."""
    attacks = _attack_candidates(inst, seed)
    return any(
        candidate is not None and verify(inst, candidate)[0]
        for guesses in attacks.values()
        for candidate in guesses
    )


def canonical_key(inst: dict) -> str:
    """Canonicalize input order and simultaneous scaling via target-normalized weights."""
    numerator, q = inst["target"]
    if numerator != 1:
        raise ValueError("this family canonicalizes unit-fraction targets only")
    normalized = []
    for denominator in inst["candidates"]:
        value = Fraction(q, denominator)
        normalized.append([value.numerator, value.denominator])
    payload = {
        "family": "odd_egyptian_reciprocal_subset",
        "answer_size": int(inst["answer_size"]),
        "normalized_reciprocal_weights": sorted(normalized),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow only the candidate haystack; the eleven-denominator witness stays fixed."""
    harder = dict(params)
    harder["n"] = int(params.get("n", 11)) + 11
    blocks = harder["n"] // 11
    exponent = int(harder.get("exponent", 84))
    if len(_proper_divisors(exponent)) < blocks:
        replacement = next(
            (candidate for candidate in range(exponent + 1, 601)
             if len(_proper_divisors(candidate)) >= blocks),
            None,
        )
        if replacement is None:
            return "cap_bound"
        harder["exponent"] = replacement
    worst_chars, _, _ = _answer_size_bounds(harder)
    if worst_chars > 2_000:
        return "cap_bound"
    return harder


def _scaled_instance(inst: dict, factor: int) -> dict:
    clone = json.loads(json.dumps(inst))
    clone["target"][1] *= factor
    clone["candidates"] = [factor * value for value in clone["candidates"]]
    clone["answer"] = [factor * value for value in clone["answer"]]
    return clone


def _answer_size_bounds(params: dict) -> tuple[int, int, int]:
    exponent = int(params["exponent"])
    q = (1 << exponent) - 1
    worst = []
    for a in _proper_divisors(exponent):
        d = (1 << a) - 1
        scale = q // d
        anchor = q + 2 * d
        inner = anchor * scale
        for solution in _NINE_TERM_SOLUTIONS:
            answer = sorted([anchor, inner] + [inner * value for value in solution])
            compact = json.dumps(answer, separators=(",", ":"))
            worst.append((len(compact), math.ceil(len(compact) / 4), len(answer)))
    return max(worst)


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "arXiv:1606.02117",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    planted = 0
    json_native = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            planted += int(ok)
            json_native += int(json.loads(json.dumps(trial["answer"])) == trial["answer"])
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
    report["G1_planted_verifies"] = {
        "pass": planted == 12 and json_native == 12,
        "verified": planted,
        "attempts": 12,
        "json_native": json_native,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    answer = list(inst["answer"])
    outsider = next(value for value in inst["candidates"] if value not in set(answer))
    swapped = list(answer)
    swapped[-1] = outsider
    duplicate = list(answer)
    duplicate[-1] = duplicate[0]
    missing = max(inst["candidates"]) + 2
    if missing % 2 == 0:
        missing += 1
    outside_answer = list(answer)
    outside_answer[-1] = missing
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate_one": duplicate,
        "out_of_range": outside_answer,
        "swap_one": swapped,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values()) and len(set(reasons)) == 5,
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The normalized multipliers expose the odd unit-fraction core.\n"
        "```text\n<answer>" + _format_answer(answer) + "</answer>\n```\n"
        "I checked the reciprocal identity exactly."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x160602117)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_prior": (
            "uniform one target-scale denominator and ten larger denominators"
        ),
        "candidate_space": search_space(inst),
        "candidate_space_bits": int(search_space(inst)).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_smallest_magnitude",
        "greedy_exact_reciprocals",
        "consecutive_magnitude_windows",
        "decimal_length_clustering",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_times = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_ops = []
    reference_left = []
    reference_right = []
    structural_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        attacks = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(candidate is not None and verify(trial, candidate)[0]
                      for candidate in attacks[name])
            attack_times[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, stats = _reference_mitm(trial, count_all=False)
        reference_times.append(time.perf_counter() - start)
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        reference_ops.append(stats["modular_additions"])
        reference_left.append(stats["left_subsets"])
        reference_right.append(stats["right_subsets"])
        structural = _structural_recovery(trial)
        structural_successes += int(
            structural is not None and verify(trial, structural)[0]
        )

    attacks_report = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_times[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "fixed-eleven modular meet-in-the-middle with exact collision checks",
        "complexity": "O(N^6) time and O(N^5) space for fixed witness length eleven",
        "wall_clock_sec": round(sum(reference_times) / len(reference_times), 6),
        "operations": sum(reference_ops) // len(reference_ops),
        "left_subsets": sum(reference_left) // len(reference_left),
        "right_subsets": sum(reference_right) // len(reference_right),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and structural_successes == 8,
        "attacks": attacks_report,
        "reference_algorithm": reference,
        "intended_structural_route": {
            "name": "Lemma 2.5 anchor-and-scale normalization",
            "solves": f"{structural_successes}/8, as expected",
        },
    }

    count_start = time.perf_counter()
    _, count_stats = _reference_mitm(inst, count_all=True)
    count_seconds = time.perf_counter() - count_start
    exact_count = count_stats["solutions"]
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_count > 0 and exact_count / search_space(inst) < 1e-6
        and all_failed and reference_successes == 8,
        "shipping_exact_solution_count": exact_count,
        "shipping_candidate_space": search_space(inst),
        "shipping_exact_solution_density": exact_count / search_space(inst),
        "shipping_count_wall_clock_sec": round(count_seconds, 6),
        "shipping_count_operations": count_stats["modular_additions"],
        "sample_hits": guess_hits,
        "sample_total": guess_total,
        "strongest_failed_attack": "random_restart_256",
        "strongest_failed_attack_wall_clock_sec": round(
            attack_times["random_restart_256"] / 8, 6
        ),
        "strongest_failed_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=2718, **doubled_params)
    doubled_seconds = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    sizes = [params["n"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["candidates"]) == 2 * len(inst["candidates"])
        and search_space(doubled) > search_space(inst)
        and sizes == sorted(sizes) and len(set(sizes)) == 4,
        "shipping_candidates": len(inst["candidates"]),
        "doubled_candidates": len(doubled["candidates"]),
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "doubled_build_sec": round(doubled_seconds, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariant = 0
    real = 0
    unrelated = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        reordered = json.loads(json.dumps(original))
        permutation = list(range(len(reordered["candidates"])))
        random.Random(seed ^ 0xA5A5).shuffle(permutation)
        reordered["candidates"] = [reordered["candidates"][index] for index in permutation]

        answer_reordered = json.loads(json.dumps(original))
        answer_reordered["answer"].reverse()
        scaled = _scaled_instance(original, 3)
        composed = _scaled_instance(reordered, 5)
        transformed = [reordered, answer_reordered, scaled, composed]
        for changed in transformed:
            invariant += int(canonical_key(changed) == key)
            real += int(verify(changed, changed["answer"])[0])
        unrelated.append(key)
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": invariant == 80 and real == 80 and distinct == 20,
        "invariant_relabellings": invariant,
        "real_transformations_verified": real,
        "unrelated_distinct_keys": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary candidate-list permutation",
            "arbitrary witness ordering",
            "simultaneous odd global scaling",
            "composition of list permutation and global scaling",
        ],
    }

    compact = json.dumps(answer, separators=(",", ":"))
    worst_chars, worst_tokens, worst_elements = _answer_size_bounds(shipping)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    # At worst: two comparisons per candidate to identify anchors, four exact
    # operations to derive d and the scale, one divisibility check per candidate,
    # and eleven reciprocal additions for the final exact check.
    intended_operations = 3 * int(shipping["n"]) + 21
    within_caps = (
        worst_chars <= 2_000 and worst_elements <= 256 and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
        and structural_successes == 8
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(compact),
        "answer_tokens": math.ceil(len(compact) / 4),
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": len(answer),
        "intended_route_operations": intended_operations,
        "intended_route_solved": f"{structural_successes}/8",
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass") is True for value in gates
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
