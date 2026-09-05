"""Verified problem generator based on Theorem 3.4 of arXiv:2509.05822.

The instance is a succinct finite Cayley graph.  A submitted set of coordinate
names defines a binary group character and therefore a two-colouring of every
vertex.  Instances are generated around a planted sparse character; constraints
are sampled only after that character is fixed.  Verification checks the
character on every displayed generator and checks the closed-neighbourhood
residue exactly, without enumerating the exponentially large vertex set.
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
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite Cayley graph on a binary vector space",
        "proper integer vertex colouring",
        "closed neighbourhood sums modulo 3",
        "sparse binary group character",
    ],
    "verification_operations": [
        "exact parity of finite set intersections",
        "exact modular addition",
        "symbolic verification of a group-character colouring",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize that almost all generator supports are rows of a hidden "
        "four-factor Kronecker product in the four-character coordinate names; "
        "otherwise solve the full binary linear system."
    ),
    "hardness_basis": (
        "Track B: in Theorem 3.4's j-regular regime with modulus 3 not dividing "
        "j+1 (shipping j=637), packed Gaussian elimination recovers the character "
        "in O(r*d^2), measured at 6,266,787 scalar bit operations and about 0.02 "
        "seconds for d=625; recognizing four Kronecker factors cuts this to 141 "
        "exact binary operations, but neither route is mechanically executable "
        "by a no-tool solver from the 637 displayed supports."
    ),
    "max_answer_tokens": 29,
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

# n is the binary-vector-space dimension.  At the four named rungs it is a
# fourth power q^4, so the hidden q-by-q factors grow while the answer stays at
# exactly 2^4 = 16 coordinate names.
DIFFICULTY = {
    "demo": {"n": 16, "extras": 3},
    "easy": {"n": 81, "extras": 6},
    "medium": {"n": 256, "extras": 9},
    "hard": {"n": 625, "extras": 12},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The generator-incidence matrix has a four-factor Kronecker symmetry in "
    "the four-character coordinate names."
)
PLACEBO_HINT = (
    "The generator-incidence data rewards careful attention to the coordinate "
    "names and parity conditions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly 16 distinct coordinate-name strings, in strict "
        "lexicographic order; it is the support of a binary group character."
    ),
    "bounds": {
        "support_size": 16,
        "coordinate_name_length": 4,
        "max_ambient_coordinates": 10000,
        "ordered": True,
        "repetitions": False,
    },
}

NOTES = (
    "Section 2 fixes proper integer colourings and closed neighbourhood sums. "
    "Theorem 3.3 says a nonproper modular labelling can be combined with an "
    "ordinary proper colouring; Theorem 3.4 is the decisive easy-case result: "
    "for a j-regular graph and modulus n not dividing j+1, the new chromatic "
    "number equals the ordinary chromatic number. Therefore this family is "
    "Track B, not Track A. The generated Cayley graph is regular and the answer "
    "is a symbolic two-colouring x -> 1+3<c,x>. A generic solver obtains c by "
    "Gaussian elimination, while construction composes four planted factor "
    "identities B_i c_i=1 and adds only odd XORs of valid rows. Per-coordinate "
    "frequency extremes, parity-gain greedy selection, marginal Cartesian "
    "pairs, and sparse random restarts are all tested."
)

# Updated only from the three independent harden.py runs.  Until then G9 is
# intentionally reported as pending rather than silently claimed to pass.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_SUPPORT_SIZE = 16
_MODULUS = 3
_FACTOR_COUNT = 4
_ENUMERATION_CAP = 200_000
_DECODE_CACHE = {"instance": None, "stamp": None, "decoded": None}


def _is_plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _rank(rows, width):
    basis = {}
    for value in rows:
        row = value
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = row
                break
            row ^= basis[pivot]
    return len(basis)


def _factor_order(dimension):
    q = 1
    while (q + 1) ** _FACTOR_COUNT <= dimension:
        q += 1
    return q


def _core_words(q):
    symbols = _ALPHABET[:q]
    return ["".join(chars) for chars in itertools.product(symbols, repeat=4)]


def _coordinate_names(dimension, q):
    core = _core_words(q)
    padding = dimension - len(core)
    width = max(4, len(str(max(0, padding - 1))))
    return core + [f"p{index:0{width}d}" for index in range(padding)]


def _sample_factor(q, rng):
    planted_positions = sorted(rng.sample(range(q), 2))
    planted = sum(1 << index for index in planted_positions)
    eligible = [
        row for row in range(1, 1 << q)
        if (row & planted).bit_count() % 2 == 1
    ]
    # Rejection sampling assembles constraints around the already-known answer;
    # it never searches for the certificate.
    for _ in range(10_000):
        rows = rng.sample(eligible, q)
        if _rank(rows, q) == q:
            return planted_positions, rows
    raise RuntimeError("could not sample an invertible planted factor")


def _tensor_row_mask(factor_rows, row_digits, q):
    choices = []
    for axis, row_index in enumerate(row_digits):
        row = factor_rows[axis][row_index]
        choices.append([digit for digit in range(q) if (row >> digit) & 1])
    mask = 0
    for digits in itertools.product(*choices):
        index = (((digits[0] * q + digits[1]) * q + digits[2]) * q + digits[3])
        mask |= 1 << index
    return mask


def _mask_to_support(mask, coordinates):
    support = []
    while mask:
        least = mask & -mask
        index = least.bit_length() - 1
        support.append(coordinates[index])
        mask ^= least
    return support


def _decode_instance(inst):
    if not isinstance(inst, dict):
        return None
    dimension = inst.get("dimension")
    q = inst.get("factor_order")
    modulus = inst.get("modulus")
    coordinates = inst.get("coordinates")
    generators = inst.get("generators")
    stamp = (
        id(inst), dimension, q, modulus,
        id(coordinates), len(coordinates) if isinstance(coordinates, list) else -1,
        id(generators), len(generators) if isinstance(generators, list) else -1,
    )
    # Generated instances are immutable values.  Identity caching keeps the
    # 200,000-candidate density measurement from reparsing 24,000 support names
    # per candidate; a different instance or replaced top-level list misses.
    if (
        _DECODE_CACHE["instance"] is inst
        and _DECODE_CACHE["stamp"] == stamp
    ):
        return _DECODE_CACHE["decoded"]
    if not _is_plain_int(dimension) or not 16 <= dimension <= 10_000:
        return None
    if not _is_plain_int(q) or q != _factor_order(dimension) or not 2 <= q <= 10:
        return None
    if modulus != _MODULUS:
        return None
    if not isinstance(coordinates, list) or len(coordinates) != dimension:
        return None
    if any(not isinstance(name, str) or not name for name in coordinates):
        return None
    if coordinates != sorted(coordinates) or len(set(coordinates)) != dimension:
        return None
    if not isinstance(generators, list) or len(generators) < dimension:
        return None
    index = {name: position for position, name in enumerate(coordinates)}
    row_masks = []
    seen_rows = set()
    for support in generators:
        if not isinstance(support, list) or not support:
            return None
        if any(not isinstance(name, str) or name not in index for name in support):
            return None
        if support != sorted(support) or len(set(support)) != len(support):
            return None
        mask = 0
        for name in support:
            mask |= 1 << index[name]
        if mask in seen_rows:
            return None
        seen_rows.add(mask)
        row_masks.append(mask)
    if (len(row_masks) + 1) % modulus == 0:
        return None
    decoded = dimension, q, modulus, coordinates, index, row_masks
    _DECODE_CACHE.update({"instance": inst, "stamp": stamp, "decoded": decoded})
    return decoded


def make_instance(n, seed=0, **params):
    """Inverse-generate a sparse character and its compatible Cayley graph."""
    extras = params.pop("extras", 12)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_plain_int(n) or not 16 <= n <= 10_000:
        raise ValueError("n must be an integer from 16 through 10000")
    if not _is_plain_int(extras) or not 0 <= extras <= 64:
        raise ValueError("extras must be an integer from 0 through 64")

    q = _factor_order(n)
    if not 2 <= q <= 10:
        raise ValueError("n gives an unsupported factor order")
    rng = random.Random(seed)
    coordinates = _coordinate_names(n, q)

    factor_rows = []
    factor_answers = []
    for _ in range(_FACTOR_COUNT):
        answer_positions, rows = _sample_factor(q, rng)
        factor_answers.append(answer_positions)
        factor_rows.append(rows)

    planted_words = sorted(
        "".join(_ALPHABET[digit] for digit in digits)
        for digits in itertools.product(*factor_answers)
    )
    coordinate_index = {name: index for index, name in enumerate(coordinates)}
    planted_mask = sum(1 << coordinate_index[name] for name in planted_words)

    basis_rows = [
        _tensor_row_mask(factor_rows, row_digits, q)
        for row_digits in itertools.product(range(q), repeat=_FACTOR_COUNT)
    ]
    # If n lies between fourth powers, add sparse independent rows that force
    # every padding coefficient to zero while retaining odd planted parity.
    for pad_index in range(q ** _FACTOR_COUNT, n):
        planted_index = coordinate_index[rng.choice(planted_words)]
        basis_rows.append((1 << pad_index) | (1 << planted_index))
    if len(basis_rows) != n or _rank(basis_rows, n) != n:
        raise AssertionError("construction did not produce a basis")
    if any((row & planted_mask).bit_count() % 2 != 1 for row in basis_rows):
        raise AssertionError("basis row violates planted character")

    all_rows = list(basis_rows)
    seen = set(all_rows)
    odd_sizes = [size for size in range(3, min(15, n) + 1, 2)]
    effective_extras = extras
    if (n + effective_extras + 1) % _MODULUS == 0:
        effective_extras += 1
    for _ in range(effective_extras):
        for _attempt in range(10_000):
            chosen = rng.sample(basis_rows, rng.choice(odd_sizes))
            row = 0
            for part in chosen:
                row ^= part
            if row and row not in seen:
                seen.add(row)
                all_rows.append(row)
                break
        else:
            raise RuntimeError("could not create a distinct redundant generator")
    rng.shuffle(all_rows)

    generators = [_mask_to_support(row, coordinates) for row in all_rows]
    return {
        "dimension": n,
        "factor_order": q,
        "modulus": _MODULUS,
        "coordinate_length": 4,
        "coordinates": coordinates,
        "generators": generators,
        "answer": planted_words,
    }


def render(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return "Malformed instance."
    dimension, q, modulus, coordinates, _index, row_masks = decoded
    lines = []
    for number, mask in enumerate(row_masks):
        support = _mask_to_support(mask, coordinates)
        lines.append(f"g{number}: " + " ".join(support))

    statement = f"""Find a symbolic proper colouring with a closed nonzero local modular constraint.

