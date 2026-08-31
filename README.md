# arXiv Generator–Verifier Problems

A distributed effort to turn **math papers with a generator–verifier gap** into
**working problem generators** — code that emits an unlimited stream of
`(question, answer, grader)` triples.

A paper qualifies when its subject matter has all three properties:

- **G — generatable.** You can build an instance *and know its answer*, by sampling the
  answer first and constructing the problem around it.
- **H — hard.** No known polynomial-time or closed-form method, and the answer space is
  far too large to guess.
- **V — verifiable.** A candidate answer is checked cheaply and exactly.

The answer must be a **witness** — a structured object you hand to a checker. Never an
absence, never an optimum whose optimality is the claim, never a real number.

Contributors, each running **Codex**, claim **one paper at a time** and let it read the
full paper, write the module, and prove the instance defeats a strong LLM.

## Dataset

| | |
|---|---|
| Papers | **12,167** |
| Both stages agreed `strong` | 9,929 |
| Upgraded by stage 2 | 2,238 |
| Families | 30 |
| Methods | 13 |

Source: a two-stage sweep of **348,102** tier-A arXiv math papers. Stage 1
(`solar-pro4`) kept 98,610; stage 2 (`codex gpt-5.5`, growing two-level taxonomy)
confirmed 44,239, of which these 12,167 are labelled `strong`. See `MANIFEST.json`.

### Top families
| family | papers |
|---|---:|
| graph structures | 5,559 |
| designs and codes | 1,022 |
| algebraic decomposition | 804 |
| integer equations | 607 |
| reconfiguration | 551 |
| geometric configurations | 533 |
| constraint satisfaction | 508 |
| algebraic identity solutions | 398 |
| algebraic geometric structures | 299 |
| schedules and allocations | 259 |

### Methods — how the gap is realised
| method | papers |
|---|---:|
| planted solution | 4,901 |
| structural scan | 3,390 |
| substitution check | 1,480 |
| inverse construction | 1,068 |
| sequence replay | 816 |
| ideal containment | 171 |
| invariant computation | 112 |
| trapdoor | 105 |

## Contribute (5 minutes to start)

1. Get **push access** and clone:
   ```bash
   git clone https://github.com/guijinSON/arxiv-gv-problems.git
   cd arxiv-gv-problems
   git config user.name "Your Name" && git config user.email "you@example.com"
   ```
2. Make sure `codex` is logged in — it should run **`gpt-5.6-sol`** at **`xhigh`**
   reasoning effort (the defaults in `scripts/run_codex.sh`) — then:
   ```bash
   export OPENAI_API_KEY=sk-...          # for the hardening loop
   bash scripts/claim.sh                 # reserves the next free paper
   bash scripts/run_codex.sh <arxiv_id>  # ~18 min, ~300k tokens
   bash scripts/submit.sh <arxiv_id>     # interface check, emit artifacts, push
   ```
   Rejecting a paper is a valid outcome — write `results/<id>/REJECTED.md` saying which
   gate failed, then `bash scripts/submit.sh <id> --reject`.

   Track progress in **[STATUS.md](STATUS.md)** or with `bash scripts/status.sh --sync`.
   Read **`CODEX.md`** first — the sandbox needs configuring and it is the most common
   thing that goes wrong.

Or open **Claude Code** in the repo and say **"do a paper"**; it follows `CLAUDE.md`.

## What a result looks like

`results/<arxiv_id>/gen_<arxiv_id>.py` exposes:

```python
DIFFICULTY, SHIPPING_DIFFICULTY
make_instance(n, seed, **params) -> dict     # contains "answer"; inverse generation
render(inst)              -> str             # self-contained statement + <answer> contract
parse_answer(text)        -> answer | None   # tolerant of prose and fences
verify(inst, answer)      -> (bool, reason)  # never reads inst["answer"]
random_candidate(inst,rng)-> answer          # for empirical P(guess)
search_space(inst)        -> int | None
enumerate_all(inst)       -> int | None
canonical_key(inst)       -> str             # equal iff same problem up to relabelling
escalate(params)          -> params | None   # strictly harder, or None if it cannot be
selftest()                -> dict            # all gates, with numbers
```

Gates a module must pass: planted verifies · corruption rejected · parse round-trips ·
**P(random guess) < 1e-6** · solutions sparse · survives an adversary panel · scales with `n`
· **and a four-vendor oracle pool at medium reasoning effort all fail to solve it**.

| role | model | effort |
|---|---|---|
| builder (Codex CLI, writes the module) | `gpt-5.6-sol` | `xhigh` |
| hardening oracle (the solvers we must defeat) | a four-vendor pool, redrawn per call | `medium` |

The pool lives in `scripts/harden.py` (`ORACLE_POOL`, overridable via the environment)
and deliberately excludes the builder model: a family checked only against its own
author, or only against one vendor, is fitted to that model's blind spots rather than
shown to be hard. Each difficulty level is asked of three distinct models on three
drawn seeds and is held only if **all three fail**; when one solves it the harness
escalates, and after three escalations the family is given up on.

The loop is owned by `scripts/harden.py`, not by the builder — see `CODEX.md`.

See `examples/1912.09051/` for a complete worked result — built under the pre-`harden.py`
rules and tagged `schema_version: 1`, so read it for the shape of a result and not for
the current interface — and `prompts/codex_task.md` for the prompt that produces them.

## Layout

```
papers/papers.jsonl          12,167 candidate papers (input)
STATUS.md                    progress board (generated; do not hand-edit)
prompts/codex_task.md        the per-paper Codex prompt
scripts/claim.sh             reserve the next free paper (race-safe via git)
scripts/run_codex.sh         build one generator/verifier
scripts/harden.py            the oracle loop: model pool, escalation, give-up verdict
scripts/submit.sh            interface-check, emit, commit, push
scripts/status.sh            progress board  (--write regenerates STATUS.md)
scripts/emit.sh              emit dataset instances from a finished module
scripts/fetch_paper.sh       polite arXiv source/PDF fetch
claims/<id>.json             who has which paper + state
results/<id>/README.md       what the problem is, why it is hard, caveats — written
                             by whoever built it, and required by submit.sh
results/<id>/gen_<id>.py     the generator/verifier module
results/<id>/                selftest_report.json, llm_loop_transcript.jsonl, codex_run.log
artifacts/<id>.jsonl         emitted instances: question + answer + params
results/<id>/.meta.json      run metadata: schema version, master seeds, oracle pool,
                             hardening verdict, duplicate rate (generated)
examples/1912.09051/         a finished example
CODEX.md                     sandbox, keys, quota — read this
CLAUDE.md                    playbook for Claude Code
```

## Honest caveats

- **Triage is not ground truth.** `candidate_generator` / `candidate_verifier` are
  hypotheses from an abstract-level pass. Papers that turn out to be in P, already
  classified, or lacking a cheap verifier do occur — reject them, with a reason.
- **An LLM failing is weak evidence of hardness.** LLMs are poor at long combinatorial
  construction even when a classical algorithm solves the problem instantly. Always also
  run the standard algorithm for the problem class.
- **Planted instances can be easy.** A correct hardness theorem does not make *random
  planted* instances hard. Measure solution density; do not assume it.
