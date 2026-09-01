# Rejected: arXiv:2606.02541

Paper: Jacob Fox and Zach Hunter, [*Three-color van der Waerden numbers grow
super-exponentially*](https://arxiv.org/abs/2606.02541), arXiv:2606.02541v1.

## Decision

I did not create `gen_2606_02541.py`.  The paper's native witness problem does
not meet the required G/H/V combination, and replacing its complete family of
arithmetic progressions by a planted list of selected constraints would be a
different, generic hypergraph-coloring problem whose hardness does not come from
this paper.

| Requirement | Result | Reason |
|---|---:|---|
| G - inverse-generatable | **fail** | A native instance is only `(N, k, r)` (or a specified abelian group and `k, r`).  It contains *every* relevant arithmetic progression.  Sampling a coloring first does not create or vary that instance, and an arbitrary sampled coloring almost never avoids all progressions.  The paper proves existence after fixing the group; it does not construct the problem around a sampled answer. |
| H - hard | **not established** | Theorems 1, 2, 4, and 5 are extremal existence/lower-bound results, not computational-hardness results.  The paper gives no NP-hardness theorem, search lower bound, or hard finite parameter window.  Treating a large van der Waerden number as evidence of computational search hardness would be unjustified. |
| V - exact verification | **formal pass, practical fail in the theorem regime** | A proposed coloring can be checked exactly by scanning all progressions.  For an explicit interval this involves about `N^2/(2(k-1))` progressions and an answer of `N` color symbols.  In the only regime supported by the main theorem, `N >= 2^(k log* k / 4)` and `k` is sufficiently large, so neither materializing the witness nor performing the scan is a usable generator/checker operation. |

Because G and H fail (and practical V fails in the supported regime), Step 0's
instruction to reject and stop applies.  No self-test or LLM-hardening transcript
was manufactured.

## What the paper actually defines

Section 1 defines `w(k; r)` as the least `N` for which every `r`-coloring of
`[N] = {1, ..., N}` has a monochromatic `k`-term arithmetic progression.  Section
2 uses the cyclic version: in an abelian group a `k`-AP is
`a, a+d, ..., a+(k-1)d` with nonzero `d`.  The most natural witness would therefore
be a complete coloring of `[N]` or `Z_N` with no monochromatic `k`-AP.

Theorem 1 only states that, for sufficiently large `k`, such a three-coloring
exists for an interval of length `2^(k log* k / 4)`.  The proof in Section 5 goes
through Theorem 4: for a fixed sufficiently small `epsilon` and positive `b`, it
requires

```text
k >= T_(3b)(1/epsilon),
q_i distinct primes in [2^(0.9k), 2^(0.9k+1)],
N = product(q_i).
```

Thus the theorem-backed parameters are far outside any range in which a standard-
library module can emit the explicit coloring or exhaustively verify it.

## Constructions and easy/unsupported regimes checked

- Section 2 begins with the explicit Erdos-Turan digit construction: for prime
  `p`, the integers whose base-`p` expansion omits digit `p-1` are `p`-AP-free.
  Lemma 2.2 gives the corresponding product construction in cyclic groups.  A
  proposed generator based directly on this rule would expose a closed-form
  witness and fail H.
- Lemmas 2.8 and 2.9 are probabilistic hitting-set constructions.  Lemma 2.9
  samples residue classes and proves success by a union bound, but requires
  `k >= exp(36/epsilon)` and allows `N` as large as `2.5^k`.  It is not inverse
  planting, and exact validation again requires scanning a huge AP family.
- Corollary 3.3 obtains suitable set-colorings from the Lovasz local lemma.
  This is an existence result after the group has been fixed, not a sampled-answer-
  first instance generator or a hardness theorem.
- Lemmas 4.1-4.3 give product and random-shifted product constructions.  Supplying
  the factor colorings/shifts as instance data would reveal a direct construction;
  omitting them leaves the module with the same nonconstructive base-coloring
  problem.
- Section 1.2 explicitly says only that the techniques are *suspected* to be
  implementable for small van der Waerden lower-bound constructions.  Therefore
  using practical small `k` would leave the paper's proved regime and would not
  support an H claim.

## Why the tempting planted variant was not used

One can sample a coloring and then retain only arithmetic-progression constraints
that are nonmonochromatic under it.  That produces a planted uniform-hypergraph
coloring/CSP instance.  It is not the paper's complete AP-coloring problem, since
the statement must now include an arbitrary selected edge list.  Its difficulty
would come from generic hypergraph colorability, while the selection process can
also leak the planted partition statistically.  Calling that a family from this
paper would overstate both provenance and hardness.

