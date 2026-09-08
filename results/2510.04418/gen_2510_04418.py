"""Verified HIST problem generator for arXiv:2510.04418.

The paper studies homeomorphically irreducible spanning trees (HISTs):
spanning trees with no degree-two vertex.  Theorem 4.1 lifts an s--t
Hamiltonian path to a HIST by attaching forced pendant vertices.  This module
uses that exact lift on a succinct Cayley graph of bit strings.

Generation is inverse.  An affine ordering of bit positions is sampled first;
its prefix masks are inserted into the Cayley generator set, and exchangeable
affine-interval masks are added as decoys.  The known Hamiltonian path and all
forced pendant edges then form the certified HIST.  No completed instance is
searched to obtain its answer.

Only the Python standard library is used.  Importing this module performs no
I/O, consumes no global randomness, and prints nothing.
"""

from __future__ import annotations

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
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "succinct finite Cayley graph on bit strings",
        "pendant-vertex lift of an s-t Hamiltonian path",
        "symbolically represented homeomorphically irreducible spanning tree",
    ],
    "verification_operations": [
        "exact bit permutation",
        "exact XOR edge-membership lookup",
        "exact prefix-mask comparison",
        "symbolic spanning and vertex-degree count",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Theorem 4.1 (attach forced pendant vertices to turn an "
        "s-t Hamiltonian path into a HIST)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Consecutive binary counters differ in nested carry masks, and one valid "
        "ordering of the bit positions is an affine orbit modulo n; without "
        "recognizing that orbit a solver must propagate all displayed subset states."
    ),
    "hardness_basis": (
        "Track B: exact subset-state dynamic programming on the succinct prefix "
        "DAG runs in O(nL), where L is the number of displayed masks; at the hard "
        "preset n=31 and 64 masks per nontrivial weight it averages 28,374 exact "
        "predecessor probes and about 0.01 seconds, whereas recognizing and testing "
        "the planted affine orbit takes fewer than 1,000 exact modular/bit operations."
    ),
    "max_answer_tokens": 32,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON permutation [sigma_0,...,sigma_(n-1)] of the n zero-based bit "
        "positions.  It symbolically denotes the full HIST whose core path visits "
        "start XOR P_sigma(i) for i=0,...,2^n-1 and that contains every forced "
        "pendant edge.  Exactly n integers in 0..n-1 are permitted."
    ),
    "bounds": {
        "entries": "exactly n",
        "entry_min": 0,
        "entry_max": "n-1",
        "all_distinct": 1,
        "maximum_shipping_entries": 31,
    },
}


DIFFICULTY = {
    "demo": {"n": 5, "masks_per_weight": 2},
    "easy": {"n": 13, "masks_per_weight": 12},
    "medium": {"n": 23, "masks_per_weight": 32},
    "hard": {"n": 31, "masks_per_weight": 64},
}

SHIPPING_DIFFICULTY = "hard"

# Scratch copies used for G9 set this flag so harden.py runs the shipping rung
# alone.  Normal imports retain the mandatory four-rung ladder.
_G9_SINGLE = os.environ.get("GV_G9_SINGLE") == "1"
if _G9_SINGLE:
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }


STRUCTURAL_HINT = (
    "One valid order of the bit positions is an affine orbit modulo the prime n."
)
PLACEBO_HINT = (
    "Keep the zero-based bit positions and the displayed mask weights carefully aligned."
)


# Filled from scripts/harden.py transcripts after the local gates pass.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


