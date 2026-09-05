"""Verified WSP plan generator based on arXiv:1205.0852, Sections 2 and 6."""

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
from collections import deque


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # Present in the repository; this finite family needs no helper routines.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "workflow steps",
        "finite user set",
        "step-user authorization relation",
        "counting constraint (1,S) requiring distinct users",
    ],
    "verification_operations": [
        "integer range check",
        "exact authorization lookup",
        "distinctness comparison",
        "counting-constraint check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "When rows are ordered by their public step residues, their sums form an "
        "arithmetic progression modulo the user count; without recognizing it, one "
        "must construct a full authorization matching."
    ),
    "hardness_basis": (
        "Track B: Section 6, Theorem 6.5 uses Hopcroft-Karp maximum matching in "
        "O(|A| sqrt(|S|+|U|)); across eight shipping instances it took 0.062070 "
        "seconds and 71,368 edge scans (8,921 per instance), while the compact "
        "row-sum route uses 238 modular field operations."
    ),
    "max_answer_tokens": 172,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# Here n is both the number of steps and users.  The second axis, degree, is the
# number of equally legitimate affine matchings superposed in the authorization
# relation.  The hard preset nearly fills both no-tool caps without crossing them.
DIFFICULTY = {
    "hard": {"n": 199, "degree": 20},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-n permutation of the n displayed integer user IDs, in fixed "
        "step-ID order; the permutation condition enforces every obvious shape "
        "and all-different requirement before authorization is tested."
    ),
    "bounds": {
        "entries": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "distinct_entries": "n",
        "candidate_count": "n!",
        "shipping_n": 199,
    },
}

STRUCTURAL_HINT = (
    "In step-residue order, the modular authorization-row sums have constant difference."
)
PLACEBO_HINT = (
    "The workflow tables reward consistent notation and careful attention to indices."
)

NOTES = """\
Section 2 fixes the native objects and semantics: a plan maps every workflow step
to an authorized user, and the counting constraint (1,S) assigns every participating
user exactly one step.  Section 3, Theorem 3.6 says counting-constraint WSP is FPT.
More decisively for this special case, Section 6, Theorem 6.5 constructs the
authorization bipartite graph and invokes Hopcroft-Karp matching; because (1,S) is
all-different, a full matching is already a complete plan.  That polynomial method
rules out Track A and is reported as the successful Track B reference algorithm.

Generation is inverse and never solves its output.  It samples a nonzero slope a and
a uniform set B of offsets in Z_p.  Every displayed edge has the form u=a*s+b for
some b in B, so each offset produces a certified perfect matching and every edge is
drawn from the same certificate-bearing construction.  One offset is sampled as the
stored witness.  Row and display orders are shuffled independently.

The compact route notices that sum(A_s)=|B|*a*s+sum(B) modulo p.  At the shipping
preset p=199=10*20-1, so the inverse of 20 is 10; summing the rows with residues 0
and 1 reveals a, and any entry of the residue-0 row supplies an offset.  Repeated
modular addition builds a residue-indexed plan, which the public step labels reorder.
The outlier attack is neutralized by exact regularity on both sides.  Row-minimum,
greedy-unused, 256 random greedy restarts, and the obvious slope-one ansatz are all
measured.  Canonicalization forgets opaque IDs and normalizes the recovered offset
set under every affine change of cyclic coordinates.
"""


