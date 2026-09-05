"""Rejected prototype for compressed Hamiltonian cycles in square-free Cayley graphs.

Retained for audit under the task's "if you built a module, KEEP it" rule.  It
is not a shippable generator: Section 3, Case 2 already gives the compressed
certificate by a constant-size formula, so the proposed distribution fails H
on Track A and has no mechanical-versus-compact gap for Track B.  See
REJECTED.md for the measured Step 0 analysis.

The native objects and certificate come from arXiv:2107.14787.  In the
two-generator case of the proof of Theorem 1.3, a Hamiltonian cycle in G/G'
whose voltage generates the cyclic normal subgroup G' is repeated |G'| times.
This module builds exact semidirect products C_(qrs) rtimes C_p for which that
certificate is known before the visible generators are relabelled and inverted.

The answer is the paper's own exponent notation made JSON-native: a bounded
run-length word and an outer repetition count.  Verification checks the
Factor Group Lemma hypotheses using exact modular group arithmetic.  It never
reads the planted answer and never expands the full pqrs-vertex cycle.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite semidirect-product group of square-free order",
        "Cayley generators as exact group elements",
        "run-length encoded generator word",
    ],
    "verification_operations": [
        "exact semidirect-product multiplication",
        "exact quotient walk comparison",
        "exact voltage computation",
        "integer gcd order test",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize a short Hamiltonian period in the cyclic quotient whose "
        "voltage generates the cyclic normal subgroup; without that quotient "
        "decomposition one confronts the enormous full Cayley graph."
    ),
    "hardness_basis": (
        "Track B: Lemma 2.4 (the Factor Group Lemma) and Case 2 of the proof "
        "give a constructive algorithm; ordinary lift materialization is "
        "O(|G|) and takes |G| exact group steps (139,133,387 at the shipping "
        "preset with seed 0); the paper's compressed Case 2 constructor is "
        "O(p log N), is timed in selftest, and recognizing/writing its eight-run "
        "quotient/voltage certificate takes at most 248 exact operations."
    ),
    "max_answer_tokens": 33,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n and prime_spread enlarge the ambient group while p and the certificate's
# eight runs stay fixed.  The demo uses the smallest nonabelian group supported
# by the construction and a three-run period that can be checked on paper.
DIFFICULTY = {
    "demo": {"n": 1, "p": 3, "run_count": 3, "prime_spread": 0},
    "easy": {"n": 1, "p": 29, "run_count": 8, "prime_spread": 1},
    "medium": {"n": 2, "p": 29, "run_count": 8, "prime_spread": 2},
    "hard": {"n": 4, "p": 29, "run_count": 8, "prime_spread": 4},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The subgroup with second coordinate zero is cyclic, and quotient periods "
    "are distinguished by the subgroup element given by their voltage."
)
PLACEBO_HINT = (
    "Keep every signed exponent and modular coordinate exact, and check the "
    "specified run count carefully before submitting."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {repeat:N,runs:[[S,e],...]} with exactly L runs; "
        "S is X or Y, every e is a nonzero integer, the absolute exponents "
        "sum to p, and repeat is the displayed N."
    ),
    "bounds": {
        "repeat": "exactly N=q*r*s",
        "runs": "L (3 for demo, 8 for every benchmark preset)",
        "symbols": ["X", "Y"],
        "exponent_absolute_min": 1,
        "exponent_absolute_max": "p",
        "absolute_exponent_sum": "p",
        "candidate_count": "binomial(p-1,L-1)*4^L",
    },
}

NOTES = (
    "Definition 1.1 fixes the native object: Cay(G;A) has group elements as "
    "vertices and generator/inverse differences as edges.  Theorem 1.2 is the "
    "pqrs existence result.  Lemma 2.4 fixes the executable certificate: a "
    "Hamiltonian quotient word with generating voltage lifts by repetition.  "
    "Theorem 2.2 identifies the easy commutator orders 1, prime, and a product "
    "of two primes; this generator deliberately uses the remaining Case 2 "
    "regime G'=C_q*C_r*C_s with two generators outside G'.  Case 2 explicitly "
    "writes the quotient word, so Track A would be false and Track B is used.  "
    "The certificate is sampled in base coordinates, then generator names, "
    "orientations, conjugacy coordinates, roots of unity, and run splits are "
    "randomized.  The outlier, single-generator, alternating, greedy-quotient, "
    "and random-run attacks are all checked separately."
)

# Filled from the three isolated harden.py runs.  Zero attempts is deliberately
# not treated as evidence; selftest requires at least three attempts per arm.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_prime_64(value):
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value >= 1 << 64:
        raise ValueError("prime search exceeded the deterministic 64-bit regime")
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _action_primes(p, n, seed, prime_spread):
    """Three distinct primes ell=1 (mod p), without solving the instance."""
    if p == 3 and prime_spread == 0:
        multiplier = 2
    else:
        # Consecutive seeds start far enough apart to make duplicate groups
        # vanishingly unlikely, while seed 0 remains the small measured baseline.
        bucket = abs(int(seed)) % 1_000_003
        multiplier = n * (2 + 200 * prime_spread * bucket)
        if multiplier % 2:
            multiplier += 1
    factors = []
    used = set()
    while len(factors) < 3:
        candidate = p * multiplier + 1
        if candidate != p and candidate not in used and _is_prime_64(candidate):
            factors.append(candidate)
            used.add(candidate)
        multiplier += 2
    return factors


def _crt(residues, moduli):
    modulus = math.prod(moduli)
    value = 0
    for residue, prime in zip(residues, moduli):
        cofactor = modulus // prime
        value += residue * cofactor * pow(cofactor, -1, prime)
    return value % modulus


def _action_parameter(p, factors, rng):
    residues = []
    for prime in factors:
        exponent = (prime - 1) // p
        root = None
        for base in range(2, prime):
            candidate = pow(base, exponent, prime)
            if candidate != 1:
                root = candidate
                break
        if root is None:
            raise RuntimeError("failed to find a nontrivial p-th root")
        residues.append(pow(root, rng.randrange(1, p), prime))
    return _crt(residues, factors)


def _mul(left, right, modulus, p, alpha):
    """Multiply (x,i)(y,j)=(x+alpha^i*y,i+j)."""
    x, i = left
    y, j = right
    return ((x + pow(alpha, i, modulus) * y) % modulus, (i + j) % p)


def _inverse(element, modulus, p, alpha):
    x, i = element
    return ((-pow(alpha, (-i) % p, modulus) * x) % modulus, (-i) % p)


def _power(element, exponent, modulus, p, alpha):
    if exponent < 0:
        element = _inverse(element, modulus, p, alpha)
        exponent = -exponent
    result = (0, 0)
    base = element
    while exponent:
        if exponent & 1:
            result = _mul(result, base, modulus, p, alpha)
        base = _mul(base, base, modulus, p, alpha)
        exponent //= 2
    return result


def _positive_parts(total, count, rng=None):
    if count < 1 or total < count:
        raise ValueError("cannot split a positive run that many ways")
    if count == 1:
        return [total]
    if rng is None:
        # Balanced deterministic split for reference algorithms and attacks.
        quotient, remainder = divmod(total, count)
        return [quotient + (i < remainder) for i in range(count)]
    cuts = sorted(rng.sample(range(1, total), count - 1))
    return [b - a for a, b in zip([0] + cuts, cuts + [total])]


def _split_chunks(chunks, run_count, rng=None):
    """Split signed symbolic chunks without changing the expanded word."""
    chunks = [(symbol, exponent) for symbol, exponent in chunks if exponent]
    if not chunks or run_count < len(chunks):
        return None
    allocation = [1] * len(chunks)
    left = run_count - len(chunks)
    choices = list(range(len(chunks)))
    while left:
        possible = [i for i in choices if allocation[i] < abs(chunks[i][1])]
        if not possible:
            return None
        if rng is None:
            index = max(possible, key=lambda i: abs(chunks[i][1]) / allocation[i])
        else:
            index = rng.choice(possible)
        allocation[index] += 1
        left -= 1
    runs = []
    for (symbol, exponent), count in zip(chunks, allocation):
        sign = 1 if exponent > 0 else -1
        for part in _positive_parts(abs(exponent), count, rng):
            runs.append([symbol, sign * part])
    return runs


def make_instance(n, seed=0, **params):
    """Construct a Cayley graph and its lift certificate before obfuscation."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    p = params.pop("p", 13)
    run_count = params.pop("run_count", 8)
    prime_spread = params.pop("prime_spread", 1)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if p < 3 or p % 2 == 0 or not _is_prime_64(p):
        raise ValueError("p must be an odd prime")
    if isinstance(run_count, bool) or not isinstance(run_count, int):
        raise ValueError("run_count must be an integer")
    if not 1 <= run_count <= p:
        raise ValueError("run_count must lie between 1 and p")
    if isinstance(prime_spread, bool) or not isinstance(prime_spread, int):
        raise ValueError("prime_spread must be an integer")
    if prime_spread < 0:
        raise ValueError("prime_spread must be nonnegative")

    rng = random.Random(seed)
    factors = _action_primes(p, n, seed, prime_spread)
    modulus = math.prod(factors)
    alpha = _action_parameter(p, factors, rng)

    # a has nonzero quotient coordinate and therefore order p.  gamma is a
    # generator of C_N because its first coordinate is a unit modulo N.
    quotient_step = rng.randrange(1, p)
    a = (rng.randrange(modulus), quotient_step)
    while True:
        gamma_coordinate = rng.randrange(1, modulus)
        if math.gcd(gamma_coordinate, modulus) == 1:
            break
    gamma = (gamma_coordinate, 0)
    if p == 3:
        k = 1
    else:
        k = rng.randrange(4, (p - 1) // 2 + 1)
    b = _mul(_power(a, k, modulus, p, alpha), gamma, modulus, p, alpha)

    # The paper's Case 2 word, represented before visible relabelling.
    base_chunks = [
        ["A", 1],
        ["A", 1],  # the two b occurrences are relabelled below
        ["A", p - k - 1],
    ] if p == 3 else [
        ["B", 1],
        ["A", -(k - 1)],
        ["B", 1],
        ["A", p - k - 1],
    ]
    if p == 3:
        base_chunks = [["B", 1], ["B", 1], ["A", 1]]

    swap = bool(rng.getrandbits(1))
    sign_a = rng.choice((-1, 1))
    sign_b = rng.choice((-1, 1))
    visible_for = {"A": ("Y" if swap else "X"), "B": ("X" if swap else "Y")}
    sign_for = {"A": sign_a, "B": sign_b}
    visible = {}
    visible[visible_for["A"]] = _power(a, sign_a, modulus, p, alpha)
    visible[visible_for["B"]] = _power(b, sign_b, modulus, p, alpha)

    translated = [
        [visible_for[symbol], exponent * sign_for[symbol]]
        for symbol, exponent in base_chunks
    ]
    runs = _split_chunks(translated, run_count, rng)
    if runs is None:
        raise RuntimeError("the requested run_count cannot encode the planted word")

    answer = {"repeat": modulus, "runs": runs}
    return {
        "family": "compressed Hamiltonian cycle in a pqrs Cayley graph",
        "n": n,
        "p": p,
        "factors": factors,
        "N": modulus,
        "alpha": alpha,
        "generators": {name: list(visible[name]) for name in ("X", "Y")},
        "run_count": run_count,
        "prime_spread": prime_spread,
        "answer": answer,
    }


def render(inst):
    p, modulus = inst["p"], inst["N"]
    x = inst["generators"]["X"]
    y = inst["generators"]["Y"]
    example_runs = [["X", 1] for _ in range(inst["run_count"])]
    example = {"repeat": modulus, "runs": example_runs}
    statement = f"""COMPRESSED HAMILTONIAN CYCLE IN A CAYLEY GRAPH

Let N={modulus}={inst['factors'][0]}*{inst['factors'][1]}*{inst['factors'][2]} and p={p}.
The vertices are all pairs (u,i) with u in {{0,...,N-1}} and i in
{{0,...,p-1}}.  Multiplication is

  (u,i)*(v,j) = (u + alpha^i*v mod N, i+j mod p),

where alpha={inst['alpha']}; exponents of alpha are evaluated modulo N.  The
identity is (0,0).  This is a group of order p*N, and the subgroup H of pairs
(u,0) is cyclic and normal.

The undirected Cayley graph has one vertex for each group element.  From a
vertex g there is an edge to g*S and g*S^(-1) for each named generator:

  X = ({x[0]},{x[1]})
  Y = ({y[0]},{y[1]})

A run [\"S\",e], where S is X or Y and e is a nonzero signed integer, means
|e| consecutive Cayley steps by S when e>0 or by S^(-1) when e<0.  A list of
runs is one period.  Repeating a period R times is a Hamiltonian cycle when its
expanded walk starts at (0,0), visits every one of the p*N vertices exactly
once before returning, and uses only the stated Cayley edges.

Give a compressed certificate with exactly L={inst['run_count']} runs.  It must
have repeat exactly N={modulus}; every run symbol must be \"X\" or \"Y\"; each
exponent must be a nonzero decimal integer with absolute value at most p={p};
and the sum of the absolute exponents must be exactly p={p}.  Thus one period
has p edges.  The checker expands this short period in the quotient modulo H,
requires it to visit each of the p quotient vertices once and return, computes
the period's exact group product (its voltage), and requires that voltage to
generate H.  These executable conditions ensure that the N repetitions visit
every full-group vertex exactly once.

The answer is one JSON object; run order and signs matter and adjacent runs are
not implicitly merged.

Give your final answer inside <answer></answer> tags, as that JSON object.
Example format only: <answer>{json.dumps(example, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON certificate, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {"repeat", "runs"}:
        return None
    if isinstance(value["repeat"], bool) or not isinstance(value["repeat"], int):
        return None
    if not isinstance(value["runs"], list):
        return None
    for run in value["runs"]:
        if not isinstance(run, list) or len(run) != 2:
            return None
        if not isinstance(run[0], str):
            return None
        if isinstance(run[1], bool) or not isinstance(run[1], int):
            return None
    return value


def verify(inst, answer):
    """Check any bounded lift witness exactly, never consulting inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"repeat", "runs"}:
        return False, "answer must contain exactly repeat and runs"
    repeat = answer["repeat"]
    runs = answer["runs"]
    if isinstance(repeat, bool) or not isinstance(repeat, int):
        return False, "repeat must be an integer"
    if repeat != inst["N"]:
        return False, f"repeat must equal N={inst['N']}"
    if not isinstance(runs, list):
        return False, "runs must be a JSON list"
    if len(runs) != inst["run_count"]:
        return False, f"expected {inst['run_count']} runs, got {len(runs)}"
    p, modulus, alpha = inst["p"], inst["N"], inst["alpha"]
    total = 0
    for index, run in enumerate(runs):
        if not isinstance(run, list) or len(run) != 2:
            return False, f"run {index + 1} must be [symbol,exponent]"
        symbol, exponent = run
        if symbol not in ("X", "Y"):
            return False, f"run {index + 1} has an unknown generator symbol"
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            return False, f"run {index + 1} exponent is not an integer"
        if exponent == 0 or abs(exponent) > p:
            return False, f"run {index + 1} exponent is outside the signed bound"
        total += abs(exponent)
    if total != p:
        return False, f"period expands to {total} steps, expected {p}"

    # Reject almost all random words in the tiny quotient before doing any
    # potentially large modular multiplication in the full group.
    quotient = 0
    seen = set()
    signed_steps = []
    step_number = 0
    for symbol, exponent in runs:
        generator = tuple(inst["generators"][symbol])
        step = _power(generator, 1 if exponent > 0 else -1, modulus, p, alpha)
        for _ in range(abs(exponent)):
            if quotient in seen:
                return False, f"quotient vertex {quotient} is revisited at step {step_number}"
            seen.add(quotient)
            quotient = (quotient + step[1]) % p
            signed_steps.append(step)
            step_number += 1
    if quotient != 0:
        return False, f"quotient period ends at {quotient}, not 0"
    if len(seen) != p:
        return False, f"quotient period visits {len(seen)} of {p} vertices"
    voltage = (0, 0)
    for step in signed_steps:
        voltage = _mul(voltage, step, modulus, p, alpha)
    if voltage[1] != 0:
        return False, "period voltage is not in the normal subgroup H"
    divisor = math.gcd(voltage[0], modulus)
    if divisor != 1:
        return False, f"period voltage does not generate H; gcd is {divisor}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact shape-aware bounded certificate language."""
    p = inst["p"]
    count = inst["run_count"]
    cuts = sorted(rng.sample(range(1, p), count - 1)) if count > 1 else []
    magnitudes = [b - a for a, b in zip([0] + cuts, cuts + [p])]
    runs = []
    for magnitude in magnitudes:
        symbol = rng.choice(("X", "Y"))
        sign = rng.choice((-1, 1))
        runs.append([symbol, sign * magnitude])
    return {"repeat": inst["N"], "runs": runs}


