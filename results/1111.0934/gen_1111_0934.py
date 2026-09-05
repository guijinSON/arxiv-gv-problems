"""Verified Track-B SALBP-2 generator for arXiv:1111.0934.

The paper defines SALBP-2 as assigning integral-time tasks to a fixed number
of ordered stations while minimizing the largest station load.  Section 1
observes that the problem is NP-complete even without precedence constraints,
where it is identical-machine makespan scheduling.

This module uses the decision/witness form with two stations and a stated
cycle time.  It composes equal-sum four-task identities, hides each identity
as a residue class, and shuffles all tasks.  The planted assignment is known
before the instance is assembled; no scheduling algorithm is used to find it.
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
from collections import defaultdict


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK: str = "B"
SHIPPING_DIFFICULTY: str = "easy"

PROBLEM_PROFILE: dict = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "integral task execution times",
        "two assembly-line stations with a common cycle time",
        "task-to-station assignment",
    ],
    "verification_operations": [
        "integer station-load summation",
        "exact capacity comparison",
        "exact assignment-cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Group task times by a concealed common residue and balance each "
        "four-task group through its equal pair sums; without that decomposition "
        "one must search for additive collisions across the whole task set."
    ),
    "hardness_basis": (
        "Track B: Section 1 identifies two-station SALBP-2 without precedences "
        "with identical-machine makespan scheduling; Horowitz-Sahni exact "
        "meet-in-the-middle costs O(2^(n/2)) and averaged 1,066,842 exact "
        "add/subtract steps (4.736 seconds for eight shipping instances in the "
        "recorded self-test), while "
        "a distribution-specific O(n^2) scan uses 780 pair additions; the compact "
        "residue decomposition needs at most 100 exact operations."
    ),
    "max_answer_tokens": 21,
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
    "demo": {"n": 8, "quotient_max": 10_000},
    "easy": {"n": 40, "quotient_max": 1_000_000_000},
    "medium": {"n": 64, "quotient_max": 1_000_000_000},
    "hard": {"n": 96, "quotient_max": 1_000_000_000},
}

# A scratch hardening run can select just the shipping rung without editing the
# checked-in module.  Normal imports still expose exactly the required ladder.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly n binary station labels.  Entry i is 0 or 1 "
        "and assigns 0-indexed task i to that station; exactly n/2 entries "
        "must have each label."
    ),
    "bounds": {
        "length": "n",
        "alphabet": [0, 1],
        "station_0_entries": "n/2",
        "station_1_entries": "n/2",
        "candidate_count": "binomial(n,n/2)",
        "shipping_atoms": 40,
    },
}


STRUCTURAL_HINT: str = (
    "Reduce every task time modulo 997: each four-task residue class contains "
    "two complementary pairs with identical sums."
)
PLACEBO_HINT: str = (
    "Compare every task time carefully with the cycle limit: each binary station "
    "label contributes to exactly one load."
)


NOTES: str = """
Section 1 fixes the native definition: SALBP assigns every integral-time task
to a station, respects the task poset, and measures an assignment by its largest
station load.  SALBP-2 fixes the station count and minimizes that load.  The
same section states that its decision version is NP-complete even when the
precedence order is empty, by identical-parallel-machine makespan scheduling.

The paper also explicitly warns that excellent constructive heuristics and
exact methods exist, and Section 5 solves the displayed integer programs with
CPLEX branch-and-cut.  Worst-case NP-completeness therefore cannot justify
Track A for an inverse-planted distribution.  This module declares Track B and
reports the successful polynomial reference algorithm rather than hiding it in
the failing-attack panel.

Generation composes scalar parallelogram identities.  In every hidden group,
four quotients satisfy q0+q3=q1+q2; the four execution times share a residue
modulo 997, so the two pairs have exactly equal loads.  Independently choosing
which pair goes to station 0 and then shuffling the tasks constructs a valid
two-station schedule without solving one.  A large common offset forces every
feasible schedule to put exactly n/2 tasks at each station.

