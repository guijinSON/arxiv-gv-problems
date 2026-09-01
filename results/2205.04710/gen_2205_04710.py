"""Inverse generator for the two-matrix Waring equation over a prime field.

The public instance is (p, k, T) and a witness is a pair (A, B) of 2 by 2
matrices over F_p satisfying A**k + B**k = T.  Everything in this module uses
only the Python standard library and is deterministic from (n, seed, params).
"""

from __future__ import annotations

import itertools
import json
import random
import re
from typing import Any


DIFFICULTY = {
    "hard": {"n": 24},
    "harder": {"n": 28},
    "extreme": {"n": 32},
}
SHIPPING_DIFFICULTY = "hard"


NOTES = r"""
Definition source: the Introduction and Section 2 of Kishore--Singh,
"Matrix Waring Problem -- II" (arXiv:2205.04710) define the task as finding
A,B in M_m(F_q) with T=A^k+B^k.  Proposition A.3 gives q>k^16 for the
two-variable scalar ingredient, and Theorem 1.1 covers all matrix sizes once q
is sufficiently large.  The later explicit bound q >= (k-1)^4+6k in
arXiv:2306.06588 confirms that the primes used here lie in the universal
representability regime.

Easy regimes deliberately avoided: k is not fixed.  For fixed k, Sections
3--6 reduce an arbitrary matrix by rational canonical form to finitely many
scalar k-th-power equations, and Section 5 explicitly solves regular nilpotent
blocks of size at least 2k.  Standard randomized finite-field polynomial
factoring then makes that fixed-k search polynomial-time.  Here k=2^n grows,
p=a*2^(16n)+1 is a Proth prime (proved prime by the stored Proth witness), and
gcd(k,p-1)=k.  The direct scalar-subgroup search consequently costs about k
trials, exponential in n.  This is a practical/no-known-polynomial hardness
claim, not a reduction proving NP-hardness.

Planting and attacks: A and B are sampled first as independent uniform dense
matrices and only their unordered presentation is normalized; T is then their
power sum.  Thus the two plants have exactly the same distribution.  The
adversary panel tests a per-entry magnitude/outlier split, coordinate-wise
greedy descent, and random restarts of the paper-inspired four-term trace
decomposition.  The generated target is required to have square-free
characteristic polynomial.  This both avoids scalar/Jordan special cases and
makes the characteristic polynomial a complete, cheap similarity invariant.
canonical_key additionally normalizes the exact T -> c^k*T homogeneity orbit.
""".strip()


_PROTH_CACHE: dict[int, tuple[int, int, int]] = {}
_SMALL_PRIMES = (
    3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61,
    67, 71, 73, 79, 83, 89, 97,
)


def _proth_prime(n: int) -> tuple[int, int, int]:
    """Return (p, coefficient, witness), with an exact Proth certificate.

    p = coefficient * 2**(16*n) + 1.  Proth's theorem proves primality when
    coefficient is odd, coefficient < 2**(16*n), and the displayed modular
    equation has value -1.  We search deterministically, so no probable-prime
    assumption enters the field arithmetic.
    """
    if n in _PROTH_CACHE:
        return _PROTH_CACHE[n]
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        raise ValueError("n must be an integer at least 2")
    exponent = 16 * n
    power_of_two = 1 << exponent
    coefficient = 1
    while coefficient < power_of_two:
        candidate = coefficient * power_of_two + 1
        if not any(candidate % r == 0 for r in _SMALL_PRIMES):
            half = (candidate - 1) // 2
            for witness in range(2, 257):
                if pow(witness, half, candidate) == candidate - 1:
                    result = (candidate, coefficient, witness)
                    _PROTH_CACHE[n] = result
                    return result
        coefficient += 2
    raise RuntimeError("no certified Proth prime found for this n")


def _zero(d: int) -> list[list[int]]:
    return [[0 for _ in range(d)] for _ in range(d)]


def _identity(d: int) -> list[list[int]]:
    out = _zero(d)
    for i in range(d):
        out[i][i] = 1
    return out


