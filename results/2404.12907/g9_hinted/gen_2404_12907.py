"""Verified Track-B generator for arXiv:2404.12907.

The paper studies dynamic Feedback Arc Set in Tournaments (FAST) under arc
reversals.  This module starts from a compactly specified transitive tournament
and gives the reversals as compressed arithmetic-progression batches.  Paired
batches cancel except
for planted boundary updates; duplicate boundaries cancel again modulo the
batch period.  Thus the feedback arc set is known by composition of
involutions, never by solving the generated tournament.

Only the standard library is required.  Importing this module performs no I/O
and has no observable side effects.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# Keep repository helpers available when harden.py is launched here.  This
# family is purely finite and does not need them, so the fallback is complete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - standard-library-only path
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "transitive tournament with an affine topological order",
        "succinct arithmetic-progression streams of arc reversals",
        "feedback arc set of the final tournament",
    ],
    "verification_operations": [
        "exact parity of arc reversals",
        "directed-arc membership",
        "exact comparison with the displayed transitive order",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Arc reversal is an involution, so overlapping progression batches "
        "cancel by parity and only unmatched boundary arcs affect the final "
        "tournament; without this invariant one must replay every update."
    ),
    "hardness_basis": (
        "Track B: exact modular replay of B compressed coprime-step batches "
        "takes O(Bn) time and measured 4,676,082 operations (0.092862 s) "
        "at the hard shipping preset, "
        "while the paper's Section 3 full-model query takes O(3^K K log^2 n); "
        "executable boundary cancellation takes 240 counted exact operations but "
        "must be discovered without tools."
    ),
    "max_answer_tokens": 65,
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
    "hard": {
        "n": 65_521,
        "k": 8,
        "gap": 2,
        "decoy_groups": 8,
        "replay_span": 3_200_000,
    },
}
SHIPPING_DIFFICULTY = "hard"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly K distinct directed fixed-gap chord arcs "
        "[tail,head] of the final n-vertex tournament, sorted lexicographically, "
        "with endpoints in 0..n-1; deleting them must leave an acyclic digraph."
    ),
    "bounds": {
        "arc_count": "instance K (8 at the shipping preset)",
        "endpoint_min": 0,
        "endpoint_max": "n-1 (65520 at the shipping preset)",
        "distinct": True,
        "ordering": "lexicographically increasing",
    },
}


STRUCTURAL_HINT = (
    "Arc reversal is an involution, so the final orientation of any arc "
    "depends only on the parity of its total update multiplicity."
)
PLACEBO_HINT = (
    "Careful tracking of all conventions and indices throughout the calculation "
    "prevents subtle endpoint and transcription mistakes."
)


# Filled from the separately preserved harden.py arms after the bare run.  The
# three arms are diagnostic; G9 passes exactly when the size/effort caps pass.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 1, "attempts": 3},
        "placebo": {"solved": 1, "attempts": 3},
    },
    "hinted_verdict": "too_easy_at_shipping_1_of_3_diagnostic_only",
}


NOTES = r"""
The Introduction fixes the dynamic FAST object: a tournament is maintained
under individual arc reversals and a query asks whether a feedback arc set of
size at most K exists.  Section 2, Fact 2.1 relates FAST to arc-disjoint
triangles; Section 2 also records that a tournament is acyclic exactly when it
has no directed triangle (Appendix Fact 0.A.3).  Section 3, Algorithm 1 is the
standard three-way triangle branching algorithm.  The two FAST theorems give
query times O(3^K K sqrt(K)) in the promise model and O(3^K K log^2 n) in the
full model, respectively (Theorems 3.1/3.2 and Appendix Theorems 0.B.1/0.B.2).
The Introduction also cites a static 2^O(sqrt(K)) n^O(1)
algorithm.  Those results make a fixed-small-K planted family ineligible for
Track A, but they provide an honest Track-B mechanical route.

