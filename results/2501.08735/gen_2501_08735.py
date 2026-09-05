"""Verified maximum-matching-cut instances from arXiv:2501.08735.

The construction is exactly the graph used in Theorem 23.  An Exact 3-Cover
instance is converted to a bipartite graph of radius at most 3 and diameter at
most 4; an exact cover of a 3n-element universe gives a matching cut of the
maximum possible size 6n.  Here the exact-cover rows are assembled in cyclic
layers.  Every layer is a known cover, so generation never searches for the
certificate.
"""

from __future__ import annotations
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
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bipartite graph of radius at most 3 and diameter at most 4",
        "complete bipartite core K_(3n,3n)",
        "labelled K_(3,3) set gadgets",
        "maximum matching cut",
    ],
    "verification_operations": [
        "exact graph-template comparison",
        "integer vertex-colour assignment",
        "crossing-edge scan",
        "per-vertex crossing-degree comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Theorem 23: Exact 3-Cover is equivalent to a matching "
        "cut of size 6n in the constructed bipartite radius-3, diameter-4 graph"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The tag difference from the first element of a gadget to its second "
        "is constant modulo n along each hidden exact-cover layer; without "
        "recognizing it, one must search the exact-cover incidence structure."
    ),
    "hardness_basis": (
        "Track B: Algorithm X with minimum-column branching has worst-case "
        "O(layers^n) search and averaged 2.90 s, 82,276 recursive nodes, and "
        "26,936,781 exact incidence tests at shipping n=35,layers=6; "
        "while the generated subclass also has an O(n*layers) tag-difference "
        "bucketing algorithm measured at about 0.00007 s and 210 modular "
        "subtractions at n=35,layers=6; a no-tool solver must first recognize "
        "and then execute that compact route."
    ),
    "max_answer_tokens": 32,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "demo": {"n": 5, "layers": 2},
    "easy": {"n": 25, "layers": 4},
    "medium": {"n": 31, "layers": 5},
    "hard": {"n": 35, "layers": 6},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Within one cut-producing layer, the tag difference from a gadget's first "
    "element to its second is constant modulo n."
)
PLACEBO_HINT = (
    "Keep the three element blocks separate and check every selected gadget ID "
    "carefully before submitting."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list containing exactly n distinct gadget IDs; the "
        "candidate language chooses exactly one of the layers gadgets incident "
        "with each element of block A, and therefore has layers^n members."
    ),
    "bounds": {
        "answer_length": "n",
        "entry_min": 0,
        "entry_max": "n*layers-1",
        "one_gadget_per_A_element": True,
        "candidate_count": "layers^n",
    },
}

NOTES = r"""
Definition and construction license. Section 1 defines a matching cut as a
matching that is exactly the set of edges crossing a nontrivial vertex
partition. Section 2, Observation 1 gives the equivalent valid red-blue
colouring. Section 4, Theorem 23 reduces Exact 3-Cover on a 3q-element universe
to Maximum Matching Cut. Its graph contains a K_(3q,3q) core and one K_(3,3)
for each triple, has radius at most 3 and diameter at most 4, and has a matching
cut of size 6q exactly when the triples have an exact cover. The selected
K_(3,3) gadgets are therefore a concise, directly executable certificate for
the paper's graph object, not a graph invented outside the paper.

STEP 0 and the track decision. Theorem 23 proves NP-hardness for bipartite
radius-3, diameter-4 graphs, while Theorems 12 and 15 make Maximum Matching Cut
polynomial on bipartite graphs of diameter at most 3 and radius at most 2,
respectively. This generator stays in Theorem 23's graph regime. Nevertheless,
its layered distribution has a public polynomial algorithm: bucket gadgets by
their cyclic tag difference. A Track A distributional claim would therefore be
false. On Track B the domain-standard mechanical reference is Algorithm X with
minimum-column branching; selftest measures its nodes, incidence tests and
wall time at shipping size. Once the cyclic invariant is seen, at most
n*layers modular subtractions expose a whole layer.

Generation and certificate provenance. Independently shuffled tags identify
three copies of Z/nZ. For each sampled pair of shifts (s,t), the n triples
(a, a+s, a+t) form a perfect cover. All layers are generated identically and
all are valid; the stored certificate is one uniformly selected layer after
gadget IDs are shuffled. No exact-cover or matching-cut routine is invoked by
make_instance. Theorem 23 then carries that cover to a cut of size 6n.

Attack controls. Every universe element occurs in exactly layers gadgets and
every graph gadget is the same K_(3,3), eliminating degree and gadget-size
outliers. Gadget IDs and element IDs are independently shuffled. The panel
tests the lowest-ID outlier rule, a nonbacktracking greedy cover, 256 uniform
structure-aware restarts, and a plausible by-hand rule that incorrectly treats
cyclic tag differences as ordinary integer differences. Algorithm X is kept
outside attacks because Track B expects it to succeed. canonical_key discards
input names and ordering and canonically normalizes the recovered shift pairs
under independent tag translations, common multiplication by a unit, and a
swap of the second and third element blocks.
""".strip()


