# Verified VC-shattering generator for arXiv:1705.09517

> **Hardening status:** the module and all local gates pass, but this result is not
> yet shippable. The required OpenRouter run was attempted on 2026-09-05 and every
> request returned HTTP 403 `Key limit exceeded (total limit)`. The error-only
> `llm_loop_transcript.jsonl` is preserved; it is not evidence that an oracle failed
> to solve the problem. The hinted and placebo arms therefore remain unmeasured.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core / certificate | other (VC shattering) / integer tuple |
| Native objects | finite universe; explicit Boolean concept-incidence matrix |
| Intuition | symmetry: two aligned halves share one symmetric-difference mask |
| Domain essentiality / reduction | native / none |

## Problem and provenance

The solver receives the paper's native explicit concept class: each displayed bit
row is a subset of a finite universe. It must return exactly `k` universe elements
that are *shattered*, meaning that the concepts realize all `2^k` binary labelings
on those elements. `verify` projects every concept onto the proposed elements and
compares the resulting exact integer patterns with the full pattern set. It accepts
any valid witness and never reads the planted answer.

This is based on Manurangsi and Rubinstein,
[*Inapproximability of VC Dimension and Littlestone's Dimension*](https://arxiv.org/abs/1705.09517).
Definition 3 in Section 2 fixes shattering. Theorem 1 proves worst-case
quasi-polynomial inapproximability under randomized ETH, and Theorem 13 realizes
that result through a particular randomized Label Cover reduction. Those theorems
do **not** establish average-case hardness for this planted distribution, so the
module deliberately makes no Track A claim. Section 3.1 is especially important:
it exhibits a natural-looking reduction whose soundness fails.

## Why Track B

The paper's general exact route enumerates universe subsets up to
`log2(|C|)` (Section 1), which includes 14,783,142,660 size-nine candidates at the
shipping preset. For this generated distribution, a stronger mechanical algorithm
enumerates pairwise XOR masks and tests which mask stabilizes the unordered concept
set. It succeeds on 8/8 instances, costs `O(|C|^2)` word operations, and measured
524,860 XOR/hash-membership operations and 0.24 seconds on average in the final
eight-seed run (the separate one-shot G5 measurement was 0.16 seconds; repeated
validation runs ranged from 0.22 to 0.43 seconds for the eight-seed average).

The compact route notices that row `i` and row `i + |C|/2` have one common XOR
mask. Its zero coordinates are the shattered set. Comparing and selecting across
60 coordinates is counted as 120 exact operations. The construction-added row
alignment is the intended Track B symmetry; it is not attributed to Theorem 13.
Without seeing that alignment, the rendered hard instance contains 1,024 rows and
the natural projection search is not realistically executable by hand.

## Worked demo (`seed=5`)

```text
Find a shattered subset in an explicit finite concept class.
Universe U = {0,1,...,6}; bit i is counted from 0 at the left.
Return exactly 3 distinct, 0-based universe indices.

0000: 1100101
0001: 0100011
0002: 0001111
0003: 1001000
0004: 0000110
0005: 1001001
0006: 1100010
0007: 0101100
0008: 1010011
0009: 0010101
0010: 0111001
0011: 1111110
0012: 0110000
0013: 1111111
0014: 1010100
0015: 0011010

<answer>[0, 3, 6]</answer>
```

`verify(inst, [0, 3, 6]) == (True, "ok")`. A corrupted answer gives
`verify(inst, [0, 3, 0]) == (False, "duplicate index: all proposed universe elements must be distinct")`.
This demo is genuinely hand-scale; in fact, all 35 three-subsets happen to be valid
for this seed, so it illustrates the definition and wire format rather than hardness.

## Presets

| Preset | `n` | `k` | Decoy rank | Concepts | Candidate space | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 7 | 3 | 2 | 16 | 35 | hand illustration |
| easy | 8 | 4 | 2 | 32 | 70 | deliberately soluble ladder rung |
| medium | 10 | 5 | 3 | 64 | 252 | deliberately soluble ladder rung |
| **hard** | **60** | **9** | **6** | **1,024** | **14,783,142,660** | intended shipping preset; oracle evidence pending |

## Local gate results

| Gate | Result |
|---|---|
| G1 planted verifies | pass, 12/12 preset-seed cases; answers JSON-round-trip |
| G2 corruptions | pass, 5/5 rejected with five distinct reason classes |
| G3 parser round-trip | pass |
| G4 structured guessing | pass, 0/200,000 uniform size-nine subsets in 5.12 seconds |
| G5 density and baseline | pass; shipping density estimate 0/200,000; demo 35/35 exact; reference 524,860 operations / 0.16 seconds |
| G6 attacks | pass; five attacks each 0/8; reference scan and 120-operation compact route each 8/8 |
| G7 scaling | pass; `n=120` still builds and verifies |
| G8 canonical key | pass; 140/140 symmetry-composition checks, 140/140 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) caps | pass; 36 worst-case characters over 100 seeds, 9 estimated tokens, 9 atoms, 120 intended operations |

