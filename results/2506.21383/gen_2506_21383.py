"""Verified generator for short zero-sum subsequences in ``C_q x C_q``.

The mathematical object is exactly the sequence over a finite abelian group
used in Definition 1.1 of arXiv:2506.21383.  The module is deterministic for a
fixed ``(n, seed, params)`` tuple, uses only the standard library, and performs
no file or network I/O.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, localcontext
import hashlib
import json
import math
import random
import re
import time
from typing import Any


NATIVE = {
    "domain": "number_theory",
    "core": "subset_sum",
    "objects": ["sequence over C_q direct-sum C_q", "index subsequence"],
    "intuition": "zero-sum modular cancellation",
    "reduction": None,
}


DIFFICULTY = {
    "demo": {"n": 8},
    "easy": {"n": 64},
    "medium": {"n": 96},
    "hard": {"n": 128},
}

SHIPPING_DIFFICULTY = "easy"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list representing any nonempty subset of the n labelled sequence "
        "positions: 1 through n distinct 0-based integer indices, in arbitrary "
        "order. Since the instance has q > n and its stated length bound is q, "
        "every nonempty index subset has the required shape."
    ),
    "bounds": {
        "min_items": 1,
        "max_items_parameter": "n",
        "max_n": 384,
        "index_min": 0,
        "index_max_parameter": "n-1",
        "repetitions": 0,
    },
}


NOTES = r"""
Definition source: Section 1, Definition 1.1 defines s_{<=k}(G) through a
nonempty subsequence of a sequence over a finite abelian group whose sum is
zero and whose length is at most k. Section 2 fixes sequences as elements of
the free abelian monoid F(G), so equal group elements at different positions
remain different selectable occurrences. This module exposes exactly those
native objects: labelled occurrences of pairs modulo q and an index witness.

Parameter regime: G=C_q direct-sum C_q, exp(G)=q, D(G)=2q-1, and the requested
bound is k=q. Thus the family lies in the paper's studied interval
[exp(G),D(G)-1]. Lemma 1.5 gives s_{<=q}(G)=3q-2 for rank two. Our sequence has
n<q, far below that universal-existence threshold, so the paper's theorem does
not hand the solver a construction; satisfiability comes only from inverse
generation. The paper also states that k>=D(G) collapses to the ordinary
Davenport constant, and records solved small/fixed regimes in Lemma 1.7. We
avoid both by keeping k=q<D(G), growing n, and making q exponential in n.

Hardness qualification: the paper is extremal additive combinatorics, not a
complexity paper, and proves no average-case hardness claim for this planted
distribution. The underlying search relation is modular SUBSET SUM: when the
modulus is binary encoded, ordinary SUBSET SUM reduces to a zero-sum sequence
by adjoining -T modulo a modulus larger than the sum of the positive inputs.
The generated distribution is placed near critical density: log2(|G|) is just
below n, so exhaustive meet-in-the-middle remains exponential while the
classical low-density LLL guarantee does not apply. This is empirical rather
than a reduction preserving this particular random distribution.

Planting defenses: the witness positions are sampled before any instance data.
Conditional on them, their values are drawn uniformly from nonzero tuples with
sum zero; decoys are uniform nonzero tuples too. The dependent position is
chosen uniformly within the planted subset and the whole list is shuffled in
effect by the initially uniform position choice. Thus no position or one-item
statistic identifies the plant. We reject only zero entries, duplicates, and
opposite pairs, symmetrically over the whole sequence, to remove accidental
one- and two-term answers. The adversary panel tests centered-norm outliers, a
modular-distance greedy rule, local-search restarts, bounded meet-in-the-middle,
and a construction-aware centered lattice embedding reduced by LLL.

Canonicalization: a group automorphism of C_q^2 is an invertible 2-by-2 matrix
over Z/qZ. canonical_key uses q, n, the multiset of element-coordinate ideals
gcd(x,y,q), and the multiset of determinant ideals gcd(det(v_i,v_j),q). These
are invariant under every such automorphism and under input permutation. This
is a strong cheap invariant, not a complete canonical form for rank-two modules;
it can over-collapse nonisomorphic instances. Independent seeds almost surely
have different public moduli, and the self-test checks both invariance and
distinctness explicitly.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_SMALL_PRIMORIAL = 3 * 5 * 7 * 11 * 13 * 17 * 19 * 23 * 29 * 31 * 37 * 41 * 43 * 47


