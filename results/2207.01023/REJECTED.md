# Rejection: arXiv 2207.01023

## Decision

No family is shipped.  The native construction clears **G** and **V**, but it fails
**H on Track A**, and the natural compressed versions also fail **H on Track B**.
The obstruction was found at Step 0, before writing a generator.

Paper: Mirko Horňák, [*On the achromatic number of the Cartesian product of two
complete graphs*](https://arxiv.org/abs/2207.01023).

## Native object and certificate

Proposition 2 identifies a proper complete colouring of
`K_p square K_q` with a `p` by `q` colour matrix: every row and column has distinct
entries, and every unordered pair of colours occurs together in some row or column.
This is the exact native object; no graph or finite-field surrogate is needed.

Lemma 5 in Section 2 gives a constructive matrix from a projective plane of order
`r`.  It first lists the `r^2+r+1` projective lines, tags the `r+1` occurrences of
each point, and expands every tagged incidence to a cyclic block of length `s`.
For `s >= r+1`, this produces a row-complete proper colouring of

`K_(r^2+r+1) square K_((r+1)s)`

with `(r^2+r+1)s` colours.  Theorem 6 and Corollary 7 in Section 3 prove that this
number is optimal when `s >= r^3+1` (and the residue parameter is zero).

Thus G is available by theorem-backed construction, and V is cheap and exact:
check the projective-plane incidences, expand the cyclic blocks, check row/column
distinctness, and check pair coverage.  The failure is hardness, not witnesshood.

## Why Track A fails

The paper does not provide a hard distribution of colouring instances.  Its
positive regime is precisely the easy one: `r` is a finite-projective-plane order,
and all currently known positive orders noted by the paper are prime powers.  In
that regime the standard coordinate plane `PG(2,r)` and Lemma 5 give the certificate
directly in polynomial time.  For prime `r`, lines can be emitted as
`y = m*x+b`, the vertical lines, and the line at infinity.

The Introduction's NP-completeness statement concerns determining the achromatic
number of arbitrary trees.  It says nothing about this generated distribution of
complete Cartesian products equipped with a prime-power projective-plane
construction.  Claiming Track A from that worst-case result would therefore be
invalid.

Planting a matrix and applying row, column, vertex, or colour permutations does not
repair this: a solver may ignore the plant and emit the same canonical `PG(2,r)`
construction.  Such relabellings also describe one canonical problem rather than
seed-diverse instances.  Adding arbitrary precolouring constraints to force recovery
of the planted relabelling would create a convenience CSP not studied or licensed
by this paper.

## Mechanical cost versus compact route (Track B audit)

I implemented the displayed coordinate construction transiently and counted one
finite-field multiplication or addition per coordinate operation and one modular
addition per emitted colouring entry.  Timings are medians of 21 runs on this
machine; they exclude import/startup time.

| candidate witness | theorem parameters | atoms | mechanical algorithm | measured mechanical cost | compact route |
|---|---:|---:|---|---:|---:|
| full colouring matrix | `r=2, s=9` (smallest exact Corollary 7 regime) | 189 | coordinate Fano plane + Lemma 5 cyclic expansion | 205 modular operations, 0.0000085 s | the identical construction: 205 operations and 189 values to write |
| projective-plane incidence descriptor | `r=5, s=126` | 186 | emit `PG(2,5)` by affine lines, verticals, and infinity | 250 field operations (full descriptor plus expansion built in 0.000738 s) | the identical coordinate formula: about 250 operations and 186 values to write |
| full colouring matrix | `r=5, s=126` | 23,436 | coordinate plane + Lemma 5 cyclic expansion | 23,686 modular operations, 0.000738 s | no shorter writable route: all 23,436 entries remain part of the answer |

The compact incidence descriptor is executable as a certificate because a checker
can expand it and verify the matrix.  It is also the strongest possible Track B
candidate here: 186 atoms and 561 compact-JSON characters fit G9(c).  Nevertheless,
its mechanical route and insight route are the same 250-operation coordinate
enumeration.  There is no million-operation mechanical method versus a dozen-step
invariant; there is nothing shorter to discover.

Conversely, retaining the paper's full matrix creates no compression gap either.
At `r=5, s=126` it has 23,436 atoms and about 110,583 compact-JSON characters, far
beyond G9(c)'s 256-atom and 2,000-character caps.  The output itself forces at least
23,436 writes, so a purported shortcut cannot meet the no-tool contract.  At the
smallest exact case, `r=2, s=9`, the entire standard construction is already just
205 operations, essentially the same length as its 189-entry output (the other
`r=2` exact cases that fit the cap have the same issue).

The other native question, the optimum value in Corollary 7, is even more direct:
`(r^2+r+1)s` is obtained by a constant number of integer operations.  A certified
numeric answer would therefore have equal mechanical and compact costs as well.

## Failed gate

- **G:** passes by Lemma 5 / Corollary 7 construction.
- **V:** passes by finite exact incidence, distinctness, and pair-coverage checks.
- **H / Track A:** fails because the shipping distribution has the explicit
  polynomial-time projective-coordinate construction.
- **H / Track B:** fails because the compact route is no shorter than that
  construction.  Full native witnesses instead exceed the output cap as soon as
  the mechanical work becomes large.

Accordingly, running the builder, adversary panel, and oracle hardening loop would
only rediscover the explicit Section 2 construction or measure transcription.  The
paper is rejected at triage rather than represented by a non-native planted-recovery
problem.
