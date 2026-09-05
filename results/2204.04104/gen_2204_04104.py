"""Self-contained Wordle strategy-certificate generator for arXiv:2204.04104.

The generator uses the paper's native Wordle objects, including Remark 4.3's
implicitly represented dictionary.  A strategy is planted by first choosing the
only seed at which a displayed composition of affine bijections vanishes and
then compiling that event into a query whose feedback separates every target.
The answer is therefore known before the instance is assembled; no strategy
search is used in generation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:                 # pragma: no cover - stdlib implementation
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "Wordle instance (alphabet, word length, implicit dictionary, target words, game length)",
        "two-level deterministic Wordle strategy",
        "exact ternary Wordle feedback vectors",
    ],
    "verification_operations": [
        "modular integer arithmetic",
        "implicit-dictionary word evaluation",
        "exact Wordle feedback computation",
        "feedback-partition comparison",
        "strategy replay against every target word",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The displayed affine substitutions compose to one bijection, whose "
        "zero selects the sole first query that turns the target set into "
        "singleton feedback classes; without composing them, one scans the "
        "implicit dictionary."
    ),
    "hardness_basis": (
        "Track B: Theorem 1's recursive solvable algorithm, specialized to "
        "g=2 and Remark 4.3's implicit dictionary, scans M legal query seeds "
        "in O(M*R+M*|W|*d) exact operations; at the shipping preset M=1000003, "
        "R=24 it tested 201773 seeds and 440241 feedbacks, totaling 26854305 "
        "counted exact operations in about 3.3 seconds, while composing the affine "
        "chain once and replaying "
        "the resulting strategy takes at most 156 exact arithmetic operations."
    ),
    "max_answer_tokens": 30,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON object {seed,query,next}.  The seed is an integer 0<=seed<M; "
        "query is the uniquely determined length-d implicit-dictionary word "
        "Q_seed; next is the uniquely determined length-d branch table, with "
        "a displayed target-row index at active positions and -1 at filler "
        "positions.  Thus there is exactly one well-formed certificate object "
        "per dictionary seed."
    ),
    "bounds": {
        "seed": "0 <= seed < M",
        "query_length": "d = target_modulus + base-p seed digits",
        "next_length": "d",
        "query_symbols": "integers 0,...,target_modulus",
        "next_entries": "-1 or a 0-based target-row index",
        "max_atomic_elements": 47,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 101, "targets": 5, "rounds": 3},
    "easy": {"n": 1_000_003, "targets": 11, "rounds": 24},
    "medium": {"n": 2_000_003, "targets": 13, "rounds": 42},
    "hard": {"n": 4_000_003, "targets": 17, "rounds": 60},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The displayed affine substitutions compose to a single affine bijection "
    "of the seed field."
)
PLACEBO_HINT: str = (
    "The displayed modular expressions should be evaluated with careful "
    "attention to their stated ranges."
)

# Replaced after the script-owned oracle arms have run.
G9_EVIDENCE: dict = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES: str = r"""
Definition and Step 0.  Definition 2.1 fixes WI=(Sigma,d,D,W,g), with W a
subset of the legal-guess dictionary D.  Definition 2.2 fixes the repeated-letter
feedback rule.  Proposition 2.4 says that a first query is winning in two rounds
exactly when every resulting consistent class is winnable in one more round;
here that means every feedback class is a singleton.  Definition 2.6 and Lemma
2.7 identify the resulting branch table as a depth-one strategy tree.  Remark
4.3 explicitly permits D to be represented by a polynomial-time membership
rule rather than listed, which is essential because this family has more than a
million indexed legal guesses.

What makes it easy.  Theorem 1 and Algorithm 2 find a strategy in |WI|^O(g)
time, so fixed g is polynomial in an explicitly listed dictionary.  This rules
out Track A for the generated distribution.  On the implicit representation,
the literal g=2 specialization enumerates seed queries and checks their Wordle
feedback partitions.  The compact alternative notices that all R displayed
maps are affine, composes them to A*s+B, and solves the one congruence.  At the
shipping preset the reference enumerator executes millions of exact operations;
the compact route, including writing and replaying the certificate, is bounded
by 156 at the shipping preset.  This is therefore Track B, not a
complexity-theoretic average-case claim.

