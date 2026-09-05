# Rejected after hardening: the hint breaks the held level

Paper: Dario Antolini, Guido Montúfar, and Alessandro Oneto,
[*Hadamard ranks of algebraic varieties*](https://arxiv.org/abs/2510.05231),
arXiv:2510.05231.

## Decision

The retained generator passes G and V and has a genuine Track-B
mechanical-versus-compact gap, but it cannot ship because **H/G9(b) fails**.
The bare oracle pool held the candidate `easy` preset on 3/3 completed attempts,
but the structural-hint arm solved it.  The rules permit one move up the named
ladder.  At that `medium` preset, a fresh bare Gemini attempt produced a witness
that the exact checker accepted.  Thus the higher level fails STEP 4 before its
hinted arm is even relevant.  Moving to `hard` would be a second hand escalation
after a G9 failure, which the protocol expressly forbids.

This is not a `cap_bound`: the answers at both tested levels fit comfortably.
It is also not a rejection merely because an efficient algorithm exists.  The
efficient algorithm and the substantial compression gap are quantified below;
the decisive evidence is that an in-context oracle actually recovered valid
witnesses at both allowed candidate levels.

The built module is retained as `rejected_gen_2510_05231.py`, as required.
`llm_loop_transcript.jsonl` and `.meta.json` are the original script-owned bare
easy run. `g9_hinted_transcript.jsonl` preserves the decisive easy hinted arm.
`medium_bare_transcript.jsonl` preserves the one permitted higher-level rerun.
The latter run was stopped after the medium solve because further escalation
would violate the one-rung rule; its API errors and the first automatically
started post-solve record remain in the transcript rather than being edited.

## What the paper actually defines

Section 2.2, Definition 2.2 defines the `X`-Hadamard rank of a projective point
`p` as the smallest number of points of `X` whose coordinatewise product is
`p`, in a fixed projective coordinate system.  This fixed basis is essential:
the paper explicitly warns that Hadamard products are not invariant under an
arbitrary projective change of coordinates.

Section 3, Lemma 3.3 quotes the exact line result used by the retained module.
If a line `L` in `P^N` avoids `Delta_(N-2)`—equivalently, no point on it has two
zero coordinates—then its `s`-th Hadamard power needs no closure and has
dimension `min(s,N)`. Proposition 3.4 concludes that `L^star N=P^N`, so every
target has a decomposition into at most `N` points of `L`.

For a line written in the affine form

```text
q(t) = 1 + t*x,
```

the retained family asks for sorted bounded rationals `t_0,...,t_(n-1)` with
`q(t_0) star ... star q(t_(n-1))` projectively equal to the supplied target.
The coordinates of `x` are nonzero and pairwise distinct, which executes the
lemma's exact hypothesis.  The solver receives the rational line and target,
and verification uses those objects directly; there is no discrete surrogate.

Two easy regimes found during the required full-paper read are important:

- Section 2.2 observes that an embedded toric variety is
  Hadamard-idempotent. Multiplying planted points of a toric `X`—the prior
  triage proposal—leaves the target in `X`; because `1` lies in `X`, a fixed
  factor count can be padded trivially. That proposed family fails H outright.
- Example 3.1 gives an explicit slice-by-slice Hadamard decomposition of any
  tensor into rank-at-most-two tensors. Its witness is produced by the displayed
  coordinate formula in linear output work, so it offers no Track-B compression
  gap.
- Section 5 treats identifiability of general Hadamard decompositions as future
  work. The paper therefore supplies no distributional hardness result that
  would license a Track-A claim for inverse-planted secant decompositions.

## Certificate production and exact checking

The retained family inverse-generates its witness. It samples positive rational
numbers on one arithmetic lattice,

```text
t_i = t_0 + i*h,
```

samples inverse line coordinates on the same lattice, forms every `q(t_i)`, and
only then multiplies them coordinatewise to create the target. Construction is
composition of exact identities, not solution of the emitted instance.

The answer is a JSON-native rational vector `[[num,den],...]`. The checker
enforces length, reduced positive bounds, distinctness, and increasing order,
reconstructs the line points with `fractions.Fraction`, and compares all target
coordinates by exact projective cross multiplication. It never reads
`inst["answer"]`. The demo setting has exactly one valid answer among 6,545
bounded candidates by complete enumeration.

## Track decision and the two required costs

Track A is not claimed. The paper's theorems establish existence, finiteness,
and dimension, not average-case search hardness for this generated
distribution.

Track B was the only defensible candidate. For a general line instance, define

```text
f(z) = product_i (1 + t_i*z).
```

The target supplies `f` at `n+1` distinct rational coordinates. A standard
exact route interpolates `f` and factors it; the implemented reference method
uses modular Newton interpolation followed by a scan of the bounded reduced
rationals for roots `-1/t`. It succeeds on 8/8 local seeds.

| candidate level | standard mechanical route | compact route | answer size |
|---|---:|---:|---:|
| easy (`n=31,H=512,D=5`) | median **212,015** exact field operations, **0.0042 s** | **84** exact arithmetic operations | 249 chars, 62 atoms on the measured seed |
| medium (`n=63,H=1536,D=7`) | median **1,307,201** exact field operations, **0.0522 s** | **150** exact arithmetic operations | at most 559 chars over 100 measured seeds, 126 atoms |

The compact route inverts the line coordinates, notices that both inverse
coordinates and factors share a step `h`, and recognizes a rising factorial.
For adjacent inverse coordinates `s,s+h`, one target ratio determines `t_0`;
repeated addition emits the sorted factors. The structural hint deliberately
names only the arithmetic-lattice/rising-factorial invariant. It does not state
the ratio, the rearrangement, or an action sequence. Hence the easy hinted solve
is a valid G9(b) failure, not an over-informative-hint artifact.

The costs are not comparable: this family really does compress hundreds of
thousands or more exact operations to under 151. Therefore the existence of
interpolation/factorization is **not** the rejection reason. The oracle evidence
shows instead that the intended insight is recoverable in context at the held
level, and the one permitted larger level is already solvable bare.

## Measured gates and oracle evidence

The retained `selftest_report.json` records the candidate easy level. It is
intentionally not all-passing because G9 is the rejection gate.

| gate | result |
|---|---|
| G1 construction | pass, 16/16 preset/seed checks |
| G2 corruptions | pass, five corruptions rejected for five distinct reasons |
| G3 output round-trip | pass |
| G4 structure-aware guessing | pass, 0/200,000; bounded space has about 5.05e66 candidates |
| G5 density + cost | pass locally; demo exact count 1, reference solves 8/8 |
| G6 adversaries | pass locally; four in-context attacks each 0/8, reference 8/8 as Track B expects |
| G7 scaling | pass |
| G8 canonical key | pass, 20/20 relabellings, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(b) | **fail**, hinted oracle solved easy |
| G9(c) | pass, 249 chars, 62 atoms, 84 intended operations at easy |

The bare easy transcript has one excluded xAI timeout followed by three scored
failures: Gemini and Claude returned wrong decompositions, and GPT-5.6-terra
returned no parseable answer. In the hinted easy transcript, Claude failed and
xAI returned a verified answer. In the medium bare rerun, Claude and
GPT-5.6-terra failed after excluded timeout records, while Gemini returned a
verified answer. The four-vendor pool was unchanged; the medium rerun used the
script's documented 240-second total-deadline override after repeated 900-second
xAI hangs. Timeout records are errors, never scored failures.

The placebo arm was not run after the decisive failures: G9(a) is diagnostic,
whereas easy had already failed the gated G9(b) test and medium had failed the
bare STEP-4 requirement. Continuing to spend oracle calls could not change the
decision and would contradict the instruction to stop once a gate fails.

## Final gate outcome

| requirement | outcome |
|---|---|
| G — generatable | **Pass:** inverse generation plus a rising-factorial product identity. |
| V — verifiable | **Pass:** exact rational line membership and projective Hadamard equality. |
| H — Track A | Not claimed; no theorem covers hardness of the generated distribution. |
| H — Track B, local | Passes the mechanical/compact distinction: 212,015 vs 84 operations at easy. |
| H — required oracle protocol | **Fails:** easy is solved with the structural hint; medium is solved bare. |
| Output cap | Passes at both tested levels; this is not `cap_bound`. |

The correct outcome is therefore rejection, with the generator and all decisive
evidence retained for audit or future reconsideration under a different G9
policy.
