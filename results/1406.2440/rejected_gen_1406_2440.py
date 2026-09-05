"""Retained rejected induced-matching generator attempt for arXiv:1406.2440.

The paper works with ordinary finite graphs and defines an induced matching as
a set of vertex-disjoint edges with no extra edge between their endpoints.
This module constructs a bounded-degree graph from regular circulant blocks.
A hidden independent transversal of its core is sampled first; attaching one
private leaf to every core vertex turns that transversal into the requested
induced matching.  The witness is known by inverse generation, but the family
fails the Track B compression test documented in REJECTED.md.
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


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bounded-maximum-degree graph",
        "induced matching of pendant edges",
    ],
    "verification_operations": [
        "exact modular subtraction",
        "graph-edge membership",
        "endpoint-disjointness check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Locate the unique translation-equivariant cyclic run in each "
        "cross-group adjacency set so its phase becomes a vertex difference."
    ),
    "hardness_basis": (
        "Rejected Track B audit: the strongest translation-marker recovery is "
        "O(k p), not O(k^2 p); at the hard preset it inspects the same 1,008 "
        "listed residues as the purported compact route and then uses 17 modular "
        "operations (1,025 total, about 0.00011 s over eight seeds)."
    ),
    "max_answer_tokens": 32,
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
        "Exactly one pendant edge E(i,x) for every group i, written as the "
        "ordered JSON list [[0,x_0],...,[k-1,x_(k-1)]], with each residue "
        "x_i in {0,...,p-1}."
    ),
    "bounds": {
        "edge_count": "k (16 at every non-demo preset)",
        "group_order": "0 through k-1 exactly once",
        "residue_range": "0 through p-1",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 19, "groups": 3},
    "easy": {"n": 43, "groups": 16},
    "medium": {"n": 83, "groups": 16},
    "hard": {"n": 127, "groups": 16},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: Each cross-group forbidden set has one uniquely longest translation-equivariant cyclic run."
)
PLACEBO_HINT: str = (
    "Hint: Each cross-group forbidden set deserves one especially careful check against every condition."
)

# Replaced with transcript-owned measurements after the hardening runs.  Keeping
# the data here lets selftest remain deterministic and offline.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run_openrouter_403_key_limit",
}

NOTES = r"""
Definition and paper regime. Section 1 defines an induced matching as a set of
edges that are vertex-disjoint and have no graph edge joining two of them.  It
also states that computing the maximum is NP-hard even for bipartite subcubic
graphs.  Theorem 1 concerns a different regime: graphs without isolated
vertices and maximum degree at least 1000.  Its proof repeatedly deletes closed
neighborhoods and isolated vertices, and the paragraph immediately before
Section 2 says that this proof gives a polynomial-time algorithm for a matching
of the guaranteed size.  Thus that theorem cannot support a Track-A claim.

Paper object used here. The sharpness and high-girth constructions in Section 1
attach private pendant vertices to a core graph and relate induced matchings to
independent core vertices.  This module stays with those native graph objects.
It has k clique groups of core vertices and one private leaf at each core
vertex.  A size-k independent core transversal gives k pendant edges; clique
groups also show that no larger core transversal exists.

Generation and certificate. A modulus p and core coordinates a_i are sampled
first.  For each group pair the generator independently samples a forbidden
half-set B_ij whose unique longest cyclic run starts at residue 1, then sets
F_ij = B_ij + a_j - a_i.  Because 0 is excluded from every B_ij, the vertices
(i,a_i) have no cross edges.  Their private leaf edges are the carried
certificate.  Every F_ij has the same size, so every core vertex has degree
p+(k-1)|B_ij|; plants and decoys are degree-identical.  make_instance never
calls the recovery routine.

Track-B audit. The original attempted claim compared an O(k^2 p) algorithm
that needlessly scanned every pair set with a route that read only the star
pairs F_0j, and it failed to count the latter's scans.  The strongest exact
recovery reads the same k sets as the supposed shortcut: the k-1 star sets and
F_12.  At the hard preset those sets contain 1,008 displayed residues.  Both
routes must inspect those residues to locate the cyclic runs, followed by 17
modular operations.  The measured routes are therefore the same O(k p)
procedure, and the corrected 1,025-operation intended route also exceeds the
G9(c) cap of 300.  This retained module is rejected evidence, not a shippable
family.

