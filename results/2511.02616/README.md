# Verified generator for arXiv:2511.02616

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / regime | algebra / finite field |
| Computational core | polynomial identity |
| Certificate | integer tuple encoding one native field element |
| Intended intuition | change of variables |
| Domain essentiality | native; no reduction |

## Problem and trust model

The source is Pang, Yuan, Wu, and Guan, [*New permutation polynomials over
\(\mathbb F_{q^2}\)*](https://arxiv.org/abs/2511.02616).  An instance gives a
quadratic field `K=F_p[alpha]/(alpha^2-u)`, several polynomials

`f_j(x)=(x^p-x+delta_j)^(p+2)+gamma_j*x`,

and a target `T`.  The solver must return the unique native field element whose
image under the ordered composition is `T`.  `verify` substitutes the proposed
pair into those same finite-field polynomials and compares two residues, using
no float and never reading the planted answer.

Generation is inverse: it samples the answer first and evaluates forward.  In
Theorem 3.1(ii), write `delta=a+b*alpha`, take nonsquare `u`, require
`p = 2 (mod 3)`, and set `gamma=2*a^2`.  Then
`Tr(delta)^2=Tr(gamma)`, so every layer is a permutation.  A composition of
these layers is again a permutation and therefore has exactly one preimage.
The literal extension-field calculation and the proof's coordinate formula are
cross-checked in G1 on every preset.

## Why this is Track B

This family makes no average-case or cryptographic hardness claim.  Section 2,
Propositions 2.1–2.2 translate an extension-field polynomial to a coordinate
map.  Theorem 3.1 and its proof are also what make this family easy with the
right insight: for `gamma=2*a^2`, the coordinates become

`(2*a^2*y-u*a*z^2+a^3, -u*z^3+b*a^2)` with
`x=y-(z-b)*alpha/2`.

The implemented mechanical solver uses that reduction but scans every `z`; it
costs `O(layers*p)`.  At shipping size its eight-seed mean was 926,457 scan
iterations, 3,705,919 counted exact operations, and 0.112 seconds on this
machine.  It solved 8/8, as Track B requires.  The compact route notices that
cubing is bijective because `gcd(3,p-1)=1`, raises to exponent `(2p-1)/3`, and
does the two linear recoveries in reverse layer order.  That route used 228
operations on the measured shipping instance and at most 231 over the panel.
The benchmark tests whether a no-tool solver can discover and execute that
compression; Track A would be false because the coordinate proof gives it.

## Worked demo (`n=11`, one layer, seed 0)

The complete rendered instance is:

```text
Invert a composition of permutation polynomials over a quadratic finite field

Let p = 11.  Work in K = F_p[alpha]/(alpha^2-u), where
u = 8.  Thus alpha^2 = 8, and all integer
coefficients and both coordinates are reduced modulo p to 0,...,p-1.
Represent r+s*alpha by the ordered pair [r,s].  Pair order matters.
Addition and multiplication are

  [r,s]+[v,w] = [r+v, s+w] (mod p),
  [r,s]*[v,w] = [r*v+8*s*w, r*w+s*v] (mod p).

For each row j below, delta_j=[a_j,b_j] means a_j+b_j*alpha and

  f_j(x) = (x^p - x + delta_j)^(p+2) + gamma_j*x.

The rows, in composition order, are:

  j | delta_j=[a_j,b_j] | gamma_j
  1 | [7,0] | 10

Define F(x)=f_L(...f_2(f_1(x))...), using the rows in the listed order.
The target is T = [6,10].

Find the unique field element x=[r,s] with F(x)=T.  Your answer must
contain exactly two decimal integers with 0 <= r,s < 11; do not
swap them.  Powers, including x^p, are powers in K, not coordinatewise
integer powers.  Every interval above is closed and repetitions are allowed.

Give your final answer inside <answer></answer> tags as one JSON list
[r,s] of two decimal integers.
Example: <answer>[3, 7]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[4, 8]</answer>` and verification returns `(True,
"ok")`.  Swapping it gives `[8,4]` and returns `(False, "wrong preimage:
F(candidate)=[7, 4], target=[6, 10]")`.  A person can solve this demo on
paper by checking its 121 field elements; `enumerate_all` confirms exactly one
answer.

## Difficulty presets

| Preset | Lower bound `n` | Actual prime | Layers | Outcome |
|---|---:|---:|---:|---|
| demo | 11 | 11 | 1 | hand-scale; not sent to oracles |
| easy | 10,007 | 10,007 | 1 | solved by 3/3 oracles |
| medium | 100,003 | 100,019 | 2 | solved by 2/3 oracles |
| hard | 500,000 | 500,009 | 4 | **ships; solved by 0/3 valid oracles** |

Both the modulus and composition depth grow while the answer remains two
coordinates.  G7 additionally built `p=1,000,037` with five layers and verified
its planted preimage.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed witnesses; coordinate identity and JSON round-trip |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | prose/fence/tag round-trip; garbage returned `None` |
| G4 | pass | 0 hits / 200,000 structure-aware samples; exact chance `1/250009000081` |
| G5 | pass | shipping sampled density 0; 4,096 restarts failed in 0.0159 s; demo count 1 |
| G6 | pass | four attacks each 0/8; mechanical reference solved 8/8 |
| G7 | pass | doubled lower bound and fifth layer built and verified |
| G8 | pass | 60/60 basis invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | hinted pool held; 14 chars/tokens, 2 atoms, 228 intended operations |

## Oracle loop

| Preset | Model | Seed | Result | Reason |
|---|---|---:|---|---|
| easy | Claude Sonnet 5 | 326674854 | solved | verified preimage |
| easy | Grok 4.6 | 627698339 | solved | verified preimage |
| easy | GPT-5.6 Terra | 1635821473 | solved | verified preimage |
| medium | Grok 4.6 | 741679431 | solved | verified preimage |
| medium | Gemini 3.1 Pro Preview | 494463874 | failed | returned pair had the wrong image |
| medium | GPT-5.6 Terra | 320303582 | solved | verified preimage |
| hard | Grok 4.6 | 648999318 | error | 900-second deadline; excluded and redrawn |
| hard | GPT-5.6 Terra | 1252533402 | failed | returned pair had the wrong image |
| hard | Claude Sonnet 5 | 419866417 | failed | empty length-limited response |
| hard | Gemini 3.1 Pro Preview | 687776903 | failed | returned pair had the wrong image |

The official bare verdict is `hardened` at `hard` after two escalations.  The
Grok error is not part of the 0/3 claim.

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted - placebo = 0.0`.  The hint bought no observed success, so this run
does not demonstrate sensitivity specifically to the declared change of
variables; it shows only that naming the pure-cube invariant did not make the
four-layer arithmetic solvable.  The measured answer was 14 characters and a
conservative 14-token bound (the language-wide maximum is 15 characters), with
two atomic elements.  The intended route used 228 exact operations.

## Use

```python
from gen_2511_02616 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
answer = parse_answer("<answer>[123, 456]</answer>")
print(verify(inst, answer))
```

From the repository root:

```bash
bash scripts/emit.sh 2511.02616
```

## Caveats

- The structural `O(layers*log p)` inverse makes this easy with modular-arithmetic
  tools.  Neither the paper nor this generator supports a Track A hardness claim.
- The `0/200,000` guess result is for the uniform prior on all `p^2` field
  elements.  It says nothing about a solver that has recognized the theorem's
  coordinate map; exact uniqueness comes from the permutation theorem, not the
  sample.
- The panel did not try a CAS, a generated lookup table, vectorized exhaustive
  evaluation, or a learned cross-instance attack.  Those are expected to help
  and do not contradict Track B.
- Claude exhausted its 32k response budget in all three hard arms.  Those count
  under the supplied harness but are weaker evidence than Terra's and Gemini's
  parsed, incorrect pairs.
- Timings are Python wall-clock measurements on this machine.  The operation
  counts are the portable comparison.
- `canonical_key` normalizes every scaling and conjugation of the trace-zero
  quadratic basis.  It does not attempt arbitrary nonlinear encodings of the
  same abstract field; the rendered representation fixes the prime-field
  coordinates and multiplication law.