Construction.  Choose a secret seed first.  Sample R-1 invertible affine maps
and a final nonzero multiplier; its final offset is chosen so the chain maps the
secret to zero.  Fermat's identity delta=1-z^(M-1) is one at that seed and zero
at every other seed.  Target x has active coordinate x+j.  Query seed s has
active coordinate (1+delta)j+(s mod p).  Non-special queries give identical
all-zero feedback for p-1 targets.  At the special seed, target x has its unique
green at j=x-(s mod p), so the supplied next table guesses x and wins on round
two.  Filler coordinates encode s to make all Q_s distinct, but use alphabet
symbols absent from every target at those positions.

Attack handling.  Seed zero, the first 64 seeds, inversion of only the terminal
substitution, 256 uniform restarts, and the tempting but incorrect unweighted
sum-of-offsets ansatz are all exercised over eight shipping instances.  The
secret is sampled away from the fixed tiny prefix, and the affine maps are
resampled only if either one-step ansatz accidentally equals it.  Position,
target, and per-position alphabet orders are independently randomized, so no
rendered row or symbol value marks the strategy.  The domain-standard exhaustive
g=2 Wordle partition search is reported separately, as Track B requires.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 200_000


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    value = max(3, int(value))
    if value % 2 == 0:
        value += 1
    while not _is_prime(value):
        value += 2
    return value


def _digit_count(modulus: int, base: int) -> int:
    count = 1
    capacity = base
    while capacity < modulus:
        capacity *= base
        count += 1
    return count


def _base_digits(value: int, base: int, count: int) -> list[int]:
    digits = []
    for _ in range(count):
        digits.append(value % base)
        value //= base
    return digits


def _chain_value(inst: dict, seed: int, counter: dict | None = None) -> int:
    value = seed
    modulus = inst["seed_modulus"]
    for multiplier, offset in inst["affine_chain"]:
        value = (multiplier * value + offset) % modulus
        if counter is not None:
            counter["chain_arithmetic_operations"] += 2
    return value


def _composed_affine(inst: dict) -> tuple[int, int]:
    """Return A,B with the displayed chain equal to A*s+B modulo M."""
    modulus = inst["seed_modulus"]
    coefficient = 1
    offset = 0
    for multiplier, addition in inst["affine_chain"]:
        coefficient = multiplier * coefficient % modulus
        offset = (multiplier * offset + addition) % modulus
    return coefficient, offset


def _root_from_chain(inst: dict) -> int:
    coefficient, offset = _composed_affine(inst)
    modulus = inst["seed_modulus"]
    return (-offset * pow(coefficient, -1, modulus)) % modulus


def _query_word(inst: dict, seed: int, counter: dict | None = None) -> list[int]:
    modulus = inst["seed_modulus"]
    p = inst["target_modulus"]
    terminal = _chain_value(inst, seed, counter)
    delta = (1 - pow(terminal, modulus - 1, modulus)) % modulus
    if counter is not None:
        exponent = modulus - 1
        # Binary powering: one square per remaining bit and one multiply per
        # remaining 1-bit.  This is a conservative exact-arithmetic count.
        counter["power_multiplications"] += max(0, exponent.bit_length() - 1)
        counter["power_multiplications"] += max(0, exponent.bit_count() - 1)
    slope = 1 + delta
    residue = seed % p
    filler_count = inst["filler_count"]
    digits = _base_digits(seed, p, filler_count)
    logical = []
    for spec in inst["positions"]:
        if spec["kind"] == "active":
            logical_value = (slope * spec["index"] + residue) % p
            if counter is not None:
                counter["query_arithmetic_operations"] += 2
        else:
            logical_value = digits[spec["index"]]
        logical.append(spec["encoding"][logical_value])
    return logical


