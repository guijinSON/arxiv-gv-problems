"""Verified problem generator for arXiv:1804.07496.

The paper's flip gadget forces two undirected edges to receive opposite
directions; two stacked flip gadgets force the two outer edges to agree.  This
module composes those native planar gadgets into an exactly checkable family.

Generation is inverse: a GF(2) orientation key is sampled first, and every
gadget is then assembled so that the induced orientation connects its terminal
pairs.  The generator never solves the instance it has just made.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The implementation below is standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"
SHIPPING_DIFFICULTY = "hard"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "GF(2) coefficient vector",
        "GF(2)-tagged mixed graph",
        "redundant GF(2) constraint system",
    ],
    "verification_operations": [
        "GF(2) inner product",
        "exact expansion of a symbolic orientation key",
        "directed graph reachability",
    ],
    "domain_essentiality": "discretised_analogue",
    "reduction_kind": "convenience",
    "reduction": (
        "Benchmark convenience wrapper around Section 2, Figure 1(a) and the "
        "variable/edge-gadget lemmas: the paper licenses the flip identities, "
        "but not the external GF(2) edge tags or symbolic-key restriction"
    ),
    "reduction_source": "benchmark_convenience",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The GF(2) constraint rows are the complements of the coordinate "
        "basis, so a dense system collapses to one global parity and "
        "coordinatewise recovery."
    ),
    "hardness_basis": (
        "Track B: generic GF(2) Gauss-Jordan elimination is O(n^3) bit "
        "operations, measured at shipping seed 314159 as 83,678 bit "
        "operations in 0.0010 seconds; the complement-basis symmetry needs "
        "288 exact XOR operations, while mechanically carrying out 83,678 "
        "such operations is out of reach in a no-tool context."
    ),
    "max_answer_tokens": 166,
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
    "demo": {"n": 4, "copies": 1},
    "easy": {"n": 48, "copies": 1},
    "medium": {"n": 72, "copies": 1},
    "hard": {"n": 96, "copies": 1},
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A canonical list [[0,c0],[1,c1],...,[n-1,c_(n-1)]] containing "
        "exactly one bit ci in {0,1} for every coefficient index.  It denotes "
        "the orientation rule printed in the statement."
    ),
    "bounds": {
        "coefficient_count": "n from the instance",
        "coefficient_alphabet": 2,
        "canonical_indices": "0 through n-1",
        "max_atomic_elements_at_shipping": 192,
    },
}

STRUCTURAL_HINT = (
    "The GF(2) row masks are the complements of the coordinate basis."
)
PLACEBO_HINT = (
    "The edge tags and terminal-pair directions should be read consistently."
)

NOTES = """
Definition: Section 1 defines Steiner Orientation on a mixed graph as orienting
every undirected edge so that every ordered terminal pair has a directed path.

Step-0 triage: Theorem 1 proves NP-completeness only in the worst case; it does
not establish distributional hardness for a planted generator.  Section 1 also
states polynomial algorithms when there are no directed arcs and for k=2, and
an n^{O(k)} XP algorithm.  A Track-A claim would therefore be unjustified.

Construction: Section 2 and Figure 1(a) show that a flip gadget connects both
terminal pairs exactly when its two undirected edges point oppositely.  The
edge-gadget lemma states that two stacked flips synchronize the outer edges.
This generator composes those two identities.  The submitted GF(2) key is a
succinct concrete orientation: verify expands it on every tagged edge and runs
ordinary directed reachability; it never trusts the displayed constraint
synopsis or inst['answer'].

Scope correction: the paper does not introduce GF(2)-tagged edges or restrict
orientations to those induced by a symbolic key.  Those are a benchmark
convenience layer.  Accordingly this retained rejected prototype is an
algebraic discretised analogue, not native coverage of Planar Steiner
Orientation and not a paper-licensed reduction.

Track B: A specialist can extract the GF(2) equations and use generic
Gauss-Jordan elimination in polynomial time.  The shipping selftest records its
wall time and bit-operation count.  The generated rows are J+I over GF(2), up
to row order, so the compact route uses one global parity and then one XOR per
coefficient.  This route stays below the no-tool operation cap.

