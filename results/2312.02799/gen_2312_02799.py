"""Verified generator for common-time recovery in toroidal Conway Life.

The family is based on the toroidal Life searches in Section 2.2 and the
independent-period composition principle in Section 2.4 of Brown et al.,
"Conway's Game of Life is Omniperiodic" (arXiv:2312.02799).  A time is sampled
first.  Several independently framed five-cell Life configurations are then
advanced to that time by an exact four-phase identity.  Generation therefore
does not solve the emitted instance.

Everything used by the public interface is standard-library-only.  ``gvlib``
is imported when available to follow the repository convention, but this
finite cellular-automaton family does not need its algebra helpers.
"""

from __future__ import annotations

import functools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "dynamics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite toroidal Conway Life configurations",
        "pairs of exact Life snapshots",
        "a common integer evolution time and its boardwise residues",
    ],
    "verification_operations": [
        "exact B3/S23 evolution of a five-cell toroidal configuration",
        "exact modular arithmetic",
        "finite set comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The five-cell state has a four-generation shape cycle accompanied by "
        "one diagonal cell of translation, so each board yields a time "
        "congruence; without noticing this, one must simulate every torus."
    ),
    "hardness_basis": (
        "Track B: sparse hash-map B3/S23 orbit simulation followed by CRT is "
        "O(sum q_i) generations for these constant-population boards; at the "
        "shipping preset the measured eight-seed mean is recorded by selftest "
        "(roughly one million exact neighbor/update operations), whereas the "
        "four-phase translation invariant leaves at most 200 coordinate and "
        "CRT operations but must first be recognized without a simulator."
    ),
    # A conservative one-character-per-token bound; the measured value is in G9.
    "max_answer_tokens": 180,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON object {time: T, residues: [r_0,...,r_(n-1)]}, where "
        "0 <= T < L and r_i is the uniquely determined residue T mod (4q_i) "
        "for board i in the displayed order."
    ),
    "bounds": {
        "time_min": 0,
        "time_max": "L-1, where L is displayed in the instance",
        "residue_count": "n",
        "residue_i": "0 <= r_i < 4q_i and r_i = time mod 4q_i",
        "atomic_elements": "n+1",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 1, "q_min": 11, "q_span": 20},
    "easy": {"n": 5, "q_min": 101, "q_span": 100},
    "medium": {"n": 6, "q_min": 251, "q_span": 180},
    "hard": {"n": 8, "q_min": 1009, "q_span": 500},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Each five-cell component has a four-generation shape cycle accompanied "
    "by one cell of diagonal translation."
)
PLACEBO_HINT = (
    "Each finite component should be read with wraparound coordinates and all "
    "five live cells tracked consistently."
)

# Filled from script-owned oracle runs.  These are diagnostics; G9(c), not an
# oracle outcome, is the gate.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper triage.  Section 1 fixes the exact synchronous B3/S23 rule and
distinguishes stationary oscillators from translating spaceships.  Section 2
restricts the omniperiodicity theorem to finite plane oscillators, because an
infinite regularly spaced glider stream gives an easy construction for every
period at least 14.  Section 2.2 explicitly describes finite wraparound tori as
the universes used by early soup searches.  Section 2.4 supplies the independent
composition identity: noninteracting periodic components have joint period the
least common multiple of their periods.  Those are the native objects used
here; there is no graph or finite-field surrogate.

The easy regimes mattered at STEP 0.  Section 2.3 says direct finite-grid
brute force is quickly infeasible but describes cell-by-cell depth-first
constraint search.  Section 2.5.2 gives an explicit construction for every
period p >= 43, and Section 2.7 says a bounded oscillator question can be sent
to a SAT solver.  Consequently, asking for an oscillator of a supplied period
would not support Track A.  This module instead declares Track B openly: exact
orbit simulation and CRT solve every instance, and selftest measures their
cost.

Construction.  Distinct odd prime torus sizes q_i are sampled.  A common time
T is sampled uniformly from [0, 4*product(q_i)).  The canonical five-cell
configuration is advanced using the identity that four Life generations move
it one diagonal cell.  Independent dihedral coordinate changes and translations
hide that identity on every board.  The target snapshots and certificate are
then direct images of the sampled T.  No search for T occurs during generation.

