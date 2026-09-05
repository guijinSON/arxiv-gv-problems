"""Verified problem generator for arXiv:2408.12951.

The paper defines b*-colorings and proves both their general hardness and their
local witness structure.  This module inverse-generates complete multipartite
graphs whose parts are affine hyperplane sections over a prime field.  A
sampled covector induces a full b*-coloring; generation never solves an emitted
instance.
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
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "simple graph given by exact nonedge lists",
        "vertex coordinate vectors over a prime field",
        "normalized field covector inducing a b*-coloring",
    ],
    "verification_operations": [
        "finite-field dot products",
        "exact proper-coloring comparison",
        "exact neighborhood color-set comparison",
        "b-vertex and nice-vertex checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "All nonedge differences lie in one common codimension-one subspace, "
        "so one affine-independent color class determines the coloring covector; "
        "without this invariant one processes the full graph and all equations."
    ),
    "hardness_basis": (
        "Track B: complement-component recognition followed by modular Gaussian "
        "elimination is polynomial, O(N^2+Nd^2), and at the hard preset averaged "
        "9,316 field operations and about 0.0048 seconds per instance over eight seeds; one class "
        "determines the covector in 185 exact field operations."
    ),
    "max_answer_tokens": 20,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 3, "dimension": 3, "prime": 11, "class_spread": 1},
    "easy": {"n": 12, "dimension": 5, "prime": 65537, "class_spread": 2},
    "medium": {"n": 24, "dimension": 6, "prime": 1000003, "class_spread": 3},
    "hard": {"n": 34, "dimension": 6, "prime": 2147483647, "class_spread": 5},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The differences between nonadjacent vertices occupy one common "
    "codimension-one subspace of the displayed finite-field coordinates."
)
PLACEBO_HINT = (
    "The vertex identifiers and all finite-field residues require consistent "
    "bookkeeping throughout the displayed instance data."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A normalized 1-by-d covector over GF(p), serialized as a JSON list of "
        "exact integer residues [1,a1,...,a_(d-1)], with every entry in 0..p-1."
    ),
    "bounds": {
        "rows": 1,
        "max_columns": 6,
        "normalization": "first coefficient equals 1",
        "coefficient_min": 0,
        "coefficient_max": "p-1, with p at most 2^61-1 on the escalation ladder",
    },
}

NOTES = (
    "Section 1 fixes the exact certificate: a proper k-coloring has a b-vertex "
    "when its neighborhood contains every other color, and is a b*-coloring "
    "when one nice b-vertex is adjacent to a b-vertex of every other color. "
    "Section 2, Proposition 5 gives NP-completeness on co-bipartite graphs, but "
    "that worst-case result does not justify a planted-distribution Track-A "
    "claim. Propositions 6-8 instead identify the easy block-graph and cactus "
    "regimes via b*(G)=m*(G)+1, and Proposition 2 computes m* in "
    "O(n Delta); those regimes were avoided. Section 3, Proposition 11 supplies "
    "the radius-two locality of every b* witness, and Proposition 13 gives the "
    "paper's exact 0-1 model. Here inverse generation samples the normalized "
    "covector first, transforms a canonical affine configuration, and uses its "
    "level sets as the parts of a complete multipartite graph. Dense random "
    "coordinate changes remove magnitude and coordinate-axis signatures; MDS "
    "difference rows make every allowed choice of one class sufficient for the "
    "compact route. Small-coefficient, axis, one-equation, greedy and random "
    "attacks are tested; the disclosed successful reference is complement "
    "recognition plus Gaussian elimination."
)

# Filled after the script-owned hardening runs.  These are diagnostics only;
# since 2026-09-05 G9 gates the size/effort caps, not oracle success.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    if not _is_int(value) or value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value == prime:
            return True
        if value % prime == 0:
            return False
    # Deterministic Miller-Rabin for unsigned 64-bit integers.
    odd, shift = value - 1, 0
    while odd % 2 == 0:
        odd //= 2
        shift += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        witness = pow(base, odd, value)
        if witness in (1, value - 1):
            continue
        for _ in range(shift - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def _validate_parameters(n, dimension, prime, class_spread):
    if not _is_int(n) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if not _is_int(dimension) or not 3 <= dimension <= 6:
        raise ValueError("dimension must be an integer from 3 through 6")
    if not _is_prime(prime) or prime <= n + dimension + class_spread:
        raise ValueError("prime must be a prime larger than all construction indices")
    if not _is_int(class_spread) or class_spread < 0:
        raise ValueError("class_spread must be a nonnegative integer")


def _identity(size):
    return [[int(row == column) for column in range(size)] for row in range(size)]


def _random_gl(size, prime, rng):
    """An invertible dense matrix, built only with invertible row operations."""
    matrix = _identity(size)
    rounds = max(20, 8 * size)
    for _ in range(rounds):
        operation = rng.randrange(3)
        if operation == 0:
            left, right = rng.sample(range(size), 2)
            matrix[left], matrix[right] = matrix[right], matrix[left]
        elif operation == 1:
            row = rng.randrange(size)
            factor = rng.randrange(1, prime)
            matrix[row] = [factor * value % prime for value in matrix[row]]
        else:
            target, source = rng.sample(range(size), 2)
            factor = rng.randrange(1, prime)
            matrix[target] = [
                (matrix[target][column] + factor * matrix[source][column]) % prime
                for column in range(size)
            ]
    return matrix


def _row_times_matrix(row, matrix, prime):
    return [
        sum(row[index] * matrix[index][column] for index in range(len(row))) % prime
        for column in range(len(matrix[0]))
    ]


def _fresh_ids(rng, count):
    values = set()
    while len(values) < count:
        values.add(rng.randrange(100000, 1000000))
    result = list(values)
    rng.shuffle(result)
    return result


def make_instance(n, seed=0, dimension=6, prime=2147483647, class_spread=5, **params):
    """Inverse-generate a graph and a normalized covector b*-certificate."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, dimension, prime, class_spread)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # Sample the certificate before constructing any vertex or edge.
    answer = [1] + [rng.randrange(prime) for _ in range(dimension - 1)]
    # A global invertible change within the kernel makes coordinate columns dense.
    kernel_map = _random_gl(dimension - 1, prime, rng)
    translation = [rng.randrange(prime) for _ in range(dimension)]

    # Sorting makes the abstract graph determined exactly by this size multiset;
    # all remaining seed variation is a coordinate/vertex relabelling.
    class_sizes = sorted(
        dimension + rng.randrange(class_spread + 1) for _ in range(n)
    )
    canonical = []
    for class_index, class_size in enumerate(class_sizes):
        points = []
        for local_index in range(class_size):
            if local_index == 0:
                kernel_coordinates = [0] * (dimension - 1)
            else:
                t = local_index % prime
                kernel_coordinates = [pow(t, exponent, prime) for exponent in range(dimension - 1)]
            dense_kernel = _row_times_matrix(kernel_coordinates, kernel_map, prime)
            rest = [
                (dense_kernel[index] + translation[index + 1]) % prime
                for index in range(dimension - 1)
            ]
            # answer dot point == class_index + translation[0] (mod prime).
            first = (
                class_index + translation[0]
                - sum(answer[index + 1] * rest[index] for index in range(dimension - 1))
            ) % prime
            points.append([first] + rest)
        canonical.append(points)

    total_vertices = sum(class_sizes)
    identifiers = _fresh_ids(rng, total_vertices)
    classes, vertices = [], []
    cursor = 0
    for class_index, points in enumerate(canonical):
        ids = identifiers[cursor:cursor + len(points)]
        cursor += len(points)
        classes.append(ids)
        for identifier, coordinates in zip(ids, points):
            vertices.append({
                "id": identifier,
                "coordinates": coordinates,
                "nonneighbors": [other for other in ids if other != identifier],
            })
    for vertex in vertices:
        rng.shuffle(vertex["nonneighbors"])
    rng.shuffle(vertices)

    inst = {
        "paper": "arXiv:2408.12951",
        "family": "finite-field covector inducing a b*-coloring",
        "n": n,
        "dimension": dimension,
        "prime": prime,
        "class_spread": class_spread,
        "required_colors": n,
        "vertex_count": total_vertices,
        "vertices": vertices,
    }
    inst["answer"] = answer
    return inst


