"""Verified Track-B generator from Equation (2) of arXiv:2408.09272.

Every L-ribbon contributes one square on each of L consecutive levels.  Thus
the square-level enumerator S and root-level enumerator Q satisfy
S=(1+x+...+x^(L-1))Q.  Instances sample sparse Q first and compose this identity.
The checker compares sparse boundary events and never reads the planted answer.
"""

from __future__ import annotations

import hashlib
import functools
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "square-level enumerator of a finite lattice region",
        "root-level enumerator of an L-ribbon tiling",
        "formal Laurent polynomials over the integers",
    ],
    "verification_operations": [
        "exact integer finite differences",
        "exact sparse polynomial multiplication",
        "coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Taking a first difference turns every length-L block of square levels "
        "into two endpoints; without it, root counts are recovered one level "
        "at a time across millions of zero or repeated coefficients."
    ),
    "hardness_basis": (
        "Track B: the Equation (2) dense recurrence is O(D) in the level span "
        "and performs at least 21 million exact arithmetic operations at the hard "
        "preset (1.38 seconds on the recorded seed); the sparse finite-difference "
        "route uses 160 exact additions there (at most 240 by construction)."
    ),
    "max_answer_tokens": 219,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 5, "terms": 3, "chains": 1, "coeff_bound": 3},
    "easy": {"n": 80_003, "terms": 32, "chains": 8, "coeff_bound": 9},
    "medium": {"n": 400_009, "terms": 40, "chains": 10, "coeff_bound": 9},
    "hard": {"n": 1_500_007, "terms": 48, "chains": 12, "coeff_bound": 9},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = "The first difference of the square-level enumerator records only where ribbon-root contributions begin or end."
PLACEBO_HINT = "Careful bookkeeping of coefficient positions and signs helps prevent indexing errors in this calculation."

CERTIFICATE_LANGUAGE = {
    "description": (
        "A canonical sparse Laurent polynomial with exactly the stated number "
        "of terms.  The two outer exponents and their coefficients are fixed by "
        "the outer level runs; the coefficient sum is fixed by S(1)=L*Q(1).  "
        "Remaining coefficients are positive rationals c/1 with "
        "1<=c<=coeff_bound, and distinct internal integer exponents are sorted."
    ),
    "bounds": {
        "max_terms_at_named_presets": 48,
        "coefficient_denominator": 1,
        "max_coefficient_at_named_presets": 9,
        "exponents": "instance-specific inclusive root range",
    },
}

