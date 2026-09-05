# Rejected at Step 0: arXiv 1010.3338

Paper: Łukasz Kubat and Jan Okniński,
[*Gröbner–Shirshov bases for plactic algebras*](https://arxiv.org/abs/1010.3338).

## Decision

No generator is shipped. The paper supplies several exact, native witness
families that clear **G** and **V**, but none has a defensible **H** claim on
either track. This conclusion comes from the complete paper and its LaTeX
source, including every reduction in the proof of Theorem 1, not from the
abstract or the prior-triage description.

| requirement | result | reason |
|---|---:|---|
| G — generatable | pass in isolation | Start with a rank-3 normal word and apply reversible Knuth relations, or instantiate the infinite relation in Theorem 3. Both carry an exact certificate by construction. |
| V — verifiable | pass in isolation | Compare insertion tableaux, replay Knuth reductions, or reduce a polynomial with the stated finite basis; all use exact finite word operations. |
| H — Track A | **fail** | The paper gives a complete finite rewrite system at rank 3 and recalls the tableau normal-form algorithm. It proves no hardness, average-case result, or hard parameter regime for any inverse-generated distribution. |
| H — Track B | **fail** | The fixed critical-pair task is a constant lookup; the scalable Theorem 3 family is solved by the paper's displayed constant-cost pattern substitution; hiding a random rewrite history removes the only solver-visible compact route. |

The failure is specifically **H on both Track A and Track B**. It is not a
witness-rule failure, and it is not the bare observation that an efficient
algorithm exists.

## What the paper actually proves

The opening definition presents the rank-`n` plactic monoid by the four Knuth
relation schemes on an ordered alphabet. Words are ordered degree-first and
then lexicographically.

Theorem 1 gives the complete rank-3 Gröbner–Shirshov basis explicitly: eleven
binomials with leading words

`332, 322, 331, 311, 221, 211, 231, 312, 3212, 32131, 32321`.

Its proof lists all **27** overlaps and resolves both branches of every one.
Directly counting the displayed arrows gives **132 rewrite applications in
total**, with no branch longer than **6** applications. Corollary 2 then gives
the irreducible words explicitly as one of

`1^i (21)^j 2^k (321)^l (32)^m 3^q`

or

`1^i (21)^j (31)^k (321)^l (32)^m 3^q`.

The corollary also points to the standard tableaux algorithm for bringing any
word to its unique tableau form. Thus rank-3 word equality, binomial ideal
membership, and normal-form recovery are exactly the problems the paper makes
mechanical.

Theorem 3 treats rank greater than 3. It proves that every basis for the same
degree-lexicographic order is infinite by exhibiting, for every `i >= 1`, the
relation

`32 3^i 431 = 321 3^i 43`.

The proof does not merely assert existence: it displays the short Knuth
identities from which this formula follows and proves that no proper subword of
the left side can supply the required leading reduction.

## Required mechanical-cost versus compact-route audit

### 1. The finite rank-3 basis and its critical pairs

- **Mechanical certificate route:** read the eleven displayed binomials and
  replay the 27 displayed ambiguity checks: 132 exact word replacements total,
  at most 6 on either branch of one ambiguity.
- **Compact route:** the same eleven-binomial table and the same fixed ambiguity
  list. A solver may copy the paper's completed table, but there is no smaller
  parameter-dependent invariant to recover.
- **Gap:** constant versus constant. Rank 3 is fixed, so relabelling or adding a
  common word context creates no new critical-pair types. Disjointly repeating
  the table only lengthens both work and answer by the same factor.

This candidate also lacks an unlimited answer space: up to the required
order-preserving normalization of the three generators, the requested basis is
the same eleven binomials in every instance.

### 2. The scalable relation from Theorem 3

Run-length encoding makes the natural scalable object writable. For four
ordered letters `a < b < c < d`, the theorem's family is the single schema

`c b c^i d c a  ->  c b a c^i d c`.

- **Mechanical certificate route for this generated distribution:** inspect the
  six run records, recognize the displayed Theorem 3 schema, and permute three
  singleton runs while copying `i`. Even counting comparisons and record
  construction generously, this is **under 12 primitive operations**,
  independent of `i`.
- **Compact route:** exactly the same pattern recognition and substitution,
  again **under 12 operations**.
- **Measured cost:** one million direct constructions of the six-run right-hand
  side with 20-digit exponents took **0.564245 seconds** in local CPython, or
  **0.564 microseconds per certificate**.
- **Gap:** fewer than 12 operations versus the same fewer than 12 operations
  (ratio 1). Making `i` a million or a trillion increases only the digits copied;
  it does not increase certificate discovery.

Expanding `c^i` and quoting `Theta(i)` Schensted insertions would be a knowingly
weak baseline. The required construction-aware attack is the formula printed
in the paper, and it succeeds on every generated instance. Order-preserving
alphabet embeddings, common contexts, or a list of many such relations do not
defeat that attack: they respectively normalize away, copy unchanged, or repeat
the same substitution while making the answer longer. This is why the tempting
large-expanded-word formulation is not a legitimate Track B compression gap.

### 3. Arbitrary inverse-generated equivalent words

A different proposal is to sample a normal word first, apply many random Knuth
moves, hide the move history, and ask the solver to recover the normal form.
That passes G by transformation and V by exact tableau comparison. It still
does not rescue either hardness track:

- A standard Schensted/tableau pass computes the unique class representative in
  polynomial time (linear in expanded word length for fixed rank when the three
  letter counts in each row are maintained).
- The paper gives no distributional-hardness theorem for endpoints of a hidden
  Knuth random walk, so Track A is unsupported.
- The retained random move history is private generator state, not a structural
  insight present in the instance. Once hidden, there is **no solver-visible
  compact route** distinct from tableau insertion or rewriting. If breadcrumbs
  sufficient to reverse the history are published, mechanical recovery and the
  supposed shortcut are both the same one-step-per-move replay, and the obvious
  in-context reversal attack succeeds.

This is the same decisive dichotomy for polynomial ideal-containment variants.
An explicitly structured sum of basis multiples is undone by directly reading
that structure; after the decomposition is expanded and hidden, fixed-basis
normal-form reduction remains available but the generator's private summands do
not become a discoverable compact route.

## Easy regimes and excluded surrogates

The paper's division is itself an easy-regime warning:

- rank 3 has the finite complete rewrite system of Theorem 1 and the explicit
  normal forms of Corollary 2;
- rank greater than 3 lacks a finite basis for this order, but Theorem 3's
  obstruction witness is an explicit formula, not a hard search problem;
- rank below 3 coincides with the related Chinese-algebra case mentioned at the
  end and supplies no harder regime.

No SAT, graph, finite-field, or integer-lattice encoding is central to this
paper. Adding one would be a benchmark-convenience reduction whose hardness
comes from the surrogate, while the solver would no longer manipulate the
paper's words, tableaux, or noncommutative polynomials.

## Reconsideration criterion

This paper could be reopened only with an additional result that supplies one
of the missing ingredients: either distributional hardness for a precisely
specified family of plactic normal-form/ideal-membership instances (Track A),
or a paper-native structured distribution where the best construction-aware
algorithm has large measured cost and the instance exposes a genuinely shorter
route that is not the generator's hidden rewrite history (Track B). Neither is
present in arXiv:1010.3338.
