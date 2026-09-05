"""Verified Track-B generator for arXiv:2602.13970.

The task is the paper's native (15,4)-list-colouring problem on a
triangle-free planar graph.  Instances and witnesses are inverse-generated;
verification uses only list membership and edgewise set disjointness.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "triangle-free planar graph",
        "15-element integer colour list at each vertex",
        "four-fold list colouring",
    ],
    "verification_operations": [
        "exact set cardinality comparison",
        "integer list-membership comparison",
        "exact set intersection on every graph edge",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A hidden multiplicative-coset invariant synchronizes each vertex "
        "label with exactly four colours in its list; without it, a solver "
        "faces 1365 locally valid four-subsets at every vertex."
    ),
    "hardness_basis": (
        "Track B: generic MRV forward-checking CSP search has worst-case "
        "O(1365^n) time and O(1365n) domain space; at shipping n=50 the "
        "reference implementation solved 8/8 and averaged 102,766 exact "
        "compatibility checks, 50 search nodes, and 0.0035 seconds, while "
        "the distribution-specific O(p+n) multiplicative-coset route uses "
        "at most 170 exact operations."
    ),
    "max_answer_tokens": 229,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 5},
    "easy": {"n": 10},
    "medium": {"n": 30},
    "hard": {"n": 50},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The nonzero vertex and colour labels occupy synchronized multiplicative "
    "cosets modulo one more than the largest vertex label."
)
PLACEBO_HINT = (
    "The integer vertex and colour labels require consistent bookkeeping "
    "across all of the stated edges."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array containing one [vertex,[c1,c2,c3,c4]] entry per vertex; "
        "the four distinct colours come from that vertex's advertised list."
    ),
    "bounds": {
        "entries": "n",
        "colours_per_vertex": 4,
        "list_size": 15,
        "local_choices": 1365,
        "max_shipping_entries": 50,
        "max_shipping_atomic_integers": 250,
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}

NOTES = r"""
Section 1 fixes the exact problem: an (L,b)-colouring chooses b listed colours
at every vertex and adjacent vertices receive disjoint sets. Theorem 3 proves
that every triangle-free planar graph is (15m,4m)-choosable for every positive
integer m; this family uses m=1. Section 2's partial-colouring language and
Observation 4 confirm that concrete chosen sets are executable witnesses.
Sections 3 and 4 prove Theorem 3 by reducible configurations and discharging,
not by a stated colouring algorithm.

STEP 0 rules out Track A for this planted distribution: a short arithmetic
algorithm is deliberately present. The paper also records easy surrounding
regimes—Groetzsch three-colourability and 3-degeneracy, hence (4m,m)-
choosability—and paths or ordinary cycles succumb to left-to-right greedy
colouring. The generator therefore uses a planar stack of pentagonal rings and
declares Track B. Generic MRV/forward-checking search is measured as the
successful reference route; the compact route recognizes a multiplicative-
coset invariant.

Each consecutive pair of rings induces a pentagonal prism, and the whole stack
is planar and triangle-free with a proper three-class labelling. The nonzero
residues modulo a prime p=1 mod 3 split into three equal multiplicative cosets.
Every vertex name is sampled from its class. An exchangeable six-colour
subpalette is sampled inside each coset; four entries of each 15-list come from
the matching subpalette and eleven from the other two. The four matching
entries are known before the list exists. All names and presentation orders
are randomized. Thus generation is inverse,
never a solve. A late trap vertex makes input-order greedy consume twelve of
its fifteen entries at its three already-presented neighbours; the front-
loaded trap entries are decoys, not a signature of the plant.

