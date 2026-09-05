"""Verified generalized list T-coloring problem generator.

The native instance is exactly the triple (G, Lambda, t) from arXiv:1311.0603:
each vertex has a finite list of natural-number labels and each edge has a set
of forbidden absolute differences containing zero.  A proper labeling is
planted before the edges are sampled, so generation never solves its output.

Every local list is an arithmetic progression with a common prime step.  Edge
differences make equal positions in two local lists conflict, giving a
mechanically solvable coloring CSP.  The compact route is less mechanical: the
least permitted labels have quadratic residues that fall into independent
equal-width buckets.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This family needs only standard-library integer arithmetic.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite graph",
        "per-vertex lists of natural-number labels",
        "per-edge sets of forbidden absolute differences",
        "proper generalized list T-coloring",
    ],
    "verification_operations": [
        "exact list-membership checks",
        "exact integer absolute differences",
        "finite forbidden-set membership checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Quadratic residues of the least permitted labels fall into equal-width "
        "buckets that are independent sets; without recognizing that invariant, "
        "one must solve the displayed finite-domain coloring CSP."
    ),
    "hardness_basis": (
        "Track B: Section 3, Theorem 1 gives Solve-GLTC in "
        "O*((tau+2)^n) time (with the clique-packing refinement later in "
        "Section 3.1), while the executable DSATUR reference on the shipping "
        "specialization has O(q^n(n+m)) worst-case cost and took a median "
        "118 search nodes, 6,669 counted operations, and about 0.005 seconds over "
        "eight shipping seeds; the residue-bucket route uses 160 exact arithmetic "
        "operations, while the bare oracle pool failed on 3/3 instances."
    ),
    "max_answer_tokens": 38,
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
    "demo": {
        "n": 6,
        "colors": 3,
        "prime_floor": 17,
        "edge_rate_num": 2,
        "edge_rate_den": 3,
    },
    "easy": {
        "n": 24,
        "colors": 4,
        "prime_floor": 43,
        "edge_rate_num": 2,
        "edge_rate_den": 5,
    },
    "medium": {
        "n": 40,
        "colors": 5,
        "prime_floor": 67,
        "edge_rate_num": 1,
        "edge_rate_den": 3,
    },
    "hard": {
        "n": 74,
        "colors": 6,
        "prime_floor": 127,
        "edge_rate_num": 7,
        "edge_rate_den": 25,
    },
}

SHIPPING_DIFFICULTY = "medium"
DIFFICULTY = {"medium": dict(DIFFICULTY["medium"])}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON-native list of exactly n natural-number labels, where entry i "
        "is one of the exactly q labels in vertex i's displayed permitted list."
    ),
    "bounds": {
        "length": "n",
        "choices_per_coordinate": "colors=q",
        "structural_rule": "coordinate i belongs to Lambda(i)",
        "maximum_shipping_coordinates": 74,
    },
}

STRUCTURAL_HINT = (
    "The hidden color classes are the equal-width buckets of squared least-permitted labels modulo the displayed prime."
)
PLACEBO_HINT = (
    "The permitted-label lists and edge differences reward careful attention to the displayed indices."
)

# Populated after the three script-owned oracle runs.  Errors do not consume an
# attempt, so zero attempts can also mean that every call was an API error.
# The arms are diagnostic and do not gate G9(c).
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_http_403",
}

NOTES = """\
Section 2 fixes the exact native object: an instance is (G,Lambda,t), zero must
belong to every t(e), and a witness chooses a permitted natural-number label at
each vertex while avoiding every edge's forbidden absolute differences.
Section 3, Theorem 1 is decisive at Step 0: Solve-GLTC runs in
O*((tau+2)^n), so the family is Track B rather than an average-case Track A
claim.  The Introduction also says the all-t(e)={0} list-coloring case has an
O*(2^n) algorithm.  Section 3.1 improves the bound for bounded maximum degree,
regular and claw-free graphs, K_1,d-free and unit-disk graphs, and graphs with a
large clique packing.  The generator does not claim to evade those algorithms;
it reports an exact DSATUR implementation separately as the successful Track-B
reference.

