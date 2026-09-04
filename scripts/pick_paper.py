#!/usr/bin/env python3
"""Pick the next paper to build: a UNIFORM RANDOM draw from the free pool.

Selection history, because it matters for reading any statistic computed over the
corpus:

1. *First free line of papers/papers.jsonl.*  That file is grouped by family, so
   the rule handed out 73 consecutive `additive combinatorial structures` papers
   before the family could change.  It reproduced the corpus's combinatorial skew
   by construction.
2. *Deficit-based stratified sampling* toward a target share per predicted solver
   family.  It fixed the grouping artefact, but it steered on
   `scripts/solver_prior.py`, a prior fitted on 23 points by rules written after
   reading those same 23 points.  Steering hard on a prior that weak means the
   selection rule, not the pool, decides what the benchmark contains -- and it
   systematically skipped papers the prior guessed were `constraint_search`,
   including any it guessed wrong.
3. *Uniform random* -- this file.

WHAT UNIFORM RANDOM BUYS.  Every measurement taken downstream becomes an unbiased
estimate of the POOL.  Acceptance rate, solver-family share and answer-shape share
now describe what these 12,167 papers actually yield, instead of describing the
interaction between the pool and a hand-tuned target vector.  That is the number
worth having, because it is the one that says whether the pool can support the
benchmark at all.

WHAT IT COSTS, STATED PLAINLY.  `scripts/solver_prior.py --distribution` predicts
~75% of the free pool is `constraint_search`.  A uniform draw will reproduce
roughly that, so the corpus will re-concentrate.  Random sampling MEASURES the
skew honestly; it does not fix it.  If the measured share comes back as bad as the
prior suggests, the fix is a new retrieval pass over arXiv -- a better pool -- not
a cleverer scheduler over this one.  `--explain` prints the running family mix so
that drift is visible while it happens rather than after 100 more builds.

Exit codes: 0 picked (id on stdout) / 3 nothing free / 4 internal error.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import random
import sys

# Imported for REPORTING only. This file no longer steers on the prior; it just
# shows what the draw is producing, so a collapse is visible early.
_sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "solver_prior.py")
try:
    _spec = importlib.util.spec_from_file_location("solver_prior", _sp)
    solver_prior = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(solver_prior)
except Exception:            # keep selection working if the prior is unavailable
    solver_prior = None


def bucket_of(rec) -> str:
    """MEASURED solver family if one exists for this paper, else the PREDICTED one.
    Diagnostic only -- it does not affect which paper is drawn."""
    if isinstance(rec, str):
        rec = {"all_cats": rec}
    pid = rec.get("arxiv_id")
    if pid and pid in _MEASURED:
        return _MEASURED[pid]
    if solver_prior is not None:
        return solver_prior.predict(rec)[0]
    return "unpredicted"


def _load_measured(root):
    try:
        with open(os.path.join(root, "audit", "attack_families.json")) as fh:
            return {k: v.get("family") for k, v in json.load(fh).get("measured", {}).items()}
    except (OSError, ValueError):
        return {}


_MEASURED = {}


def load(root: str):
    recs, order = {}, []
    with open(os.path.join(root, "papers", "papers.jsonl")) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            recs[r["arxiv_id"]] = r
            order.append(r["arxiv_id"])
    return recs, order


def taken_set(root: str):
    """Papers that are spoken for.

    A paper counts as taken if it has a claim file OR a results/ directory -- the
    latter because results/1910.10364 existed for a while with no claim file and was
    invisible to every count in the repo, including this picker.
    """
    taken = set()
    cdir = os.path.join(root, "claims")
    if os.path.isdir(cdir):
        taken |= {fn[:-5] for fn in os.listdir(cdir) if fn.endswith(".json")}
    rdir = os.path.join(root, "results")
    if os.path.isdir(rdir):
        taken |= {fn for fn in os.listdir(rdir)
                  if os.path.isdir(os.path.join(rdir, fn))}
    return taken


def status_counts(root: str, recs: dict):
    """accepted / rejected / in-progress counts per solver-family bucket. Reporting."""
    acc, rej, wip = collections.Counter(), collections.Counter(), collections.Counter()
    cdir = os.path.join(root, "claims")
    if not os.path.isdir(cdir):
        return acc, rej, wip
    for fn in os.listdir(cdir):
        if not fn.endswith(".json"):
            continue
        pid = fn[:-5]
        try:
            with open(os.path.join(cdir, fn)) as fh:
                st = json.load(fh).get("status")
        except (OSError, ValueError):
            continue
        b = bucket_of(recs.get(pid) or {"arxiv_id": pid, "all_cats": ""})
        if st == "done":
            acc[b] += 1
        elif st == "rejected":
            rej[b] += 1
        elif st in ("in_progress", "claimed"):
            wip[b] += 1
    return acc, rej, wip


def pick(root: str, exclude: set, rng: random.Random, explain: bool = False):
    global _MEASURED
    recs, order = load(root)
    _MEASURED = _load_measured(root)
    taken = taken_set(root) | exclude

    # 533 of the 12,167 ids are legacy arXiv ("math/0611582").  Every path in this
    # repo is claims/<id>.json and results/<id>/, so a slashed id needs a directory
    # that nothing creates: the claim write fails and claim.sh used to report CLAIMED
    # anyway.  The old first-free rule never reached them; a random draw does, so
    # they must be excluded explicitly until the on-disk layout is changed.
    free, skipped_legacy = [], 0
    for pid in order:
        if pid in taken:
            continue
        if "/" in pid:
            skipped_legacy += 1
            continue
        free.append(pid)

    if explain:
        acc, rej, wip = status_counts(root, recs)
        done = sum(acc.values()) + sum(rej.values())
        print(f"free {len(free)} of {len(order)} papers "
              f"({skipped_legacy} legacy slashed ids excluded)", file=sys.stderr)
        print("\nuniform random draw -- no steering. Running mix, so drift is visible:",
              file=sys.stderr)
        print(f"\n  {'solver family':28} {'acc':>4} {'rej':>4} {'wip':>4} {'acc share':>10} "
              f"{'free pool':>10}", file=sys.stderr)
        freemix = collections.Counter(bucket_of(recs[p]) for p in free)
        nacc = sum(acc.values()) or 1
        nfree = len(free) or 1
        for b in sorted(set(acc) | set(rej) | set(wip) | set(freemix),
                        key=lambda x: (-acc[x], x)):
            print(f"  {b:28} {acc[b]:>4} {rej[b]:>4} {wip[b]:>4} "
                  f"{100*acc[b]/nacc:>9.1f}% {100*freemix[b]/nfree:>9.1f}%", file=sys.stderr)
        # This rate is NOT yet an unbiased estimate of anything. Of the attempts
        # below, 77 were hand-picked and the rest came from the deficit scheduler;
        # both chose on predicted family, so the rate measures those choices as much
        # as it measures the pool. Only papers drawn from here on are uniform.
        print(f"\n  accepted {sum(acc.values())} / attempted {done} "
              f"({100*sum(acc.values())/max(done,1):.0f}% acceptance) -- HISTORICAL, "
              f"selection-confounded:", file=sys.stderr)
        print("  these were hand-picked or deficit-scheduled, not drawn uniformly.",
              file=sys.stderr)
        print("  The unbiased series starts with the next draw.", file=sys.stderr)
        print("  'free pool' is what a uniform draw converges to. Where 'acc share'"
              " tracks it,\n  the corpus mirrors the pool -- fix that with better"
              " retrieval, not selection.", file=sys.stderr)

    if not free:
        return None, None
    pid = rng.choice(free)
    return pid, bucket_of(recs[pid])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--exclude", default="", help="comma-separated ids to skip (race avoidance)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--explain", action="store_true", help="print the running mix to stderr")
    ap.add_argument("--dry-run", action="store_true", help="explain only; print nothing to stdout")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    exclude = {x for x in a.exclude.split(",") if x}
    try:
        pid, bucket = pick(a.root, exclude, rng, explain=a.explain or a.dry_run)
    except OSError as e:
        print(f"pick_paper: {e}", file=sys.stderr)
        return 4
    if pid is None:
        return 3
    if a.dry_run:
        print(f"would pick {pid} (predicted {bucket})", file=sys.stderr)
        return 0
    print(pid)
    print(f"  predicted={bucket}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
