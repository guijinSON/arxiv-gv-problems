# Stage 2 — confirmation and taxonomy pass — **UNVERIFIED RECONSTRUCTION**

> ## Read this before using or citing this file
>
> **This is not the prompt that built `papers/papers.jsonl`.** Like
> `triage/stage1_prompt.md`, the original stage-2 prompt was never committed and
> is not in the git history. This is a **good-faith reconstruction**.
>
> Stage 2 leaves more fingerprints in the data than stage 1 does — every record
> in `papers/papers.jsonl` carries stage 2's `family`, `method`,
> `candidate_generator` and `candidate_verifier` — so the *output contract*
> below is well constrained. The **instructions** that produced those outputs
> are not, and they are the part that matters for the bias question.
>
> **Consequences you must not lose:**
>
> - Any recall or coverage number measured against this file describes **this
>   file**, not the prompt that built the pool. It is not evidence for or
>   against the claim that triage caused the corpus's combinatorial bias.
> - The 30 family names and 13 method names quoted below are **real** — they are
>   measured from the data by `triage/build_taxonomy.py` and stored in
>   `triage/taxonomy.json`. The *instruction to grow the taxonomy*, and the
>   wording of every rule here, are reconstruction.
> - No date, author or model version is asserted beyond `README.md`'s record
>   that stage 2 ran `codex gpt-5.5` with a "growing two-level taxonomy".
>
> Everything between the `PROMPT-BEGIN` / `PROMPT-END` markers is the
> reconstruction proper; `triage/evaluate_triage.py` scores only that region.

<!-- PROMPT-BEGIN -->

You are the second and deeper pass of a two-stage screen for a dataset of
**generator–verifier problems**. Stage 1 has already kept this paper on an
abstract-level reading. Your job is to **confirm or reverse** that, and — when
you confirm — to say concretely *how* an instance of this paper would be
generated and checked, and to place the paper in a taxonomy.

You are shown the paper's title, abstract, arXiv categories, and stage 1's
verdict with its stated `object` and `check`. Treat stage 1's verdict as a
hypothesis to be tested, not as a finding. You may read further into the paper
if you can reach it.

## Confirm the three properties, concretely

- **G — generatable.** You can build an instance *and know its answer*, by
  sampling the answer first and constructing the problem around it.
- **H — hard.** No known polynomial-time or closed-form method, and the answer
  space is far too large to guess.
- **V — verifiable.** A candidate answer is checked cheaply and exactly:
  substitute, expand, recompute, compare.

The answer must be a **witness** — a structured object handed to a checker.
Never an absence, never an optimum whose optimality is the claim, never a real
number or an asymptotic rate.

Stage 1 was allowed to keep on a plausible-sounding phrase. You are not. For
each of G, H and V you must be able to write the concrete sentence below. If you
cannot write one of them, the paper does not survive this pass.

- **`candidate_generator`** — one sentence, in the paper's own objects, saying
  what is sampled first and how the instance is built around it.
  *e.g.* "plant a weighted zero-sum subsequence inside a longer modular sequence"
- **`candidate_verifier`** — one sentence naming the exact operation a checker
  performs.
  *e.g.* "check chosen terms and weights satisfy both modular zero-sum equations"

Write these in the objects the paper's own theorems use — vectors, matrices,
polynomials, coordinates, functions, group elements, trajectories. Do **not**
paraphrase the paper into a graph, a SAT instance or an integer program in order
to make the sentence easier to write. If the paper's object is continuous, say
what the *finite exact certificate* for it is; that certificate is the answer.

## Reverse stage 1 when

- The object stage 1 named turns out to be a real number, a rate, an absence, or
  a bare optimality claim.
- The paper's actual contribution is a classification, a survey, a complexity
  bound, or an existence theorem with no effective construction.
- The search is in P by an algorithm the paper itself gives, or gives a
  reference to.
- You cannot name the checking operation in a single clause.

A reversal is a good outcome and costs nothing. Say which of the four applies.

## Place it in the taxonomy

Assign two levels.

- **`family`** (level 1) — what kind of mathematical object the problem is
  about.
- **`method`** (level 2) — how the generator–verifier gap is realised.

Use an existing label when one fits. The taxonomy is **growing**: if no existing
label fits without distortion, coin a new one — short, lowercase, a plural noun
phrase for a family and a verb-ish noun phrase for a method — and say in
`taxonomy_note` why the existing labels did not fit. Do not force a paper into a
near-miss label; a forced label is worse than a new one, because it makes the
corpus look more uniform than it is.

Families in use so far:

