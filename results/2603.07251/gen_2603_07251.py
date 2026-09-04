"""Generator for balanced {+1,-1}-weighted zero-sum witnesses.

The family specializes the definition in Section 1 and the equal-size,
equal-sum interpretation in Observation 3.1 of arXiv:2603.07251v1.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re


DIFFICULTY = {
    "demo": {"n": 8},
    "easy": {"n": 64},
    "medium": {"n": 80},
    "hard": {"n": 96},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Paper basis and exact definition:
  Section 1 of Krishnendu Paul and Shameek Paul, "{+-1}-weighted zero-sum
  constants" (arXiv:2603.07251v1), defines an (A,B)-weighted zero-sum
  sequence (x_i) by weights a_i in A and b_i in B satisfying both
  sum(a_i*x_i)=0 and sum(b_i*a_i)=0 in the underlying module.  This generator
  takes M=R=Z/qZ, A={+1,-1}, B={1}, and uses every listed term.  Because the
  list length n is even and smaller than q, the second congruence forces
  exactly n/2 plus signs and n/2 minus signs.  Observation 3.1 gives the same
  object as two disjoint, equal-length subsequences with equal modular sum.

Hard and easy regimes:
  The paper studies extremal constants, not computational complexity, and it
  contains no NP-hardness, FPT, or search-algorithm claim.  H is supported by
  a direct reduction from PARTITION.  For inputs y_1,...,y_t, use the 2t
  values C+y_1,C,...,C+y_t,C and require t plus signs.  The constant terms
  cancel, so a balanced signed equality exists exactly when a subset of the
  y_i has half their total.  Choose a power-of-two modulus larger than the
  integer range and pad with zero pairs until its exponent equals the even
  list length; this is polynomial in the encoded input size.  Thus the general
  balanced modular search problem is NP-hard, although this does not prove
  average-case hardness of the planted distribution.

  The generated density is n/log_2(q)=1 with q=2**n.  Known dynamic programming
  is pseudo-polynomial in q and meet-in-the-middle remains exponential in n;
  no polynomial-time or closed-form method is known for this regime.  The
  generator stays below the paper's Theorem 3.4 guarantee: that theorem ensures
  some (A,{1})-weighted zero-sum subsequence only after 2k terms when
  2**k >= |M|, which is 2n terms here, whereas the instance lists n terms and
  requires all of them.  It also avoids the collapse at characteristic two in
  Section 4, the odd-modulus length-q reduction to ordinary zero sums in
  Observation 3.5 and Section 5, and the consecutive-subsequence constant
  evaluated for powers of two in Section 6.

Inverse generation and adversaries:
  A uniformly random balanced sign vector is sampled before any residues.  A
  uniformly random pivot coordinate is then solved after all other residues
  are drawn uniformly modulo q.  The pivot is uniform as well: its coefficient
  is a unit and a linear combination containing uniform residues is uniform.
  Rejection uses only whole-instance symmetric events (zeroes, duplicates, or
  all-one-parity lists), so it does not mark the pivot.  Plants and other
  coordinates therefore have the same one-coordinate distribution.

  The adversary panel tests a per-value magnitude split (outlier attack), a
  largest-first greedy number partition, and random balanced restarts followed
  by improving plus/minus swaps.  Difficulty comes from density and dimension,
  not from a separate decoy distribution.  Stronger lattice, SAT/ILP,
  meet-in-the-middle, and generalized-birthday attacks remain caveats.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 300_000


def _check_parameters(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")


def make_instance(n, seed=0, **params) -> dict:
    """Sample a balanced sign witness first, then build residues around it.

    ``n`` is the number of listed residues and the modulus bit length.  Hence
    q=2**n, while the balanced-partition search space grows as C(n,n/2).
    """
    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    _check_parameters(n)
    rng = random.Random(seed)
    modulus = 1 << n
    half = n // 2

    # G: sample the complete witness before sampling any problem values.
    plus = set(rng.sample(range(n), half))
    signs = [1 if i in plus else -1 for i in range(n)]
    pivot = rng.randrange(n)

    # For fixed signs, this samples uniformly from the planted hyperplane.
    # Redraw only on properties invariant under permutation of coordinates.
    for _ in range(256):
        values = [rng.randrange(modulus) for _ in range(n)]
        other = sum(signs[i] * values[i] for i in range(n) if i != pivot)
        values[pivot] = (-signs[pivot] * other) % modulus
        if 0 in values or len(set(values)) != n:
            continue
        if all((x & 1) == (values[0] & 1) for x in values):
            continue
        break
    else:
        raise RuntimeError("could not draw a nondegenerate planted instance")

    plus_answer = sorted(i + 1 for i in plus)
    minus_answer = sorted(i + 1 for i in range(n) if i not in plus)
    return {
        "family": "balanced_pm1_weighted_zero_sum",
        "n": n,
        "modulus": modulus,
        "A": [1, modulus - 1],
        "B": [1],
        "sequence": values,
        "answer": {"plus": plus_answer, "minus": minus_answer},
    }


def render(inst) -> str:
    """Render a complete, unambiguous problem statement and output contract."""
    n = inst["n"]
    q = inst["modulus"]
    rows = "\n".join(f"{i}: {x}" for i, x in enumerate(inst["sequence"], 1))
    return f"""Balanced {{+1,-1}}-weighted zero-sum witness

