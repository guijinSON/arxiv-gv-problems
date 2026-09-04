# Rejected: arXiv 1806.09562

This build fails **G9(b) on Track B**.  It does not fail generation or exact
verification, and it is not being rejected merely because an efficient algorithm
exists.

## Family tested

The retained module `rejected_gen_1806_09562.py` implements the paper's native
maximal-empty-square object from Section 3.  The instance gives a rational point set
and the distinguished lower-left anchor `(0,0)`.  A witness is an exact rational side
length and a named point on the top or right edge; the verifier expands the point set,
checks that no point lies in the open square, and checks that the named point blocks
every strict enlargement.  Generation samples the unique blocking batch and index
first and raises every other batch minimum by a positive offset.

The paper's Theorem 2 computes the full reach in `O(n log n)`.  For one named anchor,
the corresponding direct closest-blocker scan is `O(n)`.  Theorem 3's NP-hardness is
for maximum-area packings in the integer-coordinate Planar-Monotone-3SAT gadget
regime; it does **not** establish hardness for this inverse-generated distribution.
That is why this build was evaluated honestly as Track B rather than Track A.

## Mechanical cost versus compact route

At the final tested preset (`n=2,400,008`, eight batches), the direct exact scan costs
**21,600,072 integer operations** and averaged **0.666 seconds** over eight seeds on
this machine.  It solved 8/8 instances, as expected.  The certificate space has one
valid blocker among 2,400,008 structure-aware candidates.

The compact route uses at most **240 exact operations**.  Within a batch,

`X-Y = 2R(Pj+Q) - R^2 - K`,

so only the few integer indices next to its affine sign change need inspection.  The
eight local minima are then compared.  Thus there is a real compression gap (about
90,000 mechanical operations per compact operation); the family is not rejected for
lacking a shortcut.

## Failed gate and evidence

The first shipping candidate (`n=1,200,008`) hardened bare but was solved when given
the structural hint.  Following G9(b), the ladder was moved upward exactly once and
both arms were rerun at `n=2,400,008`.

The replacement bare run hardened **0/3 solved**.  In the replacement structural-hint
run, Gemini returned an invalid boundary fraction, one Grok call timed out and was
redrawn (so it did not count), Claude returned no answer within its reasoning budget,
and GPT-5.6 Terra returned a witness that verified exactly.  The counted result was
therefore **1/3 solved**, so G9(b) fails again after the single permitted escalation.

The hint was: "The difference between the two squared coordinate numerators is affine
in the point index within every batch."  This names one invariant only.  It gives no
crossing formula, batch, index, rational value, derived count, or follow-on step.  The
successful oracle therefore shows that naming the intended structure dissolves the
task, which is precisely G9(b)'s rejection condition.

Evidence is preserved in `llm_loop_transcript.jsonl` (replacement bare run),
`g9_hinted_transcript.jsonl` (replacement hinted run), their metadata, and the
retained rejected module.  The placebo arm was not run because the instructions say
to stop when the hinted arm breaks the family a second time; it cannot change the
gated G9(b) result.
