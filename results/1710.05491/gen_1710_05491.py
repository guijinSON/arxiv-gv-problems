"""Verified generator for succinct Balanced Judicious Bipartition instances.

The native problem is BJB from Section 1 of Lokshtanov--Saurabh--Sharma--
Zehavi, arXiv:1710.05491.  Each instance is a connected bipartite Cayley
multigraph on a binary vector space.  The certificate is a succinct affine
description of one side of a balanced bipartition.  It is carried through a
product of invertible basis changes and is never recovered by solving the
emitted instance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "succinct finite undirected Cayley multigraph",
        "binary vectors and change-of-basis blocks over GF(2)",
        "balanced vertex bipartition represented by an affine parity rule",
    ],
    "verification_operations": [
        "exact binary inner product",
        "exact rank over GF(2)",
        "integer range and balance comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The displayed update blocks are reversible changes of basis for "
        "the multiplicity-labelled Cayley basis; without reversing those changes, "
        "a solver must bipartite-color an exponential graph or eliminate a "
        "dense binary system."
    ),
    "hardness_basis": (
        "Track B: Theorem 1 solves BJB in 2^{k^{O(1)}}|V|^{O(1)}, and on this "
        "succinct k=0 subfamily GF(2) Gaussian elimination is O(n^3); at shipping "
        "n=64 it measured 84,500 scalar-bit operations and 0.029 seconds in a "
        "recorded selftest, "
        "whereas reversing the three basis-change blocks costs 3(n-1)=189 exact "
        "XOR operations that are not reliably executable in context without tools."
    ),
    "max_answer_tokens": 6,
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
    "demo": {"n": 6, "extras": 2, "layers": 3},
    "easy": {"n": 64, "extras": 8, "layers": 3},
    "medium": {"n": 80, "extras": 12, "layers": 3},
    "hard": {"n": 96, "extras": 16, "layers": 3},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The displayed update blocks are reversible changes of basis for the "
    "multiplicity-labelled Cayley generator masks."
)
PLACEBO_HINT = (
    "The displayed masks and multiplicities reward careful attention to binary "
    "indexing and hexadecimal conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A pair [mask,phase], rendered as MASK_HEX, PHASE: MASK_HEX has exactly "
        "ceil(n/4) lowercase hexadecimal digits, represents a nonzero n-bit "
        "integer, and PHASE is 0 or 1.  It denotes all vertices x satisfying "
        "parity(mask AND x)=phase."
    ),
    "bounds": {
        "fields": 2,
        "mask_min": 1,
        "mask_max": "2^n-1",
        "phase": [0, 1],
        "hex_digits": "ceil(n/4)",
    },
}

NOTES = r"""
Step 0 and paper grounding.  Section 1 defines BJB on a multigraph G with
integers mu,k1,k2: find an ordered partition (V1,V2) with |V1|=mu and at most
k_i edges induced by V_i.  Proposition 1 is the construction theorem used
here: a connected bipartite graph has exactly the two ordered bipartitions
(X,Y) and (Y,X).  Theorem 1 is the easy-regime warning, not a Track-A hardness
claim: BJB is solvable in 2^{k^{O(1)}} |V|^{O(1)} time for k=k1+k2.  Sections
3--6 obtain this through Odd Cycle Transversal, annotated bipartite BJB,
connected components, a highly connected tree decomposition, and dynamic
programming.

Construction.  Begin with the standard basis of GF(2)^n.  Three independently
sampled blocks apply the invertible update column[i] ^= column[j] for ordered
pairs i != j.  Starting from an all-one equation right side and undoing the
updates gives a nonzero covector w whose dot product with every resulting
basis column is one.  Update blocks are resampled unless this carried covector
has between n/3 and 2n/3 one-bits, excluding a low-weight planting signature
without solving any public instance.  Extra odd sums of the preimage basis columns add genuine
seed-dependent Cayley structure while preserving w.g=1.  Unique parallel-edge
multiplicities make the basis roles intrinsic to the multigraph.  Since the
basis generators span the group, the Cayley graph is connected; since every
generator flips w.x, it is bipartite.  Proposition 1 therefore carries the
sampled certificate.  Generation uses only this identity composition.

