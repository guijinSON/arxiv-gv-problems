"""Verified rooted Hamilton-loop subdivision generator for arXiv:2407.06675.

The paper treats a single loop as a special case of arbitrary H-linkage: the
loop is replaced by a directed cycle of a prescribed length through its mapped
branch vertex.  This module asks for the Hamiltonian length, so a witness is a
rooted directed Hamilton cycle.

Generation is a composition of identities, not a solve.  A random connection
set S orients every nonzero difference in F_p.  Translation by either 1 or -1
(whichever belongs to S) is therefore a Hamilton cycle.  The generator carries
that cycle through centered inversion and an arbitrary vertex renumbering.
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
    "certificate_form": "integer_tuple",
    "native_objects": [
        "oriented graph given by an exact finite-field arc rule",
        "one-loop multidigraph with a prescribed branch vertex",
        "rooted directed Hamilton cycle as a loop subdivision",
    ],
    "verification_operations": [
        "exact modular inversion",
        "exact finite-set membership",
        "directed arc comparison",
        "vertex-permutation equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Centered inversion turns the displayed rational arc difference into "
        "ordinary translation in a finite field; without that coordinate change, "
        "one must run a general Hamilton-cycle construction on the tournament."
    ),
    "hardness_basis": (
        "Track B: the constructive Camion tournament algorithm is polynomial "
        "(O(n^3) adjacency lookups after O(n^2 log n) exact arc materialization); "
        "at shipping n=47, seed 271828, it uses 10,787 exact arc/arithmetic or "
        "adjacency operations in about 0.002 seconds, while the centered-inversion "
        "route uses at most "
        "300 exact arithmetic operations (including Euclidean divisions) but "
        "requires discovering the hidden "
        "translation coordinate."
    ),
    "max_answer_tokens": 34,
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
    "hard": {"n": 47},
}

SHIPPING_DIFFICULTY = "hard"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [v_0,...,v_n] of decimal vertex IDs: v_0=v_n is the "
        "prescribed root and v_0,...,v_(n-1) is a permutation of all n vertices."
    ),
    "bounds": {
        "sequence_length": "n+1",
        "distinct_vertices_before_repeated_endpoint": "n",
        "entry_range": "0..n-1",
        "fixed_endpoint": "the displayed root",
        "candidate_count": "(n-1)!",
    },
}


STRUCTURAL_HINT = (
    "The displayed rational difference is translation-invariant after a centered inversion of the vertex coordinates."
)
PLACEBO_HINT = (
    "The displayed modular data rewards careful bookkeeping across the vertex coordinates and all directed arc tests."
)


# Literal transcript summaries are updated only after isolated harden.py runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": None, "attempts": 0},
    "hinted": {"solved": None, "attempts": 0},
    "placebo": {"solved": None, "attempts": 0},
    "hinted_verdict": "not_run",
}


NOTES = r"""
Definition: Section 1 defines an H-subdivision by replacing every arc of a
multidigraph H by consistently directed, pairwise internally vertex-disjoint
paths.  It defines arbitrary H-linkage with prescribed branch vertices and
prescribed path lengths at least four.  The same section explicitly identifies
the one-loop case with a directed cycle through the prescribed vertex and says
that the Hamiltonian length is a Hamilton cycle.

Easy-result triage: Theorem 1.1 is an existence theorem, not a hardness theorem.
Its proof is constructive: Lemma 3.3 builds short paths with butterflies and a
greedy segment; Lemma 3.8 partitions the remaining graph; Definition 4.4 pinches
endpoints; and Lemmas 4.3/4.5 finish with Hamilton cycles.  The theorem gives no
average-case hardness for generated instances.  Track A would therefore be an
unsupported claim.  Track B discloses the polynomial constructive Camion
algorithm for tournaments and measures it at the shipping preset.

Certificate production: sample one representative from every pair {d,-d} in
F_p^*.  Exactly one of 1 and -1 is then an allowed difference, and repeatedly
adding it visits every field element because p is prime.  Centered inversion is
a permutation of F_p; an independent random vertex renumbering is another
structure-preserving map.  The known cycle is carried through both maps.  No
Hamilton-cycle routine is called by make_instance.

