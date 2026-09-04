"""Verified Track-B generator for reduced lexicographic Groebner bases.

The q-Fractional Groebner Basis Problem in Section 2.1 of arXiv:1605.04472
specializes at q=1 to ordinary Groebner-basis computation. This module
inverse-generates a reduced basis over Q, then replaces it by an invertible
set of dense quadratic generators. The emitted distribution is deliberately
not claimed hard in the paper's worst-case sense: exact elimination solves it.
Its no-tool shortcut is a row-permutation-invariant diagonal-plus-rank-one
decomposition concealed in the expanded polynomial coefficients.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals, sparse_poly
except ImportError:                 # pragma: no cover - documented fallback
    exact_matrices = rationals = sparse_poly = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "dense quadratic polynomials over Q",
        "polynomial ideal",
        "reduced lexicographic Groebner basis",
    ],
    "verification_operations": [
        "exact rational polynomial reduction",
        "Buchberger S-polynomial criterion",
        "exact rational matrix rank",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "In each expanded polynomial, separate the repeated quadratic "
        "coefficient from its one exceptional coefficient and sum the "
        "normalized equations to isolate their shared weighted total."
    ),
    "hardness_basis": (
        "Track B: exact Gauss-Jordan elimination solves the 32-by-32 rational "
        "coefficient system in O(k^3); at the shipping preset it measured 8,752 "
        "mean exact operations (10,152 maximum) and 0.0033--0.0069 mean wall-clock "
        "seconds across two runs, "
        "while the row-pattern invariant uses exactly 7*k=224 exact operations."
    ),
    "max_answer_tokens": 291,
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

_DENOMS = [101, 103, 107, 109, 113, 127, 131, 137]
_RESIDUE_CACHE = {}
_LANGUAGE_CACHE = {}

DIFFICULTY: dict = {
    "demo": {"n": 4, "variables": 3, "mix_bits": 2,
             "denominators": [2, 3]},
    "easy": {"n": 64, "variables": 32, "mix_bits": 10,
             "denominators": _DENOMS},
    "medium": {"n": 88, "variables": 32, "mix_bits": 12,
               "denominators": _DENOMS},
    "hard": {"n": 112, "variables": 32, "mix_bits": 14,
             "denominators": _DENOMS},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "In each row isolate the lone coefficient differing from the repeated "
    "background, normalize that equation, and sum all rows to solve the shared total."
)
PLACEBO_HINT: str = (
    "Keep every rational in lowest terms and check the variable order carefully "
    "before committing to the final coefficient table."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON object containing k ordered monic two-term polynomials "
        "x_j^2-a_j as coefficient pairs [[-p,q],[1,1]], where a_j=p/q, "
        "2^(n-1)<=p<2^n, q is in the instance denominator list, gcd(p,q)=1, "
        "and the a_j are pairwise distinct."
    ),
    "bounds": {
        "polynomials": "k=variables",
        "terms_per_polynomial": 2,
        "max_degree": 2,
        "numerator_bits": "n",
        "denominators": "instance denominators",
        "pairwise_distinct": True,
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = (
    "Section 2.1, Definition 1 fixes the q-Fractional Groebner Basis output and "
    "explicitly identifies q=1 with the traditional problem. Section 2.1, "
    "Theorem 2 proves worst-case robust hardness for q>7/10 at degree at most 3; "
    "Section 2.2, Theorem 4 strengthens the degree bound to 2 for q>4/5. Those "
    "theorems do not establish average-case hardness for this inverse-generated "
    "distribution, and their three-variable-per-polynomial restriction is not "
    "claimed here. The Introduction names Buchberger's algorithm, while Sections "
    "2.1 and 2.2 explain that a lex basis permits efficient successive elimination. "
    "For this special family the certificate-producing algorithm is even simpler: "
    "exact Gaussian elimination after treating x_j^2 as linear unknowns. Therefore "
    "the honest claim is Track B. Generation samples the rational reduced basis "
    "first and applies an invertible matrix with one exceptional coefficient per "
    "row. Expanding and randomly reordering the generators hides the shared-total "
    "invariant. The outlier, diagonal-only, zero-total, prior-mean, and random-restart "
    "attacks are tested explicitly; exact elimination is disclosed separately and "
    "is expected to succeed."
)


def _require_int(name, value, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _validate_params(n, variables, mix_bits, denominators):
    _require_int("n", n, 2)
    _require_int("variables", variables, 3)
    _require_int("mix_bits", mix_bits, 2)
    if variables > 42:
        raise ValueError("variables must be at most 42 so the compact route stays under 300 operations")
    if not isinstance(denominators, (list, tuple)) or not denominators:
        raise ValueError("denominators must be a nonempty list")
    if any(isinstance(q, bool) or not isinstance(q, int) or q <= 1
           for q in denominators):
        raise ValueError("every allowed denominator must be an integer greater than 1")
    if len(set(denominators)) != len(denominators):
        raise ValueError("allowed denominators must be distinct")
    if max(denominators) > 10_000:
        raise ValueError("allowed denominators must be at most 10000")
    if _language_size_raw(n, denominators) < variables:
        raise ValueError("the rational language is too small for pairwise-distinct constants")


def _rat_to_json(value):
    value = Fraction(value)
    if rationals is not None:
        return rationals.to_json(value)
    return [value.numerator, value.denominator]


def _rat_from_json(pair):
    if rationals is not None:
        return rationals.from_json(pair)
    if (not isinstance(pair, (list, tuple)) or len(pair) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in pair)
            or pair[1] == 0):
        raise ValueError("not a rational pair")
    return Fraction(pair[0], pair[1])


def _bounds(n):
    return 1 << (n - 1), (1 << n) - 1


def _allowed_residues(q):
    if q not in _RESIDUE_CACHE:
        _RESIDUE_CACHE[q] = [r for r in range(q) if math.gcd(r, q) == 1]
    return _RESIDUE_CACHE[q]


def _language_descriptor(n, q):
    key = (n, q)
    if key in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[key]
    lo, hi = _bounds(n)
    first_end = min(hi + 1, (lo // q + 1) * q)
    pre = [p for p in range(lo, first_end) if math.gcd(p, q) == 1]
    start = first_end
    residues = _allowed_residues(q)
    full = max(0, (hi - start + 1) // q)
    tail_start = start + full * q
    tail = [p for p in range(tail_start, hi + 1) if math.gcd(p, q) == 1]
    result = (pre, start, residues, full, tail,
              len(pre) + full * len(residues) + len(tail))
    _LANGUAGE_CACHE[key] = result
    return result


def _count_for_denominator(n, q):
    return _language_descriptor(n, q)[-1]


def _language_size_raw(n, denominators):
    return sum(_count_for_denominator(n, q) for q in denominators)


def _nth_numerator(n, q, index):
    """The zero-based index-th p in the n-bit interval with gcd(p,q)=1."""
    pre, start, residues, full, tail, count = _language_descriptor(n, q)
    if not 0 <= index < count:
        raise IndexError("rational-language index out of range")
    if index < len(pre):
        return pre[index]
    index -= len(pre)
    block_count = full * len(residues)
    if index < block_count:
        block, offset = divmod(index, len(residues))
        return start + block * q + residues[offset]
    index -= block_count
    return tail[index]


def _fraction_at(inst, index):
    for q in inst["denominators"]:
        count = _count_for_denominator(inst["n"], q)
        if index < count:
            return Fraction(_nth_numerator(inst["n"], q, index), q)
        index -= count
    raise IndexError("rational-language index out of range")


def _sample_distinct_indices(rng, population, count):
    chosen, result = set(), []
    while len(result) < count:
        value = rng.randrange(population)
        if value not in chosen:
            chosen.add(value)
            result.append(value)
    rng.shuffle(result)
    return result


def _basis_from_values(values):
    return {"basis": [[_rat_to_json(-value), [1, 1]] for value in values]}


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a reduced basis, then apply an invertible mixing.

    Write b_j=x_j^2-a_j and S=sum_j b_j. Before its rows are shuffled, the
    generated set is f_j=u_j*S+d_j*b_j. Its coefficient matrix is
    diag(d)+u*1^T, whose determinant is prod(d_j)*(1+sum(u_j/d_j)) and is
    therefore nonzero because u_j,d_j are positive. Thus <F>=<B> without
    solving the emitted instance.
    """
    variables = params.get("variables", 32)
    mix_bits = params.get("mix_bits", 10)
    denominators = list(params.get("denominators", _DENOMS))
    _validate_params(n, variables, mix_bits, denominators)
    _require_int("seed", seed)
    rng = random.Random(seed)

    shell = {"n": n, "variables": variables, "mix_bits": mix_bits,
             "denominators": denominators}
    population = _language_size_raw(n, denominators)
    indices = _sample_distinct_indices(rng, population, variables)
    values = [_fraction_at(shell, i) for i in indices]
    shared = sum(values, Fraction(0))

    low_mix, high_mix = 1 << (mix_bits - 1), (1 << mix_bits) - 1
    rows = []
    for p in range(variables):
        background = rng.randint(low_mix, high_mix)
        diagonal = rng.randint(low_mix, high_mix)
        coeffs = [background] * variables
        coeffs[p] += diagonal
        constant = background * shared + diagonal * values[p]
        rows.append({"coefficients": coeffs,
                     "constant": _rat_to_json(constant)})
    rng.shuffle(rows)                 # generators are a set; row order is noise
    return {**shell, "rows": rows, "answer": _basis_from_values(values)}


