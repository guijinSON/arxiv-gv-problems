"""Exact congruence witnesses for insertion-only unit-disk instances.

This module is grounded in the geometric independent-set definition in
Section 1 of arXiv:2308.00979 and in the static-to-dynamic insertion reduction
of Section 5.5 (Theorem 5).  It transforms odd square-lattice instances by
exact rational similarities and translations.  A checkerboard class is known
before the disks are emitted, and is carried as a compact affine congruence.

Generation is deterministic in ``(n, seed, params)``.  The module uses only
the Python standard library, performs no file I/O, and prints nothing on
import.
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
import time
from collections import Counter, deque
from typing import Any


TRACK = "B"

_REDUCTION_CITATION = (
    "Section 5.5, Theorem 5: a static unit-disk MIS instance is transformed "
    "to a dynamic instance by inserting its disks one by one"
)

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "closed unit disks with rational centers",
        "insertion-only dynamic sequence",
        "affine congruence selection rules",
    ],
    "verification_operations": [
        "integer modular evaluation",
        "exact rational squared-distance comparison",
        "integer cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION_CITATION,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recover the two-color parity invariant of each concealed affine "
        "lattice; without it, a solver must reconstruct disk intersections "
        "or search a vast bounded language of congruence rules."
    ),
    "hardness_basis": (
        "Track B: exact intersection reconstruction followed by true geometric "
        "lattice recovery and bipartite coloring costs O(P*n^4) pair tests; "
        "shipping uses eight 21x21 panels: the measured exact reference route "
        "performs 776,160 squared-distance tests plus 13,440 edge scans, while "
        "the compact route derives each rule from two lattice directions."
    ),
    "max_answer_tokens": 183,
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
    "hard": {"n": 21, "panels": 8, "coord_bits": 32},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Each panel's distinct centers carry the two-color invariant of a hidden "
    "rank-two lattice."
)
PLACEBO_HINT = (
    "Each panel's distinct entries reward careful attention to the exact "
    "integer conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with one affine congruence rule per panel; every rule "
        "has integers 2<=m<=H and 0<=a,b,c<m and selects exactly the sites "
        "where a*X+b*Y+c is 0 modulo m."
    ),
    "bounds": {
        "max_panels": 32,
        "max_rules": 32,
        "coefficient_rule": "2 <= m <= instance H; 0 <= a,b,c < m",
        "max_coord_bits": 80,
    },
}

NOTES = r"""
Step 0 and paper grounding.  Section 1 defines geometric MIS on a collection
of disks: the required object is a maximum-cardinality pairwise-disjoint
subcollection.  Section 3 treats unit disks and Lemma 4 proves that the largest
of four shifted-grid candidates is a 12-approximation.  Theorem 1 maintains
that approximation in O(log n) worst-case update time.  Section 5 treats
arbitrary radii with nonatrees, clearance, obstacle disks, and a dynamic
farthest-neighbor structure.  Section 5.5 (Theorem 5) explicitly converts a
static unit-disk instance into an insertion-only dynamic instance by inserting
the disks one by one.  That is the paper-licensed reduction used here; the
solver is still handed the paper's rational disk centers, not an adjacency
matrix.

What makes the source problem easy.  The introduction records a static PTAS
for unit disks, and Theorem 1 gives a dynamic 12-approximation.  Neither finds
the exact threshold used here.  More importantly, this generator's own
distribution has an efficient exact algorithm: reconstruct intersections,
recognize each odd square-lattice panel, two-color it, and express the larger
color class as an affine congruence.  Consequently this is Track B, never a
Track A average-case claim.  The reference implementation is quadratic in the
number of distinct centers per panel and its measured cost is reported.

Certificate production.  Before emitting a panel, generation chooses an odd
n by n lattice.  Adjacent lattice sites are at distance at most 2 and every
nonadjacent pair is at distance greater than 2, so the even checkerboard class
is a set of (n^2+1)/2 pairwise-disjoint closed unit disks.  A rational rotation,
scale, and translation preserve all distances.  If e1,e2 are its two lattice
directions from an even corner, then

  (e2_y-e1_y)(X-X0) + (e1_x-e2_x)(Y-Y0)

