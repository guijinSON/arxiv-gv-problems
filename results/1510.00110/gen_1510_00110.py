"""Verified Track-B generator from Construction I of arXiv:1510.00110.

The paper constructs a directed strongly regular graph on G x G x Z_m.
Here G is the cyclic group Z_q.  An instance asks for a small submatrix of
the square of the graph's adjacency matrix: each requested entry is the exact
number of directed two-step paths between two displayed vertices.

The displayed coordinates are carried through long affine recurrence chains.
Generation knows their decoded values and the Construction-I path counts by
construction.  Verification independently executes every displayed recurrence
and applies the exact case count; it never reads ``inst["answer"]``.
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
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "directed graph on cyclic-group product coordinates",
        "adjacency matrix over the integers",
        "finite submatrix of the squared adjacency matrix",
    ],
    "verification_operations": [
        "exact modular affine recurrence evaluation",
        "exact directed-adjacency classification",
        "exact integer two-step path count comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The affine potential a[r]z[r]+b[r] is unchanged along each public "
        "coordinate recurrence, collapsing a long decoder to its two endpoints; "
        "without this invariant every displayed stage must be executed."
    ),
    "hardness_basis": (
        "Track B: Section 3, Theorem 3.1 (Construction I) gives the exact "
        "two-step counts, while direct evaluation of the public affine chains "
        "takes O(n*s) modular operations; at the shipping preset the reference "
        "algorithm uses 18,510 counted operations (wall-clock measured in "
        "selftest at about 0.0007 seconds), versus 222 exact operations after "
        "recognizing the invariant, "
        "so the efficient mechanical route is not executable by hand."
    ),
    "max_answer_tokens": 105,
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


_MODULI = {
    "toy": (5, 3),
    "p31": (1_000_000_007, 1_000_000_009),
    "p61": (2**61 - 1, 2**61 - 1),
    "p127": (2**127 - 1, 2**127 - 1),
}

DIFFICULTY = {
    "demo": {"n": 1, "side": 2, "moduli": "toy"},
    "easy": {"n": 128, "side": 6, "moduli": "p31"},
    "medium": {"n": 256, "side": 6, "moduli": "p61"},
    "hard": {"n": 512, "side": 6, "moduli": "p127"},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "In each displayed recurrence, the affine potential a[r]*z[r]+b[r] is "
    "invariant under the step index."
)
PLACEBO_HINT = (
    "In each displayed recurrence, every arithmetic result is represented by "
    "its canonical modular residue."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly the key counts, whose value is a side-by-side "
        "integer matrix; every entry is in the inclusive range 0,...,K, where K "
        "is the stated common in/out-degree."
    ),
    "bounds": {
        "rows": "side",
        "columns": "side",
        "entry_min": 0,
        "entry_max": "K",
        "candidate_count": "(K+1)^(side^2)",
    },
}

NOTES = (
    "Section 2 fixes a directed strongly regular graph by the exact identities "
    "A^2=tI+lambda*A+mu*(J-I-A) and AJ=JA=kJ.  Section 3, Theorem 3.1 "
    "(Construction I) fixes the native vertex set G x G x Z_m, its four "
    "adjacency cases, and the parameters (m q^2, m q+q-2, 2q+m-3, "
    "q+m-3, m+1).  The theorem's explicit formula rules out Track A but enables "
    "Track B.  Instances carry the graph through a bijective affine coordinate "
    "change whose recurrence satisfies a[r+1]z[r+1]+b[r+1]="
    "a[r]z[r]+b[r].  Generation encodes already chosen Construction-I vertices "
    "and uses the theorem's case certificate; it performs no path search.  "
    "Uniform random potentials conceal coordinate magnitude and position.  The "
    "audited attacks cover raw-coordinate outliers, a constant-mode guess, raw "
    "greedy adjacency, a one-step decoder ansatz, and random restarts."
)

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _make_chain(modulus, length, rng):
    """Sample public potentials for a bijective affine recurrence."""
    a = [rng.randrange(1, modulus) for _ in range(length + 1)]
    a_inverse = [pow(value, -1, modulus) for value in a]
    b = [rng.randrange(modulus) for _ in range(length + 1)]
    return {"a": a, "a_inverse": a_inverse, "b": b}


def _decode_scalar_direct(value, chain, modulus):
    """Execute every public recurrence stage, the Track-B reference route."""
    a = chain["a"]
    inv = chain["a_inverse"]
    b = chain["b"]
    current = value
    for r in range(len(a) - 1):
        current = (
            inv[r + 1] * (a[r] * current + b[r] - b[r + 1])
        ) % modulus
    return current


def _decode_scalar_compact(value, chain, modulus):
    """Use the invariant a[r]z[r]+b[r], inspecting endpoints only."""
    return (
        chain["a_inverse"][-1]
        * (chain["a"][0] * value + chain["b"][0] - chain["b"][-1])
    ) % modulus


def _encode_scalar(decoded, chain, modulus):
    """Inverse of the full recurrence, using its endpoint invariant."""
    return (
        chain["a_inverse"][0]
        * (chain["a"][-1] * decoded + chain["b"][-1] - chain["b"][0])
    ) % modulus


def _decode_vertex(vertex, inst, compact=False):
    decoder = _decode_scalar_compact if compact else _decode_scalar_direct
    q, m = inst["group_order"], inst["layer_order"]
    group_chain, layer_chain = inst["group_chain"], inst["layer_chain"]
    return (
        decoder(vertex[0], group_chain, q),
        decoder(vertex[1], group_chain, q),
        decoder(vertex[2], layer_chain, m),
    )


def _encode_vertex(vertex, inst):
    q, m = inst["group_order"], inst["layer_order"]
    return [
        _encode_scalar(vertex[0], inst["group_chain"], q),
        _encode_scalar(vertex[1], inst["group_chain"], q),
        _encode_scalar(vertex[2], inst["layer_chain"], m),
    ]


def _adjacent_decoded(source, target, q, m):
    """The four adjacency cases of Construction I, in additive notation."""
    x, y, i = source
    u, v, j = target
    if i == j:
        return (x == u and y != v) or (y == v and x != u)
    delta = (j - i) % m
    half = (m - 1) // 2
    product = (x + y) % q
    if 1 <= delta <= half:
        return u == product
    return v == product


def _parameters(q, m):
    return {
        "v": m * q * q,
        "k": m * q + q - 2,
        "t": 2 * q + m - 3,
        "lambda": q + m - 3,
        "mu": m + 1,
    }


def _count_for_pair(source, target, q, m):
    params = _parameters(q, m)
    if source == target:
        return params["t"]
    if _adjacent_decoded(source, target, q, m):
        return params["lambda"]
    return params["mu"]


def _answer_from_decoded(rows, columns, q, m):
    return {
        "counts": [
            [_count_for_pair(row, column, q, m) for column in columns]
            for row in rows
        ]
    }


def _distinct_random_vertices(count, q, m, rng):
    values = []
    seen = set()
    while len(values) < count:
        vertex = (rng.randrange(q), rng.randrange(q), rng.randrange(m))
        if vertex not in seen:
            seen.add(vertex)
            values.append(vertex)
    return values


def _different(value, modulus, rng):
    candidate = rng.randrange(modulus - 1)
    return candidate + (candidate >= value)


def _build_queries(side, q, m, rng):
    """Construct uniformly marginal rows/columns with every path-count case."""
    rows = _distinct_random_vertices(side, q, m, rng)
    columns = []
    for index, row in enumerate(rows):
        x, y, layer = row
        mode = index % 6
        if mode == 0:
            column = row
        elif mode == 1:
            delta = rng.randrange(1, (m + 1) // 2)
            column = ((x + y) % q, rng.randrange(q), (layer + delta) % m)
        elif mode == 2:
            delta = rng.randrange(1, (m + 1) // 2)
            column = (rng.randrange(q), (x + y) % q, (layer - delta) % m)
        elif mode == 3:
            column = (x, _different(y, q, rng), layer)
        elif mode == 4:
            column = (_different(x, q, rng), y, layer)
        else:
            column = (_different(x, q, rng), _different(y, q, rng), layer)
        # A collision is extraordinarily unlikely outside the demo.  Resolve it
        # by a structure-preserving change within the intended case.
        while column in columns:
            if mode == 0:
                forbidden = set(rows) | set(columns)
                replacement = _distinct_random_vertices(1, q, m, rng)[0]
                while replacement in forbidden:
                    replacement = _distinct_random_vertices(1, q, m, rng)[0]
                rows[index] = replacement
                x, y, layer = replacement
                column = replacement
            elif mode in (1, 2):
                free = rng.randrange(q)
                column = (
                    ((x + y) % q, free, column[2])
                    if mode == 1
                    else (free, (x + y) % q, column[2])
                )
            elif mode == 3:
                column = (x, _different(y, q, rng), layer)
            elif mode == 4:
                column = (_different(x, q, rng), y, layer)
            else:
                column = (_different(x, q, rng), _different(y, q, rng), layer)
        columns.append(column)

    # Conceal which row was used to construct which column.
    rng.shuffle(rows)
    rng.shuffle(columns)
    return rows, columns


def _validate_make_parameters(n, side, moduli):
    if not _is_int(n) or n < 1:
        raise ValueError("n must be a positive recurrence length")
    if not _is_int(side) or side < 2 or side > 15:
        raise ValueError("side must be an integer in 2,...,15")
    if moduli not in _MODULI:
        raise ValueError("unknown modulus preset")
    q, m = _MODULI[moduli]
    if q < 2 or m < 3 or m % 2 == 0:
        raise ValueError("Construction I requires q>=2 and odd m>=3")


def make_instance(n, seed=0, side=6, moduli="p31") -> dict:
    """Build an encoded Construction-I path-count instance by construction.

    The decoded query vertices are sampled first.  Columns are assembled in the
    diagonal, forward-edge, backward-edge, same-coordinate-edge, and non-edge
    cases.  The theorem supplies their two-step counts.  Finally the known
    vertices are inverse-mapped through sampled bijective recurrences.  No path
    search or certificate-solving algorithm is run.
    """
    _validate_make_parameters(n, side, moduli)
    q, m = _MODULI[moduli]
    rng = random.Random(seed)
    group_chain = _make_chain(q, n, rng)
    layer_chain = _make_chain(m, n, rng)
    decoded_rows, decoded_columns = _build_queries(side, q, m, rng)
    shell = {
        "size": n,
        "side": side,
        "moduli": moduli,
        "group_order": q,
        "layer_order": m,
        "group_chain": group_chain,
        "layer_chain": layer_chain,
    }
    rows = [_encode_vertex(vertex, shell) for vertex in decoded_rows]
    columns = [_encode_vertex(vertex, shell) for vertex in decoded_columns]
    params = _parameters(q, m)
    shell.update(
        {
            "vertex_count": params["v"],
            "degree_bound": params["k"],
            "rows": rows,
            "columns": columns,
            "answer": _answer_from_decoded(decoded_rows, decoded_columns, q, m),
        }
    )
    return shell


def _format_sequence(name, values, width=6):
    lines = []
    for start in range(0, len(values), width):
        chunk = " ".join(str(value) for value in values[start : start + width])
        lines.append(f"  {name}[{start}:{min(start + width, len(values))}] = {chunk}")
    return "\n".join(lines)


def _format_vertices(name, vertices):
    return "\n".join(
        f"  {name}[{index}] = ({vertex[0]}, {vertex[1]}, {vertex[2]})"
        for index, vertex in enumerate(vertices)
    )


def render(inst) -> str:
    """Render a complete, self-contained exact graph problem."""
    q = inst["group_order"]
    m = inst["layer_order"]
    length = inst["size"]
    side = inst["side"]
    group = inst["group_chain"]
    layer = inst["layer_chain"]
    zero_matrix = [[0 for _ in range(side)] for _ in range(side)]
    sections = [
        "Compute exact two-step path counts in a directed graph.\n",
        (
            f"The graph has V = Z_{q} x Z_{q} x Z_{m}.  Z_s means the integers "
            "0,...,s-1 with addition and multiplication reduced modulo s.  A "
            "displayed vertex is a triple (A,B,C) in these ranges.\n"
        ),
        (
            f"Coordinates are decoded by two public affine recurrences of length "
            f"L={length}.  For a displayed group coordinate z[0] in Z_{q}, use "
            "the arrays ga, gainv, gb below and compute, for r=0,...,L-1,\n\n"
            "  z[r+1] = gainv[r+1] * (ga[r]*z[r] + gb[r] - gb[r+1]) mod q.\n\n"
            "Each gainv[r] is the multiplicative inverse of ga[r] modulo q."
        ),
        _format_sequence("ga", group["a"]),
        _format_sequence("gainv", group["a_inverse"]),
        _format_sequence("gb", group["b"]),
        (
            f"For the displayed layer coordinate z[0] in Z_{m}, use ma, mainv, "
            "mb in the identical recurrence, reducing modulo m instead of q."
        ),
        _format_sequence("ma", layer["a"]),
        _format_sequence("mainv", layer["a_inverse"]),
        _format_sequence("mb", layer["b"]),
        (
            "Decode (A,B,C) as (x,y,i) by running the group recurrence on A and "
            "B separately and the layer recurrence on C.  All intervals below "
            "are inclusive.  Put h=(m-1)/2.  There is a directed edge\n\n"
            "  (x,y,i) -> (u,v,j)\n\n"
            "if and only if at least one of these four conditions holds:\n"
            "  1. i=j, x=u, and y!=v;\n"
            "  2. i=j, y=v, and x!=u;\n"
            "  3. delta=(j-i) mod m lies in 1,...,h and u=(x+y) mod q;\n"
            "  4. delta lies in h+1,...,m-1 and v=(x+y) mod q.\n"
            "Thus loops are absent.  Every vertex has the same out-degree and "
            f"in-degree K={inst['degree_bound']}."
        ),
        (
            f"The following ordered row and column lists each contain {side} "
            "distinct displayed vertices."
        ),
        _format_vertices("R", inst["rows"]),
        _format_vertices("C", inst["columns"]),
        (
            f"Return the {side}-by-{side} integer matrix W in this exact order, "
            "where W[p][q] is the number of displayed vertices X in all of V "
            "such that R[p] -> X and X -> C[q].  Every entry is an integer in "
            "the inclusive range 0,...,K.  Matrix row and column order matters; "
            "no row or entry may be omitted.\n"
        ),
        (
            "Give your final answer inside <answer></answer> tags, as exactly one "
            "JSON object with the sole key \"counts\" and a rectangular integer "
            f"matrix value.\nExample: <answer>{json.dumps({'counts': zero_matrix}, separators=(',', ':'))}"
            "</answer>\nOutput nothing else inside the tags."
        ),
    ]
    statement = "\n\n".join(sections)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse tagged JSON through surrounding prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    bodies = matches if matches else [text]
    for body in reversed(bodies):
        cleaned = body.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.I | re.S)
        if fence:
            cleaned = fence.group(1).strip()
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _reference_answer(inst):
    rows = [_decode_vertex(vertex, inst, compact=False) for vertex in inst["rows"]]
    columns = [
        _decode_vertex(vertex, inst, compact=False) for vertex in inst["columns"]
    ]
    return _answer_from_decoded(
        rows, columns, inst["group_order"], inst["layer_order"]
    )


def _compact_answer(inst):
    rows = [_decode_vertex(vertex, inst, compact=True) for vertex in inst["rows"]]
    columns = [
        _decode_vertex(vertex, inst, compact=True) for vertex in inst["columns"]
    ]
    return _answer_from_decoded(
        rows, columns, inst["group_order"], inst["layer_order"]
    )


def verify(inst, answer):
    """Check any candidate exactly, without consulting the planted answer."""
    if not isinstance(answer, dict) or set(answer) != {"counts"}:
        return False, "answer must be an object with exactly the key counts"
    matrix = answer["counts"]
    side = inst["side"]
    if not isinstance(matrix, list) or len(matrix) != side:
        return False, f"counts must contain exactly {side} rows"
    for row_index, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != side:
            return False, f"row {row_index} must contain exactly {side} entries"
    bound = inst["degree_bound"]
    for row in matrix:
        for value in row:
            if not _is_int(value) or not 0 <= value <= bound:
                return False, f"every entry must be an integer in 0,...,{bound}"

    expected = _reference_answer(inst)["counts"]
    for row_index in range(side):
        for column_index in range(side):
            if matrix[row_index][column_index] != expected[row_index][column_index]:
                return (
                    False,
                    f"entry ({row_index},{column_index}) is not the exact two-step count",
                )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the stated bounded matrix language."""
    side = inst["side"]
    bound = inst["degree_bound"]
    return {
        "counts": [
            [rng.randrange(bound + 1) for _ in range(side)] for _ in range(side)
        ]
    }


