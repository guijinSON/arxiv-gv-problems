"""Verified problem generator for arXiv:1207.0255.

Klavik, Kratochvil, Otachi and Saitoh prove in Theorem 3 that extending a
partial interval representation in a fixed host path is NP-complete.  Their
reduction makes one pre-drawn singleton at each boundary of an equal-sized
gap and one unlocated path component for every 3-PARTITION item.

This module instantiates those native objects.  It inverse-generates a legal
packing, turns item sizes into the paper's path components, and asks for a
compact placement table describing where the components go.  The generated distribution
has a deliberately hidden affine residue structure, so this is honestly Track
B: an efficient exact-triple algorithm exists and is measured below, while a
solver that notices the residue invariant can avoid its quadratic table.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "For q squared equal to M/12, the three component-length bands modulo q "
    "are affine copies of one common tag set."
)
PLACEBO_HINT: str = (
    "The component labels and fixed-path coordinates should be tracked "
    "carefully when assembling one complete extension."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "fixed host path",
        "partially represented interval graph",
        "pre-drawn singleton subpaths",
        "unlocated path components",
    ],
    "verification_operations": [
        "exact integer gap and rank checks",
        "exact component-span addition",
        "positive path-length check",
        "symbolic endpoint arithmetic for consecutive closed subpaths",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.3, Theorem 3 (3-PARTITION to RepExt(INT,Fixed))"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The component lengths in the three forced size bands carry affine "
        "copies of the same residue tags; without recognizing them, a solver "
        "must tabulate exact complementary pairs."
    ),
    "hardness_basis": (
        "Track B: an affine-residue decoder solves the promised distribution in "
        "expected O(n) time, while the domain-standard quadratic exact-triple "
        "table plus Algorithm X (exponential in the worst case) is the mechanical "
        "baseline; at shipping n=30,q=1009 the baseline examines 900 cross-band "
        "pairs per instance and used 42,605 primitive checks and 248 search nodes "
        "across eight instances in 0.062572 seconds; the efficient decoder solved "
        "8/8 in 1,232 counted operations and 0.049525 seconds, while the compact "
        "route uses at most 182 exact arithmetic operations after noticing the "
        "invariant."
    ),
    "max_answer_tokens": 151,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "q": 101, "noise_span": 3, "screen_restarts": 0},
    "easy": {"n": 18, "q": 1009, "noise_span": 4, "screen_restarts": 64},
    "medium": {"n": 30, "q": 1009, "noise_span": 4, "screen_restarts": 128},
    "hard": {"n": 42, "q": 1009, "noise_span": 4, "screen_restarts": 256},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A 3n-row integer placement table. Row i is [gap, rank] for take "
        "component T_i; gaps are 0..n-1, ranks are 0..2, every (gap,rank) "
        "slot occurs exactly once, and each gap receives one component from "
        "each of the three size bands."
    ),
    "bounds": {
        "rows": "3n",
        "columns": 2,
        "shipping_n": 30,
        "shipping_atomic_elements": 180,
        "gap_min": 0,
        "gap_max_at_shipping": 29,
        "rank_min": 0,
        "rank_max": 2,
    },
}

NOTES: str = (
    "Section 1.2 fixes the exact four host-tree modification types; this family "
    "uses Fixed, so no subdivision or added branch is allowed. Section 2 says "
    "connected components occupy disjoint areas and distinguishes located from "
    "unlocated components. Lemma 6 proves minspan(P_a)=a for interval graphs. "
    "Theorem 3 then uses singleton split gadgets at p_(M+1)i and unlocated take "
    "gadgets P_A to make extension equivalent to packing exactly three components "
    "of total span M into every gap; because the search is carried by this explicit "
    "paper reduction, the profile is licensed_reduction rather than native. The "
    "easy regimes deliberately avoided are "
    "Recog*(INT,Fixed), linear by Proposition 1; RepExt(INT,Sub), linear by "
    "Theorem 2; instances with all components located, linear as noted in "
    "Section 3.4; and bounded host-path size, FPT by Proposition 5. A pilot of "
    "ordinary inverse-generated 3-PARTITION was solved immediately by exact-cover "
    "search, so this module makes the distribution explicitly Track B instead of "
    "claiming average-case hardness. Rank-zipping, largest-first pairing, randomized "
    "residue-blind exact-pair restarts, and adjacent-size grouping are screened; the "
    "successful generic Algorithm X reference is reported separately."
)


# Updated from the script-owned oracle transcripts after all three runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 2, "error_redraws": 4},
    "placebo": {"solved": 0, "attempts": 0, "error_redraws": 4},
    "hinted_verdict": "incomplete: quota exhausted after 2/3 completed attempts",
}


def _mix_seed(seed: int, nonce: int) -> int:
    x = (int(seed) & ((1 << 64) - 1)) ^ 0x12070255A5A55A5A
    x = (x + (nonce + 1) * 0x9E3779B97F4A7C15) & ((1 << 128) - 1)
    x ^= x >> 30
    x *= 0xBF58476D1CE4E5B9
    x ^= x >> 27
    return x & ((1 << 128) - 1)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    factor = 3
    while factor * factor <= value:
        if value % factor == 0:
            return False
        factor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(5, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _bands(inst: dict) -> tuple[list[int], list[int], list[int]]:
    """Return the three size bands, a constraint visible from the statement."""
    q2 = inst["target"] // 12
    lower_cut = 7 * q2 // 2
    upper_cut = 9 * q2 // 2
    low: list[int] = []
    middle: list[int] = []
    high: list[int] = []
    for index, size in enumerate(inst["sizes"]):
        if size < lower_cut:
            low.append(index)
        elif size < upper_cut:
            middle.append(index)
        else:
            high.append(index)
    return low, middle, high


def _assignment_from_groups(inst: dict, groups: list[list[int]]) -> list[list[int]] | None:
    if len(groups) != inst["n"]:
        return None
    answer = [[-1, -1] for _ in inst["sizes"]]
    seen: set[int] = set()
    for gap, group in enumerate(groups):
        if len(group) != 3:
            return None
        for rank, component in enumerate(group):
            if (
                not isinstance(component, int)
                or isinstance(component, bool)
                or component < 0
                or component >= len(answer)
                or component in seen
            ):
                return None
            seen.add(component)
            answer[component] = [gap, rank]
    if len(seen) != len(answer):
        return None
    return answer


def _promise_residue_decoder(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Solve this module's promised distribution without reading ``answer``.

    This is the efficient algorithm whose existence makes the family Track B.
    The low and middle bands expose tag ``t`` as A mod q; the high band exposes
    it as -2t mod q.  Hashing gives expected linear time (sorting the tagged
    records instead gives deterministic O(n log n)).
    """
    q2 = inst["target"] // 12
    q = math.isqrt(q2)
    operations = 2
    if q * q != q2 or not _is_prime(q):
        return None, operations + 1
    low, middle, high = _bands(inst)
    tagged: list[dict[int, int]] = [{}, {}, {}]
    for component in low:
        tag = inst["sizes"][component] % q
        operations += 1
        if tag in tagged[0]:
            return None, operations
        tagged[0][tag] = component
    for component in middle:
        tag = inst["sizes"][component] % q
        operations += 1
        if tag in tagged[1]:
            return None, operations
        tagged[1][tag] = component
    inverse_two = (q + 1) // 2
    operations += 2
    for component in high:
        tag = (-(inst["sizes"][component] % q) * inverse_two) % q
        operations += 3
        if tag in tagged[2]:
            return None, operations
        tagged[2][tag] = component
    if any(set(band) != set(range(inst["n"])) for band in tagged):
        return None, operations
    groups = [
        [tagged[0][tag], tagged[1][tag], tagged[2][tag]]
        for tag in range(inst["n"])
    ]
    return _assignment_from_groups(inst, groups), operations