def _mat_add(a: list[list[int]], b: list[list[int]], p: int) -> list[list[int]]:
    d = len(a)
    return [[(a[i][j] + b[i][j]) % p for j in range(d)] for i in range(d)]


def _matmul(a: list[list[int]], b: list[list[int]], p: int) -> list[list[int]]:
    d = len(a)
    if d == 1:
        return [[(a[0][0] * b[0][0]) % p]]
    if d == 2:
        a00, a01 = a[0]
        a10, a11 = a[1]
        b00, b01 = b[0]
        b10, b11 = b[1]
        return [
            [(a00 * b00 + a01 * b10) % p,
             (a00 * b01 + a01 * b11) % p],
            [(a10 * b00 + a11 * b10) % p,
             (a10 * b01 + a11 * b11) % p],
        ]
    bt = list(zip(*b))
    return [[sum(x * y for x, y in zip(row, col)) % p for col in bt]
            for row in a]


def _square(a: list[list[int]], p: int) -> list[list[int]]:
    if len(a) != 2:
        return _matmul(a, a, p)
    x, y = a[0]
    z, w = a[1]
    yz = y * z
    diag_sum = x + w
    return [
        [(x * x + yz) % p, (y * diag_sum) % p],
        [(z * diag_sum) % p, (w * w + yz) % p],
    ]


def _mat_pow(a: list[list[int]], exponent: int, p: int) -> list[list[int]]:
    if exponent < 0:
        raise ValueError("negative matrix exponent")
    result = _identity(len(a))
    base = [row[:] for row in a]
    e = exponent
    while e:
        if e & 1:
            result = _matmul(result, base, p)
        e >>= 1
        if e:
            base = _square(base, p)
    return result


def _flatten(a: list[list[int]]) -> tuple[int, ...]:
    return tuple(x for row in a for x in row)


def _ordered_pair(a: list[list[int]], b: list[list[int]]) -> tuple[list[list[int]], list[list[int]]]:
    if _flatten(b) < _flatten(a):
        return b, a
    return a, b


def _trace(a: list[list[int]], p: int) -> int:
    return sum(a[i][i] for i in range(len(a))) % p


def _det2(a: list[list[int]], p: int) -> int:
    return (a[0][0] * a[1][1] - a[0][1] * a[1][0]) % p


def _trace_power_2x2(a: list[list[int]], exponent: int, p: int) -> int | None:
    """Fast exact trace(A**exponent) when exponent is a power of two."""
    if exponent <= 0 or exponent & (exponent - 1):
        return None
    tr = _trace(a, p)
    determinant_power = _det2(a, p)
    steps = exponent.bit_length() - 1
    for _ in range(steps):
        tr = (tr * tr - 2 * determinant_power) % p
        determinant_power = (determinant_power * determinant_power) % p
    return tr


def _transpose(a: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in zip(*a)]


def _conjugate(a: list[list[int]], change: list[list[int]], inverse: list[list[int]], p: int) -> list[list[int]]:
    return _matmul(_matmul(change, a, p), inverse, p)


def _charpoly2(a: list[list[int]], p: int) -> tuple[int, int, int]:
    """Coefficients of x^2 + c1*x + c2."""
    return (1, (-_trace(a, p)) % p, _det2(a, p))


