"""Verified generator for arXiv:2604.24325.

The generated problem is Identification to a given linear forest.  Every source
component is a path.  A certificate partitions the components into groups that
are chained by endpoint identifications to make the target paths.

Only the Python standard library is needed.  Importing this module performs no
I/O and consumes no global randomness.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

_REDUCTION = (
    "Section 3.1, Theorem 2, together with Section 3.3, Claim 6 "
    "(partition source path components by their diameters/lengths)"
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "linear forest specified by source path edge-counts",
        "linear forest of equal target paths",
        "path-component partition witness",
    ],
    "verification_operations": [
        "partition coverage check",
        "exact integer addition",
        "path-length equality",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Four magnitude bands are coupled by a mixed-radix linear invariant; "
        "without exposing it, a solver must mechanically enumerate complementary path pairs."
    ),
    "hardness_basis": (
        "Track B: 4SUM meet-in-the-middle plus exact-cover propagation uses "
        "O(s^2+z) expected work on s source paths and averaged 15,078.75 "
        "counted arithmetic/search operations (about 0.005 seconds) at shipping n=32 "
        "in an 8-seed audit; the executable mixed-radix inverse uses 294 exact "
        "arithmetic operations once the change of variables is recognized."
    ),
    "max_answer_tokens": 149,
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

DIFFICULTY = {
    "demo": {"n": 2, "tag_base": 4, "separation": 5},
    "easy": {"n": 8, "tag_base": 8, "separation": 15},
    "medium": {"n": 16, "tag_base": 7, "separation": 12},
    "hard": {"n": 32, "tag_base": 6, "separation": 10},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The within-band arithmetic progressions share a mixed-radix basis, and the "
    "lowest band encodes a linear mixture of the other three bands' ranks."
)
PLACEBO_HINT = (
    "The component indices and the path-length totals should both be checked "
    "carefully before the final partition is submitted."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A lexicographically sorted list of exactly n sorted 4-element lists that "
        "partition the source indices 0..4n-1; 2 <= n <= 4096."
    ),
    "bounds": {
        "max_groups": 4096,
        "group_size": 4,
        "max_source_paths": 16384,
        "ordered_groups": 1,
        "ordered_within_group": 1,
    },
}

# Patched from the three isolated harden.py runs.  They are diagnostic only;
# G9's gated part is the answer/operation cap.
G9_DIAGNOSTIC = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
}
G9_ORACLE_STATUS = "unreachable_http_403_key_total_limit"

NOTES = """
The exact definition is fixed by Section 1's H-witness structures and, for this
family, by Section 3.1 Theorem 2: disjoint source paths assigned to one target
path are chained at endpoints, so their edge-counts add.  Section 3.3 Claim 6
states the corresponding component-diameter partition criterion.  The easy
results that had to be avoided are Corollary 1 (target class is an unspecified
path/linear forest) and Lemma 6 (an XP dynamic program for a given linear forest
with a small number of target components).  Here the number of target components
grows, but every target receives exactly four source paths.  That restriction
admits an honest Track-B reference algorithm: enumerate complementary path pairs
by 4SUM, then propagate the resulting unique exact cover.