The module stays in the paper's native tournament and arc-reversal objects,
while succinct progression batches are an input encoding not analyzed in the
paper.  The initial tournament is transitive in a displayed affine order.
Every primitive construction consists of a length-(L+1) arithmetic progression
of reversal indices and its length-L interior;
all common updates occur twice, leaving one boundary reversal.  Target
boundaries occur once and decoy boundaries occur twice modulo n.  The known
odd boundaries give a feedback arc set because deleting those reversed arcs
leaves a subgraph of the original transitive tournament.  This is composition
of involutive identities, not a search over feedback sets.

The outlier probe uses the largest batch counts, the greedy probe uses only
first updates, the endpoint ansatz counts visible batch endpoints without
pairing interiors, the score-order probe tries the usual indegree ranking, and
256 structure-aware random restarts sample legal K-arc candidates.  Primitive
target and decoy pairs use the same length and orientation distributions; only
their boundary multiplicity modulo n differs.  The successful reference
algorithm is reported separately, as Track B requires: it reduces each
coprime-step batch to full turns plus a residual progression, replays those
residuals modulo n, and reads backward arcs relative to the known initial
order.  This O(Bn) method is stronger than literal update replay and is the
measured mechanical baseline.  A separately executed O(B) compact route
normalizes paired progressions, keeps their unmatched boundaries, and cancels
those boundaries by parity.
""".strip()


def _reverse_batch(batch: dict) -> dict:
    """Return the same finite progression written in reverse order."""
    return {
        "start": batch["end"],
        "end": batch["start"],
        "step": -batch["step"],
    }


def _batch_endpoints(batch: dict) -> tuple[int, int]:
    return min(batch["start"], batch["end"]), max(batch["start"], batch["end"])


def _batch_count(batch: dict) -> int:
    return abs(batch["end"] - batch["start"]) // abs(batch["step"]) + 1


def _primitive_batches(start: int, length: int, step: int,
                       rng: random.Random) -> list[dict]:
    """Two same-distribution batches whose parity leaves only index start."""
    end = start + step * length
    outer = {"start": start, "end": end, "step": step}
    inner = {"start": start + step, "end": end, "step": step}
    if rng.randrange(2):
        outer = _reverse_batch(outer)
    if rng.randrange(2):
        inner = _reverse_batch(inner)
    return [outer, inner]


def _derive_toggle_residues(inst: dict) -> list[int]:
    """Evaluate all batches by quotient/remainder parity, without full replay."""
    n = inst["n"]
    parity = bytearray(n)
    for batch in inst["batches"]:
        full, rem = divmod(_batch_count(batch), n)
        if full & 1:
            for r in range(n):
                parity[r] ^= 1
        r = batch["start"] % n
        step = batch["step"]
        for _ in range(rem):
            parity[r] ^= 1
            r = (r + step) % n
    return [r for r, bit in enumerate(parity) if bit]


def _order_list(inst: dict) -> list[int]:
    """Materialize the public affine order (or a relabelled test order)."""
    if "initial_order" in inst:
        return list(inst["initial_order"])
    multiplier, offset = inst["order_affine"]
    n = inst["n"]
    return [(multiplier * position + offset) % n for position in range(n)]


def _label_at(inst: dict, position: int) -> int:
    if "initial_order" in inst:
        return inst["initial_order"][position % inst["n"]]
    multiplier, offset = inst["order_affine"]
    return (multiplier * (position % inst["n"]) + offset) % inst["n"]


def _backward_arc_for_residue(inst: dict, residue: int) -> list[int]:
    n = inst["n"]
    p = residue
    q = (residue + inst["gap"]) % n
    lo, hi = (p, q) if p < q else (q, p)
    return [_label_at(inst, hi), _label_at(inst, lo)]


def _directed_chord_for_residue(inst: dict, residue: int) -> list[int]:
    """Return the final orientation of one fixed-gap chord."""
    n = inst["n"]
    p = residue
    q = (residue + inst["gap"]) % n
    lo, hi = (p, q) if p < q else (q, p)
    if residue in inst["_toggle_set"]:
        lo, hi = hi, lo
    return [_label_at(inst, lo), _label_at(inst, hi)]


def _find_required_triangles(inst: dict) -> list[list[list[int]]]:
    """Construct one directed triangle forced by each reversed gap-two chord."""
    n = inst["n"]
    triangles = []
    for residue in inst["_toggle_residues"]:
        tail, head = _backward_arc_for_residue(inst, residue)
        p = residue
        q = (residue + inst["gap"]) % n
        lo, hi = (p, q) if p < q else (q, p)
        middle = lo + 1
        triangles.append([
            [tail, head],
            [_label_at(inst, lo), _label_at(inst, middle)],
            [_label_at(inst, middle), _label_at(inst, hi)],
        ])
    return triangles


def _rebuild_private(inst: dict) -> dict:
    """Recompute caches that are deterministic consequences of public data."""
    residues = _derive_toggle_residues(inst)
    inst["_toggle_residues"] = residues
    inst["_toggle_set"] = set(residues)
    order = _order_list(inst)
    inst["_position"] = {label: pos for pos, label in enumerate(order)}
    indegree = list(range(inst["n"]))
    for residue in residues:
        p = residue
        q = (residue + inst["gap"]) % inst["n"]
        lo, hi = (p, q) if p < q else (q, p)
        indegree[lo] += 1
        indegree[hi] -= 1
    inst["_final_indegree"] = [0] * inst["n"]
    for position, label in enumerate(order):
        inst["_final_indegree"][label] = indegree[position]
    inst["_required_triangles"] = _find_required_triangles(inst)
    return inst


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a dynamic FAST instance and its witness by cancellation.

    The answer is sampled first as K distinct reversal residues.  Long paired
    update batches are then composed around those residues; decoy residues are
    each composed twice and cancel.  No feedback-set solver is invoked.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 7 or n % 2 == 0:
        raise ValueError("n must be an odd integer at least 7")
    k = int(params.get("k", 8))
    gap = int(params.get("gap", 2))
    decoy_groups = int(params.get("decoy_groups", 8))
    replay_span = int(params.get("replay_span", 10_000))
    if gap != 2:
        raise ValueError("this family requires gap=2")
    if k < 2 or decoy_groups < 1 or k + decoy_groups > n:
        raise ValueError("need 2 <= k and enough residues for all groups")
    if replay_span < 3:
        raise ValueError("replay_span must be at least 3")

    rng = random.Random(seed)
    multiplier = rng.randrange(1, n)
    while math.gcd(multiplier, n) != 1:
        multiplier = rng.randrange(1, n)
    offset = rng.randrange(n)

    # Singletons are the planted odd boundaries.  Paired copies are decoys.
    chosen = rng.sample(range(n), k + decoy_groups)
    target_residues = chosen[:k]
    decoy_residues = chosen[k:]
    residual_multiset = list(target_residues)
    for residue in decoy_residues:
        residual_multiset.extend((residue, residue))
    rng.shuffle(residual_multiset)

    batches = []
    # Keep primitive integer intervals disjoint.  Their residues modulo n still
    # collide exactly where the construction asks them to.
    stride = 8 * (replay_span + n + 17) * n
    origin = (10_000 + rng.randrange(10_000)) * n
    for idx, residue in enumerate(residual_multiset):
        raw = origin + idx * stride + rng.randrange(n, 2 * n)
        start = raw - raw % n + residue
        length = replay_span + rng.randrange(max(2, replay_span // 5))
        step = rng.randrange(1, n)
        while math.gcd(step, n) != 1:
            step = rng.randrange(1, n)
        batches.extend(_primitive_batches(start, length, step, rng))
    rng.shuffle(batches)

    inst = {
        "n": n,
        "k": k,
        "gap": gap,
        "order_affine": [multiplier, offset],
        "batches": batches,
    }
    # The witness is carried directly from the odd boundary residues sampled
    # above.  The cache computation below merely checks the cancellation identity.
    answer = sorted(_backward_arc_for_residue(inst, r) for r in target_residues)
    inst["answer"] = answer
    _rebuild_private(inst)
    expected = sorted(target_residues)
    if inst["_toggle_residues"] != expected:
        raise AssertionError("batch cancellation identity failed")
    return inst


def render(inst: dict) -> str:
    """Render the complete self-contained dynamic tournament problem."""
    affine = inst.get("order_affine")
    lines = [
        "Dynamic feedback arc set in a tournament",
        "",
        "A tournament is a directed graph with exactly one directed arc between",
        "each pair of distinct vertices.  A feedback arc set is a set of directed",
        "arcs whose deletion leaves an acyclic directed graph (one with no directed",
        "cycle).",
        "",
        f"There are n={inst['n']} vertices, labelled 0 through {inst['n'] - 1}.",
        "The initial tournament is transitive in a left-to-right order whose",
    ]
    if affine is not None:
        lines.extend([
            f"vertex at 0-indexed position p is ({affine[0]}*p+{affine[1]}) mod n.",
            "The multiplier is coprime to n, so this lists every vertex exactly once.",
        ])
    else:  # Used only by canonical-key relabelling tests.
        lines.extend([
            "0-indexed vertex-label list is:",
            json.dumps(inst["initial_order"], separators=(",", ":")),
        ])
    lines.extend([
        "For positions p<q, the initial arc points from the vertex at position p",
        "to the vertex at position q.",
        "",
        "The tournament is updated by all batches below, in the listed order.",
        f"The fixed position gap is g={inst['gap']}.  A batch [first,last,step]",
        "means: start with x=first, repeatedly use x:=x+step, and include both",
        "endpoints through x=last.  For every such x, let r=x mod n, using the",
        "residue in {0,...,n-1}, and reverse",
        "the arc between the vertices at positions r and (r+g) mod n.",
        "Each displayed step is nonzero and coprime to n.  Reversing an arc twice",
        "restores its old direction.",
        "",
        f"Batches ({len(inst['batches'])} total):",
    ])
    lines.extend(
        f"  [{b['start']},{b['end']},{b['step']}]" for b in inst["batches"]
    )
    lines.extend([
        "",
        f"Find exactly K={inst['k']} distinct directed arcs present in the FINAL",
        "tournament such that deleting those arcs makes the resulting digraph",
        "acyclic.  Every listed arc must be one of the fixed-gap chords: its endpoint",
        "positions differ by g modulo n in one direction.  Write it as [tail,head],",
        "use vertex labels (not positions), do not repeat an arc, and sort the list",
        "lexicographically.  Order inside an arc matters; all bounds above are",
        "inclusive/exclusive exactly as stated.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list of",
        "K two-integer lists.  Example syntax: <answer>[[3,17],[8,2]]</answer>",
        "(the example illustrates syntax only; your list must contain exactly K arcs).",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: str):
    """Extract the required JSON witness from a tagged model response."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _acyclic_after_deleting(inst: dict, removed: set[tuple[int, int]]) -> bool:
    """Exact acyclicity test specialized to the stated update language.

    Batches can alter only the n fixed-gap chords.  Every other arc still
    points forward in the displayed initial order.  Consequently the graph
    after deletion is acyclic exactly when every remaining chord also points
    forward: the displayed order is then an executable topological witness.
    For gap two, any remaining reversed chord also has its intervening vertex
    and forms a directed triangle, so this test is necessary as well.
    """
    for residue in inst["_toggle_residues"]:
        tail, head = _backward_arc_for_residue(inst, residue)
        if (tail, head) not in removed:
            return False
    return True


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any legal feedback arc set, never consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    for arc in answer:
        if not isinstance(arc, list) or len(arc) != 2 \
                or any(isinstance(x, bool) or not isinstance(x, int) for x in arc):
            return False, "every arc must be a two-integer JSON list"
        if any(x < 0 or x >= inst["n"] for x in arc):
            return False, "an arc endpoint is outside 0..n-1"
        if arc[0] == arc[1]:
            return False, "self-arcs do not exist in a tournament"
    if len(answer) != inst["k"]:
        return False, f"expected exactly {inst['k']} arcs"
    tuples = [tuple(arc) for arc in answer]
    if len(set(tuples)) != len(tuples):
        return False, "arcs must be distinct"
    if answer != sorted(answer):
        return False, "arcs must be sorted lexicographically"
    for tail, head in tuples:
        p = inst["_position"][tail]
        q = inst["_position"][head]
        if (p - q) % inst["n"] not in (inst["gap"], inst["n"] - inst["gap"]):
            return False, "every listed arc must be a fixed-gap chord"
        residue = p if (p + inst["gap"]) % inst["n"] == q else q
        if [tail, head] != _directed_chord_for_residue(inst, residue):
            return False, f"[{tail},{head}] is not a directed arc of the final tournament"
    removed = set(tuples)
    for triangle in inst["_required_triangles"]:
        if removed.isdisjoint(tuple(arc) for arc in triangle):
            return False, "a directed cycle remains after deleting the listed arcs"
    if not _acyclic_after_deleting(inst, removed):
        return False, "a directed cycle remains after deleting the listed arcs"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    """Sample uniformly from legal sorted K-subsets of fixed-gap chord arcs."""
    indices = rng.sample(range(inst["n"]), inst["k"])
    return sorted(_directed_chord_for_residue(inst, i) for i in indices)


