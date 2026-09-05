# Rejected at Step 0: arXiv 1803.01480

Paper: Curtis Bright, [*A doubling construction for Williamson
matrices*](https://arxiv.org/abs/1803.01480) (2018).

## Decision

No problem family from this paper clears **G + H + V**.  The natural task—given
four odd-order Williamson sequences, output the doubled quadruple—is
theorem-backed and exactly verifiable, but it fails **H on Track A** because
Theorem 1 is itself an explicit linear-time certificate-producing algorithm.
It also fails **H on Track B**: at every writable size, the mechanical route and
the compact route are the same three sequence operations.  There is no
mechanical-versus-compact compression gap.

Implementation therefore stopped before Step 1, as the task requires.  No
generator, self-test report, or oracle transcripts were fabricated.

## What the paper actually defines

Section 1 defines Williamson matrices as four symmetric circulant sign matrices
of order `n` satisfying

`A^2 + B^2 + C^2 + D^2 = 4n I_n`.

Because a circulant matrix is determined by its first row, Section 2.1 gives the
equivalent native sequence formulation.  Four symmetric sign sequences are
Williamson exactly when the sum of their periodic autocorrelations is zero at
every shift `1,...,floor(n/2)`.  Thus a proposed quadruple is a finite witness:
a checker can verify signs, symmetry, and all autocorrelation identities using
exact integer arithmetic.

Section 2.2 defines the three operations used by the construction: entrywise
negation, cyclic shift, and perfect-shuffle interleaving.  For odd `n`, a prime
denotes a shift by `(n-1)/2`.

Theorem 1 then says that an odd-order Williamson quadruple `(A,B,C,D)` maps to

`A interleave B',  (-A) interleave B',  C interleave D',  (-C) interleave D'`.

The proof checks even correlation shifts by reducing them to twice the source
Williamson identity.  At odd shifts, the two members of each displayed pair
cancel.  This is a composition-of-identities certificate, but it is also the
complete algorithm for producing the requested object.

## Step-0 mechanical cost versus compact route

I used the largest odd source order that could fit a natural full-sequence
answer under the task's 256-atom cap: `n=31`.  The target has order `62`, and
the four output sequences contain `8n = 248` sign atoms.

A straightforward implementation of Theorem 1 performs:

- `2n = 62` symbol copies to materialize the two shifted sequences;
- `2n = 62` arithmetic sign negations; and
- `8n = 248` output assignments for the four interleavings.

That is **372 elementary symbol operations**, including only **62 exact
arithmetic operations**.  In a standard-library Python microbenchmark (nine
batches of 20,000 calls, deterministic symmetric sign inputs), the median was
**0.000006381572 seconds per construction**.  Williamson validity does not
affect this timing because the routine only indexes, negates, and interleaves
the supplied signs.

The compact route is not shorter: it is precisely the same shift-negate-
interleave formula, with the same 62 negations and the same unavoidable 248
emitted signs.  The mechanical/compact operation ratio is therefore **1**.  A
streaming implementation can avoid the 62 temporary shift copies, but it
shortens both routes equally.

For comparison, the smallest nontrivial illustrative source order `n=3` needs
24 output signs and 36 operations by the same accounting; it is plainly a
by-hand substitution exercise.  Increasing `n` merely lengthens that identical
substitution until the answer cap is reached.  It never opens a Track-B gap.

The formal symmetric-sign candidate space at `n=31` is large—four symmetric
sequences of order 62 have `4(31+1)=128` free signs—but this does not establish
difficulty.  The theorem maps the supplied source directly to one valid member
of that space in microseconds.

## Why neither hardness track applies

### Track A

The paper proves no computational-hardness or average-case-hardness result for
finding Williamson sequences.  More decisively, on the theorem-backed
distribution the witness is output directly by Theorem 1 in `O(n)` time.  A
large ambient answer space cannot override that construction.

### Track B

The paper's structural insight is exactly the executable procedure: shift `B`
and `D`, negate `A` and `C` for the paired outputs, and interleave.  There is no
separate standard computation with millions of operations and no shorter
invariant-based decoder.  The measured mechanical route and the compact route
are the same algorithm and have the same length.  Hiding the formula from the
problem statement would test recall or rediscovery of a 372-operation
substitution, not no-tool compression of a costly method.

The remark after Theorem 1 also rules out an apparent scaling escape: this
doubling cannot be iterated.  Its symmetry argument requires an odd source
order, whereas the result has even order.  Scaling would therefore require a
new supply of odd-order Williamson quadruples from outside this theorem.

## Other native witness tasks considered

| Candidate task | Gate failure | Reason |
|---|---|---|
| Given an odd Williamson quadruple, output its doubled quadruple | **H, Tracks A and B** | Theorem 1 outputs it in linear time; mechanical and compact routes coincide. |
| Given a doubled quadruple, recover an odd precursor | **H, Tracks A and B** | Deinterleave the even and odd coordinates and undo the fixed shift; this is the same linear-size work as writing the precursor. |
| Complete erased entries in a displayed doubled quadruple | **H** | Each erased sign is copied or negated from a supplied source coordinate by the displayed formula. |
| Certify that a supplied quadruple is Williamson | **H** | Exact autocorrelation recomputation verifies an already supplied object; it does not expose a large witness search. |
| Output the four full circulant matrices instead of their first rows | **G9(c)** | At target order 62 this would contain `4*62^2 = 15,376` sign atoms, far above the 256-atom cap, while remaining explicitly constructible. |
| Find a Williamson quadruple from the order alone | **G / H unsupported** | Theorem 1 needs an odd-order source and supplies no scalable generator for those sources; the paper gives no hard parameter regime for generic Williamson search. |
| Hide one constructed quadruple among decoys or add random partial constraints | **Paper support / H unsupported** | That creates a new selection or completion distribution not studied by the paper.  Its hardness would come from the added surrogate, not the doubling theorem. |

## Gate diagnosis

| Requirement | Result |
|---|---|
| G — certificate known by construction | **Passes in isolation:** Theorem 1 constructs the doubled sequences from a supplied odd-order quadruple. |
| V — exact witness verification | **Passes in isolation:** check signs, symmetry, and periodic autocorrelation sums over the integers. |
| H — Track A structural hardness | **Fails:** the certificate-producing algorithm is the explicit `O(n)` construction, and no hard generated distribution is proved. |
| H — Track B no-tool compression | **Fails:** 372 mechanical symbol operations versus the identical 372-operation compact route at the maximum writable natural size; measured median 6.38 microseconds. |
| Scalable native supply | **Fails for this theorem alone:** the paper explicitly says the construction cannot be applied repeatedly. |
| Overall | **Rejected at Step 0.** |

This rejection is not based merely on an efficient algorithm existing.  It is
based on measuring the paper's certificate-producing algorithm at the largest
writable natural instance and finding that it is already the compact route;
there is nothing further for structural insight to compress.