def _raw_instance(n: int, q: int, noise_span: int, seed: int, nonce: int) -> dict:
    """Inverse-generate tags/groups before constructing the paper's graph."""
    rng = random.Random(_mix_seed(seed, nonce))
    q2 = q * q
    target = 12 * q2
    records: list[tuple[int, int, int]] = []
    for tag in range(n):
        u = rng.randint(1, noise_span)
        v = rng.randint(1, noise_span)
        low = 3 * q2 + q * u + tag
        middle = 4 * q2 + q * v + tag
        high = target - low - middle
        records.extend(((low, tag, 0), (middle, tag, 1), (high, tag, 2)))
    rng.shuffle(records)

    sizes = [record[0] for record in records]
    # The certificate is carried directly from the pre-sampled tags and roles.
    answer = [[record[1], record[2]] for record in records]
    return {
        "paper": "arXiv:1207.0255",
        "family": "RepExt(INT, Fixed), Theorem-3 split/take instances",
        "n": n,
        "target": target,
        "path_last_vertex": (target + 1) * n,
        "sizes": sizes,
        "answer": answer,
        "selection_attempts": nonce + 1,
    }


def _valid_fast(inst: dict, answer: object) -> bool:
    return verify(inst, answer)[0]


def _attack_band_rank_zip(inst: dict) -> list[list[int]] | None:
    low, middle, high = _bands(inst)
    key = lambda index: (inst["sizes"][index], index)
    low.sort(key=key)
    middle.sort(key=key)
    high.sort(key=key, reverse=True)
    return _assignment_from_groups(
        inst, [[low[i], middle[i], high[i]] for i in range(inst["n"])]
    )


