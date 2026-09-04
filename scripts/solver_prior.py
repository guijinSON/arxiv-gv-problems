#!/usr/bin/env python3
"""Predict which SOLVER FAMILY a paper will land in, before anyone builds it.

This closes the feedback loop. `audit/attack_families.json` records what actually
cracked each shipped family; this file turns those measurements into a prior over
unbuilt papers, so `scripts/pick_paper.py` can steer on the thing that matters --
the skill a question exercises -- instead of on arXiv category, which we measured
to be a poor proxy.

WHY CATEGORY IS THE WRONG AXIS.  Measured over 23 attacked families,
`constraint_search` is an attractor: it absorbed math.MG (kissing numbers in 17-21
dimensions), math.GR, math.LO, cs.GT, cs.IT and math.CO alike.  Selecting a
geometry paper does not get you a geometry question.  The stated `family` field
predicts the solver far better than the arXiv category does.

HONESTY ABOUT STRENGTH.  This prior is fitted on 23 labelled points.  Two rules
rest on a single observation each and say so.  Confidence is reported with every
prediction and `--validate` measures leave-one-out accuracy.  Treat a prediction as
a nudge for selection, never as a claim about a paper.

Re-run `--validate` after each new measurement lands; that is the loop.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

# Families whose questions have, without exception so far, been cracked by
# propagation + backtracking regardless of the source paper's subject.
COMBINATORIAL_FAMILIES = {
    "graph structures", "constraint satisfaction", "reconfiguration",
    "designs and codes", "schedules and allocations", "words and permutations",
    "geometric configurations", "set system structures", "combinatorial games",
    "matroid structures", "poset structures", "topological structures",
    "games and social choice", "adversarial inputs",
}
# Families whose witness is a selection of integers/group elements summing or
# cancelling to a target -- these went to meet-in-the-middle / DP / lattice.
ADDITIVE_FAMILIES = {
    "additive combinatorial structures", "integer equations",
}
# Families that produced a NON-constraint core.  Small support; see `support`.
ALGEBRAIC_FAMILIES = {
    "algebraic decomposition", "algebraic identity solutions",
    "algebraic geometric structures", "algebraic isomorphisms",
    "finite algebraic structures", "number field constructions",
}

# rule name -> (predicate, predicted family, support n, note)
RULES = [
    ("additive_or_integer_family",
     lambda r: r.get("family") in ADDITIVE_FAMILIES and "math.NT" in r.get("all_cats", ""),
     "subset_sum_knapsack", 4,
     "4 of the 6 math.NT papers measured landed here; the other 2 went to "
     "linear_algebra_finite_field and brute_force_structure"),

    ("finite_field_constructions",
     lambda r: r.get("family") == "finite field constructions",
     "brute_force_structure", 1,
     "SINGLE observation (2511.01003). Weak."),

    ("algebraic_family",
     lambda r: r.get("family") in ALGEBRAIC_FAMILIES,
     "paper_constructive", 1,
     "SINGLE observation (2205.04710, algebraic decomposition). Weak, but these "
     "are the families that produced the only non-constraint cores, so the "
     "prediction is deliberately optimistic to keep them in the draw."),

    ("planted_dense_subgraph",
     lambda r: r.get("method") == "planted solution"
               and any(k in (r.get("candidate_generator", "") + r.get("title", "")).lower()
                       for k in ("clique", "biclique", "dense subgraph", "community")),
     "dense_subgraph_spectral", 2,
     "2 observations (0901.3348, 1008.2814), both planted-clique papers."),

    ("combinatorial_family",
     lambda r: r.get("family") in COMBINATORIAL_FAMILIES,
     "constraint_search", 13,
     "13 observations spanning 8 arXiv primaries. This is the attractor: it "
     "absorbs geometry, group theory and logic papers alike."),

    ("additive_family_no_nt",
     lambda r: r.get("family") in ADDITIVE_FAMILIES,
     "subset_sum_knapsack", 1,
     "fallback for integer-selection families outside math.NT"),
]

UNKNOWN = "unpredicted"


def predict(rec: dict):
    """Return (solver_family, confidence in [0,1], rule_name).

    Confidence is a blunt function of how many measurements back the rule; it is
    not a calibrated probability and should not be reported as one.
    """
    for name, pred, fam, support, _note in RULES:
        try:
            if pred(rec):
                conf = min(0.85, 0.35 + 0.05 * support)
                return fam, conf, name
        except Exception:
            continue
    return UNKNOWN, 0.0, "none"


def load_rows(root=ROOT):
    rows = {}
    with open(os.path.join(root, "papers", "papers.jsonl")) as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                rows[r["arxiv_id"]] = r
    return rows


def load_measured(root=ROOT):
    try:
        with open(os.path.join(root, "audit", "attack_families.json")) as fh:
            return json.load(fh).get("measured", {})
    except (OSError, ValueError):
        return {}


def cmd_validate(root=ROOT):
    """Accuracy on the labelled set. Not leave-one-out in the statistical sense --
    the rules were written by reading these 23 points, so this is a consistency
    check, not a generalisation estimate. It is reported as such."""
    rows, meas = load_rows(root), load_measured(root)
    ok = tot = 0
    wrong = []
    for pid, m in meas.items():
        r = rows.get(pid)
        if not r:
            continue
        got, conf, rule = predict(r)
        tot += 1
        if got == m["family"]:
            ok += 1
        else:
            wrong.append((pid, m["family"], got, rule))
    print(f"fit on the labelled set: {ok}/{tot} = {100*ok/max(tot,1):.0f}%")
    print("NOT a generalisation estimate -- the rules were written after reading")
    print("these same 23 points. It only shows the rules are self-consistent.\n")
    if wrong:
        print("misfits:")
        for pid, want, got, rule in wrong:
            print(f"  {pid:12} measured={want:26} predicted={got:26} via {rule}")
    return 0


def cmd_distribution(root=ROOT):
    """Predicted solver family over every FREE paper -- the supply picture."""
    rows = load_rows(root)
    free = []
    for pid, r in rows.items():
        if "/" in pid:
            continue
        if os.path.exists(os.path.join(root, "claims", f"{pid}.json")):
            continue
        if os.path.isdir(os.path.join(root, "results", pid)):
            continue
        free.append(r)
    c = collections.Counter(predict(r)[0] for r in free)
    tot = sum(c.values()) or 1
    print(f"predicted solver family across {tot} FREE papers:\n")
    for fam, n in c.most_common():
        print(f"  {n:6} ({100*n/tot:5.1f}%)  {fam}")
    print("\nThis is the ceiling on diversity from this pool. If one family dominates")
    print("here, no scheduler can fix it -- that needs a new retrieval pass.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--distribution", action="store_true")
    ap.add_argument("--paper", help="predict for one arxiv id")
    a = ap.parse_args(argv)
    if a.validate:
        return cmd_validate()
    if a.distribution:
        return cmd_distribution()
    if a.paper:
        r = load_rows().get(a.paper)
        if not r:
            print(f"unknown paper {a.paper}"); return 1
        fam, conf, rule = predict(r)
        print(f"{a.paper}: {fam}  (confidence {conf:.2f}, rule {rule})")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
