# Free-group word equations from arXiv:0705.4246

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite discrete |
| Computational core | other (free-group word equation) |
| Certificate | exact symbolic pair of group words |
| Intuition | change of variables via a Nielsen matrix |
| Domain essentiality | native; no reduction |

## What the family is

An instance gives a word `w(x,y)` and a target word `u` in the free group
`F(a,b)`. The solver supplies concrete words `x,y`, of stated lengths and
letter multiplicities, such that substituting them into `w` and freely reducing
produces `u`. Verification is exact stack reduction and comparison. These are
the paper's own objects and its Section 1.1 definition, not a discrete surrogate.
Source: [Nicholas Touikan, *The equation w(x,y)=u over free groups*](https://arxiv.org/abs/0705.4246).

Generation starts from the rank-two solution calculated in Section 3 for
`[x,y]^2 x`, applies a fixed rational equivalence, and samples elementary
Nielsen transformations. Definition 2.15 and Lemma 2.16 transport the known
solution through every transformation. The certificate therefore exists before
the emitted equation is formed; the generator never searches for it.

## Why Track B

Track A would be false: the Introduction cites Ciobanu's polynomial-time
algorithm for deciding the rank-two endomorphism problem. Lemma 2.17 also makes
Nielsen reduction effective. The executable reference solver shortens the full
word by inverse Nielsen shears. At the `easy` shipping preset it solved 8/8
instances, requiring 33,268 word-symbol scans in about 0.03 seconds total;
on this positive-Nielsen distribution its cost is `O(n|w|)`.

The compressed route instead notices that the displayed exponent-sum pair is
the sum of the columns of a nonnegative unimodular matrix. A Bezout identity
recovers the columns, Euclidean subtraction factors the matrix into Nielsen
shears, and the Section 3 pair is transported backward. This used at most 121
exact operations. Section 2.1's easy regimes are avoided: Proposition 1.9 covers
primitive `w`, Lemma 2.2 covers target `1`, and Lemma 2.3/Corollary 2.5 cover
proper powers and forced rank-one solutions. The transformed Section 3 word is
nonprimitive and not a proper power, the target is nontrivial, and the planted
pair is rank two.

## Worked demo

For `seed=0`, `render()` returns this complete hand-scale statement:

```text
Solve one exact equation in the free group F(a,b).

A word is a string over a, A, b, B. Here A means a^(-1), B means
b^(-1), juxtaposition is multiplication, and the empty word is the identity.
Equality means equality after repeatedly deleting consecutive inverse pairs aA,
Aa, bB, or Bb. The unknown words x and y are substituted into a word over
x, X, y, Y, where X means x^(-1) and Y means y^(-1).

Equation word w(x,y): xyxxyXYxyXYXYXXYX
Target reduced word u: baBAbaBB

For reference, the exponent sums of x and y in w are respectively -2 and -1.
An exponent sum counts lowercase as +1 and its uppercase inverse as -1.

Find words x and y such that freely reducing w(x,y) gives exactly u. Your
spelled words need not themselves be freely reduced, but they must obey:
  x has length 5 and counts [a,A,b,B] = [1, 2, 1, 1];
  y has length 6 and counts [a,A,b,B] = [2, 1, 2, 1].
Order matters, repetitions are allowed exactly as prescribed by those counts,
and all indexing implicit in the strings is left-to-right.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly two string fields, x and y.
Example: <answer>{"x":"aB","y":"bA"}</answer>
Output nothing else inside the tags.
```

The answer is `{"x":"aBAbA","y":"aBabbA"}`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the last
letter of `x` returns `(False, "x must have length 5")`. A person can solve
this demo by hand by trying the two one-step inverse Nielsen changes.

## Difficulty presets

| preset | Nielsen depth | min. direction switches | target choices | answer cap | status |
|---|---:|---:|---:|---:|---|
| demo | 1 | 0 | 1 | 32 | hand example; skipped by hardener |
| easy | 7 | 3 | 3 | 150 | **ships; bare oracle held 0/3** |
| medium | 9 | 5 | 4 | 220 | not reached |
| hard | 10 | 6 | 4 | 250 | not reached |

## Gate results

| gate | result | measurement at shipping unless noted |
|---|---|---|
| G1 | pass | 16/16 planted witnesses verified across all presets |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON round-tripped through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; language size 10,285,670,525,130,000 |
| G5 | pass | shipping density 0/200,000; demo exactly 1/10,800; 256 restarts failed in 0.076 s |
| G6 | pass | four attacks at 0/8; reference and compact solvers both 8/8 |
| G7 | pass | `n=14` built and verified; equation length grew from 153 to 1,637 |
| G8 | pass | 60/60 relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |
| G9(c) | pass | representative: 58 chars/43 letters/15 tokens; preset maximum 116/101/29; 121 operations |

G4 samples independent uniform permutations of each disclosed letter multiset,
so all obvious shape and count constraints are already enforced. Finite quotient
checks only accelerate rejection: every quotient match is passed to the exact
verifier.

## Oracle loop

The script-owned bare loop stopped at `easy`; all three valid calls failed. A
parsed answer is shown as such below, including its exact verifier failure.

| model | seed | parsed | solved | reason |
|---|---:|---:|---:|---|
| `openai/gpt-5.6-terra` | 110126297 | yes | no | substituted word did not equal `u` |
| `google/gemini-3.8-flash` | 822038033 | yes | no | `x` had the wrong length |
| `openai/gpt-5.6-terra` | 1066872713 | yes | no | substituted word did not equal `u` |

## G9 arms

| arm | solved/attempts | result |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

Thus `hinted - placebo = 0.0`: in this three-call sample, naming the unimodular
matrix invariant bought no measurable advantage. One hinted Gemini call used
its 32,000-token completion budget in reasoning and emitted no answer; the other
five G9 calls emitted substantive answers, so this limitation is recorded rather
than hidden. The shipping witness is at most 116 serialized characters, 101
letters, and 29 estimated tokens; the compact route uses at most 121 exact
operations.

## Use

```python
from gen_0705_4246 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 0705.4246 20
```

## Caveats

This family is easy with the included reference solver or a suitable free-group
package; that is exactly why it is Track B. It also becomes easy by recognizing
the exponent-sum invariant and completing the Bezout/Euclidean route. The G4
density is empirical and relative only to uniform multiset permutations; it is
not a uniqueness proof or a bound for a structure-aware learned prior. Exact
length and letter-count constraints are benchmark scaffolding, not hypotheses
of Touikan's theorem.

The adversary panel does not implement Ciobanu's complete algorithm or a general
Whitehead automorphism search; it tests the distribution-standard full-word
L/R descent plus frequency, target-prefix, random-restart, and single-shear
attacks. `canonical_key` is complete for signed permutations/inversions of the
two coefficient generators and two variables, but not for arbitrary Nielsen
equivalence. Finally, the G9 sample is only three calls per arm and one hinted
call was output-budget-limited, so the observed zero hint effect is suggestive,
not conclusive.
