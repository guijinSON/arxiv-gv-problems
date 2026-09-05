"""Verified sparse-spectracone generator for arXiv:2409.07682.

The paper proves that every Walsh matrix is an ideal Perron similarity: its
spectracone is exactly the conical hull of its rows.  This module samples a
sparse nonnegative row combination first, relabels rows and columns by the
paper's equivalence transformations, and publishes the resulting spectral
vector.  The answer is the sparse rational row-cone decomposition.

All arithmetic is integral (hence exact).  Generation never inverts the
published Walsh transform to discover the answer.
"""

from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# gvlib is standard-library-only.  Keep the documented fallback because this
# module is also run directly from its results directory by harden.py.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import rationals
except ImportError:  # pragma: no cover - exercised only outside the repository
    rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "Walsh Perron similarity over Q",
        "spectral vector over Q",
        "sparse nonnegative row-cone decomposition",
    ],
    "verification_operations": [
        "exact parity evaluation of Walsh entries",
        "exact rational coefficient validation",
        "exact expansion and equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undo the row and column relabellings and inspect Walsh characters on "
        "the binary unit columns; without that change of variables one executes "
        "a full inverse Walsh transform."
    ),
    "hardness_basis": (
        "Track B: Theorem 4.29 and equation (4.7) make the coefficient witness "
        "computable by a fast Walsh-Hadamard inversion in O(n log n); at the "
        "provisional shipping preset n=1024 it takes 13,319 counted exact "
        "operations and 0.013314 seconds on average over eight seeds, while "
        "the unit-character route uses at most 161 exact operations and is "
        "not apparent without undoing both relabellings."
    ),
    "max_answer_tokens": 39,
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
    "demo": {"n": 16, "terms": 3, "rounds": 1, "weight_bits": 6},
    "easy": {"n": 1024, "terms": 7, "rounds": 1, "weight_bits": 32},
    "medium": {"n": 2048, "terms": 7, "rounds": 1, "weight_bits": 40},
    "hard": {"n": 4096, "terms": 7, "rounds": 2, "weight_bits": 48},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "A Walsh character evaluated on binary unit columns exposes the bits of "
    "its row label after the two displayed relabellings are undone."
)
PLACEBO_HINT = (
    "Keep the indexing conventions and all exact integer signs organized while "
    "assembling the requested sparse certificate."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A sparse rational row-cone certificate with exactly k terms, written "
        "in increasing published-weight order as [[row,[num,den]],...].  Rows "
        "are distinct 0-based integers below n; each rational is reduced, "
        "positive, and has at most weight_bits bits in numerator and denominator."
    ),
    "bounds": {
        "n_terms": "instance k (3 for demo, 7 otherwise)",
        "row_min": 0,
        "row_max": "n-1",
        "coefficient_bits": "weight_bits",
        "coefficients": "the k published positive rational weights, each once",
        "candidate_count": "n!/(n-k)!",
    },
}


NOTES = (
    "Section 4.4 fixes the native objects: Theorem 4.29 says the Walsh matrix "
    "H_(2^d) is ideal, so its spectracone equals its row cone, and equation "
    "(4.7) identifies the corresponding nonnegative Klein realizing matrices. "
    "Section 4.1, especially Theorem 4.10, licenses row and column permutation "
    "equivalences.  Section 7 gives the easy side: Theorem 7.4 is an explicit "
    "Fourier feasibility test, so a Track A claim would be false; the analogous "
    "fast Walsh-Hadamard inversion recovers every coefficient in O(n log n). "
    "The generator instead samples distinct support rows and positive rational "
    "weights first and composes their certified rays.  Uniform support sampling "
    "removes row outliers; affine relabellings defeat unmasked unit-column reads; "
    "comparable dissociated weights defeat dominant-sign peeling; and random "
    "restart is audited from the exact structure-aware certificate language."
)


# Filled with script-owned evidence after the three oracle runs.  Until then the
# explicit zeros are placeholders, not a claim made by selftest.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value):
    return value > 0 and value & (value - 1) == 0


