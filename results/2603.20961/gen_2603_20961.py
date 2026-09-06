"""Problem generator for arXiv:2603.20961 (Graham/Alspach sequencing).

The only public dependency of this module is the Python standard library.  An
instance gives a subset of a cyclic group and asks for an ordering whose partial
sums are nonzero (except where the paper permits the final sum to be zero) and
pairwise distinct.  This generator uses only instances with nonzero total sum,
so the final partial sum is nonzero in every possible ordering as well.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    # The demo rung is intentionally readable and is expected to be defeated by
    # the oracle loop.  It exists for examples and exact enumeration.
    "demo": {"n": 6, "slack": 1},
    # In the crowded rungs only a few nonzero residues are absent.  A local
    # greedy choice is therefore liable to strand the final few elements.
    "easy": {"n": 120, "slack": 6},
    "medium": {"n": 144, "slack": 8},
    "hard": {"n": 168, "slack": 8},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Section 1 of Costa--Della Fiore--Fontana--Vena fixes the exact definition: an
ordering of a set A of distinct nonzero elements is valid when its partial sums
are pairwise distinct, and it is a sequencing when all nonfinal partial sums are
also nonzero.  Theorems 1.4--1.6 prove universal existence only for |A| <= 20,
or 22/23 under extra hypotheses.  Section 3 describes the exponential BFS used
for those fixed sizes; its stated O(m^2 k^3) figure is per search-tree node, not
a polynomial bound for the whole variable-k search.  The rectification regime
quoted in Theorem 1.3 is sparse relative to the prime and is deliberately
avoided here: n grows and the prime modulus has only a small number of unused
residues.

Inverse generation samples the witnessing order first.  Starting at zero, it
chooses unused nonzero modular increments while also forbidding a repeated
endpoint; the unordered increment set is the problem.  There is no decoy class:
every displayed element is drawn by the same sequential rule, and the input is
independently shuffled after planting.  The outlier panel tries presentation
order, cyclic magnitude, and an additive-frequency statistic in both directions.
The greedy panel takes the first locally legal element.  The restart panel makes
128 independent locally legal random walks per instance.  Shipping crowding was
chosen only after all three attacks failed on eight independent seeds.  These
are empirical defenses, not a proof of average-case computational hardness.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_prime(x: int) -> bool:
    if x < 2:
        return False
    if x % 2 == 0:
        return x == 2
    d = 3
    while d * d <= x:
        if x % d == 0:
            return False
        d += 2
    return True


def _next_prime(x: int) -> int:
    x = max(2, x)
    while not _is_prime(x):
        x += 1
    return x


def _construct_order(n: int, modulus: int, rng: random.Random) -> list[int]:
    """Sample an order before constructing the unordered problem around it."""
    # Whole-path restarts preserve the simple sampling rule.  At the shipped
    # densities the median is small; 20,000 is a deterministic safety cap.
    for _restart in range(20_000):
        unused = set(range(1, modulus))
        used_sums = {0}
        partial = 0
        answer: list[int] = []
        for _position in range(n):
            choices = [
                x for x in unused
                if (partial + x) % modulus not in used_sums
            ]
            if not choices:
                break
            x = choices[rng.randrange(len(choices))]
            unused.remove(x)
            partial = (partial + x) % modulus
            used_sums.add(partial)
            answer.append(x)
        if len(answer) == n:
            return answer
    raise RuntimeError(
        "construction restart cap reached; use a larger slack parameter"
    )


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Sample a valid ordering first, then forget its order to form the input.

    ``slack`` is a lower bound on how many nonzero residues are not selected
    before adjustment to the next prime.  Smaller slack means more crowding.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    slack = params.pop("slack", max(6, n // 20))
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(slack, bool) or not isinstance(slack, int) or slack < 1:
        raise ValueError("slack must be a positive integer")

    modulus = _next_prime(n + slack + 1)
    rng = random.Random(seed)
    answer = _construct_order(n, modulus, rng)
    elements = list(answer)
    rng.shuffle(elements)
    return {
        "family": "cyclic_distinct_partial_sums",
        "n": n,
        "modulus": modulus,
        "elements": elements,
        "answer": answer,
        "slack": slack,
        "seed": seed,
    }


def render(inst: dict) -> str:
    """Return the complete, standalone statement shown to a solver."""
    n = inst["n"]
    q = inst["modulus"]
    values = ", ".join(str(x) for x in inst["elements"])
    return f"""Cyclic distinct-partial-sums problem

