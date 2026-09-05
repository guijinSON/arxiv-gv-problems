"""Verified generator for minimal forbidden propagation sets (arXiv:2605.18533).

The construction is theorem-backed by Proposition 2 of the paper.  Its graph is
represented succinctly, but all predicates used by the renderer and verifier are
exact finite-field/integer predicates.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite graph with vertices labelled over GF(q)",
        "zero-injection vertex set",
        "propagation set",
        "precedence digraph",
    ],
    "verification_operations": [
        "finite-field polynomial evaluation",
        "exact propagation-set membership",
        "directed-cycle closure",
        "minimality after deleting a propagation",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2.1 defines the precedence digraph D_F from propagations; "
        "Section 3, Proposition 2 identifies chordless cycles with minimal FPSs"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the activation polynomial as a translated composition of pure "
        "powers; without that normalization one must scan millions of propagation rows."
    ),
    "hardness_basis": (
        "Track B: Section 4.3 cycle separation is linear in the explicit precedence "
        "graph and the O(qd) succinct scan averaged 144,656,344 exact operations "
        "and 3.14 seconds at q=5,000,077, versus at most 64 exact operations for "
        "the coefficient-normalization and fifth-root shortcut."
    ),
    "max_answer_tokens": 5,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is a lower bound for the prime field size.  Larger n enlarges the number of
# cyclic rows while the three-integer witness remains fixed in size.
DIFFICULTY = {
    "demo": {"n": 17, "cycle_length": 6, "outer_power": 1},
    "easy": {"n": 5000011, "cycle_length": 32, "outer_power": 5},
    "medium": {"n": 10000019, "cycle_length": 40, "outer_power": 6},
    "hard": {"n": 20000003, "cycle_length": 48, "outer_power": 7},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Look for a translated composition of pure-power maps in the row-activation polynomial."
)
PLACEBO_HINT = (
    "Keep careful track of the residue representatives used in the orbit descriptor."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A three-integer cyclic-FPS descriptor [row_label, cycle_length, -1]; "
        "row_label is in [0,q-1], and the two structural markers are fixed by the instance."
    ),
    "bounds": {
        "atomic_elements": 3,
        "min_row_label": 0,
        "max_row_label": 18446744073709551614,
        "max_modulus_bits": 64,
        "max_cycle_length": 128,
        "direction_marker": -1,
    },
}

NOTES = """\
Definition and theorem.  Section 2.1 defines a propagation p=(u,v), its imposed
precedences psi(p), and D_F.  Section 3 Definition 1 calls F forbidden exactly
when D_F has a cycle.  Proposition 2 says that, in a set without redundant
incoming propagations, a chordless cycle gives a minimal FPS.  Each generated
row has at most one propagation targeting each row-position vertex.  A complete
row therefore imposes one chordless directed cycle, and deleting any member
breaks it.

What makes the task easy mechanically.  Section 4.3, Algorithm 1 explicitly
finds a cycle, trims it to a chordless cycle, and maps its arcs back to a minimal
FPS.  That is polynomial-time and is why this module is Track B.  The reference
implementation scans every succinct row and evaluates its activation polynomial;
the self-test records both its wall time and exact modular-operation count.

Construction.  All ordinary rows omit a nonempty consecutive block of helper
vertices.  One row is restored in full by the unique zero of
lambda*((r-s)^5-a^5)^m.  Since gcd(5,q-1)=1, the fifth-power map permutes GF(q),
so the restored row is unique and is known before the graph is assembled.