There are d={dimension} coordinate names, listed below in lexicographic order. A graph vertex is a binary function x from these names to {{0,1}}. Equivalently, x is a length-{dimension} bit vector whose positions have these names.

Coordinates:
{' '.join(coordinates)}

Each generator line below is a nonempty set of coordinate names. Two vertices x and y are adjacent exactly when y is obtained from x by flipping all bits whose names occur on one generator line. The displayed generator sets are distinct, so this defines a finite simple undirected Cayley graph. Its degree is r={len(row_masks)}.

For a proposed set C of coordinate names define

  c_C(x) = (sum of x(t) over t in C) mod 2,
  L_C(x) = 1 + {modulus}*c_C(x).

Thus L_C labels every graph vertex by either 1 or {modulus + 1}. A labelling is proper when adjacent vertices have different integer labels. The closed neighbourhood of x consists of x together with all r adjacent vertices. Its local sum is the sum of L_C over that closed neighbourhood.

Find exactly {_SUPPORT_SIZE} coordinate names C such that L_C is proper and every closed-neighbourhood sum is nonzero modulo {modulus}. The instance is promised to have such a C. The names must be distinct and submitted in strict lexicographic order. This ordered list is only the finite symbolic certificate; do not enumerate the graph's 2^{dimension} vertices.