def _format_rat(pair):
    value = _rat_from_json(pair)
    return (str(value.numerator) if value.denominator == 1
            else f"{value.numerator}/{value.denominator}")


def render(inst) -> str:
    """Render the complete exact polynomial problem and output contract."""
    k = inst["variables"]
    lines = [
        "Compute the unique reduced lexicographic Groebner basis of an ideal over Q.",
        "",
        "Definitions:",
        "- Q is the field of rational numbers.",
        f"- Work in Q[x1,...,x{k}] with lexicographic order "
        + " > ".join(f"x{j}" for j in range(1, k + 1)) + ".",
        "- A polynomial's leading monomial is its largest monomial in that order.",
        "- A finite set G is a Groebner basis of I if G generates I and its leading",
        "  monomials generate the leading-monomial ideal of I.",
        "- G is reduced if every member is monic and no non-leading monomial in one",
        "  member is divisible by another member's leading monomial.",
        "",
        "Input encoding:",
        f"Each of the following {k} rows is [q1,...,q{k}] ; c and denotes",
        f"    q1*x1^2 + ... + q{k}*x{k}^2 - c.",
        "All coefficients are exact. Fractions use num/den with positive denominator.",
        "The input ideal I is generated by all rows; row order has no meaning.",
        "",
    ]
    for number, row in enumerate(inst["rows"], 1):
        coeffs = ",".join(str(x) for x in row["coefficients"])
        lines.append(f"{number}: [{coeffs}] ; {_format_rat(row['constant'])}")
    denoms = ",".join(str(q) for q in inst["denominators"])
    lo, hi = _bounds(inst["n"])
    lines.extend([
        "",
        "It is guaranteed that the unique reduced basis is",
        f"    {{x1^2-a_1, x2^2-a_2, ..., x{k}^2-a_{k}}}.",
        f"Each a_j is a positive reduced fraction p/q with {lo} <= p <= {hi},",
        f"q in [{denoms}], and the a_j are pairwise distinct.",
        "",
        "Output one JSON object with key \"basis\". Its j-th entry (1-indexed) must",
        "be [[-p,q],[1,1]], the exact [constant, x_j^2] coefficient list for",
        "x_j^2-p/q. Rational pairs must be in lowest terms with positive denominator.",
        f"The basis array must have exactly {k} entries; order matters and repeats are forbidden.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as that JSON object.",
        "Shape example for k=2 only: <answer>{\"basis\":[[[-8,3],[1,1]],[[-11,2],[1,1]]]}</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Extract a JSON basis object from tags, fences, whitespace, or prose."""
    if not isinstance(text, str):
        return None
    try:
        tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                            flags=re.IGNORECASE | re.DOTALL)
        regions = tagged[::-1] if tagged else [text]
        decoder = json.JSONDecoder()
        for region in regions:
            clean = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", region.strip(),
                           flags=re.IGNORECASE | re.DOTALL)
            for match in re.finditer(r"\{", clean):
                try:
                    obj, _ = decoder.raw_decode(clean[match.start():])
                except (ValueError, TypeError):
                    continue
                if isinstance(obj, dict) and isinstance(obj.get("basis"), list):
                    return obj
        return None
    except Exception:               # model output is untrusted
        return None


