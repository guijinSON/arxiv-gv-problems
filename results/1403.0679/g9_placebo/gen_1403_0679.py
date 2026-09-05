"""Verified problem generator derived from arXiv:1403.0679.

The task is to recover the boundary polynomial of the monomial part of an
Andean primary component of a codimension-two lattice basis ideal.  Instances
are produced in the exact regime of Theorem 5.1.  Their answers are obtained
from that theorem at construction time, never by decomposing the generated
ideal.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# harden.py runs from this directory, while gvlib is at repository root.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This family uses only integer arithmetic and still works.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The first-coordinate residue modulo the gcd of the two target-row "
    "magnitudes is invariant along every relevant band-graph component."
)
PLACEBO_HINT: str = (
    "Careful attention to the target-variable order and exponent bounds helps "
    "avoid transcription mistakes in the polynomial."
)


PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "codimension-two lattice basis ideal over a characteristic-zero field",
        "Andean monomial primary component",
        "sparse boundary polynomial over Q",
    ],
    "verification_operations": [
        "integer sign normalization",
        "Euclidean gcd",
        "exact rational scaling",
        "sparse polynomial support comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize the gcd residue classes preserved by the slice-to-band graph "
        "straightening; without that invariant one scans millions of candidate "
        "boundary exponents or runs a general primary-decomposition procedure."
    ),
    "hardness_basis": (
        "Track B: the enumerative band-boundary algorithm implied by Theorems "
        "2.8 and 5.1 is O(X), where X is the largest target exponent; at the "
        "shipping preset an eight-seed run measured a median 2,327,105 exact "
        "operations and 0.083 seconds per instance, while the gcd-residue "
        "shortcut emits the 16-term polynomial in at most 117 exact operations "
        "and must be recognized without a CAS."
    ),
    "max_answer_tokens": 104,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY: dict = {
    "hard": {"n": 131072, "terms": 16, "lambda_min": 2, "lambda_max": 9},
}
SHIPPING_DIFFICULTY: str = "hard"


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A sparse polynomial over Q in the two listed target variables.  It has "
        "exactly T nonzero terms; every coefficient is [1,1]; exponent pairs are "
        "distinct nonnegative points within the instance rectangle and form an "
        "antichain under componentwise comparison."
    ),
    "bounds": {
        "max_terms": 16,
        "coefficient_choices": 1,
        "coefficient_numerator": 1,
        "coefficient_denominator": 1,
        "exponent_bounds": "instance-specific inclusive rectangle",
    },
}


NOTES: str = (
    "Definition 2.11 fixes I(B) from the two columns of B.  Convention 3.1 and "
    "Example 3.6 identify dependent rows in opposite open quadrants as the "
    "Andean monomial primes.  Lemma 4.6 straightens slice graphs into band "
    "graphs, Theorem 2.8 supplies the gcd residue invariant, and Theorem 5.1 "
    "gives exactly the monomial generators encoded by the answer polynomial.  "
    "Theorem 5.1 also makes Track A false: the component boundary has a direct "
    "gcd formula.  Track B is used because scaling the common gcd leaves 16 "
    "output monomials but makes literal boundary enumeration take millions of "
    "tests.  Target-row and decoy magnitudes overlap.  The attacks try a row-"
    "magnitude outlier seed, the lexicographically smallest antichain, random "
    "antichain restarts, a constant-total-degree ansatz, and a raw-row-step "
    "ansatz; the successful enumerative algorithm is disclosed separately."
)


# Replaced with measurements from the three independent harden.py runs.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_instance(inst) -> tuple[bool, str]:
    try:
        B = inst["B"]
        pair = inst["target_pair"]
    except (KeyError, TypeError):
        return False, "malformed_instance"
    if (
        not isinstance(B, list)
        or len(B) != 3
        or any(
            not isinstance(row, list)
            or len(row) != 2
            or any(not _is_int(v) for v in row)
            for row in B
        )
    ):
        return False, "instance_matrix_shape"
    if (
        not isinstance(pair, list)
        or len(pair) != 2
        or any(not _is_int(i) or not (0 <= i < 3) for i in pair)
        or pair[0] == pair[1]
    ):
        return False, "instance_target_pair"
    if all(B[a][0] * B[b][1] == B[a][1] * B[b][0] for a in range(3) for b in range(a)):
        return False, "instance_rank_below_two"
    first, second = B[pair[0]], B[pair[1]]
    if first[0] == 0 or first[1] == 0 or second[0] == 0 or second[1] == 0:
        return False, "instance_target_on_axis"
    if first[0] * second[1] != first[1] * second[0]:
        return False, "instance_target_not_dependent"
    if not (first[0] * second[0] < 0 and first[1] * second[1] < 0):
        return False, "instance_target_not_opposite"
    return True, "ok"


def _boundary_data(inst) -> dict:
    """Exact Theorem 5.1 data in the listed target-variable order."""
    ok, reason = _validate_instance(inst)
    if not ok:
        raise ValueError(reason)
    B = inst["B"]
    i, j = inst["target_pair"]
    base = [abs(B[i][0]), abs(B[i][1])]
    other = [abs(B[j][0]), abs(B[j][1])]
    d = math.gcd(base[0], base[1])
    total = base[0] + base[1]
    terms = total // d
    ratio_gcd = math.gcd(other[0], base[0])
    lambda_num = other[0] // ratio_gcd
    lambda_den = base[0] // ratio_gcd
    if other[1] * lambda_den != base[1] * lambda_num:
        raise ValueError("inconsistent_target_ratio")
    x_max = total - d
    scaled = lambda_num * x_max
    if scaled % lambda_den:
        raise ValueError("nonintegral_boundary")
    y_max = scaled // lambda_den
    return {
        "d": d,
        "total": total,
        "terms": terms,
        "lambda_num": lambda_num,
        "lambda_den": lambda_den,
        "x_max": x_max,
        "y_max": y_max,
    }


def _theorem_boundary(inst) -> list:
    """Theorem-backed construction of the sparse boundary polynomial."""
    data = _boundary_data(inst)
    answer = []
    for k in range(data["terms"]):
        x_exp = k * data["d"]
        y_num = data["lambda_num"] * (
            data["total"] - (k + 1) * data["d"]
        )
        if y_num % data["lambda_den"]:
            raise AssertionError("Theorem 5.1 produced a nonintegral exponent")
        answer.append([[1, 1], [x_exp, y_num // data["lambda_den"]]])
    return answer


def make_instance(n, seed=0, **params) -> dict:
    """Construct a Theorem 5.1 instance and its certificate without solving it.

    ``n`` controls the common gcd of the two dependent row entries.  Increasing
    it widens the boundary scanned by the reference algorithm while leaving the
    number of answer monomials fixed.
    """
    if not _is_int(n) or n < 1:
        raise ValueError("n must be a positive integer")
    terms = params.pop("terms", 16)
    lambda_min = params.pop("lambda_min", 2)
    lambda_max = params.pop("lambda_max", 9)
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if not _is_int(terms) or not (3 <= terms <= 16):
        raise ValueError("terms must be an integer from 3 through 16")
    if (
        not _is_int(lambda_min)
        or not _is_int(lambda_max)
        or not (2 <= lambda_min <= lambda_max)
    ):
        raise ValueError("lambda bounds must be integers with 2 <= min <= max")

    rng = random.Random(seed)
    # A rational multiplier in [1,2) gives seed diversity and monotone scaling
    # when n is doubled with the same seed.
    scale_code = rng.randrange(1024)
    d = n + (n * scale_code) // 1024
    coprime_splits = [
        u for u in range(2, terms - 1) if math.gcd(u, terms) == 1
    ]
    if not coprime_splits:
        coprime_splits = [u for u in range(1, terms) if math.gcd(u, terms) == 1]
    u = rng.choice(coprime_splits)
    v = terms - u
    multiplier = rng.randint(lambda_min, lambda_max)

    positive = [d * u, d * v]
    negative = [-multiplier * positive[0], -multiplier * positive[1]]
    while True:
        extra = [rng.randint(d, terms * multiplier * d) for _ in range(2)]
        if positive[0] * extra[1] != positive[1] * extra[0]:
            break

    rows = [positive, negative, extra]
    # Reordering/signing columns changes only the chosen binomial generators;
    # reordering rows is a variable relabelling.  Both preserve the task.
    if rng.getrandbits(1):
        rows = [[row[1], row[0]] for row in rows]
    signs = [(-1 if rng.getrandbits(1) else 1) for _ in range(2)]
    rows = [[row[c] * signs[c] for c in range(2)] for row in rows]
    row_order = list(range(3))
    rng.shuffle(row_order)
    inverse_order = {old: new for new, old in enumerate(row_order)}
    B = [rows[old] for old in row_order]
    target_pair = [inverse_order[0], inverse_order[1]]

    inst = {
        "paper": "1403.0679",
        "n": n,
        "B": B,
        "target_pair": target_pair,
        "field": "algebraically closed, characteristic zero",
    }
    inst["answer"] = _theorem_boundary(inst)
    return inst


def render(inst) -> str:
    """Render a self-contained exact primary-component problem."""
    data = _boundary_data(inst)
    matrix_rows = "\n".join(
        f"  row {idx + 1} (variable x{idx + 1}): [{row[0]}, {row[1]}]"
        for idx, row in enumerate(inst["B"])
    )
    i, j = inst["target_pair"]
    statement = f"""Andean primary-component boundary polynomial

