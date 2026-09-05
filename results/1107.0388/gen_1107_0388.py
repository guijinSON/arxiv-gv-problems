"""Compact Nullstellensatz certificates from arXiv:1107.0388, Example 6.3.

Andersson and Wulcan use the Masser--Philippon--Brownawell--Kollar
chain to show that the exponent c_infinity in their effective global
Briancon--Skoda--Huneke theorem is necessary.  The chain has a short
telescoping Bezout identity even though an expanded coefficient has degree
d**m-d.  This module hides that chain by a weighted Walsh--Hadamard change of
ideal generators and asks for a compact exact description of the resulting
polynomial coefficients.

The answer is planted by transforming the known telescoping identity.  It is
never obtained by solving the generated instance.
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
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "multivariate polynomials over Q",
        "polynomial ideals",
        "compact Bezout (Nullstellensatz) identities",
    ],
    "verification_operations": [
        "exact sparse-polynomial coefficient comparison",
        "exact integer Walsh matrix reconstruction",
        "composition of finite geometric-series identities",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undo the weighted Walsh mixing to expose the paper's triangular "
        "polynomial chain, then keep its repeated difference-of-powers "
        "identity factored instead of expanding exponentially many monomials."
    ),
    "hardness_basis": (
        "Track B: Buchberger/Macaulay ideal membership is effective (with "
        "doubly-exponential worst-case degree), while successive expanded "
        "elimination on the shipping m=8,d=7 chain performs 1,921,598 exact "
        "monomial arithmetic operations in a measured 0.83 seconds; the "
        "compact Walsh-and-telescoping route uses 148 exact operations."
    ),
    "max_answer_tokens": 63,
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


# n is rounded up to a power of two because the hiding transform is a Sylvester
# Walsh matrix.  d controls the degree explosion without lengthening the answer.
DIFFICULTY = {
    "demo": {"n": 2, "d": 2, "weight_max": 2},
    "easy": {"n": 4, "d": 3, "weight_max": 3},
    "medium": {"n": 8, "d": 5, "weight_max": 4},
    "hard": {"n": 8, "d": 7, "weight_max": 5},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Across generators, the coefficient columns are weighted Walsh characters "
    "of a hidden triangular difference-of-powers chain."
)
PLACEBO_HINT = (
    "Across generators, careful bookkeeping of coefficients and variable "
    "indices is important for this exact symbolic certificate."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object encoding compact Bezout polynomials: six length-m lists "
        "give a variable permutation, Walsh row and column code permutations, "
        "row and column signs in {-1,1}, and positive integer column weights. "
        "The last column code and sign are canonically fixed to 0 and 1.  The "
        "module's displayed formula turns this finite encoding into exact "
        "polynomial coefficients over Q."
    ),
    "bounds": {
        "list_length": "m",
        "permutation_ranges": "0..m-1",
        "sign_alphabet": [-1, 1],
        "weight_range": "1..weight_max",
        "fixed_last_column_code": 0,
        "fixed_last_column_sign": 1,
    },
}

NOTES = (
    "Section 1 fixes the problem as exact polynomial ideal membership and "
    "states Hermann's doubly-exponential general degree bound; it also records "
    "the easy Macaulay regime when there are no projective common zeros.  "
    "Theorem A gives the effective membership representation and its degree "
    "bound.  Example 6.3 supplies the exact triangular polynomials used here "
    "and proves that every Bezout representation has deg(F_1 Q_1) at least "
    "d^m.  Thus Track A would be dishonest: Groebner/Macaulay elimination "
    "exists.  The Track B gap is between expanding about d^(m-1) monomials and "
    "recognizing a factored geometric-series telescope.  Weighted Walsh mixing "
    "removes sparse row outliers.  The measured outlier, greedy, random-restart, "
    "and direct-unmixed ansatz attacks all fail; the exact reference recovery "
    "and expanded-elimination cost are reported separately, as Track B requires."
)


# Filled after the three harness runs.  The arms are diagnostic; only the size
# and intended-operation caps gate G9 under the current protocol.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unscored_quota_error",
}


_ANSWER_KEYS = {
    "variables",
    "row_codes",
    "column_codes",
    "row_signs",
    "column_signs",
    "weights",
}


def _power_of_two_at_least(n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    return 1 << (n - 1).bit_length()


def _walsh_entry(row, column):
    return -1 if (row & column).bit_count() & 1 else 1


def _zero_monomial(m):
    return (0,) * m


def _mono(m, entries):
    exponent = [0] * m
    for variable, power in entries:
        exponent[variable] += power
    return tuple(exponent)


def _poly_add_scaled(target, source, scale):
    if scale == 0:
        return
    for monomial, coefficient in source.items():
        value = target.get(monomial, 0) + scale * coefficient
        if value:
            target[monomial] = value
        elif monomial in target:
            del target[monomial]


def _base_chain(m, d, variables):
    """The m polynomials in Example 6.3 after a variable relabelling."""
    y = variables[-1]
    out = [{_mono(m, [(variables[0], d)]): 1}]
    for index in range(1, m - 1):
        out.append(
            {
                _mono(m, [(variables[index - 1], 1), (y, d - 1)]): 1,
                _mono(m, [(variables[index], d)]): -1,
            }
        )
    out.append(
        {
            _mono(m, [(variables[m - 2], 1), (y, d - 1)]): 1,
            _zero_monomial(m): -1,
        }
    )
    return out


def _matrix_from_answer(answer):
    m = len(answer["variables"])
    matrix = []
    for row in range(m):
        matrix.append(
            [
                answer["row_signs"][row]
                * _walsh_entry(
                    answer["row_codes"][row], answer["column_codes"][column]
                )
                * answer["column_signs"][column]
                * answer["weights"][column]
                for column in range(m)
            ]
        )
    return matrix


def _mix_chain(chain, matrix):
    polynomials = []
    for row in matrix:
        polynomial = {}
        for coefficient, base_polynomial in zip(row, chain):
            _poly_add_scaled(polynomial, base_polynomial, coefficient)
        polynomials.append(polynomial)
    return polynomials


def _encode_polynomial(polynomial):
    return [
        [coefficient, list(monomial)]
        for monomial, coefficient in sorted(polynomial.items())
    ]


def _decode_polynomial(encoded, m):
    if not isinstance(encoded, list):
        raise ValueError("polynomial is not a term list")
    polynomial = {}
    for term in encoded:
        if (
            not isinstance(term, list)
            or len(term) != 2
            or isinstance(term[0], bool)
            or not isinstance(term[0], int)
            or not isinstance(term[1], list)
            or len(term[1]) != m
            or any(isinstance(e, bool) or not isinstance(e, int) or e < 0 for e in term[1])
        ):
            raise ValueError("malformed polynomial term")
        monomial = tuple(term[1])
        polynomial[monomial] = polynomial.get(monomial, 0) + term[0]
        if not polynomial[monomial]:
            del polynomial[monomial]
    return polynomial


def _public_polynomials(inst):
    return [_decode_polynomial(poly, inst["m"]) for poly in inst["polynomials"]]


def make_instance(n, seed=0, d=7, weight_max=5, **params):
    """Transform a known telescoping identity; never solve the output instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    m = _power_of_two_at_least(n)
    if isinstance(d, bool) or not isinstance(d, int) or d < 2:
        raise ValueError("d must be an integer at least 2")
    if isinstance(weight_max, bool) or not isinstance(weight_max, int) or weight_max < 1:
        raise ValueError("weight_max must be a positive integer")

    rng = random.Random(seed)
    variables = list(range(m))
    rng.shuffle(variables)
    row_codes = list(range(m))
    rng.shuffle(row_codes)
    column_codes = list(range(1, m))
    rng.shuffle(column_codes)
    column_codes.append(0)
    row_signs = [rng.choice((-1, 1)) for _ in range(m)]
    column_signs = [rng.choice((-1, 1)) for _ in range(m - 1)] + [1]
    weights = [rng.randint(1, weight_max) for _ in range(m)]

    answer = {
        "variables": variables,
        "row_codes": row_codes,
        "column_codes": column_codes,
        "row_signs": row_signs,
        "column_signs": column_signs,
        "weights": weights,
    }
    chain = _base_chain(m, d, variables)
    matrix = _matrix_from_answer(answer)
    polynomials = _mix_chain(chain, matrix)
    return {
        "family": "compressed Masser-chain Nullstellensatz certificate",
        "requested_n": n,
        "m": m,
        "d": d,
        "weight_max": weight_max,
        "variables": [f"x{i}" for i in range(m)],
        "polynomials": [_encode_polynomial(poly) for poly in polynomials],
        "target": 1,
        "answer": answer,
    }