Attacks: independently randomized edge tags, endpoint-reference biases, vertex
labels, component order, and input order remove positional or magnitude
signatures.  Per-coordinate majority, one-pass greedy repair, random restarts,
and low-period/direct-RHS ansatzes are tested on eight shipping seeds.  Generic
elimination is expected to succeed and is reported separately, as Track B
requires.
""".strip()


def _parity(value):
    return value.bit_count() & 1


def _coeff_mask(bits):
    value = 0
    for i, bit in enumerate(bits):
        value |= (bit & 1) << i
    return value


def _answer_from_mask(mask, n):
    return [[i, (mask >> i) & 1] for i in range(n)]


def _low_complexity_masks(n):
    even = sum(1 << i for i in range(0, n, 2))
    half = (1 << (n // 2)) - 1
    return {
        0,
        (1 << n) - 1,
        even,
        ((1 << n) - 1) ^ even,
        half,
        ((1 << n) - 1) ^ half,
    }


def _sample_planted_mask(n, rng):
    """Sample a nontrivial, odd-parity key before constructing the graph."""
    forbidden = _low_complexity_masks(n)
    while True:
        value = rng.getrandbits(n)
        if _parity(value) == 0:
            value ^= 1 << rng.randrange(n)
        if value not in forbidden:
            return value


class _GraphBuilder:
    def __init__(self):
        self.vertex_count = 0
        self.arcs = []
        self.edges = []
        self.terminals = []

    def vertices(self, count):
        out = list(range(self.vertex_count, self.vertex_count + count))
        self.vertex_count += count
        return out

    def edge(self, left, right, tag, bias):
        index = len(self.edges)
        self.edges.append([left, right, tag, bias])
        return index

    def flip(self, first_index, second_index):
        """Attach the paper's Figure 1(a) flip to two existing edges."""
        first = self.edges[first_index]
        second = self.edges[second_index]
        left1, right1 = first[0], first[1]
        left2, right2 = second[0], second[1]
        s1, s2, t1, t2 = self.vertices(4)
        self.arcs.extend([
            [s1, left1], [s1, left2],
            [s2, right1], [s2, right2],
            [left1, t2], [left2, t2],
            [right1, t1], [right2, t1],
        ])
        self.terminals.extend([[s1, t1], [s2, t2]])


def _physical_bit(key_mask, edge):
    return _parity(key_mask & edge[2]) ^ edge[3]


def _add_component(builder, rng, n, key_mask, missing, copy_index):
    full = (1 << n) - 1
    row = full ^ (1 << missing)
    x_tag = rng.getrandbits(n)
    y_tag = x_tag ^ row
    x_bias = rng.randrange(2)
    y_bias = rng.randrange(2)
    relation = (_parity(key_mask & row) ^ x_bias ^ y_bias)

    x_left, x_right, y_left, y_right = builder.vertices(4)
    x_edge = builder.edge(x_left, x_right, x_tag, x_bias)
    y_edge = builder.edge(y_left, y_right, y_tag, y_bias)

    if relation == 1:
        builder.flip(x_edge, y_edge)
        edge_roles = [x_edge, y_edge]
        kind = "flip"
    else:
        m_left, m_right = builder.vertices(2)
        m_tag = rng.getrandbits(n)
        x_physical = _parity(key_mask & x_tag) ^ x_bias
        m_bias = 1 ^ x_physical ^ _parity(key_mask & m_tag)
        m_edge = builder.edge(m_left, m_right, m_tag, m_bias)
        builder.flip(x_edge, m_edge)
        builder.flip(m_edge, y_edge)
        edge_roles = [x_edge, m_edge, y_edge]
        kind = "stacked_flip"

    rhs = relation ^ x_bias ^ y_bias
    return {
        "kind": kind,
        "missing": missing,
        "copy": copy_index,
        "mask": row,
        "rhs": rhs,
        "edge_roles": edge_roles,
        # 0 means the edge record's (u,v) order agrees with this gadget role's
        # left-to-right reference.  It changes only under representation-level
        # endpoint reversal and lets canonical_key remove that convention.
        "edge_polarities": [0] * len(edge_roles),
    }


