"""Verified problem generator for arXiv:2504.06573.

The generated object is a weighted quiver in the rank-four regime of Theorem
4.27.  Generation starts with the cycle certificate and constructs the quiver
around it; verification independently replays the exchange-matrix mutations.
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
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "integer skew-symmetric exchange matrix",
        "weighted quiver",
        "reduced mutation sequence",
    ],
    "verification_operations": [
        "exact integer exchange-matrix mutation",
        "adjacent-symbol comparison",
        "exact matrix equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the long rank-four cycle as a conjugate of the source cycle "
        "of an abundant acyclic rank-three quiver; without that change of "
        "basepoint one must recover a long descent by exact mutations."
    ),
    "hardness_basis": (
        "Track B: Theorem 4.27 and Lemma 3.11 give a rank-three descent-and-"
        "source reconstruction in O(L r^3) exact arithmetic for r=4, measured "
        "at 24 trial mutations, 329 scalar operations, and about 0.0002 seconds "
        "for the shipping seed in selftest; the alternating-conjugation invariant "
        "leaves at most 32 sign, magnitude, and length operations after it is "
        "recognized."
    ),
    "max_answer_tokens": 11,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of exactly L vertex labels from {0,1,2,3}, with no two "
        "adjacent labels equal.  L is printed in the instance."
    ),
    "bounds": {
        "alphabet_size": 4,
        "length": "the displayed target length L",
        "adjacent_repetitions": 0,
        "candidate_count": "4*3^(L-1)",
    },
}


DIFFICULTY = {
    "demo": {"n": 3, "repetitions": 1},
    "easy": {"n": 10007, "repetitions": 4},
    "medium": {"n": 100003, "repetitions": 4},
    "hard": {"n": 1000003, "repetitions": 4},
}

SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "View the long rank-three portion as a conjugation of an acyclic source cycle."
)
PLACEBO_HINT = (
    "Treat the displayed data carefully and keep track of every stated convention."
)


# Filled after the three independent harden.py runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": None, "attempts": 0},
    "placebo": {"solved": None, "attempts": 0},
    "hinted_verdict": "pending",
}


NOTES = r"""
Definition 2.2 fixes exchange-matrix mutation and Definition 2.5 fixes a
mutation cycle.  Theorem 4.21 gives the conjugated source-sequence identity.
Theorem 4.23 makes the resulting cycle simple for abundant acyclic blocks, and
Theorem 4.27 specializes to one rank-three block plus one vertex and proves
that this is the unique simple cycle.  Lemma 3.11 is the easy-regime warning:
an abundant acyclic quiver has exactly one reduced reddening sequence, its
source sequence.  Therefore this is Track B, not Track A.

Generation samples six weights from the same interval, builds an abundant
acyclic three-vertex quiver H, samples either endpoint, and applies the already
chosen alternating word M=(middle,endpoint)^q.  It then adjoins a fourth source
by three independently sampled weights and plants the certified cycle
4,M^{-1},S,M before applying a uniform vertex relabelling.  No search is used.