Attack handling.  Coordinate frames and board order are independently random,
so raw extrema and a southeast-only displacement formula do not reveal T.
Using only the first board returns merely one residue, and random restart draws
from the full structure-aware time interval.  The fourth, genuinely in-context
attack performs a phase-blind CRT on lexicographic anchors; it fails because
phase and dihedral direction both matter.  The successful sparse Life simulator
is reported separately as the required Track B reference algorithm.
""".strip()


# ---------------------------------------------------------------------------
# Exact Life mechanics and the four-phase identity


Cell = tuple[int, int]
State = frozenset[Cell]

_NEIGHBORS = tuple(
    (dx, dy)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    if (dx, dy) != (0, 0)
)

# RLE bo$2bo$3o!, in zero-based Cartesian coordinates with y increasing down.
_GLIDER0: State = frozenset({(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)})


def _step_infinite(live: State) -> State:
    counts: dict[Cell, int] = {}
    for x, y in live:
        for dx, dy in _NEIGHBORS:
            c = (x + dx, y + dy)
            counts[c] = counts.get(c, 0) + 1
    return frozenset(
        cell for cell, count in counts.items()
        if count == 3 or (count == 2 and cell in live)
    )


def _make_glider_phases() -> tuple[State, State, State, State]:
    phases = [_GLIDER0]
    for _ in range(3):
        phases.append(_step_infinite(phases[-1]))
    fourth = _step_infinite(phases[-1])
    shifted = frozenset((x + 1, y + 1) for x, y in _GLIDER0)
    if fourth != shifted:            # import-time assertion, no output or I/O
        raise AssertionError("internal Life phase table is inconsistent")
    return tuple(phases)             # type: ignore[return-value]


_GLIDER_PHASES = _make_glider_phases()

# The eight isometries of the square grid.  Each preserves the toroidal Moore
# neighbourhood and therefore commutes with a Life step.
_D4 = (
    (1, 0, 0, 1),
    (0, -1, 1, 0),
    (-1, 0, 0, -1),
    (0, 1, -1, 0),
    (-1, 0, 0, 1),
    (1, 0, 0, -1),
    (0, 1, 1, 0),
    (0, -1, -1, 0),
)


def _linear(cell: Cell, transform: int) -> Cell:
    x, y = cell
    a, b, c, d = _D4[transform]
    return a * x + b * y, c * x + d * y


def _place(state: State, q: int, transform: int,
           shift: Cell = (0, 0)) -> State:
    sx, sy = shift
    return frozenset(
        ((u + sx) % q, (v + sy) % q)
        for u, v in (_linear(cell, transform) for cell in state)
    )


def _advance_canonical(residue: int) -> State:
    phase = residue % 4
    turns = residue // 4
    return frozenset(
        (x + turns, y + turns) for x, y in _GLIDER_PHASES[phase]
    )


def _step_torus(live: State, q: int) -> tuple[State, int]:
    """One exact sparse Life step and an elementary-operation count."""
    counts: dict[Cell, int] = {}
    operations = 0
    for x, y in live:
        for dx, dy in _NEIGHBORS:
            c = ((x + dx) % q, (y + dy) % q)
            counts[c] = counts.get(c, 0) + 1
            operations += 1          # one neighbor-count update
    out = set()
    for cell, count in counts.items():
        operations += 1              # one B3/S23 membership/rule decision
        if count == 3 or (count == 2 and cell in live):
            out.add(cell)
    return frozenset(out), operations


def _state_from_json(value: object, q: int) -> State | None:
    if not isinstance(value, list) or len(value) != 5:
        return None
    out = []
    for cell in value:
        if (not isinstance(cell, list) or len(cell) != 2
                or any(isinstance(z, bool) or not isinstance(z, int)
                       for z in cell)):
            return None
        x, y = cell
        if not (0 <= x < q and 0 <= y < q):
            return None
        out.append((x, y))
    if len(set(out)) != 5:
        return None
    return frozenset(out)


@functools.lru_cache(maxsize=4096)
def _frames_for_start(q: int, start_key: tuple[Cell, ...]) -> tuple[tuple[int, Cell], ...]:
    """All (D4 map, translation) frames carrying phase zero to start."""
    start = frozenset(start_key)
    frames = []
    anchor = next(iter(_GLIDER0))
    for transform in range(8):
        ax, ay = _linear(anchor, transform)
        for tx, ty in start:
            shift = ((tx - ax) % q, (ty - ay) % q)
            if _place(_GLIDER0, q, transform, shift) == start:
                frames.append((transform, shift))
    return tuple(frames)


def _formula_matches(start: State, target: State, q: int, residue: int) -> bool:
    frames = _frames_for_start(q, tuple(sorted(start)))
    if not frames:
        return False
    advanced = _advance_canonical(residue)
    return any(
        _place(advanced, q, transform, shift) == target
        for transform, shift in frames
    )


# ---------------------------------------------------------------------------
# Construction and public interface


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    d = 3
    while d * d <= value:
        if value % d == 0:
            return False
        d += 2
    return True


def _validate_params(n: int, q_min: int, q_span: int) -> None:
    for name, value in (("n", n), ("q_min", q_min), ("q_span", q_span)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 1:
        raise ValueError("n must be positive")
    if q_min < 7:
        raise ValueError("q_min must be at least 7")
    if q_span < 1:
        raise ValueError("q_span must be positive")


def make_instance(n: int, seed: int = 0, q_min: int = 101,
                  q_span: int = 100, **params) -> dict:
    """Inverse-generate a common-time instance; never solve the emitted data."""
    if params:
        unknown = ", ".join(sorted(params))
        raise ValueError(f"unknown parameter(s): {unknown}")
    _validate_params(n, q_min, q_span)
    rng = random.Random(seed)
    primes = [q for q in range(q_min, q_min + q_span + 1)
              if q % 2 == 1 and _is_prime(q)]
    if len(primes) < n:
        raise ValueError("q interval contains fewer than n odd primes")
    moduli = rng.sample(primes, n)
    horizon = 4 * math.prod(moduli)

    # The answer is selected before either target snapshot is assembled.
    hidden_time = rng.randrange(horizon)
    boards = []
    for q in moduli:
        transform = rng.randrange(8)
        shift = (rng.randrange(q), rng.randrange(q))
        residue = hidden_time % (4 * q)
        start = _place(_GLIDER0, q, transform, shift)
        target = _place(_advance_canonical(residue), q, transform, shift)
        start_list = [list(cell) for cell in start]
        target_list = [list(cell) for cell in target]
        rng.shuffle(start_list)
        rng.shuffle(target_list)
        boards.append({"q": q, "start": start_list, "target": target_list})
    rng.shuffle(boards)
    residues = [hidden_time % (4 * board["q"]) for board in boards]
    answer = {"time": hidden_time, "residues": residues}
    return {
        "n": n,
        "q_min": q_min,
        "q_span": q_span,
        "rule": "B3/S23",
        "horizon": horizon,
        "boards": boards,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete self-contained problem statement."""
    lines = [
        "COMMON-TIME RECOVERY IN TOROIDAL CONWAY LIFE",
        "",
        "A q by q toroidal board has coordinates (x,y) with 0 <= x,y < q.",
        "Coordinates wrap modulo q in both directions.  The eight neighbours of",
        "(x,y) are (x+dx,y+dy) for dx,dy in {-1,0,1}, excluding (0,0),",
        "with both coordinates reduced modulo q.",
        "",
        "All cells update simultaneously by Conway's B3/S23 rule:",
        "- a dead cell becomes live exactly when it has three live neighbours;",
        "- a live cell remains live exactly when it has two or three live",
        "  neighbours, and otherwise becomes dead.",
        "",
        f"There are {len(inst['boards'])} independent boards.  On every board,",
        "START lists all five live cells at time 0 and TARGET lists all live",
        "cells after the same unknown nonnegative integer number T of updates.",
        "The order of coordinate pairs inside a list has no significance and",
        "no coordinate is repeated.  It is promised that exactly one T in",
        f"the inclusive range 0 <= T < L={inst['horizon']} works on every board.",
        "",
        "For each board i in the displayed 0-based order, also report",
        "r_i = T mod (4*q_i), using the least nonnegative residue.",
        "",
        "INSTANCE DATA",
    ]
    for i, board in enumerate(inst["boards"]):
        lines.append(f"board {i}: q={board['q']}")
        lines.append("  START  " + json.dumps(board["start"], separators=(",", ":")))
        lines.append("  TARGET " + json.dumps(board["target"], separators=(",", ":")))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object",
        'with exactly the keys "time" and "residues".  "time" is T, and',
        f'"residues" is a list of exactly {len(inst["boards"])} integers in board order.',
        "Integers are decimal; endpoints are inclusive at 0 and exclusive at",
        "their displayed upper bounds.  Do not put prose inside the tags.",
        "Example of format only:",
        "<answer>"
        + json.dumps({"time": 17, "residues": [17] * len(inst["boards"])},
                     separators=(",", ":"))
        + "</answer>",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON answer, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, dict) or set(answer) != {"time", "residues"}:
        return None
    if isinstance(answer["time"], bool) or not isinstance(answer["time"], int):
        return None
    residues = answer["residues"]
    if not isinstance(residues, list):
        return None
    if any(isinstance(r, bool) or not isinstance(r, int) for r in residues):
        return None
    return answer


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any certificate from instance data only; never inspect answer key."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object is empty"
    if set(answer) != {"time", "residues"}:
        return False, "answer must contain exactly time and residues"
    value = answer["time"]
    residues = answer["residues"]
    if isinstance(value, bool) or not isinstance(value, int):
        return False, "time must be an integer"
    if not (0 <= value < inst["horizon"]):
        return False, "time is outside the stated half-open range"
    if not isinstance(residues, list):
        return False, "residues must be a list"
    nboards = len(inst["boards"])
    if len(residues) == 0:
        return False, "residue list is empty"
    if len(residues) == nboards - 1:
        return False, "one residue is missing"
    if len(residues) == nboards + 1 and residues[-1] in residues[:-1]:
        return False, "residue list contains a duplicate entry"
    if len(residues) != nboards:
        return False, f"residues must have length {nboards}"
    if any(isinstance(r, bool) or not isinstance(r, int) for r in residues):
        return False, "every residue must be an integer"
    expected = [value % (4 * board["q"]) for board in inst["boards"]]
    if residues != expected:
        if sorted(residues) == sorted(expected):
            return False, "residues are not in displayed board order"
        for i, (got, want, board) in enumerate(zip(residues, expected, inst["boards"])):
            if not (0 <= got < 4 * board["q"]):
                return False, f"residue {i} is outside its board range"
            if got != want:
                return False, f"residue {i} is inconsistent with time"
    for i, (board, residue) in enumerate(zip(inst["boards"], residues)):
        q = board.get("q")
        if isinstance(q, bool) or not isinstance(q, int) or q < 7:
            return False, f"board {i} has an invalid size"
        start = _state_from_json(board.get("start"), q)
        target = _state_from_json(board.get("target"), q)
        if start is None:
            return False, f"board {i} has a malformed START state"
        if target is None:
            return False, f"board {i} has a malformed TARGET state"
        if not _formula_matches(start, target, q, residue):
            return False, f"board {i} does not evolve from START to TARGET"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact bounded language after free constraints."""
    value = rng.randrange(inst["horizon"])
    return {
        "time": value,
        "residues": [value % (4 * board["q"]) for board in inst["boards"]],
    }


def search_space(inst: dict) -> int:
    """One structure-aware certificate exists for every allowed time."""
    return inst["horizon"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact valid count only for genuinely small horizons."""
    if inst["horizon"] > 10_000:
        return None
    return sum(
        1 for value in range(inst["horizon"])
        if verify(inst, {
            "time": value,
            "residues": [value % (4 * board["q"]) for board in inst["boards"]],
        })[0]
    )