def make_instance(n, seed=0, copies=1, **params):
    """Inverse-generate a planar mixed graph and a valid symbolic orientation."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    if n > 512:
        raise ValueError("n must be at most 512")
    if not isinstance(copies, int) or isinstance(copies, bool) or not 1 <= copies <= 8:
        raise ValueError("copies must be an integer in 1..8")

    rng = random.Random(seed)
    key_mask = _sample_planted_mask(n, rng)
    builder = _GraphBuilder()
    components = []
    tasks = [(missing, rep) for missing in range(n) for rep in range(copies)]
    rng.shuffle(tasks)
    for missing, rep in tasks:
        components.append(
            _add_component(builder, rng, n, key_mask, missing, rep)
        )

    # Vertex names, and every top-level input order, are presentation noise.
    vertex_perm = list(range(builder.vertex_count))
    rng.shuffle(vertex_perm)
    arcs = [[vertex_perm[u], vertex_perm[v]] for u, v in builder.arcs]
    edges = [[vertex_perm[u], vertex_perm[v], tag, bias]
             for u, v, tag, bias in builder.edges]
    terminals = [[vertex_perm[s], vertex_perm[t]]
                 for s, t in builder.terminals]
    rng.shuffle(arcs)
    rng.shuffle(terminals)

    # Reorder edges and carry the component role indices through that relabelling.
    edge_order = list(range(len(edges)))
    rng.shuffle(edge_order)
    old_to_new = {old: new for new, old in enumerate(edge_order)}
    edges = [edges[old] for old in edge_order]
    for component in components:
        component["edge_roles"] = [old_to_new[i]
                                   for i in component["edge_roles"]]
    rng.shuffle(components)

    constraints = [[component["mask"], component["rhs"]]
                   for component in components]
    inst = {
        "n": n,
        "copies": copies,
        "vertex_count": builder.vertex_count,
        "arcs": arcs,
        "edges": edges,
        "terminal_pairs": terminals,
        "constraints": constraints,
        "components": components,
        "answer": _answer_from_mask(key_mask, n),
    }
    return inst


def _hex_width(n):
    return (n + 3) // 4


def render(inst):
    """Render a complete, self-contained statement and exact output contract."""
    n = inst["n"]
    width = _hex_width(n)
    arc_text = " ".join(f"{u}>{v}" for u, v in inst["arcs"])
    edge_text = "\n".join(
        f"  e{i}: {u}-{v} tag={tag:0{width}x} bias={bias}"
        for i, (u, v, tag, bias) in enumerate(inst["edges"])
    )
    pair_text = " ".join(f"{s}>{t}" for s, t in inst["terminal_pairs"])
    constraint_text = "\n".join(
        f"  r{i}: mask={mask:0{width}x} rhs={rhs}"
        for i, (mask, rhs) in enumerate(inst["constraints"])
    )
    statement = f"""Planar tagged Steiner orientation

A mixed graph has directed arcs and undirected edges.  Choose a symbolic
orientation key c=(c_0,...,c_{n-1}) over GF(2), meaning every c_i is 0 or 1.
For an undirected edge printed as

    e: u-v tag=h bias=b

read hexadecimal h as an {n}-bit integer whose least-significant bit is bit 0.
Compute q = b XOR (the XOR of c_i over all set bits i of h).  If q=0, orient
the edge u->v; if q=1, orient it v->u.  Endpoint order u-v is therefore part of
the input convention.  Repeated vertices and repeated tag values are allowed.

Your key is valid when, after orienting every undirected edge by this rule, each
ordered terminal pair s>t has a directed path from s to t.  A path may use both
the fixed directed arcs and the newly oriented edges.

The graph below is a disjoint union of planar flip or stacked-flip components.
For auditability, a redundant GF(2) synopsis is also supplied.  Each line
mask=m, rhs=b is the equation XOR_{{i: bit i of m is 1}} c_i = b enforced by
one component.  The graph, not this synopsis, is used to grade your answer.

Dimensions: n={n}; vertices are exactly 0..{inst['vertex_count'] - 1}.

Directed arcs (u>v):
{arc_text}

Undirected edges:
{edge_text}

Ordered terminal pairs (s>t):
{pair_text}

Redundant GF(2) constraint synopsis:
{constraint_text}

