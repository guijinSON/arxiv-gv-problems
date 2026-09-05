"""Verified anchored-intercalate generator for arXiv:0907.1481.

Instances are exact switched back-circulant Latin squares.  The witness is the
four-cell support of an intercalate through a specified anchor.  Generation
carries a known half-order rectangle through invertible xorshift relabellings;
it never searches the square it has built.
"""

from __future__ import annotations

import hashlib
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
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Latin square given by an exact quasigroup operation",
        "four-cell support of a Latin intercalate",
        "cell-disjoint Latin-trade switches",
    ],
    "verification_operations": [
        "exact integer addition modulo a power of two",
        "exact bit shifts and exclusive-or",
        "finite set comparison",
        "four exact quasigroup evaluations",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A half-order difference in both hidden cyclic coordinates survives "
        "every switched intercalate; without that invariant one must search "
        "anchored rectangles or solve the relabelling maps mechanically."
    ),
    "hardness_basis": (
        "Track B: bit-packed Gaussian elimination over GF(2) solves the two "
        "xorshift preimage systems using O(n^2) bit-packed row operations "
        "(O(n^3) bit complexity); "
        "at shipping n=64 and seed 271828 it took 0.001983 seconds and 23,327 "
        "counted bit/word operations, while finite-series inversion takes 107 "
        "exact operations in the same instance."
    ),
    "max_answer_tokens": 45,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
                 + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of four distinct [row,column] cells forming the complete "
        "2-by-2 rectangle through the stated anchor.  A candidate chooses one "
        "non-anchor row and one non-anchor column, giving (q-1)^2 candidates."
    ),
    "bounds": {
        "cells": 4,
        "integers_per_cell": 2,
        "integer_range": "0..q-1",
        "candidate_count": "(q-1)^2",
    },
}

DIFFICULTY = {
    "demo": {"n": 4, "factors": 2, "switch_pairs": 1},
    "easy": {"n": 32, "factors": 4, "switch_pairs": 8},
    "medium": {"n": 64, "factors": 5, "switch_pairs": 16},
    "hard": {"n": 96, "factors": 6, "switch_pairs": 24},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "A half-order difference in both hidden cyclic coordinates is unchanged "
    "by every listed switch."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the row and column labels helps avoid small "
    "transcription errors."
)

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition 1.1 fixes Latin and partial Latin squares.  Definitions 1.2 and 1.3
give the exact bitrade conditions.  Example 1.4 gives the trade-replacement
identity, Section 2 defines B_n as the addition table modulo n, and Section 2.1
defines an intercalate as a trade of size four.  Those are exactly the objects
rendered and checked here; there is no graph or finite-field surrogate.

Step 0 rules out Track A.  The paper proves no hard distribution.  Its bundled
Sage source reduces mate-finding to DLX exact cover and its
intercalate_homology routine scans every pair of rows and columns.  For this
generated distribution a stronger polynomial algorithm exists: build the two
binary matrices induced by the public xorshift chains and solve M*t=h by
Gaussian elimination over GF(2).  It is reported as the successful Track B
reference algorithm, not disguised as a failed attack.

Generation uses composition of identities.  In B_q, adding h=q/2 to both a row
and a column gives a two-symbol rectangle.  Switching any cell-disjoint
h-by-h intercalate preserves every such rectangle.  Each relabelling factor
v -> v XOR shift(v) is invertible because the shift is nilpotent; its inverse
is the finite geometric series I+S+S^2+..., evaluated by doubling the shift
distance.  The generator applies those inverses to h and carries the anchored
rectangle through the maps.  It never recovers a witness by search.