The generator samples three hidden permutations first and composes each answer
quartet through an invertible mixed-radix identity.  It never solves its output.
The tag equation forces one item from each magnitude band; the radix equation
then forces the three hidden ranks.  Random shuffling removes positional clues.
The adversaries test magnitude/rank outliers, first-fit decreasing, random
equipartitions, and a nearest-completion by-hand heuristic.  The reference 4SUM
algorithm is kept outside attacks, as Track B requires.
""".strip()


def _canonical_groups(groups):
    return sorted((sorted(g) for g in groups), key=lambda g: tuple(g))


def _mix_code(x, y, z, radix):
    """Encode R*(x,y,z), R=[[1,1,1],[1,2,1],[1,1,2]]."""
    w0 = x + y + z
    w1 = x + 2 * y + z
    w2 = x + y + 2 * z
    return w0 + radix * w1 + radix * radix * w2


def make_instance(n, seed=0, tag_base=6, separation=10, **params):
    """Construct a certified linear-forest identification instance.

    ``n`` is the number of target path components; there are 4n source paths.
    The answer is sampled first as three random permutations and carried through
    the mixed-radix construction and a final relabelling.
    """
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameter(s): {unknown}")
    if not isinstance(n, int) or not 2 <= n <= 4096:
        raise ValueError("n must be an integer in [2, 4096]")
    if not isinstance(tag_base, int) or tag_base < 4:
        raise ValueError("tag_base must be an integer at least 4")
    if not isinstance(separation, int) or separation < 5:
        raise ValueError("separation must be an integer at least 5")

    rng = random.Random(seed)

    # These three permutations ARE the sampled certificate.  All later work is
    # forward construction, never certificate search.
    px = list(range(n))
    py = list(range(n))
    pz = list(range(n))
    rng.shuffle(px)
    rng.shuffle(py)
    rng.shuffle(pz)

    # The radix is larger than every possible coordinate discrepancy in a
    # candidate one-of-each-band quartet.  Thus scalar equality implies equality
    # in all three mixed coordinates.
    radix = 4 * n + 1
    step_a = 1 + radix + radix * radix
    step_b = 1 + 2 * radix + radix * radix
    step_c = 1 + radix + 2 * radix * radix
    lower_cap = (n - 1) * (step_a + step_b + step_c)
    q = separation * lower_cap + 1

    # For b>=4, the only multiset of four tags from this set summing to zero is
    # one copy of each: base-b uniqueness gives 1+b+b^2, balanced by tag D.
    tag_a, tag_b, tag_c = 1, tag_base, tag_base * tag_base
    tag_d = -(tag_a + tag_b + tag_c)
    center = (4 * abs(tag_d) + 16) * q
    target = 4 * center

    records = []
    for x in range(n):
        records.append([center + tag_a * q + _mix_code(x, 0, 0, radix), "A", x])
    for y in range(n):
        records.append([center + tag_b * q + _mix_code(0, y, 0, radix), "B", y])
    for z in range(n):
        records.append([center + tag_c * q + _mix_code(0, 0, z, radix), "C", z])
    for g in range(n):
        code = _mix_code(px[g], py[g], pz[g], radix)
        records.append([center + tag_d * q - code, "D", g])

    # A global translation is a solution-preserving transformation because every
    # target uses exactly four source paths.  It prevents a fixed absolute origin
    # from becoming a clue; canonical_key removes this symmetry.
    translation = rng.randrange(q + 1)
    for rec in records:
        rec[0] += translation
    target += 4 * translation

    rng.shuffle(records)
    locations = {kind: {} for kind in "ABCD"}
    lengths = []
    for index, (length, kind, label) in enumerate(records):
        lengths.append(length)
        locations[kind][label] = index

    groups = []
    for g in range(n):
        groups.append([
            locations["A"][px[g]],
            locations["B"][py[g]],
            locations["C"][pz[g]],
            locations["D"][g],
        ])
    answer = _canonical_groups(groups)

    return {
        "family": "identification_to_equal_linear_forest",
        "n_targets": n,
        "group_size": 4,
        "source_path_lengths": lengths,
        "target_path_length": target,
        "identifications": 3 * n,
        "construction_bounds": {
            "tag_base": tag_base,
            "separation": separation,
        },
        "answer": answer,
    }


def render(inst):
    n = inst["n_targets"]
    lengths = inst["source_path_lengths"]
    target = inst["target_path_length"]
    rows = "\n".join(f"  {i}: {v}" for i, v in enumerate(lengths))
    text = f"""Identification to a given linear forest

A path P_L has L edges (and therefore L+1 vertices).  The source graph G is the
disjoint union of {len(lengths)} paths.  Source component i is P_L for the L on
line i below; indices are 0-based.

