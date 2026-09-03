# `triage/` — the paper-selection stage, and how to test it

`papers/papers.jsonl` did not come from arXiv directly. It is the survivor of a
two-stage LLM screen over 348,102 tier-A arXiv math papers. That screen decides
what the whole project can ever build, and until now **it was the only stage of
the pipeline with no prompt in the repo** — which made the claim *"the triage
prompt caused the combinatorial collapse"* impossible to test, argue against, or
reproduce.

This directory makes it testable. It does **not** settle it.

### Unverified citations in the gold set

40 of the 60 gold entries cite a real arXiv id; 20 are explicitly constructed
exemplars. **13 of the 40 citations have been verified against live arXiv** — an independent
check resolved 13 ids, prioritising all 7 whose ids look future-dated, and 13/13
titles matched character-for-character. The remaining 27 are unverified; only 4 of
the 40 appear in `papers/papers.jsonl`, which is expected since that file is a
filtered subset. Before the gold set is used to *fail* a triage prompt in anger,
resolve the remaining 27 and confirm each paper says what its entry claims.

### `keep` in the gold set is a triage verdict, not a shipping verdict

24 of the 48 `keep` entries are in families whose certificate is produced by a
known algorithm — SOS by an SDP, Farkas and primal-dual by an LP, Lyapunov by a
linear solve, algebraic numbers by root isolation. That is deliberate and it is
not a contradiction with `prompts/codex_task.md`: triage decides whether a paper is
*worth a builder's read*, and the builder then decides Track A, Track B, or reject.
Those families fail **H on Track A** and are exactly the population Track B exists
to admit. A triage prompt that drops them is failing, which is what this gold set
is built to detect.

## Read this first

**The original stage-1 and stage-2 prompts were never committed and are not in
the git history.** `triage/stage1_prompt.md` and `triage/stage2_prompt.md` are
**unverified reconstructions** written from the surviving artifacts — the G/H/V
criteria in `prompts/codex_task.md`, the field names in `papers/papers.jsonl`,
and the stage counts in `README.md` / `MANIFEST.json`. Each file carries a
warning box and an itemised split of what is evidence-backed versus guessed.

Any number measured against those files describes **those files**. A good score
does not exonerate the prompt that built the pool, and a bad score does not
convict it. What this directory buys is that *from here on* a change to triage
can be scored before it is run over 348k papers.

The one file here that is **measured rather than reconstructed** is
`taxonomy.json`, regenerated from the committed pool by `build_taxonomy.py`.

## The pipeline

```
348,102 tier-A arXiv math papers
      |
      |  STAGE 1  screening pass  (README.md records: solar-pro4)
      |  reads title + abstract + categories only.  Cheap, high-recall.
      |  emits keep/drop + a strength grade.
      v
 98,610 kept  (28.3%)
      |
      |  STAGE 2  confirmation + taxonomy pass  (README.md records: codex gpt-5.5,
      |  "growing two-level taxonomy").  Confirms or reverses stage 1, writes the
      |  concrete generator and verifier sentences, assigns family + method,
      |  and may upgrade a weak stage-1 grade.
      v
 44,239 confirmed  ->  12,167 labelled `strong`  =  papers/papers.jsonl
                       9,929 both_strong + 2,238 upgraded
```

Stage 2's output is exactly the columns of `papers/papers.jsonl`: `family`,
`method`, `candidate_generator`, `candidate_verifier` (plus `agreement`). Note
that `papers.jsonl` carries **no abstract** — the abstract that both stages read
was not retained, which is itself a reproducibility gap (see *Open items*). It
means every probe in `taxonomy.json` searches triage's own output text and
nothing else.

> A `hardness_evidence` column (`{class, signal, confidence, ...}`, derived from
> arXiv categories) was added to `papers.jsonl` by separate concurrent work while
> this directory was being written. `build_taxonomy.py` does not read it, and
> `taxonomy.json` was regenerated after it landed. `build_taxonomy.py --check`
> reports a schema change like that one as stale.

## What is in here

