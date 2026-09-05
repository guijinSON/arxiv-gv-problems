# arXiv 1505.04778 — exact balanced k-means SDP certificates

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | optimization |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate | integer-tuple set partition, which compactly encodes the primal matrix and determines the dual matrix |
| Intuition | symmetry: three congruent residual clouds are translates, with a quarter-turn relation between the global mean and translation direction |
| Domain essentiality | native |
| Reduction | none |

## What the family is and whether to trust it

The source is Iguchi, Mixon, Peterson, and Villar, [*On the tightness of an SDP relaxation of k-means*](https://arxiv.org/abs/1505.04778). A solver receives an exact four-dimensional Euclidean point cloud and must partition it into three equal clusters. The answer encodes the paper's normalized primal partition matrix. From any submitted partition—not from the planted answer—the checker constructs `M`, `z`, `u`, `B`, and the dual slack matrix `Q` using Section 3's formulas, checks dual nonnegativity and complementary slackness, and performs an exact rational LDL test of `Q >= 0`. Thus acceptance is an executable primal-dual optimality certificate, not comparison with hidden labels.

Generation is inverse and theorem-backed. The partition is sampled first; three translated copies of the same antipodal residual cloud are assembled around it, a dense rational direction is chosen, all denominators are cleared by a uniform scaling, and the points are permuted. Section 3, Theorem 6 supplies the certificate construction. The asymptotic stochastic-ball theorem in Section 4 is not claimed: its distribution is rotation invariant, whereas this finite exact construction is deterministic and rational.

## Why Track B

Track A would be false. Section 2 explicitly gives a semidefinite program and explains that tightness returns an optimal clustering with a convex-duality certificate. The implemented exact specialization first recovers the partition and then runs the paper's certificate check in `O(Nm + N log N + N^3)`. At shipping `N=24`, it solved 8/8 instances using a mean **23,208 counted exact operations**, **0.215 s mean**, and **0.254 s maximum**.

The compact route notices that the global mean is a fixed rational quarter-turn of the cluster-translation direction. Recovering that direction and sorting one exact projection costs 264 arithmetic operations. The benchmark asks whether that symmetry can be found and executed without an SDP/CAS; the large rational coefficient height makes the mechanical route unsuitable for hand execution. Section 2 is also the paper result that makes the family easy with tools, so it is disclosed rather than hidden.

## Worked demo (`seed=7`)

The complete point data in the demo are:

```text
N=6, k=3, n=2, points in Q^4, indexed from 0
0: [-7524, -3703,   7524,  7942]
1: [-7524,-10553,   7524,  7942]
2: [ -396,-18077,   -418, 15466]
3: [-14652,-3029,  15466,   418]
4: [-14652, 3821,  15466,   418]
5: [ -396,-11227,   -418, 15466]
```

The full rendered statement also defines the exact `M,z,u,B,Q` test. Its answer is:

```json
{"clusters":[[0,1],[2,5],[3,4]]}
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Removing index `1` returns `(False, "each cluster must contain exactly n point indices")`. A person can solve this smallest setting by pairing the visibly translated/antipodal points and can check the centroids on paper; the full dual matrix arithmetic is deliberately small only at this demo rung.

## Difficulty presets

| Preset | Points | Coordinate bits | Radius bits | Max coordinate digits (`seed=0`) | Candidate partitions | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 6 | 4 | 4 | 5 | 15 | hand example |
| easy | 24 | 10 | 10 | 11 | 1,577,585,295 | oracle run unavailable |
| medium | 24 | 20 | 20 | 21 | 1,577,585,295 | reserve |
| hard | 24 | 36 | 36 | 35 | 1,577,585,295 | **provisional shipping preset** |

The haystack grows primarily through exact coefficient height while the 24-index answer stays fixed. `escalate()` raises both independent height parameters. Doubling `n` to 16 per cluster also built and verified, expanding the balanced-partition space to 225,890,910,734,335,847,055.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset-seed planted certificates verified |
| G2 | pass | five corruptions rejected for five distinct reasons |
| G3 | pass | tagged JSON recovered from realistic prose; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware balanced guesses; 1,577,585,295 candidates |
| G5 | pass | shipping density 0/200,000; demo exact count 1/15; reference cost 23,208 operations |
| G6 | pass | five attacks each 0/8; reference algorithm 8/8 |
| G7 | pass | 48-point doubled instance built and verified |
| G8 | pass | 40/40 composed invariance checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 82 characters, 21 estimated tokens, 24 atoms, 264 intended operations |

## Oracle hardening loop

No oracle result is being claimed. The script-owned bare run made four redraws at `easy`; all returned OpenRouter HTTP 403 `Key limit exceeded`, so `harden.py` correctly stopped with “oracle pool is unreachable” and did not set a verdict.

| Arm | Valid solved / attempts | Script-owned calls | Outcome |
|---|---:|---:|---|
| bare | 0 / 0 | 4 errors | unavailable: OpenRouter 403 |
| structural hint | 0 / 0 | 4 errors | unavailable: OpenRouter 403 |
| placebo hint | 0 / 0 | 4 errors | unavailable: OpenRouter 403 |

`hinted - placebo` is undefined with zero valid attempts (stored as `0.0` only as a JSON placeholder), so nothing can be concluded about hint value. The error transcripts are preserved in the required filenames and must be replaced by successful script-owned runs before submission. This is an infrastructure block, not evidence of hardness and not a paper rejection.

## Use

```python
from gen_1505_04778 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

After a valid hardening run, emit from the repository root with:

```bash
bash scripts/emit.sh 1505.04778 20 hard
```

## Caveats

- This is intentionally Track B. A generic SDP solver, or the disclosed mean-projection specialization, makes the generated distribution easy with tools.
- The 0/200,000 density estimate is for uniformly random **balanced unlabeled** three-partitions, exactly the declared certificate language. It measures that prior, not resistance to an algebraic or geometric recovery algorithm.
- The attacks cover every single-coordinate tertile, squared-norm tertiles, coordinate-sum tertiles, nearest-seed greed, and 256 balanced restarts per seed. They do not cover numerical SDP packages, alternative spectral embeddings, multi-start Lloyd iterations, or every possible exact invariant; the reference algorithm is expected to succeed.
- The canonical key uses the normalized multiset of pairwise squared distances. It is invariant under point relabelling, Euclidean signed-coordinate isometries, translation, and uniform scale, but homometric non-isometric clouds could collide.
- The first listed point is forced to come from the middle translated copy so the deterministic nearest-seed probe cannot receive a lucky extreme-cloud seed. This does not reveal the rest of the partition, but it is a construction-specific ordering choice a downstream user should know.
- The local mathematical gates pass, but the mandatory multi-vendor oracle and G9 diagnostics remain unmeasured because the available OpenRouter key was exhausted.
