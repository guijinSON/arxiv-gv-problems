# Rejected: arXiv 2107.02554

Paper: Bart M. P. Jansen, Shivesh K. Roy, and Michał Włodarczyk,
[*On the Hardness of Compressing Weights*](https://arxiv.org/abs/2107.02554)
(MFCS 2021).

## Decision

No generator is shipped.  A native, inverse-generated Track B family reached
the prescribed hardening loop, but the four-vendor pool produced an exactly
verified witness at **every** non-demo rung, including the largest rung allowed
by the 300-operation compact-route cap.  The harness therefore returned
`too_easy`, so STEP 4 requires the family to be given up on rather than enlarged
or retuned by hand.

The attempted module and its non-shipping transcript were removed to avoid
leaving an apparently usable generator beside this rejection.  The
script-written `.meta.json` retains the `too_easy` verdict and master-run
metadata.

## What the paper actually defines

The introduction defines **Exact-Edge-Weight Clique** on an undirected graph
`G`, a nonnegative integer weight for each edge, and a nonnegative integer
target `t`.  A witness is a vertex set inducing a clique such that the sum of
all induced edge weights is exactly `t`; clique cardinality is not constrained
in the base definition.  The same passage explicitly says cardinality can be
prescribed by adjusting weights, and that a nonedge can be replaced by an edge
of weight `t+1`.  It follows that complete, fixed-cardinality weighted graphs
are still paper-native objects.

Theorem 1 proves that, unless `NP` is contained in `coNP/poly`, the problem
parameterized by its number of vertices has no generalized kernel of
`O(n^(3-epsilon))` bits.  Theorem 2 gives a randomized polynomial-time weight
compression to `O(n^3)` bits, with one-sided error, by reduction modulo a random
prime.  These are compression results.  They do **not** prove that a randomly
planted clique distribution is hard to search, so using Theorem 1 as a Track A
hardness basis would be invalid.

## The attempted Track B construction

The certificate was sampled first as a uniform size-`k` vertex subset.  After a
random vertex permutation, vertex `v` received a positive potential

```text
a_v = offset + scale * (-2)^e(v),
```

where `e` is a permutation of `0,...,n-1`.  Every edge of the complete graph
received weight `w(u,v)=a_u+a_v`, and the target was formed from the sampled
subset.  For a size-`k` set `S`, its induced-edge weight is

```text
(k-1) * sum(a_v for v in S).
```

Distinct subsets have distinct sums because a nonzero signed combination of
`1,-2,4,-8,...` with coefficients in `{-1,0,1}` cannot vanish: its largest
term exceeds the sum of the magnitudes of all smaller terms.  Thus G and V were
clean: the generator knew a unique certificate without solving, and the checker
only checked indices and summed the submitted clique's published edge weights.

The intended compact route recovered all `a_v` from three anchor edges and then
decoded the normalized target in base `-2`.  The successful reference algorithm
recovered the same potentials and ran fixed-`k` meet-in-the-middle subset sum in
`O(n^(ceil(k/2)))` time and `O(n^(floor(k/2)))` space.  This was honestly
declared as Track B, not hidden as a Track A attack.

## Local gates before the oracle run

At the initial `easy` candidate (`n=40`, `k=8`), all local gates other than the
then-pending external G9 gate passed:

| check | measured result |
|---|---:|
| planted witnesses | 16/16 across all four presets |
| corruption branches | 5/5 rejected with distinct reasons |
| structure-aware random guesses | 0/200,000 |
| exact candidate count | 76,904,685 |
| exact witness count | 1, by signed-radix uniqueness |
| largest-potential outlier attack | 0/8 |
| target-average greedy | 0/8 |
| 512 random restarts per seed | 0/8 |
| single-swap target-average descent | 0/8 |
| meet-in-the-middle reference solver | 8/8; 931,000 combination records total; 0.358584 s total |
| canonical-key relabelling checks | 60/60, with carried witnesses 60/60 |
| unrelated canonical keys | 20/20 distinct |

The answer was only eight indices (23 characters in the measured easy sample).
The intended-route estimates were 210, 250, and 290 exact operations for easy,
medium, and hard, respectively, all within the required cap.

## Fatal hardening result

The script-owned bare run used the required fresh multi-vendor pool.  A level is
easy if **any** of its three vendors solves it.  The decisive records were:

| preset | parameters | solved / attempts | decisive verified solve |
|---|---|---:|---|
| easy | `n=40, k=8` | 1/3 | Grok 4.6, seed 1056983959 |
| medium | `n=48, k=8` | 1/3 | Claude Sonnet 5, seed 1843990685 |
| hard | `n=56, k=8` | 1/3 | Grok 4.6, seed 1543318666 |

At `hard`, the two other vendors did not solve: one exhausted its response
budget and one submitted a clique with the wrong exact sum.  This does not
rescue the rung because the third vendor recovered the additive potentials,
recognized the values as shuffled powers of `-2`, decoded the unique
negabinary representation, mapped its eight exponents back to vertices, and
submitted `[2,12,21,24,27,36,48,51]`.  The checker returned `(True, "ok")`.

The solve was the intended compact route, not a planting outlier or parsing
accident.  Enlarging past `n=56` would cross the declared 300-operation limit,
and the harness correctly stopped when `escalate()` returned `None`.

## Why no nearby family is substituted

- The paper's cross-composition from Red-Blue Dominating Set establishes a
  worst-case kernel lower bound.  Starting from arbitrary hard source instances
  loses G because the generator does not know a dominating-set witness;
  planting the witness loses the theorem's hardness guarantee.
- The paper's Subset Sum and weighted-CSP lower bounds have the same
  worst-case-generation conflict.  Their reductions do not establish average-
  case hardness for answer-first planted instances.
- The bipartite node-weighted Vertex Cover section deliberately gives a
  strongly polynomial algorithm, based on maximum `b`-matching, that preserves
  all minimum covers while reducing weights to `[1,n]`.  Turning its output into
  a certificate-search task would fail Track A's discriminator.
- A second Track B construction after the mandated `too_easy` result would be
  hand-retuning the paper past the explicit stopping rule.

## Final gate outcome

| requirement | outcome | reason |
|---|---:|---|
| G — generatable | pass for the attempted family | certificate sampled before the graph and target |
| V — exact witness checking | pass for the attempted family | exact clique cardinality, adjacency, and integer edge-sum checks |
| H — Track A | unsupported | the paper proves kernel lower bounds, not hardness of the planted distribution |
| H — Track B / STEP 4 | **fail** | a vendor executed the compact route and verified at every rung, including hard |
| G9(b) | not run | the bare family already failed STEP 4, so hinted/placebo spending could not make it shippable |
| overall | **rejected** | the required hardening verdict was `too_easy` |

This is an informative rejection: cardinality, answer size, exactness, guessing,
generic construction attacks, and cross-vendor diversity were not the problem.
The structure intended to make the instance human-compressible was itself
recoverable by an oracle at the maximum permitted no-tool workload.
