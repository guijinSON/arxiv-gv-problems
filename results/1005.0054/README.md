# Verified generator for arXiv:1005.0054

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | integer lattice |
| Computational core | linear algebra |
| Certificate | ordered integer tuple |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

This module instantiates the search version of Matrix Representability from
Caballero-Gil and Hernández-Goya, [*Secret Sharing Based on a Hard-on-Average
Problem*](https://arxiv.org/abs/1005.0054).  The solver receives square integer
matrices, represented exactly by `M_i = M1 + (i-1)R`, and a target integer
matrix `T`.  It must return an ordered list of `n` distinct one-based indices
whose matrices multiply to `T`.  The generator samples that ordered list first
and constructs `T` from it.  The checker independently multiplies the submitted
matrices using Python integers and compares every entry; it never reads the
planted answer.

Section 2 of the paper fixes the definition and cites average-case
NP-completeness for flat-distributed `20 x 20` inputs, plus average-case
search/decision equivalence.  Section 4 fixes the dealer's answer-first
construction.  Those are different distributions: conditioning the dealer's
output to be representable is not covered by the flat-distribution theorem.
Section 5 also says that concrete difficult constructions were future work.
Consequently this is deliberately **not Track A** and makes no cryptographic or
average-case hardness claim for its structured distribution.

The paper later quotes the multiset coefficient `C(k+n-1,n)` as its exhaustive
search space, which conflicts with both “ordered subset” and noncommutative
matrix multiplication.  This module resolves the ambiguity explicitly: order
matters, indices are distinct, and the candidate language has size `k!/(k-n)!`.

Internally, the generator conjugates blocks
`[[B,i],[0,1]] ⊕ D` by one integer unimodular matrix.  A product therefore
encodes its ordered indices as `i1 + B*i2 + ... + B^(n-1)*in`; all digits are
smaller than `B`, so the planted representation is unique in the declared
language.  This identity is how the generator knows the certificate without
solving its output.

The Track B reference algorithm exploits the displayed affine line, computes
`M1^n` by exact repeated matrix multiplication, extracts one scalar, and radix
decodes the witness.  Its complexity is `O(n r^3)`.  At the shipping preset it
solves 8/8 instances, costs 156,813 counted scalar operations, and takes a
median 0.0083 seconds in the final self-test on this host.  The intended shortcut recognizes a sparse
bilinear functional preserved by the common unimodular basis change; it needs
29 exact operations.  The distinction is therefore compression, not
computational intractability.

## Worked demo

This is `render(make_instance(seed=0, **DIFFICULTY["demo"]))` in full:

```text
ORDERED INTEGER-MATRIX REPRESENTATION

There are k=4 distinct square integer matrices M1,...,M4, each of order r=4.
The target is another 4 by 4 integer matrix T. An ordered representation
is a sequence of exactly n=2 DISTINCT indices (i1,...,i2) such that
ordinary left-to-right integer matrix multiplication gives
M_i1 * M_i2 * ... * M_in = T.
Order matters, no index may repeat, and indices are one-based (1 through k).
All arithmetic is over the ordinary integers, with no modulus and no rounding.
The auxiliary public integer B for this instance is B=15.

The complete matrix list is supplied by the following exact affine presentation.
Every addition and scalar multiplication in this presentation is entrywise:
M1=[[15,13,13,13],[-156,-157,-250,-250],[156,158,251,326],[0,0,0,-75]]
R=[[0,-1,-1,-1],[0,-2,-2,-2],[0,2,2,2],[0,0,0,0]]
For every one-based index i from 1 through 4, define M_i = M1 + (i-1)*R.
This formula defines all k matrices; there is no omitted data.

T=[[225,162,162,162],[-16848,-16971,-25620,-25620],[16848,16972,25621,19996],[0,0,0,5625]]

Give your final answer inside <answer></answer> tags as exactly n
comma-separated one-based decimal indices in multiplication order.
Do not use brackets and output nothing else inside the tags.
Example of the required shape: <answer>1, 2</answer>
```

The answer is `<answer>2, 4</answer>`.  `verify(inst, [2, 4])` returns
`(True, "ok")`; reversing it gives `verify(inst, [4, 2]) == (False,
"ordered product does not equal the target")`.  A person can solve this demo by
checking its twelve possible ordered pairs on paper.  The demo illustrates the
format and is not a hardness level.

## Difficulty presets

| preset | `n` | `k` | `r` | candidate language | compact ops | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 2 | 4 | 4 | 12 | 9 | hand-scale illustration |
| easy | 10 | 24 | 20 | 7,117,005,772,800 | 29 | **ships; oracle hardened** |
| medium | 12 | 32 | 20 | 108,155,131,628,544,000 | 31 | available, not needed |
| hard | 16 | 40 | 20 | 1,315,041,316,842,168,115,200,000 | 35 | available, not needed |

The ladder increases word length, the factor haystack, radix size, and basis
disguise.  `escalate()` keeps the answer length fixed while increasing `k`, the
radix, and the number of unimodular shears.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted checks passed; 12/12 answers JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | model-style tagged response round-tripped; untagged garbage rejected |
| G4 | 0/200,000 uniform structure-aware guesses; space `24P10 = 7,117,005,772,800` |
| G5 | shipping sampled fraction 0/200,000; demo exact count 1/12; baseline 156,813 ops and 0.0081 s |
| G6 | norm outlier, target-entry greedy, 256 restarts, and visible-entry radix ansatz each 0/8; reference 8/8 |
| G7 | doubling `n` from 10 to 20 built and verified; space grew from 43 to 106 bits |
| G8 | 140/140 reordering, signed-permutation, unimodular-shear, and composition checks invariant; 140/140 carried witnesses valid; 20/20 unrelated keys distinct |
| G9 | hinted pool hardened; worst-case 40 answer characters, 10 atoms, about 10 tokens, 29 intended operations |

## Oracle loop

The bare run hardened at `easy` without escalation.  All scored calls used
reasoning effort `medium` and distinct seeds.

| model | seed | result | verifier outcome |
|---|---:|---|---|
| Claude Sonnet 5 | 2,049,655,579 | failed | empty length-limited response |
| Gemini 3.1 Pro Preview | 1,224,095,402 | failed | parsed; wrong ordered product |
| GPT-5.6 Terra | 1,792,829,939 | failed | parsed; wrong ordered product |

The complete machine-written evidence is in `llm_loop_transcript.jsonl` and
`.meta.json`.

## G9 arms

| arm | solved / scored attempts | verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

The hinted-minus-placebo success difference is `0.0`.  The named invariant did
not measurably help this three-call pool, so the run does not show that the
claimed intuition was recognized.  One hinted Grok call timed out and was
correctly excluded; Gemini supplied the replacement third score.  The answer is
at most 40 serialized characters / 10 atomic elements, and the compact route is 29
exact operations, within both G9 caps.

## Use

```python
import gen_1005_0054 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
statement = g.render(inst)
answer = g.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit dataset instances with:

```bash
bash scripts/emit.sh 1005.0054
```

## Caveats

This family becomes easy with ordinary exact-arithmetic tooling: the disclosed
reference algorithm takes milliseconds.  It is a Track B benchmark only.  Its
matrices are strongly correlated along an affine line and must not be treated as
samples from the paper's flat hard-on-average distribution or as evidence for
the paper's proposed cryptosystem.  The `0/200,000` guess result applies only to
the declared uniform prior over ordered distinct index lists; it says nothing
about informed algebraic priors.

The adversary panel tests construction-specific scalar statistics, greedy
ranking, random restarts, and the obvious un-conjugated radix guess, and the
successful exact affine-line algorithm is reported separately as Track B
requires.  It does not test every CAS strategy, automated invariant discovery,
or cryptanalytic side channel.  Finally, one bare Claude response exhausted its
32,000-token allowance without emitting content; the other two bare vendors
returned concrete but invalid witnesses, and all three placebo vendors returned
concrete invalid witnesses.  The oracle evidence should be read with that
limitation visible.
