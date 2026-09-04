"""Verified generator for separated smooth biquadrate representations.

Brüdern and Wooley (arXiv:2110.04348) define ``A(P,R)`` to be the
``R``-smooth positive integers at most ``P`` and prove that sufficiently large
locally soluble integers are sums of twelve fourth powers of very smooth
integers.  This module asks for such a twelve-term representation under an
additional, explicit promise that the 2-adic valuations lie in separated
bands.  The promise creates a short invariant-based route without changing the
native objects or the exact Waring equation.
"""

from __future__ import annotations

import bisect
import functools
import hashlib
import itertools
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
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "R-smooth positive integers",
        "fourth powers (biquadrates)",
        "a twelve-term Waring equation",
        "2-adic valuation bands with odd smooth multipliers",
    ],
    "verification_operations": [
        "exact integer fourth powers and addition",
        "exact 2-adic valuation",
        "trial division encoded by smooth-number membership",
        "integer range and ordering comparisons",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Peel the summands from the least 2-adic valuation upward, since each "
        "wide valuation gap exposes one odd fourth power; without this invariant "
        "one searches every smooth candidate in every band."
    ),
    "hardness_basis": (
        "Track B: a band-by-band exact modular sieve solves the promised "
        "twelve-biquadrate problem in O(12*A*M_R(H)) candidate probes; at the "
        "shipping preset it averages 90,465 probes, 624,726 exact operations, "
        "and about 0.03--0.05 seconds over eight seeds in repeated measurements, "
        "whereas the 2-adic peeling route "
        "uses at most 120 high-level exact operations."
    ),
    "max_answer_tokens": 333,
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
    "demo": {"n": 3, "odd_bits": 1, "a_width": 1},
    "easy": {"n": 29, "odd_bits": 16, "a_width": 12},
    "medium": {"n": 59, "odd_bits": 16, "a_width": 16},
    "hard": {"n": 97, "odd_bits": 18, "a_width": 16},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Work from the least 2-adic valuation upward: each wide gap isolates one "
    "odd fourth power before the next band can contribute."
)
PLACEBO_HINT = (
    "Work through the twelve bands systematically, keeping every large integer "
    "exact and checking each smoothness condition before committing to the list."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly 12 strictly increasing positive integers.  There "
        "is one x=2^a*y per displayed band; a lies in that inclusive band and y "
        "has the form x=2^a*s*y for that band's displayed odd multiplier s, "
        "where y is odd and R-smooth with 1 <= y < 2^odd_bits."
    ),
    "bounds": {
        "length": 12,
        "a_choices_per_band": "a_width",
        "odd_part_choices": "M_R(odd_bits)",
        "candidate_count": "(a_width*M_R(odd_bits))^12",
    },
}

NOTES = (
    "Section 1 fixes A(P,R) as the positive integers at most P whose prime "
    "divisors are at most R, and Corollary 1.3 fixes the native twelve-term "
    "equation.  The paragraph after Corollary 1.3 supplies the local observation "
    "m^4 in {0,1} modulo 16 that motivates the higher 2-adic invariant here.  "
    "Theorem 1.2 and Corollary 1.3 are analytic existence results, not algorithms: "
    "the paper explicitly omits the corollary's proof and gives neither an FPT "
    "nor a representation-search procedure.  Consequently the representation is "
    "inverse-generated and no Track A hardness is claimed.  Each planted base is "
    "uniform in exactly the same (valuation, odd-smooth-part) pool as its band's "
    "decoys.  The separated bands defeat largest-first rounding, midpoint/outlier, "
    "independent low-residue, and random-restart attacks.  A complete modular "
    "sieve is reported openly as the Track B reference algorithm."
)

_TERMS = 12
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 100_000

# Filled from the three script-owned hardening runs at the shipping preset.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


@functools.lru_cache(maxsize=None)
def _primes_upto(limit):
    if limit < 2:
        return tuple()
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p : limit + 1 : p] = b"\x00" * (
                (limit - p * p) // p + 1
            )
    return tuple(i for i in range(2, limit + 1) if sieve[i])


@functools.lru_cache(maxsize=None)
def _odd_smooth_values(smooth_bound, odd_bits):
    """All odd R-smooth y with 1 <= y < 2^odd_bits, in sorted order."""
    limit = 1 << odd_bits
    primes = tuple(p for p in _primes_upto(smooth_bound) if p != 2)
    values = []

    def visit(index, value):
        if index == len(primes):
            values.append(value)
            return
        prime = primes[index]
        while value < limit:
            visit(index + 1, value)
            value *= prime

    visit(0, 1)
    return tuple(sorted(values))


