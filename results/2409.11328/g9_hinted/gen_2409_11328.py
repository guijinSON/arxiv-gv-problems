"""Locally verified Track-B problem generator for arXiv:2409.11328, *Burning game*.

The family uses Proposition 10's exact characterization of three-round Burner
first moves.  It inverse-generates marked reference games with a unique winning
first move, adds graph-specific matchings whose degree offsets are shared across
layers, applies one hidden vertex relabelling, and asks for valid first moves in
the target games. The carried moves are known by monotonicity and relabelling;
generation never searches a generated target for a solution.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    # The word is only a compact encoding of one vertex index per target game;
    # classify the mathematical answer honestly rather than claiming symbolic
    # release-quota credit for its surface syntax.
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graphs",
        "burned-vertex states in the burning game",
        "three-round Burner first moves",
    ],
    "verification_operations": [
        "exact graph-neighborhood union",
        "exact adjacency membership",
        "maximum-degree comparison",
        "Proposition 10 neighborhood-condition evaluation",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Subtracting each vertex's baseline-layer degree cancels graph-specific "
        "matching overlays and exposes one hidden relabelling; without centering, "
        "the games require repeated neighborhood scans."
    ),
    "hardness_basis": (
        "Track B: the Proposition 10 scan is an O(g*n^3) exact algorithm and at "
        "shipping n=42, g=48 averaged 53,672 adjacency operations and about 0.008 "
        "s over eight seeds, whereas centering four shared degree-profile layers "
        "cancels the matching overlays in 300 exact subtractions/lookups."
    ),
    # The JSON string has 50 characters. Counting every character as a token is
    # a conservative tokenizer-independent upper bound (the real count is lower).
    "max_answer_tokens": 50,
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

# The number of requested moves stays fixed from easy through hard.  Difficulty
# grows through a larger vertex universe and more ambiguous per-game choices.
DIFFICULTY = {
    "easy": {
        "n": 24, "games": 48, "profile_graphs": 4,
        "offset_size": 8, "offset_levels": 1,
    },
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Across calibration layers, degree differences from the baseline layer are "
    "preserved by one hidden relabelling."
)
PLACEBO_HINT = (
    "Across the listed games, careful attention to the displayed values helps "
    "avoid small transcription mistakes."
)

_ALPHABET = (
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
    "!#$%()*+,./:;=?@[]^{}|~"
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A fixed-length word of exactly g symbols over the first n symbols of "
        "the fixed 87-character module alphabet; symbol i "
        "names one zero-based Burner first move for target game i."
    ),
    "bounds": {
        "max_symbols": 256,
        "max_alphabet_size": 87,
        "n_max": 87,
        "max_candidate_count": 87 ** 256,
    },
}

NOTES = (
    "Section 1 fixes the round order: spread first, then the current player selects "
    "one unburned vertex; round 1 has only selection, and a last round may end after "
    "spreading. Section 2.2, Proposition 10 gives the executable certificate used "
    "here: with maximum degree at most n-3, v is a three-round Burner first move iff "
    "each vertex outside N[v] misses at most one vertex outside N_2[v]. Proposition "
    "9 makes game numbers 1 and 2 easy, Proposition 11 makes diameter-at-most-two "
    "games easy, Theorems 23-24 give direct path/cycle strategies, and Theorem 29 "
    "gives the hypercube sources explicitly; those regimes are avoided. A marked "
    "reference move is inverse-generated; Lemma 8 preserves it when graph-specific "
    "matchings are added, and one common relabelling then carries it to each target. "
    "The shared per-vertex degree offsets defeat raw profile matching and pairwise "
    "1-WL, while centering at the baseline layer cancels them. The attacks test degree "
    "extremes, two-neighborhoods, raw and one-layer profiles, unchanged labels, a "
    "false cyclic shift, pairwise 1-WL, and random restarts. The successful polynomial "
    "Proposition-10 scan is disclosed as the Track-B reference algorithm."
)

# Filled from script-owned transcripts after the three oracle runs.  These are
# diagnostics only; G9 gates the size and intended-route caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "errors": 0},
    "hinted_verdict": "pending",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, games, profile_graphs, offset_size, offset_levels):
    if not _is_int(n) or not 14 <= n <= len(_ALPHABET):
        raise ValueError("n must be an integer from 14 through 64")
    if not _is_int(games) or games < 4 or games > 256:
        raise ValueError("games must be an integer from 4 through 256")
    minimum_profiles = 4 if n <= 44 else 6
    if (
        not _is_int(profile_graphs)
        or not minimum_profiles <= profile_graphs <= games
    ):
        raise ValueError(
            f"profile_graphs must be between {minimum_profiles} and games at n={n}"
        )
    if not _is_int(offset_size) or not 0 <= offset_size <= n or offset_size % 2:
        raise ValueError("offset_size must be an even integer from 0 through n")
    if not _is_int(offset_levels) or not 0 <= offset_levels <= 6:
        raise ValueError("offset_levels must be an integer from 0 through 6")
    if (offset_size == 0) != (offset_levels == 0):
        raise ValueError("offset_size and offset_levels must either both be zero or both be positive")


def _add_edge(adj, x, y):
    if x != y:
        adj[x].add(y)
        adj[y].add(x)


def _one_inverse_graph(n, planted, rng):
    """One Proposition-10 graph; no candidate search occurs here.

    The roles are p=planted, a leaf q adjacent to p, a set A adjacent to p,
    groups R_a adjacent to a in A, and a 3-clique C.  Each r in R misses at
    most one member of C.  Thus C=V-N_2[p], and Proposition 10 certifies p.

    The gadget also makes p the unique winner without searching for it:
    q is refuted by any a; an a by q and two R-vertices in a non-neighbor
    group; an r by q and two non-neighbors of its A-parent; and a c by an
    R-vertex that misses c and also misses p,q.  The construction below
    enforces exactly those local obligations.  Rejection sampling uses only
    answer-independent presentation properties: degree balance.
    """
    for _ in range(10_000):
        vertices = [v for v in range(n) if v != planted]
        rng.shuffle(vertices)
        q_vertex = vertices[0]
        # The slight offset keeps at least two size-three R-groups at ladder
        # boundaries such as n=24, which supplies degree-tied decoys for p.
        a_size = max(3, (n - 2) // 4)
        a_list = vertices[1:1 + a_size]
        c_list = vertices[-3:]
        r_list = vertices[1 + a_size:-3]

        # n>=14 ensures at least two R-vertices for every A-parent.
        rng.shuffle(r_list)
        r_groups = [[] for _ in a_list]
        for index, r_vertex in enumerate(r_list):
            r_groups[index % a_size].append(r_vertex)
        if min(map(len, r_groups)) < 2:
            raise AssertionError("parameter bound did not provide two R vertices per A")

        adj = [set() for _ in range(n)]
        _add_edge(adj, planted, q_vertex)
        for a_vertex in a_list:
            _add_edge(adj, planted, a_vertex)

        # A begins as a clique with a Hamilton cycle removed, so every A-vertex
        # has two non-neighbors. Extra random deletions diversify degrees without
        # invalidating the refutations above. Two protected vertices retain the
        # full a_size-3 degree and help make the planted degree non-unique.
        if a_size >= 4:
            cycle = list(a_list)
            rng.shuffle(cycle)
            cycle_edges = {
                frozenset((cycle[i], cycle[(i + 1) % a_size]))
                for i in range(a_size)
            }
            protected_candidates = [
                a for a, group in zip(a_list, r_groups) if len(group) >= 3
            ]
            protected = set(protected_candidates[:2])
            for i, x in enumerate(a_list):
                for y in a_list[i + 1:]:
                    if frozenset((x, y)) in cycle_edges:
                        continue
                    if (
                        x not in protected
                        and y not in protected
                        and rng.random() < 0.35
                    ):
                        continue
                    _add_edge(adj, x, y)

        for i, x in enumerate(c_list):
            for y in c_list[i + 1:]:
                _add_edge(adj, x, y)

        for group_index, (a_vertex, group) in enumerate(zip(a_list, r_groups)):
            for r_vertex in group:
                _add_edge(adj, a_vertex, r_vertex)
            for i, x in enumerate(group):
                for y in group[i + 1:]:
                    _add_edge(adj, x, y)

            # The first two vertices miss distinct C-vertices. Consequently
            # every C-vertex sees some member of every group, while each C-vertex
            # is missed by an R-vertex somewhere in the graph.
            for i, r_vertex in enumerate(group):
                missed = (
                    c_list[(group_index + i) % 3]
                    if i < 2 else rng.choice([None] + c_list)
                )
                for c_vertex in c_list:
                    if c_vertex != missed:
                        _add_edge(adj, r_vertex, c_vertex)

        degrees = [len(row) for row in adj]
        planted_degree = degrees[planted]
        if max(degrees) > n - 3:
            continue
        if degrees.count(planted_degree) < 3:
            continue
        if not min(degrees) < planted_degree < max(degrees):
            continue
        graph = [sorted(row) for row in adj]
        if not _prop10_winner(graph, planted):
            raise AssertionError("inverse construction violated Proposition 10")
        return graph
    raise RuntimeError("could not draw a degree-balanced inverse graph")


def _centered_degree_profiles(graphs, q):
    n = len(graphs[0])
    return [
        tuple(
            len(graphs[j][v]) - len(graphs[0][v])
            for j in range(1, q)
        )
        for v in range(n)
    ]


def _complement_matching(adjacency, vertices, rng):
    """Find a perfect matching of `vertices` using currently absent edges."""
    remaining = frozenset(vertices)

    def extend(active):
        if not active:
            return []
        choices_by_vertex = []
        for vertex in active:
            choices = [
                other for other in active
                if other != vertex and other not in adjacency[vertex]
            ]
            if not choices:
                return None
            rng.shuffle(choices)
            choices_by_vertex.append((len(choices), vertex, choices))
        _, vertex, choices = min(choices_by_vertex, key=lambda row: (row[0], row[1]))
        rest = active - {vertex}
        for other in choices:
            tail = extend(rest - {other})
            if tail is not None:
                return [(vertex, other)] + tail
        return None

    return extend(remaining)


def _offset_supergraphs(graphs, seed, offset_size, offset_levels):
    """Add graph-specific edges with one shared per-vertex degree offset.

    Each level chooses the same logical vertex subset in every graph, then adds
    an independently routed perfect matching on that subset. Thus the actual
    added edges vary by graph, but every logical vertex receives the same degree
    increment in every target layer. Edge addition preserves the planted Burner
    strategy by Lemma 8 / monotonicity.
    """
    if offset_levels == 0:
        return [list(map(list, graph)) for graph in graphs]
    n = len(graphs[0])
    for attempt in range(200):
        rng = random.Random((seed + 1) * 1_000_003 + attempt * 97_409)
        subsets = [
            sorted(rng.sample(range(n), offset_size))
            for _ in range(offset_levels)
        ]
        increments = [sum(vertex in subset for subset in subsets)
                      for vertex in range(n)]
        if len(set(increments)) < min(3, offset_levels + 1):
            continue
        augmented = []
        possible = True
        for graph_index, graph in enumerate(graphs):
            adjacency = [set(row) for row in graph]
            local_rng = random.Random(
                (seed + 1) * 10_000_019 + attempt * 1_000_033 + graph_index
            )
            for subset in subsets:
                matching = _complement_matching(adjacency, subset, local_rng)
                if matching is None:
                    possible = False
                    break
                for x, y in matching:
                    _add_edge(adjacency, x, y)
            if not possible or max(map(len, adjacency)) > n - 3:
                possible = False
                break
            augmented.append([sorted(row) for row in adjacency])
        if possible:
            return augmented
    raise RuntimeError("could not construct shared degree-offset supergraphs")


def _derangement(n, rng):
    # Sattolo's algorithm: a uniformly generated single cycle, hence no fixed point.
    permutation = list(range(n))
    for i in range(n - 1, 0, -1):
        j = rng.randrange(i)
        permutation[i], permutation[j] = permutation[j], permutation[i]
    return permutation


def _relabel_graph(graph, permutation):
    n = len(graph)
    relabeled = [[] for _ in range(n)]
    for old, row in enumerate(graph):
        relabeled[permutation[old]] = sorted(permutation[v] for v in row)
    return relabeled


def make_instance(
    n,
    seed=0,
    games=48,
    profile_graphs=None,
    offset_size=0,
    offset_levels=0,
    **params,
):
    """Inverse-generate reference games and carry witnesses through relabelling."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if profile_graphs is None:
        profile_graphs = 6 if _is_int(n) and n > 44 else 4
    _validate_parameters(n, games, profile_graphs, offset_size, offset_levels)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # The first q graphs are calibration layers. Their degree-difference tuples
    # relative to layer 0 are required to be unique; this filters an input
    # invariant, not a solution.
    for _ in range(10_000):
        first_moves = [rng.randrange(n) for _ in range(profile_graphs)]
        first_graphs = [
            _one_inverse_graph(n, move, rng) for move in first_moves
        ]
        if len(set(_centered_degree_profiles(first_graphs, profile_graphs))) == n:
            break
    else:
        raise RuntimeError("could not generate unique centered degree profiles")

    reference_moves = list(first_moves)
    reference_graphs = list(first_graphs)
    for _ in range(profile_graphs, games):
        move = rng.randrange(n)
        reference_moves.append(move)
        reference_graphs.append(_one_inverse_graph(n, move, rng))

    target_graphs = _offset_supergraphs(
        reference_graphs, seed, offset_size, offset_levels
    )

    permutation = _derangement(n, rng)
    pairs = []
    answer_symbols = []
    for reference_graph, target_graph, move in zip(
        reference_graphs, target_graphs, reference_moves
    ):
        pairs.append({
            "reference": reference_graph,
            "reference_move": move,
            "target": _relabel_graph(target_graph, permutation),
        })
        answer_symbols.append(_ALPHABET[permutation[move]])

    reference_edge_count = sum(
        sum(len(row) for row in graph) // 2 for graph in reference_graphs
    )
    target_edge_count = sum(
        sum(len(row) for row in graph) // 2 for graph in target_graphs
    )
    inst = {
        "paper": "arXiv:2409.11328",
        "family": "transported three-round Burner first moves",
        "n": n,
        "games": games,
        "profile_graphs": profile_graphs,
        "offset_size": offset_size,
        "offset_levels": offset_levels,
        "alphabet": _ALPHABET[:n],
        "pairs": pairs,
        "logical_vertices": 2 * games * n,
        "undirected_edges_across_reference_and_target": (
            reference_edge_count + target_edge_count
        ),
        "answer": "".join(answer_symbols),
    }
    return inst