def search_space(inst):
    return pow(inst["degree_bound"] + 1, inst["side"] * inst["side"])


def enumerate_all(inst):
    """Brute-force the bounded language only when it contains <=250,000 items."""
    space = search_space(inst)
    if space > 250_000:
        return None
    side = inst["side"]
    bound = inst["degree_bound"]
    target = tuple(value for row in _reference_answer(inst)["counts"] for value in row)
    count = 0
    for candidate in itertools.product(range(bound + 1), repeat=side * side):
        count += int(candidate == target)
    return count


def _canonical_decoded(inst):
    rows = [_decode_vertex(vertex, inst, compact=True) for vertex in inst["rows"]]
    columns = [
        _decode_vertex(vertex, inst, compact=True) for vertex in inst["columns"]
    ]
    q, m = inst["group_order"], inst["layer_order"]
    best = None
    for reflected in (False, True):
        if reflected:
            base_rows = [(y, x, (-layer) % m) for x, y, layer in rows]
            base_columns = [(y, x, (-layer) % m) for x, y, layer in columns]
        else:
            base_rows = list(rows)
            base_columns = list(columns)
        all_vertices = base_rows + base_columns
        group_anchors = {1}
        layer_anchors = {0}
        for x, y, layer in all_vertices:
            if x:
                group_anchors.add(pow(x, -1, q))
            if y:
                group_anchors.add(pow(y, -1, q))
            layer_anchors.add((-layer) % m)
        for multiplier in group_anchors:
            for shift in layer_anchors:
                norm_rows = tuple(
                    sorted(
                        (
                            (multiplier * x) % q,
                            (multiplier * y) % q,
                            (layer + shift) % m,
                        )
                        for x, y, layer in base_rows
                    )
                )
                norm_columns = tuple(
                    sorted(
                        (
                            (multiplier * x) % q,
                            (multiplier * y) % q,
                            (layer + shift) % m,
                        )
                        for x, y, layer in base_columns
                    )
                )
                candidate = (q, m, norm_rows, norm_columns)
                if best is None or candidate < best:
                    best = candidate
    return best


