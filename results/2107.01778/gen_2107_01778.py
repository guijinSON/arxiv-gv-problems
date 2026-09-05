"""Verified generator for a linear tropical valued CSP from arXiv:2107.01778.

The generated objective is a maximum of absolute rational affine residuals.
An exact zero is planted before the residual equations are made, so generation
never solves its own instance.  The zero is unique because a hidden collection
of row pairs has one-coordinate differences covering every variable.
"""

import bisect
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from functools import lru_cache
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import rationals
except ImportError:  # pragma: no cover - the fallback is exercised only off-repo
    rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "continuous_analytic",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "linear tropical valued CSP over the reals",
        "rational affine forms",
        "rational assignment function",
    ],
    "verification_operations": [
        "exact rational affine evaluation",
        "exact equality comparison",
        "finite maximum lower bound at zero",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A regularly spaced pairing of dense coefficient rows differs in one "
        "coordinate, so subtracting the paired zero-residual equations isolates "
        "each coordinate while a generic method eliminates the whole dense system."
    ),
    "hardness_basis": (
        "Track B: Section 5.2 reduces linear TVCSP minimization to linear "
        "programming (polynomial time); the latest shared-runner measurement of "
        "the O(m*n^2) fraction-free elimination reference took 4.49 wall-clock "
        "seconds and 1,406,272 exact operations, whereas the row-pair invariant "
        "needs 192 exact operations after it is recognized."
    ),
    "max_answer_tokens": 152,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {
        "n": 3,
        "pair_decoys": 1,
        "height": 4,
        "max_denominator": 2,
        "coefficient_bound": 3,
    },
    "easy": {
        "n": 12,
        "pair_decoys": 6,
        "height": 12,
        "max_denominator": 5,
        "coefficient_bound": 7,
    },
    "medium": {
        "n": 32,
        "pair_decoys": 16,
        "height": 30,
        "max_denominator": 7,
        "coefficient_bound": 11,
    },
    "hard": {
        "n": 64,
        "pair_decoys": 32,
        "height": 70,
        "max_denominator": 9,
        "coefficient_bound": 15,
    },
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-n vector of pairwise-distinct reduced rationals p/q, with "
        "0 < |p| <= height and 1 <= q <= max_denominator."
    ),
    "bounds": {
        "length": "n",
        "absolute_numerator": "height",
        "max_denominator": "max_denominator",
        "pairwise_distinct": True,
    },
}

STRUCTURAL_HINT = (
    "A regularly spaced pairing of coefficient rows differs in only one coordinate."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the rational signs and indices is useful in this problem."
)

# Filled from the script-owned oracle runs after hardening.  G9(a,b) are
# diagnostics; only the size/effort caps contribute to the gate's pass flag.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 2, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
}

NOTES = """\
Section 1.1 fixes ordinary CSP solutions as functions V -> D satisfying every
relation, while Section 5 defines the paper's native tropical valued CSP and
Equation (8) makes its objective a minimax value.  Proposition 5.2 and Theorem
5.4 classify finite-domain TVCSP through ordinary CSP sublevel sets, but Section
5.2 is decisive for Step 0 here: linear real-valued relations make the objective
a supremum of rational affine functions and reduce minimization to linear
programming, so this cannot honestly be Track A.  The generator therefore
declares Track B and constructs
paired affine forms +/- (a.s-b).  It samples s first and sets b=a.s, proving
objective zero without solving.  Single-coordinate differences across the true
row pairs prove uniqueness.  Pair decoys change two coordinates under the same
base-row and coefficient-replacement rules.  Column-statistic, diagonal-dominance,
random-restart coordinate-repair, and adjacent-row hand attacks are all tested;
exact fraction-free elimination is reported separately as the successful
polynomial reference algorithm required for Track B.  Independent sampling of
the answer and columns removes value/L1 correlation; dense rows defeat the
diagonal ratio; exact uniqueness in an enormous bounded alphabet defeats local
repair; and placing true mates half a block apart defeats the adjacent-row scan.
"""


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _q(value):
    """Coerce an exact rational without ever accepting a float."""
    if rationals is not None:
        return rationals.Q(value)
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("bool is not a rational")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        num, den = value
        if (not isinstance(num, int) or isinstance(num, bool)
                or not isinstance(den, int) or isinstance(den, bool) or den == 0):
            raise ValueError("malformed rational pair")
        return Fraction(num, den)
    if isinstance(value, str):
        m = re.fullmatch(r"\s*([+-]?\d+)(?:\s*/\s*([+-]?\d+))?\s*", value)
        if not m:
            raise ValueError("malformed rational literal")
        den = int(m.group(2) or "1")
        if den == 0:
            raise ValueError("zero denominator")
        return Fraction(int(m.group(1)), den)
    raise TypeError("unsupported rational type")


