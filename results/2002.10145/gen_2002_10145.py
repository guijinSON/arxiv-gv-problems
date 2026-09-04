"""Verified inverse generator for fixed 4-colouring witness problems.

The family is the fixed-C graph-colouring problem defined in Section 2 of
arXiv:2002.10145 and used as the ETH-hard source problem in Section 4.  Every
generated graph is sampled around a colouring chosen before any non-anchor
edge is drawn.

This module uses only the Python standard library, performs no I/O, and prints
nothing when imported.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter


COLOURS = 4
ENUMERATION_CAP = 1_500_000

DIFFICULTY = {
    "demo": {
        "n": 10,
        "avg_degree": 3.0,
        "attack_restarts": 0,
        "backtrack_floor": 0,
        "filter_attacks": False,
    },
    "easy": {
        "n": 140,
        "avg_degree": 9.0,
        "attack_restarts": 32,
        "backtrack_floor": 10_000,
    },
    "medium": {
        "n": 160,
        "avg_degree": 9.0,
        "attack_restarts": 48,
        "backtrack_floor": 30_000,
    },
    "hard": {
        "n": 180,
        "avg_degree": 9.0,
        "attack_restarts": 64,
        "backtrack_floor": 60_000,
    },
}

# harden.py held this named rung against three distinct vendors.
SHIPPING_DIFFICULTY = "easy"

NOTES = """
Definition: Section 2 (Preliminaries, 'C-Coloring') defines a C-colouring as a
map V -> [1..C] whose endpoints differ on every edge.  The same section states
that every fixed C >= 3 is NP-complete and, under ETH, has no
2^o(|V|+|E|)-time algorithm.  Section 4, especially Theorem 15 and Lemma 18,
uses exactly that regime as the source for the paper's equation reductions.

Easy regimes avoided: C=1 and C=2 are elementary (2-colouring is bipartite
testing), so C is fixed at 4 and n grows.  For the paper's headline group
problem, the Introduction records polynomial algorithms for nilpotent groups
and several Fitting-length-two groups; a naive balanced random group word also
leaves about 1/|G| of assignments valid.  This generator therefore instantiates
the explicitly defined hard colouring source family rather than claiming that
such random words inherit Theorem 20's worst-case hardness.