Work over an algebraically closed field k of characteristic zero in
k[x1,x2,x3].  For an integer vector mu, let mu+ contain its positive parts
and mu- its negative parts, coordinate by coordinate.  The two columns of the
matrix B below define the codimension-two lattice basis ideal

  I(B) = < x^(mu+) - x^(mu-) : mu is a column of B >.

Here x^(a,b,c) means x1^a*x2^b*x3^c.  The rows of B are:
{matrix_rows}

The ordered target variables are x{i + 1} and x{j + 1}.  Their two rows are
linearly dependent and lie in opposite open quadrants.  Hence
P=<x{i + 1},x{j + 1}> is an Andean minimal prime of I(B).  Let Q be the
P-primary component of I(B); equivalently, Q is the isolated component whose
radical is P.  An ideal Q is P-primary when fg in Q and f not in Q imply that
some positive power of g lies in Q.

The monomials contained in Q form a monomial ideal M in the two target
variables.  Its unique minimal monomial generators are an antichain under
divisibility.  Determine the boundary polynomial F: the coefficient of every
minimal generator is 1 and the support of F is exactly that minimal generating
set.  Exponent pairs are ordered as (exponent of x{i + 1}, exponent of x{j + 1}).

For this instance F is guaranteed to have exactly {data['terms']} nonzero terms.
Every first exponent is in the inclusive interval [0,{data['x_max']}], every
second exponent is in [0,{data['y_max']}], and all exponents are integers.
Term order is irrelevant; repeated exponent pairs are forbidden.

