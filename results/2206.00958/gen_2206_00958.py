"""Verified problem generator grounded in arXiv:2206.00958.

Section 2 of the paper uses the finite-field Hilbert--90 equation
``x^q + x = c`` and explains that its kernel and translates control the
derivative systems of biprojective APN maps.  This module presents that native
linearized-polynomial equation in a shuffled normal basis after a nonsingular
rank-one mixing of its output coordinates.

The witness is sampled first.  The right-hand side is then evaluated and
mixed, so generation never solves the displayed system.  Verification is an
exact GF(2) matrix-vector multiplication and accepts either construction's
witness or any other valid normalized field element.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time


# Keep the repository helpers importable when harden.py is run in this folder.
# This family needs only integer bit operations, and therefore has a complete
# standard-library fallback.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - deliberately supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "GF(2^n) element in a normal basis",
        "q-Frobenius linearized polynomial x^q+x",
        "rank-one output-mixed coordinate equations over GF(2)",
    ],
    "verification_operations": [
        "exact GF(2) parity",
        "exact binary matrix-vector multiplication",
        "normal-basis coordinate normalization",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Relative to the normal-basis Frobenius cycle, the displayed operator "
        "has one repeated rank-one discrepancy; removing it turns the solve "
        "into a single cyclic XOR recurrence instead of dense elimination."
    ),
    "hardness_basis": (
        "Track B: Section 2.1's passage following Lemma 2.4 (Hilbert's "
        "Theorem 90) reduces "
        "linearized-polynomial kernels and translates to x^q-x; generic exact "
        "Gaussian elimination is O(n^3) and at the tested cap edge n=59 averaged "
        "38,445 counted bit operations and about 0.0004 seconds over eight seeds, "
        "while the repeated-discrepancy change of variables needs at most 293 exact "
        "GF(2) XOR operations after the structure is recognized."
    ),
    "max_answer_tokens": 5,
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


# n is the extension degree.  The answer remains one field element; its entropy
# grows with n.  All k are coprime to n, so the q-Frobenius permutation is one
# cycle and ker(x^q+x)={0,1}.
DIFFICULTY = {
    "demo": {"n": 7, "k": 2},
    "easy": {"n": 55, "k": 13},
    "medium": {"n": 57, "k": 17},
    "hard": {"n": 59, "k": 23},
}
# This is the strongest tested candidate.  The harness recorded cap_bound, so
# it is retained for audit/future larger-cap runs and is not a shipping claim.
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Relative to the normal-basis Frobenius cycle, every altered row has the same rank-one discrepancy mask."
)
PLACEBO_HINT = (
    "The shuffled equation labels and hexadecimal bit order reward especially careful bookkeeping throughout the solve."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One fixed-width lowercase hexadecimal GF(2^n) coordinate word x, "
        "with unused high bits zero and normal-basis coordinate x_0=0."
    ),
    "bounds": {
        "field_elements": 1,
        "hex_width": "ceil(n/4)",
        "value_min": 0,
        "value_max": "2^n-1",
        "normalization": "least significant bit x_0 is zero",
        "candidate_count": "2^(n-1)",
    },
}

NOTES = (
    "Section 2 fixes the definitions used here: q=2^k, L=GF(2^n), the trace "
    "map, Hilbert's Theorem 90, and GF(2)-linearized polynomials.  The paragraph "
    "after Lemma 2.4 says explicitly that kernels and translates of a*x^q-b*x "
    "reduce to x^q-x; that is the result making Track A false and Track B "
    "appropriate.  Lemma 2.5(i) gives gcd(2^k-1,2^n-1)=1 when gcd(k,n)=1, "
    "so the kernel has two elements; x_0=0 selects exactly one.  Lemma 2.3 "
    "is where these linearized systems characterize APN derivatives, and "
    "Section 2.3 records output-side GF(2)-linear equivalence.  The generator "
    "samples that normalized element before evaluating x^q+x and applies the "
    "invertible transvection M=I+u*v^T with v^T*u=0.  The repeated discrepancy "
    "in B+(Frobenius+I) exposes a compact change of variables without exposing "
    "the answer.  Dense-row voting, direct-RHS, un-mixed-cycle, display-order "
    "greedy, and random-restart attacks are audited; random dense masks, even "
    "nonconstant u, and shuffled rows remove their construction signatures.  "
    "The script-owned oracle loop solved one of three n=59 instances; raising n "
    "would exceed the 300-operation intended-route cap, so the final verdict is "
    "cap_bound and this retained module is not a shipping hardness claim."
)


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_GUESS_SAMPLES = 200_000

# Filled from the three script-owned hardening runs after the shipping rung is
# known.  These arms are diagnostics; G9's gate is only the size/effort cap.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 1, "attempts": 3, "service_errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "service_errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "service_errors": 0},
    "hinted_verdict": "not_run_after_cap_bound",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _width(n):
    return (n + 3) // 4


def _encode(value, n):
    return format(value, f"0{_width(n)}x")


def _compact_operation_bound(n):
    """Conservative exact-arithmetic count after spotting the rank-one pattern.

    Two bit toggles recover the repeated discrepancy from one altered row.  Two
    cyclic recurrences and two parity reductions cost four times (n-1) XORs;
    conditionally unmixing the right-hand side costs at most n more XORs.
    Row recognition/comparison and transcription are not arithmetic operations.
    """
    return 2 + 4 * (n - 1) + n


def _base_rows(n, k):
    """Rows of x -> x^(2^k)+x in normal-basis exponent order."""
    return [(1 << j) | (1 << ((j - k) % n)) for j in range(n)]


def _matvec(rows, value):
    out = 0
    for i, row in enumerate(rows):
        out |= ((row & value).bit_count() & 1) << i
    return out


def _dot(left, right):
    return (left & right).bit_count() & 1


def _sample_dense_mask(rng, n, *, even=None):
    """Sample a nonconstant mask with no conspicuous Hamming-weight outlier."""
    lower = max(2, n // 3)
    upper = min(n - 2, (2 * n) // 3)
    while True:
        value = rng.getrandbits(n)
        weight = value.bit_count()
        if not lower <= weight <= upper:
            continue
        if even is not None and (weight & 1) != (0 if even else 1):
            continue
        return value


def make_instance(n, seed=0, **params):
    """Inverse-generate one mixed Hilbert--90 equation and its witness."""
    if not _is_int(n) or n < 7:
        raise ValueError("n must be an integer at least 7")
    k = params.pop("k", 1)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(k) or not 0 < k < n:
        raise ValueError("k must be an integer with 0 < k < n")
    if math.gcd(k, n) != 1:
        raise ValueError("gcd(k,n) must be 1")

    rng = random.Random(seed)
    limit = (1 << n) - 1

    # The certificate is selected first, with x_0=0 fixing the two-element
    # Hilbert--90 kernel ambiguity.  Exclude only a few degenerate display cases.
    while True:
        witness = rng.getrandbits(n) & ~1
        if 2 <= witness.bit_count() <= n - 2:
            break

    sparse_rows = _base_rows(n, k)
    canonical_rhs = _matvec(sparse_rows, witness)

    # M=I+u*v^T is invertible over GF(2) exactly when v^T u=0.  Taking u of
    # even weight also makes the unavoidable v <-> v+1 ambiguity harmless.
    u = _sample_dense_mask(rng, n, even=True)
    while u == canonical_rhs:
        u = _sample_dense_mask(rng, n, even=True)
    while True:
        v = _sample_dense_mask(rng, n)
        # Two independent linear conditions: M must be invertible and the
        # rank-one correction must actually be active.  Conditioning on the
        # latter prevents the obvious "ignore the mixing" ansatz from solving
        # half the instances.
        if _dot(u, v) == 0 and _dot(canonical_rhs, v) == 1 and v not in (0, limit):
            discrepancy = 0
            for j, row in enumerate(sparse_rows):
                if (v >> j) & 1:
                    discrepancy ^= row
            if discrepancy:
                break

    mixed_rows = [
        row ^ (discrepancy if ((u >> i) & 1) else 0)
        for i, row in enumerate(sparse_rows)
    ]
    mixed_rhs = canonical_rhs ^ u

    order = list(range(n))
    rng.shuffle(order)
    equations = [
        {
            "label": i,
            "mask": mixed_rows[i],
            "rhs": (mixed_rhs >> i) & 1,
        }
        for i in order
    ]

    return {
        "family": "rank-one mixed Hilbert-90 equation",
        "n": n,
        "k": k,
        "q": 1 << k,
        "equations": equations,
        "answer": _encode(witness, n),
    }


def render(inst):
    n, k = inst["n"], inst["k"]
    width = _width(n)
    rows = "\n".join(
        f"  r{eq['label']:0{len(str(n - 1))}d}: {eq['rhs']} | "
        f"{eq['mask']:0{width}x}"
        for eq in inst["equations"]
    )
    statement = f"""Solve an exact output-mixed Hilbert--90 equation over GF(2^{n}).

