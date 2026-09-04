# Rejected: arXiv 1605.04000

Paper: Yaroslav Shitov, [*The nonnegative rank of a matrix: Hard
problems, easy solutions*](https://arxiv.org/abs/1605.04000), v2 (2017).

## Decision

This paper does not supply a problem distribution for which **G
(generatable), H (hard in the declared track), and V (exactly verifiable)**
can all be justified.  The prior-triage proposal--sample nonnegative factors
`U,V`, publish `M=UV`, and ask for a factorization--does satisfy G and V, but
it does not satisfy the distributional requirement in H.  The paper proves a
worst-case reduction from CLIQUE COVER; it says nothing about the difficulty
of recovering factors of a random inverse-generated product.

I therefore stopped at Step 0.  No generator, gate report, README, or oracle
transcript was manufactured for a family whose hardness claim is unsupported.

## What the paper actually proves

For a nonnegative matrix `A` over a subfield `F` of the reals, Section 2
defines `rank_F^+(A)` as the least number of nonnegative rank-one matrices over
`F` whose sum is `A`.

The paper then has three relevant pieces.

1. **An explicit rank-four gadget.**  Observation 1 states that the displayed
   matrix `B(alpha_1,...,alpha_n)` has nonnegative rank four exactly when all
   `alpha_i` are the same element of `[0,1] ∩ F`.  Its proof is the explicit
   convex-combination identity for the rows of the fixed `4 x 4` matrix
   `B_0`: the top row is assembled from the two alternative sums of rows of
   `B_0`.
2. **A worst-case reduction.**  Theorem 2 and Corollary 3 convert a matrix
   completion problem into ordinary nonnegative rank by adjoining one copy of
   the rank-four gadget.  Section 3 associates a partial `0/1` matrix `X(G)`
   with an arbitrary graph `G` and proves that the minimum nonnegative rank of
   a completion is exactly the clique-cover number of `G`.  Applying
   Corollary 3 to the variables proves that computing ordinary nonnegative rank
   is NP-hard.
3. **One field-separating example.**  Section 4 gives a fixed integral
   `21 x 21` matrix.  Three applications of Corollary 3 reduce its rank
   calculation to the fixed `5 x 5` matrix `C(a,b,c,d)`.  The only possible
   rank-three parameters are written down (`b=c=d=1 +/- sqrt(1/2)` and
   `a=2-1/b`), and the paper explicitly displays the three nonnegative
   rank-one summands for the real solution.  This proves that rational and real
   nonnegative rank can differ; it is not a growing search family.

The paper gives no average-case theorem, planted-distribution theorem, FPT
boundary, or parameter regime asserting that random products of sampled
nonnegative factors are hard to factor.

## Step-0 discriminating test

For the proposed inverse family, the certificate is produced by the generator
itself:

```text
sample U >= 0 and V >= 0; compute M = U V; retain (U,V)
```

This costs `O(m r n)` exact arithmetic operations for an `m x r` factor and an
`r x n` factor.  That is a valid answer-first construction, not a solver for
recovering `(U,V)` from `M`.  The fatal issue is instead the separate H gate:
the distribution of matrices produced this way is not the reduction-image
distribution in Section 3, and the paper's worst-case NP-hardness theorem does
not transfer to it.

Random dense positive factorizations also have scaling and permutation
symmetries and commonly have further nearby nonnegative factorizations.  A
checker can correctly accept all of them, but non-uniqueness does not establish
search hardness.  Restricting the answer to small integer factors merely to
obtain a finite `CERTIFICATE_LANGUAGE` would define a new bounded integer
factorization problem; the paper neither studies nor proves hardness for that
planted distribution.

Consequently neither track is honest:

- **Track A cannot be declared.**  Section 3 proves worst-case NP-hardness for
  matrices obtained from arbitrary clique-cover instances.  The task
  explicitly forbids using worst-case NP-hardness as evidence that the chosen
  random inverse-generated distribution is hard.
- **Track B cannot be declared for general exact NMF.**  The paper supplies no
  efficient exact factor-recovery algorithm whose measured mechanical cost
  could be contrasted with a short structural route.  Calling a general
  exponential search or a non-guaranteed numerical NMF heuristic the Track B
  reference algorithm would violate the definition of that track.  For the
  explicit Section 2 and Section 4 constructions, by contrast, the compact
  factorization is already displayed in the paper, so there is no meaningful
  mechanical-versus-compact gap.

## Why the paper's reduction does not repair the family

One could sample a graph together with a clique cover, form `X(G)`, and carry
the cover through Section 3.  This still does not qualify.

- Planting a clique cover (equivalently, a colouring of the complement) does
  not inherit worst-case hardness.  The paper provides no hard planted graph
  distribution, and does not analyze the spectral, greedy, or colouring
  attacks required for such a distribution.
- If the solver is asked only for the cover labels, the computational core is
  graph colouring/clique cover.  This can be reported as a paper-licensed
  reduction, but it is not an algebraic nonnegative-factorization family and
  still lacks distributional hardness.
- If the ordinary matrix and an actual explicit nonnegative factorization are
  required, every completion variable eliminated by Theorem 2 contributes four
  more rank-one summands.  Even counting only one atom per summand, the G9 limit
  of 256 atomic answer elements permits fewer than 64 such variables; a pair of
  factor matrices is much larger.  A custom macro that compresses all fixed
  gadgets back to cover labels avoids that cap only by returning to the graph
  certificate in the preceding bullet, whose distribution still lacks H.
- A factorization witnesses only an upper bound on nonnegative rank.  Asking
  for the *minimum* rank would additionally require an executable optimality
  certificate.  The paper's appeal to the optimum clique-cover number is not
  such a locally checkable certificate.

## Other native candidates considered

| Candidate task | Outcome |
|---|---|
| Factor the explicit `B(alpha,...,alpha)` gadget | G and V pass, but Observation 1's proof gives the factorization directly from the visible `alpha`; H fails. |
| Recover the common `alpha` in `B` | It is a displayed matrix entry, so the verifier's lookup is also a solver; H fails. |
| Factor the Section 4 `21 x 21` matrix over the reals | The paper prints the algebraic parameters and three summands, so this is a fixed lookup task and does not scale. |
| Prove that the same matrix has no rational factorization of the target size | The paper gives a mathematical impossibility proof, not a bounded concrete negative certificate that the requested checker can validate cheaply. |
| Take permuted or diagonally scaled copies of the Section 4 example | These are structure-preserving relabellings/scalings of one fixed problem and must collapse under an honest canonical key; they do not provide unlimited structural diversity. |
| Use block-diagonal sums of the explicit gadgets | The certificate grows with the number of blocks, while each block is recognized and factored by the same displayed identity; this scales transcription, not difficulty. |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G -- answer-first generation | pass in principle | Sample rational nonnegative `U,V`, multiply them, and retain the JSON-encoded factor matrices. |
| H -- Track A structural hardness | **fail / unsupported** | Section 3 is worst-case only and does not cover the sampled-product distribution. |
| H -- Track B no-tool compression | **fail / unsupported** | No efficient exact general recovery algorithm plus distinct compact route is supplied; the paper's explicit special cases are immediate. |
| V -- exact witness checking | pass in principle | Check dimensions and rational nonnegativity, multiply the submitted factors exactly, and compare every entry with `M`. |
| G7/G8/G9 for Section 4 | **fail** | The construction is fixed up to symmetries; scaling it by repetition makes the answer longer rather than the reasoning harder. |
| Overall | **rejected at Step 0** | G, H, and V do not hold simultaneously for a supported family. |

The 200,000-sample guess test, adversary panel, and LLM hardening loop were not
run.  Those are measurements of a qualifying family; they cannot supply the
missing distributional theorem or turn worst-case NP-hardness into an honest
Track A claim.
