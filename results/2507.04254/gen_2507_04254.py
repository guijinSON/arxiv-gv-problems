"""Verified modular edge-colouring generator for arXiv:2507.04254.

The paper's native object is an edge-colouring in which every non-isolated
degree in every colour class is 1 modulo k.  This module inverse-generates a
coordinate-labelled regular bipartite graph as a union of permutation-polynomial perfect
matchings over F_p.  Consecutive bundles of k+1 matchings form the planted
mod-k colour classes.  The answer is a short symbolic rule, not a solved search
result; verification expands that rule and recomputes all degrees exactly.

The family is Track B.  Repeated bipartite matching finds an ordinary proper
edge-colouring and bundling k+1 matchings gives the requested modular
colouring in polynomial time.  At the shipping size that route emits thousands
of edge labels.  The intended route instead recognizes a quintic finite-
difference invariant in coordinate-neighbourhood sums.
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
except ImportError:  # The family needs only standard-library finite-field arithmetic.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "coordinate-labelled regular bipartite graph",
        "permutation-polynomial rule encoding a modular edge-colouring",
    ],
    "verification_operations": [
        "exact arithmetic in the prime field",
        "exact expansion of colour classes",
        "integer degree counting modulo k",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Neighbourhood-coordinate sums form a shifted quintic sequence; its "
        "highest finite differences expose the hidden change of variables and "
        "replace thousands of edge decisions by two field elements per component."
    ),
    "hardness_basis": (
        "Track B: the Hall-matching engine in Lemma 10 and the recursive "
        "construction in the proof of Lemma 9 specialize here to eight repeated "
        "perfect matchings, an O(b r^2 p^2) augmenting-path algorithm; at the "
        "shipping preset the measured reference panel inspects about 55,000 edges "
        "in about 0.02 seconds and emits 2,144 edge labels, while the compact "
        "finite-difference route uses at most 260 exact field operations and emits "
        "eight residues."
    ),
    "max_answer_tokens": 9,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is a lower bound on the prime field order; make_instance uses the first
# prime p >= n.  The answer length stays fixed above the demo rung while the
# graph/haystack grows from 1,184 to 3,296 edges.
DIFFICULTY = {
    "demo": {"n": 13, "components": 1, "modulus": 3, "colours": 2},
    "easy": {"n": 37, "components": 4, "modulus": 3, "colours": 2},
    "medium": {"n": 67, "components": 4, "modulus": 3, "colours": 2},
    "hard": {"n": 103, "components": 4, "modulus": 3, "colours": 2},
}
SHIPPING_DIFFICULTY = "medium"

# Scratch G9 runs set this so harden.py measures one arm at the shipping rung
# instead of walking the ordinary difficulty ladder.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly b pairs [a,b], one per component, where a is "
        "nonzero and b is arbitrary modulo the displayed prime p.  The pair "
        "colours edge (u,v) from the rank of v-a*(u-b)^5 among that component's "
        "r=(k+1)c intercepts, in consecutive bundles of k+1."
    ),
    "bounds": {
        "outer_length": "number of components b",
        "pair_length": 2,
        "a_range": "1..p-1",
        "b_range": "0..p-1",
        "candidate_count": "(p(p-1))^b",
        "shipping_atomic_entries": 8,
        "shipping_prime": 67,
    },
}

STRUCTURAL_HINT = (
    "The sums of the right-coordinate neighbourhoods form a shifted quintic "
    "sequence over the prime field."
)
PLACEBO_HINT = (
    "Within each component, careful bookkeeping of vertex sides and coordinates "
    "helps avoid arithmetic mistakes."
)


# Replaced after the script-owned bare/structural/placebo oracle runs.  The
# three arms are diagnostics; G9(c)'s size/operation caps are the only gate.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "service_errors": 0},
    "hinted": {"solved": 0, "attempts": 3, "service_errors": 0},
    "placebo": {"solved": 1, "attempts": 2, "service_errors": 4},
    "hinted_verdict": "hardened; placebo third slot unavailable after key-limit errors",
}


NOTES = """\
Section 1 fixes the definition used by render and verify: a chi'_k-colouring
is an edge-colouring for which every nonzero degree in every colour class is
1 modulo k.  Lemma 10 is the Hall-type perfect-matching engine, and the proof
of Lemma 9 explicitly builds a colouring recursively from star packings and a
matching.  Those results are the Step-0 warning against a Track-A claim: on
this regular bipartite subfamily, repeated perfect matching gives a polynomial
algorithm.  Its measured cost and success are therefore disclosed as the
Track-B reference algorithm.

