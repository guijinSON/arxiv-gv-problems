"""Verified generator for motif-guided induced subgraph isomorphism.

The source is arXiv:2508.21287, especially Section III-A's exact induced
subgraph definition and Sections III-B--III-D's motif-table decomposition.
Instances here are connected graphs assembled from circulant motif blocks.
The certificate is an injective vertex map chosen before the data graph is
assembled; verification independently checks adjacency in both directions.
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
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "connected unlabeled undirected pattern graph",
        "connected unlabeled undirected data graph",
        "short-walk edge-motif tables",
        "injective induced-subgraph vertex map",
    ],
    "verification_operations": [
        "integer range and injectivity checks",
        "exact undirected edge membership",
        "exact induced adjacency equivalence",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Decompose the data graph at its bridges, compare the short-walk edge-motif "
        "profiles of the resulting circulant blocks, and recognize that the "
        "matching block's step labels differ by one modular multiplier; without "
        "that structure one must scan block-and-multiplier candidates."
    ),
    "hardness_basis": (
        "Track B: Sections III-B--III-D give an explicit join-and-filter "
        "enumeration and Section V uses VF2 as the standard baseline; for this "
        "restricted representation an exhaustive affine scan is O(B*k*r) "
        "candidate work (B blocks, prime block size k, r undirected steps) and at "
        "shipping averaged 15,504 exact operations and 0.00145 seconds over eight "
        "runs; the motif-profile route remains below 300 exact comparisons and "
        "arithmetic operations."
    ),
    "max_answer_tokens": 84,
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

# n is the number of same-size motif blocks in the connected data graph.  The
# answer remains 67 integers on every non-demo rung: escalation grows the
# haystack, not the witness.
DIFFICULTY = {
    "demo": {"n": 2, "pattern_size": 5, "step_count": 1, "crowding": 1},
    "easy": {"n": 24, "pattern_size": 67, "step_count": 6, "crowding": 1},
    "medium": {"n": 30, "pattern_size": 67, "step_count": 6, "crowding": 4},
    "hard": {"n": 36, "pattern_size": 67, "step_count": 6, "crowding": 16},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The bridge-separated blocks' short-walk edge profiles are invariant "
    "under the hidden modular multiplier."
)
PLACEBO_HINT = (
    "Carefully preserve the stated vertex order and check every index before "
    "submitting the mapping."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly k distinct data-vertex integers describing a "
        "block-respecting injection in pattern-vertex order; the bridge "
        "decomposition makes every induced copy block-respecting."
    ),
    "bounds": {
        "length": "k",
        "entry_min": 0,
        "entry_max": "B*(k+1)-1",
        "structure": "a uniformly chosen block followed by a uniform permutation",
        "candidate_count": "B*k!",
    },
}

NOTES = (
    "Section III-A fixes the definition as an injective map into a vertex-induced "
    "subgraph with adjacency preserved iff, and assumes connected unlabeled "
    "undirected graphs.  Sections III-B--III-D make motif embedding tables and "
    "join/filter the native certificate-producing algorithm; Section V identifies "
    "VF2 as the standard baseline.  Section VI-A fixes the relevant large-pattern "
    "regime (20--100 pattern vertices and 1,600--3,600-vertex structured data "
    "graphs) and reports that all embeddings are enumerated in seconds, ruling out "
    "an honest Track A claim.  The generator chooses a pattern block and affine "
    "map first, transforms its step set to make the planted data block, and only "
    "samples every block by the same rule, chooses the planted block uniformly, "
    "and obtains the pattern by an inverse affine relabelling of that known block. "
    "Equal block size, degree, triangle total, attachment, and sampling law defeat coarse "
    "outliers; nontrivial multipliers defeat identity/reversal and smallest-step "
    "greedy attacks; random permutations defeat blind restarts."
)

# Replaced with script-owned transcript counts only after successful oracle runs.
# Zero attempts means unavailable evidence, never three fabricated failures.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun: OpenRouter HTTP 403 key limit exceeded",
}


def _is_prime(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _edge(u, v):
    return (u, v) if u < v else (v, u)


def _symmetric_steps(k, representatives):
    return set(representatives) | {(-step) % k for step in representatives}


def _canonical_step(value, k):
    value %= k
    return min(value, (-value) % k)


def _multiply_steps(representatives, multiplier, k):
    return sorted({_canonical_step(multiplier * step, k) for step in representatives})


def _step_signatures(k, representatives):
    """Common-neighbor count for an edge of each displayed step type."""
    symmetric = _symmetric_steps(k, representatives)
    result = []
    for step in representatives:
        count = sum(1 for x in symmetric if (x - step) % k in symmetric)
        result.append(count)
    return result


def _profile(k, representatives):
    return tuple(sorted(_edge_fingerprints(k, representatives)))


def _edge_fingerprints(k, representatives):
    """Length-2, length-3, and length-4 walk counts across each edge type."""
    symmetric = _symmetric_steps(k, representatives)
    walks = [0] * k
    walks[0] = 1
    layers = []
    for _ in range(4):
        following = [0] * k
        for position, count in enumerate(walks):
            if count:
                for step in symmetric:
                    following[(position + step) % k] += count
        walks = following
        layers.append(walks)
    return [
        (layers[1][step], layers[2][step], layers[3][step])
        for step in representatives
    ]


def _circulant_edges(vertices, k, representatives):
    if len(vertices) != k:
        raise ValueError("circulant block has the wrong number of vertices")
    edges = set()
    for x in range(k):
        for step in representatives:
            edges.add(_edge(vertices[x], vertices[(x + step) % k]))
    return sorted(edges)


def _sample_steps(
    k,
    step_count,
    rng,
    triangle_sum=None,
    forbidden_profile=None,
):
    choices = range(1, (k + 1) // 2)
    for _ in range(100000):
        representatives = sorted(rng.sample(choices, step_count))
        signatures = _step_signatures(k, representatives)
        if triangle_sum is not None and sum(signatures) != triangle_sum:
            continue
        profile = tuple(sorted(signatures))
        if forbidden_profile is not None and profile == forbidden_profile:
            continue
        return representatives
    raise RuntimeError("could not sample a decoy step set under the stated invariants")


def _has_two_unique_signatures(signatures):
    multiplicities = Counter(signatures)
    return sum(count == 1 for count in multiplicities.values()) >= 2


def _is_affinely_equivalent(source, target, k):
    target_set = set(target)
    return any(set(_multiply_steps(source, a, k)) == target_set for a in range(1, k))


def _smallest_step_multiplier(source, target, k):
    return target[0] * pow(source[0], -1, k) % k


def _assemble_instance(k, blocks_steps, pattern_steps, answer_block, multiplier):
    block_count = len(blocks_steps)
    pattern_vertices = list(range(k))
    pattern_edges = _circulant_edges(pattern_vertices, k, pattern_steps)
    blocks = []
    data_edges = []
    connector_start = block_count * k
    connectors = [connector_start + j for j in range(block_count)]

    for index, representatives in enumerate(blocks_steps):
        vertices = [index * k + x for x in range(k)]
        edges = _circulant_edges(vertices, k, representatives)
        connector = connectors[index]
        blocks.append({
            "index": index,
            "vertices": vertices,
            "edges": edges,
            "connector": connector,
            "steps": list(representatives),
            "signatures": _step_signatures(k, representatives),
            "fingerprints": _edge_fingerprints(k, representatives),
        })
        data_edges.extend(edges)
        data_edges.append(_edge(connector, vertices[0]))

    for left, right in zip(connectors, connectors[1:]):
        data_edges.append(_edge(left, right))

    answer = [answer_block * k + (multiplier * x) % k for x in range(k)]
    return {
        "family": "motif-guided induced subgraph isomorphism",
        "n": block_count,
        "k": k,
        "step_count": len(pattern_steps),
        "pattern_vertices": pattern_vertices,
        "pattern_edges": sorted(set(pattern_edges)),
        "pattern_steps": list(pattern_steps),
        "pattern_signatures": _step_signatures(k, pattern_steps),
        "pattern_fingerprints": _edge_fingerprints(k, pattern_steps),
        "data_vertex_count": block_count * (k + 1),
        "data_edges": sorted(set(data_edges)),
        "blocks": blocks,
        "connectors": connectors,
        "answer": answer,
    }


def make_instance(n, seed=0, **params):
    """Sample identical-distribution blocks, then transform one known block.

    A block is selected uniformly after all blocks are assembled.  Its inverse
    affine relabelling constructs the pattern and carries a known vertex map; no
    search for an embedding is used.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer number of blocks, at least 2")
    k = params.pop("pattern_size", 67)
    step_count = params.pop("step_count", 6)
    crowding = params.pop("crowding", 1)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_prime(k) or k < 5:
        raise ValueError("pattern_size must be an odd prime at least 5")
    if not (1 <= step_count < (k - 1) // 2):
        raise ValueError("step_count must satisfy 1 <= step_count < (k-1)/2")
    if isinstance(crowding, bool) or not isinstance(crowding, int) or crowding < 1:
        raise ValueError("crowding must be a positive integer")

    rng = random.Random(seed)
    if k == 5 and step_count == 1:
        blocks_steps = [[rng.choice((1, 2))] for _ in range(n)]
        answer_block = rng.randrange(n)
        multiplier = rng.choice((2, 3))
        pattern_steps = _multiply_steps(
            blocks_steps[answer_block], pow(multiplier, -1, k), k
        )
        return _assemble_instance(
            k, blocks_steps, pattern_steps, answer_block, multiplier
        )

    def draw_block():
        while True:
            candidate = _sample_steps(k, step_count, rng)
            triangle_counts = _step_signatures(k, candidate)
            # A high-mass slice supplies many statistically comparable blocks.
            if k == 67 and step_count == 6 and sum(triangle_counts) != 12:
                continue
            if not _has_two_unique_signatures(_edge_fingerprints(k, candidate)):
                continue
            return candidate

    # Every block, including the one selected later as the plant, is drawn by
    # exactly the same best-of-m rule.  The common target only controls crowding.
    target_steps = draw_block()
    target_coarse = tuple(sorted(_step_signatures(k, target_steps)))
    blocks_steps = []
    for _ in range(n):
        pool = []
        while len(pool) < crowding:
            pool.append(draw_block())

        def similarity(candidate):
            coarse = tuple(sorted(_step_signatures(k, candidate)))
            prefix = 0
            for left, right in zip(target_coarse, coarse):
                if left != right:
                    break
                prefix += 1
            distance = sum(abs(left - right) for left, right in zip(target_coarse, coarse))
            return prefix, -distance

        blocks_steps.append(max(pool, key=similarity))

    # Choose the planted block uniformly only after every block exists.  A
    # modular relabelling of that known block constructs the pattern and carries
    # its certificate.  The presentation is selected to defeat the audited
    # identity/reversal and smallest-step ansatzes, never to discover a solution.
    answer_block = rng.randrange(n)
    multipliers = list(range(2, k - 1))
    rng.shuffle(multipliers)
    pattern_steps = None
    multiplier = None
    for trial in multipliers:
        candidate_pattern = _multiply_steps(
            blocks_steps[answer_block], pow(trial, -1, k), k
        )
        if any(block == candidate_pattern for block in blocks_steps):
            continue
        if any(
            set(_multiply_steps(
                candidate_pattern,
                _smallest_step_multiplier(candidate_pattern, block, k),
                k,
            )) == set(block)
            for block in blocks_steps
        ):
            continue
        pattern_steps = candidate_pattern
        multiplier = trial
        break
    if pattern_steps is None:
        raise RuntimeError("could not choose a presentation defeating cheap ansatzes")
    instance = _assemble_instance(
        k, blocks_steps, pattern_steps, answer_block, multiplier
    )
    instance["crowding"] = crowding
    return instance


def render(inst):
    k = inst["k"]
    block_count = inst["n"]
    pattern_table = ", ".join(
        f"{step}:{'/'.join(map(str, counts))}"
        for step, counts in zip(inst["pattern_steps"], inst["pattern_fingerprints"])
    )
    block_lines = []
    for block in inst["blocks"]:
        start = min(block["vertices"])
        end = max(block["vertices"])
        steps = ",".join(str(x) for x in block["steps"])
        table = ",".join(
            f"{step}:{'/'.join(map(str, counts))}"
            for step, counts in zip(block["steps"], block["fingerprints"])
        )
        block_lines.append(
            f"  block {block['index']}: global vertices {start}..{end}; "
            f"steps [{steps}]; c-table [{table}]"
        )

    statement = f"""Find an induced copy of one connected graph inside another.

All graphs here are finite, simple, undirected, and unlabeled: the displayed
integers are vertex identifiers, not vertex colors.  For integers modulo k,
an undirected circulant graph with step representatives S has vertices
0,...,k-1 and an edge {{x,y}} exactly when min((y-x) mod k,(x-y) mod k) is in S.

PATTERN GRAPH P
  k = {k}
  vertices: 0..{k - 1}
  step representatives: {inst['pattern_steps']}
Thus P has an edge {{x,y}} exactly by the circulant rule above.

DATA GRAPH D
D contains {block_count} circulant blocks, each with k local vertices.  In block
j, local vertex x has global identifier j*k+x.  Its internal edges use the
listed step representatives.  There is also one connector q_j with global
identifier {block_count * k}+j.  Connector q_j is adjacent to local vertex 0
of block j, and consecutive connectors q_j,q_(j+1) are adjacent.  These and
the internal block edges are ALL edges of D.  Hence D is connected and has
{inst['data_vertex_count']} vertices numbered 0..{inst['data_vertex_count'] - 1}.

Block data:
{chr(10).join(block_lines)}

The c-table is redundant exact motif data of the kind precomputed by the
paper's tabular method: entry s:c2/c3/c4 gives the exact numbers of walks of
length 2, 3, and 4 between the endpoints of every internal step-s edge.
For P its c-table is [{pattern_table}].  It does not add edges or labels.

Return one injective map f from P into D as a JSON list [f(0),...,f({k - 1})].
It is valid exactly when, for every pair of distinct pattern vertices x,y,
{{x,y}} is an edge of P if and only if {{f(x),f(y)}} is an edge of D.  This is
an induced-subgraph embedding: both edges and nonedges must be preserved.
All {k} entries must be distinct decimal integers in the inclusive range
0..{inst['data_vertex_count'] - 1}; order matters and repetition is forbidden.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the JSON syntax for a five-vertex toy instance: <answer>[4,0,1,2,3]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def verify(inst, answer):
    k = inst["k"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != k:
        return False, f"expected {k} mapped vertices, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every mapped vertex must be an integer"
    bad = next((x for x in answer if not 0 <= x < inst["data_vertex_count"]), None)
    if bad is not None:
        return False, f"mapped vertex {bad} is outside the data graph"
    if len(set(answer)) != k:
        return False, "mapping is not injective"

    pattern_edges = set(map(tuple, inst["pattern_edges"]))
    data_edges = set(map(tuple, inst["data_edges"]))
    for x in range(k):
        for y in range(x + 1, k):
            pattern_adjacent = (x, y) in pattern_edges
            data_adjacent = _edge(answer[x], answer[y]) in data_edges
            if pattern_adjacent != data_adjacent:
                kind = "edge" if pattern_adjacent else "nonedge"
                return False, f"induced-adjacency mismatch on pattern {kind} ({x},{y})"
    return True, "ok"


def random_candidate(inst, rng):
    block = rng.randrange(inst["n"])
    candidate = list(inst["blocks"][block]["vertices"])
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return inst["n"] * math.factorial(inst["k"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100000:
        return None
    count = 0
    for block in inst["blocks"]:
        for candidate in itertools.permutations(block["vertices"]):
            if verify(inst, list(candidate))[0]:
                count += 1
    return count


def _graph_invariant(vertices, edges):
    """A relabelling-invariant, deliberately cheaper than canonical labelling."""
    vertex_set = set(vertices)
    adjacency = {v: set() for v in vertices}
    internal = set()
    for u, v in edges:
        if u in vertex_set and v in vertex_set:
            u, v = _edge(u, v)
            internal.add((u, v))
            adjacency[u].add(v)
            adjacency[v].add(u)
    degree_hist = sorted(Counter(len(adjacency[v]) for v in vertices).items())
    pair_hist = Counter()
    vertex_profiles = []
    for i, u in enumerate(vertices):
        local = Counter()
        for v in vertices:
            if u == v:
                continue
            common = len(adjacency[u] & adjacency[v])
            flag = 1 if _edge(u, v) in internal else 0
            local[(flag, common)] += 1
        vertex_profiles.append((len(adjacency[u]), tuple(sorted(local.items()))))
        for v in vertices[i + 1:]:
            common = len(adjacency[u] & adjacency[v])
            flag = 1 if _edge(u, v) in internal else 0
            pair_hist[(flag, common)] += 1
    return (
        len(vertices),
        len(internal),
        tuple(degree_hist),
        tuple(sorted(pair_hist.items())),
        tuple(sorted(vertex_profiles)),
    )


def canonical_key(inst):
    pattern_fp = _graph_invariant(inst["pattern_vertices"], inst["pattern_edges"])
    by_connector = {}
    for block in inst["blocks"]:
        by_connector[block["connector"]] = _graph_invariant(
            block["vertices"], block["edges"]
        )
    sequence = tuple(by_connector[c] for c in inst["connectors"])
    sequence = min(sequence, tuple(reversed(sequence)))
    payload = (inst["k"], pattern_fp, sequence)
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def escalate(params):
    harder = dict(params)
    blocks = int(harder.get("n", 0))
    k = int(harder.get("pattern_size", 67))
    steps = int(harder.get("step_count", 6))
    crowding = int(harder.get("crowding", 1))
    # Profile comparisons plus map construction stay within G9(c) through 38.
    if k == 67 and steps == 6 and blocks < 38:
        harder["n"] = min(38, blocks + 2)
        harder["crowding"] = min(64, max(2, crowding * 2))
        return harder
    return None


def _reference_affine_scan(inst):
    """Straight exhaustive block/unit scan; returns mapping, operations."""
    k = inst["k"]
    source = inst["pattern_steps"]
    operations = 0
    candidates = 0
    for block_index, block in enumerate(inst["blocks"]):
        target = set(block["steps"])
        for multiplier in range(1, k):
            candidates += 1
            transformed = set()
            for step in source:
                transformed.add(_canonical_step(multiplier * step, k))
                operations += 2  # multiply/reduce and canonical sign comparison
            operations += len(source)  # exact set-membership/equality work
            if transformed == target:
                answer = [
                    block_index * k + (multiplier * x) % k for x in range(k)
                ]
                operations += k
                return answer, operations, candidates
    return None, operations, candidates


def _compact_profile_route(inst):
    """Motif-profile shortcut used only to audit the intended no-tool route."""
    target_profile = sorted(inst["pattern_fingerprints"])
    comparisons = 0
    for block_index, block in enumerate(inst["blocks"]):
        profile = sorted(block["fingerprints"])
        equal = True
        for left, right in zip(target_profile, profile):
            comparisons += 3
            if left != right:
                equal = False
                break
        if not equal:
            continue
        multiplicities = Counter(inst["pattern_fingerprints"])
        unique_value = next(v for v, count in multiplicities.items() if count == 1)
        source_step = inst["pattern_steps"][
            inst["pattern_fingerprints"].index(unique_value)
        ]
        target_step = block["steps"][block["fingerprints"].index(unique_value)]
        multiplier = target_step * pow(source_step, -1, inst["k"]) % inst["k"]
        comparisons += 2 * len(inst["pattern_steps"]) + 5
        if set(_multiply_steps(inst["pattern_steps"], multiplier, inst["k"])) != set(
            block["steps"]
        ):
            continue
        answer = [
            block_index * inst["k"] + (multiplier * x) % inst["k"]
            for x in range(inst["k"])
        ]
        return answer, comparisons + inst["k"]
    return None, comparisons


def _attack_outlier_coarse(inst):
    # Every block ties on these generator-visible scalar statistics; the attack
    # resolves the tie by input order and guesses the identity labelling.
    scores = []
    for index, block in enumerate(inst["blocks"]):
        scores.append((len(block["vertices"]), len(block["steps"]),
                       sum(block["signatures"]), index))
    chosen = min(scores)[-1]
    return verify(inst, [chosen * inst["k"] + x for x in range(inst["k"])])[0]


def _attack_identity_reversal(inst):
    k = inst["k"]
    for block_index in range(inst["n"]):
        for multiplier in (1, k - 1):
            answer = [block_index * k + multiplier * x % k for x in range(k)]
            if verify(inst, answer)[0]:
                return True
    return False


def _attack_smallest_step(inst):
    k = inst["k"]
    for block_index, block in enumerate(inst["blocks"]):
        multiplier = _smallest_step_multiplier(
            inst["pattern_steps"], block["steps"], k
        )
        answer = [block_index * k + multiplier * x % k for x in range(k)]
        if verify(inst, answer)[0]:
            return True
    return False


def _attack_random_permutations(inst, seed, restarts=256):
    rng = random.Random(seed)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _relabel_for_test(inst, rng, pattern, data, reorder):
    pmap = list(range(inst["k"]))
    dmap = list(range(inst["data_vertex_count"]))
    if pattern:
        rng.shuffle(pmap)
    if data:
        rng.shuffle(dmap)

    transformed = dict(inst)
    transformed["pattern_vertices"] = [pmap[v] for v in inst["pattern_vertices"]]
    transformed["pattern_edges"] = sorted(
        _edge(pmap[u], pmap[v]) for u, v in inst["pattern_edges"]
    )
    transformed["data_edges"] = sorted(
        _edge(dmap[u], dmap[v]) for u, v in inst["data_edges"]
    )
    transformed["connectors"] = [dmap[v] for v in inst["connectors"]]
    transformed_blocks = []
    for block in inst["blocks"]:
        copied = dict(block)
        copied["vertices"] = [dmap[v] for v in block["vertices"]]
        copied["edges"] = sorted(_edge(dmap[u], dmap[v]) for u, v in block["edges"])
        copied["connector"] = dmap[block["connector"]]
        transformed_blocks.append(copied)
    if reorder:
        rng.shuffle(transformed_blocks)
        transformed["pattern_edges"].reverse()
        transformed["data_edges"].reverse()
        if rng.randrange(2):
            transformed["connectors"].reverse()
    transformed["blocks"] = transformed_blocks

    carried = [0] * inst["k"]
    for old_pattern, old_data in enumerate(inst["answer"]):
        carried[pmap[old_pattern]] = dmap[old_data]
    transformed["answer"] = carried
    return transformed


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(v) for v in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(v) for v in answer)
    return 1


def selftest():
    report = {}

    # G1: all presets, several seeds, plus JSON-native answers.
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions = {
        "drop": planted[:-1],
        "swap": [planted[1], planted[0]] + planted[2:],
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["data_vertex_count"]],
    }
    g2_cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        g2_cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in g2_cases.values()) and len(set(reasons)) == 5,
        "cases": g2_cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the bridge decomposition and checked both nonedges and edges.\n"
        "```json\n<answer>\n" + json.dumps(planted) + "\n</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged list here") is None,
    }

    rng = random.Random(271828)
    guess_total = 200000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    guess_elapsed = time.perf_counter() - start
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_hits / guess_total,
        "candidate_space_bits": search_space(shipping).bit_length() - 1,
        "sampling_prior": "uniform block, then uniform permutation within that block",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_runs = []
    reference_successes = 0
    reference_elapsed = 0.0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        reference_start = time.perf_counter()
        answer, operations, candidates = _reference_affine_scan(inst)
        reference_elapsed += time.perf_counter() - reference_start
        ok = answer is not None and verify(inst, answer)[0]
        reference_successes += int(ok)
        reference_runs.append((operations, candidates))

    baseline_start = time.perf_counter()
    baseline_success = _attack_random_permutations(shipping, 123456, 256)
    baseline_elapsed = time.perf_counter() - baseline_start
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and guess_hits / guess_total < 1e-6
                and reference_successes == 8 and not baseline_success,
        "shipping_solution_density": guess_hits / guess_total,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_iterations": 256,
        "baseline_attack_wall_clock_sec": round(baseline_elapsed, 6),
        "reference_successes": reference_successes,
        "reference_attempts": 8,
        "reference_mean_operations": round(
            sum(x[0] for x in reference_runs) / len(reference_runs), 3
        ),
        "reference_max_operations": max(x[0] for x in reference_runs),
        "reference_mean_candidates": round(
            sum(x[1] for x in reference_runs) / len(reference_runs), 3
        ),
        "reference_mean_wall_clock_sec": round(reference_elapsed / 8, 6),
        "reference_total_wall_clock_sec": round(reference_elapsed, 6),
    }

    attack_names = (
        "outlier_degree_triangle_total",
        "greedy_smallest_step_alignment",
        "random_restart_256_block_permutations",
        "by_hand_identity_or_reversal_ansatz",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_times = {name: 0.0 for name in attack_names}
    compact_successes = 0
    compact_operations = []
    for seed in range(900, 908):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks = (
            (attack_names[0], lambda: _attack_outlier_coarse(inst)),
            (attack_names[1], lambda: _attack_smallest_step(inst)),
            (attack_names[2], lambda: _attack_random_permutations(inst, seed, 256)),
            (attack_names[3], lambda: _attack_identity_reversal(inst)),
        )
        for name, attack in attacks:
            t0 = time.perf_counter()
            attack_successes[name] += int(attack())
            attack_times[name] += time.perf_counter() - t0
        compact_answer, operations = _compact_profile_route(inst)
        compact_successes += int(
            compact_answer is not None and verify(inst, compact_answer)[0]
        )
        compact_operations.append(operations)
    attack_report = {
        name: {
            "successes": attack_successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_times[name], 6),
        }
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attack_report.values()),
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "exhaustive affine block-and-multiplier scan",
            "complexity": "O(B*k*r) exact integer operations for prime k",
            "wall_clock_sec": round(reference_elapsed / 8, 6),
            "operations": round(sum(x[0] for x in reference_runs) / 8, 3),
            "candidate_multipliers": round(sum(x[1] for x in reference_runs) / 8, 3),
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "bridge decomposition plus edge-motif profile multiplier",
            "operations_max": max(compact_operations),
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    t0 = time.perf_counter()
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_build = time.perf_counter() - t0
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    # A first-solution scan depends on the random plant position.  The complete
    # mechanical budget is the deterministic scaling quantity: B blocks times
    # k-1 units times 3r primitive transform/comparison operations.
    shipping_ops = (
        shipping["n"] * (shipping["k"] - 1) * 3 * shipping["step_count"]
    )
    doubled_ops = (
        doubled["n"] * (doubled["k"] - 1) * 3 * doubled["step_count"]
    )
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["data_vertex_count"] > shipping["data_vertex_count"]
                and doubled_ops > shipping_ops,
        "shipping_blocks": shipping["n"],
        "doubled_blocks": doubled["n"],
        "shipping_data_vertices": shipping["data_vertex_count"],
        "doubled_data_vertices": doubled["data_vertex_count"],
        "shipping_reference_operations": shipping_ops,
        "doubled_reference_operations": doubled_ops,
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariance = 0
    real = 0
    unrelated_keys = []
    transformation_names = [
        "pattern relabelling",
        "data relabelling",
        "input reordering and connector reversal",
        "all nonempty compositions of those three",
    ]
    for seed in range(20):
        inst = make_instance(seed=10000 + seed, n=6, pattern_size=67, step_count=6)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        for mask in range(1, 8):
            transformed = _relabel_for_test(
                inst,
                random.Random(50000 + 8 * seed + mask),
                pattern=bool(mask & 1),
                data=bool(mask & 2),
                reorder=bool(mask & 4),
            )
            invariance += int(canonical_key(transformed) == key)
            real += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariance == 140 and real == 140 and len(set(unrelated_keys)) == 20,
        "invariant_relabellings": invariance,
        "real_transformations_verified": real,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated_keys)),
        "transformations": transformation_names,
        "key_caveat": (
            "exact for the generated block/path representation under tested "
            "relabelings; its graph fingerprint is not a complete invariant for "
            "arbitrary graphs"
        ),
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    _, intended_operations = _compact_profile_route(shipping)
    arms = {
        key: dict(G9_ORACLE_RESULTS[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": len(answer_blob) <= 2000 and _answer_atoms(shipping["answer"]) <= 256
                and intended_operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(shipping["answer"]),
        "intended_route_operations": intended_operations,
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
