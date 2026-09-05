"""Exact seminormalized-Hadamard completion tasks for arXiv:1606.09368.

The instance is a partial system of mutually orthogonal balanced sign columns.
The requested witness is one more balanced sign column, with prescribed
coordinates. Generation starts from a Sylvester matrix and carries the answer
through equivalence operations; it never solves the displayed system.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter
from typing import Any


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This finite +/-1 family has a standard-library fallback.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "seminormalized Hadamard vectors",
        "partial orthogonal +/-1 column system",
        "balanced +/-1 completion vector with prescribed coordinates",
    ],
    "verification_operations": [
        "exact +/-1 alphabet comparison",
        "exact integer balance check",
        "exact prescribed-coordinate comparison",
        "exact integer inner products",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "View the signed columns as Walsh characters: the absent affine "
        "frequency block turns the pins into a quotient truth table, whereas "
        "a solver missing that structure faces a dense exact system."
    ),
    "hardness_basis": (
        "Track B: exact modular Gauss-Jordan elimination solves the pinned "
        "orthogonality system in O(n^3); at shipping n=128 it solved 8/8 at "
        "a measured mean 1,018,271 modular operations and 0.055743 seconds "
        "(maximum 1,093,837 operations), while the Walsh-block route uses 64 "
        "exact sign negations."
    ),
    "max_answer_tokens": 161,
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


DIFFICULTY = {"hard": {"n": 128, "block_bits": 5}}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The omitted identifiers are an affine Walsh-frequency block whose quotient values are the pins."
)
PLACEBO_HINT = (
    "The binary identifiers and coordinate tags should be tracked carefully alongside all the pins."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n signs in {-1,+1}, in output-label order, "
        "matching every prescribed coordinate and containing n/2 signs of "
        "each kind."
    ),
    "bounds": {
        "max_length": 256,
        "alphabet_size": 2,
        "shipping_pinned_entries": 32,
        "shipping_free_entries": 96,
        "shipping_required_free_positive_entries": 48,
    },
}

NOTES = r"""
Step 0 and the exact problem. Definition 1 and Equation (1) define a Hadamard
matrix by +/-1 entries and H^T H=mI. The paragraph after Lemma 1 fixes the
paper's seminormalization convention: the first column is all +1. Definition 9
defines an SH vector as a length-4k sign vector with 2k entries of each sign;
Lemma 10 proves its orthogonality to the unity column. Definition 11 and
Section 3 build a QSH matrix from distinct SH columns, and Algorithms 1 and 2
search for columns that make it orthogonal. This module poses one such native
column-extension stage, with prescribed entries to select one completion.

What produces the certificate. Equation (3) and Lemma 1 give Sylvester's
Kronecker construction at powers of two. Its columns are the Walsh characters
chi_y(x)=(-1)^<x,y>. Generation omits one affine frequency block a+W, retains
all other columns, and chooses a balanced Boolean quotient function g. The
carried answer is chi_a(x)g(x mod W). Character orthogonality proves that it is
perpendicular to every retained column, and its prescribed coordinates equal
g. Row relabelling, column reordering, and independent column negations carry
the certificate. No displayed system is solved.

Why Track B. This is not a Track-A claim. The paper gives the explicit
Sylvester construction, Algorithm 1 exhaustive search, Algorithm 2 random
vector selection, and Section 3.3 simulated annealing. For these pinned
instances, a computer can solve the n exact linear equations: selftest runs
modular Gauss-Jordan elimination, verifies the unique +/-1 result over the
integers, and records operations and time. The compact route is the Walsh
change of variables. The missing identifiers form an affine block; the pins
are one quotient truth table; other coordinate blocks are copies or negated
copies. At n=128 this needs 64 sign negations after recognizing the structure.

