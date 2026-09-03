"""Verified inverse generator for Tournament Fixing (arXiv:2601.08530).

The witness is a complete leaf order for a balanced single-elimination bracket.
Only Python's standard library is used, and generation is deterministic in
``(n, seed)``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import time
from typing import Iterable


NATIVE: dict = {
    "domain": "combinatorics",
    "core": "permutation",
    "objects": [
        "directed tournament encoded by adjacency bit masks",
        "designated favorite",
    ],
    "intuition": "recursive bracket decomposition",
    "reduction": None,
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "For an n-player instance: exactly one length-n permutation of the "
        "integers 0 through n-1, serialized as comma-separated base-10 labels "
        "inside <answer></answer> tags"
    ),
    "bounds": {
        "sequence_length": "n",
        "label_min": 0,
        "label_max": "n - 1",
        "occurrences_per_label": 1,
    },
}

DIFFICULTY: dict = {
    "easy": {"n": 256},
    "medium": {"n": 512},
    "hard": {"n": 1024},
}
SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Paper basis.  Section 2 defines a seeding as a bijection from n=2^c players to
the leaves of a complete binary tree, and Definition 1 gives the exact replay
semantics.  Proposition 1 identifies winning seedings with labeled spanning
binomial arborescences.  General Tournament Fixing is NP-hard.  Section 4,
Theorem 2 is the regime used here: under ETH its doubly-exponential dependence
on the favorite's out-degree ell is essentially unavoidable, and the reduction
has ell=log2(n).  Every generated instance also has ell=log2(n), the minimum
possible value in a yes-instance.  Section 4's easy rejection ell<log2(n), the
2^n exact algorithm in Lemma 1, the FPT algorithms for small ell (Theorem 1) and
small in-degree k (Theorem 3), and the acyclic/low-fas/fvs cases in Sections 1
and 6 are the regimes deliberately avoided.  Both k=n-1-log2(n) and ell grow.

Inverse construction.  The implementation follows the bounded-occurrence
3-SAT reduction invoked in Section 4, Theorem 2 (Aziz et al., Theorem 1).  It
first samples a truth assignment, then a satisfied 3-CNF in which every signed
literal occurs exactly twice, and then the complete witness seeding.  Only
after that are all pairwise outcomes constructed from the reduction's choice,
clause/garbage, filler, and spawning gadgets.  A final uniformly random player
relabeling hides every construction index without changing the problem.

Attack handling.  The global-degree ordering attack, a deterministic greedy
protector, and 256 randomized greedy restarts are run on eight fresh instances.
The domain-standard exact subset dynamic program from the Tournament Fixing
literature is also run with a documented 50,000-state cap; at the shipping size
the exponential frontier exhausts that cap.  Canonicalization uses rooted
directed color refinement.  Generation retries when refinement is not discrete,
so the adjacency serialization is a true canonical form for every emitted
instance without hashing its seed or its rendered text.

Two prototypes were rejected before this version.  Conditioning an otherwise
random tournament on a minimum-outdegree favorite was solved by a randomized
greedy protector on 50/50 sampled instances.  Restricting each favorable
opponent to its planted match wins stopped that greedy attack but leaked the
opponent's intended round through its degree; a tailored subtree assembler then
solved 20/20.  The shipped reduction removes both planting shortcuts: all roles
are randomly relabeled, choice particles are globally coupled to clause gadgets,
and filler/spawning gadgets force the round structure.  Degree order, greedy,
and randomized greedy restarts consequently fail; the exact recurrence reaches its
explicit resource cap rather than returning a witness.
""".strip()


def _is_power_of_two(x: int) -> bool:
    return x >= 1 and (x & (x - 1)) == 0


def _beats(rows: list[int], a: int, b: int) -> bool:
    return bool((rows[a] >> b) & 1)


def _winner(rows: list[int], seeding: Iterable[int]) -> int:
    current = list(seeding)
    while len(current) > 1:
        current = [
            a if _beats(rows, a, b) else b
            for a, b in zip(current[0::2], current[1::2])
        ]
    return current[0]