The random-candidate prior is uniform over all increasing size-nine subsets, exactly
the stated answer language. The density experiment uses exact construction identities
for candidates whose validity is forced or impossible and the same exact projection
checker for all remaining candidates; a separate 5,000-candidate cross-check agreed
with the full checker in every case.

## Oracle and G9 diagnostics

| Run | Preset / seed | Result | Why |
|---|---|---|---|
| bare attempt 1 | easy / 1054715693 | API error | OpenRouter total key limit, HTTP 403 |
| bare retry 1 | easy / 1558859073 | API error | same |
| bare retry 2 | easy / 738826864 | API error | same |
| bare retry 3 | easy / 1056545326 | API error | same |

| G9 arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare | 0 / 0 valid attempts | unavailable; API errors do not count |
| structural hint | 0 / 0 valid attempts | attempted; four quota errors |
| placebo hint | 0 / 0 valid attempts | attempted; four quota errors |

`hinted - placebo` is undefined. No conclusion about the claimed symmetry intuition
may be drawn until the quota is restored and all three isolated runs complete.

## Use

```python
import importlib.util

path = "results/1705.09517/gen_1705_09517.py"
spec = importlib.util.spec_from_file_location("vcgen", path)
vcgen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcgen)

inst = vcgen.make_instance(seed=7, **vcgen.DIFFICULTY["hard"])
question = vcgen.render(inst)
answer = vcgen.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert vcgen.verify(inst, answer) == (True, "ok")
```

After a successful hardening run, emit from the repository root with:

```bash
bash scripts/emit.sh 1705.09517 20 hard
```

## Caveats

- This is a native VC-shattering object, but its planted distribution is not the
  hard distribution of Theorem 13. Its only hardness claim is the measured Track B
  gap between mechanical recovery and the compact symmetry route.
- The aligned row halves are an intentional clue. A solver that tests that exact
  alignment solves the instance quickly; the adjacent-row attack is weaker and its
  failure must not be misread as resistance to the intended insight. Arbitrarily
  reordering the concepts preserves the mathematical problem but removes the
  120-operation alignment shortcut; G8 deliberately gives both presentations the
  same canonical key.
- The 0/200,000 estimate bounds only the declared uniform-subset prior. It says
  nothing about a construction-aware or learned prior.
- No SAT/SMT encoding, MILP formulation, or broad beam-search implementation was
  tested. The reference stabilizer scan and the paper's general subset enumeration
  are reported instead.
- The canonical key is a strong three-column histogram invariant, not a complete
  incidence-matrix isomorphism test; distinct keys certify distinction, while equal
  keys could over-collapse non-isomorphic instances.
- Most importantly, no multi-vendor oracle attempt completed because of account
  quota. Restore OpenRouter quota and rerun the bare, structural, and placebo
  harnesses before treating `hard` as a shipping result.