is det(e1,e2) times the sum of the two lattice coordinates.  Vanishing modulo
2*abs(det(e1,e2)) therefore selects precisely the known checkerboard class.
The rule is normalized and carried through the transformation.  Generation
never solves the emitted instance.

Adversaries.  A common scalar of at least 4096 conceals parity from raw x, y,
and x+y residues.  The first several lexicographic centers are collinear, so a
first-three-points basis guess is singular.  Large coordinate spans foil an
axis/outlier rule, and random bounded congruences almost always select the
wrong cardinality.  The successful reference algorithm is reported separately
as Track B requires.

Canonicalization.  Disk IDs, insertion order, panel order, translations, and
all plane isometries are ignored.  Each panel is represented by the complete
multiset of exact rational squared distances between its centers, and panel
signatures are sorted.  This is complete for the generated square panels up to
their irrelevant placement, although it is not a general disk-configuration
isomorphism algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 300_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_SCALAR = 4096

# Filled from the three script-owned hardening runs after the family holds.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _int_param(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < low or value > high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _rule_from_basis(origin: tuple[int, int], e1: tuple[int, int],
                     e2: tuple[int, int], bound: int) -> dict[str, int]:
    """Return the normalized congruence for even e1/e2 coordinate sum."""
    a = e2[1] - e1[1]
    b = e1[0] - e2[0]
    det = e1[0] * e2[1] - e1[1] * e2[0]
    if det == 0:
        raise ValueError("basis vectors are collinear")
    c = -a * origin[0] - b * origin[1]
    m = 2 * abs(det)
    g = math.gcd(math.gcd(abs(a), abs(b)), math.gcd(abs(c), m))
    a //= g
    b //= g
    c //= g
    m //= g
    a %= m
    b %= m
    c %= m
    if not (2 <= m <= bound):
        raise ValueError("normalized rule exceeds certificate bound")
    return {"a": a, "b": b, "c": c, "m": m}


