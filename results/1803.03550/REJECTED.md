# Rejection: arXiv 1803.03550

Paper: [On Optimal Polyline Simplification using the Hausdorff and Fréchet Distance](https://arxiv.org/abs/1803.03550), Marc van Kreveld, Maarten Löffler, and Lionov Wiratma.

## Decision

No generator is shipped. The native geometric problem clears **V**, and feasibility witnesses can clear **G**, but the available certificate-by-construction families fail **H**. This is an H rejection after checking both tracks, not a rejection because an algorithm merely exists.

| gate | result | reason |
|---|---|---|
| G — generatable | only feasibility, or theorem gadgets with an easy read-off | Subdividing a planted simplification gives a feasible subsequence, but it does not prove that the subsequence is minimum. Theorem 1 gives a known feasible three-vertex simplification, while the hardness reductions need a source-instance witness. |
| H — Track A | fail | Theorems 4 and 6 are worst-case NP-hardness reductions. They give no average-case or planted-distribution hardness statement. Planting a Hamiltonian cycle or a line cover therefore does not justify hardness of the generated distribution. |
| H — Track B | fail | For every paper-backed inverse construction found here, the strongest construction-aware certificate extractor is asymptotically the same route as the proposed compact insight; the costs below are comparable. |
| V — verifiable | pass in principle | A claimed subsequence and its Hausdorff or Fréchet bound can be checked by exact geometric predicates/free-space reachability. This does not establish optimality unless the task is phrased as a bounded decision witness or carries a separately generated lower bound. |

## Exact definition and easy regimes

Section 2 defines a simplification as a subsequence of the input vertices, beginning at `p1` and ending at `pn`, with error at most a supplied `epsilon > 0`. The paper's `OPT_H` uses the directed Hausdorff distance from the input polyline `P` to the simplification `Q` (Section 2). The undirected version is treated separately in Section 4.1.

The easy results that rule out careless Track A claims are explicit:

- Section 1 gives Imai–Iri's valid-link graph and a shortest-path solution in `O(n^2)` time with the cited implementations.
- Theorem 7 gives an `O(n^4)` algorithm for the reverse directed Hausdorff problem, from `Q` to `P`.
- Theorem 10 gives an `O(k n^5)` dynamic program and `O(k n^2)` space for optimal Fréchet simplification.
- Theorems 1–3 give explicit bad examples for Douglas–Peucker/Imai–Iri, but those examples expose their short optimal simplifications directly; they are counterexamples to heuristics, not hard search distributions.

The native hard results are Theorem 4 (undirected Hausdorff, via Hamiltonian Cycle in segment-intersection graphs) and Theorem 6 (directed Hausdorff from `P` to `Q`, via Covering Points by Lines). Both are worst-case reductions.

## STEP 0 certificate question

**What produces the certificate, and what does it cost?**

1. **The proposed noisy-subdivision plant.** Sample a short polyline `Q`, retain its vertices in `P`, and insert intermediate vertices within `epsilon` of its links. The generator knows a feasible `Q`. A construction-aware extractor scans the input once for the planted link changes, so its cost is `Theta(n)` geometric comparisons. The supposed compact route also has to locate those same changes and costs `Theta(n)` comparisons. At the largest size compatible with G9(c), this is at most about **300 operations versus about 300 operations**. There is no compression gap. If the bends are made visibly marked or periodic, both routes drop to `Theta(k)`; if they are hidden well enough to defeat the scan, the generator no longer has a paper-backed compact route for the solver. Moreover, this plant does not certify that `Q` is minimum.

2. **Theorem 1's three-region construction.** The proof itself gives `Q = <p1, p_i, pn>` for **any even `i`**. A construction-aware algorithm selects `p2` (or another even vertex) using **three index selections and no search**. The compact route is the same **three selections**. Concatenating `g` copies changes both costs to `Theta(g)` and makes the answer longer; it does not open a mechanical-versus-compact gap.

3. **Theorem 4's reduction.** The certificate is a Hamiltonian cycle of the source segment-intersection graph, carried to a `3n+1`-vertex simplification by Lemma 5. Producing it mechanically requires solving Hamiltonian Cycle in the source instance. Inverse-planting a cycle establishes G but the paper contains no result that planted segment-intersection instances are hard. It therefore cannot support Track A. No polynomial reference algorithm is supplied for Track B.

4. **Theorem 6's reduction.** The certificate is a minimum line cover of the source point set, carried through the geometric scaffolding. Generating merely a known cover does not certify its minimum size. Generating a specially separated or visibly grouped minimum cover makes the construction-aware extraction and the compact route the same grouping scan, `Theta(n)` versus `Theta(n)`. The paper supplies no hard planted distribution.

5. **Theorem 10's Fréchet dynamic program.** On an arbitrary instance its advertised mechanical cost is `O(k n^5)`, which could create a Track B gap. But arbitrary instances do not meet G: the generator would obtain its answer by running that dynamic program. On the proposed planted-subdivision distribution, the planted links are recovered by the same `Theta(n)` construction scan used by the compact route (or by the `O(n^2)` Imai–Iri link graph when local links are used). The relevant strongest method is the construction-aware scan, not the much slower general DP, so the two Track B costs remain comparable.

## Why no module was built

A module based on noisy intermediate vertices would honestly be a benchmark of detecting the generator's bend markers. Making the markers apparent gives a successful linear/greedy attack; making them periodic gives a constant-size formula; and removing them leaves no compact route licensed by the paper. Escalating only the number of intermediate vertices makes both certificate extraction and the intended route longer, contrary to the fixed-answer/under-300-operation requirement.

The alternative is to implement either NP-hardness reduction and plant a source witness. That would yield valid native geometry and an exactly checkable decision witness, but it would still lack the required evidence that the *generated distribution* resists the domain-standard source-problem algorithm. Worst-case NP-hardness in Theorems 4 and 6 is not that evidence.

Accordingly, the prior triage hypothesis—"plant simplified polyline, add noisy intermediate vertices within epsilon"—is rejected specifically at H. It is not rejected at the witness rule, and the polynomial Fréchet algorithm is not by itself the reason: the decisive fact is that the strongest construction-aware route and the alleged compact route have the same cost on that distribution.