The domain-standard exact reference is Horowitz-Sahni meet-in-the-middle, and a
faster distribution-specific algorithm computes all task-pair sums, hashes
collisions, and extracts the disjoint equal-sum pairs.  The latter succeeds on
every generated instance in O(n^2), so Track A would be false.  The intended
no-tool route notices the modulo-997 decomposition and compares only six pair
sums inside each four-task bucket.  At shipping size this is 40 reductions plus
60 additions, versus 780 additions for the residue-blind scan.

The per-task station side is independently flipped within every identity, so
magnitude or derivation order does not correlate with the planted label.  The
outlier split, largest-processing-time greedy schedule, sorted alternation,
extreme pairing, and balanced random restarts are all rerun by selftest().
""".strip()


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}


_MODULUS = 997
_ENUMERATION_CAP = 500_000
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)


def _validate_parameters(n: int, quotient_max: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 4:
        raise ValueError("n must be an integer multiple of 4 and at least 8")
    if n // 4 >= _MODULUS:
        raise ValueError("n/4 must be smaller than the fixed modulus 997")
    if (isinstance(quotient_max, bool)
            or not isinstance(quotient_max, int)
            or quotient_max < 100):
        raise ValueError("quotient_max must be an integer at least 100")


def _collision_groups(times: list[int]) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """All repeated pair sums, rejecting ambiguous repetitions."""
    sums: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for i in range(len(times)):
        for j in range(i + 1, len(times)):
            sums[times[i] + times[j]].append((i, j))
    collisions = []
    for pairs in sums.values():
        if len(pairs) > 1:
            if len(pairs) != 2 or len(set(pairs[0] + pairs[1])) != 4:
                return []
            collisions.append((pairs[0], pairs[1]))
    return collisions


def make_instance(n: int, seed: int = 0, quotient_max: int = 1_000_000_000,
                  **params) -> dict:
    """Compose hidden equal-load groups and return their known schedule.

    The answer is sampled while the four-term identities are assembled.  The
    final collision check only excludes accidental extra identities; it never
    searches for, repairs, or replaces the already-known certificate.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, quotient_max)
    rng = random.Random(seed)
    group_count = n // 4
    residues = rng.sample(range(1, _MODULUS), group_count)

    for _construction_attempt in range(100):
        records = []
        planted = []
        offset = _MODULUS * (n * (quotient_max + 2) + 1_000)

        for group, residue in enumerate(residues):
            while True:
                q0 = rng.randrange(quotient_max + 1)
                q1 = rng.randrange(quotient_max + 1)
                q2 = rng.randrange(quotient_max + 1)
                q3 = q1 + q2 - q0
                if (0 <= q3 <= quotient_max
                        and len({q0, q1, q2, q3}) == 4):
                    break
            side = rng.randrange(2)
            for local, quotient in enumerate((q0, q1, q2, q3)):
                task_time = offset + _MODULUS * quotient + residue
                station = side if local in (0, 3) else 1 - side
                records.append((task_time, station, group, local))
                planted.append(station)

        times_unshuffled = [row[0] for row in records]
        collisions = _collision_groups(times_unshuffled)
        # With billion-sized quotients an accidental collision is rare.  Keeping
        # only the intended n/4 disjoint identities makes the reference cost and
        # the compact explanation reproducible across seeds.
        if len(collisions) != group_count:
            continue
        covered = set()
        for left, right in collisions:
            covered.update(left)
            covered.update(right)
        if len(covered) != n:
            continue

        order = list(range(n))
        rng.shuffle(order)
        times = [records[i][0] for i in order]
        answer = [planted[i] for i in order]
        cycle_time = sum(
            task_time for task_time, station in zip(times, answer)
            if station == 0
        )
        if sum(times) != 2 * cycle_time:
            raise AssertionError("constructed station loads disagree")
        return {
            "n": n,
            "stations": 2,
            "cycle_time": cycle_time,
            "task_times": times,
            "precedences": [],
            "answer": answer,
        }

    raise RuntimeError("could not avoid accidental pair-sum collisions")


