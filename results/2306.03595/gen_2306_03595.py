"""Verified problem generator derived from arXiv:2306.03595.

The paper represents a graph collection as a 3-uniform hypergraph and defines a
transversal embedding as injective vertex and colour maps (Section 1.7).  Its
Embedding Lemma with target and candidate sets (Lemma 3.1) builds a partial
embedding and leaves candidate sets for the remaining vertices.  This module
asks for the completion of a particularly compact family of those partial
embeddings.

Generation is inverse: right-hand images are sampled first, and the required
colours are computed from them.  The verifier reconstructs the two maps and
checks graph membership exactly; it never reads the planted answer.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "bipartite graph collection indexed by F_p^2",
        "matching with a partial vertex embedding",
        "injective edge-to-colour map",
    ],
    "verification_operations": [
        "finite-field vector subtraction",
        "evaluation of displayed invertible affine layers",
        "exact graph-edge membership",
        "injectivity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Regard each displayed affine swap layer as a bijective change of "
        "coordinates, so each singleton candidate set can be decoded instead "
        "of searched."
    ),
    "hardness_basis": (
        "Track B: the arbitrary-candidate route used in the proof of Lemma 3.1 "
        "becomes a lexicographic candidate scan with complexity O(m*p^2*L); at "
        "the hard preset p=8117, m=8, L=8 its exact eight-seed mean is "
        "246,524,121 candidate tests and 8,874,868,343 finite-field operations "
        "(the final timed 100,000-test prefixes project to 363 seconds), while the "
        "successful O(m*L) reverse-layer evaluator measured 288 operations and "
        "about 19 microseconds."
    ),
    "max_answer_tokens": 25,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON list of m distinct vectors [u,v] in F_p^2, one right-"
        "cluster image for each labelled unmatched vertex of H; coordinates are "
        "integers from 0 through p-1."
    ),
    "bounds": {
        "vectors": "instance m",
        "coordinates_per_vector": 2,
        "coordinate_lower": 0,
        "coordinate_upper": "instance p-1",
        "all_vectors_distinct": True,
        "maximum_atomic_elements": 16,
    },
}

STRUCTURAL_HINT = (
    "Every displayed affine swap layer is a bijection of the two-dimensional finite-field word space."
)
PLACEBO_HINT = (
    "Every displayed finite-field coordinate deserves careful attention when checking the requested embedding."
)

DIFFICULTY = {
    "demo": {"n": 7, "m": 2, "layers": 1},
    "easy": {"n": 2027, "m": 8, "layers": 7},
    "medium": {"n": 4057, "m": 8, "layers": 8},
    "hard": {"n": 8117, "m": 8, "layers": 8},
}

SHIPPING_DIFFICULTY = "hard"

# Populated after the three harness runs.  These are diagnostics only; G9(c)
# is the gate.  Keeping the values in the module makes selftest reproducible.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
}

NOTES = """\
Section 1.7 fixes the exact certificate: a transversal embedding is a pair of
injective maps tau on vertices and sigma on edges, with every mapped edge in
its sigma-colour graph.  Section 1.2 licenses the equivalent 3-uniform
hypergraph view.  Section 3, especially Lemma 3.1 and its proof, fixes the
partial-embedding/candidate-set object used here: already embedded neighbours
and already assigned distinct colours leave candidate images for the remaining
vertices.

The paper's easy regime is a dense regular template.  Lemma 2.2 says typical
vertices and colours have many choices, and the proof of Lemma 3.1 deletes bad
choices and then selects an arbitrary survivor greedily.  This generator does
not pretend that its sparse perfect-matching colour graphs meet those density
hypotheses.  Instead it is Track B and states its actual algorithm: scan F_p^2
for each candidate, or exploit the displayed bijective layers and reverse them.
The former is the mechanical reference route; the latter is the short intended
route.

