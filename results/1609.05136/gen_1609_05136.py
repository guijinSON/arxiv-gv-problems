"""Verified problem generator for arXiv:1609.05136.

The generated objects are exact Consensus-Halving instances with rational
step-density valuations. A witness is the rational normalized coordinate of
one cut in every promised slot; the alternating +/- partition is reconstructed
from those coordinates and checked by exact integration.

Generation is inverse: choose the cut coordinates first, then choose each
agent's two guard densities so that the planted partition balances that agent.
The planted witness is never found by solving the generated instance.
"""

from __future__ import annotations

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
from fractions import Fraction


# gvlib is standard-library-only. Keep a Fraction fallback so this module also
# remains usable when copied away from the repository.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import rationals
except ImportError:  # pragma: no cover - only outside this repository
    rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Every agent has the same unit density on all cut slots, and the doubled "
    "slots collectively form a permutation of the slot indices."
)
PLACEBO_HINT: str = (
    "Keep every agent's guard index and doubled-slot index aligned with the "
    "stated zero-based interval indexing."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "optimization",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "interval with rational step-density valuations",
        "alternating consensus-halving partition",
        "rational normalized cut coordinates",
    ],
    "verification_operations": [
        "exact rational interval integration",
        "exact rational addition",
        "exact equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Decompose every balance row into one common all-slot contribution and "
        "one permuted exceptional coordinate; without this, the displayed "
        "conditions look like a dense exact linear system."
    ),
    "hardness_basis": (
        "Track B: exact Gauss-Jordan elimination solves the promised dense "
        "balance system in O(n^3) rational field operations; at shipping "
        "n=96 it uses 54819 median measured field operations, while the rank-one-plus-"
        "permutation decomposition uses 288 exact operations."
    ),
    "max_answer_tokens": 247,
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
    "demo": {"n": 2, "q": 3},
    "easy": {"n": 24, "q": 31},
    "medium": {"n": 48, "q": 127},
    "hard": {"n": 96, "q": 257},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A vector of exactly n rationals z_j=a_j/q, one per cut slot, where "
        "a_j is an integer with -q<a_j<q; z_j encodes the cut "
        "t_j=3j+3/2+(-1)^j z_j/2. Repeated coordinates are allowed."
    ),
    "bounds": {
        "coordinates": "n",
        "grid_denominator": "q",
        "integer_numerator_min": "-q+1",
        "integer_numerator_max": "q-1",
        "choices_per_coordinate": "2q-1",
        "shipping_coordinates": 96,
        "shipping_atomic_elements": 192,
    },
}

NOTES: str = (
    "Section 2 fixes Consensus-Halving on an interval, permits step-function "
    "densities, defines cuts and +/- labels, and defines exact and epsilon "
    "balance. Section 3, Theorems 1 and 2 prove PPAD-hardness for constant-error "
    "instances with n or n+k cuts, but that worst-case result is not claimed for "
    "this inverse-generated distribution. Section 5 gives PPA membership through "
    "Tucker/Leaf, while Section 1 explains that the Simmons-Su triangulation "
    "protocol is worst-case exponential. The slot promise here instead exposes "
    "a polynomial exact linear system, so this is explicitly Track B. Plants and "
    "random candidates use the same rational grid; guard indices, exceptional "
    "slots, and agent rows are independently permuted. The adversary panel tests "
    "local-row, direct-target, one-pass greedy, common-offset, and random-restart "
    "shortcuts; the disclosed reference algorithm is dense exact elimination."
)


# Filled only from script-owned hardening runs. Until those runs happen, G9 is
# intentionally not a passing gate.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
}

HARDENING_STATUS = {
    "verdict": "cap_bound",
    "max_attempted_params": {"n": 96, "q": 16847121},
    "max_attempted_solved": 1,
    "max_attempted_attempts": 3,
    "max_attempted_answer_chars": 1876,
    "next_params": {"n": 96, "q": 269553937},
    "next_answer_chars_sampled_max": 2138,
    "reason": (
        "One oracle still solved the largest in-cap fixed-length grid; the next "
        "grid escalation exceeds the 2000-character answer cap."
    ),
}


