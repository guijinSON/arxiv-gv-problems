"""Verified witness generator for arXiv:2401.06027.

The generated task is a compact certificate for a bounded Kempe-switching
sequence on a star.  It instantiates the standard reduction from Hamiltonian
Cycle in cubic graphs to Kempe Distance on stars.  A certificate is a cyclic
ordering of the non-buffer colors; the checker expands it to singleton Kempe
switchings followed by center-component switchings and replays that compressed
sequence exactly.

Only the Python standard library is used.  Generation is deterministic for
``(n, seed)`` and uses a private ``random.Random`` instance.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import deque


DIFFICULTY = {
    "demo": {"n": 4},
    "easy": {"n": 128},
    "medium": {"n": 160},
    "hard": {"n": 192},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Paper reading notes.  Section 1 of Ohsugi--Tsuchiya fixes the exact move: choose
one connected component of the subgraph induced by two colors, then exchange
those colors on that component.  Theorem 5.1 identifies Kempe equivalence with
membership in the 2-coloring ideal J_G.  Section 7, especially Procedures 1--3
and Algorithm 7.6, constructs an explicit switching sequence.  The paragraph
immediately before Algorithm 7.6 warns that enumerating all stable sets and
computing the Groebner basis is not computationally feasible for large graphs.
Proposition 6.11 records the important easy regime k >= Delta+1, where every
induced subgraph has one Kempe class.

The target paper does not itself prove a complexity lower bound.  Hardness for
the bounded witness used here comes from Bonamy et al., "Shortest
Reconfiguration of Colorings Under Kempe Changes", Theorem 12 and Lemmas
13--14: Kempe Distance is NP-complete even on stars.  Their reduction maps a
cubic Hamiltonian-cycle instance with m vertices to two colorings of a star,
using m+1 colors and K copies per directed edge for K>2m.  A sequence at the
stated bound exists exactly when the cubic graph has a Hamiltonian cycle.  Here
K=2m+1, so the number of colors grows; this avoids their FPT regime parameterized
by the number of colors.  The answer is not an optimum claim: it is a concrete
cycle certificate that expands to and exactly replays a sequence within the
given bound.

Inverse generation samples the public cyclic answer first, adds its cycle
edges, and then adds a random perfect matching.  Every public vertex has degree
three, and after random labels a planted edge has the same degree, endpoint-label
distribution, and input representation as a decoy edge.  The adversary panel
tests label-span and short-cycle outliers, deterministic low-onward-degree
greedy search, and 512 randomized greedy restarts.  The shipping size is above
the range where those attacks showed occasional successes.
"""


def _norm_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _cycle_edge_set(order: list[int]) -> set[tuple[int, int]]:
    return {
        _norm_edge(order[i], order[(i + 1) % len(order)])
        for i in range(len(order))
    }


def _random_disjoint_matching(
    vertices: list[int], forbidden: set[tuple[int, int]], rng: random.Random
) -> list[tuple[int, int]]:
    """Sample a perfect matching containing no forbidden edge."""

    for _ in range(20_000):
        shuffled = vertices[:]
        rng.shuffle(shuffled)
        pairs = [
            _norm_edge(shuffled[i], shuffled[i + 1])
            for i in range(0, len(shuffled), 2)
        ]
        if all(edge not in forbidden for edge in pairs):
            return pairs
    raise RuntimeError("could not sample a perfect matching disjoint from the cycle")


