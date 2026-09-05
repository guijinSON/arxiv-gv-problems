"""Verified problem generator for arXiv:2604.27535.

The paper studies rainbow cycles in a family of graphs.  Here a cycle is given,
and the witness is the injection assigning a distinct family member to every
cycle edge.  Instances are inverse-generated as cyclic shifts of one binary
availability word, then embedded in graph families satisfying the paper's
Ore-type condition.

Only the Python standard library is used.  Importing this module performs no
I/O, consumes no global randomness, and prints nothing.
"""

from __future__ import annotations

import collections
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
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "family of simple graphs on a common vertex set",
        "specified cycle in the common vertex set",
        "edge-to-graph injection",
    ],
    "verification_operations": [
        "distinct graph-index check",
        "exact graph-edge membership lookup",
        "cycle-edge coverage check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The edge-availability rows are cyclic shifts of one word with a unique "
        "marker; without aligning those shifts, a solver must carry out a full matching."
    ),
    "hardness_basis": (
        "Track B: Hopcroft--Karp finds the rainbow injection in "
        "O(k^2+E*sqrt(k)) time after reading the k-by-k availability table; at "
        "the shipping preset k=64 the measured reference run inspects 4096 table "
        "bits and uses about 8,000 total bit/edge operations, while marker alignment "
        "uses 134 exact index operations after the cyclic-shift symmetry is seen."
    ),
    "max_answer_tokens": 65,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {"hard": {"n": 128, "marker_len": 4}}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Each availability row contains the same cyclic marker at a different rotation."
)
PLACEBO_HINT = (
    "Keep the edge positions and graph indices aligned carefully in the final list."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list assigning one distinct relevant graph index to each of k=n/2 "
        "ordered cycle edges; 4 <= k <= 256 and graph indices lie in 0..n-1."
    ),
    "bounds": {
        "max_cycle_edges": 256,
        "max_graph_index": 511,
        "distinct_indices": 1,
        "edge_order_fixed": 1,
    },
}

# Filled from the three isolated harden.py runs after the local gates pass.
G9_DIAGNOSTIC = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_ORACLE_STATUS = "not_run"

NOTES = """
Section 1 fixes the exact witness: a rainbow subgraph requires an injection phi
from its edges to graph indices, with every edge present in its assigned graph.
Theorem 1.6 fixes the native promise and range: sigma(G)>=n gives rainbow cycles
of every length 4..n through every vertex, apart from the identical balanced
complete-bipartite exception.  The proof's first step invokes the earlier
rainbow-Hamilton-cycle theorem and then uses cycle switches; it does not provide
a small closed formula for phi on an arbitrary input.

The generator samples a binary necklace and two relabellings first.  It assigns
cycle edge j the graph at the marker origin in row j, then defines that row to
be a cyclic shift of the necklace.  Universal filler vertices make every graph
have minimum degree at least n/2, hence the paper's stronger family Ore value is
at least n.  No completed instance is searched for its witness.

All relevant graph columns have the same frequency, so degree and frequency
outliers disappear.  Rejection sampling is used only to discard presentation
relabelings on which the explicitly tested smallest-ID, largest-ID, or dihedral
heuristics happen to succeed; the planted injection remains the already sampled
marker origin throughout.  Random graph-index relabelling removes positional
clues.  The successful Hopcroft--Karp reference algorithm is reported separately
because this is Track B.
""".strip()


def _coprime_steps(k):
    return [a for a in range(2, k - 1) if math.gcd(a, k) == 1]


