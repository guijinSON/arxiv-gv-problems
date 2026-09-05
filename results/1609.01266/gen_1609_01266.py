"""Verified problem generator for arXiv:1609.01266.

The paper's Theorem 20 proves that Minimum Cycle Weighing by columns of a
pseudo-grid digraph (MCW) is strongly NP-complete.  Its proof gives an exact
reduction from 3-PARTITION.  This module samples a planted 3-partition first,
applies that displayed reduction, and asks for the normalized MCW witness used
in the forward direction of the proof.

The planted partition is never recovered by solving the generated instance.
For non-demo presets, generation merely rejects candidates that a bounded panel
of attacks can solve; the retained witness is still the initially sampled one.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "weighted pseudo-grid column tuples",
        "paper-licensed 3-PARTITION core",
    ],
    "verification_operations": [
        "exact integer triple sums",
        "set-partition checks",
        "exact max-plus pseudo-grid dynamic programming",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, Theorem 20: the displayed reduction from 3-PARTITION "
        "to Minimum Cycle Weighing (MCW)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Recognize the item columns inside the pseudo-grid weighting and propagate "
        "the exact target sum through a sparse exact-cover core instead of "
        "searching all column permutations and swaps."
    ),
    "hardness_basis": (
        "Track A: Theorem 20 proves strong NP-completeness through 3-PARTITION; "
        "the shipping regime uses shuffled planted cores with 24 target triples, "
        "T=n^2 and values strictly between T/4 and T/2, conditioned to defeat "
        "the domain-standard MRV exact-cover search for 5,000 nodes on every "
        "generated instance."
    ),
    "max_answer_tokens": 72,
}

NATIVE = {
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

DIFFICULTY = {
    "demo": {"n": 3, "filter_nodes": 0, "random_restarts": 0},
    "easy": {"n": 24, "filter_nodes": 5_000, "random_restarts": 64},
    "medium": {"n": 36, "filter_nodes": 20_000, "random_restarts": 96},
    "hard": {"n": 48, "filter_nodes": 50_000, "random_restarts": 128},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The columns whose last two coordinates are both 1 carry the exact-cover "
    "core of the pseudo-grid weighting."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the column indices helps avoid accidental mistakes "
    "in this pseudo-grid weighting."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered partition of the 3n item-column indices into exactly n "
        "unordered triples; n<=85, every index is an integer in [0,5n), and "
        "every item index occurs exactly once."
    ),
    "bounds": {
        "max_groups": 85,
        "group_size": 3,
        "max_atomic_elements": 255,
        "index_upper_exclusive": 425,
    },
}

# Filled from the script-owned oracle transcripts after the three runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 2},
    "placebo": {"solved": 0, "attempts": 2},
    "hinted_verdict": "incomplete_key_limit",
}

NOTES = (
    "Section 1 fixes the distinction that matters: equivalent-model minimization "
    "is the polynomial minimal representation problem, while minimization over "
    "isomorphic models is the hard minimum representation problem. Section 4.1, "
    "Theorem 15 gives the O(n^3)-time easy algorithm for the former, so the prior "
    "idea of merely planting a unit circular-arc representation was discarded. "
    "Section 5, Theorem 20 defines MCW and gives the exact 3-PARTITION reduction; "
    "Theorem 21 transports MCW to minimum unit circular-arc representation. The "
    "generator samples the partition before assembling the L_i, item and H_i "
    "columns. It shuffles every column and conditions only on failure of value-band, "
    "greedy, random-restart and bounded MRV exact-cover attacks. Plants and accidental "
    "decoys are therefore the same item-column population; no answer is found by "
    "the filter. Verification reconstructs the normalized Y sequence and recomputes "
    "its maximum pseudo-grid cycle weight by exact max-plus dynamic programming."
)


def _mix_seed(seed: int, nonce: int) -> int:
    """Stable integer mixing; never touches module-global random state."""
    x = (int(seed) & ((1 << 64) - 1)) ^ 0x160901266A5A5A5A
    x = (x + (nonce + 1) * 0x9E3779B97F4A7C15) & ((1 << 128) - 1)
    x ^= x >> 30
    x *= 0xBF58476D1CE4E5B9
    x ^= x >> 27
    return x & ((1 << 128) - 1)


def _l_value(n: int, i: int) -> int:
    return 2 * (n * n + i)


def _h_value(n: int, i: int) -> int:
    return _l_value(n, i) + 2


def _item_indices(inst: dict) -> list[int]:
    target = inst["target"]
    return [
        i
        for i, row in enumerate(inst["columns"])
        if row[0] == target and row[2] == 1 and row[3] == 1
    ]


def _item_value(inst: dict, index: int) -> int:
    return inst["columns"][index][1]


def _quick_partition_valid(inst: dict, answer: object) -> bool:
    if not isinstance(answer, list) or len(answer) != inst["n"]:
        return False
    flat: list[int] = []
    for group in answer:
        if not isinstance(group, list) or len(group) != 3:
            return False
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in group):
            return False
        flat.extend(group)
        if sum(_item_value(inst, x) for x in group if 0 <= x < len(inst["columns"])) != inst["target"]:
            return False
    return len(set(flat)) == len(flat) and set(flat) == set(_item_indices(inst))


def _raw_instance(n: int, seed: int, nonce: int) -> dict:
    rng = random.Random(_mix_seed(seed, nonce))
    target = n * n
    low = target // 4 + 1
    high = (target - 1) // 2
    if low > high:
        raise ValueError("n must be at least 3")

    # Inverse generation: sample n triples before any reduction object exists.
    planted_values: list[list[int]] = []
    for _ in range(n):
        for _attempt in range(100_000):
            a = rng.randint(low, high)
            b = rng.randint(low, high)
            c = target - a - b
            if low <= c <= high:
                planted_values.append([a, b, c])
                break
        else:  # pragma: no cover - the interval has ample valid pairs for n>=3
            raise RuntimeError("could not sample a planted triple")

    y_infinity = _h_value(n, n) ** 2
    records: list[dict[str, Any]] = []
    for group_id, triple in enumerate(planted_values):
        li = _l_value(n, group_id)
        hi = _h_value(n, group_id)
        records.append(
            {
                "kind": "L",
                "group": group_id,
                "row": [li * target, 1, y_infinity - li * target - 1, y_infinity - 2],
            }
        )
        for element_id, value in enumerate(triple):
            records.append(
                {
                    "kind": "item",
                    "group": group_id,
                    "element": element_id,
                    "row": [target, value, 1, 1],
                }
            )
        records.append(
            {
                "kind": "H",
                "group": group_id,
                "row": [1, hi * target, y_infinity - hi * target - 1, y_infinity - 2],
            }
        )

    rng.shuffle(records)
    columns = [record["row"] for record in records]
    answer: list[list[int]] = [[] for _ in range(n)]
    for index, record in enumerate(records):
        if record["kind"] == "item":
            answer[record["group"]].append(index)
    for group in answer:
        rng.shuffle(group)
    rng.shuffle(answer)

    bound = (
        (10 * n - 1) * y_infinity
        + sum(_h_value(n, j) * target for j in range(n))
        + n * (target + 6)
    )
    return {
        "paper": "arXiv:1609.01266",
        "family": "minimum cycle weighing on the paper's pseudo-grid",
        "n": n,
        "target": target,
        "y_infinity": y_infinity,
        "cycle_bound": bound,
        "columns": columns,
        "answer": answer,
    }


def _exact_triples(inst: dict) -> tuple[list[tuple[int, int, int]], dict[int, list[int]]]:
    items = _item_indices(inst)
    by_value: dict[int, list[int]] = {}
    for index in items:
        by_value.setdefault(_item_value(inst, index), []).append(index)
    triples: list[tuple[int, int, int]] = []
    target = inst["target"]
    for a_pos, a in enumerate(items):
        for b in items[a_pos + 1 :]:
            if b <= a:
                # items are in input order, so use a set-normalized condition below.
                pass
            needed = target - _item_value(inst, a) - _item_value(inst, b)
            for c in by_value.get(needed, ()):
                if c != a and c != b:
                    triple = tuple(sorted((a, b, c)))
                    if triple[0] == a and triple[1] == b:
                        triples.append(triple)
    triples = sorted(set(triples))
    incident = {index: [] for index in items}
    for triple_id, triple in enumerate(triples):
        for index in triple:
            incident[index].append(triple_id)
    return triples, incident


def _attack_value_bands(inst: dict) -> list[list[int]]:
    ordered = sorted(_item_indices(inst), key=lambda i: (_item_value(inst, i), i))
    n = inst["n"]
    return [[ordered[i], ordered[n + i], ordered[3 * n - 1 - i]] for i in range(n)]


def _attack_greedy_exact_sum(inst: dict) -> list[list[int]] | None:
    remaining = set(_item_indices(inst))
    groups: list[list[int]] = []
    target = inst["target"]
    while remaining:
        a = max(remaining, key=lambda i: (_item_value(inst, i), -i))
        others = sorted(remaining - {a}, key=lambda i: (_item_value(inst, i), i))
        found = None
        left, right = 0, len(others) - 1
        wanted = target - _item_value(inst, a)
        while left < right:
            total = _item_value(inst, others[left]) + _item_value(inst, others[right])
            if total == wanted:
                found = (others[left], others[right])
                break
            if total < wanted:
                left += 1
            else:
                right -= 1
        if found is None:
            return None
        group = [a, found[0], found[1]]
        groups.append(group)
        remaining.difference_update(group)
    return groups


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int
) -> tuple[list[list[int]] | None, int]:
    triples, incident = _exact_triples(inst)
    triple_sets = [set(triple) for triple in triples]
    all_items = set(_item_indices(inst))
    steps = 0
    for _ in range(restarts):
        uncovered = set(all_items)
        groups: list[list[int]] = []
        while uncovered:
            steps += 1
            pivot = rng.choice(tuple(sorted(uncovered)))
            choices = [z for z in incident[pivot] if triple_sets[z] <= uncovered]
            if not choices:
                break
            z = rng.choice(choices)
            group = list(triples[z])
            groups.append(group)
            uncovered.difference_update(group)
        if not uncovered:
            return groups, steps
    return None, steps


def _attack_exact_cover_mrv(
    inst: dict, node_cap: int
) -> tuple[list[list[int]] | None, int, int]:
    """Algorithm-X style MRV search, capped after `node_cap` recursive nodes."""
    triples, incident = _exact_triples(inst)
    items = _item_indices(inst)
    local = {index: bit for bit, index in enumerate(items)}
    masks = [sum(1 << local[x] for x in triple) for triple in triples]
    full = (1 << len(items)) - 1
    nodes = 0
    option_checks = 0

    def dfs(covered: int) -> list[int] | None | bool:
        nonlocal nodes, option_checks
        nodes += 1
        if nodes > node_cap:
            return False  # distinguished cap marker
        if covered == full:
            return []
        best_options: list[int] | None = None
        for index in items:
            if covered & (1 << local[index]):
                continue
            options: list[int] = []
            for triple_id in incident[index]:
                option_checks += 1
                if masks[triple_id] & covered == 0:
                    options.append(triple_id)
            if not options:
                return None
            if best_options is None or len(options) < len(best_options):
                best_options = options
        assert best_options is not None
        for triple_id in best_options:
            result = dfs(covered | masks[triple_id])
            if result is False:
                return False
            if isinstance(result, list):
                return [triple_id] + result
        return None

    result = dfs(0)
    if result is False or result is None:
        return None, nodes, option_checks
    return [list(triples[z]) for z in result], nodes, option_checks


def _passes_generation_filter(
    inst: dict, seed: int, nonce: int, filter_nodes: int, random_restarts: int
) -> bool:
    if filter_nodes <= 0:
        return True
    if _quick_partition_valid(inst, _attack_value_bands(inst)):
        return False
    greedy = _attack_greedy_exact_sum(inst)
    if greedy is not None and _quick_partition_valid(inst, greedy):
        return False
    restart, _ = _attack_random_restart(
        inst, random.Random(_mix_seed(seed ^ 0xA77AC, nonce)), random_restarts
    )
    if restart is not None and _quick_partition_valid(inst, restart):
        return False
    exact, _, _ = _attack_exact_cover_mrv(inst, filter_nodes)
    return exact is None


def make_instance(
    n: int,
    seed: int = 0,
    filter_nodes: int = 0,
    random_restarts: int = 64,
    **params: Any,
) -> dict:
    """Build a paper-reduction instance around a pre-sampled partition.

    `n` is the number of target triples.  The certificate is sampled before the
    MCW tuple sequence is assembled.  The bounded attack filter only chooses
    among already-certified candidates and never supplies the answer.
    """
    del params
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if n > 85:
        raise ValueError("n>85 would exceed the 256-atom answer cap")
    if filter_nodes < 0 or random_restarts < 0:
        raise ValueError("filter_nodes and random_restarts must be nonnegative")
    max_candidates = 2_048
    for nonce in range(max_candidates):
        inst = _raw_instance(n, seed, nonce)
        if _passes_generation_filter(inst, seed, nonce, filter_nodes, random_restarts):
            inst["filter_nodes"] = filter_nodes
            inst["random_restarts"] = random_restarts
            inst["selection_attempts"] = nonce + 1
            return inst
    raise RuntimeError(
        f"no attack-resistant planted instance found in {max_candidates} candidates"
    )


def render(inst: dict) -> str:
    n = inst["n"]
    k = 5 * n
    lines = [
        "Find a normalized certificate for this Minimum Cycle Weighing (MCW) instance.",
        "",
        "Definitions.",
        f"There are k={k} weighted column tuples X[q]=(x0,x1,y0,y1), listed below in shuffled order with 0-based indices.",
        f"The MCW pseudo-grid has 2k={2*k} columns and 4k={4*k} rows, with a vertex v(q,r) at every column q and row r.",
        "A diagonal edge goes from v(q,r) to v(q+1,r-1), a vertical edge goes from v(q,r) to v(q,r+1), and a horizontal edge goes from the last column back to the first in the same row whenever the stated vertices exist.",
        "For tuple (x0,x1,y0,y1) at tuple-position j and p=r mod 2: the diagonal leaving even column 2j has weight xp; a diagonal leaving an odd column and every horizontal edge have weight 1; a vertical edge leaving even column 2j has weight yp+xp+1; and a vertical edge leaving odd column 2j+1 has weight y(1-p)+xp+1.",
        "The weight of a cycle is the sum of its edge weights, and wg(Y) is the maximum cycle weight after the tuples have been reordered into sequence Y.",
        "",
        "This instance is in the normalized Theorem-20 reduction form. You must identify every item tuple, meaning a tuple (T,s,1,1), and partition their 0-based input indices into exactly n triples.",
        "For i=0,...,n-1 define l_i=2(n^2+i), h_i=l_i+2, and y_inf=h_n^2. The anchor tuples are L_i=(l_i*T,1,y_inf-l_i*T-1,y_inf-2) and H_i=(1,h_i*T,y_inf-h_i*T-1,y_inf-2).",
        "A certificate is valid exactly when every item index appears once and the three s values in every triple sum to T. The checker forms Y=(L_0, triple_0, H_0, L_1, triple_1, H_1, ..., L_(n-1), triple_(n-1), H_(n-1)), with no coordinate swaps, and independently recomputes that wg(Y) is at most the displayed bound.",
        "The order of the triples and the order of indices inside each triple do not matter. Repeats are forbidden; anchor-column indices are not item indices.",
        "",
        f"n = {n}",
        f"T = {inst['target']}",
        f"y_inf = {inst['y_infinity']}",
        f"cycle-weight bound = {inst['cycle_bound']}",
        "",
        "Shuffled tuples, as index: (x0,x1,y0,y1):",
    ]
    for index, row in enumerate(inst["columns"]):
        lines.append(f"{index}: ({row[0]},{row[1]},{row[2]},{row[3]})")
    lines.extend(
        [
            "",
            f"Give your final answer inside <answer></answer> tags as a JSON array of exactly {n} three-integer arrays.",
            "Example: <answer>[[3,17,42],[8,11,29]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    def decode_body(body: str) -> object | None:
        body = body.strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return None
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return value if isinstance(value, list) else None

    try:
        tagged = re.findall(
            r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL
        )
        for raw in reversed(tagged):
            value = decode_body(raw)
            if value is not None:
                return value

        # Models occasionally obey the JSON format but omit the XML-style tags.
        # Recover a fenced JSON answer before attempting a conservative raw scan.
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
        for raw in reversed(fenced):
            value = decode_body(raw)
            if value is not None:
                return value

        decoder = json.JSONDecoder()
        candidates: list[object] = []
        for start, char in enumerate(text):
            if char != "[":
                continue
            try:
                value, _ = decoder.raw_decode(text[start:])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(value, list):
                candidates.append(value)
        return candidates[-1] if candidates else None
    except Exception:
        return None


def _anchor_maps(inst: dict) -> tuple[dict[int, list[int]], dict[int, list[int]]]:
    n = inst["n"]
    target = inst["target"]
    yinf = inst["y_infinity"]
    rows = {tuple(row): row for row in inst["columns"]}
    lower: dict[int, list[int]] = {}
    upper: dict[int, list[int]] = {}
    for i in range(n):
        li = _l_value(n, i)
        hi = _h_value(n, i)
        lower_row = [li * target, 1, yinf - li * target - 1, yinf - 2]
        upper_row = [1, hi * target, yinf - hi * target - 1, yinf - 2]
        lower[i] = rows[tuple(lower_row)]
        upper[i] = rows[tuple(upper_row)]
    return lower, upper


def _normalized_sequence(inst: dict, answer: list[list[int]]) -> list[list[int]]:
    lower, upper = _anchor_maps(inst)
    sequence: list[list[int]] = []
    for i, group in enumerate(answer):
        sequence.append(lower[i])
        sequence.extend(inst["columns"][index] for index in group)
        sequence.append(upper[i])
    return sequence


def _max_cycle_weight(sequence: list[list[int]]) -> tuple[int, int]:
    """Exact maximum cycle weight in O(k^2) max-plus relaxations.

    Removing the sole horizontal edge from a cycle leaves a left-to-right path.
    Such a path uses exactly 2k-1 diagonals and therefore exactly 2k-1 verticals.
    Four-k rows can realize every prefix displacement, so it is enough to retain
    the initial row parity and the count of verticals already used.
    """
    k = len(sequence)
    columns = 2 * k
    diagonal_count = columns - 1
    negative = -10**200
    best = negative
    operations = 0
    for start_parity in (0, 1):
        dp = [negative] * (diagonal_count + 1)
        dp[0] = 0
        for q in range(columns):
            row = sequence[q // 2]
            for used in range(diagonal_count):
                if dp[used] == negative:
                    continue
                parity = (start_parity + used - q) & 1
                if q % 2 == 0:
                    vertical = row[2 + parity] + row[parity] + 1
                else:
                    vertical = row[2 + (1 - parity)] + row[parity] + 1
                candidate = dp[used] + vertical
                operations += 2
                if candidate > dp[used + 1]:
                    dp[used + 1] = candidate
            if q < columns - 1:
                next_dp = [negative] * (diagonal_count + 1)
                for used, value in enumerate(dp):
                    if value == negative:
                        continue
                    parity = (start_parity + used - q) & 1
                    diagonal = row[parity] if q % 2 == 0 else 1
                    next_dp[used] = value + diagonal
                    operations += 1
                dp = next_dp
        best = max(best, dp[diagonal_count] + 1)
    return best, operations


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "malformed: expected a JSON array of triples"
    if len(answer) == 0:
        return False, "empty: expected a nonempty partition"
    if len(answer) != n:
        return False, f"wrong group count: expected {n}, got {len(answer)}"

    flat: list[int] = []
    for group_number, group in enumerate(answer):
        if not isinstance(group, list) or len(group) != 3:
            return False, f"wrong group shape: group {group_number} must contain 3 indices"
        for index in group:
            if not isinstance(index, int) or isinstance(index, bool):
                return False, "malformed index: every entry must be an integer"
            if index < 0 or index >= len(inst["columns"]):
                return False, f"out of range: column index {index} is invalid"
            flat.append(index)
    if len(set(flat)) != len(flat):
        return False, "duplicate: an item-column index appears more than once"

    item_set = set(_item_indices(inst))
    used = set(flat)
    nonitems = sorted(used - item_set)
    if nonitems:
        return False, f"anchor used: column {nonitems[0]} is not an item tuple"
    missing = sorted(item_set - used)
    if missing:
        return False, f"incomplete: item column {missing[0]} is missing"

    for group_number, group in enumerate(answer):
        total = sum(_item_value(inst, index) for index in group)
        if total != inst["target"]:
            return False, (
                f"wrong target sum: group {group_number} sums to {total}, "
                f"not {inst['target']}"
            )

    sequence = _normalized_sequence(inst, answer)
    maximum, _ = _max_cycle_weight(sequence)
    if maximum > inst["cycle_bound"]:
        return False, (
            f"cycle bound exceeded: maximum weight {maximum} > {inst['cycle_bound']}"
        )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    items = _item_indices(inst)
    rng.shuffle(items)
    groups = [items[i : i + 3] for i in range(0, len(items), 3)]
    for group in groups:
        rng.shuffle(group)
    rng.shuffle(groups)
    return groups


def search_space(inst: dict) -> int | None:
    n = inst["n"]
    return math.factorial(3 * n) // (math.factorial(3) ** n * math.factorial(n))


def enumerate_all(inst: dict) -> int | None:
    if inst["n"] > 7:
        return None
    triples, incident = _exact_triples(inst)
    items = _item_indices(inst)
    triple_sets = [set(triple) for triple in triples]
    full = set(items)
    nodes = 0
    cap = 2_000_000

    def count(used: set[int]) -> int | None:
        nonlocal nodes
        nodes += 1
        if nodes > cap:
            return None
        if used == full:
            return 1
        pivot = min(full - used)
        total = 0
        for triple_id in incident[pivot]:
            triple = triple_sets[triple_id]
            if triple & used:
                continue
            subtotal = count(used | triple)
            if subtotal is None:
                return None
            total += subtotal
        return total

    return count(set())


def canonical_key(inst: dict) -> str:
    canonical = {
        "n": inst["n"],
        "target": inst["target"],
        "cycle_bound": inst["cycle_bound"],
        "columns": sorted(tuple(row) for row in inst["columns"]),
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _reorder_instance(inst: dict, order: list[int]) -> tuple[dict, list[list[int]]]:
    """Relabel columns by input reordering and carry a witness through the map."""
    if sorted(order) != list(range(len(inst["columns"]))):
        raise ValueError("order must be a permutation")
    old_to_new = {old: new for new, old in enumerate(order)}
    moved = {key: value for key, value in inst.items() if key != "answer"}
    moved["columns"] = [inst["columns"][old] for old in order]
    carried = [[old_to_new[index] for index in group] for group in inst["answer"]]
    moved["answer"] = carried
    return moved, carried


def escalate(params: dict) -> dict | str | None:
    p = {key: value for key, value in params.items() if key != "_preset"}
    nodes = int(p.get("filter_nodes", 0))
    restarts = int(p.get("random_restarts", 64))
    n = int(p["n"])
    # First condition the same-size answer against a stronger exact solver and
    # more random restarts: a fixed-length hardness axis.
    if nodes < 800_000:
        p["filter_nodes"] = max(10_000, nodes * 2)
        p["random_restarts"] = min(2_048, max(restarts + 64, restarts * 2))
        return p
    # Only after exhausting conditioning do we lengthen the certificate.
    if n < 85:
        p["n"] = min(85, n + max(4, n // 8))
        return p
    return "cap_bound"


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    return len(encoded), math.ceil(len(encoded) / 4), atoms(answer)


def selftest() -> dict:
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures: list[str] = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                restored = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if restored != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON round-trip changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]
    flat = [index for group in answer for index in group]

    wrong_sum = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            for a in range(3):
                for b in range(3):
                    trial = [group[:] for group in answer]
                    trial[i][a], trial[j][b] = trial[j][b], trial[i][a]
                    if verify(ship, trial)[1].startswith("wrong target sum"):
                        wrong_sum = trial
                        break
                if wrong_sum is not None:
                    break
            if wrong_sum is not None:
                break
        if wrong_sum is not None:
            break
    if wrong_sum is None:
        raise AssertionError("could not construct a sum corruption")

    anchor = next(index for index in range(len(ship["columns"])) if index not in set(flat))
    corruptions = {
        "empty": [],
        "drop_group": answer[:-1],
        "drop_element": [answer[0][:-1]] + [group[:] for group in answer[1:]],
        "duplicate": [[answer[0][0], answer[0][0], answer[0][2]]] + [group[:] for group in answer[1:]],
        "out_of_range": [[len(ship["columns"]), answer[0][1], answer[0][2]]] + [group[:] for group in answer[1:]],
        "anchor": [[anchor, answer[0][1], answer[0][2]]] + [group[:] for group in answer[1:]],
        "swap": wrong_sum,
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    reasons = [row["reason"] for row in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The item columns form the required exact cover.\n"
        "<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\nThe pseudo-grid bound follows."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer
        and verify(ship, parsed)[0]
        and parse_answer("unrelated garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("unrelated garbage") is None,
    }

    guess_rng = random.Random(0x160901266)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform set partitions of all item indices into unlabeled triples",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_value_bands",
        "greedy_largest_exact_pair",
        "random_restart_exact_triples",
        "algorithm_x_mrv_exact_cover",
    )
    attacks = {
        name: {
            "successes": 0,
            "attempts": 0,
            "operations": 0,
            "nodes": 0,
            "wall_clock_sec": 0.0,
        }
        for name in attack_names
    }
    for seed in range(800, 808):
        current = make_instance(seed=seed, **shipping)

        start = time.perf_counter()
        candidate = _attack_value_bands(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[0]]
        row["attempts"] += 1
        row["successes"] += int(verify(current, candidate)[0])
        row["operations"] += 3 * current["n"]
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate = _attack_greedy_exact_sum(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[1]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += (3 * current["n"]) ** 2
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, steps = _attack_random_restart(
            current,
            random.Random(_mix_seed(seed ^ 0xBEEF, 0)),
            int(shipping["random_restarts"]),
        )
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[2]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += steps
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, nodes, checks = _attack_exact_cover_mrv(
            current, int(shipping["filter_nodes"])
        )
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[3]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += checks
        row["nodes"] += nodes
        row["wall_clock_sec"] += elapsed

    for row in attacks.values():
        row["wall_clock_sec"] = round(row["wall_clock_sec"], 6)
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": "algorithm_x_mrv_exact_cover",
        "domain_standard_complexity": "exponential worst case; MRV Algorithm-X search",
        "construction_aware_attacks": [
            "outlier_value_bands",
            "greedy_largest_exact_pair",
            "random_restart_exact_triples",
        ],
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline = attacks["algorithm_x_mrv_exact_cover"]
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0 and demo_count is not None and demo_count > 0 and all_failed,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "demo_n": demo["n"],
        "strongest_attack": "algorithm_x_mrv_exact_cover",
        "strongest_attack_wall_clock_sec": baseline["wall_clock_sec"],
        "strongest_attack_nodes": baseline["nodes"],
        "strongest_attack_option_checks": baseline["operations"],
    }

    ladder = []
    for name, params in DIFFICULTY.items():
        sample = make_instance(seed=2, **params)
        ladder.append(
            {
                "preset": name,
                "n": sample["n"],
                "filter_nodes": sample["filter_nodes"],
                "space": search_space(sample),
            }
        )
    doubled_params = {
        "n": min(85, 2 * int(shipping["n"])),
        "filter_nodes": int(shipping["filter_nodes"]),
        "random_restarts": int(shipping["random_restarts"]),
    }
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    harder_fixed = escalate(shipping)
    report["G7_scales"] = {
        "pass": doubled_ok
        and isinstance(harder_fixed, dict)
        and harder_fixed["n"] == shipping["n"]
        and harder_fixed["filter_nodes"] > shipping["filter_nodes"]
        and all(ladder[i]["space"] < ladder[i + 1]["space"] for i in range(3)),
        "ladder": ladder,
        "fixed_length_escalation": harder_fixed,
        "size_doubled_params": doubled_params,
        "size_doubled_verifies": doubled_ok,
        "size_doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    failures: list[str] = []
    unrelated_keys: list[str] = []
    symmetry_params = {"n": 12, "filter_nodes": 0, "random_restarts": 0}
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **symmetry_params)
        base_key = canonical_key(original)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        order = list(range(len(original["columns"])))
        rng.shuffle(order)
        moved, carried = _reorder_instance(original, order)
        # Compose a second independent reordering with the first.
        order2 = list(range(len(moved["columns"])))
        rng.shuffle(order2)
        moved2, carried2 = _reorder_instance(moved, order2)
        for number, (variant, witness) in enumerate(
            ((moved, carried), (moved2, carried2))
        ):
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(variant, witness)[0]:
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
            "arbitrary input-column reordering",
            "composition of two independent input-column reorderings",
        ],
        "key_definition": "SHA-256 of the sorted tuple multiset and scalar MCW parameters",
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = 2 * ship["n"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
