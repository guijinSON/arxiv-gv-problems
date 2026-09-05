"""Verified problem generator for arXiv:2604.23226.

The paper proves NP-hardness of finding any nontrivial temporally connected
induced subgraph by an explicit reduction from Multicolored Clique (MCC).  This
module inverse-generates a uniquely satisfiable system of ternary parity rows,
turns its local satisfying assignments into an MCC compatibility graph, and
then uses exactly the happy directed temporal-graph construction of Section 2.

The submitted certificate is a succinct description of the paper's witness:
the bits select one local vertex in every MCC color class, and the temporal
subgraph is that clique together with the full connector gadget.  Generation
never solves an instance it has built.
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
except ImportError:                 # pragma: no cover - graceful stdlib fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "happy directed temporal graph of lifetime 11 specified by exact arc rules",
        "temporally connected induced vertex subset",
    ],
    "verification_operations": [
        "exact parity evaluation",
        "exact compatibility check for every selected vertex pair",
        "symbolic validation of directed temporal paths at integer time labels",
        "explicit all-pairs temporal closure on demo instances",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Theorem 2.1 (MCC to happy directed Nontrivial TC "
        "Subgraph at lifetime 11)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Repeated variable pairs in the MCC color classes expose an involutive "
        "parity operator; without recognizing it, a solver must perform generic "
        "temporal-subgraph, clique, or linear-system search."
    ),
    "hardness_basis": (
        "Track B: Section 2, Theorem 2.1 makes general Nontrivial TC Subgraph "
        "NP-hard even for happy directed graphs of lifetime 11, but this generated "
        "distribution is efficiently solved by parity-row extraction plus exact "
        "GF(2) Gaussian elimination in O(R+n^3); at the shipping preset it used "
        "382,679 counted scalar operations and about 0.0014 seconds on the fixed G5 "
        "instance (385,329 operations maximum over the eight G6 seeds), while "
        "recognizing the involution gives the n-bit witness in exactly 2n=160 XORs."
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
        "Exactly n JSON bits in public variable order, restricted to the "
        "structure-aware language in which the two variables in every repeated "
        "pair have opposite values; there are 2^(n/2) such candidates."
    ),
    "bounds": {
        "length": "exactly n",
        "alphabet": [0, 1],
        "recovered_pair_rule": "exactly one 1 in each of n/2 pairs",
        "maximum_shipping_length": 80,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "decoy_rows": 0},
    "easy": {"n": 24, "decoy_rows": 12},
    "medium": {"n": 48, "decoy_rows": 72},
    "hard": {"n": 80, "decoy_rows": 200},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: Repeated variable pairs among the parity colors form the rows of an involutive linear operator over GF(2)."
)
PLACEBO_HINT: str = (
    "Hint: Careful bookkeeping of vertex types and time labels is useful in this temporal connectivity problem."
)

# Replaced after the script-owned three-arm runs.  These values are diagnostic;
# only G9(c)'s answer and operation caps gate the family.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "error_calls": {"bare": 4, "hinted": 4, "placebo": 4},
    "hinted_verdict": "unavailable: OpenRouter key total limit exceeded",
}

NOTES = r"""
Definition and exact setting. Section 1 defines a temporal path as a path whose
edge labels are nondecreasing, a temporal graph as TC when every ordered vertex
pair is joined by such a path, and a closed temporal component as a vertex-
induced TC subgraph. Nontrivial means size greater than one in the directed
case. A graph is happy when every arc has one label and no in-arc and out-arc at
the same vertex share a label. Section 2, Theorem 2.1 proves NP-hardness for
happy directed temporal graphs with lifetime exactly 11.

Easy regimes found at Step 0. Open components are hereditary, so existence of a
nontrivial open component is polynomial-time checkable. The introduction also
records FPT algorithms for combinations such as k+L, and says that non-strict
undirected Nontrivial TC Subgraph is FPT in lifetime L. Those cases are avoided:
the module uses closed components, directed arcs, and exactly the lifetime-11
construction of Theorem 2.1. The paper also gives an ETH lower bound of
2^{o(N)} for its directed reduction, but that is a worst-case result and is not
misreported as a distributional lower bound here.

Generation and certificate. For n=2m, a random directed m-cycle p defines A by
  (Ax)_i     = x_i     XOR x_p(i) XOR x_(m+p(i)),
  (Ax)_(m+i) = x_(m+i) XOR x_p(i) XOR x_(m+p(i)).
