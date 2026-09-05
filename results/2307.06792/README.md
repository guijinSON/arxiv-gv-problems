# arXiv:2307.06792 — planar disjoint paths generator

> **Build status:** G1–G8 pass. The result is not yet shippable: OpenRouter hit its total key limit during the bare hardening run, so G9 and the required oracle evidence are incomplete. No API error is counted as a solver failure.

| Profile field | Value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple: two explicit vertex paths |
| Intuition | change of variables: expose binary-tree ancestry by undoing an affine relabelling |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Włodarczyk and Zehavi, [*Planar Disjoint Paths, Treewidth, and Kernels*](https://arxiv.org/abs/2307.06792). Section 1 defines the native problem: given an undirected planar graph and pairwise distinct terminal pairs \((s_i,t_i)\), find mutually vertex-disjoint \(s_i\)-to-\(t_i\) paths.

Here the graph is a complete binary tree plus pendant chains, represented exactly but succinctly. Heap position `x` receives public label `(A*x+B) mod P`. The two pairs lie in disjoint rooted subtrees. Their unique paths are sampled first as parent chains, then carried through the affine relabelling; generation never searches the emitted graph. Verification decodes labels, checks every parent/child or pendant edge, checks endpoints and simplicity, and checks global vertex-disjointness.

## Why Track B is honest

This is not a Track-A distributional-hardness claim. The paper gives a general \(2^{O(k^2)}n^{O(1)}\) algorithm in Theorem 1.5 and a polynomial kernel for parameter \(k+\mathsf{tw}\) in Theorem 1.4. These instances have treewidth one and are easier still: breadth-first search finds the unique routes in `O(k(V+E))` time.

At provisional shipping `medium`, the measured BFS reference succeeds 8/8 times, averaging **2,655,510 edge scans, 1,595,580 visited vertices, and 0.605 s**. The compact route computes one modular inverse, decodes four terminals, follows binary parents, and re-encodes the two paths in **271 exact operations**. The gap—not a claim that BFS is unknown—is the Track-B basis.

Section 5 proves the paper's WK[1]-hardness by a much larger Set Cover → non-crossing-flow → unit-demand subcubic-graph reduction. This module does not pretend to implement that reduction; its native tree distribution instead tests recognition and execution of the coordinate change.

## Worked demo

For `make_instance(n=4, route_depth=2, pairs=2, decoys=2, seed=0)`, the defining constants are `N=31, P=41, A=18, B=32`, the pendant chains are `21: 34 11` and `8: 29 6`, and the terminal pairs are `(22,40)` and `(17,35)`, each requiring three vertices. The complete answer is:

```text
<answer>[[22,27,40],[17,4,35]]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the middle `27` by `22` returns `(False, "path 0 repeats a vertex")`. A person can solve this demo on paper by inverting `18*x+32 (mod 41)` and using the two heap parents.

## Presets

| Preset | Tree depth | Route depth | Pairs | Decoys | Base vertices | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 4 | 2 | 2 | 2 | 31 | 6 | hand example |
| easy | 21 | 16 | 2 | 12 | 4,194,303 | 62 | one oracle solved; not shipping |
| medium | 22 | 16 | 2 | 16 | 8,388,607 | 62 | provisional shipping; oracle run incomplete |
| hard | 23 | 16 | 2 | 20 | 16,777,215 | 62 | available escalation |

## Gate measurements

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verify; all answers JSON-round-trip |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; candidate language is 1,334 bits |
| G5 | pass | sampled shipping density 0; exactly one tree linkage by construction; demo brute force counts 1 |
| G6 | pass | degree, numeric-greedy, 256-restart, and raw-label-heap attacks all 0/8; BFS 8/8 as expected |
| G7 | pass | doubling the graph from 8,388,638 to 16,777,250 vertices preserves a 62-atom verified answer |
| G8 | pass | 80/80 invariance checks, 20/20 carried witnesses, and 20/20 unrelated keys distinct |
| G9 | **incomplete** | 495 chars, 124 estimated tokens, 62 atoms, 271 operations are within caps; hinted oracle gate not run |

## Oracle loop

The transcript was written only by `scripts/harden.py`. The run stopped on the external key limit and therefore has no verdict.

| Preset | Model | Seed | Result | Reason |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 104316250 | failed | parsed path; non-edge at path 0 step 19 |
| easy | Grok 4.6 | 1095815076 | failed | parsed path; non-edge at path 1 step 0 |
| easy | Gemini 3.1 Pro | 880983925 | solved | verified |
| medium | GPT-5.6 Terra | 2029757823 | failed | parsed path; label outside vertex set |
| medium | remaining scheduled calls | — | API error | OpenRouter total key limit exceeded; not attempts |

## G9 arms

| Arm | Solved / attempts | Status |
|---|---:|---|
| bare | — | incomplete after quota error |
| structural hint | — | not run |
| placebo hint | — | not run |

The hinted-minus-placebo statistic is therefore unavailable. The structural hint names only the affine-coordinate invariant and does not give the inversion procedure. Once quota is restored, rerun bare at `medium`, then run structural and placebo copies in separate scratch directories as required.

## Use

```python
from gen_2307_06792 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
assert parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>") == inst["answer"]
```

After the oracle evidence is complete, emit from the repository root with:

```bash
bash scripts/emit.sh 2307.06792 20 medium
```

## Caveats

The family is easy with software and intentionally so: BFS is the disclosed reference algorithm, and anyone who recognizes the affine heap coordinates has the compact route. Its formula-defined graph is a succinct encoding rather than the conventional explicit adjacency-list encoding assumed by graph-algorithm running times; the benchmark's difficulty is therefore no-tool decompression, not a new consequence of the paper's hardness theorem. The 0/200,000 guess rate samples fixed-length, endpoint-correct, globally distinct vertex sequences; it says nothing about informed graph algorithms. The canonical key is a strong metric invariant of terminals and pendant attachment bases, not a complete tree-isomorphism canonizer. The attack panel does not include SAT/ILP encodings or a language model with arithmetic tools. Most importantly, the one successful bare `easy` attempt shows that this rung is not hard enough across vendors; `medium` must not ship until the interrupted bare pool and both G9 arms finish.
