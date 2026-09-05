"""Verified Mod/Resc parsimony generator for arXiv:1002.1292.

Section 2 of the paper defines the asymmetric Boolean row product.  This
module inverse-generates affine, block-diagonal instances of that product.
Each short affine certificate expands to the paper's two Boolean factor
matrices.  A skew difference set simultaneously supplies a fooling set whose
size equals the number of factor columns, so the submitted width is provably
minimal rather than merely feasible.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # The implementation is standard-library-complete; helpers are optional.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "Boolean compatibility matrix",
        "Boolean Mod and rescue factor matrices",
        "affine finite-field specification of the factor matrices",
    ],
    "verification_operations": [
        "exact arithmetic modulo a prime",
        "exact expansion of Boolean factor entries",
        "paper-defined asymmetric Boolean row product",
        "exact fooling-set cross-entry comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "First and centered-third moments of the 1-column labels transform "
        "affinely, recovering the hidden Mod/Resc coordinate maps; without "
        "that invariant one must scan the bounded affine certificate space."
    ),
    "hardness_basis": (
        "Track B: exhaustive affine-certificate enumeration is a polynomial "
        "O(b*p^5) exact algorithm for this generated subclass; at shipping "
        "p=41,b=2, eight measured runs used 911,832 Boolean membership tests "
        "in 0.568 seconds total, while the displayed moment invariants reduce "
        "a certificate to at most 48 modular operations."
    ),
    "max_answer_tokens": 16,
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
    "easy": {"n": 41, "blocks": 2},
}

SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "Within each block, the first and centered-third moments of a row's 1-column labels transform affinely."
)
PLACEBO_HINT: str = (
    "Within each block, careful use of the displayed residues helps keep the modular bookkeeping consistent."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One JSON object with a blocks list in block-index order; every entry "
        "is {\"a\":a,\"c\":c,\"delta\":d}, where a and c are distinct "
        "nonzero residues modulo p and d is any residue.  These affine triples "
        "succinctly and exactly define the two Boolean factor matrices."
    ),
    "bounds": {
        "block_count": "instance field blocks_count",
        "fields_per_block": 3,
        "a_range": "1..p-1",
        "c_range": "1..p-1 and c != a",
        "delta_range": "0..p-1",
        "candidates_per_block": "p*(p-1)*(p-2)",
    },
}

# Replaced after the three script-owned oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES: str = r"""
Definition and exact certificate. Section 2, Definitions 1--3, fixes
U tensor V as 1 exactly when some coordinate has U[i]=1 and V[i]=0,
extends it row-by-row, and asks for M,R of minimum common width k. Section 3,
Theorem 1 identifies a width-k factorization with a k-biclique edge cover.
The generator stays with the paper's Boolean matrices; the finite-field affine
triples are a succinct exact specification of M and R, not a graph surrogate.

STEP 0 and the hardness track. Theorem 2 says the unrestricted optimization
problem is NP-complete and hard to approximate, but that worst-case statement
does not establish this distribution. Section 4 is the decisive easy-result:
Rules 1--4 give O(N^3) kernelization, and Theorem 4 gives an FPT algorithm of
O(2^(k*2^(k-1)+3k)+N^3). Small k is therefore not a Track-A regime. This
module declares Track B. Its generated affine language also has a simpler
polynomial reference algorithm: enumerate the p*(p-1)*(p-2) triples per block
and compare their predicted Boolean product. The worst case is O(b*p^5); the
selftest records actual membership tests and wall time at the shipping preset.

Generation and parsimony. In each block, D contains 0 and exactly one of x and
-x for every nonzero residue pair. The generator samples distinct nonzero a,c
and delta, then sets C[x,y]=1 iff c*y+delta-a*x lies in D. The submitted triple
defines a width-p pair of Boolean matrices: row x has its single 1 at gene a*x,
and rescue row y has a 0 at gene g exactly when c*y+delta-g is in D. Their
paper-defined product is C. For every gene g, pair row a^(-1)g with column
c^(-1)(g-delta). Its C-entry is 1. Two such pairs have cross differences z and
-z, so at least one cross-entry is 0; pairs from distinct blocks have both
cross-entries 0. Thus no biclique/factor column can cover two pairs. The b*p
pairs prove k>=b*p, meeting the constructed width. This certificate is known
by inverse generation and a composable identity, never by solving C.

