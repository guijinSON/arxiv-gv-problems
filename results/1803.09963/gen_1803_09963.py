"""Verified LIMSAT witness generator for arXiv:1803.09963.

The paper's Section II.B turns a CNF formula into a sparse 0--1 linear
inequality system.  This module inverse-generates a satisfying assignment and
then constructs the corresponding clause columns.  The CNF happens to contain
redundant, signed 3-XOR components, but neither generation nor verification
solves the generated instance.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "sparse LIMSAT literal-clause incidence system",
        "Boolean truth assignment",
    ],
    "verification_operations": [
        "exact Boolean literal evaluation",
        "exact 0-1 clause-inequality comparison",
        "exact XOR comparison for equivalent four-clause blocks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A maximum-codegree variable pair spans a four-triple bit-recovery "
        "subsystem, whereas a mechanical solver processes the full redundant "
        "LIMSAT system."
    ),
    "hardness_basis": (
        "Track B: Section II.B permits general CNF LIMSAT instances; the reference "
        "algorithm recognizes four-clause XOR blocks and uses GF(2) Gauss-Jordan "
        "elimination in O(M*N^2) scalar bit operations (797,482 operations and "
        "0.042 s for shipping seed 314159; eight-seed mean 673,978 operations and "
        "0.042 s), while the protected-triple invariant uses 2*N XORs (224 at the "
        "initial shipping preset) and is not stated in the prompt."
    ),
    "max_answer_tokens": 84,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "Exactly n Boolean coordinates in displayed variable order; every entry is "
        "the integer 0 or 1, with n at most 256 for shipping/escalation."
    ),
    "bounds": {"dimension": "instance n", "max_dimension": 256, "alphabet_size": 2},
}

DIFFICULTY = {
    "demo": {"n": 8, "components": 2, "coverage_percent": 100},
    "easy": {"n": 64, "components": 10, "coverage_percent": 75},
    "medium": {"n": 88, "components": 12, "coverage_percent": 88},
    "hard": {"n": 112, "components": 14, "coverage_percent": 95},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "A maximum-codegree variable pair belongs to a four-triple parity invariant "
    "inside each support component."
)
PLACEBO_HINT = (
    "On every part of the instance, careful bookkeeping of signs and indices helps "
    "avoid transcription errors."
)

# Filled from the independent harden.py runs after the bare and two diagnostic
# arms have completed.  They are data, not gates; only the size/effort caps gate.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "not run: OpenRouter returned HTTP 403 key-limit errors"
EXTERNAL_BLOCKER = (
    "The required harden.py oracle loop and G9 arms could not run: every "
    "OpenRouter request returned HTTP 403, key limit exceeded. No API error was "
    "counted as an oracle failure."
)

NOTES = """
Definition: Section II.B, especially equation (2), fixes the object as a binary
literal-selection vector and the sparse clause-incidence inequalities xA <= b.
The paper removes SSP slack columns and states that LIMSAT accepts general CNF,
not only 3-CNF.  The easy route in the paper is explicit: build this matrix in
polynomial time and hand the 0-1 model to Gurobi; Section III reports seconds to
thousands of seconds.  This module therefore claims Track B, never Track A.

