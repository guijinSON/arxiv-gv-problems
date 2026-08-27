# Playbook for Claude Code

When the user says **"do a paper"** / **"process a paper"**, run this loop.

## Loop

1. `bash scripts/status.sh` — show where the effort stands.
2. `bash scripts/claim.sh` — reserves the next free paper (or `scripts/claim.sh <id>`).
3. `bash scripts/run_codex.sh <id>` — builds `results/<id>/` in the background.
   Read `CODEX.md` first if the sandbox errors.
4. Poll `results/<id>/codex_run.log` until `ps -eo comm | grep -cx codex` is 0.
5. **Audit the output yourself — do not trust the self-report.** See below.
6. `bash scripts/submit.sh <id>` — runs an interface check, then commits and pushes.

## Audit before submitting

Codex reports its own gate results. Independently confirm at least:

- `verify(inst, inst["answer"])` is True across several seeds **and** every preset
- `verify` never reads `inst["answer"]` (read the source)
- corrupted answers are rejected: drop one, duplicate, empty, out of range, wrong type
- `parse_answer` round-trips, and takes the **last** `<answer>` block, not the first
  (models often emit a draft then a correction)
- `enumerate_all` agrees with brute force at a small size, if feasible
- `search_space` and `random_candidate` describe the *same* space
- run the **standard algorithm** for the problem class as an attack — a SAT solver for
  satisfiability, rotation-extension for Hamiltonicity, an ILP for covering. Generic
  greedy/outlier attacks are not enough and have missed real breaks.

If the family is genuinely unsuitable (in P, classified, no cheap verifier), record that
in `results/<id>/REJECTED.md` with the reason and submit it. A documented rejection is a
useful result.

## Notes

- Never commit API keys. Check `git diff --cached` before pushing.
- One paper is ~18 min and ~300k Codex tokens.
- Be polite to arXiv: `scripts/fetch_paper.sh` already sleeps between requests.
