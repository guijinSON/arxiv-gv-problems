"""Verified problem generator for arXiv:2605.24023.

The paper's Corollary 1 defines binary directional projection selection from an
arbitrary 0/1 coverage matrix.  This module inverse-generates a uniquely
coverable matrix.  Complete four-clause parity blocks compose to a coverage
certificate, and one duplicated cyclic block system gives a short cancellation
route.  Generation samples the certificate first and never solves an emitted
instance.
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
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "binary projection-by-direction coverage matrix",
        "finite candidate projection set",
        "sampled plane-normal directions",
    ],
    "verification_operations": [
        "exact hexadecimal decoding",
        "exact binary coverage lookup",
        "set union and cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Adjacent cyclic three-variable coverage blocks cancel their shared pair "
        "and leave one step-three recurrence; without that change of variables, "
        "the displayed coverage matrix calls for MILP/SAT search or elimination."
    ),
    "hardness_basis": (
        "Track B: decoding the coverage quartets and applying exact GF(2) "
        "Gauss-Jordan elimination costs O((n+d)n^2) and measured 189,997 scalar "
        "operations (0.0019-0.0037 s mean across repeated local runs) at shipping "
        "n=58,d=180; "
        "the cyclic cancellation route uses at most 298 exact operations."
    ),
    "max_answer_tokens": 5,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 5, "decoys": 1},
    "easy": {"n": 23, "decoys": 20},
    "medium": {"n": 41, "decoys": 80},
    "hard": {"n": 58, "decoys": 180},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The twice-repeated blocks have variable triples that are cyclic translates "
    "of one length-three window whose adjacent parities share two variables."
)
PLACEBO_HINT = (
    "The hexadecimal bit order and the distinction between projections and "
    "directions require consistent bookkeeping throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One lowercase fixed-width hexadecimal word with ceil(n/4) digits and "
        "value below 2^n; bit r selects exactly one of P(r,0), P(r,1)."
    ),
    "bounds": {
        "hex_digits": "ceil(n/4)",
        "integer_min": 0,
        "integer_max": "2^n-1",
        "semantic_projection_choices": "n",
        "candidate_count": "2^n",
    },
}

NOTES = (
    "Section 2, Decision ROI-CTTOP fixes an at-most-k projection witness and "
    "polynomial union verifier. Corollary 1 fixes the binary directional object "
    "B, budget k, threshold L and proves NP-completeness by the paper-central "
    "Set Cover embedding. Sections 3.1 and 4.1 define the sampled directions and "
    "binary coverage matrix used here. Section 4.2 gives O(kmz) marginal-gain "
    "greedy and the (1-1/e) guarantee; Sections 4.3 and 4.5 give the exact MILP "
    "and branch-and-cut certificate route. Sections 6.1 and 8 report that the "
    "realistic CT distribution is easy in practice (pooled median greedy/MILP "
    "ratio 0.998), ruling out an honest Track-A claim for that distribution. "
    "This Track-B family samples a bitword, composes complete parity-clause "
    "coverage identities around it, and adds balanced decoy blocks. Each P(r,0) "
    "and P(r,1) has equal incidence inside every block, defeating per-projection "
    "outliers; shuffled blocks defeat position rules; decoys crowd the cyclic "
    "core; greedy, local improvement, bounded restart and low-period ansatzes are "
    "measured in selftest. Exact GF(2) elimination and clause DPLL are disclosed "
    "as successful reference algorithms."
)

# Filled from script-owned transcripts after the three oracle runs.  Since
# 2026-09-05 these arms are diagnostics; G9 gates only the exact size/effort caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 2, "attempts": 3},
    "hinted_verdict": "too_easy",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, decoys):
    if not _is_int(n) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")
    if not _is_int(decoys) or decoys < 0:
        raise ValueError("decoys must be a nonnegative integer")
    if decoys > math.comb(n, 3) - n:
        raise ValueError("too many distinct decoy triples")
    if not any(math.gcd(step, n) == 1 for step in range(2, n - 1)):
        raise ValueError("n has no supported non-unit cyclic step")


def _hex_width(n):
    return (n + 3) // 4


def _encode_bits(n, bits):
    packed = 0
    for index, bit in enumerate(bits):
        packed |= int(bit) << index
    return format(packed, f"0{_hex_width(n)}x")


def _encode_int(inst, packed):
    return format(packed, f"0{_hex_width(inst['n'])}x")


def _make_block(triple, rhs, copies, rng):
    """Four coverage columns whose simultaneous coverage is one XOR equation."""
    directions = []
    for packed in range(8):
        pattern = [(packed >> position) & 1 for position in range(3)]
        if pattern[0] ^ pattern[1] ^ pattern[2] == rhs:
            continue
        # This clause/direction is uncovered only at `pattern`.
        covers = [[triple[position], 1 - pattern[position]] for position in range(3)]
        rng.shuffle(covers)
        directions.append(covers)
    rng.shuffle(directions)
    return {"copies": copies, "directions": directions}


def make_instance(n, seed=0, decoys=0, **params):
    """Inverse-generate a binary directional coverage matrix and its witness."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, decoys)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    bits = [rng.getrandbits(1) for _ in range(n)]
    if not any(bits):
        bits[rng.randrange(n)] = 1
    if all(bits):
        bits[rng.randrange(n)] = 0

    steps = [step for step in range(2, n - 1) if math.gcd(step, n) == 1]
    step = rng.choice(steps)
    core = {
        tuple(sorted((start, (start + step) % n, (start + 2 * step) % n)))
        for start in range(n)
    }
    if len(core) != n:
        raise AssertionError("cyclic core unexpectedly repeated a triple")

    decoy_triples = set()
    while len(decoy_triples) < decoys:
        triple = tuple(sorted(rng.sample(range(n), 3)))
        if triple not in core:
            decoy_triples.add(triple)

    blocks = []
    for triple in core:
        rhs = bits[triple[0]] ^ bits[triple[1]] ^ bits[triple[2]]
        blocks.append(_make_block(list(triple), rhs, 2, rng))
    for triple in decoy_triples:
        rhs = bits[triple[0]] ^ bits[triple[1]] ^ bits[triple[2]]
        blocks.append(_make_block(list(triple), rhs, 1, rng))
    rng.shuffle(blocks)

    inst = {
        "paper": "arXiv:2605.24023",
        "family": "complete binary directional projection selection",
        "n": n,
        "decoys": decoys,
        "budget": n,
        "blocks": blocks,
        "projection_count": 2 * n,
        "direction_count": n + sum(4 * block["copies"] for block in blocks),
    }
    inst["answer"] = _encode_bits(n, bits)
    return inst


