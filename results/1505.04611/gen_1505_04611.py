"""Verified Track-B generator derived from arXiv:1505.04611.

The generated task stays in the paper's native cyclotomic/exponent-set objects.
It asks for an indexed table of exact translate-intersection sums.  Instances
are inverse-generated: the quadratic characters (and hence the two possible
intersection sums) are sampled first, after which compatible shifts are built.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import random
import re
import sys
import time
from functools import lru_cache


# Keep the repository helpers importable when this file is invoked from its own
# result directory.  This family needs only finite-field integer arithmetic, so
# it remains standard-library-only if gvlib is absent.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import rationals  # noqa: F401
except ImportError:  # pragma: no cover - documented graceful fallback
    rationals = None


TRACK = "B"


# Every pair is (prime modulus, certified primitive root).  The factorisations
# of q-1 were checked independently; only the first three non-demo entries are
# named presets, while the rest give escalate() fixed-answer-length headroom.
_PRIME_ROOTS = {
    41: 6,
    65537: 3,
    114689: 3,
    147457: 10,
    786433: 10,
    5767169: 3,
    7340033: 3,
    998244353: 3,
    2013265921: 31,
}
_MODULUS_LADDER = tuple(_PRIME_ROOTS)


PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "prime field with a certified primitive root",
        "implicitly defined quadratic cyclotomic exponent sets",
        "translate-intersection queries in a cyclic exponent group",
    ],
    "verification_operations": [
        "exact modular exponentiation",
        "Euler quadratic-character test",
        "exact integer table comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The cyclotomic exponent sets partition every exponent except the one "
        "representing -1, so a sum of two large intersections is controlled by "
        "one translated omission."
    ),
    "hardness_basis": (
        "Track B: literal construction and intersection of the Section 3 exponent "
        "sets takes O(q+nq) exact operations and measured 9,805,696 counted "
        "operations (roughly 0.2--0.5 s across local audit runs) at the current hard "
        "shipping preset, while the "
        "compact Jacobi-symbol route used 260 counted exact operations."
    ),
    "max_answer_tokens": 86,
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


DIFFICULTY = {
    "demo": {
        "n": 4,
        "modulus": 41,
        "argument_bound": 40,
        "max_jacobi_steps": 7,
    },
    "easy": {
        "n": 28,
        "modulus": 65537,
        "argument_bound": 10000,
        "max_jacobi_steps": 7,
    },
    "medium": {
        "n": 30,
        "modulus": 114689,
        "argument_bound": 10000,
        "max_jacobi_steps": 7,
    },
    "hard": {
        "n": 32,
        "modulus": 147457,
        "argument_bound": 10000,
        "max_jacobi_steps": 7,
    },
}

SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "Focus on the unique exponent representing -1, which is omitted from the "
    "partition C0 union C1."
)
PLACEBO_HINT = (
    "Focus on keeping the modular representatives and row indices consistent "
    "throughout every step of the calculation."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "An n-by-2 indexed integer table [[i,s_i],...] in canonical row order; "
        "each s_i is one of the two displayed adjacent levels and exactly n/2 "
        "rows use the lower level."
    ),
    "bounds": {
        "columns": 2,
        "index_min": 0,
        "count_values": 2,
        "lower_rows": "n/2",
        "max_rows": 120,
        "integer_only": True,
    },
}


NOTES = """\
Definition source: Section 2 defines difference levels, developments, and exact
incidence counts.  Section 3 (especially Lemma 3.1 and Theorem 3.2) fixes the
quadratic cyclotomic classes and performs the translate-intersection case split.
The source has a C_i indexing typo (it says i=1,2 and subsequently uses C_0,C_1),
so this module states the literal, standard partition explicitly and validates it
against direct enumeration.

What makes the problem easy with tools is also in Theorem 3.2's proof: cyclotomic
intersection counts reduce to quadratic characters.  Therefore this is Track B.
The reference algorithm deliberately follows the displayed set definitions in
O(q+nq); the compact route observes that C_0 union C_1 omits only the exponent of
-1 and evaluates small Jacobi symbols.  The paper proves constructions, not a
search-hardness or distributional-hardness theorem, so Track A is not claimed.

