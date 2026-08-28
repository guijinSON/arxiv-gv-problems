# Doubly-weighted zero-sum witness generator

This directory turns Krishnendu Paul and Shameek Paul's [*Doubly-weighted zero-sum constants* (arXiv:2311.00090v4)](https://arxiv.org/abs/2311.00090) into an inverse-generated witness problem.  An instance gives (2t-1) residues modulo (M=tq).  The solver must return exactly (t) distinct, increasing, 1-based indices whose values sum to zero modulo (M).  This is the paper's Section 1 definition with singleton weights (A=\{1\}) and (B=\{q\}): the second weighted sum is automatically (tq=0\pmod M).  Checking a witness is just bounds, uniqueness, and two exact integer modular sums.

## Why this construction, and why trust it?

Generation samples the size-(t) answer first, fills every sequence position uniformly modulo (M), and replaces a uniformly chosen planted position by the needed residue.  Because a sum containing a uniform residue is uniform, that replacement has the same uniform one-element distribution as every decoy.  The verifier never reads `inst["answer"]` and accepts any valid subset.

The paper is not a computational-complexity paper, so it would be misleading to call one of its existence theorems an NP-hardness theorem.  Worst-case hardness here comes from a direct reduction from exact-cardinality subset sum.  Encode each item/dummy pair in its own carry-free radix digit, set the target to require one member of every pair, append one residue equal to minus that target, and choose a sufficiently large modulus rounded up to a multiple of (t).  The result has exactly (2t-1) residues, and a size-(t) modular zero-sum exists exactly when the source instance is satisfiable.  Our modulus has about (2t) bits, so the pseudo-polynomial dynamic program is exponential in the encoded input size; (t) grows with `n`.