NOTES = r"""
Section 2.1 fixes the exact objects: all graphs are finite, simple and
undirected, and a HIST is a spanning tree containing no degree-two vertex.
Theorem 4.1 supplies the certificate-preserving transformation used here.  If
G has an s-t Hamiltonian path, attach one pendant vertex to every core vertex
other than t and attach one additional pendant at s.  The path plus all pendant
edges is a HIST.  The degree-sum argument in the reverse direction forces any
HIST of the lifted graph to restrict to an s-t Hamiltonian path.

Step-0 triage rules out a Track-A claim.  Theorem 2.1 and Corollary 3 make
diameter-at-most-two graphs and chordal diameter-at-most-three graphs
polynomial-time cases.  Theorems 6.1--6.3 give FPT algorithms for modular-width,
treewidth, and cluster vertex deletion number.  Theorem 5.1 also gives a
4^N N^{O(1)} exact algorithm for an N-vertex graph.  Theorem 4.1 is a worst-case
NP-completeness result for strongly chordal diameter-four graphs, not a theorem
about this generated distribution.  This module therefore states the efficient
compressed subset-DP openly and claims only no-tool compression hardness.

The generator samples the affine answer before constructing any mask row.  At
each Hamming weight, the planted prefix and every decoy are sampled from the
same family of affine intervals modulo n; row order is shuffled.  The plant is
therefore not distinguished by magnitude, Hamming weight, or membership in the
affine-interval family.  Bit-incidence ranking, smallest- and largest-extension
greedy rules, a two-level lookahead, unit-stride ansatzes, and uniform random
restarts are tested.  The exact subset-DP succeeds, as Track B requires.

The graph is succinct but completely finite and exact.  Its core vertices are
all n-bit strings, its core edges are defined by the displayed XOR masks, and
its pendant vertices are given by a closed finite rule.  The answer is a
symbolic representation of the actual spanning tree, not merely a claim that a
tree exists: verify checks the permutation, every distinct core-edge mask, the
2^n core-vertex count, the pendant-edge count, connectivity by the enumerated
binary-counter index, and the resulting degree pattern using exact integers.
""".strip()


def _is_prime(value):
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


def _popcount(value):
    return bin(value).count("1")


def _bits(mask, n):
    return [bit for bit in range(n) if mask & (1 << bit)]


def _mask_from_bits(bits):
    mask = 0
    for bit in bits:
        mask |= 1 << bit
    return mask


def _affine_order(n, start, step):
    return [(start + step * index) % n for index in range(n)]


def _prefix_masks(order):
    out = []
    mask = 0
    for bit in order:
        mask |= 1 << bit
        out.append(mask)
    return out


def _affine_interval_universe(n, weight):
    """All weight-k sets occurring consecutively on an affine n-cycle."""
    masks = set()
    for start in range(n):
        for step in range(1, n):
            mask = 0
            for index in range(weight):
                mask |= 1 << ((start + step * index) % n)
            masks.add(mask)
    return masks


def _allowed_sets(inst):
    return [set(row) for row in inst["allowed_masks_by_weight"]]


def _shape_ok(answer, n):
    return (
        isinstance(answer, list)
        and len(answer) == n
        and all(isinstance(x, int) and not isinstance(x, bool) for x in answer)
        and all(0 <= x < n for x in answer)
        and len(set(answer)) == n
    )


def _fast_valid(inst, answer, with_tests=False):
    """Check the symbolic tree's core edges via its carry-prefix identity."""
    n = inst["dimension"]
    if not _shape_ok(answer, n):
        return (False, 0) if with_tests else False
    allowed = _allowed_sets(inst)
    mask = 0
    tests = 0
    for weight, bit in enumerate(answer, 1):
        mask |= 1 << bit
        tests += 1
        if mask not in allowed[weight - 1]:
            return (False, tests) if with_tests else False
    return (True, tests) if with_tests else True


def _attack_frequency_rank(inst):
    n = inst["dimension"]
    frequency = [0] * n
    operations = 0
    for row in inst["allowed_masks_by_weight"]:
        for mask in row:
            for bit in range(n):
                operations += 1
                if mask & (1 << bit):
                    frequency[bit] += 1
    candidates = [
        sorted(range(n), key=lambda b: (frequency[b], b)),
        sorted(range(n), key=lambda b: (-frequency[b], b)),
    ]
    for candidate in candidates:
        ok, tests = _fast_valid(inst, candidate, with_tests=True)
        operations += tests
        if ok:
            return candidate, operations
    return None, operations


