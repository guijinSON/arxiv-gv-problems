# Rejected: spectrally exposed Token Jumping barrier

Paper: Daniel W. Cranston, Moritz Mühlenthaler, and Benjamin Peyrille,
[*A simple quadratic kernel for Token Jumping on surfaces*](https://arxiv.org/abs/2408.04743),
arXiv:2408.04743.

## Decision

No generator is shipped. The proposed bounded-length Token Jumping family met
inverse generation and exact replay, and it even received a `hardened` verdict
from the prescribed LLM loop. A subsequent construction-aware spectral attack,
motivated by the planted-colouring literature, recovered a verified witness on
**20/20 shipping instances in polynomial time**. The family therefore fails
**H (hardness)** and **G6 (adversary panel)**. The misleading generator,
self-test report, README, and oracle transcript were removed rather than leave
an apparently validated but easy family in the corpus.

## What the paper actually defines

Section 2 defines Token Jumping on a finite, undirected, simple graph. A state
is an independent vertex set. Consecutive states have the same cardinality and
differ by exactly one removed and one added vertex. Given independent sets `I`
and `J`, each of size `k`, the decision problem asks whether such a sequence
connects them.

Section 1 states the relevant hard and easy regimes. Unrestricted Token
Jumping is PSPACE-complete even on subcubic planar graphs of bounded bandwidth,
and the version parameterised by both token count `k` and number of jumps
`ell` is W[1]-hard. On the positive side, the problem is FPT on planar and,
more generally, `K_{3,t}`-free graphs when parameterised by `k`; it also has
kernels on bounded-degree, bounded-degeneracy, and fixed-surface graph classes.
Theorem 1 proves an `O(g^2 + gk + k^2)` kernel when both genus `g` and token
count `k` are parameters. These facts require `k` and `ell` to grow and rule
out treating a small planted path as hard merely because unrestricted
reachability is PSPACE-complete.

## The attempted bounded-witness reduction

The attempted family used an auxiliary graph `H` on `n` vertices. The Token
Jumping graph had:

- `n+1` independent start vertices `S` and `n+1` independent goal vertices
  `T`, with every `S`--`T` edge present;
- three choice vertices `X(v,0)`, `X(v,1)`, `X(v,2)` forming a triangle for
  every `v` in `H`; and
- an edge `X(u,c)`--`X(v,c)` for every edge `uv` of `H` and colour `c`.

A sequence of exactly `2n+1` jumps from all of `S` to all of `T` is forced to
move `n` tokens onto choice vertices before its unique `S -> T` jump. The
choice triangles force one choice per vertex of `H`, and same-colour conflict
edges make those choices a proper 3-colouring. Conversely, every proper
3-colouring gives a valid sequence. This supplied a polynomially bounded
witness and a cheap exact verifier, and it contains the ordinary worst-case
3-COLOURING relation.

For inverse generation, the code sampled three equal planted colour classes
first and then drew three edge-disjoint perfect matchings between every pair
of classes. Thus every vertex of `H` had exactly three neighbours in each of
the other two classes and none in its own class. This equalised all visible
degrees and defeated the original outlier, greedy, and short random-restart
attacks. It also created the fatal algebraic signature.

## Polynomial spectral attack

Let `A` be the adjacency matrix of `H`, and let `1_C` be the indicator vector
of a planted colour class. For

`x = 1_C0 - 1_C1`,

every vertex in `C0` has three neighbours in `C1`, every vertex in `C1` has
three neighbours in `C0`, and every vertex in `C2` has three neighbours in
both. Hence

`A x = -3 x`.

A second independent difference of class indicators has the same eigenvalue.
The supposedly hidden colouring is therefore an exact two-dimensional
eigenspace of eigenvalue `-3`. Computing that eigenspace and grouping vertices
by their two coordinates recovers the three classes whenever no accidental
extra `-3` eigenvectors occur. This takes polynomial time using standard exact
or numerical linear algebra.

The attack was tested on 20 unrelated `n=180` shipping seeds. In every case:

1. eigenvalue `-3` had multiplicity exactly two;
2. the eigenspace row embeddings formed three groups of exactly 60 vertices;
3. those groups were a proper 3-colouring; and
4. converting the colouring to the prescribed 361-jump witness made the public
   verifier return `(True, "ok")`.

Result: **20/20 verified solves**. This is not a marginal statistical leak; it
is a direct polynomial construction of the witness.

The failure is consistent with known work on planted colouring. David and
Feige's [*On the effect of randomness on planted 3-coloring models*](https://arxiv.org/abs/1603.05183)
reviews polynomial spectral recovery for random planted balanced colourings,
and Kumar, Louis, and Tulsiani's [*Finding Pseudorandom Colorings of
Pseudorandom Graphs*](https://doi.org/10.4230/LIPIcs.FSTTCS.2017.37) gives
polynomial recovery results for expanding graphs with pseudorandom balanced
colourings. The attempted construction was even more exposed because its
between-class neighbour counts were exact rather than merely concentrated.

## Why the LLM and initial gates were insufficient

Before the spectral check, the `n=180` version had these measurements:

| check | observed result |
|---|---:|
| planted replay | 12/12 preset/seed checks passed |
| corruptions | 5/5 rejected with distinct reasons |
| structure-aware random guessing | 0/200,000 |
| degree outlier | 0/8 |
| deterministic greedy colouring | 0/8 |
| 32-restart randomised DSATUR | 0/8 |
| relabelling/key checks | 120/120 invariant; 20/20 unrelated keys distinct |
| four-vendor hardening | `hardened` at `n=180` after the easy rung was solved |
| **spectral colouring** | **20/20 verified solves — failure** |

The LLM result was especially weak evidence: one decisive model exhausted its
32,000-token budget without emitting content, one explicitly declined to
answer, and one emitted an invalid sequence. None tried the two-line
eigenvector observation above. Random guessing and local heuristics measured
the wrong attack surface; their failures say nothing against a deterministic
global invariant.

An earlier `n=90` rung had already shown why the adversary panel matters: three
LLM vendors failed it, but the randomized-DSATUR attack solved 6/8 seeds. It was
retired before the final run. The spectral attack then invalidated the larger
rung too.

## Why this was not retuned again

Varying the between-class degrees could remove the exact eigenvalue, but that
would start a new planted-colouring family whose average-case hardness is not
established by the Token Jumping paper. Published planted-colouring algorithms
also make a quick density retune unsafe. The prompt explicitly forbids using
manual post-oracle tuning to chase a passing run. A defensible replacement
would require a new hard planted distribution (or a faithful worst-case
reduction with answer-first sampling), a spectral/SDP attack panel, and a fresh
hardening process. That is materially different work, not a repair to this
generator.

## Gate outcome

| requirement | result |
|---|---|
| G — inverse generation | Passed: the colouring and bounded jump sequence were sampled before edges. |
| H — no known polynomial/closed-form method | **Failed:** eigenspace recovery solved 20/20 and is polynomial. |
| V — cheap exact verification | Passed: replay checks occupancy, independence, length, and final state. |
| G6 — adversary panel | **Failed after adding the required spectral attack: 20/20 successes.** |
| Overall | **Rejected.** |

The rejection is based on a stronger attack than the required LLM loop. An
oracle transcript cannot override a known polynomial solution method.
