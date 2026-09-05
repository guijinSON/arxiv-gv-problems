# Rejected at Step 0: arXiv 1001.3546

Paper: Hilden, Lozano, and Montesinos-Amilibia, [*On representations of
2-bridge knot groups in quaternion algebras*](https://arxiv.org/abs/1001.3546)
(2010).

## Decision

No self-contained family justified by this paper clears **G + H + V**.  Exact
verification is easy, but the paper creates a sharp incompatibility between
generation and hardness:

- If a character point `(x,y)` is supplied, Theorems 3 and 4 give the
  representing quaternions by fixed explicit formulas.  This passes G and V but
  fails **H on Track A**, and the mechanical and compact routes are the same
  constant-size calculation, so it also fails **H on Track B**.
- If only a 2-bridge presentation is supplied, finding a nontrivial irreducible
  character point is the polynomial-system problem that the generator would
  have to solve.  The paper does not provide an inverse construction for such a
  point over a scalable family; its examples use Mathematica.  This fails G if
  placed in `make_instance`.
- The one theorem-backed construction available uniformly for all standard
  2-bridge knot presentations is the reducible branch of Proposition 9.  There
  `A = B`, so the same fixed witness works independently of the knot and the
  obvious by-hand ansatz succeeds on every instance.  This passes G and V but
  fails H on both tracks.

This is therefore a Step-0 rejection, not a Track-A rejection made merely
because some algorithm exists.  Both the constant-size route and the tempting
long-relator Track-B variant are costed below.  Implementation stopped before
Step 1 as the task requires; no generator, self-test report, README, or oracle
transcript has been fabricated.

## Exact paper objects and the certificate-producing algorithms

Section 4 defines a c-representation of

```text
G = <a,b : w(a,b)>
```

to be a homomorphism into the unit group of a quaternion algebra for which the
images `A` and `B` are conjugate.  Its character coordinates are

```text
x = A+ = B+,
y = -(A- B-)+.
```

Theorem 3 answers the certificate question explicitly.  Put `u = 1-x^2` and
write left multiplication by `A` and `B` in the quaternion basis
`{1,A-,B-,(A-B-)-}`.  The paper displays two universal 4-by-4 matrices
`m(A)` and `m(B)` whose entries are polynomials in `x,y`.  Evaluating the
relator and taking

```text
(w(m(A),m(B)) - I) * (1,0,0,0)^T
```

produces four integer polynomials defining the c-representation variety.
Conversely, at a common zero satisfying the stated nondegeneracy condition,
the proof writes down `A` and `B`, unique up to conjugacy.  Theorem 4 is a
complete real-case table: comparisons among `1-x^2` and `y^2`, followed by
displayed square-root formulas, select `S^3` or `SL(2,R)` and produce the
representatives.

Thus substitution is a sound, exact verifier, but it does not make an
unknown point of the variety generatable.  Section 4's trefoil and figure-eight
examples explicitly say that the defining polynomials were computed with
Mathematica.  Section 5 repeats the same situation for affine
c-representations: equation (5.4) uses evaluated Fox derivatives to produce the
additional polynomial constraints; the figure-eight example again says they
were found with Mathematica.

The easy case is stated in Section 4.1.  Proposition 9 proves that every point
on `y = 1-x^2` is realized by a reducible c-representation of a standard
2-bridge knot or link group.  Its proof sets `A- = B-`, hence `A = B`.
Proposition 10 shows that the other reducible branch `y = x^2-1` works for
2-bridge links but not for 2-bridge knots (apart from the degenerate point).
These propositions are exactly the easy regime that kills the proposed
unlimited knot-family generator.

## Mechanical cost versus compact route

Two native formulations were costed because they fail for different reasons.

| proposed native task | mechanical route | compact route | outcome |
|---|---:|---:|---|
| Given `(x,y)` on the variety, output the regular quaternion matrices | `u=1-x^2` takes 2 binary rational operations; filling the displayed matrices takes at most 8 sign changes/copies, for **at most 10 exact operations** | Read the same displayed formulas: **at most 10 exact operations** | Cost ratio 1:1; no Track-B compression gap. |
| Given a real `(x,y)`, output the Theorem-4 representative | Depending on the case, **at most 12 field operations plus 2 square roots** in the displayed formula | The claimed insight is precisely choosing that case and using the same formula: **at most 12 plus 2 square roots** | Again the routes coincide. |
| Give a length-256 standard 2-bridge relator and request any reducible c-representation | A literal Theorem-3 numerical replay costs at most `256 * 28 = 7,168` scalar multiply/add operations using 4-by-4 matrix-vector products | Set `A=B` as in Proposition 9: **0 arithmetic operations** after choosing a fixed unit quaternion | There is a gap, but the in-context ansatz succeeds 8/8 (indeed on every instance), so Track B fails its mandatory fourth attack regardless of the raw candidate-space density. |

The first two rows are the relevant comparison when the input contains enough
information to make the desired irreducible certificate generatable.  There is
no scalable parameter: a quaternion algebra remains four-dimensional, and
increasing the relator length changes only the final substitution check, not
the displayed certificate construction.

The third row explains why artificially lengthening `w` does not rescue Track
B.  A standard 2-bridge knot presentation has relation `a v(a,b) = v(a,b) b`.
After substituting `A=B`, both sides are products of the same quaternion and
are equal.  Random relabelling, conjugating the relator, or inserting freely
reducible word pairs does not remove this witness.  Requiring irreducibility
removes the shortcut, but also removes Proposition 9, leaving the generator to
solve the character equations it just created.

## Why the prior-triage proposal fails

The proposed route was “choose quaternion matrices satisfying knot-group
relations, then derive the presented group.”  For a generic chosen pair of
quaternions, deriving a nontrivial kernel word is itself a relation-search
problem; doing it inside `make_instance` is not inverse generation.  The only
relations that can be derived without such a search are planted identities:

1. tautologies or commutator identities, which admit immediate trivial or
   abelian witnesses;
2. a fixed known knot relation such as the trefoil, which has a fixed simple
   character point that works for every seed; or
3. products/conjugates of a known relator, which still accept that same fixed
   representation.

Simultaneous conjugation does not help: `verify` must accept any valid witness,
so a solver may submit the unconjugated representative unless extra gauge data
is imposed.  Imposing such data turns recovery into a fixed 2-by-2 or 4-by-4
simultaneous-conjugacy linear solve, again a constant-size version of the first
row above.  Free-group substitutions either cease to preserve the
c-representation condition or require evaluating the same substitution chain
to carry the witness; within the 2,000-character answer cap their mechanical
and intended routes do not separate.

## Gate diagnosis

| requirement | result |
|---|---|
| **G** | Passes only when `(x,y)` is already supplied, for the fixed trefoil/figure-eight examples, or on Proposition 9's reducible branch.  It fails for a scalable irreducible knot family because the point must be obtained by solving the generated polynomial system. |
| **H, Track A** | Fails for every theorem-backed distribution identified above.  The paper is constructive/classificatory and proves no distributional hardness regime.  The fixed examples and reducible branch have seed-independent simple witnesses. |
| **H, Track B** | Fails.  With a supplied point, the mechanical and compact formulas are identical (10 operations, or 12 plus two square roots).  With a long relator, `A=B` is an immediate successful by-hand attack rather than a hidden invariant. |
| **V** | Passes in principle: check unit norm and conjugacy invariants, then substitute the submitted matrices into every relator using exact rational or algebraic arithmetic. |

An artificial wrapper could hide a character point behind an unrelated hash,
large linear system, finite-field encoding, or planted change-of-basis puzzle.
None of those constructions or reductions occurs in the paper, and the
difficulty would come from the wrapper rather than from quaternionic
2-bridge-knot representations.  Building one would violate the instruction to
keep the paper's native mathematics load-bearing and would not cure this
Step-0 failure.