Compact route. Let w=|D|, S_D=sum(D), and T_D be D's centered third moment in
F_p. For row x let S_x be the sum of its 1-column labels. If q=c^(-1), then
S_x=q*(S_D+w*(a*x-delta)), while the centered third moment of any row is
q^3*T_D. Because every supported p is 2 modulo 3, cubing is bijective. The
three displayed aggregates S_0,S_1,T_0 therefore recover c, then a and delta
in at most 24 modular operations per block. This is the intended insight.

Attack hardening. Every row and column has exactly |D| ones, so degrees carry
no parameter information. Random presentation order removes positional
outliers. The boundary-pair greedy guess treats two sorted residues as
corresponding; the linear-moment ansatz deliberately misses the cubic scale;
and 256 uniform affine restarts are negligible against the product language.
The generator also requires D to have no nonidentity affine stabilizer, so
these misses cannot accidentally describe the same factorization.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value: int) -> bool:
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_supported_prime(value: int) -> int:
    candidate = max(11, int(value))
    while not (_is_prime(candidate) and candidate % 3 == 2):
        candidate += 1
    return candidate


def _validate_parameters(n: int, blocks: int) -> None:
    if not _is_int(n) or n < 11 or not _is_prime(n) or n % 3 != 2:
        raise ValueError("n must be a prime at least 11 with n congruent to 2 modulo 3")
    if not _is_int(blocks) or not 1 <= blocks <= 8:
        raise ValueError("blocks must be an integer from 1 through 8")


def _central_third(values, p: int) -> tuple[int, int]:
    values = list(values)
    width = len(values)
    total = sum(values) % p
    mean = total * pow(width, -1, p) % p
    third = sum(pow((value - mean) % p, 3, p) for value in values) % p
    return total, third


def _affine_stabilizers(values, p: int) -> list[tuple[int, int]]:
    target = set(values)
    return [
        (u, v)
        for u in range(1, p)
        for v in range(p)
        if {(u * x + v) % p for x in target} == target
    ]


def _draw_skew_set(p: int, rng: random.Random) -> list[int]:
    half = (p - 1) // 2
    for _attempt in range(20_000):
        values = {0}
        for x in range(1, half + 1):
            values.add(x if rng.getrandbits(1) else (-x) % p)
        _total, third = _central_third(values, p)
        if third and _affine_stabilizers(values, p) == [(1, 0)]:
            return sorted(values)
    raise RuntimeError("could not sample a rigid skew difference set")


def _canonical_difference_set(values, p: int) -> str:
    best = None
    for u in range(1, p):
        for v in range(p):
            mask = 0
            for x in values:
                mask |= 1 << ((u * x + v) % p)
            if best is None or mask < best:
                best = mask
    return format(best or 0, f"0{p}b")


