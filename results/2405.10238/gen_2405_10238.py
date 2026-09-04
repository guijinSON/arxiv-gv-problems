"""Verified generator inspired by arXiv:2405.10238.

The instances are relabelled hypercube graphs.  A certificate is an affine
linear polynomial over GF(2) whose zero set is a maximum independent set.
Generation is inverse: the polynomial is sampled first, and the binary vertex
labels are then assigned around it.  The verifier never reads the planted
answer.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import deque


TRACK = "B"

STRUCTURAL_HINT = (
    "An XOR invariant links the binary labels to one vertex's graph neighborhood."
)
PLACEBO_HINT = (
    "Careful bookkeeping links the binary labels to the requested polynomial coefficients."
)

# Filled from the isolated harden.py runs after the shipping rung is known.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "regular hypercube graph",
        "vertex labels over GF(2)",
        "affine parity indicator polynomial",
    ],
    "verification_operations": [
        "GF(2) dot product",
        "exact cardinality comparison",
        "graph edge scan",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "XORing all labels exposes an anchor whose graph neighbors encode the "
        "sparse parity support; without that invariant one bipartitions the graph "
        "and solves a GF(2) linear system."
    ),
    "hardness_basis": (
        "Track B: Theorem 2/Algorithm 1 gives a polynomial-time constant-degree "
        "SoS route in this regime, while the concrete reference algorithm here is "
        "BFS bipartition plus GF(2) Gaussian elimination in "
        "O(|V|+|E|+|V|d^2); its shipping-preset wall time and field-operation "
        "count are measured by selftest, versus at most 263 XOR operations after "
        "the invariant is recognized."
    ),
    "max_answer_tokens": 32,
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

DIFFICULTY = {
    "demo": {"n": 16, "label_bits": 10, "weight": 4},
    "easy": {"n": 64, "label_bits": 36, "weight": 6},
    "medium": {"n": 128, "label_bits": 48, "weight": 7},
    "hard": {"n": 256, "label_bits": 64, "weight": 8},
}

SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "Affine polynomials P(x)=constant XOR the selected coordinates over "
        "GF(2), with constant in {0,1} and exactly weight distinct support "
        "indices from 0..label_bits-1."
    ),
    "bounds": {
        "degree": 1,
        "field_order": 2,
        "constant_choices": 2,
        "support_size_parameter": "weight",
        "coordinate_count_parameter": "label_bits",
    },
}

NOTES = (
    "Section 3.2 fixes the exact independent-set predicate, and Theorem 2 "
    "(restated as Theorem 4.1 with Algorithm 1) identifies the polynomial-time "
    "near-half/one-sided-expander regime, so this is honestly Track B. Section 7 "
    "defines the hypercube used here; Q_r is regular, has a side of size n/2, "
    "and normalized second eigenvalue 1-2/r, hence it satisfies Theorem 2 at "
    "epsilon=0.001 for every preset. The plant and decoys are labels sampled from "
    "the same parity-conditioned distribution except for a hidden affine frame. "
    "Coordinate bias, edge-flip scoring, random sparse restarts, and the obvious "
    "zero-label anchor ansatz are tested and defeated. A stronger affine-frame "
    "outlier attack, added after the oracle run exposed the omission, succeeds and "
    "therefore makes this retained experimental module fail G6. The exact BFS plus "
    "GF(2) elimination algorithm is reported separately because Track B expects it "
    "to succeed."
)


def _parity(x: int) -> int:
    return x.bit_count() & 1


def _xor_all(values):
    result = 0
    for value in values:
        result ^= value
    return result


def _validate_params(n: int, label_bits: int, weight: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n & (n - 1):
        raise ValueError("n must be a power of two and at least 8")
    cube_dim = n.bit_length() - 1
    if not isinstance(label_bits, int) or label_bits < 2:
        raise ValueError("label_bits must be an integer at least 2")
    if not isinstance(weight, int) or not (2 <= weight <= cube_dim):
        raise ValueError("weight must lie between 2 and log2(n)")
    if label_bits - weight > n // 2 - 1:
        raise ValueError("not enough even-side vertices for the affine frame")
    if label_bits >= n:
        raise ValueError("label_bits must be smaller than n")
    return cube_dim


def _sample_with_parity(rng, bits, mask, wanted, used):
    while True:
        x = rng.getrandbits(bits)
        if x not in used and _parity(x & mask) == wanted:
            return x


def _make_labels(rng, n, cube_dim, label_bits, support):
    mask = sum(1 << j for j in support)
    center = rng.getrandbits(label_bits)
    if _parity(center & mask):
        center ^= 1 << support[0]

    labels = {0: center}
    used = {center}

    # Every selected coordinate is encoded by one neighbor of the center.
    root_neighbors = [1 << j for j in range(cube_dim)]
    rng.shuffle(root_neighbors)
    for q, coordinate in zip(root_neighbors, support):
        value = center ^ (1 << coordinate)
        labels[q] = value
        used.add(value)

    # The remaining unit directions occur on the center's own bipartition side.
    even_vertices = [
        q for q in range(1, n)
        if _parity(q) == 0 and q not in labels
    ]
    rng.shuffle(even_vertices)
    nonsupport = [j for j in range(label_bits) if j not in set(support)]
    for q, coordinate in zip(even_vertices, nonsupport):
        value = center ^ (1 << coordinate)
        labels[q] = value
        used.add(value)

    fixed_vertices = set(labels)
    adjustable = [q for q in range(n) if q not in fixed_vertices]
    if not adjustable:
        raise ValueError("parameters leave no room to enforce the XOR invariant")

    # Random labels on each side have exactly the same conditional distribution.
    # Resample if the final XOR correction happens to collide with another label.
    for _ in range(1000):
        trial = dict(labels)
        trial_used = set(used)
        for q in adjustable:
            x = _sample_with_parity(
                rng, label_bits, mask, _parity(q), trial_used
            )
            trial[q] = x
            trial_used.add(x)

        total = _xor_all(trial.values())
        delta = total ^ center
        q_fix = adjustable[-1]
        old = trial[q_fix]
        new = old ^ delta
        # delta lies in the kernel of the planted functional, because each
        # bipartition side has even cardinality.
        if _parity(delta & mask):
            raise AssertionError("internal parity invariant failed")
        if new == old or new not in trial_used:
            trial[q_fix] = new
            if len(set(trial.values())) == n and _xor_all(trial.values()) == center:
                return [trial[q] for q in range(n)]
    raise RuntimeError("could not construct collision-free labels")


def make_instance(n, seed=0, **params):
    """Inverse-generate a labelled hypercube and a sparse parity certificate."""
    label_bits = params.pop("label_bits", max(10, 4 * (n.bit_length() - 1)))
    weight = params.pop("weight", n.bit_length() - 1)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    cube_dim = _validate_params(n, label_bits, weight)
    rng = random.Random(seed)

    support = sorted(rng.sample(range(label_bits), weight))
    labels_by_cube = _make_labels(
        rng, n, cube_dim, label_bits, support
    )

    vertex_of_cube = list(range(n))
    rng.shuffle(vertex_of_cube)
    labels = [0] * n
    for cube_vertex, vertex in enumerate(vertex_of_cube):
        labels[vertex] = labels_by_cube[cube_vertex]

    edges = []
    for q in range(n):
        for bit in range(cube_dim):
            other = q ^ (1 << bit)
            if q < other:
                u, v = vertex_of_cube[q], vertex_of_cube[other]
                edges.append([min(u, v), max(u, v)])
    rng.shuffle(edges)

    answer = {"constant": 0, "support": support}
    inst = {
        "n": n,
        "cube_dimension": cube_dim,
        "label_bits": label_bits,
        "weight": weight,
        "target_size": n // 2,
        "labels": labels,
        "edges": edges,
        "answer": answer,
    }
    ok, reason = verify(inst, answer)
    if not ok:
        raise AssertionError("constructed answer failed: " + reason)
    return inst


def _answer_text(answer):
    return json.dumps(answer, separators=(",", ":"), sort_keys=True)


def render(inst):
    width = (inst["label_bits"] + 3) // 4
    label_lines = [
        f"  {i}: {value:0{width}x}" for i, value in enumerate(inst["labels"])
    ]
    edge_lines = []
    chunk = []
    for u, v in inst["edges"]:
        chunk.append(f"({u},{v})")
        if len(chunk) == 12:
            edge_lines.append("  " + " ".join(chunk))
            chunk = []
    if chunk:
        edge_lines.append("  " + " ".join(chunk))

    example_support = list(range(inst["weight"]))
    example = _answer_text({"constant": 0, "support": example_support})
    statement = f"""Find a sparse affine parity polynomial defining a large independent set.

