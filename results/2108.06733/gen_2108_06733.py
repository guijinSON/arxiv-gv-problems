"""Verified strong-identification-code instances from arXiv:2108.06733.

The answer is sampled first.  A dense graph is assembled around a fixed-size
constant-weight family of closed-neighborhood signatures, so the sampled set
is an index-r identification code by construction.  An affine relabelling of
the vertices and same-distribution decoys hide the code without changing it.
"""

from __future__ import annotations

import functools
import hashlib
import heapq
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
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:  # The family is standard-library-only; these helpers are not required.
    from gvlib import exact_matrices, rationals  # type: ignore
except ImportError:  # pragma: no cover - explicitly supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graph given by exact closed-neighborhood bit rows",
        "vertex subset forming a strong identification code",
        "allowed and marked vertex subsets",
    ],
    "verification_operations": [
        "exact bit-set intersection and difference",
        "population count",
        "integer cardinality and membership comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize the repeated directed-difference pattern among marked "
        "vertex labels and use the affine symmetry it exposes; without that "
        "pattern one must solve a large constrained separating-code search."
    ),
    "hardness_basis": (
        "Track B: pseudo-Boolean DPLL with unit/cardinality propagation and "
        "a full-constraint greedy/repair branching heuristic solved 8/8 "
        "shipping instances using an estimated "
        "17,145,069,404 64-bit word operations in 18.00 seconds total; a "
        "complete O(n^2 k) affine-template scan used 17,278,488 modular "
        "image operations in 3.32 seconds total, while the compact "
        "difference-multiplicity route used at most 250 exact modular "
        "operations once the symmetry was seen."
    ),
    "max_answer_tokens": 24,
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
    "demo": {
        "n": 13,
        "code_size": 6,
        "index": 1,
        "pool_size": 6,
        "marker_count": 3,
        "marker_required": 3,
    },
    "easy": {
        "n": 127,
        "code_size": 24,
        "index": 2,
        "pool_size": 48,
        "marker_count": 8,
        "marker_required": 5,
    },
    "medium": {
        "n": 257,
        "code_size": 24,
        "index": 2,
        "pool_size": 80,
        "marker_count": 10,
        "marker_required": 5,
    },
    "hard": {
        "n": 509,
        "code_size": 24,
        "index": 2,
        "pool_size": 120,
        "marker_count": 11,
        "marker_required": 5,
    },
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Directed differences between marked vertex labels have a repeated "
    "multiplicity pattern preserved by affine relabelling."
)
PLACEBO_HINT = (
    "Hint: Careful comparison of the closed-neighborhood rows helps prevent "
    "small indexing and transcription mistakes."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered set written as a JSON list of exactly k distinct graph "
        "vertices, all from the displayed allowed pool and containing exactly "
        "s displayed marked vertices; the list is canonically increasing."
    ),
    "bounds": {
        "length": "code_size (24 at shipping)",
        "vertex_min": 0,
        "vertex_max": "n-1",
        "allowed_pool": "pool_size (120 at shipping)",
        "marked_required": "marker_required (5 at shipping)",
        "candidate_count": (
            "C(marker_count,marker_required) * "
            "C(pool_size-marker_count,code_size-marker_required)"
        ),
    },
}

# Filled from the script-owned hardening transcripts after those runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "unavailable_api_error",
}

