"""Verified Track-B 3-SAT witness generator for arXiv:0906.1849.

The paper studies randomized algorithms for finding satisfying assignments of
3-CNF formulae and uses 3-variable XOR formulae as a tight example in Section
1 and Theorem 3.1.  Here the XOR blocks are coupled by an invertible binary
operator A with A^2 = I.  A satisfying assignment is sampled first, its right
hand side is evaluated, and every parity equation is expanded into four
ordinary 3-CNF clauses.  The generator never solves the formula it creates.
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
except ImportError:                 # pragma: no cover - fallback is intentional
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "3-CNF formula with signed Boolean literals",
        "Boolean satisfying assignment",
    ],
    "verification_operations": [
        "Boolean literal evaluation",
        "three-way disjunction",
        "conjunction over clauses",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Four clauses on one variable triple encode a parity row, and the "
        "coupled row operator is an involution, so applying it twice recovers "
        "the assignment without general SAT search."
    ),
    "hardness_basis": (
        "Track B: Section 1 Algorithm PPZ and Theorem 3.2 give exponential "
        "general 3-SAT routes (s=1 and shipping T_av=12 give the "
        "poly(n)*1.5875^n branch), while XOR extraction followed by GF(2) Gaussian "
        "elimination solves this distribution in expected O(M+n^3); at the hard "
        "shipping preset it solved 8/8 in 0.004501 seconds maximum with "
        "420,554 counted scalar operations mean (454,114 maximum), whereas "
        "recognizing the involution leaves exactly 160 binary XORs after 3,840 "
        "literal inspections for structure extraction."
    ),
    "max_answer_tokens": 41,
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
        "Exactly n Boolean bits [b_1,...,b_n] in public variable order; each "
        "entry is the JSON integer 0 or 1, repetitions are allowed."
    ),
    "bounds": {
        "length": "exactly n",
        "alphabet": [0, 1],
        "maximum_shipping_length": 80,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "decoy_rows": 0},
    "easy": {"n": 24, "decoy_rows": 24},
    "medium": {"n": 48, "decoy_rows": 96},
    "hard": {"n": 80, "decoy_rows": 240},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: Four clauses sharing a variable triple encode parity rows whose coefficient operator is an involution over GF(2)."
)
PLACEBO_HINT: str = (
    "Hint: Exact Boolean assignments require careful attention to every literal sign and variable index in the displayed formula."
)

# Replaced with transcript-derived values after the three harness runs.  These
# diagnostics are deliberately not part of G9's pass condition.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "unavailable: quota exhausted after the bare run",
}

NOTES = r"""
Paper definition. Section 1 defines a 3-CNF formula as a conjunction of clauses,
each containing at most three signed Boolean literals, and asks for a satisfying
assignment. It also identifies the easy boundary: 2-SAT is solvable in linear
time. Algorithms 1--3 give PPZ, DEL, and DEL--PPZ. Theorem 3.2 makes the
mechanical route explicit: DEL--PPZ is a one-sided randomized algorithm with an
expected exponential bound depending on the solution count s and the average
critical-clause parameter T_av.

Step-0 discrimination. The prior-triage suggestion of independently sampling
clauses satisfied by a planted assignment was not used: it provides no
distributional hardness theorem and leaves literal-frequency signals. Nor is
the paper's disjoint XOR example used verbatim. Section 1 and Theorem 3.1 call
that example tight for PPZ/DEL--PPZ, but its independent triples are separable
by hand. This module instead makes an honest Track-B family. Its native object
is still exactly a 3-CNF formula of the kind the paper studies, and its four-
clause parity blocks are the paper's displayed XOR objects, but a polynomial
distribution-specific reference algorithm exists and is reported.

Construction. For n=2m, choose one random directed m-cycle p and define a binary
matrix A by rows
  (Ax)_i     = x_i xor x_{p(i)} xor x_{m+p(i)},
  (Ax)_{m+i} = x_{m+i} xor x_{p(i)} xor x_{m+p(i)}.