def _validate_instance(inst):
    cached = inst.get("_validation_cache")
    if isinstance(cached, dict):
        return cached, None
    try:
        n = inst["n"]
        dimension = inst["dimension"]
        prime = inst["prime"]
        class_spread = inst["class_spread"]
        vertices = inst["vertices"]
    except (KeyError, TypeError):
        return None, "instance is missing required graph data"
    try:
        _validate_parameters(n, dimension, prime, class_spread)
    except ValueError as error:
        return None, f"invalid instance parameters: {error}"
    if not isinstance(vertices, list) or len(vertices) != inst.get("vertex_count"):
        return None, "vertex_count does not match the vertex list"
    by_id = {}
    for row in vertices:
        if not isinstance(row, dict) or not _is_int(row.get("id")):
            return None, "every vertex needs an integer id"
        identifier = row["id"]
        if identifier in by_id:
            return None, "vertex ids must be distinct"
        coordinates = row.get("coordinates")
        if (not isinstance(coordinates, list) or len(coordinates) != dimension
                or any(not _is_int(value) or not 0 <= value < prime for value in coordinates)):
            return None, f"vertex {identifier} has malformed coordinates"
        nonneighbors = row.get("nonneighbors")
        if (not isinstance(nonneighbors, list)
                or any(not _is_int(value) for value in nonneighbors)
                or len(set(nonneighbors)) != len(nonneighbors)
                or identifier in nonneighbors):
            return None, f"vertex {identifier} has a malformed nonneighbor list"
        by_id[identifier] = row
    ids = set(by_id)
    for identifier, row in by_id.items():
        for other in row["nonneighbors"]:
            if other not in ids:
                return None, f"vertex {identifier} names an unknown nonneighbor"
            if identifier not in by_id[other]["nonneighbors"]:
                return None, "the nonneighbor relation must be symmetric"

    # Components of the nonedge graph must be cliques.  They are precisely the
    # independent parts of the represented complete multipartite graph.
    remaining, components = set(ids), []
    while remaining:
        start = next(iter(remaining))
        component = {start}
        stack = [start]
        while stack:
            current = stack.pop()
            for other in by_id[current]["nonneighbors"]:
                if other not in component:
                    component.add(other)
                    stack.append(other)
        expected = component - {start}
        for identifier in component:
            if set(by_id[identifier]["nonneighbors"]) != component - {identifier}:
                return None, "a complement component is not a clique"
        remaining -= component
        components.append(sorted(component))
    components.sort(key=lambda part: (len(part), part))
    if len(components) != n:
        return None, "the complement graph does not have required_colors components"
    if any(len(component) < dimension for component in components):
        return None, "every independent part must have at least dimension vertices"
    data = {"by_id": by_id, "components": components}
    try:
        inst["_validation_cache"] = data
    except TypeError:
        pass
    return data, None