NOTES = """Definition 1 gives one square on each of L consecutive levels.
Section 2, Equation (2) states sigma_l=sum_{j=l-L+1}^l tau_j and proves that
tau_l is independent of the tiling.  We sample Q=sum tau_l*x^l first and build
S=(1+x+...+x^(L-1))Q by endpoint events; a disjoint union of translated
all-east ribbons realizes every sampled histogram.  Section 1 rules out Track
A: it cites Sheffield's linear-area algorithm for simply connected regions,
while complexity for general ribbon regions is open.  Track B reports both the
dense O(D) Equation (2) recurrence and its compact sparse alternative
(1-x)S=(1-x^L)Q.  Positive-boundary, run-start, largest-jump,
endpoint-pairing and random-polynomial attacks are measured after enforcing
the forced endpoints and coefficient sum.  Roots are interleaved across
random residue chains whose coefficients contain both rises and falls, and the
input runs are shuffled, so starts, signs, magnitude and input order do not
identify the answer."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _add_event(events, exponent, delta):
    if delta:
        events[exponent] = events.get(exponent, 0) + delta
        if events[exponent] == 0:
            del events[exponent]


def _answer_from_terms(terms):
    return [[[coefficient, 1], [exponent]] for exponent, coefficient in sorted(terms)]


def _runs_from_terms(ribbon_length, terms):
    events = {}
    for exponent, coefficient in terms:
        _add_event(events, exponent, coefficient)
        _add_event(events, exponent + ribbon_length, -coefficient)
    current = 0
    previous = None
    runs = []
    for position in sorted(events):
        if previous is not None and current and previous <= position - 1:
            runs.append([previous, position - 1, current])
        current += events[position]
        previous = position
    if current:
        raise AssertionError("unbalanced construction events")
    return runs


def _normalise_runs(raw_runs):
    if not isinstance(raw_runs, list) or not raw_runs:
        return None, "level runs must be a nonempty list"
    runs = []
    for run in raw_runs:
        if not (isinstance(run, list) and len(run) == 3 and all(_is_int(v) for v in run)):
            return None, "each level run must be [first,last,count] with integers"
        lo, hi, value = run
        if lo > hi:
            return None, "a level run has reversed endpoints"
        if value <= 0:
            return None, "level counts must be positive"
        runs.append([lo, hi, value])
    runs.sort()
    for previous, current in zip(runs, runs[1:]):
        if current[0] <= previous[1]:
            return None, "level runs overlap"
        if current[0] == previous[1] + 1 and current[2] == previous[2]:
            return None, "adjacent equal runs are not canonical"
    return runs, None


def _events_from_runs(runs):
    events = {}
    for lo, hi, value in runs:
        _add_event(events, lo, value)
        _add_event(events, hi + 1, -value)
    return events


@functools.lru_cache(maxsize=256)
def _cached_run_events(raw_runs):
    runs, error = _normalise_runs([list(run) for run in raw_runs])
    if error:
        raise ValueError(error)
    return _events_from_runs(runs)


def _sample_chain_coefficients(rng, length, bound):
    while True:
        values = [rng.randint(1, bound) for _ in range(length)]
        rises = any(a < b for a, b in zip(values, values[1:]))
        falls = any(a > b for a, b in zip(values, values[1:]))
        if length == 2 and values[0] != values[1]:
            return values
        if length >= 3 and rises and falls:
            return values


def make_instance(n, seed=0, **params):
    """Sample sparse Q first, then compose the paper's level-count identity."""
    ribbon_length = int(n)
    term_count = int(params.get("terms", 32))
    chain_count = int(params.get("chains", 8))
    coefficient_bound = int(params.get("coeff_bound", 9))
    if ribbon_length < 2:
        raise ValueError("n (the ribbon length) must be at least 2")
    if term_count < 3 or chain_count < 1 or term_count < 3 * chain_count:
        raise ValueError("terms must be at least three times chains")
    if chain_count > ribbon_length:
        raise ValueError("chains cannot exceed the ribbon length")
    if coefficient_bound < 3:
        raise ValueError("coeff_bound must be at least 3")

    rng = random.Random(seed)
    lengths = [term_count // chain_count] * chain_count
    for index in range(term_count % chain_count):
        lengths[index] += 1
    bases = rng.sample(range(ribbon_length), chain_count)
    translation = rng.randint(-2 * ribbon_length, 2 * ribbon_length)
    terms = []
    for base, length in zip(bases, lengths):
        coefficients = _sample_chain_coefficients(rng, length, coefficient_bound)
        for step, coefficient in enumerate(coefficients):
            terms.append((translation + base + step * ribbon_length, coefficient))
    terms.sort()
    runs = _runs_from_terms(ribbon_length, terms)
    rng.shuffle(runs)
    root_min = min(exponent for exponent, _ in terms)
    root_max = max(exponent for exponent, _ in terms)
    return {
        "ribbon_length": ribbon_length,
        "term_count": term_count,
        "chain_count": chain_count,
        "coefficient_bound": coefficient_bound,
        "root_exponent_range": [root_min, root_max],
        "level_runs": runs,
        "answer": _answer_from_terms(terms),
    }


def render(inst):
    lines = [
        "ROOT-LEVEL ENUMERATOR OF AN L-RIBBON TILING", "",
        "A lattice square [x,y] has integer level l=x+y. An L-ribbon is a connected",
        "north/east path of exactly L squares, so a ribbon rooted at level j contains",
        "one square at each level j,j+1,...,j+L-1.", "",
        "Let sigma_l be the number of region squares at level l and tau_j the number",
        "of ribbons rooted at level j. The promised tiling therefore satisfies",
        "sigma_l = sum(tau_j for j=l-L+1,...,l). Equivalently, for formal Laurent",
        "polynomials S(x)=sum sigma_l*x^l and Q(x)=sum tau_j*x^j,",
        "S(x)=(1+x+...+x^(L-1))*Q(x). Negative exponents are allowed.", "",
        "The nonzero coefficients of S are run-length encoded below. A record",
        "[a,b,c] means sigma_l=c for every integer a<=l<=b, inclusively. At every",
        "unlisted level sigma_l=0. Records are disjoint; their displayed order has",
        "no significance.", "",
        f"Ribbon length L: {inst['ribbon_length']}",
        f"Required number of nonzero terms in Q: {inst['term_count']}",
        f"Coefficient bound: 1 <= tau_j <= {inst['coefficient_bound']}",
        "Inclusive root-exponent range: " + json.dumps(inst["root_exponent_range"], separators=(",", ":")),
        "Level runs [first,last,count]:",
        json.dumps(inst["level_runs"], separators=(",", ":")), "",
        "Find Q. The answer must contain exactly the required number of terms, sorted",
        "by strictly increasing exponent. Encode each term c*x^e as [[c,1],[e]]:",
        "[c,1] is the exact rational coefficient c/1 and [e] is its one-variable",
        "exponent list. All coefficients are positive, so zero terms are omitted.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    lines += ["", "Give your final answer inside <answer></answer> tags as one JSON array.",
              "Example: <answer>[[[2,1],[-3]],[[1,1],[5]]]</answer>",
              "Output nothing else inside the tags."]
    return "\n".join(lines)


_ANSWER_TAG = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.I | re.S)
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.I | re.S)
_FENCE_ANYWHERE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.I | re.S)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_TAG.search(text)
    if tagged:
        body = tagged.group(1)
    else:
        fenced = _FENCE_ANYWHERE.search(text)
        if fenced:
            body = fenced.group(1)
        else:
            first, last = text.find("["), text.rfind("]")
            body = text[first:last + 1] if 0 <= first < last else text.strip()
    inner = _FENCE.match(body)
    if inner:
        body = inner.group(1)
    try:
        value = json.loads(body.strip())
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    for term in value:
        if not (isinstance(term, list) and len(term) == 2
                and isinstance(term[0], list) and len(term[0]) == 2
                and isinstance(term[1], list) and len(term[1]) == 1
                and all(_is_int(v) for v in term[0] + term[1])):
            return None
    return value


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected_terms = int(inst.get("term_count", -1))
    if len(answer) != expected_terms:
        return False, f"wrong term count: expected {expected_terms} nonzero terms"
    parsed = []
    for term in answer:
        if not (isinstance(term, list) and len(term) == 2
                and isinstance(term[0], list) and len(term[0]) == 2
                and isinstance(term[1], list) and len(term[1]) == 1
                and all(_is_int(v) for v in term[0] + term[1])):
            return False, "each term must have exact form [[integer,integer],[integer]]"
        numerator, denominator = term[0]
        exponent = term[1][0]
        if denominator != 1:
            return False, "every coefficient denominator must equal 1"
        if not 1 <= numerator <= int(inst["coefficient_bound"]):
            return False, "coefficient is outside the stated positive bound"
        parsed.append((exponent, numerator))
    exponents = [exponent for exponent, _ in parsed]
    if len(set(exponents)) != len(exponents):
        return False, "duplicate exponent"
    if exponents != sorted(exponents):
        return False, "terms are not sorted by increasing exponent"
    root_range = inst.get("root_exponent_range")
    if not (isinstance(root_range, list) and len(root_range) == 2 and all(_is_int(v) for v in root_range)):
        return False, "instance root range is malformed"
    if any(exponent < root_range[0] or exponent > root_range[1] for exponent in exponents):
        return False, "exponent is outside the inclusive root range"
    try:
        wanted = _cached_run_events(tuple(tuple(run) for run in inst.get("level_runs", [])))
    except (TypeError, ValueError) as error:
        return False, "instance level data are inconsistent: " + str(error)
    ribbon_length = inst.get("ribbon_length")
    if not _is_int(ribbon_length) or ribbon_length < 2:
        return False, "instance ribbon length is malformed"
    obtained = {}
    for exponent, coefficient in parsed:
        _add_event(obtained, exponent, coefficient)
        _add_event(obtained, exponent + ribbon_length, -coefficient)
    if obtained != wanted:
        return False, "polynomial identity does not match the level counts"
    return True, "ok"


