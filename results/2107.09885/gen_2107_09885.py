"""Verified target-set reconfiguration generator for arXiv:2107.09885.

The construction instantiates the split-graph reduction in Section 4.2.  Its
size-k target sets encode hitting sets, and a token jump encodes changing one
Boolean choice.  A hidden total order is sampled first; every prefix of that
order is then made a target set.  The answer is the resulting word of token
jumps, represented by ordered pairs of graph-vertex IDs.
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
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "succinctly specified split graph with independent twin classes",
        "integer vertex thresholds",
        "two equal-size target sets",
    ],
    "verification_operations": [
        "token-jump set update",
        "exact integer threshold comparison",
        "irreversible threshold-activation replay",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4.2, Theorem 4.4 and Lemma 4.5 (Hitting Set "
        "Reconfiguration to Target Set Reconfiguration on split graphs)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Reducing paired clique thresholds modulo a size-derived period reveals "
        "both the matched token jumps and their unique precedence ranks; without "
        "that change of variables one must decode and topologically sort thousands "
        "of shuffled constraint classes."
    ),
    "hardness_basis": (
        "Track B: the reference algorithm extracts the paper's hitting-set "
        "constraints and applies Kahn topological sorting in O(c+n^2) time; at "
        "the shipping preset it scans 1,553 compressed twin classes, takes 4,690 "
        "counted primitive operations and about 0.0003 seconds, while the "
        "compact modular route uses 192 exact arithmetic operations and is not "
        "mechanically executable from the long shuffled graph listing in context."
    ),
    "max_answer_tokens": 78,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of exactly n ordered pairs [remove, add]. The remove "
        "coordinates are a permutation of X\\Y, and the add coordinates are a "
        "permutation of Y\\X. It is a bounded symbolic word of token jumps."
    ),
    "bounds": {
        "moves": "n",
        "fields_per_move": 2,
        "vertex_id_minimum": 0,
        "vertex_id_maximum": "2n",
        "removals": "permutation of X\\Y",
        "additions": "permutation of Y\\X",
    },
}

DIFFICULTY = {
    "demo": {"n": 4, "decoy_classes": 4, "decoy_width": 2},
    "easy": {"n": 20, "decoy_classes": 256, "decoy_width": 4},
    "medium": {"n": 32, "decoy_classes": 1024, "decoy_width": 4},
    "hard": {"n": 48, "decoy_classes": 4096, "decoy_width": 4},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "After the common offset is removed, paired clique thresholds have matching "
    "quotients and complementary remainders under one size-derived modulus."
)
PLACEBO_HINT = (
    "The long graph description rewards keeping vertex roles and jump directions "
    "carefully organized throughout the calculation."
)

# Filled from the script-owned three-arm runs before release.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
    "placebo_verdict": "hardened",
}

NOTES = r"""
Step 0 and the paper. Section 2 fixes irreversible synchronous activation,
target sets, and token jumping. Section 4.2, Theorem 4.4 proves Target Set
Reconfiguration PSPACE-complete on split graphs. Lemma 4.5 is the exact
certificate bridge used here: size-k hitting sets are precisely size-k target
sets of the constructed split graph, and hitting-set jumps replay unchanged.
The construction below keeps the native split graph visible, including its
clique, independent constraint vertices, thresholds, and activation rule.

What makes the paper easy. Observation 3.1 makes every threshold-1 graph
reconfigurable; Theorem 3.2 gives a polynomial algorithm at maximum degree two;
Theorem 4.1 gives one on trees and its proof constructs an actual sequence.
Those regimes are deliberately avoided. The split-graph theorem is worst-case
PSPACE-hardness and does not establish hardness for this generated distribution.
This distribution itself has a polynomial decoder, so claiming Track A would be
false. The decoder identifies repeated two-neighbour constraint classes and
topologically sorts the remaining two-neighbour implications.