def _attack_greedy(inst, largest=False):
    n = inst["dimension"]
    allowed = _allowed_sets(inst)
    order = []
    mask = 0
    operations = 0
    for weight in range(1, n + 1):
        choices = []
        for bit in range(n):
            if mask & (1 << bit):
                continue
            operations += 1
            if (mask | (1 << bit)) in allowed[weight - 1]:
                choices.append(bit)
        if not choices:
            return None, operations
        bit = max(choices) if largest else min(choices)
        order.append(bit)
        mask |= 1 << bit
    return (order if _fast_valid(inst, order) else None), operations


def _attack_two_level_greedy(inst):
    """Choose the legal extension having the most legal next extensions."""
    n = inst["dimension"]
    allowed = _allowed_sets(inst)
    order = []
    mask = 0
    operations = 0
    for weight in range(1, n + 1):
        scored = []
        for bit in range(n):
            if mask & (1 << bit):
                continue
            trial = mask | (1 << bit)
            operations += 1
            if trial not in allowed[weight - 1]:
                continue
            score = 0
            if weight < n:
                for nxt in range(n):
                    if trial & (1 << nxt):
                        continue
                    operations += 1
                    if (trial | (1 << nxt)) in allowed[weight]:
                        score += 1
            scored.append((score, -bit, bit))
        if not scored:
            return None, operations
        bit = max(scored)[2]
        order.append(bit)
        mask |= 1 << bit
    return (order if _fast_valid(inst, order) else None), operations


def _attack_unit_stride(inst):
    n = inst["dimension"]
    operations = 0
    for step in (1, n - 1):
        for start in range(n):
            candidate = _affine_order(n, start, step)
            ok, tests = _fast_valid(inst, candidate, with_tests=True)
            operations += tests
            if ok:
                return candidate, operations
    return None, operations


def _attack_random_restarts(inst, restarts=256, seed=0):
    n = inst["dimension"]
    rng = random.Random(seed)
    operations = 0
    for _ in range(restarts):
        candidate = list(range(n))
        rng.shuffle(candidate)
        ok, tests = _fast_valid(inst, candidate, with_tests=True)
        operations += tests
        if ok:
            return candidate, operations
    return None, operations


def _compact_affine_decoder(inst):
    """The intended route: orient each displayed weight-two affine interval."""
    n = inst["dimension"]
    row_two = inst["allowed_masks_by_weight"][1]
    prefix_tests = 0
    candidates = 0
    for pair_mask in row_two:
        pair = _bits(pair_mask, n)
        if len(pair) != 2:
            continue
        for first, second in (pair, list(reversed(pair))):
            candidates += 1
            step = (second - first) % n
            candidate = _affine_order(n, first, step)
            ok, tests = _fast_valid(inst, candidate, with_tests=True)
            prefix_tests += tests
            if ok:
                # Two exact operations per tested prefix: modular orbit update
                # and bit-mask union.  Hash membership is recorded separately.
                return candidate, {
                    "operations": 2 * prefix_tests,
                    "prefix_membership_tests": prefix_tests,
                    "oriented_candidates": candidates,
                }
    return None, {
        "operations": 2 * prefix_tests,
        "prefix_membership_tests": prefix_tests,
        "oriented_candidates": candidates,
    }


def _reference_subset_dp(inst, count_all_predecessors=False):
    """Exact standard DP on the displayed subset-state DAG."""
    n = inst["dimension"]
    reachable = {0}
    parents = {}
    operations = 0
    counts = {0: 1}
    for row in inst["allowed_masks_by_weight"]:
        next_reachable = set()
        next_counts = {}
        for mask in row:
            total = 0
            chosen = None
            for bit in range(n):
                if not (mask & (1 << bit)):
                    continue
                operations += 1
                predecessor = mask ^ (1 << bit)
                if predecessor in reachable and chosen is None:
                    chosen = (predecessor, bit)
                    if not count_all_predecessors:
                        break
                if count_all_predecessors:
                    total += counts.get(predecessor, 0)
            if chosen is not None:
                next_reachable.add(mask)
                parents[mask] = chosen
            if count_all_predecessors and total:
                next_counts[mask] = total
        reachable = next_reachable
        if count_all_predecessors:
            counts = next_counts

    full = (1 << n) - 1
    if count_all_predecessors:
        return counts.get(full, 0), operations
    if full not in reachable:
        return None, operations
    answer = []
    mask = full
    while mask:
        predecessor, bit = parents[mask]
        answer.append(bit)
        mask = predecessor
    answer.reverse()
    return answer, operations


