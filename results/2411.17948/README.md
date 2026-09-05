# Parity Test Cover generator for arXiv:2411.17948

Status: the module and every local gate pass. The required four-vendor oracle audit is **blocked**, not passed: OpenRouter returned HTTP 403 `Key limit exceeded (total limit)` before any bare, hinted, or placebo attempt counted. The harness-owned error transcripts are retained. Re-run Step 4 with a funded key before treating this family as hardened or emitting it for release.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate form | integer tuple (test IDs) |
| Intuition | symmetry: a full cyclic orbit of parity masks |
| Domain essentiality | native |
| Reduction | none |

## What the family is

[Structural Parameterization of Locating-Dominating Set and Test Cover](https://arxiv.org/abs/2411.17948) defines a Test Cover as selected tests giving every pair of items different incidence signatures (Sections 1–2). An instance here uses the paper's native object—a finite set system. Its items are all vectors of `F_2^d`; a displayed mask `a` names the exact test `{x : a·x=1}`. A submitted list of `d` test IDs is valid exactly when those masks have rank `d`, because equal signatures would otherwise differ by a nonzero kernel vector. Verification is exact Gaussian reduction over `F_2` and never consults the planted answer.

The generator first samples a fixed-weight mask whose `d` cyclic rotations form a basis. Only after holding that witness does it add same-weight decoys from a proper subspace, randomly relabel coordinates, and shuffle tests while carrying the witness. This is inverse generation; it does not solve the finished instance.

## Why this is Track B

Track A would be false. Theorem 1 gives general Test Cover a `2^{O(|U| log |U|)}(|U|+|F|)^{O(1)}` algorithm, and this promised parity subclass has a much stronger polynomial method: incremental Gaussian elimination in `O(n d^2)` exact bit operations. At the provisional shipping preset `n=120,d=19`, that reference solver succeeds 8/8, averaging 15,097 counted operations per instance (120,779 total; 0.0062 s total in the recorded run).

The compact no-tool route indexes the 120 masks, detects the only complete orbit under the displayed coordinate cycle, and follows its 19 rotations. It used 141 exact mask operations on the measured shipping sample; the seed-independent conservative bound is 267, versus roughly 15,000 for elimination. The intended difficulty is recognizing the symmetry, not denying that an efficient algorithm exists.

Theorem 3's subquadratic incompressibility is a worst-case result and is not used as evidence about this generated distribution. The paper's FPT and kernel regimes for Locating-Dominating Set in Sections 3–4 are likewise not claimed here.

## Worked demo (`seed=5`)

The complete rendered demo is:

```text
Parity Test Cover on a finite binary item set

The item set U consists of all 128 binary vectors
x=(x_0,...,x_6) in {0,1}^7. Coordinate subscripts and test IDs are
0-based. The marked, oriented coordinate cycle (including its marked starting
position) is:

    (2, 3, 4, 6, 0, 5, 1)

There are 9 tests. A displayed support A defines the set

    T_A = {x in U : sum_(j in A) x_j is 1 modulo 2}.

Thus every listed test is an actual subset of the finite item set U, described
exactly rather than by enumerating its 64 members. The tests are:

T0: {0,4,5}
T1: {1,2,3}
T2: {0,4,6}
T3: {1,2,5}
T4: {0,1,5}
T5: {3,4,6}
T6: {0,5,6}
T7: {2,3,4}
T8: {2,4,5}

A collection C of tests is a test cover if every two distinct items u,v in U
are separated: at least one selected test contains exactly one of u and v.
Equivalently, write each selected support as a length-7 binary row; C is a
test cover exactly when those rows have rank 7 over F_2. This follows because
u and v have the same selected-test signature exactly when their nonzero XOR
u XOR v lies in the row matrix's kernel.

Find a test cover containing at most 7 tests. Since 7 binary answers cannot
give distinct signatures to 128 items with fewer than 7
tests, your answer must contain exactly 7 distinct test IDs. Order does not
matter and repeated IDs are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 7 distinct integers from 0 through 8.
Example: <answer>[0, 1, 2, 3, 4, 5, 6]</answer>
Output nothing else inside the tags.
```

The answer is `[1,2,3,4,5,6,7]`. A person can solve this demo by row-reducing at most nine seven-bit rows, or by spotting the orbit in the displayed cycle.

```python
verify(inst, [1,2,3,4,5,6,7])
# (True, "ok")
verify(inst, [1,2,3,4,5,6])
# (False, "wrong number of test IDs: expected 7, got 6")
```

## Difficulty presets

| Preset | Tests `n` | Dimension / answer IDs | Decoy-span dimension | Candidate space | Compact ops | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 9 | 7 | 4 | 36 | 33 | hand example; hardener skips it |
| easy | 120 | 19 | 12 | 5.834×10^21 | 267 | provisional shipping preset |
| medium | 128 | 19 | 12 | 2.196×10^22 | 283 | not reached: API blocked |
| hard | 136 | 19 | 12 | 7.577×10^22 | 299 | not reached: API blocked |

`escalate` first grows to `n=136`, then tightens the decoy subspace while keeping the 19-ID witness fixed. It returns `cap_bound` rather than exceeding the 300-operation route cap. A doubled `n=240` instance is still built and verified for G7, but is not a shippable G9 rung.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced, tagged JSON round-trip |
| G4 | pass | 0 / 200,000 structure-aware uniform 19-subsets valid |
| G5 | pass | demo has 12 / 36 exact covers; reference 120,779 ops over 8 instances |
| G6 | pass | four attacks at 0/8; Gaussian reference at 8/8 |
| G7 | pass | strictly growing preset spaces; doubled and fixed-answer probes verify |
| G8 | pass | 60 invariance + 60 carried-witness checks; 20/20 keys distinct |
| G9(c) | pass | 76 chars, 19 estimated tokens/atoms, 141 measured / 267 bounded route operations |

## Oracle loop and G9 diagnostics

No row is a scored attempt. Every call failed at account authorization and the harness stopped, correctly refusing to manufacture a hardness claim.

| Arm | Preset | Seeds | Solved / attempts | Result |
|---|---|---|---|---|
| bare | easy | 607076474, 1456803329, 1233334658, 82388422 | 0 / 0 | four HTTP 403 errors |
| structural | easy | 906988822, 1503961196, 1783444038, 965066557 | 0 / 0 | four HTTP 403 errors |
| placebo | easy | 1097845610, 1637206498, 53729141, 1120394690 | 0 / 0 | four HTTP 403 errors |

Hinted-minus-placebo is not estimable. These transcripts establish only the external block; they do not show whether the cyclic-orbit hint helps.

## Use

```python
import gen_2411_17948 as g

inst = g.make_instance(seed=5, **g.DIFFICULTY["demo"])
question = g.render(inst)
answer = g.parse_answer("<answer>[1,2,3,4,5,6,7]</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

After a successful hardening rerun, emit from the repository root with:

```bash
bash scripts/emit.sh 2411.17948 20 easy
```

## Caveats

The family becomes easy with Gaussian elimination or once the complete cyclic orbit is recognized; that is the declared Track B distinction. The 0/200,000 density estimate applies only to the uniform prior over all `d`-subsets of listed tests and says nothing about rank-aware sampling. I did not run the paper's vastly larger general dynamic program, a SAT encoding, or exhaustive orbit search as an attack; Gaussian elimination already solves every generated instance, while the measured single-anchor orbit heuristic deliberately fails because test 0 is a decoy. The set system is native Test Cover, but its parity presentation is a promised algebraic subclass devised for this generator, not a construction studied in the paper. `canonical_key` covers test reorderings and coordinate relabelings carrying the marked cycle; it is not a complete canonical form for arbitrary expanded set-system isomorphism. Most importantly, practical no-tool hardness remains unverified until the OpenRouter limit is fixed and all three arms produce scored attempts.
