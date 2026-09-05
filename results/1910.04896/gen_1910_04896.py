"""Verified Track-B generator for a structured graph-colouring family.

The paper defines proper graph colourings in Section 2 and proves in Theorem
4.8 that the chromatic number is the codimension of the graph's chromatic
monomial ideal.  This module asks for one colour class of a proper 2-colouring.

Generation chooses a binary coordinate and its two level sets first, then adds
only edges crossing those sets.  A displayed perfect matching and a connected
spine make the certificate exact.  Breadth-first search is an honest linear-time
reference algorithm.  The intended no-tool route instead notices that one bit
of every endpoint label flips across every edge.
"""

from __future__ import annotations

import hashlib
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
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple undirected graph",
        "displayed perfect matching",
        "one colour class of a proper 2-colouring",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact matching-endpoint membership",
        "exact edge-endpoint colour comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Definition 4.1 and Theorem 4.8: the paper constructs the "
        "chromatic ideal M_G and proves chi(G)=codim(S/M_G), with the proof "
        "carrying colour-class covers in both directions"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Intersect the binary-coordinate changes across the matching pairs to "
        "find the one coordinate reversed by every graph edge; without this "
        "invariant one must traverse the dense graph."
    ),
    "hardness_basis": (
        "Track B: breadth-first bipartite colouring solves the generated regime "
        "in O(|V|+|E|); at shipping n=96 it averaged 10,733 primitive "
        "operations per instance (85,864 operations and 0.263 seconds over "
        "eight seeds), while the compact common-bit route uses at most "
        "3n-1=287 exact bit operations."
    ),
    "max_answer_tokens": 106,
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
    "demo": {"n": 4, "edge_percent": 30},
    "easy": {"n": 32, "edge_percent": 35},
    "medium": {"n": 64, "edge_percent": 45},
    "hard": {"n": 96, "edge_percent": 55},
}

SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "Every matching pair reverses one common binary coordinate, and every graph "
    "edge respects that same coordinate."
)
PLACEBO_HINT = (
    "Every listed pair uses zero-based vertex labels, and every graph edge should "
    "be checked with the same convention."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A comma-separated list of exactly n distinct vertex indices denoting "
        "colour 0; because the displayed perfect matching consists of n disjoint "
        "edges, a structure-aware candidate chooses exactly one endpoint of each "
        "matching pair."
    ),
    "bounds": {
        "length": "n",
        "entry_range": "0..2n-1",
        "entries_distinct": True,
        "one_endpoint_per_matching_pair": True,
        "candidate_count": "2^n",
        "max_named_preset_length": 96,
    },
}


G9_ORACLE_RESULTS = {
    "bare": {"solved": None, "attempts": 0},
    "hinted": {"solved": None, "attempts": 0},
    "placebo": {"solved": None, "attempts": 0},
    "hinted_verdict": "pending",
}


