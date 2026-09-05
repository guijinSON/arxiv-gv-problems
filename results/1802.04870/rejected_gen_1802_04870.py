"""Rejected Track-B generator for the RAAG direct-product secret-sharing problem.

Source: Flores, Kahrobaei, and Koberda, arXiv:1802.04870.  Section 4
identifies maximal join factors of a defining graph with maximal direct-product
factors of its right-angled Artin group and computes them as components of the
complement graph.  Section 6.3.1 uses those factor counts as values of a monic
polynomial; its constant term is the secret.

Generation is inverse.  It chooses factor counts first, interpolates the unique
monic polynomial implicitly, and realizes every count as the number of orbits
of a cyclic noncommutation rule conjugated by an exact Feistel permutation.  No
generated instance is solved to obtain its planted certificate.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "graph",
    "certificate_form": "rational",
    "native_objects": [
        "right-angled Artin group presentations by exact permuted cyclic commutation rules",
        "maximal direct-product decompositions",
        "a monic polynomial over Q",
        "an exact rational secret",
    ],
    "verification_operations": [
        "syntactic validation of exact Feistel relabellings",
        "integer gcd for complement-component counts",
        "exact binomial-coefficient interpolation",
        "reduced rational comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Theorem 4.1 and Proposition 4.2: direct-product factors "
        "of A(Gamma) correspond to connected components of the complement "
        "of Gamma"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A Feistel map only relabels each enormous cyclic noncommutation graph, "
        "so its orbit count and the consecutive-node interpolation identity "
        "replace explicit graph construction."
    ),
    "hardness_basis": (
        "Track B: Proposition 4.2 gives complement construction plus connected "
        "components in polynomial time, implemented here in O(sum_i rounds*N_i + "
        "N_i*alpha(N_i)); at easy seed 271828 it uses 327,680 edge iterations "
        "and 2,621,440 Feistel-round evaluations in 0.6--1.2 local seconds "
        "across repeated audits, whereas "
        "recognizing the relabeling, reading each orbit count from the step's "
        "lowest set bit, and interpolating takes at most 127 exact operations "
        "over the eight-seed shipping audit."
    ),
    "max_answer_tokens": 6,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A reduced exact rational [numerator, denominator] with denominator "
        "exactly 1 and numerator in the displayed inclusive interval [-B,B]."
    ),
    "bounds": {
        "shape": 2,
        "denominator": 1,
        "numerator_interval": "[-answer_bound, answer_bound]",
        "answer_bound_formula": "degree! + 32*(2^degree - 1)",
        "max_factor_count": 32,
        "reduced": True,
    },
}


DIFFICULTY = {
    "demo": {"n": 8, "degree": 4, "variations": 1, "rounds": 2},
    "easy": {"n": 14, "degree": 20, "variations": 20, "rounds": 4},
    "medium": {"n": 16, "degree": 24, "variations": 24, "rounds": 6},
    "hard": {"n": 18, "degree": 28, "variations": 28, "rounds": 8},
}

SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "The displayed Feistel map changes only the vertex labels of each "
    "noncommutation graph."
)

PLACEBO_HINT = (
    "Each presentation line is exact, and careful attention to the order of "
    "its parameters prevents mistakes."
)


# Filled only from transcripts produced by scripts/harden.py.  These are G9
# diagnostics, not gates; only the answer/route caps contribute to G9 ``pass``.
G9_ORACLE_RESULTS = {
    # HTTP/API errors do not consume scored attempts.  The preserved transcript
    # files contain the failed requests; these counters remain zero until a
    # model actually receives and answers a prompt.
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


NOTES = r"""
Definition and construction source.  Section 4 defines graph joins and maximal
join decompositions.  Theorem 4.1 states that A(Gamma) is a nontrivial direct
product exactly when Gamma is a nontrivial join.  Proposition 4.2 proves that
maximal join factors are the connected components of the complement graph.
Section 6.3.1 then gives the exact secret-sharing construction used here: the
i-th participant computes a maximal join-factor count m_i=f(i) for an unknown
monic polynomial f of degree n, and the secret is f(0).

