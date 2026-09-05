"""Verified exact tensor-identity generator for arXiv:1303.6914."""
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
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None

TRACK: str = "B"
PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "simple tensors over Q in Q^3 tensor Q^d tensor Q^d",
        "polynomially parametrized rank-one tensors",
        "exact rational tensor dependence",
    ],
    "verification_operations": [
        "exact rational normalization",
        "integer polynomial evaluation",
        "exact tensor-coordinate moment comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The paired parameters are roots of one even polynomial, and reciprocal "
        "derivatives at those roots annihilate every coordinate polynomial; "
        "without that invariant one flattens the tensors and computes a nullspace."
    ),
    "hardness_basis": (
        "Track B: exact tensor flattening and rational Gaussian elimination uses "
        "O(d^4) field operations on a 3*d^2 by 2*d+4 matrix with O(nd)-bit "
        "operands; at shipping it measured 12,837 rational operations and about "
        "0.03 seconds, while the paired-root barycentric route uses 136 exact "
        "operations at d=6."
    ),
    "max_answer_tokens": 167,
}
NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}
CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An ordered vector of m=2d+4 distinct nonzero unit fractions [s,q], "
        "s in {-1,1}, 1<=q<=D, whose coefficient set is closed under negation."
    ),
    "bounds": {
        "length": "2*dimension+4", "absolute_numerator": 1,
        "max_denominator": "instance denominator_bound D",
        "pairwise_distinct": True, "closed_under_negation": True,
    },
}
DIFFICULTY: dict = {
    "medium": {"n": 9, "dimension": 6, "mix_bound": 2, "mix_rounds": 24},
}
SHIPPING_DIFFICULTY: str = "medium"
STRUCTURAL_HINT: str = (
    "The paired parameters are roots of one even polynomial, whose derivative values control its barycentric functional."
)
PLACEBO_HINT: str = (
    "Careful tracking of the displayed order and rational signs helps avoid routine transcription errors."
)
G9_EVIDENCE = {
    "arms": {name: {"solved": 0, "attempts": 0} for name in ("bare", "hinted", "placebo")},
    "hinted_verdict": "not_run",
}
NOTES: str = r"""
Definition 2.1 defines k-identifiability as uniqueness of a sum of k simple
tensors. Lemmas 3.2--3.3 use a special (3,1,1) Segre-Veronese fourfold and an
ancillary Macaulay2 calculation; Theorem 3.5 then proves that a general
rank-eight tensor in C^3 tensor C^6 tensor C^6 has at least six decompositions.
Remark 3.7 says the exact number is unknown.

That proof is existential and does not output alternate decompositions for a
scalable exact sampler. This module stays in the paper's simple-tensor language
but composes a special identity. For P(z)=product_j(z^2-x_j^2), the functional
sum_{P(t)=0} f(t)/P'(t) vanishes for deg(f)<=14. At d=6 all tensor-coordinate
products have degrees 0,...,14, so normalized reciprocal derivatives give a
dependence of sixteen simple tensors. Its two signs give two eight-term
decompositions, and unimodular mode changes preserve the certificate.

This is Track B: exact flattening plus rational Gaussian elimination is the
known polynomial reference method. The compact route uses
P'(x_j)=2*x_j*product_{k!=j}(x_j^2-x_k^2), one gcd, and a reorder. Increasing n
raises node and coefficient bit size while the witness stays at sixteen unit
fractions and the compact route stays below 300 operations. The construction
is a rational special family: it does not claim genericity, minimal rank, or
the paper's lower bound of six decompositions.
""".strip()