def _marker_word(k, marker_len, rng):
    """A weight-about-k/4 necklace with one uniquely longest cyclic 1-run."""
    if k == 4:
        return {0, 1}
    target_weight = max(marker_len, k // 4)
    chosen = set(range(marker_len))
    candidates = list(range(marker_len + 1, k - 1))
    rng.shuffle(candidates)
    for q in candidates:
        if len(chosen) >= target_weight:
            break
        if (q - 1) % k in chosen or (q + 1) % k in chosen:
            continue
        chosen.add(q)
    if len(chosen) != target_weight:
        raise ValueError("marker parameters leave too little room for isolated bits")
    return chosen


def _rows_from(k, shifts, word):
    return [
        "".join("1" if (q - shift) % k in word else "0" for q in range(k))
        for shift in shifts
    ]


def _basic_instance(n, marker_len, target_cycle, graph_order, rows, answer, meta):
    return {
        "family": "ore_rainbow_cycle_injection",
        "n_vertices": n,
        "n_graphs": n,
        "cycle_length": n // 2,
        "target_cycle": list(target_cycle),
        "graph_column_order": list(graph_order),
        "availability_rows": list(rows),
        "construction": dict(meta),
        "answer": list(answer),
    }


def make_instance(n, seed=0, marker_len=4, **params):
    """Inverse-generate a certified rainbow injection.

    There are n vertices and n graphs.  The prescribed cycle uses k=n/2
    vertices.  Every graph contains all edges incident with a filler vertex;
    only its prescribed-cycle edges vary according to the displayed matrix.
    """
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    k = n // 2
    if k > 256:
        raise ValueError("n/2 must be at most 256")
    if not isinstance(marker_len, int) or not 2 <= marker_len <= max(2, k // 3):
        raise ValueError("marker_len must be an integer in [2, floor(k/3)]")

    rng = random.Random(seed)
    vertices = list(range(n))
    rng.shuffle(vertices)
    target_cycle = vertices[:k]

    # graph_order[q] is the actual graph index represented by matrix column q.
    graph_ids = list(range(n))
    rng.shuffle(graph_ids)
    graph_order = graph_ids[:k]

    # The answer is sampled as the marker origins.  The filters below only alter
    # the presentation parameters; they never discover a witness by searching.
    for presentation_attempt in range(2000):
        word = _marker_word(k, marker_len, rng)
        steps = _coprime_steps(k)
        step = rng.choice(steps) if steps else 1
        offset = rng.randrange(k)
        shifts = [(step * j + offset) % k for j in range(k)]
        rows = _rows_from(k, shifts, word)
        answer = [graph_order[q] for q in shifts]
        inst = _basic_instance(
            n,
            marker_len,
            target_cycle,
            graph_order,
            rows,
            answer,
            {
                "marker_len": marker_len,
                "word_weight": len(word),
                "presentation_attempt": presentation_attempt,
            },
        )
        if k < 8:
            return inst
        # Avoid accidental wins by the cheap attacks.  This filters a graph
        # presentation, not a witness: answer was fixed before rows were emitted.
        if _attack_degree_rank(inst) is not None:
            continue
        if _attack_greedy(inst, largest=False) is not None:
            continue
        if _attack_greedy(inst, largest=True) is not None:
            continue
        if _attack_dihedral(inst) is not None:
            continue
        return inst
    raise RuntimeError("could not find an attack-resistant presentation")


def render(inst):
    n = inst["n_vertices"]
    k = inst["cycle_length"]
    cycle = inst["target_cycle"]
    graph_order = inst["graph_column_order"]
    rows = inst["availability_rows"]
    edge_lines = []
    for j, bits in enumerate(rows):
        u, v = cycle[j], cycle[(j + 1) % k]
        edge_lines.append(f"  edge {j:>2} = {{{u},{v}}}: {bits}")
    matrix = "\n".join(edge_lines)
    text = f"""Rainbow injection for a prescribed cycle

There are {n} simple undirected graphs G_0,...,G_{n-1} on the common vertex
set V={{0,...,{n-1}}}.  The following {k} distinct vertices, in cyclic order,
define the prescribed cycle C (the last vertex is joined back to the first):
{cycle}

Every vertex outside C is a filler vertex.  In every G_i, every unordered pair
having at least one filler endpoint is an edge.  Among pairs whose two endpoints
are on C, the only possible edges are the {k} edges of C.  Their memberships in
the graphs are given exactly by the binary table below.

The table has {k} columns.  Column q denotes the actual graph index at position q
in this list (positions are 0-based):
{graph_order}

In a row, bit q is 1 exactly when that cycle edge belongs to the graph named at
column position q; bit 0 means it does not.  Graph indices absent from the column
list contain none of the prescribed cycle edges.

{matrix}

A rainbow copy of this prescribed cycle is an injection phi from its edge
positions 0,...,{k-1} to graph indices 0,...,{n-1}, such that edge j belongs to
G_phi(j).  Find one.  Your answer must be one JSON list [g_0,...,g_{k-1}] of
exactly {k} pairwise distinct integers, where g_j=phi(j).  Order is mandatory,
repetitions are forbidden, and all bounds are inclusive at 0 and exclusive at
{n}.

Example syntax only: <answer>[7, 2, 11, 5]</answer>"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    text += (
        "\n\nGive your final answer inside <answer></answer> tags, as the JSON list "
        "specified above.\nOutput nothing else inside the tags."
    )
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    bodies = list(reversed(tagged))
    if not bodies:
        bodies = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    for body in bodies:
        body = body.strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    # Deliberately never inspect inst["answer"].
    n = inst.get("n_graphs")
    k = inst.get("cycle_length")
    graph_order = inst.get("graph_column_order")
    rows = inst.get("availability_rows")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k:
        return False, f"expected exactly {k} graph indices"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every graph index must be an integer"
    if any(x < 0 or x >= n for x in answer):
        return False, "graph index out of range"
    if len(set(answer)) != k:
        return False, "graph indices must be pairwise distinct"
    position = {graph_id: q for q, graph_id in enumerate(graph_order)}
    for j, graph_id in enumerate(answer):
        q = position.get(graph_id)
        if q is None or rows[j][q] != "1":
            return False, f"edge position {j} is absent from graph {graph_id}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the solver-visible space: permutations of relevant graphs."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    candidate = list(inst["graph_column_order"])
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return math.factorial(inst["cycle_length"])


def enumerate_all(inst):
    k = inst["cycle_length"]
    if math.factorial(k) > 200_000:
        return None
    count = 0
    for candidate in itertools.permutations(inst["graph_column_order"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _dihedral_rows(rows):
    k = len(rows)
    for shift in range(k):
        yield rows[shift:] + rows[:shift]
    rev = list(reversed(rows))
    for shift in range(k):
        yield rev[shift:] + rev[:shift]


def canonical_key(inst):
    """Canonical under vertex/graph relabelling and cycle rotation/reversal.

    Graph columns may be arbitrarily permuted, so each candidate row orientation
    is represented by the sorted multiset of its column incidence bit-vectors.
    """
    rows = inst["availability_rows"]
    k = inst["cycle_length"]
    n = inst["n_graphs"]
    forms = []
    for oriented in _dihedral_rows(rows):
        columns = ["".join(oriented[j][q] for j in range(k)) for q in range(k)]
        columns.extend(["0" * k] * (n - k))
        forms.append("|".join(sorted(columns)))
    payload = f"{n}:{k}:" + min(forms)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    p = dict(params)
    p.pop("_preset", None)
    marker_len = int(p.get("marker_len", 4))
    n = int(p["n"])
    # First shorten the visual marker at fixed answer length.  Only then enlarge
    # the cycle, stopping before either answer or intended-operation cap binds.
    if marker_len > 3:
        p["marker_len"] = marker_len - 1
        return p
    if n // 2 < 128:
        p["n"] = n + 32
        p["marker_len"] = 3
        return p
    return "cap_bound"


def _attack_degree_rank(inst):
    rows = inst["availability_rows"]
    k = inst["cycle_length"]
    graph_order = inst["graph_column_order"]
    row_order = sorted(range(k), key=lambda j: (rows[j].count("1"), j))
    col_order = sorted(
        range(k),
        key=lambda q: (sum(rows[j][q] == "1" for j in range(k)), graph_order[q]),
    )
    candidate = [None] * k
    for j, q in zip(row_order, col_order):
        candidate[j] = graph_order[q]
    return candidate if verify(inst, candidate)[0] else None


def _attack_greedy(inst, largest=False):
    graph_order = inst["graph_column_order"]
    rows = inst["availability_rows"]
    unused = set(graph_order)
    answer = []
    for row in rows:
        choices = [graph_order[q] for q, bit in enumerate(row) if bit == "1" and graph_order[q] in unused]
        if not choices:
            return None
        pick = max(choices) if largest else min(choices)
        unused.remove(pick)
        answer.append(pick)
    return answer if verify(inst, answer)[0] else None


def _attack_dihedral(inst):
    k = inst["cycle_length"]
    graph_order = inst["graph_column_order"]
    for direction in (1, -1):
        for shift in range(k):
            candidate = [graph_order[(direction * j + shift) % k] for j in range(k)]
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _attack_random(inst, seed, restarts=512):
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _marker_decode(inst):
    """Use the unique longest cyclic 1-run in every row as a common marker."""
    rows = inst["availability_rows"]
    graph_order = inst["graph_column_order"]
    k = len(rows)
    answer = []
    bit_inspections = 0
    for row in rows:
        starts = []
        for q in range(k):
            bit_inspections += 2
            if row[q] == "1" and row[(q - 1) % k] == "0":
                length = 0
                while length < k and row[(q + length) % k] == "1":
                    bit_inspections += 1
                    length += 1
                starts.append((length, q))
        if not starts:
            return None, 0, bit_inspections
        best_len = max(length for length, _ in starts)
        best = [q for length, q in starts if length == best_len]
        if len(best) != 1:
            return None, 0, bit_inspections
        answer.append(graph_order[best[0]])
    # After the pattern is recognized: one cyclic-index normalization and one
    # column-to-graph lookup per row, plus six setup operations.
    exact_operations = 2 * k + 6
    return answer, exact_operations, bit_inspections


def _hopcroft_karp(inst):
    """Reference matching algorithm; return witness and counted primitive work."""
    rows = inst["availability_rows"]
    graph_order = inst["graph_column_order"]
    k = len(rows)
    operations = k * k  # reading the full displayed table
    adjacency = [[q for q, bit in enumerate(row) if bit == "1"] for row in rows]
    pair_u = [-1] * k
    pair_v = [-1] * k
    dist = [0] * k

    def bfs():
        nonlocal operations
        queue = collections.deque()
        for u in range(k):
            operations += 1
            if pair_u[u] < 0:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = -1
        found = False
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                operations += 1
                mate = pair_v[v]
                if mate < 0:
                    found = True
                elif dist[mate] < 0:
                    dist[mate] = dist[u] + 1
                    queue.append(mate)
        return found

    def dfs(u):
        nonlocal operations
        for v in adjacency[u]:
            operations += 1
            mate = pair_v[v]
            if mate < 0 or (dist[mate] == dist[u] + 1 and dfs(mate)):
                pair_u[u] = v
                pair_v[v] = u
                return True
        dist[u] = -1
        return False

    while bfs():
        progress = 0
        for u in range(k):
            if pair_u[u] < 0 and dfs(u):
                progress += 1
        if not progress:
            break
    if any(q < 0 for q in pair_u):
        return None, operations
    return [graph_order[q] for q in pair_u], operations


def _permute_graphs(inst, old_to_new):
    n = inst["n_graphs"]
    if sorted(old_to_new) != list(range(n)):
        raise ValueError("old_to_new must be a graph-index permutation")
    out = dict(inst)
    out["graph_column_order"] = [old_to_new[i] for i in inst["graph_column_order"]]
    out["answer"] = [old_to_new[i] for i in inst["answer"]]
    return out


def _permute_vertices(inst, old_to_new):
    n = inst["n_vertices"]
    if sorted(old_to_new) != list(range(n)):
        raise ValueError("old_to_new must be a vertex permutation")
    out = dict(inst)
    out["target_cycle"] = [old_to_new[v] for v in inst["target_cycle"]]
    return out


def _rotate_cycle(inst, shift=0, reverse=False):
    k = inst["cycle_length"]
    vertices = inst["target_cycle"]
    rows = inst["availability_rows"]
    answer = inst["answer"]
    if reverse:
        vertex_indices = [(shift - j) % k for j in range(k)]
        row_indices = [(shift - j - 1) % k for j in range(k)]
    else:
        vertex_indices = [(shift + j) % k for j in range(k)]
        row_indices = [(shift + j) % k for j in range(k)]
    out = dict(inst)
    out["target_cycle"] = [vertices[j] for j in vertex_indices]
    out["availability_rows"] = [rows[j] for j in row_indices]
    out["answer"] = [answer[j] for j in row_indices]
    return out


def _permute_columns(inst, old_position_to_new):
    k = inst["cycle_length"]
    if sorted(old_position_to_new) != list(range(k)):
        raise ValueError("old_position_to_new must be a column permutation")
    order = [None] * k
    for old, new in enumerate(old_position_to_new):
        order[new] = inst["graph_column_order"][old]
    rows = []
    for row in inst["availability_rows"]:
        bits = [None] * k
        for old, new in enumerate(old_position_to_new):
            bits[new] = row[old]
        rows.append("".join(bits))
    out = dict(inst)
    out["graph_column_order"] = order
    out["availability_rows"] = rows
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "generation_route": "inverse generation by cyclic-shift composition",
        "ore_reason": "every graph has minimum degree at least n/2",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping)
    ans = inst["answer"]
    swapped = None
    for a in range(len(ans)):
        for b in range(a + 1, len(ans)):
            trial = list(ans)
            trial[a], trial[b] = trial[b], trial[a]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = list(reversed(ans))
    duplicate = list(ans)
    duplicate[1] = duplicate[0]
    out_of_range = list(ans)
    out_of_range[0] = inst["n_graphs"]
    corruptions = {}
    for name, bad in (
        ("empty", []),
        ("drop_one", ans[:-1]),
        ("swap_two", swapped),
        ("duplicate", duplicate),
        ("out_of_range", out_of_range),
    ):
        ok, why = verify(inst, bad)
        corruptions[name] = {"rejected": not ok, "reason": why}
    reasons = [v["reason"] for v in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values()) and len(set(reasons)) == 5,
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "The rotations align consistently.\n```json\n<answer>\n"
        + json.dumps(ans)
        + "\n</answer>\n```\nThis is the requested injection."
    )
    parsed = parse_answer(model_style)
    renderer_example_parses = parse_answer(render(inst)) is not None
    report["G3_round_trip"] = {
        "pass": parsed == ans and renderer_example_parses,
        "model_style_round_trip": parsed == ans,
        "renderer_example_parses": renderer_example_parses,
    }

    guess_rng = random.Random(987654321)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "estimated_probability": guess_rate,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform permutations of exactly the k graph indices that occur in the table",
    }

    attack_names = [
        "outlier_row_column_frequency",
        "greedy_smallest_graph",
        "greedy_largest_graph",
        "random_restart_512",
        "diagonal_or_reversed_shift_ansatz",
    ]
    attack_successes = {name: 0 for name in attack_names}
    attack_walls = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_walls = []
    compact_successes = 0
    compact_operations = []
    compact_inspections = []
    for seed in range(8):
        cur = make_instance(seed=4000 + seed, **shipping)
        probes = {
            "outlier_row_column_frequency": lambda: _attack_degree_rank(cur),
            "greedy_smallest_graph": lambda: _attack_greedy(cur, largest=False),
            "greedy_largest_graph": lambda: _attack_greedy(cur, largest=True),
            "random_restart_512": lambda: _attack_random(cur, 9000 + seed),
            "diagonal_or_reversed_shift_ansatz": lambda: _attack_dihedral(cur),
        }
        for name, probe in probes.items():
            started = time.perf_counter()
            got = probe()
            attack_walls[name] += time.perf_counter() - started
            attack_successes[name] += int(got is not None and verify(cur, got)[0])

        started = time.perf_counter()
        ref, ref_ops = _hopcroft_karp(cur)
        reference_walls.append(time.perf_counter() - started)
        reference_operations.append(ref_ops)
        reference_successes += int(ref is not None and verify(cur, ref)[0])

        compact, compact_ops, inspections = _marker_decode(cur)
        compact_operations.append(compact_ops)
        compact_inspections.append(inspections)
        compact_successes += int(compact is not None and verify(cur, compact)[0])

    attacks = {
        name: {
            "successes": attack_successes[name],
            "attempts": 8,
            "wall_clock_sec": attack_walls[name],
        }
        for name in attack_names
    }
    all_failed = all(v["successes"] == 0 for v in attacks.values())
    ref_avg_ops = sum(reference_operations) / len(reference_operations)
    ref_avg_wall = sum(reference_walls) / len(reference_walls)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_successes == 8 and demo_count is not None and guess_rate < 1e-6,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_solution_fraction_estimate": guess_rate,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec": ref_avg_wall,
        "baseline_operations": ref_avg_ops,
        "baseline_max_operations": max(reference_operations),
        "baseline_table_bit_inspections": inst["cycle_length"] ** 2,
        "strongest_failing_attack": "random_restart_512",
        "strongest_failing_attack_restarts": 8 * 512,
        "strongest_failing_attack_wall_clock_sec": attack_walls["random_restart_512"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Hopcroft--Karp bipartite matching after full table scan",
            "complexity": "O(k^2 + E*sqrt(2k))",
            "wall_clock_sec": ref_avg_wall,
            "operations": ref_avg_ops,
            "max_operations": max(reference_operations),
            "table_bit_inspections": inst["cycle_length"] ** 2,
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "align the unique longest cyclic marker",
            "exact_operations": max(compact_operations),
            "bit_inspections_by_literal_implementation": max(compact_inspections),
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=333, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "shipping_cycle_length": inst["cycle_length"],
        "doubled_n": doubled_params["n"],
        "doubled_cycle_length": doubled["cycle_length"],
        "shipping_space_bits": search_space(inst).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    witness_checks = 0
    keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **shipping)
        keys.append(canonical_key(base))
        rr = random.Random(70_000 + seed)
        vp = list(range(base["n_vertices"]))
        gp = list(range(base["n_graphs"]))
        cp = list(range(base["cycle_length"]))
        rr.shuffle(vp)
        rr.shuffle(gp)
        rr.shuffle(cp)
        variants = [
            _permute_vertices(base, vp),
            _permute_graphs(base, gp),
            _permute_columns(base, cp),
            _rotate_cycle(base, shift=7 % base["cycle_length"], reverse=True),
        ]
        composed = _permute_columns(_permute_graphs(_permute_vertices(base, vp), gp), cp)
        variants.append(_rotate_cycle(composed, shift=3, reverse=False))
        for moved in variants:
            invariant_checks += 1
            if canonical_key(moved) != canonical_key(base):
                continue
            ok, _ = verify(moved, moved["answer"])
            witness_checks += int(ok)
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 100 and witness_checks == 100 and len(set(keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "unrelated_distinct": len(set(keys)),
        "unrelated_attempts": 20,
        "symmetries": [
            "arbitrary vertex relabelling",
            "arbitrary graph-index relabelling",
            "arbitrary display-column reordering",
            "cycle rotation and reversal",
            "compositions of these maps",
        ],
    }

    blobs = [json.dumps(make_instance(seed=s, **shipping)["answer"]) for s in range(20)]
    answer_chars = max(map(len, blobs))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(ans)
    compact_checks = []
    compact_counts = []
    bit_counts = []
    for seed in range(20):
        cur = make_instance(seed=80_000 + seed, **shipping)
        got, ops, bits = _marker_decode(cur)
        compact_checks.append(got is not None and verify(cur, got)[0])
        compact_counts.append(ops)
        bit_counts.append(bits)
    arms = {key: dict(value) for key, value in G9_DIAGNOSTIC.items()}
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else None
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else None
    intended_ops = max(compact_counts)
    report["G9_no_tool_suitability"] = {
        "pass": (
            answer_chars <= 2000
            and answer_elements <= 256
            and intended_ops <= 300
            and all(compact_checks)
        ),
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": (
            "hardened" if arms["hinted"]["attempts"] and not arms["hinted"]["solved"]
            else "too_easy" if arms["hinted"]["solved"]
            else G9_ORACLE_STATUS
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "pattern_bit_inspections_by_literal_implementation": max(bit_counts),
        "compact_route_verifies": f"{sum(compact_checks)}/{len(compact_checks)}",
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
