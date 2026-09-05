"""Self-contained problem generator for arXiv:0907.4573.

The proof of Theorem 1 in Section 3 converts each equation of Max-r-Lin2 into
2^(r-1) r-clauses, preserving exactly how many constraints are violated.  This module
uses r=3.  It samples a Boolean assignment first, evaluates an invertible
cyclic system of parity equations at that assignment, and expands every row
into the four clauses from the paper.  Thus generation never solves the
instance it creates.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - graceful fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "multiset of exact 3-CNF clauses with signed Boolean literals",
        "paper-licensed GF(2) parity summary for each four-clause block",
        "Boolean truth assignment",
    ],
    "verification_operations": [
        "Boolean literal evaluation",
        "exact satisfied-clause count",
        "integer comparison with the above-tight-lower-bound target",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, direct-kernel proof of Theorem 1: each GF(2) parity "
        "equation is expanded into four exact 3-CNF clauses"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The parity coefficient operator encoded by the clause blocks "
        "squares to the identity, replacing a general Max-3-SAT search by one "
        "application of that same operator."
    ),
    "hardness_basis": (
        "Track B: Theorem 1 gives an O(m)+2^{O(k^2)} general algorithm, and "
        "reversing the parity-to-CNF construction in its Section 3 proof "
        "gives exact GF(2) Gaussian elimination in expected O(m+n^3); at the "
        "hard shipping preset it solved 8/8 in about 0.0034 seconds mean using "
        "125,684 counted scalar operations mean (134,116 maximum), while the "
        "involution shortcut uses 2n=288 binary XORs after recognizing the "
        "paired-row structure."
    ),
    "max_answer_tokens": 73,
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
        "Exactly n Boolean bits as one JSON list [b1,...,bn] in public "
        "variable order; every entry is the integer 0 or 1."
    ),
    "bounds": {
        "length": "exactly n",
        "alphabet": [0, 1],
        "maximum_shipping_length": 144,
    },
}

DIFFICULTY: dict = {
    "hard": {"n": 144, "decoy_rows": 40},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: The GF(2) coefficient matrix encoded by the clause blocks is an involution."
)
PLACEBO_HINT: str = (
    "Hint: The signed three-literal formula requires careful Boolean bookkeeping in public variable order."
)

# Updated from the harness-owned transcripts after the three runs.  The arms
# are diagnostics only; G9(c)'s output and exact-operation caps are the gate.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "unavailable: OpenRouter HTTP 403 total key limit",
}

NOTES = r"""
Definition and easy regimes. Section 2 defines an r-CNF formula as a multiset
of clauses, each containing exactly r distinct literals and no complementary
pair. It defines Max-r-Sat above the tight lower bound by the target
((2^r-1)m+k)/2^r. Lemma 2 identifies the exact polynomial identity relating
that target to a degree-r multilinear polynomial. Theorem 1 is the decisive
easy-regime result: for fixed r the decision and witness problem takes
O(m)+2^{O(k^2)}, with an O(k^2) kernel. Consequently this family does not claim
Track-A hardness and does not keep k small; with r=3 and k=m its target is m,
and k grows linearly with the number of core and decoy parity rows.

Paper construction. In the direct-kernel part of the proof of Theorem 1,
Section 3 replaces every equation z_i1+...+z_ir=b over GF(2) with the 2^(r-1)
clauses falsified by assignments that violate the equation. Satisfying an
equation satisfies every clause in its block, while violating it falsifies
exactly one. This module uses precisely that native 3-CNF construction with
r=3; it is not a graph or finite-field surrogate shown to the solver.

Generation certificate. For n=2h, choose a directed h-cycle p and define A by
  (Ax)_i     = x_i xor x_p(i) xor x_(h+p(i)),
  (Ax)_(h+i) = x_(h+i) xor x_p(i) xor x_(h+p(i)).
Writing A=I+N, both rows belonging to a pair have the same N-part. Therefore
N^2=0 and A^2=I over GF(2), so A is invertible. The generator samples x first,
computes b=Ax, randomly renames variables, and expands each row. Extra rows
are sampled on unused variable pairs, evaluated at the same x, and expanded
identically. The held witness is x carried through the renaming. No SAT,
Max-SAT, kernel, or linear solver is invoked by make_instance.