Generation and the compact route. A random total order and a random matching of
start/end tokens are sampled first. Variable constraints keep each matched pair
occupied; all forward implications make the sampled order the unique legal
length-n path. Decoy constraint classes all touch the common fixed token, so
they never invalidate a planted prefix. Their multiplicities are multiples of
n(2n+1), preserving a quotient/remainder invariant in clique thresholds. Thus
the certificate is known before the graph is assembled, never found by solving
it. Modulo that period, the pair tag and precedence rank can be read in 6n exact
operations; without noticing it, the reference route scans the shuffled graph
and performs a topological sort.

Attack response. Element IDs, endpoint order, constraint order, pair tags, and
decoy incidences are independently randomized. Decoys and planted tokens use
the same moving-vertex distribution. Raw threshold magnitude is dominated by
random decoy incidence. The panel tests input order, a raw-threshold outlier
rule, random permutation restarts, and the in-context strategy of recovering
the repeated twin pairs but ordering them numerically. The successful graph
decoder is reported separately as Track B's reference algorithm.
""".strip()


def _validate_params(n: int, decoy_classes: int, decoy_width: int) -> None:
    vals = (n, decoy_classes, decoy_width)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
        raise ValueError("n, decoy_classes, and decoy_width must be integers")
    if n < 2:
        raise ValueError("n must be at least 2")
    if decoy_classes < 0:
        raise ValueError("decoy_classes must be nonnegative")
    if not 1 <= decoy_width <= 2 * n:
        raise ValueError("decoy_width must lie between 1 and 2n")
    if decoy_classes > math.comb(2 * n, decoy_width):
        raise ValueError("too many distinct decoy classes for this width")


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate one split-graph target-set reconfiguration instance."""
    decoy_classes = params.pop("decoy_classes", max(4, 8 * n))
    decoy_width = params.pop("decoy_width", min(4, 2 * n))
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n, decoy_classes, decoy_width)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # Logical tokens r_i and a_i are relabelled independently of their hidden
    # precedence ranks. c is a fixed token common to both endpoints.
    element_count = 2 * n + 1
    labels = list(range(element_count))
    rng.shuffle(labels)
    r_label = labels[:n]
    a_label = labels[n:2 * n]
    common = labels[-1]

    hidden_order = list(range(n))
    rng.shuffle(hidden_order)
    rank_of = [0] * n
    for rank, var in enumerate(hidden_order):
        rank_of[var] = rank

    pair_codes = list(range(n))
    rng.shuffle(pair_codes)

    base = 2 * n + 1
    period = base * n
    constraints: list[list[object]] = []

    # A multiplicity greater than one marks each mandatory variable pair. The
    # multiple is chosen so its residue modulo period is a random pair tag.
    for var in range(n):
        code = pair_codes[var]
        multiplier = code if code else n
        constraints.append([[r_label[var], a_label[var]], base * multiplier])

    # Clause {r_j, a_i} is the implication "j moved => i moved". Including
    # every ordered rank pair makes the planted order the unique linear extension.
    for early_rank in range(n):
        early = hidden_order[early_rank]
        for late_rank in range(early_rank + 1, n):
            late = hidden_order[late_rank]
            constraints.append([[r_label[late], a_label[early]], 1])

    # Each decoy contains c, hence every candidate in the declared language hits
    # it. Multiplicities are whole periods, so they mask magnitudes but not the
    # low-order pairing/rank invariant.
    seen_decoys: set[tuple[int, ...]] = set()
    moving = r_label + a_label
    while len(seen_decoys) < decoy_classes:
        chosen = tuple(sorted(rng.sample(moving, decoy_width)))
        if chosen in seen_decoys:
            continue
        seen_decoys.add(chosen)
        endpoints = sorted((common,) + chosen)
        constraints.append([endpoints, period * rng.randint(1, 3)])

    # This singleton constraint makes the role of the common token structural.
    constraints.append([[common], 1])
    rng.shuffle(constraints)

    occurrences = [0] * element_count
    total_twins = 0
    for endpoints, multiplicity in constraints:
        total_twins += multiplicity
        for vertex in endpoints:
            occurrences[vertex] += multiplicity

    k = n + 1
    thresholds = [occ + k + 1 for occ in occurrences]
    x_threshold = total_twins + k
    start = sorted(r_label + [common])
    end = sorted(a_label + [common])
    answer = [[r_label[var], a_label[var]] for var in hidden_order]

    return {
        "family": "split_graph_order_word",
        "n": n,
        "k": k,
        "element_count": element_count,
        "special_x": element_count,
        "constraint_classes": constraints,
        "constraint_vertex_count": total_twins,
        "graph_vertex_count": element_count + 1 + total_twins,
        "thresholds": thresholds,
        "x_threshold": x_threshold,
        "start": start,
        "end": end,
        "answer": answer,
    }