Inverse generation samples an equal number of residue and nonresidue character
answers first, then chooses same-shaped prime arguments from the corresponding
classes and computes their exponent coordinates.  Magnitude, shift, parity, and
random-restart attacks are measured.  Small Jacobi-cost arguments are used for
both answer classes, preventing arithmetic length from becoming the label while
keeping the intended no-tool route under the operation cap.
"""


def _is_prime_small(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    for divisor in range(3, limit + 1, 2):
        if value % divisor == 0:
            return False
    return True


def _jacobi_with_cost(a: int, n: int) -> tuple[int, int]:
    """Return the Jacobi symbol and a transparent reduction/halving count."""
    if n <= 0 or n % 2 == 0:
        raise ValueError("Jacobi denominator must be positive and odd")
    a %= n
    cost = 1
    sign = 1
    while a:
        while a % 2 == 0:
            a //= 2
            cost += 1
            if n % 8 in (3, 5):
                sign = -sign
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            sign = -sign
        a %= n
        cost += 1
    return (sign if n == 1 else 0), cost


@lru_cache(maxsize=None)
def _eligible_arguments(
    modulus: int, argument_bound: int, max_jacobi_steps: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    residues = []
    nonresidues = []
    for value in range(3, min(argument_bound, modulus), 2):
        if not _is_prime_small(value):
            continue
        character, cost = _jacobi_with_cost(value, modulus)
        if cost > max_jacobi_steps:
            continue
        if character == 1:
            residues.append(value)
        elif character == -1:
            nonresidues.append(value)
    return tuple(residues), tuple(nonresidues)


@lru_cache(maxsize=None)
def _bsgs_setup(modulus: int, alpha: int) -> tuple[int, dict[int, int], int]:
    period = modulus - 1
    width = math.isqrt(period) + 1
    baby = {}
    value = 1
    for exponent in range(width):
        baby.setdefault(value, exponent)
        value = value * alpha % modulus
    giant_factor = pow(pow(alpha, width, modulus), -1, modulus)
    return width, baby, giant_factor


def _discrete_log(modulus: int, alpha: int, target: int) -> int:
    """Baby-step/giant-step; target is guaranteed to be nonzero."""
    width, baby, giant_factor = _bsgs_setup(modulus, alpha)
    gamma = target
    for giant in range(width + 1):
        small = baby.get(gamma)
        if small is not None:
            exponent = (giant * width + small) % (modulus - 1)
            if pow(alpha, exponent, modulus) == target:
                return exponent
        gamma = gamma * giant_factor % modulus
    raise ValueError("target is not generated by alpha")


def _levels(modulus: int) -> tuple[int, int]:
    # |C0|=(q-3)/2.  The union C0 U C1 misses one exponent, so the
    # requested sum is either |C0|-1 or |C0|.
    return (modulus - 5) // 2, (modulus - 3) // 2


def make_instance(
    n: int,
    seed: int = 0,
    modulus: int = 65537,
    argument_bound: int = 10000,
    max_jacobi_steps: int = 7,
) -> dict:
    """Inverse-generate a balanced table of cyclotomic intersection sums."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 2 or n % 2:
        raise ValueError("n must be an even integer at least 2")
    if modulus not in _PRIME_ROOTS:
        raise ValueError("unsupported certified prime modulus")
    alpha = _PRIME_ROOTS[modulus]
    residue_pool, nonresidue_pool = _eligible_arguments(
        modulus, argument_bound, max_jacobi_steps
    )
    half = n // 2
    if len(residue_pool) < half or len(nonresidue_pool) < half:
        raise ValueError("argument bound does not provide enough balanced queries")

    rng = random.Random(seed)
    # Sample the answer classes first: +1 gives the lower count, -1 the upper.
    chosen = [(value, 1) for value in rng.sample(residue_pool, half)]
    chosen += [(value, -1) for value in rng.sample(nonresidue_pool, half)]
    rng.shuffle(chosen)

    low, high = _levels(modulus)
    queries = []
    answer = []
    for index, (argument, character) in enumerate(chosen):
        x_value = (1 - argument) % modulus
        shift = _discrete_log(modulus, alpha, x_value)
        queries.append({"w": shift, "x": x_value})
        answer.append([index, low if character == 1 else high])

    return {
        "family": "cyclotomic_partition_intersection_sum",
        "q": modulus,
        "alpha": alpha,
        "n": n,
        "argument_bound": argument_bound,
        "max_jacobi_steps": max_jacobi_steps,
        "levels": [low, high],
        "balance": half,
        "queries": queries,
        "answer": answer,
    }


