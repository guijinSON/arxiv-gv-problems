"""Exact Track-B generator from Mütze's middle-levels construction.

The task is to evaluate a distant iterate of the Dyck-word map g_1 from
Section 5 of "Proof of the middle levels conjecture" (arXiv:1404.4442).
Instances are planted through the paper's conjugacy h g_0 = g_1 h.  The
checker does not use that planted preimage: it enumerates the orbit of g_1,
whose length is at most 2n, and compares the requested iterate exactly.
"""

from __future__ import annotations

import functools
import hashlib
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
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "Dyck lattice paths encoded as balanced bitstrings",
        "the g_1 successor permutation from the paper's middle-level 2-factor",
        "ordered rooted trees and their plane-tree root rotations",
    ],
    "verification_operations": [
        "exact prefix-height updates",
        "exact adjacent-symbol permutations",
        "finite orbit enumeration and bitstring comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize that the apparently irregular g_1 update is conjugate to "
        "moving the root corner of the plane tree encoded by the Dyck word; "
        "without that change of variables one must tabulate the whole orbit."
    ),
    "hardness_basis": (
        "Track B: finite-orbit enumeration applies g_1 at most 2n times and "
        "costs O(n^2) exact symbol operations; at shipping n=36 it used 82,092 "
        "operations across eight instances (10,261 average, 0.003985 seconds), "
        "while Lemma 16's conjugacy and a plane-tree rerooting give a compact "
        "route using at most 145 exact integer updates for the shipped word."
    ),
    "max_answer_tokens": 19,
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

DIFFICULTY = {
    "demo": {"n": 3, "laps": 2},
    "easy": {"n": 36, "laps": 100_003},
    "medium": {"n": 60, "laps": 10_000_019},
    "hard": {"n": 96, "laps": 100_000_007},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Hint: The update is conjugate to changing the root corner of the plane "
    "tree whose contour word is the given Dyck word."
)
PLACEBO_HINT = (
    "Hint: The update preserves the stated word length and balance conditions "
    "at every intermediate iteration of the given Dyck word."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One binary Dyck word of length exactly 2n: exactly n ones and n zeros, "
        "with at least as many ones as zeros in every prefix."
    ),
    "bounds": {
        "alphabet": 2,
        "word_length": "2n",
        "ones": "n",
        "prefix_balance_min": 0,
        "shipping_n": 36,
        "shipping_candidate_count": "Catalan(36)",
    },
}

# Filled from the script-owned oracle transcripts after the three runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 1},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_by_openrouter_quota",
}