def _modulus_bits(n: int) -> int:
    # log2(|C_q^2|) is about n-4: a critical-density, constant-solution regime.
    return max(7, n // 2 - 2)


def _draw_modulus(rng: random.Random, bits: int, n: int) -> int:
    """Draw a public odd modulus of exactly ``bits`` bits and greater than n."""
    while True:
        q = (1 << (bits - 1)) | rng.getrandbits(bits - 1) | 1
        if q > n and math.gcd(q, _SMALL_PRIMORIAL) == 1:
            return q


def _draw_nonzero_vector(rng: random.Random, q: int) -> tuple[int, int]:
    while True:
        v = (rng.randrange(q), rng.randrange(q))
        if v != (0, 0):
            return v


def _valid_simple_sequence(seq: list[tuple[int, int]], q: int) -> bool:
    seen: set[tuple[int, int]] = set()
    for v in seq:
        if v == (0, 0) or v in seen or ((-v[0]) % q, (-v[1]) % q) in seen:
            return False
        seen.add(v)
    return True


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Sample a witness first, then condition random group elements on its sum.

    ``n`` is the number of labelled sequence occurrences. Larger ``n`` raises
    both the candidate-space exponent and the modulus bit length. Optional
    ``plant_weight`` and ``modulus_bits`` exist for controlled experiments; the
    named ladder uses the critical-density defaults.
    """
    if type(n) is not int or not (8 <= n <= 384):
        raise ValueError("n must be an integer in [8, 384]")
    plant_weight = params.pop("plant_weight", n // 2)
    modulus_bits = params.pop("modulus_bits", _modulus_bits(n))
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if type(plant_weight) is not int or not (3 <= plant_weight <= n - 2):
        raise ValueError("plant_weight must be an integer in [3, n-2]")
    if type(modulus_bits) is not int or not (7 <= modulus_bits <= 190):
        raise ValueError("modulus_bits must be an integer in [7, 190]")

    rng = random.Random(seed)

    # G requires this to happen first: choose the complete answer before any
    # group, vector, or decoy is created.
    answer = sorted(rng.sample(range(n), plant_weight))
    planted_set = set(answer)
    pivot = answer[rng.randrange(plant_weight)]
    q = _draw_modulus(rng, modulus_bits, n)

    # Rejection is applied to the entire public sequence, never just to plants
    # or decoys. At named sizes a retry is fantastically unlikely, but it makes
    # the absence of trivial 1/2-term witnesses an exact invariant.
    for _ in range(10_000):
        seq: list[tuple[int, int] | None] = [None] * n
        for i in range(n):
            if i != pivot:
                seq[i] = _draw_nonzero_vector(rng, q)
        sx = sum(seq[i][0] for i in planted_set if i != pivot) % q  # type: ignore[index]
        sy = sum(seq[i][1] for i in planted_set if i != pivot) % q  # type: ignore[index]
        seq[pivot] = ((-sx) % q, (-sy) % q)
        concrete = [v for v in seq if v is not None]
        if len(concrete) == n and _valid_simple_sequence(concrete, q):
            break
    else:
        raise RuntimeError("could not draw a nontrivial simple sequence")

    inst = {
        "group_modulus": q,
        "max_length": q,
        "sequence": [[x, y] for x, y in concrete],
        "n": n,
        "answer": answer,
    }
    return inst


def render(inst: dict) -> str:
    """Return the complete statement seen by a solver."""
    n = inst["n"]
    q = inst["group_modulus"]
    rows = "\n".join(f"{i}: {v[0]} {v[1]}" for i, v in enumerate(inst["sequence"]))
    return f"""SHORT ZERO-SUM SUBSEQUENCE IN A FINITE ABELIAN GROUP

The group is C_q direct-sum C_q for q = {q}.  Concretely, a group element is
an ordered pair (x,y) of integers modulo q.  Addition is coordinatewise modulo
q, and the zero element is (0,0).

Below is a sequence of {n} labelled occurrences.  Occurrences are indexed from
0 through {n - 1}, inclusively.  Equal values, if present, would still be
different occurrences; the displayed index is what an answer selects.

A subsequence here means a subset of the displayed indices: order does not
matter and an index may not be repeated.  Find a NONEMPTY subsequence of length
at most {q} whose first coordinates sum to 0 modulo {q} and whose second
coordinates also sum to 0 modulo {q}.  Since {n} < {q}, the numerical length
bound permits every nonempty subset, but the two exact zero-sum conditions must
still hold.

INDEX: X Y
{rows}

Give your final answer inside <answer></answer> tags, as one JSON array of 1 to
{n} distinct integer indices.  Indices are 0-based, order is irrelevant, and
all bounds are inclusive.
Example: <answer>[0, 3, 7]</answer>
The example shows syntax only; it is not an answer to this instance.
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON integer list; return None on all errors."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
        if fence:
            body = fence.group(1).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if isinstance(value, list) and all(type(x) is int for x in value):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check a candidate directly without consulting the planted answer."""
    if not isinstance(answer, list):
        return False, "answer is not a JSON list"
    if not answer:
        return False, "subsequence is empty"
    if len(answer) > inst["max_length"]:
        return False, f"subsequence length {len(answer)} exceeds {inst['max_length']}"
    if any(type(i) is not int for i in answer):
        return False, "an index is not an integer"
    if len(set(answer)) != len(answer):
        return False, "an index is repeated"
    n = inst["n"]
    bad = [i for i in answer if not (0 <= i < n)]
    if bad:
        return False, f"index {bad[0]} is outside inclusive range 0..{n - 1}"
    q = inst["group_modulus"]
    sx = sum(inst["sequence"][i][0] for i in answer) % q
    sy = sum(inst["sequence"][i][1] for i in answer) % q
    if sx or sy:
        return False, f"subsequence sum is ({sx},{sy}), not (0,0) modulo {q}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from all structurally legal nonempty index subsets."""
    mask = rng.randrange(1, 1 << inst["n"])
    return [i for i in range(inst["n"]) if (mask >> i) & 1]


def search_space(inst: dict) -> int | None:
    """Number of nonempty subsets, exactly matching ``random_candidate``."""
    return (1 << inst["n"]) - 1


def enumerate_all(inst: dict) -> int | None:
    """Count all zero-sum nonempty subsets exactly when n <= 22."""
    n = inst["n"]
    if n > 22:
        return None
    q = inst["group_modulus"]
    seq = inst["sequence"]
    sx = sy = previous_gray = count = 0
    for step in range(1, 1 << n):
        gray = step ^ (step >> 1)
        changed = gray ^ previous_gray
        i = changed.bit_length() - 1
        if (gray >> i) & 1:
            sx = (sx + seq[i][0]) % q
            sy = (sy + seq[i][1]) % q
        else:
            sx = (sx - seq[i][0]) % q
            sy = (sy - seq[i][1]) % q
        if sx == 0 and sy == 0:
            count += 1
        previous_gray = gray
    return count


def canonical_key(inst: dict) -> str:
    """Hash GL(2,Z/q)- and occurrence-permutation-invariant public data."""
    q = inst["group_modulus"]
    seq = inst["sequence"]
    point_ideals = Counter(math.gcd(x, y, q) for x, y in seq)
    determinant_ideals: Counter[int] = Counter()
    for i in range(len(seq)):
        x1, y1 = seq[i]
        for j in range(i + 1, len(seq)):
            x2, y2 = seq[j]
            determinant_ideals[math.gcd((x1 * y2 - y1 * x2) % q, q)] += 1
    invariant = {
        "q": q,
        "n": len(seq),
        "point_ideals": sorted(point_ideals.items()),
        "determinant_ideals": sorted(determinant_ideals.items()),
    }
    raw = json.dumps(invariant, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase n and the automatically coupled modulus bit length."""
    if set(params) - {"n", "plant_weight", "modulus_bits"}:
        return None
    n = params.get("n")
    if type(n) is not int or n >= 384:
        return None
    new_n = min(384, n + max(32, n // 2))
    # Named presets use derived settings. Preserve an explicit density choice
    # only when a caller intentionally supplied it.
    out = {"n": new_n}
    if "plant_weight" in params:
        old_w = params["plant_weight"]
        out["plant_weight"] = max(3, round(old_w * new_n / n))
    if "modulus_bits" in params:
        old_b = params["modulus_bits"]
        out["modulus_bits"] = max(7, round(old_b * new_n / n))
    return out


# ---------------------------------------------------------------------------
# Adversary panel helpers. None reads inst["answer"].


def _centered(a: int, q: int) -> int:
    return min(a, q - a)


def _outlier_candidate(inst: dict) -> list[int]:
    q = inst["group_modulus"]
    score = [(_centered(x, q) ** 2 + _centered(y, q) ** 2, i)
             for i, (x, y) in enumerate(inst["sequence"])]
    return sorted(i for _, i in sorted(score)[: inst["n"] // 2])


def _greedy_candidate(inst: dict) -> list[int]:
    q = inst["group_modulus"]
    seq = inst["sequence"]
    chosen: list[int] = []
    unused = set(range(inst["n"]))
    sx = sy = 0
    for _ in range(inst["n"] // 2):
        def score(i: int) -> tuple[int, int]:
            nx = (sx + seq[i][0]) % q
            ny = (sy + seq[i][1]) % q
            return (_centered(nx, q) ** 2 + _centered(ny, q) ** 2, i)
        i = min(unused, key=score)
        chosen.append(i)
        unused.remove(i)
        sx = (sx + seq[i][0]) % q
        sy = (sy + seq[i][1]) % q
        if sx == 0 and sy == 0:
            return sorted(chosen)
    return sorted(chosen)


def _local_restart_attack(inst: dict, rng: random.Random, restarts: int = 64) -> tuple[list[int] | None, int]:
    """Construction-aware fixed-weight hill climbing with random restarts."""
    q = inst["group_modulus"]
    seq = inst["sequence"]
    n = inst["n"]
    w = n // 2
    iterations = 0
    for _ in range(restarts):
        chosen = set(rng.sample(range(n), w))
        sx = sum(seq[i][0] for i in chosen) % q
        sy = sum(seq[i][1] for i in chosen) % q
        for _ in range(12):
            iterations += 1
            if sx == 0 and sy == 0:
                return sorted(chosen), iterations
            current = _centered(sx, q) ** 2 + _centered(sy, q) ** 2
            best = (current, -1, -1, sx, sy)
            inside = rng.sample(sorted(chosen), min(10, w))
            outside_pool = sorted(set(range(n)) - chosen)
            outside = rng.sample(outside_pool, min(10, n - w))
            for a in inside:
                for b in outside:
                    nx = (sx - seq[a][0] + seq[b][0]) % q
                    ny = (sy - seq[a][1] + seq[b][1]) % q
                    val = _centered(nx, q) ** 2 + _centered(ny, q) ** 2
                    if val < best[0]:
                        best = (val, a, b, nx, ny)
            if best[1] < 0:
                break
            _, a, b, sx, sy = best
            chosen.remove(a)
            chosen.add(b)
    return None, iterations


def _mitm_bounded(inst: dict, node_budget: int = 250_000) -> tuple[list[int] | None, int]:
    """Bounded Horowitz-Sahni collision search over two public index blocks."""
    q = inst["group_modulus"]
    seq = inst["sequence"]
    block_bits = min(18, inst["n"] // 2)
    left_indices = list(range(block_bits))
    right_indices = list(range(block_bits, min(2 * block_bits, inst["n"])))
    table: dict[tuple[int, int], int] = {}
    nodes = 0

    sx = sy = prev = 0
    for step in range(1, 1 << len(left_indices)):
        gray = step ^ (step >> 1)
        changed = gray ^ prev
        local = changed.bit_length() - 1
        idx = left_indices[local]
        sign = 1 if (gray >> local) & 1 else -1
        sx = (sx + sign * seq[idx][0]) % q
        sy = (sy + sign * seq[idx][1]) % q
        nodes += 1
        if sx == 0 and sy == 0:
            return [left_indices[j] for j in range(len(left_indices)) if (gray >> j) & 1], nodes
        table.setdefault((sx, sy), gray)
        prev = gray
        if nodes >= node_budget:
            return None, nodes

    sx = sy = prev = 0
    for step in range(1, 1 << len(right_indices)):
        gray = step ^ (step >> 1)
        changed = gray ^ prev
        local = changed.bit_length() - 1
        idx = right_indices[local]
        sign = 1 if (gray >> local) & 1 else -1
        sx = (sx + sign * seq[idx][0]) % q
        sy = (sy + sign * seq[idx][1]) % q
        nodes += 1
        need = ((-sx) % q, (-sy) % q)
        if (sx == 0 and sy == 0) or need in table:
            ans = [right_indices[j] for j in range(len(right_indices)) if (gray >> j) & 1]
            if need in table:
                lm = table[need]
                ans += [left_indices[j] for j in range(len(left_indices)) if (lm >> j) & 1]
            if ans:
                return sorted(ans), nodes
        prev = gray
        if nodes >= node_budget:
            break
    return None, nodes


def _lll_reduce(basis: list[list[int]], max_steps: int) -> tuple[list[list[int]], int, bool]:
    """A standard Decimal LLL reduction, capped for a cheap adversary panel."""
    dim = len(basis)
    if not dim or any(len(row) != dim for row in basis):
        raise ValueError("LLL expects a square row basis")
    max_bits = max(abs(x).bit_length() for row in basis for x in row)
    with localcontext() as ctx:
        ctx.prec = max(80, int(max_bits * 0.7) + 50)
        zero = Decimal(0)
        bstar = [[zero] * dim for _ in range(dim)]
        mu = [[zero] * dim for _ in range(dim)]
        norms = [zero] * dim

        for i in range(dim):
            vi = [Decimal(x) for x in basis[i]]
            for j in range(i):
                if not norms[j]:
                    continue
                dot = sum(Decimal(basis[i][t]) * bstar[j][t] for t in range(dim))
                mu[i][j] = dot / norms[j]
                mij = mu[i][j]
                for t in range(dim):
                    vi[t] -= mij * bstar[j][t]
            bstar[i] = vi
            norms[i] = sum(x * x for x in vi)
            if not norms[i]:
                return basis, 0, False

        delta = Decimal(3) / Decimal(4)
        k = 1
        steps = 0
        while k < dim and steps < max_steps:
            steps += 1
            for j in range(k - 1, -1, -1):
                nearest = int(mu[k][j].to_integral_value(rounding="ROUND_HALF_EVEN"))
                if nearest:
                    basis[k] = [x - nearest * y for x, y in zip(basis[k], basis[j])]
                    dn = Decimal(nearest)
                    for ell in range(j):
                        mu[k][ell] -= dn * mu[j][ell]
                    mu[k][j] -= dn

            muk = mu[k][k - 1]
            if norms[k] >= (delta - muk * muk) * norms[k - 1]:
                k += 1
                continue

            basis[k], basis[k - 1] = basis[k - 1], basis[k]
            for j in range(k - 1):
                mu[k][j], mu[k - 1][j] = mu[k - 1][j], mu[k][j]
            old_mu = muk
            combined = norms[k] + old_mu * old_mu * norms[k - 1]
            if not combined:
                return basis, steps, False
            new_mu = old_mu * norms[k - 1] / combined
            norms[k] = norms[k] * norms[k - 1] / combined
            norms[k - 1] = combined
            mu[k][k - 1] = new_mu
            for i in range(k + 1, dim):
                old = mu[i][k]
                mu[i][k] = mu[i][k - 1] - old_mu * old
                mu[i][k - 1] = old + new_mu * mu[i][k]
            k = max(1, k - 1)
        return basis, steps, k == dim


def _lattice_attack(inst: dict, max_steps: int = 4_000) -> tuple[list[int] | None, int, bool]:
    """Construction-aware cardinality-centered lattice attack followed by LLL."""
    n = inst["n"]
    q = inst["group_modulus"]
    seq = inst["sequence"]
    w = n // 2
    scale = 4 * n
    dim = n + 3
    basis: list[list[int]] = []
    for i, (x, y) in enumerate(seq):
        row = [0] * dim
        row[i] = 2
        row[n] = scale * x
        row[n + 1] = scale * y
        row[n + 2] = scale
        basis.append(row)
    row_qx = [0] * dim
    row_qx[n] = scale * q
    basis.append(row_qx)
    row_qy = [0] * dim
    row_qy[n + 1] = scale * q
    basis.append(row_qy)
    special = [-1] * n + [0, 0, -scale * w]
    basis.append(special)

    reduced, steps, complete = _lll_reduce(basis, max_steps)
    candidates: list[list[int]] = []
    for row in reduced:
        if any(row[j] != 0 for j in range(n, dim)):
            continue
        head = row[:n]
        if all(x in (-1, 1) for x in head):
            candidates.append([i for i, x in enumerate(head) if x == 1])
            candidates.append([i for i, x in enumerate(head) if x == -1])
        if all(x in (0, 1) for x in head):
            candidates.append([i for i, x in enumerate(head) if x == 1])
        if all(x in (0, -1) for x in head):
            candidates.append([i for i, x in enumerate(head) if x == -1])
    for candidate in candidates:
        if candidate and verify(inst, candidate)[0]:
            return candidate, steps, complete
    return None, steps, complete


def _apply_matrix(inst: dict, matrix: tuple[int, int, int, int]) -> dict:
    a, b, c, d = matrix
    q = inst["group_modulus"]
    transformed = dict(inst)
    transformed["sequence"] = [
        [(a * x + b * y) % q, (c * x + d * y) % q]
        for x, y in inst["sequence"]
    ]
    return transformed


def _permute_instance(inst: dict, permutation: list[int]) -> tuple[dict, list[int]]:
    """new position j contains old position permutation[j]."""
    transformed = dict(inst)
    transformed["sequence"] = [inst["sequence"][i] for i in permutation]
    inverse = [0] * len(permutation)
    for new, old in enumerate(permutation):
        inverse[old] = new
    carried = [inverse[i] for i in inst["answer"]]
    return transformed, carried


def selftest() -> dict:
    """Run G1--G8 and return a fully numeric, JSON-serializable report."""
    report: dict[str, Any] = {}

    # G1: every preset and several seeds.
    g1_attempts = 0
    g1_successes = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            g1_successes += int(verify(inst, inst["answer"])[0])
    report["G1_planted_verifies"] = {
        "pass": g1_successes == g1_attempts,
        "successes": g1_successes,
        "attempts": g1_attempts,
    }

    shipping = make_instance(seed=20260903, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    unused = next(i for i in range(shipping["n"]) if i not in set(planted))
    corruptions = {
        "drop": planted[:-1],
        "swap": [unused] + planted[1:],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["n"]],
    }
    reasons: dict[str, str] = {}
    rejected = 0
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejected += int(not ok)
        reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": rejected == len(corruptions) and len(set(reasons.values())) == len(corruptions),
        "rejected": rejected,
        "attempts": len(corruptions),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    model_style = (
        "I computed both modular sums. Here is the requested object.\n\n"
        "<answer>```json\n" + json.dumps(planted) + "\n```</answer>\n"
        "The indices above are 0-based."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_items": len(parsed) if isinstance(parsed, list) else 0,
    }

    # One structure-aware sample supplies both G4 and the shipping density in G5.
    guess_rng = random.Random(0x250621383)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "samples": samples,
        "observed_fraction": hits / samples,
        "candidate_space": search_space(shipping),
    }

    # G6: all attacks must fail over eight unrelated shipping instances.
    attack_names = [
        "outlier_centered_norm",
        "greedy_modular_distance",
        "random_restart_local_256",
        "meet_in_middle_250k",
        "lattice_lll_centered",
    ]
    successes = {name: 0 for name in attack_names}
    costs = {name: {"seconds": 0.0, "work": 0} for name in attack_names}
    lll_completions = 0
    attack_seeds = list(range(3100, 3108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])

        t0 = time.perf_counter()
        candidate = _outlier_candidate(inst)
        costs[attack_names[0]]["seconds"] += time.perf_counter() - t0
        costs[attack_names[0]]["work"] += inst["n"]
        successes[attack_names[0]] += int(verify(inst, candidate)[0])

        t0 = time.perf_counter()
        candidate = _greedy_candidate(inst)
        costs[attack_names[1]]["seconds"] += time.perf_counter() - t0
        costs[attack_names[1]]["work"] += inst["n"] * inst["n"] // 2
        successes[attack_names[1]] += int(verify(inst, candidate)[0])

        t0 = time.perf_counter()
        candidate, work = _local_restart_attack(inst, random.Random(seed ^ 0xBAD5EED), 256)
        costs[attack_names[2]]["seconds"] += time.perf_counter() - t0
        costs[attack_names[2]]["work"] += work
        successes[attack_names[2]] += int(candidate is not None and verify(inst, candidate)[0])

        t0 = time.perf_counter()
        candidate, work = _mitm_bounded(inst, 250_000)
        costs[attack_names[3]]["seconds"] += time.perf_counter() - t0
        costs[attack_names[3]]["work"] += work
        successes[attack_names[3]] += int(candidate is not None and verify(inst, candidate)[0])

        t0 = time.perf_counter()
        candidate, work, complete = _lattice_attack(inst, 100_000)
        costs[attack_names[4]]["seconds"] += time.perf_counter() - t0
        costs[attack_names[4]]["work"] += work
        lll_completions += int(complete)
        successes[attack_names[4]] += int(candidate is not None and verify(inst, candidate)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": len(attack_seeds),
            "seconds": round(costs[name]["seconds"], 6),
            "work": costs[name]["work"],
        }
        for name in attack_names
    }
    attacks["lattice_lll_centered"]["completed_reductions"] = lll_completions
    all_failed = all(v == 0 for v in successes.values())
    report["G6_adversary_panel"] = {"pass": all_failed, "attacks": attacks}

    strongest = max(attack_names, key=lambda name: costs[name]["seconds"])
    demo = make_instance(seed=5, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": isinstance(demo_count, int) and hits / samples < 1e-6 and all_failed,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_fraction": hits / samples,
        "demo_n": demo["n"],
        "demo_exact_solution_count": demo_count,
        "baseline_attack": strongest,
        "baseline_seconds": round(costs[strongest]["seconds"], 6),
        "baseline_iterations_or_nodes": costs[strongest]["work"],
        "baseline_attempts": len(attack_seeds),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"]
        and doubled["group_modulus"].bit_length() > shipping["group_modulus"].bit_length(),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_modulus_bits": shipping["group_modulus"].bit_length(),
        "doubled_modulus_bits": doubled["group_modulus"].bit_length(),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    invariant_passes = 0
    carried_checks = 0
    carried_passes = 0
    unrelated_keys: list[str] = []
    for seed in range(20):
        inst = make_instance(n=32, seed=7000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        q = inst["group_modulus"]
        matrices = [
            (1, 0, 0, 1),
            (0, 1, 1, 0),
            (1, 1, 0, 1),
            (-1, 0, 0, 1),
        ]
        rng = random.Random(seed + 99)
        while len(matrices) < 6:
            matrix = tuple(rng.randrange(q) for _ in range(4))
            if math.gcd((matrix[0] * matrix[3] - matrix[1] * matrix[2]) % q, q) == 1:
                matrices.append(matrix)  # type: ignore[arg-type]
        permutation = list(range(inst["n"]))
        rng.shuffle(permutation)
        permuted, carried = _permute_instance(inst, permutation)
        for matrix in matrices:
            transformed = _apply_matrix(permuted, matrix)
            invariant_checks += 1
            invariant_passes += int(canonical_key(transformed) == base_key)
            carried_checks += 1
            carried_passes += int(verify(transformed, carried)[0])
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_passes == invariant_checks
        and carried_passes == carried_checks and distinct == len(unrelated_keys),
        "invariance_passes": invariant_passes,
        "invariance_attempts": invariant_checks,
        "carried_witness_passes": carried_passes,
        "carried_witness_attempts": carried_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": len(unrelated_keys),
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