Generator supports (order has no significance):
{chr(10).join(lines)}

Return a JSON list of exactly {_SUPPORT_SIZE} quoted coordinate-name strings. Use only names from the Coordinates line, use no repeats, and sort them strictly increasingly.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the required syntax: <answer>{json.dumps(coordinates[:_SUPPORT_SIZE], separators=(',', ':'))}</answer>
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
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        pieces = [piece.strip().strip("`'\"") for piece in body.split(",")]
        if not pieces or any(not re.fullmatch(r"[0-9A-Za-z]+", piece) for piece in pieces):
            return None
        value = pieces
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        return None
    return value


def verify(inst, answer):
    decoded = _decode_instance(inst)
    if decoded is None:
        return False, "malformed instance"
    dimension, _q, modulus, coordinates, index, row_masks = decoded
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != _SUPPORT_SIZE:
        return False, f"answer has {len(answer)} names; expected exactly {_SUPPORT_SIZE}"
    if any(not isinstance(name, str) for name in answer):
        return False, "every answer entry must be a coordinate-name string"
    if any(name not in index for name in answer):
        return False, "answer contains an unknown coordinate name"
    if len(set(answer)) != len(answer):
        return False, "answer contains a repeated coordinate name"
    if answer != sorted(answer):
        return False, "coordinate names are not in strict lexicographic order"

    answer_mask = 0
    for name in answer:
        answer_mask |= 1 << index[name]
    for generator_index, row in enumerate(row_masks):
        if (row & answer_mask).bit_count() % 2 != 1:
            return False, f"generator g{generator_index} has even intersection with C"

    # Every generator flips c_C, so every edge receives labels 1 and 4.  The
    # graph is regular; modulo 3 every label is 1, hence every closed sum is
    # degree+1.  This is an executable symbolic check, not an oracle appeal.
    residue = (len(row_masks) + 1) % modulus
    if residue == 0:
        return False, "closed-neighbourhood label sum is zero modulo 3"
    if dimension != len(coordinates):
        return False, "coordinate dimension mismatch"
    return True, "ok"