# ---------------------------------------------------------------------------
# Canonicalization under all stated relabellings


def _canonical_board(board: dict) -> tuple:
    q = board["q"]
    start = _state_from_json(board["start"], q)
    target = _state_from_json(board["target"], q)
    if start is None or target is None:
        return (q, "malformed", json.dumps(board, sort_keys=True, separators=(",", ":")))
    forms = []
    for transform in range(8):
        s0 = {_linear(cell, transform) for cell in start}
        t0 = {_linear(cell, transform) for cell in target}
        for ax, ay in s0:
            s = tuple(sorted(((x - ax) % q, (y - ay) % q) for x, y in s0))
            t = tuple(sorted(((x - ax) % q, (y - ay) % q) for x, y in t0))
            forms.append((s, t))
    return (q, min(forms))


def canonical_key(inst: dict) -> str:
    """Invariant under board/cell order, torus translation, and D4 relabelling."""
    boards = sorted(_canonical_board(board) for board in inst["boards"])
    return json.dumps(boards, separators=(",", ":"))


def escalate(params: dict) -> dict | str | None:
    """Enlarge every torus at fixed witness length and fixed CRT operation count."""
    n = params.get("n")
    q_min = params.get("q_min")
    q_span = params.get("q_span")
    if any(isinstance(x, bool) or not isinstance(x, int)
           for x in (n, q_min, q_span)):
        return None
    if q_min >= 1_000_000:
        return "cap_bound"
    return {
        "n": n,
        "q_min": 2 * q_min + 1,
        "q_span": 2 * q_span,
    }


