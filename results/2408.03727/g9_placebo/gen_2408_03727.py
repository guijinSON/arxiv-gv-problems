"""Verified cooperative-coloring generator for arXiv:2408.03727.

The instance is a pair of succinct 2-uniform chain-structured hypergraphs
(cycles).  A witness is an affine parity formula over GF(2) defining the two
parts of a cooperative coloring.  Generation transports the alternating Gray
cycle coloring through a reversible outer mixer, so no generated instance is
solved in order to obtain its certificate.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from functools import lru_cache


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "two succinct 2-uniform chain-structured hypergraphs",
        "reversible linear circuits over GF(2)",
        "an affine parity coloring formula",
    ],
    "verification_operations": [
        "exact GF(2) circuit composition",
        "exact parity-functional pullback",
        "symbolic independence check for every edge of a cycle",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The repeated reversible rounds preserve total bit parity, so a solver "
        "who notices that invariant can discard enormous repetitions and carry "
        "one parity mask only through the shared outer mixer."
    ),
    "hardness_basis": (
        "Track B: exact matrix powering followed by GF(2) elimination runs in "
        "O(n^3 log E) and its measured shipping cost is reported by selftest; "
        "the compact parity-invariant route uses 236 mask updates, while "
        "expanding the two cycles would expose 2^30 vertices."
    ),
    "max_answer_tokens": 16,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "An affine GF(2) coloring c(v)=parity(mask AND v) XOR offset, where "
        "mask is an integer in [0,2^n-1] and offset is 0 or 1; the language "
        "contains exactly 2^(n+1) formulas."
    ),
    "bounds": {
        "mask_min": 0,
        "mask_max": "2^inst['n'] - 1",
        "offset_values": [0, 1],
        "formula_terms": 2,
    },
}

DIFFICULTY = {
    "demo": {
        "n": 4,
        "outer_steps": 8,
        "round_steps": 6,
        "repeat_bits": 5,
    },
    "easy": {
        "n": 28,
        "outer_steps": 196,
        "round_steps": 64,
        "repeat_bits": 20,
    },
    "medium": {
        "n": 29,
        "outer_steps": 216,
        "round_steps": 80,
        "repeat_bits": 24,
    },
    "hard": {
        "n": 30,
        "outer_steps": 236,
        "round_steps": 96,
        "repeat_bits": 28,
    },
}

SHIPPING_DIFFICULTY = "hard"

# Scratch G9 runs set this so harden.py tests the shipping rung alone.  The
# ordinary imported module always exposes the required four-preset ladder.
_single_preset = os.environ.get("GV_SINGLE_PRESET")
if _single_preset in DIFFICULTY:
    DIFFICULTY = {_single_preset: DIFFICULTY[_single_preset]}

STRUCTURAL_HINT = (
    "Every repeated FANOUT2/SWAP round preserves the XOR of all coordinate bits."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the gate indices helps avoid small transcription errors."
)

# These values are replaced by the measured hardening transcripts before ship.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "pending"

NOTES = r"""
Definition 1.1 fixes cooperative coloring as a partition I_1,I_2 in which
I_j is independent in H_j.  Section 4 defines a chain-structured system by a
cyclic ordering with consecutive-set edges and explicitly discusses the role
of 2-edges.  The generated objects are exactly two such systems, specialized
to 2-uniform cycles and represented by reversible circuits rather than by an
exponential edge list.

The paper's easy results were decisive at triage.  Theorem 2.1 and Corollary
2.2 give a constructive coloring for two tight/loose k-uniform cycles and
paths when k >= 3; using that family as Track A would therefore be false.  Our
all-2-edge systems lie outside that theorem.  They nevertheless have an
efficient algorithm: compile the circuits to binary matrices, exponentiate
the repeated rounds, and solve a linear system over GF(2).  selftest reports
that reference algorithm, including its wall time and counted bit operations,
under Track B rather than hiding it among failing attacks.

