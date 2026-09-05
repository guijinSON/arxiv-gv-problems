"""Verified finite-field independent-set generator for arXiv:2101.04258.

Section 3 constructs intersection-omitting hypergraphs from polynomial fibres
in F_q^2.  This module keeps those objects, inverse-generates a short polynomial
graph, hides it among exchangeable translates, and applies the paper's local
fixed-core construction.  The construction secret is deliberately not part of
the rendered problem statement.
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


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The finite-field averages of the vertical fibres trace a common translate of a trinomial with adjacent equal-coefficient powers."
)
PLACEBO_HINT: str = (
    "Careful attention to the finite-field conventions and canonical term order helps prevent otherwise subtle transcription mistakes."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "polynomial",
    "native_objects": [
        "point set in the affine plane over a prime field",
        "affine-polynomial fibres with distinguished three-point cores",
        "sparse polynomial whose graph is a hypergraph independent set",
    ],
    "verification_operations": [
        "exact prime-field polynomial evaluation",
        "exact point membership",
        "exact affine-line incidence",
        "exact containment test for fixed-core hyperedges",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Finite-field fibre averages preserve a hidden polynomial up to one "
        "constant translate; without noticing that invariant, one performs "
        "full finite-field interpolation."
    ),
    "hardness_basis": (
        "Track B in Theorem 1.4's k=6, ell=2 regime and Sections 3.2--3.3: "
        "the reference algorithm is fibre averaging followed by Newton "
        "interpolation, O(q*s+n^2), measured at 34,373 exact field "
        "operations and 0.0024 seconds per shipping instance in the final run; the hidden "
        "fibre-average invariant reduces this to at most 62 operations."
    ),
    "max_answer_tokens": 8,
}

NATIVE: dict = {
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

DIFFICULTY: dict = {
    "demo": {"n": 6, "fiber_size": 5, "block_count": 1},
    "easy": {"n": 97, "fiber_size": 7, "block_count": 80},
    "medium": {"n": 397, "fiber_size": 9, "block_count": 350},
    "hard": {"n": 997, "fiber_size": 9, "block_count": 900},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A canonical sparse univariate polynomial over the displayed prime field "
        "with a nonzero constant term and exactly two further nonzero terms, represented as "
        "[[coefficient,[exponent]], ...] in strictly increasing exponent order. "
        "The structure-aware candidate prior additionally enforces the immediately "
        "checkable graph-membership constraints at x=0 and x=1."
    ),
    "bounds": {
        "n_terms": 3,
        "max_degree": "n",
        "coefficient_min": 1,
        "coefficient_max": "q-1",
        "monomial_variables": 1,
        "candidate_count": "C(n,2) times the admissible x=0/x=1 coefficient count",
    },
}

# Filled from the script-owned runs after the hardening loop.  Zero attempts are
# never interpreted as oracle failures.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES: str = r"""
Section 1.1 fixes the exact definition: an (N,k,ell)-omitting system has no two
k-edges meeting in exactly ell vertices, and an independent set contains no
edge.  Theorem 1.4 identifies the k>2ell+1 regime; this module uses its first
case (k,ell)=(6,2).  Sections 3.2 and 3.3 supply the native finite-field objects:
vertices (x,y), fibres that are graphs of low-degree polynomials, restriction to
a point set U, and local k-graphs consisting of all k-sets containing an
(ell+1)-point core.

The paper does not prove computational hardness.  Section 2 explicitly
describes the random greedy independent-set algorithm, and the Bennett--Bohman
result quoted there gives conditions under which it efficiently produces a
large witness.  A Track A claim would therefore be unsupported.  This module is
Track B and discloses its exact polynomial algorithm: average every vertical
fibre, then interpolate the resulting common translate by Newton differences.

Generation is inverse.  First choose P(x)=c+a*x^e+a*x^(e+1), with e drawn from
a broad interior interval, and choose a random offset set D whose field mean is
not itself in D.  Publish U_x=P(x)+D without publishing this decomposition.
Every translate P+delta, delta in D, has its graph in U.  Each displayed affine
line gets a three-point core using at least two offsets, so no translated graph
contains a core.  Within one block all 6-edges share three core points and meet
in at least three vertices; edges from distinct affine lines meet in at most
one.  Hence intersection size two is omitted as in Section 3.3.

Plant and decoys in a fibre are exchangeable: the stored answer chooses a
uniform offset from D, and all offsets are valid certificates.  The field mean
is deliberately not a vertex, defeating the simplest per-fibre outlier.  The
greedy integer-median interpolation, 256 structure-aware random restarts, and
obvious boundary-exponent ansatzes are tested over eight shipping seeds.  The
successful full interpolation algorithm is reported separately, as Track B
requires.