def _decode_block(block, n):
    if not isinstance(block, dict) or set(block) != {"copies", "directions"}:
        return None, "a coverage block has malformed fields"
    copies, directions = block["copies"], block["directions"]
    if copies not in (1, 2):
        return None, "a coverage block has invalid multiplicity"
    if not isinstance(directions, list) or len(directions) != 4:
        return None, "a coverage block must contain four directions"
    triple = None
    bad_patterns = set()
    for direction in directions:
        if not isinstance(direction, list) or len(direction) != 3:
            return None, "a direction must list three covering projections"
        mapping = {}
        for projection in direction:
            if (not isinstance(projection, list) or len(projection) != 2 or
                    not _is_int(projection[0]) or projection[0] < 0 or
                    projection[0] >= n or projection[1] not in (0, 1)):
                return None, "a direction contains an invalid projection label"
            variable, value = projection
            if variable in mapping:
                return None, "a direction repeats a projection pair"
            mapping[variable] = value
        variables = tuple(sorted(mapping))
        if triple is None:
            triple = variables
        elif variables != triple:
            return None, "directions in one block use different projection triples"
        bad_patterns.add(tuple(1 - mapping[variable] for variable in variables))
    if len(bad_patterns) != 4:
        return None, "a block does not have four distinct uncovered patterns"
    parities = {pattern[0] ^ pattern[1] ^ pattern[2] for pattern in bad_patterns}
    if len(parities) != 1:
        return None, "a block is not a complete three-variable parity quartet"
    rhs = 1 - next(iter(parities))
    return {"copies": copies, "triple": triple, "rhs": rhs,
            "directions": directions}, None