@functools.lru_cache(maxsize=256)
def _candidate_constraints_cached(raw_runs, root_range, ribbon_length, term_count, coefficient_bound):
    runs, error = _normalise_runs([list(run) for run in raw_runs])
    if error:
        raise ValueError(error)
    lo, hi = root_range
    coefficient_sum, remainder = divmod(
        sum((last - first + 1) * value for first, last, value in runs),
        ribbon_length,
    )
    if remainder:
        raise ValueError("level-count sum is not divisible by the ribbon length")
    return (lo, hi, term_count, coefficient_bound,
            coefficient_sum, runs[0][2], runs[-1][2])


def _candidate_constraints(inst):
    return _candidate_constraints_cached(
        tuple(tuple(run) for run in inst["level_runs"]),
        tuple(inst["root_exponent_range"]),
        int(inst["ribbon_length"]),
        int(inst["term_count"]),
        int(inst["coefficient_bound"]),
    )


@functools.lru_cache(maxsize=128)
def _bounded_composition_table(length, total, bound):
    """Counts of ordered positive bounded compositions, cached for G4 sampling."""
    rows = [[1] + [0] * total]
    for used in range(1, length + 1):
        previous = rows[-1]
        current = [0] * (total + 1)
        for subtotal in range(total + 1):
            current[subtotal] = sum(
                previous[subtotal - value]
                for value in range(1, min(bound, subtotal) + 1)
            )
        rows.append(current)
    return tuple(tuple(row) for row in rows)


