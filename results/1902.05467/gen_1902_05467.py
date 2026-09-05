"""Verified planted S-empty L(2,1)-labelings for arXiv:1902.05467.

Colucci and Gyori define L_S labelings of oriented graphs in Section 3.
For S empty only the arc constraint remains, and the paper explicitly identifies
the parameter with ordinary graph coloring (up to its label-span convention).
This module inverse-generates a balanced planted coloring, randomly orients the
edges, and asks for the corresponding partition into independent label classes.
The planted partition is known before any public arc is sampled.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter, deque


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "oriented simple graph",
        "integer-valued S-empty L(2,1)-labeling",
    ],
    "verification_operations": [
        "exact set-partition validation",
        "integer endpoint lookup for every arc",
        "exact adjacent-label separation check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Infer the balanced hidden label classes from overlapping neighbourhood "
        "constraints; single-vertex degree and orientation statistics carry no "
        "class signal."
    ),
    "hardness_basis": (
        "Track A: Theorem 1 of Abbe--Sandon (arXiv:1512.09080) proves "
        "O(n log n) acyclic-belief-propagation detection only for SNR>1; the "
        "shipping balanced q=5, a=0, b=17.5 distribution has n=240, expected "
        "degree 14 and SNR=0.875, below that proved efficient regime, with no "
        "known efficient exact-coloring method; G5 reports the measured cost "
        "of symmetry-normalized exact DSATUR at this preset."
    ),
    "max_answer_tokens": 180,
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
    "demo": {"n": 8, "colors": 4, "avg_degree": 3},
    "easy": {"n": 48, "colors": 4, "avg_degree": 7},
    "medium": {"n": 120, "colors": 4, "avg_degree": 9},
    "hard": {"n": 240, "colors": 5, "avg_degree": 14},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Repeated intersections of neighbourhood constraints carry the label "
    "information, while individual vertex degrees do not."
)
PLACEBO_HINT = (
    "Hint: Careful bookkeeping of vertex indices and arc directions helps avoid "
    "accidental transcription errors in the answer vector."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A vector of n even labels from {0,2,...,2(q-1)}, using every label. "
        "Global label names remain in the language, so it contains q! times the "
        "Stirling number S(n,q) vectors; this does not overstate guess resistance "
        "because valid labelings have the same q! renaming symmetry."
    ),
    "bounds": {
        "vertex_range": "1..n",
        "class_count": "q=colors",
        "class_size": "1..n-q+1",
        "total_vertex_atoms": "n",
        "named_preset_max_vertices": 240,
        "candidate_count": "q! times the Stirling number S(n,q)",
    },
}

# Filled from the script-owned oracle runs after local gates pass.  The three
# arms are diagnostic only; G9(c)'s answer/operation caps are the gated part.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "unreachable_openrouter_key_limit",
}

NOTES = r"""
STEP 0 and definition.  Section 1 defines a classical oriented L(2,1)
labeling: endpoints of an arc differ by at least two, and endpoints of a
directed two-step path differ by at least one.  Section 3 calls the three
two-step orientations P1, P2, P3 and defines L_S by enforcing only the path
types in S.  It explicitly identifies S=empty with ordinary coloring.  This
module therefore asks for the paper's S-empty object itself: q independent
label classes, interpreted as the even integer labels 0,2,...,2(q-1).

What is easy.  Theorem 1 and Theorems 3--5 produce broad greedy upper bounds;
they are efficient labeling algorithms when their much larger palettes are
allowed.  Section 2 also records that every directed tree has classical
oriented labeling number at most four.  Those regimes cannot support Track A.
Here the palette has exactly q classes, the graph has cycles, and the task is
the graph-coloring special case rather than the generous greedy palette.

Certificate algorithm and track.  The generator samples the balanced answer
first and then samples only cross-class edges, so its certificate is known by
inverse generation and no instance is solved.  The paper gives no algorithm
for recovering a q-class S-empty labeling.  General coloring search is still
efficient on many planted distributions, so worst-case NP-hardness is not used
as evidence.  For the independent-edge balanced planted-coloring model with
within-class rate a=0 and cross-class rate b/n, expected degree is
(q-1)b/q and the Abbe--Sandon Kesten--Stigum signal-to-noise ratio is
(a-b)^2/[q(a+(q-1)b)].  At q=5 and expected degree 14, b=17.5 and SNR=0.875:
the shipping preset sits below Theorem 1's SNR>1 efficient-detection regime.
The converse is not proved, and detection is not the same task as finding any
proper coloring.  This is therefore empirical distributional evidence, not an
average-case lower bound; G6 is decisive operationally.