| file | status | what it is |
|---|---|---|
| `stage1_prompt.md` | **UNVERIFIED RECONSTRUCTION** | screening pass, keep/drop + strength |
| `stage2_prompt.md` | **UNVERIFIED RECONSTRUCTION** | confirmation pass, taxonomy + generator/verifier sentences |
| `certificate_families.md` | **PROPOSED, never used** | an addendum naming the certificate forms the pool lacks; written now, not history |
| `taxonomy.json` | **MEASURED** | families, methods, categories and certificate vocabulary counted from `papers/papers.jsonl` |
| `build_taxonomy.py` | tool | regenerates `taxonomy.json`; `--check` fails if it is stale |
| `gold_coverage_set.jsonl` | hand-built | 60 labelled entries over 12 certificate families + negative controls |
| `evaluate_triage.py` | tool | scores a prompt, **per certificate family**; `--self-test` runs offline |

## What `taxonomy.json` measures

Two levels, as stage 2 emitted them: 30 families and 13 methods over 12,167
papers. The distribution is the problem in one table — `graph structures` alone
is 45.7% of the pool, and the six largest families are 74%.

The part that matters for coverage is `certificate_vocabulary`: how often each
certificate form appears anywhere in triage's own free text (title + family +
method + generator + verifier sentences).

| certificate form | papers | | certificate form | papers |
|---|---:|---|---|---:|
| rational SOS | 41 | | algebraic number (min poly + interval) | 3 |
| Gram matrix | 16 | | Lyapunov / barrier | **0** |
| exact geometric coordinates | 16 | | symbolic identity / antiderivative | **0** |
| Nullstellensatz | 7 | | telescoping / Gosper / Zeilberger | **0** |
| Positivstellensatz | 3 | | certified residual / interval | **0** |
| Farkas / LP duality | 1 | | primal-dual optimality | **0** |

Out of 12,167 papers. **This is a measurement of triage's output vocabulary, not
of arXiv.** A zero means the sweep never once wrote the word — it does not prove
no such paper is in the 348k pool. Distinguishing those two requires re-running a
screen over the pool, which is what the harness below is for.

## The gold coverage set

`gold_coverage_set.jsonl` — 60 entries, one JSON object per line.

- **48 `keep` entries**, exactly 4 in each of 12 `certificate_family` values:
  `rational_sos`, `positivstellensatz`, `nullstellensatz`, `farkas_lp_duality`,
  `gram_matrix`, `algebraic_number`, `lyapunov_barrier`,
  `primal_dual_optimality`, `symbolic_identity`,
  `telescoping_gosper_zeilberger`, `exact_geometric_coordinates`,
  `certified_residual_interval`.
- **12 `drop` entries** under `certificate_family: negative_control`.
- **40 real arXiv papers** (`source: "arxiv:<id>"`, `is_real_paper: true`) and
  **20 constructed exemplars** (`source: "constructed"`, `is_real_paper: false`,
  title prefixed `[CONSTRUCTED]`).

Fields: `id`, `certificate_family`, `expected_label`, `source`, `is_real_paper`,
`title`, `categories`, `blurb`, `why_it_qualifies`, `certificate_object`,
`verification`, `cue_terms`, `notes`.

### Provenance rules this file follows

- **No arXiv id or title is invented.** Every id and title was read back from
  the arXiv API (`export.arxiv.org/api/query`) on 2026-09-04 and matched
  character-for-character against what is stored here.
- **`blurb` is a paraphrase**, written for this gold set. It is not the paper's
  abstract, and it is not a quotation.
- **`why_it_qualifies` is judged from title and abstract only.** No full paper
  was read. It is a triage-level judgement, exactly like the labels it scores —
  so a reviewer who reads one of these papers may reasonably disagree with a
  label. That is a bug report, not a surprise.
- **Constructed entries are not disguised as papers.** They carry no id, and
  their titles are task descriptions.

### What `expected_label` means

`keep` = *a screen reading only title, abstract and categories should pass this
to the next stage*. It is **not** a claim that the family would ship. Hardness
is the builder's gate, not triage's — `README.md` already says triage is not
ground truth.

This matters for one entry in particular: `gold-032` (a min-cost-flow dual
certificate) is labelled `keep` although min-cost flow is in P and a builder
would almost certainly reject it at gate H. It is a keep because the
**certificate shape** is right and screening on shape is triage's job. If your
reading of triage is different — that stage 1 should reject on suspected
tractability — then this entry is mislabelled for you, and you should flip it
and say so.