The target graph H is the disjoint union of {n} indistinguishable copies of
P_{target}.

One vertex identification replaces two vertices by one vertex adjacent to the
union of their former neighbours.  Your certificate must partition all source
components into {n} groups of exactly four.  A group [i0,i1,i2,i3] means: orient
those four paths by their natural vertex order and identify the right endpoint
of path i0 with the left endpoint of i1, then i1 with i2, then i2 with i3.  This
uses three identifications and makes one path whose edge-count is the sum of the
four displayed lengths.  Across all groups the certificate uses {3*n}
identifications and must produce H.

It is guaranteed that there is a unique unordered partition satisfying these
requirements.  No component may repeat or be omitted.  Within each group list
the four indices in strictly increasing order, and sort the list of groups
lexicographically.  Thus order carries no mathematical meaning but the output
has one canonical spelling.

Source path edge-counts:
{rows}

Required edge-count of every target path: {target}

Return JSON: an outer list of exactly {n} inner lists, each containing four
integers.  Example of syntax only for a hypothetical two-target instance:
<answer>[[0, 2, 5, 7], [1, 3, 4, 6]]</answer>"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    text += (
        "\n\nGive your final answer inside <answer></answer> tags in exactly that "
        "JSON format.\nOutput nothing else inside the tags."
    )
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(matches))
    if not candidates:
        candidates = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    for body in candidates:
        body = body.strip()
        body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body, flags=re.I | re.S)
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    # Deliberately never inspect inst["answer"].
    n = inst.get("n_targets")
    lengths = inst.get("source_path_lengths")
    target = inst.get("target_path_length")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"expected exactly {n} groups"
    if any(not isinstance(g, list) for g in answer):
        return False, "every group must be a JSON list"
    if any(len(g) != 4 for g in answer):
        return False, "every group must contain exactly four indices"
    flat = [v for g in answer for v in g]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in flat):
        return False, "every source index must be an integer"
    if any(v < 0 or v >= len(lengths) for v in flat):
        return False, "source index out of range"
    if len(set(flat)) != len(flat):
        return False, "a source index is repeated"
    if any(g != sorted(g) for g in answer):
        return False, "indices inside every group must be strictly increasing"
    if answer != sorted(answer, key=lambda g: tuple(g)):
        return False, "groups must be in lexicographic order"
    expected = set(range(len(lengths)))
    if set(flat) != expected:
        return False, "the groups do not cover every source component"
    for pos, group in enumerate(answer):
        total = sum(lengths[i] for i in group)
        if total != target:
            return False, f"group {pos} has edge-count {total}, not {target}"
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    indices = list(range(len(inst["source_path_lengths"])))
    rng.shuffle(indices)
    groups = [indices[i:i + 4] for i in range(0, len(indices), 4)]
    return _canonical_groups(groups)


def search_space(inst):
    n = inst["n_targets"]
    s = 4 * n
    return math.factorial(s) // (math.factorial(4) ** n * math.factorial(n))


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    lengths = inst["source_path_lengths"]
    target = inst["target_path_length"]
    memo = {}

    def rec(remaining):
        if not remaining:
            return 1
        if remaining in memo:
            return memo[remaining]
        first = remaining[0]
        rest = remaining[1:]
        count = 0
        for companions in itertools.combinations(rest, 3):
            group = (first,) + companions
            if sum(lengths[i] for i in group) != target:
                continue
            chosen = set(group)
            nxt = tuple(i for i in remaining if i not in chosen)
            count += rec(nxt)
        memo[remaining] = count
        return count

    return rec(tuple(range(len(lengths))))


