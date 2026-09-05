"""Trapdoored binary matrix-vector products from arXiv:2502.13060.

The paper's Section 6 constructs a dense-looking matrix as M = L H + S, with
small inner dimension and sparse S, so that Mv can be evaluated as
L(Hv) + Sv.  This module constructs exact finite-field instances of that
native task.  Dense multiplication is efficient on a computer but onerous by
hand; the supplied trapdoor gives a compact exact route.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # This family needs only exact bit arithmetic.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Matrix multiplication associativity exposes the low inner dimension, "
    "while the correction matrix has one nonzero in each row."
)
PLACEBO_HINT: str = (
    "Exact binary matrix arithmetic rewards careful bookkeeping of row "
    "lengths and the stated zero-based support indices."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "dense matrix over F_2",
        "LPN-style trapdoor factorization M = L H + S",
        "binary column vector",
        "binary product vector",
    ],
    "verification_operations": [
        "exact parity inner product over F_2",
        "exact binary matrix-vector multiplication",
        "bit-for-bit equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Associate Mv as L(Hv)+Sv so the low inner dimension and one-sparse "
        "correction replace a long dense parity computation."
    ),
    "hardness_basis": (
        "Track B: ordinary dense matrix-vector multiplication over F_2 is "
        "O(nm) and at shipping n=128,m=320 uses 81,792 conventional field "
        "operations and measured 0.00020 s in the shipping selftest, while "
        "Section 6's L(Hv)+Sv trapdoor route uses at most 300 exact XORs."
    ),
    "max_answer_tokens": 128,
}

NATIVE: dict = {
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


DIFFICULTY: dict = {
    "demo": {"n": 6, "columns": 12, "inner": 2},
    "easy": {"n": 96, "columns": 192, "inner": 2},
    "medium": {"n": 128, "columns": 256, "inner": 2},
    "hard": {"n": 128, "columns": 320, "inner": 2},
}
SHIPPING_DIFFICULTY: str = "hard"

# Scratch copies used by the G9 harness can expose only the shipping rung
# without changing the default four-rung ladder or the shipped artifacts.
if os.environ.get("GV_G9_ONLY") == "1":
    DIFFICULTY = {"hard": dict(DIFFICULTY[SHIPPING_DIFFICULTY])}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A length-n binary column vector, encoded canonically as one string "
        "of exactly n characters from {0,1}."
    ),
    "bounds": {
        "alphabet_size": 2,
        "length": "exactly the public row count n",
        "max_named_ladder_length": 128,
        "max_atomic_elements": 128,
    },
}

# Patched from the script-owned transcripts after the three oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES: str = """\
Definition 5 in Section 4 fixes a Trapdoored-Matrix as a pseudorandom matrix
plus auxiliary data that makes multiplication faster.  Section 5 fixes the
LPN distribution (L, LH+S), including the convention that S is sparse.
Section 6 supplies the exact native construction and the identity
A(LH+S)=(AL)H+AS; transposed, its matrix-vector form is
(LH+S)v=L(Hv)+Sv.  The certificate producer is therefore an O(nm) dense
matrix-vector algorithm, or the cheaper trapdoor evaluation.  This is not a
Track-A recovery claim.

Section 7 states what makes the cryptographic construction easy: when
delta*mu <= 1/n, subsampling and Gaussian elimination become efficient.  This
benchmark deliberately uses inner dimension 2, gives the factorization to the
solver, and fixes one nonzero of S per row.  It is far outside the paper's
claimed LPN-secure distribution, so its only hardness claim is Track B's
no-tool compression gap.

Generation is by composition of identities.  It samples L, H, S, and v,
forms M=LH+S exactly over F_2, and carries the product through the same
identity.  It never recovers a trapdoor from M.  Balanced nonzero row types of
L and balanced dense H rows avoid degenerate all-zero components; rows and
columns are shuffled from the same construction.  A mild rejection step only
excludes the four explicitly tested heuristic outputs and keeps the compact
route below the 300-operation cap.

The failing attacks are a row-weight threshold, selected-entry majority,
256 uniform legal restarts, and the tempting low-rank-only answer that omits
S.  The successful domain-standard algorithm is ordinary dense binary
matrix-vector multiplication and is reported separately, as Track B
requires.  canonical_key exactly removes row order, column order, and every
invertible change of the two-dimensional trapdoor basis.  Because M is
determined by L,H,S, the key uses the factor data rather than re-encoding M.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000
_ATTACK_SEEDS = tuple(range(91_000, 91_008))
_ENUMERATION_CAP = 1 << 18


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _xor_rows(a: str, b: str) -> str:
    return "".join("1" if x != y else "0" for x, y in zip(a, b))