Writing A=I+N gives N^2=0 over GF(2), hence A^2=I. The generator samples x first,
computes r=Ax, relabels variables, and adds parity decoys satisfied by x. Each
row becomes one MCC color class whose four vertices are the row's satisfying
local assignments; vertices in different classes are adjacent exactly when
their shared-variable values agree. If the number of row classes is even, the
paper's own footnoted universal singleton class makes k odd. Theorem 2.1 then
maps this MCC graph to the displayed lifetime-11 temporal graph. The answer x
selects one vertex per class, and the TC witness is that clique together with
every connector vertex. Thus the witness is carried through two exact maps and
is never discovered by search.

Step-0 certificate discrimination and Track B. A general certificate can be
found mechanically by extracting the printed parity rows and running exact
GF(2) Gaussian elimination in O(R+n^3). That succeeds and is reported as the
reference algorithm, not hidden among failing attacks. The shorter intended
route recovers the repeated pairs, recognizes A^2=I, and evaluates x=Ar using
two XORs per output bit. At shipping n=80 this is 160 exact operations after
the structural recognition; input inspection is reported separately. This gap,
not a Track-A average-case hardness assertion, is the claimed difficulty.

Verification. verify() never reads inst['answer']. It evaluates each parity row,
expands the bit string to one local MCC vertex per color, checks compatibility
for every selected pair, and checks the hypotheses of the paper's explicit
temporal-path template. The demo additionally reconstructs every vertex and arc
of the induced temporal graph and recomputes strict all-pairs temporal closure;
because the graph is happy, strict and non-strict closure coincide.

Attack hardening. Plants and parity decoys use the same row distribution and
the local-option listing is independently shuffled. Variable labels, row order,
triple order, cycle, signs/RHS values, and option order are randomized. The
panel tests occurrence and RHS outliers, public-order guesses, first-local-
vertex voting, a pair-label orientation, greedy repair, and pair-aware random
restarts. The successful Gaussian route is disclosed separately.

Canonicalization. The key recovers the repeated variable pairs, quotients
variable renaming, pair-member exchange, paired bit complementation, row/triple/
option order, and rotation of the hidden directed pair cycle, then retains the
decoy-row hypergraph on cycle positions. It is deliberately a strong cheap
invariant rather than a solution of full temporal-graph isomorphism.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _row_support(n, successor, row):
    half = n // 2
    if row < half:
        i = row
        return (i, successor[i], half + successor[i])
    i = row - half
    return (half + i, successor[i], half + successor[i])


def _code_bits(code):
    return ((code >> 2) & 1, (code >> 1) & 1, code & 1)


def _bits_code(bits):
    return (bits[0] << 2) | (bits[1] << 1) | bits[2]