Generation is inverse: sample the truth vector, partition variables into hidden
components, retain a protected full-rank triple basis plus random same-form
parity rows, and emit the four CNF clauses that forbid precisely the
opposite-parity assignments.  A candidate is checked without the planted answer.
Literal polarity is neutralized exactly (each XOR block contains every sign
twice); occurrence rank, all-zero/polarity-majority, random restart, and one-pass
greedy attacks are measured.  The reference algorithm extracts the parity of
every block and performs GF(2) elimination.
""".strip()


def _component_sizes(n: int, components: int, rng: random.Random) -> list[int]:
    """A random composition with every component large enough for uniqueness."""
    if not isinstance(n, int) or not isinstance(components, int):
        raise ValueError("n and components must be integers")
    if components < 1 or n < 4 * components:
        raise ValueError("need n >= 4*components >= 4")
    sizes = [4] * components
    for _ in range(n - 4 * components):
        sizes[rng.randrange(components)] += 1
    rng.shuffle(sizes)
    return sizes


def _parity_clauses(vars3: tuple[int, int, int], rhs: int) -> list[list[int]]:
    """Four clauses equivalent to XOR(vars3) == rhs; variables are 1-based."""
    clauses: list[list[int]] = []
    for forbidden in itertools.product((0, 1), repeat=3):
        if (forbidden[0] ^ forbidden[1] ^ forbidden[2]) == rhs:
            continue
        # This clause is false exactly on `forbidden`.
        clauses.append([
            var if bit == 0 else -var for var, bit in zip(vars3, forbidden)
        ])
    return clauses


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a satisfiable native LIMSAT instance.

    The answer is sampled first.  Every subsequent clause is manufactured to
    be satisfied by it, and complete triple coverage proves uniqueness inside
    each component.  No search for a witness occurs.
    """
    components = int(params.get("components", max(1, n // 8)))
    coverage_percent = int(params.get("coverage_percent", 95))
    if not 0 <= coverage_percent <= 100:
        raise ValueError("coverage_percent must be between 0 and 100")
    rng = random.Random(seed)
    sizes = _component_sizes(n, components, rng)

    labels = list(range(1, n + 1))
    rng.shuffle(labels)
    answer = [0] * n
    blocks: list[list[int]] = []
    pos = 0
    for size in sizes:
        block = sorted(labels[pos:pos + size])
        pos += size
        # Nonconstant local witnesses defeat the constant ansatz by construction.
        weight = rng.randint(1, size - 1)
        local = [1] * weight + [0] * (size - weight)
        rng.shuffle(local)
        for v, bit in zip(block, local):
            answer[v - 1] = bit
        blocks.append(block)

    groups = []
    for block in blocks:
        anchor = tuple(block[:4])
        anchor_pair = set(anchor[:2])
        for triple in itertools.combinations(block, 3):
            protected = (
                set(triple).issubset(anchor)
                or anchor_pair.issubset(triple)
            )
            if not protected and rng.randrange(100) >= coverage_percent:
                continue
            rhs = answer[triple[0] - 1] ^ answer[triple[1] - 1] ^ answer[triple[2] - 1]
            clauses = _parity_clauses(triple, rhs)
            # Clause and literal order are deliberately semantically meaningless.
            rng.shuffle(clauses)
            for clause in clauses:
                rng.shuffle(clause)
            groups.append({"vars": list(triple), "clauses": clauses})
    groups.sort(key=lambda g: tuple(g["vars"]))

    return {
        "n": n,
        "groups": groups,
        "answer": answer,
    }


def _fmt_clause(clause: list[int]) -> str:
    return "(" + " ".join(("+" if x > 0 else "-") + str(abs(x)) for x in clause) + ")"


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "LIMSAT feasibility over a sparse clause-incidence matrix",
        "",
        f"There are {n} Boolean variables y_1,...,y_{n}.  A +i literal has value "
        "y_i; a -i literal has value 1-y_i.  Indices in the data are 1-based.",
        "Each parenthesized triple below is one LIMSAT clause column: the sum of "
        "its three literal values must be at least 1.  A row contains four such "
        "columns separated by semicolons, and every displayed column must satisfy "
        "its inequality.  Row order, column order within a row, and literal order "
        "within a column have no meaning.",
        "",
        "Find any feasible truth assignment.  Output exactly one length-n JSON "
        "array in variable order [y_1,...,y_n].  Every entry must be the integer 0 "
        "or 1; repetitions are coordinates, not a set, and no coordinate may be "
        "omitted.",
        "",
        "Sparse LIMSAT clause block:",
    ]
    for idx, group in enumerate(inst["groups"], 1):
        clauses = " ; ".join(_fmt_clause(c) for c in group["clauses"])
        lines.append(f"R{idx}: {clauses}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON array of "
        f"exactly {n} binary integers.",
        "Example format: <answer>[0, 1, 0, 1]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str):
    """Parse the last tagged JSON array, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        # A fence or a short phrase inside the tags is malformed by contract, but
        # accept a uniquely identifiable embedded JSON list when possible.
        match = re.search(r"\[[\s\S]*\]", body)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return value if isinstance(value, list) else None


def _group_rhs(group: dict) -> int:
    """Recover the XOR label from the clauses, without any planted data."""
    vars3 = group["vars"]
    if len(vars3) != 3 or len(group["clauses"]) != 4:
        raise ValueError("malformed parity block")
    clause = group["clauses"][0]
    signs = {abs(lit): (1 if lit < 0 else 0) for lit in clause}
    if set(signs) != set(vars3):
        raise ValueError("clause support does not match block")
    forbidden_parity = signs[vars3[0]] ^ signs[vars3[1]] ^ signs[vars3[2]]
    rhs = forbidden_parity ^ 1
    # Validate that every clause forbids a different assignment of the same parity.
    seen = set()
    for c in group["clauses"]:
        smap = {abs(lit): (1 if lit < 0 else 0) for lit in c}
        if set(smap) != set(vars3):
            raise ValueError("clause support does not match block")
        bits = tuple(smap[v] for v in vars3)
        if (bits[0] ^ bits[1] ^ bits[2]) != (rhs ^ 1):
            raise ValueError("four clauses do not encode one parity")
        seen.add(bits)
    if len(seen) != 4:
        raise ValueError("duplicate forbidden assignment")
    return rhs


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any candidate exactly; this function never reads inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    n = inst.get("n")
    if len(answer) != n:
        return False, f"expected {n} bits, got {len(answer)}"
    for i, bit in enumerate(answer):
        if type(bit) is not int or bit not in (0, 1):
            return False, f"entry {i + 1} is not the integer 0 or 1"
    try:
        for row, group in enumerate(inst["groups"], 1):
            a, b, c = group["vars"]
            got = answer[a - 1] ^ answer[b - 1] ^ answer[c - 1]
            want = _group_rhs(group)
            for column, clause in enumerate(group["clauses"], 1):
                literal_sum = sum(
                    answer[lit - 1] if lit > 0 else 1 - answer[-lit - 1]
                    for lit in clause
                )
                if literal_sum < 1:
                    return False, (
                        f"row R{row} column {column} has literal sum {literal_sum} < 1 "
                        f"(variables ({a},{b},{c}) have XOR {got}; this four-column "
                        f"block requires XOR {want})"
                    )
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    return [rng.randrange(2) for _ in range(inst["n"])]


def search_space(inst: dict) -> int:
    return 1 << inst["n"]


def enumerate_all(inst: dict):
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for mask in range(1 << n):
        candidate = [(mask >> i) & 1 for i in range(n)]
        if verify(inst, candidate)[0]:
            count += 1
    return count


class _DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a


def canonical_key(inst: dict) -> str:
    """Exact key under variable renaming, sign switching, and input reordering.

    The key uses exact support-hypergraph invariants and intentionally ignores all
    parity labels, because independent polarity switching can carry those labels
    to one another.  Hypergraph isomorphism is not solved; the documented degree,
    pair-codegree and row-count signature is the strongest cheap invariant used.
    """
    n = inst["n"]
    dsu = _DSU(n)
    for group in inst["groups"]:
        a, b, c = (v - 1 for v in group["vars"])
        dsu.union(a, b)
        dsu.union(a, c)
    vertices: dict[int, list[int]] = {}
    for v in range(n):
        root = dsu.find(v)
        vertices.setdefault(root, []).append(v)
    signatures = []
    for verts in vertices.values():
        vset = set(verts)
        supports = [tuple(v - 1 for v in g["vars"]) for g in inst["groups"]
                    if g["vars"][0] - 1 in vset]
        degree = {v: 0 for v in verts}
        codegree = {(a, b): 0 for a, b in itertools.combinations(verts, 2)}
        for support in supports:
            for v in support:
                degree[v] += 1
            for a, b in itertools.combinations(sorted(support), 2):
                codegree[(a, b)] += 1
        signatures.append([
            len(verts),
            len(supports),
            sorted(degree.values()),
            sorted(codegree.values()),
        ])
    signatures.sort(key=lambda x: json.dumps(x, separators=(",", ":")))
    return json.dumps({"n": n, "components": signatures}, separators=(",", ":"))


def escalate(params: dict):
    """Increase redundant constraint crowding while keeping answer length fixed."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p["n"])
    components = int(p.get("components", max(1, n // 8)))
    coverage = int(p.get("coverage_percent", 95))
    if coverage < 99:
        p["coverage_percent"] = min(99, coverage + 2)
        return p
    if components > 7:
        p["components"] = max(7, components - 2)
        return p
    # Complete triple coverage has exhausted the fixed-answer crowding axis.
    # A longer vector would exceed the 300-operation compact-route cap first.
    return "cap_bound"


def _reference_solve(inst: dict):
    """Polynomial reference algorithm: XOR extraction + GF(2) Gauss-Jordan.

    Returns (solution, metrics).  Operation count is scalar Boolean work: parsing
    each signed literal plus N+1 bit XORs for every packed row operation.
    """
    n = inst["n"]
    rows: list[list[int]] = []
    operations = 0
    for group in inst["groups"]:
        mask = 0
        for v in group["vars"]:
            mask |= 1 << (v - 1)
            operations += 1
        rhs = _group_rhs(group)
        operations += 12  # inspect four clauses with three signed literals each
        rows.append([mask, rhs])

    rank = 0
    row_xors = 0
    pivot_cols: list[int] = []
    for col in range(n):
        pivot = next((r for r in range(rank, len(rows)) if (rows[r][0] >> col) & 1), None)
        operations += max(0, len(rows) - rank)
        if pivot is None:
            continue
        if pivot != rank:
            rows[rank], rows[pivot] = rows[pivot], rows[rank]
            operations += 1
        pmask, prhs = rows[rank]
        for r in range(len(rows)):
            if r != rank and ((rows[r][0] >> col) & 1):
                rows[r][0] ^= pmask
                rows[r][1] ^= prhs
                row_xors += 1
                operations += n + 1
        pivot_cols.append(col)
        rank += 1
        if rank == n:
            break
    if rank != n:
        return None, {"rank": rank, "row_xors": row_xors, "operations": operations}
    solution = [0] * n
    for r, col in enumerate(pivot_cols):
        solution[col] = rows[r][1]
    return solution, {"rank": rank, "row_xors": row_xors, "operations": operations}


def _attack_outlier_occurrence(inst: dict):
    n = inst["n"]
    degree = [0] * n
    for group in inst["groups"]:
        for v in group["vars"]:
            degree[v - 1] += 1
    order = sorted(range(n), key=lambda i: (-degree[i], i))
    candidate = [0] * n
    for rank, v in enumerate(order):
        candidate[v] = rank & 1
    return candidate


def _attack_literal_majority(inst: dict):
    n = inst["n"]
    score = [0] * n
    for group in inst["groups"]:
        for clause in group["clauses"]:
            for lit in clause:
                score[abs(lit) - 1] += 1 if lit > 0 else -1
    return [1 if x > 0 else 0 for x in score]


def _attack_one_pass_greedy(inst: dict):
    candidate = [0] * inst["n"]
    for group in inst["groups"]:
        a, b, c = group["vars"]
        if (candidate[a - 1] ^ candidate[b - 1] ^ candidate[c - 1]) != _group_rhs(group):
            # Deliberately myopic: repair the earliest coordinate and never revisit.
            candidate[min(a, b, c) - 1] ^= 1
    return candidate


def _transform_instance(inst: dict, rng: random.Random, *, relabel: bool, switch: bool, reorder: bool):
    n = inst["n"]
    perm = list(range(n))
    if relabel:
        rng.shuffle(perm)  # old zero-based coordinate -> new zero-based coordinate
    flips = [rng.randrange(2) if switch else 0 for _ in range(n)]
    answer = [0] * n
    for old, bit in enumerate(inst["answer"]):
        answer[perm[old]] = bit ^ flips[old]

    groups = []
    for old_group in inst["groups"]:
        new_clauses = []
        for clause in old_group["clauses"]:
            nc = []
            for lit in clause:
                old = abs(lit) - 1
                positive = lit > 0
                if flips[old]:
                    positive = not positive
                nv = perm[old] + 1
                nc.append(nv if positive else -nv)
            if reorder:
                rng.shuffle(nc)
            new_clauses.append(nc)
        if reorder:
            rng.shuffle(new_clauses)
        new_vars = sorted(perm[v - 1] + 1 for v in old_group["vars"])
        groups.append({"vars": new_vars, "clauses": new_clauses})
    if reorder:
        rng.shuffle(groups)
    return {"n": n, "groups": groups, "answer": answer}


def _answer_elements(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_elements(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: all rungs, several independent seeds.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = shipping["answer"]
    different = next((i for i in range(1, len(answer)) if answer[i] != answer[0]), None)
    swapped = answer[:]
    if different is not None:
        swapped[0], swapped[different] = swapped[different], swapped[0]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_unequal": swapped,
        "duplicate_one": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [2] + answer[1:],
    }
    g2_results = {}
    for name, bad in corruptions.items():
        ok, why = verify(shipping, bad)
        g2_results[name] = {"rejected": not ok, "reason": why}
    reasons = [r["reason"] for r in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(r["rejected"] for r in g2_results.values()) and len(set(reasons)) == len(reasons),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I checked the clause inequalities.\n```text\n"
        + "<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\nThat is my final assignment."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(shipping, parsed)[0],
        "parsed_matches": parsed == answer,
    }

    samples = 200_000
    sample_rng = random.Random(0x180309963)
    hits = 0
    t0 = time.perf_counter()
    for _ in range(samples):
        if verify(shipping, random_candidate(shipping, sample_rng))[0]:
            hits += 1
    density_elapsed = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": search_space(shipping),
        "sampler": "uniform over all length-n binary vectors (all stated shape constraints enforced)",
    }

    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    t0 = time.perf_counter()
    ref_answer, ref_metrics = _reference_solve(shipping)
    ref_wall = time.perf_counter() - t0
    ref_ok = ref_answer is not None and verify(shipping, ref_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": hits / samples < 1e-6 and ref_ok and demo_count == 1,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_density_wall_seconds": round(density_elapsed, 6),
        "demo_exact_solution_count": demo_count,
        "demo_search_space": search_space(demo),
        "baseline_wall_seconds": round(ref_wall, 6),
        "baseline_operations": ref_metrics["operations"],
        "baseline_row_xors": ref_metrics["row_xors"],
        "baseline_rank": ref_metrics["rank"],
    }

    attack_names = (
        "outlier_occurrence_rank",
        "literal_polarity_majority",
        "random_restart_256",
        "one_pass_clause_greedy",
    )
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_seconds = []
    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    for trial, seed in enumerate(range(801, 809)):
        inst = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_occurrence_rank": [_attack_outlier_occurrence(inst)],
            "literal_polarity_majority": [_attack_literal_majority(inst)],
            "random_restart_256": [
                random_candidate(inst, random.Random(seed * 1009 + j)) for j in range(256)
            ],
            "one_pass_clause_greedy": [_attack_one_pass_greedy(inst)],
        }
        for name, tries in candidates.items():
            if any(verify(inst, candidate)[0] for candidate in tries):
                attack_results[name]["successes"] += 1
        rt0 = time.perf_counter()
        solved, metrics = _reference_solve(inst)
        reference_seconds.append(time.perf_counter() - rt0)
        reference_operations.append(metrics["operations"])
        if solved is not None and verify(inst, solved)[0]:
            reference_successes += 1
    all_failed = all(r["successes"] == 0 for r in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "four-clause XOR recognition plus exact GF(2) Gauss-Jordan elimination",
            "complexity": "O(M*N^2) scalar Boolean operations",
            "wall_clock_sec_mean": round(sum(reference_seconds) / len(reference_seconds), 6),
            "wall_clock_sec_max": round(max(reference_seconds), 6),
            "operations_mean": round(sum(reference_operations) / len(reference_operations)),
            "operations_max": max(reference_operations),
            "solves": f"{reference_successes}/8, as expected for Track B",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["components"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_groups": len(doubled["groups"]),
    }

    invariant_checks = 0
    transform_checks = 0
    invariant_failures = []
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=seed, **ship_params)
        base_key = canonical_key(inst)
        distinct_keys.append(base_key)
        variants = (
            _transform_instance(inst, random.Random(10000 + seed), relabel=True, switch=False, reorder=False),
            _transform_instance(inst, random.Random(20000 + seed), relabel=False, switch=True, reorder=True),
            _transform_instance(inst, random.Random(30000 + seed), relabel=True, switch=True, reorder=True),
        )
        for variant in variants:
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                invariant_failures.append(seed)
            transform_checks += 1
            if not verify(variant, variant["answer"])[0]:
                invariant_failures.append(f"transform-{seed}")
    distinct = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "transformations_verified": transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "failures": invariant_failures,
        "symmetries": [
            "variable renumbering",
            "independent Boolean polarity switching",
            "group/clause/literal reordering",
            "all three composed",
        ],
    }

    answer_blob = json.dumps(answer)
    chars = len(answer_blob)
    tokens = math.ceil(chars / 4)
    elements = _answer_elements(answer)
    operations = 2 * shipping["n"]
    arms = json.loads(json.dumps(G9_ARM_RESULTS))
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and elements <= 256 and operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["external_blocker"] = EXTERNAL_BLOCKER
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