Planting and attacks: a balanced colouring is sampled first.  Apart from the
four stated symmetry-breaking clique edges, every edge is selected uniformly
without replacement from all pairs separated by the plant.  Candidate graphs
are rejected if a degree-statistic outlier guess, deterministic DSATUR greedy,
randomised DSATUR restarts, or bounded exact DSATUR backtracking finds any valid
colouring.  Difficulty comes from the near-threshold density, increasing n,
and an increasing backtracking floor, not from a different decoy distribution.
""".strip()


def _normalise_edges(edges):
    return sorted((u, v) if u < v else (v, u) for u, v in edges)


def _adjacency(inst):
    n = inst["n"]
    adj = [set() for _ in range(n)]
    for u, v in inst["edges"]:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _is_connected(adj):
    if not adj:
        return False
    seen = {0}
    todo = [0]
    while todo:
        v = todo.pop()
        for w in adj[v]:
            if w not in seen:
                seen.add(w)
                todo.append(w)
    return len(seen) == len(adj)


def _anchors(inst):
    return {int(v): int(c) for v, c in inst["anchors"]}


def verify(inst, answer):
    """Check any proper colouring; this function never consults the plant."""
    n = inst["n"]
    q = inst["colours"]
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of colours"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"too few colours: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"too many colours: expected {n}, got {len(answer)}"
    for v, colour in enumerate(answer):
        if type(colour) is not int:
            return False, f"colour at vertex {v} is not an integer"
        if not 1 <= colour <= q:
            return False, f"colour at vertex {v} is outside 1..{q}"
    for v, colour in sorted(_anchors(inst).items()):
        if answer[v] != colour:
            return False, f"symmetry anchor requires vertex {v} to have colour {colour}"
    for u, v in inst["edges"]:
        if answer[u] == answer[v]:
            return False, f"edge ({min(u, v)}, {max(u, v)}) has equal endpoint colours"
    return True, "ok"


def _degree_outlier_attack(inst):
    """Try to read the hidden classes from per-vertex degree statistics."""
    n = inst["n"]
    q = inst["colours"]
    adj = _adjacency(inst)
    fixed = _anchors(inst)
    answer = [None] * n
    for v, colour in fixed.items():
        answer[v] = colour

    # Degree, neighbour-degree sum and local triangle count are all cheap
    # per-vertex statistics that could reveal a poorly planted class.
    features = []
    for v in range(n):
        if v in fixed:
            continue
        neighbour_degree_sum = sum(len(adj[w]) for w in adj[v])
        triangles = sum(1 for w in adj[v] for x in adj[v] if w < x and x in adj[w])
        features.append(((len(adj[v]), neighbour_degree_sum, triangles, v), v))
    features.sort()

    # Round-robin ranks create balanced guessed classes, matching the only
    # obvious marginal property of the hidden construction.
    counts = Counter(fixed.values())
    for _, v in features:
        colour = min(range(1, q + 1), key=lambda c: (counts[c], c))
        answer[v] = colour
        counts[colour] += 1
    return answer


def _dsatur_greedy(inst, rng=None):
    """One-pass DSATUR; random tie/colour choices if rng is supplied."""
    n = inst["n"]
    q = inst["colours"]
    adj = _adjacency(inst)
    answer = [0] * n
    fixed = _anchors(inst)
    for v, colour in fixed.items():
        answer[v] = colour

    for _ in range(n - len(fixed)):
        uncoloured = [v for v in range(n) if answer[v] == 0]
        best_score = max(
            (len({answer[w] for w in adj[v] if answer[w]}), len(adj[v]))
            for v in uncoloured
        )
        tied = [
            v
            for v in uncoloured
            if (len({answer[w] for w in adj[v] if answer[w]}), len(adj[v]))
            == best_score
        ]
        v = rng.choice(tied) if rng is not None else min(tied)
        available = [
            colour
            for colour in range(1, q + 1)
            if all(answer[w] != colour for w in adj[v])
        ]
        if not available:
            return None
        answer[v] = rng.choice(available) if rng is not None else available[0]
    return answer


def _attack_rng(inst, label):
    payload = {
        "label": label,
        "n": inst["n"],
        "colours": inst["colours"],
        "anchors": sorted(map(tuple, inst["anchors"])),
        "edges": _normalise_edges(inst["edges"]),
    }
    digest = hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def _random_restart_attack(inst, restarts):
    rng = _attack_rng(inst, "random-dsatur-restarts")
    for _ in range(restarts):
        answer = _dsatur_greedy(inst, rng)
        if answer is not None and verify(inst, answer)[0]:
            return answer
    return None


def _bounded_backtracking_attack(inst, node_limit):
    """Exact DSATUR until node_limit; return (answer, nodes, completed)."""
    n = inst["n"]
    q = inst["colours"]
    full = (1 << q) - 1
    fixed = _anchors(inst)
    adj_sets = _adjacency(inst)
    adj_bits = [0] * n
    degrees = [0] * n
    for v in range(n):
        mask = 0
        for w in adj_sets[v]:
            mask |= 1 << w
        adj_bits[v] = mask
        degrees[v] = len(adj_sets[v])

    answer = [0] * n
    fixed_mask = 0
    for v, colour in fixed.items():
        answer[v] = colour
        fixed_mask |= 1 << v
    uncoloured = ((1 << n) - 1) ^ fixed_mask
    saturation = [0] * n
    for v in range(n):
        if answer[v]:
            continue
        mask = adj_bits[v] & fixed_mask
        used = 0
        while mask:
            bit = mask & -mask
            w = bit.bit_length() - 1
            used |= 1 << (answer[w] - 1)
            mask -= bit
        saturation[v] = used

    nodes = 0

    class LimitReached(Exception):
        pass

    def visit(remaining):
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            raise LimitReached
        if remaining == 0:
            return True

        scan = remaining
        chosen = -1
        chosen_score = (-1, -1, 0)
        while scan:
            bit = scan & -scan
            v = bit.bit_length() - 1
            score = (saturation[v].bit_count(), degrees[v], -v)
            if score > chosen_score:
                chosen = v
                chosen_score = score
            scan -= bit

        available = full & ~saturation[chosen]
        options = []
        while available:
            colour_bit = available & -available
            colour = colour_bit.bit_length()
            affected = 0
            scan = adj_bits[chosen] & remaining
            while scan:
                bit = scan & -scan
                w = bit.bit_length() - 1
                if not saturation[w] & colour_bit:
                    affected += 1
                scan -= bit
            options.append((affected, colour, colour_bit))
            available -= colour_bit

        for _, colour, colour_bit in sorted(options):
            answer[chosen] = colour
            changed = []
            dead = False
            scan = adj_bits[chosen] & remaining
            while scan:
                bit = scan & -scan
                w = bit.bit_length() - 1
                old = saturation[w]
                if not old & colour_bit:
                    saturation[w] = old | colour_bit
                    changed.append((w, old))
                    if saturation[w] == full:
                        dead = True
                scan -= bit
            if not dead and visit(remaining ^ (1 << chosen)):
                return True
            for w, old in changed:
                saturation[w] = old
            answer[chosen] = 0
        return False

    try:
        solved = visit(uncoloured)
    except LimitReached:
        return None, nodes, False
    return (answer[:] if solved else None), nodes, True


def _attacks_fail(inst, attack_restarts, backtrack_floor):
    outlier = _degree_outlier_attack(inst)
    if verify(inst, outlier)[0]:
        return False
    greedy = _dsatur_greedy(inst)
    if greedy is not None and verify(inst, greedy)[0]:
        return False
    restarted = _random_restart_attack(inst, attack_restarts)
    if restarted is not None:
        return False
    if backtrack_floor > 0:
        exact, _, _ = _bounded_backtracking_attack(inst, backtrack_floor)
        if exact is not None and verify(inst, exact)[0]:
            return False
    return True


def make_instance(
    n,
    seed=0,
    avg_degree=9.0,
    attack_restarts=32,
    backtrack_floor=10_000,
    filter_attacks=True,
    max_tries=512,
):
    """Sample a colouring first, then draw a graph separated by that plant."""
    if type(n) is not int or n < 8:
        raise ValueError("n must be an integer at least 8")
    if not (0 < avg_degree < n):
        raise ValueError("avg_degree must be strictly between 0 and n")
    if type(attack_restarts) is not int or attack_restarts < 0:
        raise ValueError("attack_restarts must be a nonnegative integer")
    if type(backtrack_floor) is not int or backtrack_floor < 0:
        raise ValueError("backtrack_floor must be a nonnegative integer")

    rng = random.Random(seed)
    q = COLOURS
    forced = {(u, v) for u in range(q) for v in range(u + 1, q)}

    for attempt in range(1, max_tries + 1):
        # G: the complete witness is sampled before the edge set.
        tail = [1 + (i % q) for i in range(n - q)]
        rng.shuffle(tail)
        planted = list(range(1, q + 1)) + tail

        eligible = [
            (u, v)
            for u in range(n)
            for v in range(u + 1, n)
            if planted[u] != planted[v] and (u, v) not in forced
        ]
        target_edges = int(round(avg_degree * n / 2.0))
        if target_edges < len(forced) or target_edges > len(eligible) + len(forced):
            raise ValueError("requested average degree is impossible at this n")
        edges = set(forced)
        edges.update(rng.sample(eligible, target_edges - len(forced)))

        # Input order is intentionally noncanonical; canonical_key must remove it.
        edge_list = list(edges)
        rng.shuffle(edge_list)
        inst = {
            "family": "fixed-4-colouring",
            "n": n,
            "colours": q,
            "anchors": [[v, v + 1] for v in range(q)],
            "edges": edge_list,
            "answer": planted,
            "generation": {
                "avg_degree": float(avg_degree),
                "attack_restarts": attack_restarts,
                "backtrack_floor": backtrack_floor,
                "attempt": attempt,
            },
        }
        adj = _adjacency(inst)
        if min(map(len, adj)) < 2 or not _is_connected(adj):
            continue
        if filter_attacks and not _attacks_fail(inst, attack_restarts, backtrack_floor):
            continue
        return inst
    raise RuntimeError(
        f"could not sample an attack-resistant instance in {max_tries} attempts"
    )


def render(inst):
    """Render a self-contained fixed-colouring witness problem."""
    n = inst["n"]
    q = inst["colours"]
    edges = _normalise_edges(inst["edges"])
    anchors = sorted(map(tuple, inst["anchors"]))
    lines = [
        "FIXED 4-COLOURING WITNESS PROBLEM",
        "",
        f"The graph has {n} vertices, numbered 0 through {n - 1} inclusive.",
        "Each line in the edge list is one undirected edge 'u v'.",
        "There are no loops. Edge order and endpoint order have no meaning.",
        f"Assign exactly one integer colour in the inclusive range 1..{q} to every vertex.",
        "For every listed edge u v, the two endpoint colours must be different.",
        "Colours may be reused on nonadjacent vertices; there is no balance requirement.",
        "Your output order matters: entry i is the colour of vertex i (0-indexed).",
        "The graph contains a 4-clique used only to remove global colour-name symmetry.",
        "The following anchor colours are mandatory:",
    ]
    lines.extend(f"  vertex {v} -> colour {colour}" for v, colour in anchors)
    lines.extend(["", f"n = {n}", f"m = {len(edges)}", "edges:"])
    lines.extend(f"{u} {v}" for u, v in edges)
    lines.extend(
        [
            "end edges",
            "",
            f"Give your final answer inside <answer></answer> tags as exactly {n} "
            "comma-separated integers, in vertex-number order.",
            "Do not include brackets, vertex labels, explanations, or any other text inside the tags.",
            "For format only, a hypothetical 4-vertex answer would be:",
            "<answer>1, 2, 3, 4</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged comma-separated integer list, or return None."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json|text|python)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, list) or any(type(x) is not int for x in value):
            return None
        return value
    if not body:
        return None
    fields = body.split(",")
    if any(re.fullmatch(r"[+-]?\d+", field.strip()) is None for field in fields):
        return None
    try:
        return [int(field.strip()) for field in fields]
    except ValueError:
        return None


def random_candidate(inst, rng):
    """Uniform after the explicit clique symmetry-breaking constraints."""
    answer = [rng.randrange(1, inst["colours"] + 1) for _ in range(inst["n"])]
    for v, colour in _anchors(inst).items():
        answer[v] = colour
    return answer


def search_space(inst):
    return inst["colours"] ** (inst["n"] - len(_anchors(inst)))


def enumerate_all(inst):
    space = search_space(inst)
    if space > ENUMERATION_CAP:
        return None
    n = inst["n"]
    q = inst["colours"]
    anchors = _anchors(inst)
    free = [v for v in range(n) if v not in anchors]
    answer = [0] * n
    for v, colour in anchors.items():
        answer[v] = colour
    count = 0
    for values in itertools.product(range(1, q + 1), repeat=len(free)):
        for v, colour in zip(free, values):
            answer[v] = colour
        if verify(inst, answer)[0]:
            count += 1
    return count


def _wl_invariant(inst):
    """A relabelling-invariant 1-WL fingerprint with anchored initial colours."""
    n = inst["n"]
    adj = _adjacency(inst)
    initial = [0] * n
    for v, colour in _anchors(inst).items():
        initial[v] = colour
    labels = initial[:]
    for _ in range(n):
        signatures = [
            (labels[v], tuple(sorted(labels[w] for w in adj[v]))) for v in range(n)
        ]
        palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_labels = [palette[signature] for signature in signatures]
        if new_labels == labels:
            break
        labels = new_labels

    vertex_records = sorted(
        (
            labels[v],
            initial[v],
            len(adj[v]),
            tuple(sorted(labels[w] for w in adj[v])),
        )
        for v in range(n)
    )
    edge_records = sorted(
        (min(labels[u], labels[v]), max(labels[u], labels[v]))
        for u, v in inst["edges"]
    )
    anchor_records = sorted((labels[v], colour) for v, colour in _anchors(inst).items())
    return [inst["colours"], n, anchor_records, vertex_records, edge_records]


def canonical_key(inst):
    """Hash a structural WL invariant, never the seed, answer, or rendering."""
    encoded = json.dumps(_wl_invariant(inst), separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def escalate(params):
    """Increase both graph size and the exact-search resistance floor."""
    n = int(params.get("n", 140))
    if n >= 240:
        return None
    harder = dict(params)
    harder["n"] = n + 20
    harder["attack_restarts"] = int(params.get("attack_restarts", 32)) + 16
    harder["backtrack_floor"] = int(params.get("backtrack_floor", 10_000)) * 2
    return harder


def _transform_instance(inst, permutation, rng):
    """Relabel vertices and carry the witness through that relabelling."""
    n = inst["n"]
    edges = []
    for u, v in inst["edges"]:
        a, b = permutation[u], permutation[v]
        if rng.randrange(2):
            a, b = b, a
        edges.append((a, b))
    rng.shuffle(edges)
    anchors = [[permutation[v], colour] for v, colour in inst["anchors"]]
    rng.shuffle(anchors)
    answer = [0] * n
    for old, new in enumerate(permutation):
        answer[new] = inst["answer"][old]
    return {
        "family": inst["family"],
        "n": n,
        "colours": inst["colours"],
        "anchors": anchors,
        "edges": edges,
        "answer": answer,
        "generation": dict(inst.get("generation", {})),
    }


def _find_rejected_swap(inst):
    planted = list(inst["answer"])
    anchored = set(_anchors(inst))
    free = [v for v in range(inst["n"]) if v not in anchored]
    for i, u in enumerate(free):
        for v in free[i + 1 :]:
            if planted[u] == planted[v]:
                continue
            corrupt = planted[:]
            corrupt[u], corrupt[v] = corrupt[v], corrupt[u]
            ok, reason = verify(inst, corrupt)
            if not ok and reason.startswith("edge "):
                return corrupt
    # A colour replacement is a last-resort single-entry swap to a neighbour's
    # value; the generated density makes the pair-swap branch normally succeed.
    for u, v in inst["edges"]:
        if u not in anchored:
            corrupt = planted[:]
            corrupt[u] = planted[v]
            return corrupt
        if v not in anchored:
            corrupt = planted[:]
            corrupt[v] = planted[u]
            return corrupt
    raise AssertionError("no non-anchor edge for corruption test")


def selftest():
    """Run gates G1--G8 and return a JSON-serialisable evidence dictionary."""
    report = {
        "paper": "2002.10145",
        "family": "fixed-4-colouring",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every preset, several unrelated seeds.
    g1_failures = []
    g1_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 12_345):
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

    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=73_991, **params)
    planted = list(inst["answer"])

    # G2: five corruption modes, five distinct diagnostics.
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": _find_rejected_swap(inst),
        "duplicate_one": planted + [planted[-1]],
        "empty": [],
        "out_of_range": planted[:],
    }
    corruptions["out_of_range"][COLOURS] = COLOURS + 1
    g2 = {}
    for name, answer in corruptions.items():
        ok, reason = verify(inst, answer)
        g2[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in g2.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in g2.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "tests": g2,
    }

    # G3: realistic prose plus a Markdown fence around the tagged answer.
    body = ", ".join(map(str, planted))
    realistic = (
        "I checked every listed edge. My final response is below.\n\n"
        "```text\n<answer>\n" + body + "\n</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    garbage = ["", "no tagged answer", "<answer>1, nope</answer>"]
    report["G3_round_trip"] = {
        "pass": parsed == planted and all(parse_answer(x) is None for x in garbage),
        "parsed_entries": len(parsed) if isinstance(parsed, list) else None,
        "garbage_rejected": sum(parse_answer(x) is None for x in garbage),
        "garbage_total": len(garbage),
    }

    # G4: structure-aware guesses already honour all four symmetry anchors.
    guess_rng = random.Random(0x200210145)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "prior": "uniform colours on non-anchor vertices; all anchor constraints enforced",
        "naive_search_space": search_space(inst),
    }

    # G5: an exactly enumerable dense small member.
    small = make_instance(
        n=12,
        seed=90210,
        avg_degree=7.5,
        attack_restarts=0,
        backtrack_floor=0,
        filter_attacks=False,
    )
    solutions = enumerate_all(small)
    small_space = search_space(small)
    fraction = solutions / small_space if solutions is not None else None
    report["G5_sparse_solutions"] = {
        "pass": solutions is not None and fraction < 0.01,
        "n": small["n"],
        "valid_answers": solutions,
        "search_space": small_space,
        "fraction": fraction,
        "enumeration_cap": ENUMERATION_CAP,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: four attacks over eight independently generated, prefiltered graphs.
    attack_rows = {
        "degree_outlier": {"solved": 0, "total": 8},
        "deterministic_greedy": {"solved": 0, "total": 8},
        "random_restart": {
            "solved": 0,
            "total": 8,
            "restarts_each": params["attack_restarts"],
        },
        "bounded_backtracking": {
            "solved": 0,
            "total": 8,
            "node_limit": params["backtrack_floor"],
            "nodes": [],
        },
    }
    for seed in range(8100, 8108):
        attacked = make_instance(seed=seed, **params)
        outlier = _degree_outlier_attack(attacked)
        attack_rows["degree_outlier"]["solved"] += int(verify(attacked, outlier)[0])
        greedy = _dsatur_greedy(attacked)
        attack_rows["deterministic_greedy"]["solved"] += int(
            greedy is not None and verify(attacked, greedy)[0]
        )
        restarted = _random_restart_attack(attacked, params["attack_restarts"])
        attack_rows["random_restart"]["solved"] += int(restarted is not None)
        exact, nodes, _ = _bounded_backtracking_attack(
            attacked, params["backtrack_floor"]
        )
        attack_rows["bounded_backtracking"]["solved"] += int(exact is not None)
        attack_rows["bounded_backtracking"]["nodes"].append(nodes)
    report["G6_adversary_panel"] = {
        "pass": all(row["solved"] == 0 for row in attack_rows.values()),
        "attacks": attack_rows,
    }

    # G7: doubling n builds, verifies, expands the space, and resists the same
    # bounded exact attack.  The density remains in the same near-threshold band.
    doubled_params = dict(params)
    doubled_params["n"] = params["n"] * 2
    doubled = make_instance(seed=440_044, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_exact, doubled_nodes, _ = _bounded_backtracking_attack(
        doubled, params["backtrack_floor"]
    )
    report["G7_scales"] = {
        "pass": doubled_ok
        and search_space(doubled) > search_space(inst)
        and doubled_exact is None,
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_edges": len(inst["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "planted_verify_reason": doubled_reason,
        "bounded_attack_nodes": doubled_nodes,
    }

    # G8: vertex permutations, edge reordering, endpoint flips, and composed
    # transformations.  Every carried witness is independently verified.
    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for offset in range(20):
        original = make_instance(seed=600_000 + offset, **params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        n = original["n"]
        trng = random.Random(700_000 + offset)
        shuffled = list(range(n))
        trng.shuffle(shuffled)
        reverse = [n - 1 - v for v in range(n)]
        rotate = [(v + 17) % n for v in range(n)]
        composed = [reverse[shuffled[v]] for v in range(n)]
        transforms = [list(range(n)), reverse, rotate, shuffled, composed]
        for permutation in transforms:
            changed = _transform_instance(original, permutation, trng)
            same = canonical_key(changed) == key
            ok, reason = verify(changed, changed["answer"])
            invariant_checks += 1
            witness_checks += 1
            if not same or not ok:
                invariant_failures.append(
                    {"seed_offset": offset, "same_key": same, "witness_reason": reason}
                )
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct == 20,
        "invariance_passed": invariant_checks - len(invariant_failures),
        "invariance_total": invariant_checks,
        "carried_witness_passed": witness_checks - len(invariant_failures),
        "carried_witness_total": witness_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "transformations_each": [
            "edge reorder and endpoint flips",
            "reverse vertex numbering",
            "cyclic vertex renumbering",
            "random vertex permutation",
            "composed random-plus-reverse permutation",
        ],
        "failures": invariant_failures,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