def _allowed_codes(rhs):
    return [code for code in range(8)
            if (_code_bits(code)[0] ^ _code_bits(code)[1]
                ^ _code_bits(code)[2]) == rhs]


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate parity rows and carry their MCC/temporal witness."""
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
    for i, here in enumerate(cycle):
        successor[here] = cycle[(i + 1) % half]

    natural_answer = [0] * n
    for i in range(half):
        bit = rng.randrange(2)
        natural_answer[i] = bit
        natural_answer[half + i] = bit ^ 1

    old_to_public = list(range(n))
    rng.shuffle(old_to_public)
    public_answer = [0] * n
    for old, new in enumerate(old_to_public):
        public_answer[new] = natural_answer[old]

    raw_rows = []
    used_triples = set()
    used_pairs = set()
    for row_index in range(n):
        support = tuple(old_to_public[v]
                        for v in _row_support(n, successor, row_index))
        rhs = 0
        for var in support:
            rhs ^= public_answer[var]
        triple_key = tuple(sorted(support))
        used_triples.add(triple_key)
        used_pairs.update(tuple(sorted(pair))
                          for pair in itertools.combinations(support, 2))
        raw_rows.append((list(support), rhs))

    made = 0
    while made < decoy_rows:
        support = tuple(sorted(rng.sample(range(n), 3)))
        pairs = {tuple(sorted(pair))
                 for pair in itertools.combinations(support, 2)}
        if support in used_triples or not pairs.isdisjoint(used_pairs):
            continue
        used_triples.add(support)
        used_pairs.update(pairs)
        rhs = public_answer[support[0]] ^ public_answer[support[1]] \
            ^ public_answer[support[2]]
        raw_rows.append((list(support), rhs))
        made += 1

    rows = []
    for variables, rhs in raw_rows:
        rng.shuffle(variables)
        options = _allowed_codes(rhs)
        rng.shuffle(options)
        rows.append({"vars": variables, "rhs": rhs, "options": options})
    rng.shuffle(rows)

    return {
        "n": n,
        "rows": rows,
        "decoy_rows": decoy_rows,
        "answer": public_answer,
    }


def render(inst) -> str:
    """Render the full succinct temporal graph and the witness convention."""
    n = inst["n"]
    rows = inst["rows"]
    universal = len(rows) % 2 == 0
    k = len(rows) + int(universal)
    lines = [
        "Find a temporally connected induced subgraph in the happy directed",
        "temporal graph defined below. All definitions and all graph data are inline.",
        "",
        "A directed temporal arc (u,v,t) may be traversed from u to v at integer",
        "time t. A temporal path has nondecreasing traversal times. A vertex set",
        "is temporally connected (TC) when, inside its vertex-induced subgraph,",
        "every ordered pair of vertices is joined by a temporal path. This graph",
        "is happy: every arc has one time and no in-arc and out-arc at one vertex",
        "share a time, so allowing equal consecutive times changes no reachability.",
        "",
        "First define an auxiliary %d-color Multicolored Clique graph G." % k,
        "There are Boolean variables x1,...,x%d. Each row below is one color" % n,
        "class. If its variables are [xa,xb,xc] and RHS is r, its four local",
        "vertices are the listed 3-bit strings abc satisfying xa XOR xb XOR xc=r.",
        "Two local vertices from different row colors are adjacent in G exactly",
        "when they assign the same bit to every variable their rows share.",
        "Vertices of one color are never adjacent. Row, variable, and option order",
        "are presentation only. Variable indices are 1-based.",
        "",
        "Parity color classes:",
    ]
    for i, row in enumerate(rows, 1):
        variables = ",".join("x%d" % (v + 1) for v in row["vars"])
        options = ",".join(format(code, "03b") for code in row["options"])
        lines.append("R%03d: vars=[%s] rhs=%d vertices=[%s]"
                     % (i, variables, row["rhs"], options))
    if universal:
        lines.extend([
            "U: one additional vertex adjacent in G to every vertex of every R color.",
            "It is the final color class and makes the number of colors odd.",
        ])

    lines.extend([
        "",
        "Now define the directed temporal graph T (this is the instance to solve).",
        "Let V be all local vertices of G, including U when present. Color indices",
        "are 1,...,k in the displayed order. Besides V, T has alpha and omega;",
        "for every v in V it has out(v) and in(v); and it has four special vertices",
        "preout(omega), out(omega), in(alpha), postin(alpha). No arcs exist except",
        "those in the following exhaustive rules (a product means all such arcs):",
        "",
        "Selector arcs:",
        "  alpha -> V_1 at time 4; alpha -> V_i at time 8 for every i>1.",
        "  V_i -> omega at time 6 for odd i; omega -> V_i at time 5 for even i.",
        "  For even i: V_i -> V_(i-1) at time 7 and, when i<k,",
        "  V_i -> V_(i+1) at time 4.",
        "Connector arcs, for every v in V:",
        "  omega -> out(v), in(v) at time 10; out(v), in(v) -> alpha at time 2.",
        "Special connector arcs:",
        "  omega -> preout(omega) at 10; preout(omega) -> out(omega) at 11;",
        "  preout(omega), out(omega) -> alpha at 2;",
        "  omega -> in(alpha), postin(alpha) at 10; in(alpha) -> postin(alpha) at 1;",
        "  postin(alpha) -> alpha at 2.",
        "Validation arcs:",
        "  v -> out(v) at 3 for every v in V; omega -> out(omega) at 3;",
        "  in(v) -> v at 9 for every v in V; in(alpha) -> alpha at 9;",
        "  out(v) -> in(alpha) at 4 for every v in V;",
        "  out(omega) -> in(v) at 4 for every v in the final color V_k;",
        "  out(omega) -> in(alpha) at 4;",
        "  out(v) -> in(w) at 4 for every ordered pair v!=w with {v,w} an edge of G.",
        "The lifetime is therefore 11.",
        "",
        "Your answer is a succinct vertex-set witness: give n bits b1,...,bn.",
        "For every row color R_i, the bits select its unique listed local vertex",
        "whose three entries equal the bits on that row's variables; U is selected",
        "when present. Expand the claimed set S by adding alpha, omega, every",
        "out(v) and in(v) for every v in V, and all four special connector vertices.",
        "The bits are valid exactly when every selected row vertex exists and the",
        "expanded induced subgraph T[S] is TC. The checker expands this convention",
        "and checks exact directed temporal reachability; it does not compare with",
        "a stored answer. Repetitions are not meaningful, and order is x1 through xn.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list",
        "of exactly %d bits (each exactly 0 or 1) in order [x1,...,x%d]." % (n, n),
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


def _row_code(row, answer):
    return _bits_code(tuple(answer[v] for v in row["vars"]))


def _symbolic_tc_obligations(inst, answer):
    """Execute the path-template hypotheses in the proof of Theorem 2.1.

    A selected local vertex exists iff its row parity holds.  Pairwise agreement
    makes the selected vertices an MCC clique.  With an odd number of colors,
    the fixed arc schema then supplies every path family used in the paper's
    forward proof: C-to-C at (3,4,9), connector-to-alpha by time 2,
    alpha-to-omega by (4,6), and omega-to-connector from time 10.
    """
    selected = []
    for ri, row in enumerate(inst["rows"]):
        code = _row_code(row, answer)
        if code not in row["options"]:
            got = answer[row["vars"][0]] ^ answer[row["vars"][1]] \
                ^ answer[row["vars"][2]]
            return False, (
                "row %d has parity %d instead of %d, so its selected color "
                "vertex does not exist" % (ri + 1, got, row["rhs"])
            )
        selected.append({v: answer[v] for v in row["vars"]})

    # This is deliberately checked even though a single global bit vector makes
    # agreement automatic: it is the exact MCC-edge obligation the temporal
    # validation arcs encode.
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            common = set(selected[i]).intersection(selected[j])
            if any(selected[i][v] != selected[j][v] for v in common):
                return False, "selected vertices in colors %d and %d are nonadjacent" % (
                    i + 1, j + 1)

    k = len(inst["rows"]) + int(len(inst["rows"]) % 2 == 0)
    if k % 2 != 1:
        return False, "the temporal selector requires an odd number of colors"
    return True, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Verify the succinct TC witness without reading the planted answer."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    n = inst.get("n")
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, "assignment is missing %d bit%s" % (
            n - len(answer), "" if n - len(answer) == 1 else "s")
    if len(answer) > n:
        return False, "assignment has %d extra bit%s (possible duplicate)" % (
            len(answer) - n, "" if len(answer) - n == 1 else "s")
    for i, bit in enumerate(answer, 1):
        if isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1):
            return False, "entry %d is not a Boolean bit" % i
    return _symbolic_tc_obligations(inst, answer)


def _core_coordinates(inst):
    """Recover the repeated pairs and directed cycle from public parity rows."""
    rows = [(tuple(row["vars"]), row["rhs"]) for row in inst["rows"]]
    pair_counts = Counter()
    for triple, _rhs in rows:
        for pair in itertools.combinations(triple, 2):
            pair_counts[tuple(sorted(pair))] += 1
    pairs = sorted(pair for pair, count in pair_counts.items() if count == 2)
    n = inst["n"]
    if len(pairs) != n // 2 or len({v for pair in pairs for v in pair}) != n:
        raise ValueError("parity core does not induce a perfect variable pairing")
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
    rhs_by_singleton = {}
    for triple, rhs in core_rows:
        grouped = defaultdict(list)
        for var in triple:
            grouped[pair_of[var]].append(var)
        singles = [pid for pid, vs in grouped.items() if len(vs) == 1]
        doubles = [pid for pid, vs in grouped.items() if len(vs) == 2]
        if len(singles) != 1 or len(doubles) != 1:
            raise ValueError("malformed core-pair incidence")
        src, dst = singles[0], doubles[0]
        if src in successor and successor[src] != dst:
            raise ValueError("inconsistent core successor")
        successor[src] = dst
        rhs_by_singleton[grouped[src][0]] = rhs
    side = {}
    for pair in pairs:
        if sorted((rhs_by_singleton[pair[0]], rhs_by_singleton[pair[1]])) != [0, 1]:
            raise ValueError("a recovered pair lacks opposite RHS values")
        for var in pair:
            side[var] = rhs_by_singleton[var]
    return pairs, pair_of, successor, side


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the pair-aware 2^(n/2) certificate language."""
    pairs = inst.get("_candidate_pairs_cache")
    if pairs is None:
        pairs = _core_coordinates(inst)[0]
        inst["_candidate_pairs_cache"] = pairs
    candidate = [0] * inst["n"]
    for a, b in pairs:
        bit = rng.randrange(2)
        candidate[a] = bit
        candidate[b] = bit ^ 1
    return candidate