def _cycle_order(core_triples, n):
    pair_counts = {}
    for triple in core_triples:
        for pair in itertools.combinations(triple, 2):
            pair = tuple(sorted(pair))
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    adjacency = {variable: [] for variable in range(n)}
    for (left, right), count in pair_counts.items():
        if count == 2:
            adjacency[left].append(right)
            adjacency[right].append(left)
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        return None
    start = min(adjacency)
    order = [start]
    previous, current = None, start
    while True:
        candidates = [v for v in adjacency[current] if v != previous]
        if not candidates:
            return None
        nxt = min(candidates) if previous is None else candidates[0]
        if nxt == start:
            break
        if nxt in order or len(order) >= n:
            return None
        order.append(nxt)
        previous, current = current, nxt
    if len(order) != n:
        return None
    expected = {
        frozenset((order[index], order[(index + 1) % n], order[(index + 2) % n]))
        for index in range(n)
    }
    if expected != {frozenset(triple) for triple in core_triples}:
        return None
    return order


def _validate_instance(inst):
    cached = inst.get("_validation_cache")
    if isinstance(cached, dict):
        return cached, None
    n, decoys = inst.get("n"), inst.get("decoys")
    try:
        _validate_parameters(n, decoys)
    except (TypeError, ValueError) as exc:
        return None, "instance parameters are invalid: " + str(exc)
    if inst.get("budget") != n or inst.get("projection_count") != 2 * n:
        return None, "instance projection or budget metadata is inconsistent"
    blocks = inst.get("blocks")
    if not isinstance(blocks, list) or len(blocks) != n + decoys:
        return None, "instance block count is inconsistent"
    decoded = []
    seen = set()
    core = []
    for block in blocks:
        item, error = _decode_block(block, n)
        if error is not None:
            return None, error
        triple = item["triple"]
        if triple in seen:
            return None, "instance repeats a variable triple across blocks"
        seen.add(triple)
        decoded.append(item)
        if item["copies"] == 2:
            core.append(triple)
    if len(core) != n or sum(item["copies"] == 1 for item in decoded) != decoys:
        return None, "core/decoy multiplicities are inconsistent"
    order = _cycle_order(core, n)
    if order is None:
        return None, "twice-repeated blocks do not form one cyclic window system"
    direction_count = n + sum(4 * item["copies"] for item in decoded)
    if inst.get("direction_count") != direction_count:
        return None, "instance direction count is inconsistent"
    data = {"blocks": decoded, "cycle": order}
    inst["_validation_cache"] = data
    return data, None