Serialize F as a JSON list of sparse-polynomial terms.  Each term is
[[num,den],[e1,e2]], where [num,den] is a rational coefficient in lowest terms
with positive denominator and [e1,e2] is its exponent pair.  Thus the
coefficient 1 is [1,1].

Give your final answer inside <answer></answer> tags, as one JSON list.
Example syntax: <answer>[[[1,1],[0,12]],[[1,1],[4,0]]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _decode_json_list(text: str):
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json|python)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def parse_answer(text) -> object | None:
    """Extract the last JSON polynomial list from tags, fences, or prose."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    for body in reversed(tagged):
        value = _decode_json_list(body)
        if value is not None:
            return value
    fenced = re.findall(r"```(?:json|python)?\s*(.*?)```", text, flags=re.I | re.S)
    for body in reversed(fenced):
        value = _decode_json_list(body)
        if value is not None:
            return value
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except ValueError:
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check a sparse boundary polynomial exactly, without reading inst['answer']."""
    ok, reason = _validate_instance(inst)
    if not ok:
        return False, reason
    data = _boundary_data(inst)
    if not isinstance(answer, list):
        return False, "answer_not_sparse_polynomial"
    if not answer:
        return False, "empty_polynomial"

    supports = []
    for index, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term_shape_at_{index}"
        coefficient, exponent = term
        if (
            not isinstance(coefficient, list)
            or len(coefficient) != 2
            or any(not _is_int(v) for v in coefficient)
            or coefficient[1] <= 0
        ):
            return False, f"coefficient_shape_at_{index}"
        if coefficient != [1, 1]:
            return False, f"coefficient_not_one_at_{index}"
        if (
            not isinstance(exponent, list)
            or len(exponent) != 2
            or any(not _is_int(v) for v in exponent)
        ):
            return False, f"exponent_shape_at_{index}"
        x_exp, y_exp = exponent
        if not (0 <= x_exp <= data["x_max"] and 0 <= y_exp <= data["y_max"]):
            return False, f"exponent_out_of_range_at_{index}"
        supports.append((x_exp, y_exp))

    if len(set(supports)) != len(supports):
        return False, "duplicate_exponent_pair"
    if len(answer) == data["terms"] - 1:
        return False, "one_term_missing"
    if len(answer) != data["terms"]:
        return False, f"term_count:{len(answer)}_expected_{data['terms']}"
    ordered = sorted(supports)
    if any(
        ordered[k][0] >= ordered[k + 1][0]
        or ordered[k][1] <= ordered[k + 1][1]
        for k in range(len(ordered) - 1)
    ):
        return False, "support_not_divisibility_antichain"

    expected = {tuple(term[1]) for term in _theorem_boundary(inst)}
    if set(supports) != expected:
        return False, "not_the_primary_component_boundary"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the stated antichain language, including its shape rules."""
    data = _boundary_data(inst)
    count = data["terms"]
    xs = sorted(rng.sample(range(data["x_max"] + 1), count))
    ys = sorted(rng.sample(range(data["y_max"] + 1), count), reverse=True)
    return [[[1, 1], [x_exp, y_exp]] for x_exp, y_exp in zip(xs, ys)]


def search_space(inst) -> int | None:
    """Count all fixed-coefficient antichains in the stated exponent rectangle."""
    data = _boundary_data(inst)
    count = data["terms"]
    return math.comb(data["x_max"] + 1, count) * math.comb(
        data["y_max"] + 1, count
    )


def enumerate_all(inst) -> int | None:
    """Brute-force exact valid-answer count when the language has at most 100k words."""
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    data = _boundary_data(inst)
    count = data["terms"]
    valid = 0
    for xs in itertools.combinations(range(data["x_max"] + 1), count):
        for ys_ascending in itertools.combinations(
            range(data["y_max"] + 1), count
        ):
            candidate = [
                [[1, 1], [x_exp, y_exp]]
                for x_exp, y_exp in zip(xs, reversed(ys_ascending))
            ]
            valid += int(verify(inst, candidate)[0])
    return valid


def _canonical_payload(inst) -> str:
    ok, reason = _validate_instance(inst)
    if not ok:
        return "invalid:" + reason
    B = inst["B"]
    target = set(inst["target_pair"])
    representations = []
    for column_order in ((0, 1), (1, 0)):
        for signs in itertools.product((-1, 1), repeat=2):
            transformed = [
                [row[column_order[c]] * signs[c] for c in range(2)] for row in B
            ]
            pair_rows = sorted(transformed[idx] for idx in target)
            other_rows = sorted(
                transformed[idx] for idx in range(len(B)) if idx not in target
            )
            representations.append(
                json.dumps(
                    {"target_rows": pair_rows, "other_rows": other_rows},
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
    return min(representations)


def canonical_key(inst) -> str:
    """Canonicalize variable relabellings and signed/reordered ideal generators."""
    return hashlib.sha256(_canonical_payload(inst).encode("utf-8")).hexdigest()


def escalate(params) -> dict | str | None:
    """Double the scan-width scale while keeping the 16-term witness fixed."""
    result = dict(params)
    current = result.get("n", 1)
    if not _is_int(current) or current < 1:
        return None
    # Exponents grow only logarithmically in the serialized answer.  This guard
    # is far beyond the hardening ladder but distinguishes a format cap cleanly.
    if len(str(current)) > 80:
        return "cap_bound"
    result["n"] = current * 2
    return result


def _reference_boundary_scan(inst) -> tuple[list, int]:
    """Enumerate every candidate first exponent on the band boundary.

    This is the literal O(X) route: for each integer coordinate, test its gcd
    residue and, when eligible, evaluate the exact rational boundary height.
    The compact route instead jumps directly by d.
    """
    data = _boundary_data(inst)
    answer = []
    operations = 0
    for x_exp in range(data["x_max"] + 1):
        operations += 1  # residue test
        if x_exp % data["d"]:
            continue
        operations += 3  # subtraction, multiplication, divisibility test
        y_num = data["lambda_num"] * (data["x_max"] - x_exp)
        if y_num % data["lambda_den"]:
            continue
        operations += 1  # exact division
        y_exp = y_num // data["lambda_den"]
        answer.append([[1, 1], [x_exp, y_exp]])
    return answer, operations


def _candidate_ok(inst, candidate) -> bool:
    return candidate is not None and verify(inst, candidate)[0]


def _attack_outlier_entry_magnitudes(inst):
    data = _boundary_data(inst)
    magnitude_seed = 0
    for row in inst["B"]:
        magnitude_seed = (magnitude_seed * 1_000_003 + abs(row[0]) + abs(row[1]))
    return random_candidate(inst, random.Random(magnitude_seed))


def _attack_greedy_lexicographic(inst):
    data = _boundary_data(inst)
    count = data["terms"]
    xs = list(range(count))
    ys = list(range(count - 1, -1, -1))
    return [[[1, 1], [x_exp, y_exp]] for x_exp, y_exp in zip(xs, ys)]


def _attack_constant_total_degree(inst):
    data = _boundary_data(inst)
    count = data["terms"]
    xs = [(k * data["x_max"]) // (count - 1) for k in range(count)]
    # The tempting ordinary homogeneous ansatz ignores the non-unit row ratio.
    ys = [data["x_max"] - x_exp for x_exp in xs]
    return [[[1, 1], [x_exp, y_exp]] for x_exp, y_exp in zip(xs, ys)]


def _attack_raw_row_step(inst):
    data = _boundary_data(inst)
    i = inst["target_pair"][0]
    step = min(abs(value) for value in inst["B"][i])
    modulus_x = data["x_max"] + 1
    modulus_y = data["y_max"] + 1
    xs = sorted({(k * step) % modulus_x for k in range(data["terms"] * 3)})
    ys = sorted(
        {(k * step) % modulus_y for k in range(data["terms"] * 3)}, reverse=True
    )
    if len(xs) < data["terms"] or len(ys) < data["terms"]:
        return _attack_greedy_lexicographic(inst)
    return [
        [[1, 1], [x_exp, y_exp]]
        for x_exp, y_exp in zip(xs[: data["terms"]], ys[: data["terms"]])
    ]


def _attack_random_restart(inst, rng, restarts=128):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if _candidate_ok(inst, candidate):
            return candidate, restarts
    return None, restarts


def _swap_polynomial_variables(answer):
    swapped = copy.deepcopy(answer)
    for term in swapped:
        term[1][0], term[1][1] = term[1][1], term[1][0]
    return swapped


def _transform_instance(
    inst,
    row_order=(0, 1, 2),
    column_order=(0, 1),
    column_signs=(1, 1),
    reverse_target=False,
):
    transformed = copy.deepcopy(inst)
    old_B = inst["B"]
    transformed["B"] = [
        [
            old_B[old][column_order[c]] * column_signs[c]
            for c in range(2)
        ]
        for old in row_order
    ]
    inverse = {old: new for new, old in enumerate(row_order)}
    transformed["target_pair"] = [inverse[idx] for idx in inst["target_pair"]]
    transformed["answer"] = copy.deepcopy(inst["answer"])
    if reverse_target:
        transformed["target_pair"].reverse()
        transformed["answer"] = _swap_polynomial_variables(transformed["answer"])
    return transformed


def _answer_metrics(answer) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def count_atoms(value):
        if isinstance(value, list):
            return sum(count_atoms(item) for item in value)
        if isinstance(value, dict):
            return sum(count_atoms(item) for item in value.values())
        return 1

    chars = len(encoded)
    tokens = math.ceil(chars / 4)
    return chars, tokens, count_atoms(answer)


def _euclid_steps(a: int, b: int) -> int:
    steps = 0
    while b:
        a, b = b, a % b
        steps += 1
    return steps


def _intended_route_operations(inst) -> int:
    data = _boundary_data(inst)
    i, j = inst["target_pair"]
    base = [abs(value) for value in inst["B"][i]]
    other = [abs(value) for value in inst["B"][j]]
    # Conservative explicit accounting: sign normalization, two Euclidean
    # reductions, scalar setup, and four integer operations per emitted term.
    return (
        16
        + _euclid_steps(base[0], base[1])
        + _euclid_steps(other[0], base[0])
        + 6 * data["terms"]
    )


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "1403.0679",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every preset, multiple seeds, exact verification and JSON round-trip.
    failures = []
    attempts = 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 2, 19):
            candidate_inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(candidate_inst, candidate_inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(candidate_inst["answer"])) != candidate_inst["answer"]:
                failures.append(
                    {"preset": preset, "seed": seed, "reason": "not_json_native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=731, **ship_params)
    planted = inst["answer"]
    data = _boundary_data(inst)

    # G2: natural corruptions are rejected through distinct checker branches.
    dropped = copy.deepcopy(planted[:-1])
    swapped = copy.deepcopy(planted)
    swapped[1][1][1], swapped[2][1][1] = swapped[2][1][1], swapped[1][1][1]
    duplicate = copy.deepcopy(planted)
    duplicate[1] = copy.deepcopy(duplicate[0])
    out_of_range = copy.deepcopy(planted)
    out_of_range[0][1][0] = data["x_max"] + 1
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The preserved residue classes give the sparse boundary.\n\n"
        "<answer>\n```json\n"
        + json.dumps(planted)
        + "\n```\n</answer>\nThe terms are in increasing first exponent."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_reason = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_reason,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4 and shipping-density portion of G5: sample only stated antichains.
    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    expected_support = {tuple(term[1]) for term in planted}
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if {tuple(term[1]) for term in candidate} == expected_support:
            guess_hits += 1
    density_wall = time.perf_counter() - density_start
    observed = guess_hits / guess_total
    language_size = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": language_size is not None
        and language_size > 1_000_000
        and observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "exact_probability_from_unique_boundary": f"1/{language_size}",
        "candidate_prior": (
            "uniform over T-term divisibility antichains in the displayed rectangle"
        ),
        "search_space": str(language_size),
    }

    # G6: four no-tool attacks fail; the successful Track B algorithm is separate.
    attack_seeds = list(range(9100, 9108))
    success_counts = {
        "outlier_entry_magnitudes": 0,
        "greedy_lexicographic_antichain": 0,
        "random_restart_128": 0,
        "constant_total_degree_ansatz": 0,
        "raw_row_entry_step_ansatz": 0,
    }
    restart_candidates = 0
    reference_successes = 0
    reference_total_operations = 0
    reference_per_instance_operations = []
    reference_total_wall = 0.0
    reference_per_seed_wall = []
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **ship_params)
        if _candidate_ok(attack_inst, _attack_outlier_entry_magnitudes(attack_inst)):
            success_counts["outlier_entry_magnitudes"] += 1
        if _candidate_ok(attack_inst, _attack_greedy_lexicographic(attack_inst)):
            success_counts["greedy_lexicographic_antichain"] += 1
        restarted, candidates = _attack_random_restart(
            attack_inst, random.Random(seed ^ 0x5A17), 128
        )
        restart_candidates += candidates
        if _candidate_ok(attack_inst, restarted):
            success_counts["random_restart_128"] += 1
        if _candidate_ok(attack_inst, _attack_constant_total_degree(attack_inst)):
            success_counts["constant_total_degree_ansatz"] += 1
        if _candidate_ok(attack_inst, _attack_raw_row_step(attack_inst)):
            success_counts["raw_row_entry_step_ansatz"] += 1

        started = time.perf_counter()
        reference_answer, operations = _reference_boundary_scan(attack_inst)
        elapsed = time.perf_counter() - started
        reference_total_wall += elapsed
        reference_per_seed_wall.append(round(elapsed, 6))
        reference_total_operations += operations
        reference_per_instance_operations.append(operations)
        reference_successes += int(_candidate_ok(attack_inst, reference_answer))

    attacks = {
        name: {"successes": count, "attempts": len(attack_seeds)}
        for name, count in success_counts.items()
    }
    attacks["random_restart_128"]["candidates"] = restart_candidates
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    sorted_ops = sorted(reference_per_instance_operations)
    median_ops = (sorted_ops[3] + sorted_ops[4]) // 2
    sorted_wall = sorted(reference_per_seed_wall)
    median_wall = (sorted_wall[3] + sorted_wall[4]) / 2
    reference = {
        "name": "enumerative band-boundary residue scan",
        "complexity": "O(X) exact integer residue tests, X=max first exponent",
        "wall_clock_sec": round(reference_total_wall, 6),
        "wall_clock_sec_per_seed": reference_per_seed_wall,
        "median_wall_clock_sec_per_instance": round(median_wall, 6),
        "operations": reference_total_operations,
        "operations_per_instance": reference_per_instance_operations,
        "median_operations_per_instance": median_ops,
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4 and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    demo = make_instance(seed=731, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6
        and all_failed
        and reference_successes == len(attack_seeds)
        and demo_count == 1,
        "shipping_density": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": observed,
            "wall_clock_sec": round(density_wall, 6),
            "exact_fraction_from_unique_boundary": f"1/{language_size}",
        },
        "demo_exact_valid_answers": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_baseline": reference,
    }

    doubled_start = time.perf_counter()
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=731, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and _boundary_data(doubled)["x_max"] > data["x_max"]
        and len(doubled["answer"]) == len(planted),
        "base_n": inst["n"],
        "base_boundary_width": data["x_max"],
        "doubled_n": doubled["n"],
        "doubled_boundary_width": _boundary_data(doubled)["x_max"],
        "answer_terms_before": len(planted),
        "answer_terms_after": len(doubled["answer"]),
        "build_and_verify_sec": round(time.perf_counter() - doubled_start, 6),
        "verify_reason": doubled_reason,
    }

    # G8: row permutations, signed/ordered columns, and target-order reversal.
    invariance_checks = 0
    transport_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base_inst = make_instance(seed=seed, **DIFFICULTY["easy"])
        base_key = canonical_key(base_inst)
        unrelated_keys.append(base_key)
        transforms = [
            _transform_instance(base_inst, row_order=(2, 0, 1)),
            _transform_instance(base_inst, column_order=(1, 0)),
            _transform_instance(base_inst, column_signs=(-1, 1)),
            _transform_instance(
                base_inst,
                row_order=(1, 2, 0),
                column_order=(1, 0),
                column_signs=(-1, -1),
            ),
            _transform_instance(
                base_inst,
                row_order=(2, 1, 0),
                column_order=(1, 0),
                column_signs=(1, -1),
                reverse_target=True,
            ),
        ]
        for transformed in transforms:
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                g8_failures.append({"seed": seed, "kind": "key_changed"})
            transport_checks += 1
            transported_ok, transported_reason = verify(
                transformed, transformed["answer"]
            )
            if not transported_ok:
                g8_failures.append(
                    {
                        "seed": seed,
                        "kind": "transport_failed",
                        "reason": transported_reason,
                    }
                )
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures
        and invariance_checks >= 20
        and transport_checks >= 20
        and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "transport_checks": transport_checks,
        "unrelated_distinct": distinct_keys,
        "unrelated_attempts": 20,
        "transformations": [
            "variable-row permutation",
            "binomial-generator column permutation",
            "individual generator sign change",
            "compositions of those maps",
            "target-order reversal with polynomial-variable transport",
        ],
        "failures": g8_failures,
    }

    chars, tokens, elements = _answer_metrics(planted)
    intended_operations = _intended_route_operations(inst)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_pass"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