def render(inst: dict) -> str:
    """Render a self-contained SALBP-2 feasibility question."""
    n = inst["n"]
    times = inst["task_times"]
    rows = []
    width = len(str(n - 1))
    for start in range(0, n, 4):
        rows.append("  " + "   ".join(
            f"{i:0{width}d}:{times[i]}" for i in range(start, min(n, start + 4))
        ))
    statement = f"""Two-station simple assembly-line balancing (SALBP-2)

There are {n} indivisible tasks, numbered 0 through {n - 1}, and two stations,
labelled 0 and 1.  Task i has the positive integral execution time shown below.
Every task must be assigned to exactly one station.  There are no precedence
relations in this instance.  The load of a station is the sum of the execution
times assigned to it, and its load must be at most the common cycle time
{inst['cycle_time']}.

Task data are written as task:time:
{chr(10).join(rows)}

The sum of all task times is exactly twice the cycle time.  The displayed range
of task times also forces every feasible assignment to put exactly {n // 2}
tasks at each station.  Thus both station loads must equal the cycle time.

Output a JSON list of exactly {n} integers.  Entry i is the station label for
task i, so every entry must be 0 or 1; exactly {n // 2} entries must be 0 and
exactly {n // 2} must be 1.  Task order is fixed by its 0-based index.  The two
station labels may be globally swapped, but entries may not be omitted or
repeated.

Give your final answer inside <answer></answer> tags as the JSON list.
Example format: <answer>[0,1,1,0]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse tagged JSON despite surrounding prose or Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    candidates = list(reversed(matches))
    if not candidates:
        candidates.extend(reversed(_FENCE_RE.findall(text)))
    for candidate in candidates:
        try:
            value = json.loads(candidate.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any feasible assignment, never the planted answer."""
    n = inst.get("n")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"too few entries: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"too many entries: expected {n}, got {len(answer)}"
    for index, station in enumerate(answer):
        if isinstance(station, bool) or not isinstance(station, int):
            return False, f"entry {index} is not an integer station label"
        if station not in (0, 1):
            return False, f"entry {index} is outside the station range 0..1"

    zero_count = answer.count(0)
    if zero_count != n // 2:
        return False, (
            f"wrong station cardinalities: station 0 has {zero_count} tasks, "
            f"expected {n // 2}"
        )

    times = inst.get("task_times")
    if not isinstance(times, list) or len(times) != n:
        return False, "instance has malformed task times"
    loads = [0, 0]
    for task_time, station in zip(times, answer):
        if isinstance(task_time, bool) or not isinstance(task_time, int) or task_time <= 0:
            return False, "instance has a nonpositive or nonintegral task time"
        loads[station] += task_time

    cycle = inst.get("cycle_time")
    if loads[0] > cycle:
        return False, f"station 0 exceeds cycle time by {loads[0] - cycle}"
    if loads[1] > cycle:
        return False, f"station 1 exceeds cycle time by {loads[1] - cycle}"
    if loads[0] != cycle or loads[1] != cycle:
        return False, "station loads do not both equal the cycle time"
    return True, "ok"