Generation first samples balanced quadratic-residue bucket classes from the
least entries of the native permitted-label lists.  Every list is
{x,x+p,...,x+(q-1)p}; its planted label occupies the residue bucket's position,
and only then are edges sampled between different buckets.  For an edge uv,
t(uv)={0, |x_u-x_v|}; because 0<|x_u-x_v|<p, this forbids exactly equal local
positions and therefore proves the planted witness without search.  A random
valid spanning path makes G connected.  Raw-magnitude buckets, degree residue,
left-to-right greedy, 32 random greedy restarts, every affine ansatz, and a
bottom-adjacency-eigenspace/k-means spectral probe are tested as attacks.  The
exact DSATUR solver is kept out of attacks, as required for Track B, and its
node/operation/wall-clock costs are measured.
"""


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 500_000


def _is_prime(value):
    if value < 2:
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


def _next_prime(value):
    candidate = max(3, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _bucket(key, prime, colors):
    """Equal-width bucket of the least nonnegative quadratic residue."""
    return ((key * key) % prime) * colors // prime


def _balanced_sizes(n, colors):
    return [n // colors + int(color < n % colors) for color in range(colors)]


def _choose_prime(n, colors, prime_floor):
    """Choose a prime with enough distinct list minima in every bucket."""
    wanted = _balanced_sizes(n, colors)
    candidate = _next_prime(max(prime_floor, n + 2))
    while True:
        counts = [0] * colors
        for key in range(1, candidate):
            counts[_bucket(key, candidate, colors)] += 1
        if all(have >= need for have, need in zip(counts, wanted)):
            return candidate
        candidate = _next_prime(candidate + 2)


def _validate_params(n, colors, prime_floor, edge_rate_num, edge_rate_den):
    values = (
        ("n", n, 3),
        ("colors", colors, 2),
        ("prime_floor", prime_floor, 3),
        ("edge_rate_num", edge_rate_num, 1),
        ("edge_rate_den", edge_rate_den, 2),
    )
    for name, value, minimum in values:
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    if 2 * colors > n:
        raise ValueError("n must be at least twice colors")
    if edge_rate_num >= edge_rate_den:
        raise ValueError("edge_rate_num must be smaller than edge_rate_den")


def make_instance(n, seed=0, colors=6, prime_floor=101,
                  edge_rate_num=7, edge_rate_den=25, **params):
    """Inverse-generate a native generalized list T-coloring instance."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n, colors, prime_floor, edge_rate_num, edge_rate_den)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    prime = _choose_prime(n, colors, prime_floor)
    sizes = _balanced_sizes(n, colors)
    pools = [[] for _ in range(colors)]
    for key in range(1, prime):
        pools[_bucket(key, prime, colors)].append(key)

    # Including 1 and p-1 makes the global label endpoints canonical.  They are
    # in the same bucket because their squares are congruent modulo p.
    required = [[] for _ in range(colors)]
    required[0] = [1, prime - 1]
    keyed_classes = []
    for color, size in enumerate(sizes):
        available = [key for key in pools[color] if key not in required[color]]
        chosen = required[color] + rng.sample(
            available, size - len(required[color])
        )
        keyed_classes.extend((key, color) for key in chosen)
    rng.shuffle(keyed_classes)

    # These are precisely the paper's native permitted-label lists.  Distinct
    # least entries modulo p make the lists disjoint.  On an edge, forbidding
    # |x_u-x_v| therefore forbids equal list positions and no unequal position.
    label_step = prime
    vertices = []
    answer = []
    planted_colors = []
    for key, color in keyed_classes:
        labels = [key + offset * label_step for offset in range(colors)]
        vertices.append({"labels": labels})
        answer.append(labels[color])
        planted_colors.append(color)

    edge_pairs = set()
    for u in range(n):
        for v in range(u + 1, n):
            if (planted_colors[u] != planted_colors[v]
                    and rng.randrange(edge_rate_den) < edge_rate_num):
                edge_pairs.add((u, v))

    # The paper processes connected components independently.  Add a hidden
    # proper spanning path so this family stays in its connected formulation.
    by_color = [[] for _ in range(colors)]
    for vertex, color in enumerate(planted_colors):
        by_color[color].append(vertex)
    for group in by_color:
        rng.shuffle(group)
    path = []
    for row in range(max(map(len, by_color))):
        for color in range(colors):
            if row < len(by_color[color]):
                path.append(by_color[color][row])
    for u, v in zip(path, path[1:]):
        if u > v:
            u, v = v, u
        edge_pairs.add((u, v))

    edges = []
    for u, v in sorted(edge_pairs):
        difference = abs(vertices[u]["labels"][0] - vertices[v]["labels"][0])
        edges.append({"u": u, "v": v, "forbidden": [0, difference]})

    return {
        "family": "quadratic_bucket_generalized_list_T_coloring",
        "n": n,
        "colors": colors,
        "key_prime": prime,
        "label_step": label_step,
        "label_min": 1,
        "label_max": colors * prime - 1,
        "vertices": vertices,
        "edges": edges,
        "tau": max(max(edge["forbidden"]) for edge in edges),
        "answer": answer,
    }


