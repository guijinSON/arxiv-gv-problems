# Rejected: arXiv:2012.10803

This paper was read in full.  The attempted native family is retained as
`rejected_gen_2012_10803.py`, and its measured local gates are in
`selftest_report.json`.  It must not be shipped.

## Decision

**G passes and V passes, but H cannot honestly be claimed on either track; the
attempted family also fails the gated G9(c) effort cap.**

- **G:** Section 6 of [Colò--Kohel, *Orienting supersingular isogeny
  graphs*](https://arxiv.org/abs/2012.10803) defines the private bounded exponent
  vector.  The retained generator samples that vector first and then multiplies
  the corresponding ideal classes, so it uses inverse generation rather than
  solving its output.
- **V:** The witness is the bounded exponent vector.  Verification performs exact
  Gaussian-residue multiplication modulo `3^d` and an exact quotient-class
  comparison.  The planted witness verified in 16/16 preset/seed checks, and all
  five corruptions were rejected for distinct reasons.
- **Track A fails audit:** Theorem 7 supplies the class-group action, but it is not
  a distributional hardness theorem.  Section 5.1 explicitly identifies the
  smooth quotient and its order-3 filtration, and the known attack starts by
  taking discrete logarithms in that quotient.  The retained panel's basic exact
  LLL embedding failed on 0/8 instances, but it does not implement the stronger
  BKZ/relation-lattice attack of Dartois--De Feo, [*On the Security of
  OSIDH*](https://www.iacr.org/archive/pkc2022/131770037/131770037.pdf), which
  practically breaks the paper's proposed parameter sets.  Omitting the strongest
  known class of attack means the required Track-A claim is not established.
- **Track B also fails:** recognizing the smooth cyclic quotient is not a compact
  solution.  It only converts the problem to a bounded modular subset-sum, which
  still has to be solved.  There is no short change of variables, invariant, or
  symmetry that recovers the planted vector from these independently sampled
  public classes.

## Mechanical cost versus compact route

At the attempted shipping preset (`n=40`, exponents in `[-5,5]`, class-group
order about 145 bits), Pohlig--Hellman preprocessing alone took
**459,092--460,444 exact group operations** and **0.60--0.89 seconds** over eight
seeds.  The subsequent exact LLL embedding took **6,406--7,437 iterations**; the
complete audited attack took **3.45--6.00 seconds** and found no witness.  Full
enumeration would inspect `11^40 = 452592555681759518058893560348969204658401`
bounded vectors.

The **compact route length is not smaller**: no complete compact route is known.
Even after the intended cyclic-group insight, the route begins with at least the
same **459,092 operations**, and an unresolved subset-sum remains.  The earlier
figure of 242 operations was only the cost of *checking an already supplied
witness*; counting it as a solution route would confuse V with H.  Thus the real
lower bound is over 1,500 times G9(c)'s 300-operation cap before the remaining
search is counted.  This is calculator/search difficulty, not no-tool
compression.

## Paper regimes checked

- Definitions 2--3 fix orientations and isogeny chains; Lemma 4 relates
  non-backtracking chains to cyclic composed isogenies.
- Theorem 7 gives the class-group torsor used by the attempted construction.
- Proposition 15 in Section 4 reconstructs modular isogeny chains from
  `j`-invariants, while the modular-ladder method uses polynomial gcds.  Those
  native path variants therefore retain substantial finite-field polynomial
  arithmetic and do not provide a sub-300-operation shortcut either.
- Section 5.1 gives the exact residue quotient and explains why revealing the
  full descending chain makes recovery polynomial via its small successive
  kernels/Pohlig--Hellman.
- Sections 5.2 and 6 define the OSIDH bounded private exponents and discuss their
  security regime, but do not give a theorem establishing hardness for the
  inverse-generated distribution used here.

The tempting prior-triage proposal--plant a secret isogeny walk and verify its
composition--has the same defect more starkly: generation and verification are
valid, but a no-tool solver has neither a compact way to discover the walk nor a
credible Track-A theorem for the planted distribution.

## Recorded evidence and external blocker

The structure-aware guess test observed 0 valid witnesses in 200,000 uniform
bounded vectors.  Six local attacks all had 0/8 successes.  These are useful
negative measurements, not a substitute for the missing BKZ audit or a compact
solution route.

The prescribed oracle harness was also invoked, but every redraw returned HTTP
403 `Key limit exceeded`; the script-owned `llm_loop_transcript.jsonl` records
those errors and `.meta.json` contains no hardness verdict.  API errors were not
counted as model failures.  This external failure is not the reason for rejection:
the intrinsic G9(c)/track analysis above already rules out the family.