The undirected simple graph has vertices 0 through {inst['n'] - 1}. An independent
set is a set containing no pair joined by an edge. Each vertex also has a distinct
{inst['label_bits']}-bit label, written below as fixed-width hexadecimal. Bit position
0 is the least significant bit.

Your answer represents the affine polynomial over GF(2)

    P(x) = constant XOR (XOR of bit_j(x) for j in support).

The constant must be 0 or 1. The support must contain exactly {inst['weight']} distinct
indices from 0 through {inst['label_bits'] - 1}; order does not matter and repeats are
not allowed. Your polynomial is valid exactly when the vertices whose labels satisfy
P(label)=0 form an independent set of exactly {inst['target_size']} vertices.

Vertex labels (vertex: hexadecimal label):
{chr(10).join(label_lines)}

Edges (each unordered pair appears once):
{chr(10).join(edge_lines)}
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\nHint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        statement += "\nHint: " + PLACEBO_HINT + "\n"
    statement += f"""
Give your final answer inside <answer></answer> tags as one JSON object with
keys \"constant\" and \"support\". List support indices as decimal integers.
Format example only: <answer>{example}</answer>
Output nothing else inside the tags.
"""
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    if match:
        payload = match.group(1).strip()
    else:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.I | re.S)
        if fenced:
            payload = fenced.group(1)
        else:
            obj = re.search(r"\{[^{}]*\}", text, re.S)
            if not obj:
                return None
            payload = obj.group(0)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def verify(inst, answer):
    if not isinstance(answer, dict) or set(answer) != {"constant", "support"}:
        return False, "answer must be an object with exactly constant and support"
    constant = answer["constant"]
    support = answer["support"]
    if isinstance(constant, bool) or not isinstance(constant, int) or constant not in (0, 1):
        return False, "constant must be the integer 0 or 1"
    if not isinstance(support, list):
        return False, "support must be a list"
    if len(support) != inst["weight"]:
        return False, f"support must contain exactly {inst['weight']} indices"
    if any(isinstance(j, bool) or not isinstance(j, int) for j in support):
        return False, "support indices must be integers"
    if len(set(support)) != len(support):
        return False, "support indices must be distinct"
    if any(j < 0 or j >= inst["label_bits"] for j in support):
        return False, "support index out of range"

    mask = sum(1 << j for j in support)
    selected = [
        (_parity(label & mask) ^ constant) == 0 for label in inst["labels"]
    ]
    size = sum(selected)
    if size != inst["target_size"]:
        return False, f"polynomial zero set has size {size}, expected {inst['target_size']}"
    for u, v in inst["edges"]:
        if selected[u] and selected[v]:
            return False, f"polynomial zero set contains edge ({u},{v})"
    return True, "ok"


