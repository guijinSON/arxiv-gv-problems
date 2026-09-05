"""Verified problem generator for arXiv:1310.3353.

The paper's Theorem 2 proves that a one-dimensional weighted point graph has
an optimal clustering whose clusters are consecutive in line order, and gives
an O(n^2) dynamic program.  This module asks for any consecutive clustering
under a planted exact budget.  The points are presented through an affine
residue coordinate, so the generic dynamic program is mechanical while a
short change of variables exposes the constructed clustering.
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "In the affine residue coordinate, the points occupy narrow symmetric bands "
    "around an almost-threshold arithmetic progression."
)
PLACEBO_HINT: str = (
    "In this weighted instance, careful bookkeeping of ranks and endpoint "
    "conventions prevents avoidable arithmetic mistakes."
)

# These values are replaced with the measured three-arm results after hardening.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
}
G9_HINTED_VERDICT = "hardened"


PROBLEM_PROFILE: dict = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "one-dimensional weighted point graph",
        "integer line metric in an affine residue representation",
        "consecutive cluster partition",
    ],
    "verification_operations": [
        "exact modular affine transformation",
        "exact integer distance and weight evaluation",
        "exact weighted cluster-editing cost comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undoing the affine residue representation exposes symmetric point bands; "
        "without that coordinate, a solver must evaluate the quadratic dynamic program."
    ),
    "hardness_basis": (
        "Track B: Theorem 2 and Algorithm 2 solve ordered one-dimensional weighted "
        "point-graph cluster editing in O(n^2); at the hard preset the reference "
        "implementation performs about 7206 exact arithmetic operations in about "
        "0.00052 s in CPython at the shipping preset, whereas the affine-band route takes 197 "
        "exact arithmetic operations but must be recognized and executed without tools."
    ),
    "max_answer_tokens": 5,
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
    "demo": {"n": 12, "q": 3, "modulus_bits": 13, "outlier_milli": 410},
    "easy": {"n": 48, "q": 6, "modulus_bits": 31, "outlier_milli": 440},
    "medium": {"n": 56, "q": 6, "modulus_bits": 61, "outlier_milli": 440},
    "hard": {"n": 64, "q": 6, "modulus_bits": 89, "outlier_milli": 450},
}

SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing list containing any subset of the n-1 line-order "
        "cut ranks; rank c means a cut after exactly c points."
    ),
    "bounds": {
        "minimum_cut_rank": 1,
        "maximum_cut_rank": "n-1",
        "maximum_number_of_cuts": "n-1",
    },
}

NOTES: str = """
Definition source: Section 2.2 defines weighted cluster editing and its exact
insertion/deletion cost.  Section 2.3 defines one-dimensional point graphs.
Theorem 2 in Section 3.1 proves that a one-dimensional weighted point graph has
an optimal consecutive clustering, and Algorithm 2 computes it in O(n^2).
Section 3.1.2 is the easy-regime warning: the paper's truncated heuristics take
O(nk), and Section 3.2.2 observes that Algorithm 2 optimizes consecutive
clusterings for any supplied order.  Therefore this is Track B, never Track A.

Generation is inverse: choose the cut ranks and symmetric line-coordinate bands
first, compute their exact edit cost, and only then disguise each coordinate by
an invertible affine residue map.  No optimizer is called by make_instance.
The planted witness only claims cost <= budget, not uniqueness or optimality.