# ---------------------------------------------------------------------------
# Track-B reference algorithm and construction-aware adversaries


def _crt_coprime(residues: list[int], moduli: list[int]) -> tuple[int, int]:
    x = 0
    modulus = 1
    operations = 0
    for residue, q in zip(residues, moduli):
        delta = (residue - x) % q
        inv = pow(modulus, -1, q)
        step = (delta * inv) % q
        x += modulus * step
        modulus *= q
        operations += 7
    return x, operations


def _find_residue_by_simulation(board: dict) -> tuple[int | None, int, int]:
    q = board["q"]
    start = _state_from_json(board["start"], q)
    target = _state_from_json(board["target"], q)
    if start is None or target is None:
        return None, 0, 0
    live = start
    operations = 1
    if live == target:
        return 0, operations, 0
    for generation in range(1, 4 * q + 1):
        live, step_operations = _step_torus(live, q)
        operations += step_operations + 1
        if live == target:
            return generation, operations, generation
    return None, operations, 4 * q


def _reference_algorithm(inst: dict) -> dict:
    """Mechanical exact Life simulation on each board, followed by CRT."""
    start_clock = time.perf_counter()
    residues = []
    operations = 0
    generations = 0
    for board in inst["boards"]:
        residue, ops, gens = _find_residue_by_simulation(board)
        operations += ops
        generations += gens
        if residue is None:
            return {
                "answer": None, "ok": False, "reason": "orbit miss",
                "operations": operations, "generations": generations,
                "wall_clock_sec": time.perf_counter() - start_clock,
            }
        residues.append(residue)
    phase = residues[0] % 4
    if any(r % 4 != phase for r in residues):
        return {
            "answer": None, "ok": False, "reason": "incompatible phases",
            "operations": operations, "generations": generations,
            "wall_clock_sec": time.perf_counter() - start_clock,
        }
    quotients = [(r - phase) // 4 for r in residues]
    moduli = [board["q"] for board in inst["boards"]]
    turns, crt_ops = _crt_coprime(quotients, moduli)
    operations += crt_ops + 2
    value = 4 * turns + phase
    answer = {"time": value, "residues": residues}
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "operations": operations,
        "generations": generations,
        "wall_clock_sec": time.perf_counter() - start_clock,
    }