Construction.  The vertices are shuffled into equal planted classes.  Each
cross-class pair becomes an edge independently with probability
avg_degree/(n-n/q), after which every edge receives an independent random
orientation and the arc list is shuffled.  Generation conditions only on
connectedness and minimum degree at least one.  These events and all marginal
degree/orientation statistics are symmetric in the planted classes.  The
checker never reads inst['answer'].

Attacks.  G6 tests an orientation-imbalance outlier labeling, deterministic
largest-degree greedy coloring, randomized greedy restarts, Walk-COL-style
min-conflicts repair, adjacency and nonbacktracking spectral subspace methods,
and capped DSATUR/DPLL (the domain-standard exact CSP algorithm).  DSATUR fixes
the colors on both endpoints of one edge, removing all global color-renaming
symmetry before search.  The spectral and local-repair tests are required
because the generator is planted; the generic attacks alone would not be
enough.  The earlier q=4,d=9 shipping candidate was discarded after stronger
min-conflicts repaired it.

Canonicalization.  Arc order, arc direction, and vertex names do not affect an
S-empty labeling problem.  canonical_key discards direction and performs
canonical one-dimensional color refinement on the underlying graph, then
hashes the refined edge-color multiset.  Random irregular graphs are normally
discretized by this refinement.  It is a strong cheap invariant, not a complete
graph-isomorphism canonizer; this limitation is recorded in README.md.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_DSATUR_NODE_CAP = 100_000
_UNPACK_FOUR_EVEN = tuple(
    tuple(2 * ((byte >> (2 * offset)) & 3) for offset in range(4))
    for byte in range(256)
)