def _exact_pair_table(inst: dict) -> tuple[list[int], list[int], list[int], dict[int, list[tuple[int, int]]], int]:
    low, middle, high = _bands(inst)
    table: dict[int, list[tuple[int, int]]] = {}
    operations = 0
    for left in low:
        for right in middle:
            operations += 1
            table.setdefault(inst["sizes"][left] + inst["sizes"][right], []).append(
                (left, right)
            )
    return low, middle, high, table, operations


def _attack_largest_first(inst: dict) -> tuple[list[list[int]] | None, int]:
    low, middle, high, table, operations = _exact_pair_table(inst)
    unused_low = set(low)
    unused_middle = set(middle)
    groups: list[list[int]] = []
    for top in sorted(high, key=lambda i: (inst["sizes"][i], i), reverse=True):
        operations += 1
        choices = table.get(inst["target"] - inst["sizes"][top], ())
        available = [pair for pair in choices if pair[0] in unused_low and pair[1] in unused_middle]
        operations += len(choices)
        if not available:
            return None, operations
        left, right = min(
            available,
            key=lambda pair: (
                abs(inst["sizes"][pair[0]] - inst["sizes"][pair[1]]),
                pair,
            ),
        )
        unused_low.remove(left)
        unused_middle.remove(right)
        groups.append([left, right, top])
    return _assignment_from_groups(inst, groups), operations


def _attack_random_exact_pairs(
    inst: dict, rng: random.Random, restarts: int
) -> tuple[list[list[int]] | None, int]:
    low, middle, high, table, operations = _exact_pair_table(inst)
    for _ in range(restarts):
        unused_low = set(low)
        unused_middle = set(middle)
        unused_high = set(high)
        groups: list[list[int]] = []
        while unused_high:
            top = rng.choice(tuple(sorted(unused_high)))
            operations += 1
            choices = table.get(inst["target"] - inst["sizes"][top], ())
            available = [pair for pair in choices if pair[0] in unused_low and pair[1] in unused_middle]
            operations += len(choices)
            if not available:
                break
            left, right = rng.choice(available)
            unused_low.remove(left)
            unused_middle.remove(right)
            unused_high.remove(top)
            groups.append([left, right, top])
        if not unused_high:
            return _assignment_from_groups(inst, groups), operations
    return None, operations


def _attack_adjacent_sizes(inst: dict) -> list[list[int]] | None:
    ordered = sorted(range(len(inst["sizes"])), key=lambda i: (inst["sizes"][i], i))
    groups = [ordered[pos : pos + 3] for pos in range(0, len(ordered), 3)]
    return _assignment_from_groups(inst, groups)