def _answer_for_time(inst: dict, value: int) -> dict:
    value %= inst["horizon"]
    return {
        "time": value,
        "residues": [value % (4 * board["q"]) for board in inst["boards"]],
    }


def _attack_coordinate_extrema(inst: dict) -> bool:
    total = 0
    for board in inst["boards"]:
        total += max(x + y for x, y in board["target"])
        total -= max(x + y for x, y in board["start"])
    return verify(inst, _answer_for_time(inst, abs(total)))[0]


def _attack_greedy_first_board(inst: dict) -> bool:
    residue, _, _ = _find_residue_by_simulation(inst["boards"][0])
    return residue is not None and verify(inst, _answer_for_time(inst, residue))[0]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 512) -> bool:
    rng = random.Random(seed ^ 0x231202799)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_phase_blind_anchor_crt(inst: dict) -> bool:
    # A plausible by-hand shortcut: treat every frame as an unrotated southeast
    # phase-zero glider and read displacement from lexicographic x-anchors.
    displacements = []
    moduli = []
    for board in inst["boards"]:
        q = board["q"]
        sx = min(cell[0] for cell in board["start"])
        tx = min(cell[0] for cell in board["target"])
        displacements.append((tx - sx) % q)
        moduli.append(q)
    turns, _ = _crt_coprime(displacements, moduli)
    return verify(inst, _answer_for_time(inst, 4 * turns))[0]