NOTES = r"""
Paper definition and construction.  Section 2, Definition 1 says that C is an
index-r identification code when, for every ordered pair v != u,
|(N[v] \ N[u]) intersect C| >= r.  The order matters: both (v,u) and (u,v)
are checked.  The paragraph following (2.2) observes that this also makes the
whole vertex set a code whenever the graph has the r-strong-neighborhood
property.  Theorem 1 assumes the stronger (r+d+1)-property and constructs a
smaller code by sampling Z, declaring vertices bad, and adjoining the closed
neighborhoods of all bad vertices.  Section 3, Lemma 3 and Theorem 2 construct
bounded-degree strong-neighborhood graphs probabilistically.

Step-0 decision.  Neither Theorem 1 nor Theorem 2 is a computational hardness
result, so this family cannot honestly claim Track A.  The proof of Theorem 1
also gives a direct polynomial scan: for a chosen Z, inspect every ordered
vertex pair and repair every bad vertex.  Thus the paper itself rules out a
Track-A interpretation of that certificate.  Track B remains meaningful here:
the generated distribution has a complete polynomial affine-template scan,
reported as the successful reference algorithm, while its short route is a
joint modular-difference invariant that is not an individual vertex outlier.

Generation.  Before any graph is built, the base answer C0={0,...,k-1} is
fixed.  Every graph vertex receives a distinct constant-weight k-bit signature;
any ordered pair of signatures differs from 1 to 0 in at least r positions.
For the k code vertices, the signature rows are cyclic translates of a
symmetric mask containing the diagonal, so they define an undirected graph.
The remaining edges are unbiased deterministic coin flips.  Consequently the
signature of v is exactly N[v] intersect C0, and Definition 1 verifies C0 by
construction.  Sampling x -> a*x+b modulo the prime n carries the graph and
certificate to the displayed labels.  Answer and decoy vertices therefore
have identical one-vertex label marginals.  Marker decoys are rejected only on
an affine-invariant joint difference statistic.

Easy cases and attacks.  The demo pool is exactly the six-vertex answer and is
intentionally hand scale.  The ladder holds the 24-entry witness fixed while
increasing graph order and pool crowding.  Degree outliers are neutralized by
dense unbiased noncode edges and balanced constant-weight signatures.  The
greedy attack uses only shape-valid choices and optimizes a sample of directed
separation deficits.  Random restarts sample the exact certificate language.
The by-hand ansatz takes the smallest labels satisfying the explicit shape
constraints and therefore has no access to the joint modular pattern.  The
domain-standard reference is pseudo-Boolean DPLL with unit and cardinality
propagation; its branching heuristic greedily covers every ordered-pair
constraint using packed bit sets and repairs residual defects by legal
one-vertex swaps.  A second, complete algorithm for this generated distribution
exhausts affine images and checks the same native graph predicate as verify().

Canonicalization.  The same instance permits arbitrary graph-vertex
renumbering and reordering of the pool and marker lists.  canonical_key uses
isomorphism-invariant one-dimensional color refinement initialized by those
two distinguished subsets.  Random dense instances individualize; in the
unlikely non-discrete case the key falls back to the stable color quotient,
which is the strongest cheap invariant claimed here, not a full GI solver.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_JSON_LIST_RE = re.compile(r"\[[\s\d,+-]*\]", re.S)
_ENUMERATION_CAP = 200_000


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    factor = 3
    while factor <= limit:
        if value % factor == 0:
            return False
        factor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(3, value | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _iter_bits(mask: int):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def _rotate_mask(mask: int, shift: int, width: int) -> int:
    result = 0
    for bit in _iter_bits(mask):
        result |= 1 << ((bit + shift) % width)
    return result


def _base_code_mask(code_size: int) -> int:
    if code_size == 6:
        offsets = (0, 1, 5)
    elif code_size == 24:
        offsets = (0, 1, 3, 5, 7, 9, 12, 15, 17, 19, 21, 23)
    else:  # The explicit symmetric masks are part of the construction.
        raise ValueError("code_size must be 6 or 24")
    return sum(1 << value for value in offsets)


def _validate_parameters(
    n: int,
    code_size: int,
    index: int,
    pool_size: int,
    marker_count: int,
    marker_required: int,
) -> None:
    values = (n, code_size, index, pool_size, marker_count, marker_required)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("all parameters must be integers")
    if not _is_prime(n) or n <= code_size:
        raise ValueError("n must be prime and strictly larger than code_size")
    if code_size not in (6, 24):
        raise ValueError("code_size must be 6 or 24")
    expected_index = 1 if code_size == 6 else 2
    if index != expected_index:
        raise ValueError(f"index must be {expected_index} for this code_size")
    expected_markers = 3 if code_size == 6 else 5
    if marker_required != expected_markers:
        raise ValueError(
            f"marker_required must be {expected_markers} for this code_size"
        )
    if not (code_size <= pool_size <= n):
        raise ValueError("pool_size must satisfy code_size <= pool_size <= n")
    if not (marker_required <= marker_count <= pool_size - code_size + marker_required):
        raise ValueError("marker_count leaves too few marked or unmarked decoys")


@functools.lru_cache(maxsize=16)
def _build_base_rows(n: int, code_size: int, index: int) -> tuple[int, ...]:
    """Construct a graph for which range(code_size) is a code by identity."""
    weight = _base_code_mask(code_size).bit_count()
    first_mask = _base_code_mask(code_size)
    signatures = [
        _rotate_mask(first_mask, shift, code_size)
        for shift in range(code_size)
    ]

    # Fixed per-size randomness makes seed affect only the certificate-preserving
    # relabelling and decoys, not whether a graph happens to verify.
    rng = random.Random(0x51D3A7 + n * 1009 + code_size * 9176 + index)
    attempts = 0
    while len(signatures) < n:
        attempts += 1
        if attempts > 2_000_000:
            raise RuntimeError("constant-weight signature packing exhausted")
        candidate = sum(
            1 << bit for bit in rng.sample(range(code_size), weight)
        )
        if all(
            (candidate & ~other).bit_count() >= index
            and (other & ~candidate).bit_count() >= index
            for other in signatures
        ):
            signatures.append(candidate)

    rows = [1 << vertex for vertex in range(n)]
    # Signature incidence supplies every edge with at least one code endpoint.
    for vertex, signature in enumerate(signatures):
        for code_vertex in _iter_bits(signature):
            if vertex != code_vertex:
                rows[vertex] |= 1 << code_vertex
                rows[code_vertex] |= 1 << vertex

    # All remaining edges are unbiased, making code and noncode degrees overlap.
    for left in range(code_size, n):
        for right in range(left + 1, n):
            if rng.getrandbits(1):
                rows[left] |= 1 << right
                rows[right] |= 1 << left

    # Internal construction assertions are cheap and make the identity explicit.
    code_mask = (1 << code_size) - 1
    for vertex, signature in enumerate(signatures):
        if rows[vertex] & code_mask != signature:
            raise AssertionError("closed-neighborhood signature construction failed")
    return tuple(rows)


def _affine_relabel_rows(
    rows: tuple[int, ...], multiplier: int, translation: int
) -> tuple[list[int], list[int]]:
    n = len(rows)
    mapping = [
        (multiplier * vertex + translation) % n for vertex in range(n)
    ]
    relabelled = [0] * n
    for old_vertex, old_row in enumerate(rows):
        new_row = 0
        for old_neighbor in _iter_bits(old_row):
            new_row |= 1 << mapping[old_neighbor]
        relabelled[mapping[old_vertex]] = new_row
    return relabelled, mapping


def _difference_counts(values: set[int], modulus: int) -> dict[int, int]:
    counts: dict[int, int] = {}
    for left in values:
        for right in values:
            if left != right:
                difference = (right - left) % modulus
                counts[difference] = counts.get(difference, 0) + 1
    return counts


def _tight_probe_pairs(rows: list[int], pool: set[int], limit: int = 256):
    """Put the most restrictive native constraints first; exact checking follows."""
    pool_mask = sum(1 << value for value in pool)
    n = len(rows)
    return [
        [left, right]
        for _, left, right in heapq.nsmallest(
            limit,
            (
                ((rows[left] & ~rows[right] & pool_mask).bit_count(), left, right)
                for left in range(n)
                for right in range(n)
                if left != right
            ),
        )
    ]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate and affine-transport a known strong code."""
    code_size = params.pop("code_size", 24)
    index = params.pop("index", 2)
    pool_size = params.pop("pool_size", min(n, 120))
    marker_count = params.pop("marker_count", 11)
    marker_required = params.pop("marker_required", 5)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(
        n, code_size, index, pool_size, marker_count, marker_required
    )
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    multiplier = rng.randrange(1, n)
    translation = rng.randrange(n)
    base_rows = _build_base_rows(n, code_size, index)
    rows, mapping = _affine_relabel_rows(
        base_rows, multiplier, translation
    )
    answer_set = {mapping[value] for value in range(code_size)}

    all_decoys = [value for value in range(n) if value not in answer_set]
    pool_decoys = rng.sample(all_decoys, pool_size - code_size)
    pool_set = answer_set | set(pool_decoys)

    planted_marker_count = marker_required
    planted_markers = {
        mapping[value] for value in range(planted_marker_count)
    }
    if marker_count == marker_required:
        marker_set = set(planted_markers)
    else:
        marker_set = set()
        # The condition is joint and affine-invariant: +/- multiplier are the
        # unique most repeated directed differences of the marker set.
        for _ in range(50_000):
            marker_set = set(planted_markers)
            marker_set.update(
                rng.sample(pool_decoys, marker_count - marker_required)
            )
            counts = _difference_counts(marker_set, n)
            maximum = max(counts.values())
            maximizers = {
                difference
                for difference, count in counts.items()
                if count == maximum
            }
            if maximum == marker_required - 1 and maximizers == {
                multiplier,
                (-multiplier) % n,
            }:
                break
        else:
            raise RuntimeError("could not draw marker decoys without a false signal")

    return {
        "n": n,
        "index": index,
        "code_size": code_size,
        "pool": sorted(pool_set),
        "markers": sorted(marker_set),
        "marker_required": marker_required,
        "closed_rows": rows,
        "check_pairs": _tight_probe_pairs(rows, pool_set),
        "answer": sorted(answer_set),
    }


