"""Rejected candidate: odd directed 5-cycles in succinct P6-free digraphs.

This module is grounded in the definitions, Lemma 3, and the proof setup of
arXiv:2212.02272.  It constructs an orientation of a blow-up of C5.  The
underlying graph is triangle-free and has no induced P6.  A directed odd cycle
is planted by composing exact affine permutations and a Chinese-remainder
identity; generation never searches the graph for the answer.

The module is deterministic in ``(n, seed, params)``, uses only the standard
library, and performs no file I/O, network access, or printing at import time.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


# Keep the repository helpers reachable when harden.py imports this module from
# the result directory.  This finite-discrete family needs no gvlib operation,
# and remains standard-library-only when the helpers are absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices as _gv_exact_matrices  # noqa: F401
except ImportError:
    _gv_exact_matrices = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "succinctly represented oriented graph",
        "five independent vertex bags forming a blow-up of C5",
        "directed odd cycle",
    ],
    "verification_operations": [
        "exact modular affine evaluation",
        "integer rank comparison",
        "directed-edge lookup",
        "directed-cycle check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Cancel the inverse-paired affine mask, then recover the common hidden "
        "rank forced by cyclic monotonicity; without those changes of variables, "
        "a solver scans millions of possible ranks or the much larger graph."
    ),
    "hardness_basis": (
        "Track B: exhaustive common-rank scanning finds the cycle in O(N) "
        "modular tests (and explicit SCC/cycle search is O(N^2) on the "
        "five-bag graph); at the shipping preset the measured scan cost is "
        "recorded by selftest and G6, while the CRT-and-affine compact route "
        "uses fewer than 300 exact arithmetic operations."
    ),
    "max_answer_tokens": 20,
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
    "demo": {"n": 2, "mask_pairs": 0},
    "easy": {"n": 155, "mask_pairs": 20},
    "medium": {"n": 179, "mask_pairs": 22},
    "hard": {"n": 203, "mask_pairs": 24},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Each long affine mask carries a cancellation pattern among neighboring "
    "transformations around the bags' essential changes of coordinates."
)
PLACEBO_HINT = (
    "Each long affine list uses consistent modular conventions among neighboring "
    "transformations around the bags' proposed five-cycle."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered 5-tuple of global vertex identifiers, one from each "
        "successive bag, restricted to the N structure-aware candidates whose "
        "five decoded ranks agree; entries lie in 0..5N-1."
    ),
    "bounds": {
        "tuple_length": 5,
        "bags": 5,
        "max_n_parameter": 401,
        "max_inverse_mask_pairs": 24,
        "candidate_count": "N, the product of four instance primes",
    },
}

NOTES = r"""
Paper grounding and STEP 0.  Section 2 defines an oriented graph as loopless,
without parallel or antiparallel arcs; an H-free digraph excludes H as an
induced subdigraph; triangle-free means that the underlying graph has clique
number at most two; and a k-dicolouring partitions the vertices into acyclic
induced subdigraphs.  Theorem 1 proves that every induced-directed-P6-free,
triangle-free oriented graph has dichromatic number at most 382.  Lemma 3 says
that a digraph with no odd directed cycle is 2-dicolourable, and Section 4
starts the main proof from a shortest odd directed cycle.  The certificate in
this family is exactly such a finite odd directed cycle, checked arc by arc.

The discriminating certificate question.  The paper proves an existence bound,
not a hardness theorem, so a Track A claim would be unsupported.  Odd-cycle
detection is algorithmic: SCC decomposition plus the bipartiteness argument in
Lemma 3 is polynomial on explicit graphs.  On this succinct family, a still
stronger mechanical algorithm scans all N possible common ranks in O(N) tests;
the explicit graph has 5N vertices and 5N^2 edges.  This module therefore
declares Track B openly.  The compact route first notices cyclic monotonicity,
then combines four pairwise-coprime congruences and inverts five short affine
chains.  Its measured operation count is below the no-tool cap.