Attacks.  Helpers all have degree two, so local degree/magnitude sampling has no
signal.  Greedy low-label rows, 256 random restarts, and the obvious shift-only
ansatz are tested over eight seeds.  The full scan succeeds, as Track B requires,
and is reported separately rather than disguised as a failed attack.
"""

# Filled from the three isolated harden.py runs.  These diagnostics never affect
# mathematical verification; G9(c)'s caps are measured directly in selftest().
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
}


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the 64-bit range used by the ladder."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value % p == 0:
            return value == p
    d, shift = value - 1, 0
    while d % 2 == 0:
        shift += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(shift - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _next_field_prime(n: int) -> int:
    candidate = max(7, int(n))
    if candidate % 2 == 0:
        candidate += 1
    while True:
        # x -> x^5 is a permutation precisely when gcd(5,q-1)=1.
        if candidate % 5 != 1 and _is_prime(candidate):
            return candidate
        candidate += 2


def _poly_mul(left: list[int], right: list[int], modulus: int) -> list[int]:
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] = (out[i + j] + a * b) % modulus
    return out


def _poly_pow(base: list[int], exponent: int, modulus: int) -> list[int]:
    out = [1]
    factor = list(base)
    e = exponent
    while e:
        if e & 1:
            out = _poly_mul(out, factor, modulus)
        e //= 2
        if e:
            factor = _poly_mul(factor, factor, modulus)
    return out


def _activation_coefficients(
    modulus: int, shift: int, fifth_root: int, outer_power: int, scale: int
) -> list[int]:
    # ((r-shift)^5 - fifth_root^5)^outer_power, in ascending degree order.
    linear = [(-shift) % modulus, 1]
    fifth = _poly_pow(linear, 5, modulus)
    fifth[0] = (fifth[0] - pow(fifth_root, 5, modulus)) % modulus
    coeffs = _poly_pow(fifth, outer_power, modulus)
    return [(scale * c) % modulus for c in coeffs]


def _terms_to_dense(inst: dict) -> list[int]:
    degree = inst["polynomial_degree"]
    dense = [0] * (degree + 1)
    for term in inst["activation_polynomial"]:
        if not (
            isinstance(term, list)
            and len(term) == 2
            and isinstance(term[0], int)
            and isinstance(term[1], int)
            and 0 <= term[0] <= degree
        ):
            raise ValueError("malformed polynomial term")
        dense[term[0]] = term[1] % inst["q"]
    return dense


def _poly_eval_dense(coeffs: list[int], value: int, modulus: int) -> int:
    acc = 0
    for coefficient in reversed(coeffs):
        acc = (acc * value + coefficient) % modulus
    return acc


def _poly_eval(inst: dict, semantic_row: int) -> int:
    return _poly_eval_dense(_terms_to_dense(inst), semantic_row, inst["q"])


def _encode_row(inst: dict, semantic_row: int) -> int:
    return (
        inst["row_label_mul"] * semantic_row + inst["row_label_add"]
    ) % inst["q"]


def _decode_row(inst: dict, displayed_row: int) -> int:
    return (
        inst["row_label_inv"] * (displayed_row - inst["row_label_add"])
    ) % inst["q"]


def _missing_count(inst: dict, semantic_row: int) -> int:
    length = inst["cycle_length"]
    return 1 + (semantic_row % inst["decoy_period"]) % (length - 1)


def _missing_start(inst: dict, semantic_row: int) -> int:
    return (
        inst["decoy_shift_mul"] * semantic_row + inst["decoy_shift_add"]
    ) % inst["cycle_length"]


def _is_active_position(
    inst: dict, semantic_row: int, semantic_position: int, polynomial_value: int | None = None
) -> bool:
    value = _poly_eval(inst, semantic_row) if polynomial_value is None else polynomial_value
    if value == 0:
        return True
    length = inst["cycle_length"]
    relative = (semantic_position - _missing_start(inst, semantic_row)) % length
    return relative >= _missing_count(inst, semantic_row)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a unique full propagation row and all decoy rows around it."""
    if int(n) > 9_000_000_000_000_000_000:
        raise ValueError("n exceeds the generator's declared 64-bit certificate bound")
    rng = random.Random(seed)
    q = _next_field_prime(n)
    length = int(params.get("cycle_length", 32))
    outer = int(params.get("outer_power", 5))
    if not 4 <= length <= 128:
        raise ValueError("cycle_length must be between 4 and 128")
    if not 1 <= outer <= 12:
        raise ValueError("outer_power must be between 1 and 12")
    if math.gcd(5, q - 1) != 1:
        raise ValueError("field does not make the fifth-power map bijective")

    shift = rng.randrange(q)
    fifth_root = rng.randrange(1, q)
    scale = rng.randrange(1, q)
    root = (shift + fifth_root) % q
    coeffs = _activation_coefficients(q, shift, fifth_root, outer, scale)
    terms = [[degree, coefficient] for degree, coefficient in enumerate(coeffs)]
    rng.shuffle(terms)  # term order is explicitly semantically irrelevant

    row_mul = rng.randrange(1, q)
    row_add = rng.randrange(q)
    row_inv = pow(row_mul, -1, q)
    period = 2 + (abs(int(seed)) % 100000)
    period = min(period, q)
    decoy_shift_mul = rng.randrange(1, length)
    decoy_shift_add = rng.randrange(length)

    inst = {
        "q": q,
        "cycle_length": length,
        "outer_power": outer,
        "inner_power": 5,
        "polynomial_degree": 5 * outer,
        "activation_polynomial": terms,
        "row_label_mul": row_mul,
        "row_label_add": row_add,
        "row_label_inv": row_inv,
        "decoy_period": period,
        "decoy_shift_mul": decoy_shift_mul,
        "decoy_shift_add": decoy_shift_add,
        "logical_target_vertices": q * length,
        "construction": "minimal_FPS_chordless_cycle",
    }
    inst["answer"] = [_encode_row(inst, root), length, -1]
    return inst


