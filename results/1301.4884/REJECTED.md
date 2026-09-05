# Rejection: arXiv:1301.4884

## Verdict

The attempted **Track B** family fails **H (no-tool compression hardness)**.  It
passes G and V: instances are inverse-generated from a sampled common Hopf
phase, and a submitted 6-by-4 rational matrix is checked by exact norm and
inner-product calculations without reading the planted answer.  However, the
official bare oracle loop solved **12/12** instances, including every attempt at
the largest setting permitted by the 300-operation no-tool cap.

Track A is not an alternative claim.  The paper proves geometric restrictions,
not computational hardness for this generated distribution, and the attempted
family has an explicit polynomial-time six-partite compatibility CSP.  Thus it
has no paper-backed Track A hardness theorem or hard parameter regime.

## Paper result and attempted family

The paper has no numbered sections or theorem environments, so the precise
source locations are equations and pages:

- Equation (1) defines the Hopf map and Equation (3) parametrizes each fibre.
- Figure 2 and the paragraph preceding it present the 24-cell as six fibres with
  four points on each.
- Equations (4)--(7) express kissing distances through relative fibre phases.
- The sentence immediately after Equation (7) says that adding the same
  constant to all phases preserves a kissing configuration.  This identity was
  the theorem-backed construction used by the generator.
- Pages 4--8 treat fixed antipodal cases and rely on Anstreicher's uniqueness
  result for the 24-point antipodal configuration; page 8 gives an explicit
  16-point construction.  None supplies an asymptotically hard search regime.

The retained generator sampled the common phase first, applied it to six exact
rational 24-cell fibre templates, and added decoy phases occurring on at most
five fibres.  The answer selected the one phase occurring on all six fibres.
This is native geometry: the checker expands each representative by the exact
quarter-turn map and checks all 276 pairwise kissing constraints.

## STEP 0 cost comparison

The efficient mechanical method is an exact orbit-compatibility table followed
by depth-first constraint propagation.  Its cost is `O(n^2)` table construction
and `O(n^6)` worst-case search because there are six candidate lists.  At the
shipping candidate (`n=16`, crowding 5), eight local runs solved 8/8 with median
cost **64,876 counted rational dot-product operations, 167 search nodes, and
0.0512 seconds**.

The compact route normalizes each row against its fixed 24-cell template and
intersects the six recovered phase sets.  It uses at most
`2 * 6 * n = 192` exact additions/sign changes at `n=16`, or **252** at the final
in-cap escalation `n=21`.  The next realizable size has 26 candidates per fibre
and needs 312 such operations, over G9(c)'s limit.

The roughly 338-fold mechanical/compact gap made Track B worth testing.  This
rejection is therefore **not** based merely on the existence of an efficient
algorithm or on claiming that the two costs are comparable.  It is based on the
measured fact that the compact invariant is too conspicuous: every oracle found
and executed it without a hint.

## Hardening evidence

| preset | parameters | solved |
|---|---|---:|
| easy | `n=6, crowding=1` | 3/3 |
| medium | `n=11, crowding=4` | 3/3 |
| hard | `n=16, crowding=5` | 3/3 |
| escalated | `n=21, crowding=5` | 3/3 |

Every returned witness parsed and verified with reason `ok`; this is not a
parser false negative.  `harden.py` returned `too_easy` because `escalate()` had
no further in-cap axis.  The script's configured pool for this run contained
OpenAI GPT-5.6 Terra and Google Gemini 3.8 Flash, as recorded in `.meta.json`.

## Retained artifacts

- `rejected_gen_1301_4884.py` is the complete attempted generator, retained as
  required after a built family is rejected.
- `selftest_report.json` records the passing local G/V gates, including
  0/200,000 random-guess hits and four attacks at 0/8 each.
- `llm_loop_transcript.jsonl` and `.meta.json` are the unmodified script-owned
  bare-run evidence for the rejection.
- The `g9_*` files are older provider-error diagnostics and are not evidence for
  this verdict; G9 arms were unnecessary once the bare family failed H.