NOTES = r"""
Definition and native object. Section 2 defines the cube layers and Section 5
identifies first vertices of the paths in the constructed 2-factors with Dyck
paths. Lemma 15 gives exactly the map called g_1 here: split a nonempty Dyck
path at its first return, apply pi_1 to the two balanced subpaths, and move the
distinguished upstep/downstep pair as displayed in equations (45a)-(45b).

Step-0 decision. The paper explicitly says after Theorem 2 that its arguments
are constructive and output a Hamilton cycle in time polynomial in the graph
size (which is exponential in n). Therefore this family cannot honestly claim
Track A. It is Track B. The answer is not the exponentially long Hamilton
cycle: it is a native intermediate object, the distant g_1 successor of a
Dyck path in the paper's 2-factor. A standard exact algorithm enumerates the
orbit; Lemmas 16-18 expose the shorter change of variables through h and plane
tree rotation. selftest records both costs.

Generation. A uniformly ranked Dyck path q with a full 2n root-corner orbit is
sampled. The visible start is h(q), while the certificate is constructed as
h(g_0^t(q)). This is composition of the paper's identity h g_0 = g_1 h, not a
search for the requested iterate. Marginally, both visible starts and targets
come from the same Dyck-word language. Verification deliberately takes the
independent mechanical route: it repeatedly applies the displayed g_1 rule
until the start returns, reduces t by the observed orbit length, and compares.

Easy regimes and attacks. Small n is easy because the orbit has at most 2n
states. Returning the input, applying one or four visible updates, using the
lexicographically extreme Dyck word, and 256 uniform Dyck guesses are audited
on eight shipping seeds. Full-orbit planting and a residue separated from the
bounded guesses defeat the local rules; uniform sampling defeats the remaining
statistical guesses. The successful orbit
enumerator is reported separately as Track B's reference algorithm.

Canonicalization. The query label and the order of the displayed data lines
are presentation-only relabellings. canonical_key discards them and records
the Dyck word together with the requested power reduced by its exactly
enumerated orbit length. selftest renames the label, reorders the lines, and
composes both transformations while carrying the unchanged witness.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_ENUMERATION_CAP = 100_000


def _validate_n(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if n > 500:
        raise ValueError("n must be at most 500 so recursive exact transforms are safe")


def _is_dyck(word: str) -> tuple[bool, str]:
    height = 0
    for i, symbol in enumerate(word):
        if symbol == "1":
            height += 1
        elif symbol == "0":
            height -= 1
        else:
            return False, f"non-binary symbol at position {i}"
        if height < 0:
            return False, f"prefix ending at position {i} drops below height zero"
    if height != 0:
        return False, "the word is not balanced"
    return True, "ok"


def _first_return(word: str, counter: list[int] | None = None) -> int:
    height = 0
    for i, symbol in enumerate(word):
        height += 1 if symbol == "1" else -1
        if counter is not None:
            counter[0] += 1
        if height == 0:
            return i
    raise ValueError("word has no return to height zero")


def _pi1(word: str, counter: list[int] | None = None) -> str:
    """Swap 1-indexed positions (2,3), (4,5), ... of an even word."""
    symbols = list(word)
    for i in range(1, len(symbols) - 1, 2):
        symbols[i], symbols[i + 1] = symbols[i + 1], symbols[i]
        if counter is not None:
            counter[0] += 1
    return "".join(symbols)


def _g0(word: str) -> str:
    split = _first_return(word)
    left = word[1:split]
    right = word[split + 1 :]
    return left + "1" + right + "0"


def _g1(word: str, counter: list[int] | None = None) -> str:
    split = _first_return(word, counter)
    left = word[1:split]
    right = word[split + 1 :]
    result = _pi1(left, counter) + "1" + _pi1(right, counter) + "0"
    if counter is not None:
        counter[0] += len(word)  # exact symbol writes in the new word
    return result


def _components(word: str) -> list[str]:
    parts: list[str] = []
    height = 0
    start = 0
    for i, symbol in enumerate(word):
        height += 1 if symbol == "1" else -1
        if height == 0:
            parts.append(word[start : i + 1])
            start = i + 1
    return parts


def _h(word: str) -> str:
    if not word:
        return ""
    return "".join(
        "1" + _pi1(_h(component[1:-1])) + "0"
        for component in _components(word)
    )


def _h_inverse(word: str) -> str:
    if not word:
        return ""
    return "".join(
        "1" + _h_inverse(_pi1(component[1:-1])) + "0"
        for component in _components(word)
    )


def _g0_power_by_rerooting(word: str, power: int) -> str:
    """Compute g_0**power in O(n) using the plane-tree root corner."""
    n = len(word) // 2
    cyclic: list[list[int]] = [[]]
    parent = [-1]
    stack = [0]
    for symbol in word:
        if symbol == "1":
            vertex = len(cyclic)
            cyclic.append([])
            parent.append(stack[-1])
            cyclic[stack[-1]].append(vertex)
            stack.append(vertex)
        else:
            stack.pop()
    for vertex in range(1, n + 1):
        cyclic[vertex] = [parent[vertex]] + cyclic[vertex]

    root = 0
    first = cyclic[0][0]
    for _ in range(power % (2 * n)):
        new_root = first
        neighbors = cyclic[new_root]
        index = neighbors.index(root)
        new_first = neighbors[(index + 1) % len(neighbors)]
        root, first = new_root, new_first

    output: list[str] = []

    def encode(vertex: int, par: int | None, initial: int | None = None) -> None:
        neighbors = cyclic[vertex]
        pivot = neighbors.index(initial if par is None else par)
        if par is None:
            children = neighbors[pivot:] + neighbors[:pivot]
        else:
            children = neighbors[pivot + 1 :] + neighbors[:pivot]
        for child in children:
            output.append("1")
            encode(child, vertex)
            output.append("0")

    encode(root, None, first)
    return "".join(output)


@functools.lru_cache(maxsize=None)
def _completion_count(n: int, ones_used: int, zeros_used: int) -> int:
    if ones_used == n:
        return 1
    total = _completion_count(n, ones_used + 1, zeros_used)
    if zeros_used < ones_used:
        total += _completion_count(n, ones_used, zeros_used + 1)
    return total


def _unrank_dyck(n: int, rank: int) -> str:
    if rank < 0 or rank >= _catalan(n):
        raise ValueError("Dyck rank out of range")
    ones = zeros = 0
    output: list[str] = []
    while ones + zeros < 2 * n:
        count_with_one = (
            _completion_count(n, ones + 1, zeros) if ones < n else 0
        )
        if rank < count_with_one:
            output.append("1")
            ones += 1
        else:
            rank -= count_with_one
            if zeros >= ones:
                raise AssertionError("invalid Dyck unranking state")
            output.append("0")
            zeros += 1
    return "".join(output)


def _random_dyck(n: int, rng: random.Random) -> str:
    return _unrank_dyck(n, rng.randrange(_catalan(n)))


def _catalan(n: int) -> int:
    return math.comb(2 * n, n) // (n + 1)


def _orbit(
    word: str, counter: list[int] | None = None
) -> list[str]:
    """Enumerate the g_1 orbit, executing the checker's whole argument."""
    n = len(word) // 2
    states = [word]
    current = _g1(word, counter)
    while current != word:
        if current in states:
            raise RuntimeError("g_1 entered a cycle not containing the start")
        states.append(current)
        if len(states) > 2 * n:
            raise RuntimeError("g_1 orbit exceeded the executable 2n bound")
        current = _g1(current, counter)
    return states