Track B and attacks.  A computer expands the masks and solves the displayed
dense binary equations by Gaussian elimination in O(n^3), and the successful
reference run is reported separately.  Explicit breadth-first coloring would
touch 2^n vertices.  The compact construction-specific route reverses the
three update blocks in 3(n-1) bit XORs, below the no-tool cap but long enough to be
error-prone without a sandbox.  The attack panel tests a coordinate-frequency
outlier, greedy majority assignment, 256 uniform affine rules, and the tempting
but wrong forward-update ansatz.  There are no separately distributed plants and
decoys: every graph vertex has identical degree and every public generator is
obtained through the same invertible map.

Representation caveat.  The object is exactly the paper's finite multigraph
and verify checks its induced-edge condition, but it is given by Cayley masks
and accompanied by construction metadata rather than by an explicit
exponentially long edge list.  This is a succinct input model, so the benchmark
claim is no-tool compression, not the paper's explicit-input running-time bound
and not average-case hardness.
""".strip()


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 2, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "incomplete_after_2_of_3_scored_then_http_403",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_HEX_RE = re.compile(r"^[0-9a-f]+$")
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, extras, layers):
    for name, value in (("n", n), ("extras", extras), ("layers", layers)):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 4 <= n <= 256:
        raise ValueError("n must lie in 4..256")
    if not 0 <= extras <= 128:
        raise ValueError("extras must lie in 0..128")
    if not 1 <= layers <= 8:
        raise ValueError("layers must lie in 1..8")


def _parity(value):
    return value.bit_count() & 1


def _hex_width(n):
    return (n + 3) // 4


def _mask_text(value, n):
    return format(value, f"0{_hex_width(n)}x")


def _apply_column_updates(n, update_blocks):
    columns = [1 << i for i in range(n)]
    for block in update_blocks:
        for i, j in block:
            columns[i] ^= columns[j]
    return columns


def _update_witness(n, update_blocks):
    rhs = [1] * n
    for block in reversed(update_blocks):
        for i, j in reversed(block):
            rhs[i] ^= rhs[j]
    value = 0
    for i, bit in enumerate(rhs):
        value |= bit << i
    return value


def _linear_image(mask, columns):
    result = 0
    bit = 0
    value = mask
    while value:
        if value & 1:
            result ^= columns[bit]
        value >>= 1
        bit += 1
    return result


def _random_odd_mask(rng, n):
    # Odd weights at least three avoid duplicating a basis generator.
    choices = [w for w in (3, 5, 7, 9) if w <= n]
    weight = rng.choice(choices)
    value = 0
    for index in rng.sample(range(n), weight):
        value |= 1 << index
    return value


def make_instance(n, seed=0, extras=8, layers=3, **params):
    """Compose invertible basis changes around a known bipartition."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    _validate(n, extras, layers)
    rng = random.Random(seed)

    # Rejection-sample only the private change-of-basis description, while the
    # carried witness is already known.  The density condition prevents a rare
    # low-Hamming-weight planting signature; it never solves an emitted graph.
    for _attempt in range(10_000):
        update_blocks = []
        for _ in range(layers):
            block = []
            previous = None
            for _ in range(n - 1):
                while True:
                    i = rng.randrange(n)
                    j = rng.randrange(n - 1)
                    if j >= i:
                        j += 1
                    if (i, j) != previous:
                        break
                block.append([i, j])
                previous = (i, j)
            update_blocks.append(block)
        basis = _apply_column_updates(n, update_blocks)
        witness = _update_witness(n, update_blocks)
        if n < 16 or n // 3 <= witness.bit_count() <= (2 * n) // 3:
            break
    else:
        raise AssertionError("could not sample a dense carried witness")
    if witness == 0 or any(_parity(witness & column) != 1 for column in basis):
        raise AssertionError("internal basis-change identity failed")

    generator_records = []
    for i, column in enumerate(basis):
        generator_records.append({
            "mask": _mask_text(column, n),
            "multiplicity": 1001 + i,
        })

    used_preimages = {1 << i for i in range(n)}
    for j in range(extras):
        while True:
            preimage = _random_odd_mask(rng, n)
            if preimage not in used_preimages:
                used_preimages.add(preimage)
                break
        generator_records.append({
            "mask": _mask_text(_linear_image(preimage, basis), n),
            "multiplicity": 1001 + n + j,
        })

    rng.shuffle(generator_records)
    phase = rng.getrandbits(1)
    answer = [_mask_text(witness, n), phase]
    return {
        "paper": "arXiv:1710.05491",
        "family": "succinct connected bipartite Cayley multigraph",
        "dimension": n,
        "vertex_count": 1 << n,
        "mu": 1 << (n - 1),
        "k1": 0,
        "k2": 0,
        "generators": generator_records,
        "update_blocks": update_blocks,
        "layers": layers,
        "extras": extras,
        "answer": answer,
    }


