"""Verified generator for minimum Cluster Vertex Deletion witnesses.

The family uses the Vertex-Cover-to-Cluster-VD construction in Proposition 18
of arXiv:2007.08057.  The source graph is a succinct Cayley graph on GF(2)^d;
the answer is an exact symbolic description of one side of its bipartition.

Generation is inverse: choose the parity functional first, then draw generator
masks from its affine hyperplane and force their total XOR to be the functional.
The verifier never reads the planted answer.
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


# harden.py is run from this directory, while emit.sh runs from the repo root.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The implementation below remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "succinct Cayley graph on GF(2)^d",
        "pendant-vertex extension G+",
        "parity-hyperplane vertex-deletion set",
    ],
    "verification_operations": [
        "exact XOR of bit vectors",
        "exact GF(2) inner products",
        "perfect-matching cardinality comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Proposition 18: attach one pendant edge to every vertex of G; "
        "U subseteq V(G) is a Cluster-VD hitting set of G+ iff U is a "
        "vertex cover of G"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the global XOR of all displayed Cayley generators is "
        "the parity functional defining the hidden bipartition; without this "
        "invariant one must solve a dense GF(2) system."
    ),
    "hardness_basis": (
        "Track B: Gaussian elimination on the m by d GF(2) edge-alternation "
        "system is O(m d^2); at shipping d=72,m=216 it measured 474,459 "
        "scalar-bit operations (about 0.013 s), whereas the compact global-XOR "
        "route takes 215 word-XOR operations."
    ),
    "max_answer_tokens": 6,
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

DIFFICULTY = {"easy": {"n": 72, "m": 216}}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The displayed generator masks have a global XOR invariant tied to the "
    "parity bipartition."
)
PLACEBO_HINT = (
    "The displayed generator masks use fixed-width hexadecimal notation to "
    "make vertex labels unambiguous."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON pair [w,b], where w is exactly ceil(d/4) lowercase hexadecimal "
        "digits encoding a nonzero d-bit GF(2) functional and b is 0 or 1."
    ),
    "bounds": {
        "functional_bits": "d",
        "functional_min": 1,
        "functional_max": "2^d-1",
        "side_choices": 2,
        "candidate_count": "2(2^d-1)",
    },
}

NOTES = (
    "Section 1 fixes the definition: a hitting set X is a vertex set whose "
    "deletion leaves a disjoint union of cliques, equivalently X meets every "
    "induced P3. Theorem 1 and Section 3 give a polynomial O(N^4) "
    "2-approximation, while Section 1.3 records exact 1.811^k poly(N) and "
    "O(1.488^N) algorithms; these facts forbid a Track A claim for this "
    "structured distribution. Proposition 18 supplies the central reduction "
    "used here: vertex covers of G are exactly hitting sets of its pendant "
    "extension G+. The generator samples the parity functional first, draws "
    "all masks from the same affine hyperplane, shuffles them, and forces their "
    "XOR to equal that functional. A generator edge supplies a perfect matching "
    "lower bound, so either parity side is an optimum hitting set. Generator "
    "outlier, greedy pivot, random restart, and obvious-functional attacks are "
    "audited; exact GF(2) elimination is reported separately as the expected "
    "successful Track B reference algorithm. gvlib is optional and this module "
    "uses only standard-library operations when it is absent."
)


# Filled from the independently owned harden.py transcripts after the three
# arms are run.  They are diagnostics; only the size/effort caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _parity(x: int) -> int:
    return x.bit_count() & 1


def _rank_bits(rows: list[int], d: int) -> int:
    """Rank of integer-encoded row vectors over GF(2)."""

    basis = [0] * d
    rank = 0
    for value in rows:
        x = value
        while x:
            p = x.bit_length() - 1
            if basis[p]:
                x ^= basis[p]
            else:
                basis[p] = x
                rank += 1
                break
    return rank


def _sample_affine(rng: random.Random, w: int, d: int, used: set[int]) -> int:
    """Uniformly rejection-sample an unused s with <w,s>=1."""

    while True:
        s = rng.getrandbits(d)
        if s not in used and _parity(w & s) == 1:
            return s


def _xor_all(values) -> int:
    out = 0
    for value in values:
        out ^= value
    return out


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a certified optimum Cluster-VD instance.

    ``n`` is the bit-vector dimension d. ``m`` is the Cayley degree. Larger d
    enlarges the answer space; larger m crowds it with more exact constraints.
    The exponentially large graph is specified without materialising it.
    """

    if type(n) is not int:
        raise ValueError("n must be an integer")
    d = n
    m = params.pop("m", 3 * d)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if type(m) is not int:
        raise ValueError("m must be an integer")
    if d < 4:
        raise ValueError("n must be at least 4")
    if m < d:
        raise ValueError("m must be at least n so the constraints can have full rank")
    if m > (1 << (d - 1)):
        raise ValueError("m exceeds the number of distinct affine-hyperplane masks")

    rng = random.Random(seed)

    # Sample the certificate first. The parity condition is necessary for m
    # affine-hyperplane vectors to have XOR w: <w,w> = m (mod 2).
    while True:
        planted_w = rng.getrandbits(d)
        if planted_w and _parity(planted_w) == (m & 1):
            break

    # The planted four-circuits make non-isomorphic seeds cheaply detectable by
    # an invariant, while shuffling gives every displayed row the same marginal
    # role. They do not reveal the functional: every row is sampled from the
    # same affine hyperplane <w,s>=1.
    for _attempt in range(512):
        rows: list[int] = []
        used: set[int] = set()

        if d >= 16 and m >= d + 20:
            anchor_count = min(16, max(6, d // 8))
            circuit_low = max(2, d // 6)
            circuit_high = min(
                len(list(itertools.combinations(range(anchor_count), 2))),
                d // 3,
                (m - anchor_count - 2) // 2,
            )
            circuit_count = rng.randint(circuit_low, circuit_high)
        else:
            anchor_count = 0
            circuit_count = 0

        anchors: list[int] = []
        for _ in range(anchor_count):
            a = _sample_affine(rng, planted_w, d, used)
            anchors.append(a)
            rows.append(a)
            used.add(a)

        if anchors:
            pairs = list(itertools.combinations(range(len(anchors)), 2))
            for i, j in rng.sample(pairs, circuit_count):
                for _ in range(256):
                    c = _sample_affine(rng, planted_w, d, used)
                    derived = anchors[i] ^ anchors[j] ^ c
                    if derived and derived not in used and derived != c:
                        rows.extend((c, derived))
                        used.add(c)
                        used.add(derived)
                        break
                else:
                    rows = []
                    break
        if anchor_count and not rows:
            continue

        while len(rows) < m - 1:
            s = _sample_affine(rng, planted_w, d, used)
            rows.append(s)
            used.add(s)

        last = planted_w ^ _xor_all(rows)
        if not last or last in used or _parity(planted_w & last) != 1:
            continue
        rows.append(last)
        if _rank_bits(rows, d) != d:
            continue
        rng.shuffle(rows)
        break
    else:
        raise RuntimeError("could not construct a full-rank generator family")

    width = (d + 3) // 4
    side = rng.randrange(2)
    answer = [format(planted_w, f"0{width}x"), side]
    return {
        "dimension": d,
        "generator_count": m,
        "generators": [format(s, f"0{width}x") for s in rows],
        "original_vertices": 1 << d,
        "total_vertices": 1 << (d + 1),
        "minimum_deletions": 1 << (d - 1),
        "hex_width": width,
        "answer": answer,
    }


def render(inst) -> str:
    """Render a self-contained, exact statement with an explicit wire format."""

    d = inst["dimension"]
    width = inst["hex_width"]
    generator_lines = "\n".join(
        f"  {i:03d}: {s}" for i, s in enumerate(inst["generators"])
    )
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = f"\nHint: {STRUCTURAL_HINT}\n"
    elif mode == "placebo":
        hint = f"\nHint: {PLACEBO_HINT}\n"

    example_w = "0" * (width - 1) + "1"
    return f"""Minimum Cluster Vertex Deletion in a succinct graph

All arithmetic on bit-vectors below is over GF(2). A d-bit vector is written as
exactly {width} lowercase hexadecimal digits, including leading zeroes. XOR is
bitwise exclusive-or. For vectors a and z, <a,z> is the parity (0 for even, 1
for odd) of the number of 1-bits in a AND z.

A cluster graph is an undirected simple graph whose connected components are
complete graphs. A cluster vertex-deletion hitting set is a set of vertices
whose deletion leaves a cluster graph.

Here d={d}. Define an undirected simple graph H as follows. For every d-bit
vector x there are two vertices O_x (an original vertex) and P_x (its pendant).
There is an edge O_x--P_x for every x. There is also an edge O_x--O_(x XOR s)
for every x and every generator mask s in the list below. These are all edges;
repeated descriptions of the same undirected edge count only once.

Generator masks ({inst['generator_count']} total, indices are only labels):
{generator_lines}

Your answer must be a pair [w,b]. Here w is a nonzero d-bit vector in exactly
{width} lowercase hexadecimal digits, and b is the integer 0 or 1. The pair
symbolically denotes the deletion set

    X(w,b) = {{ O_x : <w,x> = b }}.

No pendant P_x is deleted. Find any [w,b] for which X(w,b) is a minimum-cardinality
cluster vertex-deletion hitting set of H. Both b choices are allowed if valid.
The minimum deletion size is promised to be {inst['minimum_deletions']}; you do
not write out those vertices. Order in the two-element pair matters.
{hint}
Give your final answer inside <answer></answer> tags as a JSON pair
["w",b], with the hexadecimal mask quoted and b unquoted.
Example of format only: <answer>["{example_w}",0]</answer>
Output nothing else inside the tags."""


def parse_answer(text) -> object | None:
    """Extract the last tagged JSON answer, tolerating surrounding prose/fences."""

    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any parity-hyperplane optimum; never consult inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer has one element; expected [w,b]"
    if len(answer) != 2:
        return False, "answer must have exactly two elements"

    encoded_w, side = answer
    if not isinstance(encoded_w, str):
        return False, "w must be a quoted hexadecimal string"
    if isinstance(side, bool) or not isinstance(side, int) or side not in (0, 1):
        return False, "b must be the integer 0 or 1"
    if not re.fullmatch(r"[0-9a-f]+", encoded_w):
        return False, "w must contain only lowercase hexadecimal digits"

    w = int(encoded_w, 16)
    d = inst["dimension"]
    if w >= (1 << d):
        return False, "w is outside the d-bit range"
    if len(encoded_w) != inst["hex_width"]:
        return False, "w has the wrong fixed hexadecimal width"
    if w == 0:
        return False, "w must be nonzero"

    for encoded_s in inst["generators"]:
        if _parity(w & int(encoded_s, 16)) != 1:
            return False, "w does not alternate across every generator edge"

    # Executable certificate logic: alternation means X(w,b) covers every Cayley
    # edge. Proposition 18 then makes it a CVD hitting set of G+. It contains
    # exactly 2^(d-1) originals. Any nonzero generator pairs every x with x XOR s,
    # a perfect matching of that size, so no vertex cover/hitting set is smaller.
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniform candidate from the stated nonzero-functional/side language."""

    d = inst["dimension"]
    w = rng.randrange(1, 1 << d)
    return [format(w, f"0{inst['hex_width']}x"), rng.randrange(2)]


def search_space(inst) -> int | None:
    """Size of the exact bounded certificate language."""

    return 2 * ((1 << inst["dimension"]) - 1)


def enumerate_all(inst) -> int | None:
    """Brute-force the bounded language only when it has at most 100,000 items."""

    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    count = 0
    for w in range(1, 1 << inst["dimension"]):
        encoded = format(w, f"0{inst['hex_width']}x")
        for side in (0, 1):
            count += int(verify(inst, [encoded, side])[0])
    return count


def _canonical_invariant(inst) -> dict:
    """A GL(d,2)- and generator-order-invariant short-circuit signature."""

    rows = [int(s, 16) for s in inst["generators"]]
    buckets: dict[int, list[tuple[int, int]]] = {}
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            buckets.setdefault(rows[i] ^ rows[j], []).append((i, j))

    circuits: set[tuple[int, int, int, int]] = set()
    bucket_sizes = []
    for pairs in buckets.values():
        if len(pairs) > 1:
            bucket_sizes.append(len(pairs))
            for a in range(len(pairs)):
                i, j = pairs[a]
                for b in range(a + 1, len(pairs)):
                    k, ell = pairs[b]
                    if len({i, j, k, ell}) == 4:
                        circuits.add(tuple(sorted((i, j, k, ell))))

    degrees = [0] * len(rows)
    for circuit in circuits:
        for i in circuit:
            degrees[i] += 1
    circuit_profiles = sorted(
        tuple(sorted(degrees[i] for i in circuit)) for circuit in circuits
    )
    intersection_histogram = [0, 0, 0, 0, 0]
    circuit_list = list(circuits)
    intersections: dict[tuple[int, int], int] = {}
    for i in range(len(circuit_list)):
        left = set(circuit_list[i])
        for j in range(i + 1, len(circuit_list)):
            overlap = len(left.intersection(circuit_list[j]))
            intersection_histogram[overlap] += 1
            if overlap:
                intersections[(i, j)] = overlap

    # Canonical colour refinement of the circuit-intersection graph.  The final
    # coloured edge list records substantially more than a degree histogram,
    # but remains invariant under every permutation of generators/circuits.
    initial = [tuple(sorted(degrees[v] for v in circuit)) for circuit in circuit_list]
    palette = {value: rank for rank, value in enumerate(sorted(set(initial)))}
    colours = [palette[value] for value in initial]
    for _ in range(8):
        signatures = []
        for i in range(len(circuit_list)):
            neighbours = []
            for (a, b), overlap in intersections.items():
                if a == i:
                    neighbours.append((overlap, colours[b]))
                elif b == i:
                    neighbours.append((overlap, colours[a]))
            signatures.append((colours[i], tuple(sorted(neighbours))))
        palette = {
            value: rank for rank, value in enumerate(sorted(set(signatures)))
        }
        new_colours = [palette[value] for value in signatures]
        if new_colours == colours:
            break
        colours = new_colours
    coloured_edges = sorted(
        (min(colours[i], colours[j]), max(colours[i], colours[j]), overlap)
        for (i, j), overlap in intersections.items()
    )
    return {
        "d": inst["dimension"],
        "m": len(rows),
        "pair_bucket_sizes": sorted(bucket_sizes),
        "four_circuit_degrees": sorted(degrees),
        "four_circuit_profiles": circuit_profiles,
        "four_circuit_intersections": intersection_histogram,
        "four_circuit_coloured_edges": coloured_edges,
        "four_circuit_count": len(circuits),
    }


def canonical_key(inst) -> str:
    """Hash a structural invariant, never the seed, answer, or rendering."""

    blob = json.dumps(_canonical_invariant(inst), sort_keys=True, separators=(",", ":"))
    return "gf2-cayley-pendant:" + hashlib.sha256(blob.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase equation crowding and then dimension while the route stays <=300."""

    p = {k: v for k, v in dict(params).items() if k != "_preset"}
    n = int(p["n"])
    m = int(p.get("m", 3 * n))
    if m < 300:
        p["m"] = min(300, m + max(4, n // 6))
        p["n"] = min(p["m"], n + max(4, n // 8))
        return p
    if n < m:
        p["n"] = min(m, n + max(4, n // 8))
        p["m"] = m
        return p
    return "cap_bound"


def _gaussian_reference(inst) -> tuple[object | None, dict]:
    """Solve <w,s>=1 by exact GF(2) elimination and count scalar bit work."""

    d = inst["dimension"]
    basis: list[tuple[int, int] | None] = [None] * d
    row_xors = 0
    pivot_inspections = 0
    for encoded in inst["generators"]:
        row = int(encoded, 16)
        rhs = 1
        while row:
            p = row.bit_length() - 1
            pivot_inspections += 1
            if basis[p] is None:
                basis[p] = (row, rhs)
                break
            old_row, old_rhs = basis[p]
            row ^= old_row
            rhs ^= old_rhs
            row_xors += 1
        else:
            if rhs:
                return None, {
                    "row_xors": row_xors,
                    "pivot_inspections": pivot_inspections,
                    "scalar_bit_operations": row_xors * (d + 1) + pivot_inspections,
                }

    if any(entry is None for entry in basis):
        return None, {
            "row_xors": row_xors,
            "pivot_inspections": pivot_inspections,
            "scalar_bit_operations": row_xors * (d + 1) + pivot_inspections,
        }

    w = 0
    back_substitution_bits = 0
    for p in range(d):
        row, rhs = basis[p]  # type: ignore[misc]
        lower = row & ((1 << p) - 1)
        rhs ^= _parity(lower & w)
        back_substitution_bits += p + 1
        if rhs:
            w |= 1 << p
    counts = {
        "row_xors": row_xors,
        "pivot_inspections": pivot_inspections,
        "back_substitution_bits": back_substitution_bits,
        "scalar_bit_operations": (
            row_xors * (d + 1) + pivot_inspections + back_substitution_bits
        ),
    }
    return [format(w, f"0{inst['hex_width']}x"), 0], counts


def _compact_candidate(inst) -> object:
    w = _xor_all(int(s, 16) for s in inst["generators"])
    return [format(w, f"0{inst['hex_width']}x"), 0]


def _attack_candidates(inst, seed: int) -> dict[str, list[object]]:
    d = inst["dimension"]
    width = inst["hex_width"]
    rows = [int(s, 16) for s in inst["generators"]]

    # Per-row statistics: try every displayed element itself, ordered from the
    # largest Hamming-weight outlier inward.
    outliers = sorted(rows, key=lambda x: abs(x.bit_count() - d / 2), reverse=True)
    outlier_candidates = [[format(x, f"0{width}x"), 0] for x in outliers]

    # A left-to-right, no-elimination pivot rule that a solver can execute from
    # the displayed equations but that ignores interactions with later rows.
    greedy_w = 0
    assigned = 0
    for row in rows:
        free = row & ~assigned
        if free:
            bit = free & -free
            if _parity(greedy_w & row) == 0:
                greedy_w ^= bit
            assigned |= bit
    greedy = [[format(greedy_w or 1, f"0{width}x"), 0]]

    ones = (1 << d) - 1
    even_xor = _xor_all(rows[::2]) or 1
    first_half = _xor_all(rows[: len(rows) // 2]) or 1
    obvious = [
        [format(ones, f"0{width}x"), 0],
        [format(even_xor, f"0{width}x"), 0],
        [format(first_half, f"0{width}x"), 0],
    ]
    obvious.extend([[format(1 << j, f"0{width}x"), 0] for j in range(d)])

    rng = random.Random(seed ^ 0xC1A57E2)
    restarts = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_generator_as_functional": outlier_candidates,
        "greedy_pivot_without_elimination": greedy,
        "random_restart_256": restarts,
        "obvious_allones_units_partial_xors": obvious,
    }


def _permute_bits(x: int, order: list[int]) -> int:
    out = 0
    for old, new in enumerate(order):
        if (x >> old) & 1:
            out |= 1 << new
    return out


def _relabel_variants(inst, seed: int) -> list[dict]:
    """All nonempty compositions of three genuine graph relabellings."""

    d = inst["dimension"]
    width = inst["hex_width"]
    original_rows = [int(s, 16) for s in inst["generators"]]
    original_w = int(inst["answer"][0], 16)
    original_side = inst["answer"][1]
    variants = []

    for flags in range(1, 8):
        rows = list(original_rows)
        w = original_w
        side = original_side
        rng = random.Random(seed ^ flags)

        # Reordering generators does not change the edge set.
        if flags & 1:
            rng.shuffle(rows)

        # A coordinate permutation relabels every x and every pendant P_x.
        if flags & 2:
            order = list(range(d))
            rng.shuffle(order)
            rows = [_permute_bits(x, order) for x in rows]
            w = _permute_bits(w, order)

        # An affine relabelling combines the invertible shear y_i=x_i+x_j
        # with a translation. The dual functional changes by w'_j=w_j+w_i;
        # translation flips the named side when its inner product is one.
        if flags & 4:
            i = rng.randrange(d)
            j = rng.randrange(d - 1)
            if j >= i:
                j += 1

            def shear(x):
                return x ^ ((1 << i) if ((x >> j) & 1) else 0)

            rows = [shear(x) for x in rows]
            if (w >> i) & 1:
                w ^= 1 << j
            translation = rng.getrandbits(d)
            side ^= _parity(w & translation)

        transformed = dict(inst)
        transformed["generators"] = [format(x, f"0{width}x") for x in rows]
        transformed["answer"] = [format(w, f"0{width}x"), side]
        variants.append(transformed)
    return variants


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run all mandatory gates and return their measurements."""

    report: dict = {
        "paper": "arXiv:2007.08057",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    planted_checks = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "checks": planted_checks,
        "failures": planted_failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    corruptions = {
        "drop": answer[:1],
        "swap": [answer[1], answer[0]],
        "duplicate": [answer[0], answer[0]],
        "empty": [],
        "out_of_range": [format(1 << inst["dimension"], "x"), answer[1]],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The parity class is the requested optimum.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe matching lower bound is tight."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x200708057)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_density": 1 / ((1 << inst["dimension"]) - 1),
        "candidate_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_generator_as_functional",
        "greedy_pivot_without_elimination",
        "random_restart_256",
        "obvious_allones_units_partial_xors",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_ops = 0
    reference_row_xors = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)

        start = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        reference_ops += counts["scalar_bit_operations"]
        reference_row_xors += counts["row_xors"]
        compact_successes += int(verify(trial, _compact_candidate(trial))[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact Gaussian elimination on <w,s>=1 over GF(2)",
        "complexity": "O(m d^2) scalar-bit operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_ops // 8,
        "row_xors": reference_row_xors // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(successes[name] == 0 for name in attack_names)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "global XOR invariant",
            "solves": f"{compact_successes}/8",
            "operations": inst["generator_count"] - 1,
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 2
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_solution_density": guess_fraction,
        "shipping_exact_valid_answers": 2,
        "shipping_exact_density": 1 / ((1 << inst["dimension"]) - 1),
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_n = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    ladder_m = [DIFFICULTY[name]["m"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["dimension"] == 2 * inst["dimension"]
        and len(render(doubled)) > len(render(inst))
        and ladder_n == sorted(ladder_n)
        and ladder_m == sorted(ladder_m),
        "shipping_n": inst["dimension"],
        "shipping_m": inst["generator_count"],
        "doubled_n": doubled["dimension"],
        "doubled_m": doubled["generator_count"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "generator reordering",
            "GF(2) coordinate permutation with carried functional",
            "affine GF(2) shear/translation with inverse-dual functional and side",
            "all seven nonempty compositions of those three maps",
        ],
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    worst_answer_chars = len(
        json.dumps(["f" * inst["hex_width"], 1], separators=(",", ":"))
    )
    worst_answer_tokens = math.ceil(worst_answer_chars / 4)
    intended_operations = inst["generator_count"] - 1
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_answer_chars,
        "worst_case_answer_tokens": worst_answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
