# Affine packing of tree factors — arXiv:1304.2429

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate form | polynomial |
| Intended intuition | invariant: take a finite-field first difference of neighbor sums |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

[Bal, Frieze, Krivelevich, and Loh, *Packing tree factors in random and pseudo-random graphs*](https://arxiv.org/abs/1304.2429) defines an (H)-factor as vertex-disjoint copies of (H) covering every vertex and notes in Section 1 that a (K_2)-factor is a perfect matching. The generated instance is a bipartite graph whose two sides are (mathbb F_p). A solver must give (k) degree-one polynomials (f_i(x)=a_i x+b_i) whose graphs are pairwise edge-disjoint perfect matchings in the displayed graph.

The answer is a symbolic packing, not a list of its (kp) edges. `verify` expands every polynomial over all (p) residues, checks every edge, proves that each right side is covered once, and checks edge-disjointness. It accepts every valid list of affine factors and never reads `inst["answer"]`.

## Why this is Track B

The paper proves existence rather than computational hardness. In its Section 3 proof of Theorem 1, one perfect matching is chosen on every super-edge and their union is a tree factor; Lemma 3.4 supplies large collections of edge-disjoint perfect matchings. The random-graph analogues are Theorems 2 and 3. None licenses a Track A distributional-hardness claim, and ordinary bipartite matching is polynomial-time.

This generator instead creates the graph as the union of (d) equally valid maps (x\mapsto ax+b), all with the same sampled nonzero slope and distinct sampled intercepts. Thus there is no distinguished planted layer. The exact reference algorithm pairs the (d) possible images of 0 with the (d) possible images of 1 and verifies the resulting affine maps on all of (mathbb F_p): (O(d^2p)), measured at a mean 256,030 exact operations and 0.0161 seconds at shipping. The compact route observes

\[
\sum N(x+1)-\sum N(x)=d a\pmod p,
\]

recovers (a) with one modular inverse, and takes any (k) intercepts from (N(0)). It is conservatively bounded at 186 exact operations. Theorem 1's regime (epsilon^6np^4\gg\log^3n), Theorem 2's (epsilon^4np\gg\log^2n), and Theorem 3's (p>C\log n/n) concern existence in random or pseudorandom host graphs; they are deliberately not cited as computational-hardness results.

## Worked demo

For `make_instance(n=7, layers=3, required=2, seed=0)`, the complete rendered data are:

```text
p=7, k=2
0: 6 0 3
6: 2 1 5
1: 5 1 4
5: 4 3 0
3: 1 0 4
4: 6 2 5
2: 3 2 6
```

The answer is `[[5,0],[5,3]]`. Calling `verify(inst, [[5,0],[5,3]])` returns `(True, "ok")`. Dropping one map returns `(False, "answer must contain exactly 2 affine maps")`. A person can solve this demo on paper: the neighbor-sum difference between rows 0 and 1 gives slope 5 modulo 7, and row 0 gives the intercepts.

## Difficulty presets

| Preset | (p) | layers (d) | requested (k) | edges | answer maps | Result |
|---|---:|---:|---:|---:|---:|---|
| demo | 7 | 3 | 2 | 21 | 2 | hand-solvable; skipped by hardener |
| easy | 127 | 20 | 4 | 2,540 | 4 | oracle solved 3/3 |
| medium | 251 | 45 | 5 | 11,295 | 5 | oracle solved 2/3 |
| **hard (ships)** | **509** | **80** | **6** | **40,720** | **6** | oracle solved 0/3 |

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 constructed certificates verified |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged, fenced JSON round-tripped |
| G4 | pass | 0/200,000 guesses; exact density (2.5226190\times10^{-8}) in a 11,912,230,852,393,872-element structure-aware space |
| G5 | pass | 300,500,200 exact shipping certificates; strongest failed attack took 0.1040 s and 325,760 edge-statistic updates over 8 seeds; reference mean 256,030 operations |
| G6 | pass | five attacks, each 0/8; reference and compact algorithms 8/8 as expected |
| G7 | pass | (p=1019), 81,520 edges, same six-map answer length |
| G8 | pass | 40 affine/side-swap invariance checks, 40 carried witnesses, 20/20 unrelated keys distinct |
| G9 | pass | 53 characters, 14 estimated tokens, 12 atoms, 186 intended operations |

## Oracle loop

| Preset | Seeds | Solved | Verification evidence |
|---|---|---:|---|
| easy | 345118000, 1028396542, 68614488 | 3/3 | all verified `ok` |
| medium | 1043438382, 1519169964, 715562395 | 2/3 | failed answer mixed slopes |
| hard | 196142485, 1741679652, 1152703830 | 0/3 | one length-limited empty reply; two answers mixed slopes |

The script-owned verdict is `hardened` at `hard` after two escalations. The empty hard reply is retained as such in the transcript; the other two independent hard failures contained parseable but invalid certificates.

## G9 diagnostic arms

| Arm | Solved/attempts | Interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 1/3 | one model used the named invariant successfully |
| placebo hint | 1/3 | one model also solved without structural information |

`hinted − placebo = 0`. With only three attempts per arm, the hint showed no net measured benefit; this does not falsify the invariant interpretation, but it is weak evidence for it. The answer and route remain well inside the gated caps: 53 serialized characters, 12 atomic coefficients, and 186 exact operations.

## Use

```python
from gen_1304_2429 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["hard"])
question = render(inst)
candidate = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, emit 20 shipping instances with:

```bash
scripts/emit.sh 1304.2429 20 hard
```

## Caveats

This is a deliberately structured subclass of the paper's packing problem, not a claim that random-graph tree-factor packing is computationally hard. A solver with code can recover all affine layers in milliseconds, and the neighbor-sum invariant is shorter still once noticed. The exact guess density applies to a prior that already enforces the freely deducible common-slope/distinct-intercept constraints; it does not model a language model's learned preference for affine patterns. The adversary panel tests degree/edge-difference outliers, sorted-row greed, 256 random restarts, ordinary rather than modular averaging, and a translation ansatz. It does not test SAT/ILP/SDP encodings or every higher-moment invariant; the disclosed affine enumerator is stronger and succeeds by design. The shipping rendering is large—about 157,658 characters, and one transcript tokenizer reported 156,835 prompt tokens—so locating the useful rows is part of the no-tool burden even though the post-insight arithmetic stays under the stated cap. Finally, one hard bare call exhausted its response-token budget, so the 0/3 hard result should be read together with the two parseable wrong answers, not as three identical reasoning failures.
