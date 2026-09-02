# Supported weakly-stable matching witness generator

This module turns the set-gadget construction in [*Ex-post Stability under Two-Sided Matching: Complexity and Characterization*](https://arxiv.org/abs/2411.14821) into an inverse generator. The solver receives a complete two-sided matching market with dichotomous preferences, represented compactly by its regular 3-set kernel and exact formulas for the random matching. It must return `n` gadget indices. Those triples must partition all `3n` elements; the checker expands that selector into a full deterministic matching and recomputes bijectivity, positive support, and every possible weak blocking pair. All arithmetic is integral except the displayed random-matching probabilities, whose row/column identities follow directly from the fixed formulas.

## Why this is hard—and what is easy

Section 2 gives the exact notions of weak stability and ex-post stability. Theorem 3.2 proves NP-completeness for complete dichotomous preferences, and Theorem 3.3 (the theorem immediately after it) proves that finding even one weakly stable matching consistent with a random matching's support is NP-complete. Its fixed-edge proof extracts exactly the selector returned here. The paper reduces from Exact Cover by 3-Sets with three occurrences per element; this generator uses six exchangeable partition layers for better crowding and adjusts the same bistochastic weights from thirds to sixths. The extraction and stability arguments are unchanged.

The avoided easy cases matter. Proposition 2.1 gives a linear-time test and polynomial decomposition when both sides are strict. Section 4.2 supplies an integer program—not a polynomial-time algorithm—for weak ex-post stability. Theorems 4.2 and 4.3 make robust ex-post stability and ex-post *strong* stability polynomial-time. This module asks for ordinary weak stability with ties, and `n` grows.

## Worked small instance

This is `render(make_instance(n=8, degree=6, seed=0))` in full:

```text
SUPPORTED WEAKLY-STABLE MATCHING — COMPACT SELECTOR WITNESS

There are 24 ground elements, numbered 0 through 23,
and 48 set gadgets, numbered 0 through 47.  Each set
gadget contains exactly three distinct ground elements; every ground element
occurs in exactly 6 gadgets.  The gadget data are:

  0: 3 12 23
  1: 1 4 12
  2: 1 16 22
  3: 9 17 20
  4: 3 10 22
  5: 4 8 23
  6: 0 4 19
  7: 6 10 21
  8: 20 21 22
  9: 0 16 19
  10: 1 5 19
  11: 1 11 13
  12: 2 6 18
  13: 4 16 18
  14: 5 12 16
  15: 7 10 17
  16: 3 11 13
  17: 9 13 17
  18: 4 7 13
  19: 0 5 19
  20: 2 21 23
  21: 8 12 18
  22: 0 15 19
  23: 3 15 16
  24: 2 11 20
  25: 0 14 17
  26: 3 9 14
  27: 6 7 18
  28: 14 15 21
  29: 1 2 22
  30: 7 8 18
  31: 9 18 23
  32: 11 14 23
  33: 6 11 20
  34: 5 9 20
  35: 1 12 13
  36: 6 7 11
  37: 3 5 19
  38: 2 8 15
  39: 7 10 21
  40: 8 13 23
  41: 0 14 22
  42: 10 21 22
  43: 10 15 17
  44: 5 9 17
  45: 6 12 14
  46: 8 15 16
  47: 2 4 20

This is a compact presentation of the following two-sided matching instance.
For each gadget j and port l in {0,1,2}, with T[j,l] the l-th displayed
element, there are agents c(j,l), d(j,l) and items x(j,l), y(j,l).  There is an
item a(e) and collector agent z(e) for every ground element e, plus agents s1,
s2 and items o1,o2.  Port arithmetic is modulo 3.

The positive entries of the supplied random matching p are exactly these
supported pairs (unlisted pairs have probability zero):

  p(c(j,l),a(T[j,l])) = 1/6
  p(c(j,l),x(j,l))    = 1/6
  p(c(j,l),y(j,l))    = 4/6
  p(d(j,l),x(j,l))    = 4/6
  p(d(j,l),y(j,l))    = 2/6
  p(z(e),x(j,l))      = 1/144  for every e,j,l
  p(s1,o1) = p(s2,o2) = 1.

These entries are nonnegative and every row and column sums to 1.  Preferences
and priorities are complete and dichotomous: every brace below is one tied top
tier, all unlisted partners form one tied bottom tier, and top is strictly
preferred to bottom.

  c(j,l) top: {a(T[j,l]), y(j,l), x(j,l-1)}
  s1 top: {o2} together with every y(j,l)
  d(j,l), z(e), and s2: indifferent among all items
  a(e) top: every c(j,l) whose T[j,l]=e
  x(j,l) top: {c(j,l), c(j,l+1)}
  y(j,l) top: {d(j,l), s1}
  o1 and o2: indifferent among all agents.

A deterministic matching is supported when every one of its pairs has positive
probability above.  It is weakly stable when there is no unmatched agent-item
pair for which BOTH sides strictly prefer each other to their assigned partners.

Your witness is the compact selector for a supported weakly stable matching.
Select exactly 8 distinct gadget indices whose triples cover every ground
element exactly once.  The checker expands them canonically: selected c ports
take their a-items; unselected c ports take their same-port x-items; every d
takes its y-item; z(e) takes the selected port's remaining x-item containing e;
and s1-o1, s2-o2 are paired.  The checker then recomputes bijectivity, support,
and weak stability.  Order of the 8 output indices does not matter; indices
are 0-based and repeats are forbidden.

Give your final answer inside <answer></answer> tags, as exactly 8
comma-separated base-10 gadget indices with no brackets.
Example (format only): <answer>0, 1, 2, 3, 4, 5, 6, 7</answer>
Output nothing else inside the tags.
```

One valid answer is `<answer>25, 31, 35, 36, 37, 42, 46, 47</answer>`, and `verify(inst, answer)` returns `(True, "ok")`. Dropping the last index returns `(False, "expected exactly 8 gadget indices")`.

## Difficulty presets

| preset | `n` | element count | gadget count | candidate subsets | status |
|---|---:|---:|---:|---:|---|
| small | 8 | 24 | 48 | 377,348,994 | rejected by all three oracles (solved) |
| **medium** | **32** | **96** | **192** | **2,861,517,736,436,550,142,707,282,052,072,092,546** | **ships; held** |
| hard | 64 | 192 | 384 | about 7.52e73 | local gates pass; oracle not needed |

## Gate results at the shipping setting

| gate | measurement | result |
|---|---|---|
| G1 | 15/15 plants verified across every preset | pass |
| G2 | 5/5 corruptions rejected with 5 distinct reasons | pass |
| G3 | 32 indices recovered from fenced prose; garbage returned `None` | pass |
| G4 | 0/200,000 uniform structure-aware guesses | pass |
| G5 | small seeds had 20, 10, and 9 answers out of 377,348,994 | pass |
| G6 | outlier, greedy, and 64-restart attacks each solved 0/8 | pass |
| G7 | doubled `n=64` built and verified; candidate space increased | pass |
| G8 | 60/60 composed relabellings invariant and real; 20/20 unrelated keys distinct | pass |

## Multi-vendor oracle loop

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| small | Gemini 3.1 Pro Preview | 2103046374 | solved | witness verified |
| small | Grok 4.6 | 1588838676 | solved | witness verified |
| small | GPT-5.6 Terra | 852471256 | solved | witness verified |
| medium | Gemini 3.1 Pro Preview | 1855555541 | failed | parsed selector overlapped at element 3 |
| medium | GPT-5.6 Terra | 1951514195 | failed | parsed selector overlapped at element 5 |
| medium | Claude Sonnet 5 | 1348953233 | failed | empty length-limited response after 32,000 completion tokens |

## Use

```python
import random
import gen_2411_14821 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=2026, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>0, 1, 2</answer>")
ok, reason = g.verify(inst, candidate)
random_guess = g.random_candidate(inst, random.Random(7))
```

From this directory, emit 20 verified records with:

```bash
bash ../../scripts/emit.sh 2411.14821 20 medium
```

## Caveats

The NP-completeness theorem is worst-case evidence for the ambient complete-dichotomous family; it is not an average-case proof for these planted instances. Each generated hypergraph is promised to be a union of six hidden exact covers. No polynomial-time recovery algorithm for that promise is known here, but an undiscovered spectral or factorization method could exploit it. The 0/200,000 figure measures only a uniform choice of 32 distinct in-range gadget indices; it does not bound informed search. The attacks do not include an industrial SAT/ILP/exact-cover solver, spectral recovery, local search with millions of restarts, or custom training on this generator. One of the three decisive medium oracle failures was an empty response caused by the fixed 32k token budget, so only two returned explicit wrong witnesses. Finally, `canonical_key` is a strong cheap invariant based on rooted closed-walk and distance histograms, not a complete hypergraph-isomorphism canonical form; rare non-isomorphic collisions are possible.