G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000


def _validate_parameters(n, seed, layers):
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if (isinstance(layers, bool) or not isinstance(layers, int)
            or not 2 <= layers < n):
        raise ValueError("layers must be an integer in [2,n-1]")


def _expected_edges(n, triples):
    """Return the exact edge set of Theorem 23's graph."""
    universe_size = 3 * n
    edges = []

    # Complete bipartite core K_(3n,3n).
    for left in range(universe_size):
        for right_local in range(universe_size):
            edges.append((left, universe_size + right_local))

    # A K_(3,3) and six incidence edges for every triple.
    gadget_start = 2 * universe_size
    for gadget_id, triple in enumerate(triples):
        base = gadget_start + 6 * gadget_id
        side_one = (base, base + 1, base + 2)
        side_two = (base + 3, base + 4, base + 5)
        for u in side_one:
            for v in side_two:
                edges.append((u, v))
        for position, element in enumerate(triple):
            edges.append((element, side_one[position]))
            edges.append((universe_size + element, side_two[position]))
    return edges


def _assemble_instance(n, layers, tags, triples, answer):
    edges = _expected_edges(n, triples)
    universe_size = 3 * n
    vertex_count = 2 * universe_size + 6 * len(triples)
    return {
        "family": "maximum_matching_cut_theorem_23",
        "n": n,
        "layers": layers,
        "universe_size": universe_size,
        "tags": list(tags),
        "triples": [list(t) for t in triples],
        "vertex_count": vertex_count,
        "edges": [list(e) for e in edges],
        "target_cut_size": 6 * n,
        "answer": sorted(answer),
    }