Construction and certificate.  The underlying graph is the blow-up of an
undirected C5: each bag is independent, consecutive bags are complete to one
another, and there are no other edges.  Its quotient has no triangle, and an
exhaustive six-position quotient check (included in selftest) shows that no
six vertices can induce P6.  Thus every orientation generated here is in the
paper's exact class.  Each bag label x is sent bijectively to a hidden rank by
a planted chain of affine permutations modulo N.  Unequal ranks orient an edge
from lower to higher rank.  At equal ranks, edge 0 points clockwise always and
edges 1..4 point clockwise precisely on four congruences.  Generation samples
the answer rank rho first and publishes its four residues.  The Chinese
remainder theorem makes rho their unique common solution.  Inverting the five
affine chains directly gives the planted vertices; no cycle-finding routine is
called during generation.

Why the cycle is unique.  A clockwise directed C5 would give five weak rank
inequalities in a closed chain, so all five ranks must agree; a counterclockwise
one has the reversed chain and again all ranks agree.  Clockwise equal-rank
ties satisfy all four congruences only at rho.  Counterclockwise ties are
impossible because edge 0 is always clockwise.  This also justifies the
structure-aware candidate language used by random_candidate: it samples one
common rank, not five unrelated vertex labels.

Attack hardening.  Affine coordinate maps independently relabel every bag, so
the planted labels are not positional outliers.  The degree-extreme attack,
the smallest-label greedy route, a random common-rank restart, and the obvious
one-congruence ansatz are all checked on eight shipping seeds.  The successful
O(N) exhaustive scan is reported separately as Track B's reference algorithm.
Canonicalization discards the affine label maps and minimizes the five tie
rules over all rotations and reflections of the C5; reflection also complements
tie directions.  Selftest carries witnesses through affine relabellings, bag
rotations, bag reflections, and their compositions.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_G4_SAMPLES = 250_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 100_000

# Filled from script-owned runs after the bare/hinted/placebo hardening passes.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _int_param(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int, forbidden: set[int]) -> int:
    candidate = max(2, value)
    while candidate in forbidden or not _is_prime(candidate):
        candidate += 1
    return candidate


def _factor_primes(n: int) -> list[int]:
    if n == 2:
        return [2, 3, 5, 7]
    result: list[int] = []
    used: set[int] = set()
    for index in range(4):
        prime = _next_prime(n + 8 * index, used)
        result.append(prime)
        used.add(prime)
    return result


def _apply_chain(chain: list[list[int]], value: int, modulus: int) -> int:
    for multiplier, shift in chain:
        value = (multiplier * value + shift) % modulus
    return value


def _invert_chain(chain: list[list[int]], value: int, modulus: int) -> int:
    for multiplier, shift in reversed(chain):
        value = (value - shift) * pow(multiplier, -1, modulus) % modulus
    return value


def _rule_true(rule: dict[str, Any], rank: int) -> bool:
    if rule["kind"] == "constant":
        base = bool(rule["value"])
    else:
        base = rank % rule["modulus"] == rule["residue"]
    return base if rule.get("polarity", 1) == 1 else not base


