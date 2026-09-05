# Rejected cyclic graph-design starter candidate (arXiv:2401.02846)

**Superseded by [REJECTED.md](REJECTED.md).** A construction-aware audit found
that marked-pair affine scanning costs only 823 coordinate transforms per
shipping instance, versus 221 operations for the proposed compact route. The
two routes are comparable, so the candidate fails H on Track B. It also lacks a
distributional-hardness theorem for Track A. The implementation is retained as
`rejected_gen_2401_02846.py` for reproducibility; the older detail below records
the pre-rejection build and is not a shipping claim.

Status: **all local G1–G9 gates pass, but the required external oracle claim is not complete**. The script-owned bare, structural-hint, and placebo runs all stopped because the configured OpenRouter key returned HTTP 403 “Key limit exceeded.” The error transcripts are retained; they are not model failures and this result must not be shipped until the three harness runs are repeated successfully.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style exact labelling |
| Certificate | integer tuple: one ordered 12-residue base block |
| Intuition | symmetry — affine maps preserve developed difference classes |
| Domain essentiality | native; no reduction |

## What the problem is and why it is checkable

[Forbes and Rutherford, *Design spectra for 6-regular graphs with 12 vertices*](https://arxiv.org/abs/2401.02846) define a `G`-design as a partition of the edges of `K_p` into copies of `G`. Section 4 represents large designs compactly: attach an ordered residue tuple to the 12 vertices of graph 201, multiply it by specified powers of `omega`, and translate it through every residue. Lemma 4.7 publishes the reference starters used here.

The solver receives graph 201, the cyclic group, multiplier, reference starter, a residue pool, and a marked subset. It must return an ordered 12-residue starter from the pool containing exactly five markers. `verify` computes every developed undirected difference class with integer modular arithmetic. There are exactly `(p-1)/2` such base-edge/multiplier pairs, so seeing every class once is equivalent to the translated copies partitioning `K_p`. No paper theorem is trusted by the checker.

## Why this is Track B

Theorem 5.1 proves existence, not hardness, and Section 6 explicitly discusses backtracking with random processes and the need for large automorphisms. Consequently this module makes no Track A claim. A successful exhaustive pool-pair affine-template algorithm exists and is reported separately. It has complexity `O(n^2 * 12)` because the images of reference coordinates 0 and 1 determine the affine map. On eight shipping instances the final self-test used 8,967,084 exact transformed-coordinate operations in 16.510 seconds, averaging 1,120,885 operations per instance. The deterministic operation count—not host timing—is the stable Track B measurement.

The short route is structural. The reference starter begins `0,1,2,3,4`; five of the markers are an affine image of that prefix. Their oriented pairwise differences have a distinctive multiplicity pattern. Recovering the two possible orientations and transporting the reference block takes at most 234 modular operations at the shipping preset. The module inverse-generates the affine map first, so the certificate is carried from Lemma 4.7 rather than discovered by solving the generated instance. Order 73 is deliberately easy; the ladder raises the paper order and both pool and marker crowding.

## Worked demo

This is the complete `demo`, seed 0 statement:

```text
Recover a cyclic graph-design base block.

Definitions and exact conventions:
- All residues below belong to the cyclic group Z_73; arithmetic is modulo 73, represented by integers 0 through 72.
- G is the simple graph on vertices 0 through 11 with these 36 unordered edges:
  (0,6) (0,7) (0,8) (0,9) (0,10) (0,11) (1,6) (1,7) (1,8) (1,9) (1,10) (1,11) (2,4) (2,5) (2,8) (2,9) (2,10) (2,11) (3,4) (3,5) (3,8) (3,9) (3,10) (3,11) (4,6) (4,7) (4,10) (4,11) (5,6) (5,7) (5,10) (5,11) (6,8) (6,9) (7,8) (7,9)
- K_73 is the complete graph on residues 0 through 72.
- For an ordered 12-residue list L=(l0,...,l11), one labelled copy of G maps graph vertex i to li.
- Develop L using multiplier omega=1 as follows. For every e=0,...,0 and d=0,...,72, include the labelled copy that maps vertex i to
      (omega^e * li + d) mod 73.
  L is a valid base block precisely when all those copies partition the unordered edges of K_73: every K_73 edge occurs exactly once.
- The following published reference base block for graph 201 is valid under that development:
  [0, 1, 2, 3, 4, 23, 32, 67, 40, 62, 19, 26]

Instance constraints:
- Your answer must be one ordered list of exactly 12 distinct residues.
- Every answer residue must belong to this unordered pool of 12 residues:
  [7, 9, 14, 30, 34, 35, 39, 45, 47, 53, 54, 57]
- Exactly 5 answer residues must belong to this unordered marked set of 5 residues:
  [7, 30, 34, 53, 57]
- Order matters: answer position i labels graph vertex i. No residue may repeat.
- The developed copies of your submitted block must partition K_73 exactly as defined above.

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 12 integers in graph-vertex order.
Example format (not necessarily a solution): <answer>[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]</answer>
Output nothing else inside the tags.
```

The five markers order as `53,30,7,57,34`, an arithmetic progression modulo 73 with step 50. Applying `x -> 50x+53` to the reference gives:

```text
[53, 30, 7, 57, 34, 35, 47, 45, 9, 14, 54, 39]
verify(instance, answer)        -> (True, "ok")
verify(instance, answer[:-1])  -> (False, "wrong length: expected 12, got 11")
```

A person can solve this demo on paper: its pool is exactly the answer set and there are no marker decoys.

## Difficulty presets

| Preset | Pool `n` | Design order `p` | Markers | Answer entries | Status |
|---|---:|---:|---:|---:|---|
| demo | 12 | 73 | 5 | 12 | hand example; harness skips it |
| easy | 40 | 217 | 8 | 12 | bare oracle run blocked before a valid attempt |
| medium | 160 | 577 | 11 | 12 | not reached by the blocked oracle loop |
| hard | 480 | 1009 | 14 | 12 | intended shipping preset; all local gates pass |

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; compact recovery also verified |
| G2 | pass | six corruptions rejected; the five required cases had five distinct reasons |
| G3 | pass | tagged prose and an untagged JSON fence both round-tripped |
| G4 | pass | 0/200,000 structure-aware guesses; candidate space 867,778,876,996,098,399,940,608,000 |
| G5 | pass | shipping sampled density 0; reference cost 8,967,084 operations / 16.510 s across eight |
| G6 | pass | magnitude, greedy, 256-restart, and small-step attacks all 0/8; reference 8/8 |
| G7 | pass | doubled pool 960 verifies while the answer remains 12 entries |
| G8 | pass | 80/80 affine/reorder/vertex-relabelling invariance checks; 20/20 unrelated keys distinct |
| G9(c) | pass | worst-case bound 69 characters, about 18 tokens, 12 atoms, 234 intended modular operations; sampled answer 59 characters |

An additional deterministic stress audit (outside `selftest()`) matched all four embedded starters against the paper source and built 700 instances across the four named presets and every escalation through a full 1,009-residue pool; every planted witness and every compactly recovered witness verified.

## Oracle loop and G9 arms

No row below is a valid oracle attempt. Harness errors are redrawn and do not count as failures.

| Arm | Preset | Seeds | Valid solved/attempts | Error calls | Reason |
|---|---|---|---:|---:|---|
| bare | easy | 1687774709, 410156308, 356857249, 1547995924 | 0/0 | 4 | OpenRouter HTTP 403 key limit |
| structural | hard | 394678098, 1363536476, 1374248804, 9695506 | 0/0 | 4 | OpenRouter HTTP 403 key limit |
| placebo | hard | 495856012, 86161582, 980476790, 1782908036 | 0/0 | 4 | OpenRouter HTTP 403 key limit |

Thus `hinted - placebo` is unavailable, not zero evidence. The current `selftest_report.json` records it as `null`, with 0/0 for every arm and `hinted_verdict="not_run"`; repeat all three script-owned runs after restoring OpenRouter quota.

## Use

```python
import gen_2401_02846 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
instance = g.make_instance(seed=123, **params)
statement = g.render(instance)
answer = g.parse_answer("<answer>" + __import__("json").dumps(instance["answer"]) + "</answer>")
assert g.verify(instance, answer) == (True, "ok")
```

From the repository root, after valid oracle evidence exists:

```bash
bash scripts/emit.sh 2401.02846 20 hard
```

## Caveats

The 0/200,000 estimate is with respect to the honest constrained prior—ordered distinct pool tuples containing exactly five markers—not a prior over arbitrary integers. It is an observed rate, not a proof of the true density or uniqueness. The construction becomes easy once affine transport is recognized; that is the declared Track B target, and the pool-pair affine scan succeeds by design. The panel does not include a general SAT/SMT package or an unconstrained randomized backtracker; it measures the exact successful affine reference algorithm and four no-tool attacks. Marker decoys are rejection-conditioned by an affine-invariant difference statistic, so the benchmark intentionally presents a clean structural signal rather than natural-instance statistics. Most importantly, multi-vendor model hardness has **not** been established because the available OpenRouter key was exhausted.
