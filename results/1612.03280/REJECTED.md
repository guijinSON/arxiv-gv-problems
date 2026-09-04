# Rejected: arXiv 1612.03280

Paper: F. Ramezani, [*Coloring Problem of Signed Interval
Graphs*](https://arxiv.org/abs/1612.03280), v2 (2019).

## Decision

The tested family passes **G** and **V**, but fails **H on Track B**.  The
repository-owned bare oracle loop returned `too_easy`: at least one model produced
a certificate that parsed and verified at every rung through the maximum permitted
three escalations.  The rules therefore prohibit further hand tuning or shipping.

Track A was never claimed.  The paper proves worst-case NP-completeness by reduction
from Maximum Biclique; it does not prove average-case hardness for an inverse-planted
matching distribution.  Moreover, the tested distribution has a polynomial
Hopcroft--Karp solver by design.  Calling it Track A would be false.

The experimental `gen_1612_03280.py`, `llm_loop_transcript.jsonl`, and `.meta.json`
are retained as evidence.  There is deliberately no shipping `README.md`,
`selftest_report.json`, or hinted/placebo transcript: the mandatory bare STEP 4 run
failed first, so G9 was never reached.

## What the paper actually defines

Section 1 defines the Naserasr--Rollova--Sopena coloring used by `INTSCOL`.  After
switching any set of vertices, a proper coloring must satisfy both conditions:

1. adjacent vertices receive different colors; and
2. two edges with different signs may not have the same unordered pair of endpoint
   colors.

This is not Zaslavsky's integer coloring from the preceding paragraphs.  `INTSCOL`
asks whether the signed chromatic number is at most `k` for a signed interval graph
whose ground graph has at most a fixed number `l0` of maximal cliques.

Section 3, Theorem 5 proves `INTSCOL` NP-complete even with two maximal cliques.  For
an `N`-vertex graph `G`, it forms two disjoint copies of `K_N`: the first clique has
only positive edges, while the negative edges of the second clique are exactly the
edges of `G`.  A biclique of size `k` in `G` switches to an all-positive `k`-set and
gives a coloring with `2N-k` colors.  Section 2 explicitly permits a biclique with
one empty side, so an independent set is a valid source biclique.

The paper also identifies easy regimes that must not be presented as Track A:

- Section 2 recalls polynomial greedy coloring of ordinary interval graphs from a
  perfect elimination ordering.
- Section 3, Theorem 4 puts the signed-clique problem `INTSCLIQ` in P when the number
  of maximal cliques is bounded.  Its proof builds the auxiliary graph `I*` and
  recursively solves maximum independent-set subproblems.
- Section 4, Proposition 2(a) characterizes connected signed interval graphs of
  signed chromatic number two by caterpillar ground graphs.

## The family that was tested

The generator used Theorem 5 without replacing the signed interval graph by a bare
surrogate.  Both interval cliques, every edge-sign rule, the signed-coloring
definition, and the coloring decoder were included in the rendered problem.

For `n` rows and `n` columns, each row received `d` allowed cells.  The generator
first sampled a modular displacement `s` and planted the perfect matching

```text
row r  ->  column r+s (mod n).
```

It then added `d-1` uniformly sampled decoy cells per row and independently shuffled
row order, cell order, and the second-clique vertex IDs.  Conditioned on a row's
unordered offset set, the planted offset is uniform among its `d` entries, so plant
and decoy cells have the same one-cell marginals.

The negative-edge graph in the second interval clique was the cell-conflict graph:
two cell vertices were negative exactly when they shared a row or column.  One cell
per row with distinct columns is therefore an independent set of size `n`, hence the
degenerate biclique allowed in Section 2.  Theorem 5 decodes it to a proper signed
coloring with `2N-n` colors, where `N=nd` is each clique's size.  The verifier checks
row membership, column distinctness, and the resulting positive repeated color
pairs without reading the planted answer.

This is valid inverse generation: the matching and its signed-coloring certificate
exist before any decoys are drawn.  No generated instance is solved to obtain
`inst["answer"]`.

## Mechanical cost and compact route

This was an honest Track B attempt.  The disclosed reference algorithm is
Hopcroft--Karp on the represented row--column graph.  Its complexity is
`O(E sqrt(V))`, with `E=nd` and `V=2n`; it succeeded on 8/8 local instances at both
the named hard and final escalated configurations.

| configuration | mechanical reference cost | compact route |
|---|---:|---:|
| hard `n=127,d=12` | median 3,820.5 edge scans, 0.000196 s | at most `n+3d = 163` modular operations |
| final `n=149,d=14` | median 4,930.5 edge scans, 0.000246 s | at most `n+3d = 191` modular operations |

The compact route computes `column-row mod n` in the first three displayed rows.
Their intersection is construction-guaranteed to contain only the planted
displacement.  It then selects that displacement in every row.  Thus a real
mechanical/compact gap existed: roughly five thousand graph-search edge scans versus
191 small modular operations at the final rung.  This justified testing Track B
rather than rejecting merely because an efficient algorithm exists.

It did **not** justify shipping.  The oracle results show that the compact pattern is
still executable in context often enough to defeat every allowed rung.  Mechanical
cost being inconvenient by hand is not sufficient once the evaluated models can
recover the shorter route.

## Local gate evidence before the oracle failure

At the named hard preset (`n=127,d=12`), the experimental module recorded:

| check | result |
|---|---:|
| planted certificates | 12/12 verified across all presets and three seeds each |
| structure-aware random candidates | 0/200,000 valid |
| bounded candidate language | `12^127` ordered one-cell-per-row strings |
| exact demo count | 2 valid matchings among `2^5 = 32` candidates |
| minimum-column-degree outlier attack | 0/8 |
| first-unused greedy matching | 0/8 |
| 256 random restarts per seed | 0/8 |
| fixed offsets `0,+1,-1` | 0/8 |
| Hopcroft--Karp reference | 8/8, as expected |
| canonical-key relabeling tests | 80/80 invariant with carried witnesses valid |
| unrelated canonical keys | 20/20 distinct |

The zero random hits only bound success under the declared prior: independently
choose one of the `d` listed cells in every row.  They do not estimate the success of
matching algorithms or of the modular invariant, which is why the reference solver
and oracle loop are decisive.

The 127-entry hard answer measured 538 characters (135 approximate tokens) on the
gate seed, and the final escalated answer had 149 atoms and 819 characters according
to `harden.py`.  Both are below the output cap.  Two difficulty axes moved (`n` and
`d`), and the final compact route remained below 300 operations.  This is therefore
not a `cap_bound` or single-axis rejection.

## Mandatory bare oracle result

The official `scripts/harden.py` run used the four-vendor pool at medium reasoning
effort.  A rung is held only when all three distinct models fail; any verified solve
defeats it.

| round | rung | solved / attempts | verified solvers | outcome |
|---:|---|---:|---|---|
| 0 | easy `n=61,d=8` | 3/3 | Terra, Grok, Gemini | defeated |
| 1 | medium `n=89,d=10` | 2/3 | Terra, Gemini | defeated |
| 2 | hard `n=127,d=12` | 1/3 | Terra | defeated |
| 3 | escalated `n=149,d=14` | 1/3 | Gemini | **defeated** |

Several failed calls exhausted their reasoning/output budget or returned a nearly
correct list with one wrong-row or repeated-column error.  Those failures do not
rescue the family because the same rung also had a clean certificate with
`verify_reason="ok"`.  The script-owned final verdict is:

```json
{"verdict":"too_easy","escalations_used":3,"axes_moved":["degree","n"],"answer_atoms":149,"answer_chars":819}
```

## Why the prior triage and other paper routes do not rescue it

The prior suggestion to “plant a valid signed coloring, then add random interval
constraints preserving it” omits the paper's second color-pair condition and gives
no distributional hardness theorem.  Arbitrary independently added interval edges
need not preserve a Naserasr coloring.  Theorem 5's two-clique construction is the
paper-backed way to preserve the witness, and that is what was tested.

Other native candidates do not justify continuing this run:

- Planting a balanced `k`-subset directly in a random signed clique reduces, after
  switching relative to an anchor, to planted clique.  The paper supplies no
  average-case hardness result for that distribution, and below known spectral
  regimes there is no sub-300-operation compact route.  It cannot honestly replace
  this failed Track B family with a Track A claim.
- `INTSCLIQ` is explicitly in P by Theorem 4.  It could only be Track B, but the
  paper's recursive auxiliary-graph algorithm supplies the certificate directly and
  no distinct compact no-tool shortcut is given.
- Section 4, Proposition 1 reduces Minimum Signature to Maximum Edge Cut.  Sampling
  a cut first would again create an unsupported planted distribution; using an
  arbitrary hard Max-Cut instance would lose the known certificate.
- Proposition 2's small-chromatic-number cases are structural classifications and
  are directly recognizable, so they fail H rather than furnish a harder family.

The bare hardening cap has been reached, so inventing a new encoding, hiding the
modular coordinates, or escalating again would tune the generator to this oracle
run.  The required disposition is rejection.

## Gate outcome

| requirement | result |
|---|---|
| G — certificate known by construction | **Pass:** sample the modular perfect matching first, then map its independent set through Theorem 5 |
| H — Track A | Not claimed; Theorem 5 is worst-case and does not cover this planted distribution |
| H — Track B | **Fail:** a verified oracle solve occurred at every rung through the maximum escalation |
| V — cheap exact witness checking | **Pass:** row, column, signed-edge, and decoded color-pair checks use exact integers |
| G9 hinted gate | Not run; the stronger prerequisite bare loop already returned `too_easy` |
| Overall | **Rejected** |