def render(inst) -> str:
    """Return the complete, exact problem statement seen by a solver."""
    n = inst["n"]
    threshold_lines = "\n".join(
        f"  {v}: {t}" for v, t in enumerate(inst["thresholds"])
    )
    constraint_lines = "\n".join(
        f"  {row}: {multiplicity} : " + " ".join(map(str, endpoints))
        for row, (endpoints, multiplicity) in enumerate(
            inst["constraint_classes"]
        )
    )
    statement = f"""Target-set token-jump certificate on a split graph

The graph below is specified exactly, with large groups of twin vertices written
compactly. It is a simple undirected graph after expansion.

Element vertices are the integer IDs 0 through {inst['element_count'] - 1}.
There is one special vertex x with ID {inst['special_x']}. These
{inst['element_count'] + 1} vertices form a clique: every two distinct vertices
among them are adjacent.

Each constraint row "r: M: v1 v2 ..." creates M distinct independent vertices
W(r,1),...,W(r,M). A W vertex is adjacent exactly to x and to the listed element
vertices. There are no edges between W vertices. Every W vertex has threshold 1.
The listed M is a positive integer multiplicity, not a parallel edge.

An irreversible activation process starts with exactly the vertices of a seed
set active. At each synchronous round, every inactive vertex having at least its
threshold number of active neighbours becomes active. Active vertices never
deactivate. A seed set is a target set when this process eventually activates
the whole expanded graph.

Thresholds of element vertices (vertex: threshold):
{threshold_lines}
The threshold of x={inst['special_x']} is {inst['x_threshold']}.

Constraint twin classes (row: multiplicity: element neighbours):
{constraint_lines}

The start target set X is:
  {' '.join(map(str, inst['start']))}
The end target set Y is:
  {' '.join(map(str, inst['end']))}
Both contain exactly k={inst['k']} vertices.

A token jump simultaneously removes one currently active seed vertex and adds
one vertex not currently in the seed set, preserving the seed-set size. Find a
sequence of exactly n={n} token jumps that changes X into Y and for which X and
every set after a jump is a target set. Because the sequence has exactly n
jumps, every vertex in X\\Y must be removed exactly once, every vertex in Y\\X
must be added exactly once, the sole vertex in X intersection Y is never moved,
and no other vertex may occur in a jump.

Give your final answer inside <answer></answer> tags as a JSON array of exactly
{n} ordered integer pairs [remove, add], in chronological order. Vertex IDs are
0-based; order matters; repeats are forbidden.
Example format only: <answer>[[3,7],[1,5]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the last tagged JSON answer, tolerating surrounding model prose."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _activation_reaches_all(inst, seed_set: set[int]) -> bool:
    """Replay synchronous activation on the compact twin-class split graph."""
    ecount = inst["element_count"]
    x = inst["special_x"]
    if any(v < 0 or v > x for v in seed_set):
        return False
    active_elements = {v for v in seed_set if v < ecount}
    active_x = x in seed_set
    rows = inst["constraint_classes"]
    active_rows = [False] * len(rows)

    # Monotonicity gives a fixed point in at most |V| rounds, but this split
    # construction reaches one in at most ecount+3 compressed rounds.
    for _round in range(ecount + 3):
        new_rows = []
        for idx, (endpoints, _multiplicity) in enumerate(rows):
            if not active_rows[idx] and (
                active_x or any(v in active_elements for v in endpoints)
            ):
                new_rows.append(idx)

        active_w_total = sum(
            multiplicity
            for is_active, (_endpoints, multiplicity) in zip(active_rows, rows)
            if is_active
        )
        incident_active = [0] * ecount
        for is_active, (endpoints, multiplicity) in zip(active_rows, rows):
            if is_active:
                for v in endpoints:
                    incident_active[v] += multiplicity

        clique_active_neighbours = len(active_elements) + int(active_x)
        new_elements = {
            v for v in range(ecount) if v not in active_elements
            and clique_active_neighbours + incident_active[v]
            >= inst["thresholds"][v]
        }
        new_x = (
            not active_x
            and len(active_elements) + active_w_total >= inst["x_threshold"]
        )
        if not new_rows and not new_elements and not new_x:
            break
        for idx in new_rows:
            active_rows[idx] = True
        active_elements.update(new_elements)
        active_x = active_x or new_x

    return (
        len(active_elements) == ecount
        and active_x
        and all(active_rows)
    )


def _threshold_signature(inst, vertex: int) -> tuple[int, int]:
    """Return (pair tag, rank residue) derived only from public thresholds."""
    n = inst["n"]
    base = 2 * n + 1
    period = base * n
    occurrence = inst["thresholds"][vertex] - (inst["k"] + 1)
    residue = occurrence % period
    return divmod(residue, base)


def verify(inst, answer) -> tuple[bool, str]:
    """Accept every valid word in the declared language; never read answer key."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) != n:
        return False, f"expected exactly {n} jumps"

    x_only = set(inst["start"]) - set(inst["end"])
    y_only = set(inst["end"]) - set(inst["start"])
    removes = []
    adds = []
    for idx, move in enumerate(answer, 1):
        if not isinstance(move, list) or len(move) != 2:
            return False, f"jump {idx} must be a two-integer JSON array"
        remove, add = move
        if (
            isinstance(remove, bool) or not isinstance(remove, int)
            or isinstance(add, bool) or not isinstance(add, int)
        ):
            return False, f"jump {idx} contains a non-integer vertex ID"
        if not (0 <= remove < inst["element_count"]):
            return False, f"jump {idx} remove vertex is out of range"
        if not (0 <= add < inst["element_count"]):
            return False, f"jump {idx} add vertex is out of range"
        if remove not in x_only:
            return False, f"jump {idx} removes a vertex outside X\\Y"
        if add not in y_only:
            return False, f"jump {idx} adds a vertex outside Y\\X"
        removes.append(remove)
        adds.append(add)

    if len(set(removes)) != n:
        return False, "a remove vertex is repeated"
    if len(set(adds)) != n:
        return False, "an add vertex is repeated"

    # Cheap exact necessary checks keep G4's 200k malformed candidates cheap.
    # They are derived from graph thresholds and are followed by native graph
    # activation replay for every candidate that survives.
    for idx, (remove, add) in enumerate(answer, 1):
        r_tag, r_rank = _threshold_signature(inst, remove)
        a_tag, a_reverse_rank = _threshold_signature(inst, add)
        if r_tag != a_tag or r_rank + a_reverse_rank != n - 1:
            return False, f"jump {idx} empties a mandatory twin class"
        if r_rank != idx - 1:
            return False, f"jump {idx} violates a precedence twin class"

    current = set(inst["start"])
    if len(current) != inst["k"] or not _activation_reaches_all(inst, current):
        return False, "the stated start set is not a target set"
    for idx, (remove, add) in enumerate(answer, 1):
        if remove not in current:
            return False, f"jump {idx} removes an absent seed"
        if add in current:
            return False, f"jump {idx} adds an existing seed"
        current.remove(remove)
        current.add(add)
        if len(current) != inst["k"]:
            return False, f"jump {idx} changes the seed-set size"
        if not _activation_reaches_all(inst, current):
            return False, f"set after jump {idx} is not a target set"
    if current != set(inst["end"]):
        return False, "the final seed set is not Y"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the structure-aware bounded certificate language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    removes = sorted(set(inst["start"]) - set(inst["end"]))
    adds = sorted(set(inst["end"]) - set(inst["start"]))
    rng.shuffle(removes)
    rng.shuffle(adds)
    return [[r, a] for r, a in zip(removes, adds)]


