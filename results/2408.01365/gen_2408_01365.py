"""Exact generators for one-dimensional SGD data-debugging witnesses.

The native problem is the fixed-order, one-epoch hinge-loss construction in
Theorem 4.4 and Appendix B.1 of arXiv:2408.01365.  Generation composes hidden
equal-pair identities before translating them into the paper's rational SGD
training samples.  Verification replays SGD exactly; it never reads the
planted answer.
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
from fractions import Fraction
from typing import Any


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
try:
    from gvlib import rationals as rat
except ImportError:  # The standard-library fallback remains exact.
    rat = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "rational_exact",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "ordered one-dimensional SGD training samples over Q",
        "hinge-like loss linear classifier",
        "one-epoch rational parameter trajectory",
    ],
    "verification_operations": [
        "exact rational margin comparison",
        "exact rational SGD update replay",
        "exact sign comparison of the test margin",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Normalizing the rational training coordinates exposes residue-class "
        "four-tuples whose equal-pair identities compose a debugging subset; "
        "without that structure one faces fixed-cardinality subset sum."
    ),
    "hardness_basis": (
        "Track B: Appendix B.1 reduces the beta=-1, d=1, one-epoch SGD task "
        "to fixed-cardinality subset sum; at shipping n=40 the exact "
        "Horowitz--Sahni reference algorithm takes O(2^(n/2)) time and storage "
        "and measured 20.09 s, 1,572,864 states and 3,145,725 operations, while "
        "the hidden residue decomposition uses at most 180 exact arithmetic "
        "operations once recognized."
    ),
    "max_answer_tokens": 20,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 8, "payload_bits": 5},
    "easy": {"n": 40, "payload_bits": 20},
    "medium": {"n": 52, "payload_bits": 28},
    "hard": {"n": 64, "payload_bits": 36},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The normalized integer offsets of the ordinary samples form four-member "
    "residue classes modulo 997, each carrying an equal-pair identity."
)
PLACEBO_HINT = (
    "The exact rational coordinates of the ordinary samples reward careful "
    "bookkeeping throughout the fixed-order one-epoch retraining calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly n/2 distinct 0-based "
        "ordinary-sample indices, containing index 0; n is a multiple of 4 "
        "and n <= 64 for every named preset."
    ),
    "bounds": {
        "max_indices": 128,
        "max_index": 255,
        "index_bits": 8,
    },
}

NOTES = r"""
Paper grounding.  Section 2 fixes the conventions used here: a binary linear
classifier predicts +1 at a nonnegative margin, training data are a multiset,
and SGD applies the samples in a specified order.  Section 4.1 and Theorems
4.1--4.2 identify the regimes that would invalidate a hardness claim: linear
loss is handled by the linear-time GTA algorithm, as is one-dimensional
hinge-like loss when beta >= 0.  This family instead uses beta=-1, d=1 and one
epoch, exactly the hard regime of Theorem 4.4.

Certificate production.  Appendix B.1 gives the rational construction from
fixed-cardinality Subset Sum.  For positive integers a_i with A=sum(a_i), its
ordinary feature-label products are 2/3+a_i/(3A), the final sentinel product is
1+1/(6A), and w0=-1-2k/3-t/(3A).  The proof shows that a nonnegative final test
margin is equivalent to retaining k ordinary samples summing to t.  Here n/4
independent identities a+b=c+d are sampled first, hidden by residues modulo
997 and a global permutation, and t=A/2.  Choosing one equal pair per identity
therefore supplies a certificate by composition; neither generation nor
verification searches for one.

