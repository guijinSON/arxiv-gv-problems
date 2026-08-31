"""Generator for balanced doubly-weighted zero-sum witnesses.

The family is derived from the definition in Section 1 of arXiv:2311.00090v4.
It deliberately does not use the broad weight sets for which Sections 3, 5,
and 7 give short direct constructions.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re


DIFFICULTY = {
    "easy": {"n": 64},
    "medium": {"n": 80},
    "hard": {"n": 96},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Paper basis and definition:
  The exact definition is Section 1 of Paul and Paul, "Doubly-weighted
  zero-sum constants", arXiv:2311.00090v4.  For a sequence (x_i) in Z/qZ,
  an (A,B)-weighted zero-sum witness supplies a_i in A and b_i in B with
  sum(a_i*x_i)=0 and sum(b_i*a_i)=0 in Z/qZ.  This generator fixes
  A={1,-1}, B={1}, uses every listed term, and prescribes equally many +1
  and -1 weights.  Thus the second congruence is satisfied exactly by shape,
  while the first is a balanced modular partition.

Hard and easy regimes:
  The paper is structural number theory, not a computational-complexity
  paper, and it does not claim NP-hardness.  H is instead supported by a
  direct reduction from PARTITION.  Given y_1,...,y_t with total W, form the
  2t integers C+y_1,C,...,C+y_t,C, require t plus signs and t minus signs,
  and choose a modulus larger than twice their total.  A valid witness exists
  exactly when a subset of the y_i sums to W/2.  The generated regime keeps
  n proportional to log_2(q) (in fact q=2^n), the critical-density region in
  which neither pseudo-polynomial dynamic programming nor low-density
  shortcuts give a polynomial method.

  Easy regimes explicitly avoided are: Section 1, Observation 1.2 and Remark
  1.4 (ordinary zero sums of length divisible by the characteristic, and the
  2q-1 existence bound); Section 3, Observations 3.1-3.2 and Theorems 3.3-3.4
  (A=Z'_q gives a witness in at most three arbitrary or four consecutive
  terms); Section 5, Observation 5.1 and Theorems 5.4-5.7 (B=Z'_q largely
  collapses the doubly-weighted problem to the singly-weighted one); and
  Section 7, Theorems 7.2-7.3 (again A=Z'_q gives constants at most four).
  Here A has only two weights, B is the singleton {1}, n is tiny compared
  with q, and the required length is n rather than q.

Inverse generation and attacks:
  The balanced sign vector is sampled first.  A uniformly chosen coordinate
  is then solved from the first congruence after all other residues are drawn
  uniformly.  Because adding/subtracting uniform residues modulo q is uniform,
  the solved coordinate has the same marginal distribution as every other
  coordinate.  The generator rejects only symmetric whole-instance events
  (zero, duplicate, or one-parity sequences), so it does not mark the pivot.
  The adversary panel tests a magnitude outlier split, a largest-first greedy
  balanced partition, and random-restart one-swap local search.  Plants and
  non-pivot coordinates use the same residue distribution; there are no
  specially distributed decoy values.
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

    ``n`` is both the number of listed residues and the number of selected
    terms.  The modulus is 2**n, so its bit length and the balanced-partition
    search space both grow exponentially with n.
    """
    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    _check_parameters(n)
    rng = random.Random(seed)
    modulus = 1 << n
    half = n // 2

    # G: sample the complete witness before any instance value.
    plus = set(rng.sample(range(n), half))
    signs = [1 if i in plus else -1 for i in range(n)]
    pivot = rng.randrange(n)

    # Drawing is repeated only on properties symmetric in all coordinates.
    # The pivot itself is uniformly random, and its solved value is uniform
    # modulo ``modulus`` because the other sum contains uniform residues.
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
        "family": "balanced_doubly_weighted_zero_sum",
        "n": n,
        "modulus": modulus,
        "A": [1, modulus - 1],
        "B": [1],
        "sequence": values,
        "answer": {"plus": plus_answer, "minus": minus_answer},
    }


