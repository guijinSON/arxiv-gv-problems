"""Verified problem generator for arXiv:1608.04838.

Lu, Wang, and Yu use absorbing edges to turn an almost-perfect matching in a
dense k-partite k-graph into a matching missing only one vertex per part.  This
module specializes their exact definition to k=3.  Vertices are binary vectors
and edge membership is given by a full-rank syndrome map, so legal pair
co-degrees are equal by construction.

The generated promise has an honest polynomial reference algorithm: Gaussian
elimination over GF(2) finds an absorbing edge.  A solver without tools can
avoid that mechanical calculation by noticing that all three part maps feed
the same linear syndrome and cancelling the transformed vectors directly.
That mechanical/structural gap is why this is Track B, not an average-case
hardness claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from collections import Counter


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "3-partite 3-uniform hypergraph with vertices in GF(2)^d",
        "type-1 vertex set S",
        "S-absorbing hyperedge",
    ],
    "verification_operations": [
        "exact coordinate permutations over GF(2)",
        "exact GF(2) matrix-vector products",
        "hyperedge membership and disjointness checks",
        "direct check of the paper's S-absorbing-edge definition",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The three part-specific coordinate permutations feed one shared linear "
        "syndrome, and the target-set XOR equals the syndrome difference of the "
        "two V1 vertices, so three cross-part XORs produce an absorber."
    ),
    "hardness_basis": (
        "Track B: Section 3's absorbing-edge definition can be searched in this "
        "finite-field family by GF(2) Gaussian elimination in O(r^2 d) bit "
        "operations (18,408 bit operations and 0.0017--0.0032 s per instance across "
        "repeated eight-run local measurements); the shared-syndrome change of variables uses exactly "
        "3d = 240 XORs."
    ),
    "max_answer_tokens": 63,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "hard": {"n": 80, "rank": 16, "target_count": 21},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "The target-set XOR and the syndrome difference of the two V1 vertices "
    "are the same invariant in the permuted coordinate spaces."
)
PLACEBO_HINT: str = (
    "The binary vertex spaces use precise conventions, so careful bookkeeping "
    "and patient checking matter throughout the calculation."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of three fixed-width binary row strings [x,y,z], encoding "
        "one GF(2)^d vertex from each labeled part, required up front to be "
        "disjoint from S and to be an edge."
    ),
    "bounds": {
        "rows": "exactly 3 binary strings",
        "columns": "exactly the instance dimension d=n bits per string",
        "entries": "characters 0 and 1 only",
        "structural_constraints": "disjoint from S and already a hyperedge",
    },
}

# Filled after the script-owned three-arm oracle runs.  These values are
# diagnostic only; G9(c)'s answer/operation caps are the gate.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}
G9_ORACLE_STATUS = (
    "blocked before any scored attempt: bare, structural-hint, and placebo "
    "harden.py runs all received OpenRouter HTTP 403 key-limit errors"
)

NOTES = r"""
Definition fixed by the paper. Section 1 defines a k-partite k-graph, legal
sets, matching, and minimum legal co-degree. Section 3, immediately before
Lemma 3.2 (absorbing-counting), defines a type-j set S and an S-absorbing edge:
one matching edge can be replaced by two edges that cover S. For k=3 and a
type-1 set S={a,a',b,c}, that definition is exactly the two alternatives
checked by verify().

Step-0 algorithm check. The main theorem is existential for sufficiently large
n and does not give an explicit finite threshold n_0. Its proof also starts
from maximum matchings and uses the probabilistic absorbing Lemma 3.4. Merely
planting an almost-perfect matching in a random dense hypergraph would not
support Track A: dense matching search has many easy witnesses. This module
therefore makes the efficient method explicit and declares Track B. In the
special finite-field family, generic GF(2) elimination is a complete reference
method. selftest reports its measured wall time and bit-operation count.

Construction and certificate. For each part i, a displayed coordinate
permutation P_i is followed by the same full-rank r-by-d matrix A. A triple is
an edge when A(P_1 x xor P_2 y xor P_3 z) belongs to the displayed target set T.
Thus every legal pair has exactly |T|*2^(d-r) neighbors, satisfying the paper's
positive constant co-degree hypothesis with c=|T|/2^r. The generator samples S
and composes three XOR identities. It never searches the instance for an
absorber. The XOR of all target syndromes is the syndrome of
P_1(a) xor P_1(a'), and three cross-part XORs make the candidate edge and both
replacement triples have exactly that syndrome.

What makes the paper's argument easy or inapplicable. Lemma 3.2 says that three
appropriate co-degree conditions create many absorbing edges, and Lemma 3.4
randomly samples a small absorbing matching. Those facts make random guessing
easier as c grows, so the shipping preset uses a fixed small positive c. The
main Theorem 1.1 concerns n-1-edge matchings at co-degree n/k; this generator
does not pretend that a single absorber is that main-theorem witness.

Attack handling. Vertex labels range over the whole vector space, all fibers of
the syndrome map have equal size, and the planted answer is made from the same
linear edge rule as every decoy. Minimum-weight and edge-first greedy choices
do not satisfy both replacement-edge tests. Raw-coordinate XOR ignores the
three independent coordinate changes. Structure-aware random restart samples
uniformly from disjoint edges, not from arbitrary triples. The successful
Gaussian method is reported separately, as Track B requires.

Canonicalization. The key uses the exact distribution of all linear
functionals on T together with normalized syndromes of S. It is unchanged by
syndrome-basis changes, simultaneous bit-coordinate relabeling, translations
that preserve T, one-part translations that translate T, swapping the two
named V_1 vertices, swapping V_2 with V_3, target ordering, and compositions
of those maps. It is a strong invariant, not a complete canonical form for
arbitrary succinct-hypergraph isomorphism.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_KEY_CACHE: dict[tuple, str] = {}
_PERM_TABLE_CACHE: dict[tuple[int, ...], tuple[tuple[int, ...], ...]] = {}
_INVERSE_PERM_CACHE: dict[tuple[int, ...], tuple[int, ...]] = {}
_PERM_FAST_CACHE: dict[tuple[int, ...], int | None] = {}
_PERM_OBJECT_CACHE: dict[int, tuple[list[int], int | None, tuple[tuple[int, ...], ...] | None]] = {}
_INVERSE_OBJECT_CACHE: dict[int, tuple[list[int], list[int]]] = {}
_ROWS_CACHE: dict[tuple[tuple[int, ...], ...], tuple[int, ...]] = {}
_TARGET_CACHE: dict[tuple[tuple[int, ...], ...], tuple[int, ...]] = {}
_S_CACHE: dict[tuple, tuple[int, int, int, int]] = {}
_SOLVER_CACHE: dict[tuple[tuple[int, ...], int], tuple] = {}
_OBJECT_CACHE: dict[int, tuple[dict, tuple[int, ...], tuple[int, ...], tuple[int, int, int, int]]] = {}


def _bits(value: int, width: int) -> list[int]:
    return [(value >> i) & 1 for i in range(width)]


def _bit_string_value(value: int, width: int) -> str:
    return format(value, f"0{width}b")[::-1]


def _from_bits(row: object) -> int | None:
    if not isinstance(row, list):
        return None
    value = 0
    for i, bit in enumerate(row):
        if not isinstance(bit, int) or isinstance(bit, bool) or bit not in (0, 1):
            return None
        value |= bit << i
    return value


def _permute(value: int, permutation: list[int]) -> int:
    """Output bit j is input bit permutation[j]."""
    object_cached = _PERM_OBJECT_CACHE.get(id(permutation))
    if object_cached is not None and object_cached[0] is permutation:
        shift, tables = object_cached[1], object_cached[2]
    else:
        key = tuple(permutation)
        possible = permutation[0] if permutation else 0
        shift = possible if all(source == (j + possible) % len(permutation)
                                for j, source in enumerate(permutation)) else None
        tables = _PERM_TABLE_CACHE.get(key)
        if shift is None and tables is None:
            mutable = [[0] * 256 for _ in range((len(permutation) + 7) // 8)]
            destinations = [0] * len(permutation)
            for destination, source in enumerate(permutation):
                destinations[source] = destination
            for chunk_index, table in enumerate(mutable):
                for byte in range(256):
                    moved = 0
                    for bit in range(8):
                        source = 8 * chunk_index + bit
                        if source < len(permutation) and ((byte >> bit) & 1):
                            moved |= 1 << destinations[source]
                    table[byte] = moved
            tables = tuple(tuple(table) for table in mutable)
            _PERM_TABLE_CACHE[key] = tables
        _PERM_OBJECT_CACHE[id(permutation)] = (permutation, shift, tables)
    if shift is not None:
        width = len(permutation)
        if shift == 0:
            return value
        return (value >> shift) | ((value & ((1 << shift) - 1)) << (width - shift))
    out = 0
    for chunk_index, table in enumerate(tables):
        out |= table[(value >> (8 * chunk_index)) & 255]
    return out


def _unpermute(value: int, permutation: list[int]) -> int:
    cached = _INVERSE_OBJECT_CACHE.get(id(permutation))
    if cached is not None and cached[0] is permutation:
        inverse = cached[1]
    else:
        mutable = [0] * len(permutation)
        for destination, source in enumerate(permutation):
            mutable[source] = destination
        inverse = mutable
        _INVERSE_OBJECT_CACHE[id(permutation)] = (permutation, inverse)
    return _permute(value, inverse)


def _mat_vec(rows: list[int], value: int) -> int:
    out = 0
    for i, row in enumerate(rows):
        out |= ((row & value).bit_count() & 1) << i
    return out


def _rows(inst: dict) -> list[int]:
    cached = _OBJECT_CACHE.get(id(inst))
    if cached is not None and cached[0] is inst and cached[1]:
        return cached[1]  # type: ignore[return-value]
    key = tuple(tuple(row) for row in inst["matrix"])
    if key not in _ROWS_CACHE:
        _ROWS_CACHE[key] = tuple(_from_bits(row) for row in inst["matrix"])  # type: ignore[arg-type]
    _cache_instance(inst, rows=_ROWS_CACHE[key])
    return _ROWS_CACHE[key]  # type: ignore[return-value]


def _vectors(inst: dict) -> tuple[int, int, int, int]:
    cached = _OBJECT_CACHE.get(id(inst))
    if cached is not None and cached[0] is inst and cached[3]:
        return cached[3]
    s = inst["S"]
    key = (
        tuple(s["V1"][0]), tuple(s["V1"][1]),
        tuple(s["V2"]), tuple(s["V3"]),
    )
    if key not in _S_CACHE:
        _S_CACHE[key] = (
            _from_bits(s["V1"][0]),
            _from_bits(s["V1"][1]),
            _from_bits(s["V2"]),
            _from_bits(s["V3"]),
        )  # type: ignore[assignment]
    _cache_instance(inst, s_values=_S_CACHE[key])
    return _S_CACHE[key]


def _targets(inst: dict) -> list[int]:
    cached = _OBJECT_CACHE.get(id(inst))
    if cached is not None and cached[0] is inst and cached[2]:
        return cached[2]  # type: ignore[return-value]
    key = tuple(tuple(row) for row in inst["targets"])
    if key not in _TARGET_CACHE:
        _TARGET_CACHE[key] = tuple(_from_bits(row) for row in inst["targets"])  # type: ignore[arg-type]
    _cache_instance(inst, targets=_TARGET_CACHE[key])
    return _TARGET_CACHE[key]  # type: ignore[return-value]


def _cache_instance(
    inst: dict,
    rows: tuple[int, ...] | None = None,
    targets: tuple[int, ...] | None = None,
    s_values: tuple[int, int, int, int] | None = None,
) -> None:
    old = _OBJECT_CACHE.get(id(inst))
    if old is not None and old[0] is inst:
        old_rows, old_targets, old_s = old[1], old[2], old[3]
    else:
        old_rows, old_targets, old_s = (), (), ()
    _OBJECT_CACHE[id(inst)] = (
        inst,
        rows if rows is not None else old_rows,
        targets if targets is not None else old_targets,
        s_values if s_values is not None else old_s,
    )  # type: ignore[arg-type]


def _syndrome(inst: dict, x: int, y: int, z: int) -> int:
    p1, p2, p3 = inst["permutations"]
    transformed = _permute(x, p1) ^ _permute(y, p2) ^ _permute(z, p3)
    return _mat_vec(_rows(inst), transformed)


def _is_edge(inst: dict, x: int, y: int, z: int) -> bool:
    return _syndrome(inst, x, y, z) in _targets(inst)


def _is_absorber(inst: dict, x: int, y: int, z: int) -> bool:
    a, aa, b, c = _vectors(inst)
    return (
        (_is_edge(inst, aa, y, c) and _is_edge(inst, a, b, z))
        or (_is_edge(inst, a, y, c) and _is_edge(inst, aa, b, z))
    )


def _candidate_ints(inst: dict, answer: object) -> tuple[int, int, int] | None:
    d = inst["n"]
    if not isinstance(answer, list) or len(answer) != 3:
        return None
    if any(
        not isinstance(row, str)
        or len(row) != d
        or re.fullmatch(r"[01]+", row) is None
        for row in answer
    ):
        return None
    return tuple(int(row[::-1], 2) for row in answer)  # type: ignore[return-value]


def _make_full_rank_rows(d: int, rank: int, rng: random.Random) -> list[int]:
    # [I | random] is full-row-rank by construction.  Column permutation and
    # invertible row additions hide the systematic coordinates without a search.
    rows = []
    for i in range(rank):
        tail = rng.getrandbits(d - rank) << rank
        rows.append((1 << i) | tail)
    coordinate_order = list(range(d))
    rng.shuffle(coordinate_order)
    rows = [_permute(row, coordinate_order) for row in rows]
    for _ in range(8 * rank):
        i = rng.randrange(rank)
        j = rng.randrange(rank - 1)
        if j >= i:
            j += 1
        rows[i] ^= rows[j]
    return rows


def _planted_values(
    s_values: tuple[int, int, int, int], permutations: list[list[int]]
) -> tuple[int, int, int]:
    a, aa, b, c = s_values
    p1, p2, p3 = permutations
    tx = _permute(b, p2) ^ _permute(c, p3)
    ty = _permute(a, p1) ^ _permute(c, p3)
    tz = _permute(aa, p1) ^ _permute(b, p2)
    return _unpermute(tx, p1), _unpermute(ty, p2), _unpermute(tz, p3)


def _make_targets(rank: int, count: int, distinguished: int, rng: random.Random) -> list[int]:
    """Compose a target set T with distinguished in T and XOR(T)=distinguished."""
    limit = 1 << rank
    for _ in range(10_000):
        chosen: set[int] = set()
        while len(chosen) < count - 2:
            value = rng.randrange(limit)
            if value != distinguished:
                chosen.add(value)
        final = 0
        for value in chosen:
            final ^= value
        if final != distinguished and final not in chosen:
            targets = list(chosen) + [final, distinguished]
            rng.shuffle(targets)
            return targets
    raise RuntimeError("could not compose a distinct target set with the required XOR")


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a certified S-absorbing edge by composing XOR identities."""
    d = int(n)
    rank = int(params.pop("rank", max(2, min(16, d - 2))))
    target_count = int(params.pop("target_count", 17))
    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    if d < 4:
        raise ValueError("n (the binary-vector dimension) must be at least 4")
    if not (1 <= rank < d):
        raise ValueError("rank must satisfy 1 <= rank < n")
    if not (5 <= target_count <= (1 << rank)) or target_count % 2 == 0:
        raise ValueError("target_count must be odd and in 5..2^rank")

    rng = random.Random(seed)
    rows = _make_full_rank_rows(d, rank, rng)

    shifts = rng.sample(range(d), 3)
    permutations = [[(j + shift) % d for j in range(d)] for shift in shifts]

    limit = 1 << d
    for _ in range(1000):
        a = rng.randrange(limit)
        aa = rng.randrange(limit)
        if aa == a:
            continue
        b = rng.randrange(limit)
        c = rng.randrange(limit)
        planted = _planted_values((a, aa, b, c), permutations)
        x, y, z = planted
        if x not in (a, aa) and y != b and z != c:
            break
    else:
        raise RuntimeError("could not draw a disjoint planted absorber")

    distinguished = _mat_vec(rows, _permute(a ^ aa, permutations[0]))
    target_values = _make_targets(rank, target_count, distinguished, rng)

    answer = [_bit_string_value(value, d) for value in planted]
    return {
        "paper": "arXiv:1608.04838",
        "family": "S-absorbing edge in a 3-partite 3-graph",
        "n": d,
        "rank": rank,
        "target_count": target_count,
        "part_size": 1 << d,
        "minimum_legal_codegree": target_count << (d - rank),
        "matrix": [_bits(row, d) for row in rows],
        "permutations": permutations,
        "targets": [_bits(value, rank) for value in target_values],
        "S": {
            "V1": [_bits(a, d), _bits(aa, d)],
            "V2": _bits(b, d),
            "V3": _bits(c, d),
        },
        "answer": answer,
    }


def _bit_string(row: list[int]) -> str:
    # Coordinate zero is printed first, matching the JSON arrays.
    return "".join(str(bit) for bit in row)


def render(inst: dict) -> str:
    d = inst["n"]
    rank = inst["rank"]
    p1, p2, p3 = inst["permutations"]
    s = inst["S"]
    lines = [
        "Find an S-absorbing edge in the following 3-partite 3-uniform hypergraph.",
        "",
        "Definitions and conventions.",
        f"GF(2)^d means all binary vectors of length d={d}; coordinates are numbered 0 through {d - 1}.",
        "XOR is coordinatewise addition modulo 2.",
        "There are three labeled vertex parts V1, V2, V3, each equal to GF(2)^d; copies in different parts are distinct vertices even when their bit vectors agree.",
        "A triple (x,y,z) always means x in V1, y in V2, and z in V3.",
        "For a listed permutation P, (P v)[j] = v[P[j]].",
        f"For the displayed {rank}-by-{d} binary matrix A, A v is ordinary matrix-vector multiplication modulo 2.",
        "A triple (x,y,z) is a hyperedge exactly when A(P1 x XOR P2 y XOR P3 z) is one of the listed target syndromes T.",
        "",
        "The set S consists of a,a' in V1, b in V2, and c in V3.",
        "An edge (x,y,z) is disjoint from S when x is neither a nor a', y is not b, and z is not c.",
        "A disjoint edge (x,y,z) is S-absorbing exactly when at least one of these two alternatives holds:",
        "  (i) (a',y,c) and (a,b,z) are both hyperedges;",
        "  (ii) (a,y,c) and (a',b,z) are both hyperedges.",
        "This is the k=3 specialization of replacing one matching edge by two edges covering S.",
        "",
        f"Every legal pair has exactly {inst['minimum_legal_codegree']} neighbors among {inst['part_size']} vertices in the missing part.",
        "",
        "P1 = " + json.dumps(p1, separators=(",", ":")),
        "P2 = " + json.dumps(p2, separators=(",", ":")),
        "P3 = " + json.dumps(p3, separators=(",", ":")),
        "",
        "Rows of A (coordinate 0 first):",
    ]
    lines.extend(_bit_string(row) for row in inst["matrix"])
    lines.extend(["", "Target syndromes T (syndrome coordinate 0 first):"])
    lines.extend(_bit_string(row) for row in inst["targets"])
    lines.extend(
        [
            "",
            "S vectors (coordinate 0 first):",
            "a  = " + _bit_string(s["V1"][0]),
            "a' = " + _bit_string(s["V1"][1]),
            "b  = " + _bit_string(s["V2"]),
            "c  = " + _bit_string(s["V3"]),
        ]
    )

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])

    example = '["' + ("0" * d) + '","' + ("0" * d) + '","' + ("0" * d) + '"]'
    lines.extend(
        [
            "",
            f"Return exactly a JSON list [x,y,z] of three quoted {d}-character binary strings; each string lists coordinate 0 first.",
            "Give your final answer inside <answer></answer> tags.",
            f"Format example: <answer>{example}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    try:
        match = _ANSWER_RE.search(text)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, list):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    d = inst["n"]
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) < 3:
        return False, "answer is missing a part vector"
    if len(answer) > 3:
        return False, "answer contains an extra part vector"
    if any(not isinstance(row, str) for row in answer):
        return False, "each part vertex must be a quoted binary string"
    if any(len(row) != d for row in answer):
        return False, f"each binary string must have exactly {d} characters"
    for row in answer:
        if re.fullmatch(r"[01]+", row) is None:
            return False, "binary strings may contain only characters 0 and 1"

    values = _candidate_ints(inst, answer)
    if values is None:
        return False, "malformed binary matrix"
    x, y, z = values
    a, aa, b, c = _vectors(inst)
    if x in (a, aa) or y == b or z == c:
        return False, "candidate edge is not disjoint from S"
    if not _is_edge(inst, x, y, z):
        return False, "candidate triple is not a hyperedge"
    if not _is_absorber(inst, x, y, z):
        return False, "edge is not S-absorbing"
    return True, "ok"


def _rref_solver(rows: list[int], d: int) -> tuple:
    """Return a particular-solution function, kernel basis, and bit-op count."""
    cache_key = (tuple(rows), d)
    if cache_key in _SOLVER_CACHE:
        return _SOLVER_CACHE[cache_key]
    rank = len(rows)
    work = list(rows)
    transform = [1 << i for i in range(rank)]
    pivots = []
    operations = 0
    pivot_row = 0
    for column in range(d):
        pivot = next((i for i in range(pivot_row, rank) if (work[i] >> column) & 1), None)
        if pivot is None:
            continue
        if pivot != pivot_row:
            work[pivot_row], work[pivot] = work[pivot], work[pivot_row]
            transform[pivot_row], transform[pivot] = transform[pivot], transform[pivot_row]
            operations += 2 * (d + rank)
        for i in range(rank):
            if i != pivot_row and ((work[i] >> column) & 1):
                work[i] ^= work[pivot_row]
                transform[i] ^= transform[pivot_row]
                operations += d + rank
        pivots.append(column)
        pivot_row += 1
        if pivot_row == rank:
            break
    if pivot_row != rank:
        raise ValueError("matrix is not full row rank")

    pivot_set = set(pivots)
    free = [j for j in range(d) if j not in pivot_set]
    kernel = []
    for column in free:
        value = 1 << column
        for i, pivot_column in enumerate(pivots):
            if (work[i] >> column) & 1:
                value |= 1 << pivot_column
        kernel.append(value)
        operations += rank

    def solve(rhs: int) -> int:
        value = 0
        for i, pivot_column in enumerate(pivots):
            if (transform[i] & rhs).bit_count() & 1:
                value |= 1 << pivot_column
        return value

    result = (solve, kernel, operations)
    _SOLVER_CACHE[cache_key] = result
    return result


def _reference_algorithm(inst: dict) -> tuple[list[str], int]:
    """Generic GF(2) elimination, deliberately not the planted XOR shortcut."""
    d = inst["n"]
    rank = inst["rank"]
    rows = _rows(inst)
    solve, kernel, operations = _rref_solver(rows, d)
    a, aa, b, c = _vectors(inst)
    p1, p2, p3 = inst["permutations"]

    desired = 0
    for target in _targets(inst):
        desired ^= target
    rhs_y = _mat_vec(rows, _permute(aa, p1) ^ _permute(c, p3)) ^ desired
    rhs_z = _mat_vec(rows, _permute(a, p1) ^ _permute(b, p2)) ^ desired
    ty = solve(rhs_y)
    tz = solve(rhs_z)
    operations += (inst["target_count"] - 1) * rank
    operations += 2 * rank * d + 2 * rank * rank + 2 * d

    y = _unpermute(ty, p2)
    if y == b:
        ty ^= kernel[0]
        y = _unpermute(ty, p2)
        operations += d
    z = _unpermute(tz, p3)
    if z == c:
        tz ^= kernel[-1]
        z = _unpermute(tz, p3)
        operations += d
    rhs_x = _mat_vec(rows, ty ^ tz) ^ desired
    tx = solve(rhs_x)
    operations += rank * d + rank * rank + d
    x = _unpermute(tx, p1)
    if x in (a, aa):
        for kernel_value in kernel:
            trial = tx ^ kernel_value
            trial_x = _unpermute(trial, p1)
            operations += d
            if trial_x not in (a, aa):
                tx, x = trial, trial_x
                break
    answer = [
        _bit_string_value(x, d),
        _bit_string_value(y, d),
        _bit_string_value(z, d),
    ]
    return answer, operations


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from all S-disjoint hyperedges, the stated prior."""
    d = inst["n"]
    rank = inst["rank"]
    rows = _rows(inst)
    solve, _, _ = _rref_solver(rows, d)
    targets = _targets(inst)
    p1, p2, p3 = inst["permutations"]
    a, aa, b, c = _vectors(inst)
    limit = 1 << d
    while True:
        x = rng.randrange(limit)
        y = rng.randrange(limit)
        z0_transformed = rng.randrange(limit)
        desired = rng.choice(targets)
        current = _mat_vec(rows, z0_transformed)
        # Project a uniform vector onto the desired syndrome fiber.  Every point
        # of that fiber has exactly 2^rank preimages, so the result is uniform.
        z_transformed = z0_transformed ^ solve(current ^ desired)
        z = _unpermute(
            z_transformed ^ _permute(x, p1) ^ _permute(y, p2), p3
        )
        if x not in (a, aa) and y != b and z != c:
            return [
                _bit_string_value(x, d),
                _bit_string_value(y, d),
                _bit_string_value(z, d),
            ]


def search_space(inst: dict) -> int | None:
    """Exact number of S-disjoint edges sampled by random_candidate."""
    d = inst["n"]
    rank = inst["rank"]
    m = inst["target_count"]
    total = m << (3 * d - rank)
    degree = m << (2 * d - rank)
    codegree = m << (d - rank)
    a, aa, b, c = _vectors(inst)
    forbidden_triples = int(_is_edge(inst, a, b, c)) + int(_is_edge(inst, aa, b, c))
    return total - 4 * degree + 5 * codegree - forbidden_triples


def enumerate_all(inst: dict) -> int | None:
    d = inst["n"]
    if d > 6:
        return None
    a, aa, b, c = _vectors(inst)
    count = 0
    for x in range(1 << d):
        if x in (a, aa):
            continue
        for y in range(1 << d):
            if y == b:
                continue
            for z in range(1 << d):
                if z != c and _is_edge(inst, x, y, z) and _is_absorber(inst, x, y, z):
                    count += 1
    return count


def _span_coordinates(values: list[int]) -> tuple[list[int], int]:
    """Coordinates in any basis of the span; the chosen basis is immaterial below."""
    pivots: dict[int, tuple[int, int]] = {}
    coordinates = []
    dimension = 0
    for value in values:
        work = value
        coordinate = 0
        while work:
            pivot = work.bit_length() - 1
            old = pivots.get(pivot)
            if old is None:
                basis_coordinate = 1 << dimension
                pivots[pivot] = (work, basis_coordinate)
                coordinate ^= basis_coordinate
                dimension += 1
                break
            work ^= old[0]
            coordinate ^= old[1]
        coordinates.append(coordinate)
    return coordinates, dimension


def _walsh_target_weights(targets: list[int], dimension: int) -> list[int]:
    """For every linear functional, count target vectors on which it is one."""
    size = 1 << dimension
    transform = [0] * size
    for target in targets:
        transform[target] += 1
    stride = 1
    while stride < size:
        block = 2 * stride
        for start in range(0, size, block):
            for offset in range(stride):
                left = transform[start + offset]
                right = transform[start + offset + stride]
                transform[start + offset] = left + right
                transform[start + offset + stride] = left - right
        stride = block
    count = len(targets)
    return [(count - value) // 2 for value in transform]


def _canonical_signature(inst: dict) -> tuple:
    rows = _rows(inst)
    p1, p2, p3 = inst["permutations"]
    a, aa, b, c = _vectors(inst)
    sa = _mat_vec(rows, _permute(a, p1))
    saa = _mat_vec(rows, _permute(aa, p1))
    sb = _mat_vec(rows, _permute(b, p2))
    sc = _mat_vec(rows, _permute(c, p3))
    delta_a = sa ^ saa
    affine_s = sa ^ sb ^ sc
    targets = tuple(sorted(_targets(inst)))
    cache_key = (inst["n"], inst["rank"], targets, delta_a, affine_s)
    if cache_key in _KEY_CACHE:
        return (_KEY_CACHE[cache_key],)

    projected, span_dimension = _span_coordinates(
        list(targets) + [delta_a, affine_s]
    )
    projected_targets = projected[:-2]
    projected_delta, projected_affine = projected[-2:]
    weights = _walsh_target_weights(projected_targets, span_dimension)

    # Translating one whole vertex part is a genuine relabelling.  It sends
    # (T, affine_s) to (T xor q, affine_s xor q).  Normalize at every target
    # anchor, then keep the strongest cheap basis-free invariant.  Enumerating
    # functionals only on the span avoids a 2^rank blow-up when rank grows.
    normalized_histograms = []
    for anchor in projected_targets:
        histogram = Counter()
        for functional, target_weight in enumerate(weights):
            anchor_bit = (functional & anchor).bit_count() & 1
            normalized_weight = (
                target_weight if anchor_bit == 0 else len(targets) - target_weight
            )
            delta_bit = (functional & projected_delta).bit_count() & 1
            affine_bit = (
                (functional & projected_affine).bit_count() & 1
            ) ^ anchor_bit
            # Swapping a and a' sends affine_s to affine_s xor delta_a.
            affine_orbit = affine_bit if delta_bit == 0 else 2
            histogram[(normalized_weight, delta_bit, affine_orbit)] += 1
        normalized_histograms.append(tuple(sorted(histogram.items())))
    payload = (
        inst["n"], inst["rank"], inst["target_count"], span_dimension,
        min(normalized_histograms),
    )
    digest = hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
    _KEY_CACHE[cache_key] = digest
    return (digest,)


def canonical_key(inst: dict) -> str:
    return _canonical_signature(inst)[0]


def escalate(params: dict) -> dict | str | None:
    current = {k: v for k, v in params.items() if k != "_preset"}
    d = int(current.get("n", 80))
    rank = int(current.get("rank", 16))
    target_count = int(current.get("target_count", 17))
    # First shrink the allowed syndrome fraction while keeping the 3d-entry
    # witness fixed.  This grows the haystack and the elimination work only.
    if rank < d - 2:
        next_rank = min(d - 2, max(rank + 8, (3 * rank) // 2))
        return {"n": d, "rank": next_rank, "target_count": target_count}
    # Only after the fixed-length axis is exhausted use the remaining atom cap.
    if d < 84:
        next_d = 84
        return {
            "n": next_d,
            "rank": min(next_d - 2, rank + 4),
            "target_count": target_count,
        }
    return "cap_bound"


def _attack_outlier_min_weight(inst: dict) -> object:
    d = inst["n"]
    a, aa, b, c = _vectors(inst)
    choices_x = [v for v in range(8) if v not in (a, aa)]
    choices_y = [v for v in range(8) if v != b]
    choices_z = [v for v in range(8) if v != c]
    return [
        _bit_string_value(choices_x[0], d),
        _bit_string_value(choices_y[0], d),
        _bit_string_value(choices_z[0], d),
    ]


def _attack_greedy_edge_first(inst: dict) -> object:
    d = inst["n"]
    a, aa, b, c = _vectors(inst)
    x = next(v for v in range(8) if v not in (a, aa))
    y = next(v for v in range(8) if v != b)
    p1, p2, p3 = inst["permutations"]
    delta = _permute(a ^ aa, p1)
    z = _unpermute(_permute(x, p1) ^ _permute(y, p2) ^ delta, p3)
    if z == c:
        z ^= 1
    return [_bit_string_value(x, d), _bit_string_value(y, d), _bit_string_value(z, d)]


def _attack_raw_xor(inst: dict) -> object:
    d = inst["n"]
    a, aa, b, c = _vectors(inst)
    # The right identity in the wrong (unpermuted) coordinate system.
    x = b ^ c
    y = a ^ c
    z = aa ^ b
    if x in (a, aa):
        x ^= 1
    if y == b:
        y ^= 2
    if z == c:
        z ^= 4
    return [_bit_string_value(x, d), _bit_string_value(y, d), _bit_string_value(z, d)]


def _random_restart(inst: dict, rng: random.Random, attempts: int = 256) -> object | None:
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _apply_coordinate_relabel(inst: dict, q: list[int]) -> dict:
    out = json.loads(json.dumps(inst))
    inverse = [0] * len(q)
    for j, source in enumerate(q):
        inverse[source] = j
    out["permutations"] = [
        [inverse[source] for source in p] for p in inst["permutations"]
    ]
    s = _vectors(inst)
    moved_s = tuple(_permute(value, q) for value in s)
    d = inst["n"]
    out["S"] = {
        "V1": [_bits(moved_s[0], d), _bits(moved_s[1], d)],
        "V2": _bits(moved_s[2], d),
        "V3": _bits(moved_s[3], d),
    }
    answer_values = _candidate_ints(inst, inst["answer"])
    out["answer"] = [_bit_string_value(_permute(value, q), d) for value in answer_values]
    return out


def _random_invertible_rows(rank: int, rng: random.Random) -> list[int]:
    rows = [1 << i for i in range(rank)]
    for _ in range(8 * rank):
        i = rng.randrange(rank)
        j = rng.randrange(rank - 1)
        if j >= i:
            j += 1
        rows[i] ^= rows[j]
    return rows


def _apply_syndrome_basis(inst: dict, change: list[int]) -> dict:
    out = json.loads(json.dumps(inst))
    old_rows = _rows(inst)
    new_rows = []
    for mask in change:
        row = 0
        for i in range(inst["rank"]):
            if (mask >> i) & 1:
                row ^= old_rows[i]
        new_rows.append(row)
    out["matrix"] = [_bits(row, inst["n"]) for row in new_rows]
    out["targets"] = [
        _bits(_mat_vec(change, target), inst["rank"]) for target in _targets(inst)
    ]
    return out


def _apply_translation(inst: dict, t1: int, t2: int) -> dict:
    out = json.loads(json.dumps(inst))
    p1, p2, p3 = inst["permutations"]
    t3 = _unpermute(_permute(t1, p1) ^ _permute(t2, p2), p3)
    a, aa, b, c = _vectors(inst)
    d = inst["n"]
    out["S"] = {
        "V1": [_bits(a ^ t1, d), _bits(aa ^ t1, d)],
        "V2": _bits(b ^ t2, d),
        "V3": _bits(c ^ t3, d),
    }
    answer_values = _candidate_ints(inst, inst["answer"])
    moved = (
        answer_values[0] ^ t1,
        answer_values[1] ^ t2,
        answer_values[2] ^ t3,
    )
    out["answer"] = [_bit_string_value(value, d) for value in moved]
    return out


def _apply_target_translation(inst: dict, t1: int) -> dict:
    """Relabel V1 by t1 and translate T by the induced syndrome."""
    out = json.loads(json.dumps(inst))
    p1 = inst["permutations"][0]
    syndrome_shift = _mat_vec(_rows(inst), _permute(t1, p1))
    out["targets"] = [
        _bits(target ^ syndrome_shift, inst["rank"])
        for target in _targets(inst)
    ]
    a, aa, b, c = _vectors(inst)
    d = inst["n"]
    out["S"] = {
        "V1": [_bits(a ^ t1, d), _bits(aa ^ t1, d)],
        "V2": _bits(b, d),
        "V3": _bits(c, d),
    }
    answer_values = _candidate_ints(inst, inst["answer"])
    moved = (answer_values[0] ^ t1, answer_values[1], answer_values[2])
    out["answer"] = [_bit_string_value(value, d) for value in moved]
    return out


def _swap_named_objects(inst: dict) -> dict:
    out = json.loads(json.dumps(inst))
    out["S"]["V1"].reverse()
    out["S"]["V2"], out["S"]["V3"] = out["S"]["V3"], out["S"]["V2"]
    out["permutations"][1], out["permutations"][2] = (
        out["permutations"][2], out["permutations"][1]
    )
    out["answer"][1], out["answer"][2] = out["answer"][2], out["answer"][1]
    out["targets"].reverse()
    return out


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atom_count(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "problem_profile": PROBLEM_PROFILE,
        "certificate_language": CERTIFICATE_LANGUAGE,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_failures = []
    g1_checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = json.loads(json.dumps(shipping["answer"]))
    swapped = None
    for row_index in range(3):
        for i in range(shipping["n"]):
            for j in range(i + 1, shipping["n"]):
                if answer[row_index][i] == answer[row_index][j]:
                    continue
                trial = json.loads(json.dumps(answer))
                chars = list(trial[row_index])
                chars[i], chars[j] = chars[j], chars[i]
                trial[row_index] = "".join(chars)
                if not verify(shipping, trial)[0]:
                    swapped = trial
                    break
            if swapped is not None:
                break
        if swapped is not None:
            break
    corruptions = {
        "drop_one": answer[:2],
        "swap_two": swapped,
        "duplicate": answer + [answer[0]],
        "empty": [],
        "out_of_range": json.loads(json.dumps(answer)),
    }
    corruptions["out_of_range"][0] = "2" + corruptions["out_of_range"][0][1:]
    rejection_rows = {}
    reasons = set()
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejection_rows[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejection_rows.values()) and len(reasons) == 5,
        "distinct_reasons": len(reasons),
        "rejections": rejection_rows,
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    model_reply = "I used the common syndrome.\n\n<answer>```json\n" + encoded + "\n```</answer>\n"
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    sample_total = 200_000
    sample_rng = random.Random(271828)
    sample_hits = 0
    sample_start = time.perf_counter()
    for _ in range(sample_total):
        if verify(shipping, random_candidate(shipping, sample_rng))[0]:
            sample_hits += 1
    sample_wall = time.perf_counter() - sample_start
    sample_fraction = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": sample_fraction < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "empirical_probability": sample_fraction,
        "candidate_space": search_space(shipping),
        "prior": "uniform over all S-disjoint hyperedges, with edge membership enforced",
        "sampling_wall_seconds": sample_wall,
    }

    reference_successes = 0
    reference_operations = 0
    reference_start = time.perf_counter()
    for seed in range(8):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate, operations = _reference_algorithm(inst)
        reference_operations += operations
        reference_successes += int(verify(inst, candidate)[0])
    reference_wall = time.perf_counter() - reference_start
    demo = make_instance(seed=2, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_successes == 8 and sample_fraction < 1e-6 and demo_count is not None,
        "shipping_candidate_space": search_space(shipping),
        "enumerate_all_shipping": enumerate_all(shipping),
        "shipping_density_sample_count": sample_total,
        "shipping_valid_hits": sample_hits,
        "shipping_observed_valid_fraction": sample_fraction,
        "density_sampling_wall_seconds": sample_wall,
        "demo_exact_valid_solution_count": demo_count,
        "reference_successes": reference_successes,
        "reference_wall_seconds": reference_wall,
        "reference_wall_seconds_mean": reference_wall / 8,
        "reference_bit_operations": reference_operations,
        "reference_bit_operations_mean": reference_operations / 8,
    }

    attacks = {
        "outlier_minimum_hamming_weight": {"successes": 0, "attempts": 8},
        "greedy_complete_lowest_edge": {"successes": 0, "attempts": 8},
        "random_restart_256_edges": {"successes": 0, "attempts": 8},
        "by_hand_raw_coordinate_xor": {"successes": 0, "attempts": 8},
    }
    for seed in range(8):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks["outlier_minimum_hamming_weight"]["successes"] += int(
            verify(inst, _attack_outlier_min_weight(inst))[0]
        )
        attacks["greedy_complete_lowest_edge"]["successes"] += int(
            verify(inst, _attack_greedy_edge_first(inst))[0]
        )
        attacks["by_hand_raw_coordinate_xor"]["successes"] += int(
            verify(inst, _attack_raw_xor(inst))[0]
        )
        attacks["random_restart_256_edges"]["successes"] += int(
            _random_restart(inst, random.Random(30_000 + seed)) is not None
        )
    all_attacks_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "GF(2) Gaussian elimination followed by three syndrome solves",
            "complexity": "O(r^2 d) exact bit operations",
            "wall_clock_sec": reference_wall,
            "wall_clock_sec_mean": reference_wall / 8,
            "operations": reference_operations,
            "operations_mean": reference_operations / 8,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_start = time.perf_counter()
    doubled = make_instance(seed=99, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_wall = time.perf_counter() - doubled_start
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["part_size"] > shipping["part_size"],
        "shipping_dimension": shipping["n"],
        "shipping_part_size": shipping["part_size"],
        "doubled_dimension": doubled["n"],
        "doubled_part_size_bits": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_wall,
    }

    invariance_checks = 0
    real_checks = 0
    distinct_keys = []
    for seed in range(20):
        # Canonicalization depends on the syndrome configuration, not on the
        # astronomical part size.  A smaller rank exercises exactly the same
        # relabeling group while keeping this proof-of-invariance inexpensive.
        inst = make_instance(
            seed=40_000 + seed, n=24, rank=10, target_count=15
        )
        original_key = canonical_key(inst)
        distinct_keys.append(original_key)
        relabel_rng = random.Random(50_000 + seed)
        q = list(range(inst["n"]))
        relabel_rng.shuffle(q)
        row_change = _random_invertible_rows(inst["rank"], relabel_rng)
        transforms = []
        transforms.append(_apply_coordinate_relabel(inst, q))
        transforms.append(_apply_syndrome_basis(inst, row_change))
        transforms.append(
            _apply_translation(inst, relabel_rng.getrandbits(inst["n"]), relabel_rng.getrandbits(inst["n"]))
        )
        transforms.append(
            _apply_target_translation(inst, relabel_rng.getrandbits(inst["n"]))
        )
        composed = _apply_coordinate_relabel(inst, q)
        composed = _apply_syndrome_basis(composed, row_change)
        composed = _apply_target_translation(
            composed, relabel_rng.getrandbits(inst["n"])
        )
        composed = _apply_translation(
            composed, relabel_rng.getrandbits(inst["n"]), relabel_rng.getrandbits(inst["n"])
        )
        composed = _swap_named_objects(composed)
        transforms.append(composed)
        for transformed in transforms:
            invariance_checks += int(canonical_key(transformed) == original_key)
            real_checks += int(verify(transformed, transformed["answer"])[0])
    shipping_key_start = time.perf_counter()
    shipping_keys = [
        canonical_key(
            make_instance(
                seed=60_000 + seed,
                **DIFFICULTY[SHIPPING_DIFFICULTY],
            )
        )
        for seed in range(20)
    ]
    shipping_key_seconds = time.perf_counter() - shipping_key_start
    report["G8_canonical_key"] = {
        "pass": (
            invariance_checks == 100
            and real_checks == 100
            and len(set(distinct_keys)) == 20
            and len(set(shipping_keys)) == 20
        ),
        "invariance_checks": invariance_checks,
        "invariance_expected": 100,
        "real_transformation_verify_checks": real_checks,
        "distinct_unrelated_keys": len(set(distinct_keys)),
        "unrelated_instances": 20,
        "shipping_distinct_unrelated_keys": len(set(shipping_keys)),
        "shipping_unrelated_instances": 20,
        "shipping_key_seconds": shipping_key_seconds,
        "symmetries": [
            "simultaneous bit-coordinate relabeling with carried witnesses",
            "arbitrary invertible syndrome-basis change",
            "kernel-preserving translations across the three parts",
            "one-part translations with the induced target-set translation",
            "composition with V1-name swap, V2/V3 swap, and target reordering",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_elements = _atom_count(shipping["answer"])
    answer_tokens = (answer_chars + 3) // 4
    intended_operations = 3 * shipping["n"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    difference = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "answer_bits": 3 * shipping["n"],
        "intended_route_operations": intended_operations,
        "diagnostic_recorded": all(arms[name]["attempts"] > 0 for name in arms),
        "oracle_evidence_status": G9_ORACLE_STATUS,
    }

    gate_rows = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(row.get("pass", False) for row in gate_rows)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
