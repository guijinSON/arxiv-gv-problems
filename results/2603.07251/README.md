# Balanced \(\{+1,-1\}\)-weighted zero sums

This generator specializes Section 1 of Krishnendu Paul and Shameek Paul, [*\(\{\pm1\}\)-weighted zero-sum constants* (arXiv:2603.07251v1)](https://arxiv.org/abs/2603.07251). A solver receives \(n\) residues modulo \(q=2^n\) and must assign exactly \(n/2\) signs \(+1\) and \(n/2\) signs \(-1\), using every position, so that the signed residue sum is zero. The answer is two lists of 1-based positions. Verification checks their shape and recomputes the paper's two congruences exactly in linear time.

## Why this regime is hard

The paper proves extremal constants, not a computational-complexity theorem; it contains no NP-hardness, FPT, or search-algorithm claim. The H basis is therefore explicit rather than attributed to the authors: balanced signed equality contains PARTITION. Given \(y_1,\ldots,y_t\), use the \(2t\) integers \(C+y_1,C,\ldots,C+y_t,C\) and require \(t\) plus signs. The constant terms cancel, and a witness exists exactly when the selected \(y_i\) sum to half the total. Padding with zero pairs and choosing a power-of-two modulus larger than the integer range keeps the reduction polynomial and makes modular equality ordinary equality. Thus the general decision problem is NP-hard; a supplied witness remains cheap to verify.

The chosen density is \(n/\log_2q=1\), where pseudo-polynomial dynamic programming costs polynomially in \(q\), not in its \(n\)-bit encoding, and meet-in-the-middle remains exponential. Section 3, Observation 3.1 fixes the exact equal-size/equal-sum form. Theorem 3.4 guarantees some weighted zero-sum subsequence at \(2k\) terms when \(2^k\ge |M|\); for \(q=2^n\) that is \(2n\) terms, while these instances have only \(n\) terms and require all of them. Other avoided collapses are Section 4's characteristic-two case, Observation 3.5 and Section 5's odd-modulus length-\(q\) reduction to ordinary zero sums, and Section 6's long consecutive-subsequence setting.

The sign vector is drawn first. A uniformly chosen coordinate is then solved after all others are sampled uniformly modulo \(q\). Its coefficient is a unit, so the solved coordinate is also uniform; rejection uses only coordinate-symmetric degeneracies. There is no separate decoy distribution.

## Difficulty presets

| preset | \(n=\log_2q\) | balanced candidate space | status |
|---|---:|---:|---|
| `easy` | 64 | 1,832,624,140,942,590,534 | **ships; three deciding vendors failed** |
| `medium` | 80 | 107,507,208,733,336,176,461,620 | available; not reached |
| `hard` | 96 | 6,435,067,013,866,298,908,421,603,100 | available; not reached |

`SHIPPING_DIFFICULTY = "easy"`. No named preset was rejected; the first rung held without retuning or escalation.

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 planted witness | pass | 12/12 across 3 presets and 4 seeds |
| G2 corruption | pass | 5/5 rejected through 5 distinct reasons |
| G3 round-trip | pass | tagged JSON recovered from prose and Markdown; garbage returned `None` |
| G4 structured guessing | pass | 0/200,000 uniformly sampled balanced partitions; measured rate 0, threshold \(<10^{-6}\) |
| G5 sparse | pass | exactly 2/184,756 valid at \(n=20\), fraction \(1.0825\times10^{-5}\) |
| G6 adversaries | pass | magnitude split 0/8; largest-first greedy 0/8; 24-restart one-swap search 0/8 |
| G7 scaling | pass | \(n=128\) built and verified; space grew to 23,951,146,041,928,082,866,135,587,776,380,551,750 |

## Oracle hardening loop

All calls used reasoning effort `medium`. Both Claude rows returned no answer after exhausting 32,000 completion tokens, so the repository harness excluded them and redrew; they are not counted as failures. Each deciding reply parsed successfully and then failed the exact first congruence, so no parser miss created the hardened verdict.

| preset | model | seed | solved? | why |
|---|---|---:|---|---|
| `easy` | Grok 4.6 | 827165603 | no | parsed; residue 3,699,934,353,795,747,764, not 0 |
| `easy` | GPT-5.6 Terra | 545242494 | no | parsed; residue 8,965,110,989,970,533,894, not 0 |
| `easy` | Claude Sonnet 5 | 258424728 | excluded error | empty length-limited response |
| `easy` | Claude Sonnet 5 | 826245695 | excluded error | empty length-limited response |
| `easy` | Gemini 3.1 Pro Preview | 1552374170 | no | parsed; residue 9,633,326,802,088,632,936, not 0 |

## Worked example

The complete smallest-preset render below is `easy`, seed 0. It is collapsed only to keep the page scannable.

<details>
<summary>Full rendered instance</summary>

```text
Balanced {+1,-1}-weighted zero-sum witness

All arithmetic below is in the ring Z/18446744073709551616Z: reduce every integer modulo 18446744073709551616,
using residue representatives 0 through 18446744073709551615.  The input is this ordered
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

A subsequence normally chooses distinct positions while retaining their input
order.  In this problem the subsequence must use ALL 64 positions.  At every
position i choose a weight a_i from A={1,18446744073709551615}, where residue 18446744073709551615
means -1 modulo 18446744073709551616.  The second weight is forced to b_i=1 because B={1}.

Find weights satisfying both congruences from the definition:

  sum(a_i*x_i for i=1..64) = 0 (mod 18446744073709551616)
  sum(b_i*a_i for i=1..64) = 0 (mod 18446744073709551616).

Report the weights as two groups of positions.  "plus" must contain exactly
32 positions assigned +1; "minus" must contain exactly 32
positions assigned -1.  The lists must be disjoint and together contain every
integer position from 1 through 64.  Positions are 1-indexed, list order does
not matter, and repeated positions are forbidden.  These shape rules make the
second congruence hold; the first is equivalently

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

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping position 59 from `plus` returns `(False, "wrong group sizes: each list must contain exactly 32 indices")`.

## Use

```python
import gen_2603_07251 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(**params, seed=12345)
question = gen.render(inst)       # give only this string to the solver
answer = gen.parse_answer(solver_output)
ok, reason = gen.verify(inst, answer)
```

From the repository root, emit 20 fresh, diversity-checked records with:

```bash
bash scripts/emit.sh 2603.07251 20 easy
```

## Caveats

NP-hardness is worst-case evidence, not proof that this planted random distribution is average-case hard. The four-vendor loop tests language models without external solver tools at medium effort; it is not a cryptographic claim. The observed 0/200,000 G4 rate comes from the strongest statement-obvious prior, uniform balanced partitions, but zero observed hits does not by itself establish a statistical upper bound below \(10^{-6}\), and it does not model meet-in-the-middle, lattice, SAT/ILP, or generalized-birthday solvers. Those stronger attacks were not run.

The solved coordinate has the same marginal distribution as every other coordinate, but planting creates a necessary global \(n\)-way correlation; the three attacks do not rule out a stronger correlation attack. Extra witnesses are allowed and `verify` accepts them. The power-of-two modulus may expose useful 2-adic structure despite the rejection of one-parity degeneracies. `canonical_key` is exact under input permutation and the affine symmetries \(x\mapsto ux+c\) for odd \(u\), which preserve balanced witnesses; it does not solve the more general problem of deciding whether unrelated residue multisets induce identical solution sets.

---

## Independent audit

Run separately from the builder's self-report, re-deriving the checks rather than
re-reading them. Attack code ships as
[`audit_pm1_attacks.py`](audit_pm1_attacks.py) (stdlib only — integral LLL was
written from scratch because this environment has no numpy/sympy/fpylll).

### Interface

| check | result |
|---|---|
| planted witness verifies | 21/21 — all 3 presets × 7 seeds |
| `verify` never reads `inst["answer"]` | confirmed by reading the source: touches only `n`, `modulus`, `sequence` |
| corrupted answers rejected | drop-one, duplicate, empty, out-of-range, `str`, `bool`, cross-group swap — all rejected, each with a distinct reason |
| `parse_answer` takes the **last** `<answer>` block | yes — draft-then-correction returns the correction; survives ``` fences and prose; garbage → `None` |
| `enumerate_all` vs brute force | exact agreement, n ∈ {8,10,12} × 3 seeds (count = 2 each: the plant and its negation) |
| `search_space` == `random_candidate` space | C(12,6) = 924, and 924 distinct partitions actually sampled; every draw shape-valid |
| `escalate` axis | n += 16 raises dimension *and* modulus together, holding density at 1.0 while MITM cost goes 2^32 → 2^40 → 2^48 |

`verify` accepting the plus/minus groups swapped is correct, not a leak: negating
every sign is a genuinely different valid witness.

### canonical_key

The one check `submit.sh` cannot make. It keys on neither the seed nor
`render(inst)`, and it is invariant under the family's real isomorphisms:

- permutation of input order — **40/40 unchanged**
- affine relabelling `x -> u*x + t (mod q)`, `u` an odd unit — **40/40 unchanged**
- both composed — **40/40 unchanged**
- unrelated instances — **40/40 distinct keys**

The affine map is a genuine relabelling, not an over-collapse: the transformed
instance still verifies against the *same* answer (checked), since
`sum(eps_i (u x_i + t)) = u*0 + t*0`.

### Attacks

The standard algorithms for this class were run against the real generator.

**Meet-in-the-middle** (exact, `O(2^(n/2))`) — correctly wired, and it solves real
instances until the space runs out:

| n | 16 | 24 | 32 | 40 | 64 (shipping) |
|---|---:|---:|---:|---:|---|
| solved | yes | yes | yes | yes | 2^32 half-space, not reachable |
| time | 0.00 s | 0.02 s | 0.45 s | 10.6 s | — |

**Lattice (LLL)** — fails at every size at the shipped density:

| n | 24 | 32 | 40 | 48 | 64 |
|---|---|---|---|---|---|
| density 1.00 | fail | fail | fail | fail | fail |

That null is only worth reporting because the same code demonstrably works where
theory says it should. Holding `n` fixed and inflating the modulus:

| density | 1.00 | 0.62 | 0.50 | 0.40 | 0.29 |
|---|---|---|---|---|---|
| lattice | fail | fail | **solved** | **solved** | **solved** |

That is the Lagarias–Odlyzko/CJLOSS boundary in the right place. Density 1 is
the deliberate choice that puts the family where lattice reduction stops working
and dynamic programming is blocked by `q = 2^n`.

**Statistical** — the plant leaves no coordinate-level trace over 400 instances at
n=64: mean value/q is 0.4969 on plus positions vs 0.4941 on minus (want 0.5);
the count of plus positions among the n/2 smallest values is 15.96 ± 2.02 against
an unbiased 16. The built-in magnitude and greedy adversaries score 0/200 each,
and `random_candidate` succeeds at the predicted ~2/C(n,n/2) — 1.09e-18 at n=64.

### Caveat the presets do not cover

MITM at `2^(n/2)` is not the best known attack. The representation technique
applies directly to balanced binary subset-sum at density 1 — Howgrave-Graham–Joux
runs in ~`2^(0.337n)` and Becker–Coron–Joux in ~`2^(0.291n)`. At the shipping
preset that is roughly **2^21.6 and 2^18.6**, not 2^32; at `hard` (n=96) still only
~2^28. **H** holds as the task defines it — every known method is exponential,
none is polynomial or closed-form — and no in-context LLM solver can execute these,
which is what the oracle pool measures. But the honest margin against a
*programmatic* attacker is ~2^19–2^28 across the whole ladder, not what the raw
candidate-space column suggests. If that threat model ever matters, `escalate`
should run well past n=96 rather than shipping `easy`.

### Verdict

Ships. The family is faithful to the paper — and notably sits *below* the paper's
own existence guarantee: the Section 3 bound yields a weighted zero-sum
subsequence only at `2k` terms with `2^k >= |M|`, i.e. 2n terms here, while
instances list n and require all of them. Existence comes from the plant, which
is why `enumerate_all` finds exactly 2 solutions rather than many.
