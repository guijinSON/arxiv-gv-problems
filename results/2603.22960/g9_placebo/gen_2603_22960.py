"""Exact projective-hyperplane witness generator for arXiv:2603.22960.

The native family is Example 3.1(1) of Chen--Hua--Li--Wu: points of
PG(d-1,q) are one-dimensional subspaces of F_q^d and blocks are hyperplanes.
An instance gives projective points spanning one block.  The witness is the
normal row of that block, in a unique projective normalization.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The task needs only exact arithmetic modulo a prime.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "projective point representatives over a prime field",
        "a projective hyperplane block",
    ],
    "verification_operations": [
        "exact finite-field dot product",
        "projective normalization check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Two-coordinate projective points encode multiplicative relations between "
        "normal coordinates; following a spanning tree replaces dense elimination."
    ),
    "hardness_basis": (
        "Track B: modular Gaussian elimination on the shipping 192-by-128 "
        "rank-127 system is O(m n^2) and measured 56,700 field operations and "
        "0.063 seconds per instance on the build host; the compact spanning-tree "
        "route takes 127 field multiplications after the multiplicative invariant "
        "is recognized."
    ),
    "max_answer_tokens": 346,
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
        "One 1-by-n row over F_p, all entries nonzero, projectively normalized "
        "so entry 0 is 1; n <= 256 and p is a prime below 2^31."
    ),
    "bounds": {
        "rows": 1,
        "max_columns": 256,
        "field_bits": 31,
        "nonzero_entries": True,
        "first_entry": 1,
    },
}

DIFFICULTY = {
    "hard": {"n": 128, "prime_bits": 29, "extra_points": 64},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Each two-coordinate point records a multiplicative relation between the "
    "corresponding coordinates of the hyperplane normal."
)
PLACEBO_HINT = (
    "Careful organization of the displayed coordinates helps prevent small "
    "indexing errors in this problem."
)

# Filled from the independent hardening runs after they are performed.  These
# are diagnostics, not gates; G9(c)'s caps are the only gating part of G9.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = """\
Definition source: Section 3, Example 3.1(1) defines PG(d-1,q) using
1-subspaces as points, hyperplanes as blocks, and containment as the point-block
relation; it also gives the exact design parameters and proves local
2-transitivity through the PGL actions.  Theorem 1.2 classifies this as family
(1.1).  The decisive easy-result scan found no computational hardness theorem:
Section 2 gives a five-step Magma subgroup/orbit procedure for sporadic cases,
and Section 3 gives direct constructions for every infinite family.  Therefore
this module makes no Track A claim.  It uses Track B and states the existing
Gaussian-elimination algorithm openly.  Generation samples the normalized
hyperplane normal first, makes every displayed point orthogonal to it, and uses
a rooted connected support graph, so rank d-1 and uniqueness are known by construction.
The coordinate-frequency, all-ones, random-restart, and one-pass propagation
attacks are defeated by random nonzero normal coordinates, shuffled constraints,
and redundant constraints drawn in exactly the same way as the spanning ones.
"""


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the sub-2^31 values used here."""

    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value == prime:
            return True
        if value % prime == 0:
            return False
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 3, 5, 7, 11):
        if base >= value:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _sample_prime(bits: int, rng: random.Random) -> int:
    if bits < 3 or bits > 30:
        raise ValueError("prime_bits must be between 3 and 30")
    low = 1 << (bits - 1)
    high = (1 << bits) - 1
    candidate = rng.randrange(low, high + 1) | 1
    while candidate <= high:
        if _is_prime(candidate):
            return candidate
        candidate += 2
    candidate = low | 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _sparse_normalize(row: dict[int, int], p: int) -> list[list[int]]:
    clean = {i: value % p for i, value in row.items() if value % p}
    if not clean:
        raise ValueError("projective representative cannot be zero")
    first = min(clean)
    inv = pow(clean[first], p - 2, p)
    return [[i, clean[i] * inv % p] for i in sorted(clean)]


def _normalise_vector(row: list[int], p: int) -> list[int]:
    first = next((x for x in row if x % p), None)
    if first is None:
        raise ValueError("zero vector has no projective normalization")
    inv = pow(first, p - 2, p)
    return [x * inv % p for x in row]