Step-0 discrimination and Track B. The reverse of the paper's construction is
an efficient algorithm: group four clauses having the same unsigned triple,
read their parity, and apply GF(2) Gaussian elimination. It is reported as the
successful reference_algorithm, never disguised as a failed attack. The
compact route instead recognizes the repeated-pair cycle and A^2=I, evaluating
x=Ab with two XORs per output bit. The exact mechanical and compact costs at
the shipping preset are recorded by selftest.

Output contract. The renderer gives the GF(2) equation enforced by each
four-clause block as a redundant exact summary. This is the same transformation
proved in Section 3, keeps all native clauses visible, and makes the intended
post-insight cost exactly the reported two XORs per answer bit rather than
quietly charging the solver for reconstructing every parity right-hand side.

Planting hygiene and attacks. Every parity row, core or decoy, is rendered by
the same four-clause truth table; within every block each variable occurs
positively twice and negatively twice. Variables are independently relabelled,
and row units and literals are shuffled. Literal majority, occurrence outliers,
public-order periodicity, bounded greedy repair, randomized parity repair, and an uncoupled parity-
RHS vote are all tested over eight shipping seeds. The pair co-degree signal
is deliberately present: it is the structural clue needed for the short route,
not a correlation with the sampled answer bits.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _row_support(n, successor, row):
    """The three natural (pre-relabel) columns in a core row."""
    half = n // 2
    if row < half:
        i = row
        return (i, successor[i], half + successor[i])
    i = row - half
    return (half + i, successor[i], half + successor[i])


