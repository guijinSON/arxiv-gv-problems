"""Verified generator for breakpoint-tight pancake-flipping witnesses.

The paper proves that minimum sorting by prefix reversals is NP-hard, and even
that deciding whether the elementary breakpoint lower bound is tight is
NP-hard.  This module stays in the paper's native objects: a stack of distinct
pancake sizes and a concrete word of prefix reversals.

Generation is inverse.  Starting from sorted sizes, it composes a random word
in which every flip creates exactly one breakpoint.  Reversing that word is a
sorting certificate of exactly the breakpoint lower bound, hence an optimal
certificate; no generated instance is solved to obtain its answer.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


# Keep the repository helper package reachable when harden.py imports this file
# from results/1111.0434.  This family needs no nontrivial helper at runtime, so
# absence of gvlib leaves it fully standard-library-only.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module does not rely on them
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "stack of distinct pancake sizes",
        "word of prefix reversals",
        "rank breakpoints",
    ],
    "verification_operations": [
        "exact prefix reversal replay",
        "integer comparison",
        "permutation parity check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Every flip in a lower-bound-tight route must remove one rank "
        "breakpoint, reducing the apparent n-way move choice to a binary "
        "but deep reconfiguration tree."
    ),
    "hardness_basis": (
        "Track A: Theorem 19 proves NP-hardness for unsigned permutations in "
        "the exact breakpoint-tight regime; the shipping distribution uses "
        "240 breakpoints on 245 pancakes, and transposition-pruned exhaustive "
        "efficient-"
        "path DFS solved 0/8 after 250,000 nodes per instance (2,000,000 nodes "
        "total in 50.135166 seconds); the theorem is worst-case, while this "
        "measured baseline is the evidence for the generated distribution."
    ),
    "max_answer_tokens": 481,
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


# Here n is the number of breakpoint-creating inverse steps, hence both the
# breakpoint count and the certificate length.  ``slack`` adds possible cut
# locations without lengthening the answer.  The named ladder stays in the
# empirically difficult high-breakpoint-density window.
DIFFICULTY = {
    "demo": {"n": 3, "slack": 3},
    "easy": {"n": 240, "slack": 5},
    "medium": {"n": 240, "slack": 30},
    "hard": {"n": 240, "slack": 48},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The useful invariant is that every flip in a breakpoint-tight route must "
    "decrease the rank-breakpoint count by exactly one."
)

PLACEBO_HINT = (
    "The useful discipline is that every flip in a submitted route must be "
    "listed with its prefix length in exact execution order."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A reduced word of exactly db(stack) prefix lengths; every length is an "
        "integer in [2,p] for p pancakes, adjacent lengths differ, and the xor "
        "of reversal parities equals the stack permutation parity."
    ),
    "bounds": {
        "length": "exactly db(stack) (240 at every non-demo preset)",
        "flip_length_min": 2,
        "flip_length_max": "number of pancakes",
        "adjacent_equal": False,
        "global_parity": "must equal the rank permutation parity",
    },
}

NOTES = (
    "Section 2 fixes all definitions used here: an unsigned stack is a "
    "permutation, a flip reverses a prefix, a breakpoint is a nonconsecutive "
    "rank adjacency (plus a wrong bottom pancake), and Property 1 says one flip "
    "changes the count by at most one.  Theorem 19 is the hardness result: "
    "MIN-SBPR is NP-hard, and deciding whether db(S) flips suffice is already "
    "NP-hard.  The introduction also records the easy routes that ruled out the "
    "initial triage proposal: arbitrary sorting has a direct linear-length "
    "pancake algorithm and a 2-approximation, while simple permutations have a "
    "polynomial-time treatment.  The paper's Definition 8 reduction was not "
    "used for generation because it expands l variables and k clauses to "
    "31l+98k pancakes and 16l+50k certificate flips; under the 256-atom cap its "
    "native path exposes at most six relevant Boolean variables.  Instead, "
    "inverse generation starts at the identity and samples every hidden flip "
    "uniformly from moves that create exactly one breakpoint.  The reverse word "
    "therefore has db(S) flips and is optimal by Property 1.  Smaller tight "
    "walks were rejected after exhaustive efficient-path search solved them; "
    "the shipping window uses 240 flips, below all G9 caps.  Random increasing "
    "size labels prevent magnitude gaps from marking cuts.  The attack panel "
    "measures a boundary-gap outlier, smallest-cut efficient greedy, randomized "
    "efficient walks, width-128 beam search, and transposition-pruned exhaustive "
    "DFS."
)


# Filled after the three script-owned oracle runs.  These are diagnostics under
# the current protocol; only the answer/operation caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _rank_permutation(stack):
    """Return the 1..n rank of each distinct displayed pancake size."""
    ordered = sorted(stack)
    if len(set(ordered)) != len(ordered):
        raise ValueError("pancake sizes must be distinct")
    rank = {value: i + 1 for i, value in enumerate(ordered)}
    return [rank[value] for value in stack]


def _breakpoint_count(permutation):
    """The paper's db: internal non-adjacencies plus a wrong bottom rank."""
    if not permutation:
        return 0
    return sum(
        abs(left - right) != 1
        for left, right in zip(permutation, permutation[1:])
    ) + (permutation[-1] != len(permutation))


