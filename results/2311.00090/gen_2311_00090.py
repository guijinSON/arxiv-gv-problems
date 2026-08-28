"""Inverse generator for a doubly-weighted zero-sum witness problem.

The problem is specialized to singleton weight sets A={1} and B={q} in
Z/(t*q)Z.  A witness is therefore a sorted list of exactly t sequence indices
whose values sum to zero modulo t*q; the second weighted equation is automatic
because t*q is zero modulo t*q.

This module uses only the Python standard library and performs no I/O.
"""

from __future__ import annotations

import itertools
import math
import random
import re
from typing import Any


DIFFICULTY: dict[str, dict[str, int]] = {
    # The demo preset is deliberately small enough for exact enumeration.  It is
    # retained for examples and diagnostics, not as a hardness claim.
    "demo": {"n": 12, "modulus_bits": 24},
    "medium": {"n": 40, "modulus_bits": 80},
    "hard": {"n": 64, "modulus_bits": 128},
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper audit (arXiv:2311.00090v4, read in full): Section 1, especially the
definition immediately before Observation 1.1, fixes the two simultaneous
congruences.  This generator uses R=M=Z/(tq)Z, A={1}, and B={q}.  A subsequence
of t terms has sum_i b_i*a_i=tq=0; its other congruence is exactly the modular
subset-sum checked here.

Easy regimes deliberately avoided: Observation 1.2 and Remark 1.4 expose a
constant-weight/length shortcut; Theorems 2.2--2.4 completely describe the
(1,1) constants; Theorems 3.3 and 3.4 make the (Z_n',1) D/C problems collapse
at lengths 3 and 4; Theorems 7.2 and 7.3 give the same constant-size phenomenon
when the first weight set is all nonzero residues.  We keep A singleton, make
the order of q in the additive group grow as t, use 2t-1 terms, and make the
modulus exponential in t, so the usual pseudo-polynomial dynamic program is
exponential in the input length.

Worst-case hardness is inherited from exact-cardinality subset sum.  A direct
reduction can encode each original item/dummy pair in a separate high radix
digit, require one member of each pair, add one residue representing minus the
target, and round a sufficiently large modulus up to a multiple of t.  It has
2t-1 residues and a size-t zero-sum exactly when the subset-sum instance is
satisfiable.  This is a worst-case statement, not a proof that the planted
distribution is average-case hard.

Planting and attacks: the planted subset and its pivot are uniformly random.
Every non-pivot entry is uniform modulo M, and the pivot (the negative sum of
at least one uniform entry) is uniform too, so plants and decoys have identical
one-element marginals.  The self-test challenges magnitude/outlier selection,
a circular-residue greedy rule, and random restarts with a two-sum completion;
all must fail on eight seeds.  Difficulty comes from crowded subset choices and
growing t, not from a different plant distribution.
""".strip()


def make_instance(n: int, seed: int = 0, **params: Any) -> dict[str, Any]:
    """Sample a size-n answer first, then construct a modular zero-sum around it.

    ``n`` is both the required witness size t and the main size parameter.  The
    public sequence has 2*n-1 entries.  ``modulus_bits`` defaults to 2*n, keeping
    the number of candidate subsets comparable to the modulus while both grow
    exponentially with n.
    """

    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    unknown = set(params) - {"modulus_bits"}
    if unknown:
        raise TypeError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
    modulus_bits = params.get("modulus_bits", max(16, 2 * n))
    if (
        isinstance(modulus_bits, bool)
        or not isinstance(modulus_bits, int)
        or modulus_bits < n.bit_length() + 3
    ):
        raise ValueError("modulus_bits must leave at least three bits for q")

    rng = random.Random(seed)
    length = 2 * n - 1

    # M=n*q and b=q make the additive order of b in Z_M exactly n.  Choosing q
    # at random also avoids a fixed power-of-two modulus or other CRT signature.
    q_bits = modulus_bits - n.bit_length() + 1
    q = rng.getrandbits(q_bits)
    q |= 1 << (q_bits - 1)
    q |= 1
    modulus = n * q

    planted_zero_based = sorted(rng.sample(range(length), n))
    pivot = rng.choice(planted_zero_based)
    sequence = [rng.randrange(modulus) for _ in range(length)]
    sequence[pivot] = -sum(
        sequence[i] for i in planted_zero_based if i != pivot
    ) % modulus

    answer = [i + 1 for i in planted_zero_based]
    return {
        "paper": "arXiv:2311.00090v4",
        "family": "singleton doubly-weighted zero-sum subsequence",
        "n": n,
        "length": length,
        "modulus": modulus,
        "a_weight": 1,
        "b_weight": q,
        "required_size": n,
        "sequence": sequence,
        "answer": answer,
    }


def render(inst: dict[str, Any]) -> str:
    """Render a self-contained problem statement without exposing the plant."""

    modulus = inst["modulus"]
    q = inst["b_weight"]
    required = inst["required_size"]
    sequence = inst["sequence"]
    rows = "\n".join(
        f"{start}: "
        + " ".join(str(x) for x in sequence[start - 1 : start - 1 + 8])
        for start in range(1, len(sequence) + 1, 8)
    )
    example = ", ".join(str(i) for i in range(1, required + 1))
    return f"""Doubly-weighted zero-sum subsequence

All arithmetic in this problem is modulo M = {modulus}.  The sequence below has
{len(sequence)} entries x_1,...,x_{len(sequence)}.  Indices are 1-based.

The two allowed weight sets are singletons: A = {{1}} and B = {{{q}}}.  Thus a
chosen subsequence with indices I has fixed weights a_i=1 and b_i={q} and is
doubly-weighted zero-sum exactly when both congruences hold:

    sum(x_i for i in I) = 0 (mod M)
    sum(b_i*a_i for i in I) = 0 (mod M).

Find exactly {required} DISTINCT indices.  The second congruence then holds because
{required}*{q} = M.  Your remaining task is to make the selected sequence values
sum to 0 modulo M.  Return the indices in STRICTLY INCREASING order; order does
not otherwise matter, and repeated indices are forbidden.  Every index endpoint
is inclusive, so each index must be an integer from 1 through {len(sequence)}.

Sequence data is laid out as "first_index: values", with consecutive indices
across and then down:
{rows}

Give your final answer inside <answer></answer> tags, as exactly {required}
comma-separated decimal indices in strictly increasing order.
Example of the required FORMAT only (not a claim that it is valid here):
<answer>{example}</answer>
Output nothing else inside the tags."""


_ANSWER_BLOCK = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_CSV_INTEGERS = re.compile(r"\s*\d+\s*(?:,\s*\d+\s*)*")


def parse_answer(text: str) -> list[int] | None:
    """Extract the LAST well-formed tagged comma-separated integer list.

    Models often emit a draft answer then a correction; the final block wins.
    """

    if not isinstance(text, str):
        return None
    matches = _ANSWER_BLOCK.findall(text)
    if not matches:
        return None
    body = matches[-1]
    if _CSV_INTEGERS.fullmatch(body) is None:
        return None
    try:
        return [int(part.strip(), 10) for part in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst: dict[str, Any], answer: object) -> tuple[bool, str]:
    """Check any witness using public instance fields only."""

    if not isinstance(answer, list):
        return False, "answer must be a list"
    if not answer:
        return False, "answer must be a nonempty list"
    required = inst["required_size"]
    if len(answer) != required:
        return False, f"wrong number of indices: expected {required}"
    if any(isinstance(i, bool) or not isinstance(i, int) for i in answer):
        return False, "every index must be an integer"
    length = len(inst["sequence"])
    if any(i < 1 or i > length for i in answer):
        return False, f"index out of range: allowed range is 1..{length}"
    if len(set(answer)) != len(answer):
        return False, "indices must be distinct"
    if any(a >= b for a, b in zip(answer, answer[1:])):
        return False, "indices must be in strictly increasing order"

    modulus = inst["modulus"]
    first_sum = sum(inst["sequence"][i - 1] for i in answer) % modulus
    if first_sum != 0:
        return False, f"selected values sum to {first_sum}, not 0 modulo M"
    second_sum = (
        len(answer) * inst["a_weight"] * inst["b_weight"]
    ) % modulus
    if second_sum != 0:
        return False, f"weighted coefficients sum to {second_sum}, not 0 modulo M"
    return True, "ok"


def random_candidate(inst: dict[str, Any], rng: random.Random) -> list[int]:
    """Uniformly sample a structurally valid candidate subset.

    Exact cardinality, distinctness, range, and canonical ordering are all free
    from the statement, so the sampler enforces all four before guessing.
    """

    required = inst["required_size"]
    length = len(inst["sequence"])
    return sorted(rng.sample(range(1, length + 1), required))


def search_space(inst: dict[str, Any]) -> int:
    """Number of shape-valid candidates: all size-t subsets of 2t-1 indices."""

    return math.comb(len(inst["sequence"]), inst["required_size"])


_ENUMERATION_CAP = 2_000_000


def enumerate_all(inst: dict[str, Any]) -> int | None:
    """Count all witnesses exactly when at most two million candidates exist."""

    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    modulus = inst["modulus"]
    sequence = inst["sequence"]
    required = inst["required_size"]
    count = 0
    for chosen in itertools.combinations(range(len(sequence)), required):
        if sum(sequence[i] for i in chosen) % modulus == 0:
            count += 1
    return count


def _attack_outlier(inst: dict[str, Any]) -> list[int]:
    """Choose entries whose centered residues have the smallest magnitudes."""

    modulus = inst["modulus"]
    required = inst["required_size"]
    ranked = sorted(
        range(len(inst["sequence"])),
        key=lambda i: (min(inst["sequence"][i], modulus - inst["sequence"][i]), i),
    )
    return sorted(i + 1 for i in ranked[:required])


def _attack_greedy(inst: dict[str, Any]) -> list[int]:
    """Greedily keep the running residue as close to zero as possible."""

    modulus = inst["modulus"]
    values = inst["sequence"]
    required = inst["required_size"]
    remaining = set(range(len(values)))
    chosen: list[int] = []
    residue = 0
    for _ in range(required):
        pick = min(
            remaining,
            key=lambda i: (
                min((residue + values[i]) % modulus, (-residue - values[i]) % modulus),
                i,
            ),
        )
        chosen.append(pick + 1)
        residue = (residue + values[pick]) % modulus
        remaining.remove(pick)
    return sorted(chosen)


def _attack_random_restart(
    inst: dict[str, Any], rng: random.Random, attempts: int = 256
) -> list[int] | None:
    """Randomly fix t-2 entries and complete them with an exact two-sum."""

    modulus = inst["modulus"]
    values = inst["sequence"]
    required = inst["required_size"]
    universe = list(range(len(values)))
    for _ in range(attempts):
        prefix = set(rng.sample(universe, required - 2))
        need = -sum(values[i] for i in prefix) % modulus
        by_value: dict[int, int] = {}
        for j in universe:
            if j in prefix:
                continue
            complement = (need - values[j]) % modulus
            k = by_value.get(complement)
            if k is not None and k != j:
                return sorted(i + 1 for i in (*prefix, k, j))
            by_value.setdefault(values[j], j)
    return None


def selftest() -> dict[str, Any]:
    """Run correctness, sparsity, guessing, attack, and scaling gates."""

    report: dict[str, Any] = {
        "paper": "2311.00090",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "presets": DIFFICULTY,
        "gates": {},
    }

    # G1: every preset, several independent seeds.
    g1_runs = []
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 2, 7):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            g1_runs.append(
                {"preset": preset, "seed": seed, "passed": ok, "reason": reason}
            )
    report["gates"]["G1_planted_verifies"] = {
        "passed": all(run["passed"] for run in g1_runs),
        "runs": g1_runs,
    }

    ship_kwargs = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=101, **ship_kwargs)
    planted = inst["answer"]

    # G2: arrange each malformed witness to exercise a distinct diagnostic.
    swapped = planted[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = planted[:]
    duplicate[-1] = duplicate[0]
    outside = planted[:]
    outside[-1] = len(inst["sequence"]) + 1
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "swap_adjacent_order": swapped,
        "duplicate": duplicate,
        "out_of_range": outside,
    }
    g2_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["gates"]["G2_rejects_corruption"] = {
        "passed": all(item["rejected"] for item in g2_results.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reason_count": len(set(reasons)),
        "results": g2_results,
    }

    # G3: prose and a Markdown fence surround the exact contract.
    csv = ", ".join(map(str, planted))
    realistic = (
        "I checked both congruences. My final response is:\n\n"
        f"```text\n<answer>  {csv}  </answer>\n```\n"
        "The tags contain only the requested indices."
    )
    parsed = parse_answer(realistic)
    report["gates"]["G3_round_trip"] = {
        "passed": parsed == planted,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("```no tagged answer```") is None,
    }
    report["gates"]["G3_round_trip"]["passed"] &= report["gates"][
        "G3_round_trip"
    ]["garbage_returns_none"]

    # G4: uniform over every structural constraint stated to the solver.
    guess_rng = random.Random(0x231100090)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    probability = hits / total
    report["gates"]["G4_guess_resistance"] = {
        "passed": probability < 1e-6,
        "hits": hits,
        "total": total,
        "measured_probability": probability,
        "sampler": "uniform size-t subsets; sorted, distinct, and in range",
        "search_space": search_space(inst),
    }

    # G5: exact enumeration on the deliberately enumerable demo preset.
    sparse_inst = make_instance(seed=303, **DIFFICULTY["demo"])
    valid_count = enumerate_all(sparse_inst)
    sparse_space = search_space(sparse_inst)
    sparse_fraction = None if valid_count is None else valid_count / sparse_space
    report["gates"]["G5_sparse"] = {
        "passed": valid_count is not None
        and valid_count >= 1
        and sparse_fraction is not None
        and sparse_fraction < 1e-5,
        "preset": "demo",
        "seed": 303,
        "valid_answers": valid_count,
        "search_space": sparse_space,
        "fraction": sparse_fraction,
        "enumeration_cap": _ENUMERATION_CAP,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: attacks are deliberately informed by how the generator plants.
    attack_rows: dict[str, list[dict[str, Any]]] = {
        "outlier_centered_magnitude": [],
        "greedy_circular_residue": [],
        "random_restart_two_sum": [],
    }
    for seed in range(800, 808):
        attacked = make_instance(seed=seed, **ship_kwargs)
        candidates = {
            "outlier_centered_magnitude": _attack_outlier(attacked),
            "greedy_circular_residue": _attack_greedy(attacked),
            "random_restart_two_sum": _attack_random_restart(
                attacked, random.Random(seed ^ 0xA77AC), attempts=256
            ),
        }
        for name, candidate in candidates.items():
            if candidate is None:
                solved = False
                reason = "attack found no completion"
            else:
                solved, reason = verify(attacked, candidate)
            attack_rows[name].append(
                {"seed": seed, "solved": solved, "reason": reason}
            )
    attack_pass = {
        name: not any(row["solved"] for row in rows)
        for name, rows in attack_rows.items()
    }
    report["gates"]["G6_adversary_panel"] = {
        "passed": len(attack_rows) >= 3 and all(attack_pass.values()),
        "seeds_per_attack": 8,
        "attack_passed": attack_pass,
        "results": attack_rows,
    }

    # G7: double both witness size and target modulus bit length.
    doubled_kwargs = dict(ship_kwargs)
    doubled_kwargs["n"] *= 2
    doubled_kwargs["modulus_bits"] *= 2
    doubled = make_instance(seed=909, **doubled_kwargs)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["gates"]["G7_scales"] = {
        "passed": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst),
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_sequence_length": len(inst["sequence"]),
        "doubled_sequence_length": len(doubled["sequence"]),
        "base_modulus_bits": inst["modulus"].bit_length(),
        "doubled_modulus_bits": doubled["modulus"].bit_length(),
        "base_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "verification_reason": doubled_reason,
    }

    report["all_passed"] = all(gate["passed"] for gate in report["gates"].values())
    return report


__all__ = [
    "DIFFICULTY",
    "SHIPPING_DIFFICULTY",
    "NOTES",
    "make_instance",
    "render",
    "parse_answer",
    "verify",
    "random_candidate",
    "search_space",
    "enumerate_all",
    "selftest",
]
