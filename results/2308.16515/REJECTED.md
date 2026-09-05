# Rejected after the bare hardening loop: arXiv:2308.16515

Track considered: **B (no-tool compression)**. The retained implementation is
`rejected_gen_2308_16515.py`; it is not a shippable generator. The final bare
evidence is the script-owned `llm_loop_transcript.jsonl`, and `.meta.json`
records `verdict: "too_easy"` after the permitted three escalations.

## What the paper actually establishes

Sheng and Xiao, [*A Discharging Method: Improved Kernels for Edge Triangle
Packing and Covering*](https://arxiv.org/abs/2308.16515), defines Edge Triangle
Packing and Edge Triangle Covering in Section 2. An edge packing contains
triangles that share no edge; an edge cover is a set of graph edges meeting
every triangle.

Section 3 defines a fat-head crown `(C,H,X)`. Its finite witness is a packing of
`|H|` triangles, each containing one vertex of `C` and one distinct edge of
`H`. Lemma 3 proves that this witness composes with a packing in the reduced
graph. These facts clear G and V: a witness packing can be constructed first,
and a checker only has to recompute graph edges and edge-disjointness.

The decisive easy result is Lemma 2. Its proof builds a bipartite graph between
candidate `C` vertices and candidate `H` edges, with incidence exactly when a
vertex spans an edge, and obtains the crown witness by matching. The paper
states an `O(m n^1.5)` implementation through the expansion lemma. Section 4.2
also obtains a maximal edge-triangle packing by an arbitrary polynomial-time
greedy scan. Theorem 5.1 is a polynomial kernelization theorem (at most `3k`
vertices), not a distributional-hardness or witness-generation theorem.

The Introduction cites worst-case NP-hardness for ETP even on planar graphs of
maximum degree 5 and for ETC even on planar graphs of maximum degree 7. It does
not prove that random inverse-generated packings are hard. Therefore those
worst-case statements cannot support Track A for the proposed distribution.

## The retained Track-B attempt

The module constructs the paper's native fat-head crown. There are `p+1` head
edges and `p+1` candidate crown vertices, indexed by the projective line over
`F_p`. A nonsingular 2-by-2 matrix is sampled first; its Möbius action is the
known witness matching. One or two random edge-disjoint permutation matchings
are added as decoys, and all row orders are shuffled. Every head and every
crown vertex has identical incidence degree. The planted matrix is known before
the graph is assembled and is never found by solving the emitted instance.

The answer may be the normalized 2-by-2 matrix or, while it fits the output
cap, the explicit matching. `verify` expands a matrix exactly modulo `p` and
checks every described triangle and all distinctness constraints. It never
reads `inst["answer"]`.

Local gates G1--G8 passed before hardening:

| Measurement | Result at hard (`p=251`, degree 3) |
|---|---:|
| Planted and JSON checks | 16/16 |
| Structure-aware guesses | 0/200,000 |
| Random-greedy baseline | 0/256; 80,541 candidate checks in 0.0133 s |
| Four failing attacks | each 0/8 |
| Reference Hopcroft--Karp | 8/8, as expected |
| Reference work over eight seeds | 28,204 incidence scans; 0.1574 s including construction |
| Canonical-key invariance | 60/60 |
| Carried-witness checks | 60/60 |
| Unrelated fingerprints | 20/20 distinct |
| Planted answer | 18 characters, 4 atoms |
| Largest accepted hard answer | 899 characters, 252 atoms |
| Intended compact route | at most 228 exact operations |

The four failed attacks were equal-degree outlier selection, left-to-right
greedy matching, 256 randomized greedy restarts, and the obvious affine-map
ansatz. The domain-standard algorithm is deliberately outside `attacks`, as
Track B requires.

## Mechanical cost and compact route

At hard seed `271828`, sparse Hopcroft--Karp produced an explicit witness in
**3,213 incidence scans and 0.000307 seconds**. Its complexity is
`O(E sqrt(V))`. The explicit output has 252 entries.

The compact route uses that a projective transformation is fixed by the images
of three points. At degree three, the candidate images of infinity, 0 and 1
give at most `3^3 = 27` hypotheses; the row for 2 isolates the planted one by
construction. Using the direct cross-ratio calculation, the intended route was
bounded at **228 exact field operations** and emits four coefficients.

This is a real compression, so the family was tested on Track B rather than
discarded merely because matching is polynomial. But the mechanical/compact
gap is only about fourteen-fold in the counted operations at the largest named
preset, and the compact route lies fully within the no-tool budget. The oracle
measurements show that strong models execute it reliably.

## Failing gate and oracle evidence

The family fails **H on Track B in the bare STEP 4 loop**. No named preset held,
and the one admissible fixed-answer escalation did not hold either:

| Rung | Parameters | Solved / attempts | Decisive result |
|---|---|---:|---|
| easy | `p=127`, degree 2 | 2/3 | Terra and Grok verified |
| medium | `p=181`, degree 3 | 3/3 | all three verified |
| hard | `p=251`, degree 3 | 2/3 | Grok and Terra verified |
| escalated | `p=503`, degree 4 | 1/3 | Terra verified |

The Claude failures at easy, hard and escalated were empty, length-limited
responses; they count under the harness policy but are weaker than completed
wrong witnesses. The decisive successes were completed outputs for which
`parse_answer` succeeded and `verify` returned `(True, "ok")`.

Escalation stops after degree four because a fifth candidate layer makes the
implemented correspondence search exceed G9(c)'s 300-operation intended-route
cap. Continuing to larger contexts would test prompt scanning or arithmetic
volume, not the claimed projective insight. The corrected harness therefore
records `too_easy`, not `cap_bound` or `budget_bound`. G9 hinted/placebo arms
were not run because the bare family never reached a shipping level.

## Why the prior Track-A proposal also fails

The prior triage suggested planting edge-disjoint triangles directly. A native
prototype sampled 50--85 edge-disjoint triangles first, on 24--34 vertices,
and used their union as the graph. Across five density settings and eight seeds
each, min-column Algorithm X found a full triangle decomposition on **40/40**
instances. It used **63--5,307 nodes and 0.003--0.315 seconds**. Thus this
inverse-generated distribution is not supported by the paper's worst-case
NP-hardness and fails the required standard-algorithm attack for Track A.

## Final diagnosis

| Requirement | Result |
|---|---|
| G -- generatable | Pass: inverse projective matching construction. |
| V -- verifiable | Pass: exact modular expansion and graph checks. |
| H -- Track A | Fail for the tested direct-plant distribution: Algorithm X solved 40/40. |
| H -- Track B | **Fail: every compliant bare rung was solved by the oracle pool.** |
| Overall | **Rejected; no generator is shipped.** |

The retained module and transcripts are intentionally kept so a future audit
can reproduce or redesign the decision.
