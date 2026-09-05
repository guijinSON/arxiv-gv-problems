"""Verified problem generator for arXiv:1502.04803.

The paper studies Independent Set Reconfiguration under token addition and
removal (TAR): consecutive independent sets differ in one vertex and have size
between k-1 and k.  This Track-B family gives a sparse final graph through a
succinct stream of edge toggles.  A certificate is an explicit TAR sequence.

The answer is known by inverse generation.  The generator first samples a
forced order of token jumps, constructs the sparse dependency graph that makes
that order valid, and only then hides the graph in paired arithmetic-progressions
of edge toggles.  Equal updates cancel because toggling is an involution.  No
reconfiguration instance is solved during generation.

Only the standard library is required.  Importing this module performs no I/O.
"""

from __future__ import annotations

from collections import Counter, deque
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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family has a complete fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "simple sparse graph specified by exact edge-toggle batches",
        "source and target independent sets",
        "token-addition/removal reconfiguration sequence",
    ],
    "verification_operations": [
        "exact arithmetic-progression membership modulo n squared",
        "edge-toggle parity",
        "independent-set membership and symmetric-difference checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Edge toggling is an involution, so paired progression batches cancel "
        "and expose a small dependency graph; without that parity invariant a "
        "solver must perform exact modular membership tests for every relevant edge."
    ),
    "hardness_basis": (
        "Track B: Theorem 2 gives an FPT kernel-and-enumerate algorithm for ISR "
        "on d-degenerate graphs, so Track A would be false; at the medium shipping "
        "preset the O(B*k^2*log(n)+transitions) reference method (exact modular "
        "batch membership followed by breadth-first search) measured 98,418 "
        "counted operations and about 0.002 seconds, whereas paired-batch cancellation "
        "uses 244 exact operations and must be recognized without tools."
    ),
    "max_answer_tokens": 53,
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


DIFFICULTY = {
    "demo": {
        "n": 11,
        "k": 3,
        "extras": 1,
        "decoy_groups": 1,
        "replay_span": 7,
    },
    "easy": {
        "n": 1007,
        "k": 8,
        "extras": 5,
        "decoy_groups": 4,
        "replay_span": 400_000,
    },
    "medium": {
        "n": 2015,
        "k": 8,
        "extras": 5,
        "decoy_groups": 4,
        "replay_span": 1_600_000,
    },
    "hard": {
        "n": 4031,
        "k": 8,
        "extras": 5,
        "decoy_groups": 4,
        "replay_span": 6_400_000,
    },
}
SHIPPING_DIFFICULTY = "medium"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly 2k nonzero signed vertex labels.  Negative "
        "labels remove each source vertex exactly once, positive labels add "
        "each target vertex exactly once, and signs alternate starting negative."
    ),
    "bounds": {
        "operations": "exactly 2k (16 at the shipping preset)",
        "vertex_labels": "absolute value in 1..n",
        "removals": "a permutation of the k source vertices",
        "additions": "a permutation of the k target vertices",
        "sign_pattern": "negative, positive, negative, positive, ...",
    },
}


STRUCTURAL_HINT = (
    "Because an edge toggle is an involution, only update multiplicities modulo "
    "two determine the final graph."
)
PLACEBO_HINT = (
    "Careful attention to signed vertex labels and inclusive batch endpoints "
    "helps prevent indexing mistakes."
)


# Filled after the three script-owned hardening runs.  These arms are diagnostic;
# G9 is gated only by the answer and intended-route caps.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 1, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


