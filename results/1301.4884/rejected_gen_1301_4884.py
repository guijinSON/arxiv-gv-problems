"""Rejected exact Hopf-fiber selection family from arXiv:1301.4884.

The paper displays the 24-cell as six Hopf fibers with four points on each
fiber and observes, after Eq. (7), that adding one common phase to every fiber
preserves all kissing distances.  An instance gives several rationally rotated
quarter-turn orbits on each of the six fibers.  The witness selects one orbit
per fiber whose union is a 24-point kissing configuration on S^3.  The retained
module passes its local correctness gates, but the official no-tool oracle loop
solved every tested level; see REJECTED.md and llm_loop_transcript.jsonl.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from collections import OrderedDict
from fractions import Fraction


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "csp_sat",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "rational unit vectors on S^3",
        "six Hopf-fiber quarter-turn orbits",
    ],
    "verification_operations": [
        "exact rational candidate membership",
        "exact rational norm",
        "exact rational inner product",
        "exact comparison with 1/2",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Normalize each orbit by its 24-cell fiber template: the six selected "
        "orbits share one common Hopf phase, while generic checking compares "
        "quadratically many orbit pairs."
    ),
    "hardness_basis": (
        "Track B: the reference compatibility-table CSP uses O(n^2) exact "
        "four-dimensional inner-product work plus O(n^6) worst-case "
        "backtracking; over eight shipping n=16 instances selftest measured a "
        "median 64,876 exact operations and 0.05-0.08 seconds in repeated runs "
        "on the current "
        "host, whereas template "
        "normalization uses at most 192 exact additions or sign changes before "
        "a six-way set intersection."
    ),
    "max_answer_tokens": 97,
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
    "demo": {"n": 1, "crowding": 1},
    "easy": {"n": 6, "crowding": 1},
    "medium": {"n": 11, "crowding": 4},
    "hard": {"n": 16, "crowding": 5},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Across the six labeled fibers, each selected row encodes the same complex "
    "phase beneath its fixed coordinate sign pattern."
)
PLACEBO_HINT = (
    "Across the six labeled fibers, careful bookkeeping of each rational row "
    "helps prevent coordinate transcription errors and misplaced signs."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A 6 by 4 rational matrix: row i is exactly one listed representative "
        "from fiber i; each reduced coordinate has positive denominator and "
        "absolute numerator and denominator at most 10,000,000,000,000."
    ),
    "bounds": {
        "rows": 6,
        "vector_dimension": 4,
        "max_choices_per_row": 416,
        "coordinate_abs_bound": 10_000_000_000_000,
    },
}

NOTES = """\
Definition: Eq. (1) is the Hopf map, Eq. (3) parameterizes a fiber, and
Eqs. (4)-(7) turn kissing into an exact phase-separation condition.  The
sentence immediately after Eq. (7) supplies the common-phase symmetry used by
the inverse generator.  The 6x4 24-cell representation is described around
Fig. 2; pages 4-8 show that antipodal structure is the tractable regime, and
page 8 explicitly constructs a smaller arrangement, so this is Track B rather
than a hardness claim about finding spherical codes.  Plants and decoys use
the same rational phase distribution, removing a per-row magnitude signature;
candidate order is independently shuffled, removing a positional cue.  Every
hard-preset decoy phase is a five-of-six near miss, which usually traps one-pass
greedy selection while keeping uniform restart density tiny.  The absolute
phase is resampled per instance, so the unrotated-24-cell ansatz has no fixed
orientation to exploit.  All four attacks are measured in selftest; the
disclosed exact compatibility-table CSP is expected to solve every instance
and is reported as the Track-B reference algorithm.
"""


_F = Fraction
_HALF = _F(1, 2)
_COORD_BOUND = 10_000_000_000_000
_PHASE_DEN = 1009
_PHASE_KEY_MAX = 500
_OPPOSITE_FIBERS = {frozenset((0, 1)), frozenset((2, 5)), frozenset((3, 4))}

# One representative from each quarter-turn orbit of the rational 24-cell
# {+/-e_i} union {(+/-1/2,+/-1/2,+/-1/2,+/-1/2)}.  With R^4 = C^2,
# multiplication by i generates the other three points on the same Hopf fiber.
_TEMPLATES = (
    (_F(-1), _F(0), _F(0), _F(0)),
    (_F(0), _F(0), _F(-1), _F(0)),
    (_HALF * -1, _HALF * -1, _HALF * -1, _HALF * -1),
    (_HALF * -1, _HALF * -1, _HALF * -1, _HALF),
    (_HALF * -1, _HALF * -1, _HALF, _HALF * -1),
    (_HALF * -1, _HALF * -1, _HALF, _HALF),
)

# Verification repeatedly samples one immutable instance in G4.  Cache only
# values recomputed exactly from public candidate data; never cache or inspect
# inst["answer"].  The small LRU keeps ordinary generator use bounded.
_VERIFY_CACHE: OrderedDict[int, tuple[dict, dict]] = OrderedDict()
_VERIFY_CACHE_LIMIT = 32


def _j(v: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    """Quarter turn: simultaneous multiplication of both complex coordinates by i."""

    x, y, z, w = v
    return -y, x, -w, z


def _j_power(v: tuple[Fraction, ...], power: int) -> tuple[Fraction, ...]:
    for _ in range(power % 4):
        v = _j(v)
    return v


def _orbit(v: tuple[Fraction, ...]) -> tuple[tuple[Fraction, ...], ...]:
    out = []
    for _ in range(4):
        out.append(v)
        v = _j(v)
    return tuple(out)


def _phase(key: int) -> tuple[Fraction, Fraction]:
    """Rational point on S^1 using the tangent-half-angle parameter key/1009."""

    k = _F(key)
    d = _F(_PHASE_DEN)
    den = d * d + k * k
    return (d * d - k * k) / den, (2 * d * k) / den


def _phase_multiply(
    v: tuple[Fraction, ...], phase: tuple[Fraction, Fraction]
) -> tuple[Fraction, ...]:
    a, b = phase
    x, y, z, w = v
    return a * x - b * y, b * x + a * y, a * z - b * w, b * z + a * w


def _dot(a: tuple[Fraction, ...], b: tuple[Fraction, ...]) -> Fraction:
    return sum((x * y for x, y in zip(a, b)), _F(0))


def _encode_fraction(x: Fraction) -> list[int]:
    return [x.numerator, x.denominator]


def _encode_vec(v: tuple[Fraction, ...]) -> list[list[int]]:
    return [_encode_fraction(x) for x in v]


def _decode_vec(row: object, enforce_bound: bool = True) -> tuple[Fraction, ...]:
    if not isinstance(row, list) or len(row) != 4:
        raise ValueError("expected a row of four rationals")
    out = []
    for item in row:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in item)
            or item[1] <= 0
        ):
            raise ValueError("each rational must be [integer, positive integer]")
        if enforce_bound and (abs(item[0]) > _COORD_BOUND or item[1] > _COORD_BOUND):
            raise OverflowError("rational coordinate exceeds the declared bound")
        out.append(_F(item[0], item[1]))
    return tuple(out)


def _verification_cache(inst: dict) -> dict:
    ident = id(inst)
    found = _VERIFY_CACHE.get(ident)
    if found is not None and found[0] is inst:
        _VERIFY_CACHE.move_to_end(ident)
        return found[1]
    decoded_rows = [[_decode_vec(row) for row in rows] for rows in inst["candidates"]]
    data = {
        "identities": [
            {id(public): (index, vector)
             for index, (public, vector) in enumerate(zip(public_rows, decoded))}
            for public_rows, decoded in zip(inst["candidates"], decoded_rows)
        ],
        "indices": [{v: index for index, v in enumerate(rows)} for rows in decoded_rows],
        "orbits": [[_orbit(v) for v in rows] for rows in decoded_rows],
        "norms": [[_dot(v, v) for v in rows] for rows in decoded_rows],
        "internal": {},
        "compat": {},
    }
    _VERIFY_CACHE[ident] = (inst, data)
    _VERIFY_CACHE.move_to_end(ident)
    while len(_VERIFY_CACHE) > _VERIFY_CACHE_LIMIT:
        _VERIFY_CACHE.popitem(last=False)
    return data


def _cached_internal_ok(cache: dict, fiber: int, index: int) -> bool:
    key = (fiber, index)
    if key not in cache["internal"]:
        orb = cache["orbits"][fiber][index]
        cache["internal"][key] = all(
            _dot(a, b) <= _HALF for a, b in itertools.combinations(orb, 2)
        )
    return cache["internal"][key]


def _cached_compatible(
    cache: dict,
    fiber_a: int,
    index_a: int,
    fiber_b: int,
    index_b: int,
) -> bool:
    key = (fiber_a, index_a, fiber_b, index_b)
    if fiber_a > fiber_b:
        key = (fiber_b, index_b, fiber_a, index_a)
    if key not in cache["compat"]:
        cache["compat"][key] = all(
            _dot(x, y) <= _HALF
            for x in cache["orbits"][fiber_a][index_a]
            for y in cache["orbits"][fiber_b][index_b]
        )
    return cache["compat"][key]


def _adjust_size(n: int, crowding: int) -> tuple[int, int]:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n must be a positive integer")
    if not isinstance(crowding, int) or crowding < 1 or crowding > 5:
        raise ValueError("crowding must be an integer in 1..5")
    if n == 1:
        return 1, 0
    per_fiber = math.comb(5, crowding - 1)
    copies = max(1, (n - 1 + per_fiber - 1) // per_fiber)
    actual = 1 + copies * per_fiber
    total_keys = 1 + copies * math.comb(6, crowding)
    if actual > CERTIFICATE_LANGUAGE["bounds"]["max_choices_per_row"]:
        raise ValueError("n exceeds the declared certificate-language bound")
    if total_keys > _PHASE_KEY_MAX:
        raise ValueError("n and crowding require too many distinct rational phases")
    return actual, copies


def make_instance(n: int, seed: int = 0, crowding: int = 5, **params) -> dict:
    """Inverse-generate six rational Hopf-fiber candidate lists.

    One common phase is sampled first and therefore gives the known certificate.
    Every other phase is placed on exactly `crowding` of the six fibers, never
    all six.  Plants and decoys are exchangeable samples from the same phase pool.
    """

    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    actual_n, copies = _adjust_size(n, crowding)
    rng = random.Random(seed)

    subsets = list(itertools.combinations(range(6), crowding)) if copies else []
    need = 1 + copies * len(subsets)
    phase_keys = rng.sample(range(1, _PHASE_KEY_MAX + 1), need)
    planted_key = phase_keys[0]
    cursor = 1
    keys_by_fiber = [[planted_key] for _ in range(6)]
    for subset in subsets:
        for _ in range(copies):
            key = phase_keys[cursor]
            cursor += 1
            for fiber in subset:
                keys_by_fiber[fiber].append(key)

    candidates = []
    for fiber, template in enumerate(_TEMPLATES):
        rows = [_encode_vec(_phase_multiply(template, _phase(key)))
                for key in keys_by_fiber[fiber]]
        rng.shuffle(rows)
        if len(rows) != actual_n:
            raise AssertionError("unbalanced candidate construction")
        candidates.append(rows)

    answer = [_encode_vec(_phase_multiply(t, _phase(planted_key))) for t in _TEMPLATES]
    return {
        "paper": "arXiv:1301.4884",
        "family": "six-fiber rational 24-cell orbit selection",
        "n": actual_n,
        "crowding": crowding,
        "candidates": candidates,
        "answer": answer,
    }


def _format_fraction(pair: list[int]) -> str:
    return f"{pair[0]}/{pair[1]}"


def _format_vec(row: list[list[int]]) -> str:
    return "(" + ", ".join(_format_fraction(x) for x in row) + ")"


def _answer_text(answer: list[list[list[int]]]) -> str:
    return ";\n".join(_format_vec(row) for row in answer)


def render(inst: dict) -> str:
    lines = [
        "Select six Hopf-fiber orbits that form a 24-point kissing configuration on S^3.",
        "",
        "Definitions.",
        "S^3 is the set of real vectors (x1,x2,x3,x4) with squared norm 1;",
        "all coordinates in this instance happen to be rational.",
        "For a vector v=(x1,x2,x3,x4), define the quarter turn",
        "J(v)=(-x2,x1,-x4,x3).  Its fiber orbit is {v,J(v),J^2(v),J^3(v)}.",
        "A 24-point kissing configuration here means 24 distinct unit vectors such",
        "that the exact Euclidean distance between every two is at least 1.",
        "Equivalently for unit vectors, every distinct pair has inner product at most 1/2.",
        "",
        "There are six labeled fibers, numbered 0 through 5.  For each fiber, select",
        "exactly one listed representative.  Expand the six selected representatives",
        "by J; all 24 expanded vectors must satisfy the kissing condition.  Fiber order",
        "in the answer is mandatory: answer row i must come from candidate list i.",
        "Candidate order within a list has no significance.  Repeats are not allowed.",
        "All rationals below are exact and are written numerator/denominator with a",
        "positive denominator; interval or floating-point answers are not accepted.",
        "",
        f"Each fiber has {inst['n']} candidates:",
    ]
    for i, rows in enumerate(inst["candidates"]):
        lines.append("")
        lines.append(f"Fiber {i}:")
        for j, row in enumerate(rows):
            lines.append(f"  {j}: {_format_vec(row)}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as exactly six",
        "semicolon-separated vectors, in fiber order 0,1,2,3,4,5.  Each vector",
        "must contain four exact num/den rationals.",
        "Format example (illustrative values only):",
        "<answer>(1/1,0/1,0/1,0/1); (0/1,0/1,1/1,0/1);",
        "(1/2,1/2,1/2,1/2); (1/2,1/2,1/2,-1/2);",
        "(1/2,1/2,-1/2,1/2); (1/2,1/2,-1/2,-1/2)</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        if not isinstance(text, str):
            return None
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:text|json|python)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        rows = [part.strip() for part in body.split(";") if part.strip()]
        if len(rows) != 6:
            return None
        answer = []
        for row in rows:
            row = row.strip()
            if row.startswith("(") and row.endswith(")"):
                row = row[1:-1]
            fields = [x.strip() for x in row.split(",")]
            if len(fields) != 4:
                return None
            encoded = []
            for field in fields:
                m = re.fullmatch(r"([+-]?\d+)\s*/\s*([+]?[1-9]\d*)", field)
                if not m:
                    return None
                value = _F(int(m.group(1)), int(m.group(2)))
                encoded.append(_encode_fraction(value))
            answer.append(encoded)
        return answer
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "malformed answer: expected a list of six rational vectors"
    if len(answer) == 0:
        return False, "empty answer: expected six selected representatives"
    if len(answer) != 6:
        return False, f"wrong row count: expected 6 vectors, got {len(answer)}"

    try:
        cache = _verification_cache(inst)
    except Exception:
        return False, "malformed instance candidate data"
    decoded = []
    chosen_indices = []
    for fiber, row in enumerate(answer):
        # random_candidate returns public immutable rows directly.  Reuse their
        # exact decoding during the 200k-sample gate; arbitrary solver objects
        # still go through the full parser and bounds checks below.
        found = cache["identities"][fiber].get(id(row))
        if found is not None:
            index, vector = found
        else:
            try:
                vector = _decode_vec(row)
            except OverflowError:
                return False, "out of range: a rational coordinate exceeds the declared bound"
            except (TypeError, ValueError, ZeroDivisionError):
                return False, "malformed rational: use four [numerator, positive_denominator] pairs per row"
            index = cache["indices"][fiber].get(vector)
        decoded.append(vector)
        chosen_indices.append(index)

    if any(answer[i] == answer[j] for i in range(6) for j in range(i + 1, 6)):
        return False, "duplicate representative: the six selected vectors must be distinct"

    for fiber, vector in enumerate(decoded):
        index = chosen_indices[fiber]
        if index is None:
            return False, f"candidate mismatch: answer row {fiber} is not listed for fiber {fiber}"
        norm = cache["norms"][fiber][index]
        if norm != 1:
            return False, f"non-unit representative in answer row {fiber}"

    # Internal fiber checks first, followed by all 15 cross-fiber pairs.  Three
    # pairs in the generator's original template labelling are automatically
    # compatible, but checking them explicitly keeps verification correct after
    # an arbitrary fibre relabelling (one of the canonical-key symmetries).
    for fiber in range(6):
        if not _cached_internal_ok(cache, fiber, chosen_indices[fiber]):
            return False, f"separation violation inside fiber {fiber}"

    for i in range(6):
        for j in range(i + 1, 6):
            if not _cached_compatible(
                cache, i, chosen_indices[i], j, chosen_indices[j]
            ):
                return False, f"separation violation between fibers {i} and {j}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    # Rows are JSON-native immutable-by-convention data owned by the instance;
    # returning the chosen references avoids millions of pointless deep copies
    # in G4.  verify never mutates them.
    return [rng.choice(rows) for rows in inst["candidates"]]


def search_space(inst: dict) -> int | None:
    return math.prod(len(rows) for rows in inst["candidates"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    count = 0
    for choice in itertools.product(*inst["candidates"]):
        if verify(inst, list(choice))[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """A strong orthogonal/reordering invariant: the full Gram-value multiset."""

    points = []
    for rows in inst["candidates"]:
        for row in rows:
            points.extend(_orbit(_decode_vec(row)))
    grams = []
    for i, a in enumerate(points):
        for b in points[i:]:
            value = _dot(a, b)
            grams.append((value.numerator, value.denominator))
    grams.sort()
    h = hashlib.sha256()
    h.update(f"hopf-six-fiber:{len(points)}|".encode("ascii"))
    for num, den in grams:
        h.update(f"{num}/{den};".encode("ascii"))
    return h.hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 1))
    crowding = int(params.get("crowding", 5))
    actual, _ = _adjust_size(n, crowding)
    if crowding < 5:
        return {"n": max(actual, 11), "crowding": min(5, crowding + 1)}
    if actual < 21:
        return {"n": 21, "crowding": 5}
    # A larger list would put the common-phase normalization route above the
    # 300-operation no-tool cap.  No other paper-native hardness axis remains.
    return None


def _compatible_counted(
    a: tuple[Fraction, ...], b: tuple[Fraction, ...], counter: list[int]
) -> bool:
    for x in _orbit(a):
        for y in _orbit(b):
            counter[0] += 7  # four products and three additions
            if _dot(x, y) > _HALF:
                return False
    return True


def _reference_csp(inst: dict) -> tuple[object | None, dict]:
    """Generic exact compatibility tables followed by depth-first propagation."""

    started = time.perf_counter()
    rows = [[_decode_vec(row) for row in fiber] for fiber in inst["candidates"]]
    counter = [0]
    tables = {}
    for i in range(6):
        for j in range(i + 1, 6):
            if frozenset((i, j)) in _OPPOSITE_FIBERS:
                continue
            table = []
            for a in rows[i]:
                allowed = set()
                for bj, b in enumerate(rows[j]):
                    if _compatible_counted(a, b, counter):
                        allowed.add(bj)
                table.append(allowed)
            tables[(i, j)] = table

    order = (0, 2, 3, 4, 5, 1)
    assigned = {}
    nodes = 0

    def compatible_with_prior(fiber: int, candidate: int) -> bool:
        for other, other_candidate in assigned.items():
            if frozenset((fiber, other)) in _OPPOSITE_FIBERS:
                continue
            i, j = sorted((fiber, other))
            if fiber == i:
                if other_candidate not in tables[(i, j)][candidate]:
                    return False
            elif candidate not in tables[(i, j)][other_candidate]:
                return False
        return True

    def dfs(depth: int) -> bool:
        nonlocal nodes
        if depth == 6:
            return True
        fiber = order[depth]
        for candidate in range(len(rows[fiber])):
            nodes += 1
            if compatible_with_prior(fiber, candidate):
                assigned[fiber] = candidate
                if dfs(depth + 1):
                    return True
                del assigned[fiber]
        return False

    found = dfs(0)
    answer = None
    if found:
        answer = [copy.deepcopy(inst["candidates"][i][assigned[i]]) for i in range(6)]
    return answer, {
        "wall_clock_sec": time.perf_counter() - started,
        "exact_arithmetic_operations": counter[0],
        "search_nodes": nodes,
    }


def _attack_outlier_l1(inst: dict) -> object:
    answer = []
    for rows in inst["candidates"]:
        decoded = [(_decode_vec(row), row) for row in rows]
        values = [sum((abs(x) for x in v), _F(0)) for v, _ in decoded]
        center = sum(values, _F(0)) / len(values)
        _, chosen = max(decoded, key=lambda vr: abs(sum(abs(x) for x in vr[0]) - center))
        answer.append(copy.deepcopy(chosen))
    return answer


def _attack_unrotated(inst: dict) -> object:
    answer = []
    for template, rows in zip(_TEMPLATES, inst["candidates"]):
        chosen = max(rows, key=lambda row: _dot(template, _decode_vec(row)))
        answer.append(copy.deepcopy(chosen))
    return answer


def _raw_compatible(a: object, b: object) -> bool:
    counter = [0]
    return _compatible_counted(_decode_vec(a), _decode_vec(b), counter)


def _attack_greedy_no_backtrack(inst: dict) -> object:
    answer = [None] * 6
    order = (0, 2, 3, 4, 5, 1)
    # A one-pass reverse-list rule: take the last displayed candidate in the
    # first fiber, then the first locally compatible row and never backtrack.
    # Trying every possible starting row is no longer a hand heuristic; it is
    # the successful compatibility-table CSP reported as the reference method.
    answer[0] = copy.deepcopy(inst["candidates"][0][-1])
    for fiber in order[1:]:
        chosen = None
        for row in inst["candidates"][fiber]:
            good = True
            for previous in order:
                if previous == fiber:
                    break
                if answer[previous] is None or frozenset((fiber, previous)) in _OPPOSITE_FIBERS:
                    continue
                if not _raw_compatible(row, answer[previous]):
                    good = False
                    break
            if good:
                chosen = copy.deepcopy(row)
                break
        answer[fiber] = chosen if chosen is not None else copy.deepcopy(inst["candidates"][fiber][0])
    return answer


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 256) -> object | None:
    for _ in range(restarts):
        answer = random_candidate(inst, rng)
        if verify(inst, answer)[0]:
            return answer
    return None


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(x) for x in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(x) for x in value)
    return 1


def _transformed_copy(inst: dict, rng: random.Random) -> dict:
    """Compose real symmetries used by G8 and carry the witness through them."""

    out = copy.deepcopy(inst)
    # Independently change the representative of every unchanged quarter-turn orbit.
    carried = []
    for i, rows in enumerate(out["candidates"]):
        original_answer = _decode_vec(out["answer"][i])
        new_rows = []
        new_answer = None
        for row in rows:
            v = _decode_vec(row)
            power = rng.randrange(4)
            moved = _j_power(v, power)
            new_rows.append(_encode_vec(moved))
            if v == original_answer:
                new_answer = _encode_vec(moved)
        rng.shuffle(new_rows)
        if new_answer is None:
            raise AssertionError("lost planted representative")
        out["candidates"][i] = new_rows
        carried.append(new_answer)
    out["answer"] = carried

    # A common rational Hopf phase is a four-dimensional orthogonal map.
    common = _phase(rng.randrange(1, _PHASE_KEY_MAX + 1))
    out["candidates"] = [[_encode_vec(_phase_multiply(_decode_vec(row), common))
                           for row in rows] for rows in out["candidates"]]
    out["answer"] = [_encode_vec(_phase_multiply(_decode_vec(row), common))
                     for row in out["answer"]]

    # Fiber labels are arbitrary; permute them together with the answer rows.
    permutation = list(range(6))
    rng.shuffle(permutation)
    out["candidates"] = [out["candidates"][i] for i in permutation]
    out["answer"] = [out["answer"][i] for i in permutation]
    return out


# Filled from the script-owned oracle transcripts after hardening.  These values
# are diagnostic only; G9(c)'s measured caps are the gate.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


def selftest() -> dict:
    report = {
        "paper": "1301.4884",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every named preset and several independent seeds.
    g1_ok = 0
    g1_total = 0
    json_native = True
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            g1_total += 1
            g1_ok += int(verify(inst, inst["answer"])[0])
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": g1_ok == g1_total and json_native,
        "verified": g1_ok,
        "attempts": g1_total,
        "answers_json_native": json_native,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five semantically different corruptions and five different diagnostics.
    planted = copy.deepcopy(shipping["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_rows": [planted[1], planted[0]] + planted[2:],
        "duplicate_row": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": copy.deepcopy(planted),
    }
    corruptions["out_of_range"][0][0] = [_COORD_BOUND + 1, 1]
    g2_results = {name: verify(shipping, answer) for name, answer in corruptions.items()}
    reasons = [reason for ok, reason in g2_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": len(reasons) == 5 and len(set(reasons)) == 5,
        "results": {name: {"accepted": ok, "reason": reason}
                    for name, (ok, reason) in g2_results.items()},
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "The common phase gives the following representatives.\n"
        "<answer>\n```text\n" + _answer_text(shipping["answer"]) + "\n```\n</answer>\n"
        "Those are my final coordinates."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed_equals_planted": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("no tagged coordinates here") is None,
    }

    # G4 and shipping density: one listed representative per fiber is already
    # every immediately visible constraint on the answer language.
    guess_rng = random.Random(271828)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "structure_aware_space": search_space(shipping),
        "prior": "independently uniform over the listed representative in each fiber",
    }

    # Run the required Track-B reference algorithm across eight shipping seeds.
    reference_runs = []
    reference_successes = 0
    attack_names = (
        "outlier_l1_coordinate",
        "greedy_no_backtracking",
        "random_restart_256",
        "unrotated_24cell_ansatz",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_attempts = {name: 0 for name in attack_names}
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        reference_answer, stats = _reference_csp(inst)
        reference_successes += int(reference_answer is not None and verify(inst, reference_answer)[0])
        reference_runs.append(stats)

        candidates = {
            "outlier_l1_coordinate": _attack_outlier_l1(inst),
            "greedy_no_backtracking": _attack_greedy_no_backtrack(inst),
            "random_restart_256": _attack_random_restart(inst, random.Random(seed ^ 0xA5A5)),
            "unrotated_24cell_ansatz": _attack_unrotated(inst),
        }
        for name, answer in candidates.items():
            attack_attempts[name] += 1
            attack_successes[name] += int(answer is not None and verify(inst, answer)[0])

    walls = sorted(run["wall_clock_sec"] for run in reference_runs)
    operations = sorted(run["exact_arithmetic_operations"] for run in reference_runs)
    nodes = sorted(run["search_nodes"] for run in reference_runs)
    median = lambda xs: (xs[len(xs) // 2] if len(xs) % 2 else
                         (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2)
    baseline = {
        "name": "exact orbit-compatibility tables plus depth-first constraint propagation",
        "complexity": "O(n^2) compatibility construction; O(n^6) worst-case search",
        "wall_clock_sec_median": median(walls),
        "exact_arithmetic_operations_median": median(operations),
        "search_nodes_median": median(nodes),
        "attempts": len(reference_runs),
        "successes": reference_successes,
    }
    demo = make_instance(seed=17, **DIFFICULTY["demo"])
    easy = make_instance(seed=17, **DIFFICULTY["easy"])
    demo_count = enumerate_all(demo)
    easy_count = enumerate_all(easy)
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count is not None
            and easy_count is not None
            and reference_successes == 8
        ),
        "shipping_density": {
            "hits": guess_hits,
            "total": guess_total,
            "observed_probability": guess_probability,
        },
        "demo_exact_valid_answers": demo_count,
        "demo_language_size": search_space(demo),
        "easy_exact_valid_answers": easy_count,
        "easy_language_size": search_space(easy),
        "strongest_attack_cost": baseline,
    }

    attacks = {name: {"successes": attack_successes[name],
                      "attempts": attack_attempts[name]}
               for name in attack_names}
    all_failed = len(attacks) >= 4 and all(x["successes"] == 0 for x in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            **baseline,
            "solves": f"{reference_successes}/8, as expected on Track B",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        crowding=DIFFICULTY[SHIPPING_DIFFICULTY]["crowding"],
        seed=424242,
    )
    report["G7_scales"] = {
        "pass": doubled["n"] > shipping["n"] and verify(doubled, doubled["answer"])[0],
        "shipping_n": shipping["n"],
        "doubled_request_actual_n": doubled["n"],
        "doubled_search_space": search_space(doubled),
    }

    invariance = 0
    real_transforms = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY["easy"])
        transformed = _transformed_copy(inst, random.Random(20_000 + seed))
        invariance += int(canonical_key(inst) == canonical_key(transformed))
        real_transforms += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(canonical_key(inst))
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariance == 20 and real_transforms == 20 and distinct == 20,
        "invariant_transformations": invariance,
        "transformation_witnesses_verified": real_transforms,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "invariant": "SHA-256 of the exact full Gram-value multiset, not seed or render text",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_elements = _atomic_elements(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_ops = 2 * 6 * shipping["n"]
    arms = copy.deepcopy(G9_ARMS)
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    caps_ok = (answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": caps_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_run" if arms["hinted"]["attempts"] == 0
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {
            "answer_chars": 2000,
            "answer_elements": 256,
            "intended_route_operations": 300,
        },
        "operation_note": (
            "two exact additions/sign changes normalize each of 6n candidates; "
            "set insertion and equality comparisons are not arithmetic operations"
        ),
    }

    gates = [value["pass"] for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