The canonical key uses a label-invariant color-refinement signature of the
three-sorted incidence structure (points, vertical fibres, affine blocks), with
core incidence distinguished.  It is invariant under input reorderings and
global nonzero scalings of x and affine changes of y.  Exact isomorphism is not
attempted, so rare color-refinement collisions remain possible.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(2, value)
    while not _is_prime(candidate):
        candidate += 1
    return candidate


def _prime_factors(value: int) -> list[int]:
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1
    if value > 1:
        factors.append(value)
    return factors


def _primitive_root(q: int) -> int:
    factors = _prime_factors(q - 1)
    for candidate in range(2, q):
        if all(pow(candidate, (q - 1) // factor, q) != 1 for factor in factors):
            return candidate
    raise ValueError("prime field has no primitive root")


def _validate_parameters(n: int, fiber_size: int, block_count: int, seed: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    if isinstance(fiber_size, bool) or not isinstance(fiber_size, int):
        raise ValueError("fiber_size must be an integer")
    if fiber_size < 3 or fiber_size % 2 == 0:
        raise ValueError("fiber_size must be an odd integer at least 3")
    if isinstance(block_count, bool) or not isinstance(block_count, int) or block_count < 0:
        raise ValueError("block_count must be a nonnegative integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    q = _next_prime(n + 2)
    if fiber_size >= q:
        raise ValueError("fiber_size must be smaller than the derived prime q")
    if block_count > q * q:
        raise ValueError("block_count cannot exceed the number q^2 of affine lines")
    return q


def _offsets_with_hidden_mean(q: int, size: int, rng: random.Random) -> list[int]:
    """Sample exchangeable offsets whose field mean is not itself an offset."""
    inverse_size = pow(size, -1, q)
    for _ in range(20_000):
        values = rng.sample(range(q), size)
        mean = sum(values) * inverse_size % q
        if mean not in values:
            rng.shuffle(values)
            return values
    raise ValueError("could not sample an offset set with a nonmember field mean")


def _eval_terms(terms: list[list], x: int, q: int) -> int:
    return sum(coefficient * pow(x, exponent_list[0], q) for coefficient, exponent_list in terms) % q


def _fiber_map(inst: dict) -> dict[int, list[int]]:
    if "fiber_lookup" in inst:
        return {x: ys for x, ys in enumerate(inst["fiber_lookup"])}
    return {fiber["x"]: fiber["ys"] for fiber in inst["vertical_fibers"]}


def make_instance(
    n: int,
    seed: int = 0,
    fiber_size: int = 5,
    block_count: int = 20,
    **params,
) -> dict:
    """Inverse-generate a polynomial graph independent-set certificate."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    q = _validate_parameters(n, fiber_size, block_count, seed)
    rng = random.Random(seed)

    offsets = _offsets_with_hidden_mean(q, fiber_size, rng)
    allowed_constants = [value for value in range(1, q) if all((value + d) % q != 0 for d in offsets)]
    if not allowed_constants:
        raise ValueError("no nonzero constant keeps the x=0 fibre away from zero")
    constant = rng.choice(allowed_constants)
    scale = rng.randrange(1, q)
    margin = max(1, min(32, (n - 2) // 4))
    exponent = rng.randrange(1 + margin, n - margin)
    answer_offset = rng.choice(offsets)

    base_terms = [
        [constant, [0]],
        [scale, [exponent]],
        [scale, [exponent + 1]],
    ]
    answer = [
        [(constant + answer_offset) % q, [0]],
        [scale, [exponent]],
        [scale, [exponent + 1]],
    ]
    if answer[0][0] == 0:
        raise AssertionError("constant selection failed to keep translated constants nonzero")

    base_values = [_eval_terms(base_terms, x, q) for x in range(q)]
    vertical_fibers = []
    fiber_sets: list[set[int]] = []
    offset_by_point: dict[tuple[int, int], int] = {}
    for x in range(q):
        ys = [(base_values[x] + delta) % q for delta in offsets]
        for y, delta in zip(ys, offsets):
            offset_by_point[(x, y)] = delta
        rng.shuffle(ys)
        vertical_fibers.append({"x": x, "ys": ys})
        fiber_sets.append(set(ys))

    blocks = []
    used_lines: set[tuple[int, int]] = set()
    attempts = 0
    attempt_cap = max(10_000, 50 * block_count)
    while len(blocks) < block_count and attempts < attempt_cap:
        attempts += 1
        slope = rng.randrange(q)
        intercept = rng.randrange(q)
        if (slope, intercept) in used_lines:
            continue
        used_lines.add((slope, intercept))
        points = [
            (x, (slope * x + intercept) % q)
            for x in range(q)
            if (slope * x + intercept) % q in fiber_sets[x]
        ]
        if len(points) < 6:
            continue
        labels = {offset_by_point[point] for point in points}
        if len(labels) < 2:
            continue
        core = None
        for _ in range(100):
            trial = rng.sample(points, 3)
            if len({offset_by_point[point] for point in trial}) >= 2:
                core = trial
                break
        if core is None:
            continue
        rng.shuffle(core)
        blocks.append(
            {
                "slope": slope,
                "intercept": intercept,
                "core": [[x, y] for x, y in core],
                "fiber_cardinality": len(points),
            }
        )
    if len(blocks) != block_count:
        raise ValueError(
            f"only {len(blocks)} eligible mixed-offset affine blocks; requested {block_count}"
        )
    rng.shuffle(vertical_fibers)
    rng.shuffle(blocks)

    fiber_lookup = [None] * q
    for fiber in vertical_fibers:
        fiber_lookup[fiber["x"]] = list(fiber["ys"])

    return {
        "family": "fixed-core affine-fibre (N,6,2)-omitting hypergraph",
        "n": n,
        "q": q,
        "primitive_root": _primitive_root(q),
        "fiber_size": fiber_size,
        "vertex_count": q * fiber_size,
        "uniformity": 6,
        "omitted_intersection": 2,
        "vertical_fibers": vertical_fibers,
        "fiber_lookup": fiber_lookup,
        "blocks": blocks,
        "block_count": len(blocks),
        "answer": answer,
    }


def render(inst: dict) -> str:
    fibers = _fiber_map(inst)
    fiber_lines = [f"  x={x}: " + " ".join(map(str, fibers[x])) for x in range(inst["q"])]
    block_lines = []
    for index, block in enumerate(inst["blocks"]):
        core = " ".join(f"({x},{y})" for x, y in block["core"])
        block_lines.append(
            f"  B{index:04d}: y={block['slope']}*x+{block['intercept']}; "
            f"core={core}; |fiber|={block['fiber_cardinality']}"
        )
    example = json.dumps([[1, [0]], [1, [1]], [1, [2]]], separators=(",", ":"))
    statement = f"""TRINOMIAL GRAPH IN AN INTERSECTION-OMITTING HYPERGRAPH

All arithmetic below is in the prime field F_{inst['q']}, represented by the
integers 0,...,{inst['q'] - 1}; reduce every sum and product modulo {inst['q']}.
For reference, g={inst['primitive_root']} is the least positive primitive root
of this field (its nonzero powers run through every nonzero field element).
The point set U is given by its vertical fibres.  A line "x=r: y1 ... ys" lists
exactly the points (r,y1),...,(r,ys) in U.  Orders within those lists do not
matter and repetitions are absent.

Point set U ({inst['vertex_count']} points):
{chr(10).join(fiber_lines)}

The following {inst['block_count']} affine blocks define a 6-uniform hypergraph
H on U.  For block Bi, let Ei be all displayed points satisfying its affine
equation y=a*x+b.  Its three listed core points belong to Ei.  The hyperedges
contributed by Bi are ALL 6-element subsets of Ei that contain all three core
points; H is the union of these hyperedges.  Thus an answer is independent when
it contains no such 6-set.  Distinct blocks are distinct affine lines.  It is
promised that the data below define an (N,6,2)-omitting hypergraph: no two
distinct hyperedges meet in exactly two points.

Blocks:
{chr(10).join(block_lines) if block_lines else '  (none at this hand-scale preset)'}

Find a polynomial Q over F_{inst['q']} satisfying all of the following:
1. Q has degree at most {inst['n']}, a nonzero constant term, and exactly two
   further nonzero monomial terms.
2. Its full graph {{(x,Q(x)) : x in F_{inst['q']}}} is contained in U.
3. That graph is an independent set of H.

Represent Q as a JSON array [[coefficient,[exponent]], ...].  Use integer field
representatives 1,...,{inst['q'] - 1} for nonzero coefficients, list exactly
three terms in strictly increasing exponent order, and use exponent lists of
length one.  Exponents are inclusive from 0 through {inst['n']}; repeats and
omitted zero coefficients are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format (not necessarily a solution): <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _json_values(text: str):
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "[":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        yield value


def parse_answer(text: str) -> object | None:
    """Extract a nested JSON polynomial from tags, fences, or surrounding prose."""
    if not isinstance(text, str):
        return None
    bodies = _ANSWER_RE.findall(text)
    if not bodies:
        bodies = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    if bodies:
        for body in reversed(bodies):
            for value in _json_values(body):
                if isinstance(value, list):
                    return value
        return None
    values = list(_json_values(text))
    return values[-1] if values and isinstance(values[-1], list) else None


def _normal_terms(inst: dict, answer: object) -> tuple[list[list] | None, str]:
    if not isinstance(answer, list):
        return None, "answer must be a JSON array"
    if not answer:
        return None, "polynomial term list is empty"
    parsed = []
    for term in answer:
        if (
            not isinstance(term, list)
            or len(term) != 2
            or isinstance(term[0], bool)
            or not isinstance(term[0], int)
            or not isinstance(term[1], list)
            or len(term[1]) != 1
            or isinstance(term[1][0], bool)
            or not isinstance(term[1][0], int)
        ):
            return None, "every term must have shape [integer_coefficient,[integer_exponent]]"
        parsed.append([term[0], [term[1][0]]])
    q = inst["q"]
    if any(coefficient <= 0 or coefficient >= q for coefficient, _ in parsed):
        return None, f"a coefficient is outside the canonical range 1..{q - 1}"
    exponents = [exponent_list[0] for _, exponent_list in parsed]
    if any(exponent < 0 or exponent > inst["n"] for exponent in exponents):
        return None, f"an exponent is outside the inclusive range 0..{inst['n']}"
    if len(set(exponents)) != len(exponents):
        return None, "a monomial exponent is duplicated"
    if exponents != sorted(exponents):
        return None, "terms are not in strictly increasing exponent order"
    if len(parsed) != 3:
        return None, "polynomial must contain exactly three nonzero terms"
    if exponents[0] != 0:
        return None, "the first term must be the nonzero constant term with exponent 0"
    return parsed, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid trinomial graph exactly; never consult inst['answer']."""
    terms, reason = _normal_terms(inst, answer)
    if terms is None:
        return False, reason
    q = inst["q"]
    fibers = inst.get("fiber_lookup")
    if not isinstance(fibers, list) or len(fibers) != q:
        mapped = _fiber_map(inst)
        fibers = [mapped[x] for x in range(q)]
    values = []
    for x in range(q):
        value = _eval_terms(terms, x, q)
        if value not in fibers[x]:
            return False, f"graph point at x={x} is absent from U"
        values.append(value)
    graph = {(x, values[x]) for x in range(q)}
    for index, block in enumerate(inst["blocks"]):
        if not all(tuple(point) in graph for point in block["core"]):
            continue
        slope = block["slope"]
        intercept = block["intercept"]
        count = sum(values[x] == (slope * x + intercept) % q for x in range(q))
        if count >= inst["uniformity"]:
            return False, f"graph contains a hyperedge from block B{index:04d}"
    return True, "ok"


def _audit_affine_blocks(inst: dict) -> tuple[bool, str]:
    """Check the finite data needed by the intersection-omitting proof."""
    q = inst["q"]
    fibers = _fiber_map(inst)
    lines = []
    for index, block in enumerate(inst["blocks"]):
        line = (block["slope"], block["intercept"])
        if line in lines:
            return False, f"block B{index:04d} repeats an affine line"
        lines.append(line)
        points = [
            (x, (line[0] * x + line[1]) % q)
            for x in range(q)
            if (line[0] * x + line[1]) % q in fibers[x]
        ]
        if len(points) != block["fiber_cardinality"] or len(points) < inst["uniformity"]:
            return False, f"block B{index:04d} has an incorrect fibre cardinality"
        core = [tuple(point) for point in block["core"]]
        if len(core) != 3 or len(set(core)) != 3 or not all(point in points for point in core):
            return False, f"block B{index:04d} has an invalid three-point core"
    return True, "ok"


def _coefficient_choice_count(inst: dict) -> int:
    q = inst["q"]
    fibers = _fiber_map(inst)
    return sum(q - 1 if (y1 - y0) % q == 0 else q - 2 for y0 in fibers[0] for y1 in fibers[1])


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing the obvious x=0 and x=1 constraints."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    q = inst["q"]
    fibers = inst.get("fiber_lookup")
    if not isinstance(fibers, list) or len(fibers) != q:
        mapped = _fiber_map(inst)
        fibers = [mapped[x] for x in range(q)]
    exponent_one, exponent_two = sorted(rng.sample(range(1, inst["n"] + 1), 2))
    # Weight each (Q(0),Q(1)) pair by its number of nonzero coefficient
    # decompositions, so every candidate counted by search_space is equiprobable.
    while True:
        constant = rng.choice(fibers[0])
        target_at_one = rng.choice(fibers[1])
        total = (target_at_one - constant) % q
        choices = q - 1 if total == 0 else q - 2
        if rng.randrange(q - 1) < choices:
            break
    while True:
        coefficient_one = rng.randrange(1, q)
        if total == 0 or coefficient_one != total:
            break
    coefficient_two = (total - coefficient_one) % q
    return [
        [constant, [0]],
        [coefficient_one, [exponent_one]],
        [coefficient_two, [exponent_two]],
    ]


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], 2) * _coefficient_choice_count(inst)


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    fibers = _fiber_map(inst)
    q = inst["q"]
    count = 0
    for exponent_one, exponent_two in itertools.combinations(range(1, inst["n"] + 1), 2):
        for constant in fibers[0]:
            for target_at_one in fibers[1]:
                total = (target_at_one - constant) % q
                for coefficient_one in range(1, q):
                    coefficient_two = (total - coefficient_one) % q
                    if coefficient_two == 0:
                        continue
                    candidate = [
                        [constant, [0]],
                        [coefficient_one, [exponent_one]],
                        [coefficient_two, [exponent_two]],
                    ]
                    count += int(verify(inst, candidate)[0])
    return count


def _incidence_signature(inst: dict) -> dict:
    """A coordinate-label-invariant signature of fibres, blocks, cores, and points."""
    fibers = _fiber_map(inst)
    points = sorted((x, y) for x, ys in fibers.items() for y in ys)
    point_index = {point: index for index, point in enumerate(points)}
    point_count = len(points)
    vertical_offset = point_count
    block_offset = point_count + inst["q"]
    node_count = block_offset + len(inst["blocks"])
    kinds = ["p"] * point_count + ["v"] * inst["q"] + ["b"] * len(inst["blocks"])
    adjacency: list[list[tuple[str, int]]] = [[] for _ in range(node_count)]

    for x in range(inst["q"]):
        vertical = vertical_offset + x
        for y in fibers[x]:
            point = point_index[(x, y)]
            adjacency[point].append(("vertical", vertical))
            adjacency[vertical].append(("vertical", point))

    for block_number, block in enumerate(inst["blocks"]):
        block_node = block_offset + block_number
        core = {tuple(point) for point in block["core"]}
        slope = block["slope"]
        intercept = block["intercept"]
        for x in range(inst["q"]):
            y = (slope * x + intercept) % inst["q"]
            if y not in fibers[x]:
                continue
            point = point_index[(x, y)]
            relation = "core" if (x, y) in core else "member"
            adjacency[point].append((relation, block_node))
            adjacency[block_node].append((relation, point))

    colors = [{"p": 0, "v": 1, "b": 2}[kind] for kind in kinds]
    rounds = 0
    for rounds in range(1, 13):
        signatures = [
            (kinds[node], colors[node], tuple(sorted((label, colors[other]) for label, other in adjacency[node])))
            for node in range(node_count)
        ]
        palette = {signature: color for color, signature in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        if new_colors == colors:
            break
        colors = new_colors

    node_hist = {}
    for kind, color in zip(kinds, colors):
        key = f"{kind}:{color}"
        node_hist[key] = node_hist.get(key, 0) + 1
    relation_hist = {}
    for node, neighbours in enumerate(adjacency):
        for label, other in neighbours:
            if node > other:
                continue
            pair = tuple(sorted((colors[node], colors[other])))
            key = f"{label}:{pair[0]}:{pair[1]}"
            relation_hist[key] = relation_hist.get(key, 0) + 1
    return {
        "q": inst["q"],
        "degree_bound": inst["n"],
        "fiber_size": inst["fiber_size"],
        "rounds": rounds,
        "node_colors": sorted(node_hist.items()),
        "relation_colors": sorted(relation_hist.items()),
    }


def canonical_key(inst: dict) -> str:
    payload = json.dumps(_incidence_signature(inst), sort_keys=True, separators=(",", ":"))
    return "affine-core-hypergraph-wl:" + hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the field and block haystack while the answer stays three terms."""
    if not isinstance(params, dict) or set(params) != {"n", "fiber_size", "block_count"}:
        return None
    n = params["n"]
    fiber_size = params["fiber_size"]
    block_count = params["block_count"]
    if not all(isinstance(value, int) for value in (n, fiber_size, block_count)):
        return None
    next_n = 2 * n + 1
    next_q = _next_prime(next_n + 2)
    width = math.isqrt(next_n - 1) + 1
    compact_operation_bound = 3 * (fiber_size + 1) + 8 + 2 * width + 2 * next_q.bit_length()
    if compact_operation_bound > 300:
        return "cap_bound"
    next_blocks = min(2400, block_count + 400)
    return {"n": next_n, "fiber_size": fiber_size, "block_count": next_blocks}


def _field_means(inst: dict, representatives=None) -> tuple[list[int], int]:
    fibers = _fiber_map(inst)
    q = inst["q"]
    inverse = pow(inst["fiber_size"], -1, q)
    values = []
    operations = 0
    for x in range(q):
        ys = fibers[x]
        if representatives is None:
            total = 0
            for y in ys:
                total = (total + y) % q
                operations += 1
            values.append(total * inverse % q)
            operations += 1
        else:
            values.append(representatives(ys))
    return values, operations


def _newton_interpolate(values: list[int], degree_bound: int, q: int) -> tuple[list[int], int]:
    """Interpolate at x=0,...,degree_bound in O(n^2) field operations."""
    size = degree_bound + 1
    divided = list(values[:size])
    operations = 0
    for order in range(1, size):
        inverse = pow(order, -1, q)
        operations += 1
        for index in range(size - 1, order - 1, -1):
            divided[index] = (divided[index] - divided[index - 1]) * inverse % q
            operations += 2

    result = [0] * size
    basis = [1]
    for index in range(size):
        coefficient = divided[index]
        for power, value in enumerate(basis):
            result[power] = (result[power] + coefficient * value) % q
            operations += 2
        if index == size - 1:
            break
        new_basis = [0] * (len(basis) + 1)
        for power, value in enumerate(basis):
            new_basis[power] = (new_basis[power] - index * value) % q
            new_basis[power + 1] = (new_basis[power + 1] + value) % q
            operations += 3
        basis = new_basis
    return result, operations


def _dense_to_terms(coefficients: list[int], q: int) -> list[list]:
    return [[value % q, [exponent]] for exponent, value in enumerate(coefficients) if value % q]


def _reference_interpolation(inst: dict) -> tuple[list[list] | None, int, int]:
    centers, operations = _field_means(inst)
    coefficients, interpolation_operations = _newton_interpolate(centers, inst["n"], inst["q"])
    operations += interpolation_operations
    fibers = _fiber_map(inst)
    offsets = [((y - centers[0]) % inst["q"]) for y in fibers[0]]
    trials = 0
    for delta in offsets:
        shifted = list(coefficients)
        shifted[0] = (shifted[0] + delta) % inst["q"]
        candidate = _dense_to_terms(shifted, inst["q"])
        trials += 1
        operations += 1
        if verify(inst, candidate)[0]:
            return candidate, operations, trials
    return None, operations, trials


def _mean_of_fiber(ys: list[int], q: int) -> tuple[int, int]:
    total = 0
    for y in ys:
        total = (total + y) % q
    return total * pow(len(ys), -1, q) % q, len(ys) + 1


def _compact_factor_solve(inst: dict) -> tuple[list[list] | None, int]:
    fibers = _fiber_map(inst)
    q = inst["q"]
    value_zero, op0 = _mean_of_fiber(fibers[0], q)
    value_one, op1 = _mean_of_fiber(fibers[1], q)
    generator = inst["primitive_root"]
    value_generator, op2 = _mean_of_fiber(fibers[generator], q)
    operations = op0 + op1 + op2
    scale = (value_one - value_zero) * pow(2, -1, q) % q
    operations += 2
    denominator = scale * (1 + generator) % q
    ratio = (value_generator - value_zero) * pow(denominator, -1, q) % q
    operations += 5
    bound = inst["n"] - 1
    width = math.isqrt(bound) + 1
    baby = {}
    current = 1
    for step in range(width):
        baby.setdefault(current, step)
        current = current * generator % q
        operations += 1
    inverse_giant_step = pow(current, -1, q)
    operations += 2 * q.bit_length()
    exponent = None
    giant = ratio
    for giant_index in range(width + 1):
        if giant in baby:
            candidate = giant_index * width + baby[giant]
            if 1 <= candidate <= bound:
                exponent = candidate
                break
        giant = giant * inverse_giant_step % q
        operations += 1
    if exponent is None:
        return None, operations
    # Every y in the x=0 fibre equals P(0)+delta for one delta in D.  The public
    # mixed-core promise makes P+delta independent, so no block scan is part of
    # the intended route.  The self-test separately verifies the returned object.
    constant = fibers[0][0]
    return [
        [constant, [0]],
        [scale, [exponent]],
        [scale, [exponent + 1]],
    ], operations


def _attack_field_mean_outlier(inst: dict) -> tuple[object, int]:
    centers, operations = _field_means(inst)
    coefficients, extra = _newton_interpolate(centers, inst["n"], inst["q"])
    return _dense_to_terms(coefficients, inst["q"]), operations + extra


def _attack_integer_median(inst: dict) -> tuple[object, int]:
    representatives = lambda ys: sorted(ys)[len(ys) // 2]
    values, _ = _field_means(inst, representatives=representatives)
    coefficients, operations = _newton_interpolate(values, inst["n"], inst["q"])
    return _dense_to_terms(coefficients, inst["q"]), operations


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 256) -> tuple[bool, int]:
    for attempt in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, attempt + 1
    return False, restarts


def _attack_boundary_exponent_scan(inst: dict) -> tuple[bool, int]:
    """Try the low/high exponent window that broke the first construction."""
    fibers = _fiber_map(inst)
    q = inst["q"]
    center_zero, op0 = _mean_of_fiber(fibers[0], q)
    center_one, op1 = _mean_of_fiber(fibers[1], q)
    scale = (center_one - center_zero) * pow(2, -1, q) % q
    constant = fibers[0][0]
    exponents = list(range(1, min(21, inst["n"])))
    exponents.extend(range(max(1, inst["n"] - 20), inst["n"]))
    exponents = sorted(set(exponents))
    for exponent in exponents:
        candidate = [
            [constant, [0]],
            [scale, [exponent]],
            [scale, [exponent + 1]],
        ]
        if verify(inst, candidate)[0]:
            return True, op0 + op1 + 2 + exponents.index(exponent) + 1
    return False, op0 + op1 + 2 + len(exponents)


def _reordered_instance(inst: dict, rng: random.Random) -> dict:
    moved = copy.deepcopy(inst)
    rng.shuffle(moved["vertical_fibers"])
    for fiber in moved["vertical_fibers"]:
        rng.shuffle(fiber["ys"])
    rng.shuffle(moved["blocks"])
    for block in moved["blocks"]:
        rng.shuffle(block["core"])
    return moved


def _coordinate_transform(
    inst: dict,
    x_scale: int,
    y_scale: int,
    y_shift: int,
    rng: random.Random,
) -> dict:
    q = inst["q"]
    if x_scale % q == 0 or y_scale % q == 0:
        raise ValueError("coordinate scales must be nonzero")
    moved = copy.deepcopy(inst)
    transformed_fibers = []
    for fiber in inst["vertical_fibers"]:
        transformed_fibers.append(
            {
                "x": x_scale * fiber["x"] % q,
                "ys": [(y_scale * y + y_shift) % q for y in fiber["ys"]],
            }
        )
    moved["vertical_fibers"] = transformed_fibers
    transformed_lookup = [None] * q
    for fiber in transformed_fibers:
        transformed_lookup[fiber["x"]] = list(fiber["ys"])
    moved["fiber_lookup"] = transformed_lookup
    inverse_x = pow(x_scale, -1, q)
    transformed_blocks = []
    for block in inst["blocks"]:
        transformed_blocks.append(
            {
                "slope": y_scale * block["slope"] * inverse_x % q,
                "intercept": (y_scale * block["intercept"] + y_shift) % q,
                "core": [
                    [x_scale * x % q, (y_scale * y + y_shift) % q]
                    for x, y in block["core"]
                ],
                "fiber_cardinality": block["fiber_cardinality"],
            }
        )
    moved["blocks"] = transformed_blocks
    transformed_terms = []
    for coefficient, exponent_list in inst["answer"]:
        exponent = exponent_list[0]
        value = y_scale * coefficient * pow(inverse_x, exponent, q) % q
        if exponent == 0:
            value = (value + y_shift) % q
        if value:
            transformed_terms.append([value, [exponent]])
    moved["answer"] = transformed_terms
    return _reordered_instance(moved, rng)


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    atoms = 0
    stack = [answer]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
        else:
            atoms += 1
    return len(encoded), math.ceil(len(encoded) / 4), atoms


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    compact_operations = []
    shipping_compact_operations = []
    translated_witness_checks = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 17):
            instance = make_instance(seed=seed, **parameters)
            ok, reason = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(instance["answer"])) == instance["answer"]:
                json_roundtrips += 1
            geometry_ok, geometry_reason = _audit_affine_blocks(instance)
            if not geometry_ok:
                g1_failures.append(f"{preset}/{seed}: {geometry_reason}")
            compact, operations = _compact_factor_solve(instance)
            compact_operations.append(operations)
            if preset == SHIPPING_DIFFICULTY:
                shipping_compact_operations.append(operations)
            if compact is None or not verify(instance, compact)[0]:
                g1_failures.append(f"{preset}/{seed}: compact factor route failed")
            elif compact is not None:
                for constant in _fiber_map(instance)[0]:
                    translated = copy.deepcopy(compact)
                    translated[0][0] = constant
                    translated_witness_checks += 1
                    translated_ok, translated_reason = verify(instance, translated)
                    if not translated_ok:
                        g1_failures.append(
                            f"{preset}/{seed}: translated witness failed: {translated_reason}"
                        )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "translated_witness_checks": translated_witness_checks,
        "failures": g1_failures,
        "construction_audit": (
            "affine blocks and cores were checked exactly, and an independent "
            "compact solver recovered a valid translated graph"
        ),
    }

    shipping_parameters = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping_parameters)
    answer = ship["answer"]
    swapped = copy.deepcopy(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = copy.deepcopy(answer)
    duplicated[2][1][0] = duplicated[1][1][0]
    out_of_range = copy.deepcopy(answer)
    out_of_range[0][0] = ship["q"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not entry["accepted"] for entry in corruption_results.values()) and len(set(reasons)) == 5,
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The common translates give the following sparse polynomial.\n```json\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n```\n"
        "All coefficients are canonical field representatives."
    )
    parsed = parse_answer(realistic)
    fenced = parse_answer("Result:\n```json\n" + json.dumps(answer) + "\n```")
    report["G3_round_trip"] = {
        "pass": parsed == answer and fenced == answer and verify(ship, parsed)[0] and parse_answer("no polynomial") is None,
        "tagged_matches": parsed == answer,
        "fenced_matches": fenced == answer,
        "garbage_returns_none": parse_answer("no polynomial") is None,
    }

    guess_rng = random.Random(0x210104258)
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
        "sampling_prior": "uniform over canonical trinomials already hitting U at x=0 and x=1",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_field_mean_as_vertex",
        "greedy_integer_median_interpolation",
        "random_restart_256_structure_aware",
        "obvious_boundary_exponent_scan_40",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_trials = 0
    reference_wall = 0.0
    compact_successes = 0
    compact_total_operations = 0
    for seed in range(800, 808):
        instance = make_instance(seed=seed, **shipping_parameters)

        t0 = time.perf_counter()
        candidate, steps = _attack_field_mean_outlier(instance)
        elapsed = time.perf_counter() - t0
        stat = attacks["outlier_field_mean_as_vertex"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(instance, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _attack_integer_median(instance)
        elapsed = time.perf_counter() - t0
        stat = attacks["greedy_integer_median_interpolation"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(instance, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _attack_random_restart(instance, random.Random(seed ^ 0xA51), 256)
        elapsed = time.perf_counter() - t0
        stat = attacks["random_restart_256_structure_aware"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _attack_boundary_exponent_scan(instance)
        elapsed = time.perf_counter() - t0
        stat = attacks["obvious_boundary_exponent_scan_40"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        reference, operations, trials = _reference_interpolation(instance)
        reference_wall += time.perf_counter() - t0
        reference_operations += operations
        reference_trials += trials
        reference_successes += int(reference is not None and verify(instance, reference)[0])

        compact, operations = _compact_factor_solve(instance)
        compact_total_operations += operations
        compact_successes += int(compact is not None and verify(instance, compact)[0])

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "fibre averaging plus Newton interpolation over F_q",
            "complexity": "O(q*fiber_size+n^2) exact field operations",
            "wall_clock_sec": round(reference_wall, 6),
            "average_wall_clock_sec": round(reference_wall / 8, 6),
            "operations": reference_operations,
            "average_operations_per_instance": reference_operations // 8,
            "offset_trials": reference_trials,
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route_audit": {
            "name": "three-fibre factor recovery and bounded discrete logarithm",
            "operations": compact_total_operations,
            "average_operations_per_instance": compact_total_operations // 8,
            "maximum_shipping_operations_seen": max(shipping_compact_operations),
            "maximum_operations_across_all_presets": max(compact_operations),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(attacks.items(), key=lambda item: item[1]["wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count is not None
            and demo_count > 0
            and guess_total >= 200_000
            and reference_successes == 8
        ),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_exact_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_average_wall_clock_sec": round(reference_wall / 8, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": reference_operations // 8,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    ladder_n = [parameters["n"] for parameters in DIFFICULTY.values()]
    ladder_blocks = [parameters["block_count"] for parameters in DIFFICULTY.values()]
    doubled = make_instance(
        n=2 * ship["n"],
        fiber_size=ship["fiber_size"],
        block_count=2 * ship["block_count"],
        seed=909,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            ladder_n == sorted(set(ladder_n))
            and ladder_blocks == sorted(set(ladder_blocks))
            and doubled_ok
            and search_space(doubled) > search_space(ship)
            and doubled["vertex_count"] > ship["vertex_count"]
        ),
        "preset_n": dict(zip(DIFFICULTY, ladder_n)),
        "preset_block_count": dict(zip(DIFFICULTY, ladder_blocks)),
        "doubled_n": doubled["n"],
        "doubled_q": doubled["q"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        instance = make_instance(n=23, fiber_size=5, block_count=30, seed=20_000 + seed)
        base_key = canonical_key(instance)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        reordered = _reordered_instance(instance, random.Random(40_000 + seed))
        x_scale = rng.randrange(1, instance["q"])
        y_scale = rng.randrange(1, instance["q"])
        old_constant = instance["answer"][0][0]
        forbidden_shift = (-y_scale * old_constant) % instance["q"]
        shift_choices = [value for value in range(instance["q"]) if value != forbidden_shift]
        y_shift = rng.choice(shift_choices)
        transformed = _coordinate_transform(
            instance, x_scale, y_scale, y_shift, random.Random(50_000 + seed)
        )
        composed = _reordered_instance(transformed, random.Random(60_000 + seed))
        for variant_number, variant in enumerate((reordered, transformed, composed)):
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                invariant_failures.append(f"seed {seed} variant {variant_number}: key changed")
            witness_checks += 1
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                invariant_failures.append(f"seed {seed} variant {variant_number}: {reason}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and invariant_checks == 60 and witness_checks == 60 and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "unrelated_instances": 20,
        "distinct_unrelated_keys": distinct_keys,
        "failures": invariant_failures,
        "transformations": [
            "vertical-fibre, point, block, and core reorderings",
            "global nonzero x scaling and affine y coordinate change",
            "composition of coordinate change with all input reorderings",
        ],
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(answer)
    intended_operations = max(shipping_compact_operations)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
