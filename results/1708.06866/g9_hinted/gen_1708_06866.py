"""Verified Track-B problem generator for arXiv:1708.06866.

The paper's concrete static-graph kernels are triangle counting and k-truss,
not arbitrary pattern/host subgraph isomorphism.  This module uses the former.
It composes the paper's eight-neighbour image graphs, hides each one behind a
unimodular integer-coordinate change, and carries the triangle counts through
that relabelling.  No generated graph is searched to obtain its certificate.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family remains stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graph given by exact vertex and edge predicates",
        "unimodularly relabelled eight-neighbour image-graph components",
        "per-component triangle-count certificate",
    ],
    "verification_operations": [
        "exact integer determinant",
        "exact edge-step normalization",
        "integer multiplication and addition",
        "exact certificate-field comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The two linear forms on each component are hidden grid coordinates in "
        "which the four edge-step pairs become all eight king moves, collapsing "
        "triangle enumeration to counting unit cells."
    ),
    "hardness_basis": (
        "Track B: the paper's Section III-A Algorithms 1-3 give polynomial-time "
        "triangle counters; the shipping reference uses forward-neighbour "
        "enumeration in O(V*Delta^2); the shipping selftest records its measured "
        "operation count and wall-clock cost over eight instances, whereas the "
        "coordinate-change route uses at most 280 exact arithmetic operations "
        "and must be recognized without a graph tool."
    ),
    "max_answer_tokens": 25,
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
    "hard": {"n": 256, "components": 8, "jitter": 63, "shears": 4},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly `component_counts` and `total`.  There is one "
        "nonnegative integer count per displayed component, bounded by "
        "floor(28*w*h/3) for its w*h-vertex maximum-degree-8 graph; `total` is "
        "forced to be their sum."
    ),
    "bounds": {
        "shipping_component_count": 8,
        "component_count_lower": 0,
        "component_count_upper": "floor(28*w*h/3)",
        "total": "sum(component_counts)",
    },
}

STRUCTURAL_HINT = (
    "Each component's two displayed linear forms are coordinates in which its "
    "four signed step pairs are precisely the eight king moves."
)
PLACEBO_HINT = (
    "Careful attention to the component order and the final total helps avoid "
    "small transcription and bookkeeping errors."
)

# Filled after the three separately preserved harden.py runs.  These arms are
# diagnostic only; G9.pass is determined solely by the published size/effort caps.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}

NOTES = """\
Section III-A fixes the native object and witness: a triangle is a set of three
mutually adjacent vertices, and correctness is an exact triangle count (Section
IV-A).  Algorithms 1-3 in Section III-A are the decisive easy-case result: they
compute the certificate by matrix products, so this cannot honestly be Track A.
Section IV-C's synthetic-data subsection supplies the construction used here:
an M by M image graph connects
each pixel to its eight neighbours.  The module composes disjoint copies and
carries their counts through integer unimodular coordinate relabellings.

The paper's Table II lists 8(M-1)^2 triangles, but its set definition and its
Algorithm 2 division by six give the ordinary undirected count 4(M-1)^2: every
unit cell induces K4 and contributes its four 3-subsets exactly once.  This
module follows that definition, not the inconsistent table.