Let L=GF(2^{n}) and choose a normal basis
  beta_e = theta^(2^e),  e=0,...,{n - 1},
where exponent labels are reduced modulo {n}.  Thus raising a field element to
q=2^{k} moves normal-basis coordinates around the single cycle e -> e+{k}
(mod {n}); gcd({k},{n})=1.  The linearized polynomial from finite-field
Hilbert 90 is T(x)=x^q+x.  Its kernel is {{0,1}}, and in a normal basis the
coordinate word of 1 is all ones.

Write x=sum_e x_e beta_e with x_e in GF(2).  An unknown nonsingular linear
change of OUTPUT coordinates has been applied to T(x)=c.  The resulting exact
binary system Bx=d is printed below.  This output mixing changes no solution.
The rows are deliberately shuffled; labels r0,...,r{n - 1} identify their
unshuffled output coordinates.

Each line has the form "row-label: rhs | mask".  A mask is exactly {width}
hexadecimal digits.  Bit e of its integer value (least significant bit is bit
0) is the coefficient of x_e.  A row is satisfied when the parity of the
selected x_e equals rhs.  There are no omitted or implicit rows.

{rows}

Find the unique solution normalized by x_0=0.  Return x as exactly {width}
lowercase hexadecimal digits encoding the integer sum_e x_e*2^e.  Leading
zeros are required; unused high bits (if any) are zero.  The row order is not
the coordinate order, and hexadecimal bit 0 is the least significant bit.

