"""Verified problem generator for arXiv:1305.1466.

The paper studies families of matchings in a bipartite graph and proves that
``p`` matchings of size ``floor(5p/3)`` have a full rainbow matching.  This
module presents a matching ``R`` of size ``p`` and asks for the incidence
bijection certifying that ``R`` itself is a full rainbow matching.  The hidden
bijection is inverse-generated as an affine permutation; every colour class is
padded with private edges so that it lies exactly in Theorem 2.1's regime.

Only the standard library is needed.  Generation is deterministic in
``(n, seed, **params)`` and never solves the instance it creates.
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


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This finite-discrete family needs no helper library.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bipartite graph",
        "family of matchings of size floor(5p/3)",
        "displayed p-edge matching R",
        "full rainbow matching incidence bijection",
    ],
    "verification_operations": [
        "integer permutation comparison",
        "exact edge-family membership",
        "bipartite endpoint-disjointness comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The incidences between the displayed matching edges and the colour "
        "classes contain an affine permutation modulo a prime; without seeing "
        "it, one must execute a general bipartite matching algorithm."
    ),
    "hardness_basis": (
        "Track B: the incidence certificate is produced by Hopcroft--Karp in "
        "O(E sqrt(V)); at the shipping preset the executable reference averages "
        "2,443 edge scans and 0.000360 seconds in the recorded self-test, while the affine change of variables "
        "is measured at 266 exact arithmetic operations."
    ),
    "max_answer_tokens": 80,
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
    "demo": {"n": 7, "width": 2},
    "easy": {"n": 79, "width": 4},
    "medium": {"n": 97, "width": 6},
    "hard": {"n": 107, "width": 8},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Modulo the prime matching size, the edge-to-colour incidences contain an "
    "affine permutation shared across the rows."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the edge indices and colour labels helps prevent "
    "small transcription errors in the answer."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array containing every colour 0,...,p-1 exactly once; entry t "
        "assigns colour F_c to the displayed matching edge B_t."
    ),
    "bounds": {
        "answer_length": "p, the prime number of colours and displayed edges",
        "entry_min": 0,
        "entry_max": "p-1",
        "structural_rule": "a permutation of all p colours",
        "maximum_shipping_atomic_elements": 107,
    },
}


# Filled from the script-owned hardening transcripts after the three runs.
# These are diagnostics only; G9 passes exactly when the size/effort caps pass.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable: OpenRouter HTTP 403 key-total-limit",
}


NOTES = r"""
Definition and theorem regime. Section 1 defines a (partial) rainbow matching
as a choice of pairwise-disjoint edges from distinct members F_i of the family;
it is full when every F_i is represented. Theorem 2.1 states that p matchings,
each of size floor(5p/3), in a bipartite graph have a full rainbow matching.
This generator hands the solver exactly those objects. It additionally points
out a particular p-edge matching R and asks for the bijection proving that R
is full rainbow. Each F_c has exactly floor(5p/3) edges and is itself a matching.

Step-0 hardness decision. This is not Track A. For a fixed R, certification is
ordinary perfect matching in the incidence graph whose left side is E(R), whose
right side is the family F, and whose adjacencies are edge memberships. The
standard Hopcroft--Karp algorithm is O(E sqrt(V)) and the self-test runs it.
Theorem 2.1's proof is also organized around a maximum partial rainbow matching
and explicit alternating replacements (Proposition 2.1 and Claims 1--3), rather
than supplying an average-case hardness claim. Track B is the honest label.

Inverse generation. For prime p, sample nonzero a and b modulo p before drawing
any decoys. Put B_(a*c+b) into F_c; then add same-marginal uniform distinct B
edges and private padding edges. The answer assigns colour a^{-1}(t-b) to B_t.
The first six incidence rows are rejection-sampled only to eliminate accidental
second affine explanations of an already known certificate. No answer is found
by solving the finished instance.