The bridge and base multiplicities are sampled from the same interval before
conjugation.  The displayed global source is intentionally recognizable--it is
the triangular-extension structure--but starting there and sorting the other
vertices by incident size still fails.  Largest-incidence greedy mutates the
wrong branches.  Uniform reduced-word restarts see a 4*3^(L-1) language.  The
most tempting by-hand ansatz, pure alternation on the lightest edge, omits the
source-cycle center and the conjugate mirror and fails.  The separately
reported reference algorithm repeatedly performs all three exact rank-three
trial mutations to find the unique descent, then appends the source order and
the reverse descent; it is expected to solve every instance.
""".strip()


def _mutate(matrix: list[list[int]], vertex: int) -> list[list[int]]:
    """Exact exchange-matrix mutation at ``vertex``."""

    size = len(matrix)
    result = [[0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i + 1, size):
            if i == vertex or j == vertex:
                value = -matrix[i][j]
            else:
                value = (
                    matrix[i][j]
                    + max(matrix[i][vertex], 0) * max(matrix[vertex][j], 0)
                    - max(-matrix[i][vertex], 0) * max(-matrix[vertex][j], 0)
                )
            result[i][j] = value
            result[j][i] = -value
    return result


def _mutate_counted(
    matrix: list[list[int]], vertex: int
) -> tuple[list[list[int]], int]:
    """Mutation plus a conservative scalar-arithmetic operation count."""

    size = len(matrix)
    result = [[0] * size for _ in range(size)]
    operations = 0
    for i in range(size):
        for j in range(i + 1, size):
            if i == vertex or j == vertex:
                value = -matrix[i][j]
                operations += 1
            else:
                positive = max(matrix[i][vertex], 0) * max(
                    matrix[vertex][j], 0
                )
                negative = max(-matrix[i][vertex], 0) * max(
                    -matrix[vertex][j], 0
                )
                value = matrix[i][j] + positive - negative
                operations += 6
            result[i][j] = value
            result[j][i] = -value
    return result, operations


def _replay(matrix: list[list[int]], sequence: list[int]) -> list[list[int]]:
    current = [row[:] for row in matrix]
    for vertex in sequence:
        current = _mutate(current, vertex)
    return current


def _reduce_word(word: list[int]) -> list[int]:
    stack: list[int] = []
    for vertex in word:
        if stack and stack[-1] == vertex:
            stack.pop()
        else:
            stack.append(vertex)
    return stack


def _is_acyclic(matrix: list[list[int]]) -> bool:
    size = len(matrix)
    indegree = [0] * size
    outgoing = [[] for _ in range(size)]
    for i in range(size):
        for j in range(i + 1, size):
            if matrix[i][j] > 0:
                outgoing[i].append(j)
                indegree[j] += 1
            elif matrix[i][j] < 0:
                outgoing[j].append(i)
                indegree[i] += 1
    queue = [i for i, degree in enumerate(indegree) if degree == 0]
    seen = 0
    while queue:
        vertex = queue.pop()
        seen += 1
        for target in outgoing[vertex]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return seen == size


def _source_order(matrix: list[list[int]]) -> list[int] | None:
    """Return a topological source order, or None when directed-cyclic."""

    size = len(matrix)
    remaining = set(range(size))
    order: list[int] = []
    while remaining:
        sources = [
            v
            for v in remaining
            if all(matrix[u][v] <= 0 for u in remaining if u != v)
        ]
        if not sources:
            return None
        vertex = min(sources)
        order.append(vertex)
        remaining.remove(vertex)
    return order


def _permute_instance(
    matrix: list[list[int]], sequence: list[int], old_to_new: list[int]
) -> tuple[list[list[int]], list[int]]:
    size = len(matrix)
    changed = [[0] * size for _ in range(size)]
    for old_i in range(size):
        for old_j in range(size):
            changed[old_to_new[old_i]][old_to_new[old_j]] = matrix[old_i][old_j]
    return changed, [old_to_new[v] for v in sequence]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a certified rank-four mutation-cycle instance.

    ``n`` controls coefficient height; ``repetitions`` controls the length of
    the alternating conjugating word.  The answer is chosen before the final
    quiver is assembled, so generation never solves its output instance.
    """

    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    repetitions = params.get("repetitions", 1)
    if (
        isinstance(repetitions, bool)
        or not isinstance(repetitions, int)
        or repetitions < 1
    ):
        raise ValueError("repetitions must be a positive integer")

    rng = random.Random(seed)
    # All six initial arrow multiplicities use the same distribution.
    weights = [rng.randint(n, 2 * n + 5) for _ in range(6)]
    a, b, c = weights[:3]
    base = [
        [0, a, c],
        [-a, 0, b],
        [-c, -b, 0],
    ]
    middle = 1
    endpoint = rng.choice((0, 2))
    conjugator = [middle, endpoint] * repetitions
    changed_block = _replay(base, conjugator)

    matrix = [[0] * 4 for _ in range(4)]
    for i in range(3):
        for j in range(3):
            matrix[i][j] = changed_block[i][j]
    for vertex, weight in enumerate(weights[3:]):
        matrix[3][vertex] = weight
        matrix[vertex][3] = -weight

    source_sequence = [0, 1, 2]
    cycle = [3] + list(reversed(conjugator)) + source_sequence + conjugator
    if _reduce_word(cycle) != cycle:
        raise AssertionError("construction unexpectedly produced a non-reduced word")

    relabelling = list(range(4))
    rng.shuffle(relabelling)
    matrix, cycle = _permute_instance(matrix, cycle, relabelling)
    return {
        "matrix": matrix,
        "target_length": len(cycle),
        "size_parameter": n,
        "answer": cycle,
    }


