"""Verified problem generator for arXiv:1612.03280.

The generated object is the two-clique signed interval graph used in Theorem 5.
A sparse bipartite matching instance is encoded as the negative-edge graph of
the second clique.  A perfect matching is an independent set there (and hence
the paper's permitted degenerate biclique), which decodes to a signed coloring.
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
import statistics
import time
from collections import Counter, deque


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The planted transversal is characterized by a common value of column minus "
    "row modulo n."
)
PLACEBO_HINT: str = (
    "A valid transversal is characterized by careful consistency between each "
    "displayed row and selected column."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "signed interval graph given by two disjoint interval cliques",
        "positive and negative signed edges",
        "compressed signed coloring certificate",
    ],
    "verification_operations": [
        "exact interval intersection by endpoint comparison",
        "signed-edge comparison",
        "exact modular integer comparison",
        "decoded color-pair consistency check",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Theorem 5: an arbitrary MBC graph is made the negative "
        "signature of one clique in a two-clique signed interval graph"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The planted perfect matching has one invariant modular displacement; "
        "without recognizing it, one must execute a general augmenting-path search."
    ),
    "hardness_basis": (
        "Track B: Hopcroft--Karp solves the encoded bipartite matching problem in "
        "O(E sqrt(V)); at attempted n=127,d=12 it took a median 3,820.5 edge scans "
        "and 0.000196 seconds over eight seeds, while the compact common-displacement "
        "route uses at most n+3d=163 modular operations."
    ),
    "max_answer_tokens": 141,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 5, "degree": 2},
    "easy": {"n": 61, "degree": 8},
    "medium": {"n": 89, "degree": 10},
    "hard": {"n": 127, "degree": 12},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An ordered list with exactly one listed second-clique vertex ID for each "
        "displayed row.  At parameters (n,d), every position has exactly d choices, "
        "so the bounded language has d^n strings.  IDs are decimal integers from "
        "1 through nd; repeated columns are syntactically allowed but fail verification."
    ),
    "bounds": {
        "max_rows": 254,
        "max_choices_per_row": 24,
        "max_answer_atoms": 254,
        "index_base": 1,
    },
}

NOTES: str = (
    "Section 1 (the paragraph preceding INTSCOL) fixes the Naserasr--Rollova--"
    "Sopena coloring definition: adjacent colors differ and equal unordered color "
    "pairs cannot occur on edges of different signs, after switching. Section 3, "
    "Theorem 5 supplies the exact two-disjoint-cliques construction and explicitly "
    "turns a biclique of size k into a coloring with 2N-k colors. Section 2 defines "
    "a biclique to include an independent set, so a matching conflict graph is a "
    "legal source object. Theorem 4 makes S-clique search polynomial for bounded "
    "numbers of maximal cliques; that easy family is not used. Proposition 2 also "
    "identifies chromatic-number-two caterpillar instances, which are avoided. "
    "Plants and decoys are identically placed within each row and have the same "
    "one-cell marginals. Random row and cell order defeats positional rules; random "
    "decoys defeat degree and greedy rules; the planted shift excludes the three "
    "fixed offsets tried by the elementary affine ansatz. Hopcroft--Karp is disclosed "
    "as the successful Track B reference algorithm."
)


# The named hard preset held on the bare prompt but failed the polarity-flipped
# structural-hint gate.  The placebo arm was not run after that gated failure.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 3, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy",
}


def _sample_distinct_offsets(rng, n, degree, planted):
    offsets = {planted}
    while len(offsets) < degree:
        offsets.add(rng.randrange(n))
    return offsets


def make_instance(n, seed=0, degree=8, **params) -> dict:
    """Inverse-generate a perfect matching, then apply Theorem 5.

    The certificate is never found by solving the generated graph: a modular shift
    is sampled first, its n matching cells are inserted, and only then are decoy
    cells and presentation permutations sampled.
    """
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer")
    if degree < 2 or degree >= n:
        raise ValueError("degree must satisfy 2 <= degree < n")

    rng = random.Random(seed)
    # Uniformity matters: conditioned on the unordered d offsets in a row, the
    # planted offset is uniformly one of them.  Cell order and IDs are shuffled
    # later, so no per-cell statistic distinguishes plant from decoy.
    planted_shift = rng.randrange(n)

    offsets_by_row = {}
    for row in range(n):
        offsets_by_row[row] = _sample_distinct_offsets(
            rng, n, degree, planted_shift
        )

    # Put three rows whose offset intersection is exactly the plant first.  This
    # does not expose which cell is planted inside any row, but it bounds the
    # arithmetic needed after the structural insight.
    prefix = None
    row_ids = list(range(n))
    for _ in range(5000):
        a, b, c = rng.sample(row_ids, 3)
        if offsets_by_row[a] & offsets_by_row[b] & offsets_by_row[c] == {planted_shift}:
            prefix = [a, b, c]
            break
    if prefix is None:  # astronomically unlikely at supported d << n
        for a, b, c in itertools.combinations(row_ids, 3):
            if offsets_by_row[a] & offsets_by_row[b] & offsets_by_row[c] == {planted_shift}:
                prefix = [a, b, c]
                break
    if prefix is None:
        raise RuntimeError("could not construct a three-row displacement witness")

    rest = [r for r in row_ids if r not in set(prefix)]
    rng.shuffle(rest)
    display_order = prefix + rest

    total_cells = n * degree
    visible_ids = list(range(1, total_cells + 1))
    rng.shuffle(visible_ids)
    id_iter = iter(visible_ids)
    rows = []
    planted_id_by_row = {}
    for row in display_order:
        cells = []
        for offset in offsets_by_row[row]:
            vertex_id = next(id_iter)
            col = (row + offset) % n
            cells.append({"id": vertex_id, "col": col})
            if offset == planted_shift:
                planted_id_by_row[row] = vertex_id
        rng.shuffle(cells)
        rows.append({"row": row, "cells": cells})

    answer = [planted_id_by_row[entry["row"]] for entry in rows]
    return {
        "family": "signed coloring of a two-clique interval graph",
        "n": n,
        "degree": degree,
        "component_size": total_cells,
        "target_colors": 2 * total_cells - n,
        "interval_model": {
            "first_clique": [0, 1],
            "second_clique": [2, 3],
            "closed": True,
        },
        "rows": rows,
        "answer": answer,
    }


def _cell_maps(inst):
    by_id = {}
    row_of = {}
    col_of = {}
    for position, row in enumerate(inst["rows"]):
        for cell in row["cells"]:
            vertex_id = cell["id"]
            by_id[vertex_id] = cell
            row_of[vertex_id] = position
            col_of[vertex_id] = cell["col"]
    return by_id, row_of, col_of


def _answer_text(answer):
    return ", ".join(str(value) for value in answer)


def render(inst) -> str:
    n = inst["n"]
    degree = inst["degree"]
    size = inst["component_size"]
    target = inst["target_colors"]
    lines = []
    for position, row in enumerate(inst["rows"], 1):
        cells = "  ".join(
            f"{cell['id']}@{cell['col']}" for cell in row["cells"]
        )
        lines.append(f"{position:3d}. row {row['row']}: {cells}")

    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""SIGNED COLORING OF A TWO-CLIQUE INTERVAL GRAPH

A signed graph labels every edge + or -.  A proper signed coloring (in the
sense used here) assigns different colors to adjacent vertices and requires
that two edges carrying the same unordered pair of endpoint colors have the
same sign.  Switching a vertex reverses every incident sign; a signed coloring
may first switch any vertices.

This instance has two disconnected components A and B, each with {size}
vertices.  It is an interval graph: all closed intervals for A are [0,1], all
closed intervals for B are [2,3], so each component is a clique and there are
no edges between them.  Every edge of A is positive.

The B vertices are the {size} listed cells below.  A token v@c means vertex ID
v has column c.  Between two B vertices the edge is NEGATIVE exactly when the
two cells occur in the same displayed row or have equal column numbers; every
other B edge is POSITIVE.  Row and column numbers are elements of Z/{n}Z,
written as 0,...,{n - 1}; equality is ordinary integer equality.  Each row has
exactly {degree} listed cells.

Find one vertex from each displayed row, in the displayed row order, with no
column repeated.  This is a compressed certificate for a proper signed
coloring with exactly {target}=2*{size}-{n} colors: color A with 1,...,{size};
give the selected B vertices colors 1,...,{n} in displayed row order; give all
other B vertices fresh distinct colors {size + 1},...,{target}.  No switching
is needed.  The selected B edges are positive because selected cells share
neither a row nor a column, so every repeated unordered color pair has the
same sign as its positive counterpart in A.

CELL TABLE
{chr(10).join(lines)}{hint}

Give your final answer inside <answer></answer> tags as exactly {n} decimal
vertex IDs separated by commas, one for each displayed row in order.  IDs must
be in 1..{size}; repeats are forbidden.  Example format:
<answer>4, 17, 9</answer>
Output nothing else inside the tags."""


