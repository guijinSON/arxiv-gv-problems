# arXiv 2202.13955 — verified permutation-graph cut certificates

> **Status (2026-09-05): verified and hardened.** All local gates pass. Three valid
> bare attempts across OpenAI and Google failed at `easy`, which is therefore the
> shipping preset. The structural and placebo diagnostic arms are also recorded.

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | combinatorics / finite field |
| Core / certificate | graph / degree-one polynomial over GF(2) |
| Intuition | invariant: the unique four-cycle’s label XOR is the cut normal |
| Domain essentiality | licensed reduction |
| Reduction | Section 4, proof of Theorem 1 |

## Problem and trust basis

The source is de Figueiredo, de Melo, Oliveira, and Silva,
[*MaxCut on Permutation Graphs is NP-complete*](https://arxiv.org/abs/2202.13955).
An instance gives a labeled cubic graph and the paper’s exact block-macro form of
the two permutations defining the much larger permutation graph. The solver returns
a GF(2) linear polynomial. Its values on the source labels define a source cut and,
through the paper’s map `f`, every side of the expanded cut. Verification performs
exact dot products, checks every source edge, counts link-link inversions, and
evaluates the paper's weighted block formula; it never reads the planted answer.

Generation is inverse. A dense even-weight polynomial is sampled first. A connected
simple cubic bipartite graph with exactly one four-cycle is sampled next. Labels are
drawn from the polynomial’s two parity half-spaces, with the four cycle labels
conditioned to XOR to the polynomial. Full rank of all edge-difference vectors makes
the bounded certificate unique. Since all source edges cross, Section 4’s inequality
certifies that the mapped permutation-graph cut reaches the threshold. No MaxCut or
linear system is solved during generation.

This is deliberately not a Track A claim. Theorem 1 is worst-case NP-completeness
from cubic MaxCut and does not make this generated distribution hard; Section 5 also
identifies threshold graphs as an easy subclass. Here dense Gauss–Jordan elimination
on `<c,label[u] XOR label[v]> = 1` is a disclosed `O(m d^2)` algorithm. On eight
shipping instances it solved 8/8 with a median 8,066 counted bit operations and
about 0.0001 s.
The compact route finds the unique four-cycle and XORs its four labels. Counting an
edge insertion, a cubic wedge inspection, every XORed bit, and every emitted bit, it
uses 188 elementary operations. The benchmark asks whether a solver notices this
roughly 43-fold compression.

The macro representation is paper-licensed and lossless. A source on `N` vertices
expands to `122N^3 + 102N^2 + 11N` vertices, so explicitly listing the shipping graph
would obscure rather than test the reduction. As a separate construction audit, the
macros were expanded for `N=16` into two genuine 526,000-element permutations; exact
inversion counting obtained 1,120,271,512 crossing edges against threshold
1,120,270,296, with the link correction inside Section 4's bound.

## Worked demo

For `demo`, seed 0, the source data are:

```text
labels: v0=df v1=e5 v2=6f v3=1a v4=4e v5=72 v6=43 v7=9a
        v8=91 v9=68 v10=30 v11=48 v12=84 v13=17 v14=e3 v15=5d
edges:  (1,13) (8,15) (3,11) (9,13) (10,12) (0,10) (0,11) (4,9)
        (4,6) (1,2) (5,8) (3,7) (5,9) (12,15) (3,5) (12,13)
        (6,10) (14,15) (6,7) (4,14) (1,7) (0,2) (8,11) (2,14)
```

The only four-cycle has vertices `(3,5,8,11)`. Its labels XOR to `0xb1`, whose
least-significant-bit-first coefficients are `<answer>10001101</answer>`.
`verify(inst, [1,0,0,0,1,1,0,1])` returns `(True, "ok")`; flipping coefficient 0
returns `(False, "source edge e3=(v9,v13) is not crossed")`. This demo is genuinely
hand-solvable: find four edges forming the cycle and do three two-hex-digit XORs.

## Difficulty and gates

| Preset | d | source V / E | expanded V | compact ops | Status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 16 / 24 | 526,000 | 104 | hand example |
| **easy** | **20** | **24 / 36** | **1,745,544** | **188** | **shipping; bare oracle held 0/3** |
| medium | 26 | 28 / 42 | 2,758,420 | 230 | locally verified |
| hard | 32 | 34 / 51 | 4,913,374 | 281 | locally verified |

From the shipping preset, `escalate()` keeps the 20-bit answer fixed and raises the
source order by two through 48 vertices. A further increase would exceed the
300-operation compact-route cap, so it returns `"cap_bound"` rather than
misclassifying the paper as exhausted.

| Gate | Measured result |
|---|---|
| G1 | 16/16 planted and four-cycle-invariant checks passed |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | model-style tagged response round-tripped; garbage returned `None` |
| G4 | 2/200,000 uniform 20-bit guesses; exact density `1/2^20 = 9.54e-7` from full rank |
| G5 | sampled density `1e-5` in 200,000 draws; exact density `1/2^20`; 256 restarts took about 0.002 s |
| G6 | four attacks 0/8 each; reference elimination 8/8 |
| G7 | `d=40,N=48` built and verified; 13,727,760 expanded vertices |
| G8 | 100/100 individual/composed relabellings invariant and valid; 20/20 unrelated keys distinct |
| G9(c) | 41 JSON chars, 11 estimated tokens, 20 atoms, 188 operations |

## Oracle loop

| Call | Preset | Seed | Model | Solved | Why |
|---:|---|---:|---|---|---|
| 1 | easy | 1526899326 | `openai/gpt-5.6-terra` | no | parsed bits failed on source edge `e0` |
| 2 | easy | 1531782745 | `google/gemini-3.8-flash` | no | length-limited empty answer; parser returned `None` |
| 3 | easy | 1870472027 | `google/gemini-3.8-flash` | no | parsed bits failed on source edge `e1` |

The script verdict is `hardened` at `easy` with no escalation. The second record is
distinguished in the transcript from an API error: it consumed a valid attempt
because the model emitted no witness within its token budget.

## G9 diagnostic

| Arm | Preset | Valid solved / attempts | Script result |
|---|---|---:|---|
| bare | easy | 0 / 3 | hardened |
| structural | easy | 1 / 3 | shipping rung defeated; next ambient size held 0/3 |
| placebo | easy | 1 / 3 | shipping rung defeated; supplementary escalation incomplete |

`hinted − placebo = 0.0`. In this small sample, naming the four-cycle invariant bought
no improvement over an equally styled placebo sentence, so the oracle experiment
does not isolate the claimed intuition even though the compact route verifies.

## Use

```python
import gen_2202_13955 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
prompt = g.render(inst)
text = "<answer>" + "".join(map(str, inst["answer"])) + "</answer>"
assert g.verify(inst, g.parse_answer(text)) == (True, "ok")
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 2202.13955 20
```

## Caveats

- The GF(2) labels and polynomial certificate are a benchmark encoding added around
  the paper’s Section 4 reduction; they are not objects introduced by the authors.
  The actual permutation graph and cut map remain present and exact, but the search
  is carried by the labeled cubic source, as `licensed_reduction` declares.
- `P(random guess)=1/2^20` is exact only for a uniform prior over shape-correct
  coefficient vectors. The observed 2/200,000 rate is noisy at this scale and does
  not contradict the exact full-rank count; neither number models a solver that
  notices the four-cycle.
- A 4,096-restart sampler did get one lucky hit across an earlier fixed eight-seed
  panel, as the exact density predicts can occasionally happen. The gated no-tool
  panel uses 256 restarts (0/8); bulk random sampling is not the Track B claim.
- The source is bipartite, so a BFS can recover its vertex cut cheaply. Converting
  that cut to the required polynomial still needs the disclosed full-rank solve.
- No SDP, spectral relaxation, or general exact MaxCut implementation was run on the
  1.75-million-vertex expansion. The specialized exact elimination is the relevant
  successful reference algorithm, but those remain untested attack surfaces.
- Canonicalization quotients identifier renaming only when the paper’s vertex and
  edge block orders are carried with it, and also quotients every common invertible
  affine change of GF(2) label coordinates; it correctly retains the structural orders.
- The G9 sample is only three calls per arm and showed no structural-over-placebo
  lift. It should not be read as evidence that the invariant is psychologically
  salient to models; only the bare 0/3 result supports the shipped hardness claim.
