# Affine Rank-Cut generator for arXiv 1305.2743

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph |
| certificate form | polynomial |
| intuition | invariant: short adjacent-label XORs span a parity kernel |
| domain essentiality | native |
| reduction | none |

**Release status:** G1–G9(c) pass, and the bare oracle loop is hardened at
`easy` after 0/3 solutions across two vendors. The structural-hint diagnostic
scored 1/3. The placebo arm is still unscored because all four retry records
returned HTTP 403, `Key limit exceeded (total limit)`. This missing diagnostic
does not change a gate, but `hinted - placebo` cannot yet be estimated.

## Problem and construction

The source is Guillemot and Marx, [*A faster FPT algorithm for Bipartite
Contraction*](https://arxiv.org/abs/1305.2743). Section 3 defines **Rank-Cut**:
given a graph, terminal sets `X,Y`, an edge set `M`, and `k`, find an `(X,Y)`
edge cut whose graphic rank after contracting `M` is at most `k`. This family
uses the native special case `M = empty`. Vertices additionally carry distinct
labels in `F_2^d`; the requested witness is an affine polynomial `P(x)=c·x+b`.
Its induced edge set contains exactly the edges whose endpoint values differ.

Verification evaluates `P` exactly, computes graphic rank with union-find,
deletes the induced cut, and checks terminal separation by BFS. It accepts any
valid affine polynomial and never reads `inst["answer"]`.

Generation is inverse. It samples a balanced, nonsparse `P` first, draws
labels from its two fibres, builds a regular connected circulant on each side,
and joins the sides by a matching of `k` edges. That matching is the planted
cut and has rank `k`. Removing an internal matching before inserting the cross
matching keeps every vertex at the same degree. Cross endpoints are resampled
until every cross-label XOR has Hamming weight at least three, so the planted
short-XOR kernel invariant holds for every generated seed, not merely with high
probability.

## Why Track B

Step 0 rules out Track A. Theorems 11 and 12 give Rank-Cut randomized
`2^{O(k^2)} n m` and deterministic `2^{O(k^2)} n^{O(1)}` algorithms; Theorem 1
transfers the result to Bipartite Contraction. Lemma 7 identifies the easy
constrained regime: weighted separation is solved in `O(k(n+m))` using at most
`k` Ford–Fulkerson rounds. Small fixed `k` and explicitly supplied constrained
partitions are therefore not claimed hard.

On this generated distribution, the honest reference algorithm is even
simpler: unit-capacity Ford–Fulkerson recovers the sparse terminal cut, then
exact Gaussian elimination over `F_2` fits its affine separator. Its complexity
is `O(k(n+m)+n d^2)`. At the shipping preset it solved 8/8 instances with a
median **20,661 counted bit operations** and **0.001526 s**. This successful
algorithm is reported under `reference_algorithm`, not among failing attacks.

The compact route inspects adjacent-label XORs of Hamming weight one or two.
Weight-one XORs anchor zero coefficients and weight-two XORs equate
coefficients; exactly one equality component remains unanchored. At shipping
size this route succeeds in **204** counted packed exact operations. The Track B
claim is only that this structural compression is short enough to execute in
context while the mechanical route is not a plausible by-hand calculation.

## Worked demo (`seed=0`)

The following is the complete rendered demo:

```text
Rank-Cut with an affine certificate

The undirected simple graph below has vertices 0 through 23.
Each vertex v has a displayed 7-bit label x(v).  In every displayed label,
the LEFTMOST bit is x_0, followed by x_1, ..., with x_6 rightmost.

An affine polynomial over F_2 is
  P(x) = c_0*x_0 XOR c_1*x_1 XOR ... XOR c_6*x_6 XOR b,
where every c_i and b is 0 or 1.  It defines the edge set
  C(P) = {uv in E : P(x(u)) != P(x(v))}.

For an edge set C, its graphic rank r(C) is the number of edges in a spanning
forest of the graph whose edge set is C (isolated vertices are irrelevant).
Equivalently, r(C) is summed as |V(K)|-1 over the nontrivial connected
components K of C.  An (X,Y)-cut is an edge set whose deletion leaves no path
from any vertex of X to any vertex of Y.

Find an affine polynomial P such that:
  1. P is oriented with P(x(22))=0 and P(x(18))=1;
  2. C(P) is an (X,Y)-cut; and
  3. r(C(P)) <= k=2.

Here X=[22] and Y=[18]; M is empty, so M-rank is ordinary rank.
The order of edges is irrelevant, there are no loops, and vertex numbering is
0-based.

Vertex labels (vertex: bits x_0...x_6):
  0: 0101000
  1: 1101101
  2: 1100101
  3: 0110100
  4: 1110110
  5: 1010010
  6: 1111001
  7: 1100111
  8: 1001101
  9: 0001110
  10: 0000100
  11: 0101111
  12: 1110001
  13: 0001000
  14: 1110100
  15: 1101001
  16: 0000001
  17: 0111111
  18: 0101101
  19: 0010110
  20: 0100001
  21: 0000000
  22: 0001100
  23: 1001100

Edges (u-v):
  4-15 2-14 0-1 10-23 13-15 1-15 1-4 5-6 10-17 4-16 19-23 8-22
  6-10 1-13 3-4 7-11 16-20 8-12 9-14 0-7 14-18 12-20 3-16 3-15
  10-18 7-8 0-11 2-9 14-21 5-12 8-11 11-22 0-13 5-20 9-19 2-17
  7-13 9-21 20-22 6-19 17-23 3-5 16-23 6-21 19-21 17-18 2-18 12-22

Give your final answer inside <answer></answer> tags as exactly 7 coefficient
bits c_0...c_6, then a vertical bar, then the constant bit b.
Example for a 5-variable instance: <answer>01011|1</answer>
Whitespace inside the tags is allowed. Output nothing else inside the tags.
```

The answer is `<answer>1011011|1</answer>`, stored as
`[1,0,1,1,0,1,1,1]`. `verify` returns `(True, "ok")`; changing the final entry
to `2` returns `(False, "coefficient outside GF(2)")`. The demo has 64 oriented
affine candidates, one valid answer, and a 55-operation compact route, so it is
genuinely hand-scale.

## Difficulty presets

| preset | n | label bits | k | degree | edges | answer atoms | compact ops | status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| demo | 24 | 7 | 2 | 4 | 48 | 8 | 55 | hand example |
| easy | 60 | 24 | 4 | 6 | 180 | 25 | 204 | selected shipping preset; hardened 0/3 |
| medium | 64 | 24 | 4 | 8 | 256 | 25 | 280 | fixed-length denser haystack |
| hard | 68 | 24 | 4 | 8 | 272 | 25 | 296 | fixed-length larger haystack |

`escalate()` continues increasing `n` with the 25-atom answer fixed, then
returns `"cap_bound"` when the next compact route would exceed 300 operations.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 preset-seed plants verify; 12/12 JSON round trips |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | fenced prose round-trip succeeds; garbage returns `None` |
| G4 | pass | 0/200,000 structured guesses; space `2^23 = 8,388,608` |
| G5 | pass | shipping 0/200,000 valid samples; demo exact count 1; reference 21,595 ops and 0.000438 s on the measured seed |
| G6 | pass | five attacks × 8 seeds, 0 successes; reference and compact routes each 8/8 |
| G7 | pass | `n` 60→120 and edges 180→360 with answer length fixed |
| G8 | pass | 80/80 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | gated caps pass: 51 chars, 13 estimated tokens, 25 atoms, 204 operations; bare 0/3, hinted 1/3, placebo unscored |

The five failing attacks are equal-degree outlier selection, eight-restart
coordinate descent, 256 uniform structured restarts, a one-shot in-context
ansatz using the two terminal labels' XOR, and an affine ansatz search of
Hamming weight at most two. The terminal-XOR attack is the specifically
no-tool fourth attack required on Track B. The current five-attack panel is
gated on the eight fresh seeds recorded above.

## Oracle loop and G9 arms

| arm | preset | model | seed | scored | reason |
|---|---|---|---:|---|---|
| bare | easy | GPT-5.6 Terra | 65407061 | yes | wrong polynomial: cut rank 5 > 4 |
| bare | easy | Gemini 3.8 Flash | 1056758131 | yes | reasoning reply ended without a tagged answer |
| bare | easy | GPT-5.6 Terra | 1899700837 | yes | wrong polynomial: cut rank 5 > 4 |
| hinted | easy | Gemini 3.8 Flash | 1749792176 | yes | solved and verified |
| hinted | easy | GPT-5.6 Terra | 87745989 | yes | wrong terminal orientation |
| hinted | easy | Gemini 3.8 Flash | 816702407 | yes | empty length-limited reply |
| placebo | easy | GPT-5.6 Terra | 742816540 | no | HTTP 403 key total limit |
| placebo | easy | GPT-5.6 Terra | 789025574 | no | HTTP 403 key total limit |
| placebo | easy | GPT-5.6 Terra | 923195157 | no | HTTP 403 key total limit |
| placebo | easy | GPT-5.6 Terra | 829570176 | no | HTTP 403 key total limit |

| G9 arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | hardened at the shipping preset |
| hinted | 1 / 3 | `too_easy` diagnostic: naming the invariant helped one oracle |
| placebo | 0 / 0 | not estimable |

`hinted - placebo` is undefined, not zero. The hinted success is consistent
with the intended difficulty being discovery of the invariant, but without a
scored placebo arm it cannot yet be separated from generic prompt leakage.

## Use

The module is standard-library-only:

```python
import gen_1305_2743 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["easy"])
statement = g.render(inst)
text = "<answer>" + g._answer_text(inst["answer"]) + "</answer>"
candidate = g.parse_answer(text)
assert g.verify(inst, candidate) == (True, "ok")
```

The bare run is complete. After supplying an OpenRouter key with available
quota, rerun only the placebo G9 mode in a fresh scratch directory as specified
by the task. From the repository root, examples may be emitted with:

```bash
bash scripts/emit.sh 1305.2743 20
```

## Caveats

- G4 samples uniformly from affine polynomials already satisfying the terminal
  orientation. It measures that declared prior only; it does not contradict the
  guaranteed kernel recovery or rule out a better nonuniform attack.
- The affine `F_2` labels and polynomial witness language are this benchmark's
  restriction of the paper's native Rank-Cut object. They are not a construction
  claimed by the paper, although verification still performs the paper's exact
  cut and graphic-rank test rather than replacing it with a surrogate.
- This is Track B because a fast reference algorithm succeeds by construction.
  The paper's FPT theorems are not evidence that this planted distribution is
  Track-A hard, and no such claim is made.
- No SAT/SMT encoding, optimized max-flow package, or full implementation of the
  paper's important-separator algorithm was tested. The inexpensive exact
  Ford–Fulkerson/elimination route is already the relevant successful baseline.
- `canonical_key` uses terminal-rooted colour refinement followed by affine
  normalization. Generated instances individualized in every audit, but the
  fallback for a hand-edited instance with unresolved twins is weaker than full
  graph isomorphism.
- The current two-vendor bare run is complete and the hinted arm has three scored
  attempts, but the placebo arm has only four HTTP-error records. Until that arm
  is rerun, the observed hinted success cannot be attributed specifically to the
  structural information rather than to generic prompt perturbation.