The raw-coordinate outlier probe is defeated by the affine permutation.  The
largest-gap probe is defeated by a pair of deliberately remote but still
same-cluster points in every band.  Unequal even band populations defeat equal
blocks.  Random restart faces the structure-aware cut language.  Agglomerative
positive-gain merging is led toward the remote-point decoys.  The exact dynamic
program is reported separately as the successful Track-B reference algorithm.
""".strip()


# Known Mersenne primes.  They make every nonzero affine multiplier invertible.
_PRIMES = {
    13: (1 << 13) - 1,
    19: (1 << 19) - 1,
    31: (1 << 31) - 1,
    61: (1 << 61) - 1,
    89: (1 << 89) - 1,
    107: (1 << 107) - 1,
    127: (1 << 127) - 1,
}


def _prime_for(bits: int) -> tuple[int, int]:
    exponent = min((b for b in _PRIMES if b >= bits), default=127)
    return exponent, _PRIMES[exponent]


def _cluster_sizes(n: int, q: int, rng: random.Random) -> list[int]:
    """Sample unequal even populations without looking at any generated graph."""

    if q < 2 or n < 4 * q:
        raise ValueError("need q >= 2 and n >= 4q")
    if n % 2:
        raise ValueError("n must be even")
    total_units = n // 2
    average = total_units / q
    low = max(2, int(average) - 1)
    high = max(low + 1, math.ceil(average) + 2)

    for _ in range(20_000):
        units = [rng.randint(low, high) for _ in range(q - 1)]
        units.append(total_units - sum(units))
        if not low <= units[-1] <= high:
            continue
        sizes = [2 * u for u in units]
        if n > 16 and max(sizes) - min(sizes) < 4:
            continue
        if n > 16:
            cumulative = 0
            equal = False
            for j, size in enumerate(sizes[:-1], 1):
                cumulative += size
                if cumulative == round(j * n / q):
                    equal = True
                    break
            if equal:
                continue
        return sizes

    # Only the tiny demo can plausibly reach this fallback.
    base, rem = divmod(n, q)
    sizes = [base + (1 if i < rem else 0) for i in range(q)]
    if any(s % 2 for s in sizes):
        raise RuntimeError("could not construct even cluster populations")
    return sizes


def _latent_coordinates(
    n: int,
    q: int,
    modulus: int,
    outlier_milli: int,
    rng: random.Random,
) -> tuple[list[int], list[int], int, int]:
    """Construct the known bands and return (coordinates, sizes, L, pitch)."""

    sizes = _cluster_sizes(n, q, rng)
    # q*pitch + the positive outlier remains strictly below modulus.
    threshold = (100 * (modulus - 1)) // (122 * q + 50)
    pitch = (122 * threshold) // 100
    extreme = (outlier_milli * threshold) // 1000
    bulk_limit = max(8, threshold // 40)

    points: list[int] = []
    for band, size in enumerate(sizes, 1):
        center = band * pitch
        values = [center - extreme, center + extreme]
        needed = (size - 2) // 2
        if needed >= bulk_limit:
            raise ValueError("modulus too small for distinct symmetric bulk points")
        # random.sample(range(...)) converts the range length through Py_ssize_t;
        # the 89/127-bit presets intentionally exceed that platform limit.
        deltas: set[int] = set()
        while len(deltas) < needed:
            deltas.add(rng.randrange(1, bulk_limit))
        for delta in sorted(deltas):
            values.extend((center - delta, center + delta))
        points.extend(values)

    if len(points) != n or len(set(points)) != n:
        raise RuntimeError("latent point construction lost a point")
    if min(points) < 0 or max(points) >= modulus:
        raise RuntimeError("latent coordinates escaped their residue interval")
    points.sort()
    return points, sizes, threshold, pitch


def _coordinates(inst: dict) -> list[int]:
    p, a, b = inst["modulus"], inst["multiplier"], inst["offset"]
    return sorted((a * z + b) % p for z in inst["encoded_points"])


def _cost_context(inst: dict) -> dict:
    """Precompute exact O(n^2) weights and all consecutive-segment scores."""

    xs = _coordinates(inst)
    n = len(xs)
    threshold = inst["threshold"]
    weights = [[0] * n for _ in range(n)]
    base = 0
    # Three operations for each affine residue coordinate: multiply, add, reduce.
    arithmetic_operations = 3 * n
    for i in range(n):
        for j in range(i + 1, n):
            w = threshold - (xs[j] - xs[i])
            arithmetic_operations += 2
            weights[i][j] = weights[j][i] = w
            if w > 0:
                base += w
                arithmetic_operations += 1

    # column_prefix[j][a] = sum_{i < a} weights[i][j].
    column_prefix = [[0] * (n + 1) for _ in range(n)]
    for j in range(n):
        running = 0
        for a in range(n):
            if a < j:
                running += weights[a][j]
                arithmetic_operations += 1
            column_prefix[j][a + 1] = running

    # segment[a][b] = sum of weights internal to the half-open interval [a,b).
    segment = [[0] * (n + 1) for _ in range(n + 1)]
    for a in range(n):
        for b in range(a + 2, n + 1):
            j = b - 1
            added = column_prefix[j][j] - column_prefix[j][a]
            segment[a][b] = segment[a][b - 1] + added
            arithmetic_operations += 2
    return {
        "x": xs,
        "weights": weights,
        "base": base,
        "segment": segment,
        "arithmetic_operations": arithmetic_operations,
    }


def _cost_from_context(ctx: dict, cuts: list[int]) -> int:
    n = len(ctx["x"])
    internal_score = 0
    start = 0
    for end in cuts + [n]:
        internal_score += ctx["segment"][start][end]
        start = end
    # sum w+ over all pairs minus sum w over within-cluster pairs is exactly
    # insertion cost within clusters plus deletion cost between clusters.
    return ctx["base"] - internal_score


def make_instance(
    n: int,
    seed: int = 0,
    q: int = 6,
    modulus_bits: int = 61,
    outlier_milli: int = 440,
    **params,
) -> dict:
    """Inverse-generate a weighted point graph and its short cut witness."""

    del params
    if n % 2:
        n += 1
    rng = random.Random(seed)
    actual_bits, modulus = _prime_for(modulus_bits)
    latent, sizes, threshold, _pitch = _latent_coordinates(
        n, q, modulus, outlier_milli, rng
    )

    multiplier = rng.randrange(2, modulus - 1)
    offset = rng.randrange(modulus)
    inverse = pow(multiplier, -1, modulus)
    encoded = [(inverse * (x - offset)) % modulus for x in latent]
    rng.shuffle(encoded)

    cuts: list[int] = []
    cumulative = 0
    for size in sizes[:-1]:
        cumulative += size
        cuts.append(cumulative)

    inst = {
        "paper": "arXiv:1310.3353",
        "n": n,
        "modulus_bits": actual_bits,
        "modulus": modulus,
        "multiplier": multiplier,
        "offset": offset,
        "threshold": threshold,
        "encoded_points": encoded,
    }
    inst["budget"] = _cost_from_context(_cost_context(inst), cuts)
    inst["answer"] = cuts
    return inst


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "Find a budget-feasible consecutive clustering of a one-dimensional weighted point graph.",
        "",
        "Definitions and exact instance.",
        f"There are {n} distinct points, represented by the following integers z:",
        " ".join(str(z) for z in inst["encoded_points"]),
        "",
        f"Let p = {inst['modulus']}, A = {inst['multiplier']}, and B = {inst['offset']}.",
        "For each displayed z, its line coordinate is x(z) = (A*z + B) mod p,",
        "where mod p means the least nonnegative residue in {0,...,p-1}.",
        "The distance between two points is the absolute difference of their x-coordinates.",
        f"Let L = {inst['threshold']}.  The pair weight is w(u,v) = L - |x(u)-x(v)|.",
        "Thus every pair is part of the weighted graph; a nonnegative weight is an edge.",
        "",
        "Sort all points by increasing x-coordinate and number their ranks 1 through n.",
        "A cut rank c (1 <= c <= n-1) places a cluster boundary after the first c points.",
        "A strictly increasing list of cut ranks therefore defines nonempty consecutive clusters.",
        "The list may contain any number of cuts, including zero; repeats are forbidden.",
        "For a pair placed in the same cluster, its cost is max(-w,0).",
        "For a pair placed in different clusters, its cost is max(w,0).",
        "The clustering cost is the sum of these integer costs over all unordered pairs.",
        f"Find any cut list whose cost is at most {inst['budget']} (inclusive).",
        "",
        "Give your final answer inside <answer></answer> tags, as increasing comma-separated integer cut ranks.",
        "Example: <answer>3, 17, 42</answer>",
        "For no cuts use <answer></answer>. Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(("", "Hint: " + STRUCTURAL_HINT))
    elif mode == "placebo":
        lines.extend(("", "Hint: " + PLACEBO_HINT))
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return []
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        tokens = [token.strip() for token in body.split(",")]
        if any(not re.fullmatch(r"[+-]?\d+", token) for token in tokens):
            return None
        return [int(token) for token in tokens]
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list) or any(
        not isinstance(c, int) or isinstance(c, bool) for c in answer
    ):
        return False, "malformed answer: expected a list of integer cut ranks"
    if len(set(answer)) != len(answer):
        return False, "duplicate cut: every cut rank must occur at most once"
    n = inst["n"]
    if any(c < 1 or c >= n for c in answer):
        return False, f"out-of-range cut: every rank must lie in 1..{n - 1}"
    if any(answer[i] >= answer[i + 1] for i in range(len(answer) - 1)):
        return False, "unordered cuts: ranks must be strictly increasing"

    cost = _cost_from_context(_cost_context(inst), answer)
    if cost > inst["budget"]:
        if not answer:
            return False, (
                f"empty clustering exceeds budget: cost {cost} > {inst['budget']}"
            )
        return False, f"budget exceeded: cost {cost} > {inst['budget']}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    # Uniform over all subsets of the n-1 legal cut positions.  Shape, ordering,
    # range, distinctness, and the statement's free arity constraint are built in.
    mask = rng.getrandbits(inst["n"] - 1)
    return [c for c in range(1, inst["n"]) if mask & (1 << (c - 1))]


def search_space(inst: dict) -> int | None:
    return 1 << (inst["n"] - 1)


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if n > 18:
        return None
    ctx = _cost_context(inst)
    count = 0
    for mask in range(1 << (n - 1)):
        cuts = [c for c in range(1, n) if mask & (1 << (c - 1))]
        if _cost_from_context(ctx, cuts) <= inst["budget"]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonical under input order, affine re-encoding, translation/reflection/scaling."""

    xs = _coordinates(inst)
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    values = gaps + [inst["threshold"], inst["budget"]]
    divisor = 0
    for value in values:
        divisor = math.gcd(divisor, abs(value))
    divisor = max(1, divisor)
    forward = [g // divisor for g in gaps]
    backward = list(reversed(forward))
    normal_gaps = min(forward, backward)
    return json.dumps(
        {
            "n": inst["n"],
            "gaps": normal_gaps,
            "threshold": inst["threshold"] // divisor,
            "budget": inst["budget"] // divisor,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def escalate(params: dict) -> dict | str | None:
    """Grow the cut haystack and arithmetic disguise while keeping five answer atoms."""

    p = dict(params)
    bits = int(p.get("modulus_bits", 61))
    outlier = int(p.get("outlier_milli", 440))
    n = int(p.get("n", 64))
    if n < 72:
        p["n"] = min(72, n + 8)
        p["modulus_bits"] = 89 if bits < 89 else bits
        p["outlier_milli"] = min(460, outlier + 10)
        return p
    if bits < 127:
        p["modulus_bits"] = 127 if bits >= 107 else (107 if bits >= 89 else 89)
        p["outlier_milli"] = min(475, outlier + 5)
        return p
    if outlier < 480:
        p["outlier_milli"] = min(480, outlier + 5)
        return p
    # Further n-growth would cross the 300-operation intended-route cap, and the
    # available fixed-length disguise/crowding axes have been exhausted.
    return None


def _reference_dynamic_program(inst: dict) -> tuple[list[int], int]:
    """Paper Algorithm 2 in maximum-internal-weight form."""

    ctx = _cost_context(inst)
    n = inst["n"]
    neg_inf = -(1 << 1000)
    best = [neg_inf] * (n + 1)
    previous = [0] * (n + 1)
    best[0] = 0
    transitions = 0
    for end in range(1, n + 1):
        for start in range(end):
            transitions += 1
            value = best[start] + ctx["segment"][start][end]
            if value > best[end]:
                best[end] = value
                previous[end] = start
    cuts: list[int] = []
    end = n
    while previous[end] > 0:
        end = previous[end]
        cuts.append(end)
    cuts.reverse()
    return cuts, ctx["arithmetic_operations"] + transitions


def _attack_raw_coordinate_outliers(inst: dict, q: int) -> list[int]:
    raw = sorted(inst["encoded_points"])
    gaps = [(raw[i] - raw[i - 1], i) for i in range(1, len(raw))]
    return sorted(i for _gap, i in sorted(gaps, reverse=True)[: q - 1])


def _attack_transformed_largest_gaps(inst: dict, q: int) -> list[int]:
    xs = _coordinates(inst)
    gaps = [(xs[i] - xs[i - 1], i) for i in range(1, len(xs))]
    return sorted(i for _gap, i in sorted(gaps, reverse=True)[: q - 1])


def _attack_equal_blocks(inst: dict, q: int) -> list[int]:
    return sorted({round(j * inst["n"] / q) for j in range(1, q)})


def _attack_agglomerative(inst: dict) -> list[int]:
    """Greedily merge the adjacent pair of blocks with greatest positive gain."""

    ctx = _cost_context(inst)
    weights = ctx["weights"]
    blocks = [(i, i + 1) for i in range(inst["n"])]
    while True:
        best: tuple[int, int] | None = None
        for index in range(len(blocks) - 1):
            a, b = blocks[index]
            c, d = blocks[index + 1]
            gain = sum(weights[i][j] for i in range(a, b) for j in range(c, d))
            if gain > 0 and (best is None or gain > best[0]):
                best = (gain, index)
        if best is None:
            break
        index = best[1]
        blocks[index : index + 2] = [(blocks[index][0], blocks[index + 1][1])]
    return [end for _start, end in blocks[:-1]]


def _attack_random_restart(
    inst: dict, q: int, rng: random.Random, restarts: int = 4096
) -> tuple[list[int] | None, int]:
    ctx = _cost_context(inst)
    for attempt in range(1, restarts + 1):
        cuts = sorted(rng.sample(range(1, inst["n"]), q - 1))
        if _cost_from_context(ctx, cuts) <= inst["budget"]:
            return cuts, attempt
    return None, restarts


def _reencode(inst: dict, xs: list[int], multiplier: int, offset: int) -> dict:
    transformed = copy.deepcopy(inst)
    p = inst["modulus"]
    inverse = pow(multiplier, -1, p)
    transformed["multiplier"] = multiplier
    transformed["offset"] = offset
    transformed["encoded_points"] = [
        (inverse * (x - offset)) % p for x in xs
    ]
    return transformed


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer)

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    return len(blob), max(1, math.ceil(len(blob) / 4)), atoms(answer)


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every named preset, several independent seeds.
    g1_attempts = 0
    g1_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    sample = make_instance(seed=314159, **shipping_params)
    planted = sample["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate": planted[:1] + planted,
        "empty": [],
        "out_of_range": [0] + planted[1:],
    }
    corruption_reasons: dict[str, str] = {}
    corruption_ok = True
    for name, candidate in corruptions.items():
        ok, why = verify(sample, candidate)
        corruption_ok = corruption_ok and not ok
        corruption_reasons[name] = why
    distinct_reasons = len(set(corruption_reasons.values())) == len(corruption_reasons)
    report["G2_rejects_corruption"] = {
        "pass": corruption_ok and distinct_reasons,
        "distinct_reasons": distinct_reasons,
        "reasons": corruption_reasons,
    }

    body = ", ".join(str(c) for c in planted)
    realistic = f"I computed the transformed ranks.\n```text\n<answer>{body}</answer>\n```"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed": parsed,
    }

    # G4/G5 shipping density: reuse one exact O(n^2) precomputation.
    ctx = _cost_context(sample)
    guess_rng = random.Random(0x13103353)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(sample, guess_rng)
        if _cost_from_context(ctx, candidate) <= sample["budget"]:
            guess_hits += 1
    density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": density,
        "candidate_space": search_space(sample),
        "sampler": "uniform over all legal increasing subsets of cut ranks",
    }

    # G6 panel.  The exact DP is intentionally separate on Track B.
    attack_seeds = list(range(800, 808))
    attack_names = (
        "outlier_raw_coordinate_gaps",
        "greedy_transformed_largest_gaps",
        "random_restart_4096",
        "agglomerative_positive_gain",
        "equal_size_ansatz",
    )
    attack_results = {
        name: {"successes": 0, "attempts": len(attack_seeds), "wall_clock_sec": 0.0}
        for name in attack_names
    }
    random_iterations = 0
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        q = shipping_params["q"]
        candidates: dict[str, object] = {}

        start = time.perf_counter()
        candidates["outlier_raw_coordinate_gaps"] = _attack_raw_coordinate_outliers(inst, q)
        attack_results["outlier_raw_coordinate_gaps"]["wall_clock_sec"] += time.perf_counter() - start

        start = time.perf_counter()
        candidates["greedy_transformed_largest_gaps"] = _attack_transformed_largest_gaps(inst, q)
        attack_results["greedy_transformed_largest_gaps"]["wall_clock_sec"] += time.perf_counter() - start

        start = time.perf_counter()
        restart_answer, used = _attack_random_restart(
            inst, q, random.Random(seed ^ 0xA5A5), 4096
        )
        random_iterations += used
        candidates["random_restart_4096"] = restart_answer
        attack_results["random_restart_4096"]["wall_clock_sec"] += time.perf_counter() - start

        start = time.perf_counter()
        candidates["agglomerative_positive_gain"] = _attack_agglomerative(inst)
        attack_results["agglomerative_positive_gain"]["wall_clock_sec"] += time.perf_counter() - start

        start = time.perf_counter()
        candidates["equal_size_ansatz"] = _attack_equal_blocks(inst, q)
        attack_results["equal_size_ansatz"]["wall_clock_sec"] += time.perf_counter() - start

        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1

        start = time.perf_counter()
        reference_answer, operations = _reference_dynamic_program(inst)
        reference_wall += time.perf_counter() - start
        reference_operations += operations
        if verify(inst, reference_answer)[0]:
            reference_successes += 1

    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    reference = {
        "name": "Theorem 2 / Algorithm 2 consecutive-clustering dynamic program",
        "complexity": "O(n^2) exact integer arithmetic",
        "wall_clock_sec": round(reference_wall, 6),
        "average_wall_clock_sec": round(reference_wall / len(attack_seeds), 6),
        "operations": reference_operations,
        "operations_per_instance": reference_operations // len(attack_seeds),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    demo = make_instance(seed=23, **DIFFICULTY["demo"])
    exact_demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and all_failed,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": density,
        "demo_exact_solution_count": exact_demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_attack_wall_clock_sec": attack_results["random_restart_4096"]["wall_clock_sec"],
        "baseline_attack_iterations": random_iterations,
        "baseline_attack_successes": attack_results["random_restart_4096"]["successes"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * sample["n"],
        "base_n": sample["n"],
        "doubled_n": doubled["n"],
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    preserved_witness_checks = 0
    distinct_keys: list[str] = []
    g8_failures: list[str] = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(inst)
        distinct_keys.append(key)
        xs = _coordinates(inst)
        rng = random.Random(20_000 + seed)

        reordered = copy.deepcopy(inst)
        rng.shuffle(reordered["encoded_points"])
        transforms: list[tuple[str, dict, list[int]]] = [
            ("input_reordering", reordered, inst["answer"]),
        ]

        a2 = rng.randrange(2, inst["modulus"] - 1)
        b2 = rng.randrange(inst["modulus"])
        transforms.append(("affine_reencoding", _reencode(inst, xs, a2, b2), inst["answer"]))

        room = inst["modulus"] - 1 - max(xs)
        shift = min(max(1, inst["threshold"] // 17), room)
        shifted_xs = [x + shift for x in xs]
        transforms.append(("translation", _reencode(inst, shifted_xs, a2, b2), inst["answer"]))

        reflected_xs = [max(xs) + min(xs) - x for x in reversed(xs)]
        reflected_answer = sorted(inst["n"] - c for c in inst["answer"])
        reflected = _reencode(inst, reflected_xs, a2, b2)
        rng.shuffle(reflected["encoded_points"])
        transforms.append(("reflection_composed_with_reencoding", reflected, reflected_answer))

        for name, transformed, carried_answer in transforms:
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed under {name}")
            ok, why = verify(transformed, carried_answer)
            preserved_witness_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}: {name} broke witness ({why})")

    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "witness_preservation_checks": preserved_witness_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": 20,
        "failures": g8_failures,
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(sample["answer"])
    intended_operations = 4 * sample["n"] + len(sample["answer"])
    arms_measured = all(v["attempts"] >= 3 for v in G9_ARM_RESULTS.values())
    hinted_hardened = G9_HINTED_VERDICT == "hardened"
    hinted_rate = (
        G9_ARM_RESULTS["hinted"]["solved"] / G9_ARM_RESULTS["hinted"]["attempts"]
        if G9_ARM_RESULTS["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        G9_ARM_RESULTS["placebo"]["solved"] / G9_ARM_RESULTS["placebo"]["attempts"]
        if G9_ARM_RESULTS["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": arms_measured and hinted_hardened and within_caps,
        "arms": copy.deepcopy(G9_ARM_RESULTS),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [v for k, v in report.items() if k.startswith("G") and isinstance(v, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
