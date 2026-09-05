# Exact mixed equilibrium generator for arXiv:2112.03442

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | optimization |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate form | exact symbolic |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

## What the problem is, and what is verified

This module turns Morris Yau's [*Approximating Nash Equilibrium in Random
Graphical Games*](https://arxiv.org/abs/2112.03442) into exact binary-action
polymatrix games. The solver receives rational pairwise payoff functions in a
succinct native representation and must give a sparse exact description of a
full-support product mixed strategy. `verify` reconstructs every probability
and checks every player's two expected pure-action payoffs by integer
Walsh-character sums. It accepts any valid certificate in the stated bounded
language and never reads `inst["answer"]`.

The certificate is known by inverse generation: four sparse centred mixing
probabilities on each side are sampled first; all forcing values are then
formed by an exact generalized Hadamard transform. The transform identity
guarantees indifference. Because the Hadamard matrix is invertible and all
probabilities have full support, the promised bounded language has exactly one
valid certificate. No equilibrium solver is used during generation.

The correctness, density, adversary, scaling, canonicalization, and output-cap
gates pass. The required external oracle evidence is **not yet complete**.
At `easy`, three valid harness calls finished and two models solved the
instance, so that rung is rejected. Those calls preceded the final G4 fix,
which made the code-zero sign constraint explicit in `render`; they are useful
diagnostic evidence but cannot certify the current renderer. When the harness advanced to `medium`, the
OpenRouter key hit HTTP 403 “Key limit exceeded (total limit)” on every redraw.
Those error records are preserved in `llm_loop_transcript.jsonl` and are not
counted as model failures. Consequently this directory is locally verified but
is not submission-ready until the bare loop and two G9 runs finish with a
usable key.

## Why this is Track B

Track A would be false. Section 2, Definitions 2.1–2.4 give the exact native
objects used here. Theorem 2.1 gives a deterministic
`(Nk)^{O(L^4 log(k)/epsilon^4)}` approximation algorithm on sufficiently dense
random interaction structures, and Section 4 says its runtime is dominated by
the convex-hierarchy/ellipsoid solve. Section 3 also identifies polymatrix
zero-sum games as polynomial-time solvable. This generator does not claim the
paper's average-case hardness—the paper proves an algorithm, not hardness.

For this structured distribution there is a still faster reference algorithm:
undo the binary shear and apply two fast Walsh–Hadamard transforms. Its
complexity is `O(n log n)` exact operations. At the shipping preset (`n=1024`
per side), eight measured runs solved 8/8, averaging **0.015340 s** and using
**24,576 counted exact/bit operations**. That is routine in a sandbox but not a
credible hand computation over 2,048 shuffled player records.

The compact route notices that the forcing values are signed superincreasing
codes and that the displayed matrix is a rank-one binary shear. Reading code
zero and the ten basis codes on each side recovers all support indices and
signs in at most **165 exact arithmetic/bit operations**, including undoing the
binary shear. The task tests discovery of that
change of variables, not whether an efficient algorithm exists.
The module implements this compact decoder as an independent executable check;
it recovered and verified the exact certificate on 8/8 gate seeds (and 400/400
additional audit instances), averaging **0.002569 s** in the recorded gate run.

## Worked demo (`seed=0`)

This is the complete rendered demo. A person can solve it on paper: only two
binary coordinates and eight player records are present.

```text
EXACT MIXED NASH EQUILIBRIUM IN A SUCCINCT POLYMATRIX GAME

There are 8 players, split into LEFT and RIGHT groups of 4.
Each player has public actions 0 and 1. Every LEFT player interacts
once with every RIGHT player; there are no same-group interactions.
Payoffs add over all of a player's pairwise interactions.

Each player record is: id  binary_code  flip  positive_scale  force.
Codes have 2 bits. The rightmost printed bit is coordinate 0.
For a public action a, define its latent action z = a XOR flip.
All binary matrix/vector arithmetic below is over GF(2).
The matrix M is given by its rows (again coordinate 0 is rightmost):
  M[0] = 11
  M[1] = 10

For binary codes r,c, define chi(r,c)=(-1)^(r dot (M c)).
For an ordered interaction from player i to opposite-side player j,
the payoff received by i is exactly

  f_ij(a_i,a_j) = 1/(4n) + z_i/(64n) *
      [scale_i*chi(code_i,code_j)*(2z_j-1) - force_i/(W*n)].

Here n=4 and W=19. These rational payoffs lie in [0,1/n],
so the game is 1-smooth in the paper's normalization.

A mixed strategy profile is a product distribution: players randomize
independently. It is a Nash equilibrium when no player can increase
expected payoff by replacing its random action with fixed action 0 or 1.

PROMISED CERTIFICATE LANGUAGE
There is a full-support equilibrium in which, for each side, exactly 2
players have nonzero centred latent probability

  t_i = 2*P(z_i=1)-1 = signed_numerator/W.

Every omitted player has t_i=0. Within each side the absolute numerators
must use each weight exactly once: [5, 9].
The sign attached to each weight is uniquely fixed by the equilibrium
equation of the opposite-side record whose binary code is all zero.
All resulting probabilities are strictly between 0 and 1.

LEFT records:
  1 00 1 3 -12
  2 10 0 3 42
  3 01 0 2 -28
  4 11 0 1 4

RIGHT records:
  5 01 1 2 -28
  6 11 0 2 28
  7 00 1 2 8
  8 10 0 3 -12

Return exactly one certificate. Pair order is irrelevant; player IDs are
the displayed 1-based IDs, cannot repeat within a side, and must belong
to that side. Every rational must be the exact JSON pair [num,den]
with den=W; do not use decimals or an implicit denominator.
Give your final answer inside <answer></answer> tags as compact JSON:
Example: <answer>{"left":[[1,[-5,19]],[2,[9,19]]],"right":[[5,[5,19]],[6,[-9,19]]]}</answer>
Output nothing else inside the tags.
```

The constructed answer is:

```json
{"left":[[2,[9,19]],[4,[-5,19]]],"right":[[5,[5,19]],[6,[-9,19]]]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last
left term returns `(False, "left must contain exactly 2 terms (got 1)")`.

## Difficulty presets

| preset | players per side | sparse terms per side | row-scale range | status |
|---|---:|---:|---:|---|
| demo | 4 | 2 | 1–3 | exhaustive count 1; hand-scale |
| easy | 64 | 4 | 1–3 | pre-final renderer rejected by oracle: 2/3 solved |
| medium | 256 | 4 | 1–5 | oracle calls blocked by exhausted key quota |
| hard | 1,024 | 4 | 1–7 | **shipping preset**, pending oracle evidence |

Difficulty grows by expanding the transform haystack and scale decoys while
the eight-term answer remains fixed. `escalate` doubles the haystack and can
also widen the scale range; it does not lengthen the witness.

## Gate results

| gate | measured result |
|---|---|
| G1 planted verifies | 12/12 preset/seed combinations, with exact pair-payoff bounds on all 12 |
| G2 corruptions | 5/5 rejected with 5 distinct reasons |
| G3 round-trip | tagged JSON recovered through prose and a Markdown fence; 4/4 malformed cases returned `None` |
| G4 structure-aware guessing | 0/200,000; language size 1,194,825,427,695,764,898,840,576 |
| G5 density and cost | sampled 0/200,000; unique exact solution; demo enumeration 1; final run: reference 0.002924 s / 24,576 ops; compact route 0.000254 s / 165 ops |
| G6 adversaries | four attacks, each 0/8; reference algorithm 8/8 and compact decoder 8/8 as expected |
| G7 scaling | doubled instance at 2,048 per side builds and verifies; space grows from 80 to 88 bits |
| G8 canonical key | 120/120 invariance and transported-witness checks; 20/20 unrelated keys distinct |
| G9(c) caps | 165 chars, 42 estimated tokens, 24 atoms, 165 intended arithmetic/bit operations |

The G4 prior is deliberately structure-aware: it samples exactly four
distinct IDs per side, assigns every required weight once, and uses the unique
sign pattern forced by each code-zero equation. It does not sample malformed
JSON, illegal supports, or sign patterns a solver can eliminate for free. Its zero-hit
estimate shows that blind guessing under that prior is rare; it does not prove
difficulty against algebraic structure, which is why G6 and the reference
algorithm are reported separately.

## Oracle loop

The valid calls below used the pre-final renderer; the final two lines added
to the current prompt expose only the already-deducible code-zero sign
constraint. The complete loop nevertheless must be rerun before submission.

| preset | seed | model | solved | result |
|---|---:|---|---|---|
| easy | 919020057 | Gemini 3.8 Flash | yes | exact certificate verified |
| easy | 1913265110 | GPT-5.6 Terra | yes | exact certificate verified |
| easy | 625355417 | GPT-5.6 Terra | no | returned an `error` object claiming no certificate exists |
| medium | 102876269 | GPT-5.6 Terra | error | HTTP 403 key limit; not counted |
| medium | 300030652 | GPT-5.6 Terra | error | HTTP 403 key limit; not counted |
| medium | 736785072 | GPT-5.6 Terra | error | HTTP 403 key limit; not counted |
| medium | 1753898299 | GPT-5.6 Terra | error | HTTP 403 key limit; not counted |

## G9 diagnostics

| arm | preset | completed attempts | solved | result |
|---|---|---:|---:|---|
| bare | hard | 0 | 0 | current shipping renderer not reached |
| structural hint | hard | 0 | 0 | not run because the credential is blocked |
| placebo hint | hard | 0 | 0 | not run because the credential is blocked |

`hinted - placebo` is therefore unavailable, and no conclusion about the
claimed intuition can honestly be drawn yet. When credentials work, run all
three arms and replace the zero-attempt diagnostics in the module/report. The
structural hint names only the signed-code/rank-one-shear invariant; it does
not give the decoding procedure.

## Use

```python
from gen_2112_03442 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
prompt = render(inst)
candidate = parse_answer('<answer>{"left":[...],"right":[...]}</answer>')
ok, reason = verify(inst, candidate)
```

From the repository root, after successful oracle runs:

```bash
bash scripts/emit.sh 2112.03442 20
```

## Caveats

The interaction pattern and payoffs are deliberately structured, not samples
from the paper's `G(N,p)` average-case distribution; the coverage is native to
the paper's polymatrix equilibrium definitions, not evidence for Theorem 2.1's
random-instance regime. A solver that implements the Walsh transform makes the
family easy in milliseconds, as Track B openly requires. The attack panel did
not test generic support-recovery packages, compressed sensing, or an external
CAS. The canonical key is invariant under the implemented presentation
symmetries (player renaming, action renaming, coordinate permutation, group
swap, and record order), but is deliberately a cheap invariant rather than a
complete strategic-equivalence canonization; rare nonisomorphic instances
could therefore share a key. It does not quotient arbitrary payoff-affine
transformations. Most importantly, only the easy rung of the multi-vendor
hardening loop has a valid measurement (and it was solved); the medium/hard
bare rungs and both G9 comparison arms remain unmeasured because of the
external 403. Local gates cannot substitute for that evidence.
