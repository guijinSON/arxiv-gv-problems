"""Forced satisfiable Model RB instances from arXiv:2103.06649.

This module keeps the paper's native growing-domain binary CSP.  It samples one
assignment first, then samples every random relation uniformly conditional on
containing the tuple induced by that assignment.  The planted assignment is
therefore a certificate known by construction; ``verify`` only performs
exact membership tests in the displayed relations.
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


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Model RB variables with growing finite domains",
        "ordered binary constraint scopes",
        "permitted tuple relations encoded as exact bit masks",
    ],
    "verification_operations": [
        "integer range comparison",
        "exact row-major tuple encoding",
        "bit-mask membership test for every constraint",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "The forced tuples have no useful one-variable signature, so local value "
        "statistics must give way to global consistency propagation across the "
        "random constraint network."
    ),
    "hardness_basis": (
        "Track A: Section 2, Theorem 4 transfers algorithmic success between "
        "one-forced and unforced Model RB for fixed parameters; this generator uses "
        "the near-threshold growing-domain regime k=2, alpha=3/5, p=1/2 and "
        "shipping r=21/25<r_c=3/(5 ln 2), while the MAC backtracker's measured "
        "node and wall-clock cost are recorded by selftest G5."
    ),
    "max_answer_tokens": 100,
}

NATIVE = {
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

# r is represented in thousandths.  The named ladder keeps the asymptotic
# constants fixed and raises n; escalate() additionally moves r toward r_c and
# the finite-domain offset, providing fixed-answer-length hardening axes.
DIFFICULTY = {
    "demo": {"n": 4, "density_milli": 800, "domain_offset": 0},
    "easy": {"n": 100, "density_milli": 840, "domain_offset": 0},
    "medium": {"n": 120, "density_milli": 845, "domain_offset": 0},
    "hard": {"n": 140, "density_milli": 850, "domain_offset": 0},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Hint: Individual value frequencies conceal the forced assignments; useful "
    "information lives in consistency propagated across overlapping constraints."
)
PLACEBO_HINT = (
    "Hint: Careful attention to tuple order avoids mistakes when reading the "
    "displayed constraint relations."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of exactly n integers, one domain value in 0..d-1 for "
        "each variable x_0..x_(n-1), with repetitions allowed and order fixed "
        "by the variable indices."
    ),
    "bounds": {
        "length": "exactly n (n <= 240 along the supported ladder)",
        "entry_min": 0,
        "entry_max": "d-1",
        "candidate_count": "d^n",
    },
}

# Filled from the script-owned hardening runs before final delivery.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Definition. Section 2.1 defines Model RB: n variables have common domain size
d=n^alpha; m=r*n*ln(n) ordered k-variable scopes are sampled with repetition;
and every permitted relation contains the nearest integer to (1-p)*d^k tuples.
It also gives the forced generator used here: sample one or two assignments,
then sample each relation conditional on admitting their induced tuple.  This
module uses the native binary CSP and not Section 5's independent-set graph.

Hard and easy regimes. Section 2 requires alpha>1/k and k>=1/(1-p), and gives
r_c=-alpha/ln(1-p).  We use k=2, alpha=3/5, p=1/2 and shipping r=21/25, hence both strict
conditions hold and r is below but close to r_c=3/(5 ln 2), about 0.8656.  The
paper identifies the phase-transition region as hard, cites exponential lower
bounds for one-forced Model RB near the threshold, and notes n=59 as challenging.
Far below the threshold the abundance of solutions is an easy regime; above it
unforced instances are almost surely unsatisfiable, so neither is used.  Theorem
The cited one-forced result and Corollary 2 show that forcing one assignment
preserves the asymptotic solution count/distribution, and Theorem 4 states the corresponding equivalence
of algorithmic success probabilities.  No polynomial certificate-producing
algorithm is given: the certificate here is generated first, not recovered by
an SDP, linear solve, spectrum, formula, table, or other efficient solver.

Generation. One assignment is sampled before any constraint.  For every random
ordered scope, the relation is a uniform subset of the required size conditional
on containing its induced tuple.  Relations are rendered as hexadecimal
row-major bit masks: bit a*d+b says whether (a,b) is permitted.  Plants and all
other permitted tuples therefore come from the same conditional distribution;
there is no positional or magnitude marker.

Attacks. The outlier attack uses permitted-tuple marginals for each variable
value.  The greedy attack assigns high-degree variables while maximizing local
support.  Random restart runs bounded min-conflicts.  The domain-standard attack
is maintaining arc consistency (MAC) with MRV and least-constraining-value
branching under a measured node budget.  The shipping preset is accepted only
if all four fail on eight independently generated instances.  Increasing n,
moving r closer to r_c, and increasing the finite domain provide separate
hardening axes.

Canonicalization. The cheap key is invariant under constraint reordering,
variable renaming, independent domain-value renaming, and reversal of ordered
binary scopes.  It combines incidence-degree/multiplicity data, invariant row
and column degree profiles of every relation, and color refinement of the
variable-constraint incidence graph.  Full binary-CSP isomorphism with coupled
domain permutations is not known to be cheap, so this is deliberately a strong
invariant rather than a complete canonical form; the README discloses the
possibility of rare collisions.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_GUESS_SAMPLES = 200_000
_ATTACK_SEEDS = tuple(range(8100, 8108))
_MAC_NODE_BUDGET = 5_000


def _validate_parameters(n: int, density_milli: int, domain_offset: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if n > 240:
        raise ValueError("n must be at most 240 under the answer cap")
    if (
        isinstance(density_milli, bool)
        or not isinstance(density_milli, int)
        or not 500 <= density_milli <= 860
    ):
        raise ValueError("density_milli must be an integer in 500..860")
    if (
        isinstance(domain_offset, bool)
        or not isinstance(domain_offset, int)
        or not 0 <= domain_offset <= 8
    ):
        raise ValueError("domain_offset must be an integer in 0..8")


def _nearest_three_fifths_power(n: int) -> int:
    """Nearest integer to n^(3/5), computed with integer comparisons."""
    target = n * n * n
    lo, hi = 1, max(2, n)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid**5 <= target:
            lo = mid
        else:
            hi = mid
    # Compare distances without floating point by comparing the fifth powers.
    if target - lo**5 <= hi**5 - target:
        return lo
    return hi


def _relation_width(d: int) -> int:
    return (d * d + 3) // 4


def _mask_to_hex(mask: int, d: int) -> str:
    return format(mask, f"0{_relation_width(d)}x")


def _mask_value(raw: object) -> int | None:
    if not isinstance(raw, str) or not raw or any(c not in "0123456789abcdef" for c in raw):
        return None
    try:
        return int(raw, 16)
    except ValueError:
        return None


def _allowed(mask: int, d: int, left: int, right: int) -> bool:
    return bool((mask >> (left * d + right)) & 1)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a one-forced native Model RB binary CSP."""
    density_milli = params.pop("density_milli", 800)
    domain_offset = params.pop("domain_offset", 0)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, density_milli, domain_offset)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    d = max(2, _nearest_three_fifths_power(n) + domain_offset)
    m = max(1, (density_milli * n * math.log(n) + 500.0) // 1000)
    m = int(m)
    permitted_count = (d * d + 1) // 2  # nearest to d^2/2; half-ties go upward

    sigma = [rng.randrange(d) for _ in range(n)]
    constraints: list[list[object]] = []
    universe = list(range(d * d))
    for _ in range(m):
        left, right = rng.sample(range(n), 2)
        forced = {sigma[left] * d + sigma[right]}
        remaining = [code for code in universe if code not in forced]
        chosen = list(forced)
        chosen.extend(rng.sample(remaining, permitted_count - len(forced)))
        mask = 0
        for code in chosen:
            mask |= 1 << code
        constraints.append([left, right, _mask_to_hex(mask, d)])

    return {
        "family": "one_forced_model_RB_binary_CSP",
        "n": n,
        "d": d,
        "k": 2,
        "alpha": [3, 5],
        "tightness_p": [1, 2],
        "density_r": [density_milli, 1000],
        "constraint_count": m,
        "permitted_tuples_per_constraint": permitted_count,
        "constraints": constraints,
        "answer": sigma,
    }


def render(inst: dict) -> str:
    n, d = inst["n"], inst["d"]
    lines = [
        "Find a satisfying assignment for this forced Model RB binary constraint satisfaction problem.",
        "",
        f"There are n={n} variables x_0,...,x_{n-1}. Each variable takes one integer value in 0,...,{d-1}.",
        "Repeated values are allowed. Variable indices and the output order are 0-based.",
        "Each constraint lists an ordered scope [i,j] and a hexadecimal permitted-tuple mask.",
        f"Decode a candidate tuple (a,b) by q=a*{d}+b. It is permitted exactly when bit q of the mask is 1,",
        "where bit 0 is the least significant (rightmost) bit. Leading hexadecimal zeroes carry no special meaning.",
        "An assignment is satisfying only if its induced ordered tuple is permitted by every listed constraint.",
        "",
        f"The {inst['constraint_count']} constraints are:",
    ]
    for index, (left, right, mask) in enumerate(inst["constraints"]):
        lines.append(f"C{index}: [{left},{right}] 0x{mask}")
    example = ",".join("0" for _ in range(n))
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as one JSON array of exactly n integers.",
            f"Example of the required shape only: <answer>[{example}]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    n, d = inst.get("n"), inst.get("d")
    if len(answer) != n:
        return False, f"answer length {len(answer)} != {n}"
    for index, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {index} is not an integer"
        if not 0 <= value < d:
            return False, f"entry {index}={value} is outside 0..{d - 1}"
    constraints = inst.get("constraints")
    if not isinstance(constraints, list):
        return False, "instance constraints are malformed"
    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, list) or len(constraint) != 3:
            return False, f"instance constraint {index} is malformed"
        left, right, raw_mask = constraint
        if (
            isinstance(left, bool)
            or not isinstance(left, int)
            or isinstance(right, bool)
            or not isinstance(right, int)
            or not 0 <= left < n
            or not 0 <= right < n
            or left == right
        ):
            return False, f"instance scope {index} is malformed"
        mask = _mask_value(raw_mask)
        if mask is None:
            return False, f"instance mask {index} is malformed"
        if not _allowed(mask, d, answer[left], answer[right]):
            return False, f"constraint C{index} on [{left},{right}] is violated"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return [rng.randrange(inst["d"]) for _ in range(inst["n"])]