def canonical_key(inst):
    """Canonicalize input order, encoder labels, and known graph symmetries."""
    canonical = _canonical_decoded(inst)
    blob = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """Lengthen the public recurrence while leaving the 6x6 certificate fixed."""
    harder = dict(params)
    current = int(harder.get("n", 0))
    if current < 1:
        return None
    harder["n"] = current * 2
    # Keep turning a fixed-answer-length axis.  The certificate never approaches
    # the cap, so this family has no answer-format ``cap_bound`` at these moduli.
    return harder


def _raw_affine_relabel(inst, group_u, group_t, layer_u, layer_t):
    """Relabel displayed coordinates and adjust the first potential."""
    out = json.loads(json.dumps(inst))

    def adjust(chain, modulus, u, shift):
        u_inverse = pow(u, -1, modulus)
        old_a0 = chain["a"][0]
        new_a0 = old_a0 * u_inverse % modulus
        chain["a"][0] = new_a0
        chain["a_inverse"][0] = pow(new_a0, -1, modulus)
        chain["b"][0] = (chain["b"][0] - new_a0 * shift) % modulus

    adjust(out["group_chain"], out["group_order"], group_u, group_t)
    adjust(out["layer_chain"], out["layer_order"], layer_u, layer_t)
    q, m = out["group_order"], out["layer_order"]
    for collection in (out["rows"], out["columns"]):
        for vertex in collection:
            vertex[0] = (group_u * vertex[0] + group_t) % q
            vertex[1] = (group_u * vertex[1] + group_t) % q
            vertex[2] = (layer_u * vertex[2] + layer_t) % m
    return out


