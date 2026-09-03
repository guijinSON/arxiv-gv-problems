#!/usr/bin/env python3
"""Deficit-based stratified paper selection.

Replaces the old rule, which was `first free line of papers/papers.jsonl`.  That
file is grouped by family, so the old rule handed out 73 consecutive
`additive combinatorial structures` papers before the family could change --
measured, not estimated.  A contributor running `scripts/claim.sh` with no
argument reproduced the corpus's combinatorial skew by construction.

Selection now works on a bucket derived from the paper's own arXiv categories,
which the builder does not control:

    priority(b) = target_share(b) * (committed + 1) - accepted(b) - in_progress(b)

The most under-represented bucket wins; a free paper is drawn at RANDOM from it
(so a lost race does not deterministically re-pick the same paper); and within a
bucket, papers carrying a hardness signal are preferred, because 24 of 45
rejections failed on H and that is the most expensive way to lose a paper.

Both accepted AND in-progress papers count against a bucket's target -- otherwise
a fleet of concurrent builders all pile into the same deficit.

Exit codes: 0 picked (id on stdout) / 3 nothing free / 4 internal error.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

# --- bucket definition ------------------------------------------------------
# Keyed on arXiv categories only, because that is all that exists for an
# UNCLAIMED paper.  The rich PROBLEM_PROFILE is written by the builder and so is
# only available after the work is done -- it cannot drive selection.
BUCKET_CATS = [
    ("symbolic_algebra", {"math.AG", "math.AC", "math.RA", "math.QA", "math.RT", "cs.SC"}),
    ("geometry_real",    {"math.MG", "math.DG", "math.GT", "math.AT", "cs.CG"}),
    ("dynamics_opt",     {"math.OC", "math.DS", "math.NA", "math.AP", "math.CA",
                          "math.FA", "math.PR", "math-ph", "math.SP", "eess.SY", "cs.SY"}),
    ("logic",            {"math.LO", "cs.LO", "cs.FL", "cs.PL"}),
    ("crypto_coding",    {"cs.CR", "cs.IT", "math.IT"}),
    ("number_theory",    {"math.NT"}),
    ("quantum",          {"quant-ph"}),
    ("discrete",         {"math.CO", "cs.DM", "cs.DS", "cs.CC", "cs.GT"}),
]

# Target release shares.  These are DELIBERATELY not the pool's shares -- the pool
# is 80.4% discrete and reproducing it is the bug.  They are also bounded by
# supply: dynamics_opt has ~524 papers total and ~25% acceptance, so it can never
# supply more than roughly 131 problems.  scripts/corpus_report.py --gate holds the
# release to these; this file only steers what gets ATTEMPTED next.
TARGET_SHARE = {
    "discrete":         0.34,
    "symbolic_algebra": 0.18,
    "geometry_real":    0.12,
    "dynamics_opt":     0.12,
    "number_theory":    0.10,
    "crypto_coding":    0.06,
    "logic":            0.05,
    "quantum":          0.02,
    "other":            0.01,
}


def bucket_of(all_cats: str) -> str:
    """First matching bucket, in BUCKET_CATS order.

    Order matters: `discrete` is LAST so that a math.AG paper cross-listed to
    math.CO counts as symbolic_algebra.  The old accounting did the opposite and
    hid most non-discrete work inside the discrete bucket.
    """
    cats = set(all_cats.split())
    for name, keys in BUCKET_CATS:
        if cats & keys:
            return name
    return "other"


def has_hardness(rec: dict) -> bool:
    """True when the record carries a non-'none' hardness signal.

    Tolerates the field being absent -- scripts/score_hardness.py may not have
    been run yet, in which case every paper is treated as equally unknown and this
    preference silently switches off rather than breaking selection.
    """
    he = rec.get("hardness_evidence")
    if not isinstance(he, dict):
        return False
    return bool(he.get("class")) and he.get("class") != "none"


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


def census(root: str, recs: dict):
    """accepted / in_progress counts per bucket, plus the set of taken papers.

    A paper is 'taken' if it has a claim file OR a results/ directory -- the
    latter because results/1910.10364 existed for a while with no claim file and
    was invisible to every count in the repo, including this picker.
    """
    accepted, inprog = {}, {}
    taken = set()
    cdir = os.path.join(root, "claims")
    if os.path.isdir(cdir):
        for fn in os.listdir(cdir):
            if not fn.endswith(".json"):
                continue
            pid = fn[:-5]
            taken.add(pid)
            try:
                with open(os.path.join(cdir, fn)) as fh:
                    st = json.load(fh).get("status")
            except (OSError, ValueError):
                continue
            b = bucket_of(recs.get(pid, {}).get("all_cats", ""))
            if st == "done":
                accepted[b] = accepted.get(b, 0) + 1
            elif st in ("in_progress", "claimed"):
                inprog[b] = inprog.get(b, 0) + 1
    rdir = os.path.join(root, "results")
    if os.path.isdir(rdir):
        for fn in os.listdir(rdir):
            if os.path.isdir(os.path.join(rdir, fn)):
                taken.add(fn)
    return accepted, inprog, taken


def priorities(accepted: dict, inprog: dict):
    committed = sum(accepted.values()) + sum(inprog.values())
    out = {}
    for b, share in TARGET_SHARE.items():
        have = accepted.get(b, 0) + inprog.get(b, 0)
        out[b] = share * (committed + 1) - have
    return out, committed


def pick(root: str, exclude: set, rng: random.Random, explain: bool = False):
    recs, order = load(root)
    accepted, inprog, taken = census(root, recs)
    taken |= exclude
    prio, committed = priorities(accepted, inprog)

    free_by_bucket: dict[str, list] = {}
    for pid in order:
        if pid in taken:
            continue
        free_by_bucket.setdefault(bucket_of(recs[pid].get("all_cats", "")), []).append(pid)

    if explain:
        print(f"{'bucket':18} {'target':>7} {'acc':>4} {'wip':>4} {'have':>5} "
              f"{'priority':>9} {'free':>6} {'w/hard':>7}", file=sys.stderr)
        for b in sorted(prio, key=lambda x: -prio[x]):
            fr = free_by_bucket.get(b, [])
            nh = sum(1 for p in fr if has_hardness(recs[p]))
            print(f"{b:18} {TARGET_SHARE[b]:>7.2f} {accepted.get(b,0):>4} "
                  f"{inprog.get(b,0):>4} {accepted.get(b,0)+inprog.get(b,0):>5} "
                  f"{prio[b]:>9.2f} {len(fr):>6} {nh:>7}", file=sys.stderr)
        print(f"committed (accepted+in_progress) = {committed}", file=sys.stderr)

    # Walk buckets by descending deficit and take the first that can actually
    # supply a paper.  This is the anti-deadlock property: an exhausted or
    # supply-starved bucket is skipped rather than blocking the queue, which
    # matters because the non-discrete buckets are small and will run dry.
    for b in sorted(prio, key=lambda x: (-prio[x], x)):
        cands = free_by_bucket.get(b, [])
        if not cands:
            continue
        hard = [p for p in cands if has_hardness(recs[p])]
        chosen_pool = hard or cands
        return rng.choice(chosen_pool), b, bool(hard)
    return None, None, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--exclude", default="", help="comma-separated ids to skip (race avoidance)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--explain", action="store_true", help="print the deficit table to stderr")
    ap.add_argument("--dry-run", action="store_true", help="explain only; print nothing to stdout")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    exclude = {x for x in a.exclude.split(",") if x}
    try:
        pid, bucket, from_hard = pick(a.root, exclude, rng, explain=a.explain or a.dry_run)
    except OSError as e:
        print(f"pick_paper: {e}", file=sys.stderr)
        return 4
    if pid is None:
        return 3
    if a.dry_run:
        print(f"would pick {pid} from {bucket}"
              f"{' (hardness-signalled)' if from_hard else ''}", file=sys.stderr)
        return 0
    print(pid)
    print(f"  bucket={bucket}{' hardness-signalled' if from_hard else ''}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