def _validate(n, dimension, mix_bound, mix_rounds):
    for name, value in (("n", n), ("dimension", dimension),
                        ("mix_bound", mix_bound), ("mix_rounds", mix_rounds)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if not 3 <= n <= 60:
        raise ValueError("n must be between 3 and 60")
    if dimension < 3 or (1 << n) < dimension + 2:
        raise ValueError("dimension must be >=3 and dimension+2 must not exceed 2^n")
    if mix_bound < 1 or mix_rounds < 0:
        raise ValueError("invalid mixing parameters")


def _identity(size):
    return [[int(i == j) for j in range(size)] for i in range(size)]


def _unimodular(size, rng, bound, rounds):
    matrix = _identity(size)
    for _ in range(rounds):
        source = rng.randrange(size)
        target = rng.randrange(size - 1)
        if target >= source:
            target += 1
        coefficient = rng.randint(1, bound) * (-1 if rng.randrange(2) else 1)
        matrix[target] = [x + coefficient * y for x, y in zip(matrix[target], matrix[source])]
    rng.shuffle(matrix)
    for row in matrix:
        if rng.randrange(2):
            row[:] = [-value for value in row]
    return matrix


def _matmul(first, second):
    return [[sum(first[i][k] * second[k][j] for k in range(len(second)))
             for j in range(len(second[0]))] for i in range(len(first))]


def _omission_orbits(dimension):
    limit = dimension + 1
    choices = set()
    for first in range(1, dimension + 1):
        for second in range(first + 1, dimension + 1):
            pair = (first, second)
            reverse = (limit - second, limit - first)
            choices.add(min(pair, reverse))
    return sorted(choices)


def _positive_derivatives(nodes):
    squares = [node * node for node in nodes]
    result = []
    for i, node in enumerate(nodes):
        value = 2 * node
        for j, square in enumerate(squares):
            if i != j:
                value *= squares[i] - square
        result.append(value)
    return result


def _sample_nodes(size_bits, rank, rng):
    for attempt in range(1, 10001):
        nodes = sorted(rng.sample(range(1, (1 << size_bits) + 1), rank))
        derivatives = _positive_derivatives(nodes)
        common = math.gcd(*(abs(value) for value in derivatives))
        denominators = [abs(value) // common for value in derivatives]
        if len(set(denominators)) == rank:
            return nodes, derivatives, attempt
    raise RuntimeError("could not sample distinct normalized derivative magnitudes")


def make_instance(n, seed=0, dimension=6, mix_bound=2, mix_rounds=None, **params):
    """Build the barycentric certificate first; never solve the finished tensor."""
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if mix_rounds is None:
        mix_rounds = 4 * dimension
    _validate(n, dimension, mix_bound, mix_rounds)
    rng = random.Random(seed)
    rank = dimension + 2
    positive, derivatives, sampling_attempt = _sample_nodes(n, rank, rng)
    common = math.gcd(*(abs(value) for value in derivatives))
    derivative = {}
    for node, value in zip(positive, derivatives):
        derivative[node], derivative[-node] = value, -value
    nodes = [value for node in positive for value in (node, -node)]
    rng.shuffle(nodes)
    answer = [[1 if derivative[t] > 0 else -1, abs(derivative[t]) // common] for t in nodes]
    omitted = _omission_orbits(dimension)[seed % len(_omission_orbits(dimension))]
    exponents = {
        "a": [0, 1, 2],
        "b": list(range(dimension)),
        "c": [e for e in range(dimension + 2) if e not in omitted],
    }
    maps = {
        "a": _unimodular(3, rng, mix_bound, min(mix_rounds, 12)),
        "b": _unimodular(dimension, rng, mix_bound, mix_rounds),
        "c": _unimodular(dimension, rng, mix_bound, mix_rounds),
    }
    return {
        "n": n, "dimension": dimension, "rank": rank, "term_count": 2 * rank,
        "top_degree": 2 * rank - 2, "a_exponents": exponents["a"],
        "b_exponents": exponents["b"], "c_exponents": exponents["c"],
        "positive_nodes": positive, "nodes": nodes, "maps": maps,
        "denominator_bound": max(q for _s, q in answer),
        "sampling_attempt": sampling_attempt, "answer": answer,
    }


def _compact_json(value):
    return json.dumps(value, separators=(",", ":"))


def render(inst):
    d, m = inst["dimension"], inst["term_count"]
    statement = f"""Exact dependence among simple tensors

All arithmetic is over Q. For exponents E and integer t, phi_E(t) is the
column vector [t^e for e in E], in the displayed order.

E_A = {_compact_json(inst['a_exponents'])}
E_B = {_compact_json(inst['b_exponents'])}
E_C = {_compact_json(inst['c_exponents'])}
M_A = {_compact_json(inst['maps']['a'])}
M_B = {_compact_json(inst['maps']['b'])}
M_C = {_compact_json(inst['maps']['c'])}

For each t_i below form a_i=M_A phi_E_A(t_i), b_i=M_B phi_E_B(t_i),
c_i=M_C phi_E_C(t_i), and the simple tensor T_i=a_i tensor b_i tensor c_i.
Its (r,s,u) coordinate is a_i[r]*b_i[s]*c_i[u]. All indices are 0-based.
The {m} parameters, in tensor-index order, are
t = {_compact_json(inst['nodes'])}

Find exactly {m} pairwise-distinct nonzero rationals lambda_i with
sum_i lambda_i T_i = 0 in Q^3 tensor Q^{d} tensor Q^{d}.
A coefficient is [s,q], meaning s/q, where s is exactly -1 or 1 and
1 <= q <= {inst['denominator_bound']}. The unordered coefficient set must be
closed under negation: [1,q] occurs iff [-1,q] occurs, each exactly once.
Order matters: coefficient i multiplies T_i. Any witness obeying all rules is
accepted. Moving the two signs to opposite sides gives equal-length tensor
decompositions.

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{m} pairs [[s_0,q_0],...,[s_{m-1},q_{m-1}]].
Example: <answer>[[1,2],[-1,2],[1,5],[-1,5]]</answer>
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
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    candidates = list(reversed(matches)) + [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = re.sub(r"\s*```$", "", re.sub(r"^```(?:json)?\s*", "", candidate.strip(), flags=re.I))
        try:
            value = json.loads(cleaned)
            if isinstance(value, list):
                return value
        except (TypeError, ValueError):
            pass
        for position, character in enumerate(cleaned):
            if character == "[":
                try:
                    value, _ = decoder.raw_decode(cleaned[position:])
                    if isinstance(value, list):
                        return value
                except ValueError:
                    pass
    return None


def _coefficient_data(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be a list"
    if not answer:
        return None, "answer must be a nonempty list"
    if len(answer) != inst["term_count"]:
        return None, f"expected {inst['term_count']} coefficients, received {len(answer)}"
    result = []
    for i, item in enumerate(answer):
        if not (isinstance(item, list) and len(item) == 2):
            return None, f"coefficient {i} is not a [sign,denominator] pair"
        sign, denominator = item
        if any(isinstance(x, bool) or not isinstance(x, int) for x in item):
            return None, f"coefficient {i} does not contain two integers"
        if sign not in (-1, 1):
            return None, f"coefficient {i} has numerator other than -1 or 1"
        if denominator <= 0:
            return None, f"coefficient {i} has a nonpositive denominator"
        if denominator > inst["denominator_bound"]:
            return None, f"coefficient {i} exceeds the denominator bound"
        result.append((sign, denominator))
    if len(set(result)) != len(result):
        return None, "coefficients must be pairwise distinct"
    if any((-sign, q) not in set(result) for sign, q in result):
        return None, "coefficient set must be closed under negation"
    return result, "ok"


def verify(inst, answer):
    coefficients, reason = _coefficient_data(inst, answer)
    if coefficients is None:
        return False, reason
    common = math.lcm(*(q for _s, q in coefficients))
    for degree in range(inst["top_degree"] + 1):
        total = sum(s * (common // q) * t**degree
                    for (s, q), t in zip(coefficients, inst["nodes"]))
        if total:
            return False, f"tensor-coordinate moment of degree {degree} is nonzero"
    return True, "ok"


def random_candidate(inst, rng):
    denominators, used = [], set()
    while len(denominators) < inst["rank"]:
        value = rng.randrange(1, inst["denominator_bound"] + 1)
        if value not in used:
            used.add(value)
            denominators.append(value)
    candidate = [[sign, q] for q in denominators for sign in (1, -1)]
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return math.comb(inst["denominator_bound"], inst["rank"]) * math.factorial(inst["term_count"])


def enumerate_all(inst):
    """Brute-force the declared language only when its exact size is modest."""
    space = search_space(inst)
    if space > 100_000:
        return None
    valid = 0
    for denominators in itertools.combinations(
            range(1, inst["denominator_bound"] + 1), inst["rank"]):
        signed = tuple((sign, q) for q in denominators for sign in (1, -1))
        for ordering in itertools.permutations(signed):
            candidate = [[sign, q] for sign, q in ordering]
            valid += int(verify(inst, candidate)[0])
    return valid


def canonical_key(inst):
    positive = sorted(abs(t) for t in inst["nodes"] if t > 0)
    common = math.gcd(*positive)
    payload = {
        "dimensions": [3, inst["dimension"], inst["dimension"]],
        "a": sorted(inst["a_exponents"]),
        "equal_modes": sorted([sorted(inst["b_exponents"]), sorted(inst["c_exponents"])]),
        "positive_nodes_up_to_scale": [t // common for t in positive],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _answer_upper_chars(n, dimension):
    rank, terms = dimension + 2, 2 * dimension + 4
    digits = math.ceil((1 + (terms - 1) * n) * math.log10(2))
    return rank * (2 * digits + 9) + terms + 1


def escalate(params):
    values = {key: value for key, value in params.items() if key != "_preset"}
    next_n = int(values["n"]) + 2
    if _answer_upper_chars(next_n, int(values.get("dimension", 6))) > 2000:
        return "cap_bound"
    values["n"] = next_n
    return values


def _mode_values(matrix, exponents, node):
    powers, operations = [1], 0
    for _ in range(max(exponents)):
        powers.append(powers[-1] * node)
        operations += 1
    basis, result = [powers[e] for e in exponents], []
    for row in matrix:
        total = 0
        for coefficient, value in zip(row, basis):
            total += coefficient * value
            operations += 2
        result.append(total)
    return result, operations


def _reference_nullspace(inst):
    """Standard exact tensor flattening followed by rational elimination."""
    started, operations = time.perf_counter(), 0
    factors = {name: [] for name in ("a", "b", "c")}
    for node in inst["nodes"]:
        for name in factors:
            values, count = _mode_values(inst["maps"][name], inst[f"{name}_exponents"], node)
            factors[name].append(values)
            operations += count
    terms, basis, rows_processed = inst["term_count"], {}, 0
    complete = False
    for ia in range(3):
        for ib in range(inst["dimension"]):
            for ic in range(inst["dimension"]):
                row = []
                for column in range(terms):
                    value = factors["a"][column][ia] * factors["b"][column][ib]
                    value *= factors["c"][column][ic]
                    row.append(Fraction(value))
                    operations += 2
                rows_processed += 1
                for pivot in sorted(basis):
                    factor = row[pivot]
                    if factor:
                        for j in range(pivot, terms):
                            row[j] -= factor * basis[pivot][j]
                            operations += 2
                pivot = next((j for j, value in enumerate(row) if value), None)
                if pivot is not None:
                    divisor = row[pivot]
                    for j in range(pivot, terms):
                        row[j] /= divisor
                        operations += 1
                    basis[pivot] = row
                if len(basis) == terms - 1:
                    complete = True
                    break
            if complete:
                break
        if complete:
            break
    stats = {"wall_clock_sec": time.perf_counter() - started,
             "operations": operations, "rows_processed": rows_processed,
             "rank": len(basis)}
    if len(basis) != terms - 1:
        return None, stats
    free = [j for j in range(terms) if j not in basis]
    if len(free) != 1:
        return None, stats
    vector = [Fraction(0) for _ in range(terms)]
    vector[free[0]] = Fraction(1)
    for pivot in sorted(basis, reverse=True):
        vector[pivot] = -sum(basis[pivot][j] * vector[j] for j in range(pivot + 1, terms))
        operations += 2 * (terms - pivot - 1)
    common = math.lcm(*(value.denominator for value in vector))
    integers = [value.numerator * (common // value.denominator) for value in vector]
    divisor = math.gcd(*(abs(value) for value in integers))
    integers = [value // divisor for value in integers]
    multiple = math.lcm(*(abs(value) for value in integers))
    candidate = [[1 if value > 0 else -1, multiple // abs(value)] for value in integers]
    stats["operations"] = operations
    return candidate, stats


def _compact_barycentric(inst):
    positive = sorted(inst["positive_nodes"])
    squares = [node * node for node in positive]
    operations, derivatives = len(positive), []
    for i, node in enumerate(positive):
        value = 2 * node
        operations += 1
        for j, square in enumerate(squares):
            if i != j:
                value *= squares[i] - square
                operations += 2
        derivatives.append(value)
    common = 0
    for value in derivatives:
        common = math.gcd(common, abs(value))
        operations += 1
    by_node = {}
    for node, value in zip(positive, derivatives):
        pair = [1 if value > 0 else -1, abs(value) // common]
        by_node[node], by_node[-node] = pair, [-pair[0], pair[1]]
    return [by_node[node] for node in inst["nodes"]], {"operations": operations}


def _factor_height(inst, column):
    node, height = inst["nodes"][column], 0
    for name in ("a", "b", "c"):
        basis = [node**e for e in inst[f"{name}_exponents"]]
        values = [sum(x * y for x, y in zip(row, basis)) for row in inst["maps"][name]]
        height += sum(abs(value) for value in values)
    return height


def _paired(denominators):
    return [[sign, q] for q in denominators for sign in (1, -1)]


def _attack_outlier_height(inst):
    order = sorted(range(inst["term_count"]), key=lambda i: (_factor_height(inst, i), i))
    answer = [None] * inst["term_count"]
    for column, value in zip(order, _paired(range(1, inst["rank"] + 1))):
        answer[column] = value
    return answer


def _attack_greedy_first_moment(inst):
    columns = sorted(range(inst["term_count"]), key=lambda i: (-abs(inst["nodes"][i]), i))
    available = [(sign, q) for q in range(1, inst["rank"] + 1) for sign in (1, -1)]
    answer, total = [None] * inst["term_count"], Fraction(0)
    for column in columns:
        node = inst["nodes"][column]
        choice = min(available,
                     key=lambda item: (abs(total + Fraction(item[0] * node, item[1])), item))
        answer[column] = [choice[0], choice[1]]
        total += Fraction(choice[0] * node, choice[1])
        available.remove(choice)
    return answer


def _attack_pair_opposites(inst):
    answer = [None] * inst["term_count"]
    for q, node in enumerate(sorted(inst["positive_nodes"]), 1):
        answer[inst["nodes"].index(node)] = [1, q]
        answer[inst["nodes"].index(-node)] = [-1, q]
    return answer


def _attack_random_restart(inst, rng, restarts=256):
    base = _paired(range(1, inst["rank"] + 1))
    for _ in range(restarts):
        candidate = copy.deepcopy(base)
        rng.shuffle(candidate)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _permute_columns(inst, permutation):
    transformed = copy.deepcopy(inst)
    transformed["nodes"] = [inst["nodes"][i] for i in permutation]
    transformed["answer"] = [inst["answer"][i] for i in permutation]
    return transformed


def _change_mode_bases(inst, seed):
    transformed, rng = copy.deepcopy(inst), random.Random(seed)
    for name, size in (("a", 3), ("b", inst["dimension"]), ("c", inst["dimension"])):
        transformed["maps"][name] = _matmul(_unimodular(size, rng, 2, 2 * size),
                                             transformed["maps"][name])
    return transformed


def _scale_nodes(inst, factor):
    transformed = copy.deepcopy(inst)
    transformed["positive_nodes"] = [factor * x for x in inst["positive_nodes"]]
    transformed["nodes"] = [factor * x for x in inst["nodes"]]
    return transformed


def _swap_equal_modes(inst):
    transformed = copy.deepcopy(inst)
    transformed["b_exponents"], transformed["c_exponents"] = transformed["c_exponents"], transformed["b_exponents"]
    transformed["maps"]["b"], transformed["maps"]["c"] = transformed["maps"]["c"], transformed["maps"]["b"]
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY,
              "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY]}
    failures, attempts = [], 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures, "verified": attempts - len(failures),
        "attempts": attempts, "json_roundtrips": attempts, "failures": failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    bad = {
        "empty": [],
        "dropped": copy.deepcopy(shipping["answer"][:-1]),
        "swapped": copy.deepcopy(shipping["answer"]),
        "duplicated": copy.deepcopy(shipping["answer"]),
        "out_of_range": copy.deepcopy(shipping["answer"]),
    }
    bad["swapped"][0], bad["swapped"][1] = bad["swapped"][1], bad["swapped"][0]
    bad["duplicated"][1] = bad["duplicated"][0]
    bad["out_of_range"][0] = [1, shipping["denominator_bound"] + 1]
    reasons = {name: verify(shipping, candidate)[1] for name, candidate in bad.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(not verify(shipping, x)[0] for x in bad.values())
                and len(set(reasons.values())) == len(reasons),
        "reasons": reasons, "distinct_reasons": len(set(reasons.values())),
    }

    response = "Prose.\n```json\n<answer>\n" + json.dumps(shipping["answer"]) + "\n</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "model_style_roundtrip": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng, total, hits = random.Random(20260905), 200_000, 0
    started = time.perf_counter()
    for _ in range(total):
        if verify(shipping, random_candidate(shipping, rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    space, exact = search_space(shipping), enumerate_all(shipping)
    sampled_density = hits / total
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6, "hits": hits, "total": total,
        "empirical_probability": hits / total, "structure_aware": True,
        "candidate_space": space, "wall_clock_sec": guess_seconds,
    }

    reference, compact = [], []
    successes = {name: 0 for name in (
        "outlier_factor_height", "greedy_minimize_degree_one",
        "random_restart_256", "in_context_pair_opposites")}
    well_formed = {name: 0 for name in successes}
    adversary_attempts = 8
    for seed in range(adversary_attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        answer, stats = _reference_nullspace(inst)
        stats["verified"] = answer is not None and verify(inst, answer)[0]
        reference.append(stats)
        answer, stats = _compact_barycentric(inst)
        stats["verified"] = verify(inst, answer)[0]
        compact.append(stats)
        candidates = {
            "outlier_factor_height": _attack_outlier_height(inst),
            "greedy_minimize_degree_one": _attack_greedy_first_moment(inst),
            "in_context_pair_opposites": _attack_pair_opposites(inst),
        }
        for name, candidate in candidates.items():
            well_formed[name] += int(_coefficient_data(inst, candidate)[0] is not None)
            successes[name] += int(verify(inst, candidate)[0])
        probe = _paired(range(1, inst["rank"] + 1))
        random.Random(8000 + seed).shuffle(probe)
        well_formed["random_restart_256"] += int(_coefficient_data(inst, probe)[0] is not None)
        successes["random_restart_256"] += int(
            _attack_random_restart(inst, random.Random(9000 + seed)) is not None)

    wall = statistics.median(item["wall_clock_sec"] for item in reference)
    operations = int(statistics.median(item["operations"] for item in reference))
    report["G5_density_and_baseline"] = {
        "pass": isinstance(sampled_density, float)
                and all(item["verified"] for item in reference),
        "shipping_exact_solution_count": exact,
        "shipping_candidate_space": space,
        "shipping_density_method": "structure-aware Monte Carlo",
        "shipping_sampled_density": sampled_density,
        "shipping_valid_hits": hits, "shipping_density_samples": total,
        "baseline_wall_clock_sec": wall, "baseline_operations": operations,
        "baseline_rows": int(statistics.median(item["rows_processed"] for item in reference)),
    }
    attacks = {name: {"successes": count, "attempts": adversary_attempts,
                      "well_formed": well_formed[name]}
               for name, count in successes.items()}
    report["G6_adversary_panel"] = {
        "pass": all(x["successes"] == 0 and x["well_formed"] == adversary_attempts
                    for x in attacks.values())
                and all(x["verified"] for x in reference)
                and all(x["verified"] for x in compact),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "dense tensor flattening plus exact rational Gaussian elimination",
            "complexity": "O(d^4) rational operations with O(nd)-bit operands",
            "wall_clock_sec_median": wall, "operations_median": operations,
            "solves": f"{sum(x['verified'] for x in reference)}/{adversary_attempts}, as expected",
        },
        "compact_route": {
            "name": "paired-root barycentric derivative products",
            "operations": int(statistics.median(x["operations"] for x in compact)),
            "solves": f"{sum(x['verified'] for x in compact)}/{adversary_attempts}",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=2718, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["denominator_bound"].bit_length()
                > shipping["denominator_bound"].bit_length(),
        "shipping_n": shipping["n"], "doubled_n": doubled["n"],
        "answer_elements_fixed": _answer_atoms(shipping["answer"]),
        "shipping_denominator_bits": shipping["denominator_bound"].bit_length(),
        "doubled_denominator_bits": doubled["denominator_bound"].bit_length(),
        "shipping_answer_chars": len(_compact_json(shipping["answer"])),
        "doubled_answer_chars": len(_compact_json(doubled["answer"])),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks, witness_checks, invariant_failures = 0, 0, []
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        reordered = _permute_columns(inst, list(reversed(range(inst["term_count"]))))
        changed = _change_mode_bases(inst, 100_000 + seed)
        scaled = _scale_nodes(inst, 3)
        swapped = _swap_equal_modes(inst)
        composed = _swap_equal_modes(_scale_nodes(_change_mode_bases(reordered, 200_000 + seed), 3))
        for label, transformed in (("reordered", reordered), ("basis", changed),
                                   ("scaled", scaled), ("equal_mode_swap", swapped),
                                   ("composed", composed)):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                invariant_failures.append([seed, label, "key changed"])
            witness_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                invariant_failures.append([seed, label, reason])
    unrelated = {canonical_key(make_instance(seed=1000 + seed,
                  **DIFFICULTY[SHIPPING_DIFFICULTY])) for seed in range(20)}
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(unrelated) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(unrelated), "unrelated_attempts": 20,
        "failures": invariant_failures,
    }

    size_measurements = []
    for seed in range(1000):
        measured = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        size_measurements.append((len(_compact_json(measured["answer"])), seed))
    chars, worst_size_seed = max(size_measurements)
    elements = _answer_atoms(shipping["answer"])
    intended = int(statistics.median(x["operations"] for x in compact))
    arms = copy.deepcopy(G9_EVIDENCE["arms"])
    difference = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        difference = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                      - arms["placebo"]["solved"] / arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and elements <= 256 and intended <= 300,
        "arms": arms, "hinted_minus_placebo": difference,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": (chars + 3) // 4,
        "answer_elements": elements, "intended_route_operations": intended,
        "answer_size_seeds_measured": len(size_measurements),
        "worst_answer_size_seed": worst_size_seed,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }
    report["all_passed"] = all(value.get("pass") is True for key, value in report.items()
                                  if key.startswith("G") and isinstance(value, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