The largest-component outlier attack ignores all other components; edge/3 and
the degree-bound midpoint lose the cell structure; the one-triangle-per-cell
ansatz misses three of K4's four triangles; copying Table II double-counts; and
uniform restarts sample the statement-aware degree-bounded certificate language.
All are checked across eight shipping seeds.  The successful standard forward
triangle algorithm is disclosed separately, as Track B requires.
"""


def _unimodular_matrix(rng: random.Random, shears: int) -> list[int]:
    """Generate [a,b,c,d] with determinant one, without search."""
    a, b, c, d = 1, 0, 0, 1
    for _ in range(shears):
        k = rng.choice((-4, -3, -2, -1, 1, 2, 3, 4))
        if rng.randrange(2):
            a, b = a + k * c, b + k * d
        else:
            c, d = c + k * a, d + k * b
    if rng.randrange(2):
        # Left multiplication by [[0,1],[-1,0]] preserves determinant one.
        a, b, c, d = c, d, -a, -b
    if rng.randrange(2):
        a, b, c, d = -a, -b, -c, -d
    assert a * d - b * c == 1
    return [a, b, c, d]


def _raw_steps(matrix: list[int]) -> list[tuple[int, int]]:
    """Images under A^-1 of (1,0),(0,1),(1,1),(1,-1)."""
    a, b, c, d = matrix
    return [(d, -c), (-b, a), (d - b, a - c), (d + b, -c - a)]


def _canonical_undirected_step(v: tuple[int, int]) -> tuple[int, int]:
    x, y = v
    return (-x, -y) if (x < 0 or (x == 0 and y < 0)) else (x, y)


def _display_steps(matrix: list[int], rng: random.Random) -> list[list[int]]:
    steps = list(_raw_steps(matrix))
    rng.shuffle(steps)
    out = []
    for x, y in steps:
        if rng.randrange(2):
            x, y = -x, -y
        out.append([x, y])
    return out


def _shape(comp) -> tuple[int, int]:
    lo1, hi1, lo2, hi2 = comp["bounds"]
    return hi1 - lo1, hi2 - lo2


def _component_count(comp) -> int:
    width, height = _shape(comp)
    # Each unit cell induces K4.  Every triangle has a unique
    # 1-by-1 bounding cell and is one of that K4's four 3-subsets.
    return 4 * (width - 1) * (height - 1)


def _component_bound(comp) -> int:
    # Delta <= 8, so at most C(8,2) incident triangle pairs per vertex; every
    # triangle is incident with three vertices.
    width, height = _shape(comp)
    return (28 * width * height) // 3


def make_instance(n, seed=0, **params) -> dict:
    """Build certified image-graph components by composition and relabelling."""
    n = int(n)
    number = int(params.get("components", 40))
    jitter = int(params.get("jitter", max(1, n // 3)))
    shears = int(params.get("shears", 4))
    if n < 3:
        raise ValueError("n must be at least 3")
    if number < 1 or number > 200:
        raise ValueError("components must be in 1..200")
    if jitter < 0:
        raise ValueError("jitter must be nonnegative")
    if shears < 0 or shears > 8:
        raise ValueError("shears must be in 0..8")

    rng = random.Random(seed)
    tags = rng.sample(range(100_000, 999_999_999), number)
    components = []
    for tag in tags:
        m = n + rng.randrange(jitter + 1)
        matrix = _unimodular_matrix(rng, shears)
        offset = [rng.randrange(-9999, 10000), rng.randrange(-9999, 10000)]
        lo1 = rng.randrange(-5000, 5001)
        lo2 = rng.randrange(-5000, 5001)
        components.append({
            "tag": tag,
            "matrix": matrix,
            "offset": offset,
            "bounds": [lo1, lo1 + m, lo2, lo2 + m],
            "steps": _display_steps(matrix, rng),
        })
    rng.shuffle(components)
    counts = [_component_count(c) for c in components]
    return {
        "paper": "1708.06866",
        "components": components,
        "answer": {"component_counts": counts, "total": sum(counts)},
    }


def _linear_form(a: int, b: int, s: int) -> str:
    def term(coef, name, first=False):
        if coef == 0:
            return ""
        magnitude = "" if abs(coef) == 1 else str(abs(coef)) + "*"
        core = magnitude + name
        if first:
            return ("-" if coef < 0 else "") + core
        return (" - " if coef < 0 else " + ") + core

    text = term(a, "x", True)
    text += term(b, "y", not text)
    if not text:
        text = "0"
    if s:
        text += (" + " if s > 0 else " - ") + str(abs(s))
    return text


def render(inst) -> str:
    lines = [
        "Count triangles in an exactly specified finite simple graph.",
        "",
        "A triangle means an unordered set of three distinct vertices for which "
        "all three undirected edges are present.  Count each such set once.",
        "",
        "The graph is the disjoint union of the components listed below.  A vertex "
        "is an integer triple (tag,x,y).  For a component line, the "
        "vertices are precisely the triples with that tag whose two displayed "
        "linear forms L1(x,y), L2(x,y) satisfy their displayed half-open bounds.",
        "Two distinct vertices are adjacent exactly when they have the same tag "
        "and their difference (x'-x,y'-y) equals one of the four listed step "
        "vectors or its negative.  There are no edges between different tags.",
        "Every displayed lower bound is inclusive and every upper bound is exclusive.",
        "",
        "Components are 0-indexed in the displayed order:",
    ]
    for i, comp in enumerate(inst["components"]):
        a, b, c, d = comp["matrix"]
        s, t = comp["offset"]
        lo1, hi1, lo2, hi2 = comp["bounds"]
        lines.append(
            f"  {i}: tag={comp['tag']}; "
            f"L1={_linear_form(a, b, s)} with {lo1} <= L1 < {hi1}; "
            f"L2={_linear_form(c, d, t)} with {lo2} <= L2 < {hi2}; "
            f"steps={json.dumps(comp['steps'], separators=(',', ':'))}"
        )
    lines += [
        "",
        "Return an object with exactly two fields:",
        "  component_counts: one nonnegative integer per component, in displayed "
        "order, each equal to that component's number of triangles;",
        "  total: the sum of component_counts, hence the graph's triangle count.",
        "Order matters, repetitions are allowed, and no component may be omitted.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object.",
        "Example format only: "
        '<answer>{"component_counts":[4,16],"total":20}</answer>',
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    """Parse the final tagged JSON object while tolerating surrounding prose."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, dict) or set(answer) != {"component_counts", "total"}:
        return None
    counts = answer.get("component_counts")
    total = answer.get("total")
    if not isinstance(counts, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in counts):
        return None
    if isinstance(total, bool) or not isinstance(total, int):
        return None
    return answer