def render(inst: dict) -> str:
    n = inst["n"]
    width = (n + 3) // 4
    format_example = list(range(inst["code_size"]))
    row_lines = "\n".join(
        f"{vertex}: {row:0{width}x}"
        for vertex, row in enumerate(inst["closed_rows"])
    )
    statement = f"""Find a strong identification code in a finite graph.

Definitions and exact conventions:
- The graph is simple and undirected, with vertices 0 through {n - 1}.
- N[v] is the closed neighborhood of v: vertex v itself together with every vertex adjacent to v.
- A vertex set C is an identification code of index r when, for every ORDERED pair of distinct vertices (v,u), at least r vertices of C lie in N[v] but not in N[u].  Thus both orders (v,u) and (u,v) are required.
- Here r = {inst['index']}.
- The graph is encoded below by one hexadecimal bit row for every N[v].  In row v, bit j (the coefficient of 2^j, with bit 0 the rightmost bit) is 1 exactly when j belongs to N[v].  Leading zeroes are included.  Every row includes its diagonal bit v.

Closed-neighborhood rows:
{row_lines}

Answer constraints:
- Return exactly {inst['code_size']} DISTINCT vertex numbers from this allowed pool:
  {inst['pool']}
- Exactly {inst['marker_required']} returned vertices must belong to this marked subset:
  {inst['markers']}
- The answer is a set: order has no mathematical meaning and repetitions are forbidden.  Write it as one increasing JSON list.
- Every integer endpoint is inclusive: valid graph vertices range from 0 through {n - 1}.

Give your final answer inside <answer></answer> tags, as one JSON array of exactly {inst['code_size']} distinct integers in increasing order.
Example format (not necessarily a solution): <answer>{format_example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.search(text)
    candidates = [tagged.group(1)] if tagged else []
    if not candidates:
        candidates.extend(match.group(0) for match in _JSON_LIST_RE.finditer(text))
    for candidate in reversed(candidates):
        try:
            value = json.loads(candidate.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        ):
            return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    expected = inst["code_size"]
    if len(answer) != expected:
        return False, f"wrong length: expected {expected}, got {len(answer)}"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every answer entry must be an integer"
    n = inst["n"]
    if any(value < 0 or value >= n for value in answer):
        return False, f"vertex out of range: valid range is 0 through {n - 1}"
    if len(set(answer)) != len(answer):
        return False, "answer vertices must be distinct"
    pool = set(inst["pool"])
    if any(value not in pool for value in answer):
        return False, "answer contains a vertex outside the allowed pool"
    marker_hits = len(set(answer) & set(inst["markers"]))
    if marker_hits != inst["marker_required"]:
        return (
            False,
            "wrong marked count: expected "
            f"{inst['marker_required']}, got {marker_hits}",
        )

    code_mask = sum(1 << value for value in answer)
    rows = inst["closed_rows"]
    required = inst["index"]
    for left, right in inst.get("check_pairs", ()):
        count = (rows[left] & ~rows[right] & code_mask).bit_count()
        if count < required:
            return (
                False,
                "ordered pair "
                f"({left},{right}) has only {count} code vertices in "
                f"N[{left}] \\ N[{right}]; need {required}",
            )
    for left, left_row in enumerate(rows):
        for right, right_row in enumerate(rows):
            if left == right:
                continue
            count = (left_row & ~right_row & code_mask).bit_count()
            if count < required:
                return (
                    False,
                    "ordered pair "
                    f"({left},{right}) has only {count} code vertices in "
                    f"N[{left}] \\ N[{right}]; need {required}",
                )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    markers = list(inst["markers"])
    marker_set = set(markers)
    unmarked = [value for value in inst["pool"] if value not in marker_set]
    chosen = rng.sample(markers, inst["marker_required"])
    chosen.extend(
        rng.sample(
            unmarked,
            inst["code_size"] - inst["marker_required"],
        )
    )
    return sorted(chosen)


def search_space(inst: dict) -> int:
    marked = len(inst["markers"])
    unmarked = len(inst["pool"]) - marked
    need_marked = inst["marker_required"]
    need_unmarked = inst["code_size"] - need_marked
    return math.comb(marked, need_marked) * math.comb(unmarked, need_unmarked)


def enumerate_all(inst: dict):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    markers = list(inst["markers"])
    marker_set = set(markers)
    unmarked = [value for value in inst["pool"] if value not in marker_set]
    total = 0
    for marked_part in itertools.combinations(markers, inst["marker_required"]):
        for unmarked_part in itertools.combinations(
            unmarked,
            inst["code_size"] - inst["marker_required"],
        ):
            candidate = sorted(marked_part + unmarked_part)
            if verify(inst, candidate)[0]:
                total += 1
    return total


def _stable_colors(inst: dict) -> tuple[list[int], bool]:
    n = inst["n"]
    pool = set(inst["pool"])
    markers = set(inst["markers"])
    colors = [2 if v in markers else 1 if v in pool else 0 for v in range(n)]
    rows = inst["closed_rows"]
    for _ in range(8):
        signatures = []
        for vertex in range(n):
            neighbor_colors = sorted(
                colors[other]
                for other in _iter_bits(rows[vertex] & ~(1 << vertex))
            )
            signatures.append((colors[vertex], tuple(neighbor_colors)))
        palette = {
            signature: number
            for number, signature in enumerate(sorted(set(signatures)))
        }
        new_colors = [palette[signature] for signature in signatures]
        if new_colors == colors:
            break
        colors = new_colors
        if len(set(colors)) == n:
            return colors, True
    return colors, len(set(colors)) == n


def canonical_key(inst: dict) -> str:
    """Invariant under arbitrary graph-vertex renumbering and list ordering."""
    colors, discrete = _stable_colors(inst)
    rows = inst["closed_rows"]
    n = inst["n"]
    digest = hashlib.sha256()
    digest.update(
        f"sic-v1:{n}:{inst['index']}:{inst['code_size']}:".encode("ascii")
    )
    if discrete:
        order = sorted(range(n), key=lambda vertex: colors[vertex])
        categories = []
        pool = set(inst["pool"])
        markers = set(inst["markers"])
        for vertex in order:
            categories.append(2 if vertex in markers else 1 if vertex in pool else 0)
        digest.update(bytes(categories))
        packed = 0
        used = 0
        for position, left in enumerate(order):
            for right in order[position + 1 :]:
                packed = (packed << 1) | ((rows[left] >> right) & 1)
                used += 1
                if used == 8:
                    digest.update(bytes([packed]))
                    packed = 0
                    used = 0
        if used:
            digest.update(bytes([packed << (8 - used)]))
    else:
        # Stable color quotient: an honest strongest-cheap-invariant fallback.
        classes: dict[int, list[int]] = {}
        for vertex, color in enumerate(colors):
            classes.setdefault(color, []).append(vertex)
        digest.update(json.dumps(sorted(map(len, classes.values()))).encode("ascii"))
        quotient = []
        for left_color in sorted(classes):
            for right_color in sorted(classes):
                edges = 0
                for left in classes[left_color]:
                    edges += sum(
                        (rows[left] >> right) & 1
                        for right in classes[right_color]
                        if left != right
                    )
                quotient.append(edges)
        digest.update(json.dumps(quotient, separators=(",", ":")).encode("ascii"))
    return digest.hexdigest()


def escalate(params: dict):
    harder = dict(params)
    n = harder["n"]
    pool_size = harder["pool_size"]
    if pool_size < n:
        new_pool = min(n, max(pool_size + 1, (pool_size * 3) // 2))
        # Preserve enough unmarked positions for the fixed-length witness.
        harder["pool_size"] = new_pool
        return harder
    new_n = _next_prime(2 * n + 1)
    harder["n"] = new_n
    harder["pool_size"] = min(new_n, max(pool_size + 1, (pool_size * 3) // 2))
    return harder


def _compact_recover(inst: dict) -> tuple[list[int] | None, int]:
    """Construction-aware short route; count exact modular operations."""
    n = inst["n"]
    markers = set(inst["markers"])
    pool = set(inst["pool"])
    operations = 0
    counts: dict[int, int] = {}
    for left in markers:
        for right in markers:
            if left == right:
                continue
            difference = (right - left) % n
            operations += 1
            counts[difference] = counts.get(difference, 0) + 1
    maximum = max(counts.values())
    steps = [value for value, count in counts.items() if count == maximum]
    prefix = inst["marker_required"]
    for step in steps:
        for start in markers:
            predecessor = (start - step) % n
            operations += 1
            if predecessor in markers:
                continue
            run = []
            for offset in range(prefix):
                run.append((start + offset * step) % n)
                operations += 1
            if not all(value in markers for value in run):
                continue
            candidate = []
            for offset in range(inst["code_size"]):
                candidate.append((start + offset * step) % n)
                operations += 1
            candidate = sorted(candidate)
            if (
                set(candidate) <= pool
                and len(set(candidate) & markers) == inst["marker_required"]
                and verify(inst, candidate)[0]
            ):
                return candidate, operations
    return None, operations


def _reference_affine_scan(inst: dict) -> tuple[list[int] | None, int, int]:
    """Complete polynomial scan of affine images of the base code template."""
    n = inst["n"]
    k = inst["code_size"]
    pool = set(inst["pool"])
    markers = set(inst["markers"])
    operations = 0
    candidates = 0
    for step in range(1, n):
        for start in range(n):
            candidates += 1
            candidate = []
            for offset in range(k):
                candidate.append((start + step * offset) % n)
                operations += 1
            candidate = sorted(candidate)
            candidate_set = set(candidate)
            if not candidate_set <= pool:
                continue
            if len(candidate_set & markers) != inst["marker_required"]:
                continue
            if verify(inst, candidate)[0]:
                return candidate, operations, candidates
    return None, operations, candidates


def _reference_csp_greedy_repair(
    inst: dict, max_repair_passes: int = 32
) -> tuple[list[int] | None, dict[str, int]]:
    """Domain-standard full-constraint greedy selection plus one-swap repair.

    One packed bit position represents one ordered vertex pair.  The bit set for
    a pool vertex records exactly the pair constraints that selecting that
    vertex covers.  Greedy maximizes newly supplied coverage units; a
    best-improvement legal swap then repairs any remaining deficient pairs.
    The method is polynomial for a fixed number of repair passes and uses no
    knowledge of the affine planting map.
    """
    n = inst["n"]
    rows = inst["closed_rows"]
    pool = list(inst["pool"])
    markers = set(inst["markers"])
    full_vertices = (1 << n) - 1
    word_width = (n * n + 63) // 64
    wide_operations = 0

    coverage: dict[int, int] = {}
    for vertex in pool:
        neighborhood = rows[vertex]
        complement = full_vertices ^ neighborhood
        packed = 0
        # Undirectedness makes rows[vertex] the set of left endpoints whose
        # closed neighborhoods contain this candidate vertex.
        for left in _iter_bits(neighborhood):
            packed |= complement << (left * n)
            wide_operations += 2  # one shift and one OR
        coverage[vertex] = packed

    target = n * (n - 1)

    def score(selected: list[int]) -> int:
        nonlocal wide_operations
        covered_once = 0
        covered_twice = 0
        for vertex in selected:
            bits = coverage[vertex]
            covered_twice |= covered_once & bits
            covered_once |= bits
            wide_operations += 3
        wide_operations += 1  # population count
        return covered_twice.bit_count()

    selected: list[int] = []
    covered_once = 0
    covered_twice = 0
    marked_used = 0
    greedy_evaluations = 0
    for position in range(inst["code_size"]):
        remaining_slots = inst["code_size"] - position
        marked_needed = inst["marker_required"] - marked_used
        eligible = [
            vertex
            for vertex in pool
            if vertex not in selected
            and not (vertex in markers and marked_needed <= 0)
            and not (vertex not in markers and marked_needed == remaining_slots)
        ]
        if not eligible:
            return None, {
                "wide_bit_operations": wide_operations,
                "estimated_64bit_word_operations": wide_operations * word_width,
                "greedy_evaluations": greedy_evaluations,
                "swap_evaluations": 0,
                "repair_passes": 0,
            }
        vertex = max(
            eligible,
            key=lambda value: (
                (coverage[value] & ~covered_twice).bit_count(),
                -value,
            ),
        )
        greedy_evaluations += len(eligible)
        wide_operations += 3 * len(eligible)
        bits = coverage[vertex]
        covered_twice |= covered_once & bits
        covered_once |= bits
        wide_operations += 3
        selected.append(vertex)
        marked_used += vertex in markers

    current_score = score(selected)
    swap_evaluations = 0
    repair_passes = 0
    while current_score < target and repair_passes < max_repair_passes:
        repair_passes += 1
        best_score = current_score
        best_swap = None
        unselected = [vertex for vertex in pool if vertex not in selected]
        for old in selected:
            for new in unselected:
                if (old in markers) != (new in markers):
                    continue
                trial = [vertex for vertex in selected if vertex != old]
                trial.append(new)
                trial_score = score(trial)
                swap_evaluations += 1
                if trial_score > best_score:
                    best_score = trial_score
                    best_swap = (old, new)
        if best_swap is None:
            break
        selected.remove(best_swap[0])
        selected.append(best_swap[1])
        current_score = best_score

    answer = sorted(selected) if current_score == target else None
    stats = {
        "wide_bit_operations": wide_operations,
        "estimated_64bit_word_operations": wide_operations * word_width,
        "greedy_evaluations": greedy_evaluations,
        "swap_evaluations": swap_evaluations,
        "repair_passes": repair_passes,
        "final_deficient_pairs": target - current_score,
    }
    return answer, stats


def _reference_pb_dpll(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Pseudo-Boolean DPLL with exact-cardinality and unit propagation.

    The full-constraint greedy/repair solution is used only as the branching
    heuristic and preferred phase.  The DPLL layer independently enforces the
    two cardinality equations and every directed-difference covering
    inequality; if a preferred branch were wrong it would backtrack.
    """
    preferred, stats = _reference_csp_greedy_repair(inst)
    pool = list(inst["pool"])
    pool_mask = sum(1 << vertex for vertex in pool)
    marker_mask = sum(1 << vertex for vertex in inst["markers"])
    rows = inst["closed_rows"]
    constraints = [
        rows[left] & ~rows[right] & pool_mask
        for left in range(inst["n"])
        for right in range(inst["n"])
        if left != right
    ]
    preferred_set = set(preferred or ())
    order = sorted(pool, key=lambda vertex: (vertex not in preferred_set, vertex))
    nodes = 0
    constraint_scans = 0
    propagations = 0

    def propagate(true_mask: int, false_mask: int):
        nonlocal constraint_scans, propagations
        while True:
            old_true, old_false = true_mask, false_mask
            undecided = pool_mask & ~(true_mask | false_mask)
            selected = (true_mask & pool_mask).bit_count()
            possible = selected + undecided.bit_count()
            if selected > inst["code_size"] or possible < inst["code_size"]:
                return None
            if selected == inst["code_size"]:
                propagations += undecided.bit_count()
                false_mask |= undecided
            elif possible == inst["code_size"]:
                propagations += undecided.bit_count()
                true_mask |= undecided

            undecided_marked = marker_mask & pool_mask & ~(true_mask | false_mask)
            selected_marked = (true_mask & marker_mask).bit_count()
            possible_marked = selected_marked + undecided_marked.bit_count()
            if (
                selected_marked > inst["marker_required"]
                or possible_marked < inst["marker_required"]
            ):
                return None
            if selected_marked == inst["marker_required"]:
                propagations += undecided_marked.bit_count()
                false_mask |= undecided_marked
            elif possible_marked == inst["marker_required"]:
                propagations += undecided_marked.bit_count()
                true_mask |= undecided_marked

            assigned = true_mask | false_mask
            for constraint in constraints:
                constraint_scans += 1
                selected_here = (constraint & true_mask).bit_count()
                if selected_here >= inst["index"]:
                    continue
                undecided_here = constraint & ~assigned
                available = undecided_here.bit_count()
                if selected_here + available < inst["index"]:
                    return None
                if selected_here + available == inst["index"]:
                    true_mask |= undecided_here
                    assigned |= undecided_here
                    propagations += undecided_here.bit_count()

            if true_mask == old_true and false_mask == old_false:
                return true_mask, false_mask

    def search(true_mask: int, false_mask: int):
        nonlocal nodes
        nodes += 1
        state = propagate(true_mask, false_mask)
        if state is None:
            return None
        true_mask, false_mask = state
        assigned = true_mask | false_mask
        if assigned & pool_mask == pool_mask:
            answer = sorted(_iter_bits(true_mask & pool_mask))
            return answer if verify(inst, answer)[0] else None
        vertex = next(value for value in order if not (assigned >> value) & 1)
        bit = 1 << vertex
        phases = (True, False) if vertex in preferred_set else (False, True)
        for phase in phases:
            result = search(
                true_mask | bit if phase else true_mask,
                false_mask if phase else false_mask | bit,
            )
            if result is not None:
                return result
        return None

    answer = search(0, 0)
    stats = dict(stats)
    stats.update(
        {
            "dpll_nodes": nodes,
            "constraint_scans": constraint_scans,
            "unit_propagations": propagations,
        }
    )
    return answer, stats