Generation samples the permutation-polynomial matchings first, bundles exactly k+1 matchings
per modular colour, and only then independently renumbers the left and right
vertices.  Thus the certificate is known by inverse generation.  Every vertex
has the same degree, every planted matching has the same size, and the offsets
within a component are a uniform subset, so plants and decoys do not have a
per-vertex size or degree signature.  The degree-constant outlier guess, the
minimum-neighbour greedy alignment, a first-pair alignment, the first-moment
affine shortcut that broke the initial build, and 256 random restarts are tested
separately.  The standard matching algorithm is
expected to solve and is not misreported as a failed attack.
"""


def _is_prime(value):
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


def _next_prime(value):
    candidate = max(2, int(value))
    while not _is_prime(candidate):
        candidate += 1
    return candidate


def _next_field_prime(value):
    """First prime >= value for which x -> x^5 permutes F_p."""
    candidate = max(7, int(value))
    while not (_is_prime(candidate) and math.gcd(5, candidate - 1) == 1):
        candidate += 1
    return candidate


def _normalise_residue_set(values, p):
    """Affine normal form of a subset of F_p, for generated-family keys."""
    base = tuple(sorted(set(int(x) % p for x in values)))
    if not base:
        return ()
    best = None
    for scale in range(1, p):
        for shift in range(p):
            image = tuple(sorted((scale * x + shift) % p for x in base))
            if best is None or image < best:
                best = image
    return best


def _coordinate_adjacency(component, p):
    left = component["left_coords"]
    right = component["right_coords"]
    adjacency = {u: [] for u in range(p)}
    for left_id, right_id in component["edges"]:
        adjacency[left[left_id]].append(right[right_id])
    return adjacency


def _recover_component_parameters(component, p):
    """Recover a,b in a*(u-b)^5 from six neighbourhood sums."""
    adjacency = _coordinate_adjacency(component, p)
    degree = len(adjacency[0])
    if degree == 0 or any(len(adjacency[u]) != degree for u in range(6)):
        return None, 0
    values = [sum(adjacency[u]) % p for u in range(6)]
    levels = [values]
    operations = 6 * (degree - 1)
    for _ in range(5):
        previous = levels[-1]
        levels.append([
            (previous[i + 1] - previous[i]) % p
            for i in range(len(previous) - 1)
        ])
        operations += len(previous) - 1

    # If S(u)=degree*a*(u-b)^5+constant, write its top terms as
    # A*u^5+B*u^4.  Delta^5 S(0)=120A and
    # Delta^4 S(0)=240A+24B.
    try:
        leading = levels[5][0] * pow(120 % p, -1, p) % p
        fourth = (levels[4][0] - 240 * leading) * pow(24 % p, -1, p) % p
        a = leading * pow(degree, -1, p) % p
        b = (-fourth) * pow((5 * leading) % p, -1, p) % p
    except ValueError:
        return None, operations + 8
    operations += 8
    if a == 0:
        return None, operations
    return [a, b], operations


def make_instance(n, seed=0, **params):
    """Inverse-generate permutation-polynomial factors and their colouring."""
    if type(n) is not int or n < 13:
        raise ValueError("n must be an integer at least 13")
    p = _next_field_prime(n)
    components = int(params.get("components", 4))
    modulus = int(params.get("modulus", 3))
    colours = int(params.get("colours", 2))
    if components < 1:
        raise ValueError("components must be positive")
    if modulus < 2:
        raise ValueError("modulus must be at least 2")
    if colours < 1:
        raise ValueError("colours must be positive")
    degree = (modulus + 1) * colours
    if degree >= p:
        raise ValueError("(modulus+1)*colours must be smaller than the prime p")

    rng = random.Random(seed)
    forbidden_scales = {1, degree % p}
    allowed_scales = [a for a in range(1, p) if a not in forbidden_scales]
    if len(allowed_scales) < components:
        raise ValueError("field is too small for distinct planted scales")
    scales = rng.sample(allowed_scales, components)
    shifts = [rng.randrange(p) for _ in range(components)]
    parameters = [[a, b] for a, b in zip(scales, shifts)]
    built = []
    used_offset_forms = set()
    for scale, shift in parameters:
        # Avoid duplicated isomorphism types inside one instance.  This affects
        # neither planted colour: all degree offsets are still exchangeable.
        while True:
            offsets = rng.sample(range(p), degree)
            form = _normalise_residue_set(offsets, p)
            if form not in used_offset_forms:
                used_offset_forms.add(form)
                break

        left_coords = list(range(p))
        right_coords = list(range(p))
        rng.shuffle(left_coords)
        rng.shuffle(right_coords)
        left_id = {coordinate: vertex_id
                   for vertex_id, coordinate in enumerate(left_coords)}
        right_id = {coordinate: vertex_id
                    for vertex_id, coordinate in enumerate(right_coords)}
        edges = [
            [left_id[u], right_id[(scale * pow((u - shift) % p, 5, p) + offset) % p]]
            for u in range(p)
            for offset in offsets
        ]
        rng.shuffle(edges)
        built.append({
            "left_coords": left_coords,
            "right_coords": right_coords,
            "edges": edges,
        })

    return {
        "paper": "2507.04254",
        "requested_n": n,
        "p": p,
        "modulus": modulus,
        "colours": colours,
        "degree": degree,
        "components": built,
        "answer": parameters,
    }


def _validate_instance_shape(inst):
    try:
        p = inst["p"]
        modulus = inst["modulus"]
        colours = inst["colours"]
        degree = inst["degree"]
        components = inst["components"]
    except (KeyError, TypeError):
        return False, "malformed instance header"
    if (type(p) is not int or not _is_prime(p) or type(modulus) is not int
            or modulus < 2 or type(colours) is not int or colours < 1
            or degree != (modulus + 1) * colours
            or not isinstance(components, list) or not components):
        return False, "malformed instance parameters"
    for index, component in enumerate(components, 1):
        try:
            left = component["left_coords"]
            right = component["right_coords"]
            edges = component["edges"]
        except (KeyError, TypeError):
            return False, f"component {index} is malformed"
        if (sorted(left) != list(range(p)) or sorted(right) != list(range(p))
                or len(edges) != p * degree):
            return False, f"component {index} has malformed vertices or edge count"
        seen = set()
        left_degrees = [0] * p
        right_degrees = [0] * p
        for edge in edges:
            if (not isinstance(edge, list) or len(edge) != 2
                    or type(edge[0]) is not int or type(edge[1]) is not int
                    or not 0 <= edge[0] < p or not 0 <= edge[1] < p):
                return False, f"component {index} contains a malformed edge"
            pair = (edge[0], edge[1])
            if pair in seen:
                return False, f"component {index} contains a repeated edge"
            seen.add(pair)
            left_degrees[edge[0]] += 1
            right_degrees[edge[1]] += 1
        if any(d != degree for d in left_degrees + right_degrees):
            return False, f"component {index} is not {degree}-regular"
    return True, "ok"


def _check_edge_colours(inst, edge_colours):
    """Check an explicit component-major edge-colouring, for generality/G8."""
    expected = sum(len(component["edges"]) for component in inst["components"])
    if not isinstance(edge_colours, list):
        return False, "edge_colors must be a list"
    if len(edge_colours) != expected:
        return False, f"expected {expected} edge colors, got {len(edge_colours)}"
    colours = inst["colours"]
    modulus = inst["modulus"]
    p = inst["p"]
    cursor = 0
    used = set()
    for component_index, component in enumerate(inst["components"], 1):
        left_degrees = [[0] * p for _ in range(colours)]
        right_degrees = [[0] * p for _ in range(colours)]
        for left_id, right_id in component["edges"]:
            colour = edge_colours[cursor]
            cursor += 1
            if type(colour) is not int or not 0 <= colour < colours:
                return False, f"edge color at position {cursor} is outside 0..{colours - 1}"
            used.add(colour)
            left_degrees[colour][left_id] += 1
            right_degrees[colour][right_id] += 1
        for colour in range(colours):
            for degree in left_degrees[colour] + right_degrees[colour]:
                if degree and degree % modulus != 1:
                    return False, (
                        f"component {component_index}, color {colour} has a "
                        f"nonzero degree {degree}, not 1 modulo {modulus}"
                    )
    if used != set(range(colours)):
        return False, f"the coloring must use every color 0..{colours - 1}"
    return True, "ok"


def verify(inst, answer):
    """Accept any valid compact rule (or any explicit valid edge-colouring)."""
    # Instances are trusted inputs produced by make_instance.  Rechecking their
    # O(bp*r) integrity on every candidate would make the 200,000-sample density
    # test measure repeated input parsing instead of witness verification.  G1
    # validates every generated instance in full; here we cheaply guard only the
    # header fields that control candidate bounds and array allocation.
    try:
        p = inst["p"]
        degree = inst["degree"]
        modulus = inst["modulus"]
        colours = inst["colours"]
        components = inst["components"]
    except (KeyError, TypeError):
        return False, "malformed instance header"
    if (type(p) is not int or not _is_prime(p) or type(modulus) is not int
            or modulus < 2 or type(colours) is not int or colours < 1
            or degree != (modulus + 1) * colours
            or not isinstance(components, list) or not components):
        return False, "malformed instance parameters"
    if isinstance(answer, dict):
        if set(answer) != {"edge_colors"}:
            return False, "answer object must contain only edge_colors"
        return _check_edge_colours(inst, answer["edge_colors"])
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of [a,b] pairs"
    if not answer:
        return False, "answer is empty"
    expected = len(inst["components"])
    if len(answer) != expected:
        return False, f"expected {expected} parameter pairs, got {len(answer)}"

    bundle = modulus + 1
    for index, pair in enumerate(answer, 1):
        if not isinstance(pair, list) or len(pair) != 2:
            return False, f"component {index} entry must be a two-integer list [a,b]"
        scale, shift = pair
        if type(scale) is not int or not 1 <= scale < p:
            return False, f"scale a at component {index} must be an integer in 1..{p - 1}"
        if type(shift) is not int or not 0 <= shift < p:
            return False, f"shift b at component {index} must be an integer in 0..{p - 1}"
        component = inst["components"][index - 1]
        left_coordinates = component["left_coords"]
        right_coordinates = component["right_coords"]
        intercepts = set()
        edge_intercepts = []
        for left_id, right_id in component["edges"]:
            intercept = (
                right_coordinates[right_id]
                - scale * pow((left_coordinates[left_id] - shift) % p, 5, p)
            ) % p
            intercepts.add(intercept)
            edge_intercepts.append(intercept)
            if len(intercepts) > degree:
                return False, (
                    f"component {index} induces more than {degree} intercepts"
                )
        if len(intercepts) != degree:
            return False, (
                f"component {index} induces {len(intercepts)} intercepts, "
                f"expected {degree}"
            )

        rank = {value: position for position, value in enumerate(sorted(intercepts))}
        left_degrees = [[0] * p for _ in range(colours)]
        right_degrees = [[0] * p for _ in range(colours)]
        for (left_id, right_id), intercept in zip(component["edges"], edge_intercepts):
            colour = rank[intercept] // bundle
            left_degrees[colour][left_id] += 1
            right_degrees[colour][right_id] += 1
        for colour in range(colours):
            for value in left_degrees[colour] + right_degrees[colour]:
                if value and value % modulus != 1:
                    return False, (
                        f"component {index}, color {colour} has nonzero degree "
                        f"{value}, not 1 modulo {modulus}"
                    )
    return True, "ok"


def render(inst):
    p = inst["p"]
    modulus = inst["modulus"]
    colours = inst["colours"]
    degree = inst["degree"]
    pair_word = "pair" if len(inst["components"]) == 1 else "pairs"
    lines = [
        "COMPRESSED MODULAR EDGE COLOURING",
        "",
        "A graph is split into the disjoint bipartite components listed below.",
        "In each component the left vertex IDs and right vertex IDs are both "
        f"0,...,{p - 1}.  Each ID has a displayed coordinate in the prime field "
        f"F_{p}; all arithmetic on coordinates is modulo {p}.  IDs and coordinates "
        "are different: always use the coordinate tables.",
        "",
        f"A mod-{modulus} edge-colouring is valid when, for each colour, every "
        f"vertex incident with that colour has degree congruent to 1 modulo {modulus} "
        "inside that colour class.  Degree zero is allowed.",
        "",
        "You must give one parameter pair [a_i,b_i] in F_p for each component i, "
        "with a_i nonzero.  It encodes the colouring as follows.  For an edge from "
        "left ID L to right ID R, look up coordinates u and v and compute the intercept",
        "    d = v - a_i*(u-b_i)^5 (mod p).",
        f"A pair is admissible only when its component has exactly {degree} distinct "
        "intercepts.  Sort those residues numerically as 0,...,p-1 and group "
        f"consecutive blocks of {modulus + 1}; block number 0,...,{colours - 1} is "
        "the edge colour.  Across components, equal block numbers are the same "
        f"global colour.  The resulting colouring must use exactly {colours} colours "
        f"and satisfy the mod-{modulus} degree condition above.",
        "",
        f"There are {len(inst['components'])} components; every component is "
        f"{degree}-regular.  Coordinate tables are JSON arrays indexed by vertex ID. "
        "Each adjacency row `Lx: ...` gives the right vertex IDs adjacent to left ID x; "
        "row order and neighbour order carry no meaning.",
    ]
    for component_index, component in enumerate(inst["components"], 1):
        lines.extend([
            "",
            f"COMPONENT {component_index}",
            "left coordinates by ID: "
            + json.dumps(component["left_coords"], separators=(",", ":")),
            "right coordinates by ID: "
            + json.dumps(component["right_coords"], separators=(",", ":")),
            "adjacency:",
        ])
        adjacency = [[] for _ in range(p)]
        for left_id, right_id in component["edges"]:
            adjacency[left_id].append(right_id)
        for left_id, neighbors in enumerate(adjacency):
            lines.append(
                f"L{left_id}: " + ",".join(str(v) for v in neighbors)
            )
    lines.extend([
        "",
        f"Return exactly {len(inst['components'])} {pair_word} in component order.  In "
        f"each [a,b], a must be an integer from 1 through {p - 1} and b an integer "
        f"from 0 through {p - 1}.  Order matters; pairs may repeat.",
        "Give your final answer inside <answer></answer> tags as a JSON list of pairs.",
        "Example format: <answer>[[3,0],[7,9]]</answer>",
        "The example only shows syntax; use the required number of pairs for this instance.",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if isinstance(value, list):
        if not all(
            isinstance(item, list) and len(item) == 2
            and all(type(entry) is int for entry in item)
            for item in value
        ):
            return None
        return value
    if isinstance(value, dict) and set(value) == {"edge_colors"}:
        edge_colours = value["edge_colors"]
        if isinstance(edge_colours, list) and all(type(x) is int for x in edge_colours):
            return value
    return None


def random_candidate(inst, rng):
    """Uniform on the stated [nonzero scale, arbitrary shift] language."""
    return [
        [rng.randrange(1, inst["p"]), rng.randrange(inst["p"])]
        for _ in inst["components"]
    ]


def search_space(inst):
    return (inst["p"] * (inst["p"] - 1)) ** len(inst["components"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    return sum(
        1 for flat in itertools.product(
            range(inst["p"] * (inst["p"] - 1)),
            repeat=len(inst["components"])
        )
        if verify(inst, [
            [value // inst["p"] + 1, value % inst["p"]]
            for value in flat
        ])[0]
    )


def canonical_key(inst):
    """Canonicalize generated components under IDs and affine coordinates.

    For this generated family, recovering each parameter pair exposes its offset set.  An
    affine normal form of that set is invariant under independent affine
    coordinate changes and under swapping the bipartition sides.  This is
    stronger than a generic cycle-count signature but is not claimed to solve
    arbitrary bipartite graph isomorphism outside the generated family.
    """
    ok, reason = _validate_instance_shape(inst)
    if not ok:
        raise ValueError(reason)
    p = inst["p"]
    forms = []
    for component in inst["components"]:
        parameters, _ = _recover_component_parameters(component, p)
        if parameters is None:
            # Deterministic, ID-invariant fallback for off-family objects.
            adjacency = [set() for _ in range(p)]
            for left_id, right_id in component["edges"]:
                adjacency[left_id].add(right_id)
            common = sorted(
                len(adjacency[i] & adjacency[j])
                for i in range(p) for j in range(i + 1, p)
            )
            forms.append(("fallback", tuple(common)))
            continue
        scale, shift = parameters
        coordinate_adjacency = _coordinate_adjacency(component, p)
        base = scale * pow((-shift) % p, 5, p) % p
        offsets = [(value - base) % p for value in coordinate_adjacency[0]]
        forms.append(("affine", _normalise_residue_set(offsets, p)))
    structural = {
        "p": p,
        "modulus": inst["modulus"],
        "colours": inst["colours"],
        "components": sorted(forms),
    }
    blob = json.dumps(structural, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    """Grow the field, then increase factor crowding within the 300-op cap."""
    n = int(params["n"])
    components = int(params["components"])
    modulus = int(params["modulus"])
    colours = int(params["colours"])
    # The first fixed-length axis is always a larger field.  On the first
    # post-ladder escalation, replace four degree-8 components by three
    # degree-10 components: more competing perfect matchings, a shorter answer,
    # and 231 intended arithmetic operations rather than 260.
    if components == 4 and modulus == 3 and colours == 2:
        components = 3
        modulus = 4
    return {
        "n": _next_field_prime(2 * n + 1),
        "components": components,
        "modulus": modulus,
        "colours": colours,
    }


def _reference_edge_colouring(inst):
    """Repeated Kuhn perfect matchings, bundled k+1 at a time."""
    p = inst["p"]
    bundle = inst["modulus"] + 1
    explicit = []
    inspections = 0
    for component in inst["components"]:
        remaining = [set() for _ in range(p)]
        for left_id, right_id in component["edges"]:
            remaining[left_id].add(right_id)
        matching_colour = {}
        for matching_index in range(inst["degree"]):
            matched_right = [-1] * p

            def augment(left_id, seen):
                nonlocal inspections
                for right_id in sorted(remaining[left_id]):
                    inspections += 1
                    if seen[right_id]:
                        continue
                    seen[right_id] = True
                    previous = matched_right[right_id]
                    if previous < 0 or augment(previous, seen):
                        matched_right[right_id] = left_id
                        return True
                return False

            for left_id in range(p):
                if not augment(left_id, [False] * p):
                    raise ValueError("reference matching unexpectedly failed")
            for right_id, left_id in enumerate(matched_right):
                if left_id < 0:
                    raise ValueError("reference matching did not cover the right side")
                remaining[left_id].remove(right_id)
                matching_colour[(left_id, right_id)] = matching_index // bundle
        explicit.extend(
            matching_colour[(left_id, right_id)]
            for left_id, right_id in component["edges"]
        )
    return {"edge_colors": explicit}, inspections


def _attack_degree_constant(inst):
    guess = inst["degree"] % inst["p"]
    guess = guess or 1
    return [[guess, 0] for _ in inst["components"]]


def _attack_minimum_neighbor(inst):
    p = inst["p"]
    guesses = []
    for component in inst["components"]:
        adjacency = _coordinate_adjacency(component, p)
        guess = (min(adjacency[1]) - min(adjacency[0])) % p
        guesses.append([guess or 1, 0])
    return guesses


def _attack_first_pair(inst):
    p = inst["p"]
    guesses = []
    for component in inst["components"]:
        left_coordinates = component["left_coords"]
        right_coordinates = component["right_coords"]
        first = {0: None, 1: None}
        for left_id, right_id in component["edges"]:
            coordinate = left_coordinates[left_id]
            if coordinate in first and first[coordinate] is None:
                first[coordinate] = right_coordinates[right_id]
            if first[0] is not None and first[1] is not None:
                break
        guess = (first[1] - first[0]) % p
        guesses.append([guess or 1, 0])
    return guesses


def _attack_first_moment_affine(inst):
    """The leak that broke v=s*u+d: fit a linear slope from row sums."""
    p = inst["p"]
    degree_inverse = pow(inst["degree"], -1, p)
    guesses = []
    for component in inst["components"]:
        adjacency = _coordinate_adjacency(component, p)
        slope = (sum(adjacency[1]) - sum(adjacency[0])) * degree_inverse % p
        guesses.append([slope or 1, 0])
    return guesses


def _random_restart_succeeds(inst, seed, restarts):
    rng = random.Random(seed)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _atom_count(value):
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def _relabel_vertex_ids(inst, rng):
    result = {
        key: value for key, value in inst.items()
        if key not in ("components", "answer")
    }
    result["answer"] = list(inst["answer"])
    transformed = []
    p = inst["p"]
    for component in inst["components"]:
        left_old_to_new = list(range(p))
        right_old_to_new = list(range(p))
        rng.shuffle(left_old_to_new)
        rng.shuffle(right_old_to_new)
        left_coords = [None] * p
        right_coords = [None] * p
        for old, new in enumerate(left_old_to_new):
            left_coords[new] = component["left_coords"][old]
        for old, new in enumerate(right_old_to_new):
            right_coords[new] = component["right_coords"][old]
        edges = [
            [left_old_to_new[left_id], right_old_to_new[right_id]]
            for left_id, right_id in component["edges"]
        ]
        rng.shuffle(edges)
        transformed.append({
            "left_coords": left_coords,
            "right_coords": right_coords,
            "edges": edges,
        })
    result["components"] = transformed
    return result


def _reorder_components(inst, rng):
    order = list(range(len(inst["components"])))
    rng.shuffle(order)
    result = {
        key: value for key, value in inst.items()
        if key not in ("components", "answer")
    }
    result["components"] = [inst["components"][i] for i in order]
    result["answer"] = [inst["answer"][i] for i in order]
    return result


def _affine_coordinates(inst, rng):
    p = inst["p"]
    result = {
        key: value for key, value in inst.items()
        if key not in ("components", "answer")
    }
    result["components"] = []
    result["answer"] = []
    for component, parameters in zip(inst["components"], inst["answer"]):
        scale, shift = parameters
        left_scale = rng.randrange(1, p)
        right_scale = rng.randrange(1, p)
        left_shift = rng.randrange(p)
        right_shift = rng.randrange(p)
        result["components"].append({
            "left_coords": [
                (left_scale * x + left_shift) % p
                for x in component["left_coords"]
            ],
            "right_coords": [
                (right_scale * y + right_shift) % p
                for y in component["right_coords"]
            ],
            "edges": [list(edge) for edge in component["edges"]],
        })
        result["answer"].append([
            right_scale * scale * pow(left_scale, -5, p) % p,
            (left_shift + left_scale * shift) % p,
        ])
    return result


def selftest():
    report = {}

    # G1: all presets, three independent seeds.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            instance = make_instance(seed=seed, **params)
            attempts += 1
            shape_ok, shape_reason = _validate_instance_shape(instance)
            if not shape_ok:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": shape_reason})
            ok, reason = verify(instance, instance["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "construction": "inverse-generated permutation-polynomial matchings bundled k+1 at a time",
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=314159, **shipping_params)

    # G2: five materially different corruptions and five distinct diagnostics.
    answer = [list(pair) for pair in inst["answer"]]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": [answer[1], answer[0]] + answer[2:],
        "duplicate_one": answer[:-1] + [list(answer[0])],
        "empty": [],
        "out_of_range": [[0, answer[0][1]]] + answer[1:],
    }
    cases = {}
    reasons = set()
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in cases.values()) and len(reasons) == len(cases),
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    # G3: realistic prose/fence wrapping plus malformed input.
    realistic = (
        "The translate calculation gives the following residues.\n"
        "<answer>\n```json\n" + json.dumps(inst["answer"]) + "\n```\n</answer>\n"
        "These pairs induce the two required colour classes."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("not an answer") is None,
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4/G5 shipping density sample, uniformly over the constrained language.
    guess_rng = random.Random(20260905)
    total = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    fraction = hits / total
    exact_space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": fraction < 1e-6,
        "hits": hits,
        "total": total,
        "fraction": fraction,
        "candidate_space": exact_space,
        "candidate_space_bits": exact_space.bit_length(),
        "exact_valid_compact_answers": 1,
        "exact_compact_density": 1 / exact_space,
        "structure_aware_constraints": [
            "exactly one [a,b] pair per component",
            "each a is nonzero and each b is arbitrary modulo p",
            "pair repetitions are allowed exactly as in the statement",
        ],
        "wall_clock_sec": round(guess_seconds, 6),
    }

    baseline_started = time.perf_counter()
    baseline_success = _random_restart_succeeds(inst, 271828, 2048)
    baseline_seconds = time.perf_counter() - baseline_started
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": fraction < 1e-6 and not baseline_success,
        "shipping_sample_hits": hits,
        "shipping_sample_total": total,
        "shipping_solution_density_estimate": fraction,
        "shipping_exact_compact_solution_count": 1,
        "shipping_exact_compact_solution_fraction": 1 / exact_space,
        "demo_candidate_space": search_space(demo),
        "demo_exact_solution_count": demo_count,
        "demo_exact_solution_fraction": demo_count / search_space(demo),
        "strongest_failing_attack": "random_restart_2048",
        "baseline_attack_restarts": 2048,
        "baseline_attack_successes": int(baseline_success),
        "baseline_attack_wall_clock_sec": round(baseline_seconds, 6),
    }

    # G6: four failed no-tool attacks, plus the successful Track-B reference.
    attack_totals = {
        "outlier_degree_constant": 0,
        "greedy_minimum_neighbor": 0,
        "random_restart_256": 0,
        "by_hand_first_pair_alignment": 0,
        "by_hand_first_moment_affine_ansatz": 0,
    }
    attack_times = {name: 0.0 for name in attack_totals}
    reference_operations = []
    reference_times = []
    compact_operations = []
    compact_times = []
    reference_successes = 0
    compact_successes = 0
    for seed in range(8):
        sample = make_instance(seed=10_000 + seed, **shipping_params)

        start = time.perf_counter()
        ok = verify(sample, _attack_degree_constant(sample))[0]
        attack_times["outlier_degree_constant"] += time.perf_counter() - start
        attack_totals["outlier_degree_constant"] += int(ok)

        start = time.perf_counter()
        ok = verify(sample, _attack_minimum_neighbor(sample))[0]
        attack_times["greedy_minimum_neighbor"] += time.perf_counter() - start
        attack_totals["greedy_minimum_neighbor"] += int(ok)

        start = time.perf_counter()
        ok = _random_restart_succeeds(sample, 20_000 + seed, 256)
        attack_times["random_restart_256"] += time.perf_counter() - start
        attack_totals["random_restart_256"] += int(ok)

        start = time.perf_counter()
        ok = verify(sample, _attack_first_pair(sample))[0]
        attack_times["by_hand_first_pair_alignment"] += time.perf_counter() - start
        attack_totals["by_hand_first_pair_alignment"] += int(ok)

        start = time.perf_counter()
        ok = verify(sample, _attack_first_moment_affine(sample))[0]
        attack_times["by_hand_first_moment_affine_ansatz"] += time.perf_counter() - start
        attack_totals["by_hand_first_moment_affine_ansatz"] += int(ok)

        start = time.perf_counter()
        explicit, operations = _reference_edge_colouring(sample)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(operations)
        reference_successes += int(verify(sample, explicit)[0])

        start = time.perf_counter()
        recovered = []
        operations = 0
        for component in sample["components"]:
            parameters, used = _recover_component_parameters(component, sample["p"])
            recovered.append(parameters)
            operations += used
        compact_times.append(time.perf_counter() - start)
        compact_operations.append(operations)
        compact_successes += int(verify(sample, recovered)[0])

    attacks = {
        name: {
            "successes": attack_totals[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_times[name], 6),
        }
        for name in attack_totals
    }
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "repeated augmenting-path perfect matchings, bundled k+1 per colour",
            "complexity": "O(b r^2 p^2) edge inspections",
            "operations": max(reference_operations),
            "operations_mean": sum(reference_operations) / len(reference_operations),
            "wall_clock_sec": round(max(reference_times), 6),
            "wall_clock_sec_total_8": round(sum(reference_times), 6),
            "output_edge_labels": sum(len(c["edges"]) for c in sample["components"]),
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "quintic finite differences of neighbourhood sums",
            "operations": max(compact_operations),
            "wall_clock_sec": round(max(compact_times), 6),
            "solves": f"{compact_successes}/8",
        },
    }

    # G7: double the requested size and also exercise fixed-answer escalation.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    start = time.perf_counter()
    doubled = make_instance(seed=12345, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_seconds = time.perf_counter() - start
    escalated = escalate(shipping_params)
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["p"] > inst["p"]
            and search_space(doubled) > search_space(inst)
            and len(doubled["answer"]) == len(inst["answer"])
            and escalated["n"] > shipping_params["n"]
        ),
        "shipping_requested_n": shipping_params["n"],
        "shipping_prime": inst["p"],
        "shipping_edges": sum(len(c["edges"]) for c in inst["components"]),
        "doubled_requested_n": doubled_params["n"],
        "doubled_prime": doubled["p"],
        "doubled_edges": sum(len(c["edges"]) for c in doubled["components"]),
        "answer_length_unchanged": len(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
        "doubled_build_and_verify_sec": round(doubled_seconds, 6),
        "escalation_after_shipping": escalated,
    }

    # G8: IDs, input order, component order, affine coordinates, and composition.
    key_failures = []
    invariant_count = 0
    real_count = 0
    unrelated_keys = set()
    for seed in range(20):
        base = make_instance(seed=30_000 + seed, **shipping_params)
        base_key = canonical_key(base)
        unrelated_keys.add(base_key)
        rng = random.Random(40_000 + seed)
        relabelled = _relabel_vertex_ids(base, rng)
        reordered = _reorder_components(base, rng)
        affined = _affine_coordinates(base, rng)
        edge_reordered = _relabel_vertex_ids(base, random.Random(50_000 + seed))
        composed = _affine_coordinates(
            _reorder_components(_relabel_vertex_ids(base, rng), rng), rng
        )
        for name, changed in (
            ("vertex_ID_relabelling_and_edge_reordering", relabelled),
            ("component_reordering", reordered),
            ("independent_affine_coordinate_changes", affined),
            ("independent_second_ID_and_edge_reordering", edge_reordered),
            ("composition_of_ID_component_and_affine_transformations", composed),
        ):
            invariant_count += 1
            try:
                same = canonical_key(changed) == base_key
            except Exception as exc:  # noqa: BLE001
                same = False
                key_failures.append({"seed": seed, "transform": name,
                                     "failure": f"key raised {type(exc).__name__}: {exc}"})
            if not same and not any(
                item.get("seed") == seed and item.get("transform") == name
                for item in key_failures
            ):
                key_failures.append({"seed": seed, "transform": name,
                                     "failure": "key changed"})
            valid, transform_reason = verify(changed, changed["answer"])
            real_count += int(valid)
            if not valid:
                key_failures.append({"seed": seed, "transform": name,
                                     "failure": transform_reason})
    report["G8_canonical_key"] = {
        "pass": not key_failures and len(unrelated_keys) == 20 and real_count == invariant_count,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_count,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(unrelated_keys),
        "transformations": [
            "arbitrary vertex-ID and edge-list relabelling",
            "component reordering with carried answer",
            "independent affine changes of left/right coordinates",
            "a second independent ID/edge reordering",
            "composition of ID, component, and affine changes",
        ],
        "key_caveat": (
            "complete for the declared generated coordinate symmetries; it uses "
            "affine offset-set normal forms and is not a general bipartite graph "
            "isomorphism algorithm outside this family"
        ),
        "failures": key_failures,
    }

    # G9: only caps gate; oracle arms are diagnostics populated after harden.py.
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atom_count(inst["answer"])
    intended_operations = (
        6 * (inst["degree"] - 1) + 15 + 8
    ) * len(inst["components"])
    arms = {
        key: dict(G9_ORACLE_RESULTS.get(key, {"solved": 0, "attempts": 0}))
        for key in ("bare", "hinted", "placebo")
    }
    diagnostic_ready = all(arms[key].get("attempts", 0) >= 3 for key in arms)
    hinted_minus_placebo = None
    if all(arms[key].get("attempts", 0) > 0 for key in arms):
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "diagnostic_evidence_ready": diagnostic_ready,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
