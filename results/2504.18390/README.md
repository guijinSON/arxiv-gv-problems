# Cyclic 1-rotational unital base-family selection

**Status:** the generator and every local gate pass, but the required oracle and G9 runs are externally incomplete. In the current bare run, two scored models both solved `easy`; OpenRouter then returned HTTP 403 `Key limit exceeded` before the required third scored attempt, so the harness could neither escalate nor issue a verdict. This result is **not ready to submit**.

| profile field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | exact cover |
| certificate form | exact symbolic (a base-block set system) |
| native objects | base blocks in `Z_125`; a 1-rotational `S(2,6,126)` difference family |
| intended intuition | invariant: centered moments reveal a shared affine multiplier |
| domain essentiality | native; no reduction |

## The problem and why the witness is trustworthy

The source is Hetman, Banakh, and Ravsky, [*Point-transitive and 1-rotational unitals of order 5*](https://arxiv.org/abs/2504.18390). Section 1 identifies an order-5 unital with a Steiner system `S(2,6,126)` and describes the order-125 action with one fixed point. Example 2.1 prints a five-block difference family over `Z_125`. The generator retains the fixed infinity block and asks the solver to choose the other four base blocks from row-wise pools of affine images.

A submitted panel is checked by forming the 30 directed differences of each chosen six-point block. The four multisets must partition the 120 nonzero residues other than `25,50,75,100`; the fixed infinity block supplies the remaining short orbit. This is an exact executable certificate. Expanding the paper's original five blocks independently gives 525 blocks whose 7,875 pairs cover all `C(126,2)=7,875` point-pairs exactly once.

Generation samples the common affine square class and its four answer blocks first, then adds affine-image peers. Within each row, plants and decoys both have a uniform unit multiplier and uniform translation. Rows A/B and C/D each share only the planted square class, so the certificate is known by transformation of the paper's displayed family rather than by solving the emitted instance.

## Why this is Track B

The paper is a fixed-order catalogue: it gives no hardness theorem, growing parameter regime, or construction-search complexity. Track A would therefore be false. The honest reference method here is row-constrained Algorithm X: compute every candidate's directed-difference mask and backtrack over four rows. Its worst case is `O(p*n^4)` mask trials after `O(p*n)` preprocessing. At the hard preset it solved 8/8 local instances, averaging 4,754 exact difference/mask operations, 434 search nodes, and 0.000459 seconds.

The shorter route uses the exact checksums printed with each candidate. If `S=uT+t`, its centered moments satisfy `C2(S)=u^2 C2(T)` and `C4(S)=u^4 C4(T)` modulo 125. Rows C and D have invertible template `C2` values, so their normalized values expose their unique common `q=u^2`; `q` and `q^2` identify the matching A and B blocks. The implemented route solved 8/8 and needs at most 98 exact modular operations at shipping size. This 4,754-versus-98 gap, not a claim that exact cover is computationally hard, is the Track B basis.

## Worked demo (`n=2, panels=1, seed=0`)

This is the complete rendered instance:

```text
CYCLIC 1-ROTATIONAL UNITAL BASE-FAMILY SELECTION

All finite point labels are residues in Z_125, with addition modulo 125.
There is also one fixed point called infinity. A block is an unordered
set of six distinct finite residues. For each panel, choose exactly one
advertised block from each displayed row, in displayed row order.

For a chosen finite block B, its development is all translates
B+t={x+t mod 125:x in B}. The fifth base block is fixed as
{0,25,50,75,100,infinity}, together with all of its translates.
Your four choices are valid exactly when their 120 directed differences
x-y mod 125 (over all ordered distinct x,y in each chosen block) are
each of the residues 1,...,124 except 25,50,75,100 exactly once.
Equivalently, the five developed base blocks form an S(2,6,126): every
unordered pair of the 126 points occurs in exactly one developed block.

Candidate promise and redundant checksums: every candidate in a row is
an affine image {u*x+t mod 125:x in T} of that row's displayed template
T, where gcd(u,125)=1. For a block S define mean(S)=21*sum(S) mod 125
and C_k(S)=sum((x-mean(S))^k for x in S) mod 125. Each line gives the
exact C_2 and C_4 values; they are redundant and can be recomputed.
Order of candidates and order of residues inside a submitted block do
not matter. Repeated blocks within a panel are not allowed by the rows.

PANEL 1
ROW A template=[0, 1, 3, 15, 47, 74] C2(T)=70 C4(T)=89
  1: [12,58,66,70,84,114] C2=30 C4=99
  2: [45,54,67,74,78,106] C2=55 C4=14
ROW B template=[0, 4, 9, 20, 65, 103] C2(T)=35 C4(T)=61
  1: [19,64,67,79,102,110] C2=90 C4=11
  2: [17,57,61,87,90,106] C2=85 C4=96
ROW C template=[0, 6, 40, 88, 95, 112] C2(T)=48 C4(T)=25
  1: [2,8,9,11,66,96] C2=73 C4=25
  2: [17,47,57,83,84,101] C2=27 C4=25
ROW D template=[0, 8, 18, 41, 76, 104] C2(T)=97 C4(T)=81
  1: [11,16,30,32,79,85] C2=78 C4=31
  2: [5,25,26,56,102,114] C2=98 C4=86

Output one JSON outer array. Its entries correspond to panels in the
displayed order. Each panel entry must be an array of exactly four
chosen six-integer blocks in displayed row order. Use integers 0..124;
do not output candidate numbers or the fixed infinity block.
Give your final answer inside <answer></answer> tags, as that JSON array.
Example: <answer>[[[0,1,2,3,4,5],[6,7,8,9,10,11],[12,13,14,15,16,17],[18,19,20,21,22,23]]]</answer>
Output nothing else inside the tags.
```

Because `48^-1=112` and `97^-1=58` modulo 125, the C-row keys are `51,24` and the D-row keys are `24,59`; their common value is `q=24`. Its square is 76. That predicts `(C2,C4)=(55,14)` in A and `(90,11)` in B, giving:

```json
[[[45,54,67,74,78,106],[19,64,67,79,102,110],[17,47,57,83,84,101],[11,16,30,32,79,85]]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last point of the first block returns `(False, "panel 0 row A block must contain exactly 6 points")`. The demo is genuinely hand-solvable; the calculation above is the intended route in miniature.

## Difficulty presets

| preset | choices/row | panels | candidate blocks | row-respecting search space | compact operations | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 2 | 1 | 8 | 16 | 25 | hand example; skipped by harden.py |
| easy | 10 | 2 | 80 | 100,000,000 | 66 | defeated by two scored oracle calls; run then blocked |
| medium | 14 | 2 | 112 | 1,475,789,056 | 82 | locally available |
| hard | 18 | 2 | 144 | 11,019,960,576 | 98 | configured shipping preset; local gates pass |

`escalate()` first raises choices per row to 25 without lengthening the witness, then adds independent panels until the 300-operation cap binds.

## Gate results

| gate | measured result |
|---|---|
| G1 | 20/20 plants verified; 20/20 answers round-trip through JSON |
| G2 | 7/7 corruptions rejected with 7 distinct reasons |
| G3 | tagged, fenced, prose-wrapped JSON round-tripped; garbage returned `None` |
| G4 | 0/200,000 row-respecting guesses; 11,019,960,576 candidates |
| G5 | exact shipping count 1; density `9.0744e-11`; reference 4,824 operations and 0.000506 s on the measured seed |
| G6 | four attacks each 0/8; Algorithm X 8/8 as expected; compact route 8/8 |
| G7 | 144-to-288 candidate-block instance built and verified; next fixed-witness escalation also verified |
| G8 | 40/40 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 175 characters, 44 estimated tokens, 48 atoms, 98 intended operations |

The full machine-readable measurements are in [selftest_report.json](selftest_report.json).

## Oracle loop and G9 diagnostic

The current checkout's harness used its two-vendor default pool. A single solved attempt defeats a rung, so `easy` is demonstrably defeated; however, the harness requires three scored attempts before moving on, and quota expired first. The script-written transcript contains:

| preset | model | seed | scored result | why |
|---|---|---:|---|---|
| easy | google/gemini-3.8-flash | 1632556603 | solved | returned a witness accepted by `verify` |
| easy | openai/gpt-5.6-terra | 39382443 | unscored error | HTTP 403: total key limit exceeded |
| easy | openai/gpt-5.6-terra | 769416981 | solved | returned a witness accepted by `verify` |
| easy | google/gemini-3.8-flash | 1894027415 | unscored error | HTTP 403: total key limit exceeded |
| easy | google/gemini-3.8-flash | 252702943 | unscored error | HTTP 403: total key limit exceeded |
| easy | openai/gpt-5.6-terra | 1337806954 | unscored error | HTTP 403: total key limit exceeded |
| easy | google/gemini-3.8-flash | 848388023 | unscored error | HTTP 403: total key limit exceeded |

There is therefore no result for `medium` or `hard` and no hardened verdict. The isolated G9 files were produced by earlier script-owned attempts and contain only provider-error records. Bare, structural-hint, and placebo shipping arms remain `0/0`, so `hinted - placebo` is unavailable and no conclusion about the invariant's effect on models is justified. The task prose still describes a four-vendor pool, while the checked-in `harden.py` currently declares two vendors; `.meta.json` records the pool actually used.

## Use

```python
from gen_2504_18390 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

After restoring OpenRouter quota, rerun the bare harness here:

```bash
python3 ../../scripts/harden.py gen_2504_18390.py
```

Run the hinted and placebo arms in separate scratch directories as required, copy their script-produced transcripts back, update `G9_RESULTS`, rerun `selftest()`, and only then emit from the repository root:

```bash
bash scripts/emit.sh 2504.18390 20 hard
```

## Caveats

- This benchmark wraps a finite catalogue entry in an affine-image selection problem. The central-moment invariant and decoy distribution are generator additions, not a hardness claim made by the paper; the underlying blocks and verification criterion remain the paper's native difference-family objects.
- The exact G4 density is for the stated prior: one uniform advertised candidate from every row. It says nothing about a solver using the printed moments, which is exactly the intended shortcut.
- The attack panel did not run SAT/ILP packages, a full DLX implementation, learned ranking, or a specialized cyclic-design isomorphism tool. The included exact-cover backtracker is the domain-standard mechanical reference and is expected to win.
- Plants and decoys have identical one-block marginals, but their cross-row square-class correlation is deliberate. Detecting that higher-order invariant is the task.
- `canonical_key` is complete for the generator's tested translations, unit multiplications, and reorderings, but is not a complete isomorphism test for arbitrary cyclic designs.
- The native order stays 5. Difficulty grows by crowding affine images and composing panels, not by claiming a theorem for unitals of larger order.
- Most importantly, the oracle hardening and G9 diagnostics remain incomplete because of external quota. Two valid `easy` solves are evidence that the first rung is too easy, not evidence about either configured higher rung; local gates do not substitute for the missing verdict.