def _expected_steps(matrix: list[int]) -> set[tuple[int, int]]:
    return {_canonical_undirected_step(v) for v in _raw_steps(matrix)}


def _validate_component(comp) -> tuple[bool, str]:
    if not isinstance(comp, dict):
        return False, "component data are malformed"
    try:
        matrix = comp["matrix"]
        offset = comp["offset"]
        bounds = comp["bounds"]
        steps = comp["steps"]
        tag = comp["tag"]
    except KeyError:
        return False, "component data omit a required field"
    if isinstance(tag, bool) or not isinstance(tag, int):
        return False, "component tag is invalid"
    if (not isinstance(matrix, list) or len(matrix) != 4
            or any(isinstance(x, bool) or not isinstance(x, int) for x in matrix)):
        return False, "component matrix is malformed"
    a, b, c, d = matrix
    if a * d - b * c != 1:
        return False, "component coordinate matrix is not unimodular"
    if (not isinstance(offset, list) or len(offset) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in offset)):
        return False, "component offset is malformed"
    if (not isinstance(bounds, list) or len(bounds) != 4
            or any(isinstance(x, bool) or not isinstance(x, int) for x in bounds)):
        return False, "component bounds are malformed"
    width, height = _shape(comp)
    if width < 3 or height < 3 or width != height:
        return False, "component bounds do not define a supported square"
    if (not isinstance(steps, list) or len(steps) != 4
            or any(not isinstance(v, list) or len(v) != 2 for v in steps)
            or any(isinstance(x, bool) or not isinstance(x, int)
                   for v in steps for x in v)):
        return False, "component edge steps are malformed"
    got = {_canonical_undirected_step((v[0], v[1])) for v in steps}
    if got != _expected_steps(matrix):
        return False, "component edge steps do not match its coordinate forms"
    return True, "ok"