def render(inst) -> str:
    """Render a complete, unambiguous statement and output contract."""
    n = inst["n"]
    q = inst["modulus"]
    rows = "\n".join(f"{i}: {x}" for i, x in enumerate(inst["sequence"], 1))
    return f"""Balanced doubly-weighted zero-sum witness

All arithmetic below is in the ring Z/{q}Z: reduce an integer modulo {q},
with residue representatives 0 through {q - 1}.  The input is an ordered
sequence of {n} residues, labelled by 1-based positions:

{rows}

A subsequence means terms chosen at distinct positions while retaining their
original order.  In this instance the subsequence must use ALL {n} positions.
For every chosen position i, choose a first weight a_i from
A = {{1, {q - 1}}}; the residue {q - 1} means -1 modulo {q}.  The second
weight is forced to b_i=1 because B={{1}}.

Find weights satisfying both defining congruences:

  sum(a_i*x_i for i=1..{n}) = 0 (mod {q})
  sum(b_i*a_i for i=1..{n}) = 0 (mod {q}).

Report the weights as two groups of positions.  "plus" contains exactly
{n // 2} positions given weight +1; "minus" contains exactly {n // 2}
positions given weight -1.  The two lists must be disjoint and together must
be exactly the positions 1 through {n}.  List order does not matter.  Repeats
are forbidden.  These shape rules make the second congruence explicit; the
first congruence is equivalently
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
    except Exception:  # A parser used for grading must fail closed on all garbage.
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
    second = (sum(1 for _ in plus) + sum(q - 1 for _ in minus)) % q
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
    """Count balanced sign assignments (all statement-implied shape enforced)."""
    return math.comb(inst["n"], inst["n"] // 2)


def enumerate_all(inst) -> int | None:
    """Brute-force the exact answer count when at most 300,000 candidates."""
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
    return (value & -value).bit_length() - 1


def canonical_key(inst) -> str:
    """Canonicalize reordering and every affine unit relabelling of Z/(2^n)."""
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
                        sorted((((x - xs[j]) % q) >> valuation) * unit % reduced_q for x in xs)
                    )
                    candidates.append(form)
        normalized = min(candidates)
    payload = json.dumps(
        [inst["family"], q, inst["n"], valuation, normalized],
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params) -> dict | None:
    """Increase the balanced-partition dimension and modulus bit length together."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = params["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        return None
    return {"n": n + (16 if n % 2 == 0 else 17)}


def _magnitude_attack(inst) -> dict:
    order = sorted(range(inst["n"]), key=lambda i: (inst["sequence"][i], i))
    half = inst["n"] // 2
    return {
        "plus": sorted(i + 1 for i in order[:half]),
        "minus": sorted(i + 1 for i in order[half:]),
    }


def _greedy_attack(inst) -> dict:
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
    """Random balanced starts followed by best improving plus/minus swaps."""
    q = inst["modulus"]
    xs = inst["sequence"]
    last = random_candidate(inst, rng)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        plus = set(i - 1 for i in candidate["plus"])
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
    """Run mandatory G1-G7 gates and return all measurements."""
    report: dict[str, object] = {
        "family": "balanced_doubly_weighted_zero_sum",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, several seeds.
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

    # G2: five different corruptions must reach five different rejection paths.
    corruptions = {}
    dropped = {"plus": planted["plus"][:-1], "minus": list(planted["minus"])}
    corruptions["drop_one"] = dropped

    swapped = None
    for p in planted["plus"]:
        for m in planted["minus"]:
            trial = {
                "plus": sorted([m if x == p else x for x in planted["plus"]]),
                "minus": sorted([p if x == m else x for x in planted["minus"]]),
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
    corruptions["empty"] = {}
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
        "pass": all(x["rejected"] for x in g2_results.values()) and len(set(reasons)) == 5,
        "distinct_reasons": len(set(reasons)),
        "cases": g2_results,
    }

    # G3: prose, a Markdown fence, tags, JSON, and whitespace all coexist.
    encoded = json.dumps(planted, separators=(",", ":"))
    model_style = f"I checked both congruences.\n```json\n<answer>\n{encoded}\n</answer>\n```\nDone."
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4: uniform over balanced partitions, not arbitrary lists or sign strings.
    guess_rng = random.Random(0x231100090)
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

    # G5: the largest exactly enumerable planted probe below the work cap.
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

    # G6: each cheap construction gets one answer per seed; none may solve.
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

    # G7: doubling n doubles modulus bit length and squares the search exponent.
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
