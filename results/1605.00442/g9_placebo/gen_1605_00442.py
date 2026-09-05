"""Verified problem generator for arXiv:1605.00442.

The witness is a frozen independent set in the split graph used by Theorem 5
of Bonamy--Bousquet.  A regular base graph with a planted dominating set is
sampled first; Theorem 5 carries that set to a frozen token placement.  Public
GF(2) annotations give an honest polynomial-time decoder, while a hidden
common-offset basis supplies the intended no-tool shortcut.
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
from collections import Counter


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Relative to the distinguished mask O, the informative decoder masks "
    "form the complete weight-one affine basis."
)
PLACEBO_HINT: str = (
    "Keep the hexadecimal bit order and the split-graph vertex labels "
    "consistent when checking the placement."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "a split graph given by its clique, independent side, and cross-neighborhoods",
        "a fixed-size independent token placement",
        "GF(2) decoder annotations attached to eligible independent-side vertices",
    ],
    "verification_operations": [
        "set cardinality and membership",
        "exact split-graph independence checks",
        "exact selected-neighbor counts for every possible token slide",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Theorem 5: a dominating set D is carried to the frozen "
        "placement {w_i : v_i in D} union {w_special} in a split graph"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Cancel the common GF(2) mask to expose coordinate equations; without "
        "that affine change of variables one must eliminate a dense binary system."
    ),
    "hardness_basis": (
        "Track B: exact GF(2) Gaussian elimination on the public decoder followed "
        "by parity classification runs in O(r*b^2+n*b) bit operations and measured "
        "790,570 counted bit operations / 0.001739 seconds at the shipping preset; "
        "the affine-basis route uses 251 packed XOR/parity operations, whereas "
        "Section 3's interval-graph reachability algorithm is polynomial and "
        "therefore cannot support Track A."
    ),
    "max_answer_tokens": 15,
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
    "medium": {
        "n": 144,
        "k": 12,
        "degree": 14,
        "key_bits": 104,
        "decoder_decoys": 96,
    },
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A normalized list [special,d1,...,dk], where special is the displayed "
        "special vertex and d1<...<dk are distinct displayed eligible vertices; "
        "the represented token placement must be frozen."
    ),
    "bounds": {
        "special_vertices": 1,
        "eligible_vertices": "instance n",
        "chosen_eligible_vertices": "instance k",
        "index_base": 0,
        "repetitions": 0,
        "max_atomic_elements": 13,
    },
}

NOTES: str = (
    "Section 1 fixes Token Sliding: consecutive independent sets differ by one "
    "token moved along one graph edge. Section 2 defines blocking/frozen sets and "
    "Theorem 5 gives the exact split-graph construction used here: a dominating "
    "set D together with w_special has no private neighbor and hence is frozen. "
    "Theorem 1/5 and Corollary 6 give co-NP-hardness and co-W[2]-hardness for "
    "connectivity of TS_k on split graphs, but those are worst-case statements, "
    "not claims about this generated distribution. Section 3, especially "
    "Procedures 1 and 2 and Theorem 3, gives a polynomial algorithm for pairwise "
    "reachability on interval graphs; that kills the prior planted-path idea as a "
    "Track-A family. The present family is therefore honestly Track B. The base "
    "graph is exactly regular, so degree and aggregate-overlap outliers vanish; "
    "random factorization supplies decoys, greedy coverage and random restarts are "
    "tested, and the obvious decoder-row-order ansatz is tested. Exact Gaussian "
    "elimination is reported separately as the successful reference algorithm."
)

# Filled only from isolated scripts/harden.py runs.  Pending values deliberately
# make G9 fail instead of manufacturing oracle evidence.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _mask(bits):
    return (1 << bits) - 1


def _public_offset(bits):
    """A conspicuous, explicitly displayed dense mask."""
    pattern = int("d6a39c5e71b428f09d3c6a57", 16)
    width = 96
    value = 0
    shift = 0
    while shift < bits:
        value |= pattern << shift
        shift += width
    return value & _mask(bits)


def _conditioned_mask(bits, key, desired, used, rng):
    for _ in range(100000):
        value = rng.getrandbits(bits)
        if value not in used and ((value & key).bit_count() & 1) == desired:
            used.add(value)
            return value
    raise RuntimeError("could not sample a distinct conditioned annotation")


def _decoder_rows(bits, decoys, key, rng):
    offset = _public_offset(bits)
    masks = [offset] + [offset ^ (1 << i) for i in range(bits)]
    used = set(masks)
    while len(masks) < bits + 1 + decoys:
        value = rng.getrandbits(bits)
        if value not in used:
            used.add(value)
            masks.append(value)
    rows = [[value, (value & key).bit_count() & 1] for value in masks]
    rng.shuffle(rows)
    return rows


def _compact_decode(rows, bits, offset):
    table = {int(mask): int(rhs) for mask, rhs in rows}
    if len(table) != len(rows) or offset not in table:
        return None
    base_rhs = table[offset]
    key = 0
    for i in range(bits):
        row = offset ^ (1 << i)
        if row not in table:
            return None
        if table[row] ^ base_rhs:
            key |= 1 << i
    return key


def _gaussian_decode(rows, bits):
    """Return (unique solution or None, counted bit operations)."""
    work = [[int(mask), int(rhs)] for mask, rhs in rows]
    pivots = []
    rank = 0
    operations = 0
    for column in range(bits):
        pivot = None
        for row in range(rank, len(work)):
            operations += 1
            if (work[row][0] >> column) & 1:
                pivot = row
                break
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for row in range(len(work)):
            if row == rank:
                continue
            operations += 1
            if (work[row][0] >> column) & 1:
                work[row][0] ^= work[rank][0]
                work[row][1] ^= work[rank][1]
                operations += bits + 1
        pivots.append((column, rank))
        rank += 1
        if rank == bits:
            break
    if rank != bits:
        return None, operations
    key = 0
    for column, row in pivots:
        operations += 1
        if work[row][1]:
            key |= 1 << column
    for mask, rhs in rows:
        operations += bits
        if ((int(mask) & key).bit_count() & 1) != int(rhs):
            return None, operations
    return key, operations


def _perfect_matching_avoiding(vertices, forbidden, rng):
    vertices = list(vertices)
    if len(vertices) % 2:
        raise ValueError("a perfect matching needs an even vertex count")
    for _ in range(2000):
        available = list(vertices)
        rng.shuffle(available)
        matching = []
        good = True
        while available:
            u = available.pop()
            choices = [i for i, v in enumerate(available)
                       if tuple(sorted((u, v))) not in forbidden]
            if not choices:
                good = False
                break
            pos = rng.choice(choices)
            v = available.pop(pos)
            edge = tuple(sorted((u, v)))
            matching.append(edge)
        if good:
            return matching
    raise RuntimeError("could not sample a new disjoint perfect matching")


def _random_regular_edges(vertices, degree, rng):
    """A simple regular graph as a union of random disjoint 1-factors."""
    vertices = list(vertices)
    if degree < 0 or degree >= len(vertices):
        raise ValueError("invalid regular degree")
    if len(vertices) % 2:
        raise ValueError("this construction requires an even vertex count")
    edges = set()
    for _ in range(degree):
        matching = _perfect_matching_avoiding(vertices, edges, rng)
        edges.update(matching)
    return edges


def _regular_dominating_graph(n, k, degree, rng):
    """Return a degree-regular graph and a planted size-k dominating set."""
    if n % k:
        raise ValueError("n must be divisible by k")
    q = (n - k) // k
    internal_d = degree - q
    internal_r = degree - 1
    if k % 2 or (n - k) % 2:
        raise ValueError("both planted and non-planted parts must have even size")
    if not (0 <= internal_d < k and 0 <= internal_r < n - k):
        raise ValueError("degree is incompatible with the regular construction")

    order = list(range(n))
    rng.shuffle(order)
    planted = set(order[:k])
    rest = order[k:]

    edges = _random_regular_edges(sorted(planted), internal_d, rng)
    edges |= _random_regular_edges(rest, internal_r, rng)

    shuffled_rest = list(rest)
    shuffled_planted = sorted(planted)
    rng.shuffle(shuffled_rest)
    rng.shuffle(shuffled_planted)
    for pos, vertex in enumerate(shuffled_rest):
        owner = shuffled_planted[pos // q]
        edges.add(tuple(sorted((owner, vertex))))

    degrees = [0] * n
    for u, v in edges:
        degrees[u] += 1
        degrees[v] += 1
    if any(value != degree for value in degrees):
        raise AssertionError("regular graph construction failed")
    for vertex in range(n):
        if vertex not in planted and not any(
            tuple(sorted((vertex, d))) in edges for d in planted
        ):
            raise AssertionError("planted set does not dominate")
    return edges, planted


def make_instance(n, seed=0, k=12, degree=12, key_bits=96,
                  decoder_decoys=48, **params) -> dict:
    """Inverse-generate a dominating set and carry it through Theorem 5."""
    del params
    for name, value in (
        ("n", n),
        ("k", k),
        ("degree", degree),
        ("key_bits", key_bits),
        ("decoder_decoys", decoder_decoys),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 12 or k < 2 or k >= n:
        raise ValueError("require n>=12 and 2<=k<n")
    if key_bits < 8:
        raise ValueError("key_bits must be at least 8")
    if decoder_decoys < 0:
        raise ValueError("decoder_decoys must be nonnegative")

    rng = random.Random(seed)
    base_edges, planted = _regular_dominating_graph(n, k, degree, rng)

    clique_size = n + k + 1
    side_size = n + k + 2
    total = clique_size + side_size
    labels = list(range(total))
    rng.shuffle(labels)
    clique_label = {i: labels[i] for i in range(clique_size)}
    side_label = {i: labels[clique_size + i] for i in range(side_size)}

    base_adj = [set([i]) for i in range(n)]
    for u, v in base_edges:
        base_adj[u].add(v)
        base_adj[v].add(u)

    neighborhoods = []
    for i in range(n):
        neighborhoods.append(
            [clique_label[i], [side_label[j] for j in sorted(base_adj[i])]]
        )
    for t in range(k + 1):
        neighborhoods.append(
            [clique_label[n + t], [side_label[n + t]]]
        )
    special = side_label[n + k + 1]
    for row in neighborhoods[:n]:
        row[1].append(special)
    for row in neighborhoods:
        rng.shuffle(row[1])
    rng.shuffle(neighborhoods)

    key = rng.getrandbits(key_bits)
    if key == 0:
        key = 1
    decoder_rows = _decoder_rows(key_bits, decoder_decoys, key, rng)
    used_masks = {int(mask) for mask, _ in decoder_rows}
    annotations = []
    for i in range(n):
        desired = 0 if i in planted else 1
        ann = _conditioned_mask(key_bits, key, desired, used_masks, rng)
        annotations.append([side_label[i], ann])
    rng.shuffle(annotations)

    clique = list(clique_label.values())
    independent_side = list(side_label.values())
    candidates = [side_label[i] for i in range(n)]
    extras = [side_label[n + i] for i in range(k + 1)]
    rng.shuffle(clique)
    rng.shuffle(independent_side)
    rng.shuffle(candidates)
    rng.shuffle(extras)
    answer = [special] + sorted(side_label[i] for i in planted)

    inst = {
        "n": n,
        "k": k,
        "degree": degree,
        "token_count": k + 1,
        "vertex_count": total,
        "clique": clique,
        "independent_side": independent_side,
        "eligible_vertices": candidates,
        "extra_vertices": extras,
        "special_vertex": special,
        "cross_neighborhoods": neighborhoods,
        "key_bits": key_bits,
        "public_offset": _public_offset(key_bits),
        "decoder_rows": decoder_rows,
        "annotations": annotations,
        "answer": answer,
    }
    ok, why = verify(inst, answer)
    if not ok:
        raise AssertionError(f"constructed witness failed: {why}")
    return inst


def _hex(value, bits):
    return f"{int(value):0{(bits + 3) // 4}x}"


def render(inst) -> str:
    bits = inst["key_bits"]
    lines = [
        "FROZEN TOKEN PLACEMENT IN A SPLIT GRAPH",
        "",
        "A split graph has a clique K (every two vertices of K are adjacent) and",
        "an independent side S (no two vertices of S are adjacent). Its remaining",
        "edges run between K and S and are listed below.",
        "",
        "A token placement is an independent set of occupied vertices. A legal token",
        "slide replaces one occupied vertex x by an unoccupied neighbor y, provided",
        "the occupied vertices after the replacement are still independent. A",
        "placement is frozen when no legal token slide exists.",
        "",
        f"There are {inst['vertex_count']} vertices, numbered 0 through "
        f"{inst['vertex_count'] - 1}.",
        "K = " + " ".join(map(str, sorted(inst["clique"]))),
        "S = " + " ".join(map(str, sorted(inst["independent_side"]))),
        "",
        "For each vertex of K, the following row gives all of its neighbors in S.",
        "There are no cross-edges other than those listed:",
    ]
    for vertex, neighbors in sorted(inst["cross_neighborhoods"]):
        lines.append(f"  {vertex}: " + " ".join(map(str, sorted(neighbors))))

    lines.extend(
        [
            "",
            "Your placement must contain the following displayed special vertex:",
            f"  special = {inst['special_vertex']}",
            f"It must also contain exactly {inst['k']} vertices from this eligible set:",
            "  eligible = " + " ".join(map(str, sorted(inst["eligible_vertices"]))),
            "The other vertices of S are not eligible for the requested certificate.",
            "",
            "Auxiliary exact decoder data are supplied to help find such a placement.",
            f"Every mask is a {bits}-bit hexadecimal integer; bit 0 is the least",
            "significant bit. For an unknown promised unique word X, each row",
            "'mask | rhs' means parity(mask AND X)=rhs over GF(2), where parity is",
            "the number of 1-bits modulo 2. XOR is addition over GF(2).",
            f"The distinguished public mask is O = {_hex(inst['public_offset'], bits)}.",
            "Decoder rows:",
        ]
    )
    for mask, rhs in inst["decoder_rows"]:
        lines.append(f"  {_hex(mask, bits)} | {rhs}")
    lines.extend(
        [
            "",
            "Each eligible vertex v has an annotation a(v). The promised frozen",
            "placement consists of special together with exactly those eligible",
            "vertices for which parity(a(v) AND X)=0. The checker does not require",
            "this decoder route: it accepts every requested-format frozen placement.",
            "Annotations (vertex : mask):",
        ]
    )
    for vertex, mask in sorted(inst["annotations"]):
        lines.append(f"  {vertex}: {_hex(mask, bits)}")
    lines.extend(
        [
            "",
            f"Output exactly {inst['token_count']} decimal vertex identifiers. The",
            "special vertex must be first. The remaining eligible identifiers must",
            "be distinct and in strictly increasing order. Order otherwise has no",
            "meaning; repetitions are forbidden; all displayed sets and bounds are",
            "inclusive; vertex numbering is 0-based.",
            "",
            "Give your final answer inside <answer></answer> tags, as comma-separated",
            "decimal integers.",
            "Example format: <answer>17, 3, 29, 41</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body:
        return []
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(part.strip()) for part in body.split(",")]
    except (TypeError, ValueError):
        return None


def _cross_map(inst):
    return {
        int(vertex): set(map(int, neighbors))
        for vertex, neighbors in inst["cross_neighborhoods"]
    }


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a list of vertex identifiers"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every answer entry must be an integer vertex identifier"
    if len(answer) != inst["token_count"]:
        return False, f"answer must contain exactly {inst['token_count']} vertices"
    if len(set(answer)) != len(answer):
        return False, "answer repeats a vertex"
    known = set(inst["clique"]) | set(inst["independent_side"])
    unknown = [value for value in answer if value not in known]
    if unknown:
        return False, f"answer contains unknown vertex {unknown[0]}"
    if answer[0] != inst["special_vertex"]:
        return False, "the displayed special vertex must be first"
    eligible = set(inst["eligible_vertices"])
    if any(value not in eligible for value in answer[1:]):
        return False, "every non-special entry must be an eligible vertex"
    if answer[1:] != sorted(answer[1:]):
        return False, "eligible vertices must be in strictly increasing order"

    selected = set(answer)
    for clique_vertex, neighbors in inst["cross_neighborhoods"]:
        occupied_neighbors = [vertex for vertex in neighbors if vertex in selected]
        if len(occupied_neighbors) == 1:
            token = occupied_neighbors[0]
            return (
                False,
                f"placement is not frozen: token {token} can slide to {clique_vertex}",
            )
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    chosen = sorted(rng.sample(list(inst["eligible_vertices"]), inst["k"]))
    return [inst["special_vertex"]] + chosen


def search_space(inst):
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    special = inst["special_vertex"]
    for chosen in itertools.combinations(sorted(inst["eligible_vertices"]), inst["k"]):
        if verify(inst, [special] + list(chosen))[0]:
            count += 1
    return count


def _coverage_data(inst):
    candidates = sorted(inst["eligible_vertices"])
    candidate_index = {vertex: i for i, vertex in enumerate(candidates)}
    special = inst["special_vertex"]
    base_rows = []
    for clique_vertex, neighbors in inst["cross_neighborhoods"]:
        nset = set(neighbors)
        if special in nset:
            base_rows.append((clique_vertex, nset & set(candidates)))
    base_rows.sort()
    row_index = {vertex: i for i, (vertex, _) in enumerate(base_rows)}
    covers = [0] * len(candidates)
    for row_vertex, neighbors in base_rows:
        bit = 1 << row_index[row_vertex]
        for candidate in neighbors:
            covers[candidate_index[candidate]] |= bit
    return candidates, covers, (1 << len(base_rows)) - 1


def _answer_from_key(inst, key):
    selected = sorted(
        vertex
        for vertex, mask in inst["annotations"]
        if ((int(mask) & int(key)).bit_count() & 1) == 0
    )
    if len(selected) != inst["k"]:
        return None
    return [inst["special_vertex"]] + selected


def _attack_outlier(inst):
    candidates, covers, _ = _coverage_data(inst)
    # Degree and aggregate pairwise overlap are the strongest natural per-item
    # statistics here.  The regular construction makes both exactly tied.
    scored = []
    for i, vertex in enumerate(candidates):
        overlap = sum((covers[i] & other).bit_count() for other in covers)
        scored.append(((covers[i].bit_count(), overlap, vertex), vertex))
    low = sorted(scored)[: inst["k"]]
    high = sorted(scored, reverse=True)[: inst["k"]]
    answers = [
        [inst["special_vertex"]] + sorted(vertex for _, vertex in low),
        [inst["special_vertex"]] + sorted(vertex for _, vertex in high),
    ]
    return next((answer for answer in answers if verify(inst, answer)[0]), answers[0])


def _attack_greedy(inst):
    candidates, covers, universe = _coverage_data(inst)
    chosen = []
    covered = 0
    remaining = set(range(len(candidates)))
    while len(chosen) < inst["k"] and remaining:
        best = max(
            remaining,
            key=lambda i: (((covers[i] & ~covered) & universe).bit_count(), -candidates[i]),
        )
        chosen.append(best)
        remaining.remove(best)
        covered |= covers[best]
    answer = [inst["special_vertex"]] + sorted(candidates[i] for i in chosen)
    return answer


def _attack_random_restart(inst, rng, restarts=512):
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, restarts
    return last, restarts


def _attack_rhs_order(inst):
    bits = inst["key_bits"]
    rows = inst["decoder_rows"][:bits]
    key = 0
    for i, (_, rhs) in enumerate(rows):
        if rhs:
            key |= 1 << i
    answer = _answer_from_key(inst, key)
    if answer is not None:
        return answer
    annotations = sorted(inst["annotations"])
    ranked = sorted(
        annotations,
        key=lambda item: (((int(item[1]) & key).bit_count() & 1), item[0]),
    )[: inst["k"]]
    return [inst["special_vertex"]] + sorted(vertex for vertex, _ in ranked)


def _attack_bounded_set_cover(inst, node_limit=200000):
    candidates, covers, universe = _coverage_data(inst)
    by_row = [[] for _ in range(inst["n"])]
    for candidate, mask in enumerate(covers):
        for row in range(inst["n"]):
            if (mask >> row) & 1:
                by_row[row].append(candidate)
    nodes = 0
    found = None
    seen = set()

    def visit(covered, chosen):
        nonlocal nodes, found
        if found is not None or nodes >= node_limit:
            return
        nodes += 1
        if covered == universe:
            found = tuple(chosen)
            return
        if len(chosen) >= inst["k"]:
            return
        remaining = universe & ~covered
        max_gain = max(((mask & remaining).bit_count() for mask in covers), default=0)
        if max_gain == 0 or len(chosen) + (remaining.bit_count() + max_gain - 1) // max_gain > inst["k"]:
            return
        state = (covered, len(chosen))
        if state in seen:
            return
        seen.add(state)
        rows = [row for row in range(inst["n"]) if (remaining >> row) & 1]
        row = min(rows, key=lambda r: len([i for i in by_row[r] if i not in chosen]))
        options = [i for i in by_row[row] if i not in chosen]
        options.sort(key=lambda i: ((covers[i] & remaining).bit_count(), -candidates[i]), reverse=True)
        for candidate in options:
            visit(covered | covers[candidate], chosen + (candidate,))
            if found is not None or nodes >= node_limit:
                return

    visit(0, tuple())
    if found is None:
        return None, nodes
    chosen = list(found)
    for candidate in range(len(candidates)):
        if len(chosen) >= inst["k"]:
            break
        if candidate not in chosen:
            chosen.append(candidate)
    answer = [inst["special_vertex"]] + sorted(candidates[i] for i in chosen)
    return answer, nodes


def _wl_signature(inst):
    clique = set(inst["clique"])
    side = set(inst["independent_side"])
    candidates = set(inst["eligible_vertices"])
    extras = set(inst["extra_vertices"])
    special = inst["special_vertex"]
    ann = {vertex: int(mask) for vertex, mask in inst["annotations"]}
    cross = _cross_map(inst)
    reverse = {vertex: set() for vertex in side}
    for cvertex, neighbors in cross.items():
        for svertex in neighbors:
            reverse[svertex].add(cvertex)

    colors = {}
    for vertex in clique:
        colors[vertex] = "KB" if special in cross[vertex] else "KE"
    for vertex in side:
        if vertex == special:
            colors[vertex] = "SS"
        elif vertex in candidates:
            colors[vertex] = f"SC:{ann[vertex].bit_count()}"
        elif vertex in extras:
            colors[vertex] = "SE"
        else:
            colors[vertex] = "SO"
    for _ in range(5):
        descriptions = {}
        for vertex in clique | side:
            neighbors = cross[vertex] if vertex in clique else reverse[vertex]
            descriptions[vertex] = (colors[vertex], tuple(sorted(colors[x] for x in neighbors)))
        palette = {value: str(i) for i, value in enumerate(sorted(set(descriptions.values())))}
        colors = {vertex: palette[value] for vertex, value in descriptions.items()}
    return sorted(Counter(colors.values()).items())


def canonical_key(inst):
    offset = int(inst["public_offset"])
    candidates, covers, _ = _coverage_data(inst)
    annotation = {vertex: int(mask) for vertex, mask in inst["annotations"]}
    payload = {
        "shape": [inst["n"], inst["k"], inst["degree"], inst["key_bits"]],
        "wl": _wl_signature(inst),
        "coverage": sorted(
            (mask.bit_count(), sum((mask & other).bit_count() for other in covers))
            for mask in covers
        ),
        "annotations": sorted(
            (
                covers[i].bit_count(),
                annotation[vertex].bit_count(),
                (annotation[vertex] ^ offset).bit_count(),
            )
            for i, vertex in enumerate(candidates)
        ),
        "decoder": sorted(
            ((int(mask) ^ offset).bit_count(), int(mask).bit_count(), int(rhs))
            for mask, rhs in inst["decoder_rows"]
        ),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _permute_mask(value, permutation):
    result = 0
    for old, new in enumerate(permutation):
        if (int(value) >> old) & 1:
            result |= 1 << new
    return result


def _relabeled(inst, rng):
    labels = list(range(inst["vertex_count"]))
    shuffled = list(labels)
    rng.shuffle(shuffled)
    rename = dict(zip(labels, shuffled))
    bit_permutation = list(range(inst["key_bits"]))
    rng.shuffle(bit_permutation)

    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {
            "clique",
            "independent_side",
            "eligible_vertices",
            "extra_vertices",
            "special_vertex",
            "cross_neighborhoods",
            "public_offset",
            "decoder_rows",
            "annotations",
            "answer",
        }
    }
    transformed["clique"] = [rename[x] for x in inst["clique"]]
    transformed["independent_side"] = [rename[x] for x in inst["independent_side"]]
    transformed["eligible_vertices"] = [rename[x] for x in inst["eligible_vertices"]]
    transformed["extra_vertices"] = [rename[x] for x in inst["extra_vertices"]]
    transformed["special_vertex"] = rename[inst["special_vertex"]]
    transformed["cross_neighborhoods"] = [
        [rename[vertex], [rename[x] for x in neighbors]]
        for vertex, neighbors in inst["cross_neighborhoods"]
    ]
    transformed["public_offset"] = _permute_mask(inst["public_offset"], bit_permutation)
    transformed["decoder_rows"] = [
        [_permute_mask(mask, bit_permutation), rhs]
        for mask, rhs in inst["decoder_rows"]
    ]
    transformed["annotations"] = [
        [rename[vertex], _permute_mask(mask, bit_permutation)]
        for vertex, mask in inst["annotations"]
    ]
    transformed["answer"] = [transformed["special_vertex"]] + sorted(
        rename[x] for x in inst["answer"][1:]
    )
    for key in (
        "clique",
        "independent_side",
        "eligible_vertices",
        "extra_vertices",
        "cross_neighborhoods",
        "decoder_rows",
        "annotations",
    ):
        rng.shuffle(transformed[key])
    for _, neighbors in transformed["cross_neighborhoods"]:
        rng.shuffle(neighbors)
    return transformed


def escalate(params):
    harder = dict(params)
    decoys = int(harder.get("decoder_decoys", 0))
    if decoys < 1536:
        harder["decoder_decoys"] = max(64, decoys * 2)
        return harder
    n = int(harder["n"])
    k = int(harder["k"])
    if n < 180:
        harder["n"] = n + 24
        q = (harder["n"] - k) // k
        harder["degree"] = q + 3
        return harder
    return None


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}
    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 8675309):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = shipping["answer"]
    corruptions = {
        "empty": [],
        "drop": answer[:-1],
        "duplicate": answer[:-1] + [answer[1]],
        "out_of_range": answer[:-1] + [shipping["vertex_count"] + 7],
        "remove_special": [shipping["extra_vertices"][0]] + answer[1:],
    }
    replacement = None
    planted = set(answer[1:])
    for old in answer[1:]:
        for new in shipping["eligible_vertices"]:
            if new in planted:
                continue
            candidate = [answer[0]] + sorted((planted - {old}) | {new})
            if not verify(shipping, candidate)[0]:
                replacement = candidate
                break
        if replacement is not None:
            break
    corruptions["swap_one"] = replacement if replacement is not None else answer[:-1]
    reasons = {name: verify(shipping, value)[1] for name, value in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(not verify(shipping, value)[0] for value in corruptions.values())
        and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
    }

    body = ", ".join(map(str, answer))
    realistic = (
        "I checked each possible slide.\n```text\n<answer>\n"
        + body
        + "\n</answer>\n```\nThe placement is frozen."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
    }

    sample_rng = random.Random(314159265)
    density_total = 200000
    density_hits = 0
    density_t0 = time.perf_counter()
    density_candidates, density_covers, density_universe = _coverage_data(shipping)
    density_index = {vertex: i for i, vertex in enumerate(density_candidates)}
    for _ in range(density_total):
        candidate = random_candidate(shipping, sample_rng)
        covered = 0
        for vertex in candidate[1:]:
            covered |= density_covers[density_index[vertex]]
        if covered == density_universe:
            density_hits += 1
    density_seconds = time.perf_counter() - density_t0
    report["G4_guess_resistance"] = {
        "pass": density_hits / density_total < 1e-6,
        "hits": density_hits,
        "total": density_total,
        "estimated_probability": density_hits / density_total,
        "candidate_space": search_space(shipping),
        "structure_aware": True,
    }

    attack_names = (
        "regular_degree_overlap_outlier",
        "greedy_maximum_coverage",
        "random_restart_512",
        "decoder_rhs_order_ansatz",
        "bounded_set_cover_dpll_200000",
    )
    attack_successes = {name: 0 for name in attack_names}
    dpll_nodes = []
    dpll_times = []
    reference_operations = []
    reference_times = []
    reference_successes = 0
    for seed in range(8001, 8009):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "regular_degree_overlap_outlier": _attack_outlier(inst),
            "greedy_maximum_coverage": _attack_greedy(inst),
            "decoder_rhs_order_ansatz": _attack_rhs_order(inst),
        }
        random_answer, _ = _attack_random_restart(inst, random.Random(seed ^ 0xBAD5EED))
        candidates["random_restart_512"] = random_answer
        t0 = time.perf_counter()
        dpll_answer, nodes = _attack_bounded_set_cover(inst)
        dpll_times.append(time.perf_counter() - t0)
        dpll_nodes.append(nodes)
        candidates["bounded_set_cover_dpll_200000"] = dpll_answer
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_successes[name] += 1

        t0 = time.perf_counter()
        key, operations = _gaussian_decode(inst["decoder_rows"], inst["key_bits"])
        reference_times.append(time.perf_counter() - t0)
        reference_operations.append(operations)
        decoded = _answer_from_key(inst, key) if key is not None else None
        if decoded is not None and verify(inst, decoded)[0]:
            reference_successes += 1

    attacks = {
        name: {"successes": attack_successes[name], "attempts": 8}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attack_successes.values())
        and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact GF(2) Gaussian elimination plus parity classification",
            "complexity": "O(r*b^2+n*b) bit operations",
            "operations_median": int(statistics.median(reference_operations)),
            "wall_clock_sec_median": round(statistics.median(reference_times), 6),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and density_hits / density_total < 1e-6,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": density_total,
        "shipping_density_estimate": density_hits / density_total,
        "sampling_wall_seconds": round(density_seconds, 6),
        "demo_exact_valid_answer_count": demo_count,
        "baseline_nodes_median": int(statistics.median(dpll_nodes)),
        "baseline_wall_seconds_median": round(statistics.median(dpll_times), 6),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    q = (doubled_params["n"] - doubled_params["k"]) // doubled_params["k"]
    doubled_params["degree"] = q + 3
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"],
        "shipping_base_vertices": shipping["n"],
        "doubled_base_vertices": doubled["n"],
        "doubled_verify_reason": doubled_why,
    }

    invariant = 0
    carried = 0
    distinct = set()
    for seed in range(20):
        inst = make_instance(seed=90000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        transformed = _relabeled(inst, random.Random(70000 + seed))
        if canonical_key(inst) == canonical_key(transformed):
            invariant += 1
        if verify(transformed, transformed["answer"])[0]:
            carried += 1
        distinct.add(canonical_key(inst))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(distinct) == 20,
        "invariance_checks_passed": invariant,
        "carried_witness_checks_passed": carried,
        "distinct_unrelated_keys": len(distinct),
        "unrelated_instances": 20,
        "transformations": [
            "arbitrary relabelling within the displayed split-graph roles",
            "cross-neighborhood, vertex-list, decoder-row, and annotation reordering",
            "arbitrary permutation of GF(2) bit coordinates",
            "composition of all listed transformations",
        ],
    }

    answer_blob = json.dumps(shipping["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_ops = shipping["key_bits"] + shipping["n"] + 3
    arms = G9_RESULTS["arms"]
    hinted_attempts = arms["hinted"]["attempts"]
    hinted_hardened = (
        G9_RESULTS["hinted_verdict"] == "hardened"
        and hinted_attempts >= 3
        and arms["hinted"]["solved"] == 0
    )
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    report["track"] = TRACK
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
