"""Verified planted 3-XORSAT generator for arXiv:1504.08316.

The paper studies random planted CSPs, explicitly including k-XORSAT in
Section 2.1.  This module uses the same native objects: Boolean variables and
parity clauses.  It inverse-generates a unique assignment, hides a nonsingular
tight-cycle subsystem among parity clauses with identically distributed
supports, and verifies submitted assignments by direct exact evaluation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Some cyclic ordering of all variables makes every three consecutive variables the support of an equation."
)
PLACEBO_HINT: str = (
    "Careful attention to the displayed variable indices and right-hand sides can prevent avoidable transcription errors here."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Boolean variables",
        "3-XORSAT parity clauses on a 3-uniform multi-hypergraph",
        "satisfying Boolean assignment",
    ],
    "verification_operations": [
        "exact XOR of three Boolean values",
        "exact comparison with a Boolean right-hand side",
        "assignment syntax and coverage checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Recognize a spanning tight cycle in the shuffled constraint supports; "
        "without it, the direct route is elimination on the full parity system."
    ),
    "hardness_basis": (
        "Track B, Section 2.1 planted 3-XORSAT: dense Gaussian elimination over "
        "GF(2) is O(m*n^2) and at the shipping preset used a measured 105895 "
        "bit XORs and about 0.016 seconds per instance; recognizing the hidden "
        "tight-cycle recurrence reduces recovery to 248 exact XORs, but the cycle "
        "must be found among 283 shuffled, identically distributed supports."
    ),
    "max_answer_tokens": 81,
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
    "demo": {"n": 5, "decoys": 0},
    "easy": {"n": 11, "decoys": 4},
    "medium": {"n": 83, "decoys": 200},
    "hard": {"n": 98, "decoys": 300},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A canonical signed-literal assignment of length n: entry i is +(i+1) "
        "for xi=1 or -(i+1) for xi=0, so every variable occurs exactly once in "
        "increasing absolute-index order."
    ),
    "bounds": {
        "shipping_atomic_elements": 83,
        "maximum_preset_atomic_elements": 98,
        "choices_per_element": 2,
        "absolute_value_min": 1,
        "maximum_preset_absolute_value": 98,
    },
}

# The script-owned bare, structural, and placebo runs reached no oracle because
# OpenRouter returned HTTP 403 on every redraw.  Zero valid attempts is deliberately
# not interpreted as an oracle failure.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_api_limit",
}

NOTES: str = r"""
Section 2.1 fixes the native definition used here: a k-uniform multi-hypergraph
whose k-XORSAT clause is satisfied exactly when the XOR of its variables equals
the displayed bit.  Procedure (1) fixes the planted model by sampling v^0 first
and including only clauses it satisfies.  Theorem 1 concerns concentration of
log Z and is not an inversion-hardness theorem.  Section 3 says the Goldreich
hardness/concentration overlap is unclear, and Section 5 repeats this as an open
problem; consequently a Track A claim would be unsupported.

The certificate-producing algorithm is therefore disclosed.  Every instance is
a linear system over GF(2), and Gaussian elimination finds its unique satisfying
assignment in polynomial time.  This module is Track B.  It samples the answer
first and plants the n supports formed by consecutive triples of a uniform cyclic
ordering.  For 3 not dividing n, subtracting adjacent cyclic equations gives
x_i=x_(i+3); cyclic closure and one original equation make the homogeneous
solution zero, so the planted assignment is unique.  Each planted-cycle support
has the same uniform marginal distribution over 3-subsets as each decoy support;
all right-hand sides are evaluations on the same uniformly sampled assignment.

The compact route recognizes the spanning tight cycle, XORs adjacent right-hand
sides, and follows the step-three recurrence in 3n-1 exact XORs.  The measured
reference route performs dense GF(2) elimination on every shuffled clause.  The
outlier attack guesses each bit from the right-hand-side frequency among its
incident equations, the greedy attack performs coordinate descent on violated
clauses, and random restart combines random initial assignments with coordinate
descent.  An all-zero assignment is also tested as the obvious no-tool ansatz.
All are checked over eight shipping seeds.  A broader sweep exposed that excessive
decoy density makes the planted optimum easier for coordinate ascent; the shipping
window was reduced to 200 decoys, where the hill-climber also failed on 32/32 fresh
audit seeds.  The hard rung uses 300 decoys and failed on another 32/32 fresh seeds.