### The negative controls are deliberately on-topic

Ten of the twelve negatives share `cue_terms` with a keep family: a creative
telescoping survey, a telescoping non-existence result, three Positivstellensatz
papers whose contribution is a rate or an abstract existence theorem, a
deep-learning-for-symbolic-integration paper, a numerical optimal-transport
method, a definite integral wanted as a number, a request for a Lyapunov
exponent as a number, and an emptiness question with no certificate requested.
The remaining two are off-topic on purpose (a combinatorial non-existence proof
and a classification request), so the negatives are not all analysis papers --
otherwise a combinatorially-biased screen would score well on specificity for
entirely the wrong reason. A screen that keeps papers by keyword will keep all of them. That is
the point: without on-topic negatives, "improve coverage" degenerates into
"match more words".

## Running an eval

### 1. Test the harness (offline, no API, no network)

```bash
python3 triage/evaluate_triage.py --self-test
```

Five stub classifiers with known failure modes, each asserted against a required
exit code, plus a schema and coverage check on the gold set. This tests the
**harness**, not any prompt. Exit 0 means the harness itself is sound.

### 2. Score a prompt with a real model

```bash
python3 triage/evaluate_triage.py \
    --prompt triage/stage1_prompt.md \
    --classifier cmd --cmd 'your-llm-cli --model <m>' \
    --json triage/eval_stage1.json
```

`--cmd` is invoked once per gold entry.

- **stdin**: `{"prompt": "<prompt body>", "entry": {...}}` — the entry with
  `expected_label`, `why_it_qualifies` and `notes` stripped out, so the
  classifier cannot read the answer.
- **stdout**: either the bare word `keep` / `drop`, or `{"label": "keep"}`.
- A non-zero exit, a timeout or unparseable output is recorded as an **error**,
  never as a `drop`. Scoring API failures as rejections is how a harness invents
  a collapse that is not there. Errors fail the run unless you pass
  `--allow-errors`.

Several prompt files can be given and are concatenated in order, so a base
prompt can be scored against base + addendum without editing either:

```bash
python3 triage/evaluate_triage.py \
    --prompt triage/stage1_prompt.md triage/certificate_families.md ...
```

Only the region between `<!-- PROMPT-BEGIN -->` and `<!-- PROMPT-END -->` is
scored, so a reconstruction's warning box does not leak into the measurement.

### 3. The offline `vocab` probe — and its hard limit

`--classifier vocab` (the default) needs no API. It keeps an entry iff one of
the entry's `cue_terms` occurs literally in the prompt body.

**It measures one thing: whether the prompt's own vocabulary can name the
family at all.** It is not a model, and it does not predict what a model does —
a model generalises past its prompt's wording, and a prompt containing a word is
no guarantee the model acts on it.

Read it in one direction only. *"This prompt cannot even name the family"* is a
real defect. *"This prompt names the family"* is worth nothing on its own.

### Exit codes

| code | meaning |
|---:|---|
| 0 | **PASS** — every family above `--min-family-recall` (0.50), aggregate and specificity bars met |
| 1 | **MASKED COLLAPSE** — aggregate accuracy and specificity look fine, but some family is at or below `--near-zero` (0.20). This is the failure this harness exists for. |
| 2 | **FAIL** — ordinary: aggregate below `--min-overall` (0.70), or specificity below `--min-specificity` (0.50), or a family below the family bar without the masking condition |
| 3 | usage or data error |

Exit 1 is separate from exit 2 on purpose. The corpus's real failure was not
"triage scored badly" — it was "triage scored fine and three certificate
families were at zero", and a single aggregate number cannot represent that. The
report prints the aggregate under a heading saying it is deliberately not the
headline, and prints per-family recall under one saying it is.

## Measured so far

Everything below was run in this repo on 2026-09-04.

**Harness self-test** — `python3 triage/evaluate_triage.py --self-test` → exit 0.

| stub | overall acc. | specificity | families at zero | required exit | got |
|---|---:|---:|---:|---:|---:|
| `oracle` | 1.000 | 1.000 | 0 | 0 PASS | 0 |
| `analysis_blind` | 0.800 | 1.000 | 3 | 1 MASKED | 1 |
| `combinatorial_prior` | 0.467 | 1.000 | 8 | 2 FAIL | 2 |
| `accept_all` | 0.800 | 0.000 | 0 | 2 FAIL | 2 |
| `reject_all` | 0.200 | 1.000 | 12 | 2 FAIL | 2 |

