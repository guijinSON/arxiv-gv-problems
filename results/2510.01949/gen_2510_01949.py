"""Self-contained problem generator for arXiv:2510.01949.

The paper studies perfect matchings whose pairwise unions are Hamilton cycles.
Section 7 represents a perfect matching of K_{n,n} by a permutation.  This
module inverse-generates a cyclically structured collection of such matchings
and asks for one more matching that is Hamilton-compatible with every given
one.  The planted permutation is composed before the displayed instance is
assembled; no instance is solved during generation.
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
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "perfect matchings of a complete balanced bipartite graph",
        "permutations representing bipartite perfect matchings",
        "alternating Hamilton cycles",
    ],
    "verification_operations": [
        "permutation length and bijectivity checks",
        "exact inverse-permutation lookup",
        "exact alternating-cycle traversal",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that the relative matching permutations lie in one hidden "
        "cyclic translation action and use the required edge to select its "
        "coset element; without that symmetry one must search for a permutation "
        "satisfying many simultaneous one-cycle constraints."
    ),
    "hardness_basis": (
        "Track B: Section 7, Theorem 7.4 makes uniform permutation sampling "
        "an expected Theta_k(n^k)-trial algorithm for fixed k, while the "
        "shipping cyclic-coset normal-form algorithm is O(n^2+k*n) and measured "
        "9,029 lookups per instance (0.0025 seconds total over eight); recognizing "
        "one relative cycle and locating the required edge takes 295 lookups."
    ),
    "max_answer_tokens": 42,
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

# n is the size of each bipartition.  make_instance advances it to the next
# odd prime.  k is the number of constraints; it grows the haystack without
# changing the answer shape for a fixed n.
DIFFICULTY = {
    "demo": {"n": 7, "k": 4},
    "easy": {"n": 59, "k": 23},
    "medium": {"n": 59, "k": 27},
    "hard": {"n": 59, "k": 31},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Regard the relative matching permutations as elements of one hidden "
    "cyclic translation action."
)
PLACEBO_HINT = (
    "Hint: Keep the two vertex classes distinct while tracing every required "
    "alternating cycle."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One JSON list P of length n containing every integer 0,...,n-1 "
        "exactly once, with the displayed required edge fixed; P[i]=j denotes "
        "the matching edge (L_i,R_j)."
    ),
    "bounds": {
        "length": "n",
        "entries": "0 <= P[i] < n",
        "all_distinct": True,
        "candidate_count": "(n-1)!",
        "atomic_elements": "n",
    },
}

# Replaced after the three script-owned oracle runs.  These values are evidence,
# not inputs to any gated local check except the separately measured size caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition: Section 7 says that a perfect matching M of K_{n,n} is represented
by a permutation pi_M, and that Hamilton compatibility is a one-cycle condition
on the relative permutations.  Theorem 7.3 is the bipartite existence theorem;
Theorem 7.4 counts compatible matchings under its parity and small-overlap
conditions.  This module hands the solver precisely those permutation-valued
matchings and checks the alternating cycles directly.

What is easy: Section 1 states that k=2 in the non-bipartite problem is greedy,
and Section 7 notes that k=2 in the random bipartite problem is just Hamilton
cycle search.  We therefore use k>=4.  More importantly, Theorem 7.4 counts
Theta_k(n^(1/2-k)(n/e)^n) compatible permutations.  Dividing by n! shows that
uniform permutation sampling succeeds with probability Theta_k(n^-k), hence is
expected polynomial for every fixed k.  That fact rules out Track A and is why
the module declares Track B.

Construction: choose independent hidden coordinate orders for the left and
right classes.  The matching indexed by a in Z_n sends hidden coordinate x to
x+a.  For prime n, the relative permutation for two different indices is a
nonzero translation and therefore one n-cycle, so every pair of distinct
constructed matchings has Hamiltonian union.  The target index and given indices
are sampled exchangeably without replacement, and one target edge is published
to select the desired missing coset element.  Thus the certificate is known by
composition before the constraints are emitted, never by solving the instance.

Mechanical and compact routes: a distribution-aware exact reference constructs
the cyclic coset generated by a relative permutation, enumerates all n powers,
classifies every supplied matching, and verifies a missing coset element.  The
paper's uniform sampler is a slower expected-polynomial fallback for fixed k.
The compact route uses any two displayed permutations as a cyclic coordinate
frame, locates the published edge in that frame, and writes the selected coset
element: five length-n passes, 5n exact lookups.  The shipping n=59 route is
therefore 295 operations, while the measured reference cost is in selftest.

Attacks: labels are independently shuffled, and target and given translation
indices come from the same distribution, so coordinate magnitude and fixed
permutation patterns carry no answer signal.  The panel tries a row-wise
outlier/avoidance assignment, a no-backtracking cycle-avoiding greedy pass,
uniform random permutations conditioned on the required edge, and the obvious
single-step forward/backward extrapolations from the first displayed pair.

Canonicalization: arbitrary left and right vertex relabellings conjugate the
relative permutations, swapping the two bipartitions inverts them, and input
reordering changes no constraint.  canonical_key recovers every affine
normalization of the cyclic index set and chooses the least one.  The selftest
checks all of those symmetries, their composition, carried witnesses, and
twenty unrelated exponent sets.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


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


def _next_odd_prime(value: int) -> int:
    q = max(7, int(value))
    if q % 2 == 0:
        q += 1
    while not _is_prime(q):
        q += 2
    return q


def _inverse(perm: list[int]) -> list[int]:
    out = [0] * len(perm)
    for i, value in enumerate(perm):
        out[value] = i
    return out


def _is_one_cycle_relative(candidate: list[int], inv_matching: list[int]) -> bool:
    """Whether x -> inv_matching[candidate[x]] is one spanning cycle."""
    n = len(candidate)
    current = 0
    for steps in range(1, n + 1):
        current = inv_matching[candidate[current]]
        if current == 0:
            return steps == n
    return False


def make_instance(n: int, seed: int = 0, k: int = 15, **params) -> dict:
    """Inverse-generate compatible permutation matchings over a hidden Z_p.

    The target and given translation indices are sampled without replacement.
    A required target edge distinguishes the desired missing cyclic-coset
    element without making its partner permutation a per-row outlier.
    """
    size = _next_odd_prime(n)
    k = int(k)
    if not 4 <= k <= size - 1:
        raise ValueError("k must satisfy 4 <= k <= p-1")

    rng = random.Random(seed)
    left_hidden = list(range(size))
    right_label = list(range(size))
    rng.shuffle(left_hidden)
    rng.shuffle(right_label)

    indices = list(range(size))
    rng.shuffle(indices)
    target_index = indices[0]
    given_indices = indices[1:k + 1]

    def matching(shift: int) -> list[int]:
        return [right_label[(left_hidden[x] + shift) % size]
                for x in range(size)]

    # Choose a presentation order whose first pair does not reveal the target
    # through a single forward or backward extrapolation.  This reorders the
    # exchangeably sampled set; it does not alter the mathematical instance.
    first_pair = None
    for a in given_indices:
        for b in given_indices:
            if a != b and target_index not in {
                    (2 * b - a) % size, (2 * a - b) % size}:
                first_pair = (a, b)
                break
        if first_pair is not None:
            break
    if first_pair is None:  # defensive only in the supported k <= p-1 regime
        first_pair = (given_indices[0], given_indices[1])
    rest = [value for value in given_indices if value not in first_pair]
    rng.shuffle(rest)
    ordered_indices = [first_pair[0], first_pair[1]] + rest

    matchings = [matching(index) for index in ordered_indices]
    answer = matching(target_index)
    required_left = rng.randrange(size)
    required_right = answer[required_left]
    inverse_matchings = [_inverse(p) for p in matchings]
    return {
        "n": size,
        "k": k,
        "matchings": matchings,
        "required_edge": [required_left, required_right],
        "_inverse_matchings": inverse_matchings,
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    rows = "\n".join(
        f"M{index:02d}: " + " ".join(map(str, matching))
        for index, matching in enumerate(inst["matchings"])
    )
    statement = f"""HAMILTON-COMPATIBLE BIPARTITE PERFECT MATCHING