def _make_block(p: int, rng: random.Random, used_shapes: set[str]) -> tuple[dict, dict]:
    for _attempt in range(2_000):
        difference_set = _draw_skew_set(p, rng)
        shape = _canonical_difference_set(difference_set, p)
        if shape not in used_shapes:
            used_shapes.add(shape)
            break
    else:
        raise RuntimeError("could not sample distinct block shapes")

    a = rng.randrange(2, p)
    c = rng.randrange(2, p)
    while c == a:
        c = rng.randrange(2, p)
    delta = rng.randrange(p)
    sum_d, third_d = _central_third(difference_set, p)
    dset = set(difference_set)

    local_rows = []
    for x in range(p):
        local_rows.append([
            1 if (c * y + delta - a * x) % p in dset else 0
            for y in range(p)
        ])
    width = len(difference_set)
    row_sums = [
        sum(y for y, bit in enumerate(local_rows[x]) if bit) % p
        for x in (0, 1)
    ]
    mean0 = row_sums[0] * pow(width, -1, p) % p
    third0 = sum(
        pow((y - mean0) % p, 3, p)
        for y, bit in enumerate(local_rows[0])
        if bit
    ) % p
    metadata = {
        "D": difference_set,
        "sum_D": sum_d,
        "third_D": third_d,
        "row0_sum": row_sums[0],
        "row1_sum": row_sums[1],
        "row0_third": third0,
    }
    answer = {"a": a, "c": c, "delta": delta}
    return {"metadata": metadata, "rows": local_rows}, answer


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a native minimum-width Mod/Resc factorization."""
    if set(params) != {"blocks"}:
        unknown = sorted(set(params) - {"blocks"})
        detail = "missing blocks" if "blocks" not in params else "unknown parameters: " + ", ".join(unknown)
        raise TypeError(detail)
    blocks = params["blocks"]
    _validate_parameters(n, blocks)
    if not _is_int(seed):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    used_shapes: set[str] = set()
    raw_blocks = []
    answers = []
    for block_id in range(blocks):
        block, answer = _make_block(n, rng, used_shapes)
        metadata = dict(block["metadata"])
        metadata["id"] = block_id
        raw_blocks.append({"metadata": metadata, "rows": block["rows"]})
        answers.append(answer)

    row_labels = [(b, x) for b in range(blocks) for x in range(n)]
    column_labels = [(b, y) for b in range(blocks) for y in range(n)]
    rng.shuffle(row_labels)
    rng.shuffle(column_labels)

    rows = []
    for b, x in row_labels:
        bits = []
        for cb, y in column_labels:
            bits.append(str(raw_blocks[b]["rows"][x][y]) if cb == b else "0")
        rows.append({"block": b, "x": x, "bits": "".join(bits)})

    return {
        "family": "Affine Mod/Resc Parsimony Inference",
        "p": n,
        "blocks_count": blocks,
        "factor_width": blocks * n,
        "blocks": [block["metadata"] for block in raw_blocks],
        "columns": [
            {"block": b, "y": y} for b, y in column_labels
        ],
        "rows": rows,
        "answer": {"blocks": answers},
    }


def render(inst: dict) -> str:
    """Render a self-contained exact Boolean-factorization problem."""
    p = inst["p"]
    block_lines = []
    for data in sorted(inst["blocks"], key=lambda item: item["id"]):
        block_lines.append(
            "Block {id}: D={D}; sum_D={sum_D}; third_D={third_D}; "
            "row0_sum={row0_sum}; row1_sum={row1_sum}; "
            "row0_third={row0_third}".format(**data)
        )
    column_lines = []
    chunk = []
    for index, column in enumerate(inst["columns"]):
        chunk.append(f"{index}=(b{column['block']},y{column['y']})")
        if len(chunk) == 8:
            column_lines.append("  " + "  ".join(chunk))
            chunk = []
    if chunk:
        column_lines.append("  " + "  ".join(chunk))
    row_lines = [
        f"  {index}: (b{row['block']},x{row['x']}) {row['bits']}"
        for index, row in enumerate(inst["rows"])
    ]

    example_blocks = [
        {"a": 1, "c": 2, "delta": 0}
        for _ in range(inst["blocks_count"])
    ]
    example = json.dumps({"blocks": example_blocks}, separators=(",", ":"))
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""MOD/RESC PARSIMONY INFERENCE — AFFINE CERTIFICATE

All arithmetic on labels in this problem is modulo the prime p={p}. There are
{inst['blocks_count']} blocks and k={inst['factor_width']} genes, labelled
(block,g) with g in 0,...,{p - 1}. Rows represent Mod strains and columns
represent rescue strains. The displayed Boolean compatibility matrix C has
{len(inst['rows'])} rows and {len(inst['columns'])} columns. Matrix rows and
columns are deliberately shown in unrelated orders; their block and local
labels are given below. Bit 1 means incompatible and bit 0 means compatible.

For Boolean length-k rows U,V define U tensor V to be 1 exactly when at least
one coordinate has U[g]=1 and V[g]=0; otherwise it is 0. Applied row-by-row,
this is the paper's Mod/Resc matrix product C=M tensor R.

Your certificate contains one affine triple (a,c,delta) for each block, in
block index order. Both a and c must lie in 1,...,{p - 1}, they must be
different, and delta lies in 0,...,{p - 1}. The triple defines full Boolean
factor matrices of common width k as follows.

* Mod row (block b,label x) has its only 1 at gene (b,a*x).
* Rescue row (block b,label y) has 0 at gene (b,g) exactly when
  c*y+delta-g modulo p belongs to that block's displayed set D. It has 1 at
  all other genes, including genes of other blocks.

The certificate is valid when these exact matrices satisfy every displayed
bit of C=M tensor R. It is then automatically parsimonious: each D contains 0
and exactly one of z and -z for every nonzero z. Pairing each gene g with Mod
row a^(-1)g and rescue column c^(-1)(g-delta) gives k 1-entries such that no
one factor coordinate can cover two of them. Thus k factors are necessary as
well as sufficient; this is an exactly checkable fooling-set lower bound.

For audit, each block also gives exact residues useful for checking structure.
sum_D is the sum of D. third_D is sum((d-mean_D)^3 for d in D), where
mean_D=sum_D/|D| in F_p. row0_sum and row1_sum are the sums of local column
labels y at 1-bits in local rows x=0 and x=1. row0_third is the analogous
centered third moment for row x=0. All six quantities are residues modulo p.

BLOCK DATA
{chr(10).join(block_lines)}

DISPLAYED COLUMN ORDER
{chr(10).join(column_lines)}

DISPLAYED MATRIX ROWS: displayed-index: (block,local-x) bitstring
{chr(10).join(row_lines)}{hint}

Give your final answer inside <answer></answer> tags as one compact JSON object
with exactly the key \"blocks\" and entries {{\"a\":int,\"c\":int,\"delta\":int}}.
Example format: <answer>{example}</answer>
Output nothing else inside the tags."""