def _decoded_symmetry(inst, multiplier=1, layer_shift=0, reflected=False):
    out = json.loads(json.dumps(inst))
    q, m = out["group_order"], out["layer_order"]
    for name in ("rows", "columns"):
        transformed = []
        for encoded in out[name]:
            x, y, layer = _decode_vertex(encoded, out, compact=True)
            if reflected:
                x, y, layer = y, x, (-layer) % m
            x = multiplier * x % q
            y = multiplier * y % q
            layer = (layer + layer_shift) % m
            transformed.append(_encode_vertex((x, y, layer), out))
        out[name] = transformed
    return out


def _reorder_queries(inst, row_order, column_order):
    out = json.loads(json.dumps(inst))
    old_answer = out["answer"]["counts"]
    out["rows"] = [out["rows"][index] for index in row_order]
    out["columns"] = [out["columns"][index] for index in column_order]
    out["answer"] = {
        "counts": [
            [old_answer[row_index][column_index] for column_index in column_order]
            for row_index in row_order
        ]
    }
    return out


def _mode_attack(inst):
    value = inst["layer_order"] + 1
    return {"counts": [[value] * inst["side"] for _ in range(inst["side"])]}


def _classify_with_vertices(inst, rows, columns):
    q, m = inst["group_order"], inst["layer_order"]
    return _answer_from_decoded(rows, columns, q, m)


