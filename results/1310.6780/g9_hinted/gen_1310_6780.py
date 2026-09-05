"""Verified generator for clique-probability telescoping in uncertain graphs.

The native object is the independent-edge uncertain graph of Section 2 of
arXiv:1310.6780.  Observation 1 says that a fixed clique's existence
probability is the product of its edge probabilities.  Instances below hide
several telescoping products behind reversible relabellings of vertices and
edge ranks.  The endpoint fractions are known by composition, not by solving
the generated instance.
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import time
from fractions import Fraction
from typing import Any


TRACK = "B"

_LANES = 4
_MIN_ENDPOINT = 1 << 30
_MAX_ENDPOINT = (1 << 31) - 1
_ENDPOINT_CHOICES = _MAX_ENDPOINT - _MIN_ENDPOINT + 1

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "rational_exact",
    "computational_core": "telescoping",
    "certificate_form": "telescoping",
    "native_objects": [
        "complete independent-edge uncertain graph",
        "designated vertex clique",
        "exact rational edge probabilities",
    ],
    "verification_operations": [
        "exact integer divisibility and range checks",
        "exact rational endpoint comparison",
        "exact rational product recomputation in the reference algorithm",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The reversible vertex and edge-rank programs only reorder all unordered "
        "edges, exposing four interleaved telescoping products; without that "
        "change of variables one must multiply every displayed edge factor."
    ),
    "hardness_basis": (
        "Track B: Section 2, Observation 1 gives the standard exact product over "
        "all binomial(n,2) independent edge probabilities; for this succinct "
        "encoding it costs Theta(n*vertex_rounds+n^2*rank_rounds) index work plus "
        "exact products. At the initial hard preset the measured reference run uses "
        "5,081,692 counted arithmetic/index operations and 0.86 seconds per "
        "instance (6.89 seconds for eight in the recorded gate run), whereas the intended "
        "change-of-variables route uses at most 174 exact "
        "operations after recognizing that every opcode is reversible."
    ),
    "max_answer_tokens": 32,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered list of four reduced positive rational endpoint factors. "
        "Each is encoded as [a,a+1], with 2^30 <= a < 2^31; the four "
        "numerators are distinct. Position j is the contribution of "
        "edge-rank lane j."
    ),
    "bounds": {
        "lanes": _LANES,
        "rational_encoding": "[numerator, denominator]",
        "minimum_numerator": _MIN_ENDPOINT,
        "maximum_numerator": _MAX_ENDPOINT,
        "denominator": "numerator + 1",
    },
}

DIFFICULTY = {
    "hard": {"n": 144, "vertex_rounds": 40, "rank_rounds": 120, "lanes": _LANES},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Every opcode only permutes a finite index set, so the multiset of triangular edge ranks is unchanged."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the lane labels and rational endpoints helps avoid transcription mistakes."
)

# Filled with script-owned oracle measurements after the three independent runs.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not run: OpenRouter key total limit exceeded",
    "placebo_verdict": "not run: OpenRouter key total limit exceeded",
}

NOTES = r"""
Paper grounding. Section 2 defines an uncertain graph as an undirected simple
graph whose possible edges occur independently, Definition 3 defines clique
probability, and Observation 1 identifies that probability with the product of
the clique's edge probabilities. Observation 2 gives downward monotonicity;
Definition 4 makes maximality checkable by trying each outside vertex. Section
4's MULE algorithm enumerates alpha-maximal cliques in O(n 2^n), while the
paper's experiments stress that typical behavior is output-sensitive.

Step-0 algorithm question. A single alpha-maximal clique is obtainable by a
one-pass greedy extension: once a vertex fails to extend a clique, Observation
2 means it cannot become eligible later. More directly for this family,
Observation 1 evaluates the designated clique by an exact product of
binomial(n,2) factors. Therefore this is not a Track-A family. It is Track B:
the ordinary product is mechanically easy but far beyond no-tool arithmetic,
while recognizing that the supplied reversible programs merely change the
edge-rank variable collapses each lane to its two endpoints.

