# Shortest dominating-set TAR reconfiguration generator

Status: the native generator and all local gates pass, but the mandatory multi-vendor oracle run is **infrastructure-blocked**. The bare loop proved that `easy` is too easy (two valid oracle solutions), then obtained one failed medium attempt before OpenRouter returned HTTP 403 `Key limit exceeded (total limit)` on every retry. `medium` is therefore only the provisional shipping preset; this directory has no script-owned hardened verdict and must not be submitted as hardened.

| Profile field | Value |
|---|---|
| Track | **B** — an efficient mechanical algorithm is disclosed below |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | exact symbolic word of `A<vertex>` / `R<vertex>` TAR moves |
| Intuition | constraint propagation through a uniquely peelable alternating incidence order |
| Domain essentiality | native; no reduction |

## Problem and trust model

This family uses the paper's native object: a finite graph, two dominating sets, a token limit, and the token-addition/removal (TAR) rule defined in Section 1 of Bousquet, Joffard, and Ouvrard, [*Linear transformations between dominating sets in the TAR-model*](https://arxiv.org/abs/2006.16726). The solver must give a shortest word of typed vertex moves (`A12` adds vertex 12; `R7` removes vertex 7). The verifier replays every move, checks membership, the size bound, exact closed-neighborhood domination after each removal, and the target endpoint. It accepts any valid sequence and never reads the planted answer.

Generation is inverse: a random total precedence order is sampled first, ordinary degree-two graph vertices encode pair and precedence constraints, the legal sequence is recorded, and only then are all graph vertices randomly relabelled. A private pair constraint forces each target addition to be followed by its matching source removal. Consecutive precedence constraints force one order; redundant forward constraints and identically shaped decoy pairs obscure it. Thus there is exactly one certificate in the declared `(n!)^2` endpoint-respecting language, known without solving the generated instance.

## Why Track B

The paper itself rules out an unqualified Track A story. Section 1 cites PSPACE-completeness for general TAR reachability but also linear-time algorithms on trees, interval graphs, and cographs, plus an FPT algorithm parameterized by `k` on fixed-`K_{d,d}`-free graphs. Section 3, Theorem 2 constructively gives a polynomial-time linear path at `k = Gamma(G) + alpha(G) - 1`; Section 4, Lemma 4 treats minor-sparse graphs, and Section 5, Theorem 6 treats bounded-treewidth graphs constructively at their stated high thresholds.

For this generated subclass, the disclosed reference algorithm scans missing target vertices and remaining source vertices until exact domination identifies the next legal pair. Its complexity is `O(n^3 (|V|+|E|))`; at provisional shipping `n=44`, the final local audit over eight seeds averaged **2.49 s, 3,728,299 exact membership tests, and 14,556 candidate pairs**, solving 8/8 as expected. The compact route recognizes that degree-two constraints between endpoint-difference vertices have a unique leaf-peeling order, then emits the corresponding add/remove pair. That route costs at most **197 link/move operations**. The benchmark tests noticing this compression, not computational intractability.

## Worked demo

The `demo` preset with seed 3 is hand-solvable. It renders:

```text
Find an exact shortest token-addition/removal reconfiguration between dominating sets.

The input is a finite simple undirected graph with vertices 1 through 19.
A set D of vertices is dominating when every graph vertex either belongs to D or
has a neighbor in D.  A legal TAR move adds one absent vertex or removes one
present vertex.  After every individual move, including removals, the current
set must be dominating and contain at most k=7 vertices.

Start at this dominating set (order is irrelevant, no repetitions):
  2 6 7 12 15 18

Finish at this dominating set (order is irrelevant, no repetitions):
  6 7 10 11 12 14

The graph has 26 edges, listed once each as two endpoints:
  8 13
  7 13
  7 8
  7 15
  2 5
  14 16
  7 18
  5 14
  6 19
  4 11
  16 18
  4 18
  2 7
  7 12
  7 11
  9 10
  6 7
  1 13
  7 17
  3 10
  2 3
  8 19
  1 12
  9 15
  7 10
  7 14

Give exactly 6 moves.  This is the symmetric-difference lower
bound, so it is a shortest sequence: every target-only vertex must be added once,
every source-only vertex must be removed once, and no other vertex may be moved.
Encode adding vertex v by the JSON string "Av" and removing it by "Rv", with the
decimal 1-based label substituted for v: for example, "A12" adds vertex 12 and
"R7" removes vertex 7.  The JSON list must alternate an addition and a removal,
beginning with an addition; the order of moves matters.

Give your final answer inside <answer></answer> tags, as one JSON list of operation strings.
Format-only example (deliberately too short to be legal): <answer>["A1","R2"]</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>["A10","R15","A14","R2","A11","R18"]</answer>`, and `verify` returns `(True, "ok")`. Swapping the first two moves gives `["R15","A10","A14","R2","A11","R18"]`, rejected as `(False, "step 1 does not dominate vertex 9")`. A person can solve this demo by tracing the three pair constraints; the larger presets preserve the idea while random labels, redundant constraints, and decoys make manual tracing costly.