def search_space(inst) -> int | None:
    """The two independent endpoint-difference permutations in the language."""
    return math.factorial(inst["n"]) ** 2


def enumerate_all(inst) -> int | None:
    """Brute-force the bounded language only at genuinely tiny settings."""
    n = inst["n"]
    if n > 5:
        return None
    removes = sorted(set(inst["start"]) - set(inst["end"]))
    adds = sorted(set(inst["end"]) - set(inst["start"]))
    count = 0
    for rp in itertools.permutations(removes):
        for ap in itertools.permutations(adds):
            ok, _why = verify(inst, [[r, a] for r, a in zip(rp, ap)])
            count += int(ok)
    return count


def _reference_decode(inst, with_operations=False):
    """Decode the hitting-set precedence DAG and apply Kahn topological sort."""
    x_only = set(inst["start"]) - set(inst["end"])
    y_only = set(inst["end"]) - set(inst["start"])
    partner_x_to_y = {}
    partner_y_to_x = {}
    operations = 0

    for endpoints, multiplicity in inst["constraint_classes"]:
        operations += 1
        if len(endpoints) == 2 and multiplicity > 1:
            a, b = endpoints
            operations += 2
            if a in x_only and b in y_only:
                partner_x_to_y[a] = b
                partner_y_to_x[b] = a
            elif b in x_only and a in y_only:
                partner_x_to_y[b] = a
                partner_y_to_x[a] = b
    if set(partner_x_to_y) != x_only or set(partner_y_to_x) != y_only:
        return (None, operations) if with_operations else None

    outgoing = {v: set() for v in x_only}
    indegree = {v: 0 for v in x_only}
    for endpoints, multiplicity in inst["constraint_classes"]:
        operations += 1
        if len(endpoints) != 2 or multiplicity != 1:
            continue
        a, b = endpoints
        if a in x_only and b in y_only:
            late, early = a, partner_y_to_x[b]
        elif b in x_only and a in y_only:
            late, early = b, partner_y_to_x[a]
        else:
            continue
        operations += 2
        if late != early and late not in outgoing[early]:
            outgoing[early].add(late)
            indegree[late] += 1

    available = sorted(v for v, d in indegree.items() if d == 0)
    order = []
    while available:
        operations += 1
        vertex = available.pop(0)
        order.append(vertex)
        for nxt in outgoing[vertex]:
            operations += 1
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                available.append(nxt)
        available.sort()
    if len(order) != inst["n"]:
        return (None, operations) if with_operations else None
    answer = [[v, partner_x_to_y[v]] for v in order]
    return (answer, operations) if with_operations else answer


