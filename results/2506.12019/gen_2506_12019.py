"""Verified Track-B problem generator for arXiv:2506.12019.

The paper studies exact Subset Sum through binary-increment navigation and the
symmetry between complementary subsets.  This module stays in that native
problem: it asks for indices of positive integers summing exactly to a target.

Instances are known by inverse generation.  Their shuffled values occur in
equal-sum complementary pairs whose deviations from a common centre form a
balanced radix code.  A structure-aware solver can decode that code compactly;
the generic reference route is Horowitz--Sahni meet in the middle.

Only the Python standard library is used.  Importing the module performs no
file I/O, network access, or printing.
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
from typing import Any


# Make gvlib available when this file is run from its result directory.  This
# family uses integers only, so the standard-library path remains complete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - gvlib is optional here
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite indexed set of positive integers",
        "integer target",
        "subset of indices",
    ],
    "verification_operations": [
        "integer index validation",
        "exact integer addition",
        "integer equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Equal-sum complementary pairs expose a common midpoint, and their "
        "geometric deviations turn the target into a uniquely decodable "
        "balanced-radix word; without that symmetry one searches subsets."
    ),
    "hardness_basis": (
        "Track B, using the Horowitz--Sahni meet-in-the-middle algorithm listed "
        "in Section 3.13 of the paper: it costs O(2^(n/2)) time and space and "
        "at shipping n=40 measured 0.22--4.85 seconds under varying shared-host "
        "load, 1,167,727 state visits, and 5,468,684 counted operations on "
        "average; the complementary-pair "
        "balanced-radix route takes at most 185 exact arithmetic operations at "
        "shipping n=40, but the generic million-state route is not executable "
        "in the no-tool evaluation context."
    ),
    "max_answer_tokens": 8,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON-native list of exactly k distinct 1-indexed item IDs in any "
        "order, where k is displayed in the instance; each ID is in [1,n]."
    ),
    "bounds": {
        "length": "instance k (10 at the shipping preset)",
        "minimum_id": 1,
        "maximum_id": "instance n",
        "distinct": True,
        "ordering": "irrelevant",
    },
}

DIFFICULTY = {
    "demo": {"n": 8, "k": 3, "scale_bits": 2},
    "easy": {"n": 28, "k": 10, "scale_bits": 16},
    "medium": {"n": 34, "k": 10, "scale_bits": 18},
    "hard": {"n": 40, "k": 10, "scale_bits": 20},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The displayed integers split into equal-sum complementary pairs whose "
    "distances from their common midpoint form a geometric radix sequence."
)
PLACEBO_HINT = (
    "The displayed integers are exact decimal values whose item identifiers "
    "should be tracked carefully during any arithmetic bookkeeping."
)

# Filled from the script-owned transcripts after the three oracle arms run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "oracle_unreachable_http_403_key_limit",
}

NOTES = r"""
Paper reading and definition.  Section 1 defines Subset Sum on a finite set of
integers (positive, negative, or zero) with a target; a concrete subset is the
witness.  Lemma 1 identifies subsets with binary inclusion strings.  Theorem 1
and Observation 2 establish complement symmetry in binary-increment order.
The generator therefore keeps the solver in the paper's native integer and
subset objects; there is no SAT, graph, finite-field, or convenience reduction.

Step 0 and the easy boundary.  Section 3.13 states that the paper's navigation
cost is O(C), where C is its number of in-bound candidates.  It explicitly says
sparse sets are easy, increasing density first makes them harder, and excessive
density makes solutions abundant and decision easy.  It also lists dynamic
programming O(nT) and meet in the middle O(2^(n/2)); Lemma 6 makes literal
powers-of-two instances uniquely and directly decodable.  The paper proves no
distributional lower bound for planted random instances.  A Track-A claim would
therefore be unsupported.  This module declares Track B and measures the
generic meet-in-the-middle algorithm at the shipping preset.

