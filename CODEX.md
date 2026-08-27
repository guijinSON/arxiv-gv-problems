# Running Codex for this repo

One paper ≈ **18 minutes** and **~300k tokens** on `gpt-5.5` at high reasoning effort.
Budget accordingly: a single Codex account covers a few hundred papers, not thousands.

## The sandbox problem

Codex sandboxes model-run shell commands with **bubblewrap**. This task needs to write
files, run Python, fetch from arXiv, and call an LLM API — so `--sandbox read-only`
(the default) will not work.

Use, in order of preference:

### 1. `--sandbox workspace-write` — try this first

```bash
codex exec --skip-git-repo-check --sandbox workspace-write \
  -m gpt-5.5 -c model_reasoning_effort="high" "$(cat TASK.md)"
```

Writes are confined to the working directory and network is allowed. This is what
`scripts/run_codex.sh` uses by default.

### 2. If bubblewrap is broken on your host

On many containers, VPS images, and hosts without user-namespace privileges you will see:

```
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

and then **every** command and file write fails — including writes to `/tmp`. Codex
reports the failure honestly rather than fabricating results, so the run ends with no
module produced.

Try first, in this order:

```bash
# a) install a real bubblewrap (the bundled one is often the problem)
sudo apt-get install -y bubblewrap && which bwrap

# b) allow unprivileged user namespaces
sudo sysctl -w kernel.unprivileged_userns_clone=1
sudo sysctl -w user.max_user_namespaces=10000
```

### 3. Last resort — no sandbox

```bash
CODEX_SANDBOX_MODE=bypass bash scripts/run_codex.sh <arxiv_id>
```

which runs `codex exec --dangerously-bypass-approvals-and-sandbox`.

**This gives the model unrestricted shell access to the machine.** Only do it when all of
these hold:

- a **disposable** VM or container you can destroy, not your laptop and not a shared box
- **no credentials on the host** beyond the one API key the task needs — no SSH keys, no
  cloud tokens, no `~/.aws`, no password manager
- run as a **non-root user** with a scoped home directory
- **no access to private networks** you care about
- you are prepared for the working directory to be modified arbitrarily

Never point it at a machine holding other people's data.

## Keys

The hardening loop needs an LLM API key:

```bash
export OPENAI_API_KEY=sk-...        # for gpt-5.6-terra
```

Never commit it. `.gitignore` covers `.orkey` and `.env`, and `scripts/submit.sh`
deletes any stray `.orkey` before committing — but check your own diffs anyway.

## Watching a run

```bash
tail -f results/<id>/codex_run.log
ps -eo comm --no-headers | grep -cx codex     # 1 = running, 0 = finished
```

Do **not** use `pgrep -f "codex exec"` to test liveness — your own shell command
contains that string and will match itself, reporting a run that is not there.

## When quota runs out

Codex accounts have a **weekly** quota. Exhaustion looks like:

```
ERROR: You've hit your usage limit ... try again at <date>
```

There is no point retrying before the reset. Switch accounts with `CODEX_HOME`:

```bash
CODEX_HOME=$HOME/.codex2 bash scripts/run_codex.sh <arxiv_id>
```