def _refinement_order(n: int, favorite: int, rows: list[int]) -> list[int] | None:
    """Return an isomorphism-invariant vertex order when 1-WL is discrete."""
    colors = [0 if v == favorite else 1 for v in range(n)]
    for _ in range(n + 1):
        signatures = []
        for v in range(n):
            outgoing = [0] * (max(colors) + 1)
            incoming = [0] * (max(colors) + 1)
            for u in range(n):
                if u == v:
                    continue
                if _beats(rows, v, u):
                    outgoing[colors[u]] += 1
                else:
                    incoming[colors[u]] += 1
            signatures.append((colors[v], tuple(outgoing), tuple(incoming)))
        palette = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        if len(set(new_colors)) == n:
            return sorted(range(n), key=new_colors.__getitem__)
        if new_colors == colors:
            return None
        colors = new_colors
    return None


def _bounded_formula(variable_count: int, assignment: list[bool], rng: random.Random):
    """A planted 3-CNF: every positive and negative literal occurs twice."""
    for _ in range(100_000):
        stubs = [(v, sign) for v in range(variable_count) for sign in (False, True)
                 for _copy in range(2)]
        rng.shuffle(stubs)
        clauses = [stubs[i:i + 3] for i in range(0, len(stubs), 3)]
        if any(len({v for v, _sign in clause}) != 3 for clause in clauses):
            continue
        if any(not any(assignment[v] == sign for v, sign in clause)
               for clause in clauses):
            continue
        return clauses
    raise RuntimeError("could not sample a bounded-occurrence planted formula")


def _spawn_winner(a: int, b: int, positions: dict[int, int]) -> int:
    """Winner relation of the paper's left-to-right spawning construction."""
    i, j = positions[a], positions[b]
    if i > j:
        i, j, a, b = j, i, b, a
    parent = j - (j & -j)
    return a if i == parent else b