def _bounded_composition_count(length, total, bound):
    if length < 0 or total < 0:
        return 0
    return _bounded_composition_table(length, total, bound)[length][total]


def _sample_bounded_composition(rng, length, total, bound):
    table = _bounded_composition_table(length, total, bound)
    if table[length][total] <= 0:
        raise ValueError("bounded coefficient language is empty")
    answer = []
    # One uniformly sampled rank identifies one uniformly sampled composition;
    # carrying that rank down the DP table avoids dozens of large-integer RNG
    # calls per G4 candidate.
    ticket = rng.randrange(table[length][total])
    for remaining in range(length, 0, -1):
        for value in range(1, bound + 1):
            if not 0 <= total - value < len(table[remaining - 1]):
                continue
            completions = table[remaining - 1][total - value]
            if ticket < completions:
                answer.append(value)
                total -= value
                break
            ticket -= completions
        else:
            raise AssertionError("composition sampler lost its count")
    if total:
        raise AssertionError("composition sampler left a nonzero remainder")
    return answer


def random_candidate(inst, rng):
    lo, hi, k, bound, total, left_coefficient, right_coefficient = _candidate_constraints(inst)
    internal_support = sorted(rng.sample(range(lo + 1, hi), k - 2))
    internal_coefficients = _sample_bounded_composition(
        rng, k - 2, total - left_coefficient - right_coefficient, bound)
    terms = [(lo, left_coefficient)]
    terms.extend(zip(internal_support, internal_coefficients))
    terms.append((hi, right_coefficient))
    return _answer_from_terms(terms)


def search_space(inst):
    lo, hi, k, bound, total, left_coefficient, right_coefficient = _candidate_constraints(inst)
    positions = hi - lo + 1
    if positions < k:
        return 0
    coefficient_count = _bounded_composition_count(
        k - 2, total - left_coefficient - right_coefficient, bound)
    return math.comb(positions - 2, k - 2) * coefficient_count


def enumerate_all(inst):
    if search_space(inst) > 200_000:
        return None
    lo, hi, k, bound, total, left_coefficient, right_coefficient = _candidate_constraints(inst)
    remaining = total - left_coefficient - right_coefficient
    hits = 0
    for support in itertools.combinations(range(lo + 1, hi), k - 2):
        for coefficients in itertools.product(range(1, bound + 1), repeat=k - 2):
            if sum(coefficients) != remaining:
                continue
            terms = [(lo, left_coefficient), *zip(support, coefficients), (hi, right_coefficient)]
            hits += int(verify(inst, _answer_from_terms(terms))[0])
    return hits