Plants and random candidates are both uniform distinct vectors of F_p^2.  The
outlier attack chooses the lexicographically smallest vectors, the local greedy
attack inspects only a short neighbourhood of each fixed left image, random
restart samples 256 complete injective maps, and the in-context ansatz reverses
only the final layer.  None receives information unavailable to a solver.  The
reference scan is kept outside attacks because Track B expects it to succeed.
"""


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def _next_prime(n: int) -> int:
    q = max(2, int(n))
    if q > 2 and q % 2 == 0:
        q += 1
    while not _is_prime(q):
        q += 1 if q == 2 else 2
    return q


def _add(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] + y[0]) % p, (x[1] + y[1]) % p)


def _sub(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] - y[0]) % p, (x[1] - y[1]) % p)


def _apply_layer(z: tuple[int, int], layer: list[int], p: int) -> tuple[int, int]:
    """(u,v) -> (v, u+a*v+b), an affine bijection over F_p."""

    a, b = layer
    return (z[1], (z[0] + a * z[1] + b) % p)


def _undo_layer(z: tuple[int, int], layer: list[int], p: int) -> tuple[int, int]:
    a, b = layer
    return ((z[1] - a * z[0] - b) % p, z[0])


def _perm(z: tuple[int, int], layers: list[list[int]], p: int) -> tuple[int, int]:
    for layer in layers:
        z = _apply_layer(z, layer, p)
    return z


def _inverse_perm(z: tuple[int, int], layers: list[list[int]], p: int) -> tuple[int, int]:
    for layer in reversed(layers):
        z = _undo_layer(z, layer, p)
    return z


def _edge_holds(
    left: tuple[int, int],
    right: tuple[int, int],
    colour: tuple[int, int],
    layers: list[list[int]],
    p: int,
) -> bool:
    return _perm(_sub(right, left, p), layers, p) == colour


def _falling(q: int, m: int) -> int:
    out = 1
    for j in range(m):
        out *= q - j
    return out


def _route_operations(m: int, layers: int) -> int:
    # Each inverse layer: multiply, two subtractions, reduction.  Recovering the
    # right image adds two coordinates and reduces both: four further operations.
    return m * (4 * layers + 4)


def make_instance(n: int, seed: int = 0, m: int = 8, layers: int = 5, **params) -> dict:
    """Inverse-generate a partial transversal-matching embedding over F_p^2.

    `n` is the prime modulus p.  The ambient candidate space has p**2 points,
    so increasing n enlarges the haystack while m, the witness length, can stay
    fixed.  No generated instance is solved during construction.
    """

    del params
    p = int(n)
    m = int(m)
    layer_count = int(layers)
    if not _is_prime(p):
        raise ValueError("n must be prime (it is the finite-field modulus p)")
    if not (2 <= m <= 8):
        raise ValueError("m must lie between 2 and 8")
    if p * p < 4 * m:
        raise ValueError("p^2 is too small for the requested matching")
    if not (1 <= layer_count <= 8):
        raise ValueError("layers must lie between 1 and 8")

    rng = random.Random(seed)
    mixers = [[rng.randrange(1, p), rng.randrange(p)] for _ in range(layer_count)]

    left: list[list[int]] = []
    right: list[list[int]] = []
    colours: list[list[int]] = []
    used_left: set[tuple[int, int]] = set()
    used_right: set[tuple[int, int]] = set()
    used_delta: set[tuple[int, int]] = set()

    while len(left) < m:
        x = (rng.randrange(p), rng.randrange(p))
        y = (rng.randrange(p), rng.randrange(p))
        z = _sub(y, x, p)
        if x in used_left or y in used_right or z in used_delta:
            continue
        c = _perm(z, mixers, p)
        used_left.add(x)
        used_right.add(y)
        used_delta.add(z)
        left.append([x[0], x[1]])
        right.append([y[0], y[1]])
        colours.append([c[0], c[1]])

    return {
        "paper": "arXiv:2306.03595",
        "p": p,
        "m": m,
        "layers": mixers,
        "h_vertices": 2 * m,
        "h_edges": [[2 * i, 2 * i + 1] for i in range(m)],
        "left_images": left,
        "required_colours": colours,
        "answer": right,
    }


def render(inst: dict) -> str:
    p = inst["p"]
    m = inst["m"]
    layer_lines = "\n".join(
        f"  {j}: (u,v) -> (v, (u + {a}*v + {b}) mod {p})"
        for j, (a, b) in enumerate(inst["layers"])
    )
    constraint_lines = "\n".join(
        f"  edge {i}: left image L_{x}, required colour {c}"
        for i, (x, c) in enumerate(zip(inst["left_images"], inst["required_colours"]))
    )
    example = [[0, i] for i in range(m)]
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = f"\nHint: {STRUCTURAL_HINT}\n"
    elif mode == "placebo":
        hint = f"\nHint: {PLACEBO_HINT}\n"

    return f"""Complete a partial transversal embedding of a matching.

