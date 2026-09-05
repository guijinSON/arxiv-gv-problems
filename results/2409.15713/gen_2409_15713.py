"""Verified Track-B generator for arXiv:2409.15713.

The native object is a succinct Sperner coloring of an exact barycentric
lattice in a 2-simplex.  A witness is a trichromatic elementary triangle.

Generation is by composition of identities.  A non-autonomous fractional-
linear recurrence is assembled from moving cross-ratio coordinates.  Its
terminal state, and hence the witness, follows from the composing identity;
the generator never searches the colored simplex.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


# Keep the repository helper path available, as required by the corpus
# contract.  This family needs only integer arithmetic, so it has a complete
# standard-library implementation when gvlib is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import rationals
except ImportError:  # pragma: no cover - only when copied outside the repo
    rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The fractional-linear update multiplies a cross-ratio of its two moving poles."
)
PLACEBO_HINT: str = (
    "The barycentric indexing rewards careful treatment of endpoints and canonical residues."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "continuous 2-simplex with an exact dyadic witness lattice",
        "succinct Sperner coloring circuit over a prime field",
        "trichromatic elementary triangle",
    ],
    "verification_operations": [
        "exact integer barycentric sums",
        "exact unit-simplex adjacency checks",
        "exact modular recurrence evaluation",
        "exact color comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Use the cross-ratio of the state with two moving poles so a long "
        "non-autonomous recurrence becomes constant multiplication."
    ),
    "hardness_basis": (
        "Track B: generic evaluation of the displayed time-varying Mobius "
        "recurrence takes O(n log P) Euclidean/word operations (O(n) field "
        "steps); at shipping n=250003, seed 314159 measured 28470558 exact "
        "operations and 0.65 seconds, while the moving-pole cross-ratio takes "
        "O(log n + log P) and at most 172 measured operations.  Theorem 15's "
        "PPAD/query lower bound is not claimed for this constructed distribution."
    ),
    "max_answer_tokens": 20,
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

# ``bits`` is chosen from exponents of known Mersenne primes.  The coloring
# circuit uses the prime P=2^bits-1, while witness coordinates have denominator
# Q=2^bits.  Consecutive witness points are therefore exactly 2^-bits apart,
# as required by the paper's continuous formulation.
DIFFICULTY: dict = {
    "demo": {"n": 7, "bits": 5},
    "easy": {"n": 250003, "bits": 31},
    "medium": {"n": 1000003, "bits": 31},
    "hard": {"n": 4000037, "bits": 31},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A lexicographically increasing 3-by-3 JSON integer matrix.  Its rows "
        "are the two consecutive vertices of one unit edge on the active face "
        "and the unique adjacent inward vertex.  Every coordinate is in "
        "0,...,2^bits and each row sums to 2^bits; division by 2^bits gives "
        "the exact rational simplex points."
    ),
    "bounds": {
        "rows": 3,
        "columns": 3,
        "atomic_elements": 9,
        "coordinate_min": 0,
        "coordinate_max": "2^bits",
        "candidate_count": "2^bits-1",
        "order": "rows lexicographically increasing",
    },
}

NOTES: str = (
    "Definitions 4, 7, and 9 fix the standard simplex, the Sperner boundary "
    "condition, the L-infinity proximity rule, "
    "and the requirement for three distinct colors.  Theorem 15 proves PPAD "
    "completeness for the paper's recursively constructed circuit distribution "
    "at side length 2^(-4kn), and Section 7.4 proves its black-box query lower "
    "bound.  Neither result licenses an average-case Track-A claim for a planted "
    "coloring.  The Introduction explicitly says that a bichromatic boundary "
    "switch is found by binary search, and Section 6 warns that exposed color "
    "switches create spurious easy trichromatic regions.  Accordingly this "
    "module is Track B.  The earlier constant-affine design was discarded at "
    "Step 0 because generic matrix powering already compressed it to O(log n), "
    "leaving no gap between the mechanical and intended routes.  The shipped "
    "design uses a genuinely time-varying Mobius recurrence: direct evaluation "
    "is linear in the horizon, while the cross-ratio of two moving poles evolves "
    "multiplicatively.  The certificate is carried through that identity, not "
    "found by scanning the coloring.  Axis order is independently randomized. "
    "The adversary panel tests endpoint/midpoint guesses, one-step greed, linear "
    "extrapolation, a frozen-pole ansatz, and random restarts.  The module uses the paper's continuous "
    "simplex formulation with a Q=2^bits rational witness lattice: the literal "
    "Definition 5 denominator 2^bits-1 would put distinct adjacent points "
    "farther apart than its simultaneous 2^-bits distance bound."
)


# Script-owned measurements from the bare hardening run and the two isolated
# G9 diagnostic runs.  The arms are recorded, while only G9(c) gates.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted": {"solved": 0, "attempts": 3, "error_calls": 0},
    "placebo": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted_verdict": "hardened",
}

_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)
_MERSENNE_PRIME_EXPONENTS = {5, 7, 13, 17, 19, 31, 61, 89, 107, 127}


def _require_int(value, name: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _shift_at(inst: dict, t: int) -> int:
    """The moving pole shared by the two projective reference points."""
    modulus = inst["recurrence_modulus"]
    return (
        inst["shift_quadratic"] * t * t
        + inst["shift_linear"] * t
        + inst["shift_constant"]
    ) % modulus


def _terminal_state(inst: dict) -> int:
    """Evaluate the non-autonomous recurrence by its cross-ratio identity."""
    modulus = inst["recurrence_modulus"]
    gap = inst["pole_gap"]
    multiplier = inst["cross_multiplier"]
    initial_cross_ratio = (1 - gap) % modulus
    final_cross_ratio = (
        pow(multiplier, inst["horizon"], modulus) * initial_cross_ratio
    ) % modulus
    if final_cross_ratio == 1:  # excluded by make_instance; defend corrupted data
        raise ValueError("terminal cross-ratio is the projective point at infinity")
    moving_part = gap * pow(1 - final_cross_ratio, -1, modulus)
    return (_shift_at(inst, inst["horizon"]) + moving_part) % modulus


def _next_state(inst: dict, state: int, t: int) -> int:
    """One literal step of the recurrence displayed to the solver."""
    modulus = inst["recurrence_modulus"]
    gap = inst["pole_gap"]
    multiplier = inst["cross_multiplier"]
    current_shift = _shift_at(inst, t)
    next_shift = _shift_at(inst, t + 1)
    offset = (state - current_shift) % modulus
    denominator = (
        (1 - multiplier) * offset + multiplier * gap
    ) % modulus
    if denominator == 0:
        raise ValueError("recurrence reached its projective pole")
    return (
        next_shift + gap * offset * pow(denominator, -1, modulus)
    ) % modulus


def _inverse_with_operation_count(value: int, modulus: int) -> tuple[int, int]:
    """Extended-Euclid inverse and a conservative exact-operation count."""
    old_r, remainder = modulus, value % modulus
    old_coefficient, coefficient = 0, 1
    operations = 1
    while remainder:
        quotient = old_r // remainder
        operations += 1
        old_r, remainder = remainder, old_r - quotient * remainder
        operations += 2
        old_coefficient, coefficient = (
            coefficient,
            old_coefficient - quotient * coefficient,
        )
        operations += 2
    if old_r != 1:
        raise ValueError("non-invertible field element")
    return old_coefficient % modulus, operations + 1


def _iterated_terminal_state(
    inst: dict, *, count_operations: bool = False
) -> int | tuple[int, int]:
    """Reference direct evaluation, with no cross-ratio compression."""
    state = inst["initial_state"]
    operations = 0
    modulus = inst["recurrence_modulus"]
    gap = inst["pole_gap"]
    multiplier = inst["cross_multiplier"]
    for t in range(inst["horizon"]):
        current_shift = _shift_at(inst, t)
        next_shift = _shift_at(inst, t + 1)
        offset = (state - current_shift) % modulus
        denominator = (
            (1 - multiplier) * offset + multiplier * gap
        ) % modulus
        if count_operations:
            inverse, inverse_ops = _inverse_with_operation_count(
                denominator, modulus
            )
            operations += 19 + inverse_ops
        else:
            inverse = pow(denominator, -1, modulus)
        state = (next_shift + gap * offset * inverse) % modulus
    if count_operations:
        return state, operations
    return state


def _triangle_for_transition(inst: dict, transition: int) -> list[list[int]]:
    """Return the canonical face-straddling triangle at edge ``transition``."""
    total = inst["simplex_denominator"]
    if not 1 <= transition <= inst["recurrence_modulus"]:
        raise ValueError("transition must be in 1,...,recurrence_modulus")
    interior_axis, traversal_axis, remaining_axis = inst["axis_order"]
    low = [0, 0, 0]
    high = [0, 0, 0]
    inward = [0, 0, 0]
    low[interior_axis] = 0
    low[traversal_axis] = transition - 1
    low[remaining_axis] = total - transition + 1
    high[interior_axis] = 0
    high[traversal_axis] = transition
    high[remaining_axis] = total - transition
    inward[interior_axis] = 1
    inward[traversal_axis] = transition - 1
    inward[remaining_axis] = total - transition
    return sorted([low, high, inward])


def _color(inst: dict, point: list[int], transition: int | None = None) -> int:
    """Evaluate the exact Sperner coloring; colors are one-based axis indices."""
    interior_axis, traversal_axis, remaining_axis = inst["axis_order"]
    if point[interior_axis] > 0:
        return interior_axis + 1
    if transition is None:
        transition = _terminal_state(inst) + 1
    if point[traversal_axis] < transition:
        return remaining_axis + 1
    return traversal_axis + 1


def make_instance(n: int, seed: int = 0, bits: int = 31, **params) -> dict:
    """Compose a valid succinct Sperner coloring with a carried witness."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    horizon = _require_int(n, "n", 1)
    _require_int(seed, "seed")
    bits = _require_int(bits, "bits", 2)
    if bits not in _MERSENNE_PRIME_EXPONENTS:
        raise ValueError("bits must be a supported Mersenne-prime exponent")

    denominator = 1 << bits
    modulus = denominator - 1
    rng = random.Random(seed)
    shift_quadratic = rng.randrange(1, modulus)
    shift_linear = rng.randrange(modulus)
    shift_constant = rng.randrange(modulus)

    # The two moving poles are R(t) and R(t)+gap.  In their cross-ratio
    # coordinate the update is just u_(t+1)=multiplier*u_t.  Choose u_0 as a
    # quadratic non-residue and the multiplier as a nontrivial square.  Every
    # u_t is then a non-residue and hence never 1, so the substitution chain has
    # no projective pole.  This theorem-backed parameter choice needs no scan.
    while True:
        initial_cross_ratio = rng.randrange(2, modulus)
        if pow(initial_cross_ratio, (modulus - 1) // 2, modulus) == modulus - 1:
            break
    pole_gap = (1 - initial_cross_ratio) % modulus
    while True:
        square_root = rng.randrange(2, modulus)
        cross_multiplier = square_root * square_root % modulus
        if cross_multiplier != 1:
            break

    axis_order = [0, 1, 2]
    rng.shuffle(axis_order)
    inst = {
        "family": "moving-cross-ratio 2D approximate Sperner transition",
        "dimension": 2,
        "bits": bits,
        "simplex_denominator": denominator,
        "recurrence_modulus": modulus,
        "horizon": horizon,
        "initial_state": (shift_constant + 1) % modulus,
        "pole_gap": pole_gap,
        "cross_multiplier": cross_multiplier,
        "shift_quadratic": shift_quadratic,
        "shift_linear": shift_linear,
        "shift_constant": shift_constant,
        "axis_order": axis_order,
    }
    target = _terminal_state(inst)
    inst["answer"] = _triangle_for_transition(inst, target + 1)
    return inst


def render(inst: dict) -> str:
    total = inst["simplex_denominator"]
    modulus = inst["recurrence_modulus"]
    i, j, k = (axis + 1 for axis in inst["axis_order"])
    statement = f"""SUCCINCT TRICHROMATIC SPERNER TRIANGLE

The exact witness lattice in the continuous 2-simplex is
    D = {{(x1,x2,x3): each xr >= 0 and x1+x2+x3 = M}},
where M={total}.  Dividing all coordinates by M embeds D in the standard
triangle, and consecutive lattice points are exactly 1/M=2^-{inst['bits']}
apart.  Color numbers and coordinate numbers are both 1-based.

A coloring is a Sperner coloring when a point may receive color r only if its
coordinate xr is positive.  The coloring below is specified by an exact
integer circuit with prime modulus P={modulus}.  "mod P" always means the
canonical residue in 0,...,P-1.

Define
    R(t) = ({inst['shift_quadratic']}*t^2 + {inst['shift_linear']}*t
            + {inst['shift_constant']}) mod P.
Let A={inst['pole_gap']} and Q={inst['cross_multiplier']}.  Start with
s_0={inst['initial_state']}.  For t=0,...,{inst['horizon'] - 1}, set

    s_(t+1) = R(t+1) + A*(s_t-R(t))
               * ((1-Q)*(s_t-R(t)) + Q*A)^(-1)  mod P.

Here z^(-1) is the unique multiplicative inverse of nonzero z modulo P;
the displayed denominators are guaranteed nonzero for this instance.  Reduce
every intermediate expression to its canonical residue.
Let T=1+s_{inst['horizon']} (so 1 <= T <= P).  For x=(x1,x2,x3) in D:

  * if x{i}>0, set C(x)={i};
  * if x{i}=0 and x{j}<T, set C(x)={k};
  * if x{i}=0 and x{j}>=T, set C(x)={j}.

This rule is a valid Sperner coloring: every returned color names a positive
coordinate.  Find the face-straddling elementary triangle at which all three
colors occur.  Your answer must be exactly three distinct rows [x1,x2,x3],
listed in lexicographically increasing order.  Two rows must be consecutive
points on the active face x{i}=0, and the third must be their unique adjacent
point with x{i}=1.  Equivalently, every pair of rows differs by at most 1 in
each coordinate.  Repetitions are forbidden and all bounds are inclusive.

Give your final answer inside <answer></answer> tags as one JSON 3-by-3 integer
matrix.  A syntax example (not necessarily a solution) is
<answer>[[0,0,{total}],[0,1,{total - 1}],[1,0,{total - 1}]]</answer>.
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse a tagged JSON matrix, tolerating prose and Markdown around it."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match is None:
        return None
    body = match.group(1).strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 3:
            body = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check the submitted triangle exactly, without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer_not_a_list"
    if len(answer) == 0:
        return False, "empty_answer"
    if len(answer) != 3:
        return False, "wrong_row_count"
    if any(not isinstance(row, list) or len(row) != 3 for row in answer):
        return False, "wrong_matrix_shape"
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for row in answer for value in row
    ):
        return False, "non_integer_coordinate"
    rows = [tuple(row) for row in answer]
    if len(set(rows)) != 3:
        return False, "repeated_point"
    if answer != sorted(answer):
        return False, "rows_not_lexicographic"

    total = inst["simplex_denominator"]
    if any(value < 0 or value > total for row in answer for value in row):
        return False, "coordinate_out_of_range"
    if any(sum(row) != total for row in answer):
        return False, "wrong_barycentric_sum"

    interior_axis, traversal_axis, _ = inst["axis_order"]
    face_rows = [row for row in answer if row[interior_axis] == 0]
    inward_rows = [row for row in answer if row[interior_axis] == 1]
    if len(face_rows) != 2 or len(inward_rows) != 1:
        return False, "not_face_straddling_unit_triangle"
    transition = max(row[traversal_axis] for row in face_rows)
    if not 1 <= transition <= inst["recurrence_modulus"]:
        return False, "not_face_straddling_unit_triangle"
    if answer != _triangle_for_transition(inst, transition):
        return False, "not_face_straddling_unit_triangle"

    actual_transition = _terminal_state(inst) + 1
    colors = {_color(inst, row, actual_transition) for row in answer}
    if len(colors) != 3:
        return False, "not_trichromatic"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the structure-aware boundary-triangle language."""
    transition = rng.randrange(1, inst["recurrence_modulus"] + 1)
    return _triangle_for_transition(inst, transition)


def search_space(inst: dict) -> int | None:
    """There is one canonical face-straddling candidate per active-face edge."""
    return inst["recurrence_modulus"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force tiny grids only; cap work rather than hiding a large scan."""
    total = inst["recurrence_modulus"]
    if total > 10000:
        return None
    count = 0
    for transition in range(1, total + 1):
        if verify(inst, _triangle_for_transition(inst, transition))[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize simultaneous coordinate/color relabeling."""
    # The induced coloring, modulo a simultaneous relabeling of its three
    # barycentric coordinates and colors, is determined by M and its transition.
    # This intentionally contains no seed and ignores the randomized axis order.
    payload = [inst["simplex_denominator"], _terminal_state(inst) + 1]
    raw = json.dumps(payload, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _compact_operation_count(inst: dict) -> int:
    """Count the intended cross-ratio route's exact field arithmetic."""
    modulus = inst["recurrence_modulus"]
    final_cross_ratio = (
        pow(inst["cross_multiplier"], inst["horizon"], modulus)
        * (1 - inst["pole_gap"])
    ) % modulus
    _, inverse_ops = _inverse_with_operation_count(
        1 - final_cross_ratio, modulus
    )
    exponent = inst["horizon"]
    power_ops = max(0, exponent.bit_length() - 1) + max(0, exponent.bit_count() - 1)
    # Twenty covers evaluating R(n), forming u_0 and u_n, applying the inverse
    # cross-ratio, adding T, and writing the three barycentric rows.
    return inverse_ops + power_ops + 20


def escalate(params: dict) -> dict | str | None:
    """Grow circuit length while keeping the witness at nine 31-bit atoms."""
    horizon = _require_int(params.get("n"), "n", 1)
    bits = _require_int(params.get("bits"), "bits", 2)
    return {"n": horizon * 4 + 1, "bits": bits}


def _relabel_instance(inst: dict, permutation: tuple[int, int, int]) -> dict:
    """Apply an old-axis -> new-axis relabeling, carrying the witness."""
    transformed = {
        key: json.loads(json.dumps(value))
        for key, value in inst.items()
        if key != "answer"
    }
    transformed["axis_order"] = [permutation[axis] for axis in inst["axis_order"]]
    carried = []
    for row in inst["answer"]:
        new_row = [0, 0, 0]
        for old_axis, value in enumerate(row):
            new_row[permutation[old_axis]] = value
        carried.append(new_row)
    transformed["answer"] = sorted(carried)
    return transformed


def _attack_guesses(inst: dict) -> dict[str, list[int]]:
    modulus = inst["recurrence_modulus"]
    gap = inst["pole_gap"]
    multiplier = inst["cross_multiplier"]
    initial = inst["initial_state"]
    horizon = inst["horizon"]
    first = _next_state(inst, initial, 0)
    final_cross_ratio = (
        pow(multiplier, horizon, modulus) * (1 - gap)
    ) % modulus
    frozen_shift = (
        _shift_at(inst, 0)
        + gap * pow(1 - final_cross_ratio, -1, modulus)
    ) % modulus
    return {
        "outlier_endpoints_midpoint": [1, (modulus + 1) // 2, modulus],
        "greedy_one_recurrence_step": [1 + first],
        "linear_extrapolation": [
            1 + (initial + horizon * (first - initial)) % modulus
        ],
        "frozen_moving_poles": [1 + frozen_shift],
        "terminal_pole_ansatz": [
            1 + (_shift_at(inst, horizon) + gap) % modulus
        ],
    }


def _answer_chars_and_atoms(answer) -> tuple[int, int]:
    chars = len(json.dumps(answer, separators=(",", ":")))

    def atoms(value) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    return chars, atoms(answer)


def selftest() -> dict:
    """Run all mandatory correctness, resistance, scaling, and audit gates."""
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset and several seeds, plus JSON-native answers.
    planted_attempts = 0
    planted_passes = 0
    json_passes = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            planted_passes += int(verify(inst, inst["answer"])[0])
            json_passes += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": planted_passes == planted_attempts == json_passes,
        "verified": planted_passes,
        "attempts": planted_attempts,
        "json_native": json_passes,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    sample = make_instance(seed=314159, **shipping_params)
    good = sample["answer"]
    corruptions = {}
    corruptions["drop_one"] = good[:-1]
    corruptions["swap_rows"] = [good[1], good[0], good[2]]
    corruptions["duplicate_row"] = [good[0], good[0], good[2]]
    corruptions["empty"] = []
    out_of_range = json.loads(json.dumps(good))
    out_of_range[0][0] = sample["simplex_denominator"] + 1
    out_of_range = sorted(out_of_range)
    corruptions["out_of_range"] = out_of_range
    corruption_reasons = {
        name: verify(sample, value)[1] for name, value in corruptions.items()
    }
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not verify(sample, value)[0] for value in corruptions.values())
            and len(set(corruption_reasons.values())) == len(corruptions)
        ),
        "cases": len(corruptions),
        "reasons": corruption_reasons,
    }

    encoded = json.dumps(good, separators=(",", ":"))
    response = (
        "I followed the boundary transition.\n\n```text\n"
        f"<answer>{encoded}</answer>\n```\nThat is my final triangle."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == good and verify(sample, parsed)[0],
        "parsed": parsed == good,
        "surrounding_prose": True,
    }

    # G4 and the shipping-density part of G5 share the required 200k uniform,
    # structure-aware draws.
    guess_rng = random.Random(8675309)
    guess_total = 200000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(sample, random_candidate(sample, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    exact_density = 1.0 / search_space(sample)
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6 and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "exact_structure_aware_probability": exact_density,
        "structure_aware_space": search_space(sample),
    }

    t0 = time.perf_counter()
    terminal = _iterated_terminal_state(sample)
    reference_wall = time.perf_counter() - t0
    counted_terminal, reference_operation_count = _iterated_terminal_state(
        sample, count_operations=True
    )
    reference_ok = verify(
        sample, _triangle_for_transition(sample, terminal + 1)
    )[0] and counted_terminal == terminal == _terminal_state(sample)
    demo_for_count = make_instance(seed=314159, **DIFFICULTY["demo"])
    demo_solution_count = enumerate_all(demo_for_count)
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            reference_ok
            and exact_density < 1e-6
            and demo_solution_count == 1
        ),
        "shipping_sampled_valid_fraction": guess_probability,
        "shipping_density_samples": guess_total,
        "shipping_density_hits": guess_hits,
        "analytic_solution_count": 1,
        "analytic_valid_fraction": exact_density,
        "demo_enumerated_solution_count": demo_solution_count,
        "demo_candidate_space": search_space(demo_for_count),
        "reference_wall_clock_seconds": reference_wall,
        "reference_operation_count": reference_operation_count,
        "reference_iterations": sample["horizon"],
        "reference_complexity": "O(n log P) Euclidean/word operations; O(n) field steps",
    }

    attack_counts = {
        "outlier_endpoints_midpoint": 0,
        "greedy_one_recurrence_step": 0,
        "linear_extrapolation": 0,
        "frozen_moving_poles": 0,
        "terminal_pole_ansatz": 0,
        "random_restart_256": 0,
    }
    attack_attempts = 8
    reference_successes = 0
    reference_wall_total = 0.0
    for seed in range(100, 100 + attack_attempts):
        inst = make_instance(seed=seed, **shipping_params)
        for name, guesses in _attack_guesses(inst).items():
            solved = any(
                verify(inst, _triangle_for_transition(inst, guess))[0]
                for guess in guesses
            )
            attack_counts[name] += int(solved)
        restart_rng = random.Random(seed ^ 0x5EEDFACE)
        restart_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_solved = True
                break
        attack_counts["random_restart_256"] += int(restart_solved)

        start = time.perf_counter()
        terminal = _iterated_terminal_state(inst)
        reference_wall_total += time.perf_counter() - start
        reference_successes += int(verify(
            inst, _triangle_for_transition(inst, terminal + 1)
        )[0])
    attacks = {
        name: {"successes": successes, "attempts": attack_attempts}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "direct evaluation of the time-varying Mobius recurrence",
            "complexity": "O(n log P) Euclidean/word operations; O(n) field steps",
            "wall_clock_sec_mean": reference_wall_total / attack_attempts,
            "operations": reference_operation_count,
            "iterations": sample["horizon"],
            "solves": f"{reference_successes}/{attack_attempts}, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    report["G7_scales"] = {
        "pass": (
            doubled["horizon"] > sample["horizon"]
            and verify(doubled, doubled["answer"])[0]
            and search_space(doubled) == search_space(sample)
        ),
        "shipping_horizon": sample["horizon"],
        "doubled_horizon": doubled["horizon"],
        "shipping_reference_field_step_lower_bound": 19 * sample["horizon"],
        "doubled_reference_field_step_lower_bound": 19 * doubled["horizon"],
    }

    permutations = list(itertools.permutations(range(3)))
    invariance_checks = 0
    carried_checks = 0
    distinct_keys = set()
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **shipping_params)
        key = canonical_key(inst)
        distinct_keys.add(key)
        for permutation in permutations:
            transformed = _relabel_instance(inst, permutation)
            invariance_checks += 1
            if canonical_key(transformed) != key:
                invariance_checks = -10**9
                break
            carried_checks += int(verify(transformed, transformed["answer"])[0])
        # A nontrivial composition, explicitly rather than only relying on the
        # fact that the six permutations are closed under composition.
        first, second = permutations[3], permutations[4]
        composed = tuple(second[first[index]] for index in range(3))
        transformed = _relabel_instance(inst, composed)
        invariance_checks += 1
        if canonical_key(transformed) != key:
            invariance_checks = -10**9
        carried_checks += int(verify(transformed, transformed["answer"])[0])
    expected_invariance = 20 * (len(permutations) + 1)
    expected_carried = expected_invariance
    report["G8_canonical_key"] = {
        "pass": (
            invariance_checks == expected_invariance
            and carried_checks == expected_carried
            and len(distinct_keys) == 20
        ),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated_keys": len(distinct_keys),
        "unrelated_instances": 20,
        "transformations": "all 6 axis/color permutations plus a composition",
    }

    answer_chars = 0
    answer_atoms = 0
    intended_ops = 0
    for seed in range(64):
        inst = make_instance(seed=9000 + seed, **shipping_params)
        chars, atoms = _answer_chars_and_atoms(inst["answer"])
        answer_chars = max(answer_chars, chars)
        answer_atoms = max(answer_atoms, atoms)
        intended_ops = max(intended_ops, _compact_operation_count(inst))
    answer_tokens = (answer_chars + 3) // 4
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_minus_placebo = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_complete": all(arm["attempts"] >= 3 for arm in arms.values()),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