Easy cases and defenses. Merely asking for a Hadamard matrix of power-of-two
order fails H because Equation (3) writes it down directly. An earlier draft
omitted arbitrary individual Walsh columns; a random Walsh-frequency attack
then solved 89/1000 shipping instances in one guess and 975/1000 with 32
guesses. The affine-block construction replaces that weak plant. Its balanced
quotient table has C(32,16)=601080390 possibilities at shipping size, and all
signed single-character tables are excluded. The panel tests row outliers,
residual greedy, balanced RVS restarts, repaired visible columns and products,
a single-character ansatz, and unmodulated repetition of the pins.
""".strip()


# Filled only from script-owned hardening runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "errors": 0},
    "hinted_verdict": "not_yet_run",
}

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_REFERENCE_PRIME = 1_000_003


def _validate_params(n: int, block_bits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 8 or n > 512 or n & (n - 1):
        raise ValueError("n must be a power of two in 8..512")
    if isinstance(block_bits, bool) or not isinstance(block_bits, int):
        raise ValueError("block_bits must be an integer")
    bits = n.bit_length() - 1
    if block_bits < 1 or block_bits > bits - 2:
        raise ValueError("block_bits must leave at least two high tag bits")


def _character(row_tag: int, frequency: int) -> int:
    return -1 if (row_tag & frequency).bit_count() & 1 else 1


def _is_signed_walsh_table(values: list[int]) -> bool:
    for frequency in range(len(values)):
        base = [_character(row, frequency) for row in range(len(values))]
        if values == base or values == [-value for value in base]:
            return True
    return False


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Construct and transform a certified partial Sylvester-Hadamard system."""
    unknown = set(params) - {"block_bits"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    block_bits = params.get("block_bits", max(1, n.bit_length() - 3))
    _validate_params(n, block_bits)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    bits = n.bit_length() - 1
    block_size = 1 << block_bits
    high_bits = bits - block_bits
    # Missing frequencies are the coset a+W, where W varies over low bits.
    absent_base = 1 << (block_bits + rng.randrange(high_bits))
    missing = set(range(absent_base, absent_base + block_size))
    column_ids = [value for value in range(n) if value not in missing]
    rng.shuffle(column_ids)
    column_signs = {
        value: (1 if value == 0 else rng.choice((-1, 1)))
        for value in column_ids
    }

    # Sample g from the same bounded balanced language on every non-demo seed.
    while True:
        positive = set(rng.sample(range(block_size), block_size // 2))
        quotient = [1 if index in positive else -1 for index in range(block_size)]
        if block_size <= 2 or not _is_signed_walsh_table(quotient):
            break

    tags = list(range(n))
    rng.shuffle(tags)
    rows = []
    anchors = []
    answer = [0] * n
    for label, tag in enumerate(tags):
        rows.append({
            "label": label,
            "tag": tag,
            "signs": [
                column_signs[frequency] * _character(tag, frequency)
                for frequency in column_ids
            ],
        })
        answer[label] = quotient[tag & (block_size - 1)] * _character(
            tag, absent_base
        )
        if tag < block_size:
            anchors.append([label, quotient[tag]])
    rng.shuffle(rows)
    anchors.sort()
    return {
        "family": "pinned_seminormalized_hadamard_completion",
        "n": n,
        "label_bits": bits,
        "block_bits": block_bits,
        "column_ids": column_ids,
        "rows": rows,
        "anchors": anchors,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the entire exact task, including every convention and datum."""
    n = inst["n"]
    bits = inst["label_bits"]
    width = len(inst["column_ids"])
    block_size = 1 << inst["block_bits"]
    header = " ".join(f"{value:0{bits}b}" for value in inst["column_ids"])
    pins = " ".join(
        f"{label:0{bits}b}={'+' if value == 1 else '-'}"
        for label, value in inst["anchors"]
    )
    lines = [
        "PINNED SEMINORMALIZED HADAMARD-VECTOR COMPLETION",
        "",
        "A sign vector has entries in {+1,-1}. Its exact integer inner product",
        "with another sign vector is the sum of coordinatewise products. An SH",
        "(seminormalized Hadamard) vector of even length n contains n/2 entries",
        "of each sign; equivalently, it is orthogonal to the all-+1 column.",
        "",
        f"Here n={n}. The table contains {width} distinct, pairwise-orthogonal",
        "sign columns, including the unity column. Rows and columns are shown in",
        "arbitrary order. Each row has a unique output label and a distinct",
        f"{bits}-bit auxiliary tag. Each column has a distinct {bits}-bit",
        "identifier. Tags and identifiers are metadata; validity is checked",
        "directly from the displayed signs.",
        "",
        f"Find ANY further SH vector w that (i) is orthogonal to all {width}",
        f"displayed columns and (ii) has the {block_size} prescribed entries",
        "listed below. Return w in increasing integer output-label order",
        "0,1,...,n-1, regardless of display order. The pins fix orientation.",
        "No entry may be omitted; only the integers 1 and -1 are allowed.",
        "",
        "Column identifiers, in displayed left-to-right order:",
        header,
        "",
        "Prescribed output-label signs (+ means 1, - means -1):",
        pins,
        "",
        "Each table row is: output_label : auxiliary_tag | displayed signs.",
    ]
    for row in inst["rows"]:
        sign_text = "".join("+" if value == 1 else "-" for value in row["signs"])
        lines.append(
            f"{row['label']:0{bits}b} : {row['tag']:0{bits}b} | {sign_text}"
        )
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as a JSON list of",
        f"exactly {n} integers in increasing output-label order.",
        "Example format: <answer>[1, -1, 1, -1]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON list, tolerating prose and a code fence."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _public_data(inst: dict) -> tuple[list[list[int]], dict[int, int]] | None:
    cached = inst.get("_public_data_cache")
    if isinstance(cached, tuple):
        return cached
    try:
        n, rows, ids = inst["n"], inst["rows"], inst["column_ids"]
        anchors_raw = inst["anchors"]
        if (not isinstance(rows, list) or len(rows) != n
                or not isinstance(ids, list) or not ids or len(set(ids)) != len(ids)
                or any(isinstance(x, bool) or not isinstance(x, int)
                       or not 0 <= x < n for x in ids)):
            return None
        by_label = {}
        seen_tags = set()
        for row in rows:
            if not isinstance(row, dict):
                return None
            label, tag, signs = row.get("label"), row.get("tag"), row.get("signs")
            if (isinstance(label, bool) or not isinstance(label, int)
                    or not 0 <= label < n or label in by_label
                    or isinstance(tag, bool) or not isinstance(tag, int)
                    or not 0 <= tag < n or tag in seen_tags
                    or not isinstance(signs, list) or len(signs) != len(ids)
                    or any(isinstance(v, bool) or not isinstance(v, int)
                           or v not in (-1, 1) for v in signs)):
                return None
            by_label[label] = signs
            seen_tags.add(tag)
        if len(by_label) != n or not isinstance(anchors_raw, list):
            return None
        anchors = {}
        for pair in anchors_raw:
            if (not isinstance(pair, list) or len(pair) != 2
                    or isinstance(pair[0], bool) or not isinstance(pair[0], int)
                    or not 0 <= pair[0] < n or pair[0] in anchors
                    or isinstance(pair[1], bool) or not isinstance(pair[1], int)
                    or pair[1] not in (-1, 1)):
                return None
            anchors[pair[0]] = pair[1]
        columns = [
            [by_label[label][column] for label in range(n)]
            for column in range(len(ids))
        ]
        result = (columns, anchors)
        inst["_public_data_cache"] = result
        return result
    except (KeyError, TypeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify from public instance data only; never inspect inst['answer']."""
    n = inst.get("n")
    if not isinstance(n, int):
        return False, "instance size is malformed"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"answer is too short: expected {n} entries"
    if len(answer) > n:
        return False, f"answer is too long: expected {n} entries"
    for index, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {index} is not an integer"
        if value not in (-1, 1):
            return False, f"entry {index} is outside the +/-1 alphabet"
    if sum(answer) != 0:
        return False, "candidate is not balanced: it must contain n/2 of each sign"
    public = _public_data(inst)
    if public is None:
        return False, "instance data is malformed"
    columns, anchors = public
    for label, required in anchors.items():
        if answer[label] != required:
            return False, f"candidate violates prescribed sign at output label {label}"
    candidate_mask = sum((value == 1) << i for i, value in enumerate(answer))
    masks = inst.get("_column_masks_cache")
    if not isinstance(masks, list):
        masks = [sum((v == 1) << i for i, v in enumerate(column))
                 for column in columns]
        inst["_column_masks_cache"] = masks
    for column_index, mask in enumerate(masks):
        dot = n - 2 * (candidate_mask ^ mask).bit_count()
        if dot:
            return False, (
                f"candidate is not orthogonal to displayed column {column_index}: "
                f"inner product {dot}"
            )
    return True, "ok"


def _candidate_shape(inst: dict) -> tuple[list[int], int, dict[int, int]]:
    public = _public_data(inst)
    if public is None:
        raise ValueError("malformed instance")
    anchors = public[1]
    free = [label for label in range(inst["n"]) if label not in anchors]
    required = inst["n"] // 2 - sum(value == 1 for value in anchors.values())
    return free, required, anchors


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform sample from balanced sign vectors satisfying every public pin."""
    free, required, anchors = _candidate_shape(inst)
    positives = set(rng.sample(free, required))
    return [anchors[i] if i in anchors else (1 if i in positives else -1)
            for i in range(inst["n"])]


def search_space(inst: dict) -> int | None:
    """Exact size of the pinned-and-balanced candidate language."""
    free, required, _ = _candidate_shape(inst)
    return math.comb(len(free), required)


def enumerate_all(inst: dict) -> int | None:
    """Count valid witnesses exactly when the candidate language is small."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    free, required, anchors = _candidate_shape(inst)
    count = 0
    for selected in itertools.combinations(free, required):
        positives = set(selected)
        candidate = [anchors[i] if i in anchors else (1 if i in positives else -1)
                     for i in range(inst["n"])]
        count += verify(inst, candidate)[0]
    return count


def _canonical_quotient_table(inst: dict) -> tuple[int, ...] | None:
    """Canonicalize the pinned truth table under tested affine tag symmetries."""
    try:
        bits = inst["label_bits"]
        tags = _row_tags(inst)
        pinned = {tags[label]: value for label, value in inst["anchors"]}
        active = [bit for bit in range(bits)
                  if len({(tag >> bit) & 1 for tag in pinned}) == 2]
        size = len(pinned)
        if size != 1 << len(active):
            return None
        fixed = next(iter(pinned))
        for bit in active:
            fixed &= ~(1 << bit)
        table = []
        for compressed in range(size):
            tag = fixed
            for index, bit in enumerate(active):
                if (compressed >> index) & 1:
                    tag |= 1 << bit
            if tag not in pinned:
                return None
            table.append(pinned[tag])
        best = None
        q = len(active)
        for permutation in itertools.permutations(range(q)):
            for shift in range(size):
                candidate = []
                for value in range(size):
                    source = shift
                    for new_bit, old_bit in enumerate(permutation):
                        if (value >> new_bit) & 1:
                            source ^= 1 << old_bit
                    candidate.append(table[source])
                normal = tuple(candidate)
                negated = tuple(-entry for entry in candidate)
                form = min(normal, negated)
                if best is None or form < best:
                    best = form
        return best
    except (KeyError, TypeError):
        return None


def canonical_key(inst: dict) -> str:
    """Strong colored weighted-row-graph invariant of the public system."""
    public = _public_data(inst)
    if public is None:
        payload: object = {"malformed": True, "n": inst.get("n")}
    else:
        columns, anchors = public
        n, width = inst["n"], len(columns)
        row_masks = [sum((columns[c][r] == 1) << c for c in range(width))
                     for r in range(n)]
        weights = [[0] * n for _ in range(n)]
        for left in range(n):
            for right in range(left + 1, n):
                value = width - 2 * (row_masks[left] ^ row_masks[right]).bit_count()
                weights[left][right] = weights[right][left] = value
        colors = [anchors.get(row, 0) + 1 for row in range(n)]
        for _ in range(8):
            signatures = [
                (colors[row], tuple(sorted(
                    (weights[row][other], colors[other])
                    for other in range(n) if other != row
                )))
                for row in range(n)
            ]
            palette = {sig: idx for idx, sig in enumerate(sorted(set(signatures)))}
            refined = [palette[sig] for sig in signatures]
            if refined == colors:
                break
            colors = refined
        edge_hist = Counter()
        for left in range(n):
            for right in range(left + 1, n):
                edge_hist[(min(colors[left], colors[right]),
                           max(colors[left], colors[right]),
                           weights[left][right])] += 1
        payload = {
            "n": n,
            "width": width,
            "color_sizes": sorted(Counter(colors).items()),
            "edges": sorted(edge_hist.items()),
            "quotient": _canonical_quotient_table(inst),
        }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Double the ambient order until the shipping answer cap binds."""
    n = int(params["n"])
    block_bits = int(params.get("block_bits", max(1, n.bit_length() - 3)))
    if n >= 256:
        return "cap_bound"
    return {"n": 2 * n, "block_bits": block_bits + 1}


# Compact decoder, exact reference algorithm, and construction-aware attacks.

def _row_tags(inst: dict) -> dict[int, int]:
    return {row["label"]: row["tag"] for row in inst["rows"]}


def _compact_completion(inst: dict) -> tuple[list[int] | None, int]:
    n = inst["n"]
    block_size = 1 << inst["block_bits"]
    missing = set(range(n)) - set(inst["column_ids"])
    if len(missing) != block_size:
        return None, 0
    absent_base = min(missing)
    if missing != set(range(absent_base, absent_base + block_size)):
        return None, 0
    tags = _row_tags(inst)
    by_tag = {tag: label for label, tag in tags.items()}
    anchors = dict(inst["anchors"])
    quotient = []
    for low in range(block_size):
        label = by_tag.get(low)
        if label is None or label not in anchors:
            return None, 0
        quotient.append(anchors[label])
    answer = [0] * n
    negations = 0
    for label, tag in tags.items():
        value = quotient[tag & (block_size - 1)]
        if _character(tag, absent_base) == -1:
            value = -value
            negations += 1
        answer[label] = value
    return answer, negations


def _reference_completion(inst: dict) -> tuple[list[int] | None, int]:
    """Solve the square public system by exact modular Gauss-Jordan."""
    public = _public_data(inst)
    if public is None:
        return None, 0
    columns, anchors = public
    n, modulus = inst["n"], _REFERENCE_PRIME
    matrix = [[columns[c][r] % modulus for r in range(n)] + [0]
              for c in range(len(columns))]
    for label, value in sorted(anchors.items()):
        equation = [0] * (n + 1)
        equation[label] = 1
        equation[n] = value % modulus
        matrix.append(equation)
    if len(matrix) != n:
        return None, 0
    operations = 0
    for pivot_col in range(n):
        pivot_row = next((r for r in range(pivot_col, n)
                          if matrix[r][pivot_col]), None)
        if pivot_row is None:
            return None, operations
        if pivot_row != pivot_col:
            matrix[pivot_col], matrix[pivot_row] = matrix[pivot_row], matrix[pivot_col]
        pivot = matrix[pivot_col][pivot_col]
        if pivot != 1:
            inverse = pow(pivot, modulus - 2, modulus)
            operations += 3 * modulus.bit_length()
            for col in range(pivot_col, n + 1):
                matrix[pivot_col][col] = matrix[pivot_col][col] * inverse % modulus
                operations += 1
        for row in range(n):
            if row == pivot_col:
                continue
            factor = matrix[row][pivot_col]
            if factor:
                for col in range(pivot_col, n + 1):
                    matrix[row][col] = (
                        matrix[row][col] - factor * matrix[pivot_col][col]
                    ) % modulus
                    operations += 2
    residues = [matrix[row][n] for row in range(n)]
    if any(value not in (1, modulus - 1) for value in residues):
        return None, operations
    return [1 if value == 1 else -1 for value in residues], operations


def _repair_from_scores(inst: dict, scores: list[int]) -> list[int]:
    free, required, anchors = _candidate_shape(inst)
    chosen = set(sorted(free, key=lambda i: (scores[i], i))[-required:])
    return [anchors[i] if i in anchors else (1 if i in chosen else -1)
            for i in range(inst["n"])]


def _attack_row_sum_outlier(inst: dict) -> list[int]:
    columns = (_public_data(inst) or ([], {}))[0]
    scores = [sum(column[row] for column in columns) for row in range(inst["n"])]
    return _repair_from_scores(inst, scores)


def _attack_residual_greedy(inst: dict) -> list[int]:
    columns, anchors = _public_data(inst) or ([], {})
    n = inst["n"]
    partial = [0] * len(columns)
    answer = [0] * n
    free, positives_left, _ = _candidate_shape(inst)
    free_left = len(free)
    for label in range(n):
        if label in anchors:
            choice = anchors[label]
        else:
            if positives_left == free_left:
                choice = 1
            elif positives_left == 0:
                choice = -1
            else:
                plus = sum((partial[j] + columns[j][label]) ** 2
                           for j in range(len(columns)))
                minus = sum((partial[j] - columns[j][label]) ** 2
                            for j in range(len(columns)))
                choice = 1 if plus <= minus else -1
            positives_left -= choice == 1
            free_left -= 1
        answer[label] = choice
        for j, column in enumerate(columns):
            partial[j] += choice * column[label]
    return answer


def _attack_copy_visible(inst: dict) -> list[int]:
    column = (_public_data(inst) or ([[]], {}))[0][0]
    return _repair_from_scores(inst, list(column))


def _attack_first_pair_product(inst: dict) -> list[int]:
    columns = (_public_data(inst) or ([], {}))[0]
    scores = [columns[0][r] * columns[1][r] for r in range(inst["n"])]
    return _repair_from_scores(inst, scores)


def _attack_single_missing_character(inst: dict) -> list[int]:
    frequency = min(set(range(inst["n"])) - set(inst["column_ids"]))
    tags = _row_tags(inst)
    scores = [_character(tags[label], frequency) for label in range(inst["n"])]
    return _repair_from_scores(inst, scores)


def _attack_repeat_pins(inst: dict) -> list[int] | None:
    block_size = 1 << inst["block_bits"]
    tags = _row_tags(inst)
    by_tag = {tag: label for label, tag in tags.items()}
    anchors = dict(inst["anchors"])
    quotient = []
    for low in range(block_size):
        label = by_tag.get(low)
        if label is None or label not in anchors:
            return None
        quotient.append(anchors[label])
    return [quotient[tags[label] & (block_size - 1)]
            for label in range(inst["n"])]


def _attack_random_restart(inst: dict, rng: random.Random,
                           restarts: int) -> tuple[list[int] | None, int]:
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


# G8 transformations.

def _copy_public_instance(inst: dict) -> dict:
    return {key: json.loads(json.dumps(value)) for key, value in inst.items()
            if key != "answer" and not key.startswith("_")}


def _reorder_presentation(inst: dict, row_order: list[int] | None = None,
                          column_order: list[int] | None = None) -> dict:
    out = _copy_public_instance(inst)
    if row_order is not None:
        out["rows"] = [out["rows"][index] for index in row_order]
    if column_order is not None:
        out["column_ids"] = [out["column_ids"][index] for index in column_order]
        for row in out["rows"]:
            row["signs"] = [row["signs"][index] for index in column_order]
    return out


def _renumber_output_labels(inst: dict, permutation: list[int]) -> tuple[dict, list[int]]:
    out = _copy_public_instance(inst)
    carried = [0] * inst["n"]
    for row in out["rows"]:
        old = row["label"]
        row["label"] = permutation[old]
        carried[permutation[old]] = inst["answer"][old]
    out["anchors"] = sorted([[permutation[label], value]
                              for label, value in out["anchors"]])
    return out, carried


def _negate_columns(inst: dict, selected: set[int]) -> dict:
    out = _copy_public_instance(inst)
    for row in out["rows"]:
        row["signs"] = [(-value if index in selected else value)
                        for index, value in enumerate(row["signs"])]
    return out


def _permute_bits(value: int, permutation: list[int]) -> int:
    result = 0
    for old, new in enumerate(permutation):
        if (value >> old) & 1:
            result |= 1 << new
    return result


def _rename_tag_basis(inst: dict, permutation: list[int]) -> dict:
    out = _copy_public_instance(inst)
    out["column_ids"] = [_permute_bits(value, permutation)
                         for value in out["column_ids"]]
    for row in out["rows"]:
        row["tag"] = _permute_bits(row["tag"], permutation)
    return out


def _translate_tags(inst: dict, translation: int) -> dict:
    """Translate every row tag; implicit column signs absorb the characters."""
    out = _copy_public_instance(inst)
    for row in out["rows"]:
        row["tag"] ^= translation
    return out


def _find_swap_corruption(inst: dict, answer: list[int]) -> list[int]:
    anchors = set(dict(inst["anchors"]))
    for left in range(len(answer)):
        if left in anchors:
            continue
        for right in range(left + 1, len(answer)):
            if right in anchors or answer[left] == answer[right]:
                continue
            corrupt = list(answer)
            corrupt[left], corrupt[right] = corrupt[right], corrupt[left]
            ok, reason = verify(inst, corrupt)
            if not ok and "not orthogonal" in reason:
                return corrupt
    raise AssertionError("could not build a pin-preserving rejected swap")


def _answer_token_estimate(answer: object) -> int:
    return (len(json.dumps(answer, separators=(",", ":"))) + 1) // 2


def selftest() -> dict:
    """Run every mandatory correctness, density, attack, scaling, and size gate."""
    report: dict[str, Any] = {
        "paper": "arXiv:1606.09368",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            answer = inst["answer"]
            g1_attempts += 1
            ok, reason = verify(inst, answer)
            if not ok:
                g1_failures.append(f"{preset}/seed={seed}: {reason}")
            if json.loads(json.dumps(answer)) != answer:
                g1_failures.append(f"{preset}/seed={seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "attempts": g1_attempts, "failures": g1_failures,
    }

    shipping = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=20260905, **shipping)
    planted = inst["answer"]
    pinned_label = inst["anchors"][0][0]
    pin_corrupt = list(planted)
    pin_corrupt[pinned_label] *= -1
    pin_repair = next(i for i, value in enumerate(pin_corrupt)
                      if i != pinned_label and i not in dict(inst["anchors"])
                      and value == pin_corrupt[pinned_label])
    pin_corrupt[pin_repair] *= -1
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate_one": planted + [planted[-1]],
        "out_of_range": [2] + planted[1:],
        "violates_pin": pin_corrupt,
        "swap_opposite": _find_swap_corruption(inst, planted),
    }
    g2_reasons = {}
    for name, corrupt in corruptions.items():
        accepted, reason = verify(inst, corrupt)
        g2_reasons[name] = "ACCEPTED" if accepted else reason
    g2_pass = ("ACCEPTED" not in g2_reasons.values()
               and len(set(g2_reasons.values())) == len(g2_reasons))
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "rejected": sum(v != "ACCEPTED" for v in g2_reasons.values()),
        "attempts": len(corruptions),
        "distinct_reasons": len(set(g2_reasons.values())),
        "reasons": g2_reasons,
    }

    wrapped = ("The Walsh calculation gives:\n<answer>```json\n"
               + json.dumps(planted) + "\n```</answer>\nAll products cancel.")
    parsed = parse_answer(wrapped)
    report["G3_round_trip"] = {
        "pass": parsed == planted, "parsed_equals_answer": parsed == planted,
    }

    density_rng = random.Random(493_001)
    density_total = 200_000
    density_hits = 0
    density_t0 = time.perf_counter()
    for _ in range(density_total):
        density_hits += verify(inst, random_candidate(inst, density_rng))[0]
    density_elapsed = time.perf_counter() - density_t0
    density = density_hits / density_total
    quotient_space = math.comb(1 << shipping["block_bits"],
                               1 << (shipping["block_bits"] - 1))
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6 and quotient_space > 1_000_000,
        "hits": density_hits,
        "total": density_total,
        "observed_probability": density,
        "structure_aware_space": search_space(inst),
        "candidate_prior": "uniform over balanced sign vectors satisfying every pin",
        "generator_balanced_quotient_table_space": quotient_space,
    }

    baseline_t0 = time.perf_counter()
    baseline_answer, baseline_operations = _reference_completion(inst)
    baseline_elapsed = time.perf_counter() - baseline_t0
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    baseline_ok = baseline_answer is not None and verify(inst, baseline_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and baseline_ok and demo_count == 1,
        "shipping_sampled_valid_fraction": density,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": density_total,
        "shipping_density_wall_seconds": round(density_elapsed, 6),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_name": "exact modular Gauss-Jordan elimination",
        "baseline_solved": baseline_ok,
        "baseline_wall_seconds": round(baseline_elapsed, 6),
        "baseline_modular_operations": baseline_operations,
    }

    attack_names = [
        "row_sum_outlier", "residual_greedy", "paper_rvs_512",
        "repaired_visible_column", "repaired_first_pair_product",
        "single_missing_character_ansatz", "repeat_pins_without_modulation",
    ]
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(8):
        attack_inst = make_instance(seed=70_000 + seed, **shipping)
        candidates = {
            "row_sum_outlier": _attack_row_sum_outlier(attack_inst),
            "residual_greedy": _attack_residual_greedy(attack_inst),
            "repaired_visible_column": _attack_copy_visible(attack_inst),
            "repaired_first_pair_product": _attack_first_pair_product(attack_inst),
            "single_missing_character_ansatz": _attack_single_missing_character(attack_inst),
            "repeat_pins_without_modulation": _attack_repeat_pins(attack_inst),
        }
        random_answer, _ = _attack_random_restart(
            attack_inst, random.Random(90_000 + seed), 512
        )
        candidates["paper_rvs_512"] = random_answer
        for name, candidate in candidates.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attacks[name]["successes"] += 1
        ref_t0 = time.perf_counter()
        reference_answer, operations = _reference_completion(attack_inst)
        reference_times.append(time.perf_counter() - ref_t0)
        reference_operations.append(operations)
        reference_successes += (
            reference_answer is not None and verify(attack_inst, reference_answer)[0]
        )
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact modular Gauss-Jordan elimination",
            "complexity": "O(n^3) exact modular arithmetic",
            "wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_operations) / 8),
            "operations_max": max(reference_operations),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = {"n": shipping["n"] * 2,
               "block_bits": shipping["block_bits"] + 1}
    doubled_inst = make_instance(seed=314159, **doubled)
    doubled_ok, doubled_reason = verify(doubled_inst, doubled_inst["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"],
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_block_bits": doubled["block_bits"],
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    failures = []
    for seed in range(20):
        base = make_instance(seed=120_000 + seed, **shipping)
        key = canonical_key(base)
        rng = random.Random(130_000 + seed)
        row_order = list(range(base["n"]))
        rng.shuffle(row_order)
        width = len(base["column_ids"])
        column_order = list(range(width))
        rng.shuffle(column_order)
        label_permutation = list(range(base["n"]))
        rng.shuffle(label_permutation)
        bit_permutation = list(range(base["label_bits"]))
        rng.shuffle(bit_permutation)
        tag_translation = rng.randrange(base["n"])
        renumbered, carried = _renumber_output_labels(base, label_permutation)
        negated = {index for index in range(width) if index % 3 == 1}
        composed = _reorder_presentation(
            renumbered, row_order=row_order, column_order=column_order
        )
        composed = _negate_columns(composed, negated)
        variants = [
            (_reorder_presentation(base, row_order=row_order), base["answer"]),
            (_reorder_presentation(base, column_order=column_order), base["answer"]),
            (_reorder_presentation(base, row_order, column_order), base["answer"]),
            (_negate_columns(base, negated), base["answer"]),
            (renumbered, carried),
            (_rename_tag_basis(base, bit_permutation), base["answer"]),
            (_translate_tags(base, tag_translation), base["answer"]),
            (composed, carried),
        ]
        for variant, witness in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                failures.append(f"seed={seed}: key changed")
            carried_checks += 1
            if not verify(variant, witness)[0]:
                failures.append(f"seed={seed}: carried witness failed")
    distinct_keys = {
        canonical_key(make_instance(seed=140_000 + seed, **shipping))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not failures and len(distinct_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_keys": len(distinct_keys),
        "distinct_instances": 20,
        "failures": failures,
        "transformations": [
            "row presentation permutation", "column permutation",
            "independent column negations",
            "output-coordinate renumbering with carried witness",
            "simultaneous primal/dual bit-basis permutation",
            "global XOR translation of row tags", "their compositions",
        ],
    }

    compact, compact_operations = _compact_completion(inst)
    compact_ok = compact is not None and verify(inst, compact)[0]
    answer_blob = json.dumps(planted, separators=(",", ":"))
    arms = {key: dict(G9_ORACLE_RESULTS[key])
            for key in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (len(answer_blob) <= 2000 and len(planted) <= 256
                   and compact_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": _answer_token_estimate(planted),
        "answer_elements": len(planted),
        "intended_route_operations": compact_operations,
        "operation_definition": "exact sign negations after recognizing the Walsh block",
        "compact_route_verifies": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