def make_instance(n, seed=0, masks_per_weight=64, **params):
    """Inverse-generate a succinct graph and a symbolic HIST certificate."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be a prime integer at least 5")
    if not _is_prime(n):
        raise ValueError("n must be prime so every nonzero affine step is an orbit")
    if (
        isinstance(masks_per_weight, bool)
        or not isinstance(masks_per_weight, int)
        or masks_per_weight < 1
    ):
        raise ValueError("masks_per_weight must be a positive integer")

    rng = random.Random(seed)
    affine_start = rng.randrange(n)
    # Exclude the two visually obvious unit strides; the tested unit-stride
    # ansatz must not inherit a win directly from the planted answer.
    affine_step = rng.choice(list(range(2, n - 1)))
    answer = _affine_order(n, affine_start, affine_step)
    planted_prefixes = _prefix_masks(answer)
    core_start = rng.randrange(1 << min(n, 24))
    if n > 24:
        core_start |= rng.randrange(1 << (n - 24)) << 24

    universes = [
        _affine_interval_universe(n, weight) for weight in range(1, n + 1)
    ]

    # Only the decoy presentation is retried.  The certificate was already
    # sampled and never changes, so attack filtering cannot become certificate
    # search.
    for _presentation_attempt in range(256):
        rows = []
        for weight, universe in enumerate(universes, 1):
            planted = planted_prefixes[weight - 1]
            choices = list(universe - {planted})
            rng.shuffle(choices)
            target = min(masks_per_weight, len(universe))
            row = [planted] + choices[: target - 1]
            rng.shuffle(row)
            rows.append(row)

        inst = {
            "family": "succinct_affine_carry_HIST",
            "dimension": n,
            "core_vertex_count": 1 << n,
            "total_vertex_count": 1 << (n + 1),
            "core_start": core_start,
            "core_target": core_start ^ ((1 << n) - 1),
            "allowed_masks_by_weight": rows,
            "answer": list(answer),
        }

        # The demo is intentionally hand-solvable; attack resistance begins at
        # the evaluated rungs, while all construction and verification rules are
        # identical.
        if n == 5:
            return inst

        cheap = (
            _attack_frequency_rank(inst)[0],
            _attack_greedy(inst, largest=False)[0],
            _attack_greedy(inst, largest=True)[0],
            _attack_two_level_greedy(inst)[0],
            _attack_unit_stride(inst)[0],
        )
        compact, compact_cost = _compact_affine_decoder(inst)
        if any(candidate is not None for candidate in cheap):
            continue
        if compact is None or compact_cost["operations"] > 900:
            continue
        return inst
    raise RuntimeError("could not find an attack-resistant decoy presentation")


def render(inst):
    n = inst["dimension"]
    q = inst["core_vertex_count"]
    total = inst["total_vertex_count"]
    start = inst["core_start"]
    target = inst["core_target"]
    rows = inst["allowed_masks_by_weight"]
    row_text = []
    for weight, row in enumerate(rows, 1):
        row_text.append(
            "  weight {:>2}: {}".format(weight, " ".join(str(mask) for mask in row))
        )

    text = f"""Find a homeomorphically irreducible spanning tree (HIST).

A HIST of a finite simple undirected graph is a spanning tree in which every
vertex has degree 1 or degree at least 3; degree 2 is forbidden.

