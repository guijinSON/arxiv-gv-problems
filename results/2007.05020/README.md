# Dota Underlords pair-alliance team search

| profile field | value |
|---|---|
| track | **A — structural hardness** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | graph |
| certificate | integer tuple (a team of hero IDs) |
| intended intuition | constraint propagation through cross-pool compatibility intersections |
| domain essentiality | licensed reduction |
| reduction | paper-licensed: Section 4.1, Theorem 1 |

This generator turns Ponomarenko and Sirotkin's [*Dota Underlords game is
NP-complete*](https://arxiv.org/abs/2007.05020) into an exact witness problem.
The solver receives equal-power heroes and the paper's native size-two
alliances, then returns a team whose total power meets the displayed threshold.
The checker performs exact integer range checks and alliance lookups and accepts
any qualifying team, not only the planted one.

This is representational rather than fully domain-essential coverage: the
statement and checker retain heroes, alliances, and team power, but Theorem 1
licenses the alliance-graph view that carries the search. The graph surrogate is
central to the paper's proof, not a convenience reduction added by the generator.

## Why this is the hard version

Section 3.2 defines hero powers, thresholded alliances, and the team-size
constraint. Theorem 1 in Section 4.1 proves hardness already in the exact regime
used here: equal hero powers; size-two alliances; activation only when both
members are selected; equal bonuses paid only to alliance members. In that
regime, active alliances are graph edges and maximizing team power is fixed-size
densest subgraph. Theorems 2 and 3 give the polynomial witness check and
NP-completeness. Section 4.4 reduces bounded-alliance Underlords instances to
maximum edge-weighted clique and points to exact branch-and-bound/quadratic
methods, but does not give a polynomial solver.

The easy regime had to be avoided. Section 3.1 says that without alliances the
answer is obtained merely by sorting hero powers. Here all powers are identical
and every hero has exactly 29 alliances into each other pool. The generator
samples one hero per pool first. For every pool pair it independently constructs
a 29-regular bipartite graph, selects an ordinary edge uniformly, and relabels
that edge onto the planted endpoints. Plants and decoys therefore have the same
per-pool degree; the generator never runs a solver.

The shipping distribution is `n=24` pools, `Q=40` heroes per pool, degree 29.
Theorem 1 is a worst-case theorem, not an average-case theorem for this planted
regular distribution. The Track A claim is consequently narrower: no efficient
exact recovery method is known for this distribution, and the measured panel
misses it. Exact MRV/forward-checking backtracking exhausts 300,001 nodes in
1.419 seconds on the baseline seed and fails on all eight panel seeds. An earlier
`n=20,Q=24,d=17` regime was solved on 8/8 seeds, and `n=22,Q=28,d=20` was solved
on 1/8 at 300,000 nodes; both were discarded before defining the final ladder.

## Worked demo

The `demo` preset at seed 0 renders as follows.

```text
DOTA UNDERLORDS PAIR-ALLIANCE TEAM

There are N*Q distinct heroes, displayed in N pools only to make
their IDs and alliance data readable. Pool c contains local heroes
x=0,...,Q-1; that hero's global ID is c*Q+x. IDs and pools are
0-indexed. Every hero has base power 1.

Every listed compatibility is a size-two alliance. If both heroes
of such an alliance are selected, each of them receives bonus power
1, so that active alliance contributes 2 total. No unlisted pair is
an alliance, and there are no alliances within a pool.

N = 4
Q = 4
Each pool pair is D-regular with D = 2
Team size limit = 4
Required total power = at least 16

For a team with r heroes and a active listed alliances, total power
is r+2a. Since r<=N, reaching N^2 is possible exactly when r=N and
all N choose 2 hero pairs are alliances. Such a team necessarily has
one hero from every pool. You may therefore return that canonical
one-per-pool representation directly.

PAIR DATA: for each 0<=i<j<N, ROWS has Q hexadecimal integers.
The x-th integer is a Q-bit mask: bit y (least-significant bit y=0)
is 1 exactly when local hero x in pool i has a size-two alliance
with local hero y in pool j. Leading zeroes do not change a mask.

PAIR_DATA_BEGIN
PAIR 0 1 ROWS a,5,5,a
PAIR 0 2 ROWS 3,c,a,5
PAIR 0 3 ROWS 9,6,a,5
PAIR 1 2 ROWS c,6,3,9
PAIR 1 3 ROWS 3,c,a,5
PAIR 2 3 ROWS c,5,a,3
PAIR_DATA_END

Return an ordered JSON array of exactly N distinct global hero IDs.
Position c must contain the chosen hero from pool c, hence it must lie
in the inclusive range c*Q through (c+1)*Q-1. Repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON
array of integer global hero IDs in pool order.
Example syntax (not a solution): <answer>[2, 27, 51]</answer>
Output nothing else inside the tags.
```

The planted answer is `[3, 7, 8, 14]`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; dropping its last
ID returns `(False, "wrong team length: expected 4, got 3")`. The demo is
genuinely hand-solvable: it has only `4^4=256` structured candidates and six
valid teams, and bitmask intersections cut that down quickly.

## Difficulty presets

| preset | pools `n` | heroes/pool `Q` | regular degree | answer IDs | rendered chars (seed 0) | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 4 | 4 | 2 | 4 | 1,793 | illustration; skipped by hardening |
| easy | 24 | 40 | 29 | 24 | 127,292 | **ships; all gates and all oracle arms held** |
| medium | 24 | 48 | 35 | 24 | 178,076 | available |
| hard | 24 | 56 | 40 | 24 | 237,692 | available |

After `hard`, `escalate()` keeps the 24-ID answer fixed and adds eight decoys
per pool. The two smaller development regimes described above were rejected by
G6's exact attack, not by the oracle.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted teams verified (four presets × four seeds); answers JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 realistic tagged/fenced replies round-tripped; garbage rejected |
| G4 | 0/200,000 structure-aware guesses; language size `40^24 = 281474976710656000000000000000000000000` |
| G5 | shipping density estimate 0/200,000; demo exact count 6/256; exact baseline 300,001 nodes, 1.419 s, unsolved |
| G6 | triangle outlier 0/8; greedy 0/8; 256-restart MRV 0/8; centered spectral 0/8; exact CSP/DPLL 0/8 |
| G7 | doubled `n=48` instance built and its 48-ID certificate verified; fixed-length escalation also verified |
| G8 | key invariant 40/40; carried witnesses 40/40; unrelated keys distinct 20/20 |
| G9 | hinted pool still hardened; 94 chars, 50 conservative tokens, 24 atoms, 276 pair checks |

Exact figures, including attack operation counts, are in
[`selftest_report.json`](selftest_report.json).

## Bare oracle loop

All calls used reasoning effort `medium`. Every returned team parsed correctly;
each failed an exact alliance check. No escalation was used.

| preset | model | seed | solved | verification result |
|---|---|---:|---:|---|
| easy | Gemini 3.1 Pro Preview | 1678884603 | no | missing alliance, pools 0–4 |
| easy | GPT-5.6 Terra | 2103448846 | no | missing alliance, pools 0–14 |
| easy | Grok 4.6 | 260602873 | no | missing alliance, pools 0–15 |

The script-owned evidence is [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl)
and [`.meta.json`](.meta.json).

## G9 arms

| arm | solved / attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. The hint therefore bought no observed solve-rate
improvement: this is evidence that merely naming compatibility intersections
does not expose the answer, but it does not establish that the benchmark cleanly
isolates the declared constraint-propagation intuition. The serialized shipping
answer is 94 characters, 50 conservatively estimated tokens, and 24 atomic
elements. Once a propagation branch has fixed one candidate per pool, checking
the complete route takes one exact lookup for each of the 276 pool pairs.

## Use

```python
from gen_2007_05020 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 deterministic shipping instances with:

```bash
bash scripts/emit.sh 2007.05020 20 easy
```

Run local gates from this directory with `python3 gen_2007_05020.py`. The oracle
files were produced only by `python3 ../../scripts/harden.py gen_2007_05020.py`;
the hint arms were run in separate scratch directories as required.

## Caveats

- Theorem 1 proves worst-case NP-hardness, not average-case hardness of these
  conditioned regular matrices. A larger exact-search budget or a stronger
  maximum-clique/CP-SAT implementation may solve the distribution.
- The shipping rendering is large: 127,292 characters, and the placebo Claude
  call reported 105,153 prompt tokens. Some oracle failure may measure navigation
  through dense exact input as well as mathematical search. The 276-operation
  figure begins after propagation has fixed a candidate per pool and excludes
  the potentially exponential work needed to find that branch.
- `0/200,000` is an observed rate, not proof that the true probability is zero.
  The prior is already structure-aware—it samples exactly one hero uniformly
  from every pool in required order—but it is not a learned solver prior.
- The panel did not run a commercial ILP/CP-SAT solver, an unbounded modern
  maximum-clique implementation, an SDP/nuclear-norm relaxation, or a learned
  recovery attack. It did run the required centered spectral probe and bounded
  exact CSP search.
- The 2-switch construction is regular and label-exchangeable but is not claimed
  to sample uniformly from all regular bipartite graphs.
- `canonical_key` is invariant under tested pool permutations, independent hero
  relabelings, pair-order reversal, and compositions, but it is a strong cheap
  invariant rather than a complete multipartite graph-isomorphism canonizer;
  rare collisions are possible.