Work in the cyclic additive group Z/{q}Z.  Its elements are the integer residues
0, 1, ..., {q - 1}; addition and every sum below are reduced modulo {q}.

The following is an unordered set A of {n} distinct nonzero residues:
A = [{values}]

Find a sequencing of A: output an ordered list a_1, ..., a_{n} that uses every
member of A exactly once, with no repetitions.  For each 1-indexed position i,
define the inclusive partial sum p_i = (a_1 + ... + a_i) mod {q}.  The residues
p_1, ..., p_{n} must be pairwise distinct, and p_i must be nonzero for every
1 <= i < {n}.  (The total sum p_{n} is fixed by A and is nonzero in this
instance.)  Order matters.  Only the displayed canonical representatives
0 through {q - 1} may be used.

Give your final answer inside <answer></answer> tags, as exactly {n} base-10
integers separated by commas, in the desired order.  Do not put brackets around
the list.  Example of syntax only: <answer>3, 17, 42</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the tagged comma-list, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match is None:
        return None
    body = match.group(1).strip()
    # Be liberal about a model wrapping just the contents in a code fence or
    # copying JSON brackets despite the explicit output instruction.
    body = re.sub(r"^```(?:json|text|python)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    body = body.strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return None
    pieces = body.split(",")
    if not pieces or any(re.fullmatch(r"[+-]?\d+", p.strip()) is None for p in pieces):
        return None
    try:
        return [int(p.strip(), 10) for p in pieces]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any proposed sequencing; the planted answer is never consulted."""
    if not isinstance(answer, list):
        return False, "malformed answer: expected a list of integers"
    if not answer:
        return False, "empty answer"
    n = inst["n"]
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "non-integer entry"
    modulus = inst["modulus"]
    if any(x < 0 or x >= modulus for x in answer):
        return False, f"entry outside the canonical range 0..{modulus - 1}"
    if len(set(answer)) != n:
        return False, "repeated entry"
    if set(answer) != set(inst["elements"]):
        return False, "answer is not a permutation of the given set"

    partial = 0
    seen: dict[int, int] = {}
    for position, x in enumerate(answer, 1):
        partial = (partial + x) % modulus
        if position < n and partial == 0:
            return False, f"partial sum p_{position} is zero"
        if partial in seen:
            return (
                False,
                f"partial sums p_{seen[partial]} and p_{position} both equal {partial}",
            )
        seen[partial] = position
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the structure-aware space: all permutations of A."""
    candidate = list(inst["elements"])
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """All shape-correct candidates already obey the obvious permutation rule."""
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count all sequencings by pruned brute force, with a hard work cap."""
    n = inst["n"]
    if n > 10:
        return None
    modulus = inst["modulus"]
    values = tuple(inst["elements"])
    node_cap = 5_000_000
    nodes = 0
    aborted = False

    def visit(remaining: tuple[int, ...], partial: int, seen: frozenset[int]) -> int:
        nonlocal nodes, aborted
        nodes += 1
        if nodes > node_cap:
            aborted = True
            return 0
        if not remaining:
            return 1
        total = 0
        final_move = len(remaining) == 1
        for i, x in enumerate(remaining):
            nxt = (partial + x) % modulus
            if nxt in seen or (not final_move and nxt == 0):
                continue
            total += visit(remaining[:i] + remaining[i + 1 :], nxt, seen | {nxt})
            if aborted:
                return 0
        return total

    count = visit(values, 0, frozenset())
    return None if aborted else count


def canonical_key(inst: dict) -> str:
    """Canonicalize input order and every automorphism x -> u*x of Z/qZ.

    The modulus is prime in generated instances.  Normalizing each possible
    member to 1 enumerates the full multiplicative automorphism orbit without
    relying on the seed, planted order, or rendered text.
    """
    modulus = inst["modulus"]
    values = tuple(sorted(inst["elements"]))
    if not values or any(x <= 0 or x >= modulus for x in values):
        raise ValueError("canonical_key expects nonzero canonical residues")
    forms = []
    for anchor in values:
        inverse = pow(anchor, -1, modulus)
        forms.append(tuple(sorted((inverse * x) % modulus for x in values)))
    normal = min(forms)
    payload = f"{modulus}|" + ",".join(map(str, normal))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase length and crowding while keeping generation reliable."""
    n = int(params.get("n", 120))
    slack = int(params.get("slack", max(6, n // 20)))
    if n >= 320:
        return None
    # Search cost grows factorially with n.  Slack grows more slowly than n, so
    # the fraction of unused residues does not increase along this escalation.
    return {"n": math.ceil(n * 1.2), "slack": max(6, math.ceil(slack * 1.1))}


def _locally_greedy(inst: dict, order_key) -> list[int] | None:
    modulus = inst["modulus"]
    remaining = list(inst["elements"])
    partial = 0
    seen = {0}
    result: list[int] = []
    while remaining:
        legal = [x for x in remaining if (partial + x) % modulus not in seen]
        if not legal:
            return None
        x = min(legal, key=order_key)
        result.append(x)
        remaining.remove(x)
        partial = (partial + x) % modulus
        seen.add(partial)
    return result


def _random_restart_attack(inst: dict, rng: random.Random, restarts: int) -> bool:
    modulus = inst["modulus"]
    for _ in range(restarts):
        remaining = list(inst["elements"])
        partial = 0
        seen = {0}
        result: list[int] = []
        while remaining:
            legal = [x for x in remaining if (partial + x) % modulus not in seen]
            if not legal:
                break
            x = legal[rng.randrange(len(legal))]
            remaining.remove(x)
            result.append(x)
            partial = (partial + x) % modulus
            seen.add(partial)
        if not remaining and verify(inst, result)[0]:
            return True
    return False


def _find_invalid_swap(inst: dict, answer: list[int]) -> list[int] | None:
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            changed = list(answer)
            changed[i], changed[j] = changed[j], changed[i]
            if not verify(inst, changed)[0]:
                return changed
    return None


def _transformed(inst: dict, multiplier: int, reverse_input: bool) -> dict:
    modulus = inst["modulus"]
    elements = [(multiplier * x) % modulus for x in inst["elements"]]
    if reverse_input:
        elements.reverse()
    return {
        "family": inst["family"],
        "n": inst["n"],
        "modulus": modulus,
        "elements": elements,
        "answer": [(multiplier * x) % modulus for x in inst["answer"]],
        "slack": inst.get("slack"),
        "seed": inst.get("seed"),
    }


def selftest() -> dict:
    """Run mandatory gates and return their measured, JSON-ready report."""
    report: dict[str, Any] = {
        "paper": "2603.20961",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, multiple unrelated seeds.
    g1_checks = 0
    g1_failures: list[str] = []
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 97):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{name}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=20260321, **shipping)

    # G2: five corruption classes, and five distinct diagnostic reasons.
    planted = list(base["answer"])
    bad_swap = _find_invalid_swap(base, planted)
    corruptions: dict[str, object] = {
        "drop_one": planted[:-1],
        "swap_two": bad_swap,
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": [base["modulus"]] + planted[1:],
    }
    g2_reasons: dict[str, str] = {}
    g2_ok = bad_swap is not None
    for label, candidate in corruptions.items():
        ok, why = verify(base, candidate)
        g2_reasons[label] = why
        g2_ok = g2_ok and not ok
    g2_ok = g2_ok and len(set(g2_reasons.values())) == len(g2_reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "reasons": g2_reasons,
        "distinct_reasons": len(set(g2_reasons.values())),
    }

    # G3: prose, a Markdown fence, whitespace, and optional copied brackets.
    answer_csv = ",\n  ".join(map(str, planted))
    realistic = (
        "I checked the modular partial sums.\n```text\n"
        f"<answer>[\n  {answer_csv}\n]</answer>\n```\n"
        "That is my final ordering."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("unrelated garbage") is None,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("unrelated garbage") is None,
    }

    # G4: uniform over all permutations, not over arbitrary residue vectors.
    guess_rng = random.Random(0x260320961)
    total_guesses = 200_000
    hits = 0
    for _ in range(total_guesses):
        candidate = random_candidate(base, guess_rng)
        if verify(base, candidate)[0]:
            hits += 1
    probability = hits / total_guesses
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total_guesses,
        "measured_probability": probability,
        "prior": "uniform over permutations of the given set",
        "naive_space_n_factorial": str(search_space(base)),
    }

    # G5: a crowded small instance is exhaustively countable.
    small = make_instance(n=9, slack=1, seed=17)
    exact = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if exact is None else exact / small_space
    report["G5_sparse"] = {
        "pass": exact is not None and fraction is not None and fraction < 0.01,
        "n": small["n"],
        "modulus": small["modulus"],
        "valid_answers": exact,
        "candidate_space": small_space,
        "fraction": fraction,
    }

    # G6: attacks run on eight instances disjoint from earlier checks.
    attack_seeds = list(range(3101, 3109))
    attack_successes = {"outlier": 0, "greedy": 0, "random_restart": 0}
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping)
        q = inst["modulus"]
        aset = set(inst["elements"])

        def frequency(x: int) -> tuple[int, int]:
            score = sum(
                1 for y in aset
                if y != x and ((x + y) % q in aset or (x - y) % q in aset)
            )
            return score, x

        outlier_orders = [
            list(inst["elements"]),
            list(reversed(inst["elements"])),
            sorted(aset, key=lambda x: (min(x, q - x), x)),
            sorted(aset, key=lambda x: (min(x, q - x), x), reverse=True),
            sorted(aset, key=frequency),
            sorted(aset, key=frequency, reverse=True),
        ]
        if any(verify(inst, candidate)[0] for candidate in outlier_orders):
            attack_successes["outlier"] += 1

        greedy = _locally_greedy(inst, lambda x: inst["elements"].index(x))
        if greedy is not None and verify(inst, greedy)[0]:
            attack_successes["greedy"] += 1

        if _random_restart_attack(inst, random.Random(seed ^ 0xA5A5), 128):
            attack_successes["random_restart"] += 1

    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attack_successes.values()),
        "seeds": len(attack_seeds),
        "successes": attack_successes,
        "outlier_variants_per_seed": 6,
        "random_restarts_per_seed": 128,
    }

    # G7: double both size and slack to preserve crowding asymptotically.
    doubled_params = {
        "n": shipping["n"] * 2,
        "slack": shipping["slack"] * 2,
    }
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(base),
        "base_n": base["n"],
        "doubled_n": doubled["n"],
        "base_modulus": base["modulus"],
        "doubled_modulus": doubled["modulus"],
        "planted_verify": doubled_why,
    }

    # G8: all cyclic automorphisms, input reversal, and their compositions.
    invariant_checks = 0
    real_transform_checks = 0
    input_generator_checks = 0
    keys: list[str] = []
    g8_failures: list[str] = []
    for seed in range(20_001, 20_021):
        inst = make_instance(seed=seed, **shipping)
        original_key = canonical_key(inst)
        keys.append(original_key)
        q = inst["modulus"]
        for multiplier in range(1, q):
            for reverse_input in (False, True):
                changed = _transformed(inst, multiplier, reverse_input)
                invariant_checks += 1
                if canonical_key(changed) != original_key:
                    g8_failures.append(
                        f"seed={seed}, multiplier={multiplier}, reverse={reverse_input}"
                    )
                ok, _why = verify(changed, changed["answer"])
                real_transform_checks += 1
                if not ok:
                    g8_failures.append(
                        f"non-preserving transform seed={seed}, multiplier={multiplier}"
                    )
        # Adjacent transpositions generate every permutation of the displayed
        # input list, so checking all of them proves the remaining relabelling
        # class without attempting to enumerate n! reorderings.
        for position in range(inst["n"] - 1):
            changed = _transformed(inst, 1, False)
            changed["elements"][position], changed["elements"][position + 1] = (
                changed["elements"][position + 1],
                changed["elements"][position],
            )
            invariant_checks += 1
            input_generator_checks += 1
            if canonical_key(changed) != original_key:
                g8_failures.append(
                    f"seed={seed}, adjacent input swap at {position}"
                )
            ok, _why = verify(changed, changed["answer"])
            real_transform_checks += 1
            if not ok:
                g8_failures.append(
                    f"non-preserving input swap seed={seed}, position={position}"
                )
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == len(keys),
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "adjacent_input_generator_checks": input_generator_checks,
        "unrelated_keys": len(keys),
        "distinct_unrelated_keys": distinct,
        "failures": g8_failures[:10],
        "symmetries": "input permutations and x -> u*x for every nonzero u mod prime q",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