def _checked_int(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _canonical_label_vector(labels: list[int]) -> list[int]:
    """Rename arbitrary class ids by order of first occurrence, then double."""
    renaming: dict[int, int] = {}
    result = []
    for label in labels:
        if label not in renaming:
            renaming[label] = 2 * len(renaming)
        result.append(renaming[label])
    return result


def _underlying_edges(inst: dict) -> list[tuple[int, int]]:
    return [
        (u - 1, v - 1) if u < v else (v - 1, u - 1)
        for u, v in inst["arcs"]
    ]


def _adjacency(inst: dict) -> list[set[int]]:
    adjacency = [set() for _ in range(inst["n"])]
    for u, v in _underlying_edges(inst):
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def _connected_and_no_isolates(n: int, edges: set[tuple[int, int]]) -> bool:
    adjacency = [[] for _ in range(n)]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    if any(not row for row in adjacency):
        return False
    seen = {0}
    queue = deque([0])
    while queue:
        u = queue.popleft()
        for v in adjacency[u]:
            if v not in seen:
                seen.add(v)
                queue.append(v)
    return len(seen) == n


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a balanced S-empty L(2,1) labeling.

    ``n`` is the number of vertices.  The planted partition is chosen first;
    public arcs are sampled only between different planted classes.
    """
    n = _checked_int("n", n, 8, 5000)
    unknown = set(params) - {"colors", "avg_degree"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    colors = _checked_int("colors", params.get("colors", 4), 3, 32)
    avg_degree = _checked_int("avg_degree", params.get("avg_degree", 9), 2, 1000)
    if n % colors:
        raise ValueError("n must be divisible by colors for balanced planting")
    class_size = n // colors
    available = n - class_size
    if avg_degree >= available:
        raise ValueError("avg_degree must be smaller than the cross-class population")

    rng = random.Random(seed)
    vertices = list(range(n))
    rng.shuffle(vertices)
    planted_class = [0] * n
    for color in range(colors):
        group = sorted(vertices[color * class_size : (color + 1) * class_size])
        for v in group:
            planted_class[v] = color

    edge_probability = avg_degree / available
    edges: set[tuple[int, int]] | None = None
    # Connectedness is an instance-quality condition symmetric in all colors.
    for _ in range(200):
        trial: set[tuple[int, int]] = set()
        for u in range(n):
            cu = planted_class[u]
            for v in range(u + 1, n):
                if cu != planted_class[v] and rng.random() < edge_probability:
                    trial.add((u, v))
        if _connected_and_no_isolates(n, trial):
            edges = trial
            break
    if edges is None:
        raise RuntimeError("could not sample a connected planted graph")

    arcs = []
    for u, v in edges:
        if rng.randrange(2):
            u, v = v, u
        arcs.append([u + 1, v + 1])
    rng.shuffle(arcs)
    answer = [2 * label for label in planted_class]
    return {
        "family": "planted_S_empty_oriented_L21_labeling",
        "n": n,
        "colors": colors,
        "avg_degree": avg_degree,
        "arcs": arcs,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a self-contained S-empty oriented-labeling problem."""
    n = inst["n"]
    colors = inst["colors"]
    arcs = inst["arcs"]
    lines = [
        "S-EMPTY L(2,1)-LABELING OF AN ORIENTED GRAPH",
        "",
        f"The vertices are the integers 1 through {n}, inclusive.  The graph",
        "is oriented: each listed ordered pair u>v denotes the arc u -> v.",
        "There are no loops, no repeated arcs, and never arcs in both directions",
        "between one pair of vertices.",
        "",
        "For this problem S is empty.  Thus no condition is imposed by any",
        "two-arc path.  Only an arc imposes a condition: its endpoint labels",
        "must differ by at least 2.  Find a labeling using exactly the even",
        f"labels 0, 2, ..., {2 * (colors - 1)} and using every one of those",
        "labels at least once.",
        "",
        "Equivalently, each even label is one nonempty independent class: no",
        "listed arc may have endpoints carrying the same label.",
        "",
        f"The {len(arcs)} arcs are listed below (u>v means u -> v):",
    ]
    width = 10
    for start in range(0, len(arcs), width):
        lines.append("  " + "  ".join(f"{u}>{v}" for u, v in arcs[start : start + width]))
    example_vector = [0, 2, 4, 6, 0, 2, 4, 6]
    lines.extend(
        [
            "",
            f"Output one JSON array of exactly {n} integers.  Entry i is the label",
            "of vertex i (so indexing is 1-based in the graph but array position 1",
            "is the first entry).  Use every allowed even label at least once.",
            "Do not put explanatory text inside the tags.",
            "",
            "Give your final answer inside <answer></answer> tags, as a JSON",
            "array of labels in vertex order.",
            "Format example only (not a solution to this instance): <answer>"
            + json.dumps(example_vector, separators=(",", ":")) + "</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Extract a flat JSON integer label vector from solver prose."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        raw = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(raw, list):
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) for value in raw):
        return None
    return raw


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid label vector without consulting the planted answer."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a JSON list of integer labels"
    if not answer:
        return False, "answer is empty"
    if len(answer) < inst["n"]:
        return False, f"too few labels: expected {inst['n']}, got {len(answer)}"
    if len(answer) > inst["n"]:
        return False, f"too many labels: expected {inst['n']}, got {len(answer)}"
    allowed = set(range(0, 2 * inst["colors"], 2))
    for vertex, label in enumerate(answer, 1):
        if isinstance(label, bool) or not isinstance(label, int):
            return False, f"vertex {vertex} has a non-integer label"
        if label not in allowed:
            return False, f"vertex {vertex} has forbidden label {label}"
    used = set(answer)
    if used != allowed:
        missing = min(allowed - used)
        return False, f"required label {missing} is unused"
    for arc_index, (u, v) in enumerate(inst["arcs"], 1):
        if abs(answer[u - 1] - answer[v - 1]) < 2:
            return False, f"arc {arc_index} ({u}->{v}) has endpoint labels less than 2 apart"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from onto words over the q named even labels."""
    n = inst["n"]
    colors = inst["colors"]
    while True:
        if colors == 4:
            # One C-level PRNG call replaces 240 Python randrange calls at the
            # shipping preset while preserving independent uniform colors.
            packed = rng.randbytes((n + 3) // 4)
            answer = [label for byte in packed for label in _UNPACK_FOUR_EVEN[byte]][:n]
            if len(set(answer)) == colors:
                return answer
        elif colors == 5:
            # Rejection from 0..249 removes the modulo bias of a byte.
            assignment = []
            while len(assignment) < n:
                block = rng.randbytes(n - len(assignment) + 8)
                assignment.extend(byte % 5 for byte in block if byte < 250)
            assignment = assignment[:n]
            if len(set(assignment)) == colors:
                return [2 * label for label in assignment]
        else:
            assignment = [rng.randrange(colors) for _ in range(n)]
            if len(set(assignment)) == colors:
                return [2 * label for label in assignment]


def search_space(inst: dict) -> int:
    """Return the Stirling number S(n,q), matching random_candidate exactly."""
    n = inst["n"]
    q = inst["colors"]
    row = [0] * (q + 1)
    row[0] = 1
    for _ in range(n):
        nxt = [0] * (q + 1)
        for k in range(1, q + 1):
            nxt[k] = row[k - 1] + k * row[k]
        row = nxt
    return math.factorial(q) * row[q]


def _restricted_growth_partitions(n: int, q: int):
    labels = [0] * n

    def visit(position: int, maximum: int):
        if position == n:
            if maximum + 1 == q:
                yield [2 * label for label in labels]
            return
        remaining = n - position - 1
        top = min(maximum + 1, q - 1)
        for label in range(top + 1):
            new_maximum = max(maximum, label)
            missing_classes = q - (new_maximum + 1)
            if missing_classes <= remaining:
                labels[position] = label
                yield from visit(position + 1, new_maximum)

    labels[0] = 0
    yield from visit(1, 0)


def enumerate_all(inst: dict) -> int | None:
    """Count valid partitions exactly when the declared space is at most 200k."""
    if search_space(inst) > 200_000:
        return None
    canonical_count = sum(
        1 for answer in _restricted_growth_partitions(inst["n"], inst["colors"])
        if verify(inst, answer)[0]
    )
    return math.factorial(inst["colors"]) * canonical_count


def canonical_key(inst: dict) -> str:
    """A vertex-, direction-, and arc-order-invariant color-refinement key."""
    n = inst["n"]
    adjacency = _adjacency(inst)
    signatures = [len(row) for row in adjacency]
    palette = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
    colors = [palette[signature] for signature in signatures]
    for _ in range(n):
        refined = [
            (colors[u], tuple(sorted(colors[v] for v in adjacency[u])))
            for u in range(n)
        ]
        mapping = {signature: index for index, signature in enumerate(sorted(set(refined)))}
        new_colors = [mapping[signature] for signature in refined]
        if len(set(new_colors)) == len(set(colors)):
            colors = new_colors
            break
        colors = new_colors
    class_sizes = sorted(Counter(colors).values())
    edge_colors = sorted(
        (min(colors[u], colors[v]), max(colors[u], colors[v]))
        for u, v in _underlying_edges(inst)
    )
    payload = [n, inst["colors"], class_sizes, edge_colors]
    encoded = json.dumps(payload, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Move along harder below/at-KS regimes without lengthening the witness."""
    current = {key: value for key, value in params.items() if key != "_preset"}
    n = int(current.get("n", 240))
    colors = int(current.get("colors", 4))
    sequence = {
        4: (5, 14),
        5: (6, 22),
        6: (8, 42),
        8: (10, 70),
        10: (12, 100),
        12: (15, 171),
        15: (16, 197),
    }
    if colors in sequence:
        next_colors, next_degree = sequence[colors]
        if n % next_colors == 0 and next_degree < n - n // next_colors:
            current["colors"] = next_colors
            current["avg_degree"] = next_degree
            return current
    # At q=16, keeping SNR near 0.875 would require average degree above the
    # 225 available cross-class vertices.  The calibrated axis is exhausted;
    # increasing n would push this 240-entry witness beyond the 256-atom cap.
    return "cap_bound"


def _answer_from_labels(labels: list[int], q: int) -> list[int]:
    if any(not 0 <= label < q for label in labels):
        raise ValueError("internal color is outside range")
    return [2 * label for label in labels]


def _outlier_orientation_attack(inst: dict) -> tuple[object, int]:
    outdegree = [0] * inst["n"]
    indegree = [0] * inst["n"]
    for u, v in inst["arcs"]:
        outdegree[u - 1] += 1
        indegree[v - 1] += 1
    order = sorted(
        range(inst["n"]),
        key=lambda vertex: (outdegree[vertex] - indegree[vertex],
                            outdegree[vertex] + indegree[vertex], vertex),
    )
    labels = [0] * inst["n"]
    size = inst["n"] // inst["colors"]
    for position, vertex in enumerate(order):
        labels[vertex] = min(position // size, inst["colors"] - 1)
    return _answer_from_labels(labels, inst["colors"]), inst["n"] + len(inst["arcs"])


def _greedy_attack(inst: dict) -> tuple[object | None, int]:
    adjacency = _adjacency(inst)
    order = sorted(range(inst["n"]), key=lambda u: (-len(adjacency[u]), u))
    labels = [-1] * inst["n"]
    steps = 0
    for u in order:
        forbidden = {labels[v] for v in adjacency[u] if labels[v] >= 0}
        steps += len(adjacency[u])
        available = [color for color in range(inst["colors"]) if color not in forbidden]
        if not available:
            return None, steps
        labels[u] = available[0]
    if len(set(labels)) != inst["colors"]:
        return None, steps
    return _answer_from_labels(labels, inst["colors"]), steps


def _random_greedy_restarts(
    inst: dict, rng: random.Random, restarts: int = 64
) -> tuple[object | None, int]:
    adjacency = _adjacency(inst)
    n = inst["n"]
    q = inst["colors"]
    steps = 0
    for _ in range(restarts):
        order = list(range(n))
        rng.shuffle(order)
        labels = [-1] * n
        failed = False
        for u in order:
            forbidden = {labels[v] for v in adjacency[u] if labels[v] >= 0}
            available = [color for color in range(q) if color not in forbidden]
            steps += len(adjacency[u]) + q
            if not available:
                failed = True
                break
            labels[u] = available[rng.randrange(len(available))]
        if not failed and len(set(labels)) == q:
            answer = _answer_from_labels(labels, q)
            if verify(inst, answer)[0]:
                return answer, steps
    return None, steps


def _min_conflicts_attack(
    inst: dict,
    rng: random.Random,
    restarts: int = 16,
    moves_per_vertex: int = 200,
) -> tuple[object | None, int]:
    """Walk-COL-style local repair with incremental conflict counts."""
    adjacency = _adjacency(inst)
    n = inst["n"]
    q = inst["colors"]
    operations = 0
    for _ in range(restarts):
        labels = [rng.randrange(q) for _ in range(n)]
        neighbor_counts = [[0] * q for _ in range(n)]
        for u in range(n):
            for v in adjacency[u]:
                neighbor_counts[u][labels[v]] += 1
                operations += 1
        conflicts = [neighbor_counts[u][labels[u]] for u in range(n)]
        bad_count = sum(value > 0 for value in conflicts)
        for _ in range(moves_per_vertex * n):
            if bad_count == 0:
                answer = _answer_from_labels(labels, q)
                if verify(inst, answer)[0]:
                    return answer, operations
            # Rejection sampling avoids materializing the conflict set on most moves.
            u = -1
            for _ in range(20):
                trial = rng.randrange(n)
                if conflicts[trial] > 0:
                    u = trial
                    break
            if u < 0:
                bad_vertices = [vertex for vertex, value in enumerate(conflicts) if value > 0]
                if not bad_vertices:
                    continue
                u = bad_vertices[rng.randrange(len(bad_vertices))]
            best = min(neighbor_counts[u])
            choices = [color for color, score in enumerate(neighbor_counts[u]) if score == best]
            # Small noise is the usual escape from local minima.
            new_color = rng.randrange(q) if rng.random() < 0.03 else choices[rng.randrange(len(choices))]
            old_color = labels[u]
            if new_color == old_color:
                continue
            old_u_conflict = conflicts[u]
            for v in adjacency[u]:
                old_v_conflict = conflicts[v]
                neighbor_counts[v][old_color] -= 1
                neighbor_counts[v][new_color] += 1
                conflicts[v] = neighbor_counts[v][labels[v]]
                if old_v_conflict == 0 < conflicts[v]:
                    bad_count += 1
                elif old_v_conflict > 0 == conflicts[v]:
                    bad_count -= 1
                operations += 2
            labels[u] = new_color
            conflicts[u] = neighbor_counts[u][new_color]
            if old_u_conflict == 0 < conflicts[u]:
                bad_count += 1
            elif old_u_conflict > 0 == conflicts[u]:
                bad_count -= 1
            operations += q
    return None, operations


def _orthonormalize(vectors: list[list[float]]) -> list[list[float]]:
    result: list[list[float]] = []
    for source in vectors:
        vector = list(source)
        mean = sum(vector) / len(vector)
        vector = [value - mean for value in vector]
        for previous in result:
            dot = sum(x * y for x, y in zip(vector, previous))
            vector = [x - dot * y for x, y in zip(vector, previous)]
        norm = math.sqrt(sum(value * value for value in vector))
        if norm < 1e-12:
            continue
        result.append([value / norm for value in vector])
    return result


def _spectral_attack(inst: dict, rng: random.Random) -> tuple[object | None, int]:
    """Bottom-adjacency subspace iteration followed by deterministic k-means."""
    adjacency = _adjacency(inst)
    n = inst["n"]
    q = inst["colors"]
    dimension = q - 1
    vectors = _orthonormalize(
        [[rng.uniform(-1.0, 1.0) for _ in range(n)] for _ in range(dimension)]
    )
    shift = max(len(row) for row in adjacency) + 1
    iterations = 60
    operations = 0
    for _ in range(iterations):
        transformed = []
        for vector in vectors:
            row = []
            for u in range(n):
                row.append(shift * vector[u] - sum(vector[v] for v in adjacency[u]))
                operations += len(adjacency[u]) + 2
            transformed.append(row)
        vectors = _orthonormalize(transformed)
        if len(vectors) < dimension:
            return None, operations
    points = [tuple(vector[u] for vector in vectors) for u in range(n)]
    centers = [points[0]]
    while len(centers) < q:
        centers.append(max(points, key=lambda point: min(
            sum((x - y) ** 2 for x, y in zip(point, center)) for center in centers
        )))
    labels = [0] * n
    for _ in range(30):
        labels = [
            min(range(q), key=lambda color: sum(
                (x - y) ** 2 for x, y in zip(point, centers[color])
            ))
            for point in points
        ]
        operations += n * q * dimension * 3
        if len(set(labels)) < q:
            return None, operations
        new_centers = []
        for color in range(q):
            members = [points[u] for u in range(n) if labels[u] == color]
            new_centers.append(tuple(sum(point[j] for point in members) / len(members)
                                     for j in range(dimension)))
        if new_centers == centers:
            break
        centers = new_centers
    return _answer_from_labels(labels, q), operations


def _nonbacktracking_spectral_attack(
    inst: dict, rng: random.Random, iterations: int = 80
) -> tuple[object | None, int]:
    """Cluster a bottom nonbacktracking subspace, then check the coloring."""
    adjacency = _adjacency(inst)
    n = inst["n"]
    q = inst["colors"]
    dimension = q - 1
    directed: list[tuple[int, int]] = []
    position: dict[tuple[int, int], int] = {}
    for u in range(n):
        for v in sorted(adjacency[u]):
            position[(u, v)] = len(directed)
            directed.append((u, v))
    reverse = [position[(v, u)] for u, v in directed]
    outgoing = [
        [position[(v, w)] for w in sorted(adjacency[v])]
        for _, v in directed
    ]
    size = len(directed)
    vectors = _orthonormalize(
        [[rng.uniform(-1.0, 1.0) for _ in range(size)] for _ in range(dimension)]
    )
    operations = 0
    transition_count = sum(len(row) for row in outgoing)
    for _ in range(iterations):
        transformed = []
        for vector in vectors:
            totals = [sum(vector[j] for j in row) for row in outgoing]
            # Apply -B: for directed edge u->v, omit the immediate v->u return.
            transformed.append(
                [-(totals[index] - vector[reverse[index]]) for index in range(size)]
            )
            operations += transition_count
        vectors = _orthonormalize(transformed)
        if len(vectors) < dimension:
            return None, operations

    points = []
    for vertex in range(n):
        incoming = [position[(u, vertex)] for u in adjacency[vertex]]
        points.append(tuple(sum(vector[index] for index in incoming) for vector in vectors))

    first = min(range(n), key=lambda index: (points[index][0], index))
    centers = [points[first]]
    while len(centers) < q:
        index = max(
            range(n),
            key=lambda i: min(
                sum((x - y) ** 2 for x, y in zip(points[i], center))
                for center in centers
            ),
        )
        centers.append(points[index])

    labels = [0] * n
    for _ in range(40):
        labels = [
            min(
                range(q),
                key=lambda color: sum(
                    (x - y) ** 2 for x, y in zip(point, centers[color])
                ),
            )
            for point in points
        ]
        operations += n * q * dimension * 3
        if len(set(labels)) < q:
            return None, operations
        new_centers = []
        for color in range(q):
            members = [points[u] for u in range(n) if labels[u] == color]
            new_centers.append(
                tuple(
                    sum(point[coordinate] for point in members) / len(members)
                    for coordinate in range(dimension)
                )
            )
        if new_centers == centers:
            break
        centers = new_centers
    return _answer_from_labels(labels, q), operations


def _dsatur_attack(inst: dict, node_cap: int = _DSATUR_NODE_CAP) -> tuple[object | None, int]:
    """Symmetry-normalized exact DSATUR/DPLL with a declared node budget."""
    adjacency = _adjacency(inst)
    n = inst["n"]
    q = inst["colors"]
    labels = [-1] * n
    neighbor_color_counts = [[0] * q for _ in range(n)]
    saturation_masks = [0] * n
    first, second = max(
        _underlying_edges(inst),
        key=lambda edge: (len(adjacency[edge[0]]) + len(adjacency[edge[1]]),
                          -edge[0], -edge[1]),
    )
    nodes = 0

    def assign(u: int, color: int) -> None:
        labels[u] = color
        bit = 1 << color
        for v in adjacency[u]:
            if labels[v] < 0:
                neighbor_color_counts[v][color] += 1
                saturation_masks[v] |= bit

    def unassign(u: int, color: int) -> None:
        labels[u] = -1
        bit = 1 << color
        for v in adjacency[u]:
            if labels[v] < 0:
                neighbor_color_counts[v][color] -= 1
                if neighbor_color_counts[v][color] == 0:
                    saturation_masks[v] &= ~bit

    # Every valid coloring gives different colors to this edge's endpoints.
    # Renaming those colors to 0 and 1 loses no solution and removes all q(q-1)
    # globally equivalent top-level branches.
    assign(first, 0)
    assign(second, 1)

    def visit(colored: int) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            return None
        if colored == n:
            return list(labels)
        uncolored = (u for u in range(n) if labels[u] < 0)
        u = max(
            uncolored,
            key=lambda x: (
                saturation_masks[x].bit_count(),
                len(adjacency[x]),
                -x,
            ),
        )
        forbidden = saturation_masks[u]
        available = [color for color in range(q) if not (forbidden >> color) & 1]
        available.sort(
            key=lambda color: sum(
                labels[v] < 0 and not (saturation_masks[v] >> color) & 1
                for v in adjacency[u]
            )
        )
        for color in available:
            assign(u, color)
            result = visit(colored + 1)
            if result is not None:
                return result
            unassign(u, color)
            if nodes > node_cap:
                return None
        return None

    result = visit(2)
    if result is None or len(set(result)) != q:
        return None, nodes
    return _answer_from_labels(result, q), nodes


def _relabel_instance(
    inst: dict,
    permutation: list[int],
    reverse_arcs: bool = False,
    reorder_arcs: bool = False,
    flip_alternate: bool = False,
) -> dict:
    """Carry an instance and its witness through a vertex permutation."""
    moved = dict(inst)
    arcs = []
    for arc_index, (u, v) in enumerate(inst["arcs"]):
        new_u = permutation[u - 1] + 1
        new_v = permutation[v - 1] + 1
        if reverse_arcs or (flip_alternate and arc_index % 2):
            new_u, new_v = new_v, new_u
        arcs.append([new_u, new_v])
    if reorder_arcs:
        arcs.reverse()
    moved["arcs"] = arcs
    labels = [0] * inst["n"]
    for old_vertex, label in enumerate(inst["answer"]):
        labels[permutation[old_vertex]] = label
    moved["answer"] = labels
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer)
    atoms = 0

    def visit(value: object) -> None:
        nonlocal atoms
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)
        else:
            atoms += 1

    visit(answer)
    return len(encoded), math.ceil(len(encoded) / 4), atoms


