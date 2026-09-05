"""Verified generator for compressed witnesses to Kingdomino reduction instances.

The source is arXiv:1909.02849, especially Section 3 (the exact K-tiling
rules) and Theorem 1 in Section 5 (the reduction from 4-Partition).  The
generator inverse-samples an exact four-items-per-bin packing.  It then writes
the corresponding Kingdomino instance in the theorem's run-length encoded
gadget language.  The answer is the exact four-items-per-bin packing as an
integer matrix.  A hidden affine normalisation gives a compact route to that
matrix, but is not part of the problem statement.

The generator never searches for a packing or a tiling.  The planted packing,
the packing, and hence the theorem-backed macro tiling are all known before the
shuffled item list is assembled.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:  # This family needs only integers, but keep the repository helper available.
    from gvlib import rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module remains standard-library-only.
    rationals = None


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "run-length encoded sequence of colored and crowned Kingdomino dominoes",
        "four-items-per-bin packing exposed by the paper's item gadgets",
        "m by 4 exact integer packing matrix",
    ],
    "verification_operations": [
        "exact item-id coverage and matrix-shape checks",
        "exact integer quartet sums",
        "exact evaluation of the paper's target-score formula",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, Theorem 1: polynomial many-one reduction from strongly "
        "NP-complete 4-Partition to K-tiling"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Modulo a concealed power of ten, the signed residue rows share one "
        "cyclic gap word whose unique long gap synchronizes the four item bands; "
        "without it one must perform pair-sum matching and exact-cover search."
    ),
    "hardness_basis": (
        "Track B: the standard four-band pair-sum index plus exact-cover search "
        "takes O(m^2+E) exact operations; at the provisional hard preset n=240 "
        "it averages 0.0049 seconds, 7,200 pair additions/lookups and 61 exact-"
        "cover nodes over eight seeds, while the cyclic-gap route uses at most "
        "n+3=243 exact gap/rotation operations."
    ),
    "max_answer_tokens": 300,
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
    "demo": {"n": 8, "modulus": 100, "arc_width": 17, "quotient_total": 12},
    "easy": {
        "n": 96,
        "modulus": 10_000,
        "arc_width": 2_200,
        "quotient_total": 48,
    },
    "medium": {
        "n": 160,
        "modulus": 1_000_000,
        "arc_width": 240_000,
        "quotient_total": 64,
    },
    "hard": {
        "n": 240,
        "modulus": 100_000_000,
        "arc_width": 26_000_000,
        "quotient_total": 80,
    },
}

SHIPPING_DIFFICULTY = "hard"

# G9 scratch copies set this so harden.py runs exactly the shipping rung.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {"easy": dict(DIFFICULTY[SHIPPING_DIFFICULTY])}


STRUCTURAL_HINT = (
    "Modulo a power of ten, the signed residue rows share one cyclic gap word "
    "with a uniquely long gap."
)

PLACEBO_HINT = (
    "The item labels and magnitude bands should be handled consistently when "
    "writing the final groups."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"groups\":[[i1,i2,i3,i4],...]}.  There are exactly "
        "m lexicographically ordered rows; every row is strictly increasing, "
        "uses one item from each of the four forced magnitude bands, and all n "
        "item ids occur once.  Taking the first band as unlabeled bin anchors, "
        "the structure-aware language contains exactly (m!)^3 matrices."
    ),
    "bounds": {
        "rows": "m=n/4",
        "columns": 4,
        "item_id_min": 1,
        "item_id_max": "n",
        "repetitions": 0,
        "items_per_magnitude_band_per_row": 1,
        "candidate_count": "(m!)^3",
    },
}


NOTES = (
    "Section 3 fixes the exact object: dominoes arrive in sequence on an "
    "unbounded Z^2 board; a domino must be placed iff some legal placement "
    "exists; legality requires a same-color edge match or tower adjacency; and "
    "the score is region area times crowns. It also states that a fully "
    "identified placement list is checked by chronological replay in polynomial "
    "time. Section 4 reports brute-force combinatorial explosion only for tiny "
    "examples. Theorem 1 in Section 5 is the hardness result used here: it "
    "multiplies a 4-Partition instance by 28 and constructs guardians, square, "
    "contour, guide, arms, anchors, items, and zippers; its forward proof turns "
    "any exact four-per-bin packing into a target-score K-tiling. The official "
    "5x5/7x7 bounding box is explicitly discarded, and the conclusion leaves "
    "bounded-color hardness open, so this family uses the theorem's unbounded "
    "board and growing colors. A native coordinate replay certificate would be "
    "far over the answer cap. The matrix here is therefore a paper-licensed "
    "compressed packing witness for the reduction, not a claim of native "
    "coordinate-level coverage. Track A is not claimed: a generic pair-sum "
    "index and exact-cover backtracking solve this finite distribution. Generation "
    "samples the two free translations and each quartet before shuffling labels. "
    "Magnitude offsets [1,2,5,17] times a gap force any target-sum quartet to use "
    "one item from every band. Quotient shares are sampled exchangeably, so no "
    "item in a planted quartet has a special magnitude distribution. Same-rank, "
    "reverse-rank, magnitude-rank, and greedy residual heuristics are tested "
    "explicitly; random restarts sample uniformly from the (m!)^3 balanced prior."
)


# Filled from the hardening transcripts after STEP 4 and the two G9 scratch runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 1, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "errors": 0},
    "hinted_verdict": "not_run_budget_bound",
}


_BAND_NAMES = ("A", "B", "C", "D")
_SIGNS = (1, 1, -1, -1)
_OFFSET_WEIGHTS = (1, 2, 5, 17)


def _validate_params(n, modulus, arc_width, quotient_total):
    values = (n, modulus, arc_width, quotient_total)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        raise TypeError("n, modulus, arc_width, and quotient_total must be integers")
    if n < 8 or n % 4:
        raise ValueError("n must be a multiple of four and at least eight")
    if modulus < 20:
        raise ValueError("modulus must be at least 20")
    if not (n // 4 - 1 <= arc_width < modulus // 3):
        raise ValueError("arc_width must fit the tags and be below modulus/3")
    if quotient_total < 4:
        raise ValueError("quotient_total must be at least four")


def _composition4(total, rng):
    """Uniform stars-and-bars composition of total into four labelled parts."""
    bars = sorted(rng.sample(range(total + 3), 3))
    return [
        bars[0],
        bars[1] - bars[0] - 1,
        bars[2] - bars[1] - 1,
        total + 2 - bars[2],
    ]


def _cyclic_gap_anchor(values, modulus):
    """Element after the unique largest cyclic gap, or None if it is tied."""
    ordered = sorted(values)
    if not ordered or len(set(ordered)) != len(ordered):
        return None
    gaps = []
    for i, value in enumerate(ordered):
        nxt = ordered[(i + 1) % len(ordered)]
        if i + 1 == len(ordered):
            nxt += modulus
        gaps.append(nxt - value)
    biggest = max(gaps)
    if gaps.count(biggest) != 1:
        return None
    index = gaps.index(biggest)
    return ordered[(index + 1) % len(ordered)]


def _row_signed_residues(band, modulus):
    sign = band["sign"]
    return sorted((sign * item["size"]) % modulus for item in band["items"])


def _heuristic_shifts_from_rows(rows, modulus, position):
    base = rows[0]
    c2 = (base[position] - rows[2][position]) % modulus
    c3 = (base[position] - rows[3][position]) % modulus
    c1 = (c2 + c3) % modulus
    return (0, c1, c2, c3)


def _simple_shift_vectors_from_rows(rows, modulus):
    return {
        "zero_shift_ansatz": (0, 0, 0, 0),
        "minimum_residue_alignment": _heuristic_shifts_from_rows(
            rows, modulus, 0
        ),
        "maximum_residue_alignment": _heuristic_shifts_from_rows(
            rows, modulus, -1
        ),
        "median_rank_alignment": _heuristic_shifts_from_rows(
            rows, modulus, len(rows[0]) // 2
        ),
    }


def _canonical_groups(groups):
    """Canonical JSON-native matrix for an unordered packing."""
    return {"groups": sorted(sorted(int(item_id) for item_id in group) for group in groups)}


def _domino_program(m, scaled_target, n):
    """Theorem 1's sequence as exact run-length/formula data."""
    return {
        "scale": 28,
        "guardians": [
            [[1, 1], [1, 0]],
            [[2, 0], [2, 0]],
            [[3, 0], [3, 0]],
            [[4, 0], [4, 0]],
        ],
        "square": {"domino": [[1, 0], [1, 0]], "repeat": 18 * m * m - 6},
        "contour_prefix": [
            [[1, 0], [5, 1]],
            [[5, 0], [6, 1]],
            [[6, 0], [7, 1]],
            [[7, 0], [8, 1]],
            [[8, 0], [1, 0]],
            [[8, 0], [1, 0]],
            [[8, 0], [2, 0]],
            [[8, 0], [9, 1]],
        ],
        "contour_nines": {
            "domino": [[9, 0], [9, 0]],
            "repeat": 9 * m - 8,
        },
        "contour_chain": {
            "start": [[9, 0], [10, 1]],
            "rule": "for c=10..3m+11 append [(c,0),(c+1,1)]",
            "end": [[3 * m + 12, 0], [5, 0]],
        },
        "guide": {
            "domino": [[6, 0], [7, 0]],
            "repeat": 18 * m * m + 12 * m,
        },
        "arms": {
            "rule": "for j=0..m append [(10+3j,0),(11+3j,0)]",
            "repeat_each": scaled_target // 4 + 2,
        },
        "anchors": {
            "rule": "for j=0..m-1 append [(12+3j,0),(3m+13,0)] twice"
        },
        "items": {
            "rule": (
                "for item i of scaled size x_i append [(3m+13,0),"
                "(3m+13+i,1)] once, then [(3m+13+i,0),"
                "(3m+13+i,0)] exactly x_i/2-1 times"
            )
        },
        "zippers": {
            "rule": (
                "for j=0..m-1 append [(11+3j,0),(3m+14+n+j,1)] "
                "then [(3m+14+n+j,0),(13+3j,0)]"
            )
        },
    }


