"""Verified generator for the Section 5.2 good-seed core of 2-OTSS.

The module is deterministic for ``(n, seed, params)``, uses only the Python
standard library, performs no file I/O, and prints nothing when imported.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import re


DIFFICULTY = {
    "demo": {"n": 3, "part_size": 4, "degree": 2, "mix_steps": 2},
    "easy": {"n": 16, "part_size": 16, "degree": 11, "mix_steps": 6},
    "medium": {"n": 20, "part_size": 18, "degree": 13, "mix_steps": 7},
    "hard": {"n": 24, "part_size": 20, "degree": 14, "mix_steps": 8},
}
SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Definition and paper regime. Section 1 ("The Model") fixes the synchronous
2-Opinion Target Set Selection process and requires equality and stability of
the two final opinion sets. Section 3 notes the universal copying shortcut when
B >= |S_a|+|S_b| and reduces ordinary Target Set Selection to 2-OTSS. The
generator uses the sharper Section 5.2 construction: its selection gadgets
force a "good" solution with T_a empty and exactly one T_b vertex in each
vertex- and edge-selection group; Lemma 13 proves that its four-round incidence
gadgets balance exactly when every selected edge is incident with the selected
endpoint vertices. Theorem 7 proves W[1]-hardness, plus its ETH lower bound, in
this constant-four-round regime. We specialize the reduction source to
Partitioned Clique (H=K_n), explicitly identified in Section 5 as W[1]-complete.

Easy regimes avoided. Theorem 1 is FPT for vertex cover, Theorem 2 for
3-path-vertex-cover, Theorem 3 for vertex integrity, and Theorem 4 for the
combined parameters rounds, maximum threshold, and treewidth. Fixed n is also
enumerable in O(part_size**n). Here n, the budget, the structural parameters,
and the reduction's thresholds all grow. In the expanded reduction there are
six initial a-seeds per selection gadget and additional special a-seeds, so its
budget is strictly below |S_a|+|S_b| and Section 3's copying shortcut is
unavailable.

Inverse generation and planting. A label in every colour class is sampled
first. Independently for each class pair, a dense simple regular bipartite graph
is generated, a uniformly random one of its edges is chosen, and vertex labels
are exchanged so that this ordinary edge joins the sampled labels. Thus every
host vertex has exactly the same per-class degree and each planted edge was
drawn from exactly the same edge distribution as a decoy edge. The returned
witness consists of the corresponding selection-vertex IDs in the four-round
reduction.

Attacks. The outlier attack uses triangle participation, a substantially richer
per-vertex statistic than degree (degree is exactly tied). The deterministic
attack greedily extends left-to-right by prior adjacency and triangle score.
The restart attack performs randomized minimum-remaining-values extension with
look-ahead support. selftest() requires all three to miss on eight shipping
seeds. The theorem is worst-case, not an average-case result for conditioned
regular hosts; the oracle loop and attacks are empirical safeguards rather than
a proof of distributional hardness.

Canonicalization. canonical_key never uses the seed, answer, rendering, input
order, or raw labels. It hashes per-class profiles of relabelling- and
transpose-invariant bipartite common-neighbour signatures. This is a strong
cheap invariant, not a complete multipartite-graph isomorphism algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _require_int(name: str, value: object, low: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise ValueError(f"{name} must be an integer at least {low}")
    return value


def _random_bit(mask: int, rng: random.Random) -> int:
    """Return a uniformly random set-bit index from a nonzero integer mask."""
    rank = rng.randrange(mask.bit_count())
    while rank:
        mask &= mask - 1
        rank -= 1
    return (mask & -mask).bit_length() - 1


def _swap_bit_labels(mask: int, a: int, b: int) -> int:
    if a == b:
        return mask
    abit = (mask >> a) & 1
    bbit = (mask >> b) & 1
    if abit != bbit:
        mask ^= (1 << a) | (1 << b)
    return mask


def _regular_matrix(q: int, degree: int, forced_left: int, forced_right: int,
                    mix_steps: int, rng: random.Random) -> list[int]:
    """Generate a label-exchangeable regular bipartite graph.

    A uniformly selected ordinary edge is relabelled to the requested endpoint
    pair.  This is preferable to inserting a special edge: degrees stay exact,
    and the distinguished edge has the same local source distribution as every
    decoy edge.
    """
    left = list(range(q))
    right = list(range(q))
    rng.shuffle(left)
    rng.shuffle(right)
    rows = [0] * q
    for pos, vertex in enumerate(left):
        for shift in range(degree):
            rows[vertex] |= 1 << right[(pos + shift) % q]

    # Degree-preserving 2-switches erase most of the initial circulant pattern.
    for _ in range(mix_steps * q * degree):
        x1 = rng.randrange(q)
        x2 = rng.randrange(q - 1)
        if x2 >= x1:
            x2 += 1
        y1 = _random_bit(rows[x1], rng)
        y2 = _random_bit(rows[x2], rng)
        if y1 == y2:
            continue
        if ((rows[x1] >> y2) & 1) or ((rows[x2] >> y1) & 1):
            continue
        rows[x1] ^= (1 << y1) | (1 << y2)
        rows[x2] ^= (1 << y2) | (1 << y1)

    # Select an ordinary edge uniformly: a uniform row followed by a uniform
    # neighbor is uniform because every row has the same degree.
    old_left = rng.randrange(q)
    old_right = _random_bit(rows[old_left], rng)
    rows[old_left], rows[forced_left] = rows[forced_left], rows[old_left]
    rows = [_swap_bit_labels(mask, old_right, forced_right) for mask in rows]

    if not ((rows[forced_left] >> forced_right) & 1):
        raise AssertionError("internal planting failure")
    if any(mask.bit_count() != degree for mask in rows):
        raise AssertionError("internal row-degree failure")
    for y in range(q):
        if sum((mask >> y) & 1 for mask in rows) != degree:
            raise AssertionError("internal column-degree failure")
    return rows


def _pair_indices(k: int):
    return itertools.combinations(range(k), 2)


def _ordered_pairs(inst: dict) -> list[dict]:
    pairs = inst["pairs"]
    keys = [(rec["i"], rec["j"]) for rec in pairs]
    if keys == sorted(keys):
        return pairs
    return sorted(pairs, key=lambda rec: (rec["i"], rec["j"]))


def _columns(rows: list[int], q: int) -> list[int]:
    cols = [0] * q
    for x, mask in enumerate(rows):
        while mask:
            bit = mask & -mask
            y = bit.bit_length() - 1
            cols[y] |= 1 << x
            mask -= bit
    return cols


def _adjacency(inst: dict) -> list[list[list[int] | None]]:
    k = inst["n"]
    q = inst["part_size"]
    adj: list[list[list[int] | None]] = [[None] * k for _ in range(k)]
    for rec in inst["pairs"]:
        i, j = rec["i"], rec["j"]
        rows = list(rec["rows"])
        adj[i][j] = rows
        adj[j][i] = _columns(rows, q)
    return adj


def _edge_id(rec: dict, degree: int, left: int, right: int) -> int | None:
    mask = rec["rows"][left]
    if not ((mask >> right) & 1):
        return None
    rank = (mask & ((1 << right) - 1)).bit_count()
    return rec["offset"] + degree * left + rank


def _decode_edge_id(rec: dict, degree: int, selector: int) -> tuple[int, int]:
    rel = selector - rec["offset"]
    left, rank = divmod(rel, degree)
    mask = rec["rows"][left]
    for _ in range(rank):
        mask &= mask - 1
    right = (mask & -mask).bit_length() - 1
    return left, right


def _answer_from_labels(inst: dict, labels: list[int]) -> list[int] | None:
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    if len(labels) != k:
        return None
    answer = [c * q + labels[c] for c in range(k)]
    for rec in _ordered_pairs(inst):
        selector = _edge_id(rec, degree, labels[rec["i"]], labels[rec["j"]])
        if selector is None:
            return None
        answer.append(selector)
    return answer


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a clique witness first, then build regular pair graphs around it."""
    k = _require_int("n", n, 3)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    q = _require_int("part_size", params.pop("part_size", 16), 4)
    degree = _require_int("degree", params.pop("degree", max(2, (7 * q) // 10)), 2)
    mix_steps = _require_int("mix_steps", params.pop("mix_steps", 6), 0)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if degree > q - 2:
        raise ValueError("degree must be at most part_size - 2")

    rng = random.Random(seed)

    # G: the semantic answer is sampled before any constraint matrix exists.
    planted_labels = [rng.randrange(q) for _ in range(k)]
    pairs: list[dict] = []
    per_edge_group = q * degree
    first_edge_id = k * q
    for pair_no, (i, j) in enumerate(_pair_indices(k)):
        rows = _regular_matrix(q, degree, planted_labels[i], planted_labels[j],
                               mix_steps, rng)
        pairs.append({
            "i": i,
            "j": j,
            "offset": first_edge_id + pair_no * per_edge_group,
            "rows": rows,
        })

    budget = k + k * (k - 1) // 2
    selector_count = first_edge_id + len(pairs) * per_edge_group
    inst = {
        "n": k,
        "part_size": q,
        "degree": degree,
        "mix_steps": mix_steps,
        "rounds": 4,
        "budget": budget,
        "selector_count": selector_count,
        "pairs": pairs,
    }
    answer = _answer_from_labels(inst, planted_labels)
    if answer is None:
        raise AssertionError("internal witness construction failure")
    inst["answer"] = answer
    return inst


def render(inst: dict) -> str:
    """Render the self-contained compressed good-seed problem."""
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    budget = inst["budget"]
    width = max(1, (q + 3) // 4)
    lines = [
        "FOUR-ROUND TWO-OPINION GOOD-SEED SEARCH",
        "",
        "This is the exact selection core of a four-round 2-Opinion Target Set",
        "Selection instance. There are K vertex-selection groups (colour classes)",
        "and one edge-selection group for every unordered pair of classes.",
        "A good added seed set T_b chooses exactly one selection vertex from every",
        "group; T_a is empty. The incidence gadgets balance after round 4 exactly",
        "when every chosen edge has the two chosen vertex labels as its endpoints.",
        "Thus no knowledge of opinion diffusion or of the source paper is needed:",
        "the complete, exact witness conditions are stated below.",
        "",
        f"K = {k}",
        f"Q = {q}",
        f"R = {degree}",
        f"B = {budget}",
        "",
        "Vertex groups are ordered by class c = 0,1,...,K-1. Class c has local",
        "labels x = 0,1,...,Q-1. Choosing label x in class c means choosing the",
        "global selection-vertex ID c*Q+x.",
        "",
        "Edge groups are ordered by (i,j) in the PAIR lines below; the lines use",
        "lexicographic order 0<=i<j<K. ROW_MASKS contains Q hexadecimal integers.",
        "For row u, bit v (least-significant bit is v=0) is 1 exactly when edge",
        "(u,v) is available. Leading zeroes have no meaning. Every row has R bits.",
        "Available edges are ordered by increasing u and then increasing v. If a",
        "PAIR has OFFSET o, edge (u,v) has global selection-vertex ID",
        "o + R*u + (number of set bits below v in row u).",
        "",
        "A valid witness is an ordered JSON array of exactly B distinct global IDs:",
        "first one ID from each of the K vertex groups, then one ID from each PAIR",
        "group in the displayed order. For every PAIR (i,j), its chosen edge must",
        "equal (the chosen local label in class i, the chosen local label in class",
        "j). Order is required, IDs are 0-indexed integers, and repeats are forbidden.",
        "",
        "PAIR_DATA_BEGIN",
    ]
    for rec in _ordered_pairs(inst):
        masks = ",".join(format(mask, f"0{width}x") for mask in rec["rows"])
        lines.append(
            f"PAIR {rec['i']} {rec['j']} OFFSET {rec['offset']} ROW_MASKS {masks}"
        )
    lines.extend([
        "PAIR_DATA_END",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON array",
        f"containing exactly {budget} integer global selection-vertex IDs.",
        "Example of the required syntax (not a solution): <answer>[0,16]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def _valid_parsed_list(value: object) -> bool:
    return (isinstance(value, list)
            and all(not isinstance(x, bool) and isinstance(x, int) for x in value))


def _json_array_from_body(body: str) -> list[int] | None:
    body = body.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        value = None
    if _valid_parsed_list(value):
        return value
    decoder = json.JSONDecoder()
    for pos, char in enumerate(body):
        if char != "[":
            continue
        try:
            value, _ = decoder.raw_decode(body[pos:])
        except (TypeError, ValueError):
            continue
        if _valid_parsed_list(value):
            return value
    return None


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed integer JSON array from model output."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        value = _json_array_from_body(body)
        if value is not None:
            return value
    for body in reversed(re.findall(r"```(?:json)?\s*(.*?)\s*```", text,
                                    re.I | re.S)):
        value = _json_array_from_body(body)
        if value is not None:
            return value
    return _json_array_from_body(text)


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any good four-round seed witness; never inspect the planted answer."""
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    budget = inst["budget"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of integer selection IDs"
    if not answer:
        return False, "answer must be a non-empty list"
    if len(answer) != budget:
        return False, f"wrong number of IDs: expected {budget}, got {len(answer)}"
    for pos, selector in enumerate(answer):
        if isinstance(selector, bool) or not isinstance(selector, int):
            return False, f"ID at position {pos} is not an integer"
        if selector < 0 or selector >= inst["selector_count"]:
            return False, (f"ID {selector} at position {pos} is outside the inclusive "
                           f"range 0..{inst['selector_count'] - 1}")
    if len(set(answer)) != len(answer):
        return False, "duplicate selection ID"

    labels = []
    for c in range(k):
        low, high = c * q, (c + 1) * q
        selector = answer[c]
        if not (low <= selector < high):
            return False, (f"position {c} must select from vertex group {c} "
                           f"(IDs {low}..{high - 1})")
        labels.append(selector - low)

    for pair_pos, rec in enumerate(_ordered_pairs(inst)):
        pos = k + pair_pos
        low = rec["offset"]
        high = low + q * degree
        selector = answer[pos]
        if not (low <= selector < high):
            return False, (f"position {pos} must select from edge group "
                           f"({rec['i']},{rec['j']}) (IDs {low}..{high - 1})")
        left, right = _decode_edge_id(rec, degree, selector)
        want_left, want_right = labels[rec["i"]], labels[rec["j"]]
        if left != want_left:
            return False, (f"incidence mismatch for pair ({rec['i']},{rec['j']}): "
                           f"chosen edge starts at {left}, expected {want_left}")
        if right != want_right:
            return False, (f"incidence mismatch for pair ({rec['i']},{rec['j']}): "
                           f"chosen edge ends at {right}, expected {want_right}")
    return True, "ok"


def random_candidate(inst: dict, rng) -> object:
    """Sample a group-correct candidate with endpoint-aware edge choices.

    Vertex labels are uniform. Whenever their exact edge exists, the uniquely
    consistent edge selector is used. Otherwise the fallback selector is chosen
    to match one endpoint. This is much stronger than uniform sampling over the
    enormous raw product of all edge groups and does not use the planted answer.
    """
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    labels = [rng.randrange(q) for _ in range(k)]
    candidate = [c * q + labels[c] for c in range(k)]
    for rec in _ordered_pairs(inst):
        left, right = labels[rec["i"]], labels[rec["j"]]
        selector = _edge_id(rec, degree, left, right)
        if selector is None:
            if rng.randrange(2) == 0:
                other_right = _random_bit(rec["rows"][left], rng)
                selector = _edge_id(rec, degree, left, other_right)
            else:
                possible_left = [u for u, mask in enumerate(rec["rows"])
                                 if (mask >> right) & 1]
                other_left = possible_left[rng.randrange(len(possible_left))]
                selector = _edge_id(rec, degree, other_left, right)
        if selector is None:
            raise AssertionError("regular graph supplied no fallback edge")
        candidate.append(selector)
    return candidate


def search_space(inst: dict) -> int | None:
    """Raw shape-correct product: one selection from every displayed group."""
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    pair_count = k * (k - 1) // 2
    return pow(q, k) * pow(q * degree, pair_count)


def _count_cliques(inst: dict, cap: int = 2_000_000) -> int | None:
    k = inst["n"]
    q = inst["part_size"]
    if pow(q, k) > cap:
        return None
    adj = _adjacency(inst)
    total = 0
    for labels in itertools.product(range(q), repeat=k):
        good = True
        for i, j in _pair_indices(k):
            rows = adj[i][j]
            if rows is None or not ((rows[labels[i]] >> labels[j]) & 1):
                good = False
                break
        if good:
            total += 1
    return total


def enumerate_all(inst: dict) -> int | None:
    """Count all good seed sets when at most two million label tuples exist."""
    return _count_cliques(inst)


def _bipartite_signature(rows: list[int], q: int) -> tuple:
    """Invariant under relabelling either side and under transposition."""
    cols = _columns(rows, q)

    def side_signature(side: list[int]) -> tuple:
        vertex_profiles = []
        for i, mask in enumerate(side):
            common = sorted((mask & side[j]).bit_count()
                            for j in range(q) if j != i)
            vertex_profiles.append(tuple(common))
        return tuple(sorted(vertex_profiles))

    a, b = side_signature(rows), side_signature(cols)
    return tuple(sorted((a, b)))


def canonical_key(inst: dict) -> str:
    """Return a strong cheap multipartite-isomorphism invariant."""
    k = inst["n"]
    q = inst["part_size"]
    pair_tokens: dict[tuple[int, int], str] = {}
    for rec in inst["pairs"]:
        signature = _bipartite_signature(rec["rows"], q)
        token = hashlib.sha256(repr(signature).encode("ascii")).hexdigest()
        pair_tokens[(rec["i"], rec["j"])] = token
    class_profiles = []
    for c in range(k):
        incident = []
        for d in range(k):
            if c == d:
                continue
            incident.append(pair_tokens[(min(c, d), max(c, d))])
        class_profiles.append(tuple(sorted(incident)))
    payload = {
        "family": "regular-multipartite-good-seed-v1",
        "k": k,
        "q": q,
        "degree": inst["degree"],
        "pair_tokens": sorted(pair_tokens.values()),
        "class_profiles": sorted(class_profiles),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase both the W[1] parameter and each colour-class domain."""
    current = dict(params)
    new_q = int(current.get("part_size", 16)) + 2
    degree = max(2, min(new_q - 2, round(0.70 * new_q)))
    return {
        "n": int(current["n"]) + 4,
        "part_size": new_q,
        "degree": degree,
        "mix_steps": int(current.get("mix_steps", 6)) + 1,
    }


# ---------------------------------------------------------------------------
# Self-test helpers: attacks and explicit relabellings.


def _triangle_scores(inst: dict) -> list[list[int]]:
    k = inst["n"]
    q = inst["part_size"]
    adj = _adjacency(inst)
    scores = [[0] * q for _ in range(k)]
    for c in range(k):
        others = [x for x in range(k) if x != c]
        for value in range(q):
            score = 0
            for at, i in enumerate(others):
                left_mask = adj[c][i][value]  # type: ignore[index]
                for j in others[at + 1:]:
                    right_mask = adj[c][j][value]  # type: ignore[index]
                    scan = left_mask
                    while scan:
                        bit = scan & -scan
                        u = bit.bit_length() - 1
                        scan -= bit
                        score += (adj[i][j][u] & right_mask).bit_count()  # type: ignore[index]
            scores[c][value] = score
    return scores


def _fallback_from_labels(inst: dict, labels: list[int]) -> list[int]:
    # A fixed seed only governs attack tie/fallback behavior, not the instance.
    rng = random.Random(0xA77AC)
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    candidate = [c * q + labels[c] for c in range(k)]
    for rec in _ordered_pairs(inst):
        left, right = labels[rec["i"]], labels[rec["j"]]
        selector = _edge_id(rec, degree, left, right)
        if selector is None:
            other = _random_bit(rec["rows"][left], rng)
            selector = _edge_id(rec, degree, left, other)
        if selector is None:
            raise AssertionError("missing fallback")
        candidate.append(selector)
    return candidate


def _attack_outlier(inst: dict) -> list[int]:
    scores = _triangle_scores(inst)
    labels = [max(range(inst["part_size"]), key=lambda x: (scores[c][x], -x))
              for c in range(inst["n"])]
    return _fallback_from_labels(inst, labels)


def _attack_greedy(inst: dict) -> list[int]:
    k = inst["n"]
    q = inst["part_size"]
    adj = _adjacency(inst)
    scores = _triangle_scores(inst)
    labels: list[int] = []
    for c in range(k):
        def merit(value: int):
            prior = sum((adj[d][c][labels[d]] >> value) & 1  # type: ignore[index]
                        for d in range(c))
            return prior, scores[c][value], -value
        labels.append(max(range(q), key=merit))
    return _fallback_from_labels(inst, labels)


def _attack_random_restart(inst: dict, seed: int, restarts: int = 32) -> list[int]:
    k = inst["n"]
    q = inst["part_size"]
    adj = _adjacency(inst)
    rng = random.Random(seed)
    full = (1 << q) - 1
    last_labels = [0] * k
    for _ in range(restarts):
        first_class = rng.randrange(k)
        chosen = {first_class: rng.randrange(q)}
        while len(chosen) < k:
            options = []
            for c in range(k):
                if c in chosen:
                    continue
                mask = full
                for other, value in chosen.items():
                    mask &= adj[other][c][value]  # type: ignore[index]
                candidates = []
                scan = mask
                while scan:
                    bit = scan & -scan
                    value = bit.bit_length() - 1
                    scan -= bit
                    support = sum(adj[c][future][value].bit_count()  # type: ignore[index]
                                  for future in range(k)
                                  if future not in chosen and future != c)
                    candidates.append((support, value))
                options.append((len(candidates), c, candidates))
            _, next_class, candidates = min(options, key=lambda x: (x[0], x[1]))
            if not candidates:
                break
            candidates.sort(reverse=True)
            chosen[next_class] = rng.choice(candidates[:min(3, len(candidates))])[1]
        for c in range(k):
            last_labels[c] = chosen.get(c, rng.randrange(q))
        if len(chosen) == k:
            answer = _answer_from_labels(inst, [chosen[c] for c in range(k)])
            if answer is not None:
                return answer
    return _fallback_from_labels(inst, last_labels)


def _relabel_instance(inst: dict, class_map: list[int],
                      local_maps: list[list[int]], reorder: bool = False) -> dict:
    """Carry an instance and its witness through a genuine family symmetry."""
    k = inst["n"]
    q = inst["part_size"]
    degree = inst["degree"]
    if sorted(class_map) != list(range(k)):
        raise ValueError("class_map is not a permutation")
    if any(sorted(perm) != list(range(q)) for perm in local_maps):
        raise ValueError("a local map is not a permutation")

    matrices: dict[tuple[int, int], list[int]] = {}
    for rec in inst["pairs"]:
        old_i, old_j = rec["i"], rec["j"]
        new_i, new_j = class_map[old_i], class_map[old_j]
        key = (min(new_i, new_j), max(new_i, new_j))
        rows = [0] * q
        for u, mask in enumerate(rec["rows"]):
            scan = mask
            while scan:
                bit = scan & -scan
                v = bit.bit_length() - 1
                scan -= bit
                nu, nv = local_maps[old_i][u], local_maps[old_j][v]
                if new_i < new_j:
                    rows[nu] |= 1 << nv
                else:
                    rows[nv] |= 1 << nu
        matrices[key] = rows

    pairs = []
    first_edge_id = k * q
    group_size = q * degree
    for pair_no, (i, j) in enumerate(_pair_indices(k)):
        pairs.append({"i": i, "j": j,
                      "offset": first_edge_id + pair_no * group_size,
                      "rows": matrices[(i, j)]})
    if reorder:
        pairs.reverse()

    transformed = {
        "n": k,
        "part_size": q,
        "degree": degree,
        "mix_steps": inst["mix_steps"],
        "rounds": 4,
        "budget": inst["budget"],
        "selector_count": inst["selector_count"],
        "pairs": pairs,
    }
    old_labels = [inst["answer"][c] - c * q for c in range(k)]
    new_labels = [0] * k
    for old_c in range(k):
        new_labels[class_map[old_c]] = local_maps[old_c][old_labels[old_c]]
    transformed_answer = _answer_from_labels(transformed, new_labels)
    if transformed_answer is None:
        raise AssertionError("relabelled witness ceased to be valid")
    transformed["answer"] = transformed_answer
    return transformed


def selftest() -> dict:
    """Run the mandatory G1--G8 gates and return JSON-serializable evidence."""
    report: dict[str, object] = {}

    # G1: every named preset, several seeds.
    g1_total = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total - len(g1_failures),
        "total": g1_total,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)

    # G2: named corruptions, each routed to a different diagnostic.
    corruptions = {}
    dropped = list(inst["answer"][:-1])
    swapped = list(inst["answer"])
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(inst["answer"])
    duplicated[1] = duplicated[0]
    out_of_range = list(inst["answer"])
    out_of_range[-1] = inst["selector_count"]
    for name, candidate in {
        "drop_one": dropped,
        "swap_two": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in corruptions.values())
                 and len(set(reasons)) == len(reasons)),
        "rejected": sum(entry["rejected"] for entry in corruptions.values()),
        "total": len(corruptions),
        "distinct_reasons": len(set(reasons)),
        "cases": corruptions,
    }

    # G3: tagged prose, a fence inside tags, and an untagged fenced fallback.
    encoded = json.dumps(inst["answer"])
    responses = [
        f"I checked all incidence pairs.\n<answer>{encoded}</answer>\nDone.",
        f"Final result:\n<answer>```json\n{encoded}\n```</answer>",
        f"Here is the requested array:\n```json\n{encoded}\n```",
    ]
    parsed = [parse_answer(text) for text in responses]
    report["G3_round_trip"] = {
        "pass": all(value == inst["answer"] for value in parsed)
                and parse_answer("garbage without an array") is None,
        "parsed_variants": sum(value == inst["answer"] for value in parsed),
        "total_variants": len(parsed),
        "garbage_returns_none": parse_answer("garbage without an array") is None,
    }

    # G4: labels are sampled first, and every possible matching edge selector is
    # filled in. This is the solver-aware q^k prior, not the raw group product.
    guess_inst = make_instance(seed=314159, **shipping)
    guess_rng = random.Random(0xC0FFEE)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        candidate = random_candidate(guess_inst, guess_rng)
        if verify(guess_inst, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "structure_aware_space": pow(guess_inst["part_size"], guess_inst["n"]),
        "naive_group_product": search_space(guess_inst),
        "prior": "uniform vertex label per class; exact edge selector whenever available",
    }

    # G5: exact enumeration on readable small instances. Report both the raw
    # group-product fraction and the more honest vertex-label-space fraction.
    sparse_rows = []
    sparse_pass = True
    for seed in range(3):
        small = make_instance(n=7, seed=seed, part_size=5, degree=2, mix_steps=5)
        count = enumerate_all(small)
        raw = search_space(small)
        structured = pow(small["part_size"], small["n"])
        if count is None:
            sparse_pass = False
            continue
        structured_fraction = count / structured
        sparse_pass &= structured_fraction < 1e-3
        sparse_rows.append({
            "seed": seed,
            "solutions": count,
            "naive_space": raw,
            "naive_fraction": count / raw,
            "structure_aware_space": structured,
            "structure_aware_fraction": structured_fraction,
        })
    report["G5_sparse"] = {
        "pass": bool(sparse_pass and len(sparse_rows) == 3),
        "instances": sparse_rows,
    }

    # G6: attacks must find no witness on at least eight unrelated instances.
    attack_results = {
        "triangle_outlier": {"successes": 0, "seeds": 8},
        "left_to_right_greedy": {"successes": 0, "seeds": 8},
        "random_restart_mrv_32": {"successes": 0, "seeds": 8},
    }
    equal_degree_checks = 0
    for seed in range(8):
        attacked = make_instance(seed=50_000 + seed, **shipping)
        if verify(attacked, _attack_outlier(attacked))[0]:
            attack_results["triangle_outlier"]["successes"] += 1
        if verify(attacked, _attack_greedy(attacked))[0]:
            attack_results["left_to_right_greedy"]["successes"] += 1
        restart = _attack_random_restart(attacked, seed=90_000 + seed, restarts=32)
        if verify(attacked, restart)[0]:
            attack_results["random_restart_mrv_32"]["successes"] += 1
        if all(mask.bit_count() == attacked["degree"]
               for rec in attacked["pairs"] for mask in rec["rows"]):
            equal_degree_checks += 1
    report["G6_adversary_panel"] = {
        "pass": (all(row["successes"] == 0 for row in attack_results.values())
                 and equal_degree_checks == 8),
        "attacks": attack_results,
        "all_regular_degree_checks": equal_degree_checks,
        "regular_degree_total": 8,
    }

    # G7: double the principal size parameter without relaxing density.
    doubled_params = dict(shipping)
    doubled_params["n"] = shipping["n"] * 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_budget": doubled["budget"],
        "doubled_selector_count": doubled["selector_count"],
        "planted_verify": doubled_ok,
        "reason": doubled_reason,
    }

    # G8: reorderings, local relabellings, class relabellings, and their
    # composition. Every carried witness is checked as a real semantic audit.
    invariant_checks = 0
    carried_checks = 0
    invariant_failures = []
    carried_failures = []
    distinct_keys = []
    for seed in range(20):
        base = make_instance(seed=70_000 + seed, **shipping)
        base_key = canonical_key(base)
        distinct_keys.append(base_key)
        rr = random.Random(80_000 + seed)
        class_perm = list(range(base["n"]))
        rr.shuffle(class_perm)
        local_perms = []
        for _ in range(base["n"]):
            perm = list(range(base["part_size"]))
            rr.shuffle(perm)
            local_perms.append(perm)
        identity_classes = list(range(base["n"]))
        identity_locals = [list(range(base["part_size"])) for _ in range(base["n"])]
        variants = {
            "pair_reorder": _relabel_instance(base, identity_classes,
                                                identity_locals, reorder=True),
            "local_labels": _relabel_instance(base, identity_classes,
                                                local_perms, reorder=False),
            "class_labels": _relabel_instance(base, class_perm,
                                                identity_locals, reorder=False),
            "composed": _relabel_instance(base, class_perm,
                                            local_perms, reorder=True),
        }
        for name, variant in variants.items():
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                invariant_failures.append({"seed": seed, "transform": name})
            carried_checks += 1
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                carried_failures.append({"seed": seed, "transform": name,
                                         "reason": reason})
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (not invariant_failures and not carried_failures
                 and distinct_count == len(distinct_keys)),
        "invariance_passed": invariant_checks - len(invariant_failures),
        "invariance_total": invariant_checks,
        "carried_witness_passed": carried_checks - len(carried_failures),
        "carried_witness_total": carried_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_total": len(distinct_keys),
        "invariance_failures": invariant_failures,
        "carried_failures": carried_failures,
        "caveat": "strong invariant, not a complete isomorphism canonizer",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