Give your final answer inside <answer></answer> tags, as that one hexadecimal word.
Example format: <answer>{'0' * width}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the last tagged hexadecimal word, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    matches = _TAG_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:text|txt)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
        body = body.strip()
    if not body or _HEX_RE.fullmatch(body) is None:
        return None
    return body.lower()


def verify(inst, answer):
    """Check any normalized solution exactly; never consult inst['answer']."""
    if not isinstance(answer, str):
        return False, "answer must be one hexadecimal string"
    if answer == "":
        return False, "answer must not be empty"
    width = _width(inst["n"])
    if len(answer) < width:
        return False, f"answer is missing hexadecimal digits (expected {width})"
    if len(answer) > width:
        return False, f"answer has extra hexadecimal digits (expected {width})"
    if _HEX_RE.fullmatch(answer) is None:
        return False, "answer contains a non-hexadecimal character"
    value = int(answer, 16)
    if value >= (1 << inst["n"]):
        return False, "unused high bits must be zero"
    if value & 1:
        return False, "normalization x_0=0 is violated"
    for eq in inst["equations"]:
        got = _dot(eq["mask"], value)
        if got != eq["rhs"]:
            return False, f"equation r{eq['label']} has parity {got}, expected {eq['rhs']}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the stated normalized field-element language."""
    value = rng.getrandbits(inst["n"]) & ~1
    return _encode(value, inst["n"])