def _target_word(positions: list[dict], x: int, p: int) -> list[int]:
    result = []
    for spec in positions:
        logical = ((x + spec["index"]) % p
                   if spec["kind"] == "active" else p)
        result.append(spec["encoding"][logical])
    return result


def _next_table(inst: dict, seed: int) -> list[int]:
    p = inst["target_modulus"]
    residue = seed % p
    row_for_x = {row["x"]: index for index, row in enumerate(inst["targets"])}
    result = []
    for spec in inst["positions"]:
        if spec["kind"] == "active":
            result.append(row_for_x[(spec["index"] + residue) % p])
        else:
            result.append(-1)
    return result


def _certificate_for_seed(inst: dict, seed: int) -> dict:
    return {
        "seed": seed,
        "query": _query_word(inst, seed),
        "next": _next_table(inst, seed),
    }


def _terminal_only_guess(chain: list[list[int]], modulus: int) -> int:
    multiplier, offset = chain[-1]
    return (-offset * pow(multiplier, -1, modulus)) % modulus


def _unweighted_guess(chain: list[list[int]], modulus: int) -> int:
    multiplier = 1
    offset = 0
    for a, b in chain:
        multiplier = multiplier * a % modulus
        offset = (offset + b) % modulus
    return (-offset * pow(multiplier, -1, modulus)) % modulus


def make_instance(n: int, seed: int = 0, targets: int = 17,
                  rounds: int = 60, **params: object) -> dict:
    """Inverse-generate a native two-round Wordle strategy instance."""
    del params
    modulus = _next_prime(n)
    p = _next_prime(targets)
    if p < 5:
        raise ValueError("at least five target words are required")
    if rounds < 2:
        raise ValueError("the affine chain needs at least two rounds")
    if rounds > 80:
        raise ValueError("rounds above 80 exceed the intended-route budget")
    if modulus <= 128:
        secret_floor = 64
    else:
        secret_floor = 64
    rng = random.Random(seed)

    # The answer is sampled first.  Resampling a chain whose deliberately weak
    # one-step ansatz happens to hit the already-fixed secret does not solve the
    # instance and does not change the planted certificate.
    secret = rng.randrange(secret_floor, modulus)
    for _attempt in range(100):
        chain = []
        value = secret
        for _ in range(rounds - 1):
            multiplier = rng.randrange(1, modulus)
            offset = rng.randrange(modulus)
            chain.append([multiplier, offset])
            value = (multiplier * value + offset) % modulus
        multiplier = rng.randrange(1, modulus)
        offset = (-multiplier * value) % modulus
        chain.append([multiplier, offset])
        if (_terminal_only_guess(chain, modulus) != secret
                and _unweighted_guess(chain, modulus) != secret):
            break
    else:
        raise RuntimeError("could not separate the planted root from weak ansatzes")

    filler_count = _digit_count(modulus, p)
    logical_positions = ([{"kind": "active", "index": j}
                          for j in range(p)]
                         + [{"kind": "filler", "index": k}
                            for k in range(filler_count)])
    rng.shuffle(logical_positions)
    positions = []
    for item in logical_positions:
        encoding = list(range(p + 1))
        rng.shuffle(encoding)
        positions.append({**item, "encoding": encoding})

    target_rows = [
        {"x": x, "word": _target_word(positions, x, p)}
        for x in range(p)
    ]
    rng.shuffle(target_rows)
    inst = {
        "seed_modulus": modulus,
        "target_modulus": p,
        "game_length": 2,
        "filler_count": filler_count,
        "affine_chain": chain,
        "positions": positions,
        "targets": target_rows,
    }
    inst["answer"] = _certificate_for_seed(inst, secret)
    return inst