def _reference_algorithm_x(
    inst: dict,
) -> tuple[list[list[int]] | None, int, int, int]:
    """Generate all exact triples and solve their exact cover by Algorithm X.

    This deliberately does not use the planted residues.  The quadratic pair
    table is the standard reduction of the promised three-band 3-PARTITION
    instance to exact cover; choosing a least-degree uncovered component is the
    usual Algorithm X branching rule.  The returned counters are, respectively,
    counted primitive operations, search nodes, and candidate triples.
    """
    low, middle, high, table, operations = _exact_pair_table(inst)
    triples: list[tuple[int, int, int]] = []
    incident: dict[int, list[int]] = {
        component: [] for component in range(len(inst["sizes"]))
    }
    for top in high:
        operations += 1
        for left, middle_component in table.get(
            inst["target"] - inst["sizes"][top], ()
        ):
            triple_index = len(triples)
            triples.append((left, middle_component, top))
            incident[left].append(triple_index)
            incident[middle_component].append(triple_index)
            incident[top].append(triple_index)
            operations += 4

    unused = set(range(len(inst["sizes"])))
    groups: list[list[int]] = []
    nodes = 0

    def search() -> bool:
        nonlocal nodes, operations
        nodes += 1
        operations += 1
        if not unused:
            return True

        best_options: list[int] | None = None
        for component in sorted(unused):
            options: list[int] = []
            for triple_index in incident[component]:
                operations += 3
                if all(member in unused for member in triples[triple_index]):
                    options.append(triple_index)
            operations += 1
            if not options:
                return False
            if best_options is None or len(options) < len(best_options):
                best_options = options
                if len(options) == 1:
                    break

        if best_options is None:  # pragma: no cover - unused is nonempty above
            return False
        for triple_index in best_options:
            triple = triples[triple_index]
            operations += 3
            if any(member not in unused for member in triple):
                continue
            for member in triple:
                unused.remove(member)
            groups.append(list(triple))
            if search():
                return True
            groups.pop()
            unused.update(triple)
        return False

    if not search():
        return None, operations, nodes, len(triples)
    return _assignment_from_groups(inst, groups), operations, nodes, len(triples)


def _passes_screen(inst: dict, seed: int, nonce: int, restarts: int) -> bool:
    if restarts <= 0:
        return True
    candidate = _attack_band_rank_zip(inst)
    if candidate is not None and _valid_fast(inst, candidate):
        return False
    candidate, _ = _attack_largest_first(inst)
    if candidate is not None and _valid_fast(inst, candidate):
        return False
    candidate, _ = _attack_random_exact_pairs(
        inst,
        random.Random(_mix_seed(seed ^ 0xBADC0DE, nonce)),
        restarts,
    )
    if candidate is not None and _valid_fast(inst, candidate):
        return False
    candidate = _attack_adjacent_sizes(inst)
    return candidate is None or not _valid_fast(inst, candidate)


def make_instance(
    n: int,
    seed: int = 0,
    q: int = 1009,
    noise_span: int = 4,
    screen_restarts: int = 0,
    **params: Any,
) -> dict:
    """Build a fixed-path partial interval representation by inverse generation.

    The tagged packing is sampled before the graph sizes are constructed.  The
    optional screen merely rejects instances solved by bounded cheap attacks;
    none of those attacks supplies or changes the retained certificate.
    """
    del params
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if not isinstance(q, int) or isinstance(q, bool) or not _is_prime(q):
        raise ValueError("q must be prime")
    if q <= 4 * n + 3:
        raise ValueError("q must exceed 4n+3 so the affine residues do not wrap")
    if not isinstance(noise_span, int) or noise_span < 1 or noise_span >= q // 8:
        raise ValueError("noise_span must be an integer in [1,q/8)")
    if not isinstance(screen_restarts, int) or screen_restarts < 0:
        raise ValueError("screen_restarts must be a nonnegative integer")

    for nonce in range(4096):
        inst = _raw_instance(n, q, noise_span, seed, nonce)
        if _passes_screen(inst, seed, nonce, screen_restarts):
            inst["screen_restarts"] = screen_restarts
            return inst
    raise RuntimeError("could not generate an instance defeating the bounded attack screen")