Give your final answer inside <answer></answer> tags as JSON: a list of exactly
{n} pairs [[0,c_0],[1,c_1],...,[{n - 1},c_{n - 1}]], in that increasing index
order, with every c_i written as the integer 0 or 1.  No index may be omitted or
repeated.  Example format: <answer>[[0,0],[1,1],[2,0],[3,1]]</answer>
Output nothing else inside the tags."""
    hint_mode = os.environ.get("GV_HINT_MODE")
    if hint_mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif hint_mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the JSON certificate from tags or a surrounding model response."""
    if not isinstance(text, str):
        return None
    candidates = []
    candidates.extend(re.findall(
        r"<answer\s*>(.*?)</answer\s*>", text,
        flags=re.IGNORECASE | re.DOTALL,
    ))
    if not candidates:
        candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", candidate,
                         flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            pass
        for match in re.finditer(r"\[", cleaned):
            try:
                value, _ = decoder.raw_decode(cleaned[match.start():])
                return value
            except ValueError:
                continue
    return None


def _decode_answer(inst, answer):
    n = inst["n"]
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    for item in answer:
        if not isinstance(item, list) or len(item) != 2:
            return None, "each coefficient entry must be a two-item list"
        if (not isinstance(item[0], int) or isinstance(item[0], bool)
                or not isinstance(item[1], int) or isinstance(item[1], bool)):
            return None, "coefficient indices and values must be integers"
    indices = [item[0] for item in answer]
    if len(indices) != len(set(indices)):
        return None, "duplicate coefficient index"
    if len(answer) != n:
        return None, f"wrong coefficient count: expected {n}"
    if any(index < 0 or index >= n for index in indices):
        return None, "coefficient index out of range"
    if indices != list(range(n)):
        return None, "coefficients are not in canonical increasing index order"
    if any(item[1] not in (0, 1) for item in answer):
        return None, "coefficient value is not a bit"
    return _coeff_mask([item[1] for item in answer]), "ok"


def _reachable(adjacency, source, target):
    if source == target:
        return True
    seen = {source}
    stack = [source]
    while stack:
        u = stack.pop()
        for v in adjacency[u]:
            if v == target:
                return True
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return False