def render(inst: dict) -> str:
    """Render the complete Wordle instance and exact certificate grammar."""
    modulus = inst["seed_modulus"]
    p = inst["target_modulus"]
    d = len(inst["positions"])
    position_lines = []
    for physical, spec in enumerate(inst["positions"]):
        label = (f"active j={spec['index']}" if spec["kind"] == "active"
                 else f"filler k={spec['index']}")
        position_lines.append(
            f"  {physical}: {label}; enc={json.dumps(spec['encoding'], separators=(',', ':'))}"
        )
    chain_lines = [
        f"  z{i + 1} = ({a}*z{i} + {b}) mod {modulus}"
        for i, (a, b) in enumerate(inst["affine_chain"])
    ]
    target_lines = [
        f"  {index}: x={row['x']}; word={json.dumps(row['word'], separators=(',', ':'))}"
        for index, row in enumerate(inst["targets"])
    ]
    statement = f"""Two-round Wordle strategy certificate

This is the generalized Wordle game below; no outside word list is used.
There are {p} possible target words, every word has length d={d}, and at most
g=2 guesses may be made.  Positions and target rows are 0-based.  Repetition is
allowed unless a rule below says otherwise.

Alphabet and feedback.  A printed entry v at physical position i denotes the
position-tagged alphabet symbol (i,v).  Thus equal printed values in different
positions are different letters.  For a guessed word u and target w, feedback
is a length-{d} vector in {{0,1,2}}: 2 means u[i]=w[i]; after all 2s are removed,
1 marks an unmatched occurrence of u[i] elsewhere in w, using occurrences from
left to right; 0 means absent.  Position tags imply that this instance actually
uses only 0 and 2 feedback, but the rule is the ordinary exact Wordle rule.

At each physical position, enc maps a logical value 0,...,{p} to the printed
symbol.  Active and filler positions are:
{chr(10).join(position_lines)}

Target list W (also legal guesses).  The x label is part of the instance data:
{chr(10).join(target_lines)}

Implicit dictionary D.  Besides the {p} target words, D contains exactly one
word Q_s for each integer seed s with 0 <= s < M={modulus}.  Compute Q_s as
follows.  Start z0=s and perform these substitutions in order:
{chr(10).join(chain_lines)}
Let z be the final value and set

  delta = (1 - z^(M-1)) mod M,  c = s mod {p}.

For an active position labelled j, Q_s has logical value
((1+delta)*j+c) mod {p}.  For filler k it has logical value floor(s/{p}^k)
mod {p}.  Apply that position's enc list to obtain each printed entry.  M is
prime, so delta is exactly 1 when z=0 and exactly 0 otherwise.  The filler
digits make all Q_s distinct; logical value {p} occurs in every target filler
and never in a Q_s filler.

Required witness.  Give a concrete depth-one strategy tree.  Its JSON object
has exactly three keys:

  seed   the seed s of the first guess Q_s;
  query  all {d} printed entries of Q_s, in physical-position order;
  next   {d} integers.  If the first feedback has its sole 2 at physical
         position i, next[i] is the 0-based target-row guessed second.  At a
         filler position next[i] must be -1.

The verifier recomputes dictionary membership, exact feedback for every target,
and every second guess.  It accepts any seed whose supplied tree wins against
all targets; it does not compare with a stored answer.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys seed, query, and next.  Example syntax:
<answer>{{"seed":7,"query":[1,4,0],"next":[2,0,-1]}}</answer>
Output nothing else inside the tags.
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\nHint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        statement += "\nHint: " + PLACEBO_HINT + "\n"
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON object, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return answer if isinstance(answer, dict) else None


def _feedback(guess: list[int], target: list[int]) -> tuple[int, ...]:
    """Definition 2.2 feedback on position-tagged symbols, exactly."""
    if len(guess) != len(target):
        raise ValueError("words must have equal length")
    response = [0] * len(guess)
    unmatched_target: dict[tuple[int, int], int] = {}
    for i, (g, w) in enumerate(zip(guess, target)):
        if g == w:
            response[i] = 2
        else:
            symbol = (i, w)
            unmatched_target[symbol] = unmatched_target.get(symbol, 0) + 1
    for i, g in enumerate(guess):
        if response[i] == 2:
            continue
        symbol = (i, g)
        if unmatched_target.get(symbol, 0):
            response[i] = 1
            unmatched_target[symbol] -= 1
    return tuple(response)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay any supplied two-round strategy; never consult inst['answer']."""
    if not isinstance(answer, dict) or not answer:
        return False, "answer must be a nonempty JSON object"
    if set(answer) != {"seed", "query", "next"}:
        return False, "answer must contain exactly seed, query, and next"
    seed = answer["seed"]
    modulus = inst["seed_modulus"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        return False, "seed must be an integer"
    if not 0 <= seed < modulus:
        return False, "seed is outside the implicit dictionary range"
    query = answer["query"]
    d = len(inst["positions"])
    if not isinstance(query, list):
        return False, "query must be a JSON list"
    if len(query) < d:
        return False, "query is missing a coordinate"
    if len(query) > d:
        return False, "query has a duplicate or extra coordinate"
    p = inst["target_modulus"]
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= p
           for v in query):
        return False, "query contains a symbol outside its printed range"
    expected_query = _query_word(inst, seed)
    if query != expected_query:
        return False, "query does not equal the implicit dictionary word Q_seed"
    next_table = answer["next"]
    if not isinstance(next_table, list):
        return False, "next must be a JSON list"
    if len(next_table) != d:
        return False, "next table has the wrong length"
    if any(isinstance(v, bool) or not isinstance(v, int)
           for v in next_table):
        return False, "next entries must be integers"
    expected_next = _next_table(inst, seed)
    if next_table != expected_next:
        return False, "next table does not match its stated branch encoding"

    seen: dict[tuple[int, ...], int] = {}
    for target_index, row in enumerate(inst["targets"]):
        response = _feedback(query, row["word"])
        if response in seen:
            return False, (
                "first query leaves indistinguishable targets "
                f"{seen[response]} and {target_index}"
            )
        seen[response] = target_index
        green_positions = [i for i, value in enumerate(response) if value == 2]
        if len(green_positions) != 1:
            return False, "first feedback is not encoded by one green position"
        physical = green_positions[0]
        if next_table[physical] != target_index:
            return False, "second-guess branch names the wrong target row"
        if _feedback(inst["targets"][next_table[physical]]["word"],
                     row["word"]) != (2,) * d:
            return False, "second guess does not solve its target branch"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the structure-aware seed-indexed language."""
    return _certificate_for_seed(inst, rng.randrange(inst["seed_modulus"]))


def search_space(inst: dict) -> int:
    return inst["seed_modulus"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the declared language when its exact cap permits."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    for seed in range(inst["seed_modulus"]):
        count += int(verify(inst, _certificate_for_seed(inst, seed))[0])
    return count


def canonical_key(inst: dict) -> str:
    """Quotient target order, position order, and alphabet relabelling."""
    payload = {
        "family": "implicit-two-round-affine-wordle",
        "seed_modulus": inst["seed_modulus"],
        "target_modulus": inst["target_modulus"],
        # Different displayed affine chains with the same zero define exactly
        # the same implicit dictionary, so the zero—not raw coefficients—is
        # the chain's semantic normal form.
        "exceptional_seed": _root_from_chain(inst),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _route_operation_bound(inst: dict) -> int:
    """Conservative post-insight exact-arithmetic bound."""
    rounds = len(inst["affine_chain"])
    p = inst["target_modulus"]
    # Compose A,B: 3 per map.  One extended-Euclid inversion is bounded by
    # twice the modulus bit length.  Query and branch tables need at most three
    # modular operations per active coordinate; filler extraction and setup add 5.
    return (3 * rounds + 2 * inst["seed_modulus"].bit_length()
            + 3 * p + inst["filler_count"] + 5)


def escalate(params: dict) -> dict | str | None:
    """Grow the implicit dictionary while keeping the strategy tree fixed."""
    harder = dict(params)
    current = int(harder.get("n", 100_003))
    harder["n"] = _next_prime(max(current + 2, (3 * current) // 2))
    harder["targets"] = int(harder.get("targets", 17))
    harder["rounds"] = min(80, int(harder.get("rounds", 60)) + 4)
    probe = make_instance(seed=98765, **harder)
    if _route_operation_bound(probe) > 300:
        return "cap_bound"
    return harder


def _reference_algorithm(inst: dict) -> dict:
    """Literal g=2 query enumeration using exact feedback partitions."""
    counter = {
        "seeds_tested": 0,
        "feedback_calls": 0,
        "feedback_coordinate_comparisons": 0,
        "chain_arithmetic_operations": 0,
        "power_multiplications": 0,
        "query_arithmetic_operations": 0,
    }
    start = time.perf_counter()
    answer = None
    d = len(inst["positions"])
    for seed in range(inst["seed_modulus"]):
        counter["seeds_tested"] += 1
        query = _query_word(inst, seed, counter)
        seen = set()
        diagnostic = True
        for row in inst["targets"]:
            response = _feedback(query, row["word"])
            counter["feedback_calls"] += 1
            counter["feedback_coordinate_comparisons"] += d
            if response in seen:
                diagnostic = False
                break
            seen.add(response)
        if diagnostic:
            candidate = {
                "seed": seed,
                "query": query,
                "next": _next_table(inst, seed),
            }
            if verify(inst, candidate)[0]:
                answer = candidate
                break
    wall = time.perf_counter() - start
    if answer is None:
        return {"ok": False, "reason": "no strategy found", "answer": None,
                "wall_clock_sec": wall, "counter": counter}
    ok, reason = verify(inst, answer)
    return {"ok": ok, "reason": reason, "answer": answer,
            "wall_clock_sec": wall, "counter": counter}


def _attack_seed(inst: dict, seed: int) -> bool:
    candidate = _certificate_for_seed(inst, seed % inst["seed_modulus"])
    return verify(inst, candidate)[0]


def _attack_greedy_prefix(inst: dict, limit: int = 64) -> bool:
    return any(_attack_seed(inst, seed)
               for seed in range(min(limit, inst["seed_modulus"])))


def _attack_random_restart(inst: dict, attack_seed: int,
                           restarts: int = 256) -> bool:
    rng = random.Random(attack_seed ^ 0x220404104)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_terminal_map(inst: dict) -> bool:
    seed = _terminal_only_guess(inst["affine_chain"], inst["seed_modulus"])
    return _attack_seed(inst, seed)


def _attack_unweighted_offsets(inst: dict) -> bool:
    seed = _unweighted_guess(inst["affine_chain"], inst["seed_modulus"])
    return _attack_seed(inst, seed)


def _reorder_targets(inst: dict, permutation: list[int]) -> dict:
    moved = copy.deepcopy(inst)
    moved["targets"] = [copy.deepcopy(inst["targets"][i]) for i in permutation]
    old_to_new = {old: new for new, old in enumerate(permutation)}
    moved["answer"]["next"] = [old_to_new[v] if v >= 0 else -1
                                  for v in inst["answer"]["next"]]
    return moved


def _permute_positions(inst: dict, permutation: list[int]) -> dict:
    moved = copy.deepcopy(inst)
    moved["positions"] = [copy.deepcopy(inst["positions"][i])
                           for i in permutation]
    for row_index, row in enumerate(inst["targets"]):
        moved["targets"][row_index]["word"] = [row["word"][i]
                                                   for i in permutation]
    moved["answer"]["query"] = [inst["answer"]["query"][i]
                                  for i in permutation]
    moved["answer"]["next"] = [inst["answer"]["next"][i]
                                 for i in permutation]
    return moved


def _relabel_alphabets(inst: dict, permutations: list[list[int]]) -> dict:
    moved = copy.deepcopy(inst)
    if len(permutations) != len(inst["positions"]):
        raise ValueError("one alphabet permutation is required per position")
    for pos, relabel in enumerate(permutations):
        if sorted(relabel) != list(range(inst["target_modulus"] + 1)):
            raise ValueError("invalid per-position alphabet permutation")
        moved["positions"][pos]["encoding"] = [
            relabel[value] for value in inst["positions"][pos]["encoding"]
        ]
        for row in moved["targets"]:
            row["word"][pos] = relabel[row["word"][pos]]
        moved["answer"]["query"][pos] = relabel[inst["answer"]["query"][pos]]
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(v) for v in value)
        return 1

    return len(encoded), (len(encoded) + 3) // 4, atoms(answer)


def selftest() -> dict:
    """Run all nine mandatory correctness and hardness gates."""
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            json_native = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            checks += 1
            if not (ok and json_native):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason, "json_native": json_native})
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    answer = copy.deepcopy(inst["answer"])
    swapped = copy.deepcopy(answer)
    swapped["query"][0], swapped["query"][1] = (
        swapped["query"][1], swapped["query"][0])
    corruptions = {
        "drop_one": {**answer, "query": answer["query"][:-1]},
        "swap_one": swapped,
        "duplicate_one": {**answer, "query": answer["query"] + [answer["query"][-1]]},
        "empty": {},
        "out_of_range": {**answer, "seed": inst["seed_modulus"]},
    }
    rejections = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejections[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in rejections.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejections.values())
                and len(set(reasons)) == len(reasons),
        "rejections": rejections,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "Composing the substitutions gives the following strategy.\n"
        "```text\n(all residues reduced exactly)\n```\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n"
        "The branch table uses displayed target rows."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(0x220404104)
    total = 200_000
    hits = 0
    sample_start = time.perf_counter()
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    sample_wall = time.perf_counter() - sample_start
    exact_valid = 1
    exact_density = exact_valid / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": total,
        "observed_probability": hits / total,
        "exact_valid_certificates": exact_valid,
        "certificate_space": search_space(inst),
        "exact_density": exact_density,
        "structure_aware_prior": (
            "uniform legal seed; query and branch table are deterministically "
            "filled from that seed, so redundant certificate fields add no entropy"
        ),
        "wall_clock_sec": round(sample_wall, 6),
    }

    demo = make_instance(seed=2718, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference = _reference_algorithm(inst)
    ref_counter = reference["counter"]
    ref_operations = sum(
        ref_counter[key] for key in (
            "chain_arithmetic_operations", "power_multiplications",
            "query_arithmetic_operations", "feedback_coordinate_comparisons"
        )
    )
    report["G5_density_and_baseline"] = {
        "pass": (demo_count == 1 and reference["ok"]
                 and exact_density < 1e-6),
        "shipping_density_exact": exact_density,
        "shipping_valid_count_exact": exact_valid,
        "shipping_certificate_space": search_space(inst),
        "shipping_sample_hits": hits,
        "shipping_sample_total": total,
        "demo_valid_count_enumerated": demo_count,
        "demo_certificate_space": search_space(demo),
        "strongest_attack": "Algorithm 2 specialized exhaustive g=2 query enumeration",
        "baseline_wall_clock_sec": round(reference["wall_clock_sec"], 6),
        "baseline_seeds_tested": ref_counter["seeds_tested"],
        "baseline_feedback_calls": ref_counter["feedback_calls"],
        "baseline_exact_operations": ref_operations,
    }

    attack_results = {
        "outlier_zero_seed": {"successes": 0, "attempts": 0},
        "greedy_first_64_seeds": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "terminal_map_only": {"successes": 0, "attempts": 0},
        "unweighted_offset_ansatz": {"successes": 0, "attempts": 0},
    }
    for attack_seed in range(8):
        trial = make_instance(seed=9000 + attack_seed, **shipping_params)
        outcomes = {
            "outlier_zero_seed": _attack_seed(trial, 0),
            "greedy_first_64_seeds": _attack_greedy_prefix(trial),
            "random_restart_256": _attack_random_restart(trial, attack_seed),
            "terminal_map_only": _attack_terminal_map(trial),
            "unweighted_offset_ansatz": _attack_unweighted_offsets(trial),
        }
        for name, success in outcomes.items():
            attack_results[name]["successes"] += int(success)
            attack_results[name]["attempts"] += 1
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference["ok"],
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Theorem 1 / Algorithm 2 specialized to g=2",
            "complexity": "O(M*R + M*|W|*d) exact operations",
            "wall_clock_sec": round(reference["wall_clock_sec"], 6),
            "operations": ref_operations,
            "seeds_tested": ref_counter["seeds_tested"],
            "feedback_calls": ref_counter["feedback_calls"],
            "solves": "1/1, as expected on Track B",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_dictionary_seeds": search_space(inst),
        "doubled_dictionary_seeds": search_space(doubled),
        "shipping_answer_atoms": _answer_metrics(inst["answer"])[2],
        "doubled_answer_atoms": _answer_metrics(doubled["answer"])[2],
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    canonical_failures = []
    keys = []
    for seed in range(20):
        trial = make_instance(seed=12_000 + seed, **shipping_params)
        key = canonical_key(trial)
        keys.append(key)
        target_perm = list(reversed(range(len(trial["targets"]))))
        position_perm = list(reversed(range(len(trial["positions"]))))
        reordered = _reorder_targets(trial, target_perm)
        repositioned = _permute_positions(trial, position_perm)
        relabel_rng = random.Random(seed ^ 0xC4A0C1)
        alphabet_perms = []
        for _ in trial["positions"]:
            permutation = list(range(trial["target_modulus"] + 1))
            relabel_rng.shuffle(permutation)
            alphabet_perms.append(permutation)
        relabelled = _relabel_alphabets(trial, alphabet_perms)
        composed = _relabel_alphabets(
            _permute_positions(reordered, position_perm),
            [alphabet_perms[i] for i in position_perm],
        )
        for name, moved in (("target_order", reordered),
                            ("position_order", repositioned),
                            ("alphabet_labels", relabelled),
                            ("composed", composed)):
            invariant_checks += 1
            if canonical_key(moved) != key:
                canonical_failures.append({"seed": seed, "map": name,
                                           "failure": "key changed"})
            ok, why = verify(moved, moved["answer"])
            carried_checks += 1
            if not ok:
                canonical_failures.append({"seed": seed, "map": name,
                                           "failure": why})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not canonical_failures and distinct == len(keys),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": len(keys),
        "distinct_keys": distinct,
        "failures": canonical_failures,
        "symmetries": [
            "target-row reordering", "physical-position permutation",
            "independent alphabet relabelling at every position",
            "their composition",
        ],
    }

    # Report a measured worst case rather than the convenient shipping seed.
    # The shape is fixed, but decimal widths vary with the planted seed and
    # alphabet relabellings.
    chars = tokens = elements = 0
    for metric_seed in range(1000):
        metric_inst = make_instance(seed=metric_seed, **shipping_params)
        trial_chars, trial_tokens, trial_elements = _answer_metrics(
            metric_inst["answer"]
        )
        chars = max(chars, trial_chars)
        tokens = max(tokens, trial_tokens)
        elements = max(elements, trial_elements)
    intended_ops = _route_operation_bound(inst)
    arms = copy.deepcopy(G9_EVIDENCE)
    hinted = arms.get("hinted", {"solved": 0, "attempts": 0})
    placebo = arms.get("placebo", {"solved": 0, "attempts": 0})
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else None)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else None)
    within_caps = chars <= 2000 and elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {name: arms.get(name, {"solved": 0, "attempts": 0})
                 for name in ("bare", "hinted", "placebo")},
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": arms.get("hinted_verdict", "not_run"),
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "diagnostic_not_gated": True,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    gate_rows = [value for key, value in report.items()
                 if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(row.get("pass") for row in gate_rows)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
