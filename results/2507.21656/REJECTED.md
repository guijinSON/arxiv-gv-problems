# Rejected at Step 0: arXiv 2507.21656

Paper: Tomasz Kościuszko, [*Schur-like numbers and a lemma of
Shearer*](https://arxiv.org/abs/2507.21656) (2025).

## Decision

No generator is shipped. The paper's native objects are colourings of
`[N] = {1,...,N}` and monochromatic solutions of additive equations. Those
objects give cheap exact witnesses, but none of the paper-backed tasks clears
G, H, and V together.

- **Track A fails H.** Given a colouring, a monochromatic witness for
  `x1+x2+x3=y1+y2` is found by the standard pair-sum/triple-sum hash join in
  polynomial time. The paper proves extremal upper bounds, not hardness of
  this search or average-case hardness of a planted distribution.
- **Track B also fails H for the native constructions.** The paper's explicit
  interval colouring is produced by the same short recurrence available to
  the solver. If one plants a single violation in it, the best compact route
  is the same linear scan that locates the defect; there is no paper-derived
  sub-300-operation shortcut. Lemma 5's lifting operation is itself the whole
  algorithm, so its mechanical and compact routes are also identical.
- Asking for a whole avoiding colouring additionally reaches the 256-atom
  answer cap at `N=256`. Compressing it to interval endpoints removes that
  output problem but makes the answer a direct evaluation of the displayed
  construction.

This is an H rejection, not a witness-rule rejection. A five-integer equation
solution is verified by five range/colour checks and one exact integer
equality. A proposed colouring can likewise be verified exactly by forming
pair and triple sums inside each colour. The obstruction is that the same
polynomial-time computation produces the witness, while the paper supplies no
distinct compact route that could support Track B.

## What the paper actually proves

Section 1 defines `S_k(n)` as the least `N` for which every `n`-colouring of
`[N]` contains a monochromatic solution of

`x1 + ... + x_(k+1) = y1 + ... + y_k`.

Variables are not required to be distinct. This is used explicitly in Lemma 5,
which repeats variables when lifting a shorter equation, and in Lemma 6, which
treats a triangle as a five-cycle by traversing an edge back and forth.

Theorem 4 proves that a colouring avoiding `x1+x2+x3=y1+y2` has
`N=O(sqrt(n!))`. Its proof turns each colour class `A_i` into the distance graph
on `[N]` with an edge `uv` when `|u-v|` lies in `A_i`, applies Shearer's
independence-number lemma, and repeatedly chooses an independent set. The
theorem is an asymptotic impossibility statement: its hidden constant does not
give a finite input threshold from which this generator could manufacture a
witness without searching for one.

Theorem 5 gives the stronger factorial saving for the 21-variable equation
`x1+...+x12=y1+...+y9`. Lemmas 5 and 6 are the constructive parts: a short
additive relation is duplicated/padded to the long equation, and a 3- or
5-cycle in a distance graph supplies such a relation. This transformation is
fully explicit and costs only the length of the output.

Section 4 treats other non-invariant equations. Theorems 6--8 use repeated
applications of Schur's theorem and an auxiliary-colour promotion procedure.
They establish finite upper bounds, but on an arbitrary explicit colouring the
procedure still has to find monochromatic Schur triples. There is no
solver-visible invariant that replaces that scan.

Most importantly for generation, Section 1 also says what is easy. For
`x1+x2+x3=y1+y2`, colour successive geometric intervals with ratio `1.5`.
Inside an interval `[L,1.5L)`, every three-term sum is at least `3L` while every
two-term sum is strictly below `3L`, so the colouring is valid by inspection.
This gives the natural answer-first certificate, but it is also the solver's
direct construction.

## Candidate-family audit

| Native task | G | V | H outcome |
|---|---|---|---|
| Output an avoiding colouring of `[N]` | Yes: use the Section 1 ratio-`1.5` intervals | Exact sum-set comparison | Fails both tracks: the displayed recurrence constructs the answer directly |
| Output interval endpoints certifying that colouring | Yes | Expand the intervals and compare exact integer sums | Fails both tracks: about `log_1.5(N)` recurrence steps mechanically and compactly |
| Find a monochromatic 3-versus-2 solution in a given colouring | Yes only after inverse planting, unless an explicit theorem threshold is supplied | Five integer checks | Track A fails because pair/triple sum matching is polynomial; the natural plant also fails G6 |
| Lift a short solution to the 12-versus-9 equation | Yes, by Lemma 5 | Substitute and add | Fails both tracks: duplicating/padding the tuple is the explicit formula |
| Return the large independent set used in Theorem 4 | Not from the theorem without carrying out an independent-set search; inverse planting is possible | Edge scan | No hard generated distribution or compact paper-derived route is proved |
| Return an upper-bound proof/certificate for a colouring | Not as a bounded executable witness | The paper proof is not an instance-local certificate language | Fails V in the required form |

## Mechanical cost versus compact route

I measured the most favourable natural Track B attempt rather than rejecting
merely because an algorithm exists. Start from the paper's geometric-interval
colouring, choose an even `a`, put `b=3a/2` into `a`'s colour, and retain the
known witness `(a,a,a;b,b)`. The construction is inverse generation, and all
uncorrupted intervals remain solution-free by the Section 1 inequality.

A construction-aware attack checks even `a` in increasing order and tests
whether `colour(a)=colour(3a/2)`. It recovered a verified witness on **100/100**
seeds at every measured size. Timings use standard-library Python 3 in this
workspace; the operation count is the number of candidate ratios inspected.

| `N` | interval colours | attack successes | ratio checks, min / median / max | median / max wall time |
|---:|---:|---:|---:|---:|
| 256 | 13 | 100/100 | 2 / 42 / 84 | 0.00000223 / 0.00000456 s |
| 4,096 | 20 | 100/100 | 26 / 664 / 1,329 | 0.00004681 / 0.00023132 s |
| 16,384 | 23 | 100/100 | 101 / 2,653 / 5,313 | 0.00020215 / 0.00041693 s |
| 65,536 | 27 | 100/100 | 403 / 10,610.5 / 21,250 | 0.00079984 / 0.00162284 s |

At the representative explicit-input size `N=16,384`, the **mechanical cost**
is a median 2,653 equality tests plus constant-time arithmetic. The **compact
route** is no shorter: because the defect location is drawn uniformly and the
colour vector contains no additional side channel, a solver must inspect the
same entries to locate it, followed by the same one multiplication and one
division. The mechanical/compact ratio is therefore 1. Rendering the colouring
as run-length intervals would expose the single exception immediately; hiding
it behind an extra code or checksum would make that invented encoding, not the
paper's additive-combinatorial structure, the entire puzzle.

For the avoiding-colouring task, the largest witness permitted by G9(c) has
`N=256`. The mechanical route assigns 256 interval colours and writes 256
atoms; the compact route must write the same 256 atoms, again a ratio of 1.
Using endpoints instead takes 13 recurrence steps at this size (27 at
`N=65,536`) in both routes. Lemma 5's 12-versus-9 certificate takes 21 output
placements in both routes. These are short formulas, but unlike a valid Track B
family there is no large mechanical computation that a separate insight
compresses.

## Why random or more carefully hidden planting does not repair the claim

A random colouring avoids the visible single-defect signature, but it produces
many witnesses. In a structure-aware experiment, I first generated a uniform
random colouring, then repeatedly chose a colour and five members of that
colour (with repetition, as the definition allows). Direct substitution gave:

| `N` | colours | valid random candidates / candidates | observed density |
|---:|---:|---:|---:|
| 4,096 | 20 | 106 / 800,000 | 1.325e-4 |
| 16,384 | 23 | 28 / 800,000 | 3.5e-5 |
| 65,536 | 27 | 8 / 800,000 | 1.0e-5 |

All three fail G4's `1e-6` requirement, and the standard sum-matching algorithm
finds one of these abundant witnesses rather than the plant. Making `N` much
larger may reduce this density, but it does not create a compact route: the
solver and the reference algorithm still perform the same search over the
explicit colouring. Conversely, placing the violation in an otherwise
structured avoiding colouring creates exactly the valuation, interval-width,
or position outlier that G6 requires the builder to attack.

One could invent a checksum, cryptographic encoding, or special labelling that
reveals a hidden five-tuple in under 300 operations while a generic sum matcher
does much more work. That would be a Track B puzzle about the added encoding.
No such encoding, invariant, or change of variables occurs in this paper, so it
cannot honestly be presented as coverage of its native mathematics.

## Gate outcome

| Requirement | Result | Evidence |
|---|:---:|---|
| G -- known certificate by construction | Possible in isolation | Section 1 interval colouring, inverse planting, or Lemma 5 lifting |
| H -- Track A structural hardness | **Fail** | Polynomial pair/triple-sum matching; no theorem for a hard generated distribution; the natural plant is recovered 100/100 |
| H -- Track B no-tool compression | **Fail** | Mechanical and compact routes have ratio 1 for the native constructions and the single-defect family |
| V -- exact witness checking | Pass in isolation | Integer range, colour, and sum comparisons |
| G4 -- guess resistance | **Fail for random colourings at tested explicit sizes** | Densities from `1.0e-5` to `1.325e-4` |
| G9(c) -- answer size | **Fail for full colourings beyond `N=256`** | One atomic colour per integer |
| Overall | **Rejected at Step 0** | No one family clears G, H, and V under either track |

No module, self-test report, or oracle transcript was created. That is
intentional: Step 0 requires stopping before implementation when a gate fails,
and oracle failures cannot manufacture the missing Track A theorem or Track B
compression gap.