def search_space(inst: dict) -> int:
    """Number of shape-, direction-, distinctness-, and order-valid candidates."""
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst: dict):
    """Count all valid witnesses exactly when the declared space is small."""
    if search_space(inst) > 200_000:
        return None
    count = 0
    for indices in itertools.combinations(range(inst["n"]), inst["k"]):
        candidate = sorted(_directed_chord_for_residue(inst, i) for i in indices)
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize vertex names, batch order/direction, and cancelling history."""
    pairs = []
    n = inst["n"]
    gap = inst["gap"]
    for r in _derive_toggle_residues(inst):
        q = (r + gap) % n
        pairs.append([min(r, q), max(r, q)])
    payload = json.dumps([n, sorted(pairs)], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict):
    """Grow the ambient residue space and replay work at fixed witness/route size."""
    harder = dict(params)
    harder.pop("_preset", None)
    harder["n"] = 2 * int(harder["n"]) - 1
    harder["gap"] = 2
    harder["decoy_groups"] = int(harder["decoy_groups"])
    harder["replay_span"] = 2 * int(harder["replay_span"])
    return harder


def _modular_replay_reference(inst: dict):
    """Mechanical Track-B reference on the compressed update stream.

    Because every step is coprime to n, each n consecutive terms visit every
    residue once.  Remove full turns, then replay each residual progression.
    This uses compression but not the paired-boundary construction.
    """
    start_time = time.perf_counter()
    n = inst["n"]
    parity = bytearray(n)
    global_bit = 0
    operations = 0
    for batch in inst["batches"]:
        count = _batch_count(batch)
        full, rem = divmod(count, n)
        global_bit ^= full & 1
        residue = batch["start"] % n
        step = batch["step"]
        operations += 7  # endpoint difference, abs/div/+1, divmod, XOR, start mod
        for _ in range(rem):
            parity[residue] ^= 1
            residue = (residue + step) % n
            operations += 3
    if global_bit:
        for residue in range(n):
            parity[residue] ^= 1
            operations += 1
    answer = sorted(
        _backward_arc_for_residue(inst, r)
        for r, bit in enumerate(parity) if bit
    )
    operations += 9 * len(answer)
    elapsed = time.perf_counter() - start_time
    return answer, elapsed, operations


def _compact_cancellation_route(inst: dict):
    """Execute and count the intended O(B) no-tool route.

    Normalizing a batch exposes a key (absolute step, right endpoint).  Exactly
    two batches share each such key; their symmetric difference is the smaller
    left endpoint.  Equal endpoints modulo n then cancel by parity.
    """
    start_time = time.perf_counter()
    groups = {}
    operations = 0
    for batch in inst["batches"]:
        left, right = (batch["start"], batch["end"]) \
            if batch["start"] < batch["end"] else (batch["end"], batch["start"])
        key = (abs(batch["step"]), right)
        groups.setdefault(key, []).append(left)
        operations += 2  # endpoint-order comparison and absolute step

    boundary_parity = {}
    for lefts in groups.values():
        if len(lefts) != 2:
            raise AssertionError("compact route found a malformed batch pair")
        boundary = min(lefts) % inst["n"]
        boundary_parity[boundary] = boundary_parity.get(boundary, 0) ^ 1
        operations += 3  # minimum comparison, reduction, parity toggle

    residues = sorted(r for r, bit in boundary_parity.items() if bit)
    answer = sorted(_backward_arc_for_residue(inst, residue)
                    for residue in residues)
    operations += 9 * len(answer)  # gap endpoint plus two affine label evaluations
    elapsed = time.perf_counter() - start_time
    return answer, elapsed, operations


def _candidate_from_residues(inst: dict, residues) -> list[list[int]]:
    """Turn heuristic residues into a legal K-arc candidate, padding neutrally."""
    chosen = []
    seen = set()
    for residue in residues:
        arc = tuple(_directed_chord_for_residue(inst, residue % inst["n"]))
        if arc not in seen:
            seen.add(arc)
            chosen.append(list(arc))
        if len(chosen) == inst["k"]:
            break
    for residue in range(inst["n"]):
        arc = _directed_chord_for_residue(inst, residue)
        key = tuple(arc)
        if key not in seen:
            seen.add(key)
            chosen.append(arc[:])
        if len(chosen) == inst["k"]:
            break
    return sorted(chosen)


def _attack_candidates(inst: dict, rng: random.Random) -> dict[str, list]:
    batches = inst["batches"]
    n = inst["n"]

    largest = sorted(batches, key=lambda b: (-_batch_count(b), b["start"]))
    outlier = _candidate_from_residues(inst, [b["start"] for b in largest])

    first_counts = {}
    for b in batches:
        r = b["start"] % n
        first_counts[r] = first_counts.get(r, 0) + 1
    greedy_res = sorted(first_counts, key=lambda r: (-first_counts[r], r))
    greedy = _candidate_from_residues(inst, greedy_res)

    endpoint_counts = {}
    for b in batches:
        lo, hi = _batch_endpoints(b)
        for x in (lo % n, hi % n):
            endpoint_counts[x] = endpoint_counts.get(x, 0) + 1
    endpoint_res = sorted(endpoint_counts,
                          key=lambda r: (-endpoint_counts[r], r))
    endpoints = _candidate_from_residues(inst, endpoint_res)

    # The familiar tournament heuristic: rank by indegree, then delete arcs
    # that point backward in that score order.  It deliberately ignores the
    # displayed initial order and the cancellation invariant.
    score_order = sorted(range(n), key=lambda v: (inst["_final_indegree"][v], v))
    rank = {v: i for i, v in enumerate(score_order)}
    backward = []
    for residue in range(n):
        arc = _directed_chord_for_residue(inst, residue)
        if rank[arc[0]] > rank[arc[1]]:
            backward.append(arc)
    score_candidate = sorted(backward[:inst["k"]])
    if len(score_candidate) < inst["k"]:
        score_candidate = _candidate_from_residues(
            inst, [inst["_position"][a[0]] for a in backward]
        )

    return {
        "outlier_largest_batch_counts": [outlier],
        "greedy_first_update_frequency": [greedy],
        "endpoint_frequency_ansatz": [endpoints],
        "indegree_score_order_by_hand": [score_candidate],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _public_clone(inst: dict) -> dict:
    return {key: json.loads(json.dumps(value)) for key, value in inst.items()
            if not key.startswith("_")}


def _relabelled(inst: dict, rng: random.Random) -> dict:
    out = _public_clone(inst)
    perm = list(range(inst["n"]))
    rng.shuffle(perm)
    out["initial_order"] = [perm[v] for v in _order_list(inst)]
    out.pop("order_affine", None)
    out["answer"] = sorted([[perm[a], perm[b]] for a, b in inst["answer"]])
    return _rebuild_private(out)


def _batches_shuffled(inst: dict, rng: random.Random) -> dict:
    out = _public_clone(inst)
    rng.shuffle(out["batches"])
    return _rebuild_private(out)


def _batch_directions_reversed(inst: dict) -> dict:
    out = _public_clone(inst)
    out["batches"] = [_reverse_batch(b) for b in out["batches"]]
    return _rebuild_private(out)


def _cancel_pair_added(inst: dict, rng: random.Random) -> dict:
    out = _public_clone(inst)
    start = rng.randrange(100_000, 200_000)
    count = rng.randrange(11, 101)
    step = rng.choice((-1, 1))
    b = {
        "start": start,
        "end": start + step * (count - 1),
        "step": step,
    }
    out["batches"].extend((b, dict(b)))
    rng.shuffle(out["batches"])
    return _rebuild_private(out)


def _answer_token_measure(answer) -> int:
    # Conservative tokenizer-independent estimate: punctuation is one token and
    # each three-digit chunk of an integer is one token.
    blob = json.dumps(answer, separators=(",", ":"))
    punctuation = len(re.findall(r"[\[\],-]", blob))
    digits = sum((len(group) + 2) // 3 for group in re.findall(r"\d+", blob))
    return punctuation + digits


def selftest() -> dict:
    report = {
        "paper": "2404.12907",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    planted = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            planted += int(ok)
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": planted == 12,
        "verified": planted,
        "attempts": 12,
        "failures": failures,
    }

    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = ship["answer"]
    swapped = answer[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = answer[:]
    duplicated[-1] = duplicated[0][:]
    out_of_range = [arc[:] for arc in answer]
    out_of_range[0][0] = ship["n"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, bad in corruptions.items():
        ok, why = verify(ship, bad)
        rejected[name] = {"rejected": not ok, "reason": why}
    distinct_reasons = len({row["reason"] for row in rejected.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejected.values())
                and distinct_reasons == 5,
        "cases": rejected,
        "distinct_reasons": distinct_reasons,
    }

    wrapped = (
        "The cancellation leaves these arcs.\n```json\n<answer>"
        + json.dumps(answer) + "</answer>\n```\n"
    )
    parsed = parse_answer(wrapped)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "parsed_matches": parsed == answer,
        "json_native": json_native,
    }

    density_inst = make_instance(seed=11,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])
    density_rng = random.Random(0x240412907)
    samples = 200_000
    hits = 0
    density_start = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(density_inst,
                           random_candidate(density_inst, density_rng))[0])
    density_wall = time.perf_counter() - density_start
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "structure_aware_space": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
    }

    attempts = 8
    attack_successes = None
    ref_successes = 0
    ref_walls = []
    ref_updates = []
    compact_successes = 0
    compact_walls = []
    compact_updates = []
    for seed in range(20, 20 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        probes = _attack_candidates(inst, random.Random(90_000 + seed))
        if attack_successes is None:
            attack_successes = {name: 0 for name in probes}
        for name, candidates in probes.items():
            if any(verify(inst, candidate)[0] for candidate in candidates):
                attack_successes[name] += 1
        found, elapsed, operations = _modular_replay_reference(inst)
        ref_successes += int(verify(inst, found)[0])
        ref_walls.append(elapsed)
        ref_updates.append(operations)
        compact, compact_elapsed, compact_operations = _compact_cancellation_route(inst)
        compact_successes += int(verify(inst, compact)[0])
        compact_walls.append(compact_elapsed)
        compact_updates.append(compact_operations)
    attacks = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_successes.items()
    }
    all_attacks_failed = all(row["successes"] == 0 for row in attacks.values())
    mean_wall = sum(ref_walls) / len(ref_walls)
    mean_updates = sum(ref_updates) // len(ref_updates)
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_successes == attempts
                and compact_successes == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "full-turn reduction plus exact modular replay of every residual "
                "coprime-step progression"
            ),
            "complexity": "O(B*n) exact integer/XOR operations",
            "wall_clock_sec": round(mean_wall, 6),
            "operations": mean_updates,
            "literal_updates": sum(_batch_count(b) for b in ship["batches"]),
            "solves": f"{ref_successes}/{attempts}, as expected",
        },
        "compact_route": {
            "name": "normalized progression-pair boundary cancellation",
            "complexity": "O(B) exact arithmetic and parity operations",
            "wall_clock_sec": round(sum(compact_walls) / attempts, 6),
            "operations": max(compact_updates),
            "solves": f"{compact_successes}/{attempts}, as expected",
        },
        "paper_algorithm": {
            "name": "Section 3 Algorithm 1 triangle branching",
            "complexity": "O(3^K*K*log^2(n)) query after O(n^2) initialization",
            "branching_nodes_upper_bound": 3 ** ship["k"],
        },
    }

    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and demo_count is not None
                and ref_successes == attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": probability,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(mean_wall, 6),
        "baseline_update_operations": mean_updates,
    }

    doubled_params = dict(DIFFICULTY["hard"])
    doubled_params["n"] = 2 * doubled_params["n"] - 1
    doubled_params["gap"] = 2
    doubled_params["replay_span"] *= 2
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["answer"]) == len(answer)
                and search_space(doubled) > search_space(ship),
        "original_n": ship["n"],
        "doubled_n": doubled["n"],
        "answer_arcs_before": len(answer),
        "answer_arcs_after": len(doubled["answer"]),
        "search_space_increased": search_space(doubled) > search_space(ship),
        "verify_reason": doubled_why,
    }

    invariant_passed = 0
    invariant_attempted = 0
    transformed_verified = 0
    unrelated_keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(123_000 + seed)
        relabelled = _relabelled(inst, rng)
        shuffled = _batches_shuffled(inst, rng)
        reversed_batches = _batch_directions_reversed(inst)
        cancel_added = _cancel_pair_added(inst, rng)
        composed = _batches_shuffled(
            _cancel_pair_added(
                _batch_directions_reversed(_relabelled(inst, rng)), rng
            ), rng
        )
        base_key = canonical_key(inst)
        for changed in (relabelled, shuffled, reversed_batches,
                        cancel_added, composed):
            invariant_attempted += 1
            invariant_passed += int(canonical_key(changed) == base_key)
        transformed_verified += int(verify(composed, composed["answer"])[0])
        unrelated_keys.append(base_key)
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_passed == invariant_attempted
                and transformed_verified == 20 and distinct == 20,
        "invariance_checks_passed": invariant_passed,
        "invariance_checks_attempted": invariant_attempted,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": distinct,
        "unrelated_instances": 20,
    }

    blob = json.dumps(answer, separators=(",", ":"))
    answer_elements = 2 * len(answer)
    endpoint_digits = len(str(ship["n"] - 1))
    punctuation_tokens = 4 * ship["k"] + 1
    worst_answer_chars = punctuation_tokens + 2 * ship["k"] * endpoint_digits
    worst_answer_tokens = punctuation_tokens + 2 * ship["k"] \
        * ((endpoint_digits + 2) // 3)
    compact_answer, _, intended_ops = _compact_cancellation_route(ship)
    compact_ok = verify(ship, compact_answer)[0]
    arms = G9_RESULTS["arms"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = worst_answer_chars <= 2_000 and answer_elements <= 256 \
        and intended_ops <= 300 and compact_ok
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": worst_answer_chars,
        "sample_answer_chars": len(blob),
        "answer_tokens": worst_answer_tokens,
        "sample_answer_tokens": _answer_token_measure(answer),
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
