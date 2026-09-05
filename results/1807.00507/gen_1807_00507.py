"""Verified completion-puzzle generator for arXiv:1807.00507.

The paper defines the n-fractions CSP.  This module composes exact balanced
three-fraction identities, masks one digit in every fraction, and asks for a
completion.  The planted completion is known from the identities; it is never
found by solving the generated instance.
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
import statistics
import sys
import time
from collections import Counter


sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family itself is standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "decimal digit variables",
        "two-digit denominators",
        "finite-domain rational equation",
    ],
    "verification_operations": [
        "exact digit occurrence counting",
        "exact integer substitution into rational fractions",
        "exact scaled-integer equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize balanced three-fraction identities with unit-fraction "
        "subtotals; without that decomposition, enumerate panel-valid digit "
        "assignments and match their exact rational sums."
    ),
    "hardness_basis": (
        "Track B: Section 2 compiles the finite-domain model to CNF for a SAT "
        "solver; on this completion distribution the measured exact panel "
        "meet-in-the-middle reference algorithm uses O(A*n) work for two "
        "panels (A=51,840 panel assignments at shipping), about 0.50 seconds "
        "and 3.0 million counted exact arithmetic operations over eight "
        "shipping seeds, while the public balanced-band/unit-fraction route "
        "uses at most 293 counted exact arithmetic operations."
    ),
    "max_answer_tokens": 10,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY: dict = {
    "demo": {"n": 6, "bands_per_panel": 1},
    "easy": {"n": 9, "bands_per_panel": 1},
    "medium": {"n": 12, "bands_per_panel": 2},
    "hard": {"n": 18, "bands_per_panel": 3},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A flat JSON list of exactly n digits in 1..9, one for each question "
        "mark in row order.  The three supplied digits in every band are "
        "pairwise distinct, and after substitution every digit 1..9 occurs "
        "exactly bands_per_panel times in each panel."
    ),
    "bounds": {
        "answer_digits": "exactly n",
        "digit_min": 1,
        "digit_max": 9,
        "n_max_supported": 36,
        "atomic_elements_max": 36,
    },
}

STRUCTURAL_HINT: str = (
    "The completed nine digits in each three-row band form a permutation of "
    "1 through 9 with a unit-fraction subtotal."
)
PLACEBO_HINT: str = (
    "The displayed panel and band labels keep every fraction row aligned with "
    "its single missing entry."
)

NOTES: str = (
    "Section 1, Equation (1), fixes the native definition: nonzero decimal "
    "digits, two-digit denominators 10*y+z, total fraction sum one, and each "
    "digit occurring between one and ceil(n/3) times. Section 2.1 gives the "
    "domain/counting constraints, Section 2.2 the lexicographic symmetry "
    "break, Sections 2.3--2.4 the common-multiple integer model, and Section 3 "
    "states that BEE compiles it to CNF and Glucose solves it. Table 1 is the "
    "easy-method warning: the paper reports 7.03 CPU seconds already at n=18 "
    "and 102.20 CPU hours at n=39, so an undisclosed Track A claim would be "
    "wrong. The generator instead uses composition of identities. Each native "
    "three-row block uses digits 1..9 once and has a checked subtotal 1/d; the "
    "chosen reciprocals sum to one. One x, one y, and one z digit are masked in "
    "each block. Panels add only digit-count constraints that imply the paper's "
    "global count condition. The reference algorithm enumerates all panel-valid "
    "multiset assignments and matches exact scaled sums. The compact route "
    "recognizes unit-fraction subtotals directly from the public rational data; "
    "it never consults the private template table. Nearest-visible-digit, "
    "equal-panel-sum, equal-band-sum, and structure-aware random-restart attacks "
    "are measured."
)


# Every tuple is (numerator, tens digit, ones digit).  Each three-tuple template
# uses digits 1..9 exactly once and its three fractions sum to 1/key.  These are
# finite identities, checked at import-independent self-test time.
_TEMPLATES = {
    2: [((5, 1, 6), (3, 4, 8), (9, 7, 2))],
    3: [
        ((2, 1, 8), (7, 4, 9), (5, 6, 3)),
        ((2, 1, 9), (6, 3, 8), (4, 5, 7)),
        ((3, 2, 7), (6, 5, 4), (9, 8, 1)),
        ((7, 3, 2), (5, 4, 8), (1, 9, 6)),
    ],
    4: [
        ((1, 2, 6), (5, 3, 9), (7, 8, 4)),
        ((3, 5, 4), (6, 7, 2), (9, 8, 1)),
        ((5, 3, 2), (1, 4, 8), (7, 9, 6)),
        ((5, 3, 2), (7, 8, 4), (1, 9, 6)),
    ],
    6: [
        ((1, 2, 4), (3, 5, 6), (7, 9, 8)),
        ((1, 3, 2), (7, 8, 4), (5, 9, 6)),
        ((1, 5, 6), (3, 7, 2), (9, 8, 4)),
    ],
    10: [((1, 3, 8), (4, 7, 6), (2, 9, 5))],
}

_DECOMPOSITIONS = {
    2: [2, 2],
    3: [3, 3, 3],
    4: [4, 4, 4, 4],
    5: [4, 4, 6, 6, 6],
    # Deliberately mixed: the obvious "all bands have equal sum" ansatz fails.
    6: [2, 10, 10, 10, 10, 10],
    7: [4, 4, 10, 10, 10, 10, 10],
    8: [6, 6, 6, 10, 10, 10, 10, 10],
    10: [10] * 10,
}

# Table 2's n=36 witness, rearranged (without changing a fraction) into twelve
# balanced three-row bands.  This is used only for G7's doubled-size check.
_PUBLISHED_36_BANDS = (
    [((2, 4, 8), (1, 7, 5), (3, 9, 6))] * 5
    + [((1, 4, 8), (2, 7, 5), (3, 9, 6))]
    + [((1, 4, 8), (3, 7, 5), (2, 9, 6))] * 6
)

_COLUMN_PATTERNS = tuple(itertools.permutations(range(3)))


def _identity_sum(rows):
    """Return (numerator, denominator) for a tiny exact rational sum."""
    num, den = 0, 1
    for x, y, z in rows:
        q = 10 * y + z
        num, den = num * q + x * den, den * q
        g = math.gcd(num, den)
        num //= g
        den //= g
    return num, den


@functools.lru_cache(maxsize=None)
def _language_count_from_counts(counts, bands):
    """Count multiset strings whose consecutive triples have distinct digits."""
    counts = tuple(counts)
    total_positions = 3 * bands

    @functools.lru_cache(maxsize=None)
    def visit(pos, remaining, used_mask):
        if pos == total_positions:
            return 1
        if pos % 3 == 0:
            used_mask = 0
        result = 0
        for index, count in enumerate(remaining):
            if count and not ((used_mask >> index) & 1):
                rest = list(remaining)
                rest[index] -= 1
                result += visit(
                    pos + 1, tuple(rest), used_mask | (1 << index)
                )
        return result

    return visit(0, counts, 0)


def _missing_counts_for_full_bands(full_bands, patterns):
    missing = []
    for rows, pattern in zip(full_bands, patterns):
        missing.extend(rows[i][pattern[i]] for i in range(3))
    counts = tuple(Counter(missing).get(d, 0) for d in range(1, 10))
    return missing, counts


def _choose_mask_patterns(full_bands, rng):
    """Choose masks with a controlled, nontrivial structure-aware language."""
    bands = len(full_bands)
    if bands >= 4:
        # Exhausting all 6^bands column patterns is unnecessary at the larger
        # fixed-answer-length escalation and made instance generation itself a
        # search bottleneck.  A uniformly sampled pattern already produces a
        # panel language many orders of magnitude larger than the shipping
        # language; it does not inspect whether the planted answer works.
        return tuple(rng.choice(_COLUMN_PATTERNS) for _ in full_bands)
    combinations = list(itertools.product(_COLUMN_PATTERNS, repeat=bands))
    rng.shuffle(combinations)
    desired = {2: 216, 3: 51_840}.get(bands)
    scored = []
    for patterns in combinations:
        _, counts = _missing_counts_for_full_bands(full_bands, patterns)
        count = _language_count_from_counts(counts, bands)
        if desired is not None and count == desired:
            return patterns
        scored.append((count, patterns))
    # Larger non-shipping panels use the largest available haystack.  This
    # selection counts a bounded language; it never searches for a solution.
    best = max(count for count, _ in scored)
    choices = [patterns for count, patterns in scored if count == best]
    return rng.choice(choices)


def _make_full_bands(n, rng):
    blocks = n // 3
    if n == 36:
        result = [[list(row) for row in band] for band in _PUBLISHED_36_BANDS]
    else:
        if blocks not in _DECOMPOSITIONS:
            raise ValueError(
                "n must be one of 6, 9, 12, 15, 18, 21, 24, 30, or 36"
            )
        result = []
        for unit_denominator in _DECOMPOSITIONS[blocks]:
            template = rng.choice(_TEMPLATES[unit_denominator])
            result.append([list(row) for row in template])
    for rows in result:
        rng.shuffle(rows)
    rng.shuffle(result)
    return result


def _common_scale(panels):
    """LCM of every denominator attainable by filling one displayed hole."""
    scale = 1
    for panel in panels:
        for band in panel:
            for row in band:
                hole = row.index(0)
                digits = range(1, 10) if hole in (1, 2) else (1,)
                for digit in digits:
                    completed = row[:]
                    completed[hole] = digit
                    scale = math.lcm(scale, 10 * completed[1] + completed[2])
    return scale


def _scaled_term(row, digit, scale):
    completed = row[:]
    completed[completed.index(0)] = digit
    return completed[0] * (scale // (10 * completed[1] + completed[2]))


def _panel_rows(panel):
    return [row for band in panel for row in band]


def _required_missing(panel):
    bands = len(panel)
    fixed = Counter(value for row in _panel_rows(panel) for value in row if value)
    missing = []
    for digit in range(1, 10):
        need = bands - fixed[digit]
        if need < 0:
            raise ValueError("invalid panel: a fixed digit is overrepresented")
        missing.extend([digit] * need)
    if len(missing) != 3 * bands:
        raise ValueError("invalid panel: fixed digit counts do not balance")
    return missing


def make_instance(n, seed=0, **params) -> dict:
    """Compose identities and mask them; never solve the generated completion."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    bands_per_panel = params.pop("bands_per_panel", 1)
    if isinstance(bands_per_panel, bool) or not isinstance(bands_per_panel, int):
        raise TypeError("bands_per_panel must be an integer")
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if n % 3 or n < 6:
        raise ValueError("n must be a supported positive multiple of 3")
    n_bands = n // 3
    if bands_per_panel < 1 or n_bands % bands_per_panel:
        raise ValueError("bands_per_panel must divide n/3")

    rng = random.Random(seed)
    full_bands = _make_full_bands(n, rng)
    panels = []
    nested_answers = []
    for start in range(0, n_bands, bands_per_panel):
        group = full_bands[start : start + bands_per_panel]
        patterns = _choose_mask_patterns(group, rng)
        masked_panel = []
        answer_panel = []
        for rows, pattern in zip(group, patterns):
            masked_band = []
            answer_band = []
            for row, hole in zip(rows, pattern):
                answer_band.append(row[hole])
                clue = row[:]
                clue[hole] = 0
                masked_band.append(clue)
            masked_panel.append(masked_band)
            answer_panel.append(answer_band)
        order = list(range(len(masked_panel)))
        rng.shuffle(order)
        panels.append([masked_panel[i] for i in order])
        nested_answers.append([answer_panel[i] for i in order])

    order = list(range(len(panels)))
    rng.shuffle(order)
    panels = [panels[i] for i in order]
    nested_answers = [nested_answers[i] for i in order]
    answer = [d for panel in nested_answers for band in panel for d in band]
    scale = _common_scale(panels)
    return {
        "n": n,
        "bands_per_panel": bands_per_panel,
        "panels": panels,
        "scale": scale,
        "answer": answer,
    }


