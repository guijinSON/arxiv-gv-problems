"""Projective-hyperplane block recovery for arXiv:2409.09730.

Lemma 4.1 constructs point- and block-primitive designs from a maximal-subgroup
orbit, and Remark 1 upgrades the construction when the point action is multiply
transitive. Here PGL(d,p) acts on projective points and a hyperplane stabilizer
supplies the block orbit. A normalized covector exactly certifies that block.
"""

from __future__ import annotations

import hashlib
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
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "projective points represented by vectors over GF(p)",
        "a hyperplane block represented by a normalized covector",
        "the PGL(d,p)-orbit 2-design of projective hyperplanes",
    ],
    "verification_operations": [
        "exact modular range and normalization checks",
        "exact finite-field point-covector inner products",
        "exact projective hyperplane incidence checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the dense hyperplane frame as the inverse of a two-tap "
        "cyclic operator, so its last coordinates determine the normal without "
        "dense elimination."
    ),
    "hardness_basis": (
        "Track B: modular Gaussian elimination recovers the hyperplane normal "
        "in O(d^3); at shipping d=72 over GF(4099) it averaged 42,650 exact "
        "field operations and 0.0024 seconds, while the cyclic inverse route "
        "uses exactly 213 exact operations and must be recognized and executed "
        "without tools."
    ),
    "max_answer_tokens": 91,
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
    "demo": {"n": 5, "p": 7},
    "easy": {"n": 48, "p": 257},
    "medium": {"n": 72, "p": 4099},
    "hard": {"n": 96, "p": 65537},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "Hint: Undo the dense frame with the two-tap cyclic change of variables "
    "defined by the displayed coordinate cycle."
)
PLACEBO_HINT = (
    "Hint: Keep the coordinate labels aligned and reduce every intermediate "
    "quantity modulo the displayed prime."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON 1-by-n matrix [[h_0,...,h_(n-1)]] over GF(p), with every "
        "entry in 0,...,p-1 and the stated normalization coordinate equal to 1."
    ),
    "bounds": {
        "rows": 1,
        "columns": "n",
        "entry_min": 0,
        "entry_max": "p-1",
        "normalization_entry": 1,
        "candidate_count": "p^(n-1)",
        "max_shipping_rows": 1,
        "max_shipping_columns": 72,
        "max_shipping_prime": 4099,
    },
}

NOTES = r"""
Paper definition and construction. Section 2 defines a t-(v,k,lambda) design
as a constant-size block system in which every t-set of points has constant
incidence, and defines point/block primitivity for an invariant permutation
group. Lemma 4.1 says that, for primitive G on Omega and a suitable maximal
subgroup M, an M-orbit Delta has a G-orbit forming a point- and block-primitive
1-design. Remark 1 upgrades it to a t-design when G is t-transitive. We take
G=PGL(d,p) on the points of PG(d-1,p), a 2-transitive action. The stabilizer M
of a projective hyperplane is maximal and has the same index as a point
stabilizer. Its orbit on the points lying in that hyperplane is Delta. Thus its
G-orbit is the point/hyperplane 2-design, with v=b=(p^d-1)/(p-1),
k=r=(p^(d-1)-1)/(p-1), and lambda=(p^(d-2)-1)/(p-1).

STEP 0 hardness decision. The paper proves no average-case hardness. Moreover,
the submitted covector is the one-dimensional nullspace of the displayed
(d-1)-by-d frame, so modular Gaussian elimination finds it in O(d^3). A Track A
claim would therefore be false. This is Track B: selftest reports the measured
elimination cost at the shipping preset. The compact route separates the
normalization column b from the dense square block A. Construction makes
A=(I+3P)^(-1), where (Pz)_i=z_(rho(i)) for the displayed cycle rho. The frame
equations are A x+b=0, hence x=-(I+3P)b. Computing the d-1 coordinates takes
one multiplication, one addition, and one negation each: 3(d-1) exact field
operations, below the no-tool cap but well beyond a casual visual guess.

Inverse generation. A normalized covector h=(x,1) is sampled uniformly first.
The cycle rho is sampled independently. The geometric-series identity
(I+3P)^(-1) = (1-(-3)^(d-1))^(-1) sum_j (-3)^j P^j constructs A directly,
and b=-Ax constructs d-1 independent projective points (A_i,b_i) incident
with h. The certificate exists before the public frame; it is never recovered
by solving that frame.

What is easy in the paper. Theorem 3.2 makes every orbit of a supplied base
block a block-transitive 1-design, and Lemma 4.1 directly supplies the design
once M and one of its point orbits are given. Asking for that orbit when M is
explicit would only require ordinary orbit traversal. Proposition 3.3 and
Tables 1-3 are MAGMA classifications/explicit parameter lists, so asking for
one listed design would be lookup rather than a scalable hard family. This
module instead hides one native hyperplane block behind its incident frame and
reports the polynomial reference algorithm honestly.

Attacks and presentation. The normal is uniform over every covector allowed by
the statement, so plant and random candidates have the same coordinate prior.
The panel tests a one-column outlier fit, greedy coordinate repair, 256 uniform
restarts, and obvious last-column/one-shift ansatzes. The exact two-tap identity
is the intended insight and is not mislabeled as a failing attack.
canonical_key solves only for the represented hyperplane and records its
covector values around the supplied directed cycle, modulo cyclic rotation; it
is invariant under reordering/rescaling point representatives and arbitrary
coordinate relabelling. General projective basis changes need not preserve the
supplied cycle as a coordinate permutation and are outside this input language.
""".strip()


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)
_TAP = 3