def search_space(inst):
    return 1 << (inst["n"] - 1)


def enumerate_all(inst):
    total = search_space(inst)
    if total > 200_000:
        return None
    count = 0
    for tail in range(total):
        count += int(verify(inst, _encode(tail << 1, inst["n"]))[0])
    return count


def _ordered_system(inst):
    rows = [None] * inst["n"]
    rhs = 0
    for eq in inst["equations"]:
        label = eq["label"]
        if not _is_int(label) or not 0 <= label < inst["n"] or rows[label] is not None:
            return None, None
        rows[label] = eq["mask"]
        rhs |= (eq["rhs"] & 1) << label
    if any(row is None for row in rows):
        return None, None
    return rows, rhs


def _gaussian_reference(inst):
    """Generic exact solve with measured pivot/row/bit operation counts."""
    n = inst["n"]
    rows = []
    for eq in inst["equations"]:
        rows.append(eq["mask"] | ((eq["rhs"] & 1) << n))
    # The public normalization makes the rank-(n-1) Hilbert map unique.
    rows.append(1)  # x_0=0, augmented RHS already zero
    pivot_row = 0
    pivot_tests = 0
    row_xors = 0
    for col in range(n):
        pivot = None
        for r in range(pivot_row, len(rows)):
            pivot_tests += 1
            if (rows[r] >> col) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(len(rows)):
            if r != pivot_row:
                pivot_tests += 1
                if (rows[r] >> col) & 1:
                    rows[r] ^= rows[pivot_row]
                    row_xors += 1
        pivot_row += 1
    for row in rows:
        if (row & ((1 << n) - 1)) == 0 and ((row >> n) & 1):
            return None, {
                "pivot_tests": pivot_tests,
                "row_xors": row_xors,
                "bit_operations": pivot_tests + row_xors * (n + 1),
            }
    pivots = {}
    for row in rows:
        coeff = row & ((1 << n) - 1)
        if coeff:
            col = (coeff & -coeff).bit_length() - 1
            pivots[col] = (row >> n) & 1
    if len(pivots) != n:
        return None, {
            "pivot_tests": pivot_tests,
            "row_xors": row_xors,
            "bit_operations": pivot_tests + row_xors * (n + 1),
        }
    value = sum(bit << col for col, bit in pivots.items())
    return _encode(value, n), {
        "pivot_tests": pivot_tests,
        "row_xors": row_xors,
        "bit_operations": pivot_tests + row_xors * (n + 1),
    }


def _cycle_solve(rhs, n, k, *, transpose=False):
    """Solve the normalized one-cycle equation Sx=rhs or S^T x=rhs."""
    value = 0
    current = 0
    for _ in range(n - 1):
        if transpose:
            nxt = (current + k) % n
            bit = ((value >> current) ^ (rhs >> current)) & 1
        else:
            nxt = (current + k) % n
            bit = ((value >> current) ^ (rhs >> nxt)) & 1
        value |= bit << nxt
        current = nxt
    return value


def _compact_solve(inst):
    """Undo the planted transvection and use the Hilbert--90 recurrence."""
    n, k = inst["n"], inst["k"]
    rows, mixed_rhs = _ordered_system(inst)
    if rows is None:
        return None
    sparse = _base_rows(n, k)
    diffs = [row ^ base for row, base in zip(rows, sparse)]
    nonzero = {item for item in diffs if item}
    if len(nonzero) != 1:
        return None
    discrepancy = next(iter(nonzero))
    u = sum((diff == discrepancy) << i for i, diff in enumerate(diffs))
    if not u or (u.bit_count() & 1):
        return None
    # discrepancy = v^T S, so solve S^T v=discrepancy.  Either normalized
    # representative gives the same unmixing scalar because trace(c)=0 and wt(u)
    # is even.
    v = _cycle_solve(discrepancy, n, k, transpose=True)
    if _dot(v, u):
        return None
    canonical_rhs = mixed_rhs ^ (u if _dot(v, mixed_rhs) else 0)
    value = _cycle_solve(canonical_rhs, n, k, transpose=False)
    answer = _encode(value, n)
    return answer if verify(inst, answer)[0] else None