The attacks test global-frequency outliers, input-order greedy, 256 randomized
low-frequency restarts, and the smallest-label ansatz. canonical_key discards
numeric names and uses degree, colour-frequency, list-intersection, and
edge-intersection signatures. It is a strong polynomial invariant for these
instances, not a complete graph-isomorphism canonical form; this limitation
is reported in the README.
""".strip()


def _is_prime(x):
    if x < 2:
        return False
    if x % 2 == 0:
        return x == 2
    d = 3
    while d * d <= x:
        if x % d == 0:
            return False
        d += 2
    return True


def _factors(x):
    out, d = [], 2
    while d * d <= x:
        if x % d == 0:
            out.append(d)
            while x % d == 0:
                x //= d
        d += 1
    if x > 1:
        out.append(x)
    return out


def _primitive_root(p):
    factors = _factors(p - 1)
    for g in range(2, p):
        if all(pow(g, (p - 1) // factor, p) != 1 for factor in factors):
            return g
    raise AssertionError("no primitive root")


def _cosets(n):
    need = max(10, (n + 2) // 3)
    p = 3 * need + 1
    while not _is_prime(p):
        p += 3
    g = _primitive_root(p)
    groups = [[], [], []]
    value = 1
    for exponent in range(p - 1):
        groups[exponent % 3].append(value)
        value = value * g % p
    return p, g, groups


def _base_graph(n):
    if n == 5:
        return [(i, (i + 1) % 5) for i in range(5)], [0, 1, 0, 1, 2]
    if n < 10 or n % 10:
        raise ValueError("n must be 5 or a positive multiple of 10")
    edges, classes = [], []
    pattern = [0, 1, 0, 1, 2]
    for ring in range(n // 5):
        base, shift = 5 * ring, ring % 3
        classes.extend((c + shift) % 3 for c in pattern)
        edges.extend((base + i, base + (i + 1) % 5) for i in range(5))
        if ring:
            edges.extend((base - 5 + i, base + i) for i in range(5))
    return edges, classes


def _neighbors(n, edges):
    result = [[] for _ in range(n)]
    for u, v in edges:
        result[u].append(v)
        result[v].append(u)
    return result


def _nonmatching(rng, groups, own, excluded, count):
    pool = [x for c, group in enumerate(groups) if c != own
            for x in group if x not in excluded]
    return rng.sample(pool, count)


def make_instance(n, seed=0, **params):
    """Build a witnessed instance without solving the generated CSP."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    rng = random.Random(seed)
    edges, classes = _base_graph(n)
    p, generator, groups = _cosets(n)
    palettes = [rng.sample(group, 6) for group in groups]

    codes = [None] * n
    for c in range(3):
        positions = [i for i, value in enumerate(classes) if value == c]
        mandatory = p - 1 if p - 1 in groups[c] else None
        pool = [value for value in groups[c] if value != mandatory]
        values = rng.sample(pool, len(positions) - int(mandatory is not None))
        if mandatory is not None:
            values.append(mandatory)
        rng.shuffle(values)
        for i, value in zip(positions, values):
            codes[i] = value

    planted = [sorted(rng.sample(palettes[c], 4)) for c in classes]
    lists = []
    for i, c in enumerate(classes):
        row = planted[i] + _nonmatching(rng, palettes, c, set(planted[i]), 11)
        rng.shuffle(row)
        lists.append(row)

    graph_neighbors = _neighbors(n, edges)
    trap = None
    front_vertices = []
    if n >= 10:
        eligible = [v for v in range(n) if len(graph_neighbors[v]) == 3 and
                    len({classes[w] for w in graph_neighbors[v]}) == 2]
        trap = rng.choice(eligible)
        own, ca, cb = classes[trap], (classes[trap] + 1) % 3, (classes[trap] + 2) % 3
        trap_a, trap_b = rng.sample(palettes[ca], 5), rng.sample(palettes[cb], 6)
        lists[trap] = planted[trap] + trap_a + trap_b
        rng.shuffle(lists[trap])
        na = [v for v in graph_neighbors[trap] if classes[v] == ca]
        nb = [v for v in graph_neighbors[trap] if classes[v] == cb]
        if len(na) == 2:
            pair, single, pair_colours, single_colours = na, nb[0], trap_b[:4], trap_a[:4]
        else:
            pair, single, pair_colours, single_colours = nb, na[0], trap_a[:4], trap_b[:4]
        split = rng.randrange(1, 4)
        fronts = {
            pair[0]: pair_colours[:split] + planted[trap][:4 - split],
            pair[1]: pair_colours[split:] + planted[trap][4 - split:],
            single: single_colours,
        }
        for vertex, front in fronts.items():
            rng.shuffle(front)
            rest = _nonmatching(rng, palettes, classes[vertex],
                                set(front) | set(planted[vertex]), 7)
            rng.shuffle(rest)
            lists[vertex] = list(front) + planted[vertex] + rest
        front_vertices = list(graph_neighbors[trap])
        rng.shuffle(front_vertices)

    if trap is None:
        presentation = list(range(n))
        rng.shuffle(presentation)
    else:
        middle = [v for v in range(n) if v != trap and v not in front_vertices]
        rng.shuffle(middle)
        presentation = front_vertices + middle + [trap]
    index = {old: new for new, old in enumerate(presentation)}
    new_edges = sorted(tuple(sorted((index[u], index[v]))) for u, v in edges)
    new_codes = [codes[old] for old in presentation]
    answer = [[new_codes[i], list(planted[presentation[i]])]
              for i in sorted(range(n), key=lambda j: new_codes[j])]
    return {
        "paper": "arXiv:2602.13970",
        "n": n,
        "m": 1,
        "list_size": 15,
        "demand": 4,
        "label_modulus": p,
        "vertices": new_codes,
        "edges": [list(edge) for edge in new_edges],
        "lists": [lists[old] for old in presentation],
        "answer": answer,
        "construction": {"primitive_root": generator},
    }