def _squarefree_charpoly2(a: list[list[int]], p: int) -> bool:
    tr = _trace(a, p)
    return (tr * tr - 4 * _det2(a, p)) % p != 0


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Sample the answer first, then form T=A^k+B^k over a certified F_p.

    n is the encoded security parameter, not the matrix dimension.  The matrix
    dimension is fixed at 2, k=2^n, and p is a deterministic Proth prime above
    k^16.  Increasing n doubles k and adds about 16 bits to p.
    """
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    p, coefficient, proth_witness = _proth_prime(n)
    k = 1 << n
    rng = random.Random(seed)
    d = 2

    # The witnesses are identically distributed.  Conditioning is only on the
    # public target having a simple similarity class; it does not distinguish
    # one planted summand from the other.
    for _ in range(10_000):
        a = [[rng.randrange(p) for _ in range(d)] for _ in range(d)]
        b = [[rng.randrange(p) for _ in range(d)] for _ in range(d)]
        a, b = _ordered_pair(a, b)
        target = _mat_add(_mat_pow(a, k, p), _mat_pow(b, k, p), p)
        if (_trace(target, p) != 0
                and target[0][1] != 0 and target[1][0] != 0
                and target[0][1] != target[1][0]
                and _squarefree_charpoly2(target, p)):
            return {
                "family": "matrix_waring_two_summands",
                "n": n,
                "dimension": d,
                "p": p,
                "k": k,
                "target": target,
                "proth_coefficient": coefficient,
                "proth_witness": proth_witness,
                "answer": {"A": a, "B": b},
            }
    raise RuntimeError("failed to sample a generic cyclic target")


def render(inst: dict) -> str:
    """Render a self-contained matrix Waring search problem."""
    p = inst["p"]
    k = inst["k"]
    d = inst["dimension"]
    target_lines = "\n".join(" ".join(str(x) for x in row) for row in inst["target"])
    zero_rows = ",".join("[" + ",".join("0" for _ in range(d)) + "]" for _ in range(d))
    example = '{"A":[' + zero_rows + '],"B":[' + zero_rows + ']} '
    return f"""Matrix Waring witness problem over a prime field

Let F_p be the field of integers modulo the prime p={p}.  All additions and
multiplications below are performed modulo p, with residues represented by the
integers 0 through p-1 inclusive.

The exponent is k={k}.  For a square matrix X, X^k means the ordinary matrix
product of exactly k copies of X; it is not entrywise exponentiation.  Matrix
row and column indices are 0-based.  Find two {d} by {d} matrices A and B over
F_p such that

    A^k + B^k = T.

The order of A and B does not matter, repeats are allowed, and every entry must
be an integer in the inclusive range 0..p-1.  The target T is given row by row:

{target_lines}

Your witness must contain exactly two matrices, each with exactly {d} rows and
{d} entries per row.  Use JSON with the exact keys "A" and "B".