def _rat(value: Fraction | int) -> list[int]:
    if rationals is not None:
        return rationals.to_json(value)
    value = value if isinstance(value, Fraction) else Fraction(value)
    return [value.numerator, value.denominator]


def _frac(value) -> Fraction:
    if rationals is not None:
        return rationals.from_json(value)
    if isinstance(value, bool):
        raise TypeError("boolean is not a rational")
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or not all(isinstance(x, int) and not isinstance(x, bool) for x in value)
        or value[1] == 0
    ):
        raise ValueError("expected [numerator, denominator]")
    return Fraction(value[0], value[1])


def _ftext(value) -> str:
    f = _frac(value) if isinstance(value, (list, tuple)) else Fraction(value)
    return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


def _sample_distinct_coordinates(n: int, q: int, rng: random.Random) -> list[int]:
    population = range(-q + 1, q)
    # Distinct planted coordinates make swap/duplication tests deterministic.
    # The certificate language itself still permits repeats.
    for _ in range(1000):
        values = rng.sample(population, n)
        total = sum(values)
        if total != 0 and all(total + value != 0 for value in values):
            return values
    raise RuntimeError("could not sample nondegenerate cut coordinates")


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate an exact promised-slot Consensus-Halving instance."""
    if "q" not in params:
        raise ValueError("q is required")
    q = params.pop("q")
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(q, bool) or not isinstance(q, int) or q < 2:
        raise ValueError("q must be an integer at least 2")
    if n >= 2 * q - 1:
        raise ValueError("n must be smaller than the 2q-1 available grid coordinates")

    rng = random.Random(seed)
    planted_nums = _sample_distinct_coordinates(n, q, rng)
    common_num = sum(planted_nums)

    exceptional_slots = list(range(n))
    guard_indices = list(range(n))
    rng.shuffle(exceptional_slots)
    rng.shuffle(guard_indices)

    # With z_j=a_j/q and S=sum(z), an agent whose exceptional slot is s has
    # slot discrepancy S+z_s. Its guards contribute exactly the negative.
    base = Fraction(2 * n + 3)
    agents = []
    for exceptional, guard in zip(exceptional_slots, guard_indices):
        target = Fraction(common_num + planted_nums[exceptional], q)
        left = base
        right = base + (target if guard % 2 == 0 else -target)
        if right < 0:
            raise AssertionError("negative guard density")
        agents.append(
            {
                "guard": guard,
                "exceptional_slot": exceptional,
                "left_density": _rat(left),
                "right_density": _rat(right),
                "slot_density": _rat(1),
            }
        )
    rng.shuffle(agents)

    return {
        "family": "exact promised-slot consensus-halving",
        "n": n,
        "q": q,
        "length": 3 * n,
        "agents": agents,
        "answer": [_rat(Fraction(a, q)) for a in planted_nums],
    }


def _answer_text(answer) -> str:
    return ", ".join(_ftext(value) for value in answer)


def render(inst) -> str:
    n, q = inst["n"], inst["q"]
    rows = []
    for i, agent in enumerate(inst["agents"], 1):
        rows.append(
            f"A{i}: guard={agent['guard']}; special={agent['exceptional_slot']}; "
            f"L={_ftext(agent['left_density'])}; "
            f"R={_ftext(agent['right_density'])}; "
            f"C={_ftext(agent['slot_density'])}"
        )

    statement = f"""EXACT PROMISED-SLOT CONSENSUS-HALVING

The divisible object is the closed interval [0,{inst['length']}]. There are
n={n} agents. A density is constant on every interval specified below and zero
elsewhere. An agent's value for a portion is the exact integral of that density
over the portion. Endpoints have measure zero.

Your answer is a vector z_0,...,z_{n-1} of exactly {n} rational normalized cut
coordinates. For every j=0,...,{n-1}, require -1<z_j<1 and q*z_j to be an
integer, where q={q}. Repeated z_j values are allowed. Coordinate z_j specifies
the cut

    t_j = 3j + 3/2 + (-1)^j*z_j/2.