# Updated only after script-owned hardening runs; importing performs no file I/O.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _is_prime(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value):
    candidate = max(3, int(value) | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _masks(authorizations):
    return [sum(1 << user for user in row) for row in authorizations]


def make_instance(n, seed=0, degree=10, **params):
    """Inverse-generate a native WSP instance and one valid plan.

    All arithmetic structure is used only to manufacture authorization edges.
    The returned certificate is sampled from those matchings, not recovered by a
    matching algorithm or any search over the completed instance.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or not _is_prime(n):
        raise ValueError("n must be a prime integer")
    if n < 5:
        raise ValueError("n must be at least 5")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer")
    if not 2 <= degree < n:
        raise ValueError("degree must satisfy 2 <= degree < n")

    rng = random.Random(seed)
    # Avoid the few slopes that make common visual ansatzes accidentally correct.
    forbidden = {0, 1, n - 1}
    slope = rng.randrange(1, n)
    while slope in forbidden:
        slope = rng.randrange(1, n)
    offsets = rng.sample(range(n), degree)
    witness_offset = offsets[rng.randrange(degree)]

    step_residues = list(range(n))
    if n > 7:
        rng.shuffle(step_residues)
    authorizations = []
    for step_residue in step_residues:
        row = [(slope * step_residue + b) % n for b in offsets]
        rng.shuffle(row)
        authorizations.append(row)

    users = list(range(n))
    step_order = list(range(n))
    rng.shuffle(users)
    rng.shuffle(step_order)
    answer = [
        (slope * step_residue + witness_offset) % n
        for step_residue in step_residues
    ]

    return {
        "n": n,
        "modulus": n,
        "degree": degree,
        "users": users,
        "user_id_mask": (1 << n) - 1,
        "user_residues": list(range(n)),
        "step_residues": step_residues,
        "step_order": step_order,
        "authorizations": authorizations,
        "authorization_masks": _masks(authorizations),
        "counting_constraint": {
            "lower": 1,
            "upper": 1,
            "steps": list(range(n)),
        },
        "answer": answer,
    }


def render(inst):
    """Render a self-contained WSP statement and an exact output contract."""
    n = inst["n"]
    identity_steps = inst["step_residues"] == list(range(n))
    identity_users = inst["user_residues"] == list(range(n))
    lines = [
        "WORKFLOW SATISFIABILITY: AUTHORIZED ALL-DIFFERENT PLAN",
        "",
        f"There are {n} workflow steps S0,...,S{n-1} and {n} users U0,...,U{n-1}.",
        "There are no precedence restrictions. A plan assigns exactly one user to",
        "each step. It is authorized when the assigned user occurs in that step's",
        "authorization row.",
        "",
        "The one counting constraint is (1,1,{all steps}): every user who performs",
        "a listed step must perform exactly one listed step. Thus all n assignments",
        "must be distinct; because there are n users, every user is used exactly once.",
        "Order matters by step, repeats are forbidden, and there are no other",
        "workflow constraints.",
        "",
        f"Each step and user also has a public residue in Z_{inst['modulus']}; all",
        "residue arithmetic is modulo that prime. Residues are instance data, not",
        "extra constraints: validity is determined only by authorization and the",
        "all-different rule.",
    ]
    if identity_steps and identity_users:
        lines.append("For every i, both Si and Ui carry residue i.")
    else:
        lines.append("Step residues: " + ",".join(
            f"S{i}={r}" for i, r in enumerate(inst["step_residues"])
        ))
        lines.append("User residues: " + ",".join(
            f"U{i}={r}" for i, r in enumerate(inst["user_residues"])
        ))
    lines.extend([
        "",
        f"Every authorization row contains exactly {inst['degree']} distinct users.",
        "The row order below and the order within each row have no significance:",
    ])
    for step in inst["step_order"]:
        row = ",".join(f"U{user}" for user in inst["authorizations"][step])
        lines.append(
            f"  S{step} [residue {inst['step_residues'][step]}]: {row}"
        )
    lines.extend([
        "",
        "Displayed user IDs (input order has no significance):",
        "  " + ",".join(f"U{user}" for user in inst["users"]),
        "",
        "Find any valid plan. Give exactly n integer user IDs in fixed step order",
        f"S0,S1,...,S{n-1}. Write IDs without the letter U and use 0-based indexing.",
        "",
        "Give your final answer inside <answer></answer> tags, as comma-separated",
        "integers. Example syntax: <answer>3, 17, 42</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.I | re.S)


def parse_answer(text):
    """Extract the last delimited comma-separated plan; never raise."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I).strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return []
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(token.strip()) for token in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Check a plan exactly without reading inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a list of user IDs"
    n = inst["n"]
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"too few plan entries: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"too many plan entries: expected {n}, got {len(answer)}"
    displayed_mask = inst.get("user_id_mask", (1 << n) - 1)
    for index, user in enumerate(answer):
        if (
            type(user) is not int
            or user < 0
            or user >= n
            or not ((displayed_mask >> user) & 1)
        ):
            return False, f"entry {index} is not a displayed user ID"
    if len(set(answer)) != n:
        return False, "counting constraint (1,1,S) is violated by a repeated user"
    masks = inst.get("authorization_masks")
    for step, user in enumerate(answer):
        authorized = (
            bool((masks[step] >> user) & 1)
            if masks is not None
            else user in inst["authorizations"][step]
        )
        if not authorized:
            return False, f"step S{step} is assigned an unauthorized user"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the structure-aware language: all user permutations."""
    candidate = list(inst["users"])
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return math.factorial(inst["n"])


def enumerate_all(inst):
    """Return an exact solution count only below a strict brute-force cap."""
    if search_space(inst) > 1_000_000:
        return None
    return sum(
        verify(inst, list(candidate))[0]
        for candidate in itertools.permutations(inst["users"])
    )


def _residue_rows(inst):
    """Authorization rows expressed in intrinsic cyclic coordinates."""
    user_residue = inst["user_residues"]
    rows = {}
    for step, row in enumerate(inst["authorizations"]):
        residue = inst["step_residues"][step]
        rows[residue] = frozenset(user_residue[user] for user in row)
    return rows


def _recover_slope_and_offsets(inst):
    """Recover the unique parallel-translation description from public data."""
    p = inst["modulus"]
    rows = _residue_rows(inst)
    if set(rows) != set(range(p)):
        raise ValueError("step residues are not a complete coordinate system")
    base = rows[0]
    candidates = sorted({(right - left) % p for left in base for right in rows[1]})
    for slope in candidates:
        if slope == 0:
            continue
        if all(
            frozenset((user - slope * step) % p for user in rows[step]) == base
            for step in range(1, p)
        ):
            return slope, tuple(sorted(base))
    raise ValueError("authorization relation has no parallel affine presentation")


def _compact_row_sum_plan(inst):
    """Execute the intended invariant route from public instance data only."""
    p = inst["modulus"]
    degree = inst["degree"]
    rows = _residue_rows(inst)
    row_sum_zero = sum(rows[0]) % p
    row_sum_one = sum(rows[1]) % p
    slope = (row_sum_one - row_sum_zero) * pow(degree, -1, p) % p
    offset = min(rows[0])
    user_by_residue = {
        residue: user for user, residue in enumerate(inst["user_residues"])
    }
    return [
        user_by_residue[(slope * residue + offset) % p]
        for residue in inst["step_residues"]
    ]


def canonical_key(inst):
    """Canonical under ID relabeling, input order, and affine coordinate changes."""
    p = inst["modulus"]
    _, offsets = _recover_slope_and_offsets(inst)
    # An affine change on either cyclic coordinate sends B to c(B-b0).  Minimize
    # over every such representation; this is exact for the generated family.
    normalized = min(
        tuple(sorted((scale * (value - origin)) % p for value in offsets))
        for origin in offsets
        for scale in range(1, p)
    )
    payload = ["parallel-affine-WSP", p, inst["degree"], normalized]
    blob = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    """The hard preset exhausts safe fixed-answer axes and reaches the output cap."""
    p = {key: value for key, value in params.items() if key != "_preset"}
    n = int(p["n"])
    degree = int(p.get("degree", 2))
    if n < 251:
        p["n"] = 251
        p["degree"] = max(degree, 25)
        return p
    # More steps exceed 256 answer atoms; more crowding makes the compact row-sum
    # route exceed 300 field operations and eventually helps random greedy matching.
    return "cap_bound"


def _hopcroft_karp_reference(inst):
    """Paper-standard maximum matching, with exact operation counters."""
    n = inst["n"]
    user_index = {user: i for i, user in enumerate(inst["users"])}
    adjacency = [
        [user_index[user] for user in inst["authorizations"][step]]
        for step in range(n)
    ]
    pair_step = [-1] * n
    pair_user = [-1] * n
    distance = [0] * n
    counts = {"edge_scans": 0, "bfs_rounds": 0, "dfs_calls": 0, "augmentations": 0}

    def bfs():
        counts["bfs_rounds"] += 1
        queue = deque()
        found = False
        for step in range(n):
            if pair_step[step] < 0:
                distance[step] = 0
                queue.append(step)
            else:
                distance[step] = -1
        while queue:
            step = queue.popleft()
            for user in adjacency[step]:
                counts["edge_scans"] += 1
                other = pair_user[user]
                if other < 0:
                    found = True
                elif distance[other] < 0:
                    distance[other] = distance[step] + 1
                    queue.append(other)
        return found

    def dfs(step):
        counts["dfs_calls"] += 1
        for user in adjacency[step]:
            counts["edge_scans"] += 1
            other = pair_user[user]
            if other < 0 or (distance[other] == distance[step] + 1 and dfs(other)):
                pair_step[step] = user
                pair_user[user] = step
                return True
        distance[step] = -1
        return False

    while bfs():
        progress = False
        for step in range(n):
            if pair_step[step] < 0 and dfs(step):
                counts["augmentations"] += 1
                progress = True
        if not progress:
            break
    if any(user < 0 for user in pair_step):
        return None, counts
    return [inst["users"][index] for index in pair_step], counts


def _attack_row_minimum(inst):
    return [min(row) for row in inst["authorizations"]]


def _attack_degree_outlier(inst):
    frequencies = [0] * inst["n"]
    for row in inst["authorizations"]:
        for user in row:
            frequencies[user] += 1
    return [min(row, key=lambda user: (frequencies[user], user)) for row in inst["authorizations"]]


def _attack_greedy_smallest(inst):
    used = set()
    answer = []
    for row in inst["authorizations"]:
        choice = next((user for user in sorted(row) if user not in used), None)
        if choice is None:
            return _attack_row_minimum(inst)
        answer.append(choice)
        used.add(choice)
    return answer


def _attack_random_greedy(inst, rng, attempts):
    n = inst["n"]
    for _ in range(attempts):
        order = list(range(n))
        rng.shuffle(order)
        answer = [None] * n
        used = set()
        for step in order:
            choices = [u for u in inst["authorizations"][step] if u not in used]
            if not choices:
                break
            user = rng.choice(choices)
            answer[step] = user
            used.add(user)
        else:
            if verify(inst, answer)[0]:
                return answer, True
    return _attack_row_minimum(inst), False


def _attack_constant_offset(inst):
    p = inst["modulus"]
    rows = _residue_rows(inst)
    offset = min(rows[0])
    user_by_residue = {residue: user for user, residue in enumerate(inst["user_residues"])}
    answer = [None] * p
    for step, residue in enumerate(inst["step_residues"]):
        answer[step] = user_by_residue[(residue + offset) % p]
    return answer


def _transform_instance(inst, step_map, user_map, row_orders, coordinate):
    """Carry an instance/witness through ID and affine-coordinate relabelings."""
    n = inst["n"]
    alpha, beta, gamma, delta = coordinate
    step_residues = [None] * n
    user_residues = [None] * n
    authorizations = [None] * n
    answer = [None] * n
    for old_user, new_user in enumerate(user_map):
        old_residue = inst["user_residues"][old_user]
        user_residues[new_user] = (gamma * old_residue + delta) % n
    for old_step, new_step in enumerate(step_map):
        old_residue = inst["step_residues"][old_step]
        step_residues[new_step] = (alpha * old_residue + beta) % n
        authorizations[new_step] = [
            user_map[inst["authorizations"][old_step][index]]
            for index in row_orders[old_step]
        ]
        answer[new_step] = user_map[inst["answer"][old_step]]
    users = [user_map[user] for user in reversed(inst["users"])]
    step_order = [step_map[step] for step in reversed(inst["step_order"])]
    constraint_steps = [step_map[step] for step in reversed(
        inst["counting_constraint"]["steps"]
    )]
    return {
        "n": n,
        "modulus": n,
        "degree": inst["degree"],
        "users": users,
        "user_id_mask": (1 << n) - 1,
        "user_residues": user_residues,
        "step_residues": step_residues,
        "step_order": step_order,
        "authorizations": authorizations,
        "authorization_masks": _masks(authorizations),
        "counting_constraint": {"lower": 1, "upper": 1, "steps": constraint_steps},
        "answer": answer,
    }


def selftest():
    """Run every local gate and return a JSON-native measurement report."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    compact_failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            compact = _compact_row_sum_plan(inst)
            compact_ok, compact_reason = verify(inst, compact)
            if not compact_ok:
                compact_failures.append([preset, seed, compact_reason])
    report["G1_planted_verifies"] = {
        "pass": not failures and not compact_failures,
        "attempts": attempts,
        "failures": failures,
        "compact_route_attempts": attempts,
        "compact_route_failures": compact_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    swapped = None
    for index in range(shipping["n"] - 1):
        trial = list(planted)
        trial[index], trial[index + 1] = trial[index + 1], trial[index]
        if not verify(shipping, trial)[0]:
            swapped = trial
            break
    duplicated = list(planted)
    duplicated[-1] = duplicated[0]
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["n"]],
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"accepted": bool(ok), "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not case["accepted"] for case in cases.values())
        and len(set(reasons)) == len(cases),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    wire = ", ".join(str(value) for value in planted)
    parsed = parse_answer(
        "I found an authorized plan.\n```text\n<answer>[" + wire + "]</answer>\n```"
    )
    json_native = json.loads(json.dumps(planted)) == planted
    report["G3_round_trip"] = {
        "pass": parsed == planted and json_native,
        "parsed_entries": len(parsed) if isinstance(parsed, list) else None,
        "json_native": json_native,
    }

    sample_total = 200_000
    sample_hits = 0
    rng = random.Random(271828)
    started = time.perf_counter()
    for _ in range(sample_total):
        sample_hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    density_wall = time.perf_counter() - started
    density = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_fraction": density,
        "structure_aware_space": search_space(shipping),
        "prior": "uniform over all permutations of the displayed users",
    }

    attack_names = (
        "outlier_low_user_degree",
        "row_minimum",
        "greedy_smallest_unused",
        "random_greedy_restart_256",
        "constant_offset_slope_one",
    )
    attacks = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    attack_wall = {name: 0.0 for name in attack_names}
    reference = {
        "name": "Hopcroft-Karp maximum matching",
        "complexity": "O(|A| * sqrt(|S|+|U|))",
        "attempts": 0,
        "successes": 0,
        "wall_clock_sec": 0.0,
        "edge_scans": 0,
        "bfs_rounds": 0,
        "dfs_calls": 0,
        "augmentations": 0,
    }
    for seed in range(8):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {}
        started = time.perf_counter()
        candidates["outlier_low_user_degree"] = _attack_degree_outlier(inst)
        attack_wall["outlier_low_user_degree"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["row_minimum"] = _attack_row_minimum(inst)
        attack_wall["row_minimum"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["greedy_smallest_unused"] = _attack_greedy_smallest(inst)
        attack_wall["greedy_smallest_unused"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["random_greedy_restart_256"] = _attack_random_greedy(
            inst, random.Random(90_000 + seed), 256
        )[0]
        attack_wall["random_greedy_restart_256"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["constant_offset_slope_one"] = _attack_constant_offset(inst)
        attack_wall["constant_offset_slope_one"] += time.perf_counter() - started
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(verify(inst, candidate)[0])

        started = time.perf_counter()
        plan, counts = _hopcroft_karp_reference(inst)
        reference["wall_clock_sec"] += time.perf_counter() - started
        reference["attempts"] += 1
        reference["successes"] += int(plan is not None and verify(inst, plan)[0])
        for key in ("edge_scans", "bfs_rounds", "dfs_calls", "augmentations"):
            reference[key] += counts[key]
    for name in attack_names:
        attacks[name]["wall_clock_sec"] = round(attack_wall[name], 6)
    reference["wall_clock_sec"] = round(reference["wall_clock_sec"], 6)
    reference["average_edge_scans"] = round(reference["edge_scans"] / 8, 1)
    reference["complexity_bound_at_shipping"] = math.ceil(
        shipping["n"] * shipping["degree"] * math.sqrt(2 * shipping["n"])
    )
    reference["solves"] = f"{reference['successes']}/{reference['attempts']}, as expected"
    all_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference["successes"] == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "regularity_check": {
            "step_degrees": sorted({len(row) for row in shipping["authorizations"]}),
            "user_degrees": sorted({
                sum(user in row for row in shipping["authorizations"])
                for user in shipping["users"]
            }),
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and enumerate_all(demo) is not None
        and reference["successes"] == reference["attempts"],
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_sampled_density": density,
        "shipping_density_wall_sec": round(density_wall, 6),
        "demo_exact_solution_count": enumerate_all(demo),
        "demo_candidate_count": search_space(demo),
        "strongest_reference_wall_sec_8_instances": reference["wall_clock_sec"],
        "strongest_reference_edge_scans_8_instances": reference["edge_scans"],
        "strongest_reference_average_edge_scans": reference["average_edge_scans"],
        "strongest_failing_attack": "random_greedy_restart_256",
        "failing_attack_restarts": 8 * 256,
        "failing_attack_wall_sec": attacks["random_greedy_restart_256"]["wall_clock_sec"],
    }

    doubled_n = _next_prime(2 * shipping["n"])
    started = time.perf_counter()
    doubled = make_instance(
        n=doubled_n,
        degree=2 * shipping["degree"],
        seed=424242,
    )
    build_wall = time.perf_counter() - started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": bool(doubled_ok) and doubled_n >= 2 * shipping["n"],
        "base_n": shipping["n"],
        "doubled_n": doubled_n,
        "base_degree": shipping["degree"],
        "doubled_degree": doubled["degree"],
        "build_wall_sec": round(build_wall, 6),
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=70_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(80_000 + seed)
        step_map = list(range(inst["n"]))
        user_map = list(range(inst["n"]))
        rng.shuffle(step_map)
        rng.shuffle(user_map)
        row_orders = []
        for row in inst["authorizations"]:
            order = list(range(len(row)))
            rng.shuffle(order)
            row_orders.append(order)
        alpha = rng.randrange(1, inst["n"])
        gamma = rng.randrange(1, inst["n"])
        coordinate = (alpha, rng.randrange(inst["n"]), gamma, rng.randrange(inst["n"]))
        transformed = _transform_instance(
            inst, step_map, user_map, row_orders, coordinate
        )
        invariant_checks += 1
        if canonical_key(transformed) != canonical_key(inst):
            g8_failures.append([seed, "key changed under a composed relabeling"])
        carried_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            g8_failures.append([seed, "carried witness failed after relabeling"])
        distinct_keys.append(canonical_key(inst))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(distinct_keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "transformations_per_check": [
            "step-ID permutation",
            "user-ID permutation",
            "step-row reordering",
            "authorization-row reordering",
            "independent affine changes of both cyclic coordinates",
        ],
        "unrelated_instances": 20,
        "distinct_keys": len(set(distinct_keys)),
        "failures": g8_failures,
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    # Two row sums, one difference, one multiplication by degree^{-1}, and a
    # residue-indexed arithmetic progression. Reordering by the public labels uses
    # table lookups, not additional arithmetic. Each modular field operation counts once.
    intended_operations = (
        2 * (shipping["degree"] - 1) + 1 + 1 + (shipping["n"] - 1)
    )
    caps = (
        answer_chars <= 2000
        and len(planted) <= 256
        and intended_operations <= 300
    )
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": caps,
        "arms": {
            name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(planted),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "within_caps": caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