def _rotate_coordinates(value, n, shift):
    """New coordinate e receives old coordinate e+shift (mod n)."""
    out = 0
    for e in range(n):
        out |= ((value >> ((e + shift) % n)) & 1) << e
    return out


def canonical_key(inst):
    """Canonicalize equation-row operations and normal-basis generator shifts."""
    answer, _ = _gaussian_reference(inst)
    if answer is None:
        payload = {
            "n": inst.get("n"),
            "k": inst.get("k"),
            "malformed": sorted(
                (eq.get("mask"), eq.get("rhs")) for eq in inst.get("equations", [])
            ),
        }
    else:
        n = inst["n"]
        value = int(answer, 16)
        full = (1 << n) - 1
        orbit = []
        for shift in range(n):
            rotated = _rotate_coordinates(value, n, shift)
            if rotated & 1:
                rotated ^= full
            orbit.append(rotated)
        payload = {"n": n, "k": inst["k"], "normalized_orbit": min(orbit)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Increase extension degree until G9's 300-operation route cap binds."""
    n = params.get("n")
    if _is_int(n) and 7 <= n < 59:
        candidate = min(59, n + 2)
        k = params.get("k", 1)
        while math.gcd(k, candidate) != 1:
            k += 1
        return {"n": candidate, "k": k}
    return "cap_bound"


def _greedy_display_order(inst):
    """Tempting but wrong: assign the first unassigned bit in each shown row."""
    assigned = 1  # coordinate 0 is fixed
    value = 0
    for eq in inst["equations"]:
        available = eq["mask"] & ~assigned
        if not available:
            continue
        pivot = available & -available
        known_parity = _dot(eq["mask"] & assigned, value)
        if known_parity != eq["rhs"]:
            value |= pivot
        assigned |= pivot
    return _encode(value, inst["n"])


def _attack_candidates(inst, seed):
    n, k = inst["n"], inst["k"]
    rows, rhs = _ordered_system(inst)
    direct = rhs & ~1
    sparse_guess = _cycle_solve(rhs, n, k) & ~1
    discrepancies = [
        row ^ base for row, base in zip(rows, _base_rows(n, k))
    ]
    u_guess = sum(bool(item) << i for i, item in enumerate(discrepancies)) & ~1

    # A per-coordinate dense-row vote, a classic outlier statistic.
    vote = 0
    for col in range(1, n):
        ones = sum(eq["rhs"] for eq in inst["equations"] if (eq["mask"] >> col) & 1)
        total = sum(1 for eq in inst["equations"] if (eq["mask"] >> col) & 1)
        if total and 2 * ones > total:
            vote |= 1 << col

    rng = random.Random(seed ^ 0x220600958)
    restarts = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_dense_row_vote": [_encode(vote, n)],
        "direct_rhs_as_coordinates": [_encode(direct, n)],
        "greedy_display_order": [_greedy_display_order(inst)],
        "obvious_unmixed_cycle_ansatz": [_encode(sparse_guess, n)],
        "discrepancy_indicator_ansatz": [_encode(u_guess, n)],
        "random_restart_256": restarts,
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    n = inst["n"]
    row_perm = list(range(n))
    rng.shuffle(row_perm)
    shift = rng.randrange(1, n)
    variants = []
    for flags in range(1, 8):
        out = {
            "family": inst["family"],
            "n": n,
            "k": inst["k"],
            "q": inst["q"],
            "equations": [dict(eq) for eq in inst["equations"]],
            "answer": inst["answer"],
        }
        if flags & 1:
            out["equations"] = [out["equations"][i] for i in row_perm]
        if flags & 2:
            # One invertible elementary output-coordinate operation.
            a, b = 0, 1
            out["equations"][a]["mask"] ^= out["equations"][b]["mask"]
            out["equations"][a]["rhs"] ^= out["equations"][b]["rhs"]
        if flags & 4:
            value = _rotate_coordinates(int(out["answer"], 16), n, shift)
            complement = bool(value & 1)
            if complement:
                value ^= (1 << n) - 1
            for eq in out["equations"]:
                eq["mask"] = _rotate_coordinates(eq["mask"], n, shift)
                if complement:
                    eq["rhs"] ^= eq["mask"].bit_count() & 1
            out["answer"] = _encode(value, n)
        variants.append(out)
    return variants


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "construction": "sample normalized x, evaluate x^q+x, then apply M=I+uv^T",
    }

    inst = make_instance(seed=29, **shipping)
    answer = inst["answer"]
    value = int(answer, 16)
    bits = [i for i in range(1, inst["n"]) if (value >> i) & 1]
    zeros = [i for i in range(1, inst["n"]) if not ((value >> i) & 1)]
    swapped_value = value ^ (1 << bits[0]) ^ (1 << zeros[0])
    corruptions = {
        "drop": answer[:-1],
        "swap": _encode(swapped_value, inst["n"]),
        "duplicate": answer + answer[-1],
        "empty": "",
        "out_of_range": _encode(1 << inst["n"], inst["n"]),
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The normal-basis recurrence gives the following field element.\n"
        "```text\n<answer>" + answer.upper() + "</answer>\n```\n"
        "The word has the required leading zeros."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x220600958)
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(inst),
        "space_bits": inst["n"] - 1,
        "sampling_prior": "uniform normalized GF(2^n) words with x_0=0",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = list(_attack_candidates(inst, 0))
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_counts = {"pivot_tests": 0, "row_xors": 0, "bit_operations": 0}
    compact_successes = 0
    compact_seconds = 0.0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        for key in reference_counts:
            reference_counts[key] += counts[key]
        start = time.perf_counter()
        compact = _compact_solve(trial)
        compact_seconds += time.perf_counter() - start
        compact_successes += int(compact is not None and verify(trial, compact)[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact GF(2) Gaussian elimination with normalization row",
        "complexity": "O(n^3) bit operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_counts["bit_operations"] // 8,
        "pivot_tests": reference_counts["pivot_tests"] // 8,
        "row_xors": reference_counts["row_xors"] // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(count == 0 for count in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "rank-one unmixing plus one Frobenius-cycle recurrence",
            "solves": f"{compact_successes}/8",
            "wall_clock_sec": round(compact_seconds / 8, 6),
            "operations_upper_bound": _compact_operation_bound(inst["n"]),
            "operation_model": (
                "2 discrepancy-bit toggles + 4(n-1) recurrence/parity XORs "
                "+ n RHS-unmixing XORs; row recognition is comparison, not arithmetic"
            ),
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8
        and compact_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": _GUESS_SAMPLES,
        "shipping_solution_density": guess_fraction,
        "exact_shipping_density": f"1/2^{inst['n'] - 1} (unique normalized solution)",
        "demo_exact_solution_count": demo_count,
        "baseline_attack": "random_restart_256",
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    while math.gcd(doubled_params["k"], doubled_params["n"]) != 1:
        doubled_params["k"] += 1
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst) ** 2 // 2
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "space_bits_shipping": inst["n"] - 1,
        "space_bits_doubled": doubled["n"] - 1,
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "displayed equation-row reordering",
            "invertible elementary output-row addition",
            "cyclic change of normal-basis generator with carried normalization",
            "all nonempty compositions of those three",
        ],
    }

    answer_chars = len(json.dumps(answer, separators=(",", ":")))
    answer_tokens = math.ceil(answer_chars / 4)
    worst_chars = _width(inst["n"]) + 2
    worst_tokens = math.ceil(worst_chars / 4)
    intended_operations = _compact_operation_bound(inst["n"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    within_caps = (
        answer_chars <= 2_000
        and 1 <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": 1,
        "semantic_field_coordinates": inst["n"],
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