> graph structures · designs and codes · algebraic decomposition · integer
> equations · reconfiguration · geometric configurations · constraint
> satisfaction · algebraic identity solutions · algebraic geometric structures ·
> schedules and allocations · words and permutations · finite field
> constructions · algebraic isomorphisms · cryptographic witnesses ·
> combinatorial games · topological structures · games and social choice · set
> system structures · additive combinatorial structures · finite algebraic
> structures · program and circuit synthesis · formal proofs · matroid
> structures · adversarial inputs · poset structures · number field
> constructions · polyhedral witnesses · fixed point solutions · quantum
> strategies · differential geometric structures

Methods in use so far:

> planted solution · structural scan · substitution check · inverse construction
> · sequence replay · ideal containment · invariant computation · trapdoor ·
> game tree check · black box evaluation · search from seed · collision search ·
> automata decision

## Grade the strength

- `strong` — the generator and verifier sentences are both concrete and you
  believe a builder could implement them from the paper.
- `weak` — one sentence is speculative, or the hard regime is unclear.

Upgrade a `weak` stage-1 grade to `strong` when your reading supports it; say so
in `reason`. Downgrade likewise.

## Output

One JSON object, nothing else.

```json
{"decision": "confirm", "strength": "strong",
 "family": "<level-1 label>", "method": "<level-2 label>",
 "candidate_generator": "<one sentence>",
 "candidate_verifier": "<one sentence>",
 "taxonomy_note": "<why a new label was coined, or null>",
 "reason": "<one sentence, <= 30 words>"}
```

`decision` is `confirm` or `reverse`. On `reverse`, set `family`, `method`,
`candidate_generator` and `candidate_verifier` to `null` and make `reason` name
which reversal condition applied.

<!-- PROMPT-END -->

---

## Reconstruction notes — *not part of the prompt*

### Evidence-backed (traceable to a committed artifact)

| element | traced to |
|---|---|
| the G / H / V wording and the witness rule | `prompts/codex_task.md`, verbatim |
| the four output fields `family`, `method`, `candidate_generator`, `candidate_verifier` | they are literally the columns of `papers/papers.jsonl` |
| the two-level taxonomy, and that it *grew* | `README.md`: "stage 2 (`codex gpt-5.5`, growing two-level taxonomy)". The long tail in `triage/taxonomy.json` corroborates growth: `differential geometric structures` has 1 paper, `fixed point solutions` and `quantum strategies` 3 each |
| the 30 family and 13 method labels quoted in the prompt | measured from `papers/papers.jsonl` by `triage/build_taxonomy.py`; counts in `triage/taxonomy.json` |
| that stage 2 could **upgrade** a stage-1 grade | the `agreement` field's `upgraded` value, on 2,238 of 12,167 records |
| that stage 2 could **reverse** stage 1 | the funnel: stage 1 kept 98,610, stage 2 confirmed 44,239 — 55% were reversed |
| the example generator/verifier sentences | copied from a real record, `2311.00090`, in `papers/papers.jsonl` |

### Guessed (no artifact constrains it)

- **The output schema** as JSON, and the key names `decision`, `strength`,
  `taxonomy_note`, `reason`. Only the four data fields above are attested;
  `taxonomy_note` in particular is my invention and is not stored anywhere.
- **The four explicit reversal conditions.** That reversals happened is
  measured; *why* is not recorded per-paper anywhere in the repo.
- **"Write these in the objects the paper's own theorems use"** and the
  instruction not to paraphrase into a graph/SAT/ILP. This is the most
  consequential guess in the file, and **it is probably an over-generous
  reconstruction** — see below.
- **The `strong` / `weak` definitions**, ordering, headings, tone.

### The most important caveat in this file

The paragraph telling stage 2 to stay in the paper's own objects, and the
sentence "if the paper's object is continuous, say what the finite exact
certificate for it is", are **almost certainly more than the original said**.

That instruction is a paraphrase of the "Build in the paper's own objects first"
section of `prompts/codex_task.md` — which was added in commit `331102c`,
*after* this pool was built. `MANIFEST.json` dates the sweep to 2026-08-27, and
the first committed version of the builder prompt (`cc08150`) contains no such
section, no `NATIVE` field and no certificate vocabulary at all.

I included it anyway because a reconstruction that produced `candidate_verifier`
sentences as varied as the real ones must have said *something* about staying
faithful to the paper. But a reviewer should treat this paragraph as the weakest
link in the file: if the original lacked it, then this reconstruction is
systematically kinder to continuous papers than the prompt that built the
corpus, and **any per-family recall measured here overstates the original's
coverage**. That direction of error is worth stating plainly, because it is the
direction that would let someone wrongly conclude the original triage was fine.
