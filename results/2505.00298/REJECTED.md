# Rejection — arXiv 2505.00298

## Verdict

The candidate family fails **H on Track A**.  It passes generation and exact
verification, but a construction-aware greedy/noisy WalkSAT attack finds a
valid certificate on every tested shipping instance in milliseconds.  The
paper is not being rejected because an algorithm merely exists: the measured
algorithm is effective on the actual generated distribution.

Track B does not rescue this family.  There is no compact invariant, symmetry,
or change of variables that replaces the local search.  The shortest route
found is the mechanical route itself, so the family tests execution of that
search rather than recognition of a concise idea.

The built candidate is retained as `rejected_gen_2505_00298.py`, and
`selftest_report.json` records the failing gates.

## Paper result and exact regime

Yu and Sun, [*Internally-disjoint Pendant Steiner Trees in
Digraphs*](https://arxiv.org/abs/2505.00298), Section 2.2, Theorem 2.6 reduce
Hypergraph 2-Coloring to deciding whether a symmetric digraph contains two
internally-disjoint pendant `(S,r)`-trees.  The theorem's hard regime fixes
`ell = 2` while `k = |S|` is part of the input.  This candidate used exactly
that regime: an edge-terminal is created for every hyperedge, so `k` grows.

The easy case was checked before building.  Section 2.2, Theorem 2.3 gives an
`O(n^(ell(k-2)+2) k^(ell(2k-3)))` algorithm on symmetric digraphs when both
`k` and `ell` are fixed.  The candidate does not fall into that regime.

The certificate-producing route is the forward implication in Theorem 2.6.
Generation first samples a balanced red/blue partition and then constructs a
simple connected regular 3-uniform hypergraph whose edges are all bichromatic.
The proof turns the two colour classes into two directed pendant trees.  Thus
G holds by inverse generation and theorem-backed composition; no solver is run
to obtain the planted certificate.  V holds because the checker reconstructs
both trees and exactly checks arcs, indegrees, reachability, terminal degrees,
arc-disjointness, and vertex intersection without reading `inst["answer"]`.

## Failed distributional-hardness audit

The initial panel was inadequate: its so-called min-conflicts attack chose a
random endpoint of a bad edge.  A standard stronger move chooses an endpoint
that minimizes the resulting number of monochromatic edges, with 25% random
noise.  With 128 restarts and at most `10n` flips per restart, it gives:

| n | degree | successes | flips over 8 seeds | edge inspections | wall clock |
|---:|---:|---:|---:|---:|---:|
| 198 | 6 | 8/8 | 1,514–10,439 | 29,766–206,112 | 0.0068–0.0413 s |
| 222 | 6 | 8/8 | 626–28,823 | 12,516–567,978 | 0.0036–0.1081 s |
| 246 | 6 | 8/8 | 833–13,239 | 16,362–262,818 | 0.0045–0.0512 s |

The required fixed-answer-length hardening axis was also tested at `n=198`:

| regular degree | successes | wall-clock range |
|---:|---:|---:|
| 8 | 8/8 | 0.0060–0.0938 s |
| 10 | 8/8 | 0.0034–0.0159 s |
| 12 | 8/8 | 0.0037–0.0124 s |

Increasing constraint density makes these samples easier, not harder.  This is
therefore not `cap_bound`: the fixed-length axes were tried and the construction
remained easy throughout the full writable ladder.

At the self-test's shipping seed 12345, the **mechanical cost** is 2,688 flips,
52,920 edge inspections, and 0.0124 seconds.  The **compact route length** is
not smaller: the best route found is that same 2,688-flip local search (and even
writing the returned partition needs 198 atoms).  The ratio between compact
and mechanical routes is therefore 1, not the large gap required by Track B;
there is no dozen-operation insight to test.

Worst-case NP-completeness from Theorem 2.6 does not contradict this result and
does not establish hardness of the planted regular distribution.  G4's
0/200,000 uniform-partition guesses also does not help: low blind-guess density
is compatible with a strong local gradient.

## Other evidence

The exact DPLL probe with forced-third-vertex propagation did not finish within
4,000 nodes on the audit seeds, but WalkSAT's success overrides that failure.
The four-vendor hardening harness was invoked as required, but the configured
OpenRouter key returned HTTP 403 `Key limit exceeded` on all redraws.  Those
service errors are preserved in the script-owned transcripts and are not
counted as model failures.  This external blocker is not the reason for the
rejection; G5 and G6 already fail locally.

An acceptable future family would need either a different theorem-backed
source distribution that survives the domain attack, or a genuine Track B
compression gap.  Relabelling or raising the regular degree of this planted
family is insufficient.