def search_space(inst):
    p, count = inst["p"], inst["run_count"]
    return math.comb(p - 1, count - 1) * (4 ** count)


def enumerate_all(inst):
    total = search_space(inst)
    if total > 100_000:
        return None
    p, count = inst["p"], inst["run_count"]
    valid = 0
    for cuts in itertools.combinations(range(1, p), count - 1):
        magnitudes = [b - a for a, b in zip([0] + list(cuts), list(cuts) + [p])]
        for choices in itertools.product(range(4), repeat=count):
            runs = []
            for magnitude, choice in zip(magnitudes, choices):
                symbol = "X" if choice < 2 else "Y"
                sign = -1 if choice % 2 == 0 else 1
                runs.append([symbol, sign * magnitude])
            valid += int(verify(inst, {"repeat": inst["N"], "runs": runs})[0])
    return valid


def _element_order(inst, element):
    order = inst["p"] * inst["N"]
    for prime in [inst["p"]] + list(inst["factors"]):
        if order % prime == 0:
            trial = order // prime
            if _power(element, trial, inst["N"], inst["p"], inst["alpha"]) == (0, 0):
                order = trial
    return order


def canonical_key(inst):
    """A group-theoretic invariant under names, inversions, and conjugacy.

    Exact Cayley-graph isomorphism is not attempted.  The action orbit and the
    multiset of orders of all signed two-letter products are a strong cheap
    invariant for this generated distribution.
    """
    p = inst["p"]
    factors = sorted(inst["factors"])
    action_orbit = min(
        tuple(pow(inst["alpha"], power, prime) for prime in factors)
        for power in range(1, p)
    )
    x = tuple(inst["generators"]["X"])
    y = tuple(inst["generators"]["Y"])
    signed = [
        _power(x, 1, inst["N"], p, inst["alpha"]),
        _power(x, -1, inst["N"], p, inst["alpha"]),
        _power(y, 1, inst["N"], p, inst["alpha"]),
        _power(y, -1, inst["N"], p, inst["alpha"]),
    ]
    product_orders = sorted(
        _element_order(inst, _mul(a, b, inst["N"], p, inst["alpha"]))
        for a in signed
        for b in signed
    )
    payload = {
        "p": p,
        "factors": factors,
        "action_orbit": action_orbit,
        "signed_two_letter_orders": product_orders,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    n = params.get("n")
    spread = params.get("prime_spread")
    if not isinstance(n, int) or not isinstance(spread, int):
        return None
    if n >= 1024 or spread >= 1024:
        return None
    harder = dict(params)
    harder["n"] = n * 2
    harder["prime_spread"] = max(1, spread * 2)
    return harder


def _reference_candidate(inst):
    """Implement the paper's Case 2 construction after trying visible roles."""
    p, modulus, alpha = inst["p"], inst["N"], inst["alpha"]
    attempts = 0
    for a_name, b_name in (("X", "Y"), ("Y", "X")):
        for a_sign in (-1, 1):
            for b_sign in (-1, 1):
                attempts += 1
                a = _power(tuple(inst["generators"][a_name]), a_sign, modulus, p, alpha)
                b = _power(tuple(inst["generators"][b_name]), b_sign, modulus, p, alpha)
                if a[1] == 0:
                    continue
                k = b[1] * pow(a[1], -1, p) % p
                chunks = [
                    [b_name, b_sign],
                    [a_name, -a_sign * (k - 1)],
                    [b_name, b_sign],
                    [a_name, a_sign * (p - k - 1)],
                ]
                runs = _split_chunks(chunks, inst["run_count"])
                if runs is None:
                    continue
                candidate = {"repeat": modulus, "runs": runs}
                if verify(inst, candidate)[0]:
                    return candidate, attempts
    return None, attempts


def _balanced_candidate(inst, symbols, signs=None):
    count = inst["run_count"]
    magnitudes = _positive_parts(inst["p"], count)
    if signs is None:
        signs = [1] * count
    runs = [
        [symbols[i % len(symbols)], signs[i % len(signs)] * magnitude]
        for i, magnitude in enumerate(magnitudes)
    ]
    return {"repeat": inst["N"], "runs": runs}


def _greedy_quotient_candidate(inst):
    """A no-backtracking quotient heuristic, then a bounded run projection."""
    p = inst["p"]
    options = []
    for symbol in ("X", "Y"):
        coordinate = inst["generators"][symbol][1]
        options.extend([(symbol, 1, coordinate), (symbol, -1, -coordinate % p)])
    current = 0
    unused = set(range(1, p))
    individual = []
    for _ in range(p - 1):
        choices = []
        for symbol, sign, delta in options:
            nxt = (current + delta) % p
            if nxt in unused:
                choices.append((nxt, symbol, sign, delta))
        if not choices:
            break
        nxt, symbol, sign, _ = min(choices)
        individual.append((symbol, sign))
        unused.remove(nxt)
        current = nxt
    closing = next(
        ((symbol, sign) for symbol, sign, delta in options if (current + delta) % p == 0),
        None,
    )
    if closing is not None:
        individual.append(closing)
    # Project the heuristic to the exact L-run language; this deliberately does
    # no backtracking when its natural word has too many transitions.
    chunks = []
    for symbol, sign in individual:
        if chunks and chunks[-1][0] == symbol and (chunks[-1][1] > 0) == (sign > 0):
            chunks[-1][1] += sign
        else:
            chunks.append([symbol, sign])
    runs = _split_chunks(chunks, inst["run_count"])
    return {"repeat": inst["N"], "runs": runs} if runs is not None else _balanced_candidate(inst, ["X"])


def _attack_candidates(inst, seed):
    x_first = min(("X", "Y"), key=lambda name: tuple(inst["generators"][name]))
    rrng = random.Random(seed ^ 0x210714787)
    return {
        "outlier_lexicographically_smaller_generator": [
            _balanced_candidate(inst, [x_first])
        ],
        "single_generator_positive_period": [
            _balanced_candidate(inst, ["X"]),
            _balanced_candidate(inst, ["Y"]),
        ],
        "alternating_positive_generators": [
            _balanced_candidate(inst, ["X", "Y"])
        ],
        "greedy_smallest_unvisited_quotient": [_greedy_quotient_candidate(inst)],
        "random_restart_4096_bounded_words": [
            random_candidate(inst, rrng) for _ in range(4096)
        ],
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    modulus, p, alpha = inst["N"], inst["p"], inst["alpha"]
    variants = []
    h = (rng.randrange(modulus), rng.randrange(p))
    h_inv = _inverse(h, modulus, p, alpha)
    for mask in range(1, 8):
        out = {
            key: json.loads(json.dumps(value))
            for key, value in inst.items()
        }
        carried = json.loads(json.dumps(inst["answer"]))
        if mask & 1:
            out["generators"] = {
                "X": list(inst["generators"]["Y"]),
                "Y": list(inst["generators"]["X"]),
            }
            for run in carried["runs"]:
                run[0] = "Y" if run[0] == "X" else "X"
        if mask & 2:
            gx = tuple(out["generators"]["X"])
            out["generators"]["X"] = list(_inverse(gx, modulus, p, alpha))
            for run in carried["runs"]:
                if run[0] == "X":
                    run[1] = -run[1]
        if mask & 4:
            for name in ("X", "Y"):
                generator = tuple(out["generators"][name])
                conjugate = _mul(_mul(h_inv, generator, modulus, p, alpha), h, modulus, p, alpha)
                out["generators"][name] = list(conjugate)
        out["answer"] = carried
        variants.append(out)
    return variants


def _materialize_lift_checksum(inst, answer):
    """Execute the O(|G|) ordinary lift without retaining its huge vertex list."""
    modulus, p, alpha = inst["N"], inst["p"], inst["alpha"]
    alpha_powers = [pow(alpha, i, modulus) for i in range(p)]
    steps = []
    for symbol, exponent in answer["runs"]:
        generator = tuple(inst["generators"][symbol])
        step = _power(generator, 1 if exponent > 0 else -1, modulus, p, alpha)
        steps.extend([step] * abs(exponent))
    position = (0, 0)
    checksum = 0
    operations = 0
    for _ in range(answer["repeat"]):
        for sx, si in steps:
            x, i = position
            checksum = (checksum + x + 3 * i) & ((1 << 64) - 1)
            position = ((x + alpha_powers[i] * sx) % modulus, (i + si) % p)
            operations += 1
    return position, checksum, operations


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
        "certificate_language": CERTIFICATE_LANGUAGE,
    }
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    exact_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
            primes = [inst["p"]] + inst["factors"]
            structural = (
                len(set(primes)) == 4
                and all(prime % 2 == 1 and _is_prime_64(prime) for prime in primes)
                and pow(inst["alpha"], inst["p"], inst["N"]) == 1
                and math.gcd(inst["alpha"] - 1, inst["N"]) == 1
            )
            exact_checks += int(structural)
    report["G1_planted_verifies"] = {
        "pass": not failures and exact_checks == 12,
        "attempts": 12,
        "exact_group_structure_checks": exact_checks,
        "failures": failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = json.loads(json.dumps(inst["answer"]))
    drop = json.loads(json.dumps(answer))
    drop["runs"].pop()
    empty = []
    out_of_range = json.loads(json.dumps(answer))
    out_of_range["runs"][0][1] = inst["p"] + 1
    duplicate = json.loads(json.dumps(answer))
    largest = max(range(len(duplicate["runs"])), key=lambda i: abs(duplicate["runs"][i][1]))
    duplicate["runs"][largest] = list(duplicate["runs"][0])
    swapped = None
    for i in range(len(answer["runs"])):
        for j in range(i + 1, len(answer["runs"])):
            trial = json.loads(json.dumps(answer))
            trial["runs"][i], trial["runs"][j] = trial["runs"][j], trial["runs"][i]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions = {
        "drop": drop,
        "swap": swapped,
        "duplicate": duplicate,
        "empty": empty,
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values()) and len(set(reasons)) == 5,
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The quotient residues close and the voltage is primitive.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThis is the compressed lift."
    )
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("there is no tagged JSON here") is None
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0] and garbage_none,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": garbage_none,
    }

    guess_rng = random.Random(0x210714787)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform compositions of p into L positive run lengths, with uniform signed X/Y choices and the mandated repeat",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_lexicographically_smaller_generator",
        "single_generator_positive_period",
        "alternating_positive_generators",
        "greedy_smallest_unvisited_quotient",
        "random_restart_4096_bounded_words",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_attempts = 0
    reference_seconds = 0.0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            started = time.perf_counter()
            success = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - started
            successes[name] += int(success)
        started = time.perf_counter()
        recovered, attempts = _reference_candidate(trial)
        reference_seconds += time.perf_counter() - started
        reference_attempts += attempts
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference_inst = make_instance(seed=0, **shipping)
    material_operations = reference_inst["p"] * reference_inst["N"]
    symbolic_started = time.perf_counter()
    recovered, orientation_attempts = _reference_candidate(reference_inst)
    symbolic_seconds = time.perf_counter() - symbolic_started
    recovered_ok = recovered is not None and verify(reference_inst, recovered)[0]
    reference = {
        "name": "paper Case 2 constructor in compressed exponent notation",
        "complexity": "O(p log N) exact arithmetic for the compressed certificate; O(pqrs) to materialize the ordinary cycle",
        "wall_clock_sec": round(symbolic_seconds, 6),
        "operations": orientation_attempts * reference_inst["p"],
        "ordinary_lift_materialization_operations": material_operations,
        "symbolic_orientation_trials_average": reference_attempts / 8,
        "seed_0_orientation_trials": orientation_attempts,
        "compressed_candidate_verifies": recovered_ok,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(successes[name] == 0 for name in attack_names)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and recovered_ok,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "recognize the quotient period and test its voltage",
            "operations_upper_bound": 248,
            "reference_symbolic_solves": f"{reference_successes}/8",
        },
    }

    demo_inst = make_instance(seed=4, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    strongest_name = "random_restart_4096_bounded_words"
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and demo_count is not None and demo_count > 0 and all_failed,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_attack": strongest_name,
        "baseline_attack_iterations": 4096,
        "baseline_attack_wall_clock_sec": round(attack_seconds[strongest_name] / 8, 6),
        "reference_operation_count": reference["operations"],
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "ordinary_lift_materialization_operations": material_operations,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_params["prime_spread"] *= 2
    started = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - started
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_sizes = []
    for name in ("easy", "medium", "hard"):
        sample = make_instance(seed=5, **DIFFICULTY[name])
        ladder_sizes.append(sample["p"] * sample["N"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["p"] * doubled["N"] > inst["p"] * inst["N"]
        and ladder_sizes == sorted(ladder_sizes)
        and len(set(ladder_sizes)) == 3
        and search_space(doubled) == search_space(inst),
        "shipping_vertices_seed_19": inst["p"] * inst["N"],
        "doubled_vertices_seed_77": doubled["p"] * doubled["N"],
        "fixed_answer_space": search_space(doubled),
        "ladder_vertices_seed_5": ladder_sizes,
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
    }

    invariant = 0
    carried = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant += int(canonical_key(transformed) == key)
            carried += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant == 140 and carried == 140 and distinct == 20,
        "invariant_relabellings": invariant,
        "real_transformations_verified": carried,
        "unrelated_distinct_keys": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "swap generator names with carried word",
            "invert one undirected generator with carried exponent signs",
            "simultaneous inner automorphism (conjugation)",
            "all nonempty compositions of those three",
        ],
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    worst = {
        # The seed-derived band is reduced modulo 1,000,003, so all supported
        # shipping repeats have fewer than 10^30 possibilities/digits.
        "repeat": 10**30 - 1,
        "runs": [["X", -inst["p"]] for _ in range(inst["run_count"])],
    }
    worst_chars = len(json.dumps(worst, separators=(",", ":")))
    worst_tokens = math.ceil(worst_chars / 4)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    have_arms = all(arms[name]["attempts"] >= 3 for name in arms)
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    answer_elements = _answer_atoms(inst["answer"])
    within_caps = (
        len(encoded) <= 2000
        and answer_elements <= 256
        and 248 <= 300
        and worst_tokens == PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        # The three arms, including the hinted arm, are diagnostics as of
        # 2026-09-05.  Only the answer/effort caps remain gating.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate if have_arms else None,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(encoded),
        "answer_tokens": math.ceil(len(encoded) / 4),
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": 248,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