def _transform_instance(inst: dict, rng: random.Random,
                        isometries: bool = True) -> tuple[dict, dict]:
    pairs = []
    for board, residue in zip(inst["boards"], inst["answer"]["residues"]):
        q = board["q"]
        transform = rng.randrange(8) if isometries else 0
        shift = ((rng.randrange(q), rng.randrange(q)) if isometries else (0, 0))
        start = _state_from_json(board["start"], q)
        target = _state_from_json(board["target"], q)
        assert start is not None and target is not None
        new_board = {
            "q": q,
            "start": [list(c) for c in _place(start, q, transform, shift)],
            "target": [list(c) for c in _place(target, q, transform, shift)],
        }
        rng.shuffle(new_board["start"])
        rng.shuffle(new_board["target"])
        pairs.append((new_board, residue))
    rng.shuffle(pairs)
    moved = {key: value for key, value in inst.items()
             if key not in ("boards", "answer")}
    moved["boards"] = [pair[0] for pair in pairs]
    carried = {
        "time": inst["answer"]["time"],
        "residues": [pair[1] for pair in pairs],
    }
    moved["answer"] = carried
    return moved, carried


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    # One character per token is a deliberately conservative tokenizer-free
    # upper bound, stronger than the approximate four-characters-per-token rule.
    return len(encoded), len(encoded), atoms(answer)


