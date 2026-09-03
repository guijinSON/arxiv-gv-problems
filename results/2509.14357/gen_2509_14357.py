"""Verified planted Freeze-Tag schedules from arXiv:2509.14357.

The public problem is the exact planar L1 construction of Section 3.3.  A
witness is its forced normal-form schedule, represented by the two permutations
from Lemmas 3.6 and 3.7.  Generation and all checks use only integer arithmetic.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re


DIFFICULTY = {
    "standard": {"n": 125, "band": 2},
    "hard": {"n": 170, "band": 2},
    "extreme": {"n": 225, "band": 2},
}
SHIPPING_DIFFICULTY = "standard"

NOTES = r"""
Definition.  Section 2 of de Oliveira Silva and Pedrosa, "Freeze-Tag is
Strongly NP-hard in 2D with L_p Distances" (arXiv:2509.14357v4), defines an
FTP schedule as a rooted wake-up tree: the source has at most one child, every
other robot at most two, and a vertex's activation time is its root-path
length.  Section 3.3 gives an integer-coordinate L1 construction.  Lemma 3.6
forces every deadline-feasible tree into a backbone through all A robots, one
A-to-B assignment per A, and two B-to-C assignments per B.  Lemma 3.7 and
Section 3.3.4 identify those assignments with two distinct-input N3DM
permutations.  This module asks for exactly that normal-form schedule.

Hard and easy regimes.  Theorem 3.1 proves strong NP-completeness for planar
L1 FTP with integer locations and an integer deadline; the final paragraph of
Section 3 transfers strong ASP-hardness to rational schedules.  Section 1 also
records a PTAS in fixed-dimensional Lp spaces and polynomial solvability for
unweighted stars.  Neither makes exact search in this planar construction
easy: approximation is not exact feasibility at the tight deadline, and the
constructed metric is neither a star nor an unweighted star instance.  We use
p=1 so that verification never needs algebraic-number comparisons.

Inverse generation.  Two answer permutations are shuffled before any numbers
or robot positions are sampled.  For each planted triple, three distinct
integer deviations summing to zero are sampled, randomly permuted among U, V,
and W, and rejected on any global collision.  Thus all 3n N3DM values are
distinct, every planted triple sums to q, and all three roles have the same
marginal construction distribution.  The paper's formulas then produce the
robots and deadline.  Input lines are independently shuffled.

Attacks.  The adversary panel attacks the generator rather than generic noise:
(1) a per-element degree/outlier rule prioritizes the rarest compatible A, B,
and C values; (2) a left-to-right nearest feasible rule follows backbone order;
(3) randomized minimum-remaining-values greedy search performs 64 restarts;
and (4) an index-alignment rule tests whether generation order leaked through
the labels.  A fifth attack runs exact MRV backtracking for 100,000 search nodes.
It exposed the original n=40 preset as easy (all three sampled instances solved
in at most 1.9 seconds), so that preset was discarded and the shipped n was
raised to 125.  Shipping requires all five to fail on eight independent seeds.

Canonicalization.  Robot identifiers and input order are presentation only.
The structural key sorts role-tagged locations after translating the source to
the origin and takes the minimum over all eight L1 signed-axis symmetries.  It
therefore removes arbitrary within-role relabelling, C-copy swaps, input order,
global translation, reflection, rotation, and every tested composition.  It
does not attempt to detect accidental non-geometric isometries of a finite
point set; that limitation is documented in README.md.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _l1(p: tuple[int, int], q: tuple[int, int]) -> int:
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def _sample_values(
    n: int,
    band: int,
    pi: list[int],
    sigma: list[int],
    rng: random.Random,
) -> tuple[list[int], list[int], list[int], int]:
    """Sample globally distinct values around a common center.

    Roles are permuted independently inside every planted triple.  This avoids
    making the derived third value recognizable by its one-dimensional
    distribution.
    """
    center = (band + 1) * n
    radius = band * n
    q = 3 * center
    for _restart in range(100):
        used: set[int] = set()
        u = [0] * n
        v = [0] * n
        w = [0] * n
        for i in range(n):
            for _attempt in range(20_000):
                dx = rng.randint(-radius, radius)
                dy = rng.randint(-radius, radius)
                dz = -dx - dy
                if not -radius <= dz <= radius:
                    continue
                values = [center + dx, center + dy, center + dz]
                if len(set(values)) != 3 or any(x in used for x in values):
                    continue
                rng.shuffle(values)
                u[i], v[pi[i]], w[sigma[i]] = values
                used.update(values)
                break
            else:
                break
        else:
            return u, v, w, q
    raise RuntimeError("could not sample distinct planted triples")