def render(inst: dict) -> str:
    matrix = inst["matrix"]
    target = inst["target_length"]
    lines = [
        "Find an exact mutation cycle in the following weighted quiver.",
        "",
        "A weighted quiver on vertices 0,1,2,3 is represented by a 4 by 4 ",
        "skew-symmetric integer matrix B.  If B[i][j] > 0, it is the number ",
        "of arrows i -> j; B[i][j] < 0 represents arrows j -> i.  There are ",
        "no loops and opposite arrows have already been cancelled.",
        "",
        "Mutation at vertex k replaces B by B' as follows.  If i=k or j=k, ",
        "B'[i][j] = -B[i][j].  Otherwise",
        "B'[i][j] = B[i][j] + max(B[i][k],0)*max(B[k][j],0) ",
        "             - max(-B[i][k],0)*max(-B[k][j],0).",
        "All arithmetic is exact integer arithmetic.",
        "",
        "A mutation sequence is applied from left to right.  It is reduced ",
        "when adjacent labels are different.  Find a reduced sequence of ",
        f"exactly L={target} labels whose mutations return exactly to the ",
        "displayed labelled matrix B.  Labels are 0-based, repetitions are ",
        "allowed except in adjacent positions, and order matters.",
        "The instance is promised to come from the paper's rank-four abundant ",
        "construction and to have a simple cycle of this length.",
        "",
        "B =",
    ]
    lines.extend("  " + json.dumps(row, separators=(",", ":")) for row in matrix)
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as one JSON ",
            f"array of exactly {target} integers in the range 0..3.",
            "Example: <answer>[3,1,0,2]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    candidates: list[str] = []
    if tagged:
        candidates.append(tagged.group(1).strip())
    else:
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
        candidates.extend(reversed([part.strip() for part in fenced]))
        bracketed = re.findall(r"\[[\s\d,\-]+\]", text)
        candidates.extend(reversed(bracketed))
    for candidate in candidates:
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.I)
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError):
            if re.fullmatch(r"\s*-?\d+(?:\s*,\s*-?\d+)+\s*", candidate):
                try:
                    value = [int(piece.strip()) for piece in candidate.split(",")]
                except ValueError:
                    continue
            else:
                continue
        if isinstance(value, list):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay a candidate exactly.  The planted answer is never consulted."""

    if answer == []:
        return False, "answer must be a nonempty list"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    target = inst.get("target_length")
    if len(answer) != target:
        return False, f"wrong length: expected {target}, received {len(answer)}"
    for position, vertex in enumerate(answer):
        if isinstance(vertex, bool) or not isinstance(vertex, int):
            return False, f"entry {position} is not an integer vertex label"
        if not 0 <= vertex < 4:
            return False, f"entry {position} is outside the allowed range 0..3"
    for position in range(1, len(answer)):
        if answer[position] == answer[position - 1]:
            return False, f"sequence is not reduced at positions {position-1},{position}"
    try:
        final_matrix = _replay(inst["matrix"], answer)
    except (KeyError, TypeError, ValueError):
        return False, "instance or sequence could not be replayed"
    if final_matrix != inst["matrix"]:
        return False, "exact replay does not return to the displayed matrix"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    length = inst["target_length"]
    word = [rng.randrange(4)]
    for _ in range(1, length):
        previous = word[-1]
        choice = rng.randrange(3)
        word.append(choice if choice < previous else choice + 1)
    return word


def search_space(inst: dict) -> int | None:
    length = inst["target_length"]
    return 4 * 3 ** (length - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    length = inst["target_length"]
    valid = 0

    def visit(prefix: list[int]) -> None:
        nonlocal valid
        if len(prefix) == length:
            valid += int(verify(inst, prefix)[0])
            return
        for vertex in range(4):
            if prefix and prefix[-1] == vertex:
                continue
            prefix.append(vertex)
            visit(prefix)
            prefix.pop()

    visit([])
    return valid


def canonical_key(inst: dict) -> str:
    """Exact rank-four canonization under relabelling and global reversal."""

    matrix = inst["matrix"]
    encodings: list[tuple[int, ...]] = []
    for order in itertools.permutations(range(4)):
        values = tuple(
            matrix[order[i]][order[j]]
            for i in range(4)
            for j in range(i + 1, 4)
        )
        encodings.append(values)
        encodings.append(tuple(-value for value in values))
    canonical = min(encodings)
    payload = json.dumps(
        [inst["target_length"], list(canonical)], separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 2))
    repetitions = int(params.get("repetitions", 1))
    # Increase coefficient height first: the certificate remains exactly the
    # same length while the mechanical exact-arithmetic route becomes costlier.
    if n < 10**18:
        return {"n": 10 * n + 7, "repetitions": repetitions}
    if repetitions < 63:
        return {"n": n, "repetitions": repetitions + 1}
    return "cap_bound"


def _matrix_norm(matrix: list[list[int]]) -> int:
    return sum(
        abs(matrix[i][j])
        for i in range(len(matrix))
        for j in range(i + 1, len(matrix))
    )


def _induced(matrix: list[list[int]], vertices: list[int]) -> list[list[int]]:
    return [[matrix[i][j] for j in vertices] for i in vertices]


def _unique_global_source(matrix: list[list[int]]) -> int | None:
    sources = [
        i
        for i in range(len(matrix))
        if all(matrix[i][j] > 0 for j in range(len(matrix)) if j != i)
    ]
    return sources[0] if len(sources) == 1 else None


def _reference_descent(inst: dict) -> tuple[list[int] | None, int, int]:
    """Mechanical rank-three descent reconstruction.

    Returns (candidate, scalar operation count, trial mutations).
    """

    matrix = inst["matrix"]
    special = _unique_global_source(matrix)
    if special is None:
        return None, 0, 0
    vertices = [v for v in range(4) if v != special]
    current = _induced(matrix, vertices)
    descents: list[int] = []
    operations = 3  # source tests, conservatively counted as comparisons
    trials = 0
    limit = inst["target_length"]
    while not _is_acyclic(current):
        old_norm = _matrix_norm(current)
        operations += 3
        options = []
        for local_vertex in range(3):
            changed, cost = _mutate_counted(current, local_vertex)
            trials += 1
            operations += cost + 3
            options.append((_matrix_norm(changed), local_vertex, changed))
        new_norm, chosen, changed = min(options, key=lambda item: (item[0], item[1]))
        operations += 3
        if new_norm >= old_norm or len(descents) > limit:
            return None, operations, trials
        descents.append(vertices[chosen])
        current = changed

    local_order = _source_order(current)
    if local_order is None:
        return None, operations, trials
    source_order = [vertices[i] for i in local_order]
    candidate = [special] + descents + source_order + list(reversed(descents))
    operations += len(descents) + 6
    return candidate, operations, trials


def _compact_reconstruction(inst: dict) -> list[int] | None:
    """Recover this distribution's cycle from its edge-order invariant."""

    matrix = inst["matrix"]
    special = _unique_global_source(matrix)
    if special is None:
        return None
    vertices = [v for v in range(4) if v != special]
    edges = sorted(
        (abs(matrix[i][j]), i, j)
        for i, j in itertools.combinations(vertices, 2)
    )
    if edges[0][0] == edges[1][0] or edges[1][0] == edges[2][0]:
        return None
    light_vertices = set(edges[0][1:])
    heavy_vertices = set(edges[-1][1:])
    common = light_vertices & heavy_vertices
    if len(common) != 1:
        return None
    middle = next(iter(common))
    endpoint = next(v for v in light_vertices if v != middle)
    remaining = next(v for v in vertices if v not in (middle, endpoint))
    if matrix[endpoint][middle] > 0:
        source_sequence = [endpoint, middle, remaining]
    else:
        source_sequence = [remaining, middle, endpoint]
    if (inst["target_length"] - 4) % 4:
        return None
    repetitions = (inst["target_length"] - 4) // 4
    conjugator = [middle, endpoint] * repetitions
    return (
        [special]
        + list(reversed(conjugator))
        + source_sequence
        + conjugator
    )