def _raw_coordinate_attack(inst):
    rows = [tuple(vertex) for vertex in inst["rows"]]
    columns = [tuple(vertex) for vertex in inst["columns"]]
    return _classify_with_vertices(inst, rows, columns)


def _one_step_vertex(vertex, inst):
    values = []
    for coordinate, chain, modulus in (
        (vertex[0], inst["group_chain"], inst["group_order"]),
        (vertex[1], inst["group_chain"], inst["group_order"]),
        (vertex[2], inst["layer_chain"], inst["layer_order"]),
    ):
        values.append(
            chain["a_inverse"][1]
            * (chain["a"][0] * coordinate + chain["b"][0] - chain["b"][1])
            % modulus
        )
    return tuple(values)


def _one_step_attack(inst):
    rows = [_one_step_vertex(vertex, inst) for vertex in inst["rows"]]
    columns = [_one_step_vertex(vertex, inst) for vertex in inst["columns"]]
    return _classify_with_vertices(inst, rows, columns)


def _diagonal_only_attack(inst):
    q, m = inst["group_order"], inst["layer_order"]
    params = _parameters(q, m)
    rows = [_decode_vertex(vertex, inst, compact=True) for vertex in inst["rows"]]
    columns = [
        _decode_vertex(vertex, inst, compact=True) for vertex in inst["columns"]
    ]
    return {
        "counts": [
            [params["t"] if row == column else params["mu"] for column in columns]
            for row in rows
        ]
    }


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(item) for item in value)
    return 1


