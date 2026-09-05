#!/usr/bin/env python3
"""Verified generalized-SET witnesses from arXiv:1309.6504.

The generator plants a multicolored clique and applies, verbatim in compact
form, the reduction in Section 2 of Lampis--Mitsou.  The planted clique is
chosen before any random background edge is drawn, so its corresponding SET
certificate is known by construction rather than recovered by search.
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


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "compactly encoded generalized SET cards",
        "attribute-value vectors",
        "paper-licensed k-partite source graph",
    ],
    "verification_operations": [
        "exact bit lookup in each color-pair adjacency matrix",
        "exact complementary-swap check for the selected card vectors",
        "integer range and shape checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Theorem 1 proof and its SET corollary: Multicolored "
        "Clique is encoded by vertex-cards and edge-cards whose exceptional "
        "attribute values swap in complementary pairs"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize that complementary value swaps force one vertex-card per "
        "color and its matching edge-card for every color pair; without that "
        "recognition the solver searches an enormous generalized-SET space."
    ),
    "hardness_basis": (
        "Track A: the Section 2 corollary to Theorem 1 proves W[1]-hardness "
        "parameterized by the number q of values (and hence SET size), with "
        "unbounded attributes; the shipping preset uses source k=24, q=300, "
        "30,912 attributes, and 56 vertices per color at the planted-clique "
        "threshold, while the measured 10,000,000-node exact clique attack fails "
        "on all eight shipping seeds."
    ),
    "max_answer_tokens": 19,
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
    "demo": {"n": 3, "part_size": 4, "density_per_10000": 3500},
    "easy": {"n": 24, "part_size": 56, "density_per_10000": 7100},
    "medium": {"n": 24, "part_size": 72, "density_per_10000": 6900},
    "hard": {"n": 24, "part_size": 96, "density_per_10000": 6720},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The exceptional coordinates form complementary swaps between each "
    "part-value label and its corresponding pair-value label."
)
PLACEBO_HINT = (
    "The displayed hexadecimal rows should be read carefully using the stated "
    "least-significant-bit indexing convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array [a_0,...,a_(k-1)] of exactly k integers, where "
        "0 <= a_i < s; position i chooses one vertex-card from color i and "
        "compactly expands to those k vertex-cards plus one prescribed "
        "edge-card for every unordered color pair."
    ),
    "bounds": {
        "array_length": "source_colors k = inst['source_colors']",
        "entry_lower_inclusive": 0,
        "entry_upper_exclusive": "inst['part_size']",
        "positions_are_color_classes": True,
        "expanded_set_size": "k + binomial(k,2)",
    },
}

NOTES = (
    "Section 1 fixes the generalized rule: a SET has k cards and, in every "
    "attribute, the k values are either all equal or all different. Section 2 "
    "and Theorem 1 fix the source Multicolored Clique instance, the n*k*(k-1) "
    "attribute groups, the k+binomial(k,2) values, and the vertex-card/edge-card "
    "construction used here. The corollary after Theorem 1 proves the same "
    "parameterization of SET W[1]-hard. The easy cases that shaped the presets "
    "are also in Section 2: two attributes are polynomial-time, fixed k has "
    "the XP enumeration algorithm, and the ordinary three-value single-round "
    "game can enumerate all SETs in polynomial time. Consequently k grows "
    "through the ladder and the family is not based on the paper's FPT "
    "multi-round parameter r. Generation samples one vertex uniformly in each "
    "color before drawing background edges, forces only the clique edges, and "
    "then applies the theorem; it never solves the resulting instance. Plant "
    "and nonplant vertices have the same labels and marginal generation rule, "
    "while the dense threshold makes the clique's degree increment smaller "
    "than background degree noise. Shuffling is inherent in the independent "
    "within-color labels. The adversary panel tests maximum degree, a "
    "left-to-right greedy clique, 256 randomized greedy restarts, centered "
    "spectral recovery, and a 10,000,000-node exact forward-checking clique solver."
)


# Filled from the script-owned bare run and the two isolated G9 runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _pair_index(i: int, j: int, k: int) -> int:
    """Lexicographic index of {i,j}, for 0 <= i < j < k."""
    if not (0 <= i < j < k):
        raise ValueError("pair indices must satisfy 0 <= i < j < k")
    return i * (2 * k - i - 1) // 2 + (j - i - 1)


def _block_map(inst: dict) -> dict[tuple[int, int], list[int]]:
    return {
        tuple(block["parts"]): list(block["rows"])
        for block in inst["blocks"]
    }


def _has_edge(inst: dict, i: int, a: int, j: int, b: int) -> bool:
    if i > j:
        i, j, a, b = j, i, b, a
    rows = inst["blocks"][_pair_index(i, j, inst["source_colors"])]["rows"]
    return bool((rows[a] >> b) & 1)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant a clique first and carry it through the paper's reduction.

    ``n`` is the number of source color classes.  The resulting generalized
    SET has q=n+binomial(n,2) cards and values.  Larger n therefore moves along
    the W[1]-hard parameter; ``part_size`` independently grows the haystack.
    """
    part_size = params.pop("part_size", 32)
    density = params.pop("density_per_10000", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if (isinstance(part_size, bool) or not isinstance(part_size, int)
            or part_size < 2):
        raise ValueError("part_size must be an integer at least 2")
    if density is None:
        density = int(round(10000 * math.exp(-2.0 * math.log(part_size) / (n - 1))))
    if (isinstance(density, bool) or not isinstance(density, int)
            or not 1 <= density <= 9999):
        raise ValueError("density_per_10000 must be an integer in 1..9999")

    rng = random.Random(seed)
    planted = [rng.randrange(part_size) for _ in range(n)]
    blocks = []
    edge_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            rows = []
            for a in range(part_size):
                mask = 0
                for b in range(part_size):
                    if rng.randrange(10000) < density:
                        mask |= 1 << b
                rows.append(mask)
            # The certificate exists before background generation conceptually;
            # this line merely carries it into the sampled public graph.
            rows[planted[i]] |= 1 << planted[j]
            edge_count += sum(row.bit_count() for row in rows)
            blocks.append({"parts": [i, j], "rows": rows})

    q = n + n * (n - 1) // 2
    attributes = part_size * n * (n - 1)
    return {
        "family": "generalized one-round SET via Multicolored Clique",
        "source_colors": n,
        "part_size": part_size,
        "density_per_10000": density,
        "blocks": blocks,
        "source_edge_count": edge_count,
        "set_size": q,
        "number_of_values": q,
        "number_of_attributes": attributes,
        "number_of_vertex_cards": n * part_size,
        "number_of_edge_cards": edge_count,
        "answer": planted,
    }


def _render_blocks(inst: dict) -> str:
    width = (inst["part_size"] + 3) // 4
    lines = []
    for block in inst["blocks"]:
        i, j = block["parts"]
        encoded = " ".join(format(row, f"0{width}x") for row in block["rows"])
        lines.append(f"{i},{j}: {encoded}")
    return "\n".join(lines)


def render(inst: dict) -> str:
    k = inst["source_colors"]
    s = inst["part_size"]
    q = inst["set_size"]
    statement = f"""Generalized one-round SET (compact card encoding)

A generalized SET with q values is a selection of exactly q distinct cards
such that, independently in every attribute, their q values are either all
equal or all different. Here q={q}. Values and all indices below are 0-based.

The dealt cards are specified exactly by a {k}-partite graph. Color classes are
0,...,{k - 1}; every class has local vertices 0,...,{s - 1}. For each color
pair i<j, the line below contains {s} fixed-width hexadecimal bitmasks, one for
each vertex a of color i in increasing order. Bit b (the least-significant bit
is bit 0) is 1 exactly when color-i vertex a is adjacent to color-j vertex b.
Leading zeroes are significant only as padding.

{_render_blocks(inst)}

This graph losslessly specifies the actual generalized-SET cards using the
construction below. There are {inst['number_of_attributes']} attributes named
(i,j,a), where i and j are distinct colors and 0<=a<{s}. There are {q} value
labels: P_i for each color i, and Q_ij for each unordered pair i<j.

* Vertex-card V(i,a) has value P_i in every attribute except (i,j,a), for each
  j!=i, where its value is Q_min(i,j),max(i,j).
* For every displayed graph edge joining (i,a) and (j,b), i<j, edge-card
  E(i,a,j,b) has value Q_ij in every attribute except (i,j,a), where it has
  P_i, and (j,i,b), where it has P_j.

You must select one vertex-card V(i,a_i) for every color and the edge-card
E(i,a_i,j,a_j) for every color pair i<j. These are {q} distinct cards. They
form a generalized SET exactly when every prescribed edge-card exists; the
complementary exceptions above then make every attribute contain all {q}
different value labels.

Output the local vertex labels [a_0,...,a_{k - 1}] as one JSON array of exactly
{k} integers. Position i is color i, each entry is in 0,...,{s - 1}, order is
therefore fixed, and equal numeric labels in different colors are allowed.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format only: <answer>{json.dumps([0] * k)}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON answer, tolerating prose and fenced JSON."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any compact SET witness without consulting ``inst['answer']``."""
    k = inst["source_colors"]
    s = inst["part_size"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k:
        return False, f"wrong number of color choices: expected {k}, got {len(answer)}"
    for i, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry for color {i} is not an integer"
        if not 0 <= value < s:
            return False, f"entry for color {i} is out of range 0..{s - 1}"

    # Executable form of the complementary-swap certificate.  The compact
    # answer expands to V(i,a_i) and E(i,a_i,j,a_j).  Such an edge-card exists
    # exactly at a 1 bit.  At every (i,j,x), V(i,a_i) swaps P_i -> Q_ij iff
    # x=a_i, while that same edge-card swaps Q_ij -> P_i iff x=a_i.  Thus all
    # q labels occur once in every attribute precisely when all bits below are 1.
    for i in range(k):
        for j in range(i + 1, k):
            if not _has_edge(inst, i, answer[i], j, answer[j]):
                return (
                    False,
                    f"missing edge-card for colors {i},{j} at local labels "
                    f"{answer[i]},{answer[j]}",
                )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated one-local-vertex-per-color language."""
    return [rng.randrange(inst["part_size"]) for _ in range(inst["source_colors"])]


def search_space(inst: dict) -> int | None:
    return inst["part_size"] ** inst["source_colors"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 2_000_000:
        return None
    count = 0
    ranges = [range(inst["part_size"])] * inst["source_colors"]
    for candidate in itertools.product(*ranges):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _adjacency(inst: dict) -> list[list[list[int]]]:
    """adj[i][a][j] is a bitmask of a's neighbors in color j."""
    k, s = inst["source_colors"], inst["part_size"]
    adj = [[[0 for _ in range(k)] for _ in range(s)] for _ in range(k)]
    for block in inst["blocks"]:
        i, j = block["parts"]
        for a, row in enumerate(block["rows"]):
            adj[i][a][j] = row
            bits = row
            while bits:
                bit = bits & -bits
                b = bit.bit_length() - 1
                bits -= bit
                adj[j][b][i] |= 1 << a
    return adj


def canonical_key(inst: dict) -> str:
    """A strong cheap invariant under color and within-color relabelling.

    Exact colored-graph isomorphism is intentionally not claimed.  The key
    combines every vertex's per-part degree/neighbor-degree profile with every
    bipartite block's two degree sequences.
    """
    k, s = inst["source_colors"], inst["part_size"]
    adj = _adjacency(inst)
    degree = [
        [sum(adj[i][a][j].bit_count() for j in range(k) if j != i)
         for a in range(s)]
        for i in range(k)
    ]
    part_profiles = []
    for i in range(k):
        vertices = []
        for a in range(s):
            across = []
            for j in range(k):
                if i == j:
                    continue
                bits = adj[i][a][j]
                neighbor_degree_sum = 0
                while bits:
                    bit = bits & -bits
                    b = bit.bit_length() - 1
                    bits -= bit
                    neighbor_degree_sum += degree[j][b]
                across.append((adj[i][a][j].bit_count(), neighbor_degree_sum))
            vertices.append((degree[i][a], tuple(sorted(across))))
        part_profiles.append(tuple(sorted(vertices)))

    block_profiles = []
    for block in inst["blocks"]:
        rows = block["rows"]
        row_degrees = sorted(row.bit_count() for row in rows)
        col_degrees = []
        for b in range(s):
            col_degrees.append(sum((row >> b) & 1 for row in rows))
        sides = sorted((tuple(row_degrees), tuple(sorted(col_degrees))))
        block_profiles.append((sum(row_degrees), sides[0], sides[1]))
    payload = [k, s, sorted(part_profiles), sorted(block_profiles)]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the source parts while keeping the compact answer length fixed."""
    if not isinstance(params, dict):
        return None
    k = int(params.get("n", 0))
    s = int(params.get("part_size", 0))
    if k < 3 or s < 2:
        return None
    new_s = max(s + 8, (3 * s + 1) // 2)
    density = int(round(10000 * math.exp(-2.0 * math.log(new_s) / (k - 1))))
    return {
        "n": k,
        "part_size": new_s,
        "density_per_10000": max(1, min(9999, density)),
    }


def _is_valid_candidate(inst: dict, candidate: object | None) -> bool:
    return candidate is not None and verify(inst, candidate)[0]


def _attack_outlier_degree(inst: dict) -> list[int]:
    adj = _adjacency(inst)
    k, s = inst["source_colors"], inst["part_size"]
    return [
        max(
            range(s),
            key=lambda a: (
                sum(adj[i][a][j].bit_count() for j in range(k) if j != i),
                -a,
            ),
        )
        for i in range(k)
    ]


def _attack_greedy(inst: dict) -> list[int] | None:
    k, s = inst["source_colors"], inst["part_size"]
    chosen = []
    for i in range(k):
        options = [
            a for a in range(s)
            if all(_has_edge(inst, j, chosen[j], i, a) for j in range(i))
        ]
        if not options:
            return None
        chosen.append(options[0])
    return chosen


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 256
) -> list[int] | None:
    k, s = inst["source_colors"], inst["part_size"]
    for _ in range(restarts):
        order = list(range(k))
        rng.shuffle(order)
        chosen = [-1] * k
        for color in order:
            options = [
                a for a in range(s)
                if all(
                    chosen[other] < 0
                    or _has_edge(inst, color, a, other, chosen[other])
                    for other in range(k)
                )
            ]
            if not options:
                break
            chosen[color] = rng.choice(options)
        else:
            return chosen
    return None


def _attack_exact_dpll(inst: dict, node_limit: int = 10_000_000) -> dict:
    """Complete multicolored-clique backtracking, stopped at a measured cap."""
    k, s = inst["source_colors"], inst["part_size"]
    adj = _adjacency(inst)
    full = (1 << s) - 1
    selected = [-1] * k
    nodes = 0
    hit_limit = False

    def visit(domains: list[int], remaining: tuple[int, ...]):
        nonlocal nodes, hit_limit
        if not remaining:
            return list(selected)
        if nodes >= node_limit:
            hit_limit = True
            return None
        color = min(remaining, key=lambda c: domains[c].bit_count())
        rest = tuple(c for c in remaining if c != color)
        bits = domains[color]
        order = []
        while bits:
            bit = bits & -bits
            value = bit.bit_length() - 1
            bits -= bit
            score = sum(
                (domains[c] & adj[color][value][c]).bit_count() for c in rest
            )
            order.append((-score, value))
        for _, value in sorted(order):
            nodes += 1
            if nodes > node_limit:
                hit_limit = True
                return None
            narrowed = list(domains)
            feasible = True
            for c in rest:
                narrowed[c] &= adj[color][value][c]
                if not narrowed[c]:
                    feasible = False
                    break
            if feasible:
                selected[color] = value
                found = visit(narrowed, rest)
                if found is not None:
                    return found
        selected[color] = -1
        return None

    started = time.perf_counter()
    answer = visit([full] * k, tuple(range(k)))
    elapsed = time.perf_counter() - started
    return {
        "candidate": answer,
        "nodes": nodes,
        "hit_limit": hit_limit,
        "wall_clock_sec": elapsed,
    }


def _attack_spectral(inst: dict, seed: int, iterations: int = 12) -> list[int]:
    """Centered adjacency power iteration, followed by one choice per color."""
    k, s = inst["source_colors"], inst["part_size"]
    rng = random.Random(seed)
    vector = [rng.random() - 0.5 for _ in range(k * s)]
    possible = (k * (k - 1) // 2) * s * s
    density = inst["source_edge_count"] / possible
    for _ in range(iterations):
        group_sums = [sum(vector[i * s:(i + 1) * s]) for i in range(k)]
        nxt = [0.0] * (k * s)
        for block in inst["blocks"]:
            i, j = block["parts"]
            rows = block["rows"]
            base_i = density * group_sums[j]
            base_j = density * group_sums[i]
            for a, row in enumerate(rows):
                bits = row
                total = 0.0
                source_value = vector[i * s + a]
                while bits:
                    bit = bits & -bits
                    b = bit.bit_length() - 1
                    bits -= bit
                    total += vector[j * s + b]
                    nxt[j * s + b] += source_value
                nxt[i * s + a] += total - base_i
            for b in range(s):
                nxt[j * s + b] -= base_j
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    high = [
        max(range(s), key=lambda a: vector[i * s + a]) for i in range(k)
    ]
    low = [
        min(range(s), key=lambda a: vector[i * s + a]) for i in range(k)
    ]
    return high if _is_valid_candidate(inst, high) else low


def _relabel_instance(
    inst: dict,
    color_map: list[int],
    vertex_maps: list[list[int]],
) -> dict:
    """Carry an instance and its certificate through genuine relabellings."""
    k, s = inst["source_colors"], inst["part_size"]
    if sorted(color_map) != list(range(k)):
        raise ValueError("color_map is not a permutation")
    if len(vertex_maps) != k or any(sorted(p) != list(range(s)) for p in vertex_maps):
        raise ValueError("a vertex map is not a permutation")
    new_rows = {
        (i, j): [0] * s for i in range(k) for j in range(i + 1, k)
    }
    for block in inst["blocks"]:
        old_i, old_j = block["parts"]
        for old_a, row in enumerate(block["rows"]):
            bits = row
            while bits:
                bit = bits & -bits
                old_b = bit.bit_length() - 1
                bits -= bit
                ni, nj = color_map[old_i], color_map[old_j]
                na = vertex_maps[old_i][old_a]
                nb = vertex_maps[old_j][old_b]
                if ni < nj:
                    new_rows[ni, nj][na] |= 1 << nb
                else:
                    new_rows[nj, ni][nb] |= 1 << na
    blocks = [
        {"parts": [i, j], "rows": rows}
        for (i, j), rows in sorted(new_rows.items())
    ]
    answer = [0] * k
    for old_i, old_value in enumerate(inst["answer"]):
        answer[color_map[old_i]] = vertex_maps[old_i][old_value]
    edge_count = sum(row.bit_count() for block in blocks for row in block["rows"])
    q = k + k * (k - 1) // 2
    return {
        "family": inst["family"],
        "source_colors": k,
        "part_size": s,
        "density_per_10000": inst["density_per_10000"],
        "blocks": blocks,
        "source_edge_count": edge_count,
        "set_size": q,
        "number_of_values": q,
        "number_of_attributes": s * k * (k - 1),
        "number_of_vertex_cards": k * s,
        "number_of_edge_cards": edge_count,
        "answer": answer,
    }


def _explicit_demo_set_check(inst: dict, answer: list[int]) -> bool:
    """Expand every selected demo card/value and check all-different directly."""
    k, s = inst["source_colors"], inst["part_size"]
    q = k + k * (k - 1) // 2

    def pair_value(i: int, j: int) -> int:
        if i > j:
            i, j = j, i
        return k + _pair_index(i, j, k)

    cards = [("V", i, answer[i], -1, -1) for i in range(k)]
    cards += [
        ("E", i, answer[i], j, answer[j])
        for i in range(k) for j in range(i + 1, k)
    ]
    for owner in range(k):
        for other in range(k):
            if owner == other:
                continue
            for position in range(s):
                values = []
                for kind, i, a, j, b in cards:
                    if kind == "V":
                        value = i
                        if i == owner and a == position:
                            value = pair_value(owner, other)
                    else:
                        value = pair_value(i, j)
                        if owner == i and other == j and position == a:
                            value = i
                        elif owner == j and other == i and position == b:
                            value = j
                    values.append(value)
                if sorted(values) != list(range(q)):
                    return False
    return True


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _find_corruption(
    inst: dict, mode: str, forbidden_reasons: set[str]
) -> tuple[list[int] | None, str]:
    truth = list(inst["answer"])
    k = len(truth)
    if mode == "swap":
        for i in range(k):
            for j in range(i + 1, k):
                if truth[i] == truth[j]:
                    continue
                bad = list(truth)
                bad[i], bad[j] = bad[j], bad[i]
                ok, why = verify(inst, bad)
                if not ok and why not in forbidden_reasons:
                    return bad, why
    elif mode == "duplicate":
        for i in range(k):
            for j in range(k):
                if i == j or truth[j] == truth[i]:
                    continue
                bad = list(truth)
                bad[j] = truth[i]
                ok, why = verify(inst, bad)
                if not ok and why not in forbidden_reasons:
                    return bad, why
    return None, f"could not construct a rejected {mode} corruption"


def selftest() -> dict:
    report: dict = {}

    # G1: all named presets, multiple seeds, JSON-native answers, and an
    # independent full coordinate expansion on the hand-scale preset.
    failures = []
    attempts = 0
    demo_expansions = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
            if preset == "demo":
                demo_expansions += 1
                if not _explicit_demo_set_check(inst, inst["answer"]):
                    failures.append(f"{preset}/{seed}: expanded SET failed")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "explicit_coordinate_expansions": demo_expansions,
        "failures": failures,
    }

    shipping = make_instance(seed=20240517, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five perturbation families, deliberately reaching different messages.
    cases = {}
    used_reasons = set()
    fixed = {
        "empty": [],
        "drop_one": shipping["answer"][:-1],
        "out_of_range": shipping["answer"][:-1] + [shipping["part_size"]],
    }
    for name, bad in fixed.items():
        ok, why = verify(shipping, bad)
        cases[name] = {"rejected": not ok, "reason": why}
        used_reasons.add(why)
    for mode in ("swap", "duplicate"):
        bad, precomputed = _find_corruption(shipping, mode, used_reasons)
        if bad is None:
            cases[mode] = {"rejected": False, "reason": precomputed}
        else:
            ok, why = verify(shipping, bad)
            cases[mode] = {"rejected": not ok, "reason": why}
            used_reasons.add(why)
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and a markdown fence inside the required tags.
    response = (
        "The complementary swaps select these local labels.\n\n"
        "<answer>```json\n"
        + json.dumps(shipping["answer"])
        + "\n```</answer>\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"]
        and parse_answer("no tagged answer here") is None
        and parse_answer("<answer>{bad json}</answer>") is None,
        "parsed": parsed,
    }

    # G4: one uniformly chosen local vertex in every color is the strongest
    # free structural prior.  Adjacency is not baked in because satisfying all
    # those constraints is exactly the search problem.
    guess_rng = random.Random(934857)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6
        and search_space(shipping) > 1_000_000,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_probability": guess_hits / guess_total,
        "candidate_space": search_space(shipping),
        "prior": "uniform over one in-range local vertex for every color",
    }

    # G5: shipping density plus actual cost of the strongest capped attack.
    baseline_inst = make_instance(seed=100, **DIFFICULTY[SHIPPING_DIFFICULTY])
    baseline = _attack_exact_dpll(baseline_inst)
    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": not _is_valid_candidate(baseline_inst, baseline["candidate"])
        and baseline["nodes"] >= 10_000_000
        and demo_count is not None,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_solution_density_estimate": guess_hits / guess_total,
        "shipping_candidate_space": search_space(shipping),
        "baseline_wall_clock_seconds": baseline["wall_clock_sec"],
        "baseline_search_nodes": baseline["nodes"],
        "baseline_node_budget": 10_000_000,
        "baseline_solved": int(_is_valid_candidate(baseline_inst, baseline["candidate"])),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
    }

    # G6: construction-aware generic probes, a spectral planted-clique probe,
    # and the standard exact forward-checking algorithm for the source problem.
    names = [
        "outlier_max_degree",
        "greedy_left_to_right",
        "random_greedy_256_restarts",
        "centered_spectral_power_iteration",
        "exact_clique_dpll_10000000_nodes",
    ]
    attack_results = {name: {"successes": 0, "attempts": 0} for name in names}
    dpll_nodes = 0
    dpll_seconds = 0.0
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_max_degree": _attack_outlier_degree(inst),
            "greedy_left_to_right": _attack_greedy(inst),
            "random_greedy_256_restarts": _attack_random_restarts(
                inst, random.Random(seed ^ 0xA51C), 256
            ),
            "centered_spectral_power_iteration": _attack_spectral(
                inst, seed ^ 0xC0FFEE, 12
            ),
        }
        exact = _attack_exact_dpll(inst)
        candidates["exact_clique_dpll_10000000_nodes"] = exact["candidate"]
        dpll_nodes += exact["nodes"]
        dpll_seconds += exact["wall_clock_sec"]
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(
                _is_valid_candidate(inst, candidate)
            )
    report["G6_adversary_panel"] = {
        "pass": all(
            item["successes"] == 0 and item["attempts"] >= 8
            for item in attack_results.values()
        ),
        "attacks": attack_results,
        "standard_algorithm": {
            "name": "exact multicolored-clique DPLL with forward checking",
            "completeness": "complete if run without the reported node cap",
            "complexity": "O(part_size^source_colors) worst case",
            "aggregate_nodes": dpll_nodes,
            "aggregate_wall_clock_seconds": dpll_seconds,
        },
    }

    # G7: named work sizes grow, n itself grows, and twice the shipping n builds.
    work_sizes = []
    for params in DIFFICULTY.values():
        inst = make_instance(seed=7, **params)
        work_sizes.append(
            inst["source_colors"] * inst["part_size"]
            + inst["source_edge_count"]
        )
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["density_per_10000"] = int(round(
        10000 * math.exp(
            -2.0 * math.log(doubled_params["part_size"])
            / (doubled_params["n"] - 1)
        )
    ))
    doubled = make_instance(seed=7, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(work_sizes, work_sizes[1:]))
        and doubled_ok,
        "named_work_sizes": work_sizes,
        "named_n_values": [p["n"] for p in DIFFICULTY.values()],
        "doubled_n": doubled_params["n"],
        "doubled_work_size": (
            doubled["source_colors"] * doubled["part_size"]
            + doubled["source_edge_count"]
        ),
        "doubled_verification": doubled_why,
    }

    # G8: color permutations, within-color permutations, and their composition.
    invariant_checks = 0
    transformed_verify_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        relabel_rng = random.Random(seed ^ 0x8CA1)
        color_perm = list(range(inst["source_colors"]))
        relabel_rng.shuffle(color_perm)
        identity_colors = list(range(inst["source_colors"]))
        identity_vertices = [list(range(inst["part_size"]))
                             for _ in range(inst["source_colors"])]
        vertex_perms = []
        for _ in range(inst["source_colors"]):
            permutation = list(range(inst["part_size"]))
            relabel_rng.shuffle(permutation)
            vertex_perms.append(permutation)
        transforms = [
            _relabel_instance(inst, color_perm, identity_vertices),
            _relabel_instance(inst, identity_colors, vertex_perms),
            _relabel_instance(inst, color_perm, vertex_perms),
        ]
        for changed in transforms:
            invariant_checks += 1
            if canonical_key(changed) != key:
                g8_failures.append(f"seed {seed}: canonical key changed")
            if seed == 0:
                transformed_verify_checks += 1
                ok, why = verify(changed, changed["answer"])
                if not ok:
                    g8_failures.append(f"real relabelling failed: {why}")
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "transformed_instances_verified": transformed_verify_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": g8_failures,
        "invariant_kind": "degree and neighbor-degree refinement; not full GI",
    }

    # G9: oracle arms are transcript-derived; size and route counts are exact.
    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    route_operations = shipping["source_colors"] * (
        shipping["source_colors"] - 1
    ) // 2
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
    hinted_hardened = (
        G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
        and arms["hinted"]["attempts"] >= 3
        and arms["hinted"]["solved"] == 0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and route_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