Writing A=I+N, N has two identical block rows and N^2=0 over GF(2), hence A^2=I.
The generator first samples one opposite bit-pair per hidden index, evaluates
r=Ax, randomly relabels variables, and expands each equation into the four
3-clauses that forbid assignments of the wrong parity. Decoy parity rows use the
same four-clause representation and are sampled around the same planted
assignment. Their variable triples form a linear 3-uniform packing and avoid
all variable pairs used by the core. Thus no single row is format-distinguishable
as plant or decoy, while pair co-degree two still identifies the involutive core.
The certificate is carried through the relabelling; no SAT or linear solver is
called during generation.

Reference algorithm and compact route. Grouping clauses by their unsigned
variable triple exposes all four-clause parity rows. Exact Gaussian elimination
over GF(2) is O(n^3), always succeeds, and is reported under reference_algorithm
as Track B requires. The compact route, also implemented and verified below,
notices A^2=I and evaluates x=Ar with two XORs per output bit. At the shipping
preset it still has to inspect every literal occurrence to extract and group the
rows; that bookkeeping is disclosed separately from the 160 exact arithmetic
operations governed by G9(c). The public clause order, literal order, variable
labels, cycle, planted pair orientations, and balanced decoy groups are
independently randomized, so recognizing that operator is the task rather than
copying a visible recurrence.

Paper parameter regime. Every three-variable parity row has three critical
clauses under its satisfying assignment. Thus the hard preset has 960 critical
clauses and T_av=960/80=12 with s=1. It is well outside the paper's improved
DEL regime; Theorem 3.2 therefore selects its poly(n)*1.5875^n branch for the
paper's general-purpose route. This is an algorithmic upper bound, not a Track-A
distributional lower bound, and the polynomial XOR algorithm remains the honest
reference method for this generated distribution.

Attacks. Literal majority receives exactly tied signs, and an occurrence-median
classifier tests the remaining per-variable degree variation. Public-order
alternation ignores the hidden relabelling. Greedy clause repair is budgeted and
checked. The stronger restart attack first recovers the opposite-bit variable
pairs and samples only their 2^(n/2) possible orientations. A label-based pair
orientation and the in-context parity-RHS vote likewise use visible structure
without applying the involution. All are re-run over eight shipping seeds. The
successful XOR/Gaussian route is disclosed separately rather than misreported
as a failed attack.

Canonicalization. The cheap key quotients variable renumbering, input ordering,
exchange of the members of every recovered pair, pairwise literal
complementation, and rotation of the recovered directed cycle. It retains the
cycle-level decoy-row hypergraph. Full signed-CNF isomorphism is intentionally
not solved; the resulting invariant is coarser, and its 20-seed distinctness
test guards against practical over-collapsing.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _row_support(n, successor, row):
    """The three natural (pre-relabel) columns in one row of A."""
    half = n // 2
    if row < half:
        i = row
        return (i, successor[i], half + successor[i])
    i = row - half
    return (half + i, successor[i], half + successor[i])