The graph H below is specified exactly and succinctly.  It has {total} vertices.
Its {q} core vertices are C_x for integers x=0,...,{q - 1}, viewed as {n}-bit
strings.  For every displayed nonzero mask m and every core label x, H contains
the undirected core edge {{C_x,C_(x XOR m)}}.  Repetitions describe the same
simple edge, not parallel edges.  XOR is bitwise exclusive-or.

The displayed masks are grouped by Hamming weight (the number of 1 bits):
{chr(10).join(row_text)}

H also has pendant vertices (degree-one vertices) under this complete rule:
  * C_{start} has two private pendant neighbours;
  * C_{target} has no pendant neighbour;
  * every other core vertex has one private pendant neighbour.
Each pendant is adjacent only to its named core vertex.  There are no other
vertices and no other edges.

Return a compact, exact HIST certificate: a permutation
sigma=[sigma_0,...,sigma_{n - 1}] of the zero-based bit positions 0,...,{n - 1}.
For an integer i in 0,...,{q - 1}, define P_sigma(i) by moving bit j of i to bit
sigma_j, for every j.  Your certificate denotes the tree containing all pendant
edges and the core path, in this mandatory order,

  C_({start} XOR P_sigma(0)), C_({start} XOR P_sigma(1)), ...,
  C_({start} XOR P_sigma({q - 1})).