def render(inst):
    """Render the complete problem statement and exact output contract."""
    n = inst["n"]
    vertex_lines = [
        f"{i}: {','.join(map(str, vertex['labels']))}"
        for i, vertex in enumerate(inst["vertices"])
    ]
    edge_lines = [
        f"{edge['u']} {edge['v']}: {','.join(map(str, edge['forbidden']))}"
        for edge in inst["edges"]
    ]
    statement = (
        "Find a proper generalized list T-coloring of the finite graph below.\n\n"
        "Definitions and conventions:\n"
        f"- The vertices are the integers 0 through {n - 1}, inclusive; all indexing is 0-based.\n"
        "- Every vertex line gives its complete increasing list of permitted natural-number labels.\n"
        "- Every undirected edge line has the form 'u v: d1,d2,...' and gives its complete set of forbidden differences. "
        "There are no loops or parallel edges, and unlisted vertex pairs are nonedges.\n"
        "- Choose exactly one integer label phi[i] from vertex i's permitted list. Repeats are allowed only when all constraints permit them.\n"
        "- For every listed edge u v, the ordinary integer absolute difference |phi[u]-phi[v]| must not equal any displayed forbidden difference for that edge. "
        "There is no modular arithmetic in this validity check.\n"
        f"- Every permitted list has q={inst['colors']} entries and common successive gap p={inst['key_prime']}; these are exact summaries of the displayed lists, not extra constraints.\n"
        f"- Return exactly {n} labels in vertex order 0,1,...,{n - 1}.\n\n"
        "VERTICES\n" + "\n".join(vertex_lines) + "\n\n"
        "EDGES AND THEIR FORBIDDEN DIFFERENCES\n" + "\n".join(edge_lines) + "\n\n"
        "Give your final answer inside <answer></answer> tags, as exactly "
        f"{n} comma-separated base-10 integers in vertex order.\n"
        "Example syntax only: <answer>3, 17, 42</answer>\n"
        "Output nothing else inside the tags."
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse one tagged comma-separated integer list, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    matches = _TAG_RE.findall(text)
    if len(matches) != 1:
        return None
    body = matches[0].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if (not isinstance(value, list)
                or any(isinstance(x, bool) or not isinstance(x, int) for x in value)):
            return None
        return value
    if not body:
        return None
    pieces = [piece.strip() for piece in body.split(",")]
    if any(not re.fullmatch(r"[+-]?\d+", piece) for piece in pieces):
        return None
    try:
        return [int(piece) for piece in pieces]
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Check any proper labeling exactly; never consult inst['answer']."""
    n = inst.get("n")
    if not isinstance(answer, list):
        return False, "answer must be a list of labels"
    if not answer:
        return False, f"answer is empty; expected {n} labels"
    if len(answer) != n:
        return False, f"wrong label count: expected {n}, received {len(answer)}"
    for vertex, label in enumerate(answer):
        if isinstance(label, bool) or not isinstance(label, int):
            return False, f"label at vertex {vertex} must be an integer"
    if len(set(answer)) != n:
        return False, "duplicate labels are impossible because the permitted lists are disjoint"
    largest = inst.get("label_max")
    if largest is None:
        largest = max(max(vertex["labels"]) for vertex in inst["vertices"])
    if any(label < 0 or label > largest for label in answer):
        return False, f"a label lies outside the displayed natural-number range 0..{largest}"
    for vertex, label in enumerate(answer):
        if label not in inst["vertices"][vertex]["labels"]:
            return False, f"label {label} is not permitted at vertex {vertex}"
    for edge_index, edge in enumerate(inst["edges"]):
        u, v = edge["u"], edge["v"]
        difference = abs(answer[u] - answer[v])
        if difference in edge["forbidden"]:
            return False, (
                f"edge {edge_index} ({u},{v}) has forbidden difference {difference}"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact product of the displayed permitted lists."""
    return [rng.choice(vertex["labels"]) for vertex in inst["vertices"]]


def search_space(inst):
    """The statement-aware Cartesian product of all local permitted lists."""
    space = 1
    for vertex in inst["vertices"]:
        space *= len(vertex["labels"])
    return space


def enumerate_all(inst):
    """Count all witnesses exactly when the declared space is safely small."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    lists = [vertex["labels"] for vertex in inst["vertices"]]
    for candidate in itertools.product(*lists):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _canonical_payload(inst, reflected):
    all_labels = [label for vertex in inst["vertices"] for label in vertex["labels"]]
    low, high = min(all_labels), max(all_labels)

    def normal(label):
        return high - label if reflected else label - low

    records_by_vertex = [
        tuple(sorted(normal(x) for x in vertex["labels"]))
        for vertex in inst["vertices"]
    ]
    records = sorted(records_by_vertex)
    edges = sorted(
        (min(records_by_vertex[edge["u"]], records_by_vertex[edge["v"]]),
         max(records_by_vertex[edge["u"]], records_by_vertex[edge["v"]]),
         tuple(sorted(edge["forbidden"])))
        for edge in inst["edges"]
    )
    return {
        "colors": inst["colors"],
        "prime": inst["key_prime"],
        "vertices": records,
        "edges": edges,
    }


def canonical_key(inst):
    """Invariant under storage order and the family's global reflections."""
    encodings = []
    for reflected in (False, True):
        payload = _canonical_payload(inst, reflected)
        encodings.append(json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ))
    return hashlib.sha256(min(encodings).encode("utf-8")).hexdigest()