For generation, begin with the binary-reflected Gray cycle, whose alternating
color is the XOR of every Gray-coordinate bit.  Both inner round circuits use
only SWAP and FANOUT2 operations; each preserves that total parity.  A common
arbitrary CNOT/SWAP outer mixer relabels every vertex of both cycles, and the
known parity certificate is carried through that relabeling gate by gate.
Thus the certificate comes from a structure-preserving transformation of a
known instance, not from solving the finished instance.

The attacks target construction leakage: gate-frequency outliers, one-pass
greedy coefficient commitment, local-search restarts on the exact residual,
and the tempting constant/coordinate-parity ansatz.  A fifth truncated-mixer
attack tests whether merely processing the visible beginning of the mixer is
enough.  The full matrix algorithm succeeds, as Track B requires.
""".strip()


# ---------------------------------------------------------------------------
# GF(2) gates and linear operators


def _check_int(name: str, value: object, low: int, high: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if value < low or (high is not None and value > high):
        upper = "" if high is None else f" and at most {high}"
        raise ValueError(f"{name} must be at least {low}{upper}")
    return value


def _transpose_gate(mask: int, gate: tuple | list) -> int:
    """Apply one gate's transpose to a parity mask.

    Gate C(c,t) is x_t ^= x_c.  Gate F(c,a,b) applies x_a ^= x_c
    and x_b ^= x_c.  Every supported gate is self-inverse.
    """

    kind = gate[0]
    if kind == "C":
        control, target = gate[1], gate[2]
        if (mask >> target) & 1:
            mask ^= 1 << control
        return mask
    if kind == "F":
        control, first, second = gate[1], gate[2], gate[3]
        if ((mask >> first) ^ (mask >> second)) & 1:
            mask ^= 1 << control
        return mask
    if kind == "S":
        first, second = gate[1], gate[2]
        if ((mask >> first) ^ (mask >> second)) & 1:
            mask ^= (1 << first) | (1 << second)
        return mask
    raise ValueError(f"unknown gate kind {kind!r}")


def _pullback_once(mask: int, gates: tuple | list) -> int:
    """Pull a parity functional backwards through a forward gate list."""

    for gate in reversed(gates):
        mask = _transpose_gate(mask, gate)
    return mask


def _inverse_pullback(mask: int, gates: tuple | list) -> int:
    """Apply the inverse of a gate-list pullback to a mask."""

    for gate in gates:
        mask = _transpose_gate(mask, gate)
    return mask


def _freeze_gates(gates: tuple | list) -> tuple[tuple, ...]:
    return tuple(tuple(gate) for gate in gates)


def _apply_op(op: tuple[int, ...], vector: int) -> int:
    result = 0
    while vector:
        bit = vector & -vector
        result ^= op[bit.bit_length() - 1]
        vector -= bit
    return result


def _compose_ops(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    """Return the operator left(right(x))."""

    return tuple(_apply_op(left, column) for column in right)


def _identity_op(n: int) -> tuple[int, ...]:
    return tuple(1 << i for i in range(n))


@lru_cache(maxsize=1024)
def _gate_op(n: int, gates: tuple[tuple, ...]) -> tuple[int, ...]:
    return tuple(_pullback_once(1 << i, gates) for i in range(n))


@lru_cache(maxsize=1024)
def _power_op(op: tuple[int, ...], exponent: int) -> tuple[int, ...]:
    result = _identity_op(len(op))
    base = op
    power = exponent
    while power:
        if power & 1:
            result = _compose_ops(base, result)
        base = _compose_ops(base, base)
        power >>= 1
    return result


def _order_op(inst: dict, which: int) -> tuple[int, ...]:
    n = inst["n"]
    outer = _freeze_gates(inst["outer_mixer"])
    rounds = _freeze_gates(inst["rounds"][which])
    outer_op = _gate_op(n, outer)
    round_op = _gate_op(n, rounds)
    repeated = _power_op(round_op, inst["repetitions"][which])
    return _compose_ops(repeated, outer_op)


def _invert_op(op: tuple[int, ...]) -> tuple[int, ...]:
    """Invert a GF(2) operator represented by its column images."""

    n = len(op)
    rows = []
    for out_bit in range(n):
        coefficients = 0
        for in_bit, image in enumerate(op):
            if (image >> out_bit) & 1:
                coefficients |= 1 << in_bit
        rows.append(coefficients | (1 << (n + out_bit)))

    pivot = 0
    for column in range(n):
        found = next((r for r in range(pivot, n) if (rows[r] >> column) & 1), None)
        if found is None:
            raise ValueError("singular operator")
        rows[pivot], rows[found] = rows[found], rows[pivot]
        for row in range(n):
            if row != pivot and ((rows[row] >> column) & 1):
                rows[row] ^= rows[pivot]
        pivot += 1

    inverse_columns = []
    for input_bit in range(n):
        image = 0
        for output_bit, row in enumerate(rows):
            if (row >> (n + input_bit)) & 1:
                image |= 1 << output_bit
        inverse_columns.append(image)
    return tuple(inverse_columns)


# ---------------------------------------------------------------------------
# Construction


def _random_outer(rng: random.Random, n: int, steps: int) -> list[list[int | str]]:
    gates: list[list[int | str]] = []
    for _ in range(steps):
        first, second = rng.sample(range(n), 2)
        if rng.random() < 0.84:
            gates.append(["C", first, second])
        else:
            gates.append(["S", first, second])
    return gates


def _random_parity_round(
    rng: random.Random, n: int, steps: int
) -> list[list[int | str]]:
    gates: list[list[int | str]] = []
    for _ in range(steps):
        if rng.random() < 0.86:
            control, first, second = rng.sample(range(n), 3)
            gates.append(["F", control, first, second])
        else:
            first, second = rng.sample(range(n), 2)
            gates.append(["S", first, second])
    return gates


def make_instance(
    n: int,
    seed: int = 0,
    outer_steps: int = 196,
    round_steps: int = 64,
    repeat_bits: int = 20,
    **params,
) -> dict:
    """Construct two cycles and carry a known symbolic coloring through them."""

    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    n = _check_int("n", n, 3, 60)
    outer_steps = _check_int("outer_steps", outer_steps, 1, 299)
    round_steps = _check_int("round_steps", round_steps, 1, 512)
    repeat_bits = _check_int("repeat_bits", repeat_bits, 2, 60)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    all_ones = (1 << n) - 1

    # Transformation route for G: all_ones is the known alternating functional
    # on the Gray cycle.  Carry it through a sampled common vertex relabeling.
    outer = None
    answer_mask = None
    for _ in range(256):
        trial = _random_outer(rng, n, outer_steps)
        carried = _inverse_pullback(all_ones, trial)
        weight = carried.bit_count()
        if max(2, n // 3) <= weight <= min(n - 2, (2 * n) // 3 + 1):
            outer = trial
            answer_mask = carried
            break
    if outer is None or answer_mask is None:
        raise RuntimeError("could not construct a nontrivial carried parity mask")

    rounds = [
        _random_parity_round(rng, n, round_steps),
        _random_parity_round(rng, n, round_steps),
    ]
    low = 1 << (repeat_bits - 1)
    high = (1 << repeat_bits) - 1
    repetitions = [rng.randrange(low, high + 1) | 1, rng.randrange(low, high + 1) | 1]
    offset = rng.randrange(2)

    inst = {
        "paper": "arXiv:2408.03727",
        "family": "succinct cooperative coloring of two chain-structured cycles",
        "n": n,
        "vertex_count": 1 << n,
        "outer_steps": outer_steps,
        "round_steps": round_steps,
        "repeat_bits": repeat_bits,
        "outer_mixer": outer,
        "rounds": rounds,
        "repetitions": repetitions,
        "answer": {"mask": answer_mask, "offset": offset},
    }

    ok, reason = verify(inst, inst["answer"])
    if not ok:
        raise RuntimeError("internal certificate transport error: " + reason)
    return inst


# ---------------------------------------------------------------------------
# Statement, parser, and exact checker


def _gate_text(gate: list | tuple) -> str:
    if gate[0] == "C":
        return f"CNOT {gate[1]} {gate[2]}"
    if gate[0] == "F":
        return f"FANOUT2 {gate[1]} {gate[2]} {gate[3]}"
    return f"SWAP {gate[1]} {gate[2]}"


def render(inst: dict) -> str:
    n = inst["n"]
    count = inst["vertex_count"]
    lines = [
        "Cooperative coloring of two succinct chain-structured hypergraphs",
        "",
        f"The common vertex set is V={{0,1,...,{count - 1}}}.  Write every vertex",
        f"as exactly {n} bits x[0],...,x[{n - 1}], with x[0] the least significant",
        "bit.  All bit operations below are over GF(2), so XOR is addition.",
        "",
        "A hypergraph is a vertex set with a collection of edges.  A set is",
        "independent when it contains no whole edge.  A cooperative coloring of",
        "ordered hypergraphs H0,H1 is a partition (I0,I1) of V such that I0 is",
        "independent in H0 and I1 is independent in H1.",
        "",
        "The binary-reflected Gray word is gray(i)=i XOR floor(i/2).  For j=0,1,",
        "define the cyclic order O_j(i), for i=0,...,|V|-1, by starting from",
        "gray(i), applying ROUND_j exactly E_j times, and applying OUTER once.",
        "Every listed circuit is read from top to bottom.  H_j has exactly the",
        "2-element edges {O_j(i),O_j((i+1) mod |V|)} for all i.  This formula is",
        "the complete exact edge list; intervals and ranges are inclusive.",
        "",
        "Gate semantics on the current bit vector x:",
        "  CNOT c t: replace x[t] by x[t] XOR x[c].",
        "  FANOUT2 c a b: simultaneously replace x[a] by x[a] XOR x[c] and",
        "                    x[b] by x[b] XOR x[c].",
        "  SWAP a b: exchange x[a] and x[b].",
        "All indices are 0-based; indices on one gate are distinct.",
        "",
        "OUTER (shared by both orders):",
    ]
    for index, gate in enumerate(inst["outer_mixer"]):
        lines.append(f"  {index}: {_gate_text(gate)}")
    for which in range(2):
        lines.extend([
            "",
            f"ROUND_{which}, repeated E_{which}={inst['repetitions'][which]} times:",
        ])
        for index, gate in enumerate(inst["rounds"][which]):
            lines.append(f"  {index}: {_gate_text(gate)}")

    lines.extend([
        "",
        "Return an affine parity certificate.  For integers mask and offset, it",
        "defines color(v)=parity(mask AND v) XOR offset, where parity is the XOR",
        "of the selected bits.  Put v in I0 when color(v)=0 and in I1 when it is",
        "1.  The mask must be in the inclusive range 0 through |V|-1 and offset",
        "must be exactly 0 or 1.  Any affine certificate whose induced partition",
        "is cooperative is accepted; you must not list the individual vertices.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON object",
        "with exactly the integer keys mask and offset.",
        "Example: <answer>{\"mask\":5,\"offset\":0}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        if not isinstance(text, str):
            return None
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if match is None:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, dict):
            return None
        if set(value) != {"mask", "offset"}:
            return None
        if any(not isinstance(value[key], int) or isinstance(value[key], bool)
               for key in ("mask", "offset")):
            return None
        return {"mask": value["mask"], "offset": value["offset"]}
    except Exception:
        return None


def _cycle_condition(pulled_mask: int, offset: int, forbidden_color: int, n: int) -> bool:
    """Whether an affine functional has no forbidden monochromatic Gray edge."""

    target = (1 << n) - 1
    if pulled_mask == target:
        return True
    if pulled_mask == 0:
        constant = offset
        return constant != forbidden_color
    return False


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any affine cooperative coloring without reading inst['answer']."""

    if not isinstance(answer, dict):
        return False, "malformed answer: expected a JSON object"
    if not answer:
        return False, "empty answer: mask and offset are required"
    missing = {"mask", "offset"} - set(answer)
    if missing:
        return False, "missing field: " + ", ".join(sorted(missing))
    extra = set(answer) - {"mask", "offset"}
    if extra:
        return False, "unexpected field: " + ", ".join(sorted(extra))
    mask = answer["mask"]
    offset = answer["offset"]
    if not isinstance(mask, int) or isinstance(mask, bool):
        return False, "mask must be an integer"
    if mask < 0 or mask >= inst["vertex_count"]:
        return False, f"mask out of range: expected 0..{inst['vertex_count'] - 1}"
    if not isinstance(offset, int) or isinstance(offset, bool):
        return False, "offset must be an integer"
    if offset not in (0, 1):
        return False, "offset out of range: expected 0 or 1"

    first = _apply_op(_order_op(inst, 0), mask)
    if not _cycle_condition(first, offset, forbidden_color=0, n=inst["n"]):
        return False, "H0 violation: I0 contains a complete cycle edge"
    second = _apply_op(_order_op(inst, 1), mask)
    if not _cycle_condition(second, offset, forbidden_color=1, n=inst["n"]):
        return False, "H1 violation: I1 contains a complete cycle edge"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform sample from every well-formed affine formula in the statement."""

    return {"mask": rng.randrange(inst["vertex_count"]), "offset": rng.randrange(2)}


def search_space(inst: dict) -> int | None:
    return 2 * inst["vertex_count"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 1_000_000:
        return None
    total = 0
    for mask in range(inst["vertex_count"]):
        for offset in (0, 1):
            total += int(verify(inst, {"mask": mask, "offset": offset})[0])
    return total


# ---------------------------------------------------------------------------
# Canonical key and genuine relabelings


def canonical_key(inst: dict) -> str:
    """Representation-invariant fingerprint of the ordered cycle pair.

    A common output relabeling cancels from Q^T(P^T)^-1.  Swapping the two
    hypergraphs inverts that relative operator, so the smaller orientation is
    used.  Circuit rewrites inducing the same linear maps also disappear.
    """

    first_inner = _power_op(
        _gate_op(inst["n"], _freeze_gates(inst["rounds"][0])),
        inst["repetitions"][0],
    )
    second_inner = _power_op(
        _gate_op(inst["n"], _freeze_gates(inst["rounds"][1])),
        inst["repetitions"][1],
    )
    relative = _compose_ops(second_inner, _invert_op(first_inner))
    inverse = _invert_op(relative)
    normalized = min(relative, inverse)
    payload = json.dumps([inst["n"], list(normalized)], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _random_relabel_gates(rng: random.Random, n: int) -> list[list[int | str]]:
    return _random_outer(rng, n, max(4, 2 * n))


def _transform_instance(inst: dict, rng: random.Random, relabel: bool, swap: bool) -> dict:
    changed = {
        key: (json.loads(json.dumps(value)) if key in {
            "outer_mixer", "rounds", "repetitions", "answer"
        } else value)
        for key, value in inst.items()
    }
    if relabel:
        gates = _random_relabel_gates(rng, inst["n"])
        changed["outer_mixer"].extend(gates)
        changed["answer"]["mask"] = _inverse_pullback(
            changed["answer"]["mask"], gates
        )
        changed["outer_steps"] = len(changed["outer_mixer"])
    if swap:
        changed["rounds"][0], changed["rounds"][1] = (
            changed["rounds"][1], changed["rounds"][0]
        )
        changed["repetitions"][0], changed["repetitions"][1] = (
            changed["repetitions"][1], changed["repetitions"][0]
        )
        changed["answer"]["offset"] ^= 1
    return changed


def escalate(params: dict) -> dict | str | None:
    """Increase repeated work first, keeping the symbolic answer fixed in size."""

    result = {key: value for key, value in params.items() if key != "_preset"}
    repeat_bits = int(result.get("repeat_bits", 20))
    round_steps = int(result.get("round_steps", 64))
    n = int(result.get("n", 28))
    if repeat_bits < 48:
        result["repeat_bits"] = min(48, repeat_bits + 6)
        result["round_steps"] = min(512, round_steps + 24)
        return result
    if round_steps < 512:
        result["round_steps"] = min(512, round_steps * 2)
        return result
    if n < 60:
        result["n"] = min(60, n + 4)
        result["outer_steps"] = min(299, int(result.get("outer_steps", 196)) + 12)
        return result
    return "cap_bound"


# ---------------------------------------------------------------------------
# Attacks and the successful Track-B reference algorithm


def _residual(inst: dict, mask: int) -> int:
    target = (1 << inst["n"]) - 1
    return (
        (_apply_op(_order_op(inst, 0), mask) ^ target).bit_count()
        + (_apply_op(_order_op(inst, 1), mask) ^ target).bit_count()
    )


def _outlier_attack(inst: dict) -> dict:
    counts = [0] * inst["n"]
    for gate in inst["outer_mixer"]:
        for index in gate[1:]:
            counts[index] += 1
    chosen = max(range(inst["n"]), key=lambda i: (counts[i], -i))
    return {"mask": 1 << chosen, "offset": 0}


def _greedy_attack(inst: dict) -> dict:
    counts = [0] * inst["n"]
    for gate in inst["outer_mixer"]:
        for index in gate[1:]:
            counts[index] += 1
    order = sorted(range(inst["n"]), key=lambda i: (-counts[i], i))
    mask = 0
    for bit in order:
        trial = mask | (1 << bit)
        if _residual(inst, trial) < _residual(inst, mask):
            mask = trial
    return {"mask": mask, "offset": 0}


def _restart_attack(inst: dict, rng: random.Random, restarts: int = 64) -> dict:
    best_mask = 0
    best_score = _residual(inst, best_mask)
    n = inst["n"]
    for _ in range(restarts):
        mask = rng.randrange(1 << n)
        score = _residual(inst, mask)
        for _step in range(3 * n):
            options = []
            for bit in range(n):
                candidate = mask ^ (1 << bit)
                options.append((_residual(inst, candidate), rng.random(), candidate))
            new_score, _, new_mask = min(options)
            if new_score >= score:
                break
            score, mask = new_score, new_mask
        if score < best_score:
            best_score, best_mask = score, mask
        if score == 0:
            return {"mask": mask, "offset": 0}
    return {"mask": best_mask, "offset": 0}


def _ansatz_candidates(inst: dict) -> list[dict]:
    n = inst["n"]
    masks = [0, (1 << n) - 1]
    masks.extend(1 << bit for bit in range(n))
    for gate in inst["outer_mixer"][: min(8, len(inst["outer_mixer"]))]:
        masks.append(sum(1 << index for index in gate[1:]))
    return [{"mask": mask, "offset": offset} for mask in set(masks) for offset in (0, 1)]


def _truncated_mixer_attack(inst: dict) -> dict:
    target = (1 << inst["n"]) - 1
    prefix = inst["outer_mixer"][: max(1, len(inst["outer_mixer"]) // 4)]
    return {"mask": _inverse_pullback(target, prefix), "offset": 0}


def _counted_apply(op: tuple[int, ...], vector: int, stats: dict, n: int) -> int:
    result = 0
    while vector:
        bit = vector & -vector
        result ^= op[bit.bit_length() - 1]
        vector -= bit
        stats["word_xors"] += 1
        stats["bit_operations"] += n
    return result


def _counted_compose(
    left: tuple[int, ...], right: tuple[int, ...], stats: dict, n: int
) -> tuple[int, ...]:
    return tuple(_counted_apply(left, column, stats, n) for column in right)


def _counted_power(op: tuple[int, ...], exponent: int, stats: dict, n: int) -> tuple[int, ...]:
    result = _identity_op(n)
    base = op
    power = exponent
    while power:
        stats["matrix_squaring_iterations"] += 1
        if power & 1:
            result = _counted_compose(base, result, stats, n)
        base = _counted_compose(base, base, stats, n)
        power >>= 1
    return result


def _solve_operator(op: tuple[int, ...], rhs: int, stats: dict) -> int:
    n = len(op)
    rows = []
    for out_bit in range(n):
        row = 0
        for in_bit, image in enumerate(op):
            stats["bit_operations"] += 1
            if (image >> out_bit) & 1:
                row |= 1 << in_bit
        if (rhs >> out_bit) & 1:
            row |= 1 << n
        rows.append(row)

    pivot = 0
    for column in range(n):
        found = next((r for r in range(pivot, n) if (rows[r] >> column) & 1), None)
        if found is None:
            raise ValueError("singular reference matrix")
        if found != pivot:
            rows[pivot], rows[found] = rows[found], rows[pivot]
            stats["row_swaps"] += 1
        for row in range(n):
            if row != pivot and ((rows[row] >> column) & 1):
                rows[row] ^= rows[pivot]
                stats["row_xors"] += 1
                stats["bit_operations"] += n + 1
        pivot += 1

    answer = 0
    for bit, row in enumerate(rows):
        if (row >> n) & 1:
            answer |= 1 << bit
    return answer


def _reference_algorithm(inst: dict) -> tuple[dict, dict]:
    """Mechanical matrix-powering/elimination route; deliberately no invariant."""

    n = inst["n"]
    stats = {
        "bit_operations": 0,
        "word_xors": 0,
        "row_xors": 0,
        "row_swaps": 0,
        "matrix_squaring_iterations": 0,
    }
    start = time.perf_counter()
    outer = _gate_op(n, _freeze_gates(inst["outer_mixer"]))
    round_op = _gate_op(n, _freeze_gates(inst["rounds"][0]))
    repeated = _counted_power(round_op, inst["repetitions"][0], stats, n)
    full = _counted_compose(repeated, outer, stats, n)
    mask = _solve_operator(full, (1 << n) - 1, stats)
    stats["wall_clock_sec"] = time.perf_counter() - start
    return {"mask": mask, "offset": 0}, stats


# ---------------------------------------------------------------------------
# Mandatory gates


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "arXiv:2408.03727",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 101):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "generation_route": "structure-preserving transformation of an alternating Gray-cycle coloring",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    planted = dict(inst["answer"])
    corruptions = {
        "drop_one_field": {"mask": planted["mask"]},
        "swap_fields": {"mask": planted["offset"], "offset": planted["mask"]},
        "duplicate_field": {**planted, "mask_copy": planted["mask"]},
        "empty": {},
        "out_of_range": {"mask": inst["vertex_count"], "offset": planted["offset"]},
        "flip_one_coefficient": {
            "mask": planted["mask"] ^ 1,
            "offset": planted["offset"],
        },
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    body = json.dumps(planted, separators=(",", ":"))
    response = (
        "The parity calculation gives the following formula.\n```json\n"
        f"<answer>{body}</answer>\n```\nI checked both cyclic orders."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed_equal": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
        "json_native": json.loads(json.dumps(planted)) == planted,
    }

    trials = 200_000
    hits = 0
    guess_rng = random.Random(240803727)
    for _ in range(trials):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    observed = hits / trials
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": observed,
        "exact_probability": 1 / inst["vertex_count"],
        "sampler": "uniform over all well-formed affine masks and both offsets",
        "candidate_space": search_space(inst),
    }

    reference, baseline = _reference_algorithm(inst)
    reference_ok, reference_reason = verify(inst, reference)
    tiny = make_instance(seed=2718, **DIFFICULTY["demo"])
    tiny_count = enumerate_all(tiny)
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6 and reference_ok and tiny_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": trials,
        "shipping_observed_fraction": observed,
        "shipping_exact_valid_answers": 2,
        "shipping_candidate_space": search_space(inst),
        "shipping_exact_fraction": 1 / inst["vertex_count"],
        "baseline_wall_clock_sec": baseline["wall_clock_sec"],
        "baseline_bit_operations": baseline["bit_operations"],
        "baseline_word_xors": baseline["word_xors"],
        "baseline_matrix_iterations": baseline["matrix_squaring_iterations"],
        "baseline_success": reference_ok,
        "baseline_reason": reference_reason,
        "demo_exact_valid_answers": tiny_count,
        "demo_candidate_space": search_space(tiny),
    }

    attack_names = (
        "gate_frequency_outlier",
        "greedy_coefficient_commit",
        "random_restart_local_64",
        "constant_and_coordinate_ansatz",
        "truncated_outer_mixer",
    )
    rows = {name: [] for name in attack_names}
    reference_rows = []
    for seed in range(800, 808):
        attacked = make_instance(seed=seed, **shipping)
        candidates = {
            "gate_frequency_outlier": [_outlier_attack(attacked)],
            "greedy_coefficient_commit": [_greedy_attack(attacked)],
            "random_restart_local_64": [
                _restart_attack(attacked, random.Random(seed ^ 0xBADC0DE))
            ],
            "constant_and_coordinate_ansatz": _ansatz_candidates(attacked),
            "truncated_outer_mixer": [_truncated_mixer_attack(attacked)],
        }
        for name, proposals in candidates.items():
            solved = False
            last_reason = "no candidate"
            for proposal in proposals:
                ok, last_reason = verify(attacked, proposal)
                solved |= ok
            rows[name].append({"seed": seed, "solved": solved, "reason": last_reason})

        candidate, cost = _reference_algorithm(attacked)
        ok, reason = verify(attacked, candidate)
        reference_rows.append({
            "seed": seed,
            "solved": ok,
            "reason": reason,
            "wall_clock_sec": cost["wall_clock_sec"],
            "bit_operations": cost["bit_operations"],
        })

    attacks = {
        name: {
            "successes": sum(int(row["solved"]) for row in results),
            "attempts": len(results),
            "results": results,
        }
        for name, results in rows.items()
    }
    reference_successes = sum(int(row["solved"]) for row in reference_rows)
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 and result["attempts"] >= 8
                    for result in attacks.values())
        and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "binary-matrix powering plus Gaussian elimination over GF(2)",
            "complexity": "O(n^3 log E + n*outer_steps) exact bit operations",
            "solves": f"{reference_successes}/8, as expected",
            "successes": reference_successes,
            "attempts": 8,
            "mean_wall_clock_sec": sum(r["wall_clock_sec"] for r in reference_rows) / 8,
            "max_wall_clock_sec": max(r["wall_clock_sec"] for r in reference_rows),
            "mean_bit_operations": sum(r["bit_operations"] for r in reference_rows) / 8,
            "rows": reference_rows,
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst),
        "base_n_bits": inst["n"],
        "base_vertices": inst["vertex_count"],
        "doubled_n_bits": doubled["n"],
        "doubled_vertices": doubled["vertex_count"],
        "search_space_ratio": search_space(doubled) // search_space(inst),
        "verify_reason": doubled_reason,
    }

    key_params = {"n": 12, "outer_steps": 30, "round_steps": 16, "repeat_bits": 10}
    invariant_checks = 0
    real_checks = 0
    key_failures = []
    unrelated = []
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **key_params)
        key = canonical_key(original)
        unrelated.append(key)
        variants = [
            _transform_instance(original, random.Random(seed + 1), True, False),
            _transform_instance(original, random.Random(seed + 2), False, True),
            _transform_instance(original, random.Random(seed + 3), True, True),
        ]
        for variant in variants:
            same = canonical_key(variant) == key
            carried, reason = verify(variant, variant["answer"])
            invariant_checks += int(same)
            real_checks += int(carried)
            if not same or not carried:
                key_failures.append({
                    "seed": seed,
                    "same_key": same,
                    "carried_answer": carried,
                    "reason": reason,
                })
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 60 and real_checks == 60 and distinct == 20,
        "invariance_passed": invariant_checks,
        "invariance_total": 60,
        "real_transform_answers_verified": real_checks,
        "real_transform_total": 60,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "transformations": [
            "arbitrary common invertible output-coordinate relabeling",
            "swap H0/H1 with color-name complement",
            "composition of common relabeling and swap",
            "circuit rewrites with the same induced linear operator",
        ],
        "key_basis": "relative inner pullback operator, canonicalized with its inverse",
        "failures": key_failures,
    }

    compact = json.dumps(planted, separators=(",", ":"))
    token_estimate = len(re.findall(r"[A-Za-z_]+|\d+|[^\sA-Za-z_\d]", compact))
    arms = {name: dict(values) for name, values in G9_ARMS.items()}
    hinted_minus_placebo = 0.0
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    within_caps = (
        len(compact) <= 2000
        and 2 <= 256
        and shipping["outer_steps"] <= 300
        and token_estimate <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    hinted_hardened = G9_HINTED_VERDICT == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": len(compact),
        "answer_tokens": token_estimate,
        "answer_elements": 2,
        "intended_route_operations": shipping["outer_steps"],
        "caps_pass": within_caps,
    }

    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