def random_candidate(inst: dict, rng) -> object:
    """Sample uniformly from the visible equal-cardinality assignment space."""
    n = inst["n"]
    station_zero = set(rng.sample(range(n), n // 2))
    return [0 if i in station_zero else 1 for i in range(n)]


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["n"] // 2)


def enumerate_all(inst: dict) -> int | None:
    """Count all balanced feasible assignments when the space is small."""
    n = inst["n"]
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    for zero_tasks in itertools.combinations(range(n), n // 2):
        zero_set = set(zero_tasks)
        candidate = [0 if i in zero_set else 1 for i in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def _pair_collision_reference(inst: dict) -> tuple[list[int] | None, int]:
    """Residue-blind O(n^2) equal-pair-sum decomposition."""
    times = inst["task_times"]
    n = len(times)
    sums: dict[int, list[tuple[int, int]]] = defaultdict(list)
    operations = 0
    for i in range(n):
        for j in range(i + 1, n):
            sums[times[i] + times[j]].append((i, j))
            operations += 1

    blocks = []
    for value in sorted(sums):
        pairs = sums[value]
        if len(pairs) == 2 and len(set(pairs[0] + pairs[1])) == 4:
            blocks.append((pairs[0], pairs[1]))
    blocks.sort(key=lambda block: min(block[0] + block[1]))

    answer = [None] * n
    for left, right in blocks:
        vertices = set(left + right)
        if any(answer[i] is not None for i in vertices):
            continue
        for i in left:
            answer[i] = 0
        for i in right:
            answer[i] = 1
    if any(value is None for value in answer):
        return None, operations
    return answer, operations


def _mitm_reference(inst: dict) -> tuple[list[int] | None, int]:
    """Horowitz-Sahni exact balanced subset sum via two half lists.

    Gray-code enumeration changes one task at a time, so the operation counter
    records one exact add/subtract per noninitial subset.  Hash lookup and bit
    bookkeeping are not counted as exact arithmetic.
    """
    times = inst["task_times"]
    n = len(times)
    split = n // 2
    left_times = times[:split]
    right_times = times[split:]
    left: dict[tuple[int, int], int] = {}
    total = 0
    cardinality = 0
    previous = 0
    operations = 0
    for serial in range(1 << len(left_times)):
        gray = serial ^ (serial >> 1)
        if serial:
            changed = gray ^ previous
            bit = (changed & -changed).bit_length() - 1
            if (gray >> bit) & 1:
                total += left_times[bit]
                cardinality += 1
            else:
                total -= left_times[bit]
                cardinality -= 1
            operations += 1
        left.setdefault((cardinality, total), gray)
        previous = gray

    target_count = n // 2
    total = 0
    cardinality = 0
    previous = 0
    found = None
    for serial in range(1 << len(right_times)):
        gray = serial ^ (serial >> 1)
        if serial:
            changed = gray ^ previous
            bit = (changed & -changed).bit_length() - 1
            if (gray >> bit) & 1:
                total += right_times[bit]
                cardinality += 1
            else:
                total -= right_times[bit]
                cardinality -= 1
            operations += 1
        left_mask = left.get((
            target_count - cardinality,
            inst["cycle_time"] - total,
        ))
        if left_mask is not None:
            found = (left_mask, gray)
            break
        previous = gray
    if found is None:
        return None, operations

    left_mask, right_mask = found
    answer = [1] * n
    for bit in range(len(left_times)):
        if (left_mask >> bit) & 1:
            answer[bit] = 0
    for bit in range(len(right_times)):
        if (right_mask >> bit) & 1:
            answer[split + bit] = 0
    return answer, operations


def _residue_compact_route(inst: dict) -> tuple[list[int] | None, int]:
    """The intended route: six local pair sums per residue bucket."""
    groups: dict[int, list[int]] = defaultdict(list)
    operations = 0
    for task, task_time in enumerate(inst["task_times"]):
        groups[task_time % _MODULUS].append(task)
        operations += 1

    answer = [None] * inst["n"]
    for residue in sorted(groups):
        tasks = sorted(groups[residue])
        if len(tasks) != 4:
            return None, operations
        local: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for i, j in itertools.combinations(tasks, 2):
            local[inst["task_times"][i] + inst["task_times"][j]].append((i, j))
            operations += 1
        collision = [pairs for pairs in local.values()
                     if len(pairs) == 2 and len(set(pairs[0] + pairs[1])) == 4]
        if len(collision) != 1:
            return None, operations
        left, right = collision[0]
        for i in left:
            answer[i] = 0
        for i in right:
            answer[i] = 1
    if any(value is None for value in answer):
        return None, operations
    return answer, operations


def _attack_answers(inst: dict) -> dict[str, list[int]]:
    times = inst["task_times"]
    n = inst["n"]
    ordered = sorted(range(n), key=lambda i: (times[i], i))

    smallest = [1] * n
    for task in ordered[:n // 2]:
        smallest[task] = 0

    alternating = [0] * n
    for rank, task in enumerate(ordered):
        alternating[task] = rank % 2

    greedy = [None] * n
    loads = [0, 0]
    counts = [0, 0]
    for task in reversed(ordered):
        choices = [station for station in (0, 1)
                   if counts[station] < n // 2]
        station = min(choices, key=lambda s: (loads[s], s))
        greedy[task] = station
        loads[station] += times[task]
        counts[station] += 1

    extremes = [None] * n
    for index in range(n // 2):
        low = ordered[index]
        high = ordered[n - 1 - index]
        extremes[low] = index % 2
        extremes[high] = 1 - index % 2

    return {
        "outlier_smallest_half": smallest,
        "greedy_lpt_balance": greedy,
        "sorted_alternating": alternating,
        "extreme_pairing_ansatz": extremes,
    }


def canonical_key(inst: dict) -> str:
    """Invariant under task order, station swap, and uniform time scaling."""
    values = [inst["cycle_time"]] + list(inst["task_times"])
    scale = 0
    for value in values:
        scale = math.gcd(scale, value)
    normalized_cycle = inst["cycle_time"] // scale
    normalized_times = sorted(value // scale for value in inst["task_times"])
    payload = json.dumps(
        [inst["stations"], normalized_cycle, normalized_times],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params) -> dict | str | None:
    """Add hidden groups until the 300-operation compact-route cap binds."""
    current = dict(params)
    current.pop("_preset", None)
    n = int(current.get("n", 0))
    if n >= 120:
        return "cap_bound"
    current["n"] = min(120, n + 12)
    # More quotient entropy is a fixed-format secondary axis: it suppresses
    # accidental global arithmetic coincidences without adding answer fields.
    current["quotient_max"] = max(
        1_000_000_000, int(current.get("quotient_max", 1_000_000_000)) * 10
    )
    return current


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _reordered(inst: dict, order: list[int]) -> tuple[dict, list[int]]:
    changed = {
        "n": inst["n"],
        "stations": inst["stations"],
        "cycle_time": inst["cycle_time"],
        "task_times": [inst["task_times"][i] for i in order],
        "precedences": [],
        "answer": [inst["answer"][i] for i in order],
    }
    return changed, list(changed["answer"])


def _scaled(inst: dict, factor: int) -> tuple[dict, list[int]]:
    changed = {
        "n": inst["n"],
        "stations": inst["stations"],
        "cycle_time": factor * inst["cycle_time"],
        "task_times": [factor * value for value in inst["task_times"]],
        "precedences": [],
        "answer": list(inst["answer"]),
    }
    return changed, list(changed["answer"])


def selftest() -> dict:
    report = {}

    planted_checks = 0
    json_checks = 0
    compact_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            json_checks += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
            compact, operations = _residue_compact_route(inst)
            compact_ok = compact is not None and verify(inst, compact)[0]
            compact_checks += int(compact_ok)
            expected_operations = inst["n"] + 6 * (inst["n"] // 4)
            if operations != expected_operations:
                g1_failures.append(
                    f"{preset}/{seed}: compact operations {operations} != {expected_operations}"
                )
    report["G1_planted_verifies"] = {
        "pass": (not g1_failures and planted_checks == 16
                 and json_checks == planted_checks
                 and compact_checks == planted_checks),
        "planted_checks": planted_checks,
        "json_native_round_trips": json_checks,
        "independent_compact_reconstructions": compact_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(
        seed=31_415, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = list(shipping["answer"])
    swapped = None
    for left in range(shipping["n"]):
        for right in range(left + 1, shipping["n"]):
            if answer[left] != answer[right]:
                candidate = list(answer)
                candidate[left], candidate[right] = candidate[right], candidate[left]
                if not verify(shipping, candidate)[0]:
                    swapped = candidate
                    break
        if swapped is not None:
            break
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate_one": answer + [answer[-1]],
        "out_of_range": [2] + answer[1:],
        "swap_two_labels": swapped,
    }
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": (swapped is not None
                 and all(entry["rejected"] for entry in rejection_reasons.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    answer_json = json.dumps(answer, separators=(",", ":"))
    wrapped = (
        "I balanced the hidden groups before checking both loads.\n```json\n"
        f"<answer>{answer_json}</answer>\n```\nThe loads agree exactly."
    )
    report["G3_round_trip"] = {
        "pass": (parse_answer(wrapped) == answer
                 and parse_answer("unrelated prose") is None),
        "prose_fence_tags_round_trip": parse_answer(wrapped) == answer,
        "garbage_returns_none": parse_answer("unrelated prose") is None,
    }

    sample_total = 200_000
    sample_rng = random.Random(0x11110934)
    sample_hits = 0
    sample_started = time.perf_counter()
    for _ in range(sample_total):
        sample_hits += int(verify(
            shipping, random_candidate(shipping, sample_rng))[0])
    sample_wall = time.perf_counter() - sample_started
    candidate_space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": sample_hits / sample_total < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_fraction": sample_hits / sample_total,
        "candidate_space": candidate_space,
        "candidate_space_log10": math.log10(candidate_space),
        "sampling_prior": (
            "uniform binary assignments conditioned on the explicitly stated "
            "n/2 tasks at each station"
        ),
        "wall_clock_sec": round(sample_wall, 6),
    }

    attack_stats = {
        "outlier_smallest_half": {"successes": 0, "attempts": 0},
        "greedy_lpt_balance": {"successes": 0, "attempts": 0},
        "sorted_alternating": {"successes": 0, "attempts": 0},
        "extreme_pairing_ansatz": {"successes": 0, "attempts": 0},
        "random_restart_256": {
            "successes": 0, "attempts": 0, "candidates": 0,
        },
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    reference_per_seed = []
    distribution_successes = 0
    distribution_operations = 0
    distribution_wall = 0.0
    distribution_per_seed = []
    compact_successes = 0
    compact_operations = 0
    strongest_failing_wall = 0.0
    for seed in range(8):
        trial = make_instance(
            seed=50_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_answers(trial).items():
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(verify(trial, candidate)[0])

        restart_rng = random.Random(60_000 + seed)
        restart_started = time.perf_counter()
        restart_solved = False
        for _ in range(256):
            candidate = random_candidate(trial, restart_rng)
            attack_stats["random_restart_256"]["candidates"] += 1
            if verify(trial, candidate)[0]:
                restart_solved = True
                break
        strongest_failing_wall += time.perf_counter() - restart_started
        attack_stats["random_restart_256"]["attempts"] += 1
        attack_stats["random_restart_256"]["successes"] += int(restart_solved)

        distribution_started = time.perf_counter()
        distribution_answer, operations = _pair_collision_reference(trial)
        distribution_elapsed = time.perf_counter() - distribution_started
        distribution_solved = (distribution_answer is not None
                               and verify(trial, distribution_answer)[0])
        distribution_successes += int(distribution_solved)
        distribution_operations += operations
        distribution_wall += distribution_elapsed
        distribution_per_seed.append({
            "seed": 50_000 + seed,
            "solved": distribution_solved,
            "pair_additions": operations,
            "wall_clock_sec": round(distribution_elapsed, 6),
        })

        started = time.perf_counter()
        reference, operations = _mitm_reference(trial)
        elapsed = time.perf_counter() - started
        solved = reference is not None and verify(trial, reference)[0]
        reference_successes += int(solved)
        reference_operations += operations
        reference_wall += elapsed
        reference_per_seed.append({
            "seed": 50_000 + seed,
            "solved": solved,
            "exact_add_or_subtract_operations": operations,
            "wall_clock_sec": round(elapsed, 6),
        })

        compact, operations = _residue_compact_route(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
        compact_operations += operations

    all_attacks_failed = all(
        entry["successes"] == 0 for entry in attack_stats.values())
    report["G6_adversary_panel"] = {
        "pass": (all_attacks_failed and reference_successes == 8
                 and distribution_successes == 8),
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "Horowitz-Sahni exact meet-in-the-middle balanced subset sum",
            "complexity": "O(2^(n/2)) time and space",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "operation_unit": "exact add/subtract steps across eight shipping instances",
            "average_operations": reference_operations // 8,
            "solves": f"{reference_successes}/8, as expected",
            "per_seed": reference_per_seed,
        },
        "distribution_specific_algorithm": {
            "name": "residue-blind all-pairs sum hashing and collision decomposition",
            "complexity": "O(n^2) exact additions and expected O(n^2) hashing",
            "wall_clock_sec": round(distribution_wall, 6),
            "operations": distribution_operations,
            "average_operations": distribution_operations // 8,
            "solves": f"{distribution_successes}/8, as expected",
            "per_seed": distribution_per_seed,
        },
        "compact_route": {
            "name": "modulo-997 four-task decomposition",
            "operations": compact_operations,
            "average_operations": compact_operations // 8,
            "solves": f"{compact_successes}/8",
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (demo_count is not None
                 and sample_hits / sample_total < 1e-6
                 and reference_successes == 8
                 and distribution_successes == 8),
        "shipping_density_method": "structure-aware Monte Carlo",
        "shipping_sampled_valid_hits": sample_hits,
        "shipping_sampled_valid_total": sample_total,
        "shipping_observed_valid_fraction": sample_hits / sample_total,
        "shipping_candidate_space": candidate_space,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_total_operations": reference_operations,
        "reference_algorithm_average_operations": reference_operations // 8,
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "distribution_algorithm_total_operations": distribution_operations,
        "distribution_algorithm_average_operations": distribution_operations // 8,
        "distribution_algorithm_wall_clock_sec": round(distribution_wall, 6),
        "strongest_failing_attack": "random_restart_256",
        "strongest_failing_attack_candidates": (
            attack_stats["random_restart_256"]["candidates"]),
        "strongest_failing_attack_wall_clock_sec": round(
            strongest_failing_wall, 6),
    }

    preset_spaces = {
        name: search_space(make_instance(seed=7, **params))
        for name, params in DIFFICULTY.items()
    }
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424_242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    names = list(DIFFICULTY)
    report["G7_scales"] = {
        "pass": (doubled_ok and all(
            preset_spaces[left] < preset_spaces[right]
            for left, right in zip(names[:-1], names[1:]))),
        "preset_candidate_spaces": preset_spaces,
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "shipping_answer_atoms": _answer_atoms(shipping["answer"]),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
    }

    invariance_checks = 0
    carried_witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        trial = make_instance(
            seed=70_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(trial)
        unrelated_keys.append(key)
        rng = random.Random(80_000 + seed)
        order = list(range(trial["n"]))
        rng.shuffle(order)
        reordered, reordered_answer = _reordered(trial, order)
        scaled, scaled_answer = _scaled(trial, 2 + seed % 5)
        composed, composed_answer = _reordered(scaled, order)
        for name, changed, carried in (
            ("task permutation", reordered, reordered_answer),
            ("uniform time scaling", scaled, scaled_answer),
            ("scaling composed with task permutation", composed, composed_answer),
        ):
            invariance_checks += 1
            if canonical_key(changed) != key:
                invariant_failures.append(f"seed {seed}/{name}: key changed")
            carried_witness_checks += 1
            if not verify(changed, carried)[0]:
                invariant_failures.append(f"seed {seed}/{name}: witness failed")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "transformations": [
            "arbitrary task renumbering",
            "uniform positive integral scaling of all times and the cycle time",
            "their composition; station-label swap leaves the instance unchanged",
        ],
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = shipping["n"] + 6 * (shipping["n"] // 4)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_complete": all(arms[name]["attempts"] > 0 for name in arms),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
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
