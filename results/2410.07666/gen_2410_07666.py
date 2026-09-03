"""Inverse generator for the NAE signal core of flat-folding gadgets.

The generated instances use the two-state variable and not-all-equal clause
gadgets described in Section 3.3 of arXiv:2410.07666.  This is the finite,
combinatorial signal layer of the crease-pattern reduction: a witness chooses
one of the two local foldings of every variable signal.

Standard library only; importing this module has no side effects.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import time
from typing import Any


NATIVE: dict = {
    "domain": "logic",
    "core": "csp_sat",
    "objects": [
        "Boolean signal variables",
        "signed not-all-equal 3-clauses",
    ],
    "intuition": "constraint satisfaction under signal-switching symmetry",
    "reduction": (
        "Section 3.3 and Theorem 2: this retains the Boolean variable/clause "
        "signal layer of the flat-folding reduction, while discarding the "
        "crease geometry, pleats, and bounded-ply embedding"
    ),
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "For an n-signal instance, one semantic Boolean assignment represented "
        "canonically by exactly n signed integer tokens in increasing absolute-"
        "index order: token +i selects state 1 and token -i selects state 0, "
        "for every index i in 1..n exactly once. The verifier also accepts token "
        "permutations as equivalent wire encodings; they are not distinct members "
        "of the sampled certificate language."
    ),
    "bounds": {
        "token_count": "inst['n']",
        "absolute_index_min": 1,
        "absolute_index_max": "inst['n']",
        "occurrences_per_index": 1,
        "sign_choices_per_index": 2,
        "canonical_order": "increasing absolute index",
    },
}


DIFFICULTY = {
    "easy": {"n": 12, "degree": 6},
    "medium": {"n": 192, "degree": 7},
    "hard": {"n": 240, "degree": 7},
}
SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Definition and hardness.  Section 3.3, especially the definition immediately
before Theorem 2, fixes NAE3SAT: each triple of (possibly negated) Boolean
signals must not be all equal.  The crease-pattern reduction represents every
variable by one of two foldings and every clause by a gadget that folds exactly
for NAE triples.  Theorem 2 transfers the ETH lower bound to flat folding even
at bounded ply.  This module exposes that reduction's finite signal-consistency
core rather than pretending to provide the paper's geometric coordinates.

Easy regime avoided.  Theorem 1 gives time (p!)^O(w) n^2 for ply p and cell-
adjacency treewidth w.  The plants here have bounded occurrence degree but use
random regular factor graphs, whose width is not artificially bounded; n grows
at fixed density.  The Section 5 reconfiguration idea was rejected because its
PSPACE witness can be exponentially long, whereas bounding the planted path
would leave the paper's hardness theorem inapplicable.

Inverse generation and attacks.  A uniformly random folding state is drawn
first.  Each variable is then put in exactly `degree` clause slots, and every
clause polarity is drawn uniformly from the six polarities accepted by the
plant.  Plant and non-plant occurrences therefore have the same distribution,
and every variable has the same degree.  Tests include literal-imbalance
rounding, deterministic greedy assignment, randomized min-conflicts restarts,
a capped DPLL solver with unit propagation (the standard SAT attack), and a
signed co-occurrence power iteration aimed specifically at planted leakage.
This experiment is REJECTED: proper min-conflicts restarts solve all eight
shipping test seeds.  The retained module and failing self-test are diagnostic
evidence, not a generator that should be shipped.
""".strip()


