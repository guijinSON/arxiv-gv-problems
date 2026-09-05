# Rejection: arXiv 2211.12813

## Verdict

The candidate family fails **H**, on both possible tracks.  It passes G: the
labeling is constructed before the shuffled instance and carried through the
relabeling, with compatible decoy edges admitted only against certificates
already held.  It passes V: `verify` checks every adjacency and distance-two
constraint exactly.  Neither fact makes the witness hard to obtain.

## Why Track A is unavailable

The paper contains no distributional hardness theorem for random or planted
hypergraphs.  Section 1 defines the L(h,k) problem and Lemma 2.4 equates it with
the 2-section problem, but neither supplies hardness.  More decisively,
Theorem 4.2 gives a constructive labeling for exactly the native Cartesian
products used by the candidate.  Calling this distribution Track A would hide
a known direct algorithm.

## Why Track B also fails

Definition 4.1 and Theorem 4.2 expose the same structure used by the generator.
The two non-decoy hyperedge sizes identify the complete-factor row partition
and the repeated star edges.  Sorting those incidence classes recovers all
coordinates, and two CRT schedules implement the theorem's diagonal coloring.

Measured on eight final hard-preset instances (`n=15`, 210--240 vertices, 12
compatible 3-edge decoys), the honest theorem-aware mechanical method required
5,094--6,234 counted incidence/sorting/assignment operations, mean **5,777.5**,
and 0.00037--0.00047 seconds, mean **0.000423 s**.  It solved 8/8.

The compact route is not materially shorter.  A solver must recover the same
coordinate map from the shuffled incidence list before using at most 180 CRT
assignments, then write 210--240 labels.  Thus its full route contains the same
5,094--6,234 incidence work plus the small CRT tail.  There is no dozen-step
invariant replacing the mechanical algorithm; the apparent difficulty comes
from scanning and transcribing a near-cap answer.

An earlier candidate report counted roughly 7.3 million operations by first
materializing every distance-two CSP relation.  That preprocessing is
unnecessary and is not an honest hardness basis: direct factor recovery solves
the same instances immediately.  The retained module now reports the direct
method instead.

## Oracle evidence is not the reason for rejection

A pre-correction hard bare run recorded 0/3 solves, and a pre-correction hinted
run recorded 0/2 completed solves before the OpenRouter key exhausted its total
quota.  The final correction changed seeded decoy instances, so those
transcripts are historical only and cannot certify the retained generator.
The placebo arm completed no scored attempt.  G9 therefore remains false and
pending in `selftest_report.json`; no oracle timeout or quota error is counted
as mathematical hardness.

The built code is retained as `rejected_gen_2211_12813.py`, together with its
reports and transcripts, so this decision can be replayed if a genuinely
compressed certificate language or a different paper-backed hard regime is
found.