def _validate_params(n, terms, rounds, weight_bits):
    for name, value in (
        ("n", n),
        ("terms", terms),
        ("rounds", rounds),
        ("weight_bits", weight_bits),
    ):
        if not _plain_int(value):
            raise ValueError(f"{name} must be an integer")
    # The declared demo is deliberately the smallest supported member of the
    # family, as required by the difficulty contract.
    if n < 16 or not _is_power_of_two(n):
        raise ValueError("n must be a power of two at least 16")
    if terms < 3 or terms >= n:
        raise ValueError("terms must satisfy 3 <= terms < n")
    if rounds < 1:
        raise ValueError("rounds must be positive")
    if weight_bits < 6:
        raise ValueError("weight_bits must be at least 6")


def _affine(value, op, modulus):
    """Apply one invertible affine permutation modulo a power of two."""
    multiplier, offset = op
    return (multiplier * value + offset) % modulus


def _network(value, operations, modulus):
    for operation in operations:
        value = _affine(value, operation, modulus)
    return value


def _inverse_operation(operation, modulus):
    multiplier, offset = operation
    inverse = pow(multiplier, -1, modulus)
    return [inverse, (-inverse * offset) % modulus]


def _inverse_network_operations(operations, modulus):
    return [_inverse_operation(op, modulus) for op in reversed(operations)]


def _inverse_network(value, operations, modulus):
    return _network(value, _inverse_network_operations(operations, modulus), modulus)


def _random_network(rng, n, rounds):
    operations = []
    for _ in range(rounds):
        multiplier = rng.randrange(1, n, 2)
        offset = rng.randrange(n)
        # Avoid an identity round: it would make the in-context no-mask attack
        # artificially stronger on a small but needless part of the distribution.
        if multiplier == 1 and offset == 0:
            offset = 1
        operations.append([multiplier, offset])
    return operations


def _walsh_entry(row_code, column_code):
    return -1 if (row_code & column_code).bit_count() & 1 else 1


def _signed_sum_table(weights):
    table = {}
    k = len(weights)
    for mask in range(1 << k):
        total = 0
        for j, weight in enumerate(weights):
            total += -weight if mask >> j & 1 else weight
        if total in table:
            return None
        table[total] = mask
    return table


def _random_weights(rng, terms, weight_bits):
    """Comparable positive weights with distinct signed subset sums."""
    low = 1 << (weight_bits - 2)
    high = 1 << (weight_bits - 1)
    if high - low < terms:
        raise ValueError("weight_bits is too small for the requested term count")
    for _ in range(20_000):
        weights = sorted(rng.sample(range(low, high), terms))
        # No coefficient alone dominates all the others.  This specifically
        # blocks the otherwise devastating sign-of-the-signal heuristic.
        if weights[-1] >= sum(weights[:-1]):
            continue
        if _signed_sum_table(weights) is not None:
            return weights
    raise RuntimeError("could not sample dissociated comparable weights")


def _rational_from_json(value):
    if rationals is not None:
        return rationals.from_json(value)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("rational must be [num,den]")
    num, den = value
    if not _plain_int(num) or not _plain_int(den) or den == 0:
        raise ValueError("malformed rational")
    return Fraction(num, den)


def _rational_bits(value):
    if rationals is not None:
        return rationals.bit_size(value)
    q = _rational_from_json(value)
    return max(abs(q.numerator).bit_length(), q.denominator.bit_length(), 1)


def _answer_from_rows(rows, weights):
    return [[row, [weight, 1]] for row, weight in zip(rows, weights)]


def _spectrum_dict(inst):
    values = {}
    for item in inst.get("spectrum", []):
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("malformed spectrum entry")
        column, value = item
        if not _plain_int(column) or not _plain_int(value):
            raise ValueError("spectrum entries must be integer pairs")
        if column in values:
            raise ValueError("duplicate spectral coordinate")
        values[column] = value
    if set(values) != set(range(inst["n"])):
        raise ValueError("spectrum does not contain every coordinate exactly once")
    return values