def _q_json(value):
    value = _q(value)
    return [value.numerator, value.denominator]


def _q_text(value):
    value = _q(value)
    if value.denominator == 1:
        return str(value.numerator)
    return "%d/%d" % (value.numerator, value.denominator)


@lru_cache(maxsize=64)
def _allowed_values(height, max_denominator):
    values = []
    for den in range(1, max_denominator + 1):
        for num in range(-height, height + 1):
            if num and math.gcd(abs(num), den) == 1:
                values.append(Fraction(num, den))
    values.sort()
    return tuple(values)


def _dot(row, vector):
    return sum((Fraction(a) * x for a, x in zip(row, vector)), Fraction(0))


def _random_row(rng, n, bound):
    while True:
        row = [rng.randint(-bound, bound) for _ in range(n)]
        if any(row):
            return row


def _changed_value(rng, old, bound):
    choices = [v for v in range(-bound, bound + 1) if abs(v - old) >= 2]
    return rng.choice(choices)


def make_instance(n, seed=0, pair_decoys=0, height=30,
                  max_denominator=7, coefficient_bound=11, **params):
    """Inverse-generate an exact linear TVCSP instance and its zero witness."""
    del params
    for name, value, minimum in (
        ("n", n, 2),
        ("pair_decoys", pair_decoys, 0),
        ("height", height, 1),
        ("max_denominator", max_denominator, 1),
        ("coefficient_bound", coefficient_bound, 2),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError("%s must be an integer >= %d" % (name, minimum))

    rng = random.Random(seed)
    language = _allowed_values(height, max_denominator)
    if len(language) < n:
        raise ValueError("certificate language has fewer than n distinct rationals")

    planted = rng.sample(language, n)
    pair_specs = [(j,) for j in rng.sample(range(n), n)]
    for _ in range(pair_decoys):
        pair_specs.append(tuple(sorted(rng.sample(range(n), 2))))
    rng.shuffle(pair_specs)

    bases = []
    modified = []
    for changed in pair_specs:
        # Reject the measure-zero-looking b=0 cases so equation orientation has
        # a column-permutation-invariant canonical sign chosen from b alone.
        while True:
            row = _random_row(rng, n, coefficient_bound)
            row2 = row[:]
            for j in changed:
                row2[j] = _changed_value(rng, row[j], coefficient_bound)
            b1 = _dot(row, planted)
            b2 = _dot(row2, planted)
            if b1 != 0 and b2 != 0:
                break
        bases.append({"a": row, "b": _q_json(b1)})
        modified.append({"a": row2, "b": _q_json(b2)})

    # Positionwise comparison of the two equal-length blocks is the intended
    # compact route.  The pair types are deliberately not stored in the instance.
    equations = bases + modified
    return {
        "family": "linear_tropical_minimax_zero",
        "n": n,
        "pair_decoys": pair_decoys,
        "height": height,
        "max_denominator": max_denominator,
        "coefficient_bound": coefficient_bound,
        "equations": equations,
        "answer": [_q_json(x) for x in planted],
    }


def render(inst):
    n = inst["n"]
    equations = inst["equations"]
    lines = [
        "Linear tropical valued CSP over the real numbers",
        "",
        "There are %d real variables s_0,...,s_%d." % (n, n - 1),
        "For every displayed equation e, let",
        "  r_e(s) = a_e,0*s_0 + ... + a_e,%d*s_%d - b_e." % (n - 1, n - 1),
        "The tropical minimax objective is",
        "  F(s) = max_e max(r_e(s), -r_e(s)) = max_e |r_e(s)|.",
        "This is the maximum of finitely many rational affine forms, so F(s) >= 0.",
        "The instance promises one unique vector in the bounded language below with F(s)=0.",
        "Find that vector.  Reaching zero also certifies global optimality because F is nonnegative.",
        "",
        "Each equation line has the exact format",
        "  index : b | a_0 a_1 ... a_%d" % (n - 1),
        "and means sum_j a_j*s_j = b.  Indices and variables are 0-based.",
        "All coefficients are integers and every b is an exact reduced rational.",
        "Equation order does not change F.",
        "",
        "n = %d; equations = %d" % (n, len(equations)),
        "certificate bounds: 0 < |numerator| <= %d, denominator <= %d, entries pairwise distinct"
        % (inst["height"], inst["max_denominator"]),
        "",
        "EQUATIONS",
    ]
    for i, eq in enumerate(equations):
        lines.append("%d : %s | %s" % (
            i,
            _q_text(eq["b"]),
            " ".join(str(x) for x in eq["a"]),
        ))
    lines.append("END EQUATIONS")
    lines.append("")
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.append("Hint: " + STRUCTURAL_HINT)
        lines.append("")
    elif mode == "placebo":
        lines.append("Hint: " + PLACEBO_HINT)
        lines.append("")
    lines.extend([
        "Give your final answer inside <answer></answer> tags as exactly %d comma-separated"
        % n,
        "reduced rationals in variable order s_0,...,s_%d.  Write an integer q as q and"
        % (n - 1),
        "a nonintegral rational as num/den with a positive denominator.",
        "Syntax example: <answer>1/2, -3, 4/5</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    """Parse a tagged comma-separated exact rational vector, never raising."""
    if not isinstance(text, str):
        return None
    match = _TAG_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    if not body:
        return []
    parts = [part.strip() for part in body.split(",")]
    if any(not part for part in parts):
        return None
    out = []
    try:
        for part in parts:
            if rationals is not None:
                value = rationals.parse_rational(part)
                if value is None:
                    return None
            else:
                value = _q(part)
            out.append(_q_json(value))
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return out


def _decode_answer(answer):
    if not isinstance(answer, list):
        raise TypeError("answer must be a list")
    return [_q(item) for item in answer]


def verify(inst, answer):
    """Check a candidate by exact substitution; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a list of rational pairs"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != inst["n"]:
        return False, "wrong vector length: expected %d, got %d" % (inst["n"], len(answer))
    try:
        values = _decode_answer(answer)
    except (TypeError, ValueError, ZeroDivisionError):
        return False, "malformed rational: use reduced [numerator, denominator] pairs"
    for i, (raw, value) in enumerate(zip(answer, values)):
        if (not isinstance(raw, list) or len(raw) != 2
                or raw[0] != value.numerator or raw[1] != value.denominator
                or value.denominator <= 0):
            return False, "entry %d is not a reduced rational pair with positive denominator" % i
        if value == 0 or abs(value.numerator) > inst["height"] \
                or value.denominator > inst["max_denominator"]:
            return False, "entry %d violates the declared numerator/denominator bounds" % i
    if len(set(values)) != len(values):
        return False, "entries must be pairwise distinct"
    for i, eq in enumerate(inst["equations"]):
        residual = _dot(eq["a"], values) - _q(eq["b"])
        if residual != 0:
            return False, "affine form %d has nonzero exact residual %s" % (i, _q_text(residual))
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the promised bounded, pairwise-distinct vector language."""
    values = _allowed_values(inst["height"], inst["max_denominator"])
    return [_q_json(x) for x in rng.sample(values, inst["n"])]


def search_space(inst):
    size = len(_allowed_values(inst["height"], inst["max_denominator"]))
    n = inst["n"]
    if n > size:
        return 0
    result = 1
    for k in range(n):
        result *= size - k
    return result


def enumerate_all(inst):
    """Brute-force the exact count only when the bounded language is small."""
    space = search_space(inst)
    if space > 200_000:
        return None
    count = 0
    values = _allowed_values(inst["height"], inst["max_denominator"])
    for candidate in itertools.permutations(values, inst["n"]):
        ok, _ = verify(inst, [_q_json(x) for x in candidate])
        count += int(ok)
    return count


def _normalised_equations(inst):
    rows = []
    for eq in inst["equations"]:
        b = _q(eq["b"])
        sign = 1 if b > 0 else -1
        rows.append((tuple(sign * int(a) for a in eq["a"]), sign * b))
    return rows


def _compress(features):
    unique = sorted(set(features))
    rank = {feature: i for i, feature in enumerate(unique)}
    return [rank[feature] for feature in features]


def canonical_key(inst):
    """A permutation-invariant weighted bipartite refinement fingerprint."""
    rows = _normalised_equations(inst)
    m = len(rows)
    n = inst["n"]
    row_colours = _compress([
        (b, tuple(sorted(a))) for a, b in rows
    ])
    col_colours = _compress([
        tuple(sorted(rows[i][0][j] for i in range(m))) for j in range(n)
    ])
    for _ in range(8):
        row_features = []
        for i, (a, b) in enumerate(rows):
            row_features.append((b, tuple(sorted((col_colours[j], a[j]) for j in range(n)))))
        new_rows = _compress(row_features)
        col_features = []
        for j in range(n):
            col_features.append(tuple(sorted((new_rows[i], rows[i][0][j]) for i in range(m))))
        new_cols = _compress(col_features)
        if new_rows == row_colours and new_cols == col_colours:
            row_colours, col_colours = new_rows, new_cols
            break
        row_colours, col_colours = new_rows, new_cols
    payload = {
        "n": n,
        "rows": sorted(
            (row_colours[i], _q_text(b), tuple(sorted(
                (col_colours[j], a[j]) for j in range(n))))
            for i, (a, b) in enumerate(rows)
        ),
        "cols": sorted(
            (col_colours[j], tuple(sorted(
                (row_colours[i], rows[i][0][j]) for i in range(m))))
            for j in range(n)
        ),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    """Grow entropy and near-miss pairs before lengthening the witness."""
    p = dict(params)
    p.pop("_preset", None)
    n = p["n"]
    decoys = p.get("pair_decoys", n // 2)
    if n < 96:
        p["n"] = min(96, n + 16)
        p["pair_decoys"] = decoys + 12
        p["height"] = min(999, p["height"] * 2)
        p["coefficient_bound"] = p["coefficient_bound"] + 4
        return p
    # Once the 96-coordinate/288-arithmetic compact route reaches the G9(c)
    # ceiling, keep the answer fixed and grow only the haystack.  There is no
    # mathematical exhaustion point here: additional two-coordinate near-miss
    # pairs and larger dense coefficients preserve the same certificate and
    # exact verifier.  The external harness, rather than a false `None`, owns
    # the escalation budget.
    p["pair_decoys"] = decoys + max(n // 2, decoys // 2, 1)
    p["height"] = min(999, p["height"] + 100)
    p["coefficient_bound"] = p["coefficient_bound"] + 8
    return p


def _difference_solution(inst):
    """The intended compact solver; it does not read the planted answer."""
    equations = inst["equations"]
    pairs = len(equations) // 2
    found = {}
    arithmetic = 0
    for i in range(pairs):
        left = equations[i]
        right = equations[i + pairs]
        changed = [j for j, (a, b) in enumerate(zip(left["a"], right["a"])) if a != b]
        if len(changed) != 1:
            continue
        j = changed[0]
        delta_b = _q(right["b"]) - _q(left["b"])
        delta_a = right["a"][j] - left["a"][j]
        value = delta_b / delta_a
        arithmetic += 3
        if j in found and found[j] != value:
            return None, arithmetic
        found[j] = value
    if set(found) != set(range(inst["n"])):
        return None, arithmetic
    return [_q_json(found[j]) for j in range(inst["n"])], arithmetic


def _integer_augmented(inst):
    matrix = []
    for eq in inst["equations"]:
        b = _q(eq["b"])
        matrix.append([int(a) * b.denominator for a in eq["a"]]
                      + [b.numerator])
    return matrix


def _reference_bareiss(inst):
    """Generic fraction-free elimination on all equations, with operation count."""
    matrix = _integer_augmented(inst)
    m = len(matrix)
    n = inst["n"]
    pivot_row = 0
    previous = 1
    operations = 0
    for col in range(n):
        pivot = next((i for i in range(pivot_row, m) if matrix[i][col] != 0), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        pv = matrix[pivot_row][col]
        for i in range(pivot_row + 1, m):
            left = matrix[i][col]
            for j in range(col + 1, n + 1):
                numerator = matrix[i][j] * pv - left * matrix[pivot_row][j]
                operations += 3
                if previous != 1:
                    numerator //= previous
                    operations += 1
                matrix[i][j] = numerator
            matrix[i][col] = 0
        previous = pv
        pivot_row += 1
        if pivot_row == n:
            break
    if pivot_row != n:
        return None, operations
    solution = [Fraction(0) for _ in range(n)]
    for i in range(n - 1, -1, -1):
        rhs = Fraction(matrix[i][n])
        for j in range(i + 1, n):
            rhs -= matrix[i][j] * solution[j]
            operations += 2
        solution[i] = rhs / matrix[i][i]
        operations += 1
    answer = [_q_json(x) for x in solution]
    ok, _ = verify(inst, answer)
    return (answer if ok else None), operations


def _nearest_distinct(values, raw_values, n):
    remaining = set(values)
    out = []
    for raw in raw_values[:n]:
        chosen = min(remaining, key=lambda x: (abs(x - raw), x))
        remaining.remove(chosen)
        out.append(chosen)
    while len(out) < n:
        chosen = min(remaining)
        remaining.remove(chosen)
        out.append(chosen)
    return [_q_json(x) for x in out]


def _closest_unused(values, unused, target):
    """Closest member of a sorted rational alphabet that remains unused."""
    pivot = bisect.bisect_left(values, target)
    left = pivot - 1
    right = pivot
    while left >= 0 and values[left] not in unused:
        left -= 1
    while right < len(values) and values[right] not in unused:
        right += 1
    if left < 0:
        return values[right]
    if right == len(values):
        return values[left]
    a = values[left]
    b = values[right]
    return a if (abs(a - target), a) <= (abs(b - target), b) else b


def _attack_outlier_columns(inst):
    allowed = _allowed_values(inst["height"], inst["max_denominator"])
    rows = inst["equations"]
    scores = [sum(abs(eq["a"][j]) for eq in rows) for j in range(inst["n"])]
    ordered_values = sorted(allowed, key=lambda x: (abs(x), x))[:inst["n"]]
    answer = [None] * inst["n"]
    for j, value in zip(sorted(range(inst["n"]), key=lambda j: scores[j]), ordered_values):
        answer[j] = _q_json(value)
    return answer


def _attack_diagonal_greedy(inst):
    allowed = _allowed_values(inst["height"], inst["max_denominator"])
    raw = []
    for j in range(inst["n"]):
        # Choose the row in which coordinate j is most dominant, then pretend
        # all other coordinates vanish.  This is a plausible one-pass dense-
        # system heuristic, but it does not exploit the hidden row pairing.
        eq = max(
            inst["equations"],
            key=lambda row: (
                Fraction(abs(row["a"][j]),
                         1 + sum(abs(a) for k, a in enumerate(row["a"]) if k != j)),
                abs(row["a"][j]),
            ),
        )
        a = eq["a"][j]
        raw.append(_q(eq["b"]) / a if a else Fraction(0))
    return _nearest_distinct(allowed, raw, inst["n"])


def _attack_adjacent_pair_differences(inst):
    """A hand-scale local-pair scan that does not know the hidden spacing."""
    equations = inst["equations"]
    raw = [Fraction(0) for _ in range(inst["n"])]
    for i in range(0, len(equations) - 1, 2):
        changed = [j for j, (a, b) in enumerate(zip(
            equations[i]["a"], equations[i + 1]["a"])) if a != b]
        if len(changed) == 1:
            j = changed[0]
            delta_a = equations[i + 1]["a"][j] - equations[i]["a"][j]
            raw[j] = (_q(equations[i + 1]["b"]) - _q(equations[i]["b"])) / delta_a
    allowed = _allowed_values(inst["height"], inst["max_denominator"])
    return _nearest_distinct(allowed, raw, inst["n"])


def _attack_random_repair(inst, rng, restarts=256):
    """Random starts followed by one greedy coordinate-repair sweep."""
    allowed = _allowed_values(inst["height"], inst["max_denominator"])
    allowed_set = set(allowed)
    n = inst["n"]
    usable_rows = [
        [eq for eq in inst["equations"] if eq["a"][j] != 0]
        for j in range(n)
    ]
    updates = 0
    for _ in range(restarts):
        current = list(rng.sample(allowed, n))
        used = set(current)
        order = list(range(n))
        rng.shuffle(order)
        for j in order:
            eq = rng.choice(usable_rows[j])
            rhs = _q(eq["b"])
            for k, coefficient in enumerate(eq["a"]):
                if k != j:
                    rhs -= coefficient * current[k]
            target = rhs / eq["a"][j]
            used.remove(current[j])
            unused = allowed_set - used
            current[j] = target if target in unused else _closest_unused(
                allowed, unused, target
            )
            used.add(current[j])
            updates += 1
        candidate = [_q_json(x) for x in current]
        if verify(inst, candidate)[0]:
            return candidate, updates
    return None, updates


def _relabeled_instance(inst, variable_order, equation_order, sign_flips):
    out = {k: v for k, v in inst.items() if k not in ("equations", "answer")}
    equations = []
    for out_i, old_i in enumerate(equation_order):
        old = inst["equations"][old_i]
        sign = -1 if sign_flips[out_i] else 1
        equations.append({
            "a": [sign * old["a"][j] for j in variable_order],
            "b": _q_json(sign * _q(old["b"])),
        })
    out["equations"] = equations
    out["answer"] = [inst["answer"][j][:] for j in variable_order]
    return out


def _answer_size(answer):
    # Match emit.sh and harden.py, both of which use json.dumps defaults.
    blob = json.dumps(answer)

    def atoms(value):
        if isinstance(value, dict):
            return sum(atoms(x) for x in value.values())
        if isinstance(value, list):
            return sum(atoms(x) for x in value)
        return 1

    return len(blob), atoms(answer), (len(blob) + 3) // 4


def selftest():
    report = {}

    # G1: every rung, four seeds, and no certificate generated by a solve.
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "tested": len(DIFFICULTY) * 4,
        "failures": g1_failures,
    }

    # G2: five distinct corruptions must reach five distinct rejection paths.
    inst = make_instance(seed=8181, **DIFFICULTY["medium"])
    good = json.loads(json.dumps(inst["answer"]))
    corruptions = {
        "drop_one": good[:-1],
        "swap_two": [good[1], good[0]] + good[2:],
        "duplicate": [good[0], good[0]] + good[2:],
        "empty": [],
        "out_of_range": [[inst["height"] + 1, 1]] + good[1:],
    }
    reasons = {}
    g2_ok = True
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        g2_ok = g2_ok and not ok
        reasons[name] = why
    g2_ok = g2_ok and len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "cases": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    # G3: realistic prose and a markdown fence around the required tags.
    body = ", ".join(_q_text(x) for x in good)
    response = "I used exact row differences.\n```text\n<answer>%s</answer>\n```\n" % body
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == good and json.loads(json.dumps(parsed)) == parsed,
        "parsed_entries": len(parsed) if isinstance(parsed, list) else None,
    }

    ship = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    recovered, compact_ops = _difference_solution(ship)
    recovered_ok, recovered_why = verify(ship, recovered) if recovered is not None else (False, "missing")

    # G4/G5 density: draw 200k full-language candidates.  Uniqueness follows
    # from the executable difference recovery, so exact equality is equivalent
    # to calling the O(mn) verifier on every draw.
    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(910701778)
    for _ in range(sample_total):
        candidate = random_candidate(ship, sample_rng)
        if candidate == recovered:
            sample_hits += 1
    probability = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": recovered_ok and probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": probability,
        "certificate_space": search_space(ship),
        "sampler": "uniform ordered sample without replacement from the promised rational alphabet",
    }

    # Reference algorithm: successful by design on Track B and kept outside attacks.
    reference_trials = []
    for seed in range(8):
        trial = make_instance(seed=30_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        started = time.perf_counter()
        solved, operations = _reference_bareiss(trial)
        elapsed = time.perf_counter() - started
        ok = solved is not None and verify(trial, solved)[0]
        reference_trials.append((ok, operations, elapsed))

    attack_names = (
        "outlier_column_l1",
        "greedy_diagonal_ratio",
        "random_restart_256_coordinate_repair",
        "by_hand_adjacent_row_differences",
    )
    successes = {name: 0 for name in attack_names}
    attack_started = time.perf_counter()
    random_iterations = 0
    random_local_updates = 0
    random_trial_seconds = []
    random_trial_updates = []
    for seed in range(8):
        trial = make_instance(seed=40_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_column_l1": _attack_outlier_columns(trial),
            "greedy_diagonal_ratio": _attack_diagonal_greedy(trial),
            "by_hand_adjacent_row_differences": _attack_adjacent_pair_differences(trial),
        }
        for name, candidate in candidates.items():
            successes[name] += int(verify(trial, candidate)[0])
        restart_rng = random.Random(50_000 + seed)
        random_started = time.perf_counter()
        repaired, updates = _attack_random_repair(trial, restart_rng, restarts=256)
        random_trial_seconds.append(time.perf_counter() - random_started)
        random_trial_updates.append(updates)
        random_iterations += 256
        random_local_updates += updates
        successes["random_restart_256_coordinate_repair"] += int(
            repaired is not None and verify(trial, repaired)[0]
        )
    attack_elapsed = time.perf_counter() - attack_started

    ref_successes = sum(ok for ok, _, _ in reference_trials)
    ref_operations = max(ops for _, ops, _ in reference_trials)
    ref_wall = max(sec for _, _, sec in reference_trials)
    report["G5_density_baseline_cost"] = {
        "pass": sample_total >= 200_000 and recovered_ok and ref_successes == 8,
        "shipping_solution_count": 1,
        "shipping_density_numerator": 1,
        "shipping_density_denominator": search_space(ship),
        "shipping_sample_hits": sample_hits,
        "shipping_sample_total": sample_total,
        "strongest_attack_name": "random_restart_256_coordinate_repair",
        "strongest_attack_wall_clock_sec": round(max(random_trial_seconds), 6),
        "strongest_attack_iterations": 256,
        "strongest_attack_local_updates": max(random_trial_updates),
        "adversary_panel_wall_clock_sec": round(attack_elapsed, 6),
        "adversary_panel_total_restarts": random_iterations,
        "adversary_panel_total_local_updates": random_local_updates,
        "reference_wall_clock_sec": round(ref_wall, 6),
        "reference_exact_operations": ref_operations,
        "compact_route_operations": compact_ops,
        "compact_route_verification": recovered_why,
    }
    panel = {
        name: {"successes": successes[name], "attempts": 8}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in panel.values()),
        "attacks": panel,
        "reference_algorithm": {
            "name": "fraction-free Bareiss elimination over Q",
            "complexity": "O(m*n^2) exact arithmetic for m equations and n variables",
            "wall_clock_sec": round(ref_wall, 6),
            "operations": ref_operations,
            "solves": "%d/8, as expected" % ref_successes,
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["pair_decoys"] *= 2
    doubled_params["height"] *= 2
    doubled = make_instance(seed=707, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["equations"]) > len(ship["equations"]),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_equations": len(ship["equations"]),
        "doubled_equations": len(doubled["equations"]),
        "doubled_reason": doubled_why,
    }

    invariant_checks = 0
    transform_validity = 0
    keys = []
    for seed in range(20):
        small_params = dict(DIFFICULTY["easy"])
        original = make_instance(seed=60_000 + seed, **small_params)
        key = canonical_key(original)
        keys.append(key)
        rng = random.Random(70_000 + seed)
        variable_order = list(range(original["n"]))
        equation_order = list(range(len(original["equations"])))
        rng.shuffle(variable_order)
        rng.shuffle(equation_order)
        sign_flips = [bool(rng.getrandbits(1)) for _ in equation_order]
        transformed = _relabeled_instance(
            original, variable_order, equation_order, sign_flips
        )
        carried_ok, _ = verify(transformed, transformed["answer"])
        transform_validity += int(carried_ok)
        for variant in (
            _relabeled_instance(original, variable_order,
                                list(range(len(original["equations"]))),
                                [False] * len(original["equations"])),
            _relabeled_instance(original, list(range(original["n"])),
                                equation_order,
                                [False] * len(original["equations"])),
            transformed,
        ):
            invariant_checks += 1
            if canonical_key(variant) != key:
                invariant_checks = -10_000
                break
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 60 and transform_validity == 20 and distinct == 20,
        "invariance_checks": max(invariant_checks, 0),
        "transformation_validity_checks": transform_validity,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "invariant": "8-round weighted bipartite colour refinement after equation-sign normalization",
    }

    sizes = [_answer_size(make_instance(seed=80_000 + seed,
                                        **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"])
             for seed in range(32)]
    answer_chars = max(x[0] for x in sizes)
    answer_elements = max(x[1] for x in sizes)
    answer_tokens = max(x[2] for x in sizes)
    hinted = G9_ARMS["hinted"]
    placebo = G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and compact_ops <= 300
    if not hinted["attempts"]:
        hinted_verdict = "blocked" if hinted.get("errors") else "not_run"
    else:
        hinted_verdict = "too_easy" if hinted["solved"] else "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": json.loads(json.dumps(G9_ARMS)),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["demo_exact_solution_count"] = enumerate_all(
        make_instance(seed=0, **DIFFICULTY["demo"])
    )
    report["all_passed"] = all(
        value.get("pass", True)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