NOTES = r"""
STEP 0 and exact definition. Section 2, Definition 2.5 defines a k-colouring as
a map from the vertices to {0,...,k-1} whose values differ on every edge.
Section 4, Definition 4.1 constructs the chromatic monomial ideal M_G, and
Theorem 4.8 proves chi(G)=codim(S/M_G). Its proof turns a colouring into a
cover by independent sets and a codimension realization back into a colouring.
The present witness uses the theorem's paper-licensed graph representation and
is one side R of a 2-colouring; the other side is V\R.
Verification executes Definition 2.5 directly, so it accepts either valid side
and never consults the planted answer.

The paper's easy and explicit regimes were checked before construction.
Theorem 6.2 and especially Lemmas 6.3--6.4/Theorem 6.6 construct colourings of
special unions of cliques. Those formulae make a Track-A claim untenable there.
More generally, the present generated graphs are bipartite, so ordinary BFS
produces the certificate in O(|V|+|E|). This module is therefore explicitly
Track B. The mechanical route scans thousands of dense edges at shipping size.
The compact route computes the bitwise intersection of the endpoint XORs of the
n displayed matching pairs, obtaining one power of two, then chooses from each
pair the endpoint on one fixed level of that bit. It needs n XORs, n-1 ANDs,
and n endpoint-bit tests: 3n-1 exact bit operations.

Inverse generation. A balanced binary coordinate and one of its level sets are
chosen before any edge exists. A perfect matching across the two levels is
sampled until the intersection of all matching endpoint XORs is exactly the
chosen bit. Symmetric cross-edges connect successive matched pairs, guaranteeing
connectedness, and all remaining decoys are sampled from the same cross-level
distribution. Thus the planted set and its complement are valid witnesses by
construction. Connectedness gives exactly two proper 2-colourings.

Attack hardening. Hidden bit zero is excluded, and a guaranteed even-even edge
defeats the obvious parity colouring. Random labelling within the bit levels and
symmetric edge sampling remove a degree-side signal. The panel measures a
per-matching degree outlier rule, a degree-ordered greedy independent-set rule,
256 structure-aware random restarts, and the ordinary even/odd ansatz. The
domain-standard BFS algorithm is expected to solve and is reported separately.

Canonicalization. Vertex relabelling, edge reordering, matching reordering, and
endpoint reversal preserve the abstract marked graph. canonical_key uses a
stable colour-refinement invariant of that marked graph and ignores the planted
answer and the arithmetic spelling of labels. This is a strong cheap invariant,
not a complete graph-isomorphism canonical form; rare colour-refinement
collisions may over-collapse unrelated instances.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _edge(u, v):
    if u == v:
        raise ValueError("a simple graph cannot contain a loop")
    return (u, v) if u < v else (v, u)


def _balanced_bit_positions(n):
    """Bits other than parity whose two levels balance on range(2*n)."""
    positions = []
    total = 2 * n
    for bit in range(1, max(2, total.bit_length())):
        zeros = sum(1 for v in range(total) if ((v >> bit) & 1) == 0)
        if zeros == n:
            positions.append(bit)
    return positions


def _matching_with_exact_common_bit(left, right, bit, rng):
    """Return a random cross-level perfect matching with XOR-AND exactly bit."""
    target = 1 << bit
    for _ in range(256):
        shuffled = list(right)
        rng.shuffle(shuffled)
        pairs = [_edge(u, v) for u, v in zip(left, shuffled)]
        common = (1 << max(1, (2 * len(left) - 1).bit_length())) - 1
        for u, v in pairs:
            common &= u ^ v
        if common == target:
            rng.shuffle(pairs)
            return pairs

    # This fallback is deterministic and should be unreachable at named sizes.
    right_by_flip = {v ^ target: v for v in right}
    if all(u in right_by_flip for u in left):
        pairs = [_edge(u, right_by_flip[u]) for u in left]
        rng.shuffle(pairs)
        return pairs
    raise RuntimeError("could not construct a matching with an exact common bit")


def make_instance(n, seed=0, **params):
    """Inverse-generate a connected bipartite graph and a colour class.

    ``n`` is the number of matching pairs, so the graph has 2n vertices and a
    submitted colour class has n vertices. Larger n grows the candidate space;
    ``edge_percent`` grows the mechanical traversal cost without growing the
    answer.
    """

    edge_percent = params.pop("edge_percent", 45)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if n > 256:
        raise ValueError("n must be at most 256 under the answer-atom cap")
    if isinstance(edge_percent, bool) or not isinstance(edge_percent, int):
        raise ValueError("edge_percent must be an integer")
    if not 1 <= edge_percent <= 95:
        raise ValueError("edge_percent must lie in 1..95")

    available_bits = _balanced_bit_positions(n)
    if not available_bits:
        raise ValueError(
            "range(2*n) has no balanced non-parity binary coordinate; "
            "choose n divisible by 2"
        )

    rng = random.Random(seed)
    bit = rng.choice(available_bits)
    side_zero = [v for v in range(2 * n) if ((v >> bit) & 1) == 0]
    side_one = [v for v in range(2 * n) if ((v >> bit) & 1) == 1]
    rng.shuffle(side_zero)
    rng.shuffle(side_one)

    matching = _matching_with_exact_common_bit(side_zero, side_one, bit, rng)
    edges = set(matching)

    # Recover the zero/one endpoint of each displayed matching pair internally.
    oriented_pairs = []
    for u, v in matching:
        if ((u >> bit) & 1) == 0:
            oriented_pairs.append((u, v))
        else:
            oriented_pairs.append((v, u))
    rng.shuffle(oriented_pairs)

    # A symmetric chain connects all matching components and removes one-sided
    # degree effects from the deterministic connectivity scaffold.
    for i in range(n - 1):
        s0, t0 = oriented_pairs[i]
        s1, t1 = oriented_pairs[i + 1]
        edges.add(_edge(s0, t1))
        edges.add(_edge(s1, t0))

    # The ordinary parity ansatz is always false because bit 0 is not the hidden
    # bit and this cross-level edge has endpoints of the same parity.
    parity_spoiler = _edge(0, 1 << bit)
    edges.add(parity_spoiler)

    # Decoys and scaffold edges have the same mathematical distribution: every
    # edge independently visible to the solver joins the two hidden levels.
    for u in side_zero:
        for v in side_one:
            e = _edge(u, v)
            if e not in edges and rng.randrange(100) < edge_percent:
                edges.add(e)

    # Symmetric greedy bait.  One vertex from each true side is made adjacent
    # to every opposite-side vertex except the other bait.  They consequently
    # have the same maximum degree, reveal no preferred colour, and a
    # degree-first independent-set heuristic selects both incompatible sides.
    bait_zero = oriented_pairs[0][0]
    bait_one = oriented_pairs[n // 2][1]
    for v in side_one:
        if v != bait_one:
            edges.add(_edge(bait_zero, v))
    for u in side_zero:
        if u != bait_zero:
            edges.add(_edge(u, bait_one))
    edges.discard(_edge(bait_zero, bait_one))

    # Retain a guaranteed same-parity edge even in the rare case where the
    # earlier parity spoiler happened to be the deliberately absent bait edge.
    for u in side_zero:
        for v in side_one:
            if (u & 1) == (v & 1) and _edge(u, v) != _edge(bait_zero, bait_one):
                edges.add(_edge(u, v))
                break
        else:
            continue
        break

    edge_list = sorted(edges)
    rng.shuffle(edge_list)
    matching_list = list(matching)
    rng.shuffle(matching_list)
    answer = sorted(side_zero)

    return {
        "family": "common-bit connected bipartite colouring",
        "n": n,
        "n_vertices": 2 * n,
        "edge_percent": edge_percent,
        "vertices": list(range(2 * n)),
        "matching": [list(e) for e in matching_list],
        "edges": [list(e) for e in edge_list],
        "answer": answer,
    }


def render(inst):
    """Render a self-contained colouring problem and exact wire format."""

    n = inst["n"]
    matching = "\n".join(
        f"  {i}: {u} {v}" for i, (u, v) in enumerate(inst["matching"])
    )
    edge_rows = []
    width = 12
    for start in range(0, len(inst["edges"]), width):
        row = " ".join(
            f"{u}-{v}" for u, v in inst["edges"][start : start + width]
        )
        edge_rows.append("  " + row)
    edges = "\n".join(edge_rows)
    example = "7, 2"
    statement = f"""Proper two-colouring of a finite graph