Give your final answer inside <answer></answer> tags, as
<answer>{{"A":[[a00,a01],[a10,a11]],"B":[[b00,b01],[b10,b11]]}}</answer>
with the obvious same row shape if the displayed dimension is not 2.
Example of the required syntax: <answer>{example.strip()}</answer>
Output nothing else inside the tags."""


_ANSWER_BLOCK = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL)


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed JSON answer block, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_BLOCK.findall(text)
    for raw in reversed(blocks):
        body = raw.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body,
                             re.IGNORECASE | re.DOTALL)
        if fence:
            body = fence.group(1).strip()
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return None


def _validate_matrix(name: str, value: object, d: int, p: int) -> tuple[bool, str]:
    if not isinstance(value, list):
        return False, f"{name} must be a list of rows"
    if len(value) != d:
        return False, f"{name} row count mismatch: expected {d}, got {len(value)}"
    for i, row in enumerate(value):
        if not isinstance(row, list):
            return False, f"{name} row {i} must be a list"
        if len(row) != d:
            return False, f"{name} row {i} length mismatch: expected {d}, got {len(row)}"
        for j, x in enumerate(row):
            if not isinstance(x, int) or isinstance(x, bool):
                return False, f"{name}[{i}][{j}] must be an integer"
            if not 0 <= x < p:
                return False, f"{name}[{i}][{j}] is outside the inclusive range 0..p-1"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any witness exactly, without consulting inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object with exactly the keys A and B"
    if set(answer) != {"A", "B"}:
        return False, "answer keys must be exactly A and B"
    d = inst["dimension"]
    p = inst["p"]
    for name in ("A", "B"):
        ok, reason = _validate_matrix(name, answer[name], d, p)
        if not ok:
            return False, reason

    a = answer["A"]
    b = answer["B"]
    k = inst["k"]
    if d == 2:
        ta = _trace_power_2x2(a, k, p)
        tb = _trace_power_2x2(b, k, p)
        if ta is not None and (ta + tb) % p != _trace(inst["target"], p):
            return False, "trace of A^k+B^k does not equal trace(T)"

    got = _mat_add(_mat_pow(a, k, p), _mat_pow(b, k, p), p)
    mismatches = [(i, j) for i in range(d) for j in range(d)
                  if got[i][j] != inst["target"][i][j]]
    if mismatches:
        i, j = mismatches[0]
        return False, (f"matrix equation mismatch in {len(mismatches)} position(s); "
                       f"first at row {i}, column {j}")
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the unordered pair space after enforcing shape/range."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    p = inst["p"]
    d = inst["dimension"]
    a = [[rng.randrange(p) for _ in range(d)] for _ in range(d)]
    b = [[rng.randrange(p) for _ in range(d)] for _ in range(d)]
    a, b = _ordered_pair(a, b)
    return {"A": a, "B": b}


def search_space(inst: dict) -> int | None:
    """Naive ordered pair count; random_candidate quotients the A/B symmetry."""
    p = inst["p"]
    d = inst["dimension"]
    return p ** (2 * d * d)


def enumerate_all(inst: dict) -> int | None:
    """Count exact witnesses only when at most 500,000 candidates are present."""
    space = search_space(inst)
    if space is None or space > 500_000:
        return None
    p = inst["p"]
    d = inst["dimension"]
    count = 0
    cells = 2 * d * d
    for flat in itertools.product(range(p), repeat=cells):
        split = d * d
        aa = flat[:split]
        bb = flat[split:]
        a = [list(aa[i * d:(i + 1) * d]) for i in range(d)]
        b = [list(bb[i * d:(i + 1) * d]) for i in range(d)]
        if verify(inst, {"A": a, "B": b})[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Exact similarity-and-homogeneity key for generated targets.

    A square-free characteristic polynomial makes the target cyclic, so two
    generated targets over the same field are similar iff their characteristic
    polynomials agree.  Homogeneity also identifies T and s*T when s is a
    nonzero k-th power: witnesses are carried by (A,B)->(cA,cB) for s=c^k.
    For nonzero trace, det(T)/trace(T)^2 and the multiplicative H-coset of the
    trace classify this combined orbit exactly.
    """
    if inst["dimension"] != 2:
        raise ValueError("canonical_key is defined for this family's 2 by 2 instances")
    p = inst["p"]
    k = inst["k"]
    tr = _trace(inst["target"], p)
    if tr == 0:
        raise ValueError("generated targets must have nonzero trace")
    determinant = _det2(inst["target"], p)
    ratio = determinant * pow(tr, p - 3, p) % p
    coset_label = pow(tr, (p - 1) // k, p)
    return json.dumps([p, k, 2, coset_label, ratio], separators=(",", ":"))


def escalate(params: dict) -> dict | None:
    """Increase subgroup index k by 16 while keeping matrix size fixed."""
    if not isinstance(params, dict) or set(params) != {"n"}:
        return None
    n = params["n"]
    if not isinstance(n, int) or isinstance(n, bool):
        return None
    return {"n": n + 4}


def _copy_answer(answer: dict) -> dict:
    return {"A": [row[:] for row in answer["A"]],
            "B": [row[:] for row in answer["B"]]}


def _equation_match_count(inst: dict, answer: dict) -> int:
    p = inst["p"]
    k = inst["k"]
    got = _mat_add(_mat_pow(answer["A"], k, p),
                   _mat_pow(answer["B"], k, p), p)
    return sum(got[i][j] == inst["target"][i][j]
               for i in range(2) for j in range(2))


def _attack_magnitude_split(inst: dict) -> dict:
    p = inst["p"]
    a = _zero(2)
    b = _zero(2)
    for i in range(2):
        for j in range(2):
            t = inst["target"][i][j]
            if t <= p // 2:
                a[i][j] = t
            else:
                b[i][j] = t
    return {"A": a, "B": b}


def _attack_greedy(inst: dict) -> dict:
    p = inst["p"]
    answer = {"A": _zero(2), "B": _zero(2)}
    for name in ("A", "B"):
        for i in range(2):
            for j in range(2):
                t = inst["target"][i][j]
                pool = (0, 1, p - 1, t, (-t) % p)
                best_value = answer[name][i][j]
                best_score = _equation_match_count(inst, answer)
                for value in pool:
                    answer[name][i][j] = value
                    score = _equation_match_count(inst, answer)
                    if score > best_score:
                        best_value, best_score = value, score
                answer[name][i][j] = best_value
    return answer


def _attack_trace_restarts(inst: dict, rng: random.Random, tries: int = 128) -> bool:
    """Conservative success flag for the paper-inspired trace attack.

    A hit only says the trace has a four-term scalar k-th-power decomposition;
    turning it into matrices and extracting the fourth root remains.  Counting
    even this precursor as success makes the attack panel conservative.
    """
    p = inst["p"]
    k = inst["k"]
    target_trace = _trace(inst["target"], p)
    membership_exponent = (p - 1) // k
    for _ in range(tries):
        roots = [rng.randrange(p) for _ in range(3)]
        residual = (target_trace - sum(pow(x, k, p) for x in roots)) % p
        if residual == 0 or pow(residual, membership_exponent, p) == 1:
            return True
    return False


def _transformed_instance(inst: dict, mode: str) -> dict:
    p = inst["p"]
    perm = [[0, 1], [1, 0]]
    perm_inv = perm
    shear = [[1, 1], [0, 1]]
    shear_inv = [[1, p - 1], [0, 1]]

    def spatial(a: list[list[int]]) -> list[list[int]]:
        if mode == "permutation":
            return _conjugate(a, perm, perm_inv, p)
        if mode in ("basis_change", "power_scaling_basis"):
            return _conjugate(a, shear, shear_inv, p)
        if mode in ("transpose", "power_scaling_transpose"):
            return _transpose(a)
        if mode in ("basis_transpose", "power_scaling_basis_transpose"):
            return _conjugate(_transpose(a), shear, shear_inv, p)
        if mode == "power_scaling":
            return [row[:] for row in a]
        raise ValueError(mode)

    scaled = mode.startswith("power_scaling")
    witness_scale = 2 if scaled else 1
    target_scale = pow(witness_scale, inst["k"], p)

    def apply_witness(a: list[list[int]]) -> list[list[int]]:
        moved = spatial(a)
        return [[witness_scale * x % p for x in row] for row in moved]

    def apply_target(a: list[list[int]]) -> list[list[int]]:
        moved = spatial(a)
        return [[target_scale * x % p for x in row] for row in moved]

    out = {key: value for key, value in inst.items() if key != "answer"}
    out["target"] = apply_target(inst["target"])
    out["answer"] = {"A": apply_witness(inst["answer"]["A"]),
                     "B": apply_witness(inst["answer"]["B"])}
    return out


def selftest() -> dict:
    """Run mandatory gates G1--G8 and return their measured report."""
    report: dict[str, Any] = {}

    # G1: every preset, several seeds.
    g1_total = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "verified": g1_total, "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)

    # G2: five corruption classes, and distinct diagnostics.
    corruptions: dict[str, object] = {}
    dropped = _copy_answer(inst["answer"])
    dropped["A"].pop()
    corruptions["drop_one"] = dropped
    duplicated = _copy_answer(inst["answer"])
    duplicated["A"].append(duplicated["A"][0][:])
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = {}
    out_of_range = _copy_answer(inst["answer"])
    out_of_range["A"][0][0] = inst["p"]
    corruptions["out_of_range"] = out_of_range

    # Find a literal swap of two entries that is rejected with a fresh reason.
    original = _copy_answer(inst["answer"])
    positions = [(i, j) for i in range(2) for j in range(2)]
    swapped_answer = None
    for left, right in itertools.combinations(positions, 2):
        trial = _copy_answer(original)
        li, lj = left
        ri, rj = right
        trial["A"][li][lj], trial["A"][ri][rj] = trial["A"][ri][rj], trial["A"][li][lj]
        if trial != original and not verify(inst, trial)[0]:
            swapped_answer = trial
            break
    corruptions["swap_two_entries"] = swapped_answer if swapped_answer is not None else None

    g2_results = {name: verify(inst, value) for name, value in corruptions.items()}
    g2_reasons = [reason for ok, reason in g2_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (all(not ok for ok, _ in g2_results.values())
                 and len(set(g2_reasons)) == len(g2_results)),
        "cases": {name: {"rejected": not ok, "reason": reason}
                  for name, (ok, reason) in g2_results.items()},
        "distinct_reasons": len(set(g2_reasons)),
    }

    # G3: realistic prose and Markdown around the answer tags.
    model_reply = ("I computed the powers modulo p.\n\n```json\n<answer>\n"
                   + json.dumps(inst["answer"])
                   + "\n</answer>\n```\nThe block above is my final witness.")
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_equal": parsed == inst["answer"],
    }

    # G4: structure-aware unordered dense pairs, with all shapes/ranges valid.
    guess_rng = random.Random(0x220504710)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": hits / total,
        "prior": "uniform dense field matrices, quotiented by the obvious A/B swap",
        "naive_ordered_search_space_digits": len(str(search_space(inst))),
    }

    # G5: exact enumeration on a deliberately tiny scalar member of the family.
    tiny = {
        "dimension": 1, "p": 401, "k": 2, "target": [[7]],
        "answer": {"A": [[0]], "B": [[0]]},
    }
    tiny_count = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    tiny_fraction = None if tiny_count is None else tiny_count / tiny_space
    report["G5_sparse"] = {
        "pass": tiny_count is not None and tiny_fraction is not None and tiny_fraction < 0.005,
        "enumerated_solutions": tiny_count,
        "ordered_search_space": tiny_space,
        "solution_fraction": tiny_fraction,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: attacks exploit target magnitude, local greed, and the paper's trace route.
    attack_rows: dict[str, list[dict[str, Any]]] = {
        "magnitude_outlier_split": [],
        "coordinate_greedy": [],
        "trace_random_restart": [],
    }
    for seed in range(8):
        attacked = make_instance(seed=10_000 + seed, **ship_params)
        outlier_ok, _ = verify(attacked, _attack_magnitude_split(attacked))
        greedy_ok, _ = verify(attacked, _attack_greedy(attacked))
        trace_hit = _attack_trace_restarts(attacked, random.Random(90_000 + seed), 128)
        attack_rows["magnitude_outlier_split"].append({"seed": seed, "solved": outlier_ok})
        attack_rows["coordinate_greedy"].append({"seed": seed, "solved": greedy_ok})
        attack_rows["trace_random_restart"].append({
            "seed": seed, "solved": trace_hit, "restarts": 128,
            "note": "counts even a scalar precursor hit as an attack success",
        })
    attack_summary = {}
    for name, rows in attack_rows.items():
        successes = sum(bool(row["solved"]) for row in rows)
        attack_summary[name] = {"successes": successes, "seeds": 8, "runs": rows}
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attack_summary.values()),
        "attacks": attack_summary,
    }

    # G7: doubling n doubles encoded field size and squares the subgroup index.
    doubled = make_instance(n=2 * ship_params["n"], seed=271828)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["k"] > inst["k"]
                 and doubled["p"].bit_length() > inst["p"].bit_length()),
        "base_n": ship_params["n"],
        "doubled_n": 2 * ship_params["n"],
        "base_k_bits": inst["k"].bit_length(),
        "doubled_k_bits": doubled["k"].bit_length(),
        "base_field_bits": inst["p"].bit_length(),
        "doubled_field_bits": doubled["p"].bit_length(),
        "planted_verify": doubled_ok,
        "verify_reason": doubled_reason,
    }

    # G8: exact similarity invariance for cyclic targets, plus real witness maps.
    modes = (
        "permutation", "basis_change", "transpose", "basis_transpose",
        "power_scaling", "power_scaling_basis", "power_scaling_transpose",
        "power_scaling_basis_transpose",
    )
    invariance_checks = 0
    real_transform_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **ship_params)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        for mode in modes:
            moved = _transformed_instance(base, mode)
            invariance_checks += 1
            if canonical_key(moved) != base_key:
                g8_failures.append({"seed": seed, "mode": mode, "kind": "key_changed"})
            ok, reason = verify(moved, moved["answer"])
            real_transform_checks += 1
            if not ok:
                g8_failures.append({"seed": seed, "mode": mode,
                                    "kind": "witness_map_failed", "reason": reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "transformations": list(modes),
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