def parse_answer(text):
    """Extract the tagged JSON certificate from arbitrary surrounding prose."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def _validate_instance_math(inst: dict) -> tuple[bool, str]:
    p = inst.get("p")
    count = inst.get("blocks_count")
    if not _is_int(p) or not _is_prime(p) or p % 3 != 2:
        return False, "instance modulus is not a supported prime"
    if not _is_int(count) or count != len(inst.get("blocks", [])):
        return False, "instance block metadata is inconsistent"
    if len(inst.get("rows", [])) != count * p or len(inst.get("columns", [])) != count * p:
        return False, "instance matrix dimensions are inconsistent"
    if inst.get("factor_width") != count * p:
        return False, "instance factor width is inconsistent"
    width = (p + 1) // 2
    for expected_id, block in enumerate(sorted(inst["blocks"], key=lambda item: item.get("id", -1))):
        if block.get("id") != expected_id:
            return False, "instance block identifiers are inconsistent"
        values = block.get("D")
        if not isinstance(values, list) or len(values) != width or len(set(values)) != width:
            return False, f"block {expected_id} difference-set size is invalid"
        if any(not _is_int(x) or not 0 <= x < p for x in values) or 0 not in values:
            return False, f"block {expected_id} difference-set entries are invalid"
        dset = set(values)
        for x in range(1, p):
            if ((x in dset) + ((-x) % p in dset)) != 1:
                return False, f"block {expected_id} is not skew"
    expected_labels = {(block, value) for block in range(count) for value in range(p)}
    row_labels = {(row.get("block"), row.get("x")) for row in inst.get("rows", [])}
    column_labels = {
        (column.get("block"), column.get("y"))
        for column in inst.get("columns", [])
    }
    if row_labels != expected_labels or len(row_labels) != len(inst["rows"]):
        return False, "instance row labels are inconsistent"
    if column_labels != expected_labels or len(column_labels) != len(inst["columns"]):
        return False, "instance column labels are inconsistent"
    return True, "ok"


def _verify_fooling_set(inst: dict, certificates: list[dict]) -> tuple[bool, str]:
    """Execute the parsimonious lower bound as a finite exact check.

    Each (block,gene) supplies one displayed 1-entry.  If every two selected
    entries have a zero in at least one cross-position, no biclique can cover
    both, so any factorization needs at least as many columns as this set.
    """
    p = inst["p"]
    row_index = {
        (row["block"], row["x"]): index
        for index, row in enumerate(inst["rows"])
    }
    column_index = {
        (column["block"], column["y"]): index
        for index, column in enumerate(inst["columns"])
    }
    selected = []
    for block_id, certificate in enumerate(certificates):
        inv_a = pow(certificate["a"], -1, p)
        inv_c = pow(certificate["c"], -1, p)
        for gene in range(p):
            ri = row_index[(block_id, inv_a * gene % p)]
            ci = column_index[
                (block_id, inv_c * (gene - certificate["delta"]) % p)
            ]
            if inst["rows"][ri]["bits"][ci] != "1":
                return False, "fooling-set diagonal entry is not 1"
            selected.append((ri, ci))
    for first, (row_a, column_a) in enumerate(selected):
        for row_b, column_b in selected[first + 1:]:
            cross_ab = inst["rows"][row_a]["bits"][column_b] == "1"
            cross_ba = inst["rows"][row_b]["bits"][column_a] == "1"
            if cross_ab and cross_ba:
                return False, "two fooling-set entries lie in one biclique"
    return True, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any certificate in the declared affine matrix language."""
    instance_ok, reason = _validate_instance_math(inst)
    if not instance_ok:
        return False, reason
    if not isinstance(answer, dict) or set(answer) != {"blocks"}:
        return False, "answer must be an object with exactly the key blocks"
    certificates = answer["blocks"]
    if not isinstance(certificates, list):
        return False, "blocks must be a list"
    if len(certificates) != inst["blocks_count"]:
        return False, "block count mismatch"
    p = inst["p"]
    dsets = {block["id"]: set(block["D"]) for block in inst["blocks"]}
    for block_id, certificate in enumerate(certificates):
        if not isinstance(certificate, dict) or set(certificate) != {"a", "c", "delta"}:
            return False, f"block {block_id} must have exactly a, c, and delta"
        a, c, delta = certificate["a"], certificate["c"], certificate["delta"]
        if any(not _is_int(value) for value in (a, c, delta)):
            return False, f"block {block_id} entries must be integers"
        if not (1 <= a < p and 1 <= c < p and 0 <= delta < p):
            return False, f"block {block_id} field element out of range"
        if a == c:
            return False, f"block {block_id} row and column multipliers must differ"

    for row_index, row in enumerate(inst["rows"]):
        if (
            not isinstance(row.get("bits"), str)
            or len(row["bits"]) != inst["blocks_count"] * p
            or set(row["bits"]) - {"0", "1"}
        ):
            return False, f"instance contains a malformed matrix row {row_index}"
        rb, x = row["block"], row["x"]
        certificate = certificates[rb]
        a, c, delta = certificate["a"], certificate["c"], certificate["delta"]
        for column_index, column in enumerate(inst["columns"]):
            if rb != column["block"]:
                predicted = 0
            else:
                predicted = int(
                    (c * column["y"] + delta - a * x) % p in dsets[rb]
                )
            if predicted != (row["bits"][column_index] == "1"):
                return False, (
                    f"product mismatch at displayed row {row_index}, "
                    f"column {column_index}"
                )
    lower_bound_ok, lower_bound_reason = _verify_fooling_set(inst, certificates)
    if not lower_bound_ok:
        return False, lower_bound_reason
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from the normalized affine certificate language."""
    p = inst["p"]
    blocks = []
    for _ in range(inst["blocks_count"]):
        a = rng.randrange(1, p)
        c_index = rng.randrange(p - 2)
        choices = [value for value in range(1, p) if value != a]
        c = choices[c_index]
        blocks.append({"a": a, "c": c, "delta": rng.randrange(p)})
    return {"blocks": blocks}


def search_space(inst) -> int:
    """Return the exact cardinality of the declared certificate language."""
    p = inst["p"]
    return (p * (p - 1) * (p - 2)) ** inst["blocks_count"]


def _local_matrix(inst, block_id: int) -> list[list[int]]:
    p = inst["p"]
    columns = {
        (column["block"], column["y"]): index
        for index, column in enumerate(inst["columns"])
    }
    rows = {row["x"]: row for row in inst["rows"] if row["block"] == block_id}
    return [
        [int(rows[x]["bits"][columns[(block_id, y)]]) for y in range(p)]
        for x in range(p)
    ]


def _enumerate_block(inst, block_id: int, stop_after_first: bool) -> tuple[list[dict], int]:
    p = inst["p"]
    matrix = _local_matrix(inst, block_id)
    dset = set(next(block["D"] for block in inst["blocks"] if block["id"] == block_id))
    # The mixed probe order makes early rejection representative of the full
    # matrix rather than accidentally privileging the first displayed row.
    probes = [(x, y, matrix[x][y]) for x in range(p) for y in range(p)]
    probe_rng = random.Random(0x10021292 + block_id)
    probe_rng.shuffle(probes)
    found = []
    operations = 0
    for a in range(1, p):
        for c in range(1, p):
            if a == c:
                continue
            for delta in range(p):
                for x, y, expected in probes:
                    operations += 1
                    got = (c * y + delta - a * x) % p in dset
                    if got != bool(expected):
                        break
                else:
                    found.append({"a": a, "c": c, "delta": delta})
                    if stop_after_first:
                        return found, operations
    return found, operations


def enumerate_all(inst) -> int | None:
    """Count all valid certificates exactly when the affine scan is capped."""
    p = inst["p"]
    work_bound = inst["blocks_count"] * p * (p - 1) * (p - 2)
    if work_bound > 2_100_000:
        return None
    count = 1
    for block_id in range(inst["blocks_count"]):
        solutions, _operations = _enumerate_block(inst, block_id, False)
        count *= len(solutions)
    return count


def canonical_key(inst) -> str:
    """Key on affine-normalized block shapes, ignoring all presentation labels."""
    p = inst["p"]
    shapes = sorted(_canonical_difference_set(block["D"], p) for block in inst["blocks"])
    payload = json.dumps(
        {"p": p, "blocks": inst["blocks_count"], "shapes": shapes},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    """Raise affine entropy/ambient size without lengthening each block witness."""
    current = dict(params)
    p = current["n"]
    blocks = current["blocks"]
    if blocks < 3:
        current["blocks"] = blocks + 1
        return current
    next_p = _next_supported_prime(p + max(12, p // 2))
    if next_p * blocks > 900:
        return "cap_bound"
    current["n"] = next_p
    return current


def _recover_by_moments(inst) -> dict:
    """The compact Track-B route, using only the displayed audit residues."""
    p = inst["p"]
    width = (p + 1) // 2
    inv_width = pow(width, -1, p)
    cube_root_exponent = pow(3, -1, p - 1)
    answer = []
    for block in sorted(inst["blocks"], key=lambda item: item["id"]):
        ratio = block["row0_third"] * pow(block["third_D"], -1, p) % p
        q = pow(ratio, cube_root_exponent, p)
        c = pow(q, -1, p)
        a = (block["row1_sum"] - block["row0_sum"]) * c * inv_width % p
        delta = (block["sum_D"] - c * block["row0_sum"]) * inv_width % p
        answer.append({"a": a, "c": c, "delta": delta})
    return {"blocks": answer}


def _reference_algorithm(inst) -> tuple[object | None, dict]:
    started = time.perf_counter()
    answer = []
    operations = 0
    for block_id in range(inst["blocks_count"]):
        found, used = _enumerate_block(inst, block_id, True)
        operations += used
        if not found:
            return None, {
                "membership_tests": operations,
                "wall_clock_sec": time.perf_counter() - started,
            }
        answer.append(found[0])
    return {"blocks": answer}, {
        "membership_tests": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _fixed_degree_attack(inst) -> dict:
    return {
        "blocks": [
            {"a": 1, "c": 2, "delta": 0}
            for _ in range(inst["blocks_count"])
        ]
    }


def _linear_moment_attack(inst) -> dict:
    p = inst["p"]
    width_inverse = pow((p + 1) // 2, -1, p)
    blocks = []
    for data in sorted(inst["blocks"], key=lambda item: item["id"]):
        c = 1
        a = (data["row1_sum"] - data["row0_sum"]) * width_inverse % p
        if a in (0, c):
            a = 2
        delta = (data["sum_D"] - data["row0_sum"]) * width_inverse % p
        blocks.append({"a": a, "c": c, "delta": delta})
    return {"blocks": blocks}


def _boundary_greedy_attack(inst) -> dict:
    p = inst["p"]
    width_inverse = pow((p + 1) // 2, -1, p)
    matrices = [_local_matrix(inst, block_id) for block_id in range(inst["blocks_count"])]
    blocks = []
    for block_id, data in enumerate(sorted(inst["blocks"], key=lambda item: item["id"])):
        ones = [y for y, bit in enumerate(matrices[block_id][0]) if bit]
        ds = sorted(data["D"])
        c = (ds[1] - ds[0]) * pow((ones[1] - ones[0]) % p, -1, p) % p
        if c == 0:
            c = 1
        a = (data["row1_sum"] - data["row0_sum"]) * c * width_inverse % p
        if a in (0, c):
            a = 1 if c != 1 else 2
        delta = (data["sum_D"] - c * data["row0_sum"]) * width_inverse % p
        blocks.append({"a": a, "c": c, "delta": delta})
    return {"blocks": blocks}


def _random_restart_attack(inst, seed: int, restarts: int = 256) -> object | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _refresh_summaries(inst: dict) -> None:
    p = inst["p"]
    width = (p + 1) // 2
    inv_width = pow(width, -1, p)
    by_id = {block["id"]: block for block in inst["blocks"]}
    for block_id in range(inst["blocks_count"]):
        matrix = _local_matrix(inst, block_id)
        sums = [sum(y for y, bit in enumerate(matrix[x]) if bit) % p for x in (0, 1)]
        mean = sums[0] * inv_width % p
        third = sum(
            pow((y - mean) % p, 3, p)
            for y, bit in enumerate(matrix[0])
            if bit
        ) % p
        by_id[block_id]["row0_sum"] = sums[0]
        by_id[block_id]["row1_sum"] = sums[1]
        by_id[block_id]["row0_third"] = third


def _reorder_presentation(inst: dict) -> tuple[dict, dict]:
    transformed = copy.deepcopy(inst)
    row_order = list(reversed(range(len(transformed["rows"]))))
    column_order = list(range(len(transformed["columns"])))
    column_order = column_order[3:] + column_order[:3]
    transformed["rows"] = [transformed["rows"][index] for index in row_order]
    transformed["columns"] = [transformed["columns"][index] for index in column_order]
    for row in transformed["rows"]:
        row["bits"] = "".join(row["bits"][index] for index in column_order)
    return transformed, copy.deepcopy(inst["answer"])


def _rename_blocks(inst: dict) -> tuple[dict, dict]:
    transformed = copy.deepcopy(inst)
    count = transformed["blocks_count"]
    mapping = {old: count - 1 - old for old in range(count)}
    for row in transformed["rows"]:
        row["block"] = mapping[row["block"]]
    for column in transformed["columns"]:
        column["block"] = mapping[column["block"]]
    new_blocks = []
    new_answers = [None] * count
    for old_block, old_answer in zip(transformed["blocks"], inst["answer"]["blocks"]):
        new_id = mapping[old_block["id"]]
        block = copy.deepcopy(old_block)
        block["id"] = new_id
        new_blocks.append(block)
        new_answers[new_id] = copy.deepcopy(old_answer)
    transformed["blocks"] = sorted(new_blocks, key=lambda item: item["id"])
    transformed["answer"] = {"blocks": new_answers}
    return transformed, copy.deepcopy(transformed["answer"])


def _affine_relabel(inst: dict) -> tuple[dict, dict]:
    transformed = copy.deepcopy(inst)
    p = transformed["p"]
    answer = copy.deepcopy(inst["answer"])
    for block_id in range(transformed["blocks_count"]):
        ur = (2 + 2 * block_id) % p
        uc = (3 + 2 * block_id) % p
        if ur == 0:
            ur = 1
        if uc == 0:
            uc = 1
        vr = (5 + block_id) % p
        vc = (7 + block_id) % p
        old = answer["blocks"][block_id]
        # The bounded certificate language requires unequal multipliers.  Choose
        # an affine relabelling that preserves that explicitly stated rule.
        while old["a"] * pow(ur, -1, p) % p == old["c"] * pow(uc, -1, p) % p:
            uc = (uc + 1) % p or 1
        for row in transformed["rows"]:
            if row["block"] == block_id:
                row["x"] = (ur * row["x"] + vr) % p
        for column in transformed["columns"]:
            if column["block"] == block_id:
                column["y"] = (uc * column["y"] + vc) % p
        new_a = old["a"] * pow(ur, -1, p) % p
        new_c = old["c"] * pow(uc, -1, p) % p
        new_delta = (old["delta"] - new_c * vc + new_a * vr) % p
        answer["blocks"][block_id] = {"a": new_a, "c": new_c, "delta": new_delta}
    transformed["answer"] = copy.deepcopy(answer)
    _refresh_summaries(transformed)
    return transformed, answer


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run all mandatory correctness, density, adversary, and invariance gates."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            json_native &= json.loads(json.dumps(instance["answer"])) == instance["answer"]
            compact = _recover_by_moments(instance)
            if compact != instance["answer"] or not verify(instance, compact)[0]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "moment recovery failed"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_native,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "json_native": json_native,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=20260905, **shipping_params)
    base = copy.deepcopy(shipping["answer"])
    corruptions = {}

    dropped = copy.deepcopy(base)
    dropped["blocks"] = dropped["blocks"][:-1]
    corruptions["drop_one"] = verify(shipping, dropped)

    swapped = copy.deepcopy(base)
    swapped["blocks"][0]["a"], swapped["blocks"][0]["c"] = (
        swapped["blocks"][0]["c"], swapped["blocks"][0]["a"]
    )
    corruptions["swap_two"] = verify(shipping, swapped)

    duplicated = copy.deepcopy(base)
    duplicated["blocks"][0]["c"] = duplicated["blocks"][0]["a"]
    corruptions["duplicate_one"] = verify(shipping, duplicated)

    corruptions["empty"] = verify(shipping, {})

    out_of_range = copy.deepcopy(base)
    out_of_range["blocks"][0]["delta"] = shipping["p"]
    corruptions["out_of_range"] = verify(shipping, out_of_range)

    corruption_reasons = {name: result[1] for name, result in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(not result[0] for result in corruptions.values())
        and len(set(corruption_reasons.values())) == len(corruption_reasons),
        "cases": {
            name: {"rejected": not result[0], "reason": result[1]}
            for name, result in corruptions.items()
        },
        "distinct_reasons": len(set(corruption_reasons.values())),
    }

    model_response = (
        "I used the finite-field moment invariant.\n\n<answer>```json\n"
        + json.dumps(shipping["answer"], separators=(",", ":"))
        + "\n```</answer>\nThe object above is my final certificate."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed_equals_answer": parsed == shipping["answer"],
        "surrounding_prose_and_fence": True,
    }

    guess_rng = random.Random(0x10021292)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_started
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "candidate_space": search_space(shipping),
        "prior": "uniform over distinct-nonzero affine multiplier triples in every block",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    count_started = time.perf_counter()
    exact_count = enumerate_all(shipping)
    count_seconds = time.perf_counter() - count_started
    reference_answer, reference_metrics = _reference_algorithm(shipping)
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    valid_fraction = (
        exact_count / search_space(shipping) if exact_count is not None else observed
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_count is not None and exact_count >= 1 and reference_ok,
        "shipping_valid_answer_count": exact_count,
        "shipping_candidate_count": search_space(shipping),
        "shipping_valid_fraction": valid_fraction,
        "exact_count_wall_seconds": round(count_seconds, 6),
        "baseline_membership_tests": reference_metrics["membership_tests"],
        "baseline_wall_seconds": round(reference_metrics["wall_clock_sec"], 6),
        "baseline_solved": reference_ok,
        "shipping_preset": SHIPPING_DIFFICULTY,
    }

    attack_names = (
        "outlier_equal_degree_identity",
        "greedy_sorted_boundary_pair",
        "random_restart_256",
        "in_context_linear_moment_c_equals_one",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_attempts = 8
    reference_successes = 0
    reference_operations = 0
    reference_seconds = 0.0
    for seed in range(8):
        instance = make_instance(seed=7000 + seed, **shipping_params)
        candidates = {
            "outlier_equal_degree_identity": _fixed_degree_attack(instance),
            "greedy_sorted_boundary_pair": _boundary_greedy_attack(instance),
            "random_restart_256": _random_restart_attack(instance, 9000 + seed),
            "in_context_linear_moment_c_equals_one": _linear_moment_attack(instance),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(instance, candidate)[0]:
                attack_successes[name] += 1
        solved, metrics = _reference_algorithm(instance)
        reference_operations += metrics["membership_tests"]
        reference_seconds += metrics["wall_clock_sec"]
        if solved is not None and verify(instance, solved)[0]:
            reference_successes += 1
    attacks = {
        name: {"successes": attack_successes[name], "attempts": attack_attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and reference_successes == attack_attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exhaustive affine-certificate enumeration with early exact comparison",
            "complexity": "O(blocks*p^5) worst-case exact; p*(p-1)*(p-2) candidates per block",
            "wall_clock_sec": round(reference_seconds, 6),
            "operations": reference_operations,
            "operation_unit": "predicted-versus-displayed Boolean membership test",
            "solves": f"{reference_successes}/{attack_attempts}, as expected",
        },
    }

    doubled_p = _next_supported_prime(2 * shipping["p"])
    doubled = make_instance(n=doubled_p, blocks=shipping["blocks_count"], seed=314159)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_p >= 2 * shipping["p"] and doubled_ok,
        "shipping_modulus": shipping["p"],
        "doubled_modulus": doubled_p,
        "shipping_matrix_side": len(shipping["rows"]),
        "doubled_matrix_side": len(doubled["rows"]),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_verifications = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        instance = make_instance(seed=12000 + seed, **shipping_params)
        original_key = canonical_key(instance)
        unrelated_keys.append(original_key)
        reordered, reordered_answer = _reorder_presentation(instance)
        renamed, renamed_answer = _rename_blocks(instance)
        relabelled, relabelled_answer = _affine_relabel(instance)
        composed, composed_answer = _reorder_presentation(relabelled)
        transformations = [
            ("row_column_reorder", reordered, reordered_answer),
            ("block_rename", renamed, renamed_answer),
            ("affine_coordinate_relabel", relabelled, relabelled_answer),
            ("affine_then_reorder", composed, composed_answer),
        ]
        for name, changed, carried in transformations:
            invariance_checks += 1
            if canonical_key(changed) != original_key:
                invariant_failures.append({"seed": seed, "transformation": name})
            if verify(changed, carried)[0]:
                carried_verifications += 1
            else:
                invariant_failures.append({"seed": seed, "transformation": name + "_not_real"})
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures
        and carried_verifications == invariance_checks
        and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_passed": invariance_checks - len(invariant_failures),
        "real_transform_verifications": carried_verifications,
        "unrelated_seeds": 20,
        "distinct_unrelated_keys": distinct_keys,
        "failures": invariant_failures,
        "symmetries": [
            "arbitrary displayed row and column reorder",
            "block renaming",
            "independent affine relabelling of public row and column coordinates",
            "compositions of these maps",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _answer_atoms(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_operations = 24 * shipping["blocks_count"]
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_operations <= 300
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(G9_ORACLE_RESULTS["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
