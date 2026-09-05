"""Verified problem generator for arXiv:1112.6263.

The paper studies Boolean MQ: common zeroes of quadratic polynomials over F_2.
This module uses inverse generation.  It samples a Boolean zero first and then
samples every quadratic equation uniformly subject to vanishing at that zero.
No solution of an emitted system is ever used to construct its certificate.

The public coefficient format is deliberately the paper's reduced square-free
monomial basis, packed as hexadecimal bit vectors.  Verification expands only
the candidate's active monomials and evaluates every equation exactly in F_2.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from itertools import combinations


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "quadratic polynomials over F_2 in the square-free monomial basis",
        "Boolean common zero",
    ],
    "verification_operations": [
        "exact Boolean monomial evaluation",
        "exact parity in F_2",
        "coefficient-vector comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "A wrong partial assignment is typically exposed by a low-degree Boolean "
        "Macaulay inconsistency relation, whereas a root survives every such filter."
    ),
    "hardness_basis": (
        "Track A: Theorem 2 analyzes square m=n, gamma-strong-semi-regular Boolean "
        "MQ systems and gives O(2^(0.841n)) deterministic and expected "
        "O(2^(0.792n)) Las Vegas bounds; Section 4 conjectures and experimentally "
        "supports this regime for random square systems, while the shipping "
        "size and bounded degree-3 Macaulay baseline are reported by selftest()."
    ),
    "max_answer_tokens": 19,
}

NATIVE: dict = {
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


DIFFICULTY: dict = {
    "demo": {"n": 4, "m": 4, "attack_budget": 0},
    "easy": {"n": 36, "m": 36, "attack_budget": 16_384},
    "medium": {"n": 52, "m": 52, "attack_budget": 32_768},
    "hard": {"n": 68, "m": 68, "attack_budget": 65_536},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "Most wrong partial assignments have a low-degree Boolean Macaulay "
    "inconsistency relation."
)
PLACEBO_HINT: str = (
    "Careful handling of the coefficient indexing helps prevent avoidable "
    "parity errors."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A vector of exactly n Boolean field elements, each encoded by the JSON "
        "integer 0 or 1, with 4 <= n <= 192."
    ),
    "bounds": {
        "min_length": 4,
        "max_length": 192,
        "alphabet": [0, 1],
        "max_atomic_elements": 192,
    },
}


# Filled from the script-owned hardening transcripts after the three oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


NOTES = r"""
Section 1 fixes the native task: Boolean MQ SAT asks for one common zero of
quadratic polynomials over F_2, and explicitly restricts the paper's main study
to m>=n.  Section 3, Theorem 2 is the hardness triage result: under
gamma-strong semi-regularity the paper's own BooleanSolve algorithm remains
exponential (0.841n deterministically and 0.792n in expectation for m=n).
Section 4 is equally important: its random model is independent uniform
coefficients, Conjecture 1 says the required strong semi-regularity tends to
probability one, and the experiments find it throughout the relevant
gamma<=0.55 range except a documented n=23 rank accident.  Section 5 explains
that low-regularity structured systems can be easier, while Section 1 notes
that sparse constraint systems admit separate faster algorithms; the generator
therefore uses dense square equations and avoids n=23.

Generation samples the answer first.  For every equation all nonconstant
coefficients are random and its constant is the one parity bit that makes the
sampled vector a zero.  Conditioning is therefore only on a certificate already
held, never on solving the emitted system.  A bounded Gray-code exhaustion filter
may discard an instance with an accidental early zero, but it
never changes or discovers the planted answer.

The adversary panel targets construction leakage as well as the paper's domain:
coefficient-correlation outliers, greedy bit flips, uniform random restarts,
and a degree-3 Boolean Macaulay/XL linearization all have to fail.  Plants and
decoys are coefficients drawn from the same conditional distribution; the
constant term is not a marker because the planted vector itself is random.