def selftest() -> dict:
    """Run all mandatory gates and return a JSON-native measured report."""
    report: dict = {}

    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            json_ok = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            g1_checks += 1
            if not (ok and json_ok):
                g1_failures.append({
                    "preset": preset, "seed": seed, "reason": reason,
                    "json_native": json_ok,
                })
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    planted = inst["answer"]
    residues = planted["residues"]
    if len(residues) < 2 or residues[0] == residues[1]:
        inst = make_instance(seed=271828, **ship_params)
        planted = inst["answer"]
        residues = planted["residues"]
    corruptions = {
        "drop_one": {"time": planted["time"], "residues": residues[:-1]},
        "swap_two": {"time": planted["time"],
                     "residues": [residues[1], residues[0]] + residues[2:]},
        "duplicate": {"time": planted["time"],
                      "residues": residues + [residues[0]]},
        "empty": {},
        "out_of_range": {"time": inst["horizon"], "residues": residues},
    }
    rejection_reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejection_reasons[name] = reason if not ok else "ACCEPTED"
    report["G2_rejects_corruption"] = {
        "pass": ("ACCEPTED" not in rejection_reasons.values()
                 and len(set(rejection_reasons.values())) == len(corruptions)),
        "rejections": rejection_reasons,
        "distinct_reasons": len(set(rejection_reasons.values())),
    }

    realistic = (
        "The common evolution time and checks are below.\n\n"
        "```json\nThis fence is only surrounding prose.\n```\n"
        "<answer>\n```json\n"
        + json.dumps(planted)
        + "\n```\n</answer>\nAll residues use the displayed board order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == planted and verify(inst, parsed)[0]
                 and parse_answer("no tagged answer here") is None),
        "parsed_matches": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_total = 200_000
    guess_rng = random.Random(0x23120279)
    hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    empirical = hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": empirical,
        "exact_probability": 1 / search_space(inst),
        "candidate_space": search_space(inst),
        "prior": (
            "uniform T in the displayed half-open interval, with every "
            "boardwise residue deterministically enforced"
        ),
        "sampling_wall_seconds": guess_seconds,
    }

    baseline = _reference_algorithm(inst)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": empirical < 1e-6 and baseline["ok"] and demo_count == 1,
        "shipping_observed_valid_fraction": empirical,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_exact_density_from_unique_orbit": 1 / search_space(inst),
        "shipping_candidate_space": search_space(inst),
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_exact_operations": baseline["operations"],
        "baseline_generations": baseline["generations"],
        "baseline_successes": int(baseline["ok"]),
        "demo_exact_solution_count": demo_count,
        "enumerate_all_shipping": None,
    }

    attack_names = (
        "outlier_coordinate_extrema",
        "greedy_first_board_residue",
        "random_restart_512_structure_aware",
        "in_context_phase_blind_anchor_crt",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes[attack_names[0]] += int(_attack_coordinate_extrema(trial))
        attack_successes[attack_names[1]] += int(_attack_greedy_first_board(trial))
        attack_successes[attack_names[2]] += int(_attack_random_restart(trial, seed))
        attack_successes[attack_names[3]] += int(_attack_phase_blind_anchor_crt(trial))
        reference_runs.append(_reference_algorithm(trial))
    ref_ok = sum(int(run["ok"]) for run in reference_runs)
    ref_wall = sum(run["wall_clock_sec"] for run in reference_runs)
    ref_ops = sum(run["operations"] for run in reference_runs)
    ref_gens = sum(run["generations"] for run in reference_runs)
    all_failed = all(successes == 0 for successes in attack_successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "sparse hash-map B3/S23 orbit simulation plus CRT",
            "complexity": (
                "O(sum q_i) generations and constant-population sparse updates; "
                "generic dense boards would cost O(sum q_i^3)"
            ),
            "wall_clock_sec": ref_wall,
            "mean_wall_clock_sec": ref_wall / 8,
            "operations": ref_ops,
            "mean_operations": ref_ops // 8,
            "generations": ref_gens,
            "mean_generations": ref_gens // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled_params["n"] == 2 * ship_params["n"]
                 and search_space(doubled) > search_space(inst)),
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "doubled_verify": doubled_reason,
        "base_candidate_space_bits": search_space(inst).bit_length(),
        "doubled_candidate_space_bits": search_space(doubled).bit_length(),
    }

    invariance_checks = 0
    invariance_attempts = 0
    witness_checks = 0
    for seed in range(20):
        trial = make_instance(seed=700 + seed, **ship_params)
        key = canonical_key(trial)
        rng = random.Random(seed ^ 0xC0FFEE)
        variants = []
        moved1, carried1 = _transform_instance(trial, rng, isometries=False)
        variants.append((moved1, carried1))       # order only
        moved2, carried2 = _transform_instance(trial, rng, isometries=True)
        variants.append((moved2, carried2))       # D4 + translations + order
        moved3, carried3 = _transform_instance(moved2, rng, isometries=True)
        variants.append((moved3, carried3))       # a genuine composition
        moved4, carried4 = _transform_instance(moved3, rng, isometries=False)
        variants.append((moved4, carried4))       # cell/board reorder composed
        for moved, carried in variants:
            invariance_attempts += 1
            invariance_checks += int(canonical_key(moved) == key)
            witness_checks += int(verify(moved, carried)[0])
    unrelated = {
        canonical_key(make_instance(seed=9000 + seed, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == invariance_attempts
                 and witness_checks == invariance_attempts
                 and len(unrelated) == 20),
        "invariance_checks": invariance_checks,
        "invariance_attempts": invariance_attempts,
        "transformed_witness_checks": witness_checks,
        "transformed_witness_attempts": invariance_attempts,
        "unrelated_distinct": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": (
            "independent torus translations and D4 isometries, coordinate-list "
            "permutations, board permutations, and their compositions"
        ),
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    intended_operations = 24 + 22 * ship_params["n"]
    evidence = G9_EVIDENCE
    h_attempts = evidence["hinted"]["attempts"]
    p_attempts = evidence["placebo"]["attempts"]
    h_rate = evidence["hinted"]["solved"] / h_attempts if h_attempts else 0.0
    p_rate = evidence["placebo"]["solved"] / p_attempts if p_attempts else 0.0
    within_caps = (chars <= 2000 and tokens <= 500 and elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": h_rate - p_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "tokens": 500,
                 "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