def _attack_outlier_degree(inst: dict):
    rows = inst["closed_rows"]
    markers = set(inst["markers"])
    marked = sorted(markers, key=lambda v: (-rows[v].bit_count(), v))
    unmarked = sorted(
        (v for v in inst["pool"] if v not in markers),
        key=lambda v: (-rows[v].bit_count(), v),
    )
    return sorted(
        marked[: inst["marker_required"]]
        + unmarked[: inst["code_size"] - inst["marker_required"]]
    )


def _attack_greedy_separator(inst: dict):
    n = inst["n"]
    rows = inst["closed_rows"]
    rng = random.Random(0x6A33 + n)
    ordered_pairs = []
    while len(ordered_pairs) < min(512, n * (n - 1)):
        left = rng.randrange(n)
        right = rng.randrange(n)
        if left != right and (left, right) not in ordered_pairs:
            ordered_pairs.append((left, right))
    deficits = [inst["index"]] * len(ordered_pairs)
    markers = set(inst["markers"])
    chosen: list[int] = []
    marked_used = 0
    for position in range(inst["code_size"]):
        remaining_slots = inst["code_size"] - position
        need_marked = inst["marker_required"] - marked_used
        eligible = []
        for vertex in inst["pool"]:
            if vertex in chosen:
                continue
            is_marked = vertex in markers
            if is_marked and need_marked <= 0:
                continue
            if not is_marked and need_marked == remaining_slots:
                continue
            score = 0
            bit = 1 << vertex
            for pair_index, (left, right) in enumerate(ordered_pairs):
                if deficits[pair_index] > 0 and rows[left] & bit and not rows[right] & bit:
                    score += 1
            eligible.append((score, -vertex, vertex))
        if not eligible:
            break
        vertex = max(eligible)[2]
        chosen.append(vertex)
        if vertex in markers:
            marked_used += 1
        bit = 1 << vertex
        for pair_index, (left, right) in enumerate(ordered_pairs):
            if deficits[pair_index] > 0 and rows[left] & bit and not rows[right] & bit:
                deficits[pair_index] -= 1
    return sorted(chosen)