## Difficulty presets

| Preset | Core swaps `n` | Decoy pairs | Extra precedence | Noise edges | Vertices | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 3 | 2 | 0 | 1 | 19 | 6 | hand example |
| easy | 32 | 48 | 16 | 36 | 289 | 64 | rejected by STEP 4: solved on 2/3 attempts |
| medium | 44 | 66 | 22 | 66 | 397 | 88 | provisional shipping; 0/1 before infrastructure failure |
| hard | 60 | 90 | 30 | 100 | 541 | 120 | not reached |

`escalate()` first grows decoy and redundant-constraint haystacks at fixed answer length. It returns `cap_bound` before either the 256-atom or 300-operation limit would be crossed.

## Local gate results

| Gate | Result |
|---|---|
| G1 | 12/12 planted paths verified; all answers JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged JSON round-trip passed; garbage returns `None` |
| G4 | 0/200,000 structure-aware guesses; declared space has 362 bits at provisional shipping |
| G5 | demo exact solution count 1; shipping sampled density 0/200,000; reference cost 3,728,299 membership tests |
| G6 | degree, smallest-label greedy, 256 restarts, and one-shot private-neighbor attacks: 0/8 successes each; reference and compact solvers: 8/8 |
| G7 | doubled `n=88` instance built and verified; candidate space grew from 362 to 893 bits |
| G8 | 140/140 relabelling/composition invariance checks and 140/140 carried witnesses passed; 20/20 unrelated keys distinct |
| G9(c) | 598 actual / 617 worst-case characters, 88 atoms, 197 intended operations: within every cap |

## Oracle loop and G9 arms

The bare script run produced four countable replies before the external budget failed. Easy is conclusively defeated because any one valid reply forces escalation; medium is undecided because one model failure is not the required three-model hold. HTTP errors are retained in the transcript and are not scored as model failures.

| Arm | Preset | Seeds | Result | Why |
|---|---|---|---|---|
| bare | easy | 1687558922 | failed 0/1 | exact replay lost domination at step 2 |
| bare | easy | 1452507051, 2026302898 | solved 2/2 | both replies replayed exactly to the target |
| bare | medium | 1793419269 | failed 0/1 | oracle incorrectly claimed no sequence exists |
| bare | medium | 352078763, 346203778, 500605287, 874502083 | 0 countable attempts | four HTTP 403 key-limit errors |
| structural | medium | 1809256448, 369867101, 1720637704, 1069072126 | 0 countable attempts | four HTTP 403 key-limit errors |
| placebo | medium | 421926928, 635885836, 2105217468, 981270657 | 0 countable attempts | four HTTP 403 key-limit errors |

`hinted - placebo` is undefined (stored numerically as 0.0 only because both denominators are zero). No conclusion about hint usefulness is justified. The structural hint names only the alternating-path invariant; it does not give the peeling procedure. The copied G9 transcripts were generated by `harden.py` in isolated directories at medium and faithfully record the infrastructure failure.

## Use

```python
import gen_2006_16726 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
prompt = g.render(inst)
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root, emission is `bash scripts/emit.sh 2006.16726 20`. Do not emit or submit yet: replenish the OpenRouter budget, rerun `python3 ../../scripts/harden.py gen_2006_16726.py`, let the script continue its ladder, then rerun both G9 copies at the actual held preset, update `G9_ORACLE_RESULTS`, and regenerate `selftest_report.json`.

## Caveats

The sampled `P(guess)` is for the deliberately strong prior that already knows the exact length, endpoint symmetric difference, alternation, and token-capacity pattern; it does not estimate arbitrary language-model behavior. The distribution is Track B and is easy for the disclosed polynomial legal-pair scan. Static attacks were tested, but no SAT/SMT encoding, bidirectional reconfiguration BFS, or learned graph heuristic was run; general BFS would also be a valid but much more expensive reference. The canonical key uses colored 1-dimensional Weisfeiler-Leman refinement, which passed all generated relabellings but is not a complete graph-isomorphism canonizer. Most importantly, the mandatory multi-vendor evidence is absent because of the external key limit, so local gates alone must not be read as a completed hardness claim.