The paper audit matters mostly for avoiding easy regimes.  Observation 1.2 and Remark 1.4 expose constant-weight length shortcuts.  Theorems 2.2-2.4 characterize the ((\{1\},\{1\})) constants.  Theorems 3.3-3.4 make the ((\mathbb Z_M',\{1\})) `D`/`C` tasks collapse at lengths 3 and 4, and Theorems 7.2-7.3 retain constant-size bounds for broad second weight sets.  This generator instead keeps (A) singleton, gives (q) additive order exactly (t), uses (2t-1) entries, and keeps (M) exponential in (t).  Section 1 fixes the definition; these results identify the shortcuts to avoid.

## Worked demo (`seed=0`)

The smallest preset renders in full as follows:

```text
Doubly-weighted zero-sum subsequence

All arithmetic in this problem is modulo M = 21250572.  The sequence below has
23 entries x_1,...,x_23.  Indices are 1-based.

The two allowed weight sets are singletons: A = {1} and B = {1770881}.  Thus a
chosen subsequence with indices I has fixed weights a_i=1 and b_i=1770881 and is
doubly-weighted zero-sum exactly when both congruences hold:

    sum(x_i for i in I) = 0 (mod M)
    sum(b_i*a_i for i in I) = 0 (mod M).

Find exactly 12 DISTINCT indices.  The second congruence then holds because
12*1770881 = M.  Your remaining task is to make the selected sequence values
sum to 0 modulo M.  Return the indices in STRICTLY INCREASING order; order does
not otherwise matter, and repeated indices are forbidden.  Every index endpoint
is inclusive, so each index must be an integer from 1 through 23.

Sequence data is laid out as "first_index: values", with consecutive indices
across and then down:
1: 4673250 9456908 4689090 3181992 20749020 8405597 17869870 20196482
9: 4931206 10406825 3313947 2474385 11079580 15842480 18784230 1556914
17: 11871267 14568389 10609800 20497965 6861134 18539618 16005792

Give your final answer inside <answer></answer> tags, as exactly 12
comma-separated decimal indices in strictly increasing order.
Example of the required FORMAT only (not a claim that it is valid here):
<answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12</answer>
Output nothing else inside the tags.
```

The planted answer is `[2, 4, 6, 8, 9, 10, 13, 14, 16, 17, 18, 23]`; `verify(inst, inst["answer"])` returns `(True, "ok")`.  Dropping its last index returns `(False, "wrong number of indices: expected 12")`.

## Difficulty presets

| preset | `t=n` | entries | target modulus bits | shape-valid search space | status |
|---|---:|---:|---:|---:|---|
| `demo` | 12 | 23 | 24 | 1,352,078 | Not shipped: exact brute force is feasible (fails H) |
| `medium` | 40 | 79 | 80 | 53,753,604,366,668,088,230,810 | **Shipping** |
| `hard` | 64 | 127 | 128 | 11,975,573,020,964,041,433,067,793,888,190,275,875 | Available larger margin |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 planted verifies | Pass | 12/12: 3 presets x 4 seeds |
| G2 rejects corruption | Pass | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | Pass | Parsed a fenced, prose-surrounded answer; garbage returned `None` |
| G4 structure-aware guess | Pass | 0/200,000 hits at `medium`; sampler is uniform over sorted size-40 subsets |
| G5 sparse | Pass | Demo seed 303: 1/1,352,078 valid, fraction 7.39602301050679e-7 |
| G6 adversary panel | Pass | magnitude outlier 0/8; circular greedy 0/8; 256-restart two-sum completion 0/8 |
| G7 scales | Pass | doubled to `n=80`, 159 entries, 161-bit realized modulus; planted witness verified |

Full per-seed diagnostics and failure residues are in [`selftest_report.json`](selftest_report.json).

## Oracle hardening loop

Both keys were present, so the preferred OpenAI API path was selected.  The installed OpenAI SDK was version 2.48.0, and its `responses.create` signature and `reasoning={"effort":"medium"}` field were checked before use.  The managed sandbox blocked DNS/network access and raised `APIConnectionError` before the first request left the process.  As an explicit fallback, isolated `gpt-5.6-terra` runtimes at medium reasoning received only the rendered text and no solver tools.  This fallback is weaker evidence than the requested authenticated API run; the failed API attempt and all raw fallback replies are preserved in [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl).

| preset | seed | solved? | verifier result |
|---|---:|---|---|
| demo | 1301 | No | residue 12,521,572 |
| demo | 1302 | No | residue 10,689,539 |
| demo | 1303 | No | residue 302,828 |
| medium | 2301 | No | residue 970,341,396,679,257,709,706,548 |
| medium | 2302 | No | residue 674,798,517,595,177,456,362,816 |
| medium | 2303 | No | residue 309,443,415,866,133,646,273,747 |
| hard | 3301 | No | residue 162,497,905,910,669,544,707,911,118,252,299,301,957 |
| hard | 3302 | No | residue 121,520,429,258,210,065,720,537,623,958,128,756,504 |
| hard | 3303 | No | residue 134,572,460,100,508,819,594,541,040,593,756,830,913 |

## Use

```python
from gen_2311_00090 import DIFFICULTY, SHIPPING_DIFFICULTY
from gen_2311_00090 import make_instance, render, parse_answer, verify

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)                 # send only this string to the solver
answer = parse_answer(model_output)
ok, reason = verify(inst, answer)
```

From the repository root, emit verified dataset records with:

```sh
bash scripts/emit.sh 2311.00090 20 medium
```

## Caveats

Worst-case NP-hardness does **not** prove this planted random distribution is average-case hard.  Revealing the seed or generator-private `answer` makes an instance trivial; the contract assumes the solver sees only `render(inst)`.  Meet-in-the-middle, representation, lattice, SAT/ILP, and generalized-birthday attacks remain relevant.  The implemented panel does not include LLL/BKZ, GPU search, a full meet-in-the-middle run, or learned multi-instance correlation attacks.

The G4 estimate is relative only to a uniform prior over all size-(t), distinct, increasing subsets.  Zero hits in 200,000 trials has point estimate 0 and passes the requested empirical threshold, but it cannot statistically resolve a true probability of (10^{-6}): the rough 95% zero-hit upper bound is about (1.5\times10^{-5}).  Exact demo enumeration and the modulus/search-space scale offer additional sparsity evidence, not a proof for `medium`.  Finally, plants and decoys have identical one-element marginals, but planting necessarily creates a higher-order correlation; attacks beyond the three tested may exploit it.  The API transport failure also means the required authenticated oracle experiment should be rerun in a network-enabled environment before treating the model evidence as final.