def render(inst):
    """Render the complete binary directional coverage instance."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    n, width = inst["n"], _hex_width(inst["n"])
    example = format((1 << min(3, n)) - 1, f"0{width}x")
    lines = [
        "Select projections that cover every sampled plane-normal direction.",
        "",
        "Definitions and conventions.",
        "There are candidate projections P(r,b), where r is an integer from 0",
        f"through {n - 1} and b is 0 or 1. A direction is covered when at least",
        "one selected projection appears in its displayed covering set. Different",
        "directions are independent, including identical-looking repeated copies.",
        f"You may select at most k={n} projections. The threshold is L={inst['direction_count']},",
        f"so all {inst['direction_count']} directions must be covered.",
        "",
        "Private directions.",
        "For every r there is one direction v_r covered by exactly {P(r,0),P(r,1)}.",
        "These private directions and the budget force every feasible selection to",
        "contain exactly one projection from each pair r.",
        "",
        "Remaining direction blocks.",
        "A block with multiplicity C represents C distinct copies of each of its",
        "four displayed directions. Repeated copies have the same covering set.",
        "Block order, direction order, and order inside a covering set have no meaning.",
    ]
    digits = len(str(len(data["blocks"]) - 1))
    for index, item in enumerate(data["blocks"]):
        chunks = []
        for direction in item["directions"]:
            covers = ",".join(f"P({variable},{value})" for variable, value in direction)
            chunks.append("{" + covers + "}")
        lines.append(
            f"  block {index:0{digits}d} C={item['copies']}: " + " ; ".join(chunks)
        )
    lines.extend([
        "",
        "Required witness and exact encoding.",
        f"Return one hexadecimal word z of exactly {width} digits and value below 2^{n}.",
        "Leading zeroes are required. Bit r of z is counted from the least-significant",
        "bit: bit 0 is the rightmost binary bit. Bit r=0 selects P(r,0), and bit",
        f"r=1 selects P(r,1). Thus z denotes exactly {n} distinct projections, with",
        "no repetitions and no ordering ambiguity. Hexadecimal letter case is ignored.",
        "Find any z whose selected projections cover every direction.",
        "",
        "Give your final answer inside <answer></answer> tags as exactly the required",
        f"{width} hexadecimal digits, without a 0x prefix.",
        f"Example format only: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract one tagged hexadecimal word, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if len(matches) != 1:
        return None
    body = matches[0].strip()
    fenced = re.fullmatch(r"```(?:text|json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    return body.lower() if re.fullmatch(r"[0-9a-fA-F]+", body) else None


def _decode_answer(inst, answer):
    if not isinstance(answer, str):
        return None, "answer must be a hexadecimal string"
    if not answer:
        return None, "answer is empty"
    width = _hex_width(inst["n"])
    if len(answer) < width:
        return None, "answer has too few hexadecimal digits"
    if len(answer) > width:
        return None, "answer has too many hexadecimal digits"
    if not re.fullmatch(r"[0-9a-fA-F]+", answer):
        return None, "answer contains a non-hexadecimal character"
    packed = int(answer, 16)
    if packed >= (1 << inst["n"]):
        return None, "answer value is outside the n-bit range"
    return packed, None


def _direction_covered(packed, direction):
    return any(((packed >> variable) & 1) == value for variable, value in direction)


def verify(inst, answer):
    """Check any encoded projection subset directly against the coverage data."""
    packed, error = _decode_answer(inst, answer)
    if error is not None:
        return False, error
    data, error = _validate_instance(inst)
    if error is not None:
        return False, error
    # The n private directions are covered because the word selects exactly one
    # projection from every pair. Check every remaining explicit B-column.
    for block_index, item in enumerate(data["blocks"]):
        for direction_index, direction in enumerate(item["directions"]):
            if not _direction_covered(packed, direction):
                return False, (
                    f"direction {direction_index} in block {block_index} is uncovered"
                )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample after enforcing all private-direction/budget constraints."""
    return _encode_int(inst, rng.getrandbits(inst["n"]))


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    if inst["n"] > 16:
        return None
    return sum(verify(inst, _encode_int(inst, value))[0]
               for value in range(1 << inst["n"]))


def _equations(inst):
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    return [(item["triple"], item["rhs"], item["copies"])
            for item in data["blocks"]]


def _satisfies_equations(equations, bits):
    return all(bits[u] ^ bits[v] ^ bits[w] == rhs
               for (u, v, w), rhs, _copies in equations)


def _unsatisfied_weight(equations, bits):
    return sum(copies for (u, v, w), rhs, copies in equations
               if bits[u] ^ bits[v] ^ bits[w] != rhs)


