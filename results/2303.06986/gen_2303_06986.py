"""Verified problem generator for arXiv:2303.06986.

The paper reduces 3-SAT to Multiset Dimension. This module inverse-generates
full-rank cyclic parity systems, expands each parity row into the paper's four
clause gadgets, and carries the sampled assignment to Claim 3.3's resolving set.
Generation never solves an emitted instance.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import deque


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "connected simple graph specified by the paper's variable and clause gadgets",
        "multiset distance representations",
        "canonical multiset resolving set encoded by Boolean gadget choices",
    ],
    "verification_operations": [
        "exact hexadecimal decoding",
        "exact parity evaluation",
        "exact validation of the paper's distinct pendant-path schedule",
        "symbolic check of the c^1/c^3 multiset-distance collision condition",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": "Section 3, Theorem 3.1 and Claims 3.2-3.4 (3-SAT to Multiset Dimension)",
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "XORing adjacent affine-window equations cancels four variables and leaves "
        "one cyclic step-three recurrence; without that change of variables, the "
        "displayed system calls for generic SAT search or elimination."
    ),
    "hardness_basis": (
        "Track B: exact O(n^3) GF(2) Gauss-Jordan elimination averaged 24,025 "
        "scalar operations and about 0.0026 seconds at provisional shipping n=53, "
        "whereas adjacent affine-window cancellation needs at most 273 exact operations."
    ),
    "max_answer_tokens": 4,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is not divisible by 3, so the cyclic window matrix is nonsingular over GF(2).
DIFFICULTY = {
    "demo": {"n": 5, "copies": 1},
    "easy": {"n": 29, "copies": 1},
    "medium": {"n": 41, "copies": 2},
    "hard": {"n": 53, "copies": 4},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Adjacent affine-window parity equations share a four-variable overlap "
    "whose cancellation leaves a cyclic step-three relation."
)
PLACEBO_HINT = (
    "The hexadecimal bit order and the zero-based gadget indices require "
    "consistent bookkeeping throughout the construction."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One lowercase fixed-width hexadecimal word with ceil(n/4) digits and "
        "value below 2^n. Bit r selects a_r^1 instead of b_r^1; every e_r^1 and "
        "every clause-gadget g^1 vertex is included automatically."
    ),
    "bounds": {
        "hex_digits": "ceil(n/4)",
        "integer_min": 0,
        "integer_max": "2^n-1",
        "semantic_boolean_atoms": "n",
        "candidate_count": "2^n",
    },
}

NOTES = (
    "Section 2 and Theorem 2.1 fix the exact witness: unordered multisets of "
    "graph distances must distinguish every vertex. Section 3, Theorem 3.1 and "
    "Claims 3.2-3.4 give the paper-central reduction. Claim 3.3 turns any satisfying "
    "assignment into the canonical resolving set containing every e^1 and g^1 "
    "plus one a^1/b^1 truth vertex per variable. The proof's distance formulas "
    "make a false clause exactly the remaining c_j^1/c_j^3 collision. The "
    "explicit king-grid witnesses in Proposition 4.2 and Theorem 4.4 and the "
    "strong-product witness in Theorem 5.1 are easy regimes and were not used. "
    "Complete XOR quartets balance signs, the affine cycle equalizes incidence, "
    "and randomized tail-block assignment plus a non-unit affine step defeat "
    "outlier, majority, greedy, restart and step-one attacks. Gaussian "
    "elimination and DPLL are disclosed as successful Track-B references."
)

# Script-owned oracle results are copied here after the three runs. They are
# diagnostics; since 2026-09-05 G9 gates only size and intended-route effort.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, copies):
    if not _is_int(n) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")
    if not _is_int(copies) or copies < 1:
        raise ValueError("copies must be a positive integer")
    if not any(math.gcd(step, n) == 1 for step in range(2, n - 1)):
        raise ValueError("n has no supported non-unit affine step")


def _hex_width(n):
    return (n + 3) // 4


def _encode_int(inst, packed):
    return format(packed, f"0{_hex_width(inst['n'])}x")


def _encode_bits(n, bits):
    packed = 0
    for index, bit in enumerate(bits):
        packed |= int(bit) << index
    return format(packed, f"0{_hex_width(n)}x")


def _invalid_patterns(rhs):
    return [
        [(pattern >> offset) & 1 for offset in range(3)]
        for pattern in range(8)
        if (((pattern >> 0) & 1) ^ ((pattern >> 1) & 1) ^ ((pattern >> 2) & 1)) != rhs
    ]


def _graph_size(n, copies):
    variable_vertices = sum(5 * (rank + 2) + 8 for rank in range(n))
    clause_count = 4 * n * copies
    sum_tails = 5 * (clause_count * (n + 2) + clause_count * (clause_count - 1) // 2)
    return variable_vertices + sum_tails + 5 * clause_count


def make_instance(n, seed=0, copies=1, **params):
    """Inverse-generate a reduction graph and its canonical resolving witness."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, copies)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    bits = [rng.getrandbits(1) for _ in range(n)]
    if not any(bits):
        bits[rng.randrange(n)] = 1
    if all(bits):
        bits[rng.randrange(n)] = 0

    steps = [step for step in range(2, n - 1) if math.gcd(step, n) == 1]
    step = rng.choice(steps)
    tail_slots = list(range(n))
    rng.shuffle(tail_slots)
    checks = []
    for start in range(n):
        variables = [start, (start + step) % n, (start + 2 * step) % n]
        rhs = bits[variables[0]] ^ bits[variables[1]] ^ bits[variables[2]]
        checks.append({
            "h": tail_slots[start],
            "vars": variables,
            "rhs": rhs,
            "patterns": _invalid_patterns(rhs),
        })
    rng.shuffle(checks)
    variables = [{"rank": rank, "t": 5 * (rank + 2)} for rank in range(n)]
    rng.shuffle(variables)
    clause_count = 4 * n * copies
    inst = {
        "paper": "arXiv:2303.06986",
        "family": "canonical multiset resolving set in the Theorem 3.1 graph",
        "n": n,
        "copies": copies,
        "variables": variables,
        "checks": checks,
        "clause_count": clause_count,
        "required_set_size": 2 * n + clause_count,
        "graph_vertices": _graph_size(n, copies),
    }
    inst["answer"] = _encode_bits(n, bits)
    return inst