def make_instance(n, seed=0, modulus=10_000, arc_width=2_600, quotient_total=80):
    """Inverse-generate a theorem-backed compressed Kingdomino witness.

    First choose a common tag set and two free row translations.  For each tag,
    sample four exchangeable quotient shares whose residue carry is cancelled.
    The resulting four positive sizes sum to one target.  Only after every
    planted quartet is known are item identifiers shuffled and the public rows
    assembled.  No packing or affine map is recovered from the finished data.
    """
    _validate_params(n, modulus, arc_width, quotient_total)
    rng = random.Random(seed)
    m = n // 4

    # A random sparse arc has one provably unique complementary long gap.
    arc_start = rng.randrange(modulus)
    if m == 2:
        positions = [0, arc_width]
    else:
        positions = [0, arc_width]
        positions.extend(rng.sample(range(1, arc_width), m - 2))
    tags = sorted({(arc_start + position) % modulus for position in positions})
    if len(tags) != m:  # impossible under arc_width < modulus, kept as an invariant.
        raise AssertionError("tag construction collided")

    # Sample translations from the exact bounded certificate language.  Reject
    # only the four explicitly audited one-line signatures; this is not a search
    # for the known certificate.
    while True:
        c2 = rng.randrange(modulus)
        c3 = rng.randrange(modulus)
        c1 = (c2 + c3) % modulus
        shifts = (0, c1, c2, c3)
        residue_rows = [
            sorted((tag - shifts[band]) % modulus for tag in tags)
            for band in range(4)
        ]
        guesses = _simple_shift_vectors_from_rows(residue_rows, modulus)
        if all(tuple(candidate) != shifts for candidate in guesses.values()):
            break

    low_span = modulus * (quotient_total + 1)
    band_gap = 8 * low_span
    offsets = [weight * band_gap for weight in _OFFSET_WEIGHTS]
    target = sum(offsets) + modulus * quotient_total

    records = []
    planted_groups = []
    for tag_index, tag in enumerate(tags):
        residues = [
            tag,
            (tag - c1) % modulus,
            (-tag + c2) % modulus,
            (-tag + c3) % modulus,
        ]
        carry = sum(residues) // modulus
        shares = _composition4(quotient_total - carry, rng)
        group = []
        for band in range(4):
            size = offsets[band] + modulus * shares[band] + residues[band]
            record = {
                "id": None,
                "size": size,
                "band": _BAND_NAMES[band],
                "band_index": band,
                "tag_index": tag_index,
            }
            records.append(record)
            group.append(record)
        if sum(item["size"] for item in group) != target:
            raise AssertionError("inverse-generated quartet misses the target")
        planted_groups.append(group)

    labels = list(range(1, n + 1))
    rng.shuffle(labels)
    for record, label in zip(records, labels):
        record["id"] = label

    bands = []
    for band_index, (name, sign) in enumerate(zip(_BAND_NAMES, _SIGNS)):
        items = [record for record in records if record["band_index"] == band_index]
        items.sort(key=lambda item: (sign * item["size"]) % modulus)
        bands.append(
            {
                "name": name,
                "sign": sign,
                "items": [
                    {"id": item["id"], "size": item["size"]} for item in items
                ],
            }
        )

    scaled_target = 28 * target
    score_target = 72 * m * m + 54 * m + (scaled_target // 2) * (3 * m + 1) + 1
    answer = _canonical_groups(
        [[record["id"] for record in group] for group in planted_groups]
    )
    return {
        "paper": "arXiv:1909.02849",
        "problem": "compressed witness for Theorem 1 Kingdomino instances",
        "n": n,
        "m": m,
        "modulus": modulus,
        "target": target,
        "scaled_target": scaled_target,
        "score_target": score_target,
        "band_gap": band_gap,
        "bands": bands,
        "domino_program": _domino_program(m, scaled_target, n),
        "answer": answer,
    }


def _render_band(band):
    pairs = [f'{item["id"]}:{item["size"]}' for item in band["items"]]
    lines = []
    for start in range(0, len(pairs), 8):
        lines.append("  " + "  ".join(pairs[start : start + 8]))
    return "\n".join(lines)


def render(inst):
    """Render the complete, self-contained compressed-witness problem."""
    m = inst["m"]
    n = inst["n"]
    modulus = inst["modulus"]
    lines = [
        "KINGDOMINO REDUCTION — COMPRESSED PACKING WITNESS",
        "",
        "A domino has two unit cells.  A cell is (color,crowns), where crowns is",
        "a nonnegative integer.  Dominoes arrive in the listed order on the",
        "unbounded integer grid.  Starting from a tower at (0,0), an arriving",
        "domino must occupy two unused edge-adjacent cells iff some placement has",
        "one cell edge-adjacent to the tower or to an earlier cell of the same",
        "color; otherwise it is discarded.  A monochromatic edge-connected region",
        "scores (number of cells) times (crowns in the region), and total score is",
        "the sum over regions.",
        "",
        "This instance is the exact run-length gadget of Theorem 1 of the cited",
        "paper.  It encodes a 4-Partition instance: all n items must be split into",
        "m=n/4 unordered groups of exactly four, each summing to K.  The theorem's",
        "forward construction turns such a packing into a K-tiling of score S.",
        "Your answer is that packing as an exact integer matrix; you do not output",
        "the enormous coordinate-by-coordinate placement list.",
        "",
        f"n = {n}",
        f"m = {m}",
        f"K = {inst['target']}",
        f"The theorem uses scaled item sizes x_i=28*a_i and scaled bin size {inst['scaled_target']}.",
        f"Its target Kingdomino score is S = {inst['score_target']}.",
        "",
        "Compressed domino sequence (R^q means q consecutive copies of R):",
        "  guardians: (1*,1),(2,2),(3,3),(4,4)",
        f"  square: (1,1)^{18*m*m-6}",
        "  contour: (1,5*),(5,6*),(6,7*),(7,8*),(8,1),(8,1),",
        f"           (8,2),(8,9*),(9,9)^{9*m-8},(9,10*), then",
        f"           (c,(c+1)*) for c=10,...,{3*m+11}, then ({3*m+12},5)",
        f"  guide: (6,7)^{18*m*m+12*m}",
        f"  arms: for j=0,...,{m}, ({10}+3j,{11}+3j)^{inst['scaled_target']//4+2}",
        f"  anchors: for j=0,...,{m-1}, two copies of ({12}+3j,{3*m+13})",
        "  items: for item i of scaled size x_i, one",
        f"         ({3*m+13},({3*m+13}+i)*) followed by x_i/2-1 copies",
        f"         of ({3*m+13}+i,{3*m+13}+i)",
        f"  zippers: for j=0,...,{m-1}, ({11}+3j,({3*m+14+n}+j)*) then",
        f"           ({3*m+14+n}+j,{13}+3j)",
        "Here * means one crown on that cell; an unstarred cell has zero crowns.",
        "",
        "The original item sizes a_i are below as id:size.  The four displayed",
        "magnitude bands A,B,C,D are forced by the separated size ranges: every",
        "four-item group summing to K contains exactly one item from each band.",
        "Item ids are 1-based and distinct.  The order within a displayed band has",
        "no semantic force and is not part of the certificate.",
        "",
    ]
    for band in inst["bands"]:
        lines.append(f'Band {band["name"]}:')
        lines.append(_render_band(band))
    lines.extend(
        [
            "",
            "Return an m-by-4 integer matrix whose rows are the groups.  Every id",
            "1,...,n must occur exactly once; each row must contain four distinct",
            "ids, one from each displayed band, whose sizes sum exactly to K.",
            "Within every row write ids in strictly increasing order, then sort the",
            "rows lexicographically.  Any packing satisfying these checks is",
            "accepted; no hidden planted answer is compared.",
            "",
            "Give your final answer inside <answer></answer> tags, as a JSON object",
            'with exactly the key "groups". Example for n=8:',
            '<answer>{"groups":[[1,3,5,8],[2,4,6,7]]}</answer>',
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
    """Extract the JSON certificate from tags or a surrounding model response."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    candidates = [matches[-1]] if matches else []
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = candidate.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            pass
        for match in re.finditer(r"\{", cleaned):
            try:
                value, _end = decoder.raw_decode(cleaned[match.start() :])
                return value
            except ValueError:
                continue
    return None


def _validate_answer_shape(inst, answer):
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if set(answer) != {"groups"}:
        return None, 'answer object must contain exactly the key "groups"'
    groups = answer["groups"]
    if not isinstance(groups, list) or len(groups) != inst["m"]:
        return None, f"groups must contain exactly {inst['m']} rows"
    for index, row in enumerate(groups):
        if not isinstance(row, list) or len(row) != 4:
            return None, f"group row {index} must contain exactly four item ids"
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in row):
            return None, f"group row {index} contains a non-integer id"
    flat = [item_id for row in groups for item_id in row]
    if any(item_id < 1 or item_id > inst["n"] for item_id in flat):
        return None, f"every item id must lie in [1,{inst['n']}]"
    if any(row != sorted(row) or len(set(row)) != 4 for row in groups):
        return None, "ids inside every group must be distinct and strictly increasing"
    if groups != sorted(groups):
        return None, "group rows must be in lexicographic order"
    if len(set(flat)) != len(flat):
        return None, "an item id is duplicated across groups"
    if set(flat) != set(range(1, inst["n"] + 1)):
        return None, "the groups do not use every item id exactly once"
    return groups, "ok"


def verify(inst, answer):
    """Check any valid four-per-bin packing without reading ``inst['answer']``."""
    groups, reason = _validate_answer_shape(inst, answer)
    if groups is None:
        return False, reason
    item_data = {}
    for band_index, band in enumerate(inst["bands"]):
        for item in band["items"]:
            item_data[item["id"]] = (item["size"], band_index)
    for row_index, group in enumerate(groups):
        data = [item_data[item_id] for item_id in group]
        if {band for _size, band in data} != {0, 1, 2, 3}:
            return False, f"group row {row_index} does not use one item from each band"
        if sum(size for size, _band in data) != inst["target"]:
            return False, f"group row {row_index} does not sum to K"
    # Recompute the reduction's scalar target, an exact consistency check on the
    # Kingdomino macro instance rather than an appeal to stored answer data.
    m = inst["m"]
    scaled_target = 28 * inst["target"]
    expected_score = 72 * m * m + 54 * m + (scaled_target // 2) * (3 * m + 1) + 1
    if inst["scaled_target"] != scaled_target or inst["score_target"] != expected_score:
        return False, "the compressed Kingdomino score data are inconsistent"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform balanced partition: one item from every forced magnitude band."""
    orders = []
    for band in inst["bands"]:
        ids = [item["id"] for item in band["items"]]
        rng.shuffle(ids)
        orders.append(ids)
    # Fix the first row's permutation as unlabeled bin anchors.  Independent
    # permutations of the other three rows sample each unordered partition once.
    anchors = sorted(orders[0])
    return _canonical_groups(zip(anchors, orders[1], orders[2], orders[3]))


def search_space(inst):
    return math.factorial(inst["m"]) ** 3


def enumerate_all(inst):
    """Brute-force the bounded language only when it has at most 50k members."""
    if search_space(inst) > 50_000:
        return None
    count = 0
    rows = [[item["id"] for item in band["items"]] for band in inst["bands"]]
    anchors = sorted(rows[0])
    permutations = [list(itertools.permutations(row)) for row in rows[1:]]
    for order1, order2, order3 in itertools.product(*permutations):
        candidate = _canonical_groups(zip(anchors, order1, order2, order3))
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    """Key on unlabeled item multisets per semantic magnitude band."""
    payload = {
        "modulus": inst["modulus"],
        "target": inst["target"],
        "bands": [
            sorted(item["size"] for item in band["items"])
            for band in inst["bands"]
        ],
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    """Grow crowding first, then integer range while answer shape stays fixed."""
    current = {key: value for key, value in params.items() if key != "_preset"}
    n = int(current.get("n", 0))
    if n < 252:
        current["n"] = 252
        current["quotient_total"] = max(int(current.get("quotient_total", 80)), 84)
        return current
    modulus = int(current["modulus"])
    if modulus >= 10**18:
        return "cap_bound"
    current["modulus"] = modulus * 100
    current["arc_width"] = int(current["arc_width"]) * 100
    return current


def _groups_from_orders(orders):
    return _canonical_groups(zip(*orders))


def _attack_candidates(inst, seed):
    rows = [[item for item in band["items"]] for band in inst["bands"]]
    same_rank = [[item["id"] for item in row] for row in rows]
    reverse_rank = [
        [item["id"] for item in rows[0]],
        [item["id"] for item in reversed(rows[1])],
        [item["id"] for item in reversed(rows[2])],
        [item["id"] for item in reversed(rows[3])],
    ]
    magnitude_rank = [
        [item["id"] for item in sorted(row, key=lambda item: item["size"])]
        for row in rows
    ]

    # A no-tool greedy: take A in increasing magnitude, choose B nearest to half
    # the target, then the C,D pair nearest to the remaining sum.
    unused = [sorted(row, key=lambda item: item["size"]) for row in rows]
    greedy_groups = []
    for anchor in unused[0]:
        b = min(
            unused[1],
            key=lambda item: abs(anchor["size"] + item["size"] - inst["target"] // 2),
        )
        unused[1].remove(b)
        c, d = min(
            itertools.product(unused[2], unused[3]),
            key=lambda pair: abs(
                anchor["size"] + b["size"] + pair[0]["size"] + pair[1]["size"]
                - inst["target"]
            ),
        )
        unused[2].remove(c)
        unused[3].remove(d)
        greedy_groups.append([anchor["id"], b["id"], c["id"], d["id"]])

    attacks = {
        "same_display_rank": [_groups_from_orders(same_rank)],
        "reverse_nonanchor_ranks": [_groups_from_orders(reverse_rank)],
        "magnitude_rank_alignment": [_groups_from_orders(magnitude_rank)],
        "greedy_residual_pair": [_canonical_groups(greedy_groups)],
    }
    rng = random.Random((seed << 20) ^ 0x190902849)
    attacks["random_restart_256"] = [random_candidate(inst, rng) for _ in range(256)]
    return attacks


def _reference_pair_sum(inst, node_limit=500_000):
    """Standard pair-sum indexing followed by exact-cover backtracking."""
    rows = [band["items"] for band in inst["bands"]]
    left = {}
    pair_operations = 0
    for a in rows[0]:
        for b in rows[1]:
            pair_operations += 1
            left.setdefault(a["size"] + b["size"], []).append((a, b))
    candidates_by_a = {item["id"]: [] for item in rows[0]}
    candidate_quartets = 0
    for c in rows[2]:
        for d in rows[3]:
            pair_operations += 1
            need = inst["target"] - c["size"] - d["size"]
            for a, b in left.get(need, ()):  # exact equality, no approximation
                group = (a["id"], b["id"], c["id"], d["id"])
                candidates_by_a[a["id"]].append(group)
                candidate_quartets += 1

    nodes = 0
    solution = None

    def dfs(remaining_a, used, chosen):
        nonlocal nodes, solution
        nodes += 1
        if nodes > node_limit:
            return False
        if not remaining_a:
            solution = list(chosen)
            return True
        best_a = None
        best_options = None
        for a_id in remaining_a:
            options = [
                group
                for group in candidates_by_a[a_id]
                if all(item_id not in used for item_id in group)
            ]
            if not options:
                return False
            if best_options is None or len(options) < len(best_options):
                best_a, best_options = a_id, options
        next_remaining = [a_id for a_id in remaining_a if a_id != best_a]
        for group in best_options:
            if dfs(next_remaining, used | set(group), chosen + [group]):
                return True
        return False

    dfs(sorted(candidates_by_a), set(), [])
    answer = _canonical_groups(solution) if solution is not None else None
    return answer, {
        "pair_operations": pair_operations,
        "candidate_quartets": candidate_quartets,
        "exact_cover_nodes": nodes,
        "node_limit": node_limit,
    }


def _compact_gap_solve(inst):
    modulus = inst["modulus"]
    ordered_items = []
    anchors = []
    for band in inst["bands"]:
        sign = band["sign"]
        row = sorted(band["items"], key=lambda item: (sign * item["size"]) % modulus)
        residues = [(sign * item["size"]) % modulus for item in row]
        anchor = _cyclic_gap_anchor(residues, modulus)
        if anchor is None:
            return None
        index = residues.index(anchor)
        ordered_items.append(row[index:] + row[:index])
        anchors.append(anchor)
    if any(anchor is None for anchor in anchors):
        return None
    return _canonical_groups(
        [[ordered_items[band][index]["id"] for band in range(4)] for index in range(inst["m"])]
    )


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(child) for child in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(child) for child in value)
    return 1


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    variants = []

    reversed_rows = copy.deepcopy(inst)
    for band in reversed_rows["bands"]:
        band["items"].reverse()
    variants.append((reversed_rows, copy.deepcopy(inst["answer"])))

    reordered = copy.deepcopy(inst)
    for band in reordered["bands"]:
        rng.shuffle(band["items"])
    variants.append((reordered, copy.deepcopy(inst["answer"])))

    relabelled = copy.deepcopy(inst)
    labels = list(range(1, inst["n"] + 1))
    shuffled = list(labels)
    rng.shuffle(shuffled)
    mapping = dict(zip(labels, shuffled))
    for band in relabelled["bands"]:
        for item in band["items"]:
            item["id"] = mapping[item["id"]]
    relabelled_answer = {
        "groups": sorted(
            sorted(mapping[item_id] for item_id in group)
            for group in inst["answer"]["groups"]
        )
    }
    variants.append((relabelled, relabelled_answer))

    composed = copy.deepcopy(relabelled)
    for band in composed["bands"]:
        rng.shuffle(band["items"])
    variants.append((composed, copy.deepcopy(relabelled_answer)))
    return variants


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "construction": (
            "inverse-generated affine rows and exact quartets, followed by the "
            "forward construction of Theorem 1"
        ),
    }

    inst = make_instance(seed=19, **shipping)
    answer = copy.deepcopy(inst["answer"])
    dropped = copy.deepcopy(answer)
    dropped["groups"].pop()
    swapped = copy.deepcopy(answer)
    swapped["groups"][0][0], swapped["groups"][0][1] = (
        swapped["groups"][0][1],
        swapped["groups"][0][0],
    )
    duplicated = copy.deepcopy(answer)
    duplicated["groups"][1][0] = duplicated["groups"][0][0]
    duplicated["groups"][1].sort()
    duplicated["groups"].sort()
    out_of_range = copy.deepcopy(answer)
    out_of_range["groups"][0][0] = 0
    out_of_range["groups"][0].sort()
    out_of_range["groups"].sort()
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    model_response = (
        "The hidden signed residue rows share the same cyclic gap word.\n"
        "```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe groups give the exact packing."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x190902849)
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
        "exact_structure_aware_candidate_space": search_space(inst),
        "planted_solution_density_lower_bound": 1 / search_space(inst),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = list(_attack_candidates(inst, 0))
    successes = {name: 0 for name in attack_names}
    attempts = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_pair_operations = 0
    reference_candidates = 0
    reference_nodes = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        for name, candidates in _attack_candidates(trial, seed).items():
            started = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates)
            attack_seconds[name] += time.perf_counter() - started
            successes[name] += int(won)
            attempts[name] += 1

        started = time.perf_counter()
        recovered, counts = _reference_pair_sum(trial)
        reference_seconds += time.perf_counter() - started
        reference_pair_operations += counts["pair_operations"]
        reference_candidates += counts["candidate_quartets"]
        reference_nodes += counts["exact_cover_nodes"]
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        compact = _compact_gap_solve(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": attempts[name],
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "four-band pair-sum index plus exact-cover backtracking",
        "complexity": "O(m^2 + E) pair indexing plus output-sensitive exact cover",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_pair_operations // 8,
        "candidate_quartets": reference_candidates // 8,
        "exact_cover_nodes": reference_nodes // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "unique cyclic-gap alignment",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": inst["n"] + 3,
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_solution_density": guess_fraction,
        "shipping_candidate_space": search_space(inst),
        "construction_known_solution_lower_bound": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_reference_wall_clock_sec": reference["wall_clock_sec"],
        "baseline_reference_pair_operations": reference["operations"],
        "baseline_reference_candidate_quartets": reference["candidate_quartets"],
        "baseline_reference_exact_cover_nodes": reference["exact_cover_nodes"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_params["quotient_total"] *= 2
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
        "answer_atoms_shipping": _atomic_elements(inst["answer"]),
        "answer_atoms_doubled": _atomic_elements(doubled["answer"]),
        "pair_index_operations_shipping": 2 * (inst["m"] ** 2),
        "pair_index_operations_doubled": 2 * (doubled["m"] ** 2),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        original_key = canonical_key(original)
        for transformed, carried_answer in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(original_key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, carried_answer)[0])
        unrelated_keys.append(original_key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 80
        and real_transform_count == 80
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariance_attempts": 80,
        "real_transformations_verified": real_transform_count,
        "real_transformation_attempts": 80,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "reverse each semantically unordered item row",
            "independently reorder every item row",
            "arbitrarily relabel every item id",
            "compose arbitrary relabelling with row reordering",
        ],
    }

    answer_blobs = []
    for seed in range(20):
        sample = make_instance(seed=seed, **shipping)
        answer_blobs.append(json.dumps(sample["answer"], separators=(",", ":")))
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    worst_chars = max(map(len, answer_blobs))
    worst_tokens = math.ceil(worst_chars / 4)
    answer_elements = _atomic_elements(inst["answer"])
    intended_operations = inst["n"] + 3
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    within_caps = (
        len(encoded) <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and math.ceil(worst_chars / 4) <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(encoded),
        "answer_tokens": math.ceil(len(encoded) / 4),
        "worst_case_answer_chars_measured": worst_chars,
        "worst_case_answer_tokens_measured": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