def _sparse_recover(inst):
    runs, error = _normalise_runs(inst["level_runs"])
    if error:
        return None, 0
    residual = _events_from_runs(runs)
    ribbon_length = int(inst["ribbon_length"])
    terms = []
    arithmetic_operations = 2 * len(runs)
    guard = 4 * int(inst["term_count"]) + 4 * len(runs) + 10
    while residual and len(terms) <= guard:
        exponent = min(residual)
        coefficient = residual.pop(exponent)
        if coefficient <= 0:
            return None, arithmetic_operations
        terms.append((exponent, coefficient))
        _add_event(residual, exponent + ribbon_length, coefficient)
        arithmetic_operations += 1
    if residual:
        return None, arithmetic_operations
    return _answer_from_terms(terms), arithmetic_operations


def _dense_recover(inst):
    runs, error = _normalise_runs(inst["level_runs"])
    if error:
        return None, 0
    ribbon_length = int(inst["ribbon_length"])
    first_level, last_level = runs[0][0], runs[-1][1]
    ring = [0] * ribbon_length
    pointer = 0
    previous_sigma = 0
    terms = []
    iterations = 0
    for level in range(first_level, last_level + 1):
        while pointer < len(runs) and level > runs[pointer][1]:
            pointer += 1
        sigma = runs[pointer][2] if pointer < len(runs) and runs[pointer][0] <= level <= runs[pointer][1] else 0
        slot = (level - first_level) % ribbon_length
        tau = sigma - previous_sigma + ring[slot]
        ring[slot] = tau
        if tau:
            terms.append((level, tau))
        previous_sigma = sigma
        iterations += 1
    return _answer_from_terms(terms), iterations * 3


def _canonical_payload(inst, reflected=False):
    runs, error = _normalise_runs(inst["level_runs"])
    if error:
        raise ValueError(error)
    if reflected:
        runs = sorted([[-hi, -lo, value] for lo, hi, value in runs])
    shift = runs[0][0]
    normal = [[lo - shift, hi - shift, value] for lo, hi, value in runs]
    return [int(inst["ribbon_length"]), int(inst["term_count"]), int(inst["coefficient_bound"]), normal]


def canonical_key(inst):
    forms = [json.dumps(_canonical_payload(inst, flag), separators=(",", ":")) for flag in (False, True)]
    return hashlib.sha256(min(forms).encode("utf-8")).hexdigest()


def escalate(params):
    harder = dict(params)
    harder["n"] = int(harder["n"]) * 4 + 1
    harder["terms"] = int(harder.get("terms", 48))
    harder["chains"] = min(harder["terms"] // 3,
                            int(harder.get("chains", 12)) + 1)
    harder["coeff_bound"] = int(harder.get("coeff_bound", 9)) * 2 + 1
    # Atom count stays fixed, but decimal numerals can eventually hit the
    # character cap.  This conservative upper bound stops only at that limit.
    per_term_chars = (12 + len(str(harder["coeff_bound"]))
                       + len(str(-8 * harder["n"])))
    if harder["terms"] * per_term_chars + 1 > 2000:
        return "cap_bound"
    return harder


def _translated(inst, amount):
    out = {"ribbon_length": inst["ribbon_length"], "term_count": inst["term_count"],
           "chain_count": inst["chain_count"], "coefficient_bound": inst["coefficient_bound"],
           "root_exponent_range": [v + amount for v in inst["root_exponent_range"]],
           "level_runs": [[lo + amount, hi + amount, c] for lo, hi, c in inst["level_runs"]]}
    if "answer" in inst:
        out["answer"] = [[[t[0][0], t[0][1]], [t[1][0] + amount]] for t in inst["answer"]]
    return out


def _reflected(inst):
    length = int(inst["ribbon_length"])
    lo, hi = inst["root_exponent_range"]
    out = {"ribbon_length": length, "term_count": inst["term_count"],
           "chain_count": inst["chain_count"], "coefficient_bound": inst["coefficient_bound"],
           "root_exponent_range": [-hi - length + 1, -lo - length + 1],
           "level_runs": [[-b, -a, c] for a, b, c in inst["level_runs"]]}
    if "answer" in inst:
        out["answer"] = _answer_from_terms([(-t[1][0] - length + 1, t[0][0]) for t in inst["answer"]])
    return out