def verify(inst, answer):
    """Verify any correct certificate exactly; never consult inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object is empty"
    missing = {"component_counts", "total"} - set(answer)
    if missing:
        return False, "answer is missing required fields"
    extra = set(answer) - {"component_counts", "total"}
    if extra:
        return False, "answer has unexpected fields"
    counts = answer["component_counts"]
    total = answer["total"]
    if not isinstance(counts, list):
        return False, "component_counts must be a JSON list"
    expected_len = len(inst["components"])
    if len(counts) < expected_len:
        return False, f"too few component counts: expected {expected_len}"
    if len(counts) > expected_len:
        return False, f"too many component counts: expected {expected_len}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in counts):
        return False, "every component count must be an integer"
    if any(x < 0 for x in counts):
        return False, "component count is outside the nonnegative range"
    if isinstance(total, bool) or not isinstance(total, int):
        return False, "total must be an integer"
    if total != sum(counts):
        return False, "total is not the sum of component_counts"

    seen_tags = set()
    for i, (comp, claimed) in enumerate(zip(inst["components"], counts)):
        ok, why = _validate_component(comp)
        if not ok:
            return False, f"component {i}: {why}"
        if comp["tag"] in seen_tags:
            return False, "component tags are not distinct"
        seen_tags.add(comp["tag"])
        expected = _component_count(comp)
        if claimed != expected:
            return False, f"component {i} triangle count is incorrect"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the degree-aware bounded certificate language."""
    counts = [rng.randrange(_component_bound(c) + 1)
              for c in inst["components"]]
    return {"component_counts": counts, "total": sum(counts)}


def search_space(inst):
    size = 1
    for comp in inst["components"]:
        size *= _component_bound(comp) + 1
    return size


def enumerate_all(inst):
    ranges = [_component_bound(c) + 1 for c in inst["components"]]
    size = math.prod(ranges)
    if size > 200_000:
        return None
    hits = 0
    for counts in itertools.product(*(range(r) for r in ranges)):
        answer = {"component_counts": list(counts), "total": sum(counts)}
        hits += int(verify(inst, answer)[0])
    return hits