An earlier affine-Feistel version failed construction-aware hardening: its
fixed top-bit differential solved 3/3 fresh oracle instances.  A nonlinear
Feistel repair still fell 2/3 at n=20 by direct arithmetic.  The current form
makes the compression auditable: generic elimination is the mechanical route,
while finite-series inversion is the compact route.  The attacks test switch
coordinate leakage, greedy neighbours, a visible half shift, inversion of only
one factor, and 256 random anchored rectangles.
""".strip()


def _copy_json(value):
    return json.loads(json.dumps(value))


def _xorshift(value, shift, direction, bits, inverse=False):
    """Apply or invert v -> v XOR shift(v) on exactly ``bits`` bits."""
    mask = (1 << bits) - 1
    value &= mask
    if not inverse:
        if direction == "left":
            return value ^ ((value << shift) & mask)
        if direction == "right":
            return value ^ (value >> shift)
        raise ValueError("unknown xorshift direction")
    distance = shift
    result = value
    while distance < bits:
        if direction == "left":
            result ^= (result << distance) & mask
        elif direction == "right":
            result ^= result >> distance
        else:
            raise ValueError("unknown xorshift direction")
        distance *= 2
    return result & mask


def _component(value, component, bits):
    kind = component.get("type")
    inverse = bool(component.get("inverse", False))
    q = 1 << bits
    if kind == "xorshift":
        return _xorshift(value, component["shift"],
                         component["direction"], bits, inverse)
    if kind == "xor":
        return value ^ component["mask"]
    if kind == "affine":
        multiplier = component["multiplier"]
        offset = component["offset"]
        if inverse:
            return ((value - offset) * pow(multiplier, -1, q)) % q
        return (multiplier * value + offset) % q
    raise ValueError("unknown map component")


def _chain(value, components, bits):
    for component in components:
        value = _component(value, component, bits)
    return value


def _inverse_chain(value, components, bits):
    for component in reversed(components):
        inverse = dict(component)
        inverse["inverse"] = not bool(component.get("inverse", False))
        value = _component(value, inverse, bits)
    return value


def _new_xorshift_chain(rng, bits, factor_count):
    directions = ["left" if i % 2 == 0 else "right"
                  for i in range(factor_count)]
    if rng.randrange(2):
        directions.reverse()
    upper = max(2, bits // 3)
    return [{"type": "xorshift", "direction": direction,
             "shift": rng.randrange(1, upper)}
            for direction in directions]


def _switch_set(inst):
    return {tuple(pair) for pair in inst["switches"]}


def _internal_entry(inst, x, y, switches=None):
    q = inst["order"]
    half = q // 2
    if switches is None:
        switches = _switch_set(inst)
    symbol = (x + y) % q
    if (x % half, y % half) in switches:
        symbol = (symbol + half) % q
    return symbol


def _entry(inst, row, column, switches=None):
    bits = inst["bits"]
    x = _chain(row, inst["row_map"], bits)
    y = _chain(column, inst["column_map"], bits)
    z = _internal_entry(inst, x, y, switches)
    return _chain(z, inst["symbol_map"], bits)


def _support(row0, row1, column0, column1):
    return [[row0, column0], [row0, column1],
            [row1, column0], [row1, column1]]


def _sample_even_switches(rng, q, pair_count):
    """Choose two corners in every distinct quarter-orbit."""
    quarter = q // 4
    if pair_count > quarter * quarter:
        raise ValueError("too many switch-pair orbits")
    orbits = set()
    while len(orbits) < pair_count:
        orbits.add((rng.randrange(quarter), rng.randrange(quarter)))
    switches = []
    corners = ((0, 0), (quarter, 0), (0, quarter),
               (quarter, quarter))
    for x, y in sorted(orbits):
        for dx, dy in rng.sample(corners, 2):
            switches.append([x + dx, y + dy])
    rng.shuffle(switches)
    return switches


def make_instance(n, seed=0, **params):
    """Construct a switched, relabelled Latin square with a known witness."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or n > 512:
        raise ValueError("n must be an integer in 4..512")
    factor_count = params.pop("factors", 5)
    switch_pairs = params.pop("switch_pairs", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if (isinstance(factor_count, bool) or not isinstance(factor_count, int)
            or not 1 <= factor_count <= 8):
        raise ValueError("factors must be an integer in 1..8")
    if (isinstance(switch_pairs, bool) or not isinstance(switch_pairs, int)
            or switch_pairs < 0):
        raise ValueError("switch_pairs must be a nonnegative integer")

    q = 1 << n
    half = q // 2
    rng = random.Random(seed)
    row_map = _new_xorshift_chain(rng, n, factor_count)
    column_map = _new_xorshift_chain(rng, n, factor_count)
    symbol_map = _new_xorshift_chain(rng, n, factor_count)
    switches = _sample_even_switches(rng, q, switch_pairs)

    row_offset = _inverse_chain(half, row_map, n)
    column_offset = _inverse_chain(half, column_map, n)
    anchor_row = rng.randrange(q)
    anchor_column = rng.randrange(q)
    partner_row = anchor_row ^ row_offset
    partner_column = anchor_column ^ column_offset
    inst = {
        "bits": n,
        "order": q,
        "row_map": row_map,
        "column_map": column_map,
        "symbol_map": symbol_map,
        "switches": switches,
        "anchor": [anchor_row, anchor_column],
    }
    inst["answer"] = _support(anchor_row, partner_row,
                               anchor_column, partner_column)
    return inst


def _format_chain(name, chain):
    return f"  {name} = " + json.dumps(chain, separators=(",", ":"))


def render(inst):
    q = inst["order"]
    bits = inst["bits"]
    anchor_row, anchor_column = inst["anchor"]
    lines = [
        "Find the anchored intercalate in an implicitly represented Latin square.",
        "",
        f"Rows, columns, and symbols are integers 0 through {q - 1}, inclusive.",
        f"The order is q={q}=2^{bits}.  Values are exact nonnegative {bits}-bit",
        "integers; XOR means bitwise exclusive-or.",
        "",
        "Map chains.  A direction=left component with shift=s sends",
        "  v to v XOR ((v left-shift s) modulo q).",
        "A direction=right component sends v to v XOR (v right-shift s).",
        "A chain applies its displayed components from left to right:",
        _format_chain("rho   (public row -> internal row)", inst["row_map"]),
        _format_chain("kappa (public column -> internal column)", inst["column_map"]),
        _format_chain("sigma (internal symbol -> public symbol)", inst["symbol_map"]),
        "",
        f"Let h=q/2={q // 2}.  Given r,c, set x=rho(r), y=kappa(c),",
        "and z=(x+y) modulo q.  If [x modulo h,y modulo h] belongs to",
        "this switch set, replace z by (z+h) modulo q:",
        "  " + json.dumps(inst["switches"], separators=(",", ":")),
        "Then L(r,c)=sigma(z).  The switch list is a set; order is irrelevant.",
        "",
        "An intercalate is a complete 2-by-2 rectangle on distinct rows r0,r1",
        "and columns c0,c1 such that L(r0,c0)=L(r1,c1),",
        "L(r0,c1)=L(r1,c0), and these two symbols are distinct.  Its four",
        "entries are a partial Latin square; swapping the two symbols gives the",
        "disjoint mate, so this is exactly a size-four Latin trade.",
        "",
        f"The rectangle must contain anchor [{anchor_row},{anchor_column}].",
        "Return its occupied cells as a JSON list of four [row,column] pairs.",
        "They must be distinct and form the complete rectangle.  Pair order is",
        "irrelevant; repeats are forbidden; all stated bounds are inclusive.",
        "",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        "Example format: <answer>[[0,0],[0,7],[5,0],[5,7]]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    candidates = list(reversed(tagged))
    candidates.extend(reversed(re.findall(
        r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        starts = [0] if candidate.lstrip().startswith("[") else []
        starts.extend(i for i, char in enumerate(candidate) if char == "[")
        for start in starts:
            try:
                value, _ = decoder.raw_decode(
                    candidate.lstrip() if start == 0 else candidate[start:])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if (isinstance(value, list) and len(value) == 4
                    and all(isinstance(cell, list) for cell in value)):
                return value
    return None


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != 4:
        return False, "support must contain exactly four cells"
    q = inst.get("order")
    if isinstance(q, bool) or not isinstance(q, int) or q < 4:
        return False, "malformed instance order"
    cells = []
    for cell in answer:
        if not isinstance(cell, list) or len(cell) != 2:
            return False, "support contains a malformed cell"
        if any(isinstance(x, bool) or not isinstance(x, int) for x in cell):
            return False, "support contains a noninteger label"
        if any(x < 0 or x >= q for x in cell):
            return False, "support contains an out-of-range label"
        cells.append(tuple(cell))
    if len(set(cells)) != 4:
        return False, "support repeats an occupied cell"
    anchor = tuple(inst.get("anchor", ()))
    if len(anchor) != 2 or anchor not in set(cells):
        return False, "support does not contain the stated anchor"
    rows = sorted({row for row, _ in cells})
    columns = sorted({column for _, column in cells})
    if (len(rows) != 2 or len(columns) != 2
            or set(cells) != {(r, c) for r in rows for c in columns}):
        return False, "support is not a complete two-row by two-column rectangle"
    switches = _switch_set(inst)
    a = _entry(inst, rows[0], columns[0], switches)
    b = _entry(inst, rows[0], columns[1], switches)
    c = _entry(inst, rows[1], columns[0], switches)
    d = _entry(inst, rows[1], columns[1], switches)
    if a != d:
        return False, "main-diagonal symbols do not match"
    if b != c:
        return False, "off-diagonal symbols do not match"
    if a == b:
        return False, "the rectangle does not contain two distinct symbols"
    return True, "ok"


def _sample_except(rng, q, excluded):
    value = rng.randrange(q - 1)
    return value + (value >= excluded)


def random_candidate(inst, rng):
    anchor_row, anchor_column = inst["anchor"]
    row = _sample_except(rng, inst["order"], anchor_row)
    column = _sample_except(rng, inst["order"], anchor_column)
    return _support(anchor_row, row, anchor_column, column)


def search_space(inst):
    return (inst["order"] - 1) ** 2


def enumerate_all(inst):
    q = inst["order"]
    if q > 32:
        return None
    anchor_row, anchor_column = inst["anchor"]
    count = 0
    for row in range(q):
        if row == anchor_row:
            continue
        for column in range(q):
            if column == anchor_column:
                continue
            candidate = _support(anchor_row, row, anchor_column, column)
            count += int(verify(inst, candidate)[0])
    return count


def _v2_mod_power_two(value, modulus):
    value %= modulus
    if value == 0:
        return modulus.bit_length() - 1
    return (value & -value).bit_length() - 1


def canonical_key(inst):
    """Cheap isotopy-invariant fingerprint of the switch configuration."""
    q = inst["order"]
    half = q // 2
    points = sorted(set(map(tuple, inst["switches"])))

    def oriented(swapped):
        pairs = {}
        for index, first in enumerate(points):
            for second in points[index + 1:]:
                dx = _v2_mod_power_two(second[0] - first[0], half)
                dy = _v2_mod_power_two(second[1] - first[1], half)
                key = (dy, dx) if swapped else (dx, dy)
                pairs[key] = pairs.get(key, 0) + 1
        row_counts, column_counts = {}, {}
        for x, y in points:
            row_counts[x] = row_counts.get(x, 0) + 1
            column_counts[y] = column_counts.get(y, 0) + 1
        first = sorted(column_counts.values() if swapped else row_counts.values())
        second = sorted(row_counts.values() if swapped else column_counts.values())
        return {
            "first_multiplicities": first,
            "second_multiplicities": second,
            "pair_valuations": [[a, b, count]
                                for (a, b), count in sorted(pairs.items())],
        }

    alternatives = [oriented(False), oriented(True)]
    normalized = min(alternatives, key=lambda x: json.dumps(x, sort_keys=True))
    payload = {"order": q, "switch_count": len(points),
               "affine_invariant": normalized}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _worst_compact_operations(n, factors):
    iterations = max(1, math.ceil(math.log2(n)))
    per_map = (((factors + 1) // 2 * 3 + factors // 2 * 2)
               * iterations)
    return 2 * per_map + 10


def escalate(params):
    harder = dict(params)
    harder["n"] = int(harder.get("n", 64)) + 32
    harder["switch_pairs"] = int(harder.get("switch_pairs", 16)) + 8
    factors = int(harder.get("factors", 5))
    if _worst_compact_operations(harder["n"], factors) > 300:
        return "cap_bound"
    return harder


def _map_support(answer, row_fn, column_fn):
    return [[row_fn(row), column_fn(column)] for row, column in answer]


def _external_relabel(inst, rng):
    result = _copy_json(inst)
    q = inst["order"]
    row_mask, column_mask, symbol_mask = (rng.randrange(q) for _ in range(3))
    result["row_map"] = [{"type": "xor", "mask": row_mask}] + result["row_map"]
    result["column_map"] = [{"type": "xor", "mask": column_mask}] + result["column_map"]
    result["symbol_map"] = result["symbol_map"] + [{"type": "xor", "mask": symbol_mask}]
    result["anchor"] = [inst["anchor"][0] ^ row_mask,
                        inst["anchor"][1] ^ column_mask]
    result["answer"] = _map_support(
        inst["answer"], lambda x: x ^ row_mask, lambda x: x ^ column_mask)
    return result


def _internal_affine_representative(inst, multiplier, row_offset, column_offset):
    result = _copy_json(inst)
    q = inst["order"]
    if multiplier % 2 != 1:
        raise ValueError("the cyclic multiplier must be odd")
    result["row_map"] += [{"type": "affine", "multiplier": multiplier,
                           "offset": row_offset % q}]
    result["column_map"] += [{"type": "affine", "multiplier": multiplier,
                              "offset": column_offset % q}]
    result["symbol_map"] = [{"type": "affine", "multiplier": multiplier,
                             "offset": (row_offset + column_offset) % q,
                             "inverse": True}] + result["symbol_map"]
    half = q // 2
    result["switches"] = [[(multiplier * x + row_offset) % half,
                            (multiplier * y + column_offset) % half]
                           for x, y in result["switches"]]
    return result


def _transpose_instance(inst):
    result = _copy_json(inst)
    result["row_map"], result["column_map"] = result["column_map"], result["row_map"]
    result["switches"] = [[y, x] for x, y in result["switches"]]
    result["anchor"] = [result["anchor"][1], result["anchor"][0]]
    result["answer"] = [[column, row] for row, column in result["answer"]]
    return result


def _gf2_solve_map(components, bits, target):
    """Solve chain(x)=target by bit-packed Gauss-Jordan elimination."""
    operations = 0
    columns = []
    for bit in range(bits):
        columns.append(_chain(1 << bit, components, bits))
        operations += 2 * len(components)
    rows = []
    for output_bit in range(bits):
        coefficients = 0
        for input_bit, column in enumerate(columns):
            operations += 1
            if (column >> output_bit) & 1:
                coefficients |= 1 << input_bit
                operations += 1
        rows.append(coefficients | (((target >> output_bit) & 1) << bits))
    for column in range(bits):
        pivot = None
        for row in range(column, bits):
            operations += 1
            if (rows[row] >> column) & 1:
                pivot = row
                break
        if pivot is None:
            raise ValueError("singular relabelling map")
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            operations += 1
        for row in range(bits):
            if row == column:
                continue
            operations += 1
            if (rows[row] >> column) & 1:
                rows[row] ^= rows[column]
                operations += 1
    solution = 0
    for bit, row in enumerate(rows):
        operations += 1
        if (row >> bits) & 1:
            solution |= 1 << bit
            operations += 1
    if _chain(solution, components, bits) != target:
        raise AssertionError("GF(2) solve failed")
    return solution, operations


def _reference_gaussian(inst):
    bits = inst["bits"]
    half = inst["order"] // 2
    row_offset, row_ops = _gf2_solve_map(inst["row_map"], bits, half)
    column_offset, column_ops = _gf2_solve_map(inst["column_map"], bits, half)
    row, column = inst["anchor"]
    return _support(row, row ^ row_offset, column, column ^ column_offset), row_ops + column_ops + 2


def _attack_greedy_neighbours(inst):
    row, column = inst["anchor"]
    q = inst["order"]
    return _support(row, (row + 1) % q, column, (column + 1) % q)


def _attack_visible_half_shift(inst):
    row, column = inst["anchor"]
    half = inst["order"] // 2
    return _support(row, row ^ half, column, column ^ half)


def _attack_single_factor_inverse(inst):
    bits, half = inst["bits"], inst["order"] // 2
    row_offset = _inverse_chain(half, [inst["row_map"][-1]], bits)
    column_offset = _inverse_chain(half, [inst["column_map"][-1]], bits)
    row, column = inst["anchor"]
    return _support(row, row ^ row_offset, column, column ^ column_offset)


def _attack_switch_coordinate_outlier(inst):
    row, column = inst["anchor"]
    if inst["switches"]:
        x, y = min(map(tuple, inst["switches"]))
        row_partner, column_partner = row ^ x, column ^ y
        if row_partner == row:
            row_partner ^= 1
        if column_partner == column:
            column_partner ^= 1
    else:
        row_partner, column_partner = row ^ 1, column ^ 1
    return _support(row, row_partner, column, column_partner)


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed)
    candidate = _attack_greedy_neighbours(inst)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return candidate


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _compact_operations(inst):
    operations = 2
    for key in ("row_map", "column_map"):
        for component in reversed(inst[key]):
            if component.get("type") != "xorshift":
                continue
            distance = component["shift"]
            per_iteration = 3 if component["direction"] == "left" else 2
            while distance < inst["bits"]:
                operations += per_iteration
                distance *= 2
    return operations + 8


def _small_latin_check(inst):
    q = inst["order"]
    if q > 32:
        return True
    switches, target = _switch_set(inst), set(range(q))
    return (all({_entry(inst, r, c, switches) for c in range(q)} == target
                for r in range(q))
            and all({_entry(inst, r, c, switches) for r in range(q)} == target
                    for c in range(q)))


def selftest():
    report = {}
    failures, attempts = [], 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    if not _small_latin_check(make_instance(seed=29, **DIFFICULTY["demo"])):
        failures.append(["demo", 29, "operation is not Latin"])
    report["G1_planted_verifies"] = {"pass": not failures,
        "attempts": attempts, "failures": failures,
        "small_latin_square_checked": True}

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)
    answer = _copy_json(inst["answer"])

    corruptions = {}
    dropped = _copy_json(answer); dropped.pop()
    corruptions["drop_one"] = verify(inst, dropped)
    swapped = _copy_json(answer)
    used_rows = {cell[0] for cell in swapped}
    swapped[0][0] = next(x for x in range(inst["order"]) if x not in used_rows)
    corruptions["swap_one"] = verify(inst, swapped)
    duplicated = _copy_json(answer); duplicated[1] = list(duplicated[0])
    corruptions["duplicate"] = verify(inst, duplicated)
    corruptions["empty"] = verify(inst, {})
    out_of_range = _copy_json(answer); out_of_range[0][0] = inst["order"]
    corruptions["out_of_range"] = verify(inst, out_of_range)
    reasons = [reason for ok, reason in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values()) and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": ok, "reason": reason}
                  for name, (ok, reason) in corruptions.items()},
        "distinct_reasons": len(set(reasons))}

    payload = json.dumps(answer, separators=(",", ":"))
    prose = "I used the invariant.\n<answer>\n" + payload + "\n</answer>\nDone."
    fenced = "Result:\n```json\n" + payload + "\n```"
    report["G3_round_trip"] = {
        "pass": parse_answer(prose) == answer and parse_answer(fenced) == answer,
        "prose": parse_answer(prose) == answer,
        "markdown_fence": parse_answer(fenced) == answer}

    sample_total = 200_000
    density_inst = make_instance(seed=314159, **shipping_params)
    rng = random.Random(161803)
    started = time.perf_counter()
    hits = sum(verify(density_inst, random_candidate(density_inst, rng))[0]
               for _ in range(sample_total))
    density_wall = time.perf_counter() - started
    exact_probability = 1 / search_space(density_inst)
    report["G4_guess_resistance"] = {"pass": hits / sample_total < 1e-6 and exact_probability < 1e-6,
        "hits": hits, "total": sample_total,
        "observed_probability": hits / sample_total,
        "exact_valid_answers": 1, "exact_probability": exact_probability,
        "candidate_space": str(search_space(density_inst)),
        "sampling_prior": "uniform non-anchor row times uniform non-anchor column"}

    uniqueness_failures = []
    for seed in range(40):
        small = make_instance(n=4, seed=seed, factors=2, switch_pairs=seed % 5)
        count = enumerate_all(small)
        if count != 1:
            uniqueness_failures.append([seed, count])
    started = time.perf_counter()
    reference_answer, reference_operations = _reference_gaussian(inst)
    reference_wall = time.perf_counter() - started
    reference_ok, reference_reason = verify(inst, reference_answer)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and not uniqueness_failures,
        "baseline_wall_clock_sec": round(reference_wall, 6),
        "baseline_operations": reference_operations,
        "shipping_density": {"preset": SHIPPING_DIFFICULTY, "seed": 314159,
            "hits": hits, "samples": sample_total,
            "observed_fraction": hits / sample_total,
            "wall_clock_sec": round(density_wall, 6)},
        "shipping_exact_valid_answers": 1,
        "shipping_exact_fraction": exact_probability,
        "small_unique_count_validation": {"checks": 40, "failures": uniqueness_failures},
        "strongest_baseline": {"name": "bit-packed Gaussian elimination over GF(2)",
            "seed": 271828, "wall_clock_sec": round(reference_wall, 6),
            "counted_word_and_bit_operations": reference_operations,
            "verify": reference_reason}}

    attack_functions = {
        "outlier_switch_coordinate": lambda x, s: _attack_switch_coordinate_outlier(x),
        "greedy_adjacent_labels": lambda x, s: _attack_greedy_neighbours(x),
        "visible_half_shift": lambda x, s: _attack_visible_half_shift(x),
        "single_factor_inverse": lambda x, s: _attack_single_factor_inverse(x),
        "random_restart_256": lambda x, s: _attack_random_restart(x, 10_000 + s)}
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    reference_successes = reference_attempts = reference_ops_total = 0
    reference_wall_total = 0.0
    for seed in range(8):
        attack_inst = make_instance(seed=seed, **shipping_params)
        for name, attack in attack_functions.items():
            attack_results[name]["successes"] += int(verify(attack_inst, attack(attack_inst, seed))[0])
            attack_results[name]["attempts"] += 1
        started = time.perf_counter()
        candidate, operations = _reference_gaussian(attack_inst)
        reference_wall_total += time.perf_counter() - started
        reference_ops_total += operations
        reference_attempts += 1
        reference_successes += int(verify(attack_inst, candidate)[0])
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {"pass": all_failed and reference_successes == reference_attempts,
        "attacks": attack_results,
        "reference_algorithm": {"name": "bit-packed Gaussian elimination over GF(2)",
            "complexity": "O(n^2) bit-packed row operations; O(n^3) bit complexity",
            "wall_clock_sec": round(reference_wall_total, 6),
            "operations": reference_ops_total,
            "per_instance_operations": reference_ops_total // reference_attempts,
            "solves": f"{reference_successes}/{reference_attempts}, as expected"}}

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2; doubled_params["switch_pairs"] *= 2
    doubled = make_instance(seed=12345, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {"pass": doubled_ok and doubled["order"] > inst["order"]
        and _answer_atoms(doubled["answer"]) == _answer_atoms(answer),
        "shipping_bits": inst["bits"], "larger_bits": doubled["bits"],
        "shipping_space_bits": search_space(inst).bit_length(),
        "larger_space_bits": search_space(doubled).bit_length(),
        "answer_atoms_each": _answer_atoms(answer), "larger_verify": doubled_reason}

    invariant_checks = carried_checks = 0
    distinct_keys, g8_failures = [], []
    for seed in range(20):
        base = make_instance(seed=seed + 500, **shipping_params)
        base_key = canonical_key(base); distinct_keys.append(base_key)
        rng = random.Random(seed + 9000)
        external = _external_relabel(base, rng)
        internal = _internal_affine_representative(base, rng.randrange(1, base["order"], 2),
            rng.randrange(base["order"]), rng.randrange(base["order"]))
        transposed = _transpose_instance(base)
        composed = _transpose_instance(_external_relabel(internal, rng))
        reordered = _copy_json(base); rng.shuffle(reordered["switches"])
        for label, transformed in (("external", external), ("internal_affine", internal),
                                   ("transpose", transposed), ("composed", composed),
                                   ("reordered_switches", reordered)):
            invariant_checks += 1
            if canonical_key(transformed) != base_key:
                g8_failures.append([seed, label, "key changed"])
            carried_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append([seed, label, reason])
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {"pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariant_checks, "carried_witness_checks": carried_checks,
        "distinct_unrelated": distinct_count, "unrelated_attempts": 20,
        "failures": g8_failures,
        "invariances": ["independent public row/column/symbol XOR relabelling",
            "common-odd-multiplier cyclic affine coordinate change",
            "row/column transpose", "compositions and switch-list reorderings"]}

    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_chars, answer_elements = len(answer_blob), _answer_atoms(answer)
    answer_tokens = math.ceil(answer_chars / 4)
    intended_operations = _compact_operations(inst)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    bare, hinted, placebo = (G9_ORACLE_RESULTS[x] for x in ("bare", "hinted", "placebo"))
    difference = None
    if isinstance(hinted["solved"], int) and isinstance(placebo["solved"], int):
        difference = hinted["solved"] / hinted["attempts"] - placebo["solved"] / placebo["attempts"]
    report["G9_no_tool_suitability"] = {"pass": within_caps,
        "arms": {"bare": dict(bare), "hinted": dict(hinted), "placebo": dict(placebo)},
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars, "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps_only_are_gated": True}

    report["pass"] = all(gate.get("pass", False) for name, gate in report.items()
                         if name.startswith("G"))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