A finite simple undirected graph has vertices 0 through {2 * n - 1}.  An edge
u-v is unordered.  A proper two-colouring assigns each vertex colour 0 or 1 so
that the endpoints of every edge have different colours.

Submit the colour-0 class R.  It must be a list of exactly {n} DISTINCT vertex
indices.  A vertex is in colour 0 exactly when it is listed; every unlisted
vertex is in colour 1.  Thus every displayed graph edge must have exactly one
endpoint in R.  Order in R does not matter.

The following {n} unordered edges form a displayed perfect matching: every
vertex occurs in exactly one of them.  Consequently, any valid R contains
exactly one endpoint of every matching pair.

MATCHING PAIRS (pair_number: endpoint endpoint):
{matching}

ALL GRAPH EDGES ({len(inst['edges'])} edges, written u-v):
{edges}

Give your final answer inside <answer></answer> tags as a comma-separated list
of exactly {n} decimal integers.  Example syntax only (not a size-{n} answer):
<answer>{example}</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the tagged comma-separated integer list; never raise."""

    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return []
    pieces = [piece.strip() for piece in body.split(",")]
    if any(not re.fullmatch(r"[+-]?\d+", piece or "") for piece in pieces):
        return None
    try:
        return [int(piece) for piece in pieces]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst, answer):
    """Check any proposed colour class directly; never inspect inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a list of vertex indices"
    if not answer:
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) != n:
        return False, f"wrong class size: expected {n}, got {len(answer)}"
    for position, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {position} is not an integer"
        if not 0 <= value < inst["n_vertices"]:
            return False, f"vertex {value} is out of range"
    if len(set(answer)) != len(answer):
        return False, "vertex indices must be distinct"

    chosen = set(answer)
    for pair_number, (u, v) in enumerate(inst["matching"]):
        if (u in chosen) == (v in chosen):
            return False, f"matching pair {pair_number} does not cross the colours"
    for edge_number, (u, v) in enumerate(inst["edges"]):
        if (u in chosen) == (v in chosen):
            return False, f"graph edge {edge_number} has equal endpoint colours"
    return True, "ok"