Construction.  Sample k pair positions and their signs before constructing the
target.  Pair i consists of M-g*q^i and M+g*q^i for q in {5,7}.  Exactly one
member of every selected pair is planted.  M is greater than twice the sum of
all deviations, so every target-hitting subset has exactly k elements.  Since
q>=5, balanced digits in {-2,-1,0,1,2} have unique value; this proves that the
planted subset is the unique witness.  Pair members are shuffled before IDs are
assigned.  Every displayed element has the same marginal probability k/n of
being planted, so plants and decoys are not separated by position, magnitude,
width, or a one-element distribution.

Compact route and attacks.  The short route finds the common pair midpoint,
reads deviations as a radix sequence, and decodes the target's balanced digits.
The operation bound counts integer arithmetic after recognizing the symmetry,
not the subset search it replaces.  The adversary panel tries closest-to-mean
outliers, residual-average greedy selection, an alternating choice from the k
smallest complementary pairs, and 512 uniform fixed-cardinality restarts.  All
must fail on eight shipping seeds.  The successful generic meet-in-the-middle
solver is deliberately reported as Track B's reference_algorithm, not as a
failing attack.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 500_000
_RADICES = (5, 7)


def _validate_params(n: int, k: int, scale_bits: int) -> None:
    values = (n, k, scale_bits)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("n, k, and scale_bits must be integers")
    if n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if not 1 <= k <= n // 2:
        raise ValueError("k must satisfy 1 <= k <= n/2")
    if not 1 <= scale_bits <= 48:
        raise ValueError("scale_bits must lie in [1,48]")