def _toggle(row: str, position: int) -> str:
    chars = list(row)
    chars[position] = "0" if chars[position] == "1" else "1"
    return "".join(chars)


def _parity_dot(row: str, vector: str) -> int:
    return (int(row, 2) & int(vector, 2)).bit_count() & 1


def _dense_product(inst: dict) -> str:
    vector = inst["vector"]
    return "".join(str(_parity_dot(row, vector)) for row in inst["matrix"])


def _trapdoor_product(inst: dict, include_sparse: bool = True) -> str:
    vector = inst["vector"]
    latent = [_parity_dot(row, vector) for row in inst["H"]]
    out = []
    for row_code, support in zip(inst["L_codes"], inst["S_support"]):
        bit = 0
        for j in range(inst["inner"]):
            if (row_code >> j) & 1:
                bit ^= latent[j]
        if include_sparse:
            bit ^= int(vector[support])
        out.append(str(bit))
    return "".join(out)


def _compact_operation_count(inst: dict) -> int:
    """Optimized XOR count for L(Hv)+Sv; selection/copying is free."""
    vector = inst["vector"]
    operations = 0
    for hrow in inst["H"]:
        selected = sum(a == "1" and b == "1" for a, b in zip(hrow, vector))
        operations += max(0, selected - 1)
    for row_code, support in zip(inst["L_codes"], inst["S_support"]):
        terms = row_code.bit_count() + int(vector[support])
        operations += max(0, terms - 1)
    return operations


def _attack_row_weight(inst: dict) -> str:
    midpoint = inst["columns"] // 2
    return "".join("1" if row.count("1") > midpoint else "0" for row in inst["matrix"])


def _attack_selected_majority(inst: dict) -> str:
    active = [j for j, bit in enumerate(inst["vector"]) if bit == "1"]
    threshold = len(active) / 2
    return "".join(
        "1" if sum(row[j] == "1" for j in active) > threshold else "0"
        for row in inst["matrix"]
    )


def _attack_first_active_column(inst: dict) -> str:
    try:
        column = inst["vector"].index("1")
    except ValueError:
        return "0" * inst["n"]
    return "".join(row[column] for row in inst["matrix"])