The complete balanced bipartite graph K_{{{n},{n}}} has left vertices
L_0,...,L_{n - 1} and right vertices R_0,...,R_{n - 1}.  A perfect matching
is represented by a permutation P of 0,...,{n - 1}: its edge incident with
L_i is (L_i,R_{{P[i]}}).

Below are {inst['k']} given perfect matchings.  Each row is one permutation in
left-vertex order.  The row order has no mathematical significance.

{rows}

Find one more perfect matching P such that, for every displayed M_j, the union
of P and M_j is one Hamilton cycle through all {2 * n} vertices.  Equivalently,
start at any left vertex, alternately follow its P edge to the right and the
M_j edge backwards to the left: you must return to the start only after every
left vertex has been visited.  A shared edge is a 2-cycle and is invalid.

The new matching must also contain the required edge
(L_{inst['required_edge'][0]},R_{inst['required_edge'][1]}), meaning
P[{inst['required_edge'][0]}] = {inst['required_edge'][1]}.

Your answer must be one JSON list of exactly {n} integers.  It must contain
each integer from 0 through {n - 1} exactly once; entry i is P[i].  Indices are
0-based, order matters, and repeats are forbidden.

Give your final answer inside <answer></answer> tags as that JSON list.
Example shape: <answer>[2,0,3,1,...]</answer>
Do not use the ellipsis in a real answer.  Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        payload = match.group(1).strip()
    else:
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
        payload = fence.group(1).strip() if fence else text.strip()
        start, end = payload.find("["), payload.rfind("]")
        if start < 0 or end < start:
            return None
        payload = payload[start:end + 1]
    payload = re.sub(r"^```(?:json)?\s*|\s*```$", "", payload,
                     flags=re.I | re.S).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer) -> tuple[bool, str]:
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"answer has fewer than {n} entries"
    if len(answer) > n:
        return False, f"answer has more than {n} entries"
    if any(type(value) is not int for value in answer):
        return False, "every entry must be an integer"
    for index, value in enumerate(answer):
        if not 0 <= value < n:
            return False, f"entry {index} is outside 0..{n - 1}"
    seen = set()
    for value in answer:
        if value in seen:
            return False, f"right vertex {value} is repeated"
        seen.add(value)

    required_left, required_right = inst["required_edge"]
    if answer[required_left] != required_right:
        return False, (
            f"required edge (L_{required_left},R_{required_right}) is missing"
        )

    inverses = inst.get("_inverse_matchings")
    if inverses is None:
        inverses = [_inverse(p) for p in inst["matchings"]]
    for index, inv_matching in enumerate(inverses):
        if not _is_one_cycle_relative(answer, inv_matching):
            return False, (
                f"union with M{index:02d} closes before visiting all vertices"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    n = inst["n"]
    required_left, required_right = inst["required_edge"]
    candidate = [-1] * n
    candidate[required_left] = required_right
    left = [x for x in range(n) if x != required_left]
    right = [x for x in range(n) if x != required_right]
    rng.shuffle(right)
    for x, value in zip(left, right):
        candidate[x] = value
    return candidate


def search_space(inst: dict) -> int | None:
    return math.factorial(inst["n"] - 1)


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if math.factorial(n - 1) > 500_000:
        return None
    required_left, required_right = inst["required_edge"]
    left = [x for x in range(n) if x != required_left]
    right = [x for x in range(n) if x != required_right]
    total = 0
    for tail in itertools.permutations(right):
        candidate = [-1] * n
        candidate[required_left] = required_right
        for x, value in zip(left, tail):
            candidate[x] = value
        if verify(inst, candidate)[0]:
            total += 1
    return total


def _cycle_coordinates(tau: list[int]) -> list[int] | None:
    """Coordinates of a one-cycle tau, anchored at displayed left vertex 0."""
    n = len(tau)
    coord = [-1] * n
    x = 0
    for t in range(n):
        if coord[x] != -1:
            return None
        coord[x] = t
        x = tau[x]
    return coord if x == 0 else None


def _normalized_signature(inst: dict, i: int, j: int):
    """Return given and required-edge exponents in basis i=0,j=1."""
    matchings = inst["matchings"]
    n = len(matchings[0])
    inv_base = _inverse(matchings[i])
    tau = [inv_base[value] for value in matchings[j]]
    coord = _cycle_coordinates(tau)
    if coord is None:
        return None
    exponents = []
    for matching in matchings:
        first_image = inv_base[matching[0]]
        shift = coord[first_image]
        for x in range(n):
            image = inv_base[matching[x]]
            if coord[image] != (coord[x] + shift) % n:
                return None
        exponents.append(shift)
    required_left, required_right = inst["required_edge"]
    target_image = inv_base[required_right]
    target_shift = (coord[target_image] - coord[required_left]) % n
    return tuple(sorted(exponents)), target_shift


def canonical_key(inst: dict) -> str:
    """Canonical cyclic-index set under relabelling and input reordering."""
    matchings = inst["matchings"]
    signatures = []
    for i in range(len(matchings)):
        for j in range(len(matchings)):
            if i == j:
                continue
            sig = _normalized_signature(inst, i, j)
            if sig is not None:
                signatures.append(sig)
    if signatures:
        best_given, best_target = min(signatures)
        payload = [inst["n"], list(best_given), best_target]
    else:
        # This branch is not used by generated instances.  It remains a strong
        # relabelling invariant for defensive calls on malformed external data.
        cycle_types = []
        for i in range(len(matchings)):
            inv = _inverse(matchings[i])
            for j in range(i + 1, len(matchings)):
                rel = [inv[value] for value in matchings[j]]
                unseen = set(range(inst["n"]))
                lengths = []
                while unseen:
                    x = next(iter(unseen))
                    length = 0
                    while x in unseen:
                        unseen.remove(x)
                        length += 1
                        x = rel[x]
                    lengths.append(length)
                cycle_types.append(sorted(lengths))
        payload = [inst["n"], sorted(cycle_types)]
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = _next_odd_prime(int(params.get("n", 59)))
    k = int(params.get("k", 15))
    if k + 4 <= n - 1:
        return {"n": n, "k": k + 4}
    # Increasing n past 59 makes the five-pass intended route exceed 300 exact
    # lookups.  The family can grow, but not under the current output/effort cap.
    return "cap_bound"


# ---------------------------------------------------------------------------
# Attacks and the Track-B reference algorithm

def _row_avoidance_attack(inst: dict) -> list[int] | None:
    n = inst["n"]
    forbidden = [set(matching[x] for matching in inst["matchings"])
                 for x in range(n)]
    required_left, required_right = inst["required_edge"]
    candidate = [-1] * n
    candidate[required_left] = required_right
    unused = set(range(n)) - {required_right}
    for x in [value for value in range(n) if value != required_left]:
        choices = sorted(unused - forbidden[x])
        if not choices:
            choices = sorted(unused)
        if not choices:
            return None
        candidate[x] = choices[0]
        unused.remove(choices[0])
    return candidate


def _would_close_partial(nxt: list[int], x: int, y: int) -> bool:
    z = y
    while z != -1:
        if z == x:
            return True
        z = nxt[z]
    return False


def _greedy_cycle_avoid_attack(inst: dict) -> list[int] | None:
    """Paper-style greedy pass, deliberately with no backtracking/absorber."""
    n = inst["n"]
    inverses = inst["_inverse_matchings"]
    nxt = [[-1] * n for _ in inverses]
    previous = [[-1] * n for _ in inverses]
    candidate = [-1] * n
    unused = set(range(n))
    required_left, required_right = inst["required_edge"]
    order = [required_left] + [x for x in range(n) if x != required_left]
    for depth, x in enumerate(order):
        selected = None
        selected_images = None
        rights = [required_right] if x == required_left else sorted(unused)
        for right in rights:
            if right not in unused:
                continue
            images = [inv[right] for inv in inverses]
            if any(previous[i][y] != -1 for i, y in enumerate(images)):
                continue
            if depth < n - 1 and any(
                    _would_close_partial(nxt[i], x, y)
                    for i, y in enumerate(images)):
                continue
            selected = right
            selected_images = images
            break
        if selected is None:
            return None
        candidate[x] = selected
        unused.remove(selected)
        for i, y in enumerate(selected_images):
            nxt[i][x] = y
            previous[i][y] = x
    return candidate


def _one_step_extrapolation_attack(inst: dict) -> list[list[int]]:
    """The forward and backward single extrapolations from the first pair."""
    a, b = inst["matchings"][:2]
    inv_a = _inverse(a)
    tau = [inv_a[value] for value in b]
    tau2 = [tau[tau[x]] for x in range(inst["n"])]
    inv_tau = _inverse(tau)
    return [
        [a[tau2[x]] for x in range(inst["n"])],
        [a[inv_tau[x]] for x in range(inst["n"])],
    ]


def _cyclic_coset_reference(inst: dict):
    """Exact distribution-aware normal-form algorithm, without the answer.

    It takes the first pair as a prospective cyclic basis, explicitly generates
    all n coset powers, confirms every given matching belongs to the coset, and
    verifies the first missing power.  Returns (candidate, operations).
    """
    matchings = inst["matchings"]
    n = inst["n"]
    operations = 0
    for i in range(len(matchings)):
        for j in range(len(matchings)):
            if i == j:
                continue
            base = matchings[i]
            inv_base = _inverse(base)
            operations += n
            tau = [inv_base[value] for value in matchings[j]]
            operations += n
            if _cycle_coordinates(tau) is None:
                operations += n
                continue
            operations += n

            current = list(range(n))
            power_to_matching = []
            signature_to_power = {}
            for exponent in range(n):
                candidate = tuple(base[current[x]] for x in range(n))
                operations += n
                power_to_matching.append(candidate)
                signature_to_power[candidate] = exponent
                current = [tau[current[x]] for x in range(n)]
                operations += n

            operations += len(matchings)
            if not all(tuple(row) in signature_to_power for row in matchings):
                continue
            supplied = {tuple(row) for row in matchings}
            required_left, required_right = inst["required_edge"]
            for candidate_tuple in power_to_matching:
                if candidate_tuple in supplied:
                    operations += 1
                    continue
                if candidate_tuple[required_left] != required_right:
                    operations += 1
                    continue
                candidate = list(candidate_tuple)
                ok, _ = verify(inst, candidate)
                operations += n * len(matchings)
                if ok:
                    return candidate, operations
    return None, operations


def _compact_candidate(inst: dict) -> tuple[list[int], int]:
    """Five-pass route: cyclic coordinates plus the required-edge shift."""
    n = inst["n"]
    a, b = inst["matchings"][:2]
    inv_a = _inverse(a)
    tau = [inv_a[value] for value in b]
    coord = _cycle_coordinates(tau)
    if coord is None:
        return [], 5 * n
    vertex_at = _inverse(coord)
    required_left, required_right = inst["required_edge"]
    target_image = inv_a[required_right]
    shift = (coord[target_image] - coord[required_left]) % n
    candidate = [a[vertex_at[(coord[x] + shift) % n]] for x in range(n)]
    return candidate, 5 * n


def _relabel_instance(inst: dict, left_old_to_new: list[int],
                      right_old_to_new: list[int], reorder: list[int],
                      swap_sides: bool = False) -> dict:
    n = inst["n"]
    transformed = []
    transformed_answer = None

    def carry(perm):
        out = [0] * n
        for old_left in range(n):
            out[left_old_to_new[old_left]] = right_old_to_new[perm[old_left]]
        return out

    rows = [carry(row) for row in inst["matchings"]]
    answer = carry(inst["answer"])
    required_left, required_right = inst["required_edge"]
    required_left = left_old_to_new[required_left]
    required_right = right_old_to_new[required_right]
    if swap_sides:
        rows = [_inverse(row) for row in rows]
        answer = _inverse(answer)
        required_left, required_right = required_right, required_left
    transformed = [rows[index] for index in reorder]
    transformed_answer = answer
    return {
        "n": n,
        "k": inst["k"],
        "matchings": transformed,
        "required_edge": [required_left, required_right],
        "_inverse_matchings": [_inverse(row) for row in transformed],
        "answer": transformed_answer,
    }


def _answer_elements(answer) -> int:
    if isinstance(answer, dict):
        return sum(_answer_elements(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_elements(value) for value in answer)
    return 1


def selftest() -> dict:
    report = {}

    # G1: all presets and several seeds, plus the actual composition identity.
    failures = []
    composition_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            compact, _ = _compact_candidate(inst)
            compact_ok = verify(inst, compact)[0] and compact == inst["answer"]
            composition_checks += 1
            if not ok or not compact_ok:
                failures.append({"preset": preset, "seed": seed,
                                 "verify": reason, "compact": compact_ok})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": 12,
        "composition_identity_checks": composition_checks,
        "failures": failures,
    }

    # G2: required corruptions, each forced to a different validation branch.
    small = make_instance(seed=314159, **DIFFICULTY["easy"])
    planted = small["answer"]
    swap = planted[:]
    required_left = small["required_edge"][0]
    swap_left = next(
        x for x in range(small["n"])
        if x != required_left
        and small["matchings"][0][x] != swap[x]
        and swap.index(small["matchings"][0][x]) != required_left
    )
    j = swap.index(small["matchings"][0][swap_left])
    swap[swap_left], swap[j] = swap[j], swap[swap_left]
    duplicate = planted[:]
    duplicate[0] = duplicate[1]
    corruptions = {
        "drop": planted[:-1],
        "swap": swap,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": planted[:-1] + [small["n"]],
    }
    corruption_results = {}
    reasons = []
    for name, value in corruptions.items():
        ok, reason = verify(small, value)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "corruptions": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: prose, a markdown fence inside the tags, whitespace, and JSON-native.
    payload = json.dumps(small["answer"], separators=(",", ":"))
    realistic = (
        "I traced the alternating cycles.\n\n"
        "<answer>\n```json\n" + payload + "\n```\n</answer>\n"
        "This is my final permutation."
    )
    round_trip = parse_answer(realistic) == small["answer"]
    json_native = json.loads(json.dumps(small["answer"])) == small["answer"]
    garbage_none = parse_answer("there is no list here") is None
    report["G3_round_trip"] = {
        "pass": round_trip and json_native and garbage_none,
        "prose_fence_tags_round_trip": round_trip,
        "answer_json_native": json_native,
        "garbage_returns_none": garbage_none,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=251001949, **ship_params)

    # G4 and shipping density for G5 use the exact stated permutation prior.
    guess_rng = random.Random(40401949)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(ship, guess_rng)
        if verify(ship, candidate)[0]:
            guess_hits += 1
    guess_wall = time.perf_counter() - guess_started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6 and guess_total >= 200_000,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": (
            "uniform over all (n-1)! permutations containing the required "
            "edge, with length, range, and bijectivity already enforced"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    # G6: attacks fail on eight shipping seeds; reference normal forms solve all.
    attack_seeds = [61000 + i for i in range(8)]
    attacks = {
        "outlier_row_avoidance": {"successes": 0, "attempts": 0},
        "greedy_cycle_avoid_no_backtracking": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0,
                               "candidates": 0},
        "in_context_one_step_extrapolation": {"successes": 0, "attempts": 0,
                                               "candidates": 0},
    }
    attack_started = time.perf_counter()
    reference_runs = []
    reference_operations = 0
    reference_wall = 0.0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **ship_params)

        candidate = _row_avoidance_attack(inst)
        attacks["outlier_row_avoidance"]["attempts"] += 1
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["outlier_row_avoidance"]["successes"] += 1

        candidate = _greedy_cycle_avoid_attack(inst)
        attacks["greedy_cycle_avoid_no_backtracking"]["attempts"] += 1
        if candidate is not None and verify(inst, candidate)[0]:
            attacks["greedy_cycle_avoid_no_backtracking"]["successes"] += 1

        rng = random.Random(70000 + seed)
        random_success = False
        for _ in range(256):
            candidate = random_candidate(inst, rng)
            attacks["random_restart_256"]["candidates"] += 1
            if verify(inst, candidate)[0]:
                random_success = True
                break
        attacks["random_restart_256"]["attempts"] += 1
        attacks["random_restart_256"]["successes"] += int(random_success)

        extrapolations = _one_step_extrapolation_attack(inst)
        attacks["in_context_one_step_extrapolation"]["candidates"] += len(
            extrapolations)
        attacks["in_context_one_step_extrapolation"]["attempts"] += 1
        if any(verify(inst, value)[0] for value in extrapolations):
            attacks["in_context_one_step_extrapolation"]["successes"] += 1

        started = time.perf_counter()
        reference_answer, operations = _cyclic_coset_reference(inst)
        elapsed = time.perf_counter() - started
        solved = reference_answer is not None and verify(inst, reference_answer)[0]
        reference_runs.append({
            "seed": seed,
            "solved": solved,
            "operations": operations,
            "wall_clock_sec": round(elapsed, 6),
        })
        reference_operations += operations
        reference_wall += elapsed

    attack_wall = time.perf_counter() - attack_started
    all_attacks_failed = all(value["successes"] == 0 for value in attacks.values())
    all_reference_solved = all(run["solved"] for run in reference_runs)
    reference_algorithm = {
        "name": "cyclic-coset permutation normal-form enumeration",
        "complexity": "O(n^2 + k*n) exact permutation lookups on this distribution",
        "operations": reference_operations,
        "average_operations": reference_operations / len(reference_runs),
        "wall_clock_sec": round(reference_wall, 6),
        "solves": f"{sum(run['solved'] for run in reference_runs)}/8, as expected",
        "per_seed": reference_runs,
        "paper_sampler": (
            "Theorem 7.4 implies expected Theta_k(n^k) uniform-permutation "
            "trials for fixed k"
        ),
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and all_reference_solved,
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    demo = make_instance(seed=202510, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and all_reference_solved,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_fraction": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "shipping_density_method": "uniform structure-aware permutation sampling",
        "enumerate_all_shipping": enumerate_all(ship),
        "demo_n": demo["n"],
        "demo_exact_solution_count": demo_count,
        "reference_algorithm_operations": reference_operations,
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "strongest_failing_attack": "random_restart_256 plus greedy cycle avoidance",
        "failing_attack_candidates": attacks["random_restart_256"]["candidates"],
        "failing_attack_panel_wall_clock_sec": round(attack_wall - reference_wall, 6),
    }

    # G7: larger n enlarges n! and the doubled instance still verifies.
    before = make_instance(n=29, k=11, seed=771)
    doubled = make_instance(n=58, k=11, seed=771)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            verify(before, before["answer"])[0]
            and doubled_ok
            and search_space(doubled) > search_space(before)
        ),
        "n_before": before["n"],
        "n_after_doubling_request": doubled["n"],
        "space_before": search_space(before),
        "space_after": search_space(doubled),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    # G8: left/right relabelling, input reorder, side swap, and composition.
    invariant_checks = 0
    carried_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=8000 + seed, **ship_params)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(9000 + seed)
        left1 = list(range(inst["n"]))
        right1 = list(range(inst["n"]))
        left2 = list(range(inst["n"]))
        right2 = list(range(inst["n"]))
        order1 = list(range(inst["k"]))
        order2 = list(range(inst["k"]))
        for seq in (left1, right1, left2, right2, order1, order2):
            rng.shuffle(seq)
        identity_order = list(range(inst["k"]))
        transformed = [
            _relabel_instance(inst, left1, right1, identity_order, False),
            _relabel_instance(inst, list(range(inst["n"])),
                              list(range(inst["n"])), order1, False),
            _relabel_instance(inst, left1, right1, order1, True),
        ]
        first = _relabel_instance(inst, left1, right1, order1, False)
        transformed.append(_relabel_instance(first, left2, right2, order2, True))
        for index, changed in enumerate(transformed):
            invariant_checks += 1
            carried_checks += 1
            if canonical_key(changed) != base_key:
                failures.append({"seed": seed, "transform": index,
                                 "kind": "key_changed"})
            if not verify(changed, changed["answer"])[0]:
                failures.append({"seed": seed, "transform": index,
                                 "kind": "carried_witness_failed"})
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "failures": failures,
        "transformations": [
            "independent arbitrary left/right vertex relabelling",
            "arbitrary reordering of the given matchings",
            "swap of the two bipartitions",
            "composition of relabelling, reordering, and side swap",
        ],
    }

    # G9(a,b) are recorded diagnostics.  Only the answer/effort caps are gated.
    answer_chars = len(json.dumps(ship["answer"], separators=(",", ":")))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_elements(ship["answer"])
    _, intended_operations = _compact_candidate(ship)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_complete": all(arms[name]["attempts"] >= 3 for name in arms),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