def _build_once(n: int, rng: random.Random) -> dict:
    variable_count = 3 * n // 128
    assignment = [bool(rng.getrandbits(1)) for _ in range(variable_count)]
    clauses = _bounded_formula(variable_count, assignment, rng)
    gadget_count = n // 16

    next_label = 0

    def fresh(count=1):
        nonlocal next_label
        if count == 1:
            value = next_label
            next_label += 1
            return value
        values = list(range(next_label, next_label + count))
        next_label += count
        return values

    M = fresh(gadget_count)
    choice = []
    for _ in range(variable_count):
        names = {name: fresh() for name in
                 ("x", "xb", "u", "a1", "a2", "b1", "b2", "c", "d", "e")}
        choice.append(names)
    clause_gadgets = []
    for _ in range(variable_count):
        names = {name: fresh() for name in
                 ("mp", "a", "b", "c", "d", "e", "cg",
                  "ap", "bp", "cp", "dp", "ep", "cgp")}
        clause_gadgets.append(names)
    filler = [fresh(15) for _ in range(gadget_count - 2 * variable_count)]
    special = []
    for _ in range(variable_count):
        special.append({"pos": fresh(3), "neg": fresh(3), "star": fresh()})
    if next_label != n:
        raise AssertionError("reduction player accounting failed")

    G = []
    for names in choice:
        G.append(list(names.values()))
    for names in clause_gadgets:
        G.append(list(names.values()))
    G.extend(filler)
    gadget_of = {v: i for i, group in enumerate(G) for v in group}
    m_positions = {v: i for i, v in enumerate(M)}
    S = {v for item in special for v in item["pos"] + item["neg"] + [item["star"]]}
    particle = {v for item in special for v in item["pos"] + item["neg"]}
    m_set = set(M)
    g_set = set(gadget_of)

    # Assign the two particles left out by every choice gadget.  Actual clauses
    # get a particle witnessing a true literal; unused c/g slots get leftovers.
    free_particles = []
    for v, truth in enumerate(assignment):
        free_particles.extend((special[v]["pos"] if truth else special[v]["neg"])[1:])
    cg_slots = []
    for names in clause_gadgets:
        cg_slots.extend((names["cg"], names["cgp"]))
    cg_clause = {}
    cg_particle = {}
    available_by_literal = {
        (v, assignment[v]): list((special[v]["pos"] if assignment[v]
                                  else special[v]["neg"])[1:])
        for v in range(variable_count)
    }
    for slot, formula_clause in zip(cg_slots, clauses):
        choices = [(v, sign) for v, sign in formula_clause if assignment[v] == sign
                   and available_by_literal[(v, sign)]]
        literal = rng.choice(choices)
        used = available_by_literal[literal].pop()
        free_particles.remove(used)
        cg_clause[slot] = formula_clause
        cg_particle[slot] = used
    rng.shuffle(free_particles)
    for slot in cg_slots[len(clauses):]:
        cg_particle[slot] = free_particles.pop()
    if free_particles:
        raise AssertionError("particle allocation failed")

    # The complete witness leaf order is now fixed, before a single match
    # outcome is constructed.
    local_seedings = []
    for v, names in enumerate(choice):
        sp = special[v]
        if assignment[v]:
            local = [M[v], names["d"], names["c"], names["e"],
                     names["x"], names["a1"], names["a2"], sp["pos"][0],
                     names["xb"], names["u"], names["b1"], sp["neg"][0],
                     names["b2"], sp["neg"][1], sp["neg"][2], sp["star"]]
        else:
            local = [M[v], names["d"], names["c"], names["e"],
                     names["xb"], names["b1"], names["b2"], sp["neg"][0],
                     names["x"], names["u"], names["a1"], sp["pos"][0],
                     names["a2"], sp["pos"][1], sp["pos"][2], sp["star"]]
        local_seedings.append(local)
    for offset, names in enumerate(clause_gadgets):
        p = cg_particle[names["cg"]]
        pp = cg_particle[names["cgp"]]
        local_seedings.append([
            M[variable_count + offset], names["a"], names["b"], names["c"],
            names["d"], names["e"], names["cg"], p,
            names["mp"], names["ap"], names["bp"], names["cp"],
            names["dp"], names["ep"], names["cgp"], pp,
        ])
    for offset, group in enumerate(filler):
        local_seedings.append([M[2 * variable_count + offset]] + group)
    answer = [v for local in local_seedings for v in local]
    if len(answer) != n or len(set(answer)) != n:
        raise AssertionError("witness is not a complete seeding")

    rows = [0] * n

    def set_winner(win: int, lose: int):
        rows[win] |= 1 << lose
        rows[lose] &= ~(1 << win)

    # Establish a complete default orientation matching the reduction's global
    # hierarchy, right-left rule, and spawning process.
    variable_of_s = {}
    kind_of_s = {}
    for i, item in enumerate(special):
        for v in item["pos"]:
            variable_of_s[v], kind_of_s[v] = i, "pos"
        for v in item["neg"]:
            variable_of_s[v], kind_of_s[v] = i, "neg"
        variable_of_s[item["star"]], kind_of_s[item["star"]] = i, "star"

    for a in range(n):
        for b in range(a + 1, n):
            if a in m_set and b in m_set:
                win = _spawn_winner(a, b, m_positions)
            elif a in S and b in S:
                va, vb = variable_of_s[a], variable_of_s[b]
                ka, kb = kind_of_s[a], kind_of_s[b]
                if va == vb and "star" in (ka, kb):
                    win = b if ka == "star" else a
                elif va != vb and ka == "star" and kb != "star":
                    win = a
                elif va != vb and kb == "star" and ka != "star":
                    win = b
                elif va != vb:
                    win = a if va > vb else b
                else:
                    # Within a literal triple, and between the two triples of a
                    # variable, use a deterministic local right-left order.
                    win = b
            elif a in S or b in S:
                win = a if a in S else b
            elif a in g_set and b in g_set:
                ga, gb = gadget_of[a], gadget_of[b]
                win = (a if ga > gb else b) if ga != gb else b
            elif a in g_set or b in g_set:
                win = a if a in g_set else b
            else:
                raise AssertionError("unclassified player")
            lose = b if win == a else a
            set_winner(win, lose)

    # Choice gadgets (Fig. 3 and the explicit replay in Fig. 6).
    for i, names in enumerate(choice):
        m, sp = M[i], special[i]
        for target in (names["d"], names["c"], names["x"], names["xb"]):
            set_winner(m, target)
        for target in (names["u"], names["a1"], names["a2"]):
            set_winner(names["x"], target)
        for target in (names["u"], names["b1"], names["b2"]):
            set_winner(names["xb"], target)
        set_winner(names["c"], names["e"])
        for a in (names["a1"], names["a2"]):
            for target in sp["pos"]:
                set_winner(a, target)
        for b in (names["b1"], names["b2"]):
            for target in sp["neg"]:
                set_winner(b, target)

    # Clause/garbage gadgets (Fig. 4).  A clause c/g player beats exactly
    # particles representing literals of its clause; garbage beats all particles.
    for offset, names in enumerate(clause_gadgets):
        m = M[variable_count + offset]
        for target in (names["a"], names["b"], names["d"], names["mp"]):
            set_winner(m, target)
        set_winner(names["b"], names["c"])
        for target in (names["e"], names["cg"]):
            set_winner(names["d"], target)
        for target in (names["ap"], names["bp"], names["dp"]):
            set_winner(names["mp"], target)
        set_winner(names["bp"], names["cp"])
        for target in (names["ep"], names["cgp"]):
            set_winner(names["dp"], target)
        for cg in (names["cg"], names["cgp"]):
            if cg in cg_clause:
                for v, sign in cg_clause[cg]:
                    for target in special[v]["pos" if sign else "neg"]:
                        set_winner(cg, target)
            else:
                for target in particle:
                    set_winner(cg, target)

    # Every filler gadget is a 16-player spawning construction rooted at m_j.
    for offset, group in enumerate(filler):
        participants = [M[2 * variable_count + offset]] + group
        positions = {v: i for i, v in enumerate(participants)}
        for ai, a in enumerate(participants):
            for b in participants[ai + 1:]:
                win = _spawn_winner(a, b, positions)
                set_winner(win, b if win == a else a)

    # Relabel every player after construction.  The solver sees no gadget or
    # formula indices, and the favorite is not tied to label zero.
    permutation = list(range(n))
    rng.shuffle(permutation)
    relabeled_rows = [0] * n
    for old_a in range(n):
        for old_b in range(n):
            if _beats(rows, old_a, old_b):
                relabeled_rows[permutation[old_a]] |= 1 << permutation[old_b]
    return {
        "n": n,
        "favorite": permutation[M[0]],
        "rows": relabeled_rows,
        "answer": [permutation[v] for v in answer],
    }


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a winning leaf order first, then construct outcomes around it."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if type(n) is not int or not _is_power_of_two(n) or n < 128:
        raise ValueError("n must be a power of two and at least 128")
    rng = random.Random(seed)
    for _ in range(128):
        inst = _build_once(n, rng)
        if _refinement_order(n, inst["favorite"], inst["rows"]) is not None:
            return inst
    raise RuntimeError("could not obtain a canonically refinable tournament")