def _validate_params(n: int, degree: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    if n % 3:
        raise ValueError("n must be divisible by 3")
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 2:
        raise ValueError("degree must be an integer at least 2")
    if degree > (n - 1) * (n - 2) // 2:
        raise ValueError("degree is too large for distinct 3-variable clauses")


def _tokens_from_bits(bits: list[int]) -> list[int]:
    return [i + 1 if bit else -(i + 1) for i, bit in enumerate(bits)]


def _bits_from_tokens(n: int, answer: Any) -> tuple[list[int] | None, str]:
    if not isinstance(answer, list):
        return None, "answer must be a list of signed integer tokens"
    if not answer:
        return None, "answer is empty"
    if len(answer) != n:
        return None, f"wrong token count: expected {n}, got {len(answer)}"
    bits = [-1] * n
    for pos, token in enumerate(answer, 1):
        if isinstance(token, bool) or not isinstance(token, int):
            return None, f"token {pos} is not an integer"
        if token == 0 or abs(token) > n:
            return None, f"variable index out of range at token {pos}: {token}"
        var = abs(token) - 1
        if bits[var] != -1:
            return None, f"duplicate variable index {var + 1}"
        bits[var] = int(token > 0)
    if any(bit < 0 for bit in bits):
        return None, "one or more variable indices are missing"
    return bits, "ok"


def _satisfies_bits(inst: dict, bits: list[int]) -> bool:
    for clause in inst["clauses"]:
        vals = [bits[v] ^ neg for v, neg in clause]
        if vals[0] == vals[1] == vals[2]:
            return False
    return True


def make_instance(n: int, seed: int = 0, degree: int = 6, **params: Any) -> dict:
    """Sample a folding-state witness first, then build accepted NAE gadgets.

    ``n`` is both the number of two-state signals and the size parameter.  The
    incidence hypergraph is regular: each signal occurs exactly ``degree``
    times, so the number of gadgets is n*degree/3.
    """
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    _validate_params(n, degree)
    rng = random.Random(seed)

    # G requires the answer to exist before the problem.  Keep this statement
    # before every draw used for clauses or labels.
    planted_bits = [rng.randrange(2) for _ in range(n)]

    # Each round is a random partition into triples.  Repeating it `degree`
    # times makes all per-variable degrees exactly equal.  Duplicate triples
    # are rejected without conditioning on the planted values.
    triples: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    rounds = 0
    retries = 0
    while rounds < degree:
        order = list(range(n))
        rng.shuffle(order)
        batch = [tuple(sorted(order[i:i + 3])) for i in range(0, n, 3)]
        if len(set(batch)) != len(batch) or any(t in seen for t in batch):
            retries += 1
            if retries > 100_000:
                raise RuntimeError("could not construct a simple regular clause hypergraph")
            continue
        triples.extend(batch)
        seen.update(batch)
        rounds += 1

    clauses: list[list[list[int]]] = []
    for triple in triples:
        allowed = []
        for mask in range(8):
            negs = [(mask >> j) & 1 for j in range(3)]
            vals = [planted_bits[triple[j]] ^ negs[j] for j in range(3)]
            if not (vals[0] == vals[1] == vals[2]):
                allowed.append(negs)
        negs = allowed[rng.randrange(len(allowed))]
        entries = [[triple[j], negs[j]] for j in range(3)]
        rng.shuffle(entries)
        clauses.append(entries)
    rng.shuffle(clauses)

    # A final signed variable relabelling erases the order in which the plant
    # and regular partitions were sampled while preserving the formula.
    permutation = list(range(n))
    rng.shuffle(permutation)
    switches = [rng.randrange(2) for _ in range(n)]
    relabelled_bits = [0] * n
    for old, new in enumerate(permutation):
        relabelled_bits[new] = planted_bits[old] ^ switches[old]
    relabelled_clauses = []
    for clause in clauses:
        relabelled = [[permutation[v], neg ^ switches[v]] for v, neg in clause]
        rng.shuffle(relabelled)
        relabelled_clauses.append(relabelled)
    rng.shuffle(relabelled_clauses)

    return {
        "family": "flat-folding-nae-signal-consistency",
        "n": n,
        "degree": degree,
        "clauses": relabelled_clauses,
        "answer": _tokens_from_bits(relabelled_bits),
    }


def render(inst: dict) -> str:
    """Render a complete, standalone folding-signal consistency problem."""
    n = inst["n"]
    lines = [
        "FLAT-FOLDING SIGNAL CONSISTENCY",
        "",
        "A crease-pattern variable gadget has two possible local flat-folded",
        "states, encoded 0 and 1.  Choose a state x_i for every signal i.",
        "Each listed clause gadget touches exactly three signed signals and is",
        "legal precisely when their three evaluated values are NOT all equal.",
        "A token +i evaluates to x_i; a token -i evaluates to 1-x_i.",
        "Thus each clause must contain at least one evaluated 0 and at least one",
        "evaluated 1.",
        "",
        f"There are {n} signals, numbered 1 through {n} inclusive.",
        f"There are {len(inst['clauses'])} clause gadgets:",
    ]
    for j, clause in enumerate(inst["clauses"], 1):
        toks = []
        for v, neg in clause:
            idx = v + 1
            toks.append(f"-{idx}" if neg else f"+{idx}")
        lines.append(f"C{j:03d}: {' '.join(toks)}")
    example = " ".join(str(i + 1 if i % 2 == 0 else -(i + 1)) for i in range(n))
    lines.extend([
        "",
        "Return exactly one signed integer for each signal.  Token +i means",
        "x_i=1 and token -i means x_i=0.  Every absolute index 1..n must occur",
        "exactly once; token order is irrelevant and repeated indices are not",
        "allowed.",
        "",
        "Give your final answer inside <answer></answer> tags, as a",
        "space-separated list of the signed integers.",
        f"Example format: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed delimited signed-integer list."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    for body in reversed(blocks):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            body = re.sub(r"^```[^\n]*\n?", "", body)
            body = re.sub(r"\n?```$", "", body).strip()
        if not body or not re.fullmatch(r"[+\-0-9,\s]+", body):
            continue
        raw = [p for p in re.split(r"[\s,]+", body) if p]
        try:
            return [int(p) for p in raw]
        except (TypeError, ValueError, OverflowError):
            continue
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any complete legal signal assignment; never inspect the plant."""
    bits, reason = _bits_from_tokens(inst["n"], answer)
    if bits is None:
        return False, reason
    for j, clause in enumerate(inst["clauses"], 1):
        vals = [bits[v] ^ neg for v, neg in clause]
        if vals[0] == vals[1] == vals[2]:
            return False, f"clause C{j:03d} is monochromatic ({vals[0]},{vals[1]},{vals[2]})"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample semantic assignments, with all syntax enforced."""
    bits = [rng.randrange(2) for _ in range(inst["n"])]
    # Canonical token order avoids pretending that the semantically irrelevant
    # n! orderings enlarge the guessing space.
    return _tokens_from_bits(bits)


def search_space(inst: dict) -> int | None:
    """Count semantic candidates; token reorderings are not distinct answers."""
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Count valid assignments exactly when at most 2^20 must be inspected."""
    n = inst["n"]
    if n > 20:
        return None
    total = 0
    for mask in range(1 << n):
        bits = [(mask >> i) & 1 for i in range(n)]
        total += int(_satisfies_bits(inst, bits))
    return total


def _trace_invariants(inst: dict, signed: bool, max_power: int = 16) -> list[int]:
    """Traces of adjacency powers of the (signed) incidence graph.

    Variable or clause complementation is diagonal switching of the signed
    adjacency matrix, and relabelling is permutation similarity, so every trace
    is invariant under all semantic relabellings used by this family.
    """
    n = inst["n"]
    m = len(inst["clauses"])
    size = n + m
    adj: list[list[tuple[int, int]]] = [[] for _ in range(size)]
    for j, clause in enumerate(inst["clauses"]):
        cnode = n + j
        for v, neg in clause:
            weight = -1 if signed and neg else 1
            adj[v].append((cnode, weight))
            adj[cnode].append((v, weight))
    traces = [0] * (max_power + 1)
    for start in range(size):
        vec = [0] * size
        vec[start] = 1
        for power in range(1, max_power + 1):
            nxt = [0] * size
            for u, value in enumerate(vec):
                if value:
                    for v, weight in adj[u]:
                        nxt[v] += value * weight
            vec = nxt
            if power >= 4 and power % 2 == 0:
                traces[power] += vec[start]
    return [traces[k] for k in range(4, max_power + 1, 2)]


def canonical_key(inst: dict) -> str:
    """Return a switching- and relabelling-invariant structural fingerprint.

    Exact signed-hypergraph isomorphism is not known to be cheap.  The key uses
    unsigned and switching-invariant signed spectral moments through degree 16;
    it can theoretically collide on cospectral nonisomorphic instances, which
    is disclosed in README.md.
    """
    payload = {
        "n": inst["n"],
        "m": len(inst["clauses"]),
        "unsigned_traces": _trace_invariants(inst, False),
        "signed_traces": _trace_invariants(inst, True),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "nae-switching-moments-v1:" + hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the factor-graph size at fixed, near-threshold density."""
    n = int(params.get("n", 0))
    degree = int(params.get("degree", 6))
    if n >= 240:
        return None
    harder_n = n + 48
    harder_n += (-harder_n) % 3
    return {"n": harder_n, "degree": degree}


# ---------------------------------------------------------------------------
# Adversary panel


def _literal_imbalance_attack(inst: dict) -> list[int]:
    score = [0] * inst["n"]
    for clause in inst["clauses"]:
        for v, neg in clause:
            score[v] += -1 if neg else 1
    bits = [int(s >= 0) for s in score]
    return _tokens_from_bits(bits)


def _greedy_left_to_right(inst: dict) -> list[int]:
    n = inst["n"]
    bits = [-1] * n
    incident: list[list[list[list[int]]]] = [[] for _ in range(n)]
    for clause in inst["clauses"]:
        for v, _ in clause:
            incident[v].append(clause)
    order = sorted(range(n), key=lambda v: (-len(incident[v]), v))

    def penalty(v: int, value: int) -> tuple[int, int]:
        bits[v] = value
        dead = 0
        bias = 0
        for clause in incident[v]:
            vals = [bits[x] ^ neg for x, neg in clause if bits[x] >= 0]
            if len(vals) == 3 and vals[0] == vals[1] == vals[2]:
                dead += 1
            elif len(vals) >= 2 and all(z == vals[0] for z in vals):
                bias += 1
        bits[v] = -1
        return dead, bias

    for v in order:
        p0 = penalty(v, 0)
        p1 = penalty(v, 1)
        bits[v] = 0 if p0 <= p1 else 1
    return _tokens_from_bits(bits)


def _cnf_clauses(inst: dict) -> list[tuple[int, int, int]]:
    cnf = []
    for clause in inst["clauses"]:
        lits = tuple((v + 1) * (-1 if neg else 1) for v, neg in clause)
        cnf.append(lits)
        cnf.append(tuple(-lit for lit in lits))
    return cnf


def _dpll_attack(inst: dict, node_limit: int = 2000) -> list[int] | None:
    """Small standard DPLL: unit propagation, occurrence branching, hard cap."""
    n = inst["n"]
    clauses = _cnf_clauses(inst)
    occurrences = [0] * n
    for clause in clauses:
        for lit in clause:
            occurrences[abs(lit) - 1] += 1
    nodes = 0

    def propagate(assign: list[int]) -> bool:
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                satisfied = False
                unassigned = []
                for lit in clause:
                    value = assign[abs(lit) - 1]
                    if value < 0:
                        unassigned.append(lit)
                    elif (value == 1) == (lit > 0):
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unassigned:
                    return False
                if len(unassigned) == 1:
                    lit = unassigned[0]
                    var = abs(lit) - 1
                    need = int(lit > 0)
                    if assign[var] >= 0 and assign[var] != need:
                        return False
                    if assign[var] < 0:
                        assign[var] = need
                        changed = True
        return True

    def solve(assign: list[int]) -> list[int] | None:
        nonlocal nodes
        if nodes >= node_limit:
            return None
        nodes += 1
        work = assign[:]
        if not propagate(work):
            return None
        if all(v >= 0 for v in work):
            return work
        var = max((i for i, v in enumerate(work) if v < 0),
                  key=lambda i: (occurrences[i], -i))
        for value in (0, 1):
            child = work[:]
            child[var] = value
            result = solve(child)
            if result is not None:
                return result
            if nodes >= node_limit:
                break
        return None

    found = solve([-1] * n)
    return _tokens_from_bits(found) if found is not None else None


def _spectral_rounding_attack(inst: dict) -> list[int] | None:
    """Power iteration on the signed pair co-occurrence signal, then round."""
    n = inst["n"]
    matrix: list[dict[int, float]] = [dict() for _ in range(n)]
    for clause in inst["clauses"]:
        for a in range(3):
            va, na = clause[a]
            for b in range(a + 1, 3):
                vb, nb = clause[b]
                weight = -1.0 if na == nb else 1.0
                matrix[va][vb] = matrix[va].get(vb, 0.0) + weight
                matrix[vb][va] = matrix[vb].get(va, 0.0) + weight
    # Several deterministic starts prevent the all-symmetric start from being
    # an accidental blind spot while keeping this a cheap rounding attack.
    for start in range(8):
        vec = [math.sin((i + 1) * (start + 1) * 1.61803398875) for i in range(n)]
        for _ in range(80):
            nxt = [sum(weight * vec[j] for j, weight in row.items())
                   for row in matrix]
            norm = math.sqrt(sum(x * x for x in nxt)) or 1.0
            vec = [x / norm for x in nxt]
        for reverse in (False, True):
            bits = [int((x >= 0) ^ reverse) for x in vec]
            candidate = _tokens_from_bits(bits)
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _walksat_random_restart(inst: dict, rng: random.Random,
                            restarts: int = 32,
                            steps_per_variable: int = 200,
                            stats: dict[str, int] | None = None) -> list[int] | None:
    """Random-restart min-conflicts with a 10% noisy WalkSAT move."""
    n = inst["n"]
    clauses = inst["clauses"]
    incident: list[list[int]] = [[] for _ in range(n)]
    for j, clause in enumerate(clauses):
        for v, _ in clause:
            incident[v].append(j)

    def violated(j: int, bits: list[int]) -> bool:
        clause = clauses[j]
        a = bits[clause[0][0]] ^ clause[0][1]
        b = bits[clause[1][0]] ^ clause[1][1]
        c = bits[clause[2][0]] ^ clause[2][1]
        return a == b == c

    restarts_started = 0
    iterations = 0
    for _ in range(restarts):
        restarts_started += 1
        bits = [rng.randrange(2) for _ in range(n)]
        bad = {j for j in range(len(clauses)) if violated(j, bits)}
        for _ in range(steps_per_variable * n):
            if not bad:
                if stats is not None:
                    stats.update({
                        "restarts_started": restarts_started,
                        "iterations": iterations,
                        "restart_limit": restarts,
                        "iteration_limit": restarts * steps_per_variable * n,
                    })
                return _tokens_from_bits(bits)
            clause_index = rng.choice(tuple(bad))
            variables = [v for v, _ in clauses[clause_index]]
            if rng.random() < 0.10:
                chosen = rng.choice(variables)
            else:
                scores = []
                for v in variables:
                    before = sum(j in bad for j in incident[v])
                    bits[v] ^= 1
                    after = sum(violated(j, bits) for j in incident[v])
                    bits[v] ^= 1
                    scores.append((after - before, v))
                best = min(score for score, _ in scores)
                chosen = rng.choice([v for score, v in scores if score == best])
            bits[chosen] ^= 1
            for j in incident[chosen]:
                if violated(j, bits):
                    bad.add(j)
                else:
                    bad.discard(j)
            iterations += 1
    if stats is not None:
        stats.update({
            "restarts_started": restarts_started,
            "iterations": iterations,
            "restart_limit": restarts,
            "iteration_limit": restarts * steps_per_variable * n,
        })
    return None


def _transformed_instance(inst: dict, rng: random.Random) -> tuple[dict, list[int]]:
    """Apply all semantic relabellings and carry the planted witness through."""
    n = inst["n"]
    original_bits, why = _bits_from_tokens(n, inst["answer"])
    if original_bits is None:
        raise AssertionError(why)
    permutation = list(range(n))
    rng.shuffle(permutation)
    variable_switch = [rng.randrange(2) for _ in range(n)]
    clauses = []
    for clause in inst["clauses"]:
        clause_switch = rng.randrange(2)
        moved = [[permutation[v], neg ^ variable_switch[v] ^ clause_switch]
                 for v, neg in clause]
        rng.shuffle(moved)
        clauses.append(moved)
    rng.shuffle(clauses)
    moved_bits = [0] * n
    for old, new in enumerate(permutation):
        moved_bits[new] = original_bits[old] ^ variable_switch[old]
    transformed = {
        "family": inst["family"],
        "n": n,
        "degree": inst["degree"],
        "clauses": clauses,
        "answer": _tokens_from_bits(moved_bits),
    }
    return transformed, transformed["answer"]


def selftest() -> dict:
    """Run all mandatory gates and return their measured, JSON-safe report."""
    report: dict[str, Any] = {}

    # G1: every preset and several independent seeds.
    g1_attempts = 0
    g1_failures = []
    for name, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": name, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "attempts": g1_attempts, "failures": g1_failures,
    }

    # G2: five meaningfully different corruptions, five distinct diagnostics.
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90125, **ship)
    answer = list(inst["answer"])
    sign_swap = None
    for i in range(len(answer)):
        trial = answer[:]
        trial[i] = -trial[i]
        if not verify(inst, trial)[0]:
            sign_swap = trial
            break
    corruptions = {
        "drop_one": answer[:-1],
        "single_sign_swap": sign_swap if sign_swap is not None else answer[:],
        "duplicate_index": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": [inst["n"] + 1] + answer[1:],
    }
    rejected = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in rejected.values())
                and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and a Markdown fence around the contract.
    body = " ".join(map(str, answer))
    response = ("I checked every clause.\n\n```text\n"
                f"<answer>{body}</answer>\n```\nThat is my final assignment.")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer, "parsed_tokens": len(parsed) if isinstance(parsed, list) else None,
    }

    # G4: uniform over semantic assignments, already enforcing all syntax.
    guess_inst = make_instance(seed=314159, **ship)
    guess_rng = random.Random(271828)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(guess_inst, guess_rng)
        hits += int(verify(guess_inst, candidate)[0])
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "prior": "uniform over 2^n complete assignments; token syntax and uniqueness enforced",
        "naive_semantic_space": search_space(guess_inst),
    }

    # G5: measure the exact shipping instance used by G4.  enumerate_all is
    # deliberately capped, so its None result triggers sampling over precisely
    # CERTIFICATE_LANGUAGE.  Keep the small exact count only as calibration.
    shipping_exact = enumerate_all(guess_inst)
    density_method = ("exact enumeration" if shipping_exact is not None
                      else "uniform random_candidate sampling")
    shipping_fraction = (
        shipping_exact / search_space(guess_inst)
        if shipping_exact is not None else probability
    )

    baseline_stats: dict[str, int] = {}
    baseline_rng = random.Random(314159 ^ 0x5EEDBEEF)
    baseline_started = time.perf_counter()
    baseline_candidate = _walksat_random_restart(
        guess_inst, baseline_rng, restarts=32, steps_per_variable=200,
        stats=baseline_stats)
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_solved = (
        baseline_candidate is not None
        and verify(guess_inst, baseline_candidate)[0]
    )

    sparse_inst = make_instance(n=18, degree=8, seed=424242)
    solution_count = enumerate_all(sparse_inst)
    sparse_space = search_space(sparse_inst)
    fraction = solution_count / sparse_space if solution_count is not None else None
    report["G5_sparse"] = {
        "pass": shipping_fraction < 1e-6 and not baseline_solved,
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_n": guess_inst["n"],
        "shipping_degree": guess_inst["degree"],
        "shipping_instance_seed": 314159,
        "density": {
            "method": density_method,
            "exact_solution_count": shipping_exact,
            "hits": shipping_exact if shipping_exact is not None else hits,
            "sample_size": (search_space(guess_inst)
                            if shipping_exact is not None else total),
            "observed_fraction": shipping_fraction,
        },
        "baseline_cost": {
            "attack": "random_restart_walksat_32x200n",
            "success": baseline_solved,
            "result": "verified witness" if baseline_solved else "limits exhausted",
            "wall_seconds": baseline_seconds,
            **baseline_stats,
        },
        "small_exact_calibration": {
            "n": sparse_inst["n"],
            "degree": sparse_inst["degree"],
            "solutions": solution_count,
            "search_space": sparse_space,
            "fraction": fraction,
        },
    }

    # G6: each attack gets the same eight unrelated instances.
    attack_names = [
        "outlier_literal_imbalance",
        "greedy_left_to_right",
        "random_restart_walksat_32x200n",
        "dpll_unit_propagation_5000",
        "spectral_signed_cooccurrence",
    ]
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    for seed in range(6100, 6108):
        attack_inst = make_instance(seed=seed, **ship)
        candidates: dict[str, object | None] = {
            "outlier_literal_imbalance": _literal_imbalance_attack(attack_inst),
            "greedy_left_to_right": _greedy_left_to_right(attack_inst),
            "dpll_unit_propagation_5000": _dpll_attack(attack_inst, 5000),
            "spectral_signed_cooccurrence": _spectral_rounding_attack(attack_inst),
        }
        rr_rng = random.Random(seed ^ 0x5EEDBEEF)
        candidates["random_restart_walksat_32x200n"] = _walksat_random_restart(
            attack_inst, rr_rng, restarts=32, steps_per_variable=200)
        for name, candidate in candidates.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
    report["G6_adversary_panel"] = {
        "pass": all(x["successes"] == 0 for x in attack_results.values()),
        "attacks": attack_results,
        "domain_standard_attack": "dpll_unit_propagation_5000",
    }

    # G7: doubling n doubles exponent bits and keeps fixed density/degree.
    base = make_instance(seed=777, **ship)
    doubled_params = dict(ship)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * base["n"]
                and len(doubled["clauses"]) == 2 * len(base["clauses"])
                and search_space(doubled) == search_space(base) ** 2,
        "base_n": base["n"],
        "doubled_n": doubled["n"],
        "base_clauses": len(base["clauses"]),
        "doubled_clauses": len(doubled["clauses"]),
        "doubled_planted_verify": doubled_why,
    }

    # G8: variable/clause/literal permutations and independent variable/clause
    # complementations, all composed in every trial.
    invariant = 0
    carried_verified = 0
    deterministic = 0
    keys = []
    for seed in range(20):
        original = make_instance(n=24, degree=6, seed=8000 + seed)
        key = canonical_key(original)
        transformed, carried = _transformed_instance(original, random.Random(9000 + seed))
        invariant += int(canonical_key(transformed) == key)
        carried_verified += int(verify(transformed, carried)[0])
        deterministic += int(canonical_key(original) == canonical_key(original))
        keys.append(key)
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried_verified == 20
                and deterministic == 20 and distinct == 20,
        "invariance": {"passed": invariant, "attempts": 20},
        "real_transform_carried_witness": {"passed": carried_verified, "attempts": 20},
        "determinism": {"passed": deterministic, "attempts": 20},
        "unrelated_distinct": {"distinct": distinct, "attempts": 20},
        "transformations": [
            "variable permutation", "clause permutation", "literal permutation",
            "independent variable complementation", "independent clause complementation",
            "all composed",
        ],
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