def _parity_clauses(triple, rhs):
    """Four clauses whose conjunction says xor(triple) == rhs."""
    clauses = []
    for bad in itertools.product((0, 1), repeat=3):
        if (bad[0] ^ bad[1] ^ bad[2]) == rhs:
            continue
        # This clause is false exactly at `bad`.
        clauses.append([
            (v + 1) if bit == 0 else -(v + 1)
            for v, bit in zip(triple, bad)
        ])
    return clauses


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a coupled-XOR 3-CNF and carry its assignment.

    The satisfying assignment exists before any clause is made.  The identity
    A^2=I proves the n parity rows are independent, so the core has exactly one
    solution.  Decoys are then chosen to be satisfied by that solution.
    """
    decoy_rows = params.pop("decoy_rows", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    if (isinstance(decoy_rows, bool) or not isinstance(decoy_rows, int)
            or decoy_rows < 0):
        raise ValueError("decoy_rows must be a nonnegative integer")

    half = n // 2
    # A conservative packing bound keeps rejection sampling far from the dense
    # regime.  Every decoy consumes three previously unused variable pairs.
    max_decoys = n * (n - 6) // 12
    if decoy_rows > max_decoys:
        raise ValueError("too many decoy rows for the linear-triple packing")
    rng = random.Random(seed)

    cycle = list(range(half))
    rng.shuffle(cycle)
    successor = [0] * half
    for i, here in enumerate(cycle):
        successor[here] = cycle[(i + 1) % half]

    # One 0 and one 1 in every hidden pair.  This makes each pair's RHS bits
    # distinct too, which gives the canonicalizer an intrinsic local orientation.
    natural_answer = [0] * n
    for i in range(half):
        bit = rng.randrange(2)
        natural_answer[i] = bit
        natural_answer[half + i] = bit ^ 1

    rhs = []
    supports = []
    for row in range(n):
        support = _row_support(n, successor, row)
        supports.append(support)
        rhs.append(natural_answer[support[0]]
                   ^ natural_answer[support[1]]
                   ^ natural_answer[support[2]])

    old_to_public = list(range(n))
    rng.shuffle(old_to_public)
    public_answer = [0] * n
    for old, new in enumerate(old_to_public):
        public_answer[new] = natural_answer[old]

    clauses = []
    core_triples = set()
    for support, bit in zip(supports, rhs):
        triple = tuple(old_to_public[v] for v in support)
        core_triples.add(tuple(sorted(triple)))
        block = _parity_clauses(triple, bit)
        for clause in block:
            rng.shuffle(clause)
        clauses.extend(block)

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
        parity = public_answer[triple[0]] ^ public_answer[triple[1]] \
            ^ public_answer[triple[2]]
        block = _parity_clauses(triple, parity)
        for clause in block:
            rng.shuffle(clause)
        clauses.extend(block)
        made += 1

    rng.shuffle(clauses)
    return {
        "n": n,
        "clauses": clauses,
        "decoy_rows": decoy_rows,
        "answer": public_answer,
    }


def render(inst) -> str:
    """Render a complete, unambiguous 3-SAT problem and optional hint."""
    n = inst["n"]
    lines = [
        "Find a satisfying assignment for the following 3-CNF formula.",
        "",
        "There are Boolean variables x1 through x%d. A positive signed integer j"
        % n,
        "means the literal xj; a negative signed integer -j means NOT xj.",
        "Each displayed line is one clause: the OR of its three literals. The",
        "whole formula is the AND of every clause. Variable indices are 1-based.",
        "Every answer entry must be exactly 0 (false) or 1 (true).",
        "",
        "n = %d; number of clauses = %d" % (n, len(inst["clauses"])),
        "Clauses:",
    ]
    for i, clause in enumerate(inst["clauses"], 1):
        lines.append("C%04d: %s" % (i, " ".join("%+d" % x for x in clause)))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list",
        "of exactly %d bits in the order [x1,x2,...,x%d]." % (n, n),
        "Example format: <answer>[0,1,0,1]</answer>",
        "The example only illustrates syntax; it does not have the required length.",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Parse a JSON bit list from tagged output; never raise on malformed text."""
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
    if not isinstance(value, list):
        return None
    return value