def make_instance(
    n: int,
    seed: int = 0,
    p: int | None = None,
    prime_bits: int = 19,
    extra_points: int = 0,
    **params,
) -> dict:
    """Construct a spanning set of points on a projective hyperplane.

    The answer is sampled first.  A random rooted tree guarantees that the
    two-coordinate constraints are connected and hence have rank n-1.
    Additional edges are redundant projective points on the same hyperplane.
    No solve or search for the witness is performed.
    """

    del params
    if n < 3 or n > 256:
        raise ValueError("n must be between 3 and 256")
    if extra_points < 0:
        raise ValueError("extra_points must be nonnegative")
    rng = random.Random(seed)
    if p is None:
        p = _sample_prime(prime_bits, rng)
    if not isinstance(p, int) or not _is_prime(p) or p < 3:
        raise ValueError("p must be an odd prime")

    # The unique representative has coefficient zero fixed to 1.  Requiring all
    # entries nonzero is visible from the connected two-coordinate system and is
    # consequently built into random_candidate and search_space.
    normal = [1] + [rng.randrange(1, p) for _ in range(n - 1)]

    order = list(range(1, n))
    rng.shuffle(order)
    order.insert(0, 0)
    position = {vertex: index for index, vertex in enumerate(order)}
    # edge_map stores a public parent -> child orientation.  Every node is
    # reachable from zero in the planted tree, but row shuffling hides a usable
    # evaluation order.
    edge_map: dict[tuple[int, int], tuple[int, int]] = {}
    for index in range(1, n):
        child = order[index]
        parent = rng.choice(order[:index])
        edge_map[(min(parent, child), max(parent, child))] = (parent, child)
    target_edges = min(n * (n - 1) // 2, n + extra_points)
    while len(edge_map) < target_edges:
        u, v = rng.sample(range(n), 2)
        edge = (min(u, v), max(u, v))
        if edge in edge_map:
            continue
        parent, child = (u, v) if position[u] < position[v] else (v, u)
        edge_map[edge] = (parent, child)

    points = []
    for parent, child in edge_map.values():
        # c*normal[parent] - normal[child] = 0.  Once the structural
        # orientation is recognized, the next coordinate costs one multiply.
        c = normal[child] * pow(normal[parent], p - 2, p) % p
        points.append([[parent, c], [child, p - 1]])
    rng.shuffle(points)

    return {
        "paper": "arXiv:2603.22960",
        "family": "spanning points of a PG(d-1,p) hyperplane block",
        "dimension": n,
        "field_prime": p,
        "points": points,
        "answer": [normal],
    }


def render(inst: dict) -> str:
    n = inst["dimension"]
    p = inst["field_prime"]
    lines = [
        f"Work in the projective space PG({n - 1}, {p}) over the prime field F_{p}.",
        f"A projective point is a nonzero coordinate row in F_{p}^{n}, where multiplying the whole row by a nonzero field element does not change the point.",
        "A hyperplane block has an equation a_0*x_0 + ... + a_{n-1}*x_{n-1} = 0 modulo p for a nonzero normal row a.",
        "The points below all lie on one hyperplane and span it (their row rank is n-1), so its normal is unique up to nonzero scaling.",
        "Find that normal, normalized by making its first nonzero entry equal to 1.",
        "In this instance every normal entry is nonzero, so a_0 is the normalized entry and must equal 1.",
        "",
        "Coordinates are 0-indexed.  Each point is written as index:value pairs; every omitted coordinate is zero.",
        "All values and all arithmetic are modulo p.  Point order has no significance.",
        "Points:",
    ]
    for number, point in enumerate(inst["points"]):
        body = " ".join(f"{index}:{value}" for index, value in point)
        lines.append(f"P{number}: {body}")
    lines.extend([
        "",
        f"Output exactly one 1-by-{n} JSON matrix of integers in 0..{p - 1}; do not omit zero entries.",
        "Give your final answer inside <answer></answer> tags, as [[a_0,a_1,...,a_{n-1}]].",
        "Format-only example (not a solution): <answer>[[" + ",".join(["1"] + ["0"] * (n - 1)) + "]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        match = re.search(
            r"<answer>(.*?)</answer>", text, flags=re.IGNORECASE | re.DOTALL
        )
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        answer = json.loads(body)
        return answer if isinstance(answer, list) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    n = inst["dimension"]
    p = inst["field_prime"]
    if not isinstance(answer, list):
        return False, "malformed: expected a JSON matrix"
    if len(answer) == 0:
        return False, "empty answer: expected one matrix row"
    if len(answer) > 1 and all(row == answer[0] for row in answer[1:]):
        return False, "duplicate rows: the certificate has exactly one row"
    if len(answer) != 1 or not isinstance(answer[0], list):
        return False, "wrong row count: expected exactly one row"
    row = answer[0]
    if len(row) != n:
        return False, f"wrong column count: expected {n}, got {len(row)}"
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in row):
        return False, "malformed entry: every coefficient must be an integer"
    if any(value < 0 or value >= p for value in row):
        return False, f"entry out of range: coefficients must lie in 0..{p - 1}"
    if not any(row):
        return False, "zero normal: a projective normal must be nonzero"
    first = next(value for value in row if value)
    if first != 1:
        return False, "not normalized: the first nonzero coefficient must be 1"
    for point_number, point in enumerate(inst["points"]):
        dot = sum(value * row[index] for index, value in point) % p
        if dot:
            return False, f"point P{point_number} does not satisfy the hyperplane equation"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    p = inst["field_prime"]
    n = inst["dimension"]
    return [[1] + rng.choices(range(1, p), k=n - 1)]


def search_space(inst: dict) -> int | None:
    return (inst["field_prime"] - 1) ** (inst["dimension"] - 1)


def enumerate_all(inst: dict) -> int | None:
    p = inst["field_prime"]
    n = inst["dimension"]
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    count = 0
    for tail in itertools.product(range(1, p), repeat=n - 1):
        if verify(inst, [[1, *tail]])[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """A deliberately conservative projective-equivalence invariant.

    Field order, ambient dimension, and configuration size survive input order,
    projective rescaling, coordinate permutation, and every change of basis.
    The varying prime makes independently generated shipping instances distinct.
    This key may over-collapse inequivalent configurations with the same triple;
    that limitation is documented in README.md.
    """

    signature = {
        "geometry": "projective-hyperplane-point-configuration",
        "p": inst["field_prime"],
        "dimension": inst["dimension"],
        "point_count": len(inst["points"]),
    }
    blob = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Add redundant points and enlarge the field without lengthening the row."""

    out = {key: value for key, value in params.items() if key != "_preset"}
    n = int(out["n"])
    extra = int(out.get("extra_points", 0))
    maximum = n * (n - 1) // 2 - n
    if extra < maximum:
        out["extra_points"] = min(maximum, extra + max(32, n // 2))
        if "p" not in out:
            out["prime_bits"] = min(30, int(out.get("prime_bits", 19)) + 1)
        return out
    if int(out.get("prime_bits", 30)) < 30 and "p" not in out:
        out["prime_bits"] = int(out.get("prime_bits", 19)) + 1
        return out
    return "cap_bound"


def _dense_rows(inst: dict) -> list[list[int]]:
    n = inst["dimension"]
    dense = []
    for point in inst["points"]:
        row = [0] * n
        for index, value in point:
            row[index] = value
        dense.append(row)
    return dense


def _gaussian_nullspace(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Reference algorithm; return a normalized null vector and field-op count."""

    p = inst["field_prime"]
    a = _dense_rows(inst)
    m = len(a)
    n = inst["dimension"]
    pivot_columns = []
    pivot_row = 0
    operations = 0
    for column in range(n):
        found = next((r for r in range(pivot_row, m) if a[r][column] % p), None)
        if found is None:
            continue
        a[pivot_row], a[found] = a[found], a[pivot_row]
        inv = pow(a[pivot_row][column], p - 2, p)
        operations += 1
        for j in range(column, n):
            a[pivot_row][j] = a[pivot_row][j] * inv % p
            operations += 1
        for r in range(pivot_row + 1, m):
            factor = a[r][column] % p
            if factor:
                for j in range(column, n):
                    a[r][j] = (a[r][j] - factor * a[pivot_row][j]) % p
                    operations += 2
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == m:
            break

    free = [column for column in range(n) if column not in set(pivot_columns)]
    if len(free) != 1:
        return None, operations
    x = [0] * n
    x[free[0]] = 1
    for r in range(len(pivot_columns) - 1, -1, -1):
        column = pivot_columns[r]
        total = 0
        for j in range(column + 1, n):
            if a[r][j] and x[j]:
                total = (total + a[r][j] * x[j]) % p
                operations += 2
        x[column] = (-total) % p
    first = next((value for value in x if value), None)
    if first is None:
        return None, operations
    inv = pow(first, p - 2, p)
    operations += 1
    x = [value * inv % p for value in x]
    operations += n
    return [x], operations


def _attack_outlier_frequency(inst: dict) -> object:
    n = inst["dimension"]
    counts = [0] * n
    for point in inst["points"]:
        for index, _ in point:
            counts[index] += 1
    chosen = min(range(n), key=lambda i: (counts[i], i))
    row = [0] * n
    row[chosen] = 1
    return [row]


def _attack_all_ones(inst: dict) -> object:
    return [[1] * inst["dimension"]]


def _attack_one_pass(inst: dict) -> object:
    """A plausible by-hand scan which never revisits earlier constraints."""

    p = inst["field_prime"]
    known = {0: 1}
    for point in inst["points"]:
        if len(point) != 2:
            continue
        (u, a), (v, b) = point
        if u in known and v not in known:
            known[v] = (-a * known[u] * pow(b, p - 2, p)) % p
        elif v in known and u not in known:
            known[u] = (-b * known[v] * pow(a, p - 2, p)) % p
    return [[known.get(i, 1) for i in range(inst["dimension"])]]


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 4096) -> object:
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _rescale_points(inst: dict) -> dict:
    out = copy.deepcopy(inst)
    p = out["field_prime"]
    scaled = []
    for number, point in enumerate(out["points"]):
        factor = (number + 2) % p or 1
        scaled.append([[i, value * factor % p] for i, value in point])
    out["points"] = scaled
    return out


def _permute_coordinates(inst: dict, permutation: list[int]) -> tuple[dict, list[list[int]]]:
    out = copy.deepcopy(inst)
    p = out["field_prime"]
    new_points = []
    for point in out["points"]:
        row = {permutation[i]: value for i, value in point}
        new_points.append(_sparse_normalize(row, p))
    out["points"] = new_points
    old_normal = inst["answer"][0]
    normal = [0] * len(permutation)
    for old, new in enumerate(permutation):
        normal[new] = old_normal[old]
    answer = [_normalise_vector(normal, p)]
    out["answer"] = answer
    return out, answer


def _shear_coordinates(inst: dict, u: int, v: int, amount: int) -> tuple[dict, list[list[int]]]:
    """Apply x'_v=x_v+amount*x_u and carry the normal by A^{-1}."""

    out = copy.deepcopy(inst)
    p = out["field_prime"]
    new_points = []
    for point in out["points"]:
        row = {i: value for i, value in point}
        row[v] = (row.get(v, 0) + amount * row.get(u, 0)) % p
        new_points.append(_sparse_normalize(row, p))
    out["points"] = new_points
    normal = list(inst["answer"][0])
    normal[u] = (normal[u] - amount * normal[v]) % p
    answer = [_normalise_vector(normal, p)]
    out["answer"] = answer
    return out, answer


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest() -> dict:
    report: dict[str, object] = {}

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    row = list(inst["answer"][0])
    swap_j = next(j for j in range(2, len(row)) if row[j] != row[1])
    swapped = list(row)
    swapped[1], swapped[swap_j] = swapped[swap_j], swapped[1]
    corruptions = {
        "drop_one": [row[:-1]],
        "swap_two": [swapped],
        "duplicate_row": [row, list(row)],
        "empty": [],
        "out_of_range": [[inst["field_prime"], *row[1:]]],
    }
    reasons = {}
    all_rejected = True
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        all_rejected &= not ok
        reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and len(set(reasons.values())) == len(reasons),
        "rejected": sum(not verify(inst, bad)[0] for bad in corruptions.values()),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    model_reply = (
        "I used the projective normalization.\n```json\n<answer>"
        + json.dumps(inst["answer"], separators=(",", ":"))
        + "</answer>\n```\nThe dot products vanish."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_matches": parsed == inst["answer"],
        "malformed_returns_none": parse_answer("not an answer") is None,
    }

    guess_rng = random.Random(0x260322960)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "structure_aware_space": str(search_space(inst)),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
    }

    reference_attempts = 8
    reference_successes = 0
    reference_operations = []
    reference_seconds = 0.0
    for seed in range(reference_attempts):
        probe = make_instance(seed=7000 + seed, **shipping_params)
        before = time.perf_counter()
        candidate, operations = _gaussian_nullspace(probe)
        reference_seconds += time.perf_counter() - before
        reference_operations.append(operations)
        reference_successes += int(candidate is not None and verify(probe, candidate)[0])

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": guess_rate < 1e-6 and reference_successes == reference_attempts,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_valid_fraction": guess_rate,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(reference_seconds, 6),
        "baseline_field_operations_mean": sum(reference_operations) // len(reference_operations),
        "baseline_field_operations_max": max(reference_operations),
    }

    attack_counts = {
        "outlier_coordinate_frequency": 0,
        "greedy_all_ones": 0,
        "random_restart_4096": 0,
        "one_pass_ratio_scan": 0,
    }
    attack_attempts = 8
    for seed in range(attack_attempts):
        probe = make_instance(seed=9000 + seed, **shipping_params)
        candidates = {
            "outlier_coordinate_frequency": _attack_outlier_frequency(probe),
            "greedy_all_ones": _attack_all_ones(probe),
            "random_restart_4096": _attack_random_restart(
                probe, random.Random(100_000 + seed)
            ),
            "one_pass_ratio_scan": _attack_one_pass(probe),
        }
        for name, candidate in candidates.items():
            attack_counts[name] += int(verify(probe, candidate)[0])
    attacks = {
        name: {"successes": successes, "attempts": attack_attempts}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "modular Gaussian elimination and back substitution",
            "complexity": "O(m*n^2) exact field operations",
            "wall_clock_sec": round(reference_seconds, 6),
            "operations": sum(reference_operations),
            "operations_mean": sum(reference_operations) // len(reference_operations),
            "solves": f"{reference_successes}/{reference_attempts}, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = shipping_params["n"] * 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    harder = escalate(shipping_params)
    report["G7_scales"] = {
        "pass": doubled_ok and isinstance(harder, dict),
        "original_dimension": shipping_params["n"],
        "doubled_dimension": doubled["dimension"],
        "doubled_verify_reason": doubled_reason,
        "fixed_answer_length_escalation": harder,
    }

    invariant_checks = 0
    key_matches = 0
    witness_matches = 0
    keys = []
    for seed in range(20):
        base = make_instance(seed=20_000 + seed, **shipping_params)
        key = canonical_key(base)
        keys.append(key)

        reordered = copy.deepcopy(base)
        reordered["points"] = list(reversed(reordered["points"]))
        transforms = [(reordered, reordered["answer"]), (_rescale_points(base), base["answer"])]

        perm_rng = random.Random(30_000 + seed)
        permutation = list(range(base["dimension"]))
        perm_rng.shuffle(permutation)
        permuted, permuted_answer = _permute_coordinates(base, permutation)
        sheared, sheared_answer = _shear_coordinates(base, 1, 2, 3)
        combined = _rescale_points(permuted)
        combined["points"] = list(reversed(combined["points"]))
        combined, combined_answer = _shear_coordinates(combined, 1, 2, 3)
        transforms.extend([
            (permuted, permuted_answer),
            (sheared, sheared_answer),
            (combined, combined_answer),
        ])
        for transformed, carried_answer in transforms:
            invariant_checks += 1
            if canonical_key(transformed) == key:
                key_matches += 1
            ok, _ = verify(transformed, carried_answer)
            witness_matches += int(ok)
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == key_matches
            and invariant_checks == witness_matches
            and distinct == 20
        ),
        "invariance_checks": invariant_checks,
        "invariant_keys": key_matches,
        "transformations_preserving_witness": witness_matches,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "invariant": "field order, ambient dimension, and point count",
    }

    answer_chars = 0
    answer_elements = 0
    for seed in range(20):
        sample = make_instance(seed=40_000 + seed, **shipping_params)
        answer_chars = max(answer_chars, len(json.dumps(sample["answer"])))
        answer_elements = max(answer_elements, _atomic_elements(sample["answer"]))
    answer_tokens = math.ceil(answer_chars / 4)
    intended_operations = shipping_params["n"] - 1
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": copy.deepcopy(G9_ARM_RESULTS),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": "diagnostic_pending" if not hinted["attempts"] else (
            "too_easy" if hinted["solved"] else "hardened"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