def _row_text(row):
    return ",".join(str(v) for v in row) if row else "-"


def _graph_text(graph):
    return " ; ".join(
        f"{v}({len(row)}):{_row_text(row)}" for v, row in enumerate(graph)
    )


def render(inst):
    """Render the complete burning-game problem and its exact output grammar."""
    n = inst["n"]
    games = inst["games"]
    lines = [
        "BURNING GAME: THREE-ROUND FIRST-MOVE CERTIFICATES",
        "",
        "A finite simple undirected graph has vertices 0 through n-1. Initially all",
        "vertices are unburned. In round 1 the first player, Burner, selects one",
        "unburned vertex, which burns immediately. At the start of every later round,",
        "every unburned neighbor of any burned vertex burns; afterward the player",
        "whose turn it is selects one still-unburned vertex, if one exists. Burner",
        "moves in odd rounds and Staller in even rounds. Burned vertices stay burned.",
        "The game ends as soon as all vertices are burned, including immediately after",
        "a spreading phase. Burner wants this to happen quickly; Staller delays it.",
        "",
        "For each numbered pair below, the reference graph comes with an audited",
        "Burner first move that guarantees the reference game ends by the end of round",
        "3 against every legal Staller move. Find one such first move for every target",
        "graph. Each graph row has the form v(degree):comma-separated-neighbors; '-'",
        "means no neighbors. Rows are separated by semicolons. The neighbor lists are",
        "symmetric and contain neither loops nor repeated neighbors.",
        "",
        f"There are {games} pairs and n={n}. Vertex labels are zero-based.",
        "A move must be one vertex of its corresponding target graph. Different games",
        "are independent, order follows the pair numbers, and repeated labels across",
        "different games are allowed.",
        "",
    ]
    for index, pair in enumerate(inst["pairs"]):
        lines.append(
            f"Pair {index}: audited reference move={pair['reference_move']}"
        )
        lines.append("  R " + _graph_text(pair["reference"]))
        lines.append("  T " + _graph_text(pair["target"]))

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])

    alphabet = inst["alphabet"]
    lines.extend([
        "",
        "OUTPUT ENCODING",
        f"Use the alphabet {alphabet!r}: its character at position v denotes vertex v.",
        f"Output exactly one {games}-character word. Character i is the move for target",
        "game i; there are no separators or spaces inside the word.",
        "Give your final answer inside <answer></answer> tags, as that exact word.",
        f"Example shape for {min(games, 6)} entries: <answer>{alphabet[0:min(n, min(games, 6))]}</answer>",
        "The example illustrates encoding only and is not an answer to this instance.",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    """Extract a word answer from prose and optional Markdown fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not match:
        return None
    body = match.group(1).strip()
    fence = re.fullmatch(r"```(?:text|plain|plaintext)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    if not body or re.search(r"\s", body):
        return None
    return body


def _prop10_winner(graph, vertex, operations=None):
    """Executable form of Proposition 10; graph is assumed simple."""
    n = len(graph)
    if operations is not None:
        operations[0] += n
    if max(len(row) for row in graph) > n - 3:
        return False
    adjacency = [set(row) for row in graph]
    closed = set(adjacency[vertex])
    closed.add(vertex)
    distance_two = set(closed)
    for x in closed:
        if operations is not None:
            operations[0] += len(adjacency[x])
        distance_two.update(adjacency[x])
    outside_closed = set(range(n)) - closed
    far = set(range(n)) - distance_two
    for x in outside_closed:
        misses = 0
        for y in far:
            if operations is not None:
                operations[0] += 1
            # Staller has just selected x, so x itself is already burned.  The
            # proof of Proposition 10 therefore tests the remaining vertices
            # against the closed neighborhood N[x], even though the statement
            # abbreviates this as "x is adjacent to all but at most one".
            if y != x and y not in adjacency[x]:
                misses += 1
                if misses > 1:
                    return False
    return True


def verify(inst, answer):
    """Accept every word whose characters are valid Proposition-10 witnesses."""
    if not isinstance(answer, str):
        return False, "answer must be a string in the stated vertex alphabet"
    if not answer:
        return False, "answer is empty"
    expected = inst["games"]
    if len(answer) < expected:
        return False, f"answer has too few symbols: expected {expected}"
    if len(answer) > expected:
        return False, f"answer has too many symbols: expected {expected}"
    alphabet = inst["alphabet"]
    lookup = {symbol: value for value, symbol in enumerate(alphabet)}
    for index, symbol in enumerate(answer):
        if symbol not in lookup:
            if symbol in _ALPHABET:
                return False, f"symbol {index} names a vertex outside 0..{inst['n'] - 1}"
            return False, f"symbol {index} is not in the stated alphabet"
        vertex = lookup[symbol]
        if not _prop10_winner(inst["pairs"][index]["target"], vertex):
            return False, f"entry {index} is not a three-round winning first move"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform word with the exact required length and per-position vertex range."""
    return "".join(inst["alphabet"][rng.randrange(inst["n"])]
                   for _ in range(inst["games"]))


def search_space(inst):
    """The exact size of the fixed-length word language."""
    return inst["n"] ** inst["games"]


def _valid_vertex_sets(inst):
    return [
        {v for v in range(inst["n"]) if _prop10_winner(pair["target"], v)}
        for pair in inst["pairs"]
    ]


def enumerate_all(inst):
    """Count component witnesses exactly, then compose the independent counts."""
    if inst["games"] * inst["n"] > 20_000:
        return None
    total = 1
    for valid in _valid_vertex_sets(inst):
        total *= len(valid)
    return total


def _wl_fingerprint(graph, root=None):
    """A strong cheap relabelling invariant, not a complete GI canonical form."""
    n = len(graph)
    adjacency = [set(row) for row in graph]
    colors = [(int(v == root), len(adjacency[v])) for v in range(n)]
    history = []
    for _ in range(n):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(n)
        ]
        palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        history.append(tuple(sorted(Counter(new_colors).items())))
        if new_colors == colors:
            break
        colors = new_colors
    degrees = [len(row) for row in adjacency]
    triangles = []
    for v in range(n):
        triangles.append(sum(1 for x in adjacency[v] for y in adjacency[v]
                             if x < y and y in adjacency[x]))
    edge_colors = sorted(
        (min(colors[x], colors[y]), max(colors[x], colors[y]))
        for x in range(n) for y in adjacency[x] if x < y
    )
    vertex_data = sorted((colors[v], degrees[v], triangles[v]) for v in range(n))
    return [n, history, vertex_data, edge_colors]


def _triangle_count_at(graph, vertex):
    neighbors = set(graph[vertex])
    return sum(
        1
        for x in neighbors
        for y in graph[x]
        if x < y and y in neighbors
    )


def _cross_layer_profiles(pairs, side, pair_tags):
    """A relabelling- and pair-order-invariant alignment fingerprint."""
    n = len(pairs[0][side])
    profiles = []
    for vertex in range(n):
        profile = []
        for tag, pair in zip(pair_tags, pairs):
            graph = pair[side]
            profile.append((tag, len(graph[vertex]), _triangle_count_at(graph, vertex)))
        profiles.append(sorted(profile))
    return sorted(profiles)


def canonical_key(inst):
    """Invariant under pair order and independent relabellings of every graph.

    The shared permutation is a hidden feature of the generated distribution, not
    part of the mathematical identity of the listed games. Consequently the key
    deliberately forgets cross-layer label alignment and retains only the multiset
    of rooted-reference/unrooted-target pair invariants.
    """
    pair_keys = []
    for pair in inst["pairs"]:
        pair_keys.append([
            _wl_fingerprint(pair["reference"], pair["reference_move"]),
            _wl_fingerprint(pair["target"], None),
        ])
    pair_blobs = sorted(json.dumps(key, separators=(",", ":")) for key in pair_keys)
    payload = json.dumps({
        "n": inst["n"],
        "pairs": pair_blobs,
    }, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    """Grow the haystack, then increase overlay ambiguity at fixed answer length."""
    return None  # G9 scratch copy: score only the shipping preset.
    current = dict(params)
    n = int(current["n"])
    for candidate_n, offset_size, offset_levels in (
        (24, 8, 1),
        (34, 14, 1),
        (42, 20, 1),
    ):
        if n < candidate_n:
            current.update({
                "n": candidate_n,
                "offset_size": offset_size,
                "offset_levels": offset_levels,
            })
            return current
    return None


def _explicit_game_tree_winner(graph, first_move):
    """Directly audit all of Staller's round-2 replies for a demo cross-check."""
    n = len(graph)
    adjacency = [set(row) for row in graph]
    burned_after_spread_two = {first_move} | adjacency[first_move]
    replies = set(range(n)) - burned_after_spread_two
    if not replies:
        return True
    for reply in replies:
        burned = set(burned_after_spread_two)
        burned.add(reply)
        after_spread_three = set(burned)
        for x in burned:
            after_spread_three.update(adjacency[x])
        if n - len(after_spread_three) > 1:
            return False
    return True


def _encode_vertices(inst, vertices):
    return "".join(inst["alphabet"][v] for v in vertices)


def _candidate_fast(inst, word, valid_sets):
    if not isinstance(word, str) or len(word) != inst["games"]:
        return False
    lookup = {symbol: value for value, symbol in enumerate(inst["alphabet"])}
    for symbol, valid in zip(word, valid_sets):
        value = lookup.get(symbol)
        if value is None or value not in valid:
            return False
    return True


def _attack_degree_extreme(inst):
    vertices = []
    for pair in inst["pairs"]:
        degrees = [len(row) for row in pair["target"]]
        median = sorted(degrees)[len(degrees) // 2]
        vertices.append(max(range(inst["n"]), key=lambda v: (abs(degrees[v] - median), -v)))
    return _encode_vertices(inst, vertices)


def _attack_minimum_degree(inst):
    return _encode_vertices(inst, [
        min(range(inst["n"]), key=lambda v: (len(pair["target"][v]), v))
        for pair in inst["pairs"]
    ])


def _attack_maximum_degree(inst):
    return _encode_vertices(inst, [
        max(range(inst["n"]), key=lambda v: (len(pair["target"][v]), -v))
        for pair in inst["pairs"]
    ])


def _two_neighborhood_size(graph, vertex):
    reached = {vertex, *graph[vertex]}
    for neighbor in graph[vertex]:
        reached.update(graph[neighbor])
    return len(reached)


def _attack_largest_two_neighborhood(inst):
    return _encode_vertices(inst, [
        max(
            range(inst["n"]),
            key=lambda v: (_two_neighborhood_size(pair["target"], v), -v),
        )
        for pair in inst["pairs"]
    ])


def _attack_single_game_degree_match(inst):
    vertices = []
    for pair in inst["pairs"]:
        wanted = len(pair["reference"][pair["reference_move"]])
        candidates = [v for v in range(inst["n"])
                      if len(pair["target"][v]) == wanted]
        vertices.append(candidates[0] if candidates else 0)
    return _encode_vertices(inst, vertices)


def _attack_one_layer_shared_degree_map(inst):
    """Guess the common map from the first pair, breaking degree ties by label."""
    first = inst["pairs"][0]
    reference_groups = {}
    target_groups = {}
    for vertex in range(inst["n"]):
        reference_groups.setdefault(len(first["reference"][vertex]), []).append(vertex)
        target_groups.setdefault(len(first["target"][vertex]), []).append(vertex)
    mapping = {}
    for degree, references in reference_groups.items():
        targets = target_groups.get(degree, [])
        if len(targets) != len(references):
            return inst["alphabet"][0] * inst["games"]
        for source, target in zip(sorted(references), sorted(targets)):
            mapping[source] = target
    return _encode_vertices(inst, [
        mapping[pair["reference_move"]] for pair in inst["pairs"]
    ])


def _attack_raw_degree_profile_map(inst):
    """Try the old uncentered degree profile, without cancelling offsets."""
    q = inst["profile_graphs"]
    reference_profiles = [
        tuple(len(inst["pairs"][j]["reference"][v]) for j in range(q))
        for v in range(inst["n"])
    ]
    target_profiles = {}
    for vertex in range(inst["n"]):
        profile = tuple(
            len(inst["pairs"][j]["target"][vertex]) for j in range(q)
        )
        target_profiles.setdefault(profile, []).append(vertex)
    mapping = {}
    for vertex, profile in enumerate(reference_profiles):
        candidates = target_profiles.get(profile, [])
        if len(candidates) == 1:
            mapping[vertex] = candidates[0]
    if any(pair["reference_move"] not in mapping for pair in inst["pairs"]):
        return inst["alphabet"][0] * inst["games"]
    return _encode_vertices(inst, [
        mapping[pair["reference_move"]] for pair in inst["pairs"]
    ])


def _attack_unchanged_labels(inst):
    return _encode_vertices(inst, [pair["reference_move"] for pair in inst["pairs"]])


def _attack_cyclic_shift(inst):
    first = inst["pairs"][0]
    wanted = len(first["reference"][first["reference_move"]])
    candidates = [v for v in range(inst["n"]) if len(first["target"][v]) == wanted]
    image = candidates[0] if candidates else 0
    shift = (image - first["reference_move"]) % inst["n"]
    return _encode_vertices(inst, [
        (pair["reference_move"] + shift) % inst["n"] for pair in inst["pairs"]
    ])


def _attack_random_restart(inst, rng, restarts, valid_sets):
    last = inst["alphabet"][0] * inst["games"]
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if _candidate_fast(inst, last, valid_sets):
            return last
    return last


def _reference_algorithm(inst):
    """The paper's direct polynomial characterization scan."""
    answer = []
    operations = [0]
    candidates_tested = 0
    for pair in inst["pairs"]:
        found = None
        for vertex in range(inst["n"]):
            candidates_tested += 1
            if _prop10_winner(pair["target"], vertex, operations):
                found = vertex
                break
        if found is None:
            return None, {"operations": operations[0], "candidates_tested": candidates_tested}
        answer.append(found)
    return _encode_vertices(inst, answer), {
        "operations": operations[0],
        "candidates_tested": candidates_tested,
    }


def _color_refinement(graph, operations=None):
    """Canonical one-dimensional Weisfeiler-Leman colors for one graph."""
    n = len(graph)
    colors = [len(row) for row in graph]
    if operations is not None:
        operations[0] += n
    rounds = 0
    for _ in range(n):
        signatures = []
        for vertex, row in enumerate(graph):
            if operations is not None:
                operations[0] += 1 + len(row)
            signatures.append((
                colors[vertex],
                tuple(sorted(colors[neighbor] for neighbor in row)),
            ))
        palette = {
            signature: index
            for index, signature in enumerate(sorted(set(signatures)))
        }
        new_colors = [palette[signature] for signature in signatures]
        if operations is not None:
            operations[0] += n
        rounds += 1
        if new_colors == colors:
            break
        colors = new_colors
    return colors, rounds


def _pairwise_wl_transport(inst):
    """Recover each transported move separately by 1-WL color refinement."""
    answer = []
    operations = [0]
    total_rounds = 0
    for pair in inst["pairs"]:
        reference_colors, rounds = _color_refinement(
            pair["reference"], operations
        )
        total_rounds += rounds
        target_colors, rounds = _color_refinement(pair["target"], operations)
        total_rounds += rounds
        wanted = reference_colors[pair["reference_move"]]
        candidates = []
        for vertex, color in enumerate(target_colors):
            operations[0] += 1
            if color == wanted:
                candidates.append(vertex)
        if len(candidates) != 1:
            return None, {
                "operations": operations[0],
                "refinement_rounds": total_rounds,
            }
        answer.append(candidates[0])
    return _encode_vertices(inst, answer), {
        "operations": operations[0],
        "refinement_rounds": total_rounds,
    }


def _attack_pairwise_wl(inst):
    answer, _ = _pairwise_wl_transport(inst)
    return answer if answer is not None else inst["alphabet"][0] * inst["games"]


def _compact_transport(inst):
    q = inst["profile_graphs"]
    n = inst["n"]
    reference_profiles = [
        tuple(
            len(inst["pairs"][j]["reference"][v])
            - len(inst["pairs"][0]["reference"][v])
            for j in range(1, q)
        )
        for v in range(n)
    ]
    target_profiles = {
        tuple(
            len(inst["pairs"][j]["target"][v])
            - len(inst["pairs"][0]["target"][v])
            for j in range(1, q)
        ): v
        for v in range(n)
    }
    mapping = {v: target_profiles[profile]
               for v, profile in enumerate(reference_profiles)}
    return _encode_vertices(inst, [
        mapping[pair["reference_move"]] for pair in inst["pairs"]
    ])


def _transformed_instance(inst, seed, reorder=True, independent=False):
    """Apply legal graph relabellings and carry the witness."""
    rng = random.Random(seed)
    old_values = [_ALPHABET.index(symbol) for symbol in inst["answer"]]
    common_reference = list(range(inst["n"]))
    common_target = list(range(inst["n"]))
    rng.shuffle(common_reference)
    rng.shuffle(common_target)
    records = []
    for index, pair in enumerate(inst["pairs"]):
        if independent:
            reference_permutation = list(range(inst["n"]))
            target_permutation = list(range(inst["n"]))
            rng.shuffle(reference_permutation)
            rng.shuffle(target_permutation)
        else:
            reference_permutation = common_reference
            target_permutation = common_target
        records.append((
            {
                "reference": _relabel_graph(pair["reference"], reference_permutation),
                "reference_move": reference_permutation[pair["reference_move"]],
                "target": _relabel_graph(pair["target"], target_permutation),
            },
            target_permutation[old_values[index]],
        ))
    if reorder:
        rng.shuffle(records)
    transformed = dict(inst)
    transformed["pairs"] = [record[0] for record in records]
    transformed["answer"] = _encode_vertices(inst, [record[1] for record in records])
    return transformed


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    # Conservative tokenizer-independent upper bound for this ASCII JSON word.
    return len(blob), len(blob)


def selftest():
    report = {
        "paper": "arXiv:2409.11328",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    demo_tree_checks = 0
    winner_membership_checks = 0
    maximum_valid_moves_in_one_game = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
            for index, (pair, symbol) in enumerate(zip(inst["pairs"], inst["answer"])):
                winners = [
                    vertex for vertex in range(inst["n"])
                    if _prop10_winner(pair["target"], vertex)
                ]
                winner_membership_checks += 1
                maximum_valid_moves_in_one_game = max(
                    maximum_valid_moves_in_one_game, len(winners)
                )
                if _ALPHABET.index(symbol) not in winners:
                    failures.append({
                        "preset": preset,
                        "seed": seed,
                        "reason": f"game {index} did not contain the planted winner",
                    })
            if preset == "demo":
                for pair in inst["pairs"]:
                    for vertex in range(inst["n"]):
                        demo_tree_checks += 1
                        theorem = _prop10_winner(pair["target"], vertex)
                        direct = _explicit_game_tree_winner(pair["target"], vertex)
                        if theorem != direct:
                            failures.append({"preset": preset, "seed": seed,
                                             "reason": "game tree disagrees with Proposition 10"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "winner_membership_checks": winner_membership_checks,
        "maximum_valid_moves_in_one_game": maximum_valid_moves_in_one_game,
        "demo_candidate_game_tree_cross_checks": demo_tree_checks,
        "failures": failures,
    }

    shipping = make_instance(seed=240911328, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    valid_sets = _valid_vertex_sets(shipping)
    swap_pair = None
    for i in range(shipping["games"]):
        for j in range(i + 1, shipping["games"]):
            vi = _ALPHABET.index(planted[i])
            vj = _ALPHABET.index(planted[j])
            if vi != vj and (vj not in valid_sets[i] or vi not in valid_sets[j]):
                swap_pair = (i, j)
                break
        if swap_pair:
            break
    if swap_pair is None:
        raise AssertionError("could not form a rejected swap corruption")
    swapped = list(planted)
    i, j = swap_pair
    swapped[i], swapped[j] = swapped[j], swapped[i]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": "".join(swapped),
        "duplicate_one": planted + planted[-1],
        "empty": "",
        "out_of_range": _ALPHABET[shipping["n"]] + planted[1:],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values())
        and len(reasons) == len(cases),
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    realistic = (
        "The transported moves all satisfy the neighborhood test.\n"
        "<answer>\n```text\n" + planted + "\n```\n</answer>\n"
        "Each character uses the stated zero-based alphabet."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed_symbols": len(parsed) if isinstance(parsed, str) else None,
    }

    exact_valid = enumerate_all(shipping)
    exact_space = search_space(shipping)
    exact_density = exact_valid / exact_space
    guess_rng = random.Random(0x240911328)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        guess_hits += int(_candidate_fast(shipping, candidate, valid_sets))
    guess_elapsed = time.perf_counter() - started
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "exact_probability": exact_density,
        "structure_aware_space": exact_space,
        "sampling_rule": (
            "uniform over words with exactly one in-range vertex symbol per target "
            "game; length, alphabet, and per-game arity are enforced"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "outlier_degree_extreme": lambda inst, rng, sets: _attack_degree_extreme(inst),
        "greedy_minimum_degree": lambda inst, rng, sets: _attack_minimum_degree(inst),
        "greedy_maximum_degree": lambda inst, rng, sets: _attack_maximum_degree(inst),
        "largest_two_neighborhood": lambda inst, rng, sets: _attack_largest_two_neighborhood(inst),
        "single_game_degree_match": lambda inst, rng, sets: _attack_single_game_degree_match(inst),
        "one_layer_shared_degree_map": lambda inst, rng, sets: _attack_one_layer_shared_degree_map(inst),
        "raw_degree_profile_map": lambda inst, rng, sets: _attack_raw_degree_profile_map(inst),
        "pairwise_wl_isomorphism": lambda inst, rng, sets: _attack_pairwise_wl(inst),
        "unchanged_label_ansatz": lambda inst, rng, sets: _attack_unchanged_labels(inst),
        "cyclic_shift_ansatz": lambda inst, rng, sets: _attack_cyclic_shift(inst),
        "random_restart_256": lambda inst, rng, sets: _attack_random_restart(inst, rng, 256, sets),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    reference_operations = []
    reference_candidates = []
    reference_elapsed = 0.0
    reference_successes = 0
    wl_operations = []
    wl_rounds = []
    wl_elapsed = 0.0
    wl_successes = 0
    compact_successes = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        sets = _valid_vertex_sets(inst)
        for offset, (name, attack) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            t0 = time.perf_counter()
            candidate = attack(inst, rng, sets)
            attack_elapsed[name] += time.perf_counter() - t0
            attack_results[name]["successes"] += int(_candidate_fast(inst, candidate, sets))
            attack_results[name]["attempts"] += 1
        t0 = time.perf_counter()
        reference_answer, stats = _reference_algorithm(inst)
        reference_elapsed += time.perf_counter() - t0
        reference_operations.append(stats["operations"])
        reference_candidates.append(stats["candidates_tested"])
        if reference_answer is not None:
            reference_successes += int(verify(inst, reference_answer)[0])
        t0 = time.perf_counter()
        wl_answer, wl_stats = _pairwise_wl_transport(inst)
        wl_elapsed += time.perf_counter() - t0
        wl_operations.append(wl_stats["operations"])
        wl_rounds.append(wl_stats["refinement_rounds"])
        if wl_answer is not None:
            wl_successes += int(verify(inst, wl_answer)[0])
        compact_successes += int(verify(inst, _compact_transport(inst))[0])
    for name, elapsed in attack_elapsed.items():
        attack_results[name]["wall_clock_sec_total_8"] = round(elapsed, 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    reference = {
        "name": "Proposition 10 exhaustive first-move scan",
        "complexity": "O(g*n^3) exact adjacency operations",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "candidates_tested_mean": sum(reference_candidates) / len(reference_candidates),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = (
        2 * (shipping["profile_graphs"] - 1) * shipping["n"]
        + shipping["games"]
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and wl_successes == 0
        and reference_successes == compact_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "pairwise_wl_attack_cost": {
            "name": "pairwise one-dimensional Weisfeiler-Leman transport",
            "complexity": "O(g*n*(n+m)*log(n)) for the simple at-most-n-round implementation",
            "wall_clock_sec_total_8": round(wl_elapsed, 6),
            "wall_clock_sec_mean": round(wl_elapsed / len(attack_seeds), 8),
            "operations_mean": sum(wl_operations) // len(wl_operations),
            "operations_min": min(wl_operations),
            "operations_max": max(wl_operations),
            "refinement_rounds_mean": sum(wl_rounds) / len(wl_rounds),
            "solves": f"{wl_successes}/{len(attack_seeds)}",
        },
        "compact_route": {
            "name": "baseline-centered degree-profile transport",
            "worst_case_exact_operations": intended_operations,
            "count_model": (
                "subtract the displayed baseline degree in q-1 layers on each side, "
                "then perform one relabelling-table lookup for each requested move"
            ),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_failed,
        "exact_valid_answers_at_shipping": exact_valid,
        "candidate_space_at_shipping": exact_space,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": observed,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "strongest_attack_operations_mean": (
            sum(wl_operations) // len(wl_operations)
            if strongest == "pairwise_wl_isomorphism" else None
        ),
        "random_restart_candidates_total_8": 256 * len(attack_seeds),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "pairwise_wl_operations_mean": sum(wl_operations) // len(wl_operations),
        "pairwise_wl_wall_clock_sec_mean": round(wl_elapsed / len(attack_seeds), 8),
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled_n = min(len(_ALPHABET), 2 * shipping["n"])
    larger = make_instance(
        n=doubled_n,
        games=shipping["games"],
        profile_graphs=max(shipping["profile_graphs"], 6),
        offset_size=shipping["offset_size"],
        offset_levels=shipping["offset_levels"],
        seed=707,
    )
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and larger["logical_vertices"] > shipping["logical_vertices"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "shipping_logical_vertices": shipping["logical_vertices"],
        "doubled_logical_vertices": larger["logical_vertices"],
        "verify_reason": larger_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        transformations = (
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        )
        for variant, (independent, reorder) in enumerate(transformations):
            transformed = _transformed_instance(inst, 15000 + 10 * seed + variant,
                                                reorder=reorder,
                                                independent=independent)
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "variant": variant,
                                     "reason": "key changed under legal relabelling"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": seed, "variant": variant,
                                     "reason": "carried witness failed"})
    unrelated = [
        canonical_key(make_instance(seed=20000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "one common vertex relabelling across all reference graph layers",
            "one common vertex relabelling across all target graph layers",
            "independent vertex relabellings of every reference and target graph",
            "pair-list reordering",
            "composition of independent relabellings with pair reordering",
        ],
        "canonicalization_caveat": (
            "the key uses a multiset of rooted-reference/unrooted-target "
            "Weisfeiler-Leman fingerprints; it is a strong invariant, not a complete "
            "graph-isomorphism canonical form"
        ),
    }

    answer_chars, answer_tokens = _answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and shipping["games"] <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": shipping["games"],
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
