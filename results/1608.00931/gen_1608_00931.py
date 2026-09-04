"""Verified generators for Suleimanova--Perfect spectral certificates.

The family uses the exact reduction in Lemma 4.1 of arXiv:1608.00931.
An instance is a real spectrum with two equal Perron roots and negative integer
eigenvalues.  A witness partitions the negative magnitudes into two equal-sum
sets, which is precisely a partition into two Suleimanova lists.

Generation is inverse: four-element equal-pair-sum identities are sampled
first, then hidden among large integer magnitudes.  The module is deterministic
in ``(n, seed, params)``, standard-library only, and silent on import.
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
from typing import Any


TRACK = "B"

_REDUCTION_CITATION = (
    "Section 4, Lemma 4.1 (I maps to (sum(I)/2, sum(I)/2, "
    "-i_n, ..., -i_1)); Section 5, Theorem 5.4 (an SP partition is an "
    "NP certificate)"
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "integer_lattice",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "real spectrum with integer eigenvalues",
        "partition into Suleimanova sublists",
    ],
    "verification_operations": [
        "exact integer summation",
        "index partition check",
        "Suleimanova sign and trace inequalities",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION_CITATION,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Residues modulo 997 reveal four-element blocks whose two equal-sum "
        "pairs compose into the required spectral partition; without that "
        "decomposition one faces balanced PARTITION."
    ),
    "hardness_basis": (
        "Track B: at shipping n=64 the domain-standard fixed-cardinality "
        "Horowitz--Sahni meet-in-the-middle algorithm is O(2^(n/2)) and "
        "requires 6,442,450,944 half-subset states; a measured 1,048,576-state "
        "shipping prefix records its cost, while the successful O(n) residue "
        "decoder uses at most 160 exact operations, chiefly 64 reductions of "
        "20-digit integers that are not mechanically executable without tools."
    ),
    # A character is a conservative upper bound on a tokenizer token.  The
    # actual compact JSON answer is measured again in G9.
    "max_answer_tokens": 106,
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
    "demo": {"n": 8, "payload_bits": 5},
    # The original n=36 easy rung passed bare hardening but all three hinted
    # oracles solved it.  G9(b) permits one upward slide, so the old medium is
    # now the first evaluated rung and n=64 is the shipping candidate.
    "easy": {"n": 64, "payload_bits": 48},
    "medium": {"n": 96, "payload_bits": 64},
    "hard": {"n": 128, "payload_bits": 96},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Reduce every magnitude modulo 997: each four-element residue bucket "
    "contains two complementary pairs with identical sums."
)
PLACEBO_HINT = (
    "Compare every magnitude carefully: the indexed presentation is intended "
    "to make exact bookkeeping and transcription more reliable."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly n/2 distinct 0-based "
        "indices, including index 0; n is divisible by 4 and at most 256."
    ),
    "bounds": {
        "max_indices": 128,
        "max_index": 255,
        "index_bits": 8,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 defines a realizable real list as the
spectrum of a nonnegative matrix.  Section 2 defines the
Suleimanova--Perfect (SP) criterion: the spectrum must partition into
Suleimanova lists, each having one nonnegative entry, all remaining entries
negative, and nonnegative trace.  Section 4, Lemma 4.1 gives the exact map
I -> (sum(I)/2, sum(I)/2, -i_n, ..., -i_1) and proves that realizability (and
SP membership) is equivalent to an equal partition of I.  Section 5,
Theorem 5.4 explicitly identifies the partition as a polynomially checkable
certificate and proves rational SP membership NP-complete.

What is easy.  Section 1 says RNIEP is completely characterized only through
order four.  Section 5 proves all Group-1 criteria (Su, Ci, Ke, Sa, Fi, So_1)
decidable in polynomial time by at most n linear inequalities.  It also warns
that a rational spectrum need not have a known rational nonnegative-matrix
certificate, so this module does not make the unjustified "sample a matrix and
publish arbitrary rational eigenvalues" move suggested by the prior triage.

Generation and Track B.  Each hidden four-element block is sampled from an
identity a+b=c+d, with the derived coordinate and the four public positions
randomized.  A common dominating offset forces every equal partition to use
exactly n/2 items.  The block members share a residue modulo 997, tags are
distinct, and input indices are globally shuffled.  Consequently a computer
can recover a witness in O(n) by residue bucketing and three local pair tests;
this is the successful reference algorithm, not a Track-A hardness claim.  At
shipping n=64, generic fixed-cardinality meet-in-the-middle requires exactly
2^31 + 2^32 = 6,442,450,944 half-subset states.  Selftest times a 2^20-state
prefix at shipping size; the compact decomposition needs at most 160 exact
operations after it is seen.  The original n=36 rung passed the bare oracle
loop but failed G9(b) when all three structurally hinted oracles solved it, so
the one permitted ladder move raised shipping to n=64.

Attacks.  Plants and decoys are not separate populations: every public number
is a member of a planted identity and the derived coordinate is randomized.
The panel tests smallest-magnitude outliers, balanced largest-first greedy,
fixed-cardinality two-swap random restart, and the hand-runnable ansatz that
consecutive magnitudes form the four-item blocks.  The randomized public order,
common offset, and interleaved payloads defeat those probes.  The successful
mod-997 decoder is reported separately, as Track B requires.
""".strip()