def _reordered(inst, rng):
    out = {"ribbon_length": inst["ribbon_length"], "term_count": inst["term_count"],
           "chain_count": inst["chain_count"], "coefficient_bound": inst["coefficient_bound"],
           "root_exponent_range": list(inst["root_exponent_range"]),
           "level_runs": [list(run) for run in inst["level_runs"]]}
    rng.shuffle(out["level_runs"])
    if "answer" in inst:
        out["answer"] = json.loads(json.dumps(inst["answer"]))
    return out


def _attack_candidate(inst, raw_terms):
    lo, hi, k, bound, total, left_coefficient, right_coefficient = _candidate_constraints(inst)
    chosen = {}
    for exponent, coefficient in raw_terms:
        if lo < exponent < hi and exponent not in chosen:
            chosen[exponent] = max(1, min(bound, abs(int(coefficient)) or 1))
        if len(chosen) == k - 2:
            break
    cursor = lo + 1
    while len(chosen) < k - 2:
        if cursor not in chosen:
            chosen[cursor] = 1
        cursor += 1

    # Give every attack all constraints stated in the output language.  Repair
    # its guessed internal coefficients to the forced total without changing
    # its chosen support or favoring the planted answer.
    ordered = sorted(chosen.items())
    target = total - left_coefficient - right_coefficient
    delta = target - sum(coefficient for _exponent, coefficient in ordered)
    while delta > 0:
        moved = 0
        for index, (exponent, coefficient) in enumerate(ordered):
            step = min(bound - coefficient, delta)
            ordered[index] = (exponent, coefficient + step)
            delta -= step
            moved += step
            if delta == 0:
                break
        if moved == 0:
            raise AssertionError("cannot repair attack coefficient sum upward")
    while delta < 0:
        moved = 0
        for index, (exponent, coefficient) in enumerate(ordered):
            step = min(coefficient - 1, -delta)
            ordered[index] = (exponent, coefficient - step)
            delta += step
            moved += step
            if delta == 0:
                break
        if moved == 0:
            raise AssertionError("cannot repair attack coefficient sum downward")
    return _answer_from_terms([(lo, left_coefficient), *ordered, (hi, right_coefficient)])


def _attack_candidates(inst):
    runs, _ = _normalise_runs(inst["level_runs"])
    events = _events_from_runs(runs)
    ordered = sorted(events.items())
    endpoint_pairing = []
    for exponent, delta in ordered:
        if delta > 0:
            endpoint_pairing.append((exponent, delta))
        else:
            endpoint_pairing.append((exponent - int(inst["ribbon_length"]), -delta))
    return {
        "greedy_positive_boundaries": _attack_candidate(inst, [(e, d) for e, d in ordered if d > 0]),
        "outlier_largest_boundary_jumps": _attack_candidate(inst, sorted(ordered, key=lambda z: (-abs(z[1]), z[0]))),
        "obvious_run_start_ansatz": _attack_candidate(inst, [(lo, c) for lo, _hi, c in runs]),
        "in_context_endpoint_pairing": _attack_candidate(inst, endpoint_pairing),
    }


def _candidate_language_ok(inst, answer):
    try:
        lo, hi, k, bound, total, left_coefficient, right_coefficient = _candidate_constraints(inst)
        parsed = [(term[1][0], term[0][0], term[0][1]) for term in answer]
    except (IndexError, KeyError, TypeError, ValueError):
        return False
    return (
        len(parsed) == k
        and [exponent for exponent, _coefficient, _denominator in parsed]
            == sorted({exponent for exponent, _coefficient, _denominator in parsed})
        and parsed[0] == (lo, left_coefficient, 1)
        and parsed[-1] == (hi, right_coefficient, 1)
        and all(lo <= exponent <= hi and denominator == 1 and 1 <= coefficient <= bound
                for exponent, coefficient, denominator in parsed)
        and sum(coefficient for _exponent, coefficient, _denominator in parsed) == total
    )


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


_ORACLE_ARMS = {"bare": {"solved": None, "attempts": 0},
                "hinted": {"solved": None, "attempts": 0},
                "placebo": {"solved": None, "attempts": 0}}
_HINTED_VERDICT = "unavailable"