def make_instance(n, seed=0, **params):
    """Inverse-generate a sparse certified point of a Walsh spectracone."""
    terms = params.pop("terms", 7)
    rounds = params.pop("rounds", 1)
    weight_bits = params.pop("weight_bits", 24)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, terms, rounds, weight_bits)

    rng = random.Random(seed)
    row_network = _random_network(rng, n, rounds)
    column_network = _random_network(rng, n, rounds)
    weights = _random_weights(rng, terms, weight_bits)

    # Sample the witness in canonical Walsh-row coordinates before publishing
    # any spectrum.  Visible rows are obtained only by carrying this witness
    # backward through the row relabelling.
    row_codes = rng.sample(range(n), terms)
    visible_rows = [
        _inverse_network(code, row_network, n) for code in row_codes
    ]

    spectrum = []
    for column in range(n):
        column_code = _network(column, column_network, n)
        value = sum(
            weight * _walsh_entry(row_code, column_code)
            for row_code, weight in zip(row_codes, weights)
        )
        spectrum.append([column, value])
    spectrum_values = [value for _, value in spectrum]
    rng.shuffle(spectrum)

    decoder = _signed_sum_table(weights)
    assert decoder is not None
    answer = _answer_from_rows(visible_rows, weights)
    inst = {
        "n": n,
        "dimension_bits": n.bit_length() - 1,
        "k": terms,
        "rounds": rounds,
        "weight_bits": weight_bits,
        "row_network": row_network,
        "column_network": column_network,
        "weights": weights,
        "signed_sum_decoder": [
            [value, format(mask, f"0{terms}b")[::-1]]
            for value, mask in sorted(decoder.items())
        ],
        "spectrum": spectrum,
        # Ordered exact cache used by the verifier's 200k-candidate audit.  The
        # shuffled pair list above is the rendered instance; both encode the
        # same vector and are cross-checked on every valid witness.
        "_spectrum_values": spectrum_values,
        "answer": answer,
    }
    # The answer crosses the JSON boundary in emit.sh.  Enforce that property
    # at construction time rather than discovering it after an oracle run.
    if json.loads(json.dumps(answer)) != answer:
        raise AssertionError("answer is not JSON-native")
    return inst


def _format_indexed_pairs(pairs, per_line=8):
    chunks = []
    for start in range(0, len(pairs), per_line):
        chunks.append("  " + "  ".join(f"{i}:{v}" for i, v in pairs[start:start + per_line]))
    return "\n".join(chunks)