def canonical_key(inst):
    """Canonical under source relabelling and positive affine length changes."""
    target = inst["target_path_length"]
    deviations = [4 * value - target for value in inst["source_path_lengths"]]
    scale = 0
    for value in deviations:
        scale = math.gcd(scale, abs(value))
    scale = scale or 1
    normal = sorted(value // scale for value in deviations)
    payload = json.dumps(
        [inst["n_targets"], inst["group_size"], normal],
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    p = dict(params)
    p.pop("_preset", None)
    separation = int(p.get("separation", 10))
    tag_base = int(p.get("tag_base", 6))
    n = int(p["n"])

    # First crowd the magnitude bands and shrink the tag hierarchy; this keeps
    # the 4n-element answer fixed.  Only after those axes are exhausted do we
    # lengthen the witness, and never beyond the 300-operation compact route.
    if separation > 5 or tag_base > 4:
        p["separation"] = max(5, separation - 1)
        p["tag_base"] = max(4, tag_base - 1)
        return p
    if 9 * (n + 1) + 6 <= 300:
        p["n"] = n + 1
        p["separation"] = 5
        p["tag_base"] = 4
        return p
    return None


def _four_sum_reference(inst):
    """Meet-in-the-middle quartet enumeration plus exact-cover propagation."""
    values = inst["source_path_lengths"]
    target = inst["target_path_length"]
    buckets = {}
    operations = 0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            operations += 1
            buckets.setdefault(values[i] + values[j], []).append((i, j))

    quartets = set()
    pair_matches = 0
    for total, left_pairs in buckets.items():
        operations += 1
        other = target - total
        if total > other or other not in buckets:
            continue
        right_pairs = buckets[other]
        if total < other:
            products = itertools.product(left_pairs, right_pairs)
        else:
            products = itertools.combinations(left_pairs, 2)
        for p1, p2 in products:
            operations += 1
            pair_matches += 1
            q = tuple(sorted(p1 + p2))
            if len(set(q)) == 4:
                quartets.add(q)

    by_vertex = {i: [] for i in range(len(values))}
    for q in quartets:
        for v in q:
            by_vertex[v].append(q)

    nodes = 0

    def cover(remaining, chosen):
        nonlocal nodes, operations
        nodes += 1
        operations += 1
        if not remaining:
            return list(chosen)
        v = min(remaining, key=lambda x: sum(set(q) <= remaining for q in by_vertex[x]))
        for q in by_vertex[v]:
            sq = set(q)
            if sq <= remaining:
                got = cover(remaining - sq, chosen + [list(q)])
                if got is not None:
                    return got
        return None

    solution = cover(set(range(len(values))), [])
    answer = None if solution is None else _canonical_groups(solution)
    return answer, {
        "operations": operations,
        "pair_sums": len(values) * (len(values) - 1) // 2,
        "pair_matches": pair_matches,
        "valid_quartets": len(quartets),
        "exact_cover_nodes": nodes,
    }


def _bands(inst):
    n = inst["n_targets"]
    ordered = sorted(range(4 * n), key=lambda i: inst["source_path_lengths"][i])
    return [ordered[i * n:(i + 1) * n] for i in range(4)]


def _mixed_radix_decode(inst):
    """Execute the intended compact inverse and count exact arithmetic.

    The four separated magnitude bands are D,A,B,C.  The latter three are
    arithmetic progressions.  The difference between the B and A step sizes
    is the hidden radix.  After subtracting the three rank-zero values from
    the target, each D value exposes three mixed-radix digits; the fixed
    unimodular mixing matrix is then inverted explicitly.

    Sorting, comparisons, indexing, and output assembly are not arithmetic
    operations.  Every subtraction, integer division, and remainder below is
    counted.
    """

    n = inst["n_targets"]
    values = inst["source_path_lengths"]
    target = inst["target_path_length"]
    bands = _bands(inst)
    if n < 2 or any(len(band) != n for band in bands):
        return None, 0
    d_band, a_band, b_band, c_band = bands
    operations = 0

    step_a = values[a_band[1]] - values[a_band[0]]
    step_b = values[b_band[1]] - values[b_band[0]]
    radix = step_b - step_a
    operations += 3
    if radix <= 1:
        return None, operations

    baseline = target - values[a_band[0]]
    baseline -= values[b_band[0]]
    baseline -= values[c_band[0]]
    operations += 3

    groups = []
    for d in d_band:
        code = baseline - values[d]
        w0 = code % radix
        quotient = code // radix
        w1 = quotient % radix
        w2 = quotient // radix
        y = w1 - w0
        z = w2 - w0
        x = w0 - y
        x -= z
        operations += 9
        if not (0 <= x < n and 0 <= y < n and 0 <= z < n):
            return None, operations
        groups.append([a_band[x], b_band[y], c_band[z], d])
    return _canonical_groups(groups), operations


def _attack_rank_bands(inst):
    bands = _bands(inst)
    # Try all global ascending/reversed rank conventions for the three upper
    # bands against the bottom band.  The hidden mixed coordinates defeat them.
    for mask in range(8):
        views = [bands[0]]
        for j in range(1, 4):
            views.append(list(reversed(bands[j])) if mask & (1 << (j - 1)) else bands[j])
        candidate = _canonical_groups([[views[j][i] for j in range(4)] for i in range(len(bands[0]))])
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_first_fit(inst):
    values = inst["source_path_lengths"]
    target = inst["target_path_length"]
    n = inst["n_targets"]
    bins = [[] for _ in range(n)]
    totals = [0] * n
    for item in sorted(range(len(values)), key=lambda i: (-values[i], i)):
        placed = False
        for b in range(n):
            if len(bins[b]) < 4 and totals[b] + values[item] <= target:
                bins[b].append(item)
                totals[b] += values[item]
                placed = True
                break
        if not placed:
            return None
    candidate = _canonical_groups(bins)
    return candidate if verify(inst, candidate)[0] else None


def _attack_random(inst, seed, restarts=512):
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_nearest_completion(inst):
    values = inst["source_path_lengths"]
    target = inst["target_path_length"]
    bands = _bands(inst)
    # For every plausible order of the three upper magnitude bands, greedily
    # choose the item that leaves the residual closest to the mean contribution
    # of the bands still to come.  This is executable by hand in principle but
    # ignores the mixed-coordinate invariant.
    for order in itertools.permutations((1, 2, 3)):
        for reverse_anchor in (False, True):
            available = {j: set(bands[j]) for j in (1, 2, 3)}
            groups = []
            anchors = list(reversed(bands[0])) if reverse_anchor else bands[0]
            failed = False
            for d in anchors:
                group = [d]
                total = values[d]
                for pos, band_id in enumerate(order):
                    future = order[pos + 1:]
                    if future:
                        future_mean = sum(
                            sum(values[i] for i in available[k]) / max(1, len(available[k]))
                            for k in future
                        )
                    else:
                        future_mean = 0.0
                    choices = available[band_id]
                    if not choices:
                        failed = True
                        break
                    pick = min(
                        choices,
                        key=lambda i: (abs(target - (total + values[i] + future_mean)), i),
                    )
                    choices.remove(pick)
                    group.append(pick)
                    total += values[pick]
                if failed:
                    break
                groups.append(group)
            if not failed:
                candidate = _canonical_groups(groups)
                if verify(inst, candidate)[0]:
                    return candidate
    return None


def _permute_instance(inst, old_to_new, multiplier=1, translation=0):
    size = len(inst["source_path_lengths"])
    if sorted(old_to_new) != list(range(size)):
        raise ValueError("old_to_new must be a permutation")
    if multiplier <= 0:
        raise ValueError("multiplier must be positive")
    lengths = [0] * size
    for old, new in enumerate(old_to_new):
        lengths[new] = multiplier * inst["source_path_lengths"][old] + translation
    carried = _canonical_groups([[old_to_new[i] for i in g] for g in inst["answer"]])
    out = dict(inst)
    out["source_path_lengths"] = lengths
    out["target_path_length"] = multiplier * inst["target_path_length"] + 4 * translation
    out["answer"] = carried
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    g1_attempts = 0
    g1_failures = []
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
        "generation_route": "inverse generation plus composition of path-length identities",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping)
    ans = inst["answer"]
    corruptions = {}
    empty = []
    drop = [list(g) for g in ans]
    drop[0] = drop[0][:-1]
    swap = [list(g) for g in ans]
    swap[0][0], swap[0][1] = swap[0][1], swap[0][0]
    duplicate = [list(g) for g in ans]
    duplicate[0][1] = duplicate[0][0]
    out_range = [list(g) for g in ans]
    out_range[0][0] = len(inst["source_path_lengths"])
    for name, bad in (
        ("empty", empty),
        ("drop_one", drop),
        ("swap_two", swap),
        ("duplicate", duplicate),
        ("out_of_range", out_range),
    ):
        ok, why = verify(inst, bad)
        corruptions[name] = {"rejected": not ok, "reason": why}
    reasons = [v["reason"] for v in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values()) and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "I checked the four-path sums.\n```json\n<answer>\n"
        + json.dumps(ans)
        + "\n</answer>\n```\nThe tags contain only the requested JSON."
    )
    parsed = parse_answer(model_style)
    example_parses = parse_answer(render(inst)) is not None
    report["G3_round_trip"] = {
        "pass": parsed == ans and example_parses,
        "model_style_round_trip": parsed == ans,
        "renderer_example_parses": example_parses,
    }

    guess_rng = random.Random(987654321)
    guess_samples = 200_000
    guess_hits = 0
    for _ in range(guess_samples):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_rate = guess_hits / guess_samples
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_samples,
        "estimated_probability": guess_rate,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform canonical equipartitions into four-element groups",
    }

    seeds = list(range(8))
    attack_counts = {
        "outlier_same_rank_bands": 0,
        "greedy_first_fit_decreasing": 0,
        "random_restart_512": 0,
        "nearest_completion_by_hand": 0,
    }
    reference_successes = 0
    reference_operations = []
    reference_walls = []
    reference_details = []
    compact_successes = 0
    compact_operations = []
    attack_walls = {name: 0.0 for name in attack_counts}
    for seed in seeds:
        cur = make_instance(seed=seed + 4000, **shipping)
        started = time.perf_counter()
        if _attack_rank_bands(cur) is not None:
            attack_counts["outlier_same_rank_bands"] += 1
        attack_walls["outlier_same_rank_bands"] += time.perf_counter() - started
        started = time.perf_counter()
        if _attack_first_fit(cur) is not None:
            attack_counts["greedy_first_fit_decreasing"] += 1
        attack_walls["greedy_first_fit_decreasing"] += time.perf_counter() - started
        started = time.perf_counter()
        if _attack_random(cur, seed=seed + 9000) is not None:
            attack_counts["random_restart_512"] += 1
        attack_walls["random_restart_512"] += time.perf_counter() - started
        started = time.perf_counter()
        if _attack_nearest_completion(cur) is not None:
            attack_counts["nearest_completion_by_hand"] += 1
        attack_walls["nearest_completion_by_hand"] += time.perf_counter() - started
        started = time.perf_counter()
        got, detail = _four_sum_reference(cur)
        wall = time.perf_counter() - started
        ok = got is not None and verify(cur, got)[0]
        reference_successes += int(ok)
        reference_operations.append(detail["operations"])
        reference_walls.append(wall)
        reference_details.append(detail)
        compact, compact_ops = _mixed_radix_decode(cur)
        compact_successes += int(compact is not None and verify(cur, compact)[0])
        compact_operations.append(compact_ops)

    attacks = {
        name: {
            "successes": successes,
            "attempts": len(seeds),
            "wall_clock_sec": attack_walls[name],
        }
        for name, successes in attack_counts.items()
    }
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8 for v in attacks.values())
    ref_avg_ops = sum(reference_operations) / len(reference_operations)
    ref_avg_wall = sum(reference_walls) / len(reference_walls)
    reference_algorithm = {
        "name": "4SUM meet-in-the-middle plus exact-cover propagation",
        "complexity": "O(s^2 + z) expected on the promised unique-quartet distribution",
        "wall_clock_sec": ref_avg_wall,
        "operations": ref_avg_ops,
        "max_operations": max(reference_operations),
        "solves": f"{reference_successes}/{len(seeds)}, as expected",
        "source_paths": len(inst["source_path_lengths"]),
    }
    report["G5_density_and_baseline"] = {
        "pass": (
            reference_successes == len(seeds)
            and guess_rate < 1e-6
            and enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"])) is not None
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_samples,
        "shipping_solution_fraction_estimate": guess_rate,
        "demo_exact_solution_count": enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"])),
        "baseline_wall_clock_sec": ref_avg_wall,
        "baseline_operations": ref_avg_ops,
        "baseline_max_operations": max(reference_operations),
        "strongest_failing_attack": "random_restart_512",
        "strongest_failing_attack_restarts": 512 * len(seeds),
        "strongest_failing_attack_wall_clock_sec": attack_walls["random_restart_512"],
    }
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed
            and reference_successes == len(seeds)
            and compact_successes == len(seeds)
        ),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
        "reference_details": reference_details,
        "compact_route": {
            "name": "exact inverse of the mixed-radix change of variables",
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/{len(seeds)}",
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * shipping["n"]
    doubled = make_instance(seed=333, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "shipping_space_bits": search_space(inst).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    witness_checks = 0
    distinct_keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **shipping)
        distinct_keys.append(canonical_key(base))
        size = len(base["source_path_lengths"])
        rr = random.Random(70_000 + seed)
        p1 = list(range(size))
        p2 = list(range(size))
        rr.shuffle(p1)
        rr.shuffle(p2)
        composed = [p2[p1[i]] for i in range(size)]
        for perm, mult, shift in ((p1, 1, 0), (p2, 3, 17), (composed, 5, 29)):
            moved = _permute_instance(base, perm, multiplier=mult, translation=shift)
            invariant_checks += 1
            if canonical_key(moved) != canonical_key(base):
                break
            ok, _ = verify(moved, moved["answer"])
            witness_checks += int(ok)
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 60
            and witness_checks == 60
            and len(set(distinct_keys)) == 20
        ),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "symmetries": [
            "arbitrary source-component relabelling",
            "positive integer scaling of every path length",
            "global translation with target translated fourfold",
            "compositions of these maps",
        ],
    }

    blobs = [
        json.dumps(make_instance(seed=s, **shipping)["answer"])
        for s in range(20)
    ]
    answer_chars = max(map(len, blobs))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(ans)
    compact_checks = []
    compact_counts = []
    for seed in range(20):
        compact_inst = make_instance(seed=80_000 + seed, **shipping)
        compact_answer, compact_count = _mixed_radix_decode(compact_inst)
        compact_checks.append(
            compact_answer is not None and verify(compact_inst, compact_answer)[0]
        )
        compact_counts.append(compact_count)
    intended_ops = max(compact_counts)
    arms = {k: dict(v) for k, v in G9_DIAGNOSTIC.items()}
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else None
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else None
    report["G9_no_tool_suitability"] = {
        "pass": (
            answer_chars <= 2000
            and answer_elements <= 256
            and intended_ops <= 300
            and all(compact_checks)
        ),
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": (
            "hardened" if arms["hinted"]["attempts"] and not arms["hinted"]["solved"]
            else "too_easy" if arms["hinted"]["solved"]
            else G9_ORACLE_STATUS
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "compact_route_verifies": f"{sum(compact_checks)}/{len(compact_checks)}",
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(v, dict) and v.get("pass")
        for key, v in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    # Useful for a local check; importing remains silent and side-effect free.
    print(json.dumps(selftest(), indent=2, sort_keys=True))