def parse_answer(text):
    """Parse a comma/whitespace-separated integer list from answer tags."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    if not body:
        return []
    try:
        if body.startswith("["):
            value = json.loads(body)
            if isinstance(value, list) and all(
                isinstance(x, int) and not isinstance(x, bool) for x in value
            ):
                return value
            return None
        pieces = [piece for piece in re.split(r"[\s,]+", body) if piece]
        if not pieces or any(re.fullmatch(r"[+-]?\d+", p) is None for p in pieces):
            return None
        return [int(piece) for piece in pieces]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    """Check the compressed coloring certificate without consulting the plant."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list of vertex IDs"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"expected exactly {n} row choices"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every vertex ID must be an integer"
    if len(set(answer)) != len(answer):
        return False, "vertex IDs must be distinct"

    by_id, row_of, col_of = _cell_maps(inst)
    for value in answer:
        if value not in by_id:
            return False, f"unknown vertex ID {value}"
    for position, value in enumerate(answer):
        if row_of[value] != position:
            return False, f"position {position + 1} selects a vertex from the wrong row"

    columns = [col_of[value] for value in answer]
    seen = set()
    for position, column in enumerate(columns):
        if column in seen:
            return False, f"column {column} is repeated by position {position + 1}"
        seen.add(column)

    # The decoder's only repeated color pairs are: A_i A_j and the two selected
    # B vertices at positions i,j.  A_i A_j is positive.  The B edge is positive
    # exactly when its cells share neither row nor column, established above.
    # Thus all signed color-pair constraints have now been checked exactly.
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the d^n one-listed-cell-per-row language."""
    return [rng.choice(row["cells"])["id"] for row in inst["rows"]]


def search_space(inst):
    return inst["degree"] ** inst["n"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    choices = [[cell["id"] for cell in row["cells"]] for row in inst["rows"]]
    for candidate in itertools.product(*choices):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _wl_graph_code(inst):
    """A relabel-invariant color-refinement code of the allowed bipartite graph."""
    rows = inst["rows"]
    n_rows = len(rows)
    columns = sorted({cell["col"] for row in rows for cell in row["cells"]})
    col_index = {column: i for i, column in enumerate(columns)}
    total = n_rows + len(columns)
    adjacency = [set() for _ in range(total)]
    for r_index, row in enumerate(rows):
        for cell in row["cells"]:
            c_index = n_rows + col_index[cell["col"]]
            adjacency[r_index].add(c_index)
            adjacency[c_index].add(r_index)

    colors = [0] * n_rows + [1] * len(columns)
    for _ in range(total + 1):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(total)
        ]
        palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        if new_colors == colors:
            break
        colors = new_colors

    class_sizes = Counter(colors)
    edge_counts = Counter()
    for r_index in range(n_rows):
        for c_index in adjacency[r_index]:
            edge_counts[(colors[r_index], colors[c_index])] += 1
    payload = {
        "classes": sorted(class_sizes.items()),
        "edges": sorted((a, b, count) for (a, b), count in edge_counts.items()),
        "discrete": len(class_sizes) == total,
    }
    if payload["discrete"]:
        payload["canonical_edges"] = sorted(
            (colors[r], colors[c])
            for r in range(n_rows)
            for c in adjacency[r]
        )
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def canonical_key(inst):
    structural_code = _wl_graph_code(inst)
    return hashlib.sha256(structural_code.encode("utf-8")).hexdigest()


def escalate(params):
    """Increase both row count and decoy degree while the answer stays writable."""
    n = int(params["n"])
    degree = int(params.get("degree", 8))
    if n >= 239 or degree >= 22:
        return "cap_bound"
    return {"n": min(239, n + 22), "degree": min(22, degree + 2)}


def _hopcroft_karp(inst):
    """Return (certificate, edge_scans), or (None, edge_scans)."""
    rows = inst["rows"]
    n = len(rows)
    columns = sorted({cell["col"] for row in rows for cell in row["cells"]})
    c_to_i = {value: i for i, value in enumerate(columns)}
    adjacency = [
        [c_to_i[cell["col"]] for cell in row["cells"]]
        for row in rows
    ]
    pair_u = [-1] * n
    pair_v = [-1] * len(columns)
    distance = [0] * n
    scans = 0

    def bfs():
        nonlocal scans
        queue = deque()
        found = False
        for u in range(n):
            if pair_u[u] == -1:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = -1
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                scans += 1
                mate = pair_v[v]
                if mate == -1:
                    found = True
                elif distance[mate] == -1:
                    distance[mate] = distance[u] + 1
                    queue.append(mate)
        return found

    def dfs(u):
        nonlocal scans
        for v in adjacency[u]:
            scans += 1
            mate = pair_v[v]
            if mate == -1 or (
                distance[mate] == distance[u] + 1 and dfs(mate)
            ):
                pair_u[u] = v
                pair_v[v] = u
                return True
        distance[u] = -1
        return False

    matching = 0
    while bfs():
        for u in range(n):
            if pair_u[u] == -1 and dfs(u):
                matching += 1
    if matching != n:
        return None, scans

    answer = []
    for u, v in enumerate(pair_u):
        column = columns[v]
        cell = next(cell for cell in rows[u]["cells"] if cell["col"] == column)
        answer.append(cell["id"])
    return answer, scans


def _outlier_candidate(inst):
    degree_by_column = Counter(
        cell["col"] for row in inst["rows"] for cell in row["cells"]
    )
    return [
        min(row["cells"], key=lambda c: (degree_by_column[c["col"]], c["id"]))["id"]
        for row in inst["rows"]
    ]


def _greedy_candidate(inst):
    used = set()
    answer = []
    for row in inst["rows"]:
        ordered = sorted(row["cells"], key=lambda cell: cell["id"])
        chosen = next((cell for cell in ordered if cell["col"] not in used), ordered[0])
        answer.append(chosen["id"])
        used.add(chosen["col"])
    return answer


def _fixed_offset_candidates(inst):
    n = inst["n"]
    for offset in (0, 1, n - 1):
        answer = []
        for row in inst["rows"]:
            target = (row["row"] + offset) % n
            cell = next((c for c in row["cells"] if c["col"] == target), None)
            if cell is None:
                break
            answer.append(cell["id"])
        if len(answer) == n:
            yield answer


def _relabel_instance(inst, rng, *, reorder=False, remap_cells=False, remap_axes=False):
    """Apply genuine presentation/ground-set relabellings and carry the witness."""
    out = copy.deepcopy(inst)
    selected_by_row = {
        row["row"]: answer_id for row, answer_id in zip(out["rows"], out["answer"])
    }

    if remap_axes:
        old_rows = sorted(row["row"] for row in out["rows"])
        old_cols = sorted({c["col"] for row in out["rows"] for c in row["cells"]})
        new_rows = old_rows[:]
        new_cols = old_cols[:]
        rng.shuffle(new_rows)
        rng.shuffle(new_cols)
        rmap = dict(zip(old_rows, new_rows))
        cmap = dict(zip(old_cols, new_cols))
        selected_by_row = {rmap[r]: value for r, value in selected_by_row.items()}
        for row in out["rows"]:
            row["row"] = rmap[row["row"]]
            for cell in row["cells"]:
                cell["col"] = cmap[cell["col"]]

    if remap_cells:
        ids = sorted(c["id"] for row in out["rows"] for c in row["cells"])
        shuffled = ids[:]
        rng.shuffle(shuffled)
        id_map = dict(zip(ids, shuffled))
        selected_by_row = {r: id_map[value] for r, value in selected_by_row.items()}
        for row in out["rows"]:
            for cell in row["cells"]:
                cell["id"] = id_map[cell["id"]]

    if reorder:
        rng.shuffle(out["rows"])
        for row in out["rows"]:
            rng.shuffle(row["cells"])

    out["answer"] = [selected_by_row[row["row"]] for row in out["rows"]]
    return out


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {}

    # G1: all named presets, multiple independent seeds, including JSON safety.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260904, **shipping_params)

    # G2: force five different validation branches.
    corruptions = {}
    dropped = inst["answer"][:-1]
    swapped = inst["answer"][:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = inst["answer"][:]
    duplicated[1] = duplicated[0]
    empty = []
    out_of_range = inst["answer"][:]
    out_of_range[0] = inst["component_size"] + 1
    for name, candidate in (
        ("drop", dropped),
        ("swap", swapped),
        ("duplicate", duplicated),
        ("empty", empty),
        ("out_of_range", out_of_range),
    ):
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: model-style prose and a fenced payload inside the required tags.
    response = (
        "I used the positive-edge condition to choose a transversal.\n\n"
        "<answer>\n```text\n"
        + _answer_text(inst["answer"])
        + "\n```\n</answer>\nThe certificate is above."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_entries": len(parsed) if isinstance(parsed, list) else None,
    }

    # G4 and the shipping density part of G5 share the same structure-aware sample.
    sample_total = 200_000
    sample_rng = random.Random(0x161203280)
    sample_hits = 0
    _, _, sample_col_of = _cell_maps(inst)
    sample_start = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(inst, sample_rng)
        # random_candidate already guarantees integer IDs, the right length, and
        # one ID from each row.  The only remaining validity test is column
        # distinctness, evaluated from the same exact map used by verify().
        if len({sample_col_of[value] for value in candidate}) == inst["n"]:
            sample_hits += 1
    sample_seconds = time.perf_counter() - sample_start
    report["G4_guess_resistance"] = {
        "pass": sample_hits / sample_total < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": sample_hits / sample_total,
        "candidate_space": search_space(inst),
        "prior": "uniform independent choice among the d listed cells in every row",
    }

    # Reference algorithm and adversary panel, all at the shipping preset.
    attack_names = (
        "outlier_min_column_degree",
        "greedy_first_unused",
        "random_restart_256",
        "fixed_offsets_0_plusminus1",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_scans = []
    reference_times = []
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **shipping_params)
        if verify(attack_inst, _outlier_candidate(attack_inst))[0]:
            attack_successes["outlier_min_column_degree"] += 1
        if verify(attack_inst, _greedy_candidate(attack_inst))[0]:
            attack_successes["greedy_first_unused"] += 1

        restart_rng = random.Random(seed ^ 0xA55A)
        restart_won = False
        for _ in range(256):
            if verify(attack_inst, random_candidate(attack_inst, restart_rng))[0]:
                restart_won = True
                break
        attack_successes["random_restart_256"] += int(restart_won)

        fixed_won = any(
            verify(attack_inst, candidate)[0]
            for candidate in _fixed_offset_candidates(attack_inst)
        )
        attack_successes["fixed_offsets_0_plusminus1"] += int(fixed_won)

        t0 = time.perf_counter()
        reference_answer, scans = _hopcroft_karp(attack_inst)
        elapsed = time.perf_counter() - t0
        solved = reference_answer is not None and verify(attack_inst, reference_answer)[0]
        reference_successes += int(solved)
        reference_scans.append(scans)
        reference_times.append(elapsed)

    median_scans = int(statistics.median(reference_scans))
    median_wall = statistics.median(reference_times)
    attacks = {
        name: {"successes": attack_successes[name], "attempts": len(attack_seeds)}
        for name in attack_names
    }
    panel_pass = all(entry["successes"] == 0 for entry in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": panel_pass and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Hopcroft-Karp bipartite maximum matching",
            "complexity": "O(E sqrt(V))",
            "wall_clock_sec_median": median_wall,
            "operations_median_edge_scans": median_scans,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": sample_hits / sample_total < 1e-6
        and demo_count is not None
        and reference_successes == len(attack_seeds),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_fraction": sample_hits / sample_total,
        "shipping_sampling_wall_seconds": sample_seconds,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_wall_seconds_median": median_wall,
        "baseline_edge_scan_operations_median": median_scans,
    }

    # G7: named ladder grows in both n and d; doubling n still constructs/verifies.
    named_bits = [
        params["n"] * math.log2(params["degree"])
        for params in DIFFICULTY.values()
    ]
    doubled_params = {
        "n": 2 * shipping_params["n"],
        "degree": shipping_params["degree"],
    }
    t0 = time.perf_counter()
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_build = time.perf_counter() - t0
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(named_bits, named_bits[1:])) and doubled_ok,
        "ladder_log2_candidate_spaces": named_bits,
        "doubled_n": doubled_params["n"],
        "doubled_build_seconds": doubled_build,
        "doubled_verify_reason": doubled_why,
    }

    # G8: four transformations (including their composition), and unrelated seeds.
    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        transforms = (
            {"reorder": True},
            {"remap_cells": True},
            {"remap_axes": True},
            {"reorder": True, "remap_cells": True, "remap_axes": True},
        )
        for index, flags in enumerate(transforms):
            moved = _relabel_instance(base, random.Random(seed * 101 + index), **flags)
            invariance_checks += 1
            if canonical_key(moved) != key:
                g8_failures.append(f"seed {seed}, transform {index}: key changed")
            ok, why = verify(moved, moved["answer"])
            carried_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}, transform {index}: {why}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": distinct_keys,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "method": "bipartite color refinement; discrete cases include canonical edges",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = inst["n"] + 3 * inst["degree"]
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_verdict = G9_RESULTS["hinted_verdict"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_verdict == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        entry.get("pass") is True
        for key, entry in report.items()
        if key.startswith("G") and isinstance(entry, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