def random_candidate(inst, rng):
    """Choose one endpoint of every displayed matching edge, uniformly."""

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    mask = rng.getrandbits(inst["n"])
    return [pair[(mask >> i) & 1] for i, pair in enumerate(inst["matching"])]


def search_space(inst):
    """The structure-aware language has two choices per matching pair."""

    return 1 << inst["n"]


def enumerate_all(inst):
    """Brute-force exact answer count only when at most 2^20 candidates exist."""

    n = inst["n"]
    if n > 20:
        return None
    total = 0
    matching = inst["matching"]
    for mask in range(1 << n):
        candidate = [matching[i][(mask >> i) & 1] for i in range(n)]
        ok, _ = verify(inst, candidate)
        total += int(ok)
    return total


def _compress_signatures(signatures):
    kinds = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
    return [kinds[signature] for signature in signatures]


def canonical_key(inst):
    """A relabelling-invariant colour-refinement key of the marked graph.

    The perfect matching is marked instance data, so matching edges have a
    distinct edge colour.  The key is a strong cheap invariant rather than a
    complete graph-isomorphism canonical labelling.
    """

    n_vertices = inst["n_vertices"]
    matching = {_edge(u, v) for u, v in inst["matching"]}
    edges = {_edge(u, v) for u, v in inst["edges"]}
    adjacency = [[] for _ in range(n_vertices)]
    for u, v in edges:
        mark = int((u, v) in matching)
        adjacency[u].append((v, mark))
        adjacency[v].append((u, mark))
    for row in adjacency:
        row.sort()

    initial = [
        (len(row), sum(mark for _, mark in row)) for row in adjacency
    ]
    colours = _compress_signatures(initial)
    for _ in range(n_vertices + 1):
        signatures = []
        for v, row in enumerate(adjacency):
            neighbourhood = tuple(sorted((mark, colours[w]) for w, mark in row))
            signatures.append((colours[v], neighbourhood))
        new_colours = _compress_signatures(signatures)
        if new_colours == colours:
            break
        colours = new_colours

    vertex_data = sorted(
        (colours[v], len(adjacency[v]), sum(m for _, m in adjacency[v]))
        for v in range(n_vertices)
    )
    edge_data = sorted(
        (int((u, v) in matching), min(colours[u], colours[v]), max(colours[u], colours[v]))
        for u, v in edges
    )
    payload = {
        "n_vertices": n_vertices,
        "n_edges": len(edges),
        "n_matching": len(matching),
        "vertices": vertex_data,
        "edges": edge_data,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    """Increase dense decoy work at fixed witness length before hitting a cap."""

    current = dict(params)
    current.pop("_preset", None)
    edge_percent = current.get("edge_percent", 45)
    if edge_percent < 85:
        current["edge_percent"] = min(85, edge_percent + 10)
        return current
    # At n=96 the compact route already uses 287 of the allowed 300 exact
    # operations. Increasing n would make difficulty come from an inadmissible
    # route even though the 256-atom output cap is not yet binding.
    return "cap_bound"


def _adjacency(inst):
    adjacency = [[] for _ in range(inst["n_vertices"])]
    for u, v in inst["edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    for row in adjacency:
        row.sort()
    return adjacency


def _reference_bfs(inst):
    """Return a BFS colour class and a count of primitive traversal operations."""

    adjacency = _adjacency(inst)
    colour = [-1] * inst["n_vertices"]
    operations = 0
    for root in range(inst["n_vertices"]):
        if colour[root] != -1:
            continue
        colour[root] = 0
        queue = [root]
        head = 0
        while head < len(queue):
            v = queue[head]
            head += 1
            operations += 1
            for w in adjacency[v]:
                operations += 1
                if colour[w] == -1:
                    colour[w] = 1 - colour[v]
                    queue.append(w)
                elif colour[w] == colour[v]:
                    return None, operations
    zero = [v for v, c in enumerate(colour) if c == 0]
    one = [v for v, c in enumerate(colour) if c == 1]
    candidate = zero if len(zero) == inst["n"] else one
    candidate.sort()
    return candidate, operations


def _attack_degree_outlier(inst):
    degree = [0] * inst["n_vertices"]
    for u, v in inst["edges"]:
        degree[u] += 1
        degree[v] += 1
    candidate = []
    for u, v in inst["matching"]:
        candidate.append(u if (degree[u], -u) >= (degree[v], -v) else v)
    candidate.sort()
    return candidate, len(inst["edges"]) * 2 + inst["n"]


def _attack_greedy_independent(inst):
    adjacency = [set(row) for row in _adjacency(inst)]
    order = sorted(
        range(inst["n_vertices"]),
        key=lambda v: (-len(adjacency[v]), v),
    )
    chosen = set()
    operations = 0
    for v in order:
        if len(chosen) >= inst["n"]:
            break
        conflict = False
        for w in adjacency[v]:
            operations += 1
            if w in chosen:
                conflict = True
                break
        if not conflict:
            chosen.add(v)
    return sorted(chosen), operations


def _attack_random_restart(inst, rng, restarts=256):
    last = []
    operations = 0
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        operations += inst["n"]
        if _fast_colouring_check(inst, last):
            return last, operations
    return last, operations


def _attack_parity_ansatz(inst):
    candidate = [v for v in range(inst["n_vertices"]) if v % 2 == 0]
    return candidate, inst["n_vertices"]


def _fast_colouring_check(inst, candidate):
    """Fast internal check for already-shaped attack and density candidates."""

    chosen = set(candidate)
    if len(chosen) != inst["n"]:
        return False
    return all((u in chosen) != (v in chosen) for u, v in inst["edges"])


def _run_adversary_panel(params):
    attacks = {
        "outlier_higher_degree_per_match": _attack_degree_outlier,
        "greedy_degree_independent_set": _attack_greedy_independent,
        "random_restart_256": None,
        "even_odd_label_ansatz": _attack_parity_ansatz,
    }
    results = {
        name: {"successes": 0, "attempts": 8, "steps": 0, "wall_clock_sec": 0.0}
        for name in attacks
    }
    ref_successes = 0
    ref_operations = 0
    ref_elapsed = 0.0
    for attempt in range(8):
        inst = make_instance(seed=8100 + attempt, **params)
        ref_start = time.perf_counter()
        candidate, operations = _reference_bfs(inst)
        ref_elapsed += time.perf_counter() - ref_start
        ref_operations += operations
        if candidate is not None and verify(inst, candidate)[0]:
            ref_successes += 1

    for attempt in range(8):
        inst = make_instance(seed=9100 + attempt, **params)
        for name, attack in attacks.items():
            start = time.perf_counter()
            if name == "random_restart_256":
                candidate, operations = _attack_random_restart(
                    inst, random.Random(12000 + attempt)
                )
            else:
                candidate, operations = attack(inst)
            elapsed = time.perf_counter() - start
            ok, _ = verify(inst, candidate)
            results[name]["successes"] += int(ok)
            results[name]["steps"] += operations
            results[name]["wall_clock_sec"] += elapsed

    for result in results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    reference = {
        "name": "breadth-first bipartite colouring",
        "complexity": "O(|V|+|E|)",
        "wall_clock_sec": round(ref_elapsed, 6),
        "operations": ref_operations,
        "average_operations_per_instance": ref_operations // 8,
        "solves": f"{ref_successes}/8, as expected",
    }
    return results, reference


def _relabel_instance(inst, permutation, edge_order=None, matching_order=None):
    if sorted(permutation) != list(range(inst["n_vertices"])):
        raise ValueError("permutation is not a relabelling")
    edges = [[permutation[u], permutation[v]] for u, v in inst["edges"]]
    matching = [[permutation[u], permutation[v]] for u, v in inst["matching"]]
    if edge_order is not None:
        edges = [edges[i] for i in edge_order]
    if matching_order is not None:
        matching = [matching[i] for i in matching_order]
    # Reverse alternating endpoints as another presentation symmetry.
    for i in range(0, len(matching), 2):
        matching[i].reverse()
    return {
        "family": inst["family"],
        "n": inst["n"],
        "n_vertices": inst["n_vertices"],
        "edge_percent": inst["edge_percent"],
        "vertices": list(range(inst["n_vertices"])),
        "matching": matching,
        "edges": edges,
        "answer": sorted(permutation[v] for v in inst["answer"]),
    }


def selftest():
    """Run mandatory gates and return their measured, JSON-native report."""

    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    report["shipping_params"] = dict(shipping_params)

    # G1: every named rung over several seeds.
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer is not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    # G2: five distinct corruption modes and reasons.
    inst = make_instance(seed=314159, **shipping_params)
    good = list(inst["answer"])
    chosen = set(good)
    selected_pair = next(
        (u, v) if u in chosen else (v, u) for u, v in inst["matching"]
    )
    selected, unselected = selected_pair
    swapped = [unselected if v == selected else v for v in good]
    corruptions = {
        "drop": good[:-1],
        "swap": swapped,
        "duplicate": good[:-1] + [good[0]],
        "empty": [],
        "out_of_range": good[:-1] + [inst["n_vertices"]],
    }
    g2_cases = {}
    reasons = set()
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        g2_cases[name] = {"accepted": ok, "reason": reason}
        reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not case["accepted"] for case in g2_cases.values())
        and len(reasons) == len(corruptions),
        "distinct_reasons": len(reasons),
        "cases": g2_cases,
    }

    # G3: realistic prose, fences, and the exact rendered wire form.
    body = ", ".join(str(v) for v in inst["answer"])
    realistic = (
        "I used the matching constraints to propagate the two sides.\n\n"
        "<answer>\n```text\n" + body + "\n```\n</answer>\n"
        "The complement gives the other naming of the colours."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no tagged answer") is None,
        "parsed_matches": parsed == inst["answer"],
        "realistic_wrapper": True,
    }

    # G4: structure-aware uniform samples, not arbitrary subsets.
    guess_rng = random.Random(20260905)
    guess_inst = make_instance(seed=271828, **shipping_params)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(
            _fast_colouring_check(guess_inst, random_candidate(guess_inst, guess_rng))
        )
    guess_elapsed = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(guess_inst),
        "sampling_prior": "uniformly choose one endpoint of each displayed matching pair",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    # G5/G6: exact density from connected bipartiteness plus measured attacks.
    attacks, reference = _run_adversary_panel(shipping_params)
    demo_inst = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    strongest_name = max(attacks, key=lambda name: attacks[name]["steps"])
    exact_count = 2
    exact_fraction = exact_count / search_space(guess_inst)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 2 and reference["solves"].startswith("8/8"),
        "shipping_certified_solution_count": exact_count,
        "shipping_exact_solution_fraction": exact_fraction,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_n": demo_inst["n"],
        "demo_bruteforce_solution_count": demo_count,
        "strongest_failing_attack": strongest_name,
        "strongest_failing_attack_steps": attacks[strongest_name]["steps"],
        "strongest_failing_attack_wall_clock_sec": attacks[strongest_name][
            "wall_clock_sec"
        ],
        "reference_algorithm_operations": reference["operations"],
        "reference_algorithm_wall_clock_sec": reference["wall_clock_sec"],
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    # G7: monotone candidate spaces, doubled size, and fixed-length density axis.
    preset_spaces = {}
    for preset, params in DIFFICULTY.items():
        preset_inst = make_instance(seed=11, **params)
        preset_spaces[preset] = search_space(preset_inst)
    doubled_params = dict(shipping_params)
    doubled_params["n"] = min(256, 2 * doubled_params["n"])
    doubled = make_instance(seed=19, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    denser_params = dict(shipping_params)
    denser_params["edge_percent"] = min(85, denser_params["edge_percent"] + 10)
    denser = make_instance(seed=23, **denser_params)
    denser_ok, denser_reason = verify(denser, denser["answer"])
    monotone = all(
        earlier < later
        for earlier, later in zip(
            list(preset_spaces.values()), list(preset_spaces.values())[1:]
        )
    )
    report["G7_scales"] = {
        "pass": monotone and doubled_ok and denser_ok,
        "preset_candidate_spaces": preset_spaces,
        "preset_n": {name: params["n"] for name, params in DIFFICULTY.items()},
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "fixed_length_axis": denser_params,
        "fixed_length_answer_elements": denser_params["n"],
        "fixed_length_verifies": denser_ok,
        "fixed_length_reason": denser_reason,
    }

    # G8: prove invariance under real relabellings and generator reorderings.
    invariance_checks = 0
    carried_checks = 0
    invariance_failures = []
    for seed in range(20):
        base = make_instance(seed=15000 + seed, **shipping_params)
        base_key = canonical_key(base)
        rng = random.Random(16000 + seed)
        permutation = list(range(base["n_vertices"]))
        rng.shuffle(permutation)
        edge_order = list(range(len(base["edges"])))
        matching_order = list(range(len(base["matching"])))
        rng.shuffle(edge_order)
        rng.shuffle(matching_order)

        relabelled = _relabel_instance(base, permutation)
        reordered = _relabel_instance(
            base,
            list(range(base["n_vertices"])),
            edge_order=edge_order,
            matching_order=matching_order,
        )
        composed = _relabel_instance(
            base,
            permutation,
            edge_order=edge_order,
            matching_order=matching_order,
        )
        for name, transformed in (
            ("vertex_relabelling", relabelled),
            ("input_reordering", reordered),
            ("composed", composed),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                invariance_failures.append({"seed": seed, "transformation": name})
            ok, _ = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                invariance_failures.append(
                    {"seed": seed, "transformation": name, "witness": "failed"}
                )

    unrelated_keys = {
        canonical_key(make_instance(seed=17000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "invariance_failures": invariance_failures,
        "unrelated_instances": 20,
        "distinct_keys": len(unrelated_keys),
        "transformations": [
            "arbitrary vertex relabelling",
            "edge and matching reorder plus pair-endpoint reversal",
            "composition of relabelling and input reorderings",
        ],
    }

    # G9(a,b) are diagnostics populated from harden.py transcripts; only caps gate.
    answer_blob = json.dumps(guess_inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(guess_inst["answer"])
    intended_operations = 3 * guess_inst["n"] - 1
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        name: {
            "solved": G9_ORACLE_RESULTS[name]["solved"],
            "attempts": G9_ORACLE_RESULTS[name]["attempts"],
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    difference = None
    if (
        isinstance(hinted, int)
        and isinstance(placebo, int)
        and arms["hinted"]["attempts"] > 0
        and arms["placebo"]["attempts"] > 0
    ):
        difference = hinted / arms["hinted"]["attempts"] - placebo / arms[
            "placebo"
        ]["attempts"]
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gate_passes = [
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate_passes)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
