# results/

Per-paper build output: `results/<arxiv_id>/`.

| file | what |
|---|---|
| `gen_<id>.py` | the module — generator, renderer, parser, verifier, gates |
| `TASK.md` | the exact prompt used (prompt template + this paper's row) |
| `codex_run.log` | full Codex transcript, including the gate numbers |
| `llm_loop_transcript.jsonl` | every `gpt-5.6-terra` attempt and raw reply |
| `REJECTED.md` | present only if the family was rejected — says which gate and why |

The paper's own PDF/source (`*.pdf`, `*.tar`, `src/`) is fetched during the build but
**not committed** — see `.gitignore`. Re-fetch with `scripts/fetch_paper.sh <id>`.
