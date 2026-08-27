"""Problem generator for arXiv:1912.09051.

The paper proves NP-completeness for Connected Spanning Central Surface by
reducing Hamiltonian cycle in 3-regular graphs to a triangulation made from
three-port node gadgets.  This module uses that gadget-level encoding directly:
find the connected spanning central surface by giving the cyclic order in which
the selected gadget tubes connect all node gadgets.
"""

from __future__ import annotations

import math
import random
import re
from collections import deque


DIFFICULTY = {
    "easy": {"n": 40},
    "medium": {"n": 80},
    "hard": {"n": 120},
}

SHIPPING_DIFFICULTY = "medium"


def _norm_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _cycle_neighbors(n: int, u: int) -> set[int]:
    return {(u - 1) % n, (u + 1) % n}


def _random_allowed_matching(n: int, rng: random.Random) -> list[tuple[int, int]]:
    vertices = list(range(n))
    for _ in range(5000):
        remaining = vertices[:]
        rng.shuffle(remaining)
        pairs: list[tuple[int, int]] = []
        ok = True
        while remaining:
            u = remaining.pop()
            choices = [v for v in remaining if v not in _cycle_neighbors(n, u)]
            if not choices:
                ok = False
                break
            v = rng.choice(choices)
            remaining.remove(v)
            pairs.append(_norm_edge(u, v))
        if ok and len(set(pairs)) == n // 2:
            return pairs
    raise RuntimeError("could not build a non-cycle perfect matching")


