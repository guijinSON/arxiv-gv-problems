"""Verified problem generator for arXiv:1401.2436.

The family uses the paper's 3XOR-to-graph gadget verbatim.  A submitted key is a
bounded symbolic recipe for the vertex bijection constructed in the proof of the
Completeness Lemma; verification expands that bijection and compares graph edges.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The checksum masks hide an affine circulant basis: XOR each with "
    "D=d6a39c5e71b428f09d3c6a57, match the 96 rotations of "
    "Q=72e5cb972e5cb972e5cb972e, XOR those right sides with the D-row, and recover "
    "the key as z XOR rotate-right(z,1) XOR rotate-right(z,3)."
)
PLACEBO_HINT: str = (
    "The checksum masks use a fixed-width hexadecimal convention: keep careful "
    "track of leading zeroes, one-based bit positions, right sides, and the exact "
    "requested output cardinality before committing to the final key, and check "
    "all graph conventions twice."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "a pair of CFI-style gadget graphs defined by 3XOR constraints",
        "GF(2) variable decoder masks",
    ],
    "verification_operations": [
        "GF(2) parity evaluation",
        "exact expansion of the graph-vertex bijection",
        "integer edge-set comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3 (gadget graph and 3XOR encoding) and Section 4, Completeness "
        "Lemma: a satisfying 3XOR assignment induces the checked graph isomorphism"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Cancel a shared affine mask, recognize a cyclic basis, and invert its "
        "three-tap transpose; without this change of variables one must row-reduce "
        "the dense-looking GF(2) checksum system."
    ),
    "hardness_basis": (
        "Track B: exact GF(2) Gaussian elimination solves the compressed system in "
        "O(mk^2) bit operations and at shipping n=120 took a median 134,649 counted "
        "bit operations and about 0.0010 seconds over eight seeds, whereas the circulant "
        "change of variables uses 292 exact word operations."
    ),
    "max_answer_tokens": 37,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 12, "key_bits": 6, "decoys": 1},
    "easy": {"n": 120, "key_bits": 96, "decoys": 2},
    "medium": {"n": 132, "key_bits": 96, "decoys": 10},
    "hard": {"n": 148, "key_bits": 96, "decoys": 20},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing list of exactly key_bits/2 distinct one-based bit "
        "positions from 1..key_bits; it denotes the fixed-weight GF(2) key whose "
        "public decoder expands to a graph-vertex bijection."
    ),
    "bounds": {
        "max_key_bits": 96,
        "max_selected_positions": 48,
        "index_base": 1,
        "coefficient_bits": 1,
    },
}

NOTES: str = (
    "Section 2 fixes alpha-isomorphism as the fraction of source edges preserved, "
    "normalized by the larger edge count. Section 3 defines the ten-vertex 3XOR "
    "gadget and the whole-instance graph, and Section 4's Completeness Lemma gives "
    "the assignment-to-bijection certificate used here. Theorem 1.2 is only a "
    "conditional Track-A statement for the paper's noisy random-3XOR reduction; its "
    "soundness proof uses m=cn with c at least 10^10, so this finite benchmark does "
    "not claim that theorem's average-case regime. The Introduction explicitly says "
    "Gaussian elimination solves satisfiable XOR instances; it also records efficient "
    "robust isomorphism for trees, an additive PTAS for dense approximate instances, "
    "and Weisfeiler--Lehman success on almost all G(n,1/2) graphs. Consequently this "
    "is honest Track B. The planted key is sampled first, checksum equations are "
    "assembled around it, and the Completeness bijection is then carried through the "
    "paper's gadget. Dense affine masks defeat raw sparse propagation and marginal "
    "outliers; shuffled constraints defeat prefix reading; constant-weight pair-swap "
    "greedy and random restarts are measured explicitly."
)

# Populated only from scripts/harden.py evidence.  During construction, "pending"
# deliberately makes G9 fail rather than manufacturing a hardness result.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _mask(k):
    return (1 << k) - 1


def _rotl(x, amount, k):
    amount %= k
    if amount == 0:
        return x & _mask(k)
    return ((x << amount) | (x >> (k - amount))) & _mask(k)


def _rotr(x, amount, k):
    return _rotl(x, -amount, k)


def _circulant_inverse(k):
    """Inverse of multiplication by 1+x+x^3 modulo x^k-1."""
    tap = 1 | (1 << 1) | (1 << 3)
    rows = []
    for output_bit in range(k):
        coeff = 0
        for input_bit in range(k):
            if (_rotl(tap, input_bit, k) >> output_bit) & 1:
                coeff |= 1 << input_bit
        rows.append([coeff, int(output_bit == 0)])

    pivot_row = 0
    for col in range(k):
        pivot = next(
            (r for r in range(pivot_row, k) if (rows[r][0] >> col) & 1),
            None,
        )
        if pivot is None:
            raise ValueError("key_bits makes the three-tap circulant singular")
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(k):
            if r != pivot_row and ((rows[r][0] >> col) & 1):
                rows[r][0] ^= rows[pivot_row][0]
                rows[r][1] ^= rows[pivot_row][1]
        pivot_row += 1
    inverse = 0
    for bit, row in enumerate(rows):
        if row[1]:
            inverse |= 1 << bit
    return inverse


def _offset(k):
    constant = int("d6a39c5e71b428f09d3c6a57", 16)
    return constant & _mask(k)


def _rank_binary(rows, ncols):
    rows = list(rows)
    rank = 0
    for col in range(ncols):
        pivot = next(
            (r for r in range(rank, len(rows)) if (rows[r] >> col) & 1),
            None,
        )
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(rank + 1, len(rows)):
            if (rows[r] >> col) & 1:
                rows[r] ^= rows[rank]
        rank += 1
        if rank == len(rows):
            break
    return rank


def _sample_full_row_rank_triples(n, m, rng):
    for _ in range(200):
        seen = set()
        triples = []
        while len(triples) < m:
            triple = tuple(sorted(rng.sample(range(n), 3)))
            if triple not in seen:
                seen.add(triple)
                triples.append(triple)
        rows = [sum(1 << i for i in triple) for triple in triples]
        if _rank_binary(rows, n) == m:
            return triples, rows
    raise RuntimeError("could not construct a full-row-rank 3XOR incidence matrix")


def _solve_variable_masks(rows, right_masks, n, key_bits, rng):
    """Solve A*U=R with random free rows; this does not solve the planted key."""
    m = len(rows)
    coeff = list(rows)
    rhs = list(right_masks)
    pivots = []
    rank = 0
    for col in range(n):
        pivot = next((r for r in range(rank, m) if (coeff[r] >> col) & 1), None)
        if pivot is None:
            continue
        coeff[rank], coeff[pivot] = coeff[pivot], coeff[rank]
        rhs[rank], rhs[pivot] = rhs[pivot], rhs[rank]
        for r in range(m):
            if r != rank and ((coeff[r] >> col) & 1):
                coeff[r] ^= coeff[rank]
                rhs[r] ^= rhs[rank]
        pivots.append(col)
        rank += 1
        if rank == m:
            break
    if rank != m:
        raise ValueError("incidence rows are not independent")

    pivot_set = set(pivots)
    free = [col for col in range(n) if col not in pivot_set]
    limit = _mask(key_bits)
    for _ in range(200):
        values = [0] * n
        for col in free:
            values[col] = rng.getrandbits(key_bits) & limit
        for r in range(m - 1, -1, -1):
            value = rhs[r]
            residue = coeff[r] & ~(1 << pivots[r])
            while residue:
                low = residue & -residue
                value ^= values[low.bit_length() - 1]
                residue ^= low
            values[pivots[r]] = value & limit
        if 0 not in values and len(set(values)) == n:
            return values
    raise RuntimeError("could not obtain distinct nonzero decoder masks")


def _structured_checksums(key_bits, decoys, rng):
    q = _circulant_inverse(key_bits)
    d = _offset(key_bits)
    special = [d] + [d ^ _rotl(q, i, key_bits) for i in range(key_bits)]
    forbidden = set(special)
    checksums = list(special)
    while len(checksums) < len(special) + decoys:
        candidate = rng.getrandbits(key_bits)
        if candidate not in forbidden:
            forbidden.add(candidate)
            checksums.append(candidate)
    rng.shuffle(checksums)
    return checksums


def _key_from_answer(answer):
    key = 0
    for position in answer:
        key |= 1 << (position - 1)
    return key


def _answer_from_key(key, key_bits):
    return [i + 1 for i in range(key_bits) if (key >> i) & 1]


def make_instance(n, seed=0, key_bits=96, decoys=2, **params) -> dict:
    """Inverse-generate a key and carry its certificate through the paper's gadget."""
    del params
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if isinstance(key_bits, bool) or not isinstance(key_bits, int):
        raise ValueError("key_bits must be an integer")
    if isinstance(decoys, bool) or not isinstance(decoys, int) or decoys < 0:
        raise ValueError("decoys must be a nonnegative integer")
    if key_bits < 4 or key_bits % 2:
        raise ValueError("key_bits must be an even integer at least 4")
    # 1+x+x^3 is singular for some cycle lengths; fail explicitly rather than
    # silently changing the certificate language.
    _circulant_inverse(key_bits)
    m = key_bits + 1 + decoys
    if n < m + 3:
        raise ValueError("n must be at least key_bits + decoys + 4")

    rng = random.Random(seed)
    chosen = rng.sample(range(key_bits), key_bits // 2)
    key = sum(1 << bit for bit in chosen)

    checksums = _structured_checksums(key_bits, decoys, rng)
    triples, incidence = _sample_full_row_rank_triples(n, m, rng)
    variable_masks = _solve_variable_masks(
        incidence, checksums, n, key_bits, rng
    )

    constraints = []
    for triple, checksum in zip(triples, checksums):
        computed = (
            variable_masks[triple[0]]
            ^ variable_masks[triple[1]]
            ^ variable_masks[triple[2]]
        )
        if computed != checksum:
            raise AssertionError("internal decoder-mask solve failed")
        rhs = (checksum & key).bit_count() & 1
        constraints.append([list(triple), rhs, checksum])

    return {
        "family": "compressed CFI graph isomorphism from exact 3XOR",
        "n": n,
        "m": m,
        "key_bits": key_bits,
        "key_weight": key_bits // 2,
        "decoys": decoys,
        "variable_masks": variable_masks,
        "constraints": constraints,
        "graph_vertex_count": 2 * n + 4 * m,
        "graph_edge_count": n + 18 * m,
        "answer": _answer_from_key(key, key_bits),
    }


def _hex(value, bits):
    return f"{value:0{(bits + 3) // 4}x}"


def render(inst) -> str:
    n = inst["n"]
    m = inst["m"]
    bits = inst["key_bits"]
    weight = inst["key_weight"]
    mask_lines = []
    for start in range(0, n, 4):
        chunk = []
        for i in range(start, min(start + 4, n)):
            chunk.append(f"{i + 1}:{_hex(inst['variable_masks'][i], bits)}")
        mask_lines.append("  " + "  ".join(chunk))
    constraint_lines = []
    for number, (triple, rhs, checksum) in enumerate(inst["constraints"], 1):
        a, b, c = (x + 1 for x in triple)
        constraint_lines.append(
            f"  {number}: {a} {b} {c} | {rhs} | {_hex(checksum, bits)}"
        )

    statement = f"""COMPRESSED ISOMORPHISM OF TWO 3XOR GADGET GRAPHS

All bit arithmetic below is over GF(2): XOR is addition, AND is bitwise AND,
and parity(x) is the number of 1-bits of x modulo 2. Hexadecimal masks have
exactly {bits} bits. Bit positions are numbered 1 through {bits} from least
significant to most significant.

The instance defines two undirected simple graphs G and H from n={n} Boolean
variables and m={m} equations. Each equation row has the format
"number: i j k | b | r" and means x_i XOR x_j XOR x_k = b. The final mask r
is an exact redundant checksum U_i XOR U_j XOR U_k, included so it may be
recomputed or used directly.

Here are the public variable masks U_i:
{chr(10).join(mask_lines)}

Here are the equations:
{chr(10).join(constraint_lines)}

The graph construction is part of the instance. In G, variable i has two
vertices (i,0) and (i,1), joined by an edge. Equation e on i,j,k has four
vertices (e,a_i,a_j,a_k), one for each bit triple with
a_i XOR a_j XOR a_k=b. Those four vertices form a clique, and each is joined
to the three consistent variable vertices (i,a_i),(j,a_j),(k,a_k).
The graph H is built identically on the same equation triples except that every
right side is 0. Thus each graph has {inst['graph_vertex_count']} vertices and
{inst['graph_edge_count']} edges. These definitions specify every vertex and
edge; there are no colors, loops, parallel edges, or omitted edges.

Your answer is a compressed isomorphism key T. It must be a strictly increasing
list of exactly {weight} distinct positions from 1..{bits}. Let K have 1-bits
exactly at T, and define tau_i=parity(U_i AND K). The decoded vertex map is
  (i,a) -> (i,a XOR tau_i),
  (e,a_i,a_j,a_k) ->
      (e,a_i XOR tau_i,a_j XOR tau_j,a_k XOR tau_k).
Find T for which this decoded map is a bijection carrying every edge of G to an
edge of H. The checker expands the map and compares the two exact edge sets.
Order in T is therefore fixed, repeats are forbidden, and all bounds are
inclusive.

Give your final answer inside <answer></answer> tags, as comma-separated decimal
integers in strictly increasing order. A format example (not an answer to this
instance) is <answer>1, 7, 12</answer>.
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S)
    body = body.strip()
    if body == "":
        return []
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, list):
            return None
        if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
            return None
        return value
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(part.strip()) for part in body.split(",")]
    except ValueError:
        return None


def _assignments(rhs):
    return [
        (a, b, c)
        for a in (0, 1)
        for b in (0, 1)
        for c in (0, 1)
        if (a ^ b ^ c) == rhs
    ]


def _graph_edges(inst, homogeneous):
    n = inst["n"]
    edges = set()
    for i in range(n):
        edges.add((2 * i, 2 * i + 1))
    for e, (triple, rhs, _checksum) in enumerate(inst["constraints"]):
        local_rhs = 0 if homogeneous else rhs
        assignments = _assignments(local_rhs)
        base = 2 * n + 4 * e
        for p in range(4):
            for q in range(p + 1, 4):
                edges.add((base + p, base + q))
        for p, assignment in enumerate(assignments):
            vertex = base + p
            for variable, value in zip(triple, assignment):
                other = 2 * variable + value
                edges.add((min(vertex, other), max(vertex, other)))
    return edges


def _decoded_permutation(inst, key):
    n = inst["n"]
    tau = [(mask & key).bit_count() & 1 for mask in inst["variable_masks"]]
    total = inst["graph_vertex_count"]
    permutation = [-1] * total
    for i, bit in enumerate(tau):
        permutation[2 * i] = 2 * i + bit
        permutation[2 * i + 1] = 2 * i + (1 ^ bit)
    for e, (triple, rhs, _checksum) in enumerate(inst["constraints"]):
        source = _assignments(rhs)
        target = _assignments(0)
        target_index = {assignment: i for i, assignment in enumerate(target)}
        base = 2 * n + 4 * e
        for p, assignment in enumerate(source):
            image_assignment = tuple(
                value ^ tau[variable]
                for variable, value in zip(triple, assignment)
            )
            q = target_index.get(image_assignment)
            if q is None:
                return None
            permutation[base + p] = base + q
    return permutation


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a list of integer bit positions"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every key position must be an integer"
    if any(x < 1 or x > inst["key_bits"] for x in answer):
        return False, f"key positions must lie in 1..{inst['key_bits']}"
    if len(set(answer)) != len(answer):
        return False, "key positions must be distinct"
    if answer != sorted(answer):
        return False, "key positions must be in strictly increasing order"
    if len(answer) != inst["key_weight"]:
        return False, f"key must contain exactly {inst['key_weight']} positions"

    key = _key_from_answer(answer)
    for e, (triple, rhs, checksum) in enumerate(inst["constraints"], 1):
        actual_checksum = (
            inst["variable_masks"][triple[0]]
            ^ inst["variable_masks"][triple[1]]
            ^ inst["variable_masks"][triple[2]]
        )
        if actual_checksum != checksum:
            return False, f"instance checksum mismatch in equation {e}"
        if ((checksum & key).bit_count() & 1) != rhs:
            return False, f"decoded assignment violates equation {e}"

    permutation = _decoded_permutation(inst, key)
    if permutation is None:
        return False, "decoded equation-vertex image does not exist in H"
    if sorted(permutation) != list(range(inst["graph_vertex_count"])):
        return False, "decoded vertex map is not a bijection"
    source_edges = _graph_edges(inst, homogeneous=False)
    target_edges = _graph_edges(inst, homogeneous=True)
    mapped = {
        tuple(sorted((permutation[u], permutation[v]))) for u, v in source_edges
    }
    if mapped != target_edges:
        return False, "decoded bijection does not carry the exact edge set of G to H"
    return True, "ok"


def random_candidate(inst, rng):
    return sorted(rng.sample(range(1, inst["key_bits"] + 1), inst["key_weight"]))


def search_space(inst):
    return math.comb(inst["key_bits"], inst["key_weight"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for answer in itertools.combinations(
        range(1, inst["key_bits"] + 1), inst["key_weight"]
    ):
        if verify(inst, list(answer))[0]:
            count += 1
    return count


def canonical_key(inst):
    """Cheap invariant under variable, equation, and decoder-bit relabelling.

    Exact isomorphism of this three-sorted incidence structure is itself a graph
    isomorphism problem.  We therefore use deterministic relational 1-WL: variable
    nodes meet equation nodes through I-edges and decoder-bit nodes through M-edges;
    equation right sides are initial colors.  The stabilized color/edge histogram
    is an isomorphism invariant, though not a complete canonical form.
    """
    n = inst["n"]
    m = inst["m"]
    k = inst["key_bits"]
    total = n + m + k
    adjacency = [[] for _ in range(total)]
    edges = []

    def add_edge(u, v, edge_type):
        adjacency[u].append((edge_type, v))
        adjacency[v].append((edge_type, u))
        edges.append((edge_type, u, v))

    for e, (triple, _rhs, _checksum) in enumerate(inst["constraints"]):
        equation_node = n + e
        for variable in triple:
            add_edge(variable, equation_node, "I")
    for variable, mask in enumerate(inst["variable_masks"]):
        residue = mask
        while residue:
            low = residue & -residue
            bit = low.bit_length() - 1
            add_edge(variable, n + m + bit, "M")
            residue ^= low

    # Variable, RHS-0 equation, RHS-1 equation, and bit-coordinate nodes begin
    # in four disjoint color classes.
    colors = [0] * n
    colors += [1 + row[1] for row in inst["constraints"]]
    colors += [3] * k
    for _ in range(total):
        signatures = [
            (colors[u], tuple(sorted((kind, colors[v]) for kind, v in adjacency[u])))
            for u in range(total)
        ]
        palette = {
            signature: color
            for color, signature in enumerate(sorted(set(signatures)))
        }
        refined = [palette[signature] for signature in signatures]
        if len(set(refined)) == len(set(colors)):
            colors = refined
            break
        colors = refined

    color_counts = {}
    for color in colors:
        color_counts[color] = color_counts.get(color, 0) + 1
    edge_color_counts = {}
    for kind, u, v in edges:
        a, b = sorted((colors[u], colors[v]))
        item = (kind, a, b)
        edge_color_counts[item] = edge_color_counts.get(item, 0) + 1
    payload = {
        "n": n,
        "m": m,
        "key_bits": k,
        "key_weight": inst["key_weight"],
        "color_counts": sorted(color_counts.items()),
        "edge_color_counts": sorted(
            [list(item) + [count] for item, count in edge_color_counts.items()]
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params):
    p = dict(params)
    decoys = int(p.get("decoys", 0))
    p["decoys"] = decoys + 8
    p["n"] = int(p["n"]) + 16
    return p


def _satisfied_count(inst, key):
    return sum(
        ((checksum & key).bit_count() & 1) == rhs
        for _triple, rhs, checksum in inst["constraints"]
    )


def _fixed_weight_from_scores(scores, weight):
    chosen = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:weight]
    return sum(1 << i for i in chosen)


def _attack_outlier_correlation(inst):
    scores = [0] * inst["key_bits"]
    nodes = 0
    for _triple, rhs, checksum in inst["constraints"]:
        sign = 1 if rhs else -1
        for bit in range(inst["key_bits"]):
            if (checksum >> bit) & 1:
                scores[bit] += sign
            nodes += 1
    key = _fixed_weight_from_scores(scores, inst["key_weight"])
    return _answer_from_key(key, inst["key_bits"]), nodes


def _attack_rhs_prefix(inst):
    raw = 0
    for bit, (_triple, rhs, _checksum) in enumerate(
        inst["constraints"][: inst["key_bits"]]
    ):
        raw |= rhs << bit
    positions = _answer_from_key(raw, inst["key_bits"])
    if len(positions) > inst["key_weight"]:
        positions = positions[: inst["key_weight"]]
    elif len(positions) < inst["key_weight"]:
        used = set(positions)
        positions += [
            i
            for i in range(1, inst["key_bits"] + 1)
            if i not in used
        ][: inst["key_weight"] - len(positions)]
    return sorted(positions), inst["key_bits"]


def _attack_raw_sparse_propagation(inst):
    known = {}
    nodes = 0
    for _triple, rhs, checksum in inst["constraints"]:
        nodes += 1
        if checksum and checksum & (checksum - 1) == 0:
            known[checksum.bit_length() - 1] = rhs
    scores = [2 if known.get(i) == 1 else (-2 if known.get(i) == 0 else 0)
              for i in range(inst["key_bits"])]
    key = _fixed_weight_from_scores(scores, inst["key_weight"])
    return _answer_from_key(key, inst["key_bits"]), nodes


def _attack_pair_swap_greedy(inst):
    answer, nodes = _attack_outlier_correlation(inst)
    key = _key_from_answer(answer)
    score = _satisfied_count(inst, key)
    for _ in range(4):
        selected = [i for i in range(inst["key_bits"]) if (key >> i) & 1]
        absent = [i for i in range(inst["key_bits"]) if not ((key >> i) & 1)]
        best_score = score
        best_key = key
        for remove in selected:
            for add in absent:
                candidate = key ^ (1 << remove) ^ (1 << add)
                candidate_score = _satisfied_count(inst, candidate)
                nodes += len(inst["constraints"])
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_key = candidate
        if best_key == key:
            break
        key, score = best_key, best_score
    return _answer_from_key(key, inst["key_bits"]), nodes


def _attack_random_restart(inst, rng, restarts=256):
    for attempt in range(restarts):
        answer = random_candidate(inst, rng)
        if verify(inst, answer)[0]:
            return answer, attempt + 1
    return random_candidate(inst, rng), restarts


def _gaussian_reference(inst):
    """Solve the advertised checksum system; return key and bit-operation count."""
    k = inst["key_bits"]
    rows = [checksum | (rhs << k) for _triple, rhs, checksum in inst["constraints"]]
    rank = 0
    pivots = []
    operations = 0
    for col in range(k):
        pivot = None
        for r in range(rank, len(rows)):
            operations += 1
            if (rows[r] >> col) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(len(rows)):
            operations += 1
            if r != rank and ((rows[r] >> col) & 1):
                rows[r] ^= rows[rank]
                operations += k + 1
        pivots.append(col)
        rank += 1
        if rank == k:
            break
    coeff_mask = (1 << k) - 1
    for row in rows:
        if (row & coeff_mask) == 0 and ((row >> k) & 1):
            return None, operations
    if rank < k:
        return None, operations
    key = 0
    for r, col in enumerate(pivots):
        key |= ((rows[r] >> k) & 1) << col
    return key, operations


def _relabel_instance(inst, rng):
    n = inst["n"]
    order = list(range(n))
    rng.shuffle(order)
    old_to_new = [0] * n
    masks = [0] * n
    for new, old in enumerate(order):
        old_to_new[old] = new
        masks[new] = inst["variable_masks"][old]
    constraints = []
    for triple, rhs, checksum in inst["constraints"]:
        mapped = [old_to_new[i] for i in triple]
        rng.shuffle(mapped)
        constraints.append([mapped, rhs, checksum])
    rng.shuffle(constraints)
    out = dict(inst)
    out["variable_masks"] = masks
    out["constraints"] = constraints
    return out


def _permute_bit_coordinates(inst, rng):
    """Rename decoder coordinates and carry the certificate through the rename."""
    k = inst["key_bits"]
    old_to_new = list(range(k))
    rng.shuffle(old_to_new)

    def rename_mask(mask):
        renamed = 0
        residue = mask
        while residue:
            low = residue & -residue
            old = low.bit_length() - 1
            renamed |= 1 << old_to_new[old]
            residue ^= low
        return renamed

    out = dict(inst)
    out["variable_masks"] = [rename_mask(mask) for mask in inst["variable_masks"]]
    out["constraints"] = [
        [list(triple), rhs, rename_mask(checksum)]
        for triple, rhs, checksum in inst["constraints"]
    ]
    out["answer"] = sorted(
        old_to_new[position - 1] + 1 for position in inst["answer"]
    )
    return out


def _corruptions(answer, key_bits):
    dropped = answer[:-1]
    swapped = list(reversed(answer))
    duplicated = list(answer)
    if len(duplicated) >= 2:
        duplicated[1] = duplicated[0]
    outside = list(answer)
    outside[-1] = key_bits + 1
    return {
        "drop_one": dropped,
        "swap_order": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": outside,
    }


def selftest():
    report = {}

    checked = 0
    json_roundtrips = 0
    g1_ok = True
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, _why = verify(inst, inst["answer"])
            g1_ok &= ok
            checked += 1
            json_roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": g1_ok and json_roundtrips == checked,
        "instances_checked": checked,
        "json_native_roundtrips": json_roundtrips,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    reasons = {}
    g2_ok = True
    for name, bad in _corruptions(ship["answer"], ship["key_bits"]).items():
        ok, why = verify(ship, bad)
        g2_ok &= not ok
        reasons[name] = why
    distinct_reasons = len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok and distinct_reasons,
        "reasons": reasons,
        "distinct_reasons": distinct_reasons,
    }

    body = ", ".join(map(str, ship["answer"]))
    parsed = parse_answer(
        "I used the parity decoder.\n```text\nFinal:\n"
        f"<answer>{body}</answer>\n```\n"
    )
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"],
        "parsed_elements": len(parsed) if isinstance(parsed, list) else None,
    }

    guess_rng = random.Random(0x14012436)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "candidate_space": search_space(ship),
        "prior": "uniform over fixed-weight, sorted keys required by the statement",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_names = (
        "outlier_bit_rhs_correlation",
        "greedy_fixed_weight_pair_swap",
        "random_restart_256",
        "raw_sparse_propagation",
        "rhs_prefix_ansatz",
    )
    attack_stats = {
        name: {"successes": 0, "attempts": 0, "nodes": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    attack_node_samples = {name: [] for name in attack_names}
    attack_time_samples = {name: [] for name in attack_names}
    ref_times = []
    ref_ops = []
    ref_successes = 0
    for trial_seed in range(800, 808):
        inst = make_instance(seed=trial_seed, **ship_params)
        rng = random.Random(trial_seed ^ 0xA55A)
        attacks = {
            "outlier_bit_rhs_correlation": lambda: _attack_outlier_correlation(inst),
            "greedy_fixed_weight_pair_swap": lambda: _attack_pair_swap_greedy(inst),
            "random_restart_256": lambda: _attack_random_restart(inst, rng, 256),
            "raw_sparse_propagation": lambda: _attack_raw_sparse_propagation(inst),
            "rhs_prefix_ansatz": lambda: _attack_rhs_prefix(inst),
        }
        for name, attack in attacks.items():
            started = time.perf_counter()
            candidate, nodes = attack()
            elapsed = time.perf_counter() - started
            success = verify(inst, candidate)[0]
            stat = attack_stats[name]
            stat["successes"] += int(success)
            stat["attempts"] += 1
            stat["nodes"] += nodes
            stat["wall_clock_sec"] += elapsed
            attack_node_samples[name].append(nodes)
            attack_time_samples[name].append(elapsed)

        started = time.perf_counter()
        ref_key, operations = _gaussian_reference(inst)
        ref_times.append(time.perf_counter() - started)
        ref_ops.append(operations)
        if ref_key is not None:
            ref_successes += int(
                verify(inst, _answer_from_key(ref_key, inst["key_bits"]))[0]
            )

    for name, stat in attack_stats.items():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
        stat["nodes_median_per_instance"] = int(
            statistics.median(attack_node_samples[name])
        )
        stat["wall_clock_sec_median_per_instance"] = round(
            statistics.median(attack_time_samples[name]), 8
        )
    all_failed = all(stat["successes"] == 0 for stat in attack_stats.values())
    reference = {
        "name": "GF(2) Gaussian elimination on checksum rows",
        "complexity": "O(m*k^2) bit operations",
        "wall_clock_sec_median": round(statistics.median(ref_times), 8),
        "operations_median": int(statistics.median(ref_ops)),
        "operations_range": [min(ref_ops), max(ref_ops)],
        "solves": f"{ref_successes}/8, as expected",
    }
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_hits / guess_total < 1e-6 and ref_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_valid_fraction": guess_hits / guess_total,
        "exact_demo_valid_answer_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
        "reference_wall_clock_sec_median": reference["wall_clock_sec_median"],
        "reference_operation_count_median": reference["operations_median"],
        "strongest_failing_attack_nodes_median": attack_stats[
            "greedy_fixed_weight_pair_swap"
        ]["nodes_median_per_instance"],
        "strongest_failing_attack_wall_clock_sec_median": attack_stats[
            "greedy_fixed_weight_pair_swap"
        ]["wall_clock_sec_median_per_instance"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attack_stats,
        "reference_algorithm": reference,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled_params["decoys"] = ship_params["decoys"] + 8
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    harder = escalate(ship_params)
    escalated = make_instance(seed=271829, **harder) if isinstance(harder, dict) else None
    escalated_ok = bool(escalated and verify(escalated, escalated["answer"])[0])
    same_answer_length = bool(
        escalated and len(escalated["answer"]) == len(ship["answer"])
    )
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok and same_answer_length,
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "doubled_vertices": doubled["graph_vertex_count"],
        "doubled_planted_verifies": doubled_ok,
        "escalated_params": harder,
        "escalated_planted_verifies": escalated_ok,
        "fixed_answer_elements_on_escalation": same_answer_length,
    }

    invariant_checks = 0
    preservation_checks = 0
    keys = []
    g8_ok = True
    for seed in range(1200, 1220):
        inst = make_instance(seed=seed, **ship_params)
        key = canonical_key(inst)
        keys.append(key)
        renamed = _relabel_instance(inst, random.Random(seed * 17 + 1))
        bit_renamed = _permute_bit_coordinates(
            inst, random.Random(seed * 17 + 2)
        )
        composed = _permute_bit_coordinates(
            renamed, random.Random(seed * 17 + 3)
        )
        for transformed in (renamed, bit_renamed, composed):
            invariant_checks += 1
            g8_ok &= canonical_key(transformed) == key
            preservation_checks += 1
            g8_ok &= verify(transformed, transformed["answer"])[0]
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": g8_ok and distinct == 20,
        "invariance_checks": invariant_checks,
        "certificate_preservation_checks": preservation_checks,
        "distinct_unrelated_instances": distinct,
        "unrelated_instances_tested": 20,
        "transformations": [
            "variable renumbering",
            "equation reordering",
            "within-equation variable reordering",
            "decoder-bit renumbering with the answer carried through",
            "composition of variable/equation and decoder-bit renumbering",
        ],
    }

    answer_char_samples = [
        len(
            json.dumps(
                make_instance(seed=seed, **ship_params)["answer"],
                separators=(",", ":"),
            )
        )
        for seed in range(64)
    ]
    observed_answer_chars = max(answer_char_samples)
    longest_position_lengths = sorted(
        (len(str(position)) for position in range(1, ship["key_bits"] + 1)),
        reverse=True,
    )[: ship["key_weight"]]
    # Compact JSON has two brackets, weight-1 commas, and the decimal positions.
    answer_chars = 2 + ship["key_weight"] - 1 + sum(longest_position_lengths)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(ship["answer"])
    # 96 rotations of Q, 96 XORs with D to locate their rows, 96 RHS XORs,
    # then two rotations and two XORs to apply the three-tap transpose.
    intended_operations = 3 * ship["key_bits"] + 4
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    hinted_hardened = G9_RESULTS.get("hinted_verdict") == "hardened"
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in arms)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and evidence_complete and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS.get("hinted_verdict"),
        "answer_chars": answer_chars,
        "answer_chars_observed_max": observed_answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "answer_size_instances_measured": len(answer_char_samples),
        "intended_route_operations": intended_operations,
        "operation_model": "exact fixed-width rotate or XOR word operations",
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = ship_params
    report["all_passed"] = all(
        value.get("pass", False)
        for name, value in report.items()
        if name.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
