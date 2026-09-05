"""Verified problem generator for arXiv:1905.00305.

The paper reduces Monotone Exact SAT to 2-CNCF-Coloring-VC-Extension in
Section 4.4.  This module inverse-generates structured exact-one instances,
builds the precoloured graph from that reduction, and asks for a compact
colouring extension: the IDs of the variables whose occurrence vertices are
blue.  ``verify`` expands this representation and checks every closed
neighbourhood of the graph exactly.

The generated exact covers are complete translation orbits among incomplete
ones.  A general exact-cover search remains expensive by hand, but a full
translation-class scan is polynomial.  The family is therefore explicitly
Track B, not an average-case hardness claim.

Only the Python standard library is required.  Importing this module performs
no file I/O, network access, or printing.
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
from collections import Counter, defaultdict
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - no helper is needed by this family
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "precoloured graph",
        "closed neighbourhoods",
        "compressed 2-CNCF colouring extension",
    ],
    "verification_operations": [
        "exact incidence expansion",
        "closed-neighbourhood colour multiplicity count",
        "integer equality comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4.4, Theorem 4.5: Monotone Exact SAT to "
        "2-CNCF-Coloring-VC-Extension"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Sets in one complete vertical-translation orbit partition the cyclic "
        "columns; without recognizing the orbit, a solver faces the exact-cover "
        "incidence system."
    ),
    "hardness_basis": (
        "Track B: the generated subfamily has a full translation-signature scan "
        "running in O(Nw), measured at the shipping preset as 1,084 modular "
        "subtractions and under 0.001 seconds; the domain-standard Algorithm X "
        "is exponential in general and averaged about 76 million row-element "
        "compatibility probes in the local eight-seed panel, while "
        "the compact first-difference route uses 271 modular subtractions, below "
        "the no-tool cap but not an obvious row-by-row exact-cover procedure."
    ),
    "max_answer_tokens": 19,
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
        "A strictly increasing JSON array of exactly n distinct 1-based set "
        "IDs from 1 through N; it represents the blue occurrence classes in "
        "the compressed 2-CNCF colouring extension."
    ),
    "bounds": {
        "selected_sets": "n",
        "minimum_set_id": 1,
        "maximum_set_id": "N = n + decoy_orbits*(n-1)",
        "distinct": True,
        "canonical_order": "strictly increasing",
    },
}

DIFFICULTY = {
    "demo": {"n": 3, "decoy_orbits": 1, "width": 2},
    "easy": {"n": 13, "decoy_orbits": 8, "width": 6},
    "medium": {"n": 17, "decoy_orbits": 11, "width": 6},
    "hard": {"n": 19, "decoy_orbits": 14, "width": 5},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Coordinate differences modulo n are invariant under a vertical translation "
    "of a set."
)
PLACEBO_HINT = (
    "Coordinate entries and set identifiers should be copied with consistent "
    "ordering and indexing."
)

# Populated after the script-owned oracle runs.  Zero-attempt placeholders are
# diagnostic only; G9(a,b) no longer gate submission.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and reduction.  Definitions 1 and 2 distinguish open- from
closed-neighbourhood conflict-free colourings.  This family uses Definition 2.
Section 4.4 defines q-CNCF-Coloring-VC-Extension, and Theorem 4.5 reduces
Monotone Exact SAT to the q=2 case.  Its forward proof colours every occurrence
vertex w_(i,j) blue exactly when variable x_j is true.  Its reverse proof shows
that the occurrence vertices for a variable have one colour and that every
clause has exactly one blue occurrence.  The returned list is therefore an
exact symbolic compression of a full colouring, not merely a claimed SAT
assignment; verify expands it and scans the graph's closed neighbourhoods.

Source correction.  The construction bullet in the arXiv v1 text says to join
clause vertices u_i to R_2, but the very next neighbourhood verification uses
N[R_1]={R_1,B_1} union {u_i}, N[R_2]={R_2} union {v_j}, and
N[u_i]={u_i,R_1} union occurrences.  Those three displayed checks and Figure 6
require the edge u_i--R_1.  This module follows the proof and figure; using the
bullet literally makes R_2's closed neighbourhood invalid on every nontrivial
instance.  README.md records the discrepancy.

Step 0 and track choice.  Theorem 4.5 establishes NP-hardness of the unrestricted
extension problem.  Theorem 4.4 simultaneously identifies an easy direction: a
kernel with O(k^2) vertices and edges exists for q=2 when parameterized by the
given vertex-cover size, and Theorem 3.1 gives a (2q^2)^t n^O(1) treewidth DP.
Neither makes a small parameter here: the paper reduction's precoloured vertex
cover grows with all elements and candidate sets.  Nevertheless, this generated
distribution has its own efficient certificate algorithm.  Full normalized
translation signatures cost N*(width-1) modular subtractions, so a Track-A claim
would be false.  Track B reports that method, the domain-standard Algorithm X,
and their measured shipping costs.  The compact route only needs each row's
first coordinate difference; construction makes those differences distinct
between orbit families, reducing the exact arithmetic to N operations.

Inverse generation.  The generator first chooses a random base vector over
Z_n and takes all n vertical translations; these n sets are the certificate and
partition all n*width elements.  Each decoy family starts from an independently
distributed base vector but omits one uniformly random translation.  Candidate
rows are shuffled.  Thus every individual planted or decoy set has the same
marginal distribution and size; only the collective completeness of an orbit
distinguishes the certificate.  No search is used to obtain the answer.

Attacks.  Equal row sizes remove a size outlier.  The degree-score attack ranks
rows using only element frequencies; a no-backtracking MRV greedy enforces
disjointness; 256 random restarts sample maximal disjoint packings; and the
in-context first-row guess follows the displayed ordering.  All fail on eight
shipping seeds.  Algorithm X is run as the domain-standard reference and is
expected to succeed on Track B.  A full translation-signature scan also succeeds
and is the efficient algorithm disclosed by the hardness basis.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 200_000
_ALGORITHM_X_NODE_CAP = 600_000


def _validate_params(n: int, decoy_orbits: int, width: int) -> None:
    for name, value in (("n", n), ("decoy_orbits", decoy_orbits),
                        ("width", width)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 3:
        raise ValueError("n must be at least 3")
    if not 1 <= decoy_orbits < n:
        raise ValueError("decoy_orbits must lie in [1,n-1]")
    if width < 2:
        raise ValueError("width must be at least 2")


def _n_candidates(inst: dict) -> int:
    return len(inst["sets"])


def _covers(inst: dict, selected_zero_based: list[int]) -> bool:
    """Fast exact-cover predicate, equivalent to the graph scan in verify."""

    universe = inst["n"] * inst["width"]
    counts = [0] * universe
    for row_index in selected_zero_based:
        for element in inst["sets"][row_index]:
            counts[element] += 1
            if counts[element] > 1:
                return False
    return all(value == 1 for value in counts)


def make_instance(n: int, seed: int = 0, decoy_orbits: int = 1,
                  width: int = 2, **params: Any) -> dict:
    """Inverse-generate a paper-licensed 2-CNCF extension instance.

    ``n`` is both the cyclic group order and the number of selected sets.  The
    certificate is chosen first as a complete translation orbit.  Decoy orbit
    families omit one translation each, so no solving is involved.
    """

    if params:
        raise TypeError(f"unexpected parameters: {sorted(params)}")
    _validate_params(n, decoy_orbits, width)
    rng = random.Random(seed)

    # The first differences are sampled without replacement.  Consequently a
    # one-coordinate normalization already separates orbit families, although
    # a reference solver need not rely on that generator-specific shortcut.
    first_differences = list(range(n))
    rng.shuffle(first_differences)
    bases: list[tuple[int, ...]] = []
    for orbit in range(decoy_orbits + 1):
        first = rng.randrange(n)
        base = [first, (first + first_differences[orbit]) % n]
        base.extend(rng.randrange(n) for _ in range(width - 2))
        bases.append(tuple(base))

    rows: list[tuple[tuple[int, ...], int]] = []
    for orbit, base in enumerate(bases):
        shifts = list(range(n))
        if orbit:
            shifts.remove(rng.randrange(n))
        for shift in shifts:
            elements = tuple(
                column * n + (base[column] + shift) % n
                for column in range(width)
            )
            rows.append((elements, orbit))

    rng.shuffle(rows)
    sets = [list(elements) for elements, _ in rows]
    answer = sorted(index + 1 for index, (_, orbit) in enumerate(rows)
                    if orbit == 0)
    inst = {
        "problem": "compressed 2-CNCF colouring extension",
        "n": n,
        "width": width,
        "decoy_orbits": decoy_orbits,
        "universe_size": n * width,
        "sets": sets,
        "answer": answer,
    }
    # This assertion checks construction, not a search for the answer.
    if len(answer) != n or not _covers(inst, [x - 1 for x in answer]):
        raise AssertionError("translation orbit failed to form the planted cover")
    return inst


def render(inst: dict) -> str:
    """Render the complete self-contained problem and its answer contract."""

    n = inst["n"]
    width = inst["width"]
    lines = [
        "Find a compressed 2-colour closed-neighbourhood conflict-free colouring.",
        "",
        "A closed neighbourhood N[v] consists of v and every vertex adjacent to v.",
        "A red/blue colouring is conflict-free on closed neighbourhoods (2-CNCF)",
        "when, for every vertex v, at least one of the two colours occurs exactly",
        "once in N[v].  Adjacent vertices are allowed to have the same colour.",
        "",
        "The graph is specified compactly from the incidence table below.",
        f"Elements are pairs (c,a), with columns c=0,...,{width - 1} and values",
        f"a=0,...,{n - 1}.  There is one candidate set V_j for each numbered row.",
        "The row lists the value a in each column c, so it contains exactly the",
        "elements (0,a_0),(1,a_1),... in that order.",
        "",
        "Graph vertices: R1, R2, B1; one U_(c,a) per element; one V_j per set;",
        "and one W_(c,a),j whenever row j contains element (c,a).",
        "Precolour R1, R2, and every U_(c,a) red.  Precolour B1 and every V_j blue.",
        "Edges are exactly R1--B1, R1--U_(c,a) for every element, R2--V_j for",
        "every set, and W_(c,a),j--U_(c,a) plus W_(c,a),j--V_j for every incidence.",
        "There are no other edges.",
        "",
        f"Your answer is a list S of exactly {n} set IDs.  It represents the full",
        "extension that colours W_(c,a),j blue iff j is in S, and red otherwise.",
        "Find S for which the resulting full red/blue colouring is 2-CNCF.",
        "Set IDs are 1-based, repetitions are forbidden, order has no mathematical",
        "meaning, and the submitted list must be in strictly increasing order.",
        "",
        f"n = {n}; number of columns = {width}; number of sets = {_n_candidates(inst)}",
        "Incidence rows (set_id: a_0 a_1 ...):",
    ]
    for set_id, row in enumerate(inst["sets"], 1):
        values = [0] * width
        for element in row:
            column, value = divmod(element, n)
            if 0 <= column < width:
                values[column] = value
        lines.append(f"{set_id}: " + " ".join(map(str, values)))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON array",
        f"of exactly {n} increasing set IDs.",
        "Format example only (shown with three IDs): <answer>[1, 4, 9]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: Any) -> object | None:
    """Extract a JSON list from answer tags; malformed output returns None."""

    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _scan_paper_graph(inst: dict, selected: set[int]) -> tuple[bool, str]:
    """Expand Theorem 4.5's graph and scan every closed neighbourhood."""

    n_sets = _n_candidates(inst)
    universe = inst["universe_size"]
    # Integer vertex IDs keep the checker exact and inexpensive.
    r1, r2, b1 = 0, 1, 2
    u_start = 3
    v_start = u_start + universe
    w_start = v_start + n_sets
    incidence_count = sum(len(row) for row in inst["sets"])
    adjacency = [set() for _ in range(w_start + incidence_count)]
    colours = [0] * len(adjacency)  # 0=red, 1=blue

    def edge(a: int, b: int) -> None:
        adjacency[a].add(b)
        adjacency[b].add(a)

    colours[b1] = 1
    edge(r1, b1)
    for element in range(universe):
        edge(r1, u_start + element)
    for row_index in range(n_sets):
        colours[v_start + row_index] = 1
        edge(r2, v_start + row_index)

    w = w_start
    for row_index, row in enumerate(inst["sets"]):
        selected_colour = 1 if row_index + 1 in selected else 0
        for element in row:
            colours[w] = selected_colour
            edge(w, u_start + element)
            edge(w, v_start + row_index)
            w += 1

    for vertex, neighbors in enumerate(adjacency):
        red = int(colours[vertex] == 0)
        blue = int(colours[vertex] == 1)
        for neighbor in neighbors:
            if colours[neighbor] == 0:
                red += 1
            else:
                blue += 1
        if red != 1 and blue != 1:
            return False, (
                f"closed neighborhood of expanded vertex {vertex} has "
                f"red={red}, blue={blue}; neither colour is unique"
            )
    return True, "ok"


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Accept any valid bounded compressed colouring; never inspect answer key."""

    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != inst["n"]:
        return False, f"expected exactly {inst['n']} set IDs"
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in answer):
        return False, "every set ID must be an integer"
    if len(set(answer)) != len(answer):
        return False, "set IDs must be distinct"
    if any(value < 1 or value > _n_candidates(inst) for value in answer):
        return False, "set ID out of range"
    if answer != sorted(answer):
        return False, "set IDs must be in strictly increasing order"
    return _scan_paper_graph(inst, set(answer))


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated n-subset language, already sorted."""

    return sorted(rng.sample(range(1, _n_candidates(inst) + 1), inst["n"]))