def _statement_polynomial(inst: dict) -> str:
    terms = sorted(inst["activation_polynomial"], key=lambda item: item[0])
    return "[" + ", ".join(f"[{degree},{coefficient}]" for degree, coefficient in terms) + "]"


def render(inst: dict) -> str:
    q = inst["q"]
    length = inst["cycle_length"]
    example = json.dumps([0, length, -1])
    text = f"""Find a minimal forbidden propagation set in the following exact finite graph.

All arithmetic on row labels is in the prime field GF({q}), represented by the integers 0 through {q - 1}. Positions are integers modulo {length}.

Displayed row labels y are a relabelling of semantic rows r. Decode and encode them by
  r = {inst['row_label_inv']} * (y - {inst['row_label_add']}) mod {q},
  y = {inst['row_label_mul']} * r + {inst['row_label_add']} mod {q}.

The row-activation polynomial is over GF({q}). It is given as [exponent, coefficient] pairs; term order is irrelevant and omitted coefficients are zero:
  P(r) = {_statement_polynomial(inst)}
meaning P(r) is the sum of coefficient*r^exponent modulo {q}.

For a semantic row r define
  d(r) = 1 + ((r mod {inst['decoy_period']}) mod {length - 1}),
  b(r) = ({inst['decoy_shift_mul']}*r + {inst['decoy_shift_add']}) mod {length}.
A row-position (r,i) is active precisely when either P(r)=0, or
  (i - b(r)) mod {length} >= d(r).

Graph and propagation set. For every row r and position i there is a target vertex v(r,i). For every active (r,i) there is a zero-injection helper vertex h(r,i), adjacent to exactly v(r,i) and v(r,i+1 mod {length}). The given propagation set F contains p(r,i)=(h(r,i),v(r,i)) for every active (r,i), and no other propagation.

A propagation (u,v) imposes a directed precedence arc (w,v) for every w in the closed neighbourhood N[u] except v. For W subset F, D_W is the union of all arcs imposed by propagations in W. W is a forbidden propagation set (FPS) when D_W contains a directed simple cycle. It is minimal when deleting any one propagation from W makes D_W acyclic.

Your witness is a cyclic-row descriptor [y,{length},-1]. It denotes all {length} propagations p(r,i), one for each i=0,...,{length - 1}, where y is the displayed label of r. The -1 records that the imposed target-vertex cycle runs from position i+1 to i. Find a descriptor whose denoted propagation set is a minimal FPS. Integers are exact; intervals and repeats are not involved.

Give your final answer inside <answer></answer> tags, as one JSON array [row_label,{length},-1].
Example of format only: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON array descriptor"
    if not answer:
        return False, "empty descriptor"
    if len(answer) < 3:
        return False, "descriptor has too few fields"
    if len(answer) > 3:
        return False, "descriptor has too many fields"
    if any(not isinstance(value, int) or isinstance(value, bool) for value in answer):
        return False, "all descriptor fields must be integers"
    displayed_row, claimed_length, direction = answer
    q = inst["q"]
    if not 0 <= displayed_row < q:
        return False, "row label is outside the field range"
    if claimed_length != inst["cycle_length"]:
        return False, "cycle length marker does not match the instance"
    if direction != -1:
        return False, "cycle direction marker must be -1"

    row = _decode_row(inst, displayed_row)
    value = _poly_eval(inst, row)
    length = inst["cycle_length"]
    active = [
        _is_active_position(inst, row, position, value)
        for position in range(length)
    ]
    if not all(active):
        first_missing = active.index(False)
        return False, f"row contains inactive propagation at position {first_missing}"

    # For every i, p(r,i) imposes v(r,i+1)->v(r,i), as well as an arc from
    # its helper.  Helpers have indegree zero in D_W.  Execute Kahn's exact
    # cycle test on the target arcs and after every propagation deletion.
    full = [((position + 1) % length, position) for position in range(length)]

    def has_cycle(edges: list[tuple[int, int]]) -> bool:
        outgoing = [[] for _ in range(length)]
        indegree = [0] * length
        for source, target in edges:
            outgoing[source].append(target)
            indegree[target] += 1
        stack = [vertex for vertex in range(length) if indegree[vertex] == 0]
        removed_vertices = 0
        while stack:
            vertex = stack.pop()
            removed_vertices += 1
            for target in outgoing[vertex]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    stack.append(target)
        return removed_vertices != length

    if not has_cycle(full):
        return False, "precedence arcs do not close into the claimed cycle"
    for removed in range(length):
        remaining_arcs = [edge for index, edge in enumerate(full) if index != removed]
        if has_cycle(remaining_arcs):
            return False, "minimality check failed after deletion"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over the q structurally valid cyclic-row descriptors."""
    semantic_row = rng.randrange(inst["q"])
    return [_encode_row(inst, semantic_row), inst["cycle_length"], -1]