def _canonical_representation(inst, reverse_roles=False):
    start = set(inst["end"] if reverse_roles else inst["start"])
    end = set(inst["start"] if reverse_roles else inst["end"])
    x_only = start - end
    y_only = end - start

    partner_y_to_x = {}
    for endpoints, multiplicity in inst["constraint_classes"]:
        if len(endpoints) != 2 or multiplicity <= 1:
            continue
        a, b = endpoints
        if a in x_only and b in y_only:
            partner_y_to_x[b] = a
        elif b in x_only and a in y_only:
            partner_y_to_x[a] = b

    outgoing = {v: set() for v in x_only}
    indegree = {v: 0 for v in x_only}
    for endpoints, multiplicity in inst["constraint_classes"]:
        if len(endpoints) != 2 or multiplicity != 1:
            continue
        a, b = endpoints
        if a in x_only and b in y_only:
            late, early = a, partner_y_to_x[b]
        elif b in x_only and a in y_only:
            late, early = b, partner_y_to_x[a]
        else:
            continue
        if late != early and late not in outgoing[early]:
            outgoing[early].add(late)
            indegree[late] += 1

    available = sorted(v for v, d in indegree.items() if d == 0)
    order = []
    while available:
        v = available.pop(0)
        order.append(v)
        for w in sorted(outgoing[v]):
            indegree[w] -= 1
            if indegree[w] == 0:
                available.append(w)
        available.sort()
    if len(order) != inst["n"]:
        raise ValueError("instance has no canonical total precedence order")

    rank = {v: i for i, v in enumerate(order)}
    canon = {}
    for xv in order:
        canon[xv] = [rank[xv], 0]
    for yv, xv in partner_y_to_x.items():
        canon[yv] = [rank[xv], 1]
    common = next(iter(start & end))
    canon[common] = [-1, 2]

    normalized_rows = []
    for endpoints, multiplicity in inst["constraint_classes"]:
        normalized_rows.append(
            [sorted(canon[v] for v in endpoints), multiplicity]
        )
    normalized_rows.sort()
    return [inst["n"], inst["k"], normalized_rows]