def verify(inst, answer) -> tuple[bool, str]:
    """Check a candidate directly against the public clauses, never the plant."""
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
    for ci, clause in enumerate(inst["clauses"], 1):
        satisfied = False
        for lit in clause:
            value = answer[abs(lit) - 1]
            if (lit > 0 and value == 1) or (lit < 0 and value == 0):
                satisfied = True
                break
        if not satisfied:
            return False, "clause %d is unsatisfied" % ci
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the explicit language of all n-bit assignments."""
    return [rng.randrange(2) for _ in range(inst["n"])]


def search_space(inst) -> int | None:
    """There are exactly 2^n syntactically admissible Boolean assignments."""
    return 1 << inst["n"]


def enumerate_all(inst) -> int | None:
    """Brute-force exact solution count only when at most 2^20 candidates."""
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for mask in range(1 << n):
        candidate = [(mask >> i) & 1 for i in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def _clause_bad_tuple(clause):
    """Return (sorted variable triple, false tuple in that sorted order)."""
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
    """Extract exact four-clause XOR blocks without consulting the answer."""
    groups = defaultdict(set)
    inspections = 0
    for clause in inst["clauses"]:
        parsed = _clause_bad_tuple(clause)
        inspections += len(clause)
        if parsed is None:
            continue
        triple, bad = parsed
        groups[triple].add(bad)
    rows = []
    for triple, bads in groups.items():
        if len(bads) != 4:
            continue
        parities = {a ^ b ^ c for a, b, c in bads}
        if len(parities) != 1:
            continue
        bad_parity = next(iter(parities))
        rows.append((triple, bad_parity ^ 1))
    return rows, inspections


def _gaussian_reference(inst):
    """Solve extracted parity rows by exact GF(2) RREF; return answer and ops."""
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
        for r in range(rank, len(packed)):
            operations += 1
            if (packed[r] >> col) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        packed[rank], packed[pivot] = packed[pivot], packed[rank]
        for r in range(len(packed)):
            if r == rank:
                continue
            operations += 1
            if (packed[r] >> col) & 1:
                packed[r] ^= packed[rank]
                operations += n + 1   # scalar GF(2) XORs represented by this word XOR
        pivot_cols.append(col)
        rank += 1
        if rank == len(packed):
            break
    if rank < n:
        return None, operations
    answer = [0] * n
    for row_index, col in enumerate(pivot_cols):
        answer[col] = (packed[row_index] >> n) & 1
    return answer, operations


def _core_coordinates(inst):
    """Recover intrinsic pair/cycle coordinates used only for canonicalization."""
    rows, _ = _extract_parity_rows(inst)
    if len(rows) != inst["n"] + inst.get("decoy_rows", 0):
        raise ValueError("instance does not contain the expected parity rows")
    pair_counts = Counter()
    for triple, _ in rows:
        for a, b in itertools.combinations(triple, 2):
            pair_counts[tuple(sorted((a, b)))] += 1
    pairs = sorted(pair for pair, count in pair_counts.items() if count == 2)
    n = inst["n"]
    if len(pairs) != n // 2 or len({v for pair in pairs for v in pair}) != n:
        raise ValueError("parity core does not induce a perfect variable pairing")
    pair_of = {}
    for pid, pair in enumerate(pairs):
        for v in pair:
            pair_of[v] = pid

    # A core destination pair occurs in two rows.  The linear packing makes
    # every pair belonging to a decoy occur once, so only core rows contain one
    # of the distinguished pairs as a two-variable subset.
    distinguished = set(pairs)
    core_rows = [
        (triple, rhs) for triple, rhs in rows
        if any(tuple(sorted(pair)) in distinguished
               for pair in itertools.combinations(triple, 2))
    ]
    if len(core_rows) != n:
        raise ValueError("pair co-degree did not isolate the expected core")

    successor = {}
    rhs_by_singleton = {}
    for triple, rhs in core_rows:
        grouped = defaultdict(list)
        for v in triple:
            grouped[pair_of[v]].append(v)
        singles = [pid for pid, vs in grouped.items() if len(vs) == 1]
        doubles = [pid for pid, vs in grouped.items() if len(vs) == 2]
        if len(singles) != 1 or len(doubles) != 1:
            raise ValueError("malformed pair incidence")
        src, dst = singles[0], doubles[0]
        singleton = grouped[src][0]
        if src in successor and successor[src] != dst:
            raise ValueError("inconsistent core successor")
        successor[src] = dst
        rhs_by_singleton[singleton] = rhs

    side = {}
    for pair in pairs:
        bits = sorted((rhs_by_singleton[pair[0]], rhs_by_singleton[pair[1]]))
        if bits != [0, 1]:
            raise ValueError("pair lacks its intrinsic 0/1 orientation")
        for v in pair:
            side[v] = rhs_by_singleton[v]
    return pairs, pair_of, successor, side


def _involution_compact_route(inst):
    """Recover the unique assignment using A^2=I, not elimination.

    ``_core_coordinates`` identifies the public variable corresponding to every
    parity row and the successor pair used by that row.  Its ``side`` output is
    therefore the public right-hand-side vector r.  Since A is its own inverse,
    x_v = r_v xor r_a xor r_b, where (a,b) is the successor pair.  Only the two
    XORs per output bit count as exact arithmetic for G9(c); literal inspection
    needed to discover the repeated triples is returned separately.
    """
    pairs, pair_of, successor, rhs = _core_coordinates(inst)
    answer = [0] * inst["n"]
    for var in range(inst["n"]):
        a, b = pairs[successor[pair_of[var]]]
        answer[var] = rhs[var] ^ rhs[a] ^ rhs[b]
    literal_inspections = sum(len(clause) for clause in inst["clauses"])
    return answer, 2 * inst["n"], literal_inspections


def canonical_key(inst) -> str:
    """Return a cheap invariant of the signed-CNF isomorphism class.

    The generated family has two independent presentation symmetries in every
    recovered variable pair: its two variable names may be exchanged, and both
    variables may be complemented.  Clause signs and the choice of a member of
    a pair therefore are not intrinsic.  We quotient them out and retain the
    directed pair cycle plus the multiset of parity-row incidences on that
    cycle.  This is deliberately coarser than full signed-CNF isomorphism, but
    it covers every presentation symmetry used by the generator and remains a
    strong diversity invariant because the decoy-row hypergraph is retained.
    """
    pairs, pair_of, successor, _side = _core_coordinates(inst)
    rows, _ = _extract_parity_rows(inst)
    half = len(pairs)
    candidates = []
    for start in range(half):
        order = []
        cur = start
        seen = set()
        while cur not in seen:
            seen.add(cur)
            order.append(cur)
            cur = successor[cur]
        if len(order) != half or cur != start:
            raise ValueError("core successor is not one directed cycle")
        position = {pid: i for i, pid in enumerate(order)}
        normalized_rows = []
        for triple, _rhs in rows:
            normalized_rows.append(tuple(sorted(
                position[pair_of[var]] for var in triple
            )))
        normalized_rows.sort()
        candidates.append(normalized_rows)
    canonical = min(candidates)
    payload = json.dumps(canonical, separators=(",", ":"))
    return "xor-involution-v2:" + hashlib.sha256(payload.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase balanced decoy crowding first, keeping the answer length fixed."""
    current = dict(params)
    current.pop("_preset", None)
    n = current.get("n")
    decoys = current.get("decoy_rows", 0)
    if not isinstance(n, int) or n < 6 or n % 2:
        return None
    limit = n * (n - 6) // 12
    harder = min(limit, decoys + n)
    if harder > decoys:
        return {"n": n, "decoy_rows": harder}
    # The fixed-length crowding axis is genuinely exhausted only after every
    # non-core triple has been used.  Increase n while the certificate and the
    # 2n-XOR intended route remain comfortably within their caps.
    if n < 150:
        next_n = min(150, n + 8)
        return {"n": next_n, "decoy_rows": decoys}
    return "cap_bound"