def _decode_basis(inst, answer):
    if not isinstance(answer, dict) or set(answer) != {"basis"}:
        return None, "answer must be one JSON object with only the key 'basis'"
    basis = answer["basis"]
    if not isinstance(basis, list):
        return None, "basis must be a JSON array"
    if len(basis) == 0:
        return None, "basis array is empty"
    k = inst["variables"]
    if len(basis) != k:
        return None, f"wrong basis length: expected {k} polynomials"
    lo, hi = _bounds(inst["n"])
    allowed = set(inst["denominators"])
    values = []
    for j, poly in enumerate(basis, 1):
        if not isinstance(poly, list) or len(poly) != 2:
            return None, f"basis polynomial {j} must contain exactly two coefficient pairs"
        try:
            constant = _rat_from_json(poly[0])
            leading = _rat_from_json(poly[1])
        except (TypeError, ValueError, ZeroDivisionError):
            return None, f"basis polynomial {j} contains a malformed rational pair"
        if poly[1] != [1, 1] or leading != 1:
            return None, f"basis polynomial {j} is not monic"
        if constant >= 0:
            return None, f"basis polynomial {j} must have a negative constant coefficient"
        value = -constant
        if poly[0] != [-value.numerator, value.denominator]:
            return None, f"basis polynomial {j} is not encoded in canonical lowest terms"
        if value.denominator not in allowed:
            return None, f"basis polynomial {j} uses a denominator outside the allowed list"
        if not lo <= value.numerator <= hi:
            return None, f"basis polynomial {j} numerator is outside the inclusive n-bit range"
        values.append(value)
    if len(set(values)) != k:
        return None, "basis constants must be pairwise distinct"
    return values, "ok"