def _format_monomial(exponents):
    factors = []
    for index, exponent in enumerate(exponents):
        if exponent == 1:
            factors.append(f"x{index}")
        elif exponent:
            factors.append(f"x{index}^{exponent}")
    return "*".join(factors) if factors else "1"


def _format_polynomial(encoded):
    pieces = []
    for coefficient, exponents in encoded:
        monomial = _format_monomial(exponents)
        magnitude = abs(coefficient)
        if monomial == "1":
            body = str(magnitude)
        elif magnitude == 1:
            body = monomial
        else:
            body = f"{magnitude}*{monomial}"
        if not pieces:
            pieces.append(("-" if coefficient < 0 else "") + body)
        else:
            pieces.append((" - " if coefficient < 0 else " + ") + body)
    return "".join(pieces) if pieces else "0"


def render(inst):
    m = inst["m"]
    d = inst["d"]
    bound = inst["weight_max"]
    lines = [
        "Find a compact exact Nullstellensatz certificate.",
        "",
        f"Work in Q[x0,...,x{m - 1}]. A monomial x0^e0*...*x{m - 1}^e{m - 1}",
        "has the usual nonnegative integer exponents. The following ordered",
        f"list contains m={m} polynomials, all of total degree d={d}:",
        "",
    ]
    for index, polynomial in enumerate(inst["polynomials"]):
        lines.append(f"G{index} = {_format_polynomial(polynomial)}")
    lines.extend(
        [
            "",
            "You must encode exact polynomials Q0,...,Q(m-1) whose polynomial",
            "identity is sum_i G_i*Q_i = 1.  Use the following compressed",
            "certificate; the definitions below are part of the required format.",
            "",
            "Submit six integer lists, each of length m:",
            "  variables, row_codes, column_codes are permutations of 0,...,m-1;",
            "  row_signs and column_signs contain only -1 or 1;",
            f"  weights contains only integers from 1 through {bound}, inclusive.",
            "Additionally column_codes[m-1]=0 and column_signs[m-1]=1.",
            "All indexing is zero-based; order matters; repetitions are forbidden",
            "in the three permutation lists and allowed in the other lists.",
            "",
            "For r,c in {0,...,m-1}, let",
            "  H(r,c)=(-1)^(popcount(r bitwise-AND c)).",
            "Your lists define A[i,j] = row_signs[i]*H(row_codes[i],",
            "column_codes[j])*column_signs[j]*weights[j]. Let y be the variable",
            "whose index is variables[m-1], and define the hidden chain",
            "  F0 = x_(variables[0])^d,",
            "  Fj = x_(variables[j-1])*y^(d-1) - x_(variables[j])^d",
            "       for 1 <= j <= m-2,",
            "  F(m-1) = x_(variables[m-2])*y^(d-1) - 1.",
            "The certificate is valid exactly when G_i=sum_j A[i,j]*Fj for every i.",
            "",
            "For completeness, here is the exact polynomial certificate encoded by",
            "those lists. Put T_r=x_(variables[r])*y^(d^(m-r-1)-1) and",
            "S_r=1+T_r+...+T_r^(d-1). Define q0=y^(d^m-d), and for 1<=j<m",
            "define qj=-y^(d*(d^(m-j-1)-1))*product_(r=0)^(j-1) S_r.",
            "Then Q_i=sum_j A[i,j]*qj/(m*weights[j]^2). Orthogonality of H and",
            "successive identities U^d-V^d=(U-V)(U^(d-1)+...+V^(d-1))",
            "give sum_i G_i*Q_i=1. The checker verifies all integer polynomial",
            "coefficients and these local telescoping relations exactly; no floats",
            "or probabilistic identity tests are used.",
            "",
            "Give your final answer inside <answer></answer> tags, as one JSON",
            "object with exactly the six keys above and integer-list values.",
            "Example: <answer>{\"variables\":[0,1],\"row_codes\":[0,1],",
            "\"column_codes\":[1,0],\"row_signs\":[1,1],",
            "\"column_signs\":[1,1],\"weights\":[1,1]}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```") and payload.endswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return answer if isinstance(answer, dict) else None


def _valid_int_list(value, length):
    return (
        isinstance(value, list)
        and len(value) == length
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    )


def _validate_answer_shape(inst, answer):
    m = inst["m"]
    if not isinstance(answer, dict):
        return "answer must be a JSON object"
    if set(answer) != _ANSWER_KEYS:
        return "answer must contain exactly the six required keys"
    if not _valid_int_list(answer["variables"], m):
        return f"variables must be a length-{m} integer list"
    if sorted(answer["variables"]) != list(range(m)):
        return "variables must be a permutation of 0,...,m-1"
    if not _valid_int_list(answer["row_codes"], m):
        return f"row_codes must be a length-{m} integer list"
    if sorted(answer["row_codes"]) != list(range(m)):
        return "row_codes must be a permutation of 0,...,m-1"
    if not _valid_int_list(answer["column_codes"], m):
        return f"column_codes must be a length-{m} integer list"
    if sorted(answer["column_codes"]) != list(range(m)):
        return "column_codes must be a permutation of 0,...,m-1"
    if answer["column_codes"][-1] != 0:
        return "the last column code must be 0"
    if not _valid_int_list(answer["row_signs"], m):
        return f"row_signs must be a length-{m} integer list"
    if any(sign not in (-1, 1) for sign in answer["row_signs"]):
        return "row_signs entries must be -1 or 1"
    if not _valid_int_list(answer["column_signs"], m):
        return f"column_signs must be a length-{m} integer list"
    if any(sign not in (-1, 1) for sign in answer["column_signs"]):
        return "column_signs entries must be -1 or 1"
    if answer["column_signs"][-1] != 1:
        return "the last column sign must be 1"
    if not _valid_int_list(answer["weights"], m):
        return f"weights must be a length-{m} integer list"
    if any(weight < 1 or weight > inst["weight_max"] for weight in answer["weights"]):
        return f"weights entries must lie in 1..{inst['weight_max']}"
    return None


def _local_telescoping_check(m, d, variables, chain):
    """Execute the sparse local identities underlying the compressed q_j."""
    y = variables[-1]
    # T_0^d = F_0*y^(d^m-d).
    left = _mono(m, [(variables[0], d), (y, d * (d ** (m - 1) - 1))])
    right = {}
    _poly_add_scaled(right, chain[0], 1)
    shifted = {tuple(e + (d ** m - d if i == y else 0) for i, e in enumerate(mon)): c
               for mon, c in chain[0].items()}
    if shifted != {left: 1}:
        return False

    # T_i = T_(i+1)^d + F_(i+1)*y^a, and T_(m-2)-1=F_(m-1).
    for index in range(m - 2):
        t_i = _mono(m, [(variables[index], 1), (y, d ** (m - index - 1) - 1)])
        t_next_d = _mono(
            m,
            [(variables[index + 1], d), (y, d * (d ** (m - index - 2) - 1))],
        )
        shift = d * (d ** (m - index - 2) - 1)
        assembled = {t_next_d: 1}
        shifted_f = {
            tuple(e + (shift if i == y else 0) for i, e in enumerate(mon)): c
            for mon, c in chain[index + 1].items()
        }
        _poly_add_scaled(assembled, shifted_f, 1)
        if assembled != {t_i: 1}:
            return False
    final_expected = {
        _mono(m, [(variables[m - 2], 1), (y, d - 1)]): 1,
        _zero_monomial(m): -1,
    }
    return chain[-1] == final_expected


def verify(inst, answer):
    """Verify a compact witness from public instance data; never read inst['answer']."""
    reason = _validate_answer_shape(inst, answer)
    if reason:
        return False, reason
    m = inst["m"]
    d = inst["d"]
    # A cheap exact necessary check makes the 200k-candidate density experiment
    # fast without weakening verification.  Only F_(m-1) has a constant term.
    predicted_constants = [
        -answer["row_signs"][row] * answer["weights"][-1]
        for row in range(m)
    ]
    try:
        # _encode_polynomial sorts exponent tuples, so the constant (present in
        # every displayed row) is the first term.
        actual_constants = [
            encoded[0][0] if encoded and not any(encoded[0][1]) else 0
            for encoded in inst["polynomials"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance polynomial data: {exc}"
    if predicted_constants != actual_constants:
        return False, "constant coefficient signature does not match the certificate"

    try:
        public = _public_polynomials(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance polynomial data: {exc}"

    chain = _base_chain(m, d, answer["variables"])
    matrix = _matrix_from_answer(answer)
    if _mix_chain(chain, matrix) != public:
        return False, "certificate does not reconstruct the displayed polynomials"
    if not _local_telescoping_check(m, d, answer["variables"], chain):
        return False, "local difference-of-powers telescope is inconsistent"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample the fully constrained finite certificate grammar, without answer bias."""
    m = inst["m"]
    variables = list(range(m))
    row_codes = list(range(m))
    remaining_columns = list(range(1, m))
    rng.shuffle(variables)
    rng.shuffle(row_codes)
    rng.shuffle(remaining_columns)
    return {
        "variables": variables,
        "row_codes": row_codes,
        "column_codes": remaining_columns + [0],
        "row_signs": [rng.choice((-1, 1)) for _ in range(m)],
        "column_signs": [rng.choice((-1, 1)) for _ in range(m - 1)] + [1],
        "weights": [rng.randint(1, inst["weight_max"]) for _ in range(m)],
    }


def search_space(inst):
    m = inst["m"]
    return (
        math.factorial(m)
        * math.factorial(m)
        * math.factorial(m - 1)
        * (1 << (2 * m - 1))
        * inst["weight_max"] ** m
    )


def enumerate_all(inst):
    if search_space(inst) > 200_000:
        return None
    m = inst["m"]
    valid = 0
    for variables in itertools.permutations(range(m)):
        for row_codes in itertools.permutations(range(m)):
            for prefix in itertools.permutations(range(1, m)):
                for row_signs in itertools.product((-1, 1), repeat=m):
                    for column_prefix in itertools.product((-1, 1), repeat=m - 1):
                        for weights in itertools.product(
                            range(1, inst["weight_max"] + 1), repeat=m
                        ):
                            candidate = {
                                "variables": list(variables),
                                "row_codes": list(row_codes),
                                "column_codes": list(prefix) + [0],
                                "row_signs": list(row_signs),
                                "column_signs": list(column_prefix) + [1],
                                "weights": list(weights),
                            }
                            if verify(inst, candidate)[0]:
                                valid += 1
    return valid


def _coefficient_vectors(inst):
    public = _public_polynomials(inst)
    monomials = set().union(*(poly.keys() for poly in public))
    return {
        monomial: tuple(poly.get(monomial, 0) for poly in public)
        for monomial in monomials
    }


def _recover_variable_order(inst, vectors):
    m = inst["m"]
    d = inst["d"]
    pure = {}
    for variable in range(m):
        monomial = _mono(m, [(variable, d)])
        if monomial in vectors:
            pure[variable] = vectors[monomial]
    pivot_candidates = [variable for variable in range(m) if variable not in pure]
    if len(pivot_candidates) != 1:
        raise ValueError("reference recovery did not find a unique pivot variable")
    y = pivot_candidates[0]
    cross = {}
    for variable in pure:
        monomial = _mono(m, [(variable, 1), (y, d - 1)])
        if monomial in vectors:
            cross[variable] = vectors[monomial]
    if len(cross) != m - 1:
        raise ValueError("reference recovery did not find all chain links")

    negative_crosses = {tuple(-value for value in vector) for vector in cross.values()}
    starts = [variable for variable, vector in pure.items() if vector not in negative_crosses]
    if len(starts) != 1:
        raise ValueError("reference recovery did not find a unique chain start")
    order = [starts[0]]
    while len(order) < m - 1:
        wanted = tuple(-value for value in cross[order[-1]])
        matches = [variable for variable, vector in pure.items() if vector == wanted]
        if len(matches) != 1 or matches[0] in order:
            raise ValueError("reference recovery found an ambiguous chain successor")
        order.append(matches[0])
    return order + [y], pure[order[0]], [cross[v] for v in order]


def _reference_recover(inst):
    """Exact structure-aware recovery from public coefficients, not planted data."""
    m = inst["m"]
    vectors = _coefficient_vectors(inst)
    variables, first_column, later_columns = _recover_variable_order(inst, vectors)
    columns = [first_column] + later_columns
    weights = []
    signs_by_column = []
    for column in columns:
        magnitudes = {abs(value) for value in column}
        if len(magnitudes) != 1 or 0 in magnitudes:
            raise ValueError("coefficient column is not a weighted sign character")
        weight = magnitudes.pop()
        weights.append(weight)
        signs_by_column.append([value // weight for value in column])

    row_signs = list(signs_by_column[-1])
    normalized = [
        [signs_by_column[column][row] * row_signs[row] for column in range(m)]
        for row in range(m)
    ]
    # Gauge-fix displayed row zero to Walsh code zero; this cancels column signs.
    column_signs = list(normalized[0])
    table = [
        [normalized[row][column] * column_signs[column] for column in range(m)]
        for row in range(m)
    ]
    bits = (m - 1).bit_length()
    usable = list(range(m - 1))
    basis_columns = None
    row_codes = None
    for choice in itertools.combinations(usable, bits):
        codes = []
        for row in range(m):
            code = 0
            for bit, column in enumerate(choice):
                if table[row][column] == -1:
                    code |= 1 << bit
            codes.append(code)
        if sorted(codes) == list(range(m)):
            basis_columns = choice
            row_codes = codes
            break
    if basis_columns is None:
        raise ValueError("reference recovery could not choose Walsh basis columns")

    column_codes = []
    for column in range(m):
        vector = [table[row][column] for row in range(m)]
        matches = [
            code
            for code in range(m)
            if vector == [_walsh_entry(row_codes[row], code) for row in range(m)]
        ]
        if len(matches) != 1:
            raise ValueError("reference recovery found an ambiguous Walsh column")
        column_codes.append(matches[0])
    recovered = {
        "variables": variables,
        "row_codes": row_codes,
        "column_codes": column_codes,
        "row_signs": row_signs,
        "column_signs": column_signs,
        "weights": weights,
    }
    ok, reason = verify(inst, recovered)
    if not ok:
        raise ValueError("reference recovery failed verification: " + reason)
    return recovered


def _canonical_payload(inst):
    recovered = _reference_recover(inst)
    m = inst["m"]
    public = _public_polynomials(inst)
    inverse_variables = {old: new for new, old in enumerate(recovered["variables"])}
    normalized_rows = []
    for polynomial in public:
        terms = []
        for monomial, coefficient in polynomial.items():
            renamed = [0] * m
            for old, exponent in enumerate(monomial):
                renamed[inverse_variables[old]] = exponent
            terms.append([coefficient, renamed])
        normalized_rows.append(sorted(terms))
    normalized_rows.sort(key=lambda row: json.dumps(row, separators=(",", ":")))
    return {
        "m": m,
        "d": inst["d"],
        "weight_max": inst["weight_max"],
        "rows": normalized_rows,
    }


def canonical_key(inst):
    payload = json.dumps(_canonical_payload(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _relabel_instance(inst, variable_map, row_order):
    m = inst["m"]
    transformed_polynomials = []
    for old_row in row_order:
        polynomial = _decode_polynomial(inst["polynomials"][old_row], m)
        transformed = {}
        for monomial, coefficient in polynomial.items():
            renamed = [0] * m
            for old_variable, exponent in enumerate(monomial):
                renamed[variable_map[old_variable]] = exponent
            transformed[tuple(renamed)] = coefficient
        transformed_polynomials.append(_encode_polynomial(transformed))
    carried = {
        key: list(value) for key, value in inst["answer"].items()
    }
    carried["variables"] = [variable_map[v] for v in carried["variables"]]
    carried["row_codes"] = [carried["row_codes"][row] for row in row_order]
    carried["row_signs"] = [carried["row_signs"][row] for row in row_order]
    out = dict(inst)
    out["polynomials"] = transformed_polynomials
    out["answer"] = carried
    return out


def _chain_columns_for_attack(inst):
    vectors = _coefficient_vectors(inst)
    variables, first, later = _recover_variable_order(inst, vectors)
    columns = [first] + later
    weights = [abs(column[0]) for column in columns]
    row_signs = [value // weights[-1] for value in columns[-1]]
    return variables, columns, weights, row_signs


def _attack_outlier_order(inst):
    m = inst["m"]
    public = _public_polynomials(inst)
    row_rank = sorted(range(m), key=lambda row: sum(abs(v) for v in public[row].values()))
    row_codes = [0] * m
    for code, row in enumerate(row_rank):
        row_codes[row] = code
    return {
        "variables": list(range(m)),
        "row_codes": row_codes,
        "column_codes": list(range(1, m)) + [0],
        "row_signs": [1] * m,
        "column_signs": [1] * m,
        "weights": [1] * m,
    }


def _attack_greedy_chain(inst):
    m = inst["m"]
    variables, _columns, weights, row_signs = _chain_columns_for_attack(inst)
    return {
        "variables": variables,
        "row_codes": list(range(m)),
        "column_codes": list(range(1, m)) + [0],
        "row_signs": row_signs,
        "column_signs": [1] * m,
        "weights": weights,
    }


def _attack_direct_unmixed(inst):
    m = inst["m"]
    variables, columns, weights, row_signs = _chain_columns_for_attack(inst)
    ordering = sorted(range(m), key=lambda row: tuple(columns[0][row:] + columns[0][:row]))
    row_codes = [0] * m
    for code, row in enumerate(ordering):
        row_codes[row] = code
    return {
        "variables": variables,
        "row_codes": row_codes,
        "column_codes": list(reversed(range(1, m))) + [0],
        "row_signs": row_signs,
        "column_signs": [1] * m,
        "weights": weights,
    }


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _measure_expanded_elimination(m, d):
    """Actually enumerate every monomial code created by expanded telescoping."""
    start = time.perf_counter()
    terms = [0]
    place = 1
    insertions = 0
    checksum = 0
    for _ in range(m - 1):
        expanded = []
        append = expanded.append
        for term in terms:
            for digit in range(d):
                code = term + digit * place
                append(code)
                checksum ^= code
        terms = expanded
        place *= d
        insertions += len(terms)
    elapsed = time.perf_counter() - start
    # Each generated monomial code performs one exact multiplication and one
    # addition.  The checksum forces complete materialisation.
    return {
        "wall_clock_sec": round(elapsed, 6),
        "monomial_insertions": insertions,
        "operations": 2 * insertions,
        "largest_coefficient_terms": len(terms),
        "checksum": checksum,
    }


def escalate(params):
    harder = dict(params)
    d = harder.get("d", 7)
    harder["d"] = d + 2
    return harder


def _atoms(value):
    if isinstance(value, dict):
        return sum(_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atoms(item) for item in value)
    return 1


def selftest():
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_checks = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 failed at {preset}/{seed}: {reason}")
            g1_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "checks": g1_checks,
        "json_native_checks": json_roundtrips,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    corruptions = {}
    dropped = {key: list(value) for key, value in shipping["answer"].items()}
    dropped["row_signs"] = dropped["row_signs"][:-1]
    corruptions["drop_one"] = dropped
    swapped = {key: list(value) for key, value in shipping["answer"].items()}
    swapped["variables"][0], swapped["variables"][1] = (
        swapped["variables"][1], swapped["variables"][0]
    )
    corruptions["swap_two"] = swapped
    duplicated = {key: list(value) for key, value in shipping["answer"].items()}
    duplicated["row_codes"][0] = duplicated["row_codes"][1]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    out_of_range = {key: list(value) for key, value in shipping["answer"].items()}
    out_of_range["weights"][0] = shipping["weight_max"] + 1
    corruptions["out_of_range"] = out_of_range
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = reason
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError(f"G2 reasons are not distinct: {reasons}")
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    blob = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = "I used the Walsh orthogonality.\n```text\nFinal:\n```\n<answer>\n" + blob + "\n</answer>\n"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "realistic_prose": True,
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }
    if not all(report["G3_round_trip"].values()):
        raise AssertionError("G3 failed")

    samples = 200_000
    rng = random.Random(8675309)
    hits = 0
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "certificate_language_size": search_space(shipping),
        "structure_aware": True,
    }
    if not report["G4_guess_resistance"]["pass"]:
        raise AssertionError("G4 failed")

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo)
    reference_cost = _measure_expanded_elimination(shipping["m"], shipping["d"])
    report["G5_density_baseline"] = {
        "pass": isinstance(probability, float) and reference_cost["operations"] > 0,
        "shipping_density_hits": hits,
        "shipping_density_total": samples,
        "reference_wall_clock_sec": reference_cost["wall_clock_sec"],
        "reference_operations": reference_cost["operations"],
        "shipping_density": {
            "kind": "sampled",
            "hits": hits,
            "total": samples,
            "observed_fraction": probability,
        },
        "demo_exact": {
            "valid_answers": exact_demo,
            "candidate_space": search_space(demo),
        },
        "strongest_attack": {
            "name": "expanded successive elimination after exact coefficient recovery",
            **reference_cost,
        },
    }

    attack_results = {
        "outlier_row_norm": {"successes": 0, "attempts": 0},
        "greedy_chain_unmixed_walsh": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "direct_unmixed_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    for seed in range(700, 708):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_row_norm": _attack_outlier_order(inst),
            "greedy_chain_unmixed_walsh": _attack_greedy_chain(inst),
            "random_restart_256": _attack_random_restart(inst, seed + 10_000),
            "direct_unmixed_ansatz": _attack_direct_unmixed(inst),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        recovered = _reference_recover(inst)
        reference_successes += int(verify(inst, recovered)[0])
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "coefficient-column recovery plus expanded successive elimination",
            "complexity": "O(m^2 + sum_(r=1)^(m-1) d^r) exact monomial operations",
            "wall_clock_sec": reference_cost["wall_clock_sec"],
            "operations": reference_cost["operations"],
            "monomial_insertions": reference_cost["monomial_insertions"],
            "solves": f"{reference_successes}/8, as expected",
        },
    }
    if not report["G6_adversary_panel"]["pass"]:
        raise AssertionError(f"G6 failed: {report['G6_adversary_panel']}")

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=2718, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["m"] > shipping["m"],
        "shipping_m": shipping["m"],
        "doubled_m": doubled["m"],
        "doubled_verification": doubled_reason,
        "shipping_reference_operations": reference_cost["operations"],
        "doubled_reference_operations": 2
        * sum(doubled["d"] ** power for power in range(1, doubled["m"])),
    }
    if not report["G7_scales"]["pass"]:
        raise AssertionError("G7 failed")

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng_local = random.Random(30_000 + seed)
        variable_map = list(range(inst["m"]))
        row_order = list(range(inst["m"]))
        rng_local.shuffle(variable_map)
        rng_local.shuffle(row_order)
        transformed = _relabel_instance(inst, variable_map, row_order)
        if canonical_key(inst) != canonical_key(transformed):
            raise AssertionError("G8 key changed under a composed relabelling")
        invariant_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            raise AssertionError("G8 carried witness failed after relabelling")
        carried_checks += 1
        distinct_keys.append(canonical_key(inst))
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks >= 20 and carried_checks >= 20 and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": carried_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": 20,
        "symmetries_tested": [
            "variable renaming",
            "input-generator reordering",
            "their composition",
        ],
    }
    if not report["G8_canonical_key"]["pass"]:
        raise AssertionError(f"G8 failed: {report['G8_canonical_key']}")

    answer_chars = max(
        len(json.dumps(make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]))
        for seed in range(20)
    )
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atoms(shipping["answer"])
    intended_operations = 148
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }
    if not within_caps:
        raise AssertionError("G9(c) failed")

    report["all_pass"] = all(
        gate.get("pass", False)
        for name, gate in report.items()
        if name.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