def escalate(params):
    """Grow residue arithmetic at fixed witness length, then crowd the graph."""
    out = {key: value for key, value in params.items() if key != "_preset"}
    prime_floor = int(out.get("prime_floor", 101))
    if prime_floor < 1_000_003:
        out["prime_floor"] = _next_prime(prime_floor * 2 + 1)
        # Stay in the measured phase-transition window without changing n.
        numerator = int(out.get("edge_rate_num", 7))
        denominator = int(out.get("edge_rate_den", 25))
        if numerator * 100 < denominator * 30:
            out["edge_rate_num"] = numerator * 100 + denominator
            out["edge_rate_den"] = denominator * 100
            divisor = math.gcd(out["edge_rate_num"], out["edge_rate_den"])
            out["edge_rate_num"] //= divisor
            out["edge_rate_den"] //= divisor
        return out
    return None


# ---------------------------------------------------------------------------
# Attack and reference-solver helpers used only by selftest.


def _adjacency(inst):
    adjacency = [set() for _ in range(inst["n"])]
    for edge in inst["edges"]:
        adjacency[edge["u"]].add(edge["v"])
        adjacency[edge["v"]].add(edge["u"])
    return adjacency


def _candidate_from_colors(inst, colors):
    if colors is None:
        return None
    return [sorted(vertex["labels"])[color]
            for vertex, color in zip(inst["vertices"], colors)]