def _find_affine_step(n, checks):
    triples = {frozenset(check["vars"]) for check in checks}
    if len(triples) != n:
        return None
    first = next(iter(triples))
    candidates = {
        (v - u) % n
        for u in first for v in first
        if u != v and math.gcd((v - u) % n, n) == 1
    }
    for step in sorted(candidates):
        expected = {
            frozenset((start, (start + step) % n, (start + 2 * step) % n))
            for start in range(n)
        }
        if expected == triples:
            return step
    return None


def _validate_instance(inst):
    cached = inst.get("_validation_cache")
    if isinstance(cached, dict):
        return cached, None
    n, copies = inst.get("n"), inst.get("copies")
    try:
        _validate_parameters(n, copies)
    except (TypeError, ValueError) as exc:
        return None, "instance parameters are invalid: " + str(exc)
    variables, checks = inst.get("variables"), inst.get("checks")
    if not isinstance(variables, list) or len(variables) != n:
        return None, "instance variable-gadget list is inconsistent"
    try:
        ordered = sorted(variables, key=lambda item: item["rank"])
        ranks = [item["rank"] for item in ordered]
        tails = [item["t"] for item in ordered]
    except (KeyError, TypeError):
        return None, "instance contains a malformed variable gadget"
    if ranks != list(range(n)) or tails != [5 * (rank + 2) for rank in range(n)]:
        return None, "instance violates the variable pendant-path schedule"
    if not isinstance(checks, list) or len(checks) != n:
        return None, "instance parity-row list is inconsistent"

    seen_h = set()
    for check in checks:
        try:
            h, row, rhs, patterns = check["h"], check["vars"], check["rhs"], check["patterns"]
        except (KeyError, TypeError):
            return None, "instance contains a malformed parity row"
        if not _is_int(h) or h < 0 or h >= n or h in seen_h:
            return None, "instance repeats or misnumbers a clause-tail block"
        seen_h.add(h)
        if (not isinstance(row, list) or len(row) != 3 or
                any(not _is_int(v) or v < 0 or v >= n for v in row) or len(set(row)) != 3):
            return None, "instance has a malformed three-variable parity row"
        if rhs not in (0, 1):
            return None, "instance has a non-Boolean parity right-hand side"
        if not isinstance(patterns, list) or len(patterns) != 4:
            return None, "instance parity row does not define four clause slots"
        normalized = []
        for pattern in patterns:
            if (not isinstance(pattern, list) or len(pattern) != 3 or
                    any(bit not in (0, 1) for bit in pattern)):
                return None, "instance has a malformed falsifying pattern"
            normalized.append(tuple(pattern))
        if set(normalized) != {tuple(pattern) for pattern in _invalid_patterns(rhs)}:
            return None, "instance clause slots do not exactly encode their parity row"
    step = _find_affine_step(n, checks)
    if step is None:
        return None, "instance parity rows are not one affine cyclic-window system"
    clause_count = 4 * n * copies
    if (inst.get("clause_count") != clause_count or
            inst.get("required_set_size") != 2 * n + clause_count or
            inst.get("graph_vertices") != _graph_size(n, copies)):
        return None, "instance size metadata is inconsistent"
    data = {"checks": checks, "step": step}
    inst["_validation_cache"] = data
    return data, None


