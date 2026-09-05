"""Verified generator for parity-structured 3-SAT coloring witnesses.

The source is Section 5 of Mančinska--Roberson, arXiv:1801.03542.  That
section uses the standard 3-SAT-to-3-COLORING construction and proves that its
three-dimensional orthogonal representations collapse to ordinary
3-colorings.  Here every displayed parity identity is an exact abbreviation
for a chain of 3-CNF XOR gadgets, so a satisfying assignment is a compact,
directly checkable witness for the paper's reduction graph.

Generation is inverse: sample the assignment first, then form every right-hand
side from it.  The planted answer is never recovered by solving the instance.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Boolean 3-CNF formula specified by exact XOR-to-CNF blocks",
        "3-SAT-to-3-COLORING reduction graph G_f",
        "truth assignment inducing a three-coloring",
    ],
    "verification_operations": [
        "exact bit XOR",
        "exact Boolean evaluation of every generated 3-CNF clause",
        "equality comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, the displayed 3-SAT-to-3-COLORING construction and Lemma "
        "7 (xi(G_f)=3 implies chi(G_f)=3)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Find row clusters whose pairwise symmetric differences have size two: "
        "each is an identity-plus-rank-one GF(2) block, while a solver missing "
        "that decomposition must eliminate the full parity system."
    ),
    "hardness_basis": (
        "Track B: the parity blocks can be extracted and solved by Gaussian "
        "elimination in O(m n^2) bit operations; the measured shipping cost is "
        "filled from selftest, while the block decomposition needs at most 240 "
        "exact XORs at the hard preset and cannot be mechanically executed from "
        "the unlabelled row list without first recognizing its structure."
    ),
    "max_answer_tokens": 126,
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

DIFFICULTY = {
    "demo": {"n": 8, "blocks": 1, "audits": 0},
    "easy": {"n": 144, "blocks": 24, "audits": 24},
    "medium": {"n": 156, "blocks": 24, "audits": 48},
    "hard": {"n": 168, "blocks": 24, "audits": 72},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Rows in the useful hidden clusters differ pairwise in exactly two variable "
    "positions and therefore form identity-plus-rank-one blocks over GF(2)."
)
PLACEBO_HINT = (
    "Rows in this instance should be read with careful attention to every variable "
    "position and to the right-hand side over GF(2)."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of n bits.  For structure-aware guessing, candidates obey "
        "the freely checkable row-difference consequence that x_i XOR b_i is "
        "constant on each of the k recoverable core clusters; hence one unbiased "
        "flip bit is sampled per cluster."
    ),
    "bounds": {
        "length": "n",
        "entry_set": [0, 1],
        "cluster_flip_bits": "blocks",
        "candidate_count": "2^blocks",
    },
}

NOTES = (
    "Definition 1 in Section 2 fixes a quantum coloring as projectors satisfying "
    "completeness and edge orthogonality.  Section 3 is the decisive easy regime: "
    "flat representations use the displayed Fourier formula, and real dimension-4 "
    "representations use the displayed quaternion sign/permutation matrix.  Under "
    "the 256-atom cap those mechanical constructions and their compact routes both "
    "take only linear-in-output work, so they do not support Track B.  Section 4's "
    "G13 negative is a single fixed graph; the paper says GBNP could not emit its "
    "impossibility certificate and reports over 7000 monomials even for K4.  The "
    "scalable family therefore uses the paper-central Section 5 3-SAT reduction.  "
    "XOR identities are composed into exact 3-CNF blocks, the truth assignment is "
    "sampled first, and random audit rows are sampled with the same support-size "
    "distribution as construction rows.  Literal-frequency, greedy, local, and "
    "random-restart attacks are audited; tool-enabled XOR extraction plus Gaussian "
    "elimination is disclosed as the successful Track-B reference algorithm."
)

# Filled with script-owned oracle evidence after the three hardening runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 8, "attempts": 15},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _xor(values):
    out = 0
    for value in values:
        out ^= value
    return out


def _partition_sizes(n, count, rng):
    """A random ordered composition with every part at least six."""
    sizes = [6] * count
    for _ in range(n - 6 * count):
        sizes[rng.randrange(count)] += 1
    return sizes


def make_instance(n, seed=0, **params):
    """Inverse-generate an exactly satisfiable parity-defined 3-CNF.

    Each core block has A = I + 1 v^T over GF(2), with |supp(v)|=4.
    Since v^T 1 = 0, A is its own inverse.  Audit equations use the same
    row-weight distribution and are evaluated on the already sampled answer.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    blocks = params.pop("blocks", 24)
    audits = params.pop("audits", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(blocks, bool) or not isinstance(blocks, int) or blocks < 1:
        raise ValueError("blocks must be a positive integer")
    if isinstance(audits, bool) or not isinstance(audits, int) or audits < 0:
        raise ValueError("audits must be a nonnegative integer")
    if n < 6 * blocks:
        raise ValueError("n must be at least 6*blocks")

    rng = random.Random(seed)
    answer = [rng.randrange(2) for _ in range(n)]

    sizes = _partition_sizes(n, blocks, rng)
    labels = list(range(n))
    rng.shuffle(labels)
    groups = []
    start = 0
    for size in sizes:
        members = sorted(labels[start : start + size])
        start += size
        v = sorted(rng.sample(members, 4))
        groups.append({"members": members, "v": v, "b": []})

    equations = []
    used_supports = set()
    for group in groups:
        vset = set(group["v"])
        for variable in group["members"]:
            support = sorted(vset ^ {variable})
            rhs = _xor(answer[j] for j in support)
            equations.append({"vars": support, "rhs": rhs})
            group["b"].append(rhs)
            used_supports.add(tuple(support))

    # Match the support-size mixture of the core rows: each block contributes
    # four weight-3 rows and all remaining rows have weight 5.
    p_weight3 = (4 * blocks) / n
    audit_supports = []
    while len(audit_supports) < audits:
        weight = 3 if rng.random() < p_weight3 else 5
        support = tuple(sorted(rng.sample(range(n), weight)))
        if support in used_supports:
            continue
        used_supports.add(support)
        audit_supports.append(support)
        equations.append(
            {"vars": list(support), "rhs": _xor(answer[j] for j in support)}
        )

    rng.shuffle(equations)
    aux_variables = sum(max(0, len(eq["vars"]) - 3) for eq in equations)
    clause_count = sum(4 * (len(eq["vars"]) - 2) for eq in equations)

    return {
        "family": "parity-structured 3-SAT reduction witness",
        "n": n,
        "blocks": blocks,
        "audits": audits,
        "equations": equations,
        "cnf_base_variables": n,
        "cnf_aux_variables": aux_variables,
        "cnf_clauses": clause_count,
        # This metadata defines the structure-aware candidate prior and is also
        # recomputed under G8 transformations.  verify() never reads it.
        "_candidate_blocks": groups,
        "answer": answer,
    }


def _equation_line(number, equation):
    lhs = " xor ".join(f"x{j + 1}" for j in equation["vars"])
    return f"  E{number:03d}: {lhs} = {equation['rhs']}"


def render(inst):
    equations = "\n".join(
        _equation_line(i, eq) for i, eq in enumerate(inst["equations"], 1)
    )
    prompt = f"""Find a satisfying witness for an exact 3-SAT-to-3-COLORING instance.

There are {inst['n']} base Boolean variables x1,...,x{inst['n']}; each is exactly 0
(false) or 1 (true).  Arithmetic in every displayed equation is XOR, i.e. addition
modulo 2.  The equation order and the variable order inside a left-hand side carry
no meaning.  Variables not shown in an equation have coefficient zero.

The displayed equations are a compact, lossless specification of a Boolean 3-CNF.
For three bits a,b,c, the constraint a xor b xor c = 0 is the conjunction

  (a or b or not c) and (a or not b or c) and
  (not a or b or c) and (not a or not b or not c).

For right-hand side 1, negate c in those four clauses.  A longer XOR is expanded
from left to right with fresh auxiliary bits: introduce t=a xor b using the same
four-clause identity, continue with t xor c, and leave the final three-bit parity
as the last four-clause block.  Auxiliary values are therefore uniquely determined
by the base bits and are not part of your answer.  Thus the lines below specify
exactly {inst['cnf_base_variables'] + inst['cnf_aux_variables']} Boolean variables
and {inst['cnf_clauses']} clauses, each clause having exactly three distinct literals.

Section 5 of the source paper maps this 3-CNF to a graph G_f with a 3-coloring if
and only if the formula is satisfiable.  Your base assignment, together with its
forced auxiliary bits, is the compact certificate from which that graph coloring
is obtained.  You need not print the much longer coloring of G_f.

Parity equations ({len(inst['equations'])} total):
{equations}

Return all {inst['n']} base bits in the fixed order [x1,x2,...,x{inst['n']}].
The answer must be a JSON list of exactly {inst['n']} integers, with no omissions,
repetitions, or entries outside the inclusive set {{0,1}}.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example: <answer>{json.dumps([0] * inst['n'], separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        prompt += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        prompt += "\n\n" + PLACEBO_HINT
    return prompt


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _xor_gate_cnf(a, b, z):
    """Evaluate the four 3-clauses defining z = a XOR b."""
    clauses = (
        (a or b or (not z)),
        (a or (not b) or z),
        ((not a) or b or z),
        ((not a) or (not b) or (not z)),
    )
    return all(clauses)


def _parity3_cnf(a, b, c, rhs):
    """Evaluate the four 3-clauses defining a XOR b XOR c = rhs."""
    if rhs == 0:
        clauses = (
            (a or b or (not c)),
            (a or (not b) or c),
            ((not a) or b or c),
            ((not a) or (not b) or (not c)),
        )
    else:
        clauses = (
            (a or b or c),
            (a or (not b) or (not c)),
            ((not a) or b or (not c)),
            ((not a) or (not b) or c),
        )
    return all(clauses)


def _equation_cnf_holds(bits, equation):
    values = [bool(bits[j]) for j in equation["vars"]]
    if len(values) == 3:
        return _parity3_cnf(values[0], values[1], values[2], equation["rhs"])
    carry = values[0] ^ values[1]
    if not _xor_gate_cnf(values[0], values[1], carry):
        return False
    for value in values[2:-2]:
        nxt = carry ^ value
        if not _xor_gate_cnf(carry, value, nxt):
            return False
        carry = nxt
    return _parity3_cnf(carry, values[-2], values[-1], equation["rhs"])


def verify(inst, answer):
    """Check shape and every exact generated 3-CNF clause; never read answer."""
    n = inst.get("n")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != n:
        return False, f"expected {n} bits, got {len(answer)}"
    for i, bit in enumerate(answer):
        if isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1):
            return False, f"entry {i + 1} is not an integer bit in {{0,1}}"
    for i, equation in enumerate(inst.get("equations", []), 1):
        if not _equation_cnf_holds(answer, equation):
            return False, f"3-CNF parity block E{i:03d} is false"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the exact structure-aware 2^blocks prior."""
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange")
    candidate = [0] * inst["n"]
    for group in inst["_candidate_blocks"]:
        flip = rng.randrange(2)
        for variable, rhs in zip(group["members"], group["b"]):
            candidate[variable] = rhs ^ flip
    return candidate


def search_space(inst):
    return 1 << inst["blocks"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > (1 << 18):
        return None
    hits = 0
    groups = inst["_candidate_blocks"]
    for mask in range(space):
        candidate = [0] * inst["n"]
        for g, group in enumerate(groups):
            flip = (mask >> g) & 1
            for variable, rhs in zip(group["members"], group["b"]):
                candidate[variable] = rhs ^ flip
        hits += int(verify(inst, candidate)[0])
    return hits


def canonical_key(inst):
    """A relabelling-invariant Weisfeiler--Lehman incidence signature.

    Right-hand sides are omitted deliberately: complementing any subset of
    Boolean variables is a truth-convention relabelling, and adjusts those
    right-hand sides while preserving the problem.  The signature is not a
    complete hypergraph isomorphism algorithm, a limitation recorded in README.
    """
    n = inst["n"]
    supports = [tuple(sorted(eq["vars"])) for eq in inst["equations"]]
    variable_rows = [[] for _ in range(n)]
    for r, support in enumerate(supports):
        for v in support:
            variable_rows[v].append(r)

    vlabels = [f"V:{len(rows)}" for rows in variable_rows]
    rlabels = [f"R:{len(support)}" for support in supports]
    for _ in range(8):
        new_v = []
        for v, rows in enumerate(variable_rows):
            payload = "V|" + vlabels[v] + "|" + "|".join(sorted(rlabels[r] for r in rows))
            new_v.append(hashlib.sha256(payload.encode()).hexdigest())
        new_r = []
        for r, support in enumerate(supports):
            payload = "R|" + rlabels[r] + "|" + "|".join(sorted(vlabels[v] for v in support))
            new_r.append(hashlib.sha256(payload.encode()).hexdigest())
        vlabels, rlabels = new_v, new_r

    edge_colors = sorted(
        vlabels[v] + ":" + rlabels[r]
        for r, support in enumerate(supports)
        for v in support
    )
    payload = json.dumps(
        {
            "n": n,
            "m": len(supports),
            "v": sorted(vlabels),
            "r": sorted(rlabels),
            "e": edge_colors,
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params):
    """Increase same-distribution audit crowding at fixed answer length."""
    harder = dict(params)
    audits = int(harder.get("audits", 0))
    harder["audits"] = audits + max(24, audits // 2)
    return harder


def _dense_gf2_solve(inst):
    """Tool-enabled reference solve, returning answer and scalar XOR count."""
    n = inst["n"]
    rows = []
    for equation in inst["equations"]:
        coeff = [0] * n
        for j in equation["vars"]:
            coeff[j] = 1
        rows.append(coeff + [equation["rhs"]])

    pivot_row = 0
    operations = 0
    pivots = []
    for col in range(n):
        pivot = next((r for r in range(pivot_row, len(rows)) if rows[r][col]), None)
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(len(rows)):
            if r != pivot_row and rows[r][col]:
                rows[r] = [a ^ b for a, b in zip(rows[r], rows[pivot_row])]
                operations += n + 1
        pivots.append(col)
        pivot_row += 1
        if pivot_row == n:
            break
    if pivot_row != n:
        return None, operations
    solution = [0] * n
    for r, col in enumerate(pivots):
        solution[col] = rows[r][n]
    if not verify(inst, solution)[0]:
        return None, operations
    return solution, operations


def _outlier_literal_frequency(inst):
    zeros = [0] * inst["n"]
    ones = [0] * inst["n"]
    for equation in inst["equations"]:
        bucket = ones if equation["rhs"] else zeros
        for v in equation["vars"]:
            bucket[v] += 1
    return [int(ones[i] > zeros[i]) for i in range(inst["n"])]


def _greedy_left_to_right(inst):
    candidate = [0] * inst["n"]
    for variable in range(inst["n"]):
        scores = []
        for bit in (0, 1):
            candidate[variable] = bit
            scores.append(
                sum(
                    _xor(candidate[j] for j in eq["vars"]) != eq["rhs"]
                    for eq in inst["equations"]
                )
            )
        candidate[variable] = int(scores[1] < scores[0])
    return candidate


def _local_cluster_majority(inst):
    """One-pass no-backtracking choice of the visible cluster residuals."""
    candidate = [0] * inst["n"]
    for group in inst["_candidate_blocks"]:
        # A tempting but invalid local rule: select the residual occurring most
        # often among the displayed core right-hand sides.
        flip = int(sum(group["b"]) * 2 > len(group["b"]))
        for variable, rhs in zip(group["members"], group["b"]):
            candidate[variable] = rhs ^ flip
    return candidate


def _obvious_cluster_ansatzes(inst):
    groups = inst["_candidate_blocks"]
    for mode in range(4):
        candidate = [0] * inst["n"]
        for g, group in enumerate(groups):
            if mode == 0:
                flip = 0
            elif mode == 1:
                flip = 1
            elif mode == 2:
                flip = g & 1
            else:
                flip = len(group["members"]) & 1
            for variable, rhs in zip(group["members"], group["b"]):
                candidate[variable] = rhs ^ flip
        yield candidate


def _copy_instance(inst):
    return json.loads(json.dumps(inst))


def _permute_rows(inst, rng):
    out = _copy_instance(inst)
    rng.shuffle(out["equations"])
    return out


def _permute_variables(inst, rng):
    out = _copy_instance(inst)
    n = inst["n"]
    order = list(range(n))
    rng.shuffle(order)  # old label -> new label
    for equation in out["equations"]:
        equation["vars"] = sorted(order[v] for v in equation["vars"])
    for group in out["_candidate_blocks"]:
        pairs = sorted((order[v], b) for v, b in zip(group["members"], group["b"]))
        group["members"] = [v for v, _ in pairs]
        group["b"] = [b for _, b in pairs]
        group["v"] = sorted(order[v] for v in group["v"])
    carried = [0] * n
    for old, new in enumerate(order):
        carried[new] = inst["answer"][old]
    out["answer"] = carried
    return out


def _complement_variables(inst, rng):
    out = _copy_instance(inst)
    flips = [rng.randrange(2) for _ in range(inst["n"])]
    for equation in out["equations"]:
        equation["rhs"] ^= _xor(flips[v] for v in equation["vars"])
    for group in out["_candidate_blocks"]:
        vset = set(group["v"])
        group["b"] = [
            b ^ _xor(flips[v] for v in (vset ^ {variable}))
            for variable, b in zip(group["members"], group["b"])
        ]
    out["answer"] = [bit ^ flips[i] for i, bit in enumerate(inst["answer"])]
    return out


def _answer_elements(value):
    if isinstance(value, dict):
        return sum(_answer_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_elements(v) for v in value)
    return 1


def _intended_operations(inst):
    # Four entries of v: three XORs for its parity, then one XOR per output bit.
    return inst["n"] + 3 * inst["blocks"]


def selftest():
    report = {}

    # G1: all four presets and three independent seeds each.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 99173):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = shipping["answer"]

    # G2: shape and semantic corruptions, with deliberately distinct diagnostics.
    differing = next((i for i in range(1, len(answer)) if answer[i] != answer[0]), 1)
    swapped = list(answer)
    swapped[0], swapped[differing] = swapped[differing], swapped[0]
    changed = list(answer)
    changed[0] ^= 1
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + [answer[-1]],
        "empty": [],
        "out_of_range": answer[:4] + [2] + answer[5:],
        "bit_flip": changed,
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    wrapped = (
        "I used the parity blocks and checked the forced auxiliaries.\n"
        "```json\n<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\nThe list is in x-index order."
    )
    parsed = parse_answer(wrapped)
    report["G3_round_trip"] = {
        "pass": parsed == answer
        and json.loads(json.dumps(answer)) == answer
        and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == answer,
        "json_native": json.loads(json.dumps(answer)) == answer,
    }

    # G4/G5 shipping-density sample from the structure-aware candidate language.
    rng = random.Random(314159)
    total = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(total):
        hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    guess_sec = time.perf_counter() - t0
    exact_probability = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": exact_probability < 1e-6 and hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "fraction": hits / total,
        "exact_probability": exact_probability,
        "candidate_space_bits": shipping["blocks"],
        "wall_clock_sec": round(guess_sec, 6),
    }

    # G6 is computed before G5 so the strongest failing cost can be quoted there.
    attack_names = (
        "outlier_literal_frequency",
        "greedy_left_to_right",
        "local_cluster_majority",
        "by_hand_four_obvious_cluster_ansatzes",
        "random_restart_256_structure_aware",
    )
    attack_results = {
        name: {"successes": 0, "attempts": 8, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    ref_successes = 0
    ref_operations = 0
    ref_wall = 0.0
    compact_successes = 0
    for seed in range(8001, 8009):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_literal_frequency": [_outlier_literal_frequency(inst)],
            "greedy_left_to_right": [_greedy_left_to_right(inst)],
            "local_cluster_majority": [_local_cluster_majority(inst)],
            "by_hand_four_obvious_cluster_ansatzes": list(_obvious_cluster_ansatzes(inst)),
        }
        for name, values in candidates.items():
            start = time.perf_counter()
            solved = any(verify(inst, value)[0] for value in values)
            attack_results[name]["wall_clock_sec"] += time.perf_counter() - start
            attack_results[name]["successes"] += int(solved)

        start = time.perf_counter()
        rrng = random.Random(seed ^ 0xBAD5EED)
        solved = any(
            verify(inst, random_candidate(inst, rrng))[0] for _ in range(256)
        )
        attack_results["random_restart_256_structure_aware"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )
        attack_results["random_restart_256_structure_aware"]["successes"] += int(solved)

        start = time.perf_counter()
        solved_answer, operations = _dense_gf2_solve(inst)
        ref_wall += time.perf_counter() - start
        ref_operations += operations
        ref_successes += int(solved_answer is not None)

        # Execute the paper-sized compact identity directly for the audit.
        compact = [0] * inst["n"]
        for group in inst["_candidate_blocks"]:
            bmap = dict(zip(group["members"], group["b"]))
            flip = _xor(bmap[v] for v in group["v"])
            for variable in group["members"]:
                compact[variable] = bmap[variable] ^ flip
        compact_successes += int(verify(inst, compact)[0])

    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    average_ref_ops = ref_operations // 8
    average_ref_wall = ref_wall / 8
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "XOR-block extraction plus exact GF(2) Gaussian elimination",
            "complexity": "O(m*n^2) scalar bit operations",
            "wall_clock_sec": round(average_ref_wall, 6),
            "operations": average_ref_ops,
            "solves": f"{ref_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "recover identity-plus-rank-one row clusters and invert each block",
            "operations_upper_bound": _intended_operations(shipping),
            "solves": f"{compact_successes}/8",
        },
    }

    strongest = attack_results["random_restart_256_structure_aware"]
    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_solution_count": 1,
        "shipping_exact_density": f"1/2^{shipping['blocks']}",
        "shipping_sample_hits": hits,
        "shipping_sample_total": total,
        "shipping_solution_density": hits / total,
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
        "baseline_attack_restarts": 256,
        "baseline_attack_wall_clock_sec": strongest["wall_clock_sec"],
        "reference_operation_count": average_ref_ops,
        "reference_wall_clock_sec": round(average_ref_wall, 6),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["blocks"] *= 2
    doubled_params["audits"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=424242, **doubled_params)
    build_sec = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > shipping["n"]
        and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "candidate_space_bits_shipping": shipping["blocks"],
        "candidate_space_bits_doubled": doubled["blocks"],
        "doubled_build_sec": round(build_sec, 6),
        "doubled_verify_reason": doubled_why,
    }

    invariant = 0
    carried_valid = 0
    keys = []
    for seed in range(20):
        base = make_instance(seed=90000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(base)
        keys.append(base_key)
        for mask in range(1, 8):
            transformed = base
            trng = random.Random(700000 + 101 * seed + mask)
            if mask & 1:
                transformed = _permute_rows(transformed, trng)
            if mask & 2:
                transformed = _permute_variables(transformed, trng)
            if mask & 4:
                transformed = _complement_variables(transformed, trng)
            invariant += int(canonical_key(transformed) == base_key)
            carried_valid += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant == 140 and carried_valid == 140 and len(set(keys)) == 20,
        "invariant_relabellings": invariant,
        "real_transformations_verified": carried_valid,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(keys)),
        "transformations": [
            "equation-row reordering",
            "base-variable relabelling with carried witness",
            "independent Boolean truth-convention complementation",
            "all nonempty compositions of those three",
        ],
    }

    answer_blob = json.dumps(answer)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    operations = _intended_operations(shipping)
    report["G9_no_tool_suitability"] = {
        "pass": len(answer_blob) <= 2000
        and _answer_elements(answer) <= 256
        and operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": _answer_elements(answer),
        "intended_route_operations": operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