_Q = 997
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000


def _validate_params(n: int, payload_bits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 8 or n % 4:
        raise ValueError("n must be a multiple of 4 and at least 8")
    if n > 256:
        raise ValueError("n may not exceed the 256-element answer cap")
    if isinstance(payload_bits, bool) or not isinstance(payload_bits, int):
        raise ValueError("payload_bits must be an integer")
    if payload_bits < 5 or payload_bits > 512:
        raise ValueError("payload_bits must lie in 5..512")


def _identity_payloads(rng: random.Random, bits: int) -> tuple[int, int, int, int]:
    """Uniformly sample three coordinates and derive a randomized fourth.

    Randomizing which signed coordinate is derived, followed by a random
    permutation, prevents the certificate coordinate from occupying a special
    public position.  Rejection keeps every payload in the same interval.
    """
    lo = 1 << (bits - 1)
    hi = (1 << bits) - 1
    while True:
        # Signs encode x0+x1=x2+x3.  Choosing the missing coordinate uniformly
        # makes the construction exchangeable across the four public values.
        missing = rng.randrange(4)
        values: list[int | None] = [None, None, None, None]
        for i in range(4):
            if i != missing:
                values[i] = rng.randint(lo, hi)
        if missing == 0:
            values[0] = values[2] + values[3] - values[1]  # type: ignore[operator]
        elif missing == 1:
            values[1] = values[2] + values[3] - values[0]  # type: ignore[operator]
        elif missing == 2:
            values[2] = values[0] + values[1] - values[3]  # type: ignore[operator]
        else:
            values[3] = values[0] + values[1] - values[2]  # type: ignore[operator]
        row = [int(x) for x in values]
        if all(lo <= x <= hi for x in row) and len(set(row)) == 4:
            return row[0], row[1], row[2], row[3]


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate an SP spectrum and a partition certificate.

    ``n`` is the number of negative eigenvalues.  Larger n creates more hidden
    four-item blocks and a larger balanced-partition space.  ``payload_bits``
    increases pseudo-polynomial search cost without lengthening the answer.
    """
    allowed = {"payload_bits"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    payload_bits = params.get("payload_bits", max(16, n // 2))
    _validate_params(n, payload_bits)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    groups = n // 4
    tags = rng.sample(range(_Q), groups)
    records: list[tuple[int, int, int]] = []

    # The variable part is strictly smaller than this bound.  The common
    # offset exceeds the sum of all variable parts, so equality forces both
    # sides to have the same cardinality.
    variable_bound = _Q * (1 << payload_bits) + _Q
    common_offset = n * variable_bound + 1

    for group, tag in enumerate(tags):
        a, b, c, d = _identity_payloads(rng, payload_bits)
        rows = [
            (common_offset + _Q * a + tag, group, 0),
            (common_offset + _Q * b + tag, group, 0),
            (common_offset + _Q * c + tag, group, 1),
            (common_offset + _Q * d + tag, group, 1),
        ]
        rng.shuffle(rows)
        records.extend(rows)

    rng.shuffle(records)
    orientation = [rng.randrange(2) for _ in range(groups)]
    weights = [row[0] for row in records]
    answer = [i for i, (_, group, side) in enumerate(records)
              if side == orientation[group]]
    if 0 not in answer:
        selected = set(answer)
        answer = [i for i in range(n) if i not in selected]
    answer.sort()

    total = sum(weights)
    if total % 2:
        raise AssertionError("identity composition produced an odd total")
    rho = total // 2
    return {
        "family": "suleimanova_perfect_partition",
        "n": n,
        "payload_bits": payload_bits,
        "perron_root": rho,
        "weights": weights,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete spectral-certificate problem and answer contract."""
    n = inst["n"]
    rows = "\n".join(f"{i}: {w}" for i, w in enumerate(inst["weights"]))
    statement = f"""Suleimanova--Perfect certificate for a real spectrum

A real list is called a Suleimanova list when it has exactly one nonnegative
entry, every other entry is negative, and the sum of all its entries is
nonnegative.  A Suleimanova--Perfect (SP) certificate for a spectrum is a
partition of all its entries into Suleimanova lists.

This instance is the spectrum (multiset)

  Lambda = ({inst['perron_root']}, {inst['perron_root']}, -w[0], ..., -w[{n - 1}]).

The two displayed positive entries are distinct copies of the same Perron
root.  The negative entries are indexed below; input order has no mathematical
meaning.  All arithmetic is exact integer arithmetic.

Find an SP certificate consisting of exactly two blocks, with one positive
Perron-root copy in each block.  Equivalently, return indices J such that
sum(w[i] for i in J) equals {inst['perron_root']}; the complementary indices
go with the other Perron root.  To remove the symmetry between the two blocks,
J must contain index 0.  It must contain exactly {n // 2} distinct indices.

Indexed negative magnitudes w[i]:
{rows}

Return J as one strictly increasing JSON array of exactly {n // 2} distinct
0-based indices.  Repeats are forbidden, and every index must lie in
0..{n - 1}.

Give your final answer inside <answer></answer> tags, as one JSON array of
integers.
Syntax-only example (not instance data): <answer>[0, 2, 5, 7]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON integer list; never raise on garbage."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if (isinstance(value, list)
                and all(isinstance(x, int) and not isinstance(x, bool)
                        for x in value)):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid two-block SP partition without consulting the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array of indices"
    if not answer:
        return False, "the index set J must not be empty"
    if any(isinstance(i, bool) or not isinstance(i, int) for i in answer):
        return False, "every member of J must be an integer index"
    n = inst.get("n")
    weights = inst.get("weights")
    rho = inst.get("perron_root")
    if (not isinstance(n, int) or not isinstance(weights, list)
            or len(weights) != n or not isinstance(rho, int)):
        return False, "malformed spectral instance"
    if len(answer) != n // 2:
        return False, f"J must contain exactly {n // 2} indices"
    if len(set(answer)) != len(answer):
        return False, "indices in J must be distinct"
    if any(i < 0 or i >= n for i in answer):
        return False, f"every index must lie in 0..{n - 1}"
    if answer != sorted(answer):
        return False, "indices in J must be strictly increasing"
    if answer[0] != 0:
        return False, "J must contain index 0 to fix block symmetry"
    if any(isinstance(w, bool) or not isinstance(w, int) or w <= 0
           for w in weights):
        return False, "malformed spectral instance: magnitudes must be positive integers"
    selected = sum(weights[i] for i in answer)
    if selected != rho:
        return False, f"selected magnitudes sum to {selected}, not {rho}"
    if sum(weights) - selected != rho:
        return False, "complementary block does not have zero trace"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied balanced, symmetry-fixed space."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    n = inst["n"]
    rest = rng.sample(range(1, n), n // 2 - 1)
    return [0] + sorted(rest)


def search_space(inst: dict) -> int | None:
    """Exact size of the bounded language sampled by random_candidate."""
    n = inst["n"]
    return math.comb(n - 1, n // 2 - 1)


def enumerate_all(inst: dict) -> int | None:
    """Count all valid canonical subsets when the exact space is capped."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    weights = inst["weights"]
    rho = inst["perron_root"]
    hits = 0
    for tail in itertools.combinations(range(1, n), n // 2 - 1):
        if weights[0] + sum(weights[i] for i in tail) == rho:
            hits += 1
    return hits


def canonical_key(inst: dict) -> str:
    """Canonical under index relabelling and positive integral scaling."""
    weights = inst["weights"]
    if not weights or any(not isinstance(w, int) or w <= 0 for w in weights):
        raise ValueError("canonical_key requires positive integer magnitudes")
    scale = 0
    for w in weights:
        scale = math.gcd(scale, w)
    normalized = sorted(w // scale for w in weights)
    form = [len(weights), normalized]
    payload = json.dumps(form, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """First enlarge coefficient entropy at fixed answer length, then n."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = params.get("n")
    bits = params.get("payload_bits", max(16, n // 2) if isinstance(n, int) else 16)
    if not isinstance(n, int) or not isinstance(bits, int):
        return None
    out = dict(params)
    if bits < 160:
        out["payload_bits"] = bits + 32
        return out
    if n < 256:
        out["n"] = min(256, n + 32 - (n % 4))
        out["payload_bits"] = bits + 16
        return out
    return "cap_bound"


def _canonical_side(indices: list[int], n: int) -> list[int]:
    side = sorted(indices)
    if 0 in side:
        return side
    chosen = set(side)
    return [i for i in range(n) if i not in chosen]


def _outlier_attack(inst: dict) -> list[int]:
    """Choose the numerically smallest half of the magnitudes."""
    n = inst["n"]
    indices = sorted(range(n), key=lambda i: (inst["weights"][i], i))[:n // 2]
    return _canonical_side(indices, n)


def _balanced_greedy_attack(inst: dict) -> list[int]:
    """Largest-first balanced greedy with an exact cardinality quota."""
    n = inst["n"]
    quota = n // 2
    sides: list[list[int]] = [[], []]
    totals = [0, 0]
    order = sorted(range(n), key=lambda i: (-inst["weights"][i], i))
    for index in order:
        if len(sides[0]) == quota:
            side = 1
        elif len(sides[1]) == quota:
            side = 0
        else:
            side = 0 if totals[0] <= totals[1] else 1
        sides[side].append(index)
        totals[side] += inst["weights"][index]
    return _canonical_side(sides[0], n)


def _adjacent_block_attack(inst: dict) -> list[int]:
    """Hand ansatz: consecutive sorted quartets are the hidden blocks."""
    n = inst["n"]
    weights = inst["weights"]
    order = sorted(range(n), key=lambda i: (weights[i], i))
    chosen: list[int] = []
    for start in range(0, n, 4):
        block = order[start:start + 4]
        pairs = list(itertools.combinations(block, 2))
        pair = min(
            pairs,
            key=lambda p: (abs(2 * (weights[p[0]] + weights[p[1]])
                              - sum(weights[i] for i in block)), p),
        )
        chosen.extend(pair)
    return _canonical_side(chosen, n)


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 24, steps: int = 160,
                           swap_trials: int = 48) -> tuple[list[int], int]:
    """Fixed-cardinality stochastic two-swap descent."""
    n = inst["n"]
    weights = inst["weights"]
    total = sum(weights)
    best_answer = random_candidate(inst, rng)
    best_score = abs(2 * sum(weights[i] for i in best_answer) - total)
    iterations = 0
    for _ in range(restarts):
        current = set(rng.sample(range(n), n // 2))
        current_sum = sum(weights[i] for i in current)
        for _ in range(steps):
            iterations += 1
            score = abs(2 * current_sum - total)
            if score == 0:
                return _canonical_side(list(current), n), iterations
            inside = tuple(current)
            outside = tuple(i for i in range(n) if i not in current)
            trial_best = None
            for _ in range(swap_trials):
                take = inside[rng.randrange(len(inside))]
                give = outside[rng.randrange(len(outside))]
                trial_sum = current_sum - weights[take] + weights[give]
                trial_score = abs(2 * trial_sum - total)
                row = (trial_score, take, give, trial_sum)
                if trial_best is None or row < trial_best:
                    trial_best = row
            assert trial_best is not None
            trial_score, take, give, trial_sum = trial_best
            if trial_score >= score and rng.randrange(8):
                continue
            current.remove(take)
            current.add(give)
            current_sum = trial_sum
            if trial_score < best_score:
                best_score = trial_score
                best_answer = _canonical_side(list(current), n)
    return best_answer, iterations


def _meet_in_middle_attack(inst: dict,
                           max_half_states: int = 1 << 20
                           ) -> tuple[list[int] | None, int]:
    """Horowitz--Sahni fixed-cardinality PARTITION, with a hard state cap.

    This is the domain-standard mechanical baseline for the Track-B claim.
    The canonical language requires index 0, so the left table enumerates the
    remaining indices in the left half and the right scan looks up both the
    missing sum and the missing cardinality.
    """
    n = inst["n"]
    split = n // 2
    left_weights = inst["weights"][1:split]
    right_weights = inst["weights"][split:]
    if ((1 << len(left_weights)) > max_half_states
            or (1 << len(right_weights)) > max_half_states):
        return None, 0

    left_size = 1 << len(left_weights)
    left_sums = [0] * left_size
    left_counts = bytearray(left_size)
    left_table: dict[tuple[int, int], int] = {(0, 0): 0}
    operations = 0
    for mask in range(1, left_size):
        bit = mask & -mask
        coordinate = bit.bit_length() - 1
        previous = mask ^ bit
        left_sums[mask] = left_sums[previous] + left_weights[coordinate]
        left_counts[mask] = left_counts[previous] + 1
        left_table.setdefault((left_counts[mask], left_sums[mask]), mask)
        operations += 1

    right_size = 1 << len(right_weights)
    right_sums = [0] * right_size
    right_counts = bytearray(right_size)
    needed_total = inst["perron_root"] - inst["weights"][0]
    needed_count = n // 2 - 1
    for mask in range(right_size):
        if mask:
            bit = mask & -mask
            coordinate = bit.bit_length() - 1
            previous = mask ^ bit
            right_sums[mask] = right_sums[previous] + right_weights[coordinate]
            right_counts[mask] = right_counts[previous] + 1
            operations += 1
        left_mask = left_table.get(
            (needed_count - right_counts[mask], needed_total - right_sums[mask])
        )
        operations += 1
        if left_mask is None:
            continue
        answer = [0]
        answer.extend(
            1 + j for j in range(len(left_weights)) if left_mask & (1 << j)
        )
        answer.extend(
            split + j for j in range(len(right_weights)) if mask & (1 << j)
        )
        return answer, operations
    return None, operations


def _meet_in_middle_prefix(inst: dict,
                           state_cap: int = 1 << 20) -> tuple[int, int, int]:
    """Execute a capped prefix of the standard left-half enumeration.

    Returns ``(performed, required_total, checksum)``.  The checksum makes the
    benchmark consume the computed exact sums instead of timing an empty loop.
    ``required_total`` includes the left table (index 0 forced) and right scan.
    """
    n = inst["n"]
    split = n // 2
    left_weights = inst["weights"][1:split]
    left_required = 1 << len(left_weights)
    right_required = 1 << (n - split)
    limit = min(state_cap, left_required)
    sums = [0] * limit
    checksum = 0
    for mask in range(1, limit):
        bit = mask & -mask
        coordinate = bit.bit_length() - 1
        previous = mask ^ bit
        # previous < mask < limit, so every dependency is in the prefix.
        sums[mask] = sums[previous] + left_weights[coordinate]
        checksum ^= sums[mask]
    return limit, left_required + right_required, checksum


def _reference_decode(inst: dict) -> tuple[list[int] | None, int]:
    """The successful Track-B O(n) residue decomposition algorithm."""
    buckets: dict[int, list[int]] = {}
    operations = 0
    for index, weight in enumerate(inst["weights"]):
        buckets.setdefault(weight % _Q, []).append(index)
        operations += 1
    chosen: list[int] = []
    for residue in sorted(buckets):
        block = buckets[residue]
        if len(block) != 4:
            return None, operations
        a, b, c, d = block
        candidates = [
            ((a, b), (c, d)),
            ((a, c), (b, d)),
            ((a, d), (b, c)),
        ]
        found = None
        for left, right in candidates:
            left_sum = inst["weights"][left[0]] + inst["weights"][left[1]]
            right_sum = inst["weights"][right[0]] + inst["weights"][right[1]]
            operations += 2
            if left_sum == right_sum:
                found = list(left)
                break
        if found is None:
            return None, operations
        chosen.extend(found)
    return _canonical_side(chosen, inst["n"]), operations


def _transform_instance(inst: dict, permutation: list[int] | None = None,
                        scale: int = 1) -> dict:
    """Carry the spectrum and witness through true family symmetries."""
    n = inst["n"]
    if permutation is None:
        permutation = list(range(n))
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation is not a relabelling of 0..n-1")
    if not isinstance(scale, int) or scale <= 0:
        raise ValueError("scale must be a positive integer")
    weights = [0] * n
    for old, new in enumerate(permutation):
        weights[new] = scale * inst["weights"][old]
    carried = _canonical_side([permutation[i] for i in inst["answer"]], n)
    return {
        "family": inst["family"],
        "n": n,
        "payload_bits": inst["payload_bits"],
        "perron_root": scale * inst["perron_root"],
        "weights": weights,
        "answer": carried,
    }


def selftest() -> dict:
    """Run G1--G9 and return machine-readable measured evidence."""
    report: dict[str, Any] = {}

    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (preset, seed, why)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "generation_route": "inverse generation plus composition of identities",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260904, **ship_params)
    answer = inst["answer"]
    unused = next(i for i in range(inst["n"]) if i not in set(answer))
    sum_bad = answer[:]
    sum_bad[-1] = unused
    sum_bad.sort()
    if sum_bad[0] != 0 or len(set(sum_bad)) != len(sum_bad):
        unused = next(i for i in range(1, inst["n"]) if i not in set(answer))
        sum_bad = sorted(answer[:-1] + [unused])
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": answer[:-1] + [answer[-2]],
        "out_of_range": answer[:-1] + [inst["n"]],
        "swap_adjacent": [answer[1], answer[0]] + answer[2:],
        "wrong_sum": sum_bad,
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "The two traces both vanish.\n```json\n<answer>"
        + json.dumps(answer)
        + "</answer>\n```\nI used zero-based indices."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged object") is None
    assert parse_answer("<answer>[0, nope]</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "answer_elements": len(answer),
        "json_native": True,
    }

    guess_inst = make_instance(seed=8675309, **ship_params)
    guess_rng = random.Random(13579)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            guess_hits += 1
    guess_density = guess_hits / guess_total
    assert guess_density < 1e-6, (guess_hits, guess_total)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_density,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform fixed-size subsets containing index 0",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1

    density_rng = random.Random(24680)
    density_inst = make_instance(seed=112358, **ship_params)
    density_total = 200_000
    density_hits = 0
    for _ in range(density_total):
        if verify(density_inst, random_candidate(density_inst, density_rng))[0]:
            density_hits += 1

    attack_seeds = list(range(3100, 3108))
    attacks = {
        "per_element_smallest_magnitude": {"successes": 0, "attempts": 8},
        "balanced_largest_first_greedy": {"successes": 0, "attempts": 8},
        "random_restart_two_swap_24x160": {"successes": 0, "attempts": 8},
        "by_hand_consecutive_quartets": {"successes": 0, "attempts": 8},
    }
    restart_iterations = 0
    restart_elapsed = 0.0
    compact_operations = []
    compact_elapsed = 0.0
    compact_successes = 0
    for seed in attack_seeds:
        target = make_instance(seed=seed, **ship_params)
        if verify(target, _outlier_attack(target))[0]:
            attacks["per_element_smallest_magnitude"]["successes"] += 1
        if verify(target, _balanced_greedy_attack(target))[0]:
            attacks["balanced_largest_first_greedy"]["successes"] += 1
        restart_t0 = time.perf_counter()
        candidate, iterations = _random_restart_attack(
            target, random.Random(seed ^ 0x5A17)
        )
        restart_elapsed += time.perf_counter() - restart_t0
        restart_iterations += iterations
        if verify(target, candidate)[0]:
            attacks["random_restart_two_swap_24x160"]["successes"] += 1
        if verify(target, _adjacent_block_attack(target))[0]:
            attacks["by_hand_consecutive_quartets"]["successes"] += 1

        compact_t0 = time.perf_counter()
        decoded, operations = _reference_decode(target)
        compact_elapsed += time.perf_counter() - compact_t0
        compact_operations.append(operations)
        if decoded is not None and verify(target, decoded)[0]:
            compact_successes += 1
    assert all(row["successes"] == 0 for row in attacks.values()), attacks
    assert compact_successes == len(attack_seeds)
    assert max(compact_operations) <= 5 * ship_params["n"] // 2

    prefix_t0 = time.perf_counter()
    prefix_states, required_states, prefix_checksum = _meet_in_middle_prefix(
        density_inst
    )
    prefix_elapsed = time.perf_counter() - prefix_t0
    assert prefix_states == 1 << 20
    assert required_states == (1 << 31) + (1 << 32)
    assert isinstance(prefix_checksum, int)

    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_sample_hits": density_hits,
        "shipping_sample_total": density_total,
        "shipping_valid_fraction": density_hits / density_total,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_seconds": compact_elapsed,
        "baseline_max_operations": max(compact_operations),
        "baseline_attempts": len(attack_seeds),
        "baseline_attack": "successful residue-bucket reference decoder",
        "mechanical_algorithm": "fixed-cardinality Horowitz--Sahni meet-in-the-middle",
        "mechanical_required_states": required_states,
        "mechanical_prefix_wall_seconds": prefix_elapsed,
        "mechanical_prefix_iterations": prefix_states,
        "failing_restart_wall_seconds": restart_elapsed,
        "failing_restart_iterations": restart_iterations,
    }

    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "residue-bucket decomposition with local equal-pair tests",
            "complexity": "O(n) expected time and O(n) storage",
            "wall_clock_sec": compact_elapsed,
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
        "mechanical_baseline": {
            "name": "fixed-cardinality Horowitz--Sahni meet-in-the-middle",
            "complexity": "O(2^(n/2)) time and storage",
            "required_states": required_states,
            "measured_prefix_states": prefix_states,
            "measured_prefix_wall_sec": prefix_elapsed,
            "completed": False,
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    assert search_space(doubled) > search_space(inst)
    report["G7_scales"] = {
        "pass": True,
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "planted_verifies": True,
    }

    invariance_checks = 0
    real_transform_checks = 0
    original_answer_transform_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(n=16, payload_bits=16, seed=9000 + seed)
        key = canonical_key(base)
        unrelated_keys.append(key)
        rng = random.Random(700_000 + seed)
        permutation = list(range(base["n"]))
        rng.shuffle(permutation)
        scale = rng.randrange(2, 100)
        transforms = [
            _transform_instance(base, permutation=permutation),
            _transform_instance(base, scale=scale),
            _transform_instance(base, permutation=permutation, scale=scale),
        ]
        for transformed in transforms:
            assert canonical_key(transformed) == key
            invariance_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            assert ok, (seed, why)
            real_transform_checks += 1
        ok, why = verify(transforms[1], base["answer"])
        assert ok, (seed, why)
        original_answer_transform_checks += 1
    distinct = len(set(unrelated_keys))
    assert distinct == len(unrelated_keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "original_answer_transform_checks": original_answer_transform_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": len(unrelated_keys),
        "symmetries": "index relabelling, positive scaling, and their composition",
    }

    compact = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact)
    answer_tokens_upper_bound = answer_chars
    answer_elements = len(inst["answer"])
    compact_answer, intended_operations = _reference_decode(inst)
    assert compact_answer is not None and verify(inst, compact_answer)[0]
    within_caps = (
        answer_chars <= 2000
        and answer_tokens_upper_bound <= 500
        and answer_elements <= 256
        and intended_operations <= 300
    )
    # Updated from the script-owned transcripts after the three hardening arms.
    arms = {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    }
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": 0.0,
        "hinted_verdict": "hardened",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens_upper_bound,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "token_measure": "conservative one-token-per-character upper bound",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for name, value in report.items()
        if name.startswith("G") and name[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
