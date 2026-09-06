"""Planted integer layered rectangle-contact instances for arXiv:2311.15057.

The witness is a bounded, integer x-coordinate for every fixed-order,
unit-height rectangle.  Widths, coordinates, and every random choice are made
with a local ``random.Random(seed)``.  Only the Python standard library is used.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re


DIFFICULTY = {
    "demo": {
        "n": 3,
        "layer_ratio": 0.75,
        "max_width": 1,
        "canvas_factor": 2,
        "plant_span_factor": 2,
        "plant_trials": 64,
    },
    "easy": {"n": 9, "layer_ratio": 1.0, "max_width": 3, "canvas_factor": 14, "plant_span_factor": 4, "plant_trials": 32},
    "medium": {
        "n": 14,
        "layer_ratio": 1.0,
        "max_width": 3,
        "canvas_factor": 14,
        "plant_span_factor": 4,
        "plant_trials": 32,
    },
    "hard": {
        "n": 22,
        "layer_ratio": 1.0,
        "max_width": 3,
        "canvas_factor": 14,
        "plant_span_factor": 4,
        "plant_trials": 40,
    },
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
The exact definition comes from Section 1, paragraph “Problem statement”:
vertices have a fixed order within each layer, rectangles have unit height and
prescribed width, gaps are allowed, contacts must have positive length, and a
contact corresponding to a nonedge is a forbidden false adjacency.  This
module uses the integer variant k-IntLayeredCrown and asks for the NP witness
from Lemma 1: all integer x-coordinates of a representation with at least k
realized edges.

Section 2 proves k-IntLayeredCrown NP-complete even for internally triangulated
graphs, with widths only 1, 2, and 3.  The combining-gadgets proof explicitly
uses a frame to force the representation into a designated bounding box; the
module states that box directly.  Section 3.2 is the easy-regime warning: the
exact dynamic program takes O(nW)^L and is XP in the number L of layers when W
is polynomial.  Consequently W stays at most 3 but L grows linearly with n;
the two-layer linear-time case discussed in Sections 1 and 3.1 is avoided.

Inverse generation samples many complete geometries first and retains the
highest-contact one, then derives its required horizontal edges and completes
each vertical strip to a random maximal noncrossing staircase.  A planted
vertical contact and a decoy therefore have the same permitted layer pair,
order type, width distribution, and local staircase degree scale.  This also
keeps the supplied graph planar.  The threshold is the retained geometry's
recomputed contact count, never an asserted optimum.

The outlier attack turns per-rectangle degree into gap sizes, the greedy attack
beam-searches translations after assigning every unknown gap its minimum
length, and random restart samples bounded valid layouts while rejecting false
adjacencies.  Independent widths, random positive gap sizes, random common
translation, and same-strip staircase decoys defeat those attacks in selftest.
The canonical key is an exact normal form for this representation's input
symmetries: arbitrary edge-list order plus horizontal reflection, vertical
reflection, and their composition.  Vertex IDs are the intrinsic 0-based
(layer, fixed-order position) pairs, so there is no additional free numbering.
""".strip()


# ---------------------------------------------------------------------------
# Geometry and generation helpers


def _weak_composition(total: int, parts: int, rng: random.Random) -> list[int]:
    """Uniform weak composition of total into ``parts`` labelled parts."""
    if parts == 1:
        return [total]
    bars = sorted(rng.sample(range(total + parts - 1), parts - 1))
    result = []
    previous = -1
    for bar in bars + [total + parts - 1]:
        result.append(bar - previous - 1)
        previous = bar
    return result


def _positions_from_gaps(widths: list[int], gaps: list[int], offset: int = 0) -> list[int]:
    x = offset + gaps[0]
    result = []
    for j, width in enumerate(widths):
        result.append(x)
        x += width + gaps[j + 1]
    return result


def _horizontal_contacts(widths: list[int], xs: list[int]) -> list[int]:
    return [j for j in range(len(widths) - 1) if xs[j] + widths[j] == xs[j + 1]]