def render(inst: dict) -> str:
    """Render the complete task, data, conventions, and answer wire format."""
    n = inst["n"]
    width = (n + 3) // 4
    rows = "\n".join(
        f"{i}: {inst['rows'][i]:0{width}x}" for i in range(n)
    )
    example = ", ".join(str(i) for i in range(n))
    return f"""Balanced knockout tournament fixing

There are {n} distinct players, numbered 0 through {n - 1}.  Player
{inst['favorite']} is the favorite.  For every two distinct players, exactly
one is predetermined to beat the other.

Construct one seeding that makes the favorite champion.  A seeding is a list
containing every player exactly once.  List position is the leaf position and
positions are 0-indexed.  In round 1, positions 0 and 1 play, positions 2 and 3
play, and so on.  In every later round, consecutive surviving winners play in
the same left-to-right order.  A match winner is determined by the table below;
there are no ties or probabilistic outcomes.  Continue until one champion
remains.  Swapping subtrees may describe an equivalent bracket, but your output
must still be a complete {n}-integer list.

Outcome table (hexadecimal bit masks): row i is a {width}-hex-digit nonnegative
integer.  Its bit j, where the least-significant/rightmost bit is bit 0, is 1
exactly when player i beats player j.  Diagonal bits are 0.  Leading zeroes are
shown and are significant only as padding.

{rows}

Give your final answer inside <answer></answer> tags, as {n} comma-separated
base-10 player numbers in leaf order.
Example format: <answer>{example}</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract one strict comma-separated integer list from tagged output."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            body = "\n".join(lines[1:-1]).strip()
    if not body:
        return []
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(piece.strip(), 10) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Replay a candidate bracket.  The planted answer is never consulted."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    if any(type(v) is not int for v in answer):
        return False, "every player label must be an integer"
    if any(v < 0 or v >= n for v in answer):
        return False, f"player label outside inclusive range 0..{n - 1}"
    if len(set(answer)) != n:
        return False, "player labels are duplicated"
    champion = _winner(inst["rows"], answer)
    if champion != inst["favorite"]:
        return False, f"favorite {inst['favorite']} did not win; champion was {champion}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the solver-visible space of complete permutations."""
    candidate = list(range(inst["n"]))
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """Count complete leaf-order responses (before bracket symmetries)."""
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Exactly count winning leaf orders when at most 8! must be replayed."""
    n = inst["n"]
    if n > 8:
        return None
    return sum(
        _winner(inst["rows"], order) == inst["favorite"]
        for order in itertools.permutations(range(n))
    )


def canonical_key(inst: dict) -> str:
    """Canonical rooted-tournament key, invariant under player renumbering."""
    n = inst["n"]
    rows = inst["rows"]
    order = _refinement_order(n, inst["favorite"], rows)
    if order is None:
        # make_instance screens this case; transformed legitimate instances are
        # equally discrete.  Refuse a misleading label-dependent fallback.
        raise ValueError("tournament color refinement is not discrete")
    where = {old: new for new, old in enumerate(order)}
    canonical_rows = []
    for old_a in order:
        mask = 0
        for old_b in order:
            if _beats(rows, old_a, old_b):
                mask |= 1 << where[old_b]
        canonical_rows.append(mask)
    payload = json.dumps(
        [n, where[inst["favorite"]], canonical_rows], separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | None:
    """Double once beyond the named ladder, to a 2048-player final rung."""
    if set(params) != {"n"}:
        return None
    n = params["n"]
    if type(n) is not int or n >= 2048:
        return None
    return {"n": n * 2}


def _merge_blocks(rows: list[int], pairs, blocks):
    next_blocks = {}
    active = []
    for a, b in pairs:
        win = a if _beats(rows, a, b) else b
        next_blocks[win] = blocks[a] + blocks[b]
        active.append(win)
    return active, next_blocks


def _greedy_protector(inst: dict, rng: random.Random | None = None):
    """Keep unused favorite-beatable players alive, using greedy bodyguards."""
    n, favorite, rows = inst["n"], inst["favorite"], inst["rows"]
    favorable = {v for v in range(n) if v != favorite and _beats(rows, favorite, v)}
    active = list(range(n))
    blocks = {v: [v] for v in active}
    while len(active) > 1:
        available = [v for v in active if v in favorable]
        if not available or favorite not in active:
            return None
        if rng is None:
            spent = min(available, key=lambda v: (rows[v].bit_count(), v))
        else:
            spent = rng.choice(available)
        pairs = [(favorite, spent)]
        used = {favorite, spent}
        favorable.remove(spent)
        protect = [v for v in active if v in favorable]
        if rng is None:
            protect.sort(key=lambda v: (rows[v].bit_count(), v))
        else:
            rng.shuffle(protect)
        for player in protect:
            victims = [
                v for v in active
                if v not in used and v not in favorable and _beats(rows, player, v)
            ]
            if not victims:
                return None
            if rng is None:
                victim = max(victims, key=lambda v: (rows[v].bit_count(), -v))
            else:
                victim = rng.choice(victims)
            pairs.append((player, victim))
            used.update((player, victim))
        rest = [v for v in active if v not in used]
        if rng is not None:
            rng.shuffle(rest)
        while rest:
            pairs.append((rest.pop(), rest.pop()))
        active, blocks = _merge_blocks(rows, pairs, blocks)
    return blocks.get(favorite)


def _outlier_degree_attack(inst: dict):
    """Put low-outdegree vertices early and the favorite in the first leaf."""
    favorite = inst["favorite"]
    others = [v for v in range(inst["n"]) if v != favorite]
    others.sort(key=lambda v: (inst["rows"][v].bit_count(), v))
    return [favorite] + others


def _subset_dp_attack(inst: dict, cap: int = 50_000):
    """Resource-bounded form of the standard exact subset recurrence.

    It computes all possible winners and one leaf-order witness for power-of-two
    subsets.  ``None`` means the state cap was exhausted before the full set.
    """
    n, rows = inst["n"], inst["rows"]
    possible = {1 << v: {v: [v]} for v in range(n)}
    states = n
    size = 2
    full = (1 << n) - 1
    while size <= n:
        layer = {}
        for combo in itertools.combinations(range(n), size):
            mask = sum(1 << v for v in combo)
            anchor = combo[0]
            rest = combo[1:]
            winners = {}
            for left_tail in itertools.combinations(rest, size // 2 - 1):
                left = (1 << anchor) | sum(1 << v for v in left_tail)
                right = mask ^ left
                if left not in possible or right not in possible:
                    continue
                for a, wa in possible[left].items():
                    for b, wb in possible[right].items():
                        win = a if _beats(rows, a, b) else b
                        if win not in winners:
                            winners[win] = wa + wb
                if len(winners) == size:
                    break
            if winners:
                layer[mask] = winners
            states += 1
            if states >= cap and mask != full:
                return None, states
        possible = layer
        if full in possible and inst["favorite"] in possible[full]:
            return possible[full][inst["favorite"]], states
        size *= 2
    return None, states


def _relabel(inst: dict, permutation: list[int]) -> dict:
    """Map each old player v to new label permutation[v]."""
    n = inst["n"]
    rows = [0] * n
    for old_a in range(n):
        new_a = permutation[old_a]
        for old_b in range(n):
            if _beats(inst["rows"], old_a, old_b):
                rows[new_a] |= 1 << permutation[old_b]
    return {
        "n": n,
        "favorite": permutation[inst["favorite"]],
        "rows": rows,
        "answer": [permutation[v] for v in inst["answer"]],
    }


def _find_losing_swap(inst: dict):
    base = inst["answer"]
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            changed = base[:]
            changed[i], changed[j] = changed[j], changed[i]
            ok, _ = verify(inst, changed)
            if not ok:
                return changed
    return None


def selftest() -> dict:
    """Run G1--G8 and return a JSON-serializable evidence report."""
    report = {}

    g1_cases = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_cases.append({"preset": preset, "seed": seed, "ok": ok, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": all(row["ok"] for row in g1_cases),
        "attempts": len(g1_cases),
        "failures": [row for row in g1_cases if not row["ok"]],
    }

    inst = make_instance(seed=202601, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = inst["answer"]
    corruptions = {
        "drop_one": base[:-1],
        "swap_one": _find_losing_swap(inst),
        "duplicate": base[:-1] + [base[0]],
        "empty": [],
        "out_of_range": base[:-1] + [inst["n"]],
    }
    g2_results = {}
    for name, candidate in corruptions.items():
        if candidate is None:
            g2_results[name] = {"rejected": False, "reason": "no losing swap found"}
        else:
            ok, why = verify(inst, candidate)
            g2_results[name] = {"rejected": not ok, "reason": why}
    reasons = [row["reason"] for row in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in g2_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    wire = ", ".join(map(str, base))
    model_reply = f"I replayed every round.\n```text\n<answer>{wire}</answer>\n```"
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == base and verify(inst, parsed)[0],
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "surrounding_prose_and_fence": True,
    }

    total = 200_000
    guess_rng = random.Random(0x260108530)
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        hits += int(verify(inst, candidate)[0])
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "prior": "uniform over all complete player permutations",
        "naive_search_space": search_space(inst),
    }

    baseline_cap = 50_000
    baseline_started = time.perf_counter()
    baseline_candidate, baseline_states = _subset_dp_attack(inst, baseline_cap)
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_success = (
        baseline_candidate is not None and verify(inst, baseline_candidate)[0]
    )
    report["G5_sparse"] = {
        "pass": (
            total == 200_000
            and probability < 1e-6
            and baseline_states == baseline_cap
            and not baseline_success
        ),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
        "density": {
            "method": "uniform random_candidate sampling",
            "sample_size": total,
            "valid_samples": hits,
            "observed_fraction": probability,
        },
        "baseline_cost": {
            "attack": "exact_subset_dp_50000",
            "wall_seconds": baseline_seconds,
            "subset_states_examined": baseline_states,
            "state_cap": baseline_cap,
            "success": baseline_success,
            "result": (
                "witness_found" if baseline_success
                else "state_cap_exhausted_without_witness"
            ),
        },
        "candidate_space": search_space(inst),
        "enumerate_all_result": "unsupported at shipping n=256",
    }

    attack_names = (
        "outlier_global_degree",
        "greedy_protector",
        "randomized_greedy_restart_256",
        "exact_subset_dp_50000",
    )
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    dp_states = []
    for seed in range(800, 808):
        sample = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate = _outlier_degree_attack(sample)
        attack_results[attack_names[0]]["successes"] += int(verify(sample, candidate)[0])

        candidate = _greedy_protector(sample)
        attack_results[attack_names[1]]["successes"] += int(
            candidate is not None and verify(sample, candidate)[0]
        )

        found = None
        restart_rng = random.Random(90_000 + seed)
        for _ in range(256):
            candidate = _greedy_protector(sample, restart_rng)
            if candidate is not None and verify(sample, candidate)[0]:
                found = candidate
                break
        attack_results[attack_names[2]]["successes"] += int(found is not None)

        candidate, states = _subset_dp_attack(sample, 50_000)
        dp_states.append(states)
        attack_results[attack_names[3]]["successes"] += int(
            candidate is not None and verify(sample, candidate)[0]
        )
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "domain_attack": "exact_subset_dp_50000",
        "domain_attack_states": dp_states,
    }

    base_n = DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
    doubled = make_instance(n=base_n * 2, seed=707)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and len(render(doubled)) > len(render(inst))
        and search_space(doubled) > search_space(inst),
        "base_n": base_n,
        "doubled_n": base_n * 2,
        "doubled_verify": doubled_why,
        "render_chars_base": len(render(inst)),
        "render_chars_doubled": len(render(doubled)),
    }

    invariant_checks = 0
    witness_checks = 0
    unrelated_keys = []
    g8_ok = True
    for seed in range(20):
        original = make_instance(n=256, seed=10_000 + seed)
        key = canonical_key(original)
        unrelated_keys.append(key)
        relabel_rng = random.Random(20_000 + seed)
        p = list(range(original["n"]))
        q = list(range(original["n"]))
        relabel_rng.shuffle(p)
        relabel_rng.shuffle(q)
        composition = [q[p[v]] for v in range(original["n"])]
        for mapping in (p, q, composition):
            transformed = _relabel(original, mapping)
            invariant_checks += 1
            g8_ok &= canonical_key(transformed) == key
            witness_checks += 1
            g8_ok &= verify(transformed, transformed["answer"])[0]
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": g8_ok and invariant_checks == 60 and witness_checks == 60 and distinct == 20,
        "invariance_checks": invariant_checks,
        "transformed_witness_checks": witness_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": "two arbitrary player relabelings and their composition",
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