def _decode_candidate(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    dimension, prime = inst["dimension"], inst["prime"]
    if len(answer) != dimension:
        return None, f"answer must contain exactly {dimension} coefficients"
    for index, value in enumerate(answer):
        if not _is_int(value):
            return None, f"coefficient {index} is not an integer"
        if not 0 <= value < prime:
            return None, f"coefficient {index} is outside 0..{prime - 1}"
    if answer[0] != 1:
        return None, "the normalization coefficient w[0] must equal 1"
    return answer, None


def verify(inst, answer):
    """Check the induced coloring and the b*/nice-vertex conditions exactly."""
    data, error = _validate_instance(inst)
    if error is not None:
        return False, error
    covector, error = _decode_candidate(inst, answer)
    if error is not None:
        return False, error
    prime = inst["prime"]
    values, component_values = {}, []
    for component_index, component in enumerate(data["components"]):
        first_id = component[0]
        first_value = sum(
            coefficient * coordinate for coefficient, coordinate in
            zip(covector, data["by_id"][first_id]["coordinates"])
        ) % prime
        values[first_id] = first_value
        for identifier in component[1:]:
            value = sum(
                coefficient * coordinate for coefficient, coordinate in
                zip(covector, data["by_id"][identifier]["coordinates"])
            ) % prime
            if value != first_value:
                return False, (
                    f"nonedge component {component_index} is split: vertices "
                    f"{component[0]} and {identifier} receive different residues"
                )
            values[identifier] = value
        component_values.append(first_value)
    if len(set(component_values)) != inst["required_colors"]:
        return False, "two adjacent independent parts receive the same residue"

    # Execute the paper's definition, rather than accepting the linear equations
    # alone. Residues are renamed by increasing order to colors 1..k.
    palette = {value: index + 1 for index, value in enumerate(sorted(component_values))}
    colors = {identifier: palette[value] for identifier, value in values.items()}
    all_colors = set(range(1, inst["required_colors"] + 1))
    b_vertices = set()
    ids = set(data["by_id"])
    for identifier, row in data["by_id"].items():
        neighbors = ids - {identifier} - set(row["nonneighbors"])
        neighbor_colors = {colors[other] for other in neighbors}
        if colors[identifier] in neighbor_colors:
            return False, f"induced coloring is not proper at vertex {identifier}"
        if neighbor_colors == all_colors - {colors[identifier]}:
            b_vertices.add(identifier)
    for identifier, row in data["by_id"].items():
        if identifier not in b_vertices:
            continue
        b_neighbor_colors = {
            colors[other] for other in b_vertices
            if other != identifier and other not in row["nonneighbors"]
        }
        if b_neighbor_colors == all_colors - {colors[identifier]}:
            return True, "ok"
    return False, "the induced proper coloring has no nice b-vertex"


def render(inst):
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    lines = [
        "Finite-field b*-coloring certificate",
        "",
        f"Let p = {inst['prime']} (a prime), d = {inst['dimension']}, and k = {inst['required_colors']}.",
        "All arithmetic on coordinates and residues is modulo p, represented by integers 0 through p-1.",
        "The undirected simple graph has the vertex rows below. Distinct vertices are nonadjacent exactly",
        "when either one lists the other after the vertical bar; every other distinct pair is an edge.",
        "Vertex identifiers are arbitrary integers. Each row is:",
        "    id : x[0],x[1],...,x[d-1] | comma-separated nonneighbor ids",
        "",
        "A candidate is a normalized covector w=[w[0],...,w[d-1]] in GF(p)^d with w[0]=1.",
        "It gives vertex v the residue r(v)=sum_j w[j]*x_v[j] mod p. There must be exactly k",
        "distinct residues. Rename those residues in increasing numeric order as colors 1,...,k.",
        "",
        "A coloring is proper when adjacent vertices have different colors. A vertex of color i is a",
        "b-vertex when its neighbors contain every color other than i. A b-vertex is nice when it is",
        "adjacent to a b-vertex of every other color. Find a normalized covector whose induced coloring",
        "is proper and has a nice vertex; this is a b*-coloring in the sense of the paper.",
        "",
        "VERTICES",
    ]
    for row in inst["vertices"]:
        coords = ",".join(str(value) for value in row["coordinates"])
        nonneighbors = ",".join(str(value) for value in row["nonneighbors"])
        lines.append(f"{row['id']} : {coords} | {nonneighbors}")
    lines.extend([
        "END VERTICES",
        "",
        f"Give your final answer inside <answer></answer> tags as one JSON list of exactly {inst['dimension']}",
        f"integer residues in 0..{inst['prime'] - 1}, with first entry 1.",
        "Example shape: <answer>[" + ", ".join(["1"] + ["0"] * (inst["dimension"] - 1))
        + "]</answer> (this illustrates syntax only, not the solution).",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the tagged JSON covector, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if match is None:
        return None
    body = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json|text)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence is not None:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(not _is_int(item) for item in value):
        return None
    return value


def random_candidate(inst, rng):
    """Uniformly sample the normalized projective covectors stated to the solver."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [1] + [rng.randrange(inst["prime"]) for _ in range(inst["dimension"] - 1)]


def search_space(inst):
    return inst["prime"] ** (inst["dimension"] - 1)


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    count = 0
    for tail in itertools.product(range(inst["prime"]), repeat=inst["dimension"] - 1):
        count += int(verify(inst, [1] + list(tail))[0])
    return count


def canonical_key(inst):
    """Canonical graph key: a complete multipartite graph is fixed by part sizes."""
    data, error = _validate_instance(inst)
    if error is not None:
        return "invalid:" + error
    payload = [
        inst["prime"],
        inst["dimension"],
        sorted(len(component) for component in data["components"]),
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    """Increase field entropy and graph crowding without lengthening the covector."""
    current = dict(params)
    primes = [65537, 1000003, 2147483647, 4294967291, 2305843009213693951]
    prime = current.get("prime", 2147483647)
    next_prime = next((candidate for candidate in primes if candidate > prime), None)
    if next_prime is None:
        if current.get("n", 2) >= 160 and current.get("class_spread", 0) >= 12:
            return None
        current["n"] = min(160, max(current.get("n", 2) + 16,
                                      current.get("n", 2) * 5 // 4))
        current["class_spread"] = min(12, current.get("class_spread", 0) + 1)
        return current
    current["prime"] = next_prime
    current["n"] = min(160, max(current.get("n", 2) + 8,
                                  current.get("n", 2) * 5 // 4))
    current["class_spread"] = min(12, current.get("class_spread", 0) + 1)
    return current


def _equation_rows(inst, first_component_only=False):
    cache_name = "_first_equation_rows" if first_component_only else "_all_equation_rows"
    cached = inst.get(cache_name)
    if isinstance(cached, list):
        return cached
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    components = data["components"][:1] if first_component_only else data["components"]
    rows = []
    for component in components:
        base = data["by_id"][component[0]]["coordinates"]
        choices = component[1:inst["dimension"]] if first_component_only else component[1:]
        for identifier in choices:
            point = data["by_id"][identifier]["coordinates"]
            rows.append([(point[index] - base[index]) % inst["prime"]
                         for index in range(inst["dimension"])])
    inst[cache_name] = rows
    return rows


def _solve_normalized(rows, dimension, prime):
    """Solve row dot [1,a...] = 0; return (answer or None, counters)."""
    matrix = [[row[column] % prime for column in range(1, dimension)] + [(-row[0]) % prime]
              for row in rows]
    rank, operations, inversions, pivot_scans = 0, 0, 0, 0
    variables = dimension - 1
    for column in range(variables):
        pivot = None
        for row_index in range(rank, len(matrix)):
            pivot_scans += 1
            if matrix[row_index][column] % prime:
                pivot = row_index
                break
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        inverse = pow(matrix[rank][column], prime - 2, prime)
        inversions += 1
        for entry in range(column, variables + 1):
            matrix[rank][entry] = matrix[rank][entry] * inverse % prime
            operations += 1
        for row_index in range(len(matrix)):
            if row_index == rank:
                continue
            factor = matrix[row_index][column] % prime
            if factor:
                for entry in range(column, variables + 1):
                    matrix[row_index][entry] = (
                        matrix[row_index][entry] - factor * matrix[rank][entry]
                    ) % prime
                    operations += 2
        rank += 1
        if rank == variables:
            break
    stats = {
        "rows": len(rows),
        "rank": rank,
        "field_operations": operations + inversions,
        "multiplications_or_subtractions": operations,
        "inversions": inversions,
        "pivot_tests": pivot_scans,
    }
    if rank != variables:
        return None, stats
    solution = [0] * variables
    for row_index in range(rank):
        pivot = next((column for column in range(variables)
                      if matrix[row_index][column] == 1
                      and all(matrix[other][column] == 0 for other in range(rank)
                              if other != row_index)), None)
        if pivot is not None:
            solution[pivot] = matrix[row_index][-1]
    candidate = [1] + solution
    # All rows, including those not used as pivots, must agree.
    if any(sum(coefficient * value for coefficient, value in zip(row, candidate)) % prime
           for row in rows):
        return None, stats
    return candidate, stats


def _reference_algorithm(inst):
    rows = _equation_rows(inst, first_component_only=False)
    return _solve_normalized(rows, inst["dimension"], inst["prime"])


def _compact_route(inst):
    rows = _equation_rows(inst, first_component_only=True)
    return _solve_normalized(rows, inst["dimension"], inst["prime"])


def _residual_score(inst, candidate, limit=None):
    rows = _equation_rows(inst, first_component_only=False)
    if limit is not None:
        rows = rows[:limit]
    prime = inst["prime"]
    return sum(bool(sum(a * b for a, b in zip(row, candidate)) % prime) for row in rows)


def _attack_axis(inst, _rng):
    return [1] + [0] * (inst["dimension"] - 1)


def _attack_small_coefficients(inst, _rng):
    prime = inst["prime"]
    best = None
    for tail in itertools.product((-1, 0, 1), repeat=inst["dimension"] - 1):
        candidate = [1] + [value % prime for value in tail]
        scored = (_residual_score(inst, candidate, limit=32), candidate)
        if best is None or scored[0] < best[0]:
            best = scored
    return best[1]


def _attack_greedy(inst, _rng):
    prime = inst["prime"]
    candidate = [1] + [0] * (inst["dimension"] - 1)
    score = _residual_score(inst, candidate, limit=64)
    for index in range(1, inst["dimension"]):
        options = []
        for delta in (-1, 1):
            trial = list(candidate)
            trial[index] = delta % prime
            options.append((_residual_score(inst, trial, limit=64), trial))
        trial_score, trial = min(options, key=lambda row: row[0])
        if trial_score < score:
            score, candidate = trial_score, trial
    return candidate


def _attack_single_equation(inst, _rng):
    row = _equation_rows(inst, first_component_only=True)[0]
    prime, dimension = inst["prime"], inst["dimension"]
    candidate = [1] + [0] * (dimension - 1)
    pivot = next((index for index in range(1, dimension) if row[index]), None)
    if pivot is not None:
        candidate[pivot] = (-row[0]) * pow(row[pivot], prime - 2, prime) % prime
    return candidate


def _attack_random_restart(inst, rng, attempts=8192):
    first = random_candidate(inst, rng)
    if verify(inst, first)[0]:
        return first
    for _ in range(attempts - 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return first


def _mat_inverse(matrix, prime):
    size = len(matrix)
    augmented = [list(row) + identity for row, identity in zip(matrix, _identity(size))]
    for column in range(size):
        pivot = next((row for row in range(column, size) if augmented[row][column] % prime), None)
        if pivot is None:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        inverse = pow(augmented[column][column], prime - 2, prime)
        augmented[column] = [value * inverse % prime for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                (augmented[row][entry] - factor * augmented[column][entry]) % prime
                for entry in range(2 * size)
            ]
    return [row[size:] for row in augmented]


def _relabel_instance(inst, seed):
    rng = random.Random(seed)
    transformed = {key: value for key, value in inst.items()
                   if key not in ("vertices", "answer", "_validation_cache")}
    old_ids = [row["id"] for row in inst["vertices"]]
    new_ids = _fresh_ids(rng, len(old_ids))
    mapping = dict(zip(old_ids, new_ids))
    vertices = []
    for row in inst["vertices"]:
        vertices.append({
            "id": mapping[row["id"]],
            "coordinates": list(row["coordinates"]),
            "nonneighbors": [mapping[value] for value in row["nonneighbors"]],
        })
    for row in vertices:
        rng.shuffle(row["nonneighbors"])
    rng.shuffle(vertices)
    transformed["vertices"] = vertices
    transformed["answer"] = list(inst["answer"])
    return transformed


def _affine_instance(inst, seed):
    rng = random.Random(seed)
    prime, dimension = inst["prime"], inst["dimension"]
    answer = list(inst["answer"])
    while True:
        matrix = _random_gl(dimension, prime, rng)
        inverse = _mat_inverse(matrix, prime)
        # Coordinates are row vectors y=xM, so covectors transform as
        # w' = w M^{-T}, not as w M^{-1}.
        inverse_transpose = [list(row) for row in zip(*inverse)]
        carried = _row_times_matrix(answer, inverse_transpose, prime)
        if carried[0] != 0:
            break
    scale = pow(carried[0], prime - 2, prime)
    carried = [value * scale % prime for value in carried]
    shift = [rng.randrange(prime) for _ in range(dimension)]
    transformed = {key: value for key, value in inst.items()
                   if key not in ("vertices", "answer", "_validation_cache")}
    transformed["vertices"] = [{
        "id": row["id"],
        "coordinates": [
            (value + shift[index]) % prime
            for index, value in enumerate(_row_times_matrix(row["coordinates"], matrix, prime))
        ],
        "nonneighbors": list(row["nonneighbors"]),
    } for row in inst["vertices"]]
    transformed["answer"] = carried
    return transformed


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    return len(compact), (len(compact) + 3) // 4


def selftest():
    report = {
        "paper": "arXiv:2408.12951",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures, attempts = [], 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
        "construction": "sample covector first; build all graph parts as its affine level sets",
    }

    shipping = make_instance(seed=240812951, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    swap_index = next(index for index in range(1, len(planted)) if planted[index] != 1)
    swapped = list(planted)
    swapped[0], swapped[swap_index] = swapped[swap_index], swapped[0]
    duplicate = list(planted)
    duplicate[-1] = duplicate[-2]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": swapped,
        "duplicate_one": duplicate,
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["prime"]],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values()) and len(reasons) == len(cases),
        "cases": cases, "distinct_reasons": len(reasons),
    }

    realistic = (
        "The common annihilator gives the following normalized row.\n"
        "<answer>\n```json\n" + json.dumps(planted) + "\n```\n</answer>\n"
        "I used residues modulo the displayed prime."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    guess_rng, guess_total, guess_hits = random.Random(0x240812951), 200_000, 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform among all normalized projective covectors w[0]=1",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "coordinate_axis_outlier": _attack_axis,
        "small_coefficient_ansatz": _attack_small_coefficients,
        "one_pass_greedy": _attack_greedy,
        "single_nonedge_equation": _attack_single_equation,
        "random_restart_8192": lambda inst, rng: _attack_random_restart(inst, rng, 8192),
    }
    attack_results = {name: {"successes": 0, "attempts": 0} for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            start = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - start
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
    for name, elapsed in attack_elapsed.items():
        attack_results[name]["wall_clock_sec_total_8"] = round(elapsed, 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())

    reference_successes = compact_successes = 0
    reference_elapsed = compact_elapsed = 0.0
    reference_ops, compact_ops, reference_rows = [], [], []
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        start = time.perf_counter()
        candidate, stats = _reference_algorithm(inst)
        reference_elapsed += time.perf_counter() - start
        reference_ops.append(stats["field_operations"])
        reference_rows.append(stats["rows"])
        if candidate is not None:
            reference_successes += int(verify(inst, candidate)[0])
        start = time.perf_counter()
        candidate, stats = _compact_route(inst)
        compact_elapsed += time.perf_counter() - start
        compact_ops.append(stats["field_operations"])
        if candidate is not None:
            compact_successes += int(verify(inst, candidate)[0])
    reference = {
        "name": "complement-component recognition plus modular Gaussian elimination",
        "complexity": "O(N^2 + N*d^2) exact field operations",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(reference_ops) // len(reference_ops),
        "operations_min": min(reference_ops),
        "operations_max": max(reference_ops),
        "equation_rows_mean": sum(reference_rows) / len(reference_rows),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = max(compact_ops)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == compact_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "solve the d-1 differences from one affine-independent nonedge class",
            "wall_clock_sec_total_8": round(compact_elapsed, 6),
            "field_operations_max": intended_operations,
            "field_operations_mean": sum(compact_ops) / len(compact_ops),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_failed,
        "exact_valid_answers": 1,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": guess_hits / guess_total,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "attack_candidate_trials_total_8": 8192 * len(attack_seeds),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    larger_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    larger_params["n"] *= 2
    larger = make_instance(seed=707, **larger_params)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and larger["vertex_count"] > shipping["vertex_count"],
        "shipping_n": shipping["n"],
        "doubled_n": larger["n"],
        "shipping_vertices": shipping["vertex_count"],
        "doubled_vertices": larger["vertex_count"],
        "verify_reason": larger_reason,
    }

    key_failures, invariance_checks, carried_checks = [], 0, 0
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        variants = [
            _relabel_instance(inst, 12000 + seed),
            _affine_instance(inst, 14000 + seed),
        ]
        variants.append(_relabel_instance(variants[1], 16000 + seed))
        for variant_index, transformed in enumerate(variants):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "variant": variant_index, "reason": "key changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": seed, "variant": variant_index,
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
            "vertex renumbering and input/list reordering",
            "invertible affine coordinate change with projectively normalized carried covector",
            "composition of coordinate change and vertex relabelling",
        ],
        "canonical_form": "prime, dimension, and sorted complete-multipartite part sizes",
    }

    answer_chars, answer_tokens = _json_answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and len(shipping["answer"]) <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(shipping["answer"]),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
