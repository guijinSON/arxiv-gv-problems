# Playbook for Claude Code

When the user says **"do a paper"** / **"process a paper"**, run this loop.

## Loop

1. `bash scripts/status.sh` — show where the effort stands.
2. `bash scripts/claim.sh` — reserves the next free paper (or `scripts/claim.sh <id>`).
3. `bash scripts/run_codex.sh <id>` — builds `results/<id>/` in the background using
   `gpt-5.6-sol` at `xhigh` reasoning effort. Needs `OPENROUTER_API_KEY`. Read
   `CODEX.md` first if the sandbox errors.
4. Poll `results/<id>/codex_run.log` until `ps -eo comm | grep -cx codex` is 0.
5. **Audit the output yourself — do not trust the self-report.** See below.
6. `bash scripts/submit.sh <id>` — interface check, emit, commit, push. It refuses a
   result missing `README.md`, `selftest_report.json` or `llm_loop_transcript.jsonl`.

**The builder writes `results/<id>/README.md`, not a script.** Only whoever read the
paper alongside the code can say which theorem the regime is steering around, which
preset was rejected and by which gate, and which attacks went untried. If it is missing,
send the builder back for it rather than generating one — a reformatted JSON dump is
not the same artifact. The spec is in `prompts/codex_task.md`, STEP 5.

## Audit before submitting

Codex reports its own gate results. Independently confirm at least:

- `verify(inst, inst["answer"])` is True across several seeds **and** every preset
- `verify` never reads `inst["answer"]` (read the source)
- corrupted answers are rejected: drop one, duplicate, empty, out of range, wrong type
- `parse_answer` round-trips, and takes the **last** `<answer>` block, not the first
  (models often emit a draft then a correction)
- `canonical_key` actually keys on the instance — not on the seed, not on a hash of
  `render(inst)`. Both of those make every instance look distinct and turn the
  duplicate check into a no-op that always passes. `submit.sh` only checks that the
  key is deterministic; whether it is invariant under relabelling is on you.
- `escalate` moves along an axis that costs a solver, not just `n`
- `enumerate_all` agrees with brute force at a small size, if feasible
- `search_space` and `random_candidate` describe the *same* space, and that space is
  the one a **solver** would search — not a naive superset. A P(guess) measured over
  uniform noise can understate a family's guessability by 20 orders of magnitude.
- run the **standard algorithm** for the problem class as an attack — a SAT solver for
  satisfiability, rotation-extension for Hamiltonicity, an ILP for covering. Generic
  greedy/outlier attacks are not enough and have missed real breaks.

If the family is genuinely unsuitable (in P, classified, no cheap verifier), record that
in `results/<id>/REJECTED.md` with the reason and submit it. A documented rejection is a
useful result.

## The hardening loop is not the builder's

`scripts/harden.py` owns it, and the builder only runs it. It draws an oracle afresh
from a four-vendor pool on every call, holds a difficulty level only if **all three**
models fail it, escalates when one solves it, and after **3 escalations** returns
`verdict: "too_easy"`.

A `too_easy` verdict means **give the paper up**. `submit.sh` refuses it. Write
`REJECTED.md` saying which theorem or regime you were counting on and why it does not
bite, then `bash scripts/submit.sh <id> --reject`. Do not hand-tune the presets past
the verdict to get something shippable — a family that only clears the bar after you
retune it by hand is tuned to that run, and that is exactly the outcome the pool and
the escalation cap exist to catch.

## Notes

- Never commit API keys. Check `git diff --cached` before pushing.
- One paper is ~18 min and ~300k Codex tokens.
- Be polite to arXiv: `scripts/fetch_paper.sh` already sleeps between requests.