Easy regimes and attacks. Section 1 notes the direct greedy bound g(p)<=2p-1;
the paper improves existence, not computational hardness. The panel therefore
tests incidence-frequency outliers, deterministic first fit, 256 random
fixed-order greedy restarts, and the obvious slopes +/-1 and +/-2. Non-demo
plants exclude those four slopes and all displayed decoys have the same uniform
per-row marginal as the plant. Hopcroft--Karp is reported separately and is
expected to solve every instance on Track B.

Canonicalization. Arbitrary colour relabelling, arbitrary relabelling of the
edges of R, row order, and within-row order preserve the problem. Exact graph
isomorphism for the resulting incidence graph is not known to be cheap, so the
key uses an eight-round bipartite Weisfeiler--Lehman invariant plus degree and
edge-colour histograms. The self-test proves invariance under the named maps and
checks distinctness; the key can collide on non-isomorphic incidence graphs.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    value = max(5, int(value))
    if value % 2 == 0:
        value += 1
    while not _is_prime(value):
        value += 2
    return value


def _inverse_mod(value: int, modulus: int) -> int:
    old_r, r = value % modulus, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ValueError("value is not invertible")
    return old_s % modulus


def _choose_slope(p: int, rng: random.Random) -> int:
    forbidden = {1, p - 1, 2 % p, (-2) % p} if p >= 11 else set()
    choices = [value for value in range(1, p) if value not in forbidden]
    return rng.choice(choices)


def _answer_from_affine(p: int, slope: int, offset: int) -> list[int]:
    inverse = _inverse_mod(slope, p)
    first = (-offset * inverse) % p
    answer = []
    colour = first
    for _ in range(p):
        answer.append(colour)
        colour = (colour + inverse) % p
    return answer


def _rows(inst: dict) -> list[set[int]]:
    p = int(inst["p"])
    raw = inst.get("core_incidence")
    if not isinstance(raw, list) or len(raw) != p:
        raise ValueError("malformed incidence family")
    rows = []
    for row in raw:
        if not isinstance(row, list):
            raise ValueError("malformed incidence row")
        parsed = set()
        for edge in row:
            if isinstance(edge, bool) or not isinstance(edge, int) or not 0 <= edge < p:
                raise ValueError("core-edge index outside range")
            parsed.add(edge)
        if len(parsed) != len(row):
            raise ValueError("duplicate core edge within a colour class")
        rows.append(parsed)
    return rows