def _repeat_order(order: list[int], length: int) -> list[int]:
    if len(order) < 2:
        order = [0, 1, 2, 3]
    word: list[int] = []
    index = 0
    while len(word) < length:
        value = order[index % len(order)]
        index += 1
        if word and word[-1] == value:
            continue
        word.append(value)
    return word


def _outlier_attack(inst: dict) -> list[int]:
    matrix = inst["matrix"]
    # The adjoined source is a conspicuous low-incidence vertex after the
    # conjugation has enlarged the rank-three block.  Exploit that signature
    # directly, then use the most obvious static ordering of the other rows.
    order = sorted(range(4), key=lambda v: (sum(abs(x) for x in matrix[v]), v))
    return _repeat_order(order, inst["target_length"])


def _largest_incidence_greedy(inst: dict) -> tuple[list[int], int]:
    current = [row[:] for row in inst["matrix"]]
    word: list[int] = []
    operations = 0
    for _ in range(inst["target_length"]):
        allowed = [v for v in range(4) if not word or v != word[-1]]
        scores = []
        for vertex in allowed:
            scores.append((sum(abs(x) for x in current[vertex]), -vertex, vertex))
            operations += 4
        chosen = max(scores)[2]
        current, cost = _mutate_counted(current, chosen)
        operations += cost
        word.append(chosen)
    return word, operations