def _balanced_bits(length: int, rng: random.Random) -> str:
    bits = ["1"] * (length // 2) + ["0"] * (length - length // 2)
    rng.shuffle(bits)
    return "".join(bits)


def make_instance(
    n: int,
    seed: int = 0,
    columns: int | None = None,
    inner: int = 2,
    **params: Any,
) -> dict:
    """Compose an exact M=LH+S instance and carry its product certificate."""
    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    if not _is_int(n) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if columns is None:
        columns = 2 * n
    if not _is_int(columns) or columns < 4:
        raise ValueError("columns must be an integer at least 4")
    if inner != 2:
        raise ValueError("this family fixes inner=2")

    rng = random.Random(seed)
    # Rejection affects only transparent benchmark regularity, never correctness.
    for _attempt in range(10_000):
        vector = _balanced_bits(columns, rng)
        h0 = _balanced_bits(columns, rng)
        h1 = _balanced_bits(columns, rng)
        if h0 == h1:
            continue
        H = [h0, h1]

        # All three nonzero binary row types occur almost equally often.
        L_codes = [1 + (i % 3) for i in range(n)]
        rng.shuffle(L_codes)
        support = [rng.randrange(columns) for _ in range(n)]
        correction_weight = sum(vector[j] == "1" for j in support)
        if not (n // 3 <= correction_weight <= (2 * n + 2) // 3):
            continue

        matrix: list[str] = []
        for row_code, position in zip(L_codes, support):
            base = "0" * columns
            if row_code & 1:
                base = _xor_rows(base, h0)
            if row_code & 2:
                base = _xor_rows(base, h1)
            matrix.append(_toggle(base, position))

        inst = {
            "n": n,
            "columns": columns,
            "inner": inner,
            "matrix": matrix,
            "L_codes": L_codes,
            "H": H,
            "S_support": support,
            "vector": vector,
        }
        answer = _trapdoor_product(inst)
        # Exclude the exact outputs of the four deterministic cheap probes.
        cheap = {
            _attack_row_weight(inst),
            _attack_selected_majority(inst),
            _attack_first_active_column(inst),
            _trapdoor_product(inst, include_sparse=False),
        }
        if answer in cheap:
            continue
        route_operations = _compact_operation_count(inst)
        if n <= 128 and columns <= 384 and route_operations > 300:
            continue
        inst["answer"] = answer
        inst["route_operations"] = route_operations
        return inst
    raise RuntimeError("could not sample a regular nondegenerate instance")


def render(inst: dict) -> str:
    """Render the complete finite-field problem and its output grammar."""
    lines = [
        "TRAPDOORED BINARY MATRIX-VECTOR PRODUCT",
        "",
        "All arithmetic is over F_2: addition is XOR and multiplication is AND.",
        (
            f"The dense matrix M has n={inst['n']} rows and m={inst['columns']} "
            f"columns.  The trapdoor inner dimension is k={inst['inner']}."
        ),
        "A bitstring lists entries from column 0 on the left to column m-1 on the right.",
        "",
        "The data obey M = L H + S over F_2.  L is encoded by one integer per row:",
        "code 1 means [1,0], code 2 means [0,1], and code 3 means [1,1].",
        (
            "S_support[i]=j means row i of S has its sole 1 in zero-based column j; "
            "all its other entries are 0."
        ),
        "",
        "M rows (row 0 first):",
    ]
    lines.extend(f"{i}: {row}" for i, row in enumerate(inst["matrix"]))
    lines.extend(
        [
            "",
            "L row codes:",
            " ".join(map(str, inst["L_codes"])),
            "",
            "H rows (row 0 first):",
        ]
    )
    lines.extend(f"{i}: {row}" for i, row in enumerate(inst["H"]))
    lines.extend(
        [
            "",
            "S_support:",
            " ".join(map(str, inst["S_support"])),
            "",
            "Input column vector v:",
            inst["vector"],
            "",
            (
                f"Find y=Mv over F_2.  The answer is exactly {inst['n']} bits in row "
                "order, with no separators."
            ),
            "Give your final answer inside <answer></answer> tags, as one binary bitstring.",
            "Example: <answer>010011</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: Any) -> str | None:
    """Extract the canonical binary vector from tagged model output."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    if not body or re.fullmatch(r"[01]+", body) is None:
        return None
    return body


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Check a candidate by exact dense multiplication; never read the plant."""
    if not isinstance(answer, str):
        return False, "answer must be a binary string"
    if answer == "":
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) < n:
        return False, f"answer is short: expected {n} bits"
    if len(answer) > n:
        return False, f"answer has surplus bits: expected {n}"
    if re.fullmatch(r"[01]+", answer) is None:
        return False, "answer contains a non-binary entry"
    expected = _dense_product(inst)
    if answer != expected:
        first = next(i for i, (a, b) in enumerate(zip(answer, expected)) if a != b)
        return False, f"incorrect product bit at row {first}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> str:
    """Sample uniformly from all correctly shaped binary output vectors."""
    return format(rng.getrandbits(inst["n"]), f"0{inst['n']}b")


def search_space(inst: dict) -> int:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the declared language only when the cap permits it."""
    size = search_space(inst)
    if size > _ENUMERATION_CAP:
        return None
    count = 0
    for value in range(size):
        candidate = format(value, f"0{inst['n']}b")
        count += int(verify(inst, candidate)[0])
    return count


def _gl2() -> list[tuple[int, int, int, int]]:
    return [
        (a, b, c, d)
        for a in range(2)
        for b in range(2)
        for c in range(2)
        for d in range(2)
        if (a * d - b * c) & 1
    ]


def _transform_l(code: int, q: tuple[int, int, int, int]) -> int:
    a, b, c, d = q
    x, y = code & 1, (code >> 1) & 1
    return (x * a ^ y * c) | ((x * b ^ y * d) << 1)


def _transform_h(code: int, q: tuple[int, int, int, int]) -> int:
    # Q^-1 = [[d,b],[c,a]] over F_2 for det(Q)=1.
    a, b, c, d = q
    x, y = code & 1, (code >> 1) & 1
    return (d * x ^ b * y) | ((c * x ^ a * y) << 1)


def _canonical_payload(inst: dict, q: tuple[int, int, int, int]) -> tuple:
    transformed_l = [_transform_l(code, q) for code in inst["L_codes"]]
    targets: list[list[int]] = [[] for _ in range(inst["columns"])]
    for code, position in zip(transformed_l, inst["S_support"]):
        targets[position].append(code)
    columns = []
    for j in range(inst["columns"]):
        hcode = int(inst["H"][0][j]) | (int(inst["H"][1][j]) << 1)
        hcode = _transform_h(hcode, q)
        columns.append((int(inst["vector"][j]), hcode, tuple(sorted(targets[j]))))
    return inst["n"], inst["columns"], tuple(sorted(columns))


def canonical_key(inst: dict) -> str:
    """Remove row/column order and GL(2,F_2) trapdoor-basis changes."""
    payload = min(_canonical_payload(inst, q) for q in _gl2())
    blob = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _relabel(
    inst: dict,
    row_order: list[int],
    column_order: list[int],
    q: tuple[int, int, int, int],
) -> dict:
    """Apply a genuine isomorphism; used only by the G8 audit."""
    inverse_column = {old: new for new, old in enumerate(column_order)}
    transformed_l = [_transform_l(code, q) for code in inst["L_codes"]]
    old_hcodes = [
        int(inst["H"][0][j]) | (int(inst["H"][1][j]) << 1)
        for j in range(inst["columns"])
    ]
    transformed_hcodes = [_transform_h(code, q) for code in old_hcodes]
    h0 = "".join(str(transformed_hcodes[j] & 1) for j in column_order)
    h1 = "".join(str((transformed_hcodes[j] >> 1) & 1) for j in column_order)
    out = {
        "n": inst["n"],
        "columns": inst["columns"],
        "inner": inst["inner"],
        "matrix": [
            "".join(inst["matrix"][i][j] for j in column_order) for i in row_order
        ],
        "L_codes": [transformed_l[i] for i in row_order],
        "H": [h0, h1],
        "S_support": [inverse_column[inst["S_support"][i]] for i in row_order],
        "vector": "".join(inst["vector"][j] for j in column_order),
        "answer": "".join(inst["answer"][i] for i in row_order),
    }
    out["route_operations"] = _compact_operation_count(out)
    return out


def escalate(params: dict) -> dict | str | None:
    """Grow dense column work while keeping the output vector fixed."""
    current = dict(params)
    columns = int(current.get("columns", 2 * int(current["n"])))
    if columns < 384:
        current["columns"] = min(384, columns + 64)
        return current
    return "cap_bound"


def _corruptions(inst: dict) -> dict[str, str]:
    answer = inst["answer"]
    different = next((i for i in range(1, len(answer)) if answer[i] != answer[0]), None)
    if different is None:
        swapped = ("1" if answer[0] == "0" else "0") + answer[1:]
    else:
        chars = list(answer)
        chars[0], chars[different] = chars[different], chars[0]
        swapped = "".join(chars)
    middle = len(answer) // 2
    return {
        "empty": "",
        "drop": answer[:-1],
        "surplus_duplicate": answer + answer[-1],
        "swap": swapped,
        "out_of_range": answer[:middle] + "2" + answer[middle + 1 :],
    }


def _run_attack_panel(params: dict) -> tuple[dict, dict]:
    names = {
        "outlier_row_weight": _attack_row_weight,
        "greedy_selected_majority": _attack_selected_majority,
        "first_active_column_proxy": _attack_first_active_column,
        "low_rank_ignore_sparse": lambda x: _trapdoor_product(x, include_sparse=False),
    }
    results = {name: {"successes": 0, "attempts": 0} for name in names}
    results["uniform_random_restart_256"] = {"successes": 0, "attempts": 0}
    dense_successes = 0
    dense_elapsed = 0.0
    dense_operations = 0
    for seed in _ATTACK_SEEDS:
        inst = make_instance(seed=seed, **params)
        for name, attack in names.items():
            candidate = attack(inst)
            results[name]["successes"] += int(verify(inst, candidate)[0])
            results[name]["attempts"] += 1
        attack_rng = random.Random(seed ^ 0x5A17C3)
        found = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, attack_rng))[0]:
                found = True
                break
        results["uniform_random_restart_256"]["successes"] += int(found)
        results["uniform_random_restart_256"]["attempts"] += 1

        started = time.perf_counter()
        candidate = _dense_product(inst)
        dense_elapsed += time.perf_counter() - started
        dense_successes += int(verify(inst, candidate)[0])
        dense_operations += 2 * inst["n"] * inst["columns"] - inst["n"]
    reference = {
        "name": "ordinary dense matrix-vector multiplication over F_2",
        "complexity": "O(n*m) exact field operations",
        "wall_clock_sec": dense_elapsed,
        "operations": dense_operations,
        "operations_per_instance": dense_operations // len(_ATTACK_SEEDS),
        "solves": f"{dense_successes}/{len(_ATTACK_SEEDS)}, as expected",
    }
    return results, reference


def selftest() -> dict:
    """Run all mandatory gates and return their measured evidence."""
    report: dict[str, Any] = {
        "paper": "2502.13060",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=73_311, **shipping_params)
    reasons: dict[str, str] = {}
    rejected = 0
    for name, corrupt in _corruptions(shipping).items():
        ok, why = verify(shipping, corrupt)
        rejected += int(not ok)
        reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": rejected == 5 and len(set(reasons.values())) == 5,
        "rejected": rejected,
        "attempts": 5,
        "reasons": reasons,
    }

    response = (
        "I used the sparse trapdoor rather than expanding every row.\n```text\n"
        f"<answer>{shipping['answer']}</answer>\n```\nThat is the exact binary vector."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed_length": len(parsed) if parsed is not None else None,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(0x250213060)
    guess_hits = 0
    for _ in range(_GUESS_SAMPLES):
        guess_hits += int(random_candidate(shipping, guess_rng) == shipping["answer"])
    guess_rate = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "observed_probability": guess_rate,
        "candidate_space": search_space(shipping),
        "sampling_prior": "uniform over every correctly shaped n-bit output vector",
    }

    started = time.perf_counter()
    baseline_answer = _dense_product(shipping)
    baseline_elapsed = time.perf_counter() - started
    baseline_ok = verify(shipping, baseline_answer)[0]
    exact_demo_count = enumerate_all(make_instance(seed=19, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": baseline_ok and exact_demo_count == 1 and guess_rate < 1e-6,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_observed_solution_fraction": guess_rate,
        "demo_exact_solution_count": exact_demo_count,
        "demo_candidate_count": 1 << DIFFICULTY["demo"]["n"],
        "baseline_wall_clock_sec": baseline_elapsed,
        "baseline_row_dot_products": shipping["n"],
        "baseline_field_operations": 2 * shipping["n"] * shipping["columns"] - shipping["n"],
    }

    attacks, reference = _run_attack_panel(shipping_params)
    panel_pass = len(attacks) >= 4 and all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": panel_pass,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["columns"] *= 2
    doubled = make_instance(seed=7_007, **doubled_params)
    escalated_params = escalate(shipping_params)
    escalated_ok = False
    if isinstance(escalated_params, dict):
        escalated = make_instance(seed=7_008, **escalated_params)
        escalated_ok = verify(escalated, escalated["answer"])[0]
    report["G7_scales"] = {
        "pass": (
            verify(doubled, doubled["answer"])[0]
            and search_space(doubled) > search_space(shipping)
            and escalated_ok
        ),
        "shipping_shape": [shipping["n"], shipping["columns"]],
        "doubled_shape": [doubled["n"], doubled["columns"]],
        "shipping_search_bits": shipping["n"],
        "doubled_search_bits": doubled["n"],
        "escalated_params": escalated_params,
    }

    invariant_checks = 0
    carried_witness_checks = 0
    keys = []
    gl = _gl2()
    for offset in range(20):
        inst = make_instance(seed=120_000 + offset, **shipping_params)
        original_key = canonical_key(inst)
        keys.append(original_key)
        relabel_rng = random.Random(220_000 + offset)
        rows = list(range(inst["n"]))
        columns = list(range(inst["columns"]))
        relabel_rng.shuffle(rows)
        relabel_rng.shuffle(columns)
        transformations = [
            (rows, list(range(inst["columns"])), gl[0]),
            (list(range(inst["n"])), columns, gl[0]),
            (list(range(inst["n"])), list(range(inst["columns"])), gl[(offset + 1) % len(gl)]),
            (rows, columns, gl[(offset + 2) % len(gl)]),
        ]
        for row_order, column_order, q in transformations:
            moved = _relabel(inst, row_order, column_order, q)
            invariant_checks += int(canonical_key(moved) == original_key)
            carried_witness_checks += int(verify(moved, moved["answer"])[0])
    distinct_keys = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 80
            and carried_witness_checks == 80
            and distinct_keys == 20
        ),
        "invariance_checks_passed": invariant_checks,
        "invariance_checks_total": 80,
        "carried_witness_checks_passed": carried_witness_checks,
        "carried_witness_checks_total": 80,
        "unrelated_distinct_keys": distinct_keys,
        "unrelated_instances": 20,
        "symmetries": ["row permutation", "column permutation", "GL(2,F_2) basis change", "compositions"],
    }

    answer_chars = len(json.dumps(shipping["answer"]))
    answer_tokens = len(shipping["answer"])  # conservative: at most one token per bit
    arms = {
        arm: {
            "solved": int(values.get("solved", 0)),
            "attempts": int(values.get("attempts", 0)),
        }
        for arm, values in G9_ORACLE_RESULTS.items()
        if arm in {"bare", "hinted", "placebo"}
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2_000
        and shipping["n"] <= 256
        and shipping["route_operations"] <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": shipping["n"],
        "intended_route_operations": shipping["route_operations"],
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