All arithmetic below is in the finite field F_{p}, represented by the integers
0,...,{p - 1} with reduction modulo {p}.  A vector is an ordered pair [u,v].

The host has two disjoint vertex classes L and R, each indexed by F_{p}^2, and
one graph G_c for every colour c in F_{p}^2.  Define P by applying these layers
in the displayed order, from layer 0 downward:
{layer_lines}

For x,y,c in F_{p}^2, the bipartite edge L_x--R_y belongs to G_c exactly when
P(y-x)=c, where subtraction is coordinatewise modulo {p}.

The target graph H is the matching on labelled vertices 0,...,{2 * m - 1}, with
edges (0,1),(2,3),...,( {2 * m - 2},{2 * m - 1}).  For edge i, target vertex
2i has already been embedded at the displayed L vertex, and that edge has
already been assigned the displayed colour:
{constraint_lines}

The {m} displayed colours and the {m} fixed left images are pairwise distinct.
Complete the embedding by giving, in edge order 0 through {m - 1}, the image
[u_i,v_i] in R of target vertex 2i+1.  Your {m} right images must be pairwise
distinct, and each must make its corresponding edge belong to its assigned
colour graph.  Thus the completed vertex map and edge-colour map are both
injective.  Order matters; repetitions are forbidden; all bounds are inclusive.
{hint}
Give your final answer inside <answer></answer> tags as one JSON list of exactly
{m} integer pairs.  Example syntax:
<answer>{json.dumps(example, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.IGNORECASE | re.DOTALL)


def parse_answer(text: str) -> object | None:
    """Parse the last delimited JSON answer, tolerating prose and code fences."""

    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.IGNORECASE | re.DOTALL)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check a completed transversal embedding without consulting inst['answer']."""

    m = inst["m"]
    p = inst["p"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != m:
        return False, f"expected exactly {m} right-image vectors"

    points: list[tuple[int, int]] = []
    for i, value in enumerate(answer):
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in value)
        ):
            return False, f"right image {i} must be an integer pair"
        if not (0 <= value[0] < p and 0 <= value[1] < p):
            return False, f"right image {i} has a coordinate outside 0..{p - 1}"
        points.append((value[0], value[1]))

    if len(set(points)) != m:
        return False, "right images are not injective"

    for i, right in enumerate(points):
        left = tuple(inst["left_images"][i])
        colour = tuple(inst["required_colours"][i])
        if not _edge_holds(left, right, colour, inst["layers"], p):
            return False, f"edge {i} is not present in its assigned colour graph"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from ordered injective F_p^2 right-image maps."""

    q = inst["p"] ** 2
    ranks = rng.sample(range(q), inst["m"])
    return [[rank // inst["p"], rank % inst["p"]] for rank in ranks]


def search_space(inst: dict) -> int:
    return _falling(inst["p"] ** 2, inst["m"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force small certificate spaces, with a hard 200,000 cap."""

    space = search_space(inst)
    if space > 200_000:
        return None
    p = inst["p"]
    total = 0
    for ranks in itertools.permutations(range(p * p), inst["m"]):
        candidate = [[rank // p, rank % p] for rank in ranks]
        if verify(inst, candidate)[0]:
            total += 1
    return total


def _rank_of_vectors(vectors: list[tuple[int, int]], p: int) -> int:
    nonzero = [v for v in vectors if v != (0, 0)]
    if not nonzero:
        return 0
    a = nonzero[0]
    if any((a[0] * b[1] - a[1] * b[0]) % p for b in nonzero[1:]):
        return 2
    return 1


def _coordinates_in_basis(
    vector: tuple[int, int],
    first: tuple[int, int],
    second: tuple[int, int],
    p: int,
) -> tuple[int, int]:
    det = (first[0] * second[1] - first[1] * second[0]) % p
    inv = pow(det, -1, p)
    return (
        ((vector[0] * second[1] - vector[1] * second[0]) * inv) % p,
        ((-vector[0] * first[1] + vector[1] * first[0]) * inv) % p,
    )


def _canonical_affine_pairs(
    pairs: list[tuple[tuple[int, int], tuple[int, int]]], p: int
) -> tuple:
    """Canonicalise under reordering, two translations, and a common GL(2,p)."""

    best = None
    for x_anchor, _ in pairs:
        for _, z_anchor in pairs:
            shifted = [(_sub(x, x_anchor, p), _sub(z, z_anchor, p)) for x, z in pairs]
            vectors = sorted(set(v for pair in shifted for v in pair if v != (0, 0)))
            rank = _rank_of_vectors(vectors, p)
            forms = []
            if rank == 2:
                for first in vectors:
                    for second in vectors:
                        if (first[0] * second[1] - first[1] * second[0]) % p == 0:
                            continue
                        forms.append(
                            tuple(
                                sorted(
                                    (
                                        _coordinates_in_basis(x, first, second, p),
                                        _coordinates_in_basis(z, first, second, p),
                                    )
                                    for x, z in shifted
                                )
                            )
                        )
            elif rank == 1:
                for first in vectors:
                    component = 0 if first[0] else 1
                    inv = pow(first[component], -1, p)

                    def scalar(v: tuple[int, int]) -> tuple[int, int]:
                        return ((v[component] * inv) % p, 0)

                    forms.append(tuple(sorted((scalar(x), scalar(z)) for x, z in shifted)))
            else:
                forms.append(tuple(sorted(shifted)))
            local = min(forms)
            if best is None or local < best:
                best = local
    assert best is not None
    return best


def canonical_key(inst: dict) -> str:
    """A structural key, never a hash of the seed or rendered statement.

    Colours are first pulled back through P, so merely renaming the colour
    graphs by a different displayed P does not manufacture diversity.  The
    remaining point-pair configuration is canonicalised under constraint
    reordering, independent translations of left images and differences, and a
    common invertible linear relabelling of F_p^2.
    """

    p = inst["p"]
    pairs = []
    for x, c in zip(inst["left_images"], inst["required_colours"]):
        z = _inverse_perm(tuple(c), inst["layers"], p)
        pairs.append((tuple(x), z))
    normal = {
        "p": p,
        "m": inst["m"],
        "configuration": _canonical_affine_pairs(pairs, p),
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the ambient field while keeping the eight-vector witness fixed."""

    out = {k: v for k, v in params.items() if k != "_preset"}
    p = int(out.get("n", 7))
    out["n"] = _next_prime(2 * p + 1)
    out["layers"] = min(8, int(out.get("layers", 1)) + 1)
    out["m"] = min(8, int(out.get("m", 8)))
    return out


def _compact_solve(inst: dict) -> list[list[int]]:
    p = inst["p"]
    answer = []
    for x, c in zip(inst["left_images"], inst["required_colours"]):
        delta = _inverse_perm(tuple(c), inst["layers"], p)
        y = _add(tuple(x), delta, p)
        answer.append([y[0], y[1]])
    return answer


def _reference_scan(inst: dict, max_tests: int | None = None) -> dict:
    """The paper-style mechanical route: scan candidate sets in order.

    With ``max_tests`` this is an honestly timed prefix, not a purported solve.
    The exact full node count is available separately because every candidate
    set is a singleton and the inverse reference algorithm identifies its rank.
    """

    p = inst["p"]
    tested = 0
    answer: list[list[int]] = []
    start = time.perf_counter()
    for x_raw, c_raw in zip(inst["left_images"], inst["required_colours"]):
        x = tuple(x_raw)
        c = tuple(c_raw)
        found = None
        for rank in range(p * p):
            if max_tests is not None and tested >= max_tests:
                elapsed = time.perf_counter() - start
                return {
                    "answer": None,
                    "solved": False,
                    "candidate_tests": tested,
                    "operations": tested * (4 + 4 * len(inst["layers"])),
                    "wall_clock_sec": elapsed,
                    "capped": True,
                }
            tested += 1
            y = (rank // p, rank % p)
            if _edge_holds(x, y, c, inst["layers"], p):
                found = [y[0], y[1]]
                break
        if found is None:
            break
        answer.append(found)
    elapsed = time.perf_counter() - start
    exact_ops = tested * (4 + 4 * len(inst["layers"]))
    ok = len(answer) == inst["m"] and verify(inst, answer)[0]
    return {
        "answer": answer if ok else None,
        "solved": ok,
        "candidate_tests": tested,
        "operations": exact_ops,
        "wall_clock_sec": elapsed,
        "capped": False,
    }


def _reference_inverse(inst: dict) -> dict:
    """Successful Track-B reference algorithm using the displayed bijections."""

    start = time.perf_counter()
    answer = _compact_solve(inst)
    elapsed = time.perf_counter() - start
    return {
        "answer": answer,
        "solved": verify(inst, answer)[0],
        "operations": _route_operations(inst["m"], len(inst["layers"])),
        "wall_clock_sec": elapsed,
    }


def _exact_scan_cost(inst: dict) -> tuple[int, int]:
    """Exact tests/operations the lexicographic scan would execute.

    This derives the unique singleton locations with the successful reference
    inverse; it does not claim that the full scan was timed.
    """

    p = inst["p"]
    answer = _compact_solve(inst)
    tests = sum(y[0] * p + y[1] + 1 for y in answer)
    return tests, tests * (4 + 4 * len(inst["layers"]))


def _attack_outlier(inst: dict) -> bool:
    p = inst["p"]
    candidate = [[i // p, i % p] for i in range(inst["m"])]
    return verify(inst, candidate)[0]


def _attack_greedy_window(inst: dict, window: int = 64) -> bool:
    p = inst["p"]
    q = p * p
    used: set[tuple[int, int]] = set()
    answer = []
    for x_raw, c_raw in zip(inst["left_images"], inst["required_colours"]):
        x = tuple(x_raw)
        c = tuple(c_raw)
        start = (x[0] * p + x[1]) % q
        chosen = None
        for offset in range(window):
            rank = (start + offset) % q
            y = (rank // p, rank % p)
            if y not in used and _edge_holds(x, y, c, inst["layers"], p):
                chosen = y
                break
        if chosen is None:
            return False
        used.add(chosen)
        answer.append([chosen[0], chosen[1]])
    return verify(inst, answer)[0]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x5A17C9E3)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_last_layer_only(inst: dict) -> bool:
    p = inst["p"]
    last = inst["layers"][-1]
    answer = []
    for x_raw, c_raw in zip(inst["left_images"], inst["required_colours"]):
        delta = _undo_layer(tuple(c_raw), last, p)
        y = _add(tuple(x_raw), delta, p)
        answer.append([y[0], y[1]])
    return verify(inst, answer)[0]


def _apply_matrix(
    matrix: tuple[tuple[int, int], tuple[int, int]],
    vector: tuple[int, int],
    p: int,
) -> tuple[int, int]:
    return (
        (matrix[0][0] * vector[0] + matrix[0][1] * vector[1]) % p,
        (matrix[1][0] * vector[0] + matrix[1][1] * vector[1]) % p,
    )


def _relabel_instance(
    inst: dict,
    order: list[int],
    matrix: tuple[tuple[int, int], tuple[int, int]],
    left_shift: tuple[int, int],
    delta_shift: tuple[int, int],
) -> tuple[dict, list[list[int]]]:
    """Carry an instance and its witness through a genuine affine relabelling."""

    out = copy.deepcopy(inst)
    p = inst["p"]
    new_left = []
    new_colours = []
    new_answer = []
    for i in order:
        x = tuple(inst["left_images"][i])
        y = tuple(inst["answer"][i])
        z = _sub(y, x, p)
        xp = _add(_apply_matrix(matrix, x, p), left_shift, p)
        zp = _add(_apply_matrix(matrix, z, p), delta_shift, p)
        yp = _add(xp, zp, p)
        cp = _perm(zp, inst["layers"], p)
        new_left.append([xp[0], xp[1]])
        new_colours.append([cp[0], cp[1]])
        new_answer.append([yp[0], yp[1]])
    out["left_images"] = new_left
    out["required_colours"] = new_colours
    out["answer"] = new_answer
    return out, new_answer


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every named preset and several independent seeds.
    planted_failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 23):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checked += 1
            if not ok:
                planted_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "instances_checked": checked,
        "failures": planted_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)

    # G2: five different corruptions must hit five distinct diagnostics.
    planted = copy.deepcopy(inst["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": [[inst["p"], 0]] + planted[1:],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        corruption_results[name] = {"accepted": ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(not x["accepted"] for x in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: answer is JSON-native and survives realistic surrounding prose/fences.
    blob = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I inverted the layers in reverse order.\n<answer>```json\n{blob}\n```</answer>\n"
    parsed = parse_answer(response)
    json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and json_native,
        "realistic_response_parsed": parsed == inst["answer"],
        "json_native": json_native,
    }

    # G4/G5 density: structure-aware candidates already obey shape, field bounds,
    # and injectivity.  The same 200k shipping samples serve both measurements.
    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(0x230603595)
    start = time.perf_counter()
    for _ in range(sample_total):
        sample_hits += int(verify(inst, random_candidate(inst, sample_rng))[0])
    sample_elapsed = time.perf_counter() - start
    report["G4_guess_resistance"] = {
        "pass": sample_hits / sample_total < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": sample_hits / sample_total,
        "candidate_prior": "uniform ordered injective maps into F_p^2",
        "search_space": search_space(inst),
        "wall_clock_sec": sample_elapsed,
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    # Track-B reference inverse, run completely on eight shipping instances.
    # Also time a real 100k-node prefix of the paper-style candidate scan and
    # derive that scan's exact full node count from the unique decoded targets.
    reference_rows = []
    for seed in range(8):
        ref_inst = make_instance(seed=seed, **ship_params)
        result = _reference_inverse(ref_inst)
        scan_tests, scan_ops = _exact_scan_cost(ref_inst)
        scan_prefix = _reference_scan(ref_inst, max_tests=100_000)
        projected_wall = (
            scan_prefix["wall_clock_sec"] * scan_tests / scan_prefix["candidate_tests"]
        )
        reference_rows.append(
            {
                "seed": seed,
                "solved": result["solved"],
                "operations": result["operations"],
                "wall_clock_sec": result["wall_clock_sec"],
                "mechanical_scan_exact_candidate_tests": scan_tests,
                "mechanical_scan_exact_operations": scan_ops,
                "mechanical_scan_prefix_tests": scan_prefix["candidate_tests"],
                "mechanical_scan_prefix_wall_clock_sec": scan_prefix["wall_clock_sec"],
                "mechanical_scan_projected_wall_clock_sec": projected_wall,
            }
        )
    mean_ops = sum(row["operations"] for row in reference_rows) / len(reference_rows)
    mean_wall = sum(row["wall_clock_sec"] for row in reference_rows) / len(reference_rows)
    mean_scan_tests = sum(
        row["mechanical_scan_exact_candidate_tests"] for row in reference_rows
    ) / len(reference_rows)
    mean_scan_ops = sum(
        row["mechanical_scan_exact_operations"] for row in reference_rows
    ) / len(reference_rows)
    mean_scan_prefix_wall = sum(
        row["mechanical_scan_prefix_wall_clock_sec"] for row in reference_rows
    ) / len(reference_rows)
    mean_scan_projected_wall = sum(
        row["mechanical_scan_projected_wall_clock_sec"] for row in reference_rows
    ) / len(reference_rows)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1
        and sample_hits / sample_total < 1e-6
        and all(row["solved"] for row in reference_rows),
        "shipping_sample_hits": sample_hits,
        "shipping_sample_total": sample_total,
        "shipping_sampled_valid_fraction": sample_hits / sample_total,
        "shipping_exact_valid_answers_by_bijection": 1,
        "shipping_exact_density_numerator": 1,
        "shipping_exact_density_denominator": search_space(inst),
        "demo_exact_solution_count_by_enumeration": demo_count,
        "baseline_reference_mean_operations": mean_ops,
        "baseline_reference_mean_wall_clock_sec": mean_wall,
        "baseline_mechanical_scan_mean_exact_candidate_tests": mean_scan_tests,
        "baseline_mechanical_scan_mean_exact_operations": mean_scan_ops,
        "baseline_mechanical_scan_mean_prefix_wall_clock_sec": mean_scan_prefix_wall,
        "baseline_mechanical_scan_mean_projected_wall_clock_sec": mean_scan_projected_wall,
        "baseline_mechanical_scan_prefix_tests_per_seed": 100_000,
        "baseline_seeds": 8,
    }

    # G6: Track B keeps the successful reference algorithm outside attacks.
    attack_counts = {
        "outlier_lexicographically_smallest": 0,
        "greedy_local_window_64": 0,
        "random_restart_256": 0,
        "in_context_last_layer_inverse": 0,
    }
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **ship_params)
        attack_counts["outlier_lexicographically_smallest"] += int(_attack_outlier(attack_inst))
        attack_counts["greedy_local_window_64"] += int(_attack_greedy_window(attack_inst))
        attack_counts["random_restart_256"] += int(_attack_random_restart(attack_inst, seed))
        attack_counts["in_context_last_layer_inverse"] += int(
            _attack_last_layer_only(attack_inst)
        )
    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attacks.values())
        and all(row["solved"] for row in reference_rows),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "reverse-layer exact evaluator",
            "complexity": "O(m*L) finite-field operations",
            "solves": f"{sum(int(row['solved']) for row in reference_rows)}/8, as expected",
            "mean_operations": mean_ops,
            "mean_wall_clock_sec": mean_wall,
            "per_seed": reference_rows,
        },
        "mechanical_route": {
            "name": "lexicographic candidate-set scan",
            "complexity": "O(m*p^2*L) finite-field operations",
            "mean_exact_candidate_tests": mean_scan_tests,
            "mean_exact_operations": mean_scan_ops,
            "timed_prefix_tests_per_seed": 100_000,
            "mean_timed_prefix_wall_clock_sec": mean_scan_prefix_wall,
            "mean_projected_full_wall_clock_sec": mean_scan_projected_wall,
            "full_scan_timed": False,
        },
        "compact_route": {
            "name": "reverse every affine swap layer",
            "operations": _route_operations(ship_params["m"], ship_params["layers"]),
            "solves": "8/8",
        },
    }

    # G7: double the modulus scale (using the next prime), not the witness.
    doubled = dict(ship_params)
    doubled["n"] = _next_prime(2 * ship_params["n"])
    doubled_start = time.perf_counter()
    doubled_inst = make_instance(seed=2718, **doubled)
    doubled_ok, doubled_why = verify(doubled_inst, doubled_inst["answer"])
    doubled_elapsed = time.perf_counter() - doubled_start
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > ship_params["n"]
        and search_space(doubled_inst) > search_space(inst)
        and len(doubled_inst["answer"]) == len(inst["answer"]),
        "shipping_modulus": ship_params["n"],
        "doubled_modulus": doubled["n"],
        "shipping_space": search_space(inst),
        "doubled_space": search_space(doubled_inst),
        "answer_vectors_before": len(inst["answer"]),
        "answer_vectors_after": len(doubled_inst["answer"]),
        "build_and_verify_wall_clock_sec": doubled_elapsed,
        "verify_reason": doubled_why,
    }

    # G8: order, affine relabelling, and their composition over 20 seeds.
    invariant_checks = 0
    carried_witness_checks = 0
    original_keys = []
    invariance_failures = []
    witness_failures = []
    for seed in range(20):
        key_inst = make_instance(seed=20_000 + seed, **ship_params)
        base_key = canonical_key(key_inst)
        original_keys.append(base_key)
        p = key_inst["p"]
        rr = random.Random(seed ^ 0x8CA11)
        while True:
            matrix = (
                (rr.randrange(p), rr.randrange(p)),
                (rr.randrange(p), rr.randrange(p)),
            )
            if (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) % p:
                break
        left_shift = (rr.randrange(p), rr.randrange(p))
        delta_shift = (rr.randrange(p), rr.randrange(p))
        identity = ((1, 0), (0, 1))
        natural = list(range(key_inst["m"]))
        reversed_order = list(reversed(natural))
        transforms = [
            (reversed_order, identity, (0, 0), (0, 0)),
            (natural, matrix, left_shift, delta_shift),
            (reversed_order, matrix, left_shift, delta_shift),
        ]
        for label, args in zip(("order", "affine", "composed"), transforms):
            changed, carried = _relabel_instance(key_inst, *args)
            invariant_checks += 1
            carried_witness_checks += 1
            if canonical_key(changed) != base_key:
                invariance_failures.append({"seed": seed, "transform": label})
            ok, why = verify(changed, carried)
            if not ok:
                witness_failures.append({"seed": seed, "transform": label, "reason": why})
    report["G8_canonical_key"] = {
        "pass": not invariance_failures
        and not witness_failures
        and len(set(original_keys)) == len(original_keys),
        "invariance_checks": invariant_checks,
        "invariance_failures": invariance_failures,
        "carried_witness_checks": carried_witness_checks,
        "carried_witness_failures": witness_failures,
        "unrelated_instances": len(original_keys),
        "distinct_keys": len(set(original_keys)),
        "transformations": [
            "constraint reordering",
            "common GL(2,p) coordinate change with independent left/difference translations",
            "composition of both",
        ],
    }

    answer_blobs = [
        json.dumps(make_instance(seed=s, **ship_params)["answer"], separators=(",", ":"))
        for s in range(20)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    route_ops = _route_operations(ship_params["m"], ship_params["layers"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and route_ops <= 300
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": copy.deepcopy(G9_ARM_RESULTS),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "too_easy" if hinted.get("solved", 0) else "hardened"
        )
        if hinted.get("attempts", 0)
        else "not_run",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_gates_pass"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