def _vertical_contacts(
    widths_a: list[int], xs_a: list[int], widths_b: list[int], xs_b: list[int]
) -> list[tuple[int, int]]:
    """All positive-length overlaps of two ordered, interior-disjoint rows."""
    i = j = 0
    contacts: list[tuple[int, int]] = []
    while i < len(widths_a) and j < len(widths_b):
        end_a = xs_a[i] + widths_a[i]
        end_b = xs_b[j] + widths_b[j]
        if max(xs_a[i], xs_b[j]) < min(end_a, end_b):
            contacts.append((i, j))
        if end_a < end_b:
            i += 1
        elif end_b < end_a:
            j += 1
        else:
            i += 1
            j += 1
    return contacts


def _raw_contacts(widths: list[list[int]], positions: list[list[int]]) -> int:
    horizontal = sum(
        len(_horizontal_contacts(widths[i], positions[i]))
        for i in range(len(widths))
    )
    vertical = sum(
        len(_vertical_contacts(widths[i], positions[i], widths[i + 1], positions[i + 1]))
        for i in range(len(widths) - 1)
    )
    return horizontal + vertical


def _staircase_through(
    q: int, required: list[tuple[int, int]], rng: random.Random
) -> list[list[int]]:
    """Random maximal product-order chain containing every required contact."""
    ordered = sorted(set(required))
    for first, second in zip(ordered, ordered[1:]):
        if first[0] > second[0] or first[1] > second[1]:
            raise AssertionError("geometric contacts must be noncrossing")
    anchors = sorted(set([(0, 0), *ordered, (q - 1, q - 1)]))
    path = [anchors[0]]
    current = anchors[0]
    for target in anchors[1:]:
        steps = [0] * (target[0] - current[0]) + [1] * (target[1] - current[1])
        rng.shuffle(steps)
        a, b = current
        for axis in steps:
            if axis == 0:
                a += 1
            else:
                b += 1
            path.append((a, b))
        current = target
    if not set(required).issubset(path):
        raise AssertionError("staircase lost a required contact")
    return [[a, b] for a, b in path]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a complete rectangle placement first, then derive graph and k.

    ``n`` is the number of rectangles per layer.  The layer count is
    ``ceil(layer_ratio*n)`` and therefore grows with n in every shipped preset.
    """
    layer_ratio = float(params.pop("layer_ratio", 1.0))
    max_width = int(params.pop("max_width", 3))
    canvas_factor = int(params.pop("canvas_factor", 14))
    plant_span_factor = int(params.pop("plant_span_factor", 4))
    plant_trials = int(params.pop("plant_trials", 32))
    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if layer_ratio <= 0:
        raise ValueError("layer_ratio must be positive")
    if max_width < 1 or max_width > 3:
        raise ValueError("max_width must be in 1..3")
    if plant_span_factor < max_width or canvas_factor < plant_span_factor:
        raise ValueError("canvas must contain the planted local span and all widths")
    if plant_trials < 1:
        raise ValueError("plant_trials must be positive")

    rng = random.Random(seed)
    layers = max(3, math.ceil(layer_ratio * n))
    q = n
    bound = canvas_factor * q
    local_span = plant_span_factor * q
    widths = [[rng.randint(1, max_width) for _ in range(q)] for _ in range(layers)]
    if any(sum(row) > local_span for row in widths):
        raise ValueError("plant_span_factor is too small for sampled widths")

    # The witness geometries are sampled before graph edges or k exist.  Keeping
    # the best of independent samples raises the threshold without claiming it
    # is globally optimal.
    best_positions: list[list[int]] | None = None
    best_score = -1
    best_tie = None
    for _ in range(plant_trials):
        local = []
        for row in widths:
            slack = local_span - sum(row)
            gaps = _weak_composition(slack, q + 1, rng)
            local.append(_positions_from_gaps(row, gaps))
        score = _raw_contacts(widths, local)
        tie = tuple(tuple(xs) for xs in local)
        if score > best_score or (score == best_score and (best_tie is None or tie < best_tie)):
            best_positions, best_score, best_tie = local, score, tie
    assert best_positions is not None
    common_offset = rng.randrange(bound - local_span + 1)
    answer = [[x + common_offset for x in row] for row in best_positions]

    horizontal_edges = [
        _horizontal_contacts(widths[i], answer[i]) for i in range(layers)
    ]
    vertical_edges = []
    for i in range(layers - 1):
        required = _vertical_contacts(
            widths[i], answer[i], widths[i + 1], answer[i + 1]
        )
        vertical_edges.append(_staircase_through(q, required, rng))

    return {
        "family": "bounded integer layered rectangle contacts",
        "layers": layers,
        "n": q,
        "bound": bound,
        "widths": widths,
        "horizontal_edges": horizontal_edges,
        "vertical_edges": vertical_edges,
        "k": best_score,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Problem contract


def render(inst: dict) -> str:
    lines = [
        "INTEGER LAYERED RECTANGLE CONTACT WITNESS",
        "",
        "There are unit-height, axis-aligned rectangles on fixed horizontal layers.",
        "Rectangle v(i,j) is on layer i at fixed left-to-right position j, has the",
        "listed positive integer width, and must be assigned an integer left x-coordinate",
        "x[i][j]. All indices are 0-based. Coordinates must satisfy 0 <= x[i][j] and",
        "x[i][j] + width[i][j] <= B. On one layer, rectangles must occur in the",
        "listed order and their interiors may not overlap: x[i][j]+width[i][j] <=",
        "x[i][j+1]. Equality is allowed and is a horizontal contact. Gaps are allowed.",
        "",
        "Rectangles on adjacent layers have a vertical contact exactly when their closed",
        "x-intervals overlap in a segment of POSITIVE length. Endpoint-only intersection",
        "has length zero and is not a contact. A horizontal contact exists exactly at",
        "equality for consecutive rectangles on one layer. A contact is permitted only",
        "when its pair appears in the corresponding edge list below; any other contact is",
        "a forbidden false adjacency. Listed edges need not all be realized.",
        "",
        "Find coordinates that form a valid representation with at least k realized",
        "listed edges. Each contact counts once. The required answer is one JSON outer",
        "array in layer order, containing exactly one inner array of exactly n integer",
        "left coordinates per layer, in the fixed rectangle order. Repeats are not",
        "allowed because widths are positive; the coordinate order is not permutable.",
        "",
        f"L = {inst['layers']}",
        f"n = {inst['n']}",
        f"B = {inst['bound']}  (right boundary is inclusive for rectangle endpoints)",
        f"k = {inst['k']}",
        "",
        "WIDTHS",
    ]
    for i, row in enumerate(inst["widths"]):
        lines.append(f"layer {i}: " + " ".join(map(str, row)))
    lines += ["", "HORIZONTAL EDGES"]
    for i, edges in enumerate(inst["horizontal_edges"]):
        shown = " ".join(f"{j}-{j + 1}" for j in sorted(set(edges))) or "none"
        lines.append(f"layer {i}: {shown}")
    lines += ["", "VERTICAL EDGES"]
    for i, edges in enumerate(inst["vertical_edges"]):
        shown = " ".join(f"{a}-{b}" for a, b in sorted({tuple(e) for e in edges}))
        lines.append(f"layers {i}/{i + 1}: {shown or 'none'}")
    example = "[[0,2,5],[1,4,8]]"
    lines += [
        "",
        "Give your final answer inside <answer></answer> tags, as the JSON array",
        "specified above (with the actual L rows and n entries per row).",
        f"Example syntax only: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ]
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer(?:\s[^>]*)?>(.*?)</answer\s*>", re.I | re.S)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON value, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid representation exactly; the planted answer is never read."""
    layers, q, bound = inst["layers"], inst["n"], inst["bound"]
    widths = inst["widths"]
    if not isinstance(answer, list) or len(answer) != layers:
        return False, f"answer must be a JSON array with exactly {layers} layer arrays"
    for i, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != q:
            return False, f"layer {i} must contain exactly {q} coordinates"
        if any(not isinstance(x, int) or isinstance(x, bool) for x in row):
            return False, f"layer {i} contains a non-integer coordinate"
        for j, x in enumerate(row):
            if x < 0 or x + widths[i][j] > bound:
                return False, f"rectangle ({i},{j}) lies outside the inclusive canvas bounds"
        for j in range(1, q):
            if row[j] == row[j - 1]:
                return False, f"layer {i} has a duplicated starting coordinate"
            if row[j] < row[j - 1]:
                return False, f"layer {i} is not in its fixed left-to-right order"
            if row[j] < row[j - 1] + widths[i][j - 1]:
                return False, f"rectangles ({i},{j - 1}) and ({i},{j}) overlap in their interiors"

    h_edges = [set(map(int, row)) for row in inst["horizontal_edges"]]
    v_edges = [{tuple(map(int, edge)) for edge in strip} for strip in inst["vertical_edges"]]
    contacts = 0
    for i in range(layers):
        for j in _horizontal_contacts(widths[i], answer[i]):
            if j not in h_edges[i]:
                return False, f"false horizontal adjacency on layer {i} between {j} and {j + 1}"
            contacts += 1
    for i in range(layers - 1):
        for edge in _vertical_contacts(widths[i], answer[i], widths[i + 1], answer[i + 1]):
            if edge not in v_edges[i]:
                return False, f"false vertical adjacency between ({i},{edge[0]}) and ({i + 1},{edge[1]})"
            contacts += 1
    if contacts < inst["k"]:
        return False, f"only {contacts} contacts are realized; at least {inst['k']} are required"
    return True, "ok"


