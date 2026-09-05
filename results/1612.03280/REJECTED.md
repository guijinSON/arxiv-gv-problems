# Rejected: arXiv 1612.03280

Paper: F. Ramezani, [*Coloring Problem of Signed Interval
Graphs*](https://arxiv.org/abs/1612.03280), v2 (2019).

## Decision

The tested family passes **G** and **V**, but fails **H on Track B** and the
polarity-flipped **G9(b)** gate.  The named hard preset held on the bare prompt,
but all three hinted oracles solved it.  The one permitted higher rung was then
retested: one of three bare oracles solved it and all three hinted oracles solved
it.  The rules prohibit another adjustment, so the family is rejected rather
than shipped.

Track A is not available for this generator.  Theorem 5 proves worst-case
NP-completeness for arbitrary negative signatures; it does not establish
average-case hardness for the inverse-planted matching distribution used here.
That specialized distribution also has a polynomial matching algorithm by
construction.

The experimental module is retained as `rejected_gen_1612_03280.py`.  The
script-owned bare transcript remains `llm_loop_transcript.jsonl`; the failed
G9 arm and the permitted higher-rung reruns are retained as
`g9_hinted_transcript.jsonl`, `g9_escalated_bare_transcript.jsonl`, and
`g9_escalated_hinted_transcript.jsonl`.

## Paper definition and theorem used

Section 1 fixes the Naserasr--Rollova--Sopena coloring notion used by `INTSCOL`.
After switching any vertex set, adjacent vertices must have different colors,
and edges with different signs may not carry the same unordered endpoint-color
pair.  This is not Zaslavsky's integer-color definition from the preceding
paragraphs.

Section 3, Theorem 5 proves `INTSCOL` NP-complete even when the interval ground
graph is two disjoint cliques.  Given an arbitrary graph `G` on `N` vertices,
the first clique is all-positive and the negative edges of the second clique are
exactly `E(G)`.  A biclique of size `k` in `G` can be switched to an all-positive
set and decoded into a signed coloring with `2N-k` colors.  Section 2 explicitly
allows one side of a biclique to be empty, so an independent set is a permitted
source biclique.

The paper also identifies regimes that cannot support a Track A claim here:

- Section 2 recalls polynomial greedy coloring for ordinary interval graphs.
- Section 3, Theorem 4 puts signed-clique search `INTSCLIQ` in P for a bounded
  number of maximal cliques.
- Section 4, Proposition 2(a) characterizes connected signed interval graphs of
  signed chromatic number two by caterpillar ground graphs.

## Tested construction

For `n` rows and columns, every row contains `d` cells.  The generator samples a
modular displacement `s` first and inserts the perfect matching
`row r -> column r+s (mod n)`, then adds `d-1` random decoys per row and shuffles
rows, cells, and vertex IDs.  Plant and decoy cells have the same one-cell
marginals.

The second interval clique has one vertex per cell.  Its edge is negative
exactly when the cells share a row or column.  A collision-free transversal is
therefore an independent set, hence the degenerate biclique allowed by the
paper.  Theorem 5 turns it into a proper signed coloring.  The compact answer is
the selected vertex ID in each displayed row; the verifier checks membership,
distinctness, and column collisions exactly without consulting `inst["answer"]`.
The certificate is sampled before the decoys, so G is inverse generation rather
than solving the generated instance.

## Mechanical cost and compact route

This was an honest Track B attempt.  Hopcroft--Karp is the disclosed reference
algorithm and runs in `O(E sqrt(V))` on the row--column graph.  A local eight-seed
measurement gave:

| parameters | mechanical reference cost | compact route | answer size |
|---|---:|---:|---:|
| `n=127,d=12` | median 3,820.5 edge scans, 0.00044 s | at most 163 modular operations | 127 atoms, 544 chars |
| `n=149,d=14` | median 4,930.5 edge scans, 0.00062 s | at most 191 modular operations | 149 atoms, 679 chars |

The compact route computes `column-row mod n` in the first three displayed rows,
whose common displacement is construction-guaranteed to be unique, and uses it
in every row.  Thus the initial mechanical/compact gap was real (roughly 25-fold
by edge scans at the higher rung), and the existence of an efficient algorithm
was not itself the rejection reason.  The rejection is empirical: once the
structural invariant alone was named, every tested oracle executed the compact
route successfully.  The invariant therefore does not create the intended
no-tool difficulty.

## Local gates

At the named hard preset, the retained module reports:

| gate | result |
|---|---|
| G1 | 12/12 planted certificates verified across all presets and seeds |
| G2 | five corruptions rejected with five distinct reasons |
| G3 | model-style fenced response round-tripped exactly |
| G4 | 0/200,000 structure-aware random candidates valid; language size `12^127` |
| G5 | demo has exactly 2 valid answers among 32; shipping density 0/200,000 |
| G6 | four attacks each 0/8; Hopcroft--Karp reference 8/8 as expected |
| G7 | doubled `n=254` instance built and verified |
| G8 | 80/80 relabeling checks invariant; 20/20 unrelated keys distinct |
| G9(c) | 544 chars, 127 atoms, about 136 tokens; intended route 163 operations |

The four failed G6 attacks were minimum-column-degree outlier selection,
first-unused greedy matching, 256 random restarts, and the fixed affine offsets
`0,+1,-1`.  The G4 zero-hit result concerns only the declared prior--one uniform
listed-cell choice per row--and says nothing about matching algorithms or the
modular invariant.

## Oracle evidence and G9(b)

The official bare loop at medium reasoning produced:

| rung | solved / attempts | outcome |
|---|---:|---|
| easy `n=61,d=8` | 3/3 | defeated |
| medium `n=89,d=10` | 2/3 | defeated |
| hard `n=127,d=12` | 0/3 | bare prompt held |

The compliant one-sentence hint was: *“The planted transversal is characterized
by a common value of column minus row modulo n.”*  It names only the invariant;
it does not chain steps or state the algorithm.  G9 results were:

| rung and arm | solved / attempts | conclusion |
|---|---:|---|
| `n=127,d=12`, hinted | 3/3 | G9(b) failed |
| `n=149,d=14`, bare | 1/3 | permitted higher rung did not harden |
| `n=149,d=14`, hinted | 3/3 | G9(b) still failed |

The placebo arm was not run after the gated hinted failure; it is diagnostic and
cannot reverse either G9(b) result.  Some bare failures were empty
length-limited replies, but every defeated rung also contains a clean parsed
certificate with `verify_reason="ok"`, so the rejection does not rely on API or
parser failures.

## Why no replacement family is claimed

A random planted balanced subset in the second clique would amount to a planted
clique-style distribution.  The paper supplies no average-case hardness theorem
for it, so relabeling that idea Track A would turn worst-case NP-completeness into
an unsupported distributional claim.  `INTSCLIQ` is explicitly polynomial by
Theorem 4.  Proposition 1's Minimum Signature reduction starts from Maximum Cut;
sampling a cut first again gives an unsupported planted distribution, while an
arbitrary hard instance loses the known certificate.  No further paper-backed
family simultaneously clears G, H, and V.

## Final gate disposition

| requirement | disposition |
|---|---|
| G | **Pass:** sample the modular perfect matching first and carry it through Theorem 5 |
| H, Track A | Not claimed: the paper proves worst-case, not planted-distribution, hardness |
| H, Track B | **Fail:** the compact invariant was solved at both tested rungs |
| V | **Pass:** exact row, column, signed-edge, and decoded-color checks |
| G9(b) | **Fail:** hinted pool solved 3/3 at both rungs |
| Overall | **Rejected** |
