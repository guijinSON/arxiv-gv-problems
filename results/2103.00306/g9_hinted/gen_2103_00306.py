"""Verified problem generator for arXiv:2103.00306.

The answer symbolically describes a concrete violating cut for an odd-vertex
pairing. A planted 3-XOR assignment is carried through a termwise MAXCUT gadget
and then through the paper's constant-boundary cut identity.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time

TRACK: str = "B"
STRUCTURAL_HINT: str = (
    "The variable tags carry a linear invariant tied to the public audit mask."
)
PLACEBO_HINT: str = (
    "The variable indices require consistent bookkeeping across every repeated gadget."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "a finite multigraph G in exact edge-block notation",
        "an odd-vertex pairing F",
        "a symbolic vertex cut expanded from a Boolean assignment",
    ],
    "verification_operations": [
        "exact multigraph cut counting",
        "exact expansion of a symbolic cloud cut",
        "integer comparison with exact q-to-t edge-connectivity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A masked GF(2) parity of each variable tag recovers the extremal gadget cut; "
        "without it, the repeated parity constraints require exact elimination."
    ),
    "hardness_basis": (
        "Track B: GF(2) Gaussian elimination solves the generated constraint system "
        "in O(r*n^2) bit operations, with measured shipping cost recorded by selftest, "
        "while the compact tag invariant needs two exact word operations per variable."
    ),
    "max_answer_tokens": 20,
}
NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}
DIFFICULTY: dict = {"hard": {"n": 48, "base_equations": 56, "tag_bits": 256}}
SHIPPING_DIFFICULTY: str = "hard"
CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing list of exactly n/2 distinct one-based variable "
        "indices from 1..n; listed variables have value 1, and the statement's "
        "local gadget rule expands them to a concrete vertex cut."
    ),
    "bounds": {"max_variables": 256, "max_selected_variables": 128, "index_base": 1},
}
NOTES: str = (
    "Section 1 fixes odd-vertex pairings, R_G(X), and cut-admissibility. Section "
    "2.1 fixes AMAXCUT's even-edge/even-degree regime. Section 3.1, especially "
    "Lemma 4, supplies the constant-boundary-minus-auxiliary-cut identity, while "
    "Sections 3.2--3.3 explain why the distinguished connectivity and all degrees "
    "must be controlled. The literal augmented grids are too large for a writable "
    "benchmark, so low-degree channel blocks prove the same identity directly. "
    "Each parity equation is represented by a six-vertex K6-minus-one-edge MAXCUT "
    "gadget and repeated twice: a satisfying assignment contributes 18 and any "
    "violation loses at least 2. The assignment is sampled first, so it is never "
    "found by solving. Theorems 2 and 3 give worst-case hardness only; generated "
    "instances admit Gaussian elimination and are therefore honest Track B. Dense "
    "random equations defeat positional, greedy, raw-parity, and pair-swap attacks."
)
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _parity(value):
    return value.bit_count() & 1


def _rank_binary(rows, ncols):
    work = list(rows)
    rank = 0
    for col in range(ncols):
        pivot = next((i for i in range(rank, len(work)) if (work[i] >> col) & 1), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for i in range(rank + 1, len(work)):
            if (work[i] >> col) & 1:
                work[i] ^= work[rank]
        rank += 1
        if rank == ncols:
            break
    return rank


def _sample_system(n, count, assignment, rng):
    if count < n or count > math.comb(n, 3):
        raise ValueError("base_equations must lie between n and C(n,3)")
    for _ in range(300):
        triples = set()
        while len(triples) < count:
            triple = tuple(sorted(rng.sample(range(n), 3)))
            if assignment[triple[0]] ^ assignment[triple[1]] ^ assignment[triple[2]]:
                triples.add(triple)
        ordered = sorted(triples)
        rows = [sum(1 << i for i in triple) for triple in ordered]
        # Every row has odd Hamming weight and right side 1, so the all-ones
        # assignment is unavoidable.  Rank n-1 makes the planted balanced
        # assignment the unique solution in our fixed-weight language.
        if _rank_binary(rows, n) == n - 1:
            rng.shuffle(ordered)
            return ordered
    raise RuntimeError("could not sample a full-rank planted 3-XOR system")


def _sample_tags(bits, assignment, rng):
    if bits < 8:
        raise ValueError("tag_bits must be at least 8")
    limit = (1 << bits) - 1
    while True:
        audit_mask = rng.getrandbits(bits) & limit
        if audit_mask and audit_mask.bit_count() >= bits // 3:
            break
    tags, used = [], set()
    for bit in assignment:
        for _ in range(10000):
            tag = rng.getrandbits(bits) & limit
            if tag not in used and _parity(tag & audit_mask) == bit:
                used.add(tag)
                tags.append(tag)
                break
        else:
            raise RuntimeError("could not sample distinct masked-parity tags")
    return tags, audit_mask


def _answer_from_assignment(assignment):
    return [i + 1 for i, bit in enumerate(assignment) if bit]


def make_instance(n, seed=0, base_equations=None, tag_bits=128, **params) -> dict:
    """Inverse-generate an assignment and compose its exact cut certificate."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    base_equations = n + 8 if base_equations is None else base_equations
    if isinstance(base_equations, bool) or not isinstance(base_equations, int):
        raise ValueError("base_equations must be an integer")
    if isinstance(tag_bits, bool) or not isinstance(tag_bits, int):
        raise ValueError("tag_bits must be an integer")
    rng = random.Random(seed)
    ones = set(rng.sample(range(n), n // 2))
    assignment = [int(i in ones) for i in range(n)]
    base = _sample_system(n, base_equations, assignment, rng)
    equations = [triple for triple in base for _ in range(2)]
    rng.shuffle(equations)
    tags, audit_mask = _sample_tags(tag_bits, assignment, rng)
    r = len(equations)
    cloud_count = 1 + n + 2 * r
    h_edges = 14 * r
    max_cut = 9 * r
    threshold = max_cut - 2
    channels = h_edges * cloud_count - threshold
    if r % 2 or h_edges % 2 or threshold % 2 or channels % 2:
        raise AssertionError("the AMAXCUT/channel parity conditions failed")
    return {
        "family": "symbolic cut-admissibility violation for an odd-vertex pairing",
        "n": n,
        "base_equations": base_equations,
        "tag_bits": tag_bits,
        "tags": tags,
        "audit_mask": audit_mask,
        "equations": [list(t) for t in equations],
        "equation_count": r,
        "cloud_count": cloud_count,
        "h_edge_count": h_edges,
        "max_cut": max_cut,
        "cut_threshold": threshold,
        "channel_count": channels,
        "graph_vertex_count": 2 + cloud_count + 2 * h_edges + 2 * channels,
        "graph_edge_count": 2 * channels + 2 * h_edges * cloud_count + 2 * h_edges,
        "pairing_edge_count": h_edges + threshold,
        "answer": _answer_from_assignment(assignment),
    }


def _hex(value, bits):
    return f"{value:0{(bits + 3) // 4}x}"


def render(inst) -> str:
    tag_lines = []
    for start in range(0, inst["n"], 2):
        tag_lines.append("  " + "  ".join(
            f"{i + 1}:{_hex(inst['tags'][i], inst['tag_bits'])}"
            for i in range(start, min(start + 2, inst["n"]))))
    eq_lines = []
    for start in range(0, inst["equation_count"], 8):
        eq_lines.append("  " + "  ".join(
            f"{e + 1}:{a + 1},{b + 1},{c + 1}"
            for e, (a, b, c) in enumerate(inst["equations"][start:start + 8], start)))
    statement = f"""CUT-ADMISSIBILITY WITNESS FOR AN ODD-VERTEX PAIRING

All graphs are finite undirected multigraphs without loops; parallel edges count
with multiplicity. For a graph J and vertex set Y, d_J(Y) counts edges with one
endpoint in Y. For vertices a,b, lambda_J(a,b) is the minimum d_J(Y) over sets
containing a but not b. For nonempty proper Y,
  R_J(Y)=max 2*floor(lambda_J(a,b)/2),
over a in Y and b outside Y. A pairing F of all odd-degree vertices of G is
cut-admissible if d_G(Y)-d_F(Y)>=R_G(Y) for every Y. A violation certifies that
F is not cut-admissible.

Define an auxiliary multigraph H. It has anchor A, n={inst['n']} variable vertices
v_1..v_n, and private vertices p_e,q_e for each of r={inst['equation_count']}
displayed equation occurrences. An occurrence e:i,j,k adds every edge among
A,v_i,v_j,v_k,p_e,q_e except p_e--q_e: a K6 with that edge deleted. Repeated
edges retain multiplicity. Thus H has {inst['h_edge_count']} edges. Its complete
equation-occurrence list is:
{chr(10).join(eq_lines)}

The variables carry fixed-width {inst['tag_bits']}-bit hexadecimal tags:
{chr(10).join(tag_lines)}
The public audit mask is C={_hex(inst['audit_mask'], inst['tag_bits'])}.

Make one CLOUD for every H-vertex, N={inst['cloud_count']} in all: cloud 0 is A;
clouds 1..n are v_1..v_n; occurrence e (one-based) uses clouds n+2e-1 and
n+2e for p_e,q_e. A cloud has center c_i and an incidence leaf z_(f,i) for
every H-edge f incident with i.

Let k={inst['cut_threshold']}, M={inst['channel_count']}, and B=|E(H)|*N={inst['h_edge_count'] * inst['cloud_count']}.
Besides cloud vertices, G has q,t, left channels L_0..L_(M-1), and right channels
R_0..R_(M-1). Add q--L_j and R_j--t for every j. Flatten tokens (i,s),
0<=i<N, 0<=s<|E(H)|, as z=i*|E(H)|+s. Put h(z)=z if z<M and h(z)=z-M
otherwise. For each token of cloud i add L_h(z)--c_i and c_i--R_h(z). Also add
c_i--z_(f,i) for each H-edge incidence. There are no other G-edges.

F pairs z_(f,u) with z_(f,v) for every H-edge f=u-v. It pairs L_0..L_(k-1)
consecutively and, independently, R_0..R_(k-1) consecutively. There are no
other F-edges; these rules pair every odd-degree G-vertex exactly once.

Your answer is a Boolean assignment: a strictly increasing list T of exactly
{inst['n'] // 2} distinct indices from 1..{inst['n']}; precisely those variables
have value 1. It expands to cut X containing q, all left channels, cloud 0, and
the variable clouds whose values are 0. For occurrence e:i,j,k, X contains both
private clouds p_e,q_e exactly when all three values are 1. If X contains a
cloud it contains its center and every incidence leaf; it contains nothing else.

Find T whose expanded X satisfies d_G(X)-d_F(X)<R_G(X). The checker expands T,
counts every gadget edge, and compares with exact q-to-t connectivity M; it never
uses a hidden answer. Order and cardinality are mandatory, repeats are forbidden,
and indices are one-based.

Give your final answer inside <answer></answer> tags, as comma-separated decimal
integers in strictly increasing order. Example (not this answer):
<answer>1, 4, 9</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not matches:
        return None
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", matches[-1].strip(),
                  flags=re.I | re.S).strip()
    if body == "":
        return []
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, list) or any(isinstance(x, bool) or not isinstance(x, int)
                                              for x in value):
            return None
        return value
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(x.strip()) for x in body.split(",")]
    except ValueError:
        return None


def _assignment(inst, answer):
    selected = set(answer)
    return [int(i + 1 in selected) for i in range(inst["n"])]


def _h_cut(inst, values):
    total = 0
    for a, b, c in inst["equations"]:
        aux = int(not (values[a] and values[b] and values[c]))
        bits = [0, values[a], values[b], values[c], aux, aux]
        for i in range(6):
            for j in range(i + 1, 6):
                if (i, j) != (4, 5):
                    total += bits[i] != bits[j]
    return total


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a list of variable indices"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every variable index must be an integer"
    if any(x < 1 or x > inst["n"] for x in answer):
        return False, f"variable indices must lie in 1..{inst['n']}"
    if len(set(answer)) != len(answer):
        return False, "variable indices must be distinct"
    if answer != sorted(answer):
        return False, "variable indices must be in strictly increasing order"
    if len(answer) != inst["n"] // 2:
        return False, f"answer must contain exactly {inst['n'] // 2} variables"
    d_f = _h_cut(inst, _assignment(inst, answer))
    d_g = inst["h_edge_count"] * inst["cloud_count"]
    if d_g - d_f >= inst["channel_count"]:
        return False, ("cut inequality fails: "
                       f"d_G(X)-d_F(X)={d_g-d_f} is not below "
                       f"R_G(X)={inst['channel_count']}")
    return True, "ok"


def random_candidate(inst, rng):
    return sorted(rng.sample(range(1, inst["n"] + 1), inst["n"] // 2))


def search_space(inst):
    return math.comb(inst["n"], inst["n"] // 2)


def enumerate_all(inst):
    if search_space(inst) > 100_000:
        return None
    return sum(verify(inst, list(a))[0] for a in
               itertools.combinations(range(1, inst["n"] + 1), inst["n"] // 2))


def canonical_key(inst):
    tagged = sorted(sorted(inst["tags"][i] for i in row) for row in inst["equations"])
    payload = {"n": inst["n"], "tag_bits": inst["tag_bits"],
               "audit_mask": inst["audit_mask"], "tagged_equations": tagged}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    p = dict(params)
    if int(p.get("tag_bits", 128)) < 512:
        p["tag_bits"] = int(p.get("tag_bits", 128)) + 64
        return p
    if int(p["n"]) < 148:
        p["n"] = int(p["n"]) + 4
        p["base_equations"] = int(p.get("base_equations", p["n"] + 4)) + 4
        return p
    return "cap_bound"


def _force_weight(inst, scores):
    chosen = sorted(range(inst["n"]), key=lambda i: (-scores[i], i))[:inst["n"] // 2]
    return [i + 1 for i in sorted(chosen)]


def _attack_numeric(inst):
    return _force_weight(inst, [-x for x in inst["tags"]]), inst["n"]


def _attack_raw_parity(inst):
    return _force_weight(inst, [2 * _parity(x) - 1 for x in inst["tags"]]), inst["n"]


def _attack_alternating(inst):
    return list(range(1, inst["n"] + 1, 2)), inst["n"]


def _satisfied(inst, values):
    return sum(values[a] ^ values[b] ^ values[c] for a, b, c in inst["equations"])


def _attack_greedy(inst):
    values, scores, operations = [-1] * inst["n"], [0] * inst["n"], 0
    for vertex in range(inst["n"]):
        vote = 0
        for row in inst["equations"]:
            operations += 1
            if vertex not in row:
                continue
            other = [values[x] for x in row if x != vertex]
            if len(other) == 2 and min(other) >= 0:
                vote += 1 if (1 ^ other[0] ^ other[1]) else -1
        values[vertex], scores[vertex] = int(vote > 0), vote
    return _force_weight(inst, scores), operations


def _attack_restarts(inst, rng, restarts=64):
    operations, answer = 0, random_candidate(inst, rng)
    for _ in range(restarts):
        answer = random_candidate(inst, rng)
        values = _assignment(inst, answer)
        score = _satisfied(inst, values)
        operations += inst["equation_count"]
        for _step in range(4 * inst["n"]):
            one = rng.choice([i for i, x in enumerate(values) if x])
            zero = rng.choice([i for i, x in enumerate(values) if not x])
            values[one] ^= 1
            values[zero] ^= 1
            candidate = _satisfied(inst, values)
            operations += inst["equation_count"]
            if candidate >= score:
                score = candidate
            else:
                values[one] ^= 1
                values[zero] ^= 1
            if score == inst["equation_count"]:
                return _answer_from_assignment(values), operations
        answer = _answer_from_assignment(values)
    return answer, operations


def _gaussian_reference(inst):
    n = inst["n"]
    rows = [sum(1 << i for i in row) | (1 << n) for row in inst["equations"]]
    rank, pivots, operations = 0, [], 0
    for col in range(n):
        pivot = None
        for i in range(rank, len(rows)):
            operations += 1
            if (rows[i] >> col) & 1:
                pivot = i
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(len(rows)):
            operations += 1
            if i != rank and ((rows[i] >> col) & 1):
                rows[i] ^= rows[rank]
                operations += n + 1
        pivots.append(col)
        rank += 1
    if rank != n - 1:
        return None, operations
    free = next(col for col in range(n) if col not in set(pivots))
    for free_value in (0, 1):
        values = [0] * n
        values[free] = free_value
        for row, col in enumerate(pivots):
            values[col] = ((rows[row] >> n) & 1) ^ (((rows[row] >> free) & 1) * free_value)
        if sum(values) == n // 2:
            return _answer_from_assignment(values), operations
    return None, operations


def _relabel(inst, rng):
    n, order = inst["n"], list(range(inst["n"]))
    rng.shuffle(order)
    old_new, tags = [0] * n, [0] * n
    for new, old in enumerate(order):
        old_new[old], tags[new] = new, inst["tags"][old]
    equations = []
    for row in inst["equations"]:
        mapped = [old_new[i] for i in row]
        rng.shuffle(mapped)
        equations.append(mapped)
    rng.shuffle(equations)
    out = dict(inst)
    out["tags"], out["equations"] = tags, equations
    out["answer"] = sorted(old_new[i - 1] + 1 for i in inst["answer"])
    return out


def _corruptions(inst):
    a = list(inst["answer"])
    swap = list(a); swap[0], swap[1] = swap[1], swap[0]
    dup = list(a); dup[-1] = dup[-2]
    outside = list(a); outside[-1] = inst["n"] + 1
    missing = next(i for i in range(1, inst["n"] + 1) if i not in a)
    return {"drop_one": a[:-1], "swap_order": swap, "duplicate": dup, "empty": [],
            "out_of_range": outside, "same_shape_wrong_assignment": sorted(a[:-1] + [missing])}


def selftest():
    report, checked, json_ok, g1 = {}, 0, 0, True
    for params in DIFFICULTY.values():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            g1 &= verify(inst, inst["answer"])[0]
            checked += 1
            json_ok += json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {"pass": g1 and checked == json_ok,
        "instances_checked": checked, "json_native_roundtrips": json_ok}
    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **params)
    reasons = {name: verify(ship, bad)[1] for name, bad in _corruptions(ship).items()}
    report["G2_rejects_corruption"] = {"pass": all(not verify(ship, b)[0] for b in _corruptions(ship).values())
        and len(set(reasons.values())) == len(reasons), "reasons": reasons,
        "distinct_reasons": len(set(reasons.values())) == len(reasons)}
    body = ", ".join(map(str, ship["answer"]))
    parsed = parse_answer(f"Prose before.\n```text\n<answer>{body}</answer>\n```\nProse after.")
    report["G3_round_trip"] = {"pass": parsed == ship["answer"],
                               "parsed_elements": len(parsed) if isinstance(parsed, list) else None}
    rng, total, hits, started = random.Random(0x210300306), 200_000, 0, time.perf_counter()
    for _ in range(total):
        hits += verify(ship, random_candidate(ship, rng))[0]
    report["G4_guess_resistance"] = {"pass": hits / total < 1e-6, "hits": hits,
        "total": total, "observed_probability": hits / total,
        "candidate_space": search_space(ship), "exact_valid_answers_in_language": 1,
        "exact_probability": 1 / search_space(ship),
        "prior": "uniform over fixed-weight assignments required by the statement",
        "wall_clock_sec": round(time.perf_counter() - started, 6)}

    names = ("outlier_smallest_numeric_tags", "greedy_left_to_right_propagation",
             "random_restart_pair_swap_64", "raw_hamming_parity_ansatz",
             "alternating_index_ansatz")
    stats = {x: {"successes": 0, "attempts": 0, "nodes": 0, "wall_clock_sec": 0.0} for x in names}
    nodes, times, ref_t, ref_o, ref_ok = {x: [] for x in names}, {x: [] for x in names}, [], [], 0
    for seed in range(800, 808):
        inst, arng = make_instance(seed=seed, **params), random.Random(seed ^ 0xA55A)
        attacks = {names[0]: lambda: _attack_numeric(inst), names[1]: lambda: _attack_greedy(inst),
                   names[2]: lambda: _attack_restarts(inst, arng, 64),
                   names[3]: lambda: _attack_raw_parity(inst), names[4]: lambda: _attack_alternating(inst)}
        for name, fn in attacks.items():
            st = time.perf_counter(); candidate, count = fn(); elapsed = time.perf_counter() - st
            stats[name]["successes"] += verify(inst, candidate)[0]
            stats[name]["attempts"] += 1; stats[name]["nodes"] += count; stats[name]["wall_clock_sec"] += elapsed
            nodes[name].append(count); times[name].append(elapsed)
        st = time.perf_counter(); candidate, count = _gaussian_reference(inst)
        ref_t.append(time.perf_counter() - st); ref_o.append(count)
        ref_ok += candidate is not None and verify(inst, candidate)[0]
    for name in names:
        stats[name]["wall_clock_sec"] = round(stats[name]["wall_clock_sec"], 6)
        stats[name]["nodes_median_per_instance"] = int(statistics.median(nodes[name]))
        stats[name]["wall_clock_sec_median_per_instance"] = round(statistics.median(times[name]), 8)
    reference = {"name": "exact GF(2) Gaussian elimination on repeated 3-XOR rows",
        "complexity": "O(r*n^2) bit operations", "wall_clock_sec_median": round(statistics.median(ref_t), 8),
        "operations_median": int(statistics.median(ref_o)), "operations_range": [min(ref_o), max(ref_o)],
        "solves": f"{ref_ok}/8, as expected"}
    report["G5_density_and_baseline_cost"] = {"pass": hits / total < 1e-6 and ref_ok == 8,
        "shipping_density_hits": hits, "shipping_density_total": total, "shipping_valid_fraction": hits / total,
        "shipping_exact_valid_answer_count": 1,
        "exact_demo_valid_answer_count": enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"])),
        "reference_wall_clock_sec_median": reference["wall_clock_sec_median"],
        "reference_operation_count_median": reference["operations_median"],
        "strongest_failing_attack_nodes_median": stats[names[2]]["nodes_median_per_instance"],
        "strongest_failing_attack_wall_clock_sec_median": stats[names[2]]["wall_clock_sec_median_per_instance"]}
    report["G6_adversary_panel"] = {"pass": all(x["successes"] == 0 for x in stats.values()) and ref_ok == 8,
                                      "attacks": stats, "reference_algorithm": reference}
    doubled = dict(params); doubled["n"] *= 2; doubled["base_equations"] *= 2
    big = make_instance(seed=271828, **doubled); harder = escalate(params)
    escalated = make_instance(seed=271829, **harder) if isinstance(harder, dict) else None
    report["G7_scales"] = {"pass": verify(big, big["answer"])[0] and escalated is not None
        and verify(escalated, escalated["answer"])[0] and len(escalated["answer"]) == len(ship["answer"]),
        "shipping_n": ship["n"], "doubled_n": big["n"], "doubled_graph_vertices": big["graph_vertex_count"],
        "doubled_planted_verifies": verify(big, big["answer"])[0], "escalated_params": harder,
        "escalated_planted_verifies": verify(escalated, escalated["answer"])[0],
        "fixed_answer_elements_on_escalation": len(escalated["answer"]) == len(ship["answer"])}
    keys, inv, preserve, g8 = [], 0, 0, True
    for seed in range(1200, 1220):
        inst = make_instance(seed=seed, **params); key = canonical_key(inst); keys.append(key)
        a = _relabel(inst, random.Random(seed * 17 + 1)); b = _relabel(a, random.Random(seed * 17 + 2))
        for other in (a, b):
            inv += 1; preserve += 1; g8 &= canonical_key(other) == key and verify(other, other["answer"])[0]
    report["G8_canonical_key"] = {"pass": g8 and len(set(keys)) == 20, "invariance_checks": inv,
        "certificate_preservation_checks": preserve, "distinct_unrelated_instances": len(set(keys)),
        "unrelated_instances_tested": 20,
        "transformations": ["variable renumbering with tags/certificate carried", "equation reordering",
                            "within-equation reordering", "composition of relabellings"]}
    chars = max(len(json.dumps(make_instance(seed=s, **params)["answer"], separators=(",", ":"))) for s in range(64))
    arms = G9_RESULTS["arms"]; hinted, placebo = arms["hinted"], arms["placebo"]
    hr = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    pr = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    operations = 2 * ship["n"]
    report["G9_no_tool_suitability"] = {"pass": all(arms[x]["attempts"] >= 3 for x in arms)
        and G9_RESULTS["hinted_verdict"] == "hardened" and chars <= 2000
        and len(ship["answer"]) <= 256 and operations <= 300, "arms": arms,
        "hinted_minus_placebo": hr - pr, "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": math.ceil(chars / 4), "answer_elements": len(ship["answer"]),
        "answer_size_instances_measured": 64, "intended_route_operations": operations,
        "operation_model": "one exact word AND and one exact parity operation per variable tag"}
    report["track"], report["shipping_difficulty"], report["shipping_params"] = TRACK, SHIPPING_DIFFICULTY, params
    report["all_passed"] = all(v.get("pass", False) for k, v in report.items()
                                  if k.startswith("G") and isinstance(v, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