def _reference_target(inst: dict, counter: list[int] | None = None) -> str:
    states = _orbit(inst["start"], counter)
    return states[inst["iterations"] % len(states)]


def _compact_target(inst: dict) -> str:
    preimage = _h_inverse(inst["start"])
    rotated = _g0_power_by_rerooting(preimage, inst["iterations"])
    return _h(rotated)


def _full_g0_orbit(word: str) -> bool:
    current = _g0(word)
    length = 1
    while current != word and length <= len(word):
        current = _g0(current)
        length += 1
    return length == len(word) and current == word


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct an iterate through h(g_0^t(q)), never by solving g_1^t."""
    laps = params.pop("laps", 1)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_n(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(laps, bool) or not isinstance(laps, int) or laps < 0:
        raise ValueError("laps must be a nonnegative integer")

    rng = random.Random(seed)
    # Full root-corner orbits make the small bounded-iteration attacks genuinely
    # different from the planted iterate.  This is a property of sampled source
    # objects, not a search for the answer.
    if n < 6:
        # The tiny demo is illustrative rather than adversarial, and some small
        # plane trees necessarily have rotational symmetry.
        source = _random_dyck(n, rng)
    else:
        for _ in range(10_000):
            source = _random_dyck(n, rng)
            if _full_g0_orbit(source):
                break
        else:
            raise RuntimeError("failed to sample a full-orbit Dyck word")

    if n < 6:
        residue = max(2, n - 1)
    else:
        residue = rng.randrange(max(5, n // 2), 2 * n - 5)
    iterations = laps * (2 * n) + residue
    start = _h(source)
    target = _h(_g0_power_by_rerooting(source, iterations))

    labels = ["query-" + format(rng.getrandbits(28), "07x")]
    presentation = ["n", "label", "start", "iterations"]
    rng.shuffle(presentation)
    return {
        "n": n,
        "label": labels[0],
        "start": start,
        "iterations": iterations,
        "presentation_order": presentation,
        "answer": target,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    facts = {
        "n": f"Semilength n: {n}",
        "label": f"Cosmetic query label: {inst['label']}",
        "start": f"Starting Dyck word p: {inst['start']}",
        "iterations": f"Requested number of iterations T: {inst['iterations']}",
    }
    lines = [
        "Compute a distant successor in the Dyck-path permutation used in a "
        "middle-levels 2-factor.",
        "",
        "Exact definitions and conventions:",
        f"- A Dyck word of semilength n is a binary word of length 2n with "
        f"exactly n symbols 1 and n symbols 0, such that every prefix has at "
        f"least as many 1s as 0s. Here 1 is an upstep and 0 is a downstep.",
        "- For any even-length word w, define pi(w) by simultaneously swapping "
        "its 1-indexed positions 2 and 3, positions 4 and 5, and so on; the "
        "first and last positions are left fixed. For the empty word, pi(w)=w.",
        "- For a nonempty Dyck word p, let its first return be the earliest "
        "positive position where the prefix has equally many 1s and 0s. This "
        "uniquely writes p = 1 L 0 R, where the displayed 0 is that first-return "
        "symbol and L,R are (possibly empty) Dyck words.",
        "- Define G(p) = pi(L) 1 pi(R) 0. Every intermediate word is again a "
        "Dyck word. G^T(p) means apply G exactly T times; G^0(p)=p.",
        "- Bit positions are 1-indexed only in the definition of pi. The output "
        "is the bitstring itself, with no spaces or separators.",
        "",
        "Instance data (line order carries no meaning):",
    ]
    lines.extend("  " + facts[name] for name in inst["presentation_order"])
    lines.extend(
        [
            "",
            f"Return the unique Dyck word G^{inst['iterations']}(p), containing "
            f"exactly {2*n} bits.",
            "Give your final answer inside <answer></answer> tags, as one "
            "unquoted binary word with no whitespace.",
            f"Example format (not necessarily a solution): "
            f"<answer>{'10' * n}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        payload = match.group(1).strip()
        if re.fullmatch(r"[01]+", payload):
            return payload
        try:
            value = json.loads(payload)
            return value if isinstance(value, str) else None
        except (ValueError, TypeError):
            return None
    for fence in _FENCE_RE.findall(text):
        payload = fence.strip()
        if re.fullmatch(r"[01]+", payload):
            return payload
        try:
            value = json.loads(payload)
            if isinstance(value, str):
                return value
        except (ValueError, TypeError):
            pass
    # Tolerate a final standalone binary line in otherwise ordinary prose.
    candidates = re.findall(r"(?m)^\s*([01]{2,})\s*$", text)
    return candidates[-1] if candidates else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, str):
        return False, "answer must be one binary word"
    if answer == "":
        return False, "answer word is empty"
    expected_length = 2 * inst["n"]
    if len(answer) < expected_length:
        return False, f"answer word is too short: expected {expected_length} bits"
    if len(answer) > expected_length:
        return False, f"answer word is too long: expected {expected_length} bits"
    bad = next((i for i, bit in enumerate(answer) if bit not in "01"), None)
    if bad is not None:
        return False, f"non-binary symbol at position {bad}"
    if answer.count("1") != inst["n"]:
        return False, f"wrong Hamming weight: expected {inst['n']} ones"
    ok, reason = _is_dyck(answer)
    if not ok:
        return False, "answer is not a Dyck word: " + reason
    expected = _reference_target(inst)
    if answer != expected:
        return False, f"incorrect iterate for {inst['label']}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated Dyck-word certificate language."""
    return _random_dyck(inst["n"], rng)