def _attack_literal_majority(inst):
    score = [0] * inst["n"]
    for clause in inst["clauses"]:
        for lit in clause:
            score[abs(lit) - 1] += 1 if lit > 0 else -1
    return [1 if value > 0 else 0 for value in score]


def _attack_public_alternation(inst):
    return [i & 1 for i in range(inst["n"])]


def _attack_occurrence_median(inst):
    counts = [0] * inst["n"]
    for clause in inst["clauses"]:
        for lit in clause:
            counts[abs(lit) - 1] += 1
    median = sorted(counts)[len(counts) // 2]
    return [int(count > median) for count in counts]


def _attack_pair_orientation_by_label(inst):
    """Use the deducible opposite-pair rule but guess every orientation."""
    pairs, _, _, _ = _core_coordinates(inst)
    candidate = [0] * inst["n"]
    for a, b in pairs:
        candidate[min(a, b)] = 0
        candidate[max(a, b)] = 1
    return candidate


def _random_pair_candidate(inst, rng):
    """Sample the 2^(n/2) assignments obeying the recovered pair constraint."""
    pairs, _, _, _ = _core_coordinates(inst)
    candidate = [0] * inst["n"]
    for a, b in pairs:
        bit = rng.randrange(2)
        candidate[a] = bit
        candidate[b] = bit ^ 1
    return candidate


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
    for _ in range(2 * inst["n"]):
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


def _attack_rhs_vote(inst):
    rows, _ = _extract_parity_rows(inst)
    votes = [[] for _ in range(inst["n"])]
    for triple, rhs in rows:
        for var in triple:
            votes[var].append(rhs)
    return [int(sum(vs) * 2 > len(vs)) if vs else 0 for vs in votes]


def _relabel_instance(inst, old_to_new, rng):
    """Carry a witness through a genuine variable relabelling and reorder input."""
    n = inst["n"]
    if sorted(old_to_new) != list(range(n)):
        raise ValueError("old_to_new must be a permutation")
    clauses = []
    for clause in inst["clauses"]:
        moved = []
        for lit in clause:
            new = old_to_new[abs(lit) - 1] + 1
            moved.append(new if lit > 0 else -new)
        rng.shuffle(moved)
        clauses.append(moved)
    rng.shuffle(clauses)
    carried = [0] * n
    for old, new in enumerate(old_to_new):
        carried[new] = inst["answer"][old]
    return {
        "n": n,
        "clauses": clauses,
        "decoy_rows": inst.get("decoy_rows", 0),
        "answer": carried,
    }


def _complement_hidden_pairs(inst, pair_ids):
    """Complement both variables of selected recovered pairs.

    This is a genuine signed-variable relabelling: every affected literal sign
    and answer bit is complemented together.  Selecting whole pairs keeps the
    transformed object inside this generator's opposite-pair family.
    """
    pairs, _, _, _ = _core_coordinates(inst)
    chosen = {v for pid in pair_ids for v in pairs[pid]}
    clauses = [
        [(-lit if abs(lit) - 1 in chosen else lit) for lit in clause]
        for clause in inst["clauses"]
    ]
    carried = [
        (bit ^ 1) if var in chosen else bit
        for var, bit in enumerate(inst["answer"])
    ]
    return {
        "n": inst["n"],
        "clauses": clauses,
        "decoy_rows": inst.get("decoy_rows", 0),
        "answer": carried,
    }


def _answer_atom_count(answer):
    return len(answer) if isinstance(answer, list) else 0


def _critical_clause_count(inst, answer):
    """Count clauses with exactly one true literal, as defined in Section 1."""
    count = 0
    for clause in inst["clauses"]:
        true_literals = sum(
            (lit > 0 and answer[abs(lit) - 1] == 1)
            or (lit < 0 and answer[abs(lit) - 1] == 0)
            for lit in clause
        )
        count += int(true_literals == 1)
    return count


def selftest() -> dict:
    report = {}

    # G1: all presets and several independent seeds.
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
        "generation_route": "inverse generation plus A^2=I theorem-backed uniqueness",
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
    distinct = {result["reason"] for result in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(x["rejected"] for x in corruption_results.values())
                 and len(distinct) == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": len(distinct),
    }

    wire = json.dumps(base, separators=(",", ":"))
    realistic = (
        "The parity blocks determine the assignment.\n"
        "<answer>```json\n" + wire + "\n```</answer>\n"
        "I checked every clause."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == base,
        "parsed_equals_answer": parsed == base,
        "json_native": json.loads(json.dumps(base)) == base,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # Shared structure-aware uniform sampling for G4 and shipping G5 density.
    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping,
                                 random_candidate(shipping, guess_rng))[0])
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
    critical_clauses = _critical_clause_count(shipping, base)
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
        "shipping_critical_clauses": critical_clauses,
        "shipping_T_av": critical_clauses / shipping["n"],
        "paper_DEL_PPZ_bound_at_s_1": "poly(n) * 1.5875^n",
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_algorithm": "XOR-block extraction plus exact GF(2) Gaussian elimination",
        "baseline_wall_clock_seconds": round(reference_sec, 6),
        "baseline_scalar_operations": reference_ops,
        "baseline_verified": reference_ok,
        "compact_route_exact_operations": compact_ops,
        "compact_route_literal_inspections": compact_inspections,
        "compact_route_verified": compact_ok,
    }

    attacks = {
        "outlier_literal_majority": {"successes": 0, "attempts": 8},
        "outlier_occurrence_median": {"successes": 0, "attempts": 8},
        "public_order_alternation": {"successes": 0, "attempts": 8},
        "pair_orientation_by_label": {"successes": 0, "attempts": 8},
        "greedy_clause_repair_2n": {"successes": 0, "attempts": 8},
        "pair_aware_random_restart_512": {"successes": 0, "attempts": 8},
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
            "public_order_alternation": _attack_public_alternation(inst),
            "pair_orientation_by_label": _attack_pair_orientation_by_label(inst),
            "greedy_clause_repair_2n": _attack_greedy_repair(inst),
            "xor_rhs_local_vote": _attack_rhs_vote(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rrng = random.Random(seed ^ 0x5A17)
        restart_hit = False
        for _ in range(512):
            if verify(inst, _random_pair_candidate(inst, rrng))[0]:
                restart_hit = True
                break
        attacks["pair_aware_random_restart_512"]["successes"] += int(restart_hit)
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
            "name": "XOR-block extraction plus exact GF(2) Gaussian elimination",
            "complexity": "expected O(M + n^3) exact binary operations",
            "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_operations) / len(reference_operations)),
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
        "shipping_clause_count": len(shipping["clauses"]),
        "doubled_clause_count": len(doubled["clauses"]),
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": shipping["n"],
        "doubled_search_space_bits": doubled["n"],
    }

    invariant = 0
    signed_invariant = 0
    carried_valid = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **shipping_params)
        rrng = random.Random(9000 + seed)
        pairs, _, _, _ = _core_coordinates(inst)
        complemented = _complement_hidden_pairs(
            inst, [pid for pid in range(len(pairs)) if rrng.randrange(2)])
        first = list(range(inst["n"]))
        second = list(range(inst["n"]))
        rrng.shuffle(first)
        rrng.shuffle(second)
        composed = [second[first[old]] for old in range(inst["n"])]
        transformed = _relabel_instance(complemented, composed, rrng)
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        signed_invariant += int(
            canonical_key(inst) == canonical_key(complemented))
        carried_valid += int(verify(transformed, transformed["answer"])[0])
    unrelated = {
        canonical_key(make_instance(seed=2000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariant == 20 and signed_invariant == 20
                 and carried_valid == 20 and len(unrelated) == 20),
        "composed_relabellings_invariant": invariant,
        "paired_literal_complementations_invariant": signed_invariant,
        "carried_witnesses_valid": carried_valid,
        "unrelated_distinct_keys": len(unrelated),
        "attempts_each": 20,
        "normalized_symmetries": [
            "variable renumbering",
            "clause reordering",
            "literal reordering within clauses",
            "exchange of the two variables in any recovered pair",
            "simultaneous literal complementation within recovered pairs",
            "rotation of the hidden directed pair cycle",
        ],
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
        "compact_route_literal_inspections": compact_inspections,
        "compact_route_verified": compact_ok,
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
