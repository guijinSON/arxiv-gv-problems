# Modular edge-colouring generator for arXiv:2507.04254

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate form | exact symbolic |
| Intended intuition | change of variables: neighbourhood-coordinate sums form a shifted quintic sequence |
| Domain essentiality | native |
| Reduction | none |

## What the family is

This implements a native problem from Berthe et al., [*On Modular Edge Colourings of Graphs*](https://arxiv.org/abs/2507.04254), arXiv:2507.04254v2.  The solver receives disjoint, coordinate-labelled regular bipartite graphs and must give a compact rule for a two-colouring of the edges.  In each colour class, every nonzero vertex degree must be (1\pmod 3), exactly the definition fixed in Section 1 of the paper.

For component (i), an answer pair `[a,b]` assigns an edge with endpoint coordinates (u,v\in F_p) the intercept (v-a(u-b)^5).  The eight resulting intercepts are sorted and bundled four at a time into two colours.  Verification expands this rule, counts every degree, and checks the congruences using integers only; it never reads the planted answer.  Generation goes in the other direction: it samples the permutation polynomial and eight offsets first, creates those eight perfect matchings, and retains the parameters as the certificate.  Because (gcd(5,p-1)=1), (u\mapsto(u-b)^5) permutes (F_p).

## Why Track B, not Track A

There is an efficient algorithm and the module says so.  Lemma 10 is the paper's Hall-type matching engine, while the proof of Lemma 9 explicitly constructs colourings by star packing and matching.  On this regular bipartite subfamily, repeated augmenting-path perfect matchings produce eight ordinary matching colours; bundling four matchings gives each modular colour degree (4\equiv1\pmod3).  The implemented reference algorithm is (O(b r^2p^2)), solves 8/8 shipping instances, inspects at most 54,433 edges in the measured panel (0.0115 s), and emits 2,144 edge labels.

That is the mechanical route.  The compact route observes that the sum of the eight right-neighbour coordinates at left coordinate (u) is a constant plus (8a(u-b)^5).  Six sums and their fourth and fifth finite differences recover (a,b).  Across four components this costs at most 260 exact field operations and emits eight residues.  The benchmark tests whether a no-tool solver finds and executes that compression; it makes no structural-hardness or NP-hardness claim.  The first affine version was discarded during hardening because a single first difference of neighbourhood sums exposed its slope; the quintic version explicitly includes that failed shortcut in its adversary panel.

## Worked demo (seed 0)

This is the complete `demo` rendering.  A person can solve it on paper by summing the neighbourhood coordinates for (u=0,1,\ldots,5), taking finite differences modulo 13, and recovering one pair.

```text
COMPRESSED MODULAR EDGE COLOURING

A graph is split into the disjoint bipartite components listed below.
In each component the left vertex IDs and right vertex IDs are both 0,...,12.  Each ID has a displayed coordinate in the prime field F_13; all arithmetic on coordinates is modulo 13.  IDs and coordinates are different: always use the coordinate tables.

A mod-3 edge-colouring is valid when, for each colour, every vertex incident with that colour has degree congruent to 1 modulo 3 inside that colour class.  Degree zero is allowed.

You must give one parameter pair [a_i,b_i] in F_p for each component i, with a_i nonzero.  It encodes the colouring as follows.  For an edge from left ID L to right ID R, look up coordinates u and v and compute the intercept
    d = v - a_i*(u-b_i)^5 (mod p).
A pair is admissible only when its component has exactly 8 distinct intercepts.  Sort those residues numerically as 0,...,p-1 and group consecutive blocks of 4; block number 0,...,1 is the edge colour.  Across components, equal block numbers are the same global colour.  The resulting colouring must use exactly 2 colours and satisfy the mod-3 degree condition above.

There are 1 components; every component is 8-regular.  Coordinate tables are JSON arrays indexed by vertex ID. Each adjacency row `Lx: ...` gives the right vertex IDs adjacent to left ID x; row order and neighbour order carry no meaning.

COMPONENT 1
left coordinates by ID: [11,4,10,6,0,1,12,2,8,3,9,5,7]
right coordinates by ID: [0,9,12,8,6,3,2,10,7,5,11,1,4]
adjacency:
L0: 2,0,5,12,4,7,3,10
L1: 11,2,7,3,0,9,6,4
L2: 6,0,8,4,10,9,12,7
L3: 11,12,3,8,2,7,6,5
L4: 9,12,3,5,0,6,1,10
L5: 10,6,1,12,11,4,3,7
L6: 12,8,1,2,4,6,3,0
L7: 9,10,2,6,5,1,7,8
L8: 8,1,3,5,11,0,7,9
L9: 8,10,2,5,3,4,9,11
L10: 9,12,7,2,11,1,5,4
L11: 2,8,11,12,0,10,9,1
L12: 11,6,10,4,5,8,1,0

Return exactly 1 pair in component order.  In each [a,b], a must be an integer from 1 through 12 and b an integer from 0 through 12.  Order matters; pairs may repeat.
Give your final answer inside <answer></answer> tags as a JSON list of pairs.
Example format: <answer>[[3,0],[7,9]]</answer>
The example only shows syntax; use the required number of pairs for this instance.
Output nothing else inside the tags.
```

The planted response is `<answer>[[9,12]]</answer>`.  `verify(inst, [[9,12]])` returns `(True, "ok")`; changing the shift gives `verify(inst, [[9,0]]) == (False, "component 1 induces more than 8 intercepts")`.

## Difficulty presets

| preset | requested n / actual p | components | edges | compact search space | status |
|---|---:|---:|---:|---:|---|
| demo | 13 / 13 | 1 | 104 | 156 | hand-scale illustration |
| easy | 37 / 37 | 4 | 1,184 | 3,147,870,802,176 | one oracle solved; rejected as shipping rung |
| medium | 67 / 67 | 4 | 2,144 | 382,362,201,079,056 | **ships; 0/3 oracle solves** |
| hard | 103 / 103 | 4 | 3,296 | 12,182,869,323,073,296 | reserve rung, not needed |

## Gate results

| gate | result at shipping preset |
|---|---|
| G1 planted verifies | 12/12 preset/seed cases; all answers JSON-native |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 round trip | fenced, prose-wrapped JSON recovered; garbage rejected |
| G4 guessing | 0/200,000; exact compact density (2.6153\times10^{-15}) |
| G5 density/cost | unique compact answer; demo count 1/156; 0/2,048 baseline restarts in 0.0141 s |
| G6 adversaries | five attacks each 0/8; matching reference 8/8, max 54,433 inspections |
| G7 scaling | doubled request builds at (p=137), 4,384 edges, same four-pair answer |
| G8 canonical key | 100/100 transformations invariant and verifying; 20/20 unrelated keys distinct |
| G9 caps | 33 chars, 8 atoms, about 9 tokens; intended route 260 operations |

## Oracle loop

The harness-owned pool available in this run contained two configured vendors, recorded in `.meta.json`; it was not the script's four-vendor default.  A rung is held only when all three scored calls fail.

| preset | seed | model | result | checker reason |
|---|---:|---|---|---|
| easy | 1700972720 | google/gemini-3.8-flash | solved | ok |
| easy | 1328594756 | openai/gpt-5.6-terra | failed | component 1 produced too many intercepts |
| easy | 671873961 | openai/gpt-5.6-terra | failed | component 2 produced too many intercepts |
| medium | 865753229 | google/gemini-3.8-flash | failed | no final answer |
| medium | 1465580988 | openai/gpt-5.6-terra | failed | no final answer |
| medium | 1099237472 | openai/gpt-5.6-terra | failed | component 2 produced too many intercepts |

## G9 diagnostic arms

| arm | solved / scored attempts | service errors | conclusion |
|---|---:|---:|---|
| bare | 0/3 | 0 | held at medium |
| structural hint | 0/3 | 0 | hint did not yield a verified answer |
| placebo hint | 1/2 | 4 | third slot unavailable after OpenRouter total-key-limit errors |

On the scored calls, hinted minus placebo is (0-1/2=-0.5).  The structural hint bought no observed improvement, but the samples use different seeds/models and the placebo arm is incomplete, so this is weak diagnostic evidence rather than a causal conclusion.  One hinted failure exhausted its 32k-token completion budget and returned an empty response; the transcript records that separately.  None of these diagnostics gates shipping under the current G9 contract.

## Use

```python
from gen_2507_04254 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit twenty shipping instances with:

```bash
bash scripts/emit.sh 2507.04254 20 medium
```

## Caveats

This is deliberately not a Track-A hardness claim: matching solves every generated graph quickly.  The benchmark also asks for a compact permutation-polynomial certificate rather than a 2,144-entry explicit colouring; `verify` nevertheless accepts a valid explicit edge-colouring under its alternate `{"edge_colors": [...]}` form.  The 0/200,000 guess result concerns uniform guesses from the declared `[a,b]` language, not arbitrary edge-colourings, and the exact density uses the fact that a proper subset of the prime cyclic group has no nonzero translation stabilizer.

The adversary panel tests degree constants, minimum-neighbour alignment, first-edge alignment, the first-moment affine attack that broke the initial generator, random restarts, and the matching reference.  It does not test SAT/SMT encodings, higher-moment symbolic fitting, or learned pattern recovery.  The canonical key is complete for vertex-ID reorderings, component reorderings, and the declared affine coordinate changes, but it is not a general bipartite graph-isomorphism algorithm.  Finally, the default four-vendor oracle claim could not be reproduced in this environment: `.meta.json` records a two-vendor override, and the OpenRouter total limit prevented the third placebo attempt.  Those are evidence limitations, not hidden successes.
