# Power domination on relabelled necklace graphs

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (a vertex set) |
| Intuition | decomposition into hidden `K4-e` diamonds |
| Domain essentiality | native |
| Reduction | none |

This generator is based on Benson et al., [*Note on Nordhaus-Gaddum problems for power domination*](https://arxiv.org/abs/1610.03115). It gives the solver a randomly relabelled cubic graph and asks for an exact-size power dominating set. Checking is cheap and exact: mark the closed neighborhood of the submitted set, repeatedly apply the paper's one-unmarked-neighbor forcing rule, and require every vertex to become marked.

The generator composes the paper's necklace graphs `N_r`. The paragraph before Theorem 2.17 defines a necklace from copies of `K4-e` joined through their degree-two vertices, Theorem 2.17 says they attain the cubic `n/4` bound, and Lemma 2.18 analyzes the same four-vertex blocks. Remark 2.16 gives the executable obstruction: the two non-connector vertices in each diamond are true twins, so a size-`r` power dominating set must meet all `r` diamonds. Conversely, any one vertex per diamond works. Generation samples those representatives first and only then relabels the graph; it never solves the generated instance. Theorem 3.13 explicitly handles disconnected cubic graphs componentwise, licensing the composition used here.

## Why Track B

This distribution is not claimed structurally hard. Sorting the four-element closed-neighborhood signatures finds every true-twin pair in `O((|V|+|E|) log Δ)` time. At the hard preset the implementation solves all 8/8 trials, averages **15,936 counted operations** and **0.000941 s**, and is therefore reported as the reference algorithm rather than as a failed attack. The compact route is to notice the diamond decomposition and make one choice per block, budgeted at **261 exact adjacency decisions**. Executing the mechanical signature pass over 996 shuffled rows is easy for code but not a plausible unaided in-context calculation.

The paper also identifies regimes that are too easy for the intended claim. Lemma 2.18 gives power domination number two for the complement of a necklace; Theorem 2.5 makes a complement two-dominated when the original diameter is at least three; and the extremal foliated family in Theorem 2.12 exposes its paired leaves directly. The generator does not present any of those as Track-A hardness.

## Worked demo

For `make_instance(n=3, component_max=3, seed=7)`, the complete rendered instance is:

```text
Power domination in a cubic graph

The graph is finite, simple, and undirected. Its vertices are 0 through 11.
For a set S, first mark S and all neighbors of S. Repeatedly, if a marked
vertex has exactly one unmarked neighbor, mark that neighbor. Find a power
dominating set of exactly 3 distinct vertices.

0: 2 5 6
1: 2 4 8
2: 0 1 6
3: 5 7 11
4: 1 8 9
5: 0 3 6
6: 0 2 5
7: 3 10 11
8: 1 4 9
9: 4 8 10
10: 7 9 11
11: 3 7 10

Give the answer as a comma-separated list inside <answer></answer> tags.
```

The three hidden diamonds are `{0,2,5,6}`, `{1,4,8,9}`, and `{3,7,10,11}`. Thus `<answer>0, 8, 11</answer>` parses to `[0, 8, 11]`, and `verify` returns `(True, "ok")`. Dropping `11` returns `(False, "answer must contain exactly 3 vertices")`. This demo is genuinely hand-solvable: compare closed neighborhoods to locate the three adjacent true-twin pairs and choose one vertex from each block.

## Difficulty presets

| preset | diamonds `n` | vertices | maximum component | status |
|---|---:|---:|---:|---|
| demo | 3 | 12 | 3 | hand example; skipped by hardener |
| easy | 24 | 96 | 8 | local gates pass |
| medium | 96 | 384 | 13 | local gates pass |
| hard | 249 | 996 | 17 | provisional shipping preset; local gates pass |

The witness grows because every necklace diamond contributes a necessary atom. `hard` is deliberately near the 256-atom cap; `escalate()` returns `cap_bound` after this level. No preset was rejected by a local gate.

## Gate results

| gate | result |
|---|---|
| G1 | pass: 16/16 preset/seed cases; every answer is JSON-native |
| G2 | pass: five corruptions rejected with five distinct reasons |
| G3 | pass: realistic tagged prose round-trips; garbage returns `None` |
| G4 | pass: 0/200,000 uniform structured guesses; exact density `1.606e-92` |
| G5 | pass: `4^249` exact solutions among `C(996,249)` candidates; reference mean 15,936 operations and 0.000941 s |
| G6 | pass: degree outlier, greedy coverage, 256 restarts, and periodic-label ansatz each solve 0/8; reference algorithm solves 8/8 |
| G7 | pass: a doubled 1,992-vertex instance builds and verifies |
| G8 | pass: 80/80 relabelling/reordering checks; 20/20 unrelated keys distinct |
| G9(c) | pass: 1,225 characters, about 307 tokens, 249 atoms, 261 intended-route operations |

## Oracle loop and G9 diagnostics

The required OpenRouter run did **not** produce hardness evidence. Four redraws all returned HTTP 403, “Key limit exceeded (total limit),” before any valid oracle response. The harness-owned error transcript and metadata are retained, but this directory is not submission-ready until the run is repeated with a funded key.

| preset | seed | model | outcome |
|---|---:|---|---|
| easy | 1900558444 | Claude Sonnet 5 | API error; not counted |
| easy | 901991679 | GPT-5.6 Terra | API error; not counted |
| easy | 899940198 | Claude Sonnet 5 | API error; not counted |
| easy | 1368701630 | Claude Sonnet 5 | API error; not counted |

| G9 arm | solved / valid attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 | blocked by OpenRouter key limit |
| structural hint | 0 / 0 | not measured |
| placebo hint | 0 / 0 | not measured |

`hinted - placebo` is therefore not defined from observations; the zero stored in `selftest_report.json` is only the module's pre-run placeholder. The structural hint names the equal-closed-neighborhood invariant and does not state the follow-up procedure.

## Use

```python
from gen_1610_03115 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer("Result: <answer>0, 8, 11</answer>")
print(verify(inst, candidate))  # (True, "ok")
```

After obtaining a valid hardened transcript, emit from the repository root with:

```bash
bash scripts/emit.sh 1610.03115 20 hard
```

## Caveats

- This is a compression benchmark, not evidence of average-case or complexity-theoretic hardness. Recognizing equal closed neighborhoods makes every instance easy.
- The `0/200,000` guess result uses the declared uniform prior over all distinct size-`k` subsets. It says nothing about an informed solver that conditions on true twins; the reference algorithm succeeds every time.
- The tested attacks do not include an ILP/SAT encoding, a generic exact power-domination solver, or a spectral method. The distribution-specific linear-time signature algorithm is stronger than those for the intended decomposition leak, but it does not benchmark their constants.
- `obstruction_blocks` is redundant instance metadata used to make the 200,000 density trials cheap. It is omitted from `render` and artifacts; `canonical_key` recovers the blocks from the graph itself.
- Structural diversity is exactly the multiset of necklace component lengths. The canonical key is complete for this generated family, but the family does not sample arbitrary cubic graphs.
- The answer has 249 atoms, close to the 256-atom cap. Greater difficulty on this construction requires more diamonds and therefore a longer certificate; that is why further escalation is `cap_bound`.