Retained-rejection note: the family fails G9(c).  It has no solver-visible
compact route after the Macaulay insight.  The measured degree-3 probe spends
55,950 exact row XORs without solving the shipping instance, so the earlier
count of n answer writes was not an honest intended-route measurement.
""".strip()


def _basis2(n: int) -> list[tuple[int, ...]]:
    return [()] + [(i,) for i in range(n)] + list(combinations(range(n), 2))


def _basis_upto(n: int, degree: int) -> list[tuple[int, ...]]:
    out: list[tuple[int, ...]] = [()]
    for d in range(1, degree + 1):
        out.extend(combinations(range(n), d))
    return out


def _row_ints(inst: dict) -> list[int]:
    cached = inst.get("_rows")
    if isinstance(cached, list):
        return cached
    return [int(s, 16) for s in inst["equations"]]


def _active_mask(bits: list[int]) -> int:
    """Coefficient-basis mask of monomials evaluating to one at bits."""
    n = len(bits)
    mask = 1  # the constant monomial
    for i, b in enumerate(bits):
        if b:
            mask |= 1 << (1 + i)
    pos = 1 + n
    for i in range(n - 1):
        if bits[i]:
            for j in range(i + 1, n):
                if bits[j]:
                    mask |= 1 << pos
                pos += 1
        else:
            pos += n - i - 1
    return mask


def _bits_from_int(value: int, n: int) -> list[int]:
    return [(value >> i) & 1 for i in range(n)]


def _is_zero_rows(rows: list[int], bits: list[int]) -> bool:
    active = _active_mask(bits)
    return all(((row & active).bit_count() & 1) == 0 for row in rows)


def _first_bad_row(rows: list[int], bits: list[int]) -> int | None:
    active = _active_mask(bits)
    for i, row in enumerate(rows):
        if (row & active).bit_count() & 1:
            return i
    return None


def _pair_position(n: int, i: int, j: int) -> int:
    if i > j:
        i, j = j, i
    if i == j:
        return 1 + i
    before = i * (2 * n - i - 1) // 2
    return 1 + n + before + (j - i - 1)


def _gray_inverse(gray: int) -> int:
    value = 0
    while gray:
        value ^= gray
        gray >>= 1
    return value


def _prefix_solution(rows: list[int], n: int, budget: int) -> list[int] | None:
    """Bounded Gray-code exhaustive attack used only as an easy-case filter."""
    budget = max(0, int(budget))
    bits = [0] * n
    active = 1
    previous_gray = 0
    for step in range(budget):
        if all(((row & active).bit_count() & 1) == 0 for row in rows):
            return list(bits)
        next_gray = (step + 1) ^ ((step + 1) >> 1)
        changed = (previous_gray ^ next_gray).bit_length() - 1
        if changed < 0 or changed >= n:
            break
        bitmask = 1 << (1 + changed)
        if bits[changed]:
            bits[changed] = 0
            active &= ~bitmask
            for j, value in enumerate(bits):
                if value:
                    active &= ~(1 << _pair_position(n, changed, j))
        else:
            bits[changed] = 1
            active |= bitmask
            for j, value in enumerate(bits):
                if j != changed and value:
                    active |= 1 << _pair_position(n, changed, j)
        previous_gray = next_gray
    return None


def make_instance(
    n: int,
    seed: int = 0,
    m: int | None = None,
    attack_budget: int = 0,
    **params,
) -> dict:
    """Inverse-generate a dense square Boolean-MQ SAT instance.

    The answer is sampled first.  Each equation's constant coefficient is then
    selected so that the equation vanishes there.  A bounded rejection filter
    can discard systems with an unrelated early root, but its output is never
    used as the certificate.
    """
    del params
    if not isinstance(n, int) or n < 4 or n > 192:
        raise ValueError("n must be an integer in [4,192]")
    if m is None:
        m = n
    if not isinstance(m, int) or m < n or m > 3 * n:
        raise ValueError("m must be an integer in [n,3n]")
    if not isinstance(attack_budget, int) or attack_budget < 0:
        raise ValueError("attack_budget must be a nonnegative integer")

    rng = random.Random(seed)
    ceiling = 1 << n
    # The filter enumerates the first attack_budget Gray words.  Keeping the
    # planted answer out of that prefix prevents a rejection loop and removes a
    # the uniform prior at non-demo sizes.
    while True:
        planted_value = rng.randrange(ceiling)
        if (
            0 < planted_value.bit_count() < n
            and _gray_inverse(planted_value) >= attack_budget
        ):
            break
    answer = _bits_from_int(planted_value, n)
    active = _active_mask(answer)
    basis_size = 1 + n + n * (n - 1) // 2
    pair_start = 1 + n
    width = (basis_size + 3) // 4

    accepted_rows: list[int] | None = None
    for _nonce in range(256):
        rows: list[int] = []
        seen: set[int] = set()
        while len(rows) < m:
            nonconstant = rng.getrandbits(basis_size - 1) << 1
            # Every input polynomial has degree exactly two, as in the paper.
            if (nonconstant >> pair_start) == 0:
                q = rng.randrange(n * (n - 1) // 2)
                nonconstant |= 1 << (pair_start + q)
            constant = (nonconstant & active).bit_count() & 1
            row = nonconstant | constant
            if row in seen:
                continue
            seen.add(row)
            rows.append(row)
        if attack_budget and _prefix_solution(rows, n, attack_budget) is not None:
            continue
        accepted_rows = rows
        break
    if accepted_rows is None:
        raise RuntimeError("could not generate an instance beyond the attack prefix")

    inst = {
        "n": n,
        "m": m,
        "basis_size": basis_size,
        "hex_width": width,
        "attack_budget": attack_budget,
        "equations": [format(row, f"0{width}x") for row in accepted_rows],
        "_rows": accepted_rows,
        "answer": answer,
    }
    # This assertion is construction auditing, not a search for the answer.
    if not _is_zero_rows(accepted_rows, answer):
        raise AssertionError("inverse-generation invariant failed")
    return inst


def render(inst: dict) -> str:
    """Render a complete standalone Boolean-MQ SAT problem."""
    n, m = inst["n"], inst["m"]
    width = inst["hex_width"]
    lines = [
        "Find a common Boolean zero of a quadratic system over F_2.",
        "",
        "Definitions.",
        f"There are n={n} variables x0,...,x{n-1}; each variable is exactly 0 or 1.",
        "All addition and multiplication are in F_2, so addition is XOR.",
        "Each polynomial is reduced by x_i^2=x_i and uses this ordered basis:",
        "  bit 0: 1 (the constant monomial);",
        f"  bits 1 through {n}: x0,x1,...,x{n-1};",
        (
            f"  bits {n+1} through {inst['basis_size']-1}: x_i*x_j for i<j, "
            "ordered first by i=0,1,... and then by j=i+1,i+2,... ."
        ),
        "A hexadecimal row below is a nonnegative integer coefficient bit-vector:",
        "bit p is 1 exactly when basis monomial p occurs in that polynomial.",
        "Leading zeroes only pad every row to the displayed common width.",
        "A row evaluates to the XOR of its selected monomial values.",
        "",
        f"The {m} equations f_i(x)=0 are (each row has {width} hex digits):",
    ]
    lines.extend(f"  f_{i}: {row}" for i, row in enumerate(inst["equations"]))
    lines.extend(
        [
            "",
            "Return any common zero; more than one may exist and every valid one is accepted.",
            f"The answer must contain exactly {n} bits in variable order x0,...,x{n-1}.",
            "The order is fixed, indices are 0-based, and no entries may be omitted.",
            "",
            "Give your final answer inside <answer></answer> tags as one JSON array of 0/1 integers.",
            "Format example (not claimed to solve this instance): <answer>"
            + json.dumps([0] * n)
            + "</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse a tagged JSON bit vector, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    bodies = tagged[-1:] if tagged else re.findall(r"\[[\s,01]+\]", text, re.S)[-1:]
    if not bodies:
        return None
    body = bodies[0].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        # Also accept the explicitly described comma-separated interior.
        raw = body.strip().strip("[]").strip()
        if not raw:
            value = []
        elif re.fullmatch(r"[01](?:\s*(?:,|\s)\s*[01])*", raw):
            value = [int(x) for x in re.findall(r"[01]", raw)]
        else:
            return None
    if not isinstance(value, list) or len(value) > 256:
        return None
    if not all(type(x) is int for x in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any proposed common zero exactly; never inspect inst['answer']."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list of Boolean bits"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"answer must contain exactly {n} bits (got {len(answer)})"
    for i, value in enumerate(answer):
        if type(value) is not int or value not in (0, 1):
            return False, f"entry {i} is not a Boolean bit"
    bad = _first_bad_row(_row_ints(inst), answer)
    if bad is not None:
        return False, f"equation {bad} evaluates to 1 in F_2"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the exact, structure-aware Boolean-vector language."""
    return _bits_from_int(rng.getrandbits(inst["n"]), inst["n"])


