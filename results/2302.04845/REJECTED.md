# Rejected: arXiv:2302.04845

## Decision

The proposed family passes **G** and **V** but fails **H on both Track A and
Track B**. I therefore do not ship a generator. The attempted module is
retained as `rejected_gen_2302_04845.py`, together with its unsuccessful
oracle transcript, so this decision can be audited or reopened.

The source is Jian Wang and Jie You, [*Minimum degree thresholds for Hamilton
\((\ell,k-\ell)\)-cycles in \(k\)-uniform
hypergraphs*](https://arxiv.org/abs/2302.04845). I read the complete v1 TeX,
not only the abstract.

## Step 0 findings from the paper

Section 1 defines a Hamilton \((\ell,k-\ell)\)-cycle as a partition
\((L_0,R_0,\ldots,L_{t-1},R_{t-1})\), with \(|L_i|=\ell\),
\(|R_i|=k-\ell\), and both \(L_i\cup R_i\) and
\(R_i\cup L_{i+1}\) hyperedges, including wraparound. That gives a finite,
cheaply checked witness. Inverse generation can sample this partition first
and add hyperedges around it, so G and V are not the problem.

Theorem 1.2 is an **existence threshold**, not a computational-hardness
theorem: for fixed \(k\ge 7\), \(k/2\le\ell\le k-1\), sufficiently large
vertex count divisible by \(k\), and minimum \(\ell\)-degree above
\(\delta(n,k,\ell)\), a cycle exists. Sections 2 and 3 prove this using the
absorbing method, a random reservoir, weak regularity, matchings/connectors,
and an extremal parity analysis. None of these results states that the
paper's dense promised distribution is hard to search.

Section 1 cites Garey--Johnson only for worst-case NP-completeness of perfect
matching or Hamilton **path** in general \(k\)-uniform hypergraphs for
\(k\ge3\). It neither proves average-case hardness for planted instances nor
establishes the required result for this generated Hamilton
\((4,3)\)-cycle distribution. Using that citation as Track A evidence would
confuse worst-case hardness with distributional hardness.

The easy structure is explicit in Section 3. For the parity hypergraphs
\(\mathcal B_{n,k}(A,B)\) and their complements, the paper defines
\(f(\mathcal B)=\eta(\mathcal B)n/k+|A|\pmod2\) and states that such a
hypergraph contains the desired Hamilton cycle exactly when \(f=0\).
Therefore presenting the paper's partition \(A\cup B\) makes this test a
direct parity calculation. Hiding that partition behind a linear system,
tags, a graph code, or a finite-field reconstruction task would be a
convenience reduction not central to the paper, rather than native coverage.

## Why Track A fails

The prior-triage proposal was to plant a cycle and then add independent random
extra hyperedges. In the tractable fixed-block specialization used by the
prototype, this is a planted directed Hamilton cycle with random transition
edges. The density suggested by Theorem 1.2 is asymptotically about one half.
At the prospective shipping size of 72 block pairs and transition probability
\(1/2\), a generic least-onward-degree directed-Hamilton DFS found a verified
cycle on **64/64 seeds**:

| measured mechanical baseline | value |
|---|---:|
| median search nodes | 74 |
| maximum search nodes | 709 |
| median branch trials | 73 |
| maximum branch trials | 708 |
| median wall time | 0.008016 s |
| maximum wall time | 0.018329 s |

These measurements used seeds 0 through 63. The DFS starts at public block 0,
orders successors by their number of still-unused outgoing neighbors, and has
a 100,000-node cap; no run approached the cap.

This is the domain-standard attack on the fixed-block transition problem, and
it succeeds immediately. Making the graph sparser does not rescue the Track A
claim: the paper supplies no theorem for hardness of that planted sparse
distribution, and random regular/circulant constructions introduce detectable
planting structure rather than a justified hard regime.

## Why Track B also fails

For the natural dense planted family there is no separate compact route. The
plant is uniformly relabelled and random decoys carry no paper-derived
invariant. The mechanical method above takes roughly one successor choice per
block (median 73 trials), while the shortest by-hand route must likewise make
roughly 72 choices and edge checks. The costs are the same scale; there is no
compression insight to test.

The retained prototype tried to manufacture a Track B gap by attaching three
large integer tags to every block, all congruent to a hidden coordinate modulo
\(q\). It reported exhaustive scanning of all 9,998 candidate moduli as the
reference algorithm. That is not the strongest algorithm. The generator
ensures that the gcd of all within-block tag differences is exactly \(q\), so
Euclid's algorithm recovers it directly and the residues give the cycle.
Measured at the prototype's shipping preset (72 blocks), this attack solved
**32/32 seeds**:

| strongest certificate-producing algorithm | value |
|---|---:|
| gcd calls | 144 |
| modular reductions | 72 |
| cycle edge checks | 72 |
| primitive operations excluding the small sort | 288 |
| median wall time | 0.000151 s |
| maximum wall time | 0.016317 s |

These measurements used prototype seeds 90000 through 90031. The same figures
are also recorded in `rejection_measurements.json`.

The supposed compact route is exactly the same sequence: take those gcds,
reduce one tag per block, sort, and check. Its length is therefore about 288
primitive operations plus sorting, not meaningfully shorter than the strongest
mechanical route. Moreover, the tags are external metadata absent from the
paper; they make the answer easier without exercising the parity obstacle,
absorber, reservoir, or minimum-degree structure.

## Gate summary and scope

| gate | result |
|---|---|
| G -- generatable | passes by inverse generation |
| H -- Track A | fails: no distributional theorem, and standard search solved 64/64 |
| H -- Track B | fails: natural family has no shortcut; tag shortcut is its fastest algorithm |
| V -- verifiable | passes in linear time by checking the partition and the \(2t\) required hyperedges |

This is not a `cap_bound` or G9 rejection. Answers at the measured sizes fit
the output cap. The failure occurs earlier, at Step 0's discriminating
hardness test. No oracle failure is used as evidence: the retained transcript
contains only OpenRouter HTTP 403 account-limit errors, which correctly count
as neither solved nor failed attempts.

## What could reopen the paper

A new attempt would need either (1) a paper-licensed reduction proving hardness
for a specific generated distribution, not merely general worst-case
NP-completeness, or (2) a paper-native invariant whose compact cycle
construction is substantially shorter than the strongest executable
recognition algorithm. I found neither in Theorem 1.2, the non-extremal
absorbing argument, or the extremal parity construction.
