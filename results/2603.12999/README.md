# Verified generator for arXiv:2603.12999

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `optimization` |
| Object regime | `finite_discrete` |
| Computational core | `subset_sum` |
| Certificate form | `integer_tuple` (one 0/1 choice per group) |
| Intended intuition | `decomposition`: cancel group centres and find equal-pair-sum quartets |
| Domain essentiality | `native` |
| Reduction | none |

This module turns Bringmann, Dürr, and Węgrzycki’s [*Tight (S)ETH-based Lower Bounds for Pseudopolynomial Algorithms for Bin Packing and Multi-Machine Scheduling*](https://arxiv.org/abs/2603.12999) into an exact witness problem in the paper’s own objects. The solver receives groups of two near-equal positive integers. It chooses one integer from every group for bin A, with the other going to bin B, so that both exact loads equal the displayed target. Checking a witness is just shape checking and integer addition; `verify` never reads `inst["answer"]`.

## Why this is generatable and Track B

Section 2.3 and Appendix A define Grouped (k)-way Partition: every bin must take exactly (s) items from each size-(ks) group, and all loads must equal the average. This generator uses the native (k=2,s=1) regime. Theorem 2.2 gives a SETH lower bound for the worst case, but it says nothing about this inverse-generated distribution, so Track A would be unjustified.

Generation composes identities rather than solving an instance. Each four-group block receives half-differences with high parts (u,u+a,u+b,u+a+b) and a common low tag. The smallest plus largest equal the two middle values. Random block orientation, centres, item order, and global group order hide the carried witness. Finally, (W=n^{10}\cdot\text{max_deficit}) puts every item in the paper’s exact inclusive interval ([W(1-1/n^{10}),W]).

The paper also identifies the easy mechanism: Section 2.3 explicitly gives a pseudopolynomial (n^{O(1)}W^{k-1}) dynamic program. The measured reference implementation first cancels group centres and then runs exact word-parallel subset-sum DP in (O(qD/\text{word size})) time. At shipping it solved 8/8 seeds, using at most 33,300,648 counted 64-bit word operations; the eight runs took 2.671 seconds total (0.670 seconds maximum). Software can do that routinely, but a no-tool solver cannot. The compact route notices the quartet decomposition and uses 180 exact arithmetic operations; its executable check also solved 8/8.

## Worked demo

The `demo` preset with seed 7 renders completely as follows:

```text
Grouped 2-way Partition (exact integer version)

There are two labelled bins, A and B, and q displayed groups.  Each
group contains exactly two positive integer items.  Choose exactly one
item from every group for bin A; the unchosen item from that group goes
to bin B.  A valid answer makes both bin loads exactly the target shown
below.  Thus every item is used once and item order within a bin is irrelevant.

q = 4 groups (8 items total)
W = 9889162199040
target load of EACH bin = 39556648768756
All item sizes are integers in the inclusive interval
[W*(1-1/8^10), W], as in the paper's definition.

Groups are numbered 0 through q-1.  Within each displayed pair the
left item has index 0 and the right item has index 1:
0: 9889162191114  9889162189830
1: 9889162190078  9889162192762
2: 9889162191477  9889162193961
3: 9889162194687  9889162193603

Give your final answer inside <answer></answer> tags as one JSON list
of exactly q bits in group order.  Bit i is 0 or 1 and chooses that
zero-based item from group i for bin A; no group may be skipped or repeated.
Example of the required shape: <answer>[0,0,0,0]</answer>
Output nothing else inside the tags.
```

The answer is `[0,0,1,1]`, and `verify(inst, inst["answer"])` returns `(True, "ok")`. Swapping the first and third choices gives `[1,0,0,1]` and returns `(False, "bin A load 39556648764988 differs from target 39556648768756")`. A person can solve this demo on paper: the four half-differences, sorted, have equal extreme-pair and middle-pair sums.

## Difficulty presets

| Preset | Total items `n` | Groups / answer bits | `spread` | `tag_mod` | Status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 4 | 40 | 100 | hand illustration; never shipped |
| easy | 144 | 72 | 2,000 | 1,000 | configured shipping preset; local gates pass |
| medium | 184 | 92 | 3,000 | 1,000 | available if easy is oracle-solved |
| hard | 216 | 108 | 4,000 | 1,000 | available if medium is oracle-solved |

`escalate()` first raises the numeric state range (`spread`, then `tag_mod`) without lengthening the witness. Only after those axes are exhausted does it increase `n`, stopping with `cap_bound` before the 256-atom limit.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses verified; 12/12 exact paper-interval checks; JSON round-trip |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses from (2^{72}=4,722,366,482,869,645,213,696) candidates |
| G5 | pass | shipping density sampled as 0/200,000; demo has exactly 2 valid answers out of 16; strongest failing panel checked 2,088 candidates in 0.273 s |
| G6 | pass | six attacks at 0/8; exact DP and compact route both at 8/8 |
| G7 | pass | doubling `n` 144→288 raises candidate entropy 72→144 bits and the planted answer still verifies |
| G8 | pass | 100/100 relabellings invariant and carried witnesses valid; 20/20 unrelated keys distinct |
| G9(c) | pass | 145 characters, 37 estimated tokens, 72 atoms, 180 intended exact operations |

The failing attacks are: always choose the smaller item; split on median half-difference; greedy signed-load balancing; alternating signs after sorting; a suffix-bucket positional guess; and 256 random restarts. Plants and non-plants are not separate item populations: every group is generated by the same quartet law.

## Oracle loop and G9 diagnostic

The required script-owned OpenRouter runs are **infrastructure-blocked, not hardened**. The bare run and both G9 scratch runs returned HTTP 403 `Key limit exceeded (total limit)` on every redraw. `harden.py` correctly refused to score those calls as failures. The error transcripts are preserved, but they are not hardness evidence and this result is not submission-ready until the account limit is restored and all three runs are repeated.

| Bare preset | Model | Seed | Solved? | Why |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 1401972756 | unscored | HTTP 403 key limit |
| easy | GPT-5.6 Terra | 1088349680 | unscored | HTTP 403 key limit |
| easy | GPT-5.6 Terra | 866872795 | unscored | HTTP 403 key limit |
| easy | Gemini 3.1 Pro | 716828737 | unscored | HTTP 403 key limit |

| Arm | Solved / scored attempts | Current conclusion |
|---|---:|---|
| bare | 0 / 0 | pending infrastructure recovery |
| structural hint | 0 / 0 | pending infrastructure recovery |
| placebo hint | 0 / 0 | pending infrastructure recovery |

With zero scored attempts, `hinted − placebo` is not estimable; the `0.0` field in `selftest_report.json` is only its defined pending placeholder. The size and intended-route caps above are independently measured and pass.

## Use

```python
from gen_2603_12999 import DIFFICULTY, make_instance, parse_answer, render, verify
import json

inst = make_instance(seed=42, **DIFFICULTY["easy"])
prompt = render(inst)
candidate = parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

After a successful bare hardening run, emit deterministic samples from the repository root with:

```bash
bash scripts/emit.sh 2603.12999 20
```

## Caveats

- This is a promised Track B subfamily. Theorem 2.2 is worst-case and does not imply distributional hardness here.
- The 0/200,000 density estimate uses exactly the declared prior: independent uniform 0/1 choices with the obvious one-item-per-group constraint already enforced. It is not the success probability of a solver that recognizes the quartet invariant.
- Once the same-suffix quartet decomposition is noticed, the family is intentionally easy. That gap—not NP-hardness—is what Track B measures.
- A low-density LLL/lattice attack was not run because no standard-library implementation was available. The paper’s own exact DP was run and succeeded as expected; CP-SAT, ILP, and external subset-sum libraries were also not tried.
- The canonical key is complete for group reorderings, within-group swaps, independent centre translations, and positive global scaling. It is not a complete invariant for every possible arithmetic equivalence.
- `gvlib` is imported opportunistically through the repository-root path, but this integer-only family needs none of its helpers and remains standard-library-only if it is absent.
- The OpenRouter limit is the only remaining completion blocker. The three error-only transcripts must be overwritten by successful `harden.py` runs, never hand-edited or counted as model failures.