def make_instance(n: int, seed: int = 0, *, k: int = 10,
                  scale_bits: int = 20) -> dict:
    """Construct a unique-solution Subset Sum instance by inverse generation.

    The witness choices are sampled first.  The public weights and target are
    then assembled from the balanced-radix identity; no completed instance is
    searched or solved by the generator.
    """

    _validate_params(n, k, scale_bits)
    rng = random.Random(seed)
    pair_count = n // 2
    radix = _RADICES[rng.randrange(len(_RADICES))]
    if scale_bits == 1:
        scale = 1
    else:
        scale = rng.randrange(1 << (scale_bits - 1), 1 << scale_bits)
    deviations = [scale * pow(radix, i) for i in range(pair_count)]
    deviation_sum = sum(deviations)

    # A non-round, seed-dependent centre prevents decimal magnitude alone from
    # exposing the construction.  The inequality enforces witness cardinality.
    centre = (3 + rng.randrange(4)) * deviation_sum + rng.randrange(1, scale + 1)
    assert centre > 2 * deviation_sum

    # G: choose the certificate before the target or displayed IDs exist.
    selected_pairs = set(rng.sample(range(pair_count), k))
    selected_sign = {
        pair: (1 if rng.randrange(2) else -1) for pair in selected_pairs
    }

    records: list[tuple[int, bool]] = []
    target_deviation = 0
    for pair, deviation in enumerate(deviations):
        for sign in (-1, 1):
            planted = pair in selected_pairs and selected_sign[pair] == sign
            records.append((centre + sign * deviation, planted))
            if planted:
                target_deviation += sign * deviation

    rng.shuffle(records)
    items = [
        {"id": item_id, "value": value}
        for item_id, (value, _planted) in enumerate(records, start=1)
    ]
    answer = sorted(
        item_id
        for item_id, (_value, planted) in enumerate(records, start=1)
        if planted
    )
    target = k * centre + target_deviation

    # Construction-only assertions.  None of the private pair/sign choices is
    # stored in the instance, and verify never reads answer.
    assert len(answer) == k
    assert sum(items[i - 1]["value"] for i in answer) == target
    assert len({item["value"] for item in items}) == n

    return {
        "family": "complement-symmetric exact Subset Sum",
        "n": n,
        "required_size": k,
        "target": target,
        "items": items,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a self-contained statement and the exact output contract."""

    rows = "\n".join(
        f'{item["id"]}: {item["value"]}'
        for item in sorted(inst["items"], key=lambda row: row["id"])
    )
    k = int(inst["required_size"])
    example = ", ".join(str(i) for i in range(1, k + 1))
    statement = f"""EXACT SUBSET SUM

You are given {inst["n"]} distinct positive integers, each with a 1-based item
ID, and an integer target.  A subset chooses an item at most once.  Find any
subset whose values add exactly to the target.

For this instance it is guaranteed that every target-hitting subset contains
exactly {k} distinct items.  Your answer must therefore contain exactly {k}
distinct IDs from 1 through {inst["n"]}.  Order does not matter; repetitions
are forbidden.  All arithmetic is exact integer arithmetic.

Target: {inst["target"]}

ITEMS (one row per item: ID: VALUE)
{rows}"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    statement += f"""

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {k} distinct item IDs.
Example of the required format only: <answer>{example}</answer>
Output nothing else inside the tags."""
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged integer list; tolerate prose and fences."""

    if not isinstance(text, str):
        return None
    for raw in reversed(_ANSWER_RE.findall(text)):
        body = raw.strip()
        if body.startswith("```") and body.endswith("```"):
            body = body[3:-3].strip()
            if "\n" in body and body.split("\n", 1)[0].lower() in {
                "json", "text", "python"
            }:
                body = body.split("\n", 1)[1].strip()
        if body.startswith("[") and body.endswith("]"):
            try:
                value = json.loads(body)
            except (TypeError, ValueError):
                continue
            if isinstance(value, list) and all(
                isinstance(v, int) and not isinstance(v, bool) for v in value
            ):
                return value
            continue
        if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
            continue
        try:
            return [int(part.strip()) for part in body.split(",")]
        except ValueError:
            continue
    return None


def _public_item_map(inst: dict) -> dict[int, int]:
    result: dict[int, int] = {}
    for row in inst.get("items", []):
        if isinstance(row, dict) and isinstance(row.get("id"), int):
            result[row["id"]] = row.get("value")
    return result


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any witness using only public instance data, never inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a list of item IDs"
    if not answer:
        return False, "answer is empty"
    if any(not isinstance(v, int) or isinstance(v, bool) for v in answer):
        return False, "every item ID must be an integer"
    if len(answer) != inst["required_size"]:
        return False, f'expected exactly {inst["required_size"]} item IDs'
    if len(set(answer)) != len(answer):
        return False, "item IDs must be distinct"
    by_id = _public_item_map(inst)
    invalid = [v for v in answer if v not in by_id]
    if invalid:
        return False, f"item ID outside the inclusive range: {invalid[0]}"
    total = sum(by_id[v] for v in answer)
    if total != inst["target"]:
        return False, f"subset sum differs from target by {total - inst['target']}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied fixed-cardinality search space."""

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    ids = sorted(_public_item_map(inst))
    return sorted(rng.sample(ids, inst["required_size"]))


def search_space(inst: dict) -> int | None:
    """Return the exact size of the certificate language for this instance."""

    return math.comb(int(inst["n"]), int(inst["required_size"]))


def enumerate_all(inst: dict) -> int | None:
    """Brute-force valid witnesses only when the exact search is safely small."""

    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.combinations(
        sorted(_public_item_map(inst)), inst["required_size"]
    ):
        count += int(verify(inst, list(candidate))[0])
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize row/ID order and nonzero integer affine value changes.

    For fixed cardinality k, replacing every value w by u*w+c and the target T
    by u*T+k*c preserves exactly the same subsets whenever the displayed values
    remain positive.  Subtracting the least value and dividing all offsets by
    their gcd removes translation and absolute scale; taking the smaller of the
    forward and reflected normal forms removes the sign of u.
    """

    weights = sorted(int(v) for v in _public_item_map(inst).values())
    origin = weights[0]
    offsets = [value - origin for value in weights]
    target_offset = int(inst["target"]) - int(inst["required_size"]) * origin
    scale = 0
    for value in offsets + [target_offset]:
        scale = math.gcd(scale, abs(value))
    scale = max(1, scale)
    normalized = [value // scale for value in offsets]
    normalized_target = target_offset // scale
    span = normalized[-1]
    reflected = sorted(span - value for value in normalized)
    reflected_target = int(inst["required_size"]) * span - normalized_target
    forward_form = (normalized, normalized_target)
    reflected_form = (reflected, reflected_target)
    chosen_offsets, chosen_target = min(forward_form, reflected_form)
    payload = {
        "n": int(inst["n"]),
        "required_size": int(inst["required_size"]),
        "offsets": chosen_offsets,
        "target_offset": chosen_target,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _intended_operation_bound(params_or_inst: dict) -> int:
    """Conservative arithmetic count after the complementary-pair insight."""

    n = int(params_or_inst["n"])
    k = int(params_or_inst.get("required_size", params_or_inst.get("k", 10)))
    pair_count = n // 2
    # Centre/complement/deviation arithmetic, radix-ratio checks, target
    # normalization, and balanced divmods.  Comparisons and ID lookups are not
    # exact arithmetic and are not included.
    return 3 * n + 2 * pair_count + 2 * k + 5


def escalate(params: dict) -> dict | str | None:
    """Grow the item haystack while keeping the ten-ID witness fixed."""

    current = {key: value for key, value in params.items() if key != "_preset"}
    proposed = dict(current)
    proposed["n"] = int(current["n"]) + 4
    if _intended_operation_bound(proposed) > 300:
        # The fixed-length haystack axis has reached G9's arithmetic-effort
        # ceiling.  This is not ``cap_bound``, which is reserved for an answer
        # that would exceed the output cap.  Increasing only decimal magnitude
        # would add calculator work without increasing structural difficulty.
        return None
    return proposed


def _fast_valid(inst: dict, candidate: list[int] | None) -> bool:
    if candidate is None or len(candidate) != inst["required_size"]:
        return False
    if len(set(candidate)) != len(candidate):
        return False
    by_id = _public_item_map(inst)
    return all(v in by_id for v in candidate) and sum(
        by_id[v] for v in candidate
    ) == inst["target"]


def _structural_decode(inst: dict) -> list[int] | None:
    """Execute the intended complementary-pair/balanced-radix route exactly."""

    by_id = _public_item_map(inst)
    by_value = {value: item_id for item_id, value in by_id.items()}
    if len(by_value) != inst["n"]:
        return None
    values = sorted(by_value)
    endpoint_sum = values[0] + values[-1]
    if endpoint_sum % 2:
        return None
    centre = endpoint_sum // 2
    sign_ids: dict[int, dict[int, int]] = {}
    for value in values:
        complement = 2 * centre - value
        if complement not in by_value:
            return None
        deviation = abs(value - centre)
        if not deviation:
            return None
        sign = 1 if value > centre else -1
        sign_ids.setdefault(deviation, {})[sign] = by_value[value]
    if any(set(sides) != {-1, 1} for sides in sign_ids.values()):
        return None

    deviations = sorted(sign_ids)
    scale = deviations[0]
    if len(deviations) < 2 or deviations[1] % scale:
        return None
    radix = deviations[1] // scale
    if radix < 5 or any(
        deviation != scale * pow(radix, exponent)
        for exponent, deviation in enumerate(deviations)
    ):
        return None

    residual = inst["target"] - inst["required_size"] * centre
    if residual % scale:
        return None
    word = residual // scale
    answer: list[int] = []
    for deviation in deviations:
        residue = word % radix
        if residue == 0:
            digit = 0
        elif residue == 1:
            digit = 1
        elif residue == radix - 1:
            digit = -1
        else:
            return None
        if digit:
            answer.append(sign_ids[deviation][digit])
        word = (word - digit) // radix
    if word or len(answer) != inst["required_size"]:
        return None
    answer.sort()
    return answer if verify(inst, answer)[0] else None


def _attack_candidates(inst: dict, restart_seed: int) -> dict[str, list[int] | None]:
    """Construction-aware cheap attacks that do not execute the intended code."""

    rows = list(inst["items"])
    k = int(inst["required_size"])
    outlier = sorted(
        row["id"]
        for row in sorted(
            rows,
            key=lambda row: (
                abs(k * row["value"] - inst["target"]), row["id"]
            ),
        )[:k]
    )

    unused = list(rows)
    residual = int(inst["target"])
    greedy: list[int] = []
    for slots in range(k, 0, -1):
        # Compare integer cross-products, avoiding float decisions.
        pick = min(
            unused,
            key=lambda row: (abs(slots * row["value"] - residual), row["id"]),
        )
        greedy.append(pick["id"])
        residual -= pick["value"]
        unused.remove(pick)

    # This attack notices the most visible part of the intended symmetry but
    # guesses that the k innermost pairs matter and alternates sides.
    ordered = sorted(rows, key=lambda row: (row["value"], row["id"]))
    pairs = [(ordered[i], ordered[-1 - i]) for i in range(inst["n"] // 2)]
    pairs.sort(key=lambda pair: pair[1]["value"] - pair[0]["value"])
    pair_guess = sorted(
        (low if index % 2 == 0 else high)["id"]
        for index, (low, high) in enumerate(pairs[:k])
    )

    rng = random.Random(restart_seed)
    random_hit = None
    for _ in range(512):
        candidate = random_candidate(inst, rng)
        if _fast_valid(inst, candidate):
            random_hit = candidate
            break

    return {
        "outlier_closest_to_target_mean": outlier,
        "greedy_residual_average": sorted(greedy),
        "by_hand_innermost_pairs_alternating": pair_guess,
        "random_restart_512": random_hit,
    }


def _reference_mitm(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Cardinality-aware Horowitz--Sahni search using public data only."""

    rows = sorted(inst["items"], key=lambda row: row["id"])
    split = len(rows) // 2
    left = rows[:split]
    right = rows[split:]
    k = int(inst["required_size"])
    target = int(inst["target"])
    operations = 0
    right_visits = 0
    left_visits = 0

    # Enumerate right subsets in Gray-code order.  Store only cardinalities
    # that can participate in a k-subset; same-cardinality sums are unique in
    # this construction, though setdefault keeps the algorithm generic.
    table: dict[tuple[int, int], int] = {}
    previous_gray = 0
    subset_sum = 0
    subset_size = 0
    for ordinal in range(1 << len(right)):
        gray = ordinal ^ (ordinal >> 1)
        if ordinal:
            changed = gray ^ previous_gray
            bit = changed.bit_length() - 1
            if gray & changed:
                subset_sum += right[bit]["value"]
                subset_size += 1
            else:
                subset_sum -= right[bit]["value"]
                subset_size -= 1
            operations += 4
        if subset_size <= k:
            table.setdefault((subset_size, subset_sum), gray)
            operations += 1
        previous_gray = gray
        right_visits += 1

    previous_gray = 0
    subset_sum = 0
    subset_size = 0
    for ordinal in range(1 << len(left)):
        gray = ordinal ^ (ordinal >> 1)
        if ordinal:
            changed = gray ^ previous_gray
            bit = changed.bit_length() - 1
            if gray & changed:
                subset_sum += left[bit]["value"]
                subset_size += 1
            else:
                subset_sum -= left[bit]["value"]
                subset_size -= 1
            operations += 4
        needed_size = k - subset_size
        if 0 <= needed_size <= len(right):
            right_mask = table.get((needed_size, target - subset_sum))
            operations += 2
            if right_mask is not None:
                answer = [
                    left[bit]["id"] for bit in range(len(left)) if gray & (1 << bit)
                ]
                answer.extend(
                    right[bit]["id"] for bit in range(len(right))
                    if right_mask & (1 << bit)
                )
                answer.sort()
                if verify(inst, answer)[0]:
                    return answer, {
                        "operations": operations,
                        "state_visits": right_visits + left_visits,
                        "stored_states": len(table),
                    }
        previous_gray = gray
        left_visits += 1
    return None, {
        "operations": operations,
        "state_visits": right_visits + left_visits,
        "stored_states": len(table),
    }


def _atom_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, list[int]]:
    old_ids = sorted(_public_item_map(inst))
    new_ids = list(old_ids)
    rng.shuffle(new_ids)
    mapping = dict(zip(old_ids, new_ids))
    changed = dict(inst)
    changed["items"] = [
        {"id": mapping[row["id"]], "value": row["value"]}
        for row in reversed(inst["items"])
    ]
    carried = sorted(mapping[item_id] for item_id in inst["answer"])
    changed["answer"] = carried
    return changed, carried