def render(inst: dict) -> str:
    q = inst["q"]
    alpha = inst["alpha"]
    n = inst["n"]
    low, high = inst["levels"]
    rows = "\n".join(
        f"{index}: w={query['w']}, x={query['x']}"
        for index, query in enumerate(inst["queries"])
    )
    statement = f"""Cyclotomic translate-intersection table

Work in the prime field F_q, represented by the integers modulo q, with
q={q}.  The number alpha={alpha} is a primitive root modulo q.  Exponents live
in Z_(q-1), so all exponent additions below are modulo {q - 1}.

A nonzero field element is a quadratic residue if it is a square modulo q; a
nonzero element that is not a square is a quadratic nonresidue.  Define

  C0 = {{z in Z_(q-1) : alpha^z + 1 modulo q is a nonzero quadratic residue}},
  C1 = {{z in Z_(q-1) : alpha^z + 1 modulo q is a quadratic nonresidue}}.

Zero belongs to neither field class.  For a subset C of Z_(q-1), define
C+w = {{(z+w) modulo (q-1) : z in C}}.  For every query row i below, x is
included as exact redundant data and satisfies x = alpha^w modulo q.  Also,
(1-x) modulo q is an odd prime below {inst['argument_bound']}.

For each row compute the exact integer

  s_i = |C0 intersect (C0+w)| + |C0 intersect (C1+w)|.

For this promised instance every s_i is either {low} or {high}, and exactly
{inst['balance']} of the {n} rows have each value.  Rows are 0-indexed, order
matters, and no row may be omitted or repeated.

Queries:
{rows}

Give your final answer inside <answer></answer> tags as a JSON n-by-2 integer
table [[row_index,s_i],...], in increasing row-index order.
Example format: <answer>[[0,{low}],[1,{high}],[2,{low}],[3,{high}]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _decode_json_fragment(fragment: str):
    candidate = fragment.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL | re.I)
    if fence:
        candidate = fence.group(1).strip()
    try:
        return json.loads(candidate)
    except (TypeError, ValueError):
        return None


def parse_answer(text: str):
    """Parse tagged JSON, fenced JSON, or a JSON array surrounded by prose."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer>(.*?)</answer>", text, re.DOTALL | re.I)
    if tagged:
        return _decode_json_fragment(tagged[-1])

    fenced = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.I)
    for fragment in reversed(fenced):
        parsed = _decode_json_fragment(fragment)
        if parsed is not None:
            return parsed

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            parsed, _ = decoder.raw_decode(text[match.start() :])
        except ValueError:
            continue
        if isinstance(parsed, list):
            return parsed
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any table in the declared language; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be an indexed list"
    if not answer:
        return False, "answer table is empty"
    n = inst["n"]
    if len(answer) != n:
        return False, f"wrong number of rows: expected {n}"

    seen = set()
    for row in answer:
        if not isinstance(row, list) or len(row) != 2:
            return False, "each row must be a two-integer list"
        index, count = row
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or not isinstance(count, int)
            or isinstance(count, bool)
        ):
            return False, "row index and count must both be integers"
        if index < 0 or index >= n:
            return False, "query index is out of range"
        if index in seen:
            return False, "duplicate query index"
        seen.add(index)

    if [row[0] for row in answer] != list(range(n)):
        return False, "rows must be in canonical increasing query order"

    low, high = inst["levels"]
    for index, count in answer:
        if count not in (low, high):
            return False, "count is outside the two allowed intersection levels"

    if sum(count == low for _, count in answer) != inst["balance"]:
        return False, "wrong balance between the two promised levels"

    q = inst["q"]
    alpha = inst["alpha"]
    for index, count in answer:
        query = inst["queries"][index]
        w = query["w"]
        x_value = query["x"]
        if not (0 < w < q - 1 and 0 < x_value < q):
            return False, "instance query is outside its modular range"
        if pow(alpha, w, q) != x_value:
            return False, "instance query has inconsistent redundant field data"
        argument = (1 - x_value) % q
        character = pow(argument, (q - 1) // 2, q)
        expected = low if character == 1 else high
        if count != expected:
            return False, f"incorrect intersection sum at row {index}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    """Uniformly sample the promised balanced two-level table."""
    n = inst["n"]
    low, high = inst["levels"]
    low_rows = set(rng.sample(range(n), inst["balance"]))
    return [[index, low if index in low_rows else high] for index in range(n)]


def search_space(inst: dict) -> int:
    return math.comb(inst["n"], inst["balance"])


def enumerate_all(inst: dict):
    space = search_space(inst)
    if space > 50000:
        return None
    n = inst["n"]
    low, high = inst["levels"]
    valid = 0
    for chosen in itertools.combinations(range(n), inst["balance"]):
        lower = set(chosen)
        candidate = [[i, low if i in lower else high] for i in range(n)]
        valid += int(verify(inst, candidate)[0])
    return valid


def canonical_key(inst: dict) -> str:
    """Invariant under query order and primitive-root exponent coordinates."""
    # Under alpha -> alpha^u (gcd(u,q-1)=1), w -> u^-1 w while x=alpha^w
    # stays fixed.  Only q and the multiset of field elements x affect the task.
    data = [
        "cyclotomic_partition_intersection_sum",
        inst["q"],
        sorted(query["x"] for query in inst["queries"]),
    ]
    return json.dumps(data, separators=(",", ":"))


def escalate(params: dict):
    """Raise the modulus first, preserving answer length; lengthen only later."""
    current = params.get("modulus", 65537)
    if current in _MODULUS_LADDER:
        position = _MODULUS_LADDER.index(current)
        if position + 1 < len(_MODULUS_LADDER):
            harder = dict(params)
            harder["modulus"] = _MODULUS_LADDER[position + 1]
            return harder

    # The fixed-length modulus axis is exhausted only beyond two billion.
    # There is still answer-length headroom, so grow it cautiously after that.
    new_n = int(params.get("n", 28)) + 2
    if 2 * new_n > 240:
        return "cap_bound"
    harder = dict(params)
    harder["n"] = new_n
    bound = int(harder.get("argument_bound", 10000))
    max_steps = int(harder.get("max_jacobi_steps", 7))
    q = int(harder.get("modulus", current))
    while True:
        residues, nonresidues = _eligible_arguments(q, bound, max_steps)
        if min(len(residues), len(nonresidues)) >= new_n // 2:
            harder["argument_bound"] = bound
            return harder
        if bound >= 200000:
            return "cap_bound"
        bound *= 2


def _candidate_from_lower_rows(inst: dict, lower_rows) -> list[list[int]]:
    low, high = inst["levels"]
    chosen = set(lower_rows)
    return [[i, low if i in chosen else high] for i in range(inst["n"])]


def _direct_reference_algorithm(inst: dict):
    """Literal construction of C0,C1 and both intersections, with cost data."""
    q = inst["q"]
    alpha = inst["alpha"]
    period = q - 1
    t0 = time.perf_counter()

    squares = {value * value % q for value in range(1, (q + 1) // 2)}
    c0 = []
    c1 = set()
    power = 1
    for exponent in range(period):
        shifted = (power + 1) % q
        if shifted in squares:
            c0.append(exponent)
        elif shifted != 0:
            c1.add(exponent)
        power = power * alpha % q
    c0_set = set(c0)

    table = []
    for index, query in enumerate(inst["queries"]):
        w = query["w"]
        first = sum(1 for z in c0 if (z - w) % period in c0_set)
        second = sum(1 for z in c0 if (z - w) % period in c1)
        table.append([index, first + second])

    elapsed = time.perf_counter() - t0
    # Count one modular reduction and one membership test per intersection
    # expression, plus the explicit residue/power/classification operations.
    operations = (
        (q - 1) // 2
        + (q - 1)
        + (q - 1)
        + 4 * inst["n"] * len(c0)
    )
    detail = {
        "quadratic_residue_squares": (q - 1) // 2,
        "power_walk_multiplications": q - 1,
        "classification_lookups": q - 1,
        "translate_reductions_and_lookups": 4 * inst["n"] * len(c0),
        "operations": operations,
        "wall_clock_sec": elapsed,
    }
    return table, detail


def _attack_candidates(inst: dict, rng: random.Random):
    half = inst["balance"]
    indexed = list(enumerate(inst["queries"]))
    smallest_argument = sorted(
        indexed, key=lambda item: ((1 - item[1]["x"]) % inst["q"], item[0])
    )[:half]
    smallest_shift = sorted(indexed, key=lambda item: (item[1]["w"], item[0]))[:half]
    parity_first = sorted(
        indexed,
        key=lambda item: (item[1]["w"] % 2, item[1]["w"], item[0]),
    )[:half]
    attacks = {
        "outlier_smallest_character_argument": _candidate_from_lower_rows(
            inst, [item[0] for item in smallest_argument]
        ),
        "greedy_smallest_shift": _candidate_from_lower_rows(
            inst, [item[0] for item in smallest_shift]
        ),
        "parity_only_ansatz": _candidate_from_lower_rows(
            inst, [item[0] for item in parity_first]
        ),
    }
    # The restart attack succeeds if any of its structure-aware balanced draws
    # succeeds.  Returning the final failed candidate keeps result handling uniform.
    last = None
    solved = False
    for _ in range(256):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            solved = True
            break
    attacks["random_restart_256"] = (last, solved)
    return attacks


# Filled with script-owned transcript results after the oracle runs.  Keeping the
# data as constants preserves the module's no-file-IO rule.
ORACLE_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    report = {}

    # G1: every named rung, several independent seeds, plus JSON nativeness.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=20260518, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: generic corruptions are routed to distinct, informative failures.
    planted = shipping["answer"]
    corruptions = {}
    corruptions["drop"] = [row[:] for row in planted[:-1]]
    swapped = [row[:] for row in planted]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap"] = swapped
    duplicated = [row[:] for row in planted]
    duplicated[1] = duplicated[0][:]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    out_of_range = [row[:] for row in planted]
    out_of_range[0][1] = shipping["levels"][1] + 1
    corruptions["out_of_range"] = out_of_range
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose + markdown fence + tags, and malformed text.
    encoded = json.dumps(planted, separators=(",", ":"))
    response = (
        "I used the missing exponent to classify each row.\n"
        "<answer>\n```json\n" + encoded + "\n```\n</answer>\n"
        "The table is indexed from zero."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no answer here") is None,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("no answer here") is None,
    }

    # G4/G5 density: sample the actual balanced certificate language at shipping.
    sample_total = 200000
    sample_hits = 0
    guess_rng = random.Random(150504611)
    density_t0 = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(shipping, guess_rng)
        sample_hits += int(verify(shipping, candidate)[0])
    density_elapsed = time.perf_counter() - density_t0
    density = sample_hits / sample_total
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6 and sample_total >= 200000,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": density,
        "declared_space": search_space(shipping),
        "exact_probability_from_unique_table": exact_density,
        "structure_aware": True,
        "wall_clock_sec": density_elapsed,
    }

    # Strongest failing attack cost (random restarts), plus the standard direct
    # algorithm cost that constitutes the Track-B mechanical baseline.
    attack_t0 = time.perf_counter()
    attack_bundle = _attack_candidates(shipping, random.Random(551122))
    restart_candidate, restart_shortcut = attack_bundle["random_restart_256"]
    restart_success = restart_shortcut or verify(shipping, restart_candidate)[0]
    attack_elapsed = time.perf_counter() - attack_t0
    reference_table, reference_detail = _direct_reference_algorithm(shipping)
    reference_ok, reference_reason = verify(shipping, reference_table)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_exact_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6 and reference_ok and demo_exact_count == 1,
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_estimate": density,
        "exact_valid_answer_count": 1,
        "certificate_space": search_space(shipping),
        "demo_exact_valid_answer_count": demo_exact_count,
        "demo_certificate_space": search_space(demo),
        "strongest_failing_attack_wall_sec": attack_elapsed,
        "strongest_failing_attack_iterations": 256,
        "strongest_failing_attack_successes": int(restart_success),
        "reference_algorithm_wall_sec": reference_detail["wall_clock_sec"],
        "reference_algorithm_operations": reference_detail["operations"],
        "reference_algorithm_verify_reason": reference_reason,
    }

    # G6: four tool-free/cheap attacks must fail on every tested seed.  The
    # domain-standard exact method is reported separately because this is Track B.
    attack_names = (
        "outlier_smallest_character_argument",
        "greedy_smallest_shift",
        "random_restart_256",
        "parity_only_ansatz",
    )
    panel = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_operations = []
    for offset in range(8):
        inst = make_instance(
            seed=8800 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        bundle = _attack_candidates(inst, random.Random(9900 + offset))
        for name in attack_names:
            if name == "random_restart_256":
                candidate, shortcut = bundle[name]
                success = shortcut or verify(inst, candidate)[0]
            else:
                success = verify(inst, bundle[name])[0]
            panel[name]["successes"] += int(success)
        table, detail = _direct_reference_algorithm(inst)
        reference_successes += int(verify(inst, table)[0])
        reference_times.append(detail["wall_clock_sec"])
        reference_operations.append(detail["operations"])
    all_failed = all(item["successes"] == 0 for item in panel.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": panel,
        "reference_algorithm": {
            "name": "literal C0/C1 construction and translate intersections",
            "complexity": "O(q+nq) exact time and O(q) memory",
            "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "operations": max(reference_operations),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    # G7: named spaces grow, and doubling the shipping n still constructs/verifies.
    spaces = {
        name: search_space(make_instance(seed=17, **params))
        for name, params in DIFFICULTY.items()
    }
    named = list(spaces.values())
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=17, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(named, named[1:])) and doubled_ok,
        "search_spaces": spaces,
        "doubled_n": doubled_params["n"],
        "doubled_search_space": search_space(doubled),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    # G8: query reordering, primitive-root coordinate change, and their composition.
    invariant_checks = 0
    witness_transport_checks = 0
    invariant_failures = []
    distinct_keys = []
    for offset in range(20):
        inst = make_instance(
            seed=12000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        base_key = canonical_key(inst)
        distinct_keys.append(base_key)

        permutation = list(range(inst["n"]))
        random.Random(22000 + offset).shuffle(permutation)
        reordered = dict(inst)
        reordered["queries"] = [inst["queries"][old] for old in permutation]
        reordered["answer"] = [
            [new, inst["answer"][old][1]]
            for new, old in enumerate(permutation)
        ]
        if canonical_key(reordered) != base_key:
            invariant_failures.append(f"seed {offset}: query reorder")
        invariant_checks += 1
        witness_transport_checks += int(verify(reordered, reordered["answer"])[0])

        period = inst["q"] - 1
        unit = next(u for u in range(3, 30, 2) if math.gcd(u, period) == 1)
        inverse_unit = pow(unit, -1, period)
        relabelled = dict(inst)
        relabelled["alpha"] = pow(inst["alpha"], unit, inst["q"])
        relabelled["queries"] = [
            {
                "w": query["w"] * inverse_unit % period,
                "x": query["x"],
            }
            for query in inst["queries"]
        ]
        if canonical_key(relabelled) != base_key:
            invariant_failures.append(f"seed {offset}: exponent relabelling")
        invariant_checks += 1
        witness_transport_checks += int(verify(relabelled, inst["answer"])[0])

        composed = dict(relabelled)
        composed["queries"] = [relabelled["queries"][old] for old in permutation]
        composed["answer"] = [
            [new, inst["answer"][old][1]]
            for new, old in enumerate(permutation)
        ]
        if canonical_key(composed) != base_key:
            invariant_failures.append(f"seed {offset}: composed relabelling")
        invariant_checks += 1
        witness_transport_checks += int(verify(composed, composed["answer"])[0])

    report["G8_canonical_key"] = {
        "pass": not invariant_failures
        and witness_transport_checks == invariant_checks
        and len(set(distinct_keys)) == 20,
        "invariance_checks": invariant_checks,
        "witness_transport_checks": witness_transport_checks,
        "invariance_failures": invariant_failures,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "query reordering",
            "cyclic exponent-coordinate automorphism",
            "composition of both",
        ],
    }

    # G9: transcript arms are constants patched after script-owned runs; they are
    # diagnostic under the current contract.  The sole gate is the locally
    # measured answer-size/operation cap, obtained without reading any files.
    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 0
    for query in shipping["queries"]:
        argument = (1 - query["x"]) % shipping["q"]
        _, cost = _jacobi_with_cost(argument, shipping["q"])
        intended_operations += cost + 2  # form 1-x and select the adjacent level
    intended_operations_worst_case = shipping["n"] * (
        shipping["max_jacobi_steps"] + 2
    )
    arms = {
        key: dict(ORACLE_ARM_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations_worst_case <= 300
    )
    diagnostic_complete = all(arms[key]["attempts"] > 0 for key in arms)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "caps_pass": within_caps,
        "diagnostic_complete": diagnostic_complete,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": ORACLE_ARM_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_operations_worst_case": intended_operations_worst_case,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
