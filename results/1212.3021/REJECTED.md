# Rejection: arXiv 1212.3021

Paper: [Momihara and Yamada, *Divisible difference families from Galois rings
GR(4,n) and Hadamard matrices*](https://arxiv.org/abs/1212.3021).

## Decision

The prior-triage family—construct the two Galois-ring blocks and return them as a
divisible difference family—passes G and V but fails H on Track A.  It also does
not have the mechanical-versus-compact gap required for Track B at any size whose
answer fits the output cap.  No generator module was built.

The paper's only genuinely open search task, Problem 4.3, asks for DDFs different
from the Theorem 3.1 family.  That task fails G here: the paper supplies neither a
theorem-backed construction of such new families nor a bounded certificate that
can be sampled first.  Generating one would mean solving the open construction
problem.

## STEP 0 findings

Definition 1.1 fixes the exact witness condition.  For blocks `D_i` in a finite
abelian group, the checker counts ordered quotients `x*y^-1` within each block and
requires one multiplicity on the nonidentity elements of the distinguished
subgroup and another multiplicity outside it.  This is finite and exactly
checkable, so V is not the problem.

Lemma 2.1 is the certificate-producing algorithm.  From an additive difference
set `D`, it explicitly forms each new block as
`D_(i,y) = y^-1 (D_i - 1) intersect N`.  Section 3 then specializes this formula
to `GR(4,n)`.  Theorem 3.1 states that for `N=D` the two resulting blocks live in

`G = Z_(2^n-1) x Z_2^(n-1)`

and each has size

`k = 2^(n-1) (2^(n-1) - 1)`.

Its proof is constructive: choose the two coset representatives and evaluate
`y^-1(D-1) intersect D`.  Example 3.3 even writes both blocks out completely for
`n=3`.  Proposition 3.4 supplies additional direct signatures—one block is closed
under inversion, the other contains no inverse pair, and both have prescribed
layer sizes.  These results make recovery easier; the paper contains no hardness
theorem or hard parameter regime to counterbalance them.

Theorem 4.1 is likewise an explicit block-matrix construction.  Given a DDF and a
Hadamard matrix, it fills the claimed symmetric Hadamard matrix entry by entry.
Remark 4.2(1) additionally says that the classical Goethals–Seidel theorem already
constructs the same orders from a Hadamard matrix alone.  Thus this route does not
provide a hidden hard witness problem either.

## Why neither track works

For the native Theorem 3.1 answer, the cap calculation is:

| extension degree `n` | `|G|` | elements per block `k` | two-block answer atoms |
|---:|---:|---:|---:|
| 2 | 6 | 2 | 4 |
| 3 | 28 | 12 | 24 |
| 4 | 120 | 56 | 112 |
| 5 | 496 | 240 | 480 (over the 256-atom cap) |

At the largest admissible row, `n=4`, the theorem's direct mechanical procedure
enumerates 120 elements of `D` and performs two shifted-membership tests per
element, hence 240 block-membership tests, before emitting 112 group elements.
The exact verifier would count `2*k*(k-1) = 6,160` ordered differences, but that is
verification cost, not certificate-search cost, and cannot be used as evidence of
hardness.

The compact route is the same displayed construction from Lemma 2.1/Theorem 3.1:
it still examines the 120 group elements and materializes the same 112 outputs.
So both routes are linear in the answer length and differ, at most, by a small
constant factor; there is no invariant or change of variables replacing a large
mechanical computation.  The next degree is not a harder shipping instance—it is
simply unwritable under the stated cap.

- **Track A fails H:** an explicit linear-size construction produces the
  certificate on every generated instance.  Claiming generic DDF search hardness
  would ignore the generated distribution and the theorem that defines it.
- **Track B fails H:** mechanical cost is 240 membership tests plus output, while
  the purported shortcut is that same 240-test construction plus output.  The
  compact route is not asymptotically or practically shorter, and the work is
  comparable to the 112 atoms the solver must transcribe.
- **G and V alone pass:** Theorem 3.1 plants valid blocks without solving an
  instance, and Definition 1.1 permits exact difference recounting.

## Alternatives considered

Proposition 3.5 gives a cyclic difference set of size `2^(n-1)-1`; under the atom
cap its construction still scans at most 511 group elements to output 255 of them,
again the same linear route with no compression gap.  Returning the Hadamard
matrix from Theorem 4.1 is worse: the concrete matrix answer grows quadratically
in its order and immediately becomes a transcription/cap test.

Hiding a known block among random decoys, asking for an affine relabelling, or
bundling many independent orientation bits could create guess resistance, but
those are benchmark wrappers not studied or licensed by the paper.  Their
hardness would come from the added recovery/CSP layer, not from the Galois-ring DDF
construction, so they were not used to manufacture a Track A claim.