def _native_keys(inst):
    """Recover list minima, normalized after any global label translation."""
    origin = min(min(vertex["labels"]) for vertex in inst["vertices"])
    return [min(vertex["labels"]) - origin + 1 for vertex in inst["vertices"]]


def _colors_verify(adjacency, colors):
    if colors is None:
        return False
    return all(colors[u] != colors[v]
               for u, neighbors in enumerate(adjacency)
               for v in neighbors if u < v)


def _greedy_colors(inst, order):
    adjacency = _adjacency(inst)
    q = inst["colors"]
    colors = [-1] * inst["n"]
    for vertex in order:
        used = {colors[neighbor] for neighbor in adjacency[vertex]
                if colors[neighbor] >= 0}
        for color in range(q):
            if color not in used:
                colors[vertex] = color
                break
        if colors[vertex] < 0:
            return None
    return colors


def _attack_degree_residue(inst):
    adjacency = _adjacency(inst)
    colors = [len(adjacency[vertex]) % inst["colors"]
              for vertex in range(inst["n"])]
    return _candidate_from_colors(inst, colors)


def _attack_raw_magnitude_buckets(inst):
    q, prime = inst["colors"], inst["key_prime"]
    colors = [key * q // prime for key in _native_keys(inst)]
    return _candidate_from_colors(inst, colors)


def _attack_greedy(inst):
    return _candidate_from_colors(inst, _greedy_colors(inst, range(inst["n"])))


def _attack_random_restart(inst, seed, restarts=32):
    rng = random.Random(seed)
    vertices = list(range(inst["n"]))
    for _ in range(restarts):
        rng.shuffle(vertices)
        colors = _greedy_colors(inst, vertices)
        if colors is not None:
            candidate = _candidate_from_colors(inst, colors)
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _attack_affine_key(inst):
    q = inst["colors"]
    adjacency = _adjacency(inst)
    keys = _native_keys(inst)
    for slope in range(q):
        for intercept in range(q):
            colors = [(slope * key + intercept) % q for key in keys]
            if _colors_verify(adjacency, colors):
                return _candidate_from_colors(inst, colors)
    return None


def _orthonormalize(columns):
    """Modified Gram-Schmidt for the small floating-point attack subspace."""
    basis = []
    for column in columns:
        vector = list(column)
        for unit in basis:
            projection = sum(x * y for x, y in zip(vector, unit))
            for index in range(len(vector)):
                vector[index] -= projection * unit[index]
        norm = math.sqrt(sum(value * value for value in vector))
        if norm < 1e-12:
            return None
        basis.append([value / norm for value in vector])
    return basis


def _kmeans_rows(rows, clusters, rng, attempts=12):
    """Deterministic-replay multi-start k-means for the spectral probe."""
    n = len(rows)
    dimension = len(rows[0])
    best = None
    for _ in range(attempts):
        centers = [list(rows[rng.randrange(n)])]
        while len(centers) < clusters:
            distances = [
                min(
                    sum((row[k] - center[k]) ** 2 for k in range(dimension))
                    for center in centers
                )
                for row in rows
            ]
            pick = max(range(n), key=lambda i: (distances[i], -i))
            centers.append(list(rows[pick]))

        labels = None
        for _ in range(50):
            new_labels = [
                min(
                    range(clusters),
                    key=lambda j: sum(
                        (row[k] - centers[j][k]) ** 2
                        for k in range(dimension)
                    ),
                )
                for row in rows
            ]
            if new_labels == labels:
                break
            labels = new_labels
            for cluster in range(clusters):
                members = [i for i, value in enumerate(labels) if value == cluster]
                if members:
                    centers[cluster] = [
                        sum(rows[i][k] for i in members) / len(members)
                        for k in range(dimension)
                    ]

        score = sum(
            sum(
                (rows[i][k] - centers[labels[i]][k]) ** 2
                for k in range(dimension)
            )
            for i in range(n)
        )
        if best is None or score < best[0]:
            best = (score, labels)
    return best[1]


def _attack_spectral(inst, seed):
    """Bottom adjacency eigenspace approximation followed by q-means."""
    adjacency = _adjacency(inst)
    n, q = inst["n"], inst["colors"]
    rng = random.Random(seed)
    columns = [
        [rng.uniform(-1.0, 1.0) for _ in range(n)]
        for _ in range(q - 1)
    ]
    columns = _orthonormalize(columns)
    shift = max(map(len, adjacency)) + 1

    # Power iteration on shift*I-A targets the bottom adjacency eigenspace,
    # which is the natural spectral signal for a planted multipartite graph.
    for _ in range(80):
        multiplied = [
            [
                shift * column[i] - sum(column[j] for j in adjacency[i])
                for i in range(n)
            ]
            for column in columns
        ]
        columns = _orthonormalize(multiplied)
        if columns is None:
            return None

    rows = [[columns[j][i] for j in range(q - 1)] for i in range(n)]
    colors = _kmeans_rows(rows, q, rng)
    return _candidate_from_colors(inst, colors)


def _dsatur_reference(inst, node_cap=2_000_000):
    """Exact q-coloring backtracking; return answer and reproducible counters."""
    adjacency = _adjacency(inst)
    n, q = inst["n"], inst["colors"]
    degrees = [len(neighbors) for neighbors in adjacency]
    colors = [-1] * n
    saturation = [set() for _ in range(n)]
    counters = {"nodes": 0, "operations": 0, "capped": False}

    def search(done):
        counters["nodes"] += 1
        if counters["nodes"] > node_cap:
            counters["capped"] = True
            return None
        if done == n:
            return colors[:]

        vertex = None
        best = None
        for candidate in range(n):
            counters["operations"] += 1
            if colors[candidate] < 0:
                key = (len(saturation[candidate]), degrees[candidate], -candidate)
                if best is None or key > best:
                    best = key
                    vertex = candidate

        for color in range(q):
            counters["operations"] += 1
            if color in saturation[vertex]:
                continue
            colors[vertex] = color
            changed = []
            valid = True
            for neighbor in adjacency[vertex]:
                counters["operations"] += 1
                if colors[neighbor] == color:
                    valid = False
                    break
                if colors[neighbor] < 0 and color not in saturation[neighbor]:
                    saturation[neighbor].add(color)
                    changed.append(neighbor)
            result = search(done + 1) if valid else None
            if result is not None:
                return result
            for neighbor in changed:
                saturation[neighbor].remove(color)
            colors[vertex] = -1
            if counters["capped"]:
                return None
        return None

    started = time.perf_counter()
    result = search(0)
    counters["wall_clock_sec"] = time.perf_counter() - started
    answer = _candidate_from_colors(inst, result) if result is not None else None
    return answer, counters


def _permute_instance(inst, new_to_old, reverse_storage=False):
    old_to_new = {old: new for new, old in enumerate(new_to_old)}
    out = json.loads(json.dumps(inst))
    out["vertices"] = [json.loads(json.dumps(inst["vertices"][old]))
                       for old in new_to_old]
    out["answer"] = [inst["answer"][old] for old in new_to_old]
    edges = []
    for edge in inst["edges"]:
        u, v = old_to_new[edge["u"]], old_to_new[edge["v"]]
        if u > v:
            u, v = v, u
        forbidden = list(edge["forbidden"])
        if reverse_storage:
            forbidden.reverse()
        edges.append({"u": u, "v": v, "forbidden": forbidden})
    if reverse_storage:
        edges.reverse()
        for vertex in out["vertices"]:
            vertex["labels"].reverse()
    out["edges"] = edges
    return out


def _translate_instance(inst, amount):
    out = json.loads(json.dumps(inst))
    for vertex in out["vertices"]:
        vertex["labels"] = [label + amount for label in vertex["labels"]]
    out["answer"] = [label + amount for label in out["answer"]]
    if "label_min" in out:
        out["label_min"] += amount
    if "label_max" in out:
        out["label_max"] += amount
    return out


def _reflect_instance(inst):
    out = json.loads(json.dumps(inst))
    labels = [label for vertex in inst["vertices"] for label in vertex["labels"]]
    center_twice = min(labels) + max(labels)
    for vertex in out["vertices"]:
        vertex["labels"] = [center_twice - label for label in vertex["labels"]]
    out["answer"] = [center_twice - label for label in out["answer"]]
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    """Run mandatory gates and return their fully measured JSON-native report."""
    report = {
        "paper": "arXiv:1311.0603",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every preset over several independent seeds.
    g1_checks = 0
    construction_identity_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 999):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
            for edge in inst["edges"]:
                left = inst["vertices"][edge["u"]]["labels"]
                right = inst["vertices"][edge["v"]]["labels"]
                for left_pos, left_label in enumerate(left):
                    for right_pos, right_label in enumerate(right):
                        construction_identity_checks += 1
                        forbidden = abs(left_label - right_label) in edge["forbidden"]
                        if forbidden != (left_pos == right_pos):
                            g1_failures.append({
                                "preset": preset,
                                "seed": seed,
                                "reason": "edge constraint does not encode unequal list positions",
                            })
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "construction_identity_checks": construction_identity_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]

    # G2: requested corruption classes, with distinguishable diagnostics.
    corruptions = {}
    variants = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": planted[:2] + [max(planted) + shipping["label_step"] + 1] + planted[3:],
    }
    reasons = []
    for name, candidate in variants.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "corruptions": corruptions,
    }

    # G3: exact round-trip through realistic surrounding prose and a fence.
    body = ", ".join(map(str, planted))
    response = "I used the edge constraints.\n```text\nFinal follows.\n```\n<answer>" + body + "</answer>\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": (
            parsed == planted
            and parse_answer("not an answer") is None
            and parse_answer("<answer></answer>") is None
        ),
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
    }

    # G4 and the shipping-density half of G5 share the required 200k exact samples.
    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(773311)
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "structure_aware_space": str(search_space(shipping)),
        "sampler": "uniform over one permitted label per displayed vertex list",
    }

    # Exact demo density is useful context; shipping density remains the gated number.
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_solutions = enumerate_all(demo)
    demo_density = demo_solutions / search_space(demo)

    attack_started = time.perf_counter()
    attack_answer = _attack_spectral(shipping, 99117)
    attack_wall = time.perf_counter() - attack_started
    attack_solved = attack_answer is not None and verify(shipping, attack_answer)[0]
    reference_answer, baseline = _dsatur_reference(shipping)
    baseline_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": guess_probability < 1e-6 and not attack_solved and baseline_ok,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_probability,
        "demo_exact_solution_count": demo_solutions,
        "demo_exact_space": search_space(demo),
        "demo_exact_solution_fraction": demo_density,
        "strongest_failing_attack_wall_clock_sec": attack_wall,
        "strongest_failing_attack_name": "spectral_bottom_eigenspace_kmeans",
        "strongest_failing_attack_power_iterations": 80,
        "strongest_failing_attack_kmeans_restarts": 12,
        "strongest_failing_attack_successes": int(attack_solved),
        "baseline_reference_wall_clock_sec": baseline["wall_clock_sec"],
        "baseline_reference_nodes": baseline["nodes"],
        "baseline_reference_operations": baseline["operations"],
        "baseline_reference_verified": baseline_ok,
    }

    # G6: four failing in-context probes plus the successful Track-B reference.
    panel_seeds = list(range(9000, 9008))
    successes = {
        "outlier_degree_residue": 0,
        "raw_magnitude_buckets": 0,
        "greedy_left_to_right": 0,
        "random_restart_greedy_32": 0,
        "obvious_affine_list_minimum_ansatz": 0,
        "spectral_bottom_eigenspace_kmeans": 0,
    }
    reference_rows = []
    for seed in panel_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_degree_residue": _attack_degree_residue(inst),
            "raw_magnitude_buckets": _attack_raw_magnitude_buckets(inst),
            "greedy_left_to_right": _attack_greedy(inst),
            "random_restart_greedy_32": _attack_random_restart(inst, 700000 + seed),
            "obvious_affine_list_minimum_ansatz": _attack_affine_key(inst),
            "spectral_bottom_eigenspace_kmeans": _attack_spectral(
                inst, 810000 + seed
            ),
        }
        for name, candidate in candidates.items():
            successes[name] += int(candidate is not None and verify(inst, candidate)[0])
        answer, counters = _dsatur_reference(inst)
        counters["verified"] = answer is not None and verify(inst, answer)[0]
        reference_rows.append(counters)

    attacks = {
        name: {"successes": count, "attempts": len(panel_seeds)}
        for name, count in successes.items()
    }
    reference_successes = sum(int(row["verified"]) for row in reference_rows)
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values())
        and reference_successes == len(panel_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact DSATUR backtracking on local-list positions",
            "complexity": "O(q^n*(n+m)) worst case",
            "wall_clock_sec": statistics.median(
                row["wall_clock_sec"] for row in reference_rows
            ),
            "operations": int(statistics.median(
                row["operations"] for row in reference_rows
            )),
            "nodes": int(statistics.median(row["nodes"] for row in reference_rows)),
            "successes": reference_successes,
            "attempts": len(panel_seeds),
            "solves": f"{reference_successes}/{len(panel_seeds)}, as expected",
        },
    }

    # G7: build and verify at doubled n using the same remaining hard parameters.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=515151, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_vertices": len(doubled["vertices"]),
        "doubled_edges": len(doubled["edges"]),
        "verify_reason": doubled_reason,
    }

    # G8: all stated relabellings, their compositions, and carried witnesses.
    invariance_checks = 0
    carried_checks = 0
    invariant_failures = []
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=20000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        distinct_keys.append(base_key)
        rng = random.Random(30000 + seed)
        order = list(range(inst["n"]))
        rng.shuffle(order)
        variants = [
            _permute_instance(inst, order, reverse_storage=False),
            _permute_instance(inst, list(reversed(order)), reverse_storage=True),
            _translate_instance(inst, 37),
            _reflect_instance(inst),
            _translate_instance(_reflect_instance(
                _permute_instance(inst, order, reverse_storage=True)), 53),
            _reflect_instance(_translate_instance(
                _permute_instance(inst, list(reversed(order)), reverse_storage=True),
                71,
            )),
        ]
        for transformed in variants:
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                invariant_failures.append({"seed": seed, "kind": "key_changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                invariant_failures.append({"seed": seed, "kind": "witness_not_carried"})
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(distinct_keys)) == len(distinct_keys),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": len(distinct_keys),
        "distinct_keys": len(set(distinct_keys)),
        "failures": invariant_failures,
        "symmetries": [
            "vertex/input permutation",
            "list, edge, and forbidden-set storage order",
            "global label translation",
            "global label reflection",
            "compositions of the above",
        ],
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(planted)
    intended_operations = 4 * shipping["n"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "note": "oracle arms are recorded diagnostics; only the size/effort caps gate",
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
