# Rejected: arXiv 2007.05020

Paper: Alexander A. Ponomarenko and Dmitry V. Sirotkin,
[*Dota Underlords game is NP-complete*](https://arxiv.org/abs/2007.05020),
arXiv:2007.05020v1.

## Decision

No family is shipped. A native **Track B** family was implemented and passed
the local generation, exact-verification, guessing, attack, scaling, and
canonical-key checks, but the unmodified four-vendor hardening loop returned
`too_easy`: at least one oracle produced a valid team at every rung through all
three permitted escalations. The final valid witness was returned by Grok 4.6
at `n=420`, `degree=10`.

This is terminal under Step 4. I did not enlarge or retune the family after the
verdict, and I did not run the G9 hint arms. The draft generator and the
harness-owned bare transcript remain only as reproducible rejection evidence;
there is intentionally no shipping `selftest_report.json`, release `README.md`,
or G9 transcript.

## What the full paper defines

The full nine-page paper and its LaTeX source were read, not only the abstract.

- Section 3.1 chooses at most `m` heroes with binary variables `x_i`. Without
  alliances the objective is the sum of nonnegative hero powers, and the paper
  explicitly says this case is solved by taking the largest powers.
- Section 3.2 and system (2) add alliances. Hero `i` has base power `s_i` and
  receives bonus `e_ijk` when it is chosen and at least `k` chosen heroes belong
  to alliance `j`. Thus a concrete team is a finite witness whose exact power
  can be recomputed from the instance.
- Section 4.1, Theorem 1 restricts to equal hero powers and equal two-hero
  alliance bonuses activated only when both members are present. In that
  regime the power of a fixed-size team is an affine function of its induced
  edge count, so fixed-cardinality densest subgraph reduces to Underlords.
- Section 4.2, Theorem 2 checks a team in `O(ntq)` operations. Section 4.3,
  Theorem 3 concludes worst-case NP-completeness of the decision problem.
- Section 4.4, Theorems 4--6 give a polynomial reduction from bounded-alliance
  Underlords instances to maximum edge-weighted clique. Section 5 solves the
  real game data with the integer-programming model.

Theorem 3 is a worst-case result. It does not establish hardness for an
answer-first planted distribution, and it does not license treating a large
candidate space as distributional evidence.

## The Step-0 certificate question

> What algorithm produces the certificate, and what does it cost?

For the paper's real-data instance, Section 5 uses integer programming. For the
attempted scalable family, the certificate was deliberately produced by a
public translated exponent-coset decoder: subtract a public center in
`GF(p)`, then enumerate two named exponent classes by repeated multiplication
by `g^7`. It costs `O(n)` exact modular arithmetic, at most 205 counted
operations over the eight shipping attack seeds, and about 43 microseconds on
this machine. That makes Track A false, so the implementation declared Track B
and reported this successful algorithm separately.

The suggested prior-triage construction—put one high-scoring feasible team
among random low-scoring alternatives—would be weaker. Unless plants and
decoys have the same observable distribution, base power, degree, alliance
frequency, or local motif statistics expose the plant directly. Worst-case
NP-completeness does not rescue that planted distribution.

## Family tested

The draft uses the paper's native size-two-alliance case directly. There are
`n=p-1` heroes, every hero has base power 1, and every unordered pair is a
two-hero alliance except for a displayed sparse conflict pair. Each active
alliance contributes bonus 1 to each member. Therefore a team of size `k` has
power

```text
k + 2 * (number of nonconflict pairs inside the team),
```

and reaches the maximum `k^2` exactly when its labels form an independent set
of size `k` in the conflict graph. The strict threshold is `k^2-1`.

Generation is inverse. It first chooses a translation and two of seven
multiplicative cosets in `GF(p)^*`; their union, of size `2n/7`, is the known
team. It then constructs a simple regular conflict graph with no edge inside
that team. All public vertices have the same degree, cross-degrees are
balanced, the remaining degree sequence is randomized by degree-preserving
switches, and edge order is shuffled. `verify` ignores both `inst["answer"]`
and the public algebraic tag: it checks labels, size, distinctness, conflicts,
and recomputes the integer Underlords power.

This is native coverage rather than a graph surrogate replacing the paper's
objects: the heroes and two-hero alliances are exactly the restricted objects
of Theorem 1. The sparse conflict list is only the exact complement notation
for the otherwise dense alliance list.

## Local measurements before hardening

These measurements establish G and V and probe obvious leaks; they do not
override the failed oracle gate.

| Check | Result |
|---|---:|
| Planted witness | 12/12 verified across four presets and three seeds |
| Corruptions | 5/5 rejected with five distinct reasons |
| Parser round trip | Passed with prose and a Markdown-fenced tagged answer |
| Structure-aware random guesses | 0 / 200,000 exact-size distinct-label subsets |
| Shipping candidate space (`n=336`, `k=96`) | `96311736322029095114747004404323468923061679537192618656702132467015466679659585368600` |
| Strongest failing baseline | 256/256 randomized greedy restarts exhausted in 4.46 s |
| Local-motif outlier | 0 / 8 |
| Deterministic residual-degree greedy | 0 / 8 |
| Randomized greedy, 256 restarts | 0 / 8 |
| Smallest-eigenvector spectral heuristic | 0 / 8 |
| Obvious by-hand label ansatzes | 0 / 8 |
| Public coset decoder | 8 / 8, as expected for Track B; at most 205 operations |
| Size doubling | `n=672` built and the plant verified |
| Canonical-key invariance | 60/60 relabelling/reordering checks |
| Carried witnesses under relabelling | 60/60 verified |
| Unrelated keys | 20/20 distinct |
| Named-hard answer size | 385 characters, 97 estimated tokens, 96 elements |
| Named-hard intended route | 202 exact modular operations for the measured seed |

The `0/200000` density is empirical under a uniform prior over all exact-size
subsets. It does not estimate a solver using the public finite-field tag and is
not a proof of hardness.

## Decisive STEP 4 result

The bare run used harness master seed `5645777893022580107`, the prescribed
four-vendor pool, and reasoning effort `medium`. Exact seeds, replies, parsing,
verification reasons, timings, and provider statuses are preserved in
`llm_loop_transcript.jsonl` and `.meta.json`.

| Round | Preset / parameters | Oracle outcomes |
|---:|---|---|
| 0 | easy: `n=112`, `degree=8` | Claude failed with an empty length-limited response; Gemini solved; Terra solved |
| 1 | medium: `n=196`, `degree=10` | Gemini solved; Claude failed with an empty length-limited response; Grok solved |
| 2 | hard: `n=336`, `degree=10` | Claude solved; Gemini returned the wrong count; Grok solved |
| 3 | escalated: `n=420`, `degree=10` | Claude failed with an empty length-limited response; Gemini returned a conflicting team; Grok solved |

The script-owned verdict is:

```json
{
  "verdict": "too_easy",
  "escalations_used": 3,
  "reason": "the oracle pool solved every level through 3 escalations"
}
```

The final Grok answer parsed and verified with reason `ok`; it was not a parser
artifact. Because the bare prerequisite failed, running hinted and placebo G9
arms could not make the family admissible.

## Why another paper-native variant does not repair H

| Candidate family | Why it is not shipped |
|---|---|
| Equal powers with a planted dense team | G and V are easy, but Theorem 3 is only worst-case; the paper gives no hard planted distribution. Degree, spectral, clique, and construction-specific attacks must be justified independently. |
| Random low-scoring decoys around a high-scoring team | The planted/decoy distributions differ by construction, inviting the outlier and greedy attacks that G6 is designed to catch. |
| No alliances | Section 3.1 solves it by sorting hero powers. |
| Bounded alliances reduced to maximum edge-weighted clique | Theorems 4--6 provide a representation, not an answer-first hard distribution; applying a clique/ILP solver to a sampled instance learns the certificate by solving it. |
| The fixed real-game data from Section 5 | It is one finite instance already solved in the paper, not an unlimited diverse family. |
| A harder tagged Track B encoding | The tested public invariant was already executed successfully at every allowed rung. Hiding or enlarging it after observing the pool would violate the terminal hardening rule. |

Thus the paper provides an exactly checkable NP witness and a worst-case
hardness theorem, but the tested inverse-generated distribution is empirically
too easy, while the suggested alternative has an even clearer planting leak.
No honest Track A or surviving Track B generator is shipped.