Thus t_j lies strictly inside its designated open slot (3j+1,3j+2), and the
cuts are automatically strictly increasing. Label [0,t_0] with + and alternate
the labels at every cut. A valid answer makes every agent's exact total value
on the + portion equal its exact total value on the - portion.

An agent row "guard=g; special=s; L; R; C" defines its entire density:

  * density L on [3g,3g+1] and density R on [3g+2,3g+3];
  * density C on every slot [3j+1,3j+2], for all j=0,...,{n-1};
  * one additional density C on slot s, so its total density there is 2C;
  * density zero on all other intervals.

All indices are zero-based. Agent rows can appear in any order. Here is the
complete instance:

{chr(10).join(rows)}

Give your final answer inside <answer></answer> tags, as exactly {n}
comma-separated rational numbers num/den in z_0,...,z_{n-1} order. Integers are
also accepted as denominator-1 rationals; denominators must be nonzero. Do not
put brackets in the tags.
Example format for a two-coordinate answer: <answer>-1/3, 2/3</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the last tagged comma-separated exact rational vector."""
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text), re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        for fence in ("~~~", chr(96) * 3):
            if body.startswith(fence) and body.endswith(fence):
                body = re.sub(r"^" + re.escape(fence) + r"[^\n]*\n?", "", body)
                body = re.sub(r"\n?" + re.escape(fence) + r"$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        tokens = [token.strip() for token in body.split(",")]
        out = []
        for token in tokens:
            match = re.fullmatch(r"([+-]?\d+)(?:\s*/\s*([+-]?\d+))?", token)
            if not match:
                return None
            numerator = int(match.group(1))
            denominator = int(match.group(2) or 1)
            if denominator == 0:
                return None
            out.append(_rat(Fraction(numerator, denominator)))
        return out
    except Exception:
        return None


def _validated_coordinates(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be a list of rational coordinates"
    if not answer:
        return None, "answer is empty"
    n, q = inst["n"], inst["q"]
    if len(answer) != n:
        return None, f"wrong number of coordinates: expected {n}"
    # Return the integer grid numerators a_j=q*z_j.  Staying in integers here
    # makes the 200k-candidate density audit cheap without weakening exactness.
    grid_numerators = []
    for j, raw in enumerate(answer):
        if (
            not isinstance(raw, (list, tuple))
            or len(raw) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in raw)
            or raw[1] == 0
        ):
            return None, f"coordinate {j} is not a valid rational"
        numerator, denominator = raw
        if denominator < 0:
            numerator, denominator = -numerator, -denominator
        if not (-denominator < numerator < denominator):
            return None, f"coordinate {j} is outside the open interval (-1,1)"
        scaled = q * numerator
        if scaled % denominator:
            return None, f"coordinate {j} is off the required 1/q grid"
        grid_numerators.append(scaled // denominator)
    return grid_numerators, "ok"


def _agent_discrepancy(agent, common_num: int, grid_numerators, q: int) -> Fraction:
    """Exact plus-value minus minus-value integral for one agent."""
    guard = agent["guard"]
    left = _frac(agent["left_density"])
    right = _frac(agent["right_density"])
    scale = _frac(agent["slot_density"])
    guard_part = (left - right) if guard % 2 == 0 else (right - left)
    slot_part = scale * Fraction(
        common_num + grid_numerators[agent["exceptional_slot"]], q
    )
    return guard_part + slot_part


def verify(inst, answer) -> tuple[bool, str]:
    """Check a proposed partition by exact rational interval integration."""
    grid_numerators, reason = _validated_coordinates(inst, answer)
    if grid_numerators is None:
        return False, reason
    common_num = sum(grid_numerators)
    for i, agent in enumerate(inst["agents"], 1):
        discrepancy = _agent_discrepancy(
            agent, common_num, grid_numerators, inst["q"]
        )
        if discrepancy:
            return (
                False,
                f"agent {i} is not balanced (exact discrepancy "
                f"{_ftext(discrepancy)})",
            )
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample every statement-visible grid/range constraint."""
    q = inst["q"]
    return [_rat(Fraction(rng.randrange(-q + 1, q), q)) for _ in range(inst["n"])]