def _complement_rule(rule: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(rule)
    result["polarity"] = -int(result.get("polarity", 1))
    return result


def _candidate_for_rank(inst: dict, rank: int) -> list[int]:
    modulus = inst["rank_count"]
    return [
        bag * modulus
        + _invert_chain(inst["rank_maps"][bag], rank, modulus)
        for bag in range(5)
    ]


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Plant one odd directed cycle by affine and CRT identity composition."""
    n = _int_param("n", n, 2, 401)
    mask_pairs = _int_param(
        "mask_pairs", params.pop("mask_pairs", 8), 0, 24
    )
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    primes = _factor_primes(n)
    rank_count = math.prod(primes)

    # Inverse generation: rho is sampled first.  Its residues subsequently
    # define the unique tie rank at which the directed C5 exists.
    planted_rank = rng.randrange(rank_count)
    rules: list[dict[str, Any]] = [
        {"kind": "constant", "value": True, "polarity": 1}
    ]
    for prime in primes:
        rules.append({
            "kind": "congruence",
            "modulus": prime,
            "residue": planted_rank % prime,
            "polarity": 1,
        })

    unit_choices = [
        value for value in range(2, 32)
        if math.gcd(value, rank_count) == 1
    ]
    # A common identity mask: every adjacent pair composes to the identity,
    # but its numeric coefficients make that cancellation non-obvious.  It is
    # analyzed once on the intended route and mechanically evaluated for each
    # bag by the reference method.
    common_mask: list[list[int]] = []
    for _pair in range(mask_pairs):
        multiplier = rng.choice(unit_choices)
        if rng.randrange(2):
            multiplier = (-multiplier) % rank_count
        shift = rng.randrange(rank_count)
        inverse = pow(multiplier, -1, rank_count)
        common_mask.append([multiplier, shift])
        common_mask.append([inverse, (-inverse * shift) % rank_count])

    rank_maps: list[list[list[int]]] = []
    core_maps: list[list[int]] = []
    for _bag in range(5):
        if n == 2 and mask_pairs == 0:
            core = [1, 0]
        else:
            multiplier = rng.choice(unit_choices)
            if rng.randrange(2):
                multiplier = (-multiplier) % rank_count
            core = [multiplier, rng.randrange(rank_count)]
        core_maps.append(core)
        rank_maps.append(copy.deepcopy(common_mask) + [core[:]])

    inst = {
        "n_parameter": n,
        "rank_count": rank_count,
        "vertex_count": 5 * rank_count,
        "bag_count": 5,
        "mask_pairs": mask_pairs,
        "rank_chain_length": 2 * mask_pairs + 1,
        "common_mask": common_mask,
        "core_maps": core_maps,
        "rank_maps": rank_maps,
        "tie_rules": rules,
        "factor_primes": primes,
        "answer": [],
    }
    inst["answer"] = _candidate_for_rank(inst, planted_rank)
    return inst


def _rule_text(index: int, rule: dict[str, Any]) -> str:
    if rule["kind"] == "constant":
        base = "true" if rule["value"] else "false"
    else:
        base = (
            f"r mod {rule['modulus']} = {rule['residue']}"
        )
    if rule.get("polarity", 1) == -1:
        base = f"NOT ({base})"
    return f"T_{index}(r) is {base}."


def render(inst: dict) -> str:
    """Render the complete succinct digraph and exact five-vertex output."""
    rank_count = inst["rank_count"]
    common_lines = "\n".join(
        f"H step {index}: x -> ({a}*x + {b}) mod {rank_count}"
        for index, (a, b) in enumerate(inst["common_mask"])
    ) or "H has no steps, so H(x)=x."
    core_text = "\n".join(
        f"B_{bag}: R_{bag}(x)=({a}*H(x)+{b}) mod {rank_count}"
        for bag, (a, b) in enumerate(inst["core_maps"])
    )
    rule_text = "\n".join(
        _rule_text(i, rule) for i, rule in enumerate(inst["tie_rules"])
    )
    example = ", ".join(str(i * rank_count) for i in range(5))

    statement = f"""Find an odd directed cycle in a (P6, triangle)-free oriented graph

There are {inst['vertex_count']} vertices, numbered 0 through
{inst['vertex_count'] - 1}.  They are split into five independent bags.  A
vertex v in bag B_i has the unique form v=i*N+x, where N={rank_count},
i is in {{0,1,2,3,4}}, and 0<=x<N.  Bag indices below are modulo 5.

The underlying undirected graph has every edge between B_i and B_(i+1),
and no other edges.  Thus it is a blow-up of the 5-cycle.  It is triangle-free
and contains no induced path on six vertices.  Every underlying edge receives
exactly one direction, so there are no antiparallel arcs.

Each bag has a hidden-rank permutation R_i.  First calculate the common mask
H(x) by applying all of its listed affine steps from top to bottom.  Then apply
the bag's final affine step.  Every intermediate value is reduced to its least
residue in 0..N-1.  No simplification of H is supplied.

{common_lines}

Final bag steps:
{core_text}

For x in B_i and y in B_(i+1), put r=R_i(x) and s=R_(i+1)(y).
If r<s, the arc is x -> y (clockwise from B_i to B_(i+1)).
If r>s, the arc is y -> x.  If r=s, the arc is clockwise exactly when
T_i(r) is true, according to these rules:
{rule_text}

Find five vertices [v_0,v_1,v_2,v_3,v_4], with v_i in B_i, which form a
directed 5-cycle.  Either v_0->v_1->v_2->v_3->v_4->v_0 or every one of
those five arrows may be reversed.  The output order is fixed by bag number,
not by the direction of traversal.  The five global vertex identifiers must
be decimal integers; repeats are forbidden (and impossible across distinct
bags).  No approximation is involved.

Give your final answer inside <answer></answer> tags, as five comma-separated
global vertex identifiers in bag order.  Format-only example:
<answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: object) -> object | None:
    """Parse one tagged five-integer tuple, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    pieces = [piece.strip() for piece in body.split(",")]
    if len(pieces) != 5 or any(not re.fullmatch(r"[+-]?\d+", p) for p in pieces):
        return None
    try:
        return [int(piece) for piece in pieces]
    except ValueError:
        return None


def _arc_forward(inst: dict, edge: int, left_x: int, right_x: int) -> bool:
    """Whether B_edge(left_x) -> B_edge+1(right_x) is an arc."""
    modulus = inst["rank_count"]
    left_rank = _apply_chain(inst["rank_maps"][edge], left_x, modulus)
    right_rank = _apply_chain(
        inst["rank_maps"][(edge + 1) % 5], right_x, modulus
    )
    if left_rank < right_rank:
        return True
    if left_rank > right_rank:
        return False
    return _rule_true(inst["tie_rules"][edge], left_rank)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check shape, bag membership, and the five directed arcs exactly."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of five vertex identifiers"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 5:
        return False, f"expected exactly 5 vertices, got {len(answer)}"
    modulus = inst["rank_count"]
    vertices: list[int] = []
    for position, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"position {position} is not an integer"
        if not 0 <= value < 5 * modulus:
            return False, f"vertex {value} at position {position} is out of range"
        bag = value // modulus
        if bag != position:
            return False, (
                f"position {position} must contain a vertex of B_{position}, "
                f"but vertex {value} lies in B_{bag}"
            )
        vertices.append(value)
    if len(set(vertices)) != 5:
        return False, "the five global vertex identifiers must be distinct"

    local = [value % modulus for value in vertices]
    directions = [
        _arc_forward(inst, edge, local[edge], local[(edge + 1) % 5])
        for edge in range(5)
    ]
    if all(directions) or not any(directions):
        return True, "ok"
    arrows = "".join("+" if direction else "-" for direction in directions)
    return False, f"the five arcs do not have one cyclic direction (pattern {arrows})"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the structure-aware common-rank language."""
    rank = rng.randrange(inst["rank_count"])
    return _candidate_for_rank(inst, rank)