def render(inst) -> str:
    n = inst["n"]
    bands_per_panel = inst["bands_per_panel"]
    lines = [
        "BALANCED n-FRACTIONS COMPLETION",
        "",
        "A fraction row (x,y,z) denotes x/(10*y+z); thus y and z are the "
        "tens and ones digits of a two-digit denominator. All digits are "
        "integers in the inclusive range 1..9, and repeated digits are allowed "
        "except where a band rule below forbids them.",
        "",
        f"There are n={n} fraction rows, divided into panels and three-row "
        "bands. Every row contains exactly one question mark.",
        "",
        "Fill every question mark subject to all three rules:",
        "1. In each three-row band, the three supplied missing digits are "
        "pairwise distinct.",
        f"2. In each panel, every digit 1..9 occurs exactly "
        f"{bands_per_panel} time(s) among all numerator and denominator digit "
        "positions after completion.",
        "3. The exact sum of all n completed fractions is 1.",
        "",
        "Rule 2 implies that globally every digit occurs exactly n/3 times, "
        "which is the n-fractions occurrence bound. Panel and band order is "
        "only an ordering of terms; fraction rows may not be moved between "
        "the displayed bands when applying Rule 1.",
        "",
        "Rows are numbered consecutively from 0. Data are written as "
        "`row: x y z`, with `?` marking the missing digit.",
    ]
    row_number = 0
    for p_index, panel in enumerate(inst["panels"]):
        lines.extend(["", f"PANEL {p_index}"])
        for b_index, band in enumerate(panel):
            lines.append(f"  Band {b_index}")
            for row in band:
                shown = ["?" if value == 0 else str(value) for value in row]
                lines.append(f"    {row_number}: {' '.join(shown)}")
                row_number += 1
    lines.extend(
        [
            "",
            f"Output one flat JSON array of exactly {n} digits, in row-number "
            "order. Entry i replaces the question mark in row i. Do not output "
            "the fixed digits. JSON array order matters; no repeats are barred "
            "except by Rules 1 and 2.",
            "",
            "Give your final answer inside <answer></answer> tags, as the JSON "
            "array just defined.",
            f"Example format: <answer>{json.dumps([1] * n, separators=(',', ':'))}</answer>",
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
    if not isinstance(text, str):
        return None
    candidates = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    candidates += re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    candidates.append(text)
    for candidate in candidates:
        candidate = candidate.strip()
        variants = [candidate]
        left, right = candidate.find("["), candidate.rfind("]")
        if 0 <= left < right:
            variants.append(candidate[left : right + 1])
        for variant in variants:
            try:
                value = json.loads(variant)
            except (TypeError, ValueError):
                continue
            if isinstance(value, list) and all(
                isinstance(x, int) and not isinstance(x, bool) for x in value
            ):
                return value
    return None


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) != n:
        return False, f"wrong answer length: expected {n} digits"
    for index, digit in enumerate(answer):
        if not isinstance(digit, int) or isinstance(digit, bool):
            return False, f"entry {index} is not an integer"
        if not 1 <= digit <= 9:
            return False, f"digit at position {index} is outside 1..9"

    scale = inst.get("scale") or _common_scale(inst["panels"])
    total = 0
    offset = 0
    for p_index, panel in enumerate(inst["panels"]):
        counts = Counter()
        for b_index, band in enumerate(panel):
            supplied = answer[offset : offset + 3]
            if len(set(supplied)) != 3:
                return (
                    False,
                    f"the three supplied digits in panel {p_index}, band "
                    f"{b_index} are not distinct",
                )
            for row, digit in zip(band, supplied):
                completed = row[:]
                completed[completed.index(0)] = digit
                counts.update(completed)
                total += _scaled_term(row, digit, scale)
            offset += 3
        want = len(panel)
        if any(counts[digit] != want for digit in range(1, 10)):
            return (
                False,
                f"panel {p_index} does not contain each digit exactly {want} "
                "time(s)",
            )
    if total != scale:
        g = math.gcd(total, scale)
        return (
            False,
            f"the completed fractions sum to {total // g}/{scale // g}, not 1",
        )
    return True, "ok"


def _random_panel_assignment(panel, rng):
    missing = _required_missing(panel)
    while True:
        candidate = missing[:]
        rng.shuffle(candidate)
        if all(
            len(set(candidate[i : i + 3])) == 3
            for i in range(0, len(candidate), 3)
        ):
            return candidate


def random_candidate(inst, rng):
    """Uniformly sample the stated digit-count and band-distinct language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    result = []
    for panel in inst["panels"]:
        result.extend(_random_panel_assignment(panel, rng))
    return result


def search_space(inst):
    result = 1
    for panel in inst["panels"]:
        missing = Counter(_required_missing(panel))
        counts = tuple(missing.get(d, 0) for d in range(1, 10))
        result *= _language_count_from_counts(counts, len(panel))
    return result


def _multiset_permutations(values):
    counts = Counter(values)
    keys = sorted(counts)
    output = [0] * len(values)

    def visit(position):
        if position == len(output):
            yield tuple(output)
            return
        for value in keys:
            if counts[value]:
                counts[value] -= 1
                output[position] = value
                yield from visit(position + 1)
                counts[value] += 1

    yield from visit(0)


def _panel_candidates(panel, scale):
    rows = _panel_rows(panel)
    missing = _required_missing(panel)
    for supplied in _multiset_permutations(missing):
        if not all(
            len(set(supplied[i : i + 3])) == 3
            for i in range(0, len(supplied), 3)
        ):
            continue
        subtotal = sum(
            _scaled_term(row, digit, scale)
            for row, digit in zip(rows, supplied)
        )
        yield subtotal, supplied


def enumerate_all(inst):
    """Count exactly with meet-in-the-middle when its bounded work is modest."""
    per_panel = []
    for panel in inst["panels"]:
        missing = Counter(_required_missing(panel))
        counts = tuple(missing.get(d, 0) for d in range(1, 10))
        count = _language_count_from_counts(counts, len(panel))
        if count > 60_000:
            return None
        per_panel.append(Counter(s for s, _ in _panel_candidates(panel, inst["scale"])))
    if not per_panel:
        return 0
    if len(per_panel) == 1:
        return per_panel[0][inst["scale"]]

    split = len(per_panel) // 2

    def combine(counters):
        result = Counter({0: 1})
        for counter in counters:
            next_result = Counter()
            if len(result) * len(counter) > 1_000_000:
                return None
            for left, left_count in result.items():
                for right, right_count in counter.items():
                    next_result[left + right] += left_count * right_count
            result = next_result
        return result

    left = combine(per_panel[:split])
    right = combine(per_panel[split:])
    if left is None or right is None:
        return None
    return sum(count * right[inst["scale"] - subtotal] for subtotal, count in left.items())


def canonical_key(inst):
    """Exact normal form under panel, band, and within-band row reorderings."""
    canonical_panels = []
    for panel in inst["panels"]:
        canonical_bands = []
        for band in panel:
            canonical_bands.append(tuple(sorted(tuple(row) for row in band)))
        canonical_panels.append(tuple(sorted(canonical_bands)))
    normal = {
        "n": inst["n"],
        "panels": tuple(sorted(canonical_panels)),
    }
    return hashlib.sha256(
        json.dumps(normal, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params):
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 18))
    bands_per_panel = int(current.get("bands_per_panel", 1))
    # First crowd the same 18 missing digits into larger panels: the witness is
    # unchanged while the standard panel language grows sharply.
    if n == 18 and bands_per_panel < 6:
        return {"n": 18, "bands_per_panel": 6}
    # The next supported level has eight bands.  Even with the same one-hole
    # format its honest public compact route needs at least 391 operations,
    # beyond G9(c); that is an effort-format bound, not evidence of easiness.
    return "cap_bound"


def _reference_solve(inst):
    """Mechanical exact panel enumeration; does not use balanced-band structure."""
    if len(inst["panels"]) != 2:
        return None, 0
    scale = inst["scale"]
    operations = 0
    first = {}
    rows0 = len(_panel_rows(inst["panels"][0]))
    for subtotal, supplied in _panel_candidates(inst["panels"][0], scale):
        first.setdefault(subtotal, supplied)
        # Per row: multiply/add the two decimal digits, exact-divide the
        # common scale, multiply by the numerator, and add into the subtotal.
        operations += 5 * rows0 - 1
    rows1 = len(_panel_rows(inst["panels"][1]))
    for subtotal, supplied in _panel_candidates(inst["panels"][1], scale):
        operations += 5 * rows1 + 1  # row arithmetic, complement, hash probe
        complement = scale - subtotal
        if complement in first:
            return list(first[complement]) + list(supplied), operations
    return None, operations


def _compact_solve(inst):
    """Recognize the public balanced-band and unit-fraction decomposition."""
    scale = inst["scale"]
    band_options = []
    operations = 0
    for panel in inst["panels"]:
        for band in panel:
            fixed = {value for row in band for value in row if value}
            missing = [digit for digit in range(1, 10) if digit not in fixed]
            if len(missing) != 3:
                return None, operations

            # One x, one y, and one z hole occur in every generated band.
            # Precompute the nine scaled contributions from public data.  The
            # numerator-hole row costs 6 exact operations and each denominator-
            # hole row costs 12: 30 total (decimal multiply/add, exact division,
            # and numerator multiplication).
            contribution = []
            for row in band:
                contribution.append(
                    {digit: _scaled_term(row, digit, scale) for digit in missing}
                )
            operations += 30
            options = []
            for supplied in itertools.permutations(missing):
                subtotal = sum(
                    contribution[index][digit]
                    for index, digit in enumerate(supplied)
                )
                # Two additions plus one exact divisibility test recognize a
                # unit fraction from the public scaled subtotal.  No private
                # list of allowed template denominators is consulted.
                operations += 3
                if subtotal > 0 and scale % subtotal == 0:
                    options.append((subtotal, supplied))
            if not options:
                return None, operations
            band_options.append(options)

    for choice in itertools.product(*band_options):
        operations += max(0, len(choice) - 1)
        if sum(item[0] for item in choice) != scale:
            continue
        answer = [digit for item in choice for digit in item[1]]
        if verify(inst, answer)[0]:
            return answer, operations
    return None, operations


def _attack_candidates(inst):
    """Return three deterministic no-tool-style candidates."""
    scale = inst["scale"]
    panels = len(inst["panels"])
    nearest_visible = []
    equal_panel = []
    for panel in inst["panels"]:
        rows = _panel_rows(panel)
        best_outlier = None
        best_greedy = None
        for subtotal, supplied in _panel_candidates(panel, scale):
            score = sum(
                abs(2 * digit - sum(value for value in row if value))
                for row, digit in zip(rows, supplied)
            )
            item = (score, supplied)
            if best_outlier is None or item < best_outlier:
                best_outlier = item
            item = (abs(subtotal * panels - scale), supplied)
            if best_greedy is None or item < best_greedy:
                best_greedy = item
        nearest_visible.extend(best_outlier[1])
        equal_panel.extend(best_greedy[1])

    # A plausible in-context shortcut notices balanced bands but assumes the
    # bands contribute equally.  Shipping deliberately mixes 1/2 and 1/10.
    n_bands = inst["n"] // 3
    equal_band = []
    for panel in inst["panels"]:
        for band in panel:
            fixed = {value for row in band for value in row if value}
            missing = [digit for digit in range(1, 10) if digit not in fixed]
            best = None
            for supplied in itertools.permutations(missing):
                subtotal = sum(
                    _scaled_term(row, digit, scale)
                    for row, digit in zip(band, supplied)
                )
                item = (abs(subtotal * n_bands - scale), supplied)
                if best is None or item < best:
                    best = item
            equal_band.extend(best[1])
    return nearest_visible, equal_panel, equal_band


def _transform_instance(inst, rng, modes):
    nested = []
    offset = 0
    for panel in inst["panels"]:
        answer_panel = []
        for _band in panel:
            answer_panel.append(inst["answer"][offset : offset + 3])
            offset += 3
        nested.append(answer_panel)

    packed_panels = []
    for panel, answer_panel in zip(inst["panels"], nested):
        packed_bands = []
        for band, answer_band in zip(panel, answer_panel):
            packed_rows = list(zip([row[:] for row in band], answer_band))
            if "rows" in modes:
                rng.shuffle(packed_rows)
            packed_bands.append(packed_rows)
        if "bands" in modes:
            rng.shuffle(packed_bands)
        packed_panels.append(packed_bands)
    if "panels" in modes:
        rng.shuffle(packed_panels)

    panels = []
    answer = []
    for packed_panel in packed_panels:
        panel = []
        for packed_band in packed_panel:
            panel.append([row for row, _ in packed_band])
            answer.extend(digit for _, digit in packed_band)
        panels.append(panel)
    return {
        "n": inst["n"],
        "bands_per_panel": inst["bands_per_panel"],
        "panels": panels,
        "scale": _common_scale(panels),
        "answer": answer,
    }


# Filled only from scored calls in the script-owned transcripts.  The bare run
# reached the shipping preset before the OpenRouter key exhausted its total
# quota; its two completed calls are evidence, but not the three calls required
# for a hardened verdict.  The two G9 comparison arms therefore remain unrun.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 2},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not run: bare panel incomplete after quota exhaustion",
}


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset, three independent seeds, plus JSON-native answers.
    failures = []
    identity_checks = 0
    for denominator, templates in _TEMPLATES.items():
        for template in templates:
            identity_checks += 1
            digits = sorted(value for row in template for value in row)
            if digits != list(range(1, 10)):
                failures.append(["template", denominator, "digits are not 1..9"])
            if _identity_sum(template) != (1, denominator):
                failures.append(["template", denominator, "wrong exact subtotal"])
    for blocks, decomposition in _DECOMPOSITIONS.items():
        identity_checks += 1
        numerator, denominator = 0, 1
        for unit_denominator in decomposition:
            numerator = numerator * unit_denominator + denominator
            denominator *= unit_denominator
            divisor = math.gcd(numerator, denominator)
            numerator //= divisor
            denominator //= divisor
        if len(decomposition) != blocks or (numerator, denominator) != (1, 1):
            failures.append(["decomposition", blocks, "does not sum exactly to one"])
    json_roundtrips = 0
    attempts = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([name, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == attempts,
        "attempts": attempts,
        "identity_checks": identity_checks,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **shipping)
    answer = inst["answer"][:]
    corruptions = {}
    tests = {
        "empty": [],
        "drop": answer[:-1],
        "out_of_range": [0] + answer[1:],
    }
    duplicate = answer[:]
    for start in range(0, len(answer), 3):
        if duplicate[start] != duplicate[start + 1]:
            duplicate[start + 1] = duplicate[start]
            break
    tests["duplicate"] = duplicate
    swap = None
    for start in range(0, len(answer), 3):
        for i, j in itertools.combinations(range(start, start + 3), 2):
            candidate = answer[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            ok, reason = verify(inst, candidate)
            if not ok and reason.startswith("the completed fractions sum"):
                swap = candidate
                break
        if swap is not None:
            break
    tests["swap_one"] = swap if swap is not None else answer[::-1]
    reasons = []
    for name, candidate in tests.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
    }

    realistic = (
        "I checked the exact digit counts and rational sum.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("not an answer") is None,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    rng = random.Random(0x180700507)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    exact_count = enumerate_all(inst)
    space = search_space(inst)
    exact_density = exact_count / space if exact_count is not None else None
    density_audit = []
    for audit_seed in range(20):
        audit_inst = make_instance(seed=30_000 + audit_seed, **shipping)
        audit_space = search_space(audit_inst)
        audit_count = enumerate_all(audit_inst)
        density_audit.append(
            {
                "seed": 30_000 + audit_seed,
                "valid_answers": audit_count,
                "candidate_count": audit_space,
                "exact_probability": audit_count / audit_space,
            }
        )
    max_audit_density = max(row["exact_probability"] for row in density_audit)
    report["G4_guess_resistance"] = {
        "pass": exact_density is not None
        and exact_density < 1e-6
        and max_audit_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_valid_answers": exact_count,
        "structure_aware_space": space,
        "exact_probability": exact_density,
        "audited_shipping_seeds": len(density_audit),
        "audited_valid_answer_range": [
            min(row["valid_answers"] for row in density_audit),
            max(row["valid_answers"] for row in density_audit),
        ],
        "maximum_audited_exact_probability": max_audit_density,
        "sampler": (
            "uniform panel digit-count completions conditioned on three "
            "distinct supplied digits per displayed band"
        ),
    }

    start = time.perf_counter()
    reference_answer, reference_operations = _reference_solve(inst)
    reference_wall = time.perf_counter() - start
    report["G5_density_and_baseline"] = {
        "pass": exact_count is not None
        and exact_density < 1e-6
        and reference_answer is not None
        and verify(inst, reference_answer)[0],
        "shipping_exact_solution_count": exact_count,
        "shipping_candidate_count": space,
        "shipping_exact_solution_fraction": exact_density,
        "shipping_sample_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "audited_shipping_seeds": len(density_audit),
        "maximum_audited_solution_fraction": max_audit_density,
        "baseline_name": "exact panel meet-in-the-middle",
        "baseline_operations": reference_operations,
        "baseline_wall_seconds": round(reference_wall, 6),
    }

    attack_names = (
        "outlier_nearest_visible_digits",
        "greedy_equal_panel_share",
        "random_restart_4096",
        "in_context_equal_band_share",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_operations_all = []
    reference_walls = []
    compact_operations_all = []
    compact_walls = []
    for seed in range(8):
        adversary_inst = make_instance(seed=10_000 + seed, **shipping)
        candidates = _attack_candidates(adversary_inst)
        if verify(adversary_inst, candidates[0])[0]:
            attack_successes[attack_names[0]] += 1
        if verify(adversary_inst, candidates[1])[0]:
            attack_successes[attack_names[1]] += 1
        if verify(adversary_inst, candidates[2])[0]:
            attack_successes[attack_names[3]] += 1

        restart_rng = random.Random(0xBAD5EED ^ seed)
        for _ in range(4096):
            if verify(
                adversary_inst, random_candidate(adversary_inst, restart_rng)
            )[0]:
                attack_successes[attack_names[2]] += 1
                break

        start = time.perf_counter()
        solved, operations = _reference_solve(adversary_inst)
        reference_walls.append(time.perf_counter() - start)
        reference_operations_all.append(operations)
        if solved is None or not verify(adversary_inst, solved)[0]:
            failures.append(["reference", seed, "did not solve"])

        start = time.perf_counter()
        solved, operations = _compact_solve(adversary_inst)
        compact_walls.append(time.perf_counter() - start)
        compact_operations_all.append(operations)
        if solved is None or not verify(adversary_inst, solved)[0]:
            failures.append(["compact", seed, "did not solve"])

    attacks = {
        name: {"successes": attack_successes[name], "attempts": 8}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": not failures and all(v == 0 for v in attack_successes.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact panel meet-in-the-middle",
            "complexity": (
                "O(A*n) for the two shipping panels after enumerating A "
                "structure-valid assignments per panel"
            ),
            "median_wall_clock_sec": round(statistics.median(reference_walls), 6),
            "median_operations": int(statistics.median(reference_operations_all)),
            "max_operations": max(reference_operations_all),
            "operations": int(statistics.median(reference_operations_all)),
            "operation_definition": (
                "decimal digit multiply/add, exact scale division, numerator "
                "multiplication, subtotal addition, complement, and hash probe"
            ),
            "solves": "8/8, as expected",
        },
        "compact_route": {
            "name": "balanced three-row unit-fraction decomposition",
            "complexity": "O(n) with six local permutations per band",
            "median_wall_clock_sec": round(statistics.median(compact_walls), 6),
            "median_operations": int(statistics.median(compact_operations_all)),
            "max_operations": max(compact_operations_all),
            "operation_definition": (
                "decimal concatenations, exact divisions/multiplications, and "
                "scaled-integer additions after the structural insight"
            ),
            "solves": "8/8, as expected",
        },
    }

    doubled = make_instance(n=36, seed=314159, bands_per_panel=3)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > space,
        "shipping_fraction_rows": inst["n"],
        "doubled_fraction_rows": doubled["n"],
        "shipping_search_space": space,
        "doubled_search_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    modes = (
        {"rows"},
        {"bands"},
        {"panels"},
        {"rows", "bands", "panels"},
    )
    unrelated = []
    for seed in range(20):
        base = make_instance(seed=20_000 + seed, **shipping)
        base_key = canonical_key(base)
        unrelated.append(base_key)
        for index, mode in enumerate(modes):
            transformed = _transform_instance(
                base, random.Random(seed * 17 + index), mode
            )
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                key_failures.append([seed, sorted(mode), "key changed"])
            ok, reason = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                key_failures.append([seed, sorted(mode), reason])
    report["G8_canonical_key"] = {
        "pass": not key_failures and len(set(unrelated)) == len(unrelated),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": len(unrelated),
        "distinct_unrelated_keys": len(set(unrelated)),
        "symmetries": (
            "panel reorder, band reorder within panels, row reorder within "
            "bands, and their composition"
        ),
        "key_basis": "exact sorted normal form of all masked fraction rows",
        "failures": key_failures,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    compact_answer, intended_operations = _compact_solve(inst)
    arms = G9_RESULTS["arms"]
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    difference = None
    if hinted_attempts and placebo_attempts:
        difference = (
            arms["hinted"]["solved"] / hinted_attempts
            - arms["placebo"]["solved"] / placebo_attempts
        )
    report["G9_no_tool_suitability"] = {
        "pass": len(answer_blob) <= 2000
        and len(inst["answer"]) <= 256
        and intended_operations <= 300
        and compact_answer is not None,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": len(inst["answer"]),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
