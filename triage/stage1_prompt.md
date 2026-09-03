# Stage 1 — screening pass — **UNVERIFIED RECONSTRUCTION**

> ## Read this before using or citing this file
>
> **This is not the prompt that built `papers/papers.jsonl`.** The original
> stage-1 prompt was never committed to this repository, and no copy of it was
> found in the git history (`git log --all --diff-filter=A` returns nothing
> matching `triage`, `stage1`, `screen`). It is not recoverable from what is here.
>
> This file is a **good-faith reconstruction**, written from the only artifacts
> that survive: the G/H/V criteria and witness rules in `prompts/codex_task.md`,
> the field names present in `papers/papers.jsonl`, and the stage counts quoted
> in `README.md` and `MANIFEST.json`. It is what a stage-1 screen *consistent
> with those artifacts* would plausibly have looked like.
>
> **Consequences you must not lose:**
>
> - Any recall or coverage number measured against this file describes **this
>   file**. It says nothing about the prompt that actually produced the 12,167
>   papers, and it is **not evidence** for or against the claim that the triage
>   prompt caused the corpus's combinatorial bias.
> - A good score here is **not** exoneration of the original. A bad score here is
>   **not** proof of the original's guilt. This file exists so the claim becomes
>   *testable going forward*, not so it can be settled retroactively.
> - No date, author, model version or provenance is asserted for this text
>   beyond what is stated in this box. `README.md` records that stage 1 ran
>   `solar-pro4`; nothing in the repo records the prompt it ran.
>
> What is **evidence-backed** vs **guessed** is itemised under
> "Reconstruction notes" at the bottom of this file.
>
> Everything between the `PROMPT-BEGIN` / `PROMPT-END` markers is the
> reconstruction proper. `triage/evaluate_triage.py` scores only that region, so
> this warning box does not contaminate a vocabulary measurement.

<!-- PROMPT-BEGIN -->

You are screening arXiv mathematics papers for a dataset of **generator–verifier
problems**: code that emits an unlimited stream of `(question, answer, grader)`
triples derived from one paper.

You will be shown one paper's **title, abstract and arXiv categories**. You will
not see the full text. Decide, cheaply, whether this paper is worth a deeper
second pass. You are a *screen*, not a judge: the second pass and the builder
that follows it both have the power to reject. Your job is to be **cheap and
high-recall**, not precise.

## The test

A paper qualifies when its subject matter has all three properties:

- **G — generatable.** You can build an instance *and know its answer*, by
  sampling the answer first and constructing the problem around it.
- **H — hard.** No known polynomial-time or closed-form method, and the answer
  space is far too large to guess.
- **V — verifiable.** A candidate answer is checked cheaply and exactly:
  substitute, expand, recompute, compare.

The answer must be a **witness** — a structured object handed to a checker.
Never an absence ("no solution exists"), never an optimum whose optimality is
the claim, never a real number or an asymptotic rate.

## Judge the object, not the wording

Ask, in this order:

1. **What object would the solver be asked to produce?** Name it concretely: a
   subset, a matrix, a polynomial, a tuple of coordinates, a function, a
   sequence of moves, a certificate.
2. **Could that object be sampled first and the problem built around it?**
   (That is G. If the only way to get an instance is to solve one, drop.)
3. **How would a checker confirm it?** Name the operation: substitute into an
   equation, expand and compare, recompute a count, evaluate signs, multiply
   out. If you cannot name it in one clause, V is doubtful.

If all three answers come easily, keep. If one of them is clearly impossible,
drop. **If you are unsure, keep** — the second pass is cheaper than a missed
paper.

## Drop these

- The answer would be a **real number**, a numerical value, or a bound stated
  asymptotically.
- The answer would be **an absence**: a non-existence or impossibility result,
  where the thing to produce is the proof that nothing exists.
- The answer's whole content is that it is **optimal**, with no accompanying
  object that certifies the optimality.
- The paper's contribution **is a complete classification**, so any instance's
  answer is a table lookup.
- The witness would be a **proof**, or an object of unbounded length.
- The paper is a **survey, tutorial, historical account or software
  announcement** — no new problem family, no hardness regime.
- The paper is **not mathematics being done**: a benchmark study, an empirical
  machine-learning evaluation, a position paper.