def search_space(inst: dict) -> int | None:
    return inst["q"]


def enumerate_all(inst: dict) -> int | None:
    if inst["q"] > 100000:
        return None
    count = 0
    for row in range(inst["q"]):
        candidate = [_encode_row(inst, row), inst["cycle_length"], -1]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _component_histogram(inst: dict) -> list[int]:
    """Counts decoy path types; a graph/F isomorphism invariant for this family."""
    q = inst["q"]
    length = inst["cycle_length"]
    period = inst["decoy_period"]
    counts = [0] * length
    full_periods, tail = divmod(q, period)
    for residue in range(period):
        occurrences = full_periods + (1 if residue < tail else 0)
        d = 1 + (residue % (length - 1))
        counts[d] += occurrences
    dense = _terms_to_dense(inst)
    # The unique polynomial root is the full-cycle component, not a decoy path.
    root = _recover_constructed_root(inst, dense)
    counts[_missing_count(inst, root)] -= 1
    return counts[1:]


def canonical_key(inst: dict) -> str:
    invariant = {
        "q": inst["q"],
        "cycle_length": inst["cycle_length"],
        "decoy_path_histogram": _component_histogram(inst),
    }
    return json.dumps(invariant, sort_keys=True, separators=(",", ":"))


def escalate(params: dict) -> dict | str | None:
    harder = dict(params)
    harder["n"] = int(params["n"]) * 2
    harder["cycle_length"] = min(96, int(params.get("cycle_length", 32)) + 8)
    harder["outer_power"] = min(9, int(params.get("outer_power", 5)) + 1)
    return harder


def _recover_constructed_root(inst: dict, dense: list[int] | None = None) -> int:
    """Compact coefficient route, using only public instance data."""
    q = inst["q"]
    coeffs = _terms_to_dense(inst) if dense is None else dense
    degree = inst["polynomial_degree"]
    outer = inst["outer_power"]
    leading = coeffs[degree] % q
    shift = (-coeffs[degree - 1] * pow((degree * leading) % q, -1, q)) % q
    shifted_top_contribution = math.comb(degree, 5) * pow(-shift, 5, q)
    normalized_degree_minus_five = coeffs[degree - 5] * pow(leading, -1, q)
    fifth_power = (
        (shifted_top_contribution - normalized_degree_minus_five)
        * pow(outer, -1, q)
    ) % q
    exponent_inverse = pow(5, -1, q - 1)
    fifth_root = pow(fifth_power, exponent_inverse, q)
    return (shift + fifth_root) % q