def selftest():
    report = {}
    verified = json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError((preset, seed, reason))
            recovered, _ = _sparse_recover(inst)
            if recovered != inst["answer"]:
                raise AssertionError((preset, seed, "sparse recovery disagrees"))
            verified += 1
            json_roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {"pass": verified == 12 and json_roundtrips == 12,
                                      "verified": verified, "json_roundtrips": json_roundtrips}

    easy = make_instance(seed=177, **DIFFICULTY["easy"])
    good = easy["answer"]
    variants = {"drop_one": json.loads(json.dumps(good[:-1])), "empty": [],
                "swap_two": json.loads(json.dumps(good)), "duplicate": json.loads(json.dumps(good)),
                "out_of_range": json.loads(json.dumps(good))}
    variants["swap_two"][0], variants["swap_two"][1] = variants["swap_two"][1], variants["swap_two"][0]
    variants["duplicate"][1][1][0] = variants["duplicate"][0][1][0]
    variants["out_of_range"][-1][1][0] = easy["root_exponent_range"][1] + 1
    corruptions = {}
    for name, candidate in variants.items():
        ok, reason = verify(easy, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {item["reason"] for item in corruptions.values()}
    report["G2_rejects_corruption"] = {"pass": all(x["rejected"] for x in corruptions.values()) and len(reasons) == 5,
                                        "cases": corruptions, "distinct_reasons": len(reasons)}

    encoded = json.dumps(good, separators=(",", ":"))
    prose = "I used exact coefficients.\n<answer>\n```json\n" + encoded + "\n```\n</answer>\n"
    report["G3_round_trip"] = {"pass": parse_answer(prose) == good and parse_answer(encoded) == good and parse_answer("garbage") is None,
                                "model_style": parse_answer(prose) == good, "raw": parse_answer(encoded) == good,
                                "garbage_rejected": parse_answer("garbage") is None}

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)
    space = search_space(shipping)
    guess_rng = random.Random(271828)
    samples = 200_000
    # Multiplication by a nonzero Laurent polynomial is injective over Z[x,x^-1],
    # so this instance has exactly one valid Q.  Equality with that canonical Q
    # is therefore the exact hit predicate and avoids redoing the same coefficient
    # comparison 200,000 times; G1 independently checks that Q with verify().
    hits = sum(int(random_candidate(shipping, guess_rng) == shipping["answer"])
               for _ in range(samples))
    exact_density_text = "1/" + str(space)
    density_log10 = -math.log10(space)
    report["G4_guess_resistance"] = {"pass": samples >= 200_000 and hits / samples < 1e-6 and 1 / space < 1e-6,
                                      "hits": hits, "total": samples, "sampled_probability": hits / samples,
                                      "exact_structure_aware_probability": exact_density_text,
                                      "exact_probability_log10": density_log10, "candidate_space": space,
                                      "prior": "uniform internal k-term support and uniform bounded positive coefficient compositions, conditioned on the forced endpoints and coefficient sum",
                                      "hit_test": "canonical equality, exact because the Laurent-polynomial multiplier is injective"}

    started = time.perf_counter()
    dense_answer, dense_operations = _dense_recover(shipping)
    dense_wall = time.perf_counter() - started
    compact_answer, compact_operations = _sparse_recover(shipping)
    dense_ok, compact_ok = verify(shipping, dense_answer)[0], verify(shipping, compact_answer)[0]
    demo_for_count = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_valid = enumerate_all(demo_for_count)
    report["G5_density_and_baseline"] = {"pass": dense_ok and compact_ok and dense_operations > 1_000_000 and space > 1_000_000,
        "shipping_preset": SHIPPING_DIFFICULTY, "exact_valid_answers": 1, "candidate_count": space,
        "exact_solution_density": exact_density_text, "exact_solution_density_log10": density_log10,
        "sampled_solution_density": hits / samples, "sample_hits": hits, "sample_total": samples,
        "demo_seed": 3, "demo_candidates_enumerated": search_space(demo_for_count),
        "demo_valid_answers_by_bruteforce": demo_valid,
        "baseline_wall_clock_sec": round(dense_wall, 6), "baseline_exact_arithmetic_operations": dense_operations,
        "compact_exact_arithmetic_operations": compact_operations}

    attack_names = list(_attack_candidates(shipping)) + ["random_sparse_restart_256"]
    successes = {name: 0 for name in attack_names}
    language_valid = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_wall = 0.0
    reference_operations = []
    attempts = 8
    for seed in range(90_000, 90_000 + attempts):
        inst = make_instance(seed=seed, **shipping_params)
        for name, candidate in _attack_candidates(inst).items():
            language_valid[name] += int(_candidate_language_ok(inst, candidate))
            successes[name] += int(verify(inst, candidate)[0])
        rrng = random.Random(700_000 + seed)
        restart_candidates = [random_candidate(inst, rrng) for _ in range(256)]
        language_valid["random_sparse_restart_256"] += int(
            all(_candidate_language_ok(inst, candidate) for candidate in restart_candidates))
        found = any(verify(inst, candidate)[0] for candidate in restart_candidates)
        successes["random_sparse_restart_256"] += int(found)
        started = time.perf_counter()
        recovered, operations = _dense_recover(inst)
        reference_wall += time.perf_counter() - started
        reference_operations.append(operations)
        reference_successes += int(verify(inst, recovered)[0])
    attacks = {name: {"successes": successes[name], "attempts": attempts,
                      "language_valid_attempts": language_valid[name]}
               for name in attack_names}
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {"pass": all_failed and len(attacks) >= 4
                                               and all(value == attempts for value in language_valid.values())
                                               and reference_successes == attempts,
        "attacks": attacks, "reference_algorithm": {"name": "dense Equation (2) recurrence tau_l=sigma_l-sigma_(l-1)+tau_(l-L)",
        "complexity": "O(D) exact arithmetic for D displayed integer levels",
        "wall_clock_sec_total": round(reference_wall, 6), "wall_clock_sec_mean": round(reference_wall / attempts, 6),
        "operations_per_instance_min": min(reference_operations), "solves": f"{reference_successes}/{attempts}, as expected"}}

    doubled = dict(shipping_params)
    doubled["n"] *= 2
    started = time.perf_counter()
    large = make_instance(seed=424242, **doubled)
    build_wall = time.perf_counter() - started
    large_ok = verify(large, large["answer"])[0]
    report["G7_scales"] = {"pass": large_ok and doubled["n"] > shipping_params["n"],
                            "shipping_n": shipping_params["n"], "doubled_n": doubled["n"],
                            "doubled_build_wall_clock_sec": round(build_wall, 6), "doubled_verifies": large_ok}

    invariant = carried = 0
    keys = []
    for seed in range(20):
        inst = make_instance(n=101, terms=12, chains=3, coeff_bound=5, seed=123_000 + seed)
        key = canonical_key(inst)
        keys.append(key)
        transforms = [_translated(inst, 137), _reflected(inst), _reordered(inst, random.Random(6000 + seed)),
                      _translated(_reflected(_reordered(inst, random.Random(8000 + seed))), -55)]
        for transformed in transforms:
            invariant += int(canonical_key(transformed) == key)
            carried += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {"pass": invariant == 80 and carried == 80 and len(set(keys)) == 20,
        "invariance_checks": invariant, "invariance_expected": 80, "carried_witness_checks": carried,
        "carried_witness_expected": 80, "unrelated_distinct": len(set(keys)), "unrelated_attempts": 20,
        "symmetries": ["global level translation", "level reflection", "input reordering", "compositions"]}

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars, answer_atoms = len(answer_blob), _answer_atoms(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    hinted, placebo = _ORACLE_ARMS["hinted"], _ORACLE_ARMS["placebo"]
    difference = None
    if hinted["attempts"] and placebo["attempts"]:
        difference = hinted["solved"] / hinted["attempts"] - placebo["solved"] / placebo["attempts"]
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and compact_operations <= 300
    # The three arms, including the hinted verdict, are diagnostic only as of
    # 2026-09-05.  G9 gates only the answer-size and intended-effort caps.
    report["G9_no_tool_suitability"] = {"pass": within_caps,
        "arms": json.loads(json.dumps(_ORACLE_ARMS)), "hinted_minus_placebo": difference,
        "hinted_verdict": _HINTED_VERDICT, "answer_chars": answer_chars, "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms, "intended_route_operations": compact_operations, "caps_pass": within_caps}
    report["all_passed"] = all(isinstance(value, dict) and value.get("pass")
                                  for name, value in report.items() if name.startswith("G"))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