def _compact_shortcut(inst):
    """Cancel adjacent cyclic three-variable equations into one recurrence."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    order, n = data["cycle"], inst["n"]
    core_rhs = {frozenset(item["triple"]): item["rhs"]
                for item in data["blocks"] if item["copies"] == 2}
    rhs = []
    for index in range(n):
        triple = frozenset((order[index], order[(index + 1) % n],
                            order[(index + 2) % n]))
        rhs.append(core_rhs[triple])
    cycle_bits = [0] * n
    position = 0
    for _ in range(n - 1):
        nxt = (position + 3) % n
        cycle_bits[nxt] = cycle_bits[position] ^ rhs[position] ^ rhs[(position + 1) % n]
        position = nxt
    correction = rhs[0] ^ cycle_bits[0] ^ cycle_bits[1] ^ cycle_bits[2]
    bits = [0] * n
    for position, variable in enumerate(order):
        bits[variable] = cycle_bits[position] ^ correction
    return bits


def canonical_key(inst):
    """Canonicalize all storage orders, truth swaps, and variable relabellings."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    order, n = data["cycle"], inst["n"]
    decoys = [item["triple"] for item in data["blocks"] if item["copies"] == 1]
    candidates = []
    for reverse in (False, True):
        base = list(reversed(order)) if reverse else list(order)
        for shift in range(n):
            oriented = base[shift:] + base[:shift]
            labels = {variable: index for index, variable in enumerate(oriented)}
            normalized = sorted(tuple(sorted(labels[v] for v in triple)) for triple in decoys)
            candidates.append(normalized)
    payload = {"n": n, "decoy_triples": min(candidates)}
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return "binary-tuy-cycle-v1:" + hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    n, decoys = params.get("n"), params.get("decoys")
    if not _is_int(n) or not _is_int(decoys):
        return None
    # Grow only the crowding/haystack: witness length and compact route stay fixed.
    candidate = decoys + max(40, n)
    if candidate > math.comb(n, 3) - n:
        return "cap_bound"
    return {"n": n, "decoys": candidate}


def _attack_incidence_outlier(inst):
    """Choose the larger row in each pair; construction balances every pair."""
    scores = [[1, 1] for _ in range(inst["n"])]  # private direction
    for item in _validate_instance(inst)[0]["blocks"]:
        for direction in item["directions"]:
            for variable, value in direction:
                scores[variable][value] += item["copies"]
    return [int(one > zero) for zero, one in scores]


def _attack_pairwise_greedy(inst):
    """Natural one-pair-at-a-time marginal coverage greedy."""
    data, _error = _validate_instance(inst)
    clauses = [(direction, item["copies"])
               for item in data["blocks"] for direction in item["directions"]]
    assignment = [-1] * inst["n"]
    covered = [False] * len(clauses)
    for _ in range(inst["n"]):
        best = None
        for variable in range(inst["n"]):
            if assignment[variable] >= 0:
                continue
            for value in (0, 1):
                gain = 0
                for index, (direction, weight) in enumerate(clauses):
                    if not covered[index] and [variable, value] in direction:
                        gain += weight
                candidate = (gain, -variable, -value, variable, value)
                if best is None or candidate > best:
                    best = candidate
        variable, value = best[-2], best[-1]
        assignment[variable] = value
        for index, (direction, _weight) in enumerate(clauses):
            if not covered[index] and [variable, value] in direction:
                covered[index] = True
    return assignment


def _attack_local_improvement(inst):
    equations = _equations(inst)
    bits = _attack_pairwise_greedy(inst)
    score = _unsatisfied_weight(equations, bits)
    for _sweep in range(2):
        changed = False
        for variable in range(inst["n"]):
            bits[variable] ^= 1
            trial = _unsatisfied_weight(equations, bits)
            if trial < score:
                score = trial
                changed = True
            else:
                bits[variable] ^= 1
        if not changed:
            break
    return bits


def _attack_random_restart(inst, rng, attempts=8192):
    equations = _equations(inst)
    bits = [0] * inst["n"]
    for _ in range(attempts):
        packed = rng.getrandbits(inst["n"])
        bits = [(packed >> index) & 1 for index in range(inst["n"])]
        if _satisfies_equations(equations, bits):
            break
    return bits


def _attack_low_period_ansatz(inst):
    equations, n = _equations(inst), inst["n"]
    candidates = []
    for period in range(1, 5):
        for packed in range(1 << period):
            candidates.append([(packed >> (index % period)) & 1 for index in range(n)])
    return min(candidates, key=lambda bits: _unsatisfied_weight(equations, bits))


def _attack_step_one_recurrence(inst):
    equations, n = _equations(inst), inst["n"]
    rhs = {frozenset(triple): value for triple, value, copies in equations if copies == 2}
    candidates = []
    for first in (0, 1):
        for second in (0, 1):
            bits = [0] * n
            bits[0], bits[1] = first, second
            for index in range(n - 2):
                value = rhs.get(frozenset((index, index + 1, index + 2)), 0)
                bits[index + 2] = value ^ bits[index] ^ bits[index + 1]
            candidates.append(bits)
    return min(candidates, key=lambda bits: _unsatisfied_weight(equations, bits))


