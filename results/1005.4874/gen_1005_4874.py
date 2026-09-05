"""Native (3,3)-CSP witnesses inspired by arXiv:1005.4874.

Scheder's Section 1 defines a (d,k)-CSP formula as a conjunction of
constraints, each a disjunction of literals (x_i != c). A listed forbidden
tuple is exactly one such constraint. This generator inverse-generates a
satisfying 3-color assignment, encodes sparse ternary-linear relations as
ordinary (3,3)-CSP constraints, and hides a quadratic-polarization shortcut in
the variable labels. Verification is only direct clause evaluation.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import random
import re
import time


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "(3,3)-CSP variables with colors 0, 1, 2",
        "disjunctions of literals (x_i != c)",
        "satisfying color assignment",
    ],
    "verification_operations": [
        "integer range checks",
        "exact tuple-code lookup equivalent to CSP literal evaluation",
        "conjunction of clause truth values",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize each forbidden-tuple block as a ternary-linear relation "
        "whose constants polarize one quadratic monomial on the displayed "
        "base-3 labels; without that invariant, solve the full clause system."
    ),
    "hardness_basis": (
        "Track B: native DPLL with unit propagation solves shipping in 5 nodes, "
        "19,776 checks, and 0.0031 seconds (worst-case O(3^n*B)), while guaranteed "
        "GF(3) Gaussian elimination is O(B*n^2) and uses 622,510 scalar "
        "operations; quadratic polarization needs at most 250 operations."
    ),
    "max_answer_tokens": 41,
}

NATIVE: dict = {
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

DIFFICULTY: dict = {
    "demo": {"n": 8, "blocks": 8},
    "easy": {"n": 50, "blocks": 160},
    "medium": {"n": 80, "blocks": 320},
    "hard": {"n": 80, "blocks": 640},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT: str = (
    "Each block is a ternary-linear relation whose constant is the polarization "
    "of one quadratic monomial on the displayed base-3 labels."
)
PLACEBO_HINT: str = (
    "Each block should be checked carefully because a single forbidden tuple "
    "is enough to invalidate an otherwise plausible assignment."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly n colors in variable order; every color is one "
        "of the integers 0, 1, 2."
    ),
    "bounds": {"length": "n (80 at shipping)", "alphabet": [0, 1, 2]},
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 1, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and native objects. Section 1 of Scheder's paper defines variables
colored from [d], literals (x_i != c), constraints as ORs of literals, and a CSP
formula as their conjunction. This module uses d=3 and constraints of arity at
most three verbatim. In the renderer, a forbidden tuple abc on scope [i,j,k]
is only shorthand for the paper's clause
  (x_i != a) OR (x_j != b) OR (x_k != c).
The witness is the paper's own satisfying assignment, and verify() checks every
such clause directly. No finite-field instance is substituted for the CSP.

Step-0 and track decision. The paper's main theorem gives a deterministic
exponential algorithm for general (d,k)-CSP; at d=k=3 its displayed bound is
about 2.077^n. That theorem is not an average-case lower bound for planted
formulas, so this module makes no Track-A claim. Its promised distribution has
an efficient specialized algorithm: recover the ternary-linear relation behind
each complete forbidden-tuple block and run exact Gaussian elimination. Native
DPLL with unit propagation is also measured and reported as the domain-standard
reference_algorithm, as Track B requires.

Generation route. Variables carry distinct nonzero vectors of a base-3 vector
space. The generator samples a quadratic monomial Q(v)=v_p*v_q, an affine
linear form, and a constant, then samples the satisfying colors first. Every
block is subsequently made from a two- or three-variable linear equation whose
right side is evaluated on that planted assignment. A triangular set of core
relations determines all non-basis variables from the basis variables, proving
that exactly 3^q assignments satisfy the formula. Extra relations are sampled
from the same vector-addition identity and are redundant. The certificate is
therefore known by inverse generation, never by solving the produced formula.

Compact route. For f(v)=v_p*v_q+L(v)+c over GF(3), the affine part cancels from
f(u)+f(v)-f(u+v). Binary basis-doubling relations reveal c, while the basis-pair
relations have one exceptional pair revealing p,q. Choosing L=0 then gives the
valid assignment f(v)=v_p*v_q+c. At n=80 this is at most 240 per-coordinate
multiply/add/reduce operations plus ten comparisons: 250 total. The full
reference route recognizes hundreds of clause blocks and eliminates a dense
matrix instead.

Easy regimes and attacks. A numeric/topological variable order made greedy
propagation recover the answer, so construction now randomly permutes variables
after all relations are built. Complete linear blocks are color-balanced, so
per-variable forbidden-tuple frequency carries no planted-color signal. The
panel also tests sequential greedy assignment, uniform random restarts, and all
affine functions of the displayed labels; the last is the natural in-context
ansatz and fails because the cross term is genuinely quadratic.

Canonicalization. Reordering blocks, renaming variables while carrying their
labels, and independently translating each variable's three colors are genuine
CSP isomorphisms. The cheap key uses the sorted base-3 label scope of every
block and the incidence counts attached to each label. It ignores right sides
because all generated consistent right sides on a fixed row system differ by a
color translation. Labels are public semantic data, so this is stronger than an
unlabelled hypergraph invariant while remaining invariant under variable names.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _dimension_for(n):
    q = 1
    power = 3
    while power <= n:
        q += 1
        power *= 3
    return q


def _trits(number, q):
    digits = []
    for _ in range(q):
        number, digit = divmod(number, 3)
        digits.append(digit)
    return digits


def _from_trits(digits):
    value = 0
    place = 1
    for digit in digits:
        value += digit * place
        place *= 3
    return value


def _add_labels(left, right):
    return [(a + b) % 3 for a, b in zip(left, right)]


def _dot(left, right):
    return sum(a * b for a, b in zip(left, right)) % 3


def _all_tuples(arity):
    return itertools.product(range(3), repeat=arity)


def _forbidden_for(coefficients, rhs):
    return [
        list(values)
        for values in _all_tuples(len(coefficients))
        if _dot(coefficients, values) != rhs
    ]


def _tuple_code(values):
    code = 0
    for value in values:
        code = 3 * code + value
    return code


def _forbidden_mask(forbidden):
    mask = 0
    for values in forbidden:
        mask |= 1 << _tuple_code(values)
    return mask


def _make_block(variables, coefficients, rhs, rng):
    order = list(range(len(variables)))
    rng.shuffle(order)
    variables = [variables[i] for i in order]
    coefficients = [coefficients[i] for i in order]
    if rng.randrange(2):
        coefficients = [(2 * value) % 3 for value in coefficients]
        rhs = (2 * rhs) % 3
    forbidden = _forbidden_for(coefficients, rhs)
    rng.shuffle(forbidden)
    return {
        "vars": variables,
        "forbidden": forbidden,
        "forbidden_mask": _forbidden_mask(forbidden),
    }


def _validate_parameters(n, blocks):
    if not _is_int(n) or not 5 <= n <= 256:
        raise ValueError("n must be an integer in 5..256")
    if not _is_int(blocks) or blocks < n - _dimension_for(n):
        raise ValueError("blocks must cover the triangular core")
    if blocks > 20_000:
        raise ValueError("blocks must be at most 20000")


def make_instance(n, seed=0, **params):
    """Inverse-generate a native (3,3)-CSP and a satisfying assignment."""
    blocks = params.pop("blocks", max(n, 2 * n))
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, blocks)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    q = _dimension_for(n)
    labels = [_trits(value, q) for value in range(1, n + 1)]

    p, r = rng.sample(range(q), 2)
    if p > r:
        p, r = r, p
    linear = [rng.randrange(3) for _ in range(q)]
    constant = rng.randrange(3)

    planted = [
        (label[p] * label[r] + _dot(linear, label) + constant) % 3
        for label in labels
    ]

    raw_relations = []
    relation_keys = set()

    def add_relation(indices, coefficients):
        key = tuple(sorted(zip(indices, coefficients)))
        if key in relation_keys:
            return False
        relation_keys.add(key)
        rhs = sum(c * planted[i] for i, c in zip(indices, coefficients)) % 3
        raw_relations.append((list(indices), list(coefficients), rhs))
        return True

    basis_values = {3**i for i in range(q) if 3**i <= n}
    for value in range(1, n + 1):
        if value in basis_values:
            continue
        label = labels[value - 1]
        nonzero = next(i for i, digit in enumerate(label) if digit)
        basis_value = 3**nonzero
        if value == 2 * basis_value:
            add_relation([basis_value - 1, value - 1], [2, 2])
            continue
        rest = list(label)
        rest[nonzero] = (rest[nonzero] - 1) % 3
        rest_value = _from_trits(rest)
        add_relation([basis_value - 1, rest_value - 1, value - 1], [1, 1, 2])

    attempts = 0
    attempt_cap = max(10_000, 100 * blocks)
    while len(raw_relations) < blocks and attempts < attempt_cap:
        attempts += 1
        left, right = rng.sample(range(1, n + 1), 2)
        summed = _from_trits(_add_labels(labels[left - 1], labels[right - 1]))
        if not 1 <= summed <= n or summed in (left, right):
            continue
        add_relation([left - 1, right - 1, summed - 1], [1, 1, 2])
    if len(raw_relations) < blocks:
        raise ValueError("requested too many distinct label-addition blocks")

    generated_blocks = [
        _make_block(variables, coefficients, rhs, rng)
        for variables, coefficients, rhs in raw_relations
    ]

    old_order = list(range(n))
    rng.shuffle(old_order)
    old_to_new = {old: new for new, old in enumerate(old_order)}
    labels = [labels[old] for old in old_order]
    answer = [planted[old] for old in old_order]
    for block in generated_blocks:
        block["vars"] = [old_to_new[index] for index in block["vars"]]
    rng.shuffle(generated_blocks)

    return {
        "family": "quadratic_polarization_3csp",
        "n": n,
        "colors": 3,
        "label_dimension": q,
        "labels": labels,
        "blocks": generated_blocks,
        "answer": answer,
    }


def _format_labels(inst):
    return " ".join(
        f"x{index}=" + "".join(map(str, reversed(label)))
        for index, label in enumerate(inst["labels"])
    )


def _format_block(index, block):
    forbidden = " ".join("".join(map(str, values)) for values in block["forbidden"])
    scope = ",".join(f"x{value}" for value in block["vars"])
    return f"B{index} [{scope}] forbid: {forbidden}"


def render(inst):
    n = inst["n"]
    lines = [
        "SATISFY A THREE-COLOR CSP",
        "",
        f"There are n={n} variables x0 through x{n-1}. Each color is 0, 1, or 2.",
        "A literal (x_i != c) is true exactly when x_i is not color c.",
        "A clause is an OR of its literals, and the formula is the AND of all clauses.",
        "",
        "Clauses are displayed in blocks. If a block has scope [x_i,x_j,x_k],",
        "a forbidden tuple abc denotes the clause",
        "(x_i != a) OR (x_j != b) OR (x_k != c).",
        "Thus every listed forbidden tuple is one ordinary CSP clause. Binary scopes",
        "and two-digit tuples have the analogous meaning. Tuple order follows scope order.",
        "All blocks and tuples are conjunctive; their displayed order has no meaning.",
        "",
        f"Each variable also has a distinct {inst['label_dimension']}-digit base-3 label:",
        _format_labels(inst),
        "",
        f"The {len(inst['blocks'])} constraint blocks are:",
    ]
    lines.extend(_format_block(i, block) for i, block in enumerate(inst["blocks"]))
    lines.extend(
        [
            "",
            f"Find any satisfying assignment as a JSON list of exactly {n} integers.",
            "Entry i is the color of x_i; indexing is 0-based, order is fixed, and",
            "only 0, 1, 2 are allowed. Repetitions are allowed.",
            "Give your final answer inside <answer></answer> tags.",
            f"Example of syntax only: <answer>{json.dumps([0] * n, separators=(',', ':'))}</answer>",
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
    match = _ANSWER_RE.search(text)
    if match:
        payload = match.group(1).strip()
    else:
        fenced = _FENCE_RE.search(text)
        payload = fenced.group(1).strip() if fenced else text.strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "assignment must be nonempty"
    if len(answer) < inst["n"]:
        return False, f"assignment is too short: got {len(answer)}, expected {inst['n']}"
    if len(answer) > inst["n"]:
        return False, f"assignment is too long: got {len(answer)}, expected {inst['n']}"
    for index, color in enumerate(answer):
        if not _is_int(color) or color not in (0, 1, 2):
            return False, f"color at position {index} is not one of 0, 1, 2"
    for block_index, block in enumerate(inst["blocks"]):
        values = (answer[index] for index in block["vars"])
        if block["forbidden_mask"] & (1 << _tuple_code(values)):
            return False, f"constraint block {block_index} forbids the chosen tuple"
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return [rng.randrange(3) for _ in range(inst["n"])]


def search_space(inst):
    return pow(3, inst["n"])


def enumerate_all(inst):
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    return sum(
        int(verify(inst, list(answer))[0])
        for answer in itertools.product(range(3), repeat=inst["n"])
    )


def canonical_key(inst):
    """Cheap isomorphism invariant under the declared CSP relabellings.

    Labels are public instance data and move with variables, so each block can
    be represented canonically by its unordered tuple of labels. Clause right
    sides are omitted intentionally: on this promised family any two consistent
    right-side vectors over the same row system differ by independent cyclic
    translations of the variables' colors.
    """
    n = inst["n"]
    incidence = {tuple(label): [0, 0] for label in inst["labels"]}
    scopes = []
    for block in inst["blocks"]:
        arity = len(block["vars"])
        scope = tuple(sorted(tuple(inst["labels"][v]) for v in block["vars"]))
        scopes.append(scope)
        for variable in block["vars"]:
            incidence[tuple(inst["labels"][variable])][arity - 2] += 1
    invariant = {
        "n": n,
        "labels": sorted(tuple(label) for label in inst["labels"]),
        "scopes": sorted(scopes),
        "incidence_by_label": sorted(
            (label, tuple(counts)) for label, counts in incidence.items()
        ),
    }
    return json.dumps(invariant, sort_keys=True, separators=(",", ":"))


def escalate(params):
    harder = dict(params)
    blocks = harder.get("blocks", 2 * harder.get("n", 80))
    if blocks >= 3_000:
        return None
    harder["blocks"] = min(3_000, 2 * blocks)
    return harder


def _decode_relation(block):
    arity = len(block["vars"])
    forbidden = {tuple(values) for values in block["forbidden"]}
    checks = 0
    for tail in itertools.product((1, 2), repeat=arity - 1):
        coefficients = (1,) + tail
        for rhs in range(3):
            expected = set()
            for values in _all_tuples(arity):
                checks += arity + 1
                if _dot(coefficients, values) != rhs:
                    expected.add(tuple(values))
            if expected == forbidden:
                return list(coefficients), rhs, checks
    raise ValueError("block is not a complete nonzero-coefficient GF(3) relation")


def _reference_gaussian(inst):
    started = time.perf_counter()
    n = inst["n"]
    matrix = []
    operations = 0
    for block in inst["blocks"]:
        coefficients, rhs, checks = _decode_relation(block)
        operations += checks
        row = [0] * (n + 1)
        for variable, coefficient in zip(block["vars"], coefficients):
            row[variable] = coefficient
        row[n] = rhs
        matrix.append(row)

    pivot_row = 0
    pivots = []
    for column in range(n):
        found = None
        for candidate in range(pivot_row, len(matrix)):
            operations += 1
            if matrix[candidate][column]:
                found = candidate
                break
        if found is None:
            continue
        matrix[pivot_row], matrix[found] = matrix[found], matrix[pivot_row]
        if matrix[pivot_row][column] == 2:
            for j in range(column, n + 1):
                matrix[pivot_row][j] = 2 * matrix[pivot_row][j] % 3
                operations += 2
        for row_index, row in enumerate(matrix):
            if row_index == pivot_row or row[column] == 0:
                continue
            factor = row[column]
            for j in range(column, n + 1):
                row[j] = (row[j] - factor * matrix[pivot_row][j]) % 3
                operations += 3
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break

    answer = [0] * n
    for row_index, column in enumerate(pivots):
        answer[column] = matrix[row_index][n]
    solved = verify(inst, answer)[0]
    return {
        "candidate": answer,
        "solved": solved,
        "rank": len(pivots),
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _reference_dpll(inst):
    """Finite-domain DPLL with unit/functional propagation on native blocks."""
    started = time.perf_counter()
    n = inst["n"]
    incidence = [[] for _ in range(n)]
    for block_index, block in enumerate(inst["blocks"]):
        for variable in block["vars"]:
            incidence[variable].append(block_index)
    operations = 0
    nodes = 0

    def propagate(assignment):
        nonlocal operations
        changed = True
        while changed:
            changed = False
            for block in inst["blocks"]:
                values = []
                missing = []
                for position, variable in enumerate(block["vars"]):
                    operations += 1
                    values.append(assignment[variable])
                    if assignment[variable] < 0:
                        missing.append(position)
                if not missing:
                    operations += 1
                    if block["forbidden_mask"] & (1 << _tuple_code(values)):
                        return False
                elif len(missing) == 1:
                    position = missing[0]
                    allowed = []
                    for color in range(3):
                        values[position] = color
                        operations += len(values) + 1
                        if not block["forbidden_mask"] & (1 << _tuple_code(values)):
                            allowed.append(color)
                    values[position] = -1
                    if not allowed:
                        return False
                    if len(allowed) == 1:
                        variable = block["vars"][position]
                        if assignment[variable] < 0:
                            assignment[variable] = allowed[0]
                            changed = True
                        elif assignment[variable] != allowed[0]:
                            return False
        return True

    def search(assignment):
        nonlocal nodes, operations
        nodes += 1
        if not propagate(assignment):
            return None
        if all(value >= 0 for value in assignment):
            return assignment if verify(inst, assignment)[0] else None
        best = None
        best_score = None
        for variable, value in enumerate(assignment):
            if value >= 0:
                continue
            constrained = 0
            for block_index in incidence[variable]:
                block = inst["blocks"][block_index]
                constrained += sum(
                    assignment[other] >= 0
                    for other in block["vars"]
                    if other != variable
                )
                operations += len(block["vars"])
            score = (constrained, len(incidence[variable]), -variable)
            if best_score is None or score > best_score:
                best_score = score
                best = variable
        for color in range(3):
            branch = list(assignment)
            branch[best] = color
            result = search(branch)
            if result is not None:
                return result
        return None

    candidate = search([-1] * n)
    solved = candidate is not None and verify(inst, candidate)[0]
    return {
        "candidate": candidate,
        "solved": solved,
        "nodes": nodes,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _attack_tuple_frequency(inst):
    scores = [[0, 0, 0] for _ in range(inst["n"])]
    for block in inst["blocks"]:
        for position, variable in enumerate(block["vars"]):
            for forbidden in block["forbidden"]:
                scores[variable][forbidden[position]] += 1
    return [
        min(range(3), key=lambda color: (scores[i][color], color))
        for i in range(inst["n"])
    ]


def _attack_sequential_greedy(inst):
    answer = [-1] * inst["n"]
    for variable in range(inst["n"]):
        best = None
        for color in range(3):
            answer[variable] = color
            violations = 0
            for block in inst["blocks"]:
                if variable not in block["vars"]:
                    continue
                if any(answer[index] < 0 for index in block["vars"]):
                    continue
                values = tuple(answer[index] for index in block["vars"])
                violations += int(any(values == tuple(f) for f in block["forbidden"]))
            score = (violations, color)
            if best is None or score < best[0]:
                best = (score, color)
        answer[variable] = best[1]
    return answer


def _attack_affine_labels(inst):
    q = inst["label_dimension"]
    attempts = 0
    for coefficients in itertools.product(range(3), repeat=q):
        for constant in range(3):
            attempts += 1
            answer = [
                (_dot(coefficients, label) + constant) % 3
                for label in inst["labels"]
            ]
            if verify(inst, answer)[0]:
                return answer, attempts
    return [0] * inst["n"], attempts


def _attack_label_digit_sum(inst):
    return [sum(label) % 3 for label in inst["labels"]]


def _translated_instance(inst, shifts):
    transformed = json.loads(json.dumps(inst))
    for block in transformed["blocks"]:
        for forbidden in block["forbidden"]:
            for position, variable in enumerate(block["vars"]):
                forbidden[position] = (forbidden[position] + shifts[variable]) % 3
        block["forbidden_mask"] = _forbidden_mask(block["forbidden"])
    transformed["answer"] = [
        (color + shift) % 3 for color, shift in zip(inst["answer"], shifts)
    ]
    return transformed


def _permuted_instance(inst, old_order):
    transformed = json.loads(json.dumps(inst))
    old_to_new = {old: new for new, old in enumerate(old_order)}
    transformed["labels"] = [inst["labels"][old] for old in old_order]
    transformed["answer"] = [inst["answer"][old] for old in old_order]
    for block in transformed["blocks"]:
        block["vars"] = [old_to_new[old] for old in block["vars"]]
    return transformed


def _atoms(value):
    if isinstance(value, dict):
        return sum(_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atoms(item) for item in value)
    return 1


def selftest():
    report = {}

    planted_attempts = 0
    roundtrip_attempts = 0
    json_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"{preset}/{seed} planted answer failed: {reason}")
            planted_attempts += 1
            blob = json.dumps(inst["answer"], separators=(",", ":"))
            if json.loads(blob) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_attempts += 1
            response = "The coloring is:\n```json\n<answer>" + blob + "</answer>\n```"
            if parse_answer(response) != inst["answer"]:
                raise AssertionError("parse round-trip failed")
            roundtrip_attempts += 1
    report["G1_planted_verifies"] = {"pass": True, "attempts": planted_attempts}

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = list(shipping["answer"])
    corruptions = {"drop_one": verify(shipping, base[:-1])}
    swap_candidate = None
    for left in range(shipping["n"]):
        for right in range(left + 1, shipping["n"]):
            if base[left] == base[right]:
                continue
            candidate = list(base)
            candidate[left], candidate[right] = candidate[right], candidate[left]
            if not verify(shipping, candidate)[0]:
                swap_candidate = candidate
                break
        if swap_candidate is not None:
            break
    if swap_candidate is None:
        raise AssertionError("could not construct a rejected swap corruption")
    corruptions["swap_one"] = verify(shipping, swap_candidate)
    corruptions["duplicate_one"] = verify(shipping, base + [base[0]])
    corruptions["empty"] = verify(shipping, [])
    out_of_range = list(base)
    out_of_range[0] = 3
    corruptions["out_of_range"] = verify(shipping, out_of_range)
    if any(result[0] for result in corruptions.values()):
        raise AssertionError("a corruption was accepted")
    reasons = [result[1] for result in corruptions.values()]
    if len(set(reasons)) != len(reasons):
        raise AssertionError("corruption reasons are not distinct")
    report["G2_rejects_corruption"] = {
        "pass": True,
        "cases": {name: reason for name, (_, reason) in corruptions.items()},
    }
    report["G3_round_trip"] = {
        "pass": True,
        "attempts": roundtrip_attempts,
        "json_native_attempts": json_attempts,
    }

    guess_rng = random.Random(0x10054874)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    probability = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": probability,
        "exact_valid_fraction": f"3^{shipping['label_dimension'] - shipping['n']}",
        "structure_aware_space": str(search_space(shipping)),
        "wall_clock_sec": guess_elapsed,
    }

    reference = _reference_dpll(shipping)
    gaussian = _reference_gaussian(shipping)
    attack_started = time.perf_counter()
    affine_candidate, affine_attempts = _attack_affine_labels(shipping)
    affine_elapsed = time.perf_counter() - attack_started
    affine_success = verify(shipping, affine_candidate)[0]
    report["G5_density_and_baseline"] = {
        "pass": reference["solved"] and gaussian["solved"] and not affine_success,
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_observed_valid_fraction": probability,
        "exact_valid_answer_count": pow(3, shipping["label_dimension"]),
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operations": reference["operations"],
        "reference_nodes": reference["nodes"],
        "gaussian_wall_clock_sec": gaussian["wall_clock_sec"],
        "gaussian_operations": gaussian["operations"],
        "gaussian_rank": gaussian["rank"],
        "strongest_failing_attack": "all_affine_label_functions",
        "strongest_failing_attack_attempts": affine_attempts,
        "strongest_failing_attack_successes": int(affine_success),
        "strongest_failing_attack_wall_clock_sec": affine_elapsed,
    }

    attacks = {
        "outlier_forbidden_tuple_frequency": {"successes": 0, "attempts": 0},
        "greedy_sequential_min_violations": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_label_digit_sum_ansatz": {"successes": 0, "attempts": 0},
        "in_context_all_affine_label_functions": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_operations = 0
    reference_nodes = 0
    reference_wall = 0.0
    gaussian_successes = 0
    gaussian_operations = 0
    gaussian_wall = 0.0
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=7000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_forbidden_tuple_frequency": _attack_tuple_frequency(inst),
            "greedy_sequential_min_violations": _attack_sequential_greedy(inst),
            "in_context_label_digit_sum_ansatz": _attack_label_digit_sum(inst),
        }
        restart_rng = random.Random(9000 + seed)
        found = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                found = True
                break
        attacks["random_restart_256"]["successes"] += int(found)
        attacks["random_restart_256"]["attempts"] += 1
        affine, _ = _attack_affine_labels(inst)
        candidates["in_context_all_affine_label_functions"] = affine
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
            attacks[name]["attempts"] += 1
        measured = _reference_dpll(inst)
        reference_successes += int(measured["solved"])
        reference_operations += measured["operations"]
        reference_nodes += measured["nodes"]
        reference_wall += measured["wall_clock_sec"]
        eliminated = _reference_gaussian(inst)
        gaussian_successes += int(eliminated["solved"])
        gaussian_operations += eliminated["operations"]
        gaussian_wall += eliminated["wall_clock_sec"]
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "native finite-domain DPLL with unit/functional propagation",
            "complexity": "worst-case O(3^n*B); measured promised instances use 5 nodes",
            "wall_clock_sec": reference_wall,
            "operations": reference_operations,
            "nodes": reference_nodes,
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
        "efficient_structure_algorithm": {
            "name": "relation recognition plus dense Gaussian elimination over GF(3)",
            "complexity": "O(B*n^2) exact scalar field operations",
            "wall_clock_sec": gaussian_wall,
            "operations": gaussian_operations,
            "solves": f"{gaussian_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    doubled = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled["n"] = min(256, 2 * doubled["n"])
    doubled_inst = make_instance(seed=314159, **doubled)
    escalated_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    escalated_inst = make_instance(seed=271828, **escalated_params)
    doubled_ok = verify(doubled_inst, doubled_inst["answer"])[0]
    escalated_ok = verify(escalated_inst, escalated_inst["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "base_n": shipping["n"],
        "doubled_n": doubled_inst["n"],
        "base_blocks": len(shipping["blocks"]),
        "escalated_blocks": len(escalated_inst["blocks"]),
        "answer_length_fixed_on_escalation": escalated_inst["n"] == shipping["n"],
    }

    invariance_checks = 0
    carried_checks = 0
    distinct_keys = set()
    for seed in range(20):
        inst = make_instance(seed=10000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        distinct_keys.add(key)
        rng = random.Random(20000 + seed)
        reordered = json.loads(json.dumps(inst))
        rng.shuffle(reordered["blocks"])
        for block in reordered["blocks"]:
            rng.shuffle(block["forbidden"])
        if canonical_key(reordered) != key:
            raise AssertionError("canonical key changed under constraint reordering")
        invariance_checks += 1
        carried_checks += int(verify(reordered, inst["answer"])[0])

        order = list(range(inst["n"]))
        rng.shuffle(order)
        permuted = _permuted_instance(inst, order)
        if canonical_key(permuted) != key:
            raise AssertionError("canonical key changed under variable renaming")
        invariance_checks += 1
        carried_checks += int(verify(permuted, permuted["answer"])[0])

        shifts = [rng.randrange(3) for _ in range(inst["n"])]
        translated = _translated_instance(inst, shifts)
        if canonical_key(translated) != key:
            raise AssertionError("canonical key changed under color translations")
        invariance_checks += 1
        carried_checks += int(verify(translated, translated["answer"])[0])

        composed = _permuted_instance(translated, order)
        if canonical_key(composed) != key:
            raise AssertionError("canonical key changed under composed relabelling")
        invariance_checks += 1
        carried_checks += int(verify(composed, composed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 80 and carried_checks == 80 and len(distinct_keys) == 20,
        "invariance_checks": invariance_checks,
        "certificate_carried_checks": carried_checks,
        "distinct_keys": len(distinct_keys),
        "unrelated_instances": 20,
        "transformations": [
            "constraint and tuple reordering",
            "variable renaming with labels carried",
            "independent cyclic color translations",
            "composition of variable and color relabellings",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atoms(shipping["answer"])
    q = shipping["label_dimension"]
    intended_operations = 3 * shipping["n"] + q + q * (q - 1) // 2
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
