"""Verified generator for affine equivalence of Dillon graph point sets.

The paper classifies Dillon hexanomials by CCZ equivalence.  A CCZ witness is
an affine permutation of the product space carrying one function graph to the
other.  Here both graphs are independently scrambled, and the requested
witness is exactly such an affine permutation.

Standard library only; importing this module performs no I/O.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
import hashlib
import json
import random
import re


DIFFICULTY = {
    "demo": {"n": 1},
    "easy": {"n": 2},
    "medium": {"n": 3},
    "hard": {"n": 4},
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Definition source: Section 1 fixes Dillon's functions over K=F_(q^2), q=2^n,
as F(x)=A*x^3+B*x^(q+1)+C*x^(2q+1)+D*x^(q+2)+E*x^(2q+2)+x^(3q).
Section 6 and its Computational Classification theorem classify graph sets by
complete CCZ-equivalence testing.  A CCZ equivalence is precisely an affine
permutation of K x K that maps one graph set onto the other, so the witness in
this module is a binary affine map and its checker merely substitutes every
point and compares two finite sets.

The paper does not prove that CCZ recovery is NP-hard.  The hardness basis here
is the general affine point-set/code-equivalence search problem: no polynomial
or closed-form recovery algorithm is known, while a witness is cheap to check.
The small q=2 and q=4 classifications in Section 6 are an easy regime to avoid:
the module uses growing n and independently uniform ambient scramblings rather
than looking up one of the paper's few listed CCZ representatives.

An earlier generator idea planted a nontrivial derivative collision directly.
It was rejected: for random conditioned coefficients, choosing a random
direction and taking the kernel of its binary derivative matrix succeeded about
half the time.  The shipped construction instead draws the requested affine
map uniformly before constructing either displayed set.  Source and target are
independently shuffled.  The outlier attack uses affine-invariant per-point
difference fingerprints; the greedy attack aligns deterministic affine bases;
and random restart aligns random affine bases.  All are exercised by selftest.
"""


# ---------------------------------------------------------------------------
# Binary polynomial and finite-field arithmetic


def _poly_mod(a: int, modulus: int) -> int:
    md = modulus.bit_length() - 1
    while a and a.bit_length() - 1 >= md:
        a ^= modulus << (a.bit_length() - 1 - md)
    return a


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_mod(a, b)
    return a


def _gf_mul(a: int, b: int, modulus: int, degree: int) -> int:
    out = 0
    while b:
        if b & 1:
            out ^= a
        b >>= 1
        a <<= 1
        if a & (1 << degree):
            a ^= modulus
    return out


def _gf_square(a: int, modulus: int, degree: int) -> int:
    return _gf_mul(a, a, modulus, degree)