def _attack_lexicographic_by_hand(inst: dict):
    """The simplest shape-aware no-tool ansatz: take the smallest legal labels."""
    marker_set = set(inst["markers"])
    marked = sorted(marker_set)[: inst["marker_required"]]
    unmarked = sorted(value for value in inst["pool"] if value not in marker_set)
    unmarked = unmarked[: inst["code_size"] - inst["marker_required"]]
    return sorted(marked + unmarked)


def _permuted_instance(inst: dict, permutation: list[int]) -> dict:
    n = inst["n"]
    new_rows = [0] * n
    for old_vertex, old_row in enumerate(inst["closed_rows"]):
        new_row = 0
        for old_neighbor in _iter_bits(old_row):
            new_row |= 1 << permutation[old_neighbor]
        new_rows[permutation[old_vertex]] = new_row
    return {
        "n": n,
        "index": inst["index"],
        "code_size": inst["code_size"],
        "pool": [permutation[value] for value in reversed(inst["pool"])],
        "markers": [permutation[value] for value in reversed(inst["markers"])],
        "marker_required": inst["marker_required"],
        "closed_rows": new_rows,
        "check_pairs": [
            [permutation[left], permutation[right]]
            for left, right in inst.get("check_pairs", ())
        ],
        "answer": sorted(permutation[value] for value in inst["answer"]),
    }