Easy-result triage.  Proposition 4.2 explicitly gives a polynomial-time
algorithm: form the complement and merge the endpoints of every complement
edge.  Therefore Track A would be false.  This module is Track B and implements
that union-find method as the successful reference algorithm.  The cyclic input
presentation makes the paper algorithm perform one merge attempt per generator,
while the compact route recognizes that the complement edges are translations
by one step and obtains the component count by gcd.

Generation.  Small power-of-two counts m_i are sampled first.  For each count,
take N=2^n and an exact step s=m_i a with a odd, so gcd(N,s)=m_i.  The complement
edges are then carried through an independently keyed Feistel permutation P:
they are {P(z),P(z+s)}.  Feistel rounds are bijections, so this is a
structure-preserving transformation of a known disjoint union of m_i cycles.
The RAAG defining graph is connected because every generated m_i is at least
four, hence its complement has several components and the defining graph joins
them.  This is inverse generation and transformation of known instances, not
solution of generated instances.

Attack hardening.  All shipping factor counts vary and every Feistel key is
sampled independently, so there is no distinguished planted line.  Unit changes,
reflection, fresh Feistel keys, and line reordering preserve the answer.  Dense
factor-count variation defeats the extreme-step and modal one-count guesses;
the truncated interpolation omits ten independently varied shares; and uniform
rational restart samples a language with about 4.9e18 candidates.  All four are
measured over eight seeds.  The standard union-find algorithm is expected to
solve and is reported separately, as Track B requires.