def _build_adjacency(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Build a planted node-gadget instance.

    `n` is the number of node gadgets.  It is rounded up to the next even value,
    because every 3-regular graph has an even number of vertices.
    """

    del params
    if n < 8:
        n = 8
    if n % 2:
        n += 1
    rng = random.Random(seed)

    planted_edges = [_norm_edge(i, (i + 1) % n) for i in range(n)]
    matching_edges = _random_allowed_matching(n, rng)
    old_edges = planted_edges + matching_edges

    labels = list(range(n))
    rng.shuffle(labels)
    relabel = {old: labels[old] for old in range(n)}
    edges = sorted(_norm_edge(relabel[u], relabel[v]) for u, v in old_edges)
    adj = _build_adjacency(n, edges)

    port_of: dict[tuple[int, int], int] = {}
    for u in range(n):
        ports = [0, 1, 2]
        rng.shuffle(ports)
        for p, v in zip(ports, adj[u]):
            port_of[(u, v)] = p

    port_arcs = []
    for u, v in edges:
        port_arcs.append((u, port_of[(u, v)], v, port_of[(v, u)]))
    port_arcs.sort()

    answer = [relabel[i] for i in range(n)]
    return {
        "paper": "arXiv:1912.09051",
        "family": "connected spanning central surface node-gadget encoding",
        "n": n,
        "seed": seed,
        "port_arcs": port_arcs,
        "edges": edges,
        "adjacency": adj,
        "answer": answer,
    }


def render(inst) -> str:
    n = inst["n"]
    lines = [
        "Find a connected spanning central surface in this node-gadget gluing instance.",
        "",
        "Definitions.",
        f"There are {n} node gadgets, numbered 0 through {n - 1}.",
        "Each gadget has exactly three ports, numbered 0, 1, and 2. A port represents one boundary annulus of the node gadget.",
        "Each listed arc glues two ports together. Every port appears in exactly one arc.",
        "A tube choice at a gadget selects exactly two of its three ports.",
        "The selected tubes form a connected spanning central surface exactly when the selected arcs connect all gadgets in one single cycle.",
        "",
        "Your witness must be a cyclic order of all gadget numbers.",
        "The order is valid if every gadget appears exactly once and each consecutive pair in the order, including the last paired with the first, is joined by a listed arc.",
        "Rotations and reversal of the same cycle are accepted. Gadget numbers are 0-indexed. Repeats are not allowed.",
        "",
        "Port arcs, one per line, in the format node:port -- node:port:",
    ]
    for u, pu, v, pv in inst["port_arcs"]:
        lines.append(f"{u}:{pu} -- {v}:{pv}")
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags, as a comma-separated list of all gadget numbers in cyclic order.",
            "Example: <answer>3, 17, 42, 8</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    try:
        match = re.search(r"<answer>(.*?)</answer>", text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:[a-zA-Z0-9_-]+)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return []
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1]
        tokens = re.split(r"[\s,]+", body.strip())
        if any(tok == "" for tok in tokens):
            tokens = [tok for tok in tokens if tok]
        if not tokens:
            return []
        if not all(re.fullmatch(r"[+-]?\d+", tok) for tok in tokens):
            return None
        return [int(tok) for tok in tokens]
    except Exception:
        return None


def _edge_set(inst) -> set[tuple[int, int]]:
    return set(tuple(e) for e in inst["edges"])


def verify(inst, answer) -> tuple[bool, str]:
    n = inst["n"]
    if not isinstance(answer, list) or not all(isinstance(x, int) for x in answer):
        return False, "malformed: expected a list of integer gadget numbers"
    if len(answer) == 0:
        return False, "empty answer: expected a cyclic order using every gadget"
    if len(answer) != n:
        return False, f"wrong length: expected {n} gadgets, got {len(answer)}"
    for x in answer:
        if x < 0 or x >= n:
            return False, f"out of range: gadget {x} is not in 0..{n - 1}"
    seen = set()
    for x in answer:
        if x in seen:
            return False, f"duplicate gadget: {x} appears more than once"
        seen.add(x)

    edges = _edge_set(inst)
    for i, u in enumerate(answer):
        v = answer[(i + 1) % n]
        if _norm_edge(u, v) not in edges:
            return False, f"not an arc: consecutive gadgets {u} and {v} are not glued"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    return rng.sample(range(inst["n"]), inst["n"])


def search_space(inst) -> int | None:
    return math.factorial(inst["n"])


def enumerate_all(inst) -> int | None:
    n = inst["n"]
    if n > 12:
        return None
    adj = inst["adjacency"]
    count_from_zero = 0
    path = [0]
    used = {0}

    def dfs(u: int) -> None:
        nonlocal count_from_zero
        if len(path) == n:
            if 0 in adj[u]:
                count_from_zero += 1
            return
        for v in adj[u]:
            if v not in used:
                used.add(v)
                path.append(v)
                dfs(v)
                path.pop()
                used.remove(v)

    dfs(0)
    return count_from_zero * n


def _candidate_from_selected_edges(n: int, selected: set[tuple[int, int]]) -> list[int] | None:
    if len(selected) != n:
        return None
    adj = [[] for _ in range(n)]
    for u, v in selected:
        adj[u].append(v)
        adj[v].append(u)
    if any(len(row) != 2 for row in adj):
        return None
    out = [0]
    prev = None
    cur = 0
    for _ in range(n - 1):
        nxts = [v for v in adj[cur] if v != prev]
        if not nxts:
            return None
        nxt = nxts[0]
        if nxt in out:
            return None
        out.append(nxt)
        prev, cur = cur, nxt
    if 0 not in adj[cur]:
        return None
    return out


def _attack_nearest_labels(inst) -> object | None:
    n = inst["n"]
    selected = set()
    for u, row in enumerate(inst["adjacency"]):
        chosen = sorted(row, key=lambda v: (abs(v - u), v))[:2]
        for v in chosen:
            selected.add(_norm_edge(u, v))
    return _candidate_from_selected_edges(n, selected)


def _attack_ports_01(inst) -> object | None:
    selected = set()
    for u, pu, v, pv in inst["port_arcs"]:
        if pu in (0, 1) and pv in (0, 1):
            selected.add(_norm_edge(u, v))
    return _candidate_from_selected_edges(inst["n"], selected)


def _attack_greedy(inst) -> object | None:
    n = inst["n"]
    adj = inst["adjacency"]
    for start in range(n):
        path = [start]
        used = {start}
        cur = start
        while len(path) < n:
            choices = [v for v in adj[cur] if v not in used]
            if not choices:
                break
            choices.sort(key=lambda v: (sum(1 for w in adj[v] if w not in used), v))
            cur = choices[0]
            used.add(cur)
            path.append(cur)
        if len(path) == n and start in adj[path[-1]]:
            return path
    return None


def _attack_random_restart(inst, rng: random.Random, restarts: int = 500) -> object | None:
    n = inst["n"]
    adj = inst["adjacency"]
    for _ in range(restarts):
        start = rng.randrange(n)
        path = [start]
        used = {start}
        cur = start
        while len(path) < n:
            choices = [v for v in adj[cur] if v not in used]
            if not choices:
                break
            weights = []
            for v in choices:
                onward = sum(1 for w in adj[v] if w not in used or w == start)
                weights.append(max(1, onward))
            total = sum(weights)
            pick = rng.randrange(total)
            acc = 0
            nxt = choices[-1]
            for v, w in zip(choices, weights):
                acc += w
                if pick < acc:
                    nxt = v
                    break
            cur = nxt
            used.add(cur)
            path.append(cur)
        if len(path) == n and start in adj[path[-1]]:
            return path
    return None


def _corruption_results(inst) -> dict:
    answer = list(inst["answer"])
    out: dict[str, str] = {}
    corruptions: dict[str, object] = {
        "drop_one": answer[:-1],
        "duplicate": [answer[1]] + answer[1:],
        "empty": [],
        "out_of_range": [inst["n"]] + answer[1:],
    }
    swapped = None
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            cand = answer[:]
            cand[i], cand[j] = cand[j], cand[i]
            if not verify(inst, cand)[0]:
                swapped = cand
                break
        if swapped is not None:
            break
    corruptions["swap_two"] = swapped if swapped is not None else list(reversed(answer))
    for name, cand in corruptions.items():
        ok, reason = verify(inst, cand)
        out[name] = "ACCEPTED" if ok else reason
    return out


def _run_attack_panel(params: dict, seeds: list[int]) -> dict:
    attacks = {
        "outlier_nearest_labels": lambda inst, rng: _attack_nearest_labels(inst),
        "outlier_ports_01": lambda inst, rng: _attack_ports_01(inst),
        "greedy_low_onward_degree": lambda inst, rng: _attack_greedy(inst),
        "random_restart_500": lambda inst, rng: _attack_random_restart(inst, rng, 500),
    }
    results = {}
    for name, attack in attacks.items():
        solved = []
        for seed in seeds:
            inst = make_instance(seed=seed, **params)
            cand = attack(inst, random.Random(10_000 + seed))
            if cand is not None and verify(inst, cand)[0]:
                solved.append(seed)
        results[name] = {"solved": len(solved), "total": len(seeds), "solved_seeds": solved}
    return results


def selftest() -> dict:
    seeds = [0, 1, 2, 3]
    out: dict[str, object] = {}

    g1 = {}
    for name, params in DIFFICULTY.items():
        rows = []
        for seed in seeds:
            inst = make_instance(seed=seed, **params)
            rows.append(verify(inst, inst["answer"]))
        g1[name] = rows
    out["G1_planted_verifies"] = g1

    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12345, **ship)
    corr = _corruption_results(inst)
    out["G2_rejects_corruption"] = corr
    out["G2_pass"] = all(not reason.startswith("ACCEPTED") for reason in corr.values()) and len(set(corr.values())) == len(corr)

    prose = "I found the cycle.\n\n<answer>\n" + ", ".join(map(str, inst["answer"])) + "\n</answer>\n"
    parsed = parse_answer(prose)
    out["G3_round_trip"] = {"ok": parsed == inst["answer"], "parsed_length": None if parsed is None else len(parsed)}

    rng = random.Random(999)
    total = 200_000
    hits = 0
    for _ in range(total):
        if verify(inst, random_candidate(inst, rng))[0]:
            hits += 1
    out["G4_guess_resistance"] = {"hits": hits, "total": total, "p_hat": hits / total, "pass": hits / total < 1e-6}

    small = make_instance(10, seed=77)
    valid = enumerate_all(small)
    space = search_space(small)
    ratio = None if valid is None or space is None else valid / space
    out["G5_sparse"] = {"n": small["n"], "valid_answers": valid, "search_space": space, "ratio": ratio, "pass": ratio is not None and ratio < 1e-3}

    panel = _run_attack_panel(ship, list(range(8)))
    out["G6_adversary_panel"] = panel
    out["G6_pass"] = all(row["solved"] == 0 for row in panel.values())

    doubled = make_instance(seed=54321, n=ship["n"] * 2)
    out["G7_scales"] = {"n": doubled["n"], "planted": verify(doubled, doubled["answer"])}

    out["all_pass"] = (
        all(ok for rows in g1.values() for ok, _ in rows)
        and out["G2_pass"]
        and out["G3_round_trip"]["ok"]
        and out["G4_guess_resistance"]["pass"]
        and out["G5_sparse"]["pass"]
        and out["G6_pass"]
        and out["G7_scales"]["planted"][0]
    )
    return out