def canonical_key(inst):
    """Canonicalize component order, tags, coordinates, and grid-axis swaps."""
    shapes = sorted(tuple(sorted(_shape(c))) for c in inst["components"])
    blob = json.dumps(shapes, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Grow every component while keeping the certificate length fixed."""
    out = dict(params)
    old_n = int(out.get("n", 96))
    out["n"] = old_n * 2
    out["jitter"] = max(int(out.get("jitter", 31)) * 2, old_n // 2)
    out["shears"] = min(int(out.get("shears", 4)) + 1, 8)
    return out


# --- Reference algorithm and adversarial probes (selftest only) ------------

def _inverse_vertex(comp, u: int, v: int) -> tuple[int, int]:
    a, b, c, d = comp["matrix"]
    s, t = comp["offset"]
    uu, vv = u - s, v - t
    return d * uu - b * vv, -c * uu + a * vv


def _reference_component_count(comp) -> tuple[int, int]:
    """Generic forward-neighbour triangle enumeration on the actual graph."""
    lo1, hi1, lo2, hi2 = comp["bounds"]
    vertices = {_inverse_vertex(comp, u, v)
                for u in range(lo1, hi1) for v in range(lo2, hi2)}
    full_steps = set()
    for dx, dy in comp["steps"]:
        full_steps.add((dx, dy))
        full_steps.add((-dx, -dy))
    triangle_count = 0
    operations = len(vertices)  # vertex insertions
    for x, y in vertices:
        higher = []
        here = (x, y)
        for dx, dy in full_steps:
            operations += 1
            other = (x + dx, y + dy)
            if other in vertices and other > here:
                higher.append(other)
        for i in range(len(higher)):
            ux, uy = higher[i]
            for j in range(i + 1, len(higher)):
                vx, vy = higher[j]
                operations += 1
                if (vx - ux, vy - uy) in full_steps:
                    triangle_count += 1
    return triangle_count, operations


def _reference_algorithm(inst):
    start = time.perf_counter()
    counts = []
    operations = 0
    for comp in inst["components"]:
        count, used = _reference_component_count(comp)
        counts.append(count)
        operations += used
    answer = {"component_counts": counts, "total": sum(counts)}
    return answer, time.perf_counter() - start, operations


def _candidate_from_counts(counts):
    return {"component_counts": counts, "total": sum(counts)}


def _attack_candidates(inst, rng):
    components = inst["components"]
    shapes = [_shape(c) for c in components]
    one_per_cell = [(w - 1) * (h - 1) for w, h in shapes]
    paper_table = [8 * (w - 1) * (h - 1) for w, h in shapes]
    edge_over_three = [
        (w * (h - 1) + h * (w - 1) + 2 * (w - 1) * (h - 1)) // 3
        for w, h in shapes
    ]
    midpoint = [_component_bound(c) // 2 for c in components]
    largest = max(range(len(components)), key=lambda i: math.prod(shapes[i]))
    largest_only = [0] * len(components)
    largest_only[largest] = _component_count(components[largest])
    return {
        "outlier_largest_component_only": [_candidate_from_counts(largest_only)],
        "greedy_edges_divided_by_three": [_candidate_from_counts(edge_over_three)],
        "degree_bound_midpoint": [_candidate_from_counts(midpoint)],
        "in_context_one_triangle_per_cell": [_candidate_from_counts(one_per_cell)],
        "paper_table_double_count": [_candidate_from_counts(paper_table)],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _reordered(inst, rng):
    perm = list(range(len(inst["components"])))
    rng.shuffle(perm)
    components = [json.loads(json.dumps(inst["components"][i])) for i in perm]
    counts = [inst["answer"]["component_counts"][i] for i in perm]
    return {"paper": inst["paper"], "components": components,
            "answer": {"component_counts": counts, "total": sum(counts)}}


def _retagged(inst, rng):
    out = json.loads(json.dumps(inst))
    tags = rng.sample(range(1_000_000_000, 1_999_999_999), len(out["components"]))
    for comp, tag in zip(out["components"], tags):
        comp["tag"] = tag
    return out


def _recoordinatized(inst, rng):
    out = json.loads(json.dumps(inst))
    for comp in out["components"]:
        matrix = _unimodular_matrix(rng, 4)
        comp["matrix"] = matrix
        comp["offset"] = [rng.randrange(-9999, 10000), rng.randrange(-9999, 10000)]
        comp["steps"] = _display_steps(matrix, rng)
    return out


def _axis_swapped(inst):
    """Swap the two hidden coordinates, an isomorphism of each square."""
    out = json.loads(json.dumps(inst))
    for comp in out["components"]:
        a, b, c, d = comp["matrix"]
        # [[c,d],[-a,-b]] has determinant one and represents (v,-u).
        matrix = [c, d, -a, -b]
        s, t = comp["offset"]
        lo1, hi1, lo2, hi2 = comp["bounds"]
        comp["matrix"] = matrix
        comp["offset"] = [t, -s]
        # If lo <= u < hi for integral u, then 1-hi <= -u < 1-lo.
        comp["bounds"] = [lo2, hi2, 1 - hi1, 1 - lo1]
        comp["steps"] = [list(v) for v in _raw_steps(matrix)]
    return out


def _answer_token_measure(answer) -> int:
    blob = json.dumps(answer, separators=(",", ":"))
    return len(re.findall(r"[A-Za-z_]+|\d+|[{}\[\],:\-]", blob))


def selftest():
    report = {
        "paper": "1708.06866",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all presets, several seeds.
    verified = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            verified += int(ok)
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": verified == 12,
        "verified": verified,
        "attempts": 12,
        "failures": failures,
    }

    # G2: corruption shapes are adapted to the structured decomposition witness.
    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = ship["answer"]
    counts = answer["component_counts"]
    pair = next((
        (i, j) for i in range(len(counts)) for j in range(i + 1, len(counts))
        if counts[i] != counts[j]
    ), (0, 1))
    swapped = counts[:]
    swapped[pair[0]], swapped[pair[1]] = swapped[pair[1]], swapped[pair[0]]
    corruptions = {
        "drop": _candidate_from_counts(counts[:-1]),
        "swap": _candidate_from_counts(swapped),
        "duplicate": _candidate_from_counts(counts + [counts[-1]]),
        "empty": {},
        "out_of_range": _candidate_from_counts([-1] + counts[1:]),
    }
    rejected = {}
    for name, bad in corruptions.items():
        ok, why = verify(ship, bad)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = {x["reason"] for x in rejected.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in rejected.values()) and len(reasons) == 5,
        "cases": rejected,
        "distinct_reasons": len(reasons),
    }

    reply = (
        "The component calculation gives:\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\n"
    )
    parsed = parse_answer(reply)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "parsed_matches": parsed == answer,
        "json_native": json_native,
    }

    # Shared structure-aware shipping density sample for G4/G5.
    density_inst = make_instance(
        seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )
    density_rng = random.Random(0x170806866)
    samples = 200_000
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(density_inst, random_candidate(density_inst, density_rng))[0])
    density_wall = time.perf_counter() - start
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "structure_aware": True,
        "language_size": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
    }

    # Track-B adversaries fail; the successful domain algorithm is separate.
    attack_success = {}
    reference_times = []
    reference_ops = []
    reference_success = 0
    for seed in range(8):
        inst = make_instance(seed=100 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks = _attack_candidates(inst, random.Random(9000 + seed))
        for name, candidates in attacks.items():
            solved = any(verify(inst, candidate)[0] for candidate in candidates)
            attack_success[name] = attack_success.get(name, 0) + int(solved)
        ref_answer, wall, operations = _reference_algorithm(inst)
        reference_success += int(verify(inst, ref_answer)[0])
        reference_times.append(wall)
        reference_ops.append(operations)

    attack_report = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_success.items()
    }
    all_failed = len(attack_report) >= 4 and all(
        row["successes"] == 0 for row in attack_report.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_success == 8,
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "forward-neighbour triangle enumeration",
            "complexity": "O(V*Delta^2) exact; Delta <= 8 here",
            "wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_ops) / 8),
            "operations_min": min(reference_ops),
            "operations_max": max(reference_ops),
            "solves": f"{reference_success}/8, as expected",
        },
    }

    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and reference_success == 8,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": probability,
        "shipping_exact_language_size": search_space(density_inst),
        "reference_wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
        "reference_operations_mean": round(sum(reference_ops) / 8),
        "demo_exact_solution_count_seed0": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
    }

    doubled_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled = make_instance(seed=23, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ship_vertices = sum(math.prod(_shape(c)) for c in ship["components"])
    doubled_vertices = sum(math.prod(_shape(c)) for c in doubled["components"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled_vertices > ship_vertices
            and len(doubled["answer"]["component_counts"])
            == len(answer["component_counts"])
        ),
        "shipping_vertices": ship_vertices,
        "doubled_vertices": doubled_vertices,
        "answer_components_before": len(answer["component_counts"]),
        "answer_components_after": len(doubled["answer"]["component_counts"]),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_failures = []
    for seed in range(20):
        inst = make_instance(seed=700 + seed, **DIFFICULTY["easy"])
        key = canonical_key(inst)
        rng = random.Random(800 + seed)
        variants = [
            _reordered(inst, rng),
            _retagged(inst, rng),
            _recoordinatized(inst, rng),
            _axis_swapped(inst),
        ]
        composed = _axis_swapped(_recoordinatized(_retagged(_reordered(inst, rng), rng), rng))
        variants.append(composed)
        for variant in variants:
            same = canonical_key(variant) == key
            ok, _ = verify(variant, variant["answer"])
            invariant_checks += int(same)
            carried_checks += int(ok)
            if not same or not ok:
                invariant_failures.append({"seed": seed, "same_key": same, "valid": ok})
    unrelated_keys = {
        canonical_key(make_instance(seed=1200 + seed, **DIFFICULTY["easy"]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 100
            and carried_checks == 100
            and len(unrelated_keys) == 20
        ),
        "invariance_passed": invariant_checks,
        "invariance_attempts": 100,
        "carried_answer_verifies": carried_checks,
        "carried_answer_attempts": 100,
        "distinct_unrelated_keys": len(unrelated_keys),
        "distinctness_attempts": 20,
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_elements = len(counts) + 1
    answer_tokens = _answer_token_measure(answer)
    # Per component, conservatively count: determinant check (3), eight
    # transformed step coordinates (3 arithmetic operations each), two bound
    # widths (2), and the 4*(w-1)*(h-1) evaluation (4).  Comparisons and set
    # recognition are not arithmetic.  Add one operation per component to sum.
    intended_operations = 34 * len(counts) + max(0, len(counts) - 1)
    arms = json.loads(json.dumps(G9_RESULTS["arms"]))
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = (
        len(answer_blob) <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [v for k, v in report.items() if k.startswith("G") and k[1:2].isdigit()]
    report["all_passed"] = all(g.get("pass") for g in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