Hardening history and rejection.  The first draft used an exposed cyclic rule
and made most factor counts equal.  The revised version carries the same known
cycle unions through independently keyed Feistel relabellings and varies every
shipping count.  A fresh script-owned oracle run on 2026-09-05 reached both
vendors and defeated every named preset plus all three supported fixed-answer-
length escalations.  Twelve of eighteen calls returned verified witnesses; at
the final n=24, degree=28, rounds=14 level all three calls solved.  The harness
therefore recorded ``too_easy``.  This preserved module passes the local G and
V gates, but the proposed family fails H on Track B and must not be shipped.
""".strip()


_COUNT_BOUND = 32
_FACTOR_COUNTS = (4, 8, 16, 32)


def _factorial(n):
    value = 1
    for k in range(2, n + 1):
        value *= k
    return value


def _language_bound(degree):
    # |sum (-1)^(i-1) C(d,i)m_i| <= M(2^d-1).
    return _factorial(degree) + _COUNT_BOUND * ((1 << degree) - 1)


def _secret_from_values(values):
    """Constant term of the unique monic degree-d polynomial through f(i)."""

    degree = len(values)
    total = _factorial(degree) if degree % 2 == 0 else -_factorial(degree)
    for point, value in enumerate(values, 1):
        weight = math.comb(degree, point)
        if point % 2 == 0:
            weight = -weight
        total += weight * value
    return total


def _gcd_with_steps(a, b):
    steps = 0
    while b:
        a, b = b, a % b
        steps += 1
    return abs(a), steps


def _rotl(value, width):
    """Rotate an unsigned ``width``-bit integer left by one place."""

    mask = (1 << width) - 1
    return ((value << 1) & mask) | (value >> (width - 1))


def _feistel_permute(value, bits, round_keys):
    """Exact balanced Feistel permutation used only to relabel vertices."""

    half = bits // 2
    mask = (1 << half) - 1
    left, right = value >> half, value & mask
    for key in round_keys:
        mixed = (right * (2 * key + 1) + key) & mask
        function = mixed ^ _rotl(right, half)
        left, right = right, left ^ function
    return (left << half) | right


def make_instance(n, seed=0, **params):
    """Inverse-generate a Section 6.3.1 RAAG secret-sharing instance.

    ``n`` is the even vertex-label bit width.  It controls the graph size—and
    therefore the paper algorithm's work—without increasing the answer shape.
    """

    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if n > 24:
        raise ValueError("n above 24 is outside the supported exact language")
    degree = params.pop("degree", 20)
    variations = params.pop("variations", degree)
    rounds = params.pop("rounds", 4)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 4:
        raise ValueError("degree must be an integer at least 4")
    if degree % 2:
        raise ValueError("degree must be even")
    if isinstance(variations, bool) or not isinstance(variations, int):
        raise ValueError("variations must be an integer")
    if not (1 <= variations <= degree):
        raise ValueError("variations must lie in 1..degree")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 2:
        raise ValueError("rounds must be an integer at least 2")
    if rounds > 16:
        raise ValueError("rounds above 16 are outside the supported language")

    rng = random.Random(seed)
    baseline = rng.choice(_FACTOR_COUNTS)

    # For non-demo instances put at least one variation in each half.  The
    # remaining positions are uniformly selected; all values come from the same
    # factor-count alphabet, so no presentation is marked as the plant.
    if variations == 1:
        positions = [rng.randrange(degree)]
    else:
        positions = [rng.randrange(degree // 2),
                     rng.randrange(degree // 2, degree)]
        remaining = [p for p in range(degree) if p not in positions]
        rng.shuffle(remaining)
        positions.extend(remaining[:variations - 2])
    positions = sorted(set(positions))
    while len(positions) < variations:
        candidate = rng.randrange(degree)
        if candidate not in positions:
            positions.append(candidate)
    positions.sort()

    values = [baseline] * degree
    for position in positions:
        choices = [value for value in _FACTOR_COUNTS if value != baseline]
        values[position] = rng.choice(choices)
    if not all(value in _FACTOR_COUNTS for value in values):
        raise AssertionError("internal count construction failed")

    generators = 1 << n
    half_mask = (1 << (n // 2)) - 1
    graphs = []
    for point, count in enumerate(values, 1):
        cycle_length = generators // count
        unit = rng.randrange(cycle_length)
        unit |= 1
        if unit >= cycle_length:
            unit -= 2
        step = count * unit
        round_keys = [rng.randrange(half_mask + 1) for _ in range(rounds)]
        if math.gcd(generators, step) != count:
            raise AssertionError("internal orbit-count construction failed")
        graphs.append({
            "point": point,
            "generators": generators,
            "noncommuting_step": step,
            "round_keys": round_keys,
        })

    # The line order is representation only and carries no interpolation data.
    rng.shuffle(graphs)
    secret = _secret_from_values(values)
    bound = _language_bound(degree)
    if abs(secret) > bound:
        raise AssertionError("internal answer bound failed")
    return {
        "degree": degree,
        "label_bits": n,
        "feistel_rounds": rounds,
        "graphs": graphs,
        "count_bound": _COUNT_BOUND,
        "answer_bound": bound,
        "answer": [secret, 1],
    }


def render(inst):
    lines = [
        "Recover the exact secret in a right-angled Artin group sharing instance.",
        "",
        "A right-angled Artin group A(Gamma) has one generator for each vertex of",
        "a finite simple graph Gamma.  Two distinct generators commute exactly when",
        "their vertices are adjacent.  A join Gamma=Gamma_1*...*Gamma_r partitions",
        "the vertices into nonempty parts so every pair from different parts is",
        "adjacent.  A maximal join decomposition is one whose parts cannot be split",
        "again; its r parts give the maximal direct-product factors of A(Gamma).",
        "",
        "Below, every presentation has N=2^w generators x_(i,0),...,x_(i,N-1).",
        "Each line supplies i, s, and a comma-separated list of Feistel keys.",
        "To define its map P, put h=w/2 and split z=L*2^h+R with h-bit L,R.",
        "For each key k from left to right, set",
        "  M = (R*(2*k+1)+k) mod 2^h,",
        "  F = M XOR rotl_h(R,1),  and  (L,R) = (R,L XOR F).",
        "Here XOR is bitwise exclusive-or and rotl_h rotates an h-bit word left",
        "by one bit.  After all keys have been processed, P(z)=L*2^h+R.",
        "Distinct generators x_(i,a),x_(i,b) fail to commute exactly when there",
        "is a z in {0,...,N-1} with {a,b}={P(z),P((z+s) mod N)}; every other",
        "distinct pair commutes.  Thus each line is a complete exact RAAG",
        "presentation, not a sample.  Subscripts are zero-based and lines may",
        "appear in any order.",
        "",
        f"There is a unique polynomial f of degree exactly {inst['degree']} with rational",
        "coefficients and leading coefficient 1 (this is what 'monic' means),",
        "such that f(i)=m_i for i=1,...,d, where m_i is the number of maximal",
        "direct-product factors of presentation i and d is the displayed degree.",
        "Find the secret f(0).  Intervals and bounds below are inclusive.",
        "",
        f"degree d = {inst['degree']}",
        f"label bit width w = {inst['label_bits']} (so N = {1 << inst['label_bits']})",
        f"Feistel rounds per presentation = {inst['feistel_rounds']}",
        f"answer numerator bound B = {inst['answer_bound']}",
        "presentation lines (i s keys):",
    ]
    for graph in inst["graphs"]:
        lines.append(
            f"  {graph['point']} {graph['noncommuting_step']} "
            + ",".join(str(key) for key in graph["round_keys"])
        )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Return one reduced exact rational num/den with gcd(|num|,den)=1,",
        "den>0, den exactly 1, and -B <= num <= B.  The JSON certificate stored",
        "by the generator is [num,den], but the answer block uses num/den text.",
        "",
        "Give your final answer inside <answer></answer> tags, as num/den.",
        "Example: <answer>-37/1</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    try:
        tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
        payload = tagged[-1].strip() if tagged else text.strip()
        fences = re.findall(r"```(?:json|text)?\s*([\s\S]*?)\s*```", payload, re.I)
        if fences:
            payload = fences[-1].strip()
        json_pairs = re.findall(r"\[\s*[-+]?\d+\s*,\s*[-+]?\d+\s*\]", payload)
        if json_pairs:
            value = json.loads(json_pairs[-1])
            if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
                return None
            return value
        fractions = re.findall(r"(?<![\w.])([-+]?\d+)\s*/\s*([-+]?\d+)(?![\w.])", payload)
        if fractions:
            num, den = fractions[-1]
            return [int(num), int(den)]
        return None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _instance_values(inst):
    try:
        degree = inst["degree"]
        label_bits = inst["label_bits"]
        feistel_rounds = inst["feistel_rounds"]
        graphs = inst["graphs"]
        count_bound = inst["count_bound"]
        answer_bound = inst["answer_bound"]
    except (KeyError, TypeError):
        return None, "malformed instance"
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 1:
        return None, "malformed degree"
    if (isinstance(label_bits, bool) or not isinstance(label_bits, int)
            or label_bits < 8 or label_bits > 24 or label_bits % 2):
        return None, "malformed label bit width"
    if (isinstance(feistel_rounds, bool) or not isinstance(feistel_rounds, int)
            or not (2 <= feistel_rounds <= 16)):
        return None, "malformed Feistel round count"
    if not isinstance(graphs, list) or len(graphs) != degree:
        return None, "wrong number of presentations"
    if count_bound != _COUNT_BOUND or answer_bound != _language_bound(degree):
        return None, "inconsistent certificate bound"
    values = [None] * degree
    for graph in graphs:
        if not isinstance(graph, dict):
            return None, "malformed presentation line"
        try:
            point = graph["point"]
            generators = graph["generators"]
            step = graph["noncommuting_step"]
            round_keys = graph["round_keys"]
        except KeyError:
            return None, "malformed presentation line"
        if any(isinstance(v, bool) or not isinstance(v, int)
               for v in (point, generators, step)):
            return None, "noninteger presentation datum"
        if not (1 <= point <= degree) or values[point - 1] is not None:
            return None, "repeated or out-of-range interpolation point"
        if generators < 5 or not (0 < step < generators):
            return None, "invalid cyclic presentation"
        if generators != 1 << label_bits:
            return None, "generator count disagrees with label bit width"
        key_bound = 1 << (label_bits // 2)
        if (not isinstance(round_keys, list)
                or len(round_keys) != feistel_rounds
                or any(isinstance(key, bool) or not isinstance(key, int)
                       or not (0 <= key < key_bound) for key in round_keys)):
            return None, "invalid Feistel key list"
        count = math.gcd(generators, step)
        cycle_length = generators // count
        if cycle_length < 5:
            return None, "presentation is outside the connected-RAAG regime"
        if count not in _FACTOR_COUNTS or count > count_bound:
            return None, "factor count is outside the declared alphabet"
        values[point - 1] = count
    if any(value is None for value in values):
        return None, "missing interpolation point"
    return values, "ok"


def verify(inst, answer):
    values, reason = _instance_values(inst)
    if values is None:
        return False, reason
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != 2:
        return False, "rational must contain exactly two integers"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "rational entries must be integers"
    numerator, denominator = answer
    if denominator <= 0:
        return False, "denominator must be positive"
    if math.gcd(abs(numerator), denominator) != 1:
        return False, "rational must be reduced"
    if denominator != 1:
        return False, "this certificate language requires denominator 1"
    if abs(numerator) > inst["answer_bound"]:
        return False, "numerator is outside the declared inclusive bound"
    expected = _secret_from_values(values)
    if numerator != expected:
        return False, "incorrect polynomial secret"
    return True, "ok"


def random_candidate(inst, rng):
    bound = inst["answer_bound"]
    return [rng.randrange(-bound, bound + 1), 1]


def search_space(inst):
    return 2 * inst["answer_bound"] + 1


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    valid = 0
    bound = inst["answer_bound"]
    for numerator in range(-bound, bound + 1):
        if verify(inst, [numerator, 1])[0]:
            valid += 1
    return valid


def canonical_key(inst):
    """Complete key for this cyclic family, invariant under generator relabelling."""

    values, reason = _instance_values(inst)
    if values is None:
        payload = {"invalid": reason}
    else:
        presentations = []
        for graph in inst["graphs"]:
            generators = graph["generators"]
            components = math.gcd(generators, graph["noncommuting_step"])
            presentations.append([
                graph["point"],
                generators,
                components,
                generators // components,
            ])
        payload = {
            "degree": inst["degree"],
            "presentations": sorted(presentations),
        }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    """Grow the implicit RAAGs while preserving the two-atom certificate."""

    harder = dict(params)
    n = int(harder.get("n", 16))
    rounds = int(harder.get("rounds", 4))
    if n >= 24 or rounds >= 16:
        return None
    # Two bits quadruple every graph; two more Feistel rounds increase the work
    # per edge.  Degree and answer shape stay fixed: only the haystack grows.
    harder["n"] = n + 2
    harder["rounds"] = rounds + 2
    return harder


def _reference_component_count(generators, step, bits, round_keys):
    """Proposition 4.2 literally: merge every edge of the complement graph."""

    parent = list(range(generators))
    size = [1] * generators
    links = 0

    def find(vertex):
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for vertex in range(generators):
        left = find(_feistel_permute(vertex, bits, round_keys))
        right = find(_feistel_permute(
            (vertex + step) % generators, bits, round_keys
        ))
        if left != right:
            if size[left] < size[right]:
                left, right = right, left
            parent[right] = left
            size[left] += size[right]
            links += 1
    return generators - links, generators


def _reference_solve(inst):
    values = [None] * inst["degree"]
    edge_iterations = 0
    for graph in inst["graphs"]:
        count, iterations = _reference_component_count(
            graph["generators"], graph["noncommuting_step"],
            inst["label_bits"], graph["round_keys"]
        )
        values[graph["point"] - 1] = count
        edge_iterations += iterations
    return [_secret_from_values(values), 1], edge_iterations


def _compact_solve(inst):
    """Intended structural route, with conservative exact-operation accounting."""

    values = [None] * inst["degree"]
    operations = 0
    for graph in inst["graphs"]:
        # N is a power of two and the multiplier used in ``step`` is odd, so
        # gcd(N,step) is exactly the lowest set bit.  Count that as one exact
        # bit operation rather than expanding the graph or running Euclid.
        step = graph["noncommuting_step"]
        count = step & -step
        values[graph["point"] - 1] = count
        operations += 1

    # Any reference value works because the consecutive-node Lagrange weights
    # sum to one.  Choosing a mode saves arithmetic.  Comparisons are not exact
    # arithmetic operations; every subtraction below is counted.
    frequencies = {}
    for value in values:
        frequencies[value] = frequencies.get(value, 0) + 1
    baseline = max(frequencies, key=lambda v: (frequencies[v], -v))

    factorial = 1
    for factor in range(2, inst["degree"] + 1):
        factorial *= factor
        operations += 1

    binomials = []
    coefficient = 1
    for point in range(1, inst["degree"] + 1):
        coefficient = coefficient * (inst["degree"] - point + 1) // point
        operations += 2
        binomials.append(coefficient)

    correction = 0
    for point, value in enumerate(values, 1):
        deviation = value - baseline
        operations += 1
        if deviation:
            signed_weight = binomials[point - 1] if point % 2 else -binomials[point - 1]
            correction += signed_weight * deviation
            operations += 2
    secret = (factorial if inst["degree"] % 2 == 0 else -factorial)
    secret += baseline + correction
    operations += 2
    return [secret, 1], operations


def _values_fast(inst):
    values = [None] * inst["degree"]
    for graph in inst["graphs"]:
        values[graph["point"] - 1] = math.gcd(
            graph["generators"], graph["noncommuting_step"]
        )
    return values


def _attack_factorial_only(inst):
    value = _factorial(inst["degree"])
    if inst["degree"] % 2:
        value = -value
    return [value, 1]


def _attack_extreme_step(inst):
    graph = max(inst["graphs"], key=lambda g: (g["noncommuting_step"], -g["point"]))
    count = math.gcd(graph["generators"], graph["noncommuting_step"])
    return [_attack_factorial_only(inst)[0] + count, 1]


def _attack_modal_greedy(inst):
    values = _values_fast(inst)
    mode = max(set(values), key=lambda v: (values.count(v), -v))
    return [_attack_factorial_only(inst)[0] + mode, 1]


def _attack_truncated_interpolation(inst):
    values = _values_fast(inst)
    mode = max(set(values), key=lambda v: (values.count(v), -v))
    cutoff = inst["degree"] // 2
    guess = _attack_factorial_only(inst)[0] + mode
    for point in range(1, cutoff + 1):
        deviation = values[point - 1] - mode
        weight = math.comb(inst["degree"], point)
        if point % 2 == 0:
            weight = -weight
        guess += weight * deviation
    return [guess, 1]


def _transformed(inst, multiplier=1, reflect=False, rekey=False,
                 reorder=False, seed=0):
    rng = random.Random(seed)
    result = {key: value for key, value in inst.items()
              if key not in {"graphs", "answer"}}
    graphs = []
    for graph in inst["graphs"]:
        generators = graph["generators"]
        unit = multiplier % generators
        if math.gcd(unit, generators) != 1:
            unit = 1
        step = (unit * graph["noncommuting_step"]) % generators
        if reflect:
            step = generators - step
        graphs.append({
            "point": graph["point"],
            "generators": generators,
            "noncommuting_step": step,
            "round_keys": (
                [rng.randrange(1 << (inst["label_bits"] // 2))
                 for _ in graph["round_keys"]]
                if rekey else list(graph["round_keys"])
            ),
        })
    if reorder:
        rng.shuffle(graphs)
    result["graphs"] = graphs
    result["answer"] = list(inst["answer"])
    return result


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)
    answer = inst["answer"]

    # Exercise the five corruption forms required by G2.  A two-coordinate
    # rational needs an explicit empty case so dropping one coordinate and
    # dropping both coordinates have distinct diagnostics.
    corruptions = {
        "drop_one": [answer[0]],
        "swap": [answer[1], answer[0]],
        "duplicate": [answer[0], answer[0]],
        "empty": [],
        "out_of_range": [inst["answer_bound"] + 1, 1],
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
                and len(set(reasons)) == len(cases),
        "attempts": len(cases),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    response = (
        "The cyclic factors and interpolation give the following exact value.\n"
        "```text\n<answer>"
        + f"{answer[0]}/{answer[1]}"
        + "</answer>\n```\nThis fraction is reduced."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_fence": True,
    }

    trials = 200_000
    rng = random.Random(0x180204870)
    hits = 0
    shipping_values, shipping_values_reason = _instance_values(inst)
    if shipping_values is None:
        raise AssertionError(shipping_values_reason)
    expected_numerator = _secret_from_values(shipping_values)
    started = time.perf_counter()
    for _ in range(trials):
        candidate = random_candidate(inst, rng)
        # The candidate sampler already guarantees every language constraint,
        # so validity reduces to this exact comparison.  Avoid reparsing the
        # unchanged instance 200,000 times; verify() itself is exercised by G1–G3.
        if candidate == [expected_numerator, 1]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    sampled_probability = hits / trials
    exact_probability = 1 / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": trials >= 200_000 and exact_probability < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": sampled_probability,
        "exact_probability": exact_probability,
        "exact_valid_answers": 1,
        "candidate_space": search_space(inst),
        "prior": "uniform over every reduced denominator-one rational in [-B,B]",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline_started = time.perf_counter()
    baseline_answer = _attack_truncated_interpolation(inst)
    baseline_success = verify(inst, baseline_answer)[0]
    baseline_seconds = time.perf_counter() - baseline_started

    reference_started = time.perf_counter()
    reference_answer, reference_iterations = _reference_solve(inst)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = verify(inst, reference_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count == 1 and reference_ok and not baseline_success,
        "shipping_seed": 271828,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_solution_density": exact_probability,
        "shipping_sample_density": sampled_probability,
        "shipping_exact_valid_answers": 1,
        "shipping_candidate_space": search_space(inst),
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "in-context truncated interpolation",
        "baseline_shares_used": inst["degree"] // 2,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_wall_clock_sec": round(reference_seconds, 6),
        "reference_edge_iterations": reference_iterations,
        "reference_feistel_round_evaluations": (
            2 * inst["feistel_rounds"] * reference_iterations
        ),
    }

    attacks = {
        "outlier_extreme_noncommuting_step": {"successes": 0, "attempts": 8},
        "greedy_modal_factor_count": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "in_context_truncated_interpolation": {"successes": 0, "attempts": 8},
    }
    attack_times = {name: 0.0 for name in attacks}
    reference_times = []
    reference_operations = []
    reference_successes = 0
    compact_operations = []
    compact_successes = 0
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping)
        candidate_builders = {
            "outlier_extreme_noncommuting_step": _attack_extreme_step,
            "greedy_modal_factor_count": _attack_modal_greedy,
            "in_context_truncated_interpolation": _attack_truncated_interpolation,
        }
        for name, builder in candidate_builders.items():
            start = time.perf_counter()
            candidate = builder(current)
            attack_times[name] += time.perf_counter() - start
            if verify(current, candidate)[0]:
                attacks[name]["successes"] += 1

        start = time.perf_counter()
        rr_rng = random.Random(seed ^ 0xA5A5A5)
        rr_answer = None
        for _ in range(256):
            candidate = random_candidate(current, rr_rng)
            if verify(current, candidate)[0]:
                rr_answer = candidate
                break
        attack_times["random_restart_256"] += time.perf_counter() - start
        if rr_answer is not None:
            attacks["random_restart_256"]["successes"] += 1

        start = time.perf_counter()
        reference_answer, iterations = _reference_solve(current)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(iterations)
        if verify(current, reference_answer)[0]:
            reference_successes += 1

        compact_answer, operations = _compact_solve(current)
        compact_operations.append(operations)
        if verify(current, compact_answer)[0]:
            compact_successes += 1

    for name in attacks:
        attacks[name]["wall_clock_sec"] = round(attack_times[name], 6)
    all_failed = all(result["successes"] == 0 and result["attempts"] >= 8
                     for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Proposition 4.2 complement-edge union-find after Feistel evaluation",
            "complexity": "O(sum rounds*N_i + N_i*alpha(N_i)) exact operations",
            "solves": f"{reference_successes}/8, as expected",
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_operations) * (1 + 2 * shipping["rounds"]),
            "operation_unit": (
                "edge iterations plus Feistel round evaluations across eight instances"
            ),
            "edge_iterations": sum(reference_operations),
            "feistel_round_evaluations": (
                2 * shipping["rounds"] * sum(reference_operations)
            ),
            "per_instance_edge_iterations": reference_operations,
        },
        "intended_compact_route": {
            "name": "Feistel-invariant lowest-set-bit counts plus interpolation",
            "solves": f"{compact_successes}/8",
            "exact_operations": compact_operations,
            "maximum_exact_operations": max(compact_operations),
        },
    }

    doubled = dict(shipping)
    doubled["n"] = shipping["n"] + 2
    doubled["rounds"] = shipping["rounds"] + 2
    doubled_inst = make_instance(seed=271828, **doubled)
    doubled_ok, doubled_reason = verify(doubled_inst, doubled_inst["answer"])
    shipping_edges = sum(graph["generators"] for graph in inst["graphs"])
    doubled_edges = sum(graph["generators"] for graph in doubled_inst["graphs"])
    shipping_work = shipping_edges * (1 + 2 * shipping["rounds"])
    doubled_work = doubled_edges * (1 + 2 * doubled["rounds"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_work > shipping_work,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_reference_edge_iterations": shipping_edges,
        "doubled_reference_edge_iterations": doubled_edges,
        "shipping_reference_operations": shipping_work,
        "doubled_reference_operations": doubled_work,
        "answer_atoms_shipping": _answer_atoms(inst["answer"]),
        "answer_atoms_doubled": _answer_atoms(doubled_inst["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_failures = []
    invariant_checks = 0
    real_transformations = 0
    for seed in range(20):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        transformations = [
            _transformed(original, multiplier=3),
            _transformed(original, reflect=True),
            _transformed(original, multiplier=5, reflect=True, rekey=True,
                         reorder=True,
                         seed=seed ^ 91),
            _transformed(original, rekey=True, reorder=True, seed=seed ^ 137),
        ]
        for transformed in transformations:
            invariant_checks += 1
            same = canonical_key(transformed) == key
            carried = verify(transformed, original["answer"])[0]
            real_transformations += int(carried)
            if not same or not carried:
                invariant_failures.append({
                    "seed": seed,
                    "same_key": same,
                    "carried_answer_verifies": carried,
                })
    unrelated = [canonical_key(make_instance(seed=50_000 + seed, **shipping))
                 for seed in range(20)]
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated)) == 20,
        "invariance_checks": invariant_checks,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "failures": invariant_failures,
        "scope": (
            "complete for line reordering, Feistel rekeying, and every odd-unit/"
            "reflection relabelling; keyed by cycle-component isomorphism type"
        ),
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(answer)
    compact_answer, seed_operations = _compact_solve(inst)
    intended_operations = max(compact_operations + [seed_operations])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and verify(inst, compact_answer)[0]
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    difference = None
    if (isinstance(hinted, int) and isinstance(placebo, int)
            and arms["hinted"]["attempts"] > 0
            and arms["placebo"]["attempts"] > 0):
        difference = (
            hinted / arms["hinted"]["attempts"]
            - placebo / arms["placebo"]["attempts"]
        )
    report["G9_no_tool_suitability"] = {
        # G9(a) and the retired G9(b) hinted arm are diagnostic only.  G9(c),
        # represented by ``within_caps``, is the sole gate as of 2026-09-05.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "within_caps": within_caps,
    }

    report["paper"] = "arXiv:1802.04870"
    report["family"] = "RAAG direct-product factor secret sharing"
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