- Verification would need **research-level machinery** rather than a short
  program.

## Grade the strength

Alongside the decision, grade how confident you are that a family survives a
deeper look:

- `strong` — you can already name the object, the sampling story and the
  checking operation, and none of them look strained.
- `weak` — one of the three is doubtful or you had to reach for it, but the
  paper is not clearly disqualified.

Grade `weak` rather than dropping whenever you are unsure. The second pass can
upgrade a `weak` paper; it cannot see a paper you dropped.

## Output

One JSON object, nothing else — no prose before or after, no code fence.

```json
{"decision": "keep", "strength": "strong",
 "object": "<the thing the solver would produce, <= 12 words>",
 "check": "<the operation that verifies it, <= 12 words>",
 "reason": "<one sentence, <= 30 words>"}
```

`decision` is `keep` or `drop`. `strength` is `strong` or `weak`. On `drop`, set
`object` and `check` to `null` and make `reason` name the disqualifier.

<!-- PROMPT-END -->

---

## Reconstruction notes — *not part of the prompt*

### Evidence-backed (traceable to a committed artifact)

| element | traced to |
|---|---|
| the G / H / V wording | `prompts/codex_task.md`, quoted verbatim; unchanged since the first commit `cc08150` |
| the witness rule ("never an absence / an optimum / a real number / a rate") | `prompts/codex_task.md`, verbatim |
| the disqualifier list | `prompts/codex_task.md` STEP 0, "Common disqualifiers" |
| that stage 1 read only abstract-level metadata | `README.md`: `candidate_generator` / `candidate_verifier` are "hypotheses from an **abstract-level pass**" |
| that stage 1 emitted a **strength** grade, not only keep/drop | `papers/papers.jsonl` has an `agreement` field with values `both_strong` (9,929) and `upgraded` (2,238). "Both" and "upgraded" are only meaningful if stage 1 also graded strength |
| that the screen was tuned for recall over precision | the funnel in `README.md` / `MANIFEST.json`: 348,102 → 98,610 kept at stage 1 (28.3%), of which stage 2 confirmed 44,239 (44.9% of those kept) |

### Guessed (no artifact constrains it — a reviewer should treat these as mine)

- **The output schema.** JSON with these key names is invention. Only `strength`
  is inferred from the data; `object`, `check` and `reason` are not recorded
  anywhere in `papers.jsonl`, so if the original emitted them they were
  discarded, and if it did not, this reconstruction is richer than the original.
- **The three ordered questions** ("what object / could it be sampled / how is
  it checked"). This is my rendering of G/H/V as a procedure. The original may
  have asked for a holistic judgement instead.
- **"If you are unsure, keep."** Consistent with the 28.3% keep rate and with
  stage 2 being allowed to upgrade, but not attested.
- **The survey / not-mathematics exclusions.** Reasonable for any screen, and
  the pool contains few obvious surveys, but no artifact records them.
- **Tone, ordering, section headings, length.** Entirely mine.

### The bias question this file exists to make testable

The reason this file was written is the claim *"the triage prompt caused the
combinatorial collapse."* Note what the reconstruction above does **not**
contain: it never names a single certificate form. No sum of squares, no Gram
matrix, no Nullstellensatz, no Lyapunov function, no antiderivative, no
telescoping certificate, no isolating interval, no interval arithmetic. It asks
"what object would the solver produce?" and leaves the model to supply its own
vocabulary of answers.

That is deliberate: those terms entered `prompts/codex_task.md` only in commits
`331102c` and `3ac35cd`, both of which post-date the pool
(`MANIFEST.json` records the sweep as generated 2026-08-27, and the first
committed `codex_task.md`, `cc08150`, contains none of that vocabulary — checked
with `git show cc08150:prompts/codex_task.md`). Importing it into a
reconstruction of the *earlier* prompt would be anachronistic, and would produce
a flattering score that means nothing.

So the experiment this enables is a **comparison, not a verdict**: score this
file, then score a variant that names the certificate families, and see whether
per-family recall moves. See `triage/README.md`, "Running an eval". A difference
is evidence about *prompt vocabulary as a mechanism*. It is still not evidence
about the original prompt, which is gone.