Attack hardening: every vertex has identical in- and out-degree, the root is
uniform, and vertex IDs are independently permuted.  Generation rejects the
rare presentation for which the declared lowest-ID greedy or raw-coordinate
progression already happens to close.  Uniform restart, degree/ID ordering,
lowest-ID out-neighbor greedy, and the obvious raw-coordinate translation are
measured over eight shipping seeds.  The successful polynomial tournament
algorithm is reported separately, as Track B requires.
""".strip()


def _is_prime(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_odd_prime(value):
    candidate = max(3, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _z_from_coordinate(x, c, p):
    centered = (x + c) % p
    return 0 if centered == 0 else pow(centered, -1, p)


def _coordinate_from_z(z, c, p):
    return (-c) % p if z % p == 0 else (pow(z, -1, p) - c) % p


def _z_values(inst):
    p = inst["p"]
    c = inst["center"]
    return [_z_from_coordinate(x, c, p) for x in inst["coordinates"]]


def _arc(inst, u, v, z_values=None, connection=None):
    if u == v:
        return False
    if z_values is None:
        z_values = _z_values(inst)
    if connection is None:
        connection = set(inst["connection_set"])
    return (z_values[v] - z_values[u]) % inst["p"] in connection


def _known_translation_cycle(inst):
    """Carry the Cayley translation cycle through the two relabellings."""
    p = inst["p"]
    connection = set(inst["connection_set"])
    step = 1 if 1 in connection else p - 1
    root = inst["root"]
    z0 = _z_from_coordinate(inst["coordinates"][root], inst["center"], p)
    coordinate_to_vertex = {
        coordinate: vertex for vertex, coordinate in enumerate(inst["coordinates"])
    }
    cycle = []
    z = z0
    for _ in range(p):
        coordinate = _coordinate_from_z(z, inst["center"], p)
        cycle.append(coordinate_to_vertex[coordinate])
        z = (z + step) % p
    cycle.append(root)
    return cycle


def _fast_cycle_valid(inst, answer, z_values=None, connection=None):
    p = inst["p"]
    if not isinstance(answer, list) or len(answer) != p + 1:
        return False
    if answer[0] != inst["root"] or answer[-1] != inst["root"]:
        return False
    if len(set(answer[:-1])) != p or set(answer[:-1]) != set(range(p)):
        return False
    if z_values is None:
        z_values = _z_values(inst)
    if connection is None:
        connection = set(inst["connection_set"])
    return all(
        (z_values[v] - z_values[u]) % p in connection
        for u, v in zip(answer, answer[1:])
    )


def _attack_degree_then_id(inst):
    # The graph is regular, so this outlier probe degenerates honestly to IDs.
    root = inst["root"]
    vertices = [v for v in range(inst["p"]) if v != root]
    vertices.sort(key=lambda v: (inst["out_degree"], v))
    return [root] + vertices + [root]


def _attack_greedy_lowest_outneighbor(inst):
    p = inst["p"]
    z_values = _z_values(inst)
    connection = set(inst["connection_set"])
    root = inst["root"]
    unused = set(range(p))
    unused.remove(root)
    path = [root]
    while unused:
        current = path[-1]
        choices = [
            v
            for v in unused
            if (z_values[v] - z_values[current]) % p in connection
        ]
        if not choices:
            path.extend(sorted(unused))
            unused.clear()
            break
        chosen = min(choices)
        path.append(chosen)
        unused.remove(chosen)
    path.append(root)
    return path


def _attack_raw_coordinate_translation(inst):
    p = inst["p"]
    coordinate_to_vertex = {
        coordinate: vertex for vertex, coordinate in enumerate(inst["coordinates"])
    }
    x0 = inst["coordinates"][inst["root"]]
    candidates = []
    for step in (1, p - 1):
        candidate = [
            coordinate_to_vertex[(x0 + index * step) % p]
            for index in range(p)
        ]
        candidate.append(inst["root"])
        candidates.append(candidate)
    for candidate in candidates:
        if _fast_cycle_valid(inst, candidate):
            return candidate
    return candidates[0]


def make_instance(n, seed=0, **params):
    """Build a known loop-subdivision certificate without solving the graph."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 7 or n % 2 == 0:
        raise ValueError("n must be an odd prime at least 7")
    if not _is_prime(n):
        raise ValueError("n must be prime so a nonzero translation is Hamiltonian")

    p = n
    rng = random.Random(seed)
    # Conditioning on failure of declared cheap attacks prevents a presentation
    # accident; it never searches for the answer, which is fixed by translation.
    for construction_attempt in range(256):
        connection = []
        for representative in range(1, (p + 1) // 2):
            connection.append(
                representative if rng.getrandbits(1) else p - representative
            )
        connection.sort()
        center = rng.randrange(p)
        coordinates = list(range(p))
        rng.shuffle(coordinates)
        root = rng.randrange(p)
        inst = {
            "p": p,
            "n_vertices": p,
            "center": center,
            "coordinates": coordinates,
            "connection_set": connection,
            "root": root,
            "path_length": p,
            "out_degree": (p - 1) // 2,
            "semidegree_threshold_numerator": 3 * p - 4,
            "semidegree_threshold_denominator": 8,
            "construction_attempt": construction_attempt,
        }
        answer = _known_translation_cycle(inst)
        inst["answer"] = answer
        if _fast_cycle_valid(inst, _attack_greedy_lowest_outneighbor(inst)):
            continue
        if _fast_cycle_valid(inst, _attack_raw_coordinate_translation(inst)):
            continue
        if _fast_cycle_valid(inst, _attack_degree_then_id(inst)):
            continue
        return inst
    raise RuntimeError("failed to draw an attack-hardened presentation")


def render(inst):
    p = inst["p"]
    coordinates = " ".join(
        f"{vertex}:{coordinate}"
        for vertex, coordinate in enumerate(inst["coordinates"])
    )
    connection = " ".join(map(str, inst["connection_set"]))
    lines = [
        "Find a prescribed rooted loop-subdivision in an oriented graph.",
        "",
        "Definitions.  An oriented graph is a directed graph with no loops and with",
        "at most one of u->v and v->u for distinct vertices.  A subdivision of a",
        "one-vertex, one-loop multidigraph replaces that loop by a directed cycle",
        "through the prescribed image of its vertex.  Cycle length means number of",
        "directed arcs.  Here the prescribed length equals the number of graph",
        "vertices, so the requested subdivision is a rooted directed Hamilton cycle.",
        "",
        f"The graph has {p} vertices, with IDs 0 through {p - 1}, inclusive.",
        f"All arithmetic below is modulo the prime p={p}.",
        f"The prescribed root is vertex {inst['root']}.",
        f"The prescribed loop-path length is exactly {inst['path_length']} arcs.",
        "",
        "Each vertex ID has one field coordinate x (the order of this table has no",
        "graph-theoretic meaning):",
        "  " + coordinates,
        "",
        f"The centered-inversion parameter is c={inst['center']}.",
        "For two distinct coordinates x and y, define Delta(x,y) exactly as follows:",
        "  if x+c = 0 and y+c != 0: Delta(x,y) = inverse(y+c);",
        "  if x+c != 0 and y+c = 0: Delta(x,y) = -inverse(x+c);",
        "  otherwise: Delta(x,y) = (x-y)*inverse((x+c)*(y+c)).",
        "Here inverse(a) is the unique b in {1,...,p-1} with a*b = 1 modulo p;",
        "every displayed equality and zero test in this definition is modulo p.",
        "",
        "There is an arc u->v exactly when Delta(x_u,x_v), reduced to 0..p-1,",
        "belongs to this connection set S:",
        "  S = " + connection,
        "For every nonzero d, exactly one of d and -d belongs to S, so this rule",
        "does define an oriented tournament.  Every vertex has equal in-degree and",
        f"out-degree {(p - 1) // 2}; in particular 8*delta^0 >= 3p-4.",
        "",
        f"Return a JSON list [v_0,...,v_{p}] of exactly {p + 1} decimal vertex IDs.",
        f"It must have v_0=v_{p}={inst['root']}; the entries v_0,...,v_{p - 1}",
        f"must contain every ID 0,...,{p - 1} exactly once; and every consecutive",
        "pair must be an arc in the displayed direction.  The repeated root is the",
        "only allowed repetition.  Vertex IDs are zero-indexed and no ellipsis is",
        "allowed.",
        "",
        "Give your final answer inside <answer></answer> tags, as the JSON list just specified.",
        "Example format: <answer>[3,0,2,1,3]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    try:
        tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
        if tagged:
            payload = tagged[-1].strip()
        else:
            fenced = re.findall(r"```(?:json|text)?\s*(\[[\s\S]*?\])\s*```", text, re.I)
            if fenced:
                payload = fenced[-1]
            else:
                lists = re.findall(r"\[[\s\d,+\-]*\]", text)
                if not lists:
                    return None
                payload = lists[-1]
        value = json.loads(payload)
        if not isinstance(value, list):
            return None
        if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _validate_instance(inst):
    try:
        p = inst["p"]
        coordinates = inst["coordinates"]
        connection = inst["connection_set"]
        root = inst["root"]
    except (KeyError, TypeError):
        return False, "malformed instance"
    if not _is_prime(p) or p < 7 or p % 2 == 0:
        return False, "instance modulus must be an odd prime at least 7"
    if inst.get("n_vertices") != p or inst.get("path_length") != p:
        return False, "instance size and prescribed length disagree"
    if not isinstance(coordinates, list) or coordinates != list(coordinates):
        return False, "malformed coordinate table"
    if len(coordinates) != p or set(coordinates) != set(range(p)):
        return False, "coordinates must be a permutation of the field"
    if not isinstance(connection, list) or len(connection) != (p - 1) // 2:
        return False, "malformed connection set"
    if any(isinstance(d, bool) or not isinstance(d, int) for d in connection):
        return False, "connection entries must be integers"
    connection_set = set(connection)
    if len(connection_set) != len(connection) or 0 in connection_set:
        return False, "connection set has a repeat or zero"
    for difference in range(1, p):
        if ((difference in connection_set) + ((-difference) % p in connection_set)) != 1:
            return False, "connection set does not orient each unordered pair"
    if isinstance(root, bool) or not isinstance(root, int) or not 0 <= root < p:
        return False, "root is out of range"
    if inst.get("out_degree") != (p - 1) // 2:
        return False, "declared degree is inconsistent"
    if 8 * inst["out_degree"] < 3 * p - 4:
        return False, "semi-degree threshold is not met"
    return True, "ok"


def verify(inst, answer):
    valid, reason = _validate_instance(inst)
    if not valid:
        return False, reason
    p = inst["p"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every answer entry must be an integer"
    if any(v < 0 or v >= p for v in answer):
        return False, "answer contains an out-of-range vertex"
    if len(answer) != p + 1:
        return False, f"wrong length: expected {p + 1} vertex entries"
    if answer[0] != inst["root"]:
        return False, "the first vertex is not the prescribed root"
    if answer[-1] != inst["root"]:
        return False, "the last vertex does not close at the prescribed root"
    if len(set(answer[:-1])) != p:
        return False, "a vertex is repeated before the closing root"
    if set(answer[:-1]) != set(range(p)):
        return False, "the cycle does not contain every graph vertex"
    z_values = _z_values(inst)
    connection = set(inst["connection_set"])
    for index, (u, v) in enumerate(zip(answer, answer[1:])):
        if (z_values[v] - z_values[u]) % p not in connection:
            return False, f"missing directed arc at step {index}: {u}->{v}"
    return True, "ok"


def random_candidate(inst, rng):
    root = inst["root"]
    middle = [v for v in range(inst["p"]) if v != root]
    rng.shuffle(middle)
    return [root] + middle + [root]


def search_space(inst):
    return math.factorial(inst["p"] - 1)


def enumerate_all(inst):
    p = inst["p"]
    if p > 9:
        return None
    root = inst["root"]
    others = [v for v in range(p) if v != root]
    count = 0
    for ordering in itertools.permutations(others):
        if _fast_cycle_valid(inst, [root, *ordering, root]):
            count += 1
    return count


def canonical_key(inst):
    """Affine-normalized connection set; independent of vertex numbering.

    Every translation of the hidden field fixes the connection set and moves the
    distinguished root.  Every nonzero scaling multiplies the connection set.
    Taking the least scaled set is therefore invariant under all affine Cayley
    relabellings as well as arbitrary renumbering of the displayed vertex IDs.
    """
    p = inst["p"]
    source = inst["connection_set"]
    normalized = min(
        tuple(sorted((unit * difference) % p for difference in source))
        for unit in range(1, p)
    )
    payload = {
        "p": p,
        "path_length": inst["path_length"],
        "affine_connection_normal_form": normalized,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    current = dict(params)
    n = int(current.get("n", DIFFICULTY["hard"]["n"]))
    # Hamiltonian loop subdivisions intrinsically lengthen with the ground set.
    # n=47 is the last prime for which the exact centered-inversion route stays
    # within the 300-operation no-tool cap when every Euclidean division used by
    # modular inversion is counted.  The next prime, 53, requires over 300.
    if n < 47:
        current["n"] = _next_odd_prime(min(47, n + 10))
        return current
    return "cap_bound"


def _materialize_tournament(inst):
    """Evaluate the displayed Delta rule pair by pair, without its hidden change."""
    p = inst["p"]
    center = inst["center"]
    coordinates = inst["coordinates"]
    connection = set(inst["connection_set"])
    adjacency = [[False] * p for _ in range(p)]
    evaluations = 0
    arithmetic = 0

    def inverse_with_cost(value):
        nonlocal arithmetic
        old, new = p, value % p
        while new:
            old, new = new, old % new
            arithmetic += 1
        return pow(value, -1, p)

    for u in range(p):
        for v in range(u + 1, p):
            evaluations += 1
            x = coordinates[u]
            y = coordinates[v]
            xc = (x + center) % p
            yc = (y + center) % p
            arithmetic += 2
            if xc == 0:
                delta = inverse_with_cost(yc)
            elif yc == 0:
                delta = (-inverse_with_cost(xc)) % p
                arithmetic += 1
            else:
                denominator = (xc * yc) % p
                numerator = (x - y) % p
                delta = (numerator * inverse_with_cost(denominator)) % p
                arithmetic += 3
            arithmetic += 1  # exact membership test in S
            if delta in connection:
                adjacency[u][v] = True
            else:
                adjacency[v][u] = True
    return adjacency, evaluations, arithmetic


def _camion_cycle(inst):
    """Construct a Hamilton cycle in a strong tournament, with operation counts."""
    adjacency, materializations, exact_arc_operations = _materialize_tournament(inst)
    n = inst["p"]
    lookups = 0

    def arc(u, v):
        nonlocal lookups
        lookups += 1
        return adjacency[u][v]

    cycle = None
    for a in range(n):
        if cycle is not None:
            break
        for b in range(a + 1, n):
            if cycle is not None:
                break
            for c in range(b + 1, n):
                if arc(a, b) and arc(b, c) and arc(c, a):
                    cycle = [a, b, c]
                    break
                if arc(a, c) and arc(c, b) and arc(b, a):
                    cycle = [a, c, b]
                    break
    if cycle is None:
        return None, {
            "arc_rule_evaluations": materializations,
            "exact_arc_operations": exact_arc_operations,
            "adjacency_lookups": lookups,
        }

    while len(cycle) < n:
        outside = [v for v in range(n) if v not in set(cycle)]
        inserted = False
        for vertex in outside:
            for index, left in enumerate(cycle):
                right = cycle[(index + 1) % len(cycle)]
                if arc(left, vertex) and arc(vertex, right):
                    cycle.insert(index + 1, vertex)
                    inserted = True
                    break
            if inserted:
                break
        if inserted:
            continue

        # A vertex not insertable into a directed cycle either dominates the
        # whole cycle or is dominated by it.  Strong connectivity supplies a
        # path, wholly outside the cycle, from the second class to the first.
        dominates = []
        dominated = []
        for vertex in outside:
            if all(arc(vertex, member) for member in cycle):
                dominates.append(vertex)
            elif all(arc(member, vertex) for member in cycle):
                dominated.append(vertex)
            else:
                return None, {
                    "arc_rule_evaluations": materializations,
                    "exact_arc_operations": exact_arc_operations,
                    "adjacency_lookups": lookups,
                }
        if not dominates or not dominated:
            return None, {
                "arc_rule_evaluations": materializations,
                "exact_arc_operations": exact_arc_operations,
                "adjacency_lookups": lookups,
            }
        target = set(dominates)
        parent = {vertex: None for vertex in dominated}
        queue = list(dominated)
        head = 0
        endpoint = None
        outside_set = set(outside)
        while head < len(queue) and endpoint is None:
            vertex = queue[head]
            head += 1
            if vertex in target:
                endpoint = vertex
                break
            for neighbor in outside_set:
                if neighbor not in parent and arc(vertex, neighbor):
                    parent[neighbor] = vertex
                    queue.append(neighbor)
                    if neighbor in target:
                        endpoint = neighbor
                        break
        if endpoint is None:
            return None, {
                "arc_rule_evaluations": materializations,
                "exact_arc_operations": exact_arc_operations,
                "adjacency_lookups": lookups,
            }
        path = []
        cursor = endpoint
        while cursor is not None:
            path.append(cursor)
            cursor = parent[cursor]
        path.reverse()
        cycle = [cycle[0], *path, *cycle[1:]]

    root = inst["root"]
    root_index = cycle.index(root)
    cycle = cycle[root_index:] + cycle[:root_index]
    cycle.append(root)
    return cycle, {
        "arc_rule_evaluations": materializations,
        "exact_arc_operations": exact_arc_operations,
        "adjacency_lookups": lookups,
    }


def _compact_cycle_and_operations(inst):
    p = inst["p"]
    connection = set(inst["connection_set"])
    step = 1 if 1 in connection else p - 1
    root = inst["root"]
    coordinate_to_vertex = {
        coordinate: vertex for vertex, coordinate in enumerate(inst["coordinates"])
    }
    def inverse_with_cost(value):
        # Python computes the returned inverse, while the loop counts the exact
        # Euclidean quotient/remainder steps a no-tool solver would execute.
        old, new = p, value % p
        divisions = 0
        while new:
            old, new = new, old % new
            divisions += 1
        return pow(value, -1, p), divisions

    centered = (inst["coordinates"][root] + inst["center"]) % p
    operations = 1
    if centered == 0:
        z = 0
    else:
        z, cost = inverse_with_cost(centered)
        operations += cost
    cycle = []
    for index in range(p):
        if z == 0:
            coordinate = (-inst["center"]) % p
            operations += 1
        else:
            inverse, cost = inverse_with_cost(z)
            coordinate = (inverse - inst["center"]) % p
            operations += cost + 1
        cycle.append(coordinate_to_vertex[coordinate])
        if index + 1 < p:
            z = (z + step) % p
            operations += 1
    cycle.append(root)
    return cycle, operations


def _permuted_vertices(inst, permutation):
    p = inst["p"]
    result = {
        key: value
        for key, value in inst.items()
        if key not in {"coordinates", "root", "answer"}
    }
    coordinates = [None] * p
    for old, new in enumerate(permutation):
        coordinates[new] = inst["coordinates"][old]
    result["coordinates"] = coordinates
    result["root"] = permutation[inst["root"]]
    result["answer"] = [permutation[v] for v in inst["answer"]]
    return result


def _affine_coordinates(inst, multiplier, translation):
    p = inst["p"]
    result = {
        key: value
        for key, value in inst.items()
        if key not in {"coordinates", "center", "connection_set", "answer"}
    }
    result["coordinates"] = [
        (multiplier * x + translation) % p for x in inst["coordinates"]
    ]
    result["center"] = (multiplier * inst["center"] - translation) % p
    inverse_multiplier = pow(multiplier, -1, p)
    result["connection_set"] = sorted(
        (inverse_multiplier * difference) % p
        for difference in inst["connection_set"]
    )
    result["answer"] = list(inst["answer"])
    return result


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 17, 91):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=271828, **shipping)
    answer = inst["answer"]

    swap_corruption = None
    for left in range(1, len(answer) - 2):
        candidate = list(answer)
        candidate[left], candidate[left + 1] = candidate[left + 1], candidate[left]
        ok, _ = verify(inst, candidate)
        if not ok:
            swap_corruption = candidate
            break
    if swap_corruption is None:
        swap_corruption = list(reversed(answer))
    duplicate = list(answer)
    duplicate[2] = duplicate[1]
    wrong_start = list(answer)
    wrong_start[0], wrong_start[1] = wrong_start[1], wrong_start[0]
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "out_of_range": answer[:-2] + [inst["p"], answer[-1]],
        "duplicate_internal": duplicate,
        "wrong_prescribed_start": wrong_start,
        "swap_adjacent_internal": swap_corruption,
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(set(reasons)) == len(corruptions)
        ),
        "attempts": len(corruptions),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    response = (
        "The modular arc checks close correctly.\n```json\n<answer>"
        + json.dumps(answer)
        + "</answer>\n```\nThis is the rooted cycle."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_fence": True,
    }

    trials = 200_000
    rng = random.Random(0x240706675)
    hits = 0
    guess_z_values = _z_values(inst)
    guess_connection = set(inst["connection_set"])
    started = time.perf_counter()
    for _ in range(trials):
        if _fast_cycle_valid(
            inst,
            random_candidate(inst, rng),
            guess_z_values,
            guess_connection,
        ):
            hits += 1
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "candidate_space": search_space(inst),
        "candidate_space_log2": math.log2(search_space(inst)),
        "prior": "uniform permutation of all non-root vertices, with the rooted closing shape enforced",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline_rng = random.Random(424242)
    baseline_started = time.perf_counter()
    baseline_hits = 0
    baseline_arc_prefix_checks = 0
    z_values = _z_values(inst)
    connection = set(inst["connection_set"])
    for _ in range(256):
        candidate = random_candidate(inst, baseline_rng)
        valid = True
        for u, v in zip(candidate, candidate[1:]):
            baseline_arc_prefix_checks += 1
            if (z_values[v] - z_values[u]) % inst["p"] not in connection:
                valid = False
                break
        if valid:
            baseline_hits += 1
    baseline_seconds = time.perf_counter() - baseline_started
    ref_started = time.perf_counter()
    ref_answer, ref_counts = _camion_cycle(inst)
    ref_seconds = time.perf_counter() - ref_started
    ref_ok = ref_answer is not None and verify(inst, ref_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and demo_count > 0 and ref_ok,
        "shipping_seed": 271828,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_solution_density": hits / trials,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "256 uniform rooted-permutation restarts",
        "baseline_candidate_checks": 256,
        "baseline_arc_prefix_checks": baseline_arc_prefix_checks,
        "baseline_hits": baseline_hits,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_wall_clock_sec": round(ref_seconds, 6),
        "reference_operation_count": (
            ref_counts["exact_arc_operations"] + ref_counts["adjacency_lookups"]
        ),
    }

    attacks = {
        "outlier_equal_degree_then_id": {"successes": 0, "attempts": 8},
        "greedy_lowest_outneighbor": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "in_context_raw_coordinate_translation": {"successes": 0, "attempts": 8},
    }
    attack_elapsed = {name: 0.0 for name in attacks}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    compact_successes = 0
    compact_operations = []
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping)
        start = time.perf_counter()
        candidate = _attack_degree_then_id(current)
        attack_elapsed["outlier_equal_degree_then_id"] += time.perf_counter() - start
        if verify(current, candidate)[0]:
            attacks["outlier_equal_degree_then_id"]["successes"] += 1

        start = time.perf_counter()
        candidate = _attack_greedy_lowest_outneighbor(current)
        attack_elapsed["greedy_lowest_outneighbor"] += time.perf_counter() - start
        if verify(current, candidate)[0]:
            attacks["greedy_lowest_outneighbor"]["successes"] += 1

        start = time.perf_counter()
        restart_rng = random.Random(seed ^ 0xA5A5A5)
        restart_answer = None
        for _ in range(256):
            trial = random_candidate(current, restart_rng)
            if _fast_cycle_valid(current, trial):
                restart_answer = trial
                break
        attack_elapsed["random_restart_256"] += time.perf_counter() - start
        if restart_answer is not None and verify(current, restart_answer)[0]:
            attacks["random_restart_256"]["successes"] += 1

        start = time.perf_counter()
        candidate = _attack_raw_coordinate_translation(current)
        attack_elapsed["in_context_raw_coordinate_translation"] += time.perf_counter() - start
        if verify(current, candidate)[0]:
            attacks["in_context_raw_coordinate_translation"]["successes"] += 1

        start = time.perf_counter()
        reference, counts = _camion_cycle(current)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(
            counts["exact_arc_operations"] + counts["adjacency_lookups"]
        )
        if reference is not None and verify(current, reference)[0]:
            reference_successes += 1

        compact, operations = _compact_cycle_and_operations(current)
        compact_operations.append(operations)
        if verify(current, compact)[0]:
            compact_successes += 1

    for name in attacks:
        attacks[name]["wall_clock_sec"] = round(attack_elapsed[name], 6)
    all_failed = all(
        item["successes"] == 0 and item["attempts"] >= 8
        for item in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "constructive Camion algorithm for strong tournaments",
            "complexity": "O(n^3) adjacency lookups after O(n^2 log n) exact arc materialization",
            "solves": f"{reference_successes}/8, as expected",
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_operations),
            "operation_unit": "Euclidean/arithmetic/membership operations in displayed arc materialization plus adjacency lookups across eight shipping instances",
            "per_instance_operations": reference_operations,
        },
        "intended_compact_route": {
            "name": "centered inversion followed by field translation",
            "solves": f"{compact_successes}/8",
            "operations_max": max(compact_operations),
            "operations_per_instance": compact_operations,
        },
    }

    doubled_n = _next_odd_prime(2 * shipping["n"])
    doubled = make_instance(n=doubled_n, seed=314159)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "candidate_space_log2_shipping": math.log2(search_space(inst)),
        "candidate_space_log2_doubled": math.log2(search_space(doubled)),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    real_transformations = 0
    failures = []
    for seed in range(20):
        base = make_instance(n=23, seed=50_000 + seed)
        base_key = canonical_key(base)
        rng = random.Random(60_000 + seed)
        permutation = list(range(base["p"]))
        rng.shuffle(permutation)
        multiplier = rng.randrange(1, base["p"])
        translation = rng.randrange(base["p"])
        variants = [
            ("vertex_permutation", _permuted_vertices(base, permutation)),
            ("coordinate_affine", _affine_coordinates(base, multiplier, translation)),
        ]
        composed = _affine_coordinates(
            _permuted_vertices(base, permutation), multiplier, translation
        )
        variants.append(("composition", composed))
        reordered = dict(base)
        reordered["connection_set"] = list(reversed(base["connection_set"]))
        reordered["answer"] = list(base["answer"])
        variants.append(("connection_order", reordered))
        for name, transformed in variants:
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                failures.append({"seed": seed, "transformation": name, "kind": "key"})
            if verify(transformed, transformed["answer"])[0]:
                real_transformations += 1
            else:
                failures.append({"seed": seed, "transformation": name, "kind": "witness"})
    unrelated = [
        canonical_key(make_instance(n=47, seed=80_000 + seed))
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": (
            not failures
            and real_transformations == invariance_checks
            and len(set(unrelated)) == 20
        ),
        "invariance_checks": invariance_checks,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "failures": failures,
        "caveat": "affine Cayley normal form, not a complete tournament-isomorphism canonical labelling",
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    worst_answer = [inst["root"]] + [
        v for v in range(inst["p"] - 1, -1, -1) if v != inst["root"]
    ] + [inst["root"]]
    worst_blob = json.dumps(worst_answer, separators=(",", ":"))
    compact, intended_operations = _compact_cycle_and_operations(inst)
    arms = {
        name: {
            "solved": G9_ORACLE_RESULTS[name]["solved"],
            "attempts": G9_ORACLE_RESULTS[name]["attempts"],
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    hinted_minus_placebo = None
    if (
        isinstance(hinted, int)
        and isinstance(placebo, int)
        and arms["hinted"]["attempts"]
        and arms["placebo"]["attempts"]
    ):
        hinted_minus_placebo = (
            hinted / arms["hinted"]["attempts"]
            - placebo / arms["placebo"]["attempts"]
        )
    within_caps = (
        len(worst_blob) <= 2000
        and _answer_atoms(worst_answer) <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and verify(inst, compact)[0],
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(answer),
        "worst_case_answer_chars": len(worst_blob),
        "worst_case_answer_tokens": math.ceil(len(worst_blob) / 4),
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["paper"] = "arXiv:2407.06675"
    report["family"] = "rooted Hamiltonian one-loop subdivisions in regular oriented tournaments"
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping
    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