def search_space(inst: dict) -> int:
    return inst["d"] ** inst["n"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.product(range(inst["d"]), repeat=inst["n"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _relation_profile(mask: int, d: int) -> tuple:
    rows = [0] * d
    cols = [0] * d
    for left in range(d):
        for right in range(d):
            if _allowed(mask, d, left, right):
                rows[left] += 1
                cols[right] += 1
    sides = sorted((tuple(sorted(rows)), tuple(sorted(cols))))
    # The number of 2x2 all-one rectangles is another exact invariant under
    # independent row/column permutations and transposition.
    rectangles = 0
    row_bits = [0] * d
    for left in range(d):
        bits = 0
        for right in range(d):
            if _allowed(mask, d, left, right):
                bits |= 1 << right
        row_bits[left] = bits
    for a in range(d):
        for b in range(a + 1, d):
            common = (row_bits[a] & row_bits[b]).bit_count()
            rectangles += common * (common - 1) // 2
    return sides[0], sides[1], rectangles


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant for the natural binary-CSP relabellings."""
    n, d = inst["n"], inst["d"]
    constraints = inst["constraints"]
    degrees = [0] * n
    pair_counts: dict[tuple[int, int], int] = {}
    relation_profiles = []
    endpoints: list[tuple[int, int]] = []
    for left, right, raw_mask in constraints:
        degrees[left] += 1
        degrees[right] += 1
        pair = (min(left, right), max(left, right))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        relation_profiles.append(_relation_profile(int(raw_mask, 16), d))
        endpoints.append((left, right))

    # Color refinement on the unlabelled incidence graph, seeded with invariant
    # relation profiles. Only histograms enter the key, so names never do.
    var_colors: list[object] = [("v", degree) for degree in degrees]
    con_colors: list[object] = [("c", profile) for profile in relation_profiles]
    for _ in range(4):
        var_neighbours: list[list[object]] = [[] for _ in range(n)]
        for ci, (left, right) in enumerate(endpoints):
            var_neighbours[left].append(con_colors[ci])
            var_neighbours[right].append(con_colors[ci])
        raw_v = [(var_colors[v], tuple(sorted(var_neighbours[v], key=repr))) for v in range(n)]
        raw_c = [
            (con_colors[ci], tuple(sorted((var_colors[left], var_colors[right]), key=repr)))
            for ci, (left, right) in enumerate(endpoints)
        ]
        palette = {item: rank for rank, item in enumerate(sorted(set(raw_v + raw_c), key=repr))}
        var_colors = [palette[item] for item in raw_v]
        con_colors = [palette[item] for item in raw_c]

    signature = {
        "n": n,
        "d": d,
        "m": len(constraints),
        "degrees": sorted(degrees),
        "pair_multiplicities": sorted(pair_counts.values()),
        "relations": sorted(relation_profiles),
        "variable_colors": sorted(var_colors),
        "constraint_colors": sorted(con_colors),
    }
    blob = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Move toward threshold/domain crowding before lengthening the witness."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p.get("n", 59))
    density = int(p.get("density_milli", 800))
    offset = int(p.get("domain_offset", 0))
    if density < 850:
        p["density_milli"] = min(850, density + 10)
        return p
    if offset < 4:
        p["domain_offset"] = offset + 1
        return p
    if n < 220:
        p["n"] = min(220, (5 * n + 3) // 4)
        p["density_milli"] = 820
        p["domain_offset"] = 0
        return p
    return "cap_bound"


def _decoded_constraints(inst: dict) -> list[tuple[int, int, int]]:
    return [(left, right, int(raw, 16)) for left, right, raw in inst["constraints"]]


def _outlier_marginal_attack(inst: dict) -> list[int]:
    n, d = inst["n"], inst["d"]
    scores = [[0] * d for _ in range(n)]
    for left, right, mask in _decoded_constraints(inst):
        for a in range(d):
            for b in range(d):
                if _allowed(mask, d, a, b):
                    scores[left][a] += 1
                    scores[right][b] += 1
    return [max(range(d), key=lambda value: (scores[var][value], -value)) for var in range(n)]


def _incidence(inst: dict) -> tuple[list[list[int]], list[tuple[int, int, int]]]:
    constraints = _decoded_constraints(inst)
    incident: list[list[int]] = [[] for _ in range(inst["n"])]
    for index, (left, right, _mask) in enumerate(constraints):
        incident[left].append(index)
        incident[right].append(index)
    return incident, constraints


def _greedy_support_attack(inst: dict) -> list[int]:
    n, d = inst["n"], inst["d"]
    incident, constraints = _incidence(inst)
    order = sorted(range(n), key=lambda var: (-len(incident[var]), var))
    answer = [-1] * n
    for var in order:
        choices = []
        for value in range(d):
            violations = 0
            support = 0
            for ci in incident[var]:
                left, right, mask = constraints[ci]
                other = right if left == var else left
                if answer[other] >= 0:
                    ok = _allowed(mask, d, value, answer[other]) if left == var else _allowed(mask, d, answer[other], value)
                    violations += not ok
                    support += ok * d
                else:
                    for other_value in range(d):
                        support += _allowed(mask, d, value, other_value) if left == var else _allowed(mask, d, other_value, value)
            choices.append((-violations, support, -value, value))
        answer[var] = max(choices)[-1]
    return answer


def _min_conflicts_attack(inst: dict, rng: random.Random, restarts: int = 16) -> tuple[list[int] | None, int]:
    n, d = inst["n"], inst["d"]
    incident, constraints = _incidence(inst)
    steps = 0
    for _ in range(restarts):
        answer = [rng.randrange(d) for _ in range(n)]
        for _ in range(6 * n):
            violated = [
                ci
                for ci, (left, right, mask) in enumerate(constraints)
                if not _allowed(mask, d, answer[left], answer[right])
            ]
            if not violated:
                return answer, steps
            ci = rng.choice(violated)
            left, right, _mask = constraints[ci]
            var = rng.choice((left, right))
            best: list[int] = []
            best_bad = len(constraints) + 1
            for value in range(d):
                bad = 0
                for cj in incident[var]:
                    a, b, mask = constraints[cj]
                    av = value if a == var else answer[a]
                    bv = value if b == var else answer[b]
                    bad += not _allowed(mask, d, av, bv)
                if bad < best_bad:
                    best_bad, best = bad, [value]
                elif bad == best_bad:
                    best.append(value)
            answer[var] = rng.choice(best)
            steps += 1
    return None, steps


def _mac_attack(inst: dict, node_budget: int = _MAC_NODE_BUDGET) -> tuple[list[int] | None, int, float]:
    """MAC + MRV + least-constraining values, capped at node_budget."""
    started = time.perf_counter()
    n, d = inst["n"], inst["d"]
    incident, constraints = _incidence(inst)
    full = (1 << d) - 1
    nodes = 0

    # support[ci][0][a] is the bitset of right values compatible with left
    # value a; support[ci][1][b] is the converse.  This turns the hot AC revise
    # loop from O(d^2) Python tests into one integer AND per source value.
    support_tables = []
    for left, right, mask in constraints:
        forward = [0] * d
        backward = [0] * d
        for a in range(d):
            for b in range(d):
                if _allowed(mask, d, a, b):
                    forward[a] |= 1 << b
                    backward[b] |= 1 << a
        support_tables.append((forward, backward))

    def revise(domains: list[int], ci: int, source: int) -> tuple[bool, bool]:
        left, right, mask = constraints[ci]
        target = right if source == left else left
        old = domains[source]
        new = 0
        source_values = old
        table = support_tables[ci][0 if source == left else 1]
        while source_values:
            bit = source_values & -source_values
            value = bit.bit_length() - 1
            source_values -= bit
            if table[value] & domains[target]:
                new |= bit
        if new == old:
            return False, bool(new)
        domains[source] = new
        return True, bool(new)

    def propagate(domains: list[int], queue: list[tuple[int, int]]) -> bool:
        pending = set(queue)
        head = 0
        while head < len(queue):
            ci, source = queue[head]
            head += 1
            pending.discard((ci, source))
            changed, nonempty = revise(domains, ci, source)
            if not nonempty:
                return False
            if changed:
                left, right, _mask = constraints[ci]
                target = right if source == left else left
                for cj in incident[source]:
                    a, b, _ = constraints[cj]
                    neighbour = b if a == source else a
                    if cj != ci or neighbour != target:
                        arc = (cj, neighbour)
                        if arc not in pending:
                            pending.add(arc)
                            queue.append(arc)
        return True

    def value_order(domains: list[int], var: int) -> list[int]:
        values = [v for v in range(d) if (domains[var] >> v) & 1]
        scored = []
        for value in values:
            support_total = 0
            for ci in incident[var]:
                left, right, mask = constraints[ci]
                other = right if left == var else left
                table = support_tables[ci][0 if left == var else 1]
                support_count = (table[value] & domains[other]).bit_count()
                support_total += support_count
            scored.append((-support_total, value))
        return [value for _negative, value in sorted(scored)]

    def search(domains: list[int]) -> list[int] | None:
        nonlocal nodes
        if nodes >= node_budget:
            return None
        unresolved = [v for v in range(n) if domains[v].bit_count() > 1]
        if not unresolved:
            candidate = [domain.bit_length() - 1 for domain in domains]
            return candidate if verify(inst, candidate)[0] else None
        var = min(unresolved, key=lambda v: (domains[v].bit_count(), -len(incident[v]), v))
        for value in value_order(domains, var):
            if nodes >= node_budget:
                return None
            nodes += 1
            child = list(domains)
            child[var] = 1 << value
            queue = []
            for ci in incident[var]:
                left, right, _ = constraints[ci]
                queue.append((ci, right if left == var else left))
            if propagate(child, queue):
                result = search(child)
                if result is not None:
                    return result
        return None

    domains = [full] * n
    initial = [(ci, source) for ci, (left, right, _mask) in enumerate(constraints) for source in (left, right)]
    answer = search(domains) if propagate(domains, initial) else None
    return answer, nodes, time.perf_counter() - started


def _transpose_mask(mask: int, d: int) -> int:
    out = 0
    for a in range(d):
        for b in range(d):
            if _allowed(mask, d, a, b):
                out |= 1 << (b * d + a)
    return out


def _relabel_for_test(inst: dict, rng: random.Random) -> dict:
    """Compose every declared isomorphism and carry the witness through it."""
    n, d = inst["n"], inst["d"]
    variable_map = list(range(n))
    rng.shuffle(variable_map)  # old variable -> new variable
    value_maps = []
    for _ in range(n):
        permutation = list(range(d))
        rng.shuffle(permutation)  # old value -> new value
        value_maps.append(permutation)
    new_answer = [0] * n
    for old in range(n):
        new_answer[variable_map[old]] = value_maps[old][inst["answer"][old]]
    new_constraints = []
    for old_left, old_right, raw in inst["constraints"]:
        old_mask = int(raw, 16)
        mapped = 0
        for a in range(d):
            for b in range(d):
                if _allowed(old_mask, d, a, b):
                    na = value_maps[old_left][a]
                    nb = value_maps[old_right][b]
                    mapped |= 1 << (na * d + nb)
        left, right = variable_map[old_left], variable_map[old_right]
        if rng.randrange(2):
            left, right = right, left
            mapped = _transpose_mask(mapped, d)
        new_constraints.append([left, right, _mask_to_hex(mapped, d)])
    rng.shuffle(new_constraints)
    out = {key: value for key, value in inst.items() if key not in ("constraints", "answer")}
    out["constraints"] = new_constraints
    out["answer"] = new_answer
    return out


def _answer_size(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer)
    elements = len(answer) if isinstance(answer, list) else 1
    return len(blob), (len(blob) + 3) // 4, elements


def _find_bad_swap(inst: dict) -> list[int] | None:
    answer = list(inst["answer"])
    for left in range(len(answer)):
        for right in range(left + 1, len(answer)):
            if answer[left] == answer[right]:
                continue
            trial = list(answer)
            trial[left], trial[right] = trial[right], trial[left]
            if not verify(inst, trial)[0]:
                return trial
    return None


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "2103.06649",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])
    swapped = _find_bad_swap(shipping)
    corruptions = {
        "drop_one": list(shipping["answer"][:-1]),
        "swap_two": swapped,
        "duplicate_one": list(shipping["answer"]) + [shipping["answer"][0]],
        "empty": [],
        "out_of_range": [shipping["d"]] + list(shipping["answer"][1:]),
    }
    corruption_reasons = {}
    corruption_ok = swapped is not None
    for name, candidate in corruptions.items():
        if candidate is None:
            corruption_reasons[name] = "no rejecting swap found"
            corruption_ok = False
            continue
        ok, why = verify(shipping, candidate)
        corruption_reasons[name] = why
        corruption_ok = corruption_ok and not ok
    corruption_ok = corruption_ok and len(set(corruption_reasons.values())) == len(corruption_reasons)
    report["G2_rejects_corruption"] = {
        "pass": corruption_ok,
        "reasons": corruption_reasons,
        "distinct_reasons": len(set(corruption_reasons.values())),
    }

    wire = json.dumps(shipping["answer"])
    response = f"I propagated the binary constraints.\n```json\n<answer>{wire}</answer>\n```"
    parsed = parse_answer(response)
    example_matches = _ANSWER_RE.findall(render(shipping))
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and bool(example_matches) and parse_answer(f"<answer>{example_matches[-1]}</answer>") is not None,
        "model_style_round_trip": parsed == shipping["answer"],
        "renderer_example_parses": bool(example_matches) and parse_answer(f"<answer>{example_matches[-1]}</answer>") is not None,
    }

    guess_rng = random.Random(20260905)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        hits += verify(shipping, random_candidate(shipping, guess_rng))[0]
    guess_wall = time.perf_counter() - guess_started
    density = hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "observed_probability": density,
        "structure_aware_space": search_space(shipping),
        "wall_clock_sec": round(guess_wall, 6),
    }

    mac_answer, mac_nodes, mac_wall = _mac_attack(shipping)
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and mac_answer is None and mac_nodes == _MAC_NODE_BUDGET,
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction": density,
        "baseline_wall_clock_sec": round(mac_wall, 6),
        "baseline_nodes": mac_nodes,
        "baseline_node_budget": _MAC_NODE_BUDGET,
        "baseline_attack_solved": mac_answer is not None,
        "demo_exact_solution_count": enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"])),
    }

    attack_results = {
        "outlier_permitted_tuple_marginal": {"successes": 0, "attempts": 0},
        "greedy_high_degree_local_support": {"successes": 0, "attempts": 0},
        "random_restart_min_conflicts_16x6n": {"successes": 0, "attempts": 0, "iterations": 0},
        "standard_MAC_MRV_LCV_5000_nodes": {"successes": 0, "attempts": 0, "nodes": 0, "wall_clock_sec": 0.0},
    }
    for seed in _ATTACK_SEEDS:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = [
            ("outlier_permitted_tuple_marginal", _outlier_marginal_attack(inst)),
            ("greedy_high_degree_local_support", _greedy_support_attack(inst)),
        ]
        local, iterations = _min_conflicts_attack(inst, random.Random(seed ^ 0x5EED))
        candidates.append(("random_restart_min_conflicts_16x6n", local))
        attack_results["random_restart_min_conflicts_16x6n"]["iterations"] += iterations
        mac, nodes, wall = _mac_attack(inst)
        candidates.append(("standard_MAC_MRV_LCV_5000_nodes", mac))
        attack_results["standard_MAC_MRV_LCV_5000_nodes"]["nodes"] += nodes
        attack_results["standard_MAC_MRV_LCV_5000_nodes"]["wall_clock_sec"] += wall
        for name, candidate in candidates:
            attack_results[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1
    attack_results["standard_MAC_MRV_LCV_5000_nodes"]["wall_clock_sec"] = round(
        attack_results["standard_MAC_MRV_LCV_5000_nodes"]["wall_clock_sec"], 6
    )
    all_failed = all(result["successes"] == 0 and result["attempts"] >= 8 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(seed=99, **doubled_params)
    doubled_build_wall = time.perf_counter() - doubled_started
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_build_wall_clock_sec": round(doubled_build_wall, 6),
        "doubled_verify_reason": doubled_why,
    }

    invariant = 0
    carried = 0
    distinct_keys = []
    for seed in range(20):
        base = make_instance(seed=12000 + seed, **DIFFICULTY["easy"])
        transformed = _relabel_for_test(base, random.Random(99000 + seed))
        invariant += canonical_key(base) == canonical_key(transformed)
        carried += verify(transformed, transformed["answer"])[0]
        distinct_keys.append(canonical_key(base))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(set(distinct_keys)) == 20,
        "invariant_relabellings": invariant,
        "relabelled_witnesses_verify": carried,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "tested_symmetries": [
            "constraint permutation",
            "variable permutation",
            "independent per-variable domain permutation",
            "ordered-scope reversal with relation transpose",
            "their composition",
        ],
    }

    answer_chars, answer_tokens, answer_elements = _answer_size(shipping["answer"])
    arms = {
        key: dict(G9_ORACLE_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else 0.0
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else 0.0
    intended_ops = shipping["n"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