def _answer_size(answer: list[int]) -> tuple[int, int, int]:
    serialised = json.dumps(answer, separators=(",", ":"))
    chars = len(serialised)
    tokens = math.ceil(chars / 4)
    return chars, tokens, len(answer)


def selftest() -> dict:
    report: dict[str, object] = {}

    # G1: every named preset, several independent affine transports.
    planted_ok = 0
    compact_ok = 0
    compact_operations = []
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if ok:
                planted_ok += 1
            else:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            recovered, operations = _compact_recover(inst)
            if recovered is not None and verify(inst, recovered)[0]:
                compact_ok += 1
                compact_operations.append(operations)
    report["G1_planted_verifies"] = {
        "pass": planted_ok == 12 and compact_ok == 12,
        "planted_verified": planted_ok,
        "compact_verified": compact_ok,
        "attempts": 12,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    corruption_inst = make_instance(seed=910, **shipping)
    planted = list(corruption_inst["answer"])
    pool = set(corruption_inst["pool"])
    markers = set(corruption_inst["markers"])
    corruptions: dict[str, object] = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate": planted[:-1] + [planted[0]],
        "out_of_range": planted[:-1] + [corruption_inst["n"]],
    }
    outside = next(value for value in range(corruption_inst["n"]) if value not in pool)
    corruptions["outside_pool"] = planted[:-1] + [outside]
    replacement = None
    for old in planted:
        if old in markers:
            continue
        for new in sorted(pool - set(planted) - markers):
            trial = sorted((set(planted) - {old}) | {new})
            if not verify(corruption_inst, trial)[0]:
                replacement = trial
                break
        if replacement is not None:
            break
    corruptions["swap_one"] = replacement if replacement is not None else planted[:-1]
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(corruption_inst, candidate)
        reasons[name] = {"rejected": not ok, "reason": reason}
    required_names = ("drop_one", "swap_one", "duplicate", "empty", "out_of_range")
    distinct_reasons = {
        reasons[name]["reason"] for name in required_names
    }
    report["G2_rejects_corruption"] = {
        "pass": all(reasons[name]["rejected"] for name in reasons)
        and len(distinct_reasons) == len(required_names),
        "cases": reasons,
        "distinct_required_reasons": len(distinct_reasons),
    }

    tagged_text = (
        "I checked the ordered pairs.\n```json\n<answer>"
        + json.dumps(planted)
        + "</answer>\n```\nThat is my final set."
    )
    fenced_text = "Reasoning omitted.\n```json\n" + json.dumps(planted) + "\n```"
    tagged_parsed = parse_answer(tagged_text)
    fenced_parsed = parse_answer(fenced_text)
    report["G3_round_trip"] = {
        "pass": tagged_parsed == planted and fenced_parsed == planted,
        "tagged": tagged_parsed == planted,
        "fenced": fenced_parsed == planted,
        "json_native": json.loads(json.dumps(planted)) == planted,
    }

    # G4 and shipping density use the same structure-aware sample.
    density_inst = make_instance(seed=424242, **shipping)
    guess_rng = random.Random(0xC0DEC0DE)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(density_inst, guess_rng)
        if verify(density_inst, candidate)[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_start
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(density_inst),
        "structure_aware": True,
        "wall_clock_sec": guess_elapsed,
    }

    attack_results = {
        "outlier_degree": {"successes": 0, "attempts": 8},
        "greedy_sampled_separator": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "lexicographic_by_hand": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    reference_wide_operations = 0
    reference_word_operations = 0
    reference_greedy_evaluations = 0
    reference_swap_evaluations = 0
    reference_repair_passes = 0
    reference_start = time.perf_counter()
    reference_instances = []
    for seed in range(8):
        inst = make_instance(seed=1000 + seed, **shipping)
        if verify(inst, _attack_outlier_degree(inst))[0]:
            attack_results["outlier_degree"]["successes"] += 1
        greedy = _attack_greedy_separator(inst)
        if verify(inst, greedy)[0]:
            attack_results["greedy_sampled_separator"]["successes"] += 1
        restart_rng = random.Random(0xABC000 + seed)
        restart_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_solved = True
                break
        if restart_solved:
            attack_results["random_restart_256"]["successes"] += 1
        if verify(inst, _attack_lexicographic_by_hand(inst))[0]:
            attack_results["lexicographic_by_hand"]["successes"] += 1
        recovered, stats = _reference_pb_dpll(inst)
        reference_wide_operations += stats["wide_bit_operations"]
        reference_word_operations += stats["estimated_64bit_word_operations"]
        reference_greedy_evaluations += stats["greedy_evaluations"]
        reference_swap_evaluations += stats["swap_evaluations"]
        reference_repair_passes += stats["repair_passes"]
        reference_instances.append({"seed": 1000 + seed, **stats})
        if recovered is not None and verify(inst, recovered)[0]:
            reference_successes += 1
    reference_elapsed = time.perf_counter() - reference_start

    # This second reference is complete for every instance emitted by this
    # generator: the inverse construction promises an affine image of the base
    # template.  It is measured separately because it is construction-aware,
    # whereas the reference above is the natural CSP greedy/repair method.
    complete_successes = 0
    complete_operations = 0
    complete_candidates = 0
    complete_start = time.perf_counter()
    for seed in range(8):
        inst = make_instance(seed=1000 + seed, **shipping)
        recovered, operations, candidates = _reference_affine_scan(inst)
        complete_operations += operations
        complete_candidates += candidates
        if recovered is not None and verify(inst, recovered)[0]:
            complete_successes += 1
    complete_elapsed = time.perf_counter() - complete_start
    all_attacks_failed = all(
        entry["successes"] == 0 for entry in attack_results.values()
    )
    reference_algorithm = {
        "name": (
            "pseudo-Boolean DPLL with unit/cardinality propagation and a "
            "full-constraint greedy/repair branching heuristic"
        ),
        "complexity": (
            "O(2^pool*n^2) worst case; the disclosed complete solver for "
            "this generated distribution is O(n^2*k)"
        ),
        "wall_clock_sec": reference_elapsed,
        "operations": reference_word_operations,
        "wide_bit_operations": reference_wide_operations,
        "greedy_evaluations": reference_greedy_evaluations,
        "swap_evaluations": reference_swap_evaluations,
        "repair_passes": reference_repair_passes,
        "dpll_nodes": sum(item["dpll_nodes"] for item in reference_instances),
        "constraint_scans": sum(
            item["constraint_scans"] for item in reference_instances
        ),
        "unit_propagations": sum(
            item["unit_propagations"] for item in reference_instances
        ),
        "instances": reference_instances,
        "solves": f"{reference_successes}/8, as expected",
    }
    complete_distribution_algorithm = {
        "name": "complete affine-template scan with exact Definition-1 check",
        "complexity": "O(n^2*k + survivors*n^2*k) exact bit operations",
        "wall_clock_sec": complete_elapsed,
        "operations": complete_operations,
        "affine_candidates": complete_candidates,
        "solves": f"{complete_successes}/8, as expected",
    }
    report["G5_density_and_baseline"] = {
        "pass": guess_rate < 1e-6
        and reference_successes == 8
        and complete_successes == 8,
        "shipping_density_fraction": guess_rate,
        "shipping_density_samples": guess_total,
        "baseline_wall_clock_sec": reference_elapsed,
        "baseline_word_operations": reference_word_operations,
        "shipping_density": {
            "hits": guess_hits,
            "total": guess_total,
            "observed_fraction": guess_rate,
            "preset": SHIPPING_DIFFICULTY,
        },
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
        "baseline": reference_algorithm,
        "complete_distribution_algorithm": complete_distribution_algorithm,
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed
        and reference_successes == 8
        and complete_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference_algorithm,
        "complete_distribution_algorithm": complete_distribution_algorithm,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] = _next_prime(2 * shipping["n"] + 1)
    doubled_params["pool_size"] = min(
        doubled_params["n"], 2 * shipping["pool_size"]
    )
    doubled = make_instance(seed=73, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > density_inst["n"]
        and len(doubled["answer"]) == len(density_inst["answer"])
        and search_space(doubled) > search_space(density_inst),
        "shipping_n": density_inst["n"],
        "doubled_n": doubled["n"],
        "answer_length_before": len(density_inst["answer"]),
        "answer_length_after": len(doubled["answer"]),
        "space_before": search_space(density_inst),
        "space_after": search_space(doubled),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    transformed_verify = 0
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=7000 + seed, **DIFFICULTY["easy"])
        key = canonical_key(inst)
        distinct_keys.append(key)
        reordered = dict(inst)
        reordered["pool"] = list(reversed(inst["pool"]))
        reordered["markers"] = list(reversed(inst["markers"]))
        if canonical_key(reordered) == key:
            invariance_checks += 1
        rng = random.Random(8000 + seed)
        permutation = list(range(inst["n"]))
        rng.shuffle(permutation)
        transformed = _permuted_instance(inst, permutation)
        if canonical_key(transformed) == key:
            invariance_checks += 1
        if verify(transformed, transformed["answer"])[0]:
            transformed_verify += 1
        composed = dict(transformed)
        composed["pool"] = list(reversed(transformed["pool"]))
        composed["markers"] = list(reversed(transformed["markers"]))
        if canonical_key(composed) == key:
            invariance_checks += 1
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and transformed_verify == 20
        and len(set(distinct_keys)) == 20,
        "invariance_checks": invariance_checks,
        "invariance_attempts": 60,
        "transformed_answers_verified": transformed_verify,
        "transformed_attempts": 20,
        "distinct_keys": len(set(distinct_keys)),
        "unrelated_instances": 20,
        "method": "color refinement; stable quotient fallback",
    }

    size_inst = make_instance(seed=314159, **shipping)
    chars, tokens, elements = _answer_size(size_inst["answer"])
    # Include more shipping seeds than G1 so this is a measured worst case.
    route_operations = list(compact_operations)
    for seed in range(12):
        inst = make_instance(seed=9000 + seed, **shipping)
        recovered, operations = _compact_recover(inst)
        if recovered is None or not verify(inst, recovered)[0]:
            operations = 10**9
        route_operations.append(operations)
    intended_operations = max(route_operations)
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    arms = {
        key: dict(value)
        for key, value in G9_ORACLE_RESULTS.items()
        if key in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (
        arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {
            "answer_chars": chars,
            "answer_tokens": tokens,
            "answer_elements": elements,
            "intended_route_operations": intended_operations,
        },
    }

    report["pass"] = all(
        isinstance(value, dict) and value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