def _physical_disjoint(s1: dict, p1: dict, s2: dict, p2: dict) -> bool:
    """Exact test that two closed unit disks have disjoint point sets."""
    d1, d2 = p1["scale"], p2["scale"]
    dx = s1["X"] * d2 - s2["X"] * d1
    dy = s1["Y"] * d2 - s2["Y"] * d1
    den = d1 * d2
    return dx * dx + dy * dy > 4 * den * den


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Transform known checkerboards and carry their congruence certificates."""
    n = _int_param("n", n, 3, 63)
    if n % 2 == 0:
        raise ValueError("n must be odd")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    panel_count = _int_param("panels", params.pop("panels", 4), 1, 32)
    coord_bits = _int_param(
        "coord_bits", params.pop("coord_bits", 16), 4, 80
    )
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))

    rng = random.Random(seed)
    bound = 1 << (coord_bits + 28)
    target_per_panel = (n * n + 1) // 2
    total_sites = panel_count * n * n
    ids = list(range(total_sites))
    rng.shuffle(ids)
    next_id = 0
    records: list[tuple[dict, dict]] = []

    # (9,40,41) is a primitive Pythagorean triple.  Its large leg delays the
    # second lattice direction in lexicographic order, defeating a first-three
    # basis guess while keeping the compact derivation below 300 operations.
    # The demo instead uses the tiny (3,4,5) triangle so its arithmetic is
    # genuinely manageable on paper.
    if n == 3 and panel_count == 1 and coord_bits <= 5:
        leg_x, leg_y, hyp = 3, 4, 5
    else:
        leg_x, leg_y, hyp = 9, 40, 41
    spacing = 200 * n

    for panel_index in range(panel_count):
        odd = rng.randrange(1 << (coord_bits - 1), 1 << coord_bits) | 1
        scalar = odd if hyp == 5 else _SCALAR * odd
        # A tiny non-proportional offset prevents the displayed rational
        # coordinates from cancelling the large scalar.
        delta = 1 if hyp == 5 else 1 + 2 * rng.randrange(1, 16)
        scale = (3 * scalar * hyp) // 5 + delta
        step_sq = scalar * scalar * hyp * hyp
        if not (step_sq <= 4 * scale * scale < 2 * step_sq):
            raise AssertionError("lattice spacing is outside the disk window")

        px, py = scalar * leg_x, scalar * leg_y
        qx, qy = -scalar * leg_y, scalar * leg_x
        # Exact rational translation.  Panels are much farther apart than
        # their diameter, so no disks from different panels meet.
        if hyp == 5:
            x0 = rng.randrange(-20, 21)
            y0 = rng.randrange(-20, 21)
        else:
            x0 = panel_index * spacing * scale + rng.randrange(-scale // 4, scale // 4)
            y0 = ((panel_index * panel_index + 3) % 11) * spacing * scale
            y0 += rng.randrange(-scale // 4, scale // 4)

        sites = []
        for u in range(n):
            for v in range(n):
                sites.append({
                    "id": ids[next_id],
                    "X": x0 + u * px + v * qx,
                    "Y": y0 + u * py + v * qy,
                })
                next_id += 1
        sites.sort(key=lambda s: (s["X"], s["Y"], s["id"]))

        # The minimum-X corner is (u,v)=(0,n-1), whose checkerboard parity is
        # even because n is odd.  Its inward directions are p and -q.
        corner = (x0 + (n - 1) * qx, y0 + (n - 1) * qy)
        rule = _rule_from_basis(corner, (px, py), (-qx, -qy), bound)
        panel = {
            "scale": scale,
            "sites": sites,
            "target": target_per_panel,
        }
        records.append((panel, rule))

    rng.shuffle(records)
    inst = {
        "n": n,
        "panel_count": panel_count,
        "coord_bits": coord_bits,
        "radius": [1, 1],
        "certificate_bound": bound,
        "target_per_panel": target_per_panel,
        "target_total": panel_count * target_per_panel,
        "panels": [p for p, _ in records],
    }
    inst["answer"] = {"rules": [r for _, r in records]}
    return inst


def render(inst: dict) -> str:
    """Render the complete exact disk-selection problem."""
    lines = [
        "AFFINE-CONGRUENCE INDEPENDENT SET OF UNIT DISKS",
        "",
        "The final active objects are closed disks of radius 1 in the real",
        "plane. They arrived by insertion only, in the displayed panel and row",
        "order; no disk was deleted. A row `id X Y` denotes the disk whose",
        "center is the rational point (X/S,Y/S), where S is that panel's",
        "positive integer scale. Disk IDs and panel numbers are 0-indexed.",
        "Two closed unit disks are disjoint exactly when the squared distance",
        "between their centers is strictly greater than 4; tangency counts as",
        "intersection.",
        "",
        "Return one affine congruence rule for every panel, in displayed panel",
        "order. A rule is four integers a,b,c,m. It selects precisely those",
        "disks in its panel for which (a*X+b*Y+c) modulo m equals 0.",
        "The rule itself, not a list of disk IDs, is the witness.",
        "",
        f"Number of panels P = {inst['panel_count']}",
        f"Each panel has {inst['n']}*{inst['n']} = {inst['n'] ** 2} disks",
        f"Each rule must select exactly K = {inst['target_per_panel']} disks",
        f"The union must therefore contain {inst['target_total']} disks",
        f"Certificate bound H = {inst['certificate_bound']}",
        "For every rule require 2 <= m <= H and 0 <= a,b,c < m.",
        "All selected disks, within and across panels, must be pairwise disjoint.",
        "",
        "Rows inside each panel are lexicographically sorted by (X,Y); this is",
        "only a presentation convention and does not change the disk collection.",
        "No fact about unlisted coordinates may be assumed.",
        "",
        "DISK_DATA_BEGIN",
    ]
    for j, panel in enumerate(inst["panels"]):
        lines.append(
            f"PANEL {j} SCALE {panel['scale']} TARGET {panel['target']}"
        )
        for site in panel["sites"]:
            lines.append(f"{site['id']} {site['X']} {site['Y']}")
        lines.append(f"END_PANEL {j}")
    lines.extend([
        "DISK_DATA_END",
        "",
        "Output a JSON object with exactly one key `rules`. Its value is an",
        "array of P objects in panel order, each with integer keys a,b,c,m.",
        "Order of keys inside a rule object is irrelevant; rules may differ",
        "from the construction's rules if they satisfy all stated conditions.",
        "",
        "Give your final answer inside <answer></answer> tags.",
        "Example syntax (not a solution):",
        '<answer>{"rules":[{"a":1,"b":2,"c":3,"m":5}]}</answer>',
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Extract the tagged JSON object; malformed output returns None."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _validate_rule_shape(rule: object, index: int, bound: int) -> tuple[bool, str]:
    if not isinstance(rule, dict):
        return False, f"panel {index}: rule must be a JSON object"
    if set(rule) != {"a", "b", "c", "m"}:
        return False, f"panel {index}: rule keys must be exactly a,b,c,m"
    for name in ("a", "b", "c", "m"):
        value = rule[name]
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"panel {index}: {name} must be an integer"
    m = rule["m"]
    if not 2 <= m <= bound:
        return False, f"panel {index}: modulus m is outside 2..H"
    for name in ("a", "b", "c"):
        if not 0 <= rule[name] < m:
            return False, f"panel {index}: coefficient {name} is outside 0..m-1"
    return True, "ok"


def _selected(panel: dict, rule: dict) -> list[dict]:
    a, b, c, m = rule["a"], rule["b"], rule["c"], rule["m"]
    return [
        site for site in panel["sites"]
        if (a * site["X"] + b * site["Y"] + c) % m == 0
    ]


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any bounded congruence witness without consulting inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object is empty"
    if set(answer) != {"rules"}:
        return False, "answer must contain exactly the key rules"
    rules = answer["rules"]
    if not isinstance(rules, list):
        return False, "rules must be a JSON array"
    if len(rules) != inst["panel_count"]:
        return False, (
            f"wrong rule count: expected {inst['panel_count']}, got {len(rules)}"
        )

    chosen_by_panel = []
    bound = inst["certificate_bound"]
    for j, (panel, rule) in enumerate(zip(inst["panels"], rules)):
        ok, reason = _validate_rule_shape(rule, j, bound)
        if not ok:
            return False, reason
        chosen = _selected(panel, rule)
        if len(chosen) != panel["target"]:
            return False, (
                f"panel {j}: rule selects {len(chosen)} disks, "
                f"expected {panel['target']}"
            )
        for left in range(len(chosen)):
            for right in range(left + 1, len(chosen)):
                if not _physical_disjoint(
                    chosen[left], panel, chosen[right], panel
                ):
                    return False, (
                        f"panel {j}: selected disks {chosen[left]['id']} and "
                        f"{chosen[right]['id']} intersect"
                    )
        chosen_by_panel.append(chosen)

    # Check separation across panels exactly too; no unexecuted promise is used.
    for i in range(len(chosen_by_panel)):
        for j in range(i + 1, len(chosen_by_panel)):
            pi, pj = inst["panels"][i], inst["panels"][j]
            for si in chosen_by_panel[i]:
                for sj in chosen_by_panel[j]:
                    if not _physical_disjoint(si, pi, sj, pj):
                        return False, (
                            f"panels {i},{j}: selected disks {si['id']} and "
                            f"{sj['id']} intersect"
                        )
    return True, "ok"


def _cube_sum_from_two(h: int) -> int:
    """sum(m^3 for m in range(2,h+1)), exactly."""
    triangular = h * (h + 1) // 2
    return triangular * triangular - 1


def _sample_weighted_modulus(bound: int, rng: random.Random) -> int:
    """Sample m with probability m^3/sum_{j=2}^H j^3 in O(1) big-int ops."""
    rank = rng.randrange(_cube_sum_from_two(bound))
    # Find the least m with T(m)^2-1 > rank.
    need_triangular = math.isqrt(rank + 1) + 1
    m = (math.isqrt(1 + 8 * need_triangular) - 1) // 2
    if m < 2:
        m = 2
    while m * (m + 1) // 2 < need_triangular:
        m += 1
    while m > 2 and (m - 1) * m // 2 >= need_triangular:
        m -= 1
    return m


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated bounded rule language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    bound = inst["certificate_bound"]
    rules = []
    for _ in range(inst["panel_count"]):
        m = _sample_weighted_modulus(bound, rng)
        rules.append({
            "a": rng.randrange(m),
            "b": rng.randrange(m),
            "c": rng.randrange(m),
            "m": m,
        })
    return {"rules": rules}


def search_space(inst: dict) -> int | None:
    """Return the exact number of bounded rule tuples for all panels."""
    per_panel = _cube_sum_from_two(inst["certificate_bound"])
    return pow(per_panel, inst["panel_count"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact count only below a strict work cap."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    bound = inst["certificate_bound"]
    rule_values = (
        {"a": a, "b": b, "c": c, "m": m}
        for m in range(2, bound + 1)
        for a in range(m)
        for b in range(m)
        for c in range(m)
    )
    # The cap makes the materialization safe, and permits a Cartesian product.
    rules = list(rule_values)
    total = 0
    for product in itertools.product(rules, repeat=inst["panel_count"]):
        if verify(inst, {"rules": list(product)})[0]:
            total += 1
    return total


def _panel_distance_signature(panel: dict) -> tuple:
    """Complete pair-distance multiset, normalized as exact rationals."""
    sites = panel["sites"]
    den0 = panel["scale"] * panel["scale"]
    counts: Counter[tuple[int, int]] = Counter()
    for i in range(len(sites)):
        for j in range(i + 1, len(sites)):
            dx = sites[i]["X"] - sites[j]["X"]
            dy = sites[i]["Y"] - sites[j]["Y"]
            num = dx * dx + dy * dy
            g = math.gcd(num, den0)
            counts[(num // g, den0 // g)] += 1
    return tuple(sorted((num, den, count) for (num, den), count in counts.items()))


def canonical_key(inst: dict) -> str:
    """Key invariant under IDs, order, translations, and plane isometries."""
    signatures = sorted(_panel_distance_signature(p) for p in inst["panels"])
    payload = (
        "unit-disk-affine-lattice-v1",
        inst["n"],
        inst["target_per_panel"],
        tuple(signatures),
    )
    return hashlib.sha256(repr(payload).encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise coefficient entropy while keeping the symbolic answer shape fixed."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    bits = int(out.get("coord_bits", 16))
    if bits < 72:
        out["coord_bits"] = min(72, bits + 8)
        return out
    # At this point more coefficient bits push the serialized symbolic answer
    # toward the 2,000-character cap; the mathematical family can keep growing.
    return "cap_bound"


def _intersection_data(panel: dict) -> tuple[list[list[int]], int]:
    sites = panel["sites"]
    scale = panel["scale"]
    threshold = 4 * scale * scale
    adjacency = [[] for _ in sites]
    tests = 0
    for i in range(len(sites)):
        for j in range(i + 1, len(sites)):
            tests += 1
            dx = sites[i]["X"] - sites[j]["X"]
            dy = sites[i]["Y"] - sites[j]["Y"]
            if dx * dx + dy * dy <= threshold:
                adjacency[i].append(j)
                adjacency[j].append(i)
    return adjacency, tests


def _reference_algorithm(inst: dict) -> tuple[object | None, dict[str, int]]:
    """Quadratic exact lattice recognition and two-coloring (Track B route)."""
    rules = []
    distance_tests = 0
    edge_scans = 0
    for panel in inst["panels"]:
        adjacency, tests = _intersection_data(panel)
        distance_tests += tests
        corners = [i for i, nbrs in enumerate(adjacency) if len(nbrs) == 2]
        if not corners:
            return None, {"distance_tests": distance_tests, "edge_scans": edge_scans}
        corner = min(
            corners,
            key=lambda i: (
                panel["sites"][i]["X"], panel["sites"][i]["Y"]
            ),
        )
        colors = [-1] * len(adjacency)
        colors[corner] = 0
        queue = deque([corner])
        bipartite = True
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                edge_scans += 1
                if colors[v] < 0:
                    colors[v] = 1 - colors[u]
                    queue.append(v)
                elif colors[v] == colors[u]:
                    bipartite = False
        if not bipartite or colors.count(0) != panel["target"]:
            return None, {"distance_tests": distance_tests, "edge_scans": edge_scans}
        neighbors = adjacency[corner]
        origin = (
            panel["sites"][corner]["X"], panel["sites"][corner]["Y"]
        )
        vectors = []
        for neighbor in neighbors:
            site = panel["sites"][neighbor]
            vectors.append((site["X"] - origin[0], site["Y"] - origin[1]))
        rules.append(_rule_from_basis(
            origin, vectors[0], vectors[1], inst["certificate_bound"]
        ))
    return {"rules": rules}, {
        "distance_tests": distance_tests,
        "edge_scans": edge_scans,
    }


def _fallback_rule() -> dict[str, int]:
    return {"a": 0, "b": 0, "c": 1, "m": 2}


def _outlier_axis_attack(inst: dict) -> object:
    rules = []
    for panel in inst["panels"]:
        xs = [s["X"] for s in panel["sites"]]
        span = max(xs) - min(xs)
        m = max(2, min(inst["certificate_bound"], span or 2))
        rules.append({"a": 1, "b": 0, "c": (-min(xs)) % m, "m": m})
    return {"rules": rules}


def _first_three_attack(inst: dict) -> object:
    rules = []
    for panel in inst["panels"]:
        sites = panel["sites"]
        origin = (sites[0]["X"], sites[0]["Y"])
        e1 = (sites[1]["X"] - origin[0], sites[1]["Y"] - origin[1])
        e2 = (sites[2]["X"] - origin[0], sites[2]["Y"] - origin[1])
        try:
            rule = _rule_from_basis(
                origin, e1, e2, inst["certificate_bound"]
            )
        except ValueError:
            rule = _fallback_rule()
        rules.append(rule)
    return {"rules": rules}


def _small_modulus_attack(inst: dict) -> object:
    rules = []
    forms = ((1, 0), (0, 1), (1, 1), (1, -1))
    moduli = (2, 4, 8, 16, 32, 64, 128, 256)
    for panel in inst["panels"]:
        best = None
        best_error = 10 ** 9
        first = panel["sites"][0]
        for m in moduli:
            for a, b in forms:
                aa, bb = a % m, b % m
                c = (-aa * first["X"] - bb * first["Y"]) % m
                rule = {"a": aa, "b": bb, "c": c, "m": m}
                error = abs(len(_selected(panel, rule)) - panel["target"])
                if error < best_error:
                    best, best_error = rule, error
        rules.append(best if best is not None else _fallback_rule())
    return {"rules": rules}


def _random_restart_attack(inst: dict, seed: int, restarts: int = 256) -> object:
    rng = random.Random(seed)
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last if last is not None else {"rules": []}


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _compact_route_operations(inst: dict) -> int:
    """Count the advertised lexicographic lattice-recovery arithmetic."""
    operations = 0
    for panel in inst["panels"]:
        sites = panel["sites"]
        x0, y0 = sites[0]["X"], sites[0]["Y"]
        d1 = (sites[1]["X"] - x0, sites[1]["Y"] - y0)
        operations += 2
        found = False
        for site in sites[2:]:
            d2 = (site["X"] - x0, site["Y"] - y0)
            operations += 5  # two differences, two products, one subtraction
            if d1[0] * d2[1] - d1[1] * d2[0]:
                found = True
                break
        if not found:
            return 10 ** 9
        # a,b,det,c,m and normalization: a conservative fixed allowance.
        operations += 12
    return operations


def _transform_for_g8(inst: dict, answer: dict, seed: int) -> tuple[dict, dict]:
    """Compose ID relabeling, reordering, rotation, translation, panel shuffle."""
    out = copy.deepcopy(inst)
    carried = copy.deepcopy(answer)
    rng = random.Random(seed)

    # Rotate 90 degrees, translate by an integer vector, and carry every rule.
    tx, ty = rng.randrange(-50, 51), rng.randrange(-50, 51)
    for panel, rule in zip(out["panels"], carried["rules"]):
        scale = panel["scale"]
        old_a, old_b, old_c, m = rule["a"], rule["b"], rule["c"], rule["m"]
        for site in panel["sites"]:
            old_x, old_y = site["X"], site["Y"]
            site["X"] = -old_y + tx * scale
            site["Y"] = old_x + ty * scale
            site["id"] = (site["id"] * 104729 + 17) % 1_000_000_007
        rng.shuffle(panel["sites"])
        rule["a"] = (-old_b) % m
        rule["b"] = old_a % m
        rule["c"] = (old_c - old_a * ty * scale + old_b * tx * scale) % m

    order = list(range(out["panel_count"]))
    rng.shuffle(order)
    out["panels"] = [out["panels"][i] for i in order]
    carried["rules"] = [carried["rules"][i] for i in order]
    return out, carried


def selftest() -> dict:
    """Run gates G1--G9 and return their measured, JSON-native report."""
    report: dict[str, Any] = {
        "paper": "2308.00979",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: all presets, several seeds, plus JSON-native answers.
    g1_ok = 0
    g1_total = 0
    json_ok = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            g1_total += 1
            if verify(inst, inst["answer"])[0]:
                g1_ok += 1
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_ok += 1
    report["G1_planted_verifies"] = {
        "pass": g1_ok == g1_total and json_ok == g1_total,
        "verified": g1_ok,
        "attempts": g1_total,
        "json_roundtrips": json_ok,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=20260905, **shipping_params)

    # G2: five corruption modes with distinct executable reasons.
    corruptions = []
    corruptions.append(("empty", {}))
    dropped = copy.deepcopy(ship["answer"])
    dropped["rules"].pop()
    corruptions.append(("drop", dropped))
    swapped = copy.deepcopy(ship["answer"])
    if len(swapped["rules"]) >= 2:
        swapped["rules"][0], swapped["rules"][1] = (
            swapped["rules"][1], swapped["rules"][0]
        )
    else:
        swapped["rules"][0]["a"], swapped["rules"][0]["b"] = (
            swapped["rules"][0]["b"], swapped["rules"][0]["a"]
        )
    corruptions.append(("swap", swapped))
    duplicated = copy.deepcopy(ship["answer"])
    if len(duplicated["rules"]) >= 2:
        duplicated["rules"][-1] = copy.deepcopy(duplicated["rules"][0])
    else:
        duplicated["rules"].append(copy.deepcopy(duplicated["rules"][0]))
    corruptions.append(("duplicate", duplicated))
    out_of_range = copy.deepcopy(ship["answer"])
    out_of_range["rules"][0]["a"] = out_of_range["rules"][0]["m"]
    corruptions.append(("out_of_range", out_of_range))
    reasons = {}
    for name, candidate in corruptions:
        ok, reason = verify(ship, candidate)
        reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({v["reason"] for v in reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in reasons.values())
        and distinct_reasons == len(reasons),
        "rejected": sum(v["rejected"] for v in reasons.values()),
        "attempts": len(reasons),
        "distinct_reasons": distinct_reasons,
        "cases": reasons,
    }

    # G3: prose, fenced JSON, whitespace, and garbage.
    body = json.dumps(ship["answer"], separators=(",", ":"))
    replies = [
        f"I used exact congruences.\n<answer>{body}</answer>\nDone.",
        f"Result:\n<answer>```json\n{body}\n```</answer>",
        f"before <answer>  {body}  </answer> after",
    ]
    parsed = sum(parse_answer(reply) == ship["answer"] for reply in replies)
    garbage_none = parse_answer("no tagged result here") is None
    report["G3_round_trip"] = {
        "pass": parsed == len(replies) and garbage_none,
        "parsed": parsed,
        "attempts": len(replies),
        "garbage_rejected": garbage_none,
    }

    # G4 and shipping density for G5 share the required 200k uniform samples.
    guess_rng = random.Random(0x230800979)
    hits = 0
    start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(ship, guess_rng)
        if verify(ship, candidate)[0]:
            hits += 1
    guess_seconds = time.perf_counter() - start
    guess_probability = hits / _G4_SAMPLES
    space = search_space(ship)
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_probability,
        "search_space": space,
        "sampling_seconds": round(guess_seconds, 6),
        "prior": "uniform over the exact bounded per-panel rule grammar",
    }

    # Reference cost: this succeeds by design and belongs outside Track-B attacks.
    start = time.perf_counter()
    reference_answer, reference_ops = _reference_algorithm(ship)
    reference_seconds = time.perf_counter() - start
    reference_ok = reference_answer is not None and verify(ship, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and _G4_SAMPLES >= 200_000,
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_density_estimate": guess_probability,
        "shipping_exact_count": enumerate_all(ship),
        "baseline_wall_seconds": round(reference_seconds, 6),
        "baseline_distance_tests": reference_ops["distance_tests"],
        "baseline_edge_scans": reference_ops["edge_scans"],
        "baseline_solved": reference_ok,
    }

    # G6: four failing no-tool/cheap probes, plus the successful reference route.
    attack_fns = {
        "outlier_axis_span": lambda i, s: _outlier_axis_attack(i),
        "greedy_first_three_basis": lambda i, s: _first_three_attack(i),
        "random_restart_256": lambda i, s: _random_restart_attack(i, s, 256),
        "small_modulus_parity_ansatz": lambda i, s: _small_modulus_attack(i),
    }
    attack_results = {
        name: {"successes": 0, "attempts": _ATTACK_SEEDS}
        for name in attack_fns
    }
    reference_successes = 0
    reference_total_tests = 0
    reference_total_scans = 0
    reference_total_seconds = 0.0
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=90_000 + seed, **shipping_params)
        for name, fn in attack_fns.items():
            candidate = fn(inst, 700_000 + seed)
            if verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        t0 = time.perf_counter()
        candidate, ops = _reference_algorithm(inst)
        reference_total_seconds += time.perf_counter() - t0
        reference_total_tests += ops["distance_tests"]
        reference_total_scans += ops["edge_scans"]
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1
    all_failed = all(v["successes"] == 0 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact disk intersections, corner recovery, and bipartite coloring",
            "complexity": "O(P*n^4) exact squared-distance tests",
            "wall_clock_sec": round(reference_total_seconds / _ATTACK_SEEDS, 6),
            "operations": reference_total_tests // _ATTACK_SEEDS
            + reference_total_scans // _ATTACK_SEEDS,
            "distance_tests": reference_total_tests // _ATTACK_SEEDS,
            "edge_scans": reference_total_scans // _ATTACK_SEEDS,
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    # G7: grow the geometric ground set while the symbolic answer has P rules.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"] + 1
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    escalated_params = escalate(shipping_params)
    escalated_ok = False
    if isinstance(escalated_params, dict):
        escalated_inst = make_instance(seed=271828, **escalated_params)
        escalated_ok = verify(escalated_inst, escalated_inst["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "shipping_disks": ship["panel_count"] * ship["n"] ** 2,
        "doubled_disks": doubled["panel_count"] * doubled["n"] ** 2,
        "doubled_n": doubled["n"],
        "doubled_verified": doubled_ok,
        "fixed_shape_escalation": escalated_params,
        "escalated_verified": escalated_ok,
    }

    # G8: all transformations are composed, and the witness is carried through.
    invariant = 0
    carried = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=400_000 + seed, **shipping_params)
        key = canonical_key(inst)
        transformed, transformed_answer = _transform_for_g8(
            inst, inst["answer"], 500_000 + seed
        )
        if canonical_key(transformed) == key:
            invariant += 1
        if verify(transformed, transformed_answer)[0]:
            carried += 1
        keys.append(key)
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and distinct == 20,
        "invariance_passed": invariant,
        "invariance_attempts": 20,
        "carried_witnesses_verified": carried,
        "carried_witness_attempts": 20,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "disk-ID relabeling",
            "site reordering",
            "panel permutation",
            "90-degree rotation",
            "global integer translation",
        ],
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(ship["answer"])
    intended_ops = _compact_route_operations(ship)
    arms = {name: dict(_ORACLE_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
        - arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    )
    hinted_hardened = _ORACLE_EVIDENCE["hinted_verdict"] == "hardened"
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