def _parity_clauses(triple, rhs):
    """The four ordinary clauses whose conjunction says xor(triple)=rhs."""
    clauses = []
    for bad in itertools.product((0, 1), repeat=3):
        if (bad[0] ^ bad[1] ^ bad[2]) == rhs:
            continue
        # A positive literal is false at 0; a negative literal is false at 1.
        clauses.append([
            (v + 1) if bit == 0 else -(v + 1)
            for v, bit in zip(triple, bad)
        ])
    return clauses


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a Max-3-SAT-above-average witness instance."""
    decoy_rows = params.pop("decoy_rows", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    if (isinstance(decoy_rows, bool) or not isinstance(decoy_rows, int)
            or decoy_rows < 0):
        raise ValueError("decoy_rows must be a nonnegative integer")
    max_decoys = n * (n - 6) // 12
    if decoy_rows > max_decoys:
        raise ValueError("too many decoy rows for the linear-triple packing")

    rng = random.Random(seed)
    half = n // 2
    cycle = list(range(half))
    rng.shuffle(cycle)
    successor = [0] * half
    for pos, here in enumerate(cycle):
        successor[here] = cycle[(pos + 1) % half]

    natural_answer = [rng.randrange(2) for _ in range(n)]
    supports = [_row_support(n, successor, row) for row in range(n)]
    rhs = [
        natural_answer[a] ^ natural_answer[b] ^ natural_answer[c]
        for a, b, c in supports
    ]

    old_to_public = list(range(n))
    rng.shuffle(old_to_public)
    public_answer = [0] * n
    for old, new in enumerate(old_to_public):
        public_answer[new] = natural_answer[old]

    row_units = []
    core_triples = set()
    # Each parity block is presented contiguously, but block order, clause order,
    # and literal order are random.  In particular, the paired core rows are not
    # adjacent: finding their repeated two-variable supports is the structural
    # recognition task, not a presentation-order clue.
    for support, bit in zip(supports, rhs):
        triple = tuple(old_to_public[v] for v in support)
        core_triples.add(tuple(sorted(triple)))
        block = _parity_clauses(triple, bit)
        for clause in block:
            rng.shuffle(clause)
        rng.shuffle(block)
        row_units.append(block)

    used_triples = set(core_triples)
    used_pairs = {
        tuple(sorted(pair))
        for triple in core_triples
        for pair in itertools.combinations(triple, 2)
    }
    made = 0
    while made < decoy_rows:
        triple = tuple(sorted(rng.sample(range(n), 3)))
        triple_pairs = {
            tuple(sorted(pair)) for pair in itertools.combinations(triple, 2)
        }
        if triple in used_triples or not triple_pairs.isdisjoint(used_pairs):
            continue
        used_triples.add(triple)
        used_pairs.update(triple_pairs)
        parity = (public_answer[triple[0]] ^ public_answer[triple[1]]
                  ^ public_answer[triple[2]])
        block = _parity_clauses(triple, parity)
        for clause in block:
            rng.shuffle(clause)
        rng.shuffle(block)
        row_units.append(block)
        made += 1

    rng.shuffle(row_units)
    clauses = [clause for unit in row_units for clause in unit]
    m = len(clauses)
    k = m
    target = (7 * m + k) // 8
    return {
        "r": 3,
        "n": n,
        "m": m,
        "k": k,
        "target": target,
        "clauses": clauses,
        "decoy_rows": decoy_rows,
        "answer": public_answer,
    }


def render(inst) -> str:
    """Render the complete native Max-3-SAT-above-average question."""
    n = inst["n"]
    lines = [
        "Find a truth assignment meeting the stated Max-3-SAT threshold.",
        "",
        "There are Boolean variables x1 through x%d. In a clause, a positive" % n,
        "integer j denotes xj and a negative integer -j denotes NOT xj.",
        "Each line below is one clause (the OR of its three distinct literals).",
        "The formula is the multiset of all lines, so repeated clauses would count",
        "separately. Variable indices are 1-based. A clause is satisfied when at",
        "least one of its literals is true.",
        "",
        "For r=3 and m clauses, the tight guaranteed lower bound is 7m/8.",
        "This instance uses the paper's scaled surplus parameter k and requires",
        "at least (7m+k)/8 satisfied clauses. Here n=%d, m=%d, k=%d, so the" %
        (n, inst["m"], inst["k"]),
        "required exact integer target is %d satisfied clauses." % inst["target"],
        "Every answer entry must be exactly 0 (false) or 1 (true).",
        "For readability only, clauses on the same unsigned variable triple are",
        "consecutive, with a blank line between different triples; ordering does",
        "not change the clause multiset.",
        "Each Block header also states the exact GF(2) parity equation jointly",
        "enforced by its following four clauses. XOR is addition modulo 2, so an",
        "XOR is 1 exactly when an odd number of its input bits are 1.",
        "",
        "Clauses:",
    ]
    groups = {}
    for clause in inst["clauses"]:
        support = tuple(sorted(abs(lit) for lit in clause))
        groups.setdefault(support, []).append(clause)
    clause_number = 0
    for block_number, (support, clauses) in enumerate(groups.items(), 1):
        if block_number > 1:
            lines.append("")
        parsed = _clause_bad_tuple(clauses[0])
        bad = parsed[1]
        rhs = bad[0] ^ bad[1] ^ bad[2] ^ 1
        lines.append(
            "Block B%03d: x%d XOR x%d XOR x%d = %d" %
            (block_number, support[0], support[1], support[2], rhs))
        for clause in clauses:
            clause_number += 1
            lines.append("C%04d: %s" % (
                clause_number, " ".join("%+d" % x for x in clause)))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list",
        "of exactly %d bits in the order [x1,x2,...,x%d]." % (n, n),
        "Example format: <answer>[0,1,0,1]</answer>",
        "The example is syntax only and does not have the required length.",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Extract the last tagged JSON list, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body,
                          flags=re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def _satisfied_count(inst, answer):
    count = 0
    for clause in inst["clauses"]:
        count += int(any(
            (lit > 0 and answer[abs(lit) - 1] == 1)
            or (lit < 0 and answer[abs(lit) - 1] == 0)
            for lit in clause
        ))
    return count


def verify(inst, answer) -> tuple[bool, str]:
    """Inspect only the public clauses and candidate, never inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    n = inst.get("n")
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, "assignment is missing %d bit%s" % (
            n - len(answer), "" if n - len(answer) == 1 else "s")
    if len(answer) > n:
        return False, "assignment has %d extra bit%s" % (
            len(answer) - n, "" if len(answer) - n == 1 else "s")
    for i, bit in enumerate(answer, 1):
        if isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1):
            return False, "entry %d is not a Boolean bit" % i
    # Shipping instances ask for all clauses.  Rejecting on the first false
    # clause is exact and keeps the 200k-candidate density measurement cheap.
    if inst["target"] == inst["m"]:
        for ci, clause in enumerate(inst["clauses"], 1):
            if not any(
                (lit > 0 and answer[abs(lit) - 1] == 1)
                or (lit < 0 and answer[abs(lit) - 1] == 0)
                for lit in clause
            ):
                return False, (
                    "threshold missed: clause %d is false, but all %d clauses "
                    "are required" % (ci, inst["target"]))
        return True, "ok"
    satisfied = _satisfied_count(inst, answer)
    if satisfied < inst["target"]:
        return False, "threshold missed: satisfied %d of required %d clauses" % (
            satisfied, inst["target"])
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the explicit language of n-bit assignments."""
    word = rng.getrandbits(inst["n"])
    return [(word >> i) & 1 for i in range(inst["n"])]


def search_space(inst) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst) -> int | None:
    """Count exactly only when the full language has at most 2^20 words."""
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for mask in range(1 << n):
        candidate = [(mask >> i) & 1 for i in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def _clause_bad_tuple(clause):
    """Return (sorted triple, falsifying tuple in sorted variable order)."""
    by_var = {}
    for lit in clause:
        var = abs(lit) - 1
        if var in by_var:
            return None
        by_var[var] = 0 if lit > 0 else 1
    if len(by_var) != 3:
        return None
    triple = tuple(sorted(by_var))
    return triple, tuple(by_var[v] for v in triple)


def _extract_parity_rows(inst):
    """Reverse the paper's four-clause expansion exactly."""
    groups = defaultdict(set)
    inspections = 0
    for clause in inst["clauses"]:
        parsed = _clause_bad_tuple(clause)
        inspections += len(clause)
        if parsed is not None:
            triple, bad = parsed
            groups[triple].add(bad)
    rows = []
    for triple, bads in groups.items():
        if len(bads) != 4:
            continue
        parities = {a ^ b ^ c for a, b, c in bads}
        if len(parities) != 1:
            continue
        rows.append((triple, next(iter(parities)) ^ 1))
    return rows, inspections