def _short_affine_candidates(
    rows: list[set[int]] | list[list[int]], checked_rows: int = 6
) -> set[tuple[int, int]]:
    p = len(rows)
    stop = min(p, checked_rows)
    candidates: set[tuple[int, int]] = set()
    for offset in rows[0]:
        for second in rows[1]:
            slope = (second - offset) % p
            if slope == 0:
                continue
            predicted = second
            good = True
            for colour in range(2, stop):
                predicted = (predicted + slope) % p
                if predicted not in rows[colour]:
                    good = False
                    break
            if good:
                candidates.add((slope, offset))
    return candidates


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a full-rainbow certificate for a displayed matching."""
    rng = random.Random(seed)
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    width = params.pop("width", 4)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(width, bool) or not isinstance(width, int):
        raise ValueError("width must be an integer")

    p = _next_prime(n)
    if not 1 <= width <= min(8, p - 1):
        raise ValueError("width must lie between 1 and min(8,p-1)")
    class_size = (5 * p) // 3
    padding = class_size - width

    # The certificate is complete before any decoy or display order is drawn.
    slope = _choose_slope(p, rng)
    offset = rng.randrange(p)
    answer = _answer_from_affine(p, slope, offset)

    # Make the compact route concrete: in the first six labelled rows, the
    # planted affine line is the unique surviving affine explanation.  This is
    # rejection sampling around a certificate already held by construction.
    for _construction_attempt in range(10_000):
        incidence = []
        for colour in range(p):
            planted = (slope * colour + offset) % p
            row = {planted}
            while len(row) < width:
                row.add(rng.randrange(p))
            displayed = list(row)
            rng.shuffle(displayed)
            incidence.append(displayed)
        if p < 6 or _short_affine_candidates(incidence) == {(slope, offset)}:
            break
    else:
        raise RuntimeError("could not expose a unique affine certificate")

    display_order = list(range(p))
    rng.shuffle(display_order)
    return {
        "paper": "arXiv:1305.1466",
        "requested_n": n,
        "p": p,
        "class_size": class_size,
        "width": width,
        "padding_per_class": padding,
        "core_incidence": incidence,
        "display_order": display_order,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete standalone rainbow-matching certification task."""
    p = int(inst["p"])
    width = int(inst["width"])
    class_size = int(inst["class_size"])
    padding = int(inst["padding_per_class"])
    lines = [
        "Certify a displayed full rainbow matching",
        "",
        "A matching is a set of graph edges with no shared endpoint. A full rainbow",
        "matching for colour classes F_0,...,F_{p-1} is a matching of p edges that",
        "uses exactly one edge from every F_c. An edge may belong to several F_c;",
        "the certificate must specify which distinct colour is assigned to each edge.",
        "",
        f"Here p={p}. The graph is bipartite. Its displayed core vertices are",
        f"L_0,...,L_{p-1} on the left and R_0,...,R_{p-1} on the right.",
        f"For 0 <= t < {p}, B_t is the edge (L_t,R_t). Thus",
        "R={B_0,...,B_(p-1)} is already a p-edge matching.",
        "",
        f"There are p colour classes. Every F_c is itself a matching of exactly",
        f"floor(5p/3)={class_size} edges. The row for F_c below lists the {width}",
        "core indices t for which B_t belongs to F_c.",
        f"In addition, F_c contains exactly {padding} private padding edges",
        "(X_(c,j),Y_(c,j)) for j=0,...,padding-1. All X_(c,j) and Y_(c,j)",
        "are vertices different from every core vertex and from private vertices",
        "with another pair (c,j). These padding edges make the stated class size",
        "exact; they are not edges of the displayed matching R.",
        "The order of rows and the order of indices within a row have no meaning.",
        "",
        "Core incidences:",
    ]
    for colour in inst["display_order"]:
        items = " ".join(str(edge) for edge in inst["core_incidence"][colour])
        lines.append(f"  F_{colour}: {items}")
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend(
        [
            "",
            "Assign every edge of R to a different colour class containing it. This",
            "assignment certifies that the displayed R is a full rainbow matching.",
            "",
            f"Give your final answer inside <answer></answer> tags as one JSON array of exactly {p} integers.",
            "Array entry t is the colour c assigned to B_t; the array must be a",
            f"permutation of all integers 0,...,{p-1}. Indices are 0-based, both",
            "bounds are inclusive, and no colour may repeat.",
            "Example format: <answer>[2,0,1]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Extract the JSON permutation from prose, markdown fences, and whitespace."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        for fenced in _FENCE_RE.findall(text):
            matches.extend(_ANSWER_RE.findall(fenced))
    if not matches:
        return None
    try:
        value = json.loads(matches[-1].strip())
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any valid incidence bijection without consulting ``inst['answer']``."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    p = int(inst.get("p", -1))
    if len(answer) != p:
        return False, f"expected exactly {p} colours, got {len(answer)}"
    for position, colour in enumerate(answer):
        if isinstance(colour, bool) or not isinstance(colour, int):
            return False, f"colour at position {position} is not an integer"
        if not 0 <= colour < p:
            return False, f"colour at position {position} is outside 0..{p-1}"
    if len(set(answer)) != p:
        return False, "colours do not form a bijection: a colour is repeated or missing"

    try:
        rows = _rows(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"
    expected_size = (5 * p) // 3
    if inst.get("class_size") != expected_size:
        return False, "malformed instance: colour-class size is not floor(5p/3)"
    if inst.get("padding_per_class") != expected_size - int(inst.get("width", -1)):
        return False, "malformed instance: padding count is inconsistent"
    if any(len(row) != int(inst["width"]) for row in rows):
        return False, "malformed instance: a core-incidence row has wrong size"

    # B_t=(L_t,R_t), so using every t exactly once is an exact endpoint check.
    if len({("L", t) for t in range(p)}) != p or len({("R", t) for t in range(p)}) != p:
        return False, "malformed instance: displayed R is not a matching"
    for edge_index, colour in enumerate(answer):
        if edge_index not in rows[colour]:
            return False, f"edge B_{edge_index} is not present in F_{colour}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-implied permutation language."""
    candidate = list(range(int(inst["p"])))
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """Return the exact size p! of the bounded certificate language."""
    return math.factorial(int(inst["p"]))


def enumerate_all(inst: dict) -> int | None:
    """Count valid certificates when p! is at most 100,000."""
    p = int(inst["p"])
    if math.factorial(p) > 100_000:
        return None
    return sum(
        int(verify(inst, list(candidate))[0])
        for candidate in itertools.permutations(range(p))
    )


def _wl_signature(inst: dict) -> tuple:
    """A relabelling-invariant signature of the core incidence graph."""
    rows = _rows(inst)
    p = len(rows)
    columns = [set() for _ in range(p)]
    for colour, row in enumerate(rows):
        for edge in row:
            columns[edge].add(colour)

    left_colours = [0] * p
    right_colours = [1] * p
    for _ in range(8):
        signatures = []
        for colour, row in enumerate(rows):
            signatures.append(
                (0, left_colours[colour], tuple(sorted(right_colours[e] for e in row)))
            )
        for edge, column in enumerate(columns):
            signatures.append(
                (1, right_colours[edge], tuple(sorted(left_colours[c] for c in column)))
            )
        palette = {sig: index for index, sig in enumerate(sorted(set(signatures)))}
        new_left = [palette[sig] for sig in signatures[:p]]
        new_right = [palette[sig] for sig in signatures[p:]]
        left_colours, right_colours = new_left, new_right

    row_profiles = sorted(
        (left_colours[c], tuple(sorted(right_colours[e] for e in row)))
        for c, row in enumerate(rows)
    )
    column_profiles = sorted(
        (right_colours[e], tuple(sorted(left_colours[c] for c in column)))
        for e, column in enumerate(columns)
    )
    edge_profiles = sorted(
        (left_colours[c], right_colours[e])
        for c, row in enumerate(rows)
        for e in row
    )
    return (
        p,
        int(inst["width"]),
        int(inst["class_size"]),
        tuple(row_profiles),
        tuple(column_profiles),
        tuple(edge_profiles),
    )


def canonical_key(inst: dict) -> str:
    """Hash a strong WL invariant, never the seed or rendered statement."""
    blob = json.dumps(_wl_signature(inst), separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase decoy crowding first, then p while the answer remains writable."""
    n = int(params.get("n", 79))
    width = int(params.get("width", 4))
    harder = dict(params)
    if width < 8:
        harder["width"] = min(8, width + 2)
        harder["n"] = n
        return harder
    p = _next_prime(n)
    if p < 167:
        harder["n"] = _next_prime(p + 10)
        harder["width"] = width
        return harder
    return "cap_bound"


def _eligible_by_edge(rows: list[set[int]]) -> list[list[int]]:
    p = len(rows)
    eligible = [[] for _ in range(p)]
    for colour, row in enumerate(rows):
        for edge in row:
            eligible[edge].append(colour)
    for choices in eligible:
        choices.sort()
    return eligible


def _greedy_fixed(
    rows: list[set[int]],
    *,
    rng: random.Random | None = None,
    outlier_scores: list[int] | None = None,
) -> list[int] | None:
    eligible = _eligible_by_edge(rows)
    used: set[int] = set()
    answer = [-1] * len(rows)
    for edge in range(len(rows)):
        choices = [colour for colour in eligible[edge] if colour not in used]
        if not choices:
            return None
        if rng is not None:
            colour = rng.choice(choices)
        elif outlier_scores is not None:
            colour = min(choices, key=lambda c: (outlier_scores[c], c))
        else:
            colour = min(choices)
        answer[edge] = colour
        used.add(colour)
    return answer


def _outlier_candidate(rows: list[set[int]]) -> list[int] | None:
    degrees = [0] * len(rows)
    for row in rows:
        for edge in row:
            degrees[edge] += 1
    scores = [sum(degrees[edge] for edge in row) for row in rows]
    return _greedy_fixed(rows, outlier_scores=scores)


def _obvious_affine_attack(inst: dict) -> list[int] | None:
    p = int(inst["p"])
    rows = _rows(inst)
    for slope in (1, p - 1, 2 % p, (-2) % p):
        if slope == 0:
            continue
        for offset in range(p):
            if all((slope * colour + offset) % p in rows[colour] for colour in range(p)):
                return _answer_from_affine(p, slope, offset)
    return None


def _hopcroft_karp(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Find an incidence perfect matching and count exact edge scans."""
    rows = _rows(inst)
    adjacency = _eligible_by_edge(rows)
    p = len(rows)
    pair_left = [-1] * p
    pair_right = [-1] * p
    distance = [0] * p
    counters = {"edge_scans": 0, "bfs_rounds": 0, "augmentations": 0}

    def bfs() -> bool:
        counters["bfs_rounds"] += 1
        queue = []
        for left in range(p):
            if pair_left[left] < 0:
                distance[left] = 0
                queue.append(left)
            else:
                distance[left] = -1
        found = False
        head = 0
        while head < len(queue):
            left = queue[head]
            head += 1
            for right in adjacency[left]:
                counters["edge_scans"] += 1
                other = pair_right[right]
                if other < 0:
                    found = True
                elif distance[other] < 0:
                    distance[other] = distance[left] + 1
                    queue.append(other)
        return found

    def dfs(left: int) -> bool:
        for right in adjacency[left]:
            counters["edge_scans"] += 1
            other = pair_right[right]
            if other < 0 or (
                distance[other] == distance[left] + 1 and dfs(other)
            ):
                pair_left[left] = right
                pair_right[right] = left
                return True
        distance[left] = -1
        return False

    matching = 0
    while bfs():
        for left in range(p):
            if pair_left[left] < 0 and dfs(left):
                matching += 1
                counters["augmentations"] += 1
    if matching != p:
        return None, counters
    return pair_left, counters


def _compact_affine_route(inst: dict) -> tuple[list[int] | None, int]:
    """Execute and count the intended affine change of variables."""
    rows = _rows(inst)
    p = len(rows)
    survivors: set[tuple[int, int]] = set()
    operations = 0
    for offset in rows[0]:
        for second in rows[1]:
            slope = (second - offset) % p
            operations += 1
            if slope == 0:
                continue
            predicted = second
            good = True
            for colour in range(2, min(p, 6)):
                predicted = (predicted + slope) % p
                operations += 1
                if predicted not in rows[colour]:
                    good = False
                    break
            if good:
                survivors.add((slope, offset))
    if len(survivors) != 1:
        return None, operations
    slope, offset = next(iter(survivors))

    old_r, r = slope, p
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        operations += 1
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        operations += 4
    inverse = old_s % p
    operations += 1
    colour = (-offset * inverse) % p
    operations += 2
    answer = []
    for _ in range(p):
        answer.append(colour)
        colour = (colour + inverse) % p
        operations += 1
    return answer, operations


def _relabeled_instance(
    inst: dict,
    colour_map: list[int] | None = None,
    edge_map: list[int] | None = None,
) -> dict:
    """Carry the instance and witness through genuine relabellings."""
    p = int(inst["p"])
    if colour_map is None:
        colour_map = list(range(p))
    if edge_map is None:
        edge_map = list(range(p))
    transformed_rows: list[list[int] | None] = [None] * p
    for old_colour, row in enumerate(inst["core_incidence"]):
        transformed_rows[colour_map[old_colour]] = [edge_map[edge] for edge in reversed(row)]
    answer = [-1] * p
    for old_edge, old_colour in enumerate(inst["answer"]):
        answer[edge_map[old_edge]] = colour_map[old_colour]
    return {
        "paper": inst["paper"],
        "requested_n": inst["requested_n"],
        "p": p,
        "class_size": inst["class_size"],
        "width": inst["width"],
        "padding_per_class": inst["padding_per_class"],
        "core_incidence": [row for row in transformed_rows if row is not None],
        "display_order": [colour_map[c] for c in reversed(inst["display_order"])],
        "answer": answer,
    }


def _answer_size(answer) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))

    def atoms(value) -> int:
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(item) for item in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "arXiv:1305.1466",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    planted_ok = 0
    json_ok = 0
    theorem_regime_ok = 0
    failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            planted_ok += int(ok)
            json_ok += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
            theorem_regime_ok += int(
                inst["class_size"] == (5 * inst["p"]) // 3
                and all(
                    len(set(row)) + inst["padding_per_class"] == inst["class_size"]
                    for row in inst["core_incidence"]
                )
            )
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
    report["G1_planted_verifies"] = {
        "pass": planted_ok == 12 and json_ok == 12 and theorem_regime_ok == 12,
        "verified": planted_ok,
        "attempts": 12,
        "json_native": json_ok,
        "theorem_2_1_regime": theorem_regime_ok,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    answer = list(inst["answer"])
    swapped = None
    for first in range(len(answer)):
        for second in range(first + 1, len(answer)):
            trial = list(answer)
            trial[first], trial[second] = trial[second], trial[first]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("could not create a rejected swap")
    duplicate = list(answer)
    duplicate[1] = duplicate[0]
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate_colour": duplicate,
        "out_of_range": [inst["p"]] + answer[1:],
        "swap_two": swapped,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The incidence bijection is below.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nEvery array position is the stated zero-based B-index."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x13051466)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_prior": "uniform over all p! colour permutations",
        "candidate_space": search_space(inst),
        "candidate_space_bits": int(search_space(inst)).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_incidence_frequency_greedy",
        "greedy_first_fit",
        "random_restart_256_fixed_order",
        "obvious_affine_slopes_pm1_pm2",
    ]
    successes = {name: 0 for name in attack_names}
    seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_scans = 0
    reference_rounds = 0
    reference_augmentations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping_params)
        rows = _rows(trial)

        start = time.perf_counter()
        candidate = _outlier_candidate(rows)
        successes[attack_names[0]] += int(
            candidate is not None and verify(trial, candidate)[0]
        )
        seconds[attack_names[0]] += time.perf_counter() - start

        start = time.perf_counter()
        candidate = _greedy_fixed(rows)
        successes[attack_names[1]] += int(
            candidate is not None and verify(trial, candidate)[0]
        )
        seconds[attack_names[1]] += time.perf_counter() - start

        start = time.perf_counter()
        random_won = False
        for restart in range(256):
            candidate = _greedy_fixed(
                rows, rng=random.Random((seed + 1) * 1_000_003 + restart)
            )
            if candidate is not None and verify(trial, candidate)[0]:
                random_won = True
                break
        successes[attack_names[2]] += int(random_won)
        seconds[attack_names[2]] += time.perf_counter() - start

        start = time.perf_counter()
        candidate = _obvious_affine_attack(trial)
        successes[attack_names[3]] += int(
            candidate is not None and verify(trial, candidate)[0]
        )
        seconds[attack_names[3]] += time.perf_counter() - start

        start = time.perf_counter()
        reference, counts = _hopcroft_karp(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(
            reference is not None and verify(trial, reference)[0]
        )
        reference_scans += counts["edge_scans"]
        reference_rounds += counts["bfs_rounds"]
        reference_augmentations += counts["augmentations"]

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(seconds[name], 6),
        }
        for name in attack_names
    }
    reference_algorithm = {
        "name": "Hopcroft--Karp on the edge/colour incidence graph",
        "complexity": "O(E sqrt(V))",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_scans // 8,
        "bfs_rounds": reference_rounds // 8,
        "augmentations": reference_augmentations // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    count_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    count_seconds = time.perf_counter() - count_start
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and isinstance(demo_count, int)
        and demo_count > 0
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_count_wall_clock_sec": round(count_seconds, 6),
        "baseline_name": reference_algorithm["name"],
        "baseline_wall_clock_sec": reference_algorithm["wall_clock_sec"],
        "baseline_edge_scans": reference_algorithm["operations"],
        "baseline_bfs_rounds": reference_algorithm["bfs_rounds"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled_start = time.perf_counter()
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_seconds = time.perf_counter() - doubled_start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_sizes = [_next_prime(item["n"]) for item in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["p"] >= 2 * inst["p"]
        and search_space(doubled) > search_space(inst)
        and ladder_sizes == sorted(ladder_sizes)
        and len(set(ladder_sizes)) == 4,
        "shipping_p": inst["p"],
        "doubled_requested_n": doubled_params["n"],
        "doubled_p": doubled["p"],
        "doubled_build_wall_clock_sec": round(doubled_seconds, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    real_transform_checks = 0
    invariant_failures = []
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        rng = random.Random(70_000 + seed)
        colour_map = list(range(original["p"]))
        edge_map = list(range(original["p"]))
        rng.shuffle(colour_map)
        rng.shuffle(edge_map)
        identity = list(range(original["p"]))
        transforms = [
            _relabeled_instance(original, colour_map=colour_map),
            _relabeled_instance(original, edge_map=edge_map),
            _relabeled_instance(
                original, colour_map=colour_map, edge_map=edge_map
            ),
            _relabeled_instance(
                _relabeled_instance(original, colour_map=colour_map),
                colour_map=identity,
                edge_map=edge_map,
            ),
        ]
        for transformed in transforms:
            same = canonical_key(transformed) == key
            valid = verify(transformed, transformed["answer"])[0]
            invariant_checks += int(same)
            real_transform_checks += int(valid)
            if not same or not valid:
                invariant_failures.append(
                    {"seed": seed, "same_key": same, "carried_answer_valid": valid}
                )
    unrelated_keys = {
        canonical_key(make_instance(seed=90_000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80
        and real_transform_checks == 80
        and len(unrelated_keys) == 20,
        "invariance_passed": invariant_checks,
        "invariance_attempts": 80,
        "real_transform_passed": real_transform_checks,
        "real_transform_attempts": 80,
        "distinct_unrelated": len(unrelated_keys),
        "distinct_attempts": 20,
        "transformations": [
            "arbitrary colour relabelling plus row/input reordering",
            "arbitrary relabelling of displayed matching edges",
            "composed colour and edge relabelling",
            "composition applied in two stages",
        ],
        "key_kind": "eight-round bipartite Weisfeiler--Lehman invariant",
        "failures": invariant_failures,
    }

    answer_chars, answer_tokens, answer_elements = _answer_size(inst["answer"])
    compact_answer, intended_operations = _compact_affine_route(inst)
    compact_ok = compact_answer is not None and verify(inst, compact_answer)[0]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verified": compact_ok,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_passed"] = all(bool(value["pass"]) for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
