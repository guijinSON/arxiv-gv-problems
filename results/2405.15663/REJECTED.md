# Rejected: soft happy colourings and community structure

Paper: [Soft happy colourings and community structure of networks](https://arxiv.org/abs/2405.15663)

## Decision

This paper does not yield a family that clears **H** under either track.  **G** and
**V** are straightforward: sample a colouring before its graph, and verify a
candidate by exact same-colour-neighbour counts.  The obstacle is hardness, not
certification.

The prior-triage proposal—plant stochastic-block-model colour classes and ask for
a complete `rho`-happy colouring—cannot be Track A.  Section 2.2 explicitly
reviews polynomial-time spectral recovery for sufficiently separated SBMs, and
Section 4 gives polynomial heuristics, including Local Maximal Colouring in
`O(m)`.  Theorem 3.3 supplies an asymptotic *generation* guarantee below its
threshold; it does not give distributional hardness.  Moving toward
indistinguishable blocks also does not fix this: the expected same-colour fraction
approaches `1/k`, so a low enough `rho` admits many unrelated balanced colourings
and loses guess resistance.  The paper supplies no exact short invariant for a
sampled SBM realisation that is materially cheaper than doing the
clustering/counting work, so this proposal does not become a justified Track-B
compression task either.

## Track-B prototype and measured failure

The retained prototype uses the paper's exact Definition 2.1 in a different native
form.  It asks for the largest rational `rho` for a fixed colouring of succinct
Cayley components over `F_p`.  The generator composes exact quadratic-form level
counts, so the answer is known without solving the emitted instance, and the
checker independently recomputes and compares exact integers and rationals.

For the shipping prototype (`4` components over `F_11^6`):

| route | measured/derived cost |
|---|---:|
| mechanical translation-reduced vector scan | **56,690,744 modular operations**, mean **2.142 s** over 8 measured runs |
| compact change-of-variables/discriminant route | **129 exact arithmetic operations** |
| answer | 3 atoms, 32 characters |

Thus an efficient algorithm exists and is stated honestly; this is not a Track-A
claim.  There is a genuine mechanical/compact gap, so the prototype was tested as
Track B rather than rejected merely because an algorithm exists.  It nevertheless
fails the required LLM hardness loop: all completed calls through the first four
rungs solved exactly.

| rung | parameters | solved |
|---|---|---:|
| easy | `n=2, p=5, d=4, |T|=3` | 3/3 |
| medium | `n=3, p=7, d=6, |T|=3` | 3/3 |
| hard | `n=4, p=11, d=6, |T|=5` | 3/3 |
| escalated | `n=5, p=13, d=6, |T|=6` | 3/3 |
| escalated | `n=6, p=17, d=6, |T|=7` | 1/1 completed call solved |

The replies explicitly used finite-field quadratic level counts and returned
certificates accepted by `verify`; these are genuine solves, not parse failures.
The last rung could not finish because OpenRouter returned HTTP 403 "Key limit
exceeded" on every redraw.  That external error is not counted as an oracle
failure and no `hardened` verdict is claimed.  The partial script-owned evidence is
kept in `llm_loop_transcript.jsonl` and `.meta.json`.

Increasing the modulus and the number of components enlarged the mechanical scan
without concealing the compact formula; the successful `p=17` call confirms that
the solver cost remained the short route.  The candidate therefore fails Track B
H (and already fails the bare STEP 4 condition), so G9(b) was not run.

## Why the remaining paper routes do not repair H

- The Introduction recalls worst-case NP-hardness of MHV/MHE for more than two
  colours, but that is not a theorem about the generated SBM distribution.
- Asking for an exact SoftMHV optimum would need a construction-carried optimality
  witness.  The paper offers heuristics, not a primal-dual or bounded refutation
  certificate; computing the optimum first would violate G.
- Planting an all-happy optimum supplies the value `|V|`, but then the requested
  witness is just the planted community recovery problem already ruled out above.
- Asking only to evaluate a displayed colouring is exactly what the retained
  Track-B prototype does, and the oracle evidence shows its compact route is too
  accessible.

The decisive paper locations are Definition 2.1 (exact happiness condition),
Section 2.2 (SBM and spectral easy regime), Theorem 3.3 (asymptotic planted
happiness), and Algorithms 4.1–4.4 (polynomial heuristic routes and their stated
complexities).