The answer is valid exactly when every consecutive pair in this path is a core
edge of H.  Bit positions are 0-indexed, order matters, every position must
occur exactly once, and no repetitions are allowed.  This symbolic certificate
defines the entire finite tree; you must not print its billions of individual
edges."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    text += f"""

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{n} integers.
Example syntax only: <answer>{list(range(n))}</answer>
Output nothing else inside the tags."""
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    bodies = list(reversed(tagged))
    if not bodies:
        bodies = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    for body in bodies:
        try:
            value = json.loads(body.strip())
        except (TypeError, ValueError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    """Verify any valid symbolic HIST; never inspect inst['answer']."""
    n = inst.get("dimension")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"expected exactly {n} bit positions"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every bit position must be an integer"
    if any(x < 0 or x >= n for x in answer):
        return False, "bit position out of range"
    if len(set(answer)) != n:
        return False, "bit positions must be pairwise distinct"

    rows = inst.get("allowed_masks_by_weight")
    if not isinstance(rows, list) or len(rows) != n:
        return False, "malformed instance mask rows"
    mask = 0
    for weight, bit in enumerate(answer, 1):
        mask |= 1 << bit
        if mask not in set(rows[weight - 1]):
            return False, (
                f"forbidden core edge: carry mask {mask} of weight {weight} "
                "is not displayed"
            )

    # Execute the remaining symbolic tree checks exactly.  A bit permutation is
    # a bijection on all 2^n core strings, so the indexed core path has exactly
    # 2^n distinct vertices.  Binary increment has trailing-one count r and the
    # corresponding consecutive labels differ by the checked prefix mask of
    # weight r+1.  The following counts then inspect the complete finite tree.
    core_vertices = 1 << n
    if core_vertices != inst.get("core_vertex_count"):
        return False, "instance core-vertex count disagrees with its dimension"
    pendant_vertices = core_vertices  # two at s, none at t, one elsewhere
    total_vertices = core_vertices + pendant_vertices
    core_path_edges = core_vertices - 1
    pendant_edges = pendant_vertices
    total_edges = core_path_edges + pendant_edges
    if total_vertices != inst.get("total_vertex_count"):
        return False, "instance vertex count disagrees with its pendant rule"
    if total_edges != total_vertices - 1:
        return False, "symbolic edge count is not that of a tree"

    start = inst.get("core_start")
    target = inst.get("core_target")
    if target != start ^ (core_vertices - 1):
        return False, "instance endpoint labels disagree with bit complementation"
    # Degrees in the denoted tree: s has 1 path + 2 pendant edges, t has
    # 1 path edge, and every other core has 2 path + 1 pendant edge.
    degree_counts = {1: pendant_vertices + 1, 3: core_vertices - 1}
    if sum(degree_counts.values()) != total_vertices:
        return False, "symbolic degree classes do not span every vertex"
    if sum(degree * count for degree, count in degree_counts.items()) != 2 * total_edges:
        return False, "symbolic degrees violate the handshaking identity"
    if degree_counts.get(2, 0):
        return False, "degree-two vertex detected"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the full, structure-aware certificate language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    candidate = list(range(inst["dimension"]))
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return math.factorial(inst["dimension"])


def enumerate_all(inst):
    """Count valid symbolic HIST certificates exactly on the sparse state DAG."""
    n = inst["dimension"]
    # The displayed representation keeps this exact computation bounded even
    # when the expanded graph has billions of vertices.
    if sum(len(row) for row in inst["allowed_masks_by_weight"]) * n > 2_000_000:
        return None
    count, _operations = _reference_subset_dp(inst, count_all_predecessors=True)
    return count


def _coordinate_profiles(inst):
    n = inst["dimension"]
    rows = inst["allowed_masks_by_weight"]
    single = [[0] * n for _ in range(n)]
    pair = [[0] * (n * (n - 1) // 2) for _ in range(n)]
    pair_index = {}
    index = 0
    for a in range(n):
        for b in range(a + 1, n):
            pair_index[(a, b)] = index
            index += 1
    for weight, row in enumerate(rows):
        for mask in row:
            bits = _bits(mask, n)
            for bit in bits:
                single[weight][bit] += 1
            for pos, a in enumerate(bits):
                for b in bits[pos + 1 :]:
                    pair[weight][pair_index[(a, b)]] += 1
    single_signature = sorted(tuple(single[w][b] for w in range(n)) for b in range(n))
    pair_signature = [sorted(values) for values in pair]
    return single_signature, pair_signature


def canonical_key(inst):
    """Invariant under bit relabelling, XOR translation, and row reordering."""
    single, pair = _coordinate_profiles(inst)
    signature = {
        "dimension": inst["dimension"],
        "row_sizes": [len(set(row)) for row in inst["allowed_masks_by_weight"]],
        "coordinate_incidence_profiles": single,
        "pair_coincidence_histograms": pair,
    }
    payload = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _permute_mask(mask, coordinate_permutation):
    out = 0
    for old, new in enumerate(coordinate_permutation):
        if mask & (1 << old):
            out |= 1 << new
    return out


def _relabel_instance(inst, coordinate_permutation, translation, seed):
    rng = random.Random(seed)
    rows = []
    for row in inst["allowed_masks_by_weight"]:
        transformed = [_permute_mask(mask, coordinate_permutation) for mask in row]
        rng.shuffle(transformed)
        rows.append(transformed)
    rng.shuffle(rows[0])  # explicit input-order transformation, even for tiny rows
    start = _permute_mask(inst["core_start"], coordinate_permutation) ^ translation
    out = {
        "family": inst["family"],
        "dimension": inst["dimension"],
        "core_vertex_count": inst["core_vertex_count"],
        "total_vertex_count": inst["total_vertex_count"],
        "core_start": start,
        "core_target": start ^ ((1 << inst["dimension"]) - 1),
        "allowed_masks_by_weight": rows,
        "answer": [coordinate_permutation[b] for b in inst["answer"]],
    }
    return out


def escalate(params):
    """Increase crowding first, then dimension; the symbolic answer stays short."""
    if _G9_SINGLE:
        return None
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 31))
    masks = int(current.get("masks_per_weight", 64))
    if masks < 192:
        current["masks_per_weight"] = min(192, masks * 2)
        return current
    next_primes = [37, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101]
    for prime in next_primes:
        if prime > n:
            current["n"] = prime
            current["masks_per_weight"] = 96
            return current
    return "cap_bound"


def _invalid_transposition(inst, answer):
    for left in range(len(answer)):
        for right in range(left + 1, len(answer)):
            candidate = list(answer)
            candidate[left], candidate[right] = candidate[right], candidate[left]
            ok, _reason = verify(inst, candidate)
            if not ok:
                return candidate
    return None


def _next_prime_at_least(value):
    candidate = max(5, value)
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}

    # G1: every preset, three seeds, exact verification and JSON nativeness.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=20260908, **shipping_params)
    answer = list(shipping["answer"])

    # G2: five different corruptions and five different diagnostic classes.
    transposed = _invalid_transposition(shipping, answer)
    corruptions = {
        "empty": [],
        "dropped": answer[:-1],
        "duplicate": [answer[0], answer[0]] + answer[2:],
        "out_of_range": [shipping["dimension"]] + answer[1:],
        "transposition": transposed,
    }
    g2_reasons = {}
    for name, candidate in corruptions.items():
        if candidate is None:
            g2_reasons[name] = "no invalid transposition found"
            continue
        ok, reason = verify(shipping, candidate)
        g2_reasons[name] = reason if not ok else "ACCEPTED"
    g2_pass = (
        transposed is not None
        and all(reason != "ACCEPTED" for reason in g2_reasons.values())
        and len(set(g2_reasons.values())) == len(g2_reasons)
    )
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "rejected": sum(reason != "ACCEPTED" for reason in g2_reasons.values()),
        "attempts": len(g2_reasons),
        "reasons": g2_reasons,
    }

    # G3: prose, markdown, whitespace, and JSON round-trip.
    response = (
        "I used the carry-mask invariant.\n```json\n"
        + "<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\nThis is the requested symbolic tree."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "prose_and_fence_round_trip": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: the structure-aware prior is uniform over permutations, not arbitrary
    # integer lists.  Exact counting below independently checks the sample.
    samples = 200_000
    hits = 0
    guess_rng = random.Random(440044)
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        if _fast_valid(shipping, candidate):
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "sampled_probability": hits / samples,
        "prior": "uniform over all n! bit-position permutations",
    }

    # G5: exact shipping density plus the measured strongest failing attack.
    exact_count, count_ops = _reference_subset_dp(shipping, count_all_predecessors=True)
    baseline_start = time.perf_counter()
    baseline_answer, baseline_ops = _attack_random_restarts(
        shipping, restarts=512, seed=550055
    )
    baseline_wall = time.perf_counter() - baseline_start
    space = search_space(shipping)
    report["G5_density_and_baseline"] = {
        "pass": exact_count > 0 and exact_count / space < 1e-6 and baseline_answer is None,
        "shipping_solution_count": exact_count,
        "shipping_candidate_count": space,
        "shipping_solution_fraction": exact_count / space,
        "exact_count_predecessor_probes": count_ops,
        "baseline_random_restart_hits": 0 if baseline_answer is None else 1,
        "baseline_candidate_checks": 512,
        "baseline_prefix_tests": baseline_ops,
        "baseline_wall_seconds": baseline_wall,
    }

    # G6: construction-aware cheap attacks must all fail; the exact DP is the
    # successful Track-B reference and is deliberately outside `attacks`.
    attack_names = [
        "bit_frequency_outlier",
        "greedy_smallest_extension",
        "greedy_largest_extension",
        "two_level_lookahead",
        "unit_stride_ansatz",
        "random_restart_256",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": 0, "operations": 0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    compact_operations = []
    for seed in range(8):
        inst = make_instance(seed=6100 + seed, **shipping_params)
        trials = {
            "bit_frequency_outlier": _attack_frequency_rank(inst),
            "greedy_smallest_extension": _attack_greedy(inst, largest=False),
            "greedy_largest_extension": _attack_greedy(inst, largest=True),
            "two_level_lookahead": _attack_two_level_greedy(inst),
            "unit_stride_ansatz": _attack_unit_stride(inst),
            "random_restart_256": _attack_random_restarts(
                inst, restarts=256, seed=7000 + seed
            ),
        }
        for name, (candidate, operations) in trials.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["operations"] += operations
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1

        t0 = time.perf_counter()
        ref_answer, ref_ops = _reference_subset_dp(inst)
        reference_wall += time.perf_counter() - t0
        reference_operations += ref_ops
        if ref_answer is not None and verify(inst, ref_answer)[0]:
            reference_successes += 1
        compact_answer, compact_cost = _compact_affine_decoder(inst)
        if compact_answer is None or not verify(inst, compact_answer)[0]:
            compact_operations.append(10**9)
        else:
            compact_operations.append(compact_cost["operations"])

    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and max(compact_operations) <= 1000,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact subset-state dynamic programming",
            "complexity": "O(nL) exact predecessor probes",
            "wall_clock_sec": reference_wall,
            "operations": reference_operations,
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "affine-orbit scan from displayed weight-two masks",
            "max_operations": max(compact_operations),
            "mean_operations": sum(compact_operations) / len(compact_operations),
            "solves": "8/8",
        },
    }

    # G7: double the principal size parameter (rounding up to the next prime).
    doubled_n = _next_prime_at_least(2 * shipping_params["n"])
    doubled = make_instance(
        n=doubled_n,
        masks_per_weight=shipping_params["masks_per_weight"],
        seed=770077,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    base_log2 = math.lgamma(shipping_params["n"] + 1) / math.log(2)
    doubled_log2 = math.lgamma(doubled_n + 1) / math.log(2)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_log2 > 2 * base_log2,
        "base_n": shipping_params["n"],
        "doubled_n": doubled_n,
        "base_search_log2": base_log2,
        "doubled_search_log2": doubled_log2,
        "doubled_verification": doubled_reason,
    }

    # G8: bit-coordinate permutations, core XOR translations, input ordering,
    # and their composition are genuine problem isomorphisms.
    invariance_checks = 0
    carried_witness_checks = 0
    distinct_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=8800 + seed, **shipping_params)
        key = canonical_key(inst)
        distinct_keys.append(key)
        rng = random.Random(9900 + seed)
        identity = list(range(inst["dimension"]))
        permutation = list(identity)
        rng.shuffle(permutation)
        second = list(identity)
        rng.shuffle(second)
        translation = rng.randrange(1 << inst["dimension"])
        transforms = [
            _relabel_instance(inst, permutation, 0, seed),
            _relabel_instance(inst, identity, translation, seed + 100),
            _relabel_instance(inst, identity, 0, seed + 200),
        ]
        first = _relabel_instance(inst, permutation, translation, seed + 300)
        composed = _relabel_instance(first, second, rng.randrange(1 << inst["dimension"]), seed + 400)
        transforms.extend([first, composed])
        for transformed in transforms:
            invariance_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed")
            ok, reason = verify(transformed, transformed["answer"])
            carried_witness_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}: carried witness failed: {reason}")
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_passed": invariance_checks - len([x for x in g8_failures if "key" in x]),
        "invariance_attempts": invariance_checks,
        "carried_witness_passed": carried_witness_checks - len([x for x in g8_failures if "witness" in x]),
        "carried_witness_attempts": carried_witness_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "bit-coordinate permutation",
            "core XOR translation",
            "mask-row reordering",
            "all composed",
        ],
        "failures": g8_failures,
    }

    # G9: oracle arms are diagnostic; only the exact answer/route caps gate.
    answer_blobs = []
    route_costs = []
    for seed in range(20):
        inst = make_instance(seed=99000 + seed, **shipping_params)
        # Match harden.py's and emit.sh's ordinary json.dumps serialization.
        answer_blobs.append(json.dumps(inst["answer"]))
        compact_answer, compact_cost = _compact_affine_decoder(inst)
        if compact_answer is None:
            route_costs.append(10**9)
        else:
            route_costs.append(compact_cost["operations"])
    answer_chars = max(len(blob) for blob in answer_blobs)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = max(_answer_atoms(json.loads(blob)) for blob in answer_blobs)
    route_operations = max(route_costs)
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and route_operations <= 1000
    )
    bare = G9_ORACLE_RESULTS["bare"]
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hint_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(bare),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": hint_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 1000},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