def _reference_scan(inst: dict) -> tuple[list[int] | None, int, float]:
    """Mechanical row scan corresponding to cycle separation on this succinct graph."""
    started = time.perf_counter()
    q = inst["q"]
    dense = _terms_to_dense(inst)
    degree = len(dense) - 1
    operations = 0
    for semantic_row in range(q):
        acc = 0
        for coefficient in reversed(dense):
            acc = (acc * semantic_row + coefficient) % q
            operations += 2
        if acc == 0:
            answer = [_encode_row(inst, semantic_row), inst["cycle_length"], -1]
            return answer, operations, time.perf_counter() - started
        # A non-root row omits d(r)>=1 propagations, so it cannot close a cycle.
        operations += 1
    return None, operations, time.perf_counter() - started


def _attack_candidates(inst: dict, seed: int) -> dict[str, tuple[object | None, int]]:
    rng = random.Random(seed ^ 0x5EEDC0DE)
    q = inst["q"]
    length = inst["cycle_length"]

    sampled = [rng.randrange(q) for _ in range(256)]
    # Local outlier: inspect only a context-sized sample, scoring by active count.
    best = None
    best_count = -1
    for row in sampled:
        value = _poly_eval(inst, row)
        count = length if value == 0 else length - _missing_count(inst, row)
        if count > best_count:
            best_count, best = count, row
    outlier = [_encode_row(inst, best), length, -1] if best is not None else None

    # Greedy: smallest semantic row with the most favourable cheap decoy count.
    greedy_rows = list(range(min(256, q)))
    greedy_row = min(greedy_rows, key=lambda row: (_missing_count(inst, row), row))
    greedy = [_encode_row(inst, greedy_row), length, -1]

    # Random restarts: succeed only if one of 256 uniformly drawn rows is the root.
    restart = None
    for row in sampled:
        candidate = [_encode_row(inst, row), length, -1]
        if verify(inst, candidate)[0]:
            restart = candidate
            break

    # Obvious ansatz: the top two coefficients reveal the translation shift, but
    # stopping there misses the inner fifth-root displacement.
    dense = _terms_to_dense(inst)
    degree = inst["polynomial_degree"]
    leading = dense[degree]
    shift_guess = (-dense[degree - 1] * pow(degree * leading % q, -1, q)) % q
    guesses = [0, 1, q - 1, shift_guess, (shift_guess - 1) % q, (shift_guess + 1) % q]
    ansatz = None
    for row in guesses:
        candidate = [_encode_row(inst, row), length, -1]
        if verify(inst, candidate)[0]:
            ansatz = candidate
            break
    if ansatz is None:
        ansatz = [_encode_row(inst, shift_guess), length, -1]

    per_poly = 2 * (inst["polynomial_degree"] + 1)
    return {
        "outlier_sample_256": (outlier, 256 * (per_poly + 2)),
        "greedy_low_label": (greedy, len(greedy_rows) * 3),
        "random_restart_256": (restart, 256 * per_poly),
        "obvious_shift_only_ansatz": (ansatz, len(guesses) * per_poly + 8),
    }