def search_space(inst) -> int | None:
    return (2 * inst["q"] - 1) ** inst["n"]


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space > 200_000:
        return None
    q, n = inst["q"], inst["n"]
    count = 0
    for nums in itertools.product(range(-q + 1, q), repeat=n):
        candidate = [_rat(Fraction(a, q)) for a in nums]
        count += int(verify(inst, candidate)[0])
    return count


def _primitive_agent(agent):
    values = [
        _frac(agent["left_density"]),
        _frac(agent["right_density"]),
        _frac(agent["slot_density"]),
    ]
    common_den = 1
    for value in values:
        common_den = math.lcm(common_den, value.denominator)
    integers = [
        value.numerator * (common_den // value.denominator) for value in values
    ]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    if divisor:
        integers = [value // divisor for value in integers]
    if next((value for value in integers if value), 1) < 0:
        integers = [-value for value in integers]
    return integers


def _canonical_payload(inst, reflected=False):
    n = inst["n"]
    rows = []
    for agent in inst["agents"]:
        left, right, scale = _primitive_agent(agent)
        guard = agent["guard"]
        exceptional = agent["exceptional_slot"]
        if reflected:
            guard = n - 1 - guard
            exceptional = n - 1 - exceptional
            left, right = right, left
        rows.append((guard, exceptional, left, right, scale))
    rows.sort()
    return n, inst["q"], tuple(rows)


def canonical_key(inst) -> str:
    """Canonicalize agent order, positive row scaling, and global reflection."""
    payload = min(_canonical_payload(inst, False), _canonical_payload(inst, True))
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _scaled_instance(inst, rng):
    out = json.loads(json.dumps(inst))
    for agent in out["agents"]:
        factor = Fraction(rng.randrange(1, 9), rng.randrange(1, 9))
        for key in ("left_density", "right_density", "slot_density"):
            agent[key] = _rat(_frac(agent[key]) * factor)
    rng.shuffle(out["agents"])
    return out


def _reflected_instance(inst):
    out = json.loads(json.dumps(inst))
    n = out["n"]
    for agent in out["agents"]:
        agent["guard"] = n - 1 - agent["guard"]
        agent["exceptional_slot"] = n - 1 - agent["exceptional_slot"]
        agent["left_density"], agent["right_density"] = (
            agent["right_density"],
            agent["left_density"],
        )
    return out


def _reflected_answer(inst, answer):
    sign = 1 if inst["n"] % 2 == 0 else -1
    return [_rat(sign * _frac(value)) for value in reversed(answer)]


def _linear_system(inst):
    n = inst["n"]
    matrix, rhs = [], []
    for agent in inst["agents"]:
        scale = _frac(agent["slot_density"])
        row = [scale for _ in range(n)]
        row[agent["exceptional_slot"]] += scale
        matrix.append(row)
        guard = agent["guard"]
        left = _frac(agent["left_density"])
        right = _frac(agent["right_density"])
        guard_part = (left - right) if guard % 2 == 0 else (right - left)
        rhs.append(-guard_part)
    return matrix, rhs


def _gauss_jordan_solve(matrix, rhs):
    """Dense exact solve, returning solution and counted field operations."""
    n = len(matrix)
    augmented = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    operations = 0
    for col in range(n):
        pivot = next((row for row in range(col, n) if augmented[row][col]), None)
        if pivot is None:
            raise ValueError("singular balance system")
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        if pivot_value != 1:
            for k in range(col, n + 1):
                augmented[col][k] /= pivot_value
                operations += 1
        for row in range(n):
            if row == col or not augmented[row][col]:
                continue
            factor = augmented[row][col]
            for k in range(col, n + 1):
                augmented[row][k] -= factor * augmented[col][k]
                operations += 2
    return [augmented[i][n] for i in range(n)], operations


def _reference_algorithm(inst):
    matrix, rhs = _linear_system(inst)
    solution, operations = _gauss_jordan_solve(matrix, rhs)
    return [_rat(value) for value in solution], operations


def _target(agent) -> Fraction:
    guard = agent["guard"]
    left = _frac(agent["left_density"])
    right = _frac(agent["right_density"])
    scale = _frac(agent["slot_density"])
    return ((right - left) if guard % 2 == 0 else (left - right)) / scale


def _nearest_grid(value: Fraction, q: int) -> Fraction:
    scaled = value * q
    numerator = scaled.numerator
    denominator = scaled.denominator
    integer = (2 * numerator + denominator) // (2 * denominator)
    integer = max(-q + 1, min(q - 1, integer))
    return Fraction(integer, q)


def _candidate_from_specials(inst, values_by_special):
    return [_rat(values_by_special[j]) for j in range(inst["n"])]


def _attack_local_exception_only(inst, rng=None):
    del rng
    q = inst["q"]
    values = [Fraction() for _ in range(inst["n"])]
    for agent in inst["agents"]:
        values[agent["exceptional_slot"]] = _nearest_grid(_target(agent) / 2, q)
    return _candidate_from_specials(inst, values), inst["n"]


def _attack_direct_target(inst, rng=None):
    del rng
    q = inst["q"]
    values = [Fraction() for _ in range(inst["n"])]
    for agent in inst["agents"]:
        values[agent["exceptional_slot"]] = _nearest_grid(_target(agent), q)
    return _candidate_from_specials(inst, values), inst["n"]


def _attack_greedy_one_pass(inst, rng=None):
    del rng
    q, n = inst["q"], inst["n"]
    values = [Fraction() for _ in range(n)]
    common = Fraction()
    for agent in inst["agents"]:
        special = agent["exceptional_slot"]
        residual = _target(agent) - (common + values[special])
        updated = _nearest_grid(values[special] + residual / 2, q)
        common += updated - values[special]
        values[special] = updated
    return _candidate_from_specials(inst, values), n


def _attack_common_offset(inst, rng=None):
    del rng
    q, n = inst["q"], inst["n"]
    for attempt, agent in enumerate(inst["agents"], 1):
        value = _nearest_grid(_target(agent) / (n + 1), q)
        candidate = [_rat(value) for _ in range(n)]
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, n


def _attack_random_restart(inst, rng, restarts=512):
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _intended_operations(n: int) -> int:
    # n signed target subtractions, n-1 additions, one division, n recoveries.
    return 3 * n


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def escalate(params) -> dict | str | None:
    """Grow grid entropy/operand size after reaching a 96-coordinate witness."""
    n, q = int(params["n"]), int(params["q"])
    if n < 96:
        harder_n = min(96, 2 * n)
        return {"n": harder_n, "q": max(q, (harder_n + 2) // 2)}
    if len(str(q)) >= 8:
        return "cap_bound"
    return {"n": n, "q": 16 * q + 1}


def selftest() -> dict:
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "hardening_status": HARDENING_STATUS,
    }

    planted = json_round_trips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {reason}")
            planted += 1
            json_round_trips += int(
                json.loads(json.dumps(inst["answer"])) == inst["answer"]
            )
    report["G1_planted_verifies"] = {
        "pass": planted == 12 and json_round_trips == 12,
        "verified": planted,
        "json_round_trips": json_round_trips,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    answer = json.loads(json.dumps(inst["answer"]))
    variants = {
        "drop": answer[:-1],
        "swap": [answer[1], answer[0]] + answer[2:],
        "duplicate": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": [[2, 1]] + answer[1:],
    }
    corruptions, reasons = {}, []
    for name, candidate in variants.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": corruptions,
    }

    response = (
        "I used exact rational balance equations.\n<answer>"
        + chr(96) * 3
        + "text\n"
        + _answer_text(answer)
        + "\n"
        + chr(96) * 3
        + "</answer>\nThese are the normalized cut coordinates."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_coordinates": len(parsed) if isinstance(parsed, list) else 0,
    }

    samples = 200_000
    guess_rng = random.Random(9141609)
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "probability": hits / samples,
        "structure_aware_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    attacks = {
        "outlier_local_exception_only": _attack_local_exception_only,
        "direct_target_without_background": _attack_direct_target,
        "greedy_one_pass": _attack_greedy_one_pass,
        "common_offset_ansatz": _attack_common_offset,
        "random_restart_512": _attack_random_restart,
    }
    attack_results = {
        name: {"successes": 0, "attempts": 8} for name in attacks
    }
    attack_seconds = {name: [] for name in attacks}
    attack_iterations = {name: [] for name in attacks}
    reference_seconds, reference_operations = [], []
    reference_successes = 0
    for seed in range(8):
        trial = make_instance(seed=7000 + seed, **shipping_params)
        for name, attack in attacks.items():
            rng = random.Random(800000 + 97 * seed)
            start = time.perf_counter()
            candidate, iterations = attack(trial, rng)
            elapsed = time.perf_counter() - start
            won = candidate is not None and verify(trial, candidate)[0]
            attack_results[name]["successes"] += int(won)
            attack_seconds[name].append(elapsed)
            attack_iterations[name].append(iterations)
        start = time.perf_counter()
        reference, operations = _reference_algorithm(trial)
        reference_seconds.append(time.perf_counter() - start)
        reference_operations.append(operations)
        reference_successes += int(verify(trial, reference)[0])

    for name in attacks:
        attack_results[name]["median_wall_clock_sec"] = round(
            statistics.median(attack_seconds[name]), 6
        )
        attack_results[name]["median_iterations"] = statistics.median(
            attack_iterations[name]
        )

    strongest = max(
        attacks, key=lambda name: statistics.median(attack_seconds[name])
    )
    baseline_seconds = statistics.median(attack_seconds[strongest])
    baseline_iterations = statistics.median(attack_iterations[strongest])
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits / samples < 1e-6 and baseline_seconds >= 0,
        "shipping_solution_hits": hits,
        "shipping_density_samples": samples,
        "shipping_sampled_density": hits / samples,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "strongest_failing_attack": strongest,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "baseline_iterations": baseline_iterations,
    }

    report["G6_adversary_panel"] = {
        "pass": all(
            item["successes"] == 0 and item["attempts"] >= 8
            for item in attack_results.values()
        )
        and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "dense exact Gauss-Jordan elimination",
            "complexity": "O(n^3) rational field operations",
            "wall_clock_sec": round(statistics.median(reference_seconds), 6),
            "operations": int(statistics.median(reference_operations)),
            "successes": reference_successes,
            "attempts": 8,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * shipping_params["n"], q=shipping_params["q"], seed=12345
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "shipping_space_bits": round(math.log2(search_space(inst)), 3),
        "doubled_space_bits": round(math.log2(search_space(doubled)), 3),
    }

    invariant = carried = 0
    for seed in range(20):
        base = make_instance(seed=9000 + seed, **shipping_params)
        key = canonical_key(base)
        reordered = json.loads(json.dumps(base))
        reordered["agents"] = list(reversed(reordered["agents"]))
        scaled = _scaled_instance(base, random.Random(seed))
        reflected = _reflected_instance(base)
        reflected_answer = _reflected_answer(base, base["answer"])
        reflected_scaled = _scaled_instance(reflected, random.Random(100 + seed))
        transforms = [
            (reordered, base["answer"]),
            (scaled, base["answer"]),
            (reflected, reflected_answer),
            (reflected_scaled, reflected_answer),
        ]
        for transformed, carried_answer in transforms:
            invariant += int(canonical_key(transformed) == key)
            carried += int(verify(transformed, carried_answer)[0])
    distinct_keys = {
        canonical_key(make_instance(seed=12000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 80 and carried == 80 and len(distinct_keys) == 20,
        "invariance_checks": invariant,
        "invariance_total": 80,
        "carried_witness_checks": carried,
        "carried_witness_total": 80,
        "distinct_unrelated_keys": len(distinct_keys),
        "distinctness_total": 20,
        "symmetries": [
            "agent reorder",
            "positive per-agent scaling",
            "global interval reflection",
            "reflection composed with scaling",
        ],
    }

    answer_chars = max(
        len(
            json.dumps(
                make_instance(seed=seed, **shipping_params)["answer"],
                separators=(",", ":"),
            )
        )
        for seed in range(1000)
    )
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = _intended_operations(inst["n"])
    arms = G9_RESULTS["arms"]
    hinted_still_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