def _is_prime(value: int) -> bool:
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


def _random_cycle(size: int, rng: random.Random) -> list[int]:
    order = list(range(size))
    rng.shuffle(order)
    rho = [0] * size
    for i, value in enumerate(order):
        rho[value] = order[(i + 1) % size]
    return rho


def _inverse_two_tap(size: int, p: int, rho: list[int]) -> list[list[int]]:
    """Return (I + 3P_rho)^-1 using a finite geometric identity."""
    ratio = (-_TAP) % p
    denominator = (1 - pow(ratio, size, p)) % p
    if denominator == 0:
        raise ValueError("I + 3P is singular for these parameters")
    scale = pow(denominator, p - 2, p)
    matrix = [[0] * size for _ in range(size)]
    for row in range(size):
        column = row
        coefficient = scale
        for _ in range(size):
            matrix[row][column] = coefficient
            coefficient = coefficient * ratio % p
            column = rho[column]
    return matrix


def _dot(row: list[int], vector: list[int], p: int) -> int:
    return sum(a * b for a, b in zip(row, vector)) % p


def make_instance(n: int, seed: int = 0, p: int = 257, **params) -> dict:
    """Inverse-generate a projective hyperplane and an incident dense frame."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if not _is_prime(p) or p <= _TAP:
        raise ValueError("p must be a prime greater than 3")

    size = n - 1
    rng = random.Random(seed)
    rho = _random_cycle(size, rng)
    matrix = _inverse_two_tap(size, p, rho)
    x = [rng.randrange(p) for _ in range(size)]
    last_column = [(-_dot(row, x, p)) % p for row in matrix]
    points = [
        {"label": i, "coordinates": matrix[i] + [last_column[i]]}
        for i in range(size)
    ]
    answer = [x + [1]]
    v = (pow(p, n) - 1) // (p - 1)
    k = (pow(p, n - 1) - 1) // (p - 1)
    lam = (pow(p, n - 2) - 1) // (p - 1)
    return {
        "family": "projective hyperplane orbit design block recovery",
        "field_prime": p,
        "dimension": n,
        "normalization_coordinate": n - 1,
        "cycle": rho + [n - 1],
        "tap_coefficient": _TAP,
        "frame_points": points,
        "design_parameters": {
            "t": 2, "v": v, "b": v, "k": k, "r": k, "lambda": lam,
        },
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete native projective-hyperplane recovery problem."""
    p = inst["field_prime"]
    n = inst["dimension"]
    norm = inst["normalization_coordinate"]
    cycle = inst["cycle"]
    active = [i for i in range(n) if i != norm]
    point_lines = "\n".join(
        f"{point['label']}: "
        + " ".join(str(value) for value in point["coordinates"])
        for point in inst["frame_points"]
    )
    cycle_line = " ".join(f"{i}->{cycle[i]}" for i in active)
    pars = inst["design_parameters"]
    statement = f"""Recover a block of a point- and block-primitive projective design

All arithmetic is in the prime field GF({p}), represented by the integers
0,...,{p - 1} with reduction modulo {p}. The ambient projective space is
PG({n - 1},{p}): a projective point is a nonzero vector z in GF({p})^{n}, where
nonzero scalar multiples represent the same point. A nonzero row covector h
defines a projective hyperplane block

    H_h = {{ [z] : sum_(j=0 to {n - 1}) h_j z_j = 0 modulo {p} }}.

The group PGL({n},{p}) acts on these projective points. Its orbit on the
hyperplane blocks is a 2-design with parameters

    2-(v={pars['v']}, k={pars['k']}, lambda={pars['lambda']}),

with b={pars['b']} blocks and r={pars['r']} blocks through each point.

Below are {n - 1} linearly independent representatives of projective points
that lie in one unknown block H_h. Coordinates and point labels are 0-based.
Each line has a point label, a colon, and exactly {n} coordinates in order
0,...,{n - 1}. Point order is irrelevant; labels are distinct.

{point_lines}

The following directed cycle on every coordinate except {norm} is part of the
presentation (the normalization coordinate {norm} is fixed):
{cycle_line}

Find the unique representative h of the unknown hyperplane normal satisfying
h_{norm}=1. Your answer must be one JSON matrix row: [[h_0,...,h_{n - 1}]].
It must contain exactly {n} integers, each in the inclusive range 0 through
{p - 1}, in coordinate order. Coordinate values may repeat; exactly one entry
per coordinate is required, with no fractions. The outer list and its single
inner row are both required.

Give your final answer inside <answer></answer> tags, as the JSON 1-by-{n} matrix.
Example: <answer>[[3,0,6,1]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON matrix, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized hyperplane covector by exact incidence tests."""
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON matrix"
    if len(answer) != 1:
        return False, f"answer matrix must have exactly one row, got {len(answer)}"
    row = answer[0]
    if not isinstance(row, list):
        return False, "the sole matrix row must be a JSON list"
    if len(row) != n:
        return False, f"matrix row has wrong length: expected {n}, got {len(row)}"
    for j, value in enumerate(row):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"coordinate {j} is not an integer"
        if not 0 <= value < p:
            return False, f"coordinate {j} is outside 0..{p - 1}"
    if row[norm] != 1:
        return False, f"normalization coordinate {norm} must equal 1"
    for point in inst["frame_points"]:
        if _dot(point["coordinates"], row, p) != 0:
            return False, (
                f"point {point['label']} is not incident with the proposed hyperplane"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing shape, field, and normalization."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    row = [rng.randrange(p) for _ in range(n)]
    row[norm] = 1
    return [row]


def search_space(inst: dict) -> int | None:
    return pow(inst["field_prime"], inst["dimension"] - 1)


def enumerate_all(inst: dict) -> int | None:
    """Enumerate only bounded languages of at most 200,000 candidates."""
    total = search_space(inst)
    if total is None or total > 200_000:
        return None
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    active = [j for j in range(n) if j != norm]
    row = [0] * n
    row[norm] = 1
    count = 0
    for code in range(total):
        value = code
        for j in active:
            row[j] = value % p
            value //= p
        count += int(verify(inst, [list(row)])[0])
    return count


def _gaussian_normal(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Generic modular elimination for the normalized nullspace."""
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    variables = [j for j in range(n) if j != norm]
    aug = []
    for point in inst["frame_points"]:
        coords = point["coordinates"]
        aug.append(
            [coords[j] % p for j in variables] + [(-coords[norm]) % p]
        )
    operations = 0
    pivot_row = 0
    pivot_cols: list[int] = []
    for column in range(n - 1):
        pivot = next(
            (r for r in range(pivot_row, len(aug)) if aug[r][column] % p),
            None,
        )
        if pivot is None:
            continue
        aug[pivot_row], aug[pivot] = aug[pivot], aug[pivot_row]
        inverse = pow(aug[pivot_row][column], p - 2, p)
        operations += 1
        for j in range(column, n):
            aug[pivot_row][j] = aug[pivot_row][j] * inverse % p
            operations += 1
        for r in range(len(aug)):
            if r == pivot_row:
                continue
            factor = aug[r][column]
            if factor == 0:
                continue
            for j in range(column, n):
                aug[r][j] = (
                    aug[r][j] - factor * aug[pivot_row][j]
                ) % p
                operations += 2
        pivot_cols.append(column)
        pivot_row += 1
        if pivot_row == n - 1:
            break
    if pivot_row != n - 1:
        return None, operations
    solution = [0] * n
    solution[norm] = 1
    for r, column in enumerate(pivot_cols):
        solution[variables[column]] = aug[r][n - 1]
    return [solution], operations


def _canonical_cycle(inst: dict) -> tuple[int, ...] | None:
    solved, _ = _gaussian_normal(inst)
    if solved is None:
        return None
    normal = solved[0]
    norm = inst["normalization_coordinate"]
    rho = inst["cycle"]
    active = [j for j in range(inst["dimension"]) if j != norm]
    current = active[0]
    sequence = []
    for _ in range(len(active)):
        sequence.append(normal[current])
        current = rho[current]
    rotations = [
        tuple(sequence[i:] + sequence[:i]) for i in range(len(sequence))
    ]
    return min(rotations)


def canonical_key(inst: dict) -> str:
    """Canonicalize the normal along the directed cycle, up to relabelling."""
    payload = {
        "family": "projective-hyperplane-frame-v1",
        "p": inst["field_prime"],
        "n": inst["dimension"],
        "cycle_normal": _canonical_cycle(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise field entropy at fixed answer length before approaching any cap."""
    if not isinstance(params, dict) or set(params) != {"n", "p"}:
        return None
    n = params["n"]
    p = params["p"]
    if n == 96 and p == 65537:
        return {"n": 96, "p": 1_000_003}
    if n == 96 and p == 1_000_003:
        return {"n": 96, "p": 1_000_000_007}
    return "cap_bound"


def _cycle_apply(inst: dict, values: list[int], steps: int = 1) -> list[int]:
    rho = inst["cycle"]
    norm = inst["normalization_coordinate"]
    result = list(values)
    for _ in range(steps):
        previous = result
        result = [0] * len(values)
        for i in range(len(values)):
            result[i] = previous[i] if i == norm else previous[rho[i]]
    return result


def _last_column_by_label(inst: dict) -> list[int]:
    n = inst["dimension"]
    norm = inst["normalization_coordinate"]
    values = [0] * n
    for point in inst["frame_points"]:
        values[point["label"]] = point["coordinates"][norm]
    values[norm] = 0
    return values


def _outlier_one_column(inst: dict) -> list[list[int]]:
    """Fit each coordinate alone to the normalization-column residual."""
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    row = [0] * n
    row[norm] = 1
    for column in range(n):
        if column == norm:
            continue
        counts: dict[int, int] = {}
        for point in inst["frame_points"]:
            coefficient = point["coordinates"][column]
            if coefficient:
                proposal = (
                    -point["coordinates"][norm]
                    * pow(coefficient, p - 2, p)
                ) % p
                counts[proposal] = counts.get(proposal, 0) + 1
        if counts:
            row[column] = min(
                counts, key=lambda value: (-counts[value], value)
            )
    return [row]


def _greedy_repair(
    inst: dict, passes: int = 2
) -> tuple[list[list[int]], int]:
    """Coordinate descent maximizing the number of incident points."""
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    row = [0] * n
    row[norm] = 1
    points = inst["frame_points"]
    residual = [point["coordinates"][norm] % p for point in points]
    steps = 0
    for _ in range(passes):
        changed = False
        for column in range(n):
            if column == norm:
                continue
            counts: dict[int, int] = {}
            for i, point in enumerate(points):
                coefficient = point["coordinates"][column]
                if coefficient:
                    delta = (
                        -residual[i] * pow(coefficient, p - 2, p)
                    ) % p
                    counts[delta] = counts.get(delta, 0) + 1
            steps += len(points)
            if not counts:
                continue
            delta, gain = min(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
            current = sum(value == 0 for value in residual)
            if delta and gain > current:
                row[column] = (row[column] + delta) % p
                residual = [
                    (
                        residual[i]
                        + delta * point["coordinates"][column]
                    ) % p
                    for i, point in enumerate(points)
                ]
                changed = True
        if not changed:
            break
    return [row], steps


def _random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[bool, int]:
    for attempt in range(1, restarts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, attempt
    return False, restarts


def _obvious_cycle_ansatz(inst: dict) -> tuple[bool, int]:
    """Try direct/scaled/one-shift readings, not the intended two-tap sum."""
    n = inst["dimension"]
    p = inst["field_prime"]
    norm = inst["normalization_coordinate"]
    b = _last_column_by_label(inst)
    pb = _cycle_apply(inst, b)
    p2b = _cycle_apply(inst, b, 2)
    candidates: list[list[list[int]]] = []
    for source in (b, pb, p2b):
        for scalar in (1, p - 1, _TAP, (-_TAP) % p):
            row = [(scalar * value) % p for value in source]
            row[norm] = 1
            candidates.append([row])
    for left, right in ((b, pb), (b, p2b), (pb, p2b)):
        row = [(left[i] + right[i]) % p for i in range(n)]
        row[norm] = 1
        candidates.append([row])
    zero = [0] * n
    zero[norm] = 1
    candidates.append([zero])
    for candidate in candidates:
        if verify(inst, candidate)[0]:
            return True, len(candidates)
    return False, len(candidates)


def _relabel_instance(inst: dict, order: list[int]) -> dict:
    """Permute ambient coordinates and carry labels, cycle, and witness."""
    n = inst["dimension"]
    inverse = [0] * n
    for new, old in enumerate(order):
        inverse[old] = new
    moved = dict(inst)
    moved["normalization_coordinate"] = inverse[
        inst["normalization_coordinate"]
    ]
    moved["cycle"] = [
        inverse[inst["cycle"][order[j]]] for j in range(n)
    ]
    moved["frame_points"] = [
        {
            "label": inverse[point["label"]],
            "coordinates": [
                point["coordinates"][order[j]] for j in range(n)
            ],
        }
        for point in inst["frame_points"]
    ]
    moved["answer"] = [[inst["answer"][0][order[j]] for j in range(n)]]
    return moved


def _rescale_and_reorder(inst: dict, rng: random.Random) -> dict:
    p = inst["field_prime"]
    moved = dict(inst)
    points = []
    for point in inst["frame_points"]:
        scalar = rng.randrange(1, p)
        points.append({
            "label": point["label"],
            "coordinates": [
                (scalar * value) % p for value in point["coordinates"]
            ],
        })
    rng.shuffle(points)
    moved["frame_points"] = points
    moved["answer"] = [list(inst["answer"][0])]
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    elements = (
        len(answer[0])
        if isinstance(answer, list) and len(answer) == 1
        else 0
    )
    return len(encoded), math.ceil(len(encoded) / 4), elements


def selftest() -> dict:
    """Run every correctness, resistance, scale, symmetry, and size gate."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every named preset over three independent seeds, including JSON.
    g1_attempts = 0
    g1_failures = []
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
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    planted = ship["answer"][0]
    differing = next(
        i
        for i in range(len(planted) - 2)
        if planted[i] != planted[i + 1]
    )
    swapped = list(planted)
    swapped[differing], swapped[differing + 1] = (
        swapped[differing + 1], swapped[differing]
    )
    corruptions = {
        "drop": [planted[:-1]],
        "swap": [swapped],
        "duplicate": [list(planted), list(planted)],
        "empty": [],
        "out_of_range": [[ship["field_prime"]] + planted[1:]],
    }
    corruption_results = {
        name: {
            "accepted": verify(ship, candidate)[0],
            "reason": verify(ship, candidate)[1],
        }
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    compact_answer = json.dumps(ship["answer"], separators=(",", ":"))
    realistic = (
        "The normal was obtained after modular reduction.\n```json\n"
        f"<answer>\n{compact_answer}\n</answer>\n```\n"
        "The tagged object is the requested one-row matrix."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"] and verify(ship, parsed)[0],
        "parsed_matches": parsed == ship["answer"],
        "realistic_wrapper": True,
    }

    # G4: candidates already satisfy all syntactic and normalization rules.
    guess_rng = random.Random(0x240909730)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(
            verify(ship, random_candidate(ship, guess_rng))[0]
        )
    guess_elapsed = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "exact_solution_fraction": 1 / search_space(ship),
        "sampling_prior": "uniform normalized 1-by-n covectors over GF(p)",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    # G6: four failing no-tool attacks; elimination is separate for Track B.
    attack_names = (
        "outlier_one_column_fit",
        "greedy_coordinate_repair",
        "random_restart_256",
        "obvious_cycle_ansatz",
    )
    attack_stats = {
        name: {
            "successes": 0,
            "attempts": 0,
            "steps": 0,
            "wall_clock_sec": 0.0,
        }
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping)

        t0 = time.perf_counter()
        candidate = _outlier_one_column(inst)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["outlier_one_column_fit"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += (inst["dimension"] - 1) ** 2
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _greedy_repair(inst)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["greedy_coordinate_repair"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _random_restart(
            inst, random.Random(seed ^ 0xA551), 256
        )
        elapsed = time.perf_counter() - t0
        stat = attack_stats["random_restart_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _obvious_cycle_ansatz(inst)
        elapsed = time.perf_counter() - t0
        stat = attack_stats["obvious_cycle_ansatz"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        solution, operations = _gaussian_normal(inst)
        elapsed = time.perf_counter() - t0
        reference_wall += elapsed
        reference_operations += operations
        reference_successes += int(
            solution is not None and verify(inst, solution)[0]
        )

    for stat in attack_stats.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(
        stat["successes"] == 0 for stat in attack_stats.values()
    )
    reference_average = reference_operations // 8
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "dense modular Gaussian elimination",
            "complexity": "O(d^3) exact field operations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations_per_instance": reference_average,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    # G5: invertibility certifies uniqueness at shipping; demo is enumerated.
    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(
        attack_stats.items(), key=lambda item: item[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == 8,
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": 1 / search_space(ship),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_bruteforce_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations_per_instance": reference_average,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": (
            strongest_failing[1]["wall_clock_sec"]
        ),
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    ladder_spaces = [
        search_space(make_instance(seed=7, **params))
        for params in DIFFICULTY.values()
    ]
    doubled = make_instance(
        n=2 * shipping["n"], p=shipping["p"], seed=909
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": ladder_spaces == sorted(set(ladder_spaces)) and doubled_ok,
        "preset_candidate_spaces": dict(zip(DIFFICULTY, ladder_spaces)),
        "doubled_n": doubled["dimension"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "fixed_length_escalation": {"n": 96, "p": 1_000_003},
    }

    # G8: coordinates, point order, and projective representatives are labels.
    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(n=25, p=257, seed=20_000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        order = list(range(inst["dimension"]))
        rng.shuffle(order)
        relabelled = _relabel_instance(inst, order)
        rescaled = _rescale_and_reorder(inst, rng)
        composed = _rescale_and_reorder(relabelled, rng)
        for number, moved in enumerate(
            (relabelled, rescaled, composed)
        ):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                invariant_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant_failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary ambient-coordinate relabelling",
            "projective rescaling and reordering of point representatives",
            "composition of coordinate relabelling, rescaling, and point reordering",
        ],
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = 3 * (ship["dimension"] - 1)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(
        1, arms["hinted"]["attempts"]
    )
    placebo_rate = arms["placebo"]["solved"] / max(
        1, arms["placebo"]["attempts"]
    )
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] >= tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": (
            G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
            and within_caps
        ),
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [
        value for key, value in report.items() if key.startswith("G")
    ]
    report["all_passed"] = all(
        gate.get("pass") is True for gate in gates
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