def _demo_graph_audit(inst):
    """Expand the entire demo graph and check every A^2 entry independently."""
    q, m = inst["group_order"], inst["layer_order"]
    vertices = [(x, y, layer) for x in range(q) for y in range(q) for layer in range(m)]
    index = {vertex: position for position, vertex in enumerate(vertices)}
    outgoing = []
    incoming_degree = [0] * len(vertices)
    for source in vertices:
        targets = {
            index[target]
            for target in vertices
            if _adjacent_decoded(source, target, q, m)
        }
        outgoing.append(targets)
        for target in targets:
            incoming_degree[target] += 1
    params = _parameters(q, m)
    if any(len(targets) != params["k"] for targets in outgoing):
        return False, "demo out-degree mismatch", 0
    if any(value != params["k"] for value in incoming_degree):
        return False, "demo in-degree mismatch", 0
    checked = 0
    for source_index, source in enumerate(vertices):
        counts = [0] * len(vertices)
        for middle in outgoing[source_index]:
            for target in outgoing[middle]:
                counts[target] += 1
        for target_index, target in enumerate(vertices):
            checked += 1
            expected = _count_for_pair(source, target, q, m)
            if counts[target_index] != expected:
                return False, "demo A^2 identity mismatch", checked
    return True, "ok", checked


