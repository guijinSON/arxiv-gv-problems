# Rejected: arXiv:1710.06282

This paper does not yield an acceptable generator in this run. The native
wheel-model certificate is generatable and exactly verifiable, but the tested
family fails **H on Track B**. It is not rejected merely because an efficient
algorithm exists.

## Step 0 findings

Section 1 defines an `$H$`-model as pairwise vertex-disjoint connected branch
sets, with touching branch sets for every edge of `$H$`, and defines `$W_t$` as
a `$t$`-cycle plus a universal hub. Theorem 1.5 proves the tight
`$O(k log k)$` Erdős–Pósa packing/transversal bound for `$W_t$`-models for every
fixed `$t >= 3$`. The theorem is extremal, not a computational or
distributional hardness theorem.

The paper also makes the algorithmic easy side impossible to ignore. Section
2 describes the standard treewidth/minor machinery, and Theorem 2.2 invokes a
polynomial kernel for deleting a fixed planar minor. These facts do not by
themselves reject a Track-B family, but they do mean that Theorem 1.5 cannot be
used as a Track-A hardness basis for a planted distribution.

## Family that was built and tested

The retained module, `rejected_gen_1710_06282.py`, inverse-generates a regular
graph with a singleton-branch-set `$W_4$`-model. In raw finite-field
coordinates an order-four automorphism has one fixed vertex. That vertex is
the planted hub, one neighboring four-orbit is closed into the rim, and a
nonlinear coordinate permutation relabels the graph. The witness is carried
through that isomorphism; generation never searches the completed graph.

Verification checks five singleton branch sets for distinctness, bounds, the
four hub edges, and the four rim-cycle edges. It accepts any canonical valid
singleton model, not only the plant. The local self-test passes G1–G9(c): at
the proposed `$n=401$` shipping preset the bounded certificate language has
1,264,040,099,700 candidates, exact enumeration found one valid answer for the
measured instance, 200,000 structure-aware guesses had zero hits, the answer
has five atoms and 30 characters, and the intended route costs 204 counted
exact operations.

## Why H fails

The certificate-producing reference algorithm is an exact scan of candidate
hubs and canonical four-cycles in each hub neighborhood. On a `$d$`-regular
graph it costs `$O(n d^4)$`. At shipping seed 17 it took 40,527 exact adjacency
probes and 0.024 seconds. Across the eight-seed adversary panel it took
2,398,351 probes and 1.40 seconds total and solved 8/8, as a Track-B reference
algorithm should.

The compact route is genuinely shorter: solve for the unique fixed point of
the supplied quarter-turn, decode its neighboring symmetry orbits, and check
which orbit is a four-cycle. The instrumented implementation uses 204 exact
modular-arithmetic and adjacency operations. Thus the mechanical cost and
compact route are not being conflated: there is a substantial gap.

Nevertheless, the no-tool oracle pool found and executed that compact route
directly. The script-owned bare hardening transcript contains 15 completed
calls over five increasing sizes:

| size | solved / attempts |
|---:|---:|
| 193 | 3 / 3 |
| 277 | 2 / 3 |
| 401 | 3 / 3 |
| 809 | 3 / 3 |
| 1621 | 3 / 3 |

That is 14/15 verified solves across both vendors. The next escalation to
`$n=3253$` stopped before an oracle call because the generator's local-density
concealment condition could no longer be met at fixed degree. This is not
counted as model failure. More importantly, five successive completed sizes
already show that growing the haystack does not repair the family: the models
recognize the disclosed symmetry before doing the mechanical scan.

The obvious alternative from the prior triage—placing `$k$` disjoint wheel
models in separate or weakly coupled pieces—has G and V but makes the packing
visible. Planting inside an otherwise random regular graph removes the compact
route and leaves no paper-backed distributional hardness theorem, so it cannot
honestly be called Track A. The tested symmetry construction supplies a compact
route, but the route is guessable in context and therefore fails Track B.

## Decision

G passes and V passes. H fails on Track B under the required bare oracle loop;
Track A is not supported by Theorem 1.5 or by evidence for the generated
distribution. The generator, self-test report, `.meta.json`, and unedited
script-owned transcript are retained so this decision can be audited or
reopened. No `gen_1710_06282.py` is shipped.