The canonical key ignores right-hand sides because complementing any subset of
variables is a native XORSAT isomorphism and carries a consistent right-hand side
with it.  It uses a label-invariant color-refinement signature of the incidence
hypergraph.  Exact hypergraph isomorphism is not attempted; this strongest cheap
invariant can theoretically collide, a limitation recorded in the README.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1 << 20


def _validate_parameters(n: int, decoys: int, seed: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")
    if isinstance(decoys, bool) or not isinstance(decoys, int) or decoys < 0:
        raise ValueError("decoys must be a nonnegative integer")
    if decoys > math.comb(n, 3) - n:
        raise ValueError("too many distinct decoy supports")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")


def _signed_answer(bits: list[int]) -> list[int]:
    return [(i + 1) if bit else -(i + 1) for i, bit in enumerate(bits)]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a uniquely satisfiable planted 3-XORSAT instance."""
    decoys = params.pop("decoys", 0)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, decoys, seed)

    rng = random.Random(seed)
    planted = [rng.randrange(2) for _ in range(n)]
    cyclic_order = list(range(n))
    rng.shuffle(cyclic_order)

    cycle_supports = {
        tuple(
            sorted(
                (
                    cyclic_order[i],
                    cyclic_order[(i + 1) % n],
                    cyclic_order[(i + 2) % n],
                )
            )
        )
        for i in range(n)
    }
    if len(cycle_supports) != n:
        raise AssertionError("tight cycle did not have n distinct supports")

    supports = set(cycle_supports)
    target_count = n + decoys
    while len(supports) < target_count:
        supports.add(tuple(sorted(rng.sample(range(n), 3))))

    constraints = []
    for support in sorted(supports):
        rhs = planted[support[0]] ^ planted[support[1]] ^ planted[support[2]]
        displayed = list(support)
        rng.shuffle(displayed)
        constraints.append({"vars": displayed, "rhs": rhs})
    rng.shuffle(constraints)

    return {
        "family": "planted cyclic 3-XORSAT with uniform-support decoys",
        "n": n,
        "arity": 3,
        "constraints": constraints,
        "constraint_count": len(constraints),
        "cycle_constraint_count": n,
        "decoy_constraint_count": decoys,
        "answer": _signed_answer(planted),
    }


def render(inst: dict) -> str:
    lines = []
    for index, constraint in enumerate(inst["constraints"]):
        variables = " XOR ".join(f"x{v}" for v in constraint["vars"])
        lines.append(f"  E{index:04d}: {variables} = {constraint['rhs']}")

    example = json.dumps([i + 1 for i in range(inst["n"])])
    statement = f"""PLANTED 3-XORSAT ASSIGNMENT

There are {inst['n']} Boolean variables x0,...,x{inst['n'] - 1}.  A Boolean value
is exactly 0 or 1.  In every equation, XOR means addition modulo 2: the equation
x_a XOR x_b XOR x_c = r is satisfied when the parity of those three values is r.

Find an assignment satisfying all {inst['constraint_count']} equations below.
The instance promises that exactly one satisfying assignment exists.  Equation
labels are only labels, variable indices are 0-based, and the order of the three
variables within an equation has no effect.

Equations:
{chr(10).join(lines)}

Write the assignment as a JSON array of exactly {inst['n']} signed integers in
canonical variable order.  At position i, write +(i+1) if xi=1 and -(i+1) if
xi=0.  Thus every absolute index 1,...,{inst['n']} occurs once, repetitions are
forbidden, and reordering entries is forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example format (not necessarily a solution): <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract a signed-integer JSON array from tags, fences, or prose."""
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.findall(text)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    bare = re.findall(r"\[(?:\s*[+-]?\d+\s*,)*\s*[+-]?\d+\s*\]", text, re.S)
    bodies = tagged if tagged else (fenced if fenced else bare)
    for body in reversed(bodies):
        candidate = body.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
            candidate = re.sub(r"\s*```$", "", candidate).strip()
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        ):
            return value
    return None


def _bits_from_answer(inst: dict, answer: object) -> tuple[list[int] | None, str]:
    n = inst["n"]
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "assignment is empty"
    if len(answer) < n:
        return None, "assignment is missing one or more variables"
    if len(answer) > n:
        return None, "assignment has extra entries"
    if any(isinstance(item, bool) or not isinstance(item, int) for item in answer):
        return None, "every assignment entry must be an integer"
    if any(item == 0 or abs(item) > n for item in answer):
        return None, "variable index is out of range"
    absolute = [abs(item) for item in answer]
    if len(set(absolute)) != n:
        return None, "a variable index is duplicated"
    if absolute != list(range(1, n + 1)):
        return None, "assignment entries are not in canonical variable order"
    return [int(item > 0) for item in answer], "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any submitted assignment exactly; never consult inst['answer']."""
    bits, reason = _bits_from_answer(inst, answer)
    if bits is None:
        return False, reason
    for index, constraint in enumerate(inst["constraints"]):
        a, b, c = constraint["vars"]
        if bits[a] ^ bits[b] ^ bits[c] != constraint["rhs"]:
            return False, f"equation E{index:04d} is violated"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample assignments already obeying the complete output grammar."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [(i + 1) if rng.randrange(2) else -(i + 1) for i in range(inst["n"])]


def search_space(inst: dict) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if (1 << n) > _ENUMERATION_CAP:
        return None
    count = 0
    for mask in range(1 << n):
        answer = [
            (i + 1) if ((mask >> i) & 1) else -(i + 1) for i in range(n)
        ]
        count += int(verify(inst, answer)[0])
    return count


def _supports(inst: dict) -> list[tuple[int, int, int]]:
    return [tuple(sorted(constraint["vars"])) for constraint in inst["constraints"]]


def _incidence_signature(inst: dict) -> dict:
    """Return a label-invariant Weisfeiler--Lehman incidence signature."""
    n = inst["n"]
    supports = sorted(_supports(inst))
    incident: list[list[int]] = [[] for _ in range(n)]
    for edge, support in enumerate(supports):
        for variable in support:
            incident[variable].append(edge)

    variable_colors = [len(edges) for edges in incident]
    edge_colors = [3] * len(supports)
    rounds = 0
    for rounds in range(1, 13):
        variable_signatures = [
            ("v", variable_colors[v], tuple(sorted(edge_colors[e] for e in incident[v])))
            for v in range(n)
        ]
        edge_signatures = [
            ("e", edge_colors[e], tuple(sorted(variable_colors[v] for v in support)))
            for e, support in enumerate(supports)
        ]
        signatures = variable_signatures + edge_signatures
        palette = {
            signature: color
            for color, signature in enumerate(sorted(set(signatures)))
        }
        new_variables = [palette[signature] for signature in variable_signatures]
        new_edges = [palette[signature] for signature in edge_signatures]
        if new_variables == variable_colors and new_edges == edge_colors:
            break
        variable_colors, edge_colors = new_variables, new_edges

    variable_hist: dict[int, int] = {}
    edge_hist: dict[int, int] = {}
    incidence_hist: dict[str, int] = {}
    for color in variable_colors:
        variable_hist[color] = variable_hist.get(color, 0) + 1
    for color in edge_colors:
        edge_hist[color] = edge_hist.get(color, 0) + 1
    for edge, support in enumerate(supports):
        for variable in support:
            key = f"{variable_colors[variable]}:{edge_colors[edge]}"
            incidence_hist[key] = incidence_hist.get(key, 0) + 1
    return {
        "n": n,
        "edges": len(supports),
        "rounds": rounds,
        "variable_colors": sorted(variable_hist.items()),
        "edge_colors": sorted(edge_hist.items()),
        "incidence_colors": sorted(incidence_hist.items()),
    }


def canonical_key(inst: dict) -> str:
    """Hash a structural invariant, never the seed, answer, or rendering."""
    payload = json.dumps(_incidence_signature(inst), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("ascii")).hexdigest()
    return f"planted-3xorsat-tight-cycle-wl:{digest}"


def escalate(params: dict) -> dict | str | None:
    """Use the last safe crowding/size step, then report the route-operation cap."""
    if not isinstance(params, dict) or set(params) != {"n", "decoys"}:
        return None
    n = params["n"]
    decoys = params["decoys"]
    if not isinstance(n, int) or not isinstance(decoys, int):
        return None
    if n < 98:
        # This is the largest tested size with 3n-1 below the 300-operation cap.
        return {"n": 98, "decoys": 300}
    if n == 98 and decoys < 300:
        return {"n": 98, "decoys": 300}
    return "cap_bound"


def _gaussian_solve(inst: dict) -> tuple[list[int] | None, int]:
    """Solve the full system densely over GF(2), counting cell-level XORs."""
    n = inst["n"]
    rows = []
    for constraint in inst["constraints"]:
        row = [0] * (n + 1)
        for variable in constraint["vars"]:
            row[variable] = 1
        row[n] = constraint["rhs"]
        rows.append(row)

    operations = 0
    pivot_row = 0
    pivot_columns: list[int] = []
    for column in range(n):
        pivot = next((r for r in range(pivot_row, len(rows)) if rows[r][column]), None)
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(len(rows)):
            if r == pivot_row or rows[r][column] == 0:
                continue
            for j in range(column, n + 1):
                rows[r][j] ^= rows[pivot_row][j]
                operations += 1
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == n:
            break

    for row in rows:
        if not any(row[:n]) and row[n]:
            return None, operations
    if pivot_row != n:
        return None, operations
    bits = [0] * n
    for row_index, column in enumerate(pivot_columns):
        bits[column] = rows[row_index][n]
    return _signed_answer(bits), operations


def _find_tight_cycle(inst: dict, node_cap: int = 2_000_000) -> tuple[list[int], int]:
    """Recover a spanning tight cycle from unordered three-variable supports."""
    n = inst["n"]
    supports = {frozenset(support) for support in _supports(inst)}
    transitions: dict[frozenset[int], set[int]] = {}
    for support in supports:
        a, b, c = tuple(support)
        for u, v, w in ((a, b, c), (a, c, b), (b, c, a)):
            transitions.setdefault(frozenset((u, v)), set()).add(w)

    first = 0
    used = {first}
    nodes = 0

    def extend(path: list[int]) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            raise RuntimeError("tight-cycle search exceeded its node cap")
        if len(path) == n:
            closing_one = frozenset((path[-2], path[-1], path[0]))
            closing_two = frozenset((path[-1], path[0], path[1]))
            if closing_one in supports and closing_two in supports:
                return list(path)
            return None
        pair = frozenset((path[-2], path[-1]))
        candidates = [candidate for candidate in transitions.get(pair, ()) if candidate not in used]
        candidates.sort(
            key=lambda candidate: -sum(
                following not in used and following != path[-2]
                for following in transitions.get(frozenset((path[-1], candidate)), ())
            )
        )
        for candidate in candidates:
            used.add(candidate)
            path.append(candidate)
            found = extend(path)
            if found is not None:
                return found
            path.pop()
            used.remove(candidate)
        return None

    second_choices = sorted(
        candidate
        for candidate in range(1, n)
        if frozenset((first, candidate)) in transitions
    )
    for second in second_choices:
        used.add(second)
        found = extend([first, second])
        used.remove(second)
        if found is not None:
            return found, nodes
    raise ValueError("constraint supports contain no spanning tight cycle")


def _compact_cycle_solve(inst: dict) -> tuple[list[int], int, int]:
    """Solve by the tight-cycle recurrence and count exact Boolean XORs."""
    order, search_nodes = _find_tight_cycle(inst)
    rhs_by_support = {
        frozenset(constraint["vars"]): constraint["rhs"]
        for constraint in inst["constraints"]
    }
    n = inst["n"]
    rhs = [
        rhs_by_support[
            frozenset((order[i], order[(i + 1) % n], order[(i + 2) % n]))
        ]
        for i in range(n)
    ]

    offsets = [0] * n
    operations = 0
    position = 0
    for _ in range(n - 1):
        difference = rhs[position] ^ rhs[(position + 1) % n]
        operations += 1
        following = (position + 3) % n
        offsets[following] = offsets[position] ^ difference
        operations += 1
        position = following

    base = rhs[0] ^ offsets[1] ^ offsets[2]
    operations += 2
    bits_by_position = [base]
    for i in range(1, n):
        bits_by_position.append(base ^ offsets[i])
        operations += 1
    bits = [0] * n
    for position, variable in enumerate(order):
        bits[variable] = bits_by_position[position]
    return _signed_answer(bits), operations, search_nodes


def _satisfied_count(inst: dict, bits: list[int]) -> int:
    return sum(
        (bits[c["vars"][0]] ^ bits[c["vars"][1]] ^ bits[c["vars"][2]]) == c["rhs"]
        for c in inst["constraints"]
    )


def _attack_rhs_incidence(inst: dict) -> tuple[list[int], int]:
    """Guess each bit from the RHS majority among its incident equations."""
    zeros = [0] * inst["n"]
    ones = [0] * inst["n"]
    for constraint in inst["constraints"]:
        for variable in constraint["vars"]:
            if constraint["rhs"]:
                ones[variable] += 1
            else:
                zeros[variable] += 1
    bits = [int(ones[i] > zeros[i]) for i in range(inst["n"])]
    return _signed_answer(bits), 3 * len(inst["constraints"])


def _attack_greedy(inst: dict, passes: int = 4) -> tuple[list[int], int]:
    bits = [0] * inst["n"]
    score = _satisfied_count(inst, bits)
    trials = 0
    for _ in range(passes):
        changed = False
        for variable in range(inst["n"]):
            bits[variable] ^= 1
            proposed = _satisfied_count(inst, bits)
            trials += 1
            if proposed > score:
                score = proposed
                changed = True
            else:
                bits[variable] ^= 1
        if not changed:
            break
    return _signed_answer(bits), trials * len(inst["constraints"])


def _attack_random_restart(
    inst: dict,
    rng: random.Random,
    restarts: int = 32,
    passes: int = 2,
) -> tuple[bool, int]:
    """Random-restart coordinate ascent, a mild generic CSP heuristic."""
    trials = 0
    for _ in range(restarts):
        bits = [rng.randrange(2) for _ in range(inst["n"])]
        score = _satisfied_count(inst, bits)
        if score == len(inst["constraints"]):
            return True, trials
        for _ in range(passes):
            changed = False
            order = list(range(inst["n"]))
            rng.shuffle(order)
            for variable in order:
                bits[variable] ^= 1
                proposed = _satisfied_count(inst, bits)
                trials += len(inst["constraints"])
                if proposed > score:
                    score = proposed
                    changed = True
                    if score == len(inst["constraints"]):
                        return True, trials
                else:
                    bits[variable] ^= 1
            if not changed:
                break
    return False, trials


def _attack_all_zero(inst: dict) -> tuple[list[int], int]:
    """The immediate no-tool ansatz: set every Boolean variable to zero."""
    return _signed_answer([0] * inst["n"]), inst["n"]


def _transform_instance(
    inst: dict,
    old_to_new: list[int],
    complemented_old: set[int],
    rng: random.Random,
) -> dict:
    """Apply a variable relabelling, coordinate flips, and input reorder."""
    n = inst["n"]
    old_bits, reason = _bits_from_answer(inst, inst["answer"])
    if old_bits is None:
        raise AssertionError(reason)
    new_bits = [0] * n
    for old, new in enumerate(old_to_new):
        new_bits[new] = old_bits[old] ^ int(old in complemented_old)

    constraints = []
    for constraint in inst["constraints"]:
        rhs = constraint["rhs"]
        for old in constraint["vars"]:
            rhs ^= int(old in complemented_old)
        variables = [old_to_new[old] for old in constraint["vars"]]
        rng.shuffle(variables)
        constraints.append({"vars": variables, "rhs": rhs})
    rng.shuffle(constraints)

    moved = copy.deepcopy(inst)
    moved["constraints"] = constraints
    moved["answer"] = _signed_answer(new_bits)
    return moved


def _answer_metrics(answer: list[int]) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def selftest() -> dict:
    """Run all construction, parsing, density, attack, scaling, and symmetry gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
            compact, operations, _ = _compact_cycle_solve(inst)
            compact_ok = verify(inst, compact)[0]
            if not compact_ok or operations != 3 * inst["n"] - 1:
                g1_failures.append(
                    f"{preset}/{seed}: compact route failed ({operations} XORs)"
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
        "construction_audit": "tight-cycle solver independently recovered a valid assignment",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping_params)
    answer = ship["answer"]

    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    out_of_range = list(answer)
    out_of_range[0] = ship["n"] + 1
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    corruption_reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(corruption_reasons)) == len(corruption_reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(corruption_reasons)),
    }

    realistic = (
        "I reduced the parity constraints exactly.\n```json\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n```\n"
        "The signed entries are in variable order."
    )
    parsed = parse_answer(realistic)
    fenced = parse_answer("Result:\n```json\n" + json.dumps(answer) + "\n```")
    report["G3_round_trip"] = {
        "pass": (
            parsed == answer
            and fenced == answer
            and verify(ship, parsed)[0]
            and parse_answer("no assignment here") is None
        ),
        "tagged_matches": parsed == answer,
        "fenced_matches": fenced == answer,
        "garbage_returns_none": parse_answer("no assignment here") is None,
    }

    guess_rng = random.Random(0x150408316)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "exact_fraction": 2.0 ** (-ship["n"]),
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform over canonical complete Boolean assignments",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_rhs_incidence_majority",
        "greedy_single_bit_clause_gain",
        "random_restart_hillclimb_32x2",
        "obvious_all_zero_ansatz",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    compact_successes = 0
    compact_operations = 0
    compact_nodes = 0
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)

        t0 = time.perf_counter()
        candidate, steps = _attack_rhs_incidence(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["outlier_rhs_incidence_majority"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _attack_greedy(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["greedy_single_bit_clause_gain"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _attack_random_restart(inst, random.Random(seed ^ 0xC5F))
        elapsed = time.perf_counter() - t0
        stat = attacks["random_restart_hillclimb_32x2"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _attack_all_zero(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["obvious_all_zero_ansatz"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        solved, operations = _gaussian_solve(inst)
        reference_wall += time.perf_counter() - t0
        reference_operations += operations
        reference_successes += int(solved is not None and verify(inst, solved)[0])

        compact, operations, nodes = _compact_cycle_solve(inst)
        compact_operations += operations
        compact_nodes += nodes
        compact_successes += int(verify(inst, compact)[0])

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    attack_count = len(attack_seeds)
    reference_average = reference_operations // attack_count
    compact_average = compact_operations // attack_count
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed
            and reference_successes == attack_count
            and compact_successes == attack_count
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "dense Gaussian elimination over GF(2)",
            "complexity": "O(m*n^2) exact cell-level bit XORs",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations_per_instance": reference_average,
            "solves": f"{reference_successes}/{attack_count}, as expected",
        },
        "compact_route_audit": {
            "name": "spanning-tight-cycle recurrence",
            "complexity": "O(n) exact XORs after support-cycle recognition",
            "operations": compact_operations,
            "average_operations_per_instance": compact_average,
            "support_search_nodes": compact_nodes,
            "average_search_nodes": compact_nodes // attack_count,
            "solves": f"{compact_successes}/{attack_count}, as expected",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(
        attacks.items(), key=lambda item: item[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == attack_count,
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": 2.0 ** (-ship["n"]),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_bruteforce_solution_count": demo_count,
        "demo_n": demo["n"],
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": reference_average,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    ladder_n = [params["n"] for params in DIFFICULTY.values()]
    ladder_constraints = [params["n"] + params["decoys"] for params in DIFFICULTY.values()]
    doubled_n = 2 * ship["n"]
    if doubled_n % 3 == 0:
        doubled_n += 1
    doubled = make_instance(
        n=doubled_n,
        decoys=2 * ship["decoy_constraint_count"],
        seed=909,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            ladder_n == sorted(set(ladder_n))
            and ladder_constraints == sorted(set(ladder_constraints))
            and doubled_ok
            and doubled["constraint_count"] > ship["constraint_count"]
            and search_space(doubled) > search_space(ship)
        ),
        "preset_n": dict(zip(DIFFICULTY, ladder_n)),
        "preset_constraint_count": dict(zip(DIFFICULTY, ladder_constraints)),
        "doubled_n": doubled["n"],
        "doubled_constraints": doubled["constraint_count"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(n=29, decoys=50, seed=20_000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        variable_map = list(range(inst["n"]))
        rng.shuffle(variable_map)
        complemented = {i for i in range(inst["n"]) if rng.randrange(2)}
        identity = list(range(inst["n"]))
        variants = (
            _transform_instance(inst, identity, set(), random.Random(seed + 1)),
            _transform_instance(inst, variable_map, set(), random.Random(seed + 2)),
            _transform_instance(inst, identity, complemented, random.Random(seed + 3)),
            _transform_instance(inst, variable_map, complemented, random.Random(seed + 4)),
        )
        for variant_number, variant in enumerate(variants):
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                invariant_failures.append(f"seed {seed} variant {variant_number}: key changed")
            witness_checks += 1
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                invariant_failures.append(
                    f"seed {seed} variant {variant_number}: carried witness {reason}"
                )
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not invariant_failures
            and invariant_checks == 80
            and witness_checks == 80
            and distinct_keys == 20
        ),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "unrelated_instances": 20,
        "distinct_unrelated_keys": distinct_keys,
        "failures": invariant_failures,
        "transformations": [
            "constraint and within-support reorder",
            "variable relabelling",
            "Boolean-coordinate complementation",
            "composition of relabelling and complementation",
        ],
    }

    # All-negative entries are the longest legal serialization at this n, so the
    # gate and profile report the language's worst case rather than a lucky seed.
    longest_answer = _signed_answer([0] * ship["n"])
    answer_chars, answer_tokens, answer_elements = _answer_metrics(longest_answer)
    intended_operations = 3 * ship["n"] - 1
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