def _v2(value):
    if value <= 0:
        raise ValueError("2-adic valuation needs a positive integer")
    return (value & -value).bit_length() - 1


def _fourth_root_floor(value):
    if value < 0:
        raise ValueError("fourth root needs a nonnegative integer")
    return math.isqrt(math.isqrt(value))


def _sorted_bands(inst):
    return sorted((int(lo), int(hi), int(multiplier))
                  for lo, hi, multiplier in inst["bands"])


def _candidate_count_per_band(inst):
    odd_count = len(_odd_smooth_values(inst["smooth_bound"], inst["odd_bits"]))
    return inst["a_width"] * odd_count


def make_instance(n, seed=0, **params):
    """Inverse-generate twelve smooth bases, then sum their fourth powers.

    ``n`` is the smoothness bound R.  Larger n admits more odd smooth parts and
    therefore enlarges the decoy pool without increasing the number of answer
    elements.  No representation search is performed during generation.
    """
    odd_bits = params.pop("odd_bits", 16)
    a_width = params.pop("a_width", 12)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value, lower in (
        ("n", n, 3),
        ("odd_bits", odd_bits, 1),
        ("a_width", a_width, 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < lower:
            raise ValueError(f"{name} must be an integer at least {lower}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    odd_values = _odd_smooth_values(n, odd_bits)
    if not odd_values:
        raise ValueError("the odd smooth pool is empty")
    rng = random.Random(seed)

    # The minimum gap between consecutive bands is odd_bits+3.  Consequently,
    # after the least power of two is removed, reduction modulo 2^(4*odd_bits)
    # contains exactly one odd fourth power and no contribution from later bands.
    stride = a_width + odd_bits + 2
    balance_step = 0
    balance_power = 1
    while balance_power < (1 << stride):
        balance_power *= 3
        balance_step += 1
    offset = rng.randrange(0, 7)
    bands = []
    answer = []
    exponents = []
    for index in range(_TERMS):
        lo = offset + index * stride
        hi = lo + a_width - 1
        a = rng.randint(lo, hi)
        y = rng.choice(odd_values)
        multiplier = 3 ** (balance_step * (_TERMS - 1 - index))
        bands.append([lo, hi, multiplier])
        answer.append((1 << a) * multiplier * y)
        exponents.append([a, y])

    answer.sort()
    target = sum(x * x * x * x for x in answer)
    base_bound = max(
        (1 << hi) * multiplier * ((1 << odd_bits) - 1)
        for _lo, hi, multiplier in bands
    )
    rng.shuffle(bands)
    return {
        "paper": "arXiv:2110.04348",
        "family": "separated_twelve_smooth_biquadrates",
        "n": n,
        "smooth_bound": n,
        "odd_bits": odd_bits,
        "a_width": a_width,
        "terms": _TERMS,
        "P": base_bound,
        "target": target,
        "bands": bands,
        "answer": answer,
    }


def render(inst):
    """Render a self-contained exact Waring-representation problem."""
    bands = inst["bands"]
    lines = [
        "Twelve smooth biquadrates in separated 2-adic bands",
        "",
        "A positive integer is R-smooth when every prime divisor is at most R;",
        "the integer 1 is R-smooth.  The 2-adic valuation v2(x) is the unique",
        "nonnegative integer a for which x=2^a*y with y odd.",
        "",
        f"Here R = {inst['smooth_bound']}, P = {inst['P']}, and the odd-part cap is",
        f"2^{inst['odd_bits']} = {1 << inst['odd_bits']} (the upper endpoint is excluded).",
        f"The target integer N is:\n{inst['target']}",
        "",
        f"Find exactly {inst['terms']} distinct R-smooth positive integers",
        f"x_0 < x_1 < ... < x_{inst['terms'] - 1}, each at most P, such that",
        "",
        "    x_0^4 + x_1^4 + ... + x_11^4 = N.",
        "",
        "There must be exactly one answer integer for each band line below.  A line",
        "'lo hi s' requires v2(x)=a in the inclusive range lo..hi and requires",
        "x=2^a*s*y, where y is odd, R-smooth, and satisfies",
        f"1 <= y < 2^{inst['odd_bits']}.  The band lines are deliberately unordered;",
        "their printed order carries no meaning.  The increasing order of the answer",
        "is mandatory, and repeats are forbidden.",
        "",
        "V2 BANDS AND ODD MULTIPLIERS (lo hi s):",
    ]
    lines.extend(f"{lo} {hi} {multiplier}" for lo, hi, multiplier in bands)
    lines.extend(
        [
            "",
            f"Return one JSON array of exactly {inst['terms']} decimal integers in",
            "strictly increasing order.  Do not return fourth powers, exponents,",
            "factorizations, labels, ellipses, or more than one array.",
            "Give your final answer inside <answer></answer> tags, as that JSON array.",
            "Example syntax only: <answer>[1,2,3,4,5,6,7,8,9,10,11,12]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged JSON integer list, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in answer):
        return None
    return answer


def verify(inst, answer):
    """Check any valid witness without consulting ``inst['answer']``."""
    if not isinstance(answer, list) or not all(
        isinstance(x, int) and not isinstance(x, bool) for x in answer
    ):
        return False, "malformed: expected one JSON list of decimal integers"
    if not answer:
        return False, "empty answer: twelve positive integers are required"
    if len(answer) != inst["terms"]:
        return False, f"wrong length: expected {inst['terms']}, got {len(answer)}"
    if any(x <= 0 or x > inst["P"] for x in answer):
        return False, f"out of range: every integer must lie in 1..{inst['P']}"
    if len(set(answer)) != len(answer):
        return False, "duplicate integer: all twelve bases must be distinct"
    if any(answer[i] >= answer[i + 1] for i in range(len(answer) - 1)):
        return False, "wrong order: the twelve bases must be strictly increasing"

    bands = _sorted_bands(inst)
    odd_set = set(_odd_smooth_values(inst["smooth_bound"], inst["odd_bits"]))
    used_bands = set()
    for index, x in enumerate(answer):
        a = _v2(x)
        matches = [
            (band_index, band)
            for band_index, band in enumerate(bands)
            if band_index not in used_bands and band[0] <= a <= band[1]
        ]
        if len(matches) != 1:
            return False, (
                f"band violation at index {index}: v2({x})={a} belongs to "
                f"{len(matches)} unused bands"
            )
        band_index, (_lo, _hi, multiplier) = matches[0]
        used_bands.add(band_index)
        odd_part = x >> a
        if odd_part % multiplier:
            return False, (
                f"multiplier violation at index {index}: odd part is not divisible "
                f"by {multiplier}"
            )
        y = odd_part // multiplier
        if y >= (1 << inst["odd_bits"]):
            return False, f"reduced odd-part cap violated at index {index}: {y} is too large"
        if y not in odd_set:
            return False, (
                f"not {inst['smooth_bound']}-smooth at index {index}: odd part {y} "
                "has a forbidden prime divisor"
            )

    total = sum(x * x * x * x for x in answer)
    if total != inst["target"]:
        return False, f"wrong fourth-power sum: got {total}, expected {inst['target']}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact band-aware bounded certificate language."""
    odd_values = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
    answer = []
    for lo, hi, multiplier in _sorted_bands(inst):
        a = rng.randint(lo, hi)
        y = rng.choice(odd_values)
        answer.append((1 << a) * multiplier * y)
    return sorted(answer)


def search_space(inst):
    return _candidate_count_per_band(inst) ** inst["terms"]


def enumerate_all(inst):
    total = search_space(inst)
    if total > _ENUMERATION_CAP:
        return None
    odd_values = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
    choices = [
        [(1 << a) * multiplier * y
         for a in range(lo, hi + 1) for y in odd_values]
        for lo, hi, multiplier in _sorted_bands(inst)
    ]
    count = 0
    for candidate in itertools.product(*choices):
        count += int(verify(inst, sorted(candidate))[0])
    return count


def canonical_key(inst):
    """Canonicalize band order and the global power-of-two scaling symmetry."""
    bands = _sorted_bands(inst)
    shift = min(lo for lo, _hi, _multiplier in bands)
    scale4 = 1 << (4 * shift)
    if inst["target"] % scale4:
        raise ValueError("target is incompatible with its lowest valuation band")
    payload = {
        "smooth_bound": inst["smooth_bound"],
        "odd_bits": inst["odd_bits"],
        "a_width": inst["a_width"],
        "terms": inst["terms"],
        "bands": [[lo - shift, hi - shift, multiplier]
                  for lo, hi, multiplier in bands],
        "target": inst["target"] // scale4,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Enlarge the smooth haystack while preserving twelve answer elements."""
    n = int(params.get("n", 29))
    odd_bits = int(params.get("odd_bits", 16))
    a_width = int(params.get("a_width", 12))
    next_params = {
        "n": n + 48,
        "odd_bits": odd_bits + int(n >= 193),
        "a_width": a_width + int(n >= 193),
    }

    # Conservatively project the longest possible JSON answer at the next level.
    # This follows the construction's largest offset and 3-power multiplier; the
    # twelve answer atoms themselves never increase.
    stride = next_params["a_width"] + next_params["odd_bits"] + 2
    balance_step = math.ceil(stride / math.log2(3))
    projected_chars = 13  # brackets plus eleven commas
    for index in range(_TERMS):
        exponent = 6 + index * stride + next_params["a_width"] - 1
        bit_bound = (
            exponent
            + balance_step * (_TERMS - 1 - index) * math.log2(3)
            + next_params["odd_bits"]
        )
        projected_chars += max(1, math.ceil(bit_bound * math.log10(2)))
    if projected_chars >= 1900:
        return "cap_bound"
    return next_params


def _compact_peel(inst):
    """Recover the witness by the intended 2-adic invariant."""
    residual = inst["target"]
    odd_set = set(_odd_smooth_values(inst["smooth_bound"], inst["odd_bits"]))
    answer = []
    modulus = 1 << (4 * (inst["odd_bits"] + 2))
    mask = modulus - 1
    for lo, hi, multiplier in _sorted_bands(inst):
        if residual <= 0:
            return None
        valuation = _v2(residual)
        if valuation % 4:
            return None
        a = valuation // 4
        odd_fourth_residue = (residual >> (4 * a)) & mask
        multiplier_fourth = pow(multiplier, 4, modulus)
        reduced_fourth = (
            odd_fourth_residue * pow(multiplier_fourth, -1, modulus)
        ) % modulus
        y = _fourth_root_floor(reduced_fourth)
        if y * y * y * y != reduced_fourth:
            return None
        if not (lo <= a <= hi) or y not in odd_set:
            return None
        x = (1 << a) * multiplier * y
        answer.append(x)
        residual -= x * x * x * x
    return sorted(answer) if residual == 0 else None


def _reference_modular_sieve(inst):
    """Mechanical band-by-band candidate sieve, with exact operation counts."""
    bands = _sorted_bands(inst)
    odd_values = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
    residual = inst["target"]
    answer = []
    probes = 0
    operations = 0
    for index, (lo, hi, multiplier) in enumerate(bands):
        next_lo = bands[index + 1][0] if index + 1 < len(bands) else None
        mask = (1 << (4 * next_lo)) - 1 if next_lo is not None else None
        wanted = residual & mask if mask is not None else residual
        found = None
        for a in range(lo, hi + 1):
            for y in odd_values:
                probes += 1
                y2 = y * y
                y4 = y2 * y2
                multiplier2 = multiplier * multiplier
                multiplier4 = multiplier2 * multiplier2
                term = (y4 * multiplier4) << (4 * a)
                operations += 6
                residue = term & mask if mask is not None else term
                operations += int(mask is not None)
                if residue == wanted:
                    found = (1 << a) * multiplier * y
                    operations += 1
                    break
            if found is not None:
                break
        if found is None:
            return None, {"candidate_probes": probes, "exact_operations": operations}
        answer.append(found)
        residual -= found * found * found * found
        operations += 3
    return (sorted(answer) if residual == 0 else None), {
        "candidate_probes": probes,
        "exact_operations": operations,
    }


def _nearest_allowed(inst, band, value):
    """Nearest legal base in one band; used only by cheap attacks."""
    odd_values = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
    best = None
    multiplier = band[2]
    for a in range(band[0], band[1] + 1):
        scaled = (value >> a) // multiplier
        pos = bisect.bisect_left(odd_values, scaled)
        for at in (pos - 1, pos):
            if 0 <= at < len(odd_values):
                candidate = (1 << a) * multiplier * odd_values[at]
                score = abs(candidate - value)
                if best is None or (score, candidate) < best:
                    best = (score, candidate)
    return best[1]


def _greedy_top_down(inst, nearest=False):
    residual = inst["target"]
    chosen = []
    for band in reversed(_sorted_bands(inst)):
        if residual <= 0:
            target_root = 1
        else:
            target_root = _fourth_root_floor(residual)
        candidate = _nearest_allowed(inst, band, target_root)
        if not nearest and candidate**4 > residual:
            # Move to the largest legal candidate not exceeding the root.
            odd_values = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
            legal = []
            multiplier = band[2]
            for a in range(band[0], band[1] + 1):
                pos = bisect.bisect_right(
                    odd_values, (target_root >> a) // multiplier
                ) - 1
                if pos >= 0:
                    legal.append((1 << a) * multiplier * odd_values[pos])
            candidate = max(legal) if legal else (1 << band[0]) * multiplier
        chosen.append(candidate)
        residual -= candidate**4
    return sorted(chosen)


def _attack_candidates(inst, seed):
    bands = _sorted_bands(inst)
    odds = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
    midpoint = [
        (1 << ((lo + hi) // 2)) * multiplier * odds[len(odds) // 2]
        for lo, hi, multiplier in bands
    ]
    midpoint.sort()
    minimum = sorted((1 << lo) * multiplier * odds[0]
                     for lo, _hi, multiplier in bands)
    rrng = random.Random(seed ^ 0x211004348)
    return {
        "outlier_band_midpoint": [midpoint],
        "greedy_largest_first": [_greedy_top_down(inst, nearest=False)],
        "by_hand_nearest_fourth_root": [_greedy_top_down(inst, nearest=True)],
        "independent_band_minima": [minimum],
        "random_restart_256": [random_candidate(inst, rrng) for _ in range(256)],
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    order = list(range(len(inst["bands"])))
    rng.shuffle(order)
    shift = rng.randint(1, 5)
    variants = []
    for mask in range(1, 4):
        out = {
            key: ([list(v) for v in value] if key == "bands" else list(value)
                  if key == "answer" else value)
            for key, value in inst.items()
        }
        if mask & 1:
            out["bands"] = [out["bands"][i] for i in order]
        if mask & 2:
            out["bands"] = [
                [lo + shift, hi + shift, multiplier]
                for lo, hi, multiplier in out["bands"]
            ]
            out["target"] <<= 4 * shift
            out["P"] <<= shift
            out["answer"] = [x << shift for x in out["answer"]]
        variants.append(out)
    return variants


def _worst_case_answer_size(inst):
    odds = _odd_smooth_values(inst["smooth_bound"], inst["odd_bits"])
    maxima = sorted((1 << hi) * multiplier * odds[-1]
                    for _lo, hi, multiplier in _sorted_bands(inst))
    blob = json.dumps(maxima, separators=(",", ":"))
    return len(blob), math.ceil(len(blob) / 4), len(maxima)


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": attempts,
        "failures": g1_failures,
        "generation_route": "inverse generation before target summation",
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": [-1] + answer[1:],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The valuation calculation gives this representation.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nEach entry is a base, not a fourth power."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x211004348)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "candidate_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
        "prior": "uniform over one legal smooth base from each valuation band",
    }

    attack_names = list(_attack_candidates(inst, 0))
    attack_successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    compact_successes = 0
    reference_seconds = 0.0
    reference_probes = 0
    reference_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name, options in candidates.items():
            started = time.perf_counter()
            won = any(verify(trial, option)[0] for option in options)
            attack_seconds[name] += time.perf_counter() - started
            attack_successes[name] += int(won)
        started = time.perf_counter()
        recovered, counts = _reference_modular_sieve(trial)
        reference_seconds += time.perf_counter() - started
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        reference_probes += counts["candidate_probes"]
        reference_operations += counts["exact_operations"]
        compact = _compact_peel(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": attack_successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    all_failed = all(value == 0 for value in attack_successes.values())
    reference = {
        "name": "exact band-by-band modular candidate sieve",
        "complexity": "O(12*a_width*M_R(odd_bits)) candidate probes",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "candidate_probes": reference_probes // 8,
        "operations": reference_operations // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "least-valuation 2-adic peeling",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": 10 * inst["terms"],
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    exact_denominator = search_space(inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": 1 / exact_denominator,
        "shipping_exact_solution_count": 1,
        "shipping_candidate_count": exact_denominator,
        "uniqueness_basis": "induction by reduction modulo the next valuation band",
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
        "reference_candidate_probes": reference["candidate_probes"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    started = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - started
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst)
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
        "answer_elements_shipping": len(inst["answer"]),
        "answer_elements_doubled": len(doubled["answer"]),
    }

    invariant_count = 0
    real_count = 0
    unrelated = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(canonical_key(transformed) == key)
            real_count += int(verify(transformed, transformed["answer"])[0])
        unrelated.append(key)
    distinct_count = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 60 and real_count == 60 and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "input-band reordering",
            "global multiplication of every base by a power of two",
            "composition of band reordering with global scaling",
        ],
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    worst_chars, worst_tokens, worst_elements = _worst_case_answer_size(inst)
    intended_operations = 10 * inst["terms"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and worst_chars <= 2_000
        and worst_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": len(inst["answer"]),
        "intended_route_operations": intended_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