def render(inst):
    lines = [
        "FOUR-FOLD LIST COLOURING", "",
        "Choose exactly four distinct colours for every graph vertex from that "
        "vertex's displayed 15-element list. For every edge, the chosen sets at "
        "its endpoints must be disjoint (share no colour).", "",
        "The graph is simple, planar, and triangle-free. Edge endpoints below are "
        "0-based row indices; the integer vertex label in each row is the label "
        "to use in the answer. A displayed list is a set, so printed order has no "
        "mathematical significance.", "",
        f"Vertices: {inst['n']}",
        "Vertex and colour labels are positive integers; equality is exact.",
        "Edges: " + json.dumps(inst["edges"], separators=(",", ":")), "",
        "Vertex table:",
    ]
    for i, (code, row) in enumerate(zip(inst["vertices"], inst["lists"])):
        lines.append(f"  row {i}: vertex {code}; list " +
                     json.dumps(row, separators=(",", ":")))
    lines += [
        "",
        "Give one [vertex,[c1,c2,c3,c4]] entry for every vertex, sorted by "
        "increasing vertex label. The four distinct colour integers must be from "
        "that vertex's list; write them in increasing order.",
        "Give your final answer inside <answer></answer> tags as one JSON array.",
        "Example: <answer>[[3,[1,4,7,9]],[8,[2,5,6,10]]]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    """Parse tagged JSON, tolerating prose, whitespace, and markdown fences."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    bodies = list(reversed(tagged))
    if not bodies:
        return None
    for body in bodies:
        cleaned = re.sub(r"^\s*```(?:json)?\s*", "", body, flags=re.I)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        attempts = [cleaned.strip()]
        # Models occasionally transcribe every row but omit the final outer
        # bracket. Recover exactly that one unambiguous JSON typo.
        if cleaned.count("[") == cleaned.count("]") + 1:
            attempts.append(cleaned.strip() + "]")
        for candidate in attempts:
            try:
                value = json.loads(candidate)
            except (ValueError, TypeError):
                continue
            if (isinstance(value, list) and value and
                    all(isinstance(entry, list) and len(entry) == 2 for entry in value)):
                return value
    return None


def _plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def verify(inst, answer):
    """Verify any valid witness without reading inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer array must not be empty"
    if len(answer) != inst["n"]:
        return False, f"expected {inst['n']} vertex entries, received {len(answer)}"
    positions = {code: i for i, code in enumerate(inst["vertices"])}
    chosen = {}
    for row_number, entry in enumerate(answer):
        if not isinstance(entry, list) or len(entry) != 2:
            return False, f"entry {row_number} must be [vertex,[four colours]]"
        code, colours = entry
        if not _plain_int(code) or code not in positions:
            return False, f"entry {row_number} has an unknown vertex label"
        vertex = positions[code]
        if vertex in chosen:
            return False, f"vertex label {code} is repeated"
        if not isinstance(colours, list) or len(colours) != 4:
            return False, f"vertex {code} must have exactly four colours"
        if not all(_plain_int(colour) for colour in colours):
            return False, f"vertex {code} has a non-integer colour"
        if len(set(colours)) != 4:
            return False, f"vertex {code} repeats a colour"
        if any(colour not in inst["lists"][vertex] for colour in colours):
            return False, f"vertex {code} selects colour outside its list"
        chosen[vertex] = set(colours)
    for u, v in inst["edges"]:
        if chosen[u] & chosen[v]:
            return False, (f"adjacent vertices {inst['vertices'][u]} and "
                           f"{inst['vertices'][v]} share a colour")
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly after enforcing per-vertex size and membership."""
    positions = {code: i for i, code in enumerate(inst["vertices"])}
    return [[code, sorted(rng.sample(inst["lists"][positions[code]], 4))]
            for code in sorted(positions)]


def search_space(inst):
    return math.comb(15, 4) ** inst["n"]


def enumerate_all(inst):
    if search_space(inst) > 2_000_000:
        return None
    choices = [list(itertools.combinations(row, 4)) for row in inst["lists"]]
    count = 0
    for product in itertools.product(*choices):
        answer = [[inst["vertices"][i], list(product[i])] for i in range(inst["n"])]
        count += int(verify(inst, answer)[0])
    return count


def _canonical_payload(inst):
    n = inst["n"]
    edges = {tuple(sorted(edge)) for edge in inst["edges"]}
    neighbors = _neighbors(n, edges)
    lists = [set(row) for row in inst["lists"]]
    freq = {}
    for row in lists:
        for colour in row:
            freq[colour] = freq.get(colour, 0) + 1
    vertices = []
    for v in range(n):
        vertices.append([
            len(neighbors[v]),
            sorted(len(lists[v] & lists[w]) for w in neighbors[v]),
            sorted(len(lists[v] & lists[w]) for w in range(n)
                   if w != v and w not in neighbors[v]),
            sorted(freq[x] for x in lists[v]),
        ])
    edge_data = sorted([
        min(len(neighbors[u]), len(neighbors[v])),
        max(len(neighbors[u]), len(neighbors[v])),
        len(lists[u] & lists[v]),
        sorted(freq[x] for x in lists[u] & lists[v]),
    ] for u, v in edges)
    pairs = sorted([int((u, v) in edges), len(lists[u] & lists[v])]
                   for u in range(n) for v in range(u + 1, n))
    return {"n": n, "degrees": sorted(map(len, neighbors)),
            "frequencies": sorted(freq.values()), "vertices": sorted(vertices),
            "edges": edge_data, "pairs": pairs}


def canonical_key(inst):
    blob = json.dumps(_canonical_payload(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    current = int(params.get("n", 0))
    harder = 10 if current == 5 else ((current + 9) // 10 + 1) * 10
    if 5 * harder > 256:
        return "cap_bound"
    result = dict(params)
    result["n"] = harder
    return result


def _answer_from_sets(inst, chosen):
    positions = {code: i for i, code in enumerate(inst["vertices"])}
    return [[code, sorted(chosen[positions[code]])] for code in sorted(positions)]


def _frequencies(inst):
    result = {}
    for row in inst["lists"]:
        for colour in row:
            result[colour] = result.get(colour, 0) + 1
    return result


def _attack_outlier(inst):
    freq = _frequencies(inst)
    chosen = {v: set(sorted(inst["lists"][v], key=lambda x: (freq[x], x))[:4])
              for v in range(inst["n"])}
    return _answer_from_sets(inst, chosen)


def _attack_smallest(inst):
    return _answer_from_sets(inst, {v: set(sorted(inst["lists"][v])[:4])
                                    for v in range(inst["n"])})


def _attack_greedy(inst):
    neighbors = _neighbors(inst["n"], inst["edges"])
    chosen = {}
    for v in range(inst["n"]):
        used = set().union(*(chosen[w] for w in neighbors[v] if w in chosen))
        available = [x for x in inst["lists"][v] if x not in used]
        if len(available) < 4:
            return None
        chosen[v] = set(available[:4])
    return _answer_from_sets(inst, chosen)


def _attack_restarts(inst, seed, restarts=256):
    rng, freq = random.Random(seed), _frequencies(inst)
    pools = [sorted(row, key=lambda x: (freq[x], x))[:9] for row in inst["lists"]]
    last = None
    for _ in range(restarts):
        last = _answer_from_sets(inst, {v: set(rng.sample(pools[v], 4))
                                               for v in range(inst["n"])})
        if verify(inst, last)[0]:
            return last
    return last


def _reference_csp(inst, limit=50_000_000):
    n, neighbors = inst["n"], _neighbors(inst["n"], inst["edges"])
    domains = [[sum(1 << x for x in choice) for choice in itertools.combinations(row, 4)]
               for row in inst["lists"]]
    assigned, operations, nodes = {}, 0, 0
    started = time.perf_counter()

    def search(current):
        nonlocal operations, nodes
        if len(assigned) == n:
            return True
        v = min((x for x in range(n) if x not in assigned),
                key=lambda x: (len(current[x]), -len(neighbors[x]), x))
        for mask in current[v]:
            nodes += 1
            bad = False
            for w in neighbors[v]:
                if w in assigned:
                    operations += 1
                    if mask & assigned[w]:
                        bad = True
                        break
            if bad:
                continue
            assigned[v] = mask
            next_domains, viable = list(current), True
            for w in neighbors[v]:
                if w in assigned:
                    continue
                filtered = []
                for candidate in next_domains[w]:
                    operations += 1
                    if not candidate & mask:
                        filtered.append(candidate)
                if not filtered:
                    viable = False
                    break
                next_domains[w] = filtered
            if viable and search(next_domains):
                return True
            del assigned[v]
            if operations >= limit:
                return False
        return False

    solved = search(domains)
    elapsed = time.perf_counter() - started
    answer = None
    if solved:
        sets = {v: {x for x in range(inst["label_modulus"])
                    if assigned[v] & (1 << x)} for v in range(n)}
        answer = _answer_from_sets(inst, sets)
    return answer, {"operations": operations, "nodes": nodes,
                    "wall_clock_sec": elapsed, "solved": solved}


def _coset_witness(inst):
    p, g = inst["label_modulus"], _primitive_root(inst["label_modulus"])
    classes, value = {}, 1
    for exponent in range(p - 1):
        classes[value] = exponent % 3
        value = value * g % p
    rows = []
    for code, colours in zip(inst["vertices"], inst["lists"]):
        selected = sorted(x for x in colours if classes[x] == classes[code])
        if len(selected) != 4:
            return None
        rows.append([code, selected])
    return sorted(rows)


def _compact_operations(inst):
    return 2 * (inst["label_modulus"] - 1) + inst["n"]


def _adjacent_corruption(inst):
    answer = copy.deepcopy(inst["answer"])
    rows = {code: colours for code, colours in answer}
    for u, v in inst["edges"]:
        common = set(inst["lists"][u]) & set(inst["lists"][v])
        if not common:
            continue
        colour = min(common)
        for code in (inst["vertices"][u], inst["vertices"][v]):
            if colour not in rows[code]:
                rows[code][-1] = colour
                rows[code] = sorted(set(rows[code]))
                if len(rows[code]) < 4:
                    extra = next(x for x in inst["lists"][
                        inst["vertices"].index(code)] if x not in rows[code])
                    rows[code].append(extra)
        return [[code, rows[code]] for code, _ in answer]
    raise AssertionError("no adjacent lists overlap")


def _relabeled(inst, seed):
    rng, n = random.Random(seed), inst["n"]
    out = copy.deepcopy(inst)
    old_at_new = list(range(n)); rng.shuffle(old_at_new)
    new_of_old = {old: new for new, old in enumerate(old_at_new)}
    old_codes, new_codes = list(inst["vertices"]), list(inst["vertices"])
    rng.shuffle(new_codes); code_map = dict(zip(old_codes, new_codes))
    used = sorted({x for row in inst["lists"] for x in row})
    renamed = list(used); rng.shuffle(renamed); colour_map = dict(zip(used, renamed))
    out["vertices"] = [code_map[inst["vertices"][old]] for old in old_at_new]
    out["lists"] = []
    for old in old_at_new:
        row = [colour_map[x] for x in inst["lists"][old]]
        rng.shuffle(row); out["lists"].append(row)
    out["edges"] = [list(sorted((new_of_old[u], new_of_old[v])))
                    for u, v in inst["edges"]]
    rng.shuffle(out["edges"])
    out["answer"] = [[code_map[code], [colour_map[x] for x in colours]]
                     for code, colours in inst["answer"]]
    rng.shuffle(out["answer"])
    return out


def _atoms(value):
    if isinstance(value, dict):
        return sum(_atoms(x) for x in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atoms(x) for x in value)
    return 1


def selftest():
    report = {"track": TRACK, "paper": "arXiv:2602.13970",
              "shipping_difficulty": SHIPPING_DIFFICULTY,
              "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY])}
    failures, checks, json_checks = [], 0, 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append([preset, seed, why])
            json_checks += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {"pass": not failures and json_checks == checks,
        "checks": checks, "json_native_roundtrips": json_checks, "failures": failures}

    ship = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])
    corrupted = {"empty": []}
    item = copy.deepcopy(ship["answer"]); item[0][1].pop(); corrupted["drop_colour"] = item
    item = copy.deepcopy(ship["answer"]); item[0][1], item[1][1] = item[1][1], item[0][1]; corrupted["swap_sets"] = item
    item = copy.deepcopy(ship["answer"]); item[0][1][-1] = item[0][1][0]; corrupted["duplicate_colour"] = item
    item = copy.deepcopy(ship["answer"]); item[0][0] = ship["label_modulus"] + 1; corrupted["out_of_range"] = item
    corrupted["adjacent_collision"] = _adjacent_corruption(ship)
    cases = {}
    for name, candidate in corrupted.items():
        ok, why = verify(ship, candidate); cases[name] = {"rejected": not ok, "reason": why}
    reasons = {row["reason"] for row in cases.values()}
    report["G2_rejects_corruption"] = {"pass": all(x["rejected"] for x in cases.values()) and len(reasons) == len(cases),
        "cases": cases, "distinct_reasons": len(reasons)}

    serialized = json.dumps(ship["answer"], separators=(",", ":"))
    parsed = parse_answer("Prose\n```json\n<answer>\n" + serialized + "\n</answer>\n```")
    report["G3_round_trip"] = {"pass": parsed == ship["answer"] and parse_answer("garbage") is None,
                                "parsed_equals_answer": parsed == ship["answer"]}

    rng, total, hits = random.Random(260213970), 200_000, 0
    started = time.perf_counter()
    for _ in range(total):
        hits += int(verify(ship, random_candidate(ship, rng))[0])
    elapsed = time.perf_counter() - started
    report["G4_guess_resistance"] = {"pass": hits / total < 1e-6, "hits": hits, "total": total,
        "observed_probability": hits / total, "structure_aware_space": str(search_space(ship)),
        "prior": "uniform four-subset of every advertised list", "wall_clock_sec": elapsed}

    attacks = {
        "outlier_global_frequency": lambda inst, seed: _attack_outlier(inst),
        "greedy_input_order": lambda inst, seed: _attack_greedy(inst),
        "random_frequency_restart_256": lambda inst, seed: _attack_restarts(inst, seed),
        "obvious_smallest_labels": lambda inst, seed: _attack_smallest(inst),
    }
    results = {name: {"successes": 0, "attempts": 8} for name in attacks}
    reference = []
    for offset in range(8):
        inst, seed = make_instance(seed=10000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]), 10000 + offset
        for name, attack in attacks.items():
            candidate = attack(inst, seed)
            results[name]["successes"] += int(candidate is not None and verify(inst, candidate)[0])
        candidate, stats = _reference_csp(inst)
        stats["verified"] = candidate is not None and verify(inst, candidate)[0]
        reference.append(stats)
    solved = sum(row["verified"] for row in reference)
    reference_summary = {
        "name": "generic MRV forward-checking CSP search",
        "complexity": "O(1365^n) worst-case time; O(1365*n) domain space",
        "wall_clock_sec": sum(x["wall_clock_sec"] for x in reference) / 8,
        "operations": round(sum(x["operations"] for x in reference) / 8),
        "nodes": round(sum(x["nodes"] for x in reference) / 8),
        "solves": f"{solved}/8, as expected",
    }
    all_failed = all(row["successes"] == 0 for row in results.values())
    report["G5_density_and_baseline"] = {"pass": solved == 8, "shipping_preset": SHIPPING_DIFFICULTY,
        "density": {"kind": "sampled_structure_aware", "hits": hits, "total": total,
                    "observed_fraction": hits / total}, "exact_solution_count": enumerate_all(ship),
        "baseline": reference_summary}
    report["G6_adversary_panel"] = {"pass": all_failed and solved == 8,
        "attacks": results, "reference_algorithm": reference_summary}

    bits = {name: search_space(make_instance(seed=77, **params)).bit_length()
            for name, params in DIFFICULTY.items()}
    doubled = make_instance(n=2 * ship["n"], seed=707)
    compact = _coset_witness(ship)
    report["G7_scales"] = {"pass": all(a < b for a, b in zip(bits.values(), list(bits.values())[1:]))
        and verify(doubled, doubled["answer"])[0] and verify(ship, compact)[0],
        "search_space_bits_by_preset": bits, "shipping_n": ship["n"], "doubled_n": doubled["n"],
        "doubled_planted_verifies": verify(doubled, doubled["answer"])[0],
        "compact_route_verifies": verify(ship, compact)[0], "next_escalation": escalate(DIFFICULTY[SHIPPING_DIFFICULTY])}

    invariance = carried = 0; key_failures = []
    for seed in range(20):
        original = make_instance(n=30, seed=20000 + seed)
        transformed = _relabeled(original, 30000 + seed)
        if canonical_key(original) == canonical_key(transformed): invariance += 1
        else: key_failures.append(seed)
        carried += int(verify(transformed, transformed["answer"])[0])
    unrelated = {canonical_key(make_instance(n=30, seed=40000 + seed)) for seed in range(20)}
    report["G8_canonical_key"] = {"pass": invariance == carried == len(unrelated) == 20,
        "invariance_checks": invariance, "carried_witness_checks": carried,
        "distinct_unrelated_keys": len(unrelated), "unrelated_instances": 20,
        "transformations": ["vertex-index permutation", "vertex-label permutation",
            "global colour permutation", "edge-order permutation", "per-list order permutation"],
        "failures": key_failures}

    chars, tokens, elements = len(serialized), (len(serialized) + 3) // 4, _atoms(ship["answer"])
    operations = _compact_operations(ship)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hr = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    pr = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {"pass": chars <= 2000 and elements <= 256 and operations <= 300
        and tokens == PROBLEM_PROFILE["max_answer_tokens"], "arms": arms,
        "hinted_minus_placebo": hr - pr, "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": tokens, "answer_elements": elements,
        "intended_route_operations": operations, "caps_only_gate": True}
    report["all_pass"] = all(value.get("pass", True) for key, value in report.items()
                                if key.startswith("G") and isinstance(value, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