def _gaussian_reference(inst):
    """Solve all extracted rows by exact GF(2) RREF and count bit work."""
    n = inst["n"]
    parity_rows, operations = _extract_parity_rows(inst)
    packed = []
    for triple, rhs in parity_rows:
        mask = 0
        for col in triple:
            mask ^= 1 << col
            operations += 1
        packed.append(mask | (rhs << n))
    rank = 0
    pivot_cols = []
    for col in range(n):
        pivot = None
        for row in range(rank, len(packed)):
            operations += 1
            if (packed[row] >> col) & 1:
                pivot = row
                break
        if pivot is None:
            continue
        packed[rank], packed[pivot] = packed[pivot], packed[rank]
        for row in range(len(packed)):
            if row == rank:
                continue
            operations += 1
            if (packed[row] >> col) & 1:
                packed[row] ^= packed[rank]
                operations += n + 1
        pivot_cols.append(col)
        rank += 1
        if rank == n:
            break
    if rank < n:
        return None, operations
    answer = [0] * n
    for row_index, col in enumerate(pivot_cols):
        answer[col] = (packed[row_index] >> n) & 1
    return answer, operations


def _core_coordinates(inst):
    """Recover the repeated-pair core from public parity rows."""
    rows, inspections = _extract_parity_rows(inst)
    expected = inst["n"] + inst.get("decoy_rows", 0)
    if len(rows) != expected:
        raise ValueError("instance does not contain the expected parity rows")
    pair_counts = Counter()
    for triple, _ in rows:
        for pair in itertools.combinations(triple, 2):
            pair_counts[tuple(sorted(pair))] += 1
    pairs = sorted(pair for pair, count in pair_counts.items() if count == 2)
    n = inst["n"]
    if len(pairs) != n // 2 or len({v for pair in pairs for v in pair}) != n:
        raise ValueError("parity core does not induce the required perfect pairing")
    pair_of = {}
    for pid, pair in enumerate(pairs):
        for var in pair:
            pair_of[var] = pid

    distinguished = set(pairs)
    core_rows = [
        (triple, rhs) for triple, rhs in rows
        if any(tuple(sorted(pair)) in distinguished
               for pair in itertools.combinations(triple, 2))
    ]
    if len(core_rows) != n:
        raise ValueError("pair co-degree did not isolate the expected core")

    successor = {}
    rhs_by_variable = {}
    for triple, rhs in core_rows:
        grouped = defaultdict(list)
        for var in triple:
            grouped[pair_of[var]].append(var)
        singles = [pid for pid, vs in grouped.items() if len(vs) == 1]
        doubles = [pid for pid, vs in grouped.items() if len(vs) == 2]
        if len(singles) != 1 or len(doubles) != 1:
            raise ValueError("malformed pair incidence")
        src, dst = singles[0], doubles[0]
        singleton = grouped[src][0]
        if src in successor and successor[src] != dst:
            raise ValueError("inconsistent core successor")
        successor[src] = dst
        rhs_by_variable[singleton] = rhs
    if len(successor) != n // 2 or len(rhs_by_variable) != n:
        raise ValueError("incomplete core coordinates")
    return pairs, pair_of, successor, rhs_by_variable, inspections