Track B and attacks.  A family-aware decoder normalizes the displayed rational
coordinates, buckets the resulting integers modulo 997, and uses the equal-pair
identity in every bucket.  It is deliberately reported as the compact route,
not as Track-A hardness.  The mechanical reference is exact fixed-cardinality
Horowitz--Sahni meet-in-the-middle; selftest runs it to completion at shipping
size, counts every answer, and records its wall time and state/operation count.
Plant and decoy elements are exchangeable within the same identity-generating
distribution.  Global shuffling defeats the input-quartet ansatz, randomized
orientation defeats a fixed-side convention, and the panel also checks a
per-element magnitude outlier, balanced greedy assignment, stochastic swap
descent, and a classic LLL subset-sum embedding.
""".strip()


_Q = 997
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000

# Filled from the three harness-owned runs after hardening.  These diagnostics
# never affect G9(c), the only gated portion of G9.
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _q(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if rat is not None:
        return rat.Q(value)
    if _is_int(value):
        return Fraction(value)
    if (isinstance(value, (list, tuple)) and len(value) == 2
            and _is_int(value[0]) and _is_int(value[1])
            and value[1] != 0):
        return Fraction(value[0], value[1])
    raise TypeError("not an exact JSON rational")


def _q_json(value: object) -> list[int]:
    q = _q(value)
    if rat is not None:
        return rat.to_json(q)
    return [q.numerator, q.denominator]


def _validate_params(n: int, payload_bits: int) -> None:
    if not _is_int(n) or n < 8 or n % 4:
        raise ValueError("n must be a multiple of 4 and at least 8")
    if n > 256:
        raise ValueError("n may not exceed the 256-row construction limit")
    if not _is_int(payload_bits) or not 5 <= payload_bits <= 512:
        raise ValueError("payload_bits must lie in 5..512")


def _identity_payloads(rng: random.Random, bits: int) -> tuple[int, int, int, int]:
    """Sample exchangeable bounded payloads satisfying a+b=c+d."""
    lo = 1 << (bits - 1)
    hi = (1 << bits) - 1
    while True:
        missing = rng.randrange(4)
        values: list[int | None] = [None, None, None, None]
        for i in range(4):
            if i != missing:
                values[i] = rng.randint(lo, hi)
        if missing == 0:
            values[0] = values[2] + values[3] - values[1]  # type: ignore[operator]
        elif missing == 1:
            values[1] = values[2] + values[3] - values[0]  # type: ignore[operator]
        elif missing == 2:
            values[2] = values[0] + values[1] - values[3]  # type: ignore[operator]
        else:
            values[3] = values[0] + values[1] - values[2]  # type: ignore[operator]
        row = tuple(int(x) for x in values)
        if all(lo <= x <= hi for x in row) and len(set(row)) == 4:
            return row  # type: ignore[return-value]


def _simulate(inst: dict, chosen: set[int]) -> tuple[Fraction, Fraction, int]:
    """Replay the stated one-epoch SGD trajectory with exact rationals."""
    w = _q(inst["initial_weight"])
    beta = _q(inst["loss"]["beta"])
    alpha = _q(inst["loss"]["alpha"])
    eta = _q(inst["learning_rate"])
    activated = 0
    for sample in inst["ordinary_samples"]:
        index = sample["id"]
        if index not in chosen:
            continue
        x = _q(sample["x"])
        y = sample["y"]
        if _q(y) * w * x < beta:
            w += eta * alpha * _q(y) * x
            activated += 1
    sentinel = inst["sentinel"]
    sx = _q(sentinel["x"])
    sy = sentinel["y"]
    if _q(sy) * w * sx < beta:
        w += eta * alpha * _q(sy) * sx
        activated += 1
    test = inst["test"]
    score = _q(test["y"]) * w * _q(test["x"])
    return score, w, activated


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Compose identities, then map them to the paper's native SGD instance."""
    unknown = set(params) - {"payload_bits"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    payload_bits = params.get("payload_bits", max(5, 5 * n // 8 - 5))
    _validate_params(n, payload_bits)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    groups = n // 4

    # G: all equalities and the selected sides exist before any SGD instance is
    # assembled.  Regenerate only to obtain primitive integer normalization.
    for _ in range(100):
        tags = rng.sample(range(_Q), groups)
        records: list[tuple[int, int, int]] = []
        for group, tag in enumerate(tags):
            a, b, c, d = _identity_payloads(rng, payload_bits)
            rows = [
                (_Q * a + tag, group, 0),
                (_Q * b + tag, group, 0),
                (_Q * c + tag, group, 1),
                (_Q * d + tag, group, 1),
            ]
            rng.shuffle(rows)
            records.extend(rows)
        if math.gcd(*[row[0] for row in records]) == 1:
            break
    else:
        raise RuntimeError("could not obtain primitive integer offsets")

    orientation = [rng.randrange(2) for _ in range(groups)]
    rng.shuffle(records)

    # The original full-data classifier must mispredict, as required by the
    # paper's Debuggable definition.  The planted side remains valid under any
    # ordinary-sample permutation, so this certification does not find it.
    for _ in range(100):
        weights = [row[0] for row in records]
        total = sum(weights)
        if total % 2:
            raise AssertionError("equal-pair composition produced an odd total")
        k = n // 2
        answer = [i for i, (_, group, side) in enumerate(records)
                  if side == orientation[group]]
        if 0 not in answer:
            selected = set(answer)
            answer = [i for i in range(n) if i not in selected]
        answer.sort()

        ordinary = [
            {"id": i, "x": _q_json(Fraction(2 * total + weight, 3 * total)), "y": 1}
            for i, weight in enumerate(weights)
        ]
        inst = {
            "family": "one_dimensional_hinge_sgd_debugging",
            "n": n,
            "payload_bits": payload_bits,
            "required_ordinary": k,
            "normalizer": total,
            "loss": {"kind": "hinge-like", "alpha": [1, 1], "beta": [-1, 1]},
            "learning_rate": [1, 1],
            "epochs": 1,
            "initial_weight": _q_json(Fraction(-(4 * k + 7), 6)),
            "ordinary_samples": ordinary,
            "sentinel": {
                "id": "a",
                "x": _q_json(Fraction(6 * total + 1, 6 * total)),
                "y": 1,
            },
            "test": {"x": [1, 1], "y": 1},
            "answer": answer,
        }
        full_score, _, _ = _simulate(inst, set(range(n)))
        planted_score, _, _ = _simulate(inst, set(answer))
        if full_score < 0 and planted_score >= 0:
            return inst
        rng.shuffle(records)
    raise RuntimeError("could not order the full data to preserve its misprediction")


def _fraction_text(pair: object) -> str:
    q = _q(pair)
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def render(inst: dict) -> str:
    """Render the complete native SGD debugging task and answer contract."""
    rows = "\n".join(
        f'{sample["id"]}: x={_fraction_text(sample["x"])} y={sample["y"]}'
        for sample in inst["ordinary_samples"]
    )
    k = inst["required_ordinary"]
    n = inst["n"]
    statement = f"""ONE-EPOCH SGD DATA DEBUGGING WITH EXACT RATIONALS

A one-dimensional binary linear classifier has rational parameter w and
predicts +1 on feature x when w*x >= 0, and -1 otherwise.  It is trained for
exactly one epoch in the displayed sample order.  The hinge-like loss has
alpha=1 and intercept beta=-1.  On a training sample (x,y), compute the margin
z=y*w*x.  If z < -1, the sample is activated and SGD updates w <- w+y*x;
if z >= -1, w is unchanged.  All comparisons and updates are exact rational
arithmetic; interval endpoints are closed exactly as stated.

The initial parameter is w0={_fraction_text(inst['initial_weight'])}.  The
learning rate is 1.  The original model trained on every ordinary sample and
then the sentinel predicts -1 on the test sample x=1,y=+1.

Choose exactly {k} of the {n} ordinary samples to retain.  They are replayed in
the fixed order below; all unchosen ordinary samples are deleted.  The sentinel
sample is always retained and processed last:

  sentinel a: x={_fraction_text(inst['sentinel']['x'])} y={inst['sentinel']['y']}

Your retained subset is valid when the retrained classifier predicts the test
label +1 on x=1.  The integer A={inst['normalizer']} is supplied as the common
normalizer used to encode the rational coordinates; it does not alter SGD.

ORDINARY SAMPLES (0-based ID: exact x, label y)
{rows}

The answer must be a strictly increasing JSON array of exactly {k} distinct
ordinary IDs.  Order in the array is only a canonical output convention; SGD
still uses the displayed order.  Every ID must lie in 0..{n - 1}.  To break the
complement symmetry, the array must contain ID 0.  Repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON array of
integers.
Syntax-only example: <answer>[0, 2, 5, 7]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON integer list; never raise on garbage."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if (isinstance(value, list)
                and all(_is_int(item) for item in value)):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay any proposed debugging subset exactly, without reading answer."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array of ordinary-sample IDs"
    if not answer:
        return False, "the retained ordinary-sample list must not be empty"
    if any(not _is_int(index) for index in answer):
        return False, "every retained sample ID must be an integer"
    try:
        n = inst["n"]
        k = inst["required_ordinary"]
        samples = inst["ordinary_samples"]
    except (KeyError, TypeError):
        return False, "malformed SGD instance"
    if len(answer) < k:
        return False, f"too few IDs: exactly {k} ordinary samples are required"
    if len(answer) > k:
        return False, f"too many IDs: exactly {k} ordinary samples are required"
    if len(set(answer)) != len(answer):
        return False, "retained sample IDs must be distinct"
    if any(index < 0 or index >= n for index in answer):
        return False, f"every retained sample ID must lie in 0..{n - 1}"
    if answer != sorted(answer):
        return False, "retained sample IDs must be strictly increasing"
    if answer[0] != 0:
        return False, "the canonical retained subset must contain ID 0"
    if len(samples) != n:
        return False, "malformed SGD instance: wrong ordinary-sample count"
    try:
        score, _, _ = _simulate(inst, set(answer))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False, "malformed SGD instance: invalid exact rational field"
    if score < 0:
        return False, f"retrained classifier predicts -1 (test margin {_fraction_text(_q_json(score))})"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated fixed-size, symmetry-broken language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    n = inst["n"]
    k = inst["required_ordinary"]
    return [0] + sorted(rng.sample(range(1, n), k - 1))


def search_space(inst: dict) -> int | None:
    """Exact size of the language sampled by random_candidate."""
    return math.comb(inst["n"] - 1, inst["required_ordinary"] - 1)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when the cap is small."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    k = inst["required_ordinary"]
    hits = 0
    for tail in itertools.combinations(range(1, n), k - 1):
        hits += int(verify(inst, [0] + list(tail))[0])
    return hits


def _offset_sum_valid(indices: list[int], weights: list[int]) -> bool:
    """The Appendix-B.1 criterion, used to make density sampling inexpensive."""
    return sum(weights[index] for index in indices) * 2 == sum(weights)


def _products(inst: dict) -> list[Fraction]:
    return [_q(sample["y"]) * _q(sample["x"])
            for sample in inst["ordinary_samples"]]


def _offsets(inst: dict) -> list[int]:
    """Recover the primitive positive integer offsets encoded by Appendix B.1."""
    normalizer = inst.get("normalizer")
    if not _is_int(normalizer) or normalizer <= 0:
        raise ValueError("normalizer must be a positive integer")
    values: list[int] = []
    for product in _products(inst):
        value = _q(normalizer) * (3 * product - 2)
        if value.denominator != 1 or value <= 0:
            raise ValueError("ordinary coordinate does not encode a positive integer")
        values.append(value.numerator)
    scale = math.gcd(*values)
    return [value // scale for value in values]


def canonical_key(inst: dict) -> str:
    """Canonical under ordinary-row relabelling and simultaneous x/y signs."""
    products = sorted((q.numerator, q.denominator) for q in _products(inst))
    sentinel = _q(inst["sentinel"]["y"]) * _q(inst["sentinel"]["x"])
    test = _q(inst["test"]["y"]) * _q(inst["test"]["x"])
    initial = _q(inst["initial_weight"])
    beta = _q(inst["loss"]["beta"])
    form = {
        "n": inst["n"],
        "k": inst["required_ordinary"],
        "ordinary_products": products,
        "sentinel_product": [sentinel.numerator, sentinel.denominator],
        "test_product": [test.numerator, test.denominator],
        "initial": [initial.numerator, initial.denominator],
        "beta": [beta.numerator, beta.denominator],
        "epochs": inst["epochs"],
    }
    payload = json.dumps(form, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase coefficient entropy first; the 64-row route reaches the effort cap."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    bits = params.get("payload_bits")
    if not _is_int(n) or not _is_int(bits):
        return None
    out = dict(params)
    if bits < 160:
        out["payload_bits"] = min(160, bits + 16)
        return out
    if n < 64:
        out["n"] = min(64, n + 4)
        out["payload_bits"] = max(bits, 5 * out["n"] // 8 - 5)
        return out
    return "cap_bound"


def _canonical_side(indices: list[int], n: int) -> list[int]:
    side = sorted(indices)
    if 0 in side:
        return side
    selected = set(side)
    return [i for i in range(n) if i not in selected]


def _outlier_attack(inst: dict) -> list[int]:
    """Choose the smallest-magnitude half of the normalized offsets."""
    weights = _offsets(inst)
    chosen = sorted(range(inst["n"]), key=lambda i: (weights[i], i))[:inst["required_ordinary"]]
    return _canonical_side(chosen, inst["n"])


def _balanced_greedy_attack(inst: dict) -> list[int]:
    """Largest-first two-bin balancing with the exact cardinality quota."""
    weights = _offsets(inst)
    n = inst["n"]
    k = inst["required_ordinary"]
    sides: list[list[int]] = [[], []]
    totals = [0, 0]
    for index in sorted(range(n), key=lambda i: (-weights[i], i)):
        if len(sides[0]) == k:
            side = 1
        elif len(sides[1]) == k:
            side = 0
        else:
            side = 0 if totals[0] <= totals[1] else 1
        sides[side].append(index)
        totals[side] += weights[index]
    return _canonical_side(sides[0], n)


def _input_quartet_attack(inst: dict) -> list[int]:
    """Hand ansatz: each four consecutive displayed rows is one identity."""
    weights = _offsets(inst)
    chosen: list[int] = []
    for start in range(0, inst["n"], 4):
        block = list(range(start, start + 4))
        pair = min(
            itertools.combinations(block, 2),
            key=lambda p: (abs(2 * (weights[p[0]] + weights[p[1]])
                              - sum(weights[i] for i in block)), p),
        )
        chosen.extend(pair)
    return _canonical_side(chosen, inst["n"])


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 24, steps: int = 160,
                           trials: int = 48) -> tuple[list[int], int]:
    """Fixed-cardinality stochastic one-swap descent on the exact residual."""
    n = inst["n"]
    k = inst["required_ordinary"]
    weights = _offsets(inst)
    target = sum(weights) // 2
    best = random_candidate(inst, rng)
    best_score = abs(sum(weights[i] for i in best) - target)
    iterations = 0
    for _ in range(restarts):
        current = set(rng.sample(range(n), k))
        current_sum = sum(weights[i] for i in current)
        for _ in range(steps):
            iterations += 1
            score = abs(current_sum - target)
            if score == 0:
                return _canonical_side(list(current), n), iterations
            inside = tuple(current)
            outside = tuple(i for i in range(n) if i not in current)
            trial_best = None
            for _ in range(trials):
                take = inside[rng.randrange(len(inside))]
                give = outside[rng.randrange(len(outside))]
                trial_sum = current_sum - weights[take] + weights[give]
                row = (abs(trial_sum - target), take, give, trial_sum)
                if trial_best is None or row < trial_best:
                    trial_best = row
            assert trial_best is not None
            trial_score, take, give, trial_sum = trial_best
            if trial_score >= score and rng.randrange(8):
                continue
            current.remove(take)
            current.add(give)
            current_sum = trial_sum
            if trial_score < best_score:
                best_score = trial_score
                best = _canonical_side(list(current), n)
    return best, iterations


def _gram_schmidt_float(basis: list[list[int]]) -> tuple[list[list[float]], list[float]]:
    """Floating Gram--Schmidt used only by the adversarial LLL probe."""
    rows = len(basis)
    cols = len(basis[0])
    star: list[list[float]] = []
    mu = [[0.0] * rows for _ in range(rows)]
    norms: list[float] = []
    for i in range(rows):
        vec = [float(x) for x in basis[i]]
        for j in range(i):
            denom = norms[j]
            coeff = 0.0 if denom == 0.0 else sum(
                float(basis[i][c]) * star[j][c] for c in range(cols)
            ) / denom
            mu[i][j] = coeff
            for c in range(cols):
                vec[c] -= coeff * star[j][c]
        star.append(vec)
        norms.append(sum(x * x for x in vec))
    return mu, norms


def _lll_embedding_attack(inst: dict, max_loops: int = 80) -> tuple[list[int], int]:
    """Capped classic cardinality-augmented subset-sum LLL embedding."""
    weights = _offsets(inst)
    n = inst["n"]
    k_required = inst["required_ordinary"]
    target = sum(weights) // 2
    scale = n
    basis: list[list[int]] = []
    for i, weight in enumerate(weights):
        row = [0] * (n + 2)
        row[i] = 2
        row[-2] = 2 * scale * weight
        row[-1] = 2 * scale
        basis.append(row)
    basis.append([1] * n + [2 * scale * target, 2 * scale * k_required])

    loops = 0
    pos = 1
    while pos < len(basis) and loops < max_loops:
        loops += 1
        mu, norms = _gram_schmidt_float(basis)
        for j in range(pos - 1, -1, -1):
            q = int(round(mu[pos][j]))
            if q:
                basis[pos] = [x - q * y for x, y in zip(basis[pos], basis[j])]
                # Size reduction leaves the Gram--Schmidt vectors and norms
                # fixed, so update this mu row without a full recomputation.
                for earlier in range(j):
                    mu[pos][earlier] -= q * mu[j][earlier]
                mu[pos][j] -= q
        if norms[pos] >= (0.75 - mu[pos][pos - 1] ** 2) * norms[pos - 1]:
            pos += 1
        else:
            basis[pos], basis[pos - 1] = basis[pos - 1], basis[pos]
            pos = max(1, pos - 1)

    for row in basis:
        for signed in (row, [-x for x in row]):
            if (signed[-2] == 0 and signed[-1] == 0
                    and all(x in (-1, 1) for x in signed[:-2])):
                chosen = [i for i, x in enumerate(signed[:-2]) if x == 1]
                if len(chosen) == k_required:
                    return _canonical_side(chosen, n), loops
    return random_candidate(inst, random.Random(0x11A + sum(weights) % 1009)), loops


def _compact_decode(inst: dict) -> tuple[list[int] | None, int]:
    """Family-aware residue decoder and its exact-arithmetic operation count."""
    weights = _offsets(inst)
    n = inst["n"]
    # Per row: 3*x, subtraction of 2, multiplication by A, and one remainder.
    operations = 4 * n
    buckets: dict[int, list[int]] = {}
    for index, weight in enumerate(weights):
        buckets.setdefault(weight % _Q, []).append(index)
    chosen: list[int] = []
    for residue in sorted(buckets):
        block = sorted(buckets[residue], key=lambda i: (weights[i], i))
        if len(block) != 4:
            return None, operations
        # For four distinct sorted numbers admitting an equal two-pair split,
        # the pairing is necessarily extremes versus the two middle values.
        left = weights[block[0]] + weights[block[3]]
        right = weights[block[1]] + weights[block[2]]
        operations += 2
        if left != right:
            return None, operations
        chosen.extend((block[0], block[3]))
    return _canonical_side(chosen, n), operations


def _mitm_count(inst: dict, max_left_states: int = 1 << 21
                ) -> tuple[int | None, list[int] | None, dict[str, int]]:
    """Exact fixed-cardinality Horowitz--Sahni count with index 0 forced."""
    weights = _offsets(inst)
    n = inst["n"]
    split = n // 2
    left_weights = weights[1:split]
    right_weights = weights[split:]
    left_size = 1 << len(left_weights)
    right_size = 1 << len(right_weights)
    if left_size > max_left_states:
        return None, None, {
            "left_states": left_size,
            "right_states": right_size,
            "states": left_size + right_size,
            "operations": 0,
        }
    table: dict[tuple[int, int], list[int]] = {(0, 0): [1, 0]}
    left_sums = [0] * left_size
    left_counts = bytearray(left_size)
    operations = 0
    for mask in range(1, left_size):
        bit = mask & -mask
        coordinate = bit.bit_length() - 1
        previous = mask ^ bit
        left_sums[mask] = left_sums[previous] + left_weights[coordinate]
        left_counts[mask] = left_counts[previous] + 1
        key = (left_counts[mask], left_sums[mask])
        row = table.get(key)
        if row is None:
            table[key] = [1, mask]
        else:
            row[0] += 1
        operations += 2

    target_sum = sum(weights) // 2 - weights[0]
    target_count = inst["required_ordinary"] - 1
    right_sums = [0] * right_size
    right_counts = bytearray(right_size)
    solutions = 0
    witness = None
    for mask in range(right_size):
        if mask:
            bit = mask & -mask
            coordinate = bit.bit_length() - 1
            previous = mask ^ bit
            right_sums[mask] = right_sums[previous] + right_weights[coordinate]
            right_counts[mask] = right_counts[previous] + 1
            operations += 1
        row = table.get((target_count - right_counts[mask],
                         target_sum - right_sums[mask]))
        operations += 1
        if row is None:
            continue
        solutions += row[0]
        if witness is None:
            left_mask = row[1]
            witness = [0]
            witness.extend(1 + j for j in range(len(left_weights))
                           if left_mask & (1 << j))
            witness.extend(split + j for j in range(len(right_weights))
                           if mask & (1 << j))
    return solutions, witness, {
        "left_states": left_size,
        "right_states": right_size,
        "states": left_size + right_size,
        "operations": operations,
    }


def _transform_instance(inst: dict, permutation: list[int] | None = None,
                        sign_seed: int | None = None) -> dict:
    """Carry a witness through row relabelling and simultaneous x/y sign flips."""
    n = inst["n"]
    if permutation is None:
        permutation = list(range(n))
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation is not a relabelling")
    rng = random.Random(sign_seed) if sign_seed is not None else None
    samples: list[dict | None] = [None] * n
    for old, new in enumerate(permutation):
        sample = inst["ordinary_samples"][old]
        sign = -1 if rng is not None and rng.randrange(2) else 1
        samples[new] = {
            "id": new,
            "x": _q_json(sign * _q(sample["x"])),
            "y": sign * sample["y"],
        }
    carried = _canonical_side([permutation[i] for i in inst["answer"]], n)
    out = {key: value for key, value in inst.items()
           if key not in {"ordinary_samples", "sentinel", "test", "answer"}}
    out["ordinary_samples"] = samples
    sentinel_sign = -1 if rng is not None and rng.randrange(2) else 1
    out["sentinel"] = {
        "id": "a",
        "x": _q_json(sentinel_sign * _q(inst["sentinel"]["x"])),
        "y": sentinel_sign * inst["sentinel"]["y"],
    }
    test_sign = -1 if rng is not None and rng.randrange(2) else 1
    out["test"] = {
        "x": _q_json(test_sign * _q(inst["test"]["x"])),
        "y": test_sign * inst["test"]["y"],
    }
    out["answer"] = carried
    return out


def selftest() -> dict:
    """Run G1--G9 and return measured, machine-readable evidence."""
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
        "certificate_language": CERTIFICATE_LANGUAGE,
    }

    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (preset, seed, why)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            full_score, _, _ = _simulate(inst, set(range(inst["n"])))
            assert full_score < 0
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "generation_route": "composition of hidden equal-pair identities",
        "original_models_mispredict": checked,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    answer = inst["answer"]
    answer_set = set(answer)
    replacement = next(i for i in range(1, inst["n"])
                       if i not in answer_set)
    swap_bad = sorted(answer[:-1] + [replacement])
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": answer[:-1] + [answer[-2]],
        "out_of_range": answer[:-1] + [inst["n"]],
        "order_swap": [answer[1], answer[0]] + answer[2:],
        "element_swap": swap_bad,
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "I replayed the activated samples exactly.\n```json\n<answer>"
        + json.dumps(answer) + "</answer>\n```\nThe indices are zero-based."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>[0, nope]</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "realistic_response": True,
        "malformed_returns_none": True,
    }

    guess_rng = random.Random(13579)
    guess_total = 200_000
    guess_hits = 0
    guess_weights = _offsets(inst)
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(_offset_sum_valid(candidate, guess_weights))
    guess_wall = time.perf_counter() - guess_start
    assert guess_hits / guess_total < 1e-6
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_hits / guess_total,
        "wall_clock_sec": guess_wall,
        "structure_aware_space": search_space(inst),
        "prior": "uniform k-subsets containing index 0",
        "measurement": "exact Appendix-B.1 integer-sum criterion",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1
    mitm_start = time.perf_counter()
    solution_count, mitm_answer, mitm_stats = _mitm_count(inst)
    mitm_wall = time.perf_counter() - mitm_start
    assert isinstance(solution_count, int) and solution_count >= 1
    assert mitm_answer is not None and verify(inst, mitm_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_exact_solution_count": solution_count,
        "shipping_candidate_count": search_space(inst),
        "shipping_valid_fraction": solution_count / search_space(inst),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec": mitm_wall,
        "baseline_state_count": mitm_stats["states"],
        "baseline_operation_count": mitm_stats["operations"],
        "baseline_attack": "exact fixed-cardinality Horowitz--Sahni meet-in-the-middle",
    }

    attack_seeds = list(range(8100, 8108))
    names = [
        "per_element_smallest_magnitude",
        "balanced_largest_first_greedy",
        "random_restart_one_swap_24x160",
        "by_hand_consecutive_quartets",
        "lll_cardinality_embedding_80_loop_prefix",
    ]
    attacks = {name: {"successes": 0, "attempts": len(attack_seeds)}
               for name in names}
    restart_iterations = 0
    lll_loops = 0
    compact_successes = 0
    compact_operations: list[int] = []
    compact_wall = 0
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **ship_params)
        restart_answer, iterations = _random_restart_attack(
            attacked, random.Random(seed ^ 0x5A17)
        )
        restart_iterations += iterations
        lll_answer, loops = _lll_embedding_attack(attacked)
        lll_loops += loops
        candidates = {
            "per_element_smallest_magnitude": _outlier_attack(attacked),
            "balanced_largest_first_greedy": _balanced_greedy_attack(attacked),
            "random_restart_one_swap_24x160": restart_answer,
            "by_hand_consecutive_quartets": _input_quartet_attack(attacked),
            "lll_cardinality_embedding_80_loop_prefix": lll_answer,
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(attacked, candidate)[0])
        compact_start = time.perf_counter()
        decoded, operations = _compact_decode(attacked)
        compact_wall += time.perf_counter() - compact_start
        compact_operations.append(operations)
        if decoded is not None and verify(attacked, decoded)[0]:
            compact_successes += 1
    assert all(row["successes"] == 0 for row in attacks.values()), attacks
    assert compact_successes == len(attack_seeds)
    assert max(compact_operations) <= 300
    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "attack_costs": {
            "random_restart_iterations": restart_iterations,
            "lll_reduction_loops": lll_loops,
        },
        "reference_algorithm": {
            "name": "exact fixed-cardinality Horowitz--Sahni meet-in-the-middle",
            "complexity": "O(2^(n/2)) time and storage",
            "wall_clock_sec": mitm_wall,
            "operations": mitm_stats["operations"],
            "states": mitm_stats["states"],
            "solves": "1/1, as expected",
        },
        "compact_route": {
            "name": "normalization plus residue-class equal-pair decomposition",
            "complexity": "O(n) exact arithmetic with a fixed modulus",
            "wall_clock_sec": compact_wall,
            "max_operations": max(compact_operations),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["payload_bits"] = max(
        doubled_params["payload_bits"], 5 * doubled_params["n"] // 8 - 5
    )
    scaled = make_instance(seed=424242, **doubled_params)
    ok, why = verify(scaled, scaled["answer"])
    assert ok, why
    assert scaled["n"] > inst["n"]
    assert search_space(scaled) > search_space(inst)
    report["G7_scales"] = {
        "pass": True,
        "base_n": inst["n"],
        "doubled_n": scaled["n"],
        "base_candidate_space": search_space(inst),
        "scaled_candidate_space": search_space(scaled),
        "planted_verifies": True,
    }

    invariance_checks = 0
    real_transform_checks = 0
    original_answer_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(n=16, payload_bits=10, seed=9000 + seed)
        key = canonical_key(base)
        unrelated_keys.append(key)
        rng = random.Random(700_000 + seed)
        permutation = list(range(base["n"]))
        rng.shuffle(permutation)
        transforms = [
            _transform_instance(base, permutation=permutation),
            _transform_instance(base, sign_seed=800_000 + seed),
            _transform_instance(base, permutation=permutation,
                                sign_seed=900_000 + seed),
        ]
        for transformed in transforms:
            assert canonical_key(transformed) == key
            invariance_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            assert ok, (seed, why)
            real_transform_checks += 1
        ok, why = verify(transforms[1], base["answer"])
        assert ok, (seed, why)
        original_answer_checks += 1
    assert len(set(unrelated_keys)) == len(unrelated_keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_transform_checks,
        "original_answer_checks": original_answer_checks,
        "distinct_unrelated": len(set(unrelated_keys)),
        "unrelated_attempts": len(unrelated_keys),
        "symmetries": [
            "ordinary-sample relabelling",
            "independent simultaneous sign flip of each (x,y) pair",
            "compositions of those transformations",
        ],
    }

    serialized = json.dumps(answer)
    answer_chars = len(serialized)
    answer_tokens = math.ceil(answer_chars / 4)
    worst_case_answer = list(range(inst["n"] - inst["required_ordinary"],
                                   inst["n"]))
    worst_case_chars = len(json.dumps(worst_case_answer))
    worst_case_tokens = math.ceil(worst_case_chars / 4)
    route_operations = max(compact_operations)
    within_caps = (answer_chars <= 2000 and len(answer) <= 256
                   and route_operations <= 300
                   and worst_case_tokens <= PROBLEM_PROFILE["max_answer_tokens"])
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else 0)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else 0)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "too_easy" if hinted["attempts"] and hinted["solved"] else
            "hardened" if hinted["attempts"] else "not_yet_run"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(answer),
        "worst_case_answer_chars": worst_case_chars,
        "worst_case_answer_tokens": worst_case_tokens,
        "intended_route_operations": route_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "token_measurement": "ceil(serialized JSON characters / 4)",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