def _oriented_rows(inst):
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    n, step = inst["n"], data["step"]
    rows = []
    for check in data["checks"]:
        triple = frozenset(check["vars"])
        start = next(s for s in check["vars"]
                     if frozenset((s, (s + step) % n, (s + 2 * step) % n)) == triple)
        rows.append((start, check))
    return step, sorted(rows)


def _expanded_clause_specs(inst):
    """Return (h, copy, slot, tail, literals) for every implicit clause gadget."""
    specs = []
    for check in inst["checks"]:
        for copy in range(inst["copies"]):
            for slot, pattern in enumerate(check["patterns"]):
                ordinal = 4 * (inst["copies"] * check["h"] + copy) + slot
                tail = 5 * (inst["n"] + ordinal + 2)
                literals = [[check["vars"][pos], 1 - pattern[pos]] for pos in range(3)]
                specs.append((check["h"], copy, slot, tail, literals))
    return specs


def render(inst):
    """Render the full graph definition and the exact answer grammar."""
    _step, rows = _oriented_rows(inst)
    n, copies, width = inst["n"], inst["copies"], _hex_width(inst["n"])
    example = format((1 << min(3, n)) - 1, f"0{width}x")
    lines = [
        "Find a multiset resolving set in the connected graph defined below.",
        "",
        "Definitions (all indices and bounds are exact).",
        "The graph is finite, simple and undirected. The distance d(u,v) is the",
        "number of edges in a shortest u-v path. For a vertex set W, the multiset",
        "representation of u is the unordered multiset {{d(u,w): w in W}}, including",
        "0 when u belongs to W. W is multiset resolving if every two distinct graph",
        "vertices have different multiset representations.",
        "",
        "Variable gadgets (r is zero-based).",
        f"For each r=0,...,{n - 1}, make vertices T_r,F_r,a_r^1,a_r^2,b_r^1,b_r^2,",
        "d_r^1,...,d_r^t,e_r^1,e_r^2, where t=5(r+2). Add edges",
        "  a_r^1--b_r^1, a_r^2--b_r^2,",
        "  T_r--a_r^1, T_r--a_r^2, F_r--b_r^1, F_r--b_r^2,",
        "  T_r--d_r^1, F_r--d_r^1, d_r^i--d_r^(i+1) for 1<=i<t,",
        "  d_r^t--e_r^1 and d_r^t--e_r^2.",
        "",
        "Parity rows and clause gadgets.",
        "Each row has a tail-block h, ordered triple (u,v,w), bit b and four slot",
        "patterns. It denotes x_u XOR x_v XOR x_w=b. For every copy c=0,...,C-1",
        "and slot a with pattern p=(p0,p1,p2), make a clause gadget Q=(h,c,a).",
        "Its literals are +x_u if p0=0 and -x_u if p0=1, and likewise for v,p1",
        "and w,p2. The clause is false exactly at p; the four slots are precisely",
        "the patterns whose parity differs from b.",
        "Q has vertices c_Q^1,c_Q^2,c_Q^3,f_Q^1,...,f_Q^s,g_Q^1,g_Q^2, where",
        "j=4(C*h+c)+a and s=5(n+j+2). Add edges c_Q^1--c_Q^2--c_Q^3,",
        "c_Q^2--f_Q^1, f_Q^i--f_Q^(i+1) for 1<=i<s, and f_Q^s--g_Q^1,g_Q^2.",
        "For every Q connect c_Q^1 to both T_r,F_r for every r. Connect c_Q^3 to",
        "both T_r,F_r when x_r is absent; only F_r when +x_r occurs; and only T_r",
        "when -x_r occurs. There are no other edges.",
        f"Here n={n}, C={copies}, so there are {inst['clause_count']} clause gadgets.",
        "Rows are presented independently of h; triple order fixes slot coordinates.",
    ]
    digits = len(str(n - 1))
    for _start, check in rows:
        patterns = ",".join("".join(str(bit) for bit in pattern) for pattern in check["patterns"])
        u, v, w = check["vars"]
        lines.append(f"  h={check['h']:0{digits}d}: ({u},{v},{w}) b={check['rhs']} slots={patterns}")
    lines.extend([
        "",
        "Required witness.",
        f"Return one hexadecimal word z of exactly {width} digits and value below 2^{n}.",
        "Leading zeroes are required. Bit r of z (bit 0 is least-significant) defines",
        "  W(z) = {e_r^1 for every r} union {g_Q^1 for every clause gadget Q}",
        "         union {a_r^1 if bit r is 1, otherwise b_r^1, for every r}.",
        f"Thus W(z) has exactly {inst['required_set_size']} vertices. Find any z for which",
        "W(z) is multiset resolving. Hexadecimal letter case is ignored on input.",
        "",
        "Give your final answer inside <answer></answer> tags as exactly the required",
        f"{width} hexadecimal digits, without a 0x prefix.",
        f"Example format only: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract one tagged hexadecimal word, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if len(matches) != 1:
        return None
    body = matches[0].strip()
    fenced = re.fullmatch(r"```(?:text|json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    return body.lower() if re.fullmatch(r"[0-9a-fA-F]+", body) else None


def _decode_answer(inst, answer):
    if not isinstance(answer, str):
        return None, "answer must be a hexadecimal string"
    if not answer:
        return None, "answer is empty"
    width = _hex_width(inst["n"])
    if len(answer) < width:
        return None, "answer has too few hexadecimal digits"
    if len(answer) > width:
        return None, "answer has too many hexadecimal digits"
    if not re.fullmatch(r"[0-9a-fA-F]+", answer):
        return None, "answer contains a non-hexadecimal character"
    packed = int(answer, 16)
    if packed >= (1 << inst["n"]):
        return None, "answer value is outside the n-bit range"
    return packed, None


def verify(inst, answer):
    """Check any canonical witness; never consult inst['answer']."""
    packed, error = _decode_answer(inst, answer)
    if error is not None:
        return False, error
    data, error = _validate_instance(inst)
    if error is not None:
        return False, error
    for check in data["checks"]:
        u, v, w = check["vars"]
        parity = ((packed >> u) & 1) ^ ((packed >> v) & 1) ^ ((packed >> w) & 1)
        if parity != check["rhs"]:
            return False, f"clause block h={check['h']} leaves c^1 and c^3 with identical multiset-distance representations"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly after enforcing the canonical witness shape and size."""
    return _encode_int(inst, rng.getrandbits(inst["n"]))


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    if inst["n"] > 16:
        return None
    return sum(verify(inst, _encode_int(inst, packed))[0] for packed in range(1 << inst["n"]))


def _compact_shortcut(inst):
    """Solve by cancelling adjacent affine-window rows."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    n, step = inst["n"], data["step"]
    rhs = [None] * n
    for check in data["checks"]:
        triple = frozenset(check["vars"])
        start = next(s for s in check["vars"]
                     if frozenset((s, (s + step) % n, (s + 2 * step) % n)) == triple)
        rhs[start] = check["rhs"]
    bits = [0] * n
    current = 0
    for _ in range(n - 1):
        nxt = (current + 3 * step) % n
        bits[nxt] = bits[current] ^ rhs[current] ^ rhs[(current + step) % n]
        current = nxt
    correction = rhs[0] ^ bits[0] ^ bits[step] ^ bits[(2 * step) % n]
    return [bit ^ correction for bit in bits]


def canonical_key(inst):
    """Canonicalize storage order, endpoint swaps and triple-coordinate order."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    solution = _compact_shortcut(inst)
    rows = []
    for check in sorted(data["checks"], key=lambda row: row["h"]):
        order = sorted(range(3), key=lambda pos: check["vars"][pos])
        variables = [check["vars"][pos] for pos in order]
        slots = [[pattern[pos] ^ solution[check["vars"][pos]] for pos in order]
                 for pattern in check["patterns"]]
        rows.append({"vars": variables, "slots": slots})
    payload = {"n": inst["n"], "copies": inst["copies"], "rows_by_tail": rows}
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return "multiset-dimension-reduction-v2:" + hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    n, copies = params.get("n"), params.get("copies", 1)
    if not _is_int(n) or not _is_int(copies):
        return None
    candidate = n + max(2, n // 10)
    while candidate % 3 == 0:
        candidate += 1
    return None if 5 * candidate + 8 > 300 else {"n": candidate, "copies": copies + 1}


def _explicit_collision_count(inst, answer):
    """Materialize demo graph and recompute every distance multiset by BFS."""
    if inst["n"] > 8 or inst["copies"] > 1:
        return None
    packed, error = _decode_answer(inst, answer)
    if error is not None:
        return None
    adjacency = {}

    def edge(left, right):
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    n = inst["n"]
    for rank in range(n):
        tail = 5 * (rank + 2)
        true, false = ("T", rank), ("F", rank)
        a1, a2, b1, b2 = ("a1", rank), ("a2", rank), ("b1", rank), ("b2", rank)
        edge(a1, b1); edge(a2, b2)
        edge(true, a1); edge(true, a2); edge(false, b1); edge(false, b2)
        path = [("d", rank, index) for index in range(1, tail + 1)]
        edge(true, path[0]); edge(false, path[0])
        for left, right in zip(path, path[1:]):
            edge(left, right)
        edge(path[-1], ("e1", rank)); edge(path[-1], ("e2", rank))

    specs = _expanded_clause_specs(inst)
    for h, copy, slot, tail, literals in specs:
        q = (h, copy, slot)
        c1, c2, c3 = ("c1", q), ("c2", q), ("c3", q)
        edge(c1, c2); edge(c2, c3)
        path = [("f", q, index) for index in range(1, tail + 1)]
        edge(c2, path[0])
        for left, right in zip(path, path[1:]):
            edge(left, right)
        edge(path[-1], ("g1", q)); edge(path[-1], ("g2", q))
        signs = {variable: sign for variable, sign in literals}
        for rank in range(n):
            edge(c1, ("T", rank)); edge(c1, ("F", rank))
            if rank not in signs:
                edge(c3, ("T", rank)); edge(c3, ("F", rank))
            elif signs[rank]:
                edge(c3, ("F", rank))
            else:
                edge(c3, ("T", rank))

    witness = [("g1", (h, copy, slot)) for h, copy, slot, _tail, _lits in specs]
    for rank in range(n):
        witness.extend([("e1", rank), ("a1", rank) if (packed >> rank) & 1 else ("b1", rank)])
    signatures = {vertex: [] for vertex in adjacency}
    for source in witness:
        distances = {source: 0}
        queue = deque([source])
        while queue:
            vertex = queue.popleft()
            for neighbor in adjacency[vertex]:
                if neighbor not in distances:
                    distances[neighbor] = distances[vertex] + 1
                    queue.append(neighbor)
        if len(distances) != len(adjacency):
            raise AssertionError("materialized demo graph is disconnected")
        for vertex in adjacency:
            signatures[vertex].append(distances[vertex])
    seen, collisions = set(), 0
    for values in signatures.values():
        signature = tuple(sorted(values))
        if signature in seen:
            collisions += 1
        else:
            seen.add(signature)
    return collisions


def _ranked_checks(inst):
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    return [{"vars": list(row["vars"]), "rhs": row["rhs"], "weight": inst["copies"]}
            for row in data["checks"]]


def _satisfies_checks(checks, bits):
    return all(bits[u] ^ bits[v] ^ bits[w] == row["rhs"]
               for row in checks for u, v, w in [row["vars"]])


def _weighted_unsatisfied(checks, bits):
    return sum(row["weight"] for row in checks for u, v, w in [row["vars"]]
               if bits[u] ^ bits[v] ^ bits[w] != row["rhs"])


def _attack_incidence_outlier(inst):
    checks = _ranked_checks(inst)
    scores = [0] * inst["n"]
    for row in checks:
        for variable in row["vars"]:
            scores[variable] += row["weight"]
    median = sorted(scores)[len(scores) // 2]
    return [int(score > median) for score in scores]


def _attack_literal_majority(inst):
    positive, negative = [0] * inst["n"], [0] * inst["n"]
    for _h, _copy, _slot, _tail, literals in _expanded_clause_specs(inst):
        for variable, sign in literals:
            (positive if sign else negative)[variable] += 1
    return [int(positive[i] > negative[i]) for i in range(inst["n"])]


def _attack_one_pass_greedy(inst):
    checks = _ranked_checks(inst)
    bits = [0] * inst["n"]
    score = _weighted_unsatisfied(checks, bits)
    for variable in range(inst["n"]):
        bits[variable] ^= 1
        trial = _weighted_unsatisfied(checks, bits)
        if trial < score:
            score = trial
        else:
            bits[variable] ^= 1
    return bits


def _attack_random_restart(inst, rng, attempts=8192):
    checks = _ranked_checks(inst)
    bits = [0] * inst["n"]
    for _ in range(attempts):
        packed = rng.getrandbits(inst["n"])
        bits = [(packed >> index) & 1 for index in range(inst["n"])]
        if _satisfies_checks(checks, bits):
            break
    return bits


def _attack_step_one_recurrence(inst):
    """Obvious no-tool ansatz: assume numeric variable order is the cycle."""
    checks = _ranked_checks(inst)
    rhs_by_set = {frozenset(row["vars"]): row["rhs"] for row in checks}
    candidates, n = [], inst["n"]
    for first in (0, 1):
        for second in (0, 1):
            bits = [0] * n
            bits[0], bits[1] = first, second
            for index in range(n - 2):
                rhs = rhs_by_set.get(frozenset((index, index + 1, index + 2)), 0)
                bits[index + 2] = rhs ^ bits[index] ^ bits[index + 1]
            candidates.append(bits)
    return min(candidates, key=lambda value: _weighted_unsatisfied(checks, value))


def _gaussian_reference(inst):
    """Generic GF(2) Gauss-Jordan elimination with scalar operation counts."""
    checks, n = _ranked_checks(inst), inst["n"]
    rows = []
    for check in checks:
        coefficients = 0
        for variable in check["vars"]:
            coefficients ^= 1 << variable
        rows.append(coefficients | (check["rhs"] << n))
    rank, pivots, bit_tests, row_xors = 0, {}, 0, 0
    for column in range(n):
        pivot = None
        for row_index in range(rank, len(rows)):
            bit_tests += 1
            if (rows[row_index] >> column) & 1:
                pivot = row_index
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for row_index in range(len(rows)):
            if row_index == rank:
                continue
            bit_tests += 1
            if (rows[row_index] >> column) & 1:
                rows[row_index] ^= rows[rank]
                row_xors += 1
        pivots[column] = rank
        rank += 1
    stats = {"rank": rank, "row_xors": row_xors, "bit_tests": bit_tests,
             "scalar_operations": bit_tests + (n + 1) * row_xors}
    if rank != n:
        return None, stats
    solution = [0] * n
    for column, row_index in pivots.items():
        solution[column] = (rows[row_index] >> n) & 1
    return solution, stats


def _dpll_reference(inst):
    """Conventional clause-level DPLL with unit propagation and counters."""
    clauses = [[(variable, sign) for variable, sign in literals]
               for _h, _copy, _slot, _tail, literals in _expanded_clause_specs(inst)]
    stats = {"literal_evaluations": 0, "propagations": 0, "decisions": 0,
             "nodes": 0, "backtracks": 0, "full_clause_passes": 0}

    def inspect(clause, assignment):
        unassigned = []
        for variable, positive in clause:
            stats["literal_evaluations"] += 1
            bit = assignment[variable]
            if bit < 0:
                unassigned.append((variable, positive))
            elif bit == positive:
                return True, unassigned
        return False, unassigned

    def recurse(assignment):
        stats["nodes"] += 1
        while True:
            stats["full_clause_passes"] += 1
            changed = False
            for clause in clauses:
                satisfied, unassigned = inspect(clause, assignment)
                if satisfied:
                    continue
                if not unassigned:
                    stats["backtracks"] += 1
                    return None
                if len(unassigned) == 1:
                    variable, required = unassigned[0]
                    if assignment[variable] < 0:
                        assignment[variable] = required
                        stats["propagations"] += 1
                        changed = True
                    elif assignment[variable] != required:
                        stats["backtracks"] += 1
                        return None
            if not changed:
                break
        if all(bit >= 0 for bit in assignment):
            return assignment
        best = None
        for clause in clauses:
            satisfied, unassigned = inspect(clause, assignment)
            if not satisfied and unassigned and (best is None or len(unassigned) < len(best)):
                best = unassigned
        variable = best[0][0] if best else next(i for i, bit in enumerate(assignment) if bit < 0)
        for bit in (0, 1):
            stats["decisions"] += 1
            child = list(assignment)
            child[variable] = bit
            solution = recurse(child)
            if solution is not None:
                return solution
        stats["backtracks"] += 1
        return None

    return recurse([-1] * inst["n"]), stats


def _transformed_instance(inst, flips, seed):
    """Apply graph-spelling symmetries and carry the witness through."""
    rng = random.Random(seed)
    transformed = {key: value for key, value in inst.items() if key != "_validation_cache"}
    variables = [dict(item) for item in inst["variables"]]
    rng.shuffle(variables)
    checks = []
    for check in inst["checks"]:
        permutation = list(range(3)); rng.shuffle(permutation)
        old_vars = check["vars"]
        new_vars = [old_vars[pos] for pos in permutation]
        new_patterns = [[pattern[pos] ^ flips[old_vars[pos]] for pos in permutation]
                        for pattern in check["patterns"]]
        rhs = check["rhs"]
        for variable in old_vars:
            rhs ^= flips[variable]
        checks.append({"h": check["h"], "vars": new_vars, "rhs": rhs,
                       "patterns": new_patterns})
    rng.shuffle(checks)
    packed, error = _decode_answer(inst, inst["answer"])
    if error is not None:
        raise ValueError(error)
    bits = [((packed >> rank) & 1) ^ flips[rank] for rank in range(inst["n"])]
    transformed["variables"], transformed["checks"] = variables, checks
    transformed["answer"] = _encode_bits(inst["n"], bits)
    return transformed


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    return len(compact), (len(compact) + 3) // 4


def selftest():
    report = {"paper": "arXiv:2303.06986", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY,
              "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY])}

    failures, attempts, bfs_checks = [], 0, 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
            if preset == "demo":
                bfs_checks += 1
                collisions = _explicit_collision_count(inst, inst["answer"])
                if collisions != 0:
                    failures.append({"preset": preset, "seed": seed,
                                     "reason": f"explicit BFS found {collisions} collisions"})
    report["G1_planted_verifies"] = {"pass": not failures, "attempts": attempts,
                                      "explicit_demo_bfs_checks": bfs_checks,
                                      "failures": failures}

    shipping = make_instance(seed=230306986, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    # Leave the high, partially-used nibble in place so the swap stays in range.
    unequal = next(((i, j) for i in range(1, len(planted)) for j in range(i + 1, len(planted))
                    if planted[i] != planted[j]), None)
    if unequal is None:
        raise AssertionError("shipping witness has no unequal hexadecimal digits to swap")
    swapped = list(planted)
    swapped[unequal[0]], swapped[unequal[1]] = swapped[unequal[1]], swapped[unequal[0]]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two_unequal_digits": "".join(swapped),
        "duplicate_one": planted + planted[-1],
        "empty": "",
        "out_of_range": "f" + "0" * (len(planted) - 1),
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values()) and len(reasons) == len(cases),
        "cases": cases, "distinct_reasons": len(reasons)}

    realistic = ("I checked the induced distance multisets.\n<answer>\n```text\n" + planted
                 + "\n```\n</answer>\nThe leading zero, if present, is retained.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed_length": len(parsed) if isinstance(parsed, str) else None}

    guess_rng, guess_total, guess_hits = random.Random(0x230306986), 200_000, 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    observed = guess_hits / guess_total
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6, "hits": guess_hits, "total": guess_total,
        "observed_probability": observed, "exact_probability_from_full_rank": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform over all n-bit canonical a/b choices; mandatory e and g vertices are already enforced",
        "wall_clock_sec": round(guess_elapsed, 6)}

    attack_functions = {
        "incidence_outlier": lambda inst, rng: _attack_incidence_outlier(inst),
        "literal_majority": lambda inst, rng: _attack_literal_majority(inst),
        "one_pass_greedy": lambda inst, rng: _attack_one_pass_greedy(inst),
        "random_restart_8192": lambda inst, rng: _attack_random_restart(inst, rng, 8192),
        "step_one_recurrence": lambda inst, rng: _attack_step_one_recurrence(inst),
    }
    attack_results = {name: {"successes": 0, "attempts": 0} for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            t0 = time.perf_counter()
            bits = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - t0
            candidate = bits if isinstance(bits, str) else _encode_bits(inst["n"], bits)
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
    for name, elapsed in attack_elapsed.items():
        attack_results[name]["wall_clock_sec_total_8"] = round(elapsed, 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())

    gaussian_successes = dpll_successes = shortcut_successes = 0
    gaussian_elapsed = dpll_elapsed = 0.0
    gaussian_operations, gaussian_xors = [], []
    dpll_evaluations, dpll_nodes, dpll_decisions = [], [], []
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        t0 = time.perf_counter()
        solution, stats = _gaussian_reference(inst)
        gaussian_elapsed += time.perf_counter() - t0
        gaussian_operations.append(stats["scalar_operations"])
        gaussian_xors.append(stats["row_xors"])
        if solution is not None:
            gaussian_successes += int(verify(inst, _encode_bits(inst["n"], solution))[0])
        t0 = time.perf_counter()
        dpll_solution, dpll_stats = _dpll_reference(inst)
        dpll_elapsed += time.perf_counter() - t0
        dpll_evaluations.append(dpll_stats["literal_evaluations"])
        dpll_nodes.append(dpll_stats["nodes"]); dpll_decisions.append(dpll_stats["decisions"])
        if dpll_solution is not None:
            dpll_successes += int(verify(inst, _encode_bits(inst["n"], dpll_solution))[0])
        shortcut_successes += int(verify(inst, _encode_bits(inst["n"], _compact_shortcut(inst)))[0])

    reference = {
        "name": "Gauss-Jordan elimination over GF(2)",
        "complexity": "O(n^3) scalar bit operations",
        "wall_clock_sec_total_8": round(gaussian_elapsed, 6),
        "wall_clock_sec_mean": round(gaussian_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(gaussian_operations) // len(gaussian_operations),
        "operations_min": min(gaussian_operations), "operations_max": max(gaussian_operations),
        "row_xors_mean": sum(gaussian_xors) // len(gaussian_xors),
        "solves": f"{gaussian_successes}/{len(attack_seeds)}, as expected"}
    intended_operations = 5 * shipping["n"] + 8
    report["G6_adversary_panel"] = {
        "pass": all_failed and gaussian_successes == dpll_successes == shortcut_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "domain_standard_sat_reference": {
            "name": "DPLL with unit propagation and minimum-residual-clause branching",
            "complexity": "O(2^n M) worst case; measured on all expanded clause gadgets",
            "wall_clock_sec_total_8": round(dpll_elapsed, 6),
            "wall_clock_sec_mean": round(dpll_elapsed / len(attack_seeds), 8),
            "literal_evaluations_mean": sum(dpll_evaluations) // len(dpll_evaluations),
            "literal_evaluations_min": min(dpll_evaluations),
            "literal_evaluations_max": max(dpll_evaluations),
            "nodes_mean": sum(dpll_nodes) / len(dpll_nodes),
            "decisions_mean": sum(dpll_decisions) / len(dpll_decisions),
            "solves": f"{dpll_successes}/{len(attack_seeds)}, as expected"},
        "compact_route": {
            "name": "adjacent affine-window cancellation to one step-three cycle",
            "worst_case_exact_operations": intended_operations,
            "count_model": "two XORs and two modular index updates per edge, a possible n-bit complement, and eight setup/check operations",
            "solves": f"{shortcut_successes}/{len(attack_seeds)}, as expected"}}

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_failed,
        "exact_valid_answers": 1, "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": observed, "density_hits": guess_hits,
        "density_samples": guess_total, "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "attack_trial_evaluations_upper_bound_total_8": 8192 * len(attack_seeds),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))}

    doubled_n = 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
    while doubled_n % 3 == 0:
        doubled_n += 1
    larger = make_instance(n=doubled_n, copies=shipping["copies"], seed=707)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and larger["graph_vertices"] > shipping["graph_vertices"],
        "shipping_n": shipping["n"], "doubled_n": doubled_n,
        "shipping_graph_vertices": shipping["graph_vertices"],
        "doubled_graph_vertices": larger["graph_vertices"], "verify_reason": larger_reason}

    invariance_checks = carried_checks = 0
    key_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key, rng = canonical_key(inst), random.Random(12000 + seed)
        for variant, flips in enumerate(([0] * inst["n"], [rng.getrandbits(1) for _ in range(inst["n"])])):
            transformed = _transformed_instance(inst, flips, 15000 + 10 * seed + variant)
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "variant": variant, "reason": "key changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": seed, "variant": variant, "reason": "carried witness failed"})
    unrelated = [canonical_key(make_instance(seed=20000 + seed,
                 **DIFFICULTY[SHIPPING_DIFFICULTY])) for seed in range(20)]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks, "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks, "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": ["storage-order permutations", "triple-coordinate permutations",
            "independent T/F and a/b endpoint swaps", "composition of all preceding maps"],
        "canonical_numbering": "unique pendant lengths rank variable gadgets and clause-tail blocks"}

    answer_chars, answer_tokens = _json_answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and shipping["n"] <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps, "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars, "answer_tokens": answer_tokens,
        "answer_elements": shipping["n"], "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300}}

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