NOTES = r"""
Sections 1 and 2 fix the native problem and its exact TAR convention: source
and target are independent sets of size k, every intermediate set is
independent, consecutive sets have symmetric difference one, and all sizes lie
in [k-1,k].  The same passage observes equivalence with token jumping.

Section 3.1 is the easy-regime warning.  Lemma 1 uses the Sunflower Lemma to
delete irrelevant low-degree vertices, and Theorem 2 proves that ISR on
d-degenerate graphs is FPT parameterized by k+d by reducing to a bounded kernel
and exhaustively enumerating its reconfiguration graph.  Our final graphs have
only O(k) edges (all other vertices are isolated) and degeneracy at most k, so
this family cannot honestly be Track A.  It is Track B, and reports the exact
algorithm that succeeds separately from the failing heuristic attacks.

The generator samples disjoint source and target sets and a hidden order.  It
adds edges t_i--s_i and, for i>0, t_i--s_(i-1), plus seed-dependent edges from
t_i to earlier source vertices.  If ranks below i have already moved, t_i has
exactly one remaining source neighbor, s_i.  Every later target retains its two
mandatory neighbors.  Induction therefore forces the planted shortest TAR
sequence, which is known before its graph is encoded.

Each final edge is encoded by two inclusive arithmetic-progression batches:
one batch and the same batch without its first update.  Their common toggles
cancel and leave the boundary edge.  Decoy boundaries are emitted twice and
cancel too.  Targets and decoys use the same step, span, orientation and offset
distributions.  The outlier attack ranks longest batches, the greedy attacks
sort labels or use visible unpaired endpoints, the prefix attack samples only
the beginning of each batch, and random restarts sample the full bounded answer
language.  The successful Track-B reference instead performs exact modular
membership for every endpoint edge and then breadth-first search; the compact
route pairs equal batch tails and propagates the forced dependency chain.

The edge-toggle batches are a succinct input encoding not studied in the paper;
they define an ordinary paper-native graph exactly and do not replace it by a
surrogate.  This representation choice and the fixed shortest-length request
are stated explicitly in the README caveats.
""".strip()


_ADJ_CACHE = {}
_ADJ_CACHE_LIMIT = 64


def _reverse_batch(batch):
    return {
        "start": batch["end"],
        "end": batch["start"],
        "step": -batch["step"],
    }


def _batch_count(batch):
    step = batch["step"]
    return abs(batch["end"] - batch["start"]) // abs(step) + 1


def _edge_code(n, u, v, orientation=0):
    if orientation:
        u, v = v, u
    return (u - 1) * n + (v - 1)


def _decode_code(n, code):
    q = code % (n * n)
    a, b = divmod(q, n)
    u, v = a + 1, b + 1
    if u == v:
        return None
    return (u, v) if u < v else (v, u)


def _fresh_step(modulus, rng):
    while True:
        step = rng.randrange(3, 98)
        if math.gcd(step, modulus) == 1:
            return step