def selftest() -> dict:
    """Run all mandatory construction, attack, diversity, and size gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                round_trip = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if round_trip != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=123, **shipping_params)
    answer = shipping["answer"]
    dropped = list(answer[:-1])
    first_u, first_v = shipping["arcs"][0]
    u = first_u - 1
    v = first_v - 1
    same_as_v = next(
        vertex for vertex, label in enumerate(answer)
        if vertex != u and label == answer[v]
    )
    swapped = list(answer)
    swapped[u], swapped[same_as_v] = swapped[same_as_v], swapped[u]
    duplicate = list(answer) + [answer[0]]
    emptied: list[int] = []
    out_of_range = list(answer)
    out_of_range[0] = 2 * shipping["colors"]
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicate,
        "empty": emptied,
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not entry["accepted"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The classes below cover every vertex once.\n```json\n<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\nI checked each arc."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(shipping, parsed)[0],
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged partition") is None,
    }

    guess_rng = random.Random(0x190205467)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(shipping, guess_rng)
        guess_hits += int(verify(shipping, candidate)[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(shipping),
        "candidate_space_log2": round(math.log2(search_space(shipping)), 3),
        "sampling_prior": (
            "uniform over all onto vectors of n entries from the q allowed even "
            "labels; shape, range, coverage, and nonemptiness are enforced"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_orientation_imbalance",
        "greedy_largest_degree_first",
        "random_greedy_64_restarts",
        "min_conflicts_16x200n",
        "spectral_bottom_subspace_kmeans",
        "nonbacktracking_spectral_kmeans",
        "dsatur_dpll_symmetry_normalized_100000_nodes",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "operations": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    for seed in range(800, 800 + _ATTACK_SEEDS):
        inst = make_instance(seed=seed, **shipping_params)
        calls = [
            ("outlier_orientation_imbalance", lambda: _outlier_orientation_attack(inst)),
            ("greedy_largest_degree_first", lambda: _greedy_attack(inst)),
            ("random_greedy_64_restarts",
             lambda seed=seed: _random_greedy_restarts(inst, random.Random(seed ^ 0xA551), 64)),
            ("min_conflicts_16x200n",
             lambda seed=seed: _min_conflicts_attack(inst, random.Random(seed ^ 0xC0111C7))),
            ("spectral_bottom_subspace_kmeans",
             lambda seed=seed: _spectral_attack(inst, random.Random(seed ^ 0x5EEC7A1))),
            ("nonbacktracking_spectral_kmeans",
             lambda seed=seed: _nonbacktracking_spectral_attack(
                 inst, random.Random(seed ^ 0xBACC7A1)
             )),
            ("dsatur_dpll_symmetry_normalized_100000_nodes", lambda: _dsatur_attack(inst)),
        ]
        for name, call in calls:
            start = time.perf_counter()
            candidate, operations = call()
            elapsed = time.perf_counter() - start
            success = candidate is not None and verify(inst, candidate)[0]
            stat = attacks[name]
            stat["attempts"] += 1
            stat["successes"] += int(success)
            stat["operations"] += operations
            stat["wall_clock_sec"] += elapsed
    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": (
            "symmetry-normalized exact DSATUR/DPLL with propagation"
        ),
        "construction_aware_attack": "nonbacktracking spectral subspace plus k-means",
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    dsatur = attacks["dsatur_dpll_symmetry_normalized_100000_nodes"]
    report["G5_density_and_baseline"] = {
        "pass": guess_fraction < 1e-6 and dsatur["successes"] == 0,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": _G4_SAMPLES,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space_log2": round(math.log2(search_space(shipping)), 3),
        "demo_exact_valid_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "strongest_attack_nodes": dsatur["operations"],
        "strongest_attack_node_budget_per_seed": _DSATUR_NODE_CAP,
        "strongest_attack_wall_clock_sec": dsatur["wall_clock_sec"],
        "strongest_attack_attempts": dsatur["attempts"],
    }

    scale_start = time.perf_counter()
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=991, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    scale_wall = time.perf_counter() - scale_start
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_vertices": shipping["n"],
        "doubled_vertices": doubled["n"],
        "shipping_arcs": len(shipping["arcs"]),
        "doubled_arcs": len(doubled["arcs"]),
        "shipping_search_log2": round(math.log2(search_space(shipping)), 3),
        "doubled_search_log2": round(math.log2(search_space(doubled)), 3),
        "doubled_verify_reason": doubled_reason,
        "build_and_verify_wall_clock_sec": round(scale_wall, 6),
    }

    invariant_checks = 0
    real_transform_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(seed ^ 0xC4A0)
        permutation = list(range(inst["n"]))
        rng.shuffle(permutation)
        transforms = [
            _relabel_instance(inst, list(range(inst["n"])), False, True),
            _relabel_instance(inst, list(range(inst["n"])), True, False),
            _relabel_instance(
                inst, list(range(inst["n"])), False, False, flip_alternate=True
            ),
            _relabel_instance(inst, permutation, False, False),
            _relabel_instance(
                inst, permutation, False, True, flip_alternate=True
            ),
        ]
        for index, transformed in enumerate(transforms):
            invariant_checks += 1
            if canonical_key(transformed) != base_key:
                invariant_failures.append(f"seed {seed}, transform {index}: key changed")
            real_transform_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                invariant_failures.append(f"seed {seed}, transform {index}: witness failed")
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated_keys)) == len(unrelated_keys),
        "invariance_checks": invariant_checks,
        "real_transform_checks": real_transform_checks,
        "unrelated_instances": len(unrelated_keys),
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "failures": invariant_failures,
        "transformations": [
            "arc-list reorder",
            "global arc reversal",
            "independent reversal of alternating arcs",
            "vertex relabeling",
            "composed relabeling, per-arc reorientation, and reorder",
        ],
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    intended_operations = shipping["n"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "route_measurement": "one propagated class assignment per vertex after search",
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass", False) for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