def render(inst):
    n = inst["n"]
    d = inst["dimension_bits"]
    k = inst["k"]
    row_ops = " ".join(f"({a},{b})" for a, b in inst["row_network"])
    col_ops = " ".join(f"({a},{b})" for a, b in inst["column_network"])
    decoder = _format_indexed_pairs(inst["signed_sum_decoder"], per_line=4)
    spectrum = _format_indexed_pairs(inst["spectrum"], per_line=8)
    statement = f"""Find a sparse certificate for a spectrum in a Walsh Perron spectracone.

All indices are 0-based.  Let d={d} and n={n}=2^{d}.  For integers u,v in
0,...,n-1, define the Walsh entry

    H[u,v] = (-1)^parity(u AND v),

where AND is bitwise AND on the {d}-bit binary expansions and parity is 0 for an
even number of 1-bits and 1 for an odd number.

An affine relabelling operation (a,b) sends z to (a*z+b) modulo n.  Apply the
operations in the displayed left-to-right order.  Every multiplier a is odd,
so every operation is a permutation.

Row-code operations R: {row_ops}
Column-code operations C: {col_ops}

The relabelled Walsh matrix S has

    S[r,c] = H[R(r), C(c)].

For an invertible matrix S, its spectracone is the set of vectors lambda for
which S*diag(lambda)*S^(-1) is a real matrix whose entries are all nonnegative;
diag(lambda) means the diagonal matrix with diagonal lambda.  A Perron
similarity is an invertible matrix that diagonalizes at least one irreducible
entrywise-nonnegative matrix.  Every relabelled Walsh matrix used here is a
Perron similarity, and its spectracone is exactly the conical hull of its rows.

A row-cone certificate for a spectral vector lambda is a list of positive
rational coefficients alpha_j and distinct row indices r_j satisfying, for
every c=0,...,n-1,

    lambda[c] = sum_j alpha_j*S[r_j,c].

Thus such a certificate proves that lambda lies in the spectracone and is the
spectrum of the entrywise-nonnegative matrix S*diag(lambda)*S^(-1).

This instance has exactly k={k} nonzero terms.  Their coefficients, in the
required answer order, are the following positive integers (integers are
rationals with denominator 1):

    {" ".join(map(str, inst["weights"]))}

For exact sign decoding, the next table lists every possible signed sum.  Each
entry is value:bits.  In the bit string, bit j is 0 when coefficient j has a
plus sign and 1 when it has a minus sign; j runs left-to-right in the published
coefficient order.

{decoder}

The complete target spectrum is below as coordinate:value pairs.  The pairs
are deliberately unordered; each coordinate 0,...,n-1 occurs exactly once.

{spectrum}

Return exactly k terms in increasing published-coefficient order.  Term j is
[r_j,[num_j,den_j]], where 0 <= r_j < n, all r_j are distinct, and the reduced
rational num_j/den_j must equal coefficient j above.  Order therefore matters,
repeated rows are forbidden, denominators must be positive, and all equalities
are exact.

Give your final answer inside <answer></answer> tags, as one JSON list of the k terms.
Example: <answer>[[0,[2,1]],[3,[5,1]]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse tagged JSON, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for block in reversed(blocks):
        candidate = block.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
            candidate = re.sub(r"\s*```$", "", candidate)
        try:
            return json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    for block in reversed(fenced):
        try:
            value = json.loads(block.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    """Verify any bounded sparse row-cone decomposition; never read answer key."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    k = inst["k"]
    n = inst["n"]
    if len(answer) != k:
        return False, f"expected exactly {k} terms, got {len(answer)}"

    rows = []
    coefficients = []
    for position, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term {position + 1} must be [row,[num,den]]"
        row, encoded = term
        if not _plain_int(row):
            return False, f"row in term {position + 1} must be an integer"
        if row < 0 or row >= n:
            return False, f"row in term {position + 1} is outside 0 <= row < n"
        if (
            not isinstance(encoded, list)
            or len(encoded) != 2
            or not all(_plain_int(part) for part in encoded)
            or encoded[1] == 0
        ):
            return False, f"coefficient in term {position + 1} is not a valid rational"
        num, den = encoded
        if den <= 0:
            return False, f"coefficient in term {position + 1} needs a positive denominator"
        if math.gcd(num, den) != 1:
            return False, f"coefficient in term {position + 1} is not reduced canonically"
        expected = inst["weights"][position]
        if num != expected * den:
            return False, f"coefficient mismatch in term {position + 1}"
        if max(abs(num).bit_length(), den.bit_length(), 1) > inst["weight_bits"]:
            return False, f"coefficient in term {position + 1} exceeds the bit bound"
        rows.append(row)
        coefficients.append(expected)

    if len(set(rows)) != k:
        return False, "row indices must be distinct"

    target = inst.get("_spectrum_values")
    if not isinstance(target, list) or len(target) != n:
        try:
            lookup = _spectrum_dict(inst)
            target = [lookup[c] for c in range(n)]
        except (KeyError, TypeError, ValueError) as exc:
            return False, f"malformed instance spectrum: {exc}"

    row_codes = [_network(row, inst["row_network"], n) for row in rows]
    for column in range(n):
        if not _plain_int(target[column]):
            return False, f"malformed instance spectrum at coordinate {column}"
        column_code = _network(column, inst["column_network"], n)
        reconstructed = sum(
            weight * _walsh_entry(row_code, column_code)
            for row_code, weight in zip(row_codes, coefficients)
        )
        if reconstructed != target[column]:
            return False, f"decomposition mismatch at spectral coordinate {column}"
    # A valid candidate reaches the end, so now pay the one-time integrity cost
    # of checking that the fast cache really is the vector shown to the solver.
    try:
        rendered_target = _spectrum_dict(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance spectrum: {exc}"
    if any(rendered_target[c] != target[c] for c in range(n)):
        return False, "ordered spectrum cache disagrees with rendered coordinates"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact structure-aware certificate language."""
    rows = rng.sample(range(inst["n"]), inst["k"])
    return _answer_from_rows(rows, inst["weights"])


def search_space(inst):
    n, k = inst["n"], inst["k"]
    return math.prod(range(n - k + 1, n + 1))


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for rows in itertools.permutations(range(inst["n"]), inst["k"]):
        count += int(verify(inst, _answer_from_rows(rows, inst["weights"]))[0])
    return count


def canonical_key(inst):
    """Normalize visible column labels and ignore visible row names."""
    n = inst["n"]
    target = _spectrum_dict(inst)
    canonical = [None] * n
    for visible_column, value in target.items():
        code = _network(visible_column, inst["column_network"], n)
        if canonical[code] is not None:
            raise ValueError("column network is not a permutation")
        canonical[code] = value
    payload = json.dumps(
        [n, inst["weights"], canonical], separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _fwht(values):
    out = list(values)
    width = 1
    n = len(out)
    while width < n:
        for start in range(0, n, 2 * width):
            for j in range(start, start + width):
                a, b = out[j], out[j + width]
                out[j] = a + b
                out[j + width] = a - b
        width *= 2
    return out


def _reference_solve(inst):
    """Full inverse Walsh transform, the expected successful Track B reference."""
    n = inst["n"]
    target = inst["_spectrum_values"]
    canonical = [0] * n
    for column, value in enumerate(target):
        canonical[_network(column, inst["column_network"], n)] = value
    transformed = _fwht(canonical)
    by_weight = {}
    for code, value in enumerate(transformed):
        if value % n:
            return None
        coefficient = value // n
        if coefficient:
            if coefficient <= 0 or coefficient in by_weight:
                return None
            by_weight[coefficient] = code
    if set(by_weight) != set(inst["weights"]):
        return None
    rows = [
        _inverse_network(by_weight[weight], inst["row_network"], n)
        for weight in inst["weights"]
    ]
    return _answer_from_rows(rows, inst["weights"])


def _compact_solve(inst, ignore_relabellings=False):
    """Recover support from Walsh characters on the binary unit columns."""
    n = inst["n"]
    d = inst["dimension_bits"]
    k = inst["k"]
    target = inst["_spectrum_values"]
    decoder = {
        value: sum((char == "1") << j for j, char in enumerate(bits))
        for value, bits in inst["signed_sum_decoder"]
    }
    codes = [0] * k
    for bit in range(d):
        canonical_column = 1 << bit
        if ignore_relabellings:
            visible_column = canonical_column
        else:
            visible_column = _inverse_network(
                canonical_column, inst["column_network"], n
            )
        mask = decoder.get(target[visible_column])
        if mask is None:
            return _answer_from_rows([0] * k, inst["weights"])
        for j in range(k):
            if mask >> j & 1:
                codes[j] |= 1 << bit
    if ignore_relabellings:
        rows = codes
    else:
        rows = [
            _inverse_network(code, inst["row_network"], n) for code in codes
        ]
    return _answer_from_rows(rows, inst["weights"])


def _greedy_sign_peeling(inst):
    """Obvious but wrong heuristic: repeatedly assign the sign to the largest weight."""
    n = inst["n"]
    d = inst["dimension_bits"]
    k = inst["k"]
    target = inst["_spectrum_values"]
    unit_values = []
    for bit in range(d):
        column = _inverse_network(1 << bit, inst["column_network"], n)
        unit_values.append(target[column])
    residual = list(unit_values)
    codes = [0] * k
    for j in range(k - 1, -1, -1):
        for bit, value in enumerate(residual):
            if value < 0:
                codes[j] |= 1 << bit
        for bit in range(d):
            sign = -1 if codes[j] >> bit & 1 else 1
            residual[bit] -= inst["weights"][j] * sign
    rows = [_inverse_network(code, inst["row_network"], n) for code in codes]
    return _answer_from_rows(rows, inst["weights"])


def _extreme_row_candidate(inst):
    """Per-row outlier probe: all-ones and lowest-complexity Walsh rows."""
    codes = sorted(range(inst["n"]), key=lambda x: (x.bit_count(), x))[:inst["k"]]
    rows = [_inverse_network(code, inst["row_network"], inst["n"]) for code in codes]
    return _answer_from_rows(rows, inst["weights"])


def _spectral_extrema_candidate(inst):
    """Treat positions of the largest spectral magnitudes as if they were row labels."""
    ordered = sorted(
        enumerate(inst["_spectrum_values"]),
        key=lambda item: (-abs(item[1]), item[0]),
    )
    rows = []
    for column, _ in ordered:
        if column not in rows:
            rows.append(column)
        if len(rows) == inst["k"]:
            break
    return _answer_from_rows(rows, inst["weights"])


def _attack_candidates(inst, seed):
    rng = random.Random(seed ^ 0x240907682)
    return {
        "outlier_low_hamming_rows": [_extreme_row_candidate(inst)],
        "outlier_spectral_extrema": [_spectral_extrema_candidate(inst)],
        "greedy_largest_weight_sign_peeling": [_greedy_sign_peeling(inst)],
        "direct_unit_decode_without_relabellings": [
            _compact_solve(inst, ignore_relabellings=True)
        ],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _relabel_instance(inst, row_phi=None, column_phi=None, reorder=False):
    """Carry an instance through visible row/column affine relabellings."""
    out = copy.deepcopy(inst)
    n = inst["n"]
    if row_phi:
        out["row_network"] = (
            _inverse_network_operations(row_phi, n) + out["row_network"]
        )
        out["answer"] = [
            [_network(term[0], row_phi, n), copy.deepcopy(term[1])]
            for term in out["answer"]
        ]
    if column_phi:
        out["column_network"] = (
            _inverse_network_operations(column_phi, n) + out["column_network"]
        )
        out["spectrum"] = [
            [_network(column, column_phi, n), value]
            for column, value in out["spectrum"]
        ]
        carried = [0] * n
        for old_column, value in enumerate(out["_spectrum_values"]):
            carried[_network(old_column, column_phi, n)] = value
        out["_spectrum_values"] = carried
    if reorder:
        out["spectrum"] = list(reversed(out["spectrum"]))
    return out


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    n = inst["n"]
    row_phi = _random_network(rng, n, 1)
    column_phi = _random_network(rng, n, 1)
    variants = []
    for row_on, column_on, reorder in itertools.product((False, True), repeat=3):
        if not (row_on or column_on or reorder):
            continue
        variants.append(
            _relabel_instance(
                inst,
                row_phi=row_phi if row_on else None,
                column_phi=column_phi if column_on else None,
                reorder=reorder,
            )
        )
    return variants


def _extended_euclid_divisions(value, modulus):
    divisions = 0
    a, b = value % modulus, modulus
    while b:
        a, b = b, a % b
        divisions += 1
    return divisions


def _reference_operation_count(inst):
    n = inst["n"]
    d = inst["dimension_bits"]
    rounds = len(inst["column_network"])
    # n*d additions/subtractions in FWHT, 3 operations for each affine map of
    # every input coordinate, and k exact divisions by n.
    return n * d + 3 * n * rounds + inst["k"]


def _intended_operation_bound(inst):
    d = inst["dimension_bits"]
    k = inst["k"]
    rounds = max(len(inst["row_network"]), len(inst["column_network"]))
    # At most 2d Euclidean divisions per odd modular inverse, one inverse for
    # every row/column affine round; three operations per inverse-map use;
    # and k bit assignments at each of d unit columns.
    return rounds * (7 * d + 3 * k) + k * d


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _worst_answer_chars(inst):
    maximum_weight = (1 << (inst["weight_bits"] - 1)) - 1
    specimen = [
        [inst["n"] - 1, [maximum_weight, 1]] for _ in range(inst["k"])
    ]
    return len(json.dumps(specimen, separators=(",", ":")))


def escalate(params):
    """Grow the Walsh ground set while keeping the sparse witness length fixed."""
    harder = dict(params)
    harder["n"] = int(harder["n"]) * 2
    # Do not claim that larger published coefficient numerators are harder: the
    # solver merely copies those coefficients.  The honest axis is more Walsh
    # rows (a larger support haystack).  Once the compact unit-character route
    # itself crosses G9's operation cap, this implementation has no further
    # in-scope rung.
    probe = make_instance(seed=0, **harder)
    if _intended_operation_bound(probe) > 300:
        return None
    if _worst_answer_chars(probe) > 2_000:
        return "cap_bound"
    return harder


def selftest():
    report = {}

    planted_attempts = 0
    planted_failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 97):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            planted_attempts += 1
            if not ok:
                planted_failures.append(
                    {"preset": preset, "seed": seed, "reason": reason}
                )
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer JSON failure"}
                )
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and planted_attempts == 12,
        "attempts": planted_attempts,
        "failures": planted_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    dropped = copy.deepcopy(answer[:-1])
    swapped = copy.deepcopy(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = copy.deepcopy(answer)
    duplicated[-1][0] = duplicated[0][0]
    out_of_range = copy.deepcopy(answer)
    out_of_range[0][0] = inst["n"]
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The sparse Walsh certificate is:\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe row labels are 0-based."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x240907682)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_candidate_space": search_space(inst),
        "exact_unique_solution_density": f"1/{search_space(inst)}",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_low_hamming_rows",
        "outlier_spectral_extrema",
        "greedy_largest_weight_sign_peeling",
        "direct_unit_decode_without_relabellings",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    compact_successes = 0
    compact_seconds = 0.0
    reference_operations = 0
    inverse_divisions = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)

        start = time.perf_counter()
        recovered = _reference_solve(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        reference_operations += _reference_operation_count(trial)
        for network in (trial["row_network"], trial["column_network"]):
            inverse_divisions += sum(
                _extended_euclid_divisions(op[0], trial["n"]) for op in network
            )

        start = time.perf_counter()
        compact = _compact_solve(trial)
        compact_seconds += time.perf_counter() - start
        compact_successes += int(verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact fast Walsh-Hadamard inversion after affine reindexing",
        "complexity": "O(n (log n + rounds)) exact integer operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "modular_inverse_euclidean_divisions": inverse_divisions // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(successes[name] == 0 for name in attack_names)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "affine-unmasking plus Walsh unit-character decoding",
            "solves": f"{compact_successes}/8",
            "wall_clock_sec": round(compact_seconds / 8, 6),
            "operations_upper_bound": _intended_operation_bound(inst),
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    strongest_name = max(attack_names, key=lambda name: attack_seconds[name])
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_solution_density": guess_fraction,
        "shipping_exact_solution_count": 1,
        "shipping_exact_solution_density": f"1/{search_space(inst)}",
        "demo_exact_solution_count_by_enumeration": demo_count,
        "strongest_failing_attack": strongest_name,
        "baseline_attack_wall_clock_sec": round(attack_seconds[strongest_name] / 8, 6),
        "baseline_attack_iterations": 256
        if strongest_name == "random_restart_256"
        else 1,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and len(render(doubled)) > len(render(inst))
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
        "candidate_space_shipping": search_space(inst),
        "candidate_space_doubled": search_space(doubled),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        original_key = canonical_key(original)
        variants = _relabel_variants(original, seed ^ 0x5A5A)
        for transformed in variants:
            invariant_count += int(canonical_key(transformed) == original_key)
            real_transform_count += int(
                verify(transformed, transformed["answer"])[0]
            )
        unrelated_keys.append(original_key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariance_attempts": 140,
        "real_transformations_verified": real_transform_count,
        "real_transformation_attempts": 140,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "reordering the listed spectral coordinates",
            "affine relabelling of visible Walsh rows with carried witness",
            "affine relabelling of visible spectral coordinates",
            "all nonempty compositions of those three",
        ],
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    worst_chars = _worst_answer_chars(inst)
    worst_tokens = math.ceil(worst_chars / 4)
    intended_operations = _intended_operation_bound(inst)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        # As of 2026-09-05 the three oracle arms are diagnostic.  Only the
        # answer/route caps gate this field.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
