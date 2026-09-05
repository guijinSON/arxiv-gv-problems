"""Verified cyclic graph-design starter completions from arXiv:2401.02846.

The paper's Lemma 4.7 gives a single ordered base block for a cyclic/multiplier
development of graph 201 at several orders.  An instance retains the paper's
native graph, cyclic group, multiplier orbit, and ordered base-block witness.
It inverse-generates an affine image of a published block, hides it in a pool,
and marks a mixture of five planted and uniformly sampled decoy residues.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the paper's 12-vertex 6-regular graph 201",
        "ordered base blocks over the cyclic group Z_p",
        "multiplier-and-translation developed graph designs",
    ],
    "verification_operations": [
        "exact modular affine relabelling",
        "exact undirected edge-difference comparison",
        "set membership and cardinality comparison",
    ],
    "domain_essentiality": "discretised_analogue",
    "reduction_kind": "convenience",
    "reduction": (
        "Benchmark convenience, not licensed by the paper: hide an affine image "
        "of a published starter in a marked residue pool."
    ),
    "reduction_source": "benchmark_convenience",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that affine relabellings preserve the cyclic multiplier "
        "development and expose themselves through pairwise-difference "
        "multiplicities among the marked residues; otherwise search for a "
        "12-vertex labelling in a large residue pool."
    ),
    "hardness_basis": (
        "Rejected Track B candidate: construction-aware marked-pair affine "
        "scanning is O(marker_count^2*|V(G)|) and used only 6,588 exact "
        "coordinate transforms across eight shipping instances (823 per "
        "instance), versus 1,768 operations (221 per instance) for the proposed "
        "difference-multiplicity route; the routes are too comparable for H."
    ),
    "max_answer_tokens": 18,
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

# n is the size of the residue pool, not the graph-design order p.
DIFFICULTY = {
    "demo": {"n": 12, "order": 73, "marker_count": 5},
    "easy": {"n": 40, "order": 217, "marker_count": 8},
    "medium": {"n": 160, "order": 577, "marker_count": 11},
    "hard": {"n": 480, "order": 1009, "marker_count": 14},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Affine relabellings preserve the multiplicity pattern of pairwise "
    "differences in the reference starter's consecutive prefix."
)
PLACEBO_HINT = (
    "Hint: Careful modular bookkeeping prevents sign mistakes while checking "
    "the displayed residues, edge differences, and graph-vertex ordering."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One ordered list of exactly 12 distinct residues from the displayed "
        "pool, containing exactly five displayed marked residues; every "
        "residue is an integer in [0,p-1]."
    ),
    "bounds": {
        "length": 12,
        "residue_min": 0,
        "residue_max": "p-1 (p <= 1009 in the named presets)",
        "marked_residues_required": 5,
        "maximum_shipping_pool": 480,
        "candidate_count": "C(marker_count,5)*C(n-marker_count,7)*12!",
    },
}

# The actual G9 numbers are filled after the script-owned runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Definition and source object. Section 1 defines a G-design of order p as an
edgewise decomposition of K_p into copies of G. Section 2 fixes graph 201 by
the binary adjacency-row code (63,63,207,207,51,51,12,12,0,0,0). Section 4
defines an ordered base block and its development map. Lemma 4.7 publishes the
four base blocks used here: orders 73, 217, 577 and 1009, with multipliers 1,
25, 27 and 139. Verification below executes the exact difference condition
that makes all multiplier-and-translation copies partition K_p.

Step-0 decision. Theorem 5.1 is an existence-spectrum theorem, not a hardness
theorem. Section 6 says that the authors obtained direct decompositions by
backtracking combined with random processes and that this is essentially
hopeless in general without a large automorphism. But the generated instances
deliberately have the large affine automorphism exposed by the paper's cyclic
construction. They therefore cannot honestly be Track A. On Track B the
construction-aware reference algorithm scans ordered pairs of marked residues,
because the generator always maps the first two reference coordinates into the
marked set, and forms twelve transformed coordinates per map. The compact route notices that
the first five reference coordinates are 0,1,2,3,4. Five of the marked
residues are their affine image, so the true step has the corresponding high
pairwise-difference multiplicity. Testing the few high-multiplicity oriented
steps recovers the entire transformed block within the no-tool operation cap.

Generation. The affine multiplier u and translation t are sampled first. The
published block is mapped coordinatewise by x -> u*x+t modulo p, which carries
its certificate through a structure-preserving map. The remaining pool
residues are sampled uniformly without replacement only after the witness is
known. Extra marker sets are sampled the same way and rejected unless the
planted progression's two oriented steps are the unique maximum-multiplicity
differences. This rejection condition is affine invariant, so individual
planted and decoy residues retain uniform marginals; the intended signal is
the joint affine pattern, not a positional or magnitude outlier.

Disposition. The marked-pair scan and the proposed compact route are both
quadratic in the marker count and differ by only a small constant factor at the
shipping preset. Moreover, the marked-pool hiding layer is benchmark
convenience rather than a reduction licensed by the paper. This candidate is
therefore retained only as rejected_gen_2401_02846.py and is not a shippable
native family.

Easy regimes and attacks. Order 73 has no multiplier orbit beyond translation
and the demo pool contains exactly the answer set, so it is intentionally hand
scale. The named ladder raises the paper order, pool crowding, and marker
crowding while the 12-entry witness stays fixed. Magnitude and input-position
outliers are removed by uniform sampling and sorted set rendering. Greedy
smallest-residue and smallest-step assignments ignore wraparound and affine
orientation. Uniform restarts sample the fully constrained certificate
language. A bounded low-step affine ansatz models what can realistically be
tried by hand without discovering the difference invariant. All four must
fail on eight shipping seeds; exhaustive affine scanning is separately
expected to solve all eight.

Canonicalization. Pool and marker order, arbitrary renumbering of graph
vertices (carrying the ordered block), and a global affine relabelling of
Z_p preserve the problem. canonical_key enumerates the 5*4 normalizations
that send an ordered pair of marked residues to 0 and 1, then chooses the
lexicographically least normalized pool/marker pair. This is exact for the
declared affine symmetry and does not hash a seed or a rendered statement.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000

# Section 2's graph 201 adjacency-row encoding.  A row integer is left-padded
# to the remaining row length, exactly as the paper's displayed 11-tuple says.
_GRAPH_201_CODE = (63, 63, 207, 207, 51, 51, 12, 12, 0, 0, 0)


def _decode_graph(code: tuple[int, ...]) -> list[list[int]]:
    edges: list[list[int]] = []
    for i, value in enumerate(code):
        bits = format(value, f"0{11 - i}b")
        for offset, bit in enumerate(bits, start=1):
            if bit == "1":
                edges.append([i, i + offset])
    return edges


_GRAPH_201_EDGES = _decode_graph(_GRAPH_201_CODE)

# Lemma 4.7, graph 201.  orbit_count=(p-1)/72.
_DESIGNS = {
    73: {
        "omega": 1,
        "base": [0, 1, 2, 3, 4, 23, 32, 67, 40, 62, 19, 26],
    },
    217: {
        "omega": 25,
        "base": [0, 1, 2, 3, 4, 6, 115, 206, 157, 196, 40, 90],
    },
    577: {
        "omega": 27,
        "base": [0, 1, 2, 3, 4, 6, 14, 501, 69, 300, 402, 539],
    },
    1009: {
        "omega": 139,
        "base": [0, 1, 2, 3, 4, 6, 13, 982, 338, 658, 314, 547],
    },
}


def _validate_parameters(n: int, order: int, marker_count: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if order not in _DESIGNS:
        raise ValueError(f"order must be one of {sorted(_DESIGNS)}")
    if n < 12 or n > order:
        raise ValueError("n must satisfy 12 <= n <= order")
    if isinstance(marker_count, bool) or not isinstance(marker_count, int):
        raise ValueError("marker_count must be an integer")
    if marker_count < 5 or marker_count > n - 7:
        raise ValueError("marker_count must satisfy 5 <= marker_count <= n-7")
    if marker_count - 5 > n - 12:
        raise ValueError("the pool has too few decoys for the requested markers")


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate an affine image of a published cyclic base block."""
    order = params.pop("order", 1009)
    marker_count = params.pop("marker_count", 14)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, order, marker_count)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    design = _DESIGNS[order]
    units = [value for value in range(1, order) if math.gcd(value, order) == 1]
    multiplier = rng.choice(units)
    translation = rng.randrange(order)
    answer = [
        (multiplier * value + translation) % order for value in design["base"]
    ]

    pool_set = set(answer)
    while len(pool_set) < n:
        pool_set.add(rng.randrange(order))
    decoy_pool = sorted(pool_set.difference(answer))
    # Rejection-condition only on an affine-invariant joint statistic: the two
    # orientations of the planted five-term progression must be the unique
    # maximum-multiplicity directed marker differences.  This makes the
    # intended compact route executable without changing any single residue's
    # uniform marginal distribution.
    for _ in range(10_000):
        marker_set = set(answer[:5])
        marker_set.update(rng.sample(decoy_pool, marker_count - 5))
        counts: dict[int, int] = {}
        for left in marker_set:
            for right in marker_set:
                if left != right:
                    difference = (right - left) % order
                    counts[difference] = counts.get(difference, 0) + 1
        maximum = max(counts.values())
        maxima = {difference for difference, count in counts.items() if count == maximum}
        if maximum == 4 and maxima == {multiplier, (-multiplier) % order}:
            break
    else:
        raise RuntimeError("could not sample a marker set with a unique affine signal")

    return {
        "family": "affine_completion_of_multiplier_developed_G201_design",
        "paper_graph": 201,
        "order": order,
        "orbit_multiplier": design["omega"],
        "orbit_count": (order - 1) // 72,
        "graph_edges": [list(edge) for edge in _GRAPH_201_EDGES],
        "reference_base_block": list(design["base"]),
        "pool": sorted(pool_set),
        "marked": sorted(marker_set),
        "marked_quota": 5,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the exact cyclic graph-design completion problem."""
    p = inst["order"]
    edge_text = " ".join(f"({u},{v})" for u, v in inst["graph_edges"])
    statement = f"""Recover a cyclic graph-design base block.

Definitions and exact conventions:
- All residues below belong to the cyclic group Z_{p}; arithmetic is modulo {p}, represented by integers 0 through {p - 1}.
- G is the simple graph on vertices 0 through 11 with these 36 unordered edges:
  {edge_text}
- K_{p} is the complete graph on residues 0 through {p - 1}.
- For an ordered 12-residue list L=(l0,...,l11), one labelled copy of G maps graph vertex i to li.
- Develop L using multiplier omega={inst['orbit_multiplier']} as follows. For every e=0,...,{inst['orbit_count'] - 1} and d=0,...,{p - 1}, include the labelled copy that maps vertex i to
      (omega^e * li + d) mod {p}.
  L is a valid base block precisely when all those copies partition the unordered edges of K_{p}: every K_{p} edge occurs exactly once.
- The following published reference base block for graph 201 is valid under that development:
  {inst['reference_base_block']}

Instance constraints:
- Your answer must be one ordered list of exactly 12 distinct residues.
- Every answer residue must belong to this unordered pool of {len(inst['pool'])} residues:
  {inst['pool']}
- Exactly {inst['marked_quota']} answer residues must belong to this unordered marked set of {len(inst['marked'])} residues:
  {inst['marked']}
- Order matters: answer position i labels graph vertex i. No residue may repeat.
- The developed copies of your submitted block must partition K_{p} exactly as defined above.

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 12 integers in graph-vertex order.
Example format (not necessarily a solution): <answer>[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract a 12-integer JSON list from tags, a fence, or prose."""
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.findall(text)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    bare = re.findall(r"\[(?:\s*-?\d+\s*,){11}\s*-?\d+\s*\]", text, re.S)
    bodies = tagged if tagged else (fenced if fenced else bare)
    for body in reversed(bodies):
        cleaned = body.strip()
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError, json.JSONDecodeError):
            nested = re.findall(
                r"\[(?:\s*-?\d+\s*,){11}\s*-?\d+\s*\]", cleaned, re.S
            )
            if not nested:
                continue
            try:
                value = json.loads(nested[-1])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        if (
            isinstance(value, list)
            and len(value) == 12
            and all(not isinstance(x, bool) and isinstance(x, int) for x in value)
        ):
            return value
    return None


def _shape_check(inst: dict, answer: object) -> tuple[list[int] | None, str]:
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    if len(answer) != 12:
        return None, f"wrong length: expected 12, got {len(answer)}"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return None, "every entry must be an integer"
    p = inst["order"]
    bad = next((value for value in answer if value < 0 or value >= p), None)
    if bad is not None:
        return None, f"residue out of range: {bad} is not in [0,{p - 1}]"
    if len(set(answer)) != 12:
        return None, "the base block repeats a residue"
    pool = set(inst["pool"])
    missing = next((value for value in answer if value not in pool), None)
    if missing is not None:
        return None, f"residue {missing} is not in the displayed pool"
    marker_hits = len(set(answer).intersection(inst["marked"]))
    if marker_hits != inst["marked_quota"]:
        return None, (
            f"wrong marked-residue count: expected {inst['marked_quota']}, "
            f"got {marker_hits}"
        )
    return answer, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any submitted cyclic starter exactly, never reading inst['answer']."""
    block, reason = _shape_check(inst, answer)
    if block is None:
        return False, reason

    p = inst["order"]
    omega = inst["orbit_multiplier"]
    seen: set[int] = set()
    for exponent in range(inst["orbit_count"]):
        scale = pow(omega, exponent, p)
        for edge_number, (left, right) in enumerate(inst["graph_edges"]):
            directed = (scale * (block[right] - block[left])) % p
            if directed == 0:
                return False, f"edge {edge_number} collapses to a loop"
            undirected = min(directed, p - directed)
            if undirected in seen:
                return False, (
                    "developed edge-difference collision at undirected class "
                    f"{undirected}"
                )
            seen.add(undirected)
    target = set(range(1, (p + 1) // 2))
    if seen != target:
        first_missing = min(target.difference(seen))
        return False, f"developed edge differences miss undirected class {first_missing}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the fully shape-, pool-, and quota-aware language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    marked = list(inst["marked"])
    unmarked = sorted(set(inst["pool"]).difference(marked))
    candidate = rng.sample(marked, inst["marked_quota"])
    candidate.extend(rng.sample(unmarked, 12 - inst["marked_quota"]))
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """Count the exact bounded language sampled by random_candidate."""
    markers = len(inst["marked"])
    unmarked = len(inst["pool"]) - markers
    quota = inst["marked_quota"]
    return (
        math.comb(markers, quota)
        * math.comb(unmarked, 12 - quota)
        * math.factorial(12)
    )


def enumerate_all(inst: dict) -> int | None:
    """Brute-force tiny languages only; return None before expensive work."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    # No named preset reaches this branch, but it is complete for custom tiny
    # instances whose declared language falls below the cap.
    import itertools

    count = 0
    markers = list(inst["marked"])
    unmarked = sorted(set(inst["pool"]).difference(markers))
    quota = inst["marked_quota"]
    for chosen_marked in itertools.combinations(markers, quota):
        for chosen_unmarked in itertools.combinations(unmarked, 12 - quota):
            for ordering in itertools.permutations(chosen_marked + chosen_unmarked):
                count += int(verify(inst, list(ordering))[0])
    return count


def _normal_form(inst: dict) -> tuple:
    """Exact canonical form under global AGL(1,p) and input set reorder."""
    p = inst["order"]
    pool = set(inst["pool"])
    marked = set(inst["marked"])
    candidates = []
    for zero in marked:
        for one in marked:
            if zero == one:
                continue
            difference = (one - zero) % p
            if math.gcd(difference, p) != 1:
                continue
            inverse = pow(difference, -1, p)
            norm_pool = tuple(sorted(((value - zero) * inverse) % p for value in pool))
            norm_marked = tuple(
                sorted(((value - zero) * inverse) % p for value in marked)
            )
            candidates.append((norm_marked, norm_pool))
    return min(candidates)


def canonical_key(inst: dict) -> str:
    """Hash an affine-normalized structural form, never a seed or rendering."""
    norm_marked, norm_pool = _normal_form(inst)
    payload = json.dumps(
        {
            "paper_graph": inst["paper_graph"],
            "order": inst["order"],
            "marked_quota": inst["marked_quota"],
            "marked": norm_marked,
            "pool": norm_pool,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "cyclic-G201-affine:" + hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase marker and pool crowding while the 12-entry answer stays fixed."""
    if not isinstance(params, dict) or set(params) != {"n", "order", "marker_count"}:
        return None
    n = params["n"]
    order = params["order"]
    marker_count = params["marker_count"]
    if order != 1009:
        return {
            "n": min(1009, max(n, 480)),
            "order": 1009,
            "marker_count": max(marker_count, 14),
        }
    # marker_count=16 is the last rung whose advertised compact route remains
    # within G9(c): 16*15 directed differences plus two 16-marker/12-coordinate
    # orientation checks cost at most 296 exact modular operations.
    if marker_count < 16:
        return {
            "n": min(order, max(n + 1, math.ceil(n * 1.25))),
            "order": order,
            "marker_count": marker_count + 1,
        }
    if n < order:
        return {"n": min(order, max(n + 1, math.ceil(n * 1.5))), "order": order, "marker_count": marker_count}
    return None


def _affine_template_scan(inst: dict) -> tuple[list[int] | None, int, int]:
    """Construction-aware solver: scan affine images induced by marked pairs."""
    p = inst["order"]
    pool = set(inst["pool"])
    marked_values = sorted(inst["marked"])
    marked = set(marked_values)
    reference = inst["reference_base_block"]
    reference_difference = (reference[1] - reference[0]) % p
    if math.gcd(reference_difference, p) != 1:
        return None, 0, 0
    reference_inverse = pow(reference_difference, -1, p)
    maps_tested = 0
    image_operations = 0
    for first_image in marked_values:
        for second_image in marked_values:
            if first_image == second_image:
                continue
            multiplier = (
                (second_image - first_image) * reference_inverse
            ) % p
            if math.gcd(multiplier, p) != 1:
                continue
            translation = (first_image - multiplier * reference[0]) % p
            maps_tested += 1
            candidate = [
                (multiplier * value + translation) % p for value in reference
            ]
            image_operations += len(reference)
            if not all(value in pool for value in candidate):
                continue
            if len(set(candidate).intersection(marked)) != inst["marked_quota"]:
                continue
            if verify(inst, candidate)[0]:
                return candidate, maps_tested, image_operations
    return None, maps_tested, image_operations


def _difference_multiplicity_solve(
    inst: dict,
) -> tuple[list[int] | None, int, int]:
    """Compact route: prioritize oriented marker differences by multiplicity."""
    p = inst["order"]
    markers = list(inst["marked"])
    counts: dict[int, int] = {}
    modular_operations = 0
    for left in markers:
        for right in markers:
            if left == right:
                continue
            difference = (right - left) % p
            modular_operations += 1
            counts[difference] = counts.get(difference, 0) + 1

    pool = set(inst["pool"])
    reference = inst["reference_base_block"]
    maximum = max(counts.values())
    ordered_steps = sorted(step for step, count in counts.items() if count == maximum)
    candidates_tested = 0
    for multiplier in ordered_steps:
        # The first five reference coordinates are 0,1,2,3,4.  The marker
        # sampler guarantees that the maximal step has exactly four directed
        # occurrences.  Build its successor graph with one modular addition
        # per marker; its unique five-vertex chain gives the endpoint.
        marker_set = set(markers)
        successors: dict[int, int] = {}
        for value in markers:
            modular_operations += 1
            successor = (value + multiplier) % p
            if successor in marker_set:
                successors[value] = successor
        non_starts = set(successors.values())
        for translation in sorted(marker_set.difference(non_starts)):
            chain = [translation]
            while chain[-1] in successors:
                chain.append(successors[chain[-1]])
            if len(chain) != 5:
                continue
            candidate = [
                (multiplier * value + translation) % p for value in reference
            ]
            modular_operations += len(reference)
            candidates_tested += 1
            if all(value in pool for value in candidate) and verify(inst, candidate)[0]:
                return candidate, modular_operations, candidates_tested
    return None, modular_operations, candidates_tested


def _valid_shape_fallback(inst: dict) -> list[int]:
    marked = list(inst["marked"][: inst["marked_quota"]])
    unmarked = sorted(set(inst["pool"]).difference(inst["marked"]))
    return marked + unmarked[: 12 - inst["marked_quota"]]


def _attack_outlier_magnitude(inst: dict) -> tuple[list[int], int]:
    """Choose the smallest allowed residues, then sort them by magnitude."""
    marked = sorted(inst["marked"])[: inst["marked_quota"]]
    unmarked = sorted(set(inst["pool"]).difference(inst["marked"]))[:7]
    return sorted(marked + unmarked), len(inst["pool"])


def _attack_greedy_vertex_order(inst: dict) -> tuple[list[int], int]:
    """Put marked residues first and greedily avoid early difference repeats."""
    available = list(inst["pool"])
    marked = set(inst["marked"])
    chosen: list[int] = []
    used_differences: set[int] = set()
    steps = 0
    for vertex in range(12):
        want_marked = vertex < inst["marked_quota"]
        candidates = [value for value in available if (value in marked) == want_marked]
        if not candidates:
            return _valid_shape_fallback(inst), steps
        best = None
        best_score = None
        for value in candidates:
            new_differences = []
            collision = 0
            for edge_left, edge_right in inst["graph_edges"]:
                if edge_right == vertex and edge_left < len(chosen):
                    difference = (value - chosen[edge_left]) % inst["order"]
                    difference = min(difference, inst["order"] - difference)
                    new_differences.append(difference)
                    collision += int(difference in used_differences)
                    steps += 1
            score = (collision, value)
            if best_score is None or score < best_score:
                best_score = score
                best = value
        assert best is not None
        chosen.append(best)
        available.remove(best)
        for edge_left, edge_right in inst["graph_edges"]:
            if edge_right == vertex and edge_left < len(chosen) - 1:
                difference = (best - chosen[edge_left]) % inst["order"]
                used_differences.add(min(difference, inst["order"] - difference))
    return chosen, steps


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[list[int], int, bool]:
    last = _valid_shape_fallback(inst)
    for attempt in range(1, restarts + 1):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, attempt, True
    return last, restarts, False


def _attack_small_step_ansatz(inst: dict) -> tuple[list[int], int]:
    """Try only small positive affine steps and the least marked translation."""
    p = inst["order"]
    translation = min(inst["marked"])
    pool = set(inst["pool"])
    attempts = 0
    for multiplier in range(1, 17):
        attempts += 1
        candidate = [
            (multiplier * value + translation) % p
            for value in inst["reference_base_block"]
        ]
        if (
            all(value in pool for value in candidate)
            and len(set(candidate).intersection(inst["marked"])) == inst["marked_quota"]
        ):
            return candidate, attempts
    return _valid_shape_fallback(inst), attempts


def _relabel_instance(
    inst: dict,
    ambient_multiplier: int,
    ambient_translation: int,
    vertex_permutation: list[int],
    rng: random.Random,
) -> dict:
    """Apply genuine ambient/vertex relabellings and carry the witness."""
    p = inst["order"]

    def move(value: int) -> int:
        return (ambient_multiplier * value + ambient_translation) % p

    moved = dict(inst)
    moved["pool"] = [move(value) for value in inst["pool"]]
    moved["marked"] = [move(value) for value in inst["marked"]]
    moved["reference_base_block"] = [0] * 12
    moved["answer"] = [0] * 12
    for old_vertex in range(12):
        new_vertex = vertex_permutation[old_vertex]
        moved["reference_base_block"][new_vertex] = move(
            inst["reference_base_block"][old_vertex]
        )
        moved["answer"][new_vertex] = move(inst["answer"][old_vertex])
    moved["graph_edges"] = [
        sorted((vertex_permutation[left], vertex_permutation[right]))
        for left, right in inst["graph_edges"]
    ]
    rng.shuffle(moved["pool"])
    rng.shuffle(moved["marked"])
    rng.shuffle(moved["graph_edges"])
    return moved


def _answer_metrics(answer: list[int]) -> tuple[int, int, int]:
    encoded = json.dumps(answer)
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def selftest() -> dict:
    """Run all local construction, density, attack, scale, and symmetry gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

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
                recovered = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if recovered != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
            compact, _, _ = _difference_multiplicity_solve(inst)
            if compact is None or not verify(inst, compact)[0]:
                g1_failures.append(f"{preset}/{seed}: compact route failed")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "construction_audit": (
            "every witness is an affine image of the exact Lemma 4.7 block, "
            "and the independent difference-multiplicity route recovered a witness"
        ),
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]

    swapped = list(answer)
    swap_pair = None
    for left in range(12):
        for right in range(left + 1, 12):
            trial = list(answer)
            trial[left], trial[right] = trial[right], trial[left]
            if not verify(ship, trial)[0]:
                swapped = trial
                swap_pair = [left, right]
                break
        if swap_pair is not None:
            break
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    outside_pool = next(
        value for value in range(ship["order"]) if value not in set(ship["pool"])
    )
    not_in_pool = list(answer)
    not_in_pool[6] = outside_pool
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": [ship["order"]] + answer[1:],
        "not_in_pool": not_in_pool,
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    core_names = ("drop", "swap", "duplicate", "empty", "out_of_range")
    core_reasons = [corruption_results[name]["reason"] for name in core_names]
    report["G2_rejects_corruption"] = {
        "pass": (
            swap_pair is not None
            and all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(core_reasons)) == len(core_reasons)
        ),
        "cases": corruption_results,
        "swap_positions": swap_pair,
        "distinct_required_reasons": len(set(core_reasons)),
    }

    realistic = (
        "The affine difference classes cover every required residue.\n```json\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n```\n"
        "This is the ordered block."
    )
    parsed = parse_answer(realistic)
    untagged = parse_answer(
        "Here is the base block:\n```json\n" + json.dumps(answer) + "\n```"
    )
    report["G3_round_trip"] = {
        "pass": (
            parsed == answer
            and untagged == answer
            and verify(ship, parsed)[0]
            and verify(ship, untagged)[0]
            and parse_answer("no block here") is None
        ),
        "parsed_matches": parsed == answer,
        "untagged_fence_matches": untagged == answer,
        "garbage_returns_none": parse_answer("no block here") is None,
    }

    guess_rng = random.Random(0x240102846)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": (
            "uniform over ordered distinct 12-tuples from the pool with "
            "exactly five marked entries"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_smallest_magnitudes",
        "greedy_vertex_order",
        "random_restart_256",
        "small_positive_step_ansatz",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_maps = 0
    reference_operations = 0
    reference_wall = 0.0
    compact_successes = 0
    compact_operations = 0
    compact_candidates = 0
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping)

        t0 = time.perf_counter()
        candidate, steps = _attack_outlier_magnitude(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["outlier_smallest_magnitudes"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _attack_greedy_vertex_order(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["greedy_vertex_order"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        _, steps, success = _attack_random_restart(
            inst, random.Random(seed ^ 0xA11F1E), 256
        )
        elapsed = time.perf_counter() - t0
        stat = attacks["random_restart_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _attack_small_step_ansatz(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["small_positive_step_ansatz"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        reference, maps_tested, operations = _affine_template_scan(inst)
        reference_wall += time.perf_counter() - t0
        reference_maps += maps_tested
        reference_operations += operations
        reference_successes += int(
            reference is not None and verify(inst, reference)[0]
        )

        compact, operations, candidates_tested = _difference_multiplicity_solve(inst)
        compact_operations += operations
        compact_candidates += candidates_tested
        compact_successes += int(compact is not None and verify(inst, compact)[0])

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed
            and reference_successes == len(attack_seeds)
            and compact_successes == len(attack_seeds)
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "construction-aware marked-pair affine-template scan",
            "complexity": "O(marker_count^2*12) exact modular operations",
            "wall_clock_sec": round(reference_wall, 6),
            "candidate_maps": reference_maps,
            "operations": reference_operations,
            "average_operations_per_instance": reference_operations // len(attack_seeds),
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route_audit": {
            "name": "marked pairwise-difference multiplicity plus affine transport",
            "complexity": "O(marker_count^2) after recognizing the affine invariant",
            "operations": compact_operations,
            "average_operations_per_instance": compact_operations // len(attack_seeds),
            "candidate_affine_maps_tested": compact_candidates,
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest_failing = max(attacks.items(), key=lambda item: item[1]["wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_fraction < 1e-6
            and reference_successes == len(attack_seeds)
            and reference_operations > 0
        ),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "enumerate_all_shipping": enumerate_all(ship),
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": reference_operations // len(attack_seeds),
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    preset_orders = [params["order"] for params in DIFFICULTY.values()]
    preset_pools = [params["n"] for params in DIFFICULTY.values()]
    preset_markers = [params["marker_count"] for params in DIFFICULTY.values()]
    doubled = make_instance(
        n=2 * shipping["n"],
        order=shipping["order"],
        marker_count=shipping["marker_count"],
        seed=909,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            preset_orders == sorted(set(preset_orders))
            and preset_pools == sorted(set(preset_pools))
            and preset_markers == sorted(set(preset_markers))
            and doubled_ok
            and len(doubled["pool"]) == 2 * len(ship["pool"])
            and len(doubled["answer"]) == len(ship["answer"])
        ),
        "preset_orders": dict(zip(DIFFICULTY, preset_orders)),
        "preset_pool_sizes": dict(zip(DIFFICULTY, preset_pools)),
        "preset_marker_counts": dict(zip(DIFFICULTY, preset_markers)),
        "doubled_n": len(doubled["pool"]),
        "answer_length_unchanged": len(doubled["answer"]) == len(ship["answer"]),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        vertex_permutation = list(range(12))
        rng.shuffle(vertex_permutation)
        variants = (
            _relabel_instance(inst, 1, 0, list(range(12)), random.Random(seed + 1)),
            _relabel_instance(
                inst,
                rng.randrange(1, inst["order"]),
                rng.randrange(inst["order"]),
                list(range(12)),
                random.Random(seed + 2),
            ),
            _relabel_instance(
                inst, 1, 0, vertex_permutation, random.Random(seed + 3)
            ),
            _relabel_instance(
                inst,
                rng.randrange(1, inst["order"]),
                rng.randrange(inst["order"]),
                vertex_permutation,
                random.Random(seed + 4),
            ),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "pool, marker, and edge-list reorder",
            "global affine relabelling of Z_p",
            "arbitrary graph-vertex renumbering with the block carried through",
            "composition of global affine and graph-vertex relabellings",
        ],
    }

    actual_chars, actual_tokens, elements = _answer_metrics(ship["answer"])
    # Exact worst-case serialisation bound for any 12 distinct residues at this
    # order: choose the twelve residues with the longest decimal spellings.
    worst_answer = list(range(ship["order"] - 12, ship["order"]))
    chars, tokens, _ = _answer_metrics(worst_answer)
    # marker_count*(marker_count-1) directed modular differences; for the two
    # uniquely maximal orientations, form one successor per marker and at most
    # one 12-term block transport each.
    intended_operations = (
        shipping["marker_count"] * (shipping["marker_count"] - 1)
        + 2 * (shipping["marker_count"] + 12)
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "sample_answer_chars": actual_chars,
        "sample_answer_tokens": actual_tokens,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "diagnostic_is_not_gated": True,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