def verify(inst, answer):
    """Expand a candidate key and check every terminal pair exactly."""
    key_mask, reason = _decode_answer(inst, answer)
    if key_mask is None:
        return False, reason
    vertex_count = inst["vertex_count"]
    adjacency = [[] for _ in range(vertex_count)]
    for u, v in inst["arcs"]:
        adjacency[u].append(v)
    for u, v, tag, bias in inst["edges"]:
        if _parity(key_mask & tag) ^ bias:
            adjacency[v].append(u)
        else:
            adjacency[u].append(v)
    for index, (source, target) in enumerate(inst["terminal_pairs"]):
        if not _reachable(adjacency, source, target):
            return False, (
                f"terminal pair {index} ({source}>{target}) has no directed path"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the exact n-bit certificate language."""
    return [[i, rng.randrange(2)] for i in range(inst["n"])]


def _candidate_satisfies_synopsis(inst, candidate):
    """Fast equivalent used for density sampling; verify still grades the graph."""
    mask, _ = _decode_answer(inst, candidate)
    if mask is None:
        return False
    return all(_parity(mask & row) == rhs
               for row, rhs in inst["constraints"])


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for mask in range(1 << n):
        count += int(verify(inst, _answer_from_mask(mask, n))[0])
    return count


def _logical_component_signature(inst, component):
    edges = inst["edges"]
    descriptors = [
        [edges[index][2], edges[index][3] ^ polarity]
        for index, polarity in zip(component["edge_roles"],
                                   component["edge_polarities"])
    ]
    if component["kind"] == "flip":
        normalized_edges = {"outer": sorted(descriptors)}
    else:
        normalized_edges = {
            "outer": sorted([descriptors[0], descriptors[2]]),
            "middle": descriptors[1],
        }
    return [
        component["kind"],
        component["missing"],
        component["mask"],
        component["rhs"],
        normalized_edges,
    ]


def canonical_key(inst):
    """Canonicalize component order and ignore all vertex/list relabellings."""
    components = [_logical_component_signature(inst, c)
                  for c in inst["components"]]
    components.sort(key=lambda x: json.dumps(x, separators=(",", ":")))
    normalized = {
        "n": inst["n"],
        "copies": inst["copies"],
        "components": components,
    }
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """Increase component crowding without lengthening the answer."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    copies = int(out.get("copies", 1))
    if copies < 4:
        out["copies"] = copies + 1
        return out
    if int(out.get("n", 4)) < 100:
        out["n"] = 100
        return out
    return "cap_bound"


def _constraint_rows(inst):
    return [[mask, rhs] for mask, rhs in inst["constraints"]]


def _gauss_jordan(inst):
    """Generic GF(2) reference solver; return answer and bit-operation count."""
    n = inst["n"]
    rows = _constraint_rows(inst)
    where = [-1] * n
    pivot = 0
    operations = 0
    for col in range(n):
        chosen = None
        for r in range(pivot, len(rows)):
            operations += 1
            if (rows[r][0] >> col) & 1:
                chosen = r
                break
        if chosen is None:
            continue
        if chosen != pivot:
            rows[pivot], rows[chosen] = rows[chosen], rows[pivot]
            operations += 1
        where[col] = pivot
        pivot_mask, pivot_rhs = rows[pivot]
        for r in range(len(rows)):
            if r == pivot:
                continue
            operations += 1
            if (rows[r][0] >> col) & 1:
                rows[r][0] ^= pivot_mask
                rows[r][1] ^= pivot_rhs
                operations += n + 1  # bit-XOR equivalents for the packed row.
        pivot += 1
    for mask, rhs in rows:
        operations += 1
        if mask == 0 and rhs:
            return None, operations
    solution = 0
    for col, row_index in enumerate(where):
        if row_index >= 0 and rows[row_index][1]:
            solution |= 1 << col
        operations += 1
    answer = _answer_from_mask(solution, n)
    return answer, operations


def _compact_solve(inst):
    """Exploit A=J+I; used only to cross-check the intended route."""
    n = inst["n"]
    full = (1 << n) - 1
    aligned = [None] * n
    seen_rows = set()
    operations = 0
    for mask, rhs in inst["constraints"]:
        if mask in seen_rows:
            continue
        seen_rows.add(mask)
        missing_mask = full ^ mask
        operations += 1
        if missing_mask and missing_mask & (missing_mask - 1) == 0:
            missing = missing_mask.bit_length() - 1
            if aligned[missing] is None:
                aligned[missing] = rhs
    if any(value is None for value in aligned):
        return None, operations
    global_parity = 0
    for value in aligned:
        global_parity ^= value
        operations += 1
    bits = []
    for value in aligned:
        bits.append(value ^ global_parity)
        operations += 1
    return _answer_from_mask(_coeff_mask(bits), n), operations


def _one_pass_greedy(inst):
    mask = 0
    for row, rhs in inst["constraints"]:
        if _parity(mask & row) != rhs:
            lowest = row & -row
            mask ^= lowest
    return _answer_from_mask(mask, inst["n"])


def _majority_candidate(inst):
    n = inst["n"]
    ones = [0] * n
    totals = [0] * n
    for row, rhs in inst["constraints"]:
        for i in range(n):
            if (row >> i) & 1:
                totals[i] += 1
                ones[i] += rhs
    bits = [int(2 * ones[i] >= totals[i]) for i in range(n)]
    return _answer_from_mask(_coeff_mask(bits), n)


def _ansatz_candidates(inst):
    n = inst["n"]
    full = (1 << n) - 1
    aligned_rhs = [0] * n
    for row, rhs in inst["constraints"]:
        missing = (full ^ row).bit_length() - 1
        if 0 <= missing < n:
            aligned_rhs[missing] = rhs
    rhs_mask = _coeff_mask(aligned_rhs)
    masks = set(_low_complexity_masks(n))
    masks.add(rhs_mask)  # The tempting but wrong direct-RHS reading.
    return [_answer_from_mask(mask, n) for mask in sorted(masks)]


def _relabel_vertices(inst, permutation):
    out = copy.deepcopy(inst)
    out["arcs"] = [[permutation[u], permutation[v]] for u, v in inst["arcs"]]
    out["edges"] = [[permutation[u], permutation[v], tag, bias]
                    for u, v, tag, bias in inst["edges"]]
    out["terminal_pairs"] = [[permutation[s], permutation[t]]
                             for s, t in inst["terminal_pairs"]]
    return out


def _reorder_inputs(inst, rng):
    out = copy.deepcopy(inst)
    rng.shuffle(out["arcs"])
    rng.shuffle(out["terminal_pairs"])
    rng.shuffle(out["components"])
    rng.shuffle(out["constraints"])
    edge_order = list(range(len(out["edges"])))
    rng.shuffle(edge_order)
    old_to_new = {old: new for new, old in enumerate(edge_order)}
    out["edges"] = [out["edges"][old] for old in edge_order]
    for component in out["components"]:
        component["edge_roles"] = [old_to_new[i]
                                   for i in component["edge_roles"]]
    return out


def _reverse_edge_records(inst, rng):
    """Reverse endpoint conventions while preserving every induced orientation."""
    out = copy.deepcopy(inst)
    reversed_indices = set()
    for index, edge in enumerate(out["edges"]):
        if rng.randrange(2):
            edge[0], edge[1] = edge[1], edge[0]
            edge[3] ^= 1
            reversed_indices.add(index)
    for component in out["components"]:
        for role, edge_index in enumerate(component["edge_roles"]):
            if edge_index in reversed_indices:
                component["edge_polarities"][role] ^= 1
    return out


def _reflect_component_roles(inst, rng):
    """Swap symmetric outer roles; this changes no graph data or solution."""
    out = copy.deepcopy(inst)
    for component in out["components"]:
        if not rng.randrange(2):
            continue
        if component["kind"] == "flip":
            component["edge_roles"].reverse()
            component["edge_polarities"].reverse()
        else:
            component["edge_roles"][0], component["edge_roles"][2] = (
                component["edge_roles"][2], component["edge_roles"][0]
            )
            component["edge_polarities"][0], component["edge_polarities"][2] = (
                component["edge_polarities"][2],
                component["edge_polarities"][0],
            )
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


# Filled from the external hardening runs.  These data never trigger network IO.
G9_MEASUREMENTS = {
    "bare": {
        "solved": 0, "attempts": 0,
        "errors": 4, "status": "unmeasured: OpenRouter total key limit exceeded",
    },
    "hinted": {
        "solved": 0, "attempts": 0,
        "errors": 4, "status": "unmeasured: OpenRouter total key limit exceeded",
    },
    "placebo": {
        "solved": 0, "attempts": 0,
        "errors": 4, "status": "unmeasured: OpenRouter total key limit exceeded",
    },
    "hinted_verdict": "unmeasured: OpenRouter total key limit exceeded",
}


def selftest():
    report = {}

    planted_checks = 0
    compact_crosschecks = 0
    json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError((preset, seed, reason))
            planted_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
            compact, _ = _compact_solve(inst)
            if compact != inst["answer"] or not verify(inst, compact)[0]:
                raise AssertionError((preset, seed, "compact route mismatch"))
            compact_crosschecks += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "checks": planted_checks,
        "compact_route_crosschecks": compact_crosschecks,
        "json_native_checks": json_checks,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    good = shipping["answer"]
    variants = {}
    variants["drop"] = copy.deepcopy(good[:-1])
    swapped = copy.deepcopy(good)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    variants["swap"] = swapped
    duplicated = copy.deepcopy(good)
    duplicated[-1][0] = duplicated[-2][0]
    variants["duplicate"] = duplicated
    variants["empty"] = []
    outside = copy.deepcopy(good)
    outside[-1][0] = shipping["n"]
    variants["out_of_range"] = outside
    corruptions = {}
    for name, candidate in variants.items():
        ok, reason = verify(shipping, candidate)
        if ok:
            raise AssertionError((name, "corruption accepted"))
        corruptions[name] = reason
    if len(set(corruptions.values())) != len(corruptions):
        raise AssertionError("corruption reasons are not distinct")
    report["G2_rejects_corruption"] = {
        "pass": True,
        "cases": corruptions,
    }

    model_style = (
        "The complement rows share one global parity.\n```json\n<answer>"
        + json.dumps(good, separators=(",", ":"))
        + "</answer>\n```\nAll indices are zero-based."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == good,
        "model_style_response_parsed": parsed == good,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    guess_rng = random.Random(0x180407496)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        guess_hits += int(_candidate_satisfies_synopsis(shipping, candidate))
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "certificate_space": search_space(shipping),
        "sampling_prior": "uniform over canonical n-bit symbolic keys",
    }

    demo = make_instance(seed=9, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    start = time.perf_counter()
    reference_answer, reference_operations = _gauss_jordan(shipping)
    reference_wall = time.perf_counter() - start
    reference_ok = reference_answer is not None and verify(
        shipping, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_ok
                and guess_hits / guess_total < 1e-6,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_sampled_density": guess_hits / guess_total,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "baseline_wall_seconds": reference_wall,
        "baseline_bit_operations": reference_operations,
    }

    attack_results = {
        "outlier_per_coordinate_majority": {"successes": 0, "attempts": 0},
        "greedy_one_pass_lowest_bit_repair": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_low_period_and_direct_rhs_ansatz": {
            "successes": 0, "attempts": 0,
        },
    }
    reference_successes = 0
    reference_max_operations = 0
    reference_start = time.perf_counter()
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])

        majority = _majority_candidate(inst)
        attack_results["outlier_per_coordinate_majority"]["successes"] += int(
            verify(inst, majority)[0]
        )
        attack_results["outlier_per_coordinate_majority"]["attempts"] += 1

        greedy = _one_pass_greedy(inst)
        attack_results["greedy_one_pass_lowest_bit_repair"]["successes"] += int(
            verify(inst, greedy)[0]
        )
        attack_results["greedy_one_pass_lowest_bit_repair"]["attempts"] += 1

        rrng = random.Random(seed ^ 0xBAD5EED)
        random_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rrng))[0]:
                random_solved = True
                break
        attack_results["random_restart_256"]["successes"] += int(random_solved)
        attack_results["random_restart_256"]["attempts"] += 1

        ansatz_solved = any(verify(inst, candidate)[0]
                            for candidate in _ansatz_candidates(inst))
        attack_results[
            "in_context_low_period_and_direct_rhs_ansatz"
        ]["successes"] += int(ansatz_solved)
        attack_results[
            "in_context_low_period_and_direct_rhs_ansatz"
        ]["attempts"] += 1

        ref_answer, ref_operations = _gauss_jordan(inst)
        reference_successes += int(
            ref_answer is not None and verify(inst, ref_answer)[0]
        )
        reference_max_operations = max(reference_max_operations, ref_operations)
    reference_total_wall = time.perf_counter() - reference_start
    all_failed = all(v["successes"] == 0 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "generic GF(2) Gauss-Jordan elimination",
            "complexity": "O(m*n^2), hence O(n^3) for m=Theta(n), exact",
            "wall_clock_sec": reference_total_wall,
            "operations": reference_max_operations,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        copies=DIFFICULTY[SHIPPING_DIFFICULTY]["copies"],
        seed=271828,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] > shipping["vertex_count"],
        "shipping_n": shipping["n"],
        "shipping_vertices": shipping["vertex_count"],
        "doubled_n": doubled["n"],
        "doubled_vertices": doubled["vertex_count"],
    }

    invariant_checks = 0
    real_transform_checks = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        keys.append(base_key)
        rrng = random.Random(90_000 + seed)
        permutation = list(range(inst["vertex_count"]))
        rrng.shuffle(permutation)
        relabelled = _relabel_vertices(inst, permutation)
        reordered = _reorder_inputs(inst, rrng)
        endpoint_reversed = _reverse_edge_records(inst, rrng)
        role_reflected = _reflect_component_roles(inst, rrng)
        composed = _reflect_component_roles(
            _reverse_edge_records(_reorder_inputs(relabelled, rrng), rrng),
            rrng,
        )
        for transformed in (
                relabelled, reordered, endpoint_reversed, role_reflected, composed):
            if canonical_key(transformed) != base_key:
                raise AssertionError("canonical key changed under relabelling")
            invariant_checks += 1
            if not verify(transformed, inst["answer"])[0]:
                raise AssertionError("relabelling did not preserve the problem")
            real_transform_checks += 1
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 100 and real_transform_checks == 100
                and distinct == 20,
        "invariance_checks": invariant_checks,
        "problem_preserving_transform_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "symmetries_tested": [
            "vertex renaming",
            "arc/edge/terminal/component/constraint input reordering",
            "endpoint-order reversal with bias transport",
            "flip/stacked-flip outer-role reflection",
            "their composition",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    compact_answer, intended_operations = _compact_solve(shipping)
    if compact_answer != shipping["answer"]:
        raise AssertionError("shipping compact solve mismatch")
    arms = {name: dict(G9_MEASUREMENTS[name])
            for name in ("bare", "hinted", "placebo")}
    hint_delta = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hint_delta = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
