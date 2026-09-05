# Perfect-matching packings for arXiv:2001.03506

> **Status:** the generator and every local gate pass, but the required Step 4
> oracle claim is incomplete. In the fresh bare run, the oracle pool solved easy
> 3/3 and medium 1/3; OpenRouter then rejected every hard-preset call before
> inference with HTTP 403 `Key limit exceeded (total limit)`. The structural-hint
> and placebo runs likewise reached no model. Service errors are preserved in the
> harness-owned transcripts and are not counted as model failures.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | combinatorics / finite discrete |
| Computational core | permutation (bipartite edge factorization) |
| Certificate | matrix certificate: one permutation row per guest |
| Native objects | regular bipartite host, perfect-matching guests, packing maps |
| Intended intuition | change of variables: reciprocal coordinates reveal translation factors |
| Domain essentiality | native; no reduction |

## Problem and trust model

Ehard and Joos's [*A short proof of the blow-up lemma for approximate
decompositions*](https://arxiv.org/abs/2001.03506) defines a packing in Section
1.1 as injective guest-vertex maps whose guest edges map injectively into one
host. This module uses that definition directly in its two-cluster special case.
Every guest is a spanning perfect matching. Its left side is normalized to the
equally labelled host vertices, so a witness is a matrix of right-side image
permutations. `verify` checks the row shapes, permutations, host-edge membership,
and global edge-disjointness exactly; it never reads `inst["answer"]`.

Generation is inverse. The module samples `host_degree` nonzero translations in
the field of `n` elements, designates `guests` of them before building the host,
and conjugates every translation by the reciprocal involution. The chosen and
unused factors are positions in the same uniformly shuffled sample. Their union
is the host, and the designated factors are the certificate. No matching or
packing algorithm runs during generation.

## Why this is Track B

The paper supplies an existence proof, not a distributional hardness result.
Theorem 1.2 is the bounded-degree multipartite packing theorem. The proof sketch
in Section 2 and the proof itself obtain a witness using random refinements, the
pseudorandom hypergraph-matching theorem (Theorem 3.6), repeated Approximate
Packing Lemma applications in Section 4, and an ordinary blow-up-lemma completion
(Theorem 3.5). Declaring Track A from those results would be unjustified.

This perfect-matching subclass has an efficient algorithm: repeatedly find a
perfect matching by augmenting paths and delete it. The implementation is
`O(kVE)` and solved 8/8 shipping instances, averaging **10,290 edge probes and
0.00123 seconds**. That number is the Track B baseline, not a failed attack.

The compact route uses `c(0)=0` and `c(x)=x^-1 mod n`. A hidden factor has
`p_s(x)=c(c(x)+s)`. The neighbors of left vertex 0 identify the available `s`
values after the coordinate change. At shipping size, one reciprocal table and
ten factor rows require at most **252 exact modular operations**, versus about
10,300 graph-search probes. The distinction is practical and no-tool only: this
family is extremely easy for a machine with a matching routine.

## Worked demo

`make_instance(n=5, host_degree=3, guests=2, seed=7)` renders the complete
hand-scale problem below. A person can solve it by listing the six perfect
matchings of the small host and choosing two disjoint ones.

```text
Find an edge-disjoint packing of perfect matchings into a bipartite host graph.

Definitions and instance.
The size parameter is n=5.
The host has a left cluster L and a right cluster R, each labelled by the integers 0 through 4.
An undirected host edge is written (x,y), with x the label in L and y the label in R.
The host is 3-regular. Its complete adjacency list is below; row order and neighbour order carry no meaning.
There are 2 labelled guest graphs, numbered 0 through 1.
Guest h has left vertices a(h,x), right vertices b(h,x), and exactly the 5 edges a(h,x)--b(h,x) for x=0,...,4.

A normalized packing fixes every a(h,x) to host vertex L_x. For every guest h you must give a permutation p_h of 0,...,n-1; b(h,x) is mapped to R_{p_h[x]}.
The packing is valid exactly when every (x,p_h[x]) is a listed host edge and no host edge is used by two guests.
Unused host edges are allowed. Guest order and all matrix positions are significant; repetitions inside a row are forbidden.

Host adjacency (inclusive 0-based labels):
  L_1: 2 3 0
  L_2: 4 0 3
  L_0: 3 1 4
  L_4: 1 2 0
  L_3: 2 1 4

Output a JSON matrix with exactly 2 rows and exactly 5 integers per row.
Row h is [p_h[0],p_h[1],...,p_h[n-1]]. Every entry must be an integer in the inclusive range shown above.
For syntax only, a two-guest instance with n=3 could use <answer>[[0,1,2],[1,2,0]]</answer>.

Give your final answer inside <answer></answer> tags, as the JSON matrix just specified.
Output nothing else inside the tags.
```

One answer is `<answer>[[3,2,0,4,1],[4,0,3,1,2]]</answer>`:

```python
verify(inst, [[3, 2, 0, 4, 1], [4, 0, 3, 1, 2]])
# (True, "ok")

bad = [[5, 2, 0, 4, 1], [4, 0, 3, 1, 2]]
verify(inst, bad)
# (False, "entry (0,0) is outside 0..4")
```

## Presets and gates

| Preset | `n` | Host degree | Guests | Answer elements | Status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 3 | 2 | 10 | hand-solvable illustration |
| easy | 13 | 9 | 6 | 78 | first oracle rung |
| medium | 17 | 12 | 8 | 136 | second oracle rung |
| hard | 23 | 16 | 10 | 230 | configured shipping preset; oracle untested |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses verified and JSON-round-tripped |
| G2 | 6/6 corruptions rejected with six distinct reasons |
| G3 | fenced, tagged JSON with surrounding prose round-tripped |
| G4 | 0/200,000 row-permutation guesses; Bregman upper bound `2.29e-33` |
| G5 | shipping density 0/200,000; demo has exactly 36/14,400 valid matrices; reference algorithm 8/8 at 10,273 probes and 0.00122s average |
| G6 | degree outlier, no-augmentation greedy, 256 randomized greedies, and raw constant-difference ansatz each 0/8; reference matching 8/8 separately |
| G7 | `n=47` instance built and verified; answer stayed near-fixed at 235 elements |
| G8 | 40/40 composed relabellings invariant, 40/40 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 611 characters, 481 conservative lexical tokens, 230 elements, 252 intended operations |

## Oracle loop and G9 diagnostics

The fresh bare harness completed easy and medium. Easy was decisively solved;
medium was also defeated because one verified answer is enough to defeat a rung,
although the other two attempts failed. The account reached its total limit at
the start of hard, so hard has no usable attempt and the run produced no hardness
verdict.

| Arm / model | Preset | Seed(s) | Usable solved/attempts | Service errors |
|---|---|---|---:|---:|
| bare / Gemini 3.8 Flash, GPT-5.6 Terra | easy | 1545365927, 2060264316, 801177941 | 3/3 | 0 |
| bare / GPT-5.6 Terra, Gemini 3.8 Flash | medium | 1787426962, 213003454, 1429672907 | 1/3 | 0 |
| bare / current two-vendor pool | hard | 536899025, 2010642497, 1432913593, 72564790 | 0/0 | 4 |
| structural / Grok 4.6, GPT-5.6 Terra | hard | 773595900, 898358256, 117542959, 1554814009 | 0/0 | 4 |
| placebo / Grok 4.6, Claude Sonnet 5 | hard | 447322641, 1463473715, 1415868160, 952657943 | 0/0 | 4 |

`hinted - placebo` is undefined because neither arm reached a model. The
structural hint names only the reciprocal-coordinate invariant. No conclusion
about whether that insight helps an oracle is warranted from the current data.

## Use

The module is standard-library-only; `gvlib` is unnecessary for this finite
permutation certificate.

```python
import gen_2001_03506 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
question = gen.render(inst)
candidate = gen.parse_answer("work... <answer>[[0]]</answer>")
ok, reason = gen.verify(inst, candidate)
```

After a funded OpenRouter run returns `verdict: hardened`, emit from the repository
root with:

```bash
bash scripts/emit.sh 2001.03506 20 hard
```

## Caveats

- The finite presets use the paper's native packing definition, but the paper's
  asymptotic constants are nonquantitative. These small reciprocal-Cayley hosts
  are not claimed to satisfy Theorem 1.2's unspecified super-regularity threshold.
- Track B makes no computational-hardness claim. The disclosed reference solver
  finishes in about a millisecond; difficulty exists only under the evaluated
  model's no-tool constraint.
- G4 samples uniformly from matrices whose rows are already permutations. Its
  zero-hit rate and permanent bound do not describe graph-aware guessing, matching,
  or a solver that recognizes the reciprocal coordinates.
- Optimized edge-colouring, SAT/ILP encodings, spectral recovery, and broader
  library-of-transforms attacks were not tested. The domain-standard augmenting-
  path algorithm was tested and, as Track B requires, succeeds.
- `canonical_key` uses row/column pair-and-triple intersection profiles. It is
  invariant under the tested vertex, side, guest, and input-order relabellings,
  but it is not a complete bipartite graph-isomorphism canonical form and may
  collide on adversarial nonisomorphic inputs.
- The answer is close to both the 256-element and approximate 500-token caps.
  The 481-token figure conservatively counts every numeral and JSON punctuation
  mark as a separate lexical token; failures may still include transcription.
- Most importantly, Step 4 and the three-arm behavioral diagnostic remain
  externally blocked by the exhausted OpenRouter key. Re-fund or replace that key
  and rerun all three harness invocations before treating this family as shippable.