def random_candidate(inst, rng):
    return {
        "constant": rng.randrange(2),
        "support": sorted(rng.sample(range(inst["label_bits"]), inst["weight"])),
    }


def search_space(inst):
    return 2 * math.comb(inst["label_bits"], inst["weight"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 50_000:
        return None
    import itertools

    count = 0
    for support in itertools.combinations(range(inst["label_bits"]), inst["weight"]):
        for constant in (0, 1):
            if verify(inst, {"constant": constant, "support": list(support)})[0]:
                count += 1
    return count


def canonical_key(inst):
    """A structural metric invariant, not a hash of seed or rendered text.

    Hamming distances survive coordinate permutations and global XOR translations.
    The two histograms below also survive vertex renumbering and edge reordering.
    """
    n = inst["n"]
    d = inst["label_bits"]
    labels = inst["labels"]
    adjacency = [set() for _ in range(n)]
    edge_hist = [0] * (d + 1)
    for u, v in inst["edges"]:
        adjacency[u].add(v)
        adjacency[v].add(u)
        edge_hist[(labels[u] ^ labels[v]).bit_count()] += 1

    pair_hist = [0] * (d + 1)
    vertex_signatures = []
    for u in range(n):
        all_dist = [0] * (d + 1)
        edge_dist = [0] * (d + 1)
        for v in range(n):
            if u == v:
                continue
            distance = (labels[u] ^ labels[v]).bit_count()
            all_dist[distance] += 1
            if v in adjacency[u]:
                edge_dist[distance] += 1
            if u < v:
                pair_hist[distance] += 1
        vertex_signatures.append((tuple(all_dist), tuple(edge_dist)))
    payload = repr(
        (n, d, inst["weight"], tuple(pair_hist), tuple(edge_hist),
         tuple(sorted(vertex_signatures)))
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    harder = dict(params)
    harder.pop("_preset", None)
    # Fixed witness length: add decoy coordinates while keeping the graph and
    # polynomial support size fixed.  This grows C(d,w) without transcription.
    maximum = harder["n"] // 2 - 1 + harder["weight"]
    if harder["label_bits"] + 8 > maximum:
        return "cap_bound"
    harder["label_bits"] += 8
    return harder


def _adjacency(inst):
    adj = [[] for _ in range(inst["n"])]
    for u, v in inst["edges"]:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def _reference_solve(inst):
    """BFS bipartition, then exact GF(2) Gauss-Jordan elimination."""
    started = time.perf_counter()
    adj = _adjacency(inst)
    color = [-1] * inst["n"]
    operations = 0
    for start in range(inst["n"]):
        if color[start] != -1:
            continue
        color[start] = 0
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                operations += 1
                if color[v] == -1:
                    color[v] = color[u] ^ 1
                    queue.append(v)
                elif color[v] == color[u]:
                    return None, operations, time.perf_counter() - started

    variables = inst["label_bits"] + 1  # support bits, then affine constant
    rows = []
    for label, rhs in zip(inst["labels"], color):
        coeff = label | (1 << inst["label_bits"])
        rows.append(coeff | (rhs << variables))

    rank = 0
    for column in range(variables):
        pivot = None
        for i in range(rank, len(rows)):
            operations += 1
            if (rows[i] >> column) & 1:
                pivot = i
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(len(rows)):
            if i == rank:
                continue
            operations += 1
            if (rows[i] >> column) & 1:
                rows[i] ^= rows[rank]
                # Count the packed row XOR as scalar GF(2) operations.
                operations += variables
        rank += 1
        if rank == variables:
            break
    if rank != variables:
        return None, operations, time.perf_counter() - started

    solution = 0
    for row in rows[:rank]:
        coeff = row & ((1 << variables) - 1)
        pivot_column = (coeff & -coeff).bit_length() - 1
        rhs = (row >> variables) & 1
        if rhs:
            solution |= 1 << pivot_column
    support_mask = solution & ((1 << inst["label_bits"]) - 1)
    answer = {
        "constant": (solution >> inst["label_bits"]) & 1,
        "support": [
            j for j in range(inst["label_bits"]) if (support_mask >> j) & 1
        ],
    }
    return answer, operations, time.perf_counter() - started


def _candidate_succeeds(inst, support):
    if len(support) != inst["weight"] or len(set(support)) != len(support):
        return False
    return any(
        verify(inst, {"constant": constant, "support": sorted(support)})[0]
        for constant in (0, 1)
    )


def _attack_coordinate_bias(inst):
    n = inst["n"]
    scores = []
    for bit in range(inst["label_bits"]):
        ones = sum((label >> bit) & 1 for label in inst["labels"])
        scores.append((abs(2 * ones - n), bit))
    support = [bit for _, bit in sorted(scores, reverse=True)[:inst["weight"]]]
    return _candidate_succeeds(inst, support)


def _attack_edge_flip(inst):
    scores = []
    for bit in range(inst["label_bits"]):
        flips = sum(((inst["labels"][u] ^ inst["labels"][v]) >> bit) & 1
                    for u, v in inst["edges"])
        scores.append((flips, bit))
    support = [bit for _, bit in sorted(scores, reverse=True)[:inst["weight"]]]
    return _candidate_succeeds(inst, support)


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed)
    for _ in range(restarts):
        answer = random_candidate(inst, rng)
        if verify(inst, answer)[0]:
            return True
    return False


def _attack_zero_anchor(inst):
    adj = _adjacency(inst)
    center_vertex = min(range(inst["n"]), key=lambda v: inst["labels"][v])
    center = inst["labels"][center_vertex]
    guessed = []
    for v in adj[center_vertex]:
        delta = center ^ inst["labels"][v]
        if delta and delta & (delta - 1) == 0:
            guessed.append(delta.bit_length() - 1)
    for bit in range(inst["label_bits"]):
        if len(guessed) >= inst["weight"]:
            break
        if bit not in guessed:
            guessed.append(bit)
    return _candidate_succeeds(inst, guessed[:inst["weight"]])


def _attack_affine_frame_outlier(inst):
    """Find the unique label with a conspicuously complete radius-one frame."""
    labels = inst["labels"]
    center_vertex = max(
        range(inst["n"]),
        key=lambda u: sum(
            1
            for v in range(inst["n"])
            if u != v
            and (labels[u] ^ labels[v]) != 0
            and ((labels[u] ^ labels[v]) & ((labels[u] ^ labels[v]) - 1)) == 0
        ),
    )
    adj = _adjacency(inst)
    support = []
    for v in adj[center_vertex]:
        delta = labels[center_vertex] ^ labels[v]
        if delta and delta & (delta - 1) == 0:
            support.append(delta.bit_length() - 1)
    return _candidate_succeeds(inst, support)


def _transform_vertex_permutation(inst, rng):
    p = list(range(inst["n"]))
    rng.shuffle(p)
    transformed = dict(inst)
    labels = [0] * inst["n"]
    for old, new in enumerate(p):
        labels[new] = inst["labels"][old]
    transformed["labels"] = labels
    transformed["edges"] = [[p[u], p[v]] for u, v in reversed(inst["edges"])]
    transformed["answer"] = dict(inst["answer"])
    return transformed


def _transform_coordinates(inst, rng):
    p = list(range(inst["label_bits"]))
    rng.shuffle(p)

    def permute_bits(value):
        result = 0
        for old, new in enumerate(p):
            if (value >> old) & 1:
                result |= 1 << new
        return result

    transformed = dict(inst)
    transformed["labels"] = [permute_bits(x) for x in inst["labels"]]
    transformed["edges"] = [list(reversed(edge)) for edge in reversed(inst["edges"])]
    answer = inst["answer"]
    transformed["answer"] = {
        "constant": answer["constant"],
        "support": sorted(p[j] for j in answer["support"]),
    }
    return transformed


def _transform_translation(inst, rng):
    translation = rng.getrandbits(inst["label_bits"])
    transformed = dict(inst)
    transformed["labels"] = [x ^ translation for x in inst["labels"]]
    support_mask = sum(1 << j for j in inst["answer"]["support"])
    transformed["answer"] = {
        "constant": inst["answer"]["constant"] ^ _parity(support_mask & translation),
        "support": list(inst["answer"]["support"]),
    }
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    planted_checks = 0
    json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError((preset, seed, reason))
            planted_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "checks": planted_checks,
        "json_native_checks": json_checks,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12345, **shipping)
    good = inst["answer"]
    outside = next(j for j in range(inst["label_bits"]) if j not in good["support"])
    corruptions = {
        "drop_one": {"constant": good["constant"], "support": good["support"][:-1]},
        "swap_one": {"constant": good["constant"],
                     "support": good["support"][:-1] + ["x"]},
        "duplicate": {"constant": good["constant"],
                      "support": good["support"][:-1] + [good["support"][0]]},
        "empty": {},
        "out_of_range": {"constant": good["constant"],
                         "support": good["support"][:-1] + [inst["label_bits"]]},
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        if ok:
            raise AssertionError(name + " corruption accepted")
        reasons[name] = reason
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError("corruption reasons are not distinct")
    # Also reject a shape-correct wrong polynomial.
    wrong_support = good["support"][:-1] + [outside]
    if verify(inst, {"constant": 0, "support": wrong_support})[0] or verify(
        inst, {"constant": 1, "support": wrong_support}
    )[0]:
        raise AssertionError("shape-correct corruption accepted")
    report["G2_rejects_corruption"] = {
        "pass": True,
        "rejected": len(corruptions) + 2,
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    model_style = (
        "I used the parity constraints and obtained:\n```json\n<answer>"
        + _answer_text(good)
        + "</answer>\n```\nThis is my final result."
    )
    parsed = parse_answer(model_style)
    roundtrip_ok = parsed == good and verify(inst, parsed)[0]
    report["G3_round_trip"] = {"pass": roundtrip_ok, "parsed": parsed}

    samples = 200_000
    hits = 0
    sample_rng = random.Random(240510238)
    density_inst = make_instance(seed=2024, **shipping)
    for _ in range(samples):
        if verify(density_inst, random_candidate(density_inst, sample_rng))[0]:
            hits += 1
    exact_density = 2 / search_space(density_inst)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_fraction": hits / samples,
        "exact_family_density": exact_density,
        "candidate_space": search_space(density_inst),
    }

    panel_seeds = list(range(31000, 31008))
    attacks = {
        "outlier_coordinate_bias": 0,
        "greedy_edge_flip_score": 0,
        "random_restart_256": 0,
        "obvious_zero_anchor_ansatz": 0,
        "affine_frame_outlier": 0,
    }
    reference_successes = 0
    reference_operations = []
    reference_times = []
    attack_started = time.perf_counter()
    for seed in panel_seeds:
        attack_inst = make_instance(seed=seed, **shipping)
        attacks["outlier_coordinate_bias"] += int(_attack_coordinate_bias(attack_inst))
        attacks["greedy_edge_flip_score"] += int(_attack_edge_flip(attack_inst))
        attacks["random_restart_256"] += int(
            _attack_random_restart(attack_inst, seed ^ 0xA5A5A5A5)
        )
        attacks["obvious_zero_anchor_ansatz"] += int(_attack_zero_anchor(attack_inst))
        attacks["affine_frame_outlier"] += int(_attack_affine_frame_outlier(attack_inst))
        ref_answer, operations, elapsed = _reference_solve(attack_inst)
        reference_successes += int(ref_answer is not None and verify(attack_inst, ref_answer)[0])
        reference_operations.append(operations)
        reference_times.append(elapsed)
    attack_elapsed = time.perf_counter() - attack_started
    attack_report = {
        name: {"successes": successes, "attempts": len(panel_seeds)}
        for name, successes in attacks.items()
    }
    panel_pass = all(result["successes"] == 0 for result in attack_report.values())
    reference = {
        "name": "BFS bipartition plus GF(2) Gauss-Jordan elimination",
        "complexity": "O(|V|+|E|+|V|*label_bits^2) GF(2) operations",
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "successes": reference_successes,
        "attempts": len(panel_seeds),
        "solves": f"{reference_successes}/{len(panel_seeds)}, as expected",
    }
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and panel_pass and reference_successes == len(panel_seeds),
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "shipping_sampled_density": hits / samples,
        "theoretical_solution_count": 2,
        "candidate_space": search_space(density_inst),
        "theoretical_solution_fraction": exact_density,
        "strongest_failing_attack_wall_sec": attack_elapsed,
        "strongest_failing_attack_restarts": 256 * len(panel_seeds),
        "reference_operations_max": max(reference_operations),
        "reference_wall_sec_max": max(reference_times),
    }
    report["G6_adversary_panel"] = {
        "pass": panel_pass and reference_successes == len(panel_seeds),
        "attacks": attack_report,
        "reference_algorithm": reference,
    }

    doubled = dict(shipping)
    doubled["n"] *= 2
    larger = make_instance(seed=777, **doubled)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and search_space(larger) >= search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_verifies": larger_ok,
        "reason": larger_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    transform_rng = random.Random(88008)
    for seed in range(20):
        base = make_instance(seed=40000 + seed, **shipping)
        key = canonical_key(base)
        unrelated_keys.append(key)
        variants = [
            _transform_vertex_permutation(base, transform_rng),
            _transform_coordinates(base, transform_rng),
            _transform_translation(base, transform_rng),
        ]
        # One composition exercises interactions between relabellings.
        variants.append(
            _transform_vertex_permutation(
                _transform_coordinates(
                    _transform_translation(base, transform_rng), transform_rng
                ),
                transform_rng,
            )
        )
        for variant in variants:
            if canonical_key(variant) != key:
                raise AssertionError("canonical key changed under a valid relabelling")
            invariant_checks += 1
            if not verify(variant, variant["answer"])[0]:
                raise AssertionError("relabelling did not carry the witness")
            carried_checks += 1
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80 and carried_checks == 80 and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "transformations": [
            "vertex permutation plus edge reorder/orientation",
            "label-coordinate permutation",
            "global label XOR translation",
            "composition of all three",
        ],
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = shipping["n"] - 1 + shipping["weight"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