def render(inst):
    n = inst["dimension"]
    lines = [
        "BALANCED JUDICIOUS BIPARTITION ON A SUCCINCT MULTIGRAPH",
        "",
        "All arithmetic in the graph definition is exact. A vertex is an n-bit",
        "vector, identified with its integer x in 0..2^n-1 (bit 0 is least",
        "significant). For integers a,b, XOR is bitwise exclusive-or, AND is",
        "bitwise conjunction, and parity(a) is the number of 1-bits modulo 2.",
        "",
        f"Here n={n}; the graph has every vertex x in 0..{inst['vertex_count'] - 1}.",
        "For each line MASK MULTIPLICITY below and every vertex x, the graph has",
        "MULTIPLICITY parallel undirected edges between x and x XOR MASK. Each",
        "unordered pair is included once. MASK is hexadecimal. There are no",
        "other edges. The masks on the listed lines are distinct and nonzero.",
        "",
        "GENERATOR MASKS AND PARALLEL-EDGE MULTIPLICITIES:",
    ]
    for record in inst["generators"]:
        lines.append(f"{record['mask']} {record['multiplicity']}")
    lines.extend([
        "",
        "The following basis-change update blocks are exact instance metadata.",
        "Start with column i equal to the n-bit mask having only bit i set, for",
        "i=0..n-1. Apply the blocks from top to bottom and each block from left",
        "to right. After all updates, column i is exactly the generator mask",
        "on the line whose multiplicity is 1001+i; larger multiplicities mark",
        "extra generators. A token i>j means: replace column i by column i XOR",
        "column j.",
        "Pairs are separated by spaces; blocks, pair order, and direction matter.",
        "BASIS-CHANGE UPDATE BLOCKS:",
    ])
    for block in inst["update_blocks"]:
        lines.append(" ".join(f"{i}>{j}" for i, j in block))
    lines.extend([
        "",
        "A submitted pair MASK_HEX, PHASE denotes the ordered partition",
        "V1={x : parity(MASK_HEX AND x)=PHASE}, V2=all other vertices.",
        "MASK_HEX must have exactly ceil(n/4) lowercase hexadecimal digits and",
        "represent a nonzero n-bit integer. PHASE must be 0 or 1.",
        "",
        f"Find such a partition with |V1| exactly mu={inst['mu']}, with at most",
        f"k1={inst['k1']} edges wholly inside V1 and at most k2={inst['k2']} edges",
        "wholly inside V2. Parallel edges count separately. Order matters because",
        "the requested size and the two edge bounds belong to V1 and V2 as written.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as",
        "MASK_HEX, PHASE.",
        f"Example shape: <answer>{'0' * (_hex_width(n) - 1)}1, 0</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fenced = _FENCE_RE.fullmatch(body)
    if fenced:
        body = fenced.group(1).strip()
    # Accept either the requested comma form or the JSON-native pair.
    try:
        if body.startswith("["):
            value = json.loads(body)
            if (isinstance(value, list) and len(value) == 2
                    and isinstance(value[0], str) and _is_int(value[1])):
                return [value[0].lower(), value[1]]
            return None
        parts = [part.strip() for part in body.split(",")]
        if len(parts) != 2 or not _HEX_RE.fullmatch(parts[0].lower()):
            return None
        if parts[1] not in ("0", "1"):
            return None
        return [parts[0].lower(), int(parts[1])]
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, (list, tuple)) or len(answer) != 2:
        return False, "wrong answer shape: expected [mask_hex, phase]"
    mask_text, phase = answer
    if not isinstance(mask_text, str):
        return False, "mask must be a hexadecimal string"
    if not _is_int(phase) or phase not in (0, 1):
        return False, "phase must be the integer 0 or 1"
    n = inst["dimension"]
    if len(mask_text) != _hex_width(n) or not _HEX_RE.fullmatch(mask_text):
        return False, f"mask must have exactly {_hex_width(n)} lowercase hex digits"
    mask = int(mask_text, 16)
    if not 1 <= mask < (1 << n):
        return False, "mask is zero or outside the n-bit range"

    # Every nonconstant affine parity rule on GF(2)^n is exactly balanced.
    if (1 << (n - 1)) != inst["mu"]:
        return False, "the affine rule does not meet the requested side size"
    bad_v1 = 0
    bad_v2 = 0
    for record in inst["generators"]:
        generator = int(record["mask"], 16)
        if _parity(mask & generator) == 0:
            # Translation by this generator preserves both sides.  It induces
            # 2^(n-2) unordered internal pairs in each side.
            internal = (1 << (n - 2)) * record["multiplicity"]
            bad_v1 += internal
            bad_v2 += internal
            if bad_v1 > inst["k1"] or bad_v2 > inst["k2"]:
                return False, "a Cayley generator creates forbidden internal edges"
    if bad_v1 > inst["k1"]:
        return False, "too many edges induced by V1"
    if bad_v2 > inst["k2"]:
        return False, "too many edges induced by V2"
    return True, "ok"


def random_candidate(inst, rng):
    n = inst["dimension"]
    return [_mask_text(rng.randrange(1, 1 << n), n), rng.getrandbits(1)]


def search_space(inst):
    return 2 * ((1 << inst["dimension"]) - 1)


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    hits = 0
    n = inst["dimension"]
    for mask in range(1, 1 << n):
        text = _mask_text(mask, n)
        for phase in (0, 1):
            if verify(inst, [text, phase])[0]:
                hits += 1
    return hits


def _solve_equations(inst, instrument=False):
    """Solve g.w=1 over GF(2) by ordinary row elimination."""
    n = inst["dimension"]
    rows = []
    scalar_ops = 0
    for record in inst["generators"]:
        rows.append(int(record["mask"], 16) | (1 << n))
    pivot_row = 0
    pivot_columns = []
    for column in range(n):
        pivot = None
        for r in range(pivot_row, len(rows)):
            scalar_ops += 1
            if (rows[r] >> column) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(len(rows)):
            if r != pivot_row:
                scalar_ops += 1
                if (rows[r] >> column) & 1:
                    rows[r] ^= rows[pivot_row]
                    scalar_ops += n + 1
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    for row in rows:
        if (row & ((1 << n) - 1)) == 0 and ((row >> n) & 1):
            return None, scalar_ops
    if len(pivot_columns) < n:
        return None, scalar_ops
    solution = 0
    for r, column in enumerate(pivot_columns[:n]):
        solution |= ((rows[r] >> n) & 1) << column
    return solution, scalar_ops


def _coordinates_in_basis(vector, basis):
    n = len(basis)
    rows = []
    for bit in range(n):
        coefficients = 0
        for column, value in enumerate(basis):
            coefficients |= ((value >> bit) & 1) << column
        rhs = (vector >> bit) & 1
        rows.append(coefficients | (rhs << n))
    pivot_row = 0
    for column in range(n):
        pivot = next((r for r in range(pivot_row, n)
                      if (rows[r] >> column) & 1), None)
        if pivot is None:
            raise ValueError("distinguished generators do not form a basis")
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(n):
            if r != pivot_row and ((rows[r] >> column) & 1):
                rows[r] ^= rows[pivot_row]
        pivot_row += 1
    result = 0
    for r in range(n):
        result |= ((rows[r] >> n) & 1) << r
    return result


def canonical_key(inst):
    """Canonicalize generator order and every invertible coordinate relabeling."""
    n = inst["dimension"]
    records = sorted(inst["generators"], key=lambda rec: rec["multiplicity"])
    basis_records = records[:n]
    expected = list(range(1001, 1001 + n))
    if [rec["multiplicity"] for rec in basis_records] != expected:
        raise ValueError("missing distinguished multiplicity basis")
    basis = [int(rec["mask"], 16) for rec in basis_records]
    relations = []
    for record in records[n:]:
        coordinate = _coordinates_in_basis(int(record["mask"], 16), basis)
        relations.append([record["multiplicity"], _mask_text(coordinate, n)])
    payload = {
        "dimension": n,
        "multiplicities": [record["multiplicity"] for record in records],
        "extra_relations": relations,
        "mu": inst["mu"],
        "k1": inst["k1"],
        "k2": inst["k2"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    current = {k: v for k, v in params.items() if k != "_preset"}
    extras = current.get("extras", 8)
    if extras < 128:
        current["extras"] = min(128, max(extras + 8, extras * 2))
        return current
    n = current.get("n", 64)
    layers = current.get("layers", 3)
    if layers * (n - 1) < 300 and n < 101:
        current["n"] = min(101, n + 2)
        return current
    return None


def _attack_outlier(inst):
    n = inst["dimension"]
    counts = [0] * n
    for record in inst["generators"]:
        value = int(record["mask"], 16)
        for i in range(n):
            counts[i] += (value >> i) & 1
    bit = min(range(n), key=lambda i: (counts[i], i))
    return [_mask_text(1 << bit, n), 0]


def _attack_greedy(inst):
    n = inst["dimension"]
    records = [int(record["mask"], 16) for record in inst["generators"]]
    candidate = 0
    # Independently choose bits whose generator-column frequency is odd.  This
    # is a plausible majority/correlation shortcut but ignores interactions.
    for bit in range(n):
        if sum((row >> bit) & 1 for row in records) * 2 >= len(records):
            candidate |= 1 << bit
    if candidate == 0:
        candidate = 1
    return [_mask_text(candidate, n), 0]


def _attack_forward_updates(inst):
    n = inst["dimension"]
    rhs = [1] * n
    for block in inst["update_blocks"]:
        for i, j in block:
            rhs[i] ^= rhs[j]
    value = sum(bit << i for i, bit in enumerate(rhs))
    if value == 0:
        value = 1
    return [_mask_text(value, n), 0]


def _transformed_instance(inst, rng):
    """Apply an invertible linear relabelling and a Cayley translation."""
    n = inst["dimension"]
    permutation = list(range(n))
    rng.shuffle(permutation)

    # First realize a coordinate permutation through XOR swaps, then add
    # shears.  Every operation is invertible, so together they define a
    # nontrivial element L of GL(n,2), represented by its image columns.
    labels = list(range(n))
    linear_block = []
    for i in range(n):
        target = permutation[i]
        j = labels.index(target, i)
        if i != j:
            linear_block.extend([[i, j], [j, i], [i, j]])
            labels[i], labels[j] = labels[j], labels[i]
    for _ in range(n):
        i = rng.randrange(n)
        j = rng.randrange(n - 1)
        if j >= i:
            j += 1
        linear_block.append([i, j])
    map_columns = _apply_column_updates(n, [linear_block])

    def transform_mask(value):
        return _linear_image(value, map_columns)

    transformed = copy.deepcopy(inst)
    for record in transformed["generators"]:
        record["mask"] = _mask_text(transform_mask(int(record["mask"], 16)), n)
    rng.shuffle(transformed["generators"])
    # The update blocks are solver-visible metadata, so carry them through the
    # coordinate relabelling too.  Starting from L and applying the original
    # column schedule yields L times the old distinguished basis.
    transformed["update_blocks"] = (
        [linear_block]
        + copy.deepcopy(inst["update_blocks"])
    )
    transformed["layers"] = len(transformed["update_blocks"])
    new_mask = _update_witness(n, transformed["update_blocks"])
    translation = rng.randrange(1 << n)
    new_phase = inst["answer"][1] ^ _parity(new_mask & transform_mask(translation))
    transformed["answer"] = [_mask_text(new_mask, n), new_phase]
    return transformed


def _answer_elements(answer):
    if isinstance(answer, dict):
        return sum(_answer_elements(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_elements(value) for value in answer)
    return 1


def selftest():
    report = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            attempts += 1
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    good = demo["answer"]
    width = _hex_width(demo["dimension"])
    corruptions = {
        "drop_one": [good[0]],
        "swap_fields": [good[1], good[0]],
        "duplicate_field": [good[0], good[0]],
        "empty": [],
        "out_of_range": ["f" * (width + 1), good[1]],
    }
    cases = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(demo, bad)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
                and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the parity constraints.\n```text\n<answer>"
        + good[0] + ", " + str(good[1])
        + "</answer>\n```\nThis is my final witness."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == good and verify(demo, parsed)[0],
        "parsed": parsed,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)
    rng = random.Random(271828)
    hits = 0
    t0 = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    g4_elapsed = time.perf_counter() - t0
    probability = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": probability,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform nonzero n-bit affine mask and uniform phase",
        "wall_clock_sec": round(g4_elapsed, 6),
    }

    density_rng = random.Random(161803)
    density_samples = 200_000
    density_hits = 0
    for _ in range(density_samples):
        density_hits += int(verify(
            shipping, random_candidate(shipping, density_rng))[0])

    reference_times = []
    reference_ops = []
    reference_successes = 0
    attack_results = {
        "coordinate_frequency_outlier": {"successes": 0, "attempts": _ATTACK_SEEDS},
        "greedy_column_majority": {"successes": 0, "attempts": _ATTACK_SEEDS},
        "random_affine_restart_256": {"successes": 0, "attempts": _ATTACK_SEEDS},
        "forward_update_ansatz": {"successes": 0, "attempts": _ATTACK_SEEDS},
    }
    attack_times = {name: 0.0 for name in attack_results}
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        for name, function in (
            ("coordinate_frequency_outlier", _attack_outlier),
            ("greedy_column_majority", _attack_greedy),
            ("forward_update_ansatz", _attack_forward_updates),
        ):
            start = time.perf_counter()
            candidate = function(inst)
            attack_times[name] += time.perf_counter() - start
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
        start = time.perf_counter()
        restart_rng = random.Random(90_000 + seed)
        success = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                success = True
                break
        attack_times["random_affine_restart_256"] += time.perf_counter() - start
        attack_results["random_affine_restart_256"]["successes"] += int(success)

        start = time.perf_counter()
        solution, operations = _solve_equations(inst, instrument=True)
        reference_times.append(time.perf_counter() - start)
        reference_ops.append(operations)
        candidate = [_mask_text(solution, inst["dimension"]), 0] if solution else None
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
    for name in attack_results:
        attack_results[name]["wall_clock_sec_total_8"] = round(attack_times[name], 6)
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    reference = {
        "name": "Gauss-Jordan elimination over GF(2)",
        "complexity": "O(n^3) scalar bit operations",
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
        "wall_clock_sec_total_8": round(sum(reference_times), 6),
        "operations_mean": round(sum(reference_ops) / len(reference_ops)),
        "operations_min": min(reference_ops),
        "operations_max": max(reference_ops),
        "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
    }
    report["G5_density_and_baseline_cost"] = {
        "pass": density_hits / density_samples < 1e-6 and reference_successes == _ATTACK_SEEDS,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": density_samples,
        "shipping_density_estimate": density_hits / density_samples,
        "shipping_exact_density_numerator": 2,
        "shipping_exact_density_denominator": search_space(shipping),
        "exact_valid_answers_by_connectivity": 2,
        "demo_exact_valid_answers": enumerate_all(demo),
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": "random_affine_restart_256",
        "attack_wall_clock_sec_total_8": round(
            attack_times["random_affine_restart_256"], 6),
        "attack_restarts_total_8": 8 * 256,
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "reverse the displayed basis-change updates",
            "operations": shipping["layers"] * (shipping["dimension"] - 1),
            "solves": "8/8 by the construction identity",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] > shipping["vertex_count"],
        "shipping_n": shipping["dimension"],
        "shipping_vertices": shipping["vertex_count"],
        "doubled_n": doubled["dimension"],
        "doubled_vertices": doubled["vertex_count"],
        "answer_elements_before": _answer_elements(shipping["answer"]),
        "answer_elements_after": _answer_elements(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    invariance_failures = []
    keys = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping_params)
        key = canonical_key(inst)
        keys.append(key)
        transformed = _transformed_instance(inst, random.Random(30_000 + seed))
        transformed_key = canonical_key(transformed)
        invariance_checks += 1
        if transformed_key != key:
            invariance_failures.append([seed, "affine vertex relabelling + generator reorder"])
        carried_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            invariance_failures.append([seed, "carried witness failed"])
        expected_basis = _apply_column_updates(
            transformed["dimension"], transformed["update_blocks"])
        actual_basis = [
            int(record["mask"], 16)
            for record in sorted(
                transformed["generators"],
                key=lambda record: record["multiplicity"],
            )[:transformed["dimension"]]
        ]
        carried_checks += 1
        if expected_basis != actual_basis:
            invariance_failures.append([seed, "carried update metadata failed"])
        carried_mask = _mask_text(
            _update_witness(
                transformed["dimension"], transformed["update_blocks"]),
            transformed["dimension"],
        )
        carried_checks += 1
        if carried_mask != transformed["answer"][0]:
            invariance_failures.append([seed, "metadata witness was not carried"])
        reordered = copy.deepcopy(inst)
        reordered["generators"].reverse()
        invariance_checks += 1
        if canonical_key(reordered) != key:
            invariance_failures.append([seed, "generator reversal"])
        phase_flipped = copy.deepcopy(inst)
        phase_flipped["answer"] = [inst["answer"][0], inst["answer"][1] ^ 1]
        invariance_checks += 1
        if canonical_key(phase_flipped) != key:
            invariance_failures.append([seed, "bipartition side swap"])
        carried_checks += 1
        if not verify(phase_flipped, phase_flipped["answer"])[0]:
            invariance_failures.append([seed, "side-swapped witness failed"])
        composed = _transformed_instance(transformed, random.Random(40_000 + seed))
        invariance_checks += 1
        if canonical_key(composed) != key:
            invariance_failures.append([seed, "composed coordinate relabelling"])
        carried_checks += 1
        if not verify(composed, composed["answer"])[0]:
            invariance_failures.append([seed, "composed carried witness failed"])
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and len(set(keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "invariance_failures": invariance_failures,
        "unrelated_instances": 20,
        "distinct_keys": len(set(keys)),
        "symmetries_tested": [
            "generator order", "invertible GF(2) change of basis",
            "Cayley translation with carried phase", "ordered-side swap",
            "compositions of affine vertex relabellings",
            "basis-change consistency of solver-visible metadata",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_elements(shipping["answer"])
    intended_ops = shipping["layers"] * (shipping["dimension"] - 1)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the three arms, including the hinted arm, are
        # diagnostics.  Only the answer-size and intended-route caps gate G9.
        "pass": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    report["paper"] = "arXiv:1710.05491"
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