def search_space(inst: dict) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Count all common zeroes exactly only when the full space is safely small."""
    n = inst["n"]
    if n > 18:
        return None
    rows = _row_ints(inst)
    return sum(_is_zero_rows(rows, _bits_from_int(v, n)) for v in range(1 << n))


def _canonical_invariant(inst: dict) -> dict:
    """Cheap invariant under equation order and variable-name permutations."""
    n = inst["n"]
    rows = _row_ints(inst)
    basis = _basis2(n)
    equation_signatures = []
    for row in rows:
        equation_signatures.append(
            (
                row & 1,
                sum((row >> (1 + i)) & 1 for i in range(n)),
                sum((row >> p) & 1 for p in range(1 + n, len(basis))),
            )
        )
    linear_counts = [sum((row >> (1 + v)) & 1 for row in rows) for v in range(n)]
    quadratic_counts = [0] * n
    pair_frequencies = []
    for p, mon in enumerate(basis[1 + n :], start=1 + n):
        frequency = sum((row >> p) & 1 for row in rows)
        pair_frequencies.append(frequency)
        quadratic_counts[mon[0]] += frequency
        quadratic_counts[mon[1]] += frequency
    variable_signatures = list(zip(linear_counts, quadratic_counts))
    return {
        "n": n,
        "m": inst["m"],
        "equations": sorted(equation_signatures),
        "variables": sorted(variable_signatures),
        "pairs": sorted(pair_frequencies),
    }


def canonical_key(inst: dict) -> str:
    payload = json.dumps(_canonical_invariant(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """First harden a fixed-length answer, then enlarge it up to the output cap."""
    p = {k: int(v) for k, v in params.items() if k != "_preset"}
    n = p.get("n", 36)
    p.setdefault("m", n)
    budget = p.get("attack_budget", 0)
    if budget < 1_048_576:
        p["attack_budget"] = max(16_384, budget * 2)
        return p
    if n >= 192:
        return "cap_bound"
    p["n"] = min(192, n + 16)
    p["m"] = p["n"]
    p["attack_budget"] = 65_536
    return p


# ---------------------------------------------------------------------------
# Adversarial probes used by selftest.  None receives inst['answer'].


def _outlier_correlation_candidate(inst: dict) -> list[int]:
    rows = _row_ints(inst)
    n = inst["n"]
    guess = []
    for i in range(n):
        agreements = sum(((row & 1) == ((row >> (1 + i)) & 1)) for row in rows)
        guess.append(1 if agreements > len(rows) // 2 else 0)
    return guess


def _unsatisfied_count(rows: list[int], bits: list[int]) -> int:
    active = _active_mask(bits)
    return sum((row & active).bit_count() & 1 for row in rows)


def _greedy_bitflip_candidate(inst: dict) -> list[int]:
    rows = _row_ints(inst)
    bits = _outlier_correlation_candidate(inst)
    score = _unsatisfied_count(rows, bits)
    for _ in range(4 * inst["n"]):
        best_score = score
        best_i = None
        for i in range(inst["n"]):
            bits[i] ^= 1
            s = _unsatisfied_count(rows, bits)
            bits[i] ^= 1
            if s < best_score:
                best_score, best_i = s, i
        if best_i is None:
            break
        bits[best_i] ^= 1
        score = best_score
        if score == 0:
            break
    return bits


def _random_restart_attack(inst: dict, seed: int, trials: int = 512) -> list[int] | None:
    rng = random.Random(seed)
    for _ in range(trials):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _macaulay_degree3_attack(inst: dict) -> tuple[list[int], dict]:
    """Degree-3 Boolean Macaulay/XL, with free lifted monomials set to zero.

    This is a bounded version of the paper's domain-standard linear-algebra
    route.  It constructs f_i and x_j*f_i rows after square-free reduction,
    solves the lifted linear system, and checks the induced singleton values.
    """
    n = inst["n"]
    basis2 = _basis2(n)
    basis3 = _basis_upto(n, 3)
    col = {mon: i for i, mon in enumerate(basis3)}
    lifted_rows: list[tuple[int, int]] = []
    for packed in _row_ints(inst):
        support = [basis2[p] for p in range(len(basis2)) if (packed >> p) & 1]
        for multiplier in [()] + [(j,) for j in range(n)]:
            coeff = 0
            for mon in support:
                product = tuple(sorted(set(mon).union(multiplier)))
                coeff ^= 1 << col[product]
            rhs = coeff & 1
            lifted_rows.append((coeff >> 1, rhs))

    pivots: dict[int, tuple[int, int]] = {}
    xor_operations = 0
    inconsistent = False
    for variables, rhs in lifted_rows:
        while variables:
            p = variables.bit_length() - 1
            old = pivots.get(p)
            if old is None:
                pivots[p] = (variables, rhs)
                break
            variables ^= old[0]
            rhs ^= old[1]
            xor_operations += 1
        if not variables and rhs:
            inconsistent = True
            break

    values: dict[int, int] = {}
    if not inconsistent:
        for p in sorted(pivots):
            variables, rhs = pivots[p]
            lower = variables & ((1 << p) - 1)
            parity = 0
            while lower:
                bit = (lower & -lower).bit_length() - 1
                parity ^= values.get(bit, 0)
                lower &= lower - 1
            values[p] = rhs ^ parity
    candidate = []
    for i in range(n):
        singleton_col = col[(i,)] - 1
        candidate.append(values.get(singleton_col, 0))
    stats = {
        "macaulay_rows": len(lifted_rows),
        "macaulay_columns": len(basis3),
        "rank": len(pivots),
        "xor_operations": xor_operations,
        "inconsistent": inconsistent,
    }
    return candidate, stats


def _reorder_equations(inst: dict, order: list[int]) -> dict:
    out = dict(inst)
    out["equations"] = [inst["equations"][i] for i in order]
    out["_rows"] = [_row_ints(inst)[i] for i in order]
    out["answer"] = list(inst["answer"])
    return out


def _permute_variables(inst: dict, old_to_new: list[int]) -> dict:
    n = inst["n"]
    if sorted(old_to_new) != list(range(n)):
        raise ValueError("not a variable permutation")
    old_basis = _basis2(n)
    new_pos = {mon: p for p, mon in enumerate(old_basis)}
    new_rows = []
    for row in _row_ints(inst):
        transformed = 0
        for p, mon in enumerate(old_basis):
            if (row >> p) & 1:
                mapped = tuple(sorted(old_to_new[v] for v in mon))
                transformed |= 1 << new_pos[mapped]
        new_rows.append(transformed)
    answer = [0] * n
    for old, new in enumerate(old_to_new):
        answer[new] = inst["answer"][old]
    out = dict(inst)
    out["equations"] = [format(row, f"0{inst['hex_width']}x") for row in new_rows]
    out["_rows"] = new_rows
    out["answer"] = answer
    return out


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    chars = len(blob)
    tokens = math.ceil(chars / 4)
    return chars, tokens, atoms(answer)


def selftest() -> dict:
    """Run every local correctness, density, attack, scaling, and G9 gate."""
    report: dict = {}

    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/seed={seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    corrupt_inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = corrupt_inst["answer"]
    corruptions: dict[str, list[int]] = {
        "drop_one": planted[:-1],
        "duplicate": planted + [planted[-1]],
        "empty": [],
        "out_of_range": list(planted),
    }
    corruptions["out_of_range"][0] = 2
    swapped = None
    for i in range(len(planted)):
        for j in range(i + 1, len(planted)):
            if planted[i] != planted[j]:
                candidate = list(planted)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                if not verify(corrupt_inst, candidate)[0]:
                    swapped = candidate
                    break
        if swapped is not None:
            break
    corruptions["swap_two"] = swapped if swapped is not None else list(reversed(planted))
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(corrupt_inst, candidate)
        if not ok:
            rejected[name] = why
    report["G2_rejects_corruption"] = {
        "pass": len(rejected) == len(corruptions) and len(set(rejected.values())) == len(rejected),
        "rejections": rejected,
        "distinct_reasons": len(set(rejected.values())),
    }

    response = (
        "I evaluated the parities.\n```text\n<answer>"
        + json.dumps(planted)
        + "</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no certificate here") is None,
        "parsed_matches": parsed == planted,
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=20240229, **shipping_params)
    rng = random.Random(0x11126263)
    sample_total = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(sample_total):
        hits += int(verify(ship, random_candidate(ship, rng))[0])
    sample_seconds = time.perf_counter() - t0
    probability = hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": sample_total,
        "empirical_probability": probability,
        "candidate_space": search_space(ship),
        "prior": "uniform over all 2^n Boolean vectors, including every stated shape/range rule",
        "sampling_wall_seconds": sample_seconds,
    }

    t0 = time.perf_counter()
    baseline_candidate, baseline_stats = _macaulay_degree3_attack(ship)
    baseline_seconds = time.perf_counter() - t0
    baseline_success = int(verify(ship, baseline_candidate)[0])
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and baseline_success == 0,
        "shipping_observed_valid_fraction": probability,
        "shipping_density_sample_count": sample_total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(ship),
        "baseline_wall_seconds": baseline_seconds,
        "baseline_xor_operations": baseline_stats["xor_operations"],
        "baseline_rows": baseline_stats["macaulay_rows"],
        "baseline_columns": baseline_stats["macaulay_columns"],
        "baseline_successes": baseline_success,
        "demo_exact_solution_count": enumerate_all(demo),
        "enumerate_all_shipping": enumerate_all(ship),
    }

    attack_names = (
        "outlier_constant_linear_correlation",
        "greedy_steepest_bitflip",
        "random_restart_512",
        "boolean_macaulay_xl_degree3",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_details = []
    attack_attempts = 8
    panel_t0 = time.perf_counter()
    for seed in range(800, 800 + attack_attempts):
        inst = make_instance(seed=seed, **shipping_params)
        candidates: dict[str, list[int] | None] = {
            attack_names[0]: _outlier_correlation_candidate(inst),
            attack_names[1]: _greedy_bitflip_candidate(inst),
            attack_names[2]: _random_restart_attack(inst, seed ^ 0xBAD5EED),
        }
        mac_candidate, mac_stats = _macaulay_degree3_attack(inst)
        candidates[attack_names[3]] = mac_candidate
        attack_details.append(mac_stats)
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_successes[name] += 1
    panel_seconds = time.perf_counter() - panel_t0
    attacks = {
        name: {"successes": attack_successes[name], "attempts": attack_attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "panel_wall_seconds": panel_seconds,
        "domain_attack_total_xor_operations": sum(d["xor_operations"] for d in attack_details),
        "domain_attack": (
            "degree-3 square-free Boolean Macaulay/XL linearization, the bounded "
            "linear-algebra core of the paper's BooleanSolve method"
        ),
    }

    doubled = dict(shipping_params)
    doubled["n"] = 2 * shipping_params["n"]
    doubled["m"] = 2 * shipping_params["m"]
    doubled_inst = make_instance(seed=271828, **doubled)
    doubled_ok, doubled_why = verify(doubled_inst, doubled_inst["answer"])
    fixed_escalation = escalate(dict(shipping_params))
    report["G7_scales"] = {
        "pass": doubled_ok and isinstance(fixed_escalation, dict)
        and fixed_escalation["n"] == shipping_params["n"]
        and fixed_escalation["attack_budget"] > shipping_params["attack_budget"],
        "base_n": shipping_params["n"],
        "doubled_n": doubled["n"],
        "doubled_verify": doubled_why,
        "candidate_space_bit_growth": doubled["n"] - shipping_params["n"],
        "fixed_answer_axis": "attack_budget",
        "fixed_axis_before": shipping_params["attack_budget"],
        "fixed_axis_after": fixed_escalation.get("attack_budget") if isinstance(fixed_escalation, dict) else None,
    }

    invariance_checks = 0
    carried_checks = 0
    invariant_failures = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(inst)
        rng8 = random.Random(seed ^ 0xC011A)
        eq_order = list(range(inst["m"]))
        rng8.shuffle(eq_order)
        var_perm = list(range(inst["n"]))
        rng8.shuffle(var_perm)
        transforms = [
            _reorder_equations(inst, eq_order),
            _permute_variables(inst, var_perm),
        ]
        composed = _reorder_equations(transforms[1], eq_order)
        transforms.append(composed)
        for transformed in transforms:
            invariance_checks += 1
            if canonical_key(transformed) != key:
                invariant_failures.append(f"seed {seed}: key changed")
            ok, why = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                invariant_failures.append(f"seed {seed}: carried witness {why}")
    unrelated = [
        canonical_key(make_instance(seed=20_000 + seed, **shipping_params))
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated)) == len(unrelated),
        "invariance_checks": invariance_checks,
        "invariance_attempts": 60,
        "transformed_witness_checks": carried_checks,
        "unrelated_distinct": len(set(unrelated)),
        "unrelated_attempts": len(unrelated),
        "transformations": (
            "equation reordering, variable-name permutation, and their composition"
        ),
        "key_definition": (
            "SHA-256 of sorted equation weight, variable-incidence, and pair-frequency invariants"
        ),
        "failures": invariant_failures,
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    # There is no compact route for the conditioned-random family.  The
    # degree-3 Macaulay probe is the cheapest measured algebraic route in this
    # module, and it has already spent this many exact row XORs without finding
    # a root.  Counting only the n writes needed after somebody hands us the
    # secret would violate G9(c): discovery, not transcription, is the route
    # whose cost the gate asks us to report.
    intended_operations = baseline_stats["xor_operations"]
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "intended_route_status": (
            "lower bound from the measured degree-3 Macaulay probe; it did not solve"
        ),
        "within_caps": within_caps,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
