# Rejected at Step 0: arXiv 1106.1258

Paper: Jiuying Dong and Xueliang Li, [*Sharp upper bound for the
rainbow connection number of a graph with diameter 2*](https://arxiv.org/abs/1106.1258)
(v3, 2011).

## Decision

No problem family from this paper clears **G + H + V**.  The native witness—a
rainbow edge-colouring—is generatable and exactly checkable, but the available
families fail **H on both tracks**.  This is not a rejection merely because an
efficient algorithm exists: the mechanical and compact costs are quantified
below, and the compressed alternative fails the structure-aware guessing and
adversary requirements outright.

Implementation stopped before Step 1, as required after a Step-0 failure.  No
generator, self-test report, README, or oracle transcripts were fabricated.

## What the paper actually says

Section 1 works with finite simple undirected graphs.  An edge-colouring need
not be proper: adjacent edges may have the same colour.  A path is *rainbow* if
its edge colours are pairwise distinct, and `rc(G)` is the least number of
colours in an edge-colouring for which every two distinct vertices have a
rainbow path.

Theorem 1 states that every connected, bridgeless graph of diameter two has a
rainbow colouring with at most five colours, and that five is sharp.  More
importantly for this task, Section 3 proves the upper bound constructively.  It
chooses a centre `u`, partitions its first and second neighbourhoods, repeatedly
selects shortest 3-, 4-, or 5-cycles through `u`, and gives explicit colours in
every case.  All searched cycles have bounded length and all remaining choices
are finite neighbourhood scans or maximal-set constructions.  Thus the proof
is a polynomial certificate-producing procedure, not only an existence proof.

Section 2 supplies the sharp examples.  For `k >= 17`, take paths

```text
u--v_i--w_i,  i = 1,...,k,
```

and make all the `w_i` vertices a clique.  The graph has diameter two and is
bridgeless.  Any four-colouring assigns one of only `4^2 = 16` ordered colour
pairs to each two-edge spoke, so two of the 17 spokes agree; the paper's
pigeonhole argument then rules out a rainbow path between their `v` endpoints.
The paper also writes down the matching five-colouring:

```text
c(u,v_1)=1, c(v_1,w_1)=2;
c(u,v_i)=3, c(v_i,w_i)=4 for i>=2;
c(w_i,w_j)=5 for every clique edge.
```

This exact formula is what produces the natural certificate.

The Introduction mentions that deciding whether `rc(G)=2` is NP-complete and
computing `rc(G)` is NP-hard, but these are cited worst-case results from
Chakraborty et al., not a distributional theorem for instances generated here.
They do not establish Track-A hardness for planted colourings, randomly hidden
colours, or the Section 2 sharp examples.

## Step-0 certificate question

| Native proposed task | Certificate producer | Result |
|---|---|---|
| Given a bridgeless diameter-two graph, return a five-colouring | The explicit cycle/neighbourhood construction in the proof of Theorem 1 | G and V pass; Track A fails because the target distribution has a polynomial constructor. |
| Colour the Section 2 sharp graph | The three-line formula displayed above | G and V pass; the obvious structural ansatz succeeds on every instance. |
| Randomly relabel that sharp graph | Recover its degree classes, then use the same formula | Relabelling does not hide the construction and does not create canonically distinct instances. |
| Plant a colouring and erase colours | The retained planted colouring | G and V pass, but the paper proves no hardness for precolouring completion or for this planted distribution. |
| Decide/find a two-colouring | A SAT/CSP search for the constraints on common neighbours | Only worst-case NP-hardness is cited; inverse generation supplies no average-case or distributional basis for Track A. |
| Certify `rc(G)=5` for the sharp graph | Upper colouring plus the Section 2 pigeonhole lower-bound argument | The number `5` alone is not a witness; a structural proof certificate is immediately recovered from degree classes, while a raw bounded refutation is neither supplied nor scalable under the answer cap. |

Verification itself would be exact and cheap enough.  For a submitted
five-colouring, a checker can run reachability on states `(vertex, used-colour
mask)` and check every source, using at most 32 masks per vertex.  This clears V
but says nothing about H.

## Mechanical cost versus compact route

The sharp graph has

```text
m(k) = 2k + k(k-1)/2
```

edges, so a natural full-colouring witness has `m(k)` atomic colour entries.
The largest sharp example fitting the 256-atom cap is `k=21`:

| quantity | `k=17` (first sharp example) | `k=21` (largest writable example) |
|---|---:|---:|
| vertices | 35 | 43 |
| edges / answer atoms | 170 | 252 |
| compact JSON colour-list characters | 341 | 505 |
| measured Section 2 constructor | 6.36 microseconds | 9.57 microseconds |

The timing is the median per construction over nine batches of 20,000 calls in
standard-library Python.  The constructor visits each edge once and performs
exactly 170 or 252 colour assignments.  No graph search is involved.

For a **full edge-colouring answer**, the compact route after recognizing the
paper's structure is not shorter than the mechanical route: it is the same
formula and still requires all 252 colour emissions at `k=21`.  Both are
`Theta(k^2)`, with a mechanical/compact output-operation ratio of **1:1**.
Increasing `k` only lengthens the answer and crosses the atom cap at `k=22`
(`m(22)=275`); it does not open a compression gap.

For a **symbolic compressed answer**, the natural executable certificate is an
exceptional spoke together with a permutation of the five colour names.  That
is only about six atoms and expands exactly to the displayed colouring.  But
every one of the `k` exceptional-spoke choices works, and every permutation of
the five colours preserves rainbow connectivity.  Consequently a
structure-aware sampler over precisely this bounded language has

```text
P(valid random candidate) = (k * 5!) / (k * 5!) = 1,
```

not less than `1e-6`.  Restricting the language to the canonical palette merely
changes this to `k/k = 1`.  The by-hand attack “identify the spoke/clique roles
and apply the displayed exceptional-spoke template” succeeds on every seed, so
it cannot be one of Track B's required failing in-context attacks.

Random vertex labels do not rescue the task.  In the exact sharp graph the
`v_i` have degree two.  Among the degree-`k` vertices, `u` is the unique one all
of whose neighbours have degree two; the other degree-`k` vertices form the
`w_i` clique.  A linear degree/neighbourhood scan recovers all roles, after
which any spoke may be exceptional.  Moreover, all random relabellings of one
`G_k` have the same correct canonical key, so seeds at fixed `k` are duplicates
rather than an unlimited supply of instances.

## Why neither hardness track applies

### Track A — structural hardness

Track A fails.  Theorem 1's proof itself constructs a certificate in polynomial
time for every graph in the theorem's regime.  On the paper's only explicit
scalable distribution, Section 2 gives the even simpler output-linear formula
measured above.  The cited NP-hardness of determining `rc(G)` is worst-case and
does not cover the generated distribution.  Adding random edges or erasing
planted colours would define a new distribution for which this paper gives no
average-case hardness result; cardinality of its colouring space would not
repair that missing evidence.

### Track B — no-tool compression

Track B also fails, for both possible representations:

- With the native full colouring, the mechanical constructor and the compact
  route are the same 252-output procedure at the largest writable size.  The
  answer itself consumes the work; there is no million-operation computation
  compressed by a short invariant.
- With an executable symbolic colouring rule, the answer is constant-size but
  every well-formed template candidate is valid.  The obvious degree-class
  ansatz recovers such a rule directly and succeeds 8/8 in principle (indeed,
  for every relabelling), so G4 and the mandatory fourth in-context G6 attack
  fail before an oracle run.

Trying to obscure the Section 2 subgraph with random supergraph edges creates a
dichotomy rather than a solution.  If the embedded roles remain visible, the
same attack succeeds.  If they are hidden well enough to require clique/CSP
search, the short compact route is gone and the intended no-tool work is the
mechanical search itself; the paper supplies neither that new hardness claim
nor a sub-300-operation structural decoder.  The benchmark's difficulty would
come from an added planted-subgraph surrogate, not from the paper's rainbow
connection argument.

## Gate diagnosis

| Requirement | Result |
|---|---|
| G — known certificate by construction | **Passable.** Use Theorem 1's constructive proof or Section 2's explicit colouring. |
| V — exact witness verification | **Passable.** Check edge colours and exact mask-state reachability for every vertex pair. |
| H — Track A | **Fails.** A polynomial constructor exists for the entire theorem regime; the only NP-hardness statement is worst-case and does not apply to a planted distribution. |
| H — Track B, full witness | **Fails.** 252 mechanical assignments versus the same 252 mandatory compact-route emissions at the largest writable sharp example; measured median 9.57 microseconds. |
| H — Track B, compressed witness | **Fails.** Every exceptional-spoke/palette candidate is valid, giving structure-aware guess probability 1, and the obvious structural ansatz always succeeds. |
| G8 diversity for the exact sharp examples | **Fails at fixed size.** Seeds only relabel one graph and must share a canonical key. |
| Overall | **Rejected at Step 0.** No paper-native family found simultaneously satisfies G, H, and V. |

This rejection deliberately does not run the 200,000-guess gate or the LLM
hardening loop.  The analytic structure-aware probability is already one for
the only compact certificate language, while the full language is defeated by
the paper's explicit constructor; oracle failures on a 252-entry transcription
would not supply the missing hardness.
