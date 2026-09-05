# Visiting All Sites with Your Dog — verified rotation family

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | geometry |
| Object regime | continuous analytic, represented exactly over Q |
| Computational core | linear algebra |
| Certificate | 2×2 rational matrix certificate |
| Intended intuition | invariant: vector sums transform under the same rotation as every point |
| Domain essentiality | native; no reduction |

## What the problem is and why it is trustworthy

[Maheshwari, Sack, and Shahbaz, *Visiting All Sites with Your Dog*](https://arxiv.org/abs/1211.4559) asks for a polygonal curve `Q` through every supplied site whose continuous Fréchet distance from a supplied curve `P` is at most `epsilon`. This generator samples an orientation-preserving rational rotation `R` first, samples rational points on one circle, and makes the unordered site set `S = R(P)`. The solver returns `R`; the checker reconstructs `Q = R(P)`, checks exact set equality, and checks all squared endpoint distances with `Fraction` arithmetic. Matching equal parameters on corresponding segments then gives a continuous leash certificate, and the segment certificates concatenate by Section 2.1, Observations 1 and 2. Generation never solves its output.

This is deliberately Track B. A generic exact algorithm maps one anchor of `P` to each possible site and tests the resulting rotation, taking `O(n²)` rational operations in the worst case. At the shipping preset it solved 8/8 instances, averaging 1,551 exact point transforms (maximum 2,356) and 0.151 seconds. The compact route instead uses the displayed sums `u=sum(P)` and `v=sum(S)`: for `R=[[c,-s],[s,c]]`,

```text
c = (u·v)/(u·u),        s = (u_x v_y - u_y v_x)/(u·u).
```

That is 12 exact arithmetic operations if the invariant is noticed. The measured reference work corresponds to 12,223 counted rational multiply/add/divide operations on average (maximum 19,656), including candidate construction. Section 2’s NP-completeness theorem is not misused as an average-case claim. Section 3, Theorem 3 makes convex-polygon input easy in `O(nk²)` (and optimization `O(nk² log(nk))`), so this generator shuffles its curve vertices into a nonconvex traversal; the generated distribution remains polynomially solvable for the disclosed congruence reason.

## Worked demo (`seed=0`)

The complete mathematical data from the demo rendering are:

```text
P has five ordered vertices; S is unordered. All coordinates are exact.
Allowed rotations are R(a,b), 1 <= a <= 7, -7 <= b <= 7,
gcd(a,|b|)=1, with
  c=(a²-b²)/(a²+b²), s=2ab/(a²+b²), R=[[c,-s],[s,c]].
epsilon² = 121680/17
sum(P) = (80/1, 27/1)
sum(S) = (3308/85, -6369/85)

P, in order:
p_0 = (39/1, -52/1)
p_1 = (-63/1, 16/1)
p_2 = (-16/1, 63/1)
p_3 = (60/1, -25/1)
p_4 = (60/1, 25/1)

S, unordered:
2168312 = (105/17, 1100/17)
7340145 = (576/17, -943/17)
2172272 = (-264/17, -1073/17)
3364227 = (5084/85, 2163/85)
5233620 = (-3861/85, -3952/85)

Required output:
<answer>[[c,-s],[s,c]]</answer>, with every entry written num/den.
```

The answer is `<answer>[[13/85,84/85],[-84/85,13/85]]</answer>`. Internally it is JSON-native as `[[[13,85],[84,85]],[[-84,85],[13,85]]]`. `verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the second row returns `(False, "rotation must be a 2 by 2 matrix")`. A person can solve this demo on paper from the two vector sums and a 2×2 rotation identity, although the fraction arithmetic is intentionally nontrivial.

## Difficulty and gates

| preset | sites `n` | circle factors | rotation height | ships? |
|---|---:|---:|---:|---|
| demo | 5 | 2 | 7 | no; hand example |
| easy | 96 | 4 | 4,095 | no |
| medium | 256 | 5 | 16,383 | no |
| hard | 768 | 5 | 65,535 | **yes** |

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verified; all answers JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | model-style and JSON-native round trips both passed |
| G4 | 0/200,000 legal random rotations; bounded language size 5,221,928,631 |
| G5 | demo has exactly 1 valid bounded rotation; shipping reference cost above |
| G6 | height outlier, nearest-anchor greedy, 16 random anchors, axis ansatz, and bounding-box ansatz: each 0/8; reference 8/8 |
| G7 | doubled 1,536-site instance built and verified |
| G8 | 40/40 isometry/relabel invariance and 40/40 carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | 111 JSON characters in a 10,000-seed worst-case sweep, about 28 tokens, 8 atomic integers; intended route 12 operations |

## Oracle loop and G9 diagnostics

The required harness was invoked, but the configured OpenRouter key had exhausted its total limit. The harness correctly counted no API error as a model failure and stopped without a hardness verdict. These are infrastructure failures, not evidence that the family is hardened.

| preset | seed | model | scored? | reason |
|---|---:|---|---|---|
| easy | 1,340,409,609 | OpenAI GPT-5.6 Terra | no | HTTP 403 key limit exceeded |
| easy | 786,192,611 | OpenAI GPT-5.6 Terra | no | HTTP 403 key limit exceeded |
| easy | 1,940,174,770 | Anthropic Claude Sonnet 5 | no | HTTP 403 key limit exceeded |
| easy | 1,627,826,155 | OpenAI GPT-5.6 Terra | no | HTTP 403 key limit exceeded |

| G9 arm | solved / scored attempts | status | conclusion |
|---|---:|---|---|
| bare | 0 / 0 | blocked by four HTTP 403 errors | no diagnostic conclusion |
| structural hint | 0 / 0 | blocked by four HTTP 403 errors | hinted verdict unrun |
| placebo hint | 0 / 0 | blocked by four HTTP 403 errors | no comparison possible |

Thus `hinted − placebo` is not estimated; the `0.0` placeholder in the report means “no scored samples,” not “no hint effect.” Restore OpenRouter quota and rerun all three isolated arms before submission.

## Use

```python
from gen_1211_4559 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
statement = render(inst)
candidate = parse_answer("<answer>[[3/5,-4/5],[4/5,3/5]]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1211.4559
```

## Caveats

This benchmark asks for a rotation-coupled visiting curve, a certified native subfamily of the paper’s problem. The checker accepts every bounded rational rotation certificate satisfying that specification, but it does not accept an unrelated feasible `Q` that lacks the synchronous rotation form. The family becomes easy immediately in a sandbox: vector sums solve it in linear input-reading time, and this is why it is Track B rather than Track A. G4 samples uniformly from primitive bounded rational rotations; it measures blind guessing in that declared language, not a solver prior conditioned on the displayed checksums. The adversary panel does not test cyclic angular-gap matching, Fourier descriptors, or a general continuous-Fréchet implementation. The canonical key uses the exact multiset of pairwise distances, which is invariant under all tested relabellings and plane isometries but can theoretically collide on noncongruent homometric point sets. Finally, no oracle-hardness claim is made until the quota-blocked script-owned runs are successfully repeated.
