# arXiv 1611.01542 — verified p-set-splitter generator

**Status:** the module and all locally gated checks pass, but the result is not yet
shippable. The required four-vendor hardening and G9 diagnostic calls all received
OpenRouter HTTP 403 `Key limit exceeded`, so no model produced a scored attempt and
no oracle-hardness verdict is claimed.

| profile | value |
|---|---|
| track | B — no-tool compression |
| native domain / regime | combinatorics / finite discrete |
| core / certificate | exact cover / integer tuple (the natural splitter subset) |
| native objects | finite set collection and a p-splitter subset |
| intuition | invariant: a modular arithmetic progression hidden among regular-incidence decoys |
| domain essentiality | native; no reduction |

## Problem and trust model

This is the native problem defined in Bernstein, Bortner, Coskey, Li, and
Simpson, [*The set splittability problem*](https://arxiv.org/abs/1611.01542).
For `p=1/d`, the solver receives an indexed finite collection whose sets all
have `d` labels and must return a subset meeting every listed set exactly once.
The verifier checks only membership and exact intersection cardinalities and
accepts any valid splitter; it never reads the planted answer.

Generation is inverse. A perfect matching of `n` three-element incidence
columns is sampled first. Decoy columns are added from cyclic regular layers,
mixed by degree-preserving switches, and all rows and labels are shuffled. The
matching labels form a modular arithmetic progression. Thus the certificate is
known before the emitted instance exists; no solving occurs in generation.

## Why Track B

Section 2 writes p-SPLIT as the binary system `M y = round(p M 1)`, and Theorem
2.1 proves NP-completeness for every fixed `0<p<1`. That is worst-case context,
not average-case evidence for this distribution, so this module does **not**
claim Track A.

The domain-standard Algorithm X reference solver succeeds 8/8 at shipping
`n=40,d=5`: 88,394 search nodes and 2.283 s on average, with maxima of 151,778
nodes and 4.506 s. The construction-aware ordered-pair progression scan also
succeeds 8/8 in exactly 1,592,000 modular advances, 0.282 s mean. Its complexity
is `O((dn)^2 n)`; Algorithm X is `O(d^n)` in this bounded-degree formulation.
Once the progression's start and step are recognized, the intended route takes
39 modular additions and at most 177 mergesort comparisons, 216 operations
total. That measured mechanical/compact gap is the Track B claim.

The generator avoids the paper's explicit easy regimes: Section 3, Theorem 3.3
handles only two sets; these instances have `3n`. Section 4, Theorem 4.5 uses
large multiplicity-one Venn regions; every generated element instead has
multiplicity three. Theorem 4.6 assumes ground-set size in `omega(2^m m)` for
`m` sets; here it is only `dn` for `m=3n`.

## Worked demo (`seed=0`)

This smallest supported instance is hand-solvable: the four answer labels form
an ordinary progression of difference 228163. The exact `render()` output is:

```text
Find an exact p-splitter for the finite set collection below.

Definitions: the ground set U is the displayed set of distinct integer labels.
For p = 1/d, a p-splitter is a subset S of U such that every listed set B
contains exactly the nearest integer to |B|/d elements of S.  Here every
listed set has d = 3 elements, so the required intersection size is exactly 1.
Every ground-set label occurs in exactly three listed sets; consequently S must have exactly n = 4 labels.
The listed sets are indexed constraints; equal rows, if present, are each checked.
Labels are residues modulo the displayed prime, represented by their unique
integers from 0 through prime-1.  Only membership in the listed sets determines
whether an answer is a valid splitter; the residue labels are part of the instance.
Order in S does not matter, repeats are forbidden, and all bounds are inclusive.

prime = 1000003
p = 1/3
U (12 labels) = 6752, 52188, 238036, 449073, 466199, 540313, 561537, 691662, 694362, 777961, 900827, 922525
Listed sets (12 total, indexed 0 through 11):
B0 = 52188, 466199, 561537
B1 = 6752, 52188, 922525
B2 = 449073, 694362, 900827
B3 = 52188, 900827, 922525
B4 = 466199, 540313, 691662
B5 = 6752, 466199, 777961
B6 = 561537, 691662, 922525
B7 = 449073, 694362, 900827
B8 = 238036, 561537, 691662
B9 = 540313, 694362, 777961
B10 = 238036, 449073, 777961
B11 = 6752, 238036, 540313

Give exactly 4 distinct labels in increasing order, separated by commas.
Give your final answer inside <answer></answer> tags, as a comma-separated list of integers.
Format example only: <answer>12, 47, 105</answer>
Output nothing else inside the tags.
```

The answer is `<answer>238036, 466199, 694362, 922525</answer>`.
`verify` returns `(True, "ok")`; dropping the last label returns
`(False, "wrong cardinality: expected 4 labels")`.

## Presets and gates

| preset | n | d | universe | answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 4 | 3 | 12 | 4 | hand example; skipped by harden.py |
| easy | 40 | 5 | 200 | 40 | shipping preset |
| medium | 40 | 6 | 240 | 40 | more decoys, same witness |
| hard | 40 | 7 | 280 | 40 | more decoys, same witness |

`escalate()` continues increasing `d` before it ever lengthens the answer.

| gate | result | measurement |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose round-trip; answer is JSON-native |
| G4 | pass | 0/200,000 fixed-cardinality guesses; language size `C(200,40)` = 2.050157995198589e42 |
| G5 | pass | shipping density 0/200,000; demo exactly 1/495; seed-17 Algorithm X 17,835 nodes / 0.746 s |
| G6 | pass | codegree outlier, first-fit, 256 restarts, first-pair AP ansatz: each 0/8; references above |
| G7 | pass | doubled `n=80` verifies; `d=6` fixed-answer escalation verifies |
| G8 | pass | 60 relabelling/composition invariance and 60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | representative 316 chars/79 tokens; worst-case bound 323/81; 40 atoms; 216 operations |

## Oracle and G9 diagnostics

The bare run made four API calls at `easy`; all were unscored HTTP 403 errors
(seeds 1965347227, 1398027265, 856828240, 1084171090). Therefore there is no
`hardened`, `too_easy`, or shipping verdict. The transcript is preserved exactly
as written by `harden.py`.

| arm | solved / scored attempts | API calls | conclusion |
|---|---:|---:|---|
| bare | 0/0 | 4 errors | not estimable |
| structural | 0/0 | 4 errors | not estimable |
| placebo | 0/0 | 4 errors | not estimable |

`hinted - placebo` is consequently not estimable (the numeric placeholder in
the report is `0.0` with `diagnostic_complete=false`). No conclusion about the
hint's effect is claimed. Restore OpenRouter quota and rerun all three arms in
their separate directories; do not interpret these errors as model failures.

## Use

```python
import gen_1611_01542 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["easy"])
candidate = g.parse_answer(
    "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
)
assert g.verify(inst, candidate) == (True, "ok")
```

After a successful hardening verdict, emit from the repository root with:

```bash
bash scripts/emit.sh 1611.01542 20 easy
```

## Caveats

This is a Track B pattern-recognition benchmark, not an average-case NP-hardness
claim. Both documented reference algorithms make it easy with a sandbox. The
0/200,000 figure is empirical under a uniform prior over all increasing
40-subsets; it is neither an exact solution count nor a confidence proof of zero
density. Recognizing the particular progression start and step is treated as
the insight; if that recognition itself requires an exhaustive pair scan, the
compact route ceases to be compact—this is the main unresolved benchmark risk
that the missing oracle/G9 runs must probe.

No external SAT/ILP package or optimized DLX implementation was tested. The
canonical key is a strong rooted-walk/codegree invariant, not a complete
incidence-isomorphism canonical form, so rare collisions remain possible. Most
importantly, the mandatory four-vendor evidence is absent for an external quota
reason; this directory must not be submitted until a scored run produces a real
verdict.