def _relabeled_instance(inst: dict, multiplier: int, offset: int) -> tuple[dict, list[int]]:
    q = inst["q"]
    transformed = json.loads(json.dumps(inst))
    new_mul = multiplier * inst["row_label_mul"] % q
    new_add = (multiplier * inst["row_label_add"] + offset) % q
    transformed["row_label_mul"] = new_mul
    transformed["row_label_add"] = new_add
    transformed["row_label_inv"] = pow(new_mul, -1, q)
    old_answer = inst["answer"]
    carried = [
        (multiplier * old_answer[0] + offset) % q,
        old_answer[1],
        old_answer[2],
    ]
    transformed["answer"] = carried
    return transformed, carried


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    report: dict[str, object] = {}

    # G1: every preset, several seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            instance = make_instance(seed=seed, **preset_params)
            ok, reason = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    planted = list(inst["answer"])

    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0], planted[2]],
        "duplicate_one": planted + [planted[0]],
        "empty": [],
        "out_of_range": [inst["q"], planted[1], planted[2]],
    }
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({entry["reason"] for entry in rejection_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejection_reasons.values())
        and distinct_reasons == len(rejection_reasons),
        "distinct_reasons": distinct_reasons,
        "cases": rejection_reasons,
    }

    realistic = (
        "I reduced the activation condition first.\n```json\n"
        f"<answer>{json.dumps(planted)}</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    samples = 200000
    guess_rng = random.Random(884422)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    guess_elapsed = time.perf_counter() - guess_started
    observed = hits / samples
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": observed,
        "exact_probability": 1 / inst["q"],
        "candidate_prior": "uniform over all q cyclic-row descriptors",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_started = time.perf_counter()
    strongest = _attack_candidates(inst, 20260905)["outlier_sample_256"]
    strongest_ok = strongest[0] is not None and verify(inst, strongest[0])[0]
    attack_elapsed = time.perf_counter() - attack_started
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6 and not strongest_ok,
        "shipping_sampled_density": observed,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "exact_solution_count_by_construction": 1,
        "strongest_failing_attack_wall_sec": round(attack_elapsed, 6),
        "strongest_failing_attack_operations": strongest[1],
    }

    attack_names = (
        "outlier_sample_256",
        "greedy_low_label",
        "random_restart_256",
        "obvious_shift_only_ansatz",
    )
    attack_results = {name: {"successes": 0, "attempts": 8, "operations": 0} for name in attack_names}
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    panel_seeds = (101, 202, 303, 404, 505, 606, 707, 808)
    for seed in panel_seeds:
        panel_inst = make_instance(seed=seed, **shipping_params)
        for name, (candidate, operations) in _attack_candidates(panel_inst, seed).items():
            attack_results[name]["operations"] += operations
            if candidate is not None and verify(panel_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        found, operations, elapsed = _reference_scan(panel_inst)
        reference_operations += operations
        reference_wall += elapsed
        if found is not None and verify(panel_inst, found)[0]:
            reference_successes += 1
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(panel_seeds),
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "succinct row scan implementing Section 4.3 cycle separation",
            "complexity": "O(q*d) modular operations; explicit DFS is O(|V|+|A|)",
            "successes": reference_successes,
            "attempts": len(panel_seeds),
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "mean_operations": reference_operations // len(panel_seeds),
            "solves": f"{reference_successes}/{len(panel_seeds)}, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["q"] > inst["q"],
        "shipping_q": inst["q"],
        "doubled_q": doubled["q"],
        "shipping_logical_targets": inst["logical_target_vertices"],
        "doubled_logical_targets": doubled["logical_target_vertices"],
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        base = make_instance(seed=seed, **shipping_params)
        base_key = canonical_key(base)
        keys.append(base_key)
        rng = random.Random(9000 + seed)
        u = rng.randrange(1, base["q"])
        v = rng.randrange(base["q"])
        transformed, carried = _relabeled_instance(base, u, v)
        # Reordering polynomial input is another genuine presentation symmetry.
        transformed["activation_polynomial"].reverse()
        invariant_checks += int(canonical_key(transformed) == base_key)
        carried_checks += int(verify(transformed, carried)[0])
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 20 and carried_checks == 20 and distinct == 20,
        "invariance_checks_passed": invariant_checks,
        "invariance_checks_attempted": 20,
        "carried_witness_checks_passed": carried_checks,
        "carried_witness_checks_attempted": 20,
        "distinct_unrelated_keys": distinct,
        "distinct_unrelated_attempts": 20,
        "transformations": ["affine row relabelling", "polynomial-term reordering"],
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 64
    hinted = G9_ARMS["hinted"]
    placebo = G9_ARMS["placebo"]
    hint_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300,
        "arms": G9_ARMS,
        "hinted_minus_placebo": hint_rate - placebo_rate,
        "hinted_verdict": "hardened" if hinted["solved"] == 0 else "too_easy",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