def make_instance(n, seed=0, **params):
    """Inverse-generate layered covers and carry one through Theorem 23."""
    unknown = set(params) - {"layers"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    layers = params.get("layers", 6)
    _validate_parameters(n, seed, layers)
    rng = random.Random(seed)

    # tags[vertex ID] is its coordinate in its copy of Z/nZ.  Shuffling each
    # copy independently removes any useful relation between public IDs.
    tags = []
    for _ in range(3):
        block = list(range(n))
        rng.shuffle(block)
        tags.extend(block)
    inverse = [[0] * n for _ in range(3)]
    for block in range(3):
        for local_id in range(n):
            inverse[block][tags[block * n + local_id]] = block * n + local_id

    second_shifts = rng.sample(range(1, n), layers)
    third_shifts = rng.sample(range(n), layers)
    rows = []
    for layer, (second_shift, third_shift) in enumerate(
            zip(second_shifts, third_shifts)):
        for coordinate in range(n):
            triple = (
                inverse[0][coordinate],
                inverse[1][(coordinate + second_shift) % n],
                inverse[2][(coordinate + third_shift) % n],
            )
            rows.append((triple, layer))
    rng.shuffle(rows)
    chosen_layer = rng.randrange(layers)
    triples = [triple for triple, _ in rows]
    answer = [j for j, (_, layer) in enumerate(rows) if layer == chosen_layer]
    return _assemble_instance(n, layers, tags, triples, answer)


def _format_element_block(inst, block):
    n = inst["n"]
    start = block * n
    return " ".join(
        f"{element}:{inst['tags'][element]}"
        for element in range(start, start + n)
    )


def render(inst):
    """Render the complete graph problem, its compact encoding, and output rule."""
    n = inst["n"]
    lines = [
        "MAXIMUM MATCHING CUT IN A BOUNDED-RADIUS BIPARTITE GRAPH",
        "",
        "A matching cut of a graph is the complete set of edges crossing some "
        "partition of the vertices into two nonempty colours, with every vertex "
        "incident to at most one crossing edge. Its size is its number of "
        "crossing edges.",
        "",
        f"Here n={n}. The universe has 3n={3*n} elements, numbered 0 through "
        f"{3*n-1}, in three blocks A, B, C. Each element also has a tag in "
        f"0..{n-1}; tag arithmetic is modulo n. The exact ID:tag tables are:",
        "A " + _format_element_block(inst, 0),
        "B " + _format_element_block(inst, 1),
        "C " + _format_element_block(inst, 2),
        "",
        "The graph is specified exactly as follows. It has core vertices L_i "
        "and R_i for every universe element i, with every L_i adjacent to every "
        "R_k. For each listed gadget j with ordered triple (a,b,c), add vertices "
        "P_j,0..P_j,2 and Q_j,0..Q_j,2; join every P_j,t to every Q_j,u; and add "
        "the six edges L_a-P_j,0, L_b-P_j,1, L_c-P_j,2, R_a-Q_j,0, "
        "R_b-Q_j,1, R_c-Q_j,2. There are no other edges. This is a bipartite "
        "graph of radius at most 3 and diameter at most 4.",
        "",
        "Gadgets (0-based gadget_id: a b c):",
    ]
    lines.extend(
        f"{j}: {triple[0]} {triple[1]} {triple[2]}"
        for j, triple in enumerate(inst["triples"])
    )
    lines.extend([
        "",
        f"Submit exactly {n} distinct gadget IDs. They encode this vertex "
        "partition: all core vertices and every unselected gadget are red; all "
        "six vertices of every selected gadget are blue. The required crossing "
        f"edges must form a matching cut of size {6*n}, which is maximum for "
        "this graph. The order of IDs does not matter and repetitions are not "
        "allowed.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON list "
        "of 0-based gadget IDs.",
        "Example: <answer>[3, 17, 42]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Parse a JSON integer list from the required tags; never raise."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        # Tolerate the common model form "1, 2, 3" inside the tags.
        try:
            if not re.fullmatch(r"\s*-?\d+(?:\s*,\s*-?\d+)*\s*", payload):
                return None
            value = [int(piece.strip()) for piece in payload.split(",")]
        except Exception:
            return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def _selection_is_cover(inst, answer):
    if len(answer) != inst["n"] or len(set(answer)) != len(answer):
        return False
    if any(isinstance(j, bool) or not isinstance(j, int)
           or j < 0 or j >= len(inst["triples"]) for j in answer):
        return False
    seen = set()
    for gadget_id in answer:
        triple = inst["triples"][gadget_id]
        if any(element in seen for element in triple):
            return False
        seen.update(triple)
    return len(seen) == inst["universe_size"]


def _template_ok(inst):
    try:
        if inst["universe_size"] != 3 * inst["n"]:
            return False
        if len(inst["triples"]) != inst["n"] * inst["layers"]:
            return False
        if inst["vertex_count"] != 6 * inst["n"] + 6 * len(inst["triples"]):
            return False
        expected = _expected_edges(inst["n"], inst["triples"])
        actual = [tuple(edge) for edge in inst["edges"]]
        return actual == expected
    except (KeyError, TypeError, ValueError):
        return False


def verify(inst, answer):
    """Verify any encoded maximum matching cut without consulting the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst.get("n"):
        return False, f"expected exactly {inst.get('n')} gadget IDs"
    if any(isinstance(j, bool) or not isinstance(j, int) for j in answer):
        return False, "every gadget ID must be an integer"
    gadget_count = len(inst.get("triples", []))
    if any(j < 0 or j >= gadget_count for j in answer):
        return False, f"gadget IDs must lie in 0..{gadget_count-1}"
    if len(set(answer)) != len(answer):
        return False, "gadget IDs must be distinct"
    if not _template_ok(inst):
        return False, "instance does not match the stated Theorem 23 graph"

    universe_size = inst["universe_size"]
    gadget_start = 2 * universe_size
    colours = bytearray(inst["vertex_count"])
    for gadget_id in answer:
        base = gadget_start + 6 * gadget_id
        colours[base:base + 6] = b"\x01" * 6

    crossing_degree = [0] * inst["vertex_count"]
    crossing_count = 0
    for u, v in inst["edges"]:
        if colours[u] != colours[v]:
            crossing_count += 1
            crossing_degree[u] += 1
            crossing_degree[v] += 1
            if crossing_degree[u] > 1 or crossing_degree[v] > 1:
                bad = u if crossing_degree[u] > 1 else v
                return False, f"vertex {bad} has more than one crossing edge"
    if crossing_count != inst["target_cut_size"]:
        return False, (
            f"cut has {crossing_count} crossing edges, expected maximum "
            f"{inst['target_cut_size']}"
        )
    return True, "ok"


def _by_first_block(inst):
    rows = [[] for _ in range(inst["n"])]
    for gadget_id, triple in enumerate(inst["triples"]):
        rows[triple[0]].append(gadget_id)
    return rows


def random_candidate(inst, rng):
    """Sample uniformly after enforcing one selected row for every A element."""
    rows = _by_first_block(inst)
    return sorted(rng.choice(rows[element]) for element in range(inst["n"]))


def search_space(inst):
    return inst["layers"] ** inst["n"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    rows = _by_first_block(inst)
    count = 0
    for candidate in itertools.product(*rows):
        if _selection_is_cover(inst, list(candidate)):
            count += 1
    return count


def _canonical_signatures(inst):
    n = inst["n"]
    tags = inst["tags"]
    signatures = {
        ((tags[b] - tags[a]) % n, (tags[c] - tags[a]) % n)
        for a, b, c in inst["triples"]
    }
    units = [u for u in range(1, n) if math.gcd(u, n) == 1]
    forms = []
    for anchor_x, anchor_y in signatures:
        translated = [((x - anchor_x) % n, (y - anchor_y) % n)
                      for x, y in signatures]
        for unit in units:
            scaled = sorted(((unit * x) % n, (unit * y) % n)
                            for x, y in translated)
            forms.append(tuple(scaled))
            forms.append(tuple(sorted((y, x) for x, y in scaled)))
    return min(forms)


def canonical_key(inst):
    """Canonicalize generated instances under their exact presentation symmetries."""
    payload = {
        "n": inst["n"],
        "layers": inst["layers"],
        "signatures": _canonical_signatures(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """Grow the candidate space, preferring more decoy layers at fixed answer size."""
    current = {k: v for k, v in params.items() if not k.startswith("_")}
    n = current.get("n")
    layers = current.get("layers", 6)
    if not isinstance(n, int) or not isinstance(layers, int):
        return None
    if n * (layers + 1) <= 290 and layers + 1 < n:
        return {"n": n, "layers": layers + 1}

    current_log_space = n * math.log(max(2, layers))
    # Once the fixed-answer axis is exhausted, enlarge n while keeping the
    # intended modular-arithmetic route below the G9 cap.
    for new_n in range(n + 1, 101):
        max_layers = min(new_n - 1, 290 // new_n)
        for new_layers in range(max_layers, 1, -1):
            if new_n * math.log(new_layers) > current_log_space + 1e-12:
                return {"n": new_n, "layers": new_layers}
    return "cap_bound"


def _attack_lowest_id(inst):
    return sorted(min(row) for row in _by_first_block(inst))


def _attack_greedy(inst):
    rows = _by_first_block(inst)
    used = set()
    answer = []
    order = sorted(range(inst["n"]), key=lambda a: inst["tags"][a])
    for a in order:
        feasible = [j for j in rows[a]
                    if inst["triples"][j][1] not in used
                    and inst["triples"][j][2] not in used]
        choices = feasible or rows[a]
        chosen = min(choices, key=lambda j: (
            inst["tags"][inst["triples"][j][1]],
            inst["tags"][inst["triples"][j][2]], j))
        answer.append(chosen)
        used.update(inst["triples"][chosen][1:])
    return sorted(answer)


def _attack_random_restarts(inst, seed, restarts=256):
    rng = random.Random(seed)
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if _selection_is_cover(inst, last):
            return last
    return last


def _ordinary_difference_attack(inst):
    """Plausible hand attack that misses the modular wraparound."""
    rows = _by_first_block(inst)
    anchor = min(range(len(inst["triples"])))
    aa, ab, ac = inst["triples"][anchor]
    target_b = inst["tags"][ab] - inst["tags"][aa]
    target_c = inst["tags"][ac] - inst["tags"][aa]
    answer = []
    for a in range(inst["n"]):
        chosen = min(rows[a], key=lambda j: (
            abs((inst["tags"][inst["triples"][j][1]] - inst["tags"][a])
                - target_b)
            + abs((inst["tags"][inst["triples"][j][2]] - inst["tags"][a])
                  - target_c),
            j,
        ))
        answer.append(chosen)
    return sorted(answer)


def _structured_reference(inst):
    """The O(n*layers) algorithm available only after seeing the invariant."""
    n = inst["n"]
    buckets = {}
    operations = 0
    for gadget_id, (a, b, _c) in enumerate(inst["triples"]):
        signature = (inst["tags"][b] - inst["tags"][a]) % n
        operations += 1
        buckets.setdefault(signature, []).append(gadget_id)
    for signature in sorted(buckets):
        candidate = sorted(buckets[signature])
        if len(candidate) == n and _selection_is_cover(inst, candidate):
            return candidate, operations
    return None, operations


def _algorithm_x(inst, node_cap=None):
    """Minimum-column Algorithm X; returns answer, nodes, incidence tests."""
    universe_size = inst["universe_size"]
    triples = inst["triples"]
    incident = [[] for _ in range(universe_size)]
    for gadget_id, triple in enumerate(triples):
        for element in triple:
            incident[element].append(gadget_id)

    available = bytearray(b"\x01" * len(triples))
    uncovered = bytearray(b"\x01" * universe_size)
    solution = []
    nodes = 0
    tests = 0

    def recurse(left):
        nonlocal nodes, tests
        nodes += 1
        if node_cap is not None and nodes > node_cap:
            return None
        if left == 0:
            return list(solution)

        candidates = None
        for element in range(universe_size):
            if not uncovered[element]:
                continue
            current = []
            for gadget_id in incident[element]:
                tests += 1
                if available[gadget_id]:
                    current.append(gadget_id)
            if not current:
                return False
            if candidates is None or len(current) < len(candidates):
                candidates = current

        for gadget_id in candidates:
            triple = triples[gadget_id]
            tests += 3
            if not all(uncovered[element] for element in triple):
                continue
            removed = []
            for element in triple:
                uncovered[element] = 0
                for other in incident[element]:
                    tests += 1
                    if available[other]:
                        available[other] = 0
                        removed.append(other)
            solution.append(gadget_id)
            result = recurse(left - 3)
            if result is None or result is not False:
                return result
            solution.pop()
            for other in removed:
                available[other] = 1
            for element in triple:
                uncovered[element] = 1
        return False

    result = recurse(universe_size)
    return (result if isinstance(result, list) else None), nodes, tests


def _relabel_instance(inst, rng):
    """Apply ground/gadget relabellings and affine tag symmetries."""
    n = inst["n"]
    old_to_new = {}
    for block in range(3):
        new_positions = list(range(block * n, (block + 1) * n))
        rng.shuffle(new_positions)
        for offset, old in enumerate(range(block * n, (block + 1) * n)):
            old_to_new[old] = new_positions[offset]

    units = [u for u in range(1, n) if math.gcd(u, n) == 1]
    unit = rng.choice(units)
    translations = [rng.randrange(n) for _ in range(3)]
    tags = [0] * (3 * n)
    for old, new in old_to_new.items():
        block = old // n
        tags[new] = (unit * inst["tags"][old] + translations[block]) % n

    order = list(range(len(inst["triples"])))
    rng.shuffle(order)
    triples = [
        tuple(old_to_new[element] for element in inst["triples"][old_id])
        for old_id in order
    ]
    # Swap the B and C copies.  This is a genuine hypergraph/graph isomorphism,
    # not merely an input reorder, and exercises the coordinate swap normalized
    # by canonical_key.
    tags = tags[:n] + tags[2 * n:3 * n] + tags[n:2 * n]
    triples = [(a, c - n, b + n) for a, b, c in triples]
    old_answer = set(inst["answer"])
    answer = [new_id for new_id, old_id in enumerate(order)
              if old_id in old_answer]
    return _assemble_instance(n, inst["layers"], tags, triples, answer)


def selftest():
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every named preset and three seeds, plus JSON-native certificates.
    planted_checks = 0
    json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            planted_checks += int(ok)
            json_checks += int(json.loads(json.dumps(inst["answer"]))
                               == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": planted_checks == 12 and json_checks == 12,
        "verified": planted_checks,
        "attempts": 12,
        "json_native": json_checks,
    }

    shipping = make_instance(seed=314159,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five materially different corruptions and five distinct diagnostics.
    planted = list(shipping["answer"])
    rows = _by_first_block(shipping)
    first_a = shipping["triples"][planted[0]][0]
    replacement = next(j for j in rows[first_a] if j not in set(planted))
    replace_one = list(planted)
    replace_one[0] = replacement
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate_one": planted[:-1] + [planted[0]],
        "out_of_range": planted[:-1] + [len(shipping["triples"])],
        "replace_one": replace_one,
    }
    corruption_reasons = {}
    rejected = 0
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejected += int(not ok)
        corruption_reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": rejected == 5 and len(set(corruption_reasons.values())) == 5,
        "rejected": rejected,
        "attempts": 5,
        "distinct_reasons": len(set(corruption_reasons.values())),
        "reasons": corruption_reasons,
    }

    # G3: realistic prose, markdown inside tags, and garbage behavior.
    model_reply = (
        "I used the cyclic layers and checked the crossing degrees.\n"
        "<answer>```json\n" + json.dumps(shipping["answer"]) +
        "\n```</answer>\nThe requested list is above."
    )
    parsed = parse_answer(model_reply)
    round_trip_ok = parsed == shipping["answer"]
    report["G3_round_trip"] = {
        "pass": round_trip_ok and parse_answer("no tagged answer") is None,
        "model_style_round_trip": round_trip_ok,
        "garbage_returns_none": parse_answer("<answer>oops</answer>") is None,
    }

    # G4/G5 density: candidates already enforce one row per A element.
    guess_rng = random.Random(8675309)
    guess_samples = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_samples):
        if _selection_is_cover(shipping, random_candidate(shipping, guess_rng)):
            guess_hits += 1
    density_elapsed = time.perf_counter() - density_start
    guess_fraction = guess_hits / guess_samples
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "samples": guess_samples,
        "observed_fraction": guess_fraction,
        "structure_aware_space": search_space(shipping),
        "space_bits": search_space(shipping).bit_length(),
        "prior": "uniform independent layer choice for each A element",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_valid_count = enumerate_all(demo)

    # One full mechanical reference run at shipping size for G5.
    reference_start = time.perf_counter()
    reference_answer, reference_nodes, reference_tests = _algorithm_x(shipping)
    reference_elapsed = time.perf_counter() - reference_start
    reference_ok = (reference_answer is not None
                    and verify(shipping, reference_answer)[0])
    baseline_start = time.perf_counter()
    baseline_candidate = _attack_random_restarts(shipping, 424242, 256)
    baseline_elapsed = time.perf_counter() - baseline_start
    baseline_success = _selection_is_cover(shipping, baseline_candidate)
    report["G5_density_and_baseline"] = {
        "pass": (guess_fraction < 1e-6 and demo_valid_count is not None
                 and reference_ok and not baseline_success),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_samples,
        "shipping_solution_fraction": guess_fraction,
        "density_wall_clock_sec": round(density_elapsed, 6),
        "demo_exact_valid_answers": demo_valid_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack_restarts": 256,
        "strongest_failing_attack_wall_clock_sec": round(baseline_elapsed, 6),
        "reference_nodes": reference_nodes,
        "reference_incidence_tests": reference_tests,
        "reference_wall_clock_sec": round(reference_elapsed, 6),
    }

    # G6: four failed in-context probes, plus successful references kept apart.
    attack_names = (
        "outlier_lowest_gadget_id",
        "greedy_no_backtracking",
        "random_restart_256",
        "by_hand_ordinary_difference",
    )
    successes = {name: 0 for name in attack_names}
    attempts = {name: 0 for name in attack_names}
    algorithm_x_successes = 0
    structured_successes = 0
    total_nodes = 0
    total_tests = 0
    total_structured_operations = 0
    reference_times = []
    structured_times = []
    for seed in range(101, 109):
        inst = make_instance(seed=seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_lowest_gadget_id": _attack_lowest_id(inst),
            "greedy_no_backtracking": _attack_greedy(inst),
            "random_restart_256": _attack_random_restarts(
                inst, seed ^ 0x5A5A, 256),
            "by_hand_ordinary_difference": _ordinary_difference_attack(inst),
        }
        for name, candidate in candidates.items():
            attempts[name] += 1
            successes[name] += int(_selection_is_cover(inst, candidate))

        t0 = time.perf_counter()
        found, nodes, tests = _algorithm_x(inst)
        reference_times.append(time.perf_counter() - t0)
        total_nodes += nodes
        total_tests += tests
        algorithm_x_successes += int(
            found is not None and verify(inst, found)[0])

        structured_start = time.perf_counter()
        structured, operations = _structured_reference(inst)
        structured_times.append(time.perf_counter() - structured_start)
        total_structured_operations += operations
        structured_successes += int(
            structured is not None and verify(inst, structured)[0])

    attacks = {
        name: {"successes": successes[name], "attempts": attempts[name]}
        for name in attack_names
    }
    all_failed = all(item["successes"] == 0 and item["attempts"] >= 8
                     for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (all_failed and algorithm_x_successes == 8
                 and structured_successes == 8),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "minimum-column Algorithm X",
            "complexity": "O(layers^n) worst case",
            "wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations": total_tests,
            "recursive_nodes": total_nodes,
            "solves": f"{algorithm_x_successes}/8, as expected",
        },
        "efficient_generated_subclass_algorithm": {
            "name": "cyclic tag-difference bucketing",
            "complexity": "O(n*layers)",
            "operations": total_structured_operations,
            "operations_mean": total_structured_operations / 8,
            "wall_clock_sec_mean": round(sum(structured_times) / 8, 6),
            "wall_clock_sec_max": round(max(structured_times), 6),
            "solves": f"{structured_successes}/8, as expected",
        },
    }

    # G7: the same construction doubles in n and preserves its certificate.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=73, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] > shipping["n"]
                 and search_space(doubled) > search_space(shipping)),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_space_bits": search_space(shipping).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
    }

    # G8: ID/gadget reorderings, affine clue symmetries, and compositions.
    invariant_checks = 0
    carried_checks = 0
    for seed in range(20):
        inst = make_instance(seed=2000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        transformed = inst
        for round_no in range(3):
            transformed = _relabel_instance(
                transformed, random.Random(90000 + 17 * seed + round_no))
            invariant_checks += 1
            if canonical_key(transformed) == original_key:
                carried_checks += int(
                    verify(transformed, transformed["answer"])[0])
    unrelated_keys = [
        canonical_key(make_instance(
            seed=5000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (invariant_checks == 60 and carried_checks == 60
                 and distinct_keys == 20),
        "invariant_relabellings": invariant_checks,
        "invariant_successes": carried_checks,
        "carried_certificate_verifies": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "independent ground-element renumbering",
            "gadget-ID reordering",
            "independent tag translations",
            "common multiplication by a unit modulo n",
            "swap of the B and C element blocks",
            "threefold compositions of all transformations",
        ],
    }

    # G9(a,b) are diagnostics.  Only answer/operation caps gate this report.
    compact = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(compact)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_operations = shipping["n"] * shipping["layers"]
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": round(hinted_rate - placebo_rate, 6),
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