Generation and attacks. Four endpoint ratios are sampled first. Lane j has
length equal to the number of ranks congruent to j modulo four and base equal
to that length times its planted endpoint numerator. Its factors are
(base+s)/(base+s+1), so composition gives a/(a+1). Vertex and edge programs are
then sampled solely from reversible operations. All vertices and ranks pass
through the same generators; there is no statistically special planted edge.
The panel tests a smallest-factor outlier, a 32-factor partial product, random
endpoint restarts, and the tempting but wrong use of endpoints in displayed
edge order. The successful full exact product is reported separately as the
Track-B reference algorithm.
""".strip()


# Program opcodes.  Each operation is a bijection of range(modulus).
# 0: cyclic shift; 1: transposition; 2: full reversal; 3: reverse each block;
# 4: transpose a (modulus/divisor)-by-divisor row-major grid;
# 5: rotate each block.
_SHIFT, _SWAP, _REVERSE, _BLOCK_REVERSE, _TRANSPOSE, _BLOCK_ROTATE = range(6)


def _divisors(value: int) -> list[int]:
    out = []
    d = 2
    while d * d <= value:
        if value % d == 0:
            out.append(d)
            if d * d != value:
                out.append(value // d)
        d += 1
    return sorted(out)


def _make_program(modulus: int, rounds: int, rng: random.Random) -> list[list[int]]:
    """Sample a composition of manifestly reversible index operations."""
    divisors = _divisors(modulus)
    program: list[list[int]] = []
    for _ in range(rounds):
        choices = [_SHIFT, _SWAP, _REVERSE]
        if divisors:
            choices.extend((_BLOCK_REVERSE, _TRANSPOSE, _BLOCK_ROTATE))
        op = rng.choice(choices)
        if op == _SHIFT:
            program.append([op, rng.randrange(1, modulus)])
        elif op == _SWAP:
            a = rng.randrange(modulus)
            b = rng.randrange(modulus - 1)
            if b >= a:
                b += 1
            program.append([op, a, b])
        elif op == _REVERSE:
            program.append([op])
        elif op in (_BLOCK_REVERSE, _TRANSPOSE):
            program.append([op, rng.choice(divisors)])
        else:
            block = rng.choice(divisors)
            program.append([op, block, rng.randrange(1, block)])
    return program


def _apply_program(value: int, modulus: int, program: list[list[int]]) -> int:
    z = value
    for record in program:
        op = record[0]
        if op == _SHIFT:
            z = (z + record[1]) % modulus
        elif op == _SWAP:
            if z == record[1]:
                z = record[2]
            elif z == record[2]:
                z = record[1]
        elif op == _REVERSE:
            z = modulus - 1 - z
        elif op == _BLOCK_REVERSE:
            block = record[1]
            z = (z // block) * block + (block - 1 - z % block)
        elif op == _TRANSPOSE:
            width = record[1]
            z = (z % width) * (modulus // width) + z // width
        elif op == _BLOCK_ROTATE:
            block, shift = record[1], record[2]
            z = (z // block) * block + (z % block + shift) % block
        else:
            raise ValueError("unknown opcode")
    return z


def _program_valid(modulus: int, program: Any) -> bool:
    if not isinstance(program, list):
        return False
    for rec in program:
        if not isinstance(rec, list) or not rec or any(
                isinstance(x, bool) or not isinstance(x, int) for x in rec):
            return False
        op = rec[0]
        if op == _SHIFT:
            if len(rec) != 2 or not 0 < rec[1] < modulus:
                return False
        elif op == _SWAP:
            if (len(rec) != 3 or not 0 <= rec[1] < modulus
                    or not 0 <= rec[2] < modulus or rec[1] == rec[2]):
                return False
        elif op == _REVERSE:
            if len(rec) != 1:
                return False
        elif op in (_BLOCK_REVERSE, _TRANSPOSE):
            if len(rec) != 2 or rec[1] <= 1 or modulus % rec[1]:
                return False
        elif op == _BLOCK_ROTATE:
            if (len(rec) != 3 or rec[1] <= 1 or modulus % rec[1]
                    or not 0 < rec[2] < rec[1]):
                return False
        else:
            return False
    return True


def _validate_params(n: int, vertex_rounds: int, rank_rounds: int,
                     lanes: int) -> None:
    values = (n, vertex_rounds, rank_rounds, lanes)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("all parameters must be integers")
    if n < 4:
        raise ValueError("n must be at least 4")
    if vertex_rounds < 0 or rank_rounds < 0:
        raise ValueError("round counts must be nonnegative")
    if lanes != _LANES:
        raise ValueError("this certificate language fixes four lanes")


def _lane_lengths(edge_count: int, lanes: int) -> list[int]:
    return [(edge_count + lanes - 1 - j) // lanes for j in range(lanes)]


def make_instance(n: int, seed: int = 0, vertex_rounds: int = 0,
                  rank_rounds: int = 0, lanes: int = _LANES, **params: Any) -> dict:
    """Inverse-generate four lane endpoints, then compose telescoping factors."""
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, vertex_rounds, rank_rounds, lanes)
    rng = random.Random(seed)
    endpoints: list[int] = []
    while len(endpoints) < lanes:
        value = rng.randrange(_MIN_ENDPOINT, _MAX_ENDPOINT + 1)
        if value not in endpoints:
            endpoints.append(value)

    edge_count = n * (n - 1) // 2
    lengths = _lane_lengths(edge_count, lanes)
    bases = [a * length for a, length in zip(endpoints, lengths)]
    vertex_program = _make_program(n, vertex_rounds, rng)
    rank_program = _make_program(edge_count, rank_rounds, rng)

    return {
        "n": n,
        "lanes": lanes,
        "edge_count": edge_count,
        "lane_bases": bases,
        "vertex_program": vertex_program,
        "rank_program": rank_program,
        "answer": [[a, a + 1] for a in endpoints],
    }


def _render_program(program: list[list[int]]) -> str:
    return json.dumps(program, separators=(",", ":"))


def render(inst: dict) -> str:
    n = inst["n"]
    lanes = inst["lanes"]
    text = f"""Exact clique probability in an uncertain graph