def search_space(inst) -> int | None:
    return 1 << (inst["n"] // 2)


def enumerate_all(inst) -> int | None:
    pairs = _core_coordinates(inst)[0]
    if len(pairs) > 20:
        return None
    count = 0
    for mask in range(1 << len(pairs)):
        candidate = [0] * inst["n"]
        for i, (a, b) in enumerate(pairs):
            candidate[a] = (mask >> i) & 1
            candidate[b] = candidate[a] ^ 1
        count += int(verify(inst, candidate)[0])
    return count


def _gaussian_reference(inst):
    """Exact GF(2) RREF on the printed rows; return answer and scalar ops."""
    n = inst["n"]
    operations = 0
    packed = []
    for row in inst["rows"]:
        mask = 0
        for col in row["vars"]:
            mask ^= 1 << col
            operations += 1
        packed.append(mask | (row["rhs"] << n))
    rank = 0
    pivots = []
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
                operations += n + 1
        pivots.append(col)
        rank += 1
        if rank == n:
            break
    if rank < n:
        return None, operations
    answer = [0] * n
    for row_index, col in enumerate(pivots):
        answer[col] = (packed[row_index] >> n) & 1
    return answer, operations


def _compact_route(inst):
    pairs, pair_of, successor, rhs = _core_coordinates(inst)
    answer = [0] * inst["n"]
    for var in range(inst["n"]):
        a, b = pairs[successor[pair_of[var]]]
        answer[var] = rhs[var] ^ rhs[a] ^ rhs[b]
    return answer, 2 * inst["n"], 3 * len(inst["rows"])


def canonical_key(inst) -> str:
    """Canonical cheap invariant under every presentation symmetry we generate."""
    pairs, pair_of, successor, _side = _core_coordinates(inst)
    half = len(pairs)
    candidates = []
    for start in range(half):
        order = []
        seen = set()
        cur = start
        while cur not in seen:
            seen.add(cur)
            order.append(cur)
            cur = successor[cur]
        if len(order) != half or cur != start:
            raise ValueError("core successor is not one directed cycle")
        position = {pid: i for i, pid in enumerate(order)}
        normalized = []
        for row in inst["rows"]:
            normalized.append(tuple(sorted(position[pair_of[v]]
                                           for v in row["vars"])))
        normalized.sort()
        candidates.append(normalized)
    payload = json.dumps(min(candidates), separators=(",", ":"))
    return "tc-xor-mcc-v1:" + hashlib.sha256(payload.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow decoy crowding first, then n while the 2n-XOR route fits G9(c)."""
    current = dict(params)
    current.pop("_preset", None)
    n = current.get("n")
    decoys = current.get("decoy_rows", 0)
    if not isinstance(n, int) or n < 6 or n % 2:
        return None
    limit = n * (n - 6) // 12
    harder_decoys = min(limit, decoys + n)
    if harder_decoys > decoys:
        return {"n": n, "decoy_rows": harder_decoys}
    if n < 150:
        next_n = min(150, n + (8 if n <= 142 else 2))
        if next_n % 2:
            next_n -= 1
        return {"n": next_n, "decoy_rows": decoys}
    return "cap_bound"


def _attack_occurrence_median(inst):
    counts = [0] * inst["n"]
    for row in inst["rows"]:
        for var in row["vars"]:
            counts[var] += 1
    median = sorted(counts)[len(counts) // 2]
    return [int(value > median) for value in counts]


def _attack_public_alternation(inst):
    return [i & 1 for i in range(inst["n"])]


def _attack_pair_orientation_by_label(inst):
    candidate = [0] * inst["n"]
    for a, b in _core_coordinates(inst)[0]:
        candidate[min(a, b)] = 0
        candidate[max(a, b)] = 1
    return candidate


def _attack_rhs_vote(inst):
    votes = [[] for _ in range(inst["n"])]
    for row in inst["rows"]:
        for var in row["vars"]:
            votes[var].append(row["rhs"])
    return [int(sum(vs) * 2 > len(vs)) if vs else 0 for vs in votes]


def _attack_first_option_vote(inst):
    votes = [[] for _ in range(inst["n"])]
    for row in inst["rows"]:
        bits = _code_bits(row["options"][0])
        for pos, var in enumerate(row["vars"]):
            votes[var].append(bits[pos])
    return [int(sum(vs) * 2 > len(vs)) if vs else 0 for vs in votes]


def _bad_rows(inst, candidate):
    return [i for i, row in enumerate(inst["rows"])
            if (_row_code(row, candidate) not in row["options"])]


def _attack_greedy_repair(inst):
    candidate = _attack_rhs_vote(inst)
    for _ in range(2 * inst["n"]):
        bad = _bad_rows(inst, candidate)
        if not bad:
            break
        row = inst["rows"][bad[0]]
        best = None
        for var in row["vars"]:
            candidate[var] ^= 1
            trial = (len(_bad_rows(inst, candidate)), var)
            candidate[var] ^= 1
            if best is None or trial < best:
                best = trial
        candidate[best[1]] ^= 1
    return candidate


def _relabel_instance(inst, old_to_new, rng):
    if sorted(old_to_new) != list(range(inst["n"])):
        raise ValueError("old_to_new must be a permutation")
    rows = []
    for source in inst["rows"]:
        row = {
            "vars": [old_to_new[v] for v in source["vars"]],
            "rhs": source["rhs"],
            "options": list(source["options"]),
        }
        rng.shuffle(row["options"])
        rows.append(row)
    rng.shuffle(rows)
    answer = [0] * inst["n"]
    for old, new in enumerate(old_to_new):
        answer[new] = inst["answer"][old]
    return {"n": inst["n"], "rows": rows,
            "decoy_rows": inst.get("decoy_rows", 0), "answer": answer}


def _complement_pairs(inst, pair_ids):
    pairs = _core_coordinates(inst)[0]
    chosen = {v for pid in pair_ids for v in pairs[pid]}
    rows = []
    for source in inst["rows"]:
        mask = 0
        flips = 0
        for pos, var in enumerate(source["vars"]):
            if var in chosen:
                mask |= 1 << (2 - pos)
                flips ^= 1
        rows.append({
            "vars": list(source["vars"]),
            "rhs": source["rhs"] ^ flips,
            "options": [code ^ mask for code in source["options"]],
        })
    answer = [(bit ^ 1) if i in chosen else bit
              for i, bit in enumerate(inst["answer"])]
    return {"n": inst["n"], "rows": rows,
            "decoy_rows": inst.get("decoy_rows", 0), "answer": answer}


def _base_vertices(inst):
    vertices = []
    for ri, row in enumerate(inst["rows"]):
        vertices.extend(("r", ri, code) for code in row["options"])
    if len(inst["rows"]) % 2 == 0:
        vertices.append(("u",))
    return vertices


def _base_class(vertex, row_count):
    return vertex[1] if vertex[0] == "r" else row_count


def _base_assignment(inst, vertex):
    if vertex[0] == "u":
        return {}
    row = inst["rows"][vertex[1]]
    return dict(zip(row["vars"], _code_bits(vertex[2])))


def _base_adjacent(inst, left, right):
    if left == right or _base_class(left, len(inst["rows"])) == _base_class(
            right, len(inst["rows"])):
        return False
    if left[0] == "u" or right[0] == "u":
        return True
    a = _base_assignment(inst, left)
    b = _base_assignment(inst, right)
    return all(a[v] == b[v] for v in set(a).intersection(b))


def _explicit_temporal_tc(inst, answer):
    """Materialize T[S] and recompute exact all-pairs temporal closure.

    Used as an independent audit on the hand-scale preset.  The batch update is
    strict temporal closure; happiness makes it equal to non-strict closure.
    """
    if not verify(inst, answer)[0]:
        return False, "certificate does not select one vertex in every color"
    base = _base_vertices(inst)
    selected = []
    for ri, row in enumerate(inst["rows"]):
        selected.append(("r", ri, _row_code(row, answer)))
    if len(inst["rows"]) % 2 == 0:
        selected.append(("u",))

    alpha = ("alpha",)
    omega = ("omega",)
    preoutw = ("preoutw",)
    outw = ("outw",)
    inalpha = ("inalpha",)
    postinalpha = ("postinalpha",)
    nodes = [alpha, omega, preoutw, outw, inalpha, postinalpha]
    nodes.extend(("out", v) for v in base)
    nodes.extend(("in", v) for v in base)
    nodes.extend(selected)
    node_id = {v: i for i, v in enumerate(nodes)}
    by_time = [[] for _ in range(12)]

    def arc(u, v, t):
        if u in node_id and v in node_id:
            by_time[t].append((node_id[u], node_id[v]))

    # Selector gadget on the one selected original vertex per class.
    for v in selected:
        ci = _base_class(v, len(inst["rows"])) + 1
        arc(alpha, v, 4 if ci == 1 else 8)
        if ci % 2:
            arc(v, omega, 6)
        else:
            arc(omega, v, 5)
    for v in selected:
        ci = _base_class(v, len(inst["rows"])) + 1
        if ci % 2 == 0:
            for w in selected:
                cj = _base_class(w, len(inst["rows"])) + 1
                if cj == ci - 1:
                    arc(v, w, 7)
                elif cj == ci + 1:
                    arc(v, w, 4)

    for v in base:
        arc(omega, ("out", v), 10)
        arc(omega, ("in", v), 10)
        arc(("out", v), alpha, 2)
        arc(("in", v), alpha, 2)
        arc(v, ("out", v), 3)
        arc(("in", v), v, 9)
        arc(("out", v), inalpha, 4)
    arc(omega, preoutw, 10)
    arc(preoutw, outw, 11)
    arc(preoutw, alpha, 2)
    arc(outw, alpha, 2)
    arc(omega, inalpha, 10)
    arc(omega, postinalpha, 10)
    arc(inalpha, postinalpha, 1)
    arc(postinalpha, alpha, 2)
    arc(omega, outw, 3)
    arc(inalpha, alpha, 9)
    final_class = len(selected) - 1
    for v in base:
        if _base_class(v, len(inst["rows"])) == final_class:
            arc(outw, ("in", v), 4)
    arc(outw, inalpha, 4)
    for i, left in enumerate(base):
        for right in base[i + 1:]:
            if _base_adjacent(inst, left, right):
                arc(("out", left), ("in", right), 4)
                arc(("out", right), ("in", left), 4)

    size = len(nodes)
    reach_into = [1 << i for i in range(size)]
    for t in range(1, 12):
        before = list(reach_into)
        additions = [0] * size
        for u, v in by_time[t]:
            additions[v] |= before[u]
        for v in range(size):
            reach_into[v] |= additions[v]
    full = (1 << size) - 1
    for target, sources in enumerate(reach_into):
        if sources != full:
            missing = (full ^ (sources & full)).bit_length() - 1
            return False, "no temporal path from node %d to node %d" % (
                missing, target)
    return True, "ok"


def _answer_atom_count(answer):
    return len(answer) if isinstance(answer, list) else 0


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
        "generation_route": (
            "inverse parity generation, local-consistency MCC composition, and "
            "the certificate-preserving reduction of Theorem 2.1"
        ),
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)
    base = shipping["answer"]
    swapped = base[:]
    left = next(i for i, bit in enumerate(swapped) if bit == 0)
    right = next(i for i, bit in enumerate(swapped) if bit == 1)
    swapped[left], swapped[right] = swapped[right], swapped[left]
    corruptions = {
        "drop": base[:-1],
        "swap": swapped,
        "duplicate": base + [base[-1]],
        "empty": [],
        "out_of_range": [2] + base[1:],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    distinct = {value["reason"] for value in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in cases.values()) and len(distinct) == 5,
        "cases": cases,
        "distinct_reasons": len(distinct),
    }

    wire = json.dumps(base, separators=(",", ":"))
    realistic = (
        "The repeated pairs determine the witness.\n<answer>```json\n"
        + wire + "\n```</answer>\nI checked the temporal paths."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == base and json.loads(json.dumps(base)) == base
        and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == base,
        "json_native": json.loads(json.dumps(base)) == base,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

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
        "prior": (
            "uniform over assignments already obeying every recovered opposite-pair rule"
        ),
    }

    t0 = time.perf_counter()
    reference_answer, reference_ops = _gaussian_reference(shipping)
    reference_sec = time.perf_counter() - t0
    reference_ok = reference_answer is not None and verify(
        shipping, reference_answer)[0]
    compact_answer, compact_ops, compact_inspections = _compact_route(shipping)
    compact_ok = verify(shipping, compact_answer)[0]
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    explicit_demo_ok, explicit_demo_reason = _explicit_temporal_tc(
        demo, demo["answer"])
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_rate < 1e-6 and reference_ok and compact_ok
                 and demo_count == 1 and explicit_demo_ok),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "construction_exact_solution_count": 1,
        "construction_exact_density": "1/2^%d" % (shipping["n"] // 2),
        "demo_exact_solution_count": demo_count,
        "baseline_algorithm": "parity extraction plus exact GF(2) Gaussian elimination",
        "baseline_wall_clock_seconds": round(reference_sec, 6),
        "baseline_scalar_operations": reference_ops,
        "baseline_verified": reference_ok,
        "compact_route_exact_operations": compact_ops,
        "compact_route_row_entry_inspections": compact_inspections,
        "compact_route_verified": compact_ok,
        "explicit_demo_all_pairs_tc": explicit_demo_ok,
        "explicit_demo_reason": explicit_demo_reason,
    }

    attacks = {
        "outlier_occurrence_median": {"successes": 0, "attempts": 8},
        "public_order_alternation": {"successes": 0, "attempts": 8},
        "pair_orientation_by_label": {"successes": 0, "attempts": 8},
        "first_local_vertex_vote": {"successes": 0, "attempts": 8},
        "greedy_parity_repair_2n": {"successes": 0, "attempts": 8},
        "pair_aware_random_restart_512": {"successes": 0, "attempts": 8},
        "xor_rhs_local_vote": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_occurrence_median": _attack_occurrence_median(inst),
            "public_order_alternation": _attack_public_alternation(inst),
            "pair_orientation_by_label": _attack_pair_orientation_by_label(inst),
            "first_local_vertex_vote": _attack_first_option_vote(inst),
            "greedy_parity_repair_2n": _attack_greedy_repair(inst),
            "xor_rhs_local_vote": _attack_rhs_vote(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rrng = random.Random(seed ^ 0x5A17)
        restart_hit = False
        for _ in range(512):
            if verify(inst, random_candidate(inst, rrng))[0]:
                restart_hit = True
                break
        attacks["pair_aware_random_restart_512"]["successes"] += int(restart_hit)
        rt0 = time.perf_counter()
        candidate, operations = _gaussian_reference(inst)
        reference_times.append(time.perf_counter() - rt0)
        reference_operations.append(operations)
        reference_successes += int(
            candidate is not None and verify(inst, candidate)[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "parity-row extraction plus exact GF(2) Gaussian elimination",
            "complexity": "O(R + n^3) exact binary operations",
            "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_operations) / len(reference_operations)),
            "operations_max": max(reference_operations),
            "solves": "%d/8, as expected" % reference_successes,
        },
    }

    doubled = make_instance(n=2 * shipping["n"],
                            decoy_rows=2 * shipping["decoy_rows"], seed=2718)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] > shipping["n"]
                 and search_space(doubled) > search_space(shipping)),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_row_count": len(shipping["rows"]),
        "doubled_row_count": len(doubled["rows"]),
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": shipping["n"] // 2,
        "doubled_search_space_bits": doubled["n"] // 2,
    }

    invariant = 0
    complemented_invariant = 0
    carried_valid = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **shipping_params)
        rrng = random.Random(9000 + seed)
        pair_count = len(_core_coordinates(inst)[0])
        complemented = _complement_pairs(
            inst, [pid for pid in range(pair_count) if rrng.randrange(2)])
        first = list(range(inst["n"]))
        second = list(range(inst["n"]))
        rrng.shuffle(first)
        rrng.shuffle(second)
        composed = [second[first[old]] for old in range(inst["n"])]
        transformed = _relabel_instance(complemented, composed, rrng)
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        complemented_invariant += int(
            canonical_key(inst) == canonical_key(complemented))
        carried_valid += int(verify(transformed, transformed["answer"])[0])
    unrelated = {canonical_key(make_instance(seed=2000 + seed, **shipping_params))
                 for seed in range(20)}
    report["G8_canonical_key"] = {
        "pass": (invariant == 20 and complemented_invariant == 20
                 and carried_valid == 20 and len(unrelated) == 20),
        "composed_relabellings_invariant": invariant,
        "paired_complementations_invariant": complemented_invariant,
        "carried_witnesses_valid": carried_valid,
        "unrelated_distinct_keys": len(unrelated),
        "attempts_each": 20,
        "normalized_symmetries": [
            "variable renumbering",
            "row and local-option reordering",
            "exchange of the two variables in recovered pairs",
            "simultaneous bit complementation within recovered pairs",
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
    compact_answer, intended_ops, inspections = _compact_route(shipping)
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
        "api_error_calls": _G9_EVIDENCE.get("error_calls", {}),
        "diagnostic_not_gated": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "compact_route_row_entry_inspections": inspections,
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
