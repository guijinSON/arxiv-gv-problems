# Rejection: arXiv 2512.15237

## Decision

No family found in this paper clears the hardness requirement in a way that is also suitable for the no-tool benchmark.  **G and V pass** for the retained inverse-generated prototype: sides are sampled before the ratio is formed, and a submitted triangle is checked by exact cross multiplication.  **H is not defensible on either track**, for different reasons below, and the generic prototype independently fails mandatory G9(c).

This decision uses the full paper, especially Section 1 equations (2)–(3), Section 2's quartic/elliptic transformation, Theorems 2–3 in Section 4, and Theorem 4 in Section 5 (“The cases `N=m^2 +/- 1`”).  It is not based on the abstract.

## Generic inverse generation: Track A is not established

The retained prototype samples three distinct odd 256-bit triangle sides and computes

`N = 2fgh / ((f+g+h)(f-g-h)(g-h-f))`.

Theorems 2 and 3 turn recovery into finding an admissible non-torsion rational point on the associated elliptic curve.  They are existence/equivalence results, not distributional hardness results.  The paper gives no theorem showing that ratios induced by random high-height triangles resist an efficient recovery algorithm.  In particular, the reduced numerator often retains factors of `fgh`, so stronger factor-and-partition methods remain a plausible untested attack.  A bounded-height elliptic search and four construction-aware attacks failing do not repair that missing Track A basis.

The measured mechanical cost also exposes a separate G9(c) failure.  Height-128 rational-point enumeration tested **96,666 candidate `u` coordinates in 29.314325 seconds across eight shipping instances**, with 0/8 successes.  On the fixed G9 shipping instance it tested **12,639 points and still found no witness**.  Recognizing the semiperimeter/quartic/elliptic change of variables therefore does not leave a compact route; it merely relocates the hard search.  The earlier figure of 18 operations counted verification of an already-known triangle, not production of the certificate, and has been corrected.  The route already exceeds the 300-operation cap without succeeding.

Thus the generic family has a valid witness and plausible computational difficulty, but it does not have the theorem-backed distributional H claim required for Track A and does not test a bounded post-insight route.

## Theorem 4 construction: Track B has no compression gap

The natural theorem-backed alternative uses Theorem 4.  For `N=m^2-1`, it directly gives

`f=(m-1)(2m+1)^2,  g=(m+1)(2m-1)^2,  h=4m`,

with the analogous displayed formula for `N=m^2+1`.  This certainly passes G and V, but fails Track A immediately because the certificate is an explicit formula.

It also fails Track B after measuring both required numbers:

- **Mechanical method:** add/subtract 1 from `N`, take exact integer square roots of the reduced numerator and denominator, evaluate the displayed formula, and remove a common gcd.  Its bit complexity is polynomial (integer square root plus a constant number of big-integer products, conservatively `O(M(b) log b)`).  At a 256-bit parameter, 10,000 complete recoveries took **0.135759 seconds**, or **13.576 microseconds per instance**.  Counting the two square-root calls, formula arithmetic, and normalization gives at most **18 top-level exact operations**.
- **Compact route:** notice that `N+1` (or `N-1`) is a rational square and evaluate exactly the same Theorem 4 formula: **the same 18 operations**.

The mechanical cost and compact route are therefore comparable, not a million-operation mechanical path versus a dozen-operation insight.  Raising the bit length would test unaided large-integer arithmetic, not structural compression.  The paper's displayed birational coordinate maps have the same defect: direct evaluation and the compact route are both constant-length rational formulas.

## Files and external run

The built prototype is retained as `rejected_gen_2512_15237.py`, as required.  `selftest_report.json` records G1–G8 passing and G9(c) failing honestly.  The bare, structural-hint, and placebo hardening scripts were attempted, but every OpenRouter redraw returned HTTP 403 “Key limit exceeded”; their script-owned error transcripts are preserved.  This provider outage is **not** the rejection reason and was not scored as a model failure.