def _affine_instance(inst: dict, multiplier: int, translation: int) -> dict:
    changed = dict(inst)
    changed["items"] = [
        {
            "id": row["id"],
            "value": multiplier * row["value"] + translation,
        }
        for row in inst["items"]
    ]
    changed["target"] = (
        multiplier * inst["target"]
        + inst["required_size"] * translation
    )
    return changed


def selftest() -> dict:
    """Run G1--G9 and return a fully JSON-native measured report."""

    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures: list[str] = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **shipping_params)
    planted = list(ship["answer"])
    unused_id = next(item_id for item_id in range(1, ship["n"] + 1)
                     if item_id not in set(planted))
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": sorted(planted[:-1] + [unused_id]),
        "duplicate_one": planted[:-1] + [planted[-2]],
        "empty": [],
        "out_of_range": planted[:-1] + [ship["n"] + 1],
    }
    cases: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    answer_text = ", ".join(str(v) for v in planted)
    model_style = (
        "I checked the exact sum.\n```text\n"
        f"<answer>{answer_text}</answer>\n```\n"
        "The IDs above are distinct."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    samples = 250_000
    sample_rng = random.Random(8675309)
    hits = 0
    for _ in range(samples):
        hits += int(_fast_valid(ship, random_candidate(ship, sample_rng)))
    density = hits / samples
    candidate_space = search_space(ship)
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6 and 1 / candidate_space < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": density,
        "exact_probability_from_unique_construction": 1 / candidate_space,
        "candidate_space": candidate_space,
        "sampler": "uniform k-subsets, with exact cardinality enforced",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_names = [
        "outlier_closest_to_target_mean",
        "greedy_residual_average",
        "by_hand_innermost_pairs_alternating",
        "random_restart_512",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": 8} for name in attack_names
    }
    reference_successes = 0
    reference_times: list[float] = []
    reference_operations: list[int] = []
    reference_visits: list[int] = []
    reference_stored: list[int] = []
    for seed in range(8):
        inst = make_instance(seed=12_000 + seed, **shipping_params)
        candidates = _attack_candidates(inst, 700_000 + seed)
        for name in attack_names:
            attack_results[name]["successes"] += int(
                _fast_valid(inst, candidates[name])
            )
        started = time.perf_counter()
        reference_answer, counts = _reference_mitm(inst)
        elapsed = time.perf_counter() - started
        reference_times.append(elapsed)
        reference_operations.append(counts["operations"])
        reference_visits.append(counts["state_visits"])
        reference_stored.append(counts["stored_states"])
        reference_successes += int(
            reference_answer is not None and verify(inst, reference_answer)[0]
        )

    reference = {
        "name": "cardinality-aware Horowitz--Sahni meet in the middle",
        "paper_location": "Section 3.13, Comparison With Traditional Methods",
        "complexity": "O(2^(n/2)) time and O(2^(n/2)) space",
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "state_visits_mean": sum(reference_visits) / len(reference_visits),
        "state_visits_max": max(reference_visits),
        "stored_states_mean": sum(reference_stored) / len(reference_stored),
        "stored_states_max": max(reference_stored),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attack_results.values()
    )
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6
        and demo_count is not None and demo_count >= 1
        and reference_successes == 8
        and reference["state_visits_mean"] >= 1_000_000,
        "shipping_density_hits": hits,
        "shipping_density_total": samples,
        "shipping_observed_fraction": density,
        "shipping_structure_aware_space": candidate_space,
        "shipping_solution_count_by_construction": 1,
        "shipping_exact_fraction_by_construction": 1 / candidate_space,
        "demo_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_sec_max": reference["wall_clock_sec_max"],
        "baseline_operations_mean": reference["operations_mean"],
        "baseline_operations_max": reference["operations_max"],
        "baseline_state_visits_mean": reference["state_visits_mean"],
        "baseline_state_visits_max": reference["state_visits_max"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and search_space(doubled) > search_space(ship)
        and len(doubled["answer"]) == len(ship["answer"]),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_space": search_space(ship),
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "answer_elements_shipping": _atom_count(ship["answer"]),
        "answer_elements_doubled": _atom_count(doubled["answer"]),
    }

    invariant_checks = 0
    real_transform_checks = 0
    composed_checks = 0
    reflected_composed_checks = 0
    unrelated_keys: list[str] = []
    g8_failures: list[str] = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(inst)
        unrelated_keys.append(key)

        reordered = dict(inst)
        reordered["items"] = list(reversed(inst["items"]))
        if canonical_key(reordered) == key:
            invariant_checks += 1
        else:
            g8_failures.append(f"row reordering changed key at seed {seed}")
        if verify(reordered, inst["answer"])[0]:
            real_transform_checks += 1
        else:
            g8_failures.append(f"row reordering rejected answer at seed {seed}")

        relabelled, carried = _relabel_instance(
            inst, random.Random(30_000 + seed)
        )
        affine = _affine_instance(relabelled, 3 + seed % 5, 11 + seed)
        if canonical_key(affine) == key and verify(affine, carried)[0]:
            composed_checks += 1
        else:
            g8_failures.append(f"composed relabel/affine map failed at seed {seed}")

        # Reflection is another genuine fixed-cardinality affine symmetry:
        # w -> -u*w+c and T -> -u*T+k*c.  Choose c so all values stay positive.
        reflection_scale = 2 + seed % 3
        reflection_shift = (
            reflection_scale
            * max(row["value"] for row in relabelled["items"])
            + 17
            + seed
        )
        reflected = _affine_instance(
            relabelled, -reflection_scale, reflection_shift
        )
        if canonical_key(reflected) == key and verify(reflected, carried)[0]:
            reflected_composed_checks += 1
        else:
            g8_failures.append(
                f"composed relabel/reflection map failed at seed {seed}"
            )
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "composed_transformation_checks": composed_checks,
        "reflected_composed_transformation_checks": reflected_composed_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "input-row reordering",
            "item-ID permutation with carried witness",
            "positive integer affine value map composed with both",
            "reflected integer affine value map composed with ID relabelling",
        ],
        "failures": g8_failures,
    }

    answer_blobs = [
        json.dumps(
            make_instance(seed=seed, **shipping_params)["answer"],
            separators=(",", ":"),
        )
        for seed in range(32)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = (answer_chars + 3) // 4
    arms = {
        name: {
            "solved": int(G9_MEASUREMENTS[name]["solved"]),
            "attempts": int(G9_MEASUREMENTS[name]["attempts"]),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    intended_operations = _intended_operation_bound(ship)
    compact_answer = _structural_decode(ship)
    within_caps = (
        answer_chars <= 2_000
        and _atom_count(ship["answer"]) <= 256
        and intended_operations <= 300
        and compact_answer is not None
        and verify(ship, compact_answer)[0]
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the three arms, including hinted, are diagnostic.
        # The sole gate is the answer/route cap.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": _atom_count(ship["answer"]),
        "intended_route_operations": intended_operations,
        "compact_route_verifies": compact_answer is not None
        and verify(ship, compact_answer)[0],
    }

    gates = [name for name in report if name.startswith("G")]
    report["all_passed"] = all(bool(report[name].get("pass")) for name in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