def _gaussian_reference(inst):
    """Generic exact GF(2) Gauss-Jordan elimination, with scalar cost counts."""
    equations, n = _equations(inst), inst["n"]
    rows = []
    for triple, rhs, _copies in equations:
        coefficients = 0
        for variable in triple:
            coefficients ^= 1 << variable
        rows.append(coefficients | (rhs << n))
    rank, pivots, bit_tests, row_xors = 0, {}, 0, 0
    for column in range(n):
        pivot = None
        for row_index in range(rank, len(rows)):
            bit_tests += 1
            if (rows[row_index] >> column) & 1:
                pivot = row_index
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for row_index in range(len(rows)):
            if row_index == rank:
                continue
            bit_tests += 1
            if (rows[row_index] >> column) & 1:
                rows[row_index] ^= rows[rank]
                row_xors += 1
        pivots[column] = rank
        rank += 1
    stats = {
        "rank": rank,
        "row_xors": row_xors,
        "bit_tests": bit_tests,
        "decode_operations": 20 * len(equations),
        "scalar_operations": bit_tests + (n + 1) * row_xors + 20 * len(equations),
    }
    if rank != n:
        return None, stats
    bits = [0] * n
    for column, row_index in pivots.items():
        bits[column] = (rows[row_index] >> n) & 1
    return bits, stats


def _clauses(inst):
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    clauses = []
    for item in data["blocks"]:
        for direction in item["directions"]:
            for _ in range(item["copies"]):
                clauses.append([(variable, value) for variable, value in direction])
    return clauses


def _dpll_reference(inst):
    """Clause-level DPLL stand-in for generic exact integer feasibility search."""
    clauses, n = _clauses(inst), inst["n"]
    stats = {"literal_evaluations": 0, "propagations": 0, "decisions": 0,
             "nodes": 0, "backtracks": 0, "full_clause_passes": 0}

    def inspect(clause, assignment):
        unassigned = []
        for variable, required in clause:
            stats["literal_evaluations"] += 1
            value = assignment[variable]
            if value < 0:
                unassigned.append((variable, required))
            elif value == required:
                return True, unassigned
        return False, unassigned

    def recurse(assignment):
        stats["nodes"] += 1
        while True:
            stats["full_clause_passes"] += 1
            changed = False
            for clause in clauses:
                satisfied, unassigned = inspect(clause, assignment)
                if satisfied:
                    continue
                if not unassigned:
                    stats["backtracks"] += 1
                    return None
                if len(unassigned) == 1:
                    variable, required = unassigned[0]
                    if assignment[variable] < 0:
                        assignment[variable] = required
                        stats["propagations"] += 1
                        changed = True
                    elif assignment[variable] != required:
                        stats["backtracks"] += 1
                        return None
            if not changed:
                break
        if all(value >= 0 for value in assignment):
            return assignment
        best = None
        for clause in clauses:
            satisfied, unassigned = inspect(clause, assignment)
            if not satisfied and unassigned and (best is None or len(unassigned) < len(best)):
                best = unassigned
        variable = best[0][0] if best else next(i for i, value in enumerate(assignment) if value < 0)
        for value in (0, 1):
            stats["decisions"] += 1
            child = list(assignment)
            child[variable] = value
            solution = recurse(child)
            if solution is not None:
                return solution
        stats["backtracks"] += 1
        return None

    return recurse([-1] * n), stats