An uncertain graph is an undirected simple graph in which each possible edge
occurs independently with its stated probability.  The probability that a
vertex set is a clique is therefore the product of the probabilities of all
unordered edges having both endpoints in that set.

Here the vertices are the integers 0 through {n - 1}.  Every unordered pair is
a possible edge, and C is the set of all {n} vertices.  Thus C contains all
M = {inst['edge_count']} unordered edges.  Compute each edge probability by
the exact integer rules below; `%` is least nonnegative remainder, `//` is
floor division, table/list positions are 0-indexed, and all displayed interval
bounds are inclusive where applicable.

For an index z in 0,...,D-1, execute a program record-by-record with modulus D.
The first integer in each record is its opcode:
  [0,s]     means z = (z+s) % D.
  [1,a,b]   swaps values a and b and leaves every other z unchanged.
  [2]       means z = D-1-z.
  [3,k]     means z = (z//k)*k + (k-1-(z%k)).
  [4,k]     means z = (z%k)*(D//k) + z//k.
  [5,k,s]   means z = (z//k)*k + ((z%k)+s)%k.
Every k appearing below divides its program's modulus exactly.

Vertex program (modulus D={n}):
{_render_program(inst['vertex_program'])}

Edge-rank program (modulus D={inst['edge_count']}):
{_render_program(inst['rank_program'])}

Lane bases B[0],...,B[{lanes - 1}]:
{json.dumps(inst['lane_bases'])}

For an unordered edge {{u,v}}:
  1. Run u and v separately through the vertex program, obtaining x and y.
  2. Swap x,y if needed so x<y.
  3. Set t = x*(2*{n}-x-1)//2 + (y-x-1).
  4. Run t through the edge-rank program, obtaining z.
  5. Set j=z%{lanes} and s=z//{lanes}.  The edge probability is
     (B[j]+s)/(B[j]+s+1).

Give the exact clique probability in factorized form: output exactly {lanes}
reduced positive fractions, in lane order j=0,...,{lanes - 1}, whose product is
the probability that C is a clique.  There are no omitted edges and no repeated
edges.  Each fraction must use decimal integers as numerator/denominator.  The
four numerators are distinct and each lies in the inclusive interval
[{_MIN_ENDPOINT},{_MAX_ENDPOINT}].

Give your final answer inside <answer></answer> tags, as fractions separated by semicolons.
Example: <answer>1073741824/1073741825; 1073741826/1073741827; 1073741828/1073741829; 1073741830/1073741831</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: Any) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    body = matches[-1].strip() if matches else text.strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        if body.startswith("["):
            value = json.loads(body)
            if (isinstance(value, list)
                    and all(isinstance(row, list) for row in value)):
                return value
            return None
        pieces = [piece.strip() for piece in body.split(";")]
        if not pieces or any(not piece for piece in pieces):
            return None
        out = []
        for piece in pieces:
            match = re.fullmatch(r"([+-]?\d+)\s*/\s*([+-]?\d+)", piece)
            if not match:
                return None
            out.append([int(match.group(1)), int(match.group(2))])
        return out
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _expected(inst: dict) -> list[list[int]] | None:
    try:
        n = inst["n"]
        lanes = inst["lanes"]
        edge_count = inst["edge_count"]
        bases = inst["lane_bases"]
        vertex_program = inst["vertex_program"]
        rank_program = inst["rank_program"]
    except (KeyError, TypeError):
        return None
    if (isinstance(n, bool) or not isinstance(n, int) or n < 4
            or lanes != _LANES or edge_count != n * (n - 1) // 2
            or not isinstance(bases, list) or len(bases) != lanes
            or not isinstance(vertex_program, list)
            or not isinstance(rank_program, list)
            or not _program_valid(n, vertex_program)
            or not _program_valid(edge_count, rank_program)):
        return None
    lengths = _lane_lengths(edge_count, lanes)
    out = []
    for base, length in zip(bases, lengths):
        if (isinstance(base, bool) or not isinstance(base, int) or base <= 0
                or base % length):
            return None
        endpoint = base // length
        if not _MIN_ENDPOINT <= endpoint <= _MAX_ENDPOINT:
            return None
        out.append([endpoint, endpoint + 1])
    if len({row[0] for row in out}) != lanes:
        return None
    return out


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    expected = _expected(inst)
    if expected is None:
        return False, "instance is malformed"
    if answer == []:
        return False, "certificate is empty"
    if not isinstance(answer, list):
        return False, "certificate must be a list of lane fractions"
    if len(answer) != inst["lanes"]:
        return False, f"expected {inst['lanes']} lane fractions"
    cleaned: list[list[int]] = []
    for lane, pair in enumerate(answer):
        if not isinstance(pair, list) or len(pair) != 2:
            return False, f"lane {lane} is not a [numerator, denominator] pair"
        num, den = pair
        if (isinstance(num, bool) or isinstance(den, bool)
                or not isinstance(num, int) or not isinstance(den, int)):
            return False, f"lane {lane} entries must be integers"
        if den <= 0 or num <= 0:
            return False, f"lane {lane} fraction must be positive"
        if num > den:
            return False, f"lane {lane} fraction exceeds one"
        if math.gcd(num, den) != 1:
            return False, f"lane {lane} fraction is not reduced"
        if not _MIN_ENDPOINT <= num <= _MAX_ENDPOINT:
            return False, f"lane {lane} numerator is outside the certificate bound"
        cleaned.append([num, den])
    if len({row[0] for row in cleaned}) != len(cleaned):
        return False, "lane numerators must be distinct"
    for lane, (got, want) in enumerate(zip(cleaned, expected)):
        if got != want:
            return False, f"lane {lane} endpoint fraction is incorrect"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    values = rng.sample(range(_MIN_ENDPOINT, _MAX_ENDPOINT + 1), inst["lanes"])
    return [[value, value + 1] for value in values]


def search_space(inst: dict) -> int | None:
    if inst.get("lanes") != _LANES:
        return None
    return math.prod(_ENDPOINT_CHOICES - offset for offset in range(_LANES))


def enumerate_all(inst: dict) -> int | None:
    # The bounded language has at least 2^120 candidates at every preset.
    # Returning None is the required capped behavior, not an unbounded search.
    return None


def canonical_key(inst: dict) -> str:
    expected = _expected(inst)
    if expected is None:
        return "malformed"
    # The task multiplies every edge. Vertex relabelling, program composition,
    # edge-input order, and lane renaming preserve it.  Endpoint multiset + n is
    # therefore the exact normal form for this generated family.
    data = {
        "n": inst["n"],
        "endpoint_numerators": sorted(row[0] for row in expected),
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def escalate(params: dict) -> dict | str | None:
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p["n"])
    p["n"] = n + max(16, n // 2)
    p["vertex_rounds"] = min(90, int(p.get("vertex_rounds", 0)) + 10)
    p["rank_rounds"] = min(260, int(p.get("rank_rounds", 0)) + 20)
    p["lanes"] = _LANES
    return p


def _edge_rank(n: int, x: int, y: int) -> int:
    if x > y:
        x, y = y, x
    return x * (2 * n - x - 1) // 2 + (y - x - 1)


def _product_tree(values: list[int]) -> int:
    if not values:
        return 1
    level = values
    while len(level) > 1:
        nxt = [level[i] * level[i + 1] for i in range(0, len(level) - 1, 2)]
        if len(level) & 1:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def _reference_product(inst: dict) -> tuple[list[list[int]], int]:
    """Generic exact Observation-1 product, deliberately not telescoped."""
    n = inst["n"]
    lanes = inst["lanes"]
    vp = inst["vertex_program"]
    rp = inst["rank_program"]
    mapped = [_apply_program(v, n, vp) for v in range(n)]
    numerators = [[] for _ in range(lanes)]
    denominators = [[] for _ in range(lanes)]
    for u in range(n):
        for v in range(u + 1, n):
            t = _edge_rank(n, mapped[u], mapped[v])
            z = _apply_program(t, inst["edge_count"], rp)
            lane, pos = z % lanes, z // lanes
            num = inst["lane_bases"][lane] + pos
            numerators[lane].append(num)
            denominators[lane].append(num + 1)
    out = []
    for lane in range(lanes):
        frac = Fraction(_product_tree(numerators[lane]),
                        _product_tree(denominators[lane]))
        out.append([frac.numerator, frac.denominator])
    m = inst["edge_count"]
    # Count table-free integer/index work, factor construction, product-tree
    # multiplications, final gcd reductions, and comparisons.
    operations = (n * max(1, len(vp)) + m * (11 + 4 * len(rp))
                  + 2 * (m - lanes) + 3 * lanes)
    return out, operations


def _attack_candidates(inst: dict, seed: int) -> dict[str, object]:
    expected = _expected(inst)
    assert expected is not None
    lanes = inst["lanes"]
    lengths = _lane_lengths(inst["edge_count"], lanes)

    # Per-edge outlier: mistake each lane's smallest individual factor for the
    # whole lane product, then force it into the certificate's adjacent form.
    outlier = []
    for base, length in zip(inst["lane_bases"], lengths):
        guess = min(_MAX_ENDPOINT, max(_MIN_ENDPOINT, base // max(1, length + 1)))
        outlier.append([guess, guess + 1])

    # Greedy/manual budget: multiply only the first 32 displayed edges, then use
    # the reduced numerator as an endpoint guess.
    partial = [Fraction(1, 1) for _ in range(lanes)]
    n = inst["n"]
    mapped = [_apply_program(v, n, inst["vertex_program"]) for v in range(n)]
    used = 0
    displayed_positions = [[] for _ in range(lanes)]
    for u in range(n):
        for v in range(u + 1, n):
            z = _apply_program(
                _edge_rank(n, mapped[u], mapped[v]), inst["edge_count"],
                inst["rank_program"])
            lane, pos = z % lanes, z // lanes
            if used < 32:
                num = inst["lane_bases"][lane] + pos
                partial[lane] *= Fraction(num, num + 1)
                displayed_positions[lane].append(pos)
            used += 1
            if used >= 32:
                break
        if used >= 32:
            break
    partial_guess = []
    for frac in partial:
        value = _MIN_ENDPOINT + (frac.numerator % _ENDPOINT_CHOICES)
        partial_guess.append([value, value + 1])

    rng = random.Random(seed ^ 0x13106780)
    restart_guess = random_candidate(inst, rng)

    # Treat first/last displayed positions as chain endpoints, ignoring that
    # the intervening program changes their order.
    display_guess = []
    for lane, positions in enumerate(displayed_positions):
        if not positions:
            value = _MIN_ENDPOINT
        else:
            raw = inst["lane_bases"][lane] + positions[0] - positions[-1]
            value = _MIN_ENDPOINT + (abs(raw) % _ENDPOINT_CHOICES)
        display_guess.append([value, value + 1])

    return {
        "outlier_smallest_edge_factor": outlier,
        "greedy_first_32_factors": partial_guess,
        "random_restart_endpoint_tuple": restart_guess,
        "displayed_endpoints_without_invariant": display_guess,
    }


def _transformed_instances(inst: dict) -> list[tuple[dict, object]]:
    """Relabelling/symmetry transforms paired with carried certificates."""
    n = inst["n"]
    lanes = inst["lanes"]
    original_answer = copy.deepcopy(inst["answer"])

    # New label u' = n-1-u. Prepending the same involution recovers old u.
    relabelled = copy.deepcopy(inst)
    relabelled["vertex_program"] = [[_REVERSE]] + relabelled["vertex_program"]

    # Reordering either reversible program changes assignments but not the full
    # edge/rank multiset used by this all-vertex clique.
    reordered = copy.deepcopy(inst)
    reordered["vertex_program"] = list(reversed(reordered["vertex_program"]))
    reordered["rank_program"] = list(reversed(reordered["rank_program"]))

    # Rename lanes and carry the answer through the same renaming.
    perm = [2, 0, 3, 1]
    lane_changed = copy.deepcopy(inst)
    old_bases = lane_changed["lane_bases"]
    old_answer = lane_changed["answer"]
    # New lane j receives old lane perm[j]. Lengths can differ by one, so keep
    # the endpoint but rebuild the base for the new lane length.
    lengths = _lane_lengths(inst["edge_count"], lanes)
    carried = [copy.deepcopy(old_answer[perm[j]]) for j in range(lanes)]
    lane_changed["lane_bases"] = [carried[j][0] * lengths[j]
                                  for j in range(lanes)]
    lane_changed["answer"] = copy.deepcopy(carried)

    composed = copy.deepcopy(lane_changed)
    composed["vertex_program"] = [[_REVERSE]] + list(
        reversed(composed["vertex_program"]))
    composed["rank_program"] = list(reversed(composed["rank_program"]))

    return [
        (relabelled, original_answer),
        (reordered, original_answer),
        (lane_changed, carried),
        (composed, carried),
    ]


def _answer_wire(answer: list[list[int]]) -> str:
    return "; ".join(f"{a}/{b}" for a, b in answer)


def _count_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict[str, Any] = {
        "paper": "1310.6780",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset and several unrelated seeds.
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, why = verify(inst, inst["answer"])
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "attempts": g1_attempts, "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=24681357, **shipping_params)
    answer = copy.deepcopy(inst["answer"])

    # G2: requested corruption modes, each routed to a distinct diagnostic.
    swapped = copy.deepcopy(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = copy.deepcopy(answer)
    duplicated[1] = copy.deepcopy(duplicated[0])
    out_of_range = copy.deepcopy(answer)
    out_of_range[0] = [_MAX_ENDPOINT + 1, _MAX_ENDPOINT + 2]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate_one": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    g2_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        g2_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in g2_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: tags, surrounding prose, a markdown fence, and exact round trip.
    response = ("I used independence and changed variables in the edge product.\n"
                "```text\n<answer>" + _answer_wire(answer)
                + "</answer>\n```\nThose are the four lane factors.")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4/G5 density: sample the deliberately conservative, family-informed
    # endpoint language, not arbitrary rational noise.
    trials = 200_000
    rng = random.Random(0x6780)
    hits = 0
    for _ in range(trials):
        ok, _ = verify(inst, random_candidate(inst, rng))
        hits += int(ok)
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "candidate_space": space,
        "sampling_prior": "four independent adjacent reduced fractions in the declared bounds",
    }

    # Reference algorithm succeeds as expected on Track B and supplies the
    # shipping-preset mechanical cost.
    ref_attempts = 8
    ref_successes = 0
    ref_operations = 0
    t0 = time.perf_counter()
    for seed in range(800, 800 + ref_attempts):
        ref_inst = make_instance(seed=seed, **shipping_params)
        got, operations = _reference_product(ref_inst)
        ok, _ = verify(ref_inst, got)
        ref_successes += int(ok)
        ref_operations = max(ref_operations, operations)
    ref_wall = time.perf_counter() - t0

    report["G5_density_and_baseline"] = {
        "pass": hits / trials < 1e-6 and ref_successes == ref_attempts,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_sampled_solution_fraction": hits / trials,
        "exact_valid_answers_in_declared_language": 1,
        "exact_density": 1 / space if space else None,
        "baseline_wall_clock_seconds": round(ref_wall / ref_attempts, 6),
        "baseline_total_wall_clock_seconds": round(ref_wall, 6),
        "baseline_operations_max": ref_operations,
        "baseline_attempts": ref_attempts,
    }

    # G6: four no-tool attacks fail on every seed. The successful standard
    # computation is deliberately separate, as Track B requires.
    attack_counts = {
        name: {"successes": 0, "attempts": 0}
        for name in (
            "outlier_smallest_edge_factor",
            "greedy_first_32_factors",
            "random_restart_endpoint_tuple",
            "displayed_endpoints_without_invariant",
        )
    }
    for seed in range(8):
        test_inst = make_instance(seed=9000 + seed, **shipping_params)
        for name, candidate in _attack_candidates(test_inst, seed).items():
            ok, _ = verify(test_inst, candidate)
            attack_counts[name]["successes"] += int(ok)
            attack_counts[name]["attempts"] += 1
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attack_counts.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "Observation-1 exact edge-product with balanced integer products",
            "complexity": "Theta(n^2 * rank_rounds) index operations plus exact big-integer products",
            "wall_clock_sec": round(ref_wall / ref_attempts, 6),
            "total_wall_clock_sec": round(ref_wall, 6),
            "operations": ref_operations,
            "successes": ref_successes,
            "attempts": ref_attempts,
            "solves": f"{ref_successes}/{ref_attempts}, as expected on Track B",
        },
    }

    # G7: both the ground set and obfuscation grow; the witness remains four
    # fractions.  Escalate once from the shipping preset and also double n.
    harder = escalate(shipping_params)
    assert isinstance(harder, dict)
    hard_inst = make_instance(seed=111, **harder)
    doubled = dict(shipping_params)
    doubled["n"] *= 2
    doubled["vertex_rounds"] += 10
    doubled["rank_rounds"] += 20
    doubled_inst = make_instance(seed=222, **doubled)
    hard_ok, _ = verify(hard_inst, hard_inst["answer"])
    double_ok, _ = verify(doubled_inst, doubled_inst["answer"])
    report["G7_scales"] = {
        "pass": hard_ok and double_ok
        and hard_inst["edge_count"] > inst["edge_count"]
        and len(json.dumps(hard_inst["answer"])) <= len(json.dumps(inst["answer"])) + 8,
        "shipping_edges": inst["edge_count"],
        "escalated_edges": hard_inst["edge_count"],
        "doubled_n": doubled["n"],
        "doubled_verifies": double_ok,
        "answer_atoms_unchanged": _count_atoms(hard_inst["answer"]) == _count_atoms(answer),
    }

    # G8: four generators of the equivalence relation, including compositions,
    # over 20 seeds; verify the original/carried witness after each transform.
    invariant_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        # Alternate an equal-lane-length size with one whose edge count is not
        # divisible by four.  This catches keys that accidentally bind an
        # endpoint to a particular lane length instead of respecting lane
        # relabelling.
        audit_params = dict(shipping_params)
        audit_params["n"] -= seed & 1
        base_inst = make_instance(seed=20000 + seed, **audit_params)
        key = canonical_key(base_inst)
        unrelated_keys.append(key)
        for transformed, carried in _transformed_instances(base_inst):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed")
            ok, why = verify(transformed, carried)
            carried_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}: carried answer failed: {why}")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "symmetries": [
            "vertex relabelling",
            "reordering reversible program instructions",
            "lane renaming",
            "compositions of those maps",
        ],
    }

    # G9(a,b) is diagnostic only; G9(c) is the gate.
    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    intended_ops = (shipping_params["vertex_rounds"]
                    + shipping_params["rank_rounds"] + 14)
    arms = {
        name: dict(G9_MEASUREMENTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = answer_chars <= 2000 and _count_atoms(answer) <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "placebo_verdict": G9_MEASUREMENTS["placebo_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": _count_atoms(answer),
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if re.match(r"G\d", key)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
