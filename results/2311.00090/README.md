# Balanced doubly-weighted zero sums

This generator turns the definition in Section 1 of Krishnendu Paul and Shameek Paul, [*Doubly-weighted zero-sum constants* (arXiv:2311.00090v4)](https://arxiv.org/abs/2311.00090), into a witness problem. The solver receives (n) residues modulo (q=2^n), uses every residue, and assigns exactly (n/2) weights (+1) and (n/2) weights (-1). With (A=\{+1,-1\}) and (B=\{1\}), the balance rule makes the paper's second congruence zero; the solver must make the signed residue sum zero too. A witness is two lists of 1-based indices. Verification is two exact modular sums plus shape checks.

## Why this regime is hard

The paper establishes structural zero-sum constants, not computational hardness, so the H claim is not borrowed from a theorem the authors did not prove. It follows by a direct reduction from PARTITION. Given positive integers (y_1,\ldots,y_t), make the (2t) numbers (C+y_1,C,\ldots,C+y_t,C) and require exactly (t) plus signs. The plus-side sum is (tC) plus the sum of a subset of the (y_i), so equal signed sums exist exactly when that subset has half the total. Pad with (y_i=0) pairs until (q=2^n) exceeds twice the integer total; then equality modulo (q) is integer equality and the reduction stays polynomial in the input bit length. The decision problem is therefore NP-complete, while a supplied witness is cheap to check.

The selected regime deliberately avoids the paper's easy cases. Observation 1.2 and Remark 1.4 give ordinary-zero-sum and (2q-1)-length shortcuts. Observations 3.1-3.2 and Theorems 3.3-3.4 construct witnesses of at most three arbitrary or four consecutive terms when (A=\mathbb Z_q'\). Observation 5.1 and Theorems 5.4-5.7 show that (B=\mathbb Z_q'\) largely collapses the double condition to a single-weight condition; Theorems 7.2-7.3 again make (A=\mathbb Z_q'\) constant-size. Here (A) has only two elements, (B=\{1\}), (n\ll q), and the required length is (n), not (q). The generator samples the balanced sign witness first, chooses its solved coordinate uniformly, and draws every other residue uniformly. The solved residue is itself uniform modulo (q), so it has no different one-item distribution.

## Difficulty presets

| preset | (n=\log_2 q) | balanced candidate space | status |
|---|---:|---:|---|
| `easy` | 64 | 1,832,624,140,942,590,534 | **ships; three deciding vendors failed** |
| `medium` | 80 | 107,507,208,733,336,176,461,620 | available; not reached |
| `hard` | 96 | 6,435,067,013,866,298,908,421,603,100 | available; not reached |

`SHIPPING_DIFFICULTY = "easy"`. No named preset was rejected; the first rung held, so the mandated loop did not retune upward.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 plant | pass | 12/12 across 3 presets and 4 seeds |
| G2 corruption | pass | 5/5 rejected through 5 distinct reasons |
| G3 round-trip | pass | prose + Markdown fence + tags + JSON recovered exactly; garbage returned `None` |
| G4 guessing | pass | 0/200,000 shape-aware balanced partitions; required threshold (<10^{-6}) |
| G5 sparse | pass | exactly 2/184,756 valid at enumerable probe (n=20), fraction (1.0825\times10^{-5}) |
| G6 adversaries | pass | magnitude split 0/8; largest-first greedy 0/8; random-restart one-swap search 0/8 |
| G7 scaling | pass | (n=128) built and verified; space grew to 23,951,146,041,928,082,866,135,587,776,380,551,750 |

## Oracle hardening loop

All calls used reasoning effort `medium`. The Claude row was an empty length-truncated response and was correctly redrawn, not treated as evidence of failure. Every non-error reply contained a parseable witness; each failed the first exact congruence, so there is no parser false negative.

| preset | model | seed | solved? | why |
|---|---|---:|---|---|
| `easy` | Claude Sonnet 5 | 1464762499 | excluded error | empty reply at the 32,000-token length limit |
| `easy` | Grok 4.6 | 1257860566 | no | parsed; residue 9,108,393,012,456,622,088, not 0 |
| `easy` | Gemini 3.1 Pro Preview | 814041027 | no | parsed; residue 10,497,809,268,379,131,668, not 0 |
| `easy` | GPT-5.6 Terra | 2089872177 | no | parsed; residue 13,295,517,895,175,320,988, not 0 |

## Worked example

The full smallest-preset render below is seed 0. It is collapsed only to keep this page scannable.

<details>
<summary>Full rendered <code>easy</code> instance</summary>