def random_candidate(inst, rng):
    decoded = _decode_instance(inst)
    if decoded is None or not hasattr(rng, "sample"):
        return []
    coordinates = decoded[3]
    return sorted(rng.sample(coordinates, _SUPPORT_SIZE))


def search_space(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return None
    return math.comb(decoded[0], _SUPPORT_SIZE)


def enumerate_all(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return None
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.combinations(decoded[3], _SUPPORT_SIZE):
        count += int(verify(inst, list(candidate))[0])
    return count


def _dependency_weight_enumerator(row_masks):
    """Weight enumerator of all linear dependencies among generator rows."""
    basis = {}
    relations = []
    for row_number, original in enumerate(row_masks):
        row = original
        provenance = 1 << row_number
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (row, provenance)
                break
            known_row, known_provenance = basis[pivot]
            row ^= known_row
            provenance ^= known_provenance
        if not row:
            relations.append(provenance)
    codewords = [0]
    for relation in relations:
        codewords += [word ^ relation for word in codewords]
    histogram = [0] * (len(row_masks) + 1)
    for word in codewords:
        histogram[word.bit_count()] += 1
    return tuple(histogram)


def canonical_key(inst):
    """Invariant under coordinate renaming and generator-line reordering.

    The dependency-code weight enumerator is a strong cheap invariant, not a
    complete graph-isomorphism canonical form; that limitation is documented in
    README.md.
    """
    decoded = _decode_instance(inst)
    if decoded is None:
        return "malformed"
    dimension, _q, modulus, _coordinates, _index, row_masks = decoded
    invariant = [
        dimension,
        len(row_masks),
        modulus,
        _dependency_weight_enumerator(row_masks),
    ]
    payload = json.dumps(invariant, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    extras = params.get("extras", 12)
    if not _is_plain_int(n) or not _is_plain_int(extras):
        return None
    # Grow the explicit linear-system haystack while the 16-name certificate is
    # fixed.  Multiples of three preserve the nonzero degree+1 residue.
    next_extras = extras + 12
    if next_extras <= 60:
        return {"n": n, "extras": next_extras}
    next_n = min(10_000, max(n + 1, int(n * 1.35)))
    if next_n > n:
        return {"n": next_n, "extras": 12}
    return None


def _gaussian_reference(inst):
    """Solve the displayed GF(2) system with exact packed elimination."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return None, {"rank": 0, "row_xors": 0, "bit_operations": 0}
    dimension, _q, _modulus, coordinates, _index, row_masks = decoded
    rows = [row | (1 << dimension) for row in row_masks]
    pivot_rows = []
    rank = 0
    row_xors = 0
    pivot_tests = 0
    for column in range(dimension):
        pivot = None
        for candidate in range(rank, len(rows)):
            pivot_tests += 1
            if (rows[candidate] >> column) & 1:
                pivot = candidate
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for target in range(rank + 1, len(rows)):
            if (rows[target] >> column) & 1:
                rows[target] ^= rows[rank]
                row_xors += 1
        pivot_rows.append((column, rank))
        rank += 1
        if rank == dimension:
            break
    if rank != dimension:
        return None, {
            "rank": rank,
            "row_xors": row_xors,
            "bit_operations": row_xors * (dimension + 1),
            "pivot_tests": pivot_tests,
        }
    for row in rows[rank:]:
        if (row & ((1 << dimension) - 1)) == 0 and ((row >> dimension) & 1):
            return None, {
                "rank": rank,
                "row_xors": row_xors,
                "bit_operations": row_xors * (dimension + 1),
                "pivot_tests": pivot_tests,
            }

    solution = 0
    back_substitution_ops = 0
    for column, row_number in reversed(pivot_rows):
        coefficient_bits = rows[row_number] & ((1 << dimension) - 1)
        parity = (coefficient_bits & solution).bit_count() & 1
        rhs = (rows[row_number] >> dimension) & 1
        bit = rhs ^ parity
        back_substitution_ops += coefficient_bits.bit_count() + 1
        if bit:
            solution |= 1 << column
    answer = _mask_to_support(solution, coordinates)
    return answer, {
        "rank": rank,
        "row_xors": row_xors,
        "pivot_tests": pivot_tests,
        "bit_operations": row_xors * (dimension + 1) + back_substitution_ops,
    }


def _is_cartesian_support(support, q):
    if not support or any(len(word) != 4 or "p" in word for word in support):
        return None
    projections = [sorted({word[axis] for word in support}) for axis in range(4)]
    product_size = math.prod(len(values) for values in projections)
    if product_size != len(support):
        return None
    expected = {
        "".join(chars) for chars in itertools.product(*projections)
    }
    if expected != set(support):
        return None
    return projections


def _solve_factor(row_subsets, symbols):
    """Solve Bx=1; count scalar GF(2) additions in row operations."""
    q = len(symbols)
    symbol_index = {symbol: index for index, symbol in enumerate(symbols)}
    rows = []
    for subset in row_subsets:
        mask = sum(1 << symbol_index[symbol] for symbol in subset)
        rows.append(mask | (1 << q))
    rank = 0
    pivots = []
    scalar_ops = 0
    for column in range(q):
        pivot = next((r for r in range(rank, q) if (rows[r] >> column) & 1), None)
        if pivot is None:
            return None, scalar_ops
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for target in range(rank + 1, q):
            if (rows[target] >> column) & 1:
                rows[target] ^= rows[rank]
                scalar_ops += q + 1
        pivots.append((column, rank))
        rank += 1
    solution = 0
    for column, row_number in reversed(pivots):
        coefficient_mask = rows[row_number] & ((1 << q) - 1)
        contributing = coefficient_mask & solution
        parity = contributing.bit_count() & 1
        scalar_ops += contributing.bit_count() + 1
        if ((rows[row_number] >> q) & 1) ^ parity:
            solution |= 1 << column
    return [symbols[i] for i in range(q) if (solution >> i) & 1], scalar_ops


def _compact_recover(inst):
    """Recover four small factors from Cartesian row projections."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return None, {"exact_binary_operations": 0}
    _dimension, q, _modulus, _coordinates, _index, row_masks = decoded
    symbols = list(_ALPHABET[:q])
    projection_counts = [dict() for _ in range(4)]
    for mask in row_masks:
        support = _mask_to_support(mask, decoded[3])
        projections = _is_cartesian_support(support, q)
        if projections is None:
            continue
        for axis, subset in enumerate(projections):
            key = tuple(subset)
            projection_counts[axis][key] = projection_counts[axis].get(key, 0) + 1
    factor_solutions = []
    operations = 0
    for axis in range(4):
        frequent = sorted(
            projection_counts[axis].items(), key=lambda item: (-item[1], item[0])
        )[:q]
        if len(frequent) != q:
            return None, {"exact_binary_operations": operations}
        row_subsets = [list(key) for key, _count in frequent]
        solution, used = _solve_factor(row_subsets, symbols)
        operations += used
        if solution is None or len(solution) != 2:
            return None, {"exact_binary_operations": operations}
        factor_solutions.append(solution)
    answer = sorted("".join(chars) for chars in itertools.product(*factor_solutions))
    return answer, {"exact_binary_operations": operations}


def _column_incidence(decoded):
    dimension, _q, _modulus, _coordinates, _index, row_masks = decoded
    columns = [0] * dimension
    for row_number, row in enumerate(row_masks):
        remaining = row
        while remaining:
            least = remaining & -remaining
            column = least.bit_length() - 1
            columns[column] |= 1 << row_number
            remaining ^= least
    return columns


def _attack_candidates(inst, seed):
    decoded = _decode_instance(inst)
    if decoded is None:
        return {name: [] for name in (
            "outlier_column_frequency_extremes",
            "greedy_parity_gain_16",
            "cartesian_marginal_pairs",
            "random_restart_256_sparse_characters",
        )}
    dimension, q, _modulus, coordinates, index, row_masks = decoded
    columns = _column_incidence(decoded)
    frequencies = [column.bit_count() for column in columns]
    low = sorted(range(dimension), key=lambda i: (frequencies[i], coordinates[i]))[:16]
    high = sorted(range(dimension), key=lambda i: (-frequencies[i], coordinates[i]))[:16]
    outlier = [
        sorted(coordinates[i] for i in low),
        sorted(coordinates[i] for i in high),
    ]

    selected = []
    parity_rows = 0
    available = set(range(dimension))
    for _ in range(16):
        choice = max(
            available,
            key=lambda i: ((parity_rows ^ columns[i]).bit_count(), -i),
        )
        selected.append(choice)
        parity_rows ^= columns[choice]
        available.remove(choice)
    greedy = sorted(coordinates[i] for i in selected)

    # A plausible no-tool ansatz: use per-digit marginal column frequencies but
    # do not reconstruct and solve the actual factor equations.
    core_words = [word for word in coordinates if len(word) == 4 and "p" not in word]
    marginal_scores = [{symbol: 0 for symbol in _ALPHABET[:q]} for _ in range(4)]
    for word in core_words:
        score = frequencies[index[word]]
        for axis, symbol in enumerate(word):
            marginal_scores[axis][symbol] += score
    cartesian = []
    for reverse in (False, True):
        pairs = []
        for scores in marginal_scores:
            ordered = sorted(scores, key=lambda symbol: (scores[symbol], symbol), reverse=reverse)
            pairs.append(sorted(ordered[:2]))
        cartesian.append(sorted("".join(chars) for chars in itertools.product(*pairs)))

    rng = random.Random(seed ^ 0x250905822)
    restarts = [sorted(rng.sample(coordinates, 16)) for _ in range(256)]
    return {
        "outlier_column_frequency_extremes": outlier,
        "greedy_parity_gain_16": [greedy],
        "cartesian_marginal_pairs": cartesian,
        "random_restart_256_sparse_characters": restarts,
    }


def _relabel_instance(inst, seed, reorder_rows=True):
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    coordinates = decoded[3]
    rng = random.Random(seed)
    images = list(coordinates)
    rng.shuffle(images)
    mapping = dict(zip(coordinates, images))
    out = dict(inst)
    out["answer"] = sorted(mapping[name] for name in inst["answer"])
    out["generators"] = [
        sorted(mapping[name] for name in support) for support in inst["generators"]
    ]
    if reorder_rows:
        rng.shuffle(out["generators"])
    return out


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = list(answer)
    duplicate[1] = duplicate[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": answer[:-1] + ["NOT_A_COORDINATE"],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The sparse character has the following support.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe names are in lexicographic order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x250905822)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(inst),
        "space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_column_frequency_extremes",
        "greedy_parity_gain_16",
        "cartesian_marginal_pairs",
        "random_restart_256_sparse_characters",
    ]
    attack_successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_counts = []
    compact_successes = 0
    compact_counts = []
    candidate_panel_seconds = 0.0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        begin = time.perf_counter()
        candidates = _attack_candidates(trial, seed)
        candidate_panel_seconds += time.perf_counter() - begin
        for name in attack_names:
            begin = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - begin
            attack_successes[name] += int(won)

        begin = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - begin
        reference_counts.append(counts)
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])

        compact, compact_count = _compact_recover(trial)
        compact_counts.append(compact_count["exact_binary_operations"])
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": attack_successes[name],
            "attempts": 8,
            "wall_clock_sec": round(
                (attack_seconds[name]
                 + (candidate_panel_seconds if name == "greedy_parity_gain_16" else 0.0))
                / 8,
                6,
            ),
        }
        for name in attack_names
    }
    reference = {
        "name": "packed exact Gaussian elimination over GF(2)",
        "complexity": "O(r*d^2) scalar bit operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": max(count["bit_operations"] for count in reference_counts),
        "row_xors": max(count["row_xors"] for count in reference_counts),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in attack_successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "recover and solve four Kronecker factors",
            "operations": max(compact_counts),
            "solves": f"{compact_successes}/8",
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and all_failed
        and reference_successes == 8
        and enumerate_all(demo) == 1,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_estimate": guess_fraction,
        "shipping_unique_solution_count_by_full_rank": 1,
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_attack": "greedy_parity_gain_16",
        "baseline_attack_wall_clock_sec": round(
            (attack_seconds["greedy_parity_gain_16"] + candidate_panel_seconds) / 8,
            6,
        ),
        "baseline_attack_iterations": 16 * inst["dimension"],
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    begin = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - begin
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [params["n"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["dimension"] == 2 * shipping["n"]
        and len(doubled["answer"]) == len(inst["answer"])
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["dimension"],
        "answer_elements_at_both_sizes": len(doubled["answer"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
    }

    invariance_passed = 0
    carried_passed = 0
    expected = 0
    for seed in range(20):
        original = make_instance(seed=1000 + seed, **shipping)
        original_key = canonical_key(original)
        # Coordinate renaming, row reordering, and their composition are the
        # explicit-representation symmetries of this sparse-character task.
        coordinate_only = _relabel_instance(original, 3000 + seed, reorder_rows=False)
        row_only = dict(original)
        row_only["generators"] = list(original["generators"])
        random.Random(4000 + seed).shuffle(row_only["generators"])
        composed = _relabel_instance(original, 5000 + seed, reorder_rows=True)
        for transformed in (coordinate_only, row_only, composed):
            expected += 1
            invariance_passed += int(canonical_key(transformed) == original_key)
            carried_passed += int(verify(transformed, transformed["answer"])[0])
    unrelated_keys = [
        canonical_key(make_instance(seed=9000 + seed, **shipping))
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": invariance_passed == expected
        and carried_passed == expected
        and len(set(unrelated_keys)) == 20,
        "invariance_checks_passed": invariance_passed,
        "invariance_checks_expected": expected,
        "carried_witness_checks_passed": carried_passed,
        "carried_witness_checks_expected": expected,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "invariant": "generator-dependency-code weight enumerator",
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(answer)
    intended_operations = max(compact_counts)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and answer_tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