def _geometry(
    u: list[int], v: list[int], w: list[int], q: int
) -> tuple[int, list[dict]]:
    """Apply the exact p=1 coordinates in Equation (3), Section 3.3."""
    n = len(u)
    a = 2 * q
    h_b = 10 * q
    b = (n + 1) * h_b + q
    span = 2 * a + 2 * b + 2 * q
    h_c = 10 * span
    c = (2 * n + 1) * h_c + 2 * q
    deadline = c + span

    robots = [
        {"id": "O", "role": "source", "x": 0, "y": 0},
        {"id": "Z", "role": "terminal", "x": deadline, "y": 0},
    ]
    for i, value in enumerate(u):
        robots.append({"id": f"A{i}", "role": "A", "x": a + value, "y": 0})
    for j, value in enumerate(v):
        x = -(j + 1) * h_b
        robots.append(
            {"id": f"B{j}", "role": "B", "x": x,
             "y": -(b + value - (j + 1) * h_b)}
        )
    for k, value in enumerate(w):
        for copy in (1, 2):
            tau = 2 * k + copy
            x = tau * h_c
            robots.append(
                {"id": f"C{k}.{copy}", "role": "C", "x": x,
                 "y": c + 2 * value - x}
            )
    return deadline, robots


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a normal-form answer first, then construct its planar L1 FTP.

    ``n`` is the number of A, B, and paired-C choices.  The instance has
    ``4*n+2`` robots and a witness space of ``(n!)^2``, so increasing ``n``
    strictly enlarges both the public instance and the structured search space.
    ``band`` controls the value band; the shipped value 2 keeps many decoy
    compatible triples without allowing collisions among the 3n inputs.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    band = params.pop("band", 2)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(band, bool) or not isinstance(band, int) or band < 2:
        raise ValueError("band must be an integer at least 2")

    rng = random.Random(seed)
    pi = list(range(n))
    sigma = list(range(n))
    rng.shuffle(pi)
    rng.shuffle(sigma)
    # The answer exists before the numerical instance does.
    answer = [[pi[i], sigma[i]] for i in range(n)]
    u, v, w, q = _sample_values(n, band, pi, sigma, rng)
    deadline, robots = _geometry(u, v, w, q)
    rng.shuffle(robots)
    w_index = {value: k for k, value in enumerate(w)}
    # Publicly derivable from the coordinates, cached so G4 can draw 200k
    # structure-aware candidates without repeating cubic geometry work.
    compatible = [
        [(j, w_index[q - u[i] - v[j]]) for j in range(n)
         if q - u[i] - v[j] in w_index]
        for i in range(n)
    ]
    return {
        "family": "planar L1 Freeze-Tag normal-form schedule",
        "metric": "L1",
        "n": n,
        "band": band,
        "deadline": deadline,
        "robots": robots,
        "_compatible": compatible,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete, self-contained solver-facing problem."""
    n = inst["n"]
    lines = "\n".join(
        f'{r["id"]} {r["x"]} {r["y"]}' for r in inst["robots"]
    )
    return f"""Planar L1 Freeze-Tag: find a deadline-feasible normal-form schedule

There are {4 * n + 2} labeled robots at integer points in the plane.  Distance
between (x1,y1) and (x2,y2) is the Manhattan distance
|x1-x2|+|y1-y2|.  Robot O is active at time 0; every other robot is frozen.
An active robot moves at speed at most 1.  When it reaches a frozen robot, that
robot activates immediately, and the arriving robot and the newly active robot
may move independently.  Waiting is allowed.  All robots must be active by the
inclusive deadline L={inst["deadline"]}.

For this instance, construct the following normal-form schedule.  Robot O moves
along the straight segment from O to Z, activating every A robot on that segment
in increasing distance from O.  On reaching A_i, one available robot goes by a shortest
L1 path directly to one B_j.  The two robots then available at B_j go by shortest
L1 paths, one directly to C_k.1 and one directly to C_k.2.  Choose exactly one
B_j and one paired C_k for each A_i, using every B index j=0,...,{n - 1} exactly
once and every C-pair index k=0,...,{n - 1} exactly once.  Routes may cross and
robots may wait; there are no collision, congestion, or capacity constraints.

Robot data are shuffled.  Each line is: label x y.  Labels and indices are
literal and 0-based; C_k.1 and C_k.2 are two distinct robots in pair k.
{lines}

Output a JSON array of exactly {n} two-integer rows.  Row i (rows are ordered
i=0,...,{n - 1}) must be [j,k], meaning A_i activates B_j and B_j activates both
C_k.1 and C_k.2.  Both columns must be permutations of 0,...,{n - 1}; order
inside [j,k] matters, and repeats are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example: <answer>[[2,0],[0,1],[1,2]]</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON value; return None on every malformed form."""
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
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _robot_positions(inst: dict) -> dict[str, tuple[int, int]]:
    return {r["id"]: (r["x"], r["y"]) for r in inst["robots"]}


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay any submitted normal-form schedule, never consulting the plant."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong row count: expected {n}, got {len(answer)}"

    bs: list[int] = []
    cs: list[int] = []
    for i, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 2:
            return False, f"row {i} must be a two-item [B,C] array"
        j, k = row
        if (isinstance(j, bool) or not isinstance(j, int) or
                isinstance(k, bool) or not isinstance(k, int)):
            return False, f"row {i} contains a non-integer index"
        if not 0 <= j < n:
            return False, f"B index {j} in row {i} is out of range 0..{n - 1}"
        if not 0 <= k < n:
            return False, f"C index {k} in row {i} is out of range 0..{n - 1}"
        bs.append(j)
        cs.append(k)
    if len(set(bs)) != n:
        return False, "a B index is repeated"
    if len(set(cs)) != n:
        return False, "a C-pair index is repeated"

    pos = _robot_positions(inst)
    expected = {"O", "Z"}
    expected.update(f"A{i}" for i in range(n))
    expected.update(f"B{i}" for i in range(n))
    expected.update(f"C{i}.{copy}" for i in range(n) for copy in (1, 2))
    if set(pos) != expected:
        return False, "instance robot labels are inconsistent"
    deadline = inst["deadline"]
    if _l1(pos["O"], pos["Z"]) > deadline:
        return False, "backbone terminal Z misses the deadline"

    for i, (j, k) in enumerate(zip(bs, cs)):
        start = _l1(pos["O"], pos[f"A{i}"])
        at_b = start + _l1(pos[f"A{i}"], pos[f"B{j}"])
        for copy in (1, 2):
            arrival = at_b + _l1(pos[f"B{j}"], pos[f"C{k}.{copy}"])
            if arrival > deadline:
                return False, (
                    f"route A{i}->B{j}->C{k}.{copy} arrives at {arrival}, "
                    f"after deadline {deadline}"
                )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Make a structure-aware guess using public local compatibility.

    Rows are visited in random order and choose a random deadline-compatible B
    not already used.  Any dead-end B slots are repaired to a B permutation.
    The locally implied C indices are retained once each, then duplicate or
    absent C indices are repaired to a C permutation.  Thus the answer always
    has the stated shape and both all-different constraints, while exploiting
    every local route constraint that survives the unresolved global collision.
    """
    n = inst["n"]
    choices = _compatible(inst)
    order = list(range(n))
    rng.shuffle(order)
    used_b: set[int] = set()
    bs: list[int | None] = [None] * n
    cs: list[int | None] = [None] * n
    bad_rows = []
    for i in order:
        options = [pair for pair in choices[i] if pair[0] not in used_b]
        if not options:
            bad_rows.append(i)
            continue
        j, k = rng.choice(options)
        bs[i] = j
        cs[i] = k
        used_b.add(j)

    missing_b = [j for j in range(n) if j not in used_b]
    rng.shuffle(missing_b)
    for i, j in zip(bad_rows, missing_b):
        bs[i] = j
        cs[i] = next((k for jj, k in choices[i] if jj == j), None)

    c_order = list(range(n))
    rng.shuffle(c_order)
    used_c: set[int] = set()
    bad_rows = []
    for i in c_order:
        k = cs[i]
        if k is None or k in used_c:
            bad_rows.append(i)
        else:
            used_c.add(k)
    missing_c = [k for k in range(n) if k not in used_c]
    rng.shuffle(missing_c)
    for i, k in zip(bad_rows, missing_c):
        cs[i] = k
    return [[int(bs[i]), int(cs[i])] for i in range(n)]


def search_space(inst: dict) -> int | None:
    """Count shape-valid answers: two independently chosen permutations."""
    return math.factorial(inst["n"]) ** 2


def _compatible(inst: dict) -> list[list[tuple[int, int]]]:
    """List public (B,C-pair) choices whose two routes meet the deadline."""
    if "_compatible" in inst:
        return inst["_compatible"]
    n = inst["n"]
    pos = _robot_positions(inst)
    deadline = inst["deadline"]
    rows: list[list[tuple[int, int]]] = []
    for i in range(n):
        start = _l1(pos["O"], pos[f"A{i}"])
        choices = []
        for j in range(n):
            at_b = start + _l1(pos[f"A{i}"], pos[f"B{j}"])
            for k in range(n):
                if all(
                    at_b + _l1(pos[f"B{j}"], pos[f"C{k}.{copy}"]) <= deadline
                    for copy in (1, 2)
                ):
                    choices.append((j, k))
        rows.append(choices)
    return rows


def enumerate_all(inst: dict) -> int | None:
    """Exactly count witnesses for n<=9; refuse larger exponential work."""
    n = inst["n"]
    if n > 9:
        return None
    choices = _compatible(inst)
    order = sorted(range(n), key=lambda i: len(choices[i]))
    memo: dict[tuple[int, int, int], int] = {}

    def count(depth: int, used_b: int, used_c: int) -> int:
        key = (depth, used_b, used_c)
        if key in memo:
            return memo[key]
        if depth == n:
            return 1
        i = order[depth]
        total = 0
        for j, k in choices[i]:
            bj = 1 << j
            ck = 1 << k
            if not used_b & bj and not used_c & ck:
                total += count(depth + 1, used_b | bj, used_c | ck)
        memo[key] = total
        return total

    return count(0, 0, 0)


def _symmetries(x: int, y: int) -> tuple[tuple[int, int], ...]:
    return (
        (x, y), (x, -y), (-x, y), (-x, -y),
        (y, x), (y, -x), (-y, x), (-y, -x),
    )


def canonical_key(inst: dict) -> str:
    """Canonicalize labels/order, translation, and all planar L1 axis symmetries."""
    source = next(r for r in inst["robots"] if r["role"] == "source")
    variants: list[str] = []
    for s in range(8):
        records = []
        for robot in inst["robots"]:
            dx = robot["x"] - source["x"]
            dy = robot["y"] - source["y"]
            tx, ty = _symmetries(dx, dy)[s]
            records.append((robot["role"], tx, ty))
        records.sort()
        variants.append(json.dumps([inst["deadline"], records], separators=(",", ":")))
    normal = min(variants)
    return hashlib.sha256(normal.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase matching dimension while retaining the safe crowded regime."""
    if "n" not in params:
        return None
    out = dict(params)
    out["n"] = int(params["n"] * 4 / 3) + 1
    return out


def _candidate_from_choices(
    n: int, selected: dict[int, tuple[int, int]]
) -> list[list[int]] | None:
    if len(selected) != n:
        return None
    return [[selected[i][0], selected[i][1]] for i in range(n)]


def _attack_index_alignment(inst: dict) -> object:
    n = inst["n"]
    return [[i, i] for i in range(n)]


def _attack_left_to_right(inst: dict) -> object | None:
    n = inst["n"]
    pos = _robot_positions(inst)
    choices = _compatible(inst)
    used_b: set[int] = set()
    used_c: set[int] = set()
    selected: dict[int, tuple[int, int]] = {}
    for i in sorted(range(n), key=lambda z: pos[f"A{z}"][0]):
        available = [x for x in choices[i] if x[0] not in used_b and x[1] not in used_c]
        if not available:
            return None
        j, k = min(
            available,
            key=lambda x: (_l1(pos[f"A{i}"], pos[f"B{x[0]}"]),
                           pos[f"B{x[0]}"][0], pos[f"C{x[1]}.1"][0]),
        )
        selected[i] = (j, k)
        used_b.add(j)
        used_c.add(k)
    return _candidate_from_choices(n, selected)


def _attack_degree_outlier(inst: dict) -> object | None:
    n = inst["n"]
    choices = _compatible(inst)
    degree_b = [0] * n
    degree_c = [0] * n
    for row in choices:
        for j, k in row:
            degree_b[j] += 1
            degree_c[k] += 1
    used_b: set[int] = set()
    used_c: set[int] = set()
    selected: dict[int, tuple[int, int]] = {}
    for i in sorted(range(n), key=lambda z: (len(choices[z]), z)):
        available = [x for x in choices[i] if x[0] not in used_b and x[1] not in used_c]
        if not available:
            return None
        j, k = min(
            available,
            key=lambda x: (degree_b[x[0]] + degree_c[x[1]],
                           degree_b[x[0]], degree_c[x[1]], x),
        )
        selected[i] = (j, k)
        used_b.add(j)
        used_c.add(k)
    return _candidate_from_choices(n, selected)


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 64
) -> object | None:
    n = inst["n"]
    choices = _compatible(inst)
    for _ in range(restarts):
        remaining = set(range(n))
        used_b: set[int] = set()
        used_c: set[int] = set()
        selected: dict[int, tuple[int, int]] = {}
        while remaining:
            feasible = {
                i: [x for x in choices[i]
                    if x[0] not in used_b and x[1] not in used_c]
                for i in remaining
            }
            minimum = min(len(row) for row in feasible.values())
            if minimum == 0:
                break
            tight = [i for i, row in feasible.items() if len(row) == minimum]
            i = rng.choice(tight)
            j, k = rng.choice(feasible[i])
            selected[i] = (j, k)
            remaining.remove(i)
            used_b.add(j)
            used_c.add(k)
        candidate = _candidate_from_choices(n, selected)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_exact_mrv(
    inst: dict, node_limit: int = 100_000
) -> tuple[object | None, int]:
    """Capped exact search, included because it broke the former n=40 preset."""
    n = inst["n"]
    choices = _compatible(inst)
    selected: dict[int, tuple[int, int]] = {}
    nodes = 0

    def search(remaining: set[int], used_b: int, used_c: int) -> bool:
        nonlocal nodes
        if nodes >= node_limit:
            return False
        nodes += 1
        if not remaining:
            return True
        best_i = -1
        best_options: list[tuple[int, int]] | None = None
        for i in remaining:
            options = [
                (j, k) for j, k in choices[i]
                if not (used_b >> j) & 1 and not (used_c >> k) & 1
            ]
            if not options:
                return False
            if best_options is None or len(options) < len(best_options):
                best_i = i
                best_options = options
        assert best_options is not None
        for j, k in best_options:
            selected[best_i] = (j, k)
            if search(remaining - {best_i}, used_b | (1 << j), used_c | (1 << k)):
                return True
            selected.pop(best_i, None)
            if nodes >= node_limit:
                break
        return False

    solved = search(set(range(n)), 0, 0)
    return (_candidate_from_choices(n, selected) if solved else None), nodes


def _copy_instance(inst: dict) -> dict:
    out = {
        **inst,
        "robots": [dict(r) for r in inst["robots"]],
        "answer": [list(row) for row in inst["answer"]],
    }
    # This cache uses the current role labels; a relabelling must recompute it.
    out.pop("_compatible", None)
    return out


def _transform_instance(inst: dict, rng: random.Random, sym: int) -> dict:
    """Compose role relabelling, C-copy swaps, input reorder, D4, translation."""
    out = _copy_instance(inst)
    n = inst["n"]
    pa = list(range(n))
    pb = list(range(n))
    pc = list(range(n))
    rng.shuffle(pa)
    rng.shuffle(pb)
    rng.shuffle(pc)
    swap_copy = [rng.randrange(2) for _ in range(n)]
    tx = rng.randint(-10_000, 10_000)
    ty = rng.randint(-10_000, 10_000)

    for robot in out["robots"]:
        name = robot["id"]
        if name.startswith("A"):
            robot["id"] = f"A{pa[int(name[1:])]}"
        elif name.startswith("B"):
            robot["id"] = f"B{pb[int(name[1:])]}"
        elif name.startswith("C"):
            head, copy_text = name[1:].split(".")
            old_k = int(head)
            copy = int(copy_text)
            if swap_copy[old_k]:
                copy = 3 - copy
            robot["id"] = f"C{pc[old_k]}.{copy}"
        x, y = _symmetries(robot["x"], robot["y"])[sym]
        robot["x"] = x + tx
        robot["y"] = y + ty

    carried = [[0, 0] for _ in range(n)]
    for old_i, (old_j, old_k) in enumerate(inst["answer"]):
        carried[pa[old_i]] = [pb[old_j], pc[old_k]]
    out["answer"] = carried
    rng.shuffle(out["robots"])
    return out


def _find_bad_swap(inst: dict) -> list[list[int]]:
    answer = [list(row) for row in inst["answer"]]
    for column in (0, 1):
        for a, b in itertools.combinations(range(inst["n"]), 2):
            trial = [list(row) for row in answer]
            trial[a][column], trial[b][column] = trial[b][column], trial[a][column]
            if not verify(inst, trial)[0]:
                return trial
    raise AssertionError("every transposition unexpectedly remains feasible")


def selftest() -> dict:
    """Run mandatory G1--G8 gates and return JSON-serializable measurements."""
    report: dict[str, object] = {
        "paper": "2509.14357",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    planted_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {reason}")
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": True, "verified": planted_total, "attempted": planted_total
    }

    base = make_instance(seed=19, **DIFFICULTY[SHIPPING_DIFFICULTY])
    corruptions: dict[str, object] = {}
    dropped = [list(row) for row in base["answer"][:-1]]
    swapped = _find_bad_swap(base)
    duplicated = [list(row) for row in base["answer"]]
    duplicated[0][0] = duplicated[1][0]
    empty: list = []
    out_of_range = [list(row) for row in base["answer"]]
    out_of_range[0][0] = base["n"]
    for name, candidate in (
        ("drop_one", dropped), ("swap_two_assignments", swapped),
        ("duplicate", duplicated), ("empty", empty),
        ("out_of_range", out_of_range),
    ):
        ok, reason = verify(base, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        corruptions[name] = reason
    reasons = list(corruptions.values())
    if len(set(reasons)) != len(reasons):
        raise AssertionError("G2 corruption reasons are not distinct")
    report["G2_rejects_corruption"] = {
        "pass": True, "rejected": len(corruptions), "attempted": len(corruptions),
        "reasons": corruptions,
    }

    response = (
        "I found a feasible allocation.\n```json\n<answer>\n"
        + json.dumps(base["answer"])
        + "\n</answer>\n```\nThe routes meet the deadline."
    )
    parsed = parse_answer(response)
    if parsed != base["answer"]:
        raise AssertionError("G3 realistic response did not round-trip")
    report["G3_round_trip"] = {
        "pass": True, "rows_recovered": len(parsed),
        "prose": True, "markdown_fence": True,
    }

    guess_inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    guess_rng = random.Random(271828)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        hits += bool(verify(guess_inst, random_candidate(guess_inst, guess_rng))[0])
    probability = hits / samples
    if probability >= 1e-6:
        raise AssertionError(f"G4 guess rate {hits}/{samples} is too high")
    report["G4_guess_resistance"] = {
        "pass": True, "hits": hits, "samples": samples,
        "measured_probability": probability,
        "prior": ("random-order locally compatible A-B greedy assignment, "
                  "then B/C permutation repair"),
        "candidate_space": str(search_space(guess_inst)),
    }

    sparse_rows = []
    for seed in (5, 6, 7):
        small = make_instance(n=7, band=2, seed=seed)
        count = enumerate_all(small)
        space = search_space(small)
        if count is None:
            raise AssertionError("G5 unexpectedly declined n=7")
        fraction = count / space
        if fraction >= 1e-3:
            raise AssertionError(f"G5 solution fraction {fraction} is not tiny")
        sparse_rows.append({
            "seed": seed, "solutions": count, "space": space, "fraction": fraction
        })
    report["G5_sparse"] = {"pass": True, "instances": sparse_rows}

    attack_counts = {
        "index_alignment": 0,
        "degree_outlier": 0,
        "left_to_right_nearest": 0,
        "random_mrv_64_restarts": 0,
        "exact_mrv_100000_nodes": 0,
    }
    exact_nodes = []
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "index_alignment": _attack_index_alignment(inst),
            "degree_outlier": _attack_degree_outlier(inst),
            "left_to_right_nearest": _attack_left_to_right(inst),
            "random_mrv_64_restarts": _attack_random_restarts(
                inst, random.Random(90_000 + seed), 64
            ),
        }
        exact_candidate, nodes = _attack_exact_mrv(inst, 100_000)
        candidates["exact_mrv_100000_nodes"] = exact_candidate
        exact_nodes.append(nodes)
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_counts[name] += 1
    if any(attack_counts.values()):
        raise AssertionError(f"G6 attacks solved shipping instances: {attack_counts}")
    report["G6_adversary_panel"] = {
        "pass": True, "seeds": len(attack_seeds),
        "solved_by_attack": attack_counts,
        "exact_mrv_nodes_by_seed": exact_nodes,
    }

    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled = make_instance(n=2 * ship["n"], band=ship["band"], seed=4242)
    ok, reason = verify(doubled, doubled["answer"])
    if not ok:
        raise AssertionError(f"G7 doubled plant failed: {reason}")
    if search_space(doubled) <= search_space(base):
        raise AssertionError("G7 search space did not grow")
    report["G7_scales"] = {
        "pass": True, "base_n": ship["n"], "doubled_n": doubled["n"],
        "doubled_robots": len(doubled["robots"]), "doubled_planted_verifies": True,
    }

    invariance = 0
    carried = 0
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **ship)
        key = canonical_key(inst)
        for sym in range(8):
            transformed = _transform_instance(
                inst, random.Random(1_000_000 + seed * 8 + sym), sym
            )
            if canonical_key(transformed) != key:
                raise AssertionError(f"G8 key changed for seed {seed}, symmetry {sym}")
            invariance += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                raise AssertionError(f"G8 carried answer failed: {reason}")
            carried += 1
    unrelated = [
        canonical_key(make_instance(seed=20_000 + seed, **ship))
        for seed in range(20)
    ]
    distinct = len(set(unrelated))
    if distinct != len(unrelated):
        raise AssertionError("G8 unrelated instances collided")
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance,
        "carried_answer_checks": carried,
        "unrelated_distinct": distinct,
        "unrelated_attempted": len(unrelated),
        "symmetries_per_seed": 8,
        "composed": [
            "within-role relabelling", "C-copy swaps", "input reordering",
            "translation", "signed-axis permutation",
        ],
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
