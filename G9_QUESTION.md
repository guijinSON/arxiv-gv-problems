# G9(b) may be inverted — a decision for the project owner, not a bug fix

**Every rejection whose family survived the oracle was rejected on G9(b).** Eight of
eight. These papers passed `G`, passed `V`, and defeated a four-vendor frontier pool
with no tools at their shipping preset — the exact condition the benchmark evaluates
under — and were then discarded.

| paper | preset held | escalations |
|---|---|---|
| 2103.00306 | hard | 2 |
| 1211.1490 | hard | 0 |
| 1806.09562 | easy | 0 |
| 2110.12933 | medium | 0 |
| 1306.6796 | easy | 0 |
| 2007.08967 | easy | 0 |
| 1904.00563 | easy | 0 |
| 1608.00931 | easy | 0 |

## What G9(b) says

> The family must still defeat the oracle pool **when it is given its one-sentence
> structural hint.**
>
> A family that survives bare but dissolves the moment you name the trick was never
> testing whether a model can *find* the structure — it was testing whether the model
> had already memorised it.

## Why that reasoning looks backwards

The inference in the second sentence does not follow. If a model had memorised the
trick, it would solve the **bare** statement too — and STEP 4 already proves it does
not. What "dissolves once you name the trick" actually demonstrates is that the
difficulty is **concentrated in finding the insight** rather than in executing it.

That is the property the benchmark is trying to select for. G9's own preamble says so:

> a model also fails a question whose answer is forty thousand tokens long, and one
> that needs ten thousand exact multiplications. Those failures say nothing about
> mathematical intuition, and a corpus full of them measures patience.

A family that stays hard *even when you hand over the insight* is hard for some reason
other than the insight — length, bookkeeping, arithmetic. G9(b) as written keeps
exactly those and deletes the insight-based ones. It selects for patience.

## Why G9(a) is right and G9(b) is the odd one out

G9(a) records bare / hinted / placebo and is explicitly **never gated**, with a good
reason given:

> gating on it would let a builder tune the hint instead of the family.

G9(b) gates on nearly the same signal and inherits exactly that problem. Measured over
the 17 modules on disk carrying a hint, 4 of 9 rejected papers handed the solver a
procedure rather than an invariant — the paper was discarded for the builder's
sentence. `submit.sh --reject` now blocks the clearest of those, but that is a patch on
the symptom: even a perfectly minimal hint fails G9(b) whenever the insight is the
whole difficulty.

## Options

1. **Drop G9(b) to a recorded diagnostic**, like G9(a). The hinted arm stays measured;
   it stops deleting families. Re-open the eight.
2. **Invert it**: require that the hint *does* help (hinted ≫ placebo), as positive
   evidence that the family tests insight rather than stamina. This is closer to G9's
   stated purpose than the current gate.
3. **Keep it**, on the view that a question whose insight can be stated in one sentence
   is too fragile to contamination — a model that has read the paper gets it free. This
   is a coherent position, but it is an argument about contamination, and it should be
   made explicitly rather than as a hardness gate.

**Not acted on.** Unlike `cap_bound` and `budget_bound`, this is not a harness bug with
an obviously correct fix — it is a judgement about what the benchmark is for. The eight
papers remain rejected pending that call. They are listed above so the decision is
cheap to execute either way.
