# Rejected: arXiv 1611.03069

## Decision

The constructed Reed--Solomon family fails mandatory gate **G9(b)** on
**Track B**.  It is therefore not shipped.  This is not a claim that the paper
or its native decoding problem lacks a useful mechanical-versus-compact gap.
The gap was measured and is substantial; the failure is that the compact route
became executable by the oracle pool as soon as its invariant was named.

## Step 0 and track

The paper's Introduction defines `RS(D,K)`, Hamming distance, bounded-distance
decoding, and the equivalent polynomial-reconstruction problem.  Theorem 1
proves NP-hardness for dimension `K=N/2-d+1` and radius `(N-K)-d`, with
`d=O(log N/log log N)` for polynomial-time reductions (and `d=O(log N)` for
quasipolynomial reductions).  The same Introduction also states the easy
regimes: unique decoding through `(N-K)/2` errors via the classical
Peterson/Berlekamp--Welch route, and list decoding through the Johnson radius
via Sudan and Guruswami--Sudan.

The prior-triage proposal--sample a codeword and corrupt it--does not inherit
Theorem 1's worst-case hardness.  No distributional theorem in the paper makes
that planted distribution Track A hard.  The retained generator instead makes
an explicit Track B claim and stays inside the unique-decoding radius.

## The retained family

The module inverse-generates a polynomial `p(X)=X*q(X^9)` over `GF(1009)`,
evaluates it on complete order-nine multiplicative orbits, and replaces four
of nine symbols in every orbit by field-uniform decoys.  Generation samples the
certificate first and never decodes the generated word.  The answer is the
ordinary dense Reed--Solomon polynomial coefficient vector, not a graph or a
finite-field surrogate for another domain.  Verification performs exact
finite-field evaluation and a Hamming-distance count without reading
`inst["answer"]`.

Thus G and V pass.  Track A is unavailable because the generated instances are
inside a known polynomial-time decoding regime.  Track B initially appeared
viable:

| route | measured medium-preset cost |
|---|---:|
| Berlekamp--Welch error-locator solve | at most 15,134,479 counted `GF(1009)` operations; 0.553 s mean over 8 seeds |
| compact ninth-root orbit route | 108 exact field operations |

The mechanical and compact costs are therefore **not comparable** and the
existence of Berlekamp--Welch is not the rejection reason.  The reference
algorithm solved 8/8 as Track B requires.  Four non-reference attacks
(per-symbol outlier, input-order greedy interpolation, 256 random interpolation
restarts, and a by-hand low-degree ansatz) each solved 0/8.

## Failing gate

At the medium preset (`N=288`, `K=20`, radius `128`), all local gates except
G9(b) passed.  The answer is at most 66 serialized characters, 20 atomic
elements, and 17 estimated tokens; the intended route is 108 operations.
Random candidates hit 0/200,000 from the exact 200-bit coefficient language.

The oracle evidence is:

| arm | solved/attempts | result |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | **3/3** | fails G9(b) |
| placebo hint | 0/3 | hardened |

The structural hint was one sentence naming only the invariant:

> Multiplication by 759 forms nine-point evaluation orbits on which the clean
> ratios y/x are constant.

It contains no chained procedure and no recovered coefficient.  Claude Sonnet
5, Grok 4.6, and Gemini 3.1 Pro each returned a polynomial that the exact
checker accepted.  By contrast, the placebo arm changed prompt length and
register but solved 0/3, so hinted-minus-placebo is `1.0`.

The first G9(b) run at `easy` was also broken by Gemini.  Following the stated
protocol, the family was moved exactly one rung to `medium`, and both the bare
and hinted arms were rerun there.  Because the hint broke `medium` as well, no
further escalation or redesign was attempted.

## Preserved evidence

- `rejected_gen_1611_03069.py`: the complete deterministic generator and its
  self-test, retained as required.
- `selftest_report.json`: all measurements; `G9_no_tool_suitability.pass` and
  `all_passed` are honestly false.
- `llm_loop_transcript.jsonl` and `.meta.json`: the script-owned bare medium run.
- `g9_hinted_transcript.jsonl`: the three verified hinted solves at medium.
- `g9_placebo_transcript.jsonl`: the three failed placebo calls at medium.
- `g9_easy_hinted_transcript.jsonl`: the initial easy-level verified solve that
  triggered the one permitted move up the ladder.

Paper: Gandikota, Ghazi, and Grigorescu, [*NP-Hardness of Reed-Solomon
Decoding, and the Prouhet-Tarry-Escott Problem*](https://arxiv.org/abs/1611.03069),
especially the Introduction, Theorem 1, Definition 1 in the Preliminaries, and
the Moments Subset Sum to RS-BDD reduction in Section 3.