All arithmetic below is in the ring Z/{q}Z: reduce every integer modulo {q},
using residue representatives 0 through {q - 1}.  The input is this ordered
sequence of {n} residues, labelled by 1-based positions:

{rows}

A subsequence normally chooses distinct positions while retaining their input
order.  In this problem the subsequence must use ALL {n} positions.  At every
position i choose a weight a_i from A={{1,{q - 1}}}, where residue {q - 1}
means -1 modulo {q}.  The second weight is forced to b_i=1 because B={{1}}.

Find weights satisfying both congruences from the definition:

  sum(a_i*x_i for i=1..{n}) = 0 (mod {q})
  sum(b_i*a_i for i=1..{n}) = 0 (mod {q}).

Report the weights as two groups of positions.  "plus" must contain exactly
{n // 2} positions assigned +1; "minus" must contain exactly {n // 2}
positions assigned -1.  The lists must be disjoint and together contain every
integer position from 1 through {n}.  Positions are 1-indexed, list order does
not matter, and repeated positions are forbidden.  These shape rules make the
second congruence hold; the first is equivalently

  sum(x_i for i in plus) - sum(x_i for i in minus) = 0 (mod {q}).

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "plus" and "minus", each mapped to a JSON list of integers.
Syntax example for a four-position instance:
<answer>{{"plus":[1,3],"minus":[2,4]}}</answer>
Output nothing else inside the tags."""


def _strip_optional_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        first_newline = value.find("\n")
        if first_newline < 0:
            return ""
        value = value[first_newline + 1 :]
        if value.rstrip().endswith("```"):
            value = value.rstrip()[:-3]
    return value.strip()


def _parsed_shape(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"plus", "minus"}:
        return False
    for key in ("plus", "minus"):
        if not isinstance(value[key], list):
            return False
        if any(isinstance(x, bool) or not isinstance(x, int) for x in value[key]):
            return False
    return True


def parse_answer(text) -> object | None:
    """Extract the last well-formed tagged JSON witness; never raise."""
    if not isinstance(text, str):
        return None
    try:
        blocks = _ANSWER_RE.findall(text)
        for block in reversed(blocks):
            try:
                value = json.loads(_strip_optional_fence(block))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if _parsed_shape(value):
                return value
    except Exception:
        return None
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any valid witness using public instance data only."""
    if not isinstance(answer, dict) or set(answer) != {"plus", "minus"}:
        return False, "answer must be an object with exactly plus and minus lists"
    plus = answer["plus"]
    minus = answer["minus"]
    if not isinstance(plus, list) or not isinstance(minus, list):
        return False, "plus and minus must both be lists"

    n = inst["n"]
    half = n // 2
    if len(plus) != half or len(minus) != half:
        return False, f"wrong group sizes: each list must contain exactly {half} indices"
    joined = plus + minus
    if any(isinstance(i, bool) or not isinstance(i, int) for i in joined):
        return False, "every index must be an integer"
    if any(i < 1 or i > n for i in joined):
        return False, f"index out of range: valid positions are 1 through {n}"
    if len(set(joined)) != len(joined):
        return False, "duplicate index: positions may not repeat or appear in both groups"
    if set(joined) != set(range(1, n + 1)):
        return False, "the two groups do not cover every input position"

    q = inst["modulus"]
    xs = inst["sequence"]
    first = (
        sum(xs[i - 1] for i in plus)
        + sum((q - 1) * xs[i - 1] for i in minus)
    ) % q
    if first != 0:
        return False, f"first weighted sum is {first}, not 0 modulo {q}"
    second = (len(plus) + (q - 1) * len(minus)) % q
    if second != 0:
        return False, f"second weighted sum is {second}, not 0 modulo {q}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample a complete balanced partition, the solver-aware prior."""
    n = inst["n"]
    plus = sorted(i + 1 for i in rng.sample(range(n), n // 2))
    plus_set = set(plus)
    minus = [i for i in range(1, n + 1) if i not in plus_set]
    return {"plus": plus, "minus": minus}


def search_space(inst) -> int | None:
    """Return the number of statement-compliant balanced sign assignments."""
    return math.comb(inst["n"], inst["n"] // 2)


def enumerate_all(inst) -> int | None:
    """Count all valid answers exactly when at most 300,000 need inspection."""
    total = search_space(inst)
    if total is None or total > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    q = inst["modulus"]
    xs = inst["sequence"]
    all_sum = sum(xs) % q
    hits = 0
    for plus in itertools.combinations(range(n), n // 2):
        plus_sum = sum(xs[i] for i in plus) % q
        if (2 * plus_sum - all_sum) % q == 0:
            hits += 1
    return hits


def _v2(value: int) -> int:
    """2-adic valuation of a positive nonzero integer."""
    return (value & -value).bit_length() - 1


def canonical_key(inst) -> str:
    """Canonicalize input order and affine relabellings of the cyclic group.

    A common translation and multiplication by any odd unit preserve balanced
    signed sums.  This function normalizes exactly over those transformations,
    including the degenerate case in which all differences share powers of two.
    """
    q = inst["modulus"]
    xs = tuple(inst["sequence"])
    if len(set(xs)) == 1:
        normalized = (0,) * len(xs)
        valuation = q.bit_length() - 1
    else:
        diffs = [
            (xs[i] - xs[j]) % q
            for i in range(len(xs))
            for j in range(len(xs))
            if xs[i] != xs[j]
        ]
        valuation = min(_v2(d) for d in diffs)
        reduced_q = q >> valuation
        candidates = []
        for i in range(len(xs)):
            for j in range(len(xs)):
                delta = (xs[i] - xs[j]) % q
                if delta and _v2(delta) == valuation:
                    unit = pow(delta >> valuation, -1, reduced_q)
                    form = tuple(
                        sorted(
                            (((x - xs[j]) % q) >> valuation) * unit % reduced_q
                            for x in xs
                        )
                    )
                    candidates.append(form)
        normalized = min(candidates)
    payload = json.dumps(
        [inst["family"], q, inst["n"], valuation, normalized],
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params) -> dict | None:
    """Increase dimension and modulus bit length together by sixteen."""
    if not isinstance(params, dict) or set(params) != {"n"}:
        return None
    n = params["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        return None
    return {"n": n + (16 if n % 2 == 0 else 17)}


def _magnitude_attack(inst) -> dict:
    """Assign signs solely from each residue's magnitude rank."""
    order = sorted(range(inst["n"]), key=lambda i: (inst["sequence"][i], i))
    half = inst["n"] // 2
    return {
        "plus": sorted(i + 1 for i in order[:half]),
        "minus": sorted(i + 1 for i in order[half:]),
    }


def _greedy_attack(inst) -> dict:
    """Largest-first greedy balanced number partitioning."""
    order = sorted(range(inst["n"]), key=lambda i: inst["sequence"][i], reverse=True)
    plus: list[int] = []
    minus: list[int] = []
    plus_sum = 0
    minus_sum = 0
    half = inst["n"] // 2
    for i in order:
        if len(plus) == half:
            target = minus
        elif len(minus) == half:
            target = plus
        elif plus_sum <= minus_sum:
            target = plus
        else:
            target = minus
        target.append(i + 1)
        if target is plus:
            plus_sum += inst["sequence"][i]
        else:
            minus_sum += inst["sequence"][i]
    return {"plus": sorted(plus), "minus": sorted(minus)}


def _residue_score(value: int, modulus: int) -> int:
    value %= modulus
    return min(value, modulus - value)


def _random_restart_attack(inst, rng, restarts: int = 24) -> dict:
    """Use random balanced starts and best improving plus/minus swaps."""
    q = inst["modulus"]
    xs = inst["sequence"]
    last = random_candidate(inst, rng)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        plus = {i - 1 for i in candidate["plus"]}
        minus = set(range(inst["n"])) - plus
        residue = (sum(xs[i] for i in plus) - sum(xs[i] for i in minus)) % q
        if residue == 0:
            return candidate
        while True:
            current = _residue_score(residue, q)
            best = None
            best_score = current
            for p in plus:
                for m in minus:
                    new_residue = (residue + 2 * (xs[m] - xs[p])) % q
                    score = _residue_score(new_residue, q)
                    if score < best_score:
                        best_score = score
                        best = (p, m, new_residue)
            if best is None:
                break
            p, m, residue = best
            plus.remove(p)
            minus.remove(m)
            plus.add(m)
            minus.add(p)
            if residue == 0:
                return {
                    "plus": sorted(i + 1 for i in plus),
                    "minus": sorted(i + 1 for i in minus),
                }
        last = {
            "plus": sorted(i + 1 for i in plus),
            "minus": sorted(i + 1 for i in minus),
        }
    return last


def selftest() -> dict:
    """Run mandatory G1-G7 gates and return all measured evidence."""
    report: dict[str, object] = {
        "family": "balanced_pm1_weighted_zero_sum",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: test every named preset with several independent deterministic seeds.
    g1_failures = []
    g1_count = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 42):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_count += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "tested": g1_count,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260831, **ship_params)
    planted = inst["answer"]

    # G2: five corruptions must be rejected through five distinct paths.
    corruptions = {
        "drop_one": {
            "plus": planted["plus"][:-1],
            "minus": list(planted["minus"]),
        },
        "empty": {},
    }

    swapped = None
    for p in planted["plus"]:
        for m in planted["minus"]:
            trial = {
                "plus": sorted(m if x == p else x for x in planted["plus"]),
                "minus": sorted(p if x == m else x for x in planted["minus"]),
            }
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions["swap_one"] = swapped if swapped is not None else planted

    duplicate = {"plus": list(planted["plus"]), "minus": list(planted["minus"])}
    duplicate["plus"][-1] = duplicate["plus"][0]
    corruptions["duplicate"] = duplicate

    out_of_range = {"plus": list(planted["plus"]), "minus": list(planted["minus"])}
    out_of_range["plus"][0] = inst["n"] + 1
    corruptions["out_of_range"] = out_of_range

    g2_results = {}
    reasons = []
    for name, answer in corruptions.items():
        ok, reason = verify(inst, answer)
        g2_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in g2_results.values())
        and len(set(reasons)) == len(g2_results),
        "distinct_reasons": len(set(reasons)),
        "cases": g2_results,
    }

    # G3: realistic prose, Markdown, tags, JSON, and whitespace coexist.
    encoded = json.dumps(planted, separators=(",", ":"))
    model_style = (
        "I checked both congruences.\n```json\n<answer>\n"
        f"{encoded}\n</answer>\n```\nDone."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("not an answer") is None,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4: sample complete balanced partitions, not arbitrary noisy JSON/lists.
    guess_rng = random.Random(0x260307251)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    rate = hits / trials
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": trials,
        "rate": rate,
        "threshold": 1e-6,
        "prior": "uniform over all balanced partitions of all n positions",
        "shape_aware_space": search_space(inst),
    }

    # G5: use the largest complete enumeration under the fixed work cap.
    sparse_inst = make_instance(n=20, seed=314159)
    exact = enumerate_all(sparse_inst)
    space = search_space(sparse_inst)
    fraction = None if exact is None else exact / space
    report["G5_sparse"] = {
        "pass": exact is not None and fraction is not None and fraction < 1e-4,
        "probe": {"n": 20, "seed": 314159},
        "valid_answers": exact,
        "candidate_space": space,
        "solution_fraction": fraction,
        "enumeration_cap": _ENUMERATION_CAP,
    }

    # G6: each cheap construction gets one attempt on each of eight seeds.
    attack_seeds = tuple(range(700, 708))
    attacks = {
        "magnitude_outlier_split": lambda x, r: _magnitude_attack(x),
        "largest_first_greedy": lambda x, r: _greedy_attack(x),
        "random_restart_one_swap": lambda x, r: _random_restart_attack(x, r),
    }
    attack_report = {}
    for name, attack in attacks.items():
        solved = []
        failures = []
        for seed in attack_seeds:
            attack_inst = make_instance(seed=seed, **ship_params)
            candidate = attack(attack_inst, random.Random(seed ^ 0xA5A5A5A5))
            ok, reason = verify(attack_inst, candidate)
            if ok:
                solved.append(seed)
            else:
                failures.append({"seed": seed, "reason": reason})
        attack_report[name] = {
            "pass": not solved,
            "solved": len(solved),
            "attempted": len(attack_seeds),
            "solved_seeds": solved,
            "failed_results": failures,
        }
    report["G6_adversary_panel"] = {
        "pass": all(x["pass"] for x in attack_report.values()),
        "seeds_per_attack": len(attack_seeds),
        "attacks": attack_report,
    }

    # G7: doubling n doubles modulus bit length and grows the search space.
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=99, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    base_space = search_space(inst)
    doubled_space = search_space(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_space > base_space,
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_modulus_bits": inst["modulus"].bit_length() - 1,
        "doubled_modulus_bits": doubled["modulus"].bit_length() - 1,
        "base_search_space": base_space,
        "doubled_search_space": doubled_space,
        "doubled_planted_verify": doubled_ok,
        "verify_reason": doubled_reason,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