`analysis_blind` is the load-bearing row: 0.800 accuracy and perfect specificity
while three families sit at zero. Aggregate-only scoring calls that a pass.

`accept_all` is the second: per-family recall is a perfect 1.00 in every family
and accuracy is still 0.800, and only the specificity bar catches it. A coverage
metric with no negative controls can be gamed by a yes-machine.

**Vocabulary probe on the reconstructions** — `--classifier vocab`:

| prompt | overall acc. | specificity | macro family recall | families at 0.00 | exit |
|---|---:|---:|---:|---:|---:|
| `stage1_prompt.md` | 0.183 | 0.917 | 0.000 | 12 of 12 | 2 |
| `stage2_prompt.md` | 0.183 | 0.917 | 0.000 | 12 of 12 | 2 |
| `stage1_prompt.md` + `certificate_families.md` | 0.817 | 0.083 | 1.000 | 0 of 12 | 2 |

Both reconstructions name zero of the twelve certificate forms, so the probe's
recall is zero everywhere. Adding the proposed addendum takes macro recall to
1.000 — **and collapses specificity from 0.917 to 0.083**, because the addendum's
vocabulary matches the on-topic negative controls just as well as the keeps.

The honest reading of that row is not "the addendum works". It is: naming the
families is necessary for them to be reachable and nowhere near sufficient for
them to be screened correctly. Whether a model can do better than the vocabulary
it is handed is an open question, and `--classifier cmd` is how to answer it.

The addendum also earned its first bug from this probe: the `primal-dual` row
originally used an en dash, and the probe correctly reported that family
unreachable at 0.00 while the other eleven went to 1.00.

## What would actually be evidence about the bias claim

Nothing here settles whether the original triage prompt caused the collapse. The
original is gone. What *would* be evidence, in rough order of cost:

1. **Run a real classifier over this gold set** with each reconstruction
   (`--classifier cmd`). This measures the reconstructions, not history, but it
   turns "prompts steer selection" from a story into a number.
2. **Re-screen a random sample of the 348k tier-A pool** with a
   certificate-aware prompt and count how many papers a certificate-blind
   prompt would have dropped. This is the only way to separate *"the pool has no
   such papers"* from *"triage never looked for them"* — and it is the question
   `taxonomy.json`'s zeros cannot answer.
3. **Retain the abstracts** on the next sweep, so a future dispute about what a
   screen saw is answerable at all.

## Open items and caveats

- **The reconstructions may be too kind.** `stage2_prompt.md` contains a
  paragraph about staying in the paper's own objects, paraphrased from a section
  of `prompts/codex_task.md` that was added *after* this pool was built. If the
  original lacked it, every number measured here overstates the original's
  coverage. That is the direction of error that could lead someone to wrongly
  conclude the original triage was fine. It is called out in that file too.
- **The gold set's labels are triage-level judgements** made from titles and
  abstracts by one author in one sitting. No second annotator, so there is no
  inter-annotator agreement number. Disagreement on individual entries is
  expected and should be recorded by editing the entry, not by tuning thresholds.
- **Four keeps per family is coarse.** Recall can only take the values 0, 0.25,
  0.5, 0.75, 1.0, so a family's number moves in 25-point jumps. It is enough to
  distinguish zero from non-zero, which is the failure being hunted; it is not
  enough for fine comparisons between prompts.
- **The 12 families are the ones the pool lacks, by construction.** This gold
  set is a *coverage* instrument. It deliberately contains no combinatorics, so
  a prompt scoring well here has not been shown to still work on graph papers —
  which are 45.7% of the real workload. A companion set holding the existing
  strengths would be needed before shipping any prompt change.
- **`taxonomy.json`'s `core_hint_distribution` is a weak heuristic**: regexes
  over one sentence, with overlapping categories whose shares do not sum to 1.
  `scripts/corpus_report.py` is the real instrument — it imports each shipped
  module and inspects the instance the solver is actually handed. Do not quote
  `core_hint` where a `corpus_report` number exists.
- **Nothing here has been run against a model.** No API call was made by
  anything in this directory.