def _matrix_rank_q(matrix):
    if exact_matrices is not None:
        return exact_matrices.rank(exact_matrices.matrix(matrix))
    a = [[Fraction(x) for x in row] for row in matrix]
    m, n = len(a), len(a[0])
    rank = 0
    for col in range(n):
        pivot = next((r for r in range(rank, m) if a[r][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        pv = a[rank][col]
        a[rank] = [x / pv for x in a[rank]]
        for r in range(rank + 1, m):
            if a[r][col]:
                factor = a[r][col]
                a[r] = [x - factor * y for x, y in zip(a[r], a[rank])]
        rank += 1
        if rank == m:
            break
    return rank


def _validate_rows(inst):
    rows = inst.get("rows")
    k = inst.get("variables")
    if not isinstance(rows, list) or not isinstance(k, int) or len(rows) != k:
        return None, "instance must contain exactly one generator row per variable"
    matrix, constants = [], []
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != {"coefficients", "constant"}:
            return None, f"instance row {i} is malformed"
        coeffs = row["coefficients"]
        if (not isinstance(coeffs, list) or len(coeffs) != k
                or any(isinstance(x, bool) or not isinstance(x, int) for x in coeffs)):
            return None, f"instance row {i} has malformed quadratic coefficients"
        try:
            constant = _rat_from_json(row["constant"])
        except (TypeError, ValueError, ZeroDivisionError):
            return None, f"instance row {i} has a malformed constant"
        matrix.append(coeffs)
        constants.append(constant)
    return (matrix, constants), "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Check the proposed reduced basis exactly without reading inst['answer']."""
    values, why = _decode_basis(inst, answer)
    if values is None:
        return False, why
    decoded, why = _validate_rows(inst)
    if decoded is None:
        return False, why
    matrix, constants = decoded

    # Reduce every input polynomial by x_j^2-a_j. A common denominator turns
    # this into exact integer arithmetic and keeps the 200k-sample gate cheap.
    common = math.lcm(*(inst["denominators"]))
    scaled_values = [a.numerator * (common // a.denominator) for a in values]
    for i, (row, constant) in enumerate(zip(matrix, constants), 1):
        lhs = sum(q * a for q, a in zip(row, scaled_values))
        if common % constant.denominator:
            return False, f"instance row {i} constant denominator is incompatible"
        rhs = constant.numerator * (common // constant.denominator)
        if lhs != rhs:
            remainder = Fraction(lhs - rhs, common)
            return False, f"input polynomial {i} has nonzero exact remainder {remainder}"

    # Pairwise-coprime leading monomials make every S-polynomial reduce to zero.
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            if values[j] * values[i] - values[i] * values[j] != 0:
                return False, f"S-polynomial ({i + 1},{j + 1}) did not reduce to zero"

    # Vanishing remainders give <F> subset <G>; full coefficient rank writes
    # each x_j^2-a_j as a Q-linear combination of F, proving reverse containment.
    if _matrix_rank_q(matrix) != inst["variables"]:
        return False, "input generators do not have full exact coefficient rank"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the bounded, distinct, reduced rational basis language."""
    population = _language_size_raw(inst["n"], inst["denominators"])
    indices = _sample_distinct_indices(rng, population, inst["variables"])
    return _basis_from_values(_fraction_at(inst, i) for i in indices)


def search_space(inst) -> int | None:
    """Ordered falling factorial of the exact rational coefficient language."""
    population = _language_size_raw(inst["n"], inst["denominators"])
    k = inst["variables"]
    return math.prod(range(population - k + 1, population + 1))


def enumerate_all(inst) -> int | None:
    """Count valid answers exactly when at most 100,000 candidates are needed."""
    space = search_space(inst)
    if space > 100_000:
        return None
    population = _language_size_raw(inst["n"], inst["denominators"])
    count = 0
    for indices in itertools.permutations(range(population), inst["variables"]):
        candidate = _basis_from_values(_fraction_at(inst, i) for i in indices)
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _reference_gaussian(inst):
    """Generic exact Gauss-Jordan solve, with a transparent arithmetic count."""
    decoded, why = _validate_rows(inst)
    if decoded is None:
        return None, 0
    matrix, constants = decoded
    aug = [[Fraction(x) for x in row] + [c]
           for row, c in zip(matrix, constants)]
    k = inst["variables"]
    pivot_row = 0
    pivots = {}
    operations = 0
    for col in range(k):
        pivot = next((r for r in range(pivot_row, k) if aug[r][col]), None)
        if pivot is None:
            continue
        aug[pivot_row], aug[pivot] = aug[pivot], aug[pivot_row]
        pv = aug[pivot_row][col]
        for j in range(col, k + 1):
            aug[pivot_row][j] /= pv
            operations += 1
        for r in range(k):
            if r == pivot_row or not aug[r][col]:
                continue
            factor = aug[r][col]
            for j in range(col, k + 1):
                aug[r][j] -= factor * aug[pivot_row][j]
                operations += 2
        pivots[col] = pivot_row
        pivot_row += 1
    if len(pivots) != k:
        return None, operations
    values = [aug[pivots[col]][k] for col in range(k)]
    for row, constant in zip(matrix, constants):
        total = sum((Fraction(q) * a for q, a in zip(row, values)), Fraction(0))
        operations += 2 * k - 1
        if total != constant:
            return None, operations
    return _basis_from_values(values), operations


def canonical_key(inst) -> str:
    """Canonicalize the ideal by its solved reduced basis, modulo variable names."""
    answer, _ = _reference_gaussian(inst)
    if answer is None:
        decoded, _ = _validate_rows(inst)
        payload = decoded if decoded is not None else repr(inst.get("rows"))
    else:
        values, _ = _decode_basis(inst, answer)
        payload = sorted((value.numerator, value.denominator) for value in values)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Raise coefficient bit complexity while keeping the 32-polynomial answer fixed."""
    p = dict(params)
    next_n = int(p.get("n", 64)) + 16
    # Measured over 100 seeds: 144 bits uses at most 1,931 characters; 160
    # bits uses 2,085, beyond the 2,000-character shipping cap.
    if next_n > 144:
        return "cap_bound"
    p["n"] = next_n
    p["mix_bits"] = int(p.get("mix_bits", 10)) + 2
    return p


def _pattern_rows(inst):
    """Return (u,d,p,c) by variable, or None if the hidden pattern is absent."""
    out = [None] * inst["variables"]
    for row in inst["rows"]:
        counts = {}
        for value in row["coefficients"]:
            counts[value] = counts.get(value, 0) + 1
        background, multiplicity = max(counts.items(), key=lambda item: item[1])
        exceptions = [(j, value) for j, value in enumerate(row["coefficients"])
                      if value != background]
        if multiplicity != inst["variables"] - 1 or len(exceptions) != 1:
            return None
        p, exceptional = exceptions[0]
        out[p] = (background, exceptional - background, p,
                  _rat_from_json(row["constant"]))
    return out if all(item is not None for item in out) else None


def _nearest_language_value(inst, estimate, used):
    lo, hi = _bounds(inst["n"])
    best = None
    for q in inst["denominators"]:
        center = int(estimate * q)
        for delta in range(0, 4 + len(used)):
            for p in ({center - delta, center + delta} if delta else {center}):
                p = min(hi, max(lo, p))
                if math.gcd(p, q) != 1:
                    continue
                value = Fraction(p, q)
                if value in used:
                    continue
                score = abs(value - estimate)
                if best is None or score < best[0]:
                    best = (score, value)
        if best is not None and best[0] == 0:
            break
    if best is None:
        for index in range(_language_size_raw(inst["n"], inst["denominators"])):
            value = _fraction_at(inst, index)
            if value not in used:
                return value
    return best[1]


def _candidate_from_estimates(inst, estimates):
    used, values = set(), []
    for estimate in estimates:
        value = _nearest_language_value(inst, Fraction(estimate), used)
        used.add(value)
        values.append(value)
    return _basis_from_values(values)


def _attack_zero_shared(inst):
    return _candidate_from_estimates(
        inst, [c / d for u, d, p, c in _pattern_rows(inst)])


def _attack_diagonal_only(inst):
    return _candidate_from_estimates(
        inst, [c / (u + d) for u, d, p, c in _pattern_rows(inst)])


def _attack_prior_mean(inst):
    lo, hi = _bounds(inst["n"])
    average_denominator = Fraction(sum(inst["denominators"]),
                                   len(inst["denominators"]))
    mean_value = Fraction(lo + hi, 2) / average_denominator
    guessed_sum = inst["variables"] * mean_value
    return _candidate_from_estimates(
        inst, [(c - u * guessed_sum) / d
               for u, d, p, c in _pattern_rows(inst)])


def _attack_rhs_rank(inst):
    pattern = _pattern_rows(inst)
    scores = [c for u, d, p, c in pattern]
    order = sorted(range(len(scores)), key=lambda j: scores[j])
    population = _language_size_raw(inst["n"], inst["denominators"])
    values = [None] * len(scores)
    for rank, p in enumerate(order):
        index = (rank + 1) * population // (len(scores) + 1)
        values[p] = _fraction_at(inst, min(index, population - 1))
    return _basis_from_values(values)


def _relabel_instance(inst, old_to_new, reorder_rows=False, row_scale=None):
    k = inst["variables"]
    out = {key: value for key, value in inst.items()
           if key not in ("rows", "answer")}
    rows = []
    for row in inst["rows"]:
        coeffs = [0] * k
        for old, new in enumerate(old_to_new):
            coeffs[new] = row["coefficients"][old]
        constant = _rat_from_json(row["constant"])
        if row_scale is not None:
            coeffs = [row_scale * value for value in coeffs]
            constant *= row_scale
        rows.append({"coefficients": coeffs,
                     "constant": _rat_to_json(constant)})
    if reorder_rows:
        rows.reverse()
    out["rows"] = rows
    values, _ = _decode_basis(inst, inst["answer"])
    carried = [None] * k
    for old, new in enumerate(old_to_new):
        carried[new] = values[old]
    out["answer"] = _basis_from_values(carried)
    return out


def _answer_metrics(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    basis = answer.get("basis", []) if isinstance(answer, dict) else []
    return len(encoded), math.ceil(len(encoded) / 4), 2 * len(basis)


def selftest() -> dict:
    """Run all mandatory G1--G9 checks and return JSON-native evidence."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures}

    inst = make_instance(seed=12345, **shipping_params)
    planted = inst["answer"]
    basis = planted["basis"]
    lo, hi = _bounds(inst["n"])
    corruptions = {
        "drop": {"basis": basis[:-1]},
        "swap": {"basis": [basis[1], basis[0]] + basis[2:]},
        "duplicate": {"basis": basis[:-1] + [basis[0]]},
        "empty": {"basis": []},
        "out_of_range": {
            "basis": [[[-(hi + 1), inst["denominators"][0]], [1, 1]]] + basis[1:]},
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in rejected.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    body = json.dumps(planted, separators=(",", ":"))
    realistic = ("I reduced every input polynomial exactly.\n```json\n<answer>"
                 + body + "</answer>\n```\nThe tagged object is final.")
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("prose without JSON") is None
    report["G3_round_trip"] = {
        "pass": parsed == planted and garbage_none,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": garbage_none,
    }

    guess_rng = random.Random(0x160504472)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": search_space(inst),
        "sampler": "uniform ordered sample without replacement from the exact bounded rational language",
    }

    attack_fns = {
        "outlier_rhs_rank": _attack_rhs_rank,
        "greedy_diagonal_only": _attack_diagonal_only,
        "random_restart_256": None,
        "by_hand_zero_shared_total": _attack_zero_shared,
        "by_hand_prior_mean_total": _attack_prior_mean,
    }
    attack_results = {name: {"successes": 0, "attempts": 8}
                      for name in attack_fns}
    ref_times, ref_operations = [], []
    ref_successes = 0
    for seed in range(800, 808):
        attack_inst = make_instance(seed=seed, **shipping_params)
        for name, fn in attack_fns.items():
            if fn is None:
                solved = False
                rr = random.Random(seed ^ 0xA55A)
                for _ in range(256):
                    if verify(attack_inst, random_candidate(attack_inst, rr))[0]:
                        solved = True
                        break
            else:
                solved = verify(attack_inst, fn(attack_inst))[0]
            attack_results[name]["successes"] += int(solved)
        t0 = time.perf_counter()
        recovered, operations = _reference_gaussian(attack_inst)
        ref_times.append(time.perf_counter() - t0)
        ref_operations.append(operations)
        ref_successes += int(recovered is not None
                             and verify(attack_inst, recovered)[0])
    all_failed = all(entry["successes"] == 0
                     for entry in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact Gauss-Jordan elimination on the quadratic coefficient matrix",
            "complexity": "O(k^3) exact rational operations",
            "wall_clock_sec_mean": sum(ref_times) / len(ref_times),
            "wall_clock_sec_max": max(ref_times),
            "operations_mean": sum(ref_operations) // len(ref_operations),
            "operations_max": max(ref_operations),
            "attempts": 8,
            "successes": ref_successes,
            "solves": f"{ref_successes}/8, as expected for Track B",
        },
    }

    report["G5_density_and_baseline"] = {
        "pass": guess_total >= 200_000 and guess_probability < 1e-6
        and ref_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_probability,
        "known_solution_count": 1,
        "shipping_candidate_space": search_space(inst),
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])),
        "baseline_wall_seconds_mean": sum(ref_times) / len(ref_times),
        "baseline_exact_operations_mean": sum(ref_operations) // len(ref_operations),
        "baseline_pivots": shipping_params["variables"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_answer, doubled_operations = _reference_gaussian(doubled)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_answer is not None
        and len(doubled["answer"]["basis"]) == len(planted["basis"]),
        "shipping_numerator_bits": shipping_params["n"],
        "doubled_numerator_bits": doubled_params["n"],
        "answer_polynomials_shipping": len(planted["basis"]),
        "answer_polynomials_doubled": len(doubled["answer"]["basis"]),
        "doubled_reference_operations": doubled_operations,
        "planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    witness_checks = 0
    keys = []
    g8_ok = True
    for seed in range(20):
        base = make_instance(seed=2000 + seed, **shipping_params)
        key = canonical_key(base)
        keys.append(key)
        perm = list(range(base["variables"]))
        random.Random(9000 + seed).shuffle(perm)
        identity = list(range(base["variables"]))
        transforms = [
            _relabel_instance(base, identity, reorder_rows=True),
            _relabel_instance(base, perm),
            _relabel_instance(base, perm, reorder_rows=True),
            _relabel_instance(base, identity, reorder_rows=True, row_scale=2),
        ]
        for transformed in transforms:
            invariant_checks += 1
            witness_checks += 1
            g8_ok &= canonical_key(transformed) == key
            g8_ok &= verify(transformed, transformed["answer"])[0]
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": bool(g8_ok and distinct == 20),
        "invariance_checks": invariant_checks,
        "real_transformation_witness_checks": witness_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "transformations": [
            "generator-row permutation",
            "variable renaming",
            "composed row permutation and variable renaming",
            "generator-row permutation with nonzero row scaling",
        ],
    }

    metric_samples = [_answer_metrics(
        make_instance(seed=seed, **shipping_params)["answer"])
        for seed in range(20)]
    answer_chars = max(item[0] for item in metric_samples)
    answer_tokens = max(item[1] for item in metric_samples)
    answer_elements = max(item[2] for item in metric_samples)
    intended_operations = 7 * shipping_params["variables"]
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
