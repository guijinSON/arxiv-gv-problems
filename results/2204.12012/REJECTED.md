# Rejected at Step 0: planting does not inherit the extremal theorem's hardness

Paper: Bingyu Luan, Yantao Tang, Guanghui Wang, and Donglei Yang,
[*Balanced subdivisions of cliques in graphs*](https://arxiv.org/abs/2204.12012),
arXiv:2204.12012v2.

## Decision

No generator is shipped. The proposed family—plant an equal-length subdivided
clique in a larger random graph—passes **G** by inverse generation and **V** by
checking the paths, but fails **H on Track A**. The paper proves an extremal
existence threshold, not distributional hardness for an inverse-planted random
graph. In the natural dense regime, a standard common-neighbour matching attack
finds unrelated witnesses almost immediately. Sparse noise instead leaves a
detectable degree signature around the planted branch vertices.

**Track B does not rescue the proposal.** The paper provides no short,
solver-visible invariant that identifies the planted vertices. At the measured
dense setting, the ordinary matching route is already tiny. The shorter route
held privately by the generator is not available from the instance; publishing
it would reduce the problem to transcription.

| requirement | result |
|---|---|
| G — certificate known without solving | Pass for inverse planting: sample branch vertices and internally disjoint equal-length paths first, then add noise. |
| H — Track A structural hardness | **Fails:** no result in the paper covers the planted distribution, and the domain-standard length-2 matching attack solved 20/20 measured instances. |
| H — Track B no-tool compression | **Fails:** 3,138 median adjacency probes plus 316.5 matching augment calls versus about 210 private plant-output/check actions, with no public compact route. |
| V — exact witness checking | Pass: check vertex ranges, distinct internal vertices, common path length, endpoints, and every graph edge. |
| overall | **Rejected at Step 0.** Steps 1–4 were not run and no gate reports or oracle transcripts were fabricated. |

This is not a `cap_bound` decision. A length-2 witness for the measured
`k = 12` case has 12 branch vertices and 66 internal vertices, only 78 atoms.
The blocker is hardness, not answer length.

## What the paper actually says

Section 1 gives the exact native definition. A subdivision replaces edges of a
graph by internally vertex-disjoint paths. A balanced subdivision
`TK_k^(z)` replaces **every** edge of `K_k` by a path of the same edge length
`z`; therefore every pair of branch vertices needs its own path, and all
`binom(k,2)` paths may intersect only at their branch endpoints.

Theorem 1.2 says that, for an absolute `c > 0` and sufficiently large average
degree `d`, every graph of average degree at least `d` contains some
`TK_(c sqrt(d))^(z)`. Theorem 1.3 strengthens the order to `cd` for `C4`-free
graphs. Neither theorem is a computational-hardness statement, and both the
constant and the sufficiently-large threshold are existential.

Section 2.3 splits the proof into dense and sparse expander cases. Lemma 2.7
handles `d >= log^240 n`; Lemma 2.8, imported from Wang, handles the complementary
expander regime. In the dense proof, Section 3 builds units whose cores become
branch vertices, uses adjusters to control path length, and greedily accumulates
internally disjoint paths. Lemmas 3.6 and 3.7 explicitly show why dense graphs
already contain large balanced subdivisions of lengths 2 and 4. These are
existence and construction ingredients, not evidence that finding one in the
generated distribution is difficult.

## Step-0 certificate-production question

There are two possible production routes, and neither yields G, H, and V
together.

1. **Rely on Theorem 1.2 or 1.3.** A sampled high-degree graph is guaranteed to
   contain a witness only in a non-explicit asymptotic regime. To place the
   actual branch vertices and paths in `inst["answer"]`, the generator would
   still have to execute the paper's graph-wide unit/adjuster/path searches (or
   another subdivision algorithm). That obtains the answer by solving the
   generated instance, contrary to G.
2. **Plant the paths first.** This repairs G and leaves exact verification cheap,
   but changes the theorem's arbitrary high-degree input into a conditioned
   planted distribution. The paper contains no average-case hardness,
   indistinguishability, or quiet-planting result for that law. The measured
   attacks below show the most direct version is easy.

The proof's use of expanders and adjusters does not give a Track-B shortcut to
the individual vertex labels. Applying those tools still requires inspecting
and searching the supplied graph. Conversely, if the generator exposes its
chosen units or paths, it exposes the witness.

## Measured audit of the proposed planted family

The audit used the smallest nontrivial balanced-path version, `z = 2`, where a
path between branch vertices `u,v` is `u-w-v`. For each seed:

- `n = 256`, `k = 12`;
- sample 12 branch vertices and 66 distinct internal vertices;
- add the two path edges for each of the 66 branch pairs;
- independently add every other graph edge with probability `p`;
- randomly relabel all 256 vertices.