def render(inst: dict) -> str:
    n = inst["n"]
    target = inst["target"]
    lines = [
        "Extend this partial interval representation in its fixed host path.",
        "",
        "Definitions.",
        "A subpath [a,b] is the nonempty set of host vertices p_a,p_(a+1),...,p_b, with integer endpoints 0 <= a <= b.",
        "An interval representation assigns one subpath to every graph vertex; two distinct graph vertices must be adjacent exactly when their assigned subpaths intersect.",
        "The host path is fixed: it may not be subdivided and no vertices or branches may be added.",
        "",
        f"Here n={n} and M={target}. The fixed host path has vertices p_0 through p_{inst['path_last_vertex']}.",
        f"The graph is the disjoint union of split vertices s_0,...,s_{n} and {3*n} take components T_0,...,T_{3*n-1}.",
        f"Only split vertices are pre-drawn: s_j is the singleton subpath [{target+1}*j,{target+1}*j] for every j=0,...,{n}.",
        "Take component T_i is a path with A_i edges and labelled graph vertices x_(i,0),...,x_(i,A_i); its A_i is listed below. No vertex of a take component is pre-drawn.",
        "Thus gap g is the M host vertices strictly between s_g and s_(g+1), namely coordinates (M+1)g+1 through (M+1)g+M, inclusive.",
        "",
        "Output a compact placement table with one row [g,r] for each T_i, in increasing i order. Here g is its 0-based gap and r is its 0-based left-to-right rank in that gap.",
        "Every gap must use ranks 0,1,2 exactly once. The checker packs those three components without empty coordinates, in rank order.",
        "If a component with A edges starts at coordinate h, the checker assigns x_(i,0)=[h,h], x_(i,A)=[h+A-1,h+A-1], and each x_(i,j)=[h+j-1,h+j] for 0<j<A.",
        "This is a full, deterministic interval representation: the three component areas must fill their gap exactly, may not touch a split coordinate, and areas in different components are disjoint.",
        "",
        "Component sizes, as i: A_i:",
    ]
    for index, size in enumerate(inst["sizes"]):
        lines.append(f"{index}: {size}")
    lines.extend(
        [
            "",
            f"Give your final answer inside <answer></answer> tags as a JSON array of exactly {3*n} two-integer rows [gap,rank], in T_i order.",
            "Example: <answer>[[0,1],[1,0],[0,2],[0,0],[1,2],[1,1]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(("", "Hint: " + STRUCTURAL_HINT))
    elif mode == "placebo":
        lines.extend(("", "Hint: " + PLACEBO_HINT))
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    def decode(raw: str) -> object | None:
        body = raw.strip()
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
        tagged = re.findall(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        for raw in reversed(tagged):
            value = decode(raw)
            if value is not None:
                return value
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
        for raw in reversed(fenced):
            value = decode(raw)
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


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    count = 3 * inst["n"]
    if not isinstance(answer, list):
        return False, "malformed: expected a JSON placement table"
    if not answer:
        return False, "empty: the placement table has no rows"
    if len(answer) != count:
        return False, f"wrong row count: expected {count}, got {len(answer)}"

    slots = [-1] * count
    for component, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 2:
            return False, f"wrong row shape: row {component} must be [gap,rank]"
        gap, rank = row
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in row):
            return False, f"non-integer entry: row {component} contains a non-integer"
        if gap < 0 or gap >= inst["n"] or rank < 0 or rank >= 3:
            return False, f"out of range: row {component} has gap/rank [{gap},{rank}]"
        slot = 3 * gap + rank
        if slots[slot] != -1:
            return False, (
                f"duplicate slot: components {slots[slot]} and {component} both use "
                f"[{gap},{rank}]"
            )
        slots[slot] = component

    # Uniqueness plus the exact row count implies that every slot is present.
    for gap in range(inst["n"]):
        components = slots[3 * gap : 3 * gap + 3]
        total = sum(inst["sizes"][component] for component in components)
        if total != inst["target"]:
            return False, (
                f"capacity mismatch: gap {gap} receives total span {total}, "
                f"not M={inst['target']}"
            )

        if any(inst["sizes"][component] < 1 for component in components):
            return False, f"invalid instance: gap {gap} contains a component with no edge"

        # Symbolically reconstruct the three consecutive component areas. Their
        # final coordinate is base+sum(A_i). Because every A_i is positive, the
        # areas are nonempty, pairwise disjoint, and avoid both split coordinates.
        # The displayed local interval formula then makes x_j meet exactly its
        # path neighbours. This checks every adjacency without iterating over the
        # millions of graph vertices represented by the compact path notation.
        base = (inst["target"] + 1) * gap
        previous_right = base + total
        expected_right = (inst["target"] + 1) * gap + inst["target"]
        if previous_right != expected_right:
            return False, f"gap not filled: gap {gap} ends at {previous_right}"

    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    # Exact sums force one component from each visible size band into every gap.
    # Sample uniformly after incorporating that freely deducible constraint.
    bands = [list(band) for band in _bands(inst)]
    for band in bands:
        rng.shuffle(band)
    groups: list[list[int]] = []
    permutations = (
        (0, 1, 2),
        (0, 2, 1),
        (1, 0, 2),
        (1, 2, 0),
        (2, 0, 1),
        (2, 1, 0),
    )
    for gap in range(inst["n"]):
        raw = (bands[0][gap], bands[1][gap], bands[2][gap])
        order = permutations[rng.randrange(6)]
        groups.append([raw[order[0]], raw[order[1]], raw[order[2]]])
    answer = _assignment_from_groups(inst, groups)
    if answer is None:  # pragma: no cover - guarded by construction
        raise AssertionError("candidate sampler produced an invalid shape")
    return answer


def search_space(inst: dict) -> int | None:
    n = inst["n"]
    return math.factorial(n) ** 3 * (math.factorial(3) ** n)


def enumerate_all(inst: dict) -> int | None:
    if inst["n"] > 7:
        return None
    low, middle, high, table, _ = _exact_pair_table(inst)
    target = inst["target"]
    by_high: dict[int, list[tuple[int, int]]] = {
        top: list(table.get(target - inst["sizes"][top], ())) for top in high
    }
    nodes = 0
    cap = 2_000_000

    def count(unused_low: frozenset[int], unused_middle: frozenset[int], unused_high: frozenset[int]) -> int | None:
        nonlocal nodes
        nodes += 1
        if nodes > cap:
            return None
        if not unused_high:
            return 1
        best_top = min(
            unused_high,
            key=lambda top: sum(
                left in unused_low and right in unused_middle
                for left, right in by_high[top]
            ),
        )
        total = 0
        for left, right in by_high[best_top]:
            if left not in unused_low or right not in unused_middle:
                continue
            subtotal = count(
                unused_low - {left},
                unused_middle - {right},
                unused_high - {best_top},
            )
            if subtotal is None:
                return None
            total += subtotal
        return total

    covers = count(frozenset(low), frozenset(middle), frozenset(high))
    if covers is None:
        return None
    # A cover's triples may be assigned to labeled gaps in n! ways, with 3!
    # left-to-right component orders independently inside each gap.
    return covers * math.factorial(inst["n"]) * (math.factorial(3) ** inst["n"])


def canonical_key(inst: dict) -> str:
    canonical = {
        "n": inst["n"],
        "target": inst["target"],
        "host_last": inst["path_last_vertex"],
        "take_path_lengths": sorted(inst["sizes"]),
        "split_positions": [
            (inst["target"] + 1) * gap for gap in range(inst["n"] + 1)
        ],
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _permute_components(inst: dict, order: list[int]) -> tuple[dict, list[list[int]]]:
    if sorted(order) != list(range(len(inst["sizes"]))):
        raise ValueError("order must be a component permutation")
    moved = copy.deepcopy(inst)
    moved["sizes"] = [inst["sizes"][old] for old in order]
    carried = [inst["answer"][old][:] for old in order]
    moved["answer"] = carried
    return moved, carried


def _reflect_host(inst: dict, answer: list[list[int]]) -> list[list[int]]:
    # Reflect gaps and ranks. Reversing each path's vertex labels is a graph
    # automorphism and returns the canonical left-to-right local representation.
    return [[inst["n"] - 1 - gap, 2 - rank] for gap, rank in answer]


def escalate(params: dict) -> dict | str | None:
    p = {key: value for key, value in params.items() if key != "_preset"}
    # Grow coefficient height and screening at fixed certificate length first.
    q = int(p.get("q", 1009))
    p["q"] = _next_prime(10 * q + 1)
    p["screen_restarts"] = min(
        4096, max(64, 2 * int(p.get("screen_restarts", 0)))
    )
    return p


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, list):
            return sum(atoms(item) for item in value)
        return 1

    return len(encoded), math.ceil(len(encoded) / 4), atoms(answer)


def selftest() -> dict:
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures: list[str] = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            try:
                restored = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if restored != inst["answer"]:
                    failures.append(f"{preset}/{seed}: JSON round-trip changed answer")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]
    swapped = None
    for left in range(len(answer)):
        for right in range(left + 1, len(answer)):
            trial = [row[:] for row in answer]
            trial[left], trial[right] = trial[right], trial[left]
            ok, reason = verify(ship, trial)
            if not ok and reason.startswith("capacity mismatch"):
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("could not construct a capacity corruption")

    corruptions: dict[str, object] = {
        "empty": [],
        "drop_row": answer[:-1],
        "drop_element": [answer[0][:-1]] + [row[:] for row in answer[1:]],
        "duplicate": [answer[0][:], answer[0][:]] + [row[:] for row in answer[2:]],
        "out_of_range": [[ship["n"], answer[0][1]]] + [row[:] for row in answer[1:]],
        "non_integer": [[str(answer[0][0]), answer[0][1]]] + [row[:] for row in answer[1:]],
        "swap": swapped,
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
        "The following placement fills every open gap.\n<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\nThe canonical subpaths now give the extension."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer
        and verify(ship, parsed)[0]
        and parse_answer("unrelated garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("unrelated garbage") is None,
    }

    guess_rng = random.Random(0x12070255)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": (
            "uniform independent assignments of each visible size band to labeled "
            "gaps, with a uniform rank permutation inside every gap"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_band_rank_zip",
        "greedy_largest_first",
        "random_restart_exact_pairs_256",
        "by_hand_adjacent_sizes",
    )
    attacks = {
        name: {
            "successes": 0,
            "attempts": 0,
            "operations": 0,
            "wall_clock_sec": 0.0,
        }
        for name in attack_names
    }
    reference = {
        "name": "quadratic exact-triple generation plus generic Algorithm X",
        "complexity": "O(n^2) candidate generation plus exponential worst-case exact-cover search",
        "successes": 0,
        "attempts": 0,
        "operations": 0,
        "operation_samples": [],
        "search_nodes": 0,
        "candidate_triples": 0,
        "wall_clock_sec": 0.0,
    }
    promise_algorithm = {
        "name": "affine-residue decoder for the generated promise",
        "complexity": "expected O(n) with hash tables; deterministic O(n log n) by sorting",
        "successes": 0,
        "attempts": 0,
        "operations": 0,
        "operation_samples": [],
        "wall_clock_sec": 0.0,
    }
    for seed in range(800, 808):
        current = make_instance(seed=seed, **shipping)

        started = time.perf_counter()
        candidate = _attack_band_rank_zip(current)
        elapsed = time.perf_counter() - started
        row = attacks[attack_names[0]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += 3 * current["n"]
        row["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, operations = _attack_largest_first(current)
        elapsed = time.perf_counter() - started
        row = attacks[attack_names[1]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, operations = _attack_random_exact_pairs(
            current, random.Random(_mix_seed(seed ^ 0x515151, 0)), 256
        )
        elapsed = time.perf_counter() - started
        row = attacks[attack_names[2]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate = _attack_adjacent_sizes(current)
        elapsed = time.perf_counter() - started
        row = attacks[attack_names[3]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += 3 * current["n"]
        row["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, operations, nodes, candidates = _reference_algorithm_x(current)
        elapsed = time.perf_counter() - started
        reference["attempts"] += 1
        reference["successes"] += int(candidate is not None and verify(current, candidate)[0])
        reference["operations"] += operations
        reference["operation_samples"].append(operations)
        reference["search_nodes"] += nodes
        reference["candidate_triples"] += candidates
        reference["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, operations = _promise_residue_decoder(current)
        elapsed = time.perf_counter() - started
        promise_algorithm["attempts"] += 1
        promise_algorithm["successes"] += int(
            candidate is not None and verify(current, candidate)[0]
        )
        promise_algorithm["operations"] += operations
        promise_algorithm["operation_samples"].append(operations)
        promise_algorithm["wall_clock_sec"] += elapsed

    for row in attacks.values():
        row["wall_clock_sec"] = round(row["wall_clock_sec"], 6)
    reference["wall_clock_sec"] = round(reference["wall_clock_sec"], 6)
    reference["solves"] = f"{reference['successes']}/{reference['attempts']}, as expected"
    promise_algorithm["wall_clock_sec"] = round(
        promise_algorithm["wall_clock_sec"], 6
    )
    promise_algorithm["solves"] = (
        f"{promise_algorithm['successes']}/{promise_algorithm['attempts']}, as expected"
    )
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference["successes"] == reference["attempts"]
        and promise_algorithm["successes"] == promise_algorithm["attempts"],
        "attacks": attacks,
        "reference_algorithm": reference,
        "efficient_promise_algorithm": promise_algorithm,
        "track_b_note": (
            "The successful reference is intentionally outside attacks; Track B "
            "claims no-tool compression, not absence of an efficient algorithm."
        ),
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest = attacks["random_restart_exact_pairs_256"]
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0
        and demo_count is not None
        and demo_count > 0
        and all_failed
        and reference["successes"] == reference["attempts"]
        and promise_algorithm["successes"] == promise_algorithm["attempts"],
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "demo_exact_valid_placements": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_n": demo["n"],
        "strongest_failing_attack": "random_restart_exact_pairs_256",
        "strongest_attack_wall_clock_sec": strongest["wall_clock_sec"],
        "strongest_attack_operations": strongest["operations"],
        "successful_reference_wall_clock_sec": reference["wall_clock_sec"],
        "successful_reference_operations": reference["operations"],
        "efficient_promise_wall_clock_sec": promise_algorithm["wall_clock_sec"],
        "efficient_promise_operations": promise_algorithm["operations"],
    }

    ladder = []
    for name, params in DIFFICULTY.items():
        sample = make_instance(seed=2, **params)
        ladder.append(
            {
                "preset": name,
                "n": sample["n"],
                "take_components": 3 * sample["n"],
                "q": params["q"],
                "candidate_space": search_space(sample),
            }
        )
    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * int(shipping["n"])
    doubled_params["q"] = _next_prime(max(int(shipping["q"]), 4 * doubled_params["n"] + 5))
    doubled_params["screen_restarts"] = 0
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    fixed_length_harder = escalate(shipping)
    report["G7_scales"] = {
        "pass": doubled_ok
        and isinstance(fixed_length_harder, dict)
        and fixed_length_harder["n"] == shipping["n"]
        and fixed_length_harder["q"] > shipping["q"]
        and all(
            ladder[index]["candidate_space"] < ladder[index + 1]["candidate_space"]
            for index in range(3)
        ),
        "ladder": ladder,
        "fixed_length_escalation": fixed_length_harder,
        "size_doubled_params": doubled_params,
        "size_doubled_verifies": doubled_ok,
        "size_doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    key_failures: list[str] = []
    unrelated_keys: list[str] = []
    symmetry_params = {"n": 12, "q": 1009, "noise_span": 4, "screen_restarts": 0}
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **symmetry_params)
        base_key = canonical_key(original)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        order = list(range(len(original["sizes"])))
        rng.shuffle(order)
        moved, carried = _permute_components(original, order)
        order2 = list(range(len(moved["sizes"])))
        rng.shuffle(order2)
        moved2, carried2 = _permute_components(moved, order2)
        reflected = _reflect_host(original, original["answer"])
        reflected_moved = _reflect_host(moved2, carried2)
        variants = (
            (moved, carried, "component permutation"),
            (moved2, carried2, "composed component permutations"),
            (original, reflected, "host reflection"),
            (moved2, reflected_moved, "permutations composed with reflection"),
        )
        for variant, witness, label in variants:
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                key_failures.append(f"key/{seed}/{label}")
            witness_checks += 1
            if not verify(variant, witness)[0]:
                key_failures.append(f"witness/{seed}/{label}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": key_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary relabeling/reordering of take components",
            "composition of two take-component relabelings",
            "reflection of the fixed host path with path-component reversal",
            "component relabelings composed with host reflection",
        ],
        "key_definition": (
            "SHA-256 of the sorted take-path length multiset, host size, target, "
            "and split-position sequence"
        ),
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    # q derivation: 2; 3n residues: 3n; high-band affine normalization:
    # 3n; writing each decoded tag into its gap: no arithmetic.
    intended_operations = 2 + 6 * ship["n"]
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else None
    )
    within_caps = (
        chars <= 2_000
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
        and elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps_only_gate": True,
    }

    report["all_gates_pass"] = all(
        isinstance(value, dict) and value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