def _is_irreducible(modulus: int, degree: int) -> bool:
    # A reducible degree-d polynomial has a factor of degree at most d//2.
    x = 2
    power = x
    for _ in range(1, degree // 2 + 1):
        power = _gf_square(power, modulus, degree)
        if _poly_gcd(power ^ x, modulus) != 1:
            return False
    power = x
    for _ in range(degree):
        power = _gf_square(power, modulus, degree)
    return power == x


@lru_cache(maxsize=None)
def _irreducible_polynomial(degree: int) -> int:
    if degree < 2:
        raise ValueError("field degree must be at least 2")
    for low in range(1, 1 << degree, 2):
        candidate = (1 << degree) | low
        if _is_irreducible(candidate, degree):
            return candidate
    raise RuntimeError("failed to find an irreducible polynomial")


def _frobenius(a: int, times: int, modulus: int, degree: int) -> int:
    for _ in range(times):
        a = _gf_square(a, modulus, degree)
    return a


def _dillon_value(x: int, coefficients: list[int], n: int,
                  modulus: int) -> int:
    """Evaluate the paper's normalized hexanomial in GF(2^(2n))."""
    field_degree = 2 * n
    a, b, c, d, e = coefficients
    x2 = _gf_square(x, modulus, field_degree)
    xq = _frobenius(x, n, modulus, field_degree)
    x2q = _gf_square(xq, modulus, field_degree)
    terms = (
        _gf_mul(a, _gf_mul(x, x2, modulus, field_degree), modulus, field_degree),
        _gf_mul(b, _gf_mul(x, xq, modulus, field_degree), modulus, field_degree),
        _gf_mul(c, _gf_mul(x, x2q, modulus, field_degree), modulus, field_degree),
        _gf_mul(d, _gf_mul(x2, xq, modulus, field_degree), modulus, field_degree),
        _gf_mul(e, _gf_mul(x2, x2q, modulus, field_degree), modulus, field_degree),
        _gf_mul(xq, x2q, modulus, field_degree),
    )
    out = 0
    for term in terms:
        out ^= term
    return out


# ---------------------------------------------------------------------------
# Binary affine maps.  Rows are displayed from the most significant output bit
# to the least; within a row the rightmost bit is input coordinate zero.


def _rank(vectors: list[int], width: int) -> int:
    basis = [0] * width
    rank = 0
    for original in vectors:
        v = original
        while v:
            pivot = v.bit_length() - 1
            if basis[pivot]:
                v ^= basis[pivot]
            else:
                basis[pivot] = v
                rank += 1
                break
    return rank


def _random_invertible(width: int, rng: random.Random) -> list[int]:
    # Rejection at each step samples a uniform ordered basis, hence uniform GL.
    rows: list[int] = []
    basis = [0] * width
    while len(rows) < width:
        original = rng.getrandbits(width)
        v = original
        while v:
            pivot = v.bit_length() - 1
            if basis[pivot]:
                v ^= basis[pivot]
            else:
                basis[pivot] = v
                rows.append(original)
                break
    return rows


def _linear_apply(rows: list[int], value: int, width: int) -> int:
    out = 0
    for row_index, row in enumerate(rows):
        if (row & value).bit_count() & 1:
            out |= 1 << (width - 1 - row_index)
    return out


def _affine_apply(rows: list[int], offset: int, value: int,
                  width: int) -> int:
    return _linear_apply(rows, value, width) ^ offset


def _matrix_compose(first: list[int], second: list[int],
                    width: int) -> list[int]:
    """Rows of first(second(x))."""
    out = []
    for functional in first:
        row = 0
        bits = functional
        while bits:
            low = bits & -bits
            coordinate = low.bit_length() - 1
            row ^= second[width - 1 - coordinate]
            bits ^= low
        out.append(row)
    return out


def _affine_compose(first: tuple[list[int], int],
                    second: tuple[list[int], int],
                    width: int) -> tuple[list[int], int]:
    """The affine map first after second."""
    a_rows, a_offset = first
    b_rows, b_offset = second
    return (_matrix_compose(a_rows, b_rows, width),
            _linear_apply(a_rows, b_offset, width) ^ a_offset)


def _matrix_inverse(rows: list[int], width: int) -> list[int]:
    # Convert to conventional row order: row k produces output bit k.
    augmented = [rows[width - 1 - k] | (1 << (width + k))
                 for k in range(width)]
    for column in range(width):
        pivot = next((i for i in range(column, width)
                      if (augmented[i] >> column) & 1), None)
        if pivot is None:
            raise ValueError("singular matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        for i in range(width):
            if i != column and ((augmented[i] >> column) & 1):
                augmented[i] ^= augmented[column]
    conventional = [(augmented[k] >> width) & ((1 << width) - 1)
                    for k in range(width)]
    return [conventional[width - 1 - k] for k in range(width)]


def _affine_inverse(affine: tuple[list[int], int],
                    width: int) -> tuple[list[int], int]:
    rows, offset = affine
    inverse = _matrix_inverse(rows, width)
    return inverse, _linear_apply(inverse, offset, width)


def _affine_span_rank(points: list[int], width: int) -> int:
    if not points:
        return 0
    anchor = points[0]
    return _rank([point ^ anchor for point in points[1:]], width)


# ---------------------------------------------------------------------------
# Required public interface


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample an affine witness first, then construct two point sets around it.

    ``n`` is the paper's exponent in q=2^n.  The Dillon function is over
    GF(2^(2n)); each displayed graph point has 4n bits.  Increasing n grows both
    the point set (by a factor four per step) and the affine search space.
    """
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameter(s): {unknown}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 10:
        raise ValueError("n must be an integer from 1 through 10")

    rng = random.Random(seed)
    field_degree = 2 * n
    ambient_width = 2 * field_degree
    field_size = 1 << field_degree
    ambient_size = 1 << ambient_width

    # G: the requested witness is sampled before any problem data.
    answer_rows = _random_invertible(ambient_width, rng)
    answer_offset = rng.randrange(ambient_size)

    modulus = _irreducible_polynomial(field_degree)
    graph = None
    coefficients = None
    # Full affine span prevents an underdetermined extension from making the
    # displayed recovery task artificially small.  n=1 cannot span four
    # dimensions with four points and is retained only for exact enumeration.
    for _ in range(256):
        coefficients = [rng.randrange(field_size) for _ in range(5)]
        graph = [x | (_dillon_value(x, coefficients, n, modulus) << field_degree)
                 for x in range(field_size)]
        if n == 1 or _affine_span_rank(graph, ambient_width) == ambient_width:
            break
    else:
        raise RuntimeError("could not obtain a full-span Dillon graph")

    source_rows = _random_invertible(ambient_width, rng)
    source_offset = rng.randrange(ambient_size)
    source = [_affine_apply(source_rows, source_offset, point, ambient_width)
              for point in graph]
    target = [_affine_apply(answer_rows, answer_offset, point, ambient_width)
              for point in source]
    rng.shuffle(source)
    rng.shuffle(target)

    return {
        "family": "dillon_ccz_affine_point_set_equivalence",
        "n": n,
        "field_degree": field_degree,
        "ambient_width": ambient_width,
        "field_modulus": modulus,
        "coefficients": coefficients,
        "source": source,
        "target": target,
        "answer": {"matrix": answer_rows, "offset": answer_offset},
    }


def _answer_json(answer: dict, width: int) -> str:
    payload = {
        "matrix": [format(row, f"0{width}b") for row in answer["matrix"]],
        "offset": format(answer["offset"], f"0{width}b"),
    }
    return json.dumps(payload, separators=(",", ":"))


def render(inst: dict) -> str:
    """Return the complete, self-contained affine-equivalence problem."""
    width = inst["ambient_width"]
    digits = (width + 3) // 4
    source_lines = "\n".join(format(point, f"0{digits}x")
                             for point in inst["source"])
    target_lines = "\n".join(format(point, f"0{digits}x")
                             for point in inst["target"])
    identity = {"matrix": [1 << (width - 1 - i) for i in range(width)],
                "offset": 0}
    example = _answer_json(identity, width)
    return f"""AFFINE EQUIVALENCE OF TWO BINARY POINT SETS

The ambient space is the {width}-dimensional vector space over GF(2).  A point
is written as exactly {digits} hexadecimal digits, with leading zeroes retained;
this is the ordinary {width}-bit binary encoding.  The two blocks below are
UNORDERED sets, each containing exactly {len(inst['source'])} distinct points.
Their line order has no meaning.

Find any affine permutation T(v) = M v XOR t that maps the entire SOURCE set
onto the entire TARGET set.  Here M is an invertible {width} by {width} binary
matrix and t is a {width}-bit vector.  All arithmetic is over GF(2): matrix
products use XOR for addition and AND/parity for scalar products.

Matrix convention: provide {width} binary row strings, top row first.  The top
row computes the leftmost (most significant) output bit.  Inside every row and
vector string, the rightmost bit is coordinate 0.  Thus an identity matrix is
listed from {'1' + '0' * (width - 1)} down to {'0' * (width - 1) + '1'}.
Order within the answer matters for matrix rows.  Repeated rows are allowed by
the syntax but make M singular and are invalid.

SOURCE
{source_lines}
END SOURCE

TARGET
{target_lines}
END TARGET

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly two fields: "matrix", a list of exactly {width} binary strings of length
{width}, and "offset", one binary string of length {width}.  Do not use 0x
prefixes.  The following shows the exact format (it is the identity example,
not necessarily a solution):
<answer>{example}</answer>
Output nothing else inside the tags.
"""


def parse_answer(text: str) -> object | None:
    """Extract the tagged JSON answer; tolerate prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\s*>(.*?)</answer\s*>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    body = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        body = fence.group(1).strip()
    try:
        raw = json.loads(body)
        if not isinstance(raw, dict) or set(raw) != {"matrix", "offset"}:
            return None
        matrix = raw["matrix"]
        offset = raw["offset"]
        if not isinstance(matrix, list) or not isinstance(offset, str):
            return None
        if any(not isinstance(row, str) or not row or
               re.fullmatch(r"[01]+", row) is None for row in matrix):
            return None
        if not offset or re.fullmatch(r"[01]+", offset) is None:
            return None
        return {"matrix": [int(row, 2) for row in matrix],
                "offset": int(offset, 2)}
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any affine witness without consulting the planted answer."""
    width = inst["ambient_width"]
    limit = 1 << width
    if not isinstance(answer, dict) or set(answer) != {"matrix", "offset"}:
        return False, "format: answer must contain exactly matrix and offset"
    matrix = answer["matrix"]
    offset = answer["offset"]
    if not isinstance(matrix, list) or len(matrix) != width:
        return False, f"shape: expected exactly {width} matrix rows"
    if any(not isinstance(row, int) or isinstance(row, bool) for row in matrix):
        return False, "type: every matrix row must be a binary integer"
    if any(row < 0 or row >= limit for row in matrix):
        return False, f"range: every matrix row must fit in {width} bits"
    if not isinstance(offset, int) or isinstance(offset, bool):
        return False, "type: offset must be a binary integer"
    if offset < 0 or offset >= limit:
        return False, f"range: offset must fit in {width} bits"
    if _rank(matrix, width) != width:
        return False, "matrix: rows are linearly dependent"

    target = set(inst["target"])
    image = set()
    for point in inst["source"]:
        mapped = _affine_apply(matrix, offset, point, width)
        if mapped not in target:
            return False, "mapping: image set differs from target"
        image.add(mapped)
    if image != target:
        return False, "mapping: image set differs from target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample an affine map after enforcing one free point correspondence.

    A solver can pick one source anchor and insist that its image be some target
    point without doing any search.  We therefore sample a uniform linear
    permutation, a uniform target image for the first displayed source point,
    and force the offset.  This is 2^d/|S| times stronger than uniform AGL and
    remains independent of the planted map.
    """
    width = inst["ambient_width"]
    matrix = _random_invertible(width, rng)
    target_image = inst["target"][rng.randrange(len(inst["target"]))]
    offset = target_image ^ _linear_apply(matrix, inst["source"][0], width)
    return {"matrix": matrix, "offset": offset}


def search_space(inst: dict) -> int | None:
    """The exact number |AGL(d,2)| of syntactically valid affine candidates."""
    width = inst["ambient_width"]
    linear = 1
    whole = 1 << width
    for i in range(width):
        linear *= whole - (1 << i)
    return whole * linear


def _all_invertible_matrices(width: int):
    rows: list[int] = []

    def visit():
        if len(rows) == width:
            yield list(rows)
            return
        for row in range(1, 1 << width):
            if _rank(rows + [row], width) == len(rows) + 1:
                rows.append(row)
                yield from visit()
                rows.pop()

    yield from visit()


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact answer count only below a fixed work cap."""
    space = search_space(inst)
    if space is None or space > 400_000:
        return None
    width = inst["ambient_width"]
    source = inst["source"]
    target = set(inst["target"])
    valid = 0
    for matrix in _all_invertible_matrices(width):
        linear_image = [_linear_apply(matrix, p, width) for p in source]
        for offset in range(1 << width):
            if {p ^ offset for p in linear_image} == target:
                valid += 1
    return valid


def _difference_spectrum(points: list[int], width: int) -> tuple:
    pair_counts: Counter[int] = Counter()
    for i, first in enumerate(points):
        for second in points[i + 1:]:
            pair_counts[first ^ second] += 1
    multiplicities = Counter(pair_counts.values())
    absent = (1 << width) - 1 - len(pair_counts)
    coarse = (len(points), width, _affine_span_rank(points, width), absent,
              tuple(sorted(multiplicities.items())))
    # The coarse differential spectrum can collide.  Refine it using the XOR
    # autocorrelation of a deterministic encoding of the multiplicity classes.
    # A linear relabelling preserves u XOR v and merely permutes all indices.
    if width <= 20:
        size = 1 << width
        # Canonical colour refinement on the additive group.  At each round,
        # XOR autocorrelations summarize how every colour class sits relative
        # to every vector.  Sorted signatures assign coordinate-free new IDs.
        initial = [(1, 0) if difference == 0
                   else (0, pair_counts.get(difference, 0))
                   for difference in range(size)]
        palette = {signature: i for i, signature in enumerate(sorted(set(initial)))}
        colors = [palette[signature] for signature in initial]
        rounds = 3 if width <= 12 else (2 if width <= 16 else 1)
        encodings = 3 if width <= 12 else (2 if width <= 16 else 1)
        for _ in range(rounds):
            correlations = []
            for power in range(1, encodings + 1):
                transformed = [(color + 1) ** power for color in colors]
                step = 1
                while step < size:
                    jump = step * 2
                    for start in range(0, size, jump):
                        for j in range(start, start + step):
                            left = transformed[j]
                            right = transformed[j + step]
                            transformed[j] = left + right
                            transformed[j + step] = left - right
                    step = jump
                transformed = [value * value for value in transformed]
                step = 1
                while step < size:
                    jump = step * 2
                    for start in range(0, size, jump):
                        for j in range(start, start + step):
                            left = transformed[j]
                            right = transformed[j + step]
                            transformed[j] = left + right
                            transformed[j + step] = left - right
                    step = jump
                correlations.append([value // size for value in transformed])
            signatures = [tuple([colors[v]] + [corr[v] for corr in correlations])
                          for v in range(size)]
            palette = {signature: i
                       for i, signature in enumerate(sorted(set(signatures)))}
            new_colors = [palette[signature] for signature in signatures]
            if new_colors == colors:
                break
            colors = new_colors
        refined = Counter(colors)
        digest = hashlib.sha256()
        for color, count in sorted(refined.items()):
            digest.update(f"{color}:{count};".encode("ascii"))
        refinement_digest = digest.hexdigest()

        # At the shipping width, add the complete distribution of intersections
        # with affine codimension-two flats.  Walsh values for each two-space in
        # the dual determine its four cell sizes; sorting those sizes removes
        # basis choice and translation signs.  This separates cases whose
        # one-dimensional spectra and additive colour refinement coincide.
        codimension_two_digest = "not-computed-width-over-12"
        if width <= 12:
            walsh = [0] * size
            for point in points:
                walsh[point] = 1
            step = 1
            while step < size:
                jump = step * 2
                for start in range(0, size, jump):
                    for j in range(start, start + step):
                        left = walsh[j]
                        right = walsh[j + step]
                        walsh[j] = left + right
                        walsh[j + step] = left - right
                step = jump
            cells = Counter()
            point_count = len(points)
            for first in range(1, size):
                for second in range(first + 1, size):
                    third = first ^ second
                    if third <= second:
                        continue
                    w1, w2, w3 = walsh[first], walsh[second], walsh[third]
                    profile = tuple(sorted((
                        (point_count + w1 + w2 + w3) // 4,
                        (point_count + w1 - w2 - w3) // 4,
                        (point_count - w1 + w2 - w3) // 4,
                        (point_count - w1 - w2 + w3) // 4,
                    )))
                    cells[profile] += 1
            cell_digest = hashlib.sha256()
            for profile, count in sorted(cells.items()):
                cell_digest.update((":".join(map(str, profile)) +
                                    f":{count};").encode("ascii"))
            codimension_two_digest = cell_digest.hexdigest()
        return coarse + (refinement_digest, codimension_two_digest)
    return coarse + ("coarse-only-width-over-20",)


def canonical_key(inst: dict) -> str:
    """Hash an affine-invariant differential spectrum, never the seed/render."""
    width = inst["ambient_width"]
    # Independent affine relabellings permute nonzero differences and preserve
    # their multiplicities.  Sorting the two spectra also makes side swapping
    # canonical.  This is a strong cheap invariant, not a complete canonical
    # form for affine point-set isomorphism (which is the search problem).
    # The generator guarantees the two sides are affine images, so their
    # complete structural signatures are identical.  Computing one side keeps
    # the codimension-two shipping invariant practical; swapping sides remains
    # invariant because the target has the same signature.
    spectrum = _difference_spectrum(inst["source"], width)
    encoded = json.dumps(spectrum, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase field dimension; each step quadruples the displayed set size."""
    n = params.get("n")
    if not isinstance(n, int) or n >= 7:
        return None
    return {"n": n + 1}


# ---------------------------------------------------------------------------
# Attacks and mandatory self-test


def _solve_full_rank(rows: list[int], rhs: list[int], width: int) -> int:
    augmented = [row | (bit << width) for row, bit in zip(rows, rhs)]
    pivot_row = 0
    pivot_for_column = [-1] * width
    for column in range(width):
        pivot = next((i for i in range(pivot_row, len(augmented))
                      if (augmented[i] >> column) & 1), None)
        if pivot is None:
            continue
        augmented[pivot_row], augmented[pivot] = augmented[pivot], augmented[pivot_row]
        for i in range(len(augmented)):
            if i != pivot_row and ((augmented[i] >> column) & 1):
                augmented[i] ^= augmented[pivot_row]
        pivot_for_column[column] = pivot_row
        pivot_row += 1
    if pivot_row != width:
        raise ValueError("basis is not full rank")
    solution = 0
    for column, row_index in enumerate(pivot_for_column):
        if (augmented[row_index] >> width) & 1:
            solution |= 1 << column
    return solution


def _ordered_affine_basis(points: list[int], width: int,
                          order: list[int]) -> list[int] | None:
    if not order:
        return None
    anchor = order[0]
    chosen = [anchor]
    differences: list[int] = []
    rank = 0
    for point in order[1:]:
        difference = point ^ anchor
        new_rank = _rank(differences + [difference], width)
        if new_rank > rank:
            differences.append(difference)
            chosen.append(point)
            rank = new_rank
            if rank == width:
                return chosen
    return None


def _map_from_bases(source_basis: list[int], target_basis: list[int],
                    width: int) -> dict:
    source_differences = [p ^ source_basis[0] for p in source_basis[1:]]
    target_differences = [p ^ target_basis[0] for p in target_basis[1:]]
    matrix = []
    for row_index in range(width):
        output_bit = width - 1 - row_index
        rhs = [(p >> output_bit) & 1 for p in target_differences]
        matrix.append(_solve_full_rank(source_differences, rhs, width))
    offset = target_basis[0] ^ _linear_apply(matrix, source_basis[0], width)
    return {"matrix": matrix, "offset": offset}


def _difference_counts(points: list[int]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for i, first in enumerate(points):
        for second in points[i + 1:]:
            counts[first ^ second] += 1
    return counts


def _local_fingerprints(points: list[int]) -> dict[int, tuple]:
    counts = _difference_counts(points)
    result = {}
    for first in points:
        profile = Counter(counts[first ^ second]
                          for second in points if second != first)
        result[first] = tuple(sorted(profile.items()))
    return result


def _basis_attack(inst: dict, fingerprint: bool) -> tuple[bool, str]:
    width = inst["ambient_width"]
    if fingerprint:
        source_fp = _local_fingerprints(inst["source"])
        target_fp = _local_fingerprints(inst["target"])
        source_order = sorted(inst["source"], key=lambda p: (source_fp[p], p))
        target_order = sorted(inst["target"], key=lambda p: (target_fp[p], p))
    else:
        source_order = sorted(inst["source"])
        target_order = sorted(inst["target"])
    source_basis = _ordered_affine_basis(inst["source"], width, source_order)
    target_basis = _ordered_affine_basis(inst["target"], width, target_order)
    if source_basis is None or target_basis is None:
        return False, "no full affine basis"
    candidate = _map_from_bases(source_basis, target_basis, width)
    return verify(inst, candidate)


def _random_restart_attack(inst: dict, rng: random.Random,
                           attempts: int = 32) -> tuple[bool, str]:
    width = inst["ambient_width"]
    for _ in range(attempts):
        source_order = list(inst["source"])
        target_order = list(inst["target"])
        rng.shuffle(source_order)
        rng.shuffle(target_order)
        source_basis = _ordered_affine_basis(inst["source"], width, source_order)
        target_basis = _ordered_affine_basis(inst["target"], width, target_order)
        if source_basis is None or target_basis is None:
            continue
        candidate = _map_from_bases(source_basis, target_basis, width)
        ok, reason = verify(inst, candidate)
        if ok:
            return True, reason
    return False, f"no solution in {attempts} independent basis alignments"


def _relabel_instance(inst: dict, source_affine: tuple[list[int], int],
                      target_affine: tuple[list[int], int],
                      reverse: bool = False) -> dict:
    width = inst["ambient_width"]
    result = dict(inst)
    result["source"] = [_affine_apply(*source_affine, p, width)
                        for p in inst["source"]]
    result["target"] = [_affine_apply(*target_affine, p, width)
                        for p in inst["target"]]
    if reverse:
        result["source"].reverse()
        result["target"].reverse()
    original = (list(inst["answer"]["matrix"]), inst["answer"]["offset"])
    carried = _affine_compose(
        target_affine,
        _affine_compose(original, _affine_inverse(source_affine, width), width),
        width,
    )
    result["answer"] = {"matrix": carried[0], "offset": carried[1]}
    return result


def selftest() -> dict:
    """Run G1--G8 and return a JSON-serializable measurement report."""
    report: dict[str, object] = {}

    # G1: every named preset, several independent seeds.
    planted_checks = 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {reason}")
            planted_checks += 1
    report["G1_planted_verifies"] = {"pass": True, "checks": planted_checks}

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    width = inst["ambient_width"]

    # G2: five named corruptions must fail for five distinct reasons.
    planted = inst["answer"]
    corruptions = {}
    empty = {}
    dropped = {"matrix": planted["matrix"][:-1], "offset": planted["offset"]}
    swapped_rows = list(planted["matrix"])
    swapped_rows[0], swapped_rows[1] = swapped_rows[1], swapped_rows[0]
    swapped = {"matrix": swapped_rows, "offset": planted["offset"]}
    duplicate_rows = list(planted["matrix"])
    duplicate_rows[1] = duplicate_rows[0]
    duplicate = {"matrix": duplicate_rows, "offset": planted["offset"]}
    out_of_range_rows = list(planted["matrix"])
    out_of_range_rows[0] = 1 << width
    out_of_range = {"matrix": out_of_range_rows, "offset": planted["offset"]}
    for name, candidate in (("empty", empty), ("drop", dropped),
                            ("swap", swapped), ("duplicate", duplicate),
                            ("out_of_range", out_of_range)):
        ok, reason = verify(inst, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        corruptions[name] = reason
    if len(set(corruptions.values())) != len(corruptions):
        raise AssertionError(f"G2 reasons not distinct: {corruptions}")
    report["G2_rejects_corruption"] = {
        "pass": True, "reasons": corruptions,
    }

    # G3: realistic prose and a markdown fence inside the required tags.
    response = ("I used affine difference invariants and checked the image.\n\n"
                "<answer>\n```json\n" + _answer_json(planted, width) +
                "\n```\n</answer>\nThis is my final result.")
    parsed = parse_answer(response)
    if parsed != planted:
        raise AssertionError("G3 realistic response did not round-trip")
    report["G3_round_trip"] = {"pass": True, "parsed": True}

    # G4: uniform over all already-invertible affine maps.
    guess_rng = random.Random(271828)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    measured = hits / total
    if measured >= 1e-6:
        raise AssertionError(f"G4 random guessing too successful: {hits}/{total}")
    report["G4_guess_resistance"] = {
        "pass": True,
        "sampling_prior": ("uniform GL linear part; offset forced so the first "
                           "source point maps to a uniform target point"),
        "hits": hits,
        "total": total,
        "measured_probability": measured,
        "naive_AGL_candidate_space": search_space(inst),
    }

    # G5: the only brute-force-feasible paper parameter q=2.
    tiny = make_instance(n=1, seed=11)
    exact = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    if exact is None:
        raise AssertionError("G5 tiny instance unexpectedly exceeded cap")
    fraction = exact / tiny_space
    if fraction >= 1e-3:
        raise AssertionError(f"G5 solution fraction not tiny: {fraction}")
    report["G5_sparse"] = {
        "pass": True, "n": 1, "valid_answers": exact,
        "candidate_space": tiny_space, "fraction": fraction,
        "larger_instances": "enumerate_all returns None above the work cap",
    }

    # G6: attacks tailored to ordering, per-point statistics, and restarts.
    attack_results = {
        "outlier_fingerprint": {"successes": 0, "instances": 0},
        "greedy_affine_basis": {"successes": 0, "instances": 0},
        "random_restart_32": {"successes": 0, "instances": 0,
                              "restarts_per_instance": 32},
    }
    for seed in range(8):
        attacked = make_instance(n=4, seed=9000 + seed)
        for name, result in (("outlier_fingerprint", _basis_attack(attacked, True)),
                             ("greedy_affine_basis", _basis_attack(attacked, False)),
                             ("random_restart_32",
                              _random_restart_attack(attacked,
                                                     random.Random(12000 + seed), 32))):
            attack_results[name]["instances"] += 1
            if result[0]:
                attack_results[name]["successes"] += 1
    if any(result["successes"] for result in attack_results.values()):
        raise AssertionError(f"G6 attack succeeded: {attack_results}")
    report["G6_adversary_panel"] = {"pass": True, "attacks": attack_results}

    # G7: doubling paper parameter n quadruples field bits' truth-table exponent.
    base = make_instance(n=2, seed=2026)
    doubled = make_instance(n=4, seed=2026)
    for label, candidate in (("base", base), ("doubled", doubled)):
        ok, reason = verify(candidate, candidate["answer"])
        if not ok:
            raise AssertionError(f"G7 {label}: {reason}")
    if len(doubled["source"]) <= len(base["source"]):
        raise AssertionError("G7 point count did not grow")
    if search_space(doubled) <= search_space(base):
        raise AssertionError("G7 affine search space did not grow")
    report["G7_scales"] = {
        "pass": True, "base_n": 2, "base_points": len(base["source"]),
        "doubled_n": 4, "doubled_points": len(doubled["source"]),
        "base_answer_bits": base["ambient_width"] ** 2 + base["ambient_width"],
        "doubled_answer_bits": doubled["ambient_width"] ** 2 + doubled["ambient_width"],
    }

    # G8: reorder, independently relabel both ambient spaces, swap sides, and
    # compose these operations.  Every carried witness is checked as a real map.
    invariance_checks = 0
    witness_checks = 0
    keys = []
    for seed in range(20):
        original = make_instance(seed=50000 + seed, **shipping)
        original_key = canonical_key(original)
        keys.append(original_key)

        reordered = dict(original)
        reordered["source"] = list(reversed(original["source"]))
        reordered["target"] = original["target"][1:] + original["target"][:1]
        if canonical_key(reordered) != original_key:
            raise AssertionError("G8 failed input-order invariance")
        invariance_checks += 1

        relabel_rng = random.Random(60000 + seed)
        source_affine = (_random_invertible(original["ambient_width"], relabel_rng),
                         relabel_rng.getrandbits(original["ambient_width"]))
        target_affine = (_random_invertible(original["ambient_width"], relabel_rng),
                         relabel_rng.getrandbits(original["ambient_width"]))
        relabelled = _relabel_instance(original, source_affine, target_affine)
        if canonical_key(relabelled) != original_key:
            raise AssertionError("G8 failed affine relabelling invariance")
        ok, reason = verify(relabelled, relabelled["answer"])
        if not ok:
            raise AssertionError(f"G8 carried relabelling is not real: {reason}")
        invariance_checks += 1
        witness_checks += 1

        swapped = dict(original)
        swapped["source"] = list(original["target"])
        swapped["target"] = list(original["source"])
        inverse = _affine_inverse((list(original["answer"]["matrix"]),
                                   original["answer"]["offset"]),
                                  original["ambient_width"])
        swapped["answer"] = {"matrix": inverse[0], "offset": inverse[1]}
        if canonical_key(swapped) != original_key:
            raise AssertionError("G8 failed side-swap invariance")
        ok, reason = verify(swapped, swapped["answer"])
        if not ok:
            raise AssertionError(f"G8 inverse witness is not real: {reason}")
        invariance_checks += 1
        witness_checks += 1

        composed = dict(relabelled)
        composed["source"] = list(reversed(relabelled["target"]))
        composed["target"] = relabelled["source"][2:] + relabelled["source"][:2]
        relabel_inverse = _affine_inverse((list(relabelled["answer"]["matrix"]),
                                           relabelled["answer"]["offset"]),
                                          original["ambient_width"])
        composed["answer"] = {"matrix": relabel_inverse[0],
                              "offset": relabel_inverse[1]}
        if canonical_key(composed) != original_key:
            raise AssertionError("G8 failed composed relabelling invariance")
        ok, reason = verify(composed, composed["answer"])
        if not ok:
            raise AssertionError(f"G8 composed witness is not real: {reason}")
        invariance_checks += 1
        witness_checks += 1

    distinct = len(set(keys))
    if distinct != len(keys):
        raise AssertionError(f"G8 structural keys collided: {distinct}/{len(keys)}")
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance_checks,
        "real_witness_checks": witness_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": len(keys),
        "invariant": ("differential spectrum, XOR colour refinement, and "
                      "shipping-width codimension-two intersection spectrum"),
        "complete_canonical_form": False,
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = True
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