Attacks. The core graph is exactly regular, defeating degree outliers.  The
first planted displacement is fixed so that the public all-zero and the
run-anchor-without-phase-correction candidates contain a certified conflict.
The panel also runs smallest-compatible greedy selection and 256 random
restarts.  All are verified rather than compared with the planted answer.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(7, value)
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _marker_anchor(values, modulus):
    """Return (start, length) of the unique longest cyclic occupied run."""
    present = set(values)
    if not present or len(present) == modulus:
        return None
    runs = []
    for start in present:
        if (start - 1) % modulus in present:
            continue
        length = 1
        while (start + length) % modulus in present:
            length += 1
        runs.append((length, start))
    largest = max(length for length, _ in runs)
    winners = [start for length, start in runs if length == largest]
    if len(winners) != 1:
        return None
    return winners[0], largest


def _sample_base(modulus, rng):
    """An aperiodic half-set excluding 0 with one conspicuous occupied run."""
    size = modulus // 2
    marker_run = max(4, min(17, modulus // 8))
    forced = set(range(1, marker_run + 1)) | {modulus - 1}
    # Residues 0 and marker_run+1 are absent, so the marked run has boundaries.
    pool = list(range(marker_run + 2, modulus - 1))
    for _ in range(10_000):
        chosen = set(rng.sample(pool, size - len(forced))) | forced
        marked = _marker_anchor(chosen, modulus)
        if marked == (1, marker_run):
            return sorted(chosen)
    raise RuntimeError("could not sample a forbidden set with a unique marker run")


def _forbidden_map(inst):
    return {
        (record[0], record[1]): frozenset(record[2])
        for record in inst["forbidden_sets"]
    }


def _forbidden_masks(records, groups):
    masks = [[0] * groups for _ in range(groups)]
    for i, j, residues in records:
        mask = 0
        for value in residues:
            mask |= 1 << value
        masks[i][j] = mask
    return masks


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a regular core and its pendant induced matching."""
    groups = params.pop("groups", 16)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 19:
        raise ValueError("n must be an integer at least 19")
    if isinstance(groups, bool) or not isinstance(groups, int) or groups < 3:
        raise ValueError("groups must be an integer at least 3")

    # Primality is unnecessary: only the additive cyclic group is used.  Taking
    # p=n makes every strict increase of n strictly enlarge the candidate space.
    modulus = n
    rng = random.Random(seed)
    coordinates = [rng.randrange(modulus)]
    # This makes the all-zero public-order heuristic fail on F_01 because the
    # unshifted marker pattern contains -1 as well as its run beginning at +1.
    coordinates.append((coordinates[0] + 1) % modulus)
    coordinates.extend(rng.randrange(modulus) for _ in range(groups - 2))

    forbidden_sets = []
    for i in range(groups):
        for j in range(i + 1, groups):
            base = _sample_base(modulus, rng)
            shift = (coordinates[j] - coordinates[i]) % modulus
            residues = sorted((value + shift) % modulus for value in base)
            forbidden_sets.append([i, j, residues])

    answer = [[i, coordinates[i]] for i in range(groups)]
    forbidden_size = len(base)
    core_degree = modulus + (groups - 1) * forbidden_size
    vertex_count = 2 * groups * modulus
    edge_count = (
        groups * modulus
        + groups * modulus * (modulus - 1) // 2
        + groups * (groups - 1) // 2 * modulus * forbidden_size
    )
    return {
        "family": "regular-circulant pendant induced matching",
        "requested_n": n,
        "modulus": modulus,
        "groups": groups,
        "forbidden_size": forbidden_size,
        "forbidden_sets": forbidden_sets,
        "forbidden_masks": _forbidden_masks(forbidden_sets, groups),
        "vertex_count": vertex_count,
        "edge_count": edge_count,
        "maximum_degree": core_degree,
        "answer": answer,
    }


def render(inst) -> str:
    p = inst["modulus"]
    k = inst["groups"]
    rows = []
    for i, j, residues in sorted(inst["forbidden_sets"], key=lambda row: (row[0], row[1])):
        rows.append(f"F {i} {j}: " + ",".join(map(str, residues)))
    format_example = json.dumps([[i, 0] for i in range(k)], separators=(",", ":"))
    statement = f"""Find a size-{k} induced matching in the finite graph defined below.

An induced matching is a set of edges that (1) share no endpoint and (2) have no other graph edge joining an endpoint of one chosen edge to an endpoint of another.

All indices are 0-based. Arithmetic on residues is modulo p={p}, using representatives 0 through {p - 1}. There are k={k} groups. For every group i and residue x there are two vertices C(i,x) (a core vertex) and L(i,x) (its private leaf). The graph has exactly these edges:

1. E(i,x) = C(i,x)--L(i,x), for every i,x.
2. C(i,x)--C(i,y), for every fixed i and every x != y; thus each core group is a clique.
3. For i<j, C(i,x)--C(j,y) exactly when (y-x) mod p belongs to the listed set F_ij.

There are no other edges. The graph has {inst['vertex_count']} vertices, {inst['edge_count']} edges, and maximum degree {inst['maximum_degree']}. Every listed F_ij has {inst['forbidden_size']} residues.

Cross-group forbidden-residue sets:
{chr(10).join(rows)}

Return exactly {k} pendant edges E(i,x), one for each group i in increasing order. Encode E(i,x) as [i,x], so the answer must be the JSON list [[0,x_0],[1,x_1],...,[{k - 1},x_{k - 1}]]. Repetitions and residues outside 0..{p - 1} are forbidden. Order matters only for the required canonical group order.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the required shape (not necessarily a valid matching): <answer>{format_example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return value


def verify(inst, answer):
    k = inst["groups"]
    p = inst["modulus"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k:
        return False, f"expected exactly {k} pendant edges"
    if any(not isinstance(edge, list) or len(edge) != 2 for edge in answer):
        return False, "each pendant edge must be a two-integer list [i,x]"
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for edge in answer for value in edge
    ):
        return False, "group and residue entries must be integers"
    if len({tuple(edge) for edge in answer}) != k:
        return False, "the same pendant edge is repeated"
    for position, (group, _) in enumerate(answer):
        if group != position:
            return False, f"entry {position} must describe group {position}"
    for group, residue in answer:
        if not 0 <= residue < p:
            return False, f"residue for group {group} is outside 0..{p - 1}"

    masks = inst.get("forbidden_masks")
    if masks is None:
        masks = _forbidden_masks(inst["forbidden_sets"], k)
    for i in range(k):
        xi = answer[i][1]
        for j in range(i + 1, k):
            xj = answer[j][1]
            difference = (xj - xi) % p
            if (masks[i][j] >> difference) & 1:
                return False, (
                    f"core endpoints in groups {i} and {j} are joined "
                    f"(forbidden difference {difference})"
                )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the statement's canonical one-pendant-edge-per-group language."""
    return [[i, rng.randrange(inst["modulus"])] for i in range(inst["groups"])]


def search_space(inst):
    return inst["modulus"] ** inst["groups"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    total = 0
    p = inst["modulus"]
    for residues in itertools.product(range(p), repeat=inst["groups"]):
        candidate = [[i, residues[i]] for i in range(inst["groups"])]
        total += int(verify(inst, candidate)[0])
    return total


def _affine_signature(values, modulus):
    """Cheap set invariant under x -> unit*x+translation and reflection."""
    counts = [0] * modulus
    for left in values:
        for right in values:
            counts[(right - left) % modulus] += 1
    return tuple(sorted(counts[1:]))


def canonical_key(inst):
    signatures = sorted(
        _affine_signature(record[2], inst["modulus"])
        for record in inst["forbidden_sets"]
    )
    material = json.dumps(
        [inst["modulus"], inst["groups"], inst["forbidden_size"], signatures],
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("ascii")).hexdigest()


def escalate(params):
    clean = {key: value for key, value in params.items() if key != "_preset"}
    n = clean.get("n")
    groups = clean.get("groups", 16)
    if not isinstance(n, int):
        return None
    # The answer remains exactly `groups` pairs; only the residue haystack grows.
    return {"n": 2 * n + 1, "groups": groups}


def _reference_alignment(inst):
    """Strongest promise-aware recovery: scan only the needed marker sets."""
    p = inst["modulus"]
    k = inst["groups"]
    forbidden = _forbidden_map(inst)
    anchors = {}
    needed = [(0, j) for j in range(1, k)] + [(1, 2)]
    operations = 0
    for pair in needed:
        marker = _marker_anchor(forbidden[pair], p)
        # Count every listed residue that must be inspected to certify the
        # unique cyclic run.  This is also work the no-tool route must do.
        operations += len(forbidden[pair])
        if marker is None:
            return None, operations
        anchor, _ = marker
        anchors[pair] = anchor

    # If anchor_ij = (a_j-a_i)+c, one triangle exposes the common phase c.
    phase = (anchors[(0, 1)] + anchors[(1, 2)] - anchors[(0, 2)]) % p
    operations += 2
    candidate = [[0, 0]]
    for j in range(1, k):
        candidate.append([j, (anchors[(0, j)] - phase) % p])
        operations += 1
    return candidate, operations


def _attack_degree_outlier(inst):
    # Every core vertex has the same displayed degree, so public order breaks ties.
    return [[i, 0] for i in range(inst["groups"])]


def _attack_greedy_smallest(inst):
    p = inst["modulus"]
    k = inst["groups"]
    forbidden = _forbidden_map(inst)
    chosen = []
    for j in range(k):
        found = None
        for residue in range(p):
            if all(
                (residue - chosen[i]) % p not in forbidden[(i, j)]
                for i in range(j)
            ):
                found = residue
                break
        if found is None:
            chosen.extend(0 for _ in range(k - len(chosen)))
            break
        chosen.append(found)
    return [[i, chosen[i]] for i in range(k)]


def _attack_marker_without_phase(inst):
    """Use each run anchor directly, omitting its one-residue phase."""
    p = inst["modulus"]
    k = inst["groups"]
    forbidden = _forbidden_map(inst)
    answer = [[0, 0]]
    for j in range(1, k):
        anchor, _ = _marker_anchor(forbidden[(0, j)], p)
        answer.append([j, anchor])
    return answer


def _directed_forbidden(forbidden, old_i, old_j, modulus):
    if old_i < old_j:
        return forbidden[(old_i, old_j)]
    return frozenset((-value) % modulus for value in forbidden[(old_j, old_i)])


def _relabel_instance(inst, group_order, unit, translations):
    """Carry graph and witness through group permutation and affine coordinates."""
    p = inst["modulus"]
    k = inst["groups"]
    if sorted(group_order) != list(range(k)):
        raise ValueError("group_order must be a permutation")
    if math.gcd(unit, p) != 1 or len(translations) != k:
        raise ValueError("invalid affine relabelling")
    old_forbidden = _forbidden_map(inst)
    new_sets = []
    for a in range(k):
        for b in range(a + 1, k):
            directed = _directed_forbidden(
                old_forbidden, group_order[a], group_order[b], p
            )
            residues = sorted(
                (unit * value + translations[b] - translations[a]) % p
                for value in directed
            )
            # Deliberately reverse storage order for half the records: row order
            # and residue order are serialization, not graph structure.
            if (a + b) % 2:
                residues.reverse()
            new_sets.append([a, b, residues])
    new_sets.reverse()
    old_answer = {group: residue for group, residue in inst["answer"]}
    carried = [
        [new_i, (unit * old_answer[old_i] + translations[new_i]) % p]
        for new_i, old_i in enumerate(group_order)
    ]
    out = dict(inst)
    out["forbidden_sets"] = new_sets
    out["forbidden_masks"] = _forbidden_masks(new_sets, k)
    out["answer"] = carried
    return out


def _answer_atom_count(answer):
    if not isinstance(answer, list):
        return 0
    return sum(len(edge) if isinstance(edge, list) else 1 for edge in answer)


def selftest() -> dict:
    report = {}

    planted_ok = 0
    planted_total = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            planted_ok += int(verify(inst, inst["answer"])[0])
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total,
        "verified": planted_ok,
        "attempts": planted_total,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]
    corruptions = {
        "drop": base[:-1],
        "swap": [base[1], base[0]] + base[2:],
        "duplicate": base[:-1] + [base[0]],
        "empty": [],
        "out_of_range": [[0, shipping["modulus"]]] + base[1:],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(reasons) == len(corruption_results),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(base, separators=(",", ":"))
    realistic = (
        "The pendant endpoints are pairwise nonadjacent.\n"
        f"<answer>```json\n{wire}\n```</answer>\nThat is my final matching."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == base,
        "parsed_equals_answer": parsed == base,
        "json_native": json.loads(json.dumps(base)) == base,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(shipping),
        "candidate_space_bits": search_space(shipping).bit_length(),
        "prior": "uniform residue per required group; shape and pendant-edge rule enforced",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    t0 = time.perf_counter()
    reference_answer, reference_ops = _reference_alignment(shipping)
    reference_seconds = time.perf_counter() - t0
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6 and reference_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "demo_exact_solution_count": enumerate_all(demo),
        "demo_candidate_space": search_space(demo),
        "baseline_algorithm": "star-only translation-marker recovery",
        "baseline_wall_clock_seconds": round(reference_seconds, 6),
        "baseline_exact_operations": reference_ops,
        "baseline_verified": reference_ok,
    }

    attacks = {
        "degree_outlier_tie_break": {"successes": 0, "attempts": 8},
        "greedy_smallest_compatible": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "run_anchor_without_phase": {"successes": 0, "attempts": 8},
    }
    ref_successes = 0
    ref_operations = []
    ref_times = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_answers = {
            "degree_outlier_tie_break": _attack_degree_outlier(inst),
            "greedy_smallest_compatible": _attack_greedy_smallest(inst),
            "run_anchor_without_phase": _attack_marker_without_phase(inst),
        }
        for name, candidate in attack_answers.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        restart_rng = random.Random(seed ^ 0x5A17)
        restart_hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_hit = True
                break
        attacks["random_restart_256"]["successes"] += int(restart_hit)

        ref_start = time.perf_counter()
        recovered, operations = _reference_alignment(inst)
        ref_times.append(time.perf_counter() - ref_start)
        ref_operations.append(operations)
        ref_successes += int(recovered is not None and verify(inst, recovered)[0])

    all_attacks_failed = all(
        item["successes"] == 0 and item["attempts"] >= 8
        for item in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "star-only translation-marker recovery",
            "complexity": "O(k p) listed-residue inspections",
            "wall_clock_sec_mean": round(sum(ref_times) / len(ref_times), 6),
            "wall_clock_sec_max": round(max(ref_times), 6),
            "operations_mean": round(sum(ref_operations) / len(ref_operations)),
            "operations_max": max(ref_operations),
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"] + 1,
        groups=DIFFICULTY[SHIPPING_DIFFICULTY]["groups"],
        seed=2718,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["modulus"] > shipping["modulus"]
        and search_space(doubled) > search_space(shipping)
        and len(doubled["answer"]) == len(shipping["answer"]),
        "shipping_modulus": shipping["modulus"],
        "doubled_modulus": doubled["modulus"],
        "shipping_vertices": shipping["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "answer_edges_unchanged": len(doubled["answer"]),
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant = 0
    carried_valid = 0
    changed_serialization = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        relabel_rng = random.Random(9000 + seed)
        order = list(range(inst["groups"]))
        relabel_rng.shuffle(order)
        unit = relabel_rng.randrange(1, inst["modulus"])
        translations = [relabel_rng.randrange(inst["modulus"]) for _ in order]
        transformed = _relabel_instance(inst, order, unit, translations)
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        carried_valid += int(verify(transformed, transformed["answer"])[0])
        changed_serialization += int(
            inst["forbidden_sets"] != transformed["forbidden_sets"]
        )
    unrelated_keys = {
        canonical_key(
            make_instance(seed=2000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        )
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20
        and carried_valid == 20
        and changed_serialization == 20
        and len(unrelated_keys) == 20,
        "composed_relabellings_invariant": invariant,
        "carried_witnesses_valid": carried_valid,
        "serializations_actually_changed": changed_serialization,
        "unrelated_distinct_keys": len(unrelated_keys),
        "attempts_each": 20,
        "symmetries_tested": (
            "group permutation + independent group translations + global unit "
            "multiplication + row/residue reordering"
        ),
    }

    answer_chars = 0
    answer_atoms = 0
    for seed in range(40):
        answer = make_instance(
            seed=3000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )["answer"]
        answer_chars = max(
            answer_chars, len(json.dumps(answer, separators=(",", ":")))
        )
        answer_atoms = max(answer_atoms, _answer_atom_count(answer))
    answer_tokens = (answer_chars + 3) // 4
    k = shipping["groups"]
    # The no-tool route cannot treat locating the runs as free: it must inspect
    # the same k displayed sets as the strongest recovery algorithm.
    intended_operations = k * shipping["forbidden_size"] + 2 + (k - 1)
    arms = _G9_EVIDENCE["arms"]
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    else:
        hinted_minus_placebo = None
    within_caps = (
        answer_chars <= 2000
        and answer_atoms <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": _G9_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
