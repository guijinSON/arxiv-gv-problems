# Rejected at Step 0: arXiv:1405.5432

Paper: Michael Kiermaier and Reinhard Laue, “Derived and Residual Subspace
Designs” ([arXiv:1405.5432](https://arxiv.org/abs/1405.5432)).

## Decision

No generator is shipped. The paper's native objects admit finite, exact
certificates, so **G** and **V** are available, but every paper-backed certificate
family fails **H on Track A**. Track B does not rescue it: the paper's construction
is already the shortest public route to its output, while hiding that route creates
a separate subspace-isomorphism/search puzzle for which the paper supplies neither
an efficient reference algorithm nor a compact recovery invariant.

This is a Step-0 hardness rejection, not a rejection caused merely by the existence
of an efficient algorithm, and not a `cap_bound` result.

## What the paper actually defines

Definition 1 says that a `t-(v,k,lambda)_q` design is a set of `k`-subspaces of
`GF(q)^v` in which every `t`-subspace occurs in exactly `lambda` blocks. Thus a
native positive witness is the actual collection of subspaces, represented for
example by canonical row-reduced basis matrices. Verification is exact: check every
basis rank and count containments of every `t`-subspace.

Definition 4 fixes the two transformations that the abstract only sketches:

- `Der_U(D)` retains precisely the blocks containing the one-dimensional subspace
  `U` and takes their quotients by `U`;
- `Res_H(D)` retains precisely the blocks contained in the codimension-one
  subspace `H`.

Lemma 5 gives their parameters. Lemma 11 says that derivation and residualization
are interchanged by exact orthogonal-complement duality. Theorem 14 is the main
certificate-producing result. Given realizations of the derived and residual
parameter sets and a surjection `phi : V -> Vbar`, it explicitly defines

```text
B1 = {phi^(-1)(Bbar) : Bbar is a derived block}
B2 = {K : K complements ker(phi) in phi^(-1)(Bbar),
          Bbar is a residual block}
BRed = B1 union B2.
```

The proof then checks the incidence count in two cases. Corollary 20 repeats this
same construction componentwise for large sets. These are direct constructors, not
hard search reductions.

## Why Track A fails

The certificate algorithm is stated in the theorem itself:

- parameter certificates use the Gaussian-binomial products and the two
  `q`-Pascal identities displayed in Section 2;
- derived and residual block sets use one containment test and one quotient or
  restriction per source block (Definition 4);
- dual block sets use one exact nullspace/orthogonal-complement computation per
  block (Section 2.3 and Lemma 11);
- reduced block sets use one preimage per derived block and enumerate all
  complements for every residual block (Theorem 14).

All are polynomial in the explicit input and output size using finite-field row
reduction. The domain-standard algorithm therefore succeeds on every distribution
obtained by applying these constructions. The paper proves existence and parameter
identities; it states no worst-case or distributional hardness result for recovering
a design.

The designs in Corollary 17 do not provide a scalable hard distribution either.
Their input designs are imported from classification/construction references and the
paper only lists their parameters. Hard-coding those fixed designs and applying
random changes of basis would produce isomorphic copies, which `canonical_key` must
collapse rather than count as unlimited diversity.

## Track B audit: mechanical cost versus compact route

The required comparison was made before writing a module. For the smallest exact
instance of Theorem 14, take `q=2`, `t=k=2`, `lambda=1`, and use the complete derived
and residual designs. Encode each two-dimensional subspace by one integer bit mask
for its three nonzero vectors. A local CPython microbenchmark of the literal
preimage/complement construction gave:

| ambient `v` | reduced blocks | JSON chars | answer atoms | mean construction time | conservative primitive work |
|---:|---:|---:|---:|---:|---:|
| 4 | 35 | 167 | 35 | 0.000016 s | 140 vector-emission/packing operations |
| 5 | 155 | 1,272 | 155 | 0.000074 s | 620 vector-emission/packing operations |
| 6 | 651 | 9,795 | 651 | 0.000247 s | at least 2,604 such operations |

The operation count deliberately understates the implementation: each output block
requires emitting its three nonzero vectors and packing the block. The **compact
route has exactly the same count**. Recognizing Theorem 14 tells the solver which
preimages and complements to emit, but it does not avoid emitting them. The
mechanical/compact cost ratio is 1 up to bookkeeping.

This small family is also mathematically useless as a benchmark: the output is the
entire Grassmannian, so once the required output size is imposed there is only one
possible block set. The `v=4` case is a short direct exercise; `v=5` already exceeds
G9(c)'s 300-operation route cap; and `v=6` exceeds both the 256-atom and 2,000-character
answer caps. Scaling grows the haystack and the witness together.

The first nontrivial reduced design in the paper's own Table 1 has parameters
`2-(8,4,63)_2` and contains

```text
63 * [8 choose 2]_2 / [4 choose 2]_2 = 19,431 blocks.
```

Even the unrealistically compressed representation of one ambient-vector membership
bit mask per block therefore needs 19,431 atoms. It is far outside G9(c), and the
paper offers no succinct witness language that an exact checker can inspect without
expanding those blocks.

The other natural targets have no hidden compression gap:

| candidate family | mechanical certificate algorithm | compact route | outcome |
|---|---|---|---|
| compute a derived/residual/reduced parameter | evaluate the displayed Gaussian-binomial formula in `O(k)` exact arithmetic operations | the same displayed formula | H fails on A and B |
| given a constructed design and a subspace `T`, return its incidence count | Lemma 2 or Theorem 14 computes `lambda_s` directly with two Gaussian-binomial values (or two powers, two subtractions, and one exact division in the reduced case) | the identical incidence formula; scanning all displayed blocks is a deliberately weaker algorithm, not the honest reference algorithm | H fails on A and B |
| output a derived, residual, or dual design | filter blocks and perform quotient, restriction, or orthogonal complement in output-linear polynomial time | the same blockwise transformation | H fails on A and B |
| output Theorem 14's reduced design | enumerate the displayed preimages and complements | the identical displayed construction; every block must still be written | H fails on A and B; useful sizes also fail G9(c) |
| certify Example 3's nonexistence | evaluate the cyclotomic/Gaussian-binomial divisibility calculation | the same factor calculation printed in Example 3 | H fails on A and B |
| output the Corollary 20 large set | apply Theorem 14 to every component and emit every block | the identical componentwise construction | H fails on A and B; witness is still larger |

In particular, replacing the block witness by the single number of blocks through a
specified subspace does not create Track B compression. Enumerating all blocks would
make the mechanical column look large, but it is not the strongest algorithm: the
paper's own Lemma 2 returns the number directly. Enlarging the declared integer range
can make a random numerical guess unlikely, but it cannot make that five-operation
formula fail the mandatory domain attack.

## Why obfuscation is not a rescue

One can randomly change coordinates, discard the construction labels, and ask a
solver to recover the hidden kernel, match two dual designs, or identify which blocks
came from `B1`. That gives G by carrying the private change of basis and V by exact
finite-field substitution. It does not give H under either permitted track:

- Track A would need evidence that the resulting planted distribution resists the
  standard subspace/code-equivalence, incidence-refinement, and linear-algebra
  attacks. The paper contains no such result.
- Track B would need a short invariant visible to the solver and a measured expensive
  reference algorithm. The only short map in Lemma 11 is the direct orthogonal
  complement once the coordinate identifications are known. Hiding those
  identifications also hides the shortcut; recovering them is the newly introduced
  isomorphism problem, not a compact route proved in this paper.

Adding decoy blocks or a planted checksum would similarly manufacture a generic CSP
or exact-cover problem. No section of the paper licenses such a reduction, so it
would be a benchmark-convenience discretised analogue rather than native coverage.

## Gate conclusion

| gate | result |
|---|---|
| G — generatable | **Passable.** Definitions 4, Lemma 11, Theorem 14, and Corollary 20 carry exact block certificates by construction. |
| V — exact witness verification | **Passable.** Finite-field rank, containment, quotient, complement, and incidence counts are exact and executable. |
| H — Track A structural hardness | **Fail.** The paper supplies the output-polynomial constructor for every generated native witness regime. |
| H — Track B no-tool compression | **Fail.** Mechanical and compact routes coincide; 140 versus 140 operations at the last small case, 620 versus 620 at the largest answer-cap-compliant case. |
| G9(c) | Does not cause the rejection, but blocks scaling: the next dimension has 651 atoms, and the first nontrivial Table 1 design has 19,431 blocks. |

No G1–G9 sampling, adversary panel, or oracle runs were fabricated after the
mandatory Step-0 failure. A module implementing these explicit formulas would only
reconfirm the reason H fails.