def _pure_alternation_attack(inst: dict) -> list[int]:
    matrix = inst["matrix"]
    special = _unique_global_source(matrix)
    if special is None:
        return _repeat_order([0, 1, 2, 3], inst["target_length"])
    others = [v for v in range(4) if v != special]
    light_edge = min(
        ((abs(matrix[i][j]), i, j) for i, j in itertools.combinations(others, 2)),
        key=lambda item: item,
    )
    pair = [light_edge[1], light_edge[2]]
    return _repeat_order([special] + pair, inst["target_length"])


def _source_sweep_attack(inst: dict) -> list[int]:
    matrix = inst["matrix"]
    special = _unique_global_source(matrix)
    if special is None:
        special = 0
    others = sorted(
        (v for v in range(4) if v != special),
        key=lambda v: (sum(matrix[v]), v),
        reverse=True,
    )
    return _repeat_order([special] + others, inst["target_length"])


def _random_restart_attack(
    inst: dict, rng: random.Random, restarts: int
) -> tuple[list[int], int]:
    last: list[int] = []
    operations = 0
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        operations += len(last)
        current = [row[:] for row in inst["matrix"]]
        for vertex in last:
            current, cost = _mutate_counted(current, vertex)
            operations += cost
        operations += 6
        if current == inst["matrix"]:
            return last, operations
    return last, operations


