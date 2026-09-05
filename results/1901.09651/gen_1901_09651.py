"""Verified complementary-tour generator for arXiv:1901.09651.

The paper's Lemma 1 certifies nonadjacency of two directed TSP-polytope
vertices when their two tours admit a different complementary Hamiltonian
decomposition.  This module asks for that native certificate in a compact
switch-component notation.

Generation never solves the emitted instance.  A twelve-vertex identity with
four relative-permutation 3-cycles is copied, independently conjugated, joined
by a cycle splice, and subdivided.  In every copy, switching its distinguished
3-cycle preserves both Hamiltonian cycles.  The stored answer is carried
through all transformations.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "two directed Hamiltonian tours",
        "relative-permutation switch components",
    ],
    "verification_operations": [
        "exact relative-permutation orbit validation",
        "exact successor permutation switching",
        "directed cycle traversal",
        "directed cycle counting",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize that the relative 3-cycles recur as independent twelve-vertex "
        "tiles under a cyclic splice; without that decomposition, the exact "
        "reference scan must test every switch component against both full tours."
    ),
    "hardness_basis": (
        "Track B: Sections 3--4 reduce each annealing move to Hopcroft--Karp "
        "matching in O(sqrt(V)E), while this bounded switch language has an exact "
        "singleton-scan reference algorithm in O(cV); at the shipping preset it took "
        "0.0016 seconds and 24,128 exact pointer visits in the final audit, "
        "whereas the repeated-tile decomposition leaves at most 116 local exact "
        "checks after the structural insight."
    ),
    "max_answer_tokens": 13,
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
    "demo": {"n": 1, "padding": 1},
    "easy": {"n": 13, "padding": 2},
    "medium": {"n": 16, "padding": 3},
    "hard": {"n": 20, "padding": 4},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The relative 3-cycles recur as independent twelve-vertex tiles under a cyclic splice."
)
PLACEBO_HINT = (
    "The indexed 3-cycles reward careful tracking of the two displayed directed tours."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly n distinct switch-component "
        "indices chosen from 0 through 4n-1."
    ),
    "bounds": {
        "length": "n (the number of composed tiles)",
        "entry_min": 0,
        "entry_max": "4n-1",
        "distinct": True,
        "sorted": True,
        "candidate_count": "binomial(4n,n)",
    },
}

NOTES = (
    "Section 1 and Lemma 1 fix the exact witness: two tours z,w, different from "
    "x,y, whose directed-arc multiset is x union y. Section 3 fixes the input "
    "representation as two tour permutations and the one-sided meaning of a found "
    "decomposition. Section 4 gives polynomial cycle-cover generation by perfect "
    "matching (Hopcroft--Karp in O(sqrt(V)E) for directed tours). Section 6 identifies "
    "the easy regimes that were avoided: pyramidal pairs have a linear-time method, "
    "and the paper's random undirected pairs were solved in essentially every trial. "
    "The generator instead composes a displayed finite permutation identity and "
    "carries its certificate through conjugation, cyclic splicing, subdivision, input "
    "swap, and relabelling. Random subdivisions remove simple positional signatures. "
    "The audit attacks try cyclic-span outliers, successor-distance greed, input-order "
    "selection, and 256 structure-aware random restarts; the exact O(cV) singleton "
    "scan is reported separately as Track B's successful reference algorithm."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000

# Explicit twelve-vertex identity.  q is (0 1 ... 11).  If r is the product
# of the four 3-cycles below, p = q o r is also a 12-cycle.  For a subset S of
# r-cycles, both q o r_S and q o r_(complement S) are 12-cycles exactly for
# masks 0000, 0001, 1110, 1111.  Thus cycle 0 is the certified singleton switch.
_BASE_R_CYCLES = (
    (2, 3, 7),
    (6, 4, 9),
    (11, 5, 1),
    (0, 10, 8),
)
_BASE_Q = tuple(range(1, 12)) + (0,)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _cycle_successor(cycle):
    return {cycle[i]: cycle[(i + 1) % len(cycle)] for i in range(len(cycle))}


def _inverse_perm(p):
    return [p.index(i) for i in range(len(p))]


def _base_r():
    r = list(range(12))
    for block in _BASE_R_CYCLES:
        for u, v in zip(block, block[1:] + block[:1]):
            r[u] = v
    return r


def _one_cycle_list(successor, start=0):
    """Return the full cycle from start, or None unless successor is one cycle."""
    n = len(successor)
    if sorted(successor) != list(range(n)):
        return None
    out = []
    seen = set()
    v = start
    while v not in seen:
        if not 0 <= v < n:
            return None
        seen.add(v)
        out.append(v)
        v = successor[v]
    if v != start or len(out) != n:
        return None
    return out


def _orbit_sets(r):
    seen = set()
    out = []
    for start in range(len(r)):
        if start in seen:
            continue
        orbit = []
        v = start
        while v not in seen:
            seen.add(v)
            orbit.append(v)
            v = r[v]
        if len(orbit) > 1:
            out.append(tuple(sorted(orbit)))
    return sorted(out)


def _validate_params(n, padding, seed):
    if not _is_int(n) or n < 1:
        raise ValueError("n must be a positive integer number of tiles")
    if not _is_int(padding) or not 1 <= padding <= 16:
        raise ValueError("padding must be an integer from 1 through 16")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def make_instance(n, seed=0, **params):
    """Compose certified complementary-tour identities without solving.

    ``n`` is the number of twelve-vertex identities.  ``padding`` independently
    subdivides their vertices, enlarging the displayed tours without changing
    the certificate length.  Every random choice is a certificate-preserving
    transformation of the explicit base identity above.
    """
    padding = params.pop("padding", 2)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, padding, seed)
    rng = random.Random(seed)

    base_r = _base_r()
    base_p = [_BASE_Q[base_r[v]] for v in range(12)]
    q = [None] * (12 * n)
    r = [None] * (12 * n)
    connectors = []
    planted_orbits = []

    for tile in range(n):
        off = 12 * tile
        flip = bool(rng.getrandbits(1))
        local_q = list(base_p if flip else _BASE_Q)
        local_r = _inverse_perm(base_r) if flip else list(base_r)

        # A conjugation changes labels but preserves all four tour identities.
        image = list(range(12))
        rng.shuffle(image)
        inv_image = [0] * 12
        for old, new in enumerate(image):
            inv_image[new] = old
        for new_v in range(12):
            old_v = inv_image[new_v]
            q[off + new_v] = off + image[local_q[old_v]]
            r[off + new_v] = off + image[local_r[old_v]]

        connector = off + rng.randrange(12)
        connectors.append(connector)
        planted_orbits.append(tuple(sorted(off + image[v] for v in _BASE_R_CYCLES[0])))

    # Rotate the outgoing q-arcs at one point per tile.  This joins n disjoint
    # q-cycles into one.  Because p is defined as q o r, the same splice joins
    # the n p-cycles, and it joins every carried candidate pair as well.
    old_next = [q[v] for v in connectors]
    for tile, v in enumerate(connectors):
        q[v] = old_next[(tile + 1) % n]
    p = [q[r[v]] for v in range(12 * n)]
    assert _one_cycle_list(q) is not None
    assert _one_cycle_list(p) is not None

    # Subdivide each vertex by a common chain used by both tours.  Only the last
    # clone carries the original choice of outgoing arc.
    lengths = [rng.randint(1, padding) for _ in range(12 * n)]
    first = []
    last = []
    cursor = 0
    for length in lengths:
        first.append(cursor)
        last.append(cursor + length - 1)
        cursor += length
    vertex_count = cursor
    x_succ = [None] * vertex_count
    y_succ = [None] * vertex_count
    for v, length in enumerate(lengths):
        a = first[v]
        for u in range(a, a + length - 1):
            x_succ[u] = u + 1
            y_succ[u] = u + 1
        x_succ[last[v]] = first[q[v]]
        y_succ[last[v]] = first[p[v]]

    components = []
    for tile in range(n):
        off = 12 * tile
        local_r = [r[off + v] - off for v in range(12)]
        for orbit in _orbit_sets(local_r):
            components.append(tuple(sorted(last[off + v] for v in orbit)))

    planted_sets = {
        tuple(sorted(last[v] for v in orbit)) for orbit in planted_orbits
    }
    assert len(components) == 4 * n
    assert len(planted_sets) == n

    # Global vertex relabelling, cyclic presentation changes, component reorder,
    # and input swap erase construction order while carrying the certificate.
    labels = list(range(vertex_count))
    rng.shuffle(labels)
    x_lab = [None] * vertex_count
    y_lab = [None] * vertex_count
    for old in range(vertex_count):
        x_lab[labels[old]] = labels[x_succ[old]]
        y_lab[labels[old]] = labels[y_succ[old]]
    components = [tuple(sorted(labels[v] for v in block)) for block in components]
    planted_sets = {tuple(sorted(labels[v] for v in block)) for block in planted_sets}

    if rng.getrandbits(1):
        x_lab, y_lab = y_lab, x_lab
    x_cycle = _one_cycle_list(x_lab, rng.randrange(vertex_count))
    y_cycle = _one_cycle_list(y_lab, rng.randrange(vertex_count))
    assert x_cycle is not None and y_cycle is not None

    order = list(range(len(components)))
    rng.shuffle(order)
    components = [components[i] for i in order]
    answer = sorted(i for i, block in enumerate(components) if block in planted_sets)
    assert len(answer) == n

    return {
        "paper": "arXiv:1901.09651",
        "family": "directed complementary Hamiltonian-tour decomposition",
        "tile_count": n,
        "padding": padding,
        "vertex_count": vertex_count,
        "tour_x": x_cycle,
        "tour_y": y_cycle,
        "switch_components": [list(block) for block in components],
        "select_count": n,
        "answer": answer,
    }


def _instance_data(inst):
    cached = inst.get("_data_cache") if isinstance(inst, dict) else None
    if isinstance(cached, tuple) and len(cached) == 5:
        return cached, "ok"
    try:
        n = inst["vertex_count"]
        x = inst["tour_x"]
        y = inst["tour_y"]
        components = inst["switch_components"]
        choose = inst["select_count"]
    except (KeyError, TypeError):
        return None, "instance fields are missing"
    if not _is_int(n) or n < 3:
        return None, "invalid vertex count"
    universe = list(range(n))
    if (not isinstance(x, list) or not isinstance(y, list)
            or len(x) != n or len(y) != n
            or sorted(x) != universe or sorted(y) != universe):
        return None, "input tours are not vertex permutations"
    if not _is_int(choose) or choose < 1:
        return None, "invalid selection size"
    if not isinstance(components, list) or len(components) != 4 * choose:
        return None, "invalid switch-component count"
    if any(not isinstance(c, list) or len(c) != 3
           or any(not _is_int(v) or not 0 <= v < n for v in c)
           or len(set(c)) != 3 for c in components):
        return None, "switch components must be triples of distinct vertices"
    flat = [v for c in components for v in c]
    if len(set(flat)) != len(flat):
        return None, "switch components overlap"

    xs_map = _cycle_successor(x)
    ys_map = _cycle_successor(y)
    xs = [xs_map[v] for v in universe]
    ys = [ys_map[v] for v in universe]
    pred_x = [0] * n
    for v, w in enumerate(xs):
        pred_x[w] = v
    rel = [pred_x[ys[v]] for v in universe]
    actual = _orbit_sets(rel)
    stated = sorted(tuple(sorted(c)) for c in components)
    if actual != stated:
        return None, "listed switch components do not match the input tours"
    data = (n, xs, ys, components, choose)
    inst["_data_cache"] = data
    return data, "ok"


def _pair_successors(data, selected):
    n, xs, ys, components, _ = data
    use_y = [False] * n
    for index in selected:
        for v in components[index]:
            use_y[v] = True
    z = [ys[v] if use_y[v] else xs[v] for v in range(n)]
    w = [xs[v] if use_y[v] else ys[v] for v in range(n)]
    return z, w


def _pair_cycle_counts(data, selected):
    """Count cycles without materialising two length-V successor arrays."""
    n, xs, ys, components, _ = data
    use_y = set()
    for index in selected:
        use_y.update(components[index])

    def count(complement):
        seen = [False] * n
        cycles = 0
        for start in range(n):
            if seen[start]:
                continue
            cycles += 1
            v = start
            while not seen[v]:
                seen[v] = True
                chosen = v in use_y
                if complement:
                    chosen = not chosen
                v = ys[v] if chosen else xs[v]
        return cycles

    return count(False), count(True)


def _cycle_count(successor):
    n = len(successor)
    if sorted(successor) != list(range(n)):
        return None
    seen = set()
    count = 0
    for start in range(n):
        if start in seen:
            continue
        count += 1
        v = start
        while v not in seen:
            seen.add(v)
            v = successor[v]
    return count


def _valid_pair(data, selected):
    return _pair_cycle_counts(data, selected) == (1, 1)


def verify(inst, answer):
    """Check any certificate in the declared switch language; never read answer."""
    data, why = _instance_data(inst)
    if data is None:
        return False, why
    _, xs, ys, components, choose = data
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != choose:
        return False, f"expected exactly {choose} component indices"
    if any(not _is_int(v) for v in answer):
        return False, "every component index must be an integer"
    if len(set(answer)) != len(answer):
        return False, "component indices must be distinct"
    if any(v < 0 or v >= len(components) for v in answer):
        return False, f"component index outside 0..{len(components) - 1}"
    if answer != sorted(answer):
        return False, "component indices must be in strictly increasing order"

    zc, wc = _pair_cycle_counts(data, set(answer))
    if zc != 1:
        return False, f"the selected tour has {zc} directed cycles, not one"
    if wc != 1:
        return False, f"the complementary tour has {wc} directed cycles, not one"
    # The language requires a nonempty proper subset of nontrivial relative
    # cycles, so both successor permutations differ from both inputs.
    return True, "ok"


def render(inst):
    data, why = _instance_data(inst)
    if data is None:
        raise ValueError(why)
    n, _, _, components, choose = data
    lines = [
        "Complementary directed Hamiltonian tours",
        "",
        "A directed Hamiltonian tour is a cyclic ordering of every vertex exactly once;",
        "the last listed vertex has an arc back to the first. Two input tours x and y",
        "on vertices 0 through %d are given below." % (n - 1),
        "",
        "A switch component is a listed triple of tail vertices. Choose exactly %d" % choose,
        "distinct component indices. For every tail in a chosen component, put y's",
        "outgoing arc in z and x's outgoing arc in w. At every other tail, put x's",
        "outgoing arc in z and y's outgoing arc in w. The listed components are",
        "pairwise disjoint. This rule uses every occurrence of every input arc exactly",
        "once, including parallel occurrences.",
        "",
        "Find indices for which z and w are each a single directed Hamiltonian tour",
        "and the unordered pair {z,w} is different from {x,y}.",
        "",
        "All indexing is 0-based. Order does not matter mathematically, but output the",
        "indices in strictly increasing order; repeats are forbidden.",
        "",
        "x: " + " ".join(map(str, inst["tour_x"])),
        "y: " + " ".join(map(str, inst["tour_y"])),
        "",
        "Switch components (index: tail vertices):",
    ]
    for index, block in enumerate(components):
        lines.append(f"{index}: " + " ".join(map(str, block)))
    example = list(range(choose))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON list of",
        f"exactly {choose} distinct increasing component indices.",
        "Format example only: <answer>" + json.dumps(example) + "</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def random_candidate(inst, rng):
    data, why = _instance_data(inst)
    if data is None:
        raise ValueError(why)
    _, _, _, components, choose = data
    return sorted(rng.sample(range(len(components)), choose))


def search_space(inst):
    data, why = _instance_data(inst)
    if data is None:
        raise ValueError(why)
    _, _, _, components, choose = data
    return math.comb(len(components), choose)


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    data, _ = _instance_data(inst)
    count = 0
    for candidate in itertools.combinations(range(len(data[3])), data[4]):
        if _valid_pair(data, set(candidate)):
            count += 1
    return count


def _relative_code(first, second):
    n = len(first)
    fs = _cycle_successor(first)
    ss = _cycle_successor(second)
    pos = {v: i for i, v in enumerate(first)}
    raw = [pos[ss[first[i]]] for i in range(n)]
    best = None
    for shift in range(n):
        code = tuple((raw[(i + shift) % n] - shift) % n for i in range(n))
        if best is None or code < best:
            best = code
    return best


def _reverse_cycle(cycle):
    return [cycle[0]] + list(reversed(cycle[1:]))


def canonical_key(inst):
    data, why = _instance_data(inst)
    if data is None:
        raise ValueError(why)
    x, y = inst["tour_x"], inst["tour_y"]
    xr, yr = _reverse_cycle(x), _reverse_cycle(y)
    code = min(
        _relative_code(x, y),
        _relative_code(y, x),
        _relative_code(xr, yr),
        _relative_code(yr, xr),
    )
    payload = json.dumps(
        [inst["vertex_count"], inst["select_count"], code],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    q = dict(params)
    padding = int(q.get("padding", 2))
    tiles = int(q.get("n", 13))
    if padding < 8:
        q["padding"] = padding + 1
        q["n"] = tiles
        return q
    if tiles < 240:
        q["n"] = min(240, tiles + max(2, tiles // 5))
        q["padding"] = padding
        return q
    return "cap_bound"


def _reference_singleton_scan(inst):
    """Exact Track-B reference: test each relative cycle as a singleton."""
    data, why = _instance_data(inst)
    if data is None:
        return None, 0, why
    n, _, _, components, choose = data
    selected = []
    visits = 0
    for index in range(len(components)):
        visits += 2 * n
        if _pair_cycle_counts(data, {index}) == (1, 1):
            selected.append(index)
    candidate = sorted(selected)
    if len(candidate) != choose:
        return candidate, visits, "singleton scan found the wrong number of components"
    ok, reason = verify(inst, candidate)
    return candidate, visits, reason if ok else reason


def _positions(inst):
    return {v: i for i, v in enumerate(inst["tour_x"])}


def _attack_minimum_span(inst, _rng):
    pos = _positions(inst)
    n = inst["vertex_count"]
    scored = []
    for index, component in enumerate(inst["switch_components"]):
        at = sorted(pos[v] for v in component)
        gaps = [at[1] - at[0], at[2] - at[1], n - at[2] + at[0]]
        scored.append((min(gaps), sum(gaps_i * gaps_i for gaps_i in gaps), index))
    return sorted(index for _, _, index in sorted(scored)[:inst["select_count"]])


def _attack_successor_distance(inst, _rng):
    pos = _positions(inst)
    ys = _cycle_successor(inst["tour_y"])
    n = inst["vertex_count"]
    scored = []
    for index, component in enumerate(inst["switch_components"]):
        distance = 0
        for v in component:
            d = (pos[ys[v]] - pos[v]) % n
            distance += min(d, n - d)
        scored.append((distance, index))
    return sorted(index for _, index in sorted(scored)[:inst["select_count"]])


def _attack_input_order(inst, _rng):
    return list(range(inst["select_count"]))


def _attack_orientation_agreement(inst, _rng):
    px = _positions(inst)
    py = {v: i for i, v in enumerate(inst["tour_y"])}
    scored = []
    for index, component in enumerate(inst["switch_components"]):
        xorder = sorted(component, key=px.get)
        yranks = [py[v] for v in xorder]
        inversions = sum(yranks[i] > yranks[j]
                         for i in range(3) for j in range(i + 1, 3))
        scored.append((inversions, index))
    return sorted(index for _, index in sorted(scored)[:inst["select_count"]])


def _attack_random_restart(inst, rng, restarts=256):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _copy_instance(inst):
    return json.loads(json.dumps({k: v for k, v in inst.items()
                                  if not k.startswith("_")}))


def _relabel_and_reorder(inst, rng):
    out = _copy_instance(inst)
    n = out["vertex_count"]
    label = list(range(n))
    rng.shuffle(label)
    out["tour_x"] = [label[v] for v in out["tour_x"]]
    out["tour_y"] = [label[v] for v in out["tour_y"]]
    old_components = [[label[v] for v in c] for c in out["switch_components"]]
    order = list(range(len(old_components)))
    rng.shuffle(order)
    out["switch_components"] = [old_components[i] for i in order]
    old_to_new = {old: new for new, old in enumerate(order)}
    out["answer"] = sorted(old_to_new[i] for i in out["answer"])
    sx = rng.randrange(n)
    sy = rng.randrange(n)
    out["tour_x"] = out["tour_x"][sx:] + out["tour_x"][:sx]
    out["tour_y"] = out["tour_y"][sy:] + out["tour_y"][:sy]
    out["tour_x"], out["tour_y"] = out["tour_y"], out["tour_x"]
    return out


def _reverse_instance_with_answer(inst):
    """Reverse every arc and carry the selected complementary decomposition."""
    data, why = _instance_data(inst)
    if data is None:
        raise ValueError(why)
    z, _ = _pair_successors(data, set(inst["answer"]))
    z_cycle = _one_cycle_list(z)
    if z_cycle is None:
        raise ValueError("cannot reverse a non-Hamiltonian carried witness")

    out = _copy_instance(inst)
    out["tour_x"] = _reverse_cycle(out["tour_x"])
    out["tour_y"] = _reverse_cycle(out["tour_y"])
    z_reversed = _reverse_cycle(z_cycle)
    n = out["vertex_count"]
    xs = _cycle_successor(out["tour_x"])
    ys = _cycle_successor(out["tour_y"])
    zs = _cycle_successor(z_reversed)
    pred_x = [0] * n
    for v, target in xs.items():
        pred_x[target] = v
    relative = [pred_x[ys[v]] for v in range(n)]
    components = [list(block) for block in _orbit_sets(relative)]
    selected_tails = {
        v for v in range(n) if xs[v] != ys[v] and zs[v] == ys[v]
    }
    out["switch_components"] = components
    out["answer"] = sorted(
        index for index, block in enumerate(components)
        if set(block) <= selected_tails
    )
    return out


def _solution_count_formula(tiles):
    # Coefficient of x^tiles in (1+x+x^3+x^4)^tiles.  The four exponents
    # are exactly the locally Hamiltonian masks 0000,0001,1110,1111.
    dp = [1] + [0] * (4 * tiles)
    for _ in range(tiles):
        nxt = [0] * len(dp)
        for degree, value in enumerate(dp):
            if value:
                for weight in (0, 1, 3, 4):
                    nxt[degree + weight] += value
        dp = nxt
    return dp[tiles]


# Filled from the separately owned harden.py runs.  These are diagnostics only;
# the harness-owned transcripts remain the authoritative per-call evidence.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "service_errors": 0},
    "hinted": {"solved": 0, "attempts": 3, "service_errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "service_errors": 0},
    "hinted_verdict": "hardened (diagnostic; 0/3 solved)",
}


def selftest():
    report = {}

    planted_attempts = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                planted_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "attempts": planted_attempts,
        "failures": planted_failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    ans = shipping["answer"]
    corruptions = {}
    tests = {
        "drop_one": ans[:-1],
        "swap_two": ([ans[1], ans[0]] + ans[2:]) if len(ans) > 1 else [1, 0],
        "duplicate": [ans[0], ans[0]] + ans[2:],
        "empty": [],
        "out_of_range": ans[:-1] + [len(shipping["switch_components"])],
    }
    for name, candidate in tests.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [v["reason"] for v in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": corruptions,
    }

    wire = json.dumps(ans)
    parsed = parse_answer(
        "I followed the cycle switches.\n```json\nintermediate omitted\n```\n"
        f"My final response is <answer>\n```json\n{wire}\n```\n</answer>."
    )
    report["G3_round_trip"] = {
        "pass": parsed == ans and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == ans,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(190109651)
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            guess_hits += 1
    guess_seconds = time.perf_counter() - t0
    guess_fraction = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "observed_fraction": guess_fraction,
        "structure_aware_space": search_space(shipping),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
    }

    ref_start = time.perf_counter()
    ref_answer, ref_visits, ref_reason = _reference_singleton_scan(shipping)
    ref_seconds = time.perf_counter() - ref_start
    ref_ok = ref_answer is not None and verify(shipping, ref_answer)[0]
    exact_valid = _solution_count_formula(shipping["tile_count"])
    exact_density = exact_valid / search_space(shipping)
    report["G5_density_and_baseline"] = {
        "pass": exact_density < 1e-6 and ref_ok,
        "shipping_valid_answer_count": exact_valid,
        "shipping_candidate_count": search_space(shipping),
        "shipping_exact_solution_fraction": exact_density,
        "sampled_hits": guess_hits,
        "sampled_total": _GUESS_SAMPLES,
        "sampled_fraction": guess_fraction,
        "baseline_wall_clock_sec": round(ref_seconds, 6),
        "baseline_pointer_visits": ref_visits,
        "baseline_components_tested": len(shipping["switch_components"]),
        "baseline_reason": ref_reason,
    }

    attacks = {
        "outlier_minimum_cyclic_span": {"successes": 0, "attempts": 0},
        "greedy_successor_distance": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "by_hand_input_order_ansatz": {"successes": 0, "attempts": 0},
        "orientation_agreement_ansatz": {"successes": 0, "attempts": 0},
    }
    ref_successes = 0
    ref_total_visits = 0
    ref_only_seconds = 0.0
    for seed in range(7100, 7108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        local_rng = random.Random(seed ^ 0x5A17)
        candidates = {
            "outlier_minimum_cyclic_span": _attack_minimum_span(inst, local_rng),
            "greedy_successor_distance": _attack_successor_distance(inst, local_rng),
            "random_restart_256": _attack_random_restart(inst, local_rng),
            "by_hand_input_order_ansatz": _attack_input_order(inst, local_rng),
            "orientation_agreement_ansatz": _attack_orientation_agreement(inst, local_rng),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attacks[name]["successes"] += 1
        one_ref_start = time.perf_counter()
        candidate, visits, _ = _reference_singleton_scan(inst)
        ref_only_seconds += time.perf_counter() - one_ref_start
        ref_total_visits += visits
        if candidate is not None and verify(inst, candidate)[0]:
            ref_successes += 1
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact singleton relative-cycle scan",
            "complexity": "O(cV) exact successor traversals",
            "wall_clock_sec_for_8": round(ref_only_seconds, 6),
            "operations_pointer_visits_for_8": ref_total_visits,
            "solves": f"{ref_successes}/8, as expected on Track B",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_tiles": shipping["tile_count"],
        "doubled_tiles": doubled["tile_count"],
        "shipping_space": search_space(shipping),
        "doubled_space": search_space(doubled),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    transformed_verifies = 0
    distinct_keys = set()
    invariant_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        distinct_keys.add(key)
        transformed = _relabel_and_reorder(inst, random.Random(12000 + seed))
        reversed_inst = _reverse_instance_with_answer(inst)
        composed = _relabel_and_reorder(reversed_inst, random.Random(15000 + seed))
        for label, variant in (
            ("relabel/reorder/rotate/input-swap", transformed),
            ("global arc reversal", reversed_inst),
            ("reversal composed with relabelling", composed),
        ):
            invariant_checks += 1
            if canonical_key(variant) != key:
                invariant_failures.append(f"seed {seed}: {label} key changed")
            if verify(variant, variant["answer"])[0]:
                transformed_verifies += 1
            else:
                invariant_failures.append(f"seed {seed}: {label} witness failed")
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and transformed_verifies == 60
                and len(distinct_keys) == 20,
        "invariance_checks": invariant_checks,
        "transformed_witness_checks": transformed_verifies,
        "unrelated_distinct_keys": len(distinct_keys),
        "unrelated_attempts": 20,
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(shipping["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_ops = 8 * shipping["tile_count"] + 12
    arms = {
        key: dict(G9_ORACLE_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