def _adjacency(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj = [[] for _ in range(n)]
    for raw_u, raw_v in edges:
        u, v = int(raw_u), int(raw_v)
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a certificate first, then build its cubic/star instance.

    ``n`` is the number of non-buffer colors (and vertices of the encoded cubic
    graph).  It is rounded up to an even integer at least 12.  The actual star is
    represented without listing its many symmetric leaves: for every directed
    cubic edge u->v there are K named leaves (u,v,r), 0 <= r < K.
    """

    if params:
        unknown = ", ".join(sorted(map(str, params)))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    n = max(12, n)
    if n % 2:
        n += 1

    rng = random.Random(seed)

    # G: sample the answer before any problem edges.
    answer = list(range(n))
    rng.shuffle(answer)
    planted_edges = _cycle_edge_set(answer)
    decoy_edges = _random_disjoint_matching(list(range(n)), planted_edges, rng)
    edges = list(planted_edges) + decoy_edges
    rng.shuffle(edges)  # input order carries no planting information

    if len(set(edges)) != 3 * n // 2:
        raise RuntimeError("internal error: cubic graph has duplicate edges")
    adj = _adjacency(n, edges)
    if any(len(row) != 3 for row in adj):
        raise RuntimeError("internal error: graph is not cubic")

    copies = 2 * n + 1
    leaf_count = 3 * copies * n
    move_bound = n * (2 * copies + 1) + 1
    return {
        "paper": "arXiv:2401.06027",
        "family": "bounded Kempe sequence on an implicitly represented star",
        "n": n,
        "seed": seed,
        "colors": n + 1,
        "buffer_color": n,
        "copies_per_directed_edge": copies,
        "leaf_count": leaf_count,
        "star_vertex_count": leaf_count + 1,
        "move_bound": move_bound,
        "edges": edges,
        "adjacency": adj,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete standalone problem statement."""

    n = inst["n"]
    copies = inst["copies_per_directed_edge"]
    buffer_color = inst["buffer_color"]
    edge_tokens = " ".join(
        f"{u}-{v}" for u, v in sorted(_norm_edge(*edge) for edge in inst["edges"])
    )
    return "\n".join(
        [
            "Compressed bounded Kempe-switching certificate",
            "",
            "A proper k-coloring assigns one integer color to every graph vertex,",
            "with different colors at the ends of every edge.  A Kempe switching",
            "chooses two distinct colors, takes the connected components of the",
            "subgraph induced by vertices currently having either color, chooses",
            "exactly one such component, and exchanges the two colors on every",
            "vertex of that component.",
            "",
            f"This instance uses colors 0 through {buffer_color} inclusive.",
            f"Colors 0 through {n - 1} are ordinary; {buffer_color} is a buffer.",
            "The graph being recolored is a star: one center is adjacent to every",
            "leaf, and there are no leaf-leaf edges.  The center has the buffer",
            "color in both the source and target colorings.",
            "",
            "The leaves are specified compactly by the undirected cubic graph below.",
            f"For each listed edge u-v and each r with 0 <= r < {copies}, there are",
            "two distinct star leaves L(u,v,r) and L(v,u,r).  Leaf L(u,v,r) has",
            "source color u and target color v.  Thus all leaf names, source colors,",
            "target colors, and star edges are fully determined by this rule.",
            f"There are {inst['leaf_count']} leaves and {inst['star_vertex_count']} star vertices.",
            "The compact graph vertices/colors are 0-indexed.  Edges are undirected.",
            f"Cubic edges ({len(inst['edges'])} total):",
            edge_tokens,
            "",
            "Your witness is a compressed Kempe sequence: give exactly one cyclic",
            f"ordering h0,...,h{n - 1} of all ordinary colors.  Every integer 0 through",
            f"{n - 1} must occur exactly once; do not repeat h0 at the end.  Rotation",
            "and reversal are both allowed.  The ordering expands deterministically:",
            "",
            "1. Define pred(h[(i+1) mod n]) = h[i].  Visit leaves in increasing",
            "   lexicographic order (u,v,r).  If a leaf L(u,v,r) currently has color",
            "   u != pred(v), switch the singleton component containing that leaf",
            "   using colors u and pred(v).",
            "2. Starting with the center still at the buffer color, switch the",
            "   component containing the center successively with the named colors",
            "   h[n-1], h[n-2], ..., h[0], and finally the buffer color.",
            "",
            f"The expanded sequence must use at most {inst['move_bound']} Kempe switchings",
            "and must finish at the target coloring.  Equivalently, every consecutive",
            "pair in your cyclic ordering, including the last paired with the first,",
            "must be one of the listed cubic edges.",
            "",
            "Give your final answer inside <answer></answer> tags, as exactly the",
            f"{n} comma-separated ordinary colors in cyclic order.",
            "Example: <answer>3, 17, 42, 8</answer>",
            "Output nothing else inside the tags.",
        ]
    )


def parse_answer(text: str) -> object | None:
    """Parse the last tagged integer list, tolerating prose and Markdown fences."""

    try:
        if not isinstance(text, str):
            return None
        matches = re.findall(
            r"<answer\b[^>]*>(.*?)</answer\s*>", text, flags=re.IGNORECASE | re.DOTALL
        )
        if not matches:
            return None
        body = matches[-1].strip()
        body = re.sub(r"^```(?:[A-Za-z0-9_+.-]+)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        if not re.fullmatch(r"[+-]?\d+(?:\s*(?:,|\s)\s*[+-]?\d+)*\s*", body):
            return None
        tokens = [tok for tok in re.split(r"[\s,]+", body) if tok]
        return [int(tok) for tok in tokens]
    except Exception:
        return None


def _replay_compressed(inst: dict, cycle: list[int]) -> tuple[bool, str, int]:
    """Symbolically replay every expanded star move, grouped by identical leaves."""

    n = inst["n"]
    copies = inst["copies_per_directed_edge"]
    buffer_color = inst["buffer_color"]
    adj = inst.get("adjacency") or _adjacency(n, inst["edges"])

    predecessor = [None] * n
    for i, color in enumerate(cycle):
        predecessor[cycle[(i + 1) % n]] = color

    # Phase 1 consists of singleton components because the center's buffer color
    # is absent from every chosen pair.  Count and apply all K identical leaves
    # in each directed-edge group.  target_class_color[v] is the common color of
    # all 3K leaves whose target color is v after this phase.
    phase1_moves = 0
    target_class_color: list[int | None] = [None] * n
    for v in range(n):
        pred = predecessor[v]
        if pred is None:
            return False, "internal replay error: predecessor is undefined", 0
        colors_after = []
        for u in adj[v]:
            if u == pred:
                colors_after.append(u)
            else:
                # K actual singleton switches u <-> pred are represented here.
                phase1_moves += copies
                colors_after.append(pred)
        if any(color != pred for color in colors_after):
            return False, f"expanded leaf phase does not unify target class {v}", phase1_moves
        target_class_color[v] = pred

    # Phase 2 exactly replays the center component.  At this point each ordinary
    # color occurs on exactly one entire target class when the certificate is a
    # permutation; the buffer occurs only at the center.
    center_color = buffer_color
    center_sequence = list(reversed(cycle)) + [buffer_color]
    phase2_moves = 0
    for named_color in center_sequence:
        if named_color == center_color:
            return False, "expanded center phase asks for two identical colors", phase1_moves + phase2_moves
        carrying = [
            target for target, color in enumerate(target_class_color)
            if color == named_color
        ]
        if len(carrying) != 1:
            return (
                False,
                f"expanded center component sees {len(carrying)} target classes of color {named_color}",
                phase1_moves + phase2_moves,
            )
        target = carrying[0]
        target_class_color[target] = center_color
        center_color = named_color
        phase2_moves += 1

    moves = phase1_moves + phase2_moves
    if center_color != buffer_color:
        return False, "expanded sequence leaves the center at the wrong color", moves
    if target_class_color != list(range(n)):
        return False, "expanded sequence does not reach the target leaf coloring", moves
    if moves > inst["move_bound"]:
        return False, f"expanded sequence uses {moves} moves, above bound {inst['move_bound']}", moves
    return True, "ok", moves


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept any certificate whose exact expansion is a short valid sequence."""

    n = inst["n"]
    if not isinstance(answer, list) or not all(
        isinstance(x, int) and not isinstance(x, bool) for x in answer
    ):
        return False, "malformed: expected a list of integer colors"
    if not answer:
        return False, f"empty answer: expected {n} ordinary colors"
    if len(answer) != n:
        return False, f"wrong length: expected {n} colors, got {len(answer)}"
    for color in answer:
        if color < 0 or color >= n:
            return False, f"out of range: color {color} is not in 0..{n - 1}"
    seen: set[int] = set()
    for color in answer:
        if color in seen:
            return False, f"duplicate color: {color} appears more than once"
        seen.add(color)

    edges = {_norm_edge(*edge) for edge in inst["edges"]}
    for i, u in enumerate(answer):
        v = answer[(i + 1) % n]
        if _norm_edge(u, v) not in edges:
            return False, f"missing transition: cyclic pair {u}-{v} is not a cubic edge"

    ok, reason, _moves = _replay_compressed(inst, answer)
    return ok, reason


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-implied permutation space."""

    return rng.sample(range(inst["n"]), inst["n"])


def search_space(inst: dict) -> int | None:
    """Number of length-n lists that satisfy range and all-different rules."""

    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count all accepted labeled lists exactly for small graphs.

    The DFS fixes color 0 first and multiplies by n for all rotations.  Its two
    traversal directions remain distinct, matching ``search_space``.  A visit
    cap prevents accidental exponential hangs.
    """

    n = inst["n"]
    if n > 14:
        return None
    adj = inst.get("adjacency") or _adjacency(n, inst["edges"])
    used = [False] * n
    used[0] = True
    visits = 0
    rooted_oriented = 0
    cap = 2_000_000

    def dfs(vertex: int, depth: int) -> None:
        nonlocal visits, rooted_oriented
        visits += 1
        if visits > cap:
            raise OverflowError
        if depth == n:
            if 0 in adj[vertex]:
                rooted_oriented += 1
            return
        for nxt in adj[vertex]:
            if not used[nxt]:
                used[nxt] = True
                dfs(nxt, depth + 1)
                used[nxt] = False

    try:
        dfs(0, 1)
    except OverflowError:
        return None
    return rooted_oriented * n


def _root_profile(n: int, edges: list[tuple[int, int]], adj: list[list[int]], root: int) -> tuple:
    distances = [-1] * n
    distances[root] = 0
    queue = deque([root])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if distances[v] < 0:
                distances[v] = distances[u] + 1
                queue.append(v)
    max_distance = max(distances)
    profile = []
    for level in range(max_distance + 1):
        vertices = sum(distance == level for distance in distances)
        within = 0
        forward = 0
        for u, v in edges:
            du, dv = distances[u], distances[v]
            if du == level and dv == level:
                within += 1
            elif (du == level and dv == level + 1) or (dv == level and du == level + 1):
                forward += 1
        profile.append((vertices, within, forward))
    return tuple(profile)


def canonical_key(inst: dict) -> str:
    """Return a relabeling-invariant structural fingerprint of the cubic graph.

    Exact canonical labeling of an arbitrary graph is deliberately not claimed.
    The fingerprint is the sorted multiset of rooted BFS layer profiles, enhanced
    with within-layer and next-layer edge counts.  It ignores the seed, the
    planted answer, edge order/orientation, and public vertex names.
    """

    n = inst["n"]
    edges = sorted({_norm_edge(*edge) for edge in inst["edges"]})
    adj = _adjacency(n, edges)
    profiles = sorted(_root_profile(n, edges, adj, root) for root in range(n))
    payload = json.dumps([n, profiles], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the encoded cubic graph while preserving guaranteed feasibility."""

    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    return {"n": n + 64}


def _candidate_from_edges(n: int, selected: set[tuple[int, int]]) -> list[int] | None:
    if len(selected) != n:
        return None
    adj = [[] for _ in range(n)]
    for u, v in selected:
        adj[u].append(v)
        adj[v].append(u)
    if any(len(row) != 2 for row in adj):
        return None
    order = [0]
    previous = -1
    current = 0
    for _ in range(n - 1):
        choices = [v for v in adj[current] if v != previous]
        if not choices:
            return None
        nxt = choices[0]
        if nxt in order:
            return None
        order.append(nxt)
        previous, current = current, nxt
    if 0 not in adj[current]:
        return None
    return order


def _ranked_path_attack(inst: dict, edge_score, reverse: bool = False) -> list[int] | None:
    n = inst["n"]
    adj = inst["adjacency"]
    for start in range(n):
        for first in adj[start]:
            path = [start, first]
            used = {start, first}
            while len(path) < n:
                current = path[-1]
                choices = [v for v in adj[current] if v not in used]
                if not choices:
                    break
                choices.sort(
                    key=lambda v: (edge_score(current, v), v), reverse=reverse
                )
                nxt = choices[0]
                path.append(nxt)
                used.add(nxt)
            if len(path) == n and start in adj[path[-1]]:
                return path
    return None


def _attack_label_span(inst: dict) -> list[int] | None:
    return _ranked_path_attack(inst, lambda u, v: abs(u - v))


def _short_cycle_scores(inst: dict) -> dict[tuple[int, int], int]:
    adj = inst["adjacency"]
    scores: dict[tuple[int, int], int] = {}
    for raw_edge in inst["edges"]:
        edge = _norm_edge(*raw_edge)
        start, goal = edge
        count = 0
        stack = [(start, (start,), 0)]
        while stack:
            vertex, path, depth = stack.pop()
            if depth >= 5:
                continue
            for nxt in adj[vertex]:
                if _norm_edge(vertex, nxt) == edge:
                    continue
                if nxt == goal and depth + 1 >= 2:
                    count += 1
                elif nxt not in path and nxt != goal:
                    stack.append((nxt, path + (nxt,), depth + 1))
        scores[edge] = count
    return scores


def _attack_short_cycle_outlier(inst: dict) -> list[int] | None:
    scores = _short_cycle_scores(inst)
    for reverse in (False, True):
        candidate = _ranked_path_attack(
            inst, lambda u, v: scores[_norm_edge(u, v)], reverse=reverse
        )
        if candidate is not None:
            return candidate
    return None


def _attack_low_onward_greedy(inst: dict) -> list[int] | None:
    n = inst["n"]
    adj = inst["adjacency"]
    for start in range(n):
        for first in adj[start]:
            path = [start, first]
            used = {start, first}
            while len(path) < n:
                current = path[-1]
                choices = [v for v in adj[current] if v not in used]
                if not choices:
                    break
                choices.sort(
                    key=lambda v: (
                        sum(w not in used or w == start for w in adj[v]),
                        v,
                    )
                )
                nxt = choices[0]
                path.append(nxt)
                used.add(nxt)
            if len(path) == n and start in adj[path[-1]]:
                return path
    return None


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 512
) -> list[int] | None:
    n = inst["n"]
    adj = inst["adjacency"]
    for _ in range(restarts):
        start = rng.randrange(n)
        path = [start]
        used = {start}
        while len(path) < n:
            choices = [v for v in adj[path[-1]] if v not in used]
            if not choices:
                break
            onward = [sum(w not in used or w == start for w in adj[v]) for v in choices]
            weights = [4 ** (3 - min(3, value)) for value in onward]
            pick = rng.randrange(sum(weights))
            upto = 0
            nxt = choices[-1]
            for candidate, weight in zip(choices, weights):
                upto += weight
                if pick < upto:
                    nxt = candidate
                    break
            path.append(nxt)
            used.add(nxt)
        if len(path) == n and start in adj[path[-1]]:
            return path
    return None


def _corruptions(inst: dict) -> dict[str, object]:
    answer = list(inst["answer"])
    swapped = None
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            candidate = answer[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if not verify(inst, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    if swapped is None:
        raise RuntimeError("could not construct a rejected swap corruption")
    return {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": [inst["n"]] + answer[1:],
    }


def _relabel_instance(inst: dict, permutation: list[int]) -> dict:
    n = inst["n"]
    transformed = dict(inst)
    transformed["edges"] = [
        _norm_edge(permutation[u], permutation[v]) for u, v in inst["edges"]
    ]
    transformed["adjacency"] = _adjacency(n, transformed["edges"])
    transformed["answer"] = [permutation[color] for color in inst["answer"]]
    return transformed


def _reorder_instance(inst: dict, rng: random.Random) -> dict:
    transformed = dict(inst)
    edges = list(inst["edges"])
    rng.shuffle(edges)
    edges = [(v, u) if rng.randrange(2) else (u, v) for u, v in edges]
    transformed["edges"] = edges
    transformed["adjacency"] = _adjacency(inst["n"], edges)
    return transformed


def selftest() -> dict:
    """Run mandatory gates and return their machine-readable measurements."""

    report: dict[str, object] = {}

    # G1: every preset, several seeds.
    g1_rows = {}
    g1_ok = True
    for preset, params in DIFFICULTY.items():
        rows = []
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            rows.append({"seed": seed, "ok": ok, "reason": reason})
            g1_ok = g1_ok and ok
        g1_rows[preset] = rows
    report["G1_planted_verifies"] = {
        "pass": g1_ok,
        "verified": sum(row["ok"] for rows in g1_rows.values() for row in rows),
        "total": sum(len(rows) for rows in g1_rows.values()),
        "by_preset": g1_rows,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12_345, **shipping)

    # G2: five required corruptions with distinct diagnostic categories.
    corruption_rows = {}
    reasons = []
    for name, candidate in _corruptions(inst).items():
        ok, reason = verify(inst, candidate)
        corruption_rows[name] = {"accepted": ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "rejected": sum(not row["accepted"] for row in corruption_rows.values()),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_rows,
    }

    # G3: prose outside tags and a Markdown fence inside them.
    realistic = (
        "I used the color-class permutation to build the Kempe sequence.\n\n"
        "<answer>\n```text\n"
        + ", ".join(map(str, inst["answer"]))
        + "\n```\n</answer>\nThe checker can replay it."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "prose_and_fence": True,
    }

    # G4: permutations already satisfy type, range, length, and all-different.
    guess_rng = random.Random(99_991)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "p_hat": guess_rate,
        "prior": "uniform over all permutations of the ordinary colors",
        "naive_space": search_space(inst),
    }

    # G5: exact counts where enumeration remains safe.
    sparse_rows = []
    sparse_ok = True
    for seed in (3, 7, 11):
        small = make_instance(n=12, seed=seed)
        answers = enumerate_all(small)
        space = search_space(small)
        ratio = None if answers is None or space is None else answers / space
        sparse_rows.append(
            {
                "seed": seed,
                "n": small["n"],
                "valid_answers": answers,
                "search_space": space,
                "ratio": ratio,
            }
        )
        sparse_ok = sparse_ok and ratio is not None and ratio < 1e-6
    report["G5_sparse"] = {
        "pass": sparse_ok,
        "instances": sparse_rows,
        "threshold": 1e-6,
    }

    # G6: attacks tailored to labels, local edge statistics, and path greediness.
    attack_seeds = list(range(800, 808))
    attacks = {
        "outlier_label_span": lambda item, rng: _attack_label_span(item),
        "outlier_short_cycle_count": lambda item, rng: _attack_short_cycle_outlier(item),
        "greedy_low_onward_degree": lambda item, rng: _attack_low_onward_greedy(item),
        "random_restart_512": lambda item, rng: _attack_random_restart(item, rng, 512),
    }
    attack_rows = {}
    for name, attack in attacks.items():
        solved_seeds = []
        for seed in attack_seeds:
            attack_inst = make_instance(seed=seed, **shipping)
            candidate = attack(attack_inst, random.Random(500_000 + seed))
            if candidate is not None and verify(attack_inst, candidate)[0]:
                solved_seeds.append(seed)
        attack_rows[name] = {
            "solved": len(solved_seeds),
            "total": len(attack_seeds),
            "solved_seeds": solved_seeds,
        }
    report["G6_adversary_panel"] = {
        "pass": all(row["solved"] == 0 for row in attack_rows.values()),
        "shipping_params": dict(shipping),
        "attacks": attack_rows,
    }

    # G7: doubled n builds, remains cubic, and its planted sequence verifies.
    doubled = make_instance(n=shipping["n"] * 2, seed=54_321)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"],
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "star_vertices": doubled["star_vertex_count"],
        "verify_ok": doubled_ok,
        "verify_reason": doubled_reason,
    }

    # G8: input reordering/orientation, arbitrary relabeling, and compositions.
    invariance_checks = 0
    carried_answer_checks = 0
    invariant_ok = True
    carried_ok = True
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=20_000 + seed, **shipping)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        transform_rng = random.Random(70_000 + seed)
        permutation = list(range(base["n"]))
        transform_rng.shuffle(permutation)
        reordered = _reorder_instance(base, transform_rng)
        relabeled = _relabel_instance(base, permutation)
        composed = _reorder_instance(relabeled, transform_rng)
        for transformed in (reordered, relabeled, composed):
            invariance_checks += 1
            invariant_ok = invariant_ok and canonical_key(transformed) == base_key
            carried_answer_checks += 1
            transformed_ok, _ = verify(transformed, transformed["answer"])
            carried_ok = carried_ok and transformed_ok
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok and carried_ok and distinct == len(unrelated_keys),
        "invariance_checks_passed": invariance_checks if invariant_ok else None,
        "invariance_checks_total": invariance_checks,
        "carried_answer_checks_passed": carried_answer_checks if carried_ok else None,
        "carried_answer_checks_total": carried_answer_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": len(unrelated_keys),
        "transformations": ["edge reorder/orientation", "vertex/color relabel", "composition"],
        "key_kind": "rooted BFS layer/edge-profile multiset (strong invariant, not exact GI canonization)",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