def canonical_key(inst) -> str:
    """Canonicalize element relabelling, row order, and endpoint reversal."""
    forward = _canonical_representation(inst, False)
    backward = _canonical_representation(inst, True)
    payload = min(
        json.dumps(forward, separators=(",", ":")),
        json.dumps(backward, separators=(",", ":")),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow shuffled redundant graph structure without lengthening the witness."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p["n"])
    width = int(p.get("decoy_width", 4))
    current = int(p.get("decoy_classes", 0))
    limit = math.comb(2 * n, width)
    if current < limit:
        p["decoy_classes"] = min(limit, max(current + 1, current * 2))
        return p
    if width < min(8, 2 * n):
        p["decoy_width"] = width + 1
        p["decoy_classes"] = current + 1
        return p
    return None


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _transform_instance(inst, rng, swap_endpoints=False):
    """Return a genuine graph relabelling/row permutation, carrying the witness."""
    out = json.loads(json.dumps(inst))
    perm = list(range(inst["element_count"]))
    rng.shuffle(perm)
    new_thresholds = [0] * inst["element_count"]
    for old, new in enumerate(perm):
        new_thresholds[new] = inst["thresholds"][old]
    out["thresholds"] = new_thresholds
    out["start"] = sorted(perm[v] for v in inst["start"])
    out["end"] = sorted(perm[v] for v in inst["end"])
    out["constraint_classes"] = [
        [sorted(perm[v] for v in endpoints), multiplicity]
        for endpoints, multiplicity in inst["constraint_classes"]
    ]
    rng.shuffle(out["constraint_classes"])
    out["answer"] = [[perm[r], perm[a]] for r, a in inst["answer"]]
    if swap_endpoints:
        out["start"], out["end"] = out["end"], out["start"]
        out["answer"] = [[a, r] for r, a in reversed(out["answer"])]
    return out


def _attack_input_order(inst):
    removes = sorted(set(inst["start"]) - set(inst["end"]))
    adds = sorted(set(inst["end"]) - set(inst["start"]))
    return [[r, a] for r, a in zip(removes, adds)]


def _pair_from_twin_rows(inst):
    x_only = set(inst["start"]) - set(inst["end"])
    y_only = set(inst["end"]) - set(inst["start"])
    pairs = []
    for endpoints, multiplicity in inst["constraint_classes"]:
        if len(endpoints) == 2 and multiplicity > 1:
            a, b = endpoints
            if a in x_only and b in y_only:
                pairs.append([a, b])
            elif b in x_only and a in y_only:
                pairs.append([b, a])
    return pairs


def _attack_raw_threshold(inst):
    removes = sorted(set(inst["start"]) - set(inst["end"]),
                     key=lambda v: (inst["thresholds"][v], v))
    unused = set(inst["end"]) - set(inst["start"])
    pairs = []
    for r in removes:
        a = min(unused, key=lambda v: (abs(inst["thresholds"][r]
                                           - inst["thresholds"][v]), v))
        unused.remove(a)
        pairs.append([r, a])
    return pairs


def _attack_greedy_gap(inst):
    pairs = _pair_from_twin_rows(inst)
    pairs.sort(key=lambda p: (abs(inst["thresholds"][p[0]]
                                  - inst["thresholds"][p[1]]), p))
    return pairs


def _attack_twin_numeric(inst):
    pairs = _pair_from_twin_rows(inst)
    pairs.sort(key=lambda p: p[0])
    return pairs


def selftest() -> dict:
    """Run all mandatory gates and return a JSON-native measurement report."""
    report = {
        "paper": "2107.09885",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every rung and several unrelated seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 23):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]

    # G2: five distinct corruptions must reach five distinct rejection reasons.
    corruptions = {}
    corruptions["drop"] = planted[:-1]
    swapped = json.loads(json.dumps(planted))
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap"] = swapped
    duplicate = json.loads(json.dumps(planted))
    duplicate[1] = duplicate[0]
    corruptions["duplicate"] = duplicate
    corruptions["empty"] = []
    out_of_range = json.loads(json.dumps(planted))
    out_of_range[0][0] = shipping["element_count"] + 10
    corruptions["out_of_range"] = out_of_range
    reasons = {}
    g2_ok = True
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        reasons[name] = why
        g2_ok = g2_ok and not ok
    g2_ok = g2_ok and len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "cases": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    # G3: realistic prose + Markdown fencing around the tagged payload.
    model_reply = (
        "I decoded the threshold residues and replayed every jump.\n"
        "<answer>\n```json\n" + json.dumps(planted) + "\n```\n</answer>\n"
        "The sequence reaches Y."
    )
    parsed = parse_answer(model_reply)
    parse_ok = parsed == planted and verify(shipping, parsed)[0]
    report["G3_round_trip"] = {
        "pass": parse_ok,
        "parsed_equals_planted": parsed == planted,
        "realistic_prose_and_fence": True,
    }

    # G4: structure-aware candidates already obey both endpoint permutations.
    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        guess_hits += int(verify(shipping, candidate)[0])
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(shipping),
    }

    # G5 and Track-B reference measurement at the actual shipping preset.
    ref_times = []
    ref_ops = []
    ref_successes = 0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        t0 = time.perf_counter()
        candidate, operations = _reference_decode(inst, True)
        elapsed = time.perf_counter() - t0
        ref_times.append(elapsed)
        ref_ops.append(operations)
        ref_successes += int(candidate is not None and verify(inst, candidate)[0])
    exact_space = search_space(shipping)
    exact_density = 1.0 / exact_space
    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_hits == 0 and demo_count == 1 and ref_successes == 8
            and min(ref_ops) > 1000
        ),
        "shipping_exact_valid_answer_count": 1,
        "shipping_candidate_space": exact_space,
        "shipping_exact_solution_fraction": exact_density,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_bruteforce_valid_count": demo_count,
        "reference_wall_clock_sec_mean": sum(ref_times) / len(ref_times),
        "reference_wall_clock_sec_max": max(ref_times),
        "reference_operation_count_mean": sum(ref_ops) / len(ref_ops),
        "reference_operation_count_max": max(ref_ops),
    }

    # G6: every attack listed here must fail; the successful polynomial decoder
    # is deliberately and honestly separated as Track B's reference algorithm.
    attack_results = {
        "input_order_zip": {"successes": 0, "attempts": 0},
        "outlier_raw_threshold": {"successes": 0, "attempts": 0},
        "greedy_smallest_threshold_gap": {"successes": 0, "attempts": 0},
        "in_context_twin_pairs_numeric_order": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
    }
    for seed in range(900, 908):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "input_order_zip": _attack_input_order(inst),
            "outlier_raw_threshold": _attack_raw_threshold(inst),
            "greedy_smallest_threshold_gap": _attack_greedy_gap(inst),
            "in_context_twin_pairs_numeric_order": _attack_twin_numeric(inst),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
        rr_rng = random.Random(10_000 + seed)
        solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rr_rng))[0]:
                solved = True
                break
        attack_results["random_restart_256"]["attempts"] += 1
        attack_results["random_restart_256"]["successes"] += int(solved)
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "constraint extraction plus Kahn topological sort",
            "complexity": "O(c+n^2) on c compressed twin classes",
            "wall_clock_sec": sum(ref_times) / len(ref_times),
            "operations": int(round(sum(ref_ops) / len(ref_ops))),
            "compressed_classes": len(shipping["constraint_classes"]),
            "expanded_graph_vertices": shipping["graph_vertex_count"],
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    # G7: both n and the fixed-answer-length decoy axis scale.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["decoy_classes"] *= 2
    t0 = time.perf_counter()
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_build_sec = time.perf_counter() - t0
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    escalated_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    escalated = make_instance(seed=161803, **escalated_params)
    escalated_ok, escalated_why = verify(escalated, escalated["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_compressed_classes": len(shipping["constraint_classes"]),
        "doubled_compressed_classes": len(doubled["constraint_classes"]),
        "doubled_build_sec": doubled_build_sec,
        "doubled_verify_reason": doubled_why,
        "escalated_params": escalated_params,
        "escalated_verify_reason": escalated_why,
    }

    # G8: graph relabelling, row permutation, their composition with endpoint
    # reversal, and carried-witness validity over twenty unrelated seeds.
    invariant_checks = 0
    invariant_passes = 0
    real_transform_checks = 0
    real_transform_passes = 0
    distinct_keys = []
    g8_params = DIFFICULTY["easy"]
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **g8_params)
        key = canonical_key(inst)
        distinct_keys.append(key)
        for j, swap in enumerate((False, True, False)):
            transformed = _transform_instance(
                inst, random.Random(30_000 + 10 * seed + j),
                swap_endpoints=swap,
            )
            invariant_checks += 1
            invariant_passes += int(canonical_key(transformed) == key)
            real_transform_checks += 1
            real_transform_passes += int(
                verify(transformed, transformed["answer"])[0]
            )
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_passes == invariant_checks
            and real_transform_passes == real_transform_checks
            and distinct_count == 20
        ),
        "invariance_passes": invariant_passes,
        "invariance_attempts": invariant_checks,
        "real_transformation_passes": real_transform_passes,
        "real_transformation_attempts": real_transform_checks,
        "distinct_unrelated_keys": distinct_count,
        "distinct_unrelated_attempts": 20,
        "transformations": [
            "element-vertex relabelling",
            "constraint-row permutation",
            "composition with endpoint reversal",
        ],
    }

    # G9(a,b) are recorded diagnostics; only the measured caps gate.
    size_samples = [
        make_instance(seed=40_000 + seed,
                      **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        for seed in range(20)
    ]
    answer_chars = max(len(json.dumps(a))
                       for a in size_samples)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = max(_answer_atoms(a) for a in size_samples)
    intended_ops = 6 * shipping["n"]
    arms = {
        name: dict(G9_MEASUREMENTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "placebo_verdict": G9_MEASUREMENTS["placebo_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