def search_space(inst: dict) -> int | None:
    """Count the exact bounded language sampled by random_candidate."""

    return math.comb(_n_candidates(inst), inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count valid answers exactly when the bounded language is small."""

    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.combinations(range(_n_candidates(inst)), inst["n"]):
        count += int(_covers(inst, list(candidate)))
    return count


def _canonical_wl_payload(inst: dict) -> dict:
    """A strong cheap isomorphism invariant of the incidence bipartite graph."""

    rows = [set(row) for row in inst["sets"]]
    universe = inst["universe_size"]
    n_sets = len(rows)
    neighbors: list[list[int]] = [[] for _ in range(n_sets + universe)]
    for row_index, row in enumerate(rows):
        for element in row:
            neighbors[row_index].append(n_sets + element)
            neighbors[n_sets + element].append(row_index)

    signatures = [
        (0 if vertex < n_sets else 1, len(neighbors[vertex]))
        for vertex in range(len(neighbors))
    ]
    palette = {signature: index for index, signature in
               enumerate(sorted(set(signatures)))}
    colours = [palette[signature] for signature in signatures]
    for _ in range(16):
        refined = [
            (0 if vertex < n_sets else 1, colours[vertex],
             tuple(sorted(colours[x] for x in neighbors[vertex])))
            for vertex in range(len(neighbors))
        ]
        palette2 = {signature: index for index, signature in
                    enumerate(sorted(set(refined)))}
        new_colours = [palette2[signature] for signature in refined]
        if new_colours == colours:
            break
        colours = new_colours

    colour_hist = sorted(Counter(
        (0 if vertex < n_sets else 1, colours[vertex], len(neighbors[vertex]))
        for vertex in range(len(neighbors))
    ).items())
    intersection_hist = Counter()
    row_profiles = []
    for i, row in enumerate(rows):
        profile = []
        for j in range(n_sets):
            if i != j:
                size = len(row & rows[j])
                profile.append(size)
                intersection_hist[size] += int(i < j)
        row_profiles.append(tuple(sorted(Counter(profile).items())))
    return {
        "parts": [n_sets, universe],
        "colour_hist": colour_hist,
        "intersection_hist": sorted(intersection_hist.items()),
        "row_profiles": sorted(Counter(row_profiles).items()),
    }


def canonical_key(inst: dict) -> str:
    """Key by incidence invariants, never by seed, labels, or rendering."""

    payload = json.dumps(_canonical_wl_payload(inst), separators=(",", ":"),
                         sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Make the orbit cover harder while keeping its answer concise."""

    current = {key: value for key, value in params.items() if key != "_preset"}
    n = int(current["n"])
    width = int(current["width"])
    decoys = int(current["decoy_orbits"])
    # A narrower cover empirically forces substantially more Algorithm-X
    # backtracking at the same answer length and number of candidate rows.
    if width > 4:
        return {"n": n, "decoy_orbits": decoys, "width": width - 1}

    # Then grow the selected orbit while keeping the row count, and therefore
    # the compact first-difference route, below the 300-operation cap.
    next_n = n + 1
    while next_n <= 257:
        trial_decoys = min(next_n - 1, (295 - next_n) // (next_n - 1))
        if trial_decoys >= 1:
            return {"n": next_n, "decoy_orbits": trial_decoys, "width": 4}
        next_n += 1
    return "cap_bound"


def _reference_translation_scan(inst: dict) -> tuple[list[int] | None, dict]:
    """Efficient full-signature algorithm disclosed for Track B."""

    start = time.perf_counter()
    n = inst["n"]
    width = inst["width"]
    groups: dict[tuple[int, ...], list[int]] = defaultdict(list)
    operations = 0
    for set_id, row in enumerate(inst["sets"], 1):
        values = [0] * width
        for element in row:
            column, value = divmod(element, n)
            values[column] = value
        signature = []
        for column in range(1, width):
            signature.append((values[column] - values[0]) % n)
            operations += 1
        groups[tuple(signature)].append(set_id)
    answer = next((sorted(ids) for ids in groups.values() if len(ids) == n), None)
    return answer, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _algorithm_x(inst: dict, node_limit: int = _ALGORITHM_X_NODE_CAP
                 ) -> tuple[list[int] | None, dict]:
    """MRV Algorithm X, the domain-standard exact-cover attack."""

    start = time.perf_counter()
    rows = inst["sets"]
    universe = inst["universe_size"]
    width = inst["width"]
    masks = []
    containing = [[] for _ in range(universe)]
    for row_index, row in enumerate(rows):
        mask = 0
        for element in row:
            mask |= 1 << element
            containing[element].append(row_index)
        masks.append(mask)

    full = (1 << universe) - 1
    chosen: list[int] = []
    nodes = 0
    operations = 0
    exhausted = False

    def visit(uncovered: int) -> list[int] | None:
        nonlocal nodes, operations, exhausted
        nodes += 1
        if nodes > node_limit:
            exhausted = True
            return None
        if uncovered == 0:
            return chosen[:]
        best_options = None
        remaining = uncovered
        while remaining:
            low = remaining & -remaining
            element = low.bit_length() - 1
            options = []
            for row_index in containing[element]:
                operations += width
                if masks[row_index] & uncovered == masks[row_index]:
                    options.append(row_index)
            if best_options is None or len(options) < len(best_options):
                best_options = options
                if not options:
                    break
            remaining ^= low
        assert best_options is not None
        for row_index in best_options:
            chosen.append(row_index)
            found = visit(uncovered ^ masks[row_index])
            if found is not None:
                return found
            chosen.pop()
            if exhausted:
                return None
        return None

    answer0 = visit(full)
    answer = None if answer0 is None else sorted(index + 1 for index in answer0)
    return answer, {
        "nodes": nodes,
        "operations": operations,
        "node_limit": node_limit,
        "exhausted": exhausted,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _attack_outlier_degree(inst: dict) -> list[int]:
    degrees = Counter(element for row in inst["sets"] for element in row)
    ranked = sorted(range(len(inst["sets"])), key=lambda row_index: (
        sum(degrees[element] for element in inst["sets"][row_index]), row_index
    ))
    return sorted(row_index + 1 for row_index in ranked[:inst["n"]])


def _attack_greedy(inst: dict) -> list[int] | None:
    rows = inst["sets"]
    universe = inst["universe_size"]
    containing = [[] for _ in range(universe)]
    for row_index, row in enumerate(rows):
        for element in row:
            containing[element].append(row_index)
    uncovered = set(range(universe))
    chosen = []
    while uncovered:
        element = min(uncovered, key=lambda x: sum(
            all(y in uncovered for y in rows[row_index])
            for row_index in containing[x]
        ))
        options = [row_index for row_index in containing[element]
                   if all(y in uncovered for y in rows[row_index])]
        if not options:
            return None
        row_index = min(options)
        chosen.append(row_index + 1)
        uncovered.difference_update(rows[row_index])
    return sorted(chosen)


def _attack_random_restarts(inst: dict, seed: int, restarts: int = 256
                           ) -> list[int] | None:
    rng = random.Random(seed)
    indices = list(range(len(inst["sets"])))
    for _ in range(restarts):
        rng.shuffle(indices)
        used: set[int] = set()
        chosen = []
        for row_index in indices:
            row = inst["sets"][row_index]
            if used.isdisjoint(row):
                used.update(row)
                chosen.append(row_index)
                if len(chosen) == inst["n"]:
                    break
        if len(chosen) == inst["n"] and _covers(inst, chosen):
            return sorted(row_index + 1 for row_index in chosen)
    return None


def _answer_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _transform_instance(inst: dict, set_order: list[int],
                        element_map: list[int], reverse_rows: bool = False) -> dict:
    """Relabel both bipartite parts and carry the compressed colouring."""

    old_to_new_set = {old_index + 1: new_index + 1
                      for new_index, old_index in enumerate(set_order)}
    transformed_rows = []
    for old_index in set_order:
        row = [element_map[element] for element in inst["sets"][old_index]]
        if reverse_rows:
            row.reverse()
        transformed_rows.append(row)
    moved = dict(inst)
    moved["sets"] = transformed_rows
    moved["answer"] = sorted(old_to_new_set[set_id]
                             for set_id in inst["answer"])
    return moved


def selftest() -> dict:
    """Run mandatory gates G1--G9 and return their measured report."""

    report: dict[str, Any] = {}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            sample = make_instance(seed=1000 + seed, **params)
            ok, reason = verify(sample, sample["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": reason})
            try:
                json_native = json.loads(json.dumps(sample["answer"]))
                if json_native != sample["answer"]:
                    g1_failures.append({"preset": preset, "seed": seed,
                                        "reason": "answer is not JSON-native"})
            except (TypeError, ValueError) as exc:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": f"answer JSON error: {exc}"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=4242, **shipping)
    planted = inst["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [_n_candidates(inst) + 1],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (all(row["rejected"] for row in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_reason_count": len(set(reasons)),
    }

    model_style = (
        "The complete translation class gives the extension.\n"
        "```json\n<answer>" + json.dumps(planted) + "</answer>\n```\n"
        "The IDs are already increasing."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(0x190500305)
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(_covers(inst, [value - 1 for value in candidate]))
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "candidate_prior": "uniform over increasing n-subsets of all set IDs",
        "search_space": search_space(inst),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    algo_rows = []
    scan_rows = []
    algorithm_successes = 0
    scan_successes = 0
    for seed in range(8):
        sample = make_instance(seed=6000 + seed, **shipping)
        candidate, metrics = _algorithm_x(sample)
        ok = candidate is not None and verify(sample, candidate)[0]
        algorithm_successes += int(ok)
        algo_rows.append({"seed": seed, "solved": bool(ok), **metrics})
        candidate2, metrics2 = _reference_translation_scan(sample)
        ok2 = candidate2 is not None and verify(sample, candidate2)[0]
        scan_successes += int(ok2)
        scan_rows.append({"seed": seed, "solved": bool(ok2), **metrics2})
    report["G5_density_and_baseline_cost"] = {
        "pass": (demo_count is not None and demo_count >= 1
                 and algorithm_successes == 8 and scan_successes == 8),
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_observed_solution_fraction": observed,
        "demo_exact_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "algorithm_x_nodes_mean": sum(row["nodes"] for row in algo_rows) / 8,
        "algorithm_x_nodes_max": max(row["nodes"] for row in algo_rows),
        "algorithm_x_operations_mean": sum(row["operations"] for row in algo_rows) / 8,
        "algorithm_x_operations_max": max(row["operations"] for row in algo_rows),
        "algorithm_x_wall_clock_sec_mean": sum(row["wall_clock_sec"] for row in algo_rows) / 8,
        "algorithm_x_wall_clock_sec_max": max(row["wall_clock_sec"] for row in algo_rows),
        "translation_scan_operations": scan_rows[0]["operations"],
        "translation_scan_wall_clock_sec_max": max(row["wall_clock_sec"] for row in scan_rows),
    }

    attack_results = {
        "outlier_element_degree_score": {"successes": 0, "attempts": 8},
        "greedy_mrv_no_backtracking": {"successes": 0, "attempts": 8},
        "random_restart_256_disjoint_packings": {"successes": 0, "attempts": 8},
        "by_hand_first_n_rows": {"successes": 0, "attempts": 8},
    }
    for seed in range(8):
        sample = make_instance(seed=9000 + seed, **shipping)
        candidates = {
            "outlier_element_degree_score": _attack_outlier_degree(sample),
            "greedy_mrv_no_backtracking": _attack_greedy(sample),
            "random_restart_256_disjoint_packings": _attack_random_restarts(
                sample, 100_000 + seed),
            "by_hand_first_n_rows": list(range(1, sample["n"] + 1)),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(sample, candidate)[0]:
                attack_results[name]["successes"] += 1
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and algorithm_successes == 8 and scan_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Algorithm X with minimum-remaining-element branching",
            "complexity": "exponential worst case in candidate sets",
            "wall_clock_sec_mean": report["G5_density_and_baseline_cost"]["algorithm_x_wall_clock_sec_mean"],
            "wall_clock_sec_max": report["G5_density_and_baseline_cost"]["algorithm_x_wall_clock_sec_max"],
            "operations_mean": report["G5_density_and_baseline_cost"]["algorithm_x_operations_mean"],
            "nodes_mean": report["G5_density_and_baseline_cost"]["algorithm_x_nodes_mean"],
            "solves": f"{algorithm_successes}/8, as expected",
        },
        "efficient_certificate_algorithm": {
            "name": "full modular translation-signature grouping",
            "complexity": "O(N*width) time and O(N*width) space",
            "operations": scan_rows[0]["operations"],
            "wall_clock_sec_max": max(row["wall_clock_sec"] for row in scan_rows),
            "solves": f"{scan_successes}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * shipping["n"], seed=8080,
                            decoy_orbits=shipping["decoy_orbits"],
                            width=shipping["width"])
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "shipping_answer_elements": _answer_atoms(inst["answer"]),
        "doubled_answer_elements": _answer_atoms(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    failures = []
    invariance_checks = 0
    real_checks = 0
    composed_checks = 0
    keys = []
    for seed in range(20):
        sample = make_instance(seed=12_000 + seed, **shipping)
        key = canonical_key(sample)
        keys.append(key)
        rng = random.Random(22_000 + seed)
        set_order = list(range(_n_candidates(sample)))
        element_map = list(range(sample["universe_size"]))
        rng.shuffle(set_order)
        rng.shuffle(element_map)
        moved = _transform_instance(sample, set_order, element_map,
                                    reverse_rows=True)
        invariance_checks += 1
        if canonical_key(moved) != key:
            failures.append({"seed": seed, "kind": "arbitrary bipartite relabel"})
        real_checks += 1
        if not verify(moved, moved["answer"])[0]:
            failures.append({"seed": seed, "kind": "carried colouring"})

        # A family-specific composition: permute cyclic columns and translate
        # each one, then also relabel candidate rows.
        n = sample["n"]
        width = sample["width"]
        column_order = list(range(width))
        rng.shuffle(column_order)
        offsets = [rng.randrange(n) for _ in range(width)]
        cyclic_map = [0] * sample["universe_size"]
        for column in range(width):
            for value in range(n):
                cyclic_map[column * n + value] = (
                    column_order[column] * n + (value + offsets[column]) % n
                )
        set_order2 = list(reversed(range(_n_candidates(sample))))
        composed = _transform_instance(sample, set_order2, cyclic_map)
        composed_checks += 1
        if (canonical_key(composed) != key
                or not verify(composed, composed["answer"])[0]):
            failures.append({"seed": seed, "kind": "column/translation composition"})
    report["G8_canonical_key"] = {
        "pass": not failures and len(set(keys)) == len(keys),
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_checks,
        "composed_transformation_checks": composed_checks,
        "unrelated_attempts": len(keys),
        "unrelated_distinct": len(set(keys)),
        "failures": failures,
        "transformations": [
            "arbitrary candidate-set relabelling",
            "arbitrary element relabelling",
            "incidence-row reversal",
            "cyclic-column permutation and independent translations composed with row relabelling",
        ],
    }

    max_chars = max_tokens = max_elements = 0
    for seed in range(32):
        sample = make_instance(seed=30_000 + seed, **shipping)
        blob = json.dumps(sample["answer"], separators=(",", ":"))
        max_chars = max(max_chars, len(blob))
        max_tokens = max(max_tokens, math.ceil(len(blob) / 4))
        max_elements = max(max_elements, _answer_atoms(sample["answer"]))
    intended_ops = _n_candidates(inst)
    arms = {name: dict(G9_MEASUREMENTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_minus_placebo = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    report["G9_no_tool_suitability"] = {
        "pass": max_chars <= 2000 and max_elements <= 256 and intended_ops <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": max_chars,
        "answer_tokens": max_tokens,
        "answer_elements": max_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_rows = [value for key, value in report.items()
                 if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(row.get("pass") for row in gate_rows)
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["track"] = TRACK
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