```text
Balanced doubly-weighted zero-sum witness

All arithmetic below is in the ring Z/18446744073709551616Z: reduce an integer modulo 18446744073709551616,
with residue representatives 0 through 18446744073709551615.  The input is an ordered
sequence of 64 residues, labelled by 1-based positions:

1: 16842081330453989823
2: 10192262804094026689
3: 4089715063379223119
4: 17847967439290631532
5: 10016396730278161277
6: 17207746803097342350
7: 13033757608824335107
8: 9966473405330394875
9: 10839621657788106151
10: 7100172914762545185
11: 4466088725509430642
12: 12113227759547217336
13: 1274398012306485116
14: 13975325745849883258
15: 15540648152043645414
16: 10693485545316635201
17: 1519513457529745562
18: 2127827264650304134
19: 11624166703806187276
20: 3511869889689616642
21: 13493594488733845086
22: 13011099469452444498
23: 14657468805718955576
24: 1365001903070189292
25: 11713680868309175090
26: 7216539931133631702
27: 8840300575657007098
28: 14771167530850900049
29: 12531743928323225080
30: 15419682365516802845
31: 4073581149739011401
32: 5553605192833625240
33: 3326278196384641513
34: 8617050225941303918
35: 7217771881808329345
36: 15595331165068745821
37: 9767075500263590769
38: 12278260277853257221
39: 11970709935651220672
40: 229409573639406250
41: 1458653927214403995
42: 2487314810424259987
43: 17582133036783065751
44: 11255016303815783515
45: 11456845623891916084
46: 4367298013510985367
47: 1489078616156076933
48: 2952950700752722293
49: 11757943629159395398
50: 581911411179293101
51: 862932939393035124
52: 1178494407519934947
53: 2908803867365249111
54: 16324363373654247500
55: 9123439963499005071
56: 15453517143821454490
57: 7701240380300404939
58: 3938834878482504181
59: 13922750591783833098
60: 11290550385783189137
61: 3361386927839246527
62: 11577897887892103550
63: 15889285693061707746
64: 780253123762538882

A subsequence means terms chosen at distinct positions while retaining their
original order.  In this instance the subsequence must use ALL 64 positions.
For every chosen position i, choose a first weight a_i from
A = {1, 18446744073709551615}; the residue 18446744073709551615 means -1 modulo 18446744073709551616.  The second
weight is forced to b_i=1 because B={1}.

Find weights satisfying both defining congruences:

  sum(a_i*x_i for i=1..64) = 0 (mod 18446744073709551616)
  sum(b_i*a_i for i=1..64) = 0 (mod 18446744073709551616).

Report the weights as two groups of positions.  "plus" contains exactly
32 positions given weight +1; "minus" contains exactly 32
positions given weight -1.  The two lists must be disjoint and together must
be exactly the positions 1 through 64.  List order does not matter.  Repeats
are forbidden.  These shape rules make the second congruence explicit; the
first congruence is equivalently
sum(x_i for i in plus) - sum(x_i for i in minus) = 0 (mod 18446744073709551616).

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "plus" and "minus", each mapped to a JSON list of integers.
Syntax example for a four-position instance:
<answer>{"plus":[1,3],"minus":[2,4]}</answer>
Output nothing else inside the tags.
```

</details>

The planted answer is:

```json
{"plus":[3,5,7,9,10,14,17,19,20,22,23,26,27,31,32,33,35,37,38,39,40,44,47,49,50,51,52,53,54,57,58,59],"minus":[1,2,4,6,8,11,12,13,15,16,18,21,24,25,28,29,30,34,36,41,42,43,45,46,48,55,56,60,61,62,63,64]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the final plus index returns `(False, "wrong group sizes: each list must contain exactly 32 indices")`.

## Use

```python
import gen_2311_00090 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(**params, seed=12345)
question = gen.render(inst)       # give only this string to the solver
answer = gen.parse_answer(solver_output)
ok, reason = gen.verify(inst, answer)
```

From the repository root, emit 20 fresh, diversity-checked records with:

```bash
bash scripts/emit.sh 2311.00090 20 easy
```

## Caveats

NP-completeness is a worst-case result, not a proof that this planted random distribution is average-case hard. The four-vendor result only tests language models without external solver tools at medium effort; it is not a cryptographic claim. The 0/200,000 G4 observation samples uniformly from all balanced partitions, incorporating every statement-obvious constraint, but it neither supplies a statistical upper confidence bound below (10^{-6}) nor models meet-in-the-middle, lattice, SAT/ILP, or generalized-birthday solvers. Those stronger attacks were not run. Density is exactly (n/\log_2 q=1), chosen to avoid the familiar low-density subset-sum regime, but the power-of-two modulus may still expose useful 2-adic structure.

The solved coordinate has the same marginal distribution as every other residue, but planting necessarily creates one global (n)-way correlation; the three implemented attacks do not rule out a stronger correlation attack. Extra solutions are allowed and `verify` accepts them. `canonical_key` is exact under input reordering and under the affine symmetries (x\mapsto ux+c) with odd (u), which preserve balanced witnesses; it does not attempt to identify unrelated instances that happen to induce the same solution set. These are the main reasons to treat the measured evidence as a practical screen rather than a proof of average-case hardness.