def _breakpoint_delta(permutation, length):
    """Change in db caused by one prefix reversal, in O(1)."""
    n = len(permutation)
    if length == n:
        return int(permutation[0] != n) - int(permutation[-1] != n)
    old_boundary = abs(permutation[length - 1] - permutation[length]) != 1
    new_boundary = abs(permutation[0] - permutation[length]) != 1
    return int(new_boundary) - int(old_boundary)


def _draw_scramble(pancakes, steps, rng):
    """Compose a reduced all-+1-breakpoint word without solving its output."""
    for _attempt in range(128):
        permutation = list(range(1, pancakes + 1))
        word = []
        for _step in range(steps):
            choices = [
                length
                for length in range(2, pancakes + 1)
                if (not word or length != word[-1])
                and _breakpoint_delta(permutation, length) == 1
            ]
            if not choices:
                break
            length = rng.choice(choices)
            permutation[:length] = reversed(permutation[:length])
            word.append(length)
        else:
            assert _breakpoint_count(permutation) == steps
            return permutation, list(reversed(word))

    raise RuntimeError("could not draw the breakpoint-creating inverse walk")


def make_instance(n, seed=0, **params):
    """Inverse-generate an optimal word, then hide ranks as exact sizes.

    ``n`` is the size parameter and equals the certificate length.  The actual
    stack has ``n + slack`` pancakes, so larger n deepens the binary efficient-
    path tree while ``slack`` tunes crowding at fixed answer length.
    """
    slack = params.pop("slack", max(3, n // 48))
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("slack", slack)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if n < 2:
        raise ValueError("n must be at least 2")
    if slack < 1:
        raise ValueError("slack must be positive")
    pancakes = n + slack

    rng = random.Random(seed)
    rank_stack, answer = _draw_scramble(pancakes, n, rng)

    # Any strictly increasing replacement of ranks is the same physical stack.
    # Independent random gaps prevent raw magnitude gaps from marking flip cuts.
    sizes_by_rank = []
    value = rng.randrange(-1_000_000, 1_000_001)
    for _ in range(pancakes):
        value += rng.randrange(2, 20)
        sizes_by_rank.append(value)
    stack = [sizes_by_rank[rank - 1] for rank in rank_stack]

    return {
        "n": pancakes,
        "size_parameter": n,
        "stack": stack,
        # Exact derived data used by repeated grading.  It is not secret (the
        # renderer defines ranks), and order-preserving relabelings keep it valid.
        "rank_stack": rank_stack,
        "permutation_parity": _permutation_parity(rank_stack),
        "rank_positions": [
            rank_stack.index(rank) + 1 for rank in range(1, pancakes + 1)
        ],
        "max_flips": n,
        "breakpoints": n,
        "slack": slack,
        "answer": answer,
    }


def render(inst):
    """Return the complete standalone statement and output contract."""
    stack = ", ".join(map(str, inst["stack"]))
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""Bounded pancake sorting by prefix reversals

A stack contains {inst['n']} pancakes of distinct integer sizes.  It is written
from top to bottom.  A prefix reversal of length k reverses exactly the first k
pancakes; k is an integer and 2 <= k <= {inst['n']}.  The goal is the unique
increasing top-to-bottom order (smallest pancake first).

Find a sequence of exactly {inst['max_flips']} prefix reversals that sorts this
stack.  Consecutive reversals must have different lengths; immediate duplicate
flips are forbidden.  Apply the listed lengths from left to right.  Repeated
lengths are otherwise allowed, and order matters.

For clarity, the rank of a pancake is its position after sorting, from rank 1
(smallest) through rank {inst['n']} (largest).  A rank breakpoint is either an
adjacent pair whose ranks do not differ by 1, or the bottom position when the
bottom pancake does not have rank {inst['n']}.  This stack has exactly
{inst['breakpoints']} rank breakpoints, so no sorting sequence can use fewer
than {inst['breakpoints']} flips.

Initial stack, top to bottom:
[{stack}]
{hint}

Give your final answer inside <answer></answer> tags, as one JSON-style
comma-separated list of exactly {inst['max_flips']} integer prefix lengths, in
execution order.
Example of the syntax: <answer>[2, 3, 2]</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)
_RAW_LIST_RE = re.compile(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*")


def parse_answer(text):
    """Parse the last tagged integer list, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) < 2:
            return None
        body = "\n".join(lines[1:-1]).strip()
    try:
        if body.startswith("[") and body.endswith("]"):
            value = json.loads(body)
        elif _RAW_LIST_RE.fullmatch(body):
            value = [int(part.strip()) for part in body.split(",")]
        else:
            return None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def _flip_parity(length):
    """Parity of reversing length items: C(length,2) modulo two."""
    return (length * (length - 1) // 2) & 1


def _permutation_parity(permutation):
    seen = [False] * len(permutation)
    cycles = 0
    for start in range(len(permutation)):
        if seen[start]:
            continue
        cycles += 1
        at = start
        while not seen[at]:
            seen[at] = True
            at = permutation[at] - 1
    return (len(permutation) - cycles) & 1


def verify(inst, answer):
    """Replay any legal candidate word; never consult inst['answer']."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of prefix lengths"
    if not answer:
        return False, "answer is empty"
    if len(answer) < inst["breakpoints"]:
        return False, "fewer flips than the rank-breakpoint lower bound"
    if len(answer) > inst["max_flips"]:
        return False, "too many prefix reversals"
    if any(isinstance(length, bool) or not isinstance(length, int) for length in answer):
        return False, "every prefix length must be an integer"
    if any(length < 2 or length > inst["n"] for length in answer):
        return False, f"a prefix length is outside 2..{inst['n']}"
    if any(left == right for left, right in zip(answer, answer[1:])):
        return False, "consecutive prefix lengths must differ"

    permutation = inst.get("rank_stack")
    if permutation is None:
        permutation = _rank_permutation(inst["stack"])
    needed_parity = inst.get("permutation_parity")
    if needed_parity is None:
        needed_parity = _permutation_parity(permutation)
    supplied_parity = 0
    for length in answer:
        supplied_parity ^= _flip_parity(length)
    if supplied_parity != needed_parity:
        return False, "wrong total reversal parity"

    # Before materialising every reversed prefix, track a few individual
    # pancakes.  This is an exact necessary condition, not a probabilistic
    # shortcut, and rejects almost every random word after O(word length) small
    # integer operations.  Candidates passing it still receive a full replay.
    positions = inst.get("rank_positions")
    if positions is None:
        positions = [permutation.index(rank) + 1 for rank in range(1, inst["n"] + 1)]
    probe_ranks = (inst["n"], 1, (inst["n"] + 1) // 2)
    for rank in probe_ranks:
        position = positions[rank - 1]
        for length in answer:
            if position <= length:
                position = length + 1 - position
        if position != rank:
            return (
                False,
                f"sequence does not sort: rank {rank} ends at position {position}",
            )

    work = list(permutation)
    for length in answer:
        work[:length] = reversed(work[:length])
    target = list(range(1, inst["n"] + 1))
    if work != target:
        mismatch = next(i for i, (got, want) in enumerate(zip(work, target)) if got != want)
        return (
            False,
            f"sequence does not sort: first mismatch at position {mismatch}",
        )
    return True, "ok"


@functools.lru_cache(maxsize=None)
def _flip_catalog(n):
    even = tuple(length for length in range(2, n + 1) if _flip_parity(length) == 0)
    odd = tuple(length for length in range(2, n + 1) if _flip_parity(length) == 1)
    return even, odd


@functools.lru_cache(maxsize=None)
def _suffix_count(n, remaining, previous_category, needed_parity):
    """Count reduced parity-constrained suffixes after a previous flip class."""
    if remaining == 0:
        return int(needed_parity == 0)
    catalogs = _flip_catalog(n)
    total = 0
    for category in (0, 1):
        choices = len(catalogs[category]) - int(previous_category == category)
        if choices:
            total += choices * _suffix_count(
                n, remaining - 1, category, needed_parity ^ category
            )
    return total


def search_space(inst):
    """Exact size of the structure-aware bounded certificate language."""
    parity = inst.get("permutation_parity")
    if parity is None:
        parity = _permutation_parity(_rank_permutation(inst["stack"]))
    return _suffix_count(inst["n"], inst["breakpoints"], 2, parity)


def _uniform_reduced_parity_word(inst, rng):
    """Draw a full-support word satisfying all cheap static constraints."""
    n = inst["n"]
    length = inst["breakpoints"]
    parity = inst.get("permutation_parity")
    if parity is None:
        parity = _permutation_parity(_rank_permutation(inst["stack"]))
    width = max(1, (n - 2).bit_length())
    mask = (1 << width) - 1
    reservoir = rng.getrandbits(width * (length + 1))
    digit = reservoir & mask
    reservoir >>= width
    word = [2 + digit % (n - 1)]
    for _ in range(1, length):
        digit = reservoir & mask
        reservoir >>= width
        chosen = 2 + digit % (n - 2)
        if chosen >= word[-1]:
            chosen += 1
        word.append(chosen)

    supplied = 0
    for chosen in word:
        supplied ^= _flip_parity(chosen)
    if supplied != parity:
        wanted_last_parity = _flip_parity(word[-1]) ^ 1
        replacements = [
            value
            for value in _flip_catalog(n)[wanted_last_parity]
            if len(word) == 1 or value != word[-2]
        ]
        word[-1] = replacements[reservoir % len(replacements)]
    return word


def _efficient_lengths(permutation, previous=0):
    """Return all flips lowering db by one, using the paper's two-choice fact."""
    n = len(permutation)
    head = permutation[0]
    choices = []
    for neighbor in (head - 1, head + 1):
        if not 1 <= neighbor <= n:
            continue
        position = permutation.index(neighbor)
        if (
            position > 0
            and position != previous
            and abs(permutation[position - 1] - neighbor) != 1
        ):
            choices.append(position)
    if head == n and permutation[-1] != n and n != previous:
        choices.append(n)
    return choices


def _efficient_random_walk(inst, rng):
    """Choose uniformly at each efficient branch; pad a dead branch legally."""
    permutation = list(inst.get("rank_stack") or _rank_permutation(inst["stack"]))
    word = []
    while len(word) < inst["breakpoints"]:
        choices = _efficient_lengths(permutation, word[-1] if word else 0)
        if not choices:
            break
        length = rng.choice(choices)
        permutation[:length] = reversed(permutation[:length])
        word.append(length)
    if len(word) == inst["breakpoints"]:
        return word

    # A dead branch is a failed random guess.  Complete its syntax without
    # searching back to the planted route, then enforce the globally forced
    # reversal parity.  The 1% uniform mixture in random_candidate gives the
    # declared language full support.
    static = _uniform_reduced_parity_word(inst, rng)
    for value in static:
        if len(word) == inst["breakpoints"]:
            break
        if not word or value != word[-1]:
            word.append(value)
    while len(word) < inst["breakpoints"]:
        value = rng.randrange(2, inst["n"] + 1)
        if not word or value != word[-1]:
            word.append(value)

    needed = inst.get("permutation_parity")
    if needed is None:
        needed = _permutation_parity(_rank_permutation(inst["stack"]))
    supplied = 0
    for value in word:
        supplied ^= _flip_parity(value)
    if supplied != needed:
        wanted = _flip_parity(word[-1]) ^ 1
        replacements = [
            value
            for value in _flip_catalog(inst["n"])[wanted]
            if len(word) == 1 or value != word[-2]
        ]
        word[-1] = rng.choice(replacements)
    return word


def random_candidate(inst, rng):
    """Sample a construction-aware solver prior without using the planted word.

    Ninety-nine percent of samples follow uniformly random efficient choices
    until they sort or deadlock, modeling the strongest obvious consequence of
    the breakpoint bound.  A one-percent static mixture preserves full support
    over CERTIFICATE_LANGUAGE.  Neither branch consults ``inst['answer']``.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    if rng.randrange(100) == 0:
        return _uniform_reduced_parity_word(inst, rng)
    return _efficient_random_walk(inst, rng)


def enumerate_all(inst):
    """Count valid witnesses exactly only when a capped raw enumeration fits."""
    n = inst["n"]
    raw = sum(
        (n - 1) ** length
        for length in range(inst["breakpoints"], inst["max_flips"] + 1)
    )
    if raw > 250_000:
        return None
    count = 0
    for length in range(inst["breakpoints"], inst["max_flips"] + 1):
        for word in itertools.product(range(2, n + 1), repeat=length):
            if any(a == b for a, b in zip(word, word[1:])):
                continue
            ok, _ = verify(inst, word)
            count += int(ok)
    return count


def canonical_key(inst):
    """Rank-normal form, invariant under every order-preserving size relabeling."""
    payload = {
        "rank_stack": _rank_permutation(inst["stack"]),
        "max_flips": inst["max_flips"],
        "breakpoints": inst["breakpoints"],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    """Use the last writable depth, then report the genuine answer-cap bound."""
    harder = dict(params)
    n = int(harder["n"])
    slack = int(harder.get("slack", max(3, n // 48)))
    # The named presets sweep the useful fixed-length crowding window first.
    # Eight more steps still fit the measured ~500-token budget; beyond that,
    # maintaining breakpoint density necessarily lengthens the answer.
    if n < 248:
        harder["n"] = 248
        harder["slack"] = max(slack, 50)
        return harder
    return "cap_bound"


def _normalise_for_attack(inst):
    return _rank_permutation(inst["stack"])


def _attack_boundary_gap(inst):
    """Guess cuts from the largest displayed per-boundary magnitude gaps."""
    permutation = _normalise_for_attack(inst)
    displayed = list(inst["stack"])
    goal = list(range(1, inst["n"] + 1))
    path = []
    while len(path) < inst["max_flips"] and permutation != goal:
        candidates = []
        for length in range(2, inst["n"] + 1):
            if path and path[-1] == length:
                continue
            gap = (
                abs(displayed[length - 1] - displayed[length])
                if length < inst["n"]
                else 0
            )
            # The construction samples random increasing gaps independently of
            # its flips.  This is precisely the leakage probe: if plants were
            # cut at exceptional magnitudes, this rule would recover them.
            candidates.append((-gap, length))
        if not candidates:
            break
        _, length = min(candidates)
        permutation[:length] = reversed(permutation[:length])
        displayed[:length] = reversed(displayed[:length])
        path.append(length)
    return path


def _attack_largest_first(inst):
    """The elementary polynomial pancake-sort algorithm."""
    permutation = _normalise_for_attack(inst)
    path = []
    for wanted in range(inst["n"], 1, -1):
        position = permutation.index(wanted)
        if position == wanted - 1:
            continue
        if position:
            permutation[: position + 1] = reversed(permutation[: position + 1])
            path.append(position + 1)
        permutation[:wanted] = reversed(permutation[:wanted])
        path.append(wanted)
    return path


def _attack_smallest_efficient(inst):
    """Always take the smaller of the at-most-two efficient prefix cuts."""
    permutation = _normalise_for_attack(inst)
    path = []
    for _ in range(inst["breakpoints"]):
        choices = _efficient_lengths(permutation, path[-1] if path else 0)
        if not choices:
            return None
        length = min(choices)
        permutation[:length] = reversed(permutation[:length])
        path.append(length)
    return path


def _attack_random_restarts(inst, seed, restarts=256):
    """Randomized walks choosing only breakpoint-decreasing flips."""
    rng = random.Random(seed)
    for _ in range(restarts):
        path = _efficient_random_walk(inst, rng)
        ok, _ = verify(inst, path)
        if ok:
            return path
    return None


def _attack_beam(inst, seed, width=128):
    """Keep a diverse beam of the most constrained efficient partial paths."""
    rng = random.Random(seed)
    start = tuple(_normalise_for_attack(inst))
    level = {(start, 0): ()}
    for _depth in range(inst["breakpoints"]):
        children = {}
        for (state, previous), path in level.items():
            for length in _efficient_lengths(state, previous):
                child = tuple(reversed(state[:length])) + state[length:]
                children.setdefault((child, length), path + (length,))
        if not children:
            return None
        if len(children) > width:
            scored = []
            for key, path in children.items():
                child, previous = key
                score = (len(_efficient_lengths(child, previous)), rng.random())
                scored.append((score, key, path))
            scored.sort(key=lambda item: item[0])
            level = {key: path for _, key, path in scored[:width]}
        else:
            level = children
    goal = tuple(range(1, inst["n"] + 1))
    for (state, _), path in level.items():
        if state == goal:
            return list(path)
    return None


def _ida_breakpoint(inst, node_cap=250_000):
    """Exhaustive efficient-path DFS with exact transposition pruning."""
    start = tuple(_normalise_for_attack(inst))
    goal = tuple(range(1, inst["n"] + 1))
    nodes = 0
    exhausted = False
    seen = set()

    def visit(state, previous):
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > node_cap:
            exhausted = True
            return None
        if state == goal:
            return []
        key = (state, previous)
        if key in seen:
            return None
        seen.add(key)
        for length in sorted(_efficient_lengths(state, previous)):
            child = tuple(reversed(state[:length])) + state[length:]
            suffix = visit(child, length)
            if suffix is not None:
                return [length] + suffix
            if exhausted:
                return None
        return None

    path = visit(start, 0)
    return {
        "path": path,
        "nodes": min(nodes, node_cap),
        "exhausted": exhausted,
        "found_depth": len(path) if path is not None else None,
    }


def _answer_token_count(answer):
    """Exact lexical token count for JSON atoms and punctuation."""
    return len(re.findall(r"-?\d+|[\[\],{}:]", json.dumps(answer)))


def selftest():
    """Run all mandatory correctness, density, attack, scaling, and key gates."""
    report = {}

    # G1: every named preset, several unrelated seeds.
    planted_attempts = 0
    planted_successes = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 9173):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            ok, _ = verify(inst, inst["answer"])
            planted_successes += int(ok)
            json_roundtrips += int(
                json.loads(json.dumps(inst["answer"])) == inst["answer"]
            )
    report["G1_planted_verifies"] = {
        "pass": planted_successes == planted_attempts == json_roundtrips,
        "successes": planted_successes,
        "attempts": planted_attempts,
        "json_native_roundtrips": json_roundtrips,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=424242, **shipping)
    answer = inst["answer"]

    # G2: five specified corruption modes with five distinct diagnostics.
    corruptions = {}
    odd_index = next(
        (i for i, length in enumerate(answer) if _flip_parity(length)), 0
    )
    corruptions["drop_one"] = answer[:odd_index] + answer[odd_index + 1 :]

    swapped = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            trial = list(answer)
            trial[i], trial[j] = trial[j], trial[i]
            ok, why = verify(inst, trial)
            if not ok and why not in {
                "wrong total reversal parity",
                "consecutive prefix lengths must differ",
            }:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = list(reversed(answer))
    corruptions["swap_two"] = swapped

    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    corruptions["duplicate_one"] = duplicated
    corruptions["empty"] = []
    outside = list(answer)
    outside[0] = inst["n"] + 1
    corruptions["out_of_range"] = outside

    reasons = {}
    rejected = 0
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected += int(not ok)
        reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": rejected == 5 and len(set(reasons.values())) == 5,
        "rejected": rejected,
        "attempts": 5,
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # G3: realistic prose, tags, whitespace, and a Markdown fence.
    response = (
        "I tracked the stack exactly.  My final certificate is:\n"
        "<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\nThe flips are listed in execution order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_elements": len(parsed) if parsed is not None else 0,
    }

    # G4/G5 density: 99% of the solver prior follows only efficient moves, the
    # strongest free consequence of asking for exactly db(stack) flips.
    guess_rng = random.Random(0x11110434)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(verify(inst, candidate)[0])
    density_wall = time.perf_counter() - density_start
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_probability,
        "structure_aware_space": search_space(inst),
        "sampler_constraints": [
            "word length = db(stack) = max_flips",
            "2 <= every prefix length <= n",
            "no adjacent equal lengths",
            "correct total reversal parity",
            "99% branch follows only breakpoint-decreasing moves until deadlock",
        ],
        "sampler_prior": "99% efficient random walk; 1% full-support static word",
        "wall_clock_sec": round(density_wall, 6),
    }

    # G6 and the G5 baseline share the same eight shipping instances.
    attack_seeds = list(range(6100, 6108))
    attack_counts = {
        "boundary_gap_outlier": 0,
        "greedy_smallest_efficient": 0,
        "random_efficient_restart_256": 0,
        "constrained_beam_width_128": 0,
        "exhaustive_efficient_dfs_250k": 0,
    }
    ida_nodes = []
    ida_depths = []
    panel_start = time.perf_counter()
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **shipping)
        for name, candidate in (
            ("boundary_gap_outlier", _attack_boundary_gap(attacked)),
            ("greedy_smallest_efficient", _attack_smallest_efficient(attacked)),
            (
                "random_efficient_restart_256",
                _attack_random_restarts(attacked, seed + 77),
            ),
            (
                "constrained_beam_width_128",
                _attack_beam(attacked, seed + 177, width=128),
            ),
        ):
            if candidate is not None:
                attack_counts[name] += int(verify(attacked, candidate)[0])
        ida = _ida_breakpoint(attacked, node_cap=250_000)
        ida_nodes.append(ida["nodes"])
        ida_depths.append(ida["found_depth"])
        if ida["path"] is not None:
            attack_counts["exhaustive_efficient_dfs_250k"] += int(
                verify(attacked, ida["path"])[0]
            )
    panel_wall = time.perf_counter() - panel_start
    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_counts.items()
    }
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4,
        "attacks": attacks,
        "ida_nodes_each": ida_nodes,
        "ida_found_depths": ida_depths,
        "panel_wall_clock_sec": round(panel_wall, 6),
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_solutions = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_probability < 1e-6
            and demo_solutions is not None
            and all_failed
            and sum(ida_nodes) > 0
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_solution_fraction": guess_probability,
        "shipping_density_wall_sec": round(density_wall, 6),
        "demo_exact_solution_count": demo_solutions,
        "demo_certificate_space": search_space(demo),
        "baseline_wall_clock_sec": round(panel_wall, 6),
        "baseline_nodes_total": sum(ida_nodes),
        "baseline_nodes_per_instance": 250_000,
        "baseline_attempts": len(attack_seeds),
        "baseline_successes": attack_counts["exhaustive_efficient_dfs_250k"],
    }

    # G7: double the size/depth parameter outside the shipping cap.  G9 applies
    # only to the shipping preset; this check establishes generator scaling.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=8080, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["size_parameter"] == 2 * inst["size_parameter"]
        and len(doubled["answer"]) == 2 * len(inst["answer"]),
        "shipping_size_parameter": inst["size_parameter"],
        "doubled_size_parameter": doubled["size_parameter"],
        "shipping_pancakes": inst["n"],
        "doubled_pancakes": doubled["n"],
        "shipping_answer_elements": len(inst["answer"]),
        "doubled_answer_elements": len(doubled["answer"]),
        "shipping_space_bits": search_space(inst).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "verify_reason": doubled_why,
    }

    # G8: arbitrary increasing size relabelings, affine relabelings, and their
    # composition preserve the rank stack and the carried flip word.
    invariance_checks = 0
    carried_checks = 0
    distinct_keys = []
    for seed in range(20):
        base = make_instance(seed=9000 + seed, **shipping)
        base_key = canonical_key(base)
        distinct_keys.append(base_key)
        old_sizes = sorted(base["stack"])
        relabel_rng = random.Random(12000 + seed)
        relabeled_values = []
        value = -50_000
        for _ in old_sizes:
            value += relabel_rng.randrange(1, 100)
            relabeled_values.append(value)
        mapping = dict(zip(old_sizes, relabeled_values))

        arbitrary = dict(base)
        arbitrary["stack"] = [mapping[x] for x in base["stack"]]
        affine = dict(base)
        affine["stack"] = [7 * x + 23 for x in base["stack"]]
        composed = dict(arbitrary)
        composed["stack"] = [5 * x - 11 for x in arbitrary["stack"]]
        for transformed in (arbitrary, affine, composed):
            invariance_checks += int(canonical_key(transformed) == base_key)
            carried_checks += int(verify(transformed, base["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and carried_checks == 60
        and len(set(distinct_keys)) == 20,
        "invariance_successes": invariance_checks,
        "invariance_attempts": 60,
        "carried_witness_successes": carried_checks,
        "carried_witness_attempts": 60,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "normal_form": "rank permutation plus bound and breakpoint count",
    }

    # G9(a,b) are recorded diagnostics; G9(c) is the actual gate.
    measured_answers = [
        make_instance(seed=13000 + seed, **shipping)["answer"]
        for seed in range(20)
    ]
    answer_chars = max(len(json.dumps(value)) for value in measured_answers)
    answer_tokens = max(_answer_token_count(value) for value in measured_answers)
    answer_elements = max(len(value) for value in measured_answers)
    intended_operations = answer_elements
    arms = {
        key: dict(G9_ORACLE_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