def _primitive_batches(code, modulus, replay_span, rng, used_keys):
    """Encode one boundary toggle as two almost-identical batches."""
    while True:
        step = _fresh_step(modulus, rng)
        length = replay_span + rng.randrange(max(2, replay_span // 7 + 1))
        lift = 10_000 + rng.randrange(10_000_000)
        first = code + modulus * lift
        last = first + step * length
        key = (step, last)
        if key not in used_keys:
            used_keys.add(key)
            break
    outer = {"start": first, "end": last, "step": step}
    inner = {"start": first + step, "end": last, "step": step}
    if rng.randrange(2):
        outer = _reverse_batch(outer)
    if rng.randrange(2):
        inner = _reverse_batch(inner)
    return [outer, inner]


def _encode_edges(n, edges, replay_span, decoy_groups, rng):
    modulus = n * n
    batches = []
    used_keys = set()
    target_codes = set()
    for u, v in sorted(edges):
        code = _edge_code(n, u, v, rng.randrange(2))
        target_codes.add(code)
        batches.extend(_primitive_batches(
            code, modulus, replay_span, rng, used_keys
        ))

    # A decoy boundary is generated twice.  It therefore has exactly the same
    # marginal distribution as a real boundary but even total parity.
    for _ in range(decoy_groups):
        while True:
            u, v = rng.sample(range(1, n + 1), 2)
            code = _edge_code(n, u, v, rng.randrange(2))
            reverse_code = _edge_code(n, u, v, 1) if code == _edge_code(n, u, v, 0) \
                else _edge_code(n, u, v, 0)
            if code not in target_codes and reverse_code not in target_codes:
                break
        batches.extend(_primitive_batches(
            code, modulus, replay_span, rng, used_keys
        ))
        batches.extend(_primitive_batches(
            code, modulus, replay_span, rng, used_keys
        ))
    rng.shuffle(batches)
    return batches


def make_instance(n, seed=0, **params):
    """Construct a yes-instance and its TAR witness without solving it."""
    k = int(params.get("k", 8))
    extras = int(params.get("extras", 5))
    decoy_groups = int(params.get("decoy_groups", 1))
    replay_span = int(params.get("replay_span", 5_000))
    if n < 2 * k:
        raise ValueError("n must be at least 2k")
    if k < 2:
        raise ValueError("k must be at least 2")
    if extras < 0 or decoy_groups < 0 or replay_span < 1:
        raise ValueError("extras and decoy_groups must be nonnegative; span positive")

    rng = random.Random(seed)
    chosen = rng.sample(range(1, n + 1), 2 * k)
    source_order = chosen[:k]
    target_order = chosen[k:]

    edges = set()
    for i in range(k):
        edges.add(tuple(sorted((source_order[i], target_order[i]))))
        if i:
            edges.add(tuple(sorted((source_order[i - 1], target_order[i]))))

    optional = [(i, j) for i in range(2, k) for j in range(i - 1)]
    if extras > len(optional):
        raise ValueError("too many optional dependency edges for k")
    for i, j in rng.sample(optional, extras):
        edges.add(tuple(sorted((source_order[j], target_order[i]))))

    batches = _encode_edges(
        n, edges, replay_span, decoy_groups, rng
    )
    answer = []
    for s, t in zip(source_order, target_order):
        answer.extend((-s, t))

    return {
        "family": "independent_set_reconfiguration_tar",
        "n": n,
        "k": k,
        "source": sorted(source_order),
        "target": sorted(target_order),
        "edge_code_modulus": n * n,
        "initial_graph": "empty",
        "batches": batches,
        "required_operations": 2 * k,
        "extras": extras,
        "decoy_groups": decoy_groups,
        "replay_span": replay_span,
        "answer": answer,
    }


def render(inst):
    lines = [
        "Independent-set reconfiguration in a succinct sparse graph",
        "",
        "A simple undirected graph has vertices labelled 1 through "
        f"n={inst['n']}.  A set is independent when no graph edge has both "
        "endpoints in the set.",
        "",
        "The graph starts empty.  Apply every edge-toggle update in every batch "
        "below.  Toggling an absent edge inserts it; toggling a present edge "
        "deletes it.  Thus two toggles of the same edge cancel.",
        "",
        f"For an integer x, set q = x mod n^2 = x mod {inst['edge_code_modulus']}, "
        "using the residue in {0,...,n^2-1}.  Write q=a*n+b with "
        "0<=a,b<n.  If a=b, the update does nothing.  Otherwise it toggles "
        "the undirected edge {a+1,b+1}; the two orders name the same edge.",
        "",
        "A batch [first,last,step] is the inclusive integer progression first, "
        "first+step, ... , last.  Its nonzero step has the sign needed to reach "
        "last, and both endpoints are included.",
        "",
        f"Batches ({len(inst['batches'])} total, in arbitrary order):",
    ]
    lines.extend(
        f"  [{b['start']},{b['end']},{b['step']}]" for b in inst["batches"]
    )
    lines.extend([
        "",
        f"Source independent set I_s (size k={inst['k']}): "
        + ", ".join(map(str, inst["source"])),
        "Target independent set I_t (also size k): "
        + ", ".join(map(str, inst["target"])),
        "",
        f"Give a reconfiguration sequence of exactly {inst['required_operations']} "
        "single-vertex operations.  Start at I_s and finish at I_t.  After every "
        "operation the current set must be independent and have size k or k-1. "
        "Consequently operations alternate removal and addition, beginning with "
        "a removal.  Vertex labels are 1-indexed; repetitions are forbidden.",
        "",
        "Encode a removal of vertex v as the negative integer -v and an addition "
        "as the positive integer v.  Give your final answer inside "
        "<answer></answer> tags as one JSON list of signed integers.",
        "Example syntax: <answer>[-3,17,-8,2]</answer>",
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
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                       flags=re.IGNORECASE | re.DOTALL)
    payload = tagged.group(1).strip() if tagged else text.strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        if tagged:
            value = json.loads(payload)
        else:
            start = payload.find("[")
            if start < 0:
                return None
            value, _ = json.JSONDecoder().raw_decode(payload[start:])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
        return None
    return value


def _batch_signature(inst):
    return (
        inst["n"],
        tuple((b["start"], b["end"], b["step"])
              for b in inst["batches"]),
        tuple(inst["source"]),
        tuple(inst["target"]),
    )


def _batch_mod_infos(inst):
    modulus = inst["edge_code_modulus"]
    infos = []
    for batch in inst["batches"]:
        count = _batch_count(batch)
        step = batch["step"] % modulus
        if math.gcd(step, modulus) != 1:
            raise ValueError("batch step must be invertible modulo n squared")
        infos.append((batch["start"] % modulus, pow(step, -1, modulus), count))
    return infos


def _code_parity(code, modulus, infos):
    bit = 0
    for start, inverse, count in infos:
        r0 = ((code - start) * inverse) % modulus
        if r0 < count:
            occurrences = 1 + (count - 1 - r0) // modulus
            bit ^= occurrences & 1
    return bit


def _edge_present(n, u, v, infos):
    if u == v:
        return False
    modulus = n * n
    q1 = _edge_code(n, u, v, 0)
    q2 = _edge_code(n, u, v, 1)
    return bool(_code_parity(q1, modulus, infos)
                ^ _code_parity(q2, modulus, infos))


def _endpoint_adjacency(inst, use_cache=True):
    key = _batch_signature(inst)
    if use_cache and key in _ADJ_CACHE:
        return _ADJ_CACHE[key]
    endpoints = sorted(set(inst["source"]) | set(inst["target"]))
    infos = _batch_mod_infos(inst)
    adj = {v: set() for v in endpoints}
    for i, u in enumerate(endpoints):
        for v in endpoints[i + 1:]:
            if _edge_present(inst["n"], u, v, infos):
                adj[u].add(v)
                adj[v].add(u)
    if use_cache:
        if len(_ADJ_CACHE) >= _ADJ_CACHE_LIMIT:
            _ADJ_CACHE.pop(next(iter(_ADJ_CACHE)))
        _ADJ_CACHE[key] = adj
    return adj


def _is_independent(vertices, adj):
    chosen = set(vertices)
    return all(not (adj[v] & chosen) for v in chosen)


def verify(inst, answer):
    """Verify any exact-length TAR witness; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must be a nonempty list"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every operation must be an integer"
    if any(x == 0 or abs(x) > inst["n"] for x in answer):
        return False, "vertex id out of range"
    if len({abs(x) for x in answer}) != len(answer):
        return False, "a vertex may be touched only once"
    if len(answer) != inst["required_operations"]:
        return False, f"expected exactly {inst['required_operations']} operations"
    if any((i % 2 == 0 and x > 0) or (i % 2 == 1 and x < 0)
           for i, x in enumerate(answer)):
        return False, "operations must alternate removal then addition"

    removals = {-answer[i] for i in range(0, len(answer), 2)}
    additions = {answer[i] for i in range(1, len(answer), 2)}
    if removals != set(inst["source"]):
        return False, "removals must use exactly the source vertices"
    if additions != set(inst["target"]):
        return False, "additions must use exactly the target vertices"

    try:
        adj = _endpoint_adjacency(inst)
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        return False, f"malformed graph encoding: {exc}"
    current = set(inst["source"])
    if not _is_independent(current, adj):
        return False, "source set is not independent"
    k = inst["k"]
    for index, operation in enumerate(answer):
        vertex = abs(operation)
        if operation < 0:
            if vertex not in current:
                return False, f"operation {index} removes an absent vertex"
            current.remove(vertex)
        else:
            if vertex in current:
                return False, f"operation {index} adds a present vertex"
            if adj[vertex] & current:
                return False, f"operation {index} creates an edge"
            current.add(vertex)
        if not (k - 1 <= len(current) <= k):
            return False, f"operation {index} violates the size bounds"
    if current != set(inst["target"]):
        return False, "final set is not the target"
    return True, "ok"


def random_candidate(inst, rng):
    removals = list(inst["source"])
    additions = list(inst["target"])
    rng.shuffle(removals)
    rng.shuffle(additions)
    candidate = []
    for s, t in zip(removals, additions):
        candidate.extend((-s, t))
    return candidate


def search_space(inst):
    return math.factorial(inst["k"]) ** 2


def enumerate_all(inst):
    space = search_space(inst)
    if space > 2_000_000:
        return None
    valid = 0
    for removals in itertools.permutations(inst["source"]):
        for additions in itertools.permutations(inst["target"]):
            candidate = []
            for s, t in zip(removals, additions):
                candidate.extend((-s, t))
            valid += int(verify(inst, candidate)[0])
    return valid


def _normal_groups(inst):
    groups = {}
    for batch in inst["batches"]:
        if batch["step"] == 0:
            raise ValueError("zero batch step")
        left = min(batch["start"], batch["end"])
        right = max(batch["start"], batch["end"])
        step = abs(batch["step"])
        if (right - left) % step:
            raise ValueError("batch endpoint not reached by its step")
        groups.setdefault((step, right), []).append(left)
    return groups


def _compact_final_edges(inst, count_operations=False):
    """Recover final edges by the intended batch-cancellation invariant."""
    operations = 0
    groups = {}
    for batch in inst["batches"]:
        left = min(batch["start"], batch["end"])
        right = max(batch["start"], batch["end"])
        step = abs(batch["step"])
        groups.setdefault((step, right), []).append(left)
        operations += 2  # endpoint comparison and absolute-value normalization

    edge_parity = set()
    for (step, _right), lefts in groups.items():
        odd_lefts = sorted(left for left, multiplicity in Counter(lefts).items()
                          if multiplicity & 1)
        if not odd_lefts:
            continue
        if len(odd_lefts) != 2 or odd_lefts[1] - odd_lefts[0] != step:
            raise ValueError("batches do not form cancellable one-boundary pairs")
        edge = _decode_code(inst["n"], odd_lefts[0])
        operations += 3  # smaller boundary, residue/divmod, parity toggle
        if edge is not None:
            if edge in edge_parity:
                edge_parity.remove(edge)
            else:
                edge_parity.add(edge)
    if count_operations:
        return edge_parity, operations
    return edge_parity


def _compact_route(inst):
    started = time.perf_counter()
    edges, operations = _compact_final_edges(inst, count_operations=True)
    sources = set(inst["source"])
    targets = set(inst["target"])
    neighbors = {t: set() for t in targets}
    incident_targets = {s: set() for s in sources}
    for u, v in edges:
        if u in sources and v in targets:
            s, t = u, v
        elif v in sources and u in targets:
            s, t = v, u
        else:
            continue
        neighbors[t].add(s)
        incident_targets[s].add(t)
        operations += 1

    remaining_s = set(sources)
    remaining_t = set(targets)
    counts = {t: len(neighbors[t]) for t in targets}
    singles = {t for t in targets if counts[t] == 1}
    answer = []
    for _ in range(inst["k"]):
        active_singles = [t for t in singles if t in remaining_t]
        if len(active_singles) != 1:
            raise ValueError("dependency graph does not expose a unique next target")
        t = active_singles[0]
        possible_s = neighbors[t] & remaining_s
        if len(possible_s) != 1:
            raise ValueError("next target does not have one remaining blocker")
        s = next(iter(possible_s))
        answer.extend((-s, t))
        remaining_t.remove(t)
        remaining_s.remove(s)
        singles.discard(t)
        operations += 2
        for later_t in incident_targets[s]:
            if later_t in remaining_t:
                counts[later_t] -= 1
                operations += 1
                if counts[later_t] == 1:
                    singles.add(later_t)
    return answer, time.perf_counter() - started, operations


def _reference_bfs(inst):
    """Mechanical Track-B reference: modular edge queries, then ordinary BFS."""
    started = time.perf_counter()
    endpoints = sorted(set(inst["source"]) | set(inst["target"]))
    infos = _batch_mod_infos(inst)
    modulus_bits = inst["edge_code_modulus"].bit_length()
    operations = len(infos) * (3 * modulus_bits)
    adj = {v: set() for v in endpoints}
    for i, u in enumerate(endpoints):
        for v in endpoints[i + 1:]:
            operations += 14 * len(infos)
            if _edge_present(inst["n"], u, v, infos):
                adj[u].add(v)
                adj[v].add(u)

    source = frozenset(inst["source"])
    target = frozenset(inst["target"])
    queue = deque([source])
    parent = {source: (None, None)}
    depth = {source: 0}
    max_depth = inst["required_operations"]
    transitions = 0
    while queue:
        state = queue.popleft()
        if state == target:
            break
        if depth[state] >= max_depth:
            continue
        if len(state) == inst["k"]:
            choices = [(-v, frozenset(set(state) - {v})) for v in state]
        else:
            choices = []
            for v in endpoints:
                if v not in state:
                    transitions += 1
                    if not (adj[v] & set(state)):
                        choices.append((v, frozenset(set(state) | {v})))
        for operation, nxt in choices:
            transitions += 1
            if nxt not in parent:
                parent[nxt] = (state, operation)
                depth[nxt] = depth[state] + 1
                queue.append(nxt)
    operations += transitions
    if target not in parent:
        return None, time.perf_counter() - started, operations, len(parent), transitions
    reversed_ops = []
    cursor = target
    while parent[cursor][0] is not None:
        previous, operation = parent[cursor]
        reversed_ops.append(operation)
        cursor = previous
    answer = list(reversed(reversed_ops))
    return (answer, time.perf_counter() - started, operations,
            len(parent), transitions)


def _candidate_from_orders(sources, targets):
    candidate = []
    for s, t in zip(sources, targets):
        candidate.extend((-s, t))
    return candidate


def _score_visible_endpoints(inst, batches):
    source = set(inst["source"])
    target = set(inst["target"])
    s_score = Counter()
    t_score = Counter()
    for batch in batches:
        for x in (batch["start"], batch["end"]):
            edge = _decode_code(inst["n"], x)
            if edge is None:
                continue
            for v in edge:
                if v in source:
                    s_score[v] += 1
                if v in target:
                    t_score[v] += 1
    s_order = sorted(source, key=lambda v: (-s_score[v], v))
    t_order = sorted(target, key=lambda v: (-t_score[v], v))
    return _candidate_from_orders(s_order, t_order)


def _attack_candidates(inst, rng):
    batches = inst["batches"]
    longest = sorted(batches, key=lambda b: (-_batch_count(b), b["start"]))
    outlier = _score_visible_endpoints(inst, longest[:max(4, len(longest) // 4)])

    smallest = _candidate_from_orders(
        sorted(inst["source"]), sorted(inst["target"])
    )
    largest = _candidate_from_orders(
        sorted(inst["source"], reverse=True),
        sorted(inst["target"], reverse=True),
    )

    prefix_batches = []
    for batch in batches:
        # Treat the first visible endpoint as if the paired tail did not exist.
        prefix_batches.append({
            "start": batch["start"],
            "end": batch["start"],
            "step": 1,
        })
    unpaired = _score_visible_endpoints(inst, prefix_batches)

    return {
        "outlier_longest_batch_endpoints": [outlier],
        "greedy_smallest_labels": [smallest],
        "greedy_largest_labels": [largest],
        "unpaired_first_endpoint_ansatz": [unpaired],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _intrinsic_matrix(inst):
    edges = _compact_final_edges(inst)
    remaining_s = set(inst["source"])
    remaining_t = set(inst["target"])
    neighbors = {t: set() for t in remaining_t}
    for u, v in edges:
        if u in remaining_s and v in remaining_t:
            neighbors[v].add(u)
        elif v in remaining_s and u in remaining_t:
            neighbors[u].add(v)
    s_order = []
    t_order = []
    while remaining_t:
        candidates = []
        for t in remaining_t:
            blockers = neighbors[t] & remaining_s
            if len(blockers) == 1:
                candidates.append((next(iter(blockers)), t))
        if len(candidates) != 1:
            raise ValueError("instance lacks an intrinsic forced order")
        s, t = candidates[0]
        s_order.append(s)
        t_order.append(t)
        remaining_s.remove(s)
        remaining_t.remove(t)
    rows = []
    for t in t_order:
        rows.append("".join("1" if s in neighbors[t] else "0" for s in s_order))
    return rows


def canonical_key(inst):
    payload = {
        "family": "ISR-TAR-toggle-v1",
        "n": inst["n"],
        "k": inst["k"],
        "intrinsic_dependency_matrix": _intrinsic_matrix(inst),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _public_clone(inst):
    return json.loads(json.dumps(inst))


def _reencode(inst, edges, source, target, answer, rng):
    out = {
        "family": inst["family"],
        "n": inst["n"],
        "k": inst["k"],
        "source": sorted(source),
        "target": sorted(target),
        "edge_code_modulus": inst["n"] * inst["n"],
        "initial_graph": "empty",
        "batches": _encode_edges(
            inst["n"], edges, inst["replay_span"], inst["decoy_groups"], rng
        ),
        "required_operations": inst["required_operations"],
        "extras": inst["extras"],
        "decoy_groups": inst["decoy_groups"],
        "replay_span": inst["replay_span"],
        "answer": answer,
    }
    return out


def _relabelled(inst, rng):
    labels = list(range(1, inst["n"] + 1))
    shuffled = labels[:]
    rng.shuffle(shuffled)
    perm = dict(zip(labels, shuffled))
    edges = {tuple(sorted((perm[u], perm[v])))
             for u, v in _compact_final_edges(inst)}
    answer = [(1 if x > 0 else -1) * perm[abs(x)] for x in inst["answer"]]
    return _reencode(
        inst, edges,
        [perm[v] for v in inst["source"]],
        [perm[v] for v in inst["target"]],
        answer, rng,
    )


def _batches_shuffled(inst, rng):
    out = _public_clone(inst)
    rng.shuffle(out["batches"])
    return out


def _batches_reversed(inst):
    out = _public_clone(inst)
    out["batches"] = [_reverse_batch(b) for b in out["batches"]]
    return out


def _cancel_pair_added(inst, rng):
    out = _public_clone(inst)
    modulus = inst["edge_code_modulus"]
    step = _fresh_step(modulus, rng)
    first = modulus * (20_000_000 + rng.randrange(10_000_000)) + rng.randrange(modulus)
    count = 17 + rng.randrange(31)
    batch = {"start": first, "end": first + step * (count - 1), "step": step}
    out["batches"].extend((batch, dict(batch)))
    rng.shuffle(out["batches"])
    return out


def escalate(params):
    harder = dict(params)
    n = int(harder["n"])
    # Fixed-length answer; grow the ambient code space and mechanical replay.
    harder["n"] = 2 * n + 1
    harder["replay_span"] = int(harder.get("replay_span", 1)) * 4
    digits = len(str(harder["n"]))
    conservative_chars = 2 + 2 * int(harder.get("k", 8)) * (digits + 2)
    if conservative_chars > 2_000:
        return "cap_bound"
    return harder


def _answer_token_measure(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    punctuation = len(re.findall(r"[\[\],-]", blob))
    digit_chunks = sum((len(x) + 2) // 3 for x in re.findall(r"\d+", blob))
    return punctuation + digit_chunks


def selftest():
    report = {}

    g1_ok = 0
    g1_total = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            g1_ok += int(ok)
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": g1_ok == g1_total,
        "verified": g1_ok,
        "attempted": g1_total,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=19, **ship_params)
    answer = ship["answer"]
    corruptions = {}
    changed = answer[:-1]
    corruptions["drop_one"] = verify(ship, changed)
    changed = answer[:]
    changed[0], changed[1] = changed[1], changed[0]
    corruptions["swap_first_pair"] = verify(ship, changed)
    changed = answer[:]
    changed[2] = changed[0]
    corruptions["duplicate_vertex"] = verify(ship, changed)
    corruptions["empty"] = verify(ship, [])
    changed = answer[:]
    changed[0] = -(ship["n"] + 1)
    corruptions["out_of_range"] = verify(ship, changed)
    reasons = [reason for ok, reason in corruptions.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(corruptions),
        "cases": {name: {"accepted": ok, "reason": reason}
                  for name, (ok, reason) in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "I paired the batches and replayed the forced moves.\n\n"
        "```json\n<answer>" + json.dumps(answer) + "</answer>\n```"
    )
    parsed = parse_answer(model_style)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "parsed_matches": parsed == answer,
        "json_native": json_native,
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }

    density_rng = random.Random(0x150204803)
    samples = 200_000
    hits = 0
    density_started = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(ship, random_candidate(ship, density_rng))[0])
    density_wall = time.perf_counter() - density_started
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "structure_aware_space": search_space(ship),
        "sampling_wall_sec": round(density_wall, 6),
    }

    attempts = 8
    attack_successes = None
    reference_successes = 0
    reference_walls = []
    reference_ops = []
    reference_nodes = []
    reference_transitions = []
    compact_successes = 0
    compact_walls = []
    compact_ops = []
    for seed in range(30, 30 + attempts):
        inst = make_instance(seed=seed, **ship_params)
        probes = _attack_candidates(inst, random.Random(70_000 + seed))
        if attack_successes is None:
            attack_successes = {name: 0 for name in probes}
        for name, candidates in probes.items():
            if any(verify(inst, candidate)[0] for candidate in candidates):
                attack_successes[name] += 1

        found, elapsed, operations, nodes, transitions = _reference_bfs(inst)
        reference_successes += int(found is not None and verify(inst, found)[0])
        reference_walls.append(elapsed)
        reference_ops.append(operations)
        reference_nodes.append(nodes)
        reference_transitions.append(transitions)

        compact, elapsed, operations = _compact_route(inst)
        compact_successes += int(verify(inst, compact)[0])
        compact_walls.append(elapsed)
        compact_ops.append(operations)

    attacks = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_successes.items()
    }
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    mean_ref_wall = sum(reference_walls) / attempts
    mean_ref_ops = sum(reference_ops) // attempts
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == attempts
                and compact_successes == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "exact modular membership for every endpoint edge, followed by "
                "breadth-first search of the bounded TAR state graph"
            ),
            "complexity": "O(B*k^2*log(n) + explored reconfiguration transitions)",
            "wall_clock_sec": round(mean_ref_wall, 6),
            "operations": mean_ref_ops,
            "nodes": sum(reference_nodes) // attempts,
            "transitions": sum(reference_transitions) // attempts,
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
        "compact_route": {
            "name": "paired-progression parity cancellation and forced-chain propagation",
            "complexity": "O(B+k+|E|) exact operations",
            "wall_clock_sec": round(sum(compact_walls) / attempts, 6),
            "operations": max(compact_ops),
            "solves": f"{compact_successes}/{attempts}, as expected",
        },
        "paper_algorithm": {
            "name": "Section 3.1 irrelevant-vertex kernelization and exhaustive enumeration",
            "complexity": "FPT in k+d (Theorem 2)",
            "applies_here": "yes; the final graph is at most k-degenerate",
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    literal_updates = sum(_batch_count(b) for b in ship["batches"])
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and demo_count is not None
                and reference_successes == attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": probability,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(mean_ref_wall, 6),
        "baseline_operations": mean_ref_ops,
        "baseline_nodes": sum(reference_nodes) // attempts,
        "literal_toggle_updates_if_expanded": literal_updates,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * doubled_params["n"] + 1
    doubled_params["replay_span"] *= 2
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_updates = sum(_batch_count(b) for b in doubled["batches"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["answer"]) == len(answer)
                and doubled_updates > literal_updates,
        "original_n": ship["n"],
        "doubled_n": doubled["n"],
        "answer_operations_before": len(answer),
        "answer_operations_after": len(doubled["answer"]),
        "literal_updates_before": literal_updates,
        "literal_updates_after": doubled_updates,
        "verify_reason": doubled_reason,
    }

    invariant_passed = 0
    invariant_attempted = 0
    transformed_verified = 0
    unrelated_keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **ship_params)
        rng = random.Random(120_000 + seed)
        relabelled = _relabelled(inst, rng)
        shuffled = _batches_shuffled(inst, rng)
        reversed_batches = _batches_reversed(inst)
        cancellation = _cancel_pair_added(inst, rng)
        composed = _cancel_pair_added(
            _batches_reversed(_batches_shuffled(relabelled, rng)), rng
        )
        base_key = canonical_key(inst)
        for changed in (relabelled, shuffled, reversed_batches,
                        cancellation, composed):
            invariant_attempted += 1
            invariant_passed += int(canonical_key(changed) == base_key)
        transformed_verified += int(verify(composed, composed["answer"])[0])
        unrelated_keys.append(base_key)
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_passed == invariant_attempted
                and transformed_verified == 20 and distinct == 20,
        "invariance_checks_passed": invariant_passed,
        "invariance_checks_attempted": invariant_attempted,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": distinct,
        "unrelated_instances": 20,
        "transformations": [
            "arbitrary vertex relabelling with carried witness",
            "batch reordering",
            "batch direction reversal",
            "addition of a duplicated canceling batch",
            "composition of all transformations",
        ],
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    worst_chars = 0
    worst_tokens = 0
    intended_ops = 0
    for seed in range(20):
        candidate_inst = make_instance(seed=seed, **ship_params)
        blob = json.dumps(candidate_inst["answer"], separators=(",", ":"))
        worst_chars = max(worst_chars, len(blob))
        worst_tokens = max(worst_tokens,
                           _answer_token_measure(candidate_inst["answer"]))
        compact, _, operations = _compact_route(candidate_inst)
        if not verify(candidate_inst, compact)[0]:
            operations = 10 ** 9
        intended_ops = max(intended_ops, operations)
    arms = G9_RESULTS["arms"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (worst_chars <= 2_000 and len(answer) <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": worst_chars,
        "sample_answer_chars": len(answer_blob),
        "answer_tokens": worst_tokens,
        "sample_answer_tokens": _answer_token_measure(answer),
        "answer_elements": len(answer),
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