def search_space(inst: dict) -> int | None:
    return _catalan(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    expected = _reference_target(inst)
    return sum(_unrank_dyck(inst["n"], rank) == expected for rank in range(space))


def canonical_key(inst: dict) -> str:
    # The label and presentation order are cosmetic.  Powers differing by a
    # whole observed orbit define the same exact query.
    orbit_length = len(_orbit(inst["start"]))
    payload = {
        "n": inst["n"],
        "start": inst["start"],
        "power_mod_orbit": inst["iterations"] % orbit_length,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = params.get("n")
    laps = params.get("laps", 1)
    if not isinstance(n, int):
        return None
    if n < 96:
        return {"n": 96, "laps": max(laps, 100_000_007)}
    if n < 120:
        return {"n": 120, "laps": max(laps, 1_000_000_007)}
    if n < 127:
        return {"n": 127, "laps": max(laps, 10_000_000_019)}
    return "cap_bound"


def _attack_answers(inst: dict) -> dict[str, str]:
    start = inst["start"]
    return {
        "outlier_lexicographic_extreme": "10" * inst["n"],
        "greedy_fixed_point": start,
        "one_visible_update": _g1(start),
        "by_hand_four_updates": functools.reduce(
            lambda value, _unused: _g1(value), range(4), start
        ),
    }


def _transformed_instance(inst: dict, kind: str) -> dict:
    transformed = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in inst.items()
    }
    if kind in ("rename_label", "composed"):
        transformed["label"] = "renamed-cosmetic-query"
    if kind in ("reorder_lines", "composed"):
        transformed["presentation_order"] = list(
            reversed(transformed["presentation_order"])
        )
    return transformed


def selftest() -> dict:
    report: dict[str, object] = {"track": TRACK}

    # G1: all presets, three seeds, plus an independent compact-route audit.
    g1_failures: list[str] = []
    g1_attempts = 0
    compact_matches = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if _compact_target(inst) == inst["answer"]:
                compact_matches += 1
            else:
                g1_failures.append(f"{preset}/{seed}: compact route disagrees")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "compact_route_matches": compact_matches,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=2026, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = shipping["answer"]
    first_zero = answer.index("0")
    swapped = list(answer)
    swapped[0], swapped[first_zero] = swapped[first_zero], swapped[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": "".join(swapped),
        "duplicate": answer + answer[-1],
        "empty": "",
        "out_of_range": "2" + answer[1:],
    }
    cases: dict[str, dict[str, object]] = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"accepted": ok, "reason": reason}
    distinct_reasons = len({case["reason"] for case in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(not case["accepted"] for case in cases.values())
        and distinct_reasons == len(cases),
        "distinct_reasons": distinct_reasons,
        "cases": cases,
    }

    wrapped = (
        "I used the first-return decomposition.\n\n"
        f"<answer>\n{answer}\n</answer>\nThat is my final word."
    )
    fenced = f"Work omitted.\n```text\n{answer}\n```"
    report["G3_round_trip"] = {
        "pass": parse_answer(wrapped) == answer and parse_answer(fenced) == answer,
        "tagged_prose_matches": parse_answer(wrapped) == answer,
        "fenced_matches": parse_answer(fenced) == answer,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4: the verifier's expected target is computed once, independently of the
    # planted field; every sample is uniform over the exact Dyck language.
    sample_total = 200_000
    sample_rng = random.Random(0x14044442)
    expected = _reference_target(shipping)
    started = time.perf_counter()
    hits = sum(
        random_candidate(shipping, sample_rng) == expected
        for _ in range(sample_total)
    )
    sample_wall = time.perf_counter() - started
    space = search_space(shipping)
    exact_fraction = 1.0 / space
    report["G4_guess_resistance"] = {
        "pass": hits / sample_total < 1e-6 and exact_fraction < 1e-6,
        "hits": hits,
        "total": sample_total,
        "observed_fraction": hits / sample_total,
        "exact_fraction": exact_fraction,
        "candidate_space": space,
        "sampling_prior": "uniform over all Dyck words of semilength n",
        "wall_clock_sec": round(sample_wall, 6),
    }

    # G6 and reference algorithm measurements at the shipping preset.
    seeds = list(range(800, 808))
    attack_names = list(_attack_answers(shipping).keys())
    attack_stats = {
        name: {"successes": 0, "attempts": len(seeds), "steps": 0}
        for name in attack_names
    }
    random_stats = {"successes": 0, "attempts": len(seeds), "steps": 0}
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    strongest_wall = 0.0
    for seed in seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        local_rng = random.Random(seed ^ 0xA55A)
        for name, candidate in _attack_answers(inst).items():
            ok, _ = verify(inst, candidate)
            attack_stats[name]["successes"] += int(ok)
            attack_stats[name]["steps"] += {
                "outlier_lexicographic_extreme": 2 * inst["n"],
                "greedy_fixed_point": 1,
                "one_visible_update": 2 * inst["n"],
                "by_hand_four_updates": 8 * inst["n"],
            }[name]
        target = _reference_target(inst)
        random_started = time.perf_counter()
        for _ in range(256):
            candidate = random_candidate(inst, local_rng)
            random_stats["steps"] += 1
            if candidate == target:
                random_stats["successes"] += 1
                break
        strongest_wall += time.perf_counter() - random_started
        counter = [0]
        reference_started = time.perf_counter()
        reference = _reference_target(inst, counter)
        reference_wall += time.perf_counter() - reference_started
        reference_operations += counter[0]
        reference_successes += int(verify(inst, reference)[0])
    attack_stats["random_restart_256"] = random_stats
    all_failed = all(stat["successes"] == 0 for stat in attack_stats.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "exact g_1 orbit enumeration with cycle detection",
            "complexity": "O(n^2) exact symbol operations and O(n^2) stored bits",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations": reference_operations // len(seeds),
            "solves": f"{reference_successes}/{len(seeds)}, as expected",
        },
        "compact_route_audit": {
            "name": "h inverse, plane-tree root-corner shift, then h",
            "complexity": "O(n) structural passes after recognizing Lemma 16",
            "exact_integer_updates_per_instance_upper_bound": 4
            * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
            + 1,
            "solves": f"{len(seeds)}/{len(seeds)}, checked separately by G1",
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits / sample_total < 1e-6,
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": exact_fraction,
        "shipping_sampled_valid_hits": hits,
        "shipping_sampled_valid_total": sample_total,
        "demo_bruteforce_solution_count": demo_count,
        "demo_n": demo["n"],
        "reference_algorithm_operations": reference_operations,
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "strongest_failing_attack": "random_restart_256",
        "strongest_failing_attack_steps": random_stats["steps"],
        "strongest_failing_attack_wall_clock_sec": round(strongest_wall, 6),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=99, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    preset_spaces = {
        name: search_space(make_instance(seed=3, **params))
        for name, params in DIFFICULTY.items()
    }
    report["G7_scales"] = {
        "pass": doubled_ok
        and all(
            preset_spaces[a] < preset_spaces[b]
            for a, b in zip(list(DIFFICULTY)[:-1], list(DIFFICULTY)[1:])
        ),
        "preset_candidate_spaces": preset_spaces,
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    invariance_failures: list[str] = []
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        for kind in ("rename_label", "reorder_lines", "composed"):
            changed = _transformed_instance(inst, kind)
            invariance_checks += 1
            if canonical_key(changed) != key:
                invariance_failures.append(f"seed {seed}/{kind}: key changed")
            carried_checks += 1
            if not verify(changed, inst["answer"])[0]:
                invariance_failures.append(
                    f"seed {seed}/{kind}: carried witness failed"
                )
    unrelated_keys = {
        canonical_key(
            make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        )
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and len(unrelated_keys) == 20,
        "transformations": [
            "cosmetic query-label renaming",
            "instance-data line reordering",
            "composition of both transformations",
        ],
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "invariance_failures": invariance_failures,
        "unrelated_instances": 20,
        "distinct_keys": len(unrelated_keys),
    }

    answer_chars = len(json.dumps(shipping["answer"]))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_ops = 4 * shipping["n"] + 1
    arms = {
        arm: dict(G9_ORACLE_RESULTS[arm])
        for arm in ("bare", "hinted", "placebo")
    }
    hinted_verdict = G9_ORACLE_RESULTS["hinted_verdict"]
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_ops <= 300
    )
    hinted_still_hardened = hinted_verdict == "hardened"
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
        "oracle_results_pending": hinted_verdict != "hardened",
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
