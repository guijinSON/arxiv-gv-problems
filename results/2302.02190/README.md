# Additive list colorings on triangulated even cycles

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple (one chosen list label per variable vertex) |
| Native objects | Example 5.4's triangulated even cycle, integer vertex lists, additive coloring |
| Intended intuition | invariant: selected-minus-omitted residues form a geometric progression modulo 7 |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

This module instantiates the additive list-coloring problem in Ian Gossett's
[An Alon-Tarsi Style Theorem for Additive Colorings](https://arxiv.org/abs/2302.02190),
using exactly the graph family `G_{2k}` in Example 5.4. The `v_i` vertices form
an even cycle, and a degree-two vertex `u_i` completes a triangle on every
cycle edge. Labels on the `u_i` are fixed; the solver chooses one positive
integer from each list on the `v_i`. A witness is valid precisely when the
ordinary-integer sums on the open neighborhoods of the endpoints of every
edge differ (Definition 2.1).

The witness is sampled before the public lists are built. Each new planted
label avoids the one value that could violate the newly closed cycle edge;
only three wrap-around constraints are retried. The planted value is then
hidden among five same-alphabet decoys, and a random dihedral relabeling is
applied. Generation never solves the public instance. Verification is exact:
list membership, integer additions, and inequality comparisons only. Theorem
5.2 plus Example 5.4 independently guarantees colorability even for arbitrary
four-element sublists, so using six-element lists stays inside the theorem's
solvable regime.

## Why Track B is honest

This is not a Track A claim. The graph has constant width. A dynamic program
that remembers the first three and last three list choices solves the cyclic
CSP in `O(n*s^7)` time, hence linear time for the fixed list size `s=6`.
At shipping `n=256`, the included generic implementation solved 8/8 instances
and averaged **1,619,199 exact operations** and **0.109 s** in the final run.

The compressed route uses the two exceptional fixed labels to recover an
origin, direction, initial residue, and primitive ratio. The offset from the
unique omitted list residue repeats with period six, so six offsets suffice
for all 256 entries. This costs **264 exact operations**, but the statement
does not announce the coupling. Theorem 5.2 makes existence easy to prove;
it does not provide a recovery algorithm—the paper's proof is through the
Combinatorial Nullstellensatz. The separate bounded-width dynamic program is
the efficient method that rules out Track A.

## Worked demo

For `make_instance(n=6, q=7, seed=3)`, the complete rendered data are:

```text
The graph has v_0,...,v_5 and u_0,...,u_5.  For every i modulo 6 its
edges are v_i--v_(i+1), u_i--v_i, and u_i--v_(i+1).

i  fixed(u_i)  list(v_i)
0      28       [1,7,6,3,5,4]
1      28       [7,5,3,1,4,6]
2      17       [3,1,6,4,5,7]
3      11       [2,7,1,6,5,3]
4      28       [2,6,4,7,3,5]
5      28       [3,6,7,4,2,5]
```

The answer is `<answer>[4,5,3,2,5,7]</answer>` and
`verify(inst, answer)` returns `(True, "ok")`. Replacing its first entry by
7 gives `[7,5,3,2,5,7]`; verification returns
`(False, "neighbour-sum collision on cycle edge v_5--v_0: both sums are 68")`.
This demo is hand-solvable: the special fixed labels decode initial residue 4
and ratio 3, and the missing-list offsets can be followed around six vertices.
It deliberately has many answers (37,634 of 46,656 list choices), because it
is an illustration rather than a difficulty level.

## Difficulty presets

| preset | `n` variable labels | candidate language | status |
|---|---:|---:|---|
| demo | 6 | `6^6` | hand-scale illustration; skipped by hardening |
| easy | 224 | `6^224` | local gates pass; this size was oracle-solved before ladder sliding |
| medium | 240 | `6^240` | local gates pass; oracle-solved before ladder sliding |
| hard | 256 | `6^256` | **shipping**; held 0/3 |

The original oracle run began at `n=160`, then tried 192, 224, 240, and 256.
Because the escalated 256 level held, the named ladder was slid upward as the
protocol requires. No preset failed a correctness or adversary gate; the
smaller levels were rejected only by the oracle loop.

## Gate results at shipping

| gate | result | measured evidence |
|---|---|---|
| G1 planted verifies | pass | 16/16 preset-seed checks; all answers JSON-native |
| G2 corruption | pass | empty, dropped, out-of-range, swapped, and duplicated perturbations all rejected with 5 distinct reasons |
| G3 round-trip | pass | tagged model-style response recovered; 4/4 garbage forms rejected |
| G4 guess resistance | pass | 0/200,000 structure-aware independent list choices; language size `6^256` (662 bits) |
| G5 density/cost | pass | shipping sampled density 0/200,000; demo exact count 37,634; random-restart baseline 256 iterations, 0.017 s; reference DP 1,619,199 operations, 0.109 s |
| G6 adversaries | pass | endpoint outlier 0/8, greedy 0/8, 256 restarts 0/8, constant-offset ansatz 0/8; reference DP 8/8 as expected |
| G7 scaling | pass | doubled `n=512` builds and verifies; candidate-space bits grow 662 to 1,324 |
| G8 canonical key | pass | 60/60 dihedral/list reorderings invariant and carried witnesses valid; 20/20 unrelated keys distinct |
| G9 caps | pass | 513 characters, 129 estimated tokens, 256 atoms, 264 intended operations |

Wall-clock figures are machine-load dependent; operation counts are the stable
comparison. Full measurements are in `selftest_report.json`.

## Bare oracle loop

The preset names below are those recorded before the required ladder slide.

| rung | model | seed | result | verifier evidence |
|---|---|---:|---|---|
| easy (`n=160`) | gpt-5.6-terra | 1546212829 | failed | returned 157 labels, expected 160 |
| easy (`n=160`) | gemini-3.8-flash | 1311272160 | solved | verified witness |
| easy (`n=160`) | gemini-3.8-flash | 66392289 | solved | verified witness |
| medium (`n=192`) | gpt-5.6-terra | 1843675721 | failed | returned 198 labels, expected 192 |
| medium (`n=192`) | gemini-3.8-flash | 753662912 | solved | verified witness |
| medium (`n=192`) | gemini-3.8-flash | 1938869194 | solved | verified witness |
| hard (`n=224`) | gemini-3.8-flash | 1587298160 | solved | verified witness |
| hard (`n=224`) | gpt-5.6-terra | 1733717803 | failed | returned 226 labels, expected 224 |
| hard (`n=224`) | gpt-5.6-terra | 788623503 | failed | label for `v_5` absent from its list |
| escalated (`n=240`) | gemini-3.8-flash | 2027678725 | solved | verified witness |
| escalated (`n=240`) | gpt-5.6-terra | 2038001609 | failed | returned 258 labels, expected 240 |
| escalated (`n=240`) | gpt-5.6-terra | 295059188 | failed | returned 242 labels, expected 240 |
| escalated (`n=256`) | gpt-5.6-terra | 319676880 | failed | label for `v_43` absent from its list |
| escalated (`n=256`) | gemini-3.8-flash | 1261045265 | failed | label for `v_186` absent from its list |
| escalated (`n=256`) | gpt-5.6-terra | 779931297 | failed | returned 294 labels, expected 256 |

The script-owned verdict is `hardened` at `n=256`. Every reply contained a
parseable tagged list, so none of these failures is a parser false negative.

## G9 diagnostic arms

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0/3 | shipping prompt held |
| structural hint | 1/3 | one model used the named recurrence successfully; the one-rung copy then reported `cap_bound` |
| placebo hint | 0/3 | adding a same-register sentence alone did not help |

Hinted minus placebo is **+1/3**. The structural sentence therefore carries
real information, consistent with an invariant-discovery task, but naming the
invariant did not make execution reliable across all three attempts. These
arms are diagnostic, not gates. Their script-owned evidence is preserved in
`g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl`.

## Use

From the repository root:

```python
import importlib.util

path = "results/2302.02190/gen_2302_02190.py"
spec = importlib.util.spec_from_file_location("g", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
prompt = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Emit 20 shipping instances with:

```bash
bash scripts/emit.sh 2302.02190 20 hard
```

## Caveats

- This is a synthetic Track B distribution, not an average-case hardness
  theorem. A solver that notices the modular recurrence can solve it compactly;
  a solver with code can always use the 0.109-second dynamic program.
- The 0/200,000 density estimate applies only to the declared prior: one
  uniformly random legal member from each list, independently. It does not
  bound recurrence-aware, local-search, SAT, or learned priors.
- The generator filters the four reported construction-aware heuristics. That
  protects against those signatures but can itself shape the distribution.
- An exact bounded-width dynamic program is stronger and more relevant here
  than a spectral relaxation. No external CP-SAT, ILP, or general SAT package
  was tested; the included exact DP is the domain-standard reference attack.
- The shipping witness sits exactly at the 256-atom cap and its compact route
  uses 264 of the allowed 300 operations. Although only 513 characters, some
  oracle failures were length errors, so part of the observed difficulty is
  faithful execution/transcription after discovery, not discovery alone.