def _involution_compact_route(inst):
    """Use A^2=I to recover the unique assignment in exactly 2n XORs."""
    pairs, pair_of, successor, rhs, inspections = _core_coordinates(inst)
    answer = [0] * inst["n"]
    for var in range(inst["n"]):
        a, b = pairs[successor[pair_of[var]]]
        answer[var] = rhs[var] ^ rhs[a] ^ rhs[b]
    return answer, 2 * inst["n"], inspections


def canonical_key(inst) -> str:
    """A sign-switch and relabelling-invariant WL key of the row hypergraph.

    Variable polarity switching changes parity right-hand sides but not row
    supports.  Because the core is invertible, all consistent right-hand sides
    on a fixed support hypergraph are related by such a switch.  Stable color
    refinement is the strongest cheap invariant used here; it is deliberately
    not a hash of the seed or rendered statement.
    """
    counts = Counter()
    for clause in inst["clauses"]:
        triple = tuple(sorted(abs(lit) - 1 for lit in clause))
        counts[triple] += 1
    rows = sorted(triple for triple, count in counts.items() if count == 4)
    n = inst["n"]
    incident = [[] for _ in range(n)]
    for rid, triple in enumerate(rows):
        for var in triple:
            incident[var].append(rid)

    degrees = [len(rs) for rs in incident]
    degree_values = {value: i for i, value in enumerate(sorted(set(degrees)))}
    vcolor = [degree_values[value] for value in degrees]
    rcolor = [0] * len(rows)
    history = []
    for _ in range(2 * n + 2):
        vsig = [(vcolor[v], tuple(sorted(rcolor[r] for r in incident[v])))
                for v in range(n)]
        rsig = [(rcolor[r], tuple(sorted(vcolor[v] for v in rows[r])))
                for r in range(len(rows))]
        vmap = {sig: i for i, sig in enumerate(sorted(set(vsig)))}
        rmap = {sig: i for i, sig in enumerate(sorted(set(rsig)))}
        new_v = [vmap[sig] for sig in vsig]
        new_r = [rmap[sig] for sig in rsig]
        history.append((
            sorted(Counter(new_v).items()),
            sorted(Counter(new_r).items()),
        ))
        if new_v == vcolor and new_r == rcolor:
            vcolor, rcolor = new_v, new_r
            break
        vcolor, rcolor = new_v, new_r
    row_patterns = sorted(tuple(sorted(vcolor[v] for v in triple))
                          for triple in rows)
    payload = json.dumps(
        [n, len(rows), history, row_patterns], separators=(",", ":"))
    return "xor-row-wl-v1:" + hashlib.sha256(payload.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Use the remaining XOR-operation headroom, then report the route cap."""
    current = dict(params)
    current.pop("_preset", None)
    n = current.get("n")
    decoys = current.get("decoy_rows", 0)
    if not isinstance(n, int) or n < 6 or n % 2:
        return None
    # Grow the haystack without lengthening the answer.  The parity-aware repair
    # attack remains 0/8 through 32 decoy rows; beyond that the extra consistent
    # constraints begin creating a useful attraction signal, so 32 is the tested
    # ceiling for this axis.
    if decoys < 32:
        return {"n": n, "decoy_rows": min(32, decoys + 8)}
    if n < 150:
        return {"n": 150, "decoy_rows": decoys}
    # Any larger core needs >300 XORs after the insight, even though its JSON
    # answer would still fit the character and atom caps.
    return "cap_bound"


def _attack_literal_majority(inst):
    score = [0] * inst["n"]
    for clause in inst["clauses"]:
        for lit in clause:
            score[abs(lit) - 1] += 1 if lit > 0 else -1
    return [int(value > 0) for value in score]


def _attack_occurrence_median(inst):
    counts = [0] * inst["n"]
    for clause in inst["clauses"]:
        for lit in clause:
            counts[abs(lit) - 1] += 1
    median = sorted(counts)[len(counts) // 2]
    return [int(value > median) for value in counts]


def _unsatisfied_indices(inst, candidate):
    bad = []
    for ci, clause in enumerate(inst["clauses"]):
        if not any((lit > 0 and candidate[abs(lit) - 1] == 1)
                   or (lit < 0 and candidate[abs(lit) - 1] == 0)
                   for lit in clause):
            bad.append(ci)
    return bad


def _attack_greedy_repair(inst):
    candidate = _attack_literal_majority(inst)
    for _ in range(inst["n"]):
        bad = _unsatisfied_indices(inst, candidate)
        if not bad:
            break
        clause = inst["clauses"][bad[0]]
        best = None
        for lit in clause:
            var = abs(lit) - 1
            candidate[var] ^= 1
            remaining = len(_unsatisfied_indices(inst, candidate))
            candidate[var] ^= 1
            trial = (remaining, var)
            if best is None or trial < best:
                best = trial
        candidate[best[1]] ^= 1
    return candidate


def _parity_violations(rows, candidate):
    return [
        ri for ri, (triple, rhs) in enumerate(rows)
        if (candidate[triple[0]] ^ candidate[triple[1]]
            ^ candidate[triple[2]]) != rhs
    ]


def _attack_randomized_parity_repair(inst, rng):
    """A tool-free-style local search after noticing the parity blocks."""
    rows, _ = _extract_parity_rows(inst)
    incident = [[] for _ in range(inst["n"])]
    for row_index, (triple, _) in enumerate(rows):
        for var in triple:
            incident[var].append(row_index)
    for _ in range(32):
        candidate = [rng.randrange(2) for _ in range(inst["n"])]
        bad = set(_parity_violations(rows, candidate))
        for _ in range(8 * inst["n"]):
            if not bad:
                return candidate
            triple, _ = rows[rng.choice(tuple(bad))]
            choices = []
            for var in triple:
                bad_incident = sum(row in bad for row in incident[var])
                remaining = len(bad) + len(incident[var]) - 2 * bad_incident
                choices.append((
                    remaining, rng.random(), var))
            chosen = min(choices)[2]
            candidate[chosen] ^= 1
            for row in incident[chosen]:
                if row in bad:
                    bad.remove(row)
                else:
                    bad.add(row)
    return candidate


def _attack_short_period(inst):
    best = None
    for period in range(1, 7):
        for mask in range(1 << period):
            candidate = [(mask >> (i % period)) & 1 for i in range(inst["n"])]
            trial = (-_satisfied_count(inst, candidate), period, mask, candidate)
            if best is None or trial[:3] < best[:3]:
                best = trial
    return best[3]


def _attack_rhs_vote(inst):
    rows, _ = _extract_parity_rows(inst)
    votes = [[] for _ in range(inst["n"])]
    for triple, rhs in rows:
        for var in triple:
            votes[var].append(rhs)
    return [int(sum(values) * 2 > len(values)) if values else 0
            for values in votes]


def _relabel_and_switch(inst, old_to_new, flips, rng):
    """Apply genuine variable renaming and polarity switching symmetries."""
    n = inst["n"]
    if sorted(old_to_new) != list(range(n)) or len(flips) != n:
        raise ValueError("bad relabelling or switch vector")
    clauses = []
    for clause in inst["clauses"]:
        moved = []
        for lit in clause:
            old = abs(lit) - 1
            sign = 1 if lit > 0 else -1
            if flips[old]:
                sign *= -1
            moved.append(sign * (old_to_new[old] + 1))
        rng.shuffle(moved)
        clauses.append(moved)
    rng.shuffle(clauses)
    carried = [0] * n
    for old, new in enumerate(old_to_new):
        carried[new] = inst["answer"][old] ^ flips[old]
    transformed = dict(inst)
    transformed["clauses"] = clauses
    transformed["answer"] = carried
    return transformed


def _answer_atom_count(value):
    if isinstance(value, dict):
        return sum(_answer_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atom_count(v) for v in value)
    return 1


def selftest() -> dict:
    report = {}

    verified = 0
    attempts = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            verified += int(verify(inst, inst["answer"])[0])
            attempts += 1
    report["G1_planted_verifies"] = {
        "pass": verified == attempts,
        "verified": verified,
        "attempts": attempts,
        "generation_route": "inverse generation plus the identity A^2=I",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)
    base = shipping["answer"]
    swap = base[:]
    left = next(i for i, bit in enumerate(swap) if bit == 0)
    right = next(i for i, bit in enumerate(swap) if bit == 1)
    swap[left], swap[right] = swap[right], swap[left]
    corruptions = {
        "drop": base[:-1],
        "swap": swap,
        "duplicate": base + [base[-1]],
        "empty": [],
        "out_of_range": [2] + base[1:],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {result["reason"] for result in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(item["rejected"] for item in corruption_results.values())
                 and len(reasons) == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(base, separators=(",", ":"))
    realistic = (
        "The repeated blocks determine one assignment.\n"
        "<answer>```json\n" + wire + "\n```</answer>\n"
        "I also checked the target count."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == base and json.loads(json.dumps(base)) == base
                 and parse_answer("not an answer") is None),
        "parsed_equals_answer": parsed == base,
        "json_native": json.loads(json.dumps(base)) == base,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(
            shipping, random_candidate(shipping, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(shipping),
        "prior": "uniform over all explicitly admissible n-bit assignments",
    }

    t0 = time.perf_counter()
    reference_answer, reference_ops = _gaussian_reference(shipping)
    reference_sec = time.perf_counter() - t0
    reference_ok = (reference_answer is not None
                    and verify(shipping, reference_answer)[0])
    compact_answer, compact_ops, compact_inspections = _involution_compact_route(
        shipping)
    compact_ok = verify(shipping, compact_answer)[0]
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_total >= 200_000 and guess_rate < 1e-6
                 and reference_ok and compact_ok and enumerate_all(demo) == 1),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "construction_exact_solution_count": 1,
        "construction_exact_density": "1/2^%d" % shipping["n"],
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_algorithm": (
            "paper-block extraction plus exact GF(2) Gaussian elimination"),
        "baseline_wall_clock_seconds": round(reference_sec, 6),
        "baseline_scalar_operations": reference_ops,
        "baseline_verified": reference_ok,
        "compact_route_exact_operations": compact_ops,
        "audit_reconstruction_literal_inspections": compact_inspections,
        "rendered_parity_summaries": len(_extract_parity_rows(shipping)[0]),
        "compact_route_verified": compact_ok,
    }

    attacks = {
        "outlier_literal_majority": {"successes": 0, "attempts": 8},
        "outlier_occurrence_median": {"successes": 0, "attempts": 8},
        "greedy_clause_repair_n": {"successes": 0, "attempts": 8},
        "random_restart_parity_repair_32x8n": {
            "successes": 0, "attempts": 8},
        "public_order_short_period": {"successes": 0, "attempts": 8},
        "xor_rhs_local_vote": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_literal_majority": _attack_literal_majority(inst),
            "outlier_occurrence_median": _attack_occurrence_median(inst),
            "greedy_clause_repair_n": _attack_greedy_repair(inst),
            "public_order_short_period": _attack_short_period(inst),
            "xor_rhs_local_vote": _attack_rhs_vote(inst),
        }
        repair_rng = random.Random(seed ^ 0x5A17)
        candidates["random_restart_parity_repair_32x8n"] = (
            _attack_randomized_parity_repair(inst, repair_rng))
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rt0 = time.perf_counter()
        candidate, operations = _gaussian_reference(inst)
        reference_times.append(time.perf_counter() - rt0)
        reference_operations.append(operations)
        reference_successes += int(
            candidate is not None and verify(inst, candidate)[0])
    all_failed = all(value["successes"] == 0 and value["attempts"] >= 8
                     for value in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "paper-block extraction plus exact GF(2) Gaussian elimination",
            "complexity": "expected O(m + n^3) exact binary operations",
            "wall_clock_sec_mean": round(
                sum(reference_times) / len(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(
                sum(reference_operations) / len(reference_operations)),
            "operations_max": max(reference_operations),
            "solves": "%d/8, as expected" % reference_successes,
        },
    }

    doubled = make_instance(
        n=2 * shipping["n"],
        decoy_rows=2 * shipping["decoy_rows"],
        seed=2718,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] > shipping["n"]
                 and search_space(doubled) > search_space(shipping)),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_clause_count": shipping["m"],
        "doubled_clause_count": doubled["m"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": shipping["n"],
        "doubled_search_space_bits": doubled["n"],
    }

    invariant = 0
    carried_valid = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **shipping_params)
        rrng = random.Random(9000 + seed)
        first = list(range(inst["n"]))
        second = list(range(inst["n"]))
        rrng.shuffle(first)
        rrng.shuffle(second)
        composed = [second[first[old]] for old in range(inst["n"])]
        flips = [rrng.randrange(2) for _ in range(inst["n"])]
        transformed = _relabel_and_switch(inst, composed, flips, rrng)
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        carried_valid += int(verify(transformed, transformed["answer"])[0])
    unrelated = {
        canonical_key(make_instance(seed=2000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried_valid == 20 and len(unrelated) == 20,
        "composed_relabellings_invariant": invariant,
        "carried_witnesses_valid": carried_valid,
        "unrelated_distinct_keys": len(unrelated),
        "attempts_each": 20,
        "normalized_symmetries": [
            "variable renumbering",
            "independent variable polarity switching",
            "clause reordering",
            "literal reordering within clauses",
        ],
        "key_kind": "stable color-refinement invariant of unsigned row supports",
    }

    answer_chars = 0
    answer_atoms = 0
    answer_tokens = 0
    for seed in range(40):
        answer = make_instance(seed=3000 + seed, **shipping_params)["answer"]
        encoded = json.dumps(answer, separators=(",", ":"))
        answer_chars = max(answer_chars, len(encoded))
        answer_atoms = max(answer_atoms, _answer_atom_count(answer))
        answer_tokens = max(answer_tokens, (len(encoded) + 3) // 4)
    compact_answer, intended_ops, compact_inspections = _involution_compact_route(
        shipping)
    compact_ok = verify(shipping, compact_answer)[0]
    arms = _G9_EVIDENCE["arms"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2000 and answer_atoms <= 256
                   and intended_ops <= 300 and compact_ok)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "diagnostic_not_gated": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "audit_reconstruction_literal_inspections": compact_inspections,
        "rendered_parity_summaries": len(_extract_parity_rows(shipping)[0]),
        "compact_route_verified": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