def selftest():
    """Run all mandatory correctness, resistance, scale, and invariance gates."""
    report = {}

    # G1: all presets and seeds, JSON round-trip, plus a fully expanded demo A^2.
    attempts = 0
    verified = 0
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            attempts += 1
            verified += int(ok)
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_ok, demo_reason, demo_entries = _demo_graph_audit(demo)
    report["G1_planted_verifies"] = {
        "pass": verified == attempts and json_native and demo_ok,
        "verified": verified,
        "attempts": attempts,
        "answer_json_native": json_native,
        "expanded_demo_a2_entries_checked": demo_entries,
        "expanded_demo_reason": demo_reason,
    }

    ship_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=12_345, **ship_params)
    planted = json.loads(json.dumps(inst["answer"]))

    # G2: five distinct corruption reasons.
    counts = planted["counts"]
    differing = None
    flat_positions = [
        (r, c) for r in range(inst["side"]) for c in range(inst["side"])
    ]
    for first in flat_positions:
        for second in flat_positions:
            if counts[first[0]][first[1]] != counts[second[0]][second[1]]:
                differing = (first, second)
                break
        if differing:
            break
    swapped = json.loads(json.dumps(planted))
    first, second = differing
    swapped["counts"][first[0]][first[1]], swapped["counts"][second[0]][second[1]] = (
        swapped["counts"][second[0]][second[1]],
        swapped["counts"][first[0]][first[1]],
    )
    variants = {
        "drop": {"counts": counts[:-1]},
        "swap": swapped,
        "duplicate": {"counts": [counts[0] + [counts[0][0]]] + counts[1:]},
        "empty": {},
        "out_of_range": {
            "counts": [[inst["degree_bound"] + 1] + counts[0][1:]] + counts[1:]
        },
    }
    corruptions = {}
    for name, candidate in variants.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(reasons) == 5,
        "corruptions": corruptions,
        "distinct_reasons": len(reasons),
    }

    # G3: tagged JSON inside prose and a Markdown fence.
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I counted the paths exactly.\n<answer>\n```json\n{encoded}\n```\n</answer>\n"
    parsed = parse_answer(response)
    garbage = parse_answer("There is no tagged JSON answer in this response.")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage is None,
        "realistic_response_recovered": parsed == inst["answer"],
        "garbage_returns_none": garbage is None,
    }

    # G4: the exact stated structure-aware matrix language.
    guess_rng = random.Random(0x151000110)
    guess_total = 200_000
    guess_hits = 0
    target = inst["answer"]
    for _ in range(guess_total):
        guess_hits += int(random_candidate(inst, guess_rng) == target)
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "exact_probability_fraction": f"1/{search_space(inst)}",
        "exact_probability_log10": -math.log10(search_space(inst)),
        "candidate_space_bits": search_space(inst).bit_length(),
        "sampling_prior": "uniform side-by-side matrices with entries in 0,...,K",
    }

    attack_names = (
        "raw_coordinate_magnitude_outlier",
        "constant_nonedge_mode",
        "raw_coordinate_greedy",
        "one_step_decoder_ansatz",
        "diagonal_only_ansatz",
        "random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    compact_successes = 0
    compact_seconds = 0.0

    for seed in range(80, 88):
        test_inst = make_instance(seed=seed, **ship_params)
        expected = test_inst["answer"]
        side = test_inst["side"]
        q = test_inst["group_order"]
        m = test_inst["layer_order"]
        params = _parameters(q, m)

        start = time.perf_counter()
        magnitude_rows = sorted(
            range(side), key=lambda r: sum(test_inst["rows"][r]), reverse=True
        )
        magnitude_columns = sorted(
            range(side), key=lambda c: sum(test_inst["columns"][c]), reverse=True
        )
        magnitude_guess = {
            "counts": [
                [
                    params["t"]
                    if magnitude_rows.index(r) == magnitude_columns.index(c)
                    else params["mu"]
                    for c in range(side)
                ]
                for r in range(side)
            ]
        }
        attack_seconds["raw_coordinate_magnitude_outlier"] += time.perf_counter() - start
        successes["raw_coordinate_magnitude_outlier"] += int(magnitude_guess == expected)

        for name, function in (
            ("constant_nonedge_mode", _mode_attack),
            ("raw_coordinate_greedy", _raw_coordinate_attack),
            ("one_step_decoder_ansatz", _one_step_attack),
            ("diagonal_only_ansatz", _diagonal_only_attack),
        ):
            start = time.perf_counter()
            candidate = function(test_inst)
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(candidate == expected)

        restart_rng = random.Random(seed ^ 0xBAD5EED)
        start = time.perf_counter()
        restart_solved = False
        for _ in range(256):
            if random_candidate(test_inst, restart_rng) == expected:
                restart_solved = True
                break
        attack_seconds["random_restart_256"] += time.perf_counter() - start
        successes["random_restart_256"] += int(restart_solved)

        start = time.perf_counter()
        reference = _reference_answer(test_inst)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(reference == expected)

        start = time.perf_counter()
        compact = _compact_answer(test_inst)
        compact_seconds += time.perf_counter() - start
        compact_successes += int(compact == expected)

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    side = inst["side"]
    reference_operations = 4 * inst["size"] * (3 * 2 * side) + 2 * side * side + 6
    compact_operations = 4 * (3 * 2 * side) + 2 * side * side + 6
    reference_algorithm = {
        "name": "direct affine-recurrence evaluation plus Construction-I case count",
        "complexity": "O(n*side + side^2) exact modular operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
        "intended_compact_route": {
            "name": "affine-potential invariant plus Construction-I case count",
            "operations": compact_operations,
            "wall_clock_sec": round(compact_seconds / 8, 6),
            "solves": f"{compact_successes}/8",
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_solution_density": guess_probability,
        "shipping_exact_density_fraction": f"1/{search_space(inst)}",
        "shipping_exact_density_log10": -math.log10(search_space(inst)),
        "shipping_exact_solution_count": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference_algorithm["wall_clock_sec"],
        "reference_operation_count": reference_operations,
    }

    # G7: double n, the recurrence length, at fixed certificate shape.
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build_sec = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_sizes = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["size"] == 2 * inst["size"]
        and len(render(doubled)) > len(render(inst))
        and ladder_sizes == sorted(ladder_sizes)
        and len(set(ladder_sizes)) == len(ladder_sizes),
        "shipping_n": inst["size"],
        "doubled_n": doubled["size"],
        "answer_atoms_shipping": _atomic_elements(inst["answer"]),
        "answer_atoms_doubled": _atomic_elements(doubled["answer"]),
        "doubled_build_sec": round(doubled_build_sec, 6),
        "doubled_verify_reason": doubled_reason,
        "reference_operations_shipping": reference_operations,
        "reference_operations_doubled": 2 * (reference_operations - 78) + 78,
    }

    # G8: encoder relabellings, graph automorphisms, input reorderings, compositions.
    invariant_count = 0
    carried_count = 0
    unrelated_keys = []
    transformations_per_seed = 7
    for seed in range(201, 221):
        original = make_instance(seed=seed, **ship_params)
        key = canonical_key(original)
        q, m = original["group_order"], original["layer_order"]
        row_reverse = list(reversed(range(original["side"])))
        column_rotate = list(range(1, original["side"])) + [0]
        variants = [
            _raw_affine_relabel(original, 3, 17, 5, 23),
            _decoded_symmetry(original, multiplier=7, layer_shift=0),
            _decoded_symmetry(original, multiplier=1, layer_shift=29),
            _decoded_symmetry(original, multiplier=11, layer_shift=31),
            _decoded_symmetry(original, multiplier=13, layer_shift=37, reflected=True),
            _reorder_queries(original, row_reverse, column_rotate),
        ]
        composed = _raw_affine_relabel(
            _decoded_symmetry(original, multiplier=17, layer_shift=41, reflected=True),
            19,
            43,
            23,
            47,
        )
        variants.append(_reorder_queries(composed, row_reverse, column_rotate))
        for transformed in variants:
            invariant_count += int(canonical_key(transformed) == key)
            carried_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    expected_invariants = 20 * transformations_per_seed
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == expected_invariants
        and carried_count == expected_invariants
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariant_attempts": expected_invariants,
        "real_transformations_verified": carried_count,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": distinct_count,
        "transformations": [
            "affine relabelling of displayed coordinates",
            "cyclic-group automorphism",
            "layer translation",
            "group automorphism composed with layer translation",
            "coordinate swap composed with layer reflection",
            "independent row/column input reorderings",
            "a composition of all three kinds",
        ],
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    worst_chars = 0
    for seed in range(32):
        candidate_inst = make_instance(seed=seed, **ship_params)
        worst_chars = max(
            worst_chars,
            len(json.dumps(candidate_inst["answer"], separators=(",", ":"))),
        )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    answer_elements = _atomic_elements(inst["answer"])
    report["G9_no_tool_suitability"] = {
        "pass": len(answer_blob) <= 2_000
        and answer_elements <= 256
        and compact_operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": answer_elements,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": (worst_chars + 3) // 4,
        "intended_route_operations": compact_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