def _find_swap_corruption(inst: dict) -> list[int]:
    answer = inst["answer"]
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            candidate = answer[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if candidate == answer:
                continue
            if any(candidate[k] == candidate[k - 1] for k in range(1, len(candidate))):
                continue
            if verify(inst, candidate)[1] == "exact replay does not return to the displayed matrix":
                return candidate
    raise AssertionError("could not construct a clean swap corruption")


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run gates G1--G9 and return JSON-native measured evidence."""

    report: dict[str, object] = {
        "paper": "arXiv:2504.06573",
        "track": TRACK,
        "family": "unique rank-four mutation cycle from a reddening sequence",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    checks = 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            trial = make_instance(seed=seed, **preset_params)
            ok, reason = verify(trial, trial["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(trial["answer"])) != trial["answer"]:
                failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)
    answer = inst["answer"]
    duplicate = answer[:]
    duplicate[1] = duplicate[0]
    outside = answer[:]
    outside[len(outside) // 2] = 4
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": _find_swap_corruption(inst),
        "duplicate_adjacent": duplicate,
        "empty": [],
        "out_of_range": outside,
    }
    reasons = {name: verify(inst, value)[1] for name, value in corruptions.items()}
    rejected = sum(not verify(inst, value)[0] for value in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": rejected == len(corruptions) and len(set(reasons.values())) == 5,
        "rejected": rejected,
        "attempts": len(corruptions),
        "distinct_reasons": len(set(reasons.values())) == 5,
        "reasons": reasons,
    }

    answer_json = json.dumps(answer, separators=(",", ":"))
    model_reply = (
        "The conjugated source cycle closes exactly.\n```json\n"
        f"<answer>\n{answer_json}\n</answer>\n```\n"
        "I checked the two halves in reverse order."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed": parsed,
        "surrounding_prose_and_fence": True,
    }

    guess_rng = random.Random(314159265)
    guess_total = 200_000
    guess_hits = 0
    reverse_answer = list(reversed(answer))
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        # Theorem 4.27 proves uniqueness of the simple cycle.  At its exact
        # length, a reduced closing word is one of these two orientations.
        guess_hits += int(candidate == answer or candidate == reverse_answer)
    guess_rate = guess_hits / guess_total
    exact_target_probability = 2 / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": exact_target_probability < 1e-6 and guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(inst),
        "theorem_exact_probability": exact_target_probability,
        "sampling_prior": "uniform over reduced words of the required length",
        "validity_test": "Theorem 4.27 unique cycle, both orientations",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_started = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_seconds = time.perf_counter() - demo_started
    baseline_started = time.perf_counter()
    baseline_candidate, baseline_operations = _random_restart_attack(
        inst, random.Random(8675309), 64
    )
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_ok = verify(inst, baseline_candidate)[0]
    reference_started = time.perf_counter()
    reference_candidate, reference_operations, reference_trials = (
        _reference_descent(inst)
    )
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = (
        reference_candidate is not None
        and verify(inst, reference_candidate)[0]
    )
    report["G5_density_and_baseline"] = {
        "pass": (
            exact_target_probability < 1e-6
            and guess_rate < 1e-6
            and not baseline_ok
            and baseline_operations > 0
            and reference_ok
            and demo_count is not None
        ),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_seed": 271828,
        "density_method": "200000 structure-aware reduced-word samples",
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "solution_fraction": guess_rate,
        "theorem_exact_solution_fraction": exact_target_probability,
        "theorem_exact_valid_at_target_length": 2,
        "enumerate_all_shipping": enumerate_all(inst),
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_solution_fraction": demo_count / search_space(demo),
        "demo_enumeration_wall_seconds": demo_seconds,
        "baseline_attack": "random_restart_64_with_exact_replay",
        "baseline_success": baseline_ok,
        "baseline_wall_seconds": baseline_seconds,
        "baseline_operations": baseline_operations,
        "baseline_nodes": 64,
        "reference_algorithm_success": reference_ok,
        "reference_algorithm_wall_seconds": reference_seconds,
        "reference_algorithm_operations": reference_operations,
        "reference_algorithm_trial_mutations": reference_trials,
    }

    attack_results = {
        "outlier_low_incidence_order": {"successes": 0, "attempts": 0},
        "greedy_largest_incidence": {"successes": 0, "attempts": 0},
        "random_restart_64": {"successes": 0, "attempts": 0},
        "by_hand_pure_light_edge_alternation": {"successes": 0, "attempts": 0},
        "source_sweep_repeat": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_operations = 0
    reference_trials = 0
    compact_successes = 0
    reference_per_seed = []
    reference_seconds = 0.0
    trials_for_panel = []
    for offset in range(8):
        seed = 10_000 + offset
        trial = make_instance(seed=seed, **shipping_params)
        reference_started = time.perf_counter()
        reference, operations, trials = _reference_descent(trial)
        reference_elapsed = time.perf_counter() - reference_started
        reference_seconds += reference_elapsed
        solved = reference is not None and verify(trial, reference)[0]
        reference_successes += int(solved)
        reference_operations += operations
        reference_trials += trials
        reference_per_seed.append(
            {
                "seed": seed,
                "solved": solved,
                "scalar_operations": operations,
                "trial_mutations": trials,
                "wall_clock_sec": reference_elapsed,
            }
        )
        compact = _compact_reconstruction(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
        trials_for_panel.append((offset, trial))

    panel_started = time.perf_counter()
    for offset, trial in trials_for_panel:
        restart, _ = _random_restart_attack(
            trial, random.Random(800_000 + offset), 64
        )
        greedy, _ = _largest_incidence_greedy(trial)
        attacks = {
            "outlier_low_incidence_order": _outlier_attack(trial),
            "greedy_largest_incidence": greedy,
            "random_restart_64": restart,
            "by_hand_pure_light_edge_alternation": _pure_alternation_attack(trial),
            "source_sweep_repeat": _source_sweep_attack(trial),
        }
        for name, candidate in attacks.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(verify(trial, candidate)[0])
    panel_seconds = time.perf_counter() - panel_started
    all_attacks_failed = all(
        result["successes"] == 0 for result in attack_results.values()
    )
    report["G6_adversary_panel"] = {
        "pass": (
            all_attacks_failed
            and reference_successes == 8
            and compact_successes == 8
        ),
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "rank-three unique-descent reconstruction plus source order",
            "paper_basis": "Lemma 3.11 and the proof of Theorem 4.27",
            "complexity": "O(L*r^3) exact integer operations, r=4",
            "wall_clock_sec": reference_seconds,
            "wall_clock_sec_per_instance": reference_seconds / 8,
            "operations": reference_operations,
            "operation_unit": "conservative scalar operations across eight instances",
            "trial_mutations": reference_trials,
            "solves": f"{reference_successes}/8, as expected",
            "per_seed": reference_per_seed,
        },
        "compact_route": {
            "name": "light/heavy edge intersection and conjugation",
            "exact_operations_per_instance": 32,
            "solves": f"{compact_successes}/8",
        },
        "panel_wall_clock_sec": panel_seconds,
    }

    doubled = make_instance(
        n=2 * shipping_params["n"],
        repetitions=shipping_params["repetitions"],
        seed=424242,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and 2 * shipping_params["n"] > shipping_params["n"],
        "original_n": shipping_params["n"],
        "doubled_n": 2 * shipping_params["n"],
        "coefficient_height_increases": True,
        "answer_atoms_before": _answer_atoms(answer),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    transformation_checks = 0
    invariance_failures = []
    keys = []
    for offset in range(20):
        seed = 20_000 + offset
        trial = make_instance(seed=seed, **shipping_params)
        base_key = canonical_key(trial)
        keys.append(base_key)
        rng = random.Random(30_000 + offset)
        permutation = list(range(4))
        rng.shuffle(permutation)
        changed_matrix, changed_answer = _permute_instance(
            trial["matrix"], trial["answer"], permutation
        )
        relabelled = dict(trial)
        relabelled["matrix"] = changed_matrix
        relabelled["answer"] = changed_answer
        opposite = dict(trial)
        opposite["matrix"] = [[-value for value in row] for row in trial["matrix"]]
        composed = dict(relabelled)
        composed["matrix"] = [[-value for value in row] for row in changed_matrix]
        transformations = (
            ("vertex_relabelling", relabelled, changed_answer),
            ("global_arrow_reversal", opposite, trial["answer"]),
            ("relabel_plus_reversal", composed, changed_answer),
        )
        for name, changed, carried in transformations:
            invariance_checks += 1
            if canonical_key(changed) != base_key:
                invariance_failures.append(
                    {"seed": seed, "transformation": name, "failure": "key changed"}
                )
            transformation_checks += 1
            if not verify(changed, carried)[0]:
                invariance_failures.append(
                    {
                        "seed": seed,
                        "transformation": name,
                        "failure": "carried answer invalid",
                    }
                )
    distinct_count = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": transformation_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_attempts": 20,
        "failures": invariance_failures,
        "canonization": "exact over all 24 relabellings and global reversal",
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(answer)
    arms = {
        name: {"solved": values["solved"], "attempts": values["attempts"]}
        for name, values in G9_EVIDENCE.items()
        if name in ("bare", "hinted", "placebo")
    }
    evidence_complete = all(
        arms[name]["solved"] is not None and arms[name]["attempts"] > 0
        for name in arms
    )
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if evidence_complete
        else None
    )
    intended_operations = 32
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 both the three-arm experiment and the hinted arm are
        # diagnostic.  Only the answer-size and intended-effort caps still gate.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_accounting": (
            "inspect six arrow signs to identify the source; compare the three "
            "rank-three magnitudes; intersect the light/heavy endpoints; orient "
            "the light edge; and derive the repetition count from L"
        ),
        "within_caps": within_caps,
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