def _transformed_instance(inst, seed):
    """Apply all spelling symmetries and carry the selected projections."""
    rng, n = random.Random(seed), inst["n"]
    permutation = list(range(n))
    rng.shuffle(permutation)
    flips = [rng.getrandbits(1) for _ in range(n)]
    packed, error = _decode_answer(inst, inst["answer"])
    if error is not None:
        raise ValueError(error)
    old_bits = [(packed >> variable) & 1 for variable in range(n)]
    new_bits = [0] * n
    for old in range(n):
        new_bits[permutation[old]] = old_bits[old] ^ flips[old]
    blocks = []
    for block in inst["blocks"]:
        directions = []
        for direction in block["directions"]:
            moved = [[permutation[old], value ^ flips[old]] for old, value in direction]
            rng.shuffle(moved)
            directions.append(moved)
        rng.shuffle(directions)
        blocks.append({"copies": block["copies"], "directions": directions})
    rng.shuffle(blocks)
    transformed = {
        key: value for key, value in inst.items()
        if key not in ("blocks", "answer", "_validation_cache")
    }
    transformed["blocks"] = blocks
    transformed["answer"] = _encode_bits(n, new_bits)
    return transformed


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    return len(compact), (len(compact) + 3) // 4


def selftest():
    report = {
        "paper": "arXiv:2605.24023",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures, attempts = [], 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    shipping = make_instance(seed=260524023, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    unequal = next(((left, right) for left in range(len(planted))
                    for right in range(left + 1, len(planted))
                    if planted[left] != planted[right] and
                    int(planted[:left] + planted[right] + planted[left + 1:right] +
                        planted[left] + planted[right + 1:], 16) < (1 << shipping["n"])),
                   None)
    if unequal is None:
        raise AssertionError("shipping answer has no unequal digits to swap")
    swapped = list(planted)
    swapped[unequal[0]], swapped[unequal[1]] = swapped[unequal[1]], swapped[unequal[0]]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two_unequal_digits": "".join(swapped),
        "duplicate_one": planted + planted[-1],
        "empty": "",
        "out_of_range": "f" + "0" * (len(planted) - 1),
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {item["reason"] for item in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in cases.values()) and len(reasons) == len(cases),
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    realistic = (
        "I checked all private and repeated directions.\n<answer>\n```text\n" +
        planted + "\n```\n</answer>\nThe leading zero, if any, is retained."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    guess_rng, guess_total, guess_hits = random.Random(0x260524023), 200_000, 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    observed = guess_hits / guess_total
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "exact_probability_from_unique_cyclic_system": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": (
            "uniform over the 2^n one-projection-per-private-pair words; budget, "
            "shape, pair coverage, no repeats, and range are already enforced"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "balanced_incidence_outlier": lambda inst, rng: _attack_incidence_outlier(inst),
        "paper_style_pairwise_greedy": lambda inst, rng: _attack_pairwise_greedy(inst),
        "two_sweep_local_improvement": lambda inst, rng: _attack_local_improvement(inst),
        "random_restart_8192": lambda inst, rng: _attack_random_restart(inst, rng, 8192),
        "low_period_by_hand_ansatz": lambda inst, rng: _attack_low_period_ansatz(inst),
        "numeric_step_one_recurrence": lambda inst, rng: _attack_step_one_recurrence(inst),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            t0 = time.perf_counter()
            bits = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - t0
            candidate = bits if isinstance(bits, str) else _encode_bits(inst["n"], bits)
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
    for name, elapsed in attack_elapsed.items():
        attack_results[name]["wall_clock_sec_total_8"] = round(elapsed, 6)
    all_failed = all(item["successes"] == 0 for item in attack_results.values())

    gaussian_successes = dpll_successes = compact_successes = 0
    gaussian_elapsed = dpll_elapsed = 0.0
    gaussian_operations, gaussian_xors = [], []
    dpll_evaluations, dpll_nodes, dpll_decisions = [], [], []
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        t0 = time.perf_counter()
        solution, stats = _gaussian_reference(inst)
        gaussian_elapsed += time.perf_counter() - t0
        gaussian_operations.append(stats["scalar_operations"])
        gaussian_xors.append(stats["row_xors"])
        if solution is not None:
            gaussian_successes += int(verify(inst, _encode_bits(inst["n"], solution))[0])
        t0 = time.perf_counter()
        dpll_solution, dpll_stats = _dpll_reference(inst)
        dpll_elapsed += time.perf_counter() - t0
        dpll_evaluations.append(dpll_stats["literal_evaluations"])
        dpll_nodes.append(dpll_stats["nodes"])
        dpll_decisions.append(dpll_stats["decisions"])
        if dpll_solution is not None:
            dpll_successes += int(verify(inst, _encode_bits(inst["n"], dpll_solution))[0])
        compact_successes += int(verify(
            inst, _encode_bits(inst["n"], _compact_shortcut(inst))
        )[0])

    reference = {
        "name": "decode parity quartets plus Gauss-Jordan elimination over GF(2)",
        "complexity": "O((n+decoys)*n^2) scalar bit operations",
        "wall_clock_sec_total_8": round(gaussian_elapsed, 6),
        "wall_clock_sec_mean": round(gaussian_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(gaussian_operations) // len(gaussian_operations),
        "operations_min": min(gaussian_operations),
        "operations_max": max(gaussian_operations),
        "row_xors_mean": sum(gaussian_xors) // len(gaussian_xors),
        "solves": f"{gaussian_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = 5 * shipping["n"] + 8
    report["G6_adversary_panel"] = {
        "pass": (all_failed and gaussian_successes == dpll_successes ==
                 compact_successes == len(attack_seeds)),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "paper_standard_exact_standin": {
            "name": "DPLL with unit propagation on the exact coverage clauses",
            "relation_to_paper": (
                "dependency-free exact integer-feasibility stand-in; the paper uses "
                "MILP branch-and-cut with LP bounds"
            ),
            "complexity": "O(2^n * z) worst case",
            "wall_clock_sec_total_8": round(dpll_elapsed, 6),
            "wall_clock_sec_mean": round(dpll_elapsed / len(attack_seeds), 8),
            "literal_evaluations_mean": sum(dpll_evaluations) // len(dpll_evaluations),
            "literal_evaluations_min": min(dpll_evaluations),
            "literal_evaluations_max": max(dpll_evaluations),
            "nodes_mean": sum(dpll_nodes) / len(dpll_nodes),
            "decisions_mean": sum(dpll_decisions) / len(dpll_decisions),
            "solves": f"{dpll_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route": {
            "name": "cancel adjacent cyclic windows to one step-three recurrence",
            "worst_case_exact_operations": intended_operations,
            "count_model": (
                "two XORs and two cyclic index updates per recurrence edge, one "
                "possible n-bit complement, and eight setup/check operations"
            ),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    per_seed_work = {
        "balanced_incidence_outlier": 2 * shipping["n"],
        "paper_style_pairwise_greedy": shipping["n"] * (shipping["n"] + 1),
        "two_sweep_local_improvement": (
            shipping["n"] * (shipping["n"] + 1) + 2 * shipping["n"]
        ),
        "random_restart_8192": 8192,
        "low_period_by_hand_ansatz": sum(1 << period for period in range(1, 5)),
        "numeric_step_one_recurrence": 4,
    }
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_failed,
        "exact_valid_answers": 1,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": observed,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "strongest_attack_candidate_or_flip_evaluations_total_8": (
            per_seed_work[strongest] * len(attack_seeds)
        ),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled_n = 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
    while doubled_n % 3 == 0:
        doubled_n += 1
    larger = make_instance(n=doubled_n, decoys=shipping["decoys"], seed=707)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and larger["direction_count"] > shipping["direction_count"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "shipping_directions": shipping["direction_count"],
        "doubled_directions": larger["direction_count"],
        "verify_reason": larger_reason,
    }

    invariance_checks = carried_checks = 0
    key_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        for variant in range(2):
            transformed = _transformed_instance(inst, 15000 + 10 * seed + variant)
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "variant": variant,
                                     "reason": "key changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": seed, "variant": variant,
                                     "reason": "carried witness failed"})
    unrelated = [canonical_key(make_instance(
        seed=20000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )) for seed in range(20)]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "arbitrary projection-pair renumbering",
            "independent 0/1 swaps inside every projection pair",
            "block/direction/covering-set storage permutations",
            "composition of all preceding maps",
        ],
        "canonicalization": (
            "recover the doubled-block cycle, minimize decoy triples over its "
            "dihedral labellings, and normalize independent truth labels"
        ),
    }

    answer_chars, answer_tokens = _json_answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and shipping["n"] <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": shipping["n"],
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