The standard attack fixes 12 candidate branch vertices, creates one left-hand
node for each of their 66 unordered pairs, connects that pair to every common
neighbour outside the branch set, and finds a matching covering all 66 pairs.
Such a matching is itself the complete exact certificate for a
`TK_12^(2)`: each matched common neighbour is a distinct internal vertex.

At `p = 0.20`, even the arbitrary candidate set `{0,...,11}` worked on **20/20**
seeds. It intersected the hidden planted branch set in between 0 and 4 vertices,
so these were overwhelmingly unrelated witnesses rather than plant recovery.

| measured quantity at `p = 0.20` | minimum | median | maximum |
|---|---:|---:|---:|
| adjacency probes used to build common-neighbour sets | 2,937 | **3,138** | 3,448 |
| recursive matching augment calls | 231 | **316.5** | 504 |
| wall-clock seconds in CPython | 0.000300 | **0.000339** | 0.002767 |

A second sweep used seeds 0–39 at each density. `top-degree match` means taking
the 12 highest-degree vertices and running the same exact matching check;
`first-12 match` uses an arbitrary fixed branch set.

| `p` | top 12 equal the planted branches | top-degree match succeeds | first-12 match succeeds | median planted vertices among top 12 |
|---:|---:|---:|---:|---:|
| 0.02 | 16/40 | 16/40 | 0/40 | 11 |
| 0.03 | 4/40 | 4/40 | 0/40 | 10 |
| 0.04 | 1/40 | 1/40 | 0/40 | 9 |
| 0.05 | 0/40 | 1/40 | 0/40 | 8 |
| 0.06 | 1/40 | 2/40 | 0/40 | 8 |
| 0.08 | 0/40 | 14/40 | 0/40 | 7 |
| 0.10 | 0/40 | 36/40 | 0/40 | 6 |
| 0.15 | 0/40 | 40/40 | 33/40 | 4.5 |
| 0.20 | 0/40 | 40/40 | 40/40 | 3 |

Thus sparse settings leak branch degree, while denser settings contain abundant
unrelated subdivisions. Any nonzero attack success would already violate the
Track-A G6 requirement. A tiny uniform-guess probability would not repair this:
candidate density and algorithmic recovery cost are separate gates.

## Mechanical cost versus compact route

For the dense proposed shipping-sized example, the successful mechanical route
costs a median **3,138 adjacency probes + 316.5 augment calls** and **0.000339
seconds**. Its complexity after choosing branch candidates is polynomial: build
the 66 common-neighbour sets and run bipartite matching.

The generator's private planted certificate has 78 vertex labels. Merely writing
those labels and checking the 132 path edges is about **210 primitive
output/check actions**. That private route is not a solver-visible compact route.
Even if it were revealed, the measured comparison would be roughly 3,455 small
operations versus 210, not the million mechanical operations versus a dozen
structural operations that Track B is intended to capture. Without revealing
the plant, the shortest identified public route is the same common-neighbour
construction and matching used above; there is no separate invariant or change
of variables in the paper that recovers the planted labels.

Longer common path length does not fix the principle. In dense expanders, the
paper's own Sections 2–4 are devoted to supplying many short connections and
adjusting them to a common length. In sparse random noise, the forced paths
contribute still more local degree and neighbourhood signal unless a separate
quiet-planting theorem is supplied.

## Other native formulations considered

| candidate | G | H | V | outcome |
|---|---:|---:|---:|---|
| Plant a balanced `TK_k^(z)` in random noise | pass | **Track A fails/unsupported; measured attacks succeed** | pass | Rejected |
| Sample a graph satisfying Theorem 1.2 and ask for the promised subdivision | **fails unless the generator searches for it** | no hardness result | pass once paths are known | Rejected |
| Use the `C4`-free Theorem 1.3 regime | same certificate-search problem; practical parameters are not covered by explicit constants | no distributional hardness | pass | Rejected |
| Subdivide every edge of a planted-clique instance once | pass by transformation | would rely on an external planted-clique assumption, not any theorem in this paper; it also compiles the balanced-path task back to ordinary clique search | pass | Not a paper-backed rescue |
| Ask for the two disjoint isomorphic subdivisions mentioned after Theorem 1.2 | pass only after a larger balanced subdivision is already known | splitting known branch vertices is direct; finding the larger object has the original problem | pass | No new hard family |

Inventing affine labels, checksums, or a hidden algebraic selector could create a
Track-B puzzle with a public shortcut. It would test that added encoding rather
than the paper's units, adjusters, or extremal threshold, so it is not used to
claim coverage of this paper.

No `gen_2204_12012.py` was written, so there is no implementation to rename and
retain. This is the required early stop after the Step-0 H failure.
