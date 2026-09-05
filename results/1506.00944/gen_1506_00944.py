"""Verified generator for compressed mixed-cluster editing instances.

The native problem is L-Cluster Editing for ell=2 from da Silva, Protti,
and Szwarcfiter, arXiv:1506.00944.  The input graph is a bipartite Cayley
lift on GF(2)^b.  An answer is an exact symbolic edition set: every listed
nonzero XOR offset denotes one full translation orbit of ordinary edge
additions or deletions.  Applying the planted orbits restores the nonzero
elements of a binary subspace.  Its cosets are then complete bipartite
components, so generation knows a witness without solving the instance.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from functools import lru_cache
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "bipartite Cayley graph on two copies of GF(2)^b",
        "translation-orbit edge edition set",
        "complete-bipartite mixed-cluster graph",
    ],
    "verification_operations": [
        "integer XOR",
        "set symmetric difference",
        "exact closure test for a binary subspace",
        "coset-to-complete-bipartite identity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A complete-bipartite Cayley cluster has a connection set closed under "
        "XOR after zero is adjoined; without recognizing that invariant, a solver "
        "must search over additions and deletions of whole translation orbits."
    ),
    "hardness_basis": (
        "Track B: exhaustive four-generator basis decoding is an exact "
        "O(C(15,4)*16) algorithm for the shipping representation and is measured "
        "at 41,866 span/membership operations and 0.012 seconds at the shipping "
        "preset, whereas "
        "XOR-support recovery uses about 130 exact operations once closure is recognized; the paper's "
        "general forbidden-subgraph search is O(6^k+n+m) for expanded edit budget k."
    ),
    "max_answer_tokens": 20,
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
    "demo": {"n": 16, "subspace_dim": 2, "errors": 1},
    "easy": {"n": 64, "subspace_dim": 3, "errors": 1},
    "medium": {"n": 1024, "subspace_dim": 4, "errors": 3},
    "hard": {"n": 4096, "subspace_dim": 4, "errors": 6},
}
SHIPPING_DIFFICULTY = "hard"
# Retained local candidate only.  The script-owned bare verdict is budget_bound:
# every rung through n=65536 was solved while escalate() still offered n=131072.

STRUCTURAL_HINT = (
    "After zero is adjoined, the intended connection set is closed under XOR."
)
PLACEBO_HINT = (
    "Keep the addition and deletion lists sorted to avoid transcription mistakes."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"add\": [...], \"remove\": [...]} containing equally "
        "many (between 1 and the displayed error bound) distinct nonzero XOR "
        "offsets in increasing order; additions must be absent from D and removals "
        "must belong to D.  Each offset expands to one translation orbit of n "
        "ordinary edge editions."
    ),
    "bounds": {
        "fields": ["add", "remove"],
        "offset_range": "1..n-1",
        "maximum_offsets_per_field": "errors",
        "expanded_edits_per_offset": "n",
    },
}

NOTES = (
    "Section 2 defines ell-cliques as connected complete ell-partite graphs, "
    "edition sets, solutions, modules, and modular decomposition. Proposition 1 "
    "characterizes L-cluster graphs by forbidden induced P4, paw, and K_(ell+2)-e. "
    "The NP-completeness theorem in Section 2 fixes the hard native problem, while "
    "the Introduction explicitly gives Cai's O((ell+2)^(2k)n^(ell+3)) FPT method "
    "and the paper's O(((ell+2)(ell+1)/2)^k+n+m) kernel-plus-search method; those "
    "algorithms rule out a Track A claim for this structured distribution.  The "
    "generator samples a binary subspace and its edition orbits first, then forms "
    "the corrupted Cayley connection set.  Numeric-extreme, random-restart, "
    "first-basis, and coordinate-subspace attacks are rejected by "
    "construction without changing or discovering the planted witness."
)

# Replaced with script-owned observations after the three oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_bare_budget_bound",
}


def _is_power_of_two(x):
    return isinstance(x, int) and not isinstance(x, bool) and x > 0 and not (x & (x - 1))


def _validate_params(n, subspace_dim, errors):
    if not _is_power_of_two(n) or n < 8:
        raise ValueError("n must be a power of two and at least 8")
    bits = n.bit_length() - 1
    if isinstance(subspace_dim, bool) or not isinstance(subspace_dim, int):
        raise ValueError("subspace_dim must be an integer")
    if not (2 <= subspace_dim < bits):
        raise ValueError("subspace_dim must satisfy 2 <= subspace_dim < log2(n)")
    if isinstance(errors, bool) or not isinstance(errors, int) or errors < 1:
        raise ValueError("errors must be a positive integer")
    if errors > (1 << subspace_dim) - subspace_dim - 1:
        raise ValueError("too many errors to retain a spanning planted set")
    return bits


def _rref_basis(vectors, bits=None):
    """Canonical descending-pivot XOR basis as a tuple, or shorter if dependent."""
    if bits is None:
        bits = max((int(v).bit_length() for v in vectors), default=0)
    rows = [0] * bits
    for raw in vectors:
        x = int(raw)
        for pivot in range(bits - 1, -1, -1):
            if not ((x >> pivot) & 1):
                continue
            if rows[pivot]:
                x ^= rows[pivot]
            else:
                rows[pivot] = x
                for low in range(pivot):
                    if rows[low] and ((rows[pivot] >> low) & 1):
                        rows[pivot] ^= rows[low]
                for high in range(pivot + 1, bits):
                    if rows[high] and ((rows[high] >> pivot) & 1):
                        rows[high] ^= rows[pivot]
                break
    return tuple(rows[p] for p in range(bits - 1, -1, -1) if rows[p])


def _span(basis):
    values = {0}
    for v in basis:
        values |= {x ^ v for x in tuple(values)}
    return values


def _random_subspace(n, dimension, rng):
    bits = n.bit_length() - 1
    basis = ()
    while len(basis) < dimension:
        basis = _rref_basis([rng.randrange(1, n) for _ in range(dimension)], bits)
    # Rejection-sampling ordered full-rank tuples is uniform over subspaces: every
    # dimension-r subspace has the same number of ordered bases.
    return basis, _span(basis)


def _answer_from_subspace(inst, subspace):
    dset = set(inst["connection_offsets"])
    nz = set(subspace)
    nz.discard(0)
    add = sorted(nz - dset)
    remove = sorted(dset - nz)
    return {"add": add, "remove": remove}


def _xor_support(dset):
    values = sorted(dset)
    counts = Counter()
    for i, a in enumerate(values):
        for b in values[i + 1 :]:
            counts[a ^ b] += 1
    return counts


def _compact_decode(inst, with_operations=False):
    """Short distribution decoder: high XOR-support elements reveal the subspace."""
    dset = set(inst["connection_offsets"])
    counts = _xor_support(dset)
    operations = math.comb(len(dset), 2)
    # Missing subspace elements are not in D, but reappear many times as XORs of
    # two retained elements.  Rank every observed element and every pair XOR.
    ordered = sorted(dset | set(counts), key=lambda x: (-counts[x], x))
    chosen = []
    for x in ordered:
        operations += 1
        if len(_rref_basis(chosen + [x], inst["bits"])) > len(chosen):
            chosen.append(x)
            if len(chosen) == inst["subspace_dim"]:
                break
    if len(chosen) != inst["subspace_dim"]:
        return (None, operations) if with_operations else None
    subspace = _span(_rref_basis(chosen, inst["bits"]))
    operations += (1 << inst["subspace_dim"])
    answer = _answer_from_subspace(inst, subspace)
    ok, _ = verify(inst, answer)
    if not ok:
        answer = None
    return (answer, operations) if with_operations else answer


def _candidate_from_span(inst, vectors):
    basis = _rref_basis(vectors, inst["bits"])
    if len(basis) != inst["subspace_dim"]:
        return None
    return _answer_from_subspace(inst, _span(basis))


def _attack_numeric_extremes(inst):
    d = inst["errors"]
    present = set(inst["connection_offsets"])
    absent = [x for x in range(1, inst["n"]) if x not in present]
    return {"add": absent[:d], "remove": sorted(present, reverse=True)[:d][::-1]}


def _attack_first_basis(inst):
    chosen = []
    for x in inst["connection_offsets"]:
        if len(_rref_basis(chosen + [x], inst["bits"])) > len(chosen):
            chosen.append(x)
        if len(chosen) == inst["subspace_dim"]:
            break
    return _candidate_from_span(inst, chosen)


def _attack_greedy_support(inst):
    d = inst["errors"]
    present = set(inst["connection_offsets"])
    counts = _xor_support(present)
    remove = sorted(present, key=lambda x: (counts[x], x))[:d]
    missing = [x for x in counts if x not in present]
    missing.sort(key=lambda x: (-counts[x], x))
    if len(missing) < d:
        return None
    return {"add": sorted(missing[:d]), "remove": sorted(remove)}


def _attack_coordinate_subspace(inst):
    basis = [1 << i for i in range(inst["subspace_dim"])]
    return _candidate_from_span(inst, basis)


def _attack_random(inst, rng, restarts):
    for _ in range(restarts):
        ans = random_candidate(inst, rng)
        if verify(inst, ans)[0]:
            return ans
    return None


def _cheap_attacks_fail(inst, trial_seed):
    candidates = (
        _attack_numeric_extremes(inst),
        _attack_first_basis(inst),
        _attack_coordinate_subspace(inst),
        _attack_random(inst, random.Random(trial_seed ^ 0xA5A55A5A), 64),
    )
    return all(ans is None or not verify(inst, ans)[0] for ans in candidates)


def _compact_route_is_invariant(inst):
    """Construction-only check that support ties cannot depend on coordinates."""
    corrected = set(inst["connection_offsets"])
    corrected.difference_update(inst["answer"]["remove"])
    corrected.update(inst["answer"]["add"])
    corrected.add(0)
    support = _xor_support(set(inst["connection_offsets"]))
    reliable = {x for x, count in support.items() if count >= 2}
    return reliable <= corrected and len(_rref_basis(reliable, inst["bits"])) == inst["subspace_dim"]


def _raw_instance(n, bits, subspace_dim, errors, rng, trial=0):
    """Sample the witness first, then corrupt its connection set."""
    _, subspace = _random_subspace(n, subspace_dim, rng)
    nonzero = sorted(subspace - {0})
    missing = set(rng.sample(nonzero, errors))
    extra = set()
    while len(extra) < errors:
        x = rng.randrange(1, n)
        if x not in subspace:
            extra.add(x)
    dset = list((set(nonzero) - missing) | extra)
    rng.shuffle(dset)
    return {
        "n": n,
        "bits": bits,
        "ell": 2,
        "subspace_dim": subspace_dim,
        "errors": errors,
        "connection_offsets": dset,
        "expanded_vertices": 2 * n,
        "expanded_edit_budget": 2 * errors * n,
        "answer": {"add": sorted(missing), "remove": sorted(extra)},
        "construction_trial": trial,
    }


@lru_cache(maxsize=16)
def _template_catalog(n, subspace_dim, errors, count=64):
    """Deterministic catalog of non-isomorphic, already-certified hard draws."""
    bits = _validate_params(n, subspace_dim, errors)
    rng = random.Random((n << 16) ^ (subspace_dim << 8) ^ errors ^ 0x150600944)
    records = []
    keys = set()
    trial = 0
    while len(records) < count and trial < 200000:
        inst = _raw_instance(n, bits, subspace_dim, errors, rng, trial)
        key = canonical_key(inst)
        if (
            key not in keys
            and _compact_decode(inst) is not None
            and _compact_route_is_invariant(inst)
            and _cheap_attacks_fail(inst, trial ^ 0x51A7)
        ):
            keys.add(key)
            records.append(
                (
                    tuple(inst["connection_offsets"]),
                    tuple(inst["answer"]["add"]),
                    tuple(inst["answer"]["remove"]),
                )
            )
        trial += 1
    if len(records) < count:
        raise RuntimeError("could not build the certified structural template catalog")
    return tuple(records)


def make_instance(n, seed=0, subspace_dim=4, errors=3, **params):
    """Inverse-generate a corrupted Cayley mixed-cluster instance.

    The subspace and the missing/extra offset orbits are sampled first.  Attack
    filtering only discards already-certified instances; it never discovers or
    changes the planted answer.
    """
    bits = _validate_params(n, subspace_dim, errors)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    if (
        n >= DIFFICULTY["hard"]["n"]
        and subspace_dim == DIFFICULTY["hard"]["subspace_dim"]
        and errors >= DIFFICULTY["hard"]["errors"]
    ):
        records = _template_catalog(n, subspace_dim, errors)
        dvals, add, remove = records[seed % len(records)]
        base = {
            "n": n,
            "bits": bits,
            "ell": 2,
            "subspace_dim": subspace_dim,
            "errors": errors,
            "connection_offsets": list(dvals),
            "expanded_vertices": 2 * n,
            "expanded_edit_budget": 2 * errors * n,
            "answer": {"add": list(add), "remove": list(remove)},
            "construction_trial": 0,
        }
        # Coordinate changes create fresh labelled instances while the catalog
        # key correctly identifies their underlying isomorphism class.
        for trial in range(1000):
            columns = _random_linear_columns(bits, rng)
            inst = _transform_instance(base, columns)
            rng.shuffle(inst["connection_offsets"])
            inst["construction_trial"] = trial
            if _cheap_attacks_fail(inst, seed ^ trial):
                return inst
        raise RuntimeError("could not relabel a certified template safely")
    max_trials = 10000
    for trial in range(max_trials):
        inst = _raw_instance(n, bits, subspace_dim, errors, rng, trial)
        # The demo is deliberately transparent.  Larger levels retain only draws
        # that defeat cheap construction-aware attacks while preserving the short
        # XOR-support decoder.
        if n < DIFFICULTY["hard"]["n"]:
            return inst
        compact = _compact_decode(inst)
        if compact is not None and _cheap_attacks_fail(inst, seed ^ (trial * 0x9E3779B1)):
            return inst
    raise RuntimeError("could not draw an attack-resistant certified instance")


def render(inst):
    dvals = " ".join(map(str, inst["connection_offsets"]))
    statement = f"""Mixed cluster editing on a bipartite Cayley graph (ell = 2).

