# Semi-positive debt-swap reachability generator

This module turns the family in [Dynamic Debt Swapping in Financial Networks](https://arxiv.org/abs/2302.11250) by Froese, Hoefer, and Wilhelmi into witness problems.  The solver receives an acyclic edge-ranking financial network and a target with the same debt-contract stubs, and must return a finite sequence of semi-positive swaps reaching that target.  A swap exchanges the creditors of two equal-liability contracts on four distinct endpoint banks.  Checking is cheap and exact: `verify` recomputes integer clearing assets immediately before and after every swap, checks semi-positivity, and compares the final creditor map with the target.

## Why this family is hard—and what is easy

Section 6, Proposition 6.4 proves that reachability by **semi-positive** swaps under edge-ranking rules is strongly NP-hard.  Its proof uses the acyclic 3-Partition gadget of Section 5, Theorem 5.8.  In the gadget, item payments can be moved to bank `V` only three at a time with sum exactly `T`; unit “pulse” swaps open successive priority gates.  A reaching sequence therefore contains an exact 3-partition witness.

The restriction matters.  Section 6, Theorem 6.1 gives a polynomial greedy algorithm for reachability by arbitrary swaps, so this generator checks semi-positivity at every step.  Section 4 also gives polynomial local-optimization dynamics for swaps improving one fixed bank (Theorem 4.6) and additional special local cases (Theorem 4.13), but those algorithms do not solve exact target reachability.  The paper states no FPT or approximation scheme for Proposition 6.4's reachability problem.  The generator asks for a sequence, never an optimum or a claim of nonexistence.

Generation is inverse: it samples the complete item/filler/pulse swap schedule first, then samples each planted triple from the same symmetric bounded zero-sum distribution and shuffles every visible item identity.  Production instances retain 4–11 candidate triples per bin overall and minimum item degree two, avoiding isolated planted triples, and reject samples solved by the three cheap attacks in G6.

## Worked `demo` example (`n=4`, seed 0)

This is the complete string returned by `render`:

```text
Semi-positive debt-swap reachability

A financial network is a directed multigraph of banks and named debt contracts.
A contract e=(debtor -> creditor, liability L) pays an integer amount between 0
and L.  A bank's total assets are its nonnegative integer external assets plus
all incoming payments.  It pays those assets along its outgoing contracts in
increasing rank order, filling each liability before paying the next.  Unspent
assets are allowed only after all outgoing liabilities are full.  This instance
is acyclic, so its clearing state is obtained exactly by processing debtors
before creditors.  Banks and contracts not assigned external assets have 0.

A debt swap chooses two CURRENT contracts with the same liability.  If their
current endpoints are u1->v1 and u2->v2, then u1,u2,v1,v2 must be four pairwise
distinct banks.  The swap changes them to u1->v2 and u2->v1.  Contract names,
debtors, liabilities, and ranks never change.  A swap is semi-positive when,
comparing exact clearing states immediately before and after it, both old
creditors v1 and v2 have weakly larger total assets and exactly one has strictly
larger total assets.

All indices below are 0-based.  Let q=4, so there are 12 item banks and
2q-1 gate banks.  The complete bank set is:
  V, R;
  I0..I11, C0..C11;
  U0..U6;
  S0..S2, D0..D2.

External assets of item bank Ii are listed as index:value:
  0:332, 1:369, 2:362, 3:354, 4:345, 5:355, 6:351, 7:352, 8:377, 9:372, 10:339, 11:328
Every listed item value is strictly between T/4 and T/2; consequently exactly
three item payments, neither fewer nor more, can total T.
Each Sj has external assets 1.  Every other bank has external assets 0.

The complete initial contract set is defined by these inclusive index ranges:
  i<idx>: I<idx> -> R, liability c=2119, rank 0, for idx=0..11.
  c<idx>: C<idx> -> V, liability c=2119, rank 0, for idx=0..11.
  g<h>: V -> U<h>, rank h, for h=0..6; its liability is T=1059
      when h is even and 1 when h is odd.
  r<j>: U(2j) -> R, liability M=2121, rank 0, for j=0..3.
  p<j>: S<j> -> U(2j+1), liability d=2120, rank 0, for j=0..2.
  d<j>: D<j> -> V, liability d=2120, rank 0, for j=0..2.
Here, for example, i7 is the literal contract name "i7", and U(2j+1)
means the bank whose name is obtained by evaluating 2j+1 (for j=2, bank U5).

The target network keeps every debtor, liability, and rank unchanged.  Its
creditors are:
  i<i> -> V and c<i> -> R for every i=0..11;
  p<j> -> V for every j=0..2;
  the d-contract targets are: d0->U3, d1->U1, d2->U5;
  every g<h> and r<j> keeps its initial creditor.

Find a sequence of exactly 15 semi-positive debt swaps
that transforms the initial network into that target.  A contract may occur in
at most one submitted swap.  Sequence order matters.  Each swap is represented
as a JSON array of its two contract-name strings.  Inside each swap, put the
lexicographically smaller contract name first; repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 15 two-string arrays.
Format example only: <answer>[["c0","i0"],["d0","p0"]]</answer>
Output nothing else inside the tags.
```

One answer is:

```json
[["c5","i11"],["c0","i3"],["c3","i8"],["d1","p0"],["c7","i5"],["c6","i9"],["c11","i0"],["d0","p1"],["c9","i2"],["c1","i4"],["c10","i7"],["d2","p2"],["c4","i1"],["c2","i6"],["c8","i10"]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`.  Replacing the first pair by `["c5","c5"]` returns `(False, "swap 1 repeats an edge")`.

## Difficulty presets

| preset | bins `n` | item banks | swaps | attack filter | status |
|---|---:|---:|---:|---|---|
| `demo` | 4 | 12 | 15 | off | all three demo oracles solved; retained only for examples/enumeration |
| `easy` | 24 | 72 | 95 | on | **shipping; held against all three non-error oracle calls** |
| `medium` | 32 | 96 | 127 | on | available, not reached after `easy` held |
| `hard` | 40 | 120 | 159 | on | available, not reached after `easy` held |

`escalate` grows the number of bins by at least eight (about 30%) while keeping the candidate-triple degree regime roughly constant; it stops at 96 bins.

## Gate results

| gate | measured result |
|---|---|
| G1 | 32/32 checks passed: optimized verification and literal clearing replay for 4 seeds × 4 presets |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | tagged JSON survived prose + Markdown; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses at shipping `easy` (`p̂=0`) |
| G5 | demo: 14,898,865,766,400 valid answers / 229,442,532,802,560,000 candidates = 6.4935×10⁻⁵ |
| G6 | rank/extremes 0/8; deterministic greedy 0/8; 24-restart randomized greedy 0/8 |
| G7 | doubled from 24 to 48 bins and 95 to 191 swaps; planted witness replayed successfully |
| G8 | 80/80 key-invariance transformations, 60/60 carried witnesses, 20/20 unrelated keys distinct |

## Oracle hardening loop

The script-selected master seed was `5521555593670297980`; effort was `medium`.  Error rows did not count as failures.

| preset | model | instance seed | result | verifier/reason |
|---|---|---:|---|---|
| demo | OpenAI GPT-5.6 Terra | 1855368412 | solved | parsed, `ok` |
| demo | Anthropic Claude Sonnet 5 | 613228152 | solved | parsed, `ok` |
| demo | xAI Grok 4.6 | 1751906715 | solved | parsed, `ok` |
| easy | Google Gemini 3.1 Pro Preview | 65066574 | failed | parsed; swap 83 block did not sum to `T` |
| easy | Anthropic Claude Sonnet 5 | 1880218965 | failed | empty length-limited response after 32,000 completion tokens |
| easy | xAI Grok 4.6 | 392003345 | error | 900-second deadline; excluded |
| easy | xAI Grok 4.6 | 1602448046 | error | 900-second deadline; excluded |
| easy | OpenAI GPT-5.6 Terra | 653424315 | failed | parsed; swap 55 block did not sum to `T` |

Harness verdict: `hardened`, shipping params `{"n":24,"spread":0.3,"attack_filter":true}`.

## Use

From this directory:

```python
import random
import gen_2302_11250 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
answer = gen.parse_answer(model_output)
ok, reason = gen.verify(inst, answer)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
candidate = gen.random_candidate(inst, random.Random(7))
```

From the repository root, emit 20 fresh deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2302.11250 20
```

## Caveats

- Strong NP-hardness is worst-case evidence, not a proof that every planted sample is hard.  The oracle and attack results are empirical.
- G4 samples the informed normal form: exactly three item swaps per gate, target-forced pulse pairs, a uniform item order, and a uniform item-to-`c`-filler bijection.  It does not model a solver's nonuniform arithmetic heuristics.  Zero hits in 200,000 trials means only that the measured rate was below the test's resolution; it does not mean probability zero.
- The filter tested rank/extremes, deterministic minimum-degree greedy, and 24 randomized greedy restarts.  It did **not** test industrial ILP/SAT/exact-cover solvers, meet-in-the-middle methods, large-neighborhood search, or learned heuristics.  Such solvers may handle these sizes.
- One of the three counted failures was an empty length-limited Claude response; the other two vendors returned parsed but invalid sequences.  The two Grok timeouts were excluded rather than treated as failures.
- `enumerate_all` intentionally returns `None` above six bins.  `canonical_key` is complete for this fixed generated gadget: it hashes the sorted item-asset multiset and ignores arbitrary bank/contract labels.  It is not a general financial-network isomorphism solver.