def search_space(inst: dict) -> int | None:
    """There is one canonical candidate for each possible common rank."""
    return inst["rank_count"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded common-rank language only when it is small."""
    count = inst["rank_count"]
    if count > _ENUMERATION_CAP:
        return None
    return sum(
        1 for rank in range(count)
        if verify(inst, _candidate_for_rank(inst, rank))[0]
    )


def _rule_key(rule: dict[str, Any]) -> tuple[Any, ...]:
    polarity = int(rule.get("polarity", 1))
    if rule["kind"] == "constant":
        value = bool(rule["value"])
        if polarity == -1:
            value = not value
        return ("constant", int(value))
    return (
        "congruence",
        int(rule["modulus"]),
        int(rule["residue"]),
        polarity,
    )


def canonical_key(inst: dict) -> str:
    """Canonicalize label maps and all dihedral relabellings of the five bags."""
    rules = inst["tie_rules"]
    candidates: list[tuple[tuple[Any, ...], ...]] = []
    for shift in range(5):
        candidates.append(tuple(
            _rule_key(rules[(j + shift) % 5]) for j in range(5)
        ))
        candidates.append(tuple(
            _rule_key(_complement_rule(rules[(shift - j - 1) % 5]))
            for j in range(5)
        ))
    payload = json.dumps(
        [inst["rank_count"], min(candidates)],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow rank crowding while holding the five-vertex answer fixed."""
    current_n = int(params.get("n", 59))
    current_pairs = int(params.get("mask_pairs", 8))
    if current_n >= 251 and current_pairs >= 24:
        return None
    harder = dict(params)
    # Grow both the candidate haystack and a cancellable structural mask while
    # holding the answer at five vertices.
    harder["n"] = min(251, current_n + 24)
    harder["mask_pairs"] = min(24, current_pairs + 2)
    return harder


def _reference_scan(inst: dict) -> tuple[list[int] | None, int]:
    """Mechanical O(N) common-rank scan; count exact congruence tests."""
    operations = 0
    for rank in range(inst["rank_count"]):
        good = True
        for rule in inst["tie_rules"]:
            operations += 1
            if not _rule_true(rule, rank):
                good = False
                break
        if good:
            return _candidate_for_rank(inst, rank), operations
    return None, operations


def _attack_degree_extreme(inst: dict) -> list[int]:
    # Unequal-rank contributions make the last rank a minimum-outdegree choice.
    return _candidate_for_rank(inst, inst["rank_count"] - 1)


def _attack_greedy_smallest_label(inst: dict) -> list[int]:
    rank = _apply_chain(inst["rank_maps"][0], 0, inst["rank_count"])
    return _candidate_for_rank(inst, rank)


def _attack_random_restart(inst: dict, attack_seed: int,
                           restarts: int = 4096) -> list[int] | None:
    rng = random.Random(attack_seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_single_congruence(inst: dict) -> list[int]:
    rule = inst["tie_rules"][1]
    return _candidate_for_rank(inst, rule["residue"])


def _relabel_affinely(inst: dict, rng: random.Random) -> dict:
    """Relabel vertices independently inside every bag, carrying the answer."""
    result = copy.deepcopy(inst)
    modulus = inst["rank_count"]
    carried: list[int] = []
    for bag in range(5):
        while True:
            multiplier = rng.randrange(1, modulus)
            if math.gcd(multiplier, modulus) == 1:
                break
        shift = rng.randrange(modulus)
        inverse = pow(multiplier, -1, modulus)
        premap = [inverse, (-inverse * shift) % modulus]
        result["rank_maps"][bag] = [premap] + result["rank_maps"][bag]
        old_x = inst["answer"][bag] % modulus
        new_x = (multiplier * old_x + shift) % modulus
        carried.append(bag * modulus + new_x)
    result["answer"] = carried
    return result


def _rebag(inst: dict, shift: int, reflect: bool) -> dict:
    """Rotate or reflect the C5 bags and carry the five-cycle witness."""
    result = copy.deepcopy(inst)
    modulus = inst["rank_count"]
    old_for_new = [
        (shift - j) % 5 if reflect else (j + shift) % 5
        for j in range(5)
    ]
    result["rank_maps"] = [
        copy.deepcopy(inst["rank_maps"][old]) for old in old_for_new
    ]
    if reflect:
        result["tie_rules"] = [
            _complement_rule(inst["tie_rules"][(shift - j - 1) % 5])
            for j in range(5)
        ]
    else:
        result["tie_rules"] = [
            copy.deepcopy(inst["tie_rules"][(j + shift) % 5])
            for j in range(5)
        ]
    result["answer"] = [
        j * modulus + inst["answer"][old_for_new[j]] % modulus
        for j in range(5)
    ]
    return result


def _quotient_has_induced_p6() -> bool:
    """Exhaust the bag patterns of a hypothetical induced six-vertex path."""
    for code in range(5 ** 6):
        value = code
        bags = []
        for _ in range(6):
            bags.append(value % 5)
            value //= 5
        valid = True
        for i in range(6):
            for j in range(i + 1, 6):
                adjacent = (bags[i] - bags[j]) % 5 in (1, 4)
                if adjacent != (j == i + 1):
                    valid = False
                    break
            if not valid:
                break
        if valid:
            return True
    return False


def _egcd_steps(a: int, b: int) -> int:
    steps = 0
    while b:
        a, b = b, a % b
        steps += 1
    return steps


def _intended_route_operations(inst: dict) -> int:
    """Count modular arithmetic in the compact CRT/affine route."""
    operations = 0
    # Merge four CRT congruences.  Each merge uses one modular inverse, two
    # modular products, one subtraction, one addition, and reductions.
    accumulated = 1
    for prime in inst["factor_primes"]:
        operations += _egcd_steps(accumulated % prime, prime) + 7
        accumulated *= prime
    # Recognize each adjacent affine/inverse-affine pair in the shared mask.
    # The mask is common to all five bags, so this is done once, not five times.
    operations += 5 * inst.get("mask_pairs", 0)
    # Invert each remaining one-step bag coordinate change.
    modulus = inst["rank_count"]
    for multiplier, _shift in inst.get("core_maps", []):
        operations += _egcd_steps(multiplier, modulus) + 6
    return operations


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return a fully JSON-native measurement report."""
    report: dict[str, Any] = {
        "paper": "2212.02272",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all presets, several independent seeds.
    g1_attempts = 0
    g1_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    probe = make_instance(seed=12345, **shipping_params)
    planted = probe["answer"]
    modulus = probe["rank_count"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0], *planted[2:]],
        "duplicate": [*planted[:4], planted[0]],
        "empty": [],
        "out_of_range": [*planted[:2], 5 * modulus, *planted[3:]],
    }
    rejection_reasons: dict[str, str] = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(probe, candidate)
        rejection_reasons[name] = "ACCEPTED" if ok else reason
    all_rejected = all(reason != "ACCEPTED" for reason in rejection_reasons.values())
    distinct_reasons = len(set(rejection_reasons.values())) == len(rejection_reasons)
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct_reasons,
        "reasons": rejection_reasons,
        "distinct_reasons": distinct_reasons,
    }

    answer_body = ", ".join(str(value) for value in planted)
    model_response = (
        "The ranks close consistently.\n```text\n"
        f"<answer>{answer_body}</answer>\n```\n"
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(probe, parsed)[0],
        "parsed": parsed,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    guess_rng = random.Random(99173)
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(probe, random_candidate(probe, guess_rng))[0])
    density_elapsed = time.perf_counter() - density_start
    guess_rate = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_rate,
        "candidate_space": search_space(probe),
        "sampling_prior": "uniform over the N common-hidden-rank candidates",
    }

    # G6 is evaluated before G5 is finalized because its reference scan is the
    # Track B mechanical baseline whose real cost G5 must report.
    attack_results = {
        "outlier_minimum_degree": {"successes": 0, "attempts": 0},
        "greedy_smallest_label": {"successes": 0, "attempts": 0},
        "random_restart_4096": {"successes": 0, "attempts": 0},
        "single_congruence_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_times: list[float] = []
    reference_operations: list[int] = []
    reference_successes = 0
    failing_attack_elapsed = 0.0
    for offset in range(_ATTACK_SEEDS):
        inst = make_instance(seed=7000 + offset, **shipping_params)
        candidates = {
            "outlier_minimum_degree": _attack_degree_extreme(inst),
            "greedy_smallest_label": _attack_greedy_smallest_label(inst),
            "single_congruence_ansatz": _attack_single_congruence(inst),
        }
        restart_start = time.perf_counter()
        candidates["random_restart_4096"] = _attack_random_restart(
            inst, 90000 + offset, 4096
        )
        failing_attack_elapsed += time.perf_counter() - restart_start
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1

        scan_start = time.perf_counter()
        found, operations = _reference_scan(inst)
        reference_times.append(time.perf_counter() - scan_start)
        reference_operations.append(operations)
        if found is not None and verify(inst, found)[0]:
            reference_successes += 1

    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attack_results.values()
    )
    sorted_times = sorted(reference_times)
    sorted_operations = sorted(reference_operations)
    median_time = sorted_times[len(sorted_times) // 2]
    median_operations = sorted_operations[len(sorted_operations) // 2]
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exhaustive common-hidden-rank scan",
            "complexity": "O(N) rank candidates and at most 5N tie tests",
            "wall_clock_sec_median": round(median_time, 6),
            "wall_clock_sec_total_8": round(sum(reference_times), 6),
            "operations_median": median_operations,
            "operations_max": max(reference_operations),
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    demo = make_instance(seed=17, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_rate < 1e-6
            and demo_count == 1
            and reference_successes == _ATTACK_SEEDS
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_total": _G4_SAMPLES,
        "shipping_observed_solution_fraction": guess_rate,
        "shipping_density_wall_clock_sec": round(density_elapsed, 6),
        "constructed_exact_valid_answers": 1,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec_median": round(median_time, 6),
        "baseline_modular_tests_median": median_operations,
        "baseline_modular_tests_max": max(reference_operations),
        "failing_attack_wall_clock_sec_total_8": round(failing_attack_elapsed, 6),
        "failing_attack_restarts_total": 4096 * _ATTACK_SEEDS,
    }

    doubled = make_instance(
        n=min(401, shipping_params["n"] * 2),
        mask_pairs=shipping_params["mask_pairs"],
        seed=8181,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(probe),
        "shipping_candidate_count": search_space(probe),
        "doubled_candidate_count": search_space(doubled),
        "answer_atoms_before": _answer_atoms(probe["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "doubled_planted_verifies": doubled_ok,
    }

    invariance_checks = 0
    carried_witness_checks = 0
    invariance_failures: list[str] = []
    distinct_keys: list[str] = []
    for offset in range(20):
        inst = make_instance(seed=11000 + offset, **shipping_params)
        key = canonical_key(inst)
        distinct_keys.append(key)
        transforms = [
            _relabel_affinely(inst, random.Random(12000 + offset)),
            _rebag(inst, offset % 5, False),
            _rebag(inst, offset % 5, True),
        ]
        composed = _rebag(
            _relabel_affinely(inst, random.Random(13000 + offset)),
            (offset + 2) % 5,
            True,
        )
        transforms.append(composed)
        for number, transformed in enumerate(transforms):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                invariance_failures.append(f"seed {offset} transform {number}: key")
            if verify(transformed, transformed["answer"])[0]:
                carried_witness_checks += 1
            else:
                invariance_failures.append(
                    f"seed {offset} transform {number}: witness"
                )
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not invariance_failures
            and invariance_checks == 80
            and carried_witness_checks == 80
            and distinct_count == 20
        ),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_unrelated": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "independent affine relabelling inside bags",
            "cyclic bag rotation",
            "bag reflection with tie-direction complement",
            "composed affine relabelling and reflection",
        ],
        "failures": invariance_failures,
    }

    answer_blob = json.dumps(probe["answer"], separators=(",", ":"))
    route_ops = max(
        _intended_route_operations(make_instance(seed=14000 + i, **shipping_params))
        for i in range(20)
    )
    arms = {
        name: dict(_ORACLE_EVIDENCE[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": (
            len(answer_blob) <= 2000
            and _answer_atoms(probe["answer"]) <= 256
            and route_ops <= 300
        ),
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": _answer_atoms(probe["answer"]),
        "intended_route_operations": route_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["paper_regime_checks"] = {
        "underlying_triangle_free": True,
        "quotient_induced_p6_patterns": int(_quotient_has_induced_p6()),
        "oriented_no_antiparallel_arcs": True,
    }
    gating = [
        value["pass"] for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_passed"] = bool(gating) and all(gating)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