Let XOR mean bitwise exclusive-or on integers.  The graph has two layers of
vertices (x,p), where 0 <= x < {inst['n']} and p is 0 or 1.  There are no
same-layer edges.  Vertices (x,0) and (y,1) are adjacent exactly when
x XOR y belongs to {{0}} union D, where

D = [{dvals}].

An offset edition is compressed notation for ordinary edge editions.  Adding
a nonzero offset delta not in D adds every edge (x,0)-(y,1) with x XOR y =
delta.  Removing an offset delta in D deletes every such edge.  For nonzero
delta this is exactly {inst['n']} ordinary edge editions: both orientations of
each of {inst['n']//2} unordered base pairs.  Thus at most
{inst['expanded_edit_budget']} ordinary edge editions are allowed.

A mixed cluster graph for ell=2 is a vertex-disjoint union of components, each
of which is either a clique or a connected complete bipartite graph.  Find
equally long lists ADD and REMOVE, of some length j with
1 <= j <= {inst['errors']}, such that applying all their offset editions makes
the displayed graph a mixed cluster graph.  Every offset must be an integer in
1..{inst['n']-1}; lists must be strictly increasing; ADD offsets must be absent
from D; REMOVE offsets must belong to D; and no offset may repeat.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys \"add\" and \"remove\" and integer-list values.
Example: <answer>{{\"add\":[3,17],\"remove\":[9,22]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(bodies))
    if not candidates:
        candidates = [text]
    decoder = json.JSONDecoder()
    for body in candidates:
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", body.strip(), flags=re.I)
        starts = [m.start() for m in re.finditer(r"\{", cleaned)] or [0]
        for start in starts:
            try:
                obj, _ = decoder.raw_decode(cleaned[start:])
            except (ValueError, TypeError):
                continue
            if isinstance(obj, dict):
                return obj
    return None


def _validate_answer_shape(inst, answer):
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"add", "remove"}:
        return False, "answer must have exactly the keys add and remove"
    add, remove = answer["add"], answer["remove"]
    if not isinstance(add, list) or not isinstance(remove, list):
        return False, "add and remove must both be lists"
    if not add and not remove:
        return False, "answer is empty"
    if len(add) != len(remove):
        return False, "add and remove must have equal lengths"
    if len(add) > inst["errors"]:
        return False, "too many offset editions for the stated budget"
    for name, values in (("add", add), ("remove", remove)):
        if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
            return False, f"{name} offsets must be integers"
        if any(x < 1 or x >= inst["n"] for x in values):
            return False, f"{name} offset outside 1..n-1"
        if len(set(values)) != len(values):
            return False, f"{name} offsets must be distinct"
        if values != sorted(values):
            return False, f"{name} offsets must be strictly increasing"
    if set(add) & set(remove):
        return False, "an offset cannot be both added and removed"
    present = set(inst["connection_offsets"])
    if any(x in present for x in add):
        return False, "an add offset is already present in D"
    if any(x not in present for x in remove):
        return False, "a remove offset is absent from D"
    return True, "ok"


def verify(inst, answer):
    """Check a compressed edition set without consulting inst['answer']."""
    ok, reason = _validate_answer_shape(inst, answer)
    if not ok:
        return False, reason
    corrected = set(inst["connection_offsets"])
    corrected.difference_update(answer["remove"])
    corrected.update(answer["add"])
    expected_size = (1 << inst["subspace_dim"]) - 1
    if len(corrected) != expected_size:
        return False, "corrected connection set has the wrong size"
    subspace = corrected | {0}
    for a in subspace:
        for b in subspace:
            if (a ^ b) not in subspace:
                return False, "corrected connection set is not XOR-closed"
    # Executable theorem certificate: cosets of this subspace partition GF(2)^b;
    # the two lifted layers over each coset induce K_(2^r,2^r), with no edges
    # between cosets.  These are precisely allowed ell=2 components.
    return True, "ok"


def _candidate_weights(inst):
    absent = inst["n"] - 1 - len(inst["connection_offsets"])
    present = len(inst["connection_offsets"])
    return [math.comb(absent, j) * math.comb(present, j) for j in range(1, inst["errors"] + 1)]


def random_candidate(inst, rng):
    present = sorted(inst["connection_offsets"])
    pset = set(present)
    weights = _candidate_weights(inst)
    pick = rng.randrange(sum(weights))
    j = 1
    for weight in weights:
        if pick < weight:
            break
        pick -= weight
        j += 1
    add = set()
    while len(add) < j:
        x = rng.randrange(1, inst["n"])
        if x not in pset:
            add.add(x)
    return {"add": sorted(add), "remove": sorted(rng.sample(present, j))}


def search_space(inst):
    return sum(_candidate_weights(inst))


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200000:
        return None
    present = sorted(inst["connection_offsets"])
    pset = set(present)
    absent = [x for x in range(1, inst["n"]) if x not in pset]
    count = 0
    for j in range(1, inst["errors"] + 1):
        for add in itertools.combinations(absent, j):
            for remove in itertools.combinations(present, j):
                if verify(inst, {"add": list(add), "remove": list(remove)})[0]:
                    count += 1
    return count


def _wl_invariant(inst):
    """Strong GL(b,2)-invariant fingerprint of the small offset configuration."""
    values = tuple(sorted(inst["connection_offsets"]))
    support = _xor_support(values)
    colors = {x: str(support[x]) for x in values}
    for _ in range(4):
        nxt = {}
        for x in values:
            neighborhood = sorted((support[x ^ y], colors[y]) for y in values if y != x)
            blob = json.dumps([colors[x], neighborhood], separators=(",", ":"))
            nxt[x] = hashlib.sha256(blob.encode()).hexdigest()
        colors = nxt
    edges = []
    for i, x in enumerate(values):
        for y in values[i + 1 :]:
            edges.append((min(colors[x], colors[y]), max(colors[x], colors[y]), support[x ^ y]))
    hist = Counter(support.values())
    # Offsets absent from support all have count zero and must be represented too.
    hist[0] += inst["n"] - 1 - len(support)
    # The weight distribution of zero-XOR subsets is the weight enumerator of the
    # binary dependency code of D.  It is invariant under every coordinate change
    # and distinguishes configurations that pairwise color refinement cannot.
    dependency_dp = {(0, 0): 1}
    for value in values:
        updated = dict(dependency_dp)
        for (xor_sum, size), multiplicity in dependency_dp.items():
            key = (xor_sum ^ value, size + 1)
            updated[key] = updated.get(key, 0) + multiplicity
        dependency_dp = updated
    zero_xor_weights = [dependency_dp.get((0, size), 0) for size in range(len(values) + 1)]
    payload = {
        "n": inst["n"],
        "r": inst["subspace_dim"],
        "e": inst["errors"],
        "support_histogram": sorted(hist.items()),
        "vertex_colors": sorted(colors.values()),
        "colored_edges": sorted(edges),
        "zero_xor_subset_weights": zero_xor_weights,
    }
    return payload


def canonical_key(inst):
    blob = json.dumps(_wl_invariant(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _apply_linear(x, columns):
    out = 0
    bit = 0
    while x:
        if x & 1:
            out ^= columns[bit]
        bit += 1
        x >>= 1
    return out


def _random_linear_columns(bits, rng):
    while True:
        cols = [rng.randrange(1, 1 << bits) for _ in range(bits)]
        if len(_rref_basis(cols, bits)) == bits:
            return cols


def _transform_instance(inst, columns, reverse_records=False):
    out = dict(inst)
    offsets = [_apply_linear(x, columns) for x in inst["connection_offsets"]]
    answer = {
        "add": sorted(_apply_linear(x, columns) for x in inst["answer"]["add"]),
        "remove": sorted(_apply_linear(x, columns) for x in inst["answer"]["remove"]),
    }
    out["connection_offsets"] = list(reversed(sorted(offsets))) if reverse_records else sorted(offsets)
    out["answer"] = answer
    return out


def _reference_basis_decode(inst):
    """Exact mechanical decoder, enumerating all displayed four-generator bases."""
    values = tuple(inst["connection_offsets"])
    r = inst["subspace_dim"]
    operations = 0
    found = None
    # Complete enumeration is deliberate: it gives a stable measured mechanical
    # cost and records all equally close witnesses rather than stopping on a lucky
    # early basis ordering.
    valid_count = 0
    seen = set()
    for combo in itertools.combinations(values, r):
        operations += r * r
        basis = _rref_basis(combo, inst["bits"])
        if len(basis) != r:
            continue
        subspace = frozenset(_span(basis))
        if subspace in seen:
            continue
        seen.add(subspace)
        operations += 1 << r
        candidate = _answer_from_subspace(inst, subspace)
        ok, _ = verify(inst, candidate)
        operations += len(inst["connection_offsets"])
        if ok:
            valid_count += 1
            if found is None:
                found = candidate
    return found, operations, valid_count


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _expanded_graph_valid(inst, answer):
    """Independent explicit graph check, used only on hand-scale test instances."""
    n = inst["n"]
    dset = set(inst["connection_offsets"])
    dset.difference_update(answer["remove"])
    dset.update(answer["add"])
    adj = [set() for _ in range(2 * n)]
    for x in range(n):
        for y in range(n):
            if (x ^ y) == 0 or (x ^ y) in dset:
                u, v = x, n + y
                adj[u].add(v)
                adj[v].add(u)
    unseen = set(range(2 * n))
    while unseen:
        root = next(iter(unseen))
        stack = [root]
        comp = set()
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            stack.extend(adj[u] - comp)
        unseen -= comp
        left = {u for u in comp if u < n}
        right = comp - left
        if not left or not right:
            return False
        if any(adj[u] & left for u in left) or any(adj[u] & right for u in right):
            return False
        if any((adj[u] & comp) != right for u in left):
            return False
        if any((adj[u] & comp) != left for u in right):
            return False
    return True


def _run_attacks(inst, seed, random_restarts=256):
    rng = random.Random(seed ^ 0xC0DEC0DE)
    return {
        "outlier_numeric_extremes": _attack_numeric_extremes(inst),
        "random_restart_256": _attack_random(inst, rng, random_restarts),
        "first_independent_basis_ansatz": _attack_first_basis(inst),
        "coordinate_low_bits_subspace": _attack_coordinate_subspace(inst),
    }


def selftest():
    report = {}

    g1_attempts = g1_success = json_roundtrips = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            if verify(inst, inst["answer"])[0]:
                g1_success += 1
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    explicit_demo = _expanded_graph_valid(demo, demo["answer"])
    report["G1_planted_verifies"] = {
        "pass": g1_success == g1_attempts and json_roundtrips == g1_attempts and explicit_demo,
        "successes": g1_success,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "explicit_demo_graph_check": explicit_demo,
    }

    shipping = make_instance(seed=7, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = json.loads(json.dumps(shipping["answer"]))
    corruptions = {}
    dropped = json.loads(json.dumps(planted))
    dropped["add"] = dropped["add"][:-1]
    corruptions["drop_one"] = dropped
    swapped = json.loads(json.dumps(planted))
    swapped["add"][0], swapped["remove"][0] = swapped["remove"][0], swapped["add"][0]
    swapped["add"].sort()
    swapped["remove"].sort()
    corruptions["swap_one"] = swapped
    duplicated = json.loads(json.dumps(planted))
    duplicated["add"][1] = duplicated["add"][0]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = {"add": [], "remove": []}
    out_of_range = json.loads(json.dumps(planted))
    out_of_range["remove"][0] = shipping["n"]
    corruptions["out_of_range"] = out_of_range
    reasons = {name: verify(shipping, ans)[1] for name, ans in corruptions.items()}
    g2_ok = all(not verify(shipping, ans)[0] for ans in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": g2_ok and len(set(reasons.values())) == len(reasons),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    model_style = "I used XOR closure.\n```json\n<answer>" + json.dumps(planted) + "</answer>\n```"
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(shipping, parsed)[0],
        "parsed": parsed is not None,
    }

    samples = 200000
    guess_rng = random.Random(150600944)
    t0 = time.perf_counter()
    hits = 0
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": search_space(shipping),
        "candidate_space_bits": search_space(shipping).bit_length() - 1,
        "sampler": "uniform over all statement-compliant equal-size add/remove offset sets",
        "wall_clock_sec": guess_seconds,
    }

    demo_count = enumerate_all(demo)
    t0 = time.perf_counter()
    attack_rng = random.Random(505)
    attack_hits = 0
    strongest_samples = 4096
    for _ in range(strongest_samples):
        attack_hits += int(verify(shipping, random_candidate(shipping, attack_rng))[0])
    attack_seconds = time.perf_counter() - t0
    t0 = time.perf_counter()
    ref_answer, ref_operations, ref_valid = _reference_basis_decode(shipping)
    ref_seconds = time.perf_counter() - t0
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and attack_hits == 0 and ref_answer is not None,
        "demo_exact_valid_answer_count": demo_count,
        "shipping_density_hits": hits,
        "shipping_density_total": samples,
        "shipping_density_estimate": hits / samples,
        "strongest_failing_attack_samples": strongest_samples,
        "strongest_failing_attack_hits": attack_hits,
        "strongest_failing_attack_wall_clock_sec": attack_seconds,
        "reference_algorithm_operations": ref_operations,
        "reference_algorithm_wall_clock_sec": ref_seconds,
        "reference_valid_subspaces": ref_valid,
    }

    attack_results = {name: {"successes": 0, "attempts": 8} for name in (
        "outlier_numeric_extremes",
        "random_restart_256",
        "first_independent_basis_ansatz",
        "coordinate_low_bits_subspace",
    )}
    ref_successes = compact_successes = 0
    ref_ops = []
    ref_times = []
    compact_ops = []
    for seed in range(8):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _run_attacks(inst, seed).items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        t0 = time.perf_counter()
        candidate, operations, _ = _reference_basis_decode(inst)
        ref_times.append(time.perf_counter() - t0)
        ref_ops.append(operations)
        ref_successes += int(candidate is not None and verify(inst, candidate)[0])
        compact, operations = _compact_decode(inst, with_operations=True)
        compact_ops.append(operations)
        compact_successes += int(compact is not None and verify(inst, compact)[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exhaustive displayed-basis decoding with exact span checks",
            "complexity": "O(C(|D|,r) * (r^2 + 2^r + |D|)) exact",
            "operations": max(ref_ops),
            "wall_clock_sec": max(ref_times),
            "solves": f"{ref_successes}/8, as expected",
        },
        "efficient_distribution_decoder": {
            "name": "XOR-pair support followed by a four-generator span",
            "complexity": "O(|D|^2 + 2^r) exact",
            "operations": max(compact_ops),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=23, **doubled_params)
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0] and search_space(doubled) > search_space(shipping),
        "shipping_vertices": shipping["expanded_vertices"],
        "doubled_vertices": doubled["expanded_vertices"],
        "shipping_space_bits": search_space(shipping).bit_length() - 1,
        "doubled_space_bits": search_space(doubled).bit_length() - 1,
    }

    invariant = carried = 0
    distinct_keys = set()
    seed = 2000
    draws = 0
    while len(distinct_keys) < 20 and draws < 500:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        seed += 1
        draws += 1
        key = canonical_key(inst)
        if key in distinct_keys:
            continue
        distinct_keys.add(key)
        rng = random.Random(9000 + seed)
        cols = _random_linear_columns(inst["bits"], rng)
        for reverse in (False, True):
            transformed = _transform_instance(inst, cols, reverse_records=reverse)
            invariant += int(canonical_key(transformed) == key)
            carried += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant == 40 and carried == 40 and len(distinct_keys) == 20,
        "invariance_attempts": 40,
        "invariant_relabellings": invariant,
        "carried_witness_attempts": 40,
        "carried_witnesses_valid": carried,
        "distinctness_attempts": 20,
        "distinct_unrelated_keys": len(distinct_keys),
        "draws_needed_for_20_unrelated_keys": draws,
        "symmetries_tested": [
            "arbitrary invertible GF(2) coordinate changes",
            "connection-record reordering",
            "vertex translations (offset representation is unchanged)",
            "global layer swap (offset representation is unchanged)",
            "compositions of these symmetries",
        ],
    }

    answer_blobs = [json.dumps(make_instance(seed=s, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"], separators=(",", ":")) for s in range(20)]
    answer_chars = max(map(len, answer_blobs))
    answer_elements = max(_answer_atoms(json.loads(blob)) for blob in answer_blobs)
    compact, intended_ops = _compact_decode(shipping, with_operations=True)
    arms = {k: dict(v) for k, v in G9_ORACLE_RESULTS.items() if k in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else 0.0
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": math.ceil(answer_chars / 4),
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    report["all_passed"] = all(v.get("pass") for k, v in report.items() if k.startswith("G"))
    return report


def escalate(params):
    """Grow the ambient group first, then crowd it with one more error orbit."""
    p = {k: v for k, v in dict(params).items() if k != "_preset"}
    n = int(p.get("n", DIFFICULTY["hard"]["n"]))
    r = int(p.get("subspace_dim", 4))
    errors = int(p.get("errors", 3))
    # This fixed-answer-length axis increases the outside-offset haystack without
    # adding answer atoms.  Every second escalation also raises corruption density.
    p["n"] = n * 2
    if n.bit_length() % 2 == 0 and errors < min(7, (1 << r) - r - 1):
        p["errors"] = errors + 1
    else:
        p["errors"] = errors
    p["subspace_dim"] = r
    return p


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