# ---------------------------------------------------------------------------
# Guess prior and exhaustive small-case counting


def _random_safe_row(
    widths: list[int], allowed_horizontal: set[int], bound: int, rng: random.Random
) -> list[int]:
    """Random compact row with no forbidden horizontal contact."""
    gaps = []
    for j in range(len(widths) - 1):
        gaps.append(rng.randrange(2) if j in allowed_horizontal else 1)
    span = sum(widths) + sum(gaps)
    if span > bound:
        raise ValueError("canvas is too narrow for structure-aware sampling")
    offset = rng.randrange(bound - span + 1)
    xs = [offset]
    for j, gap in enumerate(gaps):
        xs.append(xs[-1] + widths[j] + gap)
    return xs


def _vertical_is_allowed(
    widths_a: list[int], xs_a: list[int], widths_b: list[int], xs_b: list[int],
    allowed: set[tuple[int, int]],
) -> bool:
    return all(edge in allowed for edge in _vertical_contacts(widths_a, xs_a, widths_b, xs_b))


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample a planted-independent valid layout, including no false contacts.

    Rows use random 0/1 gaps consistent with the horizontal edge list.  Each new
    row is redrawn until all incidental vertical contacts are listed edges.  A
    deterministic outer-gap fallback guarantees termination and still uses no
    planted coordinates.  Thus every returned candidate already obeys shape,
    bounds, fixed order, nonoverlap, and the false-adjacency prohibition.
    """
    layers, bound = inst["layers"], inst["bound"]
    widths = inst["widths"]
    h_edges = [set(row) for row in inst["horizontal_edges"]]
    v_edges = [{tuple(edge) for edge in strip} for strip in inst["vertical_edges"]]
    result = [_random_safe_row(widths[0], h_edges[0], bound, rng)]
    for i in range(1, layers):
        chosen = None
        for _ in range(24):
            trial = _random_safe_row(widths[i], h_edges[i], bound, rng)
            if _vertical_is_allowed(
                widths[i - 1], result[-1], widths[i], trial, v_edges[i - 1]
            ):
                chosen = trial
                break
        if chosen is None:
            # With all internal gaps set to one, span <= 4*n for widths <= 3.
            gaps = [0] + [1] * (inst["n"] - 1) + [0]
            packed = _positions_from_gaps(widths[i], gaps)
            span = packed[-1] + widths[i][-1]
            previous_left = result[-1][0]
            previous_right = result[-1][-1] + widths[i - 1][-1]
            if previous_left >= span:
                chosen = packed
            elif bound - previous_right >= span:
                chosen = [x + bound - span for x in packed]
            else:
                # This branch is reachable only for custom cramped parameters.
                # Search every translation of the safe packed row exactly.
                for shift in range(bound - span + 1):
                    trial = [x + shift for x in packed]
                    if _vertical_is_allowed(
                        widths[i - 1], result[-1], widths[i], trial, v_edges[i - 1]
                    ):
                        chosen = trial
                        break
            if chosen is None:
                # The plant proves existence, but cramped custom canvases may
                # require non-unit gaps.  A bounded exhaustive row search is the
                # honest fallback rather than consulting inst["answer"].
                for trial in _row_placements(widths[i], bound):
                    if not all(
                        j in h_edges[i]
                        for j in _horizontal_contacts(widths[i], trial)
                    ):
                        continue
                    if _vertical_is_allowed(
                        widths[i - 1], result[-1], widths[i], trial, v_edges[i - 1]
                    ):
                        chosen = trial
                        break
            if chosen is None:
                raise RuntimeError("could not sample a valid structural candidate")
        result.append(chosen)
    return result


def search_space(inst: dict) -> int | None:
    """Naive count of bounded, fixed-order, nonoverlapping coordinate arrays."""
    total = 1
    q, bound = inst["n"], inst["bound"]
    for widths in inst["widths"]:
        slack = bound - sum(widths)
        if slack < 0:
            return 0
        total *= math.comb(slack + q, q)
    return total


def _row_placements(widths: list[int], bound: int):
    q = len(widths)
    slack = bound - sum(widths)
    prefixes = [0]
    for width in widths[:-1]:
        prefixes.append(prefixes[-1] + width)
    for reduced in itertools.combinations_with_replacement(range(slack + 1), q):
        yield [reduced[j] + prefixes[j] for j in range(q)]


def enumerate_all(inst: dict) -> int | None:
    """Exact witness count when the entire naive space has at most 500,000 rows."""
    space = search_space(inst)
    if space is None or space > 500_000:
        return None
    choices = [list(_row_placements(row, inst["bound"])) for row in inst["widths"]]
    count = 0
    for candidate in itertools.product(*choices):
        count += verify(inst, [list(row) for row in candidate])[0]
    return count


# ---------------------------------------------------------------------------
# Structural canonicalization


def _transform_instance(inst: dict, horizontal: bool, vertical: bool) -> dict:
    """Carry the instance and its witness through canvas/layer reflections."""
    layers, q, bound = inst["layers"], inst["n"], inst["bound"]
    order = list(range(layers - 1, -1, -1)) if vertical else list(range(layers))
    widths = []
    answer = []
    for old_i in order:
        old_widths = inst["widths"][old_i]
        old_answer = inst.get("answer", [[] for _ in range(layers)])[old_i]
        if horizontal:
            widths.append(list(reversed(old_widths)))
            if old_answer:
                answer.append([
                    bound - old_answer[j] - old_widths[j]
                    for j in range(q - 1, -1, -1)
                ])
            else:
                answer.append([])
        else:
            widths.append(list(old_widths))
            answer.append(list(old_answer))

    horizontal_edges = [[] for _ in range(layers)]
    for old_i, edges in enumerate(inst["horizontal_edges"]):
        new_i = layers - 1 - old_i if vertical else old_i
        horizontal_edges[new_i] = [q - 2 - int(j) if horizontal else int(j) for j in edges]

    vertical_edges = [[] for _ in range(layers - 1)]
    for old_i, edges in enumerate(inst["vertical_edges"]):
        for a0, b0 in edges:
            a = q - 1 - int(a0) if horizontal else int(a0)
            b = q - 1 - int(b0) if horizontal else int(b0)
            if vertical:
                vertical_edges[layers - 2 - old_i].append([b, a])
            else:
                vertical_edges[old_i].append([a, b])
    return {
        "family": inst.get("family", "bounded integer layered rectangle contacts"),
        "layers": layers,
        "n": q,
        "bound": bound,
        "widths": widths,
        "horizontal_edges": horizontal_edges,
        "vertical_edges": vertical_edges,
        "k": inst["k"],
        "answer": answer,
    }


def _normal_payload(inst: dict) -> str:
    payload = {
        "layers": inst["layers"],
        "n": inst["n"],
        "bound": inst["bound"],
        "k": inst["k"],
        "widths": inst["widths"],
        "horizontal_edges": [sorted(set(map(int, row))) for row in inst["horizontal_edges"]],
        "vertical_edges": [
            sorted({tuple(map(int, edge)) for edge in strip})
            for strip in inst["vertical_edges"]
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    """Exact normal form under input order and the rectangle-family reflections."""
    forms = [
        _normal_payload(_transform_instance(inst, horizontal, vertical))
        for horizontal in (False, True)
        for vertical in (False, True)
    ]
    return hashlib.sha256(min(forms).encode()).hexdigest()


def escalate(params: dict) -> dict | None:
    """Grow both row length and layer count; planting prevents unsatisfiability."""
    result = dict(params)
    result["n"] = math.ceil(int(result["n"]) * 1.45)
    result["plant_trials"] = max(int(result.get("plant_trials", 32)), 40)
    return result


# ---------------------------------------------------------------------------
# Cheap adversaries


def _degree_outlier_attack(inst: dict) -> list[list[int]]:
    """Turn conspicuous per-vertex degree into deterministic gap lengths."""
    layers, q, bound = inst["layers"], inst["n"], inst["bound"]
    degrees = [[0] * q for _ in range(layers)]
    for i, edges in enumerate(inst["horizontal_edges"]):
        for j in edges:
            degrees[i][j] += 1
            degrees[i][j + 1] += 1
    for i, strip in enumerate(inst["vertical_edges"]):
        for a, b in strip:
            degrees[i][a] += 1
            degrees[i + 1][b] += 1
    result = []
    for i in range(layers):
        median = sorted(degrees[i])[q // 2]
        gaps = [0]
        for j in range(q - 1):
            if j in set(inst["horizontal_edges"][i]):
                gaps.append(0)
            else:
                gaps.append(1 + int(degrees[i][j] < median))
        gaps.append(0)
        xs = _positions_from_gaps(inst["widths"][i], gaps)
        span = xs[-1] + inst["widths"][i][-1]
        shift = max(0, (bound - span) // 2)
        result.append([x + shift for x in xs])
    return result


def _minimum_gap_pattern(inst: dict, i: int) -> list[int]:
    allowed = set(inst["horizontal_edges"][i])
    gaps = [0] + [0 if j in allowed else 1 for j in range(inst["n"] - 1)] + [0]
    return _positions_from_gaps(inst["widths"][i], gaps)


def _greedy_translation_attack(inst: dict, beam_width: int = 24) -> list[list[int]]:
    """Beam-search layer translations after setting every unknown gap to one."""
    layers, bound = inst["layers"], inst["bound"]
    patterns = [_minimum_gap_pattern(inst, i) for i in range(layers)]
    shifts = [
        list(range(bound - (patterns[i][-1] + inst["widths"][i][-1]) + 1))
        for i in range(layers)
    ]
    if not all(shifts):
        return patterns
    first_choices = shifts[0]
    if len(first_choices) > beam_width:
        first_choices = [
            first_choices[round(t * (len(first_choices) - 1) / (beam_width - 1))]
            for t in range(beam_width)
        ]
    base_h = len(inst["horizontal_edges"][0])
    beam = [(base_h, [s], [[x + s for x in patterns[0]]]) for s in first_choices]
    for i in range(1, layers):
        allowed = {tuple(edge) for edge in inst["vertical_edges"][i - 1]}
        next_beam = []
        for score, used_shifts, rows in beam:
            previous = rows[-1]
            for shift in shifts[i]:
                row = [x + shift for x in patterns[i]]
                contacts = _vertical_contacts(
                    inst["widths"][i - 1], previous, inst["widths"][i], row
                )
                if not all(edge in allowed for edge in contacts):
                    continue
                next_beam.append((
                    score + len(inst["horizontal_edges"][i]) + len(contacts),
                    used_shifts + [shift], rows + [row],
                ))
        if not next_beam:
            return beam[0][2] + patterns[i:]
        next_beam.sort(key=lambda item: (-item[0], item[1]))
        beam = next_beam[:beam_width]
    return beam[0][2]


def _random_restart_attack(inst: dict, seed: int, restarts: int = 64) -> object | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Mandatory gates


def selftest() -> dict:
    report: dict[str, object] = {}

    g1_total, g1_failures = 0, []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)

    planted = [row[:] for row in inst["answer"]]
    dropped = [row[:] for row in planted]
    dropped[0] = dropped[0][:-1]
    swapped = [row[:] for row in planted]
    swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
    duplicate = [row[:] for row in planted]
    duplicate[0][1] = duplicate[0][0]
    out_of_range = [row[:] for row in planted]
    out_of_range[0][0] = -1
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    checked = {name: verify(inst, bad) for name, bad in corruptions.items()}
    reasons = {name: result[1] for name, result in checked.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(not result[0] for result in checked.values()) and len(set(reasons.values())) == 5,
        "rejected": sum(not result[0] for result in checked.values()),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I checked all positive-length contacts.\n<answer>```json\n{encoded}\n```</answer>\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_equal": parsed == inst["answer"],
    }

    trials, hits = 200_000, 0
    guess_rng = random.Random(271828)
    for _ in range(trials):
        hits += verify(inst, random_candidate(inst, guess_rng))[0]
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "measured_probability": hits / trials,
        "prior": (
            "random compact bounded layouts conditioned on fixed order, nonoverlap, "
            "allowed horizontal contacts, and no false vertical adjacency"
        ),
        "naive_space": search_space(inst),
    }

    tiny = make_instance(seed=17, **DIFFICULTY["demo"])
    exact = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    fraction = None if exact is None else exact / tiny_space
    report["G5_sparse"] = {
        "pass": exact is not None and fraction is not None and fraction < 0.01,
        "valid_answers": exact,
        "naive_space": tiny_space,
        "valid_fraction": fraction,
        "enumeration_cap": 500_000,
    }

    attack_seeds = list(range(800, 808))
    outlier_success = greedy_success = restart_success = 0
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **shipping_params)
        outlier_success += verify(attacked, _degree_outlier_attack(attacked))[0]
        greedy_success += verify(attacked, _greedy_translation_attack(attacked))[0]
        restart_success += _random_restart_attack(attacked, seed + 10_000) is not None
    report["G6_adversary_panel"] = {
        "pass": outlier_success == greedy_success == restart_success == 0,
        "seeds": len(attack_seeds),
        "outlier_degree_gaps": {"successes": outlier_success, "attempts": len(attack_seeds)},
        "greedy_minimum_gap_beam": {"successes": greedy_success, "attempts": len(attack_seeds)},
        "random_restart_64": {"successes": restart_success, "attempts": len(attack_seeds)},
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["layers"] > inst["layers"] and search_space(doubled) > search_space(inst),
        "base_n_layers": [inst["n"], inst["layers"]],
        "doubled_n_layers": [doubled["n"], doubled["layers"]],
        "base_search_bits": search_space(inst).bit_length(),
        "doubled_search_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = real_transform_checks = 0
    keys, errors = [], []
    transformations = [
        (False, False, "edge-list reorder"),
        (True, False, "horizontal reflection"),
        (False, True, "vertical reflection"),
        (True, True, "composed horizontal/vertical reflection"),
    ]
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        keys.append(key)
        for horizontal, vertical, name in transformations:
            changed = _transform_instance(original, horizontal, vertical)
            reorder_rng = random.Random(90_000 + 10 * seed + horizontal + 2 * vertical)
            for row in changed["horizontal_edges"]:
                reorder_rng.shuffle(row)
            for strip in changed["vertical_edges"]:
                reorder_rng.shuffle(strip)
            invariance_checks += 1
            if canonical_key(changed) != key:
                errors.append({"seed": seed, "transformation": name, "kind": "key_changed"})
            real_transform_checks += 1
            if not verify(changed, changed["answer"])[0]:
                errors.append({"seed": seed, "transformation": name, "kind": "carried_answer_failed"})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not errors and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "transformations": [item[2] for item in transformations],
        "errors": errors,
        "key_scope": "exact for edge ordering and the ambient horizontal/vertical reflections",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
